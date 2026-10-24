import React from 'react';
import {
  AudioLines,
  BrainCircuit,
  Check,
  Copy,
  Edit3,
  Heart,
  Mic,
  Paperclip,
  Plus,
  Search,
  Send,
  Settings2,
  Square,
  Trash2,
  X,
} from 'lucide-react';
import { useAIChat, type AIChatAttachment } from '../context/AIChatContext';
import { useOperations } from '../context/OperationsContext';
import { useGovernance } from '../context/GovernanceContext';
import { ATTACHMENT_LIMITS, FILE_ACCEPT, validateFile } from '../klic/conversation';
import { fileToAttachment } from '../klic/attachmentInput';
import { KlicMarkdown } from '../klic/KlicMarkdown';
import { ChatAttachment } from '../klic/ChatAttachment';
import { KlicPlasma, type KlicPlasmaState } from './KlicPlasma';
import { ClickoLoader } from './ClickoLoader';
import { useKlicVoice, type KlicVoiceMode } from '../hooks/useKlicVoice';
import { transcriptDisposition } from '../klic/voiceConversation';
import { KlicVoiceSession } from '../klic/KlicVoiceSession';
import { klicModes, type KlicModeId } from '../klic/modes';
import { useKlicClient } from '../klic/useKlicClient';
import type { AIChatMessage, AIMemoryCategory, AIMemoryScope, NavigationTab } from '../types';

const categoryLabel: Record<AIMemoryCategory, string> = {
  identity: 'Identidade',
  communication: 'Comunicação',
  content: 'Conteúdo',
  visual: 'Identidade visual',
  preference: 'Preferências',
};

const scopeLabel: Record<AIMemoryScope, string> = {
  task: 'Nesta tarefa',
  temporary: 'Temporária',
  recurring: 'Recorrente',
  permanent: 'Regra permanente',
};

const sourceLabel = {
  conversation: 'Aprendida em conversa',
  user: 'Preferência observada',
  approval: 'Aprovações',
  analytics: 'Desempenho',
  manual: 'Adicionada manualmente',
};

export function AIChatView({ onNavigate }: { onNavigate?: (tab: NavigationTab) => void }) {
  const { chat } = useAIChat();
  const klic = useKlicClient();
  const { messages, loading, clearHistory, toggleFavorite } = chat;
  const sendMessage = (content: string, actionId?: string) => chat.send(content, [], undefined, actionId).catch(() => {
    // useConversations already exposes the failure through the visible chat.error state.
  });
  const {
    contextSnapshot,
    activeClient,
    activeCampaign,
    activeWorkspace,
    aiMemory,
    upsertAIMemory,
    updateAIMemory,
    deleteAIMemory,
    addAsset,
    addPosts,
    prepareStudioHandoff,
  } = useOperations();
  const { environmentMode, currentUser } = useGovernance();
  const [input, setInput] = React.useState('');
  const [activeMode, setActiveMode] = React.useState<KlicModeId>('create');
  const [attachmentError, setAttachmentError] = React.useState('');
  const [preparingFiles, setPreparingFiles] = React.useState(false);
  const fileBusy = React.useRef(false);
  const sendBusy = React.useRef(false);
  const attachmentEpoch = React.useRef(0);
  const scrollRef = React.useRef<HTMLDivElement>(null);
  const following = React.useRef(true);
  const [showLatest, setShowLatest] = React.useState(false);
  const [sideMode, setSideMode] = React.useState<'history' | 'memory'>('history');
  const [editingId, setEditingId] = React.useState<string | null>(null);
  const [draftValue, setDraftValue] = React.useState('');
  const [newMemory, setNewMemory] = React.useState(false);
  const [mobilePanelOpen, setMobilePanelOpen] = React.useState(false);
  const [attachments, setAttachments] = React.useState<AIChatAttachment[]>([]);
  const [voiceSettingsOpen, setVoiceSettingsOpen] = React.useState(false);
  const fileInputRef = React.useRef<HTMLInputElement>(null);
  const composerInputRef = React.useRef<HTMLTextAreaElement>(null);
  const voiceSettingsRef = React.useRef<HTMLDivElement>(null);
  const awaitingVoiceResponseRef = React.useRef<string | null>(null);
  const failVoiceTurnRef = React.useRef<(message: string) => void>(() => {});
  const [voiceSessionOpen, setVoiceSessionOpen] = React.useState(false);
  const [copyFeedback, setCopyFeedback] = React.useState<{ id: string; ok: boolean } | null>(null);
  const copyFeedbackTimer = React.useRef<number | null>(null);
  const isPersonal = environmentMode === 'personal';
  const canManageMemory = isPersonal || Boolean(currentUser?.modules.includes('ai-chat'));
  const visibleMessages = messages.filter((message) => !message.id.startsWith('welcome-'));
  const isInitial = visibleMessages.length === 0;
  const [showIdlePlasma, setShowIdlePlasma] = React.useState(true);
  const selectedMode = klicModes.find((mode) => mode.id === activeMode) || klicModes[0];

  React.useEffect(() => () => { attachmentEpoch.current++; }, []);
  React.useEffect(() => {
    if (isInitial) { setShowIdlePlasma(true); return; }
    const timer = window.setTimeout(() => setShowIdlePlasma(false), 280);
    return () => window.clearTimeout(timer);
  }, [isInitial]);
  React.useEffect(() => () => { if (copyFeedbackTimer.current !== null) window.clearTimeout(copyFeedbackTimer.current); }, []);
  React.useEffect(() => { setInput(''); setAttachments([]); attachmentEpoch.current++; following.current=true; }, [chat.conversationId]);
  React.useLayoutEffect(() => { const el=scrollRef.current; if (el && following.current) el.scrollTop=el.scrollHeight; }, [messages]);

  React.useLayoutEffect(() => {
    const textarea = composerInputRef.current;
    if (!textarea) return;
    if (!input) {
      textarea.style.height = '36px';
      textarea.style.overflowY = 'hidden';
      return;
    }
    textarea.style.height = '36px';
    const nextHeight = Math.min(Math.max(textarea.scrollHeight, 36), 116);
    textarea.style.height = `${nextHeight}px`;
    textarea.style.overflowY = textarea.scrollHeight > 116 ? 'auto' : 'hidden';
  }, [input]);

  const submitValue = React.useCallback((rawValue: string) => {
    const value = rawValue.trim();
    if ((!value && !attachments.length) || loading || fileBusy.current || sendBusy.current) return false;
    sendBusy.current=true; following.current=true; setAttachmentError('');
    const sentAttachments=attachments;
    setInput(''); setAttachments([]);
    void chat.send(value, sentAttachments, undefined, selectedMode.actionId).catch(() => {
      setInput(value);
      setAttachments(sentAttachments);
      if (awaitingVoiceResponseRef.current !== null) {
        awaitingVoiceResponseRef.current = null;
        failVoiceTurnRef.current('Não foi possível obter a resposta da KLIC. Tente novamente.');
      }
    }).finally(() => { sendBusy.current=false; });
    return true;
  }, [attachments, loading, chat.send, selectedMode.actionId]);

  const submit = () => submitValue(input);
  const handleVoiceFinal = React.useCallback((transcript: string, mode: KlicVoiceMode) => {
    setInput(transcript);
    if (transcriptDisposition(mode) === 'draft') {
      composerInputRef.current?.focus();
      return;
    }
    const previousAssistantId = [...messages].reverse().find((message) => message.role === 'assistant')?.id || '';
    if (submitValue(transcript)) awaitingVoiceResponseRef.current = previousAssistantId;
  }, [messages, submitValue]);
  const handleVoiceInterim = React.useCallback((transcript: string) => setInput(transcript), []);
  const {
    phase: voicePhase,
    intensity: voiceIntensity,
    audioSignal,
    voiceEnabled,
    voicePaused,
    voiceMode,
    voiceProfile,
    voiceSupported,
    errorMessage: voiceError,
    failSession,
    startConversation,
    startDictation,
    finishDictation,
    pauseConversation,
    resumeConversation,
    endConversation,
    setVoiceProfile,
    previewVoice,
    speak,
  } = useKlicVoice({ onInterim: handleVoiceInterim, onFinal: handleVoiceFinal, processing: loading });
  failVoiceTurnRef.current = failSession;
  const openVoiceSession = React.useCallback(() => {
    setVoiceSettingsOpen(false);
    setVoiceSessionOpen(true);
    startConversation();
  }, [startConversation]);
  const closeVoiceSession = React.useCallback(() => {
    awaitingVoiceResponseRef.current = null;
    setVoiceSessionOpen(false);
    endConversation();
  }, [endConversation]);
  React.useEffect(() => {
    // Creating the first chat for the recorded question must keep voice enabled;
    // explicit chat switches must never carry a microphone/playback session over.
    if (awaitingVoiceResponseRef.current === null) {
      endConversation();
      setVoiceSessionOpen(false);
    }
  }, [chat.conversationId, endConversation]);
  const plasmaResponding = messages.at(-1)?.role === 'assistant' && messages.at(-1)?.status === 'streaming' && Boolean(messages.at(-1)?.content);
  const plasmaCompletion = messages.at(-1)?.role === 'assistant' && messages.at(-1)?.status === 'complete' ? messages.at(-1)?.id : undefined;
  const plasmaState: KlicPlasmaState = chat.error || voicePhase === 'error' ? 'error' : loading || voicePhase === 'transcribing' || voicePhase === 'thinking'
    ? 'processing'
    : voicePhase === 'requesting_permission' ? 'connecting'
      : voicePhase === 'paused' || voicePhase === 'ended' ? 'idle' : voicePhase;
  const voiceStatus = voiceError
    || (voiceEnabled
      ? voicePaused
        ? 'Microfone mutado'
        : voicePhase === 'listening'
          ? 'Escutando...'
          : voicePhase === 'speaking'
            ? 'Falando...'
          : voicePhase === 'transcribing'
            ? 'Transcrevendo sua fala...'
            : loading || voicePhase === 'thinking'
              ? 'Pensando na resposta...'
              : voicePhase === 'requesting_permission'
                ? 'Preparando microfone...'
                : 'Pronto para ouvir'
      : '');

  React.useEffect(() => {
    if (!voiceSettingsOpen) return;
    const closeOnOutside = (event: MouseEvent) => {
      if (voiceSettingsRef.current && !voiceSettingsRef.current.contains(event.target as Node)) setVoiceSettingsOpen(false);
    };
    document.addEventListener('mousedown', closeOnOutside);
    return () => {
      document.removeEventListener('mousedown', closeOnOutside);
    };
  }, [voiceSettingsOpen]);

  React.useEffect(() => {
    if (awaitingVoiceResponseRef.current === null || loading) return;
    if (chat.error) {
      awaitingVoiceResponseRef.current = null;
      failSession('Não foi possível obter a resposta da KLIC. Tente novamente.');
      return;
    }
    const latestAssistant = [...messages].reverse().find((message) => message.role === 'assistant' && !message.id.startsWith('welcome-'));
    if (!latestAssistant || latestAssistant.id === awaitingVoiceResponseRef.current) return;
    if (latestAssistant.status === 'streaming' || latestAssistant.status === 'pending') return;
    awaitingVoiceResponseRef.current = null;
    if (latestAssistant.status !== 'complete') {
      failSession('A resposta da KLIC foi interrompida. Tente novamente.');
      return;
    }
    speak(latestAssistant.content);
  }, [loading, messages, chat.error, speak, failSession]);

  const saveEdit = (id: string) => {
    if (draftValue.trim()) updateAIMemory(id, { value: draftValue.trim() });
    setEditingId(null);
  };
  const copyResponse = async (message: AIChatMessage) => {
    let ok = false;
    try { await navigator.clipboard.writeText(message.content); ok = true; } catch { /* The browser may deny clipboard access. */ }
    setCopyFeedback({ id: message.id, ok });
    if (copyFeedbackTimer.current !== null) window.clearTimeout(copyFeedbackTimer.current);
    copyFeedbackTimer.current = window.setTimeout(() => setCopyFeedback(null), 2400);
  };
  const addMemory = () => {
    if (!draftValue.trim()) return;
    upsertAIMemory({ category: 'preference', label: 'Preferência adicionada', value: draftValue.trim(), scope: 'permanent', confidence: 100, source: 'manual' });
    setDraftValue('');
    setNewMemory(false);
  };

  const addAttachments = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files=Array.from(event.target.files || []); event.target.value='';
    if (fileBusy.current || loading) return;
    fileBusy.current=true; setPreparingFiles(true); setAttachmentError('');
    const epoch=attachmentEpoch.current;
    try {
      if (files.length+attachments.length>ATTACHMENT_LIMITS.count) throw new Error('Selecione no máximo 4 anexos.');
      if (files.reduce((sum,f)=>sum+f.size,0)+attachments.reduce((sum,f)=>sum+f.size,0)>ATTACHMENT_LIMITS.bytes) throw new Error('Os anexos devem somar no máximo 6 MB.');
      files.forEach(validateFile);
      const converted=await Promise.all(files.map(fileToAttachment));
      if (epoch===attachmentEpoch.current) setAttachments(current=>[...current,...converted]);
    } catch(e) { setAttachmentError(e instanceof Error ? e.message : 'Não foi possível preparar o arquivo.'); }
    finally { fileBusy.current=false; setPreparingFiles(false); }
  };

  const handleAssistantAction = async (message: AIChatMessage, action: NonNullable<AIChatMessage['actions']>[number]) => {
    const label = action.label.toLowerCase();
    if (action.requiresConfirmation) {
      // Sensitive and external operations are completed only inside their owning,
      // permission-checked module. A chat button is never authority to execute them.
      onNavigate?.(action.tab);
      return;
    }
    if (action.risk === 'read') {
      onNavigate?.(action.tab);
      return;
    }
    if (action.actionId?.startsWith('radar.format.')) {
      void sendMessage(`Quero transformar esta tendência em ${action.label}. Desenvolva uma abordagem original para a marca e entregue conceito, gancho, estrutura, roteiro ou sequência, cenas e falas quando aplicável, CTA, legenda, sugestões de edição, duração aproximada e adaptação para a rede escolhida. Diferencie dados observados de inferências e não invente métricas.`, action.actionId);
      return;
    }
    if (label.includes('salvar') && label.includes('biblioteca')) {
      addAsset({ title: message.content.split('\n')[0].slice(0, 90) || 'Conteúdo criado pela KLIC', type: 'content', tags: ['klic', 'conteúdo'], campaignId: activeCampaign?.id });
      onNavigate?.('library');
      return;
    }
    if (action.tab === 'create-image' || action.tab === 'create-video') {
      try {
        await klic.request('actions/prepare', 'ai-chat', {
          actionId: 'content.draft.prepare', idempotencyKey: `${message.id}-${action.actionId || action.tab}`,
          input: { title: message.content.split('\n')[0].slice(0, 100) || 'Conteúdo orientado pela KLIC', brief: message.content, destination: action.tab },
        });
      } catch (error) {
        setAttachmentError(error instanceof Error ? error.message : 'Não foi possível preparar o conteúdo.');
        return;
      }
      prepareStudioHandoff({
        source: 'ai', clientId: activeClient?.id, campaignId: activeCampaign?.id,
        objective: activeClient?.currentObjective || contextSnapshot.objectives || 'Transformar a recomendação da KLIC em conteúdo.',
        title: message.content.split('\n')[0].slice(0, 100) || 'Conteúdo orientado pela KLIC',
        angle: message.content.slice(0, 280), hook: message.content.split(/[.!?\n]/)[0],
        cta: 'Continuar a conversa', format: action.tab === 'create-video' ? 'reels' : 'post', funnelStage: 'Criação',
      });
      onNavigate?.(action.tab);
      return;
    }
    if (action.tab === 'calendar') {
      const scheduledAt = new Date(Date.now() + 86_400_000).toISOString();
      let prepared: { resource: { id?: string; title?: string; copy?: string; scheduledAt?: string } };
      try {
        prepared = await klic.request('actions/prepare', 'ai-chat', {
          actionId: 'calendar.draft.prepare', idempotencyKey: `${message.id}-${action.actionId || 'calendar-draft'}`,
          input: { title: message.content.split('\n')[0].slice(0, 90) || 'Conteúdo planejado pela KLIC', copy: message.content, scheduledAt, platform: 'instagram', format: 'post' },
        });
      } catch (error) {
        setAttachmentError(error instanceof Error ? error.message : 'Não foi possível preparar o calendário.');
        return;
      }
      addPosts([{ id: prepared.resource.id || `post-ai-${Date.now()}`, workspaceId: activeWorkspace.id, title: prepared.resource.title || 'Conteúdo planejado pela KLIC', platform: 'instagram', format: 'post', copy: prepared.resource.copy || message.content, hashtags: [], scheduledAt: prepared.resource.scheduledAt || scheduledAt, status: 'draft', author: 'KLIC', createdAt: new Date().toISOString(), campaignId: activeCampaign?.id, clientId: activeClient?.id, contextRevision: contextSnapshot.revision, objective: activeClient?.currentObjective || contextSnapshot.objectives, origin: 'context' }]);
      onNavigate?.('calendar');
      return;
    }
    if (action.tab !== 'ai-chat') {
      onNavigate?.(action.tab);
      return;
    }
    void sendMessage(`Aprofunde e execute: ${action.label}`, action.actionId);
  };

  return (
    <div className="klic-chat-workspace mx-auto flex h-[calc(100dvh-82px)] min-h-[420px] w-full max-w-[1560px] flex-col px-4 py-3 sm:px-6 lg:px-8 lg:py-5">
      {voiceSessionOpen && <KlicVoiceSession phase={plasmaState} status={voiceStatus} intensity={voiceIntensity} audioSignal={audioSignal} muted={voicePaused} error={voiceError} profile={voiceProfile} messages={visibleMessages} onMute={voicePaused ? resumeConversation : pauseConversation} onEnd={closeVoiceSession} onRetry={startConversation} />}
      {mobilePanelOpen && (
        <div className="fixed inset-0 z-50">
          <button aria-label="Fechar painel da KLIC" onClick={() => setMobilePanelOpen(false)} className="absolute inset-0 bg-black/70 backdrop-blur-sm" />
          <aside className="absolute inset-y-3 right-3 flex w-[min(380px,calc(100%-24px))] flex-col overflow-hidden rounded-2xl border border-white/[0.08] bg-[rgba(128,128,128,0.14)] shadow-2xl shadow-black/50">
            <div className="flex items-center justify-between border-b border-white/[0.06] px-4 py-3">
              <div className="grid grid-cols-2 rounded-xl bg-black/25 p-1">
                <button onClick={() => setSideMode('history')} className={`rounded-lg px-4 py-2 text-[11px] font-semibold transition-colors ${sideMode === 'history' ? 'bg-white/[.07] text-white' : 'text-[#808080] hover:text-white'}`}>Conversas</button>
                <button onClick={() => setSideMode('memory')} className={`rounded-lg px-4 py-2 text-[11px] font-semibold transition-colors ${sideMode === 'memory' ? 'bg-white/[.07] text-white' : 'text-[#808080] hover:text-white'}`}>Histórico · {aiMemory.length}</button>
              </div>
              <button onClick={() => setMobilePanelOpen(false)} aria-label="Fechar painel" className="grid h-9 w-9 place-items-center rounded-full text-[#808080] transition-colors hover:bg-white/[0.05] hover:text-white"><X className="h-4 w-4" /></button>
            </div>

            {sideMode === 'history' ? (
              <>
                <div className="custom-scrollbar flex-1 space-y-1 overflow-y-auto p-3">
                  {chat.conversations.map((message) => (
                    <button key={message.id} onClick={() => { endConversation(); void chat.openConversation(message.id); setMobilePanelOpen(false); }} className="w-full rounded-xl px-3 py-3 text-left transition-colors hover:bg-white/[0.04]">
                      <span className="line-clamp-2 text-[12px] leading-relaxed text-[rgba(255,255,255,0.72)]">{message.title}</span>
                      <span className="mt-1.5 block text-[9px] uppercase tracking-wider text-[#808080]">{new Date(message.updatedAt).toLocaleDateString('pt-BR')}</span>
                    </button>
                  ))}
                  {!chat.conversations.length && <p className="px-3 py-8 text-center text-[12px] text-[#808080]">Nenhuma conversa iniciada.</p>}
                </div>
                <button onClick={() => { endConversation(); clearHistory(); setMobilePanelOpen(false); }} className="m-3 flex items-center justify-center gap-2 rounded-xl border border-white/[0.06] py-3 text-[11px] text-[#808080] transition-colors hover:border-white/[0.12] hover:text-white"><Trash2 className="h-3.5 w-3.5" />Limpar conversas</button>
              </>
            ) : (
              <>
                <div className="border-b border-white/[.05] px-4 py-4">
                  <div className="flex items-center justify-between gap-3">
                    <div><strong className="text-[13px] text-white">Memórias salvas</strong><p className="mt-1 text-[10px] text-[#808080]">Contexto isolado em {activeWorkspace.name}</p></div>
                    {canManageMemory && <button onClick={() => { setNewMemory(true); setDraftValue(''); }} className="grid h-8 w-8 place-items-center rounded-lg bg-white/[0.04] text-[#FF7F50]" aria-label="Adicionar memória"><Plus className="h-4 w-4" /></button>}
                  </div>
                </div>
                <div className="custom-scrollbar flex-1 space-y-2 overflow-y-auto p-3">
                  {newMemory && <div className="rounded-xl border border-[#FF7F50]/25 bg-black/20 p-3"><textarea autoFocus value={draftValue} onChange={(event) => setDraftValue(event.target.value)} placeholder="Adicione uma regra ou preferência..." className="min-h-20 w-full resize-none bg-transparent text-[12px] leading-relaxed text-white outline-none" /><div className="mt-2 flex gap-3"><button onClick={addMemory} className="text-[10px] font-semibold text-[#FF7F50]">Adicionar</button><button onClick={() => setNewMemory(false)} className="text-[10px] text-[#808080]">Cancelar</button></div></div>}
                  {aiMemory.map((memory) => (
                    <article key={memory.id} className="rounded-xl border border-white/[.055] bg-black/15 p-3.5">
                      <div className="flex items-start gap-2">
                        <div className="min-w-0 flex-1">
                          <span className="text-[9px] uppercase tracking-wider text-[#FF7F50]">{categoryLabel[memory.category]} · {scopeLabel[memory.scope]}</span>
                          <strong className="mt-1.5 block text-[12px] text-white">{memory.label}</strong>
                          {editingId === memory.id ? <textarea autoFocus value={draftValue} onChange={(event) => setDraftValue(event.target.value)} className="mt-2 min-h-20 w-full resize-none rounded-lg bg-black/30 p-2 text-[11px] text-white outline-none" /> : <p className="mt-1 text-[11px] leading-relaxed text-[#808080]">{memory.value}</p>}
                        </div>
                        {canManageMemory && <div className="flex"><button onClick={() => { setEditingId(memory.id); setDraftValue(memory.value); }} className="p-1.5 text-[#808080] hover:text-white" aria-label="Editar memória"><Edit3 className="h-3.5 w-3.5" /></button><button onClick={() => deleteAIMemory(memory.id)} className="p-1.5 text-[#808080] hover:text-[#FF7F50]" aria-label="Excluir memória"><Trash2 className="h-3.5 w-3.5" /></button></div>}
                      </div>
                      {editingId === memory.id && <div className="mt-2 flex gap-3"><button onClick={() => saveEdit(memory.id)} className="text-[10px] text-[#FF7F50]">Salvar</button><button onClick={() => setEditingId(null)} className="text-[10px] text-[#808080]">Cancelar</button></div>}
                      <div className="mt-2.5 flex flex-wrap justify-between gap-1 text-[9px] text-[#808080]"><span>{sourceLabel[memory.source]}</span><span>{memory.occurrences} {memory.occurrences === 1 ? 'sinal' : 'sinais'} · {memory.confidence}%</span></div>
                      {!!memory.evolution?.length && <p className="mt-1 text-[9px] text-[#808080]">Evoluiu {memory.evolution.length} {memory.evolution.length === 1 ? 'vez' : 'vezes'}; histórico preservado.</p>}
                    </article>
                  ))}
                </div>
              </>
            )}
          </aside>
        </div>
      )}

      <section className="flex min-h-0 flex-1 flex-col overflow-hidden">
        <header className="klic-chat-header mx-auto flex w-full max-w-5xl items-center justify-between gap-4 px-1 pb-4 max-[400px]:flex-wrap">
          <div className="min-w-[164px] shrink-0 max-[400px]:w-full">
            <h1 className="whitespace-nowrap text-left text-[16px] font-semibold leading-[22px] tracking-[-0.3px] text-white">KLIC AI</h1>
            <p className="mt-0.5 whitespace-nowrap text-left text-[11px] font-normal leading-4 tracking-normal text-[#808080]">Inteligência artificial da Clicko.</p>
          </div>
          <div className="flex shrink-0 items-center gap-1.5 max-[400px]:ml-auto">
            <button onClick={() => { endConversation(); chat.newConversation(); }} disabled={loading} aria-label="Nova conversa" className="grid h-9 w-9 place-items-center text-[#808080]"><Plus className="h-4 w-4" /></button>
            <button onClick={() => { setSideMode('history'); setMobilePanelOpen(true); }} className="flex h-9 items-center gap-2 rounded-full px-3 text-[10px] text-[#808080] transition-colors hover:bg-white/[0.04] hover:text-white"><Search className="h-3.5 w-3.5" /><span className="hidden sm:inline">Conversas</span></button>
            <button onClick={() => { setSideMode('memory'); setMobilePanelOpen(true); }} className="flex h-9 items-center gap-2 rounded-full px-3 text-[10px] text-[#808080] transition-colors hover:bg-white/[0.04] hover:text-[#FF7F50]"><BrainCircuit className="h-3.5 w-3.5" /><span className="hidden sm:inline">Histórico</span><span className="text-[#FF7F50]">{aiMemory.length}</span></button>
          </div>
        </header>

        <div ref={scrollRef} onScroll={() => { const el=scrollRef.current!; following.current=el.scrollHeight-el.scrollTop-el.clientHeight<80; setShowLatest(!following.current); }} className="custom-scrollbar flex-1 overflow-y-auto px-1 pb-4">
          <div className={`relative mx-auto flex min-h-full w-full max-w-3xl flex-col space-y-7 py-3 sm:py-5 ${isInitial ? 'justify-center' : 'justify-end'}`}>
            {showIdlePlasma && (
              <div className={`absolute inset-0 flex items-center justify-center px-2 text-center transition-[opacity,transform] duration-[280ms] ${isInitial ? 'opacity-100' : 'pointer-events-none scale-[0.92] opacity-0'}`} aria-hidden={!isInitial}>
                <KlicPlasma appearance="signature" particleInteraction="full" particleSurface="viewport" motionActive={isInitial && !voiceSessionOpen} state={plasmaState} intensity={voiceIntensity} audioSignal={audioSignal} interacting={Boolean(input.trim())} responding={plasmaResponding} completionId={plasmaCompletion} scopeKey={chat.conversationId} showIdentity={false} />
              </div>
            )}
            {!isInitial && visibleMessages.map((message) => (
              <div key={message.id} className={`flex gap-3 sm:gap-4 ${message.role === 'user' ? 'justify-end pl-8 sm:pl-20' : 'justify-start pr-2 sm:pr-12'}`}>
                {message.role === 'assistant' && <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center"><span className="scale-[0.88]"><KlicPlasma state={message.status === 'error' ? 'error' : message.status === 'streaming' || message.status === 'pending' ? 'processing' : message.id === messages.at(-1)?.id ? plasmaState : 'idle'} audioSignal={message.id === messages.at(-1)?.id ? audioSignal : undefined} responding={message.status === 'streaming' && Boolean(message.content)} interacting={message.id === messages.at(-1)?.id && Boolean(input.trim())} intensity={message.id === messages.at(-1)?.id ? voiceIntensity : 0} completionId={message.status === 'complete' ? message.id : undefined} compact /></span></span>}
                <div className={`${message.role === 'user' ? 'max-w-[85%] rounded-2xl rounded-br-md bg-white/[0.065] px-4 py-3 text-white' : 'min-w-0 flex-1 pt-1 text-[rgba(255,255,255,0.88)]'}`}>
                  {message.role === 'assistant' ? <KlicMarkdown content={message.content} /> : <p className="whitespace-pre-wrap break-words text-[13px] leading-[1.75] sm:text-[14px]">{message.content}</p>}
                  {!!message.attachments?.length && <div className="mt-2 flex flex-wrap gap-2">{message.attachments.map(file=><ChatAttachment key={file.id} file={file} conversationId={chat.conversationId!} />)}</div>}
                  {message.error && <p role="status" className="mt-2 text-[12px] text-[#808080]">{message.error}</p>}
                  {message.id===messages.at(-1)?.id && ['error','cancelled'].includes(message.status) && <button onClick={chat.retry} disabled={loading} className="mt-2 text-[12px] text-[#FF7F50]">Tentar novamente</button>}
                  {message.role === 'assistant' && ((message as AIChatMessage).brandScore !== undefined || (message as AIChatMessage).researchedExternally) && <div className="mt-4 flex flex-wrap gap-2">{message.brandScore !== undefined && <span className="rounded-full bg-[#FF7F50]/[.08] px-2.5 py-1 text-[9px] font-semibold text-[#FF7F50]">Compatibilidade com a marca · {message.brandScore}%</span>}{message.researchedExternally && <span className="rounded-full bg-white/[.04] px-2.5 py-1 text-[9px] text-[#808080]">Pesquisa externa atualizada</span>}</div>}
                  {message.role === 'assistant' && (message as AIChatMessage).actions?.length ? <div className="mt-4 flex flex-wrap gap-2">{message.actions.map((action) => <button key={`${message.id}-${action.label}`} onClick={() => { void handleAssistantAction(message, action); }} className="rounded-full border border-[#FF7F50]/20 bg-transparent px-3 py-1.5 text-[10px] font-semibold text-[#FF7F50] transition-colors hover:bg-white/[0.04]">{action.label}</button>)}</div> : null}
                  <div className={`mt-2.5 flex items-center gap-3 text-[9px] ${message.role === 'user' ? 'justify-end text-[#808080]' : 'text-[#808080]'}`}><span>{new Date(message.createdAt).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}</span>{message.role === 'assistant' && message.status === 'complete' && <button onClick={() => void copyResponse(message)} className="transition-colors hover:text-white" aria-label="Copiar resposta" title={copyFeedback?.id === message.id ? copyFeedback.ok ? 'Copiado' : 'Não foi possível copiar' : 'Copiar resposta'}>{copyFeedback?.id === message.id && copyFeedback.ok ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}</button>}{message.role === 'assistant' && <button onClick={() => toggleFavorite(message.id)} className="transition-colors hover:text-[#FF7F50]" aria-label="Favoritar resposta"><Heart className={`h-3.5 w-3.5 ${(message as AIChatMessage).favorite ? 'fill-[#FF7F50] text-[#FF7F50]' : ''}`} /></button>}{copyFeedback?.id === message.id && <span role="status">{copyFeedback.ok ? 'Copiado' : 'Não foi possível copiar'}</span>}</div>
                </div>
              </div>
            ))}
            {loading && <div className="flex items-center gap-3 pr-2 sm:pr-12"><ClickoLoader size="small" label={chat.phase || 'A KLIC está respondendo'} /><span className="text-[11px] text-[#808080]">{chat.phase}</span></div>}
          </div>
        </div>

        <div className="shrink-0 px-1 pb-1 pt-1.5">
          {showLatest && <button onClick={() => { following.current=true; const el=scrollRef.current; if(el)el.scrollTop=el.scrollHeight; setShowLatest(false); }} className="mx-auto block text-[11px] text-[#808080]">Ir para a resposta mais recente</button>}
          {(attachmentError || (chat.error && !messages.at(-1)?.error) || preparingFiles) && <p role="status" className="mx-auto max-w-3xl py-2 text-[11px] text-[#808080]">{preparingFiles && !attachmentError && !chat.error && <ClickoLoader size="tiny" label="Preparando anexos" className="mr-2" />}{attachmentError || chat.error || "Preparando anexos…"}</p>}
          {voiceError && !voiceSessionOpen && <p role="status" className="mx-auto max-w-3xl py-2 text-[11px] text-[#FF7F50]">{voiceError}</p>}
          <div className="mx-auto max-w-3xl">
            <div className="mb-2 flex items-center gap-1.5 overflow-x-auto pb-0.5" role="group" aria-label="Modo da KLIC">
              <span className="shrink-0 pr-1 text-[10px] text-[#808080]">Modo</span>
              {klicModes.map((mode) => {
                const selected = activeMode === mode.id;
                return <button key={mode.id} type="button" onClick={() => setActiveMode(mode.id)} aria-pressed={selected} className={`flex h-7 shrink-0 items-center justify-center rounded-full px-3 text-[10px] transition-colors ${selected ? 'bg-white/[0.09] font-semibold text-white' : 'text-[#808080] hover:bg-white/[0.045] hover:text-[rgba(255,255,255,0.72)]'}`}>{mode.label}</button>;
              })}
            </div>
            {!!attachments.length && <div className="mb-1.5 flex flex-wrap gap-1.5 px-1.5">{attachments.map((attachment) => <span key={`${attachment.name}-${attachment.size}`} className="flex items-center gap-1.5 rounded-full border border-[#FF7F50]/20 bg-[#FF7F50]/[.05] px-2 py-0.5 text-[8px] text-[rgba(255,255,255,0.72)]">{attachment.type.startsWith("image/") && <img src={attachment.dataUrl} alt="" className="h-8 w-8 rounded object-cover" />}<Paperclip className="h-2.5 w-2.5 text-[#FF7F50]" />{attachment.name}<button onClick={() => setAttachments((current) => current.filter((item) => item !== attachment))} aria-label={`Remover ${attachment.name}`}><X className="h-2.5 w-2.5" /></button></span>)}</div>}
            {voiceMode === 'dictation' && voiceEnabled && <p role="status" className="mb-2 px-2 text-[11px] text-[#6EB8F5]">{voiceStatus}{voicePhase === 'listening' ? ' Toque no microfone para concluir o ditado.' : ''}</p>}
            <div className="klic-chat-composer flex items-end gap-1 rounded-[22px] border border-white/[.1] bg-[rgba(128,128,128,0.14)] p-2 shadow-lg shadow-black/20 transition-colors focus-within:border-[#FF7F50]/35 max-[400px]:flex-wrap">
              <input ref={fileInputRef} type="file" multiple accept={FILE_ACCEPT} onChange={(event) => void addAttachments(event)} className="hidden" />
              <button onClick={() => fileInputRef.current?.click()} disabled={attachments.length >= 4 || preparingFiles || loading} className="grid h-8 w-8 shrink-0 place-items-center rounded-full text-[#808080] transition-colors hover:bg-white/[.04] hover:text-[#FF7F50] disabled:opacity-30" aria-label="Anexar arquivo"><Paperclip className="h-[15px] w-[15px]" /></button>
              <textarea ref={composerInputRef} value={input} onChange={(event) => setInput(event.target.value)} maxLength={32000} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); submit(); } }} rows={1} placeholder="Escreva para a KLIC…" aria-label="Mensagem para a KLIC" className="max-h-[116px] min-h-9 min-w-0 flex-1 resize-none overflow-y-hidden bg-transparent px-1 py-2 text-[12px] leading-5 text-white outline-none placeholder:text-[#808080] max-[400px]:basis-[calc(100%-45px)] sm:text-[13px]" />
              <div ref={voiceSettingsRef} className="relative flex shrink-0 items-center gap-0.5 max-[400px]:ml-auto">
                <button
                  type="button"
                  onClick={() => setVoiceSettingsOpen((current) => !current)}
                  className={`grid h-8 w-8 place-items-center rounded-full transition-colors ${voiceSettingsOpen ? 'bg-white/[.055] text-white' : 'text-[#808080] hover:bg-white/[.04] hover:text-white'}`}
                  aria-label={`Configurações da conversa por voz. ${voiceProfile === 'female' ? 'KLIC Feminina' : 'KLIC Masculina'}`}
                  aria-expanded={voiceSettingsOpen}
                >
                  <Settings2 className="h-[14px] w-[14px]" />
                </button>
                {voiceSettingsOpen && (
                  <div role="dialog" aria-label="Configurações da conversa por voz" className="absolute bottom-11 right-0 z-40 w-[248px] rounded-2xl border border-white/[.09] bg-[rgba(18,18,18,.98)] p-3.5 shadow-2xl shadow-black/50 backdrop-blur-xl">
                    <div className="flex items-start justify-between gap-3">
                      <div><strong className="block text-[11px] font-semibold text-white">Voz da KLIC</strong><span className="mt-0.5 block text-[9px] text-[#808080]">Escolha a voz usada nas respostas.</span></div>
                      <button type="button" onClick={() => setVoiceSettingsOpen(false)} className="grid h-6 w-6 shrink-0 place-items-center rounded-md text-[#808080] transition-colors hover:bg-white/[.05] hover:text-white" aria-label="Fechar configurações de voz"><X className="h-3.5 w-3.5" /></button>
                    </div>
                    <div className="mt-3 grid grid-cols-2 gap-1.5">
                      <button type="button" disabled={voiceEnabled} onClick={() => { setVoiceProfile('female'); void previewVoice('female'); }} aria-pressed={voiceProfile === 'female'} className={`h-8 rounded-lg border text-[9px] font-medium transition-colors disabled:opacity-50 ${voiceProfile === 'female' ? 'border-[#FF7F50]/30 bg-[#FF7F50]/10 text-white' : 'border-white/[.055] bg-white/[.02] text-[#808080] hover:text-white'}`}>KLIC Feminina</button>
                      <button type="button" disabled={voiceEnabled} onClick={() => { setVoiceProfile('male'); void previewVoice('male'); }} aria-pressed={voiceProfile === 'male'} className={`h-8 rounded-lg border text-[9px] font-medium transition-colors disabled:opacity-50 ${voiceProfile === 'male' ? 'border-[#FF7F50]/30 bg-[#FF7F50]/10 text-white' : 'border-white/[.055] bg-white/[.02] text-[#808080] hover:text-white'}`}>KLIC Masculina</button>
                    </div>
                    {voiceStatus && <div className="mt-2 flex items-center gap-1.5 text-[8px] text-[#808080]" aria-live="polite"><span className={`h-1.5 w-1.5 rounded-full ${voiceEnabled && !voicePaused ? 'bg-[#FF7F50]' : 'bg-[#808080]'}`} aria-hidden="true" />{voiceStatus}</div>}
                    <p className="mt-1.5 text-[8px] leading-4 text-[#808080]">A escolha permanece salva até você alterá-la.</p>
                    {!voiceSupported && <p className="mt-2 rounded-lg border border-[#FF7F50]/20 bg-[#FF7F50]/[.05] p-2 text-[8px] leading-4 text-[rgba(255,255,255,.72)]">Use um navegador compatível com reconhecimento e síntese de voz.</p>}
                    {voiceError && <p className="mt-2 rounded-lg border border-[#FF7F50]/20 bg-[#FF7F50]/[.05] p-2 text-[8px] leading-4 text-[rgba(255,255,255,.72)]" role="status">{voiceError}</p>}
                  </div>
                )}
                <button onClick={() => {
                  if (voiceMode === 'dictation' && voiceEnabled) finishDictation();
                  else startDictation();
                }} disabled={!voiceSupported || loading || (voiceEnabled && (voiceMode !== 'dictation' || voicePhase !== 'listening'))} className={`grid h-8 w-8 place-items-center rounded-full transition-all ${voiceMode === 'dictation' && voiceEnabled ? 'bg-[#6EB8F5]/15 text-[#6EB8F5] ring-1 ring-[#6EB8F5]/30' : 'text-[#808080] hover:bg-white/[.04] hover:text-[#6EB8F5]'} disabled:opacity-30`} aria-label={voiceMode === 'dictation' && voiceEnabled ? 'Concluir ditado' : 'Ditar mensagem'} title={voiceMode === 'dictation' && voiceEnabled ? 'Concluir ditado' : 'Ditar mensagem'}>{voiceMode === 'dictation' && voiceEnabled ? <Square className="h-[11px] w-[11px]" /> : <Mic className="h-[15px] w-[15px]" />}</button>
              </div>
              <button type="button" onClick={openVoiceSession} disabled={!voiceSupported || loading || (voiceEnabled && voiceMode === 'dictation')} className="grid h-8 w-8 shrink-0 place-items-center rounded-full text-[#6EB8F5] transition-colors hover:bg-[#6EB8F5]/[.09] disabled:opacity-30" aria-label="Iniciar conversa por voz" title="Conversa por voz"><AudioLines className="h-[16px] w-[16px]" /></button>
              <button onClick={loading ? chat.cancel : submit} disabled={!loading && ((!input.trim() && !attachments.length) || preparingFiles)} className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-[#FF7F50] text-[#000000] transition-transform hover:scale-[1.03] disabled:opacity-30 disabled:hover:scale-100" aria-label={loading ? "Interromper resposta" : "Enviar mensagem"}>{loading ? <Square className="h-3.5 w-3.5" /> : <Send className="h-3.5 w-3.5" />}</button>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
