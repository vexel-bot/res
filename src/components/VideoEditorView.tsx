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
  LayoutTemplate,
  History,
} from 'lucide-react';

export const VideoEditorView: React.FC = () => {
  const [isPlaying, setIsPlaying] = React.useState(false);
  const [autoSubtitles, setAutoSubtitles] = React.useState(true);
  const [silenceCut, setSilenceCut] = React.useState(true);
  const [voiceName, setVoiceName] = React.useState('Kore (Feminino - PT-BR)');
  const [exportFormat, setExportFormat] = React.useState('9:16 Reels / TikTok');
  const [currentTime, setCurrentTime] = React.useState('00:04 / 00:30');
  const [creationMode, setCreationMode] = React.useState<'text' | 'image' | 'avatar'>('text');

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/5 pb-4">
        <div>
          <h2 className="text-lg font-bold text-[#ededed] flex items-center gap-2">
            <Video className="w-5 h-5 text-indigo-400" /> Editor de Vídeos Inteligente
          </h2>
          <p className="text-xs text-white/40">
            Cortes automáticos de silêncio, legendas dinâmicas em estilo neon e narração sintética
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsPlaying(!isPlaying)}
            className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs flex items-center gap-1.5 shadow-lg shadow-indigo-600/20"
          >
            {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
            <span>{isPlaying ? 'Pausar' : 'Reproduzir Preview'}</span>
          </button>
          <button className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs flex items-center gap-1.5 shadow-lg shadow-emerald-600/20">
            <Download className="w-4 h-4" /> Exportar Vídeo HD
          </button>
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        {[
          { id: 'text' as const, title: 'Texto para vídeo', description: 'Transforme roteiro em cenas, narração e legendas.', icon: Type },
          { id: 'image' as const, title: 'Imagem para vídeo', description: 'Anime imagens com movimento e transições de IA.', icon: ImageIcon },
          { id: 'avatar' as const, title: 'Avatar IA', description: 'Apresente conteúdos com avatar e voz sintética.', icon: UserRound },
        ].map(({ id, title, description, icon: Icon }) => <button key={id} onClick={() => setCreationMode(id)} className={`rounded-xl border p-4 text-left transition ${creationMode === id ? 'border-[#8bd132]/30 bg-[#8bd132]/[0.06]' : 'border-white/[0.06] bg-[#182126] hover:border-white/15'}`}><div className="flex items-center gap-3"><span className="grid h-9 w-9 place-items-center rounded-lg bg-black/25"><Icon className={`h-4 w-4 ${creationMode === id ? 'text-[#8bd132]' : 'text-[#9aa4a9]'}`} /></span><div><h3 className="text-[10px] font-semibold text-white">{title}</h3><p className="mt-1 text-[8px] text-[#78848a]">{description}</p></div></div></button>)}
      </div>

      {/* Editor Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Video Stage Player */}
        <div className="lg:col-span-2 bg-[#0A0A0A] border border-white/5 rounded-2xl p-6 flex flex-col items-center justify-center min-h-[420px] relative overflow-hidden">
          <div className="relative aspect-[9/16] h-[380px] bg-black rounded-2xl overflow-hidden border border-white/10 shadow-2xl flex items-center justify-center">
            {/* Mock video content */}
            <video
              src="https://assets.mixkit.co/videos/preview/mixkit-working-late-at-a-computer-43409-large.mp4"
              className="w-full h-full object-cover"
              loop
              autoPlay={isPlaying}
              muted
            />

            {/* Simulated Neon Subtitles Overlay */}
            {autoSubtitles && (
              <div className="absolute bottom-12 left-4 right-4 text-center pointer-events-none">
                <span className="inline-block bg-black/80 border border-indigo-500/50 backdrop-blur-md px-3 py-1.5 rounded-xl text-xs font-black text-amber-300 uppercase tracking-wide shadow-xl">
                  🔥 O MAIOR SEGREDO DA RETENÇÃO!
                </span>
              </div>
            )}
          </div>
        </div>

        {/* AI Video Enhancements Sidebar */}
        <div className="bg-[#0A0A0A] border border-white/5 p-5 rounded-2xl space-y-5 text-xs">
          <div className="border-b border-white/5 pb-3">
            <h3 className="font-bold text-[#ededed] flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-indigo-400" /> Automações de Edição
            </h3>
          </div>

          <div className="space-y-4">
            {/* Auto Subtitles Toggle */}
            <div className="flex items-center justify-between p-3 rounded-xl bg-white/[0.03] border border-white/5">
              <div className="flex items-center gap-2.5">
                <Subtitles className="w-4 h-4 text-indigo-400" />
                <div>
                  <div className="font-semibold text-[#ededed]">Legendas Automáticas IA</div>
                  <div className="text-[10px] text-white/40">Destaque dinâmico palavra por palavra</div>
                </div>
              </div>
              <input
                type="checkbox"
                checked={autoSubtitles}
                onChange={(e) => setAutoSubtitles(e.target.checked)}
                className="w-4 h-4 accent-indigo-600 rounded cursor-pointer"
              />
            </div>

            {/* Silence Cutter Toggle */}
            <div className="flex items-center justify-between p-3 rounded-xl bg-white/[0.03] border border-white/5">
              <div className="flex items-center gap-2.5">
                <Scissors className="w-4 h-4 text-amber-400" />
                <div>
                  <div className="font-semibold text-[#ededed]">Remover Silêncio Padrão</div>
                  <div className="text-[10px] text-white/40">Elimina pausas mortas para retenção</div>
                </div>
              </div>
              <input
                type="checkbox"
                checked={silenceCut}
                onChange={(e) => setSilenceCut(e.target.checked)}
                className="w-4 h-4 accent-indigo-600 rounded cursor-pointer"
              />
            </div>

            {/* Narration Voice Selector */}
            <div>
              <label className="block text-neutral-300 font-semibold mb-1 flex items-center gap-1.5">
                <Mic className="w-3.5 h-3.5 text-indigo-400" /> Voz de Narração Sintética
              </label>
              <select
                value={voiceName}
                onChange={(e) => setVoiceName(e.target.value)}
                className="w-full bg-[#050505] border border-white/5 rounded-xl p-2.5 text-[#ededed] focus:outline-none focus:border-indigo-500/50"
              >
                <option value="Kore (Feminino - PT-BR)">Kore (Feminino Claro - PT-BR)</option>
                <option value="Puck (Masculino - PT-BR)">Puck (Masculino Dinâmico - PT-BR)</option>
                <option value="Zephyr (Executivo - PT-BR)">Zephyr (Voz B2B Executiva)</option>
                <option value="Fenrir (Enérgico - PT-BR)">Fenrir (Enérgico para Reels)</option>
              </select>
            </div>

            {/* Preset Export Aspect Ratio */}
            <div>
              <label className="block text-neutral-300 font-semibold mb-1">Formato de Exportação</label>
              <select
                value={exportFormat}
                onChange={(e) => setExportFormat(e.target.value)}
                className="w-full bg-[#050505] border border-white/5 rounded-xl p-2.5 text-[#ededed] focus:outline-none focus:border-indigo-500/50"
              >
                <option value="9:16 Reels / TikTok">9:16 Vertical (Reels / TikTok / Shorts)</option>
                <option value="16:9 YouTube">16:9 Horizontal (YouTube / TV)</option>
                <option value="1:1 Quadrado">1:1 Quadrado (Feed Instagram / LinkedIn)</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Video Timeline View */}
      <div className="p-5 rounded-2xl bg-[#0A0A0A] border border-white/5 space-y-3">
        <div className="flex items-center justify-between text-xs text-white/40 border-b border-white/5 pb-2">
          <div className="flex items-center gap-2">
            <Film className="w-4 h-4 text-indigo-400" /> Linha do tempo com várias faixas
          </div>
          <span className="font-mono text-indigo-300">{currentTime}</span>
        </div>

        {/* Tracks */}
        <div className="space-y-2 text-[11px]">
          {/* Video Track */}
          <div className="flex items-center gap-3">
            <span className="w-20 text-white/40 font-semibold shrink-0">Vídeo/Trechos</span>
            <div className="flex-1 h-9 rounded-xl bg-indigo-600/30 border border-indigo-500/40 p-1 flex items-center gap-1 overflow-hidden">
              <div className="h-full bg-indigo-500/50 rounded px-2 flex items-center text-white font-bold text-[10px]">
                Clip_01.mp4 (12s)
              </div>
              <div className="h-full bg-indigo-500/30 rounded px-2 flex items-center text-white font-bold text-[10px]">
                Clip_02.mp4 (18s)
              </div>
            </div>
          </div>

          {/* Subtitles Track */}
          <div className="flex items-center gap-3">
            <span className="w-20 text-white/40 font-semibold shrink-0">Legendas IA</span>
            <div className="flex-1 h-7 rounded-xl bg-amber-500/20 border border-amber-500/30 p-1 flex items-center overflow-hidden">
              <span className="text-amber-300 font-mono text-[10px] truncate px-2">
                "O maior segredo da retenção nos primeiros 3 segundos..."
              </span>
            </div>
          </div>

          {/* Audio Track */}
          <div className="flex items-center gap-3">
            <span className="w-20 text-white/40 font-semibold shrink-0">Áudio/Trilha</span>
            <div className="flex-1 h-7 rounded-xl bg-emerald-500/20 border border-emerald-500/30 p-1 flex items-center overflow-hidden">
              <span className="text-emerald-300 font-mono text-[10px] truncate px-2">
                Trilha_LoFi_Fundo.mp3 (-14dB)
              </span>
            </div>
          </div>
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-3">{[[LayoutTemplate, 'Modelos de vídeo', 'Vídeos curtos, Reels, anúncios e apresentações'], [History, 'Histórico', '12 projetos e 28 exportações recentes'], [Music, 'Biblioteca de áudio', 'Músicas e trilhas licenciadas']].map(([Icon, title, description]) => { const ItemIcon = Icon as React.ComponentType<{ className?: string }>; return <button key={String(title)} className="rounded-xl border border-white/[0.06] bg-[#182126] p-4 text-left hover:border-[#8bd132]/25"><ItemIcon className="h-4 w-4 text-[#8bd132]" /><h3 className="mt-3 text-[10px] font-semibold text-white">{String(title)}</h3><p className="mt-1 text-[8px] text-[#78848a]">{String(description)}</p></button>; })}</div>
    </div>
  );
};
