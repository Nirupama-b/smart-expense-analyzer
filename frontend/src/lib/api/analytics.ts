import { request } from './client';
import { toCategoryBreakdown } from '../transformers/categories';
import { toChartSpending } from '../transformers/spending';
import type {
  AnalyticsSummary,
  CategoryBreakdown,
  CategoryBreakdownResponse,
  MonthlySpending,
  Prediction,
  PredictionApiResponse,
  SpendingOverTime,
} from '@/types';

/* eslint-disable @typescript-eslint/no-explicit-any */
// The analytics page passes a single ExpenseFilters object to every
// helper, so all of these accept `any` for forward-compat.

export async function getAnalyticsSummary(params: any = {}) {
  return request<AnalyticsSummary>('/api/analytics/summary', {
    method: 'GET',
    params,
  });
}

export async function getSpendingOverTime(
  params: any = {},
): Promise<SpendingOverTime> {
  const raw = await request<MonthlySpending[]>(
    '/api/analytics/spending-over-time',
    {
      method: 'GET',
      params: typeof params === 'number' ? { months: params } : params,
    },
  );
  return toChartSpending(raw);
}

export async function getCategoryBreakdown(
  params: any = {},
): Promise<CategoryBreakdown> {
  const raw = await request<CategoryBreakdownResponse>(
    '/api/analytics/category-breakdown',
    { method: 'GET', params },
  );
  return toCategoryBreakdown(raw);
}

/**
 * Hits the XGBoost-backed `/api/predictions/me` endpoint.
 *
 * Returns null when the backend reports `cold_start: true` (expenses span
 * fewer than 2 distinct months).
 */
export async function getForecast(): Promise<Prediction | null> {
  const raw = await request<PredictionApiResponse>('/api/predictions/me', {
    method: 'GET',
  });
  if (
    !raw ||
    raw.cold_start ||
    raw.predicted_spend == null ||
    raw.burnout_probability == null
  ) {
    return null;
  }
  return {
    predicted_spend: raw.predicted_spend,
    burnout_probability: raw.burnout_probability,
  };
}

/* eslint-enable @typescript-eslint/no-explicit-any */
