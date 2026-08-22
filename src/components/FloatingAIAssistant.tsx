import React from 'react';
import {
  Bot,
  BrainCircuit,
  Maximize2,
  Send,
  Sparkles,
  X,
  Target,
  BarChart3,
  GitFork,
  FileText,
  Zap,
  ArrowRight
} from 'lucide-react';
import type { NavigationTab } from '../types';
import { useAIChat } from '../context/AIChatContext';
import { navigationLabel } from '../utils/localization';

interface FloatingAIAssistantProps {
  currentTab: NavigationTab;
  onOpenFullChat: () => void;
  onNavigateTab?: (tab: NavigationTab) => void;
}

const moduleSuggestions: Partial<Record<NavigationTab, string>> = {
  calendar: 'Crie uma legenda otimizada para o próximo agendamento.',
  analytics: 'Explique por que meu alcance variou este mês.',
  studio: 'Gere um post usando a Matriz Criativa.',
  'create-image': 'Remova o fundo e aplique iluminação neon nesta imagem.',
  'create-video': 'Gere legendas animadas no estilo Karaokê.',
  automations: 'Sugira um novo fluxo de captura e WhatsApp.',
  brain: 'Mostre as principais diretrizes de tom de voz da marca.',
};

export function FloatingAIAssistant({
  currentTab,
  onOpenFullChat,
  onNavigateTab,
}: FloatingAIAssistantProps) {
  const { messages, loading, sendMessage } = useAIChat();
  const [open, setOpen] = React.useState(false);
  const [input, setInput] = React.useState('');
  const recent = messages.slice(-4);

  const submit = () => {
    const value = input;
    setInput('');
    void sendMessage(value, currentTab);
  };

  const handleQuickAction = (action: string, navigateTo?: NavigationTab) => {
    if (navigateTo && onNavigateTab) {
      onNavigateTab(navigateTo);
    }
    void sendMessage(action, currentTab);
  };

  return (
    <div className="fixed bottom-5 right-5 z-[70]">
      {open && (
        <section className="mb-3 flex h-[440px] w-[340px] max-h-[calc(100vh-96px)] max-w-[calc(100vw-32px)] flex-col overflow-hidden rounded-xl border border-white/[0.09] bg-[#141b1f] shadow-xl shadow-black/50">
          {/* Header */}
          <header className="flex items-center justify-between border-b border-white/[0.06] p-3.5 bg-[#182126]">
            <div className="flex items-center gap-2">
              <span className="grid h-8 w-8 place-items-center rounded-lg bg-[#ff5c5c]/10 border border-[#ff5c5c]/20">
                <Bot className="h-4 w-4 text-[#ff5c5c]" />
              </span>
              <div>
                <h2 className="text-[11px] font-bold text-white flex items-center gap-1">
                  Copiloto Clicko IA <Sparkles className="h-3 w-3 text-[#ff5c5c]" />
                </h2>
                <p className="text-[8px] text-[#828e93]">
                  Diretor de Mídia Social · Contexto: {navigationLabel[currentTab]}
                </p>
              </div>
            </div>

            <div className="flex gap-1">
              <button
                onClick={onOpenFullChat}
                className="rounded-md p-1.5 text-[#78848a] hover:bg-white/[0.05] hover:text-white"
                title="Abrir Chat do Diretor de IA"
              >
                <Maximize2 className="h-3.5 w-3.5" />
              </button>
              <button
                onClick={() => setOpen(false)}
                className="rounded-md p-1.5 text-[#78848a] hover:bg-white/[0.05] hover:text-white"
                title="Fechar assistente"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          </header>

          {/* Quick Command Shortcuts */}
          <div className="p-2 border-b border-white/[0.05] bg-black/20 flex gap-1 overflow-x-auto custom-scrollbar">
            <button
              onClick={() => handleQuickAction('Abrir Estúdio para criar conteúdo', 'studio')}
              className="px-2 py-1 text-[8px] font-bold rounded bg-[#ff5c5c]/10 text-[#ff5c5c] whitespace-nowrap hover:bg-[#ff5c5c]/20 transition flex items-center gap-1"
            >
              <Target className="h-3 w-3" /> Matriz Criativa
            </button>
            <button
              onClick={() => handleQuickAction('Consultar dados do Brain da Marca', 'brain')}
              className="px-2 py-1 text-[8px] font-bold rounded bg-white/[0.05] text-[#b8c2c6] whitespace-nowrap hover:text-white transition flex items-center gap-1"
            >
              <BrainCircuit className="h-3 w-3" /> Ver Brain
            </button>
            <button
              onClick={() => handleQuickAction('Analisar métricas recentes do Analytics', 'analytics')}
              className="px-2 py-1 text-[8px] font-bold rounded bg-white/[0.05] text-[#b8c2c6] whitespace-nowrap hover:text-white transition flex items-center gap-1"
            >
              <BarChart3 className="h-3 w-3" /> Analytics
            </button>
            <button
              onClick={() => handleQuickAction('Abrir Automações de Lead e WhatsApp', 'automations')}
              className="px-2 py-1 text-[8px] font-bold rounded bg-white/[0.05] text-[#b8c2c6] whitespace-nowrap hover:text-white transition flex items-center gap-1"
            >
              <GitFork className="h-3 w-3" /> Automações
            </button>
          </div>

          {/* Chat Stream */}
          <div className="custom-scrollbar flex-1 space-y-3 overflow-y-auto p-3.5">
            {recent.map((message) => (
              <div
                key={message.id}
                className={`flex ${message.role === 'user' ? 'justify-end' : ''}`}
              >
                <p
                  className={`max-w-[88%] rounded-xl px-3 py-2.5 text-[10px] leading-relaxed ${
                    message.role === 'user'
                      ? 'bg-[#ff5c5c] text-[#14200e] font-medium'
                      : 'bg-black/30 border border-white/[0.06] text-[#cbd2d5]'
                  }`}
                >
                  {message.content}
                </p>
              </div>
            ))}

            {loading && (
              <div className="flex items-center gap-2 text-[9px] text-[#ff5c5c] font-semibold">
                <Sparkles className="h-3.5 w-3.5 animate-pulse" />
                Consultando o Brain & Analisando dados...
              </div>
            )}
          </div>

          {/* Bottom Input Area */}
          <div className="border-t border-white/[0.06] p-3 bg-[#182126]">
            <button
              onClick={() =>
                setInput(
                  moduleSuggestions[currentTab] || 'Como a IA pode otimizar meu trabalho nesta tela?'
                )
              }
              className="mb-2 w-full truncate rounded-lg bg-[#ff5c5c]/[0.08] border border-[#ff5c5c]/20 px-2.5 py-1.5 text-left text-[8px] font-bold text-[#ff5c5c]"
            >
              <BrainCircuit className="mr-1.5 inline h-3 w-3" />
              {moduleSuggestions[currentTab] || 'Pedir sugestão tática para esta tela'}
            </button>

            <div className="flex gap-2">
              <input
                value={input}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter') submit();
                }}
                placeholder="Comande a IA em qualquer tela..."
                className="h-9 min-w-0 flex-1 rounded-xl border border-white/[0.08] bg-black/30 px-3 text-[10px] text-white outline-none focus:border-[#ff5c5c]/40"
              />
              <button
                onClick={submit}
                disabled={!input.trim() || loading}
                className="grid h-9 w-9 place-items-center rounded-xl bg-[#ff5c5c] text-[#14200e] disabled:opacity-35 transition hover:bg-[#9be24d]"
              >
                <Send className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        </section>
      )}

      {/* Floating Toggle Button */}
      <button
        onClick={() => setOpen((value) => !value)}
        className="ml-auto grid h-12 w-12 place-items-center rounded-full border border-[#ff5c5c]/40 bg-[#182126] text-[#ff5c5c] shadow-lg shadow-black/50 transition-colors hover:bg-[#ff5c5c] hover:text-[#14200e]"
        aria-label="Abrir Copiloto de IA"
      >
        <Bot className="h-5 w-5" />
      </button>
    </div>
  );
}
