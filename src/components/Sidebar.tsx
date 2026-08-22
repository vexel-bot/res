import React from 'react';
import {
  LayoutDashboard, Image, Video, PenLine, CalendarDays, CheckCircle2,
  ChartNoAxesCombined, Bot, Workflow, LayoutTemplate, Link2, Users,
  ScrollText, Settings, CreditCard, ChevronLeft, Box, FolderKanban,
  BrainCircuit, Target, Sparkles, Send
  , Radar, GitBranch, LibraryBig
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
  pathname: string;
  onNavigatePath: (path: string) => void;
}

type NavItem = { label: string; id: NavigationTab; icon: React.ComponentType<{ className?: string }>; path?: string };

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

export const Sidebar: React.FC<SidebarProps> = ({ currentTab, onSelectTab, isCompact, onToggleCompact, pathname, onNavigatePath }) => {
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
            { label: 'Biblioteca', id: 'library', icon: FolderKanban },
            { label: 'Analytics', id: 'analytics', icon: ChartNoAxesCombined },
            { label: 'Templates', id: 'templates', icon: LayoutTemplate },
            { label: 'Histórico', id: 'publisher', icon: ScrollText },
            { label: 'Configurações', id: 'settings', icon: Settings },
          ],
        },
      ]
    : [
        {
          sectionTitle: 'CICLO OPERACIONAL',
          items: [
            { label: 'Dashboard', id: 'dashboard', icon: LayoutDashboard, path: '/dashboard' },
            { label: 'Projetos', id: 'strategy', icon: FolderKanban, path: '/projects' },
            { label: 'Descobrir', id: 'workspace', icon: Radar, path: '/discover' },
            { label: 'Radar', id: 'workspace', icon: Target, path: '/radar' },
          ],
        },
        {
          sectionTitle: 'CRIAÇÃO & MEMÓRIA',
          items: [
            { label: 'Content Command', id: 'library', icon: FolderKanban, path: '/content/dashboard' },
            { label: 'Creative Lab', id: 'studio', icon: Sparkles, path: '/content/dashboard' },
            { label: 'Studio', id: 'studio', icon: Sparkles },
            { label: 'Assets da Marca', id: 'library', icon: LibraryBig, path: '/library/assets' },
            { label: 'Lineage', id: 'library', icon: GitBranch, path: '/library/lineage' },
            { label: 'Copiloto', id: 'ai-chat', icon: Bot },
            { label: 'Memória da Marca', id: 'brain', icon: BrainCircuit },
          ],
        },
        {
          sectionTitle: 'DECISÃO & PERFORMANCE',
          items: [
            { label: 'Aprovações', id: 'approvals', icon: CheckCircle2 },
            { label: 'Calendário', id: 'calendar', icon: CalendarDays },
            { label: 'Publicador', id: 'publisher', icon: Send },
            { label: 'Learning Analytics', id: 'analytics', icon: ChartNoAxesCombined, path: '/analytics/learning' },
          ],
        },
        {
          sectionTitle: 'EQUIPE & GOVERNANÇA',
          items: [
            { label: 'Contas Conectadas', id: 'connected-accounts', icon: Link2 },
            { label: 'Equipe', id: 'team', icon: Users },
            { label: 'Automações', id: 'automations', icon: Workflow },
            { label: 'Governança de IA', id: 'settings', icon: Settings, path: '/settings/ai-governance' },
            { label: 'Auditoria', id: 'audit-logs', icon: ScrollText },
          ],
        },
      ];

  const renderItem = (item: NavItem) => {
    const Icon = item.icon;
    const selected = item.path
      ? pathname === item.path || pathname.startsWith(`${item.path}/`)
      : currentTab === item.id && !pathname.startsWith('/discover') && !pathname.startsWith('/radar');
    const badge = item.id === 'approvals' ? approvals.filter((approval) => ['in_review', 'pending_approval'].includes(approval.stage)).length : 0;
    
    if (currentUser && !canAccess(item.id)) return null;

    return (
      <button
        key={item.id}
        type="button"
        onClick={() => item.path ? onNavigatePath(item.path) : onSelectTab(item.id)}
        aria-label={item.label}
        aria-current={selected ? 'page' : undefined}
        title={isCompact ? item.label : undefined}
        className={`clicko-nav-item group relative flex w-full items-center rounded-lg text-[11px] font-medium transition-colors duration-150 max-[900px]:justify-center max-[900px]:px-2 max-[900px]:py-2.5 ${
          isCompact ? 'justify-center px-2 py-2.5' : 'gap-3 px-3 py-2'
        } ${
          selected
            ? 'bg-white/[0.055] font-semibold text-white'
            : 'text-[#78848c] hover:bg-white/[0.025] hover:text-white'
        }`}
      >
        {selected && (
          <span className="clicko-nav-active-indicator absolute inset-y-2 left-0 w-0.5 rounded-full bg-[#ff5c5c]" />
        )}
        <Icon
          className={`h-[15px] w-[15px] shrink-0 transition-colors ${
            selected ? 'text-[#ff5c5c]' : 'text-[#6c7880] group-hover:text-white'
          }`}
          strokeWidth={selected ? 2.2 : 1.8}
        />
        {!isCompact && (
          <span className="min-w-0 flex-1 truncate text-left max-[900px]:hidden tracking-tight">
            {item.label}
          </span>
        )}
        {!isCompact && badge > 0 && (
          <span className="grid h-4 min-w-[16px] place-items-center rounded-full bg-[#ff5c5c] px-1 text-[9px] font-bold text-[#080e05] max-[900px]:hidden">
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
          className="clicko-brand-link flex items-center rounded-xl transition-all hover:opacity-90 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#ff5c5c]"
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
        <div className="space-y-5">
          {navGroups.map((group, groupIdx) => {
            const hasVisibleItems = group.items.some((item) => !currentUser || canAccess(item.id));
            if (!hasVisibleItems) return null;

            return (
              <div key={group.sectionTitle} className="clicko-nav-group space-y-1">
                {!isCompact && (
                  <div className="clicko-nav-section-label px-3 pb-1.5 text-[8px] font-medium uppercase tracking-[0.22em] text-[#414b51] max-[900px]:hidden">
                    {group.sectionTitle}
                  </div>
                )}
                {groupIdx > 0 && isCompact && <div className="mx-auto my-3 w-6 border-t border-white/[0.05]" />}
                <div className="space-y-0.5">{group.items.map(renderItem)}</div>
              </div>
            );
          })}
        </div>
      </nav>

      {/* Subscription Card Widget */}
      {!isCompact && currentUser?.role === 'master' && (
        <div className="mx-2.5 my-2 border-t border-white/[0.06] px-1 py-3 max-[900px]:hidden">
          <div className="flex items-center justify-between text-xs font-bold text-white">
            <span className="tracking-tight">Plano {workspace?.planId ? ({ solo: 'Solo', team: 'Equipe', business: 'Negócios', enterprise: 'Corporativo' }[workspace.planId] || workspace.planId) : 'Corporativo'}</span>
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#ff5c5c] opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-[#ff5c5c]"></span>
            </span>
          </div>
          <div className="mt-2.5 flex items-center justify-between text-[10px] text-[#717d85]">
            <span>Assentos em uso</span>
            <span className="font-mono font-bold text-white">{occupiedSeats} / {workspace?.maxUsers ?? '12'}</span>
          </div>
          <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-white/[0.06] p-[1px]">
            <div
              className="h-full rounded-full bg-[#ff5c5c] transition-all duration-300"
              style={{ width: workspace?.maxUsers ? `${Math.min(100, (occupiedSeats / workspace.maxUsers) * 100)}%` : '25%' }}
            />
          </div>
          <button
            type="button"
            onClick={() => onSelectTab('subscription')}
            className="mt-3 w-full rounded-md border border-[#ff5c5c]/30 bg-[#ff5c5c]/10 py-2 text-[10px] font-semibold text-[#ff5c5c] transition-colors hover:bg-[#ff5c5c] hover:text-[#080e05]"
          >
            Mudar de Plano
          </button>
        </div>
      )}

      {/* Collapse Toggle */}
      <button
        type="button"
        onClick={onToggleCompact}
        className="flex h-10 shrink-0 items-center justify-center text-[#4d5a62] transition-colors hover:text-[#ff5c5c]"
        aria-label={isCompact ? 'Expandir barra lateral' : 'Recolher barra lateral'}
      >
        <ChevronLeft className={`h-4 w-4 transition-transform duration-300 ${isCompact ? 'rotate-180' : ''}`} />
      </button>

      {/* Footer Branding */}
      <footer className={`vexel-powered-divider relative shrink-0 border-t border-white/[0.05] ${isCompact ? 'px-3 py-3' : 'px-4 py-3.5'}`}>
        {isCompact ? (
          <div className="group relative flex justify-center">
            <a
              href="https://vexelbr.com/"
              target="_blank"
              rel="noopener noreferrer"
              title="Desenvolvido pela VEXEL"
              className="vexel-powered-signature vexel-powered-mark grid h-7 w-7 place-items-center rounded-lg border border-white/10 text-[#717c82] hover:text-[#ff5c5c]"
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
            className="vexel-powered-signature block text-center text-[8px] font-mono font-bold uppercase tracking-[0.3em] text-[#4d5a62] hover:text-[#ff5c5c] transition-colors"
          >
            <span>Desenvolvido pela VEXEL</span>
          </a>
        )}
      </footer>
    </aside>
  );
};

