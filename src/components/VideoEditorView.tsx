import React from 'react';
import {
  Video,
  Play,
  Pause,
  Scissors,
  Volume2,
  Mic,
  Subtitles,
  Layers,
  Sparkles,
  Download,
  Plus,
  RefreshCw,
  Film,
  Type,
  Music,
  Image as ImageIcon,
  UserRound,
  Zap,
  Globe,
  ZoomIn,
  Flame,
  LayoutTemplate
} from 'lucide-react';
import { useOperations } from '../context/OperationsContext';

export const VideoEditorView: React.FC = () => {
  const { brain } = useOperations();
  const [isPlaying, setIsPlaying] = React.useState(false);
  const [subtitleStyle, setSubtitleStyle] = React.useState<'Neon' | 'Karaoke' | 'Minimalist'>('Neon');
  const [silenceCut, setSilenceCut] = React.useState(true);
  const [voiceName, setVoiceName] = React.useState('Kore (Feminino - PT-BR)');
  const [exportFormat, setExportFormat] = React.useState('9:16 Reels / Shorts');
  const [activeAction, setActiveAction] = React.useState<string | null>(null);
  const [statusMessage, setStatusMessage] = React.useState<string | null>(null);

  const [videoUrl, setVideoUrl] = React.useState(
    'https://assets.mixkit.co/videos/preview/mixkit-working-late-at-a-computer-43409-large.mp4'
  );

  const videoAIFeatures = [
    { id: 'smart_cuts', label: 'Cortes Inteligentes', icon: Scissors, desc: 'Detecta gagueiras, pausas e corta trechos redundantes' },
    { id: 'auto_subtitles', label: 'Legendas Animadas', icon: Subtitles, desc: 'Legendas estilo Karaokê com destaques em amarelo/neon' },
    { id: 'translation', label: 'Tradução & Dublagem', icon: Globe, desc: 'Dubla o áudio para Inglês, Espanhol ou Francês mantendo o tom' },
    { id: 'silence_cut', label: 'Remoção de Silêncio', icon: Volume2, desc: 'Elimina trechos sem fala instantaneamente' },
    { id: 'auto_zoom', label: 'Zoom Dinâmico', icon: ZoomIn, desc: 'Aplica zooms automáticos nos momentos de ênfase' },
    { id: 'hooks_ai', label: 'Gerador de Hooks', icon: Flame, desc: 'Cria vinhetas iniciais com chamadas de retenção' },
    { id: 'broll', label: 'B-Roll Inteligente', icon: Film, desc: 'Insere imagens e vídeos de apoio contextuais' },
    { id: 'shorts_gen', label: 'Gerar Shorts & Reels', icon: Sparkles, desc: 'Converte vídeos longos em 3 cortes curtos virais' },
  ];

  const handleExecuteVideoAction = async (id: string, label: string) => {
    setActiveAction(id);
    setStatusMessage(`Processando vídeo com IA: "${label}"...`);
    try {
      const res = await fetch('/api/ai/video-edit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: id,
          videoUrl,
          subtitleStyle,
          brainContext: brain,
        }),
      });
      const data = await res.json();
      setStatusMessage(data.message || `Ação "${label}" executada com sucesso!`);
    } catch (err) {
      console.error(err);
    } finally {
      setActiveAction(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/[0.06] pb-4">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <Video className="w-5 h-5 text-[#8bd132]" /> Central de Edição de Vídeos & Reels com IA
          </h2>
          <p className="text-xs text-[#78858e]">
            Cortes inteligentes, legendas dinâmicas, dublagem, remoção de silêncio e geração de Shorts
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsPlaying(!isPlaying)}
            className="px-4 py-2 rounded-xl bg-[#0d1216] border border-white/[0.08] hover:bg-white/[0.06] text-white font-bold text-xs flex items-center gap-1.5 transition-all shadow-sm"
          >
            {isPlaying ? <Pause className="w-4 h-4 text-[#8bd132]" /> : <Play className="w-4 h-4 text-[#8bd132]" />}
            <span>{isPlaying ? 'Pausar Video' : 'Reproduzir Preview'}</span>
          </button>

          <button
            onClick={() => alert('Exportando vídeo em alta definição com legendas e cortes de IA...')}
            className="px-4 py-2 rounded-xl bg-[#8bd132] hover:bg-[#9be24d] text-[#0b1208] font-bold text-xs flex items-center gap-1.5 transition-all shadow-md shadow-[#8bd132]/20"
          >
            <Download className="w-4 h-4" /> Exportar Vídeo HD (Reels/TikTok)
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        {/* Main Player Stage */}
        <div className="relative flex min-h-[440px] flex-col items-center justify-center rounded-xl border border-white/[0.07] bg-[#101316] p-5 lg:col-span-7">
          <div className="relative aspect-[9/16] h-[380px] bg-black rounded-2xl overflow-hidden border border-white/10 shadow-2xl flex items-center justify-center">
            <video
              src={videoUrl}
              className="w-full h-full object-cover"
              loop
              autoPlay={isPlaying}
              muted
            />

            {/* Simulated Dynamic Subtitles Overlay */}
            <div className="absolute bottom-10 left-4 right-4 text-center pointer-events-none">
              <span className="inline-block bg-black/85 border border-[#8bd132]/50 backdrop-blur-md px-3.5 py-2 rounded-xl text-xs font-black text-[#8bd132] uppercase tracking-wide shadow-2xl">
                O SEGREDO DA RETENÇÃO EM 2026!
              </span>
            </div>
          </div>
        </div>

        {/* AI Features Sidebar */}
        <div className="space-y-4 rounded-xl border border-white/[0.07] bg-[#101316] p-5 lg:col-span-5">
          <div className="border-b border-white/[0.06] pb-3 flex items-center justify-between">
            <h3 className="font-bold text-white text-xs flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-[#8bd132]" /> Recursos de Vídeo por IA
            </h3>

            <div className="flex gap-1">
              {['Neon', 'Karaoke', 'Minimalist'].map((style) => (
                <button
                  key={style}
                  onClick={() => setSubtitleStyle(style as any)}
                  className={`px-2 py-1 text-[8px] font-bold rounded ${
                    subtitleStyle === style
                      ? 'bg-[#8bd132] text-[#14200e]'
                      : 'bg-black/20 text-[#8e989d]'
                  }`}
                >
                  {style}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 gap-2 max-h-[380px] overflow-y-auto pr-1">
            {videoAIFeatures.map(({ id, label, icon: Icon, desc }) => (
              <button
                key={id}
                onClick={() => handleExecuteVideoAction(id, label)}
                disabled={activeAction === id}
                className="flex items-center justify-between p-3 rounded-xl border border-white/[0.07] bg-black/20 hover:border-[#8bd132]/40 hover:bg-[#8bd132]/[0.05] transition text-left group"
              >
                <div className="flex items-center gap-3">
                  <span className="grid h-8 w-8 place-items-center rounded-lg bg-[#8bd132]/10 text-[#8bd132] shrink-0">
                    <Icon className="h-4 w-4" />
                  </span>
                  <div>
                    <h4 className="text-[11px] font-bold text-white">{label}</h4>
                    <p className="text-[9px] text-[#78848a] line-clamp-1">{desc}</p>
                  </div>
                </div>

                <span className="text-[9px] font-bold text-[#8bd132] opacity-0 group-hover:opacity-100 transition-opacity">
                  Executar
                </span>
              </button>
            ))}
          </div>

          {statusMessage && (
            <div className="rounded-xl border border-[#8bd132]/20 bg-[#8bd132]/[0.06] p-3 text-[10px] font-semibold text-[#8bd132] flex items-center gap-2">
              <Sparkles className="h-3.5 w-3.5 shrink-0" />
              <span>{statusMessage}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
