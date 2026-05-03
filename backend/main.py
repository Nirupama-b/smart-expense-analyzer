import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from routers import auth, receipts, expenses, analytics, query
from backend.routes.predictions import router as predictions_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

API_PREFIX = "/api"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle hook."""
    settings = get_settings()
    upload_dir = settings.UPLOAD_DIR
    os.makedirs(upload_dir, exist_ok=True)
    logger.info("Upload directory ready: %s", upload_dir)
    yield


app = FastAPI(
    title="Smart Expense Analyzer API",
    version="1.0.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers (all mounted under /api)
# ---------------------------------------------------------------------------
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(receipts.router, prefix=API_PREFIX)
app.include_router(expenses.router, prefix=API_PREFIX)
app.include_router(analytics.router, prefix=API_PREFIX)
app.include_router(query.router, prefix=API_PREFIX)
app.include_router(predictions_router, prefix="/predictions", tags=["predictions"])

# ---------------------------------------------------------------------------
# Health check (root level)
# ---------------------------------------------------------------------------
@app.get("/health")
async def health_check():
    return {"status": "healthy"}
