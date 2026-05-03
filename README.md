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

## ✨ Core Features (MVP)

* **Responsive Client Interface:** Upload unstructured receipt images (JPG/PNG) and view real-time processing status.
* **Asynchronous Data Ingestion:** An API gateway that accepts payloads and offloads computation to background queues, ensuring the main web thread is never blocked.
* **Decentralized Worker Nodes:** Background processing using EasyOCR/Tesseract to extract raw text from image tensors.
* **Semantic Data Categorization:** A local NLP pipeline (e.g., Hugging Face BERT) that automatically classifies noisy OCR output into structured financial buckets (e.g., "Food", "Transport").
* **Analytics Dashboard:** Data visualization layer displaying aggregated historical spending metrics.

*Note: Future phases will introduce predictive financial forecasting and an Agentic AI (ReAct) for natural language database querying.*

## 🛠️ Technology Stack

* **Frontend:** Next.js 14 (App Router), React 18, TypeScript, Tailwind CSS, Chart.js / react-chartjs-2, react-dropzone, axios
* **Backend:** FastAPI, Pydantic v2, Celery + Redis (async task queue), Supabase Python client, python-jose (JWT)
* **Infrastructure:** Supabase (Postgres + Auth + Row-Level Security), Redis broker, Docker
* **AI / ML:** EasyOCR (text extraction), Pillow (image preprocessing), Hugging Face Transformers (`facebook/bart-large-mnli` zero-shot categorization), XGBoost (monthly spend forecasting), scikit-learn

## 🚀 Local Setup

### Prerequisites

* Python 3.10+
* Node.js 18+
* Redis (`brew install redis` on macOS, then `redis-server`)
* A Supabase project (URL + anon key + service-role key)

### 1. Clone and configure

```bash
git clone https://github.com/Nirupama-b/smart-expense-analyzer.git
cd smart-expense-analyzer
cp backend/.env.example backend/.env
# Fill in the Supabase keys and JWT secret in backend/.env
```

### 2. Apply database migrations

Run the SQL files under `workers/` against your Supabase project, in order:

1. `001_initial_schema.sql`
2. `002_auto_create_user_profile.sql`

### 3. Start the backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 4. Start the Celery worker (separate terminal)

```bash
cd backend
source .venv/bin/activate
celery -A tasks.celery_app worker --loglevel=info
```

### 5. Start the frontend

```bash
cd frontend
npm install
npm run dev          # http://localhost:3000
```

## 🧪 Running tests

```bash
cd backend
pip install pytest pytest-asyncio
pytest tests/ -v
```

The suite covers OCR field extraction, the analytics forecast/summary
endpoints (with mocked Supabase), and the XGBoost forecasting service.

---
*See `docs/` for sprint reports and design notes.*
