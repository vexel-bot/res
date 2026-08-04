import React from 'react';
import { Bot, BrainCircuit, Clock3, Heart, Lightbulb, Megaphone, Search, Send, Sparkles, Trash2, Users, Building, Video, Layout } from 'lucide-react';
import { useAIChat } from '../context/AIChatContext';
import { useOperations } from '../context/OperationsContext';
import { useGovernance } from '../context/GovernanceContext';
import { navigationLabel } from '../utils/localization';

export function AIChatView() {
  const { messages, loading, sendMessage, clearHistory, toggleFavorite } = useAIChat();
  const { brain, activeCampaign } = useOperations();
  const { environmentMode } = useGovernance();
  const isPersonal = environmentMode === 'personal';
  const [input, setInput] = React.useState('');

  const starters = isPersonal
    ? [
        { icon: Lightbulb, label: 'Legenda', prompt: 'Crie uma legenda chamativa para meu novo post.' },
        { icon: Video, label: 'Roteiro de Vídeo', prompt: 'Gere um roteiro autoral de vídeo curto para meu nicho.' },
        { icon: Search, label: 'Analisar Perfil', prompt: 'Analise meu desempenho no Instagram e sugira melhorias.' },
        { icon: Layout, label: 'Carrossel', prompt: 'Crie a estrutura de um carrossel educativo com 5 slides.' },
      ]
    : [
        { icon: Building, label: 'Análise da Empresa', prompt: 'Analise a empresa e gargalos de mídia da equipe.' },
        { icon: Megaphone, label: 'Campanha Q3', prompt: 'Crie uma estratégia de marketing corporativa para a campanha ativa.' },
        { icon: Users, label: 'Desempenho Equipe', prompt: 'Compare resultados e engajamento por colaborador e departamento.' },
        { icon: Sparkles, label: 'Fila de Aprovações', prompt: 'Sugira melhorias para agilizar o fluxo de aprovação de conteúdo.' },
      ];

  const submit = () => { const value = input; setInput(''); void sendMessage(value, 'ai-chat'); };

  return <div className="mx-auto grid h-[calc(100vh-82px)] w-full max-w-[1500px] grid-cols-1 gap-4 p-5 lg:grid-cols-[260px_minmax(0,1fr)] lg:p-7">
    <aside className="hidden overflow-hidden rounded-xl border border-white/[0.07] bg-[#141b1f] lg:flex lg:flex-col">
      <div className="border-b border-white/[0.06] p-4"><div className="flex items-center gap-2 text-[11px] font-semibold text-white"><Clock3 className="h-4 w-4 text-[#8bd132]" />Histórico</div><p className="mt-1 text-[8px] text-[#758087]">Memória compartilhada com o assistente flutuante.</p></div>
      <div className="custom-scrollbar flex-1 space-y-1 overflow-y-auto p-2">{messages.filter((message) => message.role === 'user').slice().reverse().slice(0, 12).map((message) => <button key={message.id} className="w-full rounded-lg p-3 text-left hover:bg-white/[0.04]"><span className="line-clamp-2 text-[9px] leading-relaxed text-[#b8c0c4]">{message.content}</span><span className="mt-1 block text-[7px] uppercase text-[#5f6a70]">{navigationLabel[message.module]}</span></button>)}</div>
      <button onClick={clearHistory} className="m-3 flex items-center justify-center gap-2 rounded-lg border border-white/[0.06] py-2.5 text-[8px] text-[#7c878c] hover:text-white"><Trash2 className="h-3.5 w-3.5" />Limpar histórico</button>
    </aside>

    <section className="flex min-h-0 flex-col overflow-hidden rounded-xl border border-white/[0.07] bg-[#141b1f]">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-white/[0.06] p-4">
        <div className="flex items-center gap-3">
          <span className="grid h-10 w-10 place-items-center rounded-xl bg-[#8bd132]/10">
            <Bot className="h-5 w-5 text-[#8bd132]" />
          </span>
          <div>
            <h1 className="text-sm font-semibold text-white">
              {isPersonal ? 'Central IA — Assistente do Criador' : 'Central IA — Estrategista Corporativo'}
            </h1>
            <p className="text-[8px] text-[#758087]">
              {isPersonal
                ? 'Assistente individual para criação de conteúdo, roteiros, legendas e análises'
                : 'Inteligência corporativa para campanhas, governança, equipe e múltiplos clientes'}
            </p>
          </div>
        </div>
        <div className="flex gap-2"><span className="flex items-center gap-1.5 rounded-full bg-[#8bd132]/[0.07] px-2.5 py-1.5 text-[8px] text-[#8bd132]"><BrainCircuit className="h-3 w-3" />Memória rev. {brain.revision}</span>{activeCampaign && <span className="max-w-[190px] truncate rounded-full bg-white/[0.04] px-2.5 py-1.5 text-[8px] text-[#aab3b7]">{activeCampaign.name}</span>}</div></header>
      <div className="custom-scrollbar flex-1 overflow-y-auto p-4 md:p-6"><div className="mx-auto max-w-3xl space-y-4">{messages.map((message) => <div key={message.id} className={`group flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}><div className={`max-w-[84%] rounded-2xl px-4 py-3 ${message.role === 'user' ? 'bg-[#8bd132] text-[#14200e]' : 'border border-white/[0.06] bg-black/25 text-[#d7dddf]'}`}><p className="whitespace-pre-wrap text-[10px] leading-relaxed">{message.content}</p><div className={`mt-2 flex items-center justify-between gap-4 text-[7px] ${message.role === 'user' ? 'text-[#28411a]' : 'text-[#637076]'}`}><span>{new Date(message.createdAt).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })} · {navigationLabel[message.module]}</span>{message.role === 'assistant' && <button onClick={() => toggleFavorite(message.id)} aria-label="Favoritar resposta"><Heart className={`h-3 w-3 ${message.favorite ? 'fill-[#8bd132] text-[#8bd132]' : ''}`} /></button>}</div></div></div>)}{loading && <div className="flex items-center gap-2 text-[9px] text-[#8bd132]"><Sparkles className="h-4 w-4 animate-pulse" />Analisando o contexto da plataforma…</div>}</div></div>
      <div className="border-t border-white/[0.06] p-4"><div className="mx-auto max-w-3xl"><div className="mb-3 flex gap-2 overflow-x-auto">{starters.map(({ icon: Icon, label, prompt }) => <button key={label} onClick={() => setInput(prompt)} className="flex shrink-0 items-center gap-1.5 rounded-full border border-white/[0.06] bg-white/[0.025] px-3 py-1.5 text-[8px] text-[#9ea8ad] hover:border-[#8bd132]/25 hover:text-[#8bd132]"><Icon className="h-3 w-3" />{label}</button>)}</div><div className="flex items-end gap-2 rounded-xl border border-white/[0.08] bg-black/25 p-2 focus-within:border-[#8bd132]/30"><textarea value={input} onChange={(event) => setInput(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); submit(); } }} rows={2} placeholder="Converse com a IA usando todo o contexto da sua operação…" className="min-h-10 flex-1 resize-none bg-transparent px-2 py-1.5 text-[10px] text-white outline-none" /><button onClick={submit} disabled={!input.trim() || loading} className="grid h-9 w-9 place-items-center rounded-lg bg-[#8bd132] text-[#14200e] disabled:opacity-35"><Send className="h-4 w-4" /></button></div></div></div>
    </section>
  </div>;
}
