'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { supabase } from '@/lib/supabase';
import { getExpenses, getCategories, getAnalyticsSummary } from '@/lib/api';
import { Expense, Category, AnalyticsSummary } from '@/types';
import Navbar from '@/components/Navbar';
import ReceiptUpload from '@/components/ReceiptUpload';
import ExpenseTable from '@/components/ExpenseTable';
import QuickStats from '@/components/QuickStats';

export default function DashboardPage() {
  const router = useRouter();
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const limit = 10;

  const fetchData = useCallback(async (page: number = 1) => {
    try {
      const [expensesData, categoriesData, summaryData] = await Promise.all([
        getExpenses({ page, limit }),
        getCategories(),
        getAnalyticsSummary(),
      ]);

      setExpenses(expensesData.expenses);
      setTotalPages(Math.ceil(expensesData.total / limit));
      setCategories(categoriesData);
      setSummary(summaryData);
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
