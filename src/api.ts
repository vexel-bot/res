const TOKEN_KEY = 'nexus_access_token';

export class APIError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

export const authToken = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (token: string) => localStorage.setItem(TOKEN_KEY, token),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = authToken.get();
  const headers = new Headers(init.headers);
  if (token) headers.set('Authorization', `Bearer ${token}`);
  if (init.body && !(init.body instanceof FormData)) headers.set('Content-Type', 'application/json');
  headers.set('X-Correlation-ID', crypto.randomUUID());
  const response = await fetch(path, { ...init, headers });
  if (!response.ok) {
    let message = `Erro HTTP ${response.status}`;
    try {
      const body = await response.json();
      message = body.detail || body.error || message;
    } catch {
      // The status remains the authoritative error when the response is not JSON.
    }
    if (response.status === 401) window.dispatchEvent(new Event('nexus:unauthorized'));
    throw new APIError(message, response.status);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export async function apiFetchBlob(path: string): Promise<Blob> {
  const token = authToken.get();
  const headers = new Headers();
  if (token) headers.set('Authorization', `Bearer ${token}`);
  headers.set('X-Correlation-ID', crypto.randomUUID());
  const response = await fetch(path, { headers });
  if (!response.ok) throw new APIError(`Erro HTTP ${response.status}`, response.status);
  return response.blob();
}
