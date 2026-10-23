import React from 'react';
import { usePresence } from '../motion/usePresence';
import {
  AudioLines,
  Clock3,
  Maximize2,
  Mic,
  Paperclip,
  Plus,
  Send,
  Settings2,
  Square,
  X,
} from 'lucide-react';
import type { NavigationTab } from '../types';
import { useAIChat, type AIChatAttachment } from '../context/AIChatContext';
import { KlicPlasma, type KlicPlasmaState } from './KlicPlasma';
import { ClickoLoader } from './ClickoLoader';
import { KlicMarkdown } from '../klic/KlicMarkdown';
import { KlicVoiceSession } from '../klic/KlicVoiceSession';
import { useKlicVoice, type KlicVoiceMode } from '../hooks/useKlicVoice';
import { transcriptDisposition } from '../klic/voiceConversation';
import { ATTACHMENT_LIMITS, FILE_ACCEPT, validateFile } from '../klic/conversation';
import { fileToAttachment } from '../klic/attachmentInput';
import { klicModes, type KlicModeId } from '../klic/modes';
import { KLIC_MODULES, type KlicAnalysis } from '../klic/contracts';
import { useKlicClient } from '../klic/useKlicClient';
import { startKlicMessageCycle } from '../utils/klicMessageCycle';
import './FloatingAIAssistant.css';

interface FloatingAIAssistantProps {
  currentTab: NavigationTab;
  onOpenFullChat: () => void;
}

const proactiveMessages = [
  'Posso te ajudar a criar algo novo. O que vamos produzir hoje?',
  'Tem algum conteúdo que você precisa criar? Posso montar a ideia e o texto para você.',
  'Quer transformar uma ideia em um post pronto para publicar?',
  'Posso sugerir algumas ideias de conteúdo para sua marca.',
  'Está sem inspiração? Posso criar algumas ideias para você.',
  'Quer melhorar algum conteúdo que você já criou?',
  'Posso criar uma legenda, roteiro ou conceito visual para você.',
  'Que tal criarmos o próximo conteúdo da sua marca?',
  'Precisa de uma ideia rápida? Me diga o tema e eu faço o resto.',
  'Posso analisar seu conteúdo e sugerir como deixá-lo melhor.',
  'Quer criar um post agora? Posso começar pela ideia.',
  'Tem uma campanha em mente? Posso ajudar a estruturar tudo.',
  'Posso transformar uma ideia simples em um conteúdo completo.',
  'O que sua marca precisa comunicar hoje?',
  'Quer que eu encontre uma oportunidade de conteúdo para você?',
  'Posso criar uma sequência de conteúdos para os próximos dias.',
  'Quer explorar uma ideia diferente para sua marca?',
  'Me dê um tema. Eu transformo em conteúdo.',
  'Posso ajudar a planejar seu próximo conteúdo.',
  'Alguma tarefa de conteúdo pendente? Podemos resolver agora.',
] as const;

const contextualMessages: Partial<Record<NavigationTab, readonly string[]>> = {
  dashboard: ['Quer começar criando o próximo conteúdo da sua marca?'],
  calendar: ['Quer preencher algum espaço do seu calendário com conteúdo?'],
  library: ['Quer reaproveitar algum conteúdo que já está na sua biblioteca?'],
  'create-image': [
    'Quer criar uma imagem para acompanhar esse conteúdo?',
    'Gostou desse conteúdo? Posso criar uma variação.',
  ],
  'create-video': [
    'Tem uma ideia? Posso transformar em um roteiro de vídeo.',
    'Gostou desse conteúdo? Posso criar uma variação.',
  ],
};

const IDLE_MESSAGE_THRESHOLD = 4 * 60_000;
const idleMessage = 'Ainda por aqui? Posso te ajudar com alguma coisa.';

const pickProactiveMessage = (
  tab: NavigationTab,
  shownMessages: Set<string>,
  prioritizeIdleMessage: boolean,
  evidenceMessage?: string,
) => {
  if (evidenceMessage && !shownMessages.has(evidenceMessage)) return evidenceMessage;
  const contextual = contextualMessages[tab] || [];
  if (prioritizeIdleMessage && !shownMessages.has(idleMessage)) return idleMessage;
  let availableContextual = contextual.filter((message) => !shownMessages.has(message));
  let availableGeneral = proactiveMessages.filter((message) => !shownMessages.has(message));

  if (!availableContextual.length && !availableGeneral.length) {
    shownMessages.clear();
    availableContextual = [...contextual];
    availableGeneral = [...proactiveMessages];
  }

  const prioritizeContext = availableContextual.length > 0 && Math.random() < 0.6;
  const source = prioritizeContext || !availableGeneral.length
    ? availableContextual
    : availableGeneral;
  return source[Math.floor(Math.random() * source.length)] || proactiveMessages[0];
};

export function FloatingAIAssistant({
  currentTab,
  onOpenFullChat,
}: FloatingAIAssistantProps) {
  const { chat } = useAIChat();
  const klic = useKlicClient();
  const { messages, loading } = chat;
  const [open, setOpen] = React.useState(false);
  const presence = usePresence(open);
  const [input, setInput] = React.useState('');
  const [activeMode, setActiveMode] = React.useState<KlicModeId>('create');
  React.useEffect(() => {
    const production = () => { setOpen(true); setActiveMode('local-production'); };
    window.addEventListener('clicko:klic-production-open', production);
    return () => window.removeEventListener('clicko:klic-production-open', production);
  }, []);
  const [historyOpen, setHistoryOpen] = React.useState(false);
  const [voiceSettingsOpen, setVoiceSettingsOpen] = React.useState(false);
  const [voiceSessionOpen, setVoiceSessionOpen] = React.useState(false);
  const [attachments, setAttachments] = React.useState<AIChatAttachment[]>([]);
  const [attachmentError, setAttachmentError] = React.useState('');
  const [preparingFiles, setPreparingFiles] = React.useState(false);
  const [showLatest, setShowLatest] = React.useState(false);
  const [proactiveMessage, setProactiveMessage] = React.useState<string>();
  const [proactiveVisible, setProactiveVisible] = React.useState(false);
  const inputRef = React.useRef<HTMLTextAreaElement>(null);
  const fileInputRef = React.useRef<HTMLInputElement>(null);
  const streamRef = React.useRef<HTMLDivElement>(null);
  const voiceSettingsRef = React.useRef<HTMLDivElement>(null);
  const following = React.useRef(true);
  const sendBusy = React.useRef(false);
  const fileBusy = React.useRef(false);
  const attachmentEpoch = React.useRef(0);
  const awaitingVoiceResponse = React.useRef<string | null>(null);
  const failVoiceTurn = React.useRef<(message: string) => void>(() => {});
  const shownProactiveMessagesRef = React.useRef(new Set<string>());
  const contextualInsightRef = React.useRef<string | undefined>(undefined);
  const cycleContextRef = React.useRef({ currentTab, open, loading });
  React.useLayoutEffect(() => { cycleContextRef.current = { currentTab, open, loading }; }, [currentTab, open, loading]);
  const lastUserActivityRef = React.useRef(Date.now());
  const recent = messages.filter(message => !message.id.startsWith('welcome-')).slice(-20);
  const selectedMode = klicModes.find(mode => mode.id === activeMode) || klicModes[0];

  const submitValue = React.useCallback((rawValue: string, fromVoice = false) => {
    const value = rawValue.trim();
    if ((!value && !attachments.length) || loading || fileBusy.current || sendBusy.current) return false;
    const previousAssistantId = [...messages].reverse().find(message => message.role === 'assistant')?.id || '';
    sendBusy.current = true;
    following.current = true;
    setAttachmentError('');
    const sentAttachments = attachments;
    setInput('');
    setAttachments([]);
    if (fromVoice) awaitingVoiceResponse.current = previousAssistantId;
    void chat.send(value, sentAttachments, undefined, selectedMode.actionId).catch(() => {
      setInput(current => current || value);
      setAttachments(current => current.length ? current : sentAttachments);
      if (fromVoice && awaitingVoiceResponse.current !== null) {
        awaitingVoiceResponse.current = null;
        failVoiceTurn.current('Não foi possível obter a resposta da KLIC. Tente novamente.');
      }
    }).finally(() => { sendBusy.current = false; });
    return true;
  }, [attachments, loading, messages, chat.send, selectedMode.actionId]);

  const handleVoiceFinal = React.useCallback((transcript: string, mode: KlicVoiceMode) => {
    setInput(transcript);
    if (transcriptDisposition(mode) === 'draft') { inputRef.current?.focus(); return; }
    submitValue(transcript, true);
  }, [submitValue]);
  const {
    phase: voicePhase, intensity: voiceIntensity, audioSignal, voiceEnabled, voicePaused, voiceMode,
    voiceProfile, voiceSupported, errorMessage: voiceError, failSession,
    startConversation, startDictation, finishDictation, pauseConversation, resumeConversation,
    endConversation, setVoiceProfile, previewVoice, speak,
  } = useKlicVoice({ onInterim: setInput, onFinal: handleVoiceFinal, processing: loading });
  failVoiceTurn.current = failSession;
  const plasmaResponding = messages.at(-1)?.role === 'assistant' && messages.at(-1)?.status === 'streaming' && Boolean(messages.at(-1)?.content);
  const plasmaCompletion = messages.at(-1)?.role === 'assistant' && messages.at(-1)?.status === 'complete' ? messages.at(-1)?.id : undefined;
  const plasmaState: KlicPlasmaState = chat.error || voicePhase === 'error' ? 'error' : loading || voicePhase === 'transcribing' || voicePhase === 'thinking'
    ? 'processing' : voicePhase === 'requesting_permission' ? 'connecting'
      : voicePhase === 'paused' || voicePhase === 'ended' ? 'idle' : voicePhase;
  const voiceStatus = voiceError || (voicePaused ? 'Microfone silenciado'
    : voicePhase === 'listening' ? 'Escutando...'
      : voicePhase === 'transcribing' ? 'Transcrevendo sua fala...'
        : loading || voicePhase === 'thinking' ? 'Pensando na resposta...'
          : voicePhase === 'speaking' ? 'KLIC está falando...'
            : voicePhase === 'requesting_permission' ? 'Preparando microfone...' : 'Pronta para ouvir');

  const closeVoiceSession = React.useCallback(() => {
    awaitingVoiceResponse.current = null;
    setVoiceSessionOpen(false);
    endConversation();
  }, [endConversation]);
  const openVoiceSession = React.useCallback(() => {
    setVoiceSettingsOpen(false);
    setVoiceSessionOpen(true);
    startConversation();
  }, [startConversation]);

  React.useEffect(() => {
    if (awaitingVoiceResponse.current !== null) return;
    endConversation();
    setVoiceSessionOpen(false);
    setInput(''); setAttachments([]); attachmentEpoch.current++;
    following.current = true;
  }, [chat.conversationId, endConversation]);

  React.useEffect(() => {
    if (awaitingVoiceResponse.current === null || loading) return;
    if (chat.error) { awaitingVoiceResponse.current = null; failSession('Não foi possível obter a resposta da KLIC. Tente novamente.'); return; }
    const latestAssistant = [...messages].reverse().find(message => message.role === 'assistant' && !message.id.startsWith('welcome-'));
    if (!latestAssistant || latestAssistant.id === awaitingVoiceResponse.current || latestAssistant.status === 'streaming' || latestAssistant.status === 'pending') return;
    awaitingVoiceResponse.current = null;
    if (latestAssistant.status === 'complete') speak(latestAssistant.content);
    else failSession('A resposta da KLIC foi interrompida. Tente novamente.');
  }, [loading, messages, chat.error, speak, failSession]);

  React.useEffect(() => () => { attachmentEpoch.current++; }, []);
  React.useLayoutEffect(() => {
    const textarea = inputRef.current;
    if (!textarea) return;
    textarea.style.height = '40px';
    const next = Math.min(Math.max(textarea.scrollHeight, 40), 112);
    textarea.style.height = `${next}px`;
    textarea.style.overflowY = textarea.scrollHeight > 112 ? 'auto' : 'hidden';
  }, [input, open]);

  React.useEffect(() => {
    if (!open) return;
    const focusTimer = window.setTimeout(() => inputRef.current?.focus(), 220);
    return () => {
      window.clearTimeout(focusTimer);
    };
  }, [open]);

  React.useEffect(() => {
    if (!open) return;
    const stream = streamRef.current;
    if (stream && following.current) stream.scrollTop = stream.scrollHeight;
  }, [loading, messages, open]);

  React.useEffect(() => {
    if (!voiceSettingsOpen) return;
    const closeOnOutside = (event: MouseEvent) => {
      if (voiceSettingsRef.current && !voiceSettingsRef.current.contains(event.target as Node)) setVoiceSettingsOpen(false);
    };
    document.addEventListener('mousedown', closeOnOutside);
    return () => document.removeEventListener('mousedown', closeOnOutside);
  }, [voiceSettingsOpen]);

  React.useEffect(() => {
    const registerUserActivity = () => {
      lastUserActivityRef.current = Date.now();
    };
    document.addEventListener('focusin', registerUserActivity);
    document.addEventListener('keydown', registerUserActivity);
    document.addEventListener('pointerdown', registerUserActivity);
    return () => {
      document.removeEventListener('focusin', registerUserActivity);
      document.removeEventListener('keydown', registerUserActivity);
      document.removeEventListener('pointerdown', registerUserActivity);
    };
  }, []);

  React.useEffect(() => {
    contextualInsightRef.current = undefined;
    if (!KLIC_MODULES.includes(currentTab)) return;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      void klic.request<KlicAnalysis>('analyze', currentTab, { message: 'Identifique somente prioridades contextuais comprovadas desta tela.' }, controller.signal).then(analysis => {
        const recommendation = analysis.recommendations.find(item => item.destination) || analysis.recommendations[0];
        if (!recommendation || controller.signal.aborted) return;
        const firstSentence = recommendation.text.split(/\.(?:\s|$)/)[0].trim();
        const summary = firstSentence.length > 145 ? `${firstSentence.slice(0, 142).trimEnd()}…` : `${firstSentence}.`;
        contextualInsightRef.current = `${summary} Posso ajudar?`;
      }).catch(() => {
        // Proatividade baseada em dados é opcional; falhas nunca interrompem a tela.
      });
    }, 900);
    return () => { window.clearTimeout(timer); controller.abort(); };
  }, [currentTab, klic.request, klic.scope]);

  React.useEffect(() => {
    const reducedMotion = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    return startKlicMessageCycle({
      schedule: (callback, delay) => window.setTimeout(callback, delay),
      cancel: timer => window.clearTimeout(timer),
      canShow: () => document.visibilityState === 'visible' && !cycleContextRef.current.open && !cycleContextRef.current.loading,
      entryDuration: () => reducedMotion() ? 0 : 240,
      exitDuration: () => reducedMotion() ? 0 : 160,
      show: () => {
        const inactiveFor = Date.now() - lastUserActivityRef.current;
        const nextMessage = pickProactiveMessage(
          cycleContextRef.current.currentTab,
          shownProactiveMessagesRef.current,
          inactiveFor >= IDLE_MESSAGE_THRESHOLD,
          contextualInsightRef.current,
        );
        shownProactiveMessagesRef.current.add(nextMessage);
        setProactiveMessage(nextMessage);
        setProactiveVisible(true);
      },
      hide: () => setProactiveVisible(false),
      clear: () => setProactiveMessage(undefined),
    });
  }, []);

  const submit = () => { submitValue(input); };
  const addAttachments = async (files: FileList | null) => {
    if (!files?.length || fileBusy.current) return;
    const epoch = attachmentEpoch.current;
    const selected = Array.from(files);
    if (fileInputRef.current) fileInputRef.current.value = '';
    try {
      if (attachments.length + selected.length > ATTACHMENT_LIMITS.count) throw new Error(`Envie até ${ATTACHMENT_LIMITS.count} arquivos por mensagem.`);
      selected.forEach(validateFile);
      fileBusy.current = true;
      setPreparingFiles(true);
      const prepared = await Promise.all(selected.map(fileToAttachment));
      if (epoch === attachmentEpoch.current) setAttachments(current => [...current, ...prepared]);
    } catch (error) {
      if (epoch === attachmentEpoch.current) setAttachmentError(error instanceof Error ? error.message : 'Não foi possível anexar o arquivo.');
    } finally {
      fileBusy.current = false;
      if (epoch === attachmentEpoch.current) setPreparingFiles(false);
    }
  };
  const closePanel = () => {
    closeVoiceSession();
    if (voiceMode === 'dictation') finishDictation();
    setHistoryOpen(false);
    setVoiceSettingsOpen(false);
    setOpen(false);
  };
  const openFullChat = () => { closePanel(); onOpenFullChat(); };
  const openConversation = (id: string) => {
    if (loading) return;
    closeVoiceSession();
    setHistoryOpen(false);
    void chat.openConversation(id);
  };
  const newConversation = () => {
    if (loading) return;
    closeVoiceSession();
    chat.newConversation();
    setHistoryOpen(false);
    setInput('');
    setAttachments([]);
    inputRef.current?.focus();
  };
  const toggleDictation = () => {
    if (voiceMode === 'dictation' && voiceEnabled) finishDictation();
    else { setVoiceSettingsOpen(false); startDictation(); }
  };
  const onStreamScroll = () => {
    const stream = streamRef.current;
    if (!stream) return;
    following.current = stream.scrollHeight - stream.scrollTop - stream.clientHeight < 64;
    setShowLatest(!following.current);
  };

  return (
    <div className={`klic-floating-root ${open ? 'is-open' : ''}`}>
      {voiceSessionOpen && <KlicVoiceSession
        phase={plasmaState} status={voiceStatus} intensity={voiceIntensity} audioSignal={audioSignal}
        muted={voicePaused} error={voiceError} profile={voiceProfile} messages={messages}
        onMute={() => voicePaused ? resumeConversation() : pauseConversation()}
        onEnd={closeVoiceSession} onRetry={startConversation}
      />}
      {presence.present && (
        <section
          {...presence.props}
          id="klic-floating-dialog"
          role="dialog"
          aria-label="Conversa rápida com a KLIC"
          className="klic-floating-panel"
        >
          <header className="klic-floating-header">
            <div className="flex min-w-0 items-center gap-3">
              <KlicPlasma state={plasmaState} intensity={voiceIntensity} audioSignal={audioSignal} motionActive={!voiceSessionOpen} responding={plasmaResponding} interacting={Boolean(input.trim())} completionId={plasmaCompletion} scopeKey={chat.conversationId} compact />
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <h2 className="klic-floating-title text-[13px] font-semibold tracking-[0.08em]">KLIC AI</h2>
                  <span className="klic-floating-live-dot" aria-hidden="true" />
                </div>
                <p className="klic-floating-subtitle truncate text-[9px]">
                  Inteligência artificial da Clicko.
                </p>
              </div>
            </div>

            <div className="flex shrink-0 items-center gap-1">
              <button type="button" onClick={newConversation} disabled={loading} className="klic-floating-icon-button" aria-label="Nova conversa" title="Nova conversa"><Plus className="h-4 w-4" /></button>
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
                onClick={closePanel}
                className="klic-floating-icon-button"
                aria-label="Fechar Klic AI"
                title="Fechar"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </header>

          <div className="klic-floating-actions" aria-label="Controles da conversa">
            <button type="button" className={historyOpen ? 'is-active' : ''} onClick={() => setHistoryOpen(value => !value)} aria-pressed={historyOpen}><Clock3 className="h-3.5 w-3.5" /> Conversas</button>
            <label className="klic-floating-mode"><span>Modo</span><select value={activeMode} onChange={event => setActiveMode(event.target.value as KlicModeId)} aria-label="Modo da KLIC" disabled={loading}>{klicModes.map(mode => <option key={mode.id} value={mode.id}>{mode.label}</option>)}</select></label>
          </div>

          {historyOpen ? <div className="klic-floating-history custom-scrollbar">
            {chat.conversations.length ? chat.conversations.map(conversation => <button key={conversation.id} type="button" className={chat.conversationId === conversation.id ? 'is-active' : ''} onClick={() => openConversation(conversation.id)} disabled={loading}><span>{conversation.title || 'Nova conversa'}</span><time>{new Date(conversation.updatedAt).toLocaleDateString('pt-BR')}</time></button>) : <p>Nenhuma conversa anterior.</p>}
          </div> : <div ref={streamRef} className="klic-floating-stream custom-scrollbar" aria-live="polite" onScroll={onStreamScroll}>
            {!recent.length && !loading && <div className="klic-floating-empty"><KlicPlasma state="idle" compact /><strong>Converse com a KLIC</strong><span>Suas ideias e conversas continuam aqui e na aba completa.</span></div>}
            {recent.map((message) => (
              <div
                key={message.id}
                className={`klic-floating-message ${message.role === 'user' ? 'is-user' : 'is-assistant'}`}
              >
                {message.role === 'assistant' && (
                  <span className="klic-floating-message-mark" aria-hidden="true">
                    <span className="klic-floating-message-plasma"><KlicPlasma state={message.status === 'error' ? 'error' : message.status === 'streaming' || message.status === 'pending' ? 'processing' : 'idle'} responding={message.status === 'streaming' && Boolean(message.content)} completionId={message.status === 'complete' ? message.id : undefined} compact /></span>
                  </span>
                )}
                <div>
                  {message.role === 'assistant' ? <KlicMarkdown content={message.content || (message.status === 'streaming' ? 'Respondendo…' : '')} /> : <p>{message.content}</p>}
                  {!!message.attachments?.length && <div className="klic-floating-message-files">{message.attachments.map(file => <span key={file.id}>{file.name}</span>)}</div>}
                  {message.status === 'error' && message.error && <p className="klic-floating-error">{message.error}</p>}
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
                <ClickoLoader size="small" label={chat.phase || 'A KLIC está respondendo'} />
                <span>{chat.phase || 'A KLIC está organizando a resposta…'}</span>
              </div>
            )}
          </div>}
          {showLatest && !historyOpen && <button type="button" className="klic-floating-latest" onClick={() => { const stream = streamRef.current; if (stream) stream.scrollTop = stream.scrollHeight; following.current = true; setShowLatest(false); }}>Ver mensagens recentes ↓</button>}

          <footer className="klic-floating-composer-wrap">
            {(chat.error || attachmentError || (voiceMode === 'dictation' && voiceError)) && <div className="klic-floating-error" role="alert">{attachmentError || chat.error || voiceError}{messages.at(-1)?.status === 'error' && <button type="button" onClick={chat.retry}>Tentar novamente</button>}</div>}
            {preparingFiles && <p className="klic-floating-status"><ClickoLoader size="tiny" label="Preparando anexo" /> Preparando anexo…</p>}
            {voiceMode === 'dictation' && voiceEnabled && <p className="klic-floating-status">{voiceStatus}</p>}
            {!!attachments.length && <div className="klic-floating-attachments">{attachments.map((attachment, index) => <span key={`${attachment.name}-${index}`}>{attachment.name}<button type="button" onClick={() => setAttachments(current => current.filter((_, i) => i !== index))} aria-label={`Remover ${attachment.name}`}><X size={12} /></button></span>)}</div>}
            <div className="klic-floating-composer">
              <input ref={fileInputRef} type="file" accept={FILE_ACCEPT} multiple hidden onChange={event => { void addAttachments(event.target.files); }} />
              <button type="button" className="klic-mini-tool" onClick={() => fileInputRef.current?.click()} disabled={loading || preparingFiles} aria-label="Anexar arquivo" title="Anexar arquivo"><Paperclip className="h-4 w-4" /></button>
              <textarea
                ref={inputRef}
                value={input}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); submit(); } }}
                rows={1}
                placeholder="Converse com a KLIC…"
                aria-label="Mensagem para a KLIC"
              />
              <div ref={voiceSettingsRef} className="klic-floating-voice-settings">
                <button type="button" className="klic-mini-tool" onClick={() => setVoiceSettingsOpen(value => !value)} aria-label="Configurar voz" aria-expanded={voiceSettingsOpen} title="Configurar voz"><Settings2 className="h-4 w-4" /></button>
                {voiceSettingsOpen && <div className="klic-floating-voice-popover"><strong>Voz da KLIC</strong>{(['female', 'male'] as const).map(profile => <div key={profile}><button type="button" className={voiceProfile === profile ? 'is-active' : ''} onClick={() => { setVoiceProfile(profile); setVoiceSettingsOpen(false); }} disabled={voiceEnabled}>{profile === 'female' ? 'Feminina' : 'Masculina'}</button><button type="button" onClick={() => previewVoice(profile)} aria-label={`Ouvir voz ${profile === 'female' ? 'feminina' : 'masculina'}`}>Ouvir</button></div>)}</div>}
              </div>
              <button type="button" className={`klic-mini-tool ${voiceMode === 'dictation' && voiceEnabled ? 'is-listening' : ''}`} onClick={toggleDictation} disabled={!voiceSupported || loading || voiceSessionOpen || voicePhase === 'transcribing'} aria-label={voiceMode === 'dictation' && voiceEnabled ? 'Finalizar ditado' : 'Ditar mensagem'} title="Ditar mensagem"><Mic className="h-4 w-4" /></button>
              <button type="button" className="klic-mini-tool klic-mini-voice" onClick={openVoiceSession} disabled={!voiceSupported || loading || voicePhase === 'transcribing'} aria-label="Iniciar conversa por voz" title="Conversar por voz"><AudioLines className="h-4 w-4" /></button>
              <button
                type="button"
                className="klic-mini-send"
                onClick={loading ? chat.cancel : submit}
                disabled={!loading && ((!input.trim() && !attachments.length) || preparingFiles)}
                aria-label={loading ? 'Interromper resposta' : 'Enviar mensagem'}
              >
                {loading ? <Square className="h-3.5 w-3.5" /> : <Send className="h-4 w-4" />}
              </button>
            </div>
          </footer>
        </section>
      )}

      <button
        type="button"
        onClick={() => {
          if (open) closePanel(); else setOpen(true);
        }}
        className="klic-floating-trigger"
        aria-label={open ? 'Fechar Klic AI' : 'Abrir Klic AI'}
        aria-expanded={open}
        aria-controls="klic-floating-dialog"
      >
          <KlicPlasma appearance="signature" state={plasmaState} intensity={voiceIntensity} audioSignal={audioSignal} motionActive={!voiceSessionOpen} responding={plasmaResponding} interacting={open && Boolean(input.trim())} completionId={plasmaCompletion} scopeKey={chat.conversationId} compact />
        {proactiveMessage && (
          <span className={`klic-floating-trigger-hint${proactiveVisible ? ' is-proactive' : ''}`} aria-hidden="true">{proactiveMessage}</span>
        )}
      </button>
    </div>
  );
}
