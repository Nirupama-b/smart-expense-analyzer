/**
 * UI-shape types — what components and chart libraries actually
 * consume. Built by transformers from the wire shapes in `./api`.
 */

import type { Expense } from './api';

export interface Category {
  id: string;
  name: string;
  color?: string;
  icon?: string;
}

/**
 * UI prop shape for `ForecastGauge`. The XGBoost backend doesn't
 * return a confidence interval, so it's optional — the gauge only
 * renders the "Range" line when it's present.
 */
export interface Prediction {
  predicted_spend: number;
  confidence_interval?: {
    lower: number;
    upper: number;
  };
  burnout_probability: number;
  days_until_budget_exceeded?: number;
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
