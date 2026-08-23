import React from 'react';
import {
  BarChart3,
  GitFork,
  Maximize2,
  Send,
  Target,
  X,
} from 'lucide-react';
import type { NavigationTab } from '../types';
import { useAIChat } from '../context/AIChatContext';
import { KlicPlasma } from './KlicPlasma';

interface FloatingAIAssistantProps {
  currentTab: NavigationTab;
  onOpenFullChat: () => void;
  onNavigateTab?: (tab: NavigationTab) => void;
}

const quickActions: Array<{
  label: string;
  prompt: string;
  tab?: NavigationTab;
  icon: React.ComponentType<{ className?: string }>;
}> = [
  {
    label: 'Matriz Criativa',
    prompt: 'Abrir criação e edição de imagem',
    tab: 'create-image',
    icon: Target,
  },
  {
    label: 'Analytics',
    prompt: 'Analisar métricas recentes do Analytics',
    tab: 'analytics',
    icon: BarChart3,
  },
  {
    label: 'Automações',
    prompt: 'Abrir Automações de Lead e WhatsApp',
    tab: 'automations',
    icon: GitFork,
  },
];

export function FloatingAIAssistant({
  currentTab,
  onOpenFullChat,
  onNavigateTab,
}: FloatingAIAssistantProps) {
  const { messages, loading, sendMessage } = useAIChat();
  const [open, setOpen] = React.useState(false);
  const [input, setInput] = React.useState('');
  const inputRef = React.useRef<HTMLTextAreaElement>(null);
  const streamRef = React.useRef<HTMLDivElement>(null);
  const recent = messages.slice(-7);

  React.useEffect(() => {
    if (!open) return;
    const focusTimer = window.setTimeout(() => inputRef.current?.focus(), 220);
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false);
    };
    window.addEventListener('keydown', handleEscape);
    return () => {
      window.clearTimeout(focusTimer);
      window.removeEventListener('keydown', handleEscape);
    };
  }, [open]);

  React.useEffect(() => {
    if (!open) return;
    const stream = streamRef.current;
    if (stream) stream.scrollTop = stream.scrollHeight;
  }, [loading, messages, open]);

  const submit = () => {
    const value = input.trim();
    if (!value || loading) return;
    setInput('');
    void sendMessage(value, currentTab);
  };

  const handleQuickAction = (action: string, navigateTo?: NavigationTab) => {
    if (navigateTo && onNavigateTab) onNavigateTab(navigateTo);
    void sendMessage(action, currentTab);
  };

  const openFullChat = () => {
    setOpen(false);
    onOpenFullChat();
  };

  return (
    <div className={`klic-floating-root ${open ? 'is-open' : ''}`}>
      {open && (
        <section
          id="klic-floating-dialog"
          role="dialog"
          aria-label="Conversa rápida com a KLIC"
          className="klic-floating-panel"
        >
          <header className="klic-floating-header">
            <div className="flex min-w-0 items-center gap-3">
              <KlicPlasma state={loading ? 'processing' : 'idle'} compact />
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <h2 className="text-[13px] font-semibold tracking-[0.08em] text-white">KLIC AI</h2>
                  <span className="klic-floating-live-dot" aria-hidden="true" />
                </div>
                <p className="truncate text-[9px] text-[#69747a]">
                  Inteligência artificial da Clicko.
                </p>
              </div>
            </div>

            <div className="flex shrink-0 items-center gap-1">
              <button
                type="button"
                onClick={openFullChat}
                className="klic-floating-icon-button"
                aria-label="Abrir Klic AI em tela cheia"
                title="Abrir Klic AI"
              >
                <Maximize2 className="h-3.5 w-3.5" />
              </button>
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="klic-floating-icon-button"
                aria-label="Fechar Klic AI"
                title="Fechar"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </header>

          <div className="klic-floating-actions custom-scrollbar" aria-label="Atalhos da KLIC">
            {quickActions.map((action) => {
              const Icon = action.icon;
              return (
                <button
                  key={action.label}
                  type="button"
                  onClick={() => handleQuickAction(action.prompt, action.tab)}
                  disabled={loading}
                >
                  <Icon className="h-3 w-3" />
                  {action.label}
                </button>
              );
            })}
            <button type="button" onClick={openFullChat}>
              Memória da KLIC
            </button>
          </div>

          <div ref={streamRef} className="klic-floating-stream custom-scrollbar" aria-live="polite">
            {recent.map((message) => (
              <div
                key={message.id}
                className={`klic-floating-message ${message.role === 'user' ? 'is-user' : 'is-assistant'}`}
              >
                {message.role === 'assistant' && (
                  <span className="klic-floating-message-mark" aria-hidden="true">
                    <span className="scale-[0.72]"><KlicPlasma state="idle" compact /></span>
                  </span>
                )}
                <div>
                  <p>{message.content}</p>
                  <time>
                    {new Date(message.createdAt).toLocaleTimeString('pt-BR', {
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </time>
                </div>
              </div>
            ))}

            {loading && (
              <div className="klic-floating-thinking">
                <KlicPlasma state="processing" compact />
                <span>A KLIC está organizando a resposta…</span>
              </div>
            )}
          </div>

          <footer className="klic-floating-composer-wrap">
            <div className="klic-floating-composer">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && !event.shiftKey) {
                    event.preventDefault();
                    submit();
                  }
                }}
                rows={1}
                placeholder="Converse com a KLIC…"
                aria-label="Mensagem para a KLIC"
              />
              <button
                type="button"
                onClick={submit}
                disabled={!input.trim() || loading}
                aria-label="Enviar mensagem"
              >
                <Send className="h-4 w-4" />
              </button>
            </div>
          </footer>
        </section>
      )}

      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="klic-floating-trigger"
        aria-label={open ? 'Fechar Klic AI' : 'Abrir Klic AI'}
        aria-expanded={open}
        aria-controls="klic-floating-dialog"
      >
        <KlicPlasma state={loading ? 'processing' : 'idle'} compact />
        <span className="klic-floating-trigger-hint" aria-hidden="true">Como posso ajudar?</span>
      </button>
    </div>
  );
}
