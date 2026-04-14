'use client';

import { Prediction } from '@/types';

interface ForecastGaugeProps {
  forecast: Prediction | null;
  loading?: boolean;
}

export default function ForecastGauge({ forecast, loading }: ForecastGaugeProps) {
  if (loading) {
    return (
      <div className="glass-card p-6">
        <div className="h-4 bg-slate-800 rounded w-40 mb-6 animate-pulse" />
        <div className="h-48 bg-slate-800/50 rounded animate-pulse" />
      </div>
    );
  }

  if (!forecast) {
    return (
      <div className="glass-card p-6">
        <h3 className="text-lg font-semibold text-white mb-4">Spending Forecast</h3>
        <div className="h-48 flex flex-col items-center justify-center">
          <div className="w-16 h-16 rounded-full bg-slate-800 flex items-center justify-center mb-4">
            <svg className="w-8 h-8 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <p className="text-slate-400 font-medium">Need More Data</p>
          <p className="text-slate-500 text-sm mt-1">Upload more receipts to see forecasts</p>
        </div>
      </div>
    );
  }

  const burnoutProbability = forecast.burnout_probability * 100;
  const burnoutColor =
    burnoutProbability > 70
      ? 'bg-red-500'
      : burnoutProbability > 40
      ? 'bg-yellow-500'
      : 'bg-green-500';
  const burnoutTextColor =
    burnoutProbability > 70
      ? 'text-red-400'
      : burnoutProbability > 40
      ? 'text-yellow-400'
      : 'text-green-400';

  return (
    <div className="glass-card p-6">
      <h3 className="text-lg font-semibold text-white mb-6">Spending Forecast</h3>

      {/* Predicted Spend */}
      <div className="text-center mb-6">
        <p className="text-sm text-slate-400 mb-1">Predicted Monthly Spend</p>
        <p className="text-3xl font-bold text-gradient">
          ${forecast.predicted_spend.toFixed(2)}
        </p>
        <p className="text-xs text-slate-500 mt-1">
          Range: ${forecast.confidence_interval.lower.toFixed(2)} - $
          {forecast.confidence_interval.upper.toFixed(2)}
        </p>
      </div>

      {/* Burnout Probability */}
      <div className="mb-4">
        <div className="flex items-center justify-between mb-2">
          <p className="text-sm text-slate-400">Budget Burnout Risk</p>
          <p className={`text-sm font-medium ${burnoutTextColor}`}>
            {burnoutProbability.toFixed(0)}%
          </p>
        </div>
        <div className="w-full bg-slate-800 rounded-full h-3">
          <div
            className={`${burnoutColor} h-3 rounded-full transition-all duration-700`}
            style={{ width: `${Math.min(burnoutProbability, 100)}%` }}
          />
        </div>
      </div>

      {/* Days until exceeded */}
      {forecast.days_until_budget_exceeded !== undefined && (
        <div className="mt-4 p-3 rounded-lg bg-slate-800/50 border border-slate-700">
          <div className="flex items-center gap-2">
            <svg className="w-4 h-4 text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
            <p className="text-sm text-slate-300">
              Budget may be exceeded in{' '}
              <span className="font-medium text-yellow-400">
                {forecast.days_until_budget_exceeded} days
              </span>
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
