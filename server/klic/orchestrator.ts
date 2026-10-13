import { hasPermission } from '../../src/security/accessControl';
import type {
  KlicActionSuggestion,
  KlicActor,
  KlicIntent,
  KlicOrchestration,
  KlicPlanStage,
  KlicRequest,
  KlicSource,
  KlicStage,
} from '../../src/klic/contracts';
import type { NavigationTab } from '../../src/types';
import type { KlicCore } from './core';
import { checkedPageContext } from './pageContext';
import { recommend } from './recommendations';

const normalized = (value: string) => value.toLocaleLowerCase('pt-BR').normalize('NFD').replace(/[\u0300-\u036f]/g, '');

export function inferKlicIntent(message: string): KlicIntent {
  const text = normalized(message);
  if (/\b(excluir|deletar|remover membro|desconectar|transferir titular|alterar permiss|mudar permiss|cancelar assinatura|alterar assinatura)\b/.test(text)) return 'execution';
  if (/\b(agend|publicar|publique|poste|enviar? .*aprov|mande .*aprov|ativar? .*autom|iniciar? .*autom|execut|resolver isso)\b/.test(text)) return 'execution';
  if (/\b(organize|planeje|planejar|distribua|calendario|proxima semana|sequencia|campanha)\b/.test(text)) return 'organization';
  if (/\b(crie|criar|prepare|preparar|refaca|reescreva|legenda|roteiro|conteudo|imagem|video|variac)\b/.test(text)) return 'creation';
  if (/\b(resultado|metrica|desempenho|alcance|engajamento|cresceu|caiu|queda|melhor|pior|medir)\b/.test(text)) return 'measurement';
  if (/\b(aprenda|lembre|memorize|preferencia|tom de voz|sempre|nunca)\b/.test(text)) return 'learning';
  if (/\b(analise|analisar|compare|comparar|por que|tendencia|diagnost)\b/.test(text)) return 'analysis';
  return 'question';
}

function destinationFor(message: string, source: NavigationTab): NavigationTab {
  const text = normalized(message);
  if (/\b(video|reel|short|tiktok|roteiro)\b/.test(text)) return 'create-video';
  if (/\b(imagem|carrossel|arte|criativo visual)\b/.test(text)) return 'create-image';
  if (/\b(aprov)\b/.test(text)) return 'approvals';
  if (/\b(autom)\b/.test(text)) return 'automations';
  if (/\b(agenda|calend|semana|horario|publica)\b/.test(text)) return 'calendar';
  if (/\b(alcance|engajamento|metrica|desempenho|resultado|queda|cresceu)\b/.test(text)) return 'analytics';
  if (/\b(cliente|marca)\b/.test(text)) return 'workspace';
  if (/\b(campanha|estrateg|objetivo|meta)\b/.test(text)) return 'strategy';
  return source === 'dashboard' ? 'ai-chat' : source;
}

function requestedAction(actor: KlicActor, message: string, source: NavigationTab, intent: KlicIntent): KlicActionSuggestion | null {
  const text = normalized(message);
  const destination = destinationFor(message, source);
  if (/\b(excluir|deletar)\b/.test(text)) return { actionId: 'resource.delete.request', label: 'Revisar exclusão', destination, risk: 'critical', requiresConfirmation: true, reason: 'Exclusões permanentes exigem confirmação explícita no módulo responsável.' };
  if (/\b(desconectar)\b/.test(text)) return { actionId: 'connections.disconnect.request', label: 'Revisar desconexão', destination: 'connected-accounts', risk: 'critical', requiresConfirmation: true, reason: 'Desconectar uma conta interrompe sincronizações e publicações futuras.' };
  if (/\b(remover membro|transferir titular|alterar permiss|mudar permiss)\b/.test(text)) return { actionId: 'team.access.request', label: 'Revisar acesso da equipe', destination: 'team', risk: 'critical', requiresConfirmation: true, reason: 'Mudanças de acesso e titularidade exigem confirmação explícita.' };
  if (/\b(assinatura|mudar plano|cancelar plano)\b/.test(text)) return { actionId: 'subscription.change.request', label: 'Revisar assinatura', destination: 'subscription', risk: 'critical', requiresConfirmation: true, reason: 'Alterações financeiras nunca são executadas sem confirmação.' };
  if (/\b(publicar agora|publique agora|poste agora)\b/.test(text)) return { actionId: 'publication.publish.request', label: 'Revisar publicação', destination: 'calendar', risk: 'external', requiresConfirmation: true, reason: 'Publicações externas relevantes exigem confirmação antes do envio.' };
  if (/\b(agend|enviar? .*aprov|mande .*aprov|ativar? .*autom|iniciar? .*autom)\b/.test(text)) return { actionId: destination === 'approvals' ? 'approvals.submit.request' : destination === 'automations' ? 'automations.start.request' : 'publication.schedule.request', label: destination === 'approvals' ? 'Preparar envio para aprovação' : destination === 'automations' ? 'Revisar ativação' : 'Preparar agendamento', destination, risk: 'external', requiresConfirmation: true, reason: 'A ação altera o fluxo operacional e será confirmada antes da execução.' };
  if (intent === 'organization' && hasPermission(actor.user, 'content.create')) return { actionId: 'calendar.draft.prepare', label: 'Preparar plano no calendário', destination: 'calendar', risk: 'reversible', requiresConfirmation: false };
  if (intent === 'creation' && hasPermission(actor.user, 'content.create')) return { actionId: 'content.draft.prepare', label: destination === 'create-video' ? 'Preparar no Vídeo' : destination === 'create-image' ? 'Preparar na Imagem' : 'Preparar conteúdo', destination, risk: 'reversible', requiresConfirmation: false };
  if (/\b(objetivo|meta)\b/.test(text)) return { actionId: 'goals.manage', label: 'Revisar objetivos', destination: 'strategy', risk: 'reversible', requiresConfirmation: false };
  return null;
}

const stageSummary: Record<KlicStage, string> = {
  understand: 'Intenção, escopo, tela atual e permissões foram interpretados.',
  analyze: 'As fontes autorizadas relevantes foram cruzadas sem assumir dados ausentes.',
  create: 'A criação pode ser preparada com as ferramentas existentes da Clicko.',
  organize: 'A organização será estruturada antes de alterar calendário ou fluxos.',
  execute: 'A execução depende do risco, das permissões e da confirmação aplicável.',
  measure: 'Os resultados disponíveis serão separados de hipóteses e recomendações.',
  learn: 'Somente objetivos e memórias isolados neste escopo podem orientar próximos ciclos.',
};

function stagesFor(intent: KlicIntent, sources: KlicSource[], action: KlicActionSuggestion | null, hasGoals: boolean): KlicPlanStage[] {
  const analyzed = sources.some(source => source.status === 'available' || source.status === 'empty');
  const tools = sources.map(source => `${source.domain}.read`);
  const enabled = new Set<KlicStage>(['understand', 'analyze']);
  if (intent === 'creation') enabled.add('create');
  if (intent === 'organization' || intent === 'creation' || intent === 'execution') enabled.add('organize');
  if (intent === 'execution' || action) enabled.add('execute');
  if (intent === 'analysis' || intent === 'measurement') enabled.add('measure');
  if (intent === 'learning' || hasGoals) enabled.add('learn');
  return (['understand', 'analyze', 'create', 'organize', 'execute', 'measure', 'learn'] as KlicStage[]).map(stage => {
    let status: KlicPlanStage['status'] = enabled.has(stage) ? 'ready' : 'skipped';
    if (stage === 'understand') status = 'completed';
    if (stage === 'analyze') status = analyzed ? 'completed' : 'blocked';
    if (stage === 'execute' && action?.requiresConfirmation) status = 'awaiting_confirmation';
    return { stage, status, summary: stageSummary[stage], toolIds: stage === 'analyze' || stage === 'measure' ? tools : stage === 'execute' && action ? [action.actionId] : [] };
  });
}

export async function orchestrateKlic(core: KlicCore, actor: KlicActor, request: KlicRequest, rawPageContext?: unknown) {
  const text = normalized(request.message || '');
  const aggregateRequested = /\b(todos os|todas as|meus|minhas|carteira de)\b.{0,40}\bclientes?\b|\bclientes?\b.{0,40}\b(todos|todas|sem conteudo|aguardando aprovacao|pior desempenho)\b/.test(text);
  const canAggregate = actor.user.role === 'master' || actor.user.scope?.allClients === true || Boolean(actor.user.scope?.clientIds.length);
  const scopeMode: KlicOrchestration['scopeMode'] = aggregateRequested && canAggregate ? 'workspace' : 'client';
  const scopedActor = scopeMode === 'workspace' ? { ...actor, clientId: null } : actor;
  // Aggregate analysis deliberately excludes browser-local client snapshots. Only
  // workspace services may contribute multi-client evidence.
  const scopedRequest: KlicRequest = scopeMode === 'workspace'
    ? { ...request, clientId: null, context: undefined, pageContext: undefined }
    : request;
  const task = core.task(scopedActor, scopedRequest);
  const sources = await core.collect(task);
  const page = scopeMode === 'workspace' ? null : checkedPageContext(scopedActor, scopedRequest.source, rawPageContext ?? scopedRequest.pageContext, sources);
  const intent = inferKlicIntent(scopedRequest.message || '');
  const recommendations = recommend(sources);
  const goals = core.memory.goals(scopedActor).filter(goal => goal.status === 'active');
  let requested = requestedAction(scopedActor, scopedRequest.message || '', scopedRequest.source, intent);
  if (scopeMode === 'workspace' && requested && requested.risk === 'reversible') requested = {
    actionId: 'bulk.plan.review', label: 'Revisar plano por cliente', destination: requested.destination,
    risk: 'external', requiresConfirmation: true,
    reason: 'Operações em vários clientes exigem revisão da carga, dependências, dados disponíveis e limites antes da execução.',
  };
  const recommendationActions: KlicActionSuggestion[] = recommendations.filter(item => item.destination).slice(0, 3).map(item => ({
    actionId: `klic.review.${item.id}`,
    label: item.destination === 'approvals' ? 'Revisar aprovações' : item.destination === 'calendar' ? 'Abrir calendário' : item.destination === 'analytics' ? 'Analisar resultados' : 'Aprofundar análise',
    destination: item.destination!, risk: 'read', requiresConfirmation: false,
  }));
  const actions = [requested, ...recommendationActions].filter((item): item is KlicActionSuggestion => Boolean(item))
    .filter((item, index, all) => all.findIndex(candidate => candidate.actionId === item.actionId) === index);
  const stages = stagesFor(intent, sources, requested, goals.length > 0);
  const status: KlicOrchestration['status'] = stages.some(stage => stage.status === 'awaiting_confirmation') ? 'awaiting_confirmation'
    : stages.find(stage => stage.stage === 'analyze')?.status === 'blocked' ? 'blocked'
      : actions.some(action => action.risk === 'reversible') ? 'planned' : 'completed';
  const plan: KlicOrchestration = {
    traceId: task.traceId, intent, source: scopedRequest.source, scopeMode, page, status, stages, actions,
    goals: goals.map(({ id, title, metric, target, period, status: goalStatus }) => ({ id, title, metric, target, period, status: goalStatus })),
    evidence: sources.map(({ records, ...source }) => source),
  };
  for (const stage of stages.filter(item => item.status !== 'skipped')) core.memory.trace({
    workspaceId: scopedActor.workspaceId, userId: scopedActor.userId, clientId: scopedActor.clientId, parentId: task.traceId,
    origin: scopedRequest.source, tool: `orchestrator.${stage.stage}`, status: stage.status === 'blocked' ? 'unavailable' : stage.status === 'awaiting_confirmation' ? 'denied' : 'ok',
    durationMs: 0, recordCount: stage.toolIds.length,
  });
  return { plan, sources, recommendations };
}
