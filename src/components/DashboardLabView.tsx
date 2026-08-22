import React from "react";
import {
  ArrowRight,
  CalendarDays,
  CheckCircle2,
  Clock3,
  FileImage,
  Film,
  Grid2X2,
  Image,
  Instagram,
  Layers3,
  LoaderCircle,
  MessageSquareText,
  Plus,
  Send,
  Sparkles,
} from "lucide-react";
import type { AIActionSuggestion, NavigationTab, Post, Workspace } from "../types";
import { useOperations } from "../context/OperationsContext";
import { useAIChat } from "../context/AIChatContext";
import { useProductData } from "../context/ProductDataContext";

interface DashboardViewProps {
  posts: Post[];
  suggestions: AIActionSuggestion[];
  activeWorkspace: Workspace;
  onNavigate: (tab: NavigationTab) => void;
  onOpenCampaignWizard: () => void;
  onNewPost: () => void;
  onSelectPost: (post: Post) => void;
}

const fallbackLooks = [
  "linear-gradient(135deg,#331b39 0%,#a94f67 48%,#ffb26f 100%)",
  "linear-gradient(145deg,#102a32 0%,#256f70 46%,#e8bf83 100%)",
  "linear-gradient(145deg,#1e1d42 0%,#5d55b9 50%,#ef9db8 100%)",
  "linear-gradient(145deg,#382317 0%,#c76b34 52%,#f4d1a1 100%)",
];

function MediaCard({ post, index, onClick }: { post?: Post; index: number; onClick: () => void }) {
  return (
    <button type="button" onClick={onClick} className="clicko-media-card group relative aspect-[4/3] overflow-hidden rounded-[22px] border border-white/[0.08] bg-[#1a1a1c] text-left">
      {post?.imageUrl ? (
        <img src={post.imageUrl} alt="" className="absolute inset-0 h-full w-full object-cover transition duration-500 group-hover:scale-[1.035]" />
      ) : (
        <span className="absolute inset-0" style={{ background: fallbackLooks[index % fallbackLooks.length] }} />
      )}
      <span className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/5 to-transparent" />
      <span className="absolute inset-x-0 bottom-0 p-4">
        <strong className="block truncate text-[14px] font-bold text-white">{post?.title || ["Manifesto de marca", "Coleção editorial", "Reels de produto", "Campanha de lançamento"][index % 4]}</strong>
        <small className="mt-1 block text-[11px] text-white/55">{post ? `${post.format} · ${post.status}` : "Explorar formato"}</small>
      </span>
    </button>
  );
}

export const DashboardView: React.FC<DashboardViewProps> = ({
  activeWorkspace,
  onNavigate,
  onOpenCampaignWizard,
  onNewPost,
}) => {
  const operations = useOperations();
  const productData = useProductData();
  const { sendMessage, loading } = useAIChat();
  const [command, setCommand] = React.useState("");
  const posts = productData.status === "ready" && productData.snapshot
    ? (productData.snapshot.posts as unknown as Post[])
    : operations.posts;
  const campaigns = productData.status === "ready" && productData.snapshot
    ? productData.snapshot.campaigns
    : operations.campaigns;
  const recent = [...posts].sort((a, b) => Date.parse(b.createdAt) - Date.parse(a.createdAt)).slice(0, 4);
  const scheduled = posts.filter((post) => post.status === "scheduled").slice(0, 3);
  const pending = posts.filter((post) => ["in_review", "pending_approval", "changes_requested"].includes(post.status));
  const activeCampaign = operations.activeCampaign || campaigns[0];
  const featured = recent.find((post) => post.campaignId === activeCampaign?.id) || recent[0];

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    const value = command.trim();
    if (!value || loading) return;
    void sendMessage(value, "dashboard");
    setCommand("");
    onOpenCampaignWizard();
  };

  const formats = [
    { label: "Post", detail: "1:1", icon: FileImage, action: onNewPost },
    { label: "Carrossel", detail: "4:5", icon: Grid2X2, action: () => onNavigate("create-copy") },
    { label: "Imagem", detail: "Visual", icon: Image, action: () => onNavigate("create-image") },
    { label: "Vídeo", detail: "Reels", icon: Film, action: () => onNavigate("create-video") },
  ];

  return (
    <div className="clicko-lab-home mx-auto w-full max-w-[1560px] px-5 pb-14 pt-7 lg:px-8">
      <section className="grid gap-6 xl:grid-cols-[minmax(0,1.55fr)_minmax(320px,.65fr)]">
        <div className="overflow-hidden rounded-[30px] border border-white/[0.08] bg-[#18181a] p-5 sm:p-7">
          <div className="max-w-3xl">
            <span className="text-[12px] font-bold text-[#ff8d68]">{activeWorkspace?.name || "Seu workspace"}</span>
            <h1 className="clicko-display mt-2 text-[clamp(32px,4vw,58px)] font-semibold leading-[.96] tracking-[-.055em] text-white">
              O que vamos criar hoje?
            </h1>
          </div>

          <form onSubmit={submit} className="mt-7 flex min-h-[70px] items-center gap-3 rounded-[20px] border border-white/[0.1] bg-black/25 p-2.5 pl-4 focus-within:border-[#ff6969]/55">
            <Sparkles className="h-5 w-5 shrink-0 text-[#ff8d68]" />
            <input
              value={command}
              onChange={(event) => setCommand(event.target.value)}
              placeholder="Descreva uma ideia, campanha ou envie uma referência…"
              className="min-w-0 flex-1 bg-transparent text-[14px] text-white outline-none placeholder:text-white/28"
            />
            <button type="button" onClick={() => onNavigate("library")} className="hidden h-11 items-center gap-2 rounded-xl border border-white/[0.08] px-3 text-[12px] font-semibold text-white/50 hover:text-white sm:flex">
              <Plus className="h-4 w-4" /> Referência
            </button>
            <button type="submit" disabled={!command.trim() || loading} aria-label="Criar a partir desta ideia" className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-[#ff6969] text-[#260707] disabled:opacity-35">
              {loading ? <LoaderCircle className="h-5 w-5 animate-spin" /> : <Send className="h-5 w-5" />}
            </button>
          </form>

          <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
            {formats.map(({ label, detail, icon: Icon, action }) => (
              <button key={label} type="button" onClick={action} className="flex items-center gap-3 rounded-2xl border border-white/[0.07] bg-white/[0.025] p-3 text-left transition hover:-translate-y-0.5 hover:border-white/[0.14] hover:bg-white/[0.05]">
                <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-white/[0.06] text-[#ff8d68]"><Icon className="h-4 w-4" /></span>
                <span><strong className="block text-[12px] text-white">{label}</strong><small className="mt-0.5 block text-[11px] text-white/32">{detail}</small></span>
              </button>
            ))}
          </div>
        </div>

        <button
          type="button"
          onClick={() => onNavigate("strategy")}
          className="group relative min-h-[310px] overflow-hidden rounded-[30px] border border-white/[0.08] bg-[#1d1719] text-left"
        >
          {featured?.imageUrl ? <img src={featured.imageUrl} alt="" className="absolute inset-0 h-full w-full object-cover transition duration-700 group-hover:scale-105" /> : <span className="absolute inset-0" style={{ background: fallbackLooks[0] }} />}
          <span className="absolute inset-0 bg-gradient-to-t from-black via-black/15 to-black/5" />
          <span className="absolute inset-x-0 bottom-0 p-6">
            <small className="text-[11px] font-bold uppercase tracking-[.14em] text-[#ffb37c]">Continue criando</small>
            <strong className="clicko-display mt-2 block text-[25px] font-semibold tracking-[-.035em] text-white">{activeCampaign?.name || "Projeto em foco"}</strong>
            <span className="mt-2 flex items-center gap-2 text-[12px] text-white/55">Abrir projeto <ArrowRight className="h-4 w-4 transition group-hover:translate-x-1" /></span>
          </span>
        </button>
      </section>

      <section className="mt-9 grid gap-8 xl:grid-cols-[minmax(0,1fr)_350px]">
        <div>
          <div className="mb-4 flex items-center justify-between">
            <div><h2 className="clicko-display text-[22px] font-semibold tracking-[-.035em] text-white">Criações recentes</h2><p className="mt-1 text-[12px] text-white/35">Peças, rascunhos e variações do workspace.</p></div>
            <button type="button" onClick={() => onNavigate("library")} className="inline-flex min-h-11 items-center text-[12px] font-bold text-white/50 hover:text-white">Ver biblioteca</button>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {Array.from({ length: 4 }, (_, index) => (
              <React.Fragment key={recent[index]?.id || index}>
                <MediaCard post={recent[index]} index={index} onClick={() => recent[index] ? onNavigate("library") : onNewPost()} />
              </React.Fragment>
            ))}
          </div>

          <div className="mt-9 flex items-end justify-between gap-4">
            <div><h2 className="clicko-display text-[22px] font-semibold tracking-[-.035em] text-white">Projetos ativos</h2><p className="mt-1 text-[12px] text-white/35">Do briefing à publicação, no mesmo espaço.</p></div>
            <button type="button" onClick={() => onNavigate("strategy")} className="inline-flex min-h-11 items-center gap-2 text-[12px] font-bold text-white/55 hover:text-white">Todos os projetos <ArrowRight className="h-4 w-4" /></button>
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {campaigns.slice(0, 2).map((campaign, index) => {
              const count = posts.filter((post) => post.campaignId === campaign.id).length;
              return (
                <button key={campaign.id} type="button" onClick={() => onNavigate("strategy")} className="group flex min-h-[128px] items-center gap-4 rounded-[22px] border border-white/[0.08] bg-white/[0.025] p-4 text-left hover:bg-white/[0.045]">
                  <span className="h-24 w-24 shrink-0 rounded-[16px]" style={{ background: fallbackLooks[(index + 1) % fallbackLooks.length] }} />
                  <span className="min-w-0"><small className="text-[11px] font-bold text-[#ff8d68]">{campaign.status}</small><strong className="mt-1 block truncate text-[15px] text-white">{campaign.name}</strong><span className="mt-3 flex items-center gap-3 text-[11px] text-white/35"><span className="flex items-center gap-1"><Layers3 className="h-3.5 w-3.5" /> {count} peças</span><span>v{campaign.brainRevision}</span></span></span>
                </button>
              );
            })}
          </div>
        </div>

        <aside className="space-y-4">
          <section className="rounded-[24px] border border-white/[0.08] bg-white/[0.025] p-5">
            <div className="flex items-center justify-between"><h2 className="text-[14px] font-bold text-white">Próximas publicações</h2><button type="button" onClick={() => onNavigate("calendar")} aria-label="Abrir calendário" className="grid h-11 w-11 place-items-center text-white/35 hover:text-white"><CalendarDays className="h-4 w-4" /></button></div>
            <div className="mt-4 space-y-2">
              {scheduled.length ? scheduled.map((post) => (
                <button key={post.id} type="button" onClick={() => onNavigate("calendar")} className="flex w-full items-center gap-3 rounded-2xl p-2 text-left hover:bg-white/[0.04]">
                  <span className="grid h-10 w-10 place-items-center rounded-xl bg-[#ff6969]/10 text-[#ff8585]"><Instagram className="h-4 w-4" /></span>
                  <span className="min-w-0 flex-1"><strong className="block truncate text-[12px] text-white/80">{post.title}</strong><small className="mt-1 block text-[11px] text-white/32">{post.scheduledAt ? new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }).format(new Date(post.scheduledAt)) : "Sem data"}</small></span>
                </button>
              )) : <p className="rounded-2xl border border-dashed border-white/[0.08] p-4 text-[12px] leading-5 text-white/35">Nada agendado. Sua agenda continua honesta e vazia.</p>}
            </div>
          </section>

          <section className="rounded-[24px] border border-white/[0.08] bg-white/[0.025] p-5">
            <div className="flex items-center justify-between"><h2 className="text-[14px] font-bold text-white">Decisões</h2><span className="rounded-full bg-[#ffb36b]/10 px-2 py-1 text-[11px] font-bold text-[#ffb36b]">{pending.length}</span></div>
            <button type="button" onClick={() => onNavigate("approvals")} className="mt-4 flex w-full items-center gap-3 rounded-2xl bg-white/[0.035] p-3 text-left hover:bg-white/[0.06]">
              <span className="grid h-10 w-10 place-items-center rounded-xl bg-white/[0.05] text-white/55">{pending.length ? <Clock3 className="h-4 w-4" /> : <CheckCircle2 className="h-4 w-4" />}</span>
              <span><strong className="block text-[12px] text-white/80">{pending.length ? `${pending.length} peças aguardam revisão` : "Tudo revisado"}</strong><small className="mt-1 block text-[11px] text-white/32">Abrir contexto e comentários</small></span>
            </button>
          </section>

          <section className="rounded-[24px] border border-[#ff6969]/20 bg-[#ff6969]/[0.055] p-5">
            <MessageSquareText className="h-5 w-5 text-[#ff8585]" />
            <h2 className="mt-4 text-[13px] font-bold text-white">Próximo aprendizado</h2>
            <p className="mt-2 text-[12px] leading-5 text-white/48">Conecte métricas de publicação para o Clicko recomendar formatos com evidência real.</p>
            <button type="button" onClick={() => onNavigate("analytics")} className="mt-4 inline-flex min-h-11 items-center text-[12px] font-bold text-[#ff8585]">Configurar métricas</button>
          </section>
        </aside>
      </section>
    </div>
  );
};
