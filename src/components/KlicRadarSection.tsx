import React from 'react';
import { createPortal } from 'react-dom';
import { createRequestGuard } from '../utils/requestGuard';
import { useKlicClient } from '../klic/useKlicClient';
import { ClickoLoader } from './ClickoLoader';
import {
  CheckCircle2,
  ChevronDown,
  Clock3,
  ExternalLink,
  FileSearch,
  Flame,
  Globe2,
  MoreHorizontal,
  Radar,
  RefreshCw,
  Search,
  SlidersHorizontal,
  Sparkles,
  Target,
  TrendingDown,
  TrendingUp,
  X,
} from 'lucide-react';
import type { NavigationTab, PostFormat, SocialPlatform, Workspace } from '../types';
import { useOperations } from '../context/OperationsContext';
import { useAIChat } from '../context/AIChatContext';
import { useGovernance } from '../context/GovernanceContext';
import { KlicSymbol } from './KlicSymbol';

type RadarRegion = 'BR' | 'GLOBAL';
type RadarStatus = 'exploding' | 'hot' | 'emerging' | 'opportunity' | 'cooling' | 'saturated' | 'ended';
type RadarCategory = 'news' | 'research' | 'social' | 'technology' | 'marketing' | 'business' | 'entertainment' | 'sports' | 'culture' | 'education' | 'segment';

type RadarEvidence = {
  id: string;
  source: 'google-trends' | 'google-news' | 'youtube' | 'pinterest';
  sourceLabel: string;
  title: string;
  url: string;
  observedAt: string;
  publishedAt?: string;
  signalType: 'search-growth' | 'news-coverage' | 'video-popularity' | 'keyword-growth';
  metricLabel?: string;
  official: boolean;
};

export type RadarTrend = {
  id: string;
  title: string;
  description: string;
  category: RadarCategory;
  region: RadarRegion;
  status: RadarStatus;
  timing: 'good' | 'watch' | 'late';
  direction: 'growing' | 'stable' | 'falling';
  trendScore: number;
  brandRelevance: number;
  confidence: 'high' | 'moderate' | 'low';
  startedAt: string;
  updatedAt: string;
  relatedTerms: string[];
  keyword?: string;
  hashtags?: string[];
  platforms?: string[];
  language?: string;
  growthPercent?: number;
  history?: Array<{ score: number; observedAt: string }>;
  evidence: RadarEvidence[];
  dataExplanation: string;
  inference: string;
  opportunity?: string;
  format: string;
  formatId: PostFormat;
  angle: string;
  scoreBasis: { recency: number; sourceDiversity: number; searchSignal: number; supportingCoverage: number };
};

type RadarSourceStatus = { id: string; label: string; available: boolean; lastCheckedAt: string; detail: string };
export type RadarResponse = { trends?: unknown; sourceStatus?: unknown; updatedAt?: string; message?: string; historyAvailable?: boolean };
export type RadarInitialSnapshot = { scope: string; region: RadarRegion; data: RadarResponse };
type KlicRadarSectionProps = { activeWorkspace: Workspace; onNavigate: (tab: NavigationTab) => void; initialSnapshot?: RadarInitialSnapshot };

const statusMeta: Record<RadarStatus, { label: string; tone: string; icon: React.ComponentType<{ className?: string }> }> = {
  exploding: { label: 'Explodindo', tone: 'text-[#FF7F50]', icon: Flame },
  hot: { label: 'Em alta', tone: 'text-[#F28500]', icon: Flame },
  emerging: { label: 'Crescendo', tone: 'text-[rgba(255,255,255,0.88)]', icon: TrendingUp },
  opportunity: { label: 'Emergente', tone: 'text-[rgba(255,255,255,0.72)]', icon: Sparkles },
  cooling: { label: 'Perdendo força', tone: 'text-[#808080]', icon: TrendingDown },
  saturated: { label: 'Saturado', tone: 'text-[#808080]', icon: Clock3 },
  ended: { label: 'Encerrado', tone: 'text-[#808080]', icon: X },
};

const timingMeta = {
  good: { label: 'Bom momento', className: 'text-[#FF7F50]' },
  watch: { label: 'Observar', className: 'text-[#F28500]' },
  late: { label: 'Tarde / saturado', className: 'text-[#808080]' },
} as const;
const confidenceMeta = { high: 'Alta confiança', moderate: 'Média confiança', low: 'Baixa confiança' } as const;
const categoryLabels: Record<RadarCategory, string> = {
  news: 'Notícias', research: 'Pesquisas', social: 'Redes sociais', technology: 'Tecnologia', marketing: 'Marketing',
  business: 'Negócios', entertainment: 'Entretenimento', sports: 'Esportes', culture: 'Cultura', education: 'Educação', segment: 'Segmento',
};
const sourceShortLabel: Record<RadarEvidence['source'], string> = { 'google-trends': 'Google Trends', 'google-news': 'Notícias', youtube: 'YouTube', pinterest: 'Pinterest' };

export const isRadarTrend = (value: unknown): value is RadarTrend => {
  if (!value || typeof value !== 'object') return false;
  const trend = value as Partial<RadarTrend>;
  return Boolean(trend.id && trend.title && trend.updatedAt && Array.isArray(trend.evidence) && Number.isFinite(trend.trendScore) && Number.isFinite(trend.brandRelevance));
};

const formatRelativeTime = (value?: string) => {
  if (!value) return 'Atualização indisponível';
  const elapsedMinutes = Math.max(0, Math.round((Date.now() - new Date(value).getTime()) / 60_000));
  if (elapsedMinutes < 1) return 'Atualizado agora';
  if (elapsedMinutes < 60) return `Atualizado há ${elapsedMinutes} min`;
  const hours = Math.round(elapsedMinutes / 60);
  if (hours < 24) return `Atualizado há ${hours}h`;
  return `Atualizado em ${new Date(value).toLocaleString('pt-BR')}`;
};

export function KlicRadarSection({ activeWorkspace, onNavigate, initialSnapshot }: KlicRadarSectionProps) {
  const { activeClient, activeCampaign, contextSnapshot, prepareStudioHandoff, addPosts } = useOperations();
  const { canAccess } = useGovernance();
  const { startRadarConversation } = useAIChat();
  const klic = useKlicClient();
  const seeded = initialSnapshot?.scope === klic.scope && initialSnapshot.region === 'BR' ? initialSnapshot.data : undefined;
  const [storedTrends, setTrends] = React.useState<RadarTrend[]>(() => Array.isArray(seeded?.trends) ? seeded.trends.filter(isRadarTrend) : []);
  const [storedSources, setSources] = React.useState<RadarSourceStatus[]>(() => Array.isArray(seeded?.sourceStatus) ? seeded.sourceStatus as RadarSourceStatus[] : []);
  const [loadedScope, setLoadedScope] = React.useState(seeded ? `${klic.scope}:BR` : '');
  const [region, setRegion] = React.useState<RadarRegion>('BR');
  const [storedSelection, setSelectedTrend] = React.useState<RadarTrend | null>(null);
  const [view, setView] = React.useState<'hot' | 'emerging' | 'personal'>('hot');
  const [query, setQuery] = React.useState('');
  const [sortBy, setSortBy] = React.useState<'score' | 'growth' | 'recent' | 'relevance'>('score');
  const [network, setNetwork] = React.useState('all');
  const [period, setPeriod] = React.useState<'now' | '24h' | '7d' | '30d'>('now');
  const [category, setCategory] = React.useState('all');
  const [stage, setStage] = React.useState('all');
  const [signalType, setSignalType] = React.useState('all');
  const [growth, setGrowth] = React.useState('all');
  const [multiPlatformOnly, setMultiPlatformOnly] = React.useState(false);
  const [showAdvancedFilters, setShowAdvancedFilters] = React.useState(false);
  const [showSources, setShowSources] = React.useState(false);
  const [showDetailData, setShowDetailData] = React.useState(false);
  const [showMoreActions, setShowMoreActions] = React.useState(false);
  const [loading, setLoading] = React.useState(!seeded);
  const [refreshing, setRefreshing] = React.useState(false);
  const [error, setError] = React.useState('');
  const [message, setMessage] = React.useState(seeded?.message || '');
  const [updatedAt, setUpdatedAt] = React.useState(seeded?.updatedAt || '');
  const [historyAvailable, setHistoryAvailable] = React.useState(seeded?.historyAvailable !== false);
  const radarScope = React.useRef('');
  radarScope.current = `${klic.scope}:${region}`;
  const radarGuard = React.useRef(createRequestGuard());
  const trends = loadedScope === radarScope.current ? storedTrends : [];
  const sources = loadedScope === radarScope.current ? storedSources : [];
  const selectedTrend = loadedScope === radarScope.current ? storedSelection : null;
  React.useEffect(() => {
    if (!selectedTrend) return;
    setShowDetailData(false);
    setShowMoreActions(false);
    const closeOnEscape = (event: KeyboardEvent) => { if (event.key === 'Escape') setSelectedTrend(null); };
    window.addEventListener('keydown', closeOnEscape);
    return () => window.removeEventListener('keydown', closeOnEscape);
  }, [selectedTrend]);
  React.useEffect(() => {
    if (loadedScope === `${klic.scope}:${region}`) return;
    setSelectedTrend(null); setError(''); setMessage(''); setUpdatedAt(''); setLoading(true);
  }, [klic.scope, region, loadedScope]);

  const refreshRadar = React.useCallback(async (forceRefresh = false, signal?: AbortSignal) => {
    const isCurrent = radarGuard.current.begin(`${klic.scope}:${region}`, () => radarScope.current);
    setRefreshing(true);
    setError('');
    try {
      const data = await klic.request<RadarResponse>('radar', 'ai-chat', { region, forceRefresh }, signal);
      if (!isCurrent() || signal?.aborted) return;
      setLoadedScope(`${klic.scope}:${region}`);
      setTrends(Array.isArray(data.trends) ? data.trends.filter(isRadarTrend) : []);
      setSources(Array.isArray(data.sourceStatus) ? data.sourceStatus as RadarSourceStatus[] : []);
      setUpdatedAt(data.updatedAt || new Date().toISOString());
      setMessage(data.message || '');
      setHistoryAvailable(data.historyAvailable !== false);
    } catch (requestError) {
      if (isCurrent() && (requestError as Error).name !== 'AbortError') {
        setTrends([]);
        setError(requestError instanceof Error ? requestError.message : 'Não foi possível atualizar o Radar.');
      }
    } finally {
      if (isCurrent() && !signal?.aborted) { setLoading(false); setRefreshing(false); }
    }
  }, [klic.request, klic.scope, region]);

  React.useEffect(() => {
    const controller = new AbortController();
    if (loadedScope !== `${klic.scope}:${region}`) void refreshRadar(false, controller.signal);
    const interval = window.setInterval(() => void refreshRadar(false), 10 * 60 * 1000);
    return () => { radarGuard.current.invalidate(); controller.abort(); window.clearInterval(interval); };
  }, [refreshRadar, loadedScope, klic.scope, region]);

  const visibleTrends = React.useMemo(() => trends
    .filter((trend) => trend.status !== 'ended')
    .filter((trend) => {
      const normalizedQuery = query.trim().toLocaleLowerCase('pt-BR');
      if (!normalizedQuery) return true;
      return [trend.title, trend.description, trend.keyword, ...(trend.hashtags || []), ...trend.relatedTerms]
        .filter(Boolean)
        .some((value) => String(value).toLocaleLowerCase('pt-BR').includes(normalizedQuery));
    })
    .filter((trend) => network === 'all' || trend.evidence.some(item => item.source === network))
    .filter((trend) => category === 'all' || trend.category === category)
    .filter((trend) => stage === 'all' || trend.status === stage)
    .filter((trend) => signalType === 'all' || trend.evidence.some(item => item.signalType === signalType))
    .filter((trend) => growth === 'all' || (growth === 'measured' ? trend.growthPercent !== undefined : growth === 'high' ? (trend.growthPercent ?? -Infinity) >= 50 : trend.direction === 'growing'))
    .filter((trend) => !multiPlatformOnly || (trend.platforms?.length || 0) > 1)
    .filter((trend) => trend.region === region)
    .filter((trend) => period === 'now' || Date.now() - Date.parse(trend.startedAt) <= ({ '24h': 86400000, '7d': 7 * 86400000, '30d': 30 * 86400000 } as const)[period])
    .filter((trend) => view === 'hot' ? ['exploding', 'hot'].includes(trend.status) : view === 'emerging' ? ['opportunity', 'emerging'].includes(trend.status) : view === 'personal' ? trend.brandRelevance >= 50 : true)
    .sort((left, right) => {
      if (sortBy === 'growth') return (right.growthPercent ?? -Infinity) - (left.growthPercent ?? -Infinity);
      if (sortBy === 'recent') return Date.parse(right.updatedAt) - Date.parse(left.updatedAt);
      if (sortBy === 'relevance') return right.brandRelevance - left.brandRelevance;
      return right.trendScore - left.trendScore;
    })
    .slice(0, 18), [trends, view, query, sortBy, network, period, category, stage, signalType, growth, multiPlatformOnly, region]);

  const clearFilters = () => {
    setQuery('');
    setNetwork('all');
    setPeriod('now');
    setCategory('all');
    setStage('all');
    setSignalType('all');
    setGrowth('all');
    setMultiPlatformOnly(false);
  };

  const recordInteraction = (trend: RadarTrend, action: 'opened' | 'explored') => {
    try {
      const storageKey = `clicko-klic-radar-interactions:${klic.scope}`;
      const current = JSON.parse(localStorage.getItem(storageKey) || '[]');
      localStorage.setItem(storageKey, JSON.stringify([...current.slice(-99), { trendId: trend.id, action, createdAt: new Date().toISOString() }]));
    } catch { /* A navegação continua disponível sem armazenamento local. */ }
  };

  const exploreWithKlic = (trend: RadarTrend, intent: 'analyze' | 'content' | 'ideas' | 'script' | 'caption' = 'content') => {
    startRadarConversation({
      intent,
      title: trend.title,
      status: statusMeta[trend.status].label,
      summary: trend.description,
      observedData: trend.dataExplanation,
      inference: trend.inference,
      opportunity: trend.opportunity,
      suggestedFormat: trend.format,
      angle: trend.angle,
      evidence: trend.evidence.map((evidence) => ({ source: evidence.sourceLabel, title: evidence.title, url: evidence.url })),
    });
    recordInteraction(trend, 'explored');
    onNavigate('ai-chat');
  };

  const sendToStudio = (trend: RadarTrend, destination: 'create-image' | 'create-video') => {
    if (!canAccess(destination)) return;
    prepareStudioHandoff({
      source: 'ai', clientId: activeClient?.id, campaignId: activeCampaign?.id,
      objective: activeClient?.currentObjective || contextSnapshot.objectives || 'Interpretar uma tendência verificada para a marca.',
      title: trend.title.slice(0, 100), angle: trend.angle,
      hook: trend.description.slice(0, 180), cta: 'Desenvolver conteúdo original',
      format: destination === 'create-video' ? 'reels' : 'post', funnelStage: 'Criação',
    });
    onNavigate(destination);
  };

  const addToCalendar = (trend: RadarTrend) => {
    if (!canAccess('calendar')) return;
    const knownPlatforms: SocialPlatform[] = ['instagram', 'linkedin', 'tiktok', 'youtube', 'pinterest', 'threads', 'x', 'facebook'];
    const platform = knownPlatforms.find(item => trend.platforms?.some(source => source.toLowerCase() === item)) || 'instagram';
    addPosts([{ id: `post-radar-${Date.now()}`, workspaceId: activeWorkspace.id, title: trend.title.slice(0, 90), platform, format: trend.formatId, copy: `${trend.title}\n\n${trend.description}\n\nFonte: ${trend.evidence.map(item => item.url).join(' | ')}`.slice(0, 4000), hashtags: trend.hashtags || [], status: 'draft', author: 'Radar da Clicko', createdAt: new Date().toISOString(), campaignId: activeCampaign?.id, clientId: activeClient?.id, contextRevision: contextSnapshot.revision, objective: activeClient?.currentObjective || contextSnapshot.objectives, origin: 'context' }]);
    onNavigate('calendar');
  };

  return (
    <section className="clicko-klic-radar border-y border-white/[0.07] py-7" aria-label="Radar da Clicko">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="max-w-2xl">
          <div className="flex items-center gap-2 text-[9px] font-semibold uppercase tracking-[0.18em] text-[#FF7F50]"><Radar className="h-3.5 w-3.5" />Radar de Trends</div>
          <h2 className="mt-2 text-[clamp(22px,2.2vw,30px)] font-medium leading-tight tracking-[-0.035em] text-white">Tendências que merecem atenção</h2>
          <p className="mt-1.5 max-w-xl text-[10px] leading-5 text-[#808080]">Sinais atuais, organizados para ajudar {activeClient?.name || activeWorkspace.name} a decidir o que analisar e criar.</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="hidden text-[8px] text-[#808080] sm:inline">{formatRelativeTime(updatedAt)}</span>
          <button type="button" onClick={() => void refreshRadar(true)} disabled={refreshing} className="grid h-9 w-9 place-items-center rounded-lg border border-white/[0.08] text-[#808080] hover:bg-white/[0.035] hover:text-white disabled:opacity-50" aria-label="Atualizar Radar">{refreshing ? <ClickoLoader size="tiny" label="Atualizando Radar" /> : <RefreshCw className="h-3.5 w-3.5" />}</button>
        </div>
      </header>

      <div className="mt-5 rounded-xl border border-white/[0.07] bg-[rgba(128,128,128,0.14)] p-3 sm:p-4">
        <label className="flex h-10 items-center gap-2.5 rounded-lg border border-white/[0.08] bg-black px-3 focus-within:border-[#FF7F50]/45" aria-label="Buscar tendências">
          <Search className="h-3.5 w-3.5 shrink-0 text-[#808080]" />
          <input value={query} onChange={(event) => setQuery(event.target.value)} type="search" placeholder="Buscar tendência, assunto ou palavra-chave" className="min-w-0 flex-1 border-0 bg-transparent text-[10px] text-white outline-none placeholder:text-[#808080]" />
          {query && <button type="button" onClick={() => setQuery('')} className="grid h-6 w-6 place-items-center text-[#808080] hover:text-white" aria-label="Limpar busca"><X className="h-3 w-3" /></button>}
        </label>

        <div className="mt-3 grid grid-cols-2 gap-2 lg:grid-cols-4" aria-label="Filtros principais do Radar">
          <label className="min-w-0"><span className="mb-1 block text-[7px] uppercase tracking-[0.12em] text-[#808080]">Rede</span><select value={network} onChange={event => setNetwork(event.target.value)} className="h-9 w-full rounded-lg border border-white/[0.08] bg-black px-2.5 text-[9px] text-white"><option value="all">Todas as redes</option>{(['google-trends', 'google-news', 'youtube', 'pinterest'] as const).map(id => <option key={id} value={id}>{sourceShortLabel[id]}</option>)}</select></label>
          <label className="min-w-0"><span className="mb-1 block text-[7px] uppercase tracking-[0.12em] text-[#808080]">Período</span><select value={period} onChange={event => setPeriod(event.target.value as typeof period)} className="h-9 w-full rounded-lg border border-white/[0.08] bg-black px-2.5 text-[9px] text-white"><option value="now">Agora</option><option value="24h">Últimas 24 horas</option><option value="7d">Últimos 7 dias</option><option value="30d">Últimos 30 dias</option></select></label>
          <label className="min-w-0"><span className="mb-1 block text-[7px] uppercase tracking-[0.12em] text-[#808080]">Categoria</span><select value={category} onChange={event => setCategory(event.target.value)} className="h-9 w-full rounded-lg border border-white/[0.08] bg-black px-2.5 text-[9px] text-white"><option value="all">Todas as categorias</option>{Object.entries(categoryLabels).map(([id, label]) => <option key={id} value={id}>{label}</option>)}</select></label>
          <label className="min-w-0"><span className="mb-1 block text-[7px] uppercase tracking-[0.12em] text-[#808080]">Região</span><select value={region} onChange={event => setRegion(event.target.value as RadarRegion)} className="h-9 w-full rounded-lg border border-white/[0.08] bg-black px-2.5 text-[9px] text-white"><option value="BR">Brasil</option><option value="GLOBAL">Global · EUA</option></select></label>
        </div>

        <button type="button" onClick={() => setShowAdvancedFilters(value => !value)} aria-expanded={showAdvancedFilters} className="mt-3 flex items-center gap-1.5 text-[8px] font-medium text-[#808080] hover:text-white"><SlidersHorizontal className="h-3 w-3" />Mais filtros<ChevronDown className={`h-3 w-3 transition-transform ${showAdvancedFilters ? 'rotate-180' : ''}`} /></button>
        {showAdvancedFilters && <div className="mt-3 grid gap-2 border-t border-white/[0.06] pt-3 sm:grid-cols-2 lg:grid-cols-4">
          <label><span className="mb-1 block text-[7px] uppercase tracking-[0.12em] text-[#808080]">Estágio</span><select value={stage} onChange={event => setStage(event.target.value)} className="h-9 w-full rounded-lg border border-white/[0.08] bg-black px-2.5 text-[9px] text-white"><option value="all">Todos</option>{Object.entries(statusMeta).map(([id, meta]) => <option key={id} value={id}>{meta.label}</option>)}</select></label>
          <label><span className="mb-1 block text-[7px] uppercase tracking-[0.12em] text-[#808080]">Tipo de sinal</span><select value={signalType} onChange={event => setSignalType(event.target.value)} className="h-9 w-full rounded-lg border border-white/[0.08] bg-black px-2.5 text-[9px] text-white"><option value="all">Todos</option><option value="search-growth">Buscas Google</option><option value="keyword-growth">Buscas Pinterest</option><option value="video-popularity">Vídeos populares</option><option value="news-coverage">Cobertura</option></select></label>
          <label><span className="mb-1 block text-[7px] uppercase tracking-[0.12em] text-[#808080]">Crescimento</span><select value={growth} onChange={event => setGrowth(event.target.value)} className="h-9 w-full rounded-lg border border-white/[0.08] bg-black px-2.5 text-[9px] text-white"><option value="all">Todos</option><option value="rising">Em crescimento</option><option value="measured">Variação medida</option><option value="high">Acima de 50%</option></select></label>
          <div className="flex flex-col justify-end gap-2"><label className="flex h-9 cursor-pointer items-center gap-2 rounded-lg border border-white/[0.08] px-3 text-[8px] text-[#808080]"><input type="checkbox" checked={multiPlatformOnly} onChange={event => setMultiPlatformOnly(event.target.checked)} />Somente multiplataforma</label></div>
          <div className="flex flex-wrap items-center gap-3 sm:col-span-2 lg:col-span-4"><button type="button" onClick={() => setShowSources(value => !value)} className="flex items-center gap-1.5 text-[8px] text-[#808080] hover:text-white"><FileSearch className="h-3 w-3" />{showSources ? 'Ocultar status das fontes' : 'Ver status das fontes'}</button><button type="button" onClick={clearFilters} className="text-[8px] text-[#FF7F50] hover:text-white">Limpar filtros</button></div>
        </div>}
      </div>

      <div className="mt-5 flex flex-col gap-3 border-b border-white/[0.07] pb-3 sm:flex-row sm:items-end sm:justify-between">
        <div className="flex min-w-0 gap-4 overflow-x-auto" role="tablist" aria-label="Visões do Radar">
          {([['hot', 'Em Alta'], ['emerging', 'Emergentes'], ['personal', 'Para Você']] as const).map(([key, label]) => <button key={key} type="button" role="tab" onClick={() => setView(key)} aria-selected={view === key} className={`clicko-radar-tab relative shrink-0 pb-2 text-[9px] font-medium ${view === key ? 'text-white after:absolute after:inset-x-0 after:-bottom-[13px] after:h-px after:bg-[#FF7F50]' : 'text-[#808080] hover:text-white'}`}>{label}</button>)}
        </div>
        <label className="flex shrink-0 items-center gap-2 text-[8px] text-[#808080]">Ordenar por<select value={sortBy} onChange={event => setSortBy(event.target.value as typeof sortBy)} className="h-8 rounded-lg border border-white/[0.08] bg-black px-2 text-[8px] text-white"><option value="score">Trend Score</option><option value="growth">Maior crescimento</option><option value="recent">Mais recentes</option><option value="relevance">Maior relevância</option></select></label>
      </div>
      {!historyAvailable && <p className="mt-2 text-[8px] text-[#808080]">Histórico temporariamente indisponível; sinais atuais continuam visíveis.</p>}

      {showSources && (
        <div className="mt-3 flex flex-wrap gap-2" aria-label="Disponibilidade das fontes">
          {sources.map((source) => <span key={source.id} className="flex items-center gap-2 rounded-full border border-white/[0.07] px-2.5 py-1.5 text-[8px] text-[#808080]"><span className={`h-1.5 w-1.5 rounded-full ${source.available ? 'bg-[#FF7F50]' : 'bg-[#808080]'}`} />{source.label}<span className="opacity-70">{source.available ? 'disponível' : 'indisponível'}</span></span>)}
        </div>
      )}

      {loading ? (
        <div className="mt-4 overflow-hidden rounded-xl border border-white/[0.07]">
          <ClickoLoader context="section" label="Carregando tendências" message="Buscando tendências…" />
        </div>
      ) : visibleTrends.length ? (
        <div className="mt-4 divide-y divide-white/[0.06] overflow-hidden rounded-xl border border-white/[0.07] bg-[rgba(128,128,128,0.14)]">
          {visibleTrends.map((trend, index) => {
            const meta = statusMeta[trend.status];
            const StatusIcon = meta.icon;
            const evidenceSources = [...new Set(trend.evidence.map((evidence) => sourceShortLabel[evidence.source]))].slice(0, 3);
            return <article key={trend.id} className="group grid gap-3 p-4 transition-colors hover:bg-white/[0.018] sm:grid-cols-[28px_minmax(0,1fr)_auto] sm:items-center sm:gap-4 sm:p-5">
              <span className="hidden text-[9px] tabular-nums text-[#808080] sm:block">{String(index + 1).padStart(2, '0')}</span>
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2"><span className={`flex items-center gap-1 text-[7px] font-semibold uppercase tracking-[0.12em] ${meta.tone}`}><StatusIcon className="h-3 w-3" />{meta.label}</span><span className="text-[7px] text-[#808080]">{categoryLabels[trend.category]}</span>{trend.growthPercent !== undefined && <span className={`text-[7px] font-medium ${trend.direction === 'falling' ? 'text-[#808080]' : 'text-[#F28500]'}`}>{trend.direction === 'falling' ? '' : '+'}{Math.round(trend.growthPercent)}%</span>}</div>
                <button type="button" onClick={() => { setSelectedTrend(trend); recordInteraction(trend, 'opened'); }} className="mt-1.5 block max-w-full text-left"><h3 className="truncate text-[14px] font-medium tracking-[-0.018em] text-white group-hover:text-[#FF7F50] sm:text-[15px]">{trend.title}</h3></button>
                <p className="mt-1 line-clamp-1 text-[9px] leading-4 text-[#808080]">{trend.description}</p>
                <div className="mt-2 flex flex-wrap items-center gap-1.5">{evidenceSources.map((source) => <span key={source} title={source} className="grid h-5 min-w-5 place-items-center rounded-full border border-white/[0.07] px-1.5 text-[6px] font-medium text-[#808080]">{source === 'Google Trends' ? 'GT' : source === 'Notícias' ? 'N' : source === 'YouTube' ? 'YT' : 'P'}</span>)}{trend.brandRelevance >= 50 && <span className="text-[7px] text-[#F28500]">Para sua marca</span>}</div>
              </div>
              <div className="flex items-center justify-between gap-3 sm:justify-end">
                <div className="text-right"><span className="block text-[7px] uppercase tracking-[0.11em] text-[#808080]">Trend Score</span><strong className="mt-0.5 block text-[17px] font-medium tabular-nums text-white">{trend.trendScore}</strong></div>
                <button type="button" onClick={() => { setSelectedTrend(trend); recordInteraction(trend, 'opened'); }} className="h-8 rounded-lg border border-white/[0.08] px-3 text-[8px] font-medium text-white hover:bg-white/[0.04]">Ver detalhes</button>
              </div>
            </article>;
          })}
        </div>
      ) : (
        <div className="mt-4 flex min-h-[180px] flex-col items-center justify-center rounded-xl border border-dashed border-white/[0.08] px-6 text-center"><Radar className="h-5 w-5 text-[#808080]" /><h3 className="mt-3 text-[13px] font-medium text-white">Nenhuma tendência encontrada para esses filtros</h3><p className="mt-1 max-w-md text-[9px] leading-4 text-[#808080]">{error ? 'Não foi possível atualizar o Radar agora. Tente novamente em instantes.' : message || 'Ajuste o recorte ou limpe os filtros para ampliar os resultados.'}</p><div className="mt-4 flex gap-2"><button type="button" onClick={clearFilters} className="rounded-lg bg-[#FF7F50] px-3 py-2 text-[8px] font-semibold text-black">Limpar filtros</button><button type="button" onClick={() => void refreshRadar(true)} className="rounded-lg border border-white/[0.08] px-3 py-2 text-[8px] text-white hover:bg-white/[0.03]">Tentar novamente</button></div></div>
      )}

      {!!visibleTrends.length && <div className="mt-3 flex flex-col gap-1 text-[8px] text-[#808080] sm:flex-row sm:items-center sm:justify-between"><span>Selecione uma tendência para entender o contexto e transformar o sinal em conteúdo.</span><span>{visibleTrends.length} resultado(s)</span></div>}

      {selectedTrend && createPortal(
        <div className="clicko-radar-dialog fixed inset-0 z-[80] flex items-end justify-center bg-black/70 p-3 backdrop-blur-sm sm:items-center" role="dialog" aria-modal="true" aria-label={`Evidências de ${selectedTrend.title}`} onMouseDown={(event) => { if (event.target === event.currentTarget) setSelectedTrend(null); }}>
          <div className="clicko-radar-dialog-panel custom-scrollbar max-h-[92vh] w-full max-w-2xl overflow-y-auto rounded-2xl border border-white/[0.09] bg-[rgba(128,128,128,0.14)] p-5 shadow-2xl shadow-black/60 sm:p-6">
            <div className="flex items-start justify-between gap-4"><div className="min-w-0"><span className={`text-[8px] font-semibold uppercase tracking-[0.13em] ${statusMeta[selectedTrend.status].tone}`}>{statusMeta[selectedTrend.status].label}</span><h3 className="mt-2 text-[21px] font-medium tracking-[-0.03em] text-white sm:text-[24px]">{selectedTrend.title}</h3><p className="mt-1 text-[8px] text-[#808080]">{categoryLabels[selectedTrend.category]} · {formatRelativeTime(selectedTrend.updatedAt)}</p></div><button type="button" onClick={() => setSelectedTrend(null)} className="grid h-8 w-8 shrink-0 place-items-center rounded-lg border border-white/[0.08] text-[#808080] hover:bg-white/[0.04] hover:text-white" aria-label="Fechar detalhes"><X className="h-4 w-4" /></button></div>

            <section className="mt-5 rounded-xl border border-white/[0.07] p-4" aria-label="Resumo da tendência">
              <div className="grid gap-4 sm:grid-cols-2">
                <div><span className="text-[7px] uppercase tracking-[0.13em] text-[#808080]">O que está acontecendo</span><p className="mt-1.5 text-[10px] leading-5 text-white">{selectedTrend.description}</p></div>
                <div><span className="text-[7px] uppercase tracking-[0.13em] text-[#808080]">Por que importa</span><p className="mt-1.5 text-[10px] leading-5 text-white">{selectedTrend.opportunity || selectedTrend.inference}</p></div>
              </div>
              <div className="mt-4 flex flex-wrap gap-x-5 gap-y-2 border-t border-white/[0.06] pt-3 text-[8px] text-[#808080]"><span>Onde: <strong className="font-medium text-white">{selectedTrend.region === 'BR' ? 'Brasil' : 'Global'} · {[...new Set(selectedTrend.evidence.map(item => sourceShortLabel[item.source]))].join(', ')}</strong></span><span>Estágio: <strong className={statusMeta[selectedTrend.status].tone}>{statusMeta[selectedTrend.status].label}</strong></span><span>Momento: <strong className={timingMeta[selectedTrend.timing].className}>{timingMeta[selectedTrend.timing].label}</strong></span></div>
            </section>

            <div className="mt-4 grid grid-cols-3 divide-x divide-white/[0.06] rounded-xl border border-white/[0.07] py-3 text-center"><div><span className="block text-[7px] uppercase tracking-[0.11em] text-[#808080]">Trend Score</span><strong className="mt-1 block text-[18px] font-medium text-white">{selectedTrend.trendScore}</strong></div><div><span className="block text-[7px] uppercase tracking-[0.11em] text-[#808080]">Relevância</span><strong className="mt-1 block text-[18px] font-medium text-white">{selectedTrend.brandRelevance}</strong></div><div><span className="block text-[7px] uppercase tracking-[0.11em] text-[#808080]">Confiança</span><strong className="mt-1 block text-[9px] font-medium text-white">{confidenceMeta[selectedTrend.confidence]}</strong></div></div>

            <button type="button" onClick={() => setShowDetailData(value => !value)} aria-expanded={showDetailData} className="mt-4 flex w-full items-center justify-between rounded-lg border border-white/[0.07] px-3 py-2.5 text-left text-[8px] font-medium text-white hover:bg-white/[0.025]"><span>Dados, histórico e termos relacionados</span><ChevronDown className={`h-3.5 w-3.5 text-[#808080] transition-transform ${showDetailData ? 'rotate-180' : ''}`} /></button>
            {showDetailData && <div className="mt-3 space-y-4">
              {!!selectedTrend.history?.length && <section aria-label="Histórico do Trend Score"><div className="flex items-center justify-between text-[8px] text-[#808080]"><span>Evolução do Trend Score</span><span>{selectedTrend.history.length} observação(ões)</span></div><div className="mt-2 flex h-14 items-end gap-1 rounded-lg border border-white/[0.06] p-2">{selectedTrend.history.slice(-24).map((point, index) => <span key={`${point.observedAt}-${index}`} title={`${new Date(point.observedAt).toLocaleString('pt-BR')}: ${point.score}/100`} className="min-w-0 flex-1 rounded-sm bg-[#FF7F50]/55" style={{ height: `${Math.max(4, point.score)}%` }} />)}</div></section>}
              <div className="grid gap-4 sm:grid-cols-2"><section><span className="flex items-center gap-1.5 text-[7px] uppercase tracking-[0.13em] text-[#FF7F50]"><CheckCircle2 className="h-3 w-3" />Sinais observados</span><p className="mt-1.5 text-[9px] leading-5 text-[#808080]">{selectedTrend.dataExplanation}</p></section><section><span className="flex items-center gap-1.5 text-[7px] uppercase tracking-[0.13em] text-[#6EB8F5]"><KlicSymbol className="h-3 w-3" />Leitura da KLIC</span><p className="mt-1.5 text-[9px] leading-5 text-[#808080]">{selectedTrend.inference}</p></section></div>
              <section><div className="flex items-center justify-between"><span className="text-[7px] uppercase tracking-[0.13em] text-[#808080]">Fontes públicas</span><span className="text-[7px] text-[#808080]">{selectedTrend.evidence.length} sinal(is)</span></div><div className="mt-2 divide-y divide-white/[0.055] rounded-xl border border-white/[0.065]">{selectedTrend.evidence.map((evidence) => <a key={evidence.id} href={evidence.url} target="_blank" rel="noreferrer" className="flex items-start gap-3 p-3 hover:bg-white/[0.025]"><Globe2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#FF7F50]" /><span className="min-w-0 flex-1"><strong className="block text-[9px] font-medium text-white">{evidence.title}</strong><span className="mt-1 block text-[7px] text-[#808080]">{evidence.sourceLabel}{evidence.metricLabel ? ` · ${evidence.metricLabel}` : ''}</span></span><ExternalLink className="h-3 w-3 shrink-0 text-[#808080]" /></a>)}</div></section>
              {selectedTrend.relatedTerms.length > 0 && <div className="flex flex-wrap items-center gap-1.5">{selectedTrend.relatedTerms.map((term) => <span key={term} className="rounded-full border border-white/[0.06] px-2 py-1 text-[7px] text-[#808080]">{term}</span>)}</div>}
            </div>}

            <section className="mt-4 rounded-xl border border-white/[0.07] p-4"><span className="flex items-center gap-1.5 text-[7px] uppercase tracking-[0.13em] text-[#FF7F50]"><Target className="h-3 w-3" />Direção criativa</span><p className="mt-2 text-[9px] leading-5 text-[#808080]">{selectedTrend.angle}</p><div className="mt-2 text-[8px] text-[#808080]">Formato sugerido: <strong className="font-medium text-white">{selectedTrend.format}</strong></div></section>

            <div className="mt-5 grid gap-2 sm:grid-cols-2"><button type="button" onClick={() => exploreWithKlic(selectedTrend, 'analyze')} className="h-10 rounded-lg border border-[#6EB8F5]/35 bg-[#6EB8F5]/[0.08] px-4 text-[9px] font-semibold text-[#6EB8F5]"><KlicSymbol className="mr-1.5 inline h-3 w-3" />Analisar com a KLIC</button><button type="button" onClick={() => exploreWithKlic(selectedTrend)} className="h-10 rounded-lg bg-[#FF7F50] px-4 text-[9px] font-semibold text-black">Criar conteúdo</button></div>
            <div className="relative mt-2"><button type="button" onClick={() => setShowMoreActions(value => !value)} aria-expanded={showMoreActions} className="flex h-9 w-full items-center justify-center gap-1.5 rounded-lg border border-white/[0.07] text-[8px] text-[#808080] hover:text-white"><MoreHorizontal className="h-3.5 w-3.5" />Mais ações</button>{showMoreActions && <div className="mt-2 grid gap-1 rounded-xl border border-white/[0.08] bg-black p-2 sm:grid-cols-2"><button type="button" onClick={() => exploreWithKlic(selectedTrend, 'ideas')} className="rounded-lg px-3 py-2 text-left text-[8px] text-white hover:bg-white/[0.04]">Gerar ideias</button><button type="button" onClick={() => exploreWithKlic(selectedTrend, 'script')} className="rounded-lg px-3 py-2 text-left text-[8px] text-white hover:bg-white/[0.04]">Criar roteiro</button><button type="button" onClick={() => exploreWithKlic(selectedTrend, 'caption')} className="rounded-lg px-3 py-2 text-left text-[8px] text-white hover:bg-white/[0.04]">Criar legenda</button>{canAccess('create-image') && <button type="button" onClick={() => sendToStudio(selectedTrend, 'create-image')} className="rounded-lg px-3 py-2 text-left text-[8px] text-white hover:bg-white/[0.04]">Criar imagem</button>}{canAccess('create-video') && <button type="button" onClick={() => sendToStudio(selectedTrend, 'create-video')} className="rounded-lg px-3 py-2 text-left text-[8px] text-white hover:bg-white/[0.04]">Criar vídeo</button>}{canAccess('calendar') && <button type="button" onClick={() => addToCalendar(selectedTrend)} className="rounded-lg px-3 py-2 text-left text-[8px] text-white hover:bg-white/[0.04]">Adicionar ao calendário</button>}</div>}</div>
          </div>
        </div>, document.body
      )}
    </section>
  );
}
