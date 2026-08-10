import React from 'react';
import {
  ArrowRight, BrainCircuit, Check, ChevronRight, Compass, FileText,
  Layers3, PencilLine, Sparkles, Target, Users,
} from 'lucide-react';
import type { NavigationTab } from '../types';
import { useOperations } from '../context/OperationsContext';
import { strategyStatusLabel } from '../utils/localization';

export function WorkspaceView({ onNavigate }: { onNavigate: (tab: NavigationTab) => void }) {
  const {
    clients, activeClient, campaigns, posts, brainCompleteness,
    setActiveClientId, updateClient, prepareStudioHandoff,
  } = useOperations();
  const [editing, setEditing] = React.useState(false);
  const [objective, setObjective] = React.useState(activeClient?.currentObjective || '');
  const [offer, setOffer] = React.useState(activeClient?.featuredOffer || '');

  React.useEffect(() => {
    setObjective(activeClient?.currentObjective || '');
    setOffer(activeClient?.featuredOffer || '');
    setEditing(false);
  }, [activeClient?.id]);

  if (!activeClient) {
    return <div className="grid min-h-[60vh] place-items-center p-8"><div className="text-center"><Users className="mx-auto h-8 w-8 text-[#666]" /><h1 className="mt-4 text-lg font-semibold text-white">Nenhum cliente configurado</h1><p className="mt-2 text-sm text-[#858585]">Adicione um perfil para ativar o contexto inteligente.</p></div></div>;
  }

  const clientCampaigns = campaigns.filter((campaign) => campaign.clientId === activeClient.id || activeClient.activeCampaignIds.includes(campaign.id));
  const highlightedPosts = posts.filter((post) => activeClient.highlightedContentIds.includes(post.id)).slice(0, 3);

  const saveContext = () => {
    updateClient(activeClient.id, { currentObjective: objective, featuredOffer: offer });
    setEditing(false);
  };

  const openCreativeFlow = () => {
    prepareStudioHandoff({
      source: 'client', clientId: activeClient.id, campaignId: clientCampaigns[0]?.id,
      objective: activeClient.currentObjective, title: `Nova frente criativa — ${activeClient.name}`,
      angle: activeClient.positioning, hook: `Por que ${activeClient.featuredOffer} importa agora`,
      cta: 'Conhecer a oferta', format: 'carousel', funnelStage: 'Descoberta',
    });
    onNavigate('studio');
  };

  return <div className="clicko-client-intelligence mx-auto w-full max-w-[1480px] space-y-5 p-6 2xl:p-10">
    <header className="flex flex-wrap items-end justify-between gap-5">
      <div><div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.24em] text-[#ff7a00]"><BrainCircuit className="h-4 w-4" />Clicko Brain · inteligência do cliente</div><h1 className="mt-2 text-2xl font-semibold text-white">Clientes</h1><p className="mt-1 max-w-2xl text-sm text-[#8f999f]">Contexto persistente para que estratégia, criação e análise partam sempre do mesmo entendimento.</p></div>
      <div className="flex gap-2"><button onClick={() => onNavigate('brain')} className="rounded-lg border border-white/[0.08] px-4 py-2.5 text-[10px] font-semibold text-[#b7b7b7]">Memória completa</button><button onClick={() => onNavigate('strategy')} className="flex items-center gap-2 rounded-lg bg-[#ff5c5c] px-4 py-2.5 text-[10px] font-bold text-white"><Target className="h-4 w-4" />Construir campanha</button></div>
    </header>

    <div className="grid gap-4 xl:grid-cols-[260px_minmax(0,1fr)]">
      <aside className="rounded-xl border border-white/[0.07] bg-[#111] p-3">
        <div className="flex items-center justify-between px-2 py-2"><span className="text-[9px] font-semibold uppercase tracking-[0.16em] text-[#777]">Perfis ativos</span><span className="text-[9px] text-[#ff7a00]">{clients.length}</span></div>
        <div className="mt-1 space-y-1.5">{clients.map((client) => <button key={client.id} onClick={() => setActiveClientId(client.id)} className={`clicko-interactive-surface flex w-full items-center gap-3 rounded-lg border p-3 text-left ${client.id === activeClient.id ? 'border-[#ff5c5c]/35 bg-[#ff5c5c]/[0.07]' : 'border-transparent bg-white/[0.018]'}`}><span className={`grid h-8 w-8 shrink-0 place-items-center rounded-lg text-[10px] font-bold ${client.id === activeClient.id ? 'bg-[#ff5c5c] text-white' : 'bg-white/[0.05] text-[#aaa]'}`}>{client.name.slice(0, 2).toUpperCase()}</span><span className="min-w-0 flex-1"><strong className="block truncate text-[10px] font-medium text-white">{client.name}</strong><span className="block truncate text-[8px] text-[#777]">{client.segment}</span></span><ChevronRight className="h-3.5 w-3.5 text-[#555]" /></button>)}</div>
        <div className="mt-4 border-t border-white/[0.06] px-2 pt-4"><div className="flex items-center justify-between text-[9px]"><span className="text-[#777]">Memória estruturada</span><strong className="text-[#ff7a00]">{brainCompleteness}%</strong></div><div className="mt-2 h-1 overflow-hidden rounded-full bg-white/[0.05]"><div className="h-full bg-[#ff7a00]" style={{ width: `${brainCompleteness}%` }} /></div></div>
      </aside>

      <main className="min-w-0 space-y-4">
        <section className="rounded-xl border border-white/[0.07] bg-[#111] p-5 md:p-6">
          <div className="flex flex-wrap items-start justify-between gap-4"><div><span className="text-[9px] uppercase tracking-[0.18em] text-[#ff7a00]">Perfil de inteligência</span><h2 className="mt-1.5 text-xl font-semibold text-white">{activeClient.name}</h2><p className="mt-1 text-[10px] text-[#858585]">Atualizado {new Date(activeClient.updatedAt).toLocaleDateString('pt-BR')} · contexto sincronizado</p></div><button onClick={() => editing ? saveContext() : setEditing(true)} className="flex items-center gap-2 rounded-lg border border-white/[0.08] px-3 py-2 text-[9px] font-semibold text-[#bbb]">{editing ? <Check className="h-3.5 w-3.5 text-[#ff7a00]" /> : <PencilLine className="h-3.5 w-3.5" />}{editing ? 'Salvar contexto' : 'Atualizar contexto'}</button></div>
          <div className="mt-5 grid gap-px overflow-hidden rounded-xl border border-white/[0.06] bg-white/[0.06] md:grid-cols-2">
            <div className="bg-[#0d0d0d] p-4"><span className="text-[8px] uppercase tracking-[0.14em] text-[#666]">Objetivo atual</span>{editing ? <textarea value={objective} onChange={(event) => setObjective(event.target.value)} rows={3} className="mt-2 w-full resize-none rounded-lg border border-[#ff5c5c]/25 bg-black p-3 text-[10px] text-white outline-none" /> : <p className="mt-2 text-[11px] leading-relaxed text-[#ddd]">{activeClient.currentObjective}</p>}</div>
            <div className="bg-[#0d0d0d] p-4"><span className="text-[8px] uppercase tracking-[0.14em] text-[#666]">Oferta em destaque</span>{editing ? <textarea value={offer} onChange={(event) => setOffer(event.target.value)} rows={3} className="mt-2 w-full resize-none rounded-lg border border-[#ff5c5c]/25 bg-black p-3 text-[10px] text-white outline-none" /> : <p className="mt-2 text-[11px] leading-relaxed text-[#ddd]">{activeClient.featuredOffer}</p>}</div>
            <div className="bg-[#0d0d0d] p-4"><span className="text-[8px] uppercase tracking-[0.14em] text-[#666]">Público</span><p className="mt-2 text-[10px] leading-relaxed text-[#aaa]">{activeClient.audience}</p></div>
            <div className="bg-[#0d0d0d] p-4"><span className="text-[8px] uppercase tracking-[0.14em] text-[#666]">Posicionamento</span><p className="mt-2 text-[10px] leading-relaxed text-[#aaa]">{activeClient.positioning}</p></div>
          </div>
        </section>

        <section className="grid gap-4 lg:grid-cols-[1.15fr_.85fr]">
          <div className="rounded-xl border border-white/[0.07] bg-[#111] p-5"><div className="flex items-center justify-between"><div><span className="text-[8px] uppercase tracking-[0.16em] text-[#666]">Próximas ações</span><h3 className="mt-1 text-sm font-semibold text-white">Direcionamento recomendado</h3></div><Compass className="h-5 w-5 text-[#ff7a00]" /></div><div className="mt-4 space-y-2">{activeClient.recommendedActions.map((action, index) => <button key={action} onClick={index === 0 ? () => onNavigate('strategy') : openCreativeFlow} className="clicko-interactive-surface group flex w-full items-center gap-3 rounded-lg border border-white/[0.055] bg-black/20 p-3 text-left"><span className="grid h-6 w-6 place-items-center rounded-full bg-[#ff7a00]/10 text-[8px] font-bold text-[#ff7a00]">0{index + 1}</span><span className="flex-1 text-[10px] text-[#c9c9c9]">{action}</span><ArrowRight className="h-3.5 w-3.5 text-[#555] group-hover:text-[#ff5c5c]" /></button>)}</div><button onClick={openCreativeFlow} className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg bg-[#ff5c5c] py-2.5 text-[10px] font-bold text-white"><Sparkles className="h-4 w-4" />Iniciar explosão criativa</button></div>
          <div className="rounded-xl border border-white/[0.07] bg-[#111] p-5"><span className="text-[8px] uppercase tracking-[0.16em] text-[#666]">Campanhas ativas</span><div className="mt-3 space-y-2">{clientCampaigns.length ? clientCampaigns.slice(0, 3).map((campaign) => <button key={campaign.id} onClick={() => onNavigate('strategy')} className="clicko-interactive-surface w-full rounded-lg border border-white/[0.05] bg-black/20 p-3 text-left"><div className="flex justify-between gap-3"><strong className="text-[10px] font-medium text-white">{campaign.name}</strong><span className="text-[7px] uppercase text-[#ff7a00]">{strategyStatusLabel[campaign.status]}</span></div><p className="mt-2 line-clamp-2 text-[8px] leading-relaxed text-[#777]">{campaign.objective}</p></button>) : <div className="rounded-lg border border-dashed border-white/[0.08] p-5 text-center"><Target className="mx-auto h-5 w-5 text-[#555]" /><p className="mt-2 text-[9px] text-[#777]">Nenhuma campanha ativa para este cliente.</p></div>}</div><div className="mt-4 border-t border-white/[0.06] pt-4"><div className="flex items-center justify-between"><span className="text-[9px] text-[#777]">Conteúdos em destaque</span><span className="text-[9px] text-white">{highlightedPosts.length}</span></div>{!highlightedPosts.length && <p className="mt-2 text-[8px] leading-relaxed text-[#5f5f5f]">Eles aparecem aqui quando conteúdos são marcados como referência. Nenhum resultado real é presumido.</p>}</div></div>
        </section>

        <section className="overflow-x-auto rounded-xl border border-white/[0.07] bg-[#0c0c0c] p-4"><div className="flex min-w-[720px] items-center justify-between gap-2">{[['Cliente', Users], ['Objetivo', Target], ['Campanha', Compass], ['Matriz', Layers3], ['Produção', FileText], ['Aprendizado', BrainCircuit]].map(([label, Icon], index) => <React.Fragment key={String(label)}><div className="flex items-center gap-2 text-[9px] text-[#999]"><span className="grid h-7 w-7 place-items-center rounded-lg border border-white/[0.07] bg-white/[0.025]"><Icon className={`h-3.5 w-3.5 ${index === 0 ? 'text-[#ff5c5c]' : 'text-[#777]'}`} /></span>{String(label)}</div>{index < 5 && <ArrowRight className="h-3 w-3 text-[#3f3f3f]" />}</React.Fragment>)}</div></section>
      </main>
    </div>
  </div>;
}
