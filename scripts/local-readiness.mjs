// The API checks storage, the Python service and the DEV bridge. A cold probe
// can legitimately take longer than one second. Share one request so polling
// never piles up expensive health checks on a resource-constrained host.
export const READINESS_TIMEOUT_MS = 15_000;
export function createReadinessProbe(url, { fetch: request = fetch, timeoutMs = READINESS_TIMEOUT_MS } = {}) {
  let pending;
  return () => {
    if (pending) return pending;
    pending = (async () => {
      try {
        const response = await request(url, { signal: AbortSignal.timeout(timeoutMs) });
        const body = await response.json();
        return { ready: response.ok && body?.status === 'ready', health: body };
      } catch { return { ready: false }; }
    })().finally(() => { pending = undefined; });
    return pending;
  };
}
