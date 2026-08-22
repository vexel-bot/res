import React from "react";
import {
  Activity,
  ArrowRight,
  BadgeCheck,
  BarChart3,
  BookOpen,
  Box,
  CalendarDays,
  Check,
  ChevronRight,
  CircleAlert,
  Clock3,
  Copy,
  Download,
  Eye,
  FileText,
  Filter,
  Gauge,
  GitBranch,
  Grid2X2,
  Image,
  Layers3,
  LayoutDashboard,
  Link2,
  List,
  LockKeyhole,
  MessageSquare,
  MonitorPlay,
  MoreHorizontal,
  Move,
  Palette,
  PanelRight,
  Play,
  Plus,
  Radar,
  RefreshCcw,
  Save,
  Search,
  Send,
  Settings2,
  ShieldCheck,
  Sparkles,
  Target,
  Type,
  Upload,
  Users,
  WandSparkles,
  Workflow,
  X,
} from "lucide-react";
import { apiFetch } from "../api";
import {
  productApi,
  type CreativeCanvas,
  type CreativeRecord,
} from "../api/productApi";
import { useOperations } from "../context/OperationsContext";
import { useProductData } from "../context/ProductDataContext";
import { useServerState } from "../context/ServerStateContext";
import { useCreativeAutosave } from "../features/creative-lab/useCreativeAutosave";
import type { Post, PostFormat } from "../types";
import {
  SCREEN_TOTALS,
  STITCH_SCREENS,
  type StitchScreen,
} from "./screenManifest";
import {
  LabCreateSurface,
  LabProjectBoard,
  LabProjectsSurface,
} from "./LabProjectSurfaces";
import {
  ContextTabs,
  LabLibrarySurface,
  LabPublishSurface,
  publishTabs,
  settingsTabs,
} from "./LabOperationsSurfaces";
import { TeamManagementView } from "../components/TeamManagementView";
import { SubscriptionView } from "../components/SubscriptionView";
import { AuditLogsView } from "../components/AuditLogsView";

type Navigate = (path: string) => void;

interface ProductSurfaceViewProps {
  pathname: string;
  search: string;
  onNavigate: Navigate;
}

type IconType = React.ComponentType<{ className?: string }>;

const SURFACE_CLASS = "rounded-2xl border border-white/[0.08] bg-white/[0.025]";
const BUTTON_CLASS =
  "inline-flex items-center justify-center gap-2 rounded-xl border border-white/[0.1] bg-white/[0.04] px-3.5 py-2 text-xs font-semibold text-white transition hover:border-white/20 hover:bg-white/[0.08] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--clicko-action)]";
const ACTION_CLASS =
  "inline-flex items-center justify-center gap-2 rounded-xl bg-[var(--clicko-action)] px-3.5 py-2 text-xs font-bold text-black transition hover:bg-[var(--clicko-action-hover)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--clicko-action)] disabled:cursor-not-allowed disabled:opacity-40";

function idFromPath(pathname: string, segment: string, fallback: string) {
  const match = pathname.match(new RegExp(`/${segment}/([^/]+)`));
  return match?.[1] || fallback;
}

export function isProductSurfacePath(pathname: string) {
  return (
    pathname === "/today" ||
    pathname === "/projects" ||
    pathname.startsWith("/projects/") ||
    pathname === "/campaigns" ||
    pathname === "/discover" ||
    pathname === "/radar" ||
    pathname === "/workspaces/new" ||
    pathname === "/settings/ai-governance" ||
    pathname === "/library/lineage" ||
    pathname === "/library/assets" ||
    pathname === "/templates" ||
    pathname === "/brand-memory" ||
    pathname === "/calendar" ||
    pathname === "/analytics/learning" ||
    pathname === "/content" ||
    pathname === "/content/dashboard" ||
    pathname.startsWith("/content/") ||
    /^\/campaigns\/.+/.test(pathname) ||
    /^\/approvals\/.+/.test(pathname) ||
    /^\/publish\/.+/.test(pathname) ||
    /^\/automations\/.+/.test(pathname) ||
    pathname === "/settings/channels" ||
    pathname === "/settings/team" ||
    pathname === "/settings/billing" ||
    pathname === "/settings/audit" ||
    pathname === "/reference/screens"
  );
}

function TodayCommandSurface({ onNavigate }: { onNavigate: Navigate }) {
  const operations = useOperations();
  const server = useServerState();
  const posts =
    server.status === "connected"
      ? server.bootstrap?.posts || []
      : operations.posts;
  const activeCampaign = operations.activeCampaign || operations.campaigns[0];
  const inProduction = posts.filter((post) =>
    ["draft", "in_review", "pending_approval"].includes(post.status),
  );
  const approved = posts.filter((post) => post.status === "approved");
  const scheduled = posts.filter((post) => post.status === "scheduled");
  const actions: Array<{
    label: string;
    detail: string;
    path: string;
    icon: IconType;
    accent: "action" | "creative";
  }> = [
    {
      label: "Explorar sinais",
      detail: "Newsroom e Radar",
      path: "/discover",
      icon: Radar,
      accent: "creative",
    },
    {
      label: "Abrir Campaign Room",
      detail: activeCampaign?.name || "Campanha ativa",
      path: `/campaigns/${activeCampaign?.id || "active"}`,
      icon: Target,
      accent: "action",
    },
    {
      label: "Criar conteúdo",
      detail: "Post, carrossel, visual ou vídeo",
      path: "/content/new",
      icon: Plus,
      accent: "action",
    },
    {
      label: "Revisar decisões",
      detail: `${inProduction.length} itens no fluxo`,
      path: `/approvals/${inProduction[0]?.id || posts[0]?.id || "post-1"}`,
      icon: BadgeCheck,
      accent: "creative",
    },
  ];
  const stages = [
    {
      label: "Descobrir",
      value: 6,
      detail: "oportunidades",
      path: "/discover",
    },
    {
      label: "Planejar",
      value: operations.campaigns.length,
      detail: "campanhas",
      path: `/campaigns/${activeCampaign?.id || "active"}`,
    },
    {
      label: "Criar",
      value: inProduction.length,
      detail: "em produção",
      path: "/content/dashboard",
    },
    {
      label: "Decidir",
      value: posts.filter((post) =>
        ["in_review", "pending_approval"].includes(post.status),
      ).length,
      detail: "pendências",
      path: "/approvals",
    },
    {
      label: "Distribuir",
      value: scheduled.length,
      detail: "agendados",
      path: "/calendar",
    },
    {
      label: "Aprender",
      value: operations.learningSignals.length,
      detail: "hipóteses",
      path: "/analytics/learning",
    },
  ];
  return (
    <>
      <section className="relative mb-5 overflow-hidden rounded-3xl border border-white/[0.08] bg-[var(--clicko-surface-1)] p-6 sm:p-8">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_82%_16%,rgba(255,122,0,.14),transparent_30%),radial-gradient(circle_at_66%_100%,rgba(255,92,92,.1),transparent_34%)]" />
        <div className="relative grid gap-8 xl:grid-cols-[1fr_360px] xl:items-end">
          <div>
            <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-[var(--clicko-creative)]">
              <span className="h-1.5 w-1.5 rounded-full bg-[var(--clicko-creative)]" />
              Hoje · Command Center
            </div>
            <h1 className="mt-5 max-w-3xl text-4xl font-semibold leading-[0.98] tracking-[-0.055em] text-white sm:text-5xl">
              Da oportunidade ao aprendizado, sem perder o contexto.
            </h1>
            <p className="mt-4 max-w-2xl text-sm leading-6 text-white/45">
              O ciclo operacional do Clicko reúne sinais, campanha, criação,
              decisão e performance em uma única sequência rastreável.
            </p>
          </div>
          <div className="rounded-2xl border border-white/[0.08] bg-black/35 p-4 backdrop-blur">
            <div className="flex items-center justify-between">
              <span className="text-[9px] font-bold uppercase tracking-[0.17em] text-white/35">
                Próxima decisão
              </span>
              <StatusPill tone={inProduction.length ? "warn" : "good"}>
                {inProduction.length ? "Ação necessária" : "Fluxo limpo"}
              </StatusPill>
            </div>
            <div className="mt-5 text-base font-semibold text-white">
              {inProduction[0]?.title || "Nenhuma pendência crítica"}
            </div>
            <p className="mt-2 text-xs leading-5 text-white/40">
              {inProduction.length
                ? "Revise evidências, comentários e versão antes de liberar a distribuição."
                : "O próximo movimento pode começar pelo Radar."}
            </p>
            <button
              onClick={() =>
                onNavigate(
                  inProduction[0]
                    ? `/approvals/${inProduction[0].id}`
                    : "/discover",
                )
              }
              className={`${ACTION_CLASS} mt-5 w-full`}
            >
              {inProduction.length
                ? "Abrir Approval Room"
                : "Descobrir oportunidade"}
              <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      </section>

      <div className="mb-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {actions.map(({ label, detail, path, icon: Icon, accent }) => (
          <button
            key={label}
            onClick={() => onNavigate(path)}
            className="group rounded-2xl border border-white/[0.08] bg-white/[0.025] p-4 text-left transition hover:-translate-y-0.5 hover:border-white/20 hover:bg-white/[0.04]"
          >
            <div
              className={`grid h-9 w-9 place-items-center rounded-xl border ${accent === "creative" ? "border-[var(--clicko-creative)]/25 bg-[var(--clicko-creative)]/10 text-[var(--clicko-creative)]" : "border-[var(--clicko-action)]/25 bg-[var(--clicko-action)]/10 text-[var(--clicko-action)]"}`}
            >
              <Icon className="h-4 w-4" />
            </div>
            <div className="mt-7 flex items-end justify-between gap-3">
              <div>
                <div className="text-sm font-semibold text-white">{label}</div>
                <div className="mt-1 text-[10px] text-white/35">{detail}</div>
              </div>
              <ArrowRight className="h-4 w-4 text-white/25 transition group-hover:translate-x-1 group-hover:text-white" />
            </div>
          </button>
        ))}
      </div>

      <div className="grid gap-4 xl:grid-cols-[1fr_350px]">
        <Panel
          title="Ciclo operacional"
          eyebrow="Uma sequência, seis decisões"
          action={
            <button
              onClick={() => onNavigate("/content/dashboard")}
              className={BUTTON_CLASS}
            >
              Ver operação
              <ArrowRight className="h-3.5 w-3.5" />
            </button>
          }
        >
          <div className="grid gap-px overflow-hidden bg-white/[0.06] sm:grid-cols-2 xl:grid-cols-3">
            {stages.map((stage, index) => (
              <button
                key={stage.label}
                onClick={() => onNavigate(stage.path)}
                className="group bg-[var(--clicko-surface-1)] p-5 text-left transition hover:bg-[var(--clicko-surface-2)]"
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-[10px] text-[var(--clicko-creative)]">
                    0{index + 1}
                  </span>
                  <ChevronRight className="h-3.5 w-3.5 text-white/20 group-hover:text-white" />
                </div>
                <div className="mt-8 text-sm font-semibold text-white">
                  {stage.label}
                </div>
                <div className="mt-2 flex items-baseline gap-2">
                  <strong className="text-2xl font-semibold text-white">
                    {stage.value}
                  </strong>
                  <span className="text-[10px] text-white/35">
                    {stage.detail}
                  </span>
                </div>
              </button>
            ))}
          </div>
        </Panel>
        <div className="space-y-4">
          <Panel title="Campanha em foco" eyebrow="Contexto ativo">
            <div className="p-5">
              <StatusPill tone="good">
                {activeCampaign?.status || "ativa"}
              </StatusPill>
              <h2 className="mt-4 text-lg font-semibold tracking-tight text-white">
                {activeCampaign?.name || "Nenhuma campanha ativa"}
              </h2>
              <p className="mt-2 line-clamp-3 text-xs leading-5 text-white/40">
                {activeCampaign?.objective ||
                  "Comece a partir de uma oportunidade do Radar."}
              </p>
              <div className="mt-5 flex gap-2">
                <button
                  onClick={() =>
                    onNavigate(`/campaigns/${activeCampaign?.id || "active"}`)
                  }
                  className={BUTTON_CLASS}
                >
                  Campaign Room
                </button>
                <button
                  onClick={() =>
                    onNavigate(
                      `/campaigns/${activeCampaign?.id || "active"}/studio`,
                    )
                  }
                  className={BUTTON_CLASS}
                >
                  Studio
                </button>
              </div>
            </div>
          </Panel>
          <Panel title="Saúde do fluxo" eyebrow="Agora">
            <div className="grid grid-cols-3 divide-x divide-white/[0.06] p-4 text-center">
              <div>
                <div className="text-xl font-semibold text-white">
                  {posts.length}
                </div>
                <div className="mt-1 text-[9px] text-white/30">conteúdos</div>
              </div>
              <div>
                <div className="text-xl font-semibold text-white">
                  {approved.length}
                </div>
                <div className="mt-1 text-[9px] text-white/30">aprovados</div>
              </div>
              <div>
                <div className="text-xl font-semibold text-white">
                  {scheduled.length}
                </div>
                <div className="mt-1 text-[9px] text-white/30">agendados</div>
              </div>
            </div>
          </Panel>
        </div>
      </div>
    </>
  );
}

function ProjectsSurface({ onNavigate }: { onNavigate: Navigate }) {
  const operations = useOperations();
  const productData = useProductData();
  const campaigns =
    productData.status === "ready" && productData.snapshot
      ? productData.snapshot.campaigns
      : operations.campaigns;
  const posts =
    productData.status === "ready" && productData.snapshot
      ? productData.snapshot.posts
      : operations.posts;
  const campaignCount = campaigns.length;
  const linkedPosts = posts.filter((post) => post.campaignId);

  return (
    <>
      <SurfaceHeader
        eyebrow="Projetos e campanhas"
        title="Onde a estratégia vira produção"
        description="Cada projeto preserva briefing, mundo criativo, peças, decisões e resultados em uma única linha de contexto."
        action="Novo projeto"
        onAction={() => onNavigate("/campaigns/new")}
        breadcrumbs={["Operação", "Projetos"]}
      />
      <div className="mb-4 grid gap-3 sm:grid-cols-3">
        <Stat
          label="Projetos"
          value={campaignCount}
          detail="no workspace atual"
          icon={Target}
        />
        <Stat
          label="Conteúdos ligados"
          value={linkedPosts.length}
          detail="com origem preservada"
          icon={Layers3}
        />
        <Stat
          label="Creative Lab"
          value="19"
          detail="ferramentas e estados conectados"
          icon={Palette}
        />
      </div>
      {campaignCount === 0 ? (
        <Panel>
          <div className="grid min-h-[360px] place-items-center p-8 text-center">
            <div>
              <Target className="mx-auto h-8 w-8 text-[var(--clicko-creative)]" />
              <h2 className="mt-4 text-xl font-semibold text-white">
                Comece pelo contexto, não por uma tela vazia.
              </h2>
              <p className="mx-auto mt-2 max-w-lg text-sm leading-6 text-white/45">
                Crie um projeto a partir do Radar ou de um briefing. O Clicko
                levará público, objetivo, oferta e restrições para o Creative
                Lab.
              </p>
              <button
                type="button"
                onClick={() => onNavigate("/campaigns/new")}
                className={`${ACTION_CLASS} mt-6`}
              >
                <Plus className="h-4 w-4" />
                Criar primeiro projeto
              </button>
            </div>
          </div>
        </Panel>
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {campaigns.map((campaign) => {
            const campaignPosts = posts.filter(
              (post) => post.campaignId === campaign.id,
            );
            const pending = campaignPosts.filter((post) =>
              ["in_review", "pending_approval"].includes(post.status),
            ).length;
            const isActive =
              campaign.id === operations.activeCampaign?.id ||
              campaign.status === "active";
            return (
              <article
                key={campaign.id}
                className={`${SURFACE_CLASS} group overflow-hidden`}
              >
                <button
                  type="button"
                  onClick={() => {
                    operations.setActiveCampaignId(campaign.id);
                    onNavigate(`/projects/${campaign.id}`);
                  }}
                  className="block w-full p-5 text-left transition hover:bg-white/[0.02]"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="grid h-11 w-11 place-items-center rounded-xl border border-[var(--clicko-creative)]/25 bg-[var(--clicko-creative)]/10 text-[var(--clicko-creative)]">
                      <Target className="h-5 w-5" />
                    </div>
                    <StatusPill tone={isActive ? "good" : "neutral"}>
                      {isActive ? "Em foco" : campaign.status}
                    </StatusPill>
                  </div>
                  <h2 className="mt-8 text-xl font-semibold tracking-tight text-white">
                    {campaign.name}
                  </h2>
                  <p className="mt-2 line-clamp-2 text-sm leading-6 text-white/45">
                    {campaign.objective}
                  </p>
                  <div className="mt-6 grid grid-cols-3 divide-x divide-white/[0.07] border-y border-white/[0.07] py-3 text-center">
                    <div>
                      <strong className="block text-lg text-white">
                        {campaignPosts.length}
                      </strong>
                      <span className="text-[9px] uppercase tracking-wider text-white/30">
                        peças
                      </span>
                    </div>
                    <div>
                      <strong className="block text-lg text-white">
                        {pending}
                      </strong>
                      <span className="text-[9px] uppercase tracking-wider text-white/30">
                        decisões
                      </span>
                    </div>
                    <div>
                      <strong className="block text-lg text-white">
                        v{campaign.brainRevision}
                      </strong>
                      <span className="text-[9px] uppercase tracking-wider text-white/30">
                        memória
                      </span>
                    </div>
                  </div>
                </button>
                <div className="flex gap-2 border-t border-white/[0.06] p-3">
                  <button
                    type="button"
                    onClick={() => {
                      operations.setActiveCampaignId(campaign.id);
                      onNavigate(`/projects/${campaign.id}`);
                    }}
                    className={`${BUTTON_CLASS} flex-1`}
                  >
                    Abrir projeto
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      operations.setActiveCampaignId(campaign.id);
                      onNavigate(`/projects/${campaign.id}/creative`);
                    }}
                    className={`${ACTION_CLASS} flex-1`}
                  >
                    <Palette className="h-4 w-4" />
                    Creative Lab
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </>
  );
}

function CreativeLabHub({
  campaignId,
  onNavigate,
}: {
  campaignId: string;
  onNavigate: Navigate;
}) {
  const operations = useOperations();
  const productData = useProductData();
  const campaigns =
    productData.status === "ready" && productData.snapshot
      ? productData.snapshot.campaigns
      : operations.campaigns;
  const posts =
    productData.status === "ready" && productData.snapshot
      ? productData.snapshot.posts
      : operations.posts;
  const campaign =
    campaigns.find((item) => item.id === campaignId) ||
    operations.activeCampaign ||
    campaigns[0];
  const effectiveCampaignId = campaign?.id || "active";
  const campaignPost =
    posts.find((post) => post.campaignId === effectiveCampaignId) || posts[0];
  const labScreens = STITCH_SCREENS.filter(
    (screen) => screen.project === "creative-lab",
  );
  const labFlow = [
    {
      title: "Fundação da campanha",
      description: "Mundo, referências e ativos de marca antes de produzir.",
      ids: ["B04", "B01", "B09"],
      icon: BookOpen,
    },
    {
      title: "Direção editorial",
      description: "Planejar, criar e acompanhar conteúdos no mesmo contexto.",
      ids: ["B16", "B02", "B08", "B17", "B05", "B15"],
      icon: FileText,
    },
    {
      title: "Composição visual",
      description:
        "Canvas, tipografia, elementos, luz e handoff em uma sessão.",
      ids: ["B03", "B07", "B18", "B19", "B11"],
      icon: Palette,
    },
    {
      title: "Desdobramento",
      description: "Variações, remix, carrossel e motion a partir da peça-mãe.",
      ids: ["B10", "B12", "B13", "B14"],
      icon: Layers3,
    },
    {
      title: "Decisão criativa",
      description:
        "Revisar a peça com contexto, comentários e rastreabilidade.",
      ids: ["B06"],
      icon: BadgeCheck,
    },
  ];
  const resolveRoute = (route: string) => {
    let next = route
      .replace("/campaigns/active", `/campaigns/${effectiveCampaignId}`)
      .replace("/content/post-1", `/content/${campaignPost?.id || "post-1"}`)
      .replace(
        "/approvals/post-1",
        `/approvals/${campaignPost?.id || "post-1"}`,
      );
    if (next.startsWith("/content/draft/edit"))
      next += `${next.includes("?") ? "&" : "?"}campaign=${effectiveCampaignId}`;
    return next;
  };

  React.useEffect(() => {
    if (
      campaign?.id &&
      operations.campaigns.some((item) => item.id === campaign.id)
    )
      operations.setActiveCampaignId(campaign.id);
  }, [campaign?.id, operations.campaigns, operations.setActiveCampaignId]);

  return (
    <>
      <SurfaceHeader
        eyebrow="Creative Lab"
        title={campaign?.name || "Laboratório criativo"}
        description="Uma linha de produção contínua: direção, criação, desdobramento e decisão compartilham o mesmo projeto e histórico."
        action="Criar peça"
        onAction={() =>
          onNavigate(
            `/content/draft/edit?mode=visual&campaign=${effectiveCampaignId}`,
          )
        }
        breadcrumbs={[
          "Projetos",
          campaign?.name || "Projeto ativo",
          "Creative Lab",
        ]}
      />
      <div className="mb-5 flex gap-2 overflow-x-auto border-b border-white/[0.08] pb-3">
        <button
          type="button"
          onClick={() => onNavigate(`/projects/${effectiveCampaignId}`)}
          className={BUTTON_CLASS}
        >
          Visão geral
        </button>
        <button
          type="button"
          onClick={() => onNavigate(`/campaigns/${effectiveCampaignId}/world`)}
          className={BUTTON_CLASS}
        >
          Mundo
        </button>
        <button
          type="button"
          onClick={() =>
            onNavigate(`/campaigns/${effectiveCampaignId}/moodboard`)
          }
          className={BUTTON_CLASS}
        >
          Moodboard
        </button>
        <button
          type="button"
          className={`${ACTION_CLASS} pointer-events-none`}
          aria-current="page"
        >
          <Palette className="h-4 w-4" />
          Creative Lab
        </button>
      </div>
      <Panel title="Fluxo criativo do projeto" eyebrow="Produção conectada">
        <div className="grid gap-px overflow-hidden bg-white/[0.06] lg:grid-cols-2">
          {labFlow.map(({ title, description, ids, icon: Icon }) => {
            const screens = ids.flatMap((id) => {
              const screen = labScreens.find((item) => item.id === id);
              return screen ? [screen] : [];
            });
            return (
              <article key={title} className="bg-[var(--clicko-surface-1)] p-5">
                <div className="flex items-start gap-3">
                  <span className="grid h-9 w-9 shrink-0 place-items-center border border-[var(--clicko-creative)]/25 bg-[var(--clicko-creative)]/10 text-[var(--clicko-creative)]">
                    <Icon className="h-4 w-4" />
                  </span>
                  <div>
                    <h3 className="text-sm font-semibold text-white">
                      {title}
                    </h3>
                    <p className="mt-1 text-[10px] leading-5 text-white/40">
                      {description}
                    </p>
                  </div>
                </div>
                <div className="mt-5 flex flex-wrap gap-1.5">
                  {screens.map((screen, index) => (
                    <button
                      key={screen.id}
                      type="button"
                      data-creative-tool={screen.id}
                      onClick={() => onNavigate(resolveRoute(screen.route))}
                      className={`inline-flex items-center gap-2 border px-2.5 py-2 text-[9px] font-semibold transition ${index === 0 ? "border-[var(--clicko-action)]/35 bg-[var(--clicko-action)]/10 text-white" : "border-white/[0.08] text-white/45 hover:border-white/20 hover:text-white"}`}
                    >
                      {screen.frame
                        .replace(/^Clicko — /, "")
                        .replace(/ V\d+(\.\d+)?$/, "")
                        .replace(/ \(Canvas State\)$/, "")}
                      <ArrowRight className="h-3 w-3" />
                    </button>
                  ))}
                </div>
              </article>
            );
          })}
        </div>
      </Panel>
    </>
  );
}

function SurfaceHeader({
  eyebrow,
  title,
  description,
  action,
  onAction,
  breadcrumbs = [],
}: {
  eyebrow: string;
  title: string;
  description: string;
  action?: string;
  onAction?: () => void;
  breadcrumbs?: string[];
}) {
  return (
    <header className="mb-6 flex flex-wrap items-end justify-between gap-5">
      <div className="min-w-0 max-w-3xl">
        {breadcrumbs.length > 0 && (
          <div className="mb-3 flex flex-wrap items-center gap-1.5 text-[10px] font-semibold uppercase tracking-[0.16em] text-white/35">
            {breadcrumbs.map((item, index) => (
              <React.Fragment key={`${item}-${index}`}>
                {index > 0 && <ChevronRight className="h-3 w-3" />}
                <span>{item}</span>
              </React.Fragment>
            ))}
          </div>
        )}
        <div className="mb-2 flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-[var(--clicko-creative)]">
          <span className="h-1.5 w-1.5 rounded-full bg-[var(--clicko-creative)]" />
          {eyebrow}
        </div>
        <h1 className="text-3xl font-semibold tracking-[-0.04em] text-white sm:text-4xl">
          {title}
        </h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-white/50">
          {description}
        </p>
      </div>
      {action && (
        <button type="button" onClick={onAction} className={ACTION_CLASS}>
          {action}
          <ArrowRight className="h-4 w-4" />
        </button>
      )}
    </header>
  );
}

function Panel({
  children,
  className = "",
  title,
  eyebrow,
  action,
}: React.PropsWithChildren<{
  className?: string;
  title?: string;
  eyebrow?: string;
  action?: React.ReactNode;
}>) {
  return (
    <section className={`${SURFACE_CLASS} ${className}`}>
      {(title || eyebrow || action) && (
        <div className="flex items-center justify-between gap-4 border-b border-white/[0.06] px-5 py-4">
          <div>
            {eyebrow && (
              <div className="text-[9px] font-bold uppercase tracking-[0.18em] text-white/35">
                {eyebrow}
              </div>
            )}
            {title && (
              <h2 className="mt-0.5 text-sm font-semibold text-white">
                {title}
              </h2>
            )}
          </div>
          {action}
        </div>
      )}
      {children}
    </section>
  );
}

function Stat({
  label,
  value,
  detail,
  icon: Icon,
}: {
  label: string;
  value: string | number;
  detail: string;
  icon: IconType;
}) {
  return (
    <article className={`${SURFACE_CLASS} p-4`}>
      <div className="flex items-center justify-between text-white/40">
        <span className="text-[10px] font-bold uppercase tracking-[0.14em]">
          {label}
        </span>
        <Icon className="h-4 w-4 text-[var(--clicko-creative)]" />
      </div>
      <div className="mt-4 text-2xl font-semibold tracking-tight text-white">
        {value}
      </div>
      <div className="mt-1 text-[11px] text-white/40">{detail}</div>
    </article>
  );
}

function StatusPill({
  children,
  tone = "neutral",
}: React.PropsWithChildren<{ tone?: "neutral" | "good" | "warn" | "danger" }>) {
  const tones = {
    neutral: "border-white/10 bg-white/[0.04] text-white/55",
    good: "border-[var(--clicko-action)]/30 bg-[var(--clicko-action)]/10 text-[var(--clicko-action-hover)]",
    warn: "border-[var(--clicko-creative)]/30 bg-[var(--clicko-creative)]/10 text-[var(--clicko-creative-hover)]",
    danger:
      "border-[var(--clicko-danger)]/30 bg-[var(--clicko-danger)]/10 text-[var(--clicko-danger)]",
  };
  return (
    <span
      className={`inline-flex rounded-full border px-2 py-1 text-[9px] font-bold uppercase tracking-[0.12em] ${tones[tone]}`}
    >
      {children}
    </span>
  );
}

function ProductBreadcrumbBar({ onNavigate }: { onNavigate: Navigate }) {
  const links = [
    { label: "Hoje", path: "/today" },
    { label: "Descobrir", path: "/discover" },
    { label: "Radar", path: "/radar" },
    { label: "Campanha", path: "/campaigns/active" },
    { label: "Conteúdo", path: "/content/dashboard" },
    { label: "Referências 57/57", path: "/reference/screens" },
  ];
  return (
    <nav
      aria-label="Ciclo operacional"
      className="mb-6 flex gap-1 overflow-x-auto rounded-2xl border border-white/[0.06] bg-black/30 p-1.5"
    >
      {links.map((link) => (
        <button
          key={link.path}
          type="button"
          onClick={() => onNavigate(link.path)}
          className="shrink-0 rounded-xl px-3 py-2 text-[11px] font-semibold text-white/45 transition hover:bg-white/[0.05] hover:text-white"
        >
          {link.label}
        </button>
      ))}
    </nav>
  );
}

function DiscoverySurface({
  mode,
  onNavigate,
}: {
  mode: "discover" | "radar";
  onNavigate: Navigate;
}) {
  const { activeWorkspace, activeClient, learningSignals } = useOperations();
  const productData = useProductData();
  const radarState = productData.snapshot?.radar;
  const [query, setQuery] = React.useState("");
  const [riskFilter, setRiskFilter] = React.useState<"all" | "low">("all");
  const [feedback, setFeedback] = React.useState<
    Record<string, "saved" | "rejected">
  >({});
  const [backendState, setBackendState] = React.useState<
    "checking" | "ready" | "offline"
  >("checking");
  const signals = (radarState?.opportunities || []).filter(
    (signal) =>
      signal.eligible &&
      !signal.rejected &&
      signal.title.toLowerCase().includes(query.toLowerCase()) &&
      (riskFilter === "all" || signal.riskLevel === "low"),
  );
  const recordFeedback = async (
    opportunityId: string,
    eventType: "saved" | "rejected",
  ) => {
    setFeedback((current) => ({ ...current, [opportunityId]: eventType }));
    if (!productData.snapshot) return;
    try {
      await productApi.recordRadarFeedback({
        workspaceId: productData.snapshot.workspaceId,
        opportunityId,
        eventType,
        reason: eventType === "rejected" ? "Não combina com a marca" : null,
      });
      await productData.refresh();
    } catch {
      setFeedback((current) => {
        const next = { ...current };
        delete next[opportunityId];
        return next;
      });
    }
  };

  React.useEffect(() => {
    let active = true;
    apiFetch<{ status: string }>("/health/ready")
      .then(() => active && setBackendState("ready"))
      .catch(() => active && setBackendState("offline"));
    return () => {
      active = false;
    };
  }, []);

  return (
    <>
      <SurfaceHeader
        eyebrow={mode === "radar" ? "Inteligência de oportunidade" : "Newsroom"}
        title={
          mode === "radar"
            ? "Radar de oportunidades"
            : "Descobrir o próximo movimento"
        }
        description={`Sinais priorizados para ${activeClient?.name || activeWorkspace.name}, ligados à memória ativa e sem transformar hipótese em fato.`}
        action={mode === "radar" ? "Criar campanha" : "Abrir Radar"}
        onAction={() =>
          onNavigate(
            mode === "radar" ? "/campaigns/new?source=radar" : "/radar",
          )
        }
        breadcrumbs={["Operação", mode === "radar" ? "Radar" : "Descobrir"]}
      />
      <div className="mb-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Stat
          label="Sinais ativos"
          value={radarState?.signalCount || 0}
          detail={radarState?.collectionStatus || "sem coleta conectada"}
          icon={Radar}
        />
        <Stat
          label="Oportunidades"
          value={
            radarState?.opportunities.filter((item) => item.eligible).length ||
            0
          }
          detail={
            radarState?.state === "ready"
              ? "prontas para decisão"
              : radarState?.reason || "entre para sincronizar"
          }
          icon={Target}
        />
        <Stat
          label="Aprendizados"
          value={learningSignals.length}
          detail="com evidência rastreável"
          icon={BookOpen}
        />
        <Stat
          label="API funcional"
          value={
            backendState === "checking"
              ? "..."
              : backendState === "ready"
                ? "Online"
                : "Indisponível"
          }
          detail="health check local"
          icon={Activity}
        />
      </div>
      <div className="grid gap-4 xl:grid-cols-[1fr_320px]">
        <Panel
          title="Fila editorial priorizada"
          eyebrow="Janela de decisão"
          action={
            <button
              type="button"
              onClick={() =>
                setRiskFilter((value) => (value === "all" ? "low" : "all"))
              }
              aria-pressed={riskFilter === "low"}
              className={BUTTON_CLASS}
            >
              <Filter className="h-3.5 w-3.5" />
              {riskFilter === "low" ? "Risco baixo" : "Todos os riscos"}
            </button>
          }
        >
          <div className="border-b border-white/[0.06] p-4">
            <label className="flex items-center gap-2 rounded-xl border border-white/[0.08] bg-black/25 px-3 py-2.5">
              <Search className="h-4 w-4 text-white/30" />
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                className="min-w-0 flex-1 bg-transparent text-sm text-white outline-none placeholder:text-white/25"
                placeholder="Buscar sinal, fonte ou tema"
              />
            </label>
          </div>
          <div className="divide-y divide-white/[0.06]">
            {signals.map((signal, index) => (
              <article
                key={signal.title}
                className="group grid gap-4 p-5 transition hover:bg-white/[0.02] md:grid-cols-[auto_1fr_auto]"
              >
                <div className="grid h-10 w-10 place-items-center rounded-xl border border-[var(--clicko-creative)]/20 bg-[var(--clicko-creative)]/10 text-sm font-bold text-[var(--clicko-creative)]">
                  {Math.round(signal.score)}
                </div>
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <StatusPill
                      tone={
                        signal.scoreLabel.toLowerCase().includes("alta")
                          ? "good"
                          : "neutral"
                      }
                    >
                      {signal.scoreLabel || "Em avaliação"}
                    </StatusPill>
                    <span className="text-[10px] text-white/30">
                      {signal.windowLabel}
                    </span>
                  </div>
                  <h3 className="mt-2 text-sm font-semibold leading-5 text-white">
                    {signal.title}
                  </h3>
                  <p className="mt-1 text-[11px] text-white/40">
                    {String(signal.source?.name || "Fonte monitorada")} · risco{" "}
                    {signal.riskLevel}
                  </p>
                  <p className="mt-2 line-clamp-2 text-[11px] leading-5 text-white/35">
                    {signal.whyItFits || signal.bridge}
                  </p>
                </div>
                <div className="flex flex-col gap-2 self-center">
                  <button
                    type="button"
                    onClick={() =>
                      onNavigate(`/campaigns/new?opportunity=${signal.id}`)
                    }
                    className={ACTION_CLASS}
                  >
                    Criar campanha
                    <ChevronRight className="h-3.5 w-3.5" />
                  </button>
                  <div className="flex gap-1">
                    <button
                      type="button"
                      onClick={() => void recordFeedback(signal.id, "saved")}
                      className={`${BUTTON_CLASS} flex-1`}
                    >
                      {feedback[signal.id] === "saved" ? "Salvo" : "Salvar"}
                    </button>
                    <button
                      type="button"
                      onClick={() => void recordFeedback(signal.id, "rejected")}
                      className={`${BUTTON_CLASS} flex-1`}
                    >
                      {feedback[signal.id] === "rejected"
                        ? "Rejeitado"
                        : "Não combina"}
                    </button>
                  </div>
                </div>
              </article>
            ))}
            {signals.length === 0 && (
              <div className="p-8 text-center">
                <Radar className="mx-auto h-7 w-7 text-white/20" />
                <h3 className="mt-3 text-sm font-semibold text-white/60">
                  {radarState?.state === "ready"
                    ? "Nenhuma oportunidade para estes filtros"
                    : "Radar ainda sem oportunidades confirmadas"}
                </h3>
                <p className="mx-auto mt-2 max-w-lg text-xs leading-5 text-white/35">
                  {radarState?.reason ||
                    "Entre em um workspace conectado para usar sinais coletados. O Clicko não inventa tendências no modo local."}
                </p>
              </div>
            )}
          </div>
        </Panel>
        <div className="space-y-4">
          <Panel title="Preferências do Radar" eyebrow="Aprendizado">
            <div className="space-y-3 p-5 text-xs text-white/55">
              {(radarState?.evergreenSuggestions || []).map((item) => (
                <div
                  key={item.title}
                  className="flex items-center justify-between rounded-xl border border-white/[0.06] bg-black/20 p-3"
                >
                  <span>{item.title}</span>
                  <span className="font-mono text-[var(--clicko-creative)]">
                    {item.recommendedFormat}
                  </span>
                </div>
              ))}
              {!radarState?.evergreenSuggestions.length && (
                <div className="rounded-xl border border-dashed border-white/[0.07] p-4 text-center text-[10px] leading-5 text-white/35">
                  Sem sugestões fundamentadas disponíveis.
                </div>
              )}
            </div>
          </Panel>
          <Panel title="Fontes e transparência" eyebrow="Governança">
            <div className="p-5 text-xs leading-5 text-white/45">
              Cada oportunidade mantém fonte, janela, versão do ranking e
              feedback. A ausência de métrica aparece como ausência — nunca como
              número estimado.
            </div>
          </Panel>
        </div>
      </div>
    </>
  );
}

function CampaignSurface({
  pathname,
  search,
  onNavigate,
}: ProductSurfaceViewProps) {
  const operations = useOperations();
  const server = useServerState();
  const productData = useProductData();
  const params = new URLSearchParams(search);
  const opportunityId = params.get("opportunity");
  const opportunity = productData.snapshot?.radar.opportunities.find(
    (item) => item.id === opportunityId,
  );
  const campaigns =
    productData.status === "ready" && productData.snapshot
      ? productData.snapshot.campaigns
      : operations.campaigns;
  const posts =
    productData.status === "ready" && productData.snapshot
      ? productData.snapshot.posts
      : operations.posts;
  const campaignId = idFromPath(
    pathname,
    "campaigns",
    operations.activeCampaign?.id || "active",
  );
  const campaign =
    campaigns.find((item) => item.id === campaignId) ||
    operations.activeCampaign ||
    campaigns[0];
  const segment = pathname.split("/")[3] || "overview";
  const [name, setName] = React.useState(
    opportunity?.title || "Campanha orientada pela oportunidade",
  );
  const [objective, setObjective] = React.useState(
    opportunity
      ? `${opportunity.objective}: ${opportunity.bridge}`
      : "Transformar o sinal priorizado em uma narrativa coerente e mensurável.",
  );
  const [created, setCreated] = React.useState(false);

  if (campaignId === "new") {
    const create = async () => {
      if (server.status === "connected") {
        const remote = await server.createCampaign({
          opportunityId: opportunity?.id || null,
          originContext: opportunity
            ? {
                title: opportunity.title,
                source: opportunity.source,
                hook: opportunity.hook,
                bridge: opportunity.bridge,
                risks: opportunity.risks,
              }
            : {},
          name,
          objective,
          startDate: new Date().toISOString().slice(0, 10),
          endDate: new Date(Date.now() + 30 * 86400000)
            .toISOString()
            .slice(0, 10),
          kpis: ["Conteúdos aprovados", "Engajamento qualificado"],
          products:
            operations.activeClient?.products || operations.brain.products,
          audience:
            operations.activeClient?.audience || operations.brain.audience,
          offer: operations.activeClient?.featuredOffer || "Oferta principal",
          channels: ["instagram", "linkedin"],
          funnel: "Descoberta → Consideração → Decisão",
          ctas: ["Conhecer a proposta"],
          executionPlan: [
            "Validar narrativa",
            "Produzir kit inicial",
            "Revisar e publicar",
          ],
          status: "draft",
          brainRevision: operations.brain.revision,
        });
        setCreated(true);
        onNavigate(`/campaigns/${remote.id}`);
        return;
      }
      const next = operations.createCampaign({
        name,
        objective,
        startDate: new Date().toISOString().slice(0, 10),
        endDate: new Date(Date.now() + 30 * 86400000)
          .toISOString()
          .slice(0, 10),
        budget: "A definir",
        kpis: ["Conteúdos aprovados", "Engajamento qualificado"],
        products:
          operations.activeClient?.products || operations.brain.products,
        audience:
          operations.activeClient?.audience || operations.brain.audience,
        offer: operations.activeClient?.featuredOffer || "Oferta principal",
        channels: ["instagram", "linkedin"],
        importantDates: "",
        funnel: "Descoberta → Consideração → Decisão",
        ctas: ["Conhecer a proposta"],
        executionPlan: [
          "Validar narrativa",
          "Produzir kit inicial",
          "Revisar e publicar",
        ],
        status: "draft",
      });
      setCreated(true);
      window.setTimeout(() => onNavigate(`/campaigns/${next.id}`), 350);
    };
    return (
      <>
        <SurfaceHeader
          eyebrow="Campaign Intake"
          title="Da oportunidade à campanha"
          description="Uma revisão curta, já preenchida pelo contexto do Radar e pela memória ativa da marca."
          breadcrumbs={["Descobrir", "Oportunidade", "Nova campanha"]}
        />
        <div className="grid gap-4 xl:grid-cols-[1fr_340px]">
          <Panel title="Revisão de contexto" eyebrow="Sem formulário vazio">
            <div className="space-y-4 p-5">
              <label className="block text-xs font-semibold text-white/60">
                Nome da campanha
                <input
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  className="mt-2 w-full rounded-xl border border-white/[0.08] bg-black/25 px-3 py-3 text-sm text-white outline-none focus:border-[var(--clicko-action)]/60"
                />
              </label>
              <label className="block text-xs font-semibold text-white/60">
                Objetivo
                <textarea
                  value={objective}
                  onChange={(event) => setObjective(event.target.value)}
                  rows={4}
                  className="mt-2 w-full resize-none rounded-xl border border-white/[0.08] bg-black/25 px-3 py-3 text-sm leading-6 text-white outline-none focus:border-[var(--clicko-action)]/60"
                />
              </label>
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-xl border border-white/[0.06] p-3 text-xs text-white/45">
                  <strong className="mb-1 block text-white">Público</strong>
                  {operations.activeClient?.audience}
                </div>
                <div className="rounded-xl border border-white/[0.06] p-3 text-xs text-white/45">
                  <strong className="mb-1 block text-white">Oferta</strong>
                  {operations.activeClient?.featuredOffer}
                </div>
              </div>
              <button type="button" onClick={create} className={ACTION_CLASS}>
                {created ? (
                  <Check className="h-4 w-4" />
                ) : (
                  <Sparkles className="h-4 w-4" />
                )}
                {created
                  ? "Campanha criada"
                  : "Criar campanha com este contexto"}
              </button>
            </div>
          </Panel>
          <Panel title="Origem preservada" eyebrow="Lineage">
            <div className="p-5">
              {[
                opportunity?.title || "Briefing manual",
                `Memória v${operations.brain.revision}`,
                operations.activeClient?.name || "Workspace",
              ].map((item, index) => (
                <div key={item} className="relative flex gap-3 pb-5 last:pb-0">
                  <span className="z-10 grid h-7 w-7 shrink-0 place-items-center rounded-full border border-[var(--clicko-action)]/30 bg-[var(--clicko-action)]/10 text-[10px] font-bold text-[var(--clicko-action)]">
                    {index + 1}
                  </span>
                  {index < 2 && (
                    <span className="absolute bottom-0 left-3.5 top-7 w-px bg-white/10" />
                  )}
                  <div className="pt-1 text-xs font-semibold text-white/65">
                    {item}
                  </div>
                </div>
              ))}
            </div>
          </Panel>
        </div>
      </>
    );
  }

  const campaignPosts = posts.filter(
    (post) => !campaign || post.campaignId === campaign.id,
  );
  const tabs = [
    {
      key: "overview",
      label: "Visão geral",
      path: `/campaigns/${campaign?.id || "active"}`,
    },
    {
      key: "world",
      label: "Mundo",
      path: `/campaigns/${campaign?.id || "active"}/world`,
    },
    {
      key: "moodboard",
      label: "Moodboard",
      path: `/campaigns/${campaign?.id || "active"}/moodboard`,
    },
    {
      key: "studio",
      label: "Studio",
      path: `/campaigns/${campaign?.id || "active"}/studio`,
    },
    {
      key: "creative",
      label: "Creative Lab",
      path: `/projects/${campaign?.id || "active"}/creative`,
    },
    {
      key: "content",
      label: "Conteúdos",
      path: `/content?campaign=${campaign?.id || "active"}`,
    },
    {
      key: "approvals",
      label: "Aprovações",
      path: `/approvals/${campaignPosts[0]?.id || "post-1"}`,
    },
    { key: "calendar", label: "Calendário", path: "/calendar" },
    { key: "results", label: "Resultados", path: "/analytics/learning" },
  ];
  return (
    <>
      <SurfaceHeader
        eyebrow="Campaign Room"
        title={campaign?.name || "Campanha ativa"}
        description={
          campaign?.objective ||
          "Sala contextual da campanha, com narrativa, peças, decisões e resultados no mesmo lugar."
        }
        action="Criar peça"
        onAction={() =>
          onNavigate(`/campaigns/${campaign?.id || "active"}/studio`)
        }
        breadcrumbs={["Campanhas", campaign?.status || "Ativa"]}
      />
      <div className="mb-5 flex gap-1 overflow-x-auto border-b border-white/[0.08]">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => onNavigate(tab.path)}
            className={`border-b-2 px-4 py-3 text-xs font-semibold ${segment === tab.key || (segment === "overview" && tab.key === "overview") ? "border-[var(--clicko-action)] text-white" : "border-transparent text-white/40 hover:text-white"}`}
          >
            {tab.label}
          </button>
        ))}
      </div>
      {segment === "world" && (
        <CampaignWorld campaignName={campaign?.name || "Campanha"} />
      )}
      {segment === "moodboard" && (
        <Moodboard
          assets={
            (productData.status === "ready"
              ? productData.snapshot?.assets
              : operations.assets
            )?.map((asset) => asset.title) || []
          }
          onAdd={async () => {
            const title = `Referência ${(productData.snapshot?.assets.length || operations.assets.length) + 1}`;
            if (productData.status === "ready" && productData.snapshot) {
              await productApi.createAsset({
                workspaceId: productData.snapshot.workspaceId,
                title,
                type: "image",
                tags: ["moodboard", "campanha"],
                campaignId: campaign?.id || null,
                contentId: null,
                url: null,
              });
              await productData.refresh();
            } else {
              operations.addAsset({
                title,
                type: "image",
                tags: ["moodboard", "campanha"],
                campaignId: campaign?.id,
              });
            }
          }}
        />
      )}
      {segment === "studio" && (
        <CampaignStudio
          onNavigate={onNavigate}
          campaignId={campaign?.id || "active"}
        />
      )}
      {segment === "overview" && (
        <div className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <Stat
              label="Peças"
              value={campaignPosts.length}
              detail="ligadas à campanha"
              icon={Grid2X2}
            />
            <Stat
              label="Aprovação"
              value={
                campaignPosts.filter((post) => post.status === "approved")
                  .length
              }
              detail="prontas para publicar"
              icon={BadgeCheck}
            />
            <Stat
              label="Memória"
              value={`v${campaign?.brainRevision || operations.brain.revision}`}
              detail="revisão usada no brief"
              icon={BookOpen}
            />
            <Stat
              label="Status"
              value={campaign?.status || "Ativa"}
              detail={
                params.get("nav") === "context"
                  ? "navegação contextual"
                  : "operação em curso"
              }
              icon={Activity}
            />
          </div>
          <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
            <Panel title="Plano de execução" eyebrow="Da estratégia à peça">
              <div className="grid gap-3 p-5 md:grid-cols-2">
                {(campaign?.executionPlan || []).map((step, index) => (
                  <button
                    key={step}
                    type="button"
                    onClick={() =>
                      onNavigate(`/campaigns/${campaign?.id}/studio`)
                    }
                    className="flex items-start gap-3 rounded-xl border border-white/[0.07] bg-black/20 p-4 text-left hover:border-[var(--clicko-action)]/30"
                  >
                    <span className="font-mono text-[10px] text-[var(--clicko-action)]">
                      0{index + 1}
                    </span>
                    <span className="text-xs font-semibold leading-5 text-white/70">
                      {step}
                    </span>
                  </button>
                ))}
              </div>
            </Panel>
            <Panel title="Decisões recentes" eyebrow="Auditável">
              <div className="divide-y divide-white/[0.06]">
                {[
                  "Narrativa central aprovada",
                  "Canal LinkedIn priorizado",
                  "CTA em revisão",
                ].map((item, index) => (
                  <div key={item} className="flex items-center gap-3 p-4">
                    <span
                      className={`h-2 w-2 rounded-full ${index === 2 ? "bg-[var(--clicko-creative)]" : "bg-[var(--clicko-action)]"}`}
                    />
                    <div className="flex-1">
                      <div className="text-xs font-semibold text-white/70">
                        {item}
                      </div>
                      <div className="mt-1 text-[10px] text-white/30">
                        {index + 1}h · Pedro Henrique
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </Panel>
          </div>
        </div>
      )}
    </>
  );
}

function CampaignWorld({ campaignName }: { campaignName: string }) {
  const pillars = [
    "Precisão operacional",
    "Inteligência com contexto",
    "Criação que aprende",
  ];
  return (
    <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
      <Panel title="Mundo da campanha" eyebrow="Narrativa">
        <div className="p-5">
          <div className="rounded-2xl border border-[var(--clicko-creative)]/20 bg-gradient-to-br from-[var(--clicko-creative)]/15 via-transparent to-[var(--clicko-action)]/10 p-6">
            <div className="text-[10px] uppercase tracking-[0.2em] text-white/35">
              Ideia-mãe
            </div>
            <h2 className="mt-3 text-2xl font-semibold tracking-tight text-white">
              {campaignName}
            </h2>
            <p className="mt-3 text-sm leading-6 text-white/50">
              O trabalho invisível da operação se torna uma vantagem visível da
              marca.
            </p>
          </div>
        </div>
      </Panel>
      <Panel title="Pilares de coerência" eyebrow="Guardrails">
        <div className="grid gap-3 p-5 sm:grid-cols-3">
          {pillars.map((pillar, index) => (
            <article
              key={pillar}
              className="rounded-xl border border-white/[0.07] bg-black/20 p-4"
            >
              <span className="font-mono text-[10px] text-[var(--clicko-creative)]">
                P{index + 1}
              </span>
              <h3 className="mt-6 text-sm font-semibold text-white">
                {pillar}
              </h3>
              <p className="mt-2 text-xs leading-5 text-white/40">
                Critério ativo para texto, imagem, movimento e aprovação.
              </p>
            </article>
          ))}
        </div>
      </Panel>
    </div>
  );
}

function Moodboard({
  assets,
  onAdd,
}: {
  assets: string[];
  onAdd: () => Promise<void>;
}) {
  const [adding, setAdding] = React.useState(false);
  const cards = [
    ...assets,
    "Contraste editorial",
    "Produto em contexto",
    "Textura mineral",
    "Tipografia precisa",
  ].slice(0, 6);
  return (
    <Panel
      title="Campaign Moodboard"
      eyebrow="Direção visual"
      action={
        <button
          type="button"
          onClick={() => {
            setAdding(true);
            void onAdd().finally(() => setAdding(false));
          }}
          disabled={adding}
          className={BUTTON_CLASS}
        >
          <Upload className="h-3.5 w-3.5" />
          {adding ? "Adicionando…" : "Adicionar referência"}
        </button>
      }
    >
      <div className="grid auto-rows-[170px] gap-3 p-5 sm:grid-cols-2 lg:grid-cols-3">
        {cards.map((card, index) => (
          <article
            key={`${card}-${index}`}
            className={`group relative overflow-hidden rounded-2xl border border-white/[0.08] bg-gradient-to-br ${index % 3 === 0 ? "from-[var(--clicko-creative)]/20 to-black" : index % 3 === 1 ? "from-white/10 to-black" : "from-[var(--clicko-action)]/15 to-black"} ${index === 0 ? "sm:row-span-2" : ""}`}
          >
            <div className="absolute inset-0 opacity-50 [background-image:radial-gradient(circle_at_70%_20%,rgba(255,255,255,.18),transparent_35%)]" />
            <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black p-4 pt-10">
              <div className="text-xs font-semibold text-white">{card}</div>
              <div className="mt-1 text-[10px] text-white/40">
                Referência aprovada · marca
              </div>
            </div>
          </article>
        ))}
      </div>
    </Panel>
  );
}

function CampaignStudio({
  onNavigate,
  campaignId,
}: {
  onNavigate: Navigate;
  campaignId: string;
}) {
  const formats: Array<{ label: string; type: string; icon: IconType }> = [
    { label: "Post editorial", type: "editorial", icon: FileText },
    { label: "Carrossel", type: "carousel", icon: Layers3 },
    { label: "Visual estático", type: "visual", icon: Image },
    { label: "Vídeo curto", type: "video", icon: MonitorPlay },
  ];
  return (
    <div className="grid gap-4 xl:grid-cols-[1fr_320px]">
      <Panel title="Kit multiformato" eyebrow="Studio Composer">
        <div className="grid gap-3 p-5 sm:grid-cols-2">
          {formats.map(({ label, type, icon: Icon }) => (
            <button
              key={type}
              type="button"
              onClick={() =>
                onNavigate(
                  `/content/draft/edit?mode=${type}&campaign=${campaignId}`,
                )
              }
              className="group rounded-2xl border border-white/[0.08] bg-black/20 p-5 text-left transition hover:border-[var(--clicko-action)]/35"
            >
              <Icon className="h-5 w-5 text-[var(--clicko-creative)]" />
              <h3 className="mt-8 text-base font-semibold text-white">
                {label}
              </h3>
              <p className="mt-1 text-xs text-white/40">
                Brief, marca e campanha já conectados.
              </p>
              <ArrowRight className="mt-4 h-4 w-4 text-white/30 transition group-hover:translate-x-1 group-hover:text-white" />
            </button>
          ))}
        </div>
      </Panel>
      <Panel title="Contexto aplicado" eyebrow="Handoff">
        <div className="space-y-3 p-5">
          {[
            "Memória da marca ativa",
            "Mundo da campanha",
            "Safe areas por canal",
            "Objetivo e CTA",
          ].map((item) => (
            <div
              key={item}
              className="flex items-center gap-3 text-xs text-white/60"
            >
              <Check className="h-4 w-4 text-[var(--clicko-action)]" />
              {item}
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}

function ContentSurface({
  pathname,
  search,
  onNavigate,
}: ProductSurfaceViewProps) {
  const operations = useOperations();
  const server = useServerState();
  const productData = useProductData();
  const posts =
    productData.status === "ready" && productData.snapshot
      ? (productData.snapshot.posts as unknown as Post[])
      : server.status === "connected"
        ? server.bootstrap?.posts || []
        : operations.posts;
  const params = new URLSearchParams(search);
  const view =
    params.get("view") ||
    (pathname === "/content/dashboard" ? "dashboard" : "board");
  const contentId = idFromPath(pathname, "content", posts[0]?.id || "post-1");
  const post = posts.find((item) => item.id === contentId) || posts[0];
  if (pathname.endsWith("/edit"))
    return (
      <EditorSurface
        pathname={pathname}
        search={search}
        onNavigate={onNavigate}
      />
    );
  if (pathname.endsWith("/remix"))
    return (
      <RemixSurface
        post={post}
        visual={params.get("lab") === "visual"}
        onNavigate={onNavigate}
      />
    );
  if (pathname.endsWith("/variations"))
    return <VariationSurface post={post} onNavigate={onNavigate} />;
  if (pathname === "/content/new")
    return <CreateHub type={params.get("type")} onNavigate={onNavigate} />;
  if (pathname === "/content" || pathname === "/content/dashboard")
    return <ContentBoard posts={posts} view={view} onNavigate={onNavigate} />;
  return <ContentDetail post={post} onNavigate={onNavigate} />;
}

function ContentBoard({
  posts,
  view,
  onNavigate,
}: {
  posts: Post[];
  view: string;
  onNavigate: Navigate;
}) {
  const inventory = view === "inventory";
  return (
    <>
      <SurfaceHeader
        eyebrow="Content Command"
        title={
          view === "dashboard"
            ? "Saúde da produção"
            : inventory
              ? "Inventário de conteúdo"
              : "Board visual de conteúdo"
        }
        description="Uma única fonte para criação, fila, campanha, aprovação e desempenho."
        action="Novo conteúdo"
        onAction={() => onNavigate("/content/new")}
        breadcrumbs={["Conteúdo", inventory ? "Inventário" : "Board"]}
      />
      <div className="mb-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Stat
          label="No fluxo"
          value={posts.length}
          detail="todos os formatos"
          icon={Workflow}
        />
        <Stat
          label="Em produção"
          value={
            posts.filter((post) => ["draft", "in_review"].includes(post.status))
              .length
          }
          detail="precisam de ação"
          icon={Clock3}
        />
        <Stat
          label="Aprovados"
          value={posts.filter((post) => post.status === "approved").length}
          detail="prontos para publicar"
          icon={BadgeCheck}
        />
        <Stat
          label="Publicados"
          value={posts.filter((post) => post.status === "published").length}
          detail="com histórico"
          icon={Send}
        />
      </div>
      <Panel
        title={inventory ? "Todos os conteúdos" : "Produção visual"}
        eyebrow="Workspace"
        action={
          <div className="flex gap-1">
            <button
              onClick={() => onNavigate("/content")}
              className={BUTTON_CLASS}
            >
              <Grid2X2 className="h-3.5 w-3.5" />
            </button>
            <button
              onClick={() => onNavigate("/content?view=inventory")}
              className={BUTTON_CLASS}
            >
              <List className="h-3.5 w-3.5" />
            </button>
          </div>
        }
      >
        <div
          className={
            inventory
              ? "divide-y divide-white/[0.06]"
              : "grid gap-3 p-5 sm:grid-cols-2 xl:grid-cols-3"
          }
        >
          {posts.map((post, index) =>
            inventory ? (
              <button
                key={post.id}
                onClick={() => onNavigate(`/content/${post.id}`)}
                className="grid w-full grid-cols-[1fr_auto_auto] items-center gap-4 p-4 text-left hover:bg-white/[0.025]"
              >
                <div>
                  <div className="text-xs font-semibold text-white">
                    {post.title}
                  </div>
                  <div className="mt-1 text-[10px] text-white/35">
                    {post.format} · {post.platform}
                  </div>
                </div>
                <StatusPill
                  tone={
                    post.status === "approved" || post.status === "published"
                      ? "good"
                      : "neutral"
                  }
                >
                  {post.status}
                </StatusPill>
                <MoreHorizontal className="h-4 w-4 text-white/30" />
              </button>
            ) : (
              <button
                key={post.id}
                onClick={() => onNavigate(`/content/${post.id}`)}
                className="group overflow-hidden rounded-2xl border border-white/[0.08] bg-black/25 text-left hover:border-white/20"
              >
                <div className={`relative h-44 overflow-hidden bg-gradient-to-br ${index % 3 === 0 ? "from-[var(--clicko-creative)]/20" : index % 3 === 1 ? "from-[var(--clicko-action)]/15" : "from-white/10"} to-black`}>
                  {post.imageUrl ? (
                    <img src={post.imageUrl} alt="" className="h-full w-full object-cover transition duration-500 group-hover:scale-105" />
                  ) : (
                    <div className="absolute inset-0 grid place-items-center"><span className="text-4xl font-semibold tracking-[-0.08em] text-white/20">{String(index + 1).padStart(2, "0")}</span></div>
                  )}
                  <div className="absolute inset-0 bg-gradient-to-t from-black/55 via-transparent to-black/10" />
                  <StatusPill
                    tone={post.status === "approved" ? "good" : "neutral"}
                  >
                    <span className="absolute left-3 top-3">{post.status}</span>
                  </StatusPill>
                </div>
                <div className="p-4">
                  <h3 className="truncate text-sm font-semibold text-white">
                    {post.title}
                  </h3>
                  <p className="mt-1 text-[10px] text-white/35">
                    {post.format} · {post.platform}
                  </p>
                </div>
              </button>
            ),
          )}
        </div>
      </Panel>
    </>
  );
}

function CreateHub({
  type,
  onNavigate,
}: {
  type: string | null;
  onNavigate: Navigate;
}) {
  const choices: Array<{
    title: string;
    detail: string;
    mode: string;
    icon: IconType;
  }> = [
    {
      title: "Post editorial",
      detail: "Copy, referências e preview",
      mode: "editorial",
      icon: FileText,
    },
    {
      title: "Carrossel",
      detail: "Narrativa em slides",
      mode: "carousel",
      icon: Layers3,
    },
    {
      title: "Visual",
      detail: "Canvas profissional",
      mode: "visual",
      icon: Image,
    },
    {
      title: "Vídeo",
      detail: "Timeline, captions e motion",
      mode: "video",
      icon: MonitorPlay,
    },
  ];
  return (
    <>
      <SurfaceHeader
        eyebrow="Etapa Criar"
        title={
          type === "post" ? "Novo post com contexto" : "O que vamos criar?"
        }
        description="Comece pela intenção. O Clicko leva campanha, memória da marca e referências para o editor escolhido."
        breadcrumbs={["Operação", "Criar"]}
      />
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {choices.map(({ title, detail, mode, icon: Icon }) => (
          <button
            key={mode}
            type="button"
            onClick={() =>
              onNavigate(
                `/content/draft/edit?mode=${mode}${type ? "&type=post" : ""}`,
              )
            }
            className="group min-h-56 rounded-2xl border border-white/[0.08] bg-white/[0.025] p-5 text-left transition hover:-translate-y-1 hover:border-[var(--clicko-action)]/35"
          >
            <div className="grid h-10 w-10 place-items-center rounded-xl border border-[var(--clicko-creative)]/25 bg-[var(--clicko-creative)]/10">
              <Icon className="h-5 w-5 text-[var(--clicko-creative)]" />
            </div>
            <h2 className="mt-12 text-lg font-semibold text-white">{title}</h2>
            <p className="mt-2 text-xs text-white/40">{detail}</p>
            <div className="mt-6 flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.14em] text-white/35 group-hover:text-[var(--clicko-action)]">
              Abrir workspace
              <ArrowRight className="h-3.5 w-3.5" />
            </div>
          </button>
        ))}
      </div>
    </>
  );
}

function ContentDetail({
  post,
  onNavigate,
}: {
  post?: Post;
  onNavigate: Navigate;
}) {
  if (!post) return <EmptyState title="Nenhum conteúdo neste workspace" />;
  return (
    <>
      <SurfaceHeader
        eyebrow="Post Detail"
        title={post.title}
        description="Documento, versões, comentários, métricas e origem reunidos em uma tela auditável."
        action="Abrir no editor"
        onAction={() =>
          onNavigate(
            `/content/${post.id}/edit?mode=${post.format === "carousel" ? "carousel" : "editorial"}`,
          )
        }
        breadcrumbs={["Conteúdo", post.format, post.status]}
      />
      <div className="grid gap-4 xl:grid-cols-[1fr_360px]">
        <Panel title="Preview e conteúdo" eyebrow="Versão atual">
          <div className="grid gap-5 p-5 md:grid-cols-[260px_1fr]">
            <div className="relative aspect-[4/5] overflow-hidden rounded-2xl border border-white/[0.08] bg-gradient-to-br from-[var(--clicko-creative)]/20 via-black to-[var(--clicko-action)]/10 p-5">
              {post.imageUrl && <img src={post.imageUrl} alt="" className="absolute inset-0 h-full w-full object-cover opacity-65" />}
              <div className="absolute inset-0 bg-gradient-to-t from-black via-black/10 to-transparent" />
              <div className="flex h-full flex-col justify-between">
                <div className="relative"><StatusPill>{post.platform}</StatusPill></div>
                <div className="relative">
                  <div className="text-3xl font-semibold tracking-[-0.07em] text-white/75">
                    {post.title}
                  </div>
                  <div className="mt-2 h-1 w-16 bg-[var(--clicko-action)]" />
                </div>
              </div>
            </div>
            <div>
              <div className="flex flex-wrap gap-2">
                <StatusPill tone="good">{post.status}</StatusPill>
                <StatusPill>{post.format}</StatusPill>
              </div>
              <p className="mt-5 whitespace-pre-wrap text-sm leading-6 text-white/60">
                {post.copy || "Conteúdo ainda sem copy registrada."}
              </p>
              <div className="mt-6 flex flex-wrap gap-2">
                <button
                  onClick={() => onNavigate(`/content/${post.id}/remix`)}
                  className={BUTTON_CLASS}
                >
                  <Copy className="h-3.5 w-3.5" />
                  Reutilizar
                </button>
                <button
                  onClick={() => onNavigate(`/content/${post.id}/variations`)}
                  className={BUTTON_CLASS}
                >
                  <Grid2X2 className="h-3.5 w-3.5" />
                  Variações
                </button>
                <button
                  onClick={() => onNavigate(`/approvals/${post.id}`)}
                  className={ACTION_CLASS}
                >
                  <BadgeCheck className="h-3.5 w-3.5" />
                  Revisar
                </button>
              </div>
            </div>
          </div>
        </Panel>
        <div className="space-y-4">
          <Panel title="Lineage" eyebrow="Origem">
            <div className="space-y-3 p-5">
              {[
                `Memória v${post.brainRevision || 1}`,
                post.campaignId ? "Campanha conectada" : "Criação manual",
                `Versão ${post.versions?.length || 1}`,
              ].map((item, index) => (
                <div key={item} className="flex items-center gap-3">
                  <span className="grid h-7 w-7 place-items-center rounded-full border border-white/10 text-[10px] text-white/45">
                    {index + 1}
                  </span>
                  <span className="text-xs text-white/55">{item}</span>
                </div>
              ))}
            </div>
          </Panel>
          <Panel title="Desempenho" eyebrow="Dados reais">
            <div className="p-5">
              <div className="rounded-xl border border-dashed border-white/10 p-4 text-xs leading-5 text-white/40">
                Nenhuma métrica sincronizada para esta peça. Conecte o canal ou
                registre um snapshot — o Clicko não inventa dados.
              </div>
            </div>
          </Panel>
        </div>
      </div>
    </>
  );
}

function RemixSurface({
  post,
  visual,
  onNavigate,
}: {
  post?: Post;
  visual: boolean;
  onNavigate: Navigate;
}) {
  const operations = useOperations();
  const formats: PostFormat[] = [
    "carousel",
    "reels",
    "linkedin-article",
    "story",
  ];
  const [selected, setSelected] = React.useState<PostFormat>("carousel");
  const start = () => {
    if (post) operations.createRepurposeHandoff(post, selected);
    onNavigate(
      `/content/draft/edit?mode=${selected === "reels" ? "video" : selected === "carousel" ? "carousel" : "editorial"}&remix=${post?.id || ""}`,
    );
  };
  return (
    <>
      <SurfaceHeader
        eyebrow={visual ? "Visual Remix Lab" : "Reuse Workshop"}
        title={`Reutilizar ${post?.title || "conteúdo"}`}
        description="Preserve a mensagem central, escolha um novo formato e registre a hipótese da derivação."
        breadcrumbs={["Conteúdo", "Lineage", "Reutilizar"]}
      />
      <div className="grid gap-4 xl:grid-cols-[0.8fr_1.2fr]">
        <Panel title="Original" eyebrow="Fonte preservada">
          <div className="p-5">
            <div className="overflow-hidden rounded-2xl border border-white/[0.08] bg-black/25">
              {post?.imageUrl && <div className="aspect-video"><img src={post.imageUrl} alt="" className="h-full w-full object-cover" /></div>}
              <div className="p-5">
              <StatusPill>{post?.format || "post"}</StatusPill>
              <h2 className="mt-5 text-lg font-semibold text-white">
                {post?.title}
              </h2>
              <p className="mt-3 line-clamp-5 text-xs leading-5 text-white/45">
                {post?.copy}
              </p>
              </div>
            </div>
          </div>
        </Panel>
        <Panel title="Novo desdobramento" eyebrow="Escolha intencional">
          <div className="grid gap-3 p-5 sm:grid-cols-2">
            {formats.map((format) => (
              <button
                key={format}
                type="button"
                onClick={() => setSelected(format)}
                className={`rounded-xl border p-4 text-left ${selected === format ? "border-[var(--clicko-action)]/50 bg-[var(--clicko-action)]/10" : "border-white/[0.07] bg-black/20"}`}
              >
                <div className="text-sm font-semibold text-white">{format}</div>
                <div className="mt-1 text-[10px] text-white/35">
                  Safe areas e narrativa próprias
                </div>
              </button>
            ))}
          </div>
          <div className="flex items-center justify-between border-t border-white/[0.06] p-5">
            <div className="text-xs text-white/40">
              Hipótese: ampliar alcance sem perder a tese original.
            </div>
            <button type="button" onClick={start} className={ACTION_CLASS}>
              Aceitar handoff
              <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        </Panel>
      </div>
    </>
  );
}

function VariationSurface({
  post,
  onNavigate,
}: {
  post?: Post;
  onNavigate: Navigate;
}) {
  const formats = [
    { label: "Quadrado", ratio: "1:1", risk: "Baixo" },
    { label: "Retrato", ratio: "4:5", risk: "Baixo" },
    { label: "Stories", ratio: "9:16", risk: "Atenção" },
    { label: "LinkedIn", ratio: "1.91:1", risk: "Médio" },
  ];
  return (
    <>
      <SurfaceHeader
        eyebrow="Format & Variation Board"
        title={post?.title || "Variações do conteúdo"}
        description="Compare formatos, safe areas e risco de adaptação antes de gerar uma derivação."
        action="Editar origem"
        onAction={() =>
          onNavigate(`/content/${post?.id || "draft"}/edit?mode=visual`)
        }
        breadcrumbs={["Conteúdo", "Variações"]}
      />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {formats.map((format, index) => (
          <article key={format.label} className={`${SURFACE_CLASS} p-4`}>
            <div className={`relative mx-auto grid overflow-hidden bg-gradient-to-br from-[var(--clicko-creative)]/25 to-black p-4 ${index === 2 ? "aspect-[9/16] max-h-64" : index === 1 ? "aspect-[4/5]" : index === 3 ? "aspect-[1.91/1]" : "aspect-square"}`}>
              {post?.imageUrl && <img src={post.imageUrl} alt="" className="absolute inset-0 h-full w-full object-cover" />}
              <span className="relative self-end text-xl font-semibold tracking-tight text-white drop-shadow-lg">
                {format.ratio}
              </span>
            </div>
            <div className="mt-4 flex items-center justify-between">
              <div>
                <div className="text-sm font-semibold text-white">
                  {format.label}
                </div>
                <div className="mt-1 text-[10px] text-white/35">
                  Smart resize disponível
                </div>
              </div>
              <StatusPill tone={format.risk === "Baixo" ? "good" : "warn"}>
                {format.risk}
              </StatusPill>
            </div>
          </article>
        ))}
      </div>
    </>
  );
}

function EditorSurface({
  pathname,
  search,
  onNavigate,
}: ProductSurfaceViewProps) {
  const params = new URLSearchParams(search);
  const mode = params.get("mode") || "visual";
  const panel =
    params.get("panel") ||
    (mode === "video" ? "motion" : mode === "editorial" ? "copy" : "layers");
  const focus = params.get("focus") === "1";
  const operations = useOperations();
  const productData = useProductData();
  const campaignId =
    params.get("campaign") || operations.activeCampaign?.id || undefined;
  const remoteCreative = productData.snapshot?.creatives.find(
    (creative) =>
      creative.campaignId === campaignId && creative.kind === "document",
  );
  const localCreative = React.useMemo<CreativeRecord>(() => {
    const now = new Date().toISOString();
    const localId = `local-${campaignId || "draft"}-${mode}`;
    const persistedHeadline = localStorage.getItem(
      `clicko:creative:${localId}:headline`,
    );
    const document: CreativeCanvas = {
      schemaVersion: "creative-v1",
      width: 1080,
      height: mode === "video" ? 1920 : mode === "carousel" ? 1080 : 1350,
      safeArea: 72,
      background: "#0f0f0f",
      brandTokens: {
        action: "#ff5c5c",
        creative: "#ff7a00",
        font: "Inter Variable",
      },
      layers: [
        {
          id: "headline",
          name: "Headline",
          type: "text",
          x: 96,
          y: 840,
          width: 888,
          height: 280,
          rotation: 0,
          opacity: 1,
          visible: true,
          locked: false,
          zIndex: 10,
          text: persistedHeadline || "Transforme contexto em criação",
          fontSize: 72,
          minFontSize: 28,
          fontFamily: "Inter Variable",
          fontWeight: "bold",
          color: "#ffffff",
          align: "left",
          lineHeight: 1.05,
        },
      ],
    };
    return {
      id: localId,
      workspaceId: operations.activeWorkspace.id,
      campaignId: campaignId || null,
      postId: null,
      kind: "document",
      title: `Criação ${mode}`,
      document,
      version: 1,
      versions: [],
      createdAt: now,
      updatedAt: now,
    };
  }, [campaignId, mode, operations.activeWorkspace.id]);
  const activeCreative = remoteCreative || localCreative;
  const autosave = useCreativeAutosave(activeCreative, {
    enabled: productData.status === "ready" && Boolean(remoteCreative),
  });
  const creatingRef = React.useRef<string>();
  const [selectedLayer, setSelectedLayer] = React.useState("Headline");
  const initialHeadline = activeCreative.document.layers?.find(
    (layer) => layer.type === "text" && layer.id === "headline",
  );
  const [headline, setHeadline] = React.useState(
    initialHeadline?.type === "text"
      ? initialHeadline.text
      : "Transforme contexto em criação",
  );
  const [exportState, setExportState] = React.useState<
    "idle" | "exporting" | "ready" | "error"
  >("idle");
  const [reviewState, setReviewState] = React.useState<
    "idle" | "sending" | "error"
  >("idle");
  const [previewOpen, setPreviewOpen] = React.useState(false);
  const [handoffAccepted, setHandoffAccepted] = React.useState(false);

  React.useEffect(() => {
    const layer = activeCreative.document.layers?.find(
      (item) => item.type === "text" && item.id === "headline",
    );
    if (layer?.type === "text") setHeadline(layer.text);
  }, [activeCreative.id, activeCreative.document.layers]);

  React.useEffect(() => {
    if (
      productData.status !== "ready" ||
      remoteCreative ||
      !productData.activeWorkspace ||
      creatingRef.current === localCreative.id
    )
      return;
    creatingRef.current = localCreative.id;
    void productData
      .createCreative({
        campaignId: campaignId || null,
        postId: null,
        kind: "document",
        title: localCreative.title,
        document: localCreative.document,
      })
      .catch(() => {
        creatingRef.current = undefined;
      });
  }, [campaignId, localCreative, productData, remoteCreative]);

  const updateHeadline = (value: string) => {
    setHeadline(value);
    autosave.setDocument((document) => ({
      ...document,
      layers: (document.layers || []).map((layer) =>
        layer.type === "text" && layer.id === "headline"
          ? { ...layer, text: value }
          : layer,
      ),
    }));
    if (productData.status !== "ready")
      localStorage.setItem(
        `clicko:creative:${localCreative.id}:headline`,
        value,
      );
  };
  const save = () => {
    void autosave.saveNow().catch(() => undefined);
  };
  const exportCreative = async () => {
    if (!remoteCreative) {
      setExportState("ready");
      return;
    }
    setExportState("exporting");
    try {
      await productApi.exportCreative(remoteCreative.id, "png");
      setExportState("ready");
    } catch {
      setExportState("error");
    }
  };
  const sendToReview = async () => {
    setReviewState("sending");
    const format: PostFormat =
      mode === "video" ? "reels" : mode === "carousel" ? "carousel" : "post";
    try {
      if (productData.status === "ready") {
        const postId = await productData.createPost({
          title: headline || "Conteúdo sem título",
          platform: "instagram",
          format,
          copy: headline,
          hashtags: [],
          scheduledAt: null,
          status: "in_review",
          author: productData.bootstrap?.user.name || "Usuário",
          aiScore: null,
          campaignId: campaignId || null,
          strategyId: campaignId || null,
          brainRevision: operations.brain.revision,
          objective: operations.activeCampaign?.objective || null,
          origin: campaignId ? "strategy" : "manual",
        });
        if (remoteCreative)
          await productData.updateCreative(remoteCreative.id, { postId });
        onNavigate(`/approvals/${postId}`);
        return;
      }
      const postId = `post-${Date.now()}`;
      operations.addPosts([
        {
          id: postId,
          workspaceId: operations.activeWorkspace.id,
          title: headline || "Conteúdo sem título",
          platform: "instagram",
          format,
          copy: headline,
          hashtags: [],
          scheduledAt: new Date().toISOString(),
          status: "in_review",
          author: "Modo local",
          createdAt: new Date().toISOString(),
          campaignId,
          strategyId: campaignId,
          brainRevision: operations.brain.revision,
          objective: operations.activeCampaign?.objective,
          origin: campaignId ? "strategy" : "manual",
        },
      ]);
      onNavigate(`/approvals/${postId}`);
    } catch {
      setReviewState("error");
    }
  };
  const saveLabel =
    productData.status !== "ready"
      ? "Salvo neste navegador"
      : !remoteCreative
        ? "Preparando documento"
        : autosave.status === "saving"
          ? "Salvando…"
          : autosave.status === "conflict"
            ? "Conflito de versão"
            : autosave.status === "error"
              ? "Falha ao salvar"
              : autosave.status === "dirty"
                ? "Alterações pendentes"
                : "Sincronizado";
  const panels =
    mode === "video"
      ? ["layers", "motion", "captions", "effects"]
      : mode === "editorial"
        ? ["copy", "references", "preview"]
        : ["layers", "typography", "elements", "effects"];
  const goPanel = (nextPanel: string) =>
    onNavigate(
      `${pathname}?mode=${mode}&panel=${nextPanel}${focus ? "&focus=1" : ""}`,
    );
  return (
    <div className={focus ? "-m-5 min-h-[calc(100vh-80px)] bg-black p-4" : ""}>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() =>
              onNavigate(
                campaignId ? `/projects/${campaignId}/creative` : "/content",
              )
            }
            className={BUTTON_CLASS}
          >
            <X className="h-4 w-4" />
            Sair
          </button>
          <div>
            <div className="text-sm font-semibold text-white">
              {mode === "video"
                ? "Motion Studio"
                : mode === "carousel"
                  ? "Carousel Builder"
                  : mode === "editorial"
                    ? "Editorial Creation Desk"
                    : "Visual Editor"}
            </div>
            <div className="mt-0.5 flex items-center gap-1.5 text-[10px] text-white/35">
              <span
                className={`h-1.5 w-1.5 rounded-full ${autosave.status === "error" || autosave.status === "conflict" ? "bg-[var(--clicko-danger)]" : autosave.status === "dirty" || autosave.status === "saving" ? "bg-[var(--clicko-warning)]" : "bg-[var(--clicko-success)]"}`}
              />
              {saveLabel}
            </div>
          </div>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setPreviewOpen(true)}
            className={BUTTON_CLASS}
          >
            <Eye className="h-3.5 w-3.5" />
            Preview
          </button>
          {autosave.status === "conflict" && (
            <button
              onClick={() => void autosave.reload()}
              className={BUTTON_CLASS}
            >
              <RefreshCcw className="h-3.5 w-3.5" />
              Recarregar
            </button>
          )}
          <button onClick={save} className={BUTTON_CLASS}>
            <Save className="h-3.5 w-3.5" />
            Salvar
          </button>
          <button
            onClick={() => void exportCreative()}
            disabled={exportState === "exporting"}
            className={BUTTON_CLASS}
          >
            <Download className="h-3.5 w-3.5" />
            {exportState === "exporting"
              ? "Exportando…"
              : exportState === "ready"
                ? "Exportado"
                : exportState === "error"
                  ? "Tentar exportar"
                  : "Exportar"}
          </button>
          <button
            type="button"
            onClick={() => void sendToReview()}
            disabled={reviewState === "sending"}
            className={ACTION_CLASS}
          >
            <BadgeCheck className="h-3.5 w-3.5" />
            {reviewState === "sending" ? "Enviando…" : "Enviar para revisão"}
          </button>
        </div>
      </div>
      {reviewState === "error" && (
        <div
          role="alert"
          className="mb-3 rounded-xl border border-[var(--clicko-danger)]/30 bg-[var(--clicko-danger)]/10 px-4 py-3 text-xs text-[var(--clicko-danger)]"
        >
          Não foi possível criar o conteúdo para revisão.
        </div>
      )}
      {autosave.error && (
        <div
          role="alert"
          className="mb-3 rounded-xl border border-[var(--clicko-danger)]/30 bg-[var(--clicko-danger)]/10 px-4 py-3 text-xs text-[var(--clicko-danger)]"
        >
          {autosave.error}
        </div>
      )}
      {previewOpen && (
        <div
          className="fixed inset-0 z-[90] grid place-items-center bg-black/80 p-4 backdrop-blur-sm"
          role="dialog"
          aria-modal="true"
          aria-label="Preview da criação"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) setPreviewOpen(false);
          }}
        >
          <div className="w-full max-w-xl rounded-2xl border border-white/10 bg-[var(--clicko-surface-1)] p-4 shadow-2xl">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <div className="text-sm font-semibold text-white">
                  Preview da criação
                </div>
                <div className="mt-1 text-[10px] text-white/35">
                  {mode} · {campaignId || "sem campanha"}
                </div>
              </div>
              <button
                type="button"
                onClick={() => setPreviewOpen(false)}
                className={BUTTON_CLASS}
              >
                <X className="h-4 w-4" />
                Fechar
              </button>
            </div>
            <div className="mx-auto flex aspect-[4/5] max-h-[70vh] flex-col justify-end rounded-xl border border-white/10 bg-gradient-to-br from-[var(--clicko-creative)]/25 via-black to-[var(--clicko-action)]/15 p-[10%]">
              <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-[var(--clicko-creative)]">
                Clicko Precision
              </div>
              <div className="mt-4 text-4xl font-semibold leading-[1.05] tracking-[-0.04em] text-white">
                {headline}
              </div>
            </div>
          </div>
        </div>
      )}
      <div className="grid min-h-[680px] overflow-hidden rounded-2xl border border-white/[0.08] bg-black xl:grid-cols-[220px_1fr_300px]">
        <aside className="border-r border-white/[0.07] bg-white/[0.02] p-3">
          <div className="mb-3 text-[9px] font-bold uppercase tracking-[0.16em] text-white/30">
            Documento
          </div>
          {[
            "Background",
            "Imagem principal",
            "Headline",
            "CTA",
            mode === "video" ? "Audio" : "Logo",
          ].map((layer) => (
            <button
              key={layer}
              type="button"
              onClick={() => setSelectedLayer(layer)}
              className={`mb-1 flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left text-[11px] ${selectedLayer === layer ? "bg-white/[0.08] text-white" : "text-white/40 hover:bg-white/[0.04]"}`}
            >
              <Move className="h-3.5 w-3.5" />
              {layer}
            </button>
          ))}
        </aside>
        <main className="relative grid place-items-center overflow-hidden bg-[radial-gradient(circle_at_center,rgba(255,255,255,.055),transparent_55%)] p-8">
          <div
            className={`relative overflow-hidden border border-white/10 bg-gradient-to-br from-[var(--clicko-creative)]/25 via-black to-[var(--clicko-action)]/15 shadow-2xl shadow-black ${mode === "video" ? "aspect-[9/16] h-[560px]" : mode === "carousel" ? "aspect-square w-[min(560px,80%)]" : "aspect-[4/5] h-[560px]"}`}
          >
            <div className="absolute left-[8%] right-[8%] top-[8%] border border-dashed border-white/15" />
            <div className="absolute inset-0 flex flex-col justify-end p-[10%]">
              <div className="mb-4 text-[10px] font-bold uppercase tracking-[0.2em] text-[var(--clicko-creative)]">
                Clicko Precision
              </div>
              <div
                className={`border border-transparent p-1 text-4xl font-semibold leading-[0.98] tracking-[-0.06em] text-white ${selectedLayer === "Headline" ? "border-[var(--clicko-action)]" : ""}`}
              >
                {headline}
              </div>
              <div className="mt-5 h-1 w-20 bg-[var(--clicko-action)]" />
            </div>
          </div>
          {params.get("handoff") === "1" && !handoffAccepted && (
            <div className="absolute inset-x-8 bottom-6 flex items-center justify-between rounded-xl border border-[var(--clicko-action)]/25 bg-black/85 p-3 text-xs text-white/60 backdrop-blur">
              <span>Handoff visual recebido com contexto e safe areas.</span>
              <button
                type="button"
                onClick={() => setHandoffAccepted(true)}
                className={ACTION_CLASS}
              >
                Aceitar composição
              </button>
            </div>
          )}
        </main>
        <aside className="border-l border-white/[0.07] bg-white/[0.02]">
          <div className="flex gap-1 overflow-x-auto border-b border-white/[0.07] p-2">
            {panels.map((item) => (
              <button
                key={item}
                type="button"
                onClick={() => goPanel(item)}
                className={`rounded-lg px-2.5 py-2 text-[10px] font-semibold capitalize ${panel === item ? "bg-white/[0.08] text-white" : "text-white/35"}`}
              >
                {item}
              </button>
            ))}
          </div>
          <InspectorPanel
            panel={panel}
            headline={headline}
            onHeadline={updateHeadline}
          />
        </aside>
      </div>
    </div>
  );
}

function InspectorPanel({
  panel,
  headline,
  onHeadline,
}: {
  panel: string;
  headline: string;
  onHeadline: (value: string) => void;
}) {
  const [motionEnabled, setMotionEnabled] = React.useState(
    () => new Set(["Entrada suave", "Stagger de palavras"]),
  );
  const [selectedElement, setSelectedElement] = React.useState<string>();
  const icon: Record<string, IconType> = {
    typography: Type,
    elements: Box,
    effects: WandSparkles,
    motion: Play,
    captions: MessageSquare,
    copy: FileText,
    references: Link2,
    preview: Eye,
    layers: Layers3,
  };
  const Icon = icon[panel] || Settings2;
  return (
    <div className="p-4">
      <div className="flex items-center gap-2 text-xs font-semibold capitalize text-white">
        <Icon className="h-4 w-4 text-[var(--clicko-creative)]" />
        {panel}
      </div>
      {panel === "typography" || panel === "copy" ? (
        <div className="mt-5 space-y-4">
          <label className="block text-[10px] font-bold uppercase tracking-[0.14em] text-white/35">
            Texto
            <textarea
              value={headline}
              onChange={(event) => onHeadline(event.target.value)}
              rows={4}
              className="mt-2 w-full resize-none rounded-xl border border-white/[0.08] bg-black/30 p-3 text-xs leading-5 text-white outline-none focus:border-[var(--clicko-action)]/50"
            />
          </label>
          <Control label="Família" value="Inter Variable" />
          <Control label="Peso" value="Semibold 650" />
          <Control label="Entrelinha" value="1.05" />
        </div>
      ) : panel === "motion" ? (
        <div className="mt-5 space-y-3">
          {["Entrada suave", "Stagger de palavras", "Parallax sutil"].map(
            (item, index) => (
              <button
                key={item}
                type="button"
                onClick={() =>
                  setMotionEnabled((current) => {
                    const next = new Set(current);
                    if (next.has(item)) next.delete(item);
                    else next.add(item);
                    return next;
                  })
                }
                aria-pressed={motionEnabled.has(item)}
                className="flex w-full items-center justify-between rounded-xl border border-white/[0.07] p-3 text-xs text-white/55"
              >
                <span>{item}</span>
                <span
                  className={`h-4 w-7 rounded-full p-0.5 ${motionEnabled.has(item) ? "bg-[var(--clicko-action)]" : "bg-white/10"}`}
                >
                  <span
                    className={`block h-3 w-3 rounded-full bg-white ${motionEnabled.has(item) ? "translate-x-3" : ""}`}
                  />
                </span>
              </button>
            ),
          )}
          <p className="text-[10px] leading-4 text-white/30">
            Reduced motion desativa deslocamento e preserva opacidade.
          </p>
        </div>
      ) : (
        <div className="mt-5 grid grid-cols-2 gap-2">
          {["Marca", "Imagem", "Forma", "Gradiente", "Sombra", "Grain"].map(
            (item) => (
              <button
                key={item}
                type="button"
                onClick={() => setSelectedElement(item)}
                aria-pressed={selectedElement === item}
                className={`aspect-square rounded-xl border bg-black/20 text-[10px] font-semibold hover:text-white ${selectedElement === item ? "border-[var(--clicko-action)]/50 text-white" : "border-white/[0.07] text-white/45 hover:border-[var(--clicko-action)]/30"}`}
              >
                {item}
              </button>
            ),
          )}
        </div>
      )}
    </div>
  );
}

function Control({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-[9px] uppercase tracking-[0.14em] text-white/30">
        {label}
      </div>
      <div className="mt-1.5 rounded-lg border border-white/[0.07] bg-black/25 px-3 py-2 text-xs text-white/60">
        {value}
      </div>
    </div>
  );
}

function LibrarySurface({
  pathname,
  onNavigate,
}: {
  pathname: string;
  onNavigate: Navigate;
}) {
  const operations = useOperations();
  const productData = useProductData();
  const [lineageFilter, setLineageFilter] = React.useState<
    "all" | "campaign" | "content"
  >("all");
  const assets =
    productData.status === "ready" && productData.snapshot
      ? productData.snapshot.assets
      : operations.assets;
  if (pathname === "/library/assets")
    return (
      <>
        <SurfaceHeader
          eyebrow="Brand Asset Library"
          title="Elementos aprovados da marca"
          description="DAM conectado aos editores, com metadados, guardrails e origem."
          action="Adicionar asset"
          onAction={() => {
            const title = `Novo asset ${assets.length + 1}`;
            if (productData.status === "ready" && productData.snapshot) {
              void productApi
                .createAsset({
                  workspaceId: productData.snapshot.workspaceId,
                  title,
                  type: "image",
                  tags: ["novo", "marca"],
                  campaignId: null,
                  contentId: null,
                  url: null,
                })
                .then(() => productData.refresh());
            } else
              operations.addAsset({
                title,
                type: "image",
                tags: ["novo", "marca"],
              });
          }}
          breadcrumbs={["Biblioteca", "Assets"]}
        />
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {assets.map((asset, index) => (
            <article
              key={asset.id}
              className={`${SURFACE_CLASS} overflow-hidden`}
            >
              <div
                className={`h-40 bg-gradient-to-br ${index % 2 ? "from-[var(--clicko-action)]/15" : "from-[var(--clicko-creative)]/20"} to-black`}
              />
              <div className="p-4">
                <div className="text-sm font-semibold text-white">
                  {asset.title}
                </div>
                <div className="mt-2 flex flex-wrap gap-1">
                  {(asset.tags || []).map((tag) => (
                    <StatusPill key={tag}>{tag}</StatusPill>
                  ))}
                </div>
              </div>
            </article>
          ))}
        </div>
      </>
    );
  const nodes = [
    ...operations.campaigns.map((item) => ({
      id: item.id,
      label: item.name,
      type: "Campanha",
    })),
    ...operations.posts
      .slice(0, 5)
      .map((item) => ({ id: item.id, label: item.title, type: "Conteúdo" })),
  ].filter(
    (node) =>
      lineageFilter === "all" ||
      (lineageFilter === "campaign"
        ? node.type === "Campanha"
        : node.type === "Conteúdo"),
  );
  return (
    <>
      <SurfaceHeader
        eyebrow="Lineage Library"
        title="A origem de cada criação"
        description="Navegue por campanhas, conteúdos, versões e derivações sem perder o motivo de cada decisão."
        breadcrumbs={["Biblioteca", "Lineage"]}
      />
      <Panel
        title="Grafo de origem"
        eyebrow="Rastreabilidade"
        action={
          <button
            type="button"
            onClick={() =>
              setLineageFilter((value) =>
                value === "all"
                  ? "campaign"
                  : value === "campaign"
                    ? "content"
                    : "all",
              )
            }
            className={BUTTON_CLASS}
          >
            <Filter className="h-3.5 w-3.5" />
            {lineageFilter === "all"
              ? "Todos"
              : lineageFilter === "campaign"
                ? "Campanhas"
                : "Conteúdos"}
          </button>
        }
      >
        <div className="relative min-h-[560px] overflow-hidden p-8 [background-image:radial-gradient(circle,rgba(255,255,255,.09)_1px,transparent_1px)] [background-size:28px_28px]">
          <div className="mx-auto grid max-w-4xl gap-8">
            <button
              onClick={() => onNavigate("/brand-memory")}
              className="mx-auto rounded-2xl border border-[var(--clicko-creative)]/35 bg-[var(--clicko-creative)]/10 px-5 py-4 text-sm font-semibold text-white"
            >
              <BookOpen className="mx-auto mb-2 h-5 w-5 text-[var(--clicko-creative)]" />
              Memória da marca v{operations.brain.revision}
            </button>
            <div className="mx-auto h-8 w-px bg-white/15" />
            <div className="grid gap-4 md:grid-cols-3">
              {nodes.map((node, index) => (
                <button
                  key={node.id}
                  onClick={() =>
                    onNavigate(
                      node.type === "Campanha"
                        ? `/campaigns/${node.id}`
                        : `/content/${node.id}`,
                    )
                  }
                  className="rounded-2xl border border-white/[0.1] bg-black/70 p-4 text-left backdrop-blur"
                >
                  <StatusPill
                    tone={node.type === "Campanha" ? "warn" : "neutral"}
                  >
                    {node.type}
                  </StatusPill>
                  <div className="mt-4 text-xs font-semibold text-white/70">
                    {node.label}
                  </div>
                  <div className="mt-4 flex items-center gap-2 text-[10px] text-white/30">
                    <GitBranch className="h-3.5 w-3.5" />
                    {index + 1} vínculos
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>
      </Panel>
    </>
  );
}

function ApprovalSurface({
  pathname,
  search,
  onNavigate,
}: ProductSurfaceViewProps) {
  const operations = useOperations();
  const server = useServerState();
  const posts =
    server.status === "connected"
      ? server.bootstrap?.posts || []
      : operations.posts;
  const contentId = idFromPath(
    pathname,
    pathname.startsWith("/publish") ? "publish" : "approvals",
    posts[0]?.id || "post-1",
  );
  const post = posts.find((item) => item.id === contentId) || posts[0];
  const publishing = pathname.startsWith("/publish");
  const creative = new URLSearchParams(search).get("view") === "creative";
  const [comment, setComment] = React.useState("");
  const [commentState, setCommentState] = React.useState<
    "idle" | "saving" | "saved" | "error"
  >("idle");
  const setStatus = async (status: Post["status"]) => {
    if (!post) return;
    if (server.status === "connected") {
      const action =
        status === "approved"
          ? "approve"
          : status === "changes_requested"
            ? "request_changes"
            : status === "rejected"
              ? "reject"
              : status === "scheduled"
                ? "schedule"
                : "publish";
      await server.approvalAction(
        post.id,
        action,
        status === "scheduled"
          ? { scheduledAt: new Date(Date.now() + 86400000).toISOString() }
          : undefined,
      );
      return;
    }
    operations.updatePosts((items) =>
      items.map((item) => (item.id === post.id ? { ...item, status } : item)),
    );
  };
  const submitComment = async () => {
    if (!comment.trim()) return;
    setCommentState("saving");
    try {
      if (server.status === "connected") {
        await server.approvalAction(post.id, "comment", {
          comment: comment.trim(),
        });
      } else {
        localStorage.setItem(
          `clicko:approval:${post.id}:comment`,
          comment.trim(),
        );
      }
      setComment("");
      setCommentState("saved");
    } catch {
      setCommentState("error");
    }
  };
  if (!post) return <EmptyState title="Nenhum conteúdo para revisar" />;
  return (
    <>
      <SurfaceHeader
        eyebrow={
          publishing
            ? "Publisher Control"
            : creative
              ? "Creative Review Room"
              : "Approval Room"
        }
        title={post.title}
        description={
          publishing
            ? "Valide canal, permissão, preview e agenda antes de liberar a publicação."
            : "Compare versões, verifique evidências e registre uma decisão com contexto."
        }
        breadcrumbs={[
          publishing ? "Publicação" : "Aprovações",
          post.format,
          post.status,
        ]}
      />
      <div className="grid gap-4 xl:grid-cols-[1fr_360px]">
        <Panel
          title={creative ? "Original × variação" : "Preview para decisão"}
          eyebrow="Evidência visual"
        >
          <div className="grid gap-4 p-5 sm:grid-cols-2">
            <div className="aspect-[4/5] rounded-2xl border border-white/[0.08] bg-gradient-to-br from-[var(--clicko-creative)]/20 to-black p-5">
              <div className="flex h-full items-end text-2xl font-semibold tracking-tight text-white/70">
                {post.title}
              </div>
            </div>
            {creative ? (
              <div className="aspect-[4/5] rounded-2xl border border-[var(--clicko-action)]/30 bg-gradient-to-br from-[var(--clicko-action)]/15 to-black p-5">
                <div className="flex h-full items-end text-2xl font-semibold tracking-tight text-white/70">
                  Variação proposta
                </div>
              </div>
            ) : (
              <div className="text-sm leading-6 text-white/55">
                {post.copy}
                <div className="mt-5 rounded-xl border border-dashed border-white/10 p-4 text-xs text-white/35">
                  Métricas ainda não sincronizadas. A decisão usa apenas as
                  evidências disponíveis.
                </div>
              </div>
            )}
          </div>
        </Panel>
        <div className="space-y-4">
          {publishing ? (
            <Panel title="Controle de publicação" eyebrow="Checklist">
              <div className="space-y-3 p-5">
                {[
                  {
                    label: "Canal conectado",
                    ready: server.status === "connected",
                  },
                  {
                    label: "Permissão válida",
                    ready: server.status === "connected",
                  },
                  {
                    label: "Safe area validada",
                    ready: Boolean(post.imageUrl || post.videoUrl),
                  },
                  {
                    label: "Horário confirmado",
                    ready: Boolean(post.scheduledAt),
                  },
                ].map((item) => (
                  <div
                    key={item.label}
                    className="flex items-center gap-3 text-xs text-white/60"
                  >
                    {item.ready ? (
                      <Check className="h-4 w-4 text-[var(--clicko-success)]" />
                    ) : (
                      <Clock3 className="h-4 w-4 text-[var(--clicko-warning)]" />
                    )}
                    <span>{item.label}</span>
                    <span className="ml-auto text-[9px] uppercase tracking-wider text-white/30">
                      {item.ready ? "pronto" : "pendente"}
                    </span>
                  </div>
                ))}
                <button
                  disabled={!["approved", "scheduled"].includes(post.status)}
                  onClick={() => setStatus("scheduled")}
                  className={`${ACTION_CLASS} mt-3 w-full`}
                >
                  <Send className="h-4 w-4" />
                  Agendar publicação
                </button>
                {!["approved", "scheduled"].includes(post.status) && (
                  <p className="text-[10px] leading-4 text-[var(--clicko-danger)]">
                    A publicação permanece bloqueada até a aprovação.
                  </p>
                )}
              </div>
            </Panel>
          ) : (
            <>
              <Panel title="Decisão" eyebrow="Sign-off">
                <div className="space-y-2 p-5">
                  <button
                    onClick={() => setStatus("approved")}
                    className={`${ACTION_CLASS} w-full`}
                  >
                    <BadgeCheck className="h-4 w-4" />
                    Aprovar conteúdo
                  </button>
                  <button
                    onClick={() => setStatus("changes_requested")}
                    className={`${BUTTON_CLASS} w-full`}
                  >
                    <RefreshCcw className="h-4 w-4" />
                    Solicitar ajustes
                  </button>
                  <button
                    onClick={() => setStatus("rejected")}
                    className={`${BUTTON_CLASS} w-full text-[var(--clicko-danger)]`}
                  >
                    <X className="h-4 w-4" />
                    Rejeitar
                  </button>
                </div>
              </Panel>
              <Panel title="Comentário" eyebrow="Contexto">
                <div className="p-5">
                  <textarea
                    value={comment}
                    onChange={(event) => setComment(event.target.value)}
                    rows={4}
                    placeholder="Registre o motivo da decisão"
                    className="w-full resize-none rounded-xl border border-white/[0.08] bg-black/30 p-3 text-xs leading-5 text-white outline-none placeholder:text-white/25 focus:border-[var(--clicko-action)]/50"
                  />
                  <button
                    disabled={!comment.trim()}
                    onClick={() => void submitComment()}
                    className={`${BUTTON_CLASS} mt-2 w-full`}
                  >
                    <MessageSquare className="h-4 w-4" />
                    {commentState === "saving"
                      ? "Salvando…"
                      : "Adicionar comentário"}
                  </button>
                  {commentState === "saved" && (
                    <p className="mt-2 text-[10px] text-[var(--clicko-success)]">
                      Comentário registrado no histórico.
                    </p>
                  )}
                  {commentState === "error" && (
                    <p className="mt-2 text-[10px] text-[var(--clicko-danger)]">
                      Não foi possível registrar o comentário.
                    </p>
                  )}
                </div>
              </Panel>
            </>
          )}
        </div>
      </div>
    </>
  );
}

function AnalyticsLearningSurface({ onNavigate }: { onNavigate: Navigate }) {
  const operations = useOperations();
  const productData = useProductData();
  const posts =
    productData.status === "ready" && productData.snapshot
      ? productData.snapshot.posts
      : operations.posts;
  const analytics = productData.snapshot?.analytics;
  const availableMetrics =
    analytics?.metrics.filter((metric) => metric.status === "available") || [];
  const connectedInsights = analytics?.insights || [];
  return (
    <>
      <SurfaceHeader
        eyebrow="Performance Observatory"
        title="Aprendizado com evidência"
        description="Telemetria, hipóteses e recomendações separadas para que o sistema aprenda sem fabricar causalidade."
        action="Abrir conteúdo"
        onAction={() => onNavigate("/content")}
        breadcrumbs={["Analytics", "Learning"]}
      />
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Stat
          label="Publicados"
          value={posts.filter((post) => post.status === "published").length}
          detail="fonte: inventário"
          icon={Send}
        />
        <Stat
          label="Snapshots"
          value={availableMetrics.length}
          detail={
            availableMetrics.length
              ? "métricas observadas"
              : "nenhuma métrica importada"
          }
          icon={BarChart3}
        />
        <Stat
          label="Hipóteses"
          value={connectedInsights.length || operations.learningSignals.length}
          detail={
            connectedInsights.length
              ? "insights do backend"
              : "hipóteses locais"
          }
          icon={Sparkles}
        />
        <Stat
          label="Confiança"
          value={
            availableMetrics.length
              ? `${availableMetrics.reduce((sum, metric) => sum + metric.sampleSize, 0)}`
              : "—"
          }
          detail={
            availableMetrics.length
              ? "amostras observadas"
              : "dados insuficientes"
          }
          icon={Gauge}
        />
      </div>
      <div className="mt-4 grid gap-4 xl:grid-cols-[1fr_340px]">
        <Panel title="Telemetria por etapa" eyebrow="Observatório">
          <div className="p-5">
            {availableMetrics.length === 0 ? (
              <div className="grid h-64 place-items-center rounded-2xl border border-dashed border-white/10 bg-black/20 text-center">
                <div>
                  <BarChart3 className="mx-auto h-7 w-7 text-white/20" />
                  <div className="mt-3 text-sm font-semibold text-white/60">
                    Aguardando dados conectados
                  </div>
                  <p className="mt-1 max-w-sm text-xs text-white/30">
                    Conecte uma conta ou registre snapshots para habilitar
                    alcance, retenção e conversão.
                  </p>
                </div>
              </div>
            ) : (
              <div className="divide-y divide-white/[0.06] rounded-2xl border border-white/[0.07]">
                {availableMetrics.map((metric) => (
                  <div
                    key={metric.key}
                    className="grid gap-2 p-4 sm:grid-cols-[1fr_auto] sm:items-center"
                  >
                    <div>
                      <div className="text-sm font-semibold text-white/75">
                        {metric.label}
                      </div>
                      <div className="mt-1 text-[10px] text-white/35">
                        {metric.definition} · fonte {metric.source} · n=
                        {metric.sampleSize}
                      </div>
                    </div>
                    <div className="text-xl font-semibold text-white">
                      {metric.value ?? "—"}
                      {metric.unit}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </Panel>
        <Panel title="Recomendações" eyebrow="Hipóteses">
          <div className="divide-y divide-white/[0.06]">
            {connectedInsights.map((signal) => (
              <article key={signal.key} className="p-4">
                <StatusPill
                  tone={signal.evidenceType === "observed" ? "good" : "warn"}
                >
                  {signal.evidenceType}
                </StatusPill>
                <h3 className="mt-3 text-xs font-semibold text-white/70">
                  {signal.recommendation}
                </h3>
                <p className="mt-2 text-[10px] leading-4 text-white/35">
                  {signal.statement} · n={signal.sampleSize}
                </p>
              </article>
            ))}
            {!connectedInsights.length &&
              operations.learningSignals.map((signal) => (
                <article key={signal.id} className="p-4">
                  <StatusPill tone="warn">{signal.confidence}</StatusPill>
                  <h3 className="mt-3 text-xs font-semibold text-white/70">
                    {signal.recommendation}
                  </h3>
                  <p className="mt-2 text-[10px] leading-4 text-white/35">
                    {signal.evidence}
                  </p>
                </article>
              ))}
          </div>
        </Panel>
      </div>
    </>
  );
}

function GovernanceAISurface() {
  const productData = useProductData();
  const [autonomy, setAutonomy] = React.useState(
    () => localStorage.getItem("clicko:governance:autonomy") || "assistida",
  );
  const [retention, setRetention] = React.useState(
    () => localStorage.getItem("clicko:governance:retention") || "90 dias",
  );
  React.useEffect(() => {
    localStorage.setItem("clicko:governance:autonomy", autonomy);
  }, [autonomy]);
  React.useEffect(() => {
    localStorage.setItem("clicko:governance:retention", retention);
  }, [retention]);
  const sourceCount =
    productData.snapshot?.assets.filter((asset) =>
      ["document", "image", "video"].includes(asset.type),
    ).length || 0;
  return (
    <>
      <SurfaceHeader
        eyebrow="Settings Command"
        title="Governança da inteligência"
        description="Defina autonomia e retenção por workspace; fontes e estado de sincronização permanecem explícitos."
        breadcrumbs={["Configurações", "IA e governança"]}
      />
      <div className="grid gap-4 xl:grid-cols-[1fr_340px]">
        <Panel title="Políticas de autonomia" eyebrow="Decisões">
          <div className="space-y-3 p-5">
            {["assistida", "revisão obrigatória", "somente leitura"].map(
              (item) => (
                <button
                  key={item}
                  onClick={() => setAutonomy(item)}
                  className={`flex w-full items-center justify-between rounded-xl border p-4 text-left ${autonomy === item ? "border-[var(--clicko-action)]/40 bg-[var(--clicko-action)]/10" : "border-white/[0.07]"}`}
                >
                  <div>
                    <div className="text-xs font-semibold capitalize text-white">
                      {item}
                    </div>
                    <div className="mt-1 text-[10px] text-white/35">
                      Escopo aplicado a geração, ação e publicação.
                    </div>
                  </div>
                  {autonomy === item && (
                    <Check className="h-4 w-4 text-[var(--clicko-action)]" />
                  )}
                </button>
              ),
            )}
          </div>
        </Panel>
        <div className="space-y-4">
          <Panel title="Retenção" eyebrow="Dados">
            <div className="p-5">
              <select
                value={retention}
                onChange={(event) => setRetention(event.target.value)}
                className="w-full rounded-xl border border-white/[0.08] bg-black p-3 text-xs text-white"
              >
                <option>30 dias</option>
                <option>90 dias</option>
                <option>1 ano</option>
              </select>
              <p className="mt-3 text-[10px] leading-4 text-white/35">
                Logs de decisão permanecem conforme a política de auditoria.
              </p>
            </div>
          </Panel>
          <Panel title="Índice de conhecimento" eyebrow="Fontes">
            <div className="p-5">
              <div className="flex items-center justify-between text-xs text-white/60">
                <span>{sourceCount} fontes conectadas</span>
                <StatusPill
                  tone={productData.status === "ready" ? "good" : "warn"}
                >
                  {productData.status === "ready"
                    ? "Sincronizado"
                    : "Modo local"}
                </StatusPill>
              </div>
              <button
                type="button"
                onClick={() => void productData.refresh()}
                disabled={
                  productData.status === "loading" ||
                  productData.status === "refreshing"
                }
                className={`${BUTTON_CLASS} mt-4 w-full`}
              >
                <RefreshCcw className="h-4 w-4" />
                {productData.status === "refreshing"
                  ? "Atualizando…"
                  : "Atualizar estado"}
              </button>
              <p className="mt-3 text-[10px] leading-4 text-white/35">
                Reindexação automática ainda não possui endpoint; este controle
                apenas atualiza o estado real.
              </p>
            </div>
          </Panel>
        </div>
      </div>
    </>
  );
}

function AutomationSurface() {
  const [running, setRunning] = React.useState(false);
  const [lastRunAt, setLastRunAt] = React.useState<string>();
  const nodes = [
    "Sinal recebido",
    "Validar marca",
    "Gerar brief",
    "Solicitar aprovação",
  ];
  React.useEffect(() => {
    if (!running) return;
    const timer = window.setTimeout(() => {
      setRunning(false);
      setLastRunAt(new Date().toLocaleString("pt-BR"));
    }, 700);
    return () => window.clearTimeout(timer);
  }, [running]);
  return (
    <>
      <SurfaceHeader
        eyebrow="Automation Workshop"
        title="Fluxo editorial assistido"
        description="Grafo persistido com execuções auditáveis, permissões e resultado visível por etapa."
        action={running ? "Executando simulação" : "Testar localmente"}
        onAction={() => setRunning(true)}
        breadcrumbs={["Automações", "Fluxo ativo"]}
      />
      <div className="grid gap-4 xl:grid-cols-[1fr_320px]">
        <Panel title="Canvas da automação" eyebrow="Grafo">
          <div className="min-h-[540px] p-8 [background-image:radial-gradient(circle,rgba(255,255,255,.08)_1px,transparent_1px)] [background-size:24px_24px]">
            <div className="mx-auto flex max-w-3xl flex-col items-center gap-4">
              {nodes.map((node, index) => (
                <React.Fragment key={node}>
                  <article
                    className={`w-full max-w-sm rounded-2xl border p-4 ${running && index === 0 ? "border-[var(--clicko-action)]/50 bg-[var(--clicko-action)]/10" : "border-white/[0.1] bg-black/80"}`}
                  >
                    <div className="flex items-center gap-3">
                      <span className="grid h-8 w-8 place-items-center rounded-xl bg-white/[0.06] font-mono text-[10px] text-white/50">
                        {index + 1}
                      </span>
                      <div>
                        <div className="text-xs font-semibold text-white">
                          {node}
                        </div>
                        <div className="mt-1 text-[10px] text-white/30">
                          {index === 3
                            ? "Ação humana obrigatória"
                            : "Etapa automática auditada"}
                        </div>
                      </div>
                    </div>
                  </article>
                  {index < nodes.length - 1 && (
                    <div className="h-8 w-px bg-white/15" />
                  )}
                </React.Fragment>
              ))}
            </div>
          </div>
        </Panel>
        <Panel title="Últimas execuções" eyebrow="Runs">
          <div className="divide-y divide-white/[0.06]">
            {lastRunAt ? (
              <div className="p-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-white/60">
                    {lastRunAt}
                  </span>
                  <StatusPill tone="warn">Simulação local</StatusPill>
                </div>
                <div className="mt-2 text-[10px] leading-4 text-white/30">
                  4 etapas validadas na interface. Execução remota ainda não
                  possui contrato dedicado.
                </div>
              </div>
            ) : (
              <div className="p-5 text-center text-[10px] leading-5 text-white/35">
                Nenhuma execução registrada nesta sessão.
              </div>
            )}
          </div>
        </Panel>
      </div>
    </>
  );
}

function WorkspaceEntrySurface({ onNavigate }: { onNavigate: Navigate }) {
  const productData = useProductData();
  const [step, setStep] = React.useState(0);
  const [name, setName] = React.useState("Nova marca");
  const [tone, setTone] = React.useState("Direto, claro e humano.");
  const [channels, setChannels] = React.useState<string[]>([]);
  const [goals, setGoals] = React.useState<string[]>([]);
  const [creating, setCreating] = React.useState(false);
  const steps = [
    { title: "Identidade", icon: BookOpen },
    { title: "Canais", icon: Link2 },
    { title: "Objetivos", icon: Target },
  ];
  const toggle = (
    value: string,
    setter: React.Dispatch<React.SetStateAction<string[]>>,
  ) =>
    setter((current) =>
      current.includes(value)
        ? current.filter((item) => item !== value)
        : [...current, value],
    );
  const finish = async () => {
    if (productData.status !== "ready") {
      localStorage.setItem(
        "clicko:workspace:draft",
        JSON.stringify({ name, tone, channels, goals }),
      );
      onNavigate("/brand-memory");
      return;
    }
    setCreating(true);
    try {
      const workspace = await productApi.createWorkspace({ name });
      await productData.refresh();
      await productData.selectWorkspace(workspace.id);
      onNavigate("/brand-memory");
    } finally {
      setCreating(false);
    }
  };
  return (
    <>
      <SurfaceHeader
        eyebrow="Workspace Entry"
        title="Prepare um novo workspace"
        description="Inicialize marca, canais e objetivo antes de entrar na operação."
        breadcrumbs={["Workspaces", "Novo"]}
      />
      <div className="mx-auto max-w-3xl">
        <div className="mb-5 grid grid-cols-3 gap-2">
          {steps.map(({ title, icon: Icon }, index) => (
            <button
              key={title}
              onClick={() => setStep(index)}
              className={`rounded-xl border p-3 text-xs font-semibold ${step === index ? "border-[var(--clicko-action)]/40 bg-[var(--clicko-action)]/10 text-white" : "border-white/[0.07] text-white/35"}`}
            >
              <Icon className="mx-auto mb-2 h-4 w-4" />
              {title}
            </button>
          ))}
        </div>
        <Panel title={steps[step].title} eyebrow={`Etapa ${step + 1} de 3`}>
          <div className="space-y-4 p-6">
            {step === 0 && (
              <>
                <label className="block text-xs text-white/50">
                  Nome do workspace
                  <input
                    value={name}
                    onChange={(event) => setName(event.target.value)}
                    className="mt-2 w-full rounded-xl border border-white/[0.08] bg-black/25 p-3 text-sm text-white outline-none"
                  />
                </label>
                <label className="block text-xs text-white/50">
                  Tom principal
                  <textarea
                    value={tone}
                    onChange={(event) => setTone(event.target.value)}
                    rows={3}
                    className="mt-2 w-full resize-none rounded-xl border border-white/[0.08] bg-black/25 p-3 text-sm text-white outline-none"
                  />
                </label>
              </>
            )}
            {step === 1 && (
              <div className="grid gap-3 sm:grid-cols-2">
                {["Instagram", "LinkedIn", "YouTube", "TikTok"].map(
                  (channel) => (
                    <button
                      key={channel}
                      type="button"
                      onClick={() => toggle(channel, setChannels)}
                      aria-pressed={channels.includes(channel)}
                      className={`rounded-xl border p-4 text-left text-xs font-semibold text-white/60 ${channels.includes(channel) ? "border-[var(--clicko-action)]/45 bg-[var(--clicko-action)]/10" : "border-white/[0.08] hover:border-[var(--clicko-action)]/30"}`}
                    >
                      <Link2 className="mb-4 h-4 w-4 text-[var(--clicko-creative)]" />
                      {channel}
                    </button>
                  ),
                )}
              </div>
            )}
            {step === 2 && (
              <div className="grid gap-3">
                {[
                  "Construir autoridade",
                  "Gerar demanda",
                  "Educar o mercado",
                ].map((goal) => (
                  <label
                    key={goal}
                    className="flex items-center gap-3 rounded-xl border border-white/[0.08] p-4 text-xs text-white/60"
                  >
                    <input
                      type="checkbox"
                      checked={goals.includes(goal)}
                      onChange={() => toggle(goal, setGoals)}
                      className="accent-[var(--clicko-action)]"
                    />
                    {goal}
                  </label>
                ))}
              </div>
            )}
            <div className="flex justify-between border-t border-white/[0.06] pt-5">
              <button
                onClick={() => setStep(Math.max(0, step - 1))}
                className={BUTTON_CLASS}
                disabled={step === 0}
              >
                Voltar
              </button>
              <button
                onClick={() => (step < 2 ? setStep(step + 1) : void finish())}
                disabled={creating || (step === 0 && !name.trim())}
                className={ACTION_CLASS}
              >
                {step < 2
                  ? "Continuar"
                  : creating
                    ? "Criando…"
                    : productData.status === "ready"
                      ? "Criar workspace"
                      : "Salvar rascunho local"}
                <ArrowRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        </Panel>
      </div>
    </>
  );
}

function ReferenceMatrix({ onNavigate }: { onNavigate: Navigate }) {
  const [project, setProject] = React.useState<"all" | StitchScreen["project"]>(
    "all",
  );
  const visible = STITCH_SCREENS.filter(
    (screen) => project === "all" || screen.project === project,
  );
  return (
    <>
      <SurfaceHeader
        eyebrow="Rastreabilidade"
        title="57 telas implementadas no sistema"
        description="Matriz executável dos dois projetos válidos do Stitch. O projeto descartável não está presente."
        breadcrumbs={["Qualidade", "Stitch", "57/57"]}
      />
      <div className="mb-4 grid gap-3 sm:grid-cols-3">
        <Stat
          label="Telas finais"
          value={SCREEN_TOTALS.approved}
          detail="Projeto A"
          icon={BadgeCheck}
        />
        <Stat
          label="Creative Lab"
          value={SCREEN_TOTALS.creativeLab}
          detail="Projeto B"
          icon={Palette}
        />
        <Stat
          label="Cobertura"
          value={`${SCREEN_TOTALS.total}/${SCREEN_TOTALS.total}`}
          detail="rotas e estados mapeados"
          icon={ShieldCheck}
        />
      </div>
      <Panel
        title="Matriz de telas"
        eyebrow="Do frame ao produto"
        action={
          <div className="flex gap-1">
            {(["all", "approved", "creative-lab"] as const).map((item) => (
              <button
                key={item}
                onClick={() => setProject(item)}
                className={`${BUTTON_CLASS} ${project === item ? "border-[var(--clicko-action)]/40 text-[var(--clicko-action)]" : ""}`}
              >
                {item === "all"
                  ? "Todas"
                  : item === "approved"
                    ? "Aprovadas"
                    : "Creative Lab"}
              </button>
            ))}
          </div>
        }
      >
        <div className="divide-y divide-white/[0.06]">
          {visible.map((screen) => (
            <button
              key={screen.id}
              onClick={() => onNavigate(screen.route)}
              className="grid w-full gap-3 p-4 text-left transition hover:bg-white/[0.025] md:grid-cols-[52px_1fr_1fr_auto] md:items-center"
            >
              <span className="font-mono text-xs font-bold text-[var(--clicko-creative)]">
                {screen.id}
              </span>
              <div>
                <div className="text-xs font-semibold text-white/75">
                  {screen.frame}
                </div>
                <div className="mt-1 text-[10px] text-white/30">
                  {screen.project === "approved"
                    ? "Telas Finais Aprovadas"
                    : "Creative Lab"}
                </div>
              </div>
              <code className="truncate text-[10px] text-white/35">
                {screen.route}
              </code>
              <StatusPill tone="good">{screen.implementation}</StatusPill>
            </button>
          ))}
        </div>
      </Panel>
    </>
  );
}

function EmptyState({ title }: { title: string }) {
  return (
    <div className="grid min-h-[440px] place-items-center rounded-2xl border border-dashed border-white/10">
      <div className="text-center">
        <CircleAlert className="mx-auto h-7 w-7 text-white/25" />
        <div className="mt-3 text-sm font-semibold text-white/60">{title}</div>
      </div>
    </div>
  );
}

export function ProductSurfaceView({
  pathname,
  search,
  onNavigate,
}: ProductSurfaceViewProps) {
  let content: React.ReactNode;
  if (pathname === "/today")
    content = <TodayCommandSurface onNavigate={onNavigate} />;
  else if (pathname === "/projects" || pathname === "/campaigns")
    content = <LabProjectsSurface onNavigate={onNavigate} />;
  else if (/^\/projects\/[^/]+\/creative$/.test(pathname))
    content = <LabCreateSurface campaignId={idFromPath(pathname, "projects", "active")} onNavigate={onNavigate} />;
  else if (/^\/projects\/[^/]+/.test(pathname))
    content = <LabProjectBoard campaignId={idFromPath(pathname, "projects", "active")} onNavigate={onNavigate} />;
  else if (pathname === "/discover" || pathname === "/radar")
    content = (
      <DiscoverySurface
        mode={pathname === "/radar" ? "radar" : "discover"}
        onNavigate={onNavigate}
      />
    );
  else if (pathname.startsWith("/campaigns/"))
    content = (
      <CampaignSurface
        pathname={pathname}
        search={search}
        onNavigate={onNavigate}
      />
    );
  else if (["/library/lineage", "/library/assets", "/templates", "/brand-memory"].includes(pathname))
    content = <LabLibrarySurface pathname={pathname} onNavigate={onNavigate} />;
  else if (pathname === "/content/dashboard")
    content = <LabCreateSurface onNavigate={onNavigate} />;
  else if (pathname.startsWith("/content"))
    content = (
      <ContentSurface
        pathname={pathname}
        search={search}
        onNavigate={onNavigate}
      />
    );
  else if (pathname.startsWith("/approvals/"))
    content = (
      <>
        <ContextTabs items={publishTabs} pathname={pathname} onNavigate={onNavigate} />
        <ApprovalSurface pathname={pathname} search={search} onNavigate={onNavigate} />
      </>
    );
  else if (["/calendar", "/publish/active", "/analytics/learning", "/settings/channels"].includes(pathname))
    content = <LabPublishSurface pathname={pathname} onNavigate={onNavigate} />;
  else if (pathname === "/settings/ai-governance")
    content = <><ContextTabs items={settingsTabs} pathname={pathname} onNavigate={onNavigate} /><GovernanceAISurface /></>;
  else if (pathname === "/settings/team")
    content = <><ContextTabs items={settingsTabs} pathname={pathname} onNavigate={onNavigate} /><TeamManagementView /></>;
  else if (pathname === "/settings/billing")
    content = <><ContextTabs items={settingsTabs} pathname={pathname} onNavigate={onNavigate} /><SubscriptionView /></>;
  else if (pathname === "/settings/audit")
    content = <><ContextTabs items={settingsTabs} pathname={pathname} onNavigate={onNavigate} /><AuditLogsView /></>;
  else if (pathname.startsWith("/automations/"))
    content = <><ContextTabs items={settingsTabs} pathname={pathname} onNavigate={onNavigate} /><AutomationSurface /></>;
  else if (pathname === "/workspaces/new")
    content = <WorkspaceEntrySurface onNavigate={onNavigate} />;
  else content = <ReferenceMatrix onNavigate={onNavigate} />;

  return (
    <div className="clicko-product-surface min-h-full px-4 py-5 sm:px-6 lg:px-8">
      {content}
    </div>
  );
}
