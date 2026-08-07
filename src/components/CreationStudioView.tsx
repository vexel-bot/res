import React from 'react';
import {
  PenTool,
  Sparkles,
  Layers,
  Send,
  Calendar,
  CheckCircle2,
  Copy,
  Plus,
  Trash2,
  Sliders,
  Eye,
  Heart,
  MessageCircle,
  Bookmark,
  Share2,
  RefreshCw,
  Image as ImageIcon,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { PostFormat, SocialPlatform, Post, CarouselSlide } from '../types';
import { useOperations } from '../context/OperationsContext';
import { useGovernance } from '../context/GovernanceContext';

interface CreationStudioViewProps {
  onSavePost: (newPost: Partial<Post>) => void;
}

export const CreationStudioView: React.FC<CreationStudioViewProps> = ({
  onSavePost,
}) => {
  const { brain, activeCampaign } = useOperations();
  const { environmentMode, currentUser } = useGovernance();
  const isPersonal = environmentMode === 'personal';
  const isCollaborator = currentUser?.role === 'collaborator';
  const [copyTool, setCopyTool] = React.useState('Publicações');
  const [selectedFormat, setSelectedFormat] = React.useState<PostFormat>('carousel');
  const [selectedPlatform, setSelectedPlatform] = React.useState<SocialPlatform>('instagram');
  const [postTitle, setPostTitle] = React.useState('5 Pilares do Crescimento Digital');
  const [topicPrompt, setTopicPrompt] = React.useState('A importância de usar automação com IA nas mídias sociais');
  const [tone, setTone] = React.useState('Profissional, inovador e persuasivo');
  const [targetAudience, setTargetAudience] = React.useState('Líderes de marketing e empreendedores');
  const [copyText, setCopyText] = React.useState(
    'A automação inteligente não substitui a criatividade humana — ela impulsiona.\n\nQuando você centraliza o planejamento, criação e agendamento em uma única plataforma, sua equipe economiza até 15h semanais.\n\nQual o seu maior desafio ao criar conteúdo hoje?'
  );
  const [hashtags, setHashtags] = React.useState<string[]>([
    '#MarketingDigital',
    '#IA',
    '#Produtividade',
    '#SaaS',
  ]);
  const [slides, setSlides] = React.useState<CarouselSlide[]>([
    {
      slideNumber: 1,
      headline: '5 Pilares do Crescimento Digital em 2026',
      text: 'Como equipes de alto desempenho economizam tempo e multiplicam alcance.',
    },
    {
      slideNumber: 2,
      headline: '1. Centralização Unificada',
      text: 'Elimine a dispersão entre 10 abas diferentes.',
    },
    {
      slideNumber: 3,
      headline: '2. Tom de Voz Consistente',
      text: 'Treine a IA com as diretrizes e público exatos da sua marca.',
    },
  ]);
  const [activeSlideIndex, setActiveSlideIndex] = React.useState(0);
  const [isGenerating, setIsGenerating] = React.useState(false);
  const [previewImageUrl, setPreviewImageUrl] = React.useState(
    'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=800&q=80'
  );

  const formatsList: { id: PostFormat; label: string; platformDefault: SocialPlatform }[] = [
    { id: 'carousel', label: 'Carrossel', platformDefault: 'instagram' },
    { id: 'reels', label: 'Reels / TikTok', platformDefault: 'instagram' },
    { id: 'post', label: 'Publicação estática', platformDefault: 'instagram' },
    { id: 'story', label: 'Histórias', platformDefault: 'instagram' },
    { id: 'linkedin-article', label: 'Artigo LinkedIn', platformDefault: 'linkedin' },
    { id: 'youtube-short', label: 'YouTube Shorts', platformDefault: 'youtube' },
    { id: 'thread', label: 'Sequência / X', platformDefault: 'x' },
    { id: 'newsletter', label: 'Boletim informativo', platformDefault: 'linkedin' },
    { id: 'vsl', label: 'Roteiro VSL / Anúncio', platformDefault: 'youtube' },
  ];

  const handleGenerateAICopy = async () => {
    setIsGenerating(true);
    try {
      const res = await fetch('/api/ai/generate-copy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          platform: selectedPlatform,
          format: selectedFormat,
          topic: topicPrompt,
          tone,
          targetAudience,
          brainContext: brain,
          strategyContext: activeCampaign,
        }),
      });

      const data = await res.json();
      if (data.copy) setCopyText(data.copy);
      if (data.hashtags) setHashtags(data.hashtags);
      if (data.slides && data.slides.length > 0) setSlides(data.slides);
    } catch (err) {
      console.error(err);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleAddSlide = () => {
    const nextNum = slides.length + 1;
    setSlides([
      ...slides,
      {
        slideNumber: nextNum,
        headline: `Novo Slide ${nextNum}`,
        text: 'Insira o texto complementar aqui...',
      },
    ]);
    setActiveSlideIndex(slides.length);
  };

  const handleRemoveSlide = (index: number) => {
    if (slides.length <= 1) return;
    const newSlides = slides.filter((_, i) => i !== index);
    setSlides(newSlides);
    setActiveSlideIndex(Math.max(0, index - 1));
  };

  const handleSaveDraft = (status: Post['status']) => {
    onSavePost({
      title: postTitle,
      platform: selectedPlatform,
      format: selectedFormat,
      copy: copyText,
      hashtags,
      slides: selectedFormat === 'carousel' ? slides : undefined,
      imageUrl: previewImageUrl,
      status,
      scheduledAt: new Date(Date.now() + 86400000).toISOString(),
      author: currentUser?.name || (isPersonal ? 'Criador Solo' : 'Estúdio de Criação'),
      aiScore: 94,
    });
  };

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header & Format Selector Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/[0.06] pb-5">
        <div>
          <div className="flex items-center gap-2">
            <PenTool className="w-5 h-5 text-[#8bd132]" />
            <h2 className="text-xl font-bold tracking-tight text-white">
              {isPersonal ? 'Estúdio de Criação Pessoal' : 'Estúdio de Criação Universal'}
            </h2>
          </div>
          <p className="text-xs text-[#78848c] mt-0.5">
            {isPersonal
              ? 'Crie e publique diretamente sem necessidade de aprovação ou revisão'
              : 'Crie conteúdos com governança corporativa e fluxo de aprovação'}
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            type="button"
            onClick={() => handleSaveDraft('draft')}
            className="px-4 py-2 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] text-white font-semibold text-xs border border-white/10 transition"
          >
            Salvar Rascunho
          </button>

          {isPersonal ? (
            <>
              <button
                type="button"
                onClick={() => handleSaveDraft('published')}
                className="px-4 py-2 rounded-xl bg-[#8bd132] hover:bg-[#9be24d] text-[#080e05] font-bold text-xs shadow-lg shadow-[#8bd132]/20 transition"
              >
                Publicar Imediatamente
              </button>
              <button
                type="button"
                onClick={() => handleSaveDraft('scheduled')}
                className="px-4 py-2 rounded-xl bg-white/10 hover:bg-white/20 text-white font-semibold text-xs border border-white/10 transition"
              >
                Agendar Publicação
              </button>
            </>
          ) : isCollaborator ? (
            <button
              type="button"
              onClick={() => handleSaveDraft('pending_approval')}
              className="px-4 py-2 rounded-xl bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 font-bold text-xs border border-amber-500/30 transition shadow-lg shadow-amber-500/10"
            >
              Enviar para Aprovação
            </button>
          ) : (
            <>
              <button
                type="button"
                onClick={() => handleSaveDraft('published')}
                className="px-4 py-2 rounded-xl bg-[#8bd132] hover:bg-[#9be24d] text-[#080e05] font-bold text-xs shadow-lg shadow-[#8bd132]/20 transition"
              >
                Publicar Imediatamente
              </button>
              <button
                type="button"
                onClick={() => handleSaveDraft('scheduled')}
                className="px-4 py-2 rounded-xl bg-indigo-600/30 hover:bg-indigo-600/40 text-indigo-200 font-semibold text-xs border border-indigo-500/30 transition"
              >
                Aprovar & Agendar
              </button>
            </>
          )}
        </div>
      </div>

      <div className="rounded-xl border border-white/[0.06] bg-[#182126] p-3"><div className="mb-2 flex items-center justify-between"><span className="text-[9px] font-semibold uppercase tracking-[0.14em] text-[#7f8a90]">Ferramentas de texto</span><span className="text-[8px] text-[#8bd132]">Biblioteca de comandos conectada</span></div><div className="flex gap-2 overflow-x-auto custom-scrollbar">{['Publicações', 'Legendas', 'Texto de vendas', 'E-mail', 'Artigo', 'Página de captura', 'SEO', 'Chamada para ação', 'Marcadores', 'Roteiros', 'Tradução', 'Correção', 'Reescrita'].map((tool) => <button key={tool} onClick={() => { setCopyTool(tool); setTopicPrompt(`${tool}: ${topicPrompt.replace(/^[^:]+:\s*/, '')}`); }} className={`shrink-0 rounded-lg px-3 py-2 text-[8px] ${copyTool === tool ? 'bg-[#8bd132] font-bold text-[#14200e]' : 'border border-white/[0.06] bg-black/20 text-[#9ba5aa]'}`}>{tool}</button>)}</div></div>

      {/* Format Tabs Bar */}
      <div className="flex items-center gap-2 overflow-x-auto pb-2 custom-scrollbar">
        {formatsList.map((f) => (
          <button
            key={f.id}
            onClick={() => {
              setSelectedFormat(f.id);
              setSelectedPlatform(f.platformDefault);
            }}
            className={`px-3.5 py-2 rounded-xl text-xs font-semibold shrink-0 transition-all ${
              selectedFormat === f.id
                ? 'bg-[#8bd132] text-[#0e170a] font-bold shadow-md shadow-[#8bd132]/20 border border-[#8bd132]'
                : 'bg-[#0d1216] text-[#8e989e] hover:text-white border border-white/[0.06]'
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Studio Workspace Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Col: Content Inputs & AI Copywriter */}
        <div className="space-y-5 bg-[#0a0e11] border border-white/[0.06] p-5 rounded-2xl shadow-xl shadow-black/40">
          <div className="flex items-center justify-between border-b border-white/[0.06] pb-3">
            <span className="text-xs font-bold text-white flex items-center gap-1.5">
              <Sparkles className="w-4 h-4 text-[#8bd132]" /> Redação com IA e parâmetros
            </span>
            <button
              onClick={handleGenerateAICopy}
              disabled={isGenerating}
              className="px-3.5 py-1.5 rounded-lg bg-[#8bd132] hover:bg-[#9be24d] disabled:opacity-50 text-[#0b1208] text-xs font-bold flex items-center gap-1.5 shadow-md shadow-[#8bd132]/20 transition-all"
            >
              {isGenerating ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" /> Escrevendo...
                </>
              ) : (
                <>
                  <Sparkles className="w-3.5 h-3.5" /> Escrever com IA
                </>
              )}
            </button>
          </div>

          <div className="space-y-4 text-xs">
            <div>
              <label className="block text-xs font-semibold text-white mb-1.5">Título Interno do Projeto</label>
              <input
                type="text"
                value={postTitle}
                onChange={(e) => setPostTitle(e.target.value)}
                className="w-full bg-[#070a0d] border border-white/[0.08] rounded-xl px-3.5 py-2.5 text-xs text-white focus:outline-none focus:border-[#8bd132] focus:ring-1 focus:ring-[#8bd132] transition"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-white mb-1.5">Tópico ou Ideia do Conteúdo</label>
              <textarea
                value={topicPrompt}
                onChange={(e) => setTopicPrompt(e.target.value)}
                rows={2}
                className="w-full bg-[#070a0d] border border-white/[0.08] rounded-xl p-3 text-xs text-white focus:outline-none focus:border-[#8bd132] focus:ring-1 focus:ring-[#8bd132] resize-none transition"
                placeholder="Descreva o objetivo do conteúdo..."
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-white mb-1.5">Tom de Voz</label>
                <input
                  type="text"
                  value={tone}
                  onChange={(e) => setTone(e.target.value)}
                  className="w-full bg-[#070a0d] border border-white/[0.08] rounded-xl px-3 py-2.5 text-xs text-white focus:outline-none focus:border-[#8bd132] transition"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-white mb-1.5">Plataforma Alvo</label>
                <select
                  value={selectedPlatform}
                  onChange={(e) => setSelectedPlatform(e.target.value as SocialPlatform)}
                  className="w-full bg-[#070a0d] border border-white/[0.08] rounded-xl px-3 py-2.5 text-xs text-white focus:outline-none focus:border-[#8bd132] transition"
                >
                  <option value="instagram">Instagram</option>
                  <option value="linkedin">LinkedIn</option>
                  <option value="tiktok">TikTok</option>
                  <option value="youtube">YouTube</option>
                  <option value="pinterest">Pinterest</option>
                  <option value="threads">Threads</option>
                  <option value="x">X (Twitter)</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-white mb-1.5">Texto gerado e editável</label>
              <textarea
                value={copyText}
                onChange={(e) => setCopyText(e.target.value)}
                rows={6}
                className="w-full bg-[#070a0d] border border-white/[0.08] rounded-xl p-3 text-xs text-white focus:outline-none focus:border-[#8bd132] font-sans leading-relaxed resize-y transition"
              />
            </div>

            {/* Carousel Slide Builder (when format is carousel) */}
            {selectedFormat === 'carousel' && (
              <div className="p-4 rounded-xl bg-white/[0.02] border border-white/5 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-[#ededed] flex items-center gap-1.5">
                    <Layers className="w-4 h-4 text-indigo-400" /> Slides do Carrossel ({slides.length})
                  </span>
                  <button
                    onClick={handleAddSlide}
                    className="px-2.5 py-1 rounded-lg bg-indigo-600/20 text-indigo-300 hover:bg-indigo-600/30 text-[11px] font-bold flex items-center gap-1"
                  >
                    <Plus className="w-3.5 h-3.5" /> Slide
                  </button>
                </div>

                <div className="flex gap-2 overflow-x-auto pb-1">
                  {slides.map((s, idx) => (
                    <button
                      key={idx}
                      onClick={() => setActiveSlideIndex(idx)}
                      className={`px-3 py-1.5 rounded-lg text-[11px] font-bold shrink-0 ${
                        activeSlideIndex === idx
                          ? 'bg-indigo-600 text-white'
                          : 'bg-white/[0.03] text-white/40 hover:text-white'
                      }`}
                    >
                      Slide {idx + 1}
                    </button>
                  ))}
                </div>

                {slides[activeSlideIndex] && (
                  <div className="space-y-2 pt-2 border-t border-white/5">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] uppercase font-bold text-white/40">
                        Editando Slide {activeSlideIndex + 1}
                      </span>
                      {slides.length > 1 && (
                        <button
                          onClick={() => handleRemoveSlide(activeSlideIndex)}
                          className="text-rose-400 hover:text-rose-300 text-[10px] flex items-center gap-1"
                        >
                          <Trash2 className="w-3 h-3" /> Excluir
                        </button>
                      )}
                    </div>

                    <input
                      type="text"
                      value={slides[activeSlideIndex].headline}
                      onChange={(e) => {
                        const updated = [...slides];
                        updated[activeSlideIndex].headline = e.target.value;
                        setSlides(updated);
                      }}
                      className="w-full bg-white/[0.03] border border-white/5 rounded-lg p-2 text-xs text-[#ededed] focus:outline-none"
                      placeholder="Título do slide"
                    />

                    <textarea
                      value={slides[activeSlideIndex].text}
                      onChange={(e) => {
                        const updated = [...slides];
                        updated[activeSlideIndex].text = e.target.value;
                        setSlides(updated);
                      }}
                      rows={2}
                      className="w-full bg-white/[0.03] border border-white/5 rounded-lg p-2 text-xs text-[#ededed] focus:outline-none resize-none"
                      placeholder="Texto complementar do slide"
                    />
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Right Col: Live Social Preview Card */}
        <div className="space-y-4 flex flex-col">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-[#ededed] flex items-center gap-1.5">
              <Eye className="w-4 h-4 text-emerald-400" /> Visualização em Tempo Real ({selectedPlatform})
            </span>
            <span className="text-[10px] text-white/40">Simulação fiel da interface</span>
          </div>

          {/* Social Card Mockup */}
          <div className="flex-1 bg-[#0A0A0A] border border-white/5 rounded-2xl p-4 flex flex-col justify-center items-center">
            <div className="w-full max-w-sm bg-[#050505] border border-white/10 rounded-2xl overflow-hidden shadow-2xl">
              {/* Mockup Header */}
              <div className="p-3 border-b border-white/5 flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-full bg-indigo-600/30 border border-indigo-500/40 flex items-center justify-center text-xs font-bold text-indigo-300">
                    NX
                  </div>
                  <div>
                    <div className="text-xs font-bold text-[#ededed]">Clicko Studio</div>
                    <div className="text-[10px] text-white/40">Patrocinado • Agora</div>
                  </div>
                </div>
                <span className="text-xs text-white/30">•••</span>
              </div>

              {/* Mockup Visual Stage */}
              <div className="relative aspect-square bg-black flex items-center justify-center p-6 text-center border-b border-white/5 overflow-hidden">
                <img
                  src={previewImageUrl}
                  alt="Prévia"
                  className="absolute inset-0 w-full h-full object-cover opacity-30"
                  referrerPolicy="no-referrer"
                />

                <div className="relative z-10 space-y-3 max-w-xs">
                  {selectedFormat === 'carousel' && slides[activeSlideIndex] ? (
                    <>
                      <div className="text-xs font-bold uppercase text-indigo-400 tracking-wider">
                        Slide {activeSlideIndex + 1} / {slides.length}
                      </div>
                      <h3 className="text-base font-extrabold text-white leading-tight">
                        {slides[activeSlideIndex].headline}
                      </h3>
                      <p className="text-xs text-neutral-300 line-clamp-3">
                        {slides[activeSlideIndex].text}
                      </p>
                    </>
                  ) : (
                    <>
                      <h3 className="text-base font-extrabold text-white leading-tight">
                        {postTitle}
                      </h3>
                      <p className="text-xs text-neutral-300 line-clamp-3">
                        {copyText.slice(0, 120)}...
                      </p>
                    </>
                  )}
                </div>

                {selectedFormat === 'carousel' && slides.length > 1 && (
                  <div className="absolute bottom-3 left-0 right-0 flex justify-center gap-1.5 z-20">
                    {slides.map((_, idx) => (
                      <span
                        key={idx}
                        className={`w-1.5 h-1.5 rounded-full ${
                          idx === activeSlideIndex ? 'bg-indigo-400 w-3' : 'bg-white/30'
                        } transition-all`}
                      ></span>
                    ))}
                  </div>
                )}
              </div>

              {/* Mockup Actions & Copy */}
              <div className="p-3 space-y-2 text-xs">
                <div className="flex items-center justify-between text-neutral-300">
                  <div className="flex items-center gap-3">
                    <Heart className="w-4 h-4 hover:text-rose-400 cursor-pointer" />
                    <MessageCircle className="w-4 h-4 hover:text-indigo-400 cursor-pointer" />
                    <Share2 className="w-4 h-4 hover:text-indigo-400 cursor-pointer" />
                  </div>
                  <Bookmark className="w-4 h-4 hover:text-amber-400 cursor-pointer" />
                </div>

                <div className="text-[11px] text-neutral-300 leading-normal line-clamp-3 whitespace-pre-wrap">
                  <strong className="text-[#ededed]">clickostudio</strong> {copyText}
                </div>

                <div className="flex flex-wrap gap-1 text-[10px] text-indigo-400 font-medium pt-1">
                  {hashtags.map((h, i) => (
                    <span key={i}>{h}</span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
