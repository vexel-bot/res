import type { AIMemoryEntry, AIContextSnapshot, ClientIntelligenceProfile, Workspace } from '../types';

const hasValue = (value: unknown) => Array.isArray(value)
  ? value.some(item => String(item).trim())
  : Boolean(String(value || '').trim());

const join = (...values: unknown[]) => values
  .flatMap(value => Array.isArray(value) ? value : [value])
  .map(value => String(value || '').trim())
  .filter(Boolean)
  .filter((value, index, all) => all.indexOf(value) === index)
  .join('\n');

export const brandIntelligenceFields: Array<keyof ClientIntelligenceProfile> = [
  'name', 'segment', 'products', 'audience', 'positioning', 'toneOfVoice',
  'visualIdentity', 'brandColors', 'typography', 'visualReferences',
  'differentiators', 'competitors', 'keywords', 'avoidTopics', 'currentObjective',
];

export function brandIntelligenceCompleteness(client: ClientIntelligenceProfile) {
  const completed = brandIntelligenceFields.filter(field => hasValue(client[field])).length;
  return { completed, total: brandIntelligenceFields.length, percent: Math.round(completed / brandIntelligenceFields.length * 100) };
}

/** Builds one tenant/client-safe source of truth for every KLIC surface. */
export function buildBrandIntelligenceContext(ws: Workspace, memory: AIMemoryEntry[], client?: ClientIntelligenceProfile): AIContextSnapshot {
  const durable = memory.filter(entry => (entry.scope === 'recurring' || entry.scope === 'permanent')
    && entry.workspaceId === ws.id
    && (client ? entry.clientId === client.id : !entry.clientId));
  const find = (patterns: RegExp[], category?: AIMemoryEntry['category']) => durable.find(entry => (!category || entry.category === category)
    && patterns.some(pattern => pattern.test(`${entry.label} ${entry.value}`.toLocaleLowerCase('pt-BR'))))?.value || '';
  const identity = durable.filter(entry => entry.category === 'identity').map(entry => entry.value).join('\n');
  return {
    workspaceId: ws.id,
    revision: Math.max(1, durable.reduce((total, entry) => total + entry.occurrences, 0)),
    company: client?.name || find([/identidade/, /empresa/, /posicionamento/], 'identity') || identity || ws.name,
    products: client?.products || find([/produto/, /oferta/], 'content'),
    services: find([/serviço/, /entrega/], 'content'),
    visualIdentity: join(client?.visualIdentity, client?.brandColors?.join(', '), client?.typography, client?.visualReferences)
      || find([/visual/, /estética/, /cor/], 'visual'),
    toneOfVoice: client?.toneOfVoice || find([/tom de voz/, /comunicação/, /linguagem/], 'communication') || ws.brandProfile.tone || '',
    audience: client?.audience || find([/público/, /audiência/, /persona/], 'identity') || ws.brandProfile.targetAudience || '',
    personas: find([/persona/], 'identity'),
    objectives: client?.currentObjective || find([/objetivo/, /meta/, /prioridade/], 'content'),
    differentiators: client?.differentiators || client?.positioning || find([/diferencial/, /posicionamento/], 'identity'),
    competitors: client?.competitors || find([/concorrent/], 'identity'),
    objections: find([/objeção/], 'content'),
    pains: find([/dor/, /problema/], 'content'),
    desires: find([/desejo/, /transformação/], 'content'),
    faq: find([/faq/, /pergunta recorrente/], 'content'),
    requiredWords: client?.keywords || find([/palavra obrigatória/, /termo obrigatório/], 'communication'),
    forbiddenWords: client?.avoidTopics || find([/evitar/, /proibida/, /não usar/], 'communication'),
    history: join(client?.notes, ...durable.map(entry => `${entry.label}: ${entry.value}`)),
  };
}
