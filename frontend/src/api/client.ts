/**
 * Typed fetch client for the ReefCommand API.
 *
 * Requests go to the same-origin `/api` path, which Next.js rewrites to the
 * Python backend (see next.config.ts). Same origin means no CORS setup, and one
 * place to change the backend location rather than a base URL sprinkled through
 * feature code.
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
