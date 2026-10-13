import { canAccessNavigation } from '../../src/security/accessControl';
import { domainModule, KLIC_DOMAINS, KLIC_MODULES, type KlicActor, type KlicDomain, type KlicEnvelope, type KlicRecord, type KlicRequest } from '../../src/klic/contracts';

export class KlicError extends Error {
  constructor(readonly code: string, readonly status = 400) { super(code); }
}
export function permitted(actor: KlicActor, domain: KlicDomain) {
  if (domain === 'brand' && actor.accountType === 'personal') return canAccessNavigation(actor.user, 'ai-chat', actor.accountType);
  return canAccessNavigation(actor.user, domainModule[domain], actor.accountType);
}
export function checkRequest(actor: KlicActor, body: KlicRequest) {
  if (!body || body.workspaceId !== actor.workspaceId || (body.clientId ?? null) !== actor.clientId) throw new KlicError('KLIC_SCOPE_MISMATCH', 403);
  if (!KLIC_MODULES.includes(body.source)) throw new KlicError('KLIC_MODULE_EXCLUDED', 403);
  if (!canAccessNavigation(actor.user, body.source, actor.accountType)) throw new KlicError('KLIC_PERMISSION_DENIED', 403);
  if (actor.clientId && actor.user.role !== 'master' && !(actor.user.scope?.allClients || actor.user.scope?.clientIds.includes(actor.clientId))) throw new KlicError('KLIC_CLIENT_SCOPE_DENIED', 403);
}
const fields: Record<KlicDomain, string[]> = {
  brand: ['name', 'company', 'segment', 'products', 'services', 'audience', 'positioning', 'toneOfVoice', 'objectives', 'differentiators', 'visualIdentity', 'brandColors', 'typography', 'visualReferences', 'competitors', 'requiredWords', 'forbiddenWords'],
  clients: ['name', 'segment', 'currentObjective', 'positioning', 'status'],
  strategy: ['name', 'objective', 'status', 'startDate', 'endDate'],
  calendar: ['title', 'status', 'scheduledAt', 'createdAt', 'platform', 'objective', 'campaignId'],
  library: ['title', 'type', 'description', 'createdAt', 'updatedAt'],
  analytics: ['metric', 'current', 'previous', 'currentDays', 'previousDays', 'start', 'end', 'previousStart', 'previousEnd', 'dataStatus'],
  connections: [], approvals: [], team: [], history: [],
  automations: ['title', 'isActive', 'updatedAt'],
  radar: [],
};

/** Only task-local, allowlisted scalar data crosses the local-store boundary. */
export function localContext(actor: KlicActor, envelope?: KlicEnvelope): Partial<Record<KlicDomain, KlicRecord[]>> {
  if (!envelope) return {};
  if (envelope.source !== 'browser-local' || envelope.workspaceId !== actor.workspaceId || envelope.userId !== actor.userId || envelope.clientId !== actor.clientId) throw new KlicError('KLIC_CONTEXT_SCOPE_MISMATCH', 403);
  if (!envelope.records || typeof envelope.records !== 'object' || JSON.stringify(envelope).length > 100000) throw new KlicError('KLIC_CONTEXT_TOO_LARGE', 413);
  const result: Partial<Record<KlicDomain, KlicRecord[]>> = {};
  for (const [key, records] of Object.entries(envelope.records)) {
    if (!KLIC_DOMAINS.includes(key as KlicDomain)) throw new KlicError('KLIC_UNKNOWN_CONTEXT');
    const domain = key as KlicDomain;
    if (!Array.isArray(records) || records.length > 80) throw new KlicError('KLIC_CONTEXT_LIMIT', 413);
    if (!permitted(actor, domain)) continue;
    if (!fields[domain].length) continue;
    result[domain] = records.map(record => {
      if (!record || record.workspaceId !== actor.workspaceId || (record.clientId ?? null) !== actor.clientId) throw new KlicError('KLIC_RECORD_SCOPE_MISMATCH', 403);
      const clean: KlicRecord = { workspaceId: actor.workspaceId, clientId: actor.clientId };
      if (typeof record.id === 'string') clean.id = record.id.slice(0, 140);
      for (const field of fields[domain]) {
        const value = record[field];
        if (typeof value === 'string') clean[field] = value.slice(0, domain === 'brand' ? 800 : 300);
        else if (typeof value === 'number' && Number.isFinite(value)) clean[field] = value;
        else if (typeof value === 'boolean') clean[field] = value;
      }
      if (domain === 'library' && ['image', 'video', 'upload'].includes(String(clean.type))) throw new KlicError('KLIC_MEDIA_EXCLUDED', 403);
      return clean;
    });
  }
  return result;
}

export function domainsFor(message: string, source: KlicRequest['source']): KlicDomain[] {
  const domains = new Set<KlicDomain>(['brand']);
  const text = message.toLocaleLowerCase('pt-BR');
  if (source === 'dashboard') ['calendar', 'approvals', 'connections'].forEach(d => domains.add(d as KlicDomain));
  if (source === 'calendar' || /calend|agend|frequência|publica/.test(text)) domains.add('calendar');
  if (source === 'analytics' || /alcance|desempenho|analis|anális|métrica|engajamento/.test(text)) { domains.add('analytics'); domains.add('calendar'); }
  if (source === 'library' || /biblioteca|conteúdo anterior/.test(text)) domains.add('library');
  if (source === 'workspace' || /cliente|empresa/.test(text)) domains.add('clients');
  if (source === 'strategy' || source === 'create-copy' || /campanha|estratég/.test(text)) domains.add('strategy');
  if (source === 'approvals' || /aprova/.test(text)) domains.add('approvals');
  if (source === 'team' || /equipe|responsável/.test(text)) domains.add('team');
  if (source === 'connected-accounts' || /conect|redes sociais/.test(text)) domains.add('connections');
  if (source === 'automations' || /automa/.test(text)) domains.add('automations');
  if (/histórico operacional/.test(text)) domains.add('history');
  if (/radar|tendência|tendencia/.test(text)) domains.add('radar');
  return [...domains];
}
