import React from 'react';
import {
  ArrowRight, BrainCircuit, Check, ChevronRight, CircleAlert, Layers3,
  LoaderCircle, Plus, Sparkles, Target, WandSparkles,
} from 'lucide-react';
import { useOperations } from '../context/OperationsContext';
import { strategyStatusLabel } from '../utils/localization';
import type { CampaignContentItem, CreativeIdea, PostFormat, StrategyCampaign } from '../types';

type CampaignDraft = Pick<StrategyCampaign, 'name' | 'objective' | 'audience' | 'offer' | 'funnel' | 'centralMessage' | 'angle' | 'contentPlan'>;

const formatMap: Record<string, PostFormat> = {
  carrossel: 'carousel', reel: 'reels', reels: 'reels', story: 'story', stories: 'story', post: 'post',
};

function fallbackPlan(need: string, audience: string, offer: string): CampaignDraft {
  const contentPlan: CampaignContentItem[] = [
    { id: `plan-${Date.now()}-1`, format: 'reels', funnelStage: 'descoberta', purpose: 'Interromper o padrão e tornar o problema reconhecível.', hook: 'O custo invisível de continuar fazendo do mesmo jeito', status: 'planned' },
    { id: `plan-${Date.now()}-2`, format: 'carousel', funnelStage: 'consideracao', purpose: 'Explicar a mudança com clareza e prova lógica.', hook: 'O método em cinco decisões práticas', status: 'planned' },
    { id: `plan-${Date.now()}-3`, format: 'story', funnelStage: 'consideracao', purpose: 'Responder objeções e abrir conversa.', hook: 'A dúvida que quase todo cliente tem antes de começar', status: 'planned' },
    { id: `plan-${Date.now()}-4`, format: 'post', funnelStage: 'conversao', purpose: 'Apresentar oferta e próximo passo.', hook: 'O que muda quando você começa agora', status: 'planned' },
  ];
  return {
    name: 'Campanha orientada por objetivo', objective: need,
    audience, offer, funnel: 'Descoberta → Consideração → Conversão',
    centralMessage: 'Transformar uma necessidade real em uma decisão clara e segura.',
    angle: 'Clareza operacional e redução de fricção', contentPlan,
  };
}

export function StrategyView({ onOpenStudio }: { onOpenStudio: () => void }) {
  const {
    brain, activeClient, campaigns, activeCampaign, creativeIdeas, selectedCreativeIdeaIds,
    setActiveCampaignId, createCampaign, setCreativeIdeas, toggleCreativeIdea, prepareStudioHandoff,
  } = useOperations();
  const [need, setNeed] = React.useState('Preciso transformar esta oferta em uma campanha prática para esta semana.');
  const [draft, setDraft] = React.useState<CampaignDraft | null>(null);
  const [planning, setPlanning] = React.useState(false);
  const [error, setError] = React.useState('');
  const [success, setSuccess] = React.useState('');
  const [exploding, setExploding] = React.useState(false);

  const interpretGoal = async () => {
    if (!need.trim() || !activeClient) return;
    setPlanning(true); setError(''); setSuccess('');
    const base = fallbackPlan(need, activeClient.audience, activeClient.featuredOffer);
    try {
      const response = await fetch('/api/ai/generate-campaign', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          campaignGoal: need, productOrTopic: activeClient.featuredOffer,
          platforms: ['Instagram', 'LinkedIn'], tone: activeClient.toneOfVoice,
          brandName: activeClient.name, brainContext: brain, clientContext: activeClient, screenContext: 'strategy',
        }),
      });
      if (!response.ok) throw new Error('Não foi possível consultar o planejador.');
      const data = await response.json();
      const mapped = Array.isArray(data.posts) ? data.posts.slice(0, 6).map((post: any, index: number): CampaignContentItem => ({
        id: `plan-${Date.now()}-${index}`, format: formatMap[String(post.format || '').toLowerCase()] || 'post',
        funnelStage: index === 0 ? 'descoberta' : index === data.posts.length - 1 ? 'conversao' : 'consideracao',
        purpose: post.title || 'Peça conectada ao objetivo', hook: post.copy?.split('\n')[0] || post.title || base.contentPlan?.[index % 4]?.hook || '', status: 'planned',
      })) : base.contentPlan;
      setDraft({ ...base, name: data.title || base.name, centralMessage: data.description || base.centralMessage, contentPlan: mapped });
    } catch {
      setDraft(base);
      setError('A integração de IA não respondeu. O Clicko estruturou um plano local editável com o contexto disponível.');
    } finally { setPlanning(false); }
  };

  const confirmCampaign = () => {
    if (!draft || !activeClient) return;
    const campaign = createCampaign({
      ...draft, clientId: activeClient.id, startDate: new Date().toISOString().slice(0, 10),
      endDate: new Date(Date.now() + 7 * 86400000).toISOString().slice(0, 10), budget: 'A definir',
      kpis: ['Atenção qualificada', 'Intenção', 'Conversas iniciadas'], products: activeClient.products,
      channels: ['instagram', 'linkedin'], importantDates: 'Distribuição concentrada nos próximos sete dias',
      ctas: ['Conhecer a oferta', 'Iniciar conversa'], executionPlan: ['Validar mensagem central', 'Selecionar combinações criativas', 'Produzir peças', 'Enviar para aprovação', 'Distribuir e registrar aprendizados'], status: 'planned',
    });
    setDraft(null); setSuccess(`Campanha “${campaign.name}” criada e conectada ao fluxo.`);
  };

  const generateExplosion = () => {
    if (!activeClient || !activeCampaign) return;
    setExploding(true);
    window.setTimeout(() => {
      const combinations: Array<[string, string, PostFormat, CreativeIdea['funnelStage'], string]> = [
        ['Contraste', 'O que você perde ao manter o processo atual', 'reels', 'descoberta', 'Reconhecer o problema'],
        ['Bastidores', 'Como a transformação acontece na prática', 'carousel', 'consideracao', 'Entender o método'],
        ['Objeção', 'A pergunta que precisa ser respondida antes da decisão', 'story', 'consideracao', 'Reduzir insegurança'],
        ['Prova lógica', 'Cinco sinais de que esta solução faz sentido', 'carousel', 'consideracao', 'Validar a escolha'],
        ['Oferta', 'O próximo passo mais simples para começar', 'post', 'conversao', 'Iniciar conversa'],
        ['Visão futura', 'Como a rotina pode funcionar depois da mudança', 'reels', 'conversao', 'Visualizar resultado'],
      ];
      setCreativeIdeas(combinations.map(([angle, hook, format, funnelStage, rationale], index) => ({
        id: `idea-${Date.now()}-${index}`, clientId: activeClient.id, campaignId: activeCampaign.id,
        title: `${angle} · ${activeCampaign.name}`, angle, hook, format, funnelStage,
        cta: activeCampaign.ctas[index % activeCampaign.ctas.length] || 'Conhecer a oferta', rationale,
      })));
      setExploding(false);
    }, 520);
  };

  const sendSelectedToStudio = () => {
    const first = creativeIdeas.find((idea) => selectedCreativeIdeaIds.includes(idea.id));
    if (!first || !activeCampaign) return;
    prepareStudioHandoff({
      source: 'matrix', clientId: first.clientId, campaignId: first.campaignId,
      objective: activeCampaign.objective, title: first.title, angle: first.angle,
      hook: first.hook, cta: first.cta, format: first.format, funnelStage: first.funnelStage,
    });
    onOpenStudio();
  };

  return <div className="clicko-strategy-builder mx-auto w-full max-w-[1480px] space-y-5 p-6 2xl:p-10">
    <header className="flex flex-wrap items-end justify-between gap-4"><div><div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.24em] text-[#ff7a00]"><Target className="h-4 w-4" />Campaign Builder</div><h1 className="mt-2 text-2xl font-semibold text-white">Objetivo em plano de ação.</h1><p className="mt-1 max-w-2xl text-sm text-[#8f999f]">A IA interpreta a necessidade e distribui cada peça pela função no funil.</p></div>{activeClient && <div className="rounded-full border border-white/[0.07] bg-white/[0.025] px-3 py-2 text-[9px] text-[#aaa]"><span className="text-[#666]">Cliente ativo · </span>{activeClient.name}</div>}</header>

    <section className="rounded-xl border border-white/[0.07] bg-[#111] p-5 md:p-6"><div className="grid gap-5 lg:grid-cols-[1fr_auto]"><label><span className="text-[9px] font-semibold uppercase tracking-[0.15em] text-[#777]">O que precisa acontecer?</span><textarea value={need} onChange={(event) => setNeed(event.target.value)} rows={3} placeholder="Ex.: Quero aumentar as matrículas desta turma nas próximas duas semanas." className="mt-2 w-full resize-none rounded-xl border border-white/[0.08] bg-black p-4 text-[12px] leading-relaxed text-white outline-none focus:border-[#ff5c5c]/45" /></label><button onClick={interpretGoal} disabled={planning || !need.trim() || !activeClient} className="self-end rounded-xl bg-[#ff5c5c] px-5 py-4 text-[10px] font-bold text-white disabled:opacity-40">{planning ? <span className="flex items-center gap-2"><LoaderCircle className="h-4 w-4 animate-spin" />Interpretando…</span> : <span className="flex items-center gap-2"><WandSparkles className="h-4 w-4" />Interpretar objetivo</span>}</button></div>{error && <div className="mt-3 flex items-start gap-2 rounded-lg border border-[#ff7a00]/20 bg-[#ff7a00]/[0.06] p-3 text-[9px] text-[#d9a46f]"><CircleAlert className="mt-0.5 h-3.5 w-3.5 shrink-0" />{error}</div>}{success && <div className="mt-3 flex items-center gap-2 rounded-lg border border-[#ff5c5c]/20 bg-[#ff5c5c]/[0.06] p-3 text-[9px] text-[#ff9b9b]"><Check className="h-3.5 w-3.5" />{success}</div>}</section>

    {draft && <section className="rounded-xl border border-[#ff5c5c]/20 bg-[#111] p-5 md:p-6"><div className="flex flex-wrap items-start justify-between gap-4"><div><span className="text-[8px] uppercase tracking-[0.16em] text-[#ff5c5c]">Plano proposto</span><h2 className="mt-1 text-lg font-semibold text-white">{draft.name}</h2><p className="mt-2 max-w-3xl text-[10px] leading-relaxed text-[#aaa]">{draft.centralMessage}</p></div><button onClick={confirmCampaign} className="flex items-center gap-2 rounded-lg bg-[#ff5c5c] px-4 py-2.5 text-[9px] font-bold text-white"><Check className="h-4 w-4" />Confirmar campanha</button></div><div className="mt-5 grid gap-3 md:grid-cols-3">{[['Público', draft.audience], ['Oferta', draft.offer], ['Ângulo', draft.angle]].map(([label, value]) => <div key={label} className="rounded-lg border border-white/[0.055] bg-black/20 p-3"><span className="text-[7px] uppercase text-[#666]">{label}</span><p className="mt-2 text-[9px] leading-relaxed text-[#ccc]">{value}</p></div>)}</div><div className="mt-5 overflow-x-auto"><div className="flex min-w-[720px] gap-2">{draft.contentPlan?.map((item, index) => <div key={item.id} className="min-w-0 flex-1 rounded-lg border border-white/[0.06] bg-black/25 p-3"><div className="flex items-center justify-between"><span className="text-[7px] uppercase text-[#ff7a00]">{item.funnelStage}</span><span className="text-[7px] text-[#555]">0{index + 1}</span></div><strong className="mt-2 block text-[9px] capitalize text-white">{item.format}</strong><p className="mt-2 line-clamp-2 text-[8px] leading-relaxed text-[#777]">{item.hook}</p></div>)}</div></div></section>}

    <div className="grid gap-4 xl:grid-cols-[270px_minmax(0,1fr)]">
      <aside className="rounded-xl border border-white/[0.07] bg-[#111] p-3"><div className="flex items-center justify-between px-2 py-2"><span className="text-[9px] font-semibold uppercase tracking-[0.16em] text-[#777]">Campanhas</span><span className="text-[9px] text-[#ff7a00]">{campaigns.length}</span></div><div className="mt-1 space-y-1.5">{campaigns.map((campaign) => <button key={campaign.id} onClick={() => setActiveCampaignId(campaign.id)} className={`clicko-interactive-surface w-full rounded-lg border p-3 text-left ${activeCampaign?.id === campaign.id ? 'border-[#ff5c5c]/30 bg-[#ff5c5c]/[0.06]' : 'border-transparent bg-white/[0.018]'}`}><div className="flex items-start justify-between gap-2"><strong className="text-[10px] font-medium text-white">{campaign.name}</strong><ChevronRight className="h-3.5 w-3.5 text-[#555]" /></div><div className="mt-2 flex justify-between text-[7px] uppercase"><span className="text-[#ff7a00]">{strategyStatusLabel[campaign.status]}</span><span className="text-[#555]">Brain rev. {campaign.brainRevision}</span></div></button>)}</div></aside>

      <main className="min-w-0 rounded-xl border border-white/[0.07] bg-[#111] p-5 md:p-6">{activeCampaign ? <><div className="flex flex-wrap items-start justify-between gap-4"><div><span className="text-[8px] uppercase tracking-[0.16em] text-[#ff7a00]">Campanha ativa</span><h2 className="mt-1 text-xl font-semibold text-white">{activeCampaign.name}</h2><p className="mt-2 max-w-3xl text-[10px] leading-relaxed text-[#999]">{activeCampaign.objective}</p></div><button onClick={generateExplosion} disabled={exploding} className="flex items-center gap-2 rounded-lg border border-[#ff7a00]/25 bg-[#ff7a00]/[0.07] px-4 py-2.5 text-[9px] font-semibold text-[#ff9a3d]">{exploding ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}{exploding ? 'Combinando…' : 'Explosão criativa'}</button></div>
        <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-3">{creativeIdeas.filter((idea) => idea.campaignId === activeCampaign.id).map((idea) => { const selected = selectedCreativeIdeaIds.includes(idea.id); return <button key={idea.id} onClick={() => toggleCreativeIdea(idea.id)} className={`clicko-interactive-surface min-h-44 rounded-xl border p-4 text-left ${selected ? 'border-[#ff5c5c]/45 bg-[#ff5c5c]/[0.07]' : 'border-white/[0.06] bg-black/20'}`}><div className="flex items-center justify-between"><span className="rounded-full bg-[#ff7a00]/10 px-2 py-1 text-[7px] uppercase text-[#ff9a3d]">{idea.funnelStage}</span><span className={`grid h-5 w-5 place-items-center rounded-full border ${selected ? 'border-[#ff5c5c] bg-[#ff5c5c] text-white' : 'border-white/10 text-transparent'}`}><Check className="h-3 w-3" /></span></div><strong className="mt-3 block text-[11px] text-white">{idea.angle}</strong><p className="mt-2 text-[9px] leading-relaxed text-[#aaa]">{idea.hook}</p><div className="mt-4 flex items-center justify-between border-t border-white/[0.05] pt-3 text-[7px]"><span className="uppercase text-[#666]">{idea.format}</span><span className="text-[#888]">{idea.rationale}</span></div></button>; })}</div>
        {!creativeIdeas.some((idea) => idea.campaignId === activeCampaign.id) && <div className="mt-5 grid min-h-48 place-items-center rounded-xl border border-dashed border-white/[0.08] bg-black/10 text-center"><div><Layers3 className="mx-auto h-7 w-7 text-[#555]" /><p className="mt-3 text-[10px] text-[#888]">Gere combinações de ângulo, hook, formato, CTA e estágio do funil.</p><p className="mt-1 text-[8px] text-[#555]">A matriz organiza possibilidades; você escolhe o que segue para produção.</p></div></div>}
        {selectedCreativeIdeaIds.length > 0 && <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-[#ff5c5c]/20 bg-[#ff5c5c]/[0.05] p-3"><span className="text-[9px] text-[#ff9b9b]">{selectedCreativeIdeaIds.length} ideia(s) selecionada(s)</span><button onClick={sendSelectedToStudio} className="flex items-center gap-2 rounded-lg bg-[#ff5c5c] px-4 py-2 text-[9px] font-bold text-white">Enviar ao Studio <ArrowRight className="h-3.5 w-3.5" /></button></div>}
      </> : <div className="grid min-h-72 place-items-center text-center"><div><BrainCircuit className="mx-auto h-7 w-7 text-[#555]" /><p className="mt-3 text-[10px] text-[#888]">Crie ou selecione uma campanha para continuar.</p></div></div>}</main>
    </div>
  </div>;
}
