import React from 'react';
import {
  ArrowRight,
  BarChart3,
  Box,
  CalendarDays,
  ChartNoAxesCombined,
  CheckCircle2,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  CircleHelp,
  ClipboardList,
  Clock3,
  FileText,
  Instagram,
  Layers3,
  Pencil,
  Plus,
  Send,
  Sparkles,
  Cpu,
  Link2,
  Workflow,
  Activity,
  UserRound,
} from 'lucide-react';
import { NavigationTab, Post, AIActionSuggestion, Workspace } from '../types';
import { useOperations } from '../context/OperationsContext';
import { useGovernance } from '../context/GovernanceContext';

interface DashboardViewProps {
  posts: Post[];
  suggestions: AIActionSuggestion[];
  activeWorkspace: Workspace;
  onNavigate: (tab: NavigationTab) => void;
  onOpenCampaignWizard: () => void;
  onNewPost: () => void;
  onSelectPost: (post: Post) => void;
}

type CalendarItem = {
  day: number;
  row: number;
  title: string;
  subtitle: string;
  time: string;
  accent: string;
  image: string;
};

const calendarItems: CalendarItem[] = [
  { day: 1, row: 1, title: 'Carrossel', subtitle: 'Saúde', time: '10:00', accent: '#c7a13c', image: 'https://images.unsplash.com/photo-1559757148-5c350d0d3c56?auto=format&fit=crop&w=120&q=80' },
  { day: 1, row: 3, title: 'Histórias', subtitle: 'Dicas', time: '16:00', accent: '#3d91a6', image: 'https://images.unsplash.com/photo-1551836022-d5d88e9218df?auto=format&fit=crop&w=120&q=80' },
  { day: 1, row: 5, title: 'Reels', subtitle: 'Depoimento', time: '20:00', accent: '#8a5bc1', image: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=120&q=80' },
  { day: 2, row: 1, title: 'Publicação', subtitle: 'Promoção', time: '10:00', accent: '#a9515a', image: 'https://images.unsplash.com/photo-1549068106-b024baf5062d?auto=format&fit=crop&w=120&q=80' },
  { day: 2, row: 2, title: 'Reels', subtitle: 'Procedimentos', time: '14:00', accent: '#a9515a', image: 'https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&w=120&q=80' },
  { day: 2, row: 5, title: 'Histórias', subtitle: 'Bastidores', time: '20:00', accent: '#5b87b6', image: 'https://images.unsplash.com/photo-1580489944761-15a19d654956?auto=format&fit=crop&w=120&q=80' },
  { day: 3, row: 1, title: 'Reels', subtitle: 'Resultados', time: '10:00', accent: '#754fb2', image: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=120&q=80' },
  { day: 3, row: 3, title: 'Publicação', subtitle: 'Educação', time: '16:00', accent: '#897048', image: 'https://images.unsplash.com/photo-1529626455594-4ff0802cfb7e?auto=format&fit=crop&w=120&q=80' },
  { day: 4, row: 1, title: 'Carrossel', subtitle: 'Mitos e Verdades', time: '10:00', accent: '#a48e39', image: 'https://images.unsplash.com/photo-1517841905240-472988babdf9?auto=format&fit=crop&w=120&q=80' },
  { day: 4, row: 2, title: 'Carrossel', subtitle: 'Dicas rápidas', time: '14:00', accent: '#a48e39', image: 'https://images.unsplash.com/photo-1531123897727-8f129e1688ce?auto=format&fit=crop&w=120&q=80' },
  { day: 4, row: 5, title: 'Histórias', subtitle: 'Perguntas', time: '20:00', accent: '#69ad31', image: 'https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?auto=format&fit=crop&w=120&q=80' },
  { day: 5, row: 1, title: 'Publicação', subtitle: 'Benefícios', time: '10:00', accent: '#8054b0', image: 'https://images.unsplash.com/photo-1524504388940-b1c1722653e1?auto=format&fit=crop&w=120&q=80' },
  { day: 5, row: 3, title: 'Reels', subtitle: 'Antes e Depois', time: '16:00', accent: '#9b5555', image: 'https://images.unsplash.com/photo-1544725176-7c40e5a71c5e?auto=format&fit=crop&w=120&q=80' },
  { day: 6, row: 1, title: 'Carrossel', subtitle: 'Cuidados', time: '10:00', accent: '#4e9aad', image: 'https://images.unsplash.com/photo-1538108149393-fbbd81895907?auto=format&fit=crop&w=120&q=80' },
  { day: 6, row: 2, title: 'Histórias', subtitle: 'Depoimento', time: '14:00', accent: '#9b5555', image: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=120&q=80' },
  { day: 6, row: 5, title: 'Reels', subtitle: 'FAQ', time: '20:00', accent: '#9b5555', image: 'https://images.unsplash.com/photo-1551836022-d5d88e9218df?auto=format&fit=crop&w=120&q=80' },
  { day: 7, row: 1, title: 'Publicação', subtitle: 'Estilo de vida', time: '10:00', accent: '#8150a5', image: 'https://images.unsplash.com/photo-1531123897727-8f129e1688ce?auto=format&fit=crop&w=120&q=80' },
  { day: 7, row: 3, title: 'Histórias', subtitle: 'Dica do dia', time: '16:00', accent: '#9b742d', image: 'https://images.unsplash.com/photo-1517841905240-472988babdf9?auto=format&fit=crop&w=120&q=80' },
];

const days = [
  ['DOM', '18 MAI'],
  ['SEG', '19 MAI'],
  ['TER', '20 MAI'],
  ['QUA', '21 MAI'],
  ['QUI', '22 MAI'],
  ['SEX', '23 MAI'],
  ['SÁB', '24 MAI'],
];

const metricCards = [
  { label: 'Conteúdos gerados', value: '128', change: '+24%', detail: ' em relação à semana anterior', icon: FileText, tone: 'green' },
  { label: 'Publicações agendadas', value: '32', change: '+18%', detail: ' em relação à semana anterior', icon: CalendarDays, tone: 'green' },
  { label: 'Aprovações pendentes', value: '5', change: '', detail: '3 precisam de revisão', icon: Clock3, tone: 'amber' },
  { label: 'Engajamento (médio)', value: '4,82%', change: '+11%', detail: ' em relação à semana anterior', icon: ChartNoAxesCombined, tone: 'purple' },
];

const quickFlow = [
  { label: '1. Direcionamento', text: 'Defina o objetivo\nda semana', icon: ClipboardList },
  { label: '2. Estratégia', text: 'IA cria o plano\nde conteúdo', icon: CheckCircle2 },
  { label: '3. Geração', text: 'Conteúdos criados\nem lote', icon: Box },
  { label: '4. Edição', text: 'Edite e personalize\nse necessário', icon: Pencil },
  { label: '5. Aprovação', text: 'Envie para o cliente\naprovar', icon: Sparkles },
  { label: '6. Agendamento', text: 'Programe e publique\nautomaticamente', icon: CalendarDays },
  { label: '7. Análise', text: 'Acompanhe e otimize\nresultados', icon: BarChart3 },
];

const approvals = [
  { title: 'Carrossel - Mitos e Verdades', time: '09:30', image: 'https://images.unsplash.com/photo-1551836022-d5d88e9218df?auto=format&fit=crop&w=100&q=80' },
  { title: 'Reels - Depoimento', time: '09:15', image: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=100&q=80' },
  { title: 'Publicação - Promoção', time: '08:50', image: 'https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&w=100&q=80' },
];

const MiniSparkline = ({ tone }: { tone: string }) => (
  <svg viewBox="0 0 70 24" className="h-6 w-[70px]" aria-hidden="true">
    <path d="M1 20 C12 20 13 12 22 13 C31 15 35 22 45 13 C53 7 58 14 69 3" fill="none" stroke={tone === 'purple' ? '#9556d8' : '#8bd132'} strokeWidth="1.6" />
  </svg>
);

export const DashboardView: React.FC<DashboardViewProps> = ({ onNewPost, onNavigate }) => {
  const { activeCampaign, brainCompleteness, assets, posts } = useOperations();
  const { environmentMode, currentUser } = useGovernance();
  const isPersonal = environmentMode === 'personal';

  const publishedCount = posts.filter((p) => p.status === 'published').length;
  const scheduledCount = posts.filter((p) => p.status === 'scheduled').length;
  const pendingCount = posts.filter((p) => p.status === 'pending_approval' || p.status === 'in_review').length;

  const dynamicMetricCards = isPersonal
    ? [
        { label: 'Conteúdos criados', value: String(posts.length), change: '+24%', detail: ' produções autorais', icon: FileText, tone: 'green' },
        { label: 'Conteúdos publicados', value: String(publishedCount || 18), change: '+15%', detail: ' em suas redes', icon: CheckCircle2, tone: 'green' },
        { label: 'Agendamentos', value: String(scheduledCount || 8), change: '+10%', detail: ' programados', icon: CalendarDays, tone: 'green' },
        { label: 'Performance (médio)', value: '5,12%', change: '+14%', detail: ' alcance autoral', icon: ChartNoAxesCombined, tone: 'purple' },
      ]
    : [
        { label: 'Conteúdos gerados', value: String(posts.length || 128), change: '+24%', detail: ' na empresa', icon: FileText, tone: 'green' },
        { label: 'Publicações agendadas', value: String(scheduledCount || 32), change: '+18%', detail: ' na esteira', icon: CalendarDays, tone: 'green' },
        { label: 'Aprovações pendentes', value: String(pendingCount || 5), change: '', detail: 'necessitam revisão master', icon: Clock3, tone: 'amber' },
        { label: 'Engajamento (empresa)', value: '4,82%', change: '+11%', detail: ' consolidado equipe', icon: ChartNoAxesCombined, tone: 'purple' },
      ];

  return (
    <div className="vexel-dashboard min-h-screen px-6 pb-8 pt-4 2xl:px-10 space-y-6 max-w-[1700px] mx-auto">
      {/* Top Welcome Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-6 rounded-2xl border border-white/[0.06] bg-[#0c1015]/80 backdrop-blur-xl shadow-2xl shadow-black/50">
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
              Olá, Pedro <span className="text-[#8bd132] inline-block animate-pulse">●</span>
            </h1>
          </div>
          <p className="text-xs text-[#808c94]">
            Centro de controle operacional e produção acelerada com inteligência artificial.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          {activeCampaign && (
            <button
              type="button"
              onClick={() => onNavigate('strategy')}
              className="flex items-center gap-2 rounded-xl border border-white/[0.08] bg-[#121820] px-3.5 py-2 text-xs font-medium text-[#c0c8ce] transition hover:border-white/20 hover:bg-[#161e27]"
            >
              <Workflow className="h-3.5 w-3.5 text-[#8bd132]" />
              <span className="truncate max-w-[160px]">{activeCampaign.name}</span>
            </button>
          )}
          <button
            type="button"
            onClick={() => onNavigate('library')}
            className="flex items-center gap-2 rounded-xl border border-white/[0.08] bg-[#121820] px-3.5 py-2 text-xs font-medium text-[#c0c8ce] transition hover:border-white/20 hover:bg-[#161e27]"
          >
            <Box className="h-3.5 w-3.5 text-[#7b878f]" />
            <span>{assets.length + posts.length} Ativos no Acervo</span>
          </button>
          <button
            type="button"
            onClick={onNewPost}
            className="flex items-center gap-2 rounded-xl bg-[#8bd132] px-4 py-2 text-xs font-bold text-[#091106] transition-all hover:bg-[#9be24d] shadow-lg shadow-[#8bd132]/20"
          >
            <Plus className="h-4 w-4 stroke-[2.5]" />
            <span>Criar Conteúdo</span>
          </button>
        </div>
      </div>

      {/* Main Grid Section */}
      <div className="grid grid-cols-1 gap-6 min-[1150px]:grid-cols-[minmax(0,1fr)_340px] 2xl:grid-cols-[minmax(0,1fr)_410px]">
        {/* Left Primary Column */}
        <section className="min-w-0 space-y-6">
          {/* Top Metric Cards */}
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            {dynamicMetricCards.map((metric) => {
              const Icon = metric.icon;
              const isAccent = metric.tone === 'amber';
              return (
                <article
                  key={metric.label}
                  className="group relative flex flex-col justify-between overflow-hidden rounded-2xl border border-white/[0.06] bg-[#0c1015]/90 p-5 backdrop-blur-md transition-all duration-200 hover:border-white/15 hover:shadow-xl hover:shadow-black/50"
                >
                  <div className="flex items-start justify-between">
                    <span className="text-xs font-medium text-[#88949d]">{metric.label}</span>
                    <span
                      className={`grid h-8 w-8 place-items-center rounded-xl border ${
                        isAccent
                          ? 'border-amber-500/20 bg-amber-500/10 text-amber-400'
                          : 'border-white/[0.08] bg-white/[0.04] text-[#8bd132]'
                      }`}
                    >
                      <Icon className="h-4 w-4" strokeWidth={1.8} />
                    </span>
                  </div>

                  <div className="mt-4 flex items-end justify-between">
                    <div>
                      <div className="text-2xl font-bold tracking-tight text-white">{metric.value}</div>
                      <div className="mt-1 flex items-center gap-1 text-[10px] text-[#78848c]">
                        {metric.change && (
                          <span className="font-semibold text-[#8bd132]">{metric.change}</span>
                        )}
                        <span>{metric.detail}</span>
                      </div>
                    </div>
                    {(metric.tone === 'green' || metric.tone === 'purple') && <MiniSparkline tone={metric.tone} />}
                  </div>
                </article>
              );
            })}
          </div>

          {/* Interactive Calendar Schedule Command */}
          <section className="rounded-2xl border border-white/[0.06] bg-[#0c1015]/90 p-6 backdrop-blur-xl shadow-2xl shadow-black/40">
            <div className="mb-5 flex flex-wrap items-center justify-between gap-4 border-b border-white/[0.06] pb-4">
              <div className="space-y-0.5">
                <div className="flex items-center gap-2">
                  <CalendarDays className="h-4 w-4 text-[#8bd132]" />
                  <h2 className="text-sm font-bold tracking-tight text-white">Cronograma Visual de Publicações</h2>
                </div>
                <p className="text-[11px] text-[#78848c]">Grade da semana com distribuição de conteúdos por canal</p>
              </div>

              <div className="flex items-center gap-3">
                <div className="flex items-center gap-1.5 rounded-xl border border-white/[0.08] bg-[#070a0d] px-3 py-1.5 text-xs text-[#9ea9b1]">
                  <span>Visão:</span>
                  <span className="font-semibold text-white">Semanal</span>
                  <ChevronDown className="h-3.5 w-3.5 text-[#6c7880]" />
                </div>
                <button
                  type="button"
                  onClick={onNewPost}
                  className="flex items-center gap-1.5 rounded-xl bg-white/[0.08] border border-white/10 px-3.5 py-1.5 text-xs font-semibold text-white transition hover:bg-white/15"
                >
                  <Plus className="h-3.5 w-3.5 text-[#8bd132]" />
                  <span>Novo Item</span>
                </button>
              </div>
            </div>

            {/* Days Header */}
            <div className="grid grid-cols-[46px_repeat(7,minmax(0,1fr))] border-b border-white/[0.06]">
              <div className="flex items-center justify-center">
                <button type="button" className="grid h-7 w-7 place-items-center rounded-lg bg-white/[0.04] text-[#808c94] hover:text-white">
                  <ChevronLeft className="h-4 w-4" />
                </button>
              </div>
              {days.map(([name, date], index) => (
                <div
                  key={date}
                  className={`flex h-12 flex-col items-center justify-center border-l border-white/[0.04] text-xs transition-all ${
                    index === 3 ? 'border-t-2 border-t-[#8bd132] bg-[#8bd132]/[0.06]' : ''
                  }`}
                >
                  <span className={`font-semibold ${index === 3 ? 'text-[#8bd132]' : 'text-[#d0d7dc]'}`}>{name}</span>
                  <span className={`text-[10px] ${index === 3 ? 'text-[#8bd132]/80 font-medium' : 'text-[#6e7a82]'}`}>{date}</span>
                </div>
              ))}
            </div>

            {/* Grid Matrix */}
            <div className="relative grid grid-cols-[46px_repeat(7,minmax(0,1fr))] grid-rows-5 pt-2">
              {[8, 10, 12, 14, 16].map((time, index) => (
                <div key={time} style={{ gridColumn: 1, gridRow: index + 1 }} className="pr-3 pt-2 text-right text-[10px] font-mono text-[#626e76]">
                  {String(time).padStart(2, '0')}:00
                </div>
              ))}
              {Array.from({ length: 35 }).map((_, index) => {
                const day = (index % 7) + 1;
                const row = Math.floor(index / 7) + 1;
                return (
                  <div
                    key={index}
                    style={{ gridColumn: day + 1, gridRow: row }}
                    className={`h-[58px] border-b border-l border-white/[0.04] ${
                      day === 4 ? 'bg-[#8bd132]/[0.02]' : 'bg-transparent'
                    }`}
                  />
                );
              })}

              {calendarItems.map((item, index) => (
                <button
                  key={`${item.day}-${item.row}-${index}`}
                  type="button"
                  style={{ gridColumn: item.day + 1, gridRow: item.row, borderColor: `${item.accent}80` }}
                  className="z-10 m-[3px] flex min-w-0 items-center gap-2 rounded-xl border bg-[#11171f] p-1.5 text-left shadow-lg shadow-black/40 transition-all hover:-translate-y-0.5 hover:border-white/30 hover:bg-[#161e27]"
                >
                  <img src={item.image} alt="" className="h-8 w-7 shrink-0 rounded-lg object-cover" />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-[10px] font-bold text-white">{item.title}</span>
                    <span className="block truncate text-[9px] text-[#8e9aa2]">{item.subtitle}</span>
                  </span>
                  <Instagram className="h-3 w-3 shrink-0 text-[#e780a8]" />
                </button>
              ))}
            </div>

            <div className="mt-4 flex flex-wrap items-center gap-6 border-t border-white/[0.04] pt-3 text-[10px] text-[#78848c]">
              {[
                ['#8bd132', 'Publicado / Agendado'],
                ['#f2b33d', 'Em Aprovação'],
                ['#6ba7e8', 'Rascunho Pronto'],
                ['#e35d63', 'Ajuste Solicitado'],
              ].map(([color, label]) => (
                <span key={label} className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full" style={{ backgroundColor: color }} />
                  {label}
                </span>
              ))}
            </div>
          </section>

          {/* Quick Production Process */}
          <section className="rounded-2xl border border-white/[0.06] bg-[#0c1015]/90 p-6 backdrop-blur-xl">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-xs font-bold uppercase tracking-widest text-[#6c7880]">Esteira de Produção Inteligente</h2>
              <span className="text-[10px] text-[#8bd132] font-semibold">7 Passos Automatizados</span>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-7 gap-3">
              {quickFlow.map((step, index) => {
                const Icon = step.icon;
                return (
                  <button
                    key={step.label}
                    type="button"
                    onClick={onNewPost}
                    className="group flex flex-col items-center rounded-xl border border-white/[0.05] bg-[#080b0e] p-3 text-center transition-all hover:border-[#8bd132]/40 hover:bg-[#11171f]"
                  >
                    <span className="grid h-10 w-10 place-items-center rounded-xl border border-white/[0.08] bg-white/[0.03] text-[#8bd132] group-hover:scale-105 group-hover:bg-[#8bd132]/10 transition-all">
                      <Icon className="h-4 w-4" />
                    </span>
                    <span className="mt-2 text-[10px] font-bold text-white">{step.label}</span>
                    <span className="mt-1 text-[9px] leading-tight text-[#78848c] whitespace-pre-line">{step.text}</span>
                  </button>
                );
              })}
            </div>
          </section>
        </section>

        {/* Right Sidebar Column */}
        <aside className="space-y-6">
          {/* Status do Ambiente (Empresa ou Pessoal) */}
          {isPersonal ? (
            <section className="rounded-2xl border border-white/[0.06] bg-[#0c1015]/90 p-5 backdrop-blur-xl shadow-2xl shadow-black/40">
              <div className="flex items-center justify-between border-b border-white/[0.06] pb-3">
                <div className="flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-[#8bd132]" />
                  <h2 className="text-xs font-bold text-white">Ambiente Pessoal Ativo</h2>
                </div>
                <span className="rounded-full bg-[#8bd132]/10 border border-[#8bd132]/20 px-2 py-0.5 text-[9px] font-bold text-[#8bd132]">
                  Modo Solo
                </span>
              </div>
              <div className="mt-4 space-y-3 text-xs text-[#9ea9b0]">
                <div className="flex items-start gap-2.5 rounded-xl border border-white/[0.04] bg-[#080b0e] p-3">
                  <CheckCircle2 className="h-4 w-4 text-[#8bd132] shrink-0 mt-0.5" />
                  <div>
                    <strong className="block text-white font-semibold text-[11px]">Publicação Direta Ativa</strong>
                    <span className="text-[10px] text-[#78848c]">Conteúdos agendados e publicados vão direto aos canais sem fila de aprovação.</span>
                  </div>
                </div>
                <div className="flex items-start gap-2.5 rounded-xl border border-white/[0.04] bg-[#080b0e] p-3">
                  <UserRound className="h-4 w-4 text-[#8bd132] shrink-0 mt-0.5" />
                  <div>
                    <strong className="block text-white font-semibold text-[11px]">Operação Autônoma</strong>
                    <span className="text-[10px] text-[#78848c]">Sem limitação de permissões corporativas, auditoria entre usuários ou gestão de equipe.</span>
                  </div>
                </div>
              </div>
            </section>
          ) : (
            <section className="rounded-2xl border border-white/[0.06] bg-[#0c1015]/90 p-5 backdrop-blur-xl shadow-2xl shadow-black/40">
              <div className="flex items-center justify-between border-b border-white/[0.06] pb-3">
                <div className="flex items-center gap-2">
                  <Clock3 className="h-4 w-4 text-amber-400" />
                  <h2 className="text-xs font-bold text-white">Fila de Aprovações Corporativas</h2>
                </div>
                <button
                  type="button"
                  onClick={() => onNavigate('approvals')}
                  className="text-[10px] font-bold text-[#8bd132] hover:underline"
                >
                  Ver Todas
                </button>
              </div>
              <div className="mt-4 space-y-3">
                {approvals.map((item) => (
                  <button
                    key={item.title}
                    type="button"
                    onClick={() => onNavigate('approvals')}
                    className="flex w-full items-center gap-3 rounded-xl border border-white/[0.04] bg-[#080b0e] p-2.5 text-left transition hover:border-white/10 hover:bg-[#11171f]"
                  >
                    <img src={item.image} alt="" className="h-11 w-11 rounded-lg object-cover" />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-xs font-semibold text-white">{item.title}</span>
                      <span className="block text-[10px] text-[#78848c]">Equipe Corporativa</span>
                    </span>
                    <span className="rounded-full bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 text-[9px] font-bold text-amber-400">
                      Pendente
                    </span>
                  </button>
                ))}
              </div>
            </section>
          )}

          {/* Performance Summary Widget */}
          <section className="rounded-2xl border border-white/[0.06] bg-[#0c1015]/90 p-5 backdrop-blur-xl shadow-2xl shadow-black/40">
            <div className="flex items-center justify-between border-b border-white/[0.06] pb-3">
              <div className="flex items-center gap-2">
                <BarChart3 className="h-4 w-4 text-[#8bd132]" />
                <h2 className="text-xs font-bold text-white">Desempenho Semanal</h2>
              </div>
              <button
                type="button"
                onClick={() => onNavigate('analytics')}
                className="text-[10px] font-bold text-[#8bd132] hover:underline"
              >
                Detalhes
              </button>
            </div>

            <div className="mt-4 space-y-2.5">
              {[
                ['Alcance Total', '128.7K', '+14.5%'],
                ['Impressões', '256.3K', '+11.2%'],
                ['Engajamento Médio', '4.82%', '+11.0%'],
                ['Cliques no Link', '3.265', '+8.7%'],
              ].map(([label, value, gain]) => (
                <div key={label} className="flex items-center justify-between text-xs py-1 border-b border-white/[0.03] last:border-0">
                  <span className="text-[#808c94]">{label}</span>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-white">{value}</span>
                    <span className="text-[10px] font-bold text-[#8bd132]">{gain}</span>
                  </div>
                </div>
              ))}
            </div>

            {/* Sparkline Graphic Canvas */}
            <div className="relative mt-5 h-28 w-full">
              <svg viewBox="0 0 330 112" className="h-full w-full" preserveAspectRatio="none">
                <defs>
                  <linearGradient id="area" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0" stopColor="#8bd132" stopOpacity="0.25" />
                    <stop offset="1" stopColor="#8bd132" stopOpacity="0" />
                  </linearGradient>
                </defs>
                <path d="M6 67 C34 48 44 55 69 67 C91 78 109 42 137 48 C169 55 181 86 215 72 C244 61 254 71 282 54 C304 41 318 38 326 35 L326 112 L6 112 Z" fill="url(#area)" />
                <path d="M6 67 C34 48 44 55 69 67 C91 78 109 42 137 48 C169 55 181 86 215 72 C244 61 254 71 282 54 C304 41 318 38 326 35" fill="none" stroke="#8bd132" strokeWidth="2" />
              </svg>
            </div>
          </section>

          {/* AI Strategic Recommendation Box */}
          <section className="relative overflow-hidden rounded-2xl border border-[#8bd132]/30 bg-gradient-to-br from-[#8bd132]/10 via-[#0c1015] to-[#080b0e] p-5 shadow-2xl">
            <div className="flex items-center gap-2 text-[#8bd132]">
              <Sparkles className="h-4 w-4" />
              <h2 className="text-xs font-bold uppercase tracking-wider">Insight da Inteligência Artificial</h2>
            </div>
            <p className="mt-3 text-xs leading-relaxed text-[#c0c9cf]">
              Seus Reels com depoimentos tiveram <strong className="text-white">+27% de alcance</strong> que a média. Recomendamos gerar 3 variações focadas nessa temática para a próxima semana.
            </p>
            <button
              type="button"
              onClick={onNewPost}
              className="mt-4 flex items-center gap-2 rounded-xl bg-[#8bd132] px-4 py-2 text-xs font-bold text-[#080e05] transition hover:bg-[#9be24d] shadow-lg shadow-[#8bd132]/20"
            >
              <Sparkles className="h-3.5 w-3.5" />
              <span>Gerar Variações com IA</span>
            </button>
          </section>
        </aside>
      </div>
    </div>
  );
};
