'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { supabase } from '@/lib/supabase';
import { getExpenses, getCategories, getAnalyticsSummary, getForecast } from '@/lib/api';
import { Expense, Category, AnalyticsSummary, Prediction } from '@/types';
import Navbar from '@/components/Navbar';
import ReceiptUpload from '@/components/ReceiptUpload';
import ExpenseTable from '@/components/ExpenseTable';
import QuickStats from '@/components/QuickStats';

export default function DashboardPage() {
  const router = useRouter();
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);

  // undefined = not yet fetched, null = cold start (insufficient data)
  const [forecast, setForecast] = useState<Prediction | null | undefined>(undefined);

  const [loading, setLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const limit = 10;

  // Budget state
  const [budget, setBudget] = useState(0);
  const [budgetInput, setBudgetInput] = useState('');
  const [editingBudget, setEditingBudget] = useState(false);

  const fetchData = useCallback(async (page: number = 1) => {
    try {
      // Read current budget from localStorage each time so realtime
      // subscription and other callers always see the latest value.
      const storedBudget = parseFloat(localStorage.getItem('monthly_budget') || '0') || 0;

      const [expensesData, categoriesData, summaryData] = await Promise.all([
        getExpenses({ page, limit }),
        getCategories(),
        getAnalyticsSummary(storedBudget > 0 ? { budget: storedBudget } : {}),
      ]);

      setExpenses(expensesData.expenses);
      setTotalPages(Math.ceil(expensesData.total / limit));
      setCategories(categoriesData);
      setSummary(summaryData);

      try {
        const predictionData = await getForecast(storedBudget > 0 ? storedBudget : undefined);
        setForecast(predictionData);
      } catch (predErr) {
        console.error('Forecast failed to load:', predErr);
        setForecast(null);
      }
    } catch (err) {
      console.error('Failed to fetch dashboard data:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  // Auth check + load persisted budget
  useEffect(() => {
    const checkAuth = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        router.push('/login');
        return;
      }
      const stored = parseFloat(localStorage.getItem('monthly_budget') || '0') || 0;
      setBudget(stored);
      setBudgetInput(stored > 0 ? stored.toString() : '');
      fetchData(currentPage);
    };
    checkAuth();
  }, [router, fetchData, currentPage]);

  // Supabase realtime subscription
  useEffect(() => {
    const channel = supabase
      .channel('expenses-changes')
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'expenses' },
        () => { fetchData(currentPage); }
      )
      .subscribe();

    return () => { supabase.removeChannel(channel); };
  }, [fetchData, currentPage]);

  const handlePageChange = (page: number) => setCurrentPage(page);
  const handleUpdate = () => fetchData(currentPage);

  // Persists budget to localStorage and re-fetches so QuickStats and ForecastGauge
  // immediately reflect the new budget without requiring a page reload.
  const saveBudget = () => {
    const val = parseFloat(budgetInput);
    if (!isNaN(val) && val > 0) {
      setBudget(val);
      localStorage.setItem('monthly_budget', val.toString());
      setEditingBudget(false);
      fetchData(currentPage);
    } else {
      setEditingBudget(false);
    }
  };

  const clearBudget = () => {
    setBudget(0);
    setBudgetInput('');
    localStorage.removeItem('monthly_budget');
    setEditingBudget(false);
    fetchData(currentPage);
  };

  return (
    <div className="flex min-h-screen">
      <Navbar />
      <main className="flex-1 ml-64 p-8">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="mb-8 flex flex-wrap items-start justify-between gap-4">
            <div>
              <h1 className="text-3xl font-bold text-white">Dashboard</h1>
              <p className="text-slate-400 mt-1">Track and manage your expenses</p>
            </div>

            {/* Budget widget */}
            <div className="glass-card px-4 py-3 flex items-center gap-3">
              {editingBudget ? (
                <>
                  <span className="text-sm text-slate-400 whitespace-nowrap">Monthly Budget: $</span>
                  <input
                    type="number"
                    value={budgetInput}
                    onChange={(e) => setBudgetInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && saveBudget()}
                    className="w-28 bg-slate-800 border border-slate-700 rounded-lg px-3 py-1 text-sm text-white focus:outline-none focus:border-blue-500"
                    placeholder="e.g. 2000"
                    min="0"
                    step="50"
                    autoFocus
                  />
                  <button
                    onClick={saveBudget}
                    className="px-3 py-1 bg-blue-500 hover:bg-blue-600 text-white text-sm rounded-lg transition-colors"
                  >
                    Save
                  </button>
                  <button
                    onClick={() => setEditingBudget(false)}
                    className="px-3 py-1 bg-slate-700 hover:bg-slate-600 text-slate-300 text-sm rounded-lg transition-colors"
                  >
                    Cancel
                  </button>
                </>
              ) : (
                <>
                  <div className="w-7 h-7 rounded-lg bg-emerald-500/10 flex items-center justify-center">
                    <svg className="w-4 h-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z" />
                    </svg>
                  </div>
                  <span className="text-sm text-slate-300 whitespace-nowrap">
                    {budget > 0 ? (
                      <>Monthly Budget: <span className="text-white font-semibold">${budget.toLocaleString('en-US', { minimumFractionDigits: 2 })}</span></>
                    ) : (
                      <span className="text-slate-400">No monthly budget set</span>
                    )}
                  </span>
                  <button
                    onClick={() => setEditingBudget(true)}
                    className="px-3 py-1 bg-slate-700 hover:bg-slate-600 text-slate-300 text-sm rounded-lg border border-slate-600 transition-colors"
                  >
                    {budget > 0 ? 'Edit' : 'Set Budget'}
                  </button>
                  {budget > 0 && (
                    <button
                      onClick={clearBudget}
                      className="text-slate-500 hover:text-slate-300 text-sm transition-colors"
                      title="Clear budget"
                    >
                      ✕
                    </button>
                  )}
                </>
              )}
            </div>
          </div>

          {/* Quick Stats */}
          <div className="mb-8">
            <QuickStats summary={summary} loading={loading} hasBudget={budget > 0} />
          </div>

          {/* Forecast Panel */}
          <div className="mb-8 p-6 bg-slate-800 rounded-lg border border-slate-700">
            <h2 className="text-xl font-semibold text-white mb-4">Spending Forecast</h2>
            {forecast === undefined ? (
              <p className="text-slate-400">Loading forecast...</p>
            ) : !forecast ? (
              <p className="text-slate-400">
                Upload and process more receipts to unlock your forecast.
              </p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-4 bg-slate-700 rounded-md">
                  <p className="text-sm text-slate-400">Predicted Next Month Spend</p>
                  <p className="text-2xl font-bold text-white">
                    ${forecast.predicted_spend.toFixed(2)}
                  </p>
                </div>
                <div className="p-4 bg-slate-700 rounded-md">
                  <p className="text-sm text-slate-400">Budget Burnout Risk</p>
                  {budget > 0 ? (
                    <p
                      className={`text-2xl font-bold ${
                        forecast.burnout_probability > 0.8 ? 'text-red-400' : 'text-emerald-400'
                      }`}
                    >
                      {(forecast.burnout_probability * 100).toFixed(0)}%
                    </p>
                  ) : (
                    <p className="text-sm text-slate-500 mt-1">Set a budget above to see burnout risk</p>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Main Content - 3 panel layout */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Receipt Upload */}
            <div className="lg:col-span-1">
              <ReceiptUpload onUploadComplete={handleUpdate} />
            </div>

            {/* Expense Table */}
            <div className="lg:col-span-2">
              <ExpenseTable
                expenses={expenses}
                categories={categories}
                onUpdate={handleUpdate}
                currentPage={currentPage}
                totalPages={totalPages}
                onPageChange={handlePageChange}
              />
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
