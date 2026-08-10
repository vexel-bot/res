import React from 'react';
import { FileText, FolderArchive, Image, Search, Sparkles, Upload, Video, X } from 'lucide-react';
import { useOperations } from '../context/OperationsContext';
import type { Post, PostFormat } from '../types';

export function LibraryView({ onOpenStudio }: { onOpenStudio?: () => void }) {
  const { assets, posts, campaigns, addAsset, createRepurposeHandoff } = useOperations();
  const [query, setQuery] = React.useState('');
  const [filter, setFilter] = React.useState('all');
  const [repurposePost, setRepurposePost] = React.useState<Post | null>(null);
  const combined = [
    ...assets,
    ...posts.map((post) => ({ ...post, type: 'content' as const, tags: [post.platform, post.format, post.status], updatedAt: post.createdAt })),
    ...campaigns.map((campaign) => ({ ...campaign, title: campaign.name, type: 'campaign' as const, tags: [campaign.status, ...campaign.channels], updatedAt: campaign.updatedAt })),
  ];
  const filtered = combined.filter((asset) => (filter === 'all' || asset.type === filter) && `${asset.title} ${asset.tags.join(' ')}`.toLowerCase().includes(query.toLowerCase()));
  const icon = (type: string) => type === 'video' ? Video : type === 'image' ? Image : type === 'campaign' ? Sparkles : FileText;

  const repurpose = (format: PostFormat) => {
    if (!repurposePost) return;
    createRepurposeHandoff(repurposePost, format);
    setRepurposePost(null);
    onOpenStudio?.();
  };

  return <div className="clicko-content-library mx-auto w-full max-w-[1480px] space-y-5 p-6 2xl:p-10">
    <header className="flex flex-wrap items-end justify-between gap-4"><div><p className="text-[10px] uppercase tracking-[0.24em] text-[#ff7a00]">Memória pesquisável</p><h1 className="mt-2 text-2xl font-semibold text-white">Biblioteca</h1><p className="mt-1 text-sm text-[#8f999f]">Encontre, reutilize e transforme o que a operação já produziu.</p></div><button onClick={() => addAsset({ title: 'Novo material enviado', type: 'upload', tags: ['upload'] })} className="flex items-center gap-2 rounded-lg bg-[#ff5c5c] px-4 py-2.5 text-[11px] font-bold text-white"><Upload className="h-4 w-4" />Adicionar material</button></header>
    <div className="flex flex-wrap gap-2"><label className="flex h-10 min-w-[260px] flex-1 items-center gap-2 rounded-lg border border-white/[0.07] bg-[#111] px-3"><Search className="h-4 w-4 text-[#666]" /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar por conteúdo, campanha, tag ou formato..." className="w-full bg-transparent text-[10px] text-white outline-none" /></label>{['all', 'content', 'image', 'video', 'campaign', 'template', 'document'].map((item) => <button key={item} onClick={() => setFilter(item)} className={`rounded-lg px-3 text-[9px] capitalize ${filter === item ? 'bg-[#ff5c5c] font-bold text-white' : 'border border-white/[0.07] bg-[#111] text-[#888]'}`}>{item === 'all' ? 'Todos' : item}</button>)}</div>
    {filtered.length ? <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4">{filtered.map((asset) => { const Icon = icon(asset.type); const post = asset.type === 'content' ? posts.find((item) => item.id === asset.id) : undefined; return <article key={`${asset.type}-${asset.id}`} className="group overflow-hidden rounded-xl border border-white/[0.07] bg-[#111]"><div className="grid h-28 place-items-center bg-black/25">{'url' in asset && asset.url && asset.type === 'image' ? <img src={asset.url} alt="" className="h-full w-full object-cover opacity-75" /> : <Icon className="h-8 w-8 text-[#ff7a00]/65" />}</div><div className="p-4"><div className="flex items-start justify-between gap-2"><h2 className="line-clamp-2 text-[11px] font-medium text-white">{asset.title}</h2><span className="rounded bg-white/[0.05] px-1.5 py-1 text-[7px] uppercase text-[#777]">{asset.type}</span></div><div className="mt-3 flex flex-wrap gap-1">{asset.tags.slice(0, 3).map((tag) => <span key={tag} className="rounded-full bg-[#ff7a00]/[0.07] px-2 py-1 text-[7px] text-[#ff9a3d]">{tag}</span>)}</div>{'campaignId' in asset && asset.campaignId && <div className="mt-3 flex items-center gap-1.5 text-[8px] text-[#666]"><FolderArchive className="h-3 w-3" />Vinculado à campanha</div>}{post && <button onClick={() => setRepurposePost(post)} className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg border border-[#ff5c5c]/20 bg-[#ff5c5c]/[0.05] py-2 text-[8px] font-semibold text-[#ff8a8a]"><Sparkles className="h-3.5 w-3.5" />Reaproveitar conteúdo</button>}</div></article>; })}</section> : <section className="grid min-h-64 place-items-center rounded-xl border border-dashed border-white/[0.08]"><div className="text-center"><Search className="mx-auto h-7 w-7 text-[#555]" /><p className="mt-3 text-[10px] text-[#888]">Nenhum material corresponde aos filtros.</p><button onClick={() => { setQuery(''); setFilter('all'); }} className="mt-3 text-[9px] text-[#ff7a00]">Limpar busca</button></div></section>}

    {repurposePost && <div className="fixed inset-0 z-50 grid place-items-center bg-black/70 p-4 backdrop-blur-sm"><section role="dialog" aria-modal="true" aria-label="Reaproveitar conteúdo" className="w-full max-w-md rounded-2xl border border-white/[0.08] bg-[#111] p-5 shadow-2xl"><div className="flex items-start justify-between gap-3"><div><span className="text-[8px] uppercase tracking-[0.16em] text-[#ff7a00]">Content Repurposing</span><h2 className="mt-1 text-base font-semibold text-white">Transformar sem recomeçar.</h2><p className="mt-2 text-[9px] leading-relaxed text-[#888]">O Studio receberá a mensagem, campanha e contexto de “{repurposePost.title}”.</p></div><button onClick={() => setRepurposePost(null)} aria-label="Fechar reaproveitamento" className="grid h-7 w-7 place-items-center rounded-lg text-[#777]"><X className="h-4 w-4" /></button></div><div className="mt-5 grid grid-cols-2 gap-2">{([['reels', 'Reels / cortes'], ['story', 'Stories'], ['carousel', 'Carrossel'], ['post', 'Nova publicação']] as Array<[PostFormat, string]>).map(([format, label]) => <button key={format} onClick={() => repurpose(format)} className="clicko-interactive-surface rounded-xl border border-white/[0.07] bg-black/25 p-4 text-left"><strong className="text-[10px] text-white">{label}</strong><span className="mt-1 block text-[8px] text-[#666]">Abrir no Studio</span></button>)}</div></section></div>}
  </div>;
}
