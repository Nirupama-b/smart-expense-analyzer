"""
Expense forecasting service using XGBoost.

Provides monthly spend predictions and budget burnout probability.
"""

import logging
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

_MIN_RECORDS = 10  # cold-start guard


class ForecastingService:
    """XGBoost-backed expense forecasting."""

    @staticmethod
    def predict_monthly_spend(
        user_expenses_df: pd.DataFrame,
    ) -> Optional[dict]:
        """
        Predict next month's spend for a user given their expense history.

        Parameters:
            user_expenses_df: DataFrame with at least ``date`` (datetime-like)
                and ``amount`` (numeric) columns.  An optional ``category``
                column is used for encoding if present.

        Returns:
            A dict with ``predicted_amount``, ``features_used``, and
            ``training_rows``, or **None** if there are fewer than
            ``_MIN_RECORDS`` rows (cold-start).
        """
        if user_expenses_df is None or len(user_expenses_df) < _MIN_RECORDS:
            logger.info(
                "Not enough records (%s) for forecasting — need at least %d",
                0 if user_expenses_df is None else len(user_expenses_df),
                _MIN_RECORDS,
            )
            return None

        from xgboost import XGBRegressor

        df = user_expenses_df.copy()

        # ── Ensure datetime ──────────────────────────────────────────
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)

        # ── Feature engineering ──────────────────────────────────────
        df["month"] = df["date"].dt.month
        df["day_of_week"] = df["date"].dt.dayofweek

        # Encode category if available
        if "category" in df.columns:
            df["category_encoded"] = df["category"].astype("category").cat.codes
        else:
            df["category_encoded"] = 0

        # Rolling averages (7-day and 30-day, on the amount column)
        df["rolling_avg_7"] = (
            df["amount"].rolling(window=7, min_periods=1).mean()
        )
        df["rolling_avg_30"] = (
            df["amount"].rolling(window=30, min_periods=1).mean()
        )

        feature_cols = [
            "month",
            "day_of_week",
            "category_encoded",
            "rolling_avg_7",
            "rolling_avg_30",
        ]

        X = df[feature_cols].values
        y = df["amount"].values

        # ── Train ────────────────────────────────────────────────────
        model = XGBRegressor(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.1,
            random_state=42,
        )
        model.fit(X, y)

        # ── Predict next month ───────────────────────────────────────
        last_row = df.iloc[-1]
        next_month = int(last_row["month"] % 12 + 1)
        next_features = np.array(
            [[
                next_month,
                last_row["day_of_week"],
                last_row["category_encoded"],
                last_row["rolling_avg_7"],
                last_row["rolling_avg_30"],
            ]]
        )

        predicted = float(model.predict(next_features)[0])
        logger.info("Predicted next-month spend: %.2f", predicted)

        return {
            "predicted_amount": round(predicted, 2),
            "features_used": feature_cols,
            "training_rows": len(df),
        }

    @staticmethod
    def calculate_burnout_probability(
        predicted_spend: float, budget: float
    ) -> dict:
        """
        Estimate the probability that the user will exceed their budget.

        Returns a dict with ``ratio``, ``probability`` (0-1), and a
        human-friendly ``risk_level`` string.
        """
        if budget <= 0:
            return {
                "ratio": None,
                "probability": 1.0,
                "risk_level": "critical",
            }

        ratio = predicted_spend / budget

        if ratio >= 1.0:
            probability = min(ratio / 1.5, 1.0)  # scale above 1
            risk_level = "critical"
        elif ratio >= 0.8:
            probability = ratio
            risk_level = "high"
        elif ratio >= 0.5:
            probability = ratio * 0.7
            risk_level = "medium"
        else:
            probability = ratio * 0.3
            risk_level = "low"

        return {
            "ratio": round(ratio, 4),
            "probability": round(probability, 4),
            "risk_level": risk_level,
        }
