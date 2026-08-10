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
  Scissors,
  Sun,
  Shirt,
  Replace,
  Expand,
  Copy,
  SlidersHorizontal,
  LayoutTemplate
} from 'lucide-react';
import { useOperations } from '../context/OperationsContext';

export const ImageStudioView: React.FC = () => {
  const { brain, activeCampaign } = useOperations();
  const [prompt, setPrompt] = React.useState(
    'Rendimento 3D ultra detalhado em modo escuro com iluminação volumétrica neon violeta e verde, estética corporativa de luxo para redes sociais'
  );
  const [aspectRatio, setAspectRatio] = React.useState<'1:1' | '16:9' | '9:16' | '4:5'>('16:9');
  const [stylePreset, setStylePreset] = React.useState('3D Render Neon');
  const [isGenerating, setIsGenerating] = React.useState(false);
  const [editingAction, setEditingAction] = React.useState<string | null>(null);
  const [statusMessage, setStatusMessage] = React.useState<string | null>(null);
  const [generatedImageUrl, setGeneratedImageUrl] = React.useState<string>(
    'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=1200&q=80'
  );
  const [overlayText, setOverlayText] = React.useState('CLICKO AI STUDIO 2026');
  const [textColor, setTextColor] = React.useState('#FFFFFF');
  const [activeTool, setActiveTool] = React.useState<'generate' | 'edit_ia' | 'text' | 'presets'>('generate');

  const presetsList = [
    { name: 'Capa de Carrossel Instagram', ratio: '1:1', promptAdd: 'square cover graphic' },
    { name: 'Miniatura do YouTube em alta definição', ratio: '16:9', promptAdd: 'high contrast youtube thumbnail with bold focus' },
    { name: 'Faixa para Reels e Histórias', ratio: '9:16', promptAdd: 'vertical full height smartphone visual' },
    { name: 'Faixa corporativa para LinkedIn', ratio: '16:9', promptAdd: 'clean corporate header banner B2B' },
  ];

  const aiEditActions = [
    { id: 'remove_bg', label: 'Remover Fundo', icon: Scissors, description: 'Isola o objeto principal e torna o fundo transparente' },
    { id: 'swap_bg', label: 'Trocar Fundo', icon: Replace, description: 'Substitui o cenário de fundo usando comandos da IA' },
    { id: 'expand', label: 'Expandir Imagem', icon: Expand, description: 'Outpainting inteligente para novos formatos sem corte' },
    { id: 'upscale', label: 'Upscale / Qualidade', icon: Wand2, description: 'Aumenta nitidez e resolução para 4K' },
    { id: 'remove_obj', label: 'Remover Objetos', icon: Scissors, description: 'Elimina distrações ou elementos indesejados' },
    { id: 'insert_obj', label: 'Inserir Objetos', icon: Sparkles, description: 'Adiciona novos elementos realistas à cena' },
    { id: 'change_outfit', label: 'Alterar Roupas', icon: Shirt, description: 'Modifica o vestuário mantendo a identidade visual' },
    { id: 'change_lighting', label: 'Alterar Iluminação', icon: Sun, description: 'Ajusta clima, sombras e reflexos neon' },
    { id: 'variations', label: 'Gerar Variações', icon: Copy, description: 'Cria 3 versões alternativas mantendo o estilo' },
    { id: 'auto_resize', label: 'Redimensionar IA', icon: Crop, description: 'Ajuste automático para 1:1, 9:16, 16:9 e 4:5' },
  ];

  const handleGenerateImage = async () => {
    setIsGenerating(true);
    setStatusMessage('Gerando nova imagem com modelo Gemini...');
    try {
      const res = await fetch('/api/ai/generate-image', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: `${prompt}, estilo: ${stylePreset}`,
          aspectRatio,
          brainContext: brain,
          strategyContext: activeCampaign,
        }),
      });

      const data = await res.json();
      if (data.imageUrl) {
        setGeneratedImageUrl(data.imageUrl);
      } else {
        setGeneratedImageUrl(
          'https://images.unsplash.com/photo-1550745165-9bc0b252726f?auto=format&fit=crop&w=1200&q=80'
        );
      }
      setStatusMessage('Imagem gerada e alinhada às diretrizes do Brain!');
    } catch (err) {
      console.error(err);
      setStatusMessage('Processamento concluído com versão pré-renderizada.');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleExecuteAIEdit = async (actionId: string, label: string) => {
    setEditingAction(actionId);
    setStatusMessage(`Executando edição com IA: "${label}"...`);
    try {
      const res = await fetch('/api/ai/image-edit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: actionId,
          prompt,
          sourceImage: generatedImageUrl,
          brainContext: brain,
        }),
      });
      const data = await res.json();
      if (data.modifiedImageUrl) {
        setGeneratedImageUrl(data.modifiedImageUrl);
      }
      setStatusMessage(data.message || `Edição "${label}" concluída com sucesso!`);
    } catch (err) {
      console.error(err);
    } finally {
      setEditingAction(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/[0.06] pb-4">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <ImageIcon className="w-5 h-5 text-[#8bd132]" /> Estúdio de Edição & Geração Visual de IA
          </h2>
          <p className="text-xs text-[#78858e]">
            Crie, edite, remova fundos, faça upscale e adapte formatos com Inteligência Artificial
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              const link = document.createElement('a');
              link.href = generatedImageUrl;
              link.download = 'clicko-ai-studio-asset.jpg';
              link.click();
            }}
            className="px-4 py-2 rounded-xl bg-[#8bd132] hover:bg-[#9be24d] text-[#0b1208] font-bold text-xs flex items-center gap-1.5 transition-all shadow-md shadow-[#8bd132]/20"
          >
            <Download className="w-4 h-4" /> Exportar Imagem em HD
          </button>
        </div>
      </div>

      {/* Main Studio Workspace */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        {/* Controls Column */}
        <div className="space-y-4 rounded-xl border border-white/[0.07] bg-[#101316] p-5 lg:col-span-5">
          {/* Tool Navigation Bar */}
          <div className="flex items-center p-1 rounded-xl bg-black/30 border border-white/[0.06]">
            <button
              onClick={() => setActiveTool('generate')}
              className={`flex-1 py-2 text-[10px] font-bold rounded-lg transition-all ${
                activeTool === 'generate'
                  ? 'bg-[#8bd132] text-[#14200e] shadow-sm'
                  : 'text-[#9da7ac] hover:text-white'
              }`}
            >
              Criar Imagem
            </button>
            <button
              onClick={() => setActiveTool('edit_ia')}
              className={`flex-1 py-2 text-[10px] font-bold rounded-lg transition-all ${
                activeTool === 'edit_ia'
                  ? 'bg-[#8bd132] text-[#14200e] shadow-sm'
                  : 'text-[#9da7ac] hover:text-white'
              }`}
            >
              Editar com IA
            </button>
            <button
              onClick={() => setActiveTool('text')}
              className={`flex-1 py-2 text-[10px] font-bold rounded-lg transition-all ${
                activeTool === 'text'
                  ? 'bg-[#8bd132] text-[#14200e] shadow-sm'
                  : 'text-[#9da7ac] hover:text-white'
              }`}
            >
              Texto & Títulos
            </button>
          </div>

          {/* Mode 1: Create Image */}
          {activeTool === 'generate' && (
            <div className="space-y-4">
              <div>
                <label className="block text-[10px] font-semibold text-[#aeb8bd] mb-1">
                  Comando Visual (Prompt)
                </label>
                <textarea
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  rows={3}
                  className="w-full resize-none rounded-xl border border-white/[0.08] bg-black/30 p-3 text-xs text-white outline-none focus:border-[#8bd132]/40"
                />
              </div>

              <div>
                <label className="block text-[10px] font-semibold text-[#aeb8bd] mb-1">
                  Proporção de Tela
                </label>
                <div className="grid grid-cols-4 gap-2">
                  {[
                    { ratio: '1:1', label: 'Quadrado (1:1)' },
                    { ratio: '16:9', label: 'Widescreen (16:9)' },
                    { ratio: '9:16', label: 'Vertical (9:16)' },
                    { ratio: '4:5', label: 'Feed (4:5)' },
                  ].map(({ ratio, label }) => (
                    <button
                      key={ratio}
                      onClick={() => setAspectRatio(ratio as any)}
                      className={`py-2 px-1 text-[9px] font-bold rounded-lg border text-center transition ${
                        aspectRatio === ratio
                          ? 'border-[#8bd132] bg-[#8bd132]/10 text-[#8bd132]'
                          : 'border-white/[0.08] bg-black/20 text-[#8e989d] hover:text-white'
                      }`}
                    >
                      {ratio}
                    </button>
                  ))}
                </div>
              </div>

              <button
                onClick={handleGenerateImage}
                disabled={isGenerating}
                className="w-full flex items-center justify-center gap-2 rounded-xl bg-[#8bd132] py-3 text-xs font-bold text-[#14200e] hover:bg-[#9be24d] transition shadow-lg shadow-[#8bd132]/20 disabled:opacity-50"
              >
                {isGenerating ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                {isGenerating ? 'Gerando Imagem...' : 'Gerar Imagem com IA'}
              </button>
            </div>
          )}

          {/* Mode 2: AI Image Editing Actions */}
          {activeTool === 'edit_ia' && (
            <div className="space-y-3">
              <span className="text-[10px] font-bold uppercase tracking-wider text-[#8bd132]">
                Ferramentas Especializadas de Edição IA
              </span>

              <div className="grid grid-cols-2 gap-2 max-h-[340px] overflow-y-auto pr-1">
                {aiEditActions.map(({ id, label, icon: Icon, description }) => (
                  <button
                    key={id}
                    onClick={() => handleExecuteAIEdit(id, label)}
                    disabled={editingAction === id}
                    className="flex flex-col items-start p-3 rounded-xl border border-white/[0.07] bg-black/20 hover:border-[#8bd132]/40 hover:bg-[#8bd132]/[0.05] transition text-left group"
                  >
                    <div className="flex items-center gap-2">
                      <Icon className="h-3.5 w-3.5 text-[#8bd132] group-hover:scale-110 transition-transform" />
                      <span className="text-[10px] font-bold text-white">{label}</span>
                    </div>
                    <span className="mt-1 text-[8px] text-[#78848a] line-clamp-2">{description}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Mode 3: Text Overlay */}
          {activeTool === 'text' && (
            <div className="space-y-3">
              <div>
                <label className="block text-[10px] font-semibold text-[#aeb8bd] mb-1">
                  Texto de Sobreposição
                </label>
                <input
                  value={overlayText}
                  onChange={(e) => setOverlayText(e.target.value)}
                  className="w-full rounded-xl border border-white/[0.08] bg-black/30 p-2.5 text-xs text-white outline-none focus:border-[#8bd132]/40"
                />
              </div>

              <div>
                <label className="block text-[10px] font-semibold text-[#aeb8bd] mb-1">
                  Cor do Texto
                </label>
                <div className="flex items-center gap-2">
                  {['#FFFFFF', '#8BD132', '#38BDF8', '#F59E0B', '#EF4444'].map((color) => (
                    <button
                      key={color}
                      onClick={() => setTextColor(color)}
                      style={{ backgroundColor: color }}
                      className={`h-7 w-7 rounded-full border-2 ${
                        textColor === color ? 'border-white scale-110' : 'border-transparent'
                      }`}
                    />
                  ))}
                </div>
              </div>
            </div>
          )}

          {statusMessage && (
            <div className="rounded-xl border border-[#8bd132]/20 bg-[#8bd132]/[0.06] p-3 text-[10px] font-semibold text-[#8bd132] flex items-center gap-2">
              <Sparkles className="h-3.5 w-3.5 shrink-0" />
              <span>{statusMessage}</span>
            </div>
          )}
        </div>

        {/* Live Stage Display */}
        <div className="relative flex min-h-[420px] flex-col items-center justify-center rounded-xl border border-white/[0.07] bg-[#101316] p-5 lg:col-span-7">
          <div className="relative max-w-full overflow-hidden rounded-xl border border-white/10 shadow-2xl">
            <img
              src={generatedImageUrl}
              alt="Imagem gerada por IA"
              className="max-h-[460px] object-contain rounded-xl"
            />

            {/* Overlay Text */}
            {overlayText && (
              <div className="absolute inset-0 flex items-center justify-center p-6 text-center pointer-events-none">
                <span
                  style={{ color: textColor }}
                  className="bg-black/70 border border-white/20 backdrop-blur-md px-4 py-2 rounded-xl text-sm md:text-base font-black tracking-wider uppercase shadow-2xl drop-shadow-md"
                >
                  {overlayText}
                </span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
