import { randomUUID } from 'node:crypto';
import { AtomicJsonStore } from '../atomicJsonStore';
import { emptyCapabilities, socialProviderIds, type SocialIntegrationSnapshot, type SocialOwnerType, type SocialProviderId, type StoredOAuthSelection, type StoredOAuthState, type StoredSocialAuditEvent, type StoredSocialConnection, type StoredSocialPublication, type StoredSocialAnalyticsSnapshot, type StoredScheduledPublication } from './types';

const initialSnapshot = (): SocialIntegrationSnapshot => ({ version: 1, connections: [], oauthStates: [], oauthSelections: [], auditEvents: [], publicationOperations: [], analyticsSnapshots: [], scheduledPublications: [] });

function validStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every(item => typeof item === 'string');
}

function validSnapshot(value: unknown): value is SocialIntegrationSnapshot {
  if (!value || typeof value !== 'object') return false;
  const snapshot = value as SocialIntegrationSnapshot;
  if (snapshot.version !== 1 || !Array.isArray(snapshot.connections) || !Array.isArray(snapshot.oauthStates)) return false;
  const connectionIds = new Set<string>();
  const uniqueAccounts = new Set<string>();
  const connectionsValid = snapshot.connections.every(connection => {
    if (!connection || typeof connection !== 'object' || !connection.id || connectionIds.has(connection.id)) return false;
    connectionIds.add(connection.id);
    const accountKey = [connection.ownerType, connection.ownerId, connection.provider, connection.providerAccountId].join(':');
    if (uniqueAccounts.has(accountKey)) return false;
    uniqueAccounts.add(accountKey);
    return ['personal', 'workspace'].includes(connection.ownerType)
      && socialProviderIds.includes(connection.provider)
      && typeof connection.ownerId === 'string'
      && typeof connection.providerAccountId === 'string'
      && typeof connection.displayName === 'string'
      && typeof connection.accessTokenEncrypted === 'string'
      && validStringArray(connection.scopes)
      && Boolean(connection.capabilities && Object.values(connection.capabilities).every(capability => typeof capability === 'boolean'))
      && ['connected', 'expired', 'permission_insufficient', 'authorization_revoked', 'error'].includes(connection.status)
      && typeof connection.createdAt === 'string'
      && typeof connection.updatedAt === 'string';
  });
  const stateHashes = new Set<string>();
  const statesValid = snapshot.oauthStates.every(state => state && typeof state.stateHash === 'string'
    && !stateHashes.has(state.stateHash) && Boolean(stateHashes.add(state.stateHash))
    && socialProviderIds.includes(state.provider)
    && ['personal', 'workspace'].includes(state.ownerType)
    && typeof state.ownerId === 'string' && typeof state.actorId === 'string'
    && (state.browserBindingHash === undefined || typeof state.browserBindingHash === 'string')
    && typeof state.redirectUri === 'string' && typeof state.returnTo === 'string'
    && typeof state.expiresAt === 'string' && typeof state.createdAt === 'string');
  const operations = snapshot.publicationOperations || [];
  const operationKeys = new Set<string>();
  const operationsValid = Array.isArray(operations) && operations.every(operation => {
    const key = [operation.ownerType, operation.ownerId, operation.idempotencyKey].join(':');
    if (!operation || operationKeys.has(key)) return false;
    operationKeys.add(key);
    return typeof operation.id === 'string' && ['personal', 'workspace'].includes(operation.ownerType)
      && typeof operation.ownerId === 'string' && typeof operation.connectionId === 'string'
      && typeof operation.idempotencyKey === 'string' && typeof operation.requestHash === 'string'
      && ['processing', 'published', 'indeterminate', 'failed'].includes(operation.status)
      && typeof operation.createdAt === 'string' && typeof operation.updatedAt === 'string';
  });
  const selectionsValid = (snapshot.oauthSelections || []).every(selection => selection && typeof selection.tokenHash === 'string'
    && socialProviderIds.includes(selection.provider) && ['personal', 'workspace'].includes(selection.ownerType)
    && typeof selection.ownerId === 'string' && typeof selection.actorId === 'string'
    && Array.isArray(selection.accounts) && selection.accounts.every(account => account && typeof account.providerAccountId === 'string'
      && typeof account.displayName === 'string' && typeof account.accessTokenEncrypted === 'string'
      && validStringArray(account.scopes) && Boolean(account.capabilities))
    && typeof selection.expiresAt === 'string' && typeof selection.createdAt === 'string');
  const auditValid = (snapshot.auditEvents || []).every(event => event && typeof event.id === 'string'
    && ['personal', 'workspace'].includes(event.ownerType) && socialProviderIds.includes(event.provider)
    && typeof event.ownerId === 'string' && typeof event.actorId === 'string'
    && typeof event.action === 'string' && ['success', 'failure'].includes(event.outcome)
    && typeof event.createdAt === 'string');
  const analyticsValid = Array.isArray(snapshot.analyticsSnapshots || []) && (snapshot.analyticsSnapshots || []).every(item => item && ['personal', 'workspace'].includes(item.ownerType)
    && typeof item.ownerId === 'string' && typeof item.connectionId === 'string' && socialProviderIds.includes(item.provider)
    && typeof item.from === 'string' && typeof item.to === 'string' && typeof item.updatedAt === 'string'
    && item.metrics && Object.values(item.metrics).every(value => typeof value === 'number' && Number.isFinite(value)));
  const scheduleKeys = new Set<string>();
  const scheduledValid = Array.isArray(snapshot.scheduledPublications || []) && (snapshot.scheduledPublications || []).every(item => {
    if (!item || !['personal', 'workspace'].includes(item.ownerType) || !['scheduled', 'publishing', 'published', 'processing', 'failed', 'indeterminate', 'cancelled'].includes(item.status)) return false;
    const key = [item.ownerType, item.ownerId, item.contentId, item.connectionId].join(':');
    if (scheduleKeys.has(key)) return false;
    scheduleKeys.add(key);
    return typeof item.id === 'string' && typeof item.ownerId === 'string' && typeof item.connectionId === 'string'
      && typeof item.contentId === 'string' && typeof item.scheduledAt === 'string' && Number.isFinite(Date.parse(item.scheduledAt))
      && item.request && typeof item.request.kind === 'string' && typeof item.createdAt === 'string' && typeof item.updatedAt === 'string';
  });
  return connectionsValid && statesValid && operationsValid && selectionsValid && auditValid && analyticsValid && scheduledValid;
}

export type SocialOwner = { ownerType: SocialOwnerType; ownerId: string; clientId?: string };

export class SocialIntegrationRepository {
  private state: SocialIntegrationSnapshot;
  private readonly store?: AtomicJsonStore<SocialIntegrationSnapshot>;

  constructor(filename: string | null) {
    this.store = filename ? new AtomicJsonStore(filename, validSnapshot) : undefined;
    const loaded = this.store?.load(initialSnapshot()) || initialSnapshot();
    this.state = {
      ...loaded,
      connections: loaded.connections.map(connection => ({ ...connection, capabilities: { ...emptyCapabilities(), ...connection.capabilities } })),
      oauthStates: loaded.oauthStates.filter(state => typeof state.browserBindingHash === 'string'),
      oauthSelections: loaded.oauthSelections || [],
      auditEvents: loaded.auditEvents || [],
      publicationOperations: loaded.publicationOperations || [],
      analyticsSnapshots: loaded.analyticsSnapshots || [],
    };
  }

  private mutate<T>(action: (draft: SocialIntegrationSnapshot) => T) {
    const previous = this.state;
    const draft = structuredClone(previous);
    const result = action(draft);
    this.store?.save(draft);
    this.state = draft;
    return result;
  }

  health() {
    return { storage: this.store ? 'json' : 'memory' as const };
  }

  list(owner: SocialOwner, provider?: SocialProviderId) {
    return this.state.connections
      .filter(connection => connection.ownerType === owner.ownerType && connection.ownerId === owner.ownerId && (!provider || connection.provider === provider))
      .map(connection => structuredClone(connection));
  }

  listByOwnerId(ownerId: string) {
    return this.state.connections.filter(connection => connection.ownerId === ownerId).map(connection => structuredClone(connection));
  }

  listAnalyticsSnapshots(owner: SocialOwner) {
    return (this.state.analyticsSnapshots || []).filter(item => item.ownerType === owner.ownerType && item.ownerId === owner.ownerId
      && this.state.connections.some(connection => connection.id === item.connectionId && connection.ownerType === owner.ownerType && connection.ownerId === owner.ownerId))
      .map(item => structuredClone(item));
  }

  upsertAnalyticsSnapshot(owner: SocialOwner, input: Omit<StoredSocialAnalyticsSnapshot, 'ownerType' | 'ownerId'>) {
    return this.mutate(draft => {
      if (!draft.connections.some(connection => connection.id === input.connectionId && connection.ownerType === owner.ownerType && connection.ownerId === owner.ownerId)) return undefined;
      draft.analyticsSnapshots ||= [];
      const snapshot = { ...owner, ...input };
      const index = draft.analyticsSnapshots.findIndex(item => item.ownerType === owner.ownerType && item.ownerId === owner.ownerId
        && item.connectionId === input.connectionId && item.from === input.from && item.to === input.to);
      if (index < 0) draft.analyticsSnapshots.push(snapshot); else draft.analyticsSnapshots[index] = snapshot;
      return structuredClone(snapshot);
    });
  }

  addState(state: StoredOAuthState) {
    this.mutate(draft => {
      draft.oauthStates = draft.oauthStates.filter(item => Date.parse(item.expiresAt) > Date.now() && item.stateHash !== state.stateHash);
      draft.oauthStates.push(state);
    });
  }

  consumeState(stateHash: string, now = Date.now()) {
    return this.mutate(draft => {
      const state = draft.oauthStates.find(item => item.stateHash === stateHash);
      draft.oauthStates = draft.oauthStates.filter(item => item.stateHash !== stateHash && Date.parse(item.expiresAt) > now);
      return state && Date.parse(state.expiresAt) > now ? structuredClone(state) : undefined;
    });
  }

  findState(stateHash: string, now = Date.now()) {
    const state = this.state.oauthStates.find(item => item.stateHash === stateHash && Date.parse(item.expiresAt) > now);
    return state ? structuredClone(state) : undefined;
  }

  addSelection(selection: StoredOAuthSelection, now = Date.now()) {
    this.mutate(draft => {
      draft.oauthSelections = (draft.oauthSelections || []).filter(item => Date.parse(item.expiresAt) > now && item.tokenHash !== selection.tokenHash);
      draft.oauthSelections.push(selection);
    });
  }

  selection(tokenHash: string, owner: SocialOwner, actorId: string, now = Date.now()) {
    const selection = (this.state.oauthSelections || []).find(item => item.tokenHash === tokenHash
      && item.ownerType === owner.ownerType && item.ownerId === owner.ownerId && item.actorId === actorId
      && Date.parse(item.expiresAt) > now);
    return selection ? structuredClone(selection) : undefined;
  }

  consumeSelection(tokenHash: string, owner: SocialOwner, actorId: string, now = Date.now()) {
    return this.mutate(draft => {
      const selection = (draft.oauthSelections || []).find(item => item.tokenHash === tokenHash
        && item.ownerType === owner.ownerType && item.ownerId === owner.ownerId && item.actorId === actorId
        && Date.parse(item.expiresAt) > now);
      draft.oauthSelections = (draft.oauthSelections || []).filter(item => item.tokenHash !== tokenHash && Date.parse(item.expiresAt) > now);
      return selection ? structuredClone(selection) : undefined;
    });
  }

  audit(input: Omit<StoredSocialAuditEvent, 'id' | 'createdAt'>, timestamp = new Date().toISOString()) {
    return this.mutate(draft => {
      draft.auditEvents ||= [];
      const event: StoredSocialAuditEvent = { ...input, id: `social-audit-${randomUUID()}`, createdAt: timestamp };
      draft.auditEvents.push(event);
      if (draft.auditEvents.length > 10_000) draft.auditEvents.splice(0, draft.auditEvents.length - 10_000);
      return structuredClone(event);
    });
  }

  upsert(input: Omit<StoredSocialConnection, 'id' | 'createdAt' | 'updatedAt'>, timestamp = new Date().toISOString()) {
    return this.mutate(draft => {
      const existing = draft.connections.find(item => item.ownerType === input.ownerType && item.ownerId === input.ownerId && item.provider === input.provider && item.providerAccountId === input.providerAccountId);
      if (existing) {
        Object.assign(existing, input, { id: existing.id, clientId: existing.clientId, createdAt: existing.createdAt, updatedAt: timestamp });
        return structuredClone(existing);
      }
      const connection: StoredSocialConnection = { ...input, id: `social-${randomUUID()}`, createdAt: timestamp, updatedAt: timestamp };
      draft.connections.push(connection);
      return structuredClone(connection);
    });
  }

  update(id: string, owner: SocialOwner, values: Partial<StoredSocialConnection>) {
    return this.mutate(draft => {
      const connection = draft.connections.find(item => item.id === id && item.ownerType === owner.ownerType && item.ownerId === owner.ownerId);
      if (!connection) return undefined;
      Object.assign(connection, values, { id: connection.id, ownerType: connection.ownerType, ownerId: connection.ownerId, updatedAt: new Date().toISOString() });
      return structuredClone(connection);
    });
  }

  remove(owner: SocialOwner, provider: SocialProviderId, ids?: string[]) {
    return this.mutate(draft => {
      const removed = draft.connections.filter(item => item.ownerType === owner.ownerType && item.ownerId === owner.ownerId && item.provider === provider && (!ids || ids.includes(item.id)));
      const removedIds = new Set(removed.map(item => item.id));
      draft.connections = draft.connections.filter(item => !removedIds.has(item.id));
        draft.analyticsSnapshots = (draft.analyticsSnapshots || []).filter(item => !removedIds.has(item.connectionId));
        draft.scheduledPublications = (draft.scheduledPublications || []).map(item => removedIds.has(item.connectionId) && item.status === 'scheduled'
          ? { ...item, status: 'cancelled', errorCode: 'ACCOUNT_DISCONNECTED', updatedAt: new Date().toISOString() } : item);
      return structuredClone(removed);
    });
  }

  publication(owner: SocialOwner, idempotencyKey: string) {
    const operation = (this.state.publicationOperations || []).find(item => item.ownerType === owner.ownerType && item.ownerId === owner.ownerId && item.idempotencyKey === idempotencyKey);
    return operation ? structuredClone(operation) : undefined;
  }

  claimPublication(owner: SocialOwner, input: Pick<StoredSocialPublication, 'connectionId' | 'idempotencyKey' | 'requestHash'>, timestamp = new Date().toISOString()) {
    return this.mutate(draft => {
      draft.publicationOperations ||= [];
      const existing = draft.publicationOperations.find(item => item.ownerType === owner.ownerType && item.ownerId === owner.ownerId && item.idempotencyKey === input.idempotencyKey);
      if (existing) return structuredClone(existing);
      const operation: StoredSocialPublication = {
        id: `publish-${randomUUID()}`, ...owner, ...input, status: 'processing', createdAt: timestamp, updatedAt: timestamp,
      };
      draft.publicationOperations.push(operation);
      return structuredClone(operation);
    });
  }

  updatePublication(owner: SocialOwner, id: string, values: Partial<StoredSocialPublication>, timestamp = new Date().toISOString()) {
    return this.mutate(draft => {
      const operation = (draft.publicationOperations || []).find(item => item.id === id && item.ownerType === owner.ownerType && item.ownerId === owner.ownerId);
      if (!operation) return undefined;
      Object.assign(operation, values, { id: operation.id, ownerType: operation.ownerType, ownerId: operation.ownerId, idempotencyKey: operation.idempotencyKey, requestHash: operation.requestHash, updatedAt: timestamp });
      return structuredClone(operation);
    });
  }

  listScheduled(owner: SocialOwner) {
    return (this.state.scheduledPublications || []).filter(item => item.ownerType === owner.ownerType && item.ownerId === owner.ownerId).map(item => structuredClone(item));
  }

  schedule(owner: SocialOwner, input: Omit<StoredScheduledPublication, 'id' | 'ownerType' | 'ownerId' | 'status' | 'createdAt' | 'updatedAt'>, timestamp = new Date().toISOString()) {
    return this.mutate(draft => {
      if (!draft.connections.some(item => item.id === input.connectionId && item.ownerType === owner.ownerType && item.ownerId === owner.ownerId)) return undefined;
      draft.scheduledPublications ||= [];
      const existing = draft.scheduledPublications.find(item => item.ownerType === owner.ownerType && item.ownerId === owner.ownerId && item.contentId === input.contentId && item.connectionId === input.connectionId);
      if (existing) return structuredClone(existing);
      const created: StoredScheduledPublication = { id: `schedule-${randomUUID()}`, ...owner, ...input, status: 'scheduled', createdAt: timestamp, updatedAt: timestamp };
      draft.scheduledPublications.push(created);
      return structuredClone(created);
    });
  }

  claimDue(nowIso: string, limit = 10) {
    if (!(this.state.scheduledPublications || []).some(item => item.status === 'scheduled' && item.scheduledAt <= nowIso)) return [] as StoredScheduledPublication[];
    return this.mutate(draft => {
      const due = (draft.scheduledPublications || []).filter(item => item.status === 'scheduled' && item.scheduledAt <= nowIso)
        .sort((a, b) => a.scheduledAt.localeCompare(b.scheduledAt)).slice(0, limit);
      due.forEach(item => { item.status = 'publishing'; item.updatedAt = nowIso; });
      return structuredClone(due);
    });
  }

  recoverStalePublishing(beforeIso: string, timestamp = new Date().toISOString()) {
    if (!(this.state.scheduledPublications || []).some(item => item.status === 'publishing' && item.updatedAt < beforeIso)) return [] as StoredScheduledPublication[];
    return this.mutate(draft => {
      const stale = (draft.scheduledPublications || []).filter(item => item.status === 'publishing' && item.updatedAt < beforeIso);
      stale.forEach(item => { item.status = 'indeterminate'; item.errorCode = 'SOCIAL_PUBLICATION_INDETERMINATE'; item.updatedAt = timestamp; });
      return structuredClone(stale);
    });
  }

  updateScheduled(owner: SocialOwner, id: string, values: Pick<StoredScheduledPublication, 'status'> & Partial<Pick<StoredScheduledPublication, 'providerPostId' | 'errorCode'>>, timestamp = new Date().toISOString()) {
    return this.mutate(draft => {
      const item = (draft.scheduledPublications || []).find(item => item.id === id && item.ownerType === owner.ownerType && item.ownerId === owner.ownerId);
      if (!item) return undefined;
      Object.assign(item, values, { updatedAt: timestamp });
      return structuredClone(item);
    });
  }

  cancelScheduled(owner: SocialOwner, id: string, timestamp = new Date().toISOString()) {
    return this.mutate(draft => {
      const item = (draft.scheduledPublications || []).find(item => item.id === id && item.ownerType === owner.ownerType && item.ownerId === owner.ownerId && item.status === 'scheduled');
      if (!item) return undefined;
      item.status = 'cancelled'; item.updatedAt = timestamp;
      return structuredClone(item);
    });
  }

  rescheduleScheduled(owner: SocialOwner, id: string, scheduledAt: string, timestamp = new Date().toISOString()) {
    return this.mutate(draft => {
      const item = (draft.scheduledPublications || []).find(row => row.id === id && row.ownerType === owner.ownerType && row.ownerId === owner.ownerId && row.status === 'scheduled');
      if (!item) return undefined;
      item.scheduledAt = scheduledAt;
      item.updatedAt = timestamp;
      return structuredClone(item);
    });
  }
}

/**
 * Storage port used by the HTTP/application layer. The bundled implementation
 * is an atomic JSON adapter for development and single-instance tests. A SaaS
 * deployment must inject a durable transactional adapter (for example,
 * PostgreSQL) implementing this contract.
 */
type Awaitable<T> = T | Promise<T>;
type AsyncCompatibleMethod<T extends (...args: never[]) => unknown> = (...args: Parameters<T>) => Awaitable<ReturnType<T>>;
export type SocialIntegrationRepositoryPort = {
  [K in 'list' | 'listByOwnerId' | 'addState' | 'findState' | 'consumeState'
    | 'addSelection' | 'selection' | 'consumeSelection' | 'upsert' | 'update' | 'remove'
    | 'publication' | 'claimPublication' | 'updatePublication' | 'audit' | 'listAnalyticsSnapshots' | 'upsertAnalyticsSnapshot'
    | 'listScheduled' | 'schedule' | 'claimDue' | 'recoverStalePublishing' | 'updateScheduled' | 'cancelScheduled' | 'rescheduleScheduled']:
  SocialIntegrationRepository[K] extends (...args: never[]) => unknown ? AsyncCompatibleMethod<SocialIntegrationRepository[K]> : never;
} & {
  health: () => Awaitable<{ storage: string }>;
  close?: () => Awaitable<void>;
};
