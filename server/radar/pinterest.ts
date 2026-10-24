/** Pinterest Trends is a separately authorized API; social OAuth alone does not grant it. */
import { createHash } from 'node:crypto';
export type PinterestKeyword = {
  keyword: string;
  pct_growth_wow?: number;
  pct_growth_mom?: number;
  pct_growth_yoy?: number;
  time_series?: Record<string, number>;
};

const cache = new Map<string, { expiresAt: number; keywords: PinterestKeyword[] }>();
const running = new Map<string, Promise<PinterestKeyword[]>>();
const circuits = new Map<string, { failures: number; unavailableUntil: number }>();

async function queryPinterest(url: string, token: string, fetcher: typeof fetch): Promise<unknown> {
  const deadline = Date.now() + 8000;
  for (let attempt = 1; attempt <= 3; attempt++) {
    const remaining = deadline - Date.now();
    if (remaining <= 0) throw new Error('PINTEREST_TIMEOUT');
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), remaining);
    try {
      const response = await fetcher(url, { signal: controller.signal, headers: { Authorization: `Bearer ${token}` } });
      if (response.ok) return await response.json();
      if (![429, 503].includes(response.status) || attempt === 3 || Date.now() + 250 >= deadline) throw new Error(`PINTEREST_HTTP_${response.status}`);
      const retryAfter = Number(response.headers.get('retry-after'));
      const delay = Math.min(Math.max(0, deadline - Date.now() - 200), Number.isFinite(retryAfter) && retryAfter > 0 ? Math.min(10000, retryAfter * 1000) : 200 * 2 ** (attempt - 1) + Math.random() * 150);
      await new Promise(resolve => setTimeout(resolve, delay));
    } finally { clearTimeout(timeout); }
  }
  throw new Error('PINTEREST_UNAVAILABLE');
}

export async function collectPinterestKeywords(region: 'BR' | 'GLOBAL', fetcher: typeof fetch = fetch, forceRefresh = false): Promise<PinterestKeyword[] | null> {
  const token = process.env.RADAR_PINTEREST_ACCESS_TOKEN?.trim();
  if (!token || /^MY_|^REPLACE_|^YOUR_/i.test(token)) return null;
  const country = region === 'BR' ? 'BR' : 'US';
  const url = `https://api.pinterest.com/v5/trends/keywords/${country}/top/growing?limit=25`;
  const cacheKey = `${country}:${createHash('sha256').update(token).digest('hex')}`;
  const circuit = circuits.get(cacheKey) || { failures: 0, unavailableUntil: 0 };
  if (Date.now() < circuit.unavailableUntil) throw new Error('PINTEREST_CIRCUIT_OPEN');
  const cached = cache.get(cacheKey);
  if (cached && cached.expiresAt > Date.now() && (!forceRefresh || cached.expiresAt - 10 * 60000 > Date.now() - 30_000)) return structuredClone(cached.keywords);
  const existing = running.get(cacheKey);
  if (existing) return structuredClone(await existing);
  const work = (async () => {
    const body = await queryPinterest(url, token, fetcher);
    if (!body || typeof body !== 'object' || !Array.isArray((body as { trends?: unknown }).trends)) throw new Error('PINTEREST_RESPONSE_INVALID');
    const keywords: PinterestKeyword[] = (body as { trends: unknown[] }).trends.slice(0, 25).flatMap((item) => {
      if (!item || typeof item !== 'object') return [];
      const keyword = item as Record<string, unknown>;
      if (typeof keyword.keyword !== 'string' || !keyword.keyword.trim() || keyword.keyword.length > 180) return [];
      const growth = (key: string) => typeof keyword[key] === 'number' && Number.isFinite(keyword[key]) ? keyword[key] as number : undefined;
      const series = keyword.time_series && typeof keyword.time_series === 'object' && !Array.isArray(keyword.time_series)
        ? Object.fromEntries(Object.entries(keyword.time_series).filter(([date, value]) => /^\d{4}-\d{2}-\d{2}$/.test(date) && typeof value === 'number' && Number.isFinite(value)).slice(-52)) as Record<string, number>
        : undefined;
      return [{ keyword: keyword.keyword.trim(), pct_growth_wow: growth('pct_growth_wow'), pct_growth_mom: growth('pct_growth_mom'), pct_growth_yoy: growth('pct_growth_yoy'), time_series: series }];
    });
    circuits.delete(cacheKey);
    cache.set(cacheKey, { expiresAt: Date.now() + 10 * 60000, keywords });
    return keywords;
  })().catch(error => {
    const failures = circuit.failures + 1;
    if (circuits.size > 80) circuits.delete(circuits.keys().next().value!);
    circuits.set(cacheKey, { failures, unavailableUntil: failures >= 3 ? Date.now() + 60000 : 0 });
    throw error;
  }).finally(() => running.delete(cacheKey));
  running.set(cacheKey, work);
  return structuredClone(await work);
}
