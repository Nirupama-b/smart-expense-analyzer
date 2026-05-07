# Smart Expense Analyzer — Frontend

Next.js 14 (App Router) single-page application for the Smart Expense Analyzer.

## Structure

```
frontend/src/
├── app/                     # Next.js pages (each folder = route)
│   ├── page.tsx             # Landing page (/)
│   ├── login/page.tsx       # Login form (/login)
│   ├── register/page.tsx    # Registration form (/register)
│   ├── dashboard/page.tsx   # Main dashboard (/dashboard) — budget, upload, expenses
│   ├── analytics/page.tsx   # Analytics page (/analytics) — charts, filters
│   ├── query/page.tsx       # AI query chat interface (/query)
│   └── settings/page.tsx    # Profile, password, CSV export (/settings)
├── components/
│   ├── Navbar.tsx           # Collapsible left sidebar navigation
│   ├── ReceiptUpload.tsx    # Drag-and-drop upload + real-time Celery status polling
│   ├── ExpenseTable.tsx     # Paginated expense list with inline editing
│   ├── QuickStats.tsx       # Stat cards: total spend, top category, budget utilization
│   ├── SpendingChart.tsx    # Chart.js line chart — spending over time
│   ├── CategoryPieChart.tsx # Chart.js doughnut — spend by category
│   └── ForecastGauge.tsx    # XGBoost prediction card with burnout probability
├── lib/
│   ├── api/
│   │   ├── client.ts        # Axios wrapper: auto-attaches Supabase JWT to every request
│   │   ├── analytics.ts     # getAnalyticsSummary, getSpendingOverTime, getCategoryBreakdown, getForecast
│   │   ├── expenses.ts      # getExpenses, updateExpense, deleteExpense, getCategories
│   │   ├── receipts.ts      # uploadReceipt, getTaskStatus
│   │   └── query.ts         # submitQuery
│   ├── supabase.ts          # Supabase JS client (anon key, browser-side)
│   └── transformers/        # Wire-type → UI-type converters
└── types/
    ├── api.ts               # Wire types — mirrors FastAPI Pydantic schemas exactly
    └── ui.ts                # UI-only types consumed by components
```

## Prerequisites

- Node.js 18+
- The backend server running on `http://localhost:8000`

## Setup

```bash
# From the frontend/ directory:
npm install
```

No `.env` file is required for local development — the API URL defaults to
`http://localhost:8000`. To override it, create `frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Running the development server

```bash
npm run dev
# Opens at http://localhost:3000
# If port 3000 is occupied, Next.js will try 3001.
# Make sure backend/.env CORS_ORIGINS includes whichever port is used.
```

## Other scripts

```bash
npm run build    # Production build
npm run start    # Serve the production build
npm run lint     # ESLint check
```

## Key design decisions

- **Auth flow**: All pages (except `/`, `/login`, `/register`) check for a live Supabase
  session on mount. If no session exists the user is redirected to `/login`.
- **JWT attachment**: `lib/api/client.ts` calls `supabase.auth.getSession()` before every
  request and injects the `access_token` as a `Bearer` header. No manual token management
  is needed in page components.
- **Budget persistence**: The monthly budget is stored in `localStorage` under the key
  `monthly_budget` so it survives page refreshes without requiring a server-side field.
  `fetchData` reads from localStorage on every call to avoid stale closure issues.
- **Real-time status**: `ReceiptUpload` polls `GET /api/receipts/status/{task_id}` every
  2 seconds after upload. An `abortRef` flag prevents state updates on unmounted components.
- **Category filter and pie chart**: When a category filter is applied, it is intentionally
  excluded from the `getCategoryBreakdown` call so the doughnut chart always shows the full
  category split for the selected date range, rather than a single-slice chart.
