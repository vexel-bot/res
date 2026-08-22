import createClient, { type Middleware } from 'openapi-fetch';
import { authToken } from '../api';
import type { components, paths } from './schema';

export type BackendSchema<Name extends keyof components['schemas']> = components['schemas'][Name];

export class BackendRequestError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly detail?: unknown,
  ) {
    super(message);
    this.name = 'BackendRequestError';
  }
}

export const backendClient = createClient<paths>({ baseUrl: '' });

const requestContextMiddleware: Middleware = {
  async onRequest({ request }) {
    const token = authToken.get();
    if (token) request.headers.set('Authorization', `Bearer ${token}`);
    request.headers.set('X-Correlation-ID', crypto.randomUUID());
    return request;
  },
  async onResponse({ response }) {
    if (response.status === 401) window.dispatchEvent(new Event('nexus:unauthorized'));
    return response;
  },
};

backendClient.use(requestContextMiddleware);

type BackendResult<T> = {
  data?: T;
  error?: unknown;
  response: Response;
};

function detailMessage(detail: unknown, fallback: string) {
  if (!detail || typeof detail !== 'object') return fallback;
  const candidate = detail as { detail?: unknown; error?: unknown; message?: unknown };
  const value = candidate.detail ?? candidate.error ?? candidate.message;
  return typeof value === 'string' ? value : fallback;
}

export function requireBackendData<T>(result: BackendResult<T>, label: string): T {
  if (result.data !== undefined) return result.data;
  throw new BackendRequestError(
    detailMessage(result.error, `${label} falhou (${result.response.status}).`),
    result.response.status,
    result.error,
  );
}

export function requireBackendSuccess(result: BackendResult<unknown>, label: string) {
  if (result.response.ok) return;
  throw new BackendRequestError(
    detailMessage(result.error, `${label} falhou (${result.response.status}).`),
    result.response.status,
    result.error,
  );
}
