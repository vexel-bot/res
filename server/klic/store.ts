import path from 'node:path';
import { randomUUID } from 'node:crypto';
import { AtomicJsonStore } from '../atomicJsonStore';
import { scopeKey, type KlicGoal, type KlicRecord, type KlicScope } from '../../src/klic/contracts';

export type Trace = KlicScope & {
  id: string; parentId?: string; origin: string; tool: string; status: 'ok' | 'denied' | 'unavailable' | 'error';
  createdAt: string; durationMs: number; recordCount: number; errorCode?: string;
};
type Preference = KlicScope & { id: string; key: string; value: string; consent: true; updatedAt: string };
type EventRecord = KlicScope & { id: string; type: string; createdAt: string };
export type PreparedAction = KlicScope & { id: string; idempotencyKey: string; actionId: string; status: 'prepared'; executed: false; resource: KlicRecord; createdAt: string };
type State = { version: 1; traces: Trace[]; preferences: Preference[]; events: EventRecord[]; goals: KlicGoal[]; actions: PreparedAction[] };
const validScope = (value: unknown) => {
  if (!value || typeof value !== 'object') return false;
  const scope = value as Record<string, unknown>;
  return typeof scope.workspaceId === 'string' && typeof scope.userId === 'string' && (scope.clientId === null || typeof scope.clientId === 'string');
};
const identity = ({ workspaceId, userId, clientId }: KlicScope): KlicScope => ({ workspaceId, userId, clientId });
function valid(v: unknown): v is State {
  const s = v as State;
  return Boolean(s && s.version === 1 && Array.isArray(s.traces) && Array.isArray(s.preferences) && Array.isArray(s.events)
    && s.traces.every(t => validScope(t) && typeof t.id === 'string' && typeof t.tool === 'string' && typeof t.createdAt === 'string')
    && s.preferences.every(p => validScope(p) && p.consent === true && typeof p.key === 'string' && typeof p.value === 'string')
    && s.events.every(e => validScope(e) && typeof e.id === 'string' && typeof e.type === 'string' && typeof e.createdAt === 'string')
    && (s.goals === undefined || Array.isArray(s.goals) && s.goals.every(goal => validScope(goal) && typeof goal.id === 'string'
      && typeof goal.title === 'string' && goal.source === 'user' && ['active', 'completed', 'archived'].includes(goal.status)
      && typeof goal.createdAt === 'string' && typeof goal.updatedAt === 'string'))
    && (s.actions === undefined || Array.isArray(s.actions) && s.actions.every(action => validScope(action) && typeof action.id === 'string'
      && typeof action.idempotencyKey === 'string' && typeof action.actionId === 'string' && action.status === 'prepared' && action.executed === false
      && action.resource && typeof action.resource === 'object' && action.resource.workspaceId === action.workspaceId
      && (action.resource.clientId ?? null) === action.clientId && typeof action.createdAt === 'string')));
}

/** Reuses the application's atomic repository; never stores prompts, tokens or provider payloads. */
export class KlicMemory {
  private state: State = { version: 1, traces: [], preferences: [], events: [], goals: [], actions: [] };
  private repository?: AtomicJsonStore<State>;
  constructor(filename: string | null = path.resolve('.clicko-data/klic.json')) {
    if (filename === null) return;
    const resolved = path.resolve(filename);
    for (const root of ['public', 'dist']) {
      const relative = path.relative(path.resolve(root), resolved);
      if (!relative || (!relative.startsWith('..' + path.sep) && relative !== '..' && !path.isAbsolute(relative))) throw new Error('KLIC_PRIVATE_STORAGE_REQUIRED');
    }
    this.repository = new AtomicJsonStore(resolved, valid);
    const loaded = this.repository.load(this.state);
    this.state = { ...loaded, goals: loaded.goals || [], actions: loaded.actions || [] };
  }
  private save(next: State) { this.repository?.save(next); this.state = next; }
  trace(record: Omit<Trace, 'id' | 'createdAt'>) {
    const trace = { ...record, id: randomUUID(), createdAt: new Date().toISOString() };
    this.save({ ...this.state, traces: [trace, ...this.state.traces].slice(0, 2000) });
    return trace.id;
  }
  traces(scope: KlicScope) { return this.state.traces.filter(t => scopeKey(t) === scopeKey(scope)).slice(0, 50); }
  preferences(scope: KlicScope) { return this.state.preferences.filter(p => scopeKey(p) === scopeKey(scope)).slice(0, 12); }
  remember(scope: KlicScope, key: string, value: string) {
    const item: Preference = { ...identity(scope), id: randomUUID(), key, value, consent: true, updatedAt: new Date().toISOString() };
    this.save({ ...this.state, preferences: [item, ...this.state.preferences.filter(p => scopeKey(p) !== scopeKey(scope) || p.key !== key)].slice(0, 1000) });
    return item;
  }
  forget(scope: KlicScope, key: string) { this.save({ ...this.state, preferences: this.state.preferences.filter(p => scopeKey(p) !== scopeKey(scope) || p.key !== key) }); }
  goals(scope: KlicScope) { return this.state.goals.filter(goal => scopeKey(goal) === scopeKey(scope)).slice(0, 40).map(goal => structuredClone(goal)); }
  setGoal(scope: KlicScope, input: Pick<KlicGoal, 'title' | 'metric' | 'target' | 'period'>) {
    const timestamp = new Date().toISOString();
    const title = input.title.trim();
    const existing = this.state.goals.find(goal => scopeKey(goal) === scopeKey(scope) && goal.status === 'active' && goal.title.toLocaleLowerCase('pt-BR') === title.toLocaleLowerCase('pt-BR'));
    const goal: KlicGoal = existing
      ? { ...existing, ...input, title, source: 'user', updatedAt: timestamp }
      : { ...identity(scope), ...input, id: randomUUID(), title, status: 'active', source: 'user', createdAt: timestamp, updatedAt: timestamp };
    this.save({ ...this.state, goals: [goal, ...this.state.goals.filter(item => item.id !== goal.id)].slice(0, 1000) });
    return structuredClone(goal);
  }
  updateGoal(scope: KlicScope, id: string, status: KlicGoal['status']) {
    const current = this.state.goals.find(goal => goal.id === id && scopeKey(goal) === scopeKey(scope));
    if (!current) return null;
    const goal: KlicGoal = { ...current, status, updatedAt: new Date().toISOString() };
    this.save({ ...this.state, goals: this.state.goals.map(item => item.id === goal.id ? goal : item) });
    return structuredClone(goal);
  }
  preparedAction(scope: KlicScope, idempotencyKey: string) {
    const action = this.state.actions.find(item => scopeKey(item) === scopeKey(scope) && item.idempotencyKey === idempotencyKey);
    return action ? structuredClone(action) : null;
  }
  prepareAction(scope: KlicScope, idempotencyKey: string, actionId: string, resource: KlicRecord) {
    const existing = this.preparedAction(scope, idempotencyKey);
    if (existing) return existing;
    if (resource.workspaceId !== scope.workspaceId || (resource.clientId ?? null) !== scope.clientId) throw new Error('KLIC_ACTION_SCOPE_MISMATCH');
    const action: PreparedAction = { ...identity(scope), id: randomUUID(), idempotencyKey, actionId, status: 'prepared', executed: false, resource: structuredClone(resource), createdAt: new Date().toISOString() };
    this.save({ ...this.state, actions: [action, ...this.state.actions].slice(0, 1000) });
    return structuredClone(action);
  }
  hasEvent(scope: KlicScope, id: string) { return this.state.events.some(e => scopeKey(e) === scopeKey(scope) && e.id === id); }
  event(scope: KlicScope, id: string, type: string) {
    this.save({ ...this.state, events: [{ ...identity(scope), id, type, createdAt: new Date().toISOString() }, ...this.state.events].slice(0, 1000) });
  }
}
