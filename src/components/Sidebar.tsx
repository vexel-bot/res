import React from 'react';
import {
  LayoutDashboard, Image, Video, PenLine, CalendarDays, CheckCircle2,
  ChartNoAxesCombined, Bot, Workflow, LayoutTemplate, Link2, Users,
  ScrollText, Settings, CreditCard, ChevronLeft, Box, FolderKanban,
  BrainCircuit, Target, Sparkles, Send
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

type NavGroup = {
  sectionTitle: string;
  items: NavItem[];
};

const navGroups: NavGroup[] = [
  {
    sectionTitle: 'OPERAÇÃO',
    items: [
      { label: 'Painel', id: 'dashboard', icon: LayoutDashboard },
      { label: 'Ambiente', id: 'workspace', icon: FolderKanban },
      { label: 'Memória da Marca', id: 'brain', icon: BrainCircuit },
      { label: 'Estratégia', id: 'strategy', icon: Target },
    ],
  },
  {
    sectionTitle: 'CRIAÇÃO COM IA',
    items: [
      { label: 'Estúdio Unificado', id: 'studio', icon: Sparkles },
      { label: 'Criar Imagem', id: 'create-image', icon: Image },
      { label: 'Criar Vídeo', id: 'create-video', icon: Video },
      { label: 'Criar Texto', id: 'create-copy', icon: PenLine },
      { label: 'Chat com IA', id: 'ai-chat', icon: Bot },
    ],
  },
  {
    sectionTitle: 'PUBLICAÇÃO & PERFORMANCE',
    items: [
      { label: 'Calendário', id: 'calendar', icon: CalendarDays },
      { label: 'Publicador', id: 'publisher', icon: Send },
      { label: 'Aprovações', id: 'approvals', icon: CheckCircle2 },
      { label: 'Análises', id: 'analytics', icon: ChartNoAxesCombined },
      { label: 'Biblioteca', id: 'library', icon: FolderKanban },
      { label: 'Modelos', id: 'templates', icon: LayoutTemplate },
      { label: 'Automações', id: 'automations', icon: Workflow },
    ],
  },
  {
    sectionTitle: 'GOVERNANÇA & EQUIPE',
    items: [
      { label: 'Contas Conectadas', id: 'connected-accounts', icon: Link2 },
      { label: 'Equipe', id: 'team', icon: Users },
      { label: 'Registros de Auditoria', id: 'audit-logs', icon: ScrollText },
      { label: 'Assinatura', id: 'subscription', icon: CreditCard },
      { label: 'Configurações', id: 'settings', icon: Settings },
    ],
  },
];

export const Sidebar: React.FC<SidebarProps> = ({ currentTab, onSelectTab, isCompact, onToggleCompact }) => {
  const { canAccess, currentUser, workspace, users, approvals, environmentMode } = useGovernance();
  const occupiedSeats = users.filter((user) => user.status !== 'disabled').length;
  const isPersonal = environmentMode === 'personal';

  const navGroups: NavGroup[] = isPersonal
    ? [
        {
          sectionTitle: 'MEU STUDIO PESSOAL',
          items: [
            { label: 'Dashboard', id: 'dashboard', icon: LayoutDashboard },
            { label: 'Studio', id: 'studio', icon: Sparkles },
            { label: 'Central IA', id: 'ai-chat', icon: Bot },
            { label: 'Biblioteca da Marca', id: 'brain', icon: BrainCircuit },
          ],
        },
        {
          sectionTitle: 'PUBLICAÇÃO & PERFORMANCE',
          items: [
            { label: 'Contas Conectadas', id: 'connected-accounts', icon: Link2 },
            { label: 'Calendário', id: 'calendar', icon: CalendarDays },
            { label: 'Analytics', id: 'analytics', icon: ChartNoAxesCombined },
            { label: 'Templates', id: 'templates', icon: LayoutTemplate },
            { label: 'Histórico', id: 'publisher', icon: ScrollText },
            { label: 'Configurações', id: 'settings', icon: Settings },
          ],
        },
      ]
    : [
        {
          sectionTitle: 'OPERAÇÃO CORPORATIVA',
          items: [
            { label: 'Dashboard', id: 'dashboard', icon: LayoutDashboard },
            { label: 'Studio', id: 'studio', icon: Sparkles },
            { label: 'Central IA', id: 'ai-chat', icon: Bot },
            { label: 'Clientes', id: 'workspace', icon: FolderKanban },
            { label: 'Biblioteca da Marca', id: 'brain', icon: BrainCircuit },
          ],
        },
        {
          sectionTitle: 'PUBLICAÇÃO & GOVERNANÇA',
          items: [
            { label: 'Contas Conectadas', id: 'connected-accounts', icon: Link2 },
            { label: 'Calendário', id: 'calendar', icon: CalendarDays },
            { label: 'Aprovações', id: 'approvals', icon: CheckCircle2 },
            { label: 'Analytics', id: 'analytics', icon: ChartNoAxesCombined },
            { label: 'Templates', id: 'templates', icon: LayoutTemplate },
            { label: 'Automações', id: 'automations', icon: Workflow },
          ],
        },
        {
          sectionTitle: 'EQUIPE & GOVERNANÇA',
          items: [
            { label: 'Equipe', id: 'team', icon: Users },
            { label: 'Logs', id: 'audit-logs', icon: ScrollText },
            { label: 'Histórico', id: 'publisher', icon: Send },
            { label: 'Configurações', id: 'settings', icon: Settings },
          ],
        },
      ];

  const renderItem = (item: NavItem) => {
    const Icon = item.icon;
    const selected = currentTab === item.id;
    const badge = item.id === 'approvals' ? approvals.filter((approval) => ['in_review', 'pending_approval'].includes(approval.stage)).length : 0;
    
    if (currentUser && !canAccess(item.id)) return null;

    return (
      <button
        key={item.id}
        type="button"
        onClick={() => onSelectTab(item.id)}
        aria-label={item.label}
        title={isCompact ? item.label : undefined}
        className={`group relative flex w-full items-center rounded-xl text-xs font-semibold transition-all duration-150 max-[900px]:justify-center max-[900px]:px-2.5 max-[900px]:py-2.5 ${
          isCompact ? 'justify-center px-2.5 py-2.5' : 'gap-3 px-3.5 py-2.5'
        } ${
          selected
            ? 'bg-[#8bd132]/10 text-white shadow-sm border border-[#8bd132]/20 font-bold'
            : 'text-[#78848c] hover:bg-white/[0.04] hover:text-white border border-transparent'
        }`}
      >
        {selected && (
          <span className="absolute inset-y-1.5 left-0 w-[3px] rounded-r-full bg-[#8bd132] shadow-[0_0_10px_#8bd132]" />
        )}
        <Icon
          className={`h-4 w-4 shrink-0 transition-colors ${
            selected ? 'text-[#8bd132]' : 'text-[#6c7880] group-hover:text-white'
          }`}
          strokeWidth={selected ? 2.2 : 1.8}
        />
        {!isCompact && (
          <span className="min-w-0 flex-1 truncate text-left max-[900px]:hidden tracking-tight">
            {item.label}
          </span>
        )}
        {!isCompact && badge > 0 && (
          <span className="grid h-4 min-w-[16px] place-items-center rounded-full bg-[#8bd132] px-1 text-[9px] font-bold text-[#080e05] max-[900px]:hidden">
            {badge}
          </span>
        )}
      </button>
    );
  };

  return (
    <aside
      className={`fixed inset-y-0 left-0 z-40 flex flex-col border-r border-white/[0.06] bg-[#000000] backdrop-blur-2xl transition-[width] duration-200 max-[900px]:w-[76px] ${
        isCompact ? 'w-[76px]' : 'w-[210px] 2xl:w-[240px]'
      }`}
    >
      {/* Header Logo Area - Seamlessly matching Clicko AI Studios Logo background */}
      <div
        className={`flex h-[76px] shrink-0 items-center border-b border-white/[0.06] bg-[#000000] max-[900px]:justify-center max-[900px]:px-3 ${
          isCompact ? 'justify-center px-3' : 'px-5 2xl:px-6'
        }`}
      >
        <button
          type="button"
          onClick={() => onSelectTab('dashboard')}
          className="clicko-brand-link flex items-center rounded-md focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#8bd132]"
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
              className="clicko-logo-full-responsive h-[60px] w-[124px] 2xl:h-[66px] 2xl:w-[136px]"
            />
          )}
        </button>
      </div>

      {/* Navigation Group Scroll */}
      <nav className={`custom-scrollbar flex-1 overflow-y-auto py-4 ${isCompact ? 'px-2' : 'px-3'}`}>
        <div className="space-y-5">
          {navGroups.map((group, groupIdx) => {
            const hasVisibleItems = group.items.some((item) => !currentUser || canAccess(item.id));
            if (!hasVisibleItems) return null;

            return (
              <div key={group.sectionTitle} className="space-y-1">
                {!isCompact && (
                  <div className="px-3 pb-1.5 text-[9px] font-bold uppercase tracking-[0.2em] text-[#525e66] max-[900px]:hidden">
                    {group.sectionTitle}
                  </div>
                )}
                {groupIdx > 0 && isCompact && <div className="mx-auto my-2 w-6 border-t border-white/[0.06]" />}
                <div className="space-y-0.5">{group.items.map(renderItem)}</div>
              </div>
            );
          })}
        </div>
      </nav>

      {/* Subscription Card Widget */}
      {!isCompact && currentUser?.role === 'master' && (
        <div className="mx-3 my-2 rounded-2xl border border-white/[0.06] bg-[#0c1015] p-3.5 max-[900px]:hidden shadow-xl shadow-black/40">
          <div className="flex items-center justify-between text-xs font-bold text-white">
            <span>Plano {workspace?.planId ? ({ solo: 'Solo', team: 'Equipe', business: 'Negócios', enterprise: 'Corporativo' }[workspace.planId] || workspace.planId) : 'Corporativo'}</span>
            <span className="h-2 w-2 rounded-full bg-[#8bd132] animate-pulse" />
          </div>
          <div className="mt-2 flex items-center justify-between text-[10px] text-[#78848c]">
            <span>Assentos</span>
            <span className="font-semibold text-white">{occupiedSeats} / {workspace?.maxUsers ?? '12'}</span>
          </div>
          <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-white/[0.06]">
            <div
              className="h-full rounded-full bg-[#8bd132]"
              style={{ width: workspace?.maxUsers ? `${Math.min(100, (occupiedSeats / workspace.maxUsers) * 100)}%` : '25%' }}
            />
          </div>
          <button
            type="button"
            onClick={() => onSelectTab('subscription')}
            className="mt-3 w-full rounded-xl bg-[#8bd132] py-2 text-xs font-bold text-[#080e05] transition hover:bg-[#9be24d]"
          >
            Mudar de Plano
          </button>
        </div>
      )}

      {/* Collapse Toggle */}
      <button
        type="button"
        onClick={onToggleCompact}
        className="flex h-10 shrink-0 items-center justify-center text-[#525e66] transition-colors hover:text-[#8bd132]"
        aria-label={isCompact ? 'Expandir barra lateral' : 'Recolher barra lateral'}
      >
        <ChevronLeft className={`h-4 w-4 transition-transform duration-200 ${isCompact ? 'rotate-180' : ''}`} />
      </button>

      {/* Footer Branding */}
      <footer className={`vexel-powered-divider relative shrink-0 border-t border-white/[0.06] ${isCompact ? 'px-3 py-3' : 'px-4 py-3'}`}>
        {isCompact ? (
          <div className="group relative flex justify-center">
            <a
              href="https://vexelbr.com/"
              target="_blank"
              rel="noopener noreferrer"
              title="Desenvolvido pela VEXEL"
              className="vexel-powered-signature vexel-powered-mark grid h-7 w-7 place-items-center rounded-lg border border-white/10 text-[#717c82] hover:text-[#8bd132]"
              aria-label="Desenvolvido pela VEXEL"
            >
              <Box className="h-3.5 w-3.5" strokeWidth={1.6} />
            </a>
            <div role="tooltip" className="vexel-powered-tooltip pointer-events-none absolute bottom-0 left-full z-50 ml-3 whitespace-nowrap rounded-md border px-2.5 py-1.5 text-[9px] font-medium uppercase tracking-[0.2em] opacity-0 transition-opacity group-hover:opacity-100">
              Desenvolvido pela VEXEL
            </div>
          </div>
        ) : (
          <a
            href="https://vexelbr.com/"
            target="_blank"
            rel="noopener noreferrer"
            title="Desenvolvido pela VEXEL"
            className="vexel-powered-signature block text-center text-[8px] font-bold uppercase tracking-[0.28em] text-[#525e66] hover:text-[#8bd132]"
          >
            <span>Desenvolvido pela VEXEL</span>
          </a>
        )}
      </footer>
    </aside>
  );
};

