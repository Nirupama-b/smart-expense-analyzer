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

  const fetchData = useCallback(async (page: number = 1) => {
    try {
      // 1. Fetch the vital, guaranteed data first
      const [expensesData, categoriesData, summaryData] = await Promise.all([
        getExpenses({ page, limit }),
        getCategories(),
        getAnalyticsSummary(),
      ]);

      setExpenses(expensesData.expenses);
      setTotalPages(Math.ceil(expensesData.total / limit));
      setCategories(categoriesData);
      setSummary(summaryData);
      
      // Fetch forecast separately so a cold-start / model failure doesn't block the page.
      try {
        const predictionData = await getForecast();
        setForecast(predictionData); // null = cold start, Prediction = ready
      } catch (predErr) {
        console.error("Forecast failed to load:", predErr);
        setForecast(null);
      }
      
    } catch (err) {
      console.error('Failed to fetch dashboard data:', err);
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
        {
          event: '*',
          schema: 'public',
          table: 'expenses',
        },
        () => {
          fetchData(currentPage);
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [fetchData, currentPage]);

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };

  const handleUpdate = () => {
    fetchData(currentPage);
  };

  return (
    <div className="flex min-h-screen">
      <Navbar />
      <main className="flex-1 ml-64 p-8">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-white">Dashboard</h1>
            <p className="text-slate-400 mt-1">Track and manage your expenses</p>
          </div>

          {/* Quick Stats */}
          <div className="mb-8">
            <QuickStats summary={summary} loading={loading} />
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
                  <p
                    className={`text-2xl font-bold ${
                      forecast.burnout_probability > 0.8 ? 'text-red-400' : 'text-emerald-400'
                    }`}
                  >
                    {(forecast.burnout_probability * 100).toFixed(0)}%
                  </p>
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