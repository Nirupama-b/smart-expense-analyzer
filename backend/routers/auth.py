import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from supabase import create_client

from config import get_settings, Settings
from middleware.auth import get_current_user
from models.schemas import UserCreate, UserLogin, TokenResponse, UserResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


def _get_supabase(settings: Optional[Settings] = None):
    """Return a Supabase client using the anon key (for auth flows)."""
    s = settings or get_settings()
    return create_client(s.SUPABASE_URL, s.SUPABASE_KEY)


def _get_admin_supabase(settings: Optional[Settings] = None):
    """Return a Supabase client using the service-role key (admin ops)."""
    s = settings or get_settings()
    return create_client(s.SUPABASE_URL, s.SUPABASE_SERVICE_KEY)


# ---------------------------------------------------------------------------
# POST /api/auth/register
# ---------------------------------------------------------------------------
@router.post("/register", response_model=TokenResponse)
async def register(payload: UserCreate):
    """Register a new user via Supabase Auth and return a JWT."""
    settings = get_settings()
    supabase = _get_supabase(settings)

    try:
        res = supabase.auth.sign_up(
            {"email": payload.email, "password": payload.password}
        )
    except Exception as exc:
        logger.error("Supabase sign_up error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    if not res.user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration failed - no user returned",
        )

    session = res.session
    if not session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration succeeded but no session created. Check email confirmation settings.",
        )

    user = UserResponse(
        id=str(res.user.id),
        email=res.user.email or payload.email,
        created_at=getattr(res.user, "created_at", None),
    )

    return TokenResponse(
        access_token=session.access_token,
        expires_in=session.expires_in or 3600,
        user=user,
    )


# ---------------------------------------------------------------------------
# POST /api/auth/login
# ---------------------------------------------------------------------------
@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLogin):
    """Authenticate an existing user and return a JWT."""
    settings = get_settings()
    supabase = _get_supabase(settings)

    try:
        res = supabase.auth.sign_in_with_password(
            {"email": payload.email, "password": payload.password}
        )
    except Exception as exc:
        logger.error("Supabase sign_in error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not res.user or not res.session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    user = UserResponse(
        id=str(res.user.id),
        email=res.user.email or payload.email,
        created_at=getattr(res.user, "created_at", None),
    )

    return TokenResponse(
        access_token=res.session.access_token,
        expires_in=res.session.expires_in or 3600,
        user=user,
    )


# ---------------------------------------------------------------------------
# GET /api/auth/me
# ---------------------------------------------------------------------------
@router.get("/me", response_model=UserResponse)
async def me(user_id: str = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    settings = get_settings()
    admin = _get_admin_supabase(settings)

    try:
        res = admin.auth.admin.get_user_by_id(user_id)
    except Exception as exc:
        logger.error("Failed to look up user %s: %s", user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if not res.user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return UserResponse(
        id=str(res.user.id),
        email=res.user.email or "",
        created_at=getattr(res.user, "created_at", None),
    )
