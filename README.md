# AI-Powered Smart Expense & Receipt Analyzer

**Course:** CS 520: Theory and Practice of Software Engineering (Spring 2026)  
**University:** University of Massachusetts Amherst  

### Team Members
* Dhevdharsan Bhavani Satish Kumar 
* Harshit Katragadda 
* Nirupama Balasubramanian 
* Daniel Kennedy

---

## 📖 Project Overview

**The Problem:** Traditional expense trackers rely heavily on tedious manual data entry or synchronous optical character recognition (OCR). Synchronous OCR blocks server threads, leading to poor performance and a frustrating user experience. Additionally, most standard financial applications only offer historical data without providing proactive insights. 

**The Solution:** We are architecting a full-stack web application that completely automates the extraction, categorization, and predictive forecasting of financial data from unstructured receipt images. By implementing an event-driven, asynchronous data ingestion pipeline and utilizing local machine learning for classification, the system provides a seamless, non-blocking user experience. 

**Community Impact:** This financial tool is specifically designed to serve the Five College community. It provides students, student organizations, and faculty with an efficient, automated way to track limited budgets, manage project funds, or monitor personal daily expenses (such as dining and groceries) without the friction of manual entry.

## ✨ Core Features

* **Responsive Client Interface:** Upload unstructured receipt images (JPEG/PNG/WebP/HEIC) and view real-time processing status via Supabase Realtime.
* **Asynchronous Data Ingestion:** The API gateway returns HTTP 202 immediately; OCR and NLP computation are offloaded to a Celery/Redis worker so the main server thread is never blocked.
* **Receipt OCR Pipeline:** Tesseract (pytesseract) extracts text after Pillow preprocessing (grayscale → 1.5× contrast → sharpen). Merchant, amount, and date are parsed from the raw text using regex heuristics.
* **Semantic Data Categorization:** `facebook/bart-large-mnli` zero-shot classifier automatically assigns one of 10 expense categories (Groceries, Dining, Transport, etc.). Users can correct the category inline.
* **Predictive Analytics:** XGBoost model trained on lag features (lag_1/2/3, rolling_3, month_num) forecasts next-month spend and computes a burnout probability via sigmoid function.
* **Analytics Dashboard:** Chart.js line chart (spending over time) and doughnut chart (category breakdown). Date-range and category filters apply to all visualizations simultaneously.
* **Monthly Budget Tracking:** Users set a budget in the dashboard; utilization percentage and burnout probability update across the entire application.
* **Natural Language Query:** Chat interface answers questions about totals, breakdowns, averages, and recent transactions via a rule-based engine with a LangChain/DistilGPT-2 fallback.

## 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14 (App Router), React 18, TypeScript, Tailwind CSS, Chart.js / react-chartjs-2, react-dropzone, axios |
| Backend | Python, FastAPI, Uvicorn |
| Database / Auth | Supabase (managed PostgreSQL), Row-Level Security, Supabase Realtime |
| Task Queue | Celery + Redis |
| OCR | Tesseract via pytesseract; Pillow (grayscale, contrast, sharpen preprocessing) |
| NLP Categorization | Hugging Face Transformers — `facebook/bart-large-mnli` (zero-shot classification) |
| Forecasting | XGBoost, scikit-learn, pandas, numpy |
| Query Agent | LangChain, DistilGPT-2 (best-effort NL fallback) |
| Auth Middleware | python-jose (JWT), httpx (JWKS fetching with 1-hour TTL cache) |

## 🚀 Build & Run Instructions

### Prerequisites

| Tool | Version | Install (macOS) |
|---|---|---|
| Python | 3.10+ | `brew install python` |
| Node.js | 18+ | `brew install node` |
| Redis | any | `brew install redis && redis-server` |
| Tesseract | any | `brew install tesseract` |
| Supabase project | — | Sign up at [supabase.com](https://supabase.com) |

### Step 1 — Clone the repository

```bash
git clone https://github.com/Nirupama-b/smart-expense-analyzer.git
cd smart-expense-analyzer
```

### Step 2 — Apply database migrations

In your Supabase project dashboard, open the **SQL Editor** and run the following
files in order:

1. `migrations/001_initial_schema.sql` — creates all tables, RLS policies, indexes, triggers, and seeds the 10 categories
2. `migrations/002_auto_create_user_profile.sql` — adds trigger to auto-create a `public.users` row on sign-up

### Step 3 — Configure the backend

```bash
cd backend
cp .env.example .env
```

Open `backend/.env` and fill in:
- `SUPABASE_URL` — your project URL (e.g. `https://xyzabc.supabase.co`)
- `SUPABASE_KEY` — anon/public key (from Supabase → Settings → API)
- `SUPABASE_SERVICE_KEY` — service-role key (keep secret)
- `JWT_SECRET` — JWT secret (from Supabase → Settings → API → JWT Secret)

### Step 4 — Install backend dependencies and start the server

```bash
# From backend/
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

API docs are available at **http://localhost:8000/docs**

### Step 5 — Start the Celery worker (separate terminal)

```bash
# From backend/ with the venv active
OMP_NUM_THREADS=1 celery -A tasks.celery_app worker --pool=solo --loglevel=info
```

> **Why `--pool=solo` and `OMP_NUM_THREADS=1`?**
> PyTorch and Tesseract are not fork-safe on macOS arm64. The solo pool runs tasks
> in the main process (no forking), and setting `OMP_NUM_THREADS=1` prevents
> OpenMP from spawning threads that conflict with the event loop.

### Step 6 — Install frontend dependencies and start the dev server

```bash
cd ../frontend
npm install
npm run dev          # opens at http://localhost:3000
```

> If port 3000 is already in use, Next.js will use 3001. If that happens, make sure
> `backend/.env` includes `http://localhost:3001` in `CORS_ORIGINS`.

---

## 🧪 Running Tests

```bash
cd backend
source .venv/bin/activate
pytest tests/ -v
```

The test suite has 31 tests across three files and completes in under 2 seconds:
- `test_ocr_service.py` — 12 unit tests for OCR field extraction (no image I/O)
- `test_forecasting.py` — 12 unit tests for XGBoost forecasting service (mocked Supabase)
- `test_analytics_forecast.py` — 7 integration tests for analytics endpoints (mocked Supabase)

---

## 📁 Repository Layout

```
smart-expense-analyzer/
├── backend/          # FastAPI app, Celery worker, OCR/NLP/ML services
│   └── README.md     # Backend-specific setup and architecture notes
├── frontend/         # Next.js 14 app (React, TypeScript, Tailwind CSS)
│   └── README.md     # Frontend-specific setup and component guide
├── migrations/       # Supabase SQL migration files (run in order)
├── docs/             # Sprint reports and design notes
└── README.md         # This file
```

---
*See `docs/` for sprint reports and design notes.*
