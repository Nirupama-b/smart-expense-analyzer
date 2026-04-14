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
  status: 'pending' | 'processed' | 'verified' | 'error';
  confidence_score?: number;
  created_at: string;
  updated_at: string;
}

export interface Category {
  id: string;
  name: string;
  color?: string;
  icon?: string;
}

export interface Prediction {
  predicted_spend: number;
  confidence_interval: {
    lower: number;
    upper: number;
  };
  burnout_probability: number;
  days_until_budget_exceeded?: number;
}

export interface TaskStatus {
  task_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress?: number;
  result?: Expense;
  error?: string;
}

export interface QueryResponse {
  answer: string;
  data?: Record<string, unknown>;
  visualization?: string;
}

export interface AnalyticsSummary {
  total_spend: number;
  average_daily: number;
  transaction_count: number;
  top_category: string;
  top_category_amount: number;
  budget_utilization: number;
  month_over_month_change: number;
}

export interface SpendingOverTime {
  labels: string[];
  datasets: {
    label: string;
    data: number[];
  }[];
}

export interface CategoryBreakdown {
  categories: string[];
  amounts: number[];
  percentages: number[];
  colors: string[];
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
}
