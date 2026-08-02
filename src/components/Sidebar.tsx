import React from 'react';
import {
  LayoutDashboard,
  Users,
  Building2,
  BrainCircuit,
  Target,
  Clapperboard,
  CalendarDays,
  Sparkles,
  Send,
  ChartNoAxesCombined,
  PanelsTopLeft,
  Library,
  Settings,
  ChevronLeft,
  Box,
  CreditCard,
  ScrollText,
} from 'lucide-react';
import { NavigationTab } from '../types';
import { ClickoLogo } from './ClickoLogo';
import { useGovernance } from '../context/GovernanceContext';

interface SidebarProps {
  currentTab: NavigationTab;
  onSelectTab: (tab: NavigationTab) => void;
  isCompact: boolean;
  onToggleCompact: () => void;
  onOpenSpotlight: () => void;
  onNewPost: () => void;
}

const navItems: Array<{
  label: string;
  id: NavigationTab;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string;
}> = [
  { label: 'Dashboard', id: 'dashboard', icon: LayoutDashboard },
  { label: 'Workspace', id: 'workspace', icon: Building2 },
  { label: 'Brain', id: 'brain', icon: BrainCircuit },
  { label: 'Strategy', id: 'strategy', icon: Target },
  { label: 'Studio', id: 'studio', icon: Clapperboard },
  { label: 'Biblioteca', id: 'library', icon: Library },
  { label: 'Calendário', id: 'calendar', icon: CalendarDays },
  { label: 'Aprovações', id: 'approvals', icon: Sparkles },
  { label: 'Publicações', id: 'publisher', icon: Send },
  { label: 'Analytics', id: 'analytics', icon: ChartNoAxesCombined },
  { label: 'Equipe', id: 'team', icon: Users },
  { label: 'Templates / Automações', id: 'automations', icon: PanelsTopLeft },
  { label: 'Logs', id: 'audit-logs', icon: ScrollText },
  { label: 'Configurações', id: 'settings', icon: Settings },
];

export const Sidebar: React.FC<SidebarProps> = ({
  currentTab,
  onSelectTab,
  isCompact,
  onToggleCompact,
}) => {
  const { canAccess, currentUser, workspace, users, approvals } = useGovernance();
  const visibleNavItems = currentUser ? navItems.filter((item) => canAccess(item.id)) : navItems.filter((item) => item.id === 'dashboard');
  const occupiedSeats = users.filter((user) => user.status !== 'disabled').length;

  return (
    <aside
      className={`fixed inset-y-0 left-0 z-40 flex flex-col border-r border-white/[0.075] bg-[#0B0B0B] transition-[width] duration-200 max-[900px]:w-[76px] ${
        isCompact ? 'w-[76px]' : 'w-[188px] 2xl:w-[226px]'
      }`}
    >
      <div className={`flex h-[82px] items-center bg-black max-[900px]:justify-center max-[900px]:px-3 ${isCompact ? 'justify-center px-3' : 'px-5 2xl:px-7'}`}>
        <button
          type="button"
          onClick={() => onSelectTab('dashboard')}
          className="clicko-brand-link flex items-center rounded-sm focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#8bd132]"
          aria-label="Voltar ao Dashboard"
          title="Voltar ao Dashboard"
        >
          <ClickoLogo appearance="seamless" variant="icon" className={`clicko-logo-collapsed-size shrink-0 ${isCompact ? 'clicko-logo-force-visible' : 'clicko-logo-compact-responsive'}`} />
          {!isCompact && <ClickoLogo appearance="seamless" className="clicko-logo-full-responsive h-[64px] w-[128px] 2xl:h-[70px] 2xl:w-[140px]" />}
        </button>
      </div>

      <nav className={`custom-scrollbar mt-3 flex-1 overflow-y-auto ${isCompact ? 'px-2.5' : 'px-3.5'}`}>
        <div className="space-y-0.5">
          {visibleNavItems.map((item) => {
            const Icon = item.icon;
            const selected = currentTab === item.id;
            const badge = item.id === 'approvals' ? String(approvals.filter((approval) => ['in_review', 'pending_approval'].includes(approval.stage)).length) : item.badge;
            return (
              <button
                key={item.label}
                type="button"
                onClick={() => onSelectTab(item.id)}
                aria-label={item.label}
                title={isCompact ? item.label : undefined}
                className={`relative flex w-full items-center rounded-[9px] text-[12px] transition-colors max-[900px]:justify-center max-[900px]:px-2 max-[900px]:py-2.5 ${
                  isCompact ? 'justify-center px-2 py-2.5' : 'gap-3 px-3 py-[9px]'
                } ${selected ? 'bg-[#21292e] font-medium text-white' : 'text-[#d2d6d9] hover:bg-white/[0.035] hover:text-white'}`}
              >
                {selected && <span className="absolute inset-y-0 left-0 w-[2px] rounded-full bg-[#8bd132]" />}
                <Icon className={`h-[16px] w-[16px] shrink-0 ${selected ? 'text-[#8bd132]' : 'text-[#c4c9cc]'}`} strokeWidth={1.7} />
                {!isCompact && <span className="flex-1 text-left max-[900px]:hidden">{item.label}</span>}
                {!isCompact && badge && badge !== '0' && (
                  <span className="grid h-[18px] min-w-[18px] place-items-center rounded-full bg-[#8bd132] px-1 text-[9px] font-bold text-[#14200e] max-[900px]:hidden">
                    {badge}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </nav>

      {!isCompact && currentUser?.role === 'master' && (
        <div className="m-3.5 rounded-[11px] border border-white/[0.055] bg-[#1b2328] p-3.5 max-[900px]:hidden">
          <div className="text-[12px] font-semibold text-white">Plano {workspace?.planId ? workspace.planId.charAt(0).toUpperCase() + workspace.planId.slice(1) : '—'}</div>
          <div className="mt-3 flex items-center justify-between text-[9px] text-[#c1c7ca]">
            <span>Assentos usados</span>
            <span>{occupiedSeats} / {workspace?.maxUsers ?? '∞'}</span>
          </div>
          <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-[#30393e]">
            <div className="h-full rounded-full bg-[#8bd132]" style={{ width: workspace?.maxUsers ? `${Math.min(100, (occupiedSeats / workspace.maxUsers) * 100)}%` : '32%' }} />
          </div>
          <div className="mt-3.5 space-y-2">
            <button onClick={() => onSelectTab('subscription')} className="w-full rounded-md bg-[#8bd132] py-2 text-[10px] font-bold text-[#14200e] transition hover:bg-[#9be24d]">
              Fazer upgrade
            </button>
            <button onClick={() => onSelectTab('subscription')} className="flex w-full items-center justify-center gap-1.5 rounded-md border border-white/[0.08] bg-white/[0.025] py-2 text-[9px] font-medium text-[#aeb6ba] transition hover:border-white/15 hover:bg-white/[0.05] hover:text-white">
              <CreditCard className="h-3.5 w-3.5" />Ver Mais
            </button>
          </div>
        </div>
      )}

      <button
        type="button"
        onClick={onToggleCompact}
        className="flex h-10 items-center justify-center text-[#69747a] transition-colors hover:text-[#8bd132]"
        aria-label={isCompact ? 'Expandir barra lateral' : 'Recolher barra lateral'}
      >
        <ChevronLeft className={`h-[18px] w-[18px] transition-transform duration-200 ${isCompact ? 'rotate-180' : ''}`} />
      </button>

      <footer className={`vexel-powered-divider relative border-t ${isCompact ? 'px-3 py-3.5' : 'px-4 py-[18px]'}`}>
        {isCompact ? (
          <div className="group relative flex justify-center">
            <a
              href="https://vexelbr.com/"
              target="_blank"
              rel="noopener noreferrer"
              title="Powered by VEXEL"
              className="vexel-powered-signature vexel-powered-mark grid h-8 w-8 place-items-center rounded-lg border"
              aria-label="Powered by VEXEL"
            >
              <Box className="h-[17px] w-[17px]" strokeWidth={1.6} />
            </a>
            <div
              role="tooltip"
              className="vexel-powered-tooltip pointer-events-none absolute bottom-0 left-full z-50 ml-3 whitespace-nowrap rounded-md border px-3 py-2 text-[9px] font-medium uppercase tracking-[0.22em] opacity-0 transition-opacity duration-150 group-hover:opacity-100 group-focus-within:opacity-100"
            >
              Powered by VEXEL
            </div>
          </div>
        ) : (
          <a
            href="https://vexelbr.com/"
            target="_blank"
            rel="noopener noreferrer"
            title="Powered by VEXEL"
            className="vexel-powered-signature block text-center text-[8px] font-medium uppercase tracking-[0.3em] max-[900px]:grid max-[900px]:place-items-center"
          >
            <Box className="hidden h-[17px] w-[17px] max-[900px]:block" strokeWidth={1.6} />
            <span className="max-[900px]:hidden">Powered by VEXEL</span>
          </a>
        )}
      </footer>
    </aside>
  );
};
