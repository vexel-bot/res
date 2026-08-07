import React from 'react';
import {
  FileText,
  Sparkles,
  Calendar,
  Layers,
  ArrowRight,
  CheckCircle2,
  RefreshCw,
  Send,
  Target,
  Megaphone,
  Briefcase
} from 'lucide-react';
import { useOperations } from '../context/OperationsContext';

export const SmartBriefingView: React.FC = () => {
  const { brain, activeCampaign, createCampaign, setPosts } = useOperations();

  const [objetivo, setObjetivo] = React.useState('Aumentar Vendas e Autoridade de Marca');
  const [campanha, setCampanha] = React.useState('Lançamento Primavera/Verão 2026');
  const [produto, setProduto] = React.useState('Plataforma SaaS Clicko Studio');
  const [oferta, setOferta] = React.useState('30% de Desconto + Consultoria com IA Integrada');
  const [publico, setPublico] = React.useState('Agências de Marketing, Social Medias e Empreendedores Digitais');

  const [isGenerating, setIsGenerating] = React.useState(false);
  const [briefingResult, setBriefingResult] = React.useState<any>({
    planning: `Plano estratégico estruturado para o "${campanha}". A meta principal é impulsionar "${objetivo}" ancorando na oferta irrelevante "${oferta}" para o público "${publico}".`,
    timeline: [
      'Semana 1: Conscientização e Revelação de Dores de Mercado (Topo de Funil)',
      'Semana 2: Demonstração de Recursos da IA e Estudos de Caso (Meio de Funil)',
      'Semana 3: Lançamento Oficial da Oferta e Depoimentos (Fundo de Funil)',
      'Semana 4: Última Chamada para Condição Especial e Bônus Exclusivos'
    ],
    suggestedContents: [
      { platform: 'Instagram', format: 'Carrossel', title: `5 Motivos para usar o Sistema Operacional da ${produto}`, date: 'Segunda-feira, 09:00' },
      { platform: 'LinkedIn', format: 'Artigo Executivo', title: `Como a IA reduz 80% do tempo de produção de redes sociais`, date: 'Terça-feira, 11:30' },
      { platform: 'TikTok', format: 'Reels / Short', title: `Testando a IA ao vivo na criação do ${campanha}`, date: 'Quarta-feira, 18:00' },
      { platform: 'Instagram', format: 'Anúncio / VSL', title: `Garantir Oferta com ${oferta}`, date: 'Sexta-feira, 19:00' }
    ],
    adsStructure: [
      { hook: 'Se você perde tempo criando posts um a um, pare agora.', adType: 'Tráfego Direto - Vídeo Curto', target: 'Público Frio' },
      { hook: `Ainda dá tempo de garantir ${oferta} neste trimestre.`, adType: 'Remarketing - Carrossel', target: 'Público Engajado' }
    ]
  });

  const handleGenerateBriefing = async () => {
    setIsGenerating(true);
    try {
      const res = await fetch('/api/ai/intelligent-briefing', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          objetivo,
          campanha,
          produto,
          oferta,
          publico,
          brainContext: brain,
          strategyContext: activeCampaign,
        }),
      });
      const data = await res.json();
      setBriefingResult(data);
    } catch (err) {
      console.error(err);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleExportToCampaignAndCalendar = () => {
    if (!briefingResult) return;

    // 1. Create strategy campaign
    createCampaign({
      name: campanha,
      objective: briefingResult.planning || objetivo,
      startDate: new Date().toISOString().slice(0, 10),
      endDate: new Date(Date.now() + 30 * 86_400_000).toISOString().slice(0, 10),
      budget: 'Definido pelo Briefing',
      kpis: ['Vendas', 'Leads Qualificados', 'Engajamento'],
      products: produto,
      audience: publico,
      offer: oferta,
      channels: ['instagram', 'linkedin', 'tiktok'],
      importantDates: briefingResult.timeline?.join('\n') || '',
      funnel: 'Topo, Meio e Fundo de Funil Integrados',
      ctas: ['Garantir Vaga', 'Acessar Demonstração'],
      executionPlan: briefingResult.timeline || [],
      status: 'active',
    });

    // 2. Inject suggested contents into Posts
    if (briefingResult.suggestedContents && briefingResult.suggestedContents.length > 0) {
      const newPosts = briefingResult.suggestedContents.map((item: any, idx: number) => ({
        id: `post-briefing-${Date.now()}-${idx}`,
        workspaceId: brain.workspaceId || 'current-ws',
        title: item.title,
        platform: item.platform?.toLowerCase() || 'instagram',
        format: item.format?.toLowerCase()?.includes('carrossel') ? 'carousel' : 'post',
        copy: `[Gerado por Briefing Inteligente]\n\n${item.title}\n\nGaranta os detalhes da nossa campanha "${campanha}" e aproveite a oferta "${oferta}".`,
        hashtags: ['#BriefingInteligente', '#ClickoStudio', '#Campanha2026'],
        scheduledAt: new Date(Date.now() + (idx + 1) * 86_400_000).toISOString(),
        status: 'scheduled' as const,
        author: 'IA Clicko Studio',
        createdAt: new Date().toISOString(),
        aiScore: 97,
        origin: 'brain' as const,
      }));

      setPosts((prev) => [...newPosts, ...prev]);
    }

    alert('Briefing convertido em Campanha Ativa e inserido no Calendário Editorial com sucesso!');
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="rounded-2xl border border-white/[0.08] bg-gradient-to-r from-[#182126] via-[#12191d] to-[#0d1316] p-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-[#8bd132]/30 bg-[#8bd132]/[0.08] px-3 py-1 text-[10px] font-bold text-[#8bd132]">
              <FileText className="h-3.5 w-3.5" /> Briefing Estratégico Guiado por IA
            </div>
            <h2 className="mt-2 text-xl font-bold text-white">Briefing Inteligente de Mídia Social</h2>
            <p className="mt-1 text-xs text-[#8f9a9f]">
              Informe o objetivo e a oferta. A IA constrói instantaneamente o planejamento, cronograma, calendário e estrutura de anúncios.
            </p>
          </div>
          <button
            onClick={handleGenerateBriefing}
            disabled={isGenerating}
            className="flex items-center gap-2 rounded-xl bg-[#8bd132] px-5 py-3 text-xs font-bold text-[#14200e] hover:bg-[#9be24d] transition shadow-lg shadow-[#8bd132]/20 disabled:opacity-50"
          >
            {isGenerating ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
            {isGenerating ? 'Montando Planejamento...' : 'Gerar Briefing Completo'}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Input Column */}
        <div className="lg:col-span-5 space-y-4">
          <div className="rounded-2xl border border-white/[0.07] bg-[#182126] p-5 space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-white flex items-center gap-2 border-b border-white/[0.06] pb-3">
              <Briefcase className="h-4 w-4 text-[#8bd132]" /> Dados do Briefing
            </h3>

            <div>
              <label className="block text-[10px] font-semibold text-[#aeb8bd] mb-1">
                Nome da Campanha
              </label>
              <input
                value={campanha}
                onChange={(e) => setCampanha(e.target.value)}
                placeholder="Ex: Lançamento Trimestral 2026"
                className="w-full rounded-xl border border-white/[0.08] bg-black/30 p-2.5 text-xs text-white outline-none focus:border-[#8bd132]/40"
              />
            </div>

            <div>
              <label className="block text-[10px] font-semibold text-[#aeb8bd] mb-1">
                Objetivo Estratégico
              </label>
              <input
                value={objetivo}
                onChange={(e) => setObjetivo(e.target.value)}
                placeholder="Ex: Gerar 500 novos leads B2B qualificados"
                className="w-full rounded-xl border border-white/[0.08] bg-black/30 p-2.5 text-xs text-white outline-none focus:border-[#8bd132]/40"
              />
            </div>

            <div>
              <label className="block text-[10px] font-semibold text-[#aeb8bd] mb-1">
                Produto ou Serviço
              </label>
              <input
                value={produto}
                onChange={(e) => setProduto(e.target.value)}
                placeholder="Ex: Mentoria de IA para Marketing"
                className="w-full rounded-xl border border-white/[0.08] bg-black/30 p-2.5 text-xs text-white outline-none focus:border-[#8bd132]/40"
              />
            </div>

            <div>
              <label className="block text-[10px] font-semibold text-[#aeb8bd] mb-1">
                Oferta Principal (Hook Comercial)
              </label>
              <textarea
                value={oferta}
                onChange={(e) => setOferta(e.target.value)}
                rows={2}
                placeholder="Ex: 50% de desconto no primeiro mês + onboarding VIP"
                className="w-full resize-none rounded-xl border border-white/[0.08] bg-black/30 p-2.5 text-xs text-white outline-none focus:border-[#8bd132]/40"
              />
            </div>

            <div>
              <label className="block text-[10px] font-semibold text-[#aeb8bd] mb-1">
                Público-Alvo Prioritário
              </label>
              <input
                value={publico}
                onChange={(e) => setPublico(e.target.value)}
                placeholder="Ex: Diretores de Agências e Gestores"
                className="w-full rounded-xl border border-white/[0.08] bg-black/30 p-2.5 text-xs text-white outline-none focus:border-[#8bd132]/40"
              />
            </div>
          </div>
        </div>

        {/* AI Briefing Results Column */}
        <div className="lg:col-span-7 space-y-4">
          <div className="rounded-2xl border border-white/[0.07] bg-[#182126] p-6 space-y-5">
            <div className="flex items-center justify-between border-b border-white/[0.06] pb-3">
              <div className="flex items-center gap-2">
                <span className="grid h-8 w-8 place-items-center rounded-lg bg-[#8bd132]/10 text-[#8bd132]">
                  <Target className="h-4 w-4" />
                </span>
                <div>
                  <h3 className="text-xs font-bold text-white">Plano Gerado Automaticamente</h3>
                  <p className="text-[10px] text-[#78848a]">Sincronizado com os dados do seu Brain</p>
                </div>
              </div>
            </div>

            {/* Executive Summary */}
            <div className="rounded-xl border border-white/[0.06] bg-black/25 p-4 space-y-1">
              <span className="text-[9px] font-bold uppercase tracking-wider text-[#8bd132]">
                Resumo Executivo do Planejamento
              </span>
              <p className="text-xs text-[#cdd4d7] leading-relaxed">{briefingResult.planning}</p>
            </div>

            {/* Timeline */}
            {briefingResult.timeline && (
              <div className="space-y-2">
                <span className="text-[9px] font-bold uppercase tracking-wider text-[#8bd132]">
                  Cronograma de Execução por Semanas
                </span>
                <div className="space-y-2">
                  {briefingResult.timeline.map((step: string, idx: number) => (
                    <div
                      key={idx}
                      className="flex items-center gap-3 rounded-xl border border-white/[0.05] bg-black/30 p-3"
                    >
                      <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-[#8bd132]/10 text-[10px] font-bold text-[#8bd132]">
                        {idx + 1}
                      </span>
                      <p className="text-xs text-white">{step}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Suggested Editorial Content */}
            {briefingResult.suggestedContents && (
              <div className="space-y-2">
                <span className="text-[9px] font-bold uppercase tracking-wider text-[#8bd132]">
                  Conteúdos Sugeridos para o Calendário
                </span>
                <div className="grid gap-2 md:grid-cols-2">
                  {briefingResult.suggestedContents.map((c: any, i: number) => (
                    <div key={i} className="rounded-xl border border-white/[0.06] bg-black/30 p-3 space-y-1">
                      <div className="flex items-center justify-between text-[9px] font-bold text-[#8bd132]">
                        <span>{c.platform} · {c.format}</span>
                        <span className="text-[#8e989d]">{c.date}</span>
                      </div>
                      <h5 className="text-[11px] font-semibold text-white line-clamp-2">{c.title}</h5>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Ads Structure */}
            {briefingResult.adsStructure && (
              <div className="space-y-2">
                <span className="text-[9px] font-bold uppercase tracking-wider text-[#8bd132]">
                  Estrutura de Anúncios Recomenda
                </span>
                <div className="space-y-2">
                  {briefingResult.adsStructure.map((ad: any, i: number) => (
                    <div key={i} className="rounded-xl border border-white/[0.06] bg-black/30 p-3 flex flex-col md:flex-row md:items-center justify-between gap-2">
                      <div>
                        <span className="text-[9px] font-bold text-[#8bd132]">{ad.adType} · {ad.target}</span>
                        <p className="text-xs text-white font-medium mt-0.5">"{ad.hook}"</p>
                      </div>
                      <span className="shrink-0 text-[9px] font-bold bg-[#8bd132]/10 px-2 py-1 rounded text-[#8bd132]">
                        Pronto para Tráfego
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Action Bar */}
            <div className="pt-3 border-t border-white/[0.06]">
              <button
                onClick={handleExportToCampaignAndCalendar}
                className="w-full flex items-center justify-center gap-2 rounded-xl bg-[#8bd132] py-3 text-xs font-bold text-[#14200e] hover:bg-[#9be24d] transition shadow-lg shadow-[#8bd132]/20"
              >
                <Calendar className="h-4 w-4" /> Converter em Campanha Ativa & Inserir no Calendário
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
