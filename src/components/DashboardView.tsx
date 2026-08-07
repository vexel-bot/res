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

export const DashboardView: React.FC<DashboardViewProps> = ({
  onNewPost,
  onNavigate,
  activeWorkspace,
  onOpenCampaignWizard,
}) => {
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
    <div className="vexel-dashboard min-h-screen px-8 pb-12 pt-6 2xl:px-12 space-y-8 max-w-[1720px] mx-auto">
      {/* Top Command Welcome Banner */}
      <div className="relative overflow-hidden flex flex-col md:flex-row md:items-center justify-between gap-6 p-7 rounded-3xl border border-white/[0.08] bg-gradient-to-r from-[#0d1217] via-[#090d10] to-[#070a0d] backdrop-blur-2xl shadow-[0_16px_48px_rgba(0,0,0,0.7)]">
        <div className="absolute top-0 right-1/4 w-96 h-96 bg-[#8bd132]/5 blur-[120px] pointer-events-none rounded-full" />
        <div className="relative z-10 space-y-2">
          <div className="flex flex-wrap items-center gap-3">
            <span className="flex items-center gap-1.5 rounded-full border border-[#8bd132]/30 bg-[#8bd132]/10 px-3 py-1 text-[10px] font-mono font-bold uppercase tracking-wider text-[#8bd132]">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#8bd132] opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-[#8bd132]"></span>
              </span>
              Sistema Operacional Ativo
            </span>
            <span className="text-[11px] text-[#6c7880]">
              Workspace: <strong className="text-white font-semibold">{activeWorkspace?.name || 'Geral'}</strong>
            </span>
          </div>

          <h1 className="text-3xl font-extrabold tracking-tight text-white flex items-center gap-3">
            Central Operacional de Conteúdo
          </h1>
          <p className="text-xs text-[#8e9aa2] max-w-xl leading-relaxed">
            Painel unificado com esteira acelerada de criação, cronograma inteligente, métricas em tempo real e orquestração de IA.
          </p>
        </div>

        <div className="relative z-10 flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={onNewPost}
            className="flex items-center gap-2 rounded-xl bg-[#8bd132] px-4 py-2.5 text-xs font-bold text-[#080e05] transition-all hover:bg-[#9be24d] hover:shadow-[0_0_20px_rgba(139,209,50,0.3)] active:scale-[0.98]"
          >
            <Plus className="h-4 w-4" />
            <span>Criar Novo Conteúdo</span>
          </button>
          <button
            type="button"
            onClick={onOpenCampaignWizard}
            className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.05] px-4 py-2.5 text-xs font-semibold text-white transition-all hover:bg-white/10 hover:border-white/20 active:scale-[0.98]"
          >
            <Sparkles className="h-4 w-4 text-[#8bd132]" />
            <span>Assistente IA</span>
          </button>
        </div>
      </div>

      {/* Main Grid Section */}
      <div className="grid grid-cols-1 gap-8 min-[1180px]:grid-cols-[minmax(0,1fr)_360px] 2xl:grid-cols-[minmax(0,1fr)_420px]">
        {/* Left Primary Column */}
        <section className="min-w-0 space-y-8">
          {/* Top Metric Cards - Redesigned Bento Row */}
          <div className="grid grid-cols-2 gap-5 lg:grid-cols-4">
            {dynamicMetricCards.map((metric) => {
              const Icon = metric.icon;
              const isAccent = metric.tone === 'amber';
              return (
                <article
                  key={metric.label}
                  className="group relative flex flex-col justify-between overflow-hidden rounded-2xl border border-white/[0.05] bg-gradient-to-b from-[#0e1318] to-[#080b0e] p-6 backdrop-blur-xl transition-all duration-200 hover:border-white/15 hover:shadow-[0_12px_36px_rgba(0,0,0,0.6)]"
                >
                  <div className="flex items-start justify-between gap-2">
                    <span className="text-xs font-semibold text-[#717d85] tracking-tight">{metric.label}</span>
                    <span
                      className={`grid h-9 w-9 place-items-center rounded-xl border ${
                        isAccent
                          ? 'border-amber-500/20 bg-amber-500/10 text-amber-400'
                          : 'border-white/[0.08] bg-white/[0.03] text-[#8bd132]'
                      }`}
                    >
                      <Icon className="h-4 w-4" strokeWidth={1.8} />
                    </span>
                  </div>

                  <div className="mt-6 flex items-end justify-between">
                    <div>
                      <div className="text-3xl font-extrabold tracking-tight text-white">{metric.value}</div>
                      <div className="mt-1.5 flex items-center gap-1.5 text-[11px] text-[#627078]">
                        {metric.change && (
                          <span className="font-bold text-[#8bd132]">{metric.change}</span>
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
          <section className="rounded-2xl border border-white/[0.05] bg-gradient-to-b from-[#0e1318] to-[#080b0e] p-7 backdrop-blur-xl shadow-[0_16px_48px_rgba(0,0,0,0.6)]">
            <div className="mb-6 flex flex-wrap items-center justify-between gap-4 border-b border-white/[0.05] pb-5">
              <div className="space-y-1">
                <div className="flex items-center gap-2.5">
                  <CalendarDays className="h-4 w-4 text-[#8bd132]" />
                  <h2 className="text-sm font-bold tracking-tight text-white">Cronograma Visual de Publicações</h2>
                </div>
                <p className="text-xs text-[#717d85]">Grade da semana com distribuição de conteúdos por canal e horário</p>
              </div>

              <div className="flex items-center gap-3">
                <div className="flex items-center gap-2 rounded-xl border border-white/[0.08] bg-[#070a0d] px-3.5 py-2 text-xs text-[#9ea9b1]">
                  <span>Visão:</span>
                  <span className="font-semibold text-white">Semanal</span>
                  <ChevronDown className="h-3.5 w-3.5 text-[#5a6770]" />
                </div>
                <button
                  type="button"
                  onClick={onNewPost}
                  className="flex items-center gap-2 rounded-xl bg-white/[0.06] border border-white/10 px-4 py-2 text-xs font-semibold text-white transition hover:bg-white/12"
                >
                  <Plus className="h-3.5 w-3.5 text-[#8bd132]" />
                  <span>Novo Item</span>
                </button>
              </div>
            </div>

            {/* Days Header */}
            <div className="grid grid-cols-[48px_repeat(7,minmax(0,1fr))] border-b border-white/[0.05]">
              <div className="flex items-center justify-center">
                <button type="button" className="grid h-8 w-8 place-items-center rounded-xl bg-white/[0.03] text-[#717d85] hover:text-white transition-colors">
                  <ChevronLeft className="h-4 w-4" />
                </button>
              </div>
              {days.map(([name, date], index) => (
                <div
                  key={date}
                  className={`flex h-14 flex-col items-center justify-center border-l border-white/[0.04] text-xs transition-all ${
                    index === 3 ? 'border-t-2 border-t-[#8bd132] bg-[#8bd132]/[0.05]' : ''
                  }`}
                >
                  <span className={`font-bold ${index === 3 ? 'text-[#8bd132]' : 'text-[#d0d7dc]'}`}>{name}</span>
                  <span className={`text-[10px] font-mono ${index === 3 ? 'text-[#8bd132]/90' : 'text-[#627078]'}`}>{date}</span>
                </div>
              ))}
            </div>

            {/* Grid Matrix */}
            <div className="relative grid grid-cols-[48px_repeat(7,minmax(0,1fr))] grid-rows-5 pt-3">
              {[8, 10, 12, 14, 16].map((time, index) => (
                <div key={time} style={{ gridColumn: 1, gridRow: index + 1 }} className="pr-3 pt-2 text-right text-[10px] font-mono text-[#5a6770]">
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
                    className={`h-[64px] border-b border-l border-white/[0.04] ${
                      day === 4 ? 'bg-[#8bd132]/[0.02]' : 'bg-transparent'
                    }`}
                  />
                );
              })}

              {calendarItems.map((item, index) => (
                <button
                  key={`${item.day}-${item.row}-${index}`}
                  type="button"
                  style={{ gridColumn: item.day + 1, gridRow: item.row, borderColor: `${item.accent}60` }}
                  className="z-10 m-[3px] flex min-w-0 items-center gap-2 rounded-xl border bg-[#0d1217] p-2 text-left shadow-lg shadow-black/50 transition-all hover:-translate-y-0.5 hover:border-white/30 hover:bg-[#121820]"
                >
                  <img src={item.image} alt="" className="h-9 w-8 shrink-0 rounded-lg object-cover" />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-[11px] font-bold text-white">{item.title}</span>
                    <span className="block truncate text-[9px] text-[#8e9aa2]">{item.subtitle}</span>
                  </span>
                  <Instagram className="h-3.5 w-3.5 shrink-0 text-[#e780a8]" />
                </button>
              ))}
            </div>

            <div className="mt-5 flex flex-wrap items-center gap-6 border-t border-white/[0.04] pt-4 text-xs text-[#717d85]">
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
          <section className="rounded-2xl border border-white/[0.05] bg-gradient-to-b from-[#0e1318] to-[#080b0e] p-7 backdrop-blur-xl">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xs font-mono font-bold uppercase tracking-[0.2em] text-[#627078]">Esteira de Produção Inteligente</h2>
              <span className="text-[10px] text-[#8bd132] font-semibold bg-[#8bd132]/10 border border-[#8bd132]/20 px-2.5 py-0.5 rounded-full">
                7 Passos Automatizados
              </span>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-7 gap-3.5">
              {quickFlow.map((step) => {
                const Icon = step.icon;
                return (
                  <button
                    key={step.label}
                    type="button"
                    onClick={onNewPost}
                    className="group flex flex-col items-center rounded-2xl border border-white/[0.05] bg-[#070a0d] p-4 text-center transition-all hover:border-[#8bd132]/40 hover:bg-[#10151c]"
                  >
                    <span className="grid h-10 w-10 place-items-center rounded-xl border border-white/[0.08] bg-white/[0.03] text-[#8bd132] group-hover:scale-110 group-hover:bg-[#8bd132]/10 transition-all duration-200">
                      <Icon className="h-4 w-4" />
                    </span>
                    <span className="mt-3 text-[11px] font-bold text-white">{step.label}</span>
                    <span className="mt-1 text-[9px] leading-tight text-[#717d85] whitespace-pre-line">{step.text}</span>
                  </button>
                );
              })}
            </div>
          </section>
        </section>

        {/* Right Sidebar Column */}
        <aside className="space-y-8">
          {/* Status do Ambiente */}
          {isPersonal ? (
            <section className="rounded-2xl border border-white/[0.05] bg-gradient-to-b from-[#0e1318] to-[#080b0e] p-6 backdrop-blur-xl shadow-[0_12px_36px_rgba(0,0,0,0.6)]">
              <div className="flex items-center justify-between border-b border-white/[0.05] pb-4">
                <div className="flex items-center gap-2.5">
                  <Sparkles className="h-4 w-4 text-[#8bd132]" />
                  <h2 className="text-xs font-bold text-white">Ambiente Pessoal Ativo</h2>
                </div>
                <span className="rounded-full bg-[#8bd132]/10 border border-[#8bd132]/20 px-2.5 py-0.5 text-[9px] font-bold text-[#8bd132]">
                  Modo Solo
                </span>
              </div>
              <div className="mt-5 space-y-3.5 text-xs text-[#a0abb2]">
                <div className="flex items-start gap-3 rounded-xl border border-white/[0.04] bg-[#070a0d] p-3.5">
                  <CheckCircle2 className="h-4 w-4 text-[#8bd132] shrink-0 mt-0.5" />
                  <div>
                    <strong className="block text-white font-semibold text-[11px]">Publicação Direta Ativa</strong>
                    <span className="text-[10px] text-[#717d85]">Conteúdos agendados e publicados vão direto aos canais sem fila de aprovação.</span>
                  </div>
                </div>
                <div className="flex items-start gap-3 rounded-xl border border-white/[0.04] bg-[#070a0d] p-3.5">
                  <UserRound className="h-4 w-4 text-[#8bd132] shrink-0 mt-0.5" />
                  <div>
                    <strong className="block text-white font-semibold text-[11px]">Operação Autônoma</strong>
                    <span className="text-[10px] text-[#717d85]">Sem limitação de permissões corporativas, auditoria entre usuários ou gestão de equipe.</span>
                  </div>
                </div>
              </div>
            </section>
          ) : (
            <section className="rounded-2xl border border-white/[0.05] bg-gradient-to-b from-[#0e1318] to-[#080b0e] p-6 backdrop-blur-xl shadow-[0_12px_36px_rgba(0,0,0,0.6)]">
              <div className="flex items-center justify-between border-b border-white/[0.05] pb-4">
                <div className="flex items-center gap-2.5">
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
              <div className="mt-5 space-y-3">
                {approvals.map((item) => (
                  <button
                    key={item.title}
                    type="button"
                    onClick={() => onNavigate('approvals')}
                    className="flex w-full items-center gap-3.5 rounded-xl border border-white/[0.04] bg-[#070a0d] p-3 text-left transition-all hover:border-white/10 hover:bg-[#10151c]"
                  >
                    <img src={item.image} alt="" className="h-11 w-11 rounded-lg object-cover" />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-xs font-bold text-white">{item.title}</span>
                      <span className="block text-[10px] text-[#717d85]">Equipe Corporativa</span>
                    </span>
                    <span className="rounded-full bg-amber-500/10 border border-amber-500/20 px-2.5 py-0.5 text-[9px] font-bold text-amber-400">
                      Pendente
                    </span>
                  </button>
                ))}
              </div>
            </section>
          )}

          {/* Performance Summary Widget */}
          <section className="rounded-2xl border border-white/[0.05] bg-gradient-to-b from-[#0e1318] to-[#080b0e] p-6 backdrop-blur-xl shadow-[0_12px_36px_rgba(0,0,0,0.6)]">
            <div className="flex items-center justify-between border-b border-white/[0.05] pb-4">
              <div className="flex items-center gap-2.5">
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

            <div className="mt-5 space-y-3">
              {[
                ['Alcance Total', '128.7K', '+14.5%'],
                ['Impressões', '256.3K', '+11.2%'],
                ['Engajamento Médio', '4.82%', '+11.0%'],
                ['Cliques no Link', '3.265', '+8.7%'],
              ].map(([label, value, gain]) => (
                <div key={label} className="flex items-center justify-between text-xs py-1.5 border-b border-white/[0.03] last:border-0">
                  <span className="text-[#717d85]">{label}</span>
                  <div className="flex items-center gap-2.5">
                    <span className="font-bold font-mono text-white">{value}</span>
                    <span className="text-[10px] font-bold text-[#8bd132]">{gain}</span>
                  </div>
                </div>
              ))}
            </div>

            {/* Sparkline Graphic Canvas */}
            <div className="relative mt-6 h-28 w-full">
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
          <section className="relative overflow-hidden rounded-2xl border border-[#8bd132]/30 bg-gradient-to-br from-[#8bd132]/10 via-[#0a0e12] to-[#06080a] p-6 shadow-2xl">
            <div className="flex items-center gap-2 text-[#8bd132]">
              <Sparkles className="h-4 w-4" />
              <h2 className="text-xs font-mono font-bold uppercase tracking-wider">Insight da IA Copilot</h2>
            </div>
            <p className="mt-3.5 text-xs leading-relaxed text-[#c0c9cf]">
              Seus Reels com depoimentos tiveram <strong className="text-white">+27% de alcance</strong> que a média. Recomendamos gerar 3 variações focadas nessa temática para a próxima semana.
            </p>
            <button
              type="button"
              onClick={onNewPost}
              className="mt-5 flex items-center gap-2.5 rounded-xl bg-[#8bd132] px-4 py-2.5 text-xs font-bold text-[#080e05] transition-all hover:bg-[#9be24d] shadow-[0_0_20px_rgba(139,209,50,0.25)]"
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
