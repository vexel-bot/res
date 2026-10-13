import type { AutomationFlow, AutomationNode } from '../types';

export type StepType = AutomationNode['type'] | 'condition' | 'wait';
export type FlowStep = Omit<AutomationNode, 'type'> & { type: StepType; minutes?: number };
export type Flow = Omit<AutomationFlow, 'nodes'> & { nodes: FlowStep[]; updatedAt: string; journeyId?: string; clientId?: string; responsible?: string; deadline?: string; expectedResult?: string; indicator?: string; requiresOperation?: boolean };
export type CheckStep = { id: string; label: string; createdAt: string; durationMs: number; status: 'valid' | 'blocked'; message: string };
export type FlowLog = { id: string; flowId: string; flowTitle?: string; kind?: 'validation'; status: 'valid' | 'blocked'; message: string; createdAt: string; durationMs?: number; steps?: CheckStep[] };
export const stepNames: Record<StepType, string> = { trigger: 'Quando acontecer', ai_generate: 'Pedir à KLIC', image_studio: 'Preparar criação visual', schedule: 'Agendar conteúdo', publish: 'Publicar conteúdo', notify: 'Notificar equipe', condition: 'Verificar condição', wait: 'Aguardar' };
export const stepHelp: Record<StepType, string> = { trigger: 'Descreva o evento que inicia este fluxo.', ai_generate: 'Explique o que a KLIC deve produzir ou analisar.', image_studio: 'Descreva a imagem ou o material visual desejado.', schedule: 'Defina o conteúdo e o momento de agendamento.', publish: 'Informe a rede conectada e o conteúdo a publicar.', notify: 'Indique quem deve receber a informação e qual mensagem.', condition: 'Descreva o requisito para continuar. Se não for atendido, o fluxo deve parar.', wait: 'Defina o intervalo antes da próxima etapa.' };
export const uid = () => crypto.randomUUID();
export const makeStep = (type: StepType, label = '', details = ''): FlowStep => ({ id: uid(), type, label: label || stepNames[type], details, ...(type === 'wait' ? { minutes: 60 } : {}) });
export const newFlow = (): Flow => ({ id: uid(), title: '', trigger: '', nodes: [makeStep('trigger')], isActive: false, executionsCount: 0, updatedAt: new Date().toISOString() });
type Template = { id: string; title: string; category: string; description: string; steps: Array<{ type: StepType; label: string; details: string; minutes?: number }> };
export const templates: Template[] = [
  { id: 'approval', title: 'Da aprovação ao calendário', category: 'Conteúdo', description: 'Prepare o agendamento assim que um conteúdo for aprovado.', steps: [{ type: 'trigger', label: 'Conteúdo aprovado', details: 'Quando um conteúdo receber aprovação final.' }, { type: 'schedule', label: 'Organizar a publicação', details: 'Agendar o conteúdo aprovado no próximo horário definido no calendário.' }, { type: 'notify', label: 'Avisar a equipe', details: 'Informar à equipe que o conteúdo foi agendado.' }] },
  { id: 'ideas', title: 'Ideias para a próxima semana', category: 'KLIC', description: 'Um ponto de partida para planejar a produção com a KLIC.', steps: [{ type: 'trigger', label: 'Início da semana', details: 'Toda segunda-feira às 09h, no fuso do workspace.' }, { type: 'ai_generate', label: 'Sugerir ideias', details: 'Criar cinco ideias de conteúdo alinhadas à marca para revisão da equipe.' }, { type: 'notify', label: 'Enviar para revisão', details: 'Notificar a equipe sobre as ideias disponíveis para revisão.' }] },
  { id: 'report', title: 'Aprender com os resultados', category: 'Analytics', description: 'Transforme as métricas sincronizadas em uma leitura acionável.', steps: [{ type: 'trigger', label: 'Analytics atualizado', details: 'Quando novas métricas forem sincronizadas.' }, { type: 'condition', label: 'Há dados suficientes?', details: 'Continuar apenas quando existirem dados comparáveis de dois períodos.' }, { type: 'ai_generate', label: 'Analisar resultados', details: 'Analisar os dados do Analytics e recomendar a principal melhoria sem inventar métricas.' }, { type: 'notify', label: 'Compartilhar a leitura', details: 'Enviar o resumo à equipe responsável pelo conteúdo.' }] },
  { id: 'publish', title: 'Publicação com revisão', category: 'Publicação', description: 'Valide a aprovação antes de encaminhar o conteúdo à rede.', steps: [{ type: 'trigger', label: 'Horário de publicação', details: 'Quando chegar o horário previsto no calendário.' }, { type: 'condition', label: 'Conteúdo aprovado', details: 'Continuar somente se o conteúdo estiver aprovado e a conta conectada.' }, { type: 'publish', label: 'Publicar na rede', details: 'Publicar o conteúdo aprovado na rede definida no agendamento.' }] },
  { id: 'visual', title: 'Do briefing à criação visual', category: 'Criação', description: 'Organize o conceito e o material visual em um único fluxo.', steps: [{ type: 'trigger', label: 'Briefing disponível', details: 'Quando um novo briefing de conteúdo estiver pronto.' }, { type: 'ai_generate', label: 'Preparar conceito', details: 'Criar um conceito visual e um prompt a partir do briefing e da identidade da marca.' }, { type: 'image_studio', label: 'Preparar imagem', details: 'Encaminhar o conceito para preparação no estúdio de imagem.' }] },
  { id: 'followup', title: 'Lembrete de revisão', category: 'Equipe', description: 'Dê tempo para a revisão e lembre a equipe quando necessário.', steps: [{ type: 'trigger', label: 'Conteúdo enviado para revisão', details: 'Quando um conteúdo entrar em revisão.' }, { type: 'wait', label: 'Aguardar um dia', details: 'Aguardar antes de verificar a revisão.', minutes: 1440 }, { type: 'condition', label: 'Revisão pendente', details: 'Continuar apenas se o conteúdo ainda aguardar revisão.' }, { type: 'notify', label: 'Lembrar responsáveis', details: 'Notificar os responsáveis pela aprovação pendente.' }] },
];
export function fromTemplate(template: Template): Flow {
  return { ...newFlow(), title: template.title, trigger: template.steps[0].details, nodes: template.steps.map(step => ({ ...step, id: uid() })) };
}
export function validateFlow(flow: Flow, connected: boolean): FlowLog {
  const started = performance.now();
  const steps: CheckStep[] = [];
  const check = (label: string, valid: boolean, success: string, error: string) => {
    const at = performance.now();
    steps.push({ id: uid(), label, createdAt: new Date().toISOString(), durationMs: performance.now() - at, status: valid ? 'valid' : 'blocked', message: valid ? success : error });
  };
  check('Nome e início', Boolean(flow.title.trim() && flow.trigger.trim()), 'Nome e evento de início definidos.', 'Informe o nome e o evento que inicia a automação.');
  check('Ordem do fluxo', flow.nodes[0]?.type === 'trigger' && flow.nodes.filter(step => step.type === 'trigger').length === 1, 'Um gatilho inicia o fluxo.', 'Mantenha um único gatilho na primeira posição.');
  check('Ações', flow.nodes.some(step => !['trigger','condition','wait'].includes(step.type)), 'O fluxo possui uma ação.', 'Adicione pelo menos uma ação depois do gatilho.');
  flow.nodes.forEach(step => check(step.label || stepNames[step.type], Boolean(step.label.trim() && step.details.trim() && (step.type !== 'wait' || (Number.isFinite(step.minutes) && step.minutes! > 0))), 'Configuração preenchida.', step.type === 'wait' ? 'Informe uma espera maior que zero e descreva a etapa.' : 'Preencha o nome e os detalhes desta etapa.'));
  check('Conexão para publicar', !flow.nodes.some(step => step.type === 'publish') || connected, 'Dependência de publicação verificada.', 'Conecte e sincronize uma rede em Conexões antes de ativar a publicação.');
  const firstError = steps.find(step => step.status === 'blocked');
  return { id: uid(), flowId: flow.id, flowTitle: flow.title, kind: 'validation', createdAt: new Date().toISOString(), durationMs: performance.now() - started, steps, status: firstError ? 'blocked' : 'valid', message: firstError?.message || 'Estrutura validada. Nenhuma ação foi executada nesta verificação.' };
}

export function parseSuggestion(reply: string): Flow {
  const clean = reply.trim().replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/, '');
  const value: unknown = JSON.parse(clean);
  if (!value || typeof value !== 'object') throw new Error('A KLIC não retornou um fluxo completo. Tente descrever o evento e o resultado desejado.');
  const rawNodes = Reflect.get(value, 'nodes');
  if (typeof Reflect.get(value, 'title') !== 'string' || typeof Reflect.get(value, 'trigger') !== 'string' || !Array.isArray(rawNodes) || rawNodes.length < 2 || rawNodes.length > 20) throw new Error('A KLIC não retornou um fluxo completo. Tente descrever o evento e o resultado desejado.');
  const title = Reflect.get(value, 'title') as string;
  const trigger = Reflect.get(value, 'trigger') as string;
  const nodes: FlowStep[] = rawNodes.map((candidate: unknown) => {
    if (!candidate || typeof candidate !== 'object') throw new Error('A sugestão contém uma etapa incompatível. Tente novamente.');
    const node = candidate as Record<string, unknown>;
    const type = node.type;
    if (typeof type !== 'string' || !Object.hasOwn(stepNames, type) || typeof node.label !== 'string' || typeof node.details !== 'string') throw new Error('A sugestão contém uma etapa incompatível. Tente novamente.');
    if (!node.label.trim() || !node.details.trim()) throw new Error('A sugestão contém etapas sem descrição. Tente novamente.');
    if (type === 'wait' && (typeof node.minutes !== 'number' || !Number.isInteger(node.minutes) || node.minutes < 1 || node.minutes > 525600)) throw new Error('A sugestão contém um tempo de espera inválido. Tente novamente.');
    return { id: uid(), type: type as StepType, label: node.label.slice(0,100), details: node.details.slice(0,2000), ...(type === 'wait' ? { minutes: node.minutes as number } : {}) };
  });
  if (nodes[0].type !== 'trigger' || nodes.filter(node => node.type === 'trigger').length !== 1) throw new Error('A sugestão precisa começar com um único gatilho. Tente novamente.');
  if (!title.trim() || !trigger.trim() || !nodes.some(node => !['trigger', 'wait', 'condition'].includes(node.type))) throw new Error('A sugestão precisa de nome, gatilho e pelo menos uma ação. Tente novamente.');
  return { ...newFlow(), title: title.slice(0,100), trigger: trigger.slice(0,2000), nodes };
}
