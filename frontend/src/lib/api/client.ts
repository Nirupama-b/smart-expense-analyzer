/**
 * Shared axios client for the FastAPI backend.
 *
 * Attaches the Supabase access token (from getSession) as a Bearer
 * header so the backend's `get_current_user` dependency can
 * authenticate the request.
 */

import axios, { AxiosRequestConfig } from 'axios';
import { supabase } from '../supabase';

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export async function authHeaders(): Promise<Record<string, string>> {
  const {
    data: { session },
  } = await supabase.auth.getSession();
  return session?.access_token
    ? { Authorization: `Bearer ${session.access_token}` }
    : {};
}

export async function request<T>(
  path: string,
  config: AxiosRequestConfig = {},
): Promise<T> {
  const headers = { ...(config.headers ?? {}), ...(await authHeaders()) };
  const res = await axios.request<T>({
    url: `${API_URL}${path}`,
    ...config,
    headers,
  });
  return res.data;
}
