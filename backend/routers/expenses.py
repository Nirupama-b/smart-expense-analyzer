import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from supabase import create_client

from config import get_settings
from middleware.auth import get_current_user
from models.schemas import (
    CategoryResponse,
    ExpenseCreate,
    ExpenseResponse,
    ExpenseUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/expenses", tags=["expenses"])

VALID_CATEGORIES = [
    "Groceries",
    "Dining",
    "Transport",
    "Entertainment",
    "Utilities",
    "Healthcare",
    "Shopping",
    "Education",
    "Travel",
    "Rent",
    "Insurance",
    "Subscriptions",
    "Personal Care",
    "Gifts & Donations",
    "Other",
]


def _get_admin_supabase():
    settings = get_settings()
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


def _row_to_expense(row: dict) -> ExpenseResponse:
    """Map a Supabase row (with joined category) to an ExpenseResponse."""
    category_name = None
    if row.get("categories") and isinstance(row["categories"], dict):
        category_name = row["categories"].get("name")
    elif row.get("category"):
        category_name = row["category"]

    return ExpenseResponse(
        id=row["id"],
        user_id=row["user_id"],
        amount=float(row.get("amount", 0)),
        merchant=row.get("merchant"),
        category=category_name,
        date=row.get("date"),
        raw_text=row.get("raw_text"),
        image_path=row.get("image_path"),
        status=row.get("status", "pending"),
        created_at=row.get("created_at"),
    )


def _resolve_category_id(supabase, category_name: str) -> Optional[int]:
    """Look up category_id by name, returns None if not found."""
    try:
        res = (
            supabase.table("categories")
            .select("id")
            .eq("name", category_name)
            .limit(1)
            .execute()
        )
        if res.data:
            return res.data[0]["id"]
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# GET /api/expenses/categories
# ---------------------------------------------------------------------------
@router.get("/categories", response_model=CategoryResponse)
async def list_categories(user_id: str = Depends(get_current_user)):
    """Return the list of valid expense categories."""
    return CategoryResponse(categories=VALID_CATEGORIES)


# ---------------------------------------------------------------------------
# GET /api/expenses
# ---------------------------------------------------------------------------
@router.get("/")
async def list_expenses(
    category: Optional[str] = Query(None, description="Filter by category name"),
    start_date: Optional[date] = Query(None, description="Filter expenses from this date"),
    end_date: Optional[date] = Query(None, description="Filter expenses until this date"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user_id: str = Depends(get_current_user),
):
    """List expenses for the authenticated user with optional filters."""
    supabase = _get_admin_supabase()

    query = (
        supabase.table("expenses")
        .select("*, categories(name)")
        .eq("user_id", user_id)
        .order("date", desc=True)
    )

    if category:
        cat_id = _resolve_category_id(supabase, category)
        if cat_id is not None:
            query = query.eq("category_id", cat_id)
        else:
            return []

    if start_date:
        query = query.gte("date", start_date.isoformat())
    if end_date:
        query = query.lte("date", end_date.isoformat())

    query = query.range(offset, offset + limit - 1)

    try:
        res = query.execute()
    except Exception as exc:
        logger.error("Failed to list expenses: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve expenses",
        )

    expenses = [_row_to_expense(row) for row in res.data]
    return {"expenses": expenses, "total": len(expenses)}


# ---------------------------------------------------------------------------
# GET /api/expenses/{expense_id}
# ---------------------------------------------------------------------------
@router.get("/{expense_id}", response_model=ExpenseResponse)
async def get_expense(
    expense_id: str,
    user_id: str = Depends(get_current_user),
):
    """Retrieve a single expense by ID."""
    supabase = _get_admin_supabase()

    try:
        res = (
            supabase.table("expenses")
            .select("*, categories(name)")
            .eq("id", expense_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.error("Failed to get expense %s: %s", expense_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve expense",
        )

    if not res.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found",
        )

    return _row_to_expense(res.data[0])


# ---------------------------------------------------------------------------
# PUT /api/expenses/{expense_id}
# ---------------------------------------------------------------------------
@router.put("/{expense_id}", response_model=ExpenseResponse)
async def update_expense(
    expense_id: str,
    payload: ExpenseUpdate,
    user_id: str = Depends(get_current_user),
):
    """Partially update an expense."""
    supabase = _get_admin_supabase()

    update_data: dict = {}
    if payload.amount is not None:
        update_data["amount"] = payload.amount
    if payload.merchant is not None:
        update_data["merchant"] = payload.merchant
    if payload.date is not None:
        update_data["date"] = payload.date.isoformat()
    if payload.raw_text is not None:
        update_data["raw_text"] = payload.raw_text
    if payload.status is not None:
        update_data["status"] = payload.status
    if payload.category is not None:
        cat_id = _resolve_category_id(supabase, payload.category)
        if cat_id is not None:
            update_data["category_id"] = cat_id
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown category: {payload.category}",
            )

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )

    try:
        res = (
            supabase.table("expenses")
            .update(update_data)
            .eq("id", expense_id)
            .eq("user_id", user_id)
            .execute()
        )
    except Exception as exc:
        logger.error("Failed to update expense %s: %s", expense_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update expense",
        )

    if not res.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found",
        )

    # Re-fetch with joined category
    fetched = (
        supabase.table("expenses")
        .select("*, categories(name)")
        .eq("id", expense_id)
        .limit(1)
        .execute()
    )

    return _row_to_expense(fetched.data[0])


# ---------------------------------------------------------------------------
# DELETE /api/expenses/{expense_id}
# ---------------------------------------------------------------------------
@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_expense(
    expense_id: str,
    user_id: str = Depends(get_current_user),
):
    """Delete an expense."""
    supabase = _get_admin_supabase()

    try:
        res = (
            supabase.table("expenses")
            .delete()
            .eq("id", expense_id)
            .eq("user_id", user_id)
            .execute()
        )
    except Exception as exc:
        logger.error("Failed to delete expense %s: %s", expense_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete expense",
        )

    if not res.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found",
        )

    return None
