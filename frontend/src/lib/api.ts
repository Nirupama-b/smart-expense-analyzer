/**
 * Thin axios client for the FastAPI backend.
 *
 * Each call attaches the Supabase access token (from getSession) as a
 * Bearer header so the backend's `get_current_user` dependency can
 * authenticate the request.
 *
 * NOTE: Stub-level wiring — function signatures match the call sites in
 * the existing pages/components. Daniel's `daniel-frontend-integration`
 * branch will refine error handling, response shapes, and add a unified
 * axios interceptor for auth.
 */

import axios, { AxiosRequestConfig } from 'axios';
import { supabase } from './supabase';
import type {
  AnalyticsSummary,
  Category,
  CategoryBreakdown,
  Expense,
  ExpenseFilters,
  Prediction,
  QueryResponse,
  SpendingOverTime,
  TaskStatus,
} from '@/types';

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

async function authHeaders(): Promise<Record<string, string>> {
  const {
    data: { session },
  } = await supabase.auth.getSession();
  return session?.access_token
    ? { Authorization: `Bearer ${session.access_token}` }
    : {};
}

async function request<T>(
  path: string,
  config: AxiosRequestConfig = {},
): Promise<T> {
  const headers = { ...(config.headers ?? {}), ...(await authHeaders()) };
  const res = await axios.request<T>({
    url: `${API_URL}${path}`,
    ...config,
    headers,
  });
  return res.data;
}

// --- Expenses ---------------------------------------------------------------

export async function getExpenses(filters: ExpenseFilters = {}) {
  return request<{ expenses: Expense[]; total: number }>('/api/expenses/', {
    method: 'GET',
    params: filters,
  });
}

export async function updateExpense(id: string, data: Partial<Expense>) {
  return request<Expense>(`/api/expenses/${id}`, {
    method: 'PUT',
    data,
  });
}

export async function deleteExpense(id: string) {
  return request<void>(`/api/expenses/${id}`, { method: 'DELETE' });
}

export async function getCategories() {
  return request<{ categories: string[] }>('/api/expenses/categories', {
    method: 'GET',
  }).then((r) =>
    r.categories.map<Category>((name, i) => ({ id: String(i), name })),
  );
}

// --- Receipts ---------------------------------------------------------------

export async function uploadReceipt(file: File) {
  const form = new FormData();
  form.append('file', file);
  return request<{ task_id: string; status: string; message: string }>(
    '/api/receipts/upload',
    {
      method: 'POST',
      data: form,
      headers: { 'Content-Type': 'multipart/form-data' },
    },
  );
}

export async function getTaskStatus(taskId: string) {
  return request<TaskStatus>(`/api/receipts/status/${taskId}`, {
    method: 'GET',
  });
}

// --- Analytics --------------------------------------------------------------

/* eslint-disable @typescript-eslint/no-explicit-any */
// The analytics page passes a single ExpenseFilters object to every
// helper, so all of these accept `any` for now. Daniel's frontend
// branch will tighten the shapes once the filter contract is settled.

export async function getAnalyticsSummary(params: any = {}) {
  return request<AnalyticsSummary>('/api/analytics/summary', {
    method: 'GET',
    params,
  });
}

export async function getSpendingOverTime(params: any = {}) {
  return request<SpendingOverTime>('/api/analytics/spending-over-time', {
    method: 'GET',
    params: typeof params === 'number' ? { months: params } : params,
  });
}

export async function getCategoryBreakdown(params: any = {}) {
  return request<CategoryBreakdown>('/api/analytics/category-breakdown', {
    method: 'GET',
    params,
  });
}

export async function getForecast(params: any = {}): Promise<any> {
  // Backend returns Prediction[]; the analytics page treats this as a
  // single Prediction. Return type is `any` to satisfy both call sites
  // until Daniel reconciles the shape.
  return request<Prediction[]>('/api/analytics/forecast', {
    method: 'GET',
    params: typeof params === 'number' ? { months_ahead: params } : params,
  });
}
/* eslint-enable @typescript-eslint/no-explicit-any */

// --- Natural-language query ------------------------------------------------

export async function queryAI(question: string) {
  return request<QueryResponse>('/api/query/', {
    method: 'POST',
    data: { question },
  });
}
