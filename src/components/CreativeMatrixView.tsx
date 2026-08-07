import React from 'react';
import {
  Sparkles,
  Target,
  Flame,
  HelpCircle,
  TrendingUp,
  Zap,
  ArrowRight,
  CheckCircle2,
  Copy,
  Calendar,
  Layers,
  Send,
  RefreshCw,
  Sliders,
  UserCheck
} from 'lucide-react';
import { useOperations } from '../context/OperationsContext';
import type { Post } from '../types';

interface CreativeMatrixViewProps {
  onSavePost?: (post: Partial<Post>) => void;
}

export const CreativeMatrixView: React.FC<CreativeMatrixViewProps> = ({ onSavePost }) => {
  const { brain, activeCampaign } = useOperations();

  const [gancho, setGancho] = React.useState('O maior erro que impede seu crescimento em 2026');
  const [angulo, setAngulo] = React.useState('Contradição e Eficiência Operacional');
  const [emocao, setEmocao] = React.useState('Urgência com Empoderamento');
  const [dor, setDor] = React.useState('Perda de tempo com processos repetitivos de criação');
  const [desejo, setDesejo] = React.useState('Centralizar toda a estratégia em um único Sistema Operacional de IA');
  const [cta, setCta] = React.useState('Comente "SISTEMA" para testar gratuitamente');
  const [estagioFunil, setEstagioFunil] = React.useState('Topo de Funil');
  const [persona, setPersona] = React.useState('Social Medias e Gestores de Comunicação');
  const [platform, setPlatform] = React.useState('instagram');
  const [format, setFormat] = React.useState('carousel');

  const [isGenerating, setIsGenerating] = React.useState(false);
  const [matrixResult, setMatrixResult] = React.useState<any>({
    headline: '[ATENÇÃO] Por que continuar gastando 15 horas semanais em tarefas manuais?',
    copy: `Se você quer resultados extraordinários na gestão de redes sociais, precisa parar de tratar a IA como um simples chat.\n\nÂngulo: Contradição e Eficiência\nEmoção: Urgência e Empoderamento\n\n1. O modelo tradicional de criação está esgotado\n2. Quem usa um Sistema Operacional com IA multiplica o alcance com menos esforço\n3. Unifique Brain, Agendamento e Produção Multimídia\n\nComente "SISTEMA" para testar gratuitamente.`,
    slides: [
      { slideNumber: 1, headline: 'O ERRO QUE CUSTA 15H POR SEMANA', text: 'Você ainda cria posts sem um cérebro estratégico unificado?' },
      { slideNumber: 2, headline: '1. Dispersão de Dados', text: 'A informação da marca fica dividida em 10 abas e notas soltas.' },
      { slideNumber: 3, headline: '2. A Solução Definitiva', text: 'Um Sistema Operacional que consulta seu Brain permanente a cada clique.' }
    ],
    aiScore: 98,
    funnelStage: 'Topo de Funil',
    targetPersona: 'Social Medias e Gestores de Comunicação'
  });

  const handleGenerateMatrix = async () => {
    setIsGenerating(true);
    try {
      const res = await fetch('/api/ai/creative-matrix', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          gancho,
          angulo,
          emocao,
          dor,
          desejo,
          cta,
          estagioFunil,
          persona,
          platform,
          format,
          brainContext: brain,
          strategyContext: activeCampaign,
        }),
      });
      const data = await res.json();
      setMatrixResult(data);
    } catch (err) {
      console.error(err);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleSaveToPosts = () => {
    if (!onSavePost || !matrixResult) return;
    onSavePost({
      title: matrixResult.headline || 'Post Gerado via Matriz Criativa',
      copy: matrixResult.copy || '',
      platform: platform as any,
      format: format as any,
      slides: matrixResult.slides || [],
      hashtags: ['#MatrizCriativa', '#ClickoStudio', '#SocialMediaOS', '#EstrategiaIA'],
      status: 'pending_approval',
      aiScore: matrixResult.aiScore || 95,
      objective: `${estagioFunil} - ${persona}`,
      origin: 'brain',
    });
  };

  return (
    <div className="space-y-6">
      {/* Top Header Banner */}
      <div className="rounded-2xl border border-white/[0.08] bg-gradient-to-r from-[#182126] via-[#12191d] to-[#0d1316] p-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-[#8bd132]/30 bg-[#8bd132]/[0.08] px-3 py-1 text-[10px] font-bold text-[#8bd132]">
              <Target className="h-3.5 w-3.5" /> Engenharia Estratégica de Conteúdo
            </div>
            <h2 className="mt-2 text-xl font-bold text-white">Matriz Criativa de Alta Conversão</h2>
            <p className="mt-1 text-xs text-[#8f9a9f]">
              Combine Gancho, Ângulo, Emoção, Dor, Desejo e Funil para gerar peças certeiras validadas pela IA.
            </p>
          </div>
          <button
            onClick={handleGenerateMatrix}
            disabled={isGenerating}
            className="flex items-center gap-2 rounded-xl bg-[#8bd132] px-5 py-3 text-xs font-bold text-[#14200e] hover:bg-[#9be24d] transition shadow-lg shadow-[#8bd132]/20 disabled:opacity-50"
          >
            {isGenerating ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
            {isGenerating ? 'Processando Matriz...' : 'Gerar Conteúdo via Matriz'}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Matrix Inputs Column */}
        <div className="lg:col-span-5 space-y-4">
          <div className="rounded-2xl border border-white/[0.07] bg-[#182126] p-5 space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-white flex items-center gap-2 border-b border-white/[0.06] pb-3">
              <Sliders className="h-4 w-4 text-[#8bd132]" /> Parâmetros da Matriz
            </h3>

            {/* Gancho / Hook */}
            <div>
              <label className="block text-[10px] font-semibold text-[#aeb8bd] mb-1">
                Gancho (Hook)
              </label>
              <input
                value={gancho}
                onChange={(e) => setGancho(e.target.value)}
                placeholder="Ex: O maior erro do seu setor..."
                className="w-full rounded-xl border border-white/[0.08] bg-black/30 p-2.5 text-xs text-white outline-none focus:border-[#8bd132]/40"
              />
            </div>

            {/* Ângulo */}
            <div>
              <label className="block text-[10px] font-semibold text-[#aeb8bd] mb-1">
                Ângulo Estratégico
              </label>
              <input
                value={angulo}
                onChange={(e) => setAngulo(e.target.value)}
                placeholder="Ex: Contradição, Curiosidade, Estatística surpreendente..."
                className="w-full rounded-xl border border-white/[0.08] bg-black/30 p-2.5 text-xs text-white outline-none focus:border-[#8bd132]/40"
              />
            </div>

            {/* Emoção & Persona */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-[10px] font-semibold text-[#aeb8bd] mb-1">
                  Emoção Ativada
                </label>
                <input
                  value={emocao}
                  onChange={(e) => setEmocao(e.target.value)}
                  placeholder="Ex: Urgência, Confiança"
                  className="w-full rounded-xl border border-white/[0.08] bg-black/30 p-2.5 text-xs text-white outline-none focus:border-[#8bd132]/40"
                />
              </div>

              <div>
                <label className="block text-[10px] font-semibold text-[#aeb8bd] mb-1">
                  PersonaAlvo
                </label>
                <input
                  value={persona}
                  onChange={(e) => setPersona(e.target.value)}
                  placeholder="Ex: Social Media Pro"
                  className="w-full rounded-xl border border-white/[0.08] bg-black/30 p-2.5 text-xs text-white outline-none focus:border-[#8bd132]/40"
                />
              </div>
            </div>

            {/* Dor & Desejo */}
            <div>
              <label className="block text-[10px] font-semibold text-[#aeb8bd] mb-1">
                Dor Principal (Pain)
              </label>
              <textarea
                value={dor}
                onChange={(e) => setDor(e.target.value)}
                rows={2}
                placeholder="Ex: Perda de tempo criando tudo do zero..."
                className="w-full resize-none rounded-xl border border-white/[0.08] bg-black/30 p-2.5 text-xs text-white outline-none focus:border-[#8bd132]/40"
              />
            </div>

            <div>
              <label className="block text-[10px] font-semibold text-[#aeb8bd] mb-1">
                Desejo Alvo (Desire)
              </label>
              <textarea
                value={desejo}
                onChange={(e) => setDesejo(e.target.value)}
                rows={2}
                placeholder="Ex: Escalar a produção mantendo qualidade extrema..."
                className="w-full resize-none rounded-xl border border-white/[0.08] bg-black/30 p-2.5 text-xs text-white outline-none focus:border-[#8bd132]/40"
              />
            </div>

            {/* CTA & Funil */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-[10px] font-semibold text-[#aeb8bd] mb-1">
                  CTA
                </label>
                <input
                  value={cta}
                  onChange={(e) => setCta(e.target.value)}
                  placeholder="Ex: Comente 'SISTEMA'"
                  className="w-full rounded-xl border border-white/[0.08] bg-black/30 p-2.5 text-xs text-white outline-none focus:border-[#8bd132]/40"
                />
              </div>

              <div>
                <label className="block text-[10px] font-semibold text-[#aeb8bd] mb-1">
                  Estágio do Funil
                </label>
                <select
                  value={estagioFunil}
                  onChange={(e) => setEstagioFunil(e.target.value)}
                  className="w-full rounded-xl border border-white/[0.08] bg-black/30 p-2.5 text-xs text-white outline-none focus:border-[#8bd132]/40"
                >
                  <option value="Topo de Funil">Topo de Funil (Atração)</option>
                  <option value="Meio de Funil">Meio de Funil (Nutrição)</option>
                  <option value="Fundo de Funil">Fundo de Funil (Conversão)</option>
                </select>
              </div>
            </div>
          </div>
        </div>

        {/* Matrix AI Output Column */}
        <div className="lg:col-span-7 space-y-4">
          <div className="rounded-2xl border border-white/[0.07] bg-[#182126] p-6 space-y-5">
            <div className="flex items-center justify-between border-b border-white/[0.06] pb-3">
              <div className="flex items-center gap-2">
                <span className="grid h-8 w-8 place-items-center rounded-lg bg-[#8bd132]/10 text-[#8bd132]">
                  <Sparkles className="h-4 w-4" />
                </span>
                <div>
                  <h3 className="text-xs font-bold text-white">Resultado da Matriz Criativa</h3>
                  <p className="text-[10px] text-[#78848a]">Sintetizado com o Brain da sua marca</p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <span className="rounded-lg bg-[#8bd132]/10 px-2.5 py-1 text-[10px] font-bold text-[#8bd132]">
                  Score IA: {matrixResult.aiScore || 95}/100
                </span>
              </div>
            </div>

            {/* Headline */}
            <div className="rounded-xl border border-white/[0.06] bg-black/25 p-4">
              <span className="text-[9px] font-bold uppercase tracking-wider text-[#8bd132]">
                Headline Principal
              </span>
              <h4 className="mt-1 text-sm font-bold text-white">{matrixResult.headline}</h4>
            </div>

            {/* Copy Content */}
            <div className="rounded-xl border border-white/[0.06] bg-black/25 p-4 space-y-2">
              <span className="text-[9px] font-bold uppercase tracking-wider text-[#8bd132]">
                Legenda / Copy Desenvolvida
              </span>
              <p className="whitespace-pre-line text-xs leading-relaxed text-[#cdd4d7]">
                {matrixResult.copy}
              </p>
            </div>

            {/* Slide Breakdown if Carousel */}
            {matrixResult.slides && matrixResult.slides.length > 0 && (
              <div className="space-y-2">
                <span className="text-[9px] font-bold uppercase tracking-wider text-[#8bd132]">
                  Estrutura de Slides / Carrossel ({matrixResult.slides.length} lâminas)
                </span>
                <div className="grid gap-2 md:grid-cols-3">
                  {matrixResult.slides.map((slide: any) => (
                    <div
                      key={slide.slideNumber}
                      className="rounded-xl border border-white/[0.06] bg-black/30 p-3 space-y-1"
                    >
                      <span className="text-[9px] font-bold text-[#8bd132]">Slide {slide.slideNumber}</span>
                      <h5 className="text-[10px] font-bold text-white truncate">{slide.headline}</h5>
                      <p className="text-[9px] text-[#8e989d] line-clamp-2">{slide.text}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Action Bar */}
            <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-white/[0.06]">
              <button
                onClick={() => navigator.clipboard.writeText(matrixResult.copy)}
                className="flex items-center gap-1.5 rounded-lg border border-white/[0.08] bg-black/20 px-3 py-2 text-[10px] font-semibold text-[#aeb7bb] hover:text-white"
              >
                <Copy className="h-3.5 w-3.5" /> Copiar Copy
              </button>

              <button
                onClick={handleSaveToPosts}
                className="flex items-center gap-1.5 rounded-lg bg-[#8bd132] px-4 py-2 text-[10px] font-bold text-[#14200e] hover:bg-[#9be24d] transition shadow-md shadow-[#8bd132]/20"
              >
                <Send className="h-3.5 w-3.5" /> Enviar para Aprovações & Publicador
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
