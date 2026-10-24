import React from 'react';
import {
  ArrowUpRight, CalendarClock, CircleAlert, HardDrive, Image as ImageIcon,
  Link2, RefreshCw, Users, Video, Workflow,
} from 'lucide-react';
import { useGovernance } from '../context/GovernanceContext';
import { hasPermission } from '../security/accessControl';
import type { UsageResource } from '../types';
import { ClickoLoader } from './ClickoLoader';
import { KlicSymbol } from './KlicSymbol';
import './ConsumptionSettingsView.css';

const formatter = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 1 });
const dateFormatter = new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: 'short', year: 'numeric' });

const resourceMeta: Record<UsageResource, { label: string; group: 'main' | 'account'; icon: React.ComponentType<{ size?: number }> }> = {
  klic_credits: { label: 'KLIC', group: 'main', icon: KlicSymbol },
  image_generations: { label: 'Imagens', group: 'main', icon: ImageIcon },
  video_minutes: { label: 'Vídeo', group: 'main', icon: Video },
  storage_bytes: { label: 'Armazenamento', group: 'account', icon: HardDrive },
  social_accounts: { label: 'Contas sociais', group: 'account', icon: Link2 },
  clients: { label: 'Clientes cadastrados', group: 'account', icon: Users },
  automations: { label: 'Automações', group: 'account', icon: Workflow },
};

const resourceOrder: UsageResource[] = [
  'klic_credits', 'image_generations', 'video_minutes',
  'storage_bytes', 'social_accounts', 'clients', 'automations',
];

function formatDate(value?: string) {
  return value && Number.isFinite(Date.parse(value)) ? dateFormatter.format(new Date(value)) : 'Não informado';
}

function formatAmount(resource: UsageResource, amount: number | null) {
  if (amount === null) return 'Ilimitado';
  if (resource === 'storage_bytes') return `${formatter.format(amount / 1_000_000_000)} GB`;
  if (resource === 'video_minutes') return `${formatter.format(amount)} min`;
  return formatter.format(amount);
}

function openPlans() {
  window.history.pushState({}, '', '/subscription');
  window.dispatchEvent(new PopStateEvent('popstate'));
}

export const ConsumptionSettingsView: React.FC = () => {
  const {
    environmentMode, activeAccount, currentUser, plans, subscription, usage, workspace,
    loading, feedback, refresh,
  } = useGovernance();
  const canReadOrganization = environmentMode === 'personal' || hasPermission(currentUser, 'usage.read.organization');
  const plan = plans.find((item) => item.id === (subscription?.planId || workspace?.planId));
  const planName = plan?.name || activeAccount.planName || 'Plano não informado';

  const items = usage ? resourceOrder.map((resource) => {
    const allowance = usage.resources[resource];
    const ownUsed = usage.memberUsage[currentUser?.id || '']?.[resource] ?? 0;
    const ownLimit = usage.memberLimits[currentUser?.id || '']?.[resource];
    return {
      resource,
      used: canReadOrganization ? allowance.used : ownUsed,
      limit: canReadOrganization ? allowance.limit : ownLimit ?? allowance.limit,
    };
  }) : [];

  if (loading && !usage) {
    return <div className="cu-shell" aria-busy="true"><ClickoLoader context="section" label="Carregando consumo" message="Carregando consumo…" /></div>;
  }

  if (!usage) {
    const failed = feedback?.type === 'error';
    return <div className="cu-shell"><div className="cu-empty" role={failed ? 'alert' : 'status'}><CircleAlert size={21} /><h3>{failed ? 'Não foi possível carregar o consumo' : 'Consumo ainda indisponível'}</h3><p>{failed ? feedback.message : 'O servidor ainda não retornou dados de utilização para este ambiente.'}</p><button type="button" onClick={() => void refresh()}><RefreshCw size={14} /> Tentar novamente</button></div></div>;
  }

  const periodEnd = usage.periodEndsAt || subscription?.renewsAt;

  const renderGroup = (group: 'main' | 'account', title: string, description: string) => {
    const groupItems = items.filter(({ resource }) => resourceMeta[resource].group === group);
    return <section className="cu-group" aria-labelledby={`cu-${group}`}><header><div><h3 id={`cu-${group}`}>{title}</h3><p>{description}</p></div><span>{groupItems.length} recursos</span></header><div className="cu-grid">{groupItems.map(({ resource, used, limit }) => {
      const meta = resourceMeta[resource];
      const Icon = meta.icon;
      const percent = typeof limit === 'number' && limit > 0 ? Math.min(100, Math.max(0, used / limit * 100)) : null;
      const state = limit === 0 ? 'excluded' : percent !== null && percent >= 100 ? 'reached' : percent !== null && percent >= 80 ? 'near' : 'normal';
      const isUnlimited = limit === null;
      return <article className={`cu-card ${resource === 'klic_credits' ? 'is-klic' : ''}`} data-state={state} key={resource}>
        <div className="cu-card-heading"><span className="cu-icon"><Icon size={17} /></span><h4>{meta.label}</h4>{isUnlimited && <span className="cu-unlimited">Ilimitado</span>}</div>
        {limit === 0 ? <div className="cu-not-included"><strong>Não incluído neste plano</strong><button type="button" onClick={openPlans}>Ver opções <ArrowUpRight size={13} /></button></div> : <>
          <div className="cu-value"><strong>{formatAmount(resource, used)}</strong><span>{isUnlimited ? 'utilizado' : `/ ${formatAmount(resource, limit)}`}</span></div>
          {!isUnlimited && <div className="cu-progress" role="progressbar" aria-label={`Consumo de ${meta.label}`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(percent || 0)}><span style={{ width: `${percent || 0}%` }} /></div>}
          <div className="cu-card-note">{state === 'reached' ? 'Limite do período atingido.' : state === 'near' ? 'Você está próximo do limite deste recurso.' : isUnlimited ? 'Este recurso não possui limite definido.' : `${formatter.format(percent || 0)}% utilizado`}</div>
        </>}
      </article>;
    })}</div></section>;
  };

  return <div className="cu-shell">
    <section className="cu-summary" aria-label="Resumo do período de consumo"><div><span className="cu-overline">PLANO ATUAL</span><h3>{planName}</h3><p>{environmentMode === 'company' ? 'Consumo compartilhado deste workspace.' : 'Consumo exclusivo do seu perfil pessoal.'}</p></div><div className="cu-cycle"><CalendarClock size={17} /><div><span>Período atual</span><strong>{formatDate(usage.periodStartedAt)} — {formatDate(periodEnd)}</strong></div></div><p className="cu-renewal">Os limites são renovados automaticamente a cada novo ciclo da assinatura.</p></section>
    {renderGroup('main', 'Uso principal', 'Criação e inteligência incluídas no plano.')}
    {renderGroup('account', 'Recursos da conta', 'Capacidade estrutural disponível neste ambiente.')}
  </div>;
};
