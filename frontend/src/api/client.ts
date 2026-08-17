/**
 * Typed fetch client for the ReefCommand API.
 *
 * Requests go through the Vite dev proxy at /api, so the base URL is configured
 * in one place rather than sprinkled through feature code.
 */

const BASE_URL = '/api';

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export async function get<T>(path: string): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`);
  if (!response.ok) {
    throw new ApiError(`GET ${path} failed`, response.status);
  }
  return (await response.json()) as T;
}

export async function post<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new ApiError(`POST ${path} failed`, response.status);
  }
  return (await response.json()) as T;
}
