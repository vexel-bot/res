import React from 'react';
import { klicPageScope, useKlicPageDetails } from '../klic/pageContext';
import {
  Check,
  CircleAlert,
  Clock3,
  Link2,
  Linkedin,
  Plus,
  RefreshCw,
  Settings2,
  ShieldCheck,
  Unplug,
  X,
} from 'lucide-react';
import { siFacebook, siInstagram, siPinterest, siThreads, siTiktok, siX, siYoutube } from 'simple-icons';
import { useGovernance } from '../context/GovernanceContext';
import { useOperations } from '../context/OperationsContext';
import { hasPermission } from '../security/accessControl';
import type { ConnectedAccount, ConnectedResource, SocialPlatform } from '../types';
import { connectedAccountsFromServer } from '../operations/socialConnections';
import { ClickoLoader } from './ClickoLoader';

type VisiblePlatform = Extract<SocialPlatform, 'instagram' | 'facebook' | 'tiktok' | 'youtube' | 'linkedin' | 'threads' | 'pinterest' | 'x'>;
type BusyState = 'connecting' | 'syncing' | 'testing';
type SyncPreference = NonNullable<ConnectedAccount['syncPreferences']>[number];
type ProviderState = { id: VisiblePlatform; name: string; configured: boolean; status: 'ready' | 'configuration_required'; missingConfiguration: string[] };
type ServerConnection = {
  id: string;
  clientId?: string;
  provider: VisiblePlatform;
  providerAccountId: string;
  username?: string;
  displayName: string;
  avatarUrl?: string;
  tokenExpiresAt?: string;
  tokenExpiring?: boolean;
  accountType?: string;
  createdAt?: string;
  scopes: string[];
  status: 'connected' | 'expired' | 'permission_insufficient' | 'authorization_revoked' | 'error';
  capabilities: NonNullable<ConnectedAccount['capabilities']>;
  lastSyncedAt?: string;
  lastError?: string;
};
type PendingOAuthAccount = {
  providerAccountId: string;
  displayName: string;
  username?: string;
  avatarUrl?: string;
  accountType?: string;
};
type PendingOAuthSelection = { token: string; provider: VisiblePlatform; accounts: PendingOAuthAccount[] };

type PlatformDefinition = {
  id: VisiblePlatform;
  name: string;
  icon?: { path: string };
  iconComponent?: React.ComponentType<{ className?: string }>;
};

const socialPlatforms: PlatformDefinition[] = [
  { id: 'instagram', name: 'Instagram', icon: siInstagram },
  { id: 'facebook', name: 'Facebook', icon: siFacebook },
  { id: 'tiktok', name: 'TikTok', icon: siTiktok },
  { id: 'youtube', name: 'YouTube', icon: siYoutube },
  { id: 'linkedin', name: 'LinkedIn', iconComponent: Linkedin },
  { id: 'threads', name: 'Threads', icon: siThreads },
  { id: 'pinterest', name: 'Pinterest', icon: siPinterest },
  { id: 'x', name: 'X', icon: siX },
];

const syncOptions: Array<{ id: SyncPreference; label: string; description: string }> = [
  { id: 'profile', label: 'Perfil e canais', description: 'Identidade, páginas e canais selecionados.' },
  { id: 'publishing', label: 'Publicação', description: 'Envio de conteúdos autorizados pela plataforma.' },
  { id: 'analytics', label: 'Métricas', description: 'Alcance, desempenho e sinais para o Analytics.' },
];

const platformLabel = (platform: SocialPlatform) => socialPlatforms.find((item) => item.id === platform)?.name || platform;

function SocialIcon({ definition }: { definition: PlatformDefinition }) {
  if (definition.iconComponent) {
    const Icon = definition.iconComponent;
    return <Icon className="h-5 w-5" />;
  }
  return <svg aria-hidden="true" viewBox="0 0 24 24" className="h-5 w-5 fill-current"><path d={definition.icon?.path} /></svg>;
}

function statusPresentation(account?: ConnectedAccount, busy?: BusyState, providerState?: ProviderState) {
  const status = busy || account?.connectionStatus || 'not_configured';
  if (status === 'connecting') return { label: 'Conectando', className: 'bg-[#FF7F50]/[0.08] text-[#FF7F50]', pulse: true };
  if (status === 'syncing') return { label: 'Sincronizando', className: 'bg-[#FF7F50]/[0.08] text-[#FF7F50]', pulse: true };
  if (status === 'testing') return { label: 'Testando conexão', className: 'bg-[#FF7F50]/[0.08] text-[#FF7F50]', pulse: true };
  if (status === 'synced') return { label: 'Sincronizada', className: 'bg-[#FF7F50]/[0.08] text-[#FF7F50]', pulse: false };
  if (status === 'sync_error') return { label: 'Erro na sincronização', className: 'bg-[#FF7F50]/[0.08] text-[#FF7F50]', pulse: false };
  if (status === 'error') return { label: 'Erro na conexão', className: 'bg-[#FF7F50]/[0.08] text-[#FF7F50]', pulse: false };
  if (status === 'permission_insufficient') return { label: 'Permissão insuficiente', className: 'bg-[#F28500]/[0.08] text-[#F28500]', pulse: false };
  if (status === 'authorization_revoked') return { label: 'Autorização revogada', className: 'bg-[#F28500]/[0.08] text-[#F28500]', pulse: false };
  if (status === 'expired') return { label: 'Reconexão necessária', className: 'bg-[#F28500]/[0.08] text-[#F28500]', pulse: false };
  if (account?.tokenExpiring) return { label: 'Token expirando', className: 'bg-[#F28500]/[0.08] text-[#F28500]', pulse: false };
  if (providerState && !providerState.configured) return { label: 'Configuração necessária', className: 'bg-white/[0.045] text-[#808080]', pulse: false };
  if (account?.connected && status === 'connected') return { label: 'Conectada', className: 'bg-[#FF7F50]/[0.08] text-[#FF7F50]', pulse: false };
  return { label: 'Não conectada', className: 'bg-white/[0.045] text-[#808080]', pulse: false };
}

function hasExistingConnection(account?: ConnectedAccount) {
  return Boolean(account && (account.connected || ['connected', 'synced', 'syncing', 'sync_error', 'expired', 'permission_insufficient', 'authorization_revoked', 'error'].includes(account.connectionStatus || '')));
}

function formatLastSync(value?: string) {
  if (!value || value === 'Nunca') return 'Ainda não sincronizada';
  if (value === 'Agora') return 'Sincronizada agora';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return `Última sincronização: ${value}`;
  return `Última sincronização: ${new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' }).format(date)}`;
}

function supportsPreference(account: ConnectedAccount, preference: SyncPreference) {
  if (!account.capabilities) return true;
  if (preference === 'profile') return account.capabilities.canReadProfile;
  if (preference === 'analytics') return account.capabilities.canReadAnalytics;
  return account.capabilities.canPublishText || account.capabilities.canPublishImage || account.capabilities.canPublishCarousel || account.capabilities.canPublishVideo || account.capabilities.canPublishShortVideo || account.capabilities.canPublishStory || account.capabilities.canPublishDocument;
}

function selectedPreferencesFor(account: ConnectedAccount) {
  const selected = account.syncPreferences || ['profile', 'analytics'];
  return selected.filter(preference => supportsPreference(account, preference));
}

function enabledCapabilityLabels(account: ConnectedAccount) {
  if (!account.capabilities) return [];
  const labels: Array<[keyof NonNullable<ConnectedAccount['capabilities']>, string]> = [
    ['canReadProfile', 'Perfil'], ['canReadPosts', 'Conteúdos'], ['canReadAnalytics', 'Analytics'],
    ['canPublishText', 'Texto'], ['canPublishImage', 'Imagem'], ['canPublishCarousel', 'Carrossel'],
    ['canPublishVideo', 'Vídeo'], ['canPublishShortVideo', 'Vídeo curto'], ['canPublishStory', 'Story'],
    ['canPublishDocument', 'Documento'], ['canReadComments', 'Comentários'], ['canReplyComments', 'Responder comentários'],
  ];
  return labels.filter(([key]) => account.capabilities?.[key]).map(([, label]) => label);
}

export function ConnectedAccountsView() {
  const { environmentMode, currentUser } = useGovernance();
  const canManageConnections = hasPermission(currentUser, 'connections.manage');
  const {
    activeWorkspace,
    activeClient,
    clients,
    connectedAccounts: accounts,
    addConnectedAccount,
    updateConnectedAccount,
    setSocialAccounts,
  } = useOperations();
  const [feedback, setFeedback] = React.useState<{ tone: 'neutral' | 'error'; message: string }>();
  const [busyPlatforms, setBusyPlatforms] = React.useState<Partial<Record<VisiblePlatform, BusyState>>>({});
  const [providerStates, setProviderStates] = React.useState<Partial<Record<VisiblePlatform, ProviderState>>>({});
  const [managingId, setManagingId] = React.useState<string>();
  const [selectedClientId, setSelectedClientId] = React.useState<string>('');
  const [selectedResources, setSelectedResources] = React.useState<string[]>([]);
  const [selectedPreferences, setSelectedPreferences] = React.useState<SyncPreference[]>([]);
  const [pendingSelection, setPendingSelection] = React.useState<PendingOAuthSelection>();
  const [selectingAccounts, setSelectingAccounts] = React.useState(false);
  const [selectedPendingIds, setSelectedPendingIds] = React.useState<string[]>([]);
  const [connectionPickerOpen, setConnectionPickerOpen] = React.useState(false);
  useKlicPageDetails('connected-accounts', klicPageScope(activeWorkspace.id, activeClient?.id), {
    view: connectionPickerOpen ? 'Conectar conta' : managingId ? 'Gerenciar conta' : 'Contas conectadas',
    selected: managingId && accounts.some(account => account.id === managingId) ? { kind: 'conta', id: managingId } : undefined,
  });
  const scopeRef = React.useRef(activeWorkspace.id);
  const connectionPickerTriggerRef = React.useRef<HTMLButtonElement>(null);
  const connectionPickerCloseRef = React.useRef<HTMLButtonElement>(null);
  scopeRef.current = activeWorkspace.id;
  React.useEffect(() => { scopeRef.current = activeWorkspace.id; setManagingId(undefined); setPendingSelection(undefined); setConnectionPickerOpen(false); setFeedback(undefined); setBusyPlatforms({}); return () => { scopeRef.current = ''; }; }, [activeWorkspace.id]);

  const closeConnectionPicker = React.useCallback(() => {
    setConnectionPickerOpen(false);
    window.setTimeout(() => connectionPickerTriggerRef.current?.focus(), 0);
  }, []);

  React.useEffect(() => {
    if (!connectionPickerOpen) return;
    const focusFrame = window.requestAnimationFrame(() => connectionPickerCloseRef.current?.focus());
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') closeConnectionPicker();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.cancelAnimationFrame(focusFrame);
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [closeConnectionPicker, connectionPickerOpen]);

  const managingAccount = accounts.find((account) => account.id === managingId);

  const integrationHeaders = React.useMemo(() => ({
    'Content-Type': 'application/json',
  }), []);

  const accountFor = React.useCallback((platform: VisiblePlatform) => accounts.find((account) => account.platform === platform), [accounts]);
  const ensureAccount = React.useCallback((platform: VisiblePlatform) => accountFor(platform) || addConnectedAccount(platform), [accountFor, addConnectedAccount]);

  const refreshConnections = React.useCallback(async () => {
    const requestedWorkspace = activeWorkspace.id;
    const response = await fetch('/api/integrations/connections', { headers: integrationHeaders });
    const data = await response.json().catch(() => ({})) as { providers?: ProviderState[]; connections?: ServerConnection[]; error?: string };
    if (scopeRef.current !== requestedWorkspace) return;
    if (!response.ok) throw new Error(data.error || 'Não foi possível verificar as conexões sociais.');
    const nextProviders = Object.fromEntries((data.providers || []).map(provider => [provider.id, provider])) as Partial<Record<VisiblePlatform, ProviderState>>;
    setProviderStates(nextProviders);
    setSocialAccounts(data.connections || []);
    return data.connections || [];
  }, [activeWorkspace.id, integrationHeaders, setSocialAccounts]);

  React.useEffect(() => {
    let active = true;
    refreshConnections().catch(() => { if (active) setFeedback({ tone: 'error', message: 'Não foi possível verificar as conexões agora.' }); });
    return () => { active = false; };
  }, [refreshConnections]);

  const loadResources = React.useCallback(async (account: ConnectedAccount) => {
    const response = await fetch(`/api/integrations/${account.platform}/resources`, { headers: integrationHeaders });
    const data = await response.json().catch(() => ({}));
    if (scopeRef.current !== activeWorkspace.id) return [];
    if (!response.ok) throw new Error(data.error || data.message || 'Não foi possível carregar os perfis disponíveis.');
    const resources = Array.isArray(data.resources) ? data.resources as ConnectedResource[] : [];
    updateConnectedAccount(account.id, {
      availableResources: resources,
      selectedResourceIds: account.selectedResourceIds || [],
      permissions: Array.isArray(data.permissions) ? data.permissions : [],
      lastError: undefined,
    });
    return resources;
  }, [integrationHeaders, updateConnectedAccount]);

  React.useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const integration = params.get('integration') as VisiblePlatform | null;
    const status = params.get('status');
    if (!integration || !socialPlatforms.some((platform) => platform.id === integration)) return;
    window.history.replaceState({}, '', '/connected-accounts');
    const account = ensureAccount(integration);
    if (status === 'selection_required') {
      const token = params.get('selection') || '';
      fetch(`/api/integrations/oauth/selections/${encodeURIComponent(token)}`, { headers: integrationHeaders })
        .then(async response => {
          const data = await response.json().catch(() => ({}));
          if (!response.ok || !Array.isArray(data.accounts)) throw new Error(data.error || 'A seleção de contas expirou. Inicie a conexão novamente.');
          const available = data.accounts as PendingOAuthAccount[];
          setPendingSelection({ token, provider: integration, accounts: available });
          setSelectedPendingIds(available.map(item => item.providerAccountId));
        })
        .catch(error => setFeedback({ tone: 'error', message: error instanceof Error ? error.message : 'Não foi possível carregar as contas disponíveis.' }));
      return;
    }
    if (status !== 'connected') {
      const reason = params.get('reason');
      const message = reason === 'permission_insufficient' ? 'A plataforma não disponibilizou uma conta compatível com as permissões concedidas.'
        : reason === 'configuration_required' ? 'A integração precisa ser configurada pelo administrador.'
          : reason === 'authorization_revoked' ? 'A autorização expirou ou foi revogada. Conecte novamente.'
            : reason === 'authorization_denied' ? 'A autorização foi cancelada na plataforma.'
              : 'A plataforma não concluiu a autorização. Tente novamente.';
      updateConnectedAccount(account.id, { connected: false, connectionStatus: 'authorization_required', lastError: message });
      setFeedback({ tone: 'error', message });
      return;
    }
    refreshConnections().then(connections => {
      const target = connectedAccountsFromServer(activeWorkspace.id, connections.filter(item => item.provider === integration), accounts);
      const connected = target.find(item => item.connected);
      if (!connected) throw new Error('A conta autorizada ainda não apareceu neste ambiente.');
      setManagingId(connected.id);
      setSelectedResources(connected.selectedResourceIds || []);
      setSelectedPreferences(selectedPreferencesFor(connected));
      return loadResources(connected);
    }).catch((error) => {
      setFeedback({ tone: 'error', message: error instanceof Error ? error.message : 'Não foi possível carregar os perfis disponíveis.' });
    });
  }, [ensureAccount, integrationHeaders, loadResources, refreshConnections, updateConnectedAccount, activeWorkspace.id, accounts]);

  const confirmPendingSelection = async () => {
    if (!pendingSelection || !selectedPendingIds.length || selectingAccounts) return;
    const requestedWorkspace = activeWorkspace.id;
    setSelectingAccounts(true);
    try {
      const response = await fetch(`/api/integrations/oauth/selections/${encodeURIComponent(pendingSelection.token)}`, {
        method: 'POST', headers: integrationHeaders, body: JSON.stringify({ providerAccountIds: selectedPendingIds }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.error || 'Não foi possível concluir a seleção.');
      if (scopeRef.current !== requestedWorkspace) return;
      const platform = pendingSelection.provider;
      setPendingSelection(undefined);
      setSelectedPendingIds([]);
      const connections = await refreshConnections();
      const account = connectedAccountsFromServer(requestedWorkspace, connections.filter(item => item.provider === platform), accounts)[0];
      if (!account) throw new Error('A rede não confirmou a conta selecionada.');
      setManagingId(account.id);
      await loadResources(account);
      setFeedback({ tone: 'neutral', message: `${selectedPendingIds.length} conta(s) conectada(s) com sucesso.` });
    } catch (error) {
      if (scopeRef.current === requestedWorkspace) setFeedback({ tone: 'error', message: error instanceof Error ? error.message : 'Não foi possível concluir a seleção.' });
    } finally {
      setSelectingAccounts(false);
    }
  };

  const connect = async (platform: VisiblePlatform) => {
    const account = ensureAccount(platform);
    setBusyPlatforms((current) => ({ ...current, [platform]: 'connecting' }));
    setFeedback(undefined);
    try {
      const response = await fetch(`/api/integrations/${platform}/authorize`, {
        method: 'POST',
        headers: integrationHeaders,
        body: JSON.stringify({ returnTo: '/connected-accounts' }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok || !data.authorizationUrl) throw new Error(data.error || data.message || 'Não foi possível iniciar a autorização.');
      if (scopeRef.current !== activeWorkspace.id) return;
      updateConnectedAccount(account.id, { connectionStatus: 'connecting', lastError: undefined });
      setConnectionPickerOpen(false);
      window.location.assign(data.authorizationUrl);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Não foi possível iniciar a autorização.';
      if (scopeRef.current !== activeWorkspace.id) return;
      updateConnectedAccount(account.id, { connected: false, connectionStatus: 'authorization_required', lastError: message });
      setFeedback({ tone: 'error', message });
      setBusyPlatforms((current) => ({ ...current, [platform]: undefined }));
    }
  };

  const openManagement = async (account: ConnectedAccount) => {
    setManagingId(account.id);
    setSelectedClientId(account.clientId || '');
    setSelectedResources(account.selectedResourceIds || []);
    setSelectedPreferences(selectedPreferencesFor(account));
    if (!account.availableResources?.length) {
      try { await loadResources(account); } catch (error) {
        setFeedback({ tone: 'error', message: error instanceof Error ? error.message : 'Não foi possível atualizar os perfis.' });
      }
    }
  };

  const saveManagement = async () => {
    if (!managingAccount) return;
    const requestedWorkspace = activeWorkspace.id;
    try {
      if (environmentMode === 'company' && selectedClientId) {
        const client = clients.find(item => item.id === selectedClientId);
        if (!client) throw new Error('Selecione um cliente deste ambiente.');
        const registration = await fetch('/api/governance/clients/register', { method: 'POST', headers: integrationHeaders, body: JSON.stringify({ id: client.id, name: client.name }) });
        if (!registration.ok) throw new Error((await registration.json().catch(() => ({}))).error || 'Não foi possível vincular o cliente.');
      }
      const response = await fetch(`/api/integrations/connections/${encodeURIComponent(managingAccount.id)}/client`, {
        method: 'PATCH', headers: integrationHeaders,
        body: JSON.stringify({ clientId: environmentMode === 'company' ? selectedClientId || null : null }),
      });
      if (!response.ok) throw new Error((await response.json().catch(() => ({}))).error || 'Não foi possível salvar o vínculo da conta.');
      if (scopeRef.current !== requestedWorkspace) return;
      await refreshConnections();
    } catch (error) {
      if (scopeRef.current === requestedWorkspace) setFeedback({ tone: 'error', message: error instanceof Error ? error.message : 'Não foi possível salvar as preferências.' });
      return;
    }
    updateConnectedAccount(managingAccount.id, {
      clientId: environmentMode === 'company' ? selectedClientId || undefined : undefined,
      selectedResourceIds: selectedResources,
      syncPreferences: selectedPreferences,
      connectionStatus: 'connected',
      lastError: undefined,
    });
    setManagingId(undefined);
    setFeedback({ tone: 'neutral', message: `Preferências do ${platformLabel(managingAccount.platform)} salvas somente em ${activeWorkspace.name}.` });
  };

  const syncNow = async (account: ConnectedAccount) => {
    if (account.availableResources?.length && !account.selectedResourceIds?.length) {
      setFeedback({ tone: 'error', message: `Escolha ao menos um perfil do ${platformLabel(account.platform)} antes de sincronizar.` });
      openManagement(account);
      return;
    }
    setBusyPlatforms((current) => ({ ...current, [account.platform as VisiblePlatform]: 'syncing' }));
    updateConnectedAccount(account.id, { connectionStatus: 'syncing', lastError: undefined });
    try {
      const response = await fetch(`/api/integrations/${account.platform}/sync`, {
        method: 'POST',
        headers: integrationHeaders,
        body: JSON.stringify({ connectionId: account.id, selectedResourceIds: account.selectedResourceIds || [], syncPreferences: account.syncPreferences || [] }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.error || data.message || 'A sincronização não pôde ser concluída.');
      if (scopeRef.current !== activeWorkspace.id) return;
      updateConnectedAccount(account.id, { connectionStatus: 'synced', lastSync: data.syncedAt || new Date().toISOString(), lastError: undefined, ...(data.analytics && data.analytics.dataStatus !== 'unavailable' ? { analytics: data.analytics } : {}) });
      setFeedback({ tone: 'neutral', message: data.analyticsMessage || `${platformLabel(account.platform)} sincronizado com sucesso.` });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'A sincronização não pôde ser concluída.';
      if (scopeRef.current !== activeWorkspace.id) return;
      updateConnectedAccount(account.id, { connectionStatus: 'sync_error', lastError: message });
      setFeedback({ tone: 'error', message });
    } finally {
      if (scopeRef.current === activeWorkspace.id) setBusyPlatforms((current) => ({ ...current, [account.platform as VisiblePlatform]: undefined }));
    }
  };

  const testConnection = async (account: ConnectedAccount) => {
    setBusyPlatforms(current => ({ ...current, [account.platform as VisiblePlatform]: 'testing' }));
    setFeedback(undefined);
    try {
      const response = await fetch(`/api/integrations/${account.platform}/test`, { method: 'POST', headers: integrationHeaders, body: '{}' });
      const data = await response.json().catch(() => ({}));
      if (!response.ok || data.healthy !== true) throw new Error(data.error || 'A conexão precisa ser renovada.');
      if (scopeRef.current !== activeWorkspace.id) return;
      await refreshConnections();
      setFeedback({ tone: 'neutral', message: `Conexão com ${platformLabel(account.platform)} validada com sucesso.` });
    } catch (error) {
      if (scopeRef.current !== activeWorkspace.id) return;
      await refreshConnections().catch(() => undefined);
      setFeedback({ tone: 'error', message: error instanceof Error ? error.message : 'Não foi possível validar a conexão.' });
    } finally {
      if (scopeRef.current === activeWorkspace.id) setBusyPlatforms(current => ({ ...current, [account.platform as VisiblePlatform]: undefined }));
    }
  };

  const disconnect = async (account: ConnectedAccount) => {
    try {
      const response = await fetch(`/api/integrations/${account.platform}/disconnect`, { method: 'POST', headers: integrationHeaders, body: JSON.stringify({ connectionId: account.id }) });
      if (scopeRef.current !== activeWorkspace.id) return;
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.error || data.message || 'Não foi possível revogar a conexão. Tente novamente.');
      }
      await refreshConnections();
      setManagingId(undefined);
      setFeedback({ tone: 'neutral', message: `${platformLabel(account.platform)} desconectado de ${activeWorkspace.name}.` });
    } catch (error) {
      if (scopeRef.current !== activeWorkspace.id) return;
      setFeedback({ tone: 'error', message: error instanceof Error ? error.message : 'Falha ao desconectar. A conexão foi preservada.' });
    }
  };

  const connectedAccounts = accounts.filter((account) =>
    socialPlatforms.some(({ id }) => id === account.platform)
    && hasExistingConnection(account),
  );
  const connectedCount = connectedAccounts.length;

  return <div className="mx-auto w-full max-w-[1360px] space-y-7 p-5 sm:p-6 2xl:p-10">
    <header className="flex flex-col gap-5 border-b border-white/[0.06] pb-7 sm:flex-row sm:items-end sm:justify-between">
      <div className="max-w-2xl">
        <p className="text-[10px] font-medium uppercase tracking-[0.24em] text-[#FF7F50]">Integrações</p>
        <h1 className="mt-2 text-2xl font-semibold tracking-[-0.02em] text-white">Conexões</h1>
        <p className="mt-2 text-sm leading-6 text-[#808080]">Gerencie as contas que já fazem parte deste ambiente.</p>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        {canManageConnections ? <button ref={connectionPickerTriggerRef} type="button" onClick={() => setConnectionPickerOpen(true)} className="inline-flex h-10 items-center gap-2 rounded-lg bg-[#FF7F50] px-4 text-[10px] font-semibold text-black transition hover:bg-[#F28500] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#FF7F50]/50">
          <Plus className="h-4 w-4" />Conectar conta
        </button> : <span className="rounded-lg border border-white/[0.07] px-3 py-2 text-[9px] text-[#808080]">Somente leitura</span>}
      </div>
    </header>

    {feedback && <div role="status" className={`flex items-center justify-between gap-4 rounded-xl border px-4 py-3 text-[10px] leading-relaxed ${feedback.tone === 'error' ? 'border-[#F28500]/15 bg-[#F28500]/[0.045] text-[#F28500]' : 'border-white/[0.06] bg-white/[0.025] text-[rgba(255,255,255,0.72)]'}`}>
      <span className="flex items-center gap-2">{feedback.tone === 'error' ? <CircleAlert className="h-4 w-4 shrink-0 text-[#F28500]" /> : <Check className="h-4 w-4 shrink-0 text-[#FF7F50]" />}{feedback.message}</span>
      <button type="button" onClick={() => setFeedback(undefined)} className="shrink-0 rounded-md p-1 text-current opacity-60 transition hover:bg-white/[0.05] hover:opacity-100" aria-label="Fechar aviso"><X className="h-3.5 w-3.5" /></button>
    </div>}

    <section aria-labelledby="social-connections-title" className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h2 id="social-connections-title" className="text-[10px] font-semibold uppercase tracking-[0.18em] text-[rgba(255,255,255,0.72)]">Contas conectadas</h2>
          <p className="mt-1 text-[10px] text-[#808080]">{connectedCount} {connectedCount === 1 ? 'conta conectada' : 'contas conectadas'} neste ambiente</p>
        </div>
      </div>

      {connectedAccounts.length ? <div className="space-y-3">
        {connectedAccounts.map((account) => {
          const definition = socialPlatforms.find(({ id }) => id === account.platform)!;
          const platform = definition.id;
          const ready = Boolean(account.connected && ['connected', 'synced', 'syncing'].includes(account.connectionStatus || ''));
          const status = statusPresentation(account, busyPlatforms[platform], providerStates[platform]);
          const connectedProfiles = account.providerConnectionIds?.length || 1;
          return <article key={account.id} className="group rounded-xl border border-white/[0.065] bg-[rgba(128,128,128,0.14)] px-4 py-4 transition-colors hover:border-white/[0.11] sm:px-5">
            <div className="flex flex-col gap-4 xl:flex-row xl:items-center">
              <div className="flex min-w-0 flex-1 items-center gap-3">
                {account.avatar ? <img src={account.avatar} alt="" className="h-11 w-11 shrink-0 rounded-lg border border-white/[0.06] object-cover" /> : <span className="grid h-11 w-11 shrink-0 place-items-center rounded-lg border border-white/[0.06] bg-black/20 text-[rgba(255,255,255,0.88)]"><SocialIcon definition={definition} /></span>}
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="truncate text-[11px] font-semibold text-white">{account.name || definition.name}</h3>
                    <span className={`inline-flex items-center gap-1.5 rounded-full px-2 py-1 text-[8px] font-medium ${status.className}`}>{status.pulse ? <ClickoLoader size="tiny" label={status.label} /> : <span className="h-1.5 w-1.5 rounded-full bg-current" />}{status.label}</span>
                  </div>
                  <p className="mt-1 truncate text-[9px] text-[rgba(255,255,255,0.68)]">{definition.name}{account.handle ? ` · ${account.handle}` : ''}{connectedProfiles > 1 ? ` · ${connectedProfiles} perfis` : ''}</p>
                  <p className="mt-1 text-[9px] text-[#808080]">{ready ? formatLastSync(account.lastSync) : account.lastError || 'Esta conexão precisa de atenção.'}</p>
                </div>
              </div>
              {canManageConnections && <div className="flex flex-wrap items-center gap-1.5 border-t border-white/[0.055] pt-3 xl:border-l xl:border-t-0 xl:pl-4 xl:pt-0">
                {!ready ? <button type="button" disabled={Boolean(busyPlatforms[platform]) || providerStates[platform]?.configured === false} onClick={() => connect(platform)} className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-[#FF7F50] px-3 text-[9px] font-semibold text-black transition hover:bg-[#F28500] disabled:cursor-not-allowed disabled:opacity-45">
                  {busyPlatforms[platform] === 'connecting' ? <ClickoLoader size="tiny" tone="light" label="Reconectando conta" /> : <Link2 className="h-3.5 w-3.5" />}Reconectar
                </button> : <>
                  <button type="button" disabled={Boolean(busyPlatforms[platform])} onClick={() => syncNow(account)} className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-white/[0.075] px-2.5 text-[9px] font-medium text-[rgba(255,255,255,0.72)] transition hover:border-white/[0.14] hover:text-white disabled:cursor-wait disabled:opacity-60">
                    {busyPlatforms[platform] === 'syncing' ? <ClickoLoader size="tiny" label="Sincronizando conta" /> : <RefreshCw className="h-3.5 w-3.5" />}Sincronizar
                  </button>
                  <button type="button" disabled={Boolean(busyPlatforms[platform])} onClick={() => testConnection(account)} className="inline-flex h-8 items-center gap-1.5 rounded-lg px-2.5 text-[9px] text-[#808080] transition hover:bg-white/[0.04] hover:text-white disabled:cursor-wait disabled:opacity-60">{busyPlatforms[platform] === 'testing' ? <ClickoLoader size="tiny" label="Testando conexão" /> : <ShieldCheck className="h-3.5 w-3.5" />}Testar</button>
                  <button type="button" onClick={() => openManagement(account)} className="inline-flex h-8 items-center gap-1.5 rounded-lg px-2.5 text-[9px] text-[#808080] transition hover:bg-white/[0.04] hover:text-white"><Settings2 className="h-3.5 w-3.5" />Detalhes</button>
                </>}
                <button type="button" onClick={() => disconnect(account)} className="ml-auto inline-flex h-8 items-center gap-1.5 rounded-lg px-2 text-[9px] text-[#808080] transition hover:bg-red-500/[0.08] hover:text-red-400"><Unplug className="h-3.5 w-3.5" />Desconectar</button>
              </div>}
            </div>
          </article>;
        })}
      </div> : <div className="grid min-h-[280px] place-items-center rounded-2xl border border-dashed border-white/[0.08] bg-white/[0.015] px-6 py-12 text-center">
        <div className="max-w-sm">
          <span className="mx-auto grid h-11 w-11 place-items-center rounded-xl border border-white/[0.07] bg-white/[0.025] text-[#FF7F50]"><Link2 className="h-5 w-5" /></span>
          <h3 className="mt-4 text-sm font-semibold text-white">Nenhuma conta conectada ainda</h3>
          <p className="mt-2 text-[10px] leading-5 text-[#808080]">Conecte uma rede social para disponibilizar seus canais e recursos em toda a Clicko.</p>
          {canManageConnections && <button type="button" onClick={() => setConnectionPickerOpen(true)} className="mt-5 inline-flex h-10 items-center gap-2 rounded-lg bg-[#FF7F50] px-4 text-[10px] font-semibold text-black transition hover:bg-[#F28500]"><Plus className="h-4 w-4" />Conectar conta</button>}
        </div>
      </div>}
    </section>

    <footer className="flex items-start gap-3 rounded-xl border border-[#FF7F50]/[0.12] bg-[#FF7F50]/[0.035] px-4 py-4 sm:px-5">
      <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-[#FF7F50]" />
      <div>
        <strong className="block text-[10px] font-semibold text-[rgba(255,255,255,0.82)]">Seus canais, sob seu controle.</strong>
        <p className="mt-1 text-[9px] leading-5 text-[#808080]">Cada conexão pertence apenas a este ambiente. Você autoriza o acesso diretamente na rede social; a Clicko nunca pede sua senha.</p>
      </div>
    </footer>

    {canManageConnections && connectionPickerOpen && <div className="fixed inset-0 z-[100] grid place-items-center bg-black/75 p-4 backdrop-blur-sm" role="dialog" aria-modal="true" aria-labelledby="connect-account-title" aria-describedby="connect-account-description">
      <button type="button" className="absolute inset-0" onClick={closeConnectionPicker} aria-label="Fechar seletor de plataformas" />
      <section className="relative max-h-[calc(100dvh-32px)] w-full max-w-[620px] overflow-y-auto rounded-2xl border border-white/[0.08] bg-[#111111] p-5 shadow-2xl sm:p-6">
        <div className="flex items-start justify-between gap-4 border-b border-white/[0.06] pb-5">
          <div>
            <p className="text-[9px] font-medium uppercase tracking-[0.2em] text-[#FF7F50]">Nova conexão</p>
            <h2 id="connect-account-title" className="mt-1.5 text-lg font-semibold tracking-[-0.01em] text-white">Conectar uma conta</h2>
            <p id="connect-account-description" className="mt-1 text-[10px] leading-relaxed text-[#808080]">Escolha a rede social que deseja conectar à Clicko.</p>
          </div>
          <button ref={connectionPickerCloseRef} type="button" onClick={closeConnectionPicker} className="rounded-lg p-2 text-[#808080] transition hover:bg-white/[0.05] hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#FF7F50]/40" aria-label="Fechar"><X className="h-4 w-4" /></button>
        </div>

        <div className="mt-5 grid gap-2 sm:grid-cols-2">
          {socialPlatforms.map((definition) => {
            const account = accountFor(definition.id);
            const providerState = providerStates[definition.id];
            const busy = busyPlatforms[definition.id];
            const connected = hasExistingConnection(account);
            const unavailable = providerState?.configured === false;
            return <button key={definition.id} type="button" disabled={Boolean(busy) || unavailable} onClick={() => connect(definition.id)} className="group flex min-h-[70px] items-center gap-3 rounded-xl border border-white/[0.065] bg-white/[0.018] p-3 text-left transition hover:border-white/[0.13] hover:bg-white/[0.035] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#FF7F50]/35 disabled:cursor-not-allowed disabled:opacity-45">
              <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg border border-white/[0.06] bg-black/20 text-[rgba(255,255,255,0.82)] transition group-hover:text-white"><SocialIcon definition={definition} /></span>
              <span className="min-w-0 flex-1">
                <strong className="block text-[10px] font-semibold text-white">{definition.name}</strong>
                <span className={`mt-1 block text-[9px] ${unavailable ? 'text-[#808080]' : connected ? 'text-[#FF7F50]' : 'text-[#808080]'}`}>
                  {busy === 'connecting' ? 'Abrindo autorização…' : unavailable ? 'Configuração necessária' : connected ? 'Conectada · adicionar outra' : 'Disponível para conectar'}
                </span>
              </span>
              {busy === 'connecting' ? <ClickoLoader size="tiny" label="Conectando conta" /> : connected ? <Check className="h-4 w-4 text-[#FF7F50]" /> : <Plus className="h-4 w-4 text-[#808080] transition group-hover:text-[#FF7F50]" />}
            </button>;
          })}
        </div>
        <p className="mt-4 text-[9px] leading-relaxed text-[#808080]">A autorização acontece no site oficial de cada plataforma. A Clicko não solicita suas senhas.</p>
      </section>
    </div>}

    {canManageConnections && managingAccount && <div className="fixed inset-0 z-[100] flex justify-end bg-black/70 backdrop-blur-sm" role="dialog" aria-modal="true" aria-labelledby="manage-integration-title">
      <button type="button" className="absolute inset-0" onClick={() => setManagingId(undefined)} aria-label="Fechar gerenciamento" />
      <aside className="relative h-full w-full max-w-[460px] overflow-y-auto border-l border-white/[0.07] bg-[rgba(128,128,128,0.14)] p-5 shadow-2xl sm:p-6">
        <div className="flex items-start justify-between gap-4 border-b border-white/[0.06] pb-5">
          <div><p className="text-[9px] uppercase tracking-[0.18em] text-[#FF7F50]">Gerenciar conexão</p><h2 id="manage-integration-title" className="mt-1.5 text-lg font-semibold text-white">{platformLabel(managingAccount.platform)}</h2><p className="mt-1 text-[10px] text-[#808080]">Escolha exatamente o que será usado neste ambiente.</p></div>
          <button type="button" onClick={() => setManagingId(undefined)} className="rounded-lg p-2 text-[#808080] transition hover:bg-white/[0.05] hover:text-white" aria-label="Fechar"><X className="h-4 w-4" /></button>
        </div>

        <section className="mt-6">
          <h3 className="text-[9px] font-semibold uppercase tracking-[0.16em] text-[rgba(255,255,255,0.72)]">Perfis, páginas e canais</h3>
          {managingAccount.availableResources?.length ? <div className="mt-3 space-y-2">{managingAccount.availableResources.map((resource) => {
            const selected = selectedResources.includes(resource.id);
            return <button key={resource.id} type="button" onClick={() => setSelectedResources((current) => selected ? current.filter((id) => id !== resource.id) : [...current, resource.id])} className={`flex w-full items-center gap-3 rounded-xl border p-3 text-left transition ${selected ? 'border-[#FF7F50]/25 bg-[#FF7F50]/[0.045]' : 'border-white/[0.06] bg-white/[0.018] hover:border-white/[0.11]'}`}>
              {resource.avatar ? <img src={resource.avatar} alt="" className="h-9 w-9 rounded-lg object-cover" /> : <span className="grid h-9 w-9 place-items-center rounded-lg bg-black/20 text-[9px] font-semibold uppercase text-[#808080]">{resource.type.slice(0, 2)}</span>}
              <span className="min-w-0 flex-1"><strong className="block truncate text-[10px] font-medium text-white">{resource.name}</strong><span className="mt-0.5 block truncate text-[9px] text-[#808080]">{resource.handle || ({ profile: 'Perfil', page: 'Página', channel: 'Canal', board: 'Pasta', organization: 'Organização' }[resource.type])}</span></span>
              <span className={`grid h-4 w-4 place-items-center rounded border ${selected ? 'border-[#FF7F50] bg-[#FF7F50] text-[#000000]' : 'border-white/15'}`}>{selected && <Check className="h-3 w-3" />}</span>
            </button>;
          })}</div> : <div className="mt-3 rounded-xl border border-dashed border-white/[0.07] p-4 text-[9px] leading-relaxed text-[#808080]">Nenhum perfil foi disponibilizado pelo provedor. Verifique as permissões concedidas ou autorize novamente.</div>}
        </section>

        <section className="mt-7 border-t border-white/[0.06] pt-6">
          <h3 className="text-[9px] font-semibold uppercase tracking-[0.16em] text-[rgba(255,255,255,0.72)]">Detalhes da conta</h3>
          <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-3 rounded-xl border border-white/[0.055] bg-white/[0.015] p-3 text-[9px]">
            <div><dt className="text-[#808080]">Identidade</dt><dd className="mt-1 truncate text-[rgba(255,255,255,0.82)]">{managingAccount.handle || managingAccount.name}</dd></div>
            <div><dt className="text-[#808080]">Tipo</dt><dd className="mt-1 capitalize text-[rgba(255,255,255,0.82)]">{managingAccount.accountType || 'perfil'}</dd></div>
            <div><dt className="text-[#808080]">Conectada em</dt><dd className="mt-1 text-[rgba(255,255,255,0.82)]">{managingAccount.connectedAt ? new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short' }).format(new Date(managingAccount.connectedAt)) : 'Não informado'}</dd></div>
            <div><dt className="text-[#808080]">Permissões</dt><dd className="mt-1 text-[rgba(255,255,255,0.82)]">{managingAccount.permissions?.length || 0} concedidas</dd></div>
          </dl>
          <div className="mt-3 flex flex-wrap gap-1.5">
            {enabledCapabilityLabels(managingAccount).length ? enabledCapabilityLabels(managingAccount).map(label => <span key={label} className="rounded-full border border-white/[0.06] bg-white/[0.02] px-2 py-1 text-[8px] text-[#808080]">{label}</span>) : <span className="text-[9px] text-[#808080]">Nenhuma capacidade adicional foi liberada por esta autorização.</span>}
          </div>
        </section>

        {environmentMode === 'company' && <section className="mt-7">
          <label htmlFor="social-client" className="text-[9px] font-semibold uppercase tracking-[0.16em] text-[rgba(255,255,255,0.72)]">Cliente vinculado</label>
          <select id="social-client" value={selectedClientId} onChange={event => setSelectedClientId(event.target.value)} className="mt-3 h-10 w-full rounded-lg border border-white/[0.075] bg-[#111111] px-3 text-[10px] text-white">
            <option value="">Sem cliente</option>
            {clients.map(client => <option key={client.id} value={client.id}>{client.name}</option>)}
          </select>
          <p className="mt-2 text-[9px] text-[#808080]">Publicações deste cliente poderão usar apenas as contas vinculadas a ele.</p>
        </section>}

        <section className="mt-7">
          <h3 className="text-[9px] font-semibold uppercase tracking-[0.16em] text-[rgba(255,255,255,0.72)]">Dados sincronizados</h3>
          <div className="mt-3 space-y-2">{syncOptions.map((option) => {
            const selected = selectedPreferences.includes(option.id);
            const supported = supportsPreference(managingAccount, option.id);
            return <button key={option.id} type="button" disabled={!supported} onClick={() => setSelectedPreferences((current) => selected ? current.filter((id) => id !== option.id) : [...current, option.id])} className="flex w-full items-center gap-3 rounded-xl border border-white/[0.055] bg-white/[0.015] p-3 text-left transition hover:border-white/[0.1] disabled:cursor-not-allowed disabled:opacity-45">
              <span className={`relative h-5 w-9 shrink-0 rounded-full transition ${selected ? 'bg-[#FF7F50]' : 'bg-white/[0.09]'}`}><span className={`absolute top-0.5 h-4 w-4 rounded-full bg-white transition ${selected ? 'left-[18px]' : 'left-0.5'}`} /></span>
              <span><strong className="block text-[10px] font-medium text-[rgba(255,255,255,0.88)]">{option.label}{!supported ? ' · Indisponível nesta autorização' : ''}</strong><span className="mt-0.5 block text-[8px] leading-relaxed text-[#808080]">{option.description}</span></span>
            </button>;
          })}</div>
        </section>

        <div className="mt-7 flex items-center gap-2 rounded-xl bg-white/[0.025] p-3 text-[9px] text-[#808080]"><Clock3 className="h-4 w-4 shrink-0 text-[#FF7F50]" />{formatLastSync(managingAccount.lastSync)}</div>
        <button type="button" onClick={saveManagement} className="mt-5 h-10 w-full rounded-lg bg-[#FF7F50] text-[10px] font-semibold text-[#000000] transition hover:bg-[#F28500]">Salvar preferências</button>
      </aside>
    </div>}

    {canManageConnections && pendingSelection && <div className="fixed inset-0 z-[110] grid place-items-center bg-black/75 p-4 backdrop-blur-sm" role="dialog" aria-modal="true" aria-labelledby="select-social-accounts-title">
      <section className="w-full max-w-[520px] rounded-2xl border border-white/[0.08] bg-[#111111] p-5 shadow-2xl sm:p-6">
        <div className="flex items-start justify-between gap-4 border-b border-white/[0.06] pb-4">
          <div><p className="text-[9px] uppercase tracking-[0.18em] text-[#FF7F50]">Conexão autorizada</p><h2 id="select-social-accounts-title" className="mt-1.5 text-lg font-semibold text-white">Escolha as contas</h2><p className="mt-1 text-[10px] leading-relaxed text-[#808080]">A plataforma disponibilizou mais de um recurso. Selecione somente os que deseja vincular a este ambiente.</p></div>
          <button type="button" onClick={() => setPendingSelection(undefined)} className="rounded-lg p-2 text-[#808080] transition hover:bg-white/[0.05] hover:text-white" aria-label="Fechar"><X className="h-4 w-4" /></button>
        </div>
        <div className="mt-4 max-h-[48vh] space-y-2 overflow-y-auto">{pendingSelection.accounts.map(item => {
          const selected = selectedPendingIds.includes(item.providerAccountId);
          return <button key={item.providerAccountId} type="button" onClick={() => setSelectedPendingIds(current => selected ? current.filter(id => id !== item.providerAccountId) : [...current, item.providerAccountId])} className={`flex w-full items-center gap-3 rounded-xl border p-3 text-left transition ${selected ? 'border-[#FF7F50]/30 bg-[#FF7F50]/[0.05]' : 'border-white/[0.06] bg-white/[0.018] hover:border-white/[0.12]'}`}>
            {item.avatarUrl ? <img src={item.avatarUrl} alt="" className="h-10 w-10 rounded-lg object-cover" /> : <span className="grid h-10 w-10 place-items-center rounded-lg bg-white/[0.04] text-[9px] uppercase text-[#808080]">{item.accountType?.slice(0, 2) || 'ID'}</span>}
            <span className="min-w-0 flex-1"><strong className="block truncate text-[10px] font-medium text-white">{item.displayName}</strong><span className="mt-0.5 block truncate text-[9px] text-[#808080]">{item.username ? `@${item.username.replace(/^@/, '')}` : item.accountType || 'Conta'}</span></span>
            <span className={`grid h-4 w-4 place-items-center rounded border ${selected ? 'border-[#FF7F50] bg-[#FF7F50] text-black' : 'border-white/15'}`}>{selected && <Check className="h-3 w-3" />}</span>
          </button>;
        })}</div>
        <button type="button" disabled={!selectedPendingIds.length || selectingAccounts} onClick={confirmPendingSelection} className="mt-5 flex h-10 w-full items-center justify-center gap-2 rounded-lg bg-[#FF7F50] text-[10px] font-semibold text-black transition hover:bg-[#F28500] disabled:cursor-not-allowed disabled:opacity-45">{selectingAccounts && <ClickoLoader size="tiny" tone="light" label="Adicionando contas" />}Adicionar {selectedPendingIds.length || ''} conta(s)</button>
      </section>
    </div>}
  </div>;
}
