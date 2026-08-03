import React from 'react';
import {
  Sparkles,
  Send,
  Bot,
  User,
  Plus,
  CheckCircle2,
  Share2,
  Calendar,
  Layers,
  ArrowRight,
  RefreshCw,
  Zap,
  Tag,
  SlidersHorizontal,
} from 'lucide-react';
import { Workspace, Post } from '../types';

interface AICentralViewProps {
  activeWorkspace: Workspace;
  onAddGeneratedPosts: (newPosts: Partial<Post>[]) => void;
  initialPrompt?: string;
}

interface ChatMessage {
  id: string;
  sender: 'user' | 'ai';
  text: string;
  timestamp: string;
  campaignCard?: any;
}

export const AICentralView: React.FC<AICentralViewProps> = ({
  activeWorkspace,
  onAddGeneratedPosts,
  initialPrompt = '',
}) => {
  const [activeSubTab, setActiveSubTab] = React.useState<'chat' | 'campaign-wizard' | 'brand-knowledge'>('chat');
  
  // Chat state
  const [chatInput, setChatInput] = React.useState(initialPrompt);
  const [chatMessages, setChatMessages] = React.useState<ChatMessage[]>([
    {
      id: 'm1',
      sender: 'ai',
      text: `Olá! Sou a IA Central da marca **${activeWorkspace.brandProfile.name}**. Conheço seu tom de voz (*${activeWorkspace.brandProfile.tone}*), seu público-alvo e seu histórico. Como posso ajudar seu marketing hoje?`,
      timestamp: '10:00',
    },
  ]);
  const [isLoadingChat, setIsLoadingChat] = React.useState(false);

  // Assistente de campanha state
  const [wizardGoal, setWizardGoal] = React.useState('Lançamento de Novo Produto / Serviço');
  const [wizardTopic, setWizardTopic] = React.useState('Plataforma de IA com automação de mídias sociais');
  const [wizardTone, setWizardTone] = React.useState(activeWorkspace.brandProfile.tone);
  const [selectedPlatforms, setSelectedPlatforms] = React.useState<string[]>([
    'Instagram',
    'LinkedIn',
    'TikTok',
    'YouTube',
  ]);
  const [isGeneratingCampaign, setIsGeneratingCampaign] = React.useState(false);
  const [generatedCampaign, setGeneratedCampaign] = React.useState<any>(null);
  const [addedToSchedule, setAddedToSchedule] = React.useState(false);

  // Chat submit handler
  const handleSendChatMessage = async (customText?: string) => {
    const messageToSend = customText || chatInput;
    if (!messageToSend.trim()) return;

    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      sender: 'user',
      text: messageToSend,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setChatMessages((prev) => [...prev, userMsg]);
    if (!customText) setChatInput('');
    setIsLoadingChat(true);

    try {
      const res = await fetch('/api/ai/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: messageToSend,
          brandProfile: activeWorkspace.brandProfile,
        }),
      });

      const data = await res.json();
      const aiMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        sender: 'ai',
        text: data.reply || 'Processamento concluído.',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };

      setChatMessages((prev) => [...prev, aiMsg]);
    } catch (err) {
      console.error(err);
      setChatMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          sender: 'ai',
          text: 'Entendido! Analisei sua solicitação. Posso estruturar essa campanha agora mesmo no Gerador de Campanhas.',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
    } finally {
      setIsLoadingChat(false);
    }
  };

  // Campaign generator handler
  const handleGenerateCampaign = async () => {
    setIsGeneratingCampaign(true);
    setGeneratedCampaign(null);
    setAddedToSchedule(false);

    try {
      const res = await fetch('/api/ai/generate-campaign', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          campaignGoal: wizardGoal,
          productOrTopic: wizardTopic,
          platforms: selectedPlatforms,
          tone: wizardTone,
          brandName: activeWorkspace.brandProfile.name,
        }),
      });

      const data = await res.json();
      setGeneratedCampaign(data);
    } catch (err) {
      console.error(err);
    } finally {
      setIsGeneratingCampaign(false);
    }
  };

  const handleApplyCampaignToSchedule = () => {
    if (!generatedCampaign || !generatedCampaign.posts) return;

    const postsToCreate: Partial<Post>[] = generatedCampaign.posts.map((p: any, idx: number) => ({
      title: p.title,
      platform: (p.platform.toLowerCase() as any) || 'instagram',
      format: (p.format.toLowerCase() as any) || 'post',
      copy: p.copy,
      hashtags: p.hashtags || [],
      scheduledAt: new Date(Date.now() + (idx + 1) * 86400000).toISOString(),
      status: 'scheduled',
      author: 'Assistente da IA Central',
      aiScore: 95,
      imageUrl: 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=800&q=80',
    }));

    onAddGeneratedPosts(postsToCreate);
    setAddedToSchedule(true);
  };

  const togglePlatform = (p: string) => {
    if (selectedPlatforms.includes(p)) {
      setSelectedPlatforms(selectedPlatforms.filter((item) => item !== p));
    } else {
      setSelectedPlatforms([...selectedPlatforms, p]);
    }
  };

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Tab Navigation sub-header */}
      <div className="flex items-center justify-between border-b border-white/5 pb-4">
        <div className="flex items-center gap-2">
          <div className="p-2 rounded-xl bg-indigo-600/20 border border-indigo-500/30 text-indigo-400">
            <Sparkles className="w-5 h-5 animate-pulse" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-[#ededed]">IA Central de Marca</h2>
            <p className="text-xs text-white/40">Assistente estratégico, inteligência de audiência e estúdio multicanal</p>
          </div>
        </div>

        <div className="flex items-center p-1 rounded-xl bg-white/[0.02] border border-white/5">
          <button
            onClick={() => setActiveSubTab('chat')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all duration-150 ${
              activeSubTab === 'chat'
                ? 'bg-indigo-600 text-white shadow-sm shadow-indigo-600/20'
                : 'text-white/40 hover:text-white'
            }`}
          >
            Chat Estratégico
          </button>
          <button
            onClick={() => setActiveSubTab('campaign-wizard')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all duration-150 ${
              activeSubTab === 'campaign-wizard'
                ? 'bg-indigo-600 text-white shadow-sm shadow-indigo-600/20'
                : 'text-white/40 hover:text-white'
            }`}
          >
            Gerador de Campanhas
          </button>
          <button
            onClick={() => setActiveSubTab('brand-knowledge')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all duration-150 ${
              activeSubTab === 'brand-knowledge'
                ? 'bg-indigo-600 text-white shadow-sm shadow-indigo-600/20'
                : 'text-white/40 hover:text-white'
            }`}
          >
            Cérebro da Marca
          </button>
        </div>
      </div>

      {/* Sub-Tab 1: Conversational Chat */}
      {activeSubTab === 'chat' && (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 h-[640px]">
          {/* Main Chat Stream */}
          <div className="lg:col-span-3 rounded-2xl bg-[#0A0A0A] border border-white/5 flex flex-col overflow-hidden">
            <div className="p-4 border-b border-white/5 bg-white/[0.01] flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-ping"></span>
                <span className="text-xs font-bold text-[#ededed]">IA Central Pronta</span>
              </div>
              <span className="text-[10px] text-white/40">Contexto: {activeWorkspace.brandProfile.name}</span>
            </div>

            {/* Messages Body */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
              {chatMessages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex items-start gap-3 ${msg.sender === 'user' ? 'flex-row-reverse' : ''}`}
                >
                  <div
                    className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 ${
                      msg.sender === 'user'
                        ? 'bg-indigo-600 text-white font-bold text-xs'
                        : 'bg-indigo-950 border border-indigo-500/30 text-indigo-400'
                    }`}
                  >
                    {msg.sender === 'user' ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                  </div>

                  <div
                    className={`max-w-xl p-4 rounded-2xl text-xs leading-relaxed space-y-2 ${
                      msg.sender === 'user'
                        ? 'bg-indigo-600 text-white rounded-tr-none'
                        : 'bg-white/[0.03] border border-white/5 text-neutral-200 rounded-tl-none'
                    }`}
                  >
                    <div className="whitespace-pre-wrap">{msg.text}</div>
                    <div
                      className={`text-[9px] text-right ${
                        msg.sender === 'user' ? 'text-indigo-200' : 'text-white/30'
                      }`}
                    >
                      {msg.timestamp}
                    </div>
                  </div>
                </div>
              ))}

              {isLoadingChat && (
                <div className="flex items-center gap-2 text-xs text-indigo-400 p-2">
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>IA Central pensando e gerando estratégia...</span>
                </div>
              )}
            </div>

            {/* Input Bar */}
            <div className="p-4 border-t border-white/5 bg-white/[0.01] flex items-center gap-3">
              <input
                type="text"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSendChatMessage()}
                placeholder="Ex: Crie um plano de 5 publicações para lançamento do nosso novo SaaS..."
                className="flex-1 bg-white/[0.03] border border-white/5 rounded-xl px-4 py-2.5 text-xs text-[#ededed] placeholder-white/30 focus:outline-none focus:border-indigo-500/50"
              />
              <button
                onClick={() => handleSendChatMessage()}
                disabled={isLoadingChat || !chatInput.trim()}
                className="px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium text-xs flex items-center gap-2 shadow-lg shadow-indigo-600/20 transition-all"
              >
                <span>Enviar</span>
                <Send className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* Right Quick Prompts Panel */}
          <div className="rounded-2xl bg-[#0A0A0A] border border-white/5 p-4 space-y-4 flex flex-col justify-between">
            <div>
              <h3 className="text-xs font-bold text-[#ededed] mb-1 flex items-center gap-2">
                <Zap className="w-4 h-4 text-amber-400" /> Comandos rápidos
              </h3>
              <p className="text-[11px] text-white/40 mb-3">Clique para disparar ações diretas com a IA Central</p>

              <div className="space-y-2">
                {[
                  'Crie uma campanha de lançamento para o meu produto',
                  'Gere 5 ideias virais de Reels para esta semana',
                  'Analise meu histórico e sugira o melhor horário de postagem',
                  'Escreva um artigo do LinkedIn sobre Inovação B2B',
                  'Como aumentar em 20% a taxa de salvamentos?',
                ].map((promptText, i) => (
                  <button
                    key={i}
                    onClick={() => {
                      setChatInput(promptText);
                      handleSendChatMessage(promptText);
                    }}
                    className="w-full text-left p-2.5 rounded-xl bg-white/[0.02] hover:bg-white/[0.05] border border-white/5 hover:border-indigo-500/30 text-[11px] text-neutral-300 transition-all group flex items-center justify-between"
                  >
                    <span className="line-clamp-2">{promptText}</span>
                    <ArrowRight className="w-3 h-3 text-white/40 group-hover:text-indigo-400 shrink-0 ml-2" />
                  </button>
                ))}
              </div>
            </div>

            <div className="p-3 rounded-xl bg-indigo-600/10 border border-indigo-500/20 text-[11px] text-neutral-300">
              <div className="font-semibold text-indigo-300 mb-1">Dica de Produtividade</div>
              A IA Central pode gerar textos, comandos de imagem, hashtags e datas num único comando!
            </div>
          </div>
        </div>
      )}

      {/* Sub-Tab 2: Campaign Generator Wizard */}
      {activeSubTab === 'campaign-wizard' && (
        <div className="space-y-6">
          <div className="p-6 rounded-2xl bg-[#0A0A0A] border border-white/5 space-y-6">
            <div className="flex items-center justify-between border-b border-white/5 pb-4">
              <div>
                <h3 className="text-sm font-bold text-[#ededed]">Gerador de Campanhas Multicanal Inteligente</h3>
                <p className="text-xs text-white/40 mt-0.5">
                  Preencha o objetivo e a IA gerará automaticamente as publicações, os textos, imagens e agenda em poucas frações de segundo.
                </p>
              </div>
              <button
                onClick={() => setActiveSubTab('chat')}
                className="text-xs text-indigo-400 hover:text-indigo-300 font-medium"
              >
                Voltar ao Chat
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-neutral-300 mb-1.5">
                  Objetivo da Campanha
                </label>
                <input
                  type="text"
                  value={wizardGoal}
                  onChange={(e) => setWizardGoal(e.target.value)}
                  className="w-full bg-white/[0.03] border border-white/5 rounded-xl px-3.5 py-2.5 text-xs text-[#ededed] focus:outline-none focus:border-indigo-500/50"
                  placeholder="Ex: Lançamento de Produto, Promoção de Black Friday, Autoridade de Marca"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-neutral-300 mb-1.5">
                  Tópico / Oferta / Produto
                </label>
                <input
                  type="text"
                  value={wizardTopic}
                  onChange={(e) => setWizardTopic(e.target.value)}
                  className="w-full bg-white/[0.03] border border-white/5 rounded-xl px-3.5 py-2.5 text-xs text-[#ededed] focus:outline-none focus:border-indigo-500/50"
                  placeholder="Ex: Novo módulo de análises com IA"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-neutral-300 mb-2">
                Canais de Distribuição
              </label>
              <div className="flex flex-wrap gap-2">
                {['Instagram', 'LinkedIn', 'TikTok', 'YouTube', 'Pinterest', 'Threads', 'X'].map((plat) => {
                  const isSelected = selectedPlatforms.includes(plat);
                  return (
                    <button
                      key={plat}
                      type="button"
                      onClick={() => togglePlatform(plat)}
                      className={`px-3 py-1.5 rounded-xl text-xs font-medium transition-all ${
                        isSelected
                          ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/20 border border-indigo-400/30'
                          : 'bg-white/[0.03] text-white/40 hover:text-white border border-white/5'
                      }`}
                    >
                      {plat}
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="pt-2 flex justify-end">
              <button
                onClick={handleGenerateCampaign}
                disabled={isGeneratingCampaign}
                className="px-6 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs shadow-xl shadow-indigo-600/20 border border-indigo-400/30 transition-all flex items-center gap-2"
              >
                {isGeneratingCampaign ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>Gerando Campanha Completa...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4 text-amber-300" />
                    <span>Gerar Campanha com IA Central</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Output Generated Campaign Cards */}
          {generatedCampaign && (
            <div className="p-6 rounded-2xl bg-[#0A0A0A] border border-indigo-500/30 space-y-6 animate-in fade-in duration-200">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/5 pb-4">
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                    Campanha Gerada pela IA
                  </span>
                  <h3 className="text-lg font-bold text-[#ededed] mt-1">{generatedCampaign.title}</h3>
                  <p className="text-xs text-neutral-300 mt-0.5">{generatedCampaign.description}</p>
                </div>

                <button
                  onClick={handleApplyCampaignToSchedule}
                  disabled={addedToSchedule}
                  className={`px-4 py-2.5 rounded-xl font-bold text-xs flex items-center gap-2 transition-all ${
                    addedToSchedule
                      ? 'bg-emerald-600 text-white cursor-default'
                      : 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-600/20'
                  }`}
                >
                  <CheckCircle2 className="w-4 h-4" />
                  <span>{addedToSchedule ? 'Adicionado ao Calendário!' : 'Agendar Todos na Fila'}</span>
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {generatedCampaign.posts?.map((p: any, idx: number) => (
                  <div
                    key={idx}
                    className="p-4 rounded-xl bg-white/[0.02] border border-white/5 space-y-3 flex flex-col justify-between"
                  >
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                          {p.platform} • {p.format}
                        </span>
                        <span className="text-[10px] text-white/40">{p.suggestedTime}</span>
                      </div>

                      <h4 className="text-xs font-bold text-[#ededed]">{p.title}</h4>
                      <p className="text-xs text-neutral-300 leading-relaxed whitespace-pre-wrap line-clamp-4">
                        {p.copy}
                      </p>

                      {p.hashtags && (
                        <div className="flex flex-wrap gap-1 pt-1">
                          {p.hashtags.map((tag: string, i: number) => (
                            <span key={i} className="text-[10px] text-indigo-400">
                              {tag}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>

                    <div className="pt-2 border-t border-white/5 text-[10px] text-white/30 italic">
                      Comando de imagem: {p.imagePrompt}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Sub-Tab 3: Conhecimento da marca Settings */}
      {activeSubTab === 'brand-knowledge' && (
        <div className="p-6 rounded-2xl bg-[#0A0A0A] border border-white/5 space-y-6">
          <div className="border-b border-white/5 pb-4">
            <h3 className="text-sm font-bold text-[#ededed]">Parâmetros de Conhecimento da Marca</h3>
            <p className="text-xs text-white/40 mt-0.5">
              A IA Central consulta este perfil para garantir tom de voz, público e diretrizes em 100% dos conteúdos.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs">
            <div className="space-y-4">
              <div>
                <label className="block text-neutral-300 font-semibold mb-1">Nome da Marca</label>
                <div className="p-2.5 rounded-xl bg-white/[0.03] border border-white/5 text-[#ededed]">
                  {activeWorkspace.brandProfile.name}
                </div>
              </div>

              <div>
                <label className="block text-neutral-300 font-semibold mb-1">Setor de Atuação</label>
                <div className="p-2.5 rounded-xl bg-white/[0.03] border border-white/5 text-[#ededed]">
                  {activeWorkspace.brandProfile.industry}
                </div>
              </div>

              <div>
                <label className="block text-neutral-300 font-semibold mb-1">Tom de Voz Principal</label>
                <div className="p-2.5 rounded-xl bg-white/[0.03] border border-white/5 text-[#ededed]">
                  {activeWorkspace.brandProfile.tone}
                </div>
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-neutral-300 font-semibold mb-1">Público-Alvo Prioritário</label>
                <div className="p-2.5 rounded-xl bg-white/[0.03] border border-white/5 text-[#ededed]">
                  {activeWorkspace.brandProfile.targetAudience}
                </div>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">Diretrizes (O que Fazer & Não Fazer)</label>
                <div className="p-2.5 rounded-xl bg-white/[0.03] border border-white/5 text-[#ededed] leading-relaxed">
                  {activeWorkspace.brandProfile.doAndDonts}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
