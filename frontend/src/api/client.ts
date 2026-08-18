/**
 * Typed fetch client for the ReefCommand API.
 *
 * Requests go to the same-origin `/api` path, which Next.js rewrites to the
 * Python backend (see next.config.ts). Same origin means no CORS setup, and one
 * place to change the backend location rather than a base URL sprinkled through
 * feature code.
 *
 * Response types come from `@/types`, which aliases the schema generated from
 * the backend's OpenAPI document. Nothing here declares a payload shape of its
 * own.
 */

const BASE_URL = '/api';

/** The error body shape documented in docs/api_requirements.md. */
interface ApiErrorBody {
  detail?: unknown;
  code?: unknown;
}

/**
 * A non-2xx response.
 *
 * `detail` carries the backend's human-readable message when it sent one, so a
 * caller can surface the real reason instead of a generic failure. A
 * Coordinator business-rule violation arrives here as a 500, which is the
 * pipeline correctly refusing malformed model output rather than a client
 * mistake.
 */
export class ApiError extends Error {
  readonly status: number;
  readonly detail: string | null;
  readonly code: string | null;

  constructor(
    message: string,
    status: number,
    options: { detail?: string | null; code?: string | null } = {},
  ) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = options.detail ?? null;
    this.code = options.code ?? null;
  }
}

/**
 * Pull `detail` and `code` out of an error response without assuming it is JSON.
 *
 * FastAPI sends a 422 body whose `detail` is an array of validation objects
 * rather than a string, so anything non-string is stringified instead of being
 * dropped or rendered as "[object Object]".
 */
async function readErrorBody(
  response: Response,
): Promise<{ detail: string | null; code: string | null }> {
  let body: ApiErrorBody | null = null;
  try {
    body = (await response.json()) as ApiErrorBody;
  } catch {
    return { detail: null, code: null };
  }
  if (body === null || typeof body !== 'object') {
    return { detail: null, code: null };
  }
  const { detail, code } = body;
  return {
    detail:
      typeof detail === 'string'
        ? detail
        : detail === undefined || detail === null
          ? null
          : JSON.stringify(detail),
    code: typeof code === 'string' ? code : null,
  };
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    method,
    headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  if (!response.ok) {
    const { detail, code } = await readErrorBody(response);
    throw new ApiError(`${method} ${path} failed with ${response.status}`, response.status, {
      detail,
      code,
    });
  }

  return (await response.json()) as T;
}

export function get<T>(path: string): Promise<T> {
  return request<T>('GET', path);
}

export function post<T>(path: string, body?: unknown): Promise<T> {
  return request<T>('POST', path, body);
}

export function patch<T>(path: string, body: unknown): Promise<T> {
  return request<T>('PATCH', path, body);
}
