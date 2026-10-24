import React from 'react';
import { ArrowDown, ArrowLeft, ArrowRight, ArrowUp, CheckCircle2, ChevronDown, Clock3, Copy, GitFork, History, Image, Pause, Pencil, Play, Plus, Search, Send, ShieldCheck, Trash2, X } from 'lucide-react';
import { useOperations } from '../context/OperationsContext';
import { useGovernance } from '../context/GovernanceContext';
import type { NavigationTab } from '../types';
import { CLIENT_OPERATION_REQUIRED, hasClientOperation } from '../clients/clientOperations';
import { useClientOperations } from '../clients/useClientOperations';
import { fromJourney, journeyGoals } from '../automations/journeyCatalog';
import { fromTemplate, makeStep, newFlow, stepHelp, stepNames, templates, uid, validateFlow, type Flow, type FlowLog, type FlowStep, type StepType } from '../automations/automationModel';
import './AutomationWorkspace.css';
import { KlicSymbol } from './KlicSymbol';
import { klicPageScope, useKlicPageDetails } from '../klic/pageContext';

type Tab = 'flows' | 'templates' | 'history';
const icons: Record<StepType, React.ComponentType<{ size?: number }>> = { trigger: Play, ai_generate: KlicSymbol, image_studio: Image, schedule: Clock3, publish: Send, notify: Send, condition: GitFork, wait: Clock3 };
function load<T>(key: string): T[] { try { const value = JSON.parse(localStorage.getItem(key) || '[]'); return Array.isArray(value) ? value : []; } catch { return []; } }
function formatTime(date: string) { return Number.isFinite(Date.parse(date)) ? new Date(date).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' }) : 'Horário indisponível'; }
const duration = (value?: number) => value === undefined ? 'Não registrado' : value < 1 ? 'Menos de 1 ms' : value < 1000 ? `${Math.round(value)} ms` : `${(value / 1000).toFixed(1)} s`;

function Modal({ title, children, onClose }: { title: string; children: React.ReactNode; onClose: () => void }) {
  const ref = React.useRef<HTMLDialogElement>(null);
  const titleId = React.useId();
  React.useEffect(() => { const dialog = ref.current; dialog?.showModal(); return () => dialog?.close(); }, []);
  return <dialog ref={ref} className="au-dialog" aria-labelledby={titleId} onCancel={event => { event.preventDefault(); onClose(); }}><header><h2 id={titleId}>{title}</h2><button className="au-button au-icon" aria-label="Fechar" onClick={onClose}><X /></button></header>{children}</dialog>;
}

function StepEditor({ step, onSave, onClose }: { step: FlowStep; onSave: (step: FlowStep) => void; onClose: () => void }) {
  const [draft, setDraft] = React.useState(step);
  return <Modal title={stepNames[draft.type]} onClose={onClose}><form onSubmit={event => { event.preventDefault(); onSave(draft); }}><p className="au-muted">{stepHelp[draft.type]}</p><label>Nome da etapa<input autoFocus required maxLength={100} value={draft.label} onChange={event => setDraft({ ...draft, label: event.target.value })} /></label><label>{draft.type === 'trigger' ? 'Quando deve começar?' : draft.type === 'ai_generate' ? 'O que a KLIC deve fazer?' : 'O que deve acontecer?'}<textarea required rows={4} maxLength={2000} value={draft.details} onChange={event => setDraft({ ...draft, details: event.target.value })} placeholder={stepHelp[draft.type]} /></label>{draft.type === 'wait' && <label>Tempo de espera (minutos)<input required type="number" min={1} max={525600} value={draft.minutes ?? 60} onChange={event => setDraft({ ...draft, minutes: Number(event.target.value) })} /></label>}<footer><button type="button" className="au-button" onClick={onClose}>Cancelar</button><button className="au-button au-primary" type="submit">Salvar etapa</button></footer></form></Modal>;
}

function LogDetails({ log, onFix }: { key?: string; log: FlowLog; onFix?: () => void }) {
  return <details className="au-log"><summary><span className={`au-log-icon ${log.status === 'blocked' ? 'is-blocked' : ''}`}><ShieldCheck /></span><span><strong>{log.flowTitle || 'Automação'} · {log.status === 'valid' ? 'Validação concluída' : 'Ajuste necessário'}</strong><small>{formatTime(log.createdAt)} · {duration(log.durationMs)}</small></span><ChevronDown /></summary><div className="au-log-body"><p>{log.message}</p>{log.steps?.map(step => <div className="au-log-step" key={step.id}><span className={step.status === 'valid' ? 'au-muted' : 'au-coral'}>{step.status === 'valid' ? <CheckCircle2 /> : <Pencil />}</span><div><strong>{step.label}</strong><p>{step.message}</p><small>{formatTime(step.createdAt)} · {duration(step.durationMs)}</small></div></div>)}{log.status === 'blocked' && onFix && <button className="au-button" onClick={onFix}>Revisar automação<ArrowRight /></button>}<p className="au-muted">Registro de validação da configuração. As ações do fluxo não foram executadas.</p></div></details>;
}

export const AutomationBuilderView: React.FC<{ onNavigate: (tab: NavigationTab) => void }> = ({ onNavigate }) => {
  const { activeWorkspace } = useOperations();
  return <AutomationWorkspace key={activeWorkspace.id} workspaceId={activeWorkspace.id} onNavigate={onNavigate} />;
};

function AutomationWorkspace({ workspaceId, onNavigate }: { workspaceId: string; onNavigate: (tab: NavigationTab) => void; key?: string }) {
  const { connectedAccounts, clients, activeClient } = useOperations();
  const { currentUser } = useGovernance();
  const clientOperations = useClientOperations(workspaceId, currentUser?.id || '');
  const operationByClient = React.useMemo(() => new Map(clientOperations.records.map(record => [record.id, record])), [clientOperations.records]);
  const flowsKey = `clicko:automations:${workspaceId}`;
  const logsKey = `clicko:automation-logs:${workspaceId}`;
  const [flows, setFlows] = React.useState<Flow[]>(() => load<Flow>(flowsKey));
  const [logs, setLogs] = React.useState<FlowLog[]>(() => load<FlowLog>(logsKey));
  const [tab, setTab] = React.useState<Tab>('flows');
  const [search, setSearch] = React.useState('');
  const [status, setStatus] = React.useState('all');
  const [historyFilter, setHistoryFilter] = React.useState('all');
  const [draft, setDraft] = React.useState<Flow | null>(null);
  const [dirty, setDirty] = React.useState(false);
  const [editingStep, setEditingStep] = React.useState<FlowStep | null>(null);
  const [adding, setAdding] = React.useState(false);
  const [confirm, setConfirm] = React.useState<{ type: 'flow' | 'step' | 'discard'; id: string; title: string } | null>(null);
  const [feedback, setFeedback] = React.useState<string | null>(null);
  useKlicPageDetails('automations', klicPageScope(workspaceId, activeClient?.id), {
    view: draft ? 'Editar automação' : tab,
    filters: { busca: search, status, historico: historyFilter },
    selected: draft ? { kind: 'automacao', id: draft.id } : undefined,
  });
  const connected = connectedAccounts.some(account => account.connected && ['connected', 'synced'].includes(account.connectionStatus || ''));
  React.useEffect(() => {
    if (!dirty) return;
    const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ''; };
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, [dirty]);
  function persist(next: Flow[]) { try { localStorage.setItem(flowsKey, JSON.stringify(next)); setFlows(next); return true; } catch { setFeedback('Não foi possível salvar. Verifique o espaço disponível no navegador e tente novamente.'); return false; } }
  function record(log: FlowLog) { const next = [log, ...logs].slice(0, 100); try { localStorage.setItem(logsKey, JSON.stringify(next)); setLogs(next); } catch { setFeedback('A validação terminou, mas o histórico não pôde ser salvo.'); } }
  function open(flow: Flow) { setDraft({ ...flow, nodes: flow.nodes.map(node => ({ ...node })) }); setDirty(false); setAdding(false); setFeedback(null); }
  function change(next: Flow) { setDraft({ ...next, isActive: false }); setDirty(true); }
  function create() { open(newFlow()); setDirty(true); }
  async function operationAllowed(flow: Flow) {
    if (!flow.requiresOperation) return true;
    if (!flow.clientId) { setFeedback('Escolha o cliente desta jornada antes de continuar.'); return false; }
    const selectedClient = clients.find(item => item.id === flow.clientId);
    if (!operationByClient.has(flow.clientId) && selectedClient) {
      try { await clientOperations.mutate('/clients/register', { id: selectedClient.id, name: selectedClient.name }); }
      catch { setFeedback('Não foi possível verificar o cadastro deste cliente no servidor.'); return false; }
    }
    try {
      const response = await fetch(`/api/governance/clients/${encodeURIComponent(flow.clientId)}/operation-access`, { headers: { 'x-workspace-id': workspaceId, 'x-user-id': currentUser?.id || '' }, cache: 'no-store' });
      if (response.ok) return true;
    } catch { /* Fail closed when the licence cannot be verified. */ }
    const kind = ['cost-approval', 'budget-limit'].includes(flow.journeyId || '') ? 'costs' : flow.journeyId === 'period-close' ? 'reports' : 'automations';
    try { await clientOperations.mutate(`/clients/${encodeURIComponent(flow.clientId)}/operation-intents`, { kind }); }
    catch { /* The licence gate remains closed even if the recommendation cannot be recorded. */ }
    setFeedback(CLIENT_OPERATION_REQUIRED);
    return false;
  }
  async function save(flow: Flow, activate = false) {
    if (!flow.title.trim()) { setFeedback('Dê um nome à automação antes de salvar.'); return; }
    if (flow.journeyId && journeyGoals.find(goal => goal.id === flow.journeyId)?.requiresClient && !flow.clientId) { setFeedback('Escolha o cliente desta jornada antes de salvar.'); return; }
    if (!await operationAllowed(flow)) return;
    if (activate) { const log = validateFlow(flow, connected); record(log); if (log.status === 'blocked') { setFeedback(log.message); return; } }
    const next = { ...flow, title: flow.title.trim(), updatedAt: new Date().toISOString(), isActive: activate || flow.isActive };
    if (persist(flows.some(item => item.id === next.id) ? flows.map(item => item.id === next.id ? next : item) : [next, ...flows])) {
      setDraft(next); setDirty(false);
      setFeedback(activate ? 'Configuração ativada. A execução automática depende da conexão dos gatilhos ao executor.' : 'Automação salva neste workspace.');
    }
  }
  async function toggle(flow: Flow) {
    if (!flow.isActive && !await operationAllowed(flow)) return;
    if (!flow.isActive) { const log = validateFlow(flow, connected); record(log); if (log.status === 'blocked') { setFeedback(log.message); return; } }
    const next = { ...flow, isActive: !flow.isActive, updatedAt: new Date().toISOString() };
    if (persist(flows.map(item => item.id === flow.id ? next : item))) { if (draft?.id === flow.id) setDraft(next); setFeedback(flow.isActive ? 'Automação pausada.' : 'Configuração ativada. O executor automático ainda não está conectado.'); }
  }
  function removeConfirmed() {
    if (!confirm) return;
    if (confirm.type === 'discard') { setDraft(null); setDirty(false); }
    if (confirm.type === 'flow') { if (!persist(flows.filter(flow => flow.id !== confirm.id))) return; if (draft?.id === confirm.id) setDraft(null); setFeedback('Automação excluída. O histórico de validações foi preservado.'); }
    if (confirm.type === 'step' && draft) change({ ...draft, nodes: draft.nodes.filter(node => node.id !== confirm.id) });
    setConfirm(null);
  }
  function moveStep(index: number, direction: -1 | 1) {
    if (!draft || index <= 0 || index + direction <= 0 || index + direction >= draft.nodes.length) return;
    const nodes = [...draft.nodes]; [nodes[index], nodes[index + direction]] = [nodes[index + direction], nodes[index]];
    change({ ...draft, nodes });
  }
  const flowState = (flow: Flow) => { const latest = logs.find(log => log.flowId === flow.id); return (flow.requiresOperation && !hasClientOperation(operationByClient.get(flow.clientId || ''))) || latest?.status === 'blocked' ? 'error' : flow.isActive ? 'active' : 'paused'; };
  const shown = flows.filter(flow => flow.title.toLocaleLowerCase('pt-BR').includes(search.toLocaleLowerCase('pt-BR')) && (status === 'all' || flowState(flow) === status));
  const history = logs.filter(log => historyFilter === 'all' || log.status === historyFilter);
  const counts = { active: flows.filter(flow => flowState(flow) === 'active').length, paused: flows.filter(flow => !flow.isActive).length, error: flows.filter(flow => flowState(flow) === 'error').length, runs: flows.reduce((sum, flow) => sum + (flow.executionsCount || 0), 0) };
  return <div className="clicko-automation-workspace"><div className="au-shell">
    <header className="au-header"><div><span className="au-eyebrow">Metodologia Clicko</span><h1>Jornadas Clicko</h1><p>Comece pelo objetivo. A Clicko organiza os sinais, decisões, responsáveis e resultados.</p></div>{!draft && <button className="au-button au-primary" onClick={() => setTab('templates')}><Plus />Escolher objetivo</button>}</header>
    <p className="au-availability"><ShieldCheck />Jornadas podem ser planejadas e validadas. A execução automática ainda não está conectada; nenhuma ação é disparada ao ativar uma configuração.</p>
    {feedback && <div role="status" className="au-feedback"><CheckCircle2 /><span>{feedback}</span><button aria-label="Dispensar mensagem" onClick={() => setFeedback(null)}><X /></button></div>}
    {draft ? <>
      <div className="au-editor-toolbar"><button className="au-text-button" onClick={() => dirty ? setConfirm({ type: 'discard', id: draft.id, title: 'Descartar alterações não salvas?' }) : setDraft(null)}><ArrowLeft />Minhas jornadas</button><span>{dirty ? 'Alterações não salvas' : draft.isActive ? 'Configuração pronta' : 'Rascunho'}</span><button className="au-button" onClick={() => { const log = validateFlow(draft, connected); record(log); setFeedback(log.message); }}><ShieldCheck />Validar</button><button className="au-button" onClick={() => void save(draft)}>Salvar</button><button className="au-button au-primary" onClick={() => void (draft.isActive ? toggle(draft) : save(draft, true))}>{draft.isActive ? <Pause /> : <Play />}{draft.isActive ? 'Pausar' : 'Salvar configuração'}</button></div>
      <div className="au-editor-layout"><section className="au-builder"><label className="au-name-label">Nome da jornada<input aria-label="Nome da jornada" maxLength={100} value={draft.title} onChange={event => change({ ...draft, title: event.target.value })} placeholder="Ex.: Organizar a entrada de um cliente" /></label>
        {draft.journeyId && <><label className="au-client-select">Cliente relacionado<select value={draft.clientId || ''} onChange={event => change({ ...draft, clientId: event.target.value || undefined })}><option value="">Selecione um cliente</option>{clients.map(client => <option key={client.id} value={client.id}>{client.name}</option>)}</select></label>{draft.requiresOperation && !hasClientOperation(operationByClient.get(draft.clientId || '')) && <div className="au-license-warning" role="note"><ShieldCheck /><span>{CLIENT_OPERATION_REQUIRED}</span><button className="au-text-button" onClick={() => onNavigate('workspace')}>Ir para Clientes <ArrowRight /></button></div>}</>}
        <div className="au-flow-intro"><span>Sinal identificado</span><ArrowRight /><span>Decisão</span><ArrowRight /><span>Próxima ação</span></div>
        <ol className="au-steps">{draft.nodes.map((step, index) => { const Icon = icons[step.type] || GitFork; return <li key={step.id}><article className={`au-step ${step.type === 'trigger' ? 'is-trigger' : ''}`}><span className="au-step-icon"><Icon size={step.type === 'ai_generate' ? 24 : undefined} /></span><button className="au-step-copy" onClick={() => setEditingStep(step)}><span>{index === 0 ? 'Quando' : step.type === 'condition' ? 'Se' : step.type === 'wait' ? 'Aguarde' : 'Então'} · {stepNames[step.type]}</span><strong>{step.label}</strong><p>{step.details || 'Clique para configurar esta etapa.'}</p>{step.type === 'wait' && <small>{step.minutes ?? 60} minutos</small>}</button><div className="au-step-tools"><button title="Editar etapa" aria-label={`Editar ${step.label}`} onClick={() => setEditingStep(step)}><Pencil /></button>{index > 0 && <><button disabled={index === 1} aria-label={`Mover ${step.label} para cima`} onClick={() => moveStep(index, -1)}><ArrowUp /></button><button disabled={index === draft.nodes.length - 1} aria-label={`Mover ${step.label} para baixo`} onClick={() => moveStep(index, 1)}><ArrowDown /></button><button aria-label={`Remover ${step.label}`} onClick={() => setConfirm({ type: 'step', id: step.id, title: `Remover “${step.label}”?` })}><Trash2 /></button></>}</div></article></li>; })}</ol>
        {!draft.nodes.some(node => node.type === 'trigger') && <button className="au-button" onClick={() => { const step = makeStep('trigger'); change({ ...draft, nodes: [step, ...draft.nodes] }); setEditingStep(step); }}>Adicionar gatilho</button>}
        <button className="au-add-step" aria-expanded={adding} onClick={() => setAdding(value => !value)}><Plus />Adicionar etapa</button>
        {adding && <div className="au-step-picker">{(Object.keys(stepNames) as StepType[]).filter(type => type !== 'trigger').map(type => { const Icon = icons[type]; return <button key={type} onClick={() => { setEditingStep(makeStep(type)); setAdding(false); }}><Icon size={type === 'ai_generate' ? 24 : undefined} /><span><strong>{stepNames[type]}</strong><small>{stepHelp[type]}</small></span><Plus /></button>; })}</div>}
      </section><aside className="au-editor-aside"><span className="au-eyebrow">Resultado da jornada</span><h2>{draft.nodes.length} etapas</h2><p>{draft.trigger || 'Configure o sinal que inicia esta jornada.'}</p>{draft.journeyId && <div className="au-journey-fields"><label>Responsável<input value={draft.responsible || ''} onChange={event => change({ ...draft, responsible: event.target.value })} /></label><label>Prazo<input value={draft.deadline || ''} onChange={event => change({ ...draft, deadline: event.target.value })} /></label><label>Resultado esperado<textarea rows={2} value={draft.expectedResult || ''} onChange={event => change({ ...draft, expectedResult: event.target.value })} /></label><label>Indicador<input value={draft.indicator || ''} onChange={event => change({ ...draft, indicator: event.target.value })} /></label></div>}<div className="au-aside-note"><ShieldCheck /><p>Ao alterar uma etapa, a configuração é pausada para revisão.</p></div><details><summary>Disponibilidade de execução<ChevronDown /></summary><p>O sistema atual salva e valida configurações. A execução automática dos gatilhos ainda depende de um executor conectado. Condições e esperas ficam salvas no fluxo para essa integração.</p></details><h3>Última validação</h3>{logs.find(log => log.flowId === draft.id) ? <LogDetails log={logs.find(log => log.flowId === draft.id)!} /> : <p>Nenhuma validação registrada.</p>}</aside></div>
    </> : <>
      <div className="au-stats">{[{ label: 'Configurações prontas', value: counts.active, icon: Play }, { label: 'Rascunhos', value: counts.paused, icon: Pause }, { label: 'Precisam de atenção', value: counts.error, icon: Pencil }, { label: 'Execuções registradas', value: counts.runs, icon: History }].map(({ label, value, icon: Icon }) => <div key={label}><span>{label}<Icon /></span><strong>{value}</strong></div>)}</div>
      <nav className="au-tabs" aria-label="Áreas de jornadas">{[{ id: 'flows', label: 'Minhas jornadas' }, { id: 'templates', label: 'Objetivos' }, { id: 'history', label: 'Histórico' }].map(item => <button key={item.id} aria-current={tab === item.id ? 'page' : undefined} onClick={() => setTab(item.id as Tab)}>{item.label}</button>)}</nav>
      {tab === 'flows' && <>
        <div className="au-list-toolbar"><label className="au-search"><Search /><input aria-label="Pesquisar jornadas" placeholder="Pesquisar jornadas" value={search} onChange={event => setSearch(event.target.value)} /></label><select aria-label="Filtrar por status" value={status} onChange={event => setStatus(event.target.value)}><option value="all">Todos os status</option><option value="active">Prontas</option><option value="paused">Rascunhos</option><option value="error">Com pendências</option></select><span>{shown.length} jornadas</span></div>
        {shown.length ? <div className="au-flow-list">{shown.map(flow => { const state = flowState(flow); return <article key={flow.id} className="au-flow-row"><span className="au-flow-icon"><GitFork /></span><button className="au-flow-description" onClick={() => open(flow)}><strong>{flow.title}</strong><p>{flow.trigger}</p><small>{flow.nodes.length} etapas · {flow.lastRun ? `Última execução: ${formatTime(flow.lastRun)}` : 'Sem execução registrada'}</small></button><span className={`au-status ${state}`}>{state === 'active' ? 'Pronta' : state === 'paused' ? 'Rascunho' : 'Revisar licença'}</span><div className="au-row-actions"><button aria-label={`${flow.isActive ? 'Pausar' : 'Preparar'} ${flow.title}`} onClick={() => void toggle(flow)}>{flow.isActive ? <Pause /> : <Play />}</button><button aria-label={`Duplicar ${flow.title}`} onClick={() => { open({ ...flow, id: uid(), title: `${flow.title} — cópia`, isActive: false, executionsCount: 0, lastRun: undefined, nodes: flow.nodes.map(node => ({ ...node, id: uid() })) }); setDirty(true); }}><Copy /></button><button aria-label={`Excluir ${flow.title}`} onClick={() => setConfirm({ type: 'flow', id: flow.id, title: `Excluir “${flow.title}”?` })}><Trash2 /></button></div></article>; })}</div> : <section className="au-empty"><GitFork /><h2>{flows.length ? 'Nenhuma jornada neste filtro' : 'Escolha o resultado que deseja alcançar'}</h2><p>{flows.length ? 'Experimente outro nome ou status.' : 'A Clicko sugere a estrutura e você ajusta apenas o necessário.'}</p>{!flows.length && <div><button className="au-button au-primary" onClick={() => setTab('templates')}>Explorar objetivos<ArrowRight /></button></div>}</section>}
        {logs.length > 0 && <section className="au-recent"><div className="au-between"><h2>Atividade recente</h2><button className="au-text-button" onClick={() => setTab('history')}>Ver histórico<ArrowRight /></button></div>{logs.slice(0, 3).map(log => <LogDetails key={log.id} log={{ ...log, flowTitle: log.flowTitle || flows.find(flow => flow.id === log.flowId)?.title }} onFix={flows.some(flow => flow.id === log.flowId) ? () => open(flows.find(flow => flow.id === log.flowId)!) : undefined} />)}</section>}
      </>}
      {tab === 'templates' && <>
        <div className="au-section-heading"><h2>O que você quer resolver?</h2><p>Escolha um objetivo e revise a jornada sugerida. Cadastrar clientes é gratuito; operar separadamente exige licença ativa.</p></div>
        <div className="au-template-grid">{journeyGoals.map(goal => <article className="au-template au-journey-card" key={goal.id}>
          <span className="au-eyebrow">{goal.category}</span><h2>{goal.title}</h2><p>{goal.objective}</p>
          <details className="au-goal-details"><summary>Ver método da jornada <ChevronDown /></summary><dl>
            <div><dt>Sinal</dt><dd>{goal.signal}</dd></div><div><dt>Decisão</dt><dd>{goal.condition}</dd></div>
            <div><dt>Próxima ação</dt><dd>{goal.action}</dd></div><div><dt>Responsável · prazo</dt><dd>{goal.responsible} · {goal.deadline}</dd></div>
            <div><dt>Resultado · indicador</dt><dd>{goal.expectedResult} · {goal.indicator}</dd></div>
          </dl></details>
          <footer><span>{goal.requiresOperation ? 'Licença operacional necessária' : 'Carteira do assinante'}</span><button className="au-text-button" onClick={() => { open(fromJourney(goal)); setDirty(true); }}>Usar jornada <ArrowRight /></button></footer>
        </article>)}</div>
        <details className="au-legacy-models"><summary>Modelos anteriores <ChevronDown /></summary><p>Fluxos antigos permanecem disponíveis para preservar suas configurações.</p><div className="au-template-grid">{templates.map(template => <article className="au-template" key={template.id}><span className="au-eyebrow">{template.category}</span><h2>{template.title}</h2><p>{template.description}</p><footer><span>{template.steps.length} etapas</span><button className="au-text-button" onClick={() => { open(fromTemplate(template)); setDirty(true); }}>Usar modelo <ArrowRight /></button></footer></article>)}</div><button className="au-button" onClick={create}>Criar fluxo personalizado <Plus /></button></details>
      </>}
      {tab === 'history' && <><div className="au-section-heading"><h2>Histórico de atividade</h2><p>Confira as validações e os ajustes necessários. Nenhuma execução é simulada.</p></div><div className="au-list-toolbar"><select aria-label="Filtrar histórico" value={historyFilter} onChange={event => setHistoryFilter(event.target.value)}><option value="all">Todos os resultados</option><option value="valid">Validações concluídas</option><option value="blocked">Com pendências</option></select><span>{history.length} registros</span></div>{history.length ? history.map(log => <LogDetails key={log.id} log={{ ...log, flowTitle: log.flowTitle || flows.find(flow => flow.id === log.flowId)?.title }} onFix={flows.some(flow => flow.id === log.flowId) ? () => open(flows.find(flow => flow.id === log.flowId)!) : undefined} />) : <section className="au-empty"><History /><h2>Nenhuma atividade por aqui</h2><p>Valide uma automação para conferir o resultado de cada verificação.</p></section>}</>}
    </>}
    {editingStep && draft && <StepEditor step={editingStep} onClose={() => setEditingStep(null)} onSave={step => { const exists = draft.nodes.some(node => node.id === step.id); change({ ...draft, trigger: step.type === 'trigger' ? step.details : draft.trigger, nodes: exists ? draft.nodes.map(node => node.id === step.id ? step : node) : [...draft.nodes, step] }); setEditingStep(null); }} />}
    {confirm && <Modal title={confirm.title} onClose={() => setConfirm(null)}><p className="au-muted">{confirm.type === 'discard' ? 'As mudanças feitas desde o último salvamento serão perdidas.' : confirm.type === 'flow' ? 'A configuração será removida deste workspace. O histórico será mantido.' : 'A etapa será retirada do fluxo. Revise e salve a nova configuração.'}</p><footer><button className="au-button" onClick={() => setConfirm(null)}>Cancelar</button><button className="au-button au-primary" onClick={removeConfirmed}>{confirm.type === 'discard' ? 'Descartar alterações' : 'Remover'}</button></footer></Modal>}
  </div></div>;
}
