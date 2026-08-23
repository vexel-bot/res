import React from 'react';
import type { AIChatMessage, AIMemoryEntry, NavigationTab } from '../types';
import { useOperations } from './OperationsContext';
import { useGovernance } from './GovernanceContext';

type AIChatContextValue = {
  messages: AIChatMessage[];
  loading: boolean;
  sendMessage: (content: string, module: NavigationTab, actionId?: string, attachments?: AIChatAttachment[], conversationStartIndex?: number) => Promise<void>;
  clearHistory: () => void;
  toggleFavorite: (id: string) => void;
};

export type AIChatAttachment = {
  name: string;
  type: string;
  size: number;
  dataUrl?: string;
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
  const operations = useOperations();
  const { approvals, environmentMode, activeAccount, currentUser } = useGovernance();
  const { contextSnapshot, activeClient, activeCampaign, activeWorkspace, aiMemory, posts, learningSignals, connectedAccounts, upsertAIMemory } = operations;
  const storageKey = `clicko:ai-chat:${activeWorkspace.id}`;
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
  const loadedChatWorkspaceId = React.useRef(activeWorkspace.id);

  React.useEffect(() => {
    if (loadedChatWorkspaceId.current !== activeWorkspace.id) {
      loadedChatWorkspaceId.current = activeWorkspace.id;
      setMessages(loadMessages());
      return;
    }
    localStorage.setItem(storageKey, JSON.stringify({ workspaceId: activeWorkspace.id, messages }));
  }, [activeWorkspace.id, loadMessages, messages, storageKey]);
  React.useEffect(() => {
    approvals.forEach((approval) => {
      const memoryId = `memory-approval-${approval.id}-${approval.stage}`;
      if (aiMemory.some((entry) => entry.id === memoryId)) return;
      if (approval.stage === 'approved' || approval.stage === 'published') {
        upsertAIMemory({ id: memoryId, category: 'content', label: `Padrão aprovado · ${approval.title}`, value: `O conteúdo “${approval.title}” foi aprovado. Use como sinal positivo, não como regra absoluta.`, scope: 'recurring', confidence: 75, source: 'approval' });
      } else if ((approval.stage === 'changes_requested' || approval.stage === 'rejected') && approval.comments.length) {
        const feedback = approval.comments[approval.comments.length - 1]?.message;
        if (feedback) upsertAIMemory({ id: memoryId, category: 'preference', label: `Feedback em ${approval.title}`, value: feedback, scope: 'task', confidence: 70, source: 'approval' });
      }
    });
  }, [aiMemory, approvals, upsertAIMemory]);

  const learnConversationMemory = React.useCallback((content: string) => {
    if (environmentMode === 'company' && currentUser?.role !== 'master') return;
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
    upsertAIMemory({ category: match.category, label: match.label, value: match.value || content.trim(), scope: permanent ? 'permanent' : 'recurring', confidence: permanent ? 95 : 78, source: 'conversation' });
  }, [currentUser?.role, environmentMode, upsertAIMemory]);

  const sendMessage = React.useCallback(async (content: string, module: NavigationTab, actionId?: string, attachments: AIChatAttachment[] = [], conversationStartIndex?: number) => {
    const clean = content.trim();
    if (!clean || loading) return;
    learnConversationMemory(clean);
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
      const response = await fetch('/api/ai/chat', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
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
      });
      if (!response.ok) throw new Error(`Falha HTTP ${response.status}`);
      const data = await response.json();
      const suggested = Array.isArray(data.actionSuggestions) ? data.actionSuggestions.slice(0, 5) : [];
      const actions: AIChatMessage['actions'] = suggested.map((suggestion: string | { label: string; actionId?: string }) => {
        const label = typeof suggestion === 'string' ? suggestion : suggestion.label;
        const tab = actionDestination(label);
        return { label, tab, kind: kindForTab(tab), actionId: typeof suggestion === 'string' ? undefined : suggestion.actionId };
      });
      if (!actions.length) actions.push(
        { label: 'Transformar em estratégia', tab: 'strategy', kind: 'campaign', actionId: 'strategy.create' },
        { label: 'Criar imagem', tab: 'create-image', kind: 'studio', actionId: 'create.image' },
        { label: 'Montar calendário', tab: 'calendar', kind: 'calendar', actionId: 'strategy.calendar' },
      );
      const assistant: AIChatMessage = { id: `chat-ai-${Date.now()}`, role: 'assistant', content: data.reply || 'Preparei a análise, mas não consegui formatar a resposta agora.', createdAt: new Date().toISOString(), module, actions, brandScore: typeof data.brandCompatibilityScore === 'number' ? data.brandCompatibilityScore : undefined, researchedExternally: Boolean(data.researchedExternally) };
      setMessages((current) => [...current, assistant]);
    } catch {
      setMessages((current) => [...current, { id: `chat-fallback-${Date.now()}`, role: 'assistant', content: `Não consegui consultar a KLIC agora. Mantive seu pedido no contexto de ${activeClient?.name || activeWorkspace.name} para você continuar sem perder o raciocínio.`, createdAt: new Date().toISOString(), module }]);
    } finally { setLoading(false); }
  }, [activeAccount.id, activeCampaign, activeClient, activeWorkspace.id, activeWorkspace.name, aiMemory, approvals, connectedAccounts, contextSnapshot, environmentMode, learnConversationMemory, learningSignals, loading, messages, posts]);

  const clearHistory = React.useCallback(() => setMessages([welcome()]), [welcome]);
  const toggleFavorite = React.useCallback((id: string) => setMessages((current) => current.map((message) => message.id === id ? { ...message, favorite: !message.favorite } : message)), []);
  return <AIChatContext.Provider value={{ messages, loading, sendMessage, clearHistory, toggleFavorite }}>{children}</AIChatContext.Provider>;
}

const AIChatContext = React.createContext<AIChatContextValue | null>(null);
export function useAIChat() { const value = React.useContext(AIChatContext); if (!value) throw new Error('useAIChat deve ser usado dentro de AIChatProvider.'); return value; }
