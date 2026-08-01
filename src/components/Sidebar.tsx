import React from 'react';
import {
  LayoutDashboard,
  Sparkles,
  PenTool,
  Image,
  Video,
  Calendar,
  Share2,
  BarChart3,
  GitFork,
  Users,
  Settings,
  ChevronDown,
  Command,
  Plus,
  Layers,
} from 'lucide-react';
import { NavigationTab, Workspace } from '../types';

interface SidebarProps {
  currentTab: NavigationTab;
  onSelectTab: (tab: NavigationTab) => void;
  workspaces: Workspace[];
  activeWorkspace: Workspace;
  onSelectWorkspace: (ws: Workspace) => void;
  isCompact: boolean;
  onOpenSpotlight: () => void;
  onNewPost: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentTab,
  onSelectTab,
  workspaces,
  activeWorkspace,
  onSelectWorkspace,
  isCompact,
  onOpenSpotlight,
  onNewPost,
}) => {
  const [showWsMenu, setShowWsMenu] = React.useState(false);

  const navItems: { id: NavigationTab; label: string; icon: React.FC<{ className?: string }>; badge?: string }[] = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'ai-central', label: 'IA Central', icon: Sparkles, badge: 'Pro' },
    { id: 'creation', label: 'Estúdio de Criação', icon: PenTool },
    { id: 'images', label: 'Geração de Imagens', icon: Image },
    { id: 'video', label: 'Edição de Vídeo', icon: Video },
    { id: 'calendar', label: 'Calendário Editorial', icon: Calendar },
    { id: 'publisher', label: 'Publicação & Canais', icon: Share2 },
    { id: 'analytics', label: 'Analytics Inteligente', icon: BarChart3 },
    { id: 'automations', label: 'Automações', icon: GitFork },
    { id: 'collaboration', label: 'Colaboração & Times', icon: Users },
    { id: 'settings', label: 'Configurações', icon: Settings },
  ];

  return (
    <aside
      className={`fixed top-0 left-0 h-screen z-30 bg-[#0A0A0A] border-r border-white/5 flex flex-col transition-all duration-200 ${
        isCompact ? 'w-20' : 'w-64'
      }`}
    >
      {/* Brand Header & Workspace Selector */}
      <div className="p-3.5 border-b border-white/5 relative">
        <div
          onClick={() => setShowWsMenu(!showWsMenu)}
          className="flex items-center justify-between p-2 rounded-xl bg-white/[0.02] hover:bg-white/[0.05] border border-white/5 cursor-pointer transition-all duration-150 group"
        >
          <div className="flex items-center gap-2.5 min-w-0">
            <img
              src={activeWorkspace.avatar}
              alt={activeWorkspace.name}
              className="w-7 h-7 rounded-lg object-cover ring-1 ring-white/10"
              referrerPolicy="no-referrer"
            />
            {!isCompact && (
              <div className="min-w-0 text-left">
                <div className="text-xs font-medium text-[#ededed] truncate group-hover:text-indigo-300 transition-colors">
                  {activeWorkspace.name}
                </div>
                <div className="text-[10px] text-white/40 flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                  {activeWorkspace.plan}
                </div>
              </div>
            )}
          </div>
          {!isCompact && <ChevronDown className="w-3.5 h-3.5 text-white/40 group-hover:text-white transition-colors" />}
        </div>

        {/* Workspace Menu Dropdown */}
        {showWsMenu && !isCompact && (
          <div className="absolute top-16 left-3.5 right-3.5 bg-[#0A0A0A] border border-white/10 rounded-xl shadow-2xl p-1.5 z-50 animate-in fade-in zoom-in-95 duration-150">
            <div className="text-[10px] uppercase font-semibold text-white/40 px-2 py-1 tracking-wider">
              Espaços de Trabalho
            </div>
            {workspaces.map((ws) => (
              <div
                key={ws.id}
                onClick={() => {
                  onSelectWorkspace(ws);
                  setShowWsMenu(false);
                }}
                className={`flex items-center justify-between p-2 rounded-lg text-xs cursor-pointer transition-all duration-150 ${
                  ws.id === activeWorkspace.id
                    ? 'bg-indigo-600/15 text-indigo-300 font-medium border border-indigo-500/20'
                    : 'text-neutral-300 hover:bg-white/5'
                }`}
              >
                <div className="flex items-center gap-2">
                  <img src={ws.avatar} alt={ws.name} className="w-5 h-5 rounded object-cover" referrerPolicy="no-referrer" />
                  <span className="truncate max-w-[120px]">{ws.name}</span>
                </div>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-white/5 text-neutral-400">{ws.plan}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Quick Action Button & Spotlight Launcher */}
      <div className="p-3 border-b border-white/5 space-y-2">
        <button
          onClick={onNewPost}
          className="w-full flex items-center justify-center gap-2 py-2 px-3 bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs rounded-xl shadow-sm shadow-indigo-600/20 border border-indigo-500/30 transition-all duration-150 active:scale-[0.98]"
        >
          <Plus className="w-4 h-4" />
          {!isCompact && <span>Novo Conteúdo</span>}
        </button>

        {!isCompact && (
          <button
            onClick={onOpenSpotlight}
            className="w-full flex items-center justify-between py-1.5 px-3 bg-white/[0.02] hover:bg-white/[0.06] text-white/40 hover:text-white/80 text-xs rounded-xl border border-white/5 transition-all duration-150"
          >
            <div className="flex items-center gap-2">
              <Command className="w-3.5 h-3.5 text-indigo-400" />
              <span>Busca Global...</span>
            </div>
            <kbd className="text-[10px] bg-white/10 px-1.5 py-0.5 rounded font-mono text-white/40">⌘K</kbd>
          </button>
        )}
      </div>

      {/* Main Navigation */}
      <nav className="flex-1 overflow-y-auto p-3 space-y-1 custom-scrollbar">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onSelectTab(item.id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-medium transition-all group relative ${
                isActive
                  ? 'bg-indigo-600/15 text-indigo-300 border border-indigo-500/30 shadow-sm shadow-indigo-500/10'
                  : 'text-neutral-400 hover:text-[#ededed] hover:bg-white/[0.04]'
              }`}
              title={isCompact ? item.label : undefined}
            >
              <Icon
                className={`w-4 h-4 shrink-0 transition-colors ${
                  isActive ? 'text-indigo-400' : 'text-neutral-400 group-hover:text-neutral-200'
                }`}
              />
              {!isCompact && (
                <span className="truncate flex-1 text-left">{item.label}</span>
              )}
              {!isCompact && item.badge && (
                <span className="text-[9px] font-bold px-1.5 py-0.2 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                  {item.badge}
                </span>
              )}
              {isActive && (
                <span className="absolute left-0 top-2 bottom-2 w-1 bg-indigo-500 rounded-r"></span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Footer User Info */}
      <div className="p-3 border-t border-white/5 bg-white/[0.01]">
        <div className="flex items-center gap-3 px-2 py-1.5 rounded-xl">
          <div className="relative">
            <img
              src="https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=120&q=80"
              alt="User"
              className="w-8 h-8 rounded-full object-cover ring-2 ring-indigo-500/40"
              referrerPolicy="no-referrer"
            />
            <span className="absolute bottom-0 right-0 w-2.5 h-2.5 bg-emerald-500 border-2 border-[#0A0A0A] rounded-full"></span>
          </div>
          {!isCompact && (
            <div className="min-w-0 flex-1">
              <div className="text-xs font-semibold text-[#ededed] truncate">Elena Vance</div>
              <div className="text-[10px] text-white/40 truncate">Estrategista Chefe</div>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
};
