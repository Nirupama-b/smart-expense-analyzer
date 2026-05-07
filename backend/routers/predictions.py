"""ML-backed spending forecast endpoints.

Wraps `services.forecasting.ForecastingService` (XGBoost) — the
canonical "after 10 receipts predict next month" path. Mounted at
`/api/predictions` to match every other router under `/api`.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from supabase import create_client

from config import get_settings
from middleware.auth import get_current_user
from services.forecasting import ForecastingService

router = APIRouter(prefix="/predictions", tags=["predictions"])


def _get_admin_supabase():
    settings = get_settings()
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


@router.get("/me", summary="Get this month's spending forecast")
def get_my_prediction(
    budget: Optional[float] = Query(None, description="Override monthly budget for burnout calculation"),
    user_id: str = Depends(get_current_user),
):
    supabase = _get_admin_supabase()
    try:
        return ForecastingService(supabase).get_prediction_for_user(user_id, budget=budget)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Forecasting failed: {str(exc)}",
        )


@router.get("/history", summary="Get all past monthly predictions")
def get_prediction_history(user_id: str = Depends(get_current_user)):
    supabase = _get_admin_supabase()
    try:
        resp = (
            supabase.table("predictions")
            .select("*")
            .eq("user_id", user_id)
            .order("month", desc=True)
            .execute()
        )
        return {"predictions": resp.data or []}
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not fetch history: {str(exc)}",
        )
