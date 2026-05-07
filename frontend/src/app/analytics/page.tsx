'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { supabase } from '@/lib/supabase';
import {
  getAnalyticsSummary,
  getSpendingOverTime,
  getCategoryBreakdown,
  getForecast,
  getCategories,
} from '@/lib/api';
import {
  AnalyticsSummary,
  SpendingOverTime,
  CategoryBreakdown,
  Prediction,
  Category,
  ExpenseFilters,
} from '@/types';
import Navbar from '@/components/Navbar';
import SpendingChart from '@/components/SpendingChart';
import CategoryPieChart from '@/components/CategoryPieChart';
import ForecastGauge from '@/components/ForecastGauge';

export default function AnalyticsPage() {
  const router = useRouter();
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [spendingData, setSpendingData] = useState<SpendingOverTime | null>(null);
  const [categoryData, setCategoryData] = useState<CategoryBreakdown | null>(null);
  const [forecast, setForecast] = useState<Prediction | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);

  // Filter state
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');

  const fetchData = useCallback(async (filters: ExpenseFilters = {}) => {
    setLoading(true);
    try {
      const params: ExpenseFilters = { ...filters };
      if (params.start_date === '') delete params.start_date;
      if (params.end_date === '') delete params.end_date;
      if (params.category === '') delete params.category;

      const storedBudget = parseFloat(localStorage.getItem('monthly_budget') || '0') || 0;

      // Summary gets budget; category-breakdown gets dates only (not category,
      // so the pie always shows the full split for the selected date range)
      const summaryParams = storedBudget > 0 ? { ...params, budget: storedBudget } : params;
      const breakdownParams: ExpenseFilters = { start_date: params.start_date, end_date: params.end_date };

      const [summaryData, spendingResult, categoryResult, forecastResult, categoriesResult] =
        await Promise.all([
          getAnalyticsSummary(summaryParams),
          getSpendingOverTime(params),
          getCategoryBreakdown(breakdownParams),
          getForecast(storedBudget > 0 ? storedBudget : undefined).catch(() => null),
          getCategories(),
        ]);

      setSummary(summaryData);
      setSpendingData(spendingResult);
      setCategoryData(categoryResult);
      setForecast(forecastResult);
      setCategories(categoriesResult);
    } catch (err) {
      console.error('Failed to fetch analytics data:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  // Auth check
  useEffect(() => {
    const checkAuth = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        router.push('/login');
        return;
      }
      fetchData();
    };
    checkAuth();
  }, [router, fetchData]);

  const handleApplyFilters = () => {
    fetchData({
      start_date: startDate,
      end_date: endDate,
      category: selectedCategory,
    });
  };

  // BUG FIX: handleClearFilters fetches data directly with empty params
  // instead of calling fetchData() which would have a stale closure over filter state
  const handleClearFilters = () => {
    setStartDate('');
    setEndDate('');
    setSelectedCategory('');
    fetchData({
      start_date: '',
      end_date: '',
      category: '',
    });
  };

  return (
    <div className="flex min-h-screen">
      <Navbar />
      <main className="flex-1 ml-64 p-8">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-white">Analytics</h1>
            <p className="text-slate-400 mt-1">Insights into your spending patterns</p>
          </div>

          {/* Filter Toolbar */}
          <div className="glass-card p-4 mb-8">
            <div className="flex flex-wrap items-center gap-4">
              <div className="flex items-center gap-2">
                <label className="text-sm text-slate-400">From:</label>
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-blue-500"
                />
              </div>
              <div className="flex items-center gap-2">
                <label className="text-sm text-slate-400">To:</label>
                <input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-blue-500"
                />
              </div>
              <div className="flex items-center gap-2">
                <label className="text-sm text-slate-400">Category:</label>
                <select
                  value={selectedCategory}
                  onChange={(e) => setSelectedCategory(e.target.value)}
                  className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-blue-500"
                >
                  <option value="">All Categories</option>
                  {categories.map((cat) => (
                    <option key={cat.id} value={cat.name}>
                      {cat.name}
                    </option>
                  ))}
                </select>
              </div>
              <button
                onClick={handleApplyFilters}
                className="px-4 py-1.5 bg-blue-500 hover:bg-blue-600 text-white text-sm rounded-lg transition-colors"
              >
                Apply
              </button>
              <button
                onClick={handleClearFilters}
                className="px-4 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm rounded-lg border border-slate-700 transition-colors"
              >
                Clear
              </button>
            </div>
          </div>

          {/* Quick Insights */}
          {summary && (
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
              <div className="glass-card p-4">
                <p className="text-xs text-slate-400 mb-1">Total Spend</p>
                <p className="text-xl font-bold text-white">${summary.total_spend.toFixed(2)}</p>
              </div>
              <div className="glass-card p-4">
                <p className="text-xs text-slate-400 mb-1">Daily Average</p>
                <p className="text-xl font-bold text-white">${summary.average_daily.toFixed(2)}</p>
              </div>
              <div className="glass-card p-4">
                <p className="text-xs text-slate-400 mb-1">Transactions</p>
                <p className="text-xl font-bold text-white">{summary.transaction_count}</p>
              </div>
              <div className="glass-card p-4">
                <p className="text-xs text-slate-400 mb-1">Month-over-Month</p>
                <p
                  className={`text-xl font-bold ${
                    summary.month_over_month_change >= 0 ? 'text-red-400' : 'text-green-400'
                  }`}
                >
                  {summary.month_over_month_change >= 0 ? '+' : ''}
                  {summary.month_over_month_change.toFixed(1)}%
                </p>
              </div>
            </div>
          )}

          {/* Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
            <SpendingChart data={spendingData} loading={loading} />
            <CategoryPieChart data={categoryData} loading={loading} />
          </div>

          {/* Forecast */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <ForecastGauge forecast={forecast} loading={loading} />

            {/* Additional Insights */}
            <div className="glass-card p-6">
              <h3 className="text-lg font-semibold text-white mb-4">Quick Insights</h3>
              <div className="space-y-4">
                {summary && (
                  <>
                    <div className="flex items-start gap-3 p-3 rounded-lg bg-slate-800/30">
                      <div className="w-8 h-8 rounded-full bg-blue-500/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                        <svg className="w-4 h-4 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                        </svg>
                      </div>
                      <div>
                        <p className="text-sm text-white font-medium">Top Spending Category</p>
                        <p className="text-xs text-slate-400 mt-0.5">
                          {summary.top_category ?? 'N/A'} accounts for ${(summary.top_category_amount ?? 0).toFixed(2)} of your spending
                        </p>
                      </div>
                    </div>
                    <div className="flex items-start gap-3 p-3 rounded-lg bg-slate-800/30">
                      <div className="w-8 h-8 rounded-full bg-purple-500/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                        <svg className="w-4 h-4 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                      </div>
                      <div>
                        <p className="text-sm text-white font-medium">Daily Average</p>
                        <p className="text-xs text-slate-400 mt-0.5">
                          You spend an average of ${summary.average_daily.toFixed(2)} per day
                        </p>
                      </div>
                    </div>
                    <div className="flex items-start gap-3 p-3 rounded-lg bg-slate-800/30">
                      <div className="w-8 h-8 rounded-full bg-green-500/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                        <svg className="w-4 h-4 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                      </div>
                      <div>
                        <p className="text-sm text-white font-medium">Budget Status</p>
                        <p className="text-xs text-slate-400 mt-0.5">
                          {summary.budget_utilization != null
                            ? `You've used ${summary.budget_utilization.toFixed(0)}% of your monthly budget`
                            : 'Set a budget in the Dashboard to track utilization'}
                        </p>
                      </div>
                    </div>
                  </>
                )}
                {!summary && !loading && (
                  <p className="text-sm text-slate-500 text-center py-4">
                    No insights available yet. Start adding expenses to see insights.
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
