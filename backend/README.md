# Smart Expense Analyzer — Backend

FastAPI application that powers the receipt OCR pipeline, analytics, and ML forecasting.

## Structure

```
backend/
├── main.py                  # FastAPI app factory: CORS, router registration, startup hooks
├── config.py                # Pydantic settings loaded from .env
├── constants/categories.py  # Canonical 10-category taxonomy shared by NLP + API
├── middleware/auth.py        # JWT validation (ES256 via JWKS, HS256 fallback); 1-hour key cache
├── models/schemas.py         # Pydantic request/response models (wire types)
├── routers/
│   ├── auth.py              # POST /api/auth/register|login, GET /api/auth/me
│   ├── receipts.py          # POST /api/receipts/upload (returns 202), GET /api/receipts/status/{id}
│   ├── expenses.py          # CRUD /api/expenses — list, get, update, delete
│   ├── analytics.py         # /api/analytics/summary|spending-over-time|category-breakdown|forecast
│   ├── predictions.py       # GET /api/predictions/me (XGBoost) and /history
│   └── query.py             # POST /api/query — natural-language expense queries
├── services/
│   ├── ocr_service.py       # Tesseract OCR + Pillow preprocessing + regex field extraction
│   ├── nlp_service.py       # facebook/bart-large-mnli zero-shot classifier (lazy singleton)
│   ├── forecasting.py       # XGBoost on lag features; sigmoid burnout probability
│   └── agent_service.py     # LangChain query scaffold
├── tasks/
│   ├── celery_app.py        # Celery app config (Redis broker)
│   └── receipt_tasks.py     # process_receipt orchestrator task (OCR → NLP → Supabase write)
├── tests/                   # pytest suite (31 tests)
├── requirements.txt
└── .env.example             # Copy to .env and fill in credentials
```

## Prerequisites

- Python 3.10+
- Redis running locally (`brew install redis && redis-server` on macOS)
- Tesseract OCR installed (`brew install tesseract` on macOS)
- A Supabase project with the migrations in `../migrations/` applied

## Setup

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment variables
cp .env.example .env
# Edit .env and fill in SUPABASE_URL, SUPABASE_KEY, SUPABASE_SERVICE_KEY, JWT_SECRET
```

## Running the server

```bash
# From the backend/ directory with the venv active:
uvicorn main:app --reload --port 8000
```

Interactive API docs available at http://localhost:8000/docs once running.

## Running the Celery worker

Open a **separate terminal** (same venv):

```bash
# macOS/Linux — OMP_NUM_THREADS=1 and --pool=solo prevent fork-safety issues
# with PyTorch/Tesseract on macOS arm64
OMP_NUM_THREADS=1 celery -A tasks.celery_app worker --pool=solo --loglevel=info
```

## Running tests

```bash
# From backend/ with the venv active:
pytest tests/ -v
```

All 31 tests should pass in under 2 seconds. Tests mock Supabase and do not require
a live database connection.

## Key design decisions

- **Async upload**: `POST /api/receipts/upload` returns HTTP 202 immediately; the OCR
  and NLP pipeline runs inside the Celery worker so the main thread is never blocked.
- **Single orchestrator task**: OCR, NLP, and the Supabase write all happen inside one
  Celery task (`process_receipt`) rather than as chained sub-tasks. Celery chains on the
  `solo` pool deadlock waiting for results that the same worker must produce.
- **JWKS caching**: Public keys are fetched from Supabase and cached in-process for 1 hour.
  A time-based TTL (rather than `lru_cache`) ensures key rotations are picked up without
  restarting the server.
- **CPU-only NLP**: `device=-1` forces the Hugging Face pipeline to CPU, avoiding MPS
  crashes in forked Celery worker processes on macOS.
