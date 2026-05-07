from __future__ import annotations
from datetime import date, datetime
import logging
from typing import Optional
import numpy as np
import pandas as pd
from supabase import Client
from xgboost import XGBRegressor

logger = logging.getLogger(__name__)

MIN_MONTHS_FOR_FORECAST = 2   # need at least 2 distinct calendar months to train XGBoost
DEFAULT_MONTHLY_BUDGET  = 500.0


class ForecastingService:
    """XGBoost-based monthly spend forecasting and burnout probability calculation.

    Pipeline:
      1. Fetch all *processed* expenses for the user from Supabase.
      2. Aggregate into monthly totals.
      3. Engineer lag features (lag_1/2/3, rolling_3, month_num).
      4. Train XGBoost on the full history (small dataset — fast).
      5. Predict next-month spend from the most recent month's features.
      6. Compute burnout probability via a sigmoid centred at budget.
      7. Upsert the result into the predictions table.

    Returns a ``cold_start: true`` payload when fewer than
    MIN_MONTHS_FOR_FORECAST distinct months are available.
    """

    def __init__(self, supabase: Client):
        self.db = supabase

    def get_prediction_for_user(self, user_id: str, budget: Optional[float] = None) -> dict:
        """Run the full forecast pipeline for *user_id*.

        Args:
            user_id: Authenticated user's UUID.
            budget:  Monthly budget override. Falls back to the DB value, then
                     DEFAULT_MONTHLY_BUDGET if neither is available.

        Returns:
            Dict with ``predicted_spend``, ``burnout_probability``, ``budget``,
            ``cold_start``, and metadata fields.
        """
        expenses = self._fetch_expenses(user_id)
        if not expenses:
            return self._cold_start_response(0, 0)
        df = self._to_dataframe(expenses)
        distinct_months = df["month"].nunique()
        if distinct_months < MIN_MONTHS_FOR_FORECAST:
            return self._cold_start_response(len(expenses), distinct_months)
        monthly = self._aggregate_monthly(df)
        predicted_spend     = self._run_model(monthly)
        budget              = budget if budget is not None else self._fetch_budget(user_id)
        burnout_probability = self._burnout_prob(predicted_spend, budget)
        result = {
            "user_id":             user_id,
            "month":               self._current_month_str(),
            "predicted_spend":     round(float(predicted_spend), 2),
            "burnout_probability": round(float(burnout_probability), 4),
            "budget":              budget,
            "generated_at":        datetime.utcnow().isoformat(),
            "cold_start":          False,
        }
        self._upsert_prediction(result)
        return result

    def _fetch_expenses(self, user_id: str) -> list[dict]:
        """Return all processed expense rows (amount + date) for the user."""
        resp = (self.db.table("expenses").select("amount, date, category_id")
                .eq("user_id", user_id).eq("status", "processed")
                .order("date", desc=False).execute())
        return resp.data or []

    def _fetch_budget(self, user_id: str) -> float:
        """Fetch the user's stored monthly_budget, falling back to DEFAULT_MONTHLY_BUDGET."""
        try:
            resp = (self.db.table("users").select("monthly_budget")
                    .eq("id", user_id).single().execute())
            val = resp.data.get("monthly_budget")
            return float(val) if val else DEFAULT_MONTHLY_BUDGET
        except Exception:
            return DEFAULT_MONTHLY_BUDGET

    def _to_dataframe(self, expenses: list[dict]) -> pd.DataFrame:
        """Convert raw expense dicts to a DataFrame with typed date and amount columns."""
        df           = pd.DataFrame(expenses)
        df["date"]   = pd.to_datetime(df["date"])
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
        df["month"]  = df["date"].dt.to_period("M")
        return df

    def _aggregate_monthly(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aggregate daily expenses into monthly totals and engineer lag features.

        Lag features capture the autoregressive pattern in monthly spending:
          lag_1/2/3  — previous 1/2/3 months' totals
          rolling_3  — 3-month rolling mean of the previous month
          month_num  — calendar month (1-12) to capture seasonal effects
        """
        monthly = (df.groupby("month")["amount"].sum().reset_index()
                   .rename(columns={"amount": "total_spend"}).sort_values("month"))
        monthly["lag_1"]     = monthly["total_spend"].shift(1)
        monthly["lag_2"]     = monthly["total_spend"].shift(2)
        monthly["lag_3"]     = monthly["total_spend"].shift(3)
        # min_periods=1 so rolling never produces NaN when fewer than 3 prior months exist
        monthly["rolling_3"] = monthly["total_spend"].shift(1).rolling(3, min_periods=1).mean()
        monthly["month_num"] = monthly["month"].apply(lambda p: p.month)
        # Fill unavailable lag slots with the expanding mean rather than dropping rows.
        # dropna() silently removed every row when < 4 months of data existed.
        expanding_mean = monthly["total_spend"].expanding().mean()
        for col in ["lag_1", "lag_2", "lag_3"]:
            monthly[col] = monthly[col].fillna(expanding_mean)
        return monthly.reset_index(drop=True)

    def _run_model(self, monthly: pd.DataFrame) -> float:
        """Train XGBoost on the full monthly history and predict next-month spend.

        The model is retrained on every call because each user's dataset is small
        (typically < 24 rows), making incremental training impractical.
        Prediction is clamped to 0.0 — negative spend is nonsensical.
        """
        feature_cols = ["lag_1", "lag_2", "lag_3", "rolling_3", "month_num"]
        X = monthly[feature_cols].values
        y = monthly["total_spend"].values
        model = XGBRegressor(n_estimators=200, max_depth=3, learning_rate=0.05,
                             subsample=0.8, random_state=42, verbosity=0)
        model.fit(X, y)
        last = monthly.iloc[-1]
        next_features = np.array([[
            last["total_spend"], last["lag_1"], last["lag_2"],
            float(monthly["total_spend"].tail(3).mean()),
            int((last["month_num"] % 12) + 1),
        ]])
        return max(float(model.predict(next_features)[0]), 0.0)

    @staticmethod
    def _burnout_prob(predicted_spend: float, budget: float) -> float:
        """Sigmoid probability that predicted spend will exceed budget.

        Formula: 1 / (1 + exp(-10 × (ratio - 1)))
        At ratio=1 (spend == budget) the probability is exactly 0.5.
        The steepness factor of 10 makes the transition sharp around the budget threshold.
        Returns 1.0 when budget is zero or negative (certain burnout).
        """
        if budget <= 0:
            return 1.0
        ratio = predicted_spend / budget
        return float(np.clip(1.0 / (1.0 + np.exp(-10.0 * (ratio - 1.0))), 0.0, 1.0))

    def _upsert_prediction(self, result: dict) -> None:
        """Persist the prediction to Supabase, replacing any existing row for the same user+month."""
        try:
            self.db.table("predictions").upsert({
                "user_id":             result["user_id"],
                "month":               result["month"],
                "predicted_spend":     result["predicted_spend"],
                "burnout_probability": result["burnout_probability"],
                "generated_at":        result["generated_at"],
            }, on_conflict="user_id,month").execute()
        except Exception as exc:
            logger.error("ForecastingService: prediction upsert failed: %s", exc)

    @staticmethod
    def _cold_start_response(expense_count: int, month_count: int) -> dict:
        months_needed = max(0, MIN_MONTHS_FOR_FORECAST - month_count)
        return {
            "cold_start": True,
            "expense_count": expense_count,
            "month_count": month_count,
            "months_needed": months_needed,
            "predicted_spend": None,
            "burnout_probability": None,
            "budget": None,
            "message": (
                f"Add expenses from {months_needed} more month(s) to unlock your forecast."
            ),
        }

    @staticmethod
    def _current_month_str() -> str:
        t = date.today()
        return f"{t.year}-{t.month:02d}"
