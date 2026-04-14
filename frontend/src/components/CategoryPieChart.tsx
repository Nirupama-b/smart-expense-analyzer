'use client';

import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend,
} from 'chart.js';
import { Doughnut } from 'react-chartjs-2';
import { CategoryBreakdown } from '@/types';

ChartJS.register(ArcElement, Tooltip, Legend);

interface CategoryPieChartProps {
  data: CategoryBreakdown | null;
  loading?: boolean;
}

const defaultColors = [
  'rgb(59, 130, 246)',
  'rgb(168, 85, 247)',
  'rgb(34, 197, 94)',
  'rgb(249, 115, 22)',
  'rgb(236, 72, 153)',
  'rgb(14, 165, 233)',
  'rgb(245, 158, 11)',
  'rgb(239, 68, 68)',
  'rgb(99, 102, 241)',
  'rgb(20, 184, 166)',
];

export default function CategoryPieChart({ data, loading }: CategoryPieChartProps) {
  if (loading) {
    return (
      <div className="glass-card p-6">
        <div className="h-4 bg-slate-800 rounded w-40 mb-6 animate-pulse" />
        <div className="h-64 bg-slate-800/50 rounded animate-pulse" />
      </div>
    );
  }

  if (!data || !data.categories || data.categories.length === 0) {
    return (
      <div className="glass-card p-6">
        <h3 className="text-lg font-semibold text-white mb-4">Category Breakdown</h3>
        <div className="h-64 flex items-center justify-center text-slate-500">
          No category data available
        </div>
      </div>
    );
  }

  const colors = data.colors && data.colors.length > 0 ? data.colors : defaultColors;

  const chartData = {
    labels: data.categories,
    datasets: [
      {
        data: data.amounts,
        backgroundColor: colors.map((c) => c.replace('rgb', 'rgba').replace(')', ', 0.8)')),
        borderColor: colors,
        borderWidth: 2,
        hoverOffset: 8,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    cutout: '65%',
    plugins: {
      legend: {
        display: false,
      },
      tooltip: {
        backgroundColor: 'rgb(15, 23, 42)',
        titleColor: 'rgb(255, 255, 255)',
        bodyColor: 'rgb(148, 163, 184)',
        borderColor: 'rgb(51, 65, 85)',
        borderWidth: 1,
        padding: 12,
        callbacks: {
          label: (context: { label: string; parsed: number; dataset: { data: number[] } }) => {
            const total = context.dataset.data.reduce((a: number, b: number) => a + b, 0);
            const percentage = ((context.parsed / total) * 100).toFixed(1);
            return `${context.label}: $${context.parsed.toFixed(2)} (${percentage}%)`;
          },
        },
      },
    },
  };

  return (
    <div className="glass-card p-6">
      <h3 className="text-lg font-semibold text-white mb-4">Category Breakdown</h3>
      <div className="flex items-center gap-8">
        <div className="h-64 w-64 flex-shrink-0">
          <Doughnut data={chartData} options={options} />
        </div>
        <div className="flex-1 space-y-2">
          {data.categories.map((category, index) => (
            <div key={category} className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: colors[index % colors.length] }}
                />
                <span className="text-sm text-slate-300">{category}</span>
              </div>
              <div className="text-right">
                <span className="text-sm font-medium text-white">
                  ${data.amounts[index].toFixed(2)}
                </span>
                <span className="text-xs text-slate-500 ml-2">
                  {data.percentages[index].toFixed(1)}%
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
