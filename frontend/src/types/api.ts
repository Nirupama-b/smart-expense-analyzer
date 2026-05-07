/**
 * Wire-shape types — these match what the FastAPI backend returns
 * over the network. Do not add UI-only fields here. Components
 * should consume the UI-shape types from `./ui` instead, with
 * transformers in `lib/transformers/` mapping wire → UI.
 */

export interface User {
  id: string;
  email: string;
  name?: string;
  created_at: string;
}

export interface Expense {
  id: string;
  user_id: string;
  merchant: string;
  amount: number;
  currency: string;
  category: string;
  date: string;
  receipt_url?: string;
  status: 'pending' | 'processing' | 'processed' | 'verified' | 'error';
  confidence_score?: number;
  created_at: string;
  updated_at: string;
}

export interface ExpenseFilters {
  start_date?: string;
  end_date?: string;
  category?: string;
  min_amount?: number;
  max_amount?: number;
  status?: string;
  page?: number;
  limit?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  budget?: number;
}

export interface MonthlySpending {
  month: string;
  total: number;
}

export interface CategoryBreakdownResponse {
  categories: { category: string; amount: number; percentage: number }[];
  total: number;
}

export interface AnalyticsSummary {
  total_spend: number;
  average_daily: number;
  transaction_count: number;
  top_category?: string | null;
  top_category_amount: number;
  budget_utilization?: number | null;
  month_over_month_change: number;
}

/**
 * Response from `/api/predictions/me`.
 *
 * When `cold_start` is true the user has fewer than the 10 processed
 * receipts the XGBoost model needs, and the numeric fields are null.
 */
export interface PredictionApiResponse {
  cold_start: boolean;
  predicted_spend?: number | null;
  burnout_probability?: number | null;
  budget?: number | null;
  expense_count?: number;
  expenses_needed?: number;
  message?: string;
  month?: string;
  user_id?: string;
  generated_at?: string;
}
