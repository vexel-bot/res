/** Small, per-user/workspace recovery for navigation. Never stores credentials or Blob URLs. */
const memory = new Map<string, unknown>();
const prefix = 'clicko:studios-navigation:v1:';
const maxBytes = 1_000_000;
export function matchesStudioDraft(value: unknown, template: object): boolean {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return false;
  return Object.entries(template).every(([key, sample]) => {
    const item = (value as Record<string, unknown>)[key];
    return typeof item === typeof sample && (typeof item !== 'number' || Number.isFinite(item));
  });
}
export function readStudioSession<T>(scope: string): T | undefined {
  if (memory.has(scope)) return memory.get(scope) as T;
  try {
    const raw = sessionStorage.getItem(prefix + scope);
    if (!raw || raw.length > maxBytes) return undefined;
    const parsed = JSON.parse(raw);
    if (parsed?.version !== 1 || !parsed.value || typeof parsed.value !== 'object') return undefined;
    memory.set(scope, parsed.value);
    return parsed.value as T;
  } catch { return undefined; }
}
export function writeStudioSession(scope: string, value: unknown) {
  memory.set(scope, value);
  try {
    const raw = JSON.stringify({ version: 1, value });
    if (raw.length <= maxBytes) sessionStorage.setItem(prefix + scope, raw);
    else sessionStorage.removeItem(prefix + scope);
  } catch { /* In-memory recovery still works; existing beforeunload guards remain. */ }
}
