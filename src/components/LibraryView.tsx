import React from 'react';
import { klicPageScope, useKlicPageDetails } from '../klic/pageContext';
import {
  CalendarDays, Copy, FileText, Heart, Image, LayoutTemplate, Megaphone, Palette,
  Plus, Search, Share2, Trash2, Upload, Video, X,
} from 'lucide-react';
import { useOperations } from '../context/OperationsContext';
import type { LibraryAsset } from '../types';
import './LibraryView.css';
import { ClickoLoader } from './ClickoLoader';

type LibraryTab = 'files' | 'templates' | 'brand' | 'campaigns' | 'lineage';
type SortMode = 'recent' | 'oldest' | 'name';
type TemplateCategory = 'image' | 'video' | 'copy' | 'campaign' | 'calendar' | 'prompt' | 'brand';

const templateMeta: Record<TemplateCategory, readonly [string, React.ComponentType<{ className?: string }>]> = {
  image: ['Imagem', Image], video: ['Vídeo', Video], copy: ['Texto', FileText], campaign: ['Campanha', Megaphone],
  calendar: ['Calendário', CalendarDays], prompt: ['Comando', LayoutTemplate], brand: ['Identidade visual', Palette],
};

const tabs: Array<{ id: LibraryTab; label: string }> = [
  { id: 'files', label: 'Arquivos' }, { id: 'templates', label: 'Modelos' },
  { id: 'brand', label: 'Marca' }, { id: 'campaigns', label: 'Campanhas' }, { id: 'lineage', label: 'Linhagem' },
];

function humanSize(size?: number) {
  if (!size) return 'Tamanho não informado';
  if (size < 1024 * 1024) return `${Math.max(1, Math.round(size / 1024))} KB`;
  return `${(size / (1024 * 1024)).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} MB`;
}

function templateCategory(asset: LibraryAsset): TemplateCategory {
  const value = asset.tags.find((tag) => tag.startsWith('template:'))?.split(':')[1];
  return value && value in templateMeta ? value as TemplateCategory : 'copy';
}

function fileType(file: File): LibraryAsset['type'] {
  if (file.type.startsWith('image/')) return 'image';
  if (file.type.startsWith('video/')) return 'video';
  if (file.type.includes('pdf') || file.type.startsWith('text/') || /\.(docx?|pdf|txt|md)$/i.test(file.name)) return 'document';
  return 'upload';
}

function AssetPreview({ asset }: { asset: LibraryAsset }) {
  if (asset.url && asset.type === 'video') return <video src={asset.url} muted playsInline preload="metadata" />;
  if (asset.url && asset.type === 'image') return <img src={asset.url} alt={asset.title} />;
  const Icon = asset.type === 'template' ? LayoutTemplate : asset.type === 'video' ? Video : asset.type === 'image' ? Image : FileText;
  return <span className="cx-library-file-placeholder"><Icon /><small>{asset.type === 'template' ? 'Modelo' : asset.mimeType || 'Arquivo'}</small></span>;
}

export function LibraryView({ onOpenStudio }: { onOpenStudio?: () => void }) {
  const { assets, addAsset, updateAsset, removeAsset, activeWorkspace, activeClient } = useOperations();
  const workspaceRef = React.useRef(activeWorkspace.id);
  workspaceRef.current = activeWorkspace.id;
  React.useEffect(() => { workspaceRef.current = activeWorkspace.id; return () => { workspaceRef.current = ''; }; }, [activeWorkspace.id]);
  const fileInput = React.useRef<HTMLInputElement>(null);
  const [activeTab, setActiveTab] = React.useState<LibraryTab>('files');
  const [query, setQuery] = React.useState('');
  const [typeFilter, setTypeFilter] = React.useState<'all' | LibraryAsset['type']>('all');
  const [sortMode, setSortMode] = React.useState<SortMode>('recent');
  const [selectedId, setSelectedId] = React.useState<string>();
  const [toast, setToast] = React.useState('');
  const [templateModalOpen, setTemplateModalOpen] = React.useState(false);
  const [templateName, setTemplateName] = React.useState('');
  const [templateDescription, setTemplateDescription] = React.useState('');
  const [templateKind, setTemplateKind] = React.useState<TemplateCategory>('copy');
  const [pendingDelete, setPendingDelete] = React.useState<LibraryAsset>();
  const [uploading, setUploading] = React.useState(false);
  useKlicPageDetails('library', klicPageScope(activeWorkspace.id, activeClient?.id), {
    view: activeTab, filters: { busca: query, tipo: typeFilter, ordenacao: sortMode },
    selected: selectedId ? { kind: 'arquivo', id: selectedId } : undefined,
  });

  const visibleAssets = React.useMemo(() => {
    const normalized = query.trim().toLocaleLowerCase('pt-BR');
    return assets.filter((asset) => {
      const matchesTab = activeTab === 'files' ? asset.type !== 'template'
        : activeTab === 'templates' ? asset.type === 'template'
        : activeTab === 'brand' ? asset.tags.includes('marca') || asset.tags.includes('brand')
        : activeTab === 'campaigns' ? Boolean(asset.campaignId)
        : Boolean(asset.contentId || asset.campaignId);
      const matchesType = typeFilter === 'all' || asset.type === typeFilter;
      const matchesQuery = !normalized || `${asset.title} ${asset.description || ''} ${asset.tags.join(' ')}`.toLocaleLowerCase('pt-BR').includes(normalized);
      return matchesTab && matchesType && matchesQuery;
    }).sort((a, b) => sortMode === 'name'
      ? a.title.localeCompare(b.title, 'pt-BR')
      : sortMode === 'oldest'
        ? new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime()
        : new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime());
  }, [activeTab, assets, query, sortMode, typeFilter]);

  const selected = visibleAssets.find((asset) => asset.id === selectedId) || visibleAssets[0];

  React.useEffect(() => { setSelectedId(undefined); setPendingDelete(undefined); setTemplateModalOpen(false); setUploading(false); setQuery(''); setTypeFilter('all'); }, [activeWorkspace.id]);

  React.useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(''), 2600);
    return () => window.clearTimeout(timer);
  }, [toast]);

  const uploadFiles = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const workspaceId = activeWorkspace.id;
    const input = event.currentTarget;
    const files = Array.from(input.files || []) as File[];
    if (!files.length) return;
    setUploading(true);
    let added = 0;
    for (const file of files.slice(0, 4)) {
      if (file.size > 3 * 1024 * 1024) {
        setToast(`${file.name} excede o limite de 3 MB para armazenamento local.`);
        continue;
      }
      const dataUrl = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(String(reader.result));
        reader.onerror = () => reject(reader.error);
        reader.readAsDataURL(file);
      }).catch(() => '');
      if (workspaceId !== workspaceRef.current) return;
      if (!dataUrl) continue;
      const asset = addAsset({
        title: file.name.replace(/\.[^.]+$/, ''), type: fileType(file),
        tags: ['upload', file.name.split('.').pop()?.toLocaleLowerCase('pt-BR') || 'arquivo'],
        url: dataUrl, mimeType: file.type || 'application/octet-stream', size: file.size,
      });
      setSelectedId(asset.id);
      added += 1;
    }
    input.value = '';
    setUploading(false);
    if (added) setToast(`${added} ${added === 1 ? 'arquivo adicionado' : 'arquivos adicionados'} à Biblioteca.`);
  };

  const createTemplate = () => {
    if (!templateName.trim()) return;
    const asset = addAsset({
      title: templateName.trim(), type: 'template', description: templateDescription.trim(),
      tags: [`template:${templateKind}`],
    });
    setSelectedId(asset.id);
    setActiveTab('templates');
    setTemplateModalOpen(false);
    setTemplateName(''); setTemplateDescription(''); setTemplateKind('copy');
    setToast('Modelo criado e salvo neste workspace.');
  };

  const duplicate = (asset: LibraryAsset) => {
    const copy = addAsset({
      title: `${asset.title} — cópia`, type: asset.type, tags: asset.tags.filter((tag) => tag !== 'shared'),
      campaignId: asset.campaignId, clientId: asset.clientId, contentId: asset.contentId,
      url: asset.url, description: asset.description, mimeType: asset.mimeType, size: asset.size,
    });
    setSelectedId(copy.id);
    setToast('Cópia criada.');
  };

  const toggleTag = (asset: LibraryAsset, tag: 'favorite' | 'shared') => {
    updateAsset(asset.id, { tags: asset.tags.includes(tag) ? asset.tags.filter((item) => item !== tag) : [...asset.tags, tag] });
  };

  return <section className="cx-library-approved">
    <header>
      <div><h1>Biblioteca</h1><p>Arquivos e modelos salvos no contexto atual, prontos para reutilização.</p></div>
      <input ref={fileInput} type="file" hidden multiple accept="image/*,video/*,.pdf,.txt,.md,.doc,.docx" onChange={uploadFiles} />
      <button className="cx-library-button" disabled={uploading} onClick={() => fileInput.current?.click()}>{uploading ? <ClickoLoader size="tiny" label="Enviando arquivos" /> : <Upload />}{uploading ? 'Enviando…' : 'Adicionar arquivos'}</button>
      <button className="cx-library-button is-primary" onClick={() => setTemplateModalOpen(true)}><Plus />Criar modelo</button>
    </header>
    <nav aria-label="Seções da Biblioteca">{tabs.map((tab) => <button className={activeTab === tab.id ? 'is-active' : ''} onClick={() => { setActiveTab(tab.id); setSelectedId(undefined); }} key={tab.id}>{tab.label}</button>)}</nav>
    <div className="cx-library-toolbar">
      <label><Search /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar por nome, descrição ou etiqueta…" /></label>
      <select value={typeFilter} onChange={(event) => setTypeFilter(event.target.value as typeof typeFilter)} aria-label="Filtrar por tipo"><option value="all">Todos os tipos</option><option value="image">Imagens</option><option value="video">Vídeos</option><option value="document">Documentos</option><option value="content">Conteúdos</option><option value="template">Modelos</option></select>
      <select value={sortMode} onChange={(event) => setSortMode(event.target.value as SortMode)} aria-label="Ordenar Biblioteca"><option value="recent">Mais recentes</option><option value="oldest">Mais antigos</option><option value="name">Nome A–Z</option></select>
    </div>

    {visibleAssets.length ? <div className="cx-library-layout">
      <main>
        <div className="cx-library-section-head"><h2>{tabs.find((tab) => tab.id === activeTab)?.label}</h2><span>{visibleAssets.length} {visibleAssets.length === 1 ? 'item' : 'itens'}</span></div>
        {activeTab === 'templates'
          ? <div className="cx-template-grid">{visibleAssets.map((asset) => { const [label, Icon] = templateMeta[templateCategory(asset)]; return <article key={asset.id} className={selected?.id === asset.id ? 'is-active' : ''} onClick={() => setSelectedId(asset.id)}><div className="cx-template-card-top"><span><Icon /></span><button onClick={(event) => { event.stopPropagation(); toggleTag(asset, 'favorite'); }} aria-label={asset.tags.includes('favorite') ? 'Remover dos favoritos' : 'Favoritar modelo'}><Heart className={asset.tags.includes('favorite') ? 'is-favorite' : ''} /></button></div><small>{label}</small><h3>{asset.title}</h3><p>{asset.description || 'Modelo sem descrição.'}</p><footer><span>Atualizado {new Date(asset.updatedAt).toLocaleDateString('pt-BR')}</span><div><button onClick={(event) => { event.stopPropagation(); duplicate(asset); }} aria-label="Duplicar modelo"><Copy /></button><button onClick={(event) => { event.stopPropagation(); toggleTag(asset, 'shared'); }} aria-label={asset.tags.includes('shared') ? 'Desativar compartilhamento' : 'Compartilhar modelo'}><Share2 className={asset.tags.includes('shared') ? 'is-shared' : ''} /></button></div></footer></article>; })}</div>
          : <div className="cx-library-assets">{visibleAssets.map((asset) => <button className={selected?.id === asset.id ? 'is-active' : ''} onClick={() => setSelectedId(asset.id)} key={asset.id}><AssetPreview asset={asset} /><b>{asset.title}</b><small>{asset.tags.slice(0, 2).join(' · ') || asset.type}</small></button>)}</div>}
      </main>
      {selected && <aside>
        <h2>{selected.title}</h2><p>{selected.description || 'Item salvo na Biblioteca.'}</p>
        <div className="cx-library-preview"><AssetPreview asset={selected} /></div>
        <small>DETALHES</small><KeyValue label="Tipo" value={selected.type} /><KeyValue label="Tamanho" value={humanSize(selected.size)} /><KeyValue label="Atualizado" value={new Date(selected.updatedAt).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })} />
        <small>CONTEXTO</small><KeyValue label="Campanha" value={selected.campaignId || 'Sem campanha'} /><KeyValue label="Etiquetas" value={selected.tags.filter((tag) => !tag.startsWith('template:')).join(', ') || 'Sem etiquetas'} />
        <button className="cx-library-button is-primary is-wide" onClick={onOpenStudio}>Usar na criação</button>
        <button className="cx-library-button is-wide" onClick={() => duplicate(selected)}>Duplicar item</button>
        <button className="cx-delete-asset" onClick={() => setPendingDelete(selected)}><Trash2 />Excluir arquivo</button>
      </aside>}
    </div> : <div className="cx-library-empty"><strong>Nenhum item encontrado</strong><p>{query || typeFilter !== 'all' ? 'Revise a busca ou os filtros aplicados.' : activeTab === 'templates' ? 'Crie o primeiro modelo reutilizável deste workspace.' : 'Adicione arquivos para começar a organizar sua Biblioteca.'}</p><button onClick={() => { if (query || typeFilter !== 'all') { setQuery(''); setTypeFilter('all'); } else if (activeTab === 'templates') setTemplateModalOpen(true); else fileInput.current?.click(); }}>{query || typeFilter !== 'all' ? 'Limpar filtros' : activeTab === 'templates' ? 'Criar modelo' : 'Adicionar arquivo'}</button></div>}

    {templateModalOpen && <div className="cx-library-modal" role="dialog" aria-modal="true" aria-labelledby="new-template-title"><button className="cx-library-modal-backdrop" onClick={() => setTemplateModalOpen(false)} aria-label="Fechar" /><form onSubmit={(event) => { event.preventDefault(); createTemplate(); }}><header><div><h2 id="new-template-title">Novo modelo</h2><p>Salve uma estrutura reutilizável neste workspace.</p></div><button type="button" onClick={() => setTemplateModalOpen(false)} aria-label="Fechar"><X /></button></header><label>Nome<input autoFocus value={templateName} onChange={(event) => setTemplateName(event.target.value)} required maxLength={80} /></label><label>Categoria<select value={templateKind} onChange={(event) => setTemplateKind(event.target.value as TemplateCategory)}>{Object.entries(templateMeta).map(([id, [label]]) => <option key={id} value={id}>{label}</option>)}</select></label><label>Descrição<textarea rows={4} value={templateDescription} onChange={(event) => setTemplateDescription(event.target.value)} maxLength={240} placeholder="Explique quando e como usar este modelo." /></label><footer><button type="button" className="cx-library-button" onClick={() => setTemplateModalOpen(false)}>Cancelar</button><button className="cx-library-button is-primary" type="submit">Salvar modelo</button></footer></form></div>}
    {pendingDelete && <div className="cx-library-modal" role="dialog" aria-modal="true" aria-labelledby="delete-asset-title"><button className="cx-library-modal-backdrop" onClick={() => setPendingDelete(undefined)} aria-label="Cancelar exclusão" /><form onSubmit={(event) => { event.preventDefault(); removeAsset(pendingDelete.id); setPendingDelete(undefined); setSelectedId(undefined); setToast('Item excluído da Biblioteca.'); }}><header><div><h2 id="delete-asset-title">Excluir “{pendingDelete.title}”?</h2><p>O item será removido deste workspace e desvinculado dos conteúdos relacionados.</p></div><button type="button" onClick={() => setPendingDelete(undefined)} aria-label="Fechar"><X /></button></header><footer><button type="button" className="cx-library-button" onClick={() => setPendingDelete(undefined)}>Cancelar</button><button className="cx-library-button is-danger" type="submit">Excluir</button></footer></form></div>}
    {toast && <div className="cx-library-toast" role="status">{toast}</div>}
  </section>;
}

function KeyValue({ label, value }: { label: string; value: string }) {
  return <div className="cx-library-kv"><span>{label}</span><b>{value}</b></div>;
}
