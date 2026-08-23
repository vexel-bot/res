import React from 'react';
import {
  AlertCircle,
  Bot,
  CalendarDays,
  Check,
  ChevronLeft,
  ChevronRight,
  Clock3,
  Filter,
  FolderOpen,
  History,
  LayoutList,
  LoaderCircle,
  Plus,
  RefreshCw,
  Send,
  Sparkles,
  WandSparkles,
  UserRound,
  X,
} from 'lucide-react';
import { useGovernance } from '../context/GovernanceContext';
import { useOperations } from '../context/OperationsContext';
import type { ApprovalStage, NavigationTab, Post, PostFormat, PostStatus, SocialPlatform } from '../types';
import { postStatusLabel } from '../utils/localization';

interface EditorialCalendarViewProps {
  posts: Post[];
  onSelectPost: (post: Post) => void;
  onNewPost: () => void;
  onNavigate?: (tab: NavigationTab) => void;
}

type ViewMode = 'month' | 'week' | 'list';
type CalendarSuggestion = { id: string; title: string; platform: SocialPlatform; format: PostFormat; suggestedAt: string; copy: string; rationale: string };

const visiblePlatforms: Array<{ id: SocialPlatform; label: string; short: string }> = [
  { id: 'instagram', label: 'Instagram', short: 'IG' },
  { id: 'facebook', label: 'Facebook', short: 'FB' },
  { id: 'tiktok', label: 'TikTok', short: 'TT' },
  { id: 'linkedin', label: 'LinkedIn', short: 'IN' },
  { id: 'youtube', label: 'YouTube', short: 'YT' },
  { id: 'threads', label: 'Threads', short: 'TH' },
];

const formats: Array<{ id: PostFormat; label: string }> = [
  { id: 'post', label: 'Post' }, { id: 'carousel', label: 'Carrossel' }, { id: 'reels', label: 'Reels' },
  { id: 'story', label: 'Story' }, { id: 'script', label: 'Roteiro de vídeo' }, { id: 'youtube-short', label: 'YouTube Short' },
  { id: 'linkedin-article', label: 'Artigo' }, { id: 'thread', label: 'Thread' },
];

const statusStyle: Record<PostStatus, string> = {
  draft: 'bg-white/[0.06] text-[#949da2]', in_production: 'bg-sky-400/[0.08] text-sky-300',
  in_review: 'bg-violet-400/[0.08] text-violet-300', pending_approval: 'bg-amber-400/[0.08] text-amber-300',
  approved: 'bg-[#8bd132]/[0.08] text-[#8bd132]', changes_requested: 'bg-orange-400/[0.08] text-orange-300',
  rejected: 'bg-red-400/[0.08] text-red-300', scheduled: 'bg-cyan-400/[0.08] text-cyan-300',
  published: 'bg-emerald-400/[0.08] text-emerald-300', error: 'bg-red-400/[0.08] text-red-300',
};

const statusDot: Record<PostStatus, string> = {
  draft: 'bg-[#737d82]', in_production: 'bg-sky-300', in_review: 'bg-violet-300', pending_approval: 'bg-amber-300',
  approved: 'bg-[#8bd132]', changes_requested: 'bg-orange-300', rejected: 'bg-red-300', scheduled: 'bg-cyan-300',
  published: 'bg-emerald-300', error: 'bg-red-400',
};

const pad = (value: number) => String(value).padStart(2, '0');
const dateKey = (date: Date) => `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
const toDateInput = (value?: string) => value ? dateKey(new Date(value)) : dateKey(new Date());
const startOfWeek = (date: Date) => { const result = new Date(date); result.setDate(result.getDate() - result.getDay()); result.setHours(0, 0, 0, 0); return result; };
const formatPlatform = (platform: SocialPlatform) => visiblePlatforms.find((item) => item.id === platform)?.label || platform;
const formatName = (format: PostFormat) => formats.find((item) => item.id === format)?.label || format;
const scheduledTime = (post: Post) => post.scheduledAt ? new Date(post.scheduledAt).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }) : 'Sem horário';

const approvalStatus = (stage?: ApprovalStage): PostStatus | undefined => {
  if (!stage) return undefined;
  return ({ draft: 'draft', in_review: 'in_review', pending_approval: 'pending_approval', approved: 'approved', changes_requested: 'changes_requested', rejected: 'rejected', published: 'published' } as const)[stage];
};

export const EditorialCalendarView: React.FC<EditorialCalendarViewProps> = ({ posts, onSelectPost, onNewPost, onNavigate }) => {
  const {
    activeWorkspace, activeCampaign, activeClient, contextSnapshot, clients, campaigns, connectedAccounts, assets,
    addPosts, updatePosts,
  } = useOperations();
  const { currentUser, users, approvals, workspace, environmentMode, isMaster, createApproval, approvalAction } = useGovernance();
  const [viewMode, setViewMode] = React.useState<ViewMode>('month');
  const [currentDate, setCurrentDate] = React.useState(() => new Date());
  const [showFilters, setShowFilters] = React.useState(false);
  const [filterPlatform, setFilterPlatform] = React.useState('all');
  const [filterStatus, setFilterStatus] = React.useState('all');
  const [filterFormat, setFilterFormat] = React.useState('all');
  const [filterResponsible, setFilterResponsible] = React.useState('all');
  const [filterCampaign, setFilterCampaign] = React.useState('all');
  const [selectedPostId, setSelectedPostId] = React.useState<string>();
  const [draggedPostId, setDraggedPostId] = React.useState<string>();
  const [notice, setNotice] = React.useState<{ tone: 'success' | 'error'; text: string }>();
  const [createOpen, setCreateOpen] = React.useState(false);
  const [aiOpen, setAiOpen] = React.useState(false);
  const [aiObjective, setAiObjective] = React.useState('');
  const [aiLoading, setAiLoading] = React.useState(false);
  const [aiSuggestions, setAiSuggestions] = React.useState<CalendarSuggestion[]>([]);
  const [selectedSuggestions, setSelectedSuggestions] = React.useState<string[]>([]);
  const [form, setForm] = React.useState({
    title: '', copy: '', date: dateKey(new Date()), time: '09:00', channels: [] as SocialPlatform[], format: 'post' as PostFormat,
    status: 'draft' as Extract<PostStatus, 'draft' | 'in_production' | 'scheduled'>, responsibleId: currentUser?.id || '', campaignId: activeCampaign?.id || '',
    assetIds: [] as string[], requiresApproval: false,
  });

  const authorizedAccounts = React.useMemo(() => connectedAccounts.filter((account) => account.connected && ['connected', 'synced'].includes(account.connectionStatus || '')), [connectedAccounts]);
  const connectedPlatforms = React.useMemo(() => [...new Set(authorizedAccounts.map((account) => account.platform))], [authorizedAccounts]);
  const approvalByContent = React.useMemo(() => new Map(approvals.map((item) => [item.contentId, item])), [approvals]);
  const normalizedPosts = React.useMemo(() => posts.map((post) => {
    const approval = approvalByContent.get(post.id);
    return approval ? { ...post, status: approvalStatus(approval.stage) || post.status, scheduledAt: approval.scheduledAt || post.scheduledAt } : post;
  }), [approvalByContent, posts]);
  const selectedPost = normalizedPosts.find((post) => post.id === selectedPostId);
  const selectedApproval = selectedPost ? approvalByContent.get(selectedPost.id) : undefined;

  const filteredPosts = React.useMemo(() => normalizedPosts.filter((post) => {
    const channels = post.channels?.length ? post.channels : [post.platform];
    if (filterPlatform !== 'all' && !channels.includes(filterPlatform as SocialPlatform)) return false;
    if (filterStatus !== 'all' && post.status !== filterStatus) return false;
    if (filterFormat !== 'all' && post.format !== filterFormat) return false;
    if (filterCampaign !== 'all' && post.campaignId !== filterCampaign) return false;
    if (filterResponsible !== 'all' && post.responsibleId !== filterResponsible && post.author !== users.find((user) => user.id === filterResponsible)?.name) return false;
    return true;
  }), [filterCampaign, filterFormat, filterPlatform, filterResponsible, filterStatus, normalizedPosts, users]);

  const calendarDates = React.useMemo(() => {
    const start = viewMode === 'week' ? startOfWeek(currentDate) : startOfWeek(new Date(currentDate.getFullYear(), currentDate.getMonth(), 1));
    return Array.from({ length: viewMode === 'week' ? 7 : 42 }, (_, index) => { const day = new Date(start); day.setDate(start.getDate() + index); return day; });
  }, [currentDate, viewMode]);

  const postsByDay = React.useMemo(() => {
    const grouped = new Map<string, Post[]>();
    filteredPosts.forEach((post) => {
      if (!post.scheduledAt) return;
      const key = dateKey(new Date(post.scheduledAt));
      grouped.set(key, [...(grouped.get(key) || []), post].sort((a, b) => String(a.scheduledAt).localeCompare(String(b.scheduledAt))));
    });
    return grouped;
  }, [filteredPosts]);

  const futurePosts = React.useMemo(() => filteredPosts.filter((post) => post.scheduledAt && new Date(post.scheduledAt).getTime() >= Date.now() && !['published', 'rejected'].includes(post.status)).sort((a, b) => String(a.scheduledAt).localeCompare(String(b.scheduledAt))).slice(0, 4), [filteredPosts]);

  const planningSignals = React.useMemo(() => {
    const viewKeys = calendarDates.filter((date) => viewMode === 'week' || date.getMonth() === currentDate.getMonth()).map(dateKey);
    const empty = viewKeys.filter((key) => !(postsByDay.get(key)?.length)).length;
    const overloaded = viewKeys.filter((key) => (postsByDay.get(key)?.length || 0) >= 3).length;
    const counts = new Map<SocialPlatform, number>();
    filteredPosts.forEach((post) => (post.channels?.length ? post.channels : [post.platform]).forEach((platform) => counts.set(platform, (counts.get(platform) || 0) + 1)));
    const total = [...counts.values()].reduce((sum, value) => sum + value, 0);
    const dominant = [...counts.entries()].sort((a, b) => b[1] - a[1])[0];
    const bestTime = authorizedAccounts.find((account) => account.bestTime && account.bestTime !== 'Sem dados');
    return [
      { label: 'Espaços disponíveis', value: `${empty} dias livres`, tone: empty > 4 ? 'positive' : 'neutral' },
      { label: 'Dias concentrados', value: overloaded ? `${overloaded} com 3+ conteúdos` : 'Cadência equilibrada', tone: overloaded ? 'warning' : 'positive' },
      { label: 'Distribuição por canal', value: dominant && total && dominant[1] / total > 0.6 ? `${formatPlatform(dominant[0])} concentra ${Math.round(dominant[1] / total * 100)}%` : 'Sem concentração excessiva', tone: dominant && total && dominant[1] / total > 0.6 ? 'warning' : 'positive' },
      ...(bestTime ? [{ label: 'Dado conectado', value: `${formatPlatform(bestTime.platform)} recomenda ${bestTime.bestTime}`, tone: 'positive' }] : []),
    ];
  }, [authorizedAccounts, calendarDates, currentDate, filteredPosts, postsByDay, viewMode]);

  const openCreate = (date = new Date()) => {
    const firstConnected = connectedPlatforms[0];
    setForm({ title: '', copy: '', date: dateKey(date), time: '09:00', channels: firstConnected ? [firstConnected] : [], format: 'post', status: 'draft', responsibleId: currentUser?.id || '', campaignId: activeCampaign?.id || '', assetIds: [], requiresApproval: false });
    setCreateOpen(true);
    setNotice(undefined);
  };

  const toggleChannel = (platform: SocialPlatform) => setForm((current) => ({ ...current, channels: current.channels.includes(platform) ? current.channels.filter((item) => item !== platform) : [...current.channels, platform] }));
  const toggleAsset = (id: string) => setForm((current) => ({ ...current, assetIds: current.assetIds.includes(id) ? current.assetIds.filter((item) => item !== id) : [...current.assetIds, id] }));

  const hasPublishingPermission = (platform: SocialPlatform) => authorizedAccounts.some((account) => account.platform === platform && (account.permissions || []).some((permission) => /publish|content_publish|manage_posts|youtube\.upload/i.test(permission)));

  const saveContent = async () => {
    if (!form.title.trim()) return setNotice({ tone: 'error', text: 'Informe um título para o conteúdo.' });
    if (!form.channels.length) return setNotice({ tone: 'error', text: 'Selecione ao menos uma rede social para o planejamento.' });
    if (form.status === 'scheduled') {
      const unavailable = form.channels.filter((platform) => !hasPublishingPermission(platform));
      if (unavailable.length) return setNotice({ tone: 'error', text: `Para agendar, autorize publicação em ${unavailable.map(formatPlatform).join(', ')} na área Conexões.` });
    }
    const scheduledAt = new Date(`${form.date}T${form.time}:00`).toISOString();
    const responsible = users.find((user) => user.id === form.responsibleId) || currentUser;
    const needsApproval = environmentMode === 'company' && Boolean(workspace?.settings.requireApproval) && (currentUser?.role !== 'master' || form.requiresApproval);
    const postId = `post-${Date.now()}`;
    const createdAt = new Date().toISOString();
    const post: Post = {
      id: postId, workspaceId: activeWorkspace.id, title: form.title.trim(), copy: form.copy.trim(), hashtags: [],
      platform: form.channels[0], channels: form.channels, format: form.format, scheduledAt,
      status: needsApproval ? 'pending_approval' : form.status, author: currentUser?.name || 'Usuário', createdAt,
      responsibleId: responsible?.id, responsibleName: responsible?.name, campaignId: form.campaignId || undefined,
      strategyId: form.campaignId || undefined, assetIds: form.assetIds, origin: 'manual', contextRevision: contextSnapshot.revision,
      history: [{ id: `post-history-${Date.now()}`, action: 'created', detail: needsApproval ? 'Conteúdo criado e enviado para aprovação' : 'Conteúdo criado pelo Calendário', actorName: currentUser?.name || 'Usuário', createdAt }],
    };
    addPosts([post]);
    if (needsApproval) {
      const approval = await createApproval({ contentId: post.id, title: post.title, copy: post.copy, platform: post.platform, format: post.format, scheduledAt: post.scheduledAt, campaignId: post.campaignId, strategyId: post.strategyId });
      if (!approval) updatePosts((current) => current.map((item) => item.id === post.id ? { ...item, status: 'draft' } : item));
    }
    setCreateOpen(false);
    setNotice({ tone: 'success', text: needsApproval ? 'Conteúdo adicionado e enviado para aprovação.' : 'Conteúdo adicionado ao calendário.' });
  };

  const movePost = (postId: string, date: Date) => {
    updatePosts((current) => current.map((post) => {
      if (post.id !== postId || post.status === 'published') return post;
      const previous = post.scheduledAt ? new Date(post.scheduledAt) : new Date();
      const scheduledAt = new Date(date); scheduledAt.setHours(previous.getHours(), previous.getMinutes(), 0, 0);
      return { ...post, scheduledAt: scheduledAt.toISOString(), history: [{ id: `post-history-${Date.now()}`, action: 'rescheduled', detail: `Reagendado para ${date.toLocaleDateString('pt-BR')}`, actorName: currentUser?.name || 'Usuário', createdAt: new Date().toISOString() }, ...(post.history || [])] };
    }));
    setDraggedPostId(undefined);
    setNotice({ tone: 'success', text: `Conteúdo reagendado para ${date.toLocaleDateString('pt-BR')}.` });
  };

  const handleApproval = async (action: 'approve' | 'request_changes') => {
    if (!selectedPost || !selectedApproval) return;
    const comment = action === 'request_changes' ? 'Ajustes solicitados pelo Calendário.' : undefined;
    const result = await approvalAction(selectedApproval.id, action, comment);
    if (!result) return;
    const nextStatus: PostStatus = action === 'approve' ? 'approved' : 'changes_requested';
    updatePosts((current) => current.map((post) => post.id === selectedPost.id ? { ...post, status: nextStatus, history: [{ id: `post-history-${Date.now()}`, action, detail: action === 'approve' ? 'Conteúdo aprovado' : 'Alterações solicitadas', actorName: currentUser?.name || 'Usuário', createdAt: new Date().toISOString() }, ...(post.history || [])] } : post));
    setNotice({ tone: 'success', text: action === 'approve' ? 'Conteúdo aprovado.' : 'Alterações solicitadas ao responsável.' });
  };

  const generatePlan = async () => {
    if (!aiObjective.trim()) return setNotice({ tone: 'error', text: 'Descreva o objetivo do planejamento.' });
    setAiLoading(true); setAiSuggestions([]); setSelectedSuggestions([]); setNotice(undefined);
    const periodStart = viewMode === 'week' ? startOfWeek(currentDate) : new Date(currentDate.getFullYear(), currentDate.getMonth(), 1);
    const periodEnd = viewMode === 'week' ? new Date(periodStart.getTime() + 7 * 86_400_000 - 1) : new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 0, 23, 59, 59);
    try {
      const response = await fetch('/api/ai/plan-calendar', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({
        objective: aiObjective, periodStart: periodStart.toISOString(), periodEnd: periodEnd.toISOString(), connectedPlatforms,
        existingPosts: normalizedPosts.map((post) => ({ title: post.title, platform: post.platform, status: post.status, scheduledAt: post.scheduledAt })),
        workspaceId: activeWorkspace.id, contextProfile: contextSnapshot, clientContext: activeClient, strategyContext: activeCampaign,
      }) });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.error || 'Não foi possível gerar o planejamento.');
      setAiSuggestions(data.suggestions || []);
      setSelectedSuggestions((data.suggestions || []).map((item: CalendarSuggestion) => item.id));
    } catch (error) {
      setNotice({ tone: 'error', text: error instanceof Error ? error.message : 'Não foi possível gerar o planejamento.' });
    } finally { setAiLoading(false); }
  };

  const addSuggestions = () => {
    const selected = aiSuggestions.filter((item) => selectedSuggestions.includes(item.id));
    if (!selected.length) return;
    const createdAt = new Date().toISOString();
    addPosts(selected.map((suggestion, index): Post => ({
      id: `post-ai-${Date.now()}-${index}`, workspaceId: activeWorkspace.id, title: suggestion.title, platform: suggestion.platform,
      channels: [suggestion.platform], format: suggestion.format, copy: suggestion.copy, hashtags: [], scheduledAt: suggestion.suggestedAt,
      status: 'draft', author: currentUser?.name || 'KLIC', createdAt, responsibleId: currentUser?.id, responsibleName: currentUser?.name,
      campaignId: activeCampaign?.id, strategyId: activeCampaign?.id, origin: 'ai', contextRevision: contextSnapshot.revision,
      history: [{ id: `post-history-ai-${Date.now()}-${index}`, action: 'ai_suggestion_accepted', detail: 'Sugestão da KLIC revisada e adicionada como rascunho', actorName: currentUser?.name || 'Usuário', createdAt }],
    })));
    setAiOpen(false); setAiSuggestions([]); setSelectedSuggestions([]);
    setNotice({ tone: 'success', text: `${selected.length} sugestão(ões) adicionada(s) como rascunho para revisão.` });
  };

  const navigatePeriod = (direction: number) => setCurrentDate((date) => { const next = new Date(date); viewMode === 'month' ? next.setMonth(next.getMonth() + direction) : next.setDate(next.getDate() + direction * 7); return next; });
  const periodTitle = viewMode === 'week'
    ? `${startOfWeek(currentDate).toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' })} — ${new Date(startOfWeek(currentDate).getTime() + 6 * 86_400_000).toLocaleDateString('pt-BR', { day: '2-digit', month: 'short', year: 'numeric' })}`
    : currentDate.toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' });

  return <div className="mx-auto w-full max-w-[1500px] space-y-5 p-5 sm:p-6 2xl:p-9">
    <header className="flex flex-col gap-5 border-b border-white/[0.06] pb-6 xl:flex-row xl:items-end xl:justify-between">
      <div className="max-w-2xl"><p className="text-[10px] font-medium uppercase tracking-[0.22em] text-[#8bd132]">Operação de conteúdo</p><h1 className="mt-2 text-2xl font-semibold tracking-[-0.02em] text-white">Calendário</h1><p className="mt-2 text-sm leading-6 text-[#879298]">Planeje, aprove, agende e acompanhe cada conteúdo em um fluxo centralizado.</p></div>
      <div className="flex flex-wrap gap-2"><button onClick={() => setAiOpen(true)} className="inline-flex h-9 items-center gap-2 rounded-lg border border-white/[0.08] px-3.5 text-[10px] font-medium text-[#c0c7ca] transition hover:border-white/[0.14] hover:text-white">Planejar com a KLIC</button><button onClick={() => openCreate()} className="inline-flex h-9 items-center gap-2 rounded-lg bg-[#8bd132] px-4 text-[10px] font-semibold text-[#13200d]"><Plus className="h-4 w-4" />Novo conteúdo</button></div>
    </header>

    {notice && <div role="status" className={`flex items-center justify-between gap-4 rounded-xl border px-4 py-3 text-[10px] ${notice.tone === 'error' ? 'border-amber-400/15 bg-amber-400/[0.045] text-amber-100' : 'border-[#8bd132]/15 bg-[#8bd132]/[0.035] text-[#b9c3b3]'}`}><span className="flex items-center gap-2">{notice.tone === 'error' ? <AlertCircle className="h-4 w-4 text-amber-300" /> : <Check className="h-4 w-4 text-[#8bd132]" />}{notice.text}</span><button onClick={() => setNotice(undefined)} aria-label="Fechar aviso"><X className="h-3.5 w-3.5" /></button></div>}

    <section aria-label="Próximos conteúdos" className="rounded-xl border border-white/[0.06] bg-[#141a1d] p-4">
      <div className="mb-3 flex items-center justify-between"><div><h2 className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[#aeb6ba]">Próximos conteúdos</h2><p className="mt-1 text-[9px] text-[#677176]">O que exige atenção nas próximas horas e dias.</p></div><button onClick={() => { setCurrentDate(new Date()); setViewMode('week'); }} className="rounded-lg px-2.5 py-2 text-[9px] text-[#8f999e] hover:bg-white/[0.04] hover:text-white">Ir para hoje</button></div>
      {futurePosts.length ? <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">{futurePosts.map((post) => <button key={post.id} onClick={() => { setSelectedPostId(post.id); onSelectPost(post); }} className="flex min-w-0 items-center gap-3 rounded-lg border border-white/[0.05] bg-black/15 p-3 text-left transition hover:border-white/[0.1]"><span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-white/[0.04] text-[8px] font-semibold text-[#c5cbce]">{visiblePlatforms.find((item) => item.id === post.platform)?.short}</span><span className="min-w-0 flex-1"><strong className="block truncate text-[9px] font-medium text-white">{post.title}</strong><span className="mt-1 block text-[8px] text-[#707a7f]">{new Date(post.scheduledAt!).toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' })} · {scheduledTime(post)}</span></span><span className={`h-1.5 w-1.5 rounded-full ${statusDot[post.status]}`} /></button>)}</div> : <div className="rounded-lg border border-dashed border-white/[0.06] py-4 text-center text-[9px] text-[#667176]">Nenhum conteúdo futuro com os filtros atuais.</div>}
    </section>

    <section className="space-y-3">
      <div className="flex flex-col gap-3 rounded-xl border border-white/[0.06] bg-[#101416] p-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-center gap-2"><button onClick={() => navigatePeriod(-1)} aria-label="Período anterior" className="rounded-lg p-2 text-[#8b959a] hover:bg-white/[0.05] hover:text-white"><ChevronLeft className="h-4 w-4" /></button><button onClick={() => { setCurrentDate(new Date()); }} className="rounded-lg px-2 py-1.5 text-[9px] text-[#8b959a] hover:bg-white/[0.05] hover:text-white">Hoje</button><button onClick={() => navigatePeriod(1)} aria-label="Próximo período" className="rounded-lg p-2 text-[#8b959a] hover:bg-white/[0.05] hover:text-white"><ChevronRight className="h-4 w-4" /></button><h2 className="ml-1 min-w-[170px] capitalize text-[12px] font-semibold text-white">{periodTitle}</h2></div>
        <div className="flex flex-wrap items-center gap-2"><button onClick={() => setShowFilters((value) => !value)} className={`inline-flex h-8 items-center gap-1.5 rounded-lg border px-2.5 text-[9px] ${showFilters ? 'border-[#8bd132]/25 bg-[#8bd132]/[0.045] text-[#8bd132]' : 'border-white/[0.07] text-[#899399]'}`}><Filter className="h-3.5 w-3.5" />Filtros</button><div className="flex rounded-lg border border-white/[0.06] bg-black/15 p-0.5">{([{ id: 'month', label: 'Mês', icon: CalendarDays }, { id: 'week', label: 'Semana', icon: Clock3 }, { id: 'list', label: 'Lista', icon: LayoutList }] as const).map(({ id, label, icon: Icon }) => <button key={id} onClick={() => setViewMode(id)} className={`inline-flex h-7 items-center gap-1.5 rounded-md px-2.5 text-[8px] font-medium ${viewMode === id ? 'bg-white/[0.08] text-white' : 'text-[#687277]'}`}><Icon className="h-3 w-3" />{label}</button>)}</div></div>
      </div>

      {showFilters && <div className="grid gap-2 rounded-xl border border-white/[0.055] bg-white/[0.018] p-3 sm:grid-cols-2 lg:grid-cols-5">
        <FilterSelect label="Plataforma" value={filterPlatform} onChange={setFilterPlatform} options={[['all', 'Todas'], ...visiblePlatforms.map((item) => [item.id, item.label])]} />
        <FilterSelect label="Status" value={filterStatus} onChange={setFilterStatus} options={[['all', 'Todos'], ...Object.entries(postStatusLabel)]} />
        <FilterSelect label="Formato" value={filterFormat} onChange={setFilterFormat} options={[['all', 'Todos'], ...formats.map((item) => [item.id, item.label])]} />
        <FilterSelect label="Responsável" value={filterResponsible} onChange={setFilterResponsible} options={[['all', 'Todos'], ...users.filter((user) => user.status === 'active').map((user) => [user.id, user.name])]} />
        <FilterSelect label="Campanha" value={filterCampaign} onChange={setFilterCampaign} options={[['all', 'Todas'], ...campaigns.map((campaign) => [campaign.id, campaign.name])]} />
      </div>}

      {viewMode === 'list' ? <ListView posts={filteredPosts} onOpen={(post) => { setSelectedPostId(post.id); onSelectPost(post); }} /> : <div className="custom-scrollbar overflow-x-auto rounded-xl border border-white/[0.06] bg-[#101416] p-3">
        <div className="min-w-[820px]"><div className="grid grid-cols-7 border-b border-white/[0.05] pb-2 text-center text-[8px] font-semibold uppercase tracking-[0.12em] text-[#657076]">{['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'].map((day) => <div key={day}>{day}</div>)}</div>
          <div className="mt-2 grid grid-cols-7 gap-1.5">{calendarDates.map((date) => {
            const key = dateKey(date); const dayPosts = postsByDay.get(key) || []; const today = key === dateKey(new Date()); const otherMonth = viewMode === 'month' && date.getMonth() !== currentDate.getMonth();
            return <div key={key} onDragOver={(event) => event.preventDefault()} onDrop={() => draggedPostId && movePost(draggedPostId, date)} className={`group flex ${viewMode === 'week' ? 'min-h-[360px]' : 'min-h-[128px]'} flex-col rounded-lg border p-2 transition ${today ? 'border-[#8bd132]/25 bg-[#8bd132]/[0.035]' : otherMonth ? 'border-white/[0.025] bg-white/[0.008] opacity-40' : 'border-white/[0.045] bg-white/[0.014] hover:border-white/[0.09]'}`}>
              <button onClick={() => openCreate(date)} className="flex items-center justify-between text-left"><span className={`text-[9px] font-medium ${today ? 'text-[#8bd132]' : 'text-[#879196]'}`}>{date.getDate()}</span>{today && <span className="text-[7px] uppercase text-[#8bd132]">Hoje</span>}<Plus className="h-3 w-3 text-[#596267] opacity-0 transition group-hover:opacity-100" /></button>
              <div className="mt-2 space-y-1.5">{dayPosts.slice(0, viewMode === 'week' ? 8 : 3).map((post) => <CalendarEvent key={post.id} post={post} onDrag={() => setDraggedPostId(post.id)} onOpen={() => { setSelectedPostId(post.id); onSelectPost(post); }} />)}{dayPosts.length > (viewMode === 'week' ? 8 : 3) && <button onClick={() => setViewMode('list')} className="w-full py-1 text-center text-[7px] text-[#6f797e]">+{dayPosts.length - 3} conteúdos</button>}</div>
            </div>;
          })}</div>
        </div>
      </div>}
    </section>

    <section aria-label="Planejamento inteligente" className="border-t border-white/[0.06] pt-5"><div className="mb-3 flex items-center gap-2"><WandSparkles className="h-4 w-4 text-[#8bd132]" /><h2 className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[#aeb6ba]">Planejamento inteligente</h2></div><div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">{planningSignals.map((signal) => <div key={signal.label} className="rounded-lg border border-white/[0.05] bg-white/[0.015] px-3 py-2.5"><span className="text-[8px] text-[#677176]">{signal.label}</span><strong className={`mt-1 block text-[9px] font-medium ${signal.tone === 'warning' ? 'text-amber-300' : signal.tone === 'positive' ? 'text-[#aebf9b]' : 'text-[#aeb6ba]'}`}>{signal.value}</strong></div>)}</div></section>

    {createOpen && <CreatePanel form={form} setForm={setForm} connectedPlatforms={connectedPlatforms} assets={assets} users={users} campaigns={campaigns} environmentMode={environmentMode} requiresWorkspaceApproval={Boolean(workspace?.settings.requireApproval)} toggleChannel={toggleChannel} toggleAsset={toggleAsset} onClose={() => setCreateOpen(false)} onSave={saveContent} onAdvanced={() => { setCreateOpen(false); onNewPost(); }} onNavigate={(tab) => { setCreateOpen(false); onNavigate?.(tab); }} />}
    {aiOpen && <AIPlanningPanel objective={aiObjective} setObjective={setAiObjective} loading={aiLoading} suggestions={aiSuggestions} selected={selectedSuggestions} connectedPlatforms={connectedPlatforms} onToggle={(id) => setSelectedSuggestions((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id])} onGenerate={generatePlan} onAdd={addSuggestions} onClose={() => setAiOpen(false)} onConnect={() => { setAiOpen(false); onNavigate?.('connected-accounts'); }} />}
    {selectedPost && <DetailPanel post={selectedPost} approval={selectedApproval} campaignName={campaigns.find((campaign) => campaign.id === selectedPost.campaignId)?.name} assetNames={(selectedPost.assetIds || []).map((id) => assets.find((asset) => asset.id === id)?.title).filter(Boolean) as string[]} canApprove={isMaster && Boolean(selectedApproval && ['pending_approval', 'in_review'].includes(selectedApproval.stage))} onApprove={() => handleApproval('approve')} onRequestChanges={() => handleApproval('request_changes')} onClose={() => setSelectedPostId(undefined)} onFixConnection={() => { setSelectedPostId(undefined); onNavigate?.('connected-accounts'); }} />}
  </div>;
};

function FilterSelect({ label, value, onChange, options }: { label: string; value: string; onChange: (value: string) => void; options: string[][] }) {
  return <label><span className="mb-1.5 block text-[8px] text-[#6d777c]">{label}</span><select value={value} onChange={(event) => onChange(event.target.value)} className="h-9 w-full rounded-lg border border-white/[0.06] bg-[#0d1214] px-2.5 text-[9px] text-[#b8c0c4] outline-none">{options.map(([id, name]) => <option value={id} key={id}>{name}</option>)}</select></label>;
}

function CalendarEvent({ post, onDrag, onOpen }: { key?: React.Key; post: Post; onDrag: () => void; onOpen: () => void }) {
  const channels = post.channels?.length ? post.channels : [post.platform];
  return <button draggable={post.status !== 'published'} onDragStart={onDrag} onClick={onOpen} className="block w-full rounded-md border border-white/[0.045] bg-black/20 p-2 text-left transition hover:border-white/[0.12]"><div className="flex items-start gap-1.5"><span className={`mt-1 h-1.5 w-1.5 shrink-0 rounded-full ${statusDot[post.status]}`} /><span className="min-w-0 flex-1"><strong className="block truncate text-[8px] font-medium text-[#d8dcde]">{post.title}</strong><span className="mt-1 flex items-center gap-1 text-[7px] text-[#687277]"><Clock3 className="h-2.5 w-2.5" />{scheduledTime(post)} · {channels.slice(0, 2).map((platform) => visiblePlatforms.find((item) => item.id === platform)?.short).join(' + ')}{channels.length > 2 ? ` +${channels.length - 2}` : ''}</span></span></div></button>;
}

function ListView({ posts, onOpen }: { posts: Post[]; onOpen: (post: Post) => void }) {
  const sorted = [...posts].sort((a, b) => String(a.scheduledAt || '9999').localeCompare(String(b.scheduledAt || '9999')));
  return <div className="overflow-hidden rounded-xl border border-white/[0.06] bg-[#101416]">{sorted.length ? sorted.map((post) => <button key={post.id} onClick={() => onOpen(post)} className="grid w-full grid-cols-[92px_1fr_auto] items-center gap-3 border-b border-white/[0.045] px-4 py-3 text-left last:border-0 hover:bg-white/[0.018] sm:grid-cols-[125px_1fr_110px_130px]"><span className="text-[8px] text-[#727d82]">{post.scheduledAt ? new Date(post.scheduledAt).toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' }) : 'Sem data'}<strong className="ml-1 font-medium text-[#aab2b6]">{scheduledTime(post)}</strong></span><span className="min-w-0"><strong className="block truncate text-[9px] font-medium text-white">{post.title}</strong><span className="mt-1 block truncate text-[8px] text-[#667176]">{formatPlatform(post.platform)} · {formatName(post.format)} · {post.responsibleName || post.author}</span></span><span className="hidden text-[8px] text-[#707a7f] sm:block">{post.channels?.length || 1} canal(is)</span><span className={`justify-self-end rounded-full px-2 py-1 text-[7px] ${statusStyle[post.status]}`}>{postStatusLabel[post.status]}</span></button>) : <div className="p-10 text-center text-[9px] text-[#657076]">Nenhum conteúdo encontrado.</div>}</div>;
}

type CreationForm = { title: string; copy: string; date: string; time: string; channels: SocialPlatform[]; format: PostFormat; status: Extract<PostStatus, 'draft' | 'in_production' | 'scheduled'>; responsibleId: string; campaignId: string; assetIds: string[]; requiresApproval: boolean };

function CreatePanel({ form, setForm, connectedPlatforms, assets, users, campaigns, environmentMode, requiresWorkspaceApproval, toggleChannel, toggleAsset, onClose, onSave, onAdvanced, onNavigate }: {
  form: CreationForm; setForm: React.Dispatch<React.SetStateAction<CreationForm>>; connectedPlatforms: SocialPlatform[]; assets: ReturnType<typeof useOperations>['assets']; users: ReturnType<typeof useGovernance>['users']; campaigns: ReturnType<typeof useOperations>['campaigns']; environmentMode: ReturnType<typeof useGovernance>['environmentMode']; requiresWorkspaceApproval: boolean; toggleChannel: (platform: SocialPlatform) => void; toggleAsset: (id: string) => void; onClose: () => void; onSave: () => void; onAdvanced: () => void; onNavigate: (tab: NavigationTab) => void;
}) {
  return <div className="fixed inset-0 z-[100] flex justify-end bg-black/70 backdrop-blur-sm" role="dialog" aria-modal="true" aria-labelledby="new-content-title"><button className="absolute inset-0" onClick={onClose} aria-label="Fechar criação" /><aside className="relative h-full w-full max-w-[520px] overflow-y-auto border-l border-white/[0.07] bg-[#111719] p-5 shadow-2xl sm:p-6">
    <div className="flex items-start justify-between border-b border-white/[0.06] pb-5"><div><p className="text-[9px] uppercase tracking-[0.18em] text-[#8bd132]">Planejar conteúdo</p><h2 id="new-content-title" className="mt-1.5 text-lg font-semibold text-white">Novo conteúdo</h2><p className="mt-1 text-[9px] text-[#727d82]">Defina somente o essencial. Você poderá refinar depois.</p></div><button onClick={onClose} aria-label="Fechar" className="rounded-lg p-2 text-[#727d82] hover:bg-white/[0.05] hover:text-white"><X className="h-4 w-4" /></button></div>
    <div className="mt-5 grid grid-cols-3 gap-2"><button onClick={onAdvanced} className="rounded-lg border border-white/[0.06] p-3 text-left hover:border-white/[0.12]"><Plus className="h-4 w-4 text-[#8bd132]" /><strong className="mt-2 block text-[9px] text-white">Editor completo</strong><span className="mt-1 block text-[7px] text-[#687277]">Criar do zero</span></button><button onClick={() => onNavigate('library')} className="rounded-lg border border-white/[0.06] p-3 text-left hover:border-white/[0.12]"><FolderOpen className="h-4 w-4 text-[#8bd132]" /><strong className="mt-2 block text-[9px] text-white">Biblioteca</strong><span className="mt-1 block text-[7px] text-[#687277]">Escolher material</span></button><button onClick={() => onNavigate('ai-chat')} className="rounded-lg border border-white/[0.06] p-3 text-left hover:border-white/[0.12]"><Bot className="h-4 w-4 text-[#8bd132]" /><strong className="mt-2 block text-[9px] text-white">KLIC</strong><span className="mt-1 block text-[7px] text-[#687277]">Iniciar criação</span></button></div>
    <div className="mt-6 space-y-4"><Field label="Título"><input value={form.title} onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))} placeholder="Identificação curta do conteúdo" /></Field><Field label="Texto ou orientação"><textarea rows={4} value={form.copy} onChange={(event) => setForm((current) => ({ ...current, copy: event.target.value }))} placeholder="Legenda, roteiro ou orientação para a equipe" /></Field>
      <div><span className="mb-2 block text-[8px] text-[#8c969b]">Canais</span><div className="grid grid-cols-3 gap-2">{visiblePlatforms.map((platform) => { const connected = connectedPlatforms.includes(platform.id); const selected = form.channels.includes(platform.id); return <button key={platform.id} onClick={() => toggleChannel(platform.id)} className={`rounded-lg border p-2.5 text-left transition ${selected ? 'border-[#8bd132]/30 bg-[#8bd132]/[0.045]' : 'border-white/[0.06] bg-white/[0.012]'}`}><span className="flex items-center justify-between"><strong className="text-[8px] text-[#d2d7d9]">{platform.short}</strong><span className={`h-1.5 w-1.5 rounded-full ${connected ? 'bg-[#8bd132]' : 'bg-[#596267]'}`} /></span><span className="mt-1.5 block truncate text-[7px] text-[#687277]">{platform.label}</span></button>; })}</div>{!connectedPlatforms.length && <button onClick={() => onNavigate('connected-accounts')} className="mt-2 text-[8px] text-amber-300">Nenhuma rede autorizada · abrir Conexões</button>}</div>
      <div className="grid grid-cols-2 gap-3"><Field label="Formato"><select value={form.format} onChange={(event) => setForm((current) => ({ ...current, format: event.target.value as PostFormat }))}>{formats.map((format) => <option key={format.id} value={format.id}>{format.label}</option>)}</select></Field><Field label="Etapa"><select value={form.status} onChange={(event) => setForm((current) => ({ ...current, status: event.target.value as CreationForm['status'] }))}><option value="draft">Rascunho</option><option value="in_production">Em produção</option><option value="scheduled">Agendado</option></select></Field></div>
      <div className="grid grid-cols-2 gap-3"><Field label="Data"><input type="date" value={form.date} onChange={(event) => setForm((current) => ({ ...current, date: event.target.value }))} /></Field><Field label="Horário"><input type="time" value={form.time} onChange={(event) => setForm((current) => ({ ...current, time: event.target.value }))} /></Field></div>
      <div className="grid grid-cols-2 gap-3"><Field label="Responsável"><select value={form.responsibleId} onChange={(event) => setForm((current) => ({ ...current, responsibleId: event.target.value }))}>{users.filter((user) => user.status === 'active').map((user) => <option key={user.id} value={user.id}>{user.name}</option>)}</select></Field><Field label="Campanha"><select value={form.campaignId} onChange={(event) => setForm((current) => ({ ...current, campaignId: event.target.value }))}><option value="">Sem campanha</option>{campaigns.map((campaign) => <option key={campaign.id} value={campaign.id}>{campaign.name}</option>)}</select></Field></div>
      <div><span className="mb-2 block text-[8px] text-[#8c969b]">Materiais da Biblioteca</span>{assets.length ? <div className="max-h-36 space-y-1.5 overflow-y-auto">{assets.slice(0, 10).map((asset) => <button key={asset.id} onClick={() => toggleAsset(asset.id)} className={`flex w-full items-center gap-2 rounded-lg border px-3 py-2 text-left ${form.assetIds.includes(asset.id) ? 'border-[#8bd132]/25 bg-[#8bd132]/[0.035]' : 'border-white/[0.05]'}`}><FolderOpen className="h-3.5 w-3.5 text-[#798388]" /><span className="min-w-0 flex-1 truncate text-[8px] text-[#aeb6ba]">{asset.title}</span>{form.assetIds.includes(asset.id) && <Check className="h-3 w-3 text-[#8bd132]" />}</button>)}</div> : <p className="rounded-lg border border-dashed border-white/[0.06] p-3 text-[8px] text-[#687277]">Nenhum material disponível.</p>}</div>
      {environmentMode === 'company' && requiresWorkspaceApproval && <label className="flex items-center justify-between rounded-lg border border-white/[0.055] p-3"><span><strong className="block text-[9px] font-medium text-[#d1d6d8]">Enviar para aprovação</strong><span className="mt-1 block text-[7px] text-[#687277]">Obrigatório para colaboradores; opcional para o administrador.</span></span><input type="checkbox" checked={form.requiresApproval} onChange={(event) => setForm((current) => ({ ...current, requiresApproval: event.target.checked }))} className="accent-[#8bd132]" /></label>}
    </div>
    <button onClick={onSave} className="mt-6 h-10 w-full rounded-lg bg-[#8bd132] text-[10px] font-semibold text-[#13200d]">Adicionar ao calendário</button>
  </aside></div>;
}

function Field({ label, children }: { label: string; children: React.ReactNode }) { return <label className="block"><span className="mb-1.5 block text-[8px] text-[#8c969b]">{label}</span><span className="contents [&_input]:h-10 [&_input]:w-full [&_input]:rounded-lg [&_input]:border [&_input]:border-white/[0.07] [&_input]:bg-[#0c1113] [&_input]:px-3 [&_input]:text-[9px] [&_input]:text-white [&_input]:outline-none [&_select]:h-10 [&_select]:w-full [&_select]:rounded-lg [&_select]:border [&_select]:border-white/[0.07] [&_select]:bg-[#0c1113] [&_select]:px-3 [&_select]:text-[9px] [&_select]:text-white [&_textarea]:w-full [&_textarea]:rounded-lg [&_textarea]:border [&_textarea]:border-white/[0.07] [&_textarea]:bg-[#0c1113] [&_textarea]:p-3 [&_textarea]:text-[9px] [&_textarea]:leading-relaxed [&_textarea]:text-white [&_textarea]:outline-none">{children}</span></label>; }

function AIPlanningPanel({ objective, setObjective, loading, suggestions, selected, connectedPlatforms, onToggle, onGenerate, onAdd, onClose, onConnect }: { objective: string; setObjective: (value: string) => void; loading: boolean; suggestions: CalendarSuggestion[]; selected: string[]; connectedPlatforms: SocialPlatform[]; onToggle: (id: string) => void; onGenerate: () => void; onAdd: () => void; onClose: () => void; onConnect: () => void }) {
  return <div className="fixed inset-0 z-[100] flex justify-end bg-black/70 backdrop-blur-sm" role="dialog" aria-modal="true" aria-labelledby="ai-plan-title"><button className="absolute inset-0" onClick={onClose} aria-label="Fechar planejamento" /><aside className="relative h-full w-full max-w-[500px] overflow-y-auto border-l border-white/[0.07] bg-[#111719] p-5 sm:p-6"><div className="flex items-start justify-between border-b border-white/[0.06] pb-5"><div><p className="text-[9px] uppercase tracking-[0.18em] text-[#8bd132]">KLIC</p><h2 id="ai-plan-title" className="mt-1.5 text-lg font-semibold text-white">Planejar calendário</h2><p className="mt-1 text-[9px] text-[#727d82]">As sugestões só entram no calendário após sua revisão.</p></div><button onClick={onClose} aria-label="Fechar" className="rounded-lg p-2 text-[#727d82] hover:bg-white/[0.05]"><X className="h-4 w-4" /></button></div>
    <div className="mt-5"><label className="text-[8px] text-[#8c969b]">Objetivo do período</label><textarea rows={4} value={objective} onChange={(event) => setObjective(event.target.value)} placeholder="Ex.: distribuir uma campanha educativa com três publicações por semana..." className="mt-2 w-full rounded-xl border border-white/[0.07] bg-[#0c1113] p-3 text-[9px] leading-relaxed text-white outline-none" />{connectedPlatforms.length ? <p className="mt-2 text-[8px] text-[#687277]">Canais autorizados: {connectedPlatforms.map(formatPlatform).join(', ')}</p> : <button onClick={onConnect} className="mt-2 text-[8px] text-amber-300">Conecte uma rede social para planejar a distribuição.</button>}<button disabled={loading || !connectedPlatforms.length} onClick={onGenerate} className="mt-4 inline-flex h-9 w-full items-center justify-center gap-2 rounded-lg border border-white/[0.08] text-[9px] font-medium text-white disabled:opacity-40">{loading ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4 text-[#8bd132]" />}{loading ? 'Analisando o calendário...' : 'Gerar sugestões'}</button></div>
    {suggestions.length > 0 && <div className="mt-6 space-y-2"><h3 className="text-[9px] font-semibold uppercase tracking-[0.15em] text-[#aeb6ba]">Revisar sugestões</h3>{suggestions.map((suggestion) => { const checked = selected.includes(suggestion.id); return <button key={suggestion.id} onClick={() => onToggle(suggestion.id)} className={`w-full rounded-xl border p-3 text-left ${checked ? 'border-[#8bd132]/25 bg-[#8bd132]/[0.035]' : 'border-white/[0.06]'}`}><div className="flex items-start gap-3"><span className={`mt-0.5 grid h-4 w-4 shrink-0 place-items-center rounded border ${checked ? 'border-[#8bd132] bg-[#8bd132] text-[#13200d]' : 'border-white/15'}`}>{checked && <Check className="h-3 w-3" />}</span><span className="min-w-0 flex-1"><strong className="block text-[9px] text-white">{suggestion.title}</strong><span className="mt-1 block text-[8px] text-[#778186]">{formatPlatform(suggestion.platform)} · {formatName(suggestion.format)} · {new Date(suggestion.suggestedAt).toLocaleString('pt-BR', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })}</span><span className="mt-2 block text-[8px] leading-relaxed text-[#697378]">{suggestion.rationale}</span></span></div></button>; })}<button onClick={onAdd} className="mt-4 h-10 w-full rounded-lg bg-[#8bd132] text-[10px] font-semibold text-[#13200d]">Adicionar selecionados como rascunho</button></div>}
  </aside></div>;
}

function DetailPanel({ post, approval, campaignName, assetNames, canApprove, onApprove, onRequestChanges, onClose, onFixConnection }: { post: Post; approval?: ReturnType<typeof useGovernance>['approvals'][number]; campaignName?: string; assetNames: string[]; canApprove: boolean; onApprove: () => void; onRequestChanges: () => void; onClose: () => void; onFixConnection: () => void }) {
  const history = [...(approval?.history || []).map((entry) => ({ id: entry.id, detail: entry.detail, actorName: entry.actorName, createdAt: entry.createdAt })), ...(post.history || [])].sort((a, b) => b.createdAt.localeCompare(a.createdAt));
  const channels = post.channels?.length ? post.channels : [post.platform];
  return <div className="fixed inset-0 z-[100] flex justify-end bg-black/70 backdrop-blur-sm" role="dialog" aria-modal="true" aria-labelledby="content-detail-title"><button className="absolute inset-0" onClick={onClose} aria-label="Fechar conteúdo" /><aside className="relative h-full w-full max-w-[500px] overflow-y-auto border-l border-white/[0.07] bg-[#111719] p-5 sm:p-6"><div className="flex items-start justify-between border-b border-white/[0.06] pb-5"><div className="min-w-0"><span className={`inline-flex rounded-full px-2 py-1 text-[8px] ${statusStyle[post.status]}`}>{postStatusLabel[post.status]}</span><h2 id="content-detail-title" className="mt-3 text-lg font-semibold leading-snug text-white">{post.title}</h2></div><button onClick={onClose} aria-label="Fechar" className="rounded-lg p-2 text-[#727d82] hover:bg-white/[0.05]"><X className="h-4 w-4" /></button></div>
    <div className="mt-5 grid grid-cols-2 gap-2"><Meta label="Publicação" value={post.scheduledAt ? new Date(post.scheduledAt).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' }) : 'Sem data'} /><Meta label="Formato" value={formatName(post.format)} /><Meta label="Responsável" value={post.responsibleName || post.author} /><Meta label="Campanha" value={campaignName || 'Sem campanha'} /></div>
    <section className="mt-6"><h3 className="text-[8px] uppercase tracking-[0.15em] text-[#747f84]">Canais</h3><div className="mt-2 flex flex-wrap gap-1.5">{channels.map((platform) => <span key={platform} className="rounded-full border border-white/[0.06] px-2.5 py-1 text-[8px] text-[#aeb6ba]">{formatPlatform(platform)}</span>)}</div></section>
    {post.copy && <section className="mt-6"><h3 className="text-[8px] uppercase tracking-[0.15em] text-[#747f84]">Conteúdo</h3><p className="mt-2 whitespace-pre-wrap rounded-xl border border-white/[0.05] bg-black/15 p-4 text-[9px] leading-relaxed text-[#aeb6ba]">{post.copy}</p></section>}
    {assetNames.length > 0 && <section className="mt-6"><h3 className="text-[8px] uppercase tracking-[0.15em] text-[#747f84]">Materiais vinculados</h3><div className="mt-2 space-y-1.5">{assetNames.map((name) => <div key={name} className="flex items-center gap-2 rounded-lg border border-white/[0.05] px-3 py-2 text-[8px] text-[#9ca5aa]"><FolderOpen className="h-3.5 w-3.5" />{name}</div>)}</div></section>}
    {post.publicationError && <div className="mt-5 rounded-xl border border-red-400/15 bg-red-400/[0.04] p-3 text-[8px] leading-relaxed text-red-200"><strong className="block text-[9px]">Falha na publicação</strong><span className="mt-1 block">{post.publicationError}</span><button onClick={onFixConnection} className="mt-2 text-red-100 underline underline-offset-2">Corrigir conexão</button></div>}
    {canApprove && <div className="mt-6 grid grid-cols-2 gap-2"><button onClick={onRequestChanges} className="h-9 rounded-lg border border-white/[0.07] text-[9px] text-[#aeb6ba]">Solicitar alterações</button><button onClick={onApprove} className="h-9 rounded-lg bg-[#8bd132] text-[9px] font-semibold text-[#13200d]">Aprovar conteúdo</button></div>}
    <section className="mt-7 border-t border-white/[0.06] pt-5"><div className="flex items-center gap-2"><History className="h-4 w-4 text-[#8bd132]" /><h3 className="text-[9px] font-semibold uppercase tracking-[0.15em] text-[#aeb6ba]">Histórico</h3></div>{history.length ? <div className="mt-4 space-y-3">{history.slice(0, 10).map((entry) => <div key={entry.id} className="relative border-l border-white/[0.08] pl-3"><span className="absolute -left-[3px] top-1 h-1.5 w-1.5 rounded-full bg-[#7a858a]" /><p className="text-[8px] text-[#b0b7ba]">{entry.detail}</p><span className="mt-1 block text-[7px] text-[#626c71]">{entry.actorName} · {new Date(entry.createdAt).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })}</span></div>)}</div> : <p className="mt-3 text-[8px] text-[#626c71]">Nenhuma alteração registrada.</p>}</section>
  </aside></div>;
}

function Meta({ label, value }: { label: string; value: string }) { return <div className="rounded-lg border border-white/[0.05] bg-white/[0.012] p-3"><span className="text-[7px] text-[#667176]">{label}</span><strong className="mt-1 block truncate text-[8px] font-medium text-[#c3c9cc]">{value}</strong></div>; }
