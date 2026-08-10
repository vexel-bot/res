import React from 'react';
import {
  Search,
  Sparkles,
  PenTool,
  Calendar,
  GitFork,
  FileText,
  Users,
  Settings,
  ArrowRight,
  X,
  Share2,
} from 'lucide-react';
import { NavigationTab, SearchResultItem } from '../types';

interface SpotlightModalProps {
  isOpen: boolean;
  onClose: () => void;
  onNavigate: (tab: NavigationTab) => void;
}

export const SpotlightModal: React.FC<SpotlightModalProps> = ({
  isOpen,
  onClose,
  onNavigate,
}) => {
  const [query, setQuery] = React.useState('');

  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        if (isOpen) onClose();
        else setQuery('');
      }
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const ALL_SEARCH_ITEMS: SearchResultItem[] = [
    {
      id: 's1',
      title: '5 Regras da IA corporativa em 2026',
      subtitle: 'Publicação em carrossel agendado para Instagram',
      type: 'post',
      tabToNavigate: 'create-copy',
    },
    {
      id: 's2',
      title: 'Campanha de Lançamento Q3',
      subtitle: 'Estratégia multicanal com 5 conteúdos ativos',
      type: 'campaign',
      tabToNavigate: 'ai-chat',
    },
    {
      id: 's3',
      title: 'Fluxo automático de Reels & Shorts',
      subtitle: 'Automação ativa com 38 execuções',
      type: 'automation',
      tabToNavigate: 'automations',
    },
    {
      id: 's4',
      title: 'Configuração da Marca & Tom de Voz',
      subtitle: 'Parâmetros e diretrizes para a IA Central',
      type: 'action',
      tabToNavigate: 'brain',
    },
    {
      id: 's5',
      title: 'Aprovação de Vídeo por Marcus Thorne',
      subtitle: 'Comentário pendente no Reels/TikTok',
      type: 'post',
      tabToNavigate: 'approvals',
    },
    {
      id: 's6',
      title: 'Gerador de Capa & Banners HD',
      subtitle: 'Criar imagem com nano banana / Gemini',
      type: 'action',
      tabToNavigate: 'create-image',
    },
    {
      id: 's7',
      title: 'Métricas de Engajamento do Mês',
      subtitle: 'Análise inteligente de alcance e cliques',
      type: 'action',
      tabToNavigate: 'analytics',
    },
  ];

  const filtered = ALL_SEARCH_ITEMS.filter(
    (item) =>
      item.title.toLowerCase().includes(query.toLowerCase()) ||
      item.subtitle.toLowerCase().includes(query.toLowerCase())
  );

  const getTypeIcon = (type: SearchResultItem['type']) => {
    switch (type) {
      case 'post':
        return <PenTool className="w-4 h-4 text-indigo-400" />;
      case 'campaign':
        return <Sparkles className="w-4 h-4 text-amber-400" />;
      case 'automation':
        return <GitFork className="w-4 h-4 text-emerald-400" />;
      case 'workspace':
        return <Users className="w-4 h-4 text-cyan-400" />;
      default:
        return <FileText className="w-4 h-4 text-slate-400" />;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4 bg-black/75 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="w-full max-w-2xl bg-[#0A0A0A] border border-white/10 rounded-xl shadow-xl shadow-black/40 overflow-hidden flex flex-col">
        {/* Search Input Bar */}
        <div className="p-4 border-b border-white/5 flex items-center gap-3 bg-white/[0.02]">
          <Search className="w-5 h-5 text-indigo-400 shrink-0" />
          <input
            type="text"
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Digite para buscar qualquer projeto, publicação, comando, cliente ou automação..."
            className="w-full bg-transparent text-[#ededed] placeholder-white/30 text-sm focus:outline-none"
          />
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-white/40 hover:text-white hover:bg-white/10 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Results List */}
        <div className="max-h-96 overflow-y-auto p-2 space-y-1 custom-scrollbar">
          {filtered.length === 0 ? (
            <div className="p-8 text-center text-white/30 text-xs">
              Nenhum resultado encontrado para "{query}"
            </div>
          ) : (
            filtered.map((item) => (
              <div
                key={item.id}
                onClick={() => {
                  onNavigate(item.tabToNavigate);
                  onClose();
                }}
                className="group flex items-center justify-between p-3 rounded-lg hover:bg-[#8bd132]/10 border border-transparent hover:border-[#8bd132]/25 cursor-pointer transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-white/5 border border-white/5 group-hover:bg-[#8bd132]/15 group-hover:border-[#8bd132]/25">
                    {getTypeIcon(item.type)}
                  </div>
                  <div>
                    <div className="text-xs font-semibold text-[#ededed] group-hover:text-indigo-300">
                      {item.title}
                    </div>
                    <div className="text-[11px] text-white/40">{item.subtitle}</div>
                  </div>
                </div>

                <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                  <span className="text-[10px] text-indigo-300 font-medium">Abrir</span>
                  <ArrowRight className="w-3.5 h-3.5 text-indigo-400" />
                </div>
              </div>
            ))
          )}
        </div>

        {/* Modal Footer */}
        <div className="p-3 border-t border-white/5 bg-white/[0.01] flex items-center justify-between text-[11px] text-white/40">
          <span>Clique em um item para acessar</span>
          <span>Mecanismo de busca Clicko Studio</span>
        </div>
      </div>
    </div>
  );
};
