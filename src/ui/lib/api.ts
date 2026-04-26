/**
 * API Client for Adaptive Academic Advisor
 * Handles communication between Next.js frontend and FastAPI backend.
 * Includes X-User-Id header for session management (when available).
 */

import { getSessionId } from '@/hooks/use-session'

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "https://a20-app-070-production.up.railway.app/api";

export async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${BASE_URL}${endpoint}`;
  const sessionId = getSessionId();
  
  // Build headers - only add X-User-Id if sessionId exists
  const headers: HeadersInit = {
    ...options.headers,
  };
  
  if (sessionId) {
    headers['X-User-Id'] = sessionId;
  }
  
  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `API request failed: ${response.status}`);
  }

  return response.json();
}

export const api = {
  get: <T>(endpoint: string, options?: RequestInit) =>
    apiRequest<T>(endpoint, { ...options, method: "GET" }),
    
  post: <T>(endpoint: string, data: any, options?: RequestInit) => {
    const isFormData = data instanceof FormData;
    return apiRequest<T>(endpoint, {
      ...options,
      method: "POST",
      headers: {
        ...(isFormData ? {} : { "Content-Type": "application/json" }),
        ...options?.headers,
      },
      body: isFormData ? data : JSON.stringify(data),
    });
  },
};
