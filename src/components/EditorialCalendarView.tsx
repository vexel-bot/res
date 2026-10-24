import React from 'react';
import {
  AlertCircle,
  CalendarDays,
  CalendarRange,
  Check,
  ChevronLeft,
  ChevronRight,
  Clock3,
  Filter,
  FolderOpen,
  History,
  LayoutList,
  Plus,
  X,
} from 'lucide-react';
import { useGovernance } from '../context/GovernanceContext';
import { ClickoSelectMenu } from './ClickoSelectMenu';
import { hasPermission } from '../security/accessControl';
import { useOperations } from '../context/OperationsContext';
import type { ApprovalStage, NavigationTab, Post, PostFormat, PostStatus, SocialPlatform } from '../types';
import { postStatusLabel } from '../utils/localization';
import { calendarIncludesDate, calendarPeriodBounds, calendarPeriodDates, calendarSchedule, navigateCalendarDate, type CalendarCustomRange } from '../utils/calendarDates';
import { ClickoLoader } from './ClickoLoader';
import { createRequestGuard } from '../utils/requestGuard';
import { calendarPublishRequest } from '../operations/publicationRequest';
import { PublishedHistory, type ConfirmedPublication } from './PublishedHistory';
import { KlicSymbol } from './KlicSymbol';
import { klicPageScope, useKlicPageDetails, type KlicPageDetails } from '../klic/pageContext';
import './EditorialCalendarView.css';

interface EditorialCalendarViewProps {
  posts: Post[];
  onSelectPost?: (post: Post) => void;
  onNewPost: () => void;
  onNavigate?: (tab: NavigationTab) => void;
}

type PeriodMode = 'day' | 'month' | 'week' | 'custom';
type DisplayMode = 'calendar' | 'list';
type CalendarArea = 'schedule' | 'published';
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
  draft: 'bg-white/[0.06] text-[rgba(255,255,255,0.72)]', in_production: 'bg-[#FF7F50]/[0.08] text-[#FF7F50]',
  in_review: 'bg-[#FF7F50]/[0.08] text-[#FF7F50]', pending_approval: 'bg-[#F28500]/[0.08] text-[#F28500]',
  approved: 'bg-[#FF7F50]/[0.08] text-[#FF7F50]', changes_requested: 'bg-[#F28500]/[0.08] text-[#F28500]',
  rejected: 'bg-[#FF7F50]/[0.08] text-[#FF7F50]', scheduled: 'bg-[#FF7F50]/[0.08] text-[#FF7F50]', processing: 'bg-[#F28500]/[0.08] text-[#F28500]',
  published: 'bg-[#FF7F50]/[0.08] text-[#FF7F50]', error: 'bg-[#FF7F50]/[0.08] text-[#FF7F50]', cancelled: 'bg-white/[0.06] text-[rgba(255,255,255,0.72)]',
};

const statusDot: Record<PostStatus, string> = {
  draft: 'bg-[#808080]', in_production: 'bg-[#FF7F50]', in_review: 'bg-[#FF7F50]', pending_approval: 'bg-[#F28500]',
  approved: 'bg-[#FF7F50]', changes_requested: 'bg-[#F28500]', rejected: 'bg-[#FF7F50]', scheduled: 'bg-[#FF7F50]', processing: 'bg-[#F28500]',
  published: 'bg-[#FF7F50]', error: 'bg-[#FF7F50]', cancelled: 'bg-[#808080]',
};

const pad = (value: number) => String(value).padStart(2, '0');
const dateKey = (date: Date) => `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
const compactPeriodDate = (date: Date, includeYear = false) => date.toLocaleDateString('pt-BR', { day: '2-digit', month: 'short', ...(includeYear ? { year: 'numeric' } : {}) }).replaceAll(' de ', ' ').replaceAll('.', '');
const formatPlatform = (platform: SocialPlatform) => visiblePlatforms.find((item) => item.id === platform)?.label || platform;
const formatName = (format: PostFormat) => formats.find((item) => item.id === format)?.label || format;
const scheduledTime = (post: Post) => post.scheduledAt ? new Date(post.scheduledAt).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }) : 'Sem horário';

const approvalStatus = (stage?: ApprovalStage): PostStatus | undefined => {
  if (!stage) return undefined;
  return ({ draft: 'draft', in_review: 'in_review', pending_approval: 'pending_approval', approved: 'approved', changes_requested: 'changes_requested', rejected: 'rejected', published: 'published' } as const)[stage];
};

export const EditorialCalendarView: React.FC<EditorialCalendarViewProps> = ({ posts, onSelectPost, onNewPost, onNavigate }) => {
  const {
    activeWorkspace, activeCampaign, activeClient, contextSnapshot, campaigns, clients, connectedAccounts, assets,
    addPosts, updatePosts, createRepurposeHandoff,
  } = useOperations();
  const { currentUser, users, approvals, workspace, environmentMode, createApproval, approvalAction } = useGovernance();
  const canApprove = hasPermission(currentUser, 'content.approve');
  const canPublish = hasPermission(currentUser, 'content.publish');
  const canReadConnections = hasPermission(currentUser, 'connections.read');
  const [periodMode, setPeriodMode] = React.useState<PeriodMode>('month');
  const [displayMode, setDisplayMode] = React.useState<DisplayMode>('calendar');
  const [calendarArea, setCalendarArea] = React.useState<CalendarArea>('schedule');
  const [publishedContext, setPublishedContext] = React.useState<KlicPageDetails>({ view: 'Publicados' });
  const [publicationJobs, setPublicationJobs] = React.useState<ConfirmedPublication[]>([]);
  const [publicationHistoryLoading, setPublicationHistoryLoading] = React.useState(false);
  const [publicationHistoryError, setPublicationHistoryError] = React.useState(false);
  const [currentDate, setCurrentDate] = React.useState(() => new Date());
  const [customRange, setCustomRange] = React.useState<CalendarCustomRange>(() => {
    const start = new Date(); const end = new Date(); end.setDate(end.getDate() + 6);
    return { start: dateKey(start), end: dateKey(end) };
  });
  const [customRangeDraft, setCustomRangeDraft] = React.useState<CalendarCustomRange>(() => {
    const start = new Date(); const end = new Date(); end.setDate(end.getDate() + 6);
    return { start: dateKey(start), end: dateKey(end) };
  });
  const [showCustomRange, setShowCustomRange] = React.useState(false);
  const [showFilters, setShowFilters] = React.useState(false);
  const [filterPlatform, setFilterPlatform] = React.useState('all');
  const [filterStatus, setFilterStatus] = React.useState('all');
  const [filterFormat, setFilterFormat] = React.useState('all');
  const [filterResponsible, setFilterResponsible] = React.useState('all');
  const [filterCampaign, setFilterCampaign] = React.useState('all');
  const [selectedPostId, setSelectedPostId] = React.useState<string>();
  const [draggedPostId, setDraggedPostId] = React.useState<string>();
  const [notice, setNotice] = React.useState<{ tone: 'success' | 'error'; text: string }>();
  const [schedulingId, setSchedulingId] = React.useState<string>();
  const [createOpen, setCreateOpen] = React.useState(false);
  const [aiOpen, setAiOpen] = React.useState(false);
  const [aiObjective, setAiObjective] = React.useState('');
  const [aiLoading, setAiLoading] = React.useState(false);
  const [aiSuggestions, setAiSuggestions] = React.useState<CalendarSuggestion[]>([]);
  const [selectedSuggestions, setSelectedSuggestions] = React.useState<string[]>([]);
  const calendarScope = React.useRef(activeWorkspace.id);
  calendarScope.current = activeWorkspace.id;
  const saving = React.useRef(false);
  const moving = React.useRef(false);
  const moveGuard = React.useRef(createRequestGuard());
  React.useEffect(() => {
    calendarScope.current = activeWorkspace.id;
    saving.current = false;
    moving.current = false;
    moveGuard.current.invalidate();
    setCreateOpen(false); setAiOpen(false); setAiLoading(false); setAiSuggestions([]); setSelectedSuggestions([]);
    setSelectedPostId(undefined); setDraggedPostId(undefined); setNotice(undefined);
    setFilterPlatform('all'); setFilterStatus('all'); setFilterFormat('all'); setFilterResponsible('all'); setFilterCampaign('all');
    setPublicationJobs([]); setPublicationHistoryError(false); setPublicationHistoryLoading(canReadConnections);
    return () => { calendarScope.current = ''; moveGuard.current.invalidate(); };
  }, [activeWorkspace.id, canReadConnections]);
  const [form, setForm] = React.useState({
    title: '', copy: '', date: dateKey(new Date()), time: '09:00', channels: [] as SocialPlatform[], format: 'post' as PostFormat,
    status: 'draft' as Extract<PostStatus, 'draft' | 'in_production' | 'scheduled'>, responsibleId: currentUser?.id || '', campaignId: activeCampaign?.id || '',
    assetIds: [] as string[], accountIds: [] as string[], clientId: activeClient?.id || '', requiresApproval: false, tiktokConsent: false,
  });

  const authorizedAccounts = React.useMemo(() => connectedAccounts.filter((account) => account.connected && ['connected', 'synced'].includes(account.connectionStatus || '')
    && (environmentMode !== 'company' || !form.clientId || account.clientId === form.clientId)), [connectedAccounts, environmentMode, form.clientId]);

  const schedulePost = async (post: Post) => {
    if (post.socialAccountIds?.length !== 1) throw new Error('Selecione exatamente uma conta para este agendamento.');
    const account = connectedAccounts.find(item => item.id === post.socialAccountIds![0] && item.connected && item.capabilities?.canSchedule);
    if (!account) throw new Error('A conta escolhida não está apta a agendar. Revise a conexão.');
    if (environmentMode === 'company' && post.clientId && account.clientId !== post.clientId) throw new Error('Esta conta pertence a outro cliente.');
    const request = calendarPublishRequest(post, account, assets);
    const response = await fetch('/api/integrations/publications/schedule', {
      method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json', 'x-workspace-id': activeWorkspace.id },
      body: JSON.stringify({ contentId: post.id, title: post.title, connectionId: account.id, clientId: environmentMode === 'company' ? post.clientId || null : null,
        scheduledAt: post.scheduledAt, request }),
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok || !result.publication?.id) throw new Error(result.error || 'Não foi possível confirmar o agendamento.');
    return result.publication as { id: string; status: string };
  };

  React.useEffect(() => {
    if (!canReadConnections) return;
    const workspaceId = activeWorkspace.id;
    let active = true;
    const reconcile = async () => {
      let response: Response;
      try {
        response = await fetch('/api/integrations/publications/scheduled', { credentials: 'same-origin', headers: { 'x-workspace-id': workspaceId } });
      } catch {
        if (active && calendarScope.current === workspaceId) { setPublicationHistoryError(true); setPublicationHistoryLoading(false); }
        return;
      }
      if (!active || calendarScope.current !== workspaceId) return;
      if (!response.ok) { setPublicationHistoryError(true); setPublicationHistoryLoading(false); return; }
      const body = await response.json().catch(() => ({})) as { publications?: Array<{
        id: string; ownerId: string; contentId: string; connectionId: string; clientId?: string; provider?: SocialPlatform; title?: string;
        status: string; scheduledAt: string; createdAt: string; updatedAt: string; request: { kind: string; text?: string; mediaUrls?: string[] };
        providerPostId?: string; errorCode?: string; permalink?: string;
      }> };
      if (!active || calendarScope.current !== workspaceId) return;
      setPublicationJobs((body.publications || []) as ConfirmedPublication[]);
      setPublicationHistoryError(false); setPublicationHistoryLoading(false);
      const jobs = new Map((body.publications || []).map(item => [item.contentId, item]));
      if (!jobs.size) return;
      updatePosts(current => {
        let changed = false;
        const reconciled = current.map(post => {
        if (post.workspaceId !== workspaceId) return post;
        const job = jobs.get(post.id);
        if (!job) return post;
        if (job.status === 'cancelled') {
          if (!post.scheduledPublicationId && !['scheduled', 'processing'].includes(post.status)) return post;
          changed = true;
          return { ...post, status: 'draft' as const, scheduledAt: undefined, scheduledPublicationId: undefined, publicationError: undefined };
        }
        const status: PostStatus = job.status === 'published' ? 'published' : job.status === 'processing' || job.status === 'publishing' ? 'processing'
          : job.status === 'failed' || job.status === 'indeterminate' ? 'error' : job.status === 'cancelled' ? 'cancelled' : 'scheduled';
        const publicationError = ['failed', 'indeterminate'].includes(job.status) ? `Publicação não confirmada (${job.errorCode || job.status}).` : undefined;
        const scheduledPublicationId = job.status === 'cancelled' ? undefined : job.id;
        if (post.status === status && post.scheduledAt === job.scheduledAt && post.scheduledPublicationId === scheduledPublicationId && post.externalPostId === job.providerPostId && post.publicationError === publicationError) return post;
        changed = true;
        return { ...post, status, scheduledAt: job.scheduledAt, scheduledPublicationId, externalPostId: job.providerPostId, publicationError };
        });
        const known = new Set(reconciled.filter(post => post.workspaceId === workspaceId).map(post => post.id));
        for (const job of jobs.values()) {
          if (job.status === 'cancelled') continue;
          if (known.has(job.contentId)) continue;
          const platform = job.provider || connectedAccounts.find(account => account.id === job.connectionId)?.platform;
          if (!platform || !visiblePlatforms.some(item => item.id === platform)) continue;
          changed = true;
          const format: PostFormat = job.request.kind === 'carousel' ? 'carousel' : job.request.kind === 'story' ? 'story'
            : job.request.kind === 'video' || job.request.kind === 'short_video' ? 'reels' : job.request.kind === 'document' ? 'linkedin-article' : 'post';
          const status: PostStatus = job.status === 'published' ? 'published' : ['publishing', 'processing'].includes(job.status) ? 'processing'
            : ['failed', 'indeterminate'].includes(job.status) ? 'error' : job.status === 'cancelled' ? 'cancelled' : 'scheduled';
          reconciled.push({ id: job.contentId, workspaceId, title: job.title || job.request.text?.slice(0, 80) || 'Conteúdo agendado',
            platform, channels: [platform], format, copy: job.request.text || '', hashtags: [], scheduledAt: job.scheduledAt,
            status, author: 'Clicko', createdAt: job.createdAt, clientId: job.clientId, socialAccountIds: [job.connectionId],
            scheduledPublicationId: job.status === 'cancelled' ? undefined : job.id, externalPostId: job.providerPostId,
            publicationError: ['failed', 'indeterminate'].includes(job.status) ? `Publicação não confirmada (${job.errorCode || job.status}).` : undefined });
        }
        return changed ? reconciled : current;
      });
    };
    void reconcile().catch(() => undefined);
    const timer = window.setInterval(() => { if (document.visibilityState === 'visible') void reconcile().catch(() => undefined); }, 15_000);
    return () => { active = false; window.clearInterval(timer); };
  }, [activeWorkspace.id, connectedAccounts, canReadConnections, updatePosts]);
  const connectedPlatforms = React.useMemo(() => [...new Set(authorizedAccounts.map((account) => account.platform))], [authorizedAccounts]);
  const approvalByContent = React.useMemo(() => new Map(approvals.map((item) => [item.contentId, item])), [approvals]);
  const normalizedPosts = React.useMemo(() => posts.filter(post => post.workspaceId === activeWorkspace.id).map((post) => {
    const approval = approvalByContent.get(post.id);
    return approval ? { ...post, status: approval.stage === 'approved' && ['scheduled', 'processing', 'published', 'error', 'cancelled'].includes(post.status)
      ? post.status : approvalStatus(approval.stage) || post.status, scheduledAt: approval.scheduledAt || post.scheduledAt } : post;
  }), [approvalByContent, posts, activeWorkspace.id]);
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

  const periodPosts = React.useMemo(() => filteredPosts.filter(post => calendarIncludesDate(post.scheduledAt, currentDate, periodMode, customRange)), [filteredPosts, currentDate, customRange, periodMode]);
  // Undated drafts remain accessible in the list, where they already say “Sem data”.
  const listPosts = React.useMemo(() => [...periodPosts, ...filteredPosts.filter(post => !post.scheduledAt)], [periodPosts, filteredPosts]);

  const calendarDates = React.useMemo(() => calendarPeriodDates(currentDate, periodMode, customRange), [currentDate, customRange, periodMode]);

  const postsByDay = React.useMemo(() => {
    const grouped = new Map<string, Post[]>();
    filteredPosts.forEach((post) => {
      if (!post.scheduledAt) return;
      const key = dateKey(new Date(post.scheduledAt));
      grouped.set(key, [...(grouped.get(key) || []), post].sort((a, b) => String(a.scheduledAt).localeCompare(String(b.scheduledAt))));
    });
    return grouped;
  }, [filteredPosts]);

  const futurePosts = React.useMemo(() => filteredPosts.filter((post) => post.scheduledAt && new Date(post.scheduledAt).getTime() >= Date.now() && !['processing', 'published', 'rejected', 'cancelled'].includes(post.status)).sort((a, b) => String(a.scheduledAt).localeCompare(String(b.scheduledAt))).slice(0, 4), [filteredPosts]);

  const planningSignals = React.useMemo(() => {
    const viewKeys = calendarDates.filter((date) => periodMode !== 'month' || date.getMonth() === currentDate.getMonth()).map(dateKey);
    const empty = viewKeys.filter((key) => !(postsByDay.get(key)?.length)).length;
    const overloaded = viewKeys.filter((key) => (postsByDay.get(key)?.length || 0) >= 3).length;
    const counts = new Map<SocialPlatform, number>();
    periodPosts.forEach((post) => (post.channels?.length ? post.channels : [post.platform]).forEach((platform) => counts.set(platform, (counts.get(platform) || 0) + 1)));
    const total = [...counts.values()].reduce((sum, value) => sum + value, 0);
    const dominant = [...counts.entries()].sort((a, b) => b[1] - a[1])[0];
    const bestTime = authorizedAccounts.find((account) => account.bestTime && account.bestTime !== 'Sem dados');
    return [
      { label: 'Espaços disponíveis', value: `${empty} dias livres`, tone: empty > 4 ? 'positive' : 'neutral' },
      { label: 'Dias concentrados', value: overloaded ? `${overloaded} com 3+ conteúdos` : 'Cadência equilibrada', tone: overloaded ? 'warning' : 'positive' },
      { label: 'Distribuição por canal', value: dominant && total && dominant[1] / total > 0.6 ? `${formatPlatform(dominant[0])} concentra ${Math.round(dominant[1] / total * 100)}%` : 'Sem concentração excessiva', tone: dominant && total && dominant[1] / total > 0.6 ? 'warning' : 'positive' },
      ...(bestTime ? [{ label: 'Dado conectado', value: `${formatPlatform(bestTime.platform)} recomenda ${bestTime.bestTime}`, tone: 'positive' }] : []),
    ];
  }, [authorizedAccounts, calendarDates, currentDate, periodMode, periodPosts, postsByDay]);

  const openCreate = (date = new Date()) => {
    const available = connectedAccounts.filter(account => account.connected && ['connected', 'synced'].includes(account.connectionStatus || '')
      && (environmentMode !== 'company' || !activeClient?.id || account.clientId === activeClient.id));
    const firstConnected = available[0]?.platform;
    setForm({ title: '', copy: '', date: dateKey(date), time: '09:00', channels: firstConnected ? [firstConnected] : [], format: 'post', status: 'draft', responsibleId: currentUser?.id || '', campaignId: activeCampaign?.id || '', assetIds: [], accountIds: available.filter(account => account.platform === firstConnected).slice(0, 1).map(account => account.id), clientId: activeClient?.id || '', requiresApproval: false, tiktokConsent: false });
    setCreateOpen(true);
    setNotice(undefined);
  };

  const toggleChannel = (platform: SocialPlatform) => setForm(current => {
    const selected = current.channels.includes(platform);
    return { ...current, channels: selected ? current.channels.filter(item => item !== platform) : [...current.channels, platform],
      accountIds: selected ? current.accountIds.filter(id => authorizedAccounts.find(account => account.id === id)?.platform !== platform)
        : [...current.accountIds, ...authorizedAccounts.filter(account => account.platform === platform).slice(0, 1).map(account => account.id)] };
  });
  const toggleAsset = (id: string) => setForm((current) => ({ ...current, assetIds: current.assetIds.includes(id) ? current.assetIds.filter((item) => item !== id) : [...current.assetIds, id] }));

  const hasPublishingPermission = (platform: SocialPlatform) => authorizedAccounts.some(account => account.platform === platform && form.accountIds.includes(account.id)
    && account.capabilities?.canSchedule);

  const saveContent = async () => {
    if (saving.current) return;
    if (!form.title.trim()) return setNotice({ tone: 'error', text: 'Informe um título para o conteúdo.' });
    if (!form.channels.length) return setNotice({ tone: 'error', text: 'Selecione ao menos uma rede social para o planejamento.' });
    if (form.channels.some(platform => !form.accountIds.some(id => authorizedAccounts.some(account => account.id === id && account.platform === platform))))
      return setNotice({ tone: 'error', text: 'Selecione uma conta conectada e vinculada ao cliente para cada rede escolhida.' });
    if (form.status === 'scheduled') {
      if (form.accountIds.length !== 1) return setNotice({ tone: 'error', text: 'O agendamento automático exige uma conta por conteúdo. Crie uma publicação para cada conta.' });
      const unavailable = form.channels.filter((platform) => !hasPublishingPermission(platform));
      if (unavailable.length) return setNotice({ tone: 'error', text: `Para agendar, autorize publicação em ${unavailable.map(formatPlatform).join(', ')} na área Conexões.` });
    }
    const scheduledAt = calendarSchedule(form.date, form.time);
    if (!scheduledAt) return setNotice({ tone: 'error', text: 'Informe uma data e horário válidos.' });
    if (form.status === 'scheduled' && Date.parse(scheduledAt) <= Date.now()) return setNotice({ tone: 'error', text: 'Escolha uma data futura para agendar.' });
    const responsible = users.find((user) => user.id === form.responsibleId) || currentUser;
    const needsApproval = environmentMode === 'company' && ((Boolean(workspace?.settings.requireApproval) && (!canApprove || form.requiresApproval)) || (form.status === 'scheduled' && !canPublish));
    const postId = `post-${Date.now()}`;
    const createdAt = new Date().toISOString();
    const post: Post = {
      id: postId, workspaceId: activeWorkspace.id, title: form.title.trim(), copy: form.copy.trim(), hashtags: [],
      platform: form.channels[0], channels: form.channels, format: form.format, scheduledAt,
      status: needsApproval ? 'pending_approval' : form.status, author: currentUser?.name || 'Usuário', createdAt,
      responsibleId: responsible?.id, responsibleName: responsible?.name, campaignId: form.campaignId || undefined,
      strategyId: form.campaignId || undefined, assetIds: form.assetIds, socialAccountIds: form.accountIds,
      clientId: form.clientId || undefined, tiktokConsentConfirmed: form.tiktokConsent, origin: 'manual', contextRevision: contextSnapshot.revision,
      history: [{ id: `post-history-${Date.now()}`, action: 'created', detail: needsApproval ? 'Conteúdo criado e enviado para aprovação' : 'Conteúdo criado pelo Calendário', actorName: currentUser?.name || 'Usuário', createdAt }],
    };
    saving.current = true;
    try {
    const validated = await fetch('/api/integrations/connections/validate', {
      method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json', 'x-workspace-id': activeWorkspace.id },
      body: JSON.stringify({ connectionIds: form.accountIds, clientId: environmentMode === 'company' ? form.clientId || null : null, requireScheduling: form.status === 'scheduled' }),
    });
    if (!validated.ok) {
      const result = await validated.json().catch(() => ({}));
      if (calendarScope.current === activeWorkspace.id) setNotice({ tone: 'error', text: result.error || 'Não foi possível validar as contas escolhidas.' });
      return;
    }
    if (calendarScope.current !== activeWorkspace.id) return;
    if (form.status === 'scheduled' && !needsApproval) {
      const publication = await schedulePost(post);
      if (calendarScope.current !== activeWorkspace.id) return;
      post.scheduledPublicationId = publication.id;
    }
    addPosts([post]);
    if (needsApproval) {
      const approval = await createApproval({ contentId: post.id, title: post.title, copy: post.copy, platform: post.platform, format: post.format, scheduledAt: post.scheduledAt, campaignId: post.campaignId, strategyId: post.strategyId });
      if (calendarScope.current !== activeWorkspace.id) return;
      if (!approval) {
        updatePosts((current) => current.map((item) => item.id === post.id ? { ...item, status: 'draft' } : item));
        setCreateOpen(false);
        setNotice({ tone: 'error', text: 'Não foi possível enviar para aprovação. O conteúdo foi preservado como rascunho no calendário.' });
        return;
      }
    }
    setCreateOpen(false);
    setNotice({ tone: 'success', text: needsApproval ? 'Conteúdo adicionado e enviado para aprovação.' : 'Conteúdo adicionado ao calendário.' });
    } catch (error) {
      if (calendarScope.current === activeWorkspace.id) setNotice({ tone: 'error', text: error instanceof Error ? error.message : 'Não foi possível validar as contas escolhidas.' });
    } finally { if (calendarScope.current === activeWorkspace.id) saving.current = false; }
  };

  const movePost = async (postId: string, date: Date) => {
    if (moving.current) return;
    setDraggedPostId(undefined);
    const target = normalizedPosts.find(post => post.id === postId);
    if (!target || ['processing', 'published', 'cancelled'].includes(target.status)) return setNotice({ tone: 'error', text: 'Este conteúdo não pode ser reagendado.' });
    if (target.scheduledPublicationId) return setNotice({ tone: 'error', text: 'Cancele o agendamento confirmado antes de alterar a data.' });
    const approval = approvalByContent.get(postId);
    if (!canApprove && (approval || ['pending_approval', 'in_review', 'changes_requested', 'approved', 'rejected'].includes(target.status))) {
      return setNotice({ tone: 'error', text: 'Solicite ao administrador a alteração de data deste conteúdo em aprovação.' });
    }
    const previous = target.scheduledAt ? new Date(target.scheduledAt) : new Date();
    const scheduledAt = calendarSchedule(dateKey(date), `${pad(previous.getHours())}:${pad(previous.getMinutes())}`);
    if (!scheduledAt || ((approval || target.status === 'scheduled') && Date.parse(scheduledAt) <= Date.now())) {
      return setNotice({ tone: 'error', text: 'Escolha uma data e horário futuros válidos para reagendar.' });
    }
    const isCurrent = moveGuard.current.begin(activeWorkspace.id, () => calendarScope.current);
    moving.current = true;
    try {
    if (approval) {
      const result = await approvalAction(approval.id, 'reschedule', undefined, scheduledAt);
      if (!isCurrent()) return;
      if (!result) return setNotice({ tone: 'error', text: 'Não foi possível reagendar. A data anterior foi mantida.' });
    }
    if (!isCurrent()) return;
    updatePosts((current) => current.map((post) => {
      if (post.id !== postId || post.workspaceId !== activeWorkspace.id || post.status === 'published') return post;
      return { ...post, scheduledAt, history: [{ id: `post-history-${Date.now()}`, action: 'rescheduled', detail: `Reagendado para ${date.toLocaleDateString('pt-BR')}`, actorName: currentUser?.name || 'Usuário', createdAt: new Date().toISOString() }, ...(post.history || [])] };
    }));
    setNotice({ tone: 'success', text: `Conteúdo reagendado para ${date.toLocaleDateString('pt-BR')}.` });
    } finally { if (isCurrent()) moving.current = false; }
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

  const handleScheduleApproved = async () => {
    if (!selectedPost || !canPublish || schedulingId) return;
    const workspaceId = activeWorkspace.id;
    setSchedulingId(selectedPost.id);
    try {
      const publication = await schedulePost(selectedPost);
      if (calendarScope.current !== workspaceId) return;
      updatePosts(current => current.map(post => post.id === selectedPost.id && post.workspaceId === workspaceId
        ? { ...post, status: 'scheduled', scheduledPublicationId: publication.id, publicationError: undefined } : post));
      setNotice({ tone: 'success', text: 'Publicação automática confirmada para a data escolhida.' });
    } catch (error) {
      if (calendarScope.current === workspaceId) setNotice({ tone: 'error', text: error instanceof Error ? error.message : 'Não foi possível confirmar o agendamento.' });
    } finally { if (calendarScope.current === workspaceId) setSchedulingId(undefined); }
  };

  const handleCancelSchedule = async () => {
    if (!selectedPost?.scheduledPublicationId || !canPublish || schedulingId) return;
    const postId = selectedPost.id;
    const workspaceId = activeWorkspace.id;
    setSchedulingId(postId);
    try {
      const response = await fetch(`/api/integrations/publications/scheduled/${encodeURIComponent(selectedPost.scheduledPublicationId)}`, {
        method: 'DELETE', credentials: 'same-origin', headers: { 'x-workspace-id': workspaceId },
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(result.error || 'Não foi possível cancelar. A publicação pode já estar em andamento.');
      if (calendarScope.current !== workspaceId) return;
      updatePosts(current => current.map(post => post.id === postId && post.workspaceId === workspaceId
        ? { ...post, status: 'draft', scheduledAt: undefined, scheduledPublicationId: undefined, publicationError: undefined } : post));
      setNotice({ tone: 'success', text: 'Publicação automática cancelada. O conteúdo permanece como rascunho.' });
    } catch (error) {
      if (calendarScope.current === workspaceId) setNotice({ tone: 'error', text: error instanceof Error ? error.message : 'Não foi possível cancelar o agendamento.' });
    } finally { if (calendarScope.current === workspaceId) setSchedulingId(undefined); }
  };

  const handleRescheduleSelected = async (date: string, time: string) => {
    if (!selectedPost || schedulingId || selectedPost.status === 'published' || selectedPost.status === 'processing') return;
    const scheduledAt = calendarSchedule(date, time);
    if (!scheduledAt || Date.parse(scheduledAt) <= Date.now()) return setNotice({ tone: 'error', text: 'Escolha uma data e um horário futuros válidos.' });
    const postId = selectedPost.id;
    const workspaceId = activeWorkspace.id;
    setSchedulingId(postId);
    try {
      if (selectedPost.scheduledPublicationId) {
        if (!canPublish) throw new Error('Seu perfil não pode alterar este agendamento.');
        const response = await fetch(`/api/integrations/publications/scheduled/${encodeURIComponent(selectedPost.scheduledPublicationId)}`, {
          method: 'PATCH', credentials: 'same-origin', headers: { 'Content-Type': 'application/json', 'x-workspace-id': workspaceId },
          body: JSON.stringify({ scheduledAt }),
        });
        const body = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(body.error || 'Não foi possível alterar o agendamento.');
        if (calendarScope.current !== workspaceId) return;
        setPublicationJobs(current => current.map(job => job.id === selectedPost.scheduledPublicationId ? { ...job, scheduledAt, updatedAt: body.publication?.updatedAt || job.updatedAt } : job));
      } else if (selectedApproval) {
        if (!canApprove) throw new Error('Solicite ao administrador a alteração da data.');
        const changed = await approvalAction(selectedApproval.id, 'reschedule', undefined, scheduledAt);
        if (!changed) throw new Error('Não foi possível alterar a data da aprovação.');
      }
      if (calendarScope.current !== workspaceId) return;
      updatePosts(current => current.map(post => post.id === postId && post.workspaceId === workspaceId
        ? { ...post, scheduledAt, history: [{ id: `post-history-${Date.now()}`, action: 'rescheduled', detail: `Reagendado para ${new Date(scheduledAt).toLocaleString('pt-BR')}`, actorName: currentUser?.name || 'Usuário', createdAt: new Date().toISOString() }, ...(post.history || [])] } : post));
      setNotice({ tone: 'success', text: 'Agendamento atualizado.' });
    } catch (error) {
      if (calendarScope.current === workspaceId) setNotice({ tone: 'error', text: error instanceof Error ? error.message : 'Não foi possível alterar o agendamento.' });
    } finally { if (calendarScope.current === workspaceId) setSchedulingId(undefined); }
  };

  const removeUnconfirmedSchedule = () => {
    if (!selectedPost || selectedPost.scheduledPublicationId || selectedPost.status === 'published') return;
    const postId = selectedPost.id;
    updatePosts(current => current.map(post => post.id === postId && post.workspaceId === activeWorkspace.id
      ? { ...post, scheduledAt: undefined, status: 'draft' } : post));
    setSelectedPostId(undefined);
    setNotice({ tone: 'success', text: 'Data removida. O conteúdo foi mantido como rascunho.' });
  };

  const generatePlan = async () => {
    if (!aiObjective.trim()) return setNotice({ tone: 'error', text: 'Descreva o objetivo do planejamento.' });
    setAiLoading(true); setAiSuggestions([]); setSelectedSuggestions([]); setNotice(undefined);
    const bounds = calendarPeriodBounds(currentDate, periodMode, customRange);
    if (!bounds) return setNotice({ tone: 'error', text: 'Selecione um intervalo de datas válido.' });
    const periodStart = bounds.start;
    const periodEnd = new Date(bounds.end.getTime() - 1);
    try {
      const response = await fetch('/api/ai/plan-calendar', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({
        objective: aiObjective, periodStart: periodStart.toISOString(), periodEnd: periodEnd.toISOString(), connectedPlatforms,
        existingPosts: normalizedPosts.map((post) => ({ title: post.title, platform: post.platform, status: post.status, scheduledAt: post.scheduledAt })),
        workspaceId: activeWorkspace.id, contextProfile: contextSnapshot, clientContext: activeClient, strategyContext: activeCampaign,
      }) });
      const data = await response.json().catch(() => ({}));
      if (calendarScope.current !== activeWorkspace.id) return;
      if (!response.ok) throw new Error(data.error || 'Não foi possível gerar o planejamento.');
      setAiSuggestions(data.suggestions || []);
      setSelectedSuggestions((data.suggestions || []).map((item: CalendarSuggestion) => item.id));
    } catch (error) {
      if (calendarScope.current !== activeWorkspace.id) return;
      setNotice({ tone: 'error', text: error instanceof Error ? error.message : 'Não foi possível gerar o planejamento.' });
    } finally { if (calendarScope.current === activeWorkspace.id) setAiLoading(false); }
  };

  const addSuggestions = () => {
    const selected = aiSuggestions.filter((item) => selectedSuggestions.includes(item.id));
    if (!selected.length) return;
    const createdAt = new Date().toISOString();
    addPosts(selected.map((suggestion, index): Post => ({
      id: `post-ai-${Date.now()}-${index}`, workspaceId: activeWorkspace.id, title: suggestion.title, platform: suggestion.platform,
      channels: [suggestion.platform], format: suggestion.format, copy: suggestion.copy, hashtags: [], scheduledAt: suggestion.suggestedAt,
      status: 'draft', author: currentUser?.name || 'KLIC', createdAt, responsibleId: currentUser?.id, responsibleName: currentUser?.name,
      socialAccountIds: authorizedAccounts.filter(account => account.platform === suggestion.platform).slice(0, 1).map(account => account.id),
      clientId: activeClient?.id,
      campaignId: activeCampaign?.id, strategyId: activeCampaign?.id, origin: 'ai', contextRevision: contextSnapshot.revision,
      history: [{ id: `post-history-ai-${Date.now()}-${index}`, action: 'ai_suggestion_accepted', detail: 'Sugestão da KLIC revisada e adicionada como rascunho', actorName: currentUser?.name || 'Usuário', createdAt }],
    })));
    setAiOpen(false); setAiSuggestions([]); setSelectedSuggestions([]);
    setNotice({ tone: 'success', text: `${selected.length} sugestão(ões) adicionada(s) como rascunho para revisão.` });
  };

  const navigatePeriod = (direction: number) => {
    if (periodMode === 'custom') {
      const bounds = calendarPeriodBounds(currentDate, periodMode, customRange);
      if (!bounds) return;
      const span = Math.max(1, Math.round((bounds.end.getTime() - bounds.start.getTime()) / 86_400_000));
      const start = new Date(bounds.start); const end = new Date(bounds.end);
      start.setDate(start.getDate() + direction * span); end.setDate(end.getDate() + direction * span - 1);
      const next = { start: dateKey(start), end: dateKey(end) };
      setCustomRange(next); setCustomRangeDraft(next); setCurrentDate(start);
      return;
    }
    setCurrentDate((date) => navigateCalendarDate(date, periodMode, direction));
  };
  const bounds = calendarPeriodBounds(currentDate, periodMode, customRange);
  useKlicPageDetails('calendar', klicPageScope(activeWorkspace.id, activeClient?.id), {
    ...(calendarArea === 'published' ? publishedContext : {
      view: `Agenda · ${displayMode}`,
      period: bounds ? `${dateKey(bounds.start)} a ${dateKey(new Date(bounds.end.getTime() - 1))}` : undefined,
      filters: { plataforma: filterPlatform, status: filterStatus, formato: filterFormat, responsavel: filterResponsible, campanha: filterCampaign },
      selected: selectedPost ? { kind: 'publicacao', id: selectedPost.id } : undefined,
    }),
  });
  const periodTitle = periodMode === 'day'
    ? currentDate.toLocaleDateString('pt-BR', { weekday: 'long', day: '2-digit', month: 'long', year: 'numeric' })
    : periodMode === 'week' && bounds
      ? `${compactPeriodDate(bounds.start)} — ${compactPeriodDate(new Date(bounds.end.getTime() - 1), true)}`
      : periodMode === 'custom' && bounds
        ? `${compactPeriodDate(bounds.start)} — ${compactPeriodDate(new Date(bounds.end.getTime() - 1), true)}`
        : currentDate.toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' });

  const selectPeriod = (mode: PeriodMode) => {
    if (mode === 'custom') {
      setCustomRangeDraft(customRange);
      setShowCustomRange(true);
      return;
    }
    setPeriodMode(mode);
    if (mode === 'day') setCurrentDate(new Date());
    setShowCustomRange(false);
  };

  const applyCustomRange = () => {
    const nextBounds = calendarPeriodBounds(currentDate, 'custom', customRangeDraft);
    if (!nextBounds) return setNotice({ tone: 'error', text: 'A data final deve ser igual ou posterior à data inicial.' });
    setCustomRange(customRangeDraft); setCurrentDate(nextBounds.start); setPeriodMode('custom'); setDisplayMode('list'); setShowCustomRange(false); setNotice(undefined);
  };

  const historySource = (job: ConfirmedPublication, post?: Post): Post | null => {
    if (post) return post;
    const platform = job.provider || connectedAccounts.find(account => account.id === job.connectionId)?.platform;
    if (!platform) return null;
    const format: PostFormat = job.request.kind === 'carousel' ? 'carousel' : job.request.kind === 'story' ? 'story'
      : job.request.kind === 'short_video' || job.request.kind === 'video' ? 'reels' : 'post';
    return { id: job.contentId, workspaceId: activeWorkspace.id, title: job.title || job.request.text?.slice(0, 80) || 'Publicação',
      platform, channels: [platform], format, copy: job.request.text || '', hashtags: [], status: 'published',
      scheduledAt: job.scheduledAt, author: 'Clicko', createdAt: job.createdAt, clientId: job.clientId,
      socialAccountIds: [job.connectionId], externalPostId: job.providerPostId };
  };

  const duplicateFromHistory = (job: ConfirmedPublication, post?: Post) => {
    const source = historySource(job, post);
    if (!source) return setNotice({ tone: 'error', text: 'A rede desta publicação não está disponível para duplicação.' });
    const account = connectedAccounts.find(item => item.id === job.connectionId && item.connected);
    const nextDate = new Date(); nextDate.setDate(nextDate.getDate() + 1);
    setForm({ title: source.title, copy: source.copy, date: dateKey(nextDate), time: '09:00', channels: [source.platform], format: source.format,
      status: 'draft', responsibleId: currentUser?.id || '', campaignId: source.campaignId || '', assetIds: source.assetIds || [],
      accountIds: account ? [account.id] : [], clientId: source.clientId || '', requiresApproval: false, tiktokConsent: false });
    setCreateOpen(true);
  };

  const reuseFromHistory = (job: ConfirmedPublication, post?: Post) => {
    const source = historySource(job, post);
    if (!source) return setNotice({ tone: 'error', text: 'A rede desta publicação não está disponível para reutilização.' });
    createRepurposeHandoff(source, source.format);
    onNavigate?.('create-copy');
  };

  const viewHistoryPerformance = (job: ConfirmedPublication) => {
    const query = new URLSearchParams({ publication: job.providerPostId || job.contentId, account: job.connectionId,
      date: job.updatedAt.slice(0, 10), title: job.title || 'Publicação' });
    onNavigate?.('analytics');
    window.history.replaceState({}, '', `/analytics?${query.toString()}`);
  };

  return <div className="clicko-calendar-workspace mx-auto w-full max-w-[1500px] space-y-5 p-5 sm:p-6 2xl:p-9">
    <header className="calendar-page-header flex flex-col gap-5 border-b border-white/[0.06] pb-6 xl:flex-row xl:items-end xl:justify-between">
      <div className="max-w-2xl"><p className="text-[10px] font-medium uppercase tracking-[0.22em] text-[#FF7F50]">Operação de conteúdo</p><h1 className="mt-2 text-2xl font-semibold tracking-[-0.02em] text-white">Calendário</h1><p className="mt-2 text-sm leading-6 text-[#808080]">Planeje, aprove, agende e acompanhe cada conteúdo em um fluxo centralizado.</p></div>
      <div className="calendar-header-actions flex flex-wrap gap-2"><button onClick={() => openCreate()} className="inline-flex h-9 items-center gap-2 rounded-lg bg-[#FF7F50] px-4 text-[10px] font-semibold text-[#000000]"><Plus className="h-4 w-4" />Novo conteúdo</button></div>
    </header>

    {notice && <div role="status" className={`flex items-center justify-between gap-4 rounded-xl border px-4 py-3 text-[10px] ${notice.tone === 'error' ? 'border-[#F28500]/15 bg-[#F28500]/[0.045] text-[#F28500]' : 'border-[#FF7F50]/15 bg-[#FF7F50]/[0.035] text-[rgba(255,255,255,0.72)]'}`}><span className="flex items-center gap-2">{notice.tone === 'error' ? <AlertCircle className="h-4 w-4 text-[#F28500]" /> : <Check className="h-4 w-4 text-[#FF7F50]" />}{notice.text}</span><button onClick={() => setNotice(undefined)} aria-label="Fechar aviso"><X className="h-3.5 w-3.5" /></button></div>}

    <nav className="calendar-area-tabs" aria-label="Áreas do Calendário"><button type="button" className={calendarArea === 'schedule' ? 'is-active' : ''} aria-current={calendarArea === 'schedule' ? 'page' : undefined} onClick={() => setCalendarArea('schedule')}><CalendarDays />Agenda</button><button type="button" className={calendarArea === 'published' ? 'is-active' : ''} aria-current={calendarArea === 'published' ? 'page' : undefined} onClick={() => setCalendarArea('published')}><Check />Publicados</button></nav>

    {calendarArea === 'schedule' ? <>

    <section aria-label="Próximos conteúdos" className="calendar-upcoming rounded-xl border border-white/[0.06] bg-[rgba(128,128,128,0.14)] p-4">
      <div className="mb-3 flex items-center justify-between"><div><h2 className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[rgba(255,255,255,0.72)]">Próximos conteúdos</h2><p className="mt-1 text-[9px] text-[#808080]">O que exige atenção nas próximas horas e dias.</p></div><button onClick={() => { setCurrentDate(new Date()); setPeriodMode('day'); setDisplayMode('calendar'); setShowCustomRange(false); }} className="rounded-lg px-2.5 py-2 text-[9px] text-[#808080] hover:bg-white/[0.04] hover:text-white">Ir para hoje</button></div>
      {futurePosts.length ? <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">{futurePosts.map((post) => <button key={post.id} onClick={() => { setSelectedPostId(post.id); onSelectPost?.(post); }} className="flex min-w-0 items-center gap-3 rounded-lg border border-white/[0.05] bg-black/15 p-3 text-left transition hover:border-white/[0.1]"><span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-white/[0.04] text-[8px] font-semibold text-[rgba(255,255,255,0.72)]">{visiblePlatforms.find((item) => item.id === post.platform)?.short}</span><span className="min-w-0 flex-1"><strong className="block truncate text-[9px] font-medium text-white">{post.title}</strong><span className="mt-1 block text-[8px] text-[#808080]">{new Date(post.scheduledAt!).toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' })} · {scheduledTime(post)}</span></span><span className={`h-1.5 w-1.5 rounded-full ${statusDot[post.status]}`} /></button>)}</div> : <div className="rounded-lg border border-dashed border-white/[0.06] py-4 text-center text-[9px] text-[#808080]">Nenhum conteúdo futuro com os filtros atuais.</div>}
    </section>

    <section className="calendar-main-section space-y-3">
      <div className="calendar-period-card rounded-xl border border-white/[0.06] bg-[rgba(128,128,128,0.14)] p-3">
        <div className="calendar-period-nav"><button onClick={() => navigatePeriod(-1)} aria-label="Período anterior"><ChevronLeft /></button><div><span>Período selecionado</span><h2>{periodTitle}</h2></div><button onClick={() => navigatePeriod(1)} aria-label="Próximo período"><ChevronRight /></button></div>
        <div className="calendar-period-presets" role="tablist" aria-label="Selecionar período">{([{ id: 'day', label: 'Hoje', icon: Clock3 }, { id: 'week', label: 'Semana', icon: CalendarDays }, { id: 'month', label: 'Mês', icon: CalendarDays }, { id: 'custom', label: 'Personalizado', icon: CalendarRange }] as const).map(({ id, label, icon: Icon }) => { const active = periodMode === id || (id === 'custom' && showCustomRange); return <button type="button" role="tab" aria-selected={active} key={id} onClick={() => selectPeriod(id)} className={active ? 'is-active' : ''}><Icon />{label}</button>; })}</div>
        <div className="calendar-toolbar-actions"><div className="calendar-display-toggle" aria-label="Forma de exibição"><button type="button" aria-pressed={displayMode === 'calendar'} onClick={() => setDisplayMode('calendar')} className={displayMode === 'calendar' ? 'is-active' : ''}><CalendarDays />Calendário</button><button type="button" aria-pressed={displayMode === 'list'} onClick={() => setDisplayMode('list')} className={displayMode === 'list' ? 'is-active' : ''}><LayoutList />Lista</button></div><button type="button" onClick={() => setShowFilters((value) => !value)} aria-expanded={showFilters} className={`calendar-filter-button ${showFilters ? 'is-active' : ''}`}><Filter />Filtros</button></div>
      </div>

      {showCustomRange && <div className="calendar-custom-range" role="group" aria-label="Intervalo personalizado"><div><CalendarRange /><span><strong>Escolha seu intervalo</strong><small>Selecione a data inicial e a data final.</small></span></div><label><span>Data inicial</span><input type="date" value={customRangeDraft.start} onInput={event => { const value = event.currentTarget.value; setCustomRangeDraft(current => ({ ...current, start: value })); }} /></label><label><span>Data final</span><input type="date" min={customRangeDraft.start} value={customRangeDraft.end} onInput={event => { const value = event.currentTarget.value; setCustomRangeDraft(current => ({ ...current, end: value })); }} /></label><div className="calendar-custom-actions"><button type="button" onClick={() => { setShowCustomRange(false); setCustomRangeDraft(customRange); }}>Cancelar</button><button type="button" onClick={applyCustomRange}>Aplicar período</button></div></div>}

      {showFilters && <div className="calendar-filter-grid grid gap-2 rounded-xl border border-white/[0.055] bg-white/[0.018] p-3 sm:grid-cols-2 lg:grid-cols-5">
        <FilterSelect label="Plataforma" value={filterPlatform} onChange={setFilterPlatform} options={[['all', 'Todas'], ...visiblePlatforms.map((item) => [item.id, item.label])]} />
        <FilterSelect label="Status" value={filterStatus} onChange={setFilterStatus} options={[['all', 'Todos'], ...Object.entries(postStatusLabel)]} />
        <FilterSelect label="Formato" value={filterFormat} onChange={setFilterFormat} options={[['all', 'Todos'], ...formats.map((item) => [item.id, item.label])]} />
        <FilterSelect label="Responsável" value={filterResponsible} onChange={setFilterResponsible} options={[['all', 'Todos'], ...users.filter((user) => user.status === 'active').map((user) => [user.id, user.name])]} />
        <FilterSelect label="Campanha" value={filterCampaign} onChange={setFilterCampaign} options={[['all', 'Todas'], ...campaigns.map((campaign) => [campaign.id, campaign.name])]} />
      </div>}

      {displayMode === 'list' ? <ListView posts={listPosts} onOpen={(post) => { setSelectedPostId(post.id); onSelectPost?.(post); }} /> : <div className="calendar-grid-shell custom-scrollbar overflow-x-auto rounded-xl border border-white/[0.06] bg-[rgba(128,128,128,0.14)] p-3">
        <div style={{ minWidth: periodMode === 'month' || periodMode === 'week' ? 820 : Math.max(220, calendarDates.length * 170) }}><div className="calendar-weekdays grid border-b border-white/[0.05] pb-2 text-center text-[8px] font-semibold uppercase tracking-[0.12em] text-[#808080]" style={{ gridTemplateColumns: `repeat(${Math.max(1, periodMode === 'month' || periodMode === 'week' ? 7 : calendarDates.length)}, minmax(0, 1fr))` }}>{periodMode === 'month' || periodMode === 'week' ? ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'].map((day) => <div key={day}>{day}</div>) : calendarDates.map(date => <div key={dateKey(date)}>{date.toLocaleDateString('pt-BR', { weekday: 'short' })}</div>)}</div>
          <div className="calendar-days-grid mt-2 grid gap-1.5" style={{ gridTemplateColumns: `repeat(${Math.max(1, periodMode === 'month' || periodMode === 'week' ? 7 : calendarDates.length)}, minmax(0, 1fr))` }}>{calendarDates.map((date) => {
            const key = dateKey(date); const dayPosts = postsByDay.get(key) || []; const today = key === dateKey(new Date()); const otherMonth = periodMode === 'month' && date.getMonth() !== currentDate.getMonth();
            return <div key={key} onDragOver={(event) => event.preventDefault()} onDrop={() => draggedPostId && movePost(draggedPostId, date)} className={`group flex ${periodMode === 'month' ? 'min-h-[128px]' : 'min-h-[360px]'} flex-col rounded-lg border p-2 transition ${today ? 'border-[#FF7F50]/25 bg-[#FF7F50]/[0.035]' : otherMonth ? 'border-white/[0.025] bg-white/[0.008] opacity-40' : 'border-white/[0.045] bg-white/[0.014] hover:border-white/[0.09]'}`}>
              <button onClick={() => openCreate(date)} className="flex items-center justify-between text-left"><span className={`text-[9px] font-medium ${today ? 'text-[#FF7F50]' : 'text-[#808080]'}`}>{date.getDate()}</span>{today && <span className="text-[7px] uppercase text-[#FF7F50]">Hoje</span>}<Plus className="h-3 w-3 text-[#808080] opacity-0 transition group-hover:opacity-100" /></button>
              <div className="mt-2 space-y-1.5">{dayPosts.slice(0, periodMode === 'month' ? 3 : 8).map((post) => <CalendarEvent key={post.id} post={post} onDrag={() => setDraggedPostId(post.id)} onOpen={() => { setSelectedPostId(post.id); onSelectPost?.(post); }} />)}{dayPosts.length > (periodMode === 'month' ? 3 : 8) && <button onClick={() => setDisplayMode('list')} className="w-full py-1 text-center text-[7px] text-[#808080]">+{dayPosts.length - (periodMode === 'month' ? 3 : 8)} conteúdos</button>}</div>
            </div>;
          })}</div>
        </div>
      </div>}
    </section>

    <section aria-label="Planejamento inteligente" className="border-t border-white/[0.06] pt-5"><div className="mb-3 flex items-center gap-2"><KlicSymbol className="h-4 w-4 text-[#FF7F50]" /><h2 className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[rgba(255,255,255,0.72)]">Planejamento inteligente</h2></div><div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">{planningSignals.map((signal) => <div key={signal.label} className="rounded-lg border border-white/[0.05] bg-white/[0.015] px-3 py-2.5"><span className="text-[8px] text-[#808080]">{signal.label}</span><strong className={`mt-1 block text-[9px] font-medium ${signal.tone === 'warning' ? 'text-[#F28500]' : signal.tone === 'positive' ? 'text-[#FF7F50]' : 'text-[rgba(255,255,255,0.72)]'}`}>{signal.value}</strong></div>)}</div></section>
    </> : <PublishedHistory key={activeWorkspace.id} jobs={publicationJobs.filter(job => job.ownerId === activeWorkspace.id)} posts={normalizedPosts} accounts={connectedAccounts} clients={clients} assets={assets} loading={publicationHistoryLoading} error={publicationHistoryError} canRead={canReadConnections} onDuplicate={duplicateFromHistory} onReuse={reuseFromHistory} onPerformance={viewHistoryPerformance} onContextChange={setPublishedContext} />}

    {createOpen && <CreatePanel form={form} setForm={setForm} connectedPlatforms={connectedPlatforms} connectedAccounts={authorizedAccounts} clients={clients} assets={assets} users={users} campaigns={campaigns} environmentMode={environmentMode} requiresWorkspaceApproval={Boolean(workspace?.settings.requireApproval)} toggleChannel={toggleChannel} toggleAsset={toggleAsset} onClose={() => setCreateOpen(false)} onSave={saveContent} onAdvanced={() => { setCreateOpen(false); onNewPost(); }} onNavigate={(tab) => { setCreateOpen(false); onNavigate?.(tab); }} />}
    {aiOpen && <AIPlanningPanel objective={aiObjective} setObjective={setAiObjective} loading={aiLoading} suggestions={aiSuggestions} selected={selectedSuggestions} connectedPlatforms={connectedPlatforms} onToggle={(id) => setSelectedSuggestions((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id])} onGenerate={generatePlan} onAdd={addSuggestions} onClose={() => setAiOpen(false)} onConnect={() => { setAiOpen(false); onNavigate?.('connected-accounts'); }} />}
    {selectedPost && <DetailPanel post={selectedPost} approval={selectedApproval} campaignName={campaigns.find((campaign) => campaign.id === selectedPost.campaignId)?.name} assetNames={(selectedPost.assetIds || []).map((id) => assets.find((asset) => asset.id === id)?.title).filter(Boolean) as string[]} canApprove={canApprove && Boolean(selectedApproval && ['pending_approval', 'in_review'].includes(selectedApproval.stage))} canSchedule={canPublish && selectedApproval?.stage === 'approved' && selectedPost.status !== 'cancelled' && !selectedPost.scheduledPublicationId && Boolean(selectedPost.scheduledAt && Date.parse(selectedPost.scheduledAt) > Date.now())} canCancelSchedule={canPublish && selectedPost.status === 'scheduled' && Boolean(selectedPost.scheduledPublicationId)} canEditSchedule={Boolean(selectedPost.scheduledAt && !['processing', 'published', 'cancelled'].includes(selectedPost.status) && (!selectedApproval || canApprove) && (!selectedPost.scheduledPublicationId || canPublish))} canRemoveSchedule={Boolean(selectedPost.scheduledAt && !selectedPost.scheduledPublicationId && !['processing', 'published'].includes(selectedPost.status) && (!selectedApproval || canApprove))} scheduling={schedulingId === selectedPost.id} onSchedule={() => void handleScheduleApproved()} onCancelSchedule={() => void handleCancelSchedule()} onReschedule={(date, time) => void handleRescheduleSelected(date, time)} onRemoveSchedule={removeUnconfirmedSchedule} onApprove={() => handleApproval('approve')} onRequestChanges={() => handleApproval('request_changes')} onClose={() => setSelectedPostId(undefined)} onFixConnection={() => { setSelectedPostId(undefined); onNavigate?.('connected-accounts'); }} />}
  </div>;
};

function FilterSelect({ label, value, onChange, options }: { label: string; value: string; onChange: (value: string) => void; options: string[][] }) {
  return <ClickoSelectMenu label={label} value={value} onChange={onChange} options={options} className="calendar-filter-select" triggerClassName="calendar-filter-trigger" menuClassName="calendar-filter-menu" />;
}

function CalendarEvent({ post, onDrag, onOpen }: { key?: React.Key; post: Post; onDrag: () => void; onOpen: () => void }) {
  const channels = post.channels?.length ? post.channels : [post.platform];
  return <button draggable={post.status !== 'published'} onDragStart={onDrag} onClick={onOpen} className="block w-full rounded-md border border-white/[0.045] bg-black/20 p-2 text-left transition hover:border-white/[0.12]"><div className="flex items-start gap-1.5"><span className={`mt-1 h-1.5 w-1.5 shrink-0 rounded-full ${statusDot[post.status]}`} /><span className="min-w-0 flex-1"><strong className="block truncate text-[8px] font-medium text-[rgba(255,255,255,0.88)]">{post.title}</strong><span className="mt-1 flex items-center gap-1 text-[7px] text-[#808080]"><Clock3 className="h-2.5 w-2.5" />{scheduledTime(post)} · {channels.slice(0, 2).map((platform) => visiblePlatforms.find((item) => item.id === platform)?.short).join(' + ')}{channels.length > 2 ? ` +${channels.length - 2}` : ''}</span></span></div></button>;
}

function ListView({ posts, onOpen }: { posts: Post[]; onOpen: (post: Post) => void }) {
  const sorted = [...posts].sort((a, b) => String(a.scheduledAt || '9999').localeCompare(String(b.scheduledAt || '9999')));
  return <div className="overflow-hidden rounded-xl border border-white/[0.06] bg-[rgba(128,128,128,0.14)]">{sorted.length ? sorted.map((post) => <button key={post.id} onClick={() => onOpen(post)} className="grid w-full grid-cols-[92px_1fr_auto] items-center gap-3 border-b border-white/[0.045] px-4 py-3 text-left last:border-0 hover:bg-white/[0.018] sm:grid-cols-[125px_1fr_110px_130px]"><span className="text-[8px] text-[#808080]">{post.scheduledAt ? new Date(post.scheduledAt).toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' }) : 'Sem data'}<strong className="ml-1 font-medium text-[rgba(255,255,255,0.72)]">{scheduledTime(post)}</strong></span><span className="min-w-0"><strong className="block truncate text-[9px] font-medium text-white">{post.title}</strong><span className="mt-1 block truncate text-[8px] text-[#808080]">{formatPlatform(post.platform)} · {formatName(post.format)} · {post.responsibleName || post.author}</span></span><span className="hidden text-[8px] text-[#808080] sm:block">{post.channels?.length || 1} canal(is)</span><span className={`justify-self-end rounded-full px-2 py-1 text-[7px] ${statusStyle[post.status]}`}>{postStatusLabel[post.status]}</span></button>) : <div className="p-10 text-center text-[9px] text-[#808080]">Nenhum conteúdo encontrado.</div>}</div>;
}

type CreationForm = { title: string; copy: string; date: string; time: string; channels: SocialPlatform[]; accountIds: string[]; clientId: string; format: PostFormat; status: Extract<PostStatus, 'draft' | 'in_production' | 'scheduled'>; responsibleId: string; campaignId: string; assetIds: string[]; requiresApproval: boolean; tiktokConsent: boolean };

function CreatePanel({ form, setForm, connectedPlatforms, connectedAccounts, clients, assets, users, campaigns, environmentMode, requiresWorkspaceApproval, toggleChannel, toggleAsset, onClose, onSave, onAdvanced, onNavigate }: {
  form: CreationForm; setForm: React.Dispatch<React.SetStateAction<CreationForm>>; connectedPlatforms: SocialPlatform[]; connectedAccounts: ReturnType<typeof useOperations>['connectedAccounts']; clients: ReturnType<typeof useOperations>['clients']; assets: ReturnType<typeof useOperations>['assets']; users: ReturnType<typeof useGovernance>['users']; campaigns: ReturnType<typeof useOperations>['campaigns']; environmentMode: ReturnType<typeof useGovernance>['environmentMode']; requiresWorkspaceApproval: boolean; toggleChannel: (platform: SocialPlatform) => void; toggleAsset: (id: string) => void; onClose: () => void; onSave: () => void; onAdvanced: () => void; onNavigate: (tab: NavigationTab) => void;
}) {
  return <div className="fixed inset-0 z-[100] flex justify-end bg-black/70 backdrop-blur-sm" role="dialog" aria-modal="true" aria-labelledby="new-content-title"><button className="absolute inset-0" onClick={onClose} aria-label="Fechar criação" /><aside className="relative h-full w-full max-w-[520px] overflow-y-auto border-l border-white/[0.07] bg-[rgba(128,128,128,0.14)] p-5 shadow-2xl sm:p-6">
    <div className="flex items-start justify-between border-b border-white/[0.06] pb-5"><div><p className="text-[9px] uppercase tracking-[0.18em] text-[#FF7F50]">Planejar conteúdo</p><h2 id="new-content-title" className="mt-1.5 text-lg font-semibold text-white">Novo conteúdo</h2><p className="mt-1 text-[9px] text-[#808080]">Defina somente o essencial. Você poderá refinar depois.</p></div><button onClick={onClose} aria-label="Fechar" className="rounded-lg p-2 text-[#808080] hover:bg-white/[0.05] hover:text-white"><X className="h-4 w-4" /></button></div>
    <div className="mt-5 grid grid-cols-2 gap-2"><button onClick={onAdvanced} className="rounded-lg border border-white/[0.06] p-3 text-left hover:border-white/[0.12]"><Plus className="h-4 w-4 text-[#FF7F50]" /><strong className="mt-2 block text-[9px] text-white">Editor completo</strong><span className="mt-1 block text-[7px] text-[#808080]">Criar do zero</span></button><button onClick={() => onNavigate('library')} className="rounded-lg border border-white/[0.06] p-3 text-left hover:border-white/[0.12]"><FolderOpen className="h-4 w-4 text-[#FF7F50]" /><strong className="mt-2 block text-[9px] text-white">Biblioteca</strong><span className="mt-1 block text-[7px] text-[#808080]">Escolher material</span></button></div>
    <div className="mt-6 space-y-4"><Field label="Título"><input value={form.title} onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))} placeholder="Identificação curta do conteúdo" /></Field><Field label="Texto ou orientação"><textarea rows={4} value={form.copy} onChange={(event) => setForm((current) => ({ ...current, copy: event.target.value }))} placeholder="Legenda, roteiro ou orientação para a equipe" /></Field>
      <div><span className="mb-2 block text-[8px] text-[#808080]">Canais</span><div className="grid grid-cols-3 gap-2">{visiblePlatforms.map((platform) => { const connected = connectedPlatforms.includes(platform.id); const selected = form.channels.includes(platform.id); return <button key={platform.id} onClick={() => toggleChannel(platform.id)} className={`rounded-lg border p-2.5 text-left transition ${selected ? 'border-[#FF7F50]/30 bg-[#FF7F50]/[0.045]' : 'border-white/[0.06] bg-white/[0.012]'}`}><span className="flex items-center justify-between"><strong className="text-[8px] text-[rgba(255,255,255,0.88)]">{platform.short}</strong><span className={`h-1.5 w-1.5 rounded-full ${connected ? 'bg-[#FF7F50]' : 'bg-[#808080]'}`} /></span><span className="mt-1.5 block truncate text-[7px] text-[#808080]">{platform.label}</span></button>; })}</div>{!connectedPlatforms.length && <button onClick={() => onNavigate('connected-accounts')} className="mt-2 text-[8px] text-[#F28500]">Nenhuma rede autorizada · abrir Conexões</button>}</div>
      {environmentMode === 'company' && <Field label="Cliente"><select value={form.clientId} onChange={event => setForm(current => ({ ...current, clientId: event.target.value, campaignId: '', accountIds: [] }))}><option value="">Sem cliente</option>{clients.map(client => <option key={client.id} value={client.id}>{client.name}</option>)}</select></Field>}
      {form.channels.map(platform => <Field key={platform} label={`Conta ${formatPlatform(platform)}`}><select value={form.accountIds.find(id => connectedAccounts.some(account => account.id === id && account.platform === platform)) || ''} onChange={event => setForm(current => ({ ...current, accountIds: [...current.accountIds.filter(id => !connectedAccounts.some(account => account.id === id && account.platform === platform)), event.target.value] }))}><option value="">Selecione uma conta</option>{connectedAccounts.filter(account => account.platform === platform).map(account => <option key={account.id} value={account.id}>{account.name || account.handle} · {account.handle}</option>)}</select></Field>)}
      <div className="grid grid-cols-2 gap-3"><Field label="Formato"><select value={form.format} onChange={(event) => setForm((current) => ({ ...current, format: event.target.value as PostFormat }))}>{formats.map((format) => <option key={format.id} value={format.id}>{format.label}</option>)}</select></Field><Field label="Etapa"><select value={form.status} onChange={(event) => setForm((current) => ({ ...current, status: event.target.value as CreationForm['status'] }))}><option value="draft">Rascunho</option><option value="in_production">Em produção</option><option value="scheduled">Agendado</option></select></Field></div>
      <div className="grid grid-cols-2 gap-3"><Field label="Data"><input type="date" value={form.date} onChange={(event) => setForm((current) => ({ ...current, date: event.target.value }))} /></Field><Field label="Horário"><input type="time" value={form.time} onChange={(event) => setForm((current) => ({ ...current, time: event.target.value }))} /></Field></div>
      <div className="grid grid-cols-2 gap-3"><Field label="Responsável"><select value={form.responsibleId} onChange={(event) => setForm((current) => ({ ...current, responsibleId: event.target.value }))}>{users.filter((user) => user.status === 'active').map((user) => <option key={user.id} value={user.id}>{user.name}</option>)}</select></Field><Field label="Campanha"><select value={form.campaignId} onChange={(event) => setForm((current) => ({ ...current, campaignId: event.target.value }))}><option value="">Sem campanha</option>{campaigns.map((campaign) => <option key={campaign.id} value={campaign.id}>{campaign.name}</option>)}</select></Field></div>
      <div><span className="mb-2 block text-[8px] text-[#808080]">Materiais da Biblioteca</span>{assets.length ? <div className="max-h-36 space-y-1.5 overflow-y-auto">{assets.slice(0, 10).map((asset) => <button key={asset.id} onClick={() => toggleAsset(asset.id)} className={`flex w-full items-center gap-2 rounded-lg border px-3 py-2 text-left ${form.assetIds.includes(asset.id) ? 'border-[#FF7F50]/25 bg-[#FF7F50]/[0.035]' : 'border-white/[0.05]'}`}><FolderOpen className="h-3.5 w-3.5 text-[#808080]" /><span className="min-w-0 flex-1 truncate text-[8px] text-[rgba(255,255,255,0.72)]">{asset.title}</span>{form.assetIds.includes(asset.id) && <Check className="h-3 w-3 text-[#FF7F50]" />}</button>)}</div> : <p className="rounded-lg border border-dashed border-white/[0.06] p-3 text-[8px] text-[#808080]">Nenhum material disponível.</p>}</div>
      {environmentMode === 'company' && requiresWorkspaceApproval && <label className="flex items-center justify-between rounded-lg border border-white/[0.055] p-3"><span><strong className="block text-[9px] font-medium text-[rgba(255,255,255,0.88)]">Enviar para aprovação</strong><span className="mt-1 block text-[7px] text-[#808080]">Obrigatório para colaboradores; opcional para o administrador.</span></span><input type="checkbox" checked={form.requiresApproval} onChange={(event) => setForm((current) => ({ ...current, requiresApproval: event.target.checked }))} className="accent-[#FF7F50]" /></label>}
      {form.channels.includes('tiktok') && form.status === 'scheduled' && <label className="flex items-center justify-between rounded-lg border border-white/[0.055] p-3"><span className="text-[9px] text-[rgba(255,255,255,0.88)]">Autorizo o envio deste vídeo ao TikTok no horário escolhido.</span><input type="checkbox" checked={form.tiktokConsent} onChange={event => setForm(current => ({ ...current, tiktokConsent: event.target.checked }))} className="accent-[#FF7F50]" /></label>}
    </div>
    <button onClick={onSave} className="mt-6 h-10 w-full rounded-lg bg-[#FF7F50] text-[10px] font-semibold text-[#000000]">Adicionar ao calendário</button>
  </aside></div>;
}

function Field({ label, children }: { label: string; children: React.ReactNode }) { return <label className="block"><span className="mb-1.5 block text-[8px] text-[#808080]">{label}</span><span className="contents [&_input]:h-10 [&_input]:w-full [&_input]:rounded-lg [&_input]:border [&_input]:border-white/[0.07] [&_input]:bg-[rgba(128,128,128,0.14)] [&_input]:px-3 [&_input]:text-[9px] [&_input]:text-white [&_input]:outline-none [&_select]:h-10 [&_select]:w-full [&_select]:rounded-lg [&_select]:border [&_select]:border-white/[0.07] [&_select]:bg-[rgba(128,128,128,0.14)] [&_select]:px-3 [&_select]:text-[9px] [&_select]:text-white [&_textarea]:w-full [&_textarea]:rounded-lg [&_textarea]:border [&_textarea]:border-white/[0.07] [&_textarea]:bg-[rgba(128,128,128,0.14)] [&_textarea]:p-3 [&_textarea]:text-[9px] [&_textarea]:leading-relaxed [&_textarea]:text-white [&_textarea]:outline-none">{children}</span></label>; }

function AIPlanningPanel({ objective, setObjective, loading, suggestions, selected, connectedPlatforms, onToggle, onGenerate, onAdd, onClose, onConnect }: { objective: string; setObjective: (value: string) => void; loading: boolean; suggestions: CalendarSuggestion[]; selected: string[]; connectedPlatforms: SocialPlatform[]; onToggle: (id: string) => void; onGenerate: () => void; onAdd: () => void; onClose: () => void; onConnect: () => void }) {
  return <div className="fixed inset-0 z-[100] flex justify-end bg-black/70 backdrop-blur-sm" role="dialog" aria-modal="true" aria-labelledby="ai-plan-title"><button className="absolute inset-0" onClick={onClose} aria-label="Fechar planejamento" /><aside className="relative h-full w-full max-w-[500px] overflow-y-auto border-l border-white/[0.07] bg-[rgba(128,128,128,0.14)] p-5 sm:p-6"><div className="flex items-start justify-between border-b border-white/[0.06] pb-5"><div><p className="text-[9px] uppercase tracking-[0.18em] text-[#FF7F50]">KLIC</p><h2 id="ai-plan-title" className="mt-1.5 text-lg font-semibold text-white">Planejar calendário</h2><p className="mt-1 text-[9px] text-[#808080]">As sugestões só entram no calendário após sua revisão.</p></div><button onClick={onClose} aria-label="Fechar" className="rounded-lg p-2 text-[#808080] hover:bg-white/[0.05]"><X className="h-4 w-4" /></button></div>
    <div className="mt-5"><label className="text-[8px] text-[#808080]">Objetivo do período</label><textarea rows={4} value={objective} onChange={(event) => setObjective(event.target.value)} placeholder="Ex.: distribuir uma campanha educativa com três publicações por semana..." className="mt-2 w-full rounded-xl border border-white/[0.07] bg-[rgba(128,128,128,0.14)] p-3 text-[9px] leading-relaxed text-white outline-none" />{connectedPlatforms.length ? <p className="mt-2 text-[8px] text-[#808080]">Canais autorizados: {connectedPlatforms.map(formatPlatform).join(', ')}</p> : <button onClick={onConnect} className="mt-2 text-[8px] text-[#F28500]">Conecte uma rede social para planejar a distribuição.</button>}<button disabled={loading || !connectedPlatforms.length} onClick={onGenerate} className="mt-4 inline-flex h-9 w-full items-center justify-center gap-2 rounded-lg border border-white/[0.08] text-[9px] font-medium text-white disabled:opacity-40">{loading ? <ClickoLoader size="tiny" label="Analisando o calendário" /> : <KlicSymbol className="h-4 w-4 text-[#FF7F50]" />}{loading ? 'Analisando o calendário...' : 'Gerar sugestões'}</button></div>
    {suggestions.length > 0 && <div className="mt-6 space-y-2"><h3 className="text-[9px] font-semibold uppercase tracking-[0.15em] text-[rgba(255,255,255,0.72)]">Revisar sugestões</h3>{suggestions.map((suggestion) => { const checked = selected.includes(suggestion.id); return <button key={suggestion.id} onClick={() => onToggle(suggestion.id)} className={`w-full rounded-xl border p-3 text-left ${checked ? 'border-[#FF7F50]/25 bg-[#FF7F50]/[0.035]' : 'border-white/[0.06]'}`}><div className="flex items-start gap-3"><span className={`mt-0.5 grid h-4 w-4 shrink-0 place-items-center rounded border ${checked ? 'border-[#FF7F50] bg-[#FF7F50] text-[#000000]' : 'border-white/15'}`}>{checked && <Check className="h-3 w-3" />}</span><span className="min-w-0 flex-1"><strong className="block text-[9px] text-white">{suggestion.title}</strong><span className="mt-1 block text-[8px] text-[#808080]">{formatPlatform(suggestion.platform)} · {formatName(suggestion.format)} · {new Date(suggestion.suggestedAt).toLocaleString('pt-BR', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })}</span><span className="mt-2 block text-[8px] leading-relaxed text-[#808080]">{suggestion.rationale}</span></span></div></button>; })}<button onClick={onAdd} className="mt-4 h-10 w-full rounded-lg bg-[#FF7F50] text-[10px] font-semibold text-[#000000]">Adicionar selecionados como rascunho</button></div>}
  </aside></div>;
}

function DetailPanel({ post, approval, campaignName, assetNames, canApprove, canSchedule, canCancelSchedule, canEditSchedule, canRemoveSchedule, scheduling, onSchedule, onCancelSchedule, onReschedule, onRemoveSchedule, onApprove, onRequestChanges, onClose, onFixConnection }: { post: Post; approval?: ReturnType<typeof useGovernance>['approvals'][number]; campaignName?: string; assetNames: string[]; canApprove: boolean; canSchedule: boolean; canCancelSchedule: boolean; canEditSchedule: boolean; canRemoveSchedule: boolean; scheduling: boolean; onSchedule: () => void; onCancelSchedule: () => void; onReschedule: (date: string, time: string) => void; onRemoveSchedule: () => void; onApprove: () => void; onRequestChanges: () => void; onClose: () => void; onFixConnection: () => void }) {
  const history = [...(approval?.history || []).map((entry) => ({ id: entry.id, detail: entry.detail, actorName: entry.actorName, createdAt: entry.createdAt })), ...(post.history || [])].sort((a, b) => b.createdAt.localeCompare(a.createdAt));
  const channels = post.channels?.length ? post.channels : [post.platform];
  const [date, setDate] = React.useState(() => post.scheduledAt ? dateKey(new Date(post.scheduledAt)) : '');
  const [time, setTime] = React.useState(() => post.scheduledAt ? `${pad(new Date(post.scheduledAt).getHours())}:${pad(new Date(post.scheduledAt).getMinutes())}` : '09:00');
  return <div className="fixed inset-0 z-[100] flex justify-end bg-black/70 backdrop-blur-sm" role="dialog" aria-modal="true" aria-labelledby="content-detail-title"><button className="absolute inset-0" onClick={onClose} aria-label="Fechar conteúdo" /><aside className="relative h-full w-full max-w-[500px] overflow-y-auto border-l border-white/[0.07] bg-[rgba(128,128,128,0.14)] p-5 sm:p-6"><div className="flex items-start justify-between border-b border-white/[0.06] pb-5"><div className="min-w-0"><span className={`inline-flex rounded-full px-2 py-1 text-[8px] ${statusStyle[post.status]}`}>{postStatusLabel[post.status]}</span><h2 id="content-detail-title" className="mt-3 text-lg font-semibold leading-snug text-white">{post.title}</h2></div><button onClick={onClose} aria-label="Fechar" className="rounded-lg p-2 text-[#808080] hover:bg-white/[0.05]"><X className="h-4 w-4" /></button></div>
    <div className="mt-5 grid grid-cols-2 gap-2"><Meta label="Publicação" value={post.scheduledAt ? new Date(post.scheduledAt).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' }) : 'Sem data'} /><Meta label="Formato" value={formatName(post.format)} /><Meta label="Responsável" value={post.responsibleName || post.author} /><Meta label="Campanha" value={campaignName || 'Sem campanha'} /></div>
    <section className="mt-6"><h3 className="text-[8px] uppercase tracking-[0.15em] text-[#808080]">Canais</h3><div className="mt-2 flex flex-wrap gap-1.5">{channels.map((platform) => <span key={platform} className="rounded-full border border-white/[0.06] px-2.5 py-1 text-[8px] text-[rgba(255,255,255,0.72)]">{formatPlatform(platform)}</span>)}</div></section>
    {post.copy && <section className="mt-6"><h3 className="text-[8px] uppercase tracking-[0.15em] text-[#808080]">Conteúdo</h3><p className="mt-2 whitespace-pre-wrap rounded-xl border border-white/[0.05] bg-black/15 p-4 text-[9px] leading-relaxed text-[rgba(255,255,255,0.72)]">{post.copy}</p></section>}
    {assetNames.length > 0 && <section className="mt-6"><h3 className="text-[8px] uppercase tracking-[0.15em] text-[#808080]">Materiais vinculados</h3><div className="mt-2 space-y-1.5">{assetNames.map((name) => <div key={name} className="flex items-center gap-2 rounded-lg border border-white/[0.05] px-3 py-2 text-[8px] text-[rgba(255,255,255,0.72)]"><FolderOpen className="h-3.5 w-3.5" />{name}</div>)}</div></section>}
    {post.publicationError && <div className="mt-5 rounded-xl border border-[#FF7F50]/15 bg-[#FF7F50]/[0.04] p-3 text-[8px] leading-relaxed text-[#FF7F50]"><strong className="block text-[9px]">Falha na publicação</strong><span className="mt-1 block">{post.publicationError}</span><button onClick={onFixConnection} className="mt-2 text-[#FF7F50] underline underline-offset-2">Corrigir conexão</button></div>}
    {canApprove && <div className="mt-6 grid grid-cols-2 gap-2"><button onClick={onRequestChanges} className="h-9 rounded-lg border border-white/[0.07] text-[9px] text-[rgba(255,255,255,0.72)]">Solicitar alterações</button><button onClick={onApprove} className="h-9 rounded-lg bg-[#FF7F50] text-[9px] font-semibold text-[#000000]">Aprovar conteúdo</button></div>}
    {canSchedule && <button type="button" disabled={scheduling} onClick={onSchedule} className="mt-5 h-9 w-full rounded-lg bg-[#FF7F50] text-[9px] font-semibold text-[#000000] disabled:opacity-50">{scheduling ? 'Confirmando agendamento…' : 'Confirmar agendamento'}</button>}
    {canEditSchedule && <section className="calendar-schedule-edit"><h3>Editar agendamento</h3><p>Altere a data e o horário antes do início da publicação.</p><div><label>Data<input type="date" value={date} onChange={event => setDate(event.target.value)} /></label><label>Horário<input type="time" value={time} onChange={event => setTime(event.target.value)} /></label></div><button type="button" disabled={scheduling || !date || !time} onClick={() => onReschedule(date, time)}>{scheduling ? 'Salvando…' : 'Salvar nova data'}</button></section>}
    {canCancelSchedule && <button type="button" disabled={scheduling} onClick={onCancelSchedule} className="mt-5 h-9 w-full rounded-lg border border-white/[0.08] text-[9px] text-[rgba(255,255,255,0.72)] disabled:opacity-50">{scheduling ? 'Cancelando agendamento…' : 'Cancelar agendamento'}</button>}
    {canRemoveSchedule && <button type="button" disabled={scheduling} onClick={onRemoveSchedule} className="mt-3 h-9 w-full rounded-lg border border-white/[0.08] text-[9px] text-[rgba(255,255,255,0.72)] disabled:opacity-50">Remover data e manter rascunho</button>}
    {post.externalPostId && <p className="mt-4 text-[8px] text-[#808080]">ID externo confirmado: {post.externalPostId}</p>}
    <section className="mt-7 border-t border-white/[0.06] pt-5"><div className="flex items-center gap-2"><History className="h-4 w-4 text-[#FF7F50]" /><h3 className="text-[9px] font-semibold uppercase tracking-[0.15em] text-[rgba(255,255,255,0.72)]">Histórico</h3></div>{history.length ? <div className="mt-4 space-y-3">{history.slice(0, 10).map((entry) => <div key={entry.id} className="relative border-l border-white/[0.08] pl-3"><span className="absolute -left-[3px] top-1 h-1.5 w-1.5 rounded-full bg-[#808080]" /><p className="text-[8px] text-[rgba(255,255,255,0.72)]">{entry.detail}</p><span className="mt-1 block text-[7px] text-[#808080]">{entry.actorName} · {new Date(entry.createdAt).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })}</span></div>)}</div> : <p className="mt-3 text-[8px] text-[#808080]">Nenhuma alteração registrada.</p>}</section>
  </aside></div>;
}

function Meta({ label, value }: { label: string; value: string }) { return <div className="rounded-lg border border-white/[0.05] bg-white/[0.012] p-3"><span className="text-[7px] text-[#808080]">{label}</span><strong className="mt-1 block truncate text-[8px] font-medium text-[rgba(255,255,255,0.72)]">{value}</strong></div>; }
