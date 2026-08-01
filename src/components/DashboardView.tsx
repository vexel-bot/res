import React from 'react';
import {
  Sparkles,
  Calendar,
  Clock,
  TrendingUp,
  ArrowUpRight,
  CheckCircle2,
  Plus,
  Send,
  Eye,
  Heart,
  MessageSquare,
  Share2,
  Layers,
  ChevronRight,
  AlertCircle,
  Play,
} from 'lucide-react';
import {
  NavigationTab,
  Post,
  AIActionSuggestion,
  Workspace,
} from '../types';

interface DashboardViewProps {
  posts: Post[];
  suggestions: AIActionSuggestion[];
  activeWorkspace: Workspace;
  onNavigate: (tab: NavigationTab) => void;
  onOpenCampaignWizard: () => void;
  onNewPost: () => void;
  onSelectPost: (post: Post) => void;
}

export const DashboardView: React.FC<DashboardViewProps> = ({
  posts,
  suggestions,
  activeWorkspace,
  onNavigate,
  onOpenCampaignWizard,
  onNewPost,
  onSelectPost,
}) => {
  const scheduledPosts = posts.filter((p) => p.status === 'scheduled');
  const pendingPosts = posts.filter((p) => p.status === 'pending_approval');

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Top Welcome & AI Proactive Banner */}
      <div className="relative overflow-hidden rounded-2xl bg-[#0A0A0A] border border-white/5 p-6 shadow-sm">
        <div className="absolute -right-10 -bottom-10 w-64 h-64 bg-indigo-600/5 rounded-full blur-3xl pointer-events-none"></div>

        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1.5">
            <div className="flex items-center gap-2">
              <span className="text-[10px] uppercase font-semibold tracking-wider px-2.5 py-0.5 rounded-full bg-indigo-500/15 text-indigo-300 border border-indigo-500/25">
                IA Central Ativa
              </span>
              <span className="text-xs text-white/40">
                • {activeWorkspace.brandProfile.name}
              </span>
            </div>
            <h2 className="text-lg font-semibold text-[#ededed] tracking-tight">
              Sua presença digital está em ritmo acelerado hoje.
            </h2>
            <p className="text-xs text-neutral-400 max-w-2xl leading-relaxed">
              Você possui <strong className="text-indigo-300 font-medium">{scheduledPosts.length} conteúdos programados</strong> para
              esta semana e <strong className="text-amber-300 font-medium">{pendingPosts.length} aprovação pendente</strong>. A IA sugeriu um novo
              plano de 3 carrosséis.
            </p>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            <button
              onClick={onOpenCampaignWizard}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs shadow-sm shadow-indigo-600/20 border border-indigo-500/30 transition-all duration-150 active:scale-[0.98]"
            >
              <Sparkles className="w-3.5 h-3.5 text-amber-300" />
              <span>Gerar Campanha com IA</span>
            </button>
          </div>
        </div>
      </div>

      {/* Quick Executive Stats Bar */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-4 rounded-2xl bg-[#0A0A0A] border border-white/5 flex flex-col justify-between">
          <div className="flex items-center justify-between text-white/40">
            <span className="text-xs font-medium">Alcance Total (30d)</span>
            <Eye className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="mt-3 flex items-baseline justify-between">
            <span className="text-2xl font-bold text-[#ededed]">184.2K</span>
            <span className="text-xs font-medium text-emerald-400 flex items-center gap-0.5">
              <ArrowUpRight className="w-3.5 h-3.5" /> +18.4%
            </span>
          </div>
          <span className="text-[10px] text-white/40 mt-1">Impulsionado por Carrosséis</span>
        </div>

        <div className="p-4 rounded-2xl bg-[#0A0A0A] border border-white/5 flex flex-col justify-between">
          <div className="flex items-center justify-between text-white/40">
            <span className="text-xs font-medium">Taxa de Engajamento</span>
            <Heart className="w-4 h-4 text-rose-400" />
          </div>
          <div className="mt-3 flex items-baseline justify-between">
            <span className="text-2xl font-bold text-[#ededed]">6.8%</span>
            <span className="text-xs font-medium text-emerald-400 flex items-center gap-0.5">
              <ArrowUpRight className="w-3.5 h-3.5" /> +1.2%
            </span>
          </div>
          <span className="text-[10px] text-white/40 mt-1">3.2x acima da média da indústria</span>
        </div>

        <div className="p-4 rounded-2xl bg-[#0A0A0A] border border-white/5 flex flex-col justify-between">
          <div className="flex items-center justify-between text-white/40">
            <span className="text-xs font-medium">Agendamentos Ativos</span>
            <Calendar className="w-4 h-4 text-amber-400" />
          </div>
          <div className="mt-3 flex items-baseline justify-between">
            <span className="text-2xl font-bold text-[#ededed]">{scheduledPosts.length + pendingPosts.length}</span>
            <span className="text-xs font-medium text-indigo-300">Próximos 7 dias</span>
          </div>
          <span className="text-[10px] text-white/40 mt-1">Frequência garantida</span>
        </div>

        <div className="p-4 rounded-2xl bg-[#0A0A0A] border border-white/5 flex flex-col justify-between">
          <div className="flex items-center justify-between text-white/40">
            <span className="text-xs font-medium">Pontuação da Marca IA</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="mt-3 flex items-baseline justify-between">
            <span className="text-2xl font-bold text-[#ededed]">96 / 100</span>
            <span className="text-xs font-medium text-emerald-400">Consistente</span>
          </div>
          <span className="text-[10px] text-white/40 mt-1">Tom de voz alinhado ao guia</span>
        </div>
      </div>

      {/* Main Grid: AI Suggestions + Scheduled Posts Queue */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: AI Proactive Suggestions & Scheduled Queue */}
        <div className="lg:col-span-2 space-y-6">
          {/* AI Suggestions Box */}
          <div className="p-5 rounded-2xl bg-[#0A0A0A] border border-white/5 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-indigo-400" />
                <h3 className="text-sm font-bold text-[#ededed]">Ações Recomendadas pela IA Central</h3>
              </div>
              <button
                onClick={() => onNavigate('ai-central')}
                className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1 font-medium"
              >
                Ver todas <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {suggestions.map((sug) => (
                <div
                  key={sug.id}
                  onClick={onOpenCampaignWizard}
                  className="p-3.5 rounded-xl bg-white/[0.02] hover:bg-white/[0.05] border border-white/5 hover:border-indigo-500/30 cursor-pointer transition-all flex flex-col justify-between group"
                >
                  <div className="space-y-1">
                    <span className="text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                      {sug.badge}
                    </span>
                    <h4 className="text-xs font-semibold text-[#ededed] group-hover:text-indigo-300 transition-colors mt-2">
                      {sug.title}
                    </h4>
                    <p className="text-[11px] text-white/40 line-clamp-2 mt-1">
                      {sug.description}
                    </p>
                  </div>
                  <div className="mt-3 pt-2 border-t border-white/5 flex items-center justify-between text-[10px]">
                    <span className="text-emerald-400 font-medium">{sug.impact}</span>
                    <ChevronRight className="w-3.5 h-3.5 text-white/40 group-hover:text-indigo-400 transform group-hover:translate-x-0.5 transition-all" />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Scheduled & Pending Posts Queue */}
          <div className="p-5 rounded-2xl bg-[#0A0A0A] border border-white/5 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-indigo-400" />
                <h3 className="text-sm font-bold text-[#ededed]">Conteúdos Programados e Pendências</h3>
              </div>
              <button
                onClick={() => onNavigate('calendar')}
                className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1 font-medium"
              >
                Ver Calendário Completo <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>

            <div className="space-y-2.5">
              {posts.map((post) => (
                <div
                  key={post.id}
                  onClick={() => onSelectPost(post)}
                  className="p-3.5 rounded-xl bg-white/[0.02] hover:bg-white/[0.05] border border-white/5 hover:border-white/10 transition-all flex items-center justify-between gap-4 cursor-pointer group"
                >
                  <div className="flex items-center gap-3.5 min-w-0">
                    <div className="relative shrink-0">
                      <img
                        src={post.imageUrl || 'https://picsum.photos/seed/post/100/100'}
                        alt={post.title}
                        className="w-12 h-12 rounded-lg object-cover ring-1 ring-white/10"
                        referrerPolicy="no-referrer"
                      />
                      <span className="absolute -bottom-1 -right-1 px-1 py-0.2 rounded text-[9px] font-bold uppercase bg-[#0A0A0A] border border-white/10 text-indigo-300">
                        {post.platform.slice(0, 2)}
                      </span>
                    </div>

                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold text-[#ededed] group-hover:text-indigo-300 truncate">
                          {post.title}
                        </span>
                        <span className="text-[10px] uppercase px-2 py-0.2 rounded font-medium bg-white/5 text-white/60 shrink-0">
                          {post.format}
                        </span>
                      </div>
                      <p className="text-[11px] text-white/40 truncate mt-0.5">{post.copy}</p>
                    </div>
                  </div>

                  <div className="flex items-center gap-4 shrink-0 text-right">
                    <div>
                      <span
                        className={`inline-block text-[10px] font-bold px-2 py-0.5 rounded-full ${
                          post.status === 'scheduled'
                            ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                            : post.status === 'pending_approval'
                            ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                            : 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30'
                        }`}
                      >
                        {post.status === 'scheduled'
                          ? 'Programado'
                          : post.status === 'pending_approval'
                          ? 'Pendente'
                          : 'Publicado'}
                      </span>
                      <div className="text-[10px] text-white/40 mt-1">
                        {post.scheduledAt ? new Date(post.scheduledAt).toLocaleDateString('pt-BR', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }) : 'Publicado'}
                      </div>
                    </div>
                    <ChevronRight className="w-4 h-4 text-white/40 group-hover:text-white transition-colors" />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Col: Mini Calendar & Recent Team Activity */}
        <div className="space-y-6">
          {/* Quick Schedule Overview Card */}
          <div className="p-5 rounded-2xl bg-[#0A0A0A] border border-white/5 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-[#ededed] flex items-center gap-2">
                <Calendar className="w-4 h-4 text-indigo-400" /> Esta Semana
              </h3>
              <span className="text-[10px] text-white/40">Julho / Agosto 2026</span>
            </div>

            <div className="grid grid-cols-7 gap-1 text-center text-[10px]">
              {['S', 'T', 'Q', 'Q', 'S', 'S', 'D'].map((d, i) => (
                <div key={i} className="text-white/40 font-bold py-1">
                  {d}
                </div>
              ))}
              {[27, 28, 29, 30, 31, 1, 2].map((day, idx) => (
                <div
                  key={idx}
                  className={`p-2 rounded-lg flex flex-col items-center gap-1 ${
                    day === 30
                      ? 'bg-indigo-600 text-white font-bold ring-1 ring-indigo-400'
                      : 'bg-white/[0.03] text-neutral-300 hover:bg-white/[0.07]'
                  }`}
                >
                  <span>{day}</span>
                  {day === 30 || day === 31 || day === 1 ? (
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
                  ) : null}
                </div>
              ))}
            </div>

            <div className="p-3 rounded-xl bg-white/[0.02] border border-white/5 text-xs text-neutral-300 flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />
              <span>
                Melhor horário de hoje: <strong className="text-white">18:30 (Instagram)</strong>.
              </span>
            </div>
          </div>

          {/* Recent Activity Stream */}
          <div className="p-5 rounded-2xl bg-[#0A0A0A] border border-white/5 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-[#ededed] flex items-center gap-2">
                <Layers className="w-4 h-4 text-indigo-400" /> Últimas Atividades
              </h3>
              <button
                onClick={() => onNavigate('collaboration')}
                className="text-[11px] text-white/40 hover:text-white"
              >
                Ver time
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="flex items-start gap-3">
                <img
                  src="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=80&q=80"
                  alt="Marcus"
                  className="w-7 h-7 rounded-full object-cover shrink-0 mt-0.5"
                  referrerPolicy="no-referrer"
                />
                <div>
                  <div className="text-[#ededed] font-medium">
                    Marcus Thorne <span className="text-white/40 font-normal">aprovou o carrossel</span>
                  </div>
                  <div className="text-[10px] text-white/40 mt-0.5">Há 15 minutos • "5 Regras da IA Enterprise"</div>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <div className="w-7 h-7 rounded-full bg-indigo-600/20 text-indigo-300 flex items-center justify-center shrink-0 mt-0.5 font-bold text-[10px]">
                  IA
                </div>
                <div>
                  <div className="text-[#ededed] font-medium">
                    IA Central <span className="text-white/40 font-normal">gerou 3 opções de imagens HD</span>
                  </div>
                  <div className="text-[10px] text-white/40 mt-0.5">Há 1 hora • Estúdio de Imagens</div>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <img
                  src="https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=80&q=80"
                  alt="Gabriel"
                  className="w-7 h-7 rounded-full object-cover shrink-0 mt-0.5"
                  referrerPolicy="no-referrer"
                />
                <div>
                  <div className="text-[#ededed] font-medium">
                    Gabriel Santos <span className="text-white/40 font-normal">agendou post no LinkedIn</span>
                  </div>
                  <div className="text-[10px] text-white/40 mt-0.5">Há 2 horas • "Por que centralizar seu workflow"</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
