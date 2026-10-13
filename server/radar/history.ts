import path from 'node:path';
import { Pool } from 'pg';
import { AtomicJsonStore } from '../atomicJsonStore';
import type { RadarTrend } from '../radar';

export type RadarHistoryPoint = { scope: string; region: 'BR' | 'GLOBAL'; trendId: string; score: number; observedAt: string; observedValue?: number; metricKind?: 'traffic' | 'growth' };
type State = { version: 1; points: RadarHistoryPoint[]; saved?: Array<{ scope: string; trend: RadarTrend }> };
const valid = (value: unknown): value is State => {
  if (!value || typeof value !== 'object') return false;
  const state = value as State;
  return state.version === 1 && Array.isArray(state.points) && (!state.saved || Array.isArray(state.saved) && state.saved.every(item => typeof item.scope === 'string' && typeof item.trend?.id === 'string')) && state.points.every(point =>
    typeof point.scope === 'string' && typeof point.trendId === 'string' &&
    ['BR', 'GLOBAL'].includes(point.region) && Number.isFinite(point.score) &&
    typeof point.observedAt === 'string');
};

/** Keeps only calculated scores, never OAuth tokens or raw provider responses. */
export class RadarHistoryStore {
  private readonly pool?: Pool;
  private readonly ready?: Promise<void>;
  private readonly local?: AtomicJsonStore<State>;
  private state?: State;

  constructor(filename = path.resolve('.clicko-data/radar-history.json')) {
    if (process.env.NODE_ENV === 'production') {
      const connectionString = process.env.SOCIAL_DATABASE_URL;
      if (!connectionString) throw new Error('RADAR_DATABASE_REQUIRED');
      this.pool = new Pool({ connectionString, ssl: process.env.SOCIAL_DATABASE_SSL === 'disable' ? undefined : { rejectUnauthorized: true }, max: 3, connectionTimeoutMillis: 10000 });
      this.ready = this.pool.query(`CREATE TABLE IF NOT EXISTS clicko_radar_history (
        scope text NOT NULL, region text NOT NULL, trend_id text NOT NULL,
        observed_at timestamptz NOT NULL, score smallint NOT NULL,
        observed_value double precision, metric_kind text,
        PRIMARY KEY (scope, region, trend_id, observed_at)
      );
      ALTER TABLE clicko_radar_history ADD COLUMN IF NOT EXISTS observed_value double precision;
      ALTER TABLE clicko_radar_history ADD COLUMN IF NOT EXISTS metric_kind text;
      CREATE TABLE IF NOT EXISTS clicko_radar_saved (
        scope text NOT NULL, trend_id text NOT NULL, data jsonb NOT NULL,
        saved_at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY (scope, trend_id)
      );`).then(() => undefined);
    } else {
      const resolved = path.resolve(filename);
      for (const root of ['public', 'dist']) {
        const relative = path.relative(path.resolve(root), resolved);
        if (!relative || (!relative.startsWith('..' + path.sep) && relative !== '..' && !path.isAbsolute(relative))) throw new Error('RADAR_PRIVATE_STORAGE_REQUIRED');
      }
      this.local = new AtomicJsonStore(resolved, valid);
      this.state = this.local.load({ version: 1, points: [] });
    }
  }

  async list(scope: string, region: 'BR' | 'GLOBAL'): Promise<RadarHistoryPoint[]> {
    const cutoff = new Date(Date.now() - 30 * 86400000).toISOString();
    if (this.pool) {
      await this.ready;
      const result = await this.pool.query<{ trend_id: string; score: number; observed_at: Date; observed_value: number | null; metric_kind: 'traffic' | 'growth' | null }>(
        'SELECT trend_id, score, observed_at, observed_value, metric_kind FROM clicko_radar_history WHERE scope=$1 AND region=$2 AND observed_at >= $3 ORDER BY observed_at DESC LIMIT 3000',
        [scope, region, cutoff]);
      return result.rows.map(row => ({ scope, region, trendId: row.trend_id, score: row.score, observedAt: row.observed_at.toISOString(), observedValue: row.observed_value ?? undefined, metricKind: row.metric_kind ?? undefined }));
    }
    return (this.state?.points || []).filter(point => point.scope === scope && point.region === region && point.observedAt >= cutoff);
  }

  async append(points: RadarHistoryPoint[]): Promise<void> {
    if (!points.length) return;
    if (this.pool) {
      await this.ready;
      const client = await this.pool.connect();
      try {
        await client.query('BEGIN');
        for (const point of points) await client.query(
          'INSERT INTO clicko_radar_history(scope,region,trend_id,observed_at,score,observed_value,metric_kind) VALUES ($1,$2,$3,$4,$5,$6,$7) ON CONFLICT DO NOTHING',
          [point.scope, point.region, point.trendId, point.observedAt, point.score, point.observedValue ?? null, point.metricKind ?? null]);
        await client.query('DELETE FROM clicko_radar_history WHERE observed_at < now() - interval \'30 days\'');
        await client.query('COMMIT');
      } catch (error) { await client.query('ROLLBACK'); throw error; }
      finally { client.release(); }
      return;
    }
    const cutoff = new Date(Date.now() - 30 * 86400000).toISOString();
    const state: State = { version: 1, points: [...(this.state?.points || []), ...points].filter(point => point.observedAt >= cutoff).slice(-3000), saved: this.state?.saved || [] };
    this.local?.save(state);
    this.state = state;
  }

  async saved(scope: string): Promise<RadarTrend[]> {
    if (this.pool) {
      await this.ready;
      const result = await this.pool.query<{ data: RadarTrend }>('SELECT data FROM clicko_radar_saved WHERE scope=$1 ORDER BY saved_at DESC LIMIT 20', [scope]);
      return result.rows.map(row => row.data);
    }
    return (this.state?.saved || []).filter(item => item.scope === scope).map(item => item.trend).slice(0, 20);
  }

  async setSaved(scope: string, trends: RadarTrend[]): Promise<void> {
    const selected = trends.slice(0, 20);
    if (this.pool) {
      await this.ready;
      const client = await this.pool.connect();
      try {
        await client.query('BEGIN');
        await client.query('DELETE FROM clicko_radar_saved WHERE scope=$1', [scope]);
        for (const trend of selected) await client.query('INSERT INTO clicko_radar_saved(scope,trend_id,data) VALUES ($1,$2,$3)', [scope, trend.id, JSON.stringify(trend)]);
        await client.query('COMMIT');
      } catch (error) { await client.query('ROLLBACK'); throw error; }
      finally { client.release(); }
      return;
    }
    const state: State = { version: 1, points: this.state?.points || [], saved: [
      ...(this.state?.saved || []).filter(item => item.scope !== scope),
      ...selected.map(trend => ({ scope, trend })),
    ].slice(-1000) };
    this.local?.save(state);
    this.state = state;
  }
}

let instance: RadarHistoryStore | undefined;
export const radarHistoryStore = () => instance ||= new RadarHistoryStore();
