import React from 'react';
import {
  BarChart3,
  Sparkles,
  TrendingUp,
  Eye,
  Heart,
  MessageSquare,
  Share2,
  RefreshCw,
  ArrowUpRight,
  Filter,
  Users,
  Building,
  Target,
  FolderKanban,
  Share,
  BrainCircuit,
  WandSparkles,
} from 'lucide-react';
import { useOperations } from '../context/OperationsContext';
import { useGovernance } from '../context/GovernanceContext';

export const AnalyticsView: React.FC<{ onOpenStudio?: () => void }> = ({ onOpenStudio }) => {
  const { brain, activeClient, activeCampaign, learningSignals, createCampaign, prepareStudioHandoff, addLearningSignal } = useOperations();
  const { environmentMode, users } = useGovernance();
  const isPersonal = environmentMode === 'personal';

  const [period, setPeriod] = React.useState('Últimos 30 Dias');
  const [selectedClient, setSelectedClient] = React.useState('Todos os Clientes');
  const [selectedTeam, setSelectedTeam] = React.useState('Toda a Equipe');
  const [selectedCollaborator, setSelectedCollaborator] = React.useState('Todos os Colaboradores');
  const [selectedNetwork, setSelectedNetwork] = React.useState('Todas as Redes');
  const [selectedCampaign, setSelectedCampaign] = React.useState('Todas as Campanhas');

  const [aiAnalysis, setAiAnalysis] = React.useState<any>(null);
  const [isLoadingAnalysis, setIsLoadingAnalysis] = React.useState(false);

  const fetchAiAnalysis = async () => {
    setIsLoadingAnalysis(true);
    try {
      const res = await fetch('/api/ai/analyze-metrics', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          period,
          environmentMode,
          selectedClient,
          selectedCollaborator,
          reachChange: 18.4,
          engagementRate: 6.8,
          topPost: isPersonal ? 'Artigo autoral sobre IA & Engenharia' : '5 Regras da IA corporativa em 2026',
          brainContext: brain,
          clientContext: activeClient,
          strategyContext: activeCampaign,
        }),
      });

      const data = await res.json();
      setAiAnalysis(data);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoadingAnalysis(false);
    }
  };

  React.useEffect(() => {
    fetchAiAnalysis();
  }, [period, environmentMode, selectedClient, selectedCollaborator]);

  const turnInsightIntoCampaign = () => {
    if (!aiAnalysis) return;
    createCampaign({
      name: `Oportunidade de performance — ${period}`,
      objective: aiAnalysis.recommendation || aiAnalysis.insight,
      startDate: new Date().toISOString().slice(0, 10),
      endDate: new Date(Date.now() + 21 * 86_400_000).toISOString().slice(0, 10),
      budget: 'A definir',
      kpis: ['Alcance qualificado', 'Engajamento', 'Conversões'],
      products: brain.products,
      audience: brain.audience,
      offer: 'Conteúdo derivado do melhor padrão de desempenho',
      channels: ['instagram', 'linkedin'],
      importantDates: '',
      funnel: 'Descoberta → Consideração → Conversão',
      ctas: ['Conhecer a solução'],
      executionPlan: aiAnalysis.keyTakeaways || ['Replicar o padrão vencedor', 'Testar variações', 'Medir resultados'],
      clientId: activeClient?.id,
      centralMessage: aiAnalysis.recommendation || aiAnalysis.insight,
      angle: 'Aprendizado orientado por padrões de conteúdo',
      status: 'planned',
    });
  };

  const createVariants = () => {
    if (!aiAnalysis) return;
    prepareStudioHandoff({
      source: 'analytics', clientId: activeClient?.id, campaignId: activeCampaign?.id,
      objective: aiAnalysis.recommendation || 'Transformar o aprendizado em novas variações.',
      title: 'Variações orientadas por aprendizado', angle: aiAnalysis.insight || 'Reaplicar o padrão observado',
      hook: aiAnalysis.keyTakeaways?.[0] || 'Uma nova abordagem para a mensagem que já existe',
      cta: 'Criar cinco variações', format: 'carousel', funnelStage: 'Aprendizado',
    });
    addLearningSignal({
      clientId: activeClient?.id, campaignId: activeCampaign?.id,
      label: 'Hipótese enviada para produção', evidence: 'Derivada do diagnóstico exibido com dados locais de demonstração.',
      recommendation: aiAnalysis.recommendation || 'Testar variações antes de validar o padrão.',
      confidence: 'hypothesis', source: 'content-metadata',
    });
    onOpenStudio?.();
  };

  return (
    <div className="clicko-analytics-editorial mx-auto max-w-[1580px] space-y-5 p-5">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/[0.06] pb-4">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-[#ff5c5c]" />
            {isPersonal ? 'Analytics Pessoal & Performance Autoral' : 'Analytics Corporativo & Inteligência de Operação'}
          </h2>
          <p className="text-xs text-[#78858e]">
            {isPersonal
              ? 'Acompanhe seu alcance autoral, engajamento autônomo e crescimento de audiência'
              : 'Métricas analíticas consolidadas por empresa, cliente, equipe, colaborador e canal'}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2"><span className="rounded-full border border-[#ff7a00]/20 bg-[#ff7a00]/[0.06] px-2.5 py-1.5 text-[8px] text-[#ff9a3d]">Dados locais demonstrativos</span><select
          value={period}
          onChange={(e) => setPeriod(e.target.value)}
          className="bg-[#0c1014] border border-white/[0.08] rounded-xl px-3.5 py-2 text-xs text-white focus:outline-none focus:border-[#ff5c5c]/50"
        >
          <option value="Últimos 7 Dias">Últimos 7 Dias</option>
          <option value="Últimos 30 Dias">Últimos 30 Dias</option>
          <option value="Últimos 90 Dias">Últimos 90 Dias</option>
        </select></div>
      </div>

      {/* Corporate Multi-Filters Bar */}
      {!isPersonal && (
        <div className="space-y-2 rounded-xl border border-white/[0.06] bg-[#101316] p-4">
          <div className="flex items-center gap-2 text-xs font-bold text-[#ff5c5c]">
            <Filter className="w-3.5 h-3.5" />
            <span>Filtros Corporativos Avançados</span>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2.5">
            <select
              value={selectedClient}
              onChange={(e) => setSelectedClient(e.target.value)}
              className="bg-[#121820] border border-white/10 rounded-xl px-3 py-1.5 text-xs text-white focus:outline-none focus:border-[#ff5c5c]/50"
            >
              <option value="Todos os Clientes">Todos os Clientes</option>
              <option value="Clínica Vitalis">Clínica Vitalis</option>
              <option value="Nexus Tech">Nexus Tech</option>
            </select>

            <select
              value={selectedTeam}
              onChange={(e) => setSelectedTeam(e.target.value)}
              className="bg-[#121820] border border-white/10 rounded-xl px-3 py-1.5 text-xs text-white focus:outline-none focus:border-[#ff5c5c]/50"
            >
              <option value="Toda a Equipe">Toda a Equipe</option>
              <option value="Marketing Digital">Marketing Digital</option>
              <option value="Criação & Design">Criação & Design</option>
            </select>

            <select
              value={selectedCollaborator}
              onChange={(e) => setSelectedCollaborator(e.target.value)}
              className="bg-[#121820] border border-white/10 rounded-xl px-3 py-1.5 text-xs text-white focus:outline-none focus:border-[#ff5c5c]/50"
            >
              <option value="Todos os Colaboradores">Todos Colaboradores</option>
              {users.map((u) => (
                <option key={u.id} value={u.name}>
                  {u.name}
                </option>
              ))}
            </select>

            <select
              value={selectedCampaign}
              onChange={(e) => setSelectedCampaign(e.target.value)}
              className="bg-[#121820] border border-white/10 rounded-xl px-3 py-1.5 text-xs text-white focus:outline-none focus:border-[#ff5c5c]/50"
            >
              <option value="Todas as Campanhas">Todas Campanhas</option>
              <option value="Lançamento Q3">Lançamento Q3</option>
              <option value="Branding Institucional">Branding Institucional</option>
            </select>

            <select
              value={selectedNetwork}
              onChange={(e) => setSelectedNetwork(e.target.value)}
              className="bg-[#121820] border border-white/10 rounded-xl px-3 py-1.5 text-xs text-white focus:outline-none focus:border-[#ff5c5c]/50"
            >
              <option value="Todas as Redes">Todas as Redes</option>
              <option value="Instagram">Instagram</option>
              <option value="LinkedIn">LinkedIn</option>
              <option value="YouTube">YouTube</option>
              <option value="TikTok">TikTok</option>
            </select>
          </div>
        </div>
      )}

      {/* AI Explanation Banner (High Context) */}
      <div className="space-y-4 rounded-xl border border-[#ff5c5c]/20 bg-[#101316] p-5">
        <div className="flex items-center justify-between border-b border-white/[0.06] pb-3">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-[#ff5c5c]" />
            <h3 className="text-sm font-bold text-[#ededed]">Diagnóstico e Explicação Contextual da IA</h3>
          </div>
          <button
            onClick={fetchAiAnalysis}
            disabled={isLoadingAnalysis}
            className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoadingAnalysis ? 'animate-spin' : ''}`} /> Recalcular
          </button>
        </div>

        {aiAnalysis ? (
          <div className="space-y-4 text-xs">
            <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.08] text-[#c0c8ce] space-y-1.5">
              <div className="font-bold text-white flex items-center gap-1.5">
                <Sparkles className="h-3.5 w-3.5 text-[#ff5c5c]" /> Análise do Período ({period})
              </div>
              <p className="leading-relaxed text-[#a0abb2]">{aiAnalysis.insight}</p>
            </div>

            <div className="p-4 rounded-xl bg-[#ff5c5c]/10 border border-[#ff5c5c]/30 text-white space-y-1.5">
              <div className="font-bold text-[#ff5c5c]">Recomendação Prática de Ação</div>
              <p className="leading-relaxed text-[#d0d8dd]">{aiAnalysis.recommendation}</p>
            </div>

            {aiAnalysis.keyTakeaways && (
              <div className="space-y-1 pt-1">
                <span className="font-bold text-white text-[11px]">Principais Conclusões:</span>
                <ul className="list-disc list-inside space-y-1 text-[#808c94]">
                  {aiAnalysis.keyTakeaways.map((item: string, i: number) => (
                    <li key={i}>{item}</li>
                  ))}
                </ul>
              </div>
            )}
            <button
              type="button"
              onClick={turnInsightIntoCampaign}
              className="flex items-center gap-2 rounded-lg bg-[#ff5c5c] px-4 py-2.5 text-xs font-semibold text-[#080e05] transition-colors hover:bg-[#9be24d]"
            >
              <Sparkles className="h-4 w-4" />
              <span>Criar Campanha a partir desta Análise</span>
            </button>
            <button type="button" onClick={createVariants} className="ml-2 inline-flex items-center gap-2 rounded-lg border border-[#ff5c5c]/25 bg-[#ff5c5c]/[0.07] px-4 py-2.5 text-xs font-semibold text-[#ff8a8a]"><WandSparkles className="h-4 w-4" />Criar 5 variações no Studio</button>
          </div>
        ) : (
          <div className="p-4 text-center text-[#78848c] text-xs">Carregando diagnóstico contextual...</div>
        )}
      </div>

      <section className="rounded-xl border border-white/[0.07] bg-[#101010] p-5"><div className="flex items-start justify-between gap-4"><div><div className="flex items-center gap-2 text-[9px] uppercase tracking-[0.16em] text-[#ff7a00]"><BrainCircuit className="h-4 w-4" />Aprendizado do Brain</div><h3 className="mt-1 text-sm font-semibold text-white">Padrões viram próximas ações.</h3></div><span className="text-[8px] text-[#666]">Hipóteses até a conexão de analytics</span></div><div className="mt-4 grid gap-2 md:grid-cols-2">{learningSignals.slice(0, 4).map((signal) => <article key={signal.id} className="rounded-lg border border-white/[0.055] bg-black/20 p-3"><div className="flex items-center justify-between gap-2"><strong className="text-[9px] text-white">{signal.label}</strong><span className={`rounded-full px-2 py-1 text-[7px] uppercase ${signal.confidence === 'validated' ? 'bg-[#ff5c5c]/10 text-[#ff8a8a]' : 'bg-[#ff7a00]/10 text-[#ff9a3d]'}`}>{signal.confidence === 'validated' ? 'validado' : 'hipótese'}</span></div><p className="mt-2 text-[8px] leading-relaxed text-[#777]">{signal.evidence}</p><p className="mt-2 text-[8px] leading-relaxed text-[#aaa]">{signal.recommendation}</p></article>)}</div></section>

      {/* AI Social Media BI Breakdown Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="space-y-2 rounded-xl border border-white/[0.07] bg-[#101316] p-4">
          <span className="text-[9px] font-bold uppercase tracking-wider text-[#ff5c5c]">
            Hipótese de horário
          </span>
          <h4 className="text-xs font-bold text-white">Faixas a validar</h4>
          <ul className="text-[10px] text-[#a0abb0] space-y-1">
            <li className="flex justify-between"><span>Manhã</span><strong className="text-[#ff5c5c]">Teste A</strong></li>
            <li className="flex justify-between"><span>Fim da tarde</span><strong className="text-[#ff5c5c]">Teste B</strong></li>
            <li className="pt-1 text-[#6f7a80]">Conecte uma fonte para identificar horários reais.</li>
          </ul>
        </div>

        <div className="space-y-2 rounded-xl border border-white/[0.07] bg-[#101316] p-4">
          <span className="text-[9px] font-bold uppercase tracking-wider text-[#ff5c5c]">
            Hipótese de formato
          </span>
          <h4 className="text-xs font-bold text-white">Carrossel vs publicação estática</h4>
          <div className="text-[10px] text-[#a0abb0] space-y-1">
            <p>• Testar a mesma mensagem nos dois formatos.</p>
            <p>• Comparar retenção e intenção com critérios iguais.</p>
            <p className="text-[#ff5c5c] font-semibold mt-1">Recomendação: criar variações controladas antes de concluir.</p>
          </div>
        </div>

        <div className="space-y-2 rounded-xl border border-white/[0.07] bg-[#101316] p-4">
          <span className="text-[9px] font-bold uppercase tracking-wider text-[#ff5c5c]">
            Oportunidades contextuais
          </span>
          <h4 className="text-xs font-bold text-white">Pautas sugeridas pelo Brain</h4>
          <div className="text-[10px] text-[#a0abb0] space-y-1">
            <p>• Explorar “Automação Operacional” pelo ângulo de clareza e rotina.</p>
            <p>• Validar Reels e carrosséis sem presumir resultado futuro.</p>
          </div>
        </div>
      </div>

      {/* Metrics Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="space-y-2 rounded-xl border border-white/[0.06] bg-[#101316] p-4">
          <div className="flex items-center justify-between text-white/40 text-xs">
            <span>Alcance Orgânico</span>
            <Eye className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-2xl font-extrabold text-[#ededed]">—</div>
          <div className="text-xs text-[#6f7a80] flex items-center gap-0.5">
            Aguardando fonte conectada
          </div>
        </div>

        <div className="space-y-2 rounded-xl border border-white/[0.06] bg-[#101316] p-4">
          <div className="flex items-center justify-between text-white/40 text-xs">
            <span>Interações Totais</span>
            <Heart className="w-4 h-4 text-rose-400" />
          </div>
          <div className="text-2xl font-extrabold text-[#ededed]">—</div>
          <div className="text-xs text-[#6f7a80] flex items-center gap-0.5">
            Aguardando fonte conectada
          </div>
        </div>

        <div className="space-y-2 rounded-xl border border-white/[0.06] bg-[#101316] p-4">
          <div className="flex items-center justify-between text-white/40 text-xs">
            <span>Salvamentos / Compartilhamentos</span>
            <Share2 className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-extrabold text-[#ededed]">—</div>
          <div className="text-xs text-[#6f7a80] flex items-center gap-0.5">
            Aguardando fonte conectada
          </div>
        </div>

        <div className="space-y-2 rounded-xl border border-white/[0.06] bg-[#101316] p-4">
          <div className="flex items-center justify-between text-white/40 text-xs">
            <span>Conversão em Leads</span>
            <TrendingUp className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-extrabold text-[#ededed]">—</div>
          <div className="text-xs text-[#6f7a80] flex items-center gap-0.5">
            Aguardando fonte conectada
          </div>
        </div>
      </div>
    </div>
  );
};
