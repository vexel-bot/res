import React from 'react';
import { Bell, CircleHelp, ChevronDown, Search } from 'lucide-react';
import { NavigationTab, Workspace } from '../types';
import { useGovernance } from '../context/GovernanceContext';
import { roleLabel } from '../security/accessControl';
import { ClickoLogo } from './ClickoLogo';

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
  const { currentUser, approvals } = useGovernance();
  const pendingApprovals = approvals.filter((item) => ['in_review', 'pending_approval'].includes(item.stage)).length;

  return (
    <header className="sticky top-0 z-30 flex h-[82px] items-center justify-between bg-black/95 px-6 backdrop-blur-xl 2xl:px-10">
      <div className="flex min-w-0 items-center">
        <button
          type="button"
          onClick={onOpenSpotlight}
          className="flex h-10 w-[448px] max-w-[36vw] items-center gap-2.5 rounded-[10px] border border-white/[0.035] bg-[#20282d] px-3 text-[#8f989e] transition hover:border-white/10 hover:bg-[#252e33] max-[700px]:w-10 max-[700px]:px-3"
        >
          <Search className="h-4 w-4" />
          <span className="truncate text-[11px] max-[700px]:hidden">Buscar conteúdos, clientes, campanhas...</span>
        </button>
      </div>

      <div className="flex items-center gap-3">
        <div className="relative">
          <button
            type="button"
            onClick={() => setShowNotifications((value) => !value)}
            className="relative grid h-10 w-10 place-items-center rounded-[10px] border border-white/[0.045] bg-[#1d252a] text-[#d8dcde] hover:bg-[#252e33]"
            aria-label="Notificações"
          >
            <Bell className="h-[18px] w-[18px]" />
            {pendingApprovals > 0 && <span className="absolute -right-0.5 -top-0.5 grid h-[17px] min-w-[17px] place-items-center rounded-full bg-[#76bc3c] px-1 text-[8px] font-bold text-white">{pendingApprovals}</span>}
          </button>
          {showNotifications && (
            <div className="absolute right-0 top-12 w-72 rounded-xl border border-white/10 bg-[#182126] p-3 shadow-2xl">
              <div className="mb-2 text-[12px] font-semibold text-white">Notificações</div>
              <div className="space-y-1.5 text-[10px] text-[#b5bdc1]">
                {pendingApprovals > 0 && <div className="rounded-lg bg-white/[0.035] p-2.5">{pendingApprovals} conteúdo{pendingApprovals > 1 ? 's' : ''} aguardando aprovação.</div>}
                <div className="rounded-lg bg-white/[0.035] p-2.5">Sua campanha atingiu +14,5% de alcance.</div>
              </div>
            </div>
          )}
        </div>

        <button type="button" className="grid h-10 w-10 place-items-center rounded-[10px] border border-white/[0.045] bg-[#1d252a] text-[#d8dcde] hover:bg-[#252e33] max-[700px]:hidden" aria-label="Ajuda">
          <CircleHelp className="h-[18px] w-[18px]" />
        </button>

        <button type="button" className="flex h-11 items-center gap-2.5 rounded-[10px] border border-white/[0.035] bg-[#1d252a] px-2.5 text-left hover:bg-[#252e33]">
          {currentUser?.avatar ? (
            <img
              src={currentUser.avatar}
              className="h-8 w-8 rounded-full object-cover ring-1 ring-white/10"
              alt={currentUser.name}
            />
          ) : (
            <ClickoLogo appearance="badge" className="h-8 w-10" />
          )}
          <span className="hidden min-w-[104px] sm:block">
            <span className="block text-[11px] font-semibold text-white">{currentUser?.name || 'Carregando…'}</span>
            <span className="block text-[9px] text-[#929ba0]">{currentUser ? roleLabel(currentUser.role) : '—'}</span>
          </span>
          <ChevronDown className="h-4 w-4 text-[#aab1b5]" />
        </button>
      </div>
    </header>
  );
};
