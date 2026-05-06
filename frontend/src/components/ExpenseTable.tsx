'use client';

import { useState } from 'react';
import { Expense, Category } from '@/types';
import { updateExpense, deleteExpense } from '@/lib/api';

interface ExpenseTableProps {
  expenses: Expense[];
  categories: Category[];
  onUpdate: () => void;
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

type SortField = 'date' | 'merchant' | 'amount' | 'category' | 'status';

const STATUS_OPTIONS: Expense['status'][] = [
  'pending',
  'processing',
  'processed',
  'verified',
  'error',
];

interface EditValues {
  date: string;
  merchant: string;
  category: string;
  amount: number;
  status: Expense['status'];
}

const inputClass =
  'bg-slate-800 border border-slate-700 rounded px-2 py-1 text-sm text-white focus:outline-none focus:border-blue-500';

export default function ExpenseTable({
  expenses,
  categories,
  onUpdate,
  currentPage,
  totalPages,
  onPageChange,
}: ExpenseTableProps) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValues, setEditValues] = useState<EditValues>({
    date: '',
    merchant: '',
    category: '',
    amount: 0,
    status: 'pending',
  });
  const [saving, setSaving] = useState(false);
  const [sortField, setSortField] = useState<SortField>('date');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('desc');
    }
  };

  const sortedExpenses = [...expenses].sort((a, b) => {
    const modifier = sortOrder === 'asc' ? 1 : -1;
    if (sortField === 'amount') {
      return (a.amount - b.amount) * modifier;
    }
    const aVal = String(a[sortField] ?? '');
    const bVal = String(b[sortField] ?? '');
    return aVal.localeCompare(bVal) * modifier;
  });

  const handleEdit = (expense: Expense) => {
    setEditingId(expense.id);
    setEditValues({
      date: expense.date ?? '',
      merchant: expense.merchant ?? '',
      category: expense.category ?? '',
      amount: expense.amount,
      status: expense.status,
    });
  };

  const handleSave = async (id: string) => {
    setSaving(true);
    try {
      await updateExpense(id, {
        date: editValues.date,
        merchant: editValues.merchant,
        category: editValues.category,
        amount: editValues.amount,
        status: editValues.status,
      });
      setEditingId(null);
      onUpdate();
    } catch (err) {
      console.error('Failed to update expense:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    setEditingId(null);
  };

  const handleKeyDown = (e: React.KeyboardEvent, id: string) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSave(id);
    } else if (e.key === 'Escape') {
      handleCancel();
    }
  };

  const handleDelete = async (id: string) => {
    setDeletingId(id);
    try {
      await deleteExpense(id);
      onUpdate();
    } catch (err) {
      console.error('Failed to delete expense:', err);
    } finally {
      setDeletingId(null);
    }
  };

  const getStatusBadge = (status: string) => {
    const styles: Record<string, string> = {
      pending: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
      processing: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
      processed: 'bg-green-500/10 text-green-400 border-green-500/20',
      verified: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
      error: 'bg-red-500/10 text-red-400 border-red-500/20',
    };
    return (
      <span
        className={`px-2 py-1 rounded-full text-xs font-medium border ${styles[status] ?? styles.pending}`}
      >
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    );
  };

  const SortIcon = ({ field }: { field: SortField }) => (
    <span className="ml-1 inline-block">
      {sortField === field ? (
        sortOrder === 'asc' ? (
          <svg className="w-3 h-3 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
          </svg>
        ) : (
          <svg className="w-3 h-3 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        )
      ) : (
        <svg className="w-3 h-3 inline opacity-30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
        </svg>
      )}
    </span>
  );

  return (
    <div className="glass-card overflow-hidden">
      <div className="p-6 border-b border-slate-800">
        <h2 className="text-lg font-semibold text-white">Recent Expenses</h2>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-slate-800">
              {(
                [
                  { field: 'date' as SortField, label: 'Date' },
                  { field: 'merchant' as SortField, label: 'Merchant' },
                  { field: 'category' as SortField, label: 'Category' },
                  { field: 'amount' as SortField, label: 'Amount' },
                  { field: 'status' as SortField, label: 'Status' },
                ] as const
              ).map(({ field, label }) => (
                <th
                  key={field}
                  onClick={() => handleSort(field)}
                  className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider cursor-pointer hover:text-slate-200 transition-colors"
                >
                  {label}
                  <SortIcon field={field} />
                </th>
              ))}
              <th className="px-6 py-3 text-right text-xs font-medium text-slate-400 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/50">
            {sortedExpenses.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-6 py-12 text-center text-slate-500">
                  No expenses found. Upload a receipt to get started.
                </td>
              </tr>
            ) : (
              sortedExpenses.map((expense) => {
                const isEditing = editingId === expense.id;
                return (
                  <tr key={expense.id} className="hover:bg-slate-800/30 transition-colors">
                    {/* Date */}
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-300">
                      {isEditing ? (
                        <input
                          type="date"
                          value={editValues.date}
                          onChange={(e) =>
                            setEditValues({ ...editValues, date: e.target.value })
                          }
                          onKeyDown={(e) => handleKeyDown(e, expense.id)}
                          className={inputClass}
                        />
                      ) : (
                        new Date(expense.date).toLocaleDateString()
                      )}
                    </td>

                    {/* Merchant */}
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-white font-medium">
                      {isEditing ? (
                        <input
                          type="text"
                          value={editValues.merchant}
                          onChange={(e) =>
                            setEditValues({ ...editValues, merchant: e.target.value })
                          }
                          onKeyDown={(e) => handleKeyDown(e, expense.id)}
                          className={`${inputClass} w-36`}
                        />
                      ) : (
                        expense.merchant
                      )}
                    </td>

                    {/* Category */}
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      {isEditing ? (
                        <select
                          value={editValues.category}
                          onChange={(e) =>
                            setEditValues({ ...editValues, category: e.target.value })
                          }
                          onKeyDown={(e) => handleKeyDown(e, expense.id)}
                          className={inputClass}
                        >
                          {categories.map((cat) => (
                            <option key={cat.id} value={cat.name}>
                              {cat.name}
                            </option>
                          ))}
                        </select>
                      ) : (
                        <span className="text-slate-300">{expense.category}</span>
                      )}
                    </td>

                    {/* Amount */}
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      {isEditing ? (
                        <input
                          type="number"
                          step="0.01"
                          min="0"
                          value={editValues.amount}
                          onChange={(e) =>
                            setEditValues({
                              ...editValues,
                              amount: parseFloat(e.target.value) || 0,
                            })
                          }
                          onKeyDown={(e) => handleKeyDown(e, expense.id)}
                          className={`${inputClass} w-24`}
                        />
                      ) : (
                        <span className="text-white font-medium">
                          ${expense.amount.toFixed(2)}
                        </span>
                      )}
                    </td>

                    {/* Status */}
                    <td className="px-6 py-4 whitespace-nowrap">
                      {isEditing ? (
                        <select
                          value={editValues.status}
                          onChange={(e) =>
                            setEditValues({
                              ...editValues,
                              status: e.target.value as Expense['status'],
                            })
                          }
                          onKeyDown={(e) => handleKeyDown(e, expense.id)}
                          className={inputClass}
                        >
                          {STATUS_OPTIONS.map((s) => (
                            <option key={s} value={s}>
                              {s.charAt(0).toUpperCase() + s.slice(1)}
                            </option>
                          ))}
                        </select>
                      ) : (
                        getStatusBadge(expense.status)
                      )}
                    </td>

                    {/* Actions */}
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm">
                      {isEditing ? (
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => handleSave(expense.id)}
                            disabled={saving}
                            title="Save (Enter)"
                            className="text-green-400 hover:text-green-300 transition-colors disabled:opacity-50"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                            </svg>
                          </button>
                          <button
                            onClick={handleCancel}
                            title="Cancel (Escape)"
                            className="text-slate-400 hover:text-slate-300 transition-colors"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                          </button>
                        </div>
                      ) : (
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => handleEdit(expense)}
                            className="text-slate-400 hover:text-blue-400 transition-colors"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                            </svg>
                          </button>
                          <button
                            onClick={() => handleDelete(expense.id)}
                            disabled={deletingId === expense.id}
                            className="text-slate-400 hover:text-red-400 transition-colors disabled:opacity-50"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="px-6 py-4 border-t border-slate-800 flex items-center justify-between">
          <p className="text-sm text-slate-400">
            Page {currentPage} of {totalPages}
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => onPageChange(currentPage - 1)}
              disabled={currentPage <= 1}
              className="px-3 py-1 rounded bg-slate-800 text-slate-300 text-sm hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Previous
            </button>
            <button
              onClick={() => onPageChange(currentPage + 1)}
              disabled={currentPage >= totalPages}
              className="px-3 py-1 rounded bg-slate-800 text-slate-300 text-sm hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
