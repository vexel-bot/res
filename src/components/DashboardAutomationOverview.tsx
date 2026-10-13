import React from 'react';
import { ArrowRight, Bell, CalendarDays, Check, CircleAlert, Clock3, GitBranch, Image as ImageIcon, Send, Workflow, Zap } from 'lucide-react';
import type { NavigationTab } from '../types';
import { stepNames, type Flow, type FlowLog, type FlowStep, type StepType } from '../automations/automationModel';
import { KlicSymbol } from './KlicSymbol';

type Props = { workspaceId: string; onNavigate: (tab: NavigationTab) => void };
type Snapshot = { workspaceId: string; flows: Flow[]; logs: FlowLog[] };
const nodeIcons: Record<StepType, React.ComponentType<{ size?: number; 'aria-hidden'?: boolean | 'true' | 'false' }>> = { trigger: Zap, condition: GitBranch, wait: Clock3, ai_generate: KlicSymbol, image_studio: ImageIcon, schedule: CalendarDays, publish: Send, notify: Bell };
const demonstration = [
  { id: 'demo-trigger', type: 'trigger', label: 'Conteúdo aprovado', details: 'Exemplo de evento inicial.' },
  { id: 'demo-condition', type: 'condition', label: 'Verificar condição', details: 'Exemplo de uma condição antes da ação.' },
  { id: 'demo-schedule', type: 'schedule', label: 'Agendar conteúdo', details: 'Exemplo de ação no calendário.' },
  { id: 'demo-notify', type: 'notify', label: 'Avisar a equipe', details: 'Exemplo de notificação.' },
] satisfies FlowStep[];

function readSnapshot(workspaceId: string): Snapshot {
  try {
    const flows: unknown = JSON.parse(localStorage.getItem(`clicko:automations:${workspaceId}`) || '[]');
    const logs: unknown = JSON.parse(localStorage.getItem(`clicko:automation-logs:${workspaceId}`) || '[]');
    return {
      workspaceId,
      flows: Array.isArray(flows) ? flows.filter((item): item is Flow => Boolean(item && typeof item.id === 'string' && typeof item.title === 'string' && typeof item.isActive === 'boolean')) : [],
      logs: Array.isArray(logs) ? logs.filter((item): item is FlowLog => Boolean(item && typeof item.flowId === 'string' && typeof item.createdAt === 'string' && ['valid', 'blocked'].includes(item.status))) : [],
    };
  } catch { return { workspaceId, flows: [], logs: [] }; }
}

export function DashboardAutomationOverview({ workspaceId, onNavigate }: Props) {
  const [stored, setStored] = React.useState(() => readSnapshot(workspaceId));
  React.useEffect(() => {
    const refresh = () => setStored(readSnapshot(workspaceId));
    refresh();
    const onStorage = (event: StorageEvent) => {
      if (event.key === `clicko:automations:${workspaceId}` || event.key === `clicko:automation-logs:${workspaceId}`) refresh();
    };
    window.addEventListener('storage', onStorage);
    window.addEventListener('focus', refresh);
    return () => { window.removeEventListener('storage', onStorage); window.removeEventListener('focus', refresh); };
  }, [workspaceId]);

  const { flows, logs } = stored.workspaceId === workspaceId ? stored : { flows: [], logs: [] };
  const latestLog = new Map<string, FlowLog>();
  [...logs].sort((a, b) => b.createdAt.localeCompare(a.createdAt)).forEach(log => { if (!latestLog.has(log.flowId)) latestLog.set(log.flowId, log); });
  const active = flows.filter(flow => flow.isActive).length;
  const attention = flows.filter(flow => latestLog.get(flow.id)?.status === 'blocked').length;
  const completed = logs.filter(log => log.status === 'valid').length;
  const recent = [...flows].sort((a, b) => (b.updatedAt || '').localeCompare(a.updatedAt || '')).slice(0, 2);
  const preview = recent[0];
  const nodes = preview ? (Array.isArray(preview.nodes) ? preview.nodes.filter(node => node && Object.hasOwn(stepNames, node.type) && typeof node.label === 'string' && typeof node.details === 'string') : []) : demonstration;

  return <section className="cd-module cd-automations" aria-labelledby="cd-automations-title">
    <header className="cd-automation-intro"><div><span className="cd-eyebrow">Operação automatizada</span><h2 id="cd-automations-title">Automações</h2><p>Visualize suas rotinas, acompanhe validações e mantenha o trabalho em movimento.</p></div><button type="button" className="cd-button cd-button-primary" onClick={() => onNavigate('automations')}>Gerenciar Automações<ArrowRight size={17} /></button></header>
    <div className="cd-automation-status" aria-label="Resumo das automações"><span><i data-state={active ? 'active' : 'idle'} />{flows.length ? `${flows.length} ${flows.length === 1 ? 'fluxo configurado' : 'fluxos configurados'}` : 'Nenhum fluxo configurado'}</span><span>{active} {active === 1 ? 'ativo' : 'ativos'}</span>{attention > 0 && <span className="is-attention"><CircleAlert size={13} />{attention} para revisar</span>}</div>
    <div className="cd-automation-layout">
      <article className="cd-automation-featured"><div className="cd-automation-featured-head"><span className="cd-automation-symbol"><Workflow size={20} /></span><div><small>{preview ? 'Fluxo em destaque' : 'Exemplo de jornada'}</small><h3>{preview?.title || 'Da aprovação à publicação'}</h3></div><span className={`cd-automation-state ${preview?.isActive ? 'is-active' : ''}`}>{preview?.isActive ? 'Ativa' : preview ? 'Pausada' : 'Demonstração'}</span></div>
      <div className="cd-automation-preview">{nodes.length ? <div className="cd-automation-path" role="group" aria-label={preview ? `Resumo do fluxo ${preview.title}` : 'Exemplo informativo de automação, não ativa'}>{nodes.slice(0, 4).map(node => {
        const Icon = nodeIcons[node.type];
        return <button type="button" key={node.id} className={`cd-automation-node ${node.type === 'ai_generate' ? 'is-klic' : ''}`} onClick={() => onNavigate('automations')} title={node.details}><span><Icon size={18} aria-hidden="true" /></span><small>{stepNames[node.type]}</small><strong>{node.label || stepNames[node.type]}</strong></button>;
      })}{nodes.length > 4 && <button type="button" className="cd-automation-more" onClick={() => onNavigate('automations')}>+{nodes.length - 4} ações<ArrowRight size={15} /></button>}</div> : <p className="cd-automation-unconfigured">Este fluxo ainda não tem etapas definidas.</p>}</div>
      <button type="button" className="cd-automation-open" onClick={() => onNavigate('automations')}>Abrir fluxo completo<ArrowRight size={15} /></button></article>
      <aside className="cd-automation-overview" aria-label="Indicadores e fluxos recentes"><div className="cd-automation-metrics"><div><span><Workflow size={15} /></span><strong>{flows.length}</strong><small>Configurados</small></div><div><span><Zap size={15} /></span><strong>{active}</strong><small>Ativos agora</small></div><div className={attention ? 'is-attention' : ''}><span>{attention ? <CircleAlert size={15} /> : <Check size={15} />}</span><strong>{attention || completed}</strong><small>{attention ? 'Para revisar' : 'Validações concluídas'}</small></div></div>
      <div className="cd-automation-recent"><div className="cd-automation-recent-heading"><span>Fluxos recentes</span>{recent.length > 0 && <small>{recent.length} exibidos</small>}</div>{recent.length ? recent.map(flow => <button type="button" key={flow.id} onClick={() => onNavigate('automations')}><span><i data-state={flow.isActive ? 'active' : 'paused'} /><span><strong>{flow.title}</strong><small>{latestLog.get(flow.id)?.status === 'blocked' ? 'Revisar validação' : flow.isActive ? 'Configuração ativa' : 'Pausada'}</small></span></span><ArrowRight size={15} /></button>) : <div className="cd-automation-empty"><CircleAlert size={17} /><span><strong>Comece pela primeira rotina.</strong><p>Use um modelo pronto ou monte um novo fluxo.</p></span></div>}</div></aside>
    </div>
    <footer className="cd-automation-caveat"><CircleAlert size={14} /><span>As configurações podem ser salvas e validadas; a execução automática ainda não está conectada.</span></footer>
  </section>;
}
