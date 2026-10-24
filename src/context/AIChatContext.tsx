import React from 'react';
import { useConversations } from '../klic/useConversations';
import type { AIChatMessage, AIMemoryEntry, NavigationTab } from '../types';
import { useOperations } from './OperationsContext';
import { useGovernance } from './GovernanceContext';
import { createRequestGuard } from '../utils/requestGuard';
import { useKlicClient } from '../klic/useKlicClient';

type AIChatContextValue = {
  chat: ReturnType<typeof useConversations>;
  messages: AIChatMessage[];
  loading: boolean;
  sendMessage: (content: string, module: NavigationTab, actionId?: string, attachments?: AIChatAttachment[], conversationStartIndex?: number) => Promise<void>;
  startRadarConversation: (context: RadarConversationContext) => void;
  conversationStartIndexHint: number | null;
  consumeConversationStartHint: () => void;
  clearHistory: () => void;
  toggleFavorite: (id: string) => void;
};

export type AIChatAttachment = {
  name: string;
  type: string;
  size: number;
  dataUrl?: string;
};

export type RadarConversationContext = {
  intent?: 'analyze' | 'content' | 'ideas' | 'script' | 'caption';
  title: string;
  status: string;
  summary: string;
  observedData: string;
  inference: string;
  opportunity?: string;
  suggestedFormat: string;
  angle: string;
  evidence: Array<{ source: string; title: string; url: string }>;
};

const actionDestination = (label: string): NavigationTab => {
  const value = label.toLowerCase();
  if (value.includes('vídeo') || value.includes('video') || value.includes('roteiro')) return 'create-video';
  if (value.includes('imagem') || value.includes('carrossel') || value.includes('post') || value.includes('copy') || value.includes('legenda')) return 'create-image';
  if (value.includes('calend') || value.includes('agend')) return 'calendar';
  if (value.includes('resultado') || value.includes('analis') || value.includes('desempenho')) return 'analytics';
  if (value.includes('biblioteca') || value.includes('reaprove')) return 'library';
  if (value.includes('estratég') || value.includes('campanha') || value.includes('pilar')) return 'strategy';
  return 'ai-chat';
};

const kindForTab = (tab: NavigationTab): 'campaign' | 'studio' | 'calendar' | 'variants' => tab === 'strategy' ? 'campaign' : tab === 'calendar' ? 'calendar' : tab === 'library' ? 'variants' : 'studio';

const selectRelevantMemory = (memory: ReturnType<typeof useOperations>['aiMemory'], intent: string) => {
  const normalized = intent.toLowerCase();
  const categories = /competitor|concorrent|research|tendên|radar|explor/.test(normalized)
    ? ['identity', 'content', 'preference']
    : /video|roteiro|reel/.test(normalized)
      ? ['communication', 'content', 'visual', 'preference']
      : /image|imagem|carrossel|visual/.test(normalized)
        ? ['visual', 'communication', 'content', 'preference']
        : /analysis|diagn|resultado|desempenho/.test(normalized)
          ? ['content', 'identity', 'preference']
          : ['identity', 'communication', 'content', 'preference'];
  return memory
    .filter((entry) => categories.includes(entry.category) && (entry.scope === 'recurring' || entry.scope === 'permanent'))
    .sort((a, b) => Number(b.scope === 'permanent') - Number(a.scope === 'permanent') || b.confidence - a.confidence || b.occurrences - a.occurrences)
    .slice(0, 12);
};

export function AIChatProvider({ children }: { children: React.ReactNode }) {
  const klic = useKlicClient();
  const chat = useConversations();
  const [legacyActive, setLegacyActive] = React.useState(false);
  const operations = useOperations();
  const { approvals, environmentMode, activeAccount, currentUser } = useGovernance();
  const { contextSnapshot, activeClient, activeCampaign, activeWorkspace, aiMemory, posts, learningSignals, connectedAccounts, upsertAIMemory } = operations;
  const storageKey = `clicko:ai-chat:v2:${klic.scope}`;
  const welcome = React.useCallback((): AIChatMessage => ({
    id: `welcome-${activeWorkspace.id}`, role: 'assistant', createdAt: new Date().toISOString(), module: 'ai-chat',
    content: `Olá! Sou a KLIC, IA da Clicko Studios. Posso pesquisar, planejar, criar, organizar e analisar a operação de ${activeClient?.name || activeWorkspace.name} usando apenas o contexto deste ${environmentMode === 'personal' ? 'perfil' : 'workspace'}.`,
    actions: [
      { label: 'Criar estratégia', tab: 'strategy', kind: 'campaign', actionId: 'strategy.create' },
      { label: 'Pesquisar tendências', tab: 'ai-chat', kind: 'studio', actionId: 'research.trends' },
      { label: 'Criar conteúdo', tab: 'create-image', kind: 'studio', actionId: 'create.post' },
    ],
  }), [activeClient?.name, activeWorkspace.id, activeWorkspace.name, environmentMode]);

  const loadMessages = React.useCallback(() => {
    try {
      const saved = localStorage.getItem(storageKey);
      if (!saved) return [welcome()];
      const parsed = JSON.parse(saved) as AIChatMessage[] | { workspaceId?: string; messages?: AIChatMessage[] };
      if (Array.isArray(parsed)) return parsed;
      return parsed.workspaceId === activeWorkspace.id && Array.isArray(parsed.messages) ? parsed.messages : [welcome()];
    }
    catch { return [welcome()]; }
  }, [activeWorkspace.id, storageKey, welcome]);
  const [messages, setMessages] = React.useState<AIChatMessage[]>(loadMessages);
  const [loading, setLoading] = React.useState(false);
  const [conversationStartIndexHint, setConversationStartIndexHint] = React.useState<number | null>(null);
  const loadedChatWorkspaceId = React.useRef(klic.scope);
  const chatScope = React.useRef(klic.scope);
  chatScope.current = klic.scope;
  const replyGuard = React.useRef(createRequestGuard());
  const pendingReply = React.useRef<AbortController | null>(null);
  React.useEffect(() => () => { replyGuard.current.invalidate(); pendingReply.current?.abort(); }, []);

  React.useEffect(() => {
    if (loadedChatWorkspaceId.current !== klic.scope) {
      replyGuard.current.invalidate();
      pendingReply.current?.abort();
      pendingReply.current = null;
      setLoading(false);
      setConversationStartIndexHint(null);
      loadedChatWorkspaceId.current = klic.scope;
      setMessages(loadMessages());
      return;
    }
    try { localStorage.setItem(storageKey, JSON.stringify({ workspaceId: activeWorkspace.id, messages })); }
    catch { console.warn('Não foi possível persistir o histórico da KLIC no navegador. As mensagens permanecem nesta sessão.'); }
  }, [activeWorkspace.id, klic.scope, loadMessages, messages, storageKey]);
  React.useEffect(() => {
    approvals.filter(approval => approval.workspaceId === activeWorkspace.id).forEach((approval) => {
      const memoryId = `memory-approval-${approval.id}-${approval.stage}`;
      if (aiMemory.some((entry) => entry.id === memoryId)) return;
      if (approval.stage === 'approved' || approval.stage === 'published') {
        upsertAIMemory({ id: memoryId, category: 'content', label: `Padrão aprovado · ${approval.title}`, value: `O conteúdo “${approval.title}” foi aprovado. Use como sinal positivo, não como regra absoluta.`, scope: 'recurring', confidence: 75, source: 'approval' });
      } else if ((approval.stage === 'changes_requested' || approval.stage === 'rejected') && approval.comments.length) {
        const feedback = approval.comments[approval.comments.length - 1]?.message;
        if (feedback) upsertAIMemory({ id: memoryId, category: 'preference', label: `Feedback em ${approval.title}`, value: feedback, scope: 'task', confidence: 70, source: 'approval' });
      }
    });
  }, [aiMemory, approvals, upsertAIMemory, activeWorkspace.id]);

  const learnConversationMemory = React.useCallback((content: string) => {
    if (environmentMode === 'company' && !currentUser?.modules.includes('ai-chat')) return;
    const normalized = content.toLowerCase();
    const temporary = /\b(hoje|agora|neste post|nesta peça|essa campanha|esta campanha|essa semana|por enquanto|só desta vez)\b/.test(normalized);
    if (temporary) return;
    const permanent = /\b(sempre|daqui para frente|regra|nunca|em todos os conteúdos)\b/.test(normalized);
    const candidates: Array<{ test: RegExp; category: AIMemoryEntry['category']; label: string; value?: string }> = [
      { test: /minha empresa (se chama|é)|nossa empresa (se chama|é)|somos a |trabalho na /, category: 'identity', label: 'Identidade da empresa' },
      { test: /vendemos|oferecemos|nosso produto|nosso serviço|nossa solução/, category: 'content', label: 'Produtos e serviços' },
      { test: /nosso público|nossa audiência|atendemos|clientes são|persona/, category: 'identity', label: 'Público principal' },
      { test: /nosso objetivo|nossa meta|queremos alcançar|prioridade é/, category: 'content', label: 'Objetivo recorrente' },
      { test: /nosso processo|nosso fluxo|trabalhamos com|etapa de|forma de trabalhar/, category: 'content', label: 'Processo de trabalho' },
      { test: /identidade visual|estética|paleta|cores da marca|estilo visual/, category: 'visual', label: 'Preferência visual' },
      { test: /tom de voz|linguagem|forma de comunicar|mais sofisticad|mais premium|mais direto|menos texto|mais curto|seja breve/, category: 'communication', label: 'Tom de voz' },
      { test: /sem emoji|não (quero|use|usar).*emoji|evit.*emoji/, category: 'preference', label: 'Uso de emojis', value: 'Evitar emojis nas peças e respostas.' },
      { test: /não gostei.*cta|evit.*cta/, category: 'preference', label: 'Preferência de CTA' },
      { test: /use esse estilo|gostei.*estilo|estrutura ficou excelente/, category: 'preference', label: 'Padrão aprovado' },
    ];
    const match = candidates.find((candidate) => candidate.test.test(normalized));
    if (!match) return;
    upsertAIMemory({ clientId: activeClient?.id, category: match.category, label: match.label, value: match.value || content.trim(), scope: permanent ? 'permanent' : 'recurring', confidence: permanent ? 95 : 78, source: 'conversation' });
  }, [activeClient?.id, currentUser?.modules, environmentMode, upsertAIMemory]);

  const startRadarConversation = React.useCallback((radar: RadarConversationContext) => {
    const brandName = activeClient?.name || activeWorkspace.name;
    const sourceLines = radar.evidence.slice(0, 5).map((evidence) => `• ${evidence.source}: ${evidence.title}\n  ${evidence.url}`).join('\n');
    const content = [
      'Contexto recebido do Radar da Clicko',
      '',
      `Tendência: ${radar.title}`,
      `Status: ${radar.status}`,
      `Contexto observado: ${radar.summary}`,
      '',
      radar.observedData,
      radar.inference,
      sourceLines ? `\nFontes verificadas:\n${sourceLines}` : '',
      '',
      `Para ${brandName}, o ponto de partida é ${radar.opportunity || `avaliar uma conexão original com o contexto da marca antes de produzir`}.`,
      `Formato inicialmente sugerido: ${radar.suggestedFormat}. Ângulo: ${radar.angle}.`,
      '',
      ({
        analyze: 'Analise criticamente por que este assunto está crescendo, onde há evidência real, qual é o estágio e como a marca pode aproveitá-lo. Separe dados observados de inferências e não invente métricas.',
        ideas: 'Gere ideias originais de conteúdo para esta marca a partir da tendência, indicando público, rede, formato e gancho. Não copie conteúdos existentes nem invente métricas.',
        script: 'Crie um roteiro original a partir da tendência, com gancho, sequência, cenas ou falas, duração aproximada e CTA. Separe fatos observados de sugestões criativas.',
        caption: 'Crie uma legenda original e adequada à marca a partir desta tendência, com CTA e hashtags somente quando fizerem sentido. Não apresente hipóteses como dados.',
        content: 'Como você quer aproveitar esta tendência? Escolha Post, Carrossel, Reel, TikTok, YouTube Short, Vídeo ou Story — ou descreva livremente sua intenção. Vou conectar o assunto à marca sem copiar a tendência literalmente.',
      } as const)[radar.intent || 'content'],
    ].filter(Boolean).join('\n');
    const assistant: AIChatMessage = {
      id: `chat-radar-${Date.now()}`,
      role: 'assistant',
      content,
      createdAt: new Date().toISOString(),
      module: 'ai-chat',
      researchedExternally: true,
      actions: [
        ['Post', 'post'], ['Carrossel', 'carousel'], ['Reel', 'reel'], ['TikTok', 'tiktok'],
        ['YouTube Short', 'youtube-short'], ['Vídeo', 'video'], ['Story', 'story'],
      ].map(([label, format]) => ({ label, tab: 'ai-chat' as const, kind: 'studio' as const, actionId: `radar.format.${format}` })),
    };
    setConversationStartIndexHint(messages.length);
    setMessages((current) => [...current, assistant]);
    chat.newConversation();
    void chat.send(content).catch(() => {});
  }, [activeClient?.name, activeWorkspace.name, messages.length, chat.newConversation, chat.send]);

  const consumeConversationStartHint = React.useCallback(() => setConversationStartIndexHint(null), []);

  const sendMessage = React.useCallback(async (content: string, module: NavigationTab, actionId?: string, attachments: AIChatAttachment[] = [], conversationStartIndex?: number) => {
    setLegacyActive(module === 'create-image' || module === 'create-video');
    if (module !== 'create-image' && module !== 'create-video') { await chat.send(content, attachments, undefined, actionId).catch(() => {}); return; }
    const clean = content.trim();
    if (!clean || loading || pendingReply.current || loadedChatWorkspaceId.current !== klic.scope) return;
    const controller = new AbortController();
    pendingReply.current = controller;
    const isCurrent = replyGuard.current.begin(klic.scope, () => chatScope.current);
    const legacyMedia = module === 'create-image' || module === 'create-video';
    if (legacyMedia) learnConversationMemory(clean);
    const userMessage: AIChatMessage = { id: `chat-user-${Date.now()}`, role: 'user', content: clean, createdAt: new Date().toISOString(), module };
    const contextStart = conversationStartIndex === undefined
      ? Math.max(0, messages.length - 11)
      : Math.max(0, Math.min(conversationStartIndex, messages.length));
    const conversation = [...messages.slice(contextStart), userMessage].slice(-12).map(({ role, content: messageContent }) => ({ role, content: messageContent }));
    setMessages((current) => [...current, userMessage]);
    setLoading(true);
    try {
      let operatorPreferences: unknown = undefined;
      try { operatorPreferences = JSON.parse(localStorage.getItem(`clicko-studio:user-settings:${activeAccount.id}`) || '{}')?.personalAI; } catch { operatorPreferences = undefined; }
      const coreData = !legacyMedia ? await klic.request<any>('chat', module, { message: clean, actionId, conversationContext: conversation, attachments }, controller.signal) : undefined;
      const response = legacyMedia ? await fetch('/api/ai/chat', {
        method: 'POST', signal: controller.signal, headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: clean, actionId, contextProfile: contextSnapshot, clientContext: activeClient, strategyContext: activeCampaign,
          screenContext: module, workspaceId: activeWorkspace.id, environmentMode, conversationContext: conversation, attachments, operatorPreferences,
          memoryContext: selectRelevantMemory(aiMemory, `${actionId || ''} ${clean}`),
          operationSummary: {
            contentHistory: posts.slice(0, 60).map((post) => ({ title: post.title, platform: post.platform, format: post.format, status: post.status, objective: post.objective, campaignId: post.campaignId, scheduledAt: post.scheduledAt, hashtags: post.hashtags })),
            learningSignals: learningSignals.slice(0, 10),
            approvals: approvals.slice(0, 10).map((item) => ({ title: item.title, stage: item.stage, comments: item.comments.slice(-2) })),
            connectedAccounts: connectedAccounts.map((account) => ({ platform: account.platform, connected: account.connected && account.connectionStatus === 'connected', permissions: account.permissions || [] })),
            knowledgeGaps: ['products', 'services', 'audience', 'objectives', 'differentiators'].filter((field) => !String(contextSnapshot[field as keyof typeof contextSnapshot] || '').trim()),
          },
        }),
      }) : undefined;
      if (response && !response.ok) throw new Error(`Falha HTTP ${response.status}`);
      const data = coreData || await response!.json();
      if (!isCurrent()) return;
      const suggested = Array.isArray(data.actionSuggestions) ? data.actionSuggestions.slice(0, 5) : [];
      const actions: AIChatMessage['actions'] = suggested.map((suggestion: string | { label: string; actionId?: string; destination?: NavigationTab; risk?: 'read' | 'reversible' | 'external' | 'critical'; requiresConfirmation?: boolean }) => {
        const label = typeof suggestion === 'string' ? suggestion : suggestion.label;
        const tab = typeof suggestion === 'string' ? actionDestination(label) : suggestion.destination || actionDestination(label);
        return { label, tab, kind: kindForTab(tab), actionId: typeof suggestion === 'string' ? undefined : suggestion.actionId, risk: typeof suggestion === 'string' ? undefined : suggestion.risk, requiresConfirmation: typeof suggestion === 'string' ? false : suggestion.requiresConfirmation };
      });
      if (legacyMedia && !actions.length) actions.push(
        { label: 'Transformar em estratégia', tab: 'strategy', kind: 'campaign', actionId: 'strategy.create' },
        { label: 'Criar imagem', tab: 'create-image', kind: 'studio', actionId: 'create.image' },
        { label: 'Montar calendário', tab: 'calendar', kind: 'calendar', actionId: 'strategy.calendar' },
      );
      const assistant: AIChatMessage = { id: `chat-ai-${Date.now()}`, role: 'assistant', content: data.reply || 'Preparei a análise, mas não consegui formatar a resposta agora.', createdAt: new Date().toISOString(), module, actions, brandScore: typeof data.brandCompatibilityScore === 'number' ? data.brandCompatibilityScore : undefined, researchedExternally: Boolean(data.researchedExternally) };
      setMessages((current) => [...current, assistant]);
    } catch {
      if (!isCurrent()) return;
      setMessages((current) => [...current, { id: `chat-fallback-${Date.now()}`, role: 'assistant', content: `Não consegui consultar a KLIC agora. Mantive seu pedido no contexto de ${activeClient?.name || activeWorkspace.name} para você continuar sem perder o raciocínio.`, createdAt: new Date().toISOString(), module }]);
    } finally { if (isCurrent()) { pendingReply.current = null; setLoading(false); } }
  }, [activeAccount.id, activeCampaign, activeClient, activeWorkspace.id, activeWorkspace.name, aiMemory, approvals, connectedAccounts, contextSnapshot, environmentMode, learnConversationMemory, learningSignals, loading, messages, posts, klic.request, klic.scope, chat.send]);

  const clearHistory = React.useCallback(() => { replyGuard.current.invalidate(); pendingReply.current?.abort(); pendingReply.current = null; setLoading(false); setMessages([welcome()]); setConversationStartIndexHint(null); }, [welcome]);
  const toggleFavorite = React.useCallback((id: string) => setMessages((current) => current.map((message) => message.id === id ? { ...message, favorite: !message.favorite } : message)), []);
  return <AIChatContext.Provider value={{ chat, messages: legacyActive ? (loadedChatWorkspaceId.current === klic.scope ? messages : [welcome()]) : chat.messages, loading: legacyActive ? loading : chat.loading, sendMessage, startRadarConversation, conversationStartIndexHint, consumeConversationStartHint, clearHistory, toggleFavorite }}>{children}</AIChatContext.Provider>;
}

const AIChatContext = React.createContext<AIChatContextValue | null>(null);
export function useAIChat() { const value = React.useContext(AIChatContext); if (!value) throw new Error('useAIChat deve ser usado dentro de AIChatProvider.'); return value; }
