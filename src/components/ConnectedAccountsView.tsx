import React from 'react';
import {
  Check,
  ChevronRight,
  CircleAlert,
  Clock3,
  Link2,
  Linkedin,
  LoaderCircle,
  RefreshCw,
  Settings2,
  ShieldCheck,
  Unplug,
  X,
} from 'lucide-react';
import { siFacebook, siInstagram, siThreads, siTiktok, siYoutube } from 'simple-icons';
import { useGovernance } from '../context/GovernanceContext';
import { useOperations } from '../context/OperationsContext';
import type { ConnectedAccount, ConnectedResource, SocialPlatform } from '../types';

type VisiblePlatform = Exclude<SocialPlatform, 'x'>;
type BusyState = 'connecting' | 'syncing';
type SyncPreference = NonNullable<ConnectedAccount['syncPreferences']>[number];

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
  { id: 'linkedin', name: 'LinkedIn', iconComponent: Linkedin },
  { id: 'youtube', name: 'YouTube', icon: siYoutube },
  { id: 'threads', name: 'Threads', icon: siThreads },
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

function statusPresentation(account?: ConnectedAccount, busy?: BusyState) {
  const status = busy || account?.connectionStatus || 'not_configured';
  if (status === 'connecting') return { label: 'Conectando', className: 'bg-sky-400/[0.08] text-sky-300', pulse: true };
  if (status === 'syncing') return { label: 'Sincronizando', className: 'bg-sky-400/[0.08] text-sky-300', pulse: true };
  if (status === 'synced') return { label: 'Sincronizada', className: 'bg-[#8bd132]/[0.08] text-[#8bd132]', pulse: false };
  if (status === 'sync_error' || status === 'error') return { label: 'Erro na sincronização', className: 'bg-red-400/[0.08] text-red-300', pulse: false };
  if (account?.connected && status === 'connected') return { label: 'Conectada', className: 'bg-[#8bd132]/[0.08] text-[#8bd132]', pulse: false };
  return { label: 'Não conectada', className: 'bg-white/[0.045] text-[#7f898e]', pulse: false };
}

function formatLastSync(value?: string) {
  if (!value || value === 'Nunca') return 'Ainda não sincronizada';
  if (value === 'Agora') return 'Sincronizada agora';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return `Última sincronização: ${value}`;
  return `Última sincronização: ${new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' }).format(date)}`;
}

export function ConnectedAccountsView() {
  const { currentUser, environmentMode } = useGovernance();
  const {
    activeWorkspace,
    connectedAccounts: accounts,
    addConnectedAccount,
    updateConnectedAccount,
  } = useOperations();
  const [feedback, setFeedback] = React.useState<{ tone: 'neutral' | 'error'; message: string }>();
  const [busyPlatforms, setBusyPlatforms] = React.useState<Partial<Record<VisiblePlatform, BusyState>>>({});
  const [managingId, setManagingId] = React.useState<string>();
  const [selectedResources, setSelectedResources] = React.useState<string[]>([]);
  const [selectedPreferences, setSelectedPreferences] = React.useState<SyncPreference[]>([]);

  const managingAccount = accounts.find((account) => account.id === managingId);

  const integrationHeaders = React.useMemo(() => ({
    'Content-Type': 'application/json',
    'x-workspace-id': activeWorkspace.id,
    'x-user-id': currentUser?.id || 'current-user',
  }), [activeWorkspace.id, currentUser?.id]);

  const accountFor = React.useCallback((platform: VisiblePlatform) => accounts.find((account) => account.platform === platform), [accounts]);
  const ensureAccount = React.useCallback((platform: VisiblePlatform) => accountFor(platform) || addConnectedAccount(platform), [accountFor, addConnectedAccount]);

  const loadResources = React.useCallback(async (account: ConnectedAccount) => {
    const response = await fetch(`/api/integrations/${account.platform}/resources`, { headers: integrationHeaders });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.message || 'Não foi possível carregar os perfis disponíveis.');
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
    if (status !== 'connected') {
      const reason = params.get('reason') || 'A autorização não foi concluída pelo provedor.';
      updateConnectedAccount(account.id, { connected: false, connectionStatus: 'authorization_required', lastError: reason });
      setFeedback({ tone: 'error', message: reason });
      return;
    }
    updateConnectedAccount(account.id, { connected: true, connectionStatus: 'connected', lastError: undefined });
    setManagingId(account.id);
    setSelectedResources(account.selectedResourceIds || []);
    setSelectedPreferences(account.syncPreferences || ['profile', 'analytics']);
    loadResources(account).catch((error) => {
      setFeedback({ tone: 'error', message: error instanceof Error ? error.message : 'Não foi possível carregar os perfis disponíveis.' });
    });
  }, [ensureAccount, loadResources, updateConnectedAccount]);

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
      if (!response.ok || !data.authorizationUrl) throw new Error(data.message || 'Não foi possível iniciar a autorização.');
      updateConnectedAccount(account.id, { connectionStatus: 'connecting', lastError: undefined });
      window.location.assign(data.authorizationUrl);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Não foi possível iniciar a autorização.';
      updateConnectedAccount(account.id, { connected: false, connectionStatus: 'authorization_required', lastError: message });
      setFeedback({ tone: 'error', message });
      setBusyPlatforms((current) => ({ ...current, [platform]: undefined }));
    }
  };

  const openManagement = async (account: ConnectedAccount) => {
    setManagingId(account.id);
    setSelectedResources(account.selectedResourceIds || []);
    setSelectedPreferences(account.syncPreferences || ['profile', 'analytics']);
    if (!account.availableResources?.length) {
      try { await loadResources(account); } catch (error) {
        setFeedback({ tone: 'error', message: error instanceof Error ? error.message : 'Não foi possível atualizar os perfis.' });
      }
    }
  };

  const saveManagement = () => {
    if (!managingAccount) return;
    updateConnectedAccount(managingAccount.id, {
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
        body: JSON.stringify({ selectedResourceIds: account.selectedResourceIds || [], syncPreferences: account.syncPreferences || [] }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.message || 'A sincronização não pôde ser concluída.');
      updateConnectedAccount(account.id, { connectionStatus: 'synced', lastSync: data.syncedAt || new Date().toISOString(), lastError: undefined });
      setFeedback({ tone: 'neutral', message: `${platformLabel(account.platform)} sincronizado com sucesso.` });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'A sincronização não pôde ser concluída.';
      updateConnectedAccount(account.id, { connectionStatus: 'sync_error', lastError: message });
      setFeedback({ tone: 'error', message });
    } finally {
      setBusyPlatforms((current) => ({ ...current, [account.platform as VisiblePlatform]: undefined }));
    }
  };

  const disconnect = async (account: ConnectedAccount) => {
    try {
      await fetch(`/api/integrations/${account.platform}/disconnect`, { method: 'POST', headers: integrationHeaders });
    } finally {
      updateConnectedAccount(account.id, {
        connected: false,
        connectionStatus: 'authorization_required',
        handle: 'Autorização pendente',
        lastSync: 'Nunca',
        permissions: [],
        availableResources: [],
        selectedResourceIds: [],
        syncPreferences: [],
        lastError: undefined,
      });
      setManagingId(undefined);
      setFeedback({ tone: 'neutral', message: `${platformLabel(account.platform)} desconectado de ${activeWorkspace.name}.` });
    }
  };

  const connectedCount = socialPlatforms.filter(({ id }) => {
    const account = accountFor(id);
    return account?.connected && ['connected', 'synced', 'syncing'].includes(account.connectionStatus || '');
  }).length;

  return <div className="mx-auto w-full max-w-[1360px] space-y-7 p-5 sm:p-6 2xl:p-10">
    <header className="flex flex-col gap-5 border-b border-white/[0.06] pb-7 sm:flex-row sm:items-end sm:justify-between">
      <div className="max-w-2xl">
        <p className="text-[10px] font-medium uppercase tracking-[0.24em] text-[#8bd132]">Integrações</p>
        <h1 className="mt-2 text-2xl font-semibold tracking-[-0.02em] text-white">Conexões</h1>
        <p className="mt-2 text-sm leading-6 text-[#8f999f]">Conecte as plataformas que deseja usar em todo o sistema e mantenha seus canais sincronizados em um só lugar.</p>
      </div>
      <div className="flex items-center gap-3 text-[10px] text-[#778187]">
        <span className="grid h-8 w-8 place-items-center rounded-lg border border-white/[0.06] bg-white/[0.025]"><ShieldCheck className="h-4 w-4 text-[#8bd132]" /></span>
        <span><strong className="block font-medium text-[#c6cccf]">{environmentMode === 'personal' ? 'Conta pessoal' : 'Workspace'}</strong>{activeWorkspace.name}</span>
      </div>
    </header>

    {feedback && <div role="status" className={`flex items-center justify-between gap-4 rounded-xl border px-4 py-3 text-[10px] leading-relaxed ${feedback.tone === 'error' ? 'border-amber-400/15 bg-amber-400/[0.045] text-amber-100' : 'border-white/[0.06] bg-white/[0.025] text-[#aab3b7]'}`}>
      <span className="flex items-center gap-2">{feedback.tone === 'error' ? <CircleAlert className="h-4 w-4 shrink-0 text-amber-300" /> : <Check className="h-4 w-4 shrink-0 text-[#8bd132]" />}{feedback.message}</span>
      <button type="button" onClick={() => setFeedback(undefined)} className="shrink-0 rounded-md p-1 text-current opacity-60 transition hover:bg-white/[0.05] hover:opacity-100" aria-label="Fechar aviso"><X className="h-3.5 w-3.5" /></button>
    </div>}

    <section aria-labelledby="social-connections-title" className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h2 id="social-connections-title" className="text-[10px] font-semibold uppercase tracking-[0.18em] text-[#aeb6ba]">Redes sociais</h2>
          <p className="mt-1 text-[10px] text-[#687278]">{connectedCount} de {socialPlatforms.length} plataformas conectadas</p>
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        {socialPlatforms.map((definition) => {
          const account = accountFor(definition.id);
          const ready = Boolean(account?.connected && ['connected', 'synced', 'syncing'].includes(account.connectionStatus || ''));
          const status = statusPresentation(account, busyPlatforms[definition.id]);
          return <article key={definition.id} className="group rounded-xl border border-white/[0.065] bg-[#182126] p-4 transition-colors hover:border-white/[0.11]">
            <div className="flex items-start gap-3">
              <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg border border-white/[0.06] bg-black/20 text-[#d6dadd] transition-colors group-hover:text-white"><SocialIcon definition={definition} /></span>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h3 className="text-[11px] font-semibold text-white">{definition.name}</h3>
                  <span className={`inline-flex items-center gap-1.5 rounded-full px-2 py-1 text-[8px] font-medium ${status.className}`}><span className={`h-1.5 w-1.5 rounded-full bg-current ${status.pulse ? 'animate-pulse' : ''}`} />{status.label}</span>
                </div>
                <p className="mt-1 text-[9px] text-[#6f797e]">{ready ? formatLastSync(account?.lastSync) : 'Autorize pelo provedor oficial para começar.'}</p>
              </div>
            </div>

            <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-white/[0.055] pt-3">
              {!ready ? <button type="button" disabled={Boolean(busyPlatforms[definition.id])} onClick={() => connect(definition.id)} className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-[#8bd132] px-3 text-[9px] font-semibold text-[#13200d] transition hover:bg-[#9ade3e] disabled:cursor-wait disabled:opacity-60">
                {busyPlatforms[definition.id] === 'connecting' ? <LoaderCircle className="h-3.5 w-3.5 animate-spin" /> : <Link2 className="h-3.5 w-3.5" />}Conectar
              </button> : <>
                <button type="button" disabled={Boolean(busyPlatforms[definition.id])} onClick={() => account && syncNow(account)} className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-white/[0.075] px-3 text-[9px] font-medium text-[#b5bdc1] transition hover:border-white/[0.14] hover:text-white disabled:cursor-wait disabled:opacity-60">
                  {busyPlatforms[definition.id] === 'syncing' ? <LoaderCircle className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}Sincronizar agora
                </button>
                <button type="button" onClick={() => account && openManagement(account)} className="inline-flex h-8 items-center gap-1.5 rounded-lg px-2.5 text-[9px] text-[#818b90] transition hover:bg-white/[0.04] hover:text-white"><Settings2 className="h-3.5 w-3.5" />Gerenciar</button>
                <button type="button" onClick={() => account && disconnect(account)} className="ml-auto inline-flex h-8 items-center gap-1.5 rounded-lg px-2 text-[9px] text-[#677176] transition hover:bg-red-400/[0.055] hover:text-red-300"><Unplug className="h-3.5 w-3.5" />Desconectar</button>
              </>}
              {!ready && <ChevronRight className="ml-auto h-3.5 w-3.5 text-[#4f595e]" />}
            </div>
          </article>;
        })}
      </div>
    </section>

    <footer className="flex items-start gap-3 rounded-xl border border-white/[0.055] bg-white/[0.018] px-4 py-3 text-[9px] leading-relaxed text-[#727d82]">
      <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-[#8bd132]" />
      <p>As conexões ficam isoladas em <strong className="font-medium text-[#aeb6ba]">{activeWorkspace.name}</strong>. A autorização acontece no site oficial de cada plataforma e as credenciais nunca são solicitadas nesta tela.</p>
    </footer>

    {managingAccount && <div className="fixed inset-0 z-[100] flex justify-end bg-black/70 backdrop-blur-sm" role="dialog" aria-modal="true" aria-labelledby="manage-integration-title">
      <button type="button" className="absolute inset-0" onClick={() => setManagingId(undefined)} aria-label="Fechar gerenciamento" />
      <aside className="relative h-full w-full max-w-[460px] overflow-y-auto border-l border-white/[0.07] bg-[#111719] p-5 shadow-2xl sm:p-6">
        <div className="flex items-start justify-between gap-4 border-b border-white/[0.06] pb-5">
          <div><p className="text-[9px] uppercase tracking-[0.18em] text-[#8bd132]">Gerenciar conexão</p><h2 id="manage-integration-title" className="mt-1.5 text-lg font-semibold text-white">{platformLabel(managingAccount.platform)}</h2><p className="mt-1 text-[10px] text-[#737d82]">Escolha exatamente o que será usado neste ambiente.</p></div>
          <button type="button" onClick={() => setManagingId(undefined)} className="rounded-lg p-2 text-[#737d82] transition hover:bg-white/[0.05] hover:text-white" aria-label="Fechar"><X className="h-4 w-4" /></button>
        </div>

        <section className="mt-6">
          <h3 className="text-[9px] font-semibold uppercase tracking-[0.16em] text-[#aeb6ba]">Perfis, páginas e canais</h3>
          {managingAccount.availableResources?.length ? <div className="mt-3 space-y-2">{managingAccount.availableResources.map((resource) => {
            const selected = selectedResources.includes(resource.id);
            return <button key={resource.id} type="button" onClick={() => setSelectedResources((current) => selected ? current.filter((id) => id !== resource.id) : [...current, resource.id])} className={`flex w-full items-center gap-3 rounded-xl border p-3 text-left transition ${selected ? 'border-[#8bd132]/25 bg-[#8bd132]/[0.045]' : 'border-white/[0.06] bg-white/[0.018] hover:border-white/[0.11]'}`}>
              {resource.avatar ? <img src={resource.avatar} alt="" className="h-9 w-9 rounded-lg object-cover" /> : <span className="grid h-9 w-9 place-items-center rounded-lg bg-black/20 text-[9px] font-semibold uppercase text-[#889297]">{resource.type.slice(0, 2)}</span>}
              <span className="min-w-0 flex-1"><strong className="block truncate text-[10px] font-medium text-white">{resource.name}</strong><span className="mt-0.5 block truncate text-[9px] text-[#6e787d]">{resource.handle || ({ profile: 'Perfil', page: 'Página', channel: 'Canal', board: 'Pasta' }[resource.type])}</span></span>
              <span className={`grid h-4 w-4 place-items-center rounded border ${selected ? 'border-[#8bd132] bg-[#8bd132] text-[#13200d]' : 'border-white/15'}`}>{selected && <Check className="h-3 w-3" />}</span>
            </button>;
          })}</div> : <div className="mt-3 rounded-xl border border-dashed border-white/[0.07] p-4 text-[9px] leading-relaxed text-[#6f797e]">Nenhum perfil foi disponibilizado pelo provedor. Verifique as permissões concedidas ou autorize novamente.</div>}
        </section>

        <section className="mt-7">
          <h3 className="text-[9px] font-semibold uppercase tracking-[0.16em] text-[#aeb6ba]">Dados sincronizados</h3>
          <div className="mt-3 space-y-2">{syncOptions.map((option) => {
            const selected = selectedPreferences.includes(option.id);
            return <button key={option.id} type="button" onClick={() => setSelectedPreferences((current) => selected ? current.filter((id) => id !== option.id) : [...current, option.id])} className="flex w-full items-center gap-3 rounded-xl border border-white/[0.055] bg-white/[0.015] p-3 text-left transition hover:border-white/[0.1]">
              <span className={`relative h-5 w-9 shrink-0 rounded-full transition ${selected ? 'bg-[#8bd132]' : 'bg-white/[0.09]'}`}><span className={`absolute top-0.5 h-4 w-4 rounded-full bg-white transition ${selected ? 'left-[18px]' : 'left-0.5'}`} /></span>
              <span><strong className="block text-[10px] font-medium text-[#d4d8da]">{option.label}</strong><span className="mt-0.5 block text-[8px] leading-relaxed text-[#6d777c]">{option.description}</span></span>
            </button>;
          })}</div>
        </section>

        <div className="mt-7 flex items-center gap-2 rounded-xl bg-white/[0.025] p-3 text-[9px] text-[#717b80]"><Clock3 className="h-4 w-4 shrink-0 text-[#8bd132]" />{formatLastSync(managingAccount.lastSync)}</div>
        <button type="button" onClick={saveManagement} className="mt-5 h-10 w-full rounded-lg bg-[#8bd132] text-[10px] font-semibold text-[#13200d] transition hover:bg-[#9ade3e]">Salvar preferências</button>
      </aside>
    </div>}
  </div>;
}
