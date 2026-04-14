'use client';

import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import { SpendingOverTime } from '@/types';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

interface SpendingChartProps {
  data: SpendingOverTime | null;
  loading?: boolean;
}

export default function SpendingChart({ data, loading }: SpendingChartProps) {
  if (loading) {
    return (
      <div className="glass-card p-6">
        <div className="h-4 bg-slate-800 rounded w-40 mb-6 animate-pulse" />
        <div className="h-64 bg-slate-800/50 rounded animate-pulse" />
      </div>
    );
  }

  if (!data || !data.labels || data.labels.length === 0) {
    return (
      <div className="glass-card p-6">
        <h3 className="text-lg font-semibold text-white mb-4">Spending Over Time</h3>
        <div className="h-64 flex items-center justify-center text-slate-500">
          No spending data available
        </div>
      </div>
    );
  }

  const chartData = {
    labels: data.labels,
    datasets: data.datasets.map((dataset, index) => ({
      ...dataset,
      borderColor: index === 0 ? 'rgb(59, 130, 246)' : 'rgb(168, 85, 247)',
      backgroundColor: (context: { chart: ChartJS }) => {
        const ctx = context.chart.ctx;
        const gradient = ctx.createLinearGradient(0, 0, 0, 300);
        if (index === 0) {
          gradient.addColorStop(0, 'rgba(59, 130, 246, 0.3)');
          gradient.addColorStop(1, 'rgba(59, 130, 246, 0.0)');
        } else {
          gradient.addColorStop(0, 'rgba(168, 85, 247, 0.3)');
          gradient.addColorStop(1, 'rgba(168, 85, 247, 0.0)');
        }
        return gradient;
      },
      fill: true,
      tension: 0.4,
      pointBackgroundColor: index === 0 ? 'rgb(59, 130, 246)' : 'rgb(168, 85, 247)',
      pointBorderColor: 'transparent',
      pointRadius: 4,
      pointHoverRadius: 6,
    })),
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: data.datasets.length > 1,
        labels: {
          color: 'rgb(148, 163, 184)',
          usePointStyle: true,
          pointStyle: 'circle',
        },
      },
      tooltip: {
        backgroundColor: 'rgb(15, 23, 42)',
        titleColor: 'rgb(255, 255, 255)',
        bodyColor: 'rgb(148, 163, 184)',
        borderColor: 'rgb(51, 65, 85)',
        borderWidth: 1,
        padding: 12,
        displayColors: false,
        callbacks: {
          label: (context: { parsed: { y: number } }) => `$${context.parsed.y.toFixed(2)}`,
        },
      },
    },
    scales: {
      x: {
        grid: {
          color: 'rgba(51, 65, 85, 0.3)',
        },
        ticks: {
          color: 'rgb(148, 163, 184)',
        },
      },
      y: {
        grid: {
          color: 'rgba(51, 65, 85, 0.3)',
        },
        ticks: {
          color: 'rgb(148, 163, 184)',
          callback: (value: number | string) => `$${value}`,
        },
      },
    },
  };

  return (
    <div className="glass-card p-6">
      <h3 className="text-lg font-semibold text-white mb-4">Spending Over Time</h3>
      <div className="h-64">
        <Line data={chartData} options={options} />
      </div>
    </div>
  );
}
