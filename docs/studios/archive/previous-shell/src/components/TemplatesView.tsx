import React from 'react';
import { CalendarDays, Copy, FileText, Heart, Image, LayoutTemplate, Megaphone, Palette, Plus, Search, Share2, Video } from 'lucide-react';
import type { ContentTemplate } from '../types';

const seed: ContentTemplate[] = [
  { id: 'tpl-1', name: 'Carrossel educativo premium', category: 'image', description: 'Estrutura visual de 7 slides para conteúdo educativo.', favorite: true, shared: true, uses: 42, updatedAt: '2026-08-02' },
  { id: 'tpl-2', name: 'Reels com gancho e prova', category: 'video', description: 'Roteiro de vídeo curto com gancho, demonstração e chamada para ação.', favorite: false, shared: true, uses: 31, updatedAt: '2026-08-01' },
  { id: 'tpl-3', name: 'Texto de lançamento', category: 'copy', description: 'Estrutura de texto persuasivo para produtos digitais.', favorite: true, shared: false, uses: 68, updatedAt: '2026-07-31' },
  { id: 'tpl-4', name: 'Campanha multicanal', category: 'campaign', description: 'Plano completo para lançamento em quatro canais.', favorite: false, shared: true, uses: 19, updatedAt: '2026-07-29' },
  { id: 'tpl-5', name: 'Calendário contínuo', category: 'calendar', description: 'Cadência mensal equilibrada por etapa do funil.', favorite: false, shared: false, uses: 24, updatedAt: '2026-07-28' },
  { id: 'tpl-6', name: 'Comando de fotografia editorial', category: 'prompt', description: 'Comando detalhado para imagens consistentes de campanha.', favorite: true, shared: true, uses: 57, updatedAt: '2026-07-25' },
  { id: 'tpl-7', name: 'Identidade Clicko', category: 'brand', description: 'Cores, tipografia, espaçamento e diretrizes da marca.', favorite: true, shared: true, uses: 86, updatedAt: '2026-08-02' },
];

const meta = {
  image: ['Imagem', Image], video: ['Vídeo', Video], copy: ['Texto', FileText], campaign: ['Campanha', Megaphone],
  calendar: ['Calendário', CalendarDays], prompt: ['Comando', LayoutTemplate], brand: ['Identidade visual', Palette],
} as const;

export function TemplatesView() {
  const [templates, setTemplates] = React.useState(seed);
  const [query, setQuery] = React.useState('');
  const [category, setCategory] = React.useState<'all' | ContentTemplate['category']>('all');
  const filtered = templates.filter((template) => (category === 'all' || template.category === category) && `${template.name} ${template.description}`.toLowerCase().includes(query.toLowerCase()));
  const duplicate = (template: ContentTemplate) => setTemplates((current) => [{ ...template, id: `tpl-${Date.now()}`, name: `${template.name} — cópia`, uses: 0, shared: false, updatedAt: new Date().toISOString().slice(0, 10) }, ...current]);
  const toggle = (id: string, field: 'favorite' | 'shared') => setTemplates((current) => current.map((template) => template.id === id ? { ...template, [field]: !template[field] } : template));

  return <div className="clicko-templates-view mx-auto w-full max-w-[1480px] space-y-5 p-6 2xl:p-10">
    <div className="flex flex-wrap items-end justify-between gap-4"><div><p className="text-[10px] uppercase tracking-[0.24em] text-[#ff5c5c]">Biblioteca reutilizável</p><h1 className="mt-2 text-2xl font-semibold text-white">Modelos</h1><p className="mt-1 text-sm text-[#8f999f]">Modelos para imagem, vídeo, textos, campanhas, calendário, comandos e identidade.</p></div><button onClick={() => setTemplates((current) => [{ id: `tpl-${Date.now()}`, name: 'Novo modelo', category: 'copy', description: 'Modelo personalizado pronto para edição.', favorite: false, shared: false, uses: 0, updatedAt: new Date().toISOString().slice(0, 10) }, ...current])} className="flex items-center gap-2 rounded-lg bg-[#ff5c5c] px-4 py-2.5 text-[10px] font-bold text-[#14200e]"><Plus className="h-4 w-4" />Novo modelo</button></div>
    <div className="flex flex-wrap gap-2"><label className="flex h-10 min-w-[260px] flex-1 items-center gap-2 rounded-lg border border-white/[0.07] bg-[#182126] px-3"><Search className="h-4 w-4 text-[#748087]" /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar modelos…" className="w-full bg-transparent text-[10px] text-white outline-none" /></label>{(['all', ...Object.keys(meta)] as const).map((item) => <button key={item} onClick={() => setCategory(item)} className={`rounded-lg px-3 text-[8px] ${category === item ? 'bg-[#ff5c5c] font-bold text-[#14200e]' : 'border border-white/[0.07] bg-[#182126] text-[#9aa4a9]'}`}>{item === 'all' ? 'Todos' : meta[item][0]}</button>)}</div>
    <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">{filtered.map((template) => { const Icon = meta[template.category][1]; return <article key={template.id} className="group rounded-xl border border-white/[0.07] bg-[#182126] p-4 transition hover:border-[#ff5c5c]/25"><div className="flex items-start justify-between"><span className="grid h-10 w-10 place-items-center rounded-lg bg-[#ff5c5c]/[0.07]"><Icon className="h-5 w-5 text-[#ff5c5c]" /></span><button onClick={() => toggle(template.id, 'favorite')} aria-label="Favoritar modelo"><Heart className={`h-4 w-4 ${template.favorite ? 'fill-[#ff5c5c] text-[#ff5c5c]' : 'text-[#657177]'}`} /></button></div><span className="mt-4 block text-[8px] uppercase tracking-[0.14em] text-[#78848a]">{meta[template.category][0]}</span><h2 className="mt-1 text-[11px] font-semibold text-white">{template.name}</h2><p className="mt-2 line-clamp-2 min-h-8 text-[9px] leading-relaxed text-[#8e999e]">{template.description}</p><div className="mt-4 flex items-center justify-between border-t border-white/[0.055] pt-3 text-[8px] text-[#6f7a80]"><span>{template.uses} usos</span><div className="flex gap-1"><button onClick={() => duplicate(template)} title="Duplicar" className="rounded-md p-1.5 hover:bg-white/[0.05] hover:text-white"><Copy className="h-3.5 w-3.5" /></button><button onClick={() => toggle(template.id, 'shared')} title="Compartilhar" className={`rounded-md p-1.5 hover:bg-white/[0.05] ${template.shared ? 'text-[#ff5c5c]' : ''}`}><Share2 className="h-3.5 w-3.5" /></button></div></div></article>; })}</section>
  </div>;
}
