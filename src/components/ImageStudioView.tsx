import React from 'react';
import {
  Image as ImageIcon,
  Sparkles,
  RefreshCw,
  Download,
  Wand2,
  Crop,
  Layers,
  Sliders,
  Type,
  Maximize2,
  Check,
  Zap,
  Heart,
  History,
  LayoutTemplate,
} from 'lucide-react';
import { useOperations } from '../context/OperationsContext';

export const ImageStudioView: React.FC = () => {
  const { brain, activeCampaign } = useOperations();
  const [prompt, setPrompt] = React.useState(
    'Minimalist dark mode 3D render of glowing violet neon crystal geometric shapes, high resolution, soft volumetric lighting, sleek social media cover banner'
  );
  const [aspectRatio, setAspectRatio] = React.useState<'1:1' | '16:9' | '9:16' | '4:5'>('16:9');
  const [stylePreset, setStylePreset] = React.useState('3D Render Neon');
  const [isGenerating, setIsGenerating] = React.useState(false);
  const [generatedImageUrl, setGeneratedImageUrl] = React.useState<string>(
    'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=1200&q=80'
  );
  const [overlayText, setOverlayText] = React.useState('LANÇAMENTO ENTERPRISE 2026');
  const [textColor, setTextColor] = React.useState('#FFFFFF');
  const [activeTool, setActiveTool] = React.useState<'generate' | 'text' | 'filters' | 'presets'>('generate');

  const presetsList = [
    { name: 'Capa de Carrossel Instagram', ratio: '1:1', promptAdd: 'square cover graphic' },
    { name: 'Miniatura do YouTube em alta definição', ratio: '16:9', promptAdd: 'high contrast youtube thumbnail with bold focus' },
    { name: 'Faixa para Reels e Histórias', ratio: '9:16', promptAdd: 'vertical full height smartphone visual' },
    { name: 'Faixa corporativa para LinkedIn', ratio: '16:9', promptAdd: 'clean corporate header banner B2B' },
  ];

  const handleGenerateImage = async () => {
    setIsGenerating(true);
    try {
      const res = await fetch('/api/ai/generate-image', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: `${prompt}, style: ${stylePreset}`,
          aspectRatio,
          brainContext: brain,
          strategyContext: activeCampaign,
        }),
      });

      const data = await res.json();
      if (data.imageUrl) {
        setGeneratedImageUrl(data.imageUrl);
      } else {
        // Fallback high quality visual placeholder for demo
        setGeneratedImageUrl(
          'https://images.unsplash.com/photo-1550745165-9bc0b252726f?auto=format&fit=crop&w=1200&q=80'
        );
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/5 pb-4">
        <div>
          <h2 className="text-lg font-bold text-[#ededed] flex items-center gap-2">
            <ImageIcon className="w-5 h-5 text-indigo-400" /> Estúdio de Geração e Edição de Imagens IA
          </h2>
          <p className="text-xs text-white/40">
            Crie thumbnails, banners, capas e mockups em alta definição sem precisar de softwares externos
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              const link = document.createElement('a');
              link.href = generatedImageUrl;
              link.download = 'clicko-ai-studios-asset.jpg';
              link.click();
            }}
            className="px-4 py-2 rounded-xl bg-white/[0.03] hover:bg-white/10 text-[#ededed] font-bold text-xs flex items-center gap-1.5 border border-white/5 shadow-sm"
          >
            <Download className="w-4 h-4" /> Exportar Imagem
          </button>
        </div>
      </div>

      {/* Main Studio Workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Controls Column */}
        <div className="space-y-5 bg-[#0A0A0A] border border-white/5 p-5 rounded-2xl flex flex-col justify-between">
          <div className="space-y-4">
            {/* Tool Tabs */}
            <div className="flex items-center p-1 rounded-xl bg-white/[0.03] border border-white/5">
              <button
                onClick={() => setActiveTool('generate')}
                className={`flex-1 py-1.5 text-[11px] font-bold rounded-lg ${
                  activeTool === 'generate' ? 'bg-indigo-600 text-white' : 'text-white/40'
                }`}
              >
                Gerar IA
              </button>
              <button
                onClick={() => setActiveTool('text')}
                className={`flex-1 py-1.5 text-[11px] font-bold rounded-lg ${
                  activeTool === 'text' ? 'bg-indigo-600 text-white' : 'text-white/40'
                }`}
              >
                Texto Layer
              </button>
              <button
                onClick={() => setActiveTool('presets')}
                className={`flex-1 py-1.5 text-[11px] font-bold rounded-lg ${
                  activeTool === 'presets' ? 'bg-indigo-600 text-white' : 'text-white/40'
                }`}
              >
                Modelos
              </button>
            </div>

            {activeTool === 'generate' && (
              <div className="space-y-4 text-xs">
                <div>
                  <label className="block text-neutral-300 font-semibold mb-1">Prompt da Imagem</label>
                  <textarea
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    rows={4}
                    className="w-full bg-white/[0.03] border border-white/5 rounded-xl p-3 text-[#ededed] focus:outline-none focus:border-indigo-500/50 text-xs resize-none"
                    placeholder="Descreva detalhadamente o elemento visual..."
                  />
                </div>

                <div>
                  <label className="block text-neutral-300 font-semibold mb-1">Proporção (Aspect Ratio)</label>
                  <div className="grid grid-cols-4 gap-2">
                    {[
                      { id: '1:1', label: '1:1 (Post)' },
                      { id: '16:9', label: '16:9 (Banner)' },
                      { id: '9:16', label: '9:16 (História)' },
                      { id: '4:5', label: '4:5 (Insta)' },
                    ].map((r) => (
                      <button
                        key={r.id}
                        type="button"
                        onClick={() => setAspectRatio(r.id as any)}
                        className={`p-2 rounded-xl text-[10px] font-bold border transition-all ${
                          aspectRatio === r.id
                            ? 'bg-indigo-600/30 text-indigo-300 border-indigo-500/40'
                            : 'bg-white/[0.03] text-white/40 border-white/5'
                        }`}
                      >
                        {r.label}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block text-neutral-300 font-semibold mb-1">Estilo Visual</label>
                  <select
                    value={stylePreset}
                    onChange={(e) => setStylePreset(e.target.value)}
                    className="w-full bg-[#050505] border border-white/5 rounded-xl p-2.5 text-[#ededed] focus:outline-none focus:border-indigo-500/50"
                  >
                    <option value="3D Render Neon">3D Render Neon Dark</option>
                    <option value="Fotorealista HD">Fotorealista Estúdio</option>
                    <option value="Flat Minimalista">Flat Minimalista Vercel</option>
                    <option value="Ilustração Vetorial">Ilustração Vetorial</option>
                    <option value="Vintage Cyberpunk">Vintage Cyberpunk</option>
                  </select>
                </div>

                {/* AI Editing Options */}
                <div className="pt-2 border-t border-white/5 space-y-2">
                  <span className="text-[10px] uppercase font-bold text-white/40">Edição Rápida por IA</span>
                  <div className="grid grid-cols-2 gap-2 text-[11px]">
                    <button
                      onClick={() => setPrompt((p) => `${p}, remove background isolate subject`)}
                      className="p-2 rounded-xl bg-white/[0.03] hover:bg-white/10 border border-white/5 text-neutral-300 text-left"
                    >
                      Remover Fundo
                    </button>
                    <button
                      onClick={() => setPrompt((p) => `${p}, upscale 4k crystal clear details`)}
                      className="p-2 rounded-xl bg-white/[0.03] hover:bg-white/10 border border-white/5 text-neutral-300 text-left"
                    >
                      Restaurar & Upscale
                    </button>
                  </div>
                </div>
              </div>
            )}

            {activeTool === 'text' && (
              <div className="space-y-4 text-xs">
                <div>
                  <label className="block text-neutral-300 font-semibold mb-1">Texto em Sobreposição</label>
                  <input
                    type="text"
                    value={overlayText}
                    onChange={(e) => setOverlayText(e.target.value)}
                    className="w-full bg-white/[0.03] border border-white/5 rounded-xl p-2.5 text-[#ededed] focus:outline-none focus:border-indigo-500/50"
                  />
                </div>

                <div>
                  <label className="block text-neutral-300 font-semibold mb-1">Cor do Texto</label>
                  <input
                    type="color"
                    value={textColor}
                    onChange={(e) => setTextColor(e.target.value)}
                    className="w-full h-10 bg-transparent cursor-pointer rounded-xl"
                  />
                </div>
              </div>
            )}

            {activeTool === 'presets' && (
              <div className="space-y-2">
                {presetsList.map((preset, i) => (
                  <div
                    key={i}
                    onClick={() => {
                      setAspectRatio(preset.ratio as any);
                      setPrompt((p) => `${p}, ${preset.promptAdd}`);
                    }}
                    className="p-3 rounded-xl bg-white/[0.03] hover:bg-white/10 border border-white/5 cursor-pointer transition-all"
                  >
                    <div className="text-xs font-bold text-[#ededed]">{preset.name}</div>
                    <div className="text-[10px] text-indigo-400 font-mono mt-0.5">{preset.ratio}</div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <button
            onClick={handleGenerateImage}
            disabled={isGenerating}
            className="w-full py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs shadow-xl shadow-indigo-600/20 border border-indigo-400/30 transition-all flex items-center justify-center gap-2"
          >
            {isGenerating ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" /> Renderizando com Gemini...
              </>
            ) : (
              <>
                <Wand2 className="w-4 h-4 text-amber-300" /> Renderizar Imagem em Alta
              </>
            )}
          </button>
        </div>

        {/* Live Canvas Column */}
        <div className="lg:col-span-2 bg-[#0A0A0A] border border-white/5 rounded-2xl p-6 flex flex-col items-center justify-center min-h-[500px] relative overflow-hidden">
          <div className="text-xs text-white/40 mb-3 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400"></span> Canvas de Pré-Visualização HD ({aspectRatio})
          </div>

          {/* Visual Image Stage */}
          <div
            className={`relative rounded-2xl overflow-hidden border border-white/10 shadow-2xl transition-all max-w-full max-h-[460px] flex items-center justify-center bg-black ${
              aspectRatio === '1:1'
                ? 'aspect-square w-96'
                : aspectRatio === '16:9'
                ? 'aspect-video w-full'
                : aspectRatio === '9:16'
                ? 'aspect-[9/16] h-[420px]'
                : 'aspect-[4/5] w-80'
            }`}
          >
            <img
              src={generatedImageUrl}
              alt="Generated Result"
              className="w-full h-full object-cover"
              referrerPolicy="no-referrer"
            />

            {/* Overlay Text Layer */}
            {overlayText && (
              <div className="absolute inset-0 flex items-center justify-center p-6 bg-gradient-to-t from-black/80 via-transparent to-black/30 pointer-events-none">
                <h2
                  style={{ color: textColor }}
                  className="text-xl md:text-2xl font-extrabold uppercase tracking-widest text-center shadow-2xl drop-shadow-[0_5px_5px_rgba(0,0,0,0.8)]"
                >
                  {overlayText}
                </h2>
              </div>
            )}
          </div>
        </div>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">{[[Maximize2, 'Expandir imagem', 'Amplie a área com preenchimento por IA'], [Heart, 'Favoritos', 'Salve referências e resultados preferidos'], [History, 'Histórico', 'Revise comandos, variações e versões'], [LayoutTemplate, 'Modelos e biblioteca', 'Reutilize estilos e identidades visuais']].map(([Icon, title, description]) => { const ItemIcon = Icon as React.ComponentType<{ className?: string }>; return <button key={String(title)} className="rounded-xl border border-white/[0.06] bg-[#182126] p-4 text-left hover:border-[#8bd132]/25"><ItemIcon className="h-4 w-4 text-[#8bd132]" /><h3 className="mt-3 text-[10px] font-semibold text-white">{String(title)}</h3><p className="mt-1 text-[8px] text-[#78848a]">{String(description)}</p></button>; })}</div>
    </div>
  );
};
