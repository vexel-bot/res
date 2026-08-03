import React from 'react';
import {
  Calendar as CalendarIcon,
  ChevronLeft,
  ChevronRight,
  Clock,
  Plus,
  Filter,
  CheckCircle2,
  AlertCircle,
  Eye,
  Send,
  X,
} from 'lucide-react';
import { Post, SocialPlatform, PostStatus } from '../types';
import { useOperations } from '../context/OperationsContext';

interface EditorialCalendarViewProps {
  posts: Post[];
  onSelectPost: (post: Post) => void;
  onNewPost: () => void;
}

export const EditorialCalendarView: React.FC<EditorialCalendarViewProps> = ({
  posts,
  onSelectPost,
  onNewPost,
}) => {
  const { activeCampaign } = useOperations();
  const [viewMode, setViewMode] = React.useState<'month' | 'week' | 'day'>('month');
  const [filterPlatform, setFilterPlatform] = React.useState<string>('all');
  const [selectedPostDetail, setSelectedPostDetail] = React.useState<Post | null>(null);
  const [draggedPostId, setDraggedPostId] = React.useState<string>();
  const [lastMoved, setLastMoved] = React.useState<string>();

  const daysInMonth = [
    { day: 27, isOtherMonth: true },
    { day: 28, isOtherMonth: true },
    { day: 29, isOtherMonth: true },
    { day: 30, posts: posts.filter((p) => p.status === 'scheduled') },
    { day: 31, posts: posts.filter((p) => p.status === 'pending_approval') },
    { day: 1, posts: posts.filter((p) => p.status === 'published') },
    { day: 2, posts: [] },
    { day: 3, posts: [] },
    { day: 4, posts: [] },
    { day: 5, posts: [] },
    { day: 6, posts: [] },
    { day: 7, posts: [] },
    { day: 8, posts: [] },
    { day: 9, posts: [] },
    { day: 10, posts: [] },
    { day: 11, posts: [] },
    { day: 12, posts: [] },
    { day: 13, posts: [] },
    { day: 14, posts: [] },
    { day: 15, posts: [] },
  ];

  const getStatusBadge = (status: PostStatus) => {
    switch (status) {
      case 'scheduled':
        return <span className="w-2 h-2 rounded-full bg-emerald-400"></span>;
      case 'pending_approval':
        return <span className="w-2 h-2 rounded-full bg-amber-400"></span>;
      case 'published':
        return <span className="w-2 h-2 rounded-full bg-indigo-400"></span>;
      default:
        return <span className="w-2 h-2 rounded-full bg-slate-400"></span>;
    }
  };

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {activeCampaign && <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-[#8bd132]/20 bg-[#8bd132]/[0.055] p-3"><div><span className="text-[8px] uppercase tracking-[0.16em] text-[#8bd132]">Estratégia ativa no calendário</span><p className="mt-1 text-[10px] font-medium text-white">{activeCampaign.name}</p></div><p className="max-w-xl text-[9px] text-[#9ca6ab]">{activeCampaign.objective}</p></div>}

      {/* Calendar Header Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/5 pb-4">
        <div>
          <h2 className="text-lg font-bold text-[#ededed] flex items-center gap-2">
            <CalendarIcon className="w-5 h-5 text-indigo-400" /> Calendário Editorial Inteligente
          </h2>
          <p className="text-xs text-white/40">
            Visualização completa no estilo Google Calendar com arrasto inteligente e sugestão de melhores horários
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <select className="rounded-xl border border-white/5 bg-white/[0.03] px-3 py-2 text-[10px] text-[#ededed] outline-none"><option>Todos os clientes</option><option>Clicko AI Studios</option></select>
          <select className="rounded-xl border border-white/5 bg-white/[0.03] px-3 py-2 text-[10px] text-[#ededed] outline-none"><option>Todos os projetos</option><option>Lançamento Q3</option></select>
          <select className="rounded-xl border border-white/5 bg-white/[0.03] px-3 py-2 text-[10px] text-[#ededed] outline-none"><option>Todas as contas</option><option>@clickostudio</option><option>Clicko AI Studios · LinkedIn</option></select>
          {/* Filter by Platform */}
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white/[0.03] border border-white/5 text-xs text-neutral-300">
            <Filter className="w-3.5 h-3.5 text-indigo-400" />
            <select
              value={filterPlatform}
              onChange={(e) => setFilterPlatform(e.target.value)}
              className="bg-transparent focus:outline-none text-[#ededed] cursor-pointer"
            >
              <option value="all" className="bg-[#050505]">Todas as Redes</option>
              <option value="instagram" className="bg-[#050505]">Instagram</option>
              <option value="linkedin" className="bg-[#050505]">LinkedIn</option>
              <option value="tiktok" className="bg-[#050505]">TikTok</option>
              <option value="youtube" className="bg-[#050505]">YouTube</option>
            </select>
          </div>

          {/* View Mode Toggle */}
          <div className="flex items-center p-1 rounded-xl bg-white/[0.03] border border-white/5">
            <button
              onClick={() => setViewMode('month')}
              className={`px-3 py-1 text-xs font-semibold rounded-lg ${
                viewMode === 'month' ? 'bg-indigo-600 text-white' : 'text-white/40'
              }`}
            >
              Mês
            </button>
            <button
              onClick={() => setViewMode('week')}
              className={`px-3 py-1 text-xs font-semibold rounded-lg ${
                viewMode === 'week' ? 'bg-indigo-600 text-white' : 'text-white/40'
              }`}
            >
              Semana
            </button>
            <button
              onClick={() => setViewMode('day')}
              className={`px-3 py-1 text-xs font-semibold rounded-lg ${
                viewMode === 'day' ? 'bg-indigo-600 text-white' : 'text-white/40'
              }`}
            >
              Dia
            </button>
          </div>

          <button
            onClick={onNewPost}
            className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs flex items-center gap-1.5 shadow-lg shadow-indigo-600/20"
          >
            <Plus className="w-4 h-4" /> Agendar Post
          </button>
        </div>
      </div>

      {/* Month Navigator Header */}
      <div className="flex items-center justify-between bg-[#0A0A0A] border border-white/5 p-4 rounded-2xl">
        <div className="flex items-center gap-3">
          <button className="p-2 rounded-xl bg-white/[0.03] hover:bg-white/10 text-white">
            <ChevronLeft className="w-4 h-4" />
          </button>
          <h3 className="text-sm font-bold text-[#ededed]">Julho / Agosto 2026</h3>
          <button className="p-2 rounded-xl bg-white/[0.03] hover:bg-white/10 text-white">
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>

        {/* Legend */}
        <div className="flex items-center gap-4 text-xs">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400"></span>
            <span className="text-neutral-300">Programado</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-400"></span>
            <span className="text-neutral-300">Pendente</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-indigo-400"></span>
            <span className="text-neutral-300">Publicado</span>
          </div>
        </div>
      </div>

      {/* Calendar Grid (Month View) */}
      <div className="bg-[#0A0A0A] border border-white/5 rounded-2xl overflow-hidden p-4 space-y-2">
        {/* Day of Week Labels */}
        <div className="grid grid-cols-7 gap-2 text-center text-xs font-bold text-white/40 border-b border-white/5 pb-3">
          <div>DOM</div>
          <div>SEG</div>
          <div>TER</div>
          <div>QUA</div>
          <div>QUI</div>
          <div>SEX</div>
          <div>SÁB</div>
        </div>

        {/* Days Matrix */}
        <div className="grid grid-cols-7 gap-2">
          {daysInMonth.map((item, idx) => (
            <div
              key={idx}
              onDragOver={(event) => event.preventDefault()}
              onDrop={() => { if (draggedPostId) { setLastMoved(`Conteúdo reagendado para o dia ${item.day}`); setDraggedPostId(undefined); } }}
              className={`min-h-[110px] p-2 rounded-xl border flex flex-col justify-between transition-all ${
                item.isOtherMonth
                  ? 'bg-white/[0.01] border-white/5 text-white/20'
                  : item.day === 30
                  ? 'bg-indigo-600/10 border-indigo-500/30 text-white'
                  : 'bg-white/[0.02] border-white/5 hover:border-white/10 text-neutral-200'
              }`}
            >
              <div className="flex items-center justify-between text-xs">
                <span className={`font-bold ${item.day === 30 ? 'text-indigo-400' : ''}`}>
                  {item.day}
                </span>
                {item.day === 30 && (
                  <span className="text-[9px] px-1.5 py-0.2 rounded bg-indigo-500/20 text-indigo-300">
                    Hoje
                  </span>
                )}
              </div>

              {/* Event Cards inside Day cell */}
              <div className="space-y-1.5 my-1 flex-1">
                {item.posts &&
                  item.posts.map((post) => (
                    <div
                      key={post.id}
                      draggable
                      onDragStart={() => setDraggedPostId(post.id)}
                      onClick={() => {
                        setSelectedPostDetail(post);
                        onSelectPost(post);
                      }}
                      className="p-1.5 rounded-lg bg-[#050505] border border-white/5 hover:border-indigo-500/40 text-[10px] cursor-pointer transition-all space-y-1"
                    >
                      <div className="flex items-center justify-between gap-1">
                        <span className="font-bold text-[#ededed] truncate">{post.title}</span>
                        {getStatusBadge(post.status)}
                      </div>
                      <div className="text-[9px] text-indigo-300 font-mono">
                        {post.platform} • 18:30
                      </div>
                    </div>
                  ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Post Detail Drawer Modal */}
      {lastMoved && <div className="fixed bottom-20 right-6 z-50 rounded-lg border border-[#8bd132]/25 bg-[#182126] px-4 py-3 text-[9px] text-[#8bd132] shadow-xl">{lastMoved}<button onClick={() => setLastMoved(undefined)} className="ml-3 text-[#7e898f]">Fechar</button></div>}

      {selectedPostDetail && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-in fade-in duration-150">
          <div className="w-full max-w-lg bg-[#0A0A0A] border border-white/10 rounded-2xl shadow-2xl p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-white/5 pb-3">
              <span className="text-xs font-bold uppercase tracking-wider px-2.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                {selectedPostDetail.platform} • {selectedPostDetail.format}
              </span>
              <button
                onClick={() => setSelectedPostDetail(null)}
                className="p-1 text-white/40 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <h3 className="text-base font-bold text-[#ededed]">{selectedPostDetail.title}</h3>
            <p className="text-xs text-neutral-300 leading-relaxed whitespace-pre-wrap bg-white/[0.03] p-3 rounded-xl border border-white/5">
              {selectedPostDetail.copy}
            </p>

            <div className="flex items-center justify-between text-xs text-white/40 pt-2 border-t border-white/5">
              <div>Status: <strong className="text-[#ededed] capitalize">{selectedPostDetail.status}</strong></div>
              <div>Autor: <strong className="text-[#ededed]">{selectedPostDetail.author}</strong></div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                onClick={() => setSelectedPostDetail(null)}
                className="px-4 py-2 rounded-xl bg-indigo-600 text-white font-bold text-xs"
              >
                Fechar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
