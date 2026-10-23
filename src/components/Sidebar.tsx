import React from 'react';
import {
  LayoutDashboard, Clapperboard, CalendarDays, CheckCircle2,
  ChartNoAxesCombined, Workflow, Link2, User, Users,
  Settings, ChevronLeft, FolderKanban, CreditCard, Gauge
} from 'lucide-react';
import type { NavigationTab } from '../types';
import { ClickoLogo } from './ClickoLogo';
import { KlicSymbol } from './KlicSymbol';
import { useGovernance } from '../context/GovernanceContext';
import { hasPermission } from '../security/accessControl';
import { isStudioModule } from '../studios/studioNavigation';

interface SidebarProps {
  currentTab: NavigationTab;
  onSelectTab: (tab: NavigationTab) => void;
  isCompact: boolean;
  onToggleCompact: () => void;
  onOpenSpotlight: () => void;
  onNewPost: () => void;
}

type NavItem = { label: string; id: NavigationTab; icon: React.ComponentType<{ className?: string; strokeWidth?: number }> };

export const Sidebar: React.FC<SidebarProps> = ({ currentTab, onSelectTab, isCompact, onToggleCompact }) => {
  const { canAccess, currentUser, workspace, plans, subscription, activeAccount, approvals, environmentMode } = useGovernance();
  const isPersonal = environmentMode === 'personal';
  const currentPlan = plans.find((plan) => plan.id === (subscription?.planId || workspace?.planId));
  const currentPlanName = currentPlan?.name || activeAccount.planName || 'Plano não informado';

  const openConsumption = () => {
    onSelectTab('settings');
    window.history.replaceState({}, '', '/settings?section=billing');
    window.dispatchEvent(new CustomEvent('clicko:settings-section', { detail: { section: 'billing' } }));
  };

  const navItems: NavItem[] = [
    { label: 'Dashboard', id: 'dashboard', icon: LayoutDashboard },
    { label: 'Studios', id: canAccess('create-image') ? 'create-image' : 'create-video', icon: Clapperboard },
    { label: 'Klic AI', id: 'ai-chat', icon: KlicSymbol },
    { label: 'Biblioteca', id: 'library', icon: FolderKanban },
    { label: 'Calendário', id: 'calendar', icon: CalendarDays },
    { label: 'Conexões', id: 'connected-accounts', icon: Link2 },
    ...(!isPersonal ? [
      { label: 'Clientes', id: 'workspace' as const, icon: User },
      { label: 'Aprovações', id: 'approvals' as const, icon: CheckCircle2 },
      { label: 'Automações', id: 'automations' as const, icon: Workflow },
    ] : []),
    { label: 'Analytics', id: 'analytics', icon: ChartNoAxesCombined },
    ...(!isPersonal ? [{ label: 'Equipe', id: 'team' as const, icon: Users }] : []),
    { label: 'Configurações', id: 'settings', icon: Settings },
  ];

  const renderItem = (item: NavItem) => {
    const Icon = item.icon;
    const selected = currentTab === item.id || (item.label === 'Studios' && isStudioModule(currentTab));
    const badge = item.id === 'approvals' ? approvals.filter((approval) => ['in_review', 'pending_approval'].includes(approval.stage)).length : 0;
    
    if (currentUser && !canAccess(item.id)) return null;

    return (
      <button
        key={item.id}
        type="button"
        onClick={() => onSelectTab(item.id)}
        aria-label={item.label}
        aria-current={selected ? 'page' : undefined}
        title={isCompact ? item.label : undefined}
        className={`clicko-nav-item group relative flex w-full items-center rounded-lg text-[11px] font-medium transition-colors duration-150 max-[900px]:justify-center max-[900px]:px-2 max-[900px]:py-2.5 ${
          isCompact ? 'justify-center px-2 py-2.5' : 'gap-3 px-3 py-2'
        } ${
          selected
            ? 'bg-white/[0.055] font-semibold text-white'
            : 'text-[#808080] hover:bg-white/[0.025] hover:text-white'
        }`}
      >
        {selected && (
          <span className="clicko-nav-active-indicator absolute inset-y-2 left-0 w-0.5 rounded-full bg-[#FF7F50]" />
        )}
        <Icon
          className={`h-[15px] w-[15px] shrink-0 transition-colors ${
            selected ? 'text-[#FF7F50]' : 'text-[#808080] group-hover:text-white'
          }`}
          strokeWidth={selected ? 2.2 : 1.8}
        />
        {!isCompact && (
          <span className="min-w-0 flex-1 truncate text-left max-[900px]:hidden tracking-tight">
            {item.label}
          </span>
        )}
        {!isCompact && badge > 0 && (
          <span className="grid h-4 min-w-[16px] place-items-center rounded-full bg-[#FF7F50] px-1 text-[9px] font-bold text-[#000000] max-[900px]:hidden">
            {badge}
          </span>
        )}
      </button>
    );
  };

  return (
    <aside
      className={`clicko-sidebar fixed bottom-2 left-2 top-2 z-40 flex flex-col overflow-hidden rounded-2xl border border-white/[0.06] bg-[#000000] transition-[width] duration-300 ease-out max-[900px]:w-[64px] ${
        isCompact ? 'w-[64px]' : 'w-[216px]'
      }`}
    >
      {/* Header Logo Area */}
      <div
        className={`clicko-sidebar-brand flex h-[64px] shrink-0 items-center border-b border-white/[0.045] bg-[#000000] max-[900px]:justify-center max-[900px]:px-2 ${
          isCompact ? 'justify-center px-2' : 'px-4 2xl:px-5'
        }`}
      >
        <button
          type="button"
          onClick={() => onSelectTab('dashboard')}
          className="clicko-brand-link flex items-center rounded-xl transition-all hover:opacity-90 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#FF7F50]"
          aria-label="Voltar ao Painel"
          title="Voltar ao Painel"
        >
          <ClickoLogo
            appearance="seamless"
            variant="icon"
            className={`clicko-logo-collapsed-size shrink-0 ${
              isCompact ? 'clicko-logo-force-visible' : 'clicko-logo-compact-responsive'
            }`}
          />
          {!isCompact && (
            <ClickoLogo
              appearance="seamless"
              className="clicko-sidebar-logo-full clicko-logo-full-responsive"
            />
          )}
        </button>
      </div>

      {/* Navigation Group Scroll */}
      <nav className={`clicko-sidebar-nav custom-scrollbar flex-1 overflow-y-auto py-4 ${isCompact ? 'px-2' : 'px-3'}`}>
        <div className="space-y-0.5">{navItems.map(renderItem)}</div>
      </nav>

      {/* Subscription actions */}
      {hasPermission(currentUser, 'subscription.read') && !isCompact && (
        <section className="clicko-plan-widget mx-2.5 my-2 max-[900px]:hidden" aria-label={`Plano ativo: ${currentPlanName}`}>
          <strong>{`Plano ${currentPlanName}`}</strong>
          <button type="button" className="clicko-plan-widget__primary" onClick={() => onSelectTab('subscription')}><CreditCard size={14} />Mudar de plano</button>
          <button type="button" className="clicko-plan-widget__secondary" onClick={openConsumption}><Gauge size={14} />Ver consumo</button>
        </section>
      )}
      {hasPermission(currentUser, 'subscription.read') && (
        <div className={`clicko-plan-widget-compact my-2 ${isCompact ? 'grid' : 'hidden max-[900px]:grid'}`} aria-label={`Plano ativo: ${currentPlanName}`}>
          <button type="button" onClick={() => onSelectTab('subscription')} aria-label={`Mudar de plano. Plano atual: ${currentPlanName}`} title={`Plano ${currentPlanName}`}><CreditCard size={16} /></button>
          <button type="button" onClick={openConsumption} aria-label="Ver consumo do plano" title="Ver consumo"><Gauge size={16} /></button>
        </div>
      )}

      {/* Collapse Toggle */}
      <button
        type="button"
        onClick={onToggleCompact}
        className="flex h-11 shrink-0 items-center justify-center border-t border-white/[0.05] text-[rgba(255,127,80,0.22)] transition-colors hover:text-[#FF7F50]"
        aria-label={isCompact ? 'Expandir barra lateral' : 'Recolher barra lateral'}
      >
        <ChevronLeft className={`h-4 w-4 transition-transform duration-300 ${isCompact ? 'rotate-180' : ''}`} />
      </button>
    </aside>
  );
};

