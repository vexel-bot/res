import React from 'react';
import { Bell, CircleHelp, ChevronDown, Search, Building2, User, Check, Plus, Trash2 } from 'lucide-react';
import { NavigationTab, Workspace } from '../types';
import { useGovernance } from '../context/GovernanceContext';
import { AddAccountModal } from './AddAccountModal';

interface HeaderProps {
  currentTab: NavigationTab;
  activeWorkspace: Workspace;
  onOpenSpotlight: () => void;
  onOpenAICentral: () => void;
  onNewPost: () => void;
  isCompact: boolean;
  onToggleCompact: () => void;
  isDarkMode: boolean;
  onToggleDarkMode: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onOpenSpotlight }) => {
  const [showNotifications, setShowNotifications] = React.useState(false);
  const [showPlanMenu, setShowPlanMenu] = React.useState(false);
  const [showAddAccountModal, setShowAddAccountModal] = React.useState(false);

  const {
    approvals,
    accounts,
    activeAccount,
    switchAccount,
    removeAccount,
  } = useGovernance();

  const pendingApprovals = approvals.filter((item) => ['in_review', 'pending_approval'].includes(item.stage)).length;

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

  return (
    <header className="sticky top-0 z-30 flex h-[76px] items-center justify-between border-b border-white/[0.05] bg-[#070a0d]/90 px-8 backdrop-blur-2xl 2xl:px-12">
      {/* Search & Navigation Bar - Left */}
      <div className="flex min-w-0 items-center gap-4">
        {/* Global Command Search Bar */}
        <button
          type="button"
          onClick={onOpenSpotlight}
          className="group flex h-10 w-[420px] max-w-[40vw] items-center justify-between gap-3 rounded-xl border border-white/[0.07] bg-[#0c1015]/80 px-4 text-[#717d85] transition-all hover:border-white/20 hover:bg-[#11161c] hover:text-white max-[900px]:w-10 max-[900px]:px-2.5 shadow-sm"
        >
          <div className="flex items-center gap-3 min-w-0">
            <Search className="h-4 w-4 shrink-0 text-[#5a6770] group-hover:text-[#8bd132] transition-colors" />
            <span className="truncate text-xs font-medium max-[900px]:hidden">Buscar no workspace, conteúdos, IA...</span>
          </div>
          <kbd className="hidden sm:inline-flex items-center gap-1 rounded-md border border-white/10 bg-white/[0.04] px-2 py-0.5 text-[10px] font-mono font-bold text-[#627078]">
            ⌘K
          </kbd>
        </button>
      </div>

      {/* Right Action Bar with Profile / Account Switcher */}
      <div className="flex items-center gap-3.5">
        {/* Notifications Button */}
        <div className="relative">
          <button
            type="button"
            onClick={() => setShowNotifications((value) => !value)}
            className="relative grid h-10 w-10 place-items-center rounded-xl border border-white/[0.07] bg-[#0c1015]/80 text-[#a2adba] transition-all hover:border-white/20 hover:bg-[#11161c] hover:text-white"
            aria-label="Notificações"
          >
            <Bell className="h-4 w-4" />
            {pendingApprovals > 0 && (
              <span className="absolute -right-1 -top-1 grid h-4 min-w-[16px] place-items-center rounded-full bg-[#8bd132] px-1 text-[9px] font-bold text-[#080e05] shadow-[0_0_10px_rgba(139,209,50,0.5)]">
                {pendingApprovals}
              </span>
            )}
          </button>
          {showNotifications && (
            <div className="absolute right-0 top-12 w-80 rounded-2xl border border-white/10 bg-[#0d1217]/95 p-4 shadow-2xl backdrop-blur-2xl z-50 animate-in fade-in zoom-in-95 duration-150">
              <div className="mb-3 flex items-center justify-between border-b border-white/[0.06] pb-2.5">
                <span className="text-xs font-bold text-white tracking-tight">Central de Notificações</span>
                <span className="text-[10px] text-[#8bd132] font-semibold">{pendingApprovals} pendentes</span>
              </div>
              <div className="space-y-2.5 text-xs text-[#a0abb2]">
                {pendingApprovals > 0 && (
                  <div className="rounded-xl border border-white/[0.06] bg-[#07090c] p-3">
                    <span className="font-semibold text-white block mb-0.5">Fila de Revisão</span>
                    {pendingApprovals} conteúdo(s) aguardando sua autorização final.
                  </div>
                )}
                <div className="rounded-xl border border-white/[0.06] bg-[#07090c] p-3">
                  <span className="font-semibold text-white block mb-0.5">Campanha em Alta</span>
                  Sua estratégia de conteúdo registrou crescimento de +14.5% em alcance.
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Help Button */}
        <button
          type="button"
          className="grid h-10 w-10 place-items-center rounded-xl border border-white/[0.07] bg-[#0c1015]/80 text-[#a2adba] transition-all hover:border-white/20 hover:bg-[#11161c] hover:text-white max-[700px]:hidden"
          aria-label="Ajuda"
        >
          <CircleHelp className="h-4 w-4" />
        </button>

        {/* Profile / Account Switcher Component */}
        <div className="relative" ref={planDropdownRef}>
          <button
            type="button"
            onClick={() => setShowPlanMenu((v) => !v)}
            className="group flex h-10 items-center gap-3 rounded-xl border border-white/[0.07] bg-[#0c1015]/80 px-3.5 text-left transition-all hover:border-white/20 hover:bg-[#11161c]"
            aria-label="Seletor de Perfis"
            title="Seletor de Perfis"
          >
            <div
              className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-lg ${
                isCompany
                  ? 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30'
                  : 'bg-[#8bd132]/20 text-[#8bd132] border border-[#8bd132]/30'
              }`}
            >
              {isCompany ? <Building2 className="h-3.5 w-3.5" /> : <User className="h-3.5 w-3.5" />}
            </div>

            <div className="flex flex-col min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold tracking-tight text-white truncate max-w-[130px]">
                  {activeAccount?.name || 'Selecione a Conta'}
                </span>
                <span className="h-1.5 w-1.5 rounded-full bg-[#8bd132] shadow-[0_0_8px_#8bd132]" />
              </div>
              <span className="truncate text-[10px] text-[#717d85]">
                {isCompany ? 'Workspace Corporativo' : 'Workspace Pessoal'}
              </span>
            </div>

            <ChevronDown
              className={`h-4 w-4 text-[#5a6770] transition-transform duration-200 ${
                showPlanMenu ? 'rotate-180 text-white' : 'group-hover:text-white'
              }`}
            />
          </button>

          {/* Account Switcher Dropdown Menu */}
          {showPlanMenu && (
            <div className="absolute right-0 top-12 z-50 w-80 rounded-2xl border border-white/10 bg-[#0d1217] p-3.5 shadow-2xl backdrop-blur-2xl animate-in fade-in zoom-in-95 duration-150">
              <div className="px-2.5 py-2 border-b border-white/[0.06] mb-2.5 flex items-center justify-between">
                <span className="text-[10px] font-bold uppercase tracking-wider text-[#6c7880]">
                  Seletor de Perfis
                </span>
                <span className="text-[9px] text-[#8bd132] font-semibold flex items-center gap-1.5 bg-[#8bd132]/10 border border-[#8bd132]/30 px-2 py-0.5 rounded-md">
                  <span className="h-1.5 w-1.5 rounded-full bg-[#8bd132] animate-pulse" />
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
                              ? 'bg-indigo-950/40 border border-indigo-500/40 text-white shadow-lg'
                              : 'bg-[#8bd132]/10 border border-[#8bd132]/40 text-white shadow-lg'
                            : 'hover:bg-white/[0.04] border border-transparent text-[#808c94] hover:text-white'
                        }`}
                      >
                        <div
                          className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl ${
                            isAccCompany
                              ? isActive ? 'bg-indigo-500 text-white shadow-md' : 'bg-[#182028] text-[#808c94]'
                              : isActive ? 'bg-[#8bd132] text-[#080e05] shadow-md' : 'bg-[#182028] text-[#808c94]'
                          }`}
                        >
                          {isAccCompany ? <Building2 className="h-4 w-4" /> : <User className="h-4 w-4" />}
                        </div>

                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between pr-4">
                            <span className="text-xs font-bold text-white truncate max-w-[160px]">
                              {acc.name}
                            </span>
                            {isActive && (
                              <span className="flex items-center gap-1 text-[10px] font-bold text-[#8bd132]">
                                <Check className="h-3.5 w-3.5" />
                              </span>
                            )}
                          </div>
                          <p className="text-[10px] text-[#78848c] line-clamp-1 mt-0.5">
                            {acc.planName || (isAccCompany ? 'Plano Corporativo' : 'Plano Solo')}
                          </p>
                          <div className="mt-1.5 flex items-center gap-2">
                            <span
                              className={`rounded-md px-1.5 py-0.2 text-[8px] font-bold uppercase border ${
                                isAccCompany
                                  ? 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30'
                                  : 'bg-[#8bd132]/20 text-[#8bd132] border-[#8bd132]/30'
                              }`}
                            >
                              {isAccCompany ? 'Workspace' : 'Pessoal'}
                            </span>
                            {acc.membersCount ? (
                              <span className="text-[9px] text-[#6c7880]">{acc.membersCount} Membros</span>
                            ) : (
                              <span className="text-[9px] text-[#6c7880]">{acc.role || 'Solo Creator'}</span>
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
                          className="absolute right-2 top-2 hidden h-6 w-6 place-items-center rounded-md bg-red-500/10 text-red-400 hover:bg-red-500/20 group-hover/item:grid"
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
                  className="flex w-full items-center justify-center gap-2 rounded-xl border border-dashed border-white/15 bg-white/[0.03] py-2.5 text-xs font-semibold text-white transition hover:border-[#8bd132]/50 hover:bg-[#8bd132]/10 hover:text-[#8bd132]"
                >
                  <Plus className="h-4 w-4 text-[#8bd132]" />
                  <span>Adicionar conta</span>
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

