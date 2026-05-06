import logging
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from supabase import create_client

from config import get_settings
from middleware.auth import get_current_user
from models.schemas import MonthlySpending, PredictionResponse, SpendingSummary

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _get_admin_supabase():
    settings = get_settings()
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


# ---------------------------------------------------------------------------
# GET /api/analytics/summary
# ---------------------------------------------------------------------------
@router.get("/summary", response_model=SpendingSummary)
async def spending_summary(
    budget: Optional[float] = Query(None, description="Monthly budget for utilization calc"),
    start_date: Optional[date] = Query(None, description="Filter expenses from this date"),
    end_date: Optional[date] = Query(None, description="Filter expenses until this date"),
    category: Optional[str] = Query(None, description="Filter by category name"),
    user_id: str = Depends(get_current_user),
):
    """Total spend, top category, and budget utilization for the current month."""
    supabase = _get_admin_supabase()

    today = date.today()
    first_of_month = today.replace(day=1)

    # Use provided dates or fall back to current month
    s_date = start_date or first_of_month
    e_date = end_date or today

    # Resolve category_id if a category filter was provided
    cat_id = None
    if category:
        try:
            cat_res = (
                supabase.table("categories")
                .select("id")
                .eq("name", category)
                .limit(1)
                .execute()
            )
            if cat_res.data:
                cat_id = cat_res.data[0]["id"]
        except Exception:
            pass

    # Primary query: expenses within the date range
    try:
        q = (
            supabase.table("expenses")
            .select("amount, category_id, categories(name)")
            .eq("user_id", user_id)
            .gte("date", s_date.isoformat())
            .lte("date", e_date.isoformat())
        )
        if cat_id is not None:
            q = q.eq("category_id", cat_id)
        res = q.execute()
    except Exception as exc:
        logger.error("Summary query failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to compute spending summary",
        )

    rows = list(res.data or [])

    # Also include expenses with NULL date (just uploaded, OCR not done yet)
    # so the dashboard Total Spend is never 0 after uploading.
    try:
        null_res = (
            supabase.table("expenses")
            .select("amount, category_id, categories(name)")
            .eq("user_id", user_id)
            .is_("date", "null")
            .execute()
        )
        existing_ids = {r.get("id") for r in rows if r.get("id")}
        for r in (null_res.data or []):
            if r.get("id") not in existing_ids:
                rows.append(r)
    except Exception:
        pass

    total_spend = sum(float(r.get("amount", 0)) for r in rows)

    # Determine top category
    cat_totals: dict[str, float] = defaultdict(float)
    for r in rows:
        cat = None
        if r.get("categories") and isinstance(r["categories"], dict):
            cat = r["categories"].get("name")
        if cat:
            cat_totals[cat] += float(r.get("amount", 0))

    top_category = max(cat_totals, key=cat_totals.get, default=None) if cat_totals else None

    budget_util = None
    if budget and budget > 0:
        budget_util = round(total_spend / budget * 100, 2)

    # Average daily spend (divide by days elapsed so far this month)
    days_elapsed = max(today.day, 1)
    average_daily = round(total_spend / days_elapsed, 2)

    # Month-over-month change: compare to same-length window last month
    last_month_end = first_of_month - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)
    try:
        prev_res = (
            supabase.table("expenses")
            .select("amount")
            .eq("user_id", user_id)
            .gte("date", last_month_start.isoformat())
            .lte("date", last_month_end.isoformat())
            .execute()
        )
        prev_spend = sum(float(r.get("amount", 0)) for r in (prev_res.data or []))
    except Exception:
        prev_spend = 0.0

    if prev_spend > 0:
        mom_change = round((total_spend - prev_spend) / prev_spend * 100, 1)
    else:
        mom_change = 0.0

    top_category_amount = round(cat_totals.get(top_category, 0.0), 2) if top_category else 0.0

    return SpendingSummary(
        total_spend=round(total_spend, 2),
        top_category=top_category,
        top_category_amount=top_category_amount,
        budget_utilization=budget_util,
        expense_count=len(rows),
        transaction_count=len(rows),
        average_daily=average_daily,
        month_over_month_change=mom_change,
    )


# ---------------------------------------------------------------------------
# GET /api/analytics/spending-over-time
# ---------------------------------------------------------------------------
@router.get("/spending-over-time", response_model=list[MonthlySpending])
async def spending_over_time(
    months: int = Query(6, ge=1, le=24, description="Number of past months"),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    category: Optional[str] = Query(None),
    user_id: str = Depends(get_current_user),
):
    """Monthly spending totals for the past N months."""
    supabase = _get_admin_supabase()

    today = date.today()
    s_date = start_date or (today.replace(day=1) - timedelta(days=(months - 1) * 30)).replace(day=1)
    e_date = end_date or today

    # Resolve category_id if filter given
    cat_id = None
    if category:
        try:
            cat_res = (
                supabase.table("categories")
                .select("id")
                .eq("name", category)
                .limit(1)
                .execute()
            )
            if cat_res.data:
                cat_id = cat_res.data[0]["id"]
            else:
                return _empty_months(s_date, e_date)
        except Exception:
            pass

    try:
        q = (
            supabase.table("expenses")
            .select("amount, date")
            .eq("user_id", user_id)
            .gte("date", s_date.isoformat())
            .lte("date", e_date.isoformat())
        )
        if cat_id is not None:
            q = q.eq("category_id", cat_id)
        res = q.execute()
    except Exception as exc:
        logger.error("Spending-over-time query failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to compute spending over time",
        )

    monthly: dict[str, float] = defaultdict(float)
    for r in res.data or []:
        if r.get("date"):
            month_key = r["date"][:7]  # "YYYY-MM"
            monthly[month_key] += float(r.get("amount", 0))

    # Fill in missing months with zero
    result: list[MonthlySpending] = []
    cursor = s_date
    while cursor <= e_date:
        key = cursor.strftime("%Y-%m")
        result.append(MonthlySpending(month=key, total=round(monthly.get(key, 0), 2)))
        if cursor.month == 12:
            cursor = cursor.replace(year=cursor.year + 1, month=1)
        else:
            cursor = cursor.replace(month=cursor.month + 1)

    return result


def _empty_months(s_date: date, e_date: date) -> list[MonthlySpending]:
    """Return zeroed MonthlySpending entries for a date range."""
    result = []
    cursor = s_date
    while cursor <= e_date:
        result.append(MonthlySpending(month=cursor.strftime("%Y-%m"), total=0.0))
        if cursor.month == 12:
            cursor = cursor.replace(year=cursor.year + 1, month=1)
        else:
            cursor = cursor.replace(month=cursor.month + 1)
    return result


# ---------------------------------------------------------------------------
# GET /api/analytics/category-breakdown
# ---------------------------------------------------------------------------
@router.get("/category-breakdown")
async def category_breakdown(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    category: Optional[str] = Query(None),
    user_id: str = Depends(get_current_user),
):
    """Spending by category with amounts and percentages."""
    supabase = _get_admin_supabase()

    today = date.today()
    s_date = start_date or today.replace(day=1)
    e_date = end_date or today

    cat_id = None
    if category:
        try:
            cat_res = (
                supabase.table("categories")
                .select("id")
                .eq("name", category)
                .limit(1)
                .execute()
            )
            if cat_res.data:
                cat_id = cat_res.data[0]["id"]
        except Exception:
            pass

    try:
        q = (
            supabase.table("expenses")
            .select("amount, categories(name)")
            .eq("user_id", user_id)
            .gte("date", s_date.isoformat())
            .lte("date", e_date.isoformat())
        )
        if cat_id is not None:
            q = q.eq("category_id", cat_id)
        res = q.execute()
    except Exception as exc:
        logger.error("Category breakdown query failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to compute category breakdown",
        )

    cat_totals: dict[str, float] = defaultdict(float)
    for r in res.data or []:
        cat = "Other"
        if r.get("categories") and isinstance(r["categories"], dict):
            cat = r["categories"].get("name", "Other")
        cat_totals[cat] += float(r.get("amount", 0))

    grand_total = sum(cat_totals.values())

    breakdown = []
    for cat, total in sorted(cat_totals.items(), key=lambda x: x[1], reverse=True):
        pct = round(total / grand_total * 100, 2) if grand_total > 0 else 0
        breakdown.append(
            {"category": cat, "amount": round(total, 2), "percentage": pct}
        )

    return {"categories": breakdown, "total": round(grand_total, 2)}


# ---------------------------------------------------------------------------
# GET /api/analytics/forecast
# ---------------------------------------------------------------------------
@router.get("/forecast", response_model=list[PredictionResponse])
async def forecast(
    months_ahead: int = Query(3, ge=1, le=12, description="Months to forecast"),
    user_id: str = Depends(get_current_user),
):
    """Simple linear-trend forecast of future monthly spending."""
    supabase = _get_admin_supabase()

    today = date.today()
    history_start = (today.replace(day=1) - timedelta(days=365)).replace(day=1)

    try:
        res = (
            supabase.table("expenses")
            .select("amount, date")
            .eq("user_id", user_id)
            .gte("date", history_start.isoformat())
            .lte("date", today.isoformat())
            .execute()
        )
    except Exception as exc:
        logger.error("Forecast query failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to compute forecast",
        )

    monthly: dict[str, float] = defaultdict(float)
    for r in res.data or []:
        if r.get("date"):
            monthly[r["date"][:7]] += float(r.get("amount", 0))

    if not monthly:
        result = []
        cursor = today
        for _ in range(months_ahead):
            if cursor.month == 12:
                cursor = cursor.replace(year=cursor.year + 1, month=1)
            else:
                cursor = cursor.replace(month=cursor.month + 1)
            result.append(PredictionResponse(
                month=cursor.strftime("%Y-%m"),
                predicted_spend=0.0,
            ))
        return result

    sorted_months = sorted(monthly.keys())
    n = len(sorted_months)
    x_vals = list(range(n))
    y_vals = [monthly[m] for m in sorted_months]

    x_mean = sum(x_vals) / n
    y_mean = sum(y_vals) / n

    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_vals, y_vals))
    denominator = sum((x - x_mean) ** 2 for x in x_vals)
    slope = numerator / denominator if denominator != 0 else 0
    intercept = y_mean - slope * x_mean

    result = []
    last_month_str = sorted_months[-1]
    last_year, last_month_num = int(last_month_str[:4]), int(last_month_str[5:7])
    cursor_date = date(last_year, last_month_num, 1)

    for i in range(1, months_ahead + 1):
        if cursor_date.month == 12:
            cursor_date = cursor_date.replace(year=cursor_date.year + 1, month=1)
        else:
            cursor_date = cursor_date.replace(month=cursor_date.month + 1)

        predicted = max(0.0, intercept + slope * (n - 1 + i))
        result.append(PredictionResponse(
            month=cursor_date.strftime("%Y-%m"),
            predicted_spend=round(predicted, 2),
        ))

    return result