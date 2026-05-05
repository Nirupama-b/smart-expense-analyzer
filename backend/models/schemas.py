import datetime as _dt
from typing import Any, List, Optional

from pydantic import BaseModel, EmailStr


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    created_at: Optional[_dt.datetime] = None


class TokenResponse(BaseModel):
    access_token: str
    expires_in: int
    user: UserResponse


# ---------------------------------------------------------------------------
# Expenses
# ---------------------------------------------------------------------------

class ExpenseCreate(BaseModel):
    amount: float
    merchant: Optional[str] = None
    category: Optional[str] = None
    date: Optional[_dt.date] = None
    raw_text: Optional[str] = None
    image_path: Optional[str] = None


class ExpenseUpdate(BaseModel):
    amount: Optional[float] = None
    merchant: Optional[str] = None
    category: Optional[str] = None
    date: Optional[_dt.date] = None
    raw_text: Optional[str] = None
    status: Optional[str] = None


class ExpenseResponse(BaseModel):
    id: str
    user_id: str
    amount: float
    merchant: Optional[str] = None
    category: Optional[str] = None
    date: Optional[_dt.date] = None
    raw_text: Optional[str] = None
    image_path: Optional[str] = None
    status: str = "pending"
    created_at: Optional[_dt.datetime] = None


# ---------------------------------------------------------------------------
# Receipt processing
# ---------------------------------------------------------------------------

class ReceiptUploadResponse(BaseModel):
    task_id: str
    status: str
    message: str


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    result: Optional[Any] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Predictions / analytics
# ---------------------------------------------------------------------------

class PredictionResponse(BaseModel):
    month: str
    predicted_spend: float


class CategoryResponse(BaseModel):
    categories: List[str]


class SpendingSummary(BaseModel):
    total_spend: float
    top_category: Optional[str] = None
    budget_utilization: Optional[float] = None
    expense_count: int = 0
    transaction_count: int = 0
    average_daily: float = 0.0
    top_category_amount: float = 0.0
    month_over_month_change: float = 0.0


class MonthlySpending(BaseModel):
    month: str
    total: float


# ---------------------------------------------------------------------------
# Natural language query
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    answer: str
    data: Optional[Any] = None
