import React from 'react';
import {
  BrainCircuit,
  Edit3,
  Heart,
  Mic,
  MicOff,
  Paperclip,
  Plus,
  Search,
  Send,
  Trash2,
  X,
} from 'lucide-react';
import { useAIChat, type AIChatAttachment } from '../context/AIChatContext';
import { useOperations } from '../context/OperationsContext';
import { useGovernance } from '../context/GovernanceContext';
import { navigationLabel } from '../utils/localization';
import { KlicPlasma, type KlicPlasmaState } from './KlicPlasma';
import { useKlicVoice } from '../hooks/useKlicVoice';
import type { AIChatMessage, AIMemoryCategory, AIMemoryScope, LibraryAsset, NavigationTab } from '../types';

type KlicModeId = 'create' | 'strategy' | 'research' | 'analyze' | 'ideas' | 'post' | 'image' | 'video';

const klicModes: Array<{ id: KlicModeId; label: string; actionId: string }> = [
  { id: 'create', label: 'Criar', actionId: 'create.general' },
  { id: 'strategy', label: 'Estratégia', actionId: 'mode.strategist' },
  { id: 'research', label: 'Pesquisar', actionId: 'mode.explorer' },
  { id: 'analyze', label: 'Analisar', actionId: 'mode.diagnostic' },
  { id: 'ideas', label: 'Ideias', actionId: 'create.ideas' },
  { id: 'post', label: 'Post', actionId: 'create.post' },
  { id: 'image', label: 'Imagem', actionId: 'create.image' },
  { id: 'video', label: 'Vídeo', actionId: 'create.video' },
];

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

const fileToAttachment = (file: File) => new Promise<AIChatAttachment>((resolve, reject) => {
  const reader = new FileReader();
  reader.onload = () => resolve({ name: file.name, type: file.type || 'application/octet-stream', size: file.size, dataUrl: String(reader.result || '') });
  reader.onerror = () => reject(reader.error);
  reader.readAsDataURL(file);
});

const assetTypeForFile = (file: File): LibraryAsset['type'] => {
  if (file.type.startsWith('image/')) return 'image';
  if (file.type.startsWith('video/')) return 'video';
  if (file.type.includes('pdf') || file.type.startsWith('text/')) return 'document';
  return 'upload';
};

export function AIChatView({ onNavigate }: { onNavigate?: (tab: NavigationTab) => void }) {
  const { messages, loading, sendMessage, clearHistory, toggleFavorite } = useAIChat();
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
  const [conversationStartIndex, setConversationStartIndex] = React.useState(messages.length);
  const [sideMode, setSideMode] = React.useState<'history' | 'memory'>('history');
  const [editingId, setEditingId] = React.useState<string | null>(null);
  const [draftValue, setDraftValue] = React.useState('');
  const [newMemory, setNewMemory] = React.useState(false);
  const [mobilePanelOpen, setMobilePanelOpen] = React.useState(false);
  const [attachments, setAttachments] = React.useState<AIChatAttachment[]>([]);
  const fileInputRef = React.useRef<HTMLInputElement>(null);
  const composerInputRef = React.useRef<HTMLTextAreaElement>(null);
  const awaitingVoiceResponseRef = React.useRef(false);
  const isPersonal = environmentMode === 'personal';
  const canManageMemory = isPersonal || currentUser?.role === 'master';
  const visibleMessages = messages.slice(conversationStartIndex).filter((message) => !message.id.startsWith('welcome-'));
  const isInitial = visibleMessages.length === 0;
  const selectedMode = klicModes.find((mode) => mode.id === activeMode) || klicModes[0];

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
    if (!value || loading) return;
    const attachmentNote = attachments.length ? `\n\nReferências anexadas: ${attachments.map((item) => item.name).join(', ')}.` : '';
    setInput('');
    const sentAttachments = attachments;
    setAttachments([]);
    void sendMessage(`${value}${attachmentNote}`, 'ai-chat', selectedMode.actionId, sentAttachments, conversationStartIndex);
  }, [attachments, conversationStartIndex, loading, selectedMode.actionId, sendMessage]);

  const submit = () => submitValue(input);
  const handleVoiceFinal = React.useCallback((transcript: string) => {
    awaitingVoiceResponseRef.current = true;
    setInput(transcript);
    submitValue(transcript);
  }, [submitValue]);
  const handleVoiceInterim = React.useCallback((transcript: string) => setInput(transcript), []);
  const { phase: voicePhase, intensity: voiceIntensity, voiceEnabled, toggleVoice, speak } = useKlicVoice({ onInterim: handleVoiceInterim, onFinal: handleVoiceFinal });
  const plasmaState: KlicPlasmaState = loading ? 'processing' : voicePhase;

  React.useEffect(() => {
    if (!awaitingVoiceResponseRef.current || loading) return;
    const latestAssistant = [...messages].reverse().find((message) => message.role === 'assistant' && !message.id.startsWith('welcome-'));
    if (!latestAssistant) return;
    awaitingVoiceResponseRef.current = false;
    speak(latestAssistant.content);
  }, [loading, messages, speak]);

  const saveEdit = (id: string) => {
    if (draftValue.trim()) updateAIMemory(id, { value: draftValue.trim() });
    setEditingId(null);
  };
  const addMemory = () => {
    if (!draftValue.trim()) return;
    upsertAIMemory({ category: 'preference', label: 'Preferência adicionada', value: draftValue.trim(), scope: 'permanent', confidence: 100, source: 'manual' });
    setDraftValue('');
    setNewMemory(false);
  };

  const addAttachments = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const currentSize = attachments.reduce((total, item) => total + item.size, 0);
    let selectedSize = currentSize;
    const selectedFiles = Array.from(event.target.files || []) as File[];
    const files = selectedFiles.filter((file) => {
      if (file.size > 8 * 1024 * 1024 || selectedSize + file.size > 8 * 1024 * 1024) return false;
      selectedSize += file.size;
      return true;
    }).slice(0, 4 - attachments.length);
    if (!files.length) return;
    const converted = await Promise.all(files.map(fileToAttachment));
    files.forEach((file) => addAsset({
      title: file.name,
      type: assetTypeForFile(file),
      tags: ['anexo', 'klic'],
      campaignId: activeCampaign?.id,
      url: URL.createObjectURL(file),
    }));
    setAttachments((current) => [...current, ...converted].slice(0, 4));
    event.target.value = '';
  };

  const handleAssistantAction = (message: AIChatMessage, action: NonNullable<AIChatMessage['actions']>[number]) => {
    const label = action.label.toLowerCase();
    if (label.includes('salvar') && label.includes('biblioteca')) {
      addAsset({ title: message.content.split('\n')[0].slice(0, 90) || 'Conteúdo criado pela KLIC', type: 'content', tags: ['klic', 'conteúdo'], campaignId: activeCampaign?.id });
      onNavigate?.('library');
      return;
    }
    if (action.tab === 'create-image' || action.tab === 'create-video') {
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
      addPosts([{ id: `post-ai-${Date.now()}`, workspaceId: activeWorkspace.id, title: message.content.split('\n')[0].slice(0, 90) || 'Conteúdo planejado pela KLIC', platform: 'instagram', format: 'post', copy: message.content, hashtags: [], scheduledAt, status: isPersonal ? 'scheduled' : 'draft', author: 'KLIC', createdAt: new Date().toISOString(), campaignId: activeCampaign?.id, clientId: activeClient?.id, contextRevision: contextSnapshot.revision, objective: activeClient?.currentObjective || contextSnapshot.objectives, origin: 'context' }]);
      onNavigate?.('calendar');
      return;
    }
    if (action.tab !== 'ai-chat') {
      onNavigate?.(action.tab);
      return;
    }
    void sendMessage(`Aprofunde e execute: ${action.label}`, 'ai-chat', action.actionId, [], conversationStartIndex);
  };

  return (
    <div className="mx-auto flex h-[calc(100vh-82px)] w-full max-w-[1560px] flex-col px-4 py-3 sm:px-6 lg:px-8 lg:py-5">
      {mobilePanelOpen && (
        <div className="fixed inset-0 z-50">
          <button aria-label="Fechar painel da KLIC" onClick={() => setMobilePanelOpen(false)} className="absolute inset-0 bg-black/70 backdrop-blur-sm" />
          <aside className="absolute inset-y-3 right-3 flex w-[min(380px,calc(100%-24px))] flex-col overflow-hidden rounded-2xl border border-white/[0.08] bg-[#11171a] shadow-2xl shadow-black/50">
            <div className="flex items-center justify-between border-b border-white/[0.06] px-4 py-3">
              <div className="grid grid-cols-2 rounded-xl bg-black/25 p-1">
                <button onClick={() => setSideMode('history')} className={`rounded-lg px-4 py-2 text-[11px] font-semibold transition-colors ${sideMode === 'history' ? 'bg-white/[.07] text-white' : 'text-[#758087] hover:text-white'}`}>Conversas</button>
                <button onClick={() => setSideMode('memory')} className={`rounded-lg px-4 py-2 text-[11px] font-semibold transition-colors ${sideMode === 'memory' ? 'bg-white/[.07] text-white' : 'text-[#758087] hover:text-white'}`}>Memória · {aiMemory.length}</button>
              </div>
              <button onClick={() => setMobilePanelOpen(false)} aria-label="Fechar painel" className="grid h-9 w-9 place-items-center rounded-full text-[#778288] transition-colors hover:bg-white/[0.05] hover:text-white"><X className="h-4 w-4" /></button>
            </div>

            {sideMode === 'history' ? (
              <>
                <div className="custom-scrollbar flex-1 space-y-1 overflow-y-auto p-3">
                  {messages.filter((message) => message.role === 'user').slice().reverse().slice(0, 16).map((message) => (
                    <button key={message.id} onClick={() => { setConversationStartIndex(0); setMobilePanelOpen(false); }} className="w-full rounded-xl px-3 py-3 text-left transition-colors hover:bg-white/[0.04]">
                      <span className="line-clamp-2 text-[12px] leading-relaxed text-[#c0c7ca]">{message.content}</span>
                      <span className="mt-1.5 block text-[9px] uppercase tracking-wider text-[#5f6a70]">{message.module ? navigationLabel[message.module] : 'KLIC'}</span>
                    </button>
                  ))}
                  {!messages.some((message) => message.role === 'user') && <p className="px-3 py-8 text-center text-[12px] text-[#69747a]">Nenhuma conversa iniciada.</p>}
                </div>
                <button onClick={() => { clearHistory(); setConversationStartIndex(1); setMobilePanelOpen(false); }} className="m-3 flex items-center justify-center gap-2 rounded-xl border border-white/[0.06] py-3 text-[11px] text-[#7c878c] transition-colors hover:border-white/[0.12] hover:text-white"><Trash2 className="h-3.5 w-3.5" />Limpar conversas</button>
              </>
            ) : (
              <>
                <div className="border-b border-white/[.05] px-4 py-4">
                  <div className="flex items-center justify-between gap-3">
                    <div><strong className="text-[13px] text-white">Memórias salvas</strong><p className="mt-1 text-[10px] text-[#68747a]">Contexto isolado em {activeWorkspace.name}</p></div>
                    {canManageMemory && <button onClick={() => { setNewMemory(true); setDraftValue(''); }} className="grid h-8 w-8 place-items-center rounded-lg bg-white/[0.04] text-[#8bd132]" aria-label="Adicionar memória"><Plus className="h-4 w-4" /></button>}
                  </div>
                </div>
                <div className="custom-scrollbar flex-1 space-y-2 overflow-y-auto p-3">
                  {newMemory && <div className="rounded-xl border border-[#8bd132]/25 bg-black/20 p-3"><textarea autoFocus value={draftValue} onChange={(event) => setDraftValue(event.target.value)} placeholder="Adicione uma regra ou preferência..." className="min-h-20 w-full resize-none bg-transparent text-[12px] leading-relaxed text-white outline-none" /><div className="mt-2 flex gap-3"><button onClick={addMemory} className="text-[10px] font-semibold text-[#8bd132]">Adicionar</button><button onClick={() => setNewMemory(false)} className="text-[10px] text-[#777]">Cancelar</button></div></div>}
                  {aiMemory.map((memory) => (
                    <article key={memory.id} className="rounded-xl border border-white/[.055] bg-black/15 p-3.5">
                      <div className="flex items-start gap-2">
                        <div className="min-w-0 flex-1">
                          <span className="text-[9px] uppercase tracking-wider text-[#8bd132]">{categoryLabel[memory.category]} · {scopeLabel[memory.scope]}</span>
                          <strong className="mt-1.5 block text-[12px] text-white">{memory.label}</strong>
                          {editingId === memory.id ? <textarea autoFocus value={draftValue} onChange={(event) => setDraftValue(event.target.value)} className="mt-2 min-h-20 w-full resize-none rounded-lg bg-black/30 p-2 text-[11px] text-white outline-none" /> : <p className="mt-1 text-[11px] leading-relaxed text-[#879197]">{memory.value}</p>}
                        </div>
                        {canManageMemory && <div className="flex"><button onClick={() => { setEditingId(memory.id); setDraftValue(memory.value); }} className="p-1.5 text-[#68747a] hover:text-white" aria-label="Editar memória"><Edit3 className="h-3.5 w-3.5" /></button><button onClick={() => deleteAIMemory(memory.id)} className="p-1.5 text-[#68747a] hover:text-red-400" aria-label="Excluir memória"><Trash2 className="h-3.5 w-3.5" /></button></div>}
                      </div>
                      {editingId === memory.id && <div className="mt-2 flex gap-3"><button onClick={() => saveEdit(memory.id)} className="text-[10px] text-[#8bd132]">Salvar</button><button onClick={() => setEditingId(null)} className="text-[10px] text-[#777]">Cancelar</button></div>}
                      <div className="mt-2.5 flex flex-wrap justify-between gap-1 text-[9px] text-[#566269]"><span>{sourceLabel[memory.source]}</span><span>{memory.occurrences} {memory.occurrences === 1 ? 'sinal' : 'sinais'} · {memory.confidence}%</span></div>
                      {!!memory.evolution?.length && <p className="mt-1 text-[9px] text-[#566269]">Evoluiu {memory.evolution.length} {memory.evolution.length === 1 ? 'vez' : 'vezes'}; histórico preservado.</p>}
                    </article>
                  ))}
                </div>
              </>
            )}
          </aside>
        </div>
      )}

      <section className="flex min-h-0 flex-1 flex-col overflow-hidden">
        <header className="mx-auto flex w-full max-w-5xl items-center justify-between gap-4 px-1 pb-4">
          <div className="w-[128px] min-w-0">
            <h1 className="truncate text-left text-[16px] font-semibold leading-5 tracking-[-0.3px] text-white">KLIC AI</h1>
            <p className="mt-0.5 whitespace-nowrap text-left text-[11px] font-normal leading-4 tracking-normal text-[#69747a]">Inteligência artificial da Clicko.</p>
          </div>
          <div className="flex shrink-0 items-center gap-1.5">
            <button onClick={() => { setSideMode('history'); setMobilePanelOpen(true); }} className="flex h-9 items-center gap-2 rounded-full px-3 text-[10px] text-[#7f8a90] transition-colors hover:bg-white/[0.04] hover:text-white"><Search className="h-3.5 w-3.5" /><span className="hidden sm:inline">Conversas</span></button>
            <button onClick={() => { setSideMode('memory'); setMobilePanelOpen(true); }} className="flex h-9 items-center gap-2 rounded-full px-3 text-[10px] text-[#7f8a90] transition-colors hover:bg-white/[0.04] hover:text-[#8bd132]"><BrainCircuit className="h-3.5 w-3.5" /><span className="hidden sm:inline">Memória</span><span className="text-[#8bd132]">{aiMemory.length}</span></button>
          </div>
        </header>

        <div className="custom-scrollbar flex-1 overflow-y-auto px-1 pb-4">
          <div className={`mx-auto flex min-h-full max-w-3xl flex-col space-y-7 py-3 sm:py-5 ${isInitial ? 'justify-center' : 'justify-end'}`}>
            {isInitial ? (
              <div className="flex flex-1 items-center justify-center px-2 text-center">
                <KlicPlasma state={plasmaState} intensity={voiceIntensity} showIdentity={false} onActivate={toggleVoice} />
              </div>
            ) : visibleMessages.map((message) => (
              <div key={message.id} className={`flex gap-3 sm:gap-4 ${message.role === 'user' ? 'justify-end pl-8 sm:pl-20' : 'justify-start pr-2 sm:pr-12'}`}>
                {message.role === 'assistant' && <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center"><span className="scale-[0.88]"><KlicPlasma state="idle" compact /></span></span>}
                <div className={`${message.role === 'user' ? 'max-w-[85%] rounded-2xl rounded-br-md bg-white/[0.065] px-4 py-3 text-white' : 'min-w-0 flex-1 pt-1 text-[#d4dadd]'}`}>
                  <p className="whitespace-pre-wrap text-[13px] leading-[1.75] sm:text-[14px]">{message.content}</p>
                  {message.role === 'assistant' && (message.brandScore !== undefined || message.researchedExternally) && <div className="mt-4 flex flex-wrap gap-2"><span className="rounded-full bg-[#8bd132]/[.08] px-2.5 py-1 text-[9px] font-semibold text-[#8bd132]">Compatibilidade com a marca · {message.brandScore ?? 0}%</span>{message.researchedExternally && <span className="rounded-full bg-white/[.04] px-2.5 py-1 text-[9px] text-[#929ca1]">Pesquisa externa atualizada</span>}</div>}
                  {message.role === 'assistant' && message.actions?.length ? <div className="mt-4 flex flex-wrap gap-2">{message.actions.map((action) => <button key={`${message.id}-${action.label}`} onClick={() => handleAssistantAction(message, action)} className="rounded-full border border-[#8bd132]/20 bg-transparent px-3 py-1.5 text-[10px] font-semibold text-[#8bd132] transition-colors hover:bg-white/[0.04]">{action.label}</button>)}</div> : null}
                  <div className={`mt-2.5 flex items-center gap-3 text-[9px] ${message.role === 'user' ? 'justify-end text-[#7d898f]' : 'text-[#59656b]'}`}><span>{new Date(message.createdAt).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}</span>{message.role === 'assistant' && <button onClick={() => toggleFavorite(message.id)} className="transition-colors hover:text-[#8bd132]" aria-label="Favoritar resposta"><Heart className={`h-3.5 w-3.5 ${message.favorite ? 'fill-[#8bd132] text-[#8bd132]' : ''}`} /></button>}</div>
                </div>
              </div>
            ))}
            {loading && <div className="flex items-center gap-3 pr-2 sm:pr-12"><KlicPlasma state="processing" compact /><span className="text-[11px] text-[#78848a]">A KLIC está cruzando marca, memória, histórico e dados da operação…</span></div>}
          </div>
        </div>

        <div className="shrink-0 px-1 pb-1 pt-1.5">
          <div className="mx-auto max-w-3xl">
            <div className="mb-1.5 grid grid-cols-4 gap-1.5 sm:grid-cols-8" role="listbox" aria-label="Modo da KLIC">
              {klicModes.map((mode) => {
                const selected = activeMode === mode.id;
                return <button key={mode.id} type="button" onClick={() => setActiveMode(mode.id)} role="option" aria-selected={selected} className={`flex h-7 shrink-0 items-center justify-center rounded-lg border px-2.5 text-[9px] transition-colors ${selected ? 'border-white/[0.08] bg-white/[0.075] font-semibold text-white' : 'border-white/[0.025] bg-white/[0.025] text-[#748086] hover:bg-white/[0.045] hover:text-[#b8c1c5]'}`}>{mode.label}</button>;
              })}
            </div>
            {!!attachments.length && <div className="mb-1.5 flex flex-wrap gap-1.5 px-1.5">{attachments.map((attachment) => <span key={`${attachment.name}-${attachment.size}`} className="flex items-center gap-1.5 rounded-full border border-[#8bd132]/20 bg-[#8bd132]/[.05] px-2 py-0.5 text-[8px] text-[#aeb6ba]"><Paperclip className="h-2.5 w-2.5 text-[#8bd132]" />{attachment.name}<button onClick={() => setAttachments((current) => current.filter((item) => item !== attachment))} aria-label={`Remover ${attachment.name}`}><X className="h-2.5 w-2.5" /></button></span>)}</div>}
            <div className="flex items-end gap-1.5 rounded-[18px] border border-white/[.09] bg-[#141b1f] p-1.5 shadow-lg shadow-black/20 transition-colors focus-within:border-[#8bd132]/35">
              <input ref={fileInputRef} type="file" multiple accept="image/*,video/*,.pdf,.txt,.md" onChange={(event) => void addAttachments(event)} className="hidden" />
              <button onClick={() => fileInputRef.current?.click()} disabled={attachments.length >= 4} className="grid h-8 w-8 shrink-0 place-items-center rounded-full text-[#758087] transition-colors hover:bg-white/[.04] hover:text-[#8bd132] disabled:opacity-30" aria-label="Anexar arquivo"><Paperclip className="h-[15px] w-[15px]" /></button>
              <textarea ref={composerInputRef} value={input} onChange={(event) => setInput(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); submit(); } }} rows={1} placeholder={`Modo ${selectedMode.label} · converse com a KLIC…`} className="max-h-[116px] min-h-9 flex-1 resize-none overflow-y-hidden bg-transparent px-1 py-2 text-[12px] leading-5 text-white outline-none placeholder:text-[#59656b] sm:text-[13px]" />
              <button onClick={toggleVoice} disabled={loading} className={`grid h-8 w-8 shrink-0 place-items-center rounded-full transition-all ${voiceEnabled ? 'bg-[#8bd132]/15 text-[#8bd132] ring-1 ring-[#8bd132]/30' : 'text-[#758087] hover:bg-white/[.04] hover:text-[#8bd132]'} disabled:opacity-30`} aria-label={voiceEnabled ? 'Encerrar conversa por voz' : 'Iniciar conversa por voz'} title={voiceEnabled ? 'Encerrar voz' : 'Conversar por voz'}>{voiceEnabled ? <MicOff className="h-[15px] w-[15px]" /> : <Mic className="h-[15px] w-[15px]" />}</button>
              <button onClick={submit} disabled={!input.trim() || loading} className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-[#8bd132] text-[#10150d] transition-transform hover:scale-[1.03] disabled:opacity-30 disabled:hover:scale-100" aria-label="Enviar mensagem"><Send className="h-3.5 w-3.5" /></button>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
