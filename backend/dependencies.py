"""
Shared FastAPI dependencies.

Provides ``get_current_user`` and ``get_supabase_client`` for routers that
live under ``backend.routes`` (as opposed to the older ``backend.routers``
package which imports the middleware directly).

The predictions router expects ``current_user`` as a dict with an ``id``
key, so we wrap the middleware's ``get_current_user`` (which returns the
user_id string) and adapt the shape here.
"""

from fastapi import Depends
from supabase import Client, create_client

from config import get_settings
from middleware.auth import get_current_user as _get_current_user_id


async def get_current_user(user_id: str = Depends(_get_current_user_id)) -> dict:
    """Return the authenticated user as a dict (``{"id": <uuid>}``).

    The underlying middleware dependency returns the raw ``sub`` claim;
    callers in ``backend.routes`` expect a dict to make adding extra
    profile fields later straightforward.
    """
    return {"id": user_id}


def get_supabase_client() -> Client:
    """Return a Supabase admin client built from app settings."""
    settings = get_settings()
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
