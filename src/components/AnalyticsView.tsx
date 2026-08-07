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
} from 'lucide-react';
import { useOperations } from '../context/OperationsContext';
import { useGovernance } from '../context/GovernanceContext';

export const AnalyticsView: React.FC = () => {
  const { brain, activeCampaign, createCampaign } = useOperations();
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
      status: 'planned',
    });
  };

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/[0.06] pb-4">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-[#8bd132]" />
            {isPersonal ? 'Analytics Pessoal & Performance Autoral' : 'Analytics Corporativo & Inteligência de Operação'}
          </h2>
          <p className="text-xs text-[#78858e]">
            {isPersonal
              ? 'Acompanhe seu alcance autoral, engajamento autônomo e crescimento de audiência'
              : 'Métricas analíticas consolidadas por empresa, cliente, equipe, colaborador e canal'}
          </p>
        </div>

        <select
          value={period}
          onChange={(e) => setPeriod(e.target.value)}
          className="bg-[#0c1014] border border-white/[0.08] rounded-xl px-3.5 py-2 text-xs text-white focus:outline-none focus:border-[#8bd132]/50"
        >
          <option value="Últimos 7 Dias">Últimos 7 Dias</option>
          <option value="Últimos 30 Dias">Últimos 30 Dias</option>
          <option value="Últimos 90 Dias">Últimos 90 Dias</option>
        </select>
      </div>

      {/* Corporate Multi-Filters Bar */}
      {!isPersonal && (
        <div className="p-4 rounded-2xl bg-[#0c1015] border border-white/[0.06] space-y-2">
          <div className="flex items-center gap-2 text-xs font-bold text-[#8bd132]">
            <Filter className="w-3.5 h-3.5" />
            <span>Filtros Corporativos Avançados</span>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2.5">
            <select
              value={selectedClient}
              onChange={(e) => setSelectedClient(e.target.value)}
              className="bg-[#121820] border border-white/10 rounded-xl px-3 py-1.5 text-xs text-white focus:outline-none focus:border-[#8bd132]/50"
            >
              <option value="Todos os Clientes">Todos os Clientes</option>
              <option value="Clínica Vitalis">Clínica Vitalis</option>
              <option value="Nexus Tech">Nexus Tech</option>
            </select>

            <select
              value={selectedTeam}
              onChange={(e) => setSelectedTeam(e.target.value)}
              className="bg-[#121820] border border-white/10 rounded-xl px-3 py-1.5 text-xs text-white focus:outline-none focus:border-[#8bd132]/50"
            >
              <option value="Toda a Equipe">Toda a Equipe</option>
              <option value="Marketing Digital">Marketing Digital</option>
              <option value="Criação & Design">Criação & Design</option>
            </select>

            <select
              value={selectedCollaborator}
              onChange={(e) => setSelectedCollaborator(e.target.value)}
              className="bg-[#121820] border border-white/10 rounded-xl px-3 py-1.5 text-xs text-white focus:outline-none focus:border-[#8bd132]/50"
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
              className="bg-[#121820] border border-white/10 rounded-xl px-3 py-1.5 text-xs text-white focus:outline-none focus:border-[#8bd132]/50"
            >
              <option value="Todas as Campanhas">Todas Campanhas</option>
              <option value="Lançamento Q3">Lançamento Q3</option>
              <option value="Branding Institucional">Branding Institucional</option>
            </select>

            <select
              value={selectedNetwork}
              onChange={(e) => setSelectedNetwork(e.target.value)}
              className="bg-[#121820] border border-white/10 rounded-xl px-3 py-1.5 text-xs text-white focus:outline-none focus:border-[#8bd132]/50"
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
      <div className="p-6 rounded-2xl bg-[#0a0e11] border border-[#8bd132]/30 space-y-4 shadow-xl shadow-black/40">
        <div className="flex items-center justify-between border-b border-white/[0.06] pb-3">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-[#8bd132]" />
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
                <Sparkles className="h-3.5 w-3.5 text-[#8bd132]" /> Análise do Período ({period})
              </div>
              <p className="leading-relaxed text-[#a0abb2]">{aiAnalysis.insight}</p>
            </div>

            <div className="p-4 rounded-xl bg-[#8bd132]/10 border border-[#8bd132]/30 text-white space-y-1.5">
              <div className="font-bold text-[#8bd132]">Recomendação Prática de Ação</div>
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
              className="flex items-center gap-2 rounded-xl bg-[#8bd132] px-4 py-2.5 text-xs font-bold text-[#080e05] transition hover:bg-[#9be24d] shadow-lg shadow-[#8bd132]/20"
            >
              <Sparkles className="h-4 w-4" />
              <span>Criar Campanha a partir desta Análise</span>
            </button>
          </div>
        ) : (
          <div className="p-4 text-center text-[#78848c] text-xs">Carregando diagnóstico contextual...</div>
        )}
      </div>

      {/* AI Social Media BI Breakdown Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-4 rounded-2xl bg-[#182126] border border-white/[0.07] space-y-2">
          <span className="text-[9px] font-bold uppercase tracking-wider text-[#8bd132]">
            Melhores Horários
          </span>
          <h4 className="text-xs font-bold text-white">Horários de Pico da Audiência</h4>
          <ul className="text-[10px] text-[#a0abb0] space-y-1">
            <li className="flex justify-between"><span>Terças-feiras</span><strong className="text-[#8bd132]">18:30 (Retenção 94%)</strong></li>
            <li className="flex justify-between"><span>Quintas-feiras</span><strong className="text-[#8bd132]">09:00 (Engajamento 8.8%)</strong></li>
            <li className="flex justify-between"><span>Sábados</span><strong className="text-[#8bd132]">11:00 (Salvamentos 2.4x)</strong></li>
          </ul>
        </div>

        <div className="p-4 rounded-2xl bg-[#182126] border border-white/[0.07] space-y-2">
          <span className="text-[9px] font-bold uppercase tracking-wider text-[#8bd132]">
            Formatos & Performance
          </span>
          <h4 className="text-xs font-bold text-white">Carrosséis vs Posts Estáticos</h4>
          <div className="text-[10px] text-[#a0abb0] space-y-1">
            <p>• Carrosséis educativos têm <strong className="text-white">8.4% engajamento</strong></p>
            <p>• Posts estáticos simples tiveram <strong className="text-amber-400">pior desempenho (1.8%)</strong></p>
            <p className="text-[#8bd132] font-semibold mt-1">Recomendação: Substituir textos únicos por carrossel de 3 lâminas.</p>
          </div>
        </div>

        <div className="p-4 rounded-2xl bg-[#182126] border border-white/[0.07] space-y-2">
          <span className="text-[9px] font-bold uppercase tracking-wider text-[#8bd132]">
            Oportunidades de Conteúdo
          </span>
          <h4 className="text-xs font-bold text-white">Gaps Detectados pela IA</h4>
          <div className="text-[10px] text-[#a0abb0] space-y-1">
            <p>• Pauta "Automação Operacional" tem busca alta e pouca concorrência.</p>
            <p>• Publicar 1 Reel semanal gera <strong className="text-white">+380 novos seguidores qualificados</strong>.</p>
          </div>
        </div>
      </div>

      {/* Metrics Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-4 rounded-2xl bg-[#0A0A0A] border border-white/5 space-y-2">
          <div className="flex items-center justify-between text-white/40 text-xs">
            <span>Alcance Orgânico</span>
            <Eye className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-2xl font-extrabold text-[#ededed]">184,200</div>
          <div className="text-xs font-bold text-emerald-400 flex items-center gap-0.5">
            <ArrowUpRight className="w-3.5 h-3.5" /> +18.4% este mês
          </div>
        </div>

        <div className="p-4 rounded-2xl bg-[#0A0A0A] border border-white/5 space-y-2">
          <div className="flex items-center justify-between text-white/40 text-xs">
            <span>Interações Totais</span>
            <Heart className="w-4 h-4 text-rose-400" />
          </div>
          <div className="text-2xl font-extrabold text-[#ededed]">14,820</div>
          <div className="text-xs font-bold text-emerald-400 flex items-center gap-0.5">
            <ArrowUpRight className="w-3.5 h-3.5" /> +22.1% este mês
          </div>
        </div>

        <div className="p-4 rounded-2xl bg-[#0A0A0A] border border-white/5 space-y-2">
          <div className="flex items-center justify-between text-white/40 text-xs">
            <span>Salvamentos / Compartilhamentos</span>
            <Share2 className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-extrabold text-[#ededed]">3,120</div>
          <div className="text-xs font-bold text-emerald-400 flex items-center gap-0.5">
            <ArrowUpRight className="w-3.5 h-3.5" /> +34.0% este mês
          </div>
        </div>

        <div className="p-4 rounded-2xl bg-[#0A0A0A] border border-white/5 space-y-2">
          <div className="flex items-center justify-between text-white/40 text-xs">
            <span>Conversão em Leads</span>
            <TrendingUp className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-extrabold text-[#ededed]">418</div>
          <div className="text-xs font-bold text-emerald-400 flex items-center gap-0.5">
            <ArrowUpRight className="w-3.5 h-3.5" /> +12.8% este mês
          </div>
        </div>
      </div>
    </div>
  );
};
