import React from "react";
import {
  ArrowRight,
  BadgeCheck,
  CalendarDays,
  ChevronDown,
  FileImage,
  Film,
  FolderKanban,
  Grid2X2,
  Image,
  Images,
  Layers3,
  Lightbulb,
  Link2,
  MessageSquareText,
  MoreHorizontal,
  Plus,
  Search,
  Sparkles,
  Upload,
  Users,
  WandSparkles,
} from "lucide-react";
import { useOperations } from "../context/OperationsContext";
import { useProductData } from "../context/ProductDataContext";
import type { Post } from "../types";
import { STITCH_SCREENS } from "./screenManifest";

type Navigate = (path: string) => void;

const covers = [
  "linear-gradient(145deg,#311b35,#a34663 52%,#ffad72)",
  "linear-gradient(145deg,#102b35,#2f7476 50%,#edc286)",
  "linear-gradient(145deg,#1d1b42,#5c50b3 52%,#e99cb9)",
  "linear-gradient(145deg,#392214,#bd632f 52%,#f0cc9e)",
  "linear-gradient(145deg,#172e26,#328568 48%,#d7d66f)",
];

function Artwork({ post, index, className = "" }: { post?: Post; index: number; className?: string }) {
  if (post?.imageUrl) return <img src={post.imageUrl} alt="" className={`h-full w-full object-cover ${className}`} />;
  return <span className={`block h-full w-full ${className}`} style={{ background: covers[index % covers.length] }} />;
}

export function LabProjectsSurface({ onNavigate }: { onNavigate: Navigate }) {
  const operations = useOperations();
  const productData = useProductData();
  const campaigns = productData.status === "ready" && productData.snapshot ? productData.snapshot.campaigns : operations.campaigns;
  const posts = (productData.status === "ready" && productData.snapshot ? productData.snapshot.posts : operations.posts) as unknown as Post[];
  const [query, setQuery] = React.useState("");
  const visible = campaigns.filter((campaign) => campaign.name.toLowerCase().includes(query.toLowerCase()));

  return (
    <div className="clicko-project-gallery mx-auto max-w-[1560px] px-1 py-2">
      <header className="flex flex-wrap items-end justify-between gap-5 pb-7">
        <div>
          <span className="text-[12px] font-bold text-[#ff8d68]">Workspace criativo</span>
          <h1 className="clicko-display mt-1 text-[clamp(32px,4vw,52px)] font-semibold tracking-[-.055em] text-white">Projetos</h1>
          <p className="mt-2 text-[13px] text-white/38">Campanhas, referências e peças reunidas pelo trabalho — não pela ferramenta.</p>
        </div>
        <button type="button" onClick={() => onNavigate("/campaigns/new")} className="inline-flex h-11 items-center gap-2 rounded-xl bg-[#ff6969] px-4 text-[12px] font-extrabold text-[#260707] hover:bg-[#ff8585]"><Plus className="h-4 w-4" /> Novo projeto</button>
      </header>

      <div className="mb-5 flex flex-wrap items-center gap-2">
        <label className="flex h-10 min-w-[260px] items-center gap-2 rounded-xl border border-white/[0.08] bg-white/[0.025] px-3 text-white/35 focus-within:border-white/[0.16]">
          <Search className="h-4 w-4" /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar projetos" className="min-w-0 flex-1 bg-transparent text-[12px] text-white outline-none placeholder:text-white/28" />
        </label>
        {["Todos", "Em produção", "Em revisão", "Publicados"].map((filter, index) => <button key={filter} type="button" className={`h-10 rounded-xl px-3 text-[12px] font-semibold ${index === 0 ? "bg-white text-black" : "border border-white/[0.08] text-white/40 hover:text-white"}`}>{filter}</button>)}
      </div>

      {visible.length ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {visible.map((campaign, index) => {
            const campaignPosts = posts.filter((post) => post.campaignId === campaign.id);
            const featured = campaignPosts.find((post) => post.imageUrl) || campaignPosts[0];
            const pending = campaignPosts.filter((post) => ["in_review", "pending_approval"].includes(post.status)).length;
            return (
              <article key={campaign.id} className="group overflow-hidden rounded-[26px] border border-white/[0.08] bg-white/[0.025]">
                <button type="button" onClick={() => { operations.setActiveCampaignId(campaign.id); onNavigate(`/projects/${campaign.id}`); }} className="block w-full text-left">
                  <div className="relative aspect-[16/10] overflow-hidden"><Artwork post={featured} index={index} className="transition duration-700 group-hover:scale-[1.035]" /><span className="absolute inset-0 bg-gradient-to-t from-black/65 via-transparent to-black/10" /><span className="absolute left-4 top-4 rounded-full border border-white/15 bg-black/45 px-2.5 py-1 text-[11px] font-bold text-white/70 backdrop-blur">{campaign.status}</span><span className="absolute right-4 top-4 grid h-8 w-8 place-items-center rounded-full bg-black/40 text-white/60 backdrop-blur"><MoreHorizontal className="h-4 w-4" /></span></div>
                  <div className="p-5"><h2 className="clicko-display truncate text-[20px] font-semibold tracking-[-.03em] text-white">{campaign.name}</h2><p className="mt-2 line-clamp-2 min-h-10 text-[12px] leading-5 text-white/38">{campaign.objective}</p><div className="mt-5 flex items-center gap-4 border-t border-white/[0.07] pt-4 text-[11px] text-white/35"><span className="flex items-center gap-1.5"><Layers3 className="h-3.5 w-3.5" />{campaignPosts.length} peças</span><span className="flex items-center gap-1.5"><MessageSquareText className="h-3.5 w-3.5" />{pending} decisões</span><span className="ml-auto flex items-center gap-1 font-bold text-white/55">Abrir <ArrowRight className="h-3.5 w-3.5" /></span></div></div>
                </button>
              </article>
            );
          })}
        </div>
      ) : (
        <div className="grid min-h-[420px] place-items-center rounded-[28px] border border-dashed border-white/[0.1] text-center"><div><FolderKanban className="mx-auto h-8 w-8 text-[#ff8d68]" /><h2 className="clicko-display mt-4 text-[24px] font-semibold text-white">Seu próximo projeto começa com contexto.</h2><p className="mx-auto mt-2 max-w-md text-[13px] leading-6 text-white/38">Traga uma ideia, oportunidade ou briefing. O Clicko conecta marca, referências e produção desde o início.</p><button type="button" onClick={() => onNavigate("/campaigns/new")} className="mt-5 rounded-xl bg-[#ff6969] px-4 py-3 text-[12px] font-extrabold text-[#260707]">Criar projeto</button></div></div>
      )}
    </div>
  );
}

export function LabCreateSurface({ onNavigate, campaignId }: { onNavigate: Navigate; campaignId?: string }) {
  const operations = useOperations();
  const posts = operations.posts;
  const campaign = operations.campaigns.find((item) => item.id === campaignId) || operations.activeCampaign || operations.campaigns[0];
  const effectiveCampaign = campaign?.id || "active";
  const labScreens = STITCH_SCREENS.filter((screen) => screen.project === "creative-lab");
  const recent = posts.slice(0, 5);
  const [advancedOpen, setAdvancedOpen] = React.useState(false);
  const resolveRoute = (route: string) => route
    .replace("/campaigns/active", `/campaigns/${effectiveCampaign}`)
    .replace("/content/post-1", `/content/${recent[0]?.id || "post-1"}`)
    .replace("/approvals/post-1", `/approvals/${recent[0]?.id || "post-1"}`);
  const starts = [
    { label: "Post", detail: "Feed e anúncio", icon: FileImage, path: "/content/new?type=post" },
    { label: "Carrossel", detail: "Narrativa em slides", icon: Grid2X2, path: "/content/draft/edit?mode=carousel" },
    { label: "Imagem", detail: "Canvas por camadas", icon: Image, path: "/content/draft/edit?mode=visual" },
    { label: "Vídeo", detail: "Reels e motion", icon: Film, path: "/content/draft/edit?mode=video" },
  ];

  return (
    <div className="mx-auto max-w-[1560px] px-1 py-2">
      <header className="max-w-4xl pb-6"><span className="text-[12px] font-bold text-[#ff8d68]">Creative Lab</span><h1 className="clicko-display mt-1 text-[clamp(34px,5vw,62px)] font-semibold leading-[.98] tracking-[-.06em] text-white">Da ideia à peça, sem trocar de contexto.</h1><p className="mt-3 max-w-2xl text-[13px] leading-6 text-white/38">Combine objetivo, marca e referências. O Clicko organiza a direção e leva tudo ao editor.</p></header>

      <section className="grid overflow-hidden rounded-[30px] border border-white/[0.08] bg-[#18181a] lg:grid-cols-[minmax(0,1.5fr)_370px]">
        <div className="p-5 sm:p-7">
          <div className="flex min-h-[150px] flex-col rounded-[22px] border border-white/[0.1] bg-black/20 p-4 focus-within:border-[#ff6969]/50">
            <textarea placeholder="Ex.: campanha de lançamento com estética editorial, foco no produto e três variações para Instagram…" className="min-h-[70px] flex-1 resize-none bg-transparent text-[15px] leading-6 text-white outline-none placeholder:text-white/25" />
            <div className="mt-4 flex flex-wrap items-center gap-2"><button type="button" onClick={() => onNavigate("/library/assets")} className="inline-flex h-9 items-center gap-2 rounded-xl border border-white/[0.09] px-3 text-[11px] font-semibold text-white/48 hover:text-white"><Upload className="h-4 w-4" /> Referências</button><button type="button" onClick={() => onNavigate("/brand-memory")} className="inline-flex h-9 items-center gap-2 rounded-xl border border-white/[0.09] px-3 text-[11px] font-semibold text-white/48 hover:text-white"><Link2 className="h-4 w-4" /> Usar marca</button><button type="button" onClick={() => onNavigate(`/content/draft/edit?mode=visual&campaign=${effectiveCampaign}`)} className="ml-auto inline-flex h-10 items-center gap-2 rounded-xl bg-[#ff6969] px-4 text-[12px] font-extrabold text-[#260707]"><WandSparkles className="h-4 w-4" /> Criar</button></div>
          </div>
          <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">{starts.map(({ label, detail, icon: Icon, path }) => <button key={label} type="button" onClick={() => onNavigate(`${path}${path.includes("?") ? "&" : "?"}campaign=${effectiveCampaign}`)} className="group rounded-[20px] border border-white/[0.08] bg-white/[0.025] p-4 text-left hover:-translate-y-0.5 hover:bg-white/[0.05]"><Icon className="h-5 w-5 text-[#ff8d68]" /><strong className="mt-6 block text-[13px] text-white">{label}</strong><small className="mt-1 block text-[11px] text-white/32">{detail}</small></button>)}</div>
        </div>
        <aside className="border-t border-white/[0.08] bg-white/[0.018] p-5 lg:border-l lg:border-t-0">
          <div className="flex items-center justify-between"><div><small className="text-[11px] font-bold text-[#ff8d68]">Projeto ativo</small><h2 className="clicko-display mt-1 text-[19px] font-semibold text-white">{campaign?.name || "Criação livre"}</h2></div><Users className="h-4 w-4 text-white/30" /></div>
          <div className="mt-5 overflow-hidden rounded-[20px] border border-white/[0.08]"><div className="aspect-[16/10]"><Artwork post={recent.find((post) => post.imageUrl)} index={2} /></div><div className="p-4"><p className="text-[12px] leading-5 text-white/42">{campaign?.objective || "Escolha um formato ou comece por uma referência visual."}</p><button type="button" onClick={() => onNavigate(`/projects/${effectiveCampaign}`)} className="mt-4 flex items-center gap-2 text-[11px] font-bold text-white/60 hover:text-white">Abrir board <ArrowRight className="h-3.5 w-3.5" /></button></div></div>
        </aside>
      </section>

      <section className="mt-9"><div className="mb-4 flex items-end justify-between"><div><h2 className="clicko-display text-[22px] font-semibold text-white">Continue de onde parou</h2><p className="mt-1 text-[12px] text-white/35">Resultados e rascunhos recentes.</p></div><button type="button" onClick={() => onNavigate("/library/assets")} className="text-[12px] font-bold text-white/45 hover:text-white">Ver tudo</button></div><div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5">{Array.from({ length: 5 }, (_, index) => <button key={recent[index]?.id || index} type="button" onClick={() => onNavigate(`/content/${recent[index]?.id || "draft"}/edit?mode=visual`)} className="group overflow-hidden rounded-[20px] border border-white/[0.08] bg-white/[0.025] text-left"><div className="aspect-square overflow-hidden"><Artwork post={recent[index]} index={index} className="transition duration-500 group-hover:scale-105" /></div><div className="p-3"><strong className="block truncate text-[12px] text-white/75">{recent[index]?.title || "Nova direção"}</strong><small className="mt-1 block text-[11px] text-white/28">{recent[index]?.status || "Inspiração"}</small></div></button>)}</div></section>

      <section className="mt-8 border-t border-white/[0.07] pt-5"><button type="button" onClick={() => setAdvancedOpen((value) => !value)} className="flex w-full items-center justify-between text-left"><span><strong className="text-[13px] text-white/65">Ferramentas avançadas</strong><small className="ml-2 text-[11px] text-white/28">19 estados conectados ao mesmo projeto</small></span><ChevronDown className={`h-4 w-4 text-white/35 transition ${advancedOpen ? "rotate-180" : ""}`} /></button>{advancedOpen && <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">{labScreens.map((screen) => <button key={screen.id} type="button" data-creative-tool={screen.id} onClick={() => onNavigate(resolveRoute(screen.route))} className="flex items-center justify-between rounded-xl border border-white/[0.07] bg-white/[0.02] px-3 py-3 text-left hover:bg-white/[0.05]"><span className="truncate text-[11px] font-semibold text-white/55">{screen.frame.replace(/^Clicko — /, "").replace(/ V\d+(\.\d+)?$/, "")}</span><ArrowRight className="h-3.5 w-3.5 shrink-0 text-white/25" /></button>)}</div>}</section>
    </div>
  );
}

export function LabProjectBoard({ campaignId, onNavigate }: { campaignId: string; onNavigate: Navigate }) {
  const operations = useOperations();
  const campaign = operations.campaigns.find((item) => item.id === campaignId) || operations.activeCampaign || operations.campaigns[0];
  const posts = operations.posts.filter((post) => !campaign || post.campaignId === campaign.id);
  const stages = [
    { label: "Referências", icon: Lightbulb, items: posts.slice(0, 2) },
    { label: "Em criação", icon: Sparkles, items: posts.filter((post) => ["draft", "changes_requested"].includes(post.status)) },
    { label: "Em revisão", icon: MessageSquareText, items: posts.filter((post) => ["in_review", "pending_approval"].includes(post.status)) },
    { label: "Pronto", icon: BadgeCheck, items: posts.filter((post) => ["approved", "scheduled", "published"].includes(post.status)) },
  ];
  React.useEffect(() => { if (campaign?.id) operations.setActiveCampaignId(campaign.id); }, [campaign?.id, operations.setActiveCampaignId]);

  return (
    <div className="mx-auto max-w-[1700px] px-1 py-2">
      <header className="flex flex-wrap items-end justify-between gap-5 pb-6"><div><button type="button" onClick={() => onNavigate("/projects")} className="text-[11px] font-bold text-white/35 hover:text-white">Projetos /</button><h1 className="clicko-display mt-2 text-[clamp(30px,4vw,48px)] font-semibold tracking-[-.05em] text-white">{campaign?.name || "Projeto ativo"}</h1><p className="mt-2 max-w-2xl text-[12px] leading-5 text-white/38">{campaign?.objective || "Board criativo compartilhado"}</p></div><div className="flex gap-2"><button type="button" onClick={() => onNavigate("/calendar")} className="inline-flex h-10 items-center gap-2 rounded-xl border border-white/[0.09] px-3 text-[11px] font-bold text-white/55"><CalendarDays className="h-4 w-4" /> Agenda</button><button type="button" onClick={() => onNavigate(`/projects/${campaignId}/creative`)} className="inline-flex h-10 items-center gap-2 rounded-xl bg-[#ff6969] px-4 text-[11px] font-extrabold text-[#260707]"><Plus className="h-4 w-4" /> Criar peça</button></div></header>
      <nav className="mb-5 flex gap-1 overflow-x-auto border-b border-white/[0.07] pb-2">{[
        ["Board", `/projects/${campaignId}`],
        ["Moodboard", `/campaigns/${campaignId}/moodboard`],
        ["Conteúdos", `/content?campaign=${campaignId}`],
        ["Calendário", `/calendar?campaign=${campaignId}`],
        ["Resultados", `/analytics/learning?campaign=${campaignId}`],
      ].map(([tab, path], index) => <button key={tab} type="button" onClick={() => onNavigate(path)} className={`rounded-xl px-3 py-2 text-[11px] font-bold ${index === 0 ? "bg-white text-black" : "text-white/38 hover:text-white"}`}>{tab}</button>)}</nav>
      <div className="grid min-w-[1000px] grid-cols-4 gap-3 overflow-x-auto pb-4">{stages.map(({ label, icon: Icon, items }, column) => <section key={label} className="min-h-[540px] rounded-[22px] border border-white/[0.07] bg-white/[0.018] p-3"><div className="flex items-center gap-2 px-1 py-2"><Icon className="h-4 w-4 text-[#ff8d68]" /><h2 className="text-[12px] font-bold text-white/65">{label}</h2><span className="ml-auto rounded-full bg-white/[0.05] px-2 py-0.5 text-[10px] text-white/30">{items.length}</span></div><div className="mt-2 space-y-3">{items.slice(0, 4).map((post, index) => <button key={post.id} type="button" onClick={() => onNavigate(`/content/${post.id}/edit?mode=visual`)} className="group w-full overflow-hidden rounded-[18px] border border-white/[0.08] bg-[#18181a] text-left hover:border-white/[0.15]"><div className="aspect-[16/10] overflow-hidden"><Artwork post={post} index={column + index} className="transition duration-500 group-hover:scale-105" /></div><div className="p-3"><strong className="block truncate text-[12px] text-white/75">{post.title}</strong><span className="mt-2 flex items-center gap-2 text-[10px] text-white/28"><span>{post.format}</span><span>·</span><span>{post.author}</span></span></div></button>)}{items.length === 0 && <button type="button" onClick={() => onNavigate(`/projects/${campaignId}/creative`)} className="flex min-h-[120px] w-full flex-col items-center justify-center rounded-[18px] border border-dashed border-white/[0.08] text-[11px] text-white/25 hover:border-white/[0.16] hover:text-white/50"><Plus className="mb-2 h-4 w-4" />Adicionar ao board</button>}</div></section>)}</div>
    </div>
  );
}
