import { randomUUID } from 'node:crypto';
import { Pool, type PoolClient } from 'pg';
import type { SocialIntegrationRepositoryPort, SocialOwner } from './repository';
import type { SocialProviderId, StoredOAuthSelection, StoredOAuthState, StoredSocialAuditEvent, StoredSocialConnection, StoredSocialPublication, StoredSocialAnalyticsSnapshot, StoredScheduledPublication } from './types';

type JsonRow<T> = { data: T };

const connectionKey = (owner: SocialOwner, provider: SocialProviderId, providerAccountId: string) => [owner.ownerType, owner.ownerId, provider, providerAccountId];

export class PostgresSocialIntegrationRepository implements SocialIntegrationRepositoryPort {
  private readonly pool: Pool;
  private readonly ready: Promise<void>;

  constructor(connectionString: string, ssl: boolean) {
    if (!connectionString) throw new Error('SOCIAL_DATABASE_URL_REQUIRED');
    this.pool = new Pool({ connectionString, ssl: ssl ? { rejectUnauthorized: true } : undefined, max: 12, idleTimeoutMillis: 30_000, connectionTimeoutMillis: 10_000 });
    this.ready = this.ensureSchema();
  }

  private async ensureSchema() {
    await this.pool.query(`
      CREATE TABLE IF NOT EXISTS clicko_social_connections (
        id text PRIMARY KEY,
        owner_type text NOT NULL CHECK (owner_type IN ('personal','workspace')),
        owner_id text NOT NULL,
        client_id text NOT NULL DEFAULT '',
        provider text NOT NULL,
        provider_account_id text NOT NULL,
        data jsonb NOT NULL,
        created_at timestamptz NOT NULL,
        updated_at timestamptz NOT NULL,
        UNIQUE (owner_type, owner_id, client_id, provider, provider_account_id)
      );
      CREATE INDEX IF NOT EXISTS clicko_social_connections_owner_idx ON clicko_social_connections(owner_type, owner_id, provider);
      CREATE UNIQUE INDEX IF NOT EXISTS clicko_social_connections_identity_idx ON clicko_social_connections(owner_type, owner_id, provider, provider_account_id);
      CREATE TABLE IF NOT EXISTS clicko_social_analytics_snapshots (
        owner_type text NOT NULL CHECK (owner_type IN ('personal','workspace')),
        owner_id text NOT NULL,
        connection_id text NOT NULL REFERENCES clicko_social_connections(id) ON DELETE CASCADE,
        period_from date NOT NULL,
        period_to date NOT NULL,
        data jsonb NOT NULL,
        updated_at timestamptz NOT NULL,
        PRIMARY KEY (owner_type, owner_id, connection_id, period_from, period_to)
      );
      CREATE INDEX IF NOT EXISTS clicko_social_analytics_owner_idx ON clicko_social_analytics_snapshots(owner_type,owner_id,updated_at DESC);
      CREATE TABLE IF NOT EXISTS clicko_social_scheduled_publications (
        id text PRIMARY KEY,
        owner_type text NOT NULL CHECK (owner_type IN ('personal','workspace')),
        owner_id text NOT NULL,
        connection_id text NOT NULL,
        content_id text NOT NULL,
        scheduled_at timestamptz NOT NULL,
        status text NOT NULL,
        data jsonb NOT NULL,
        created_at timestamptz NOT NULL,
        updated_at timestamptz NOT NULL,
        UNIQUE(owner_type,owner_id,content_id,connection_id)
      );
      CREATE INDEX IF NOT EXISTS clicko_social_scheduled_due_idx ON clicko_social_scheduled_publications(scheduled_at) WHERE status='scheduled';
      CREATE INDEX IF NOT EXISTS clicko_social_scheduled_stale_idx ON clicko_social_scheduled_publications(updated_at) WHERE status='publishing';
      CREATE INDEX IF NOT EXISTS clicko_social_scheduled_owner_idx ON clicko_social_scheduled_publications(owner_type,owner_id,created_at DESC);
      CREATE TABLE IF NOT EXISTS clicko_social_oauth_states (
        state_hash text PRIMARY KEY,
        data jsonb NOT NULL,
        expires_at timestamptz NOT NULL
      );
      CREATE INDEX IF NOT EXISTS clicko_social_oauth_states_expiry_idx ON clicko_social_oauth_states(expires_at);
      CREATE TABLE IF NOT EXISTS clicko_social_oauth_selections (
        token_hash text PRIMARY KEY,
        owner_type text NOT NULL CHECK (owner_type IN ('personal','workspace')),
        owner_id text NOT NULL,
        actor_id text NOT NULL,
        data jsonb NOT NULL,
        expires_at timestamptz NOT NULL
      );
      CREATE INDEX IF NOT EXISTS clicko_social_oauth_selections_owner_idx ON clicko_social_oauth_selections(owner_type, owner_id, actor_id);
      CREATE TABLE IF NOT EXISTS clicko_social_publications (
        id text PRIMARY KEY,
        owner_type text NOT NULL CHECK (owner_type IN ('personal','workspace')),
        owner_id text NOT NULL,
        idempotency_key text NOT NULL,
        data jsonb NOT NULL,
        created_at timestamptz NOT NULL,
        updated_at timestamptz NOT NULL,
        UNIQUE (owner_type, owner_id, idempotency_key)
      );
      CREATE TABLE IF NOT EXISTS clicko_social_audit_events (
        id text PRIMARY KEY,
        owner_type text NOT NULL CHECK (owner_type IN ('personal','workspace')),
        owner_id text NOT NULL,
        actor_id text NOT NULL,
        provider text NOT NULL,
        action text NOT NULL,
        outcome text NOT NULL,
        data jsonb NOT NULL,
        created_at timestamptz NOT NULL
      );
      CREATE INDEX IF NOT EXISTS clicko_social_audit_owner_idx ON clicko_social_audit_events(owner_type, owner_id, created_at DESC);
    `);
  }

  async health() {
    await this.ready;
    await this.pool.query('SELECT 1');
    return { storage: 'postgres' };
  }

  async close() {
    await this.pool.end();
  }

  private async transaction<T>(action: (client: PoolClient) => Promise<T>) {
    await this.ready;
    const client = await this.pool.connect();
    try {
      await client.query('BEGIN');
      const result = await action(client);
      await client.query('COMMIT');
      return result;
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally { client.release(); }
  }

  async list(owner: SocialOwner, provider?: SocialProviderId) {
    await this.ready;
    const values: unknown[] = [owner.ownerType, owner.ownerId];
    const providerClause = provider ? ` AND provider = $${values.push(provider)}` : '';
    const result = await this.pool.query<JsonRow<StoredSocialConnection>>(`SELECT data FROM clicko_social_connections WHERE owner_type = $1 AND owner_id = $2${providerClause} ORDER BY created_at`, values);
    return result.rows.map(row => structuredClone(row.data));
  }

  async listByOwnerId(ownerId: string) {
    await this.ready;
    const result = await this.pool.query<JsonRow<StoredSocialConnection>>('SELECT data FROM clicko_social_connections WHERE owner_id = $1 ORDER BY created_at', [ownerId]);
    return result.rows.map(row => structuredClone(row.data));
  }

  async listAnalyticsSnapshots(owner: SocialOwner) {
    await this.ready;
    const rows = await this.pool.query<JsonRow<StoredSocialAnalyticsSnapshot>>(`SELECT s.data FROM clicko_social_analytics_snapshots s
      JOIN clicko_social_connections c ON c.id=s.connection_id AND c.owner_type=s.owner_type AND c.owner_id=s.owner_id
      WHERE s.owner_type=$1 AND s.owner_id=$2 ORDER BY s.updated_at DESC`, [owner.ownerType, owner.ownerId]);
    return rows.rows.map(row => structuredClone(row.data));
  }

  async upsertAnalyticsSnapshot(owner: SocialOwner, input: Omit<StoredSocialAnalyticsSnapshot, 'ownerType' | 'ownerId'>) {
    await this.ready;
    const snapshot: StoredSocialAnalyticsSnapshot = { ...owner, ...input };
    const rows = await this.pool.query<JsonRow<StoredSocialAnalyticsSnapshot>>(`INSERT INTO clicko_social_analytics_snapshots(owner_type,owner_id,connection_id,period_from,period_to,data,updated_at)
      SELECT $1,$2,c.id,$4::date,$5::date,$6::jsonb,$7::timestamptz FROM clicko_social_connections c
      WHERE c.id=$3 AND c.owner_type=$1 AND c.owner_id=$2
      ON CONFLICT(owner_type,owner_id,connection_id,period_from,period_to) DO UPDATE SET data=excluded.data,updated_at=excluded.updated_at RETURNING data`,
      [owner.ownerType, owner.ownerId, input.connectionId, input.from, input.to, JSON.stringify(snapshot), input.updatedAt]);
    return rows.rows[0] ? structuredClone(rows.rows[0].data) : undefined;
  }

  async addState(state: StoredOAuthState) {
    await this.ready;
    await this.pool.query('DELETE FROM clicko_social_oauth_states WHERE expires_at <= now() OR state_hash = $1', [state.stateHash]);
    await this.pool.query('INSERT INTO clicko_social_oauth_states(state_hash,data,expires_at) VALUES($1,$2::jsonb,$3)', [state.stateHash, JSON.stringify(state), state.expiresAt]);
  }

  async findState(stateHash: string, now = Date.now()) {
    await this.ready;
    const result = await this.pool.query<JsonRow<StoredOAuthState>>('SELECT data FROM clicko_social_oauth_states WHERE state_hash = $1 AND expires_at > $2', [stateHash, new Date(now)]);
    return result.rows[0] ? structuredClone(result.rows[0].data) : undefined;
  }

  async consumeState(stateHash: string, now = Date.now()) {
    return this.transaction(async client => {
      const result = await client.query<JsonRow<StoredOAuthState>>('DELETE FROM clicko_social_oauth_states WHERE state_hash = $1 AND expires_at > $2 RETURNING data', [stateHash, new Date(now)]);
      await client.query('DELETE FROM clicko_social_oauth_states WHERE expires_at <= $1', [new Date(now)]);
      return result.rows[0] ? structuredClone(result.rows[0].data) : undefined;
    });
  }

  async addSelection(selection: StoredOAuthSelection, now = Date.now()) {
    await this.ready;
    await this.pool.query('DELETE FROM clicko_social_oauth_selections WHERE expires_at <= $1 OR token_hash = $2', [new Date(now), selection.tokenHash]);
    await this.pool.query('INSERT INTO clicko_social_oauth_selections(token_hash,owner_type,owner_id,actor_id,data,expires_at) VALUES($1,$2,$3,$4,$5::jsonb,$6)', [selection.tokenHash, selection.ownerType, selection.ownerId, selection.actorId, JSON.stringify(selection), selection.expiresAt]);
  }

  async selection(tokenHash: string, owner: SocialOwner, actorId: string, now = Date.now()) {
    await this.ready;
    const result = await this.pool.query<JsonRow<StoredOAuthSelection>>('SELECT data FROM clicko_social_oauth_selections WHERE token_hash=$1 AND owner_type=$2 AND owner_id=$3 AND actor_id=$4 AND expires_at>$5', [tokenHash, owner.ownerType, owner.ownerId, actorId, new Date(now)]);
    return result.rows[0] ? structuredClone(result.rows[0].data) : undefined;
  }

  async consumeSelection(tokenHash: string, owner: SocialOwner, actorId: string, now = Date.now()) {
    return this.transaction(async client => {
      const result = await client.query<JsonRow<StoredOAuthSelection>>('DELETE FROM clicko_social_oauth_selections WHERE token_hash=$1 AND owner_type=$2 AND owner_id=$3 AND actor_id=$4 AND expires_at>$5 RETURNING data', [tokenHash, owner.ownerType, owner.ownerId, actorId, new Date(now)]);
      await client.query('DELETE FROM clicko_social_oauth_selections WHERE expires_at <= $1', [new Date(now)]);
      return result.rows[0] ? structuredClone(result.rows[0].data) : undefined;
    });
  }

  async upsert(input: Omit<StoredSocialConnection, 'id' | 'createdAt' | 'updatedAt'>, timestamp = new Date().toISOString()) {
    return this.transaction(async client => {
      const owner = { ownerType: input.ownerType, ownerId: input.ownerId, clientId: input.clientId };
      const key = connectionKey(owner, input.provider, input.providerAccountId);
      const existing = await client.query<JsonRow<StoredSocialConnection>>('SELECT data FROM clicko_social_connections WHERE owner_type=$1 AND owner_id=$2 AND provider=$3 AND provider_account_id=$4 FOR UPDATE', key);
      const prior = existing.rows[0]?.data;
      const connection: StoredSocialConnection = { ...input, clientId: prior?.clientId || input.clientId, id: prior?.id || `social-${randomUUID()}`, createdAt: prior?.createdAt || timestamp, updatedAt: timestamp };
      const saved = await client.query<JsonRow<StoredSocialConnection>>(`INSERT INTO clicko_social_connections(id,owner_type,owner_id,client_id,provider,provider_account_id,data,created_at,updated_at)
        VALUES($1,$2,$3,$4,$5,$6,$7::jsonb,$8,$9)
        ON CONFLICT(owner_type,owner_id,provider,provider_account_id)
        DO UPDATE SET data=(EXCLUDED.data - 'id' - 'createdAt' - 'clientId')
          || jsonb_build_object('id',clicko_social_connections.id,'createdAt',clicko_social_connections.data->'createdAt')
          || CASE WHEN clicko_social_connections.data ? 'clientId' THEN jsonb_build_object('clientId',clicko_social_connections.data->'clientId') ELSE '{}'::jsonb END,
          updated_at=EXCLUDED.updated_at RETURNING data`, [connection.id, owner.ownerType, owner.ownerId, connection.clientId || '', input.provider, input.providerAccountId, JSON.stringify(connection), connection.createdAt, connection.updatedAt]);
      return structuredClone(saved.rows[0].data);
    });
  }

  async update(id: string, owner: SocialOwner, values: Partial<StoredSocialConnection>) {
    return this.transaction(async client => {
      const result = await client.query<JsonRow<StoredSocialConnection>>('SELECT data FROM clicko_social_connections WHERE id=$1 AND owner_type=$2 AND owner_id=$3 FOR UPDATE', [id, owner.ownerType, owner.ownerId]);
      const current = result.rows[0]?.data;
      if (!current) return undefined;
      const updated: StoredSocialConnection = { ...current, ...values, id: current.id, ownerType: current.ownerType, ownerId: current.ownerId, updatedAt: new Date().toISOString() };
      await client.query('UPDATE clicko_social_connections SET client_id=$1, data=$2::jsonb, updated_at=$3 WHERE id=$4', [updated.clientId || '', JSON.stringify(updated), updated.updatedAt, id]);
      return structuredClone(updated);
    });
  }

  async remove(owner: SocialOwner, provider: SocialProviderId, ids?: string[]) {
    return this.transaction(async client => {
      const values: unknown[] = [owner.ownerType, owner.ownerId, provider];
      const idsClause = ids ? ` AND id = ANY($${values.push(ids)}::text[])` : '';
      const affected = await client.query<{ id: string }>(`SELECT id FROM clicko_social_connections WHERE owner_type=$1 AND owner_id=$2 AND provider=$3${idsClause}`, values);
      for (const row of affected.rows) {
        await client.query(`UPDATE clicko_social_scheduled_publications SET status='cancelled',updated_at=now(),
          data=jsonb_set(jsonb_set(jsonb_set(data,'{status}','"cancelled"'::jsonb),'{errorCode}',
          '"ACCOUNT_DISCONNECTED"'::jsonb),'{updatedAt}',to_jsonb(now()::text))
          WHERE owner_type=$1 AND owner_id=$2 AND connection_id=$3 AND status='scheduled'`, [owner.ownerType, owner.ownerId, row.id]);
      }
      const result = await client.query<JsonRow<StoredSocialConnection>>(`DELETE FROM clicko_social_connections WHERE owner_type=$1 AND owner_id=$2 AND provider=$3${idsClause} RETURNING data`, values);
      return result.rows.map(row => structuredClone(row.data));
    });
  }

  async publication(owner: SocialOwner, idempotencyKey: string) {
    await this.ready;
    const result = await this.pool.query<JsonRow<StoredSocialPublication>>('SELECT data FROM clicko_social_publications WHERE owner_type=$1 AND owner_id=$2 AND idempotency_key=$3', [owner.ownerType, owner.ownerId, idempotencyKey]);
    return result.rows[0] ? structuredClone(result.rows[0].data) : undefined;
  }

  async claimPublication(owner: SocialOwner, input: Pick<StoredSocialPublication, 'connectionId' | 'idempotencyKey' | 'requestHash'>, timestamp = new Date().toISOString()) {
    await this.ready;
    const operation: StoredSocialPublication = { id: `publish-${randomUUID()}`, ...owner, ...input, status: 'processing', createdAt: timestamp, updatedAt: timestamp };
    const result = await this.pool.query<JsonRow<StoredSocialPublication>>(`INSERT INTO clicko_social_publications(id,owner_type,owner_id,idempotency_key,data,created_at,updated_at)
      VALUES($1,$2,$3,$4,$5::jsonb,$6,$7) ON CONFLICT(owner_type,owner_id,idempotency_key) DO UPDATE SET id=clicko_social_publications.id RETURNING data`,
      [operation.id, owner.ownerType, owner.ownerId, operation.idempotencyKey, JSON.stringify(operation), timestamp, timestamp]);
    return structuredClone(result.rows[0]?.data || operation);
  }

  async updatePublication(owner: SocialOwner, id: string, values: Partial<StoredSocialPublication>, timestamp = new Date().toISOString()) {
    return this.transaction(async client => {
      const result = await client.query<JsonRow<StoredSocialPublication>>('SELECT data FROM clicko_social_publications WHERE id=$1 AND owner_type=$2 AND owner_id=$3 FOR UPDATE', [id, owner.ownerType, owner.ownerId]);
      const current = result.rows[0]?.data;
      if (!current) return undefined;
      const updated: StoredSocialPublication = { ...current, ...values, id: current.id, ownerType: current.ownerType, ownerId: current.ownerId, idempotencyKey: current.idempotencyKey, requestHash: current.requestHash, updatedAt: timestamp };
      await client.query('UPDATE clicko_social_publications SET data=$1::jsonb, updated_at=$2 WHERE id=$3', [JSON.stringify(updated), timestamp, id]);
      return structuredClone(updated);
    });
  }

  async listScheduled(owner: SocialOwner) {
    await this.ready;
    const rows = await this.pool.query<JsonRow<StoredScheduledPublication>>('SELECT data FROM clicko_social_scheduled_publications WHERE owner_type=$1 AND owner_id=$2 ORDER BY created_at DESC', [owner.ownerType, owner.ownerId]);
    return rows.rows.map(row => structuredClone(row.data));
  }

  async schedule(owner: SocialOwner, input: Omit<StoredScheduledPublication, 'id' | 'ownerType' | 'ownerId' | 'status' | 'createdAt' | 'updatedAt'>, timestamp = new Date().toISOString()) {
    await this.ready;
    const item: StoredScheduledPublication = { id: `schedule-${randomUUID()}`, ...owner, ...input, status: 'scheduled', createdAt: timestamp, updatedAt: timestamp };
    const rows = await this.pool.query<JsonRow<StoredScheduledPublication>>(`INSERT INTO clicko_social_scheduled_publications(id,owner_type,owner_id,connection_id,content_id,scheduled_at,status,data,created_at,updated_at)
      SELECT $1,$2,$3,c.id,$5,$6::timestamptz,'scheduled',$7::jsonb,$8::timestamptz,$8::timestamptz FROM clicko_social_connections c
      WHERE c.id=$4 AND c.owner_type=$2 AND c.owner_id=$3
      ON CONFLICT(owner_type,owner_id,content_id,connection_id) DO UPDATE SET id=clicko_social_scheduled_publications.id
      WHERE clicko_social_scheduled_publications.status='scheduled' RETURNING data`,
      [item.id, owner.ownerType, owner.ownerId, input.connectionId, input.contentId, input.scheduledAt, JSON.stringify(item), timestamp]);
    return rows.rows[0] ? structuredClone(rows.rows[0].data) : undefined;
  }

  async claimDue(nowIso: string, limit = 10) {
    await this.ready;
    const rows = await this.pool.query<JsonRow<StoredScheduledPublication>>(`WITH due AS (
      SELECT id FROM clicko_social_scheduled_publications WHERE status='scheduled' AND scheduled_at <= $1::timestamptz
      ORDER BY scheduled_at FOR UPDATE SKIP LOCKED LIMIT $2
    ) UPDATE clicko_social_scheduled_publications p SET status='publishing',updated_at=$1::timestamptz,
      data=jsonb_set(jsonb_set(p.data,'{status}','"publishing"'::jsonb),'{updatedAt}',to_jsonb($1::text))
      FROM due WHERE p.id=due.id RETURNING p.data`, [nowIso, limit]);
    return rows.rows.map(row => structuredClone(row.data));
  }

  async recoverStalePublishing(beforeIso: string, timestamp = new Date().toISOString()) {
    await this.ready;
    const rows = await this.pool.query<JsonRow<StoredScheduledPublication>>(`UPDATE clicko_social_scheduled_publications SET status='indeterminate',updated_at=$2::timestamptz,
      data=jsonb_set(jsonb_set(jsonb_set(data,'{status}','"indeterminate"'::jsonb),'{errorCode}',
      '"SOCIAL_PUBLICATION_INDETERMINATE"'::jsonb),'{updatedAt}',to_jsonb($2::text))
      WHERE status='publishing' AND updated_at < $1::timestamptz RETURNING data`, [beforeIso, timestamp]);
    return rows.rows.map(row => structuredClone(row.data));
  }

  async updateScheduled(owner: SocialOwner, id: string, values: Pick<StoredScheduledPublication, 'status'> & Partial<Pick<StoredScheduledPublication, 'providerPostId' | 'errorCode'>>, timestamp = new Date().toISOString()) {
    return this.transaction(async client => {
      const rows = await client.query<JsonRow<StoredScheduledPublication>>('SELECT data FROM clicko_social_scheduled_publications WHERE id=$1 AND owner_type=$2 AND owner_id=$3 FOR UPDATE', [id, owner.ownerType, owner.ownerId]);
      const current = rows.rows[0]?.data;
      if (!current) return undefined;
      const updated = { ...current, ...values, updatedAt: timestamp };
      await client.query('UPDATE clicko_social_scheduled_publications SET status=$1,data=$2::jsonb,updated_at=$3 WHERE id=$4', [values.status, JSON.stringify(updated), timestamp, id]);
      return structuredClone(updated);
    });
  }

  async cancelScheduled(owner: SocialOwner, id: string, timestamp = new Date().toISOString()) {
    await this.ready;
    const rows = await this.pool.query<JsonRow<StoredScheduledPublication>>(`UPDATE clicko_social_scheduled_publications SET status='cancelled',updated_at=$4::timestamptz,
      data=jsonb_set(jsonb_set(data,'{status}','"cancelled"'::jsonb),'{updatedAt}',to_jsonb($4::text))
      WHERE id=$1 AND owner_type=$2 AND owner_id=$3 AND status='scheduled' RETURNING data`, [id, owner.ownerType, owner.ownerId, timestamp]);
    return rows.rows[0] ? structuredClone(rows.rows[0].data) : undefined;
  }

  async rescheduleScheduled(owner: SocialOwner, id: string, scheduledAt: string, timestamp = new Date().toISOString()) {
    await this.ready;
    const rows = await this.pool.query<JsonRow<StoredScheduledPublication>>(`UPDATE clicko_social_scheduled_publications SET scheduled_at=$4::timestamptz,updated_at=$5::timestamptz,
      data=jsonb_set(jsonb_set(data,'{scheduledAt}',to_jsonb($4::text)),'{updatedAt}',to_jsonb($5::text))
      WHERE id=$1 AND owner_type=$2 AND owner_id=$3 AND status='scheduled' RETURNING data`,
      [id, owner.ownerType, owner.ownerId, scheduledAt, timestamp]);
    return rows.rows[0] ? structuredClone(rows.rows[0].data) : undefined;
  }

  async audit(input: Omit<StoredSocialAuditEvent, 'id' | 'createdAt'>, timestamp = new Date().toISOString()) {
    await this.ready;
    const event: StoredSocialAuditEvent = { ...input, id: `social-audit-${randomUUID()}`, createdAt: timestamp };
    await this.pool.query('INSERT INTO clicko_social_audit_events(id,owner_type,owner_id,actor_id,provider,action,outcome,data,created_at) VALUES($1,$2,$3,$4,$5,$6,$7,$8::jsonb,$9)', [event.id, event.ownerType, event.ownerId, event.actorId, event.provider, event.action, event.outcome, JSON.stringify(event), event.createdAt]);
    return structuredClone(event);
  }
}
