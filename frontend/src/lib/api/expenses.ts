import { request } from './client';
import type { Category, Expense, ExpenseFilters } from '@/types';

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
