import React from 'react';
import {
  ArrowRight,
  BarChart3,
  CalendarDays,
  ChartNoAxesCombined,
  CheckCircle2,
  ChevronDown,
  Clock3,
  FileText,
  Instagram,
  Plus,
  Sparkles,
} from 'lucide-react';
import type { AIActionSuggestion, NavigationTab, Post, Workspace } from '../types';
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

const days = [
  ['DOM', '18'], ['SEG', '19'], ['TER', '20'], ['QUA', '21'], ['QUI', '22'], ['SEX', '23'], ['SÁB', '24'],
];

const schedule = [
  { day: 1, row: 1, title: 'Carrossel', subtitle: 'Saúde', image: 'https://images.unsplash.com/photo-1559757148-5c350d0d3c56?auto=format&fit=crop&w=120&q=80' },
  { day: 1, row: 3, title: 'Stories', subtitle: 'Dicas', image: 'https://images.unsplash.com/photo-1551836022-d5d88e9218df?auto=format&fit=crop&w=120&q=80' },
  { day: 2, row: 1, title: 'Post', subtitle: 'Promoção', image: 'https://images.unsplash.com/photo-1549068106-b024baf5062d?auto=format&fit=crop&w=120&q=80' },
  { day: 2, row: 2, title: 'Reels', subtitle: 'Processos', image: 'https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&w=120&q=80' },
  { day: 3, row: 1, title: 'Reels', subtitle: 'Resultados', image: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=120&q=80' },
  { day: 3, row: 3, title: 'Post', subtitle: 'Educação', image: 'https://images.unsplash.com/photo-1529626455594-4ff0802cfb7e?auto=format&fit=crop&w=120&q=80' },
  { day: 4, row: 1, title: 'Carrossel', subtitle: 'Mitos', image: 'https://images.unsplash.com/photo-1517841905240-472988babdf9?auto=format&fit=crop&w=120&q=80' },
  { day: 4, row: 2, title: 'Carrossel', subtitle: 'Dicas', image: 'https://images.unsplash.com/photo-1531123897727-8f129e1688ce?auto=format&fit=crop&w=120&q=80' },
  { day: 5, row: 1, title: 'Post', subtitle: 'Benefícios', image: 'https://images.unsplash.com/photo-1524504388940-b1c1722653e1?auto=format&fit=crop&w=120&q=80' },
  { day: 6, row: 2, title: 'Stories', subtitle: 'Depoimento', image: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=120&q=80' },
  { day: 7, row: 1, title: 'Post', subtitle: 'Lifestyle', image: 'https://images.unsplash.com/photo-1531123897727-8f129e1688ce?auto=format&fit=crop&w=120&q=80' },
];

const approvalItems = [
  { title: 'Carrossel — Mitos e Verdades', meta: 'Equipe Corporativa · 09:30', image: 'https://images.unsplash.com/photo-1551836022-d5d88e9218df?auto=format&fit=crop&w=100&q=80' },
  { title: 'Reels — Depoimento', meta: 'Equipe Corporativa · 09:15', image: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=100&q=80' },
  { title: 'Post — Promoção', meta: 'Equipe Corporativa · 08:50', image: 'https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&w=100&q=80' },
];

const flow = ['Direcionamento', 'Estratégia', 'Geração', 'Edição', 'Aprovação', 'Agendamento', 'Análise'];

export const DashboardView: React.FC<DashboardViewProps> = ({
  activeWorkspace,
  onNavigate,
  onOpenCampaignWizard,
  onNewPost,
}) => {
  const { posts } = useOperations();
  const { environmentMode } = useGovernance();
  const isPersonal = environmentMode === 'personal';
  const published = posts.filter((post) => post.status === 'published').length;
  const scheduled = posts.filter((post) => post.status === 'scheduled').length;
  const pending = posts.filter((post) => post.status === 'pending_approval' || post.status === 'in_review').length;
  const metrics = isPersonal
    ? [
        ['Conteúdos', String(posts.length), '+24%', FileText],
        ['Publicados', String(published || 18), '+15%', CheckCircle2],
        ['Agendados', String(scheduled || 8), '+10%', CalendarDays],
        ['Performance', '5,12%', '+14%', ChartNoAxesCombined],
      ]
    : [
        ['Conteúdos', String(posts.length || 128), '+24%', FileText],
        ['Agendados', String(scheduled || 32), '+18%', CalendarDays],
        ['Em aprovação', String(pending || 5), '3 urgentes', Clock3],
        ['Engajamento', '4,82%', '+11%', ChartNoAxesCombined],
      ];

  return (
    <div className="clicko-dashboard-editorial min-h-screen px-7 pb-10 pt-7 2xl:px-10 2xl:pt-9">
      <header className="clicko-dashboard-hero flex flex-col gap-7 border-b border-white/[0.07] pb-8 xl:flex-row xl:items-end xl:justify-between">
        <div className="max-w-3xl">
          <div className="mb-4 flex flex-wrap items-center gap-3 text-[9px] font-medium uppercase tracking-[0.22em] text-[#78848c]">
            <span className="flex items-center gap-2 text-[#8bd132]"><span className="h-1.5 w-1.5 rounded-full bg-[#8bd132]" />Operação ativa</span>
            <span className="h-3 w-px bg-white/10" />
            <span>{activeWorkspace?.name || 'Workspace geral'}</span>
          </div>
          <h1 className="max-w-none text-[clamp(26px,2.6vw,42px)] font-medium leading-[1.08] tracking-[-0.045em] text-white">
            Sua operação, em um único ritmo.
          </h1>
          <p className="mt-3 max-w-2xl text-[13px] leading-6 text-[#7f8a91]">
            Conteúdo, agenda e performance organizados para você decidir rápido e produzir melhor.
          </p>
        </div>
        <div className="flex flex-wrap gap-2.5">
          <button type="button" onClick={onOpenCampaignWizard} className="h-10 rounded-lg border border-white/10 px-4 text-[11px] font-medium text-[#c6cdd1] transition-colors hover:bg-white/[0.04] hover:text-white">
            <Sparkles className="mr-2 inline h-3.5 w-3.5 text-[#8bd132]" />Assistente IA
          </button>
          <button type="button" onClick={onNewPost} className="h-10 rounded-lg bg-[#8bd132] px-4 text-[11px] font-semibold text-[#101608] transition-colors hover:bg-[#9be24d]">
            <Plus className="mr-2 inline h-3.5 w-3.5" />Novo conteúdo
          </button>
        </div>
      </header>

      <section className="clicko-dashboard-metrics grid border-b border-white/[0.07] sm:grid-cols-2 xl:grid-cols-4">
        {metrics.map(([label, value, detail, Icon], index) => {
          const MetricIcon = Icon as React.ComponentType<{ className?: string }>;
          return (
            <article key={String(label)} className={`clicko-metric-cell relative py-7 sm:px-6 ${index === 0 ? 'sm:pl-0' : ''} ${index > 0 ? 'sm:border-l sm:border-white/[0.06]' : ''}`}>
              <div className="flex items-center gap-2 text-[10px] font-medium uppercase tracking-[0.13em] text-[#6e7980]"><MetricIcon className="h-3.5 w-3.5" />{String(label)}</div>
              <div className="mt-3 flex items-end justify-between gap-4">
                <strong className="text-[clamp(28px,3vw,42px)] font-medium leading-none tracking-[-0.04em] text-white">{String(value)}</strong>
                <span className="pb-1 text-[10px] font-semibold text-[#8bd132]">{String(detail)}</span>
              </div>
            </article>
          );
        })}
      </section>

      <div className="clicko-dashboard-body grid gap-0 xl:grid-cols-[minmax(0,1fr)_320px] 2xl:grid-cols-[minmax(0,1fr)_350px]">
        <section className="clicko-dashboard-calendar min-w-0 py-8 xl:pr-8">
          <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
            <div>
              <span className="text-[9px] font-medium uppercase tracking-[0.2em] text-[#8bd132]">Agenda editorial</span>
              <h2 className="mt-1.5 text-[20px] font-medium text-white">Próximas publicações</h2>
            </div>
            <div className="flex items-center gap-2">
              <button className="h-8 rounded-md border border-white/[0.07] px-3 text-[10px] text-[#8a959b]">Semana <ChevronDown className="ml-2 inline h-3 w-3" /></button>
              <button type="button" onClick={onNewPost} className="h-8 rounded-md border border-white/[0.07] px-3 text-[10px] text-white hover:bg-white/[0.04]"><Plus className="mr-1.5 inline h-3 w-3 text-[#8bd132]" />Adicionar</button>
            </div>
          </div>

          <div className="custom-scrollbar overflow-x-auto">
            <div className="min-w-[760px]">
              <div className="grid grid-cols-[42px_repeat(7,minmax(0,1fr))] border-y border-white/[0.06]">
                <div />
                {days.map(([day, date], index) => <div key={day} className={`py-3 text-center ${index === 3 ? 'bg-[#8bd132]/[0.06]' : ''}`}><span className={`block text-[10px] font-semibold ${index === 3 ? 'text-[#8bd132]' : 'text-[#a7b0b5]'}`}>{day}</span><span className="mt-0.5 block text-[9px] text-[#59656c]">{date} MAI</span></div>)}
              </div>
              <div className="relative grid grid-cols-[42px_repeat(7,minmax(0,1fr))] grid-rows-3">
                {[8, 12, 16].map((time, row) => <div key={time} style={{ gridColumn: 1, gridRow: row + 1 }} className="border-b border-white/[0.045] pr-2 pt-3 text-right text-[8px] text-[#4f5b62]">{String(time).padStart(2, '0')}:00</div>)}
                {Array.from({ length: 21 }).map((_, index) => <div key={index} style={{ gridColumn: (index % 7) + 2, gridRow: Math.floor(index / 7) + 1 }} className={`h-[82px] border-b border-l border-white/[0.045] ${(index % 7) === 3 ? 'bg-[#8bd132]/[0.018]' : ''}`} />)}
                {schedule.map((item, index) => <button key={`${item.day}-${item.row}-${index}`} type="button" onClick={onNewPost} style={{ gridColumn: item.day + 1, gridRow: item.row }} className="clicko-interactive-surface group z-10 mx-1 my-2 flex min-w-0 items-center gap-2 rounded-md border border-white/[0.07] bg-[#11161a] px-2 py-1.5 text-left hover:border-[#8bd132]/35 hover:bg-[#151c20]">
                  <img src={item.image} alt="" className="h-8 w-8 shrink-0 rounded object-cover grayscale-[20%] transition group-hover:grayscale-0" />
                  <span className="min-w-0 flex-1"><strong className="block truncate text-[9px] font-medium text-white">{item.title}</strong><span className="block truncate text-[8px] text-[#68747b]">{item.subtitle}</span></span>
                  <Instagram className="h-3 w-3 shrink-0 text-[#a66b85]" />
                </button>)}
              </div>
            </div>
          </div>
        </section>

        <aside className="clicko-dashboard-side border-t border-white/[0.07] py-8 xl:border-l xl:border-t-0 xl:pl-8">
          <section>
            <div className="flex items-center justify-between">
              <div><span className="text-[9px] uppercase tracking-[0.18em] text-[#69757c]">Agora</span><h2 className="mt-1 text-[15px] font-medium text-white">{isPersonal ? 'Operação pessoal' : 'Fila de aprovação'}</h2></div>
              {!isPersonal && <button type="button" onClick={() => onNavigate('approvals')} className="text-[9px] font-medium text-[#8bd132]">Ver tudo</button>}
            </div>
            <div className="mt-5 divide-y divide-white/[0.055]">
              {(isPersonal ? approvalItems.slice(0, 2) : approvalItems).map((item) => <button key={item.title} type="button" onClick={() => onNavigate(isPersonal ? 'calendar' : 'approvals')} className="clicko-interactive-surface group flex w-full items-center gap-3 rounded-md border border-transparent px-2 py-3 text-left">
                <img src={item.image} alt="" className="h-9 w-9 rounded-md object-cover opacity-80 group-hover:opacity-100" />
                <span className="min-w-0 flex-1"><strong className="block truncate text-[10px] font-medium text-[#d6dcdf]">{item.title}</strong><span className="mt-0.5 block truncate text-[8px] text-[#5f6b72]">{isPersonal ? 'Publicação programada' : item.meta}</span></span>
                <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
              </button>)}
            </div>
          </section>

          <section className="mt-8 border-t border-white/[0.07] pt-7">
            <div className="flex items-center justify-between"><div><span className="text-[9px] uppercase tracking-[0.18em] text-[#69757c]">Últimos 7 dias</span><h2 className="mt-1 text-[15px] font-medium text-white">Desempenho</h2></div><button type="button" onClick={() => onNavigate('analytics')} className="grid h-8 w-8 place-items-center rounded-full border border-white/[0.07] text-[#8bd132]"><ArrowRight className="h-3.5 w-3.5" /></button></div>
            <div className="mt-5 space-y-3.5">
              {[
                ['Alcance', '128.7K', '+14,5%'], ['Impressões', '256.3K', '+11,2%'], ['Cliques', '3.265', '+8,7%'],
              ].map(([label, value, gain]) => <div key={label} className="grid grid-cols-[1fr_auto_auto] items-center gap-3 text-[10px]"><span className="text-[#69757c]">{label}</span><strong className="font-medium text-white">{value}</strong><span className="text-[#8bd132]">{gain}</span></div>)}
            </div>
            <div className="clicko-chart group relative mt-6 h-20" role="img" tabIndex={0} aria-label="Evolução de desempenho nos últimos sete dias">
              <svg viewBox="0 0 300 80" className="h-full w-full overflow-visible" preserveAspectRatio="none" aria-hidden="true">
                <path className="clicko-chart-area" d="M2 62 C35 32 51 66 82 48 C110 30 127 29 151 48 C175 67 202 56 225 44 C247 34 264 41 298 18 L298 80 L2 80Z" fill="rgba(139,209,50,.06)" />
                <path className="clicko-chart-line" d="M2 62 C35 32 51 66 82 48 C110 30 127 29 151 48 C175 67 202 56 225 44 C247 34 264 41 298 18" fill="none" stroke="#8bd132" strokeWidth="1.5" />
                <circle className="clicko-chart-point" cx="298" cy="18" r="3" fill="#8bd132" />
              </svg>
              <div className="clicko-chart-tooltip pointer-events-none absolute right-0 top-0 rounded-md border border-white/10 bg-[#111517]/95 px-2.5 py-1.5 text-[8px] text-[#aeb7bb] opacity-0 shadow-lg shadow-black/20 backdrop-blur-sm">
                <strong className="block text-[9px] font-medium text-white">Pico semanal</strong>
                +14,5% de alcance
              </div>
            </div>
          </section>
        </aside>
      </div>

      <section className="clicko-dashboard-insight grid border-y border-white/[0.07] lg:grid-cols-[1.2fr_1fr]">
        <div className="py-7 lg:pr-8">
          <div className="flex items-center gap-2 text-[9px] font-medium uppercase tracking-[0.18em] text-[#8bd132]"><Sparkles className="h-3.5 w-3.5" />Leitura da IA</div>
          <p className="mt-3 max-w-2xl text-[15px] leading-6 text-[#bbc3c7]">Reels com depoimentos superaram a média em <strong className="font-medium text-white">27% de alcance</strong>. Transforme esse sinal em três novas variações.</p>
          <button type="button" onClick={onNewPost} className="mt-4 text-[10px] font-semibold text-[#8bd132]">Gerar variações <ArrowRight className="ml-1.5 inline h-3 w-3" /></button>
        </div>
        <div className="border-t border-white/[0.07] py-7 lg:border-l lg:border-t-0 lg:pl-8">
          <div className="flex items-center gap-2 text-[9px] font-medium uppercase tracking-[0.18em] text-[#69757c]"><BarChart3 className="h-3.5 w-3.5" />Ritmo da operação</div>
          <div className="mt-4 grid grid-cols-3 gap-5"><div><strong className="block text-[20px] font-medium text-white">86%</strong><span className="text-[8px] text-[#647078]">no prazo</span></div><div><strong className="block text-[20px] font-medium text-white">2,4h</strong><span className="text-[8px] text-[#647078]">tempo médio</span></div><div><strong className="block text-[20px] font-medium text-white">12</strong><span className="text-[8px] text-[#647078]">em produção</span></div></div>
        </div>
      </section>

      <section className="clicko-dashboard-flow py-8">
        <div className="mb-5 flex items-center justify-between"><div><span className="text-[9px] uppercase tracking-[0.18em] text-[#69757c]">Fluxo contínuo</span><h2 className="mt-1 text-[15px] font-medium text-white">Da ideia ao resultado</h2></div><span className="text-[9px] text-[#59656c]">7 etapas conectadas</span></div>
        <div className="custom-scrollbar flex overflow-x-auto border-y border-white/[0.055]">
          {flow.map((step, index) => <button key={step} type="button" onClick={onNewPost} className="clicko-interactive-surface group flex min-w-[150px] flex-1 items-center gap-3 border border-transparent border-r-white/[0.055] px-4 py-4 text-left last:border-r-transparent hover:bg-white/[0.02]"><span className="text-[9px] text-[#4f5b62]">0{index + 1}</span><span className="text-[10px] font-medium text-[#929ca1] group-hover:text-white">{step}</span>{index < flow.length - 1 && <ArrowRight className="ml-auto h-3 w-3 text-[#3f494f]" />}</button>)}
        </div>
      </section>
    </div>
  );
};
