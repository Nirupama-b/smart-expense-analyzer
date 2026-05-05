import { request } from './client';
import type { QueryResponse } from '@/types';

export async function queryAI(question: string) {
  return request<QueryResponse>('/api/query/', {
    method: 'POST',
    data: { question },
  });
}
