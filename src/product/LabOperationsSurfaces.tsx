import React from "react";
import {
  Activity,
  ArrowRight,
  BadgeCheck,
  BarChart3,
  BookOpen,
  CalendarDays,
  Check,
  Clock3,
  FileText,
  FolderKanban,
  GitBranch,
  Image,
  Instagram,
  Layers3,
  Library,
  Link2,
  Palette,
  Plus,
  Radio,
  Search,
  Send,
  Settings2,
  ShieldCheck,
  Sparkles,
  Upload,
  Users,
  Workflow,
} from "lucide-react";
import { useGovernance } from "../context/GovernanceContext";
import { useOperations } from "../context/OperationsContext";
import { useProductData } from "../context/ProductDataContext";
import type { Post } from "../types";

type Navigate = (path: string) => void;

const artwork = [
  "linear-gradient(145deg,#321b37,#a94b69 53%,#ffb177)",
  "linear-gradient(145deg,#102d36,#277276 50%,#edc28b)",
  "linear-gradient(145deg,#201c46,#6254bc 50%,#eca0be)",
  "linear-gradient(145deg,#3b2417,#c66935 52%,#f5d0a0)",
  "linear-gradient(145deg,#172f28,#398b70 48%,#d8d96f)",
];

function Media({ post, index }: { post?: Post; index: number }) {
  return post?.imageUrl ? <img src={post.imageUrl} alt="" className="h-full w-full object-cover" /> : <span className="block h-full w-full" style={{ background: artwork[index % artwork.length] }} />;
}

export function ContextTabs({ items, pathname, onNavigate }: { items: Array<{ label: string; path: string; icon?: React.ComponentType<{ className?: string }> }>; pathname: string; onNavigate: Navigate }) {
  return (
    <nav className="clicko-context-tabs mb-7 flex gap-1 overflow-x-auto border-b border-white/[0.07] pb-2" aria-label="Navegação contextual">
      {items.map(({ label, path, icon: Icon }) => {
        const active = pathname === path || (path.includes("/approvals/") && pathname.startsWith("/approvals/"));
        return <button key={label} type="button" onClick={() => onNavigate(path)} aria-current={active ? "page" : undefined} className={`inline-flex min-h-10 shrink-0 items-center gap-2 rounded-xl px-3 text-[12px] font-bold ${active ? "bg-white text-black" : "text-white/38 hover:bg-white/[0.04] hover:text-white"}`}>{Icon && <Icon className="h-4 w-4" />}{label}</button>;
      })}
    </nav>
  );
}

export const libraryTabs = [
  { label: "Arquivos", path: "/library/assets", icon: Library },
  { label: "Templates", path: "/templates", icon: Layers3 },
  { label: "Marca", path: "/brand-memory", icon: Palette },
  { label: "Linhagem", path: "/library/lineage", icon: GitBranch },
];

export const publishTabs = [
  { label: "Calendário", path: "/calendar", icon: CalendarDays },
  { label: "Aprovações", path: "/approvals/post-1", icon: BadgeCheck },
  { label: "Publicação", path: "/publish/active", icon: Send },
  { label: "Desempenho", path: "/analytics/learning", icon: BarChart3 },
  { label: "Canais", path: "/settings/channels", icon: Radio },
];

export const settingsTabs = [
  { label: "Marca", path: "/brand-memory", icon: Palette },
  { label: "Equipe", path: "/settings/team", icon: Users },
  { label: "Canais", path: "/settings/channels", icon: Radio },
  { label: "IA", path: "/settings/ai-governance", icon: Sparkles },
  { label: "Automações", path: "/automations/active", icon: Workflow },
  { label: "Plano", path: "/settings/billing", icon: Activity },
  { label: "Auditoria", path: "/settings/audit", icon: ShieldCheck },
];

export function LabLibrarySurface({ pathname, onNavigate }: { pathname: string; onNavigate: Navigate }) {
  const operations = useOperations();
  const productData = useProductData();
  const posts = (productData.status === "ready" && productData.snapshot ? productData.snapshot.posts : operations.posts) as unknown as Post[];
  const [query, setQuery] = React.useState("");
  const [editingBrand, setEditingBrand] = React.useState(false);
  const [tone, setTone] = React.useState(operations.brain.toneOfVoice);
  const isBrand = pathname === "/brand-memory";
  const isTemplates = pathname === "/templates";
  const isLineage = pathname === "/library/lineage";
  const filteredAssets = operations.assets.filter((asset) => `${asset.title} ${asset.tags.join(" ")}`.toLowerCase().includes(query.toLowerCase()));

  const uploadAsset = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    operations.addAsset({ title: file.name, type: file.type.startsWith("image/") ? "image" : "document", tags: ["upload"] });
    event.target.value = "";
  };

  return (
    <div className="mx-auto max-w-[1560px]">
      <ContextTabs items={libraryTabs} pathname={pathname} onNavigate={onNavigate} />
      {isBrand ? (
        <>
          <header className="flex flex-wrap items-end justify-between gap-5"><div><span className="text-[12px] font-bold text-[#ff8d68]">Contexto compartilhado</span><h1 className="clicko-display mt-1 text-[clamp(32px,4vw,52px)] font-semibold tracking-[-.055em] text-white">Memória da marca</h1><p className="mt-2 max-w-2xl text-[13px] leading-6 text-white/38">A fonte usada por briefing, geração, revisão e aprendizado.</p></div><button type="button" onClick={() => setEditingBrand((value) => !value)} className="rounded-xl bg-[#ff6969] px-4 py-3 text-[12px] font-extrabold text-[#260707]">{editingBrand ? "Concluir" : "Editar memória"}</button></header>
          <div className="mt-7 grid gap-4 lg:grid-cols-[1.2fr_.8fr]">
            <section className="rounded-[26px] border border-white/[0.08] bg-white/[0.025] p-6"><div className="flex items-center justify-between"><div><small className="text-[11px] font-bold text-[#ff8d68]">Revisão {operations.brain.revision}</small><h2 className="clicko-display mt-1 text-[24px] font-semibold text-white">{operations.activeClient?.name || "Marca ativa"}</h2></div><span className="rounded-full border border-white/[0.08] px-3 py-1 text-[11px] text-white/45">{operations.brainCompleteness}% completa</span></div><div className="mt-6 grid gap-4 sm:grid-cols-2">{[["Oferta", operations.brain.products],["Público", operations.brain.audience],["Posicionamento", operations.brain.objectives],["Diferenciais", operations.brain.differentiators]].map(([label, value]) => <article key={label} className="rounded-[18px] border border-white/[0.07] bg-black/15 p-4"><small className="text-[10px] font-bold uppercase tracking-[.12em] text-white/30">{label}</small><p className="mt-2 line-clamp-4 text-[12px] leading-5 text-white/58">{value}</p></article>)}</div></section>
            <aside className="space-y-4"><section className="rounded-[24px] border border-white/[0.08] bg-white/[0.025] p-5"><div className="flex items-center gap-2"><BookOpen className="h-4 w-4 text-[#ff8d68]" /><h2 className="text-[13px] font-bold text-white">Tom de voz</h2></div>{editingBrand ? <textarea value={tone} onChange={(event) => setTone(event.target.value)} onBlur={() => operations.updateBrain({ toneOfVoice: tone })} className="mt-4 min-h-28 w-full resize-none rounded-xl border border-white/[0.1] bg-black/20 p-3 text-[12px] leading-5 text-white outline-none" /> : <p className="mt-3 text-[12px] leading-5 text-white/48">{operations.brain.toneOfVoice}</p>}</section><section className="rounded-[24px] border border-white/[0.08] bg-white/[0.025] p-5"><h2 className="text-[13px] font-bold text-white">Fontes</h2><div className="mt-3 space-y-2">{operations.brain.sourceFiles.map((source) => <div key={source.id} className="flex items-center gap-3 rounded-xl bg-white/[0.03] p-3"><FileText className="h-4 w-4 text-white/35" /><span className="truncate text-[11px] text-white/55">{source.name}</span><Check className="ml-auto h-3.5 w-3.5 text-emerald-400" /></div>)}</div></section></aside>
          </div>
        </>
      ) : isLineage ? (
        <>
          <header><span className="text-[12px] font-bold text-[#ff8d68]">Rastreabilidade</span><h1 className="clicko-display mt-1 text-[clamp(32px,4vw,52px)] font-semibold tracking-[-.055em] text-white">Linhagem criativa</h1><p className="mt-2 text-[13px] text-white/38">Da memória e campanha até cada peça e decisão.</p></header>
          <div className="mt-8 overflow-x-auto"><div className="grid min-w-[980px] grid-cols-[.8fr_1.2fr_1.4fr_.8fr] gap-5">{[["Marca", [operations.activeClient?.name || "Clicko"]],["Projetos", operations.campaigns.map((item) => item.name)],["Peças", posts.slice(0, 6).map((item) => item.title)],["Estados", posts.slice(0, 6).map((item) => item.status)]].map(([label, items], column) => <section key={String(label)}><h2 className="mb-3 text-[11px] font-bold uppercase tracking-[.12em] text-white/30">{String(label)}</h2><div className="space-y-3">{(items as string[]).map((item, index) => <button key={`${item}-${index}`} type="button" onClick={() => column === 1 ? onNavigate(`/projects/${operations.campaigns[index]?.id || "active"}`) : undefined} className="relative flex min-h-[72px] w-full items-center gap-3 rounded-[18px] border border-white/[0.08] bg-white/[0.025] p-3 text-left hover:bg-white/[0.05]"><span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-white/[0.05] text-[#ff8d68]">{column === 0 ? <Palette className="h-4 w-4" /> : column === 1 ? <FolderKanban className="h-4 w-4" /> : column === 2 ? <Image className="h-4 w-4" /> : <BadgeCheck className="h-4 w-4" />}</span><span className="line-clamp-2 text-[11px] font-semibold text-white/60">{item}</span>{column < 3 && <ArrowRight className="absolute -right-4 h-4 w-4 text-white/20" />}</button>)}</div></section>)}</div></div>
        </>
      ) : (
        <>
          <header className="flex flex-wrap items-end justify-between gap-5"><div><span className="text-[12px] font-bold text-[#ff8d68]">{isTemplates ? "Sistemas reutilizáveis" : "Acervo do workspace"}</span><h1 className="clicko-display mt-1 text-[clamp(32px,4vw,52px)] font-semibold tracking-[-.055em] text-white">{isTemplates ? "Templates" : "Biblioteca"}</h1><p className="mt-2 text-[13px] text-white/38">{isTemplates ? "Estruturas consistentes que continuam editáveis." : "Referências, uploads, peças e ativos de marca em um só lugar."}</p></div><label className="inline-flex h-11 cursor-pointer items-center gap-2 rounded-xl bg-[#ff6969] px-4 text-[12px] font-extrabold text-[#260707]"><Upload className="h-4 w-4" /> Enviar arquivo<input type="file" aria-label="Selecionar arquivo para a biblioteca" className="sr-only" onChange={uploadAsset} /></label></header>
          <div className="mt-6 flex flex-wrap gap-2"><label className="flex h-10 min-w-[270px] items-center gap-2 rounded-xl border border-white/[0.08] bg-white/[0.025] px-3"><Search className="h-4 w-4 text-white/30" /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar no acervo" className="min-w-0 flex-1 bg-transparent text-[12px] text-white outline-none placeholder:text-white/25" /></label>{["Tudo", "Imagens", "Vídeos", "Documentos"].map((label, index) => <button key={label} type="button" className={`rounded-xl px-3 text-[11px] font-bold ${index === 0 ? "bg-white text-black" : "border border-white/[0.08] text-white/38"}`}>{label}</button>)}</div>
          <div className="mt-5 grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5">{(isTemplates ? [...filteredAssets.filter((asset) => asset.type === "template"), ...filteredAssets] : filteredAssets).slice(0, 5).map((asset, index) => <button key={`${asset.id}-${index}`} type="button" onClick={() => isTemplates ? onNavigate("/content/draft/edit?mode=visual") : undefined} className="group overflow-hidden rounded-[20px] border border-white/[0.08] bg-white/[0.025] text-left"><div className="aspect-square overflow-hidden"><Media post={posts[index]} index={index} /></div><div className="p-3"><strong className="block truncate text-[12px] text-white/70">{asset.title}</strong><small className="mt-1 block text-[10px] text-white/28">{asset.type} · {asset.tags.join(" · ")}</small></div></button>)}{posts.slice(0, Math.max(0, 5 - filteredAssets.length)).map((post, index) => <button key={post.id} type="button" onClick={() => onNavigate(`/content/${post.id}/edit?mode=visual`)} className="overflow-hidden rounded-[20px] border border-white/[0.08] bg-white/[0.025] text-left"><div className="aspect-square"><Media post={post} index={index + 2} /></div><div className="p-3"><strong className="block truncate text-[12px] text-white/70">{post.title}</strong><small className="mt-1 block text-[10px] text-white/28">{post.format} · {post.status}</small></div></button>)}</div>
        </>
      )}
    </div>
  );
}

export function LabPublishSurface({ pathname, onNavigate }: { pathname: string; onNavigate: Navigate }) {
  const operations = useOperations();
  const productData = useProductData();
  const posts = (productData.status === "ready" && productData.snapshot ? productData.snapshot.posts : operations.posts) as unknown as Post[];
  const isQueue = pathname.startsWith("/publish");
  const isAnalytics = pathname.startsWith("/analytics");
  const isChannels = pathname === "/settings/channels";
  const scheduled = posts.filter((post) => ["approved", "scheduled"].includes(post.status));
  const published = posts.filter((post) => post.status === "published");
  const days = Array.from({ length: 7 }, (_, index) => { const date = new Date(); date.setDate(date.getDate() + index); return date; });

  const publishNow = async (post: Post) => {
    operations.updatePosts((current) => current.map((item) => item.id === post.id ? { ...item, status: "published" } : item));
    if (productData.status === "ready") await productData.updatePost(post.id, { status: "published" });
  };

  return (
    <div className="mx-auto max-w-[1560px]">
      <ContextTabs items={publishTabs} pathname={pathname} onNavigate={onNavigate} />
      {isChannels ? (
        <><header><span className="text-[12px] font-bold text-[#ff8d68]">Distribuição</span><h1 className="clicko-display mt-1 text-[clamp(32px,4vw,52px)] font-semibold tracking-[-.055em] text-white">Canais</h1><p className="mt-2 text-[13px] text-white/38">Conexões usadas para publicar e coletar métricas reais.</p></header><div className="mt-7 grid gap-3 md:grid-cols-2 xl:grid-cols-3">{[["Instagram",Instagram,"Conectado"],["LinkedIn",Link2,"Conectado"],["TikTok",Activity,"Configurar"],["YouTube",Send,"Configurar"],["Facebook",Users,"Configurar"],["Pinterest",Image,"Configurar"]].map(([label, Icon, state]) => { const ChannelIcon = Icon as React.ComponentType<{className?:string}>; return <article key={String(label)} className="flex items-center gap-4 rounded-[22px] border border-white/[0.08] bg-white/[0.025] p-5"><span className="grid h-12 w-12 place-items-center rounded-[16px] bg-white/[0.05] text-[#ff8d68]"><ChannelIcon className="h-5 w-5" /></span><div><h2 className="text-[13px] font-bold text-white">{String(label)}</h2><p className="mt-1 text-[11px] text-white/32">{String(state)}</p></div><button type="button" className="ml-auto rounded-xl border border-white/[0.08] px-3 py-2 text-[11px] font-bold text-white/45 hover:text-white">{state === "Conectado" ? "Gerenciar" : "Conectar"}</button></article>; })}</div></>
      ) : isAnalytics ? (
        <><header><span className="text-[12px] font-bold text-[#ff8d68]">Aprendizado real</span><h1 className="clicko-display mt-1 text-[clamp(32px,4vw,52px)] font-semibold tracking-[-.055em] text-white">Desempenho</h1><p className="mt-2 text-[13px] text-white/38">O que já foi publicado orienta a próxima criação.</p></header><div className="mt-7 grid gap-4 lg:grid-cols-[1fr_1fr]"> <section className="rounded-[24px] border border-white/[0.08] bg-white/[0.025] p-5"><h2 className="text-[13px] font-bold text-white">Sinais de aprendizado</h2><div className="mt-4 space-y-3">{operations.learningSignals.map((signal) => <article key={signal.id} className="rounded-[18px] bg-white/[0.03] p-4"><small className="text-[10px] font-bold uppercase tracking-[.12em] text-[#ff8d68]">{signal.confidence}</small><h3 className="mt-2 text-[13px] font-bold text-white/75">{signal.label}</h3><p className="mt-2 text-[11px] leading-5 text-white/38">{signal.recommendation}</p></article>)}</div></section><section className="rounded-[24px] border border-white/[0.08] bg-white/[0.025] p-5"><div className="flex items-center justify-between"><h2 className="text-[13px] font-bold text-white">Conteúdos publicados</h2><span className="text-[11px] text-white/30">{published.length} com dados</span></div><div className="mt-4 space-y-2">{published.map((post, index) => <button key={post.id} type="button" onClick={() => onNavigate(`/content/${post.id}`)} className="flex w-full items-center gap-3 rounded-[16px] p-2 text-left hover:bg-white/[0.04]"><span className="h-12 w-12 shrink-0 overflow-hidden rounded-xl"><Media post={post} index={index} /></span><span className="min-w-0"><strong className="block truncate text-[11px] text-white/65">{post.title}</strong><small className="mt-1 block text-[10px] text-white/28">{post.platform} · {post.format}</small></span></button>)}</div></section></div></>
      ) : isQueue ? (
        <><header className="flex items-end justify-between gap-5"><div><span className="text-[12px] font-bold text-[#ff8d68]">Fila de distribuição</span><h1 className="clicko-display mt-1 text-[clamp(32px,4vw,52px)] font-semibold tracking-[-.055em] text-white">Publicação</h1><p className="mt-2 text-[13px] text-white/38">Peças aprovadas, canais e horários antes de ir ao ar.</p></div><span className="rounded-full border border-white/[0.08] px-3 py-2 text-[11px] text-white/38">{scheduled.length} prontas</span></header><div className="mt-7 space-y-3">{scheduled.map((post, index) => <article key={post.id} className="grid items-center gap-4 rounded-[22px] border border-white/[0.08] bg-white/[0.025] p-4 md:grid-cols-[72px_minmax(0,1fr)_160px_140px]"><span className="h-[72px] overflow-hidden rounded-[16px]"><Media post={post} index={index} /></span><div className="min-w-0"><small className="text-[10px] font-bold uppercase tracking-[.1em] text-[#ff8d68]">{post.status}</small><h2 className="mt-1 truncate text-[13px] font-bold text-white">{post.title}</h2><p className="mt-1 text-[11px] text-white/30">{post.platform} · {post.format}</p></div><div className="text-[11px] text-white/40"><Clock3 className="mr-2 inline h-4 w-4" />{post.scheduledAt ? new Intl.DateTimeFormat("pt-BR",{day:"2-digit",month:"short",hour:"2-digit",minute:"2-digit"}).format(new Date(post.scheduledAt)) : "Sem horário"}</div><button type="button" onClick={() => void publishNow(post)} className="h-10 rounded-xl bg-white px-3 text-[11px] font-extrabold text-black">Publicar agora</button></article>)}</div></>
      ) : (
        <><header className="flex items-end justify-between gap-5"><div><span className="text-[12px] font-bold text-[#ff8d68]">Planejamento editorial</span><h1 className="clicko-display mt-1 text-[clamp(32px,4vw,52px)] font-semibold tracking-[-.055em] text-white">Calendário</h1><p className="mt-2 text-[13px] text-white/38">Cadência, conflitos e próximos conteúdos em uma semana.</p></div><button type="button" onClick={() => onNavigate("/content/new?type=post")} className="inline-flex h-11 items-center gap-2 rounded-xl bg-[#ff6969] px-4 text-[12px] font-extrabold text-[#260707]"><Plus className="h-4 w-4" /> Agendar conteúdo</button></header><div className="mt-7 overflow-x-auto"><div className="grid min-w-[980px] grid-cols-7 gap-2">{days.map((day, column) => { const items = posts.filter((post) => post.scheduledAt && new Date(post.scheduledAt).getDay() === day.getDay()); return <section key={day.toISOString()} className="min-h-[520px] rounded-[20px] border border-white/[0.07] bg-white/[0.018] p-2"><header className="px-2 py-3 text-center"><small className="text-[10px] font-bold uppercase text-white/28">{new Intl.DateTimeFormat("pt-BR",{weekday:"short"}).format(day)}</small><strong className="mt-1 block text-[15px] text-white/65">{day.getDate()}</strong></header><div className="space-y-2">{items.map((post,index) => <button key={post.id} type="button" onClick={() => onNavigate(`/approvals/${post.id}`)} className="w-full overflow-hidden rounded-[15px] border border-white/[0.07] bg-white/[0.03] text-left"><div className="aspect-[4/3]"><Media post={post} index={column+index} /></div><div className="p-2.5"><strong className="line-clamp-2 text-[10px] leading-4 text-white/65">{post.title}</strong><small className="mt-1 block text-[9px] text-white/25">{post.platform}</small></div></button>)}</div></section>; })}</div></div></>
      )}
    </div>
  );
}

export function LabSettingsSurface({ pathname, onNavigate }: { pathname: string; onNavigate: Navigate }) {
  const governance = useGovernance();
  const operations = useOperations();
  const entries = [
    { title: "Diretrizes de IA", detail: "Autonomia, fontes e revisão humana", path: "/settings/ai-governance", icon: Sparkles },
    { title: "Equipe e acesso", detail: "Papéis, convites e permissões", path: "/settings/team", icon: Users },
    { title: "Canais", detail: "Publicação e métricas", path: "/settings/channels", icon: Radio },
    { title: "Automações", detail: "Regras e gatilhos do fluxo", path: "/automations/active", icon: Workflow },
    { title: "Plano e capacidade", detail: "Assinatura, usuários e limites", path: "/settings/billing", icon: Activity },
    { title: "Auditoria", detail: "Histórico de ações e decisões", path: "/settings/audit", icon: ShieldCheck },
  ];
  return <div className="mx-auto max-w-[1200px]"><ContextTabs items={settingsTabs} pathname={pathname} onNavigate={onNavigate} /><header><span className="text-[12px] font-bold text-[#ff8d68]">Workspace</span><h1 className="clicko-display mt-1 text-[clamp(32px,4vw,52px)] font-semibold tracking-[-.055em] text-white">Configurações</h1><p className="mt-2 text-[13px] text-white/38">{operations.activeWorkspace.name} · {governance.currentUser?.name || "Operação local"}</p></header><div className="mt-7 grid gap-3 md:grid-cols-2">{entries.map(({title,detail,path,icon:Icon}) => <button key={title} type="button" onClick={() => onNavigate(path)} className="flex min-h-[110px] items-center gap-4 rounded-[22px] border border-white/[0.08] bg-white/[0.025] p-5 text-left hover:bg-white/[0.05]"><span className="grid h-12 w-12 shrink-0 place-items-center rounded-[16px] bg-white/[0.05] text-[#ff8d68]"><Icon className="h-5 w-5" /></span><span><strong className="block text-[13px] text-white/75">{title}</strong><small className="mt-1 block text-[11px] text-white/32">{detail}</small></span><ArrowRight className="ml-auto h-4 w-4 text-white/25" /></button>)}</div><section className="mt-7 rounded-[22px] border border-white/[0.08] bg-white/[0.025] p-5"><div className="flex items-center gap-3"><Settings2 className="h-5 w-5 text-[#ff8d68]" /><div><h2 className="text-[13px] font-bold text-white">Estado do workspace</h2><p className="mt-1 text-[11px] text-white/32">Memória v{operations.brain.revision} · {operations.campaigns.length} projeto · {operations.posts.length} conteúdos</p></div></div></section></div>;
}
