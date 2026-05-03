"""Pytest configuration: set dummy env vars and put `backend/` on sys.path.

The FastAPI config loader requires several Supabase / JWT settings to be
present, which would normally come from a real `.env`. Tests don't need
real values — they mock out Supabase — so we inject placeholders here
before any application module gets imported.
"""

import os
import sys
from pathlib import Path

# --- 1. Ensure imports like `services.ocr_service` and `routers.analytics`
#       resolve when pytest is invoked from the repository root.
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

REPO_ROOT = BACKEND_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# --- 2. Inject dummy values for required settings.
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-anon-key")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test-service-key")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
