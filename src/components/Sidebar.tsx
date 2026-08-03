import React from 'react';
import {
  LayoutDashboard, Image, Video, PenLine, CalendarDays, CheckCircle2,
  ChartNoAxesCombined, Bot, Workflow, LayoutTemplate, Link2, Users,
  ScrollText, Settings, CreditCard, ChevronLeft, Box,
} from 'lucide-react';
import type { NavigationTab } from '../types';
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

type NavItem = { label: string; id: NavigationTab; icon: React.ComponentType<{ className?: string }> };

const primaryItems: NavItem[] = [
  { label: 'Dashboard', id: 'dashboard', icon: LayoutDashboard },
  { label: 'Criar Imagem', id: 'create-image', icon: Image },
  { label: 'Criar Vídeo', id: 'create-video', icon: Video },
  { label: 'Criar Copy', id: 'create-copy', icon: PenLine },
  { label: 'Calendário', id: 'calendar', icon: CalendarDays },
  { label: 'Aprovações', id: 'approvals', icon: CheckCircle2 },
  { label: 'Analytics', id: 'analytics', icon: ChartNoAxesCombined },
  { label: 'AI Chat', id: 'ai-chat', icon: Bot },
  { label: 'Automações', id: 'automations', icon: Workflow },
  { label: 'Templates', id: 'templates', icon: LayoutTemplate },
  { label: 'Contas Conectadas', id: 'connected-accounts', icon: Link2 },
  { label: 'Equipe', id: 'team', icon: Users },
  { label: 'Logs', id: 'audit-logs', icon: ScrollText },
];

const secondaryItems: NavItem[] = [
  { label: 'Configurações', id: 'settings', icon: Settings },
  { label: 'Assinatura', id: 'subscription', icon: CreditCard },
];

export const Sidebar: React.FC<SidebarProps> = ({ currentTab, onSelectTab, isCompact, onToggleCompact }) => {
  const { canAccess, currentUser, workspace, users, approvals } = useGovernance();
  const occupiedSeats = users.filter((user) => user.status !== 'disabled').length;
  const visible = (items: NavItem[]) => currentUser ? items.filter((item) => canAccess(item.id)) : items.filter((item) => item.id === 'dashboard');

  const renderItem = (item: NavItem) => {
    const Icon = item.icon;
    const selected = currentTab === item.id;
    const badge = item.id === 'approvals' ? approvals.filter((approval) => ['in_review', 'pending_approval'].includes(approval.stage)).length : 0;
    return <button key={item.id} type="button" onClick={() => onSelectTab(item.id)} aria-label={item.label} title={isCompact ? item.label : undefined} className={`relative flex w-full items-center rounded-[9px] text-[11px] transition-colors max-[900px]:justify-center max-[900px]:px-2 max-[900px]:py-2.5 ${isCompact ? 'justify-center px-2 py-2.5' : 'gap-3 px-3 py-[8px]'} ${selected ? 'bg-[#21292e] font-medium text-white' : 'text-[#d2d6d9] hover:bg-white/[0.035] hover:text-white'}`}>
      {selected && <span className="absolute inset-y-0 left-0 w-[2px] rounded-full bg-[#8bd132]" />}
      <Icon className={`h-[15px] w-[15px] shrink-0 ${selected ? 'text-[#8bd132]' : 'text-[#c4c9cc]'}`} strokeWidth={1.7} />
      {!isCompact && <span className="min-w-0 flex-1 truncate text-left max-[900px]:hidden">{item.label}</span>}
      {!isCompact && badge > 0 && <span className="grid h-[18px] min-w-[18px] place-items-center rounded-full bg-[#8bd132] px-1 text-[9px] font-bold text-[#14200e] max-[900px]:hidden">{badge}</span>}
    </button>;
  };

  return <aside className={`fixed inset-y-0 left-0 z-40 flex flex-col border-r border-white/[0.075] bg-[#0B0B0B] transition-[width] duration-200 max-[900px]:w-[76px] ${isCompact ? 'w-[76px]' : 'w-[188px] 2xl:w-[226px]'}`}>
    <div className={`flex h-[82px] shrink-0 items-center bg-black max-[900px]:justify-center max-[900px]:px-3 ${isCompact ? 'justify-center px-3' : 'px-5 2xl:px-7'}`}>
      <button type="button" onClick={() => onSelectTab('dashboard')} className="clicko-brand-link flex items-center rounded-sm focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#8bd132]" aria-label="Voltar ao Dashboard" title="Voltar ao Dashboard">
        <ClickoLogo appearance="seamless" variant="icon" className={`clicko-logo-collapsed-size shrink-0 ${isCompact ? 'clicko-logo-force-visible' : 'clicko-logo-compact-responsive'}`} />
        {!isCompact && <ClickoLogo appearance="seamless" className="clicko-logo-full-responsive h-[64px] w-[128px] 2xl:h-[70px] 2xl:w-[140px]" />}
      </button>
    </div>

    <nav className={`custom-scrollbar mt-2 flex-1 overflow-y-auto ${isCompact ? 'px-2.5' : 'px-3.5'}`}>
      <div className="space-y-0.5">{visible(primaryItems).map(renderItem)}</div>
      <div className="my-2.5 border-t border-white/[0.07]" />
      <div className="space-y-0.5">{visible(secondaryItems).map(renderItem)}</div>
    </nav>

    {!isCompact && currentUser?.role === 'master' && <div className="m-3.5 mt-2 rounded-[11px] border border-white/[0.055] bg-[#1b2328] p-3.5 max-[900px]:hidden">
      <div className="text-[11px] font-semibold text-white">Plano {workspace?.planId ? workspace.planId.charAt(0).toUpperCase() + workspace.planId.slice(1) : '—'}</div>
      <div className="mt-2 flex items-center justify-between text-[8px] text-[#c1c7ca]"><span>Assentos usados</span><span>{occupiedSeats} / {workspace?.maxUsers ?? '∞'}</span></div>
      <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-[#30393e]"><div className="h-full rounded-full bg-[#8bd132]" style={{ width: workspace?.maxUsers ? `${Math.min(100, occupiedSeats / workspace.maxUsers * 100)}%` : '32%' }} /></div>
      <button onClick={() => onSelectTab('subscription')} className="mt-3 w-full rounded-md bg-[#8bd132] py-2 text-[9px] font-bold text-[#14200e] transition hover:bg-[#9be24d]">Fazer upgrade</button>
    </div>}

    <button type="button" onClick={onToggleCompact} className="flex h-9 shrink-0 items-center justify-center text-[#69747a] transition-colors hover:text-[#8bd132]" aria-label={isCompact ? 'Expandir barra lateral' : 'Recolher barra lateral'}><ChevronLeft className={`h-[18px] w-[18px] transition-transform duration-200 ${isCompact ? 'rotate-180' : ''}`} /></button>
    <footer className={`vexel-powered-divider relative shrink-0 border-t ${isCompact ? 'px-3 py-3.5' : 'px-4 py-[16px]'}`}>
      {isCompact ? <div className="group relative flex justify-center"><a href="https://vexelbr.com/" target="_blank" rel="noopener noreferrer" title="Powered by VEXEL" className="vexel-powered-signature vexel-powered-mark grid h-8 w-8 place-items-center rounded-lg border" aria-label="Powered by VEXEL"><Box className="h-[17px] w-[17px]" strokeWidth={1.6} /></a><div role="tooltip" className="vexel-powered-tooltip pointer-events-none absolute bottom-0 left-full z-50 ml-3 whitespace-nowrap rounded-md border px-3 py-2 text-[9px] font-medium uppercase tracking-[0.22em] opacity-0 transition-opacity group-hover:opacity-100">Powered by VEXEL</div></div> : <a href="https://vexelbr.com/" target="_blank" rel="noopener noreferrer" title="Powered by VEXEL" className="vexel-powered-signature block text-center text-[8px] font-medium uppercase tracking-[0.3em]"><span>Powered by VEXEL</span></a>}
    </footer>
  </aside>;
};
