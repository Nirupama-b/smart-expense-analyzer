import type { MonthlySpending, SpendingOverTime } from '@/types';

export function toChartSpending(raw: MonthlySpending[]): SpendingOverTime {
  return {
    labels: raw.map((r) => r.month),
    datasets: [{ label: 'Monthly Spend', data: raw.map((r) => r.total) }],
  };
}
