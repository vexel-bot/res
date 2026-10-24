import React from 'react';
import { ArrowRight, BarChart3, CalendarDays, Check, ChevronDown, CircleAlert, Clock3, FolderOpen, Link2, Plus, Sparkles } from 'lucide-react';
import type { ClientIntelligenceProfile, ConnectedAccount, ContentApprovalItem, LibraryAsset, NavigationTab, Post, Workspace } from '../types';
import { formatNumber, networkMeta, percentChange } from '../analytics/analyticsModel';
import { useAnalyticsReport } from '../analytics/useAnalyticsReport';
import { DashboardRadarOverview } from './DashboardRadarOverview';
import { DashboardAutomationOverview } from './DashboardAutomationOverview';
import { dashboardUpcoming, dashboardWeek } from './dashboardOperationalModel';

type Report = ReturnType<typeof useAnalyticsReport>;
type Props = {
  posts: Post[]; assets: LibraryAsset[]; approvals: ContentApprovalItem[]; accounts: ConnectedAccount[]; clients: ClientIntelligenceProfile[];
  workspace: Workspace; isPersonal: boolean; canAccess: (tab: NavigationTab) => boolean;
  onNavigate: (tab: NavigationTab) => void; onNewPost: () => void; onSelectPost: (post: Post) => void;
};
const needsAttention = (account: ConnectedAccount) => account.tokenExpiring ||
  ['expired', 'permission_insufficient', 'authorization_revoked', 'sync_error', 'error'].includes(account.connectionStatus || '');
const dateLabel = (value: string | Date) => new Date(typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value) ? `${value}T12:00:00` : value).toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' });
const timeLabel = (value: string) => new Date(value).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
function Heading({ id, title, detail, action, onAction }: { id: string; title: string; detail?: string; action?: string; onAction?: () => void }) {
  return <div className="cd-panel-heading"><div><h2 id={id}>{title}</h2>{detail && <p>{detail}</p>}</div>{action && <button type="button" className="cd-link" onClick={onAction}>{action}<ArrowRight size={15} aria-hidden="true" /></button>}</div>;
}

function Overview({ report, ...props }: Props & { report: Report | null }) {
  const pending = props.approvals.filter(item => ['in_review', 'pending_approval'].includes(item.stage));
  const scheduled = props.posts.filter(post => ['scheduled', 'approved'].includes(post.status) && post.scheduledAt && Date.parse(post.scheduledAt) >= Date.now());
  const published = props.posts.filter(post => post.status === 'published');
  const attention = props.accounts.filter(needsAttention);
  const failedPublications = props.posts.filter(post => post.status === 'error' || Boolean(post.publicationError));
  const futureClientIds = new Set(props.posts.filter(post => post.scheduledAt && Date.parse(post.scheduledAt) >= Date.now() && ['scheduled', 'approved', 'processing'].includes(post.status)).map(post => post.clientId).filter(Boolean));
  const uncoveredClients = props.isPersonal ? [] : props.clients.filter(client => client.status === 'active' && !futureClientIds.has(client.id));
  const healthIssueCount = failedPublications.length + attention.length + pending.length + uncoveredClients.length;
  const prioritySummary = [
    failedPublications.length ? `${failedPublications.length} ${failedPublications.length === 1 ? 'falha de publicação' : 'falhas de publicação'}` : '',
    attention.length ? `${attention.length} ${attention.length === 1 ? 'conexão para revisar' : 'conexões para revisar'}` : '',
    pending.length ? `${pending.length} ${pending.length === 1 ? 'aprovação pendente' : 'aprovações pendentes'}` : '',
    uncoveredClients.length ? `${uncoveredClients.length} ${uncoveredClients.length === 1 ? 'cliente sem programação futura' : 'clientes sem programação futura'}` : '',
  ].filter(Boolean).join(', ');
  const metrics = [
    ...(props.canAccess('calendar') ? [{ label: 'Agendados', value: scheduled.length, detail: 'próximas publicações', tab: 'calendar' as NavigationTab, change: null, icon: CalendarDays }] : []),
    ...(report?.totals.reach !== null && report?.totals.reach !== undefined ? [{ label: 'Alcance', value: report.totals.reach, detail: 'últimos 30 dias', tab: 'analytics' as NavigationTab, change: percentChange(report.totals.reach, report.priorTotals.reach), icon: BarChart3 }]
      : props.canAccess('calendar') ? [{ label: 'Publicados', value: published.length, detail: 'registrados no calendário', tab: 'calendar' as NavigationTab, change: null, icon: Check }] : []),
    ...(report?.totals.engagements !== null && report?.totals.engagements !== undefined ? [{ label: 'Engajamentos', value: report.totals.engagements, detail: 'últimos 30 dias', tab: 'analytics' as NavigationTab, change: percentChange(report.totals.engagements, report.priorTotals.engagements), icon: Sparkles }]
      : !props.isPersonal && props.canAccess('approvals') ? [{ label: 'Em aprovação', value: pending.length, detail: 'aguardando revisão', tab: 'approvals' as NavigationTab, change: null, icon: Clock3 }] : []),
    ...(props.canAccess('connected-accounts') ? [{ label: 'Contas conectadas', value: props.accounts.filter(account => account.connected).length, detail: 'neste ambiente', tab: 'connected-accounts' as NavigationTab, change: null, icon: Link2 }] : []),
  ].slice(0, 4);
  return <section className="cd-overview" aria-labelledby="cd-overview-title">
    <div className="cd-overview-header"><Heading id="cd-overview-title" title="Visão geral" detail={healthIssueCount ? `A KLIC identificou: ${prioritySummary}.` : 'A KLIC não identificou pendências operacionais neste momento.'} /><span className="cd-overview-health" data-state={healthIssueCount ? 'attention' : 'healthy'}><i />{healthIssueCount ? `${healthIssueCount} ${healthIssueCount === 1 ? 'ponto de atenção' : 'pontos de atenção'}` : 'Operação em dia'}</span></div>
    {metrics.length > 0 && <div className="cd-overview-metrics">{metrics.map(metric => {
      const Icon = metric.icon;
      return <button type="button" key={metric.label} onClick={() => props.onNavigate(metric.tab)} aria-label={`${metric.label}: ${formatNumber(metric.value)}. ${metric.detail}`}><span className="cd-metric-top"><span className="cd-metric-icon"><Icon size={15} /></span><span className="cd-metric-label">{metric.label}</span><ArrowRight size={13} /></span><span className="cd-metric-value"><strong>{formatNumber(metric.value)}</strong>{metric.change !== null && <em data-trend={metric.change >= 0 ? 'up' : 'down'}>{metric.change > 0 ? '+' : ''}{metric.change.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%</em>}</span><small>{metric.change !== null ? 'comparado ao período anterior' : metric.detail}</small></button>;
    })}</div>}
    <div className="cd-attention-line" aria-label="Saúde da operação">
      <span className="cd-attention-heading"><span className="cd-attention-symbol">{healthIssueCount ? <CircleAlert size={15} /> : <Check size={15} />}</span><span><strong className="cd-attention-title">Saúde da operação</strong><small>{healthIssueCount ? 'Prioridades que pedem sua atenção' : 'Nenhuma pendência sinalizada'}</small></span></span>
      <span className="cd-attention-items">
        {failedPublications.length > 0 && <button type="button" data-priority="critical" onClick={() => props.onNavigate('calendar')}><CircleAlert size={15} /><span>{failedPublications.length} {failedPublications.length === 1 ? 'publicação falhou' : 'publicações falharam'}</span><ArrowRight size={13} /></button>}
        {attention.length > 0 && <button type="button" onClick={() => props.onNavigate('connected-accounts')}><Link2 size={15} /><span>{attention.length} {attention.length === 1 ? 'conexão precisa' : 'conexões precisam'} de atenção</span><ArrowRight size={13} /></button>}
        {pending.length > 0 && <button type="button" onClick={() => props.onNavigate('approvals')}><Clock3 size={15} /><span>{pending.length} {pending.length === 1 ? 'aprovação pendente' : 'aprovações pendentes'}</span><ArrowRight size={13} /></button>}
        {uncoveredClients.length > 0 && props.canAccess('workspace') && <button type="button" onClick={() => props.onNavigate('workspace')}><CalendarDays size={15} /><span>{uncoveredClients.length} {uncoveredClients.length === 1 ? 'cliente sem programação futura' : 'clientes sem programação futura'}</span><ArrowRight size={13} /></button>}
        {!healthIssueCount && <span className="cd-attention-clear"><Check size={15} />Tudo pronto para continuar criando.</span>}
      </span>
    </div>
  </section>;
}

function QuickActions(props: Props) {
  const connected = props.accounts.filter(account => account.connected);
  const displayed = [...props.accounts.filter(needsAttention), ...connected.filter(account => !needsAttention(account))].slice(0, 4);
  const actions = [
    { tab: 'calendar' as NavigationTab, label: 'Calendário', icon: CalendarDays },
    { tab: 'analytics' as NavigationTab, label: 'Analytics', icon: BarChart3 },
    { tab: 'library' as NavigationTab, label: 'Biblioteca', icon: FolderOpen },
    { tab: 'connected-accounts' as NavigationTab, label: 'Conexões', icon: Link2 },
  ];
  return <nav className="cd-quick-actions" aria-label="Ações rápidas">
    <div className="cd-quick-main"><span className="cd-small-label">Ações rápidas</span><div>
      {props.canAccess('create-copy') && <button type="button" className="cd-button cd-button-primary" onClick={props.onNewPost}><Plus size={16} />Criar conteúdo</button>}
      {actions.filter(action => props.canAccess(action.tab)).map(({ tab, label, icon: Icon }) => <button type="button" key={tab} className={`cd-button cd-button-quiet ${tab === 'ai-chat' ? 'cd-quick-klic' : ''}`} onClick={() => props.onNavigate(tab)}><Icon size={16} />{label}</button>)}
    </div></div>
    <div className="cd-quick-secondary">
      {props.canAccess('connected-accounts') && <details className="cd-connections-menu"><summary>{connected.length} {connected.length === 1 ? 'conta conectada' : 'contas conectadas'}<ChevronDown size={14} /></summary><div>
        {displayed.map(account => <button type="button" key={account.id} onClick={() => props.onNavigate('connected-accounts')}><span className="cd-network-mark">{networkMeta[account.platform].short}</span><span><strong>{account.name || account.handle || networkMeta[account.platform].label}</strong><small>{networkMeta[account.platform].label}{account.handle && ` · ${account.handle}`}</small></span><span className={needsAttention(account) ? 'cd-connection-warning' : 'cd-connection-state'}>{needsAttention(account) ? account.tokenExpiring ? 'Token expirando' : account.connectionStatus === 'permission_insufficient' ? 'Permissão insuficiente' : 'Revisar conexão' : 'Conectada'}</span></button>)}
        {!displayed.length && <p>Nenhuma conta conectada neste ambiente.</p>}
        <button type="button" className="cd-link" onClick={() => props.onNavigate('connected-accounts')}>{connected.length ? 'Gerenciar conexões' : 'Conectar primeira conta'}<ArrowRight size={14} /></button>
      </div></details>}
    </div>
  </nav>;
}

function ProductionPreview({ assets, posts, onNavigate, onSelectPost }: Props) {
  const entries = [
    ...assets.map(asset => ({ id: `asset-${asset.id}`, title: asset.title, date: asset.createdAt, image: asset.type === 'image' ? asset.url : undefined, post: undefined as Post | undefined })),
    ...posts.filter(post => !assets.some(asset => asset.contentId === post.id)).map(post => ({ id: `post-${post.id}`, title: post.title, date: post.createdAt, image: post.imageUrl, post })),
  ].filter(entry => Number.isFinite(Date.parse(entry.date))).sort((a, b) => Date.parse(b.date) - Date.parse(a.date)).slice(0, 3);
  return <div className="cd-production-preview"><div className="cd-subheading"><h3>Produção recente</h3><button type="button" className="cd-link" onClick={() => onNavigate('library')}>Ver Biblioteca<ArrowRight size={14} /></button></div>
    {entries.length ? <div className="cd-production-list">{entries.map(entry => <button type="button" key={entry.id} onClick={() => entry.post ? onSelectPost(entry.post) : onNavigate('library')}><span className="cd-production-thumb"><FolderOpen size={18} />{entry.image && <img src={entry.image} alt="" loading="lazy" onError={event => { event.currentTarget.style.display = 'none'; }} />}</span><span><strong>{entry.title}</strong><small>{dateLabel(entry.date)}</small></span><ArrowRight size={14} /></button>)}</div> : <p className="cd-inline-empty">Os materiais mais recentes aparecerão aqui.</p>}
  </div>;
}

function ActivityPlanning(props: Props) {
  const [view, setView] = React.useState<'upcoming' | 'recent' | 'approval'>('upcoming');
  const [selectedDay, setSelectedDay] = React.useState<string | null>(null);
  const week = dashboardWeek(props.posts, props.workspace.id);
  const upcoming = dashboardUpcoming(props.posts, props.workspace.id);
  const pending = props.approvals.filter(item => ['in_review', 'pending_approval'].includes(item.stage));
  const selected = week.find(day => day.key === selectedDay);
  const recent = props.posts.filter(post => post.status === 'published').sort((a, b) => Date.parse(b.scheduledAt || b.createdAt) - Date.parse(a.scheduledAt || a.createdAt)).slice(0, 3);
  const visiblePosts = view === 'recent' ? recent : selected ? selected.posts.slice(0, 3) : upcoming;
  const tabs = [
    ...(props.canAccess('calendar') ? [{ id: 'upcoming' as const, label: 'A seguir' }, { id: 'recent' as const, label: 'Publicados' }] : []),
    ...(!props.isPersonal && props.canAccess('approvals') ? [{ id: 'approval' as const, label: `Aprovações${pending.length ? ` (${pending.length})` : ''}` }] : []),
  ];
  const currentView = tabs.some(tab => tab.id === view) ? view : tabs[0]?.id;
  return <section className="cd-planning" aria-labelledby="cd-planning-title">
    <Heading id="cd-planning-title" title="Atividade e planejamento" detail="Sua programação e o que vem a seguir." action={props.canAccess('calendar') ? 'Ver calendário' : undefined} onAction={() => props.onNavigate('calendar')} />
    {props.canAccess('calendar') && <>
      <div className="cd-week-caption"><span>{dateLabel(week[0].date)} — {dateLabel(week[6].date)}</span>{selected && <button type="button" className="cd-link" onClick={() => setSelectedDay(null)}>Ver próximos conteúdos</button>}</div>
      <div className="cd-week-scroll" tabIndex={0} role="region" aria-label="Agenda de segunda a domingo"><div className="cd-week">{week.map(day => <button type="button" key={day.key} className={`cd-week-day ${day.today ? 'is-today' : ''} ${selectedDay === day.key ? 'is-selected' : ''}`} aria-pressed={selectedDay === day.key} aria-label={`${dateLabel(day.date)}${day.today ? ', hoje' : ''}, ${day.posts.length} conteúdos programados`} onClick={() => { setSelectedDay(day.key); setView('upcoming'); }}>
        <span>{day.date.toLocaleDateString('pt-BR', { weekday: 'short' }).replace('.', '')}</span><strong>{day.date.getDate()}</strong><small>{day.posts.length ? `${day.posts.length} ${day.posts.length === 1 ? 'conteúdo' : 'conteúdos'}` : '—'}</small>{day.today && <i aria-hidden="true" />}
      </button>)}</div></div>
    </>}
    {tabs.length > 0 && <><div className="cd-activity-tabs" role="tablist" aria-label="Atividade do ambiente">{tabs.map(tab => <button type="button" role="tab" aria-selected={currentView === tab.id} aria-controls="cd-activity-content" id={`cd-activity-${tab.id}`} tabIndex={currentView === tab.id ? 0 : -1} key={tab.id} onClick={() => { setView(tab.id); setSelectedDay(null); }} onKeyDown={event => {
      const position = tabs.findIndex(item => item.id === tab.id);
      const next = event.key === 'ArrowRight' ? (position + 1) % tabs.length : event.key === 'ArrowLeft' ? (position - 1 + tabs.length) % tabs.length : event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1 : -1;
      if (next >= 0) { event.preventDefault(); setView(tabs[next].id); setSelectedDay(null); event.currentTarget.parentElement?.querySelectorAll<HTMLButtonElement>('button')[next]?.focus(); }
    }}>{tab.label}</button>)}</div>
      <div id="cd-activity-content" className="cd-activity-content" role="tabpanel" aria-labelledby={`cd-activity-${currentView}`} tabIndex={0}>
        {currentView === 'approval' ? pending.length ? <div className="cd-timeline">{pending.slice(0, 3).map(item => <button type="button" key={item.id} onClick={() => props.onNavigate('approvals')}><span className="cd-timeline-time"><Clock3 size={15} /><small>Revisão</small></span><span><strong>{item.title}</strong><small>{networkMeta[item.platform].label} · {item.authorName}</small></span><ArrowRight size={14} /></button>)}</div> : <p className="cd-inline-empty">Nenhum conteúdo aguardando aprovação.</p>
          : visiblePosts.length ? <div className="cd-timeline">{visiblePosts.map(post => <button type="button" key={post.id} onClick={() => props.onSelectPost(post)} title={post.title}><span className="cd-timeline-time"><strong>{dateLabel(post.scheduledAt || post.createdAt)}</strong><small>{post.scheduledAt ? timeLabel(post.scheduledAt) : '—'}</small></span><span><strong>{post.title}</strong><small>{networkMeta[post.platform].label} · {currentView === 'recent' ? 'Publicado no calendário' : 'Programado'}</small></span><ArrowRight size={14} /></button>)}</div>
            : <div className="cd-activity-empty"><CalendarDays size={22} /><strong>{currentView === 'recent' ? 'Nenhuma publicação registrada.' : selected ? `Sem programação em ${dateLabel(selected.date)}` : 'Sua próxima publicação começa aqui.'}</strong><p>{currentView === 'recent' ? 'Os conteúdos publicados aparecerão nesta lista.' : 'Você ainda não tem conteúdos programados para este período.'}</p>{props.canAccess('create-copy') && currentView !== 'recent' && <button type="button" className="cd-link" onClick={props.onNewPost}>Criar conteúdo<Plus size={15} /></button>}</div>}
        {currentView === 'upcoming' && selected && selected.posts.length > 3 && <button type="button" className="cd-link" onClick={() => props.onNavigate('calendar')}>Ver mais {selected.posts.length - 3} conteúdos<ArrowRight size={14} /></button>}
        {currentView === 'approval' && pending.length > 3 && <button type="button" className="cd-link" onClick={() => props.onNavigate('approvals')}>Ver todas as aprovações<ArrowRight size={14} /></button>}
      </div></>}
    {props.canAccess('library') && <ProductionPreview {...props} />}
  </section>;
}

function PanelContents({ report, ...props }: Props & { report: Report | null }) {
  const showPlanning = props.canAccess('calendar') || props.canAccess('approvals') || props.canAccess('library');
  const showRadar = props.canAccess('strategy') && props.canAccess('ai-chat');
  return <div className="cd-content cd-operations">
    <Overview {...props} report={report} />
    <QuickActions {...props} />
    {(showPlanning || showRadar) && <div className={`cd-command-grid ${showPlanning && showRadar ? '' : 'is-single'}`}>
      {showPlanning && <ActivityPlanning {...props} />}
      {showRadar && <aside className="cd-command-side cd-trends-side" aria-label="Assuntos em alta"><DashboardRadarOverview activeWorkspace={props.workspace} onNavigate={props.onNavigate} /></aside>}
    </div>}
    {props.canAccess('automations') && <DashboardAutomationOverview workspaceId={props.workspace.id} onNavigate={props.onNavigate} />}
  </div>;
}

function AnalyticsPanel(props: Props) {
  const report = useAnalyticsReport();
  return <PanelContents {...props} report={report} />;
}

export function DashboardControlPanel(props: Props) {
  return props.canAccess('analytics') ? <AnalyticsPanel key={props.workspace.id} {...props} /> : <PanelContents key={props.workspace.id} {...props} report={null} />;
}
