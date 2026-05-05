import type {
  CategoryBreakdown,
  CategoryBreakdownResponse,
} from '@/types';

export function toCategoryBreakdown(
  raw: CategoryBreakdownResponse,
): CategoryBreakdown {
  return {
    categories: raw.categories.map((c) => c.category),
    amounts: raw.categories.map((c) => c.amount),
    percentages: raw.categories.map((c) => c.percentage),
    colors: [],
  };
}
