from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client
from backend.dependencies import get_current_user, get_supabase_client
from backend.services.forecasting import ForecastingService

router = APIRouter()

@router.get("/me", summary="Get this month's spending forecast")
def get_my_prediction(
    current_user: dict = Depends(get_current_user),
    supabase: Client  = Depends(get_supabase_client),
):
    try:
        return ForecastingService(supabase).get_prediction_for_user(current_user["id"])
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Forecasting failed: {str(exc)}")

@router.get("/history", summary="Get all past monthly predictions")
def get_prediction_history(
    current_user: dict = Depends(get_current_user),
    supabase: Client  = Depends(get_supabase_client),
):
    try:
        resp = (supabase.table("predictions").select("*")
                .eq("user_id", current_user["id"]).order("month", desc=True).execute())
        return {"predictions": resp.data or []}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Could not fetch history: {str(exc)}")
