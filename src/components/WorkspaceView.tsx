import React from 'react';
import {
  ArrowLeft,
  ArrowRight,
  Building2,
  CalendarDays,
  Check,
  ChevronRight,
  Clock3,
  FileCheck2,
  FileText,
  Filter,
  FolderOpen,
  Image as ImageIcon,
  Plus,
  Search,
  ShieldCheck,
  Target,
  UserRound,
  Video,
  X,
} from 'lucide-react';
import type { ClientIntelligenceProfile, NavigationTab, Post } from '../types';
import { useGovernance } from '../context/GovernanceContext';
import { useOperations } from '../context/OperationsContext';
import { postStatusLabel } from '../utils/localization';
import { hasPermission } from '../security/accessControl';
import { CLIENT_OPERATION_REQUIRED, clientOperationLabels, hasClientOperation, type ClientOperationRecord } from '../clients/clientOperations';
import { useClientOperations } from '../clients/useClientOperations';
import { brandIntelligenceCompleteness } from '../operations/brandIntelligence';
import { klicPageScope, useKlicPageDetails } from '../klic/pageContext';
import './WorkspaceView.css';

type ClientSection = 'overview' | 'content' | 'brand' | 'calendar' | 'approvals' | 'strategy';
type ClientFilter = 'all' | NonNullable<ClientIntelligenceProfile['status']>;

const sectionOptions: Array<{ id: ClientSection; label: string }> = [
  { id: 'overview', label: 'Visão geral' },
  { id: 'content', label: 'Conteúdo' },
  { id: 'brand', label: 'Inteligência da Marca' },
  { id: 'calendar', label: 'Calendário' },
  { id: 'approvals', label: 'Aprovações' },
  { id: 'strategy', label: 'Perfil estratégico' },
];

const clientStatus = {
  active: { label: 'Ativo', className: 'is-active' },
  approval: { label: 'Em aprovação', className: 'is-approval' },
  paused: { label: 'Pausado', className: 'is-paused' },
} as const;

const approvalStageLabel = {
  draft: 'Rascunho', in_review: 'Em revisão', pending_approval: 'Aguardando aprovação', approved: 'Aprovado',
  changes_requested: 'Alterações solicitadas', rejected: 'Reprovado', published: 'Publicado',
} as const;

const productionStatuses = new Set(['draft', 'in_production', 'in_review', 'changes_requested']);
const approvalStatuses = new Set(['pending_approval', 'in_review', 'changes_requested']);

const initials = (name: string) => name.split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase();
const formatDate = (value?: string, options?: Intl.DateTimeFormatOptions) => value
  ? new Intl.DateTimeFormat('pt-BR', options || { day: '2-digit', month: 'short', year: 'numeric' }).format(new Date(value))
  : 'Sem registro';

function ClientAvatar({ client, size = 'medium' }: { client: ClientIntelligenceProfile; size?: 'small' | 'medium' | 'large' }) {
  return <span className={`cx-client-avatar is-${size}`}>
    {client.logoUrl ? <img src={client.logoUrl} alt={`Logo de ${client.name}`} /> : initials(client.name)}
  </span>;
}

export function WorkspaceView({ onNavigate }: { onNavigate: (tab: NavigationTab) => void }) {
  const {
    clients, activeClient, activeWorkspace, campaigns, posts, assets,
    createClient, setActiveClientId, updateClient, prepareStudioHandoff,
  } = useOperations();
  const { approvals, currentUser } = useGovernance();
  const operations = useClientOperations(activeWorkspace.id, currentUser?.id || '');
  const operationByClient = React.useMemo(() => new Map(operations.records.map(record => [record.id, record])), [operations.records]);
  const [screen, setScreen] = React.useState<'portfolio' | 'detail'>('portfolio');
  const [section, setSection] = React.useState<ClientSection>('overview');
  const [query, setQuery] = React.useState('');
  const [filter, setFilter] = React.useState<ClientFilter>('all');
  const [addOpen, setAddOpen] = React.useState(false);
  const [activationClient, setActivationClient] = React.useState<ClientIntelligenceProfile | null>(null);
  const [activationEmail, setActivationEmail] = React.useState('');
  const [activationBusy, setActivationBusy] = React.useState(false);
  const [activationError, setActivationError] = React.useState('');
  const [invitationUrl, setInvitationUrl] = React.useState('');
  const [editingProfile, setEditingProfile] = React.useState(false);
  const [notice, setNotice] = React.useState('');
  const [newClient, setNewClient] = React.useState({ name: '', segment: '', responsibleName: currentUser?.name || 'Equipe Clicko' });
  const [profileDraft, setProfileDraft] = React.useState<Partial<ClientIntelligenceProfile>>({});
  useKlicPageDetails('workspace', klicPageScope(activeWorkspace.id, activeClient?.id), {
    view: screen === 'detail' ? `Cliente · ${section}` : 'Clientes',
    filters: screen === 'portfolio' ? { status: filter, busca: query } : undefined,
    selected: screen === 'detail' && activeClient ? { kind: 'cliente', id: activeClient.id } : undefined,
  });

  React.useEffect(() => {
    if (!activeClient) return;
    setProfileDraft({
      segment: activeClient.segment,
      products: activeClient.products,
      audience: activeClient.audience,
      positioning: activeClient.positioning,
      toneOfVoice: activeClient.toneOfVoice,
      visualIdentity: activeClient.visualIdentity,
      differentiators: activeClient.differentiators,
      competitors: activeClient.competitors || '',
      keywords: activeClient.keywords || '',
      avoidTopics: activeClient.avoidTopics || '',
      notes: activeClient.notes || '',
      currentObjective: activeClient.currentObjective,
      featuredOffer: activeClient.featuredOffer,
      typography: activeClient.typography || '',
      visualReferences: activeClient.visualReferences || '',
    });
    setEditingProfile(false);
  }, [activeClient]);

  React.useEffect(() => {
    if (!notice) return;
    const timer = window.setTimeout(() => setNotice(''), 2400);
    return () => window.clearTimeout(timer);
  }, [notice]);

  const approvalByContent = React.useMemo(() => new Map(approvals.map((approval) => [approval.contentId, approval])), [approvals]);

  const portfolio = React.useMemo(() => clients.map((client, clientIndex) => {
    const scopedPosts = posts.filter((post) => post.clientId === client.id || (!post.clientId && clientIndex === 0));
    const production = scopedPosts.filter((post) => productionStatuses.has(post.status)).length;
    const pending = scopedPosts.filter((post) => approvalStatuses.has(post.status) || approvalByContent.has(post.id)).length;
    const upcoming = scopedPosts.filter((post) => post.status === 'scheduled' || Boolean(post.scheduledAt)).length;
    const activityDates = [client.lastActivityAt, client.updatedAt, ...scopedPosts.map((post) => post.createdAt)].filter(Boolean) as string[];
    const lastActivity = activityDates.sort((a, b) => +new Date(b) - +new Date(a))[0];
    return { client, production, pending, upcoming, lastActivity };
  }), [approvalByContent, clients, posts]);

  const filteredPortfolio = portfolio.filter(({ client }) => {
    const matchesQuery = `${client.name} ${client.segment} ${client.responsibleName || ''}`.toLowerCase().includes(query.trim().toLowerCase());
    return matchesQuery && (filter === 'all' || (client.status || 'active') === filter);
  });

  const activeClientIndex = activeClient ? clients.findIndex((client) => client.id === activeClient.id) : -1;
  const clientPosts = activeClient ? posts.filter((post) => post.clientId === activeClient.id || (!post.clientId && activeClientIndex === 0)) : [];
  const clientAssets = activeClient ? assets.filter((asset) => asset.clientId === activeClient.id || (!asset.clientId && activeClientIndex === 0)) : [];
  const clientApprovals = clientPosts.map((post) => ({ post, approval: approvalByContent.get(post.id) })).filter(({ post, approval }) => approval || approvalStatuses.has(post.status));
  const scheduledPosts = clientPosts.filter((post) => post.scheduledAt || post.status === 'scheduled').sort((a, b) => +(new Date(a.scheduledAt || a.createdAt)) - +(new Date(b.scheduledAt || b.createdAt)));
  const recentPosts = [...clientPosts].sort((a, b) => +new Date(b.createdAt) - +new Date(a.createdAt));
  const clientCampaigns = activeClient ? campaigns.filter((campaign) => campaign.clientId === activeClient.id || activeClient.activeCampaignIds.includes(campaign.id)) : [];

  const openClient = (client: ClientIntelligenceProfile) => {
    setActiveClientId(client.id);
    setSection('overview');
    setScreen('detail');
    if (currentUser && hasPermission(currentUser, 'clients.manage') && !operationByClient.has(client.id)) {
      void operations.mutate('/clients/register', { id: client.id, name: client.name }).catch(() => setNotice('Não foi possível sincronizar este cadastro com o servidor. Tente novamente antes de convidar ou ativar.'));
    }
  };

  const navigateWithContext = (tab: NavigationTab) => {
    if (!activeClient) return;
    setActiveClientId(activeClient.id);
    if (tab === 'create-image' || tab === 'create-video') {
      prepareStudioHandoff({
        source: 'client', clientId: activeClient.id, campaignId: clientCampaigns[0]?.id,
        objective: activeClient.currentObjective || 'Criar conteúdo alinhado ao perfil estratégico do cliente.',
        title: `Novo conteúdo — ${activeClient.name}`, angle: activeClient.positioning || activeClient.differentiators,
        hook: activeClient.featuredOffer ? `Por que ${activeClient.featuredOffer} importa agora` : `Uma ideia relevante para ${activeClient.audience}`,
        cta: 'Continuar a conversa', format: tab === 'create-video' ? 'reels' : 'carousel', funnelStage: 'Descoberta',
      });
    }
    onNavigate(tab);
  };

  const submitClient = (event: React.FormEvent) => {
    event.preventDefault();
    if (!newClient.name.trim() || !newClient.segment.trim()) return;
    const created = createClient({ name: newClient.name, segment: newClient.segment, responsibleName: newClient.responsibleName, currentObjective: 'Definir o primeiro objetivo estratégico.', status: 'active' });
    setAddOpen(false);
    setNewClient({ name: '', segment: '', responsibleName: currentUser?.name || 'Equipe Clicko' });
    setNotice('Cliente adicionado à carteira');
    openClient(created);
  };

  const ensureRegistered = async (client: ClientIntelligenceProfile) => {
    if (operationByClient.has(client.id)) return;
    await operations.mutate('/clients/register', { id: client.id, name: client.name });
  };

  const openActivation = (client: ClientIntelligenceProfile) => {
    setActivationClient(client); setActivationEmail(''); setActivationError(''); setInvitationUrl('');
  };

  const inviteClient = async (kind: 'portal' | 'independent') => {
    if (!activationClient) return;
    setActivationBusy(true); setActivationError('');
    try {
      await ensureRegistered(activationClient);
      const result = await operations.mutate<{ inviteUrl?: string; deliveryConfigured: boolean }>(`/clients/${encodeURIComponent(activationClient.id)}/invite`, { email: activationEmail, kind });
      setInvitationUrl(result.inviteUrl || '');
      setNotice(result.deliveryConfigured ? 'Convite enviado.' : 'Convite preparado. O envio por e-mail ainda não está configurado.');
    } catch (error) { setActivationError(error instanceof Error ? error.message : 'Não foi possível preparar o convite.'); }
    finally { setActivationBusy(false); }
  };

  const startManagedCheckout = async () => {
    if (!activationClient) return;
    setActivationBusy(true); setActivationError('');
    try {
      await ensureRegistered(activationClient);
      const result = await operations.mutate<{ checkoutUrl: string }>(`/clients/${encodeURIComponent(activationClient.id)}/managed-checkout`, {});
      window.location.assign(result.checkoutUrl);
    } catch (error) { setActivationError(error instanceof Error ? error.message : 'Não foi possível iniciar o pagamento.'); setActivationBusy(false); }
  };

  const saveProfile = () => {
    if (!activeClient) return;
    updateClient(activeClient.id, { ...profileDraft, lastActivityAt: new Date().toISOString() });
    setEditingProfile(false);
    setNotice('Perfil do cliente atualizado');
  };

  return <div className="cx-clients-shell">
    {screen === 'portfolio' || !activeClient ? <>
      <header className="cx-clients-page-header">
        <div><span className="cx-eyebrow"><Building2 />Carteira de clientes</span><h1>Clientes</h1><p>Cadastre clientes sem custo. Uma operação própria exige assinatura ou adicional gerenciado.</p></div>
        <button className="cx-client-button is-primary" onClick={() => setAddOpen(true)}><Plus />Adicionar cliente</button>
      </header>

      <section className="cx-client-toolbar" aria-label="Busca e filtros de clientes">
        <label><Search /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar por cliente, segmento ou responsável" /></label>
        <div><Filter /><select value={filter} onChange={(event) => setFilter(event.target.value as ClientFilter)} aria-label="Filtrar clientes por status"><option value="all">Todos os status</option><option value="active">Ativos</option><option value="approval">Em aprovação</option><option value="paused">Pausados</option></select></div>
        <span>{filteredPortfolio.length} {filteredPortfolio.length === 1 ? 'cliente' : 'clientes'}</span>
      </section>

      <section className="cx-client-list" aria-label="Carteira de clientes">
        <div className="cx-client-list-head"><span>Cliente</span><span>Produção</span><span>Aprovações</span><span>Publicações</span><span>Última atividade</span><span>Responsável</span><span /></div>
        {filteredPortfolio.map(({ client, production, pending, upcoming, lastActivity }) => {
          const status = clientStatus[client.status || 'active'];
          return <button className="cx-client-row" key={client.id} onClick={() => openClient(client)}>
            <span className="cx-client-identity"><ClientAvatar client={client} /><span><strong>{client.name}</strong><small>{client.segment}</small><em className={status.className}>{status.label}</em><em className="cx-operation-tag">{clientOperationLabels[operationByClient.get(client.id)?.operationState || 'registered']}</em></span></span>
            <span data-label="Em produção"><strong>{production}</strong><small>conteúdos</small></span>
            <span data-label="Aguardando aprovação"><strong>{pending}</strong><small>pendentes</small></span>
            <span data-label="Próximas publicações"><strong>{upcoming}</strong><small>programadas</small></span>
            <span data-label="Última atividade"><strong className="is-date">{formatDate(lastActivity, { day: '2-digit', month: 'short' })}</strong><small>atualização</small></span>
            <span data-label="Responsável" className="cx-client-owner"><UserRound /><span><strong>{client.responsibleName || 'Equipe Clicko'}</strong><small>responsável</small></span></span>
            <ChevronRight />
          </button>;
        })}
        {!filteredPortfolio.length && <div className="cx-client-no-results"><Search /><strong>Nenhum cliente encontrado</strong><p>Ajuste a busca ou o filtro para visualizar outras contas.</p></div>}
      </section>
    </> : <ClientDetail client={activeClient} operation={operationByClient.get(activeClient.id)} workspaceId={activeWorkspace.id} userId={currentUser?.id || ''} onRefreshOperations={operations.refresh} section={section} setSection={setSection} posts={clientPosts} assets={clientAssets} approvals={clientApprovals} scheduledPosts={scheduledPosts} recentPosts={recentPosts} campaigns={clientCampaigns} editingProfile={editingProfile} setEditingProfile={setEditingProfile} profileDraft={profileDraft} setProfileDraft={setProfileDraft} onSaveProfile={saveProfile} onBack={() => setScreen('portfolio')} onNavigate={navigateWithContext} onActivate={() => openActivation(activeClient)} />}

    {addOpen && <div className="cx-client-dialog-backdrop" role="presentation" onMouseDown={(event) => { if (event.currentTarget === event.target) setAddOpen(false); }}>
      <form className="cx-client-dialog" role="dialog" aria-modal="true" aria-labelledby="add-client-title" onSubmit={submitClient}>
        <header><div><span className="cx-eyebrow">Nova conta</span><h2 id="add-client-title">Adicionar cliente</h2><p>Comece com as informações essenciais. O perfil pode ser completado depois.</p></div><button type="button" onClick={() => setAddOpen(false)} aria-label="Fechar"><X /></button></header>
        <label>Nome do cliente<input autoFocus value={newClient.name} onChange={(event) => setNewClient((current) => ({ ...current, name: event.target.value }))} placeholder="Ex.: Clínica Aurora" required /></label>
        <label>Segmento<input value={newClient.segment} onChange={(event) => setNewClient((current) => ({ ...current, segment: event.target.value }))} placeholder="Ex.: Saúde e bem-estar" required /></label>
        <label>Responsável<input value={newClient.responsibleName} onChange={(event) => setNewClient((current) => ({ ...current, responsibleName: event.target.value }))} /></label>
        <footer><button type="button" className="cx-client-button" onClick={() => setAddOpen(false)}>Cancelar</button><button className="cx-client-button is-primary" type="submit"><Plus />Adicionar cliente</button></footer>
      </form>
    </div>}
    {activationClient && <div className="cx-client-dialog-backdrop" role="presentation" onMouseDown={(event) => { if (event.currentTarget === event.target) setActivationClient(null); }}>
      <section className="cx-client-dialog cx-activation-dialog" role="dialog" aria-modal="true" aria-labelledby="cx-activation-title">
        <header><div><span className="cx-eyebrow">Licença por operação</span><h2 id="cx-activation-title">Ativar operação na Clicko</h2><p>{activationClient.name} já pode permanecer na carteira sem custo. Escolha como abrir uma operação separada.</p></div><button type="button" onClick={() => setActivationClient(null)} aria-label="Fechar"><X /></button></header>
        <div className="cx-activation-options"><article><strong>O cliente assina diretamente</strong><p>Prepare um convite para criar uma conta própria e contratar um plano. A operação só será liberada após assinatura ativa.</p><label>E-mail do cliente<input type="email" value={activationEmail} onChange={event => setActivationEmail(event.target.value)} placeholder="cliente@empresa.com" /></label><button type="button" className="cx-client-button" disabled={activationBusy || !activationEmail.trim()} onClick={() => void inviteClient('independent')}>Preparar convite de assinatura <ArrowRight /></button></article><article><strong>Eu gerencio e pago por ele</strong><p>Inicie a contratação de uma operação gerenciada. O cliente não recebe uma conta gratuita nem assume a cobrança.</p><button type="button" className="cx-client-button is-primary" disabled={activationBusy} onClick={() => void startManagedCheckout()}>Continuar para pagamento <ArrowRight /></button></article></div>
        <div className="cx-portal-invite"><strong>Acesso limitado para colaborar</strong><p>Convidar para o portal não ativa uma operação nem libera custos, integrações ou automações.</p><button type="button" className="cx-client-button" disabled={activationBusy || !activationEmail.trim()} onClick={() => void inviteClient('portal')}>Preparar convite limitado</button></div>
        {invitationUrl && <div className="cx-invitation-link"><span>Envio automático indisponível. Compartilhe o link de cadastro com o cliente:</span><input readOnly aria-label="Link do convite" value={invitationUrl} onFocus={event => event.currentTarget.select()} /></div>}
        {activationError && <p className="cx-activation-error" role="alert">{activationError}</p>}
        <p className="cx-activation-disclaimer">Clientes apenas cadastrados não são cobrados. O adicional gerenciado depende de preço configurado no provedor e pagamento confirmado. Condições de plano Parceiro/Gestor, transferência de cobrança e indicação dependem de contratação específica.</p>
      </section>
    </div>}
    {notice && <div className="cx-client-toast" role="status"><Check />{notice}</div>}
  </div>;
}

type ClientDetailProps = {
  client: ClientIntelligenceProfile;
  operation?: ClientOperationRecord;
  workspaceId: string;
  userId: string;
  onRefreshOperations: () => Promise<void>;
  section: ClientSection;
  setSection: (section: ClientSection) => void;
  posts: Post[];
  assets: ReturnType<typeof useOperations>['assets'];
  approvals: Array<{ post: Post; approval: ReturnType<typeof useGovernance>['approvals'][number] | undefined }>;
  scheduledPosts: Post[];
  recentPosts: Post[];
  campaigns: ReturnType<typeof useOperations>['campaigns'];
  editingProfile: boolean;
  setEditingProfile: (editing: boolean) => void;
  profileDraft: Partial<ClientIntelligenceProfile>;
  setProfileDraft: React.Dispatch<React.SetStateAction<Partial<ClientIntelligenceProfile>>>;
  onSaveProfile: () => void;
  onBack: () => void;
  onNavigate: (tab: NavigationTab) => void;
  onActivate: () => void;
};

function ClientDetail({ client, operation, workspaceId, userId, onRefreshOperations, section, setSection, posts, assets, approvals, scheduledPosts, recentPosts, campaigns, editingProfile, setEditingProfile, profileDraft, setProfileDraft, onSaveProfile, onBack, onNavigate, onActivate }: ClientDetailProps) {
  const status = clientStatus[client.status || 'active'];
  const productionCount = posts.filter((post) => productionStatuses.has(post.status)).length;
  const brandProgress = brandIntelligenceCompleteness(client);

  return <>
    <header className="cx-client-detail-header">
      <button className="cx-client-back" onClick={onBack}><ArrowLeft />Clientes</button>
      <div className="cx-client-detail-title"><ClientAvatar client={client} size="large" /><div><span className={`cx-client-status ${status.className}`}>{status.label}</span><span className="cx-operation-tag">{clientOperationLabels[operation?.operationState || 'registered']}</span><h1>{client.name}</h1><p>{client.segment} · Responsável: {client.responsibleName || 'Equipe Clicko'}</p></div></div>
      <div className="cx-client-header-actions"><button className="cx-client-button is-primary" onClick={() => onNavigate('create-copy')}><Plus />Criar conteúdo</button></div>
    </header>

    <section className="cx-operation-banner" aria-label="Situação da operação do cliente"><div><span className="cx-eyebrow">Operação do cliente</span><strong>{hasClientOperation(operation) ? `${clientOperationLabels[operation!.operationState]} ativa` : operation?.billingStatus === 'checkout_pending' ? 'Pagamento em confirmação' : operation?.operationSignals?.length ? 'Demanda por operação própria identificada' : clientOperationLabels[operation?.operationState || 'registered']}</strong><p>{hasClientOperation(operation) ? 'Esta operação possui liberação confirmada pelo servidor.' : CLIENT_OPERATION_REQUIRED}</p>{!hasClientOperation(operation) && Boolean(operation?.operationSignals?.length) && <small>Sinais: {operation?.operationSignals?.map(signal => ({ costs: 'custos', reports: 'relatórios', automations: 'automações', integrations: 'integrações', team: 'equipe', settings: 'configurações' })[signal.kind]).join(', ')}.</small>}</div>{!hasClientOperation(operation) && <button className="cx-client-button is-primary" onClick={onActivate}>Ativar operação na Clicko <ArrowRight /></button>}</section>

    <nav className="cx-client-tabs" aria-label="Seções do cliente">{sectionOptions.map((option) => <button key={option.id} className={section === option.id ? 'is-active' : ''} onClick={() => setSection(option.id)}>{option.label}</button>)}</nav>

    {section === 'overview' && <section className="cx-client-section">
      <div className="cx-client-metrics">
        <Metric icon={FileText} label="Conteúdo" value={`${posts.length}`} detail={`${productionCount} em produção`} />
        <Metric icon={FileCheck2} label="Aprovações" value={`${approvals.length}`} detail="aguardando decisão" />
        <Metric icon={CalendarDays} label="Calendário" value={`${scheduledPosts.length}`} detail="próximas publicações" />
        <Metric icon={Clock3} label="Atividade" value={formatDate(client.lastActivityAt || client.updatedAt, { day: '2-digit', month: 'short' })} detail="última atualização" />
      </div>
      <div className="cx-client-overview-grid">
        <article className="cx-client-panel"><PanelHeading eyebrow="Atividade" title="Movimentações recentes" /><div className="cx-client-activity-list">{recentPosts.slice(0, 5).map((post) => <div key={post.id}><span><FileText /></span><div><strong>{post.title}</strong><p>{postStatusLabel[post.status]} · {post.author}</p></div><time>{formatDate(post.createdAt, { day: '2-digit', month: 'short' })}</time></div>)}{!recentPosts.length && <EmptyState icon={Clock3} title="Sem atividades recentes" text="As próximas ações desta conta aparecerão aqui." />}</div></article>
        <article className="cx-client-panel"><PanelHeading eyebrow="Calendário" title="Próximas publicações" action="Abrir calendário" onAction={() => onNavigate('calendar')} /><div className="cx-client-compact-list">{scheduledPosts.slice(0, 4).map((post) => <button key={post.id} onClick={() => onNavigate('calendar')}><span className="cx-client-date"><strong>{formatDate(post.scheduledAt || post.createdAt, { day: '2-digit' })}</strong><small>{formatDate(post.scheduledAt || post.createdAt, { month: 'short' })}</small></span><span><strong>{post.title}</strong><small>{post.platform} · {postStatusLabel[post.status]}</small></span><ChevronRight /></button>)}{!scheduledPosts.length && <EmptyState icon={CalendarDays} title="Nada programado" text="Planeje a próxima publicação deste cliente." />}</div></article>
      </div>
      <div className="cx-client-overview-grid is-secondary">
        <article className="cx-client-panel"><PanelHeading eyebrow="Direcionamento" title="Próximas ações" /><div className="cx-client-actions-list">{client.recommendedActions.map((action, index) => <button key={action} onClick={() => onNavigate(index === 0 ? 'strategy' : 'create-copy')}><span>0{index + 1}</span><strong>{action}</strong><ArrowRight /></button>)}</div></article>
        <article className="cx-client-panel"><PanelHeading eyebrow="Governança" title="Acesso por cliente" /><p className="cx-client-panel-copy">Estrutura preparada para evoluir permissões específicas desta conta sem aumentar a complexidade atual.</p><div className="cx-client-access">{(['Visualizar', 'Criar', 'Editar', 'Aprovar', 'Publicar'] as const).map((label, index) => <span className={(Object.values(client.access || { view: true, create: true, edit: true, approve: true, publish: false })[index]) ? 'is-enabled' : ''} key={label}><ShieldCheck />{label}</span>)}</div></article>
      </div>
      {operation && <ClientPortalTools clientId={client.id} operation={operation} workspaceId={workspaceId} userId={userId} onRefresh={onRefreshOperations} />}
    </section>}

    {section === 'content' && <section className="cx-client-section cx-client-content-grid">
      <article className="cx-client-panel"><PanelHeading eyebrow={`${posts.length} itens`} title="Conteúdos do cliente" action="Criar conteúdo" onAction={() => onNavigate('create-copy')} /><div className="cx-client-content-list">{recentPosts.map((post) => <div key={post.id}><span className="cx-client-file-icon">{post.format.includes('video') || post.format === 'reels' ? <Video /> : <ImageIcon />}</span><span><strong>{post.title}</strong><small>{post.format} · {post.platform} · {postStatusLabel[post.status]}</small></span><time>{formatDate(post.createdAt, { day: '2-digit', month: 'short' })}</time></div>)}{!posts.length && <EmptyState icon={FolderOpen} title="Nenhum conteúdo associado" text="Os conteúdos criados neste contexto serão vinculados automaticamente ao cliente." />}</div></article>
      <aside className="cx-client-panel"><PanelHeading eyebrow={`${assets.length} arquivos`} title="Materiais vinculados" action="Abrir biblioteca" onAction={() => onNavigate('library')} /><div className="cx-client-asset-list">{assets.slice(0, 8).map((asset) => <div key={asset.id}><FileText /><span><strong>{asset.title}</strong><small>{asset.type} · {asset.tags.join(', ') || 'sem etiquetas'}</small></span></div>)}{!assets.length && <EmptyState icon={FolderOpen} title="Nenhum material" text="Arquivos associados ao cliente aparecerão aqui." />}</div><div className="cx-client-create-split"><button onClick={() => onNavigate('create-image')}><ImageIcon />Criar imagem</button><button onClick={() => onNavigate('create-video')}><Video />Criar vídeo</button></div></aside>
    </section>}

    {section === 'brand' && <section className="cx-client-section"><article className="cx-client-panel"><PanelHeading eyebrow={`${brandProgress.percent}% do contexto essencial`} title="Inteligência da Marca" action={editingProfile ? 'Salvar alterações' : 'Editar inteligência'} onAction={editingProfile ? onSaveProfile : () => setEditingProfile(true)} /><p className="cx-client-panel-copy">Esta é a fonte de contexto de {client.name} para a KLIC, estratégia, criação e planejamento. Informações ausentes não são inventadas.</p><div className="cx-client-brand-progress" role="progressbar" aria-label="Completude da Inteligência da Marca" aria-valuemin={0} aria-valuemax={100} aria-valuenow={brandProgress.percent}><span style={{ width: `${brandProgress.percent}%` }} /></div><div className="cx-client-brand-grid">
      <div className="cx-client-brand-logo"><ClientAvatar client={client} size="large" /><div><strong>Logo principal</strong><p>{client.logoUrl ? 'Arquivo configurado' : 'Avatar gerado pelas iniciais da marca'}</p></div></div>
      <BrandField label="Cores" editing={editingProfile} value={(client.brandColors || ['#000000', '#FFFFFF', '#FF7F50']).join(', ')} onChange={(value) => setProfileDraft((current) => ({ ...current, brandColors: value.split(',').map((color) => color.trim()).filter(Boolean) }))}><div className="cx-client-swatches">{(client.brandColors || ['#000000', '#FFFFFF', '#FF7F50']).map((color) => <span key={color} style={{ background: color }} title={color} />)}</div></BrandField>
      <BrandField label="Tipografia" editing={editingProfile} value={String(profileDraft.typography || '')} onChange={(value) => setProfileDraft((current) => ({ ...current, typography: value }))} />
      <BrandField label="Identidade visual" editing={editingProfile} value={String(profileDraft.visualIdentity || '')} onChange={(value) => setProfileDraft((current) => ({ ...current, visualIdentity: value }))} />
      <BrandField label="Tom de voz" editing={editingProfile} value={String(profileDraft.toneOfVoice || '')} onChange={(value) => setProfileDraft((current) => ({ ...current, toneOfVoice: value }))} />
      <BrandField label="Referências visuais" editing={editingProfile} value={String(profileDraft.visualReferences || '')} onChange={(value) => setProfileDraft((current) => ({ ...current, visualReferences: value }))} />
      <BrandField label="Posicionamento" editing={editingProfile} value={String(profileDraft.positioning || '')} onChange={(value) => setProfileDraft((current) => ({ ...current, positioning: value }))} />
      <BrandField label="Concorrentes e referências" editing={editingProfile} value={String(profileDraft.competitors || '')} onChange={(value) => setProfileDraft((current) => ({ ...current, competitors: value }))} />
      <BrandField label="Termos preferidos" editing={editingProfile} value={String(profileDraft.keywords || '')} onChange={(value) => setProfileDraft((current) => ({ ...current, keywords: value }))} />
      <BrandField label="Assuntos e expressões a evitar" editing={editingProfile} value={String(profileDraft.avoidTopics || '')} onChange={(value) => setProfileDraft((current) => ({ ...current, avoidTopics: value }))} />
    </div>{editingProfile && <div className="cx-client-form-actions"><button className="cx-client-button" onClick={() => setEditingProfile(false)}>Cancelar</button><button className="cx-client-button is-primary" onClick={onSaveProfile}><Check />Salvar marca</button></div>}</article></section>}

    {section === 'calendar' && <section className="cx-client-section"><article className="cx-client-panel"><PanelHeading eyebrow="Agenda contextual" title={`Calendário de ${client.name}`} action="Abrir calendário completo" onAction={() => onNavigate('calendar')} /><div className="cx-client-timeline">{scheduledPosts.map((post) => <div key={post.id}><span className="cx-client-date"><strong>{formatDate(post.scheduledAt || post.createdAt, { day: '2-digit' })}</strong><small>{formatDate(post.scheduledAt || post.createdAt, { month: 'short' })}</small></span><span><strong>{post.title}</strong><small>{post.platform} · {post.format}</small></span><em>{postStatusLabel[post.status]}</em></div>)}{!scheduledPosts.length && <EmptyState icon={CalendarDays} title="Calendário livre" text="Ainda não existem publicações programadas para este cliente." />}</div></article></section>}

    {section === 'approvals' && <section className="cx-client-section"><article className="cx-client-panel"><PanelHeading eyebrow={`${approvals.length} pendências`} title="Aprovações do cliente" action="Abrir aprovações" onAction={() => onNavigate('approvals')} /><div className="cx-client-approval-list">{approvals.map(({ post, approval }) => <div key={post.id}><span className="cx-client-file-icon"><FileCheck2 /></span><span><strong>{post.title}</strong><small>{approval ? approvalStageLabel[approval.stage] : postStatusLabel[post.status]} · {post.platform}</small>{approval?.comments.at(-1)?.message && <p>“{approval.comments.at(-1)?.message}”</p>}</span><button onClick={() => onNavigate('approvals')}>Revisar <ChevronRight /></button></div>)}{!approvals.length && <EmptyState icon={FileCheck2} title="Nenhuma aprovação pendente" text="Conteúdos enviados para revisão aparecerão aqui." />}</div></article></section>}

    {section === 'strategy' && <section className="cx-client-section"><article className="cx-client-panel"><PanelHeading eyebrow="Contexto da KLIC" title="Perfil estratégico" action={editingProfile ? 'Salvar alterações' : 'Editar perfil'} onAction={editingProfile ? onSaveProfile : () => setEditingProfile(true)} /><p className="cx-client-panel-copy">Essas informações orientam a KLIC, a criação e o planejamento sempre que este cliente estiver selecionado.</p><div className="cx-client-strategy-form">{([
      ['segment', 'Segmento'], ['audience', 'Público-alvo'], ['currentObjective', 'Objetivos'], ['products', 'Produtos e serviços'], ['differentiators', 'Diferenciais'], ['positioning', 'Posicionamento'], ['toneOfVoice', 'Tom de comunicação'], ['competitors', 'Concorrentes'], ['keywords', 'Palavras-chave'], ['avoidTopics', 'Assuntos que devem ser evitados'], ['notes', 'Observações'],
    ] as Array<[keyof ClientIntelligenceProfile, string]>).map(([key, label]) => <label key={key} className={key === 'notes' || key === 'products' ? 'is-wide' : ''}><span>{label}</span>{editingProfile ? <textarea rows={key === 'notes' || key === 'products' ? 3 : 2} value={String(profileDraft[key] || '')} onChange={(event) => setProfileDraft((current) => ({ ...current, [key]: event.target.value }))} /> : <p>{String(profileDraft[key] || 'Não informado')}</p>}</label>)}</div>{editingProfile && <div className="cx-client-form-actions"><button className="cx-client-button" onClick={() => setEditingProfile(false)}>Cancelar</button><button className="cx-client-button is-primary" onClick={onSaveProfile}><Check />Salvar perfil</button></div>}<div className="cx-client-campaigns"><PanelHeading eyebrow={`${campaigns.length} campanhas`} title="Estratégias relacionadas" action="Construir campanha" onAction={() => onNavigate('strategy')} />{campaigns.map((campaign) => <button key={campaign.id} onClick={() => onNavigate('strategy')}><Target /><span><strong>{campaign.name}</strong><small>{campaign.objective}</small></span><ChevronRight /></button>)}</div></article></section>}
  </>;
}

function Metric({ icon: Icon, label, value, detail }: { icon: React.ComponentType<{ className?: string }>; label: string; value: string; detail: string }) {
  return <article><span><Icon /></span><div><small>{label}</small><strong>{value}</strong><p>{detail}</p></div></article>;
}

function PanelHeading({ eyebrow, title, action, onAction }: { eyebrow: string; title: string; action?: string; onAction?: () => void }) {
  return <header className="cx-client-panel-heading"><div><span>{eyebrow}</span><h2>{title}</h2></div>{action && <button onClick={onAction}>{action}<ArrowRight /></button>}</header>;
}

function EmptyState({ icon: Icon, title, text }: { icon: React.ComponentType<{ className?: string }>; title: string; text: string }) {
  return <div className="cx-client-inline-empty"><Icon /><strong>{title}</strong><p>{text}</p></div>;
}

function BrandField({ label, editing, value, onChange, children }: { label: string; editing: boolean; value: string; onChange: (value: string) => void; children?: React.ReactNode }) {
  return <label className="cx-client-brand-field"><span>{label}</span>{editing ? <textarea rows={3} value={value} onChange={(event) => onChange(event.target.value)} /> : children || <p>{value || 'Não informado'}</p>}</label>;
}

function ClientPortalTools({ clientId, operation, workspaceId, userId, onRefresh }: { clientId: string; operation: ClientOperationRecord; workspaceId: string; userId: string; onRefresh: () => Promise<void> }) {
  const [summary, setSummary] = React.useState(operation.sharedSummary || '');
  const [title, setTitle] = React.useState('');
  const [detail, setDetail] = React.useState('');
  const [error, setError] = React.useState('');
  const [busy, setBusy] = React.useState(false);
  React.useEffect(() => setSummary(operation.sharedSummary || ''), [operation.sharedSummary]);
  const headers = { 'Content-Type': 'application/json', 'x-workspace-id': workspaceId, 'x-user-id': userId };
  const save = async (path: string, method: 'POST' | 'PATCH', body: object) => {
    setBusy(true); setError('');
    try {
      const response = await fetch(`/api/governance/clients/${encodeURIComponent(clientId)}${path}`, { method, headers, body: JSON.stringify(body) });
      if (!response.ok) { const payload = await response.json().catch(() => ({})) as { error?: string }; throw new Error(payload.error || 'Não foi possível salvar.'); }
      await onRefresh();
      if (path === '/portal-request') { setTitle(''); setDetail(''); }
    } catch (failure) { setError(failure instanceof Error ? failure.message : 'Não foi possível salvar.'); }
    finally { setBusy(false); }
  };
  const download = async (documentId: string) => {
    setError('');
    try {
      const response = await fetch(`/api/governance/clients/${encodeURIComponent(clientId)}/portal-documents/${encodeURIComponent(documentId)}`, { headers });
      if (!response.ok) throw new Error('Não foi possível baixar o documento.');
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a'); anchor.href = url; anchor.download = operation.portalDocuments?.find(item => item.id === documentId)?.name || 'documento'; anchor.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (failure) { setError(failure instanceof Error ? failure.message : 'Falha no download.'); }
  };
  return <article className="cx-client-panel cx-client-portal-tools"><PanelHeading eyebrow="Colaboração limitada" title="Portal do cliente" /><p className="cx-client-panel-copy">Compartilhe apenas o necessário. O convidado pode comentar, aprovar solicitações e enviar documentos — sem acessar a operação interna.</p><div className="cx-portal-tools-grid"><div><label>Informações compartilhadas<textarea maxLength={2000} rows={3} value={summary} onChange={event => setSummary(event.target.value)} placeholder="Resumo visível no portal" /></label><button className="cx-client-button" disabled={busy || summary === (operation.sharedSummary || '')} onClick={() => void save('/shared-summary', 'PATCH', { summary })}>Salvar informações</button></div><div><label>Nova solicitação<input maxLength={120} value={title} onChange={event => setTitle(event.target.value)} placeholder="Ex.: Aprovar documento" /></label><label>Descrição<textarea maxLength={2000} rows={2} value={detail} onChange={event => setDetail(event.target.value)} placeholder="O que precisa ser aprovado?" /></label><button className="cx-client-button" disabled={busy || !title.trim()} onClick={() => void save('/portal-request', 'POST', { title, detail })}>Criar solicitação</button></div></div><div className="cx-portal-tools-activity"><div><strong>Solicitações</strong>{operation.portalRequests?.map(item => <p key={item.id}>{item.title} · {item.status === 'approved' ? 'Aprovada' : 'Pendente'}</p>)}{!operation.portalRequests?.length && <p>Nenhuma solicitação.</p>}</div><div><strong>Comentários</strong>{operation.portalComments?.map(item => <p key={item.id}>{item.message}</p>)}{!operation.portalComments?.length && <p>Nenhum comentário.</p>}</div><div><strong>Documentos recebidos</strong>{operation.portalDocuments?.map(item => <button key={item.id} onClick={() => void download(item.id)}>{item.name} <ArrowRight /></button>)}{!operation.portalDocuments?.length && <p>Nenhum documento.</p>}</div></div>{error && <p className="cx-activation-error" role="alert">{error}</p>}</article>;
}
