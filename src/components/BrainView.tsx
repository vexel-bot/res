import React from 'react';
import { BrainCircuit, Check, FilePlus2, Link2, Save, ShieldCheck } from 'lucide-react';
import { useOperations } from '../context/OperationsContext';
import type { BrandBrain } from '../types';

const fields: Array<{ key: keyof BrandBrain; label: string; description: string; wide?: boolean }> = [
  { key: 'company', label: 'Empresa', description: 'Quem é a marca, contexto e modelo de negócio', wide: true },
  { key: 'products', label: 'Produtos', description: 'Portfólio e prioridades comerciais' },
  { key: 'services', label: 'Serviços', description: 'Entregas e escopo oferecido' },
  { key: 'visualIdentity', label: 'Identidade visual', description: 'Cores, estética, composição e restrições', wide: true },
  { key: 'toneOfVoice', label: 'Tom de voz', description: 'Personalidade e estilo verbal' },
  { key: 'audience', label: 'Público', description: 'Segmentos e perfil de audiência' },
  { key: 'personas', label: 'Personas', description: 'Papéis, contexto e motivações' },
  { key: 'objectives', label: 'Objetivos', description: 'Resultados estratégicos esperados' },
  { key: 'differentiators', label: 'Diferenciais', description: 'Razões para escolher a marca' },
  { key: 'competitors', label: 'Concorrentes', description: 'Alternativas e referências de mercado' },
  { key: 'objections', label: 'Objeções', description: 'Barreiras à decisão' },
  { key: 'pains', label: 'Dores', description: 'Problemas que precisam ser resolvidos' },
  { key: 'desires', label: 'Desejos', description: 'Transformações buscadas pela audiência' },
  { key: 'faq', label: 'FAQ', description: 'Perguntas e respostas recorrentes', wide: true },
  { key: 'requiredWords', label: 'Palavras obrigatórias', description: 'Termos que devem aparecer' },
  { key: 'forbiddenWords', label: 'Palavras proibidas', description: 'Termos que a IA nunca deve usar' },
  { key: 'history', label: 'Histórico da marca', description: 'Origem, marcos e aprendizados', wide: true },
];

export function BrainView() {
  const { brain, brainCompleteness, updateBrain, addBrainSource } = useOperations();
  const [draft, setDraft] = React.useState(brain);
  const [saved, setSaved] = React.useState(false);
  React.useEffect(() => setDraft(brain), [brain]);
  const save = () => { updateBrain(draft); setSaved(true); window.setTimeout(() => setSaved(false), 1800); };

  return <div className="mx-auto w-full max-w-[1480px] p-6 2xl:p-10">
    <div className="flex flex-wrap items-end justify-between gap-4"><div><div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.24em] text-[#8bd132]"><BrainCircuit className="h-4 w-4" />Memória estratégica persistente</div><h1 className="mt-2 text-2xl font-semibold text-white">Memória da marca</h1><p className="mt-1 text-sm text-[#8f999f]">Fonte única de verdade consultada em toda ação de IA.</p></div><button onClick={save} className="flex items-center gap-2 rounded-lg bg-[#8bd132] px-4 py-2.5 text-[11px] font-bold text-[#14200e]">{saved ? <Check className="h-4 w-4" /> : <Save className="h-4 w-4" />}{saved ? 'Memória atualizada' : 'Salvar nova revisão'}</button></div>
    <div className="mt-5 grid gap-4 xl:grid-cols-[1fr_280px]">
      <section className="grid gap-3 md:grid-cols-2">{fields.map(({ key, label, description, wide }) => <label key={key} className={`rounded-xl border border-white/[0.07] bg-[#182126] p-4 ${wide ? 'md:col-span-2' : ''}`}><span className="text-[11px] font-semibold text-white">{label}</span><span className="mt-0.5 block text-[9px] text-[#78848a]">{description}</span><textarea value={String(draft[key] ?? '')} onChange={(event) => setDraft((current) => ({ ...current, [key]: event.target.value }))} rows={wide ? 3 : 4} className="mt-3 w-full resize-none rounded-lg border border-white/[0.06] bg-black/25 p-3 text-[11px] leading-relaxed text-[#dbe0e2] outline-none focus:border-[#8bd132]/40" /></label>)}</section>
      <aside className="space-y-4">
        <div className="sticky top-24 rounded-xl border border-white/[0.07] bg-[#182126] p-5"><div className="flex items-center justify-between"><span className="text-[11px] font-semibold text-white">Completude</span><span className="text-lg font-semibold text-[#8bd132]">{brainCompleteness}%</span></div><div className="mt-3 h-1.5 overflow-hidden rounded-full bg-white/[0.06]"><div className="h-full bg-[#8bd132]" style={{ width: `${brainCompleteness}%` }} /></div><div className="mt-4 flex items-center gap-2 rounded-lg bg-[#8bd132]/[0.07] p-3 text-[9px] leading-relaxed text-[#b8c0c4]"><ShieldCheck className="h-5 w-5 shrink-0 text-[#8bd132]" />IA vinculada à revisão {brain.revision}. Nenhuma geração acontece sem este contexto.</div><h3 className="mt-5 text-[10px] font-semibold uppercase tracking-[0.16em] text-[#9da6ab]">Fontes conectadas</h3><div className="mt-3 space-y-2">{brain.sourceFiles.map((source) => <div key={source.id} className="flex items-center gap-2 rounded-lg border border-white/[0.05] bg-black/20 p-2.5"><FilePlus2 className="h-4 w-4 text-[#8bd132]" /><span className="min-w-0 truncate text-[9px] text-[#cbd1d4]">{source.name}</span></div>)}</div><button onClick={() => addBrainSource({ id: `source-${Date.now()}`, name: 'Novo material de referência', type: 'document', addedAt: new Date().toISOString() })} className="mt-3 flex w-full items-center justify-center gap-2 rounded-lg border border-dashed border-white/10 py-2.5 text-[9px] text-[#9ba5aa] hover:border-[#8bd132]/35 hover:text-[#8bd132]"><FilePlus2 className="h-4 w-4" />Adicionar arquivo</button><div className="mt-3 flex items-center gap-2 text-[9px] text-[#758087]"><Link2 className="h-3.5 w-3.5" />{brain.sourceLinks.length} link conectado</div></div>
      </aside>
    </div>
  </div>;
}
