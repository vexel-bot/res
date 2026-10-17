const TOKEN_KEY = 'nexus_access_token';
let studioScope: { module: 'create-image' | 'create-video'; clientId: string | null } | undefined;
export function setStudioScope(value: typeof studioScope) { studioScope = value; }
export function studioRequestHeaders(headers = new Headers()) {
  const root = typeof document === 'undefined' ? null : document.querySelector<HTMLElement>('[data-clicko-studio]');
  const renderedModule = root?.dataset.clickoStudio;
  const scope = renderedModule === 'create-image' || renderedModule === 'create-video'
    ? { module: renderedModule, clientId: root?.dataset.clickoStudioClient || null } : studioScope;
  if (scope) {
    headers.set('x-clicko-studio-module', scope.module);
    if (scope.clientId) headers.set('x-clicko-client-id', scope.clientId);
  }
  return headers;
}

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
  const headers = studioRequestHeaders(new Headers(init.headers));
  if (init.body && !(init.body instanceof FormData)) headers.set('Content-Type', 'application/json');
  headers.set('X-Correlation-ID', crypto.randomUUID());
  const response = await fetch(path, { ...init, credentials: 'same-origin', headers });
  if (!response.ok) {
    let message = `Erro HTTP ${response.status}`;
    try {
      const body = await response.json();
      const detail = body.detail || body.error;
      message = typeof detail === "string"
        ? detail
        : typeof detail?.code === "string"
          ? detail.code
          : message;
      if (/craft_runtime|craft_engine.*unavailable|craft_.*not_built/.test(message)) message = 'A produção avançada está indisponível neste ambiente. Seu pedido permanece salvo para continuar quando o serviço estiver pronto.';
    } catch {
      // The status remains the authoritative error when the response is not JSON.
    }
    if (response.status === 401) window.dispatchEvent(new Event('nexus:unauthorized'));
    throw new APIError(message, response.status);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export async function apiFetchBlob(path: string, signal?: AbortSignal): Promise<Blob> {
  const headers = studioRequestHeaders();
  headers.set('X-Correlation-ID', crypto.randomUUID());
  const response = await fetch(path, { headers, signal, credentials: 'same-origin' });
  if (!response.ok) throw new APIError(`Erro HTTP ${response.status}`, response.status);
  return response.blob();
}
