import logging
import time
from typing import Optional

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt, jwk
from jose.utils import base64url_decode

from config import get_settings

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)

_JWKS_TTL = 3600.0  # re-fetch public keys at most once per hour
_jwks_cache: dict = {}
_jwks_cache_at: float = 0.0


def _fetch_jwks(supabase_url: str) -> dict:
    """Return the JWKS from Supabase, using a 1-hour in-process cache.

    A bounded TTL ensures that a key rotation is picked up within an hour
    without requiring a server restart (the old lru_cache held keys forever).
    """
    global _jwks_cache, _jwks_cache_at
    now = time.monotonic()
    if _jwks_cache and (now - _jwks_cache_at) < _JWKS_TTL:
        return _jwks_cache
    jwks_url = f"{supabase_url}/auth/v1/.well-known/jwks.json"
    logger.info("Auth: fetching JWKS from %s", jwks_url)
    resp = httpx.get(jwks_url, timeout=10)
    resp.raise_for_status()
    _jwks_cache = resp.json()
    _jwks_cache_at = now
    return _jwks_cache


def _get_signing_key(token: str, supabase_url: str):
    """Extract the correct public key from JWKS based on the token's 'kid' header."""
    jwks = _fetch_jwks(supabase_url)
    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header.get("kid")

    for key_data in jwks.get("keys", []):
        if key_data.get("kid") == kid:
            return key_data

    raise JWTError(f"No matching key found for kid={kid}")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """Validate JWT and return the user_id (``sub`` claim).

    Supports both HS256 (legacy) and ES256 (current Supabase) tokens.
    Raises ``401`` when the token is missing or invalid.
    """
    if credentials is None:
        logger.warning("Auth: no credentials provided in request")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    settings = get_settings()

    try:
        # Check the algorithm in the token header
        unverified_header = jwt.get_unverified_header(token)
        alg = unverified_header.get("alg", "HS256")

        if alg == "ES256":
            # Verify using Supabase JWKS public key
            key_data = _get_signing_key(token, settings.SUPABASE_URL)
            payload = jwt.decode(
                token,
                key_data,
                algorithms=["ES256"],
                options={"verify_aud": False},
            )
        else:
            # Fallback to HS256 with JWT secret
            payload = jwt.decode(
                token,
                settings.JWT_SECRET,
                algorithms=[settings.JWT_ALGORITHM],
                options={"verify_aud": False},
            )

        user_id: Optional[str] = payload.get("sub")
        if user_id is None:
            raise JWTError("Missing 'sub' claim")
        logger.info("Auth: successfully authenticated user %s", user_id)
        return user_id
    except JWTError as exc:
        logger.warning("Auth: JWT validation failed - %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as exc:
        logger.error("Auth: unexpected error - %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )
