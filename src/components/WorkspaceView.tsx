import React from 'react';
import { ArrowRight, BrainCircuit, CalendarDays, Clapperboard, FolderKanban, Target, Users } from 'lucide-react';
import type { NavigationTab } from '../types';
import { useGovernance } from '../context/GovernanceContext';
import { useOperations } from '../context/OperationsContext';
import { strategyStatusLabel } from '../utils/localization';

export function WorkspaceView({ onNavigate }: { onNavigate: (tab: NavigationTab) => void }) {
  const { activeWorkspace, campaigns, posts, assets, brainCompleteness } = useOperations();
  const { users } = useGovernance();
  const active = campaigns.filter((campaign) => campaign.status === 'active').length;
  const scheduled = posts.filter((post) => post.status === 'scheduled').length;

  const modules = [
    { id: 'brain' as const, title: 'Memória da marca', detail: `${brainCompleteness}% estruturada`, icon: BrainCircuit },
    { id: 'strategy' as const, title: 'Estratégias', detail: `${active} campanha ativa`, icon: Target },
    { id: 'studio' as const, title: 'Estúdio', detail: `${posts.length} conteúdos no fluxo`, icon: Clapperboard },
    { id: 'library' as const, title: 'Biblioteca', detail: `${assets.length + posts.length} ativos indexados`, icon: FolderKanban },
  ];

  return <div className="mx-auto w-full max-w-[1480px] space-y-5 p-6 2xl:p-10">
    <section className="flex flex-wrap items-end justify-between gap-4">
      <div><p className="text-[10px] uppercase tracking-[0.25em] text-[#8bd132]">Centro operacional</p><h1 className="mt-2 text-2xl font-semibold text-white">{activeWorkspace.name}</h1><p className="mt-1 text-sm text-[#899399]">Clientes, projetos, pessoas e produção conectados em um único contexto.</p></div>
      <button onClick={() => onNavigate('strategy')} className="rounded-lg bg-[#8bd132] px-4 py-2.5 text-[11px] font-bold text-[#14200e]">Nova estratégia</button>
    </section>

    <section className="grid gap-3 md:grid-cols-4">
      {[['Campanhas ativas', active, Target], ['Conteúdos agendados', scheduled, CalendarDays], ['Pessoas no ambiente', users.length, Users], ['Ativos de memória', assets.length + posts.length, FolderKanban]].map(([label, value, Icon]) => <div key={String(label)} className="rounded-xl border border-white/[0.07] bg-[#182126] p-4"><div className="flex items-center justify-between"><span className="text-[10px] text-[#9da6ab]">{String(label)}</span><Icon className="h-4 w-4 text-[#8bd132]" /></div><strong className="mt-4 block text-2xl font-medium text-white">{String(value)}</strong></div>)}
    </section>

    <section className="grid gap-4 lg:grid-cols-[1.25fr_.75fr]">
      <div className="rounded-xl border border-white/[0.07] bg-[#182126] p-5">
        <div className="flex items-center justify-between"><div><h2 className="text-sm font-semibold text-white">Arquitetura do ambiente de trabalho</h2><p className="mt-1 text-[10px] text-[#8d979d]">Cada etapa alimenta a próxima sem duplicar contexto.</p></div><span className="rounded-full bg-[#8bd132]/10 px-2.5 py-1 text-[9px] text-[#8bd132]">Sincronizado</span></div>
        <div className="mt-5 grid gap-3 sm:grid-cols-2">
          {modules.map(({ id, title, detail, icon: Icon }) => <button key={id} onClick={() => onNavigate(id)} className="group flex items-center gap-3 rounded-xl border border-white/[0.055] bg-black/20 p-4 text-left hover:border-[#8bd132]/30"><span className="grid h-10 w-10 place-items-center rounded-lg bg-[#8bd132]/10"><Icon className="h-5 w-5 text-[#8bd132]" /></span><span className="min-w-0 flex-1"><span className="block text-[12px] font-medium text-white">{title}</span><span className="block text-[10px] text-[#899399]">{detail}</span></span><ArrowRight className="h-4 w-4 text-[#58646a] group-hover:text-[#8bd132]" /></button>)}
        </div>
      </div>
      <div className="rounded-xl border border-white/[0.07] bg-[#182126] p-5"><h2 className="text-sm font-semibold text-white">Campanhas recentes</h2><div className="mt-4 space-y-3">{campaigns.slice(0, 4).map((campaign) => <button key={campaign.id} onClick={() => onNavigate('strategy')} className="w-full rounded-lg border border-white/[0.05] bg-black/20 p-3 text-left"><div className="flex justify-between gap-3"><span className="text-[11px] font-medium text-white">{campaign.name}</span><span className="text-[8px] uppercase text-[#8bd132]">{strategyStatusLabel[campaign.status]}</span></div><p className="mt-1 line-clamp-2 text-[9px] text-[#899399]">{campaign.objective}</p></button>)}</div></div>
    </section>
  </div>;
}
