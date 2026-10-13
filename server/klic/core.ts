import { randomUUID } from 'node:crypto';
import { scopeKey, type KlicActor, type KlicDomain, type KlicRequest, type KlicSource, type KlicAnalysis } from '../../src/klic/contracts';
import { checkRequest, domainsFor, KlicError, localContext, permitted } from './context';
import { KlicMemory } from './store';
import { recommend } from './recommendations';
import type { RadarSnapshot } from '../radar';

type Task = { actor: KlicActor; request: KlicRequest; local: ReturnType<typeof localContext>; traceId: string };
type ToolResult = KlicSource & { radar?: RadarSnapshot };
export type KlicTool = { id: string; domain: KlicDomain; effect: 'read' | 'draft' | 'external'; run: (task: Task, input?: unknown) => Promise<ToolResult> | ToolResult };
type Event = { id: string; type: string; actor: KlicActor; request: KlicRequest };
export class KlicEventBus {
  private listeners = new Set<(event: Event) => Promise<void>>();
  subscribe(listener: (event: Event) => Promise<void>) { this.listeners.add(listener); return () => this.listeners.delete(listener); }
  async publish(event: Event) {
    const results = await Promise.allSettled([...this.listeners].map(listener => Promise.resolve().then(() => listener(event))));
    return results.every(result => result.status === 'fulfilled');
  }
}
export class KlicCore {
  readonly events = new KlicEventBus();
  private tools = new Map<string, KlicTool>();
  private runningEvents = new Set<string>();
  private analyses = new Map<string, { createdAt: number; analysis: KlicAnalysis }>();
  constructor(readonly memory: KlicMemory) {
    this.events.subscribe(async event => { await this.analyze(event.actor, event.request); });
  }
  register(tool: KlicTool) {
    if (this.tools.has(tool.id)) throw new Error('KLIC_DUPLICATE_TOOL');
    this.tools.set(tool.id, tool);
  }
  catalog(actor: KlicActor) { return [...this.tools.values()].filter(t => permitted(actor, t.domain)).map(({ id, domain, effect }) => ({ id, domain, effect })); }
  task(actor: KlicActor, request: KlicRequest): Task {
    checkRequest(actor, request);
    return { actor, request, local: localContext(actor, request.context), traceId: randomUUID() };
  }
  async run(task: Task, toolId: string, input?: unknown): Promise<ToolResult> {
    const started = Date.now();
    const tool = this.tools.get(toolId);
    if (!tool) throw new KlicError('KLIC_UNKNOWN_TOOL', 404);
    let status: 'ok' | 'denied' | 'unavailable' | 'error' = 'ok';
    let errorCode: string | undefined;
    let result: ToolResult;
    try {
      if (!permitted(task.actor, tool.domain)) throw new KlicError('KLIC_PERMISSION_DENIED', 403);
      // No blanket confirmed=true flag can bypass the owning module's approval flow.
      if (tool.effect === 'external') throw new KlicError('KLIC_USE_MODULE_CONFIRMATION', 409);
      let timer: ReturnType<typeof setTimeout>;
      try {
        result = await Promise.race([
          Promise.resolve().then(() => tool.run(task, input)),
          new Promise<never>((_, reject) => { timer = setTimeout(() => reject(new KlicError('KLIC_SERVICE_TIMEOUT', 503)), 12000); }),
        ]);
      } finally { clearTimeout(timer!); }
      if (result.records.some(record => record.workspaceId !== task.actor.workspaceId || (record.clientId ?? null) !== task.actor.clientId)) throw new KlicError('KLIC_ADAPTER_SCOPE_MISMATCH', 403);
      if (result.status === 'unavailable') status = 'unavailable';
    } catch (error) {
      status = error instanceof KlicError && [403, 409].includes(error.status) ? 'denied' : 'error';
      errorCode = error instanceof KlicError ? error.code : 'KLIC_SERVICE_UNAVAILABLE';
      result = { domain: tool.domain, provenance: 'service', status: status === 'denied' ? 'denied' : 'unavailable', records: [], reason: errorCode };
    }
    this.memory.trace({ workspaceId: task.actor.workspaceId, userId: task.actor.userId, clientId: task.actor.clientId, parentId: task.traceId, origin: task.request.source, tool: tool.id, status, durationMs: Date.now() - started, recordCount: result.records.length, errorCode });
    return result;
  }
  async collect(task: Task) {
    const domains = domainsFor(task.request.message || '', task.request.source);
    return Promise.all(domains.map(async domain => {
      const { radar, ...source } = await this.run(task, domain + '.read');
      return source;
    }));
  }
  async analyze(actor: KlicActor, request: KlicRequest): Promise<KlicAnalysis> {
    const task = this.task(actor, request);
    const sources = await this.collect(task);
    const recommendations = recommend(sources);
    this.memory.trace({ workspaceId: actor.workspaceId, userId: actor.userId, clientId: actor.clientId, parentId: task.traceId, origin: request.source, tool: 'recommendations.build', status: 'ok', durationMs: 0, recordCount: recommendations.length });
    const analysis: KlicAnalysis = { traceId: task.traceId, recommendations, sources: sources.map(({ records, ...source }) => source), insight: recommendations.map(r => r.text).join('\n\n') || 'Não há evidências suficientes no contexto autorizado para recomendar uma mudança operacional.' };
    const key = JSON.stringify([scopeKey(actor), request.source]);
    this.analyses.delete(key);
    this.analyses.set(key, { createdAt: Date.now(), analysis });
    while (this.analyses.size > 200) this.analyses.delete(this.analyses.keys().next().value!);
    return analysis;
  }
  /** Ephemeral, permission-checked output for existing insight surfaces; never a raw data cache. */
  latest(actor: KlicActor, request: KlicRequest): KlicAnalysis | null {
    this.task(actor, request);
    const key = JSON.stringify([scopeKey(actor), request.source]);
    const entry = this.analyses.get(key);
    if (!entry) return null;
    if (Date.now() - entry.createdAt > 5 * 60000 || entry.analysis.sources.some(source => !permitted(actor, source.domain))) {
      this.analyses.delete(key);
      return null;
    }
    return structuredClone(entry.analysis);
  }
  async event(event: Event) {
    this.task(event.actor, event.request);
    const key = scopeKey(event.actor) + event.id;
    if (this.runningEvents.has(key) || this.memory.hasEvent(event.actor, event.id)) return { duplicate: true, processed: true };
    this.runningEvents.add(key);
    try {
      this.memory.trace({ workspaceId: event.actor.workspaceId, userId: event.actor.userId, clientId: event.actor.clientId, origin: event.request.source, tool: 'event.' + event.type, status: 'ok', durationMs: 0, recordCount: 1 });
      const processed = await this.events.publish(event);
      if (processed) this.memory.event(event.actor, event.id, event.type);
      return { duplicate: false, processed };
    } finally { this.runningEvents.delete(key); }
  }
}
