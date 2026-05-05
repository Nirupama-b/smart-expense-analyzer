import { request } from './client';
import type { TaskStatus } from '@/types';

export async function uploadReceipt(file: File) {
  const form = new FormData();
  form.append('file', file);
  return request<{ task_id: string; status: string; message: string }>(
    '/api/receipts/upload',
    {
      method: 'POST',
      data: form,
      headers: { 'Content-Type': 'multipart/form-data' },
    },
  );
}

export async function getTaskStatus(taskId: string) {
  return request<TaskStatus>(`/api/receipts/status/${taskId}`, {
    method: 'GET',
  });
}
