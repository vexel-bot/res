import React from 'react';
import { CalendarDays, Copy, FileText, Heart, Image, LayoutTemplate, Megaphone, Palette, Plus, Search, Share2, Upload, Video } from 'lucide-react';
import { useOperations } from '../context/OperationsContext';
import type { ContentTemplate } from '../types';
import './LibraryView.css';

type LibraryDisplayAsset = readonly [title: string, meta: string, preview: string];

const libraryAssets: LibraryDisplayAsset[] = [
  ['Ritual de foco 01', 'Post · 4 usos', '/canonical/figma/phase2/s05-creative.png'],
  ['Aurora — UGC', 'UGC · 2 usos', '/canonical/figma/phase2/s04-carousel.png'],
  ['Carrossel tipográfico', 'Carrossel · 3 usos', '/canonical/figma/phase2/s04-stories.png'],
  ['Origem e textura', 'Foto · 5 usos', '/canonical/figma/phase2/s16-product.png'],
  ['Oferta espresso', 'Produto · licenciado', '/canonical/figma/phase2/s04-offer.png'],
  ['Produto limpo', 'Produto · próprio', '/canonical/figma/phase2/s16-texture.png'],
  ['Textura Cerrado', 'Referência · interna', '/canonical/figma/phase2/s16-product.png'],
  ['Fumaça e movimento', 'Referência · licenciada', '/canonical/figma/phase2/s05-creative.png'],
];

const templateSeed: ContentTemplate[] = [
  { id: 'tpl-1', name: 'Carrossel educativo premium', category: 'image', description: 'Estrutura visual de 7 slides para conteúdo educativo.', favorite: true, shared: true, uses: 42, updatedAt: '2026-08-02' },
  { id: 'tpl-2', name: 'Reels com gancho e prova', category: 'video', description: 'Roteiro de vídeo curto com gancho, demonstração e chamada para ação.', favorite: false, shared: true, uses: 31, updatedAt: '2026-08-01' },
  { id: 'tpl-3', name: 'Texto de lançamento', category: 'copy', description: 'Estrutura de texto persuasivo para produtos digitais.', favorite: true, shared: false, uses: 68, updatedAt: '2026-07-31' },
  { id: 'tpl-4', name: 'Campanha multicanal', category: 'campaign', description: 'Plano completo para lançamento em quatro canais.', favorite: false, shared: true, uses: 19, updatedAt: '2026-07-29' },
  { id: 'tpl-5', name: 'Calendário contínuo', category: 'calendar', description: 'Cadência mensal equilibrada por etapa do funil.', favorite: false, shared: false, uses: 24, updatedAt: '2026-07-28' },
  { id: 'tpl-6', name: 'Comando de fotografia editorial', category: 'prompt', description: 'Comando detalhado para imagens consistentes de campanha.', favorite: true, shared: true, uses: 57, updatedAt: '2026-07-25' },
  { id: 'tpl-7', name: 'Identidade Clicko', category: 'brand', description: 'Cores, tipografia, espaçamento e diretrizes da marca.', favorite: true, shared: true, uses: 86, updatedAt: '2026-08-02' },
];

const templateMeta = {
  image: ['Imagem', Image], video: ['Vídeo', Video], copy: ['Texto', FileText], campaign: ['Campanha', Megaphone],
  calendar: ['Calendário', CalendarDays], prompt: ['Comando', LayoutTemplate], brand: ['Identidade visual', Palette],
} as const;

export function LibraryView({ onOpenStudio }: { onOpenStudio?: () => void }) {
  const { addAsset, assets } = useOperations();
  const [selected, setSelected] = React.useState(0);
  const [query, setQuery] = React.useState('');
  const [activeTab, setActiveTab] = React.useState('Arquivos');
  const [deleted, setDeleted] = React.useState(false);
  const [toast, setToast] = React.useState('');
  const [templates, setTemplates] = React.useState(templateSeed);
  const [templateCategory, setTemplateCategory] = React.useState<'all' | ContentTemplate['category']>('all');
  const contextualAssets = React.useMemo<LibraryDisplayAsset[]>(() => assets.map((asset) => [
    asset.title,
    `${asset.type === 'content' ? 'Conteúdo da KLIC' : asset.type === 'upload' ? 'Upload' : asset.type} · ${asset.tags.slice(0, 2).join(' · ') || 'sem etiquetas'}`,
    asset.url || '/canonical/figma/phase2/s05-creative.png',
  ]), [assets]);
  const allLibraryAssets = React.useMemo(() => [
    ...libraryAssets.slice(0, 4),
    ...contextualAssets,
    ...libraryAssets.slice(4),
  ], [contextualAssets]);
  const matchesQuery = React.useCallback((asset: LibraryDisplayAsset) => `${asset[0]} ${asset[1]}`.toLowerCase().includes(query.toLowerCase()), [query]);
  const visibleUsed = libraryAssets.slice(0, 4).filter(matchesQuery);
  const visibleBrand = [...contextualAssets, ...libraryAssets.slice(4)].filter(matchesQuery);
  const current = allLibraryAssets[selected] || allLibraryAssets[0];
  const visibleTemplates = templates.filter((template) => (templateCategory === 'all' || template.category === templateCategory) && `${template.name} ${template.description}`.toLowerCase().includes(query.toLowerCase()));

  const upload = () => {
    addAsset({ title: 'Novo material enviado', type: 'upload', tags: ['upload'] });
    setToast('Upload preparado');
  };

  const createTemplate = () => {
    const template: ContentTemplate = { id: `tpl-${Date.now()}`, name: 'Novo modelo', category: 'copy', description: 'Modelo personalizado pronto para edição.', favorite: false, shared: false, uses: 0, updatedAt: new Date().toISOString().slice(0, 10) };
    setTemplates((currentTemplates) => [template, ...currentTemplates]);
    setActiveTab('Modelos'); setTemplateCategory('all'); setQuery(''); setToast('Novo modelo criado');
  };

  const updateTemplate = (id: string, field: 'favorite' | 'shared') => setTemplates((currentTemplates) => currentTemplates.map((template) => template.id === id ? { ...template, [field]: !template[field] } : template));
  const duplicateTemplate = (template: ContentTemplate) => { setTemplates((currentTemplates) => [{ ...template, id: `tpl-${Date.now()}`, name: `${template.name} — cópia`, uses: 0, shared: false, updatedAt: new Date().toISOString().slice(0, 10) }, ...currentTemplates]); setToast('Modelo duplicado'); };

  React.useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(''), 2400);
    return () => window.clearTimeout(timer);
  }, [toast]);

  return <section className="cx-library-approved">
    <header>
      <div><h1>Biblioteca</h1><p>Tudo o que a marca pode reutilizar, adaptar e provar.</p></div>
      <button className="cx-library-button" onClick={upload}><Upload />Upload</button>
      <button className="cx-library-button is-primary" onClick={createTemplate}><Plus />Criar modelo</button>
    </header>
    <nav>{['Arquivos', 'Modelos', 'Marca', 'Campanhas', 'Linhagem'].map((tab) => <button className={activeTab === tab ? 'is-active' : ''} onClick={() => setActiveTab(tab)} key={tab}>{tab}</button>)}</nav>
    <div className="cx-library-toolbar">
      <label><Search /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar por nome, campanha, uso ou direito..." /></label>
      {activeTab === 'Modelos' ? <select value={templateCategory} onChange={(event) => setTemplateCategory(event.target.value as typeof templateCategory)}>{(['all', ...Object.keys(templateMeta)] as const).map((category) => <option key={category} value={category}>{category === 'all' ? 'Todas as categorias' : templateMeta[category][0]}</option>)}</select> : <><button className="cx-library-button">Filtros 3</button><button className="cx-library-button">Mais recentes⌄</button></>}
    </div>
    {activeTab === 'Modelos' ? <TemplateLibrary templates={visibleTemplates} onToggle={updateTemplate} onDuplicate={duplicateTemplate} /> : <div className="cx-library-layout">
      <main>
        {deleted ? <div className="cx-library-empty"><strong>Arquivo removido da visão</strong><p>A exclusão foi aplicada apenas à demonstração.</p><button onClick={() => setDeleted(false)}>Desfazer</button></div> : <>
          <div className="cx-library-section-head"><h2>Usados na campanha Aurora</h2><button>Ver campanha →</button></div>
          <div className="cx-library-used">{visibleUsed.map((asset) => { const index = allLibraryAssets.indexOf(asset); return <button className={selected === index ? 'is-active' : ''} onClick={() => setSelected(index)} key={`${asset[0]}-${index}`}><img src={asset[2]} alt="" /><b>{asset[0]}</b><small>{asset[1]}</small></button>; })}</div>
          <div className="cx-library-section-head"><h2>Ativos da marca</h2><span>{allLibraryAssets.length} arquivos</span></div>
          <div className="cx-library-assets">{visibleBrand.map((asset) => { const index = allLibraryAssets.indexOf(asset); return <button className={selected === index ? 'is-active' : ''} onClick={() => setSelected(index)} key={`${asset[0]}-${index}`}><img src={asset[2]} alt="" /><b>{asset[0]}</b><small>{asset[1]}</small></button>; })}</div>
          <h2>Referências recentes</h2><article className="cx-library-reference"><img src={libraryAssets[1][2]} alt="" /><span><b>Direção humana — cenas cotidianas</b><small>Moodboard Aurora · adicionada hoje por João</small></span><em>Uso interno</em><button>Abrir →</button></article>
        </>}
      </main>
      <aside>
        <h2>{current[0]}</h2><p>Imagem selecionada</p>
        <div className="cx-library-preview"><img src={current[2]} alt="" /><em>EM USO</em></div>
        <small>DETALHES</small><KeyValue label="Tipo" value="Imagem 1080 × 1350" /><KeyValue label="Campanha" value="Aurora — Copa" /><KeyValue label="Direitos" value="Licença comercial" />
        <small>USOS E LINHAGEM</small><article><b>Carrossel Ritual de foco</b><small>3 variações · 2 publicadas</small><button>Abrir →</button></article><KeyValue label="Origem" value="Moodboard / Ref. 04" /><KeyValue label="Alterações" value="Corte, contraste, texto" />
        <button className="cx-library-button is-primary is-wide" onClick={onOpenStudio}>Inserir no editor</button><button className="cx-library-button is-wide" onClick={onOpenStudio}>Criar variação com contexto</button><button className="cx-delete-asset" onClick={() => setDeleted(true)}>Excluir arquivo</button>
      </aside>
    </div>}
    {toast && <div className="cx-library-toast">{toast}</div>}
  </section>;
}

function TemplateLibrary({ templates, onToggle, onDuplicate }: { templates: ContentTemplate[]; onToggle: (id: string, field: 'favorite' | 'shared') => void; onDuplicate: (template: ContentTemplate) => void }) {
  return <div className="cx-template-library"><div className="cx-library-section-head"><h2>Modelos reutilizáveis</h2><span>{templates.length} modelos</span></div>{templates.length ? <div className="cx-template-grid">{templates.map((template) => { const [label, Icon] = templateMeta[template.category]; return <article key={template.id}><div className="cx-template-card-top"><span><Icon /></span><button onClick={() => onToggle(template.id, 'favorite')} aria-label="Favoritar modelo"><Heart className={template.favorite ? 'is-favorite' : ''} /></button></div><small>{label}</small><h3>{template.name}</h3><p>{template.description}</p><footer><span>{template.uses} usos</span><div><button onClick={() => onDuplicate(template)} title="Duplicar"><Copy /></button><button onClick={() => onToggle(template.id, 'shared')} title="Compartilhar"><Share2 className={template.shared ? 'is-shared' : ''} /></button></div></footer></article>; })}</div> : <div className="cx-library-empty"><strong>Nenhum modelo encontrado</strong><p>Ajuste a busca ou crie um novo modelo.</p></div>}</div>;
}

function KeyValue({ label, value }: { label: string; value: string }) {
  return <div className="cx-library-kv"><span>{label}</span><b>{value}</b></div>;
}
