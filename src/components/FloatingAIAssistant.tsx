import React from 'react';
import { Bot, BrainCircuit, Maximize2, Send, Sparkles, X } from 'lucide-react';
import type { NavigationTab } from '../types';
import { useAIChat } from '../context/AIChatContext';
import { navigationLabel } from '../utils/localization';

const moduleSuggestions: Partial<Record<NavigationTab, string>> = {
  calendar: 'Crie uma legenda para a próxima publicação.', analytics: 'Explique por que meu alcance mudou.',
  'create-image': 'Melhore o prompt desta imagem.', 'create-video': 'Transforme este roteiro em um vídeo.',
  'create-copy': 'Reescreva este texto para aumentar conversão.', automations: 'Sugira uma automação para este fluxo.',
  templates: 'Qual template combina com meu objetivo?', 'connected-accounts': 'Analise o status das minhas conexões.',
};

export function FloatingAIAssistant({ currentTab, onOpenFullChat }: { currentTab: NavigationTab; onOpenFullChat: () => void }) {
  const { messages, loading, sendMessage } = useAIChat();
  const [open, setOpen] = React.useState(false);
  const [input, setInput] = React.useState('');
  const recent = messages.slice(-4);
  const submit = () => { const value = input; setInput(''); void sendMessage(value, currentTab); };

  return <div className="fixed bottom-5 right-5 z-[70]">
    {open && <section className="mb-3 flex h-[430px] w-[340px] max-w-[calc(100vw-32px)] flex-col overflow-hidden rounded-2xl border border-white/[0.09] bg-[#141b1f] shadow-2xl shadow-black/60">
      <header className="flex items-center justify-between border-b border-white/[0.06] p-3.5"><div className="flex items-center gap-2"><span className="grid h-8 w-8 place-items-center rounded-lg bg-[#8bd132]/10"><Bot className="h-4 w-4 text-[#8bd132]" /></span><div><h2 className="text-[10px] font-semibold text-white">Assistente Clicko</h2><p className="text-[7px] text-[#748087]">Contexto: {navigationLabel[currentTab]}</p></div></div><div className="flex gap-1"><button onClick={onOpenFullChat} className="rounded-md p-1.5 text-[#78848a] hover:bg-white/[0.05] hover:text-white" aria-label="Abrir chat com IA"><Maximize2 className="h-3.5 w-3.5" /></button><button onClick={() => setOpen(false)} className="rounded-md p-1.5 text-[#78848a] hover:bg-white/[0.05] hover:text-white" aria-label="Fechar assistente"><X className="h-3.5 w-3.5" /></button></div></header>
      <div className="custom-scrollbar flex-1 space-y-3 overflow-y-auto p-3.5">{recent.map((message) => <div key={message.id} className={`flex ${message.role === 'user' ? 'justify-end' : ''}`}><p className={`max-w-[88%] rounded-xl px-3 py-2.5 text-[9px] leading-relaxed ${message.role === 'user' ? 'bg-[#8bd132] text-[#14200e]' : 'bg-black/25 text-[#cbd2d5]'}`}>{message.content}</p></div>)}{loading && <div className="flex items-center gap-2 text-[8px] text-[#8bd132]"><Sparkles className="h-3.5 w-3.5 animate-pulse" />Pensando…</div>}</div>
      <div className="border-t border-white/[0.06] p-3"><button onClick={() => setInput(moduleSuggestions[currentTab] || 'Como você pode me ajudar nesta tela?')} className="mb-2 w-full truncate rounded-lg bg-[#8bd132]/[0.06] px-2.5 py-2 text-left text-[8px] text-[#8bd132]"><BrainCircuit className="mr-1.5 inline h-3 w-3" />{moduleSuggestions[currentTab] || 'Pedir uma sugestão contextual'}</button><div className="flex gap-2"><input value={input} onChange={(event) => setInput(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter') submit(); }} placeholder="Pergunte sobre esta tela…" className="h-9 min-w-0 flex-1 rounded-lg border border-white/[0.07] bg-black/25 px-3 text-[9px] text-white outline-none focus:border-[#8bd132]/30" /><button onClick={submit} disabled={!input.trim() || loading} className="grid h-9 w-9 place-items-center rounded-lg bg-[#8bd132] text-[#14200e] disabled:opacity-35"><Send className="h-3.5 w-3.5" /></button></div></div>
    </section>}
    <button onClick={() => setOpen((value) => !value)} className="ml-auto grid h-12 w-12 place-items-center rounded-full border border-[#8bd132]/35 bg-[#182126] text-[#8bd132] shadow-xl shadow-black/50 transition hover:scale-105 hover:bg-[#8bd132] hover:text-[#14200e]" aria-label="Abrir assistente de IA"><Bot className="h-5 w-5" /></button>
  </div>;
}
