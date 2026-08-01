import React from 'react';
import {
  Bell,
  Sparkles,
  Search,
  Maximize2,
  Minimize2,
  Moon,
  Sun,
  SlidersHorizontal,
  Plus,
} from 'lucide-react';
import { NavigationTab, Workspace } from '../types';

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

const TAB_TITLE_MAP: Record<NavigationTab, { title: string; subtitle: string }> = {
  dashboard: { title: 'Dashboard Geral', subtitle: 'Visão executiva unificada da sua presença digital' },
  'ai-central': { title: 'IA Central de Marca', subtitle: 'Estrategista inteligente e gerador de campanhas' },
  creation: { title: 'Estúdio de Criação', subtitle: 'Criador universal de posts, carrosséis, reels e artigos' },
  images: { title: 'Geração de Imagens IA', subtitle: 'Studio de criação visual, mockups e capas para redes' },
  video: { title: 'Edição de Vídeo IA', subtitle: 'Timeline de reels, legendas automáticas e voz sintética' },
  calendar: { title: 'Calendário Editorial', subtitle: 'Planejamento e agendamento drag & drop de publicações' },
  publisher: { title: 'Publicação & Canais', subtitle: 'Conexão e disparo simultâneo para redes sociais' },
  analytics: { title: 'Analytics Inteligente', subtitle: 'Métricas contextuais explicadas por inteligência artificial' },
  automations: { title: 'Automações & Flows', subtitle: 'Orquestração de fluxos automáticos sem código' },
  collaboration: { title: 'Colaboração & Times', subtitle: 'Aprovação de conteúdo, comentários e permissões' },
  settings: { title: 'Configurações do Sistema', subtitle: 'Parâmetros da marca, chaves API e preferências' },
};

export const Header: React.FC<HeaderProps> = ({
  currentTab,
  activeWorkspace,
  onOpenSpotlight,
  onOpenAICentral,
  onNewPost,
  isCompact,
  onToggleCompact,
  isDarkMode,
  onToggleDarkMode,
}) => {
  const tabInfo = TAB_TITLE_MAP[currentTab];
  const [showNotifications, setShowNotifications] = React.useState(false);

  return (
    <header className="sticky top-0 z-20 bg-[#050505]/90 backdrop-blur-md border-b border-white/5 px-6 py-3 flex items-center justify-between">
      {/* Title & Context */}
      <div>
        <div className="flex items-center gap-2.5">
          <h1 className="text-sm font-semibold text-[#ededed] tracking-tight">{tabInfo.title}</h1>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-white/[0.03] border border-white/5 text-neutral-400">
            {activeWorkspace.name}
          </span>
        </div>
        <p className="text-xs text-neutral-400 mt-0.5">{tabInfo.subtitle}</p>
      </div>

      {/* Action Toolbar */}
      <div className="flex items-center gap-2.5">
        {/* Spotlight Trigger */}
        <button
          onClick={onOpenSpotlight}
          className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-white/[0.02] hover:bg-white/[0.06] border border-white/5 text-neutral-300 text-xs transition-all duration-150"
        >
          <Search className="w-3.5 h-3.5 text-indigo-400" />
          <span className="text-neutral-400">Pesquisar...</span>
          <kbd className="text-[10px] bg-white/10 px-1.5 py-0.5 rounded font-mono text-white/40">⌘K</kbd>
        </button>

        {/* AI Assistant Quick Trigger */}
        <button
          onClick={onOpenAICentral}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-indigo-600/15 hover:bg-indigo-600/25 border border-indigo-500/30 text-indigo-300 text-xs font-medium transition-all duration-150"
        >
          <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
          <span className="hidden md:inline">Assistente IA</span>
        </button>

        {/* Notification Bell */}
        <div className="relative">
          <button
            onClick={() => setShowNotifications(!showNotifications)}
            className="p-2 rounded-xl bg-white/[0.02] hover:bg-white/[0.06] border border-white/5 text-neutral-300 transition-all duration-150 relative"
            title="Notificações e Alertas da IA"
          >
            <Bell className="w-3.5 h-3.5" />
            <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 rounded-full bg-indigo-500"></span>
          </button>

          {showNotifications && (
            <div className="absolute right-0 top-11 w-80 bg-[#0A0A0A] border border-white/10 rounded-2xl shadow-2xl p-4 z-50 animate-in fade-in zoom-in-95 duration-150">
              <div className="flex items-center justify-between pb-3 border-b border-white/5">
                <span className="text-xs font-semibold text-[#ededed] flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-indigo-400" /> Alertas da IA
                </span>
                <span className="text-[10px] text-white/40">3 novos</span>
              </div>
              <div className="mt-3 space-y-2 text-xs">
                <div className="p-2.5 rounded-xl bg-indigo-600/10 border border-indigo-500/20 text-neutral-200">
                  <div className="font-medium text-indigo-300 text-[11px]">Carrossel Aprovado</div>
                  <div className="text-[11px] text-neutral-400 mt-0.5">Marcus Thorne aprovou o post "5 Regras da IA Enterprise".</div>
                </div>
                <div className="p-2.5 rounded-xl bg-white/[0.02] border border-white/5 text-neutral-200">
                  <div className="font-medium text-emerald-400 text-[11px]">Sugestão de Horário</div>
                  <div className="text-[11px] text-neutral-400 mt-0.5">Sua audiência no TikTok está 30% mais ativa hoje às 20h.</div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Density Toggle */}
        <button
          onClick={onToggleCompact}
          className="p-2 rounded-xl bg-white/[0.02] hover:bg-white/[0.06] border border-white/5 text-neutral-300 transition-all duration-150"
          title={isCompact ? 'Expandir Menu' : 'Modo Compacto'}
        >
          {isCompact ? <Maximize2 className="w-3.5 h-3.5" /> : <Minimize2 className="w-3.5 h-3.5" />}
        </button>

        {/* Theme Switcher */}
        <button
          onClick={onToggleDarkMode}
          className="p-2 rounded-xl bg-white/[0.02] hover:bg-white/[0.06] border border-white/5 text-neutral-300 transition-all duration-150"
          title={isDarkMode ? 'Light Mode Opcional' : 'Dark Mode Padrão'}
        >
          {isDarkMode ? <Sun className="w-3.5 h-3.5 text-amber-400" /> : <Moon className="w-3.5 h-3.5 text-indigo-400" />}
        </button>

        {/* Create Post Button */}
        <button
          onClick={onNewPost}
          className="flex items-center gap-1.5 py-1.5 px-3.5 bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs rounded-xl shadow-sm shadow-indigo-600/20 transition-all duration-150 border border-indigo-500/30 active:scale-[0.98]"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>Criar</span>
        </button>
      </div>
    </header>
  );
};
