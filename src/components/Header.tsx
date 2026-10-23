import React from 'react';
import { usePresence } from '../motion/usePresence';
import { Bell, ChevronDown, Search, Building2, User, Check, Plus, Trash2, LogOut, AlertTriangle, CalendarClock, ClipboardCheck, Link2 } from 'lucide-react';
import { NavigationTab, Workspace } from '../types';
import { useGovernance } from '../context/GovernanceContext';
import { useOperations } from '../context/OperationsContext';
import { AddAccountModal } from './AddAccountModal';
import { useAuth } from '../context/AuthContext';
import { ProfileAvatar } from './ProfileAvatar';
import { DevEnvironmentBadge } from '../development/DevEnvironmentBadge';

interface HeaderProps {
  currentTab: NavigationTab;
  activeWorkspace: Workspace;
  onOpenSpotlight: () => void;
  onOpenAICentral: () => void;
  onNewPost: () => void;
  isCompact: boolean;
  onToggleCompact: () => void;
  onNavigate: (tab: NavigationTab) => void;
}

type OperationalNotification = {
  id: string;
  level: 'critical' | 'action' | 'info';
  title: string;
  description: string;
  count: number;
  destination: NavigationTab;
  icon: React.ReactNode;
};

export const Header: React.FC<HeaderProps> = ({ onOpenSpotlight, onNavigate }) => {
  const auth = useAuth();
  const { posts, connectedAccounts } = useOperations();
  const [showNotifications, setShowNotifications] = React.useState(false);
  const [showPlanMenu, setShowPlanMenu] = React.useState(false);
  const [showAddAccountModal, setShowAddAccountModal] = React.useState(false);
  const notificationsPresence = usePresence(showNotifications);
  const profilePresence = usePresence(showPlanMenu);

  const {
    approvals,
    accounts,
    activeAccount,
    currentUser,
    canAccess,
    switchAccount,
    removeAccount,
  } = useGovernance();

  const pendingApprovals = approvals.filter((item) => ['in_review', 'pending_approval'].includes(item.stage)).length;
  const failedPublications = posts.filter((post) => post.status === 'error' || Boolean(post.publicationError)).length;
  const connectionIssues = connectedAccounts.filter((account) => ['expired', 'permission_insufficient', 'authorization_revoked', 'sync_error', 'error'].includes(account.connectionStatus || '')).length;
  const todayKey = new Date().toLocaleDateString('en-CA');
  const scheduledToday = posts.filter((post) => post.status === 'scheduled' && post.scheduledAt?.slice(0, 10) === todayKey).length;
  const notifications = React.useMemo<OperationalNotification[]>(() => {
    const items: OperationalNotification[] = [];
    if (failedPublications > 0 && canAccess('calendar')) items.push({
      id: 'publication-failures', level: 'critical', title: 'Falhas de publicação',
      description: `${failedPublications} conteúdo(s) precisam de correção antes de uma nova tentativa.`,
      count: failedPublications, destination: 'calendar', icon: <AlertTriangle className="h-4 w-4" />,
    });
    if (connectionIssues > 0 && canAccess('connected-accounts')) items.push({
      id: 'connection-issues', level: 'action', title: 'Conexões exigem atenção',
      description: `${connectionIssues} conta(s) com autorização, permissão ou sincronização pendente.`,
      count: connectionIssues, destination: 'connected-accounts', icon: <Link2 className="h-4 w-4" />,
    });
    if (pendingApprovals > 0 && canAccess('approvals')) items.push({
      id: 'pending-approvals', level: 'action', title: 'Fila de revisão',
      description: `${pendingApprovals} conteúdo(s) aguardando sua autorização final.`,
      count: pendingApprovals, destination: 'approvals', icon: <ClipboardCheck className="h-4 w-4" />,
    });
    if (scheduledToday > 0 && canAccess('calendar')) items.push({
      id: 'scheduled-today', level: 'info', title: 'Agenda de hoje',
      description: `${scheduledToday} conteúdo(s) programado(s) para hoje.`,
      count: scheduledToday, destination: 'calendar', icon: <CalendarClock className="h-4 w-4" />,
    });
    return items;
  }, [canAccess, connectionIssues, failedPublications, pendingApprovals, scheduledToday]);
  const actionableCount = notifications.filter((item) => item.level !== 'info').reduce((total, item) => total + item.count, 0);

  const planDropdownRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (planDropdownRef.current && !planDropdownRef.current.contains(event.target as Node)) {
        setShowPlanMenu(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelectAccount = (accountId: string) => {
    switchAccount(accountId);
    setShowPlanMenu(false);
  };

  const isCompany = activeAccount?.type === 'company';
  const profileName = currentUser?.name || (isCompany ? 'Usuário' : activeAccount?.name) || 'Usuário';

  return (
    <header className="clicko-topbar sticky top-2 z-30 mx-3 mt-2 flex h-[56px] items-center justify-between rounded-2xl border border-white/[0.06] px-3.5 lg:mx-4 lg:px-4 2xl:mx-5">
      {/* Search & Navigation Bar - Left */}
      <div className="flex min-w-0 items-center gap-4">
        {/* Global Command Search Bar */}
        <button
          type="button"
          onClick={onOpenSpotlight}
          className="clicko-command-search group flex h-9 w-[420px] max-w-[42vw] items-center justify-between gap-3 rounded-xl border border-white/[0.06] bg-transparent px-3.5 text-[#808080] transition-colors hover:border-white/15 hover:bg-white/[0.025] hover:text-white max-[900px]:w-9 max-[900px]:px-2.5"
        >
          <div className="flex items-center gap-3 min-w-0">
            <Search className="h-4 w-4 shrink-0 text-[#808080] group-hover:text-[#FF7F50] transition-colors" />
            <span className="truncate text-xs font-medium max-[900px]:hidden">Buscar no workspace, conteúdos ou KLIC...</span>
          </div>
        </button>
      </div>

      {/* Right Action Bar with Profile / Account Switcher */}
      <div className="flex items-center gap-2.5">
        <DevEnvironmentBadge />
        {/* Notifications Button */}
        <div className="relative">
          <button
            type="button"
            onClick={() => setShowNotifications((value) => !value)}
            className="relative grid h-9 w-9 place-items-center rounded-xl border border-white/[0.06] bg-transparent text-[#808080] transition-colors hover:border-white/15 hover:bg-white/[0.025] hover:text-white"
            aria-label="Notificações"
            aria-expanded={showNotifications}
          >
            <Bell className="h-4 w-4" />
            {actionableCount > 0 && (
              <span className="absolute -right-1 -top-1 grid h-4 min-w-[16px] place-items-center rounded-full bg-[#FF7F50] px-1 text-[9px] font-bold text-[#000000]">
                {actionableCount > 99 ? '99+' : actionableCount}
              </span>
            )}
          </button>
          {notificationsPresence.present && (
            <div {...notificationsPresence.props} className="clicko-notification-panel absolute right-0 top-12 z-50 w-80 max-w-[calc(100vw-24px)] rounded-xl border border-white/10 bg-[rgba(128,128,128,0.14)]/95 p-4 shadow-xl shadow-black/40 backdrop-blur-sm animate-in fade-in zoom-in-95 duration-150">
              <div className="mb-3 flex items-center justify-between border-b border-white/[0.06] pb-2.5">
                <span className="text-xs font-bold text-white tracking-tight">Central de Notificações</span>
                <span className="text-[10px] text-[#FF7F50] font-semibold">{actionableCount} exigem atenção</span>
              </div>
              <div className="space-y-2 text-xs text-[rgba(255,255,255,0.72)]">
                {notifications.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => { setShowNotifications(false); onNavigate(item.destination); }}
                    className={`clicko-notification-item flex w-full gap-3 rounded-xl border p-3 text-left transition ${item.level === 'critical' ? 'border-[#FF7F50]/35 bg-[#FF7F50]/[0.08]' : 'border-white/[0.06] bg-[#000000]'}`}
                  >
                    <span className={item.level === 'critical' ? 'text-[#FF7F50]' : item.level === 'action' ? 'text-[#F28500]' : 'text-[#808080]'}>{item.icon}</span>
                    <span className="min-w-0 flex-1">
                      <span className="mb-0.5 block font-semibold text-white">{item.title}</span>
                      <span className="block leading-relaxed">{item.description}</span>
                    </span>
                    <span className="text-[10px] font-bold text-[#FF7F50]">{item.count}</span>
                  </button>
                ))}
                {notifications.length === 0 && <div className="rounded-xl border border-white/[0.06] bg-[#000000] p-3"><span className="font-semibold text-white block mb-0.5">Operação em dia</span>Não há eventos operacionais pendentes neste Perfil/Workspace.</div>}
              </div>
            </div>
          )}
        </div>

        {/* Profile / Account Switcher Component */}
        <div className="relative" ref={planDropdownRef}>
          <button
            type="button"
            onClick={() => setShowPlanMenu((v) => !v)}
            className="group flex h-9 items-center gap-2.5 rounded-xl border border-white/[0.06] bg-transparent px-2.5 text-left transition-colors hover:border-white/15 hover:bg-white/[0.025]"
            aria-label="Seletor de Perfis"
            aria-expanded={showPlanMenu}
            title="Seletor de Perfis"
          >
            <div
              className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-lg ${
                isCompany
                  ? 'bg-[#FF7F50]/20 text-[#FF7F50] border border-[#FF7F50]/30'
                  : 'bg-[#FF7F50]/20 text-[#FF7F50] border border-[#FF7F50]/30'
              }`}
            >
              <ProfileAvatar src={activeAccount?.avatar} alt="Foto de perfil" className="h-full w-full" fallback={isCompany ? <Building2 className="h-3.5 w-3.5" /> : <User className="h-3.5 w-3.5" />} />
            </div>

            <div className="clicko-profile-copy flex min-w-0 flex-col">
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold tracking-tight text-white truncate max-w-[130px]">
                  {profileName}
                </span>
                <span className="h-1.5 w-1.5 rounded-full bg-[#FF7F50]" />
              </div>
              <span className="truncate text-[10px] text-[#808080]">
                {isCompany ? 'Corporativo' : 'Pessoal'}
              </span>
            </div>

            <ChevronDown
              className={`h-4 w-4 text-[#808080] transition-transform duration-200 ${
                showPlanMenu ? 'rotate-180 text-white' : 'group-hover:text-white'
              }`}
            />
          </button>

          {/* Account Switcher Dropdown Menu */}
          {profilePresence.present && (
            <div {...profilePresence.props} id="clicko-profile-menu" className="absolute right-0 top-12 z-50 w-80 max-w-[calc(100vw-24px)] rounded-xl border border-white/10 p-3.5 shadow-xl shadow-black/40 animate-in fade-in zoom-in-95 duration-150">
              <div className="px-2.5 py-2 border-b border-white/[0.06] mb-2.5 flex items-center justify-between">
                <span className="text-[10px] font-bold uppercase tracking-wider text-[#808080]">
                  Seletor de Perfis
                </span>
                <span className="text-[9px] text-[#FF7F50] font-semibold flex items-center gap-1.5 bg-[#FF7F50]/10 border border-[#FF7F50]/30 px-2 py-0.5 rounded-md">
                  <span className="h-1.5 w-1.5 rounded-full bg-[#FF7F50] animate-pulse" />
                  Ativo
                </span>
              </div>

              {/* List of Accounts */}
              <div className="space-y-2 max-h-[300px] overflow-y-auto custom-scrollbar pr-0.5">
                {accounts.map((acc) => {
                  const isActive = acc.id === activeAccount?.id;
                  const isAccCompany = acc.type === 'company';

                  return (
                    <div key={acc.id} className="group/item relative">
                      <button
                        type="button"
                        onClick={() => handleSelectAccount(acc.id)}
                        className={`w-full flex items-start gap-3 rounded-xl p-3 text-left transition-all ${
                          isActive
                            ? isAccCompany
                              ? 'bg-[#FF7F50]/40 border border-[#FF7F50]/40 text-white shadow-lg'
                              : 'bg-[#FF7F50]/10 border border-[#FF7F50]/40 text-white shadow-lg'
                            : 'hover:bg-white/[0.04] border border-transparent text-[#808080] hover:text-white'
                        }`}
                      >
                        <div
                          className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl ${
                            isAccCompany
                              ? isActive ? 'bg-[#FF7F50] text-white shadow-md' : 'bg-[#000000] text-[#808080]'
                              : isActive ? 'bg-[#FF7F50] text-[#000000] shadow-md' : 'bg-[#000000] text-[#808080]'
                          }`}
                        >
                          <ProfileAvatar src={acc.avatar} alt="Foto de perfil" className="h-full w-full" fallback={isAccCompany ? <Building2 className="h-4 w-4" /> : <User className="h-4 w-4" />} />
                        </div>

                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between pr-4">
                            <span className="text-xs font-bold text-white truncate max-w-[160px]">
                              {acc.name}
                            </span>
                            {isActive && (
                              <span className="flex items-center gap-1 text-[10px] font-bold text-[#FF7F50]">
                                <Check className="h-3.5 w-3.5" />
                              </span>
                            )}
                          </div>
                          <p className="text-[10px] text-[#808080] line-clamp-1 mt-0.5">
                            {acc.planName || (isAccCompany ? 'Plano Corporativo' : 'Plano Solo')}
                          </p>
                          <div className="mt-1.5 flex items-center gap-2">
                            <span
                              className={`rounded-md px-1.5 py-0.2 text-[8px] font-bold uppercase border ${
                                isAccCompany
                                  ? 'bg-[#FF7F50]/20 text-[#FF7F50] border-[#FF7F50]/30'
                                  : 'bg-[#FF7F50]/20 text-[#FF7F50] border-[#FF7F50]/30'
                              }`}
                            >
                              {isAccCompany ? 'Workspace' : 'Pessoal'}
                            </span>
                            {acc.membersCount ? (
                              <span className="text-[9px] text-[#808080]">{acc.membersCount} Membros</span>
                            ) : (
                              <span className="text-[9px] text-[#808080]">{acc.role || 'Solo Creator'}</span>
                            )}
                          </div>
                        </div>
                      </button>

                      {/* Optional Remove button if user has > 1 account */}
                      {accounts.length > 1 && (
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            removeAccount(acc.id);
                          }}
                          className="absolute right-2 top-2 hidden h-6 w-6 place-items-center rounded-md bg-[#FF7F50]/10 text-[#FF7F50] hover:bg-[#FF7F50]/20 group-hover/item:grid"
                          title="Remover conta do seletor"
                        >
                          <Trash2 className="h-3 w-3" />
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>

              {/* Botão Adicionar Conta */}
              <div className="mt-3 border-t border-white/[0.06] pt-2.5">
                <button
                  type="button"
                  onClick={() => {
                    setShowPlanMenu(false);
                    setShowAddAccountModal(true);
                  }}
                  className="flex w-full items-center justify-center gap-2 rounded-xl border border-dashed border-white/15 bg-white/[0.03] py-2.5 text-xs font-semibold text-white transition hover:border-[#FF7F50]/50 hover:bg-[#FF7F50]/10 hover:text-[#FF7F50]"
                >
                  <Plus className="h-4 w-4 text-[#FF7F50]" />
                  <span>Adicionar conta</span>
                </button>
                <button
                  type="button"
                  onClick={() => { setShowPlanMenu(false); void auth.logout(); }}
                  className="clicko-sign-out mt-2 flex w-full items-center justify-center gap-2 rounded-xl py-2.5 text-xs text-[#808080] transition hover:bg-white/[0.03] hover:text-white"
                >
                  <LogOut className="h-4 w-4" /> Sair da Clicko
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Add Account Modal */}
      <AddAccountModal
        isOpen={showAddAccountModal}
        onClose={() => setShowAddAccountModal(false)}
      />
    </header>
  );
};

