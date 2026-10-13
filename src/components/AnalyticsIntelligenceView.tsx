import React from 'react';
import { useOperations } from '../context/OperationsContext';
import { klicPageScope, useKlicPageDetails } from '../klic/pageContext';
import { Activity, ArrowDownRight, ArrowRight, ArrowUpRight, BarChart3, ChevronDown, Eye, FileText, Link2, RefreshCw, Search, SlidersHorizontal, Users, X } from 'lucide-react';
import { KlicSymbol } from './KlicSymbol';
import type { NavigationTab } from '../types';
import { dateInput, useAnalyticsReport } from '../analytics/useAnalyticsReport';
import { formatNumber, formatPercent, networkMeta, percentChange, type AnalyticsContent, type AnalyticsMetric } from '../analytics/analyticsModel';
import { availableMetrics, groupPoints, rangeLabel } from '../analytics/analyticsWorkbench';
import { detectContentAnomalies } from '../analytics/analyticsIntelligence';
import { AnalyticsTrendChart, analyticsFormatLabels, analyticsMetricLabels } from './AnalyticsPrimitives';
import { ClickoLoader } from './ClickoLoader';
import './AnalyticsWorkspace.css';

type Report = ReturnType<typeof useAnalyticsReport>;
type Section = 'overview' | 'content' | 'networks';
type Ranking = 'reach' | 'engagementRate' | 'shares' | 'saves' | 'clicks' | 'views';
const sectionNames: Record<Section, string> = { overview: 'Visão geral', content: 'Conteúdos', networks: 'Redes' };
const formatDate = (value: string) => value ? new Date(`${value}T12:00:00`).toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' }).replace('.', '') : '—';

function Delta({ current, previous, enabled }: { current: number | null; previous: number | null; enabled: boolean }) {
  const change = enabled ? percentChange(current, previous) : null;
  if (change === null) return <span className="aw-muted">{enabled ? 'Sem comparação' : 'No período'}</span>;
  const Icon = change < 0 ? ArrowDownRight : ArrowUpRight;
  return <span className="aw-delta"><Icon aria-hidden="true" />{formatPercent(Math.abs(change))}<span className="aw-muted">vs. anterior</span></span>;
}
function PanelTitle({ eyebrow, title, children }: { eyebrow?: string; title: string; children?: React.ReactNode }) {
  return <div className="aw-panel-heading"><div>{eyebrow && <span className="aw-eyebrow">{eyebrow}</span>}<h2>{title}</h2></div>{children}</div>;
}
function Empty({ title, children }: { title: string; children?: React.ReactNode }) {
  return <div className="aw-empty"><BarChart3 aria-hidden="true" /><h3>{title}</h3>{children && <p>{children}</p>}</div>;
}
function ReportFilters({ report: r }: { report: Report }) {
  const [expanded, setExpanded] = React.useState(false);
  const platforms: Array<keyof typeof networkMeta> = [...new Set<keyof typeof networkMeta>(r.dataset?.networks.map(row => row.network) || [])];
  return <section className="aw-filters" aria-label="Filtros do Analytics">
    <div className="aw-filter-line">
      <label className="aw-select"><span className="sr-only">Rede</span><select value={r.network} onChange={event => { r.setNetwork(event.target.value as Report['network']); r.setAccount('all'); }}><option value="all">Todas as redes</option>{platforms.map(platform => <option key={platform} value={platform}>{networkMeta[platform].label}</option>)}</select><ChevronDown aria-hidden="true" /></label>
      <label className="aw-select"><span className="sr-only">Período</span><select value={r.period} onChange={event => r.setPeriod(Number(event.target.value))}>{[[1, 'Hoje'], [7, '7 dias'], [14, '14 dias'], [30, '30 dias'], [90, '90 dias'], [0, 'Personalizado']].map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select><ChevronDown aria-hidden="true" /></label>
      <label className="aw-check"><input type="checkbox" checked={r.compare} onChange={event => r.setCompare(event.target.checked)} />Comparar período</label>
      <button type="button" className={`aw-button aw-filter-toggle ${expanded ? 'is-active' : ''}`} aria-expanded={expanded} aria-controls="analytics-extra-filters" onClick={() => setExpanded(value => !value)}><SlidersHorizontal />Filtros{(r.account !== 'all' || r.client !== 'all') && <i className="aw-dot" />}</button>
      <span className="aw-window">{formatDate(r.start)} — {formatDate(r.end)}</span>
    </div>
    {r.period === 0 && <div className="aw-date-fields"><label>De<input aria-label="Data inicial" type="date" max={r.customEnd} value={r.customStart} onChange={event => r.setCustomStart(event.target.value)} /></label><label>Até<input aria-label="Data final" type="date" min={r.customStart} value={r.customEnd} onChange={event => r.setCustomEnd(event.target.value)} /></label></div>}
    {expanded && <div id="analytics-extra-filters" className="aw-extra-filters">{!r.demoMode && <label>Cliente<select value={r.client} onChange={event => { r.setClient(event.target.value); r.setAccount('all'); }}><option value="all">Todos os clientes</option>{r.clients.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>}<label>Conta<select value={r.account} onChange={event => r.setAccount(event.target.value)}><option value="all">Todas as contas</option>{r.dataset?.networks.filter(row => (r.network === 'all' || row.network === r.network) && (r.demoMode || r.client === 'all' || r.connectedAccounts.find(connection => connection.id === row.accountId)?.clientId === r.client)).map(row => <option key={row.accountId} value={row.accountId}>{row.accountLabel}</option>)}</select></label>{r.compare && <><label className="aw-check"><input type="checkbox" checked={r.manualComparison} onChange={event => r.setManualComparison(event.target.checked)} />Comparação personalizada</label>{r.manualComparison && <div className="aw-date-fields"><label>Comparar de<input type="date" value={r.comparisonStart} max={r.comparisonEnd} onChange={event => r.setComparisonStart(event.target.value)} /></label><label>Até<input type="date" value={r.comparisonEnd} min={r.comparisonStart} onChange={event => r.setComparisonEnd(event.target.value)} /></label></div>}</>}</div>}
    {!r.validDates && <p role="alert" className="aw-feedback">Escolha um intervalo válido: a data final deve ser igual ou posterior à inicial.</p>}
  </section>;
}
function Metrics({ report: r, metric, onSelect }: { report: Report; metric: AnalyticsMetric; onSelect: (metric: AnalyticsMetric) => void }) {
  const metrics = [{ id: 'reach', title: 'Alcance', icon: Eye }, { id: 'engagements', title: 'Engajamentos', icon: Activity }, { id: 'followers', title: 'Seguidores', icon: Users }, { id: 'clicks', title: 'Cliques', icon: ArrowUpRight }] as const;
  return <div className="aw-metrics" aria-label="Indicadores principais">{metrics.map(({ id, title, icon: Icon }) => <button type="button" key={id} className={`aw-metric ${metric === id ? 'is-selected' : ''}`} aria-pressed={metric === id} onClick={() => onSelect(id)}><span className="aw-metric-label">{title}<Icon aria-hidden="true" /></span><strong>{r.points.length ? formatNumber(r.totals[id]) : '—'}</strong><Delta current={r.totals[id]} previous={r.priorTotals[id]} enabled={r.compare} /></button>)}</div>;
}
function Engagement({ report: r }: { report: Report }) {
  const [active, setActive] = React.useState<string | null>(null);
  const parts = [{ key: 'likes', label: 'Curtidas', color: 'var(--cw-coral, #FF7F50)' }, { key: 'comments', label: 'Comentários', color: 'var(--cw-tangerine, #F28500)' }, { key: 'shares', label: 'Compartilhamentos', color: 'var(--cw-clicko-blue-ink, #6EB8F5)' }, { key: 'saves', label: 'Salvamentos', color: 'var(--cw-chart-previous, #808080)' }, { key: 'clicks', label: 'Cliques', color: 'var(--cw-chart-ink, #FFFFFF)' }] as const;
  const data = parts.flatMap(part => r.totals[part.key] === null ? [] : [{ ...part, value: r.totals[part.key]! }]);
  const total = data.reduce((sum, row) => sum + row.value, 0);
  const selected = data.find(row => row.key === active);
  let offset = 0;
  return <section className="aw-panel"><PanelTitle eyebrow="Interações" title="Como sua audiência responde" />{total > 0 ? <div className="aw-composition"><div className="aw-donut"><svg viewBox="0 0 160 160" aria-label="Distribuição das interações" role="img"><circle cx="80" cy="80" r="62" fill="none" stroke="var(--cw-chart-grid, rgba(255,255,255,.05))" strokeWidth="12" />{data.map(row => { const start = offset; const size = row.value / total * 100; offset += size; return <circle key={row.key} cx="80" cy="80" r="62" pathLength="100" transform="rotate(-90 80 80)" fill="none" stroke={row.color} strokeWidth={selected?.key === row.key ? 15 : 12} strokeDasharray={`${Math.max(0, size - .7)} ${100 - Math.max(0, size - .7)}`} strokeDashoffset={-start} onPointerEnter={() => setActive(row.key)} onPointerLeave={() => setActive(null)} />; })}</svg><div><strong>{selected ? formatPercent(selected.value / total * 100) : formatNumber(total)}</strong><span>{selected?.label || 'interações'}</span></div></div><div className="aw-legend">{data.map(row => <button key={row.key} type="button" className={active === row.key ? 'is-active' : ''} onFocus={() => setActive(row.key)} onBlur={() => setActive(null)} onMouseEnter={() => setActive(row.key)} onMouseLeave={() => setActive(null)} onClick={() => setActive(row.key)}><i style={{ background: row.color }} /><span>{row.label}</span><strong>{formatNumber(row.value)}</strong></button>)}</div></div> : <Empty title="Interações ainda indisponíveis">As interações aparecem aqui assim que forem sincronizadas.</Empty>}</section>;
}
function NetworkRanking({ report: r, full = false, onOpen }: { report: Report; full?: boolean; onOpen?: () => void }) {
  const [selection, setSelection] = React.useState<string[]>([]);
  const rows = [...r.rows].sort((a, b) => (b.current.reach ?? -1) - (a.current.reach ?? -1));
  const shown = full ? rows.filter(row => !selection.length || selection.includes(row.accountId)) : rows.slice(0, 4);
  const maximum = Math.max(1, ...rows.map(row => row.current.reach || 0));
  React.useEffect(() => setSelection([]), [r.network, r.account, r.demoMode]);
  return <section className="aw-panel"><PanelTitle eyebrow="Distribuição" title={full ? 'Compare suas redes' : 'Alcance por rede'}>{onOpen && <button className="aw-text-button" onClick={onOpen}>Ver redes<ArrowRight /></button>}</PanelTitle>
    {full && <div className="aw-platform-options">{rows.map(row => <button key={row.accountId} type="button" aria-pressed={selection.includes(row.accountId)} className={`aw-button ${selection.includes(row.accountId) ? 'is-active' : ''}`} onClick={() => setSelection(value => value.includes(row.accountId) ? value.filter(id => id !== row.accountId) : [...value, row.accountId])}>{networkMeta[row.network].label} · {row.accountLabel}</button>)}</div>}
    {shown.length ? <div className="aw-network-list">{shown.map(row => <div key={row.accountId} className="aw-network-row"><span className="aw-network-icon">{networkMeta[row.network].short}</span><div><div className="aw-between"><span>{networkMeta[row.network].label}<small>{row.accountLabel}</small></span><strong>{formatNumber(row.current.reach)}</strong></div><div className="aw-bar"><i style={{ width: `${(row.current.reach || 0) / maximum * 100}%` }} /></div>{full && <div className="aw-network-details"><span>{formatNumber(row.current.followers)} seguidores</span><span>{formatPercent(row.current.engagementRate)} engajamento</span><Delta current={row.current.reach} previous={row.previous.reach} enabled={r.compare} /></div>}</div></div>)}</div> : <Empty title="Nenhuma rede neste filtro" />}
  </section>;
}
function ContentList({ report: r, full, onSelect, onOpen }: { report: Report; full?: boolean; onSelect: (content: AnalyticsContent) => void; onOpen?: () => void }) {
  const [sort, setSort] = React.useState<Ranking>('reach');
  const [search, setSearch] = React.useState('');
  const [format, setFormat] = React.useState('all');
  const [limit, setLimit] = React.useState(12);
  React.useEffect(() => setLimit(12), [search, format, sort, r.start, r.end]);
  const filtered = r.contents.filter(content => (format === 'all' || content.format === format) && content.title.toLocaleLowerCase('pt-BR').includes(search.toLocaleLowerCase('pt-BR'))).sort((a, b) => (b[sort] ?? -1) - (a[sort] ?? -1));
  const rows = filtered.slice(0, full ? limit : 4);
  return <section className="aw-panel aw-content-panel"><PanelTitle eyebrow="Publicações" title={full ? 'Desempenho dos conteúdos' : 'Conteúdos em destaque'}>{onOpen && <button className="aw-text-button" onClick={onOpen}>Ver conteúdos<ArrowRight /></button>}</PanelTitle>
    {full && <div className="aw-content-tools"><label className="aw-search"><Search aria-hidden="true" /><input placeholder="Buscar publicação" aria-label="Buscar publicação" value={search} onChange={event => setSearch(event.target.value)} /></label><select aria-label="Formato" value={format} onChange={event => setFormat(event.target.value)}><option value="all">Todos os formatos</option>{[...new Set<string>(r.contents.map(content => content.format))].map(item => <option key={item} value={item}>{analyticsFormatLabels[item] || item}</option>)}</select><select aria-label="Ordenar conteúdos" value={sort} onChange={event => setSort(event.target.value as Ranking)}>{(['reach', 'engagementRate', 'shares', 'saves', 'clicks', 'views'] as const).map(item => <option key={item} value={item}>{item === 'engagementRate' ? 'Taxa de engajamento' : analyticsMetricLabels[item]}</option>)}</select></div>}
    <div className="aw-content-table" role="region" tabIndex={0} aria-label="Desempenho das publicações">
    <div className="aw-content-labels"><span>Publicação</span><span>{sort === 'engagementRate' ? 'Engajamento' : analyticsMetricLabels[sort]}</span><span>Engajamento</span></div>
    {rows.length ? rows.map((content, index) => <button type="button" className="aw-content-row" key={`${content.accountId}-${content.id}`} onClick={() => onSelect(content)}><span className="aw-content-name"><span className="aw-rank">{String(index + 1).padStart(2, '0')}</span><span><strong>{content.title}</strong><small>{networkMeta[content.network].label} · {analyticsFormatLabels[content.format] || content.format} · {new Date(content.date).toLocaleDateString('pt-BR')}</small></span></span><strong>{sort === 'engagementRate' ? formatPercent(content[sort]) : formatNumber(content[sort])}</strong><span className="aw-content-rate">{formatPercent(content.engagementRate)}<ArrowRight /></span></button>) : <Empty title="Nenhuma publicação encontrada">Experimente outro período ou ajuste os filtros.</Empty>}
    </div>
    {full && filtered.length > limit && <button type="button" className="aw-button aw-load-more" onClick={() => setLimit(value => value + 12)}>Mostrar mais</button>}
  </section>;
}
function Journey({ report: r }: { report: Report }) {
  const stages = [{ label: 'Alcance', value: r.totals.reach }, { label: 'Visualizações', value: r.totals.views }, { label: 'Engajamentos', value: r.totals.engagements }, { label: 'Cliques', value: r.totals.clicks }, { label: 'Conversões', value: r.totals.conversions }];
  return <details className="aw-panel aw-journey"><summary><span>Jornada de performance<small>Volumes das etapas disponíveis no período</small></span><ChevronDown /></summary><div className="aw-stages">{stages.map(stage => <div key={stage.label}><span>{stage.label}</span><strong>{formatNumber(stage.value)}</strong></div>)}</div><p className="aw-muted">Os volumes descrevem cada etapa; não representam o acompanhamento das mesmas pessoas entre elas.</p></details>;
}
function ContentDetail({ content, onClose }: { content: AnalyticsContent; onClose: () => void }) {
  const ref = React.useRef<HTMLDialogElement>(null);
  React.useEffect(() => { const dialog = ref.current; dialog?.showModal(); return () => dialog?.close(); }, []);
  return <dialog ref={ref} className="aw-dialog" aria-labelledby="analytics-detail-title" onClose={onClose} onClick={event => { if (event.target === event.currentTarget) onClose(); }}><div><header><span className="aw-eyebrow">{networkMeta[content.network].label} · {analyticsFormatLabels[content.format]}</span><button type="button" className="aw-button aw-icon-button" aria-label="Fechar detalhes" onClick={onClose}><X /></button></header><h2 id="analytics-detail-title">{content.title}</h2><p>{new Date(content.date).toLocaleDateString('pt-BR')}</p><div className="aw-detail-metrics">{(['reach', 'impressions', 'likes', 'comments', 'shares', 'saves', 'clicks', 'views'] as const).map(key => <div key={key}><span>{analyticsMetricLabels[key]}</span><strong>{formatNumber(content[key], false)}</strong></div>)}</div><p>Taxa de engajamento: <strong>{formatPercent(content.engagementRate)}</strong></p>{content.caption && <p className="aw-caption">{content.caption}</p>}</div></dialog>;
}

export const AnalyticsView: React.FC<{ onOpenStudio?: () => void; onNavigate?: (tab: NavigationTab) => void }> = ({ onNavigate }) => {
  const r = useAnalyticsReport();
  const { activeWorkspace, activeClient } = useOperations();
  const [focusedPublication] = React.useState(() => {
    const query = new URLSearchParams(window.location.search);
    const id = query.get('publication'); const account = query.get('account'); const date = query.get('date');
    return id && account && date && /^\d{4}-\d{2}-\d{2}$/.test(date) ? { id, account, date, title: query.get('title') || 'Publicação' } : null;
  });
  const [section, setSection] = React.useState<Section>('overview');
  const [metric, setMetric] = React.useState<AnalyticsMetric>('reach');
  const [granularity, setGranularity] = React.useState<'daily' | 'weekly' | 'monthly'>('daily');
  const [selected, setSelected] = React.useState<AnalyticsContent | null>(null);
  const focusedMetrics = focusedPublication ? r.contents.find(content => content.id === focusedPublication.id && content.accountId === focusedPublication.account) : undefined;
  const metrics = availableMetrics(r.points);
  const anomalies = React.useMemo(() => detectContentAnomalies(r.contents), [r.contents]);
  const change = r.compare ? percentChange(r.totals[metric], r.priorTotals[metric]) : null;
  const dateRange = `${formatDate(r.start)} — ${formatDate(r.end)}`;
  useKlicPageDetails('analytics', klicPageScope(activeWorkspace.id, activeClient?.id), {
    view: section, period: `${r.start} a ${r.end}`,
    filters: { rede: r.network, conta: r.account, metrica: metric, granularidade: granularity },
    selected: selected ? { kind: 'publicacao', id: selected.id } : undefined,
  });
  const synced = r.networks.map(row => row.lastSync).filter((value): value is string => !!value && Number.isFinite(Date.parse(value))).sort().at(-1);
  const analysisSummary = change === null ? 'Selecione uma métrica e compare períodos para acompanhar sua evolução.' : `${analyticsMetricLabels[metric]} ${change >= 0 ? 'cresceu' : 'recuou'} ${formatPercent(Math.abs(change))} em relação ao período comparado.`;
  React.useEffect(() => { setSelected(null); }, [r.demoMode, r.account, r.network, r.start, r.end]);
  React.useEffect(() => {
    if (!focusedPublication) return;
    setSection('content'); r.changeSource(false); r.setAccount(focusedPublication.account); r.setPeriod(0);
    const target = new Date(`${focusedPublication.date}T12:00:00`);
    const before = new Date(target); before.setDate(before.getDate() - 2);
    const after = new Date(target); after.setDate(after.getDate() + 2);
    r.setCustomStart(dateInput(before)); r.setCustomEnd(dateInput(after));
    window.history.replaceState({}, '', '/analytics');
  }, []);
  React.useEffect(() => { if (focusedMetrics) setSelected(focusedMetrics); }, [focusedMetrics?.id, focusedMetrics?.accountId]);
  return <div className="clicko-analytics-workspace"><div className="aw-shell">
    <header className="aw-header"><div><div className="aw-heading-line"><h1>Analytics</h1>{r.demoMode && <span className="aw-demo-label">Demonstração</span>}</div><p>Entenda os resultados. Encontre seu próximo passo.</p></div><div className="aw-header-actions">{r.demoMode ? <button className="aw-button" onClick={() => r.changeSource(false)}>Sair da demonstração</button> : <>{r.dataset && <button className="aw-button" disabled={r.refreshing} onClick={() => void r.refresh()}>{r.refreshing ? <ClickoLoader size="tiny" label="Atualizando Analytics" /> : <RefreshCw />}{r.refreshing ? 'Atualizando' : 'Atualizar'}</button>}<button className="aw-button" onClick={() => onNavigate?.('connected-accounts')}><Link2 />Conexões</button></>}</div></header>
    {!r.dataset ? <section className="aw-connect"><span className="aw-connect-icon"><BarChart3 /></span><span className="aw-eyebrow">Seus resultados, em perspectiva</span><h2>Uma visão clara de tudo<br />que o seu conteúdo alcança.</h2><p>Conecte suas redes para acompanhar desempenho, comparar períodos e descobrir quais conteúdos fazem a diferença.</p><div><button className="aw-button aw-primary" onClick={() => onNavigate?.('connected-accounts')}>Conectar uma conta<ArrowRight /></button></div><footer><span><Eye />Alcance e audiência</span><span><Activity />Interações</span><span><FileText />Conteúdo</span></footer></section> : <>
      <ReportFilters report={r} />
      <nav className="aw-tabs" aria-label="Áreas do Analytics">{(Object.keys(sectionNames) as Section[]).map(item => <button type="button" key={item} aria-current={section === item ? 'page' : undefined} onClick={() => setSection(item)}>{sectionNames[item]}</button>)}<span>{r.networks.length} {r.networks.length === 1 ? 'conta' : 'contas'}{synced && !r.demoMode ? ` · ${new Date(synced).toLocaleDateString('pt-BR')}` : ''}</span></nav>
      {focusedPublication && !focusedMetrics && <p role="status" className="aw-feedback">Ainda não há métricas específicas disponíveis para “{focusedPublication.title}”. Os dados aparecerão quando a rede social os disponibilizar para esta conta.</p>}
      {r.refreshError && <p role="alert" className="aw-feedback">{r.refreshError}<button className="aw-text-button" onClick={() => void r.refresh()}>Tentar novamente</button></p>}
      <div className="aw-section" key={section}>
      {section === 'overview' && <>
        <Metrics report={r} metric={metric} onSelect={setMetric} />
        <section className="aw-panel aw-trend"><PanelTitle eyebrow="Evolução no período" title={analyticsMetricLabels[metric]}><div className="aw-chart-controls"><select value={metric} aria-label="Métrica do gráfico" onChange={event => setMetric(event.target.value as AnalyticsMetric)}>{[...new Set([metric, ...metrics])].map(item => <option key={item} value={item}>{analyticsMetricLabels[item]}</option>)}</select><select aria-label="Agrupar por" value={granularity} onChange={event => setGranularity(event.target.value as typeof granularity)}><option value="daily">Diário</option><option value="weekly">Semanal</option><option value="monthly">Mensal</option></select></div></PanelTitle><AnalyticsTrendChart showInsight={false} key={`${metric}-${r.start}-${r.end}-${r.network}-${r.account}-${r.demoMode}-${granularity}`} points={groupPoints(r.points, granularity)} previous={groupPoints(r.previous, granularity)} metric={metric} compare={r.compare} loading={r.refreshing} rangeLabel={dateRange} comparisonRangeLabel={rangeLabel(r.previous)} /></section>
        <div className="aw-secondary-metrics">{[{ label: 'Impressões', value: r.totals.impressions }, { label: 'Taxa de engajamento', value: r.totals.engagementRate, percent: true }, { label: 'Saldo de seguidores', value: r.totals.netGrowth }, { label: 'Conteúdos publicados', value: r.points.length ? r.totals.posts : null }].map(item => <div key={item.label}><span>{item.label}</span><strong>{item.percent ? formatPercent(item.value) : formatNumber(item.value)}</strong></div>)}</div>
        <aside className="aw-klic" aria-label="Leitura da KLIC">
          <div className="aw-klic-mark" aria-hidden="true"><span className="aw-klic-icon"><KlicSymbol size={20} /></span><i /></div>
          <div className="aw-klic-copy">
            <div className="aw-klic-heading"><span className="aw-eyebrow">Leitura da KLIC{r.demoMode ? ' · ilustrativa' : ''}</span><span className="aw-klic-context">{r.points.length ? 'Período selecionado' : 'Aguardando dados'}</span></div>
            <h2>Sinais do seu desempenho</h2>
            <p>{r.analysis || analysisSummary}</p>
            {anomalies.length > 0 && <details><summary>Um sinal merece atenção</summary><p>{anomalies[0].explanation}</p></details>}
          </div>
          <div className="aw-klic-action"><button className="aw-button" disabled={r.demoMode || r.analyzing || !r.points.length} onClick={() => void r.askKlic()}>{r.analyzing ? <><ClickoLoader size="tiny" label="Analisando desempenho" />Analisando…</> : <>Aprofundar análise<ArrowRight /></>}</button></div>
        </aside>
        <div className="aw-two-columns"><Engagement report={r} /><NetworkRanking report={r} onOpen={() => setSection('networks')} /></div>
        <ContentList report={r} onSelect={setSelected} onOpen={() => setSection('content')} />
        <Journey report={r} />
      </>}
      {section === 'content' && <><div className="aw-section-intro"><h2>O que está funcionando no seu conteúdo</h2><p>Compare as publicações e abra cada uma para conhecer seus resultados.</p></div><ContentList report={r} full onSelect={setSelected} /></>}
      {section === 'networks' && <><div className="aw-section-intro"><h2>Cada rede, no mesmo contexto</h2><p>Compare alcance, audiência e engajamento no intervalo selecionado.</p></div><NetworkRanking report={r} full /><div className="aw-two-columns"><Engagement report={r} /><section className="aw-panel"><PanelTitle eyebrow="Audiência" title="Crescimento de seguidores" /><div className="aw-audience-totals">{[{ name: 'Ganhos', value: r.totals.gained }, { name: 'Perdas', value: r.totals.lost }, { name: 'Saldo', value: r.totals.netGrowth }].map(row => <div key={row.name}><span>{row.name}</span><strong>{formatNumber(row.value)}</strong></div>)}</div><p className="aw-muted">{dateRange}</p><Delta current={r.totals.netGrowth} previous={r.priorTotals.netGrowth} enabled={r.compare} /></section></div></>}
      </div>
      <footer className="aw-footer"><span>{r.demoMode ? 'Dados de demonstração' : 'Métricas disponíveis nas suas contas conectadas'}</span>{!r.demoMode && <button className="aw-text-button" onClick={() => r.changeSource(true)}>Ver demonstração</button>}</footer>
    </>}
    {selected && <ContentDetail content={selected} onClose={() => setSelected(null)} />}
  </div></div>;
};
