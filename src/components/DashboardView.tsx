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
} from 'lucide-react';
import { NavigationTab, Post, AIActionSuggestion, Workspace } from '../types';
import { useOperations } from '../context/OperationsContext';

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
  { day: 1, row: 3, title: 'Stories', subtitle: 'Dicas', time: '16:00', accent: '#3d91a6', image: 'https://images.unsplash.com/photo-1551836022-d5d88e9218df?auto=format&fit=crop&w=120&q=80' },
  { day: 1, row: 5, title: 'Reels', subtitle: 'Depoimento', time: '20:00', accent: '#8a5bc1', image: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=120&q=80' },
  { day: 2, row: 1, title: 'Post feed', subtitle: 'Promoção', time: '10:00', accent: '#a9515a', image: 'https://images.unsplash.com/photo-1549068106-b024baf5062d?auto=format&fit=crop&w=120&q=80' },
  { day: 2, row: 2, title: 'Reels', subtitle: 'Procedimentos', time: '14:00', accent: '#a9515a', image: 'https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&w=120&q=80' },
  { day: 2, row: 5, title: 'Stories', subtitle: 'Bastidores', time: '20:00', accent: '#5b87b6', image: 'https://images.unsplash.com/photo-1580489944761-15a19d654956?auto=format&fit=crop&w=120&q=80' },
  { day: 3, row: 1, title: 'Reels', subtitle: 'Resultados', time: '10:00', accent: '#754fb2', image: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=120&q=80' },
  { day: 3, row: 3, title: 'Post feed', subtitle: 'Educação', time: '16:00', accent: '#897048', image: 'https://images.unsplash.com/photo-1529626455594-4ff0802cfb7e?auto=format&fit=crop&w=120&q=80' },
  { day: 4, row: 1, title: 'Carrossel', subtitle: 'Mitos e Verdades', time: '10:00', accent: '#a48e39', image: 'https://images.unsplash.com/photo-1517841905240-472988babdf9?auto=format&fit=crop&w=120&q=80' },
  { day: 4, row: 2, title: 'Carrossel', subtitle: 'Dicas rápidas', time: '14:00', accent: '#a48e39', image: 'https://images.unsplash.com/photo-1531123897727-8f129e1688ce?auto=format&fit=crop&w=120&q=80' },
  { day: 4, row: 5, title: 'Stories', subtitle: 'Perguntas', time: '20:00', accent: '#69ad31', image: 'https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?auto=format&fit=crop&w=120&q=80' },
  { day: 5, row: 1, title: 'Post feed', subtitle: 'Benefícios', time: '10:00', accent: '#8054b0', image: 'https://images.unsplash.com/photo-1524504388940-b1c1722653e1?auto=format&fit=crop&w=120&q=80' },
  { day: 5, row: 3, title: 'Reels', subtitle: 'Antes e Depois', time: '16:00', accent: '#9b5555', image: 'https://images.unsplash.com/photo-1544725176-7c40e5a71c5e?auto=format&fit=crop&w=120&q=80' },
  { day: 6, row: 1, title: 'Carrossel', subtitle: 'Cuidados', time: '10:00', accent: '#4e9aad', image: 'https://images.unsplash.com/photo-1538108149393-fbbd81895907?auto=format&fit=crop&w=120&q=80' },
  { day: 6, row: 2, title: 'Stories', subtitle: 'Depoimento', time: '14:00', accent: '#9b5555', image: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=120&q=80' },
  { day: 6, row: 5, title: 'Reels', subtitle: 'FAQ', time: '20:00', accent: '#9b5555', image: 'https://images.unsplash.com/photo-1551836022-d5d88e9218df?auto=format&fit=crop&w=120&q=80' },
  { day: 7, row: 1, title: 'Post feed', subtitle: 'Lifestyle', time: '10:00', accent: '#8150a5', image: 'https://images.unsplash.com/photo-1531123897727-8f129e1688ce?auto=format&fit=crop&w=120&q=80' },
  { day: 7, row: 3, title: 'Stories', subtitle: 'Dica do dia', time: '16:00', accent: '#9b742d', image: 'https://images.unsplash.com/photo-1517841905240-472988babdf9?auto=format&fit=crop&w=120&q=80' },
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
  { label: 'Conteúdos gerados', value: '128', change: '+24%', detail: 'vs semana anterior', icon: FileText, tone: 'green' },
  { label: 'Publicações agendadas', value: '32', change: '+18%', detail: 'vs semana anterior', icon: CalendarDays, tone: 'green' },
  { label: 'Aprovações pendentes', value: '5', change: '', detail: '3 precisam de revisão', icon: Clock3, tone: 'amber' },
  { label: 'Engajamento (médio)', value: '4,82%', change: '+11%', detail: 'vs semana anterior', icon: ChartNoAxesCombined, tone: 'purple' },
];

const quickFlow = [
  { label: '1. Briefing', text: 'Defina o objetivo\nda semana', icon: ClipboardList },
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
  { title: 'Post feed - Promoção', time: '08:50', image: 'https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&w=100&q=80' },
];

const MiniSparkline = ({ tone }: { tone: string }) => (
  <svg viewBox="0 0 70 24" className="h-6 w-[70px]" aria-hidden="true">
    <path d="M1 20 C12 20 13 12 22 13 C31 15 35 22 45 13 C53 7 58 14 69 3" fill="none" stroke={tone === 'purple' ? '#9556d8' : '#8bd132'} strokeWidth="1.6" />
  </svg>
);

export const DashboardView: React.FC<DashboardViewProps> = ({ onNewPost, onNavigate }) => {
  const { activeCampaign, brainCompleteness, assets, posts } = useOperations();
  return (
    <div className="vexel-dashboard px-6 pb-5 pt-1 2xl:px-10">
      <div className="grid grid-cols-1 gap-4 min-[1100px]:grid-cols-[minmax(0,1fr)_300px] 2xl:grid-cols-[minmax(0,1fr)_390px]">
        <section className="min-w-0 space-y-4">
          <div className="pt-1">
            <h1 className="text-[21px] font-semibold tracking-[-0.03em] text-white">Olá, Pedro! <span className="text-[17px]">👋</span></h1>
            <div className="mt-1 flex flex-wrap items-center gap-2 text-[10px] text-[#a2aaaf]"><span>Aqui está o resumo da sua operação hoje.</span><span className="rounded-full bg-[#8bd132]/10 px-2 py-1 text-[8px] text-[#8bd132]">Brain {brainCompleteness}%</span>{activeCampaign && <button onClick={() => onNavigate('strategy')} className="rounded-full bg-white/[0.045] px-2 py-1 text-[8px] text-[#b9c0c3]">{activeCampaign.name}</button>}<button onClick={() => onNavigate('library')} className="rounded-full bg-white/[0.045] px-2 py-1 text-[8px] text-[#b9c0c3]">{assets.length + posts.length} ativos</button></div>
          </div>

          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            {metricCards.map((metric) => {
              const Icon = metric.icon;
              const iconClass = metric.tone === 'amber' ? 'bg-[#5b4115] text-[#f2b63b]' : metric.tone === 'purple' ? 'bg-[#36234c] text-[#a969db]' : 'bg-[#273f22] text-[#8bd132]';
              return (
                <article key={metric.label} className="vexel-card flex h-[116px] flex-col justify-between p-[18px]">
                  <div className="flex items-start justify-between">
                    <span className="text-[11px] text-[#c5cace]">{metric.label}</span>
                    <span className={`grid h-9 w-9 place-items-center rounded-full ${iconClass}`}><Icon className="h-[18px] w-[18px]" strokeWidth={1.7} /></span>
                  </div>
                  <div className="flex items-end justify-between">
                    <div>
                      <div className="text-[26px] font-light leading-none tracking-[-0.03em] text-[#f4f5f5]">{metric.value}</div>
                      <div className="mt-2 whitespace-nowrap text-[9px] text-[#899297]">
                        {metric.change && <span className="mr-1 text-[#8bd132]">{metric.change}</span>}{metric.detail}
                      </div>
                    </div>
                    {(metric.tone === 'green' || metric.tone === 'purple') && <MiniSparkline tone={metric.tone} />}
                  </div>
                </article>
              );
            })}
          </div>

          <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {[
              { label: 'Contas conectadas', value: '8 canais', detail: '7 sincronizados agora', icon: Link2, tab: 'connected-accounts' as const },
              { label: 'Automações', value: '5 ativas', detail: '52 execuções este mês', icon: Workflow, tab: 'automations' as const },
              { label: 'Consumo de IA', value: '68%', detail: '34.120 de 50.000 créditos', icon: Cpu, tab: 'subscription' as const },
              { label: 'Atividade recente', value: '24 ações', detail: 'Última há 3 minutos', icon: Activity, tab: 'audit-logs' as const },
            ].map(({ label, value, detail, icon: Icon, tab }) => <button key={label} onClick={() => onNavigate(tab)} className="vexel-card flex items-center gap-3 p-3.5 text-left transition hover:border-[#8bd132]/25"><span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-[#8bd132]/[0.07]"><Icon className="h-4 w-4 text-[#8bd132]" /></span><span className="min-w-0"><span className="block text-[8px] text-[#7e898f]">{label}</span><strong className="mt-0.5 block text-[11px] font-medium text-white">{value}</strong><span className="block truncate text-[7px] text-[#69757b]">{detail}</span></span></button>)}
          </section>

          <section className="vexel-card overflow-hidden p-[18px]">
            <div className="mb-3 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <h2 className="text-[15px] font-semibold text-white">Calendário de publicações</h2>
                <CircleHelp className="h-4 w-4 text-[#8c959a]" />
              </div>
              <div className="flex items-center gap-3">
                <button className="flex h-9 items-center gap-2 rounded-lg bg-[#242c31] px-3 text-[10px] text-[#aab1b5]">Visualização: <span className="font-medium text-white">Semana</span><ChevronDown className="h-3.5 w-3.5" /></button>
                <button onClick={onNewPost} className="flex h-9 items-center gap-2 rounded-lg bg-[#8bd132] px-4 text-[10px] font-bold text-[#15200f] hover:bg-[#9be24d]"><Plus className="h-4 w-4" />Novo conteúdo</button>
              </div>
            </div>

            <div className="grid grid-cols-[42px_repeat(7,minmax(62px,1fr))] border-b border-white/[0.055] 2xl:grid-cols-[48px_repeat(7,minmax(90px,1fr))]">
              <div className="flex items-center justify-center"><button className="grid h-8 w-8 place-items-center rounded-lg bg-[#252d32] text-[#c6cbce]"><ChevronLeft className="h-4 w-4" /></button></div>
              {days.map(([name, date], index) => (
                <div key={date} className={`relative flex h-[48px] flex-col items-center justify-center border-l border-white/[0.04] text-[10px] ${index === 3 ? 'rounded-t-lg border-x border-t border-[#8bd132] bg-[#111b18]' : ''}`}>
                  <span className={index === 3 ? 'font-semibold text-[#8bd132]' : 'text-[#d5d9db]'}>{name}</span>
                  <span className={`mt-0.5 text-[9px] ${index === 3 ? 'text-[#8bd132]' : 'text-[#a5adb1]'}`}>{date}</span>
                  {index === 6 && <ChevronRight className="absolute right-3 top-[17px] h-4 w-4 text-[#9da5aa]" />}
                </div>
              ))}
            </div>

            <div className="relative grid grid-cols-[42px_repeat(7,minmax(62px,1fr))] grid-rows-5 2xl:grid-cols-[48px_repeat(7,minmax(90px,1fr))]">
              {[8, 10, 12, 14, 16].map((time, index) => (
                <div key={time} style={{ gridColumn: 1, gridRow: index + 1 }} className="pr-3 pt-1.5 text-right text-[9px] text-[#a5adb1]">{String(time).padStart(2, '0')}:00</div>
              ))}
              {Array.from({ length: 35 }).map((_, index) => {
                const day = (index % 7) + 1;
                const row = Math.floor(index / 7) + 1;
                return <div key={index} style={{ gridColumn: day + 1, gridRow: row }} className={`h-[54px] border-b border-l border-white/[0.045] ${day === 4 ? 'bg-[#101a17]' : 'bg-[#131a1e]/60'} ${day === 4 && row === 5 ? 'border-b-[#8bd132]' : ''}`} />;
              })}
              <div className="pointer-events-none z-10 rounded-[10px] border border-[#8bd132]" style={{ gridColumn: 5, gridRow: '1 / 6' }} />
              {calendarItems.map((item, index) => (
                <button
                  key={`${item.day}-${item.row}-${index}`}
                  type="button"
                  style={{ gridColumn: item.day + 1, gridRow: item.row, borderColor: item.accent }}
                  className="z-20 m-[3px] flex min-w-0 items-center gap-1.5 rounded-[7px] border bg-[#222a2f] px-1.5 text-left shadow-sm transition hover:-translate-y-px hover:bg-[#293237]"
                >
                  <img src={item.image} alt="" className="h-9 w-7 shrink-0 rounded-[5px] object-cover" />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-[8px] font-semibold text-white">{item.title}</span>
                    <span className="block truncate text-[8px] text-[#e2e5e6]">{item.subtitle}</span>
                    <span className="block text-[8px] text-[#abb2b6]">{item.time}</span>
                  </span>
                  <Instagram className="h-3 w-3 shrink-0 text-[#e780a8]" />
                </button>
              ))}
            </div>

            <div className="mt-3 flex items-center gap-8 pl-2 text-[9px] text-[#aab1b5]">
              {[['#8bd132', 'Agendado'], ['#f2b33d', 'Pendente'], ['#6ba7e8', 'Aprovado'], ['#e35d63', 'Reprovado']].map(([color, label]) => (
                <span key={label} className="flex items-center gap-2"><i className="h-2 w-2 rounded-full" style={{ backgroundColor: color }} />{label}</span>
              ))}
            </div>
          </section>

          <section className="vexel-card p-[18px]">
            <h2 className="text-[14px] font-semibold text-white">Fluxo rápido</h2>
            <div className="mt-4 flex items-start justify-between gap-2">
              {quickFlow.map((step, index) => {
                const Icon = step.icon;
                return (
                  <React.Fragment key={step.label}>
                    <button className="group flex min-w-0 flex-1 flex-col items-center text-center">
                      <span className="grid h-[54px] w-[54px] place-items-center rounded-[12px] border border-[#3d5637] bg-[#19231e] text-[#8bd132] transition group-hover:bg-[#22301f]"><Icon className="h-7 w-7" strokeWidth={1.7} /></span>
                      <span className="mt-2 text-[10px] font-semibold text-white">{step.label}</span>
                      <span className="mt-0.5 whitespace-pre-line text-[9px] leading-[1.35] text-[#b2b9bd]">{step.text}</span>
                    </button>
                    {index < quickFlow.length - 1 && <ArrowRight className="mt-5 h-4 w-4 shrink-0 text-[#8bd132]" />}
                  </React.Fragment>
                );
              })}
            </div>
          </section>
        </section>

        <aside className="space-y-4 pt-[2px]">
          <section className="vexel-card p-[18px]">
            <div className="flex items-center justify-between">
              <h2 className="text-[13px] font-semibold text-white">Aprovações pendentes</h2>
              <button onClick={() => onNavigate('approvals')} className="text-[10px] font-medium text-[#8bd132]">Ver todas</button>
            </div>
            <div className="mt-4 space-y-3.5">
              {approvals.map((item) => (
                <button key={item.title} onClick={() => onNavigate('approvals')} className="flex w-full items-center gap-3 text-left">
                  <img src={item.image} alt="" className="h-[53px] w-[53px] rounded-[8px] object-cover" />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-[10px] font-medium text-white">{item.title}</span>
                    <span className="mt-1 block text-[9px] text-[#a4adb1]">Clínica Vitalis</span>
                    <span className="mt-0.5 block text-[8px] text-[#7f898e]">Solicitado em 21/05 às {item.time}</span>
                  </span>
                  <span className="rounded-full bg-[#514017] px-2.5 py-1.5 text-[8px] font-medium text-[#f4bd3d]">Pendente</span>
                </button>
              ))}
            </div>
          </section>

          <section className="vexel-card p-[18px]">
            <div className="flex items-center justify-between">
              <h2 className="text-[13px] font-semibold text-white">Desempenho <span className="font-normal text-[#8e979c]">(últimos 7 dias)</span></h2>
              <button onClick={() => onNavigate('analytics')} className="text-[10px] font-medium text-[#8bd132]">Ver relatório</button>
            </div>
            <div className="mt-4 space-y-3">
              {[
                ['Alcance', '128.7K', '+14,5%'],
                ['Impressões', '256.3K', '+11,2%'],
                ['Engajamento', '4,82%', '+11,0%'],
                ['Cliques no link', '3.265', '+8,7%'],
              ].map(([label, value, gain], index) => (
                <div key={label} className="grid grid-cols-[18px_1fr_auto_auto] items-center gap-2 text-[10px]">
                  {index === 0 ? <Sparkles className="h-3.5 w-3.5 text-[#d4d9db]" /> : index === 1 ? <Layers3 className="h-3.5 w-3.5 text-[#d4d9db]" /> : index === 2 ? <ChartNoAxesCombined className="h-3.5 w-3.5 text-[#d4d9db]" /> : <Send className="h-3.5 w-3.5 text-[#d4d9db]" />}
                  <span className="text-[#c0c6c9]">{label}</span><span className="text-white">{value}</span><span className="w-14 text-right text-[#8bd132]">{gain}</span>
                </div>
              ))}
            </div>
            <div className="relative mt-4 h-[120px] border-b border-l border-white/[0.05]">
              {[0, 1, 2, 3].map((line) => <i key={line} className="absolute left-0 right-0 border-t border-white/[0.045]" style={{ top: `${line * 33}%` }} />)}
              <svg viewBox="0 0 330 112" className="absolute inset-0 h-full w-full" preserveAspectRatio="none">
                <defs><linearGradient id="area" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#8bd132" stopOpacity=".28"/><stop offset="1" stopColor="#8bd132" stopOpacity="0"/></linearGradient></defs>
                <path d="M6 67 C34 48 44 55 69 67 C91 78 109 42 137 48 C169 55 181 86 215 72 C244 61 254 71 282 54 C304 41 318 38 326 35 L326 112 L6 112 Z" fill="url(#area)" />
                <path d="M6 67 C34 48 44 55 69 67 C91 78 109 42 137 48 C169 55 181 86 215 72 C244 61 254 71 282 54 C304 41 318 38 326 35" fill="none" stroke="#8bd132" strokeWidth="2" />
                {[['6','67'],['69','67'],['137','48'],['215','72'],['282','54'],['326','35']].map(([cx,cy]) => <circle key={cx} cx={cx} cy={cy} r="3" fill="#8bd132" />)}
              </svg>
              <div className="absolute -bottom-5 left-0 right-0 flex justify-between text-[8px] text-[#818b90]"><span>15/mai</span><span>16/mai</span><span>17/mai</span><span>18/mai</span><span>19/mai</span><span>20/mai</span><span>21/mai</span></div>
            </div>
            <div className="h-4" />
          </section>

          <section className="vexel-card relative min-h-[170px] overflow-hidden p-[18px]">
            <div className="flex items-center gap-2 text-[#8bd132]"><Sparkles className="h-4 w-4" /><h2 className="text-[13px] font-semibold text-white">Dica da IA</h2></div>
            <p className="mt-4 max-w-[245px] text-[10px] leading-relaxed text-[#d0d5d7]">Seus Reels com depoimentos tiveram 27% mais engajamento que a média. Que tal gerar mais conteúdos nesse formato?</p>
            <button className="mt-4 rounded-lg bg-[#2d4527] px-4 py-2 text-[9px] font-semibold text-[#9ae14d]">Gerar variações</button>
            <div className="absolute bottom-5 right-5 grid h-[94px] w-[94px] place-items-center rounded-full border-2 border-[#8bd132] text-[#8bd132]"><Sparkles className="h-11 w-11" fill="currentColor" strokeWidth={1.2} /></div>
          </section>
        </aside>
      </div>
    </div>
  );
};
