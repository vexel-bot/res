import React from 'react';
import type { AIChatMessage, NavigationTab } from '../types';
import { useOperations } from './OperationsContext';

type AIChatContextValue = {
  messages: AIChatMessage[];
  loading: boolean;
  sendMessage: (content: string, module: NavigationTab) => Promise<void>;
  clearHistory: () => void;
  toggleFavorite: (id: string) => void;
};

const storageKey = 'clicko:ai-chat:history';
const initialMessage: AIChatMessage = {
  id: 'welcome', role: 'assistant', createdAt: new Date().toISOString(),
  content: 'Olá! Sou o assistente da Clicko. Posso ajudar com criação, estratégia, planejamento, análise e automações usando a memória da sua marca.',
  module: 'dashboard',
};

const AIChatContext = React.createContext<AIChatContextValue | null>(null);

export function AIChatProvider({ children }: { children: React.ReactNode }) {
  const { brain, activeCampaign } = useOperations();
  const [messages, setMessages] = React.useState<AIChatMessage[]>(() => {
    try { const saved = localStorage.getItem(storageKey); return saved ? JSON.parse(saved) : [initialMessage]; }
    catch { return [initialMessage]; }
  });
  const [loading, setLoading] = React.useState(false);

  React.useEffect(() => { localStorage.setItem(storageKey, JSON.stringify(messages)); }, [messages]);

  const sendMessage = React.useCallback(async (content: string, module: NavigationTab) => {
    const clean = content.trim();
    if (!clean || loading) return;
    const userMessage: AIChatMessage = { id: `chat-user-${Date.now()}`, role: 'user', content: clean, createdAt: new Date().toISOString(), module };
    setMessages((current) => [...current, userMessage]);
    setLoading(true);
    try {
      const response = await fetch('/api/ai/chat', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: `[Contexto da tela: ${module}] ${clean}`, brainContext: brain, strategyContext: activeCampaign, screenContext: module }),
      });
      const data = await response.json();
      const assistant: AIChatMessage = { id: `chat-ai-${Date.now()}`, role: 'assistant', content: data.reply || 'Preparei a análise, mas não consegui formatar a resposta agora.', createdAt: new Date().toISOString(), module };
      setMessages((current) => [...current, assistant]);
    } catch {
      setMessages((current) => [...current, { id: `chat-fallback-${Date.now()}`, role: 'assistant', content: 'A IA está temporariamente indisponível. Sua mensagem foi mantida no histórico para continuar depois.', createdAt: new Date().toISOString(), module }]);
    } finally { setLoading(false); }
  }, [activeCampaign, brain, loading]);

  const clearHistory = React.useCallback(() => setMessages([initialMessage]), []);
  const toggleFavorite = React.useCallback((id: string) => setMessages((current) => current.map((message) => message.id === id ? { ...message, favorite: !message.favorite } : message)), []);
  return <AIChatContext.Provider value={{ messages, loading, sendMessage, clearHistory, toggleFavorite }}>{children}</AIChatContext.Provider>;
}

export function useAIChat() {
  const value = React.useContext(AIChatContext);
  if (!value) throw new Error('useAIChat deve ser usado dentro de AIChatProvider.');
  return value;
}
