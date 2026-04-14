'use client';

import { AnalyticsSummary } from '@/types';

interface QuickStatsProps {
  summary: AnalyticsSummary | null;
  loading?: boolean;
}

export default function QuickStats({ summary, loading }: QuickStatsProps) {
  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="glass-card p-6 animate-pulse">
            <div className="h-4 bg-slate-800 rounded w-24 mb-3" />
            <div className="h-8 bg-slate-800 rounded w-32" />
          </div>
        ))}
      </div>
    );
  }

  const totalSpend = summary?.total_spend ?? 0;
  const topCategory = summary?.top_category ?? 'N/A';
  const topCategoryAmount = summary?.top_category_amount ?? 0;
  const budgetUtilization = summary?.budget_utilization ?? 0;

  const utilizationColor =
    budgetUtilization > 90
      ? 'bg-red-500'
      : budgetUtilization > 70
      ? 'bg-yellow-500'
      : 'bg-green-500';

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {/* Total Spend */}
      <div className="glass-card p-6">
        <div className="flex items-center justify-between mb-2">
          <p className="text-sm text-slate-400">Total Spend</p>
          <div className="w-8 h-8 rounded-lg bg-blue-500/10 flex items-center justify-center">
            <svg className="w-4 h-4 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
        </div>
        <p className="text-2xl font-bold text-white">${totalSpend.toFixed(2)}</p>
        {summary?.month_over_month_change !== undefined && (
          <p
            className={`text-xs mt-1 ${
              summary.month_over_month_change >= 0 ? 'text-red-400' : 'text-green-400'
            }`}
          >
            {summary.month_over_month_change >= 0 ? '+' : ''}
            {summary.month_over_month_change.toFixed(1)}% vs last month
          </p>
        )}
      </div>

      {/* Top Category */}
      <div className="glass-card p-6">
        <div className="flex items-center justify-between mb-2">
          <p className="text-sm text-slate-400">Top Category</p>
          <div className="w-8 h-8 rounded-lg bg-purple-500/10 flex items-center justify-center">
            <svg className="w-4 h-4 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
            </svg>
          </div>
        </div>
        <p className="text-2xl font-bold text-white">{topCategory}</p>
        <p className="text-xs text-slate-400 mt-1">${topCategoryAmount.toFixed(2)} spent</p>
      </div>

      {/* Budget Utilization */}
      <div className="glass-card p-6">
        <div className="flex items-center justify-between mb-2">
          <p className="text-sm text-slate-400">Budget Utilization</p>
          <div className="w-8 h-8 rounded-lg bg-green-500/10 flex items-center justify-center">
            <svg className="w-4 h-4 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </div>
        </div>
        <p className="text-2xl font-bold text-white">{budgetUtilization.toFixed(0)}%</p>
        <div className="mt-2 w-full bg-slate-800 rounded-full h-2">
          <div
            className={`${utilizationColor} h-2 rounded-full transition-all duration-500`}
            style={{ width: `${Math.min(budgetUtilization, 100)}%` }}
          />
        </div>
      </div>
    </div>
  );
}
