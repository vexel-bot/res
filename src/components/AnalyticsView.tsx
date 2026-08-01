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
  HelpCircle,
} from 'lucide-react';

export const AnalyticsView: React.FC = () => {
  const [period, setPeriod] = React.useState('Últimos 30 Dias');
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
          reachChange: 18.4,
          engagementRate: 6.8,
          topPost: '5 Regras da IA Enterprise em 2026',
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
  }, [period]);

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/5 pb-4">
        <div>
          <h2 className="text-lg font-bold text-[#ededed] flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-indigo-400" /> Analytics Contextual Explicado por IA
          </h2>
          <p className="text-xs text-white/40">
            A IA analisa a oscilação de métricas e traduz os números em justificativas estratégicas e táticas acionáveis
          </p>
        </div>

        <select
          value={period}
          onChange={(e) => setPeriod(e.target.value)}
          className="bg-[#050505] border border-white/5 rounded-xl px-3.5 py-2 text-xs text-[#ededed] focus:outline-none focus:border-indigo-500/50"
        >
          <option value="Últimos 7 Dias">Últimos 7 Dias</option>
          <option value="Últimos 30 Dias">Últimos 30 Dias</option>
          <option value="Últimos 90 Dias">Últimos 90 Dias</option>
        </select>
      </div>

      {/* AI Explanation Banner (High Context) */}
      <div className="p-6 rounded-2xl bg-[#0A0A0A] border border-indigo-500/30 space-y-4 shadow-xl">
        <div className="flex items-center justify-between border-b border-white/5 pb-3">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-indigo-400" />
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
            <div className="p-4 rounded-xl bg-indigo-600/10 border border-indigo-500/20 text-neutral-200 space-y-1.5">
              <div className="font-bold text-indigo-300">Análise do Período ({period})</div>
              <p className="leading-relaxed text-neutral-300">{aiAnalysis.insight}</p>
            </div>

            <div className="p-4 rounded-xl bg-emerald-600/10 border border-emerald-500/20 text-neutral-200 space-y-1.5">
              <div className="font-bold text-emerald-400">Recomendação Prática de Ação</div>
              <p className="leading-relaxed text-neutral-300">{aiAnalysis.recommendation}</p>
            </div>

            {aiAnalysis.keyTakeaways && (
              <div className="space-y-1 pt-1">
                <span className="font-bold text-neutral-300 text-[11px]">Principais Conclusões:</span>
                <ul className="list-disc list-inside space-y-1 text-white/40">
                  {aiAnalysis.keyTakeaways.map((item: string, i: number) => (
                    <li key={i}>{item}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ) : (
          <div className="p-4 text-center text-white/40 text-xs">Carregando diagnóstico...</div>
        )}
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
