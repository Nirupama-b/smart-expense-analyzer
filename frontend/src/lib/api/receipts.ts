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
      // Do NOT set Content-Type manually — axios must auto-set it with the
      // correct multipart boundary, otherwise the backend cannot parse the body.
    },
  );
}

export async function getTaskStatus(taskId: string) {
  return request<TaskStatus>(`/api/receipts/status/${taskId}`, {
    method: 'GET',
  });
}
