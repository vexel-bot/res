import React from "react";
import {
  routeForPath,
  effectiveRouteOwnerForPath,
} from "../app/router/routeRegistry";
import {
  experienceActionForId,
  experienceScreenForLocation,
} from "../app/experience/registry";
import { emitExperienceTelemetry } from "../app/experience/telemetry";
import {
  ExperienceShell,
  HonestState,
} from "../app/experience/shells";
import {
  siDropbox,
  siFacebook,
  siGooglecalendar,
  siGoogledrive,
  siInstagram,
  siMeta,
  siPinterest,
  siThreads,
  siTiktok,
  siTwitch,
  siUnsplash,
  siX,
  siYoutube,
} from "simple-icons";
import {
  Activity,
  AppWindow,
  ArrowLeft,
  ArrowRight,
  AtSign,
  BarChart3,
  Bell,
  BookOpen,
  Bot,
  Boxes,
  CalendarDays,
  Check,
  ChevronDown,
  ChevronRight,
  CircleHelp,
  Clock3,
  Command,
  Compass,
  Copy,
  FileText,
  FolderKanban,
  Grid2X2,
  Home,
  Image,
  Layers3,
  LayoutGrid,
  Library,
  Link2,
  ListFilter,
  Menu,
  MessageSquare,
  MoreHorizontal,
  MousePointer2,
  Palette,
  PanelLeftClose,
  Play,
  Plus,
  Radar,
  Rocket,
  Search,
  Send,
  Settings,
  Share2,
  Sparkles,
  Target,
  Type,
  Upload,
  UserRoundCheck,
  Users,
  WandSparkles,
  X,
  Zap,
} from "lucide-react";
import { useProductData } from "../context/ProductDataContext";
import {
  productApi,
  type StudioAcousticAnalysisCapability,
  type StudioDocumentRecord,
  type StudioGenerationJobRecord,
  type StudioListeningReviewSubmission,
  type StudioPublicationPreflightRecord,
  type StudioReviewRecord,
} from "../api/productApi";
import { BackendRequestError } from "../api/client";
import { ReviewSnapshotPreview } from "../studios/ReviewSnapshotPreview";
import { STOCK_AVATAR_CANDIDATES } from "../studios/stockAvatars";
import {
  studioHeadlines,
  useStudioDocument,
} from "../studios/useStudioDocument";
import { VideoStudio } from "../studios/VideoStudio";
import {
  demoCampaign,
  demoMedia,
  demoOpportunity,
  demoPosts,
  statusLabel,
} from "./demo";
import "./canonical.css";
import "../app/experience/shells.css";
import "./feedback.css";

type Navigate = (path: string, options?: { replace?: boolean }) => void;
type ProductProps = { pathname: string; search: string; onNavigate: Navigate };
type AnyRecord = Record<string, any>;

const demoBrands: AnyRecord = {
  aurora: {
    id: "aurora",
    name: "Café Aurora",
    avatar: "CA",
    category: "Café especial",
    campaign: "Ritual de Foco",
  },
  horizonte: {
    id: "horizonte",
    name: "Clínica Horizonte",
    avatar: "CH",
    category: "Saúde integrada",
    campaign: "Cuidar antes da urgência",
  },
};

const brandIcons: AnyRecord = {
  dropbox: siDropbox,
  facebook: siFacebook,
  googleCalendar: siGooglecalendar,
  googleDrive: siGoogledrive,
  instagram: siInstagram,
  meta: siMeta,
  pinterest: siPinterest,
  threads: siThreads,
  tiktok: siTiktok,
  twitch: siTwitch,
  unsplash: siUnsplash,
  x: siX,
  youtube: siYoutube,
};

function BrandIcon({ brand, label }: { brand: string; label?: string }) {
  const normalizedBrand =
    brand === "google-business-profile" ? "googleBusinessProfile" : brand;
  const icon = brandIcons[normalizedBrand];
  if (icon) {
    return (
      <svg
        className="cx-brand-icon"
        viewBox="0 0 24 24"
        role="img"
        aria-label={label || icon.title}
        style={{ color: `#${icon.hex}` }}
      >
        <path fill="currentColor" d={icon.path} />
      </svg>
    );
  }
  if (normalizedBrand === "canva") {
    return (
      <svg
        className="cx-brand-icon"
        viewBox="0 0 24 24"
        role="img"
        aria-label={label || "Canva"}
      >
        <defs>
          <linearGradient id="cx-canva" x1="0" y1="1" x2="1" y2="0">
            <stop stopColor="#7d2ae8" />
            <stop offset="1" stopColor="#00c4cc" />
          </linearGradient>
        </defs>
        <circle cx="12" cy="12" r="11" fill="url(#cx-canva)" />
        <path
          d="M16.5 8.2c-1.1-1.5-3.2-1.7-5-.5-2.5 1.7-3.9 5.2-2.6 7.2 1.2 1.8 4.2.9 5.8-.4"
          fill="none"
          stroke="#fff"
          strokeWidth="1.8"
          strokeLinecap="round"
        />
      </svg>
    );
  }
  if (normalizedBrand === "linkedin") {
    return (
      <svg
        className="cx-brand-icon"
        viewBox="0 0 24 24"
        role="img"
        aria-label={label || "LinkedIn"}
      >
        <rect width="24" height="24" rx="4" fill="#0a66c2" />
        <circle cx="6.4" cy="7" r="1.5" fill="#fff" />
        <path
          fill="#fff"
          d="M5.1 9.4h2.6v8.5H5.1zm4.2 0h2.5v1.2h.1c.4-.7 1.3-1.5 2.8-1.5 3 0 3.5 1.9 3.5 4.5v4.3h-2.6v-3.8c0-.9 0-2.2-1.3-2.2s-1.5 1-1.5 2.1v3.9H9.3z"
        />
      </svg>
    );
  }
  if (normalizedBrand === "googleBusinessProfile") {
    return (
      <svg
        className="cx-brand-icon"
        viewBox="0 0 24 24"
        role="img"
        aria-label={label || "Google Business Profile"}
      >
        <path fill="#4285f4" d="M4 10h16v10H4z" />
        <path fill="#fff" d="M8 13h8v7H8z" />
        <path fill="#34a853" d="M3 8h4l1-4H5z" />
        <path fill="#fbbc04" d="M7 8h4V4H8z" />
        <path fill="#ea4335" d="M11 8h4l-1-4h-3z" />
        <path fill="#4285f4" d="M15 8h6l-2-4h-5z" />
      </svg>
    );
  }
  if (normalizedBrand === "slack") {
    return (
      <svg
        className="cx-brand-icon"
        viewBox="0 0 24 24"
        role="img"
        aria-label={label || "Slack"}
      >
        <path
          fill="#36c5f0"
          d="M5.2 14.1a2.1 2.1 0 1 1-2.1-2.1h2.1zM6.3 14.1a2.1 2.1 0 0 1 4.2 0v5.3a2.1 2.1 0 1 1-4.2 0z"
        />
        <path
          fill="#2eb67d"
          d="M9.9 5.2a2.1 2.1 0 1 1 2.1-2.1v2.1zM9.9 6.3a2.1 2.1 0 0 1 0 4.2H4.6a2.1 2.1 0 1 1 0-4.2z"
        />
        <path
          fill="#ecb22e"
          d="M18.8 9.9a2.1 2.1 0 1 1 2.1 2.1h-2.1zM17.7 9.9a2.1 2.1 0 0 1-4.2 0V4.6a2.1 2.1 0 1 1 4.2 0z"
        />
        <path
          fill="#e01e5a"
          d="M14.1 18.8a2.1 2.1 0 1 1-2.1 2.1v-2.1zM14.1 17.7a2.1 2.1 0 0 1 0-4.2h5.3a2.1 2.1 0 1 1 0 4.2z"
        />
      </svg>
    );
  }
  return <Boxes className="cx-brand-icon" aria-label={label || brand} />;
}

const navItems = [
  ["/dashboard", Home, "Home"],
  ["/projects", FolderKanban, "Projetos"],
  ["/library/assets", Library, "Biblioteca"],
  ["/calendar", CalendarDays, "Publicar"],
] as const;

const createItems = [
  [Image, "Post visual", "/content/draft/edit?mode=visual", "1080 × 1350"],
  [
    FileText,
    "Conteúdo editorial",
    "/content/draft/edit?mode=editorial",
    "Texto e pauta",
  ],
  [Layers3, "Carrossel", "/content/draft/edit?mode=carousel", "Até 10 páginas"],
  [Play, "Vídeo", "/content/draft/edit?mode=video", "Reel ou story"],
  [WandSparkles, "Campanha com IA", "/campaigns/new", "Do briefing ao kit"],
] as const;

function normalize(pathname: string) {
  return pathname.replace(/\/+$/, "") || "/";
}

export function isCanonicalPath(pathname: string) {
  return effectiveRouteOwnerForPath(pathname) === "canonical";
}

export function CanonicalProduct({
  pathname,
  search,
  onNavigate,
}: ProductProps) {
  const data = useProductData();
  const params = new URLSearchParams(search);
  const [spotlight, setSpotlight] = React.useState(
    params.get("spotlight") === "open",
  );
  const [mobileNav, setMobileNav] = React.useState(false);
  const [toast, setToast] = React.useState("");
  const triggerRef = React.useRef<HTMLButtonElement>(null);
  const demo = data.status === "guest";
  const brandKey = params.get("brand") === "horizonte" ? "horizonte" : "aurora";
  const brand = demo ? demoBrands[brandKey] : data.activeWorkspace;
  const workspace = demo
    ? { id: brand.id, name: brand.name, avatar: brand.avatar }
    : data.activeWorkspace;
  const focus = pathname.includes("/edit") || pathname.includes("/approvals/");

  React.useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setSpotlight(true);
      }
      if (
        !event.metaKey &&
        !event.ctrlKey &&
        !event.altKey &&
        event.key.toLowerCase() === "c" &&
        !target?.closest("input, textarea, [contenteditable='true']")
      ) {
        event.preventDefault();
        onNavigate(`${normalize(pathname)}?create=open`);
      }
      if (event.key === "Escape") {
        setSpotlight(false);
        setMobileNav(false);
        const overlayParams = new URLSearchParams(search);
        if (
          ["create", "activity", "workspace", "spotlight"].some((key) =>
            overlayParams.has(key),
          )
        )
          onNavigate(normalize(pathname));
        window.requestAnimationFrame(() => triggerRef.current?.focus());
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onNavigate, pathname, search]);
  React.useEffect(() => {
    if (params.get("spotlight") === "open") setSpotlight(true);
  }, [search]);
  React.useEffect(() => {
    if (!toast) return;
    const t = window.setTimeout(() => setToast(""), 3200);
    return () => clearTimeout(t);
  }, [toast]);

  const navigate = React.useCallback(
    (path: string) => {
      setMobileNav(false);
      if (demo && brandKey !== "aurora") {
        const target = new URL(path, window.location.origin);
        if (!target.searchParams.has("brand")) {
          target.searchParams.set("brand", brandKey);
        }
        onNavigate(`${target.pathname}${target.search}${target.hash}`);
        return;
      }
      onNavigate(path);
    },
    [brandKey, demo, onNavigate],
  );
  const state = {
    data,
    demo,
    workspace,
    brand,
    pathname,
    search,
    params,
    navigate,
    setToast,
  };
  const canonicalLocation = `${pathname}${search}`;
  const route = routeForPath(canonicalLocation);
  const experienceScreen = experienceScreenForLocation(canonicalLocation);
  React.useEffect(() => {
    if (!experienceScreen) return;
    emitExperienceTelemetry({
      event: experienceScreen.analyticsViewEvent,
      kind: "view",
      route: canonicalLocation,
      screenId: experienceScreen.screenId,
    });
  }, [canonicalLocation, experienceScreen]);
  const routeState =
    data.status === "loading"
      ? "loading"
      : data.status === "error"
        ? "recoverable-error"
        : "ready";
  const canonicalCxShellsEnabled =
    import.meta.env.VITE_CANONICAL_CX_SHELLS !== "false";
  const captureNativeActionTelemetry = React.useCallback(
    (event: React.MouseEvent<HTMLDivElement>) => {
      const origin = event.target;
      if (!(origin instanceof Element)) return;
      const control = origin.closest<HTMLElement>("[data-action-id]");
      if (!control || control.classList.contains("cx-button")) return;
      const actionId = control.dataset.actionId;
      if (!actionId) return;
      const contract = experienceActionForId(actionId);
      emitExperienceTelemetry({
        event:
          contract?.analyticsEvent ||
          `unregistered.${actionId.toLowerCase()}`,
        kind: "action",
        route: canonicalLocation,
        actionId,
      });
    },
    [canonicalLocation],
  );
  const routeContent = (
    <>
      {data.status === "error" && (
        <HonestState
          compact
          state="recoverable-error"
          title="A sincronização falhou"
          detail={data.error || "Os dados remotos não puderam ser atualizados."}
          preserved="o conteúdo que já estava aberto nesta sessão"
          impact="publicação e alterações remotas permanecem pausadas"
          actionLabel="Tentar novamente"
          actionId="WORKSPACE-RETRY-SYNC"
          onAction={() => void data.refresh()}
        />
      )}
      {demo && (
        <div className="cx-demo-banner">
          <Sparkles size={14} /> Workspace demonstrativo · exemplos não são
          persistidos{" "}
          <button data-action-id="AUTH-OPEN-LOGIN" onClick={() => navigate("/login")}>
            Entrar para conectar dados reais
          </button>
        </div>
      )}
      {data.status === "loading" ? (
        <HonestState
          state="loading"
          detail="Estamos reconstruindo o workspace e o contexto desta rota."
          preserved="a rota, o documento solicitado e a intenção de criação"
          impact="nenhuma alteração pode ser enviada até o carregamento terminar"
        />
      ) : (
        <RouteSurface {...state} />
      )}
    </>
  );

  return (
    <div
      className={`cx-product ${focus ? "cx-focus" : ""}`}
      onClickCapture={captureNativeActionTelemetry}
      data-theme="dark"
      data-demo={demo}
      data-brand={brand?.id || "workspace"}
    >
      <a className="cx-skip" href="#cx-main">
        Pular para o conteúdo
      </a>
      {!focus && (
        <Sidebar
          pathname={pathname}
          navigate={navigate}
          open={mobileNav}
          onClose={() => setMobileNav(false)}
          workspace={workspace}
          demo={demo}
          onWorkspace={() => navigate(`${normalize(pathname)}?workspace=menu`)}
        />
      )}
      {focus && <FocusRail navigate={navigate} pathname={pathname} />}
      <div className="cx-stage">
        <Header
          workspace={workspace}
          demo={demo}
          busy={data.status === "loading" || data.status === "refreshing"}
          focus={focus}
          onMenu={() => setMobileNav(true)}
          onSearch={() => setSpotlight(true)}
          triggerRef={triggerRef}
          onActivity={() => navigate(`${normalize(pathname)}?activity=open`)}
          onHelp={() =>
            setToast("Atalhos: use a busca global ou pressione C para criar.")
          }
          onProfile={() => navigate("/settings/ai-governance")}
        />
        <main id="cx-main" className="cx-main" tabIndex={-1}>
          {canonicalCxShellsEnabled && route ? (
            <ExperienceShell
              shell={route.shell}
              routeId={route.routeId}
              screenId={experienceScreen?.screenId}
              state={routeState}
            >
              {routeContent}
            </ExperienceShell>
          ) : (
            routeContent
          )}
        </main>
      </div>
      {params.get("create") === "open" && (
        <CreateMenu
          navigate={navigate}
          onClose={() => navigate(normalize(pathname))}
        />
      )}
      {params.get("activity") === "open" && (
        <ActivityDrawer
          data={data}
          demo={demo}
          navigate={navigate}
          onClose={() => navigate(normalize(pathname))}
        />
      )}
      {params.has("workspace") && (
        <WorkspaceDialog
          data={data}
          demo={demo}
          pathname={pathname}
          brand={brand}
          navigate={navigate}
          onClose={() => navigate(normalize(pathname))}
        />
      )}
      {spotlight && (
        <Spotlight
          onClose={() => {
            setSpotlight(false);
            if (params.get("spotlight") === "open")
              navigate(normalize(pathname));
            triggerRef.current?.focus();
          }}
          navigate={navigate}
        />
      )}
      {toast && (
        <div className="cx-toast" role="status">
          <Check size={16} />
          {toast}
        </div>
      )}
    </div>
  );
}

function Sidebar({
  pathname,
  navigate,
  open,
  onClose,
  workspace,
  demo,
  onWorkspace,
}: AnyRecord) {
  return (
    <>
      {open && (
        <button
          data-action-id="SHELL-TOGGLE-NAV"
          className="cx-nav-scrim"
          aria-label="Fechar navegação"
          onClick={onClose}
        />
      )}
      <aside
        className={`cx-sidebar ${open ? "is-open" : ""}`}
        aria-label="Navegação principal"
      >
        <div className="cx-logo" aria-label="Clicko Creative Lab">
          <b>
            Clicko<span>*</span>
          </b>
          <small>Creative Lab</small>
        </div>
        <button
          className="cx-create"
          data-action-id="HOME-OPEN-CREATE"
          onClick={() => navigate("/dashboard?create=open")}
        >
          <Plus size={18} />
          Criar <kbd>C</kbd>
        </button>
        <nav>
          {navItems.map(([path, Icon, label]) => {
            const active =
              pathname === path ||
              (path !== "/dashboard" && pathname.startsWith(path));
            return (
              <button
                key={path}
                data-action-id="SHELL-NAVIGATE"
                className={active ? "is-active" : ""}
                onClick={() => navigate(path)}
              >
                <Icon size={19} />
                <span>{label}</span>
                {active && <i />}
              </button>
            );
          })}
        </nav>
        <button
          data-action-id="SHELL-SELECT-WORKSPACE"
          className="cx-sidebar-workspace"
          onClick={onWorkspace}
          aria-label={`Trocar workspace: ${workspace?.name || "Workspace"}`}
        >
          <span>{workspace?.avatar?.slice?.(0, 2) || "C"}</span>
          <div>
            <b>{workspace?.name || "Workspace"}</b>
            <small>
              {demo ? "Workspace demonstrativo" : "Workspace atual"}
            </small>
          </div>
          <ChevronDown size={16} />
        </button>
      </aside>
    </>
  );
}

function FocusRail({
  navigate,
  pathname,
}: {
  navigate: Navigate;
  pathname: string;
}) {
  const contentId = pathname.split("/")[2] || "draft";
  const editorPath = `/content/${contentId}/edit`;
  return (
    <aside className="cx-focus-rail">
      <button
        data-action-id="CONTENT-BACK-INVENTORY"
        aria-label="Voltar aos conteúdos"
        onClick={() => navigate("/content")}
      >
        <ArrowLeft size={20} />
      </button>
      <div className="cx-mark">c</div>
      <button
        data-action-id="CONTENT-OPEN-VISUAL"
        aria-label="Editar foto e camadas"
        onClick={() => navigate(`${editorPath}?mode=visual`)}
      >
        <Layers3 size={19} />
      </button>
      <button
        data-action-id="CONTENT-OPEN-LIBRARY"
        aria-label="Abrir biblioteca de assets"
        onClick={() => navigate("/library/assets")}
      >
        <Image size={19} />
      </button>
      <button
        data-action-id="CONTENT-OPEN-REVIEW"
        aria-label="Abrir comentários e revisão"
        onClick={() => navigate(`/approvals/${contentId}`)}
      >
        <MessageSquare size={19} />
      </button>
      <span />
      <button
        data-action-id="CONTENT-OPEN-DETAIL"
        aria-label="Ver detalhes do conteúdo"
        onClick={() => navigate(`/content/${contentId}`)}
      >
        <CircleHelp size={19} />
      </button>
    </aside>
  );
}

function Header({
  busy,
  focus,
  onMenu,
  onSearch,
  onActivity,
  onHelp,
  onProfile,
  triggerRef,
}: AnyRecord) {
  return (
    <header className="cx-header">
      {!focus && (
        <button
          data-action-id="SHELL-TOGGLE-NAV"
          className="cx-mobile-menu"
          onClick={onMenu}
          aria-label="Abrir navegação"
        >
          <Menu size={20} />
        </button>
      )}
      <button
        data-action-id="SHELL-OPEN-SEARCH"
        ref={triggerRef}
        className="cx-search"
        onClick={onSearch}
        aria-label="Buscar projetos, modelos ou conteúdos"
      >
        <Search size={17} />
        <span>Buscar projetos, modelos ou conteúdos</span>
        <kbd>
          <Command size={12} />K
        </kbd>
      </button>
      {busy && (
        <span className="cx-sync">
          <span />
          Sincronizando
        </span>
      )}
      <button
        className="cx-icon-button"
        data-action-id="SHELL-OPEN-ACTIVITY"
        onClick={onActivity}
        aria-label="Abrir atividade"
      >
        <Bell size={19} />
        <i />
      </button>
      <button
        className="cx-icon-button"
        data-action-id="SHELL-OPEN-HELP"
        aria-label="Abrir ajuda"
        onClick={onHelp}
      >
        <CircleHelp size={19} />
      </button>
      <button
        className="cx-avatar"
        data-action-id="SHELL-OPEN-PROFILE"
        aria-label="Abrir configurações do perfil"
        onClick={onProfile}
      >
        EG
      </button>
    </header>
  );
}

function RouteSurface(props: AnyRecord) {
  const p = normalize(props.pathname);
  const mode = props.params.get("mode");
  if (p === "/" || p === "/dashboard" || p === "/today")
    return <HomeSurface {...props} />;
  if (p === "/radar" && props.params.get("view") === "opportunity")
    return <OpportunitySurface {...props} />;
  if (p === "/radar") return <RadarSurface {...props} />;
  if (p.startsWith("/radar/opportunities/"))
    return <OpportunitySurface {...props} />;
  if (p === "/campaigns/new") return <CampaignIntake {...props} />;
  if (/^\/campaigns\/[^/]+\/(world|moodboard)$/.test(p))
    return p.endsWith("moodboard") ? (
      <MoodboardSurface {...props} />
    ) : (
      <WorldSurface {...props} />
    );
  if (/^\/campaigns\/[^/]+$/.test(p)) return <CampaignSurface {...props} />;
  if (p === "/content") return <ApprovedContentHub {...props} />;
  if (/^\/content\/[^/]+\/edit$/.test(p) && mode === "presenter")
    return <PresenterStudioSurface {...props} />;
  if (/^\/content\/[^/]+\/edit$/.test(p))
    return <ApprovedEditorSurface {...props} mode={mode || "visual"} />;
  if (/^\/approvals\/[^/]+$/.test(p))
    return <ApprovedReviewSurface {...props} />;
  if (p === "/calendar") return <ApprovedCalendarSurface {...props} />;
  if (/^\/publish\/[^/]+$/.test(p))
    return <ApprovedPublisherSurface {...props} />;
  if (/^\/content\/[^/]+\/remix$/.test(p))
    return <ApprovedRemixSurface {...props} />;
  if (/^\/content\/[^/]+$/.test(p)) return <ApprovedPostDetail {...props} />;
  if (p === "/brand-memory") return <BrandMemory {...props} />;
  if (p === "/library/identities") return <IdentityLibrarySurface {...props} />;
  if (/^\/library\/assets\/[^/]+\/edit$/.test(p))
    return <ImageLabSurface {...props} />;
  if (p === "/library/assets") return <ApprovedLibrarySurface {...props} />;
  if (p === "/analytics/learning")
    return <ApprovedAnalyticsSurface {...props} />;
  if (p === "/factory" || /^\/factory\/[^/]+$/.test(p))
    return <ApprovedFactorySurface {...props} />;
  if (p === "/projects") return <ProjectsSurface {...props} />;
  if (p === "/apps") return <ApprovedAppsSurface {...props} />;
  if (/^\/apps\/[^/]+$/.test(p)) return <SocialIntegrationSurface {...props} />;
  return (
    <HonestState
      state="empty"
      title="Esta rota ainda não possui uma superfície canônica"
      detail="O contexto foi preservado, mas não existe uma tarefa implementada para este endereço."
      preserved="o endereço e o workspace atual"
      impact="nenhuma alteração foi feita"
      actionLabel="Voltar à Home"
      actionId="ROUTE-RETURN-HOME"
      onAction={() => props.navigate("/dashboard")}
    />
  );
}

function Page({
  eyebrow,
  title,
  description,
  actions,
  children,
  wide = false,
}: AnyRecord) {
  return (
    <section className={`cx-page ${wide ? "cx-page--wide" : ""}`}>
      <div className="cx-page-head">
        <div>
          <small>{eyebrow}</small>
          <h1>{title}</h1>
          {description && <p>{description}</p>}
        </div>
        {actions && <div className="cx-actions">{actions}</div>}
      </div>
      {children}
    </section>
  );
}
function Button({
  children,
  tone = "default",
  icon: Icon,
  onClick,
  disabled = false,
  type = "button",
  ariaLabel,
  actionId,
  title,
  className = "",
}: AnyRecord) {
  const hasConsequence = typeof onClick === "function" || type === "submit";
  const isDisabled = disabled || !hasConsequence;
  const disabledReason =
    title ||
    (!hasConsequence
      ? "Ação ainda não disponível neste contexto."
      : disabled
        ? "Ação indisponível enquanto esta etapa está bloqueada."
        : undefined);
  const handleClick = (event: React.MouseEvent<HTMLButtonElement>) => {
    if (actionId) {
      const contract = experienceActionForId(actionId);
      emitExperienceTelemetry({
        event:
          contract?.analyticsEvent ||
          `unregistered.${String(actionId).toLowerCase()}`,
        kind: "action",
        route: `${window.location.pathname}${window.location.search}`,
        actionId,
      });
    }
    onClick?.(event);
  };
  return (
    <button
      type={type}
      className={`cx-button cx-button--${tone} ${className}`.trim()}
      onClick={handleClick}
      disabled={isDisabled}
      aria-disabled={isDisabled || undefined}
      aria-label={ariaLabel}
      title={disabledReason}
      data-disabled-reason={isDisabled ? disabledReason : undefined}
      data-action-id={actionId}
    >
      {Icon && <Icon size={16} />}
      <span>{children}</span>
    </button>
  );
}
function Chip({ children, tone = "neutral" }: AnyRecord) {
  return <span className={`cx-chip cx-chip--${tone}`}>{children}</span>;
}
function StateBanner({
  tone = "neutral",
  title,
  detail,
  action,
  onAction,
  actionId,
}: AnyRecord) {
  return (
    <div className={`cx-state-banner cx-state-banner--${tone}`} role="status">
      <div>
        <b>{title}</b>
        <span>{detail}</span>
      </div>
      {action && (
        <Button actionId={actionId} onClick={onAction}>
          {action}
        </Button>
      )}
    </div>
  );
}
function EmptyState({ title, detail, action, actionId, onAction }: AnyRecord) {
  return (
    <div className="cx-empty">
      <div>
        <Sparkles />
      </div>
      <h2>{title}</h2>
      <p>{detail}</p>
      {action && (
        <Button tone="primary" actionId={actionId} onClick={onAction}>
          {action}
        </Button>
      )}
    </div>
  );
}

function HomeSurface({ data, demo, navigate, brand }: AnyRecord) {
  const campaigns = demo ? [demoCampaign] : data.snapshot?.campaigns || [];
  const posts = demo ? demoPosts : data.snapshot?.posts || [];
  const firstCampaign = campaigns[0] || demoCampaign;
  const isHorizonte = brand?.id === "horizonte";
  const formats = [
    [Image, "Post para Instagram", "1:1"],
    [Layers3, "Carrossel", "4:5"],
    [Play, "Stories", "9:16"],
    [Play, "Reels", "9:16"],
    [Target, "Anúncio", "1:1"],
    [FolderKanban, "Campanha", "360°"],
  ] as const;
  const continues = isHorizonte
    ? [
        [
          "Cuidar antes da urgência",
          "Em criação",
          "Última alteração há 1h por Renata",
          "/campaigns/horizonte-prevencao",
          "/canonical/brands/horizonte/campaign.svg",
        ],
        [
          "Guia de check-up por fase da vida",
          "Aguardando aprovação",
          "Revisão clínica solicitada há 3h",
          "/approvals/post-ritual?view=creative",
          "/canonical/brands/horizonte/winner.svg",
        ],
        [
          "Série: sinais que não devem esperar",
          "Pronto para publicar",
          "Última alteração há 30min por Caio",
          "/publish/post-ritual",
          "/canonical/brands/horizonte/signal.svg",
        ],
      ]
    : [
        [
          firstCampaign.name || "Campanha Ritual de Foco",
          "Em criação",
          "Última alteração há 1h por Mariana",
          `/campaigns/${firstCampaign.id || "campaign-aurora"}`,
          "/canonical/figma/s01/cover-01.png",
        ],
        [
          posts[0]?.title || "Lançamento Aurora Origens",
          "Aguardando aprovação",
          "Última alteração há 3h por João",
          `/approvals/${posts[0]?.id || "post-ritual"}?view=creative`,
          "/canonical/figma/s01/cover-02.png",
        ],
        [
          posts[1]?.title || "Stories Semana Aurora",
          "Pronto para publicar",
          "Última alteração há 30min por Felipe",
          `/publish/${posts[1]?.id || "post-ritual"}`,
          "/canonical/figma/s01/cover-03.png",
        ],
      ];
  return (
    <section className="cx-home-approved">
      <div className="cx-home-intro">
        <small>CLICKO CREATIVE LAB</small>
        <h1>O que vamos criar hoje?</h1>
        <p>
          A Clicko já conectou sinais, decisões e vencedores de{" "}
          {brand?.name || "sua marca"}.
        </p>
      </div>
      <div className="cx-home-intelligence" aria-label="Prioridades de hoje">
        {[
          [
            Radar,
            isHorizonte
              ? "4 oportunidades de prevenção"
              : "3 oportunidades merecem ação",
            "Radar",
            "/radar",
          ],
          [
            Check,
            "2 decisões esperando sua equipe",
            "Decidir",
            "/approvals/post-ritual?view=creative",
          ],
          [
            Activity,
            isHorizonte
              ? "A série de check-up ganhou força"
              : "Uma campanha perdeu força",
            "Diagnosticar",
            "/analytics/learning",
          ],
          [
            Layers3,
            "Este vencedor pode gerar 4 novas peças",
            "Reutilizar",
            "/content/post-ritual/remix",
          ],
        ].map(([Icon, title, action, path], index) => (
          <button
            key={String(title)}
            data-action-id="HOME-OPEN-PRIORITY"
            onClick={() => navigate(String(path))}
          >
            <span className={`tone-${index}`}>
              <Icon />
            </span>
            <b>{title}</b>
            <small>{action} →</small>
          </button>
        ))}
      </div>
      <div className="cx-home-or">OU COMECE COM UMA INTENÇÃO</div>
      <div className="cx-composer">
        <div>
          <Sparkles size={21} />
          <textarea
            aria-label="Descreva uma ideia, campanha ou conteúdo"
            placeholder="Descreva uma ideia, campanha ou conteúdo..."
          />
          <button
            data-action-id="HOME-START-FROM-PROMPT"
            aria-label="Gerar ponto de partida"
            onClick={() => navigate("/campaigns/new")}
          >
            <ArrowRight />
          </button>
        </div>
        <footer>
          {formats.map(([Icon, label, size]) => (
            <button
              key={label}
              data-action-id="HOME-OPEN-FORMAT"
              onClick={() =>
                navigate(
                  label === "Campanha"
                    ? "/campaigns/new"
                    : label === "Carrossel"
                      ? "/content/draft/edit?mode=carousel"
                      : "/content/draft/edit?mode=visual",
                )
              }
            >
              <Icon size={17} />
              <span>{label}</span>
              <small>{size}</small>
            </button>
          ))}
          <button
            data-action-id="HOME-OPEN-CREATE"
            onClick={() => navigate("/dashboard?create=open")}
          >
            <Plus size={17} />
            <span>Tamanho personalizado</span>
          </button>
          <Button
            icon={Upload}
            actionId="HOME-OPEN-LIBRARY"
            onClick={() => navigate("/library/assets")}
          >
            Importar da Biblioteca
          </Button>
        </footer>
      </div>
      <div className="cx-approved-section-head">
        <div>
          <small>PARA VOCÊ</small>
          <h2>Recomendado para sua marca hoje</h2>
        </div>
        <button data-action-id="HOME-OPEN-RADAR" onClick={() => navigate("/radar")}>
          Ver radar completo <ArrowRight size={15} />
        </button>
      </div>
      <div className="cx-recommendations">
        <button
          data-action-id="HOME-OPEN-OPPORTUNITY"
          onClick={() => navigate(`/radar/opportunities/${demoOpportunity.id}`)}
        >
          <img
            src={
              isHorizonte
                ? "/canonical/brands/horizonte/signal.svg"
                : "/canonical/figma/s01/hero-coffee-atmosphere.png"
            }
            alt={
              isHorizonte
                ? "Sinal de prevenção da Clínica Horizonte"
                : "Grãos de café e atmosfera de ritual"
            }
          />
          <img
            className="cx-recommendation-proof"
            src="/canonical/figma/s01/signal.png"
            alt="Sinal de crescimento de 38%"
          />
          <span className="cx-gradient" />
          <div>
            <Chip tone="orange">Em alta</Chip>
            <h3>
              {isHorizonte ? "Prevenção" : "Ritual de foco"}{" "}
              <em>está crescendo</em>
            </h3>
            <p>
              {isHorizonte
                ? "Conversas sobre check-up preventivo cresceram 42% na região nos últimos 14 dias."
                : "A busca por “ritual matinal + foco” cresceu 38% na sua categoria nos últimos 7 dias."}
            </p>
            <b>
              Criar campanha <ArrowRight size={15} />
            </b>
          </div>
        </button>
        <button
          data-action-id="HOME-OPEN-REUSE"
          onClick={() =>
            navigate(`/content/${posts[0]?.id || "post-ritual"}/remix`)
          }
        >
          <img
            src={
              isHorizonte
                ? "/canonical/brands/horizonte/winner.svg"
                : "/canonical/figma/s01/winning-content.png"
            }
            alt={`Conteúdo vencedor de ${brand?.name || "sua marca"}`}
          />
          <span className="cx-gradient" />
          <div>
            <Chip tone="coral">Remix</Chip>
            <h3>
              Seu melhor conteúdo <em>pode voltar</em>
            </h3>
            <p>
              {isHorizonte
                ? "O guia ‘Cuidar começa antes do sintoma’ teve 2,6× mais compartilhamentos."
                : "Seu post sobre “ritual de foco” teve 3× mais salvamentos que a média."}
            </p>
            <b>
              Gerar variações <ArrowRight size={15} />
            </b>
          </div>
        </button>
        <button
          data-action-id="HOME-OPEN-MOODBOARD"
          onClick={() =>
            navigate(
              `/campaigns/${firstCampaign.id || "campaign-aurora"}/moodboard`,
            )
          }
        >
          <img
            src={
              isHorizonte
                ? "/canonical/brands/horizonte/campaign.svg"
                : "/canonical/figma/s01/ugc-preview.png"
            }
            alt={
              isHorizonte
                ? "Universo criativo da Clínica Horizonte"
                : "Criadora segurando uma xícara de café"
            }
          />
          <span className="cx-gradient" />
          <div>
            <Chip>Direção</Chip>
            <h3>
              A campanha {isHorizonte ? "Horizonte" : "Aurora"}{" "}
              <em>pede um novo ângulo</em>
            </h3>
            <p>
              {isHorizonte
                ? "Perguntas reais e orientação médica clara estão gerando mais confiança."
                : "UGC e bastidores têm gerado mais conexão com o público agora."}
            </p>
            <b>
              Explorar direção <ArrowRight size={15} />
            </b>
          </div>
        </button>
      </div>
      <div className="cx-approved-section-head">
        <div>
          <small>EM ANDAMENTO</small>
          <h2>Continue de onde parou</h2>
        </div>
        <button
          data-action-id="HOME-OPEN-PROJECTS"
          onClick={() => navigate("/projects")}
        >
          Ver projetos <ArrowRight size={15} />
        </button>
      </div>
      <div className="cx-continue-grid">
        {continues.map(([title, state, meta, path, image]) => (
          <button
            key={String(title)}
            data-action-id="HOME-CONTINUE-WORK"
            onClick={() => navigate(String(path))}
          >
            <img src={String(image)} alt="" />
            <div>
              <Chip
                tone={
                  state === "Em criação"
                    ? "coral"
                    : state === "Aguardando aprovação"
                      ? "orange"
                      : "neutral"
                }
              >
                {state}
              </Chip>
              <h3>{title}</h3>
              <p>{meta}</p>
            </div>
            <ArrowRight />
          </button>
        ))}
      </div>
    </section>
  );
}
function Metric({ value, label }: AnyRecord) {
  return (
    <div>
      <strong>{value}</strong>
      <span>{label}</span>
    </div>
  );
}
function SectionHead({ title }: AnyRecord) {
  return (
    <div className="cx-section-head">
      <h2>{title}</h2>
    </div>
  );
}

function RadarSurface({ data, demo, navigate }: AnyRecord) {
  const radarState = data.snapshot?.radar;
  const samples = [
    {
      id: demoOpportunity.id,
      rank: 1,
      kind: "EVENTO · CULTURA",
      title: "Festival Brasileiro de Cafés Especiais ganha atenção",
      source: "ABIC",
      time: "24 de mai, 08:40",
      image: "/canonical/figma/phase2/s03-festival.png",
      score: 87,
      audience: "Alta",
      saturation: "Média",
      risk: "Baixo",
      window: "18h",
    },
    {
      id: "ritual-matinal",
      rank: 2,
      kind: "COMPORTAMENTO",
      title: "Ritual matinal cresce nas buscas",
      source: "Google Trends",
      time: "24 de mai, 07:20",
      image: "/canonical/figma/phase2/s03-ritual.png",
      score: 72,
      audience: "Alta",
      saturation: "Alta",
      risk: "Médio",
      window: "36h",
    },
    {
      id: "cafe-em-casa",
      rank: 3,
      kind: "CONSUMO EM ALTA",
      title: "Café brasileiro em casa",
      source: "Social Listening",
      time: "24 de mai, 06:10",
      image: "/canonical/figma/phase2/s03-coffee-home.png",
      score: 64,
      audience: "Média",
      saturation: "Média",
      risk: "Baixo",
      window: "48h",
    },
    {
      id: "memorial-day",
      rank: 4,
      kind: "TEMA EXTERNO",
      title: "Dia Memorial (EUA)",
      source: "Calendário Global",
      time: "24 de mai, 05:10",
      image: "/canonical/figma/phase2/s03-memorial.png",
      score: 12,
      audience: "Baixa",
      saturation: "Baixa",
      risk: "Alto",
      window: "Não recomendado",
    },
  ];
  const opportunities = demo
    ? samples
    : (radarState?.opportunities || []).map((op: AnyRecord, i: number) => ({
        id: op.id || String(i),
        rank: i + 1,
        kind: op.category || "OPORTUNIDADE",
        title: op.title,
        source: op.source || "Radar",
        time: op.detectedAt || "Atualizado agora",
        image: op.imageUrl || samples[i % samples.length].image,
        score: op.fitScore || op.fit || 0,
        audience: op.audienceFit || "A confirmar",
        saturation: op.saturation || "A confirmar",
        risk: op.risk || "A confirmar",
        window: op.window || "A confirmar",
      }));
  const [selectedId, setSelectedId] = React.useState(
    opportunities[0]?.id || "",
  );
  const selected =
    opportunities.find((op: AnyRecord) => op.id === selectedId) ||
    opportunities[0];
  const [saved, setSaved] = React.useState(false);
  const [timeframe, setTimeframe] = React.useState("Últimas 24h");
  const [region, setRegion] = React.useState("Brasil");
  const [theme, setTheme] = React.useState("Todos os temas");
  const [view, setView] = React.useState<"queue" | "grid">("queue");
  const [radarTab, setRadarTab] = React.useState<
    "Prioridades" | "Salvos" | "Descartados"
  >("Prioridades");
  const visibleOpportunities =
    radarTab === "Prioridades"
      ? opportunities
      : radarTab === "Salvos" && saved && selected
        ? [selected]
        : [];
  return (
    <section className="cx-radar-approved">
      <div className="cx-radar-approved-head">
        <div>
          <span>
            Descobrir <b>›</b> Radar
          </span>
          <h1>O que vale criar hoje?</h1>
          <p>Sinais atuais cruzados com sua marca, público e oferta.</p>
        </div>
        <div>
          <button
            data-action-id="RADAR-SELECT-FILTER"
            onClick={() =>
              setTimeframe((current) =>
                current === "Últimas 24h" ? "Últimos 7 dias" : "Últimas 24h",
              )
            }
            aria-label="Alterar período do Radar"
          >
            {timeframe} <ChevronDown />
          </button>
          <button
            data-action-id="RADAR-SELECT-FILTER"
            onClick={() =>
              setRegion((current) =>
                current === "Brasil" ? "Global" : "Brasil",
              )
            }
            aria-label="Alterar região do Radar"
          >
            {region} <ChevronDown />
          </button>
          <button
            data-action-id="RADAR-SELECT-FILTER"
            onClick={() =>
              setTheme((current) =>
                current === "Todos os temas"
                  ? "Café e cultura"
                  : "Todos os temas",
              )
            }
            aria-label="Alterar tema do Radar"
          >
            {theme} <ChevronDown />
          </button>
          <button
            data-action-id="RADAR-SELECT-VIEW"
            aria-label={`Alternar para visualização em ${view === "queue" ? "grade" : "fila"}`}
            aria-pressed={view === "grid"}
            onClick={() =>
              setView((current) => (current === "queue" ? "grid" : "queue"))
            }
          >
            {view === "queue" ? <Grid2X2 /> : <LayoutGrid />}
          </button>
          <small>
            <Activity size={14} aria-hidden="true" /> 12 fontes monitoradas
          </small>
        </div>
      </div>
      {!demo && radarState?.state !== "ready" && (
        <div className="cx-state-banner cx-state-banner--orange" role="status">
          <div>
            <b>Radar em preparação</b>
            <span>
              {radarState?.reason ||
                "Conecte fontes para revelar oportunidades relevantes."}
            </span>
          </div>
          <Button
            actionId="RADAR-CONFIGURE-SOURCES"
            onClick={() => navigate("/settings/channels")}
          >
            Configurar fontes
          </Button>
        </div>
      )}
      <div className="cx-radar-tabs">
        {(["Prioridades", "Salvos", "Descartados"] as const).map((item) => (
          <button
            data-action-id="RADAR-SELECT-TAB"
            className={radarTab === item ? "is-active" : ""}
            aria-pressed={radarTab === item}
            onClick={() => setRadarTab(item)}
            key={item}
          >
            {item}
          </button>
        ))}
      </div>
      {visibleOpportunities.length ? (
        <div className="cx-radar-layout" data-view={view}>
          <div className="cx-radar-queue">
            {visibleOpportunities.map((op: AnyRecord) => (
              <button
                data-action-id="RADAR-SELECT-OPPORTUNITY"
                key={op.id}
                className={selected?.id === op.id ? "is-selected" : ""}
                onClick={() => setSelectedId(op.id)}
              >
                <span className="cx-radar-rank">{op.rank}</span>
                <img src={op.image} alt="" />
                <div className="cx-radar-row-copy">
                  <small>{op.kind}</small>
                  <h2>{op.title}</h2>
                  <p>
                    Fonte: {op.source}
                    <br />
                    {op.time}
                  </p>
                </div>
                <div className="cx-mini-signal">
                  <svg viewBox="0 0 100 45">
                    <path d="M2 35 L18 29 L34 34 L50 18 L67 25 L84 8 L98 14" />
                  </svg>
                </div>
                <RadarMetric label="Relevância" value={op.score} />
                <RadarMetric label="Audiência" value={op.audience} />
                <RadarMetric label="Saturação" value={op.saturation} />
                <RadarMetric label="Janela" value={op.window} />
              </button>
            ))}
          </div>
          <aside className="cx-radar-detail">
            <header>
              <h2>{selected.title.replace(" ganha atenção", "")}</h2>
              <Chip tone="orange">✦ Oportunidade forte</Chip>
            </header>
            <div className="cx-radar-bridge-mini">
              <span>Acontecimento</span>
              <ArrowRight />
              <span>Interesse do público</span>
              <ArrowRight />
              <span className="is-active">Kit Degustação</span>
            </div>
            <h3>Por que combina</h3>
            {[
              "O festival movimenta a comunidade de cafés especiais e gera picos de conversa.",
              "Seu público valoriza origem, qualidade e histórias reais — alinhado ao posicionamento da marca.",
              "O kit degustação é a porta ideal para novos clientes provarem o melhor do Brasil.",
            ].map((x) => (
              <p className="cx-radar-reason" key={x}>
                <Check />
                {x}
              </p>
            ))}
            <dl>
              <div>
                <dt>Melhor abordagem</dt>
                <dd>Carrossel editorial + Stories</dd>
              </div>
              <div>
                <dt>Gancho sugerido</dt>
                <dd>O Brasil cabe em uma xícara.</dd>
              </div>
              <div>
                <dt>Objetivo recomendado</dt>
                <dd>Alcance qualificado</dd>
              </div>
              <div>
                <dt>Janela estimada</dt>
                <dd>{selected.window}</dd>
              </div>
              <div>
                <dt>Risco e cuidados</dt>
                <dd>
                  Creditar produtores.
                  <br />
                  Não alegar premiações.
                </dd>
              </div>
            </dl>
            <Button
              tone="primary"
              icon={ArrowRight}
              actionId="RADAR-CREATE-CAMPAIGN"
              onClick={() =>
                navigate(`/campaigns/new?opportunity=${selected.id}`)
              }
            >
              Transformar em campanha
            </Button>
            <Button
              icon={Sparkles}
              actionId="RADAR-EXPLORE-ANGLE"
              onClick={() =>
                setSelectedId(
                  opportunities[
                    (opportunities.indexOf(selected) + 1) % opportunities.length
                  ].id,
                )
              }
            >
              Explorar outro ângulo
            </Button>
            <Button
              icon={saved ? Check : BookOpen}
              actionId="RADAR-SAVE-OPPORTUNITY"
              onClick={() => setSaved(!saved)}
            >
              {saved ? "Oportunidade salva" : "Salvar oportunidade"}
            </Button>
          </aside>
        </div>
      ) : (
        <EmptyState
          title="Nenhuma oportunidade pronta"
          detail="O Radar continua coletando sinais. Você pode criar uma campanha evergreen enquanto isso."
          action="Criar campanha"
          actionId="RADAR-CREATE-CAMPAIGN"
          onAction={() => navigate("/campaigns/new")}
        />
      )}
      <div className="cx-radar-sources">
        <span>
          Fontes
          <br />e coleta
        </span>
        {[
          "ABIC",
          "Google Trends",
          "Social Listening",
          "Meta Insights",
          "YouTube Trends",
          "X (Twitter)",
          "TikTok Creative",
          "Reddit Trending",
          "Pinterest Trends",
          "Nielsen IQ",
          "Statista",
          "Eventos BR",
        ].map((x, i) => (
          <span key={x}>
            <i className={i ? "" : "is-on"} />
            {x}
          </span>
        ))}
        <small>
          Última atualização
          <br />
          24 de mai, 08:40
        </small>
      </div>
    </section>
  );
}
function RadarMetric({ label, value }: AnyRecord) {
  return (
    <div className="cx-radar-metric">
      <small>{label}</small>
      <b>{value}</b>
    </div>
  );
}

function OpportunitySurface({ navigate }: AnyRecord) {
  const [saved, setSaved] = React.useState(false);
  const [approach, setApproach] = React.useState(0);
  return (
    <section className="cx-opportunity-approved">
      <div className="cx-opportunity-main">
        <div className="cx-opportunity-head">
          <div>
            <small>
              Radar <b>/</b> Festival Brasileiro de Cafés Especiais
            </small>
            <h1>A ponte certa para sua marca</h1>
            <p>Do acontecimento à campanha, com contexto e guardrails.</p>
          </div>
          <span>Detectado há 2h · janela estimada 18h</span>
        </div>
        <div className="cx-opportunity-hero">
          <img
            src="/canonical/figma/phase2/s04-festival.png"
            alt="Festival Brasileiro de Cafés Especiais"
          />
          <span />
          <div>
            <h2>
              Festival Brasileiro
              <br />
              de Cafés Especiais
            </h2>
            <b>Crescendo nas últimas 24h</b>
            <p>Fonte ABIC · Agenda do evento · Google Trends</p>
            <small>
              Relevância <strong>87</strong> /100
            </small>
          </div>
        </div>
        <div className="cx-opportunity-bridge">
          {[
            [
              "Acontecimento",
              "origens brasileiras em evidência",
              "/canonical/figma/phase2/s04-event.png",
            ],
            [
              "Interesse do público",
              "procedência, ritual e descoberta",
              "/canonical/figma/phase2/s04-interest.png",
            ],
            [
              "Kit Degustação",
              "quatro cafés para experimentar em casa",
              "/canonical/figma/phase2/s04-kit.png",
            ],
          ].map(([title, text, image], i) => (
            <React.Fragment key={title}>
              <article>
                <img src={image} />
                <span>
                  <i>{i === 2 ? "✦" : "◎"}</i>
                  <b>{title}</b>
                  <small>{text}</small>
                </span>
              </article>
              {i < 2 && <ArrowRight />}
            </React.Fragment>
          ))}
        </div>
        <section className="cx-direction-preview">
          <h3>✦ Direção recomendada</h3>
          <div>
            {[
              [
                "CONCEITO CENTRAL",
                "O Brasil cabe em uma xícara.",
                "/canonical/figma/phase2/s04-carousel.png",
                "Carrossel editorial",
              ],
              [
                "STORIES",
                "Origens que contam histórias",
                "/canonical/figma/phase2/s04-stories.png",
                "Stories de bastidores",
              ],
              [
                "OFERTA",
                "Kit Degustação",
                "/canonical/figma/phase2/s04-offer.png",
                "Post de oferta",
              ],
            ].map(([eyebrow, title, image, caption]) => (
              <figure key={caption}>
                <img src={image} />
                <div>
                  <small>{eyebrow}</small>
                  <b>{title}</b>
                </div>
                <figcaption>{caption}</figcaption>
              </figure>
            ))}
          </div>
        </section>
        <div className="cx-provenance">
          <KeyValue
            label="Proveniência"
            value="ABIC · Agenda do evento · Google Trends"
          />
          <KeyValue label="Capturado em" value="24 de mai, 06:40" />
          <KeyValue label="Frescura" value="Muito alta" />
          <KeyValue label="Confiança" value="Alta" />
          <KeyValue label="Última atualização" value="24 de mai, 08:40" />
        </div>
      </div>
      <aside className="cx-opportunity-score">
        <h2>✦ Oportunidade forte</h2>
        {[
          ["Relevância", 92],
          ["Conexão com a oferta", 88],
          ["Atualidade", 94],
          ["Compartilhamento", 82],
          ["Saturação", 46],
          ["Risco", 18],
        ].map(([label, value]) => (
          <div className="cx-score-bar" key={String(label)}>
            <span>
              {label}
              <b>{value}</b>
            </span>
            <i>
              <em style={{ width: `${value}%` }} />
            </i>
          </div>
        ))}
        <hr />
        <h3>Por que combina</h3>
        {[
          "Festival movimenta a comunidade de cafés especiais e gera picos de conversa.",
          "Seu público valoriza origem, qualidade e histórias reais — alinhado ao posicionamento da marca.",
          "O kit degustação é a porta ideal para novos clientes provarem o melhor do Brasil.",
        ].map((x) => (
          <p className="cx-radar-reason" key={x}>
            <Check />
            {x}
          </p>
        ))}
        <hr />
        <h3>Melhor abordagem</h3>
        <dl>
          <div>
            <dt>Formato</dt>
            <dd>Carrossel editorial + Stories</dd>
          </div>
          <div>
            <dt>Objetivo</dt>
            <dd>Alcance qualificado</dd>
          </div>
          <div>
            <dt>Gancho</dt>
            <dd>O Brasil cabe em uma xícara.</dd>
          </div>
          <div>
            <dt>Janela</dt>
            <dd>Publicar em até 18h</dd>
          </div>
        </dl>
        <hr />
        <h3>Guardrails</h3>
        <p>
          · Creditar produtores e fontes.
          <br />· Não alegar premiações ou exclusividade.
        </p>
        <StateBanner
          tone="orange"
          title="E se não usar?"
          detail="A oportunidade perde força após o encerramento do evento."
        />
        <Button
          tone="primary"
          icon={ArrowRight}
          actionId="RADAR-CREATE-CAMPAIGN"
          onClick={() =>
            navigate(`/campaigns/new?opportunity=${demoOpportunity.id}`)
          }
        >
          Criar campanha com esta oportunidade
        </Button>
        <Button
          icon={Sparkles}
          actionId="RADAR-EXPLORE-ANGLE"
          onClick={() => setApproach((value) => value + 1)}
        >
          {approach
            ? `Abordagem alternativa ${approach}`
            : "Explorar outra abordagem"}
        </Button>
        <Button
          icon={saved ? Check : BookOpen}
          actionId="RADAR-SAVE-OPPORTUNITY"
          onClick={() => setSaved(!saved)}
        >
          {saved ? "Salva para depois" : "Salvar para depois"}
        </Button>
      </aside>
    </section>
  );
}

function CampaignIntake({ data, demo, params, navigate, setToast }: AnyRecord) {
  const targetMode = params.get("mode");
  const contentIntent = params.get("intent") === "content" && Boolean(targetMode);
  const [name, setName] = React.useState(
    params.get("opportunity")
      ? "O Brasil cabe em uma xícara"
      : contentIntent
        ? "Nova criação com contexto"
        : "",
  );
  const [objective, setObjective] = React.useState(
    params.get("opportunity")
      ? "Transformar o interesse por origens brasileiras em alcance qualificado e pedidos do Kit Degustação."
      : contentIntent
        ? "Transformar a oferta e a memória da marca em uma peça clara, revisável e pronta para produção."
        : demoCampaign.objective,
  );
  const [busy, setBusy] = React.useState(false);
  const [formats, setFormats] = React.useState([
    "Instagram",
    "Stories",
    "Carrossel",
    "Post de oferta",
    "Roteiro UGC",
  ]);
  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    setBusy(true);
    try {
      let id = demoCampaign.id;
      if (!demo)
        id = await data.createCampaign({
          name,
          objective,
          status: "draft",
          opportunityId: params.get("opportunity"),
          originContext: {
            source: "canonical-intake",
            intent: contentIntent ? "content" : "campaign",
            targetMode: targetMode || undefined,
          },
          startDate: "",
          endDate: "",
          budget: "",
          kpis: [],
          products: "",
          audience: "",
          offer: "",
          promise: "",
          proof: "",
          emotion: "",
          constraints: "",
          formats: [],
          formatSuggestions: [],
          cta: "",
          channels: [],
          importantDates: "",
          funnel: "",
          ctas: [],
          executionPlan: [],
          bigIdea: "",
          centralMessage: "",
          angles: [],
          hooks: [],
          narrativeSequence: [],
          creativeMatrix: [],
          brainRevision: 1,
        });
      setToast(
        demo
          ? "Campanha demonstrativa preparada"
          : "Campanha criada e sincronizada",
      );
      if (contentIntent) {
        navigate(
          `/content/draft/edit?mode=${encodeURIComponent(targetMode)}&campaign=${encodeURIComponent(id)}`,
        );
      } else {
        navigate(`/campaigns/${id}`);
      }
    } catch {
      setToast("Não foi possível criar a campanha");
    } finally {
      setBusy(false);
    }
  };
  return (
    <form className="cx-intake-approved" onSubmit={submit}>
      <main>
        <div className="cx-intake-approved-head">
          <small>
            Radar <b>/</b> Oportunidade <b>/</b> Nova campanha
          </small>
          <h1>Transforme a oportunidade em campanha</h1>
          <p>O contexto já está pronto. Revise o essencial antes de criar.</p>
        </div>
        <div className="cx-context-chain">
          <span>
            <Radar />
            Festival Brasileiro
            <br />
            de Cafés Especiais
          </span>
          <ArrowRight />
          <span>
            <BookOpen />
            Memória da marca v4
          </span>
          <ArrowRight />
          <span>
            <Target />
            Café Aurora
          </span>
          <ArrowRight />
          <span className="is-done">
            <Check />
            Contexto preservado
          </span>
        </div>
        <section className="cx-intake-section">
          <h2>◎ Fundação da campanha</h2>
          <div className="cx-foundation-grid">
            <label>
              <span>Nome da campanha</span>
              <input
                data-action-id="CAMPAIGN-EDIT-FOUNDATION"
                autoFocus
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </label>
            <label>
              <span>Objetivo</span>
              <textarea
                data-action-id="CAMPAIGN-EDIT-FOUNDATION"
                value={objective}
                onChange={(e) => setObjective(e.target.value)}
              />
            </label>
            <label>
              <span>Meta</span>
              <input defaultValue="120 pedidos em 14 dias" />
            </label>
            <label>
              <span>Período</span>
              <input defaultValue="24 mai – 07 jun" />
            </label>
          </div>
        </section>
        <section className="cx-intake-section">
          <h2>Oferta e público</h2>
          <div className="cx-offer-public">
            <article>
              <img src="/canonical/figma/phase2/s05-product.png" />
              <div>
                <small>Oferta</small>
                <b>Kit Degustação Grãos Raros · R$ 149</b>
              </div>
            </article>
            <article>
              <div>
                <small>Público</small>
                <b>
                  25–44 anos · café especial · procedência · experiências em
                  casa
                </b>
              </div>
            </article>
          </div>
        </section>
        <section className="cx-intake-section">
          <h2>▦ Canais e formatos</h2>
          <div className="cx-format-choices">
            {[
              "Instagram",
              "Stories",
              "Carrossel",
              "Post de oferta",
              "Roteiro UGC",
            ].map((x) => (
              <button
                type="button"
                data-action-id="DIRECTION-SELECT-FORMAT"
                key={x}
                className={formats.includes(x) ? "is-selected" : ""}
                onClick={() =>
                  setFormats((current) =>
                    current.includes(x)
                      ? current.filter((y) => y !== x)
                      : [...current, x],
                  )
                }
              >
                {formats.includes(x) ? <Check /> : <Plus />}
                {x}
              </button>
            ))}
          </div>
          <p>
            Seleção de canais e formatos para esta campanha. Publicações não
            serão feitas automaticamente.
          </p>
        </section>
        <section className="cx-intake-section">
          <h2>Guardrails preservados</h2>
          <div className="cx-guardrail-grid">
            {[
              "Creditar produtores e fontes",
              "Não alegar premiações ou exclusividade",
              "Tom sensorial, claro, sem elitismo",
            ].map((x) => (
              <span key={x}>
                <Check />
                {x}
              </span>
            ))}
          </div>
          <p>Essas diretrizes orientam toda a criação e revisão.</p>
        </section>
      </main>
      <aside className="cx-intake-preview">
        <div className="cx-intake-steps">
          {["Contexto", "Oferta", "Direção", "Confirmar"].map((x, i) => (
            <span className={i === 0 ? "is-active" : ""} key={x}>
              <i>{i + 1}</i>
              {x}
            </span>
          ))}
        </div>
        <h2>◎ Prévia da campanha</h2>
        <img
          src="/canonical/figma/phase2/s05-creative.png"
          alt="Prévia O Brasil cabe em uma xícara"
        />
        <h3>◎ Direção inicial</h3>
        <dl>
          <div>
            <dt>Big idea</dt>
            <dd>Quatro territórios. Uma experiência.</dd>
          </div>
          <div>
            <dt>Promessa</dt>
            <dd>Descobrir origens brasileiras em casa.</dd>
          </div>
          <div>
            <dt>Emoção</dt>
            <dd>Descoberta</dd>
          </div>
          <div>
            <dt>Funnel</dt>
            <dd>Descoberta → Consideração → Decisão</dd>
          </div>
        </dl>
        <h3>Kit inicial previsto</h3>
        {formats.map((x, i) => (
          <p className="cx-kit-line" key={x}>
            <span>{x}</span>
            <i />
            {i === 1 ? 3 : 1}
          </p>
        ))}
        <StateBanner
          tone="orange"
          title="Direção refinável"
          detail="A direção poderá ser refinada na Campaign Room."
        />
        <Button
          type="submit"
          tone="primary"
          icon={ArrowRight}
          actionId="DIRECTION-APPROVE"
          disabled={busy || !name.trim()}
        >
          {busy
            ? contentIntent
              ? "Aprovando direção…"
              : "Criando…"
            : contentIntent
              ? `Aprovar direção e abrir ${
                  targetMode === "editorial"
                    ? "Editorial"
                    : targetMode === "visual"
                      ? "Visual"
                      : targetMode === "video"
                        ? "Vídeo"
                        : "Studio"
                }`
              : "Criar campanha"}
        </Button>
        <Button
          icon={Sparkles}
          actionId="DIRECTION-REFINE"
          onClick={() =>
            setToast(
              "Direção inicial refinada sem perder o contexto da oportunidade",
            )
          }
        >
          Refinar direção
        </Button>
        <Button
          icon={ArrowLeft}
          actionId="DIRECTION-BACK-OPPORTUNITY"
          onClick={() =>
            navigate(
              `/radar/opportunities/${params.get("opportunity") || demoOpportunity.id}`,
            )
          }
        >
          Voltar à oportunidade
        </Button>
        <small>Nada será publicado automaticamente.</small>
      </aside>
    </form>
  );
}

function CampaignTabs({ id, navigate, active = "Visão geral" }: AnyRecord) {
  const tabs = [
    ["Visão geral", "", `/campaigns/${id}`],
    ["Direção", "Mundo · Moodboard", `/campaigns/${id}/world`],
    ["Produção", "Studio · Peças", "/content"],
    ["Operação", "Aprovação · Calendário", "/calendar"],
    ["Resultados", "", "/analytics/learning"],
  ];
  return (
    <div className="cx-campaign-tabs-approved">
      {tabs.map(([x, sub, p]) => (
        <button
          data-action-id="SHELL-NAVIGATE"
          key={x}
          onClick={() => navigate(p)}
          className={active === x ? "is-active" : ""}
        >
          <b>{x}</b>
          {sub && <small>{sub}</small>}
        </button>
      ))}
    </div>
  );
}
function CampaignSurface({ data, demo, pathname, navigate }: AnyRecord) {
  const id = pathname.split("/")[2];
  const campaign = demo
    ? demoCampaign
    : data.snapshot?.campaigns.find((x: AnyRecord) => x.id === id) ||
      data.snapshot?.campaigns[0];
  if (!campaign)
    return (
      <EmptyState
        title="Campanha não encontrada"
        detail="Crie uma campanha para começar."
        action="Nova campanha"
        actionId="CREATE-START-DIRECTION"
        onAction={() => navigate("/campaigns/new")}
      />
    );
  const kit = [
    [
      "Carrossel editorial",
      "Em criação",
      "/canonical/figma/phase2/s06-slides.png",
      "Retomar",
      "/content/post-ritual/edit?mode=carousel",
    ],
    [
      "Stories de bastidores",
      "Rascunho",
      "/canonical/figma/phase2/s06-stories.png",
      "Abrir",
      "/content/post-ritual/edit?mode=visual",
    ],
    [
      "Post de oferta",
      "Aguardando direção",
      "/canonical/figma/phase2/s06-offer.png",
      "Ver peça",
      "/content/post-ritual",
    ],
    [
      "Roteiro UGC",
      "Pronto para revisar",
      "/canonical/figma/phase2/s06-ugc.png",
      "Revisar",
      "/approvals/post-ritual?view=creative",
    ],
  ];
  return (
    <section className="cx-campaign-approved">
      <div className="cx-campaign-approved-main">
        <div className="cx-campaign-title">
          <div>
            <small>
              Projetos <b>/</b> {campaign.name}
            </small>
            <h1>{campaign.name}</h1>
          </div>
          <Chip tone="orange">Em produção</Chip>
          <span>24 mai – 07 jun</span>
          <div />
          <Button
            tone="primary"
            icon={Plus}
            actionId="CAMPAIGN-CREATE-PIECE"
            onClick={() => navigate("/content/draft/edit?mode=visual")}
          >
            Criar peça
          </Button>
          <Button
            icon={Sparkles}
            actionId="CAMPAIGN-OPEN-WORLD"
            onClick={() => navigate(`/campaigns/${id}/world`)}
          >
            Explorar direção
          </Button>
          <Button icon={MoreHorizontal} ariaLabel="Mais ações" />
        </div>
        <CampaignTabs id={id} navigate={navigate} />
        <div className="cx-campaign-foundation">
          <img src="/canonical/figma/phase2/s06-foundation.png" />
          <span />
          <div>
            <h2>
              O Brasil cabe
              <br />
              em uma xícara.
            </h2>
            <p>Quatro territórios. Uma experiência.</p>
            <dl>
              <div>
                <dt>Objetivo</dt>
                <dd>120 pedidos em 14 dias</dd>
              </div>
              <div>
                <dt>Origem da oportunidade</dt>
                <dd>Festival Brasileiro de Cafés Especiais</dd>
              </div>
            </dl>
          </div>
        </div>
        <section className="cx-next-action">
          <h3>◎ Próxima melhor ação</h3>
          <div>
            <img src="/canonical/figma/phase2/s06-slides.png" />
            <div>
              <h2>
                Finalize o carrossel editorial
                <br />
                para abrir a primeira rodada
                <br />
                de aprovação.
              </h2>
              <dl>
                <div>
                  <dt>Responsável</dt>
                  <dd>● Mariana</dd>
                </div>
                <div>
                  <dt>Prazo</dt>
                  <dd>Hoje, 16h</dd>
                </div>
                <div>
                  <dt>Progresso</dt>
                  <dd>4 de 6 slides</dd>
                </div>
              </dl>
              <p>✦ O hook já está alinhado à oportunidade.</p>
            </div>
            <Button
              tone="primary"
              actionId="CAMPAIGN-RESUME-CREATION"
              onClick={() =>
                navigate("/content/post-ritual/edit?mode=carousel")
              }
            >
              Retomar criação
            </Button>
          </div>
        </section>
        <section className="cx-campaign-kit">
          <h3>Kit da campanha</h3>
          <div>
            {kit.map(([title, status, image, action, path]) => (
              <article key={title}>
                <header>
                  <b>{title}</b>
                  <span>{status}</span>
                </header>
                <img src={image} />
                <footer>
                  <small>
                    ●{" "}
                    {title.includes("UGC")
                      ? "Lívia"
                      : title.includes("Stories")
                        ? "João"
                        : "Mariana"}
                  </small>
                  <button
                    data-action-id="CAMPAIGN-OPEN-KIT-ITEM"
                    onClick={() => navigate(path)}
                  >
                    {action}
                  </button>
                </footer>
              </article>
            ))}
          </div>
        </section>
        <section className="cx-campaign-flow">
          <h3>Fluxo da campanha</h3>
          <div>
            {[
              ["Oportunidade", "Festival Brasileiro de Cafés Especiais"],
              ["Campanha", "O Brasil cabe em uma xícara"],
              ["Produção", "4 peças em criação"],
              ["Aprovação", "Primeira rodada pendente"],
              ["Calendário", "Programação em preparação"],
            ].map(([title, text], i) => (
              <React.Fragment key={title}>
                <article className={i === 2 ? "is-active" : ""}>
                  <b>
                    {i < 2 ? "✓" : "⊕"} {title}
                  </b>
                  <small>{text}</small>
                </article>
                {i < 4 && <ArrowRight />}
              </React.Fragment>
            ))}
          </div>
        </section>
      </div>
      <aside className="cx-campaign-aside">
        <h3>Fundação ativa</h3>
        <img src="/canonical/figma/phase2/s05-creative.png" />
        <dl>
          <div>
            <dt>Big idea</dt>
            <dd>Quatro territórios. Uma experiência.</dd>
          </div>
          <div>
            <dt>Promessa</dt>
            <dd>Descobrir origens brasileiras em casa.</dd>
          </div>
          <div>
            <dt>Audiência</dt>
            <dd>25–44 · café especial · procedência</dd>
          </div>
          <div>
            <dt>Oferta</dt>
            <dd>Kit Degustação · R$ 149</dd>
          </div>
          <div>
            <dt>Revisão de marca</dt>
            <dd>Memória da marca v4</dd>
          </div>
        </dl>
        <hr />
        <h3>Guardrails</h3>
        {[
          "Creditar produtores e fontes",
          "Não alegar premiações ou exclusividade",
          "Tom sensorial, claro, sem elitismo",
        ].map((x) => (
          <p className="cx-aside-check" key={x}>
            <Check />
            {x}
          </p>
        ))}
        <hr />
        <h3>▣ Decisões recentes</h3>
        {[
          ["Conceito aprovado", "Lucas · há 2d"],
          ["Carrossel priorizado", "Mariana · há 1d"],
          ["CTA em revisão", "João · há 6h"],
        ].map(([x, y], i) => (
          <p className="cx-decision" key={x}>
            <i className={i === 1 ? "is-active" : ""} />
            <span>{x}</span>
            <small>{y}</small>
          </p>
        ))}
        <hr />
        <h3 className="cx-health">▥ Saúde da campanha</h3>
        <p>4 peças · 1 pronta para revisão · 0 aprovadas</p>
        <Button actionId="CAMPAIGN-OPEN-WORLD" onClick={() => navigate(`/campaigns/${id}/world`)}>
          Abrir mundo da campanha
        </Button>
        <Button actionId="CAMPAIGN-OPEN-MOODBOARD" onClick={() => navigate(`/campaigns/${id}/moodboard`)}>
          Abrir moodboard
        </Button>
      </aside>
    </section>
  );
}

const phase3Arts = [
  "/canonical/figma/phase2/s05-creative.png",
  "/canonical/figma/phase2/s04-carousel.png",
  "/canonical/figma/phase2/s04-stories.png",
  "/canonical/figma/phase2/s04-offer.png",
  "/canonical/figma/phase2/s16-product.png",
  "/canonical/figma/phase2/s16-texture.png",
];

const studioVisualHeadline = "O Brasil cabe em uma xícara.";
const studioKernelEnabled =
  import.meta.env.VITE_STUDIO_KERNEL_ENABLED !== "false";
const studioCarouselHeadlines = [
  "Ritual de foco",
  "Mais ruído, menos clareza",
  "Foco é escolha",
  "Um ritual muda o ritmo",
  "Comece pequeno",
  "Salve para amanhã",
];

function activeBrandRevision(data: AnyRecord) {
  const raw = data.activeWorkspace?.brandProfile?.watchlist?.brainRevision;
  const revision = Number(raw);
  return Number.isInteger(revision) && revision > 0 ? revision : 1;
}

function linkedOpportunityId(data: AnyRecord, post: AnyRecord) {
  return data.snapshot?.campaigns?.find(
    (campaign: AnyRecord) => campaign.id === post?.campaignId,
  )?.opportunityId;
}

function StudioVersionHistory({ studio, onClose, setToast }: AnyRecord) {
  const [selectedNumber, setSelectedNumber] = React.useState<number>();
  const [loading, setLoading] = React.useState(true);
  const [restoring, setRestoring] = React.useState(false);

  React.useEffect(() => {
    let active = true;
    studio.loadVersions()
      .then((history: AnyRecord[]) => {
        if (active) setSelectedNumber(history[0]?.number);
      })
      .catch(() => setToast("O histórico não pôde ser carregado"))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [setToast, studio.loadVersions]);

  const selected = studio.versions.find(
    (item: AnyRecord) => item.number === selectedNumber,
  );
  const selectedHeadlines = studioHeadlines(selected?.snapshot);
  const currentHeadlines = studioHeadlines(studio.document);
  const maxRows = Math.max(selectedHeadlines.length, currentHeadlines.length);
  const restore = async () => {
    if (!selected) return;
    setRestoring(true);
    try {
      await studio.restoreVersion(selected.number);
      setToast(`v${selected.number} restaurada como uma nova versão`);
      onClose();
    } catch {
      setToast("A versão não pôde ser restaurada");
    } finally {
      setRestoring(false);
    }
  };

  return (
    <ModalFrame onClose={onClose} label="Histórico de versões do Studio">
      <section className="cx-studio-history-modal">
        <header>
          <div className="cx-presenter-heading">
            <small>DOCUMENTO CANÔNICO</small>
            <h2>Histórico de versões</h2>
            <p>Compare snapshots e restaure sem sobrescrever o histórico.</p>
          </div>
          <button
            data-action-id="VERSION-HISTORY-CLOSE"
            onClick={onClose}
            aria-label="Fechar histórico"
          >
            <X />
          </button>
        </header>
        <div className="cx-studio-history-body">
          <aside aria-label="Versões disponíveis">
            {loading && <p>Carregando histórico…</p>}
            {!loading && !studio.versions.length && (
              <p>Crie uma versão para iniciar o histórico comparável.</p>
            )}
            {studio.versions.map((item: AnyRecord) => (
              <button
                data-action-id="VERSION-HISTORY-SELECT"
                key={item.number}
                className={item.number === selectedNumber ? "is-active" : ""}
                onClick={() => setSelectedNumber(item.number)}
              >
                <span>v{item.number}</span>
                <b>{item.label}</b>
                <small>
                  {new Intl.DateTimeFormat("pt-BR", {
                    dateStyle: "short",
                    timeStyle: "short",
                  }).format(new Date(item.createdAt))}
                </small>
              </button>
            ))}
          </aside>
          <main>
            {selected ? (
              <>
                <div className="cx-studio-history-summary">
                  <span>
                    Snapshot selecionado <b>v{selected.number}</b>
                  </span>
                  <span>
                    Estado atual <b>v{studio.document?.version}</b>
                  </span>
                </div>
                <div className="cx-studio-version-compare">
                  <div>
                    <small>VERSÃO SELECIONADA</small>
                    <b>{selected.snapshot.title}</b>
                  </div>
                  <div>
                    <small>DOCUMENTO ATUAL</small>
                    <b>{studio.document?.title}</b>
                  </div>
                  {Array.from({ length: maxRows }, (_, index) => {
                    const before = selectedHeadlines[index] || "—";
                    const after = currentHeadlines[index] || "—";
                    const changed = before !== after;
                    return (
                      <React.Fragment key={`${selected.number}-${index}`}>
                        <p className={changed ? "is-changed" : ""}>{before}</p>
                        <p className={changed ? "is-changed" : ""}>{after}</p>
                      </React.Fragment>
                    );
                  })}
                </div>
                <div className="cx-studio-history-warning">
                  <b>Restauração não destrutiva</b>
                  <p>
                    A Clicko cria um backup automático do estado atual e restaura o
                    snapshot como uma nova versão auditável.
                  </p>
                </div>
              </>
            ) : (
              <div className="cx-studio-history-empty">Selecione uma versão para comparar.</div>
            )}
          </main>
        </div>
        <footer>
          <Button actionId="VERSION-HISTORY-CLOSE" onClick={onClose}>
            Cancelar
          </Button>
          <Button
            tone="primary"
            actionId="VERSION-HISTORY-RESTORE"
            disabled={!selected || restoring}
            onClick={() => void restore()}
          >
            {restoring ? "Restaurando…" : "Restaurar como nova versão"}
          </Button>
        </footer>
      </section>
    </ModalFrame>
  );
}

function ApprovedContentHub({ navigate }: AnyRecord) {
  const [query, setQuery] = React.useState("");
  const [tab, setTab] = React.useState("Para criar");
  const [viewMode, setViewMode] = React.useState<"board" | "inventory">(
    "board",
  );
  const continueItems = [
    [
      "Campanha · Ritual de Foco",
      "Carrossel",
      "O Brasil cabe em uma xícara",
      "4 de 6 slides",
      "Em criação",
      phase3Arts[0],
    ],
    [
      "Campanha · Diário de Bastidores",
      "Stories",
      "Stories de bastidores",
      "Rascunho",
      "Rascunho",
      phase3Arts[2],
    ],
    [
      "Campanha · Kit Degustação",
      "Post",
      "Post Kit Degustação",
      "Aguardando direção",
      "Aguardando direção",
      phase3Arts[3],
    ],
  ].filter((item) => item[2].toLowerCase().includes(query.toLowerCase()));
  const winners = [
    ["Ritual de foco", "3× mais salvamentos", phase3Arts[0]],
    ["Origem que conta histórias", "842 compartilhamentos", phase3Arts[1]],
    ["Segunda com foco", "2,1× mais comentários", phase3Arts[2]],
  ];
  return (
    <section className="cx-content-hub-approved">
      <header className="cx-content-hub-title">
        <div>
          <h1>Criar e organizar conteúdo</h1>
          <p>
            Comece algo novo, retome uma peça ou encontre o que já funciona.
          </p>
        </div>
        <div className="cx-view-switch">
          <button
            data-action-id="CONTENT-HUB-SELECT-VIEW"
            className={viewMode === "board" ? "is-active" : ""}
            aria-pressed={viewMode === "board"}
            onClick={() => setViewMode("board")}
          >
            <Grid2X2 />
            Board visual
          </button>
          <button
            data-action-id="CONTENT-HUB-SELECT-VIEW"
            className={viewMode === "inventory" ? "is-active" : ""}
            aria-pressed={viewMode === "inventory"}
            onClick={() => setViewMode("inventory")}
          >
            <LayoutGrid />
            Inventário
          </button>
        </div>
        <Button
          tone="primary"
          icon={Plus}
          actionId="HOME-OPEN-CREATE"
          onClick={() => navigate("/dashboard?create=open")}
        >
          Novo conteúdo
        </Button>
      </header>
      <nav className="cx-content-hub-tabs">
        {[
          "Para criar",
          "Em produção",
          "Todos os conteúdos",
          "Vencedores e reuso",
        ].map((item) => (
          <button
            data-action-id="CONTENT-HUB-SELECT-VIEW"
            className={tab === item ? "is-active" : ""}
            onClick={() => setTab(item)}
            key={item}
          >
            {item}
          </button>
        ))}
      </nav>
      <h2>Comece por aqui</h2>
      <div className="cx-start-cards">
        {[
          [Image, "Post", "Imagem única ou estática"],
          [Layers3, "Carrossel", "Várias imagens em sequência"],
          [Play, "Stories", "Conteúdo vertical imersivo"],
          [Sparkles, "Usar oportunidade", "Transforme insights em conteúdo"],
          [Play, "Vídeo · Em desenvolvimento", "Em breve"],
        ].map(([Icon, title, detail], i) => (
          <button
            key={String(title)}
            data-action-id="HOME-OPEN-FORMAT"
            disabled={i === 4}
            onClick={() =>
              i === 3
                ? navigate("/radar")
                : navigate(
                    `/content/draft/edit?mode=${i === 1 ? "carousel" : i === 2 ? "visual" : "editorial"}`,
                  )
            }
          >
            <span>
              <Icon />
            </span>
            <div>
              <b>{title}</b>
              <small>{detail}</small>
            </div>
          </button>
        ))}
      </div>
      <div className="cx-content-filterbar">
        <label>
          <Search />
          <input
            data-action-id="CONTENT-HUB-SELECT-FILTER"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Buscar conteúdo"
          />
        </label>
        {[
          "Campanha  Todas",
          "Status  Todos",
          "Formato  Todos",
          "Responsável  Equipe",
          "Ordenar por  Atualizados recentemente",
        ].map((x) => (
          <button
            key={x}
            disabled
            title="Os filtros combinados serão liberados quando houver dados suficientes neste workspace."
          >
            {x}⌄
          </button>
        ))}
        <button
          disabled
          title="Os filtros avançados serão liberados quando houver dados suficientes neste workspace."
        >
          <ListFilter />
          Filtros
        </button>
      </div>
      <div
        className={`cx-content-hub-layout cx-content-hub-layout--${viewMode}`}
      >
        <main>
          <h2>Continue criando</h2>
          <div className="cx-continue-grid">
            {continueItems.map(
              ([campaign, format, title, meta, status, image], i) => (
                <article key={title}>
                  <Chip tone="orange">{campaign}</Chip>
                  <img src={image} />
                  <small>{format}</small>
                  <h3>{title}</h3>
                  <p>
                    {meta}
                    <Chip tone={i === 1 ? "neutral" : "orange"}>{status}</Chip>
                  </p>
                  <footer>
                    ● {i === 1 ? "João" : "Mariana"} · Editado há {i + 2}h{" "}
                    <button
                      data-action-id="CONTENT-HUB-OPEN-ITEM"
                      onClick={() =>
                        navigate(
                          `/content/draft/edit?mode=${i === 0 ? "carousel" : "visual"}`,
                        )
                      }
                    >
                      {i === 0 ? "Retomar" : "Abrir"} →
                    </button>
                  </footer>
                </article>
              ),
            )}
          </div>
          <div className="cx-awaiting-head">
            <h2>Aguardando decisão</h2>
            <button
              data-action-id="CONTENT-OPEN-REVIEW"
              onClick={() => navigate("/approvals/post-ritual")}
            >
              Ver todos
            </button>
          </div>
          <div className="cx-awaiting-grid">
            {[
              ["Roteiro UGC", "Pronto para revisão", phase3Arts[2]],
              [
                "Carrossel Ritual de foco",
                "Ajustes solicitados",
                phase3Arts[0],
              ],
            ].map(([title, status, image], i) => (
              <article key={title}>
                <img src={image} />
                <div>
                  <h3>{title}</h3>
                  <p>
                    ▦ {i ? "Carrossel" : "Post"}
                    <br />
                    Editado há {i + 1} dia
                  </p>
                </div>
                <Chip tone={i ? "orange" : "green"}>{status}</Chip>
                <button
                  data-action-id="CONTENT-OPEN-REVIEW"
                  onClick={() =>
                    navigate("/approvals/post-ritual?view=creative")
                  }
                >
                  Abrir →
                </button>
              </article>
            ))}
          </div>
        </main>
        <aside>
          <div>
            <h2>Vencedores para reutilizar</h2>
            <button
              data-action-id="HOME-OPEN-REUSE"
              onClick={() => navigate("/content/post-ritual/remix")}
            >
              Ver todos
            </button>
          </div>
          {winners.map(([title, metric, image]) => (
            <article key={title}>
              <img src={image} />
              <div>
                <b>{title}</b>
                <small>Campanha Ritual de Foco</small>
                <strong>{metric}</strong>
                <button
                  data-action-id="HOME-OPEN-REUSE"
                  onClick={() => navigate("/content/post-ritual/remix")}
                >
                  Abrir no Reuse Lab →
                </button>
              </div>
            </article>
          ))}
        </aside>
      </div>
    </section>
  );
}

function ApprovedEditorSurface(props: AnyRecord) {
  if (props.mode === "editorial") return <ApprovedEditorialDesk {...props} />;
  if (props.mode === "carousel") return <ApprovedCarouselBuilder {...props} />;
  if (props.mode === "video") return <VideoStudio {...props} />;
  return <ApprovedVisualEditor {...props} />;
}

function ApprovedEditorialDesk({ navigate, setToast }: AnyRecord) {
  const [selected, setSelected] = React.useState(0);
  const [hook, setHook] = React.useState(
    "O Brasil cabe em uma xícara — mas você sabe reconhecer a origem do que bebe?",
  );
  const [activeTool, setActiveTool] = React.useState("Estrutura");
  const [previewTab, setPreviewTab] = React.useState("Feed");
  const [safeArea, setSafeArea] = React.useState(false);
  const slides = [
    "Hook",
    "Origem",
    "Cerrado Mineiro",
    "Mantiqueira",
    "Experiência",
    "CTA",
  ];
  return (
    <section className="cx-editor-approved cx-editorial-approved">
      <header>
        <button
          data-action-id="SHELL-NAVIGATE"
          className="cx-editor-home"
          onClick={() => navigate("/dashboard")}
        >
          <strong>
            Clicko<span>*</span>
          </strong>
          <small>Home</small>
        </button>
        <button
          data-action-id="EDITORIAL-BACK-CAMPAIGN"
          onClick={() => navigate("/campaigns/campaign-aurora")}
        >
          ← O Brasil cabe em uma xícara
        </button>
        <h1>Carrossel editorial</h1>
        <span>◉ Instagram · 4:5　● Salvo há poucos segundos</span>
        <div />
        <Button
          actionId="EDITORIAL-PREVIEW"
          onClick={() =>
            setToast("O canvas atual é o preview disponível neste primeiro slice.")
          }
        >
          Preview
        </Button>
        <Button actionId="EDITORIAL-SAVE" onClick={() => setToast("Conteúdo salvo")}>
          Salvar
        </Button>
        <Button
          actionId="EDITORIAL-OPEN-VISUAL"
          onClick={() => navigate("/content/post-ritual/edit?mode=visual")}
        >
          Abrir no Visual
        </Button>
        <Button
          actionId="EDITORIAL-OPEN-CAROUSEL"
          onClick={() => navigate("/content/post-ritual/edit?mode=carousel")}
        >
          Abrir no Carrossel
        </Button>
        <Button
          actionId="EDITORIAL-OPEN-VIDEO"
          onClick={() => navigate("/content/post-ritual/edit?mode=video")}
        >
          Abrir no Vídeo
        </Button>
        <Button
          actionId="EDITORIAL-OPEN-PRESENTER"
          onClick={() => navigate("/content/post-ritual/edit?mode=presenter")}
        >
          Abrir no Presenter
        </Button>
        <Button
          tone="primary"
          actionId="EDITORIAL-SEND-REVIEW"
          onClick={() => navigate("/approvals/post-ritual?view=creative")}
        >
          Enviar para revisão
        </Button>
      </header>
      <nav className="cx-editor-rail">
        {[
          [Grid2X2, "Estrutura"],
          [FolderKanban, "Arquivos"],
          [Sparkles, "IA"],
          [Upload, "Upload"],
          [Target, "Contexto"],
          [CalendarDays, "Agenda"],
        ].map(([Icon, label], i) => (
          <button
            data-action-id="EDITORIAL-SELECT-TOOL"
            className={activeTool === label ? "is-active" : ""}
            aria-pressed={activeTool === label}
            title={String(label)}
            key={String(label)}
            onClick={() => setActiveTool(String(label))}
          >
            <Icon />
          </button>
        ))}
      </nav>
      <main className="cx-editorial-copy">
        <div className="cx-editorial-brief">
          <KeyValue label="Objetivo" value="Autoridade + conversão" />
          <KeyValue label="Público" value="café especial · procedência" />
          <KeyValue label="Funil" value="Consideração" />
        </div>
        <h2>Hook</h2>
        <textarea
          data-action-id="EDITORIAL-EDIT-HOOK"
          value={hook}
          onChange={(e) => setHook(e.target.value)}
        />
        <Button
          icon={Sparkles}
          actionId="EDITORIAL-STRENGTHEN-HOOK"
          onClick={() => {
            setHook(
              "O Brasil cabe em uma xícara — descubra a origem que transforma cada gole em uma história.",
            );
            setToast("Hook fortalecido; a alteração continua editável.");
          }}
        >
          Fortalecer hook
        </Button>
        <h2>Sequência do carrossel</h2>
        <div className="cx-sequence-list">
          {slides.map((slide, i) => (
            <button
              data-action-id="EDITORIAL-SELECT-SLIDE"
              className={selected === i ? "is-active" : ""}
              onClick={() => setSelected(i)}
              key={slide}
            >
              ⋮　{i + 1}
              <span>{slide}</span>
              <b>
                {
                  [
                    "Quatro territórios. Uma caixa.",
                    "Cada café começa em um lugar.",
                    "Do Cerrado Mineiro para a sua rotina.",
                    "Da Mantiqueira para momentos reais.",
                    "Experiências que cabem no seu tempo.",
                    "Conheça o Kit Degustação.",
                  ][i]
                }
              </b>
              <small>{28 + i}</small>
              <i />
            </button>
          ))}
        </div>
        <h2>Legenda e CTA</h2>
        <div className="cx-rich-copy">
          Negrito　Itálico　Lista　Link
          <textarea defaultValue="Quatro territórios. Muitas histórias. Um só propósito: levar o melhor do café brasileiro até você.\n\nDescubra origens, aromas e experiências únicas com o Kit Degustação Café Aurora." />
          <label>
            CTA do post <input defaultValue="Conheça o Kit Degustação" />
          </label>
        </div>
        <h3>Hashtags sugeridas</h3>
        <div className="cx-tags">
          {[
            "#CafeAurora",
            "#CafeEspecial",
            "#OrigemImporta",
            "#CafeDoBrasil",
            "#Degustacao",
          ].map((x) => (
            <span key={x}>{x}</span>
          ))}
        </div>
        <footer>
          Contagem total de texto: 379 caracteres <b>● Legibilidade boa</b>
        </footer>
      </main>
      <section className="cx-editorial-preview">
        <nav>
          {["Feed", "Legenda", "Slides"].map((item) => (
            <button
              data-action-id="EDITORIAL-SELECT-PREVIEW"
              className={previewTab === item ? "is-active" : ""}
              aria-pressed={previewTab === item}
              onClick={() => setPreviewTab(item)}
              key={item}
            >
              {item}
            </button>
          ))}
        </nav>
        <span>{selected + 1} / 6</span>
        <img src={selected === 5 ? phase3Arts[3] : phase3Arts[0]} />
        <div className="cx-preview-arrows">
          <button
            data-action-id="EDITORIAL-STEP-SLIDE"
            onClick={() => setSelected((selected + 5) % 6)}
          >
            ‹
          </button>
          <button
            data-action-id="EDITORIAL-SELECT-PREVIEW"
            aria-pressed={safeArea}
            onClick={() => setSafeArea((current) => !current)}
          >
            {safeArea ? "Ocultar área segura" : "Exibir área segura"}
          </button>
          <button
            data-action-id="EDITORIAL-STEP-SLIDE"
            onClick={() => setSelected((selected + 1) % 6)}
          >
            ›
          </button>
        </div>
        <div className="cx-preview-strip">
          {slides.map((_, i) => (
            <button
              data-action-id="EDITORIAL-SELECT-SLIDE"
              className={selected === i ? "is-active" : ""}
              onClick={() => setSelected(i)}
              key={i}
            >
              <img src={i === 5 ? phase3Arts[3] : phase3Arts[0]} />
              <span>{i + 1}</span>
            </button>
          ))}
        </div>
        <small>
          ⓘ O que você edita aqui reflete no Visual. Layouts, fontes e imagens
          seguem o Board Visual.
        </small>
      </section>
      <aside className="cx-editorial-context">
        <h2>Contexto aplicado</h2>
        <KeyValue label="Campanha" value="O Brasil cabe em uma xícara" />
        <KeyValue
          label="Oportunidade"
          value="Festival Brasileiro de Cafés Especiais"
        />
        <KeyValue label="Brand Memory" value="v4" />
        <StateBanner
          tone="orange"
          title="Guardrail"
          detail="Creditar produtores. Não alegar premiação."
        />
        <h3>Referências úteis</h3>
        {[
          ["Ritual de foco", "3× saves", phase3Arts[0]],
          ["Origem que conta histórias", "", phase3Arts[1]],
        ].map(([title, meta, image]) => (
          <button
            key={title}
            data-action-id="EDITORIAL-SELECT-TOOL"
            onClick={() => setToast(`Referência selecionada: ${title}`)}
          >
            <img src={image} />
            <span>
              {title}
              <b>{meta}</b>
            </span>
          </button>
        ))}
        <h3>Assistência local</h3>
        {[
          "Reduzir texto",
          "Variar CTA",
          "Adaptar tom",
          "Explicar recomendação",
        ].map((x) => (
          <button
            className="cx-assist"
            data-action-id="EDITORIAL-SELECT-TOOL"
            onClick={() => setToast(`${x}: sugestão aplicada`)}
            key={x}
          >
            {x}
            <ChevronRight />
          </button>
        ))}
        <StateBanner tone="orange" title="A IA sugere. Você decide." />
      </aside>
    </section>
  );
}

function ApprovedVisualEditor({
  data,
  demo,
  navigate,
  pathname,
  search,
  setToast,
}: AnyRecord) {
  const [layer, setLayer] = React.useState(0);
  const [zoom, setZoom] = React.useState(82);
  const [fontFamily, setFontFamily] = React.useState("Bricolage Grotesque");
  const [fontWeight, setFontWeight] = React.useState("Semibold");
  const [fontSize, setFontSize] = React.useState(76);
  const [textAlign, setTextAlign] = React.useState<"left" | "center">("left");
  const [positionX, setPositionX] = React.useState(90);
  const [positionY, setPositionY] = React.useState(120);
  const [activeSlide, setActiveSlide] = React.useState(1);
  const [synced, setSynced] = React.useState(true);
  const [slidesOpen, setSlidesOpen] = React.useState(true);
  const [historyOpen, setHistoryOpen] = React.useState(false);
  const requestedTool = new URLSearchParams(search || "").get("tool");
  const [visualTool, setVisualTool] = React.useState(
    requestedTool === "motion" ? "Movimento" : "Camadas",
  );
  const [designPanel, setDesignPanel] = React.useState<"design" | "motion">(
    requestedTool === "motion" ? "motion" : "design",
  );
  const [motionPreset, setMotionPreset] = React.useState<
    "subtle" | "balanced" | "emphasis"
  >("balanced");
  const [motionDuration, setMotionDuration] = React.useState(60);
  const [motionReduced, setMotionReduced] = React.useState(() =>
    typeof window === "undefined"
      ? false
      : window.matchMedia("(prefers-reduced-motion: reduce)").matches,
  );
  const [motionBefore, setMotionBefore] = React.useState(false);
  const [motionPreviewing, setMotionPreviewing] = React.useState(false);
  const [motionRecord, setMotionRecord] = React.useState<AnyRecord>();
  const [motionProjection, setMotionProjection] = React.useState<AnyRecord>();
  const [motionStatus, setMotionStatus] = React.useState<
    "idle" | "loading" | "saving" | "reviewing" | "ready" | "error"
  >("idle");
  const [motionError, setMotionError] = React.useState("");
  const routeId = pathname.split("/")[2];
  const targetId = demo ? "post-ritual" : routeId;
  const localStudioMode = demo || !studioKernelEnabled;
  const post = data.snapshot?.posts?.find((item: AnyRecord) => item.id === routeId);
  const studio = useStudioDocument({
    enabled: studioKernelEnabled && !demo && Boolean(post),
    workspaceId: data.activeWorkspace?.id,
    postId: post?.id,
    campaignId: post?.campaignId ?? undefined,
    contentType: "visual",
    title: post?.title || "Peça visual",
    initialHeadlines: [studioVisualHeadline],
    objective: post?.objective || "Criar uma peça visual pronta para revisão",
    audience: "Audiência do conteúdo",
    brandRevision: activeBrandRevision(data),
    opportunityId: linkedOpportunityId(data, post),
  });
  const [headline, setHeadline] = React.useState(studioVisualHeadline);
  React.useEffect(() => {
    const savedHeadline = studioHeadlines(studio.document)[0];
    if (savedHeadline) {
      setHeadline(savedHeadline);
      setSynced(true);
    }
  }, [studio.document]);
  React.useEffect(() => {
    if (requestedTool === "motion") {
      setVisualTool("Movimento");
      setDesignPanel("motion");
    }
  }, [requestedTool]);
  React.useEffect(() => {
    if (localStudioMode || !data.activeWorkspace?.id || !studio.document?.documentId) {
      return;
    }
    let current = true;
    setMotionStatus("loading");
    setMotionError("");
    void productApi
      .studioMotionGraphs(data.activeWorkspace.id, studio.document.documentId)
      .then((records) => {
        if (!current) return;
        const latest = records[0];
        setMotionRecord(latest);
        setMotionProjection(undefined);
        setMotionStatus("ready");
      })
      .catch((error) => {
        if (!current) return;
        setMotionError(
          error instanceof Error
            ? error.message
            : "Não foi possível recuperar o movimento deste documento.",
        );
        setMotionStatus("error");
      });
    return () => {
      current = false;
    };
  }, [data.activeWorkspace?.id, localStudioMode, studio.document?.documentId]);
  const saveVisual = async () => {
    if (localStudioMode) {
      setSynced(true);
      setToast("Peça visual salva");
      return;
    }
    try {
      await studio.save({
        headlines: [headline],
        narrative: { headline },
      });
      setSynced(true);
      setToast("Peça visual salva");
    } catch {
      setToast("A peça visual não pôde ser salva");
    }
  };
  const versionVisual = async () => {
    try {
      await studio.createVersion("Direção visual");
      setToast("Nova versão visual criada");
    } catch {
      setToast("A versão não pôde ser criada");
    }
  };
  const reviewVisual = async () => {
    if (localStudioMode) {
      navigate(`/approvals/${targetId}?view=creative`);
      return;
    }
    try {
      await studio.requestReview();
      navigate(`/approvals/${targetId}?view=creative`);
    } catch {
      setToast("A revisão não pôde ser solicitada");
    }
  };
  const exportVisual = async () => {
    if (localStudioMode) {
      setToast("Exportação demonstrativa preparada");
      return;
    }
    try {
      await studio.exportPng();
      setToast("PNG exportado para a biblioteca");
    } catch {
      setToast("A exportação não pôde ser concluída");
    }
  };
  const layers = [
    headline,
    "Quatro territórios. Uma caixa.",
    "Imagem do produto",
    "Xícara de café",
    "Textura de fundo",
    "Café Aurora (assinatura)",
  ];
  const selectedDocumentLayer = studio.document?.composition.pages[0]?.layers[layer];
  const motionLayerUnavailable = !localStudioMode && !selectedDocumentLayer;
  const motionLayerLocked = Boolean(selectedDocumentLayer?.locked);
  const motionStale = Boolean(
    motionRecord &&
      studio.document &&
      motionRecord.graph.documentRevision !== studio.document.revision,
  );
  const previewMotion = () => {
    setMotionBefore(false);
    setMotionPreviewing(false);
    window.requestAnimationFrame(() => setMotionPreviewing(!motionReduced));
    setToast(
      motionReduced
        ? "Prévia estática: preferência de movimento reduzido respeitada"
        : "Prévia local reproduzida; o documento ainda não mudou",
    );
  };
  const saveMotionSuggestion = async () => {
    setMotionError("");
    if (motionLayerUnavailable || motionLayerLocked) {
      setMotionError(
        motionLayerLocked
          ? "A camada selecionada está bloqueada. Desbloqueie-a antes de animar."
          : "Esta camada ainda não existe no documento persistido. Selecione a headline.",
      );
      return;
    }
    if (localStudioMode) {
      setMotionRecord({
        graph: {
          graphId: "motion-demo",
          status: "suggested",
          documentRevision: 1,
          tracks: [{ trackId: "opacity-demo" }],
        },
        storageRevision: 1,
      });
      setMotionStatus("ready");
      setToast("Sugestão demonstrativa criada; nenhum dado foi persistido");
      return;
    }
    if (!data.activeWorkspace?.id || !studio.document) return;
    setMotionStatus("saving");
    try {
      const activeDocument = studio.document.composition.mediaTimeline
        ? studio.document
        : await studio.save({
            headlines: [headline],
            narrative: { headline },
          });
      const timeline = activeDocument.composition.mediaTimeline;
      const page = activeDocument.composition.pages[0];
      const targetLayer = page.layers[layer];
      if (!timeline || !targetLayer) {
        throw new Error("O documento ainda não possui timeline ou camada compatível.");
      }
      if (targetLayer.locked) {
        throw new Error("A camada selecionada está bloqueada.");
      }
      const graphId = `motion-${crypto.randomUUID()}`;
      const endFrame = Math.max(
        1,
        Math.min(motionDuration, timeline.durationFrames - 1),
      );
      const scaleStart =
        motionPreset === "subtle" ? 0.98 : motionPreset === "balanced" ? 0.94 : 0.88;
      const opacityStart =
        motionPreset === "subtle" ? 0.62 : motionPreset === "balanced" ? 0.28 : 0;
      const trackIds = ["opacity", "scale-x", "scale-y"].map(
        (name) => `${graphId}-${name}`,
      );
      const tracks = [
        {
          trackId: trackIds[0],
          targetLayerId: targetLayer.id,
          property: "opacity" as const,
          unit: "ratio" as const,
          keyframes: [
            { frame: 0, value: opacityStart, easing: "ease_out" as const },
            { frame: endFrame, value: 1, easing: "ease_out" as const },
          ],
        },
        ...(["scale_x", "scale_y"] as const).map((property, index) => ({
          trackId: trackIds[index + 1],
          targetLayerId: targetLayer.id,
          property,
          unit: "ratio" as const,
          keyframes: [
            { frame: 0, value: scaleStart, easing: "ease_out" as const },
            { frame: endFrame, value: 1, easing: "ease_out" as const },
          ],
        })),
      ];
      const created = await productApi.createStudioMotionGraph({
        workspaceId: data.activeWorkspace.id,
        graph: {
          schemaVersion: "studio.motion-graph.v1",
          graphId,
          workspaceId: data.activeWorkspace.id,
          documentId: activeDocument.documentId,
          documentRevision: activeDocument.revision,
          frameRate: timeline.frameRate,
          durationFrames: timeline.durationFrames,
          canvasWidth: page.width,
          canvasHeight: page.height,
          realityMode: "graphic",
          completeness: "complete",
          status: "suggested",
          nodes: [],
          tracks,
          transitions: [],
          audioEvents: [],
          reducedMotionSupported: true,
          constraints: [
            {
              constraintId: `${graphId}-no-overshoot`,
              kind: "no_overshoot",
              targetTrackIds: trackIds,
              frameRange: {
                startFrame: 0,
                endFrameExclusive: timeline.durationFrames,
              },
              severity: "blocking",
            },
          ],
          sourceEvidenceIds: [],
          abstentions: [],
          createdBy: "studio-ui",
          humanReviewRequired: true,
          createdAt: new Date().toISOString(),
        },
        idempotencyKey: graphId,
      });
      setMotionRecord(created);
      setMotionProjection(
        await productApi.studioMotionProjection(created.graph.graphId, "hyperframes"),
      );
      setMotionStatus("ready");
      setToast("Sugestão reversível salva; revisão humana ainda obrigatória");
    } catch (error) {
      setMotionError(
        error instanceof Error ? error.message : "Não foi possível salvar a sugestão.",
      );
      setMotionStatus("error");
    }
  };
  const applyMotion = async () => {
    if (!motionRecord) return;
    if (localStudioMode) {
      setMotionRecord({
        ...motionRecord,
        graph: { ...motionRecord.graph, status: "reviewed" },
        storageRevision: motionRecord.storageRevision + 1,
      });
      setToast("Movimento demonstrativo aplicado");
      return;
    }
    if (!data.activeWorkspace?.id || motionStale) {
      setMotionError(
        "O documento mudou depois desta sugestão. Salve uma nova sugestão para a revisão atual.",
      );
      return;
    }
    setMotionStatus("reviewing");
    setMotionError("");
    try {
      const reviewed = await productApi.reviewStudioMotionGraph(
        motionRecord.graph.graphId,
        {
          workspaceId: data.activeWorkspace.id,
          expectedRevision: motionRecord.storageRevision,
        },
      );
      setMotionRecord(reviewed);
      setMotionProjection(
        await productApi.studioMotionProjection(reviewed.graph.graphId, "hyperframes"),
      );
      setMotionStatus("ready");
      setToast("Movimento revisado e aplicado sem achatar o documento");
    } catch (error) {
      setMotionError(
        error instanceof Error ? error.message : "Não foi possível aplicar o movimento.",
      );
      setMotionStatus("error");
    }
  };
  return (
    <section
      className={`cx-visual-approved ${designPanel === "motion" ? "is-motion-open" : ""}`}
    >
      <header>
        <button
          data-action-id="SHELL-NAVIGATE"
          className="cx-editor-home"
          onClick={() => navigate("/dashboard")}
        >
          <strong>
            Clicko<span>*</span>
          </strong>
          <small>Home</small>
        </button>
        <button
          data-action-id="VISUAL-BACK-EDITORIAL"
          className="cx-editor-back"
          onClick={() => navigate(`/content/${targetId}/edit?mode=editorial`)}
        >
          ← Carrossel editorial
        </button>
        <b>{post?.title || "O Brasil cabe em uma xícara"} · Slide 1</b>
        <span>1080×1350 · Instagram 4:5</span>
        <strong>v{studio.document?.version || 3}</strong>
        <i>
          ● {studio.status === "loading" ? "Abrindo" : studio.status === "saving" ? "Salvando" : studio.status === "dirty" ? "Alterado" : studio.status === "conflict" ? "Conflito" : studio.status === "offline" ? "Offline" : studio.status === "error" ? "Falha ao sincronizar" : synced ? "Sincronizado" : "Alterado"}
        </i>
        <div />
        <Button actionId="VISUAL-PREVIEW" onClick={() => setToast("Prévia atualizada no canvas")}>
          Preview
        </Button>
        <Button
          actionId="VISUAL-SAVE"
          disabled={!localStudioMode && studio.status !== "ready"}
          onClick={() => void saveVisual()}
        >
          Salvar
        </Button>
        <Button
          actionId="VISUAL-EXPORT"
          disabled={!localStudioMode && !studio.document}
          onClick={() => void exportVisual()}
        >
          Exportar
        </Button>
        <Button
          actionId="VISUAL-OPEN-VIDEO"
          onClick={() => navigate(`/content/${targetId}/edit?mode=video`)}
        >
          Editar vídeo
        </Button>
        <Button
          actionId="VISUAL-OPEN-HISTORY"
          disabled={localStudioMode || !studio.document}
          onClick={() => setHistoryOpen(true)}
        >
          Histórico
        </Button>
        <Button
          actionId="VISUAL-CREATE-VERSION"
          disabled={!localStudioMode && !studio.document}
          onClick={() => void versionVisual()}
        >
          Criar versão
        </Button>
        <Button
          tone="primary"
          actionId="VISUAL-SEND-REVIEW"
          onClick={() => void reviewVisual()}
        >
          Enviar para revisão
        </Button>
      </header>
      <nav className="cx-visual-tools">
        {[
          [Grid2X2, "Templates"],
          [Sparkles, "Marca"],
          [Image, "Mídia"],
          [Type, "Texto"],
          [Boxes, "Elementos"],
          [Layers3, "Camadas"],
        ].map(([Icon, label], i) => (
          <button
            data-action-id="VISUAL-SELECT-TOOL"
            className={visualTool === label ? "is-active" : ""}
            key={String(label)}
            onClick={() => {
              setVisualTool(String(label));
              setToast(`${String(label)} selecionado`);
            }}
          >
            <Icon />
            <span>{label}</span>
          </button>
        ))}
      </nav>
      <aside className="cx-layers-approved">
        <h2>
          Camadas <small>×</small>
        </h2>
        {layers.map((x, i) => (
          <button
            data-action-id="VISUAL-SELECT-LAYER"
            className={layer === i ? "is-active" : ""}
            onClick={() => setLayer(i)}
            key={x}
          >
            <span>{i < 2 ? "Texto" : "Imagem"}</span>
            <span>{x}</span>
          </button>
        ))}
        <Button
          icon={Plus}
          title="A criação de novas camadas será liberada após o editor persistir geometria completa."
        >
          Adicionar camada
        </Button>
      </aside>
      <main className="cx-visual-canvas">
        <div className="cx-visual-toolbar">
          <button
            data-action-id="VISUAL-TRANSFORM-LAYER"
            onClick={() =>
              setFontFamily((current) =>
                current === "Bricolage Grotesque" ? "Manrope" : "Bricolage Grotesque",
              )
            }
          >
            {fontFamily}
          </button>
          <button
            data-action-id="VISUAL-TRANSFORM-LAYER"
            onClick={() =>
              setFontWeight((current) =>
                current === "Semibold" ? "Bold" : "Semibold",
              )
            }
          >
            {fontWeight}
          </button>
          <button
            data-action-id="VISUAL-TRANSFORM-LAYER"
            onClick={() => setFontSize((current) => (current === 76 ? 64 : 76))}
          >
            {fontSize}
          </button>
          <button
            data-action-id="VISUAL-TRANSFORM-LAYER"
            aria-label="Alternar alinhamento do texto"
            aria-pressed={textAlign === "center"}
            onClick={() =>
              setTextAlign((current) => (current === "left" ? "center" : "left"))
            }
          >
            Alinhamento
          </button>
          <button
            data-action-id="VISUAL-TRANSFORM-LAYER"
            onClick={() => setTextAlign((current) => (current === "left" ? "center" : "left"))}
          >
            {textAlign === "left" ? "À esquerda" : "Centralizado"}
          </button>
          <button data-action-id="VISUAL-TRANSFORM-LAYER" onClick={() => setPositionX((current) => current + 8)}>
            X {positionX}
          </button>
          <button data-action-id="VISUAL-TRANSFORM-LAYER" onClick={() => setPositionY((current) => current + 8)}>
            Y {positionY}
          </button>
        </div>
        <div className="cx-visual-stage">
          <div
            className={`${designPanel === "motion" && motionPreviewing && !motionBefore ? `is-motion-preview is-${motionPreset}` : ""} ${motionReduced ? "is-reduced-motion" : ""}`}
            onAnimationEnd={() => setMotionPreviewing(false)}
          >
            <img
              src={phase3Arts[0]}
              alt="Composição visual do slide ativo"
            />
            <span className="cx-safe-area" />
            <span
              className="cx-selection"
              style={{
                fontFamily,
                fontSize: `${fontSize}px`,
                fontWeight: fontWeight === "Bold" ? 700 : 600,
                textAlign,
                transform: `translate(${positionX - 90}px, ${positionY - 120}px)`,
              }}
            >
              <strong>
                {headline.toUpperCase()}
              </strong>
              <i />
              <i />
              <i />
              <i />
            </span>
          </div>
        </div>
        <div className="cx-zoom">
          <button data-action-id="VISUAL-SET-ZOOM" onClick={() => setZoom(Math.max(40, zoom - 5))}>−</button>
          {zoom}%
          <button data-action-id="VISUAL-SET-ZOOM" onClick={() => setZoom(Math.min(120, zoom + 5))}>+</button>
        </div>
      </main>
      <aside className="cx-design-approved">
        <nav>
          <button
            data-action-id="VISUAL-SELECT-PANEL"
            className={designPanel === "design" ? "is-active" : ""}
            onClick={() => {
              setDesignPanel("design");
              navigate(`${pathname}?mode=visual`, { replace: true });
            }}
          >
            Design
          </button>
          <button disabled title="Efeitos chegarão em uma etapa posterior">Efeitos · Depois</button>
          <Button
            className={designPanel === "motion" ? "is-active" : ""}
            actionId="VISUAL-OPEN-MOTION"
            onClick={() => {
              setDesignPanel("motion");
              setVisualTool("Movimento");
              navigate(`${pathname}?mode=visual&tool=motion`, { replace: true });
            }}
          >
            Movimento
          </Button>
        </nav>
        {designPanel === "motion" ? (
          <div className="cx-motion-inspector" data-testid="motion-inspector">
            <header>
              <span>Motion Inspector</span>
              <small>Camada: {layers[layer]}</small>
            </header>
            {motionLayerUnavailable && (
              <StateBanner
                tone="orange"
                title="Camada ainda não vinculada"
                detail="Selecione a headline, que é a camada editável persistida neste documento."
              />
            )}
            {motionLayerLocked && (
              <StateBanner
                tone="orange"
                title="Camada bloqueada"
                detail="O movimento não pode alterar uma camada protegida."
              />
            )}
            <section>
              <h2>Intenção</h2>
              <div className="cx-motion-presets" role="group" aria-label="Intenção do movimento">
                {[
                  ["subtle", "Sutil"],
                  ["balanced", "Equilibrado"],
                  ["emphasis", "Ênfase"],
                ].map(([value, label]) => (
                  <button
                    data-action-id="MOTION-SELECT-PRESET"
                    key={value}
                    className={motionPreset === value ? "is-active" : ""}
                    onClick={() => setMotionPreset(value as typeof motionPreset)}
                  >
                    {label}
                  </button>
                ))}
              </div>
              <label>
                Duração <b>{motionDuration} frames</b>
                <input
                  data-action-id="MOTION-CONFIGURE-PREVIEW"
                  aria-label="Duração do movimento em frames"
                  type="range"
                  min="24"
                  max="120"
                  step="6"
                  value={motionDuration}
                  onChange={(event) => setMotionDuration(Number(event.target.value))}
                />
              </label>
              <label className="cx-motion-toggle">
                <input
                  data-action-id="MOTION-CONFIGURE-PREVIEW"
                  type="checkbox"
                  checked={motionReduced}
                  onChange={(event) => setMotionReduced(event.target.checked)}
                />
                Respeitar movimento reduzido
              </label>
            </section>
            <section>
              <h2>Comparação segura</h2>
              <div className="cx-motion-compare">
                <button
                  data-action-id="MOTION-COMPARE"
                  className={motionBefore ? "is-active" : ""}
                  onClick={() => setMotionBefore(true)}
                >
                  Antes
                </button>
                <button
                  data-action-id="MOTION-COMPARE"
                  className={!motionBefore ? "is-active" : ""}
                  onClick={() => setMotionBefore(false)}
                >
                  Depois
                </button>
              </div>
              <Button actionId="MOTION-PREVIEW" onClick={previewMotion}>
                <Play size={15} aria-hidden="true" /> Pré-visualizar localmente
              </Button>
            </section>
            {motionStatus === "loading" && (
              <StateBanner tone="blue" title="Recuperando movimento salvo…" />
            )}
            {motionError && (
              <StateBanner
                tone="orange"
                title="O movimento não foi alterado"
                detail={motionError}
              />
            )}
            {motionRecord && (
              <section className="cx-motion-record">
                <small>
                  {motionRecord.graph.status === "reviewed" ? "APLICADO" : "SUGESTÃO"}
                </small>
                <b>{motionRecord.graph.tracks.length} trilhas · revisão {motionRecord.graph.documentRevision}</b>
                <p>
                  {motionStale
                    ? "Documento mudou: esta sugestão ficou histórica."
                    : motionProjection?.previewOnly
                      ? "Projeção de preview; aplicação humana pendente."
                      : motionRecord.graph.status === "reviewed"
                        ? "Projeção HyperFrames liberada para produção."
                        : "Sugestão recuperada e ainda não aplicada."}
                </p>
              </section>
            )}
            <footer>
              <Button
                actionId="MOTION-SAVE-SUGGESTION"
                disabled={
                  motionStatus === "saving" ||
                  motionStatus === "reviewing" ||
                  motionLayerUnavailable ||
                  motionLayerLocked
                }
                onClick={() => void saveMotionSuggestion()}
              >
                {motionStatus === "saving" ? "Salvando…" : "Salvar sugestão"}
              </Button>
              <Button
                tone="primary"
                actionId="MOTION-APPLY"
                disabled={
                  !motionRecord ||
                  motionRecord.graph.status === "reviewed" ||
                  motionStatus === "reviewing" ||
                  motionStale
                }
                onClick={() => void applyMotion()}
              >
                {motionStatus === "reviewing" ? "Validando…" : "Revisar e aplicar"}
              </Button>
              <button
                data-action-id="MOTION-RESET-PREVIEW"
                className="cx-motion-reset"
                onClick={() => {
                  setMotionPreset("balanced");
                  setMotionDuration(60);
                  setMotionBefore(true);
                  setMotionPreviewing(false);
                  setToast("A prévia local foi redefinida; registros salvos foram preservados");
                }}
              >
                Redefinir apenas a prévia
              </button>
            </footer>
          </div>
        ) : (
          <>
        <h2>Tipografia</h2>
        <textarea
          data-action-id="VISUAL-EDIT-HEADLINE"
          className="cx-visual-headline-field"
          aria-label="Headline visual"
          disabled={!localStudioMode && studio.status !== "ready"}
          value={headline}
          onChange={(event) => {
            const nextHeadline = event.target.value;
            setHeadline(nextHeadline);
            setSynced(false);
            if (!localStudioMode) {
              studio.queueSave({
                headlines: [nextHeadline],
                narrative: { headline: nextHeadline },
              });
            }
          }}
        />
        {studio.status === "conflict" && (
          <StateBanner
            tone="orange"
            title="Este documento mudou em outra sessão."
            action="Recarregar versão atual"
            onAction={() => void studio.reload()}
          />
        )}
        <input
          aria-label="Família tipográfica selecionada"
          value="Bricolage Grotesque"
          readOnly
        />
        <div>
          <input aria-label="Peso tipográfico selecionado" value="Semibold" readOnly />
          <input aria-label="Tamanho tipográfico selecionado" value="76 px" readOnly />
        </div>
        <small>Altura da linha　 Espaçamento　 Alinhamento</small>
        <p>0,95　　　　 0%　　　　 Alinhamento à esquerda</p>
        <hr />
        <h2>Posição e tamanho</h2>
        <div className="cx-design-grid">
          {["X 90", "Y 120", "L 900", "A 540", "↻ 0°", "Opacidade 100%"].map(
            (x) => (
              <button
                key={x}
                disabled
                title="Edite posição e tamanho pela barra do canvas neste slice."
              >
                {x}
              </button>
            ),
          )}
        </div>
        <hr />
        <h2>Guardrail da marca</h2>
        <p>✓ Contraste aprovado</p>
        <p>✓ Headline dentro da área segura</p>
        <p>✓ Tom visual alinhado à Memória v4</p>
        <Button actionId="VISUAL-OPEN-COACH" onClick={() => setToast("Composition Coach aberto")}>
          ✦ Ver Composition Coach
        </Button>
        <hr />
        <h2>Plano de fundo</h2>
        <article>
          <img src={phase3Arts[0]} alt="Textura de fundo selecionada" />
          <span>
            Textura de fundo · Café Aurora
            <small>Asset aprovado da campanha</small>
          </span>
          <button
            data-action-id="VISUAL-REPLACE-ASSET"
            onClick={() =>
              navigate(`/library/assets?returnTo=${encodeURIComponent(`${pathname}${search || ""}`)}`)
            }
          >
            Substituir
          </button>
        </article>
        <hr />
        <h2>Recursos avançados</h2>
        {[
          "Sombras　Beta △",
          "Máscaras　Beta △",
          "Modos de mesclagem　Beta △",
        ].map((x) => (
          <button
            className="cx-disabled"
            key={x}
            disabled
            title="Recurso em avaliação; nenhuma alteração será aplicada."
          >
            {x}
          </button>
        ))}
          </>
        )}
      </aside>
      <div
        className={`cx-slide-strip-approved ${slidesOpen ? "" : "is-collapsed"}`}
      >
        <b>Slides do carrossel</b>
        <button
          data-action-id="VISUAL-SELECT-PANEL"
          className="cx-slide-strip-toggle"
          onClick={() => setSlidesOpen(!slidesOpen)}
        >
          {slidesOpen ? "Recolher" : "Abrir slides"}
        </button>
        <div>
          {[1, 2, 3, 4, 5, 6].map((x) => (
            <button
              data-action-id="VISUAL-SELECT-LAYER"
              className={x === activeSlide ? "is-active" : ""}
              aria-pressed={x === activeSlide}
              aria-label={`Selecionar slide ${x}`}
              onClick={() => setActiveSlide(x)}
              key={x}
            >
              <img src={x === 6 ? phase3Arts[3] : phase3Arts[0]} alt="" />
              <span>{x}</span>
            </button>
          ))}
          <button
            className="cx-add-slide"
            disabled
            title="Adicione slides no Studio de Carrossel para preservar a narrativa e o versionamento."
          >
            <Plus />
            Adicionar slide
          </button>
          <aside>
            <button
              disabled
              title="Crie variações pelo fluxo Reuse para preservar lineage."
            >
              Variações
            </button>
            <button
              data-action-id="VISUAL-OPEN-REFERENCES"
              onClick={() => navigate("/library/assets")}
            >
              Referências
            </button>
          </aside>
        </div>
      </div>
      {historyOpen && (
        <StudioVersionHistory
          studio={studio}
          onClose={() => setHistoryOpen(false)}
          setToast={setToast}
        />
      )}
    </section>
  );
}

function ApprovedCarouselBuilder({
  data,
  demo,
  navigate,
  pathname,
  setToast,
}: AnyRecord) {
  const routeId = pathname.split("/")[2];
  const targetId = demo ? "post-ritual" : routeId;
  const localStudioMode = demo || !studioKernelEnabled;
  const post = data.snapshot?.posts?.find((item: AnyRecord) => item.id === routeId);
  const studio = useStudioDocument({
    enabled: studioKernelEnabled && !demo && Boolean(post),
    workspaceId: data.activeWorkspace?.id,
    postId: post?.id,
    campaignId: post?.campaignId ?? undefined,
    contentType: "carousel",
    title: post?.title || "Carrossel",
    initialHeadlines: studioCarouselHeadlines,
    objective: post?.objective || "Criar um carrossel com progressão narrativa",
    audience: "Audiência do conteúdo",
    brandRevision: activeBrandRevision(data),
    opportunityId: linkedOpportunityId(data, post),
  });
  const [slides, setSlides] = React.useState(studioCarouselHeadlines);
  const [selected, setSelected] = React.useState(0);
  const [shared, setShared] = React.useState(false);
  const [previewOpen, setPreviewOpen] = React.useState(false);
  const [historyOpen, setHistoryOpen] = React.useState(false);
  const [canvasTab, setCanvasTab] = React.useState("Conteúdo");
  const [inspectorTab, setInspectorTab] = React.useState("Conteúdo");
  const [transition, setTransition] = React.useState("Corte limpo · 0,4s");
  const [cta, setCta] = React.useState("Salve para amanhã");
  const carouselRole = (index: number) =>
    ["promessa", "tensão", "virada", "prova", "ação", "cta"][index] ||
    "apoio";
  React.useEffect(() => {
    const savedHeadlines = studioHeadlines(studio.document);
    if (savedHeadlines.length > 1) setSlides(savedHeadlines);
  }, [studio.document]);
  React.useEffect(() => {
    if (!previewOpen) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setPreviewOpen(false);
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [previewOpen]);
  const title = slides[selected] || "Novo momento";
  const saveCarousel = async () => {
    if (localStudioMode) {
      setToast("Carrossel salvo");
      return;
    }
    try {
      await studio.save({
        headlines: slides,
        narrative: {
          arc: slides,
          roles: slides.map((_, index) => carouselRole(index)),
          selectedSlide: selected + 1,
        },
      });
      setToast("Carrossel salvo");
    } catch {
      setToast("O carrossel não pôde ser salvo");
    }
  };
  const exportCarousel = async () => {
    if (localStudioMode) {
      setToast("Exportação demonstrativa preparada");
      return;
    }
    try {
      await studio.exportPng();
      setToast("Pacote PNG ordenado exportado para a biblioteca");
    } catch {
      setToast("A exportação não pôde ser concluída");
    }
  };
  const updateSlides = (next: string[]) => {
    setSlides(next);
    if (!localStudioMode) {
      studio.queueSave({
        headlines: next,
        narrative: {
          arc: next,
          roles: next.map((_, index) => carouselRole(index)),
          selectedSlide: Math.min(selected + 1, next.length),
        },
      });
    }
  };
  const moveSelected = (direction: -1 | 1) => {
    const destination = selected + direction;
    if (destination < 0 || destination >= slides.length) return;
    const next = [...slides];
    [next[selected], next[destination]] = [next[destination], next[selected]];
    setSelected(destination);
    updateSlides(next);
  };
  const duplicateSelected = () => {
    const next = [...slides];
    next.splice(selected + 1, 0, `${slides[selected]} — variação`);
    setSelected(selected + 1);
    updateSlides(next);
  };
  const removeSelected = () => {
    if (slides.length <= 2) return;
    const next = slides.filter((_, index) => index !== selected);
    setSelected(Math.min(selected, next.length - 1));
    updateSlides(next);
  };
  const reviewCarousel = async () => {
    if (localStudioMode) {
      navigate(`/approvals/${targetId}?view=creative`);
      return;
    }
    try {
      await studio.requestReview();
      navigate(`/approvals/${targetId}?view=creative`);
    } catch {
      setToast("A revisão não pôde ser solicitada");
    }
  };
  return (
    <section className="cx-carousel-approved">
      <header>
        <strong>Clicko*</strong>
        <b>Carrossel — {post?.title || "Ritual de foco"}</b>
        <span>
          {studio.status === "loading" ? "Abrindo…" : studio.status === "saving" ? "Salvando…" : studio.status === "dirty" ? "Alterações pendentes" : studio.status === "conflict" ? "Conflito de edição" : studio.status === "offline" ? "Offline · alterações pendentes" : studio.status === "error" ? "Falha ao sincronizar" : `v${studio.document?.version || 1} · Salvo agora`}
        </span>
        <div />
        <Button
          actionId="CAROUSEL-UNDO"
          disabled={!localStudioMode}
          onClick={() => setToast("Desfazer permanece disponível somente no modo demonstrativo.")}
        >
          ↶
        </Button>
        <Button
          actionId="CAROUSEL-VISUALIZE-SET"
          onClick={() => setPreviewOpen(true)}
        >
          Visualizar conjunto
        </Button>
        <Button
          actionId="CAROUSEL-SHARE"
          icon={shared ? Check : Share2}
          onClick={() => {
            if (localStudioMode) setShared(!shared);
            else setToast("Compartilhamento externo ainda não está habilitado.");
          }}
        >
          {localStudioMode && shared ? "Link copiado" : "Compartilhar"}
        </Button>
        <Button
          actionId="CAROUSEL-SAVE"
          disabled={!localStudioMode && studio.status !== "ready"}
          onClick={() => void saveCarousel()}
        >
          Salvar
        </Button>
        <Button
          tone="primary"
          actionId="CAROUSEL-EXPORT"
          disabled={!localStudioMode && !studio.document}
          onClick={() => void exportCarousel()}
        >
          Exportar
        </Button>
        <Button
          actionId="CAROUSEL-CREATE-VERSION"
          disabled={!localStudioMode && !studio.document}
          onClick={() => void studio.createVersion("Direção do carrossel").then(() => setToast("Nova versão do carrossel criada")).catch(() => setToast("A versão não pôde ser criada"))}
        >
          Criar versão
        </Button>
        <Button
          actionId="CAROUSEL-OPEN-HISTORY"
          disabled={localStudioMode || !studio.document}
          onClick={() => setHistoryOpen(true)}
        >
          Histórico
        </Button>
        <Button actionId="CAROUSEL-SEND-REVIEW" onClick={() => void reviewCarousel()}>
          Revisar
        </Button>
      </header>
      <aside className="cx-carousel-narrative">
        <small>NARRATIVA</small>
        <p>{slides.length} slides · 48s de leitura</p>
        {slides.map((text, i) => (
          <button
            data-action-id="CAROUSEL-SELECT-SLIDE"
            className={selected === i ? "is-active" : ""}
            onClick={() => setSelected(i)}
            key={`${text}-${i}`}
          >
            <span>{String(i + 1).padStart(2, "0")}</span>
            <small>
              {["PROMESSA", "TENSÃO", "VIRADA", "PROVA", "AÇÃO", "CTA"][i] ||
                "APOIO"}
            </small>
            <b>{text}</b>
            <i>
              <em style={{ width: `${54 + i * 7}%` }} />
            </i>
          </button>
        ))}
        <Button
          icon={Plus}
          actionId="CAROUSEL-ADD-SLIDE"
          onClick={() => updateSlides([...slides, "Novo momento"])}
        >
          Adicionar slide
        </Button>
        <div className="cx-carousel-order-tools" aria-label="Organizar slide selecionado">
          <button
            data-action-id="CAROUSEL-MOVE-SLIDE"
            disabled={selected === 0}
            onClick={() => moveSelected(-1)}
            aria-label="Mover slide para cima"
          >
            ↑
          </button>
          <button
            data-action-id="CAROUSEL-MOVE-SLIDE"
            disabled={selected === slides.length - 1}
            onClick={() => moveSelected(1)}
            aria-label="Mover slide para baixo"
          >
            ↓
          </button>
          <button data-action-id="CAROUSEL-DUPLICATE-SLIDE" onClick={duplicateSelected}>
            Duplicar
          </button>
          <button
            data-action-id="CAROUSEL-DELETE-SLIDE"
            disabled={slides.length <= 2}
            onClick={removeSelected}
          >
            Excluir
          </button>
        </div>
        <footer>
          Ritmo narrativo
          <br />
          <b>PROMESSA → TENSÃO → VIRADA → PROVA → AÇÃO</b>
        </footer>
      </aside>
      <main className="cx-carousel-stage">
        <nav>
          {["Conteúdo", "Design", "Animação"].map((item) => (
            <button
              data-action-id="CAROUSEL-SELECT-TOOL"
              className={canvasTab === item ? "is-active" : ""}
              aria-pressed={canvasTab === item}
              onClick={() => setCanvasTab(item)}
              key={item}
            >
              {item}
            </button>
          ))}
          <span>−　82%　+</span>
        </nav>
        <div className="cx-carousel-art">
          <img src="/canonical/figma/phase3/s17-visual.png" />
          <div>
            <small>RITUAL DE FOCO</small>
            <h1>{title}</h1>
            <p>
              Um ritual simples ajuda a separar
              <br />o que importa do que apenas chama.
            </p>
            <i />
            <b>CAFÉ AURORA</b>
            <span>
              {String(selected + 1).padStart(2, "0")} /{" "}
              {String(slides.length).padStart(2, "0")}
            </span>
          </div>
        </div>
        <div className="cx-carousel-transition">
          <button
            data-action-id="CAROUSEL-STEP-SLIDE"
            onClick={() =>
              setSelected((selected - 1 + slides.length) % slides.length)
            }
          >
            ‹
          </button>
          <span>
            Transição entre slides
            <button
              data-action-id="CAROUSEL-SELECT-TOOL"
              onClick={() =>
                setTransition((current) =>
                  current === "Corte limpo · 0,4s"
                    ? "Dissolver · 0,6s"
                    : "Corte limpo · 0,4s",
                )
              }
            >
              {transition}
            </button>
          </span>
          <button
            data-action-id="CAROUSEL-VISUALIZE-SET"
            aria-label="Abrir preview contínuo"
            onClick={() => setPreviewOpen(true)}
          >
            Reproduzir
          </button>
          <button
            data-action-id="CAROUSEL-STEP-SLIDE"
            onClick={() => setSelected((selected + 1) % slides.length)}
          >
            ›
          </button>
        </div>
      </main>
      <aside className="cx-carousel-inspector">
        <nav>
          {["Conteúdo", "Design", "Marca", "Sequência"].map((x) => (
            <button
              data-action-id="CAROUSEL-SELECT-TOOL"
              className={inspectorTab === x ? "is-active" : ""}
              aria-pressed={inspectorTab === x}
              onClick={() => setInspectorTab(x)}
              key={x}
            >
              {x}
            </button>
          ))}
        </nav>
        <small>FUNÇÃO NARRATIVA</small>
        <button
          disabled
          title="A função narrativa é calculada pela posição; reordene o slide para alterá-la."
        >
          Promessa principal
        </button>
        <small>TÍTULO</small>
        <textarea
          data-action-id="CAROUSEL-EDIT-TITLE"
          aria-label="Título do slide"
          disabled={!localStudioMode && studio.status !== "ready"}
          value={title}
          onChange={(event) => {
            const next = slides.map((headline, index) =>
              index === selected ? event.target.value : headline,
            );
            updateSlides(next);
          }}
        />
        {studio.status === "conflict" && (
          <StateBanner
            tone="orange"
            title="Este carrossel mudou em outra sessão."
            action="Recarregar versão atual"
            onAction={() => void studio.reload()}
          />
        )}
        <small>TEXTO DE APOIO</small>
        <textarea defaultValue="Um ritual simples ajuda a separar o que importa do que apenas chama." />
        <small>ASSET PRINCIPAL</small>
        <article>
          <img src="/canonical/figma/phase3/s17-visual.png" />
          <span>
            ritual_de_foco_01.jpg<small>Campanha Aurora · Licenciado</small>
          </span>
          <button
            data-action-id="CAROUSEL-REPLACE-ASSET"
            onClick={() =>
              navigate(`/library/assets?returnTo=${encodeURIComponent(pathname)}`)
            }
          >
            Trocar
          </button>
        </article>
        <small>CTA</small>
        <button
          data-action-id="CAROUSEL-SELECT-TOOL"
          onClick={() => {
            setCta((current) =>
              current === "Salve para amanhã"
                ? "Conheça o ritual"
                : "Salve para amanhã",
            );
            setToast("CTA alterado no rascunho atual.");
          }}
        >
          {cta}
        </button>
        <small>CONSISTÊNCIA DA SEQUÊNCIA</small>
        <p className="cx-sequence-check">
          ✓ Tipografia consistente
          <br />✓ Progressão narrativa clara
          <br />! Slide 04 precisa de mais contraste
        </p>
        <StateBanner
          tone="orange"
          title="Sugestão Clicko Intelligence"
          detail="Encurte o título do slide 03 para preservar o ritmo da sequência."
        />
        <button
          data-action-id="CAROUSEL-APPLY-SUGGESTION"
          className="cx-apply-suggestion"
          onClick={() => {
            updateSlides(
              slides.map((headline, index) =>
                index === selected ? "FOCO É ESCOLHA." : headline,
              ),
            );
            setToast("Sugestão aplicada");
          }}
        >
          Aplicar sugestão
        </button>
        <button
          disabled
          title="Ajustes avançados ainda não estão disponíveis neste slice."
        >
          Ajustes avançados
        </button>
      </aside>
      {previewOpen && (
        <div className="cx-carousel-preview-backdrop" role="presentation">
          <section
            className="cx-carousel-set-preview"
            role="dialog"
            aria-modal="true"
            aria-labelledby="carousel-preview-title"
          >
            <header>
              <div>
                <small>PREVIEW CONTÍNUO</small>
                <h2 id="carousel-preview-title">Carrossel completo</h2>
                <p>{slides.length} slides na ordem que será exportada.</p>
              </div>
              <button
                data-action-id="CAROUSEL-CLOSE-PREVIEW"
                onClick={() => setPreviewOpen(false)}
                aria-label="Fechar preview do carrossel"
              >
                <X />
              </button>
            </header>
            <div>
              {slides.map((headline, index) => (
                <button
                  key={`${headline}-preview-${index}`}
                  data-action-id="CAROUSEL-SELECT-PREVIEW-SLIDE"
                  onClick={() => {
                    setSelected(index);
                    setPreviewOpen(false);
                  }}
                  aria-label={`Abrir slide ${index + 1}: ${headline}`}
                >
                  <img src="/canonical/figma/phase3/s17-visual.png" alt="" />
                  <span>{String(index + 1).padStart(2, "0")}</span>
                  <small>{carouselRole(index).toUpperCase()}</small>
                  <strong>{headline}</strong>
                </button>
              ))}
            </div>
          </section>
        </div>
      )}
      {historyOpen && (
        <StudioVersionHistory
          studio={studio}
          onClose={() => setHistoryOpen(false)}
          setToast={setToast}
        />
      )}
    </section>
  );
}

function ContentBoard({ data, demo, navigate }: AnyRecord) {
  const posts = demo ? demoPosts : data.snapshot?.posts || [];
  const [viewMode, setViewMode] = React.useState<"board" | "list">("board");
  const [statusFilter, setStatusFilter] = React.useState<string | null>(null);
  const [query, setQuery] = React.useState("");
  const visiblePosts = posts.filter(
    (post: AnyRecord) =>
      (!statusFilter || post.status === statusFilter) &&
      (!query || post.title?.toLowerCase().includes(query.toLowerCase())),
  );
  return (
    <Page
      eyebrow="Produção"
      title="Conteúdos"
      description="Todas as peças, do primeiro rascunho à publicação."
      actions={
        <Button
          tone="primary"
          icon={Plus}
          actionId="HOME-OPEN-CREATE"
          onClick={() => navigate("/dashboard?create=open")}
        >
          Novo conteúdo
        </Button>
      }
    >
      <div className="cx-toolbar">
        <div className="cx-view-switch">
          <button
            data-action-id="CONTENT-HUB-SELECT-VIEW"
            className={viewMode === "board" ? "is-active" : ""}
            aria-pressed={viewMode === "board"}
            onClick={() => setViewMode("board")}
          >
            <Grid2X2 size={16} />
            Quadro
          </button>
          <button
            data-action-id="CONTENT-HUB-SELECT-VIEW"
            className={viewMode === "list" ? "is-active" : ""}
            aria-pressed={viewMode === "list"}
            onClick={() => setViewMode("list")}
          >
            <LayoutGrid size={16} />
            Lista
          </button>
        </div>
        <button
          data-action-id="CONTENT-HUB-SELECT-FILTER"
          aria-pressed={Boolean(statusFilter)}
          onClick={() =>
            setStatusFilter((current) => (current ? null : "in_review"))
          }
        >
          <ListFilter size={16} />
          {statusFilter ? "Limpar filtro" : "Filtrar revisão"}
        </button>
        <label>
          <Search size={15} />
          <input
            data-action-id="REVIEW-FILTER-CONTENT"
            placeholder="Buscar conteúdo"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </label>
      </div>
      <div className={`cx-board cx-board--${viewMode}`}>
        {[
          ["Ideias", "draft"],
          ["Em produção", "in_review"],
          ["Aprovados", "approved"],
          ["Agendados", "scheduled"],
        ].map(([title, status], col) => (
          <section key={status}>
            <header>
              <b>{title}</b>
              <span>
                {visiblePosts.filter((p: AnyRecord) => p.status === status).length ||
                  [3, 2, 2, 1][col]}
              </span>
              <Plus size={15} />
            </header>
            {visiblePosts
              .filter((p: AnyRecord) => p.status === status)
              .map((p: AnyRecord) => (
                <button
                  data-action-id="CONTENT-HUB-OPEN-ITEM"
                  className="cx-content-card"
                  key={p.id}
                  onClick={() => navigate(`/content/${p.id}`)}
                >
                  {p.imageUrl && <img src={p.imageUrl} alt="" />}
                  <small>
                    {p.platform} · {p.format}
                  </small>
                  <h3>{p.title}</h3>
                  <footer>
                    <Chip>{statusLabel[p.status]}</Chip>
                    <span className="cx-mini-avatar">
                      {p.author?.slice(0, 2) || "EG"}
                    </span>
                  </footer>
                </button>
              ))}
            {!visiblePosts.some((p: AnyRecord) => p.status === status) && (
              <button
                data-action-id="CAMPAIGN-CREATE-PIECE"
                className="cx-ghost-card"
                onClick={() => navigate("/content/draft/edit?mode=visual")}
              >
                <Plus />
                Adicionar peça
              </button>
            )}
          </section>
        ))}
      </div>
    </Page>
  );
}

function EditorSurface({ data, demo, mode, navigate, setToast }: AnyRecord) {
  const [caption, setCaption] = React.useState(
    "O primeiro gole não acorda apenas o corpo. Ele abre espaço para o que importa.",
  );
  const [saved, setSaved] = React.useState("Salvo agora");
  const [activeTool, setActiveTool] = React.useState("Selecionar");
  const [inspectorTab, setInspectorTab] = React.useState("Design");
  const [fontFamily, setFontFamily] = React.useState("Manrope");
  const [fontSize, setFontSize] = React.useState(64);
  const [alignment, setAlignment] = React.useState<"left" | "center" | "right">(
    "center",
  );
  const [carouselPage, setCarouselPage] = React.useState(1);
  const [carouselPages, setCarouselPages] = React.useState(5);
  const visual = mode !== "editorial";
  const carousel = mode === "carousel";
  const save = async () => {
    setSaved("Salvando…");
    const existing = data.snapshot?.posts?.[0];
    const creative = data.snapshot?.creatives?.[0];
    try {
      if (!demo && existing)
        await data.updatePost(existing.id, { copy: caption });
      if (!demo && visual) {
        const document = {
          schemaVersion: "creative-v1" as const,
          width: 1080,
          height: carousel ? 1080 : 1350,
          safeArea: 48,
          background: "#17130f",
          brandTokens: { accent: "#ff6464" },
          layers: [],
        };
        if (creative)
          await data.updateCreative(creative.id, {
            expectedUpdatedAt: creative.updatedAt,
            title: existing?.title || "Peça visual",
            postId: existing?.id || null,
            document,
          });
        else
          await data.createCreative({
            campaignId: existing?.campaignId || null,
            postId: existing?.id || null,
            kind: "document",
            title: existing?.title || "Peça visual",
            document,
          });
      }
      setSaved("Salvo agora");
      setToast(
        demo
          ? "Alteração mantida nesta demonstração"
          : "Alteração sincronizada com o backend",
      );
    } catch {
      setSaved("Erro ao salvar");
    }
  };
  return (
    <div className="cx-editor">
      <div className="cx-editor-top">
        <button
          data-action-id="EDITOR-BACK-CAMPAIGN"
          onClick={() => navigate("/campaigns/active")}
        >
          <ArrowLeft size={17} />
          Ritual Café Aurora
        </button>
        <span>
          {mode === "editorial"
            ? "Post editorial"
            : carousel
              ? "Carrossel"
              : "Post visual"}{" "}
          · <em>{saved}</em>
        </span>
        <div>
          <Button
            actionId="EDITOR-PREVIEW"
            onClick={() => navigate("/approvals/post-ritual?view=creative")}
          >
            Visualizar
          </Button>
          <Button
            tone="primary"
            icon={Send}
            actionId="EDITOR-SEND-REVIEW"
            onClick={async () => {
              await save();
              navigate(
                `/approvals/${data.snapshot?.posts?.[0]?.id || "post-ritual"}?view=creative`,
              );
            }}
          >
            Enviar para revisão
          </Button>
        </div>
      </div>
      <aside className="cx-toolbox">
        {[
          [MousePointer2, "Selecionar"],
          [Type, "Texto"],
          [Image, "Mídia"],
          [Palette, "Marca"],
          [Sparkles, "IA"],
          [Upload, "Upload"],
        ].map(([Icon, label]: any) => (
          <button
            data-action-id="EDITOR-SELECT-TOOL"
            key={label}
            title={label}
            className={activeTool === label ? "is-active" : ""}
            aria-pressed={activeTool === label}
            onClick={() => setActiveTool(label)}
          >
            <Icon size={20} />
            <span>{label}</span>
          </button>
        ))}
      </aside>
      <section className={`cx-canvas ${visual ? "" : "cx-canvas--editorial"}`}>
        {mode === "editorial" ? (
          <article className="cx-document">
            <small>CAFÉ AURORA · EDITORIAL</small>
            <h1>O primeiro gole é um lugar</h1>
            <p className="cx-lead">
              Um manifesto sobre presença, origem e manhãs que começam no
              próprio ritmo.
            </p>
            <img src={demoMedia.pour} alt="Preparo de café filtrado" />
            <textarea
              data-action-id="EDITOR-EDIT-COPY"
              value={caption}
              onChange={(e) => setCaption(e.target.value)}
              onBlur={save}
            />
          </article>
        ) : (
          <div
            className={`cx-artboard ${carousel ? "cx-artboard--carousel" : ""}`}
          >
            <img src={demoMedia.hero} alt="Café sobre mesa de madeira" />
            <span className="cx-artboard-shade" />
            <div>
              <small>CAFÉ AURORA</small>
              <h1>
                {carousel
                  ? "Um ritual em 5 gestos"
                  : "O primeiro gole é um lugar."}
              </h1>
              <p>Presença também se prepara.</p>
            </div>
            {carousel && <b>1 / 5</b>}
          </div>
        )}
      </section>
      <aside className="cx-inspector">
        <div className="cx-inspector-tabs">
          {["Design", "Camadas"].map((item) => (
            <button
              data-action-id="EDITOR-SELECT-PANEL"
              className={inspectorTab === item ? "is-active" : ""}
              aria-pressed={inspectorTab === item}
              onClick={() => setInspectorTab(item)}
              key={item}
            >
              {item}
            </button>
          ))}
        </div>
        <section>
          <small>TEXTO</small>
          <label>
            Conteúdo
            <textarea
              data-action-id="EDITOR-EDIT-COPY"
              value={caption}
              onChange={(e) => setCaption(e.target.value)}
              onBlur={save}
            />
          </label>
          <div className="cx-inline-fields">
            <button
              data-action-id="EDITOR-SET-TYPOGRAPHY"
              onClick={() =>
                setFontFamily((current) =>
                  current === "Manrope" ? "Bricolage Grotesque" : "Manrope",
                )
              }
            >
              {fontFamily}
            </button>
            <button
              data-action-id="EDITOR-SET-TYPOGRAPHY"
              onClick={() =>
                setFontSize((current) => (current === 64 ? 56 : 64))
              }
            >
              {fontSize} px
            </button>
          </div>
        </section>
        <section>
          <small>MARCA</small>
          <div className="cx-color-row">
            <i />
            <i />
            <i />
            <i />
          </div>
        </section>
        <section>
          <small>POSIÇÃO</small>
          <div className="cx-align-row">
            {(["left", "center", "right"] as const).map((item) => (
              <button
                data-action-id="EDITOR-ALIGN-LAYER"
                aria-label={`Alinhar ${item}`}
                aria-pressed={alignment === item}
                className={alignment === item ? "is-active" : ""}
                onClick={() => setAlignment(item)}
                key={item}
              >
                {item === "left" ? "Esquerda" : item === "right" ? "Direita" : "Centro"}
              </button>
            ))}
          </div>
        </section>
        <section className="cx-ai-box">
          <Sparkles />
          <b>Ajustar com IA</b>
          <p>Peça contraste, uma nova hierarquia ou adapte o texto.</p>
          <Button
            icon={Sparkles}
            actionId="EDITOR-OPEN-COPILOT"
            onClick={() => navigate("/copilot?context=editor")}
          >
            Abrir co-piloto
          </Button>
        </section>
      </aside>
      {carousel && (
        <div className="cx-page-strip">
          {Array.from({ length: carouselPages }, (_, index) => index + 1).map((x) => (
            <button
              data-action-id="EDITOR-SELECT-PAGE"
              className={x === carouselPage ? "is-active" : ""}
              aria-pressed={x === carouselPage}
              onClick={() => setCarouselPage(x)}
              key={x}
            >
              <span>{x}</span>
            </button>
          ))}
          <button
            data-action-id="EDITOR-ADD-PAGE"
            aria-label="Adicionar página"
            onClick={() => {
              setCarouselPages((current) => current + 1);
              setCarouselPage(carouselPages + 1);
            }}
          >
            <Plus />
          </button>
        </div>
      )}
    </div>
  );
}

function ApprovedReviewSurface({
  data,
  demo,
  navigate,
  pathname,
  setToast,
}: AnyRecord) {
  const routeId = pathname.split("/")[2];
  const post = demo
    ? demoPosts[0]
    : data.snapshot?.posts?.find((item: AnyRecord) => item.id === routeId);
  const [currentDocument, setCurrentDocument] = React.useState<StudioDocumentRecord>();
  const [studioReview, setStudioReview] = React.useState<StudioReviewRecord>();
  const [reviewError, setReviewError] = React.useState<string>();
  const [previewReady, setPreviewReady] = React.useState(false);
  const [deciding, setDeciding] = React.useState(false);
  const [decisionConflict, setDecisionConflict] = React.useState(false);
  React.useEffect(() => {
    setStudioReview(undefined);
    setCurrentDocument(undefined);
    setReviewError(undefined);
    setDecisionConflict(false);
    setPreviewReady(false);
    if (demo || !studioKernelEnabled || !data.activeWorkspace?.id || !post?.id) return;
    let current = true;
    productApi
      .latestStudioReview(data.activeWorkspace.id, { postId: post.id })
      .then(async (review) => {
        const document = await productApi.studioDocument(review.documentId);
        if (current) { setStudioReview(review); setCurrentDocument(document); }
      })
      .catch((error) => {
        if (current) setReviewError(error instanceof Error ? error.message : "Revisão não encontrada");
      });
    return () => {
      current = false;
    };
  }, [data.activeWorkspace?.id, demo, post?.id]);
  const reviewedDocument = studioReview?.snapshot;
  const [selectedSlide, setSelectedSlide] = React.useState(1);
  const persistedHeadline = studioHeadlines(reviewedDocument)[selectedSlide - 1];
  const currentVersion = `v${studioReview?.documentVersion || reviewedDocument?.version || 3}`;
  const previousVersion = `v${Math.max(1, (studioReview?.documentVersion || reviewedDocument?.version || 3) - 1)}`;
  const [version, setVersion] = React.useState("v3");
  React.useEffect(() => {
    if (studioReview) setVersion(`v${studioReview.documentVersion}`);
    setSelectedSlide(1);
  }, [studioReview]);
  const [comment, setComment] = React.useState("");
  const [decision, setDecision] = React.useState("Decisão");
  const [comparisonMode, setComparisonMode] = React.useState(false);
  const [listenedEntireMix, setListenedEntireMix] = React.useState(false);
  const [listeningChecks, setListeningChecks] = React.useState({
    speechAbsent: "pending",
    musicAbsent: "pending",
    naturalSoundsCoherent: "pending",
    mixBalanced: "pending",
  });
  React.useEffect(() => {
    setListenedEntireMix(false);
    setListeningChecks({
      speechAbsent: "pending",
      musicAbsent: "pending",
      naturalSoundsCoherent: "pending",
      mixBalanced: "pending",
    });
  }, [studioReview?.id]);
  const listeningRequired = Boolean(reviewedDocument && ["video", "presenter"].includes(reviewedDocument.contentType) && (
    reviewedDocument.composition.narrative.naturalSoundPolicy === "required-before-approval"
    || reviewedDocument.composition.narrative.voicePolicy === "prohibited"
    || reviewedDocument.composition.narrative.audioMode === "natural-foley-only"
  ));
  const [acousticCapability, setAcousticCapability] = React.useState<StudioAcousticAnalysisCapability>();
  const [acousticJob, setAcousticJob] = React.useState<StudioGenerationJobRecord>();
  const [acousticError, setAcousticError] = React.useState<string>();
  React.useEffect(() => {
    setAcousticCapability(undefined);
    setAcousticJob(undefined);
    setAcousticError(undefined);
    if (demo || !listeningRequired || !studioReview?.id) return;
    let active = true;
    void productApi.studioAcousticAnalysisCapability(studioReview.id)
      .then((capability) => { if (active) setAcousticCapability(capability); })
      .catch((error) => {
        if (active) setAcousticError(error instanceof Error ? error.message : "Não foi possível consultar o detector.");
      });
    return () => { active = false; };
  }, [demo, listeningRequired, studioReview?.id]);
  React.useEffect(() => {
    if (!acousticJob || !["queued", "running", "retrying"].includes(acousticJob.status)) return;
    const timer = window.setTimeout(() => {
      void productApi.studioGenerationJob(acousticJob.id)
        .then(async (job) => {
          setAcousticJob(job);
          if (job.status === "succeeded" && studioReview && data.activeWorkspace?.id) {
            const refreshed = await productApi.latestStudioReview(data.activeWorkspace.id, {
              documentId: studioReview.documentId,
            });
            setStudioReview(refreshed);
          }
        })
        .catch((error) => setAcousticError(
          error instanceof Error ? error.message : "Não foi possível atualizar a análise.",
        ));
    }, 900);
    return () => window.clearTimeout(timer);
  }, [acousticJob, data.activeWorkspace?.id, studioReview]);
  const runAcousticAnalysis = async () => {
    if (!studioReview || acousticCapability?.status !== "ready" || ["queued", "running", "retrying"].includes(acousticJob?.status || "")) return;
    setAcousticError(undefined);
    try {
      const job = await productApi.enqueueStudioAcousticAnalysis(
        studioReview.id,
        `review-acoustic-${studioReview.id}-${crypto.randomUUID()}`,
      );
      setAcousticJob(job);
      setToast("Análise do MP4 iniciada");
    } catch (error) {
      const detail = error instanceof BackendRequestError
        ? error.detail as { detail?: { code?: string } }
        : undefined;
      const code = detail?.detail?.code;
      setAcousticError(
        code === "acoustic_detector_not_approved"
          ? "Nenhum detector foi aprovado para produção."
          : "A análise não pôde ser iniciada; nenhuma evidência foi registrada.",
      );
    }
  };
  const listeningComplete = listenedEntireMix && Object.values(listeningChecks).every((value) => value !== "pending");
  const listeningPassed = listeningComplete && Object.values(listeningChecks).every((value) => value === "pass");
  const listeningSubmission = (): StudioListeningReviewSubmission | undefined => {
    if (!listeningComplete || !studioReview?.renderAssetId || !studioReview.renderChecksumSha256) return undefined;
    return {
      renderAssetId: studioReview.renderAssetId,
      renderChecksumSha256: studioReview.renderChecksumSha256,
      listenedEntireMix: true,
      speechAbsent: listeningChecks.speechAbsent as "pass" | "fail" | "inconclusive",
      musicAbsent: listeningChecks.musicAbsent as "pass" | "fail" | "inconclusive",
      naturalSoundsCoherent: listeningChecks.naturalSoundsCoherent as "pass" | "fail" | "inconclusive",
      mixBalanced: listeningChecks.mixBalanced as "pass" | "fail" | "inconclusive",
    };
  };
  const stale = !demo && Boolean(studioReview && currentDocument && (
    currentDocument.version !== studioReview.documentVersion || currentDocument.review.approvalId !== studioReview.id
  ));
  const decisionBlocked = !demo && (!previewReady || stale || decisionConflict || !currentDocument || studioReview?.status !== "requested");
  const approvalBlocked = decisionBlocked || (!demo && listeningRequired && !listeningPassed);
  const decisionReason = deciding ? "Salvando decisão…" : stale || decisionConflict ? "O documento mudou. Envie a versão atual pelo Studio para nova revisão." : !previewReady ? "Carregue a mídia da versão fixada antes de decidir." : "Esta revisão já foi decidida ou ainda não está disponível.";
  const approvalReason = !decisionBlocked && listeningRequired && !listeningPassed
    ? "Ouça o MP4 fixado e aprove todos os critérios de som antes da aprovação criativa."
    : decisionReason;
  const decide = async (action: "approve" | "request_changes" | "reject") => {
    if (deciding || decisionBlocked || (action === "approve" && approvalBlocked)) return;
    if (action === "request_changes" && !comment.trim()) {
      setToast("Escreva o comentário obrigatório para solicitar ajustes");
      return;
    }
    setDeciding(true);
    try {
      if (!demo && studioReview) {
        const decided = await productApi.decideStudioReview(
          studioReview.id,
          action,
          comment || undefined,
          action === "reject" ? undefined : listeningSubmission(),
        );
        setStudioReview(decided);
      }
      setToast(
        action === "approve"
          ? "Versão aprovada"
          : action === "reject"
            ? "Versão rejeitada"
            : "Ajustes solicitados",
      );
      if (action === "approve") navigate(`/publish/${routeId}`);
    } catch (error) {
      if (error instanceof BackendRequestError && error.status === 409) {
        const detail = error.detail as { detail?: { code?: string } } | undefined;
        const code = detail?.detail?.code;
        if (["studio_publication_render_changed", "studio_review_listening_render_mismatch"].includes(code || "")) {
          setDecisionConflict(true);
          setToast("O MP4 fixado mudou ou não corresponde à escuta. Gere uma nova prova e envie outra revisão.");
        } else if (["studio_review_listening_required", "studio_review_listening_failed"].includes(code || "")) {
          setToast("Conclua a escuta e deixe todos os critérios aprovados antes de aprovar esta versão.");
        } else {
          setDecisionConflict(true);
          setToast("A revisão mudou ou já foi decidida. Reabra a revisão ou envie a versão atual pelo Studio.");
        }
      } else setToast("A decisão não pôde ser salva. Tente novamente; nenhuma aprovação foi confirmada.");
    } finally {
      setDeciding(false);
    }
  };
  return (
    <section className="cx-review-approved">
      <header>
        <button
          data-action-id="REVIEW-BACK-CAMPAIGN"
          onClick={() =>
            navigate(post?.campaignId ? `/campaigns/${post.campaignId}` : demo ? "/campaigns/campaign-aurora" : "/content")
          }
        >
          {demo || post?.campaignId ? "← Campaign Room" : "← Voltar à produção"}
        </button>
        <b>{post?.title || "Carrossel editorial · O Brasil cabe em uma xícara"}</b>
        <Chip>{demo || studioReview ? version : "Sem versão fixada"}</Chip>
        <span>{demo ? "Em revisão" : studioReview?.status === "approved" ? "Aprovada" : studioReview?.status === "rejected" ? "Rejeitada" : studioReview?.status === "changes_requested" ? "Ajustes solicitados" : studioReview ? "Em revisão" : "Carregando revisão"}</span>
        <span>{demo ? "Hoje, 18h" : studioReview ? new Date(studioReview.requestedAt).toLocaleString("pt-BR") : ""}</span>
        <div />
        <Button
          actionId="REVIEW-EDIT"
          onClick={() => navigate(`/content/${routeId}/edit?mode=${reviewedDocument?.contentType === "carousel" ? "carousel" : reviewedDocument?.contentType === "video" ? "video" : "visual"}`)}
        >
          Editar
        </Button>
        <Button
          actionId="REVIEW-OPEN-REUSE"
          onClick={() => navigate(`/content/${routeId}/remix`)}
        >
          Criar variação
        </Button>
        <Button
          actionId="REVIEW-COMPARE-VERSIONS"
          disabled={!demo}
          title={!demo ? "Abra o histórico no Studio para comparar versões carregadas." : undefined}
          onClick={() =>
            setVersion(
              version === currentVersion ? previousVersion : currentVersion,
            )
          }
        >
          Comparar versões
        </Button>
      </header>
      <main>
        {(stale || decisionConflict) && <StateBanner tone="orange" title="Esta revisão não pode aprovar o documento atual" detail="O snapshot abaixo continua preservado. Use Editar e Enviar para revisão no Studio para fixar a nova versão." />}
        {reviewError && !demo && (
          <StateBanner
            tone="orange"
            title="Nenhuma versão fixada para revisão"
            detail="Volte ao Studio e use Enviar para revisão para criar um snapshot imutável."
          />
        )}
        <section className="cx-review-preview-approved">
          <div className="cx-review-version">
            <button
              data-action-id="REVIEW-SELECT-VERSION"
              className={version === currentVersion ? "is-active" : ""}
              onClick={() => setVersion(currentVersion)}
            >
              {demo ? "Versão atual" : "Versão fixada"}　 <b>{studioReview || demo ? currentVersion : "—"}</b>
            </button>
            <button
              data-action-id="REVIEW-SELECT-VERSION"
              disabled={!demo}
              title={
                !demo
                  ? "A comparação anterior fica disponível após carregar as duas versões."
                  : undefined
              }
              onClick={() => setVersion(previousVersion)}
            >
              {demo ? `Versão anterior　 ${previousVersion}` : "Anterior indisponível"}
            </button>
            <button
              data-action-id="REVIEW-COMPARE-VERSIONS"
              disabled={!demo}
              title={!demo ? "Comparação disponível no histórico do Studio; esta tela mostra somente o snapshot fixado." : undefined}
              aria-pressed={comparisonMode}
              onClick={() => setComparisonMode((current) => !current)}
            >
              {comparisonMode ? "Comparação ativa" : "Comparar lado a lado"}
            </button>
          </div>
          {demo ? <img src={phase3Arts[0]} alt={`Peça ${version} em revisão`} /> : studioReview ? <ReviewSnapshotPreview review={studioReview} pageId={reviewedDocument?.composition.pages[selectedSlide - 1]?.id} onReady={setPreviewReady} /> : <p role="status">{reviewError ? "Sem mídia fixada para exibir." : "Carregando a versão fixada…"}</p>}
          <div className="cx-review-zoom">{demo ? "Menos　82%　Mais" : "Ajustado ao espaço disponível"}</div>
          <div className="cx-review-thumbs" data-comparison={comparisonMode}>
            {(demo ? [1, 2, 3, 4, 5, 6] : reviewedDocument?.composition.pages.map((_, i) => i + 1) ?? []).map((i) => (
              <button
                data-action-id="REVIEW-SELECT-SLIDE"
                className={i === selectedSlide ? "is-active" : ""}
                aria-pressed={i === selectedSlide}
                aria-label={`Revisar slide ${i}`}
                onClick={() => { if (i !== selectedSlide) setPreviewReady(false); setSelectedSlide(i); }}
                key={i}
              >
                {demo ? <img src={i === 6 ? phase3Arts[3] : phase3Arts[0]} alt="" /> : <p>{studioHeadlines(reviewedDocument)[i - 1]}</p>}
                <span>{i}</span>
              </button>
            ))}
            <button
              className="cx-add-slide"
              disabled
              title="A revisão trabalha sobre uma versão fixada; volte ao Studio para adicionar slides."
            >
              <Plus />
              Adicionar slide
            </button>
          </div>
          <footer>
            <p>
              {post?.title || "Festival Brasileiro de Cafés Especiais"}　→　
              <strong data-testid="review-studio-headline">
                {persistedHeadline || (demo ? "O Brasil cabe em uma xícara" : "Sem texto nesta página")}
              </strong>
              　→　Peça {version}
            </p>
            <div>
              {(demo ? [
                "Produtores creditados",
                "Sem alegação de premiação",
                "Contraste aprovado",
              ] : ["Conteúdo do snapshot", "Fontes sob revisão humana", "Sem garantia automática de qualidade"]).map((x) => (
                <span key={x}>
                  {x}
                  {demo && <Check />}
                </span>
              ))}
            </div>
          </footer>
        </section>
        <aside className="cx-review-decision">
          <nav>
            {["Decisão", demo ? "Comentários · 3" : "Observação", demo ? "Versões · 3" : "Versão fixada", "Contexto"].map(
              (x) => (
                <button
                  data-action-id="REVIEW-SELECT-PANEL"
                  className={decision === x ? "is-active" : ""}
                  onClick={() => setDecision(x)}
                  key={x}
                >
                  {x}
                </button>
              ),
            )}
          </nav>
          {decision === "Decisão" ? (
            <>
              <h2>Esta versão está pronta?</h2>
              <div className="cx-review-people">
                <KeyValue label="Revisão por" value={demo ? "JO　João" : studioReview?.decidedBy || "Decisão pendente"} />
                <KeyValue label="Solicitante" value={demo ? "MA　Mariana" : studioReview?.requestedBy || "Não informado"} />
              </div>
              <p>{demo ? "Hook e composição ajustados na v3. CTA preservado." : "Avalie a mídia fixada, a oferta e as alegações. Aprovar não publica o conteúdo."}</p>
              {!demo && listeningRequired && studioReview && (
                studioReview.listeningReview ? (
                  <section className="cx-listening-review" data-result={studioReview.listeningReview.result}>
                    <h3>Escuta do MP4 fixado</h3>
                    <p>
                      {studioReview.listeningReview.result === "pass" ? "Mix aprovado na escuta humana." : "Escuta registrada com necessidade de ajustes."}
                    </p>
                    <small>Arquivo {studioReview.renderChecksumSha256?.slice(0, 12)} · versão v{studioReview.documentVersion} · publicação ainda bloqueada até direitos e análise automática.</small>
                  </section>
                ) : (
                  <fieldset className="cx-listening-review" disabled={deciding || decisionBlocked}>
                    <legend>Escuta do MP4 fixado</legend>
                    <p>Reproduza o vídeo com som. Avalie somente o mix natural e a legenda; voz e música não fazem parte desta versão.</p>
                    <label className="cx-listening-attestation">
                      <input
                        type="checkbox"
                        data-action-id="REVIEW-EDIT-LISTENING-ASSESSMENT"
                        checked={listenedEntireMix}
                        onChange={(event) => setListenedEntireMix(event.target.checked)}
                      />
                      Ouvi o mix inteiro deste MP4
                    </label>
                    {([
                      ["speechAbsent", "Fala ou narração incidental", "Não detectei fala", "Detectei fala"],
                      ["musicAbsent", "Música incidental", "Não detectei música", "Detectei música"],
                      ["naturalSoundsCoherent", "Coerência dos sons naturais", "Coerentes com a ação", "Descompassados ou artificiais"],
                      ["mixBalanced", "Equilíbrio do mix", "Volume e transições adequados", "Volume ou transições inadequados"],
                    ] as const).map(([key, label, passLabel, failLabel]) => (
                      <label key={key}>
                        {label}
                        <select
                          data-action-id="REVIEW-EDIT-LISTENING-ASSESSMENT"
                          value={listeningChecks[key]}
                          onChange={(event) => setListeningChecks((current) => ({ ...current, [key]: event.target.value }))}
                        >
                          <option value="pending">Selecione</option>
                          <option value="pass">{passLabel}</option>
                          <option value="fail">{failLabel}</option>
                          <option value="inconclusive">Não consegui concluir</option>
                        </select>
                      </label>
                    ))}
                    <small>Este registro fica vinculado ao hash do MP4 e à versão. Ele não comprova licença nem substitui a análise de fala e música.</small>
                  </fieldset>
                )
              )}
              {!demo && listeningRequired && studioReview && (
                <section
                  className="cx-acoustic-analysis"
                  data-status={studioReview.naturalSoundAdmission ? "admitted" : studioReview.acousticAnalysis?.status || acousticCapability?.status || "loading"}
                >
                  <h3>Análise automática do MP4</h3>
                  {studioReview.naturalSoundAdmission ? (
                    <>
                      <p>Fala e música ausentes no arquivo admitido para entrega.</p>
                      <small>
                        Evidência {studioReview.naturalSoundAdmission.acousticAnalysisId.slice(0, 8)} ·
                        escuta {studioReview.naturalSoundAdmission.listeningAssessmentId.slice(0, 8)} ·
                        arquivo {studioReview.renderChecksumSha256?.slice(0, 12)}
                      </small>
                    </>
                  ) : studioReview.acousticAnalysis ? (
                    <>
                      <p>
                        {studioReview.acousticAnalysis.status === "pass"
                          ? "O detector qualificado não encontrou fala nem música. A entrega ainda exige direitos e escuta no mesmo arquivo."
                          : studioReview.acousticAnalysis.status === "fail"
                            ? "O detector encontrou fala ou música. Este MP4 não pode ser entregue neste perfil."
                            : "O detector não conseguiu concluir. Gere outra prova ou encaminhe para investigação."}
                      </p>
                      <small>
                        {studioReview.acousticAnalysis.result.provider} · modelo {studioReview.acousticAnalysis.modelDigestSha256.slice(0, 12)} · arquivo {studioReview.acousticAnalysis.renderChecksumSha256.slice(0, 12)}
                      </small>
                    </>
                  ) : (
                    <>
                      <p role={acousticError ? "alert" : "status"}>
                        {acousticError || acousticCapability?.detail || "Consultando detector aprovado…"}
                      </p>
                      <Button
                        actionId="REVIEW-RUN-ACOUSTIC-ANALYSIS"
                        disabled={acousticCapability?.status !== "ready" || ["queued", "running", "retrying"].includes(acousticJob?.status || "")}
                        title={acousticCapability?.status !== "ready" ? acousticCapability?.detail : undefined}
                        onClick={() => void runAcousticAnalysis()}
                      >
                        {["queued", "running", "retrying"].includes(acousticJob?.status || "")
                          ? `Analisando MP4 · ${acousticJob?.progress || 0}%`
                          : "Analisar fala e música"}
                      </Button>
                      <small>A análise usa somente o MP4 fixado. O script YAMNet/VAD de pesquisa não é aceito neste gate.</small>
                    </>
                  )}
                </section>
              )}
              <Button
                tone="primary"
                actionId="REVIEW-APPROVE"
                disabled={deciding || approvalBlocked}
                title={deciding || approvalBlocked ? approvalReason : undefined}
                onClick={() => void decide("approve")}
              >
                Aprovar esta versão　→
              </Button>
              <Button
                actionId="REVIEW-REQUEST-CHANGES"
                disabled={deciding || decisionBlocked}
                title={deciding || decisionBlocked ? decisionReason : undefined}
                onClick={() => void decide("request_changes")}
              >
                Solicitar ajustes　→
              </Button>
              <Button
                actionId="REVIEW-REJECT"
                disabled={deciding || decisionBlocked}
                title={deciding || decisionBlocked ? decisionReason : undefined}
                onClick={() => void decide("reject")}
              >
                Rejeitar　→
              </Button>
              <label>
                Comentário da decisão
                <textarea
                  data-action-id="REVIEW-EDIT-COMMENT"
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  placeholder="Explique o que deve mudar ou por que está aprovado."
                />
                <small>Comentário obrigatório para solicitar ajustes.</small>
              </label>
              {demo ? <div className="cx-review-comments">
                <p>
                  <b>MA　Mariana · 14:32</b>
                  <br />
                  Reduzi o texto do slide 3 e reforcei a origem.
                </p>
                <p>
                  <b>JO　João · 15:10</b>
                  <br />A composição ficou mais clara.
                </p>
              </div> : <p>{studioReview?.decisionComment || "Nenhuma observação registrada nesta revisão."}</p>}
              <h3>Evidência de performance ⓘ</h3>
              <div className="cx-no-evidence">
                ⊕ Sem evidência de performance para esta decisão.
              </div>
              <h3>Contexto rápido</h3>
              {[
                [
                  "Campanha",
                  data.snapshot?.campaigns?.find(
                    (campaign: AnyRecord) => campaign.id === post?.campaignId,
                  )?.name || "Sem campanha vinculada",
                ],
                ["Objetivo", post?.objective || reviewedDocument?.brief.objective || "Não informado"],
                ["Público", reviewedDocument?.brief.audience || "Não informado"],
                ["Brand Memory", `v${reviewedDocument?.brandMemoryRef.revision || 1}`],
              ].map(([a, b]) => (
                <KeyValue label={a} value={b} key={a} />
              ))}
            </>
          ) : (
            <div className="cx-review-tab-state">
              <h2>{decision}</h2>
              <p>
                {!demo ? decision === "Observação" ? studioReview?.decisionComment || "Nenhuma observação registrada." : decision === "Versão fixada" ? `Snapshot ${studioReview ? `v${studioReview.documentVersion}, revisão ${studioReview.snapshot.revision}` : "ainda não carregado"}. Consulte o histórico no Studio para outras versões.` : reviewedDocument ? `${reviewedDocument.brief.objective} — ${reviewedDocument.brief.audience}` : "Contexto não carregado." : decision.startsWith("Comentários")
                  ? "3 comentários contextuais registrados nesta versão."
                  : decision.startsWith("Versões")
                    ? "v3 atual · v2 anterior · v1 arquivada."
                    : "Campanha, oportunidade, público e memória permanecem aplicados."}
              </p>
            </div>
          )}
        </aside>
      </main>
    </section>
  );
}

function ApprovalSurface({ data, demo, navigate, setToast }: AnyRecord) {
  const post = demo ? demoPosts[0] : data.snapshot?.posts?.[0];
  const [zoom, setZoom] = React.useState(72);
  const [comment, setComment] = React.useState("");
  const decide = async (action: "approve" | "request_changes") => {
    try {
      if (!demo && post)
        await data.decidePost(post.id, {
          action,
          comment:
            action === "approve"
              ? "Direção aprovada na revisão canônica."
              : "Ajustar contraste do título.",
        });
      setToast(action === "approve" ? "Peça aprovada" : "Ajustes enviados");
      if (action === "approve") navigate("/calendar");
    } catch {
      setToast("A decisão não pôde ser salva");
    }
  };
  return (
    <div className="cx-review">
      <header>
        <button
          data-action-id="CONTENT-BACK-INVENTORY"
          onClick={() => navigate("/content")}
        >
          <ArrowLeft />
          Voltar à produção
        </button>
        <div>
          <b>{post?.title || "O primeiro gole"}</b>
          <span>Versão 4 · criada há 18 min</span>
        </div>
        <Button icon={MoreHorizontal} />
      </header>
      <main>
        <div className="cx-review-art">
          <div className="cx-review-artboard">
            <img
              src={post?.imageUrl || demoMedia.hero}
              alt="Peça criativa em revisão"
            />
            <span />
            <h1>O primeiro gole é um lugar.</h1>
            <i className="cx-pin">1</i>
          </div>
          <div className="cx-review-controls">
            <button
              data-action-id="REVIEW-SET-ZOOM"
              aria-label="Reduzir zoom"
              onClick={() => setZoom((current) => Math.max(40, current - 8))}
            >
              Menos
            </button>
            <span>{zoom}%</span>
            <button
              data-action-id="REVIEW-SET-ZOOM"
              aria-label="Aumentar zoom"
              onClick={() => setZoom((current) => Math.min(160, current + 8))}
            >
              Mais
            </button>
            <button data-action-id="REVIEW-SET-ZOOM" onClick={() => setZoom(72)}>
              Ajustar
            </button>
          </div>
        </div>
        <aside>
          <div className="cx-review-title">
            <div>
              <Chip tone="orange">Revisão criativa</Chip>
              <h2>Comentários</h2>
            </div>
            <Users size={19} />
          </div>
          <div className="cx-thread">
            <article>
              <span>MA</span>
              <div>
                <b>
                  Marina Alves <small>há 12 min</small>
                </b>
                <p>Podemos ganhar um pouco mais de contraste no título?</p>
                <button
                  data-action-id="REVIEW-REPLY"
                  onClick={() => setComment("@Marina ")}
                >
                  Responder
                </button>
              </div>
            </article>
            <article>
              <span>EG</span>
              <div>
                <b>
                  Edu Gomes <small>agora</small>
                </b>
                <p>
                  Ajustado nesta versão. Também preservei a textura do fundo.
                </p>
              </div>
            </article>
          </div>
          <label className="cx-comment-box">
            <textarea
              data-action-id="REVIEW-EDIT-COMMENT"
              placeholder="Deixe um comentário…"
              value={comment}
              onChange={(event) => setComment(event.target.value)}
            />
            <footer>
              <button
                disabled
                title="Anexos serão liberados quando o armazenamento de revisão estiver ativo."
              >
                <Link2 />
              </button>
              <Button
                tone="primary"
                icon={Send}
                actionId="REVIEW-ADD-COMMENT"
                disabled={!comment.trim()}
                title={!comment.trim() ? "Escreva um comentário antes de enviar." : undefined}
                onClick={() => {
                  setToast("Comentário registrado nesta sessão de revisão.");
                  setComment("");
                }}
              >
                Comentar
              </Button>
            </footer>
          </label>
          <div className="cx-review-actions">
            <Button
              actionId="REVIEW-REQUEST-CHANGES"
              onClick={() => void decide("request_changes")}
            >
              Solicitar ajustes
            </Button>
            <Button
              tone="primary"
              icon={Check}
              actionId="REVIEW-APPROVE"
              onClick={() => void decide("approve")}
            >
              Aprovar peça
            </Button>
          </div>
        </aside>
      </main>
    </div>
  );
}

function ApprovedCalendarSurface({ navigate }: AnyRecord) {
  const [selected, setSelected] = React.useState(1);
  const [range, setRange] = React.useState("Semana");
  const [moved, setMoved] = React.useState(false);
  const [detailOpen, setDetailOpen] = React.useState(true);
  const days = [
    "SEG\n20 mai",
    "TER\n21 mai",
    "QUA\n22 mai",
    "QUI\n23 mai",
    "SEX\n24 mai",
    "SÁB\n25 mai",
    "DOM\n26 mai",
  ];
  const cards = [
    ["Stories", "Semana das origens", phase3Arts[1], "Publicado"],
    ["Carrossel", "O Brasil cabe em uma xícara", phase3Arts[0], "Aprovado"],
    ["Carrossel", "Do Cerrado à xícara", phase3Arts[1], "Agendado"],
    ["Post", "Kit Degustação", phase3Arts[3], "Aprovado"],
    ["UGC", "Quatro origens em casa", phase3Arts[0], "Em revisão"],
  ];
  return (
    <section className="cx-calendar-approved">
      <header>
        <div>
          <small>Projetos　/　O Brasil cabe em uma xícara</small>
          <h1>Calendário editorial</h1>
          <p>Cadência, qualidade e saída da sua produção de conteúdo.</p>
        </div>
        <Button
          tone="primary"
          icon={CalendarDays}
          actionId="CALENDAR-CREATE-CONTENT"
          onClick={() => navigate("/dashboard?create=open")}
        >
          Agendar conteúdo
        </Button>
        <Button
          icon={Sparkles}
          actionId="CAMPAIGN-OPEN-WORLD"
          onClick={() => navigate("/campaigns/campaign-aurora/world")}
        >
          Explorar direção
        </Button>
      </header>
      <div className="cx-calendar-controls">
        <nav>
          {["Semana", "Mês", "Trimestre"].map((x) => (
            <button
              data-action-id="CALENDAR-SELECT-FILTER"
              className={range === x ? "is-active" : ""}
              onClick={() => setRange(x)}
              key={x}
            >
              {x}
            </button>
          ))}
        </nav>
        <Button>Campanha　O Brasil cabe em uma xícara</Button>
        <Button>Canal　Todos</Button>
        <Button>Status　Todos</Button>
        <Button>‹　20 – 26 mai　›</Button>
      </div>
      <div className="cx-calendar-rhythm">
        <b>Ritmo da semana</b>
        <span>▦ 8　 peças na linha</span>
        <span>○ 2　 lacunas</span>
        <span>△ 1　 conflito</span>
        <span>✓ 3　 prontas para sair</span>
      </div>
      <div className="cx-calendar-approved-layout">
        <main>
          <div className="cx-calendar-week">
            {days.map((day, i) => (
              <section className={i === 3 ? "is-today" : ""} key={day}>
                <header>
                  {day.split("\n").map((x) => (
                    <span key={x}>{x}</span>
                  ))}
                </header>
                {i < 5 ? (
                  <button
                    data-action-id="CALENDAR-SELECT-ITEM"
                    className={selected === i ? "is-selected" : ""}
                    onClick={() => {
                      setSelected(i);
                      setDetailOpen(true);
                    }}
                  >
                    <small>{cards[i][0]}</small>
                    <b>{cards[i][1]}</b>
                    <img src={cards[i][2]} />
                    <span>
                      10:30
                      <br />
                      <i>●</i> {cards[i][3]}
                    </span>
                  </button>
                ) : i === 5 ? (
                  <div className="cx-calendar-conflict">
                    <b>△ CONFLITO</b>
                    {[
                      ["Reels", "Ritual do Café Aurora", phase3Arts[0]],
                      ["Stories", "Bastidores da torra", phase3Arts[2]],
                    ].map((x) => (
                      <button
                        data-action-id="CALENDAR-SELECT-ITEM"
                        onClick={() => {
                          setSelected(1);
                          setDetailOpen(true);
                        }}
                        key={x[1]}
                      >
                        <small>{x[0]}</small>
                        <b>{x[1]}</b>
                        <img src={x[2]} />
                        <span>10:00　△ Conflito</span>
                      </button>
                    ))}
                  </div>
                ) : (
                  <div className="cx-calendar-gap">
                    <span>▣</span>
                    <p>Lacuna identificada</p>
                    <Button
                      tone="primary"
                      actionId="CALENDAR-CREATE-CONTENT"
                      onClick={() => navigate("/dashboard?create=open")}
                    >
                      Criar para esta lacuna
                    </Button>
                  </div>
                )}
                {i === 3 && (
                  <button
                    className="cx-add-calendar"
                    data-action-id="CALENDAR-CREATE-CONTENT"
                    onClick={() => navigate("/dashboard?create=open")}
                  >
                    ⊕<br />
                    Adicionar peça
                  </button>
                )}
              </section>
            ))}
          </div>
          <footer>
            {[
              "✓ Publicado",
              "⊙ Agendado",
              "● Em revisão",
              "✓ Aprovado",
              "△ Conflito",
              "○ Lacuna",
              "Arraste para reagendar",
            ].map((x) => (
              <span key={x}>{x}</span>
            ))}
          </footer>
        </main>
        {detailOpen && <aside>
          <header>
            <h2>O Brasil cabe em uma xícara</h2>
            <button
              data-action-id="CALENDAR-CLOSE-DETAIL"
              aria-label="Fechar detalhes"
              onClick={() => setDetailOpen(false)}
            >
              Fechar
            </button>
          </header>
          <Chip tone="green">✓ Aprovado　⌄</Chip>
          <img src={cards[selected]?.[2] || phase3Arts[0]} />
          {[
            ["Campanha", "O Brasil cabe em uma xícara"],
            ["Responsável", "● Mariana"],
            ["Canal", "◎ Instagram"],
            ["Formato", "▦ Carrossel"],
            ["Agendamento", "▣ Ter, 21 mai · 10:30"],
          ].map(([a, b]) => (
            <KeyValue label={a} value={b} key={a} />
          ))}
          <h3>Pré-flight</h3>
          <div className="cx-preflight">
            {["Conteúdo aprovado", "Asset disponível", "Horário futuro"].map(
              (x) => (
                <p key={x}>
                  ✓ {x}
                  <span>›</span>
                </p>
              ),
            )}
            <p className="is-warning">
              △ Canal ainda requer confirmação<span>›</span>
            </p>
          </div>
          <Button
            tone="primary"
            actionId="CALENDAR-OPEN-PUBLISHER"
            onClick={() => navigate("/publish/post-ritual")}
          >
            Abrir Publisher Control
          </Button>
          <Button actionId="CALENDAR-RESCHEDULE" onClick={() => setMoved(!moved)}>
            {moved ? "Reagendado" : "Reagendar"}
          </Button>
          <Button
            actionId="CALENDAR-OPEN-CONTENT"
            onClick={() => navigate("/content/post-ritual")}
          >
            Abrir peça <ArrowRight size={15} aria-hidden="true" />
          </Button>
          <StateBanner
            tone="orange"
            title="O agendamento interno não confirma publicação na rede."
          />
          <small>Campanha　›　Carrossel v3　›　Calendário</small>
        </aside>}
      </div>
    </section>
  );
}

function nextScheduleInputValue() {
  const date = new Date(Date.now() + 24 * 60 * 60 * 1000);
  date.setMinutes(0, 0, 0);
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 16);
}

function downloadBrowserBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 0);
}

function publicationPreflightError(error: unknown) {
  const code = error instanceof Error ? error.message : "";
  if (code.includes("natural_sound_evidence_pending")) return "O mix de sons naturais ainda não foi validado. Direitos, ausência de voz e música e escuta humana devem estar vinculados ao vídeo final antes da entrega.";
  if (code.includes("acoustic_promotion_revoked")) return "O detector ou modelo usado nesta análise foi revogado. A entrega permanece bloqueada até uma nova análise com runtime aprovado.";
  if (code.includes("natural_sound_rights_changed")) return "Os direitos de um som expiraram ou mudaram depois da análise. Renove a autorização e envie uma nova versão para revisão.";
  if (code.includes("copy_changed")) return "A legenda ou os metadados mudaram depois da aprovação. Envie a versão atual para uma nova revisão.";
  if (code.includes("snapshot_stale")) return "O documento mudou depois da aprovação. Envie a versão atual para uma nova revisão.";
  if (code.includes("rights_restricted")) return "Há um asset com uso restrito. Regularize os direitos antes de preparar a saída.";
  if (code.includes("handoff_missing")) return "Esta revisão é anterior ao vínculo verificável de legenda. Envie a versão atual para uma nova revisão.";
  if (code.includes("not_approved")) return "A versão atual ainda não está aprovada para saída.";
  if (code.includes("source") || code.includes("render")) return "Um arquivo aprovado não está mais disponível ou não corresponde ao checksum revisado.";
  return "O pré-flight não pôde ser validado. Reabra a revisão e confira a versão aprovada.";
}

function AuthenticatedApprovedPublisherSurface({ data, navigate, pathname, setToast }: AnyRecord) {
  const postId = pathname.split("/")[2];
  const [review, setReview] = React.useState<StudioReviewRecord>();
  const [preflight, setPreflight] = React.useState<StudioPublicationPreflightRecord>();
  const [error, setError] = React.useState<string>();
  const [loading, setLoading] = React.useState(true);
  const [busy, setBusy] = React.useState<"schedule" | "package">();
  const [copied, setCopied] = React.useState(false);
  const [previewTab, setPreviewTab] = React.useState("Visual");
  const [selectedCheck, setSelectedCheck] = React.useState(0);
  const [slide, setSlide] = React.useState(0);
  const [previewReady, setPreviewReady] = React.useState(false);
  const [scheduleValue, setScheduleValue] = React.useState(nextScheduleInputValue);

  const load = React.useCallback(async () => {
    if (!data.activeWorkspace?.id || !postId) return;
    setLoading(true);
    setError(undefined);
    try {
      const latest = await productApi.latestStudioReview(data.activeWorkspace.id, { postId });
      if (latest.status !== "approved") throw new Error("A versão mais recente ainda não foi aprovada.");
      const result = await productApi.studioPublicationPreflight(latest.id);
      setReview(latest);
      setPreflight(result);
      setSlide(0);
      if (result.scheduledAt) {
        const scheduled = new Date(result.scheduledAt);
        const local = new Date(scheduled.getTime() - scheduled.getTimezoneOffset() * 60_000);
        setScheduleValue(local.toISOString().slice(0, 16));
      }
    } catch (requestError) {
      setReview(undefined);
      setPreflight(undefined);
      setError(publicationPreflightError(requestError));
    } finally {
      setLoading(false);
    }
  }, [data.activeWorkspace?.id, postId]);

  React.useEffect(() => { void load(); }, [load]);
  React.useEffect(() => { setPreviewReady(false); }, [review?.id, slide]);

  const approvedCaption = preflight
    ? `${preflight.caption}${preflight.hashtags.length ? `\n\n${preflight.hashtags.join(" ")}` : ""}`
    : "";
  const downloadPackage = async () => {
    if (!review || busy) return;
    setBusy("package");
    try {
      const blob = await productApi.studioPublicationPackageBlob(review.id);
      downloadBrowserBlob(blob, `clicko-${postId}-v${review.documentVersion}.zip`);
      setToast("Pacote aprovado baixado");
    } catch {
      setToast("O pacote não foi gerado. Revalide a versão e os arquivos.");
      await load();
    } finally {
      setBusy(undefined);
    }
  };
  const schedule = async () => {
    if (!review || !scheduleValue || busy) return;
    setBusy("schedule");
    try {
      await productApi.scheduleStudioPublication(review.id, new Date(scheduleValue).toISOString());
      setToast("Agendamento interno salvo; nenhuma publicação externa foi confirmada");
      await load();
      await data.refresh?.();
    } catch {
      setToast("O agendamento não foi salvo. Use uma data futura e revalide a aprovação.");
      await load();
    } finally {
      setBusy(undefined);
    }
  };

  if (loading) return <section className="cx-publisher-approved"><StateBanner title="Validando a versão aprovada…" detail="Conferindo revisão, copy, mídia e permissões do workspace." /></section>;
  if (error || !review || !preflight) return (
    <section className="cx-publisher-approved">
      <StateBanner tone="orange" title="O pré-flight não está disponível" detail={error || "Não foi encontrada uma revisão aprovada vinculada a este conteúdo."} action="Voltar à revisão" actionId="PUBLISH-OPEN-EDITOR" onAction={() => navigate(`/approvals/${postId}`)} />
    </section>
  );

  const pages = preflight.pageIds;
  const selectedPage = pages[slide];
  const contentLabel = preflight.contentType === "carousel" ? `${pages.length} slides` : preflight.contentType === "visual" ? "Imagem" : "Vídeo";
  const failed = preflight.checks.some((check) => check.status === "failed");
  const scheduledText = preflight.scheduledAt
    ? new Intl.DateTimeFormat("pt-BR", { dateStyle: "medium", timeStyle: "short", timeZone: "America/Sao_Paulo" }).format(new Date(preflight.scheduledAt))
    : undefined;
  const editorMode = preflight.contentType === "presenter" ? "presenter" : preflight.contentType === "video" ? "video" : "visual";
  return (
    <section className="cx-publisher-approved">
      <header>
        <div><small>Conteúdos / {preflight.title} / Publicação</small><h1>Controle de publicação</h1><p>Revise o artefato aprovado e prepare o handoff manual.</p></div>
        <Chip tone={preflight.status === "scheduled" ? "green" : "orange"}>{preflight.status === "scheduled" ? "Agendamento interno salvo" : "Pré-flight: ação necessária"}</Chip>
      </header>
      <div className="cx-publisher-layout">
        <section className="cx-publisher-content" aria-labelledby="publisher-preview-heading">
          <h2 id="publisher-preview-heading">Prévia do conteúdo aprovado</h2>
          <div className="cx-publisher-channel"><b>{preflight.platform}</b><Chip tone="orange">Conector externo indisponível</Chip><span>{preflight.format} · {contentLabel} · v{preflight.documentVersion}</span></div>
          <nav aria-label="Dados da publicação">
            {["Visual", "Legenda", "Metadados"].map((item) => <button data-action-id="PUBLISH-SELECT-PREVIEW" className={previewTab === item ? "is-active" : ""} aria-pressed={previewTab === item} onClick={() => setPreviewTab(item)} key={item}>{item}</button>)}
          </nav>
          {previewTab === "Visual" && <>
            <div className="cx-publisher-preview">
              <span>{pages.length ? `${slide + 1} / ${pages.length}` : "Render aprovado"}</span>
              {pages.length > 1 && <button data-action-id="PUBLISH-SELECT-PREVIEW" aria-label="Slide anterior" onClick={() => setSlide((slide + pages.length - 1) % pages.length)}>‹</button>}
              <div className="cx-publisher-approved-media"><ReviewSnapshotPreview review={review} pageId={selectedPage} onReady={setPreviewReady} /></div>
              {pages.length > 1 && <button data-action-id="PUBLISH-SELECT-PREVIEW" aria-label="Próximo slide" onClick={() => setSlide((slide + 1) % pages.length)}>›</button>}
            </div>
            {pages.length > 1 && <div className="cx-publisher-thumbs">{pages.map((pageId, index) => <button data-action-id="PUBLISH-SELECT-PREVIEW" className={slide === index ? "is-active" : ""} aria-label={`Mostrar slide ${index + 1}`} aria-pressed={slide === index} onClick={() => setSlide(index)} key={pageId}><span>{index + 1}</span></button>)}</div>}
          </>}
          {previewTab === "Legenda" && <div className="cx-final-caption"><b>Legenda aprovada</b><p>{approvedCaption || "A versão aprovada não possui legenda."}</p></div>}
          {previewTab === "Metadados" && <dl className="cx-publisher-metadata"><div><dt>Revisão</dt><dd>{review.id}</dd></div><div><dt>Documento</dt><dd>{review.documentId}</dd></div><div><dt>Versão</dt><dd>v{review.documentVersion}</dd></div><div><dt>Formato</dt><dd>{preflight.format}</dd></div></dl>}
          <div className="cx-final-caption"><b>Legenda final aprovada</b><p>{approvedCaption || "Sem legenda nesta versão."}</p></div>
          <div className="cx-publisher-actions">
            <Button actionId="PUBLISH-COPY-CAPTION" disabled={!approvedCaption} onClick={async () => { try { await navigator.clipboard.writeText(approvedCaption); setCopied(true); setToast("Legenda aprovada copiada"); } catch { setCopied(false); setToast("O navegador bloqueou a cópia. Selecione a legenda manualmente."); } }}>{copied ? "Legenda copiada" : "Copiar legenda"}</Button>
            <Button actionId="PUBLISH-DOWNLOAD-ASSETS" disabled={busy === "package"} onClick={downloadPackage}>{busy === "package" ? "Gerando pacote…" : "Baixar arquivos"}</Button>
            <Button actionId="PUBLISH-OPEN-EDITOR" onClick={() => navigate(`/content/${postId}/edit?mode=${editorMode}`)}>Abrir no editor</Button>
          </div>
          <footer>A prévia vem da revisão fixada. Ela representa o arquivo de saída, não a interface exata da rede social.</footer>
        </section>
        <aside>
          <h2>Checklist de saída</h2>
          {preflight.checks.map((check, index) => <button data-action-id="PUBLISH-SELECT-CHECK" className={`${check.status !== "passed" ? "is-warning" : ""} ${selectedCheck === index ? "is-active" : ""}`.trim()} aria-pressed={selectedCheck === index} onClick={() => setSelectedCheck(index)} key={check.key}><span>{index + 1}</span><b>{check.label}<small>{check.status === "passed" ? "Verificado" : "Atenção"}</small></b></button>)}
          <section><h3>Agendamento interno</h3><label className="cx-publisher-schedule">Data e horário em America/São_Paulo<input data-action-id="PUBLISH-SET-SCHEDULE" aria-label="Data e horário do agendamento interno" type="datetime-local" value={scheduleValue} min={nextScheduleInputValue()} onChange={(event) => setScheduleValue(event.target.value)} /></label>{scheduledText && <p>Salvo para {scheduledText}. Isso não confirma postagem externa.</p>}</section>
          <section><h3>Handoff manual</h3><p>O pacote inclui a mídia aprovada, a legenda e um manifesto vinculado à revisão v{review.documentVersion}.</p></section>
          <Button tone="primary" actionId="PUBLISH-SCHEDULE" disabled={failed || busy === "schedule" || !previewReady} title={!previewReady ? "Carregue a mídia aprovada antes de agendar." : undefined} onClick={schedule}>{busy === "schedule" ? "Salvando…" : preflight.status === "scheduled" ? "Atualizar agendamento interno" : "Agendar internamente"}</Button>
          <Button actionId="PUBLISH-EXPORT-PACKAGE" disabled={busy === "package"} onClick={downloadPackage}>Exportar pacote manual</Button>
          <Button disabled title="Conecte e valide um canal de publicação para liberar esta ação.">Publicar agora · conector indisponível</Button>
          <StateBanner tone="orange" title="Nenhuma postagem externa será feita" detail="A Clicko salva o horário e prepara o pacote; um operador ainda precisa concluir a publicação no canal." />
          <footer>Studio → revisão v{review.documentVersion} → pré-flight → agendamento interno → handoff manual</footer>
        </aside>
      </div>
    </section>
  );
}

function ApprovedPublisherSurface(props: AnyRecord) {
  return props.demo ? <DemoApprovedPublisherSurface {...props} /> : <AuthenticatedApprovedPublisherSurface {...props} />;
}

function DemoApprovedPublisherSurface({ navigate, setToast }: AnyRecord) {
  const [slide, setSlide] = React.useState(0);
  const [scheduled, setScheduled] = React.useState(false);
  const [copied, setCopied] = React.useState(false);
  const [previewTab, setPreviewTab] = React.useState("Visual");
  const [selectedCheck, setSelectedCheck] = React.useState(0);
  const downloadApprovedAssets = () => {
    phase3Arts.forEach((assetUrl, index) => {
      const anchor = document.createElement("a");
      anchor.href = assetUrl;
      anchor.download = `clicko-publicacao-slide-${index + 1}.png`;
      anchor.click();
    });
    setToast("6 imagens aprovadas enviadas para download");
  };
  return (
    <section className="cx-publisher-approved">
      <header>
        <div>
          <small>
            Calendário　/　O Brasil cabe em uma xícara　/　Publicação
          </small>
          <h1>Controle de publicação</h1>
          <p>Revise a peça e prepare a saída com segurança.</p>
        </div>
        <Chip tone="orange">△ Pré-flight: atenção necessária</Chip>
      </header>
      <div className="cx-publisher-layout">
        <main>
          <h2>Prévia do conteúdo</h2>
          <div className="cx-publisher-channel">
            ◎ Instagram · @cafeaurora　⌄{" "}
            <Chip tone="orange">Confirmação pendente</Chip>
            <span>Carrossel · 4:5 · 6 slides</span>
          </div>
          <nav>
            {["Visual", "Legenda", "Metadados"].map((item) => (
              <button
                data-action-id="PUBLISH-SELECT-PREVIEW"
                className={previewTab === item ? "is-active" : ""}
                aria-pressed={previewTab === item}
                onClick={() => setPreviewTab(item)}
                key={item}
              >
                {item}
              </button>
            ))}
          </nav>
          <div className="cx-publisher-preview">
            <span>{slide + 1} / 6</span>
            <button
              data-action-id="PUBLISH-SELECT-PREVIEW"
              aria-label="Slide anterior"
              onClick={() => setSlide((slide + 5) % 6)}
            >
              ‹
            </button>
            <img
              src={slide === 5 ? phase3Arts[3] : phase3Arts[0]}
              alt={`Prévia do slide ${slide + 1}`}
            />
            <button
              data-action-id="PUBLISH-SELECT-PREVIEW"
              aria-label="Próximo slide"
              onClick={() => setSlide((slide + 1) % 6)}
            >
              ›
            </button>
          </div>
          <div className="cx-publisher-thumbs">
            {[1, 2, 3, 4, 5, 6].map((x, i) => (
              <button
                data-action-id="PUBLISH-SELECT-PREVIEW"
                className={slide === i ? "is-active" : ""}
                aria-label={`Mostrar slide ${x}`}
                aria-pressed={slide === i}
                onClick={() => setSlide(i)}
                key={x}
              >
                <img src={i === 5 ? phase3Arts[3] : phase3Arts[0]} alt="" />
              </button>
            ))}
          </div>
          <div className="cx-final-caption">
            <b>Legenda final</b>
            <p>
              O Brasil cabe em uma xícara.
              <br />
              Quatro territórios. Uma experiência.
              <br />
              #CafeAurora #CafeEspecial #DoBrasilParaVocê
            </p>
          </div>
          <div className="cx-publisher-actions">
            <Button
              actionId="PUBLISH-COPY-CAPTION"
              onClick={() => {
                setCopied(true);
                setToast("Legenda copiada");
              }}
            >
              ▣ {copied ? "Legenda copiada" : "Copiar legenda"}
            </Button>
            <Button actionId="PUBLISH-DOWNLOAD-ASSETS" onClick={downloadApprovedAssets}>
              Baixar imagens
            </Button>
            <Button
              actionId="PUBLISH-OPEN-EDITOR"
              onClick={() => navigate("/content/post-ritual/edit?mode=visual")}
            >
              ⌁ Abrir no editor
            </Button>
          </div>
          <footer>
            Informação: a prévia representa o formato, não o chrome exato da rede.
          </footer>
        </main>
        <aside>
          <h2>Checklist de saída</h2>
          {[
            "Conteúdo aprovado",
            "Versão v3 selecionada",
            "Assets disponíveis",
            "Área segura validada",
            "Data e horário futuros",
            "Conta/canal confirmado",
          ].map((x, i) => (
            <button
              data-action-id="PUBLISH-SELECT-CHECK"
              className={`${i === 5 ? "is-warning" : ""} ${selectedCheck === i ? "is-active" : ""}`.trim()}
              aria-pressed={selectedCheck === i}
              onClick={() => setSelectedCheck(i)}
              key={x}
            >
              <span>{i + 1}</span>
              <b>
                {x}
                <small>
                  {i === 5 ? "Conector ainda não disponível" : "✓ OK　⌄"}
                </small>
              </b>
            </button>
          ))}
          <section>
            <h3>Agendamento interno</h3>
            <div>
              <Button>21 mai 2026　⌄</Button>
              <Button>10:30　⌄</Button>
              <Button>● America/São_Paulo　⌄</Button>
            </div>
            <Button>▣ O Brasil cabe em uma xícara　⌄</Button>
          </section>
          <section>
            <h3>
              Handoff manual <Button>↧ Exportar pacote</Button>
            </h3>
            <p>Pacote inclui 6 imagens, legenda, hashtags e instruções.</p>
          </section>
          <Button
            tone="primary"
            actionId="PUBLISH-SCHEDULE"
            onClick={() => {
              setScheduled(true);
              setToast("Agendamento interno salvo");
            }}
          >
            ▣ {scheduled ? "Agendamento salvo" : "Agendar internamente"}
          </Button>
          <Button actionId="PUBLISH-EXPORT-PACKAGE" onClick={() => setToast("Pacote exportado")}>
            ↧ Exportar pacote
          </Button>
          <Button
            disabled
            title="Conecte um canal de publicação para liberar esta ação."
          >
            Publicar agora · conector indisponível
          </Button>
          <StateBanner
            tone="orange"
            title="A Clicko salvará o agendamento, mas não confirma postagem externa sem um conector ativo."
          />
          <footer>
            Opportunity → Campaign → Carousel v3 → Approved → Schedule
          </footer>
        </aside>
      </div>
    </section>
  );
}

function ApprovedPostDetail({ navigate }: AnyRecord) {
  const [detailTab, setDetailTab] = React.useState("Peça");
  const [tab, setTab] = React.useState("Desempenho");
  return (
    <section className="cx-post-approved">
      <header>
        <div>
          <small>Conteúdos　/　Ritual de foco</small>
          <h1>Ritual de foco</h1>
          <p>
            <Chip tone="green">Publicado</Chip>　Instagram · Carrossel · 12 mai
            2026 · Campanha Aurora Origens
          </p>
        </div>
        <Button
          actionId="POST-EDIT"
          onClick={() => navigate("/content/post-ritual/edit?mode=visual")}
        >
          Editar
        </Button>
        <Button>Comparar versões</Button>
        <Button
          tone="primary"
          actionId="POST-OPEN-REUSE"
          onClick={() => navigate("/content/post-ritual/remix")}
        >
          Abrir no Reuse Lab
        </Button>
      </header>
      <div className="cx-post-approved-layout">
        <main>
          <div className="cx-post-visual">
            <img src="/canonical/figma/phase3/s17-visual.png" />
            <div>
              {[1, 2, 3, 4, 5].map((x) => (
                <img src="/canonical/figma/phase3/s17-visual.png" key={x} />
              ))}
            </div>
            <span>1 / 5</span>
          </div>
          <nav>
            {["Peça", "Legenda", "Versões", "Comentários"].map((x) => (
              <button
                data-action-id="POST-SELECT-DETAIL"
                className={detailTab === x ? "is-active" : ""}
                aria-pressed={detailTab === x}
                onClick={() => setDetailTab(x)}
                key={x}
              >
                {x}
              </button>
            ))}
          </nav>
          <p>
            Legenda final <Chip>Versão publicada v2</Chip>
          </p>
          <article>
            Concentre-se no que realmente importa. Um café. Um ritual.
            <br />
            Menos ruído, mais presença. #RitualDeFoco #CafeAurora
          </article>
          <h3>Linhagem desta peça</h3>
          <div className="cx-post-lineage">
            {[
              ["Oportunidade", "Café"],
              ["Aurora Origens", "Campanha"],
              ["Memória v3", "Estratégia"],
              ["Carrossel v2", "Peça"],
              ["Publicação", "Instagram"],
              ["Snapshot", "13 mai 2026"],
            ].map(([a, b], i) => (
              <React.Fragment key={a}>
                <span className={i === 0 ? "is-active" : ""}>
                  <b>{a}</b>
                  <small>{b}</small>
                </span>
                {i < 5 && <i>→</i>}
              </React.Fragment>
            ))}
          </div>
          <footer>
            Fonte: snapshot informado/sincronizado{" "}
            <span>13 mai 2026 às 09:12</span>
          </footer>
        </main>
        <aside>
          <nav>
            {["Desempenho", "Versões", "Comentários", "Linhagem"].map((x) => (
              <button
                data-action-id="POST-SELECT-DETAIL"
                className={tab === x ? "is-active" : ""}
                onClick={() => setTab(x)}
                key={x}
              >
                {x}
              </button>
            ))}
          </nav>
          {tab === "Desempenho" ? (
            <>
              <h2>O que aconteceu</h2>
              <div className="cx-post-metrics">
                {[
                  ["Alcance", "45,2 mil"],
                  ["Salvamentos", "1,2 mil"],
                  ["Compartilhamentos", "842"],
                  ["CTR", "4,8%"],
                ].map(([a, b]) => (
                  <KeyValue label={a} value={b} key={a} />
                ))}
              </div>
              <small>
                Fonte: snapshot informado/sincronizado · 13 mai 2026 · atribuído
                a esta peça
              </small>
              <StateBanner
                tone="neutral"
                title="✦ 3× mais salvamentos que a média da campanha"
              />
              <h3>Aprendizado acionável</h3>
              {[
                [
                  "PRESERVAR",
                  "Clareza do ritual e fotografia de produto",
                  "Alta performance consistente",
                ],
                [
                  "ADAPTAR",
                  "CTA e quantidade de texto",
                  "CTRs abaixo do potencial",
                ],
                [
                  "TESTAR",
                  "Novo hook mantendo a composição",
                  "Hipótese: pode aumentar retenção inicial",
                ],
              ].map(([a, b, c], i) => (
                <article className="cx-learning-action" key={a}>
                  <span>{i ? "Ação" : "Teste"}</span>
                  <div>
                    <small>{a}</small>
                    <b>{b}</b>
                  </div>
                  <p>{c}</p>
                </article>
              ))}
              <small>ⓘ Associação observada. Não comprova causalidade.</small>
              <div className="cx-next-pass">
                <h3>Próxima passagem</h3>
                <p>Transforme este vencedor em uma derivação rastreável.</p>
                <Button
                  tone="primary"
                  actionId="POST-OPEN-REUSE"
                  onClick={() => navigate("/content/post-ritual/remix")}
                >
                  Abrir no Reuse Lab →
                </Button>
                <Button>✦ Registrar hipótese</Button>
              </div>
              <h3>Evolução por snapshot</h3>
              <div className="cx-snapshot-line">
                <i />
                <i />
                <i />
              </div>
              <section className="cx-provenance-box">
                <h3>Proveniência</h3>
                <p>
                  Definições das métricas
                  <br />• Alcance: contas únicas impactadas
                  <br />• Salvamentos: total de salvamentos
                  <br />• Compartilhamentos: total de compartilhamentos
                  <br />• CTR: cliques no link / impressões
                </p>
              </section>
            </>
          ) : (
            <div className="cx-post-tab-state">
              <h2>{tab}</h2>
              <p>
                {tab === "Versões"
                  ? "v2 publicada · v1 anterior."
                  : tab === "Comentários"
                    ? "2 comentários resolvidos após a publicação."
                    : "Oportunidade, campanha, memória, peça, publicação e snapshot conectados."}
              </p>
            </div>
          )}
        </aside>
      </div>
    </section>
  );
}

function ApprovedRemixSurface({ data, demo, navigate, pathname, setToast }: AnyRecord) {
  const sourceId = pathname.split("/")[2];
  const source = demo
    ? demoPosts.find((post) => post.id === sourceId) || demoPosts[0]
    : data.snapshot?.posts?.find((post: AnyRecord) => post.id === sourceId);
  const [hypothesis, setHypothesis] = React.useState(0);
  const [creating, setCreating] = React.useState(false);
  const [derivativeIds, setDerivativeIds] = React.useState<Record<string, string>>({});
  const [selectedFormats, setSelectedFormats] = React.useState(() =>
    new Set(["post", "story", "square"]),
  );
  const [reuseError, setReuseError] = React.useState("");
  const [reuseMode, setReuseMode] = React.useState("Remix guiado");
  const [sourceView, setSourceView] = React.useState("Derivação");
  const [hypothesisSelected, setHypothesisSelected] = React.useState(true);
  const preserveOptions = [
    ["Texto principal", "Promessa e linguagem da origem"],
    ["Composição central", "Hierarquia e foco visual"],
    ["Assinatura da marca", "Elementos de reconhecimento"],
  ];
  const adaptOptions = [
    ["Formato", "Proporção e canal de destino"],
    ["CTA", "Chamada adequada ao novo objetivo"],
    ["Quantidade de texto", "Leitura adequada ao novo formato"],
  ];
  const [selectedPreserve, setSelectedPreserve] = React.useState(
    () => new Set(preserveOptions.map(([label]) => label)),
  );
  const [selectedAdapt, setSelectedAdapt] = React.useState(
    () => new Set(adaptOptions.map(([label]) => label)),
  );
  const formats = [
    { key: "post", title: "Instagram Post 4:5", state: "Pronto como rascunho", risk: "Baixo", format: "post", mode: "visual" },
    { key: "story", title: "Story 9:16", state: "Revisão manual necessária", risk: "Médio", format: "story", mode: "visual" },
    { key: "square", title: "Square 1:1", state: "Ajuste de composição", risk: "Médio", format: "post", mode: "visual" },
    { key: "smart", title: "Smart resize automático", state: "Ainda não disponível", risk: "—", format: "post", mode: "visual", disabled: true },
  ];
  const hypothesisText = hypothesis
    ? "Seu foco começa no primeiro gole."
    : "Seu ritual começa antes do primeiro gole.";
  const sourceCampaign = data.snapshot?.campaigns?.find(
    (campaign: AnyRecord) => campaign.id === source?.campaignId,
  );
  const persistedDerivatives = React.useMemo(() => {
    const next: Record<string, string> = {};
    for (const post of data.snapshot?.posts || []) {
      const lineage = (post.versions || [])
        .map((version: AnyRecord) => version?.lineage)
        .find((candidate: AnyRecord) => candidate?.sourcePostId === sourceId);
      const key = lineage?.derivationKey;
      if (typeof key === "string" && formats.some((format) => format.key === key)) {
        next[key] = post.id;
      }
    }
    return next;
  }, [data.snapshot?.posts, sourceId]);
  React.useEffect(() => {
    if (!Object.keys(persistedDerivatives).length) return;
    setDerivativeIds((current) => ({ ...persistedDerivatives, ...current }));
  }, [persistedDerivatives]);
  const selectedDerivativeIds = formats
    .filter((format) => selectedFormats.has(format.key) && derivativeIds[format.key])
    .map((format) => derivativeIds[format.key]);
  const pendingFormats = formats.filter(
    (format) =>
      !format.disabled &&
      selectedFormats.has(format.key) &&
      !derivativeIds[format.key],
  );
  const toggleSelection = (
    setter: React.Dispatch<React.SetStateAction<Set<string>>>,
    value: string,
  ) =>
    setter((current) => {
      const next = new Set(current);
      if (next.has(value)) next.delete(value);
      else next.add(value);
      return next;
    });
  const createDerivations = async () => {
    if (creating) return;
    if (!source) {
      setReuseError("A peça de origem não foi encontrada neste workspace.");
      return;
    }
    if (!hypothesisSelected) {
      setReuseError("Selecione a hipótese principal antes de gerar derivações.");
      return;
    }
    if (!pendingFormats.length) {
      setToast("As derivações selecionadas já estão salvas.");
      return;
    }
    setCreating(true);
    setReuseError("");
    const createdNow: Record<string, string> = {};
    try {
      for (const format of pendingFormats) {
        if (demo) {
          createdNow[format.key] = `${source.id}-${format.key}`;
          continue;
        }
        const id = await data.createPostDerivation(source.id, {
          title: `${source.title} — ${format.title}`,
           format: format.format,
           platform: "instagram",
           objective: `Testar ${hypothesisText}`,
           derivationKey: format.key,
           hypothesis: hypothesisText,
           preserve: [...selectedPreserve],
           adapt: [...selectedAdapt],
        });
        createdNow[format.key] = id;
      }
      setDerivativeIds((current) => ({ ...current, ...createdNow }));
      setToast(
        `${Object.keys(createdNow).length} derivações criadas com lineage`,
      );
    } catch (error) {
      setDerivativeIds((current) => ({ ...current, ...createdNow }));
      setReuseError(
        error instanceof Error
          ? error.message
          : "Nem todas as derivações puderam ser criadas.",
      );
    } finally {
      setCreating(false);
    }
  };
  return (
    <section className="cx-remix-approved">
      <header>
        <div>
          <small>Conteúdos　/　{source?.title || "Origem indisponível"}　/　Reuse Lab</small>
          <h1>Transforme o que funcionou em uma nova peça</h1>
          <p>Preserve a força, adapte o formato e registre a hipótese.</p>
        </div>
        <Button
          actionId="REUSE-SUGGEST-HYPOTHESIS"
          onClick={() => setHypothesis((hypothesis + 1) % 2)}
        >
          Sugerir hipótese
        </Button>
        <Button
          actionId="REUSE-GENERATE-DERIVATIONS"
          tone="primary"
          disabled={creating || pendingFormats.length === 0 || !source || !hypothesisSelected}
          onClick={() => void createDerivations()}
        >
          {creating
            ? "Criando derivações…"
            : pendingFormats.length
              ? `Gerar derivações · ${pendingFormats.length}`
              : "Derivações salvas"}
        </Button>
        <Button
          actionId="REUSE-SEND-FACTORY"
          disabled={selectedDerivativeIds.length === 0}
          onClick={() => {
            const query = new URLSearchParams({
              source: source?.id || sourceId,
              derivatives: selectedDerivativeIds.join(","),
            });
            navigate(`/factory?${query.toString()}`);
          }}
        >
          Enviar à Fábrica
        </Button>
      </header>
      <nav>
        {["Remix guiado", "Variações"].map((item) => (
          <button
            data-action-id="REUSE-SELECT-MODE"
            className={reuseMode === item ? "is-active" : ""}
            aria-pressed={reuseMode === item}
            onClick={() => setReuseMode(item)}
            key={item}
          >
            {item}
          </button>
        ))}
      </nav>
      {reuseError && (
        <HonestState
          compact
          state="recoverable-error"
          detail={reuseError}
          preserved="a origem, as hipóteses e qualquer derivação já criada"
          impact="somente os formatos ainda não criados precisam ser tentados novamente"
          actionLabel="Tentar formatos pendentes"
          actionId="REUSE-GENERATE-DERIVATIONS"
          onAction={() => void createDerivations()}
        />
      )}
      <div className="cx-remix-approved-grid">
        <aside>
          <h2>Peça de origem</h2>
          {source?.imageUrl ? (
            <img src={source.imageUrl} alt={`Prévia da origem ${source.title}`} />
          ) : (
            <div
              className="cx-remix-source-preview"
              role="img"
              aria-label="Origem sem prévia visual"
            >
              <small>SEM PRÉVIA VISUAL</small>
              <strong>{source?.title || "Origem indisponível"}</strong>
              <span>{source?.copy || "Nenhum texto de origem disponível."}</span>
            </div>
          )}
          <Chip tone={source?.status === "published" ? "green" : "orange"}>
            {source?.status === "published" ? "Publicado" : "Origem selecionada"}
          </Chip>
          {[
            ["Campanha", sourceCampaign?.title || "Sem campanha vinculada"],
            ["Formato", source ? `${source.platform} · ${source.format}` : "Indisponível"],
            [
              "Criado em",
              source?.createdAt
                ? new Intl.DateTimeFormat("pt-BR", { dateStyle: "medium" }).format(
                    new Date(source.createdAt),
                  )
                : "Sem data observada",
            ],
          ].map(([a, b]) => (
            <KeyValue label={a} value={b} key={a} />
          ))}
          <h3>Evidência real</h3>
          <div className="cx-remix-metrics">
            <KeyValue label="Alcance" value={source?.reach ? String(source.reach) : "Sem dado observado"} />
            <KeyValue label="Salvamentos" value={source?.saves ? String(source.saves) : "Sem dado observado"} />
            <KeyValue label="Compartilhamentos" value={source?.shares ? String(source.shares) : "Sem dado observado"} />
          </div>
          <h3>Por que reutilizar</h3>
          <p>{source?.objective || "Nenhum objetivo foi registrado para esta origem."}</p>
          <h3>Linhagem</h3>
          <p>{sourceCampaign?.title || "Sem campanha"}　›　{source?.title || "Origem"}　›　v{source?.versions?.length || 1}</p>
        </aside>
        <section className="cx-remix-plan" aria-labelledby="reuse-plan-title">
          <h2 id="reuse-plan-title">Plano da derivação</h2>
          <small>PRESERVAR</small>
          {preserveOptions.map((x) => (
            <label key={x[0]}>
              <input
                type="checkbox"
                data-action-id="REUSE-TOGGLE-PRESERVE"
                checked={selectedPreserve.has(x[0])}
                onChange={() => toggleSelection(setSelectedPreserve, x[0])}
              />
              {x[0]}
              <span>{x[1]}</span>
            </label>
          ))}
          <small>ADAPTAR</small>
          {adaptOptions.map((x) => (
            <label key={x[0]}>
              <input
                type="checkbox"
                data-action-id="REUSE-TOGGLE-ADAPT"
                checked={selectedAdapt.has(x[0])}
                onChange={() => toggleSelection(setSelectedAdapt, x[0])}
              />
              {x[0]}
              <span>{x[1]}</span>
            </label>
          ))}
          <small>TESTAR</small>
          <button
            data-action-id="REUSE-TOGGLE-HYPOTHESIS"
            className={`cx-hypothesis ${hypothesisSelected ? "is-active" : ""}`}
            aria-pressed={hypothesisSelected}
            onClick={() => setHypothesisSelected((current) => !current)}
          >
            <i />
            Novo hook:{" "}
            {hypothesisText}
            <span>Hipótese principal</span>
          </button>
          <KeyValue label="Objetivo" value={source?.objective || "Não informado"} />
          <KeyValue label="Campanha de destino" value={sourceCampaign?.title || "Sem campanha vinculada"} />
          <footer>ⓘ A hipótese ficará registrada na linhagem.</footer>
        </section>
        <section>
          <header>
            <h2>Formatos derivados</h2>
            <nav>
              {["Original", "Derivação"].map((item) => (
                <button
                  data-action-id="REUSE-SELECT-SOURCE-VIEW"
                  className={sourceView === item ? "is-active" : ""}
                  aria-pressed={sourceView === item}
                  onClick={() => setSourceView(item)}
                  key={item}
                >
                  {item}
                </button>
              ))}
            </nav>
          </header>
          <div>
            {formats.map((format, i) => (
              <article className={format.disabled ? "is-disabled" : ""} key={format.key}>
                <label className="cx-derivation-select">
                  <input
                    type="checkbox"
                    data-action-id="REUSE-TOGGLE-FORMAT"
                    checked={selectedFormats.has(format.key)}
                    disabled={format.disabled || creating}
                    onChange={() =>
                      setSelectedFormats((current) => {
                        const next = new Set(current);
                        if (next.has(format.key)) next.delete(format.key);
                        else next.add(format.key);
                        return next;
                      })
                    }
                  />
                  Incluir formato
                </label>
                <h3>{format.title}</h3>
                <small>
                  {i === 0 ? "✓" : "△"} {format.state}
                </small>
                <div className="cx-smart-empty">
                  <small>{sourceView.toUpperCase()}</small>
                  <strong>
                    {format.disabled
                      ? "Formato indisponível"
                      : derivativeIds[format.key]
                        ? "Rascunho persistido"
                        : "Ainda não gerado"}
                  </strong>
                </div>
                <p>
                  Elementos preservados
                  <br />Cor, forma e tipografia
                </p>
                <p>
                  Risco de adaptação
                  <br />
                  <b>{format.risk}</b>
                </p>
                <Button
                  actionId="REUSE-OPEN-DERIVATION"
                  disabled={!derivativeIds[format.key]}
                  onClick={() => navigate(`/content/${derivativeIds[format.key]}/edit?mode=${format.mode}`)}
                >
                  {format.disabled
                    ? "Em breve"
                    : derivativeIds[format.key]
                      ? "Abrir derivado no editor →"
                      : "Gere para abrir"}
                </Button>
              </article>
            ))}
          </div>
          <footer>
            ⓘ Adaptação de layout e texto não automática. Revisão humana é
            sempre necessária.
          </footer>
        </section>
      </div>
      <footer className="cx-remix-lineage">
        <h3>Linhagem da derivação</h3>
        {[
          [source?.title || "Origem indisponível", "Peça de origem"],
          ["Reuse event", "Remix guiado"],
          [
            selectedDerivativeIds.length
              ? `${selectedDerivativeIds.length} derivações persistidas`
              : "Nova derivação v1",
            selectedDerivativeIds.length ? "Reidratável após recarregar" : "Ainda não criada",
          ],
          ["Visual Editor", "Próxima estação"],
          ["Métricas não são copiadas", "para nova peça"],
        ].map(([a, b], i) => (
          <React.Fragment key={a}>
            <article className={i === 2 ? "is-active" : ""}>
              <b>{a}</b>
              <small>{b}</small>
            </article>
            {i < 4 && <ArrowRight />}
          </React.Fragment>
        ))}
      </footer>
    </section>
  );
}

function ApprovedAnalyticsSurface({ navigate, setToast }: AnyRecord) {
  const [round, setRound] = React.useState(false);
  const [metric, setMetric] = React.useState("Alcance");
  return (
    <section className="cx-observatory-approved">
      <header>
        <div>
          <h1>Observatório de performance</h1>
          <p>
            Evidência para decidir a próxima rodada — sem inventar causalidade.
          </p>
        </div>
        <Button>Últimos 30 dias⌄</Button>
        <Button>Todos canais⌄</Button>
        <Button
          tone="primary"
          actionId="ANALYTICS-IMPORT-METRICS"
          onClick={() => setToast("Importação preparada")}
        >
          Importar métricas
        </Button>
      </header>
      <div className="cx-observatory-source">
        24 conteúdos analisados · Instagram + TikTok · última importação hoje,
        08:40 <b>Dados externos não são coletados automaticamente</b>
      </div>
      <div className="cx-observatory-kpis">
        {[
          ["ALCANCE", "482 mil", "+18%"],
          ["SALVAMENTOS", "8.420", "+31%"],
          ["COMPARTILHAMENTOS", "4.180", "+24%"],
          ["CLIQUES", "2.906", "+12%"],
        ].map(([a, b, c]) => (
          <article key={a}>
            <small>{a}</small>
            <strong>{b}</strong>
            <span>{c}</span>
            <p>vs. período anterior</p>
          </article>
        ))}
      </div>
      <div className="cx-observatory-grid">
        <section>
          <h2>Conteúdos que carregam evidência</h2>
          <p>Ordenados por contribuição, não apenas por vaidade.</p>
          {[
            [
              "01",
              "Ritual de foco",
              "Carrossel",
              "+42% salvamentos",
              phase3Arts[0],
            ],
            [
              "02",
              "Aurora UGC",
              "Reel",
              "+35% compartilhamentos",
              phase3Arts[2],
            ],
            [
              "03",
              "Origem em 3 atos",
              "Carrossel",
              "+21% cliques",
              phase3Arts[1],
            ],
          ].map((x) => (
            <button
              data-action-id="ANALYTICS-OPEN-CONTENT"
              onClick={() => navigate("/content/post-ritual")}
              key={x[0]}
            >
              <span>{x[0]}</span>
              <img src={x[4]} />
              <b>
                {x[1]}
                <small>{x[2]}</small>
              </b>
              <strong>
                {x[3]}
                <small>Promessa curta + textura</small>
              </strong>
              <i>Abrir →</i>
            </button>
          ))}
        </section>
        <section>
          <h2>Evolução por semana</h2>
          <nav>
            {["Alcance", "Salvamentos"].map((item) => (
              <button
                data-action-id="ANALYTICS-SELECT-METRIC"
                className={metric === item ? "is-active" : ""}
                aria-pressed={metric === item}
                onClick={() => setMetric(item)}
                key={item}
              >
                {item}
              </button>
            ))}
          </nav>
          <div className="cx-observatory-chart">
            <svg viewBox="0 0 400 220">
              <path d="M5 180L60 195L115 140L165 205L215 120L265 190L320 80L375 155" />
              <path d="M5 160L60 175L115 155L165 165L215 130L265 145L320 115L375 135" />
            </svg>
            <span>Sem 1　 　　 Sem 2　　　 Sem 3　　　 Sem 4</span>
          </div>
        </section>
        <section>
          <h2>Padrões criativos observados</h2>
          {[
            [
              "PRESERVAR",
              "Abertura curta + contraste tipográfico",
              "Aparece nos 3 melhores conteúdos",
            ],
            [
              "ADAPTAR",
              "Produto integrado à rotina",
              "Funcionou; testar mais rostos reais",
            ],
            [
              "TESTAR",
              "CTA antes do último slide",
              "Hipótese para elevar cliques",
            ],
          ].map(([a, b, c], i) => (
            <article key={a}>
              <span>{a}</span>
              <b>
                {b}
                <small>{c}</small>
              </b>
              <i>→</i>
            </article>
          ))}
        </section>
        <section>
          <h2>Próxima rodada</h2>
          <p>O sistema propõe ações; você decide o que vira campanha.</p>
          <StateBanner
            tone="orange"
            title="✦ Reutilizar o vencedor"
            detail="Transformar ‘Ritual de foco’ em 3 Reels com rosto, mantendo promessa e direção visual."
          />
          <Button
            tone="primary"
            actionId="ANALYTICS-CREATE-ROUND"
            onClick={() => {
              setRound(true);
              setToast("Rodada criada");
            }}
          >
            {round ? "Rodada criada" : "Criar rodada"}
          </Button>
          <h3>LACUNAS DE DADOS</h3>
          <p>
            · Conversões não atribuídas
            <br />· 6 posts sem métricas ou retenção
          </p>
          <strong>Correlação não prova causalidade.</strong>
        </section>
      </div>
    </section>
  );
}

function CalendarSurface({ data, demo, navigate }: AnyRecord) {
  const posts = demo ? demoPosts : data.snapshot?.posts || [];
  const [monthOffset, setMonthOffset] = React.useState(0);
  const [calendarView, setCalendarView] = React.useState("Semana");
  const days = [
    "SEG 17",
    "TER 18",
    "QUA 19",
    "QUI 20",
    "SEX 21",
    "SÁB 22",
    "DOM 23",
  ];
  return (
    <Page
      eyebrow="Planejamento"
      title="Calendário editorial"
      description="Veja a cadência antes de ocupar o feed."
      actions={
        <>
          <Button>Hoje</Button>
          <Button
            tone="primary"
            icon={Plus}
            actionId="CALENDAR-CREATE-CONTENT"
            onClick={() => navigate("/dashboard?create=open")}
          >
            Agendar conteúdo
          </Button>
        </>
      }
      wide
    >
      <div className="cx-calendar-head">
        <button
          data-action-id="CALENDAR-STEP-PERIOD"
          aria-label="Período anterior"
          onClick={() => setMonthOffset((current) => current - 1)}
        >
          Anterior
        </button>
        <h2>{monthOffset === 0 ? "Agosto 2026" : monthOffset < 0 ? "Julho 2026" : "Setembro 2026"}</h2>
        <button
          data-action-id="CALENDAR-STEP-PERIOD"
          aria-label="Próximo período"
          onClick={() => setMonthOffset((current) => current + 1)}
        >
          Próximo
        </button>
        <div />
        {["Semana", "Mês"].map((item) => (
          <button
            data-action-id="CALENDAR-SELECT-VIEW"
            className={calendarView === item ? "is-active" : ""}
            aria-pressed={calendarView === item}
            onClick={() => setCalendarView(item)}
            key={item}
          >
            {item}
          </button>
        ))}
      </div>
      <div className="cx-calendar">
        {days.map((day, i) => (
          <section key={day}>
            <header>{day}</header>
            <div className="cx-time">09:00</div>
            {(i === 1 || i === 3 || i === 5) && (
        <button
          data-action-id="CALENDAR-OPEN-PUBLISHER"
          onClick={() =>
                  navigate(`/publish/${posts[0]?.id || "post-ritual"}`)
                }
                style={{ top: `${92 + (i % 2) * 100}px` }}
              >
                <img
                  src={
                    posts[i % Math.max(posts.length, 1)]?.imageUrl ||
                    demoMedia.cup
                  }
                />
                <div>
                  <small>{i === 5 ? "TikTok" : "Instagram"}</small>
                  <b>
                    {
                      [
                        "Manhã sem pressa",
                        "O primeiro gole",
                        "Da origem à xícara",
                      ][i % 3]
                    }
                  </b>
                  <Chip tone={i === 3 ? "green" : "neutral"}>
                    {i === 3 ? "Aprovado" : "Rascunho"}
                  </Chip>
                </div>
              </button>
            )}
            <div className="cx-time cx-time--two">13:00</div>
            <div className="cx-time cx-time--three">17:00</div>
          </section>
        ))}
      </div>
    </Page>
  );
}

function PublisherSurface({ data, demo, navigate, setToast }: AnyRecord) {
  const post = demo ? demoPosts[0] : data.snapshot?.posts?.[0];
  const [scheduled, setScheduled] = React.useState("2026-08-20T09:30");
  const [publishMode, setPublishMode] = React.useState("Agendar");
  const publish = async () => {
    try {
      if (!demo && post)
        await data.decidePost(post.id, {
          action: "schedule",
          scheduledAt: new Date(scheduled).toISOString(),
        });
      setToast("Publicação agendada");
      navigate("/calendar");
    } catch {
      setToast("Não foi possível agendar");
    }
  };
  return (
    <Page
      eyebrow="Publicação"
      title="Pronto para entrar no ar"
      description="Última conferência de canal, legenda e horário."
      actions={
        <Button
          actionId="CONTENT-OPEN-DETAIL"
          onClick={() => navigate(`/content/${post?.id || "post-ritual"}`)}
        >
          Voltar
        </Button>
      }
    >
      <div className="cx-publish-grid">
        <div className="cx-phone">
          <header>
            <span className="cx-mini-avatar">CA</span>
            <b>cafeaurora</b>
            <MoreHorizontal />
          </header>
          <img
            src={post?.imageUrl || demoMedia.hero}
            alt="Prévia da publicação"
          />
          <div className="cx-phone-actions">
            <span>Curtir</span>
            <span>Comentar</span>
            <span>Compartilhar</span>
          </div>
          <p>
            <b>cafeaurora</b> O primeiro gole não acorda apenas o corpo. Ele
            abre espaço para o que importa.
          </p>
        </div>
        <aside className="cx-publish-panel">
          <section>
            <small>CANAL</small>
            <button
              className="cx-channel"
              disabled
              title="O canal é fixado pelo preflight desta versão. Volte ao projeto para trocá-lo."
            >
              <span>◎</span>
              <div>
                <b>Instagram · @cafeaurora</b>
                <small>Feed · 1080 × 1350</small>
              </div>
              <Check />
            </button>
          </section>
          <section>
            <small>LEGENDA</small>
            <textarea
              rows={6}
              defaultValue={
                post?.copy ||
                "O primeiro gole não acorda apenas o corpo. Ele abre espaço para o que importa.\n\n#CafeAurora #RitualDaManhã"
              }
            />
          </section>
          <section>
            <small>QUANDO PUBLICAR</small>
            <div className="cx-schedule">
              <button
                data-action-id="PUBLISH-SELECT-MODE"
                className={publishMode === "Agendar" ? "is-active" : ""}
                aria-pressed={publishMode === "Agendar"}
                onClick={() => setPublishMode("Agendar")}
              >
                <Clock3 />
                Agendar
              </button>
              <button
                data-action-id="PUBLISH-SELECT-MODE"
                className={publishMode === "Agora" ? "is-active" : ""}
                aria-pressed={publishMode === "Agora"}
                onClick={() => setPublishMode("Agora")}
              >
                <Zap />
                Agora
              </button>
            </div>
            <input
              data-action-id="CALENDAR-SET-SCHEDULE"
              type="datetime-local"
              value={scheduled}
              onChange={(e) => setScheduled(e.target.value)}
            />
          </section>
          <StateBanner
            tone="green"
            title="Tudo pronto"
            detail="Formato, canal e direitos de mídia verificados."
          />
          <Button
            tone="primary"
            icon={CalendarDays}
            actionId="PUBLISH-SCHEDULE"
            onClick={() => void publish()}
          >
            Agendar publicação
          </Button>
          <p className="cx-truth-note">
            Publicação externa depende do canal conectado. O agendamento é salvo
            no workspace.
          </p>
        </aside>
      </div>
    </Page>
  );
}

function PostDetail({ data, demo, pathname, navigate }: AnyRecord) {
  const id = pathname.split("/")[2];
  const post = demo
    ? demoPosts.find((x) => x.id === id) || demoPosts[0]
    : data.snapshot?.posts.find((x: AnyRecord) => x.id === id) ||
      data.snapshot?.posts[0];
  if (!post)
    return (
      <EmptyState
        title="Conteúdo não encontrado"
        detail="Crie a primeira peça deste workspace."
        action="Criar"
        onAction={() => navigate("/dashboard?create=open")}
      />
    );
  return (
    <Page
      eyebrow="Conteúdo"
      title={post.title}
      description={`${post.platform} · ${post.format}`}
      actions={
        <>
          <Button
            icon={Copy}
            actionId="POST-OPEN-REUSE"
            onClick={() => navigate(`/content/${post.id}/remix`)}
          >
            Reutilizar
          </Button>
          <Button
            tone="primary"
            actionId="POST-EDIT"
            onClick={() => navigate(`/content/${post.id}/edit?mode=visual`)}
          >
            Editar
          </Button>
        </>
      }
    >
      <div className="cx-post-detail">
        <div className="cx-post-media">
          <img
            src={post.imageUrl || demoMedia.hero}
            alt="Conteúdo da campanha"
          />
        </div>
        <aside>
          <div className="cx-post-status">
            <Chip tone={post.status === "approved" ? "green" : "orange"}>
              {statusLabel[post.status] || post.status}
            </Chip>
            <span>Atualizado há 18 min</span>
          </div>
          <section>
            <small>LEGENDA</small>
            <p>
              {post.copy ||
                "O primeiro gole não acorda apenas o corpo. Ele abre espaço para o que importa."}
            </p>
          </section>
          <section>
            <small>CAMPANHA</small>
            <button
              data-action-id="POST-OPEN-CAMPAIGN"
              onClick={() => navigate("/campaigns/active")}
            >
              <span className="cx-mini-thumb">
                <img src={demoMedia.cup} />
              </span>
              <div>
                <b>Ritual Café Aurora</b>
                <small>Campanha ativa</small>
              </div>
              <ChevronRight />
            </button>
          </section>
          <section>
            <small>HISTÓRICO</small>
            {["Direção visual aprovada", "Legenda ajustada", "Peça criada"].map(
              (x, i) => (
                <div className="cx-history" key={x}>
                  <i />
                  <div>
                    <b>{x}</b>
                    <span>{["Agora", "há 12 min", "ontem"][i]}</span>
                  </div>
                </div>
              ),
            )}
          </section>
          <Button
            icon={Send}
            actionId="POST-PREPARE-PUBLISH"
            onClick={() => navigate(`/publish/${post.id}`)}
          >
            Preparar publicação
          </Button>
        </aside>
      </div>
    </Page>
  );
}

function RemixSurface({ navigate }: AnyRecord) {
  const [selected, setSelected] = React.useState(1);
  return (
    <Page
      eyebrow="Reutilizar conteúdo"
      title="Uma ideia, novos formatos"
      description="A Clicko preserva a mensagem e adapta ritmo, proporção e canal."
      actions={
        <Button actionId="REUSE-CANCEL" onClick={() => navigate("/content/post-ritual")}>
          Cancelar
        </Button>
      }
    >
      <div className="cx-remix">
        <div className="cx-remix-source">
          <small>ORIGINAL</small>
          <img src={demoMedia.hero} />
          <h3>O primeiro gole</h3>
          <p>Post · Instagram</p>
        </div>
        <div className="cx-remix-arrow">
          <ArrowRight />
        </div>
        <div className="cx-remix-options">
          <small>ESCOLHA O DESTINO</small>
          {[
            [Layers3, "Carrossel", "5 páginas · Instagram"],
            [Play, "Reel", "12–18s · vertical"],
            [FileText, "Newsletter", "Abertura + história"],
            [Image, "Story", "3 telas · 9:16"],
          ].map(([Icon, title, desc]: any, i) => (
            <button
              data-action-id="REUSE-SELECT-MODE"
              className={selected === i ? "is-selected" : ""}
              onClick={() => setSelected(i)}
              key={title}
            >
              <Icon />
              <div>
                <b>{title}</b>
                <span>{desc}</span>
              </div>
              {selected === i && <Check />}
            </button>
          ))}
        </div>
        <aside className="cx-remix-ai">
          <Sparkles />
          <small>ADAPTAÇÃO</small>
          <h3>O que será preservado</h3>
          <p>
            A tensão da pressa, o ritual como virada e o tom íntimo da marca.
          </p>
          <hr />
          <b>Tempo estimado</b>
          <strong>~ 40 segundos</strong>
          <Button
            tone="primary"
            icon={WandSparkles}
            actionId="REUSE-GENERATE-ADAPTATION"
            onClick={() => navigate("/content/draft/edit?mode=carousel")}
          >
            Gerar adaptação
          </Button>
        </aside>
      </div>
    </Page>
  );
}

function WorldSurface({ navigate, pathname }: AnyRecord) {
  const id = pathname.split("/")[2];
  const [approved, setApproved] = React.useState(false);
  const [angleVersion, setAngleVersion] = React.useState(0);
  const inputs = [
    [
      "OPORTUNIDADE",
      "Festival Brasileiro de Cafés Especiais",
      "Evento de alta atenção e afinidade com cafés de origem.",
      "/canonical/figma/phase2/s15-angle-1.png",
    ],
    [
      "AUDIÊNCIA",
      "25–44 · procedência · experiências em casa",
      "Apreciadores que buscam descobertas e ritual.",
      "/canonical/figma/phase2/s15-angle-2.png",
    ],
    [
      "OFERTA",
      "Kit Degustação · R$ 149",
      "Quatro cafés de regiões do Brasil.",
      "/canonical/figma/phase2/s15-output.png",
    ],
    [
      "OBJETIVO",
      "120 pedidos em 14 dias",
      "Impulsionar pedidos qualificados.",
      "",
    ],
  ];
  const angles = [
    [
      "ÂNGULO 01",
      "A origem muda o sabor",
      "/canonical/figma/phase2/s15-angle-1.png",
    ],
    [
      "ÂNGULO 02",
      "Quatro cafés, quatro territórios",
      "/canonical/figma/phase2/s15-angle-2.png",
    ],
    [
      "ÂNGULO 03",
      angleVersion
        ? "Uma viagem sensorial sem sair de casa"
        : "Seu ritual atravessa o Brasil",
      "/canonical/figma/phase2/s15-angle-3.png",
    ],
  ];
  const outputs = [
    ["CARROSSEL", "Descoberta das origens"],
    ["STORIES", "Bastidores e ritual"],
    ["POST DE OFERTA", "Kit Degustação R$ 149"],
    ["UGC SCRIPT", "Roteiro para comunidade"],
  ];
  return (
    <section className="cx-world-approved">
      <div className="cx-world-title">
        <div>
          <small>
            Projetos <b>/</b> O Brasil cabe em uma xícara
          </small>
          <h1>O Brasil cabe em uma xícara</h1>
        </div>
        <Chip tone="orange">Em produção</Chip>
        <span>24 mai – 07 jun</span>
        <div />
        <Button
          tone="primary"
          icon={Check}
          actionId="DIRECTION-APPROVE"
          onClick={() => setApproved(!approved)}
        >
          {approved ? "Direção aprovada" : "Aprovar direção"}
        </Button>
        <Button
          icon={Sparkles}
          actionId="CAMPAIGN-EXPLORE-ANGLE"
          onClick={() => setAngleVersion((value) => value + 1)}
        >
          {angleVersion ? "Novo ângulo aplicado" : "Explorar outro ângulo"}
        </Button>
      </div>
      <CampaignTabs id={id} navigate={navigate} active="Direção" />
      <div className="cx-world-subtabs">
        <button
          className="is-active"
          disabled
          title="Você já está no Mundo da campanha."
        >
          Mundo
        </button>
        <button
          data-action-id="CAMPAIGN-OPEN-MOODBOARD"
          onClick={() => navigate(`/campaigns/${id}/moodboard`)}
        >
          Moodboard
        </button>
      </div>
      <div className="cx-world-approved-layout">
        <main>
          <header>
            <h2>Mundo da campanha</h2>
            <p>A blueprint que mantém todas as peças no mesmo universo.</p>
          </header>
          <div className="cx-world-blueprint">
            <section>
              <small>Fontes (Entradas)</small>
              {inputs.map(([eyebrow, title, text, image]) => (
                <article key={eyebrow}>
                  <div>
                    <b>{eyebrow}</b>
                    <strong>{title}</strong>
                    <p>{text}</p>
                  </div>
                  {image && <img src={image} />}
                </article>
              ))}
            </section>
            <ArrowRight />
            <section className="cx-world-concept">
              <small>Ideia-mãe (Conceito central)</small>
              <article>
                <img src="/canonical/figma/phase2/s15-concept.png" />
                <div>
                  <h2>
                    O Brasil cabe
                    <br />
                    em uma xícara.
                  </h2>
                  <p>
                    Quatro territórios.
                    <br />
                    Uma experiência.
                  </p>
                  <Chip tone="orange">Direção ativa</Chip>
                </div>
              </article>
            </section>
            <ArrowRight />
            <section>
              <small>Expressões (Ângulos e saídas)</small>
              {angles.map(([eyebrow, title, image]) => (
                <article key={eyebrow}>
                  <div>
                    <b>{eyebrow}</b>
                    <strong>{title}</strong>
                  </div>
                  <img src={image} />
                </article>
              ))}
            </section>
            <ArrowRight />
            <section>
              <small>Saídas (Exemplos)</small>
              {outputs.map(([eyebrow, title], i) => (
                <article key={eyebrow}>
                  <div>
                    <b>{eyebrow}</b>
                    <strong>{title}</strong>
                  </div>
                  <img src={angles[i % 3][2]} />
                </article>
              ))}
            </section>
          </div>
          <div className="cx-coherence-line">
            <h3>Linha de coerência</h3>
            <div>
              {[
                [
                  "1 Contexto",
                  "Festival, comportamento e desejo de descoberta.",
                ],
                ["2 Narrativa", "Quatro territórios. Uma experiência."],
                ["3 Expressão", "Ângulos que traduzem a ideia central."],
                ["4 Peças", "Formatos que entregam a ideia com consistência."],
              ].map(([title, text], i) => (
                <React.Fragment key={title}>
                  <article className={i === 2 ? "is-active" : ""}>
                    <b>{title}</b>
                    <small>{text}</small>
                  </article>
                  {i < 3 && <ArrowRight />}
                </React.Fragment>
              ))}
            </div>
          </div>
          <div className="cx-quality-gate">
            <small>Portão de qualidade atual</small>
            <b>
              {approved ? "Direção aprovada" : "Direção pronta para aprovação"}
            </b>
          </div>
        </main>
        <aside>
          <h3>Fundação da direção</h3>
          {[
            ["PROMESSA", "Descobrir origens brasileiras em casa."],
            ["PROVA", "Produtores, origem e notas informados pela marca."],
            ["EMOÇÃO", "Descoberta"],
            ["CTA", "Conheça as quatro origens"],
            ["MEMÓRIA DE MARCA", "v4"],
          ].map(([a, b]) => (
            <div className="cx-foundation-item" key={a}>
              <small>{a}</small>
              <p>{b}</p>
            </div>
          ))}
          <hr />
          <h3>Pilares de coerência</h3>
          <div className="cx-pillar-row">
            <span>Origem brasileira</span>
            <span>Ritual em casa</span>
            <span>Produtor e território</span>
          </div>
          <div className="cx-do-dont">
            <div>
              <b>DEVE</b>
              <p>
                ✓ Fotografia tátil
                <br />✓ Fonte editorial
                <br />✓ Produto real
              </p>
            </div>
            <div>
              <b>NÃO DEVE</b>
              <p>
                × Inventar prêmio
                <br />× Exotizar produtor
                <br />× Usar clichê turístico
              </p>
            </div>
          </div>
          <hr />
          <h3>Decisões registradas</h3>
          {["Conceito aprovado", "Promessa definida", "Ângulos validados"].map(
            (x, i) => (
              <p className="cx-decision" key={x}>
                <i className={i === 1 ? "is-active" : ""} />
                <span>{x}</span>
                <small>
                  {["Lucas · há 2d", "Mariana · há 1d", "João · há 6h"][i]}
                </small>
              </p>
            ),
          )}
          <Button actionId="CAMPAIGN-OPEN-MOODBOARD" onClick={() => navigate(`/campaigns/${id}/moodboard`)}>
            Abrir Moodboard
          </Button>
          <Button
            tone="primary"
            actionId="CAMPAIGN-CREATE-PIECE"
            onClick={() => navigate("/content/draft/edit?mode=visual")}
          >
            Criar primeira peça
          </Button>
        </aside>
      </div>
    </section>
  );
}
function MoodboardSurface({ navigate, pathname }: AnyRecord) {
  const id = pathname.split("/")[2];
  const [filter, setFilter] = React.useState("Todos");
  const [applied, setApplied] = React.useState(false);
  const [query, setQuery] = React.useState("");
  const [shared, setShared] = React.useState(false);
  const [added, setAdded] = React.useState(false);
  const refs = [
    [
      "Produto + ritual",
      "Produto",
      "/canonical/figma/phase2/s16-product-ritual.png",
    ],
    [
      "Gente real, luz quente",
      "Pessoas",
      "/canonical/figma/phase2/s16-people.png",
    ],
    [
      "Ritmo editorial",
      "Tipografia",
      "/canonical/figma/phase2/s16-editorial.png",
    ],
    ["Textura e origem", "Produto", "/canonical/figma/phase2/s16-texture.png"],
    [
      "Tipografia condensada",
      "Tipografia",
      "/canonical/figma/phase2/s16-typography.png",
    ],
    ["Cultura", "Atmosfera", "/canonical/figma/phase2/s16-culture.png"],
    ["Produto", "Produto", "/canonical/figma/phase2/s16-product.png"],
  ];
  const availableRefs = added
    ? [
        [
          "Nova referência editorial",
          "Atmosfera",
          "/canonical/figma/phase2/s16-culture.png",
        ],
        ...refs,
      ]
    : refs;
  const visible = availableRefs.filter(
    (reference) =>
      (filter === "Todos" || reference[1] === filter) &&
      reference[0].toLowerCase().includes(query.toLowerCase()),
  );
  return (
    <section className="cx-moodboard-approved">
      <div className="cx-moodboard-title">
        <div>
          <small>Campanha / O Brasil cabe em uma xícara</small>
          <h1>O Brasil cabe em uma xícara</h1>
          <p>Direção visual viva da campanha</p>
        </div>
        <Chip tone="orange">Em construção</Chip>
        <Button
          icon={shared ? Check : Share2}
          actionId="MOODBOARD-SHARE"
          onClick={() => setShared(!shared)}
        >
          {shared ? "Link copiado" : "Compartilhar"}
        </Button>
      </div>
      <div className="cx-moodboard-tabs">
        <button
          data-action-id="MOODBOARD-NAVIGATE"
          onClick={() => navigate(`/campaigns/${id}`)}
        >
          Visão geral
        </button>
        <button
          className="is-active"
          disabled
          title="Você já está no Moodboard."
        >
          Moodboard
        </button>
        <button
          data-action-id="MOODBOARD-NAVIGATE"
          onClick={() => navigate(`/campaigns/${id}/world`)}
        >
          Narrativa
        </button>
        <button data-action-id="MOODBOARD-NAVIGATE" onClick={() => navigate("/content")}>
          Peças
        </button>
      </div>
      <div className="cx-moodboard-layout">
        <main>
          <div className="cx-moodboard-head">
            <div>
              <h2>Referências da direção</h2>
              <p>{visible.length} referências selecionadas</p>
            </div>
            <label>
              <Search />
              <input
                data-action-id="MOODBOARD-SELECT-FILTER"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Buscar referências"
              />
            </label>
            <Button
              tone="primary"
              icon={added ? Check : Plus}
              actionId="MOODBOARD-ADD-REFERENCE"
              onClick={() => setAdded(!added)}
            >
              {added ? "Referência adicionada" : "Adicionar"}
            </Button>
          </div>
          <div className="cx-moodboard-filters">
            {[
              "Todos",
              "Atmosfera",
              "Produto",
              "Pessoas",
              "Tipografia",
              "Movimento",
            ].map((x) => (
              <button
                data-action-id="MOODBOARD-SELECT-FILTER"
                className={filter === x ? "is-active" : ""}
                onClick={() => setFilter(x)}
                key={x}
              >
                {x}
              </button>
            ))}
          </div>
          <div className="cx-masonry">
            {visible.map(([title, , image], i) => (
              <figure className={`item-${i % 7}`} key={title}>
                <img src={image} />
                <figcaption>
                  <b>{title}</b>
                  <small>{i === 2 ? "Em análise" : "Selecionada"}</small>
                </figcaption>
              </figure>
            ))}
          </div>
        </main>
        <aside>
          <h2>Direção visual</h2>
          <p>
            A campanha traduz brasilidade contemporânea sem cair em clichê.
            Café, encontro e movimento entram como linguagem — não como
            decoração.
          </p>
          <small>PRINCÍPIOS</small>
          {[
            "Humano antes de perfeito",
            "Quente, tátil e editorial",
            "Produto sempre integrado à cena",
            "Movimento com intenção",
          ].map((x, i) => (
            <p className="cx-mood-principle" key={x}>
              <i className={i ? "" : "is-coral"} />
              {x}
            </p>
          ))}
          <small>OBRIGATÓRIO</small>
          <p>
            • Presença do café ou ritual
            <br />• Contraste alto e leitura móvel
            <br />• Um ponto coral por peça
          </p>
          <small>EVITAR</small>
          <p>
            • Bandeira literal e excesso de verde
            <br />• Banco de imagens genérico
            <br />• Futurismo ou estética “IA”
          </p>
          <small>COBERTURA DA DIREÇÃO</small>
          {[
            ["Atmosfera", 88],
            ["Produto", 72],
            ["Pessoas", 54],
            ["Tipografia", 66],
            ["Movimento", 42],
          ].map(([x, v], i) => (
            <div className="cx-coverage" key={String(x)}>
              <span>{x}</span>
              <i>
                <em
                  className={i < 2 ? "is-coral" : ""}
                  style={{ width: `${v}%` }}
                />
              </i>
            </div>
          ))}
          <Button
            tone="primary"
            icon={applied ? Check : Sparkles}
            actionId="MOODBOARD-APPLY-DIRECTION"
            onClick={() => setApplied(!applied)}
          >
            {applied ? "Direção aplicada" : "Aplicar direção à campanha"}
          </Button>
        </aside>
      </div>
    </section>
  );
}

function BrandMemory({ data, demo, navigate }: AnyRecord) {
  const profile = data.activeWorkspace?.brandProfile;
  const score = demo ? 86 : profile?.readinessScore || 72;
  const [tab, setTab] = React.useState("Essência");
  const sections: Record<string, [string, string, string][]> = {
    Essência: [
      [
        "ESSÊNCIA",
        "Clareza para escolher o que importa",
        "A Café Aurora transforma pequenos rituais em momentos de presença, foco e conversa.",
      ],
      [
        "POSICIONAMENTO",
        "Café especial sem cerimônia",
        "Qualidade editorial e origem rastreável com linguagem acessível — sem elitismo ou excesso técnico.",
      ],
      [
        "DIFERENCIAIS",
        "Origem, ritual e design como uma só história",
        "Microlotes brasileiros, torra fresca, assinatura sensorial e uma experiência visual reconhecível.",
      ],
    ],
    Posicionamento: [
      [
        "TERRITÓRIO",
        "Origem brasileira contemporânea",
        "Cultura, procedência e produto real sem folclore ou clichê.",
      ],
      [
        "PROMESSA",
        "Descoberta acessível",
        "Especial sem cerimônia; sensorial sem elitismo.",
      ],
      [
        "PROVA",
        "Rastreabilidade e torra fresca",
        "Fontes, produtores e notas registrados na memória.",
      ],
    ],
    Oferta: [
      [
        "OFERTA PRINCIPAL",
        "Kit Degustação Grãos Raros",
        "Quatro origens brasileiras, R$ 149.",
      ],
      [
        "VALOR",
        "Descobrir em casa",
        "Produto, guia sensorial e ritual de preparo.",
      ],
      [
        "LIMITES",
        "Sem promessas inventadas",
        "Preço, estoque e prazos sempre vêm de fontes ativas.",
      ],
    ],
    Público: [
      [
        "PRIMÁRIO",
        "25–44 · café especial",
        "Pessoas que valorizam procedência e experiências em casa.",
      ],
      [
        "MOTIVAÇÃO",
        "Ritual e descoberta",
        "Buscam qualidade sem excesso técnico.",
      ],
      [
        "BARREIRA",
        "Elitismo percebido",
        "A linguagem precisa ser clara e acolhedora.",
      ],
    ],
    "Tom de voz": [
      [
        "VOZ",
        "Sensorial, clara, próxima",
        "Frases precisas, imagens táteis e ritmo calmo.",
      ],
      ["DEVE", "Convidar sem pressionar", "Explicar origem com humanidade."],
      [
        "EVITAR",
        "Urgência artificial",
        "Não soar solene, técnico demais ou genérico.",
      ],
    ],
    Identidade: [
      [
        "VISUAL",
        "Quente, tátil e editorial",
        "Alto contraste, produto real e um ponto coral.",
      ],
      [
        "TIPOGRAFIA",
        "Editorial com leitura móvel",
        "Hierarquia forte e textos curtos.",
      ],
      [
        "EVITAR",
        "Estética de banco ou IA",
        "Sem clichês turísticos e futurismo genérico.",
      ],
    ],
    Guardrails: [
      [
        "FONTE",
        "Creditar produtores e referências",
        "Toda alegação precisa apontar para evidência ativa.",
      ],
      [
        "PROIBIDO",
        "Não alegar premiações",
        "Nem exclusividade sem comprovação.",
      ],
      [
        "REVISÃO",
        "Humano antes de publicar",
        "A memória orienta; a decisão continua responsável.",
      ],
    ],
  };
  return (
    <section className="cx-memory-approved">
      <div className="cx-memory-approved-title">
        <div>
          <h1>Memória da marca</h1>
          <p>A base viva que orienta estratégia, criação e revisão.</p>
        </div>
        <Button
          icon={Clock3}
          actionId="BRAND-MEMORY-OPEN-HISTORY"
          onClick={() => navigate("/settings/ai-governance")}
        >
          Histórico
        </Button>
        <Button
          tone="primary"
          icon={Sparkles}
          actionId="BRAND-MEMORY-UPDATE"
          onClick={() => navigate("/settings/brand-memory")}
        >
          Atualizar
        </Button>
      </div>
      <div className="cx-memory-readiness">
        <div>
          <small>PRONTIDÃO DA MEMÓRIA</small>
          <strong>{score}%</strong>
        </div>
        <div>
          <p>A marca já consegue gerar conteúdo consistente.</p>
          <i>
            <em style={{ width: `${score}%` }} />
          </i>
        </div>
        <aside>
          <b>2 lacunas com impacto alto</b>
          <p>Provas sociais e limites de linguagem precisam de validação.</p>
        </aside>
      </div>
      <div className="cx-memory-tabs">
        {Object.keys(sections).map((x) => (
          <button
            data-action-id="BRAND-MEMORY-SELECT-SECTION"
            className={tab === x ? "is-active" : ""}
            onClick={() => setTab(x)}
            key={x}
          >
            {x}
          </button>
        ))}
      </div>
      <div className="cx-memory-approved-layout">
        <main>
          {sections[tab].map(([eyebrow, title, text]) => (
            <article key={eyebrow}>
              <div>
                <small>{eyebrow}</small>
                <h2>{title}</h2>
                <p>{text}</p>
              </div>
              <Chip tone="green">Validado</Chip>
            </article>
          ))}
          <div className="cx-content-pillars">
            <small>PILARES DE CONTEÚDO</small>
            <div>
              {[
                ["Ritual cotidiano", "35%"],
                ["Origem brasileira", "25%"],
                ["Foco e criatividade", "25%"],
                ["Produto e prova", "15%"],
              ].map(([x, v]) => (
                <article key={x}>
                  <b>{x}</b>
                  <strong>{v}</strong>
                  <small>Ativo nas gerações</small>
                </article>
              ))}
            </div>
          </div>
          <footer>
            <Button
              actionId="BRAND-MEMORY-EDIT-SECTION"
              onClick={() => navigate("/settings/brand-memory")}
            >
              Editar esta seção
            </Button>
            <span>Última atualização há 2 dias por Mariana</span>
          </footer>
        </main>
        <aside>
          <h2>Usado agora</h2>
          <p>Esta memória influencia as próximas gerações.</p>
          {[
            [Radar, "Radar", "Relevância e adequação"],
            [FolderKanban, "Campanhas", "Ângulos e narrativa"],
            [Palette, "Editor", "Tom, visual e guardrails"],
            [Check, "Revisão", "Critérios de qualidade"],
          ].map(([Icon, title, text]: any) => (
            <article key={title}>
              <Icon />
              <div>
                <b>{title}</b>
                <small>{text}</small>
              </div>
            </article>
          ))}
          <small>FONTES ATIVAS</small>
          <p>12 documentos · 34 respostas · 8 aprovações</p>
          <StateBanner
            tone="orange"
            title="A busca da memória está ativa"
            detail="Última indexação hoje, 09:42"
          />
          <small>INFLUÊNCIA</small>
          {[
            ["Estratégia", 88],
            ["Criação", 80],
            ["Revisão", 73],
          ].map(([x, v], i) => (
            <div className="cx-memory-influence" key={String(x)}>
              <span>{x}</span>
              <i>
                <em
                  className={i ? "" : "is-coral"}
                  style={{ width: `${v}%` }}
                />
              </i>
            </div>
          ))}
          <Button
            actionId="BRAND-MEMORY-OPEN-SOURCES"
            onClick={() => navigate("/settings/brand-memory/sources")}
          >
            Ver fontes, mudanças e responsáveis
          </Button>
        </aside>
      </div>
    </section>
  );
}

function ApprovedLibrarySurface({ data, navigate, setToast }: AnyRecord) {
  const demoAssets = [
    ["Ritual de foco 01", "Post · 4 usos", phase3Arts[0], "demo-0"],
    ["Aurora — UGC", "UGC · 2 usos", phase3Arts[1], "demo-1"],
    ["Carrossel tipográfico", "Carrossel · 3 usos", phase3Arts[2], "demo-2"],
    ["Origem e textura", "Foto · 5 usos", phase3Arts[4], "demo-3"],
    ["Oferta espresso", "Produto · licenciado", phase3Arts[3], "demo-4"],
    ["Produto limpo", "Produto · próprio", phase3Arts[5], "demo-5"],
    ["Textura Cerrado", "Referência · interna", phase3Arts[4], "demo-6"],
    ["Fumaça e movimento", "Referência · licenciada", phase3Arts[0], "demo-7"],
  ];
  const persistedAssets = (data.snapshot?.assets || [])
    .filter((asset: AnyRecord) => asset.type === "image")
    .map((asset: AnyRecord) => [
      asset.title,
      asset.metadata?.sourceAssetId ? "Derivação · revisão pendente" : "Imagem privada",
      null,
      asset.id,
    ]);
  const assets = persistedAssets.length ? persistedAssets : demoAssets;
  const [selected, setSelected] = React.useState(0);
  const [query, setQuery] = React.useState("");
  const [deleted, setDeleted] = React.useState(false);
  const [libraryTab, setLibraryTab] = React.useState("Arquivos");
  const visible = assets.filter((x) =>
    String(x[0]).toLowerCase().includes(query.toLowerCase()),
  );
  const current = assets[selected] || assets[0];
  const selectedRecord = data.snapshot?.assets?.find(
    (asset: AnyRecord) => asset.id === current?.[3],
  );
  const [privatePreview, setPrivatePreview] = React.useState("");
  React.useEffect(() => {
    if (!selectedRecord?.id) {
      setPrivatePreview("");
      return;
    }
    let objectUrl = "";
    let currentRequest = true;
    void productApi
      .studioAssetBlob(selectedRecord.id)
      .then((blob) => {
        if (!currentRequest) return;
        objectUrl = URL.createObjectURL(blob);
        setPrivatePreview(objectUrl);
      })
      .catch(() => currentRequest && setPrivatePreview(""));
    return () => {
      currentRequest = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [selectedRecord?.id]);
  return (
    <section className="cx-library-approved">
      <header>
        <div>
          <h1>Biblioteca</h1>
          <p>Tudo o que a marca pode reutilizar, adaptar e provar.</p>
        </div>
        <Button actionId="LIBRARY-UPLOAD" icon={Upload} onClick={() => setToast("Upload preparado")}>
          Upload
        </Button>
        <Button tone="primary" icon={Plus}>
          Criar modelo
        </Button>
      </header>
      <nav>
        {["Arquivos", "Modelos", "Marca", "Campanhas", "Linhagem"].map(
          (x) => (
            <button
              data-action-id="LIBRARY-SELECT-FILTER"
              className={libraryTab === x ? "is-active" : ""}
              aria-pressed={libraryTab === x}
              onClick={() => setLibraryTab(x)}
              key={x}
            >
              {x}
            </button>
          ),
        )}
      </nav>
      <div className="cx-library-toolbar">
        <label>
          <Search />
          <input
            data-action-id="LIBRARY-SELECT-FILTER"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Buscar por nome, campanha, uso ou direito..."
          />
        </label>
        <Button>Filtros 3</Button>
        <Button>Mais recentes⌄</Button>
      </div>
      <div className="cx-library-layout">
        <main>
          {deleted ? (
            <EmptyState
              title="Arquivo removido da visão"
              detail="A exclusão foi aplicada apenas à demonstração."
              action="Desfazer"
              onAction={() => setDeleted(false)}
            />
          ) : (
            <>
              <div className="cx-library-section-head">
                <h2>Usados na campanha Aurora</h2>
                <button
                  data-action-id="LIBRARY-OPEN-CAMPAIGN"
                  onClick={() => navigate("/campaigns/campaign-aurora")}
                >
                  Ver campanha
                </button>
              </div>
              <div className="cx-library-used">
                {visible.slice(0, 4).map((asset, i) => (
                  <button
                    data-action-id="LIBRARY-SELECT-ASSET"
                    className={selected === i ? "is-active" : ""}
                    onClick={() => setSelected(i)}
                    key={asset[0]}
                  >
                    {asset[2] ? <img src={String(asset[2])} /> : <span className="cx-private-thumb"><Image /></span>}
                    <b>{asset[0]}</b>
                    <small>{asset[1]}</small>
                  </button>
                ))}
              </div>
              <div className="cx-library-section-head">
                <h2>Ativos da marca</h2>
                <span>28 arquivos</span>
              </div>
              <div className="cx-library-assets">
                {visible.slice(4).map((asset, i) => (
                  <button
                    data-action-id="LIBRARY-SELECT-ASSET"
                    onClick={() => setSelected(i + 4)}
                    key={asset[0]}
                  >
                    {asset[2] ? <img src={String(asset[2])} /> : <span className="cx-private-thumb"><Image /></span>}
                    <b>{asset[0]}</b>
                    <small>{asset[1]}</small>
                  </button>
                ))}
              </div>
              <h2>Referências recentes</h2>
              <article className="cx-library-reference">
                <img src={phase3Arts[1]} />
                <span>
                  <b>Direção humana — cenas cotidianas</b>
                  <small>Moodboard Aurora · adicionada hoje por João</small>
                </span>
                <Chip tone="green">Uso interno</Chip>
                <button
                  data-action-id="HOME-OPEN-MOODBOARD"
                  onClick={() => navigate("/campaigns/campaign-aurora/moodboard")}
                >
                  Abrir
                </button>
              </article>
            </>
          )}
        </main>
        <aside>
          <h2>{current[0]}</h2>
          <p>Imagem selecionada</p>
          <div className="cx-library-preview">
            {privatePreview || current[2] ? (
              <img src={privatePreview || String(current[2])} />
            ) : (
              <span className="cx-private-thumb"><Image /></span>
            )}
            <Chip tone="orange">EM USO</Chip>
          </div>
          <small>DETALHES</small>
          <KeyValue label="Tipo" value="Imagem 1080 × 1350" />
          <KeyValue label="Campanha" value="Aurora — Copa" />
          <KeyValue label="Direitos" value="Licença comercial" />
          <small>USOS E LINHAGEM</small>
          <article>
            <b>Carrossel Ritual de foco</b>
            <small>3 variações · 2 publicadas</small>
            <button
              data-action-id="CONTENT-OPEN-DETAIL"
              onClick={() => navigate("/content/post-ritual")}
            >
              Abrir
            </button>
          </article>
          <KeyValue label="Origem" value="Moodboard / Ref. 04" />
          <KeyValue label="Alterações" value="Corte, contraste, texto" />
          <Button
            tone="primary"
            actionId="LIBRARY-OPEN-IMAGE-LAB"
            disabled={Boolean(selectedRecord && !selectedRecord.checksumSha256)}
            title={selectedRecord && !selectedRecord.checksumSha256 ? "Este asset ainda não possui checksum verificável" : undefined}
            onClick={() =>
              navigate(
                `/library/assets/${encodeURIComponent(String(current[3]))}/edit?mode=image&returnTo=${encodeURIComponent("/library/assets")}`,
              )
            }
          >
            Editar imagem sem alterar original
          </Button>
          <Button
            actionId="LIBRARY-INSERT-EDITOR"
            onClick={() =>
              navigate(
                `/content/post-ritual/edit?mode=visual&asset=${encodeURIComponent(String(current[3]))}`,
              )
            }
          >
            Inserir no editor
          </Button>
          <Button actionId="HOME-OPEN-REUSE" onClick={() => navigate("/content/post-ritual/remix")}>
            Criar variação com contexto
          </Button>
          <button
            className="cx-delete-asset"
            data-action-id="LIBRARY-DELETE-ASSET"
            onClick={() => setDeleted(true)}
          >
            Excluir arquivo
          </button>
        </aside>
      </div>
    </section>
  );
}

function LibrarySurface({ data, demo, navigate }: AnyRecord) {
  const assets = demo
    ? [
        { id: "a1", title: "Luz da manhã", type: "image", url: demoMedia.hero },
        {
          id: "a2",
          title: "Grãos de origem",
          type: "image",
          url: demoMedia.beans,
        },
        {
          id: "a3",
          title: "Preparo coado",
          type: "image",
          url: demoMedia.pour,
        },
        { id: "a4", title: "Mesa Aurora", type: "image", url: demoMedia.table },
      ]
    : data.snapshot?.assets || [];
  const [assetFilter, setAssetFilter] = React.useState("Todos");
  const [assetQuery, setAssetQuery] = React.useState("");
  const filteredAssets = assets.filter(
    (asset: AnyRecord) =>
      (assetFilter === "Todos" ||
        (assetFilter === "Imagens" && asset.type === "image") ||
        (assetFilter === "Vídeos" && asset.type === "video")) &&
      (!assetQuery || asset.title?.toLowerCase().includes(assetQuery.toLowerCase())),
  );
  return (
    <Page
      eyebrow="Biblioteca"
      title="Assets"
      description="Mídia organizada para encontrar, reutilizar e manter consistência."
      actions={
        <Button tone="primary" icon={Upload}>
          Enviar arquivos
        </Button>
      }
    >
      <div className="cx-toolbar">
        <div className="cx-filter-row">
          {["Todos", "Imagens", "Vídeos", "Logos", "Documentos"].map((item) => (
            <button
              data-action-id="LIBRARY-SELECT-FILTER"
              className={assetFilter === item ? "is-active" : ""}
              aria-pressed={assetFilter === item}
              onClick={() => setAssetFilter(item)}
              key={item}
            >
              {item}
            </button>
          ))}
        </div>
        <label>
          <Search />
          <input
            data-action-id="LIBRARY-SELECT-FILTER"
            placeholder="Buscar por nome ou tag"
            value={assetQuery}
            onChange={(event) => setAssetQuery(event.target.value)}
          />
        </label>
      </div>
      {filteredAssets.length ? (
        <div className="cx-assets">
          {filteredAssets.map((asset: AnyRecord, i: number) => (
            <button
              data-action-id="LIBRARY-INSERT-EDITOR"
              key={asset.id}
              onClick={() => navigate("/content/draft/edit?mode=visual")}
            >
              <div>
                {asset.url ? <img src={asset.url} /> : <FileText />}
                <span>
                  <MoreHorizontal />
                </span>
              </div>
              <b>{asset.title}</b>
              <small>
                {asset.type} · {i % 2 ? "Campanha Aurora" : "Marca"}
              </small>
            </button>
          ))}
        </div>
      ) : (
        <EmptyState
          title="Sua biblioteca está vazia"
          detail="Envie a primeira imagem ou crie uma peça na Fábrica."
          action="Abrir Fábrica"
          onAction={() => navigate("/factory")}
        />
      )}
    </Page>
  );
}

function AnalyticsSurface({ data, demo, navigate }: AnyRecord) {
  const metrics = data.snapshot?.analytics?.metrics || [];
  return (
    <Page
      eyebrow="Aprendizado"
      title="O que funcionou — e por quê"
      description="Resultados transformados em decisões para a próxima criação."
      actions={<Button icon={CalendarDays}>Últimos 30 dias</Button>}
    >
      <div className="cx-kpi-grid">
        {[
          ["Alcance", metrics[0]?.value || "184 mil", "+18%"],
          ["Engajamento", metrics[1]?.value || "6,8%", "+1,2 p.p."],
          ["Salvamentos", metrics[2]?.value || "4.280", "+31%"],
          ["Conversões", metrics[3]?.value || "392", "+12%"],
        ].map(([a, b, c]) => (
          <article key={a}>
            <small>{a}</small>
            <strong>{String(b)}</strong>
            <Chip tone="green">{c}</Chip>
          </article>
        ))}
      </div>
      <div className="cx-analytics-grid">
        <section>
          <SectionHead title="Desempenho por semana" />
          <div className="cx-chart">
            <div className="cx-chart-grid" />
            <svg viewBox="0 0 600 210" preserveAspectRatio="none">
              <path d="M0,170 C80,175 85,110 155,122 S240,85 310,100 S400,35 470,65 S550,28 600,35" />
              <path
                className="area"
                d="M0,170 C80,175 85,110 155,122 S240,85 310,100 S400,35 470,65 S550,28 600,35 L600,210 L0,210Z"
              />
            </svg>
            <div className="cx-chart-labels">
              <span>20 jul</span>
              <span>27 jul</span>
              <span>03 ago</span>
              <span>10 ago</span>
              <span>17 ago</span>
            </div>
          </div>
        </section>
        <aside>
          <small>MELHOR SINAL</small>
          <img src={demoMedia.hero} />
          <h3>Textura + frase curta</h3>
          <p>
            Peças com uma imagem tátil e menos de 9 palavras no título tiveram
            1,8× mais salvamentos.
          </p>
          <Button
            actionId="POST-OPEN-REUSE"
            onClick={() => navigate("/content/post-ritual/remix")}
          >
            Reutilizar aprendizado
          </Button>
        </aside>
      </div>
      <SectionHead title="Aprendizados acionáveis" />
      <div className="cx-learning-list">
        {[
          ["01", "Abra com uma tensão cotidiana", "+23% retenção"],
          ["02", "Mostre mãos, não poses", "+31% salvamentos"],
          ["03", "Publique antes das 9h30", "+18% alcance"],
        ].map(([n, t, m]) => (
          <article key={n}>
            <span>{n}</span>
            <div>
              <h3>{t}</h3>
              <p>
                Baseado em conteúdo publicado e sinais observados no período.
              </p>
            </div>
            <Chip tone="green">{m}</Chip>
            <button
              data-action-id="POST-OPEN-REUSE"
              onClick={() => navigate("/content/post-ritual/remix")}
            >
              <ArrowRight />
            </button>
          </article>
        ))}
      </div>
    </Page>
  );
}

async function factoryRoundIdFor(
  workspaceId: string,
  sourcePostId: string | null,
  derivativeIds: string[],
) {
  const identity = JSON.stringify({
    workspaceId,
    sourcePostId,
    derivativeIds: [...new Set(derivativeIds)].sort(),
  });
  const digest = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(identity),
  );
  const fingerprint = Array.from(new Uint8Array(digest))
    .map((value) => value.toString(16).padStart(2, "0"))
    .join("")
    .slice(0, 32);
  return `round-${fingerprint}`;
}

function ApprovedFactorySurface({
  data,
  demo,
  navigate,
  pathname,
  params,
  setToast,
  brand,
  workspace,
}: AnyRecord) {
  const routeRoundId = pathname.startsWith("/factory/")
    ? pathname.split("/")[2]
    : undefined;
  const persistedRound = data.snapshot?.factoryRounds?.find(
    (item: AnyRecord) => item.resourceKey === routeRoundId,
  );
  const [localRound, setLocalRound] = React.useState<AnyRecord>();
  const [starting, setStarting] = React.useState(false);
  const [factoryError, setFactoryError] = React.useState("");
  const roundPayload = localRound || persistedRound?.payload;
  const derivativeIds = String(params.get("derivatives") || "")
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean);
  const linkedDerivativeIds: string[] = derivativeIds.length
    ? derivativeIds
    : Array.isArray(roundPayload?.derivativeIds)
      ? roundPayload.derivativeIds
      : [];
  const sourcePostId = params.get("source") || roundPayload?.sourcePostId || null;
  const sourcePost = data.snapshot?.posts?.find(
    (item: AnyRecord) => item.id === sourcePostId,
  );
  const sourceCampaign = data.snapshot?.campaigns?.find(
    (item: AnyRecord) => item.id === sourcePost?.campaignId,
  );
  const derivativePosts = linkedDerivativeIds
    .map((postId) =>
      data.snapshot?.posts?.find((item: AnyRecord) => item.id === postId),
    )
    .filter(Boolean);
  const derivativeLineage = derivativePosts
    .map((post: AnyRecord) =>
      post.versions?.find(
        (version: AnyRecord) => version.lineage?.sourcePostId === sourcePostId,
      )?.lineage,
    )
    .filter(Boolean);
  const preservedDecisions = [
    ...new Set(
      derivativeLineage.flatMap((lineage: AnyRecord) => lineage.preserve || []),
    ),
  ];
  const adaptedDecisions = [
    ...new Set(
      derivativeLineage.flatMap((lineage: AnyRecord) => lineage.adapt || []),
    ),
  ];
  const observedHypothesis = derivativeLineage.find(
    (lineage: AnyRecord) => lineage.hypothesis,
  )?.hypothesis;
  const cells: AnyRecord[] = Array.isArray(roundPayload?.cells)
    ? roundPayload.cells
    : [];
  const reviewableCells = cells.filter(
    (cell) => cell.documentId && cell.versionNumber,
  );
  const canStart = demo || derivativeIds.length > 0;

  const startRound = async () => {
    if (starting) return;
    if (demo) {
      const demoRound = {
        schemaVersion: "clicko.factory-round.v1",
        id: "round-demo",
        status: "review_required",
        cells: [{ postId: "post-ritual", documentId: "demo-document", versionNumber: 1 }],
      };
      setLocalRound(demoRound);
      setToast("Rodada demonstrativa preparada");
      navigate("/factory/round-demo");
      return;
    }
    if (!workspace?.id || derivativeIds.length === 0) {
      setFactoryError("Envie ao menos uma derivação do Reuse Lab antes de iniciar a rodada.");
      return;
    }

    setStarting(true);
    setFactoryError("");
    let roundId: string;
    try {
      roundId = await factoryRoundIdFor(
        workspace.id,
        params.get("source"),
        derivativeIds,
      );
    } catch (error) {
      setFactoryError(
        error instanceof Error
          ? error.message
          : "Não foi possível identificar esta rodada.",
      );
      setStarting(false);
      return;
    }
    const existingRound = data.snapshot?.factoryRounds?.find(
      (item: AnyRecord) => item.resourceKey === roundId,
    );
    if (existingRound?.payload) {
      setLocalRound(existingRound.payload);
      setToast("Rodada existente recuperada sem duplicar versões ou jobs");
      navigate(`/factory/${roundId}`);
      setStarting(false);
      return;
    }
    const nextCells: AnyRecord[] = [];
    for (const postId of derivativeIds) {
      const post = data.snapshot?.posts?.find((item: AnyRecord) => item.id === postId);
      try {
        const existingDocuments = await productApi.studioDocuments(workspace.id, { postId });
        let document = existingDocuments.find(
          (item) => item.contentType === "visual" || item.contentType === "carousel",
        );
        if (!document) {
          const title = post?.title || `Derivação ${postId.slice(0, 8)}`;
          document = await productApi.createStudioDocument({
            workspaceId: workspace.id,
            title,
            contentType: "visual",
            campaignId: post?.campaignId ?? null,
            postId,
            opportunityId: null,
            brandRevision: 1,
            brief: {
              schemaVersion: "studio.creative-brief.v1",
              objective: post?.objective || "Preparar derivação para revisão humana",
              audience: "Audiência definida no conteúdo de origem",
              angle: "",
              promise: "",
              hook: post?.copy || title,
              cta: "Revisar antes de publicar",
              channel: post?.platform || "instagram",
              format: post?.format || "post",
              tone: "coerente com a memória da marca",
              restrictions: [],
              hypotheses: [],
              evidence: [],
            },
            composition: {
              pages: [
                {
                  id: "page-1",
                  role: "content",
                  width: 1080,
                  height: 1350,
                  safeArea: 76,
                  background: "#10181c",
                  durationMs: null,
                  layers: [
                    {
                      id: "page-1-headline",
                      kind: "text",
                      name: title,
                      x: 90,
                      y: 120,
                      width: 900,
                      height: 540,
                      rotation: 0,
                      opacity: 1,
                      visible: true,
                      locked: false,
                      zIndex: 1,
                      properties: {
                        type: "text",
                        text: post?.copy || title,
                        fontSize: 76,
                        minFontSize: 24,
                        fontFamily: "DejaVu Sans",
                        fontWeight: "bold",
                        color: "#ffffff",
                        align: "left",
                        lineHeight: 0.95,
                      },
                    },
                  ],
                },
              ],
              narrative: {
                sourcePostId: postId,
                factoryRoundId: roundId,
              },
              tracks: [],
            },
            assets: [],
            correlationId: `${roundId}:${postId}`,
          });
        }
        const version = await productApi.createStudioVersion(
          document.documentId,
          `Entrada da rodada ${roundId}`,
        );
        const job = await productApi.enqueueStudioGenerationJob(
          {
            workspaceId: workspace.id,
            documentId: document.documentId,
            jobType: "document_snapshot",
            provider: "builtin.snapshot",
            request: { roundId, postId, purpose: "factory_preflight" },
            correlationId: `${roundId}:${postId}`,
          },
          `factory:${roundId}:${postId}:snapshot`,
        );
        nextCells.push({
          postId,
          title: post?.title || document.title,
          documentId: document.documentId,
          versionNumber: version.version,
          jobId: job.id,
          status: job.status,
          gate: "human_review",
        });
      } catch (error) {
        nextCells.push({
          postId,
          title: post?.title || `Derivação ${postId.slice(0, 8)}`,
          status: "blocked",
          gate: "document_or_job_failed",
          error: error instanceof Error ? error.message : "Falha ao preparar a célula",
        });
      }
    }

    const payload = {
      schemaVersion: "clicko.factory-round.v1",
      id: roundId,
      sourcePostId: params.get("source"),
      derivativeIds,
      status: nextCells.some((cell) => cell.status === "blocked")
        ? "partially_blocked"
        : "queued",
      cells: nextCells,
      createdAt: new Date().toISOString(),
      humanGates: ["brand_review", "publication_approval"],
    };
    try {
      await data.saveWorkspaceResource("factory_round", roundId, payload);
      setLocalRound(payload);
      const queued = nextCells.filter((cell) => cell.jobId).length;
      setToast(`${queued} células fixadas e enfileiradas`);
      navigate(`/factory/${roundId}`);
    } catch (error) {
      setFactoryError(
        error instanceof Error ? error.message : "Não foi possível persistir a rodada.",
      );
    } finally {
      setStarting(false);
    }
  };
  const isHorizonte = brand?.id === "horizonte";
  const factoryInputs: Array<[
    React.ComponentType<AnyRecord>,
    string,
    string,
    string,
  ]> = demo
    ? [
        [Radar, "Oportunidade", isHorizonte ? "+42% prevenção" : "+38% ritual de foco", "pronto"],
        [Target, "Oferta", isHorizonte ? "Check-up integrado" : "Kit quatro origens", "pronto"],
        [FileText, "Briefing", "Promessa e guardrails validados", "pronto"],
        [BarChart3, "Vencedor", isHorizonte ? "2,6× compartilhamentos" : "3× mais salvamentos", "pronto"],
      ]
    : [
        [FileText, "Conteúdo de origem", sourcePost?.title || "Não vinculado", sourcePost ? "observado" : "ausente"],
        [Target, "Objetivo", sourcePost?.objective || "Não informado", sourcePost?.objective ? "observado" : "ausente"],
        [Radar, "Campanha", sourceCampaign?.name || "Não vinculada", sourceCampaign ? "observado" : "ausente"],
        [BarChart3, "Derivações", `${linkedDerivativeIds.length} vinculadas`, linkedDerivativeIds.length ? "observado" : "ausente"],
      ];
  const recipeSteps = demo
    ? ["Tensão real", "Prova da marca", "Formato certo", "CTA responsável"]
    : [
        ...preservedDecisions.map((item) => `Preservar: ${item}`),
        ...adaptedDecisions.map((item) => `Adaptar: ${item}`),
      ].slice(0, 4);
  const decisionCells = demo
    ? [
        { title: "Cenário do vídeo", detail: "Aceitar consultório com luz natural?", urgency: "Alta", postId: "post-ritual" },
        { title: "Contraste do slide 04", detail: "Texto está abaixo do mínimo da marca.", urgency: "Média", postId: "post-ritual" },
        { title: "Cadência de sábado", detail: "Dois conteúdos disputam o mesmo horário.", urgency: "Média", postId: "post-ritual", calendar: true },
      ]
    : cells.map((cell) => ({
        title:
          cell.status === "blocked"
            ? `Corrigir ${cell.title || "célula bloqueada"}`
            : `Revisar ${cell.title || "versão fixa"}`,
        detail:
          cell.status === "blocked"
            ? cell.error || "A preparação desta célula falhou."
            : `Documento ${String(cell.documentId).slice(0, 8)} · versão ${cell.versionNumber}`,
        urgency: cell.status === "blocked" ? "Bloqueada" : "Revisão",
        postId: cell.postId,
        blocked: cell.status === "blocked",
      }));
  const destinationCounts = derivativePosts.reduce(
    (counts: Record<string, number>, post: AnyRecord) => {
      const destination = post.platform || post.format || "Destino não informado";
      counts[destination] = (counts[destination] || 0) + 1;
      return counts;
    },
    {},
  );
  const factoryVisuals = isHorizonte
    ? [
        "/canonical/brands/horizonte/signal.svg",
        "/canonical/brands/horizonte/winner.svg",
        "/canonical/brands/horizonte/campaign.svg",
      ]
    : [phase3Arts[2], phase3Arts[4], phase3Arts[0]];
  const factoryCells = cells.length
    ? cells.map((cell, index) => ({
        title: cell.title || `Derivação ${index + 1}`,
        format: "Documento canônico · versão fixa",
        progress:
          cell.status === "blocked"
            ? "Preparação bloqueada"
            : `Job ${cell.status || "queued"}`,
        gate:
          cell.status === "blocked"
            ? "CORREÇÃO NECESSÁRIA"
            : "REVISÃO HUMANA",
        destination: "Revisão em lote",
        percent: cell.status === "succeeded" ? 100 : cell.status === "blocked" ? 0 : 24,
      }))
    : linkedDerivativeIds.length
      ? linkedDerivativeIds.map((postId, index) => ({
          title:
            data.snapshot?.posts?.find((post: AnyRecord) => post.id === postId)?.title ||
            `Derivação ${index + 1}`,
          format: "Entrada selecionada",
          progress: "Aguardando início da rodada",
          gate: "PRÉ-FLIGHT",
          destination: "Documento do Studio",
          percent: 0,
        }))
      : demo
        ? [
          {
            title: "Carrossel de autoridade",
            format: "6 slides · 4:5",
            progress: "Demonstração de montagem",
            gate: "REVISÃO HUMANA",
            destination: "Instagram",
            percent: 78,
          },
          {
            title: isHorizonte ? "Reel com especialista" : "Reel com Mariana",
            format: "25 s · 9:16",
            progress: "Demonstração de calibração",
            gate: "CENA PENDENTE",
            destination: "Reels + TikTok",
            percent: 64,
          },
          {
            title: "Sequência de Stories",
            format: "5 telas · 9:16",
            progress: "Demonstração de pré-flight",
            gate: "PRÉ-FLIGHT",
            destination: "Stories",
            percent: 91,
          },
          ]
        : [];
  return (
    <section className="cx-factory-approved">
      <header>
        <div>
          <h1>Fábrica de conteúdo</h1>
          <p>
            Da oportunidade à peça pronta, com contexto, direção e controle.
          </p>
        </div>
        <Button>{brand?.name || "Workspace"}⌄</Button>
        <Button>Todas campanhas⌄</Button>
        <Button
          tone="primary"
          icon={Plus}
          actionId="FACTORY-NEW-PRODUCTION"
          onClick={() => navigate("/campaigns/new")}
        >
          Nova produção
        </Button>
      </header>
      <div className="cx-factory-metrics">
        {[
          [String(cells.filter((cell) => cell.jobId).length), "JOBS OBSERVÁVEIS"],
          [String(cells.filter((cell) => cell.status === "blocked").length), "CÉLULAS BLOQUEADAS"],
          [String(reviewableCells.length), "VERSÕES FIXADAS"],
          [String(linkedDerivativeIds.length || cells.length), "ENTRADAS DA RODADA"],
        ].map(([v, l], i) => (
          <article className={`tone-${i}`} key={l}>
            <strong>{v}</strong>
            <span>{l}</span>
          </article>
        ))}
        <small>
          {roundPayload
            ? `Estado persistido · ${roundPayload.status}`
            : "Pré-flight · nenhum processamento começou"}
        </small>
      </div>
      {factoryError && (
        <HonestState
          compact
          state="recoverable-error"
          detail={factoryError}
          preserved="as derivações, a receita e qualquer célula já criada"
          impact="nenhuma publicação foi executada"
          actionLabel="Tentar iniciar novamente"
          actionId="FACTORY-START-ROUND"
          onAction={() => void startRound()}
        />
      )}
      <div className="cx-factory-system">
        <section className="cx-factory-inputs">
          <header>
            <span>01</span>
            <div>
              <small>ENTRADAS VIVAS</small>
              <h2>Contexto que alimenta esta rodada</h2>
            </div>
            <Button
              actionId="FACTORY-OPEN-SOURCE"
              onClick={() =>
                navigate(
                  sourcePost
                    ? `/content/${sourcePost.id}/edit?mode=editorial`
                    : "/radar",
                )
              }
            >
              Ver origem
            </Button>
          </header>
          <div>
            {factoryInputs.map(([Icon, label, value, state]) => (
              <article key={String(label)}>
                <Icon />
                <small>{label}</small>
                <b>{value}</b>
                <i className={state === "ausente" ? "is-missing" : ""}>
                  {state}
                </i>
              </article>
            ))}
          </div>
        </section>

        <section className="cx-factory-recipe">
          <header>
            <span>02</span>
            <div>
              <small>RECEITA ESTRATÉGICA APLICADA</small>
              <h2>
                {demo
                  ? isHorizonte
                    ? "Clareza clínica sem alarmismo"
                    : "Presença antes da produtividade"
                  : observedHypothesis || "Hipótese ainda não registrada"}
              </h2>
            </div>
            <strong>
              {demo
                ? "COERÊNCIA 92%"
                : `${recipeSteps.length} decisões de transformação`}
            </strong>
          </header>
          {recipeSteps.length ? (
            <div>
              {recipeSteps.map((item, index) => (
                <React.Fragment key={item}>
                  <span>
                    <b>{index + 1}</b>
                    {item}
                  </span>
                  {index < recipeSteps.length - 1 && <ArrowRight />}
                </React.Fragment>
              ))}
            </div>
          ) : (
            <p className="cx-factory-empty-note">
              Nenhuma decisão de preservação ou adaptação foi registrada na linhagem.
            </p>
          )}
        </section>

        <section className="cx-factory-engine">
          <header>
            <span>03</span>
            <div>
              <small>
                MOTOR CLICKO · {roundPayload ? "RODADA PERSISTIDA" : "PRÉ-FLIGHT"}
              </small>
              <h2>
                {cells.length
                  ? `${cells.length} células com identidade própria`
                  : "Entradas aguardando validação da rodada"}
              </h2>
            </div>
            <em>{linkedDerivativeIds.length || cells.length} derivações vinculadas</em>
          </header>
          <div className="cx-factory-cells">
            {factoryCells.map((cell, index) => (
              <article key={`${cell.title}-${index}`}>
                {demo ? (
                  <img src={factoryVisuals[index % factoryVisuals.length]} alt="" />
                ) : (
                  <figure className="cx-factory-cell-identity" aria-hidden="true">
                    Documento canônico
                  </figure>
                )}
                <span>{String(index + 1).padStart(2, "0")}</span>
                <small>{cell.format}</small>
                <h3>{cell.title}</h3>
                <div>
                  <i style={{ width: `${cell.percent}%` }} />
                </div>
                <p>{cell.progress}</p>
                <b>{cell.gate}</b>
                <footer>Destino · {cell.destination}</footer>
              </article>
            ))}
          </div>
        </section>

        <aside className="cx-factory-decisions">
          <header>
            <span>04</span>
            <div>
              <small>GATES HUMANOS</small>
              <h2>
                {decisionCells.length
                  ? `${decisionCells.length} decisões antes da saída`
                  : "Nenhuma decisão disponível"}
              </h2>
            </div>
          </header>
          {decisionCells.map((decision: AnyRecord, index: number) => (
            <button
              data-action-id="FACTORY-OPEN-DECISION"
              key={`${decision.postId}-${index}`}
              onClick={() =>
                navigate(
                  decision.calendar
                    ? "/calendar"
                    : decision.blocked
                      ? `/content/${decision.postId}/edit?mode=visual`
                      : `/approvals/${decision.postId}?view=creative&batch=${roundPayload?.id || "demo"}`,
                )
              }
            >
              <i>{index + 1}</i>
              <span>
                <b>{decision.title}</b>
                <small>{decision.detail}</small>
              </span>
              <em>{decision.urgency}</em>
              <ChevronRight />
            </button>
          ))}
          {!decisionCells.length && (
            <p className="cx-factory-empty-note">
              Inicie a rodada para materializar versões revisáveis e seus gates humanos.
            </p>
          )}
        </aside>

        <section className="cx-factory-destinations">
          <small>DESTINOS DESTA RODADA</small>
          <div>
            {Object.entries(destinationCounts).length ? (
              Object.entries(destinationCounts).map(([destination, count]) => (
                <span key={destination}>
                  {destination} · {count}
                </span>
              ))
            ) : (
              <span>Nenhum destino registrado</span>
            )}
          </div>
          <strong>
            {roundPayload
              ? `${reviewableCells.length} versões aguardando decisão humana`
              : "Nenhuma capacidade foi consumida"}
          </strong>
        </section>
      </div>
      <footer className="cx-factory-next">
        <small>✦ PRÓXIMA MELHOR AÇÃO</small>
        <div>
          <b>
            {roundPayload
              ? "Rodada persistida com documentos, versões e jobs rastreáveis."
              : canStart
                ? "Valide as entradas e crie uma rodada observável antes da produção."
                : "Selecione e gere derivações no Reuse Lab para alimentar esta rodada."}
          </b>
          <span>Nenhum conteúdo é publicado sem revisão humana.</span>
        </div>
        <Button
          actionId="FACTORY-START-ROUND"
          tone="primary"
          disabled={starting || Boolean(roundPayload) || !canStart}
          onClick={() => void startRound()}
        >
          {starting
            ? "Fixando versões e criando jobs…"
            : roundPayload
              ? "Rodada iniciada"
              : "Iniciar nova rodada"}
        </Button>
        {roundPayload && (
          <Button
            actionId="FACTORY-OPEN-BATCH-REVIEW"
            disabled={reviewableCells.length === 0}
            onClick={() =>
              navigate(
                `/approvals/${reviewableCells[0]?.postId}?batch=${roundPayload.id}`,
              )
            }
          >
            Revisar lote elegível
          </Button>
        )}
      </footer>
    </section>
  );
}

function FactorySurface({ navigate }: AnyRecord) {
  return (
    <Page
      eyebrow="Fábrica"
      title="Comece pelo formato. A marca já vem junto."
      description="Ferramentas especializadas, todas conectadas à mesma campanha e memória."
      actions={<Button icon={Clock3}>Recentes</Button>}
    >
      <div className="cx-factory-hero">
        <div>
          <Chip tone="orange">Novo · Co-piloto criativo</Chip>
          <h2>
            Descreva a intenção.
            <br />A Clicko monta o ponto de partida.
          </h2>
          <p>
            “Quero lançar uma sequência sobre a origem do nosso novo microlote.”
          </p>
          <button data-action-id="FACTORY-OPEN-AI" onClick={() => navigate("/campaigns/new")}>
            <Sparkles />
            Começar com IA
            <ArrowRight />
          </button>
        </div>
        <div className="cx-orbit">
          <span className="one">
            <Image />
          </span>
          <span className="two">
            <Type />
          </span>
          <span className="three">
            <Play />
          </span>
          <span className="four">
            <Layers3 />
          </span>
          <i>
            <Sparkles />
          </i>
        </div>
      </div>
      <SectionHead title="Escolha uma ferramenta" />
      <div className="cx-tool-grid">
        {createItems.slice(0, 4).map(([Icon, title, path, detail], i) => (
          <button
            data-action-id="FACTORY-OPEN-TOOL"
            key={title}
            onClick={() => navigate(path)}
          >
            <span className={`tone-${i}`}>
              <Icon />
            </span>
            <small>{detail}</small>
            <h3>{title}</h3>
            <p>
              {
                [
                  "Componha no canvas com assets e marca.",
                  "Estruture ideias, pautas e legendas.",
                  "Conte uma história em sequência.",
                  "Edite ritmo, cena e trilha em um só lugar.",
                ][i]
              }
            </p>
            <footer>
              Abrir ferramenta <ArrowRight />
            </footer>
          </button>
        ))}
      </div>
      <SectionHead title="Continuar de onde parou" />
      <div className="cx-recent">
        <img src={demoMedia.hero} />
        <div>
          <Chip>Post visual</Chip>
          <h3>O primeiro gole</h3>
          <p>Ritual Café Aurora · editado há 18 min</p>
        </div>
        <Button
          actionId="FACTORY-CONTINUE"
          onClick={() => navigate("/content/draft/edit?mode=visual")}
        >
          Continuar
        </Button>
      </div>
    </Page>
  );
}

function ProjectsSurface({ data, demo, navigate, brand }: AnyRecord) {
  const isHorizonte = brand?.id === "horizonte";
  const auroraProjects = [
    {
      id: "campaign-aurora",
      name: "Campanha Ritual de Foco",
      stage: "Em criação",
      progress: 38,
      owner: "Mariana",
      updated: "Hoje, 10:24",
      next: "Escrever roteiros",
      decision: "Escolher a direção dos 3 Reels",
      signal: "+38% interesse em rituais de foco",
      pieces: 6,
      versions: 12,
      outputs: ["Carrossel", "Reels", "Stories"],
      image: "/canonical/figma/phase2/s23-cover-1.png",
    },
    {
      id: "origens",
      name: "Lançamento Aurora Origens",
      stage: "Controle de qualidade",
      progress: 72,
      owner: "João",
      updated: "Hoje, 09:11",
      next: "Aprovar conteúdos",
      decision: "Aprovar o corte UGC ou pedir nova versão",
      signal: "842 compartilhamentos no conteúdo de origem",
      pieces: 9,
      versions: 18,
      outputs: ["UGC", "Post", "Anúncio"],
      image: "/canonical/figma/phase2/s23-cover-2.png",
    },
    {
      id: "brasil-xicara",
      name: "O Brasil cabe em uma xícara",
      stage: "Pronto para sair",
      progress: 85,
      owner: "Mariana",
      updated: "Ontem, 16:45",
      next: "Agendar publicações",
      decision: "Confirmar cadência e canal de estreia",
      signal: "Carrossel teve 3× mais salvamentos",
      pieces: 8,
      versions: 15,
      outputs: ["Carrossel", "Feed", "Newsletter"],
      image: "/canonical/figma/phase2/s23-cover-3.png",
    },
    {
      id: "festival",
      name: "Festival Brasileiro de Cafés",
      stage: "Em estruturação",
      progress: 22,
      owner: "Lucas",
      updated: "Ontem, 11:02",
      next: "Definir roteiros",
      decision: "Vincular oportunidade à promessa central",
      signal: "Janela cultural termina em 18 horas",
      pieces: 4,
      versions: 7,
      outputs: ["Cobertura", "Stories", "Reels"],
      image: "/canonical/figma/phase2/s23-cover-1.png",
    },
    {
      id: "kit",
      name: "Kit Degustação Grãos Raros",
      stage: "Em criação",
      progress: 41,
      owner: "Lívia",
      updated: "26 mai, 15:20",
      next: "Gravar vídeos",
      decision: "Escolher rosto e cenário da demonstração",
      signal: "Oferta com maior intenção de compra",
      pieces: 5,
      versions: 9,
      outputs: ["Vídeo", "Produto", "Landing"],
      image: "/canonical/figma/phase2/s23-cover-2.png",
    },
  ];
  const horizonteProjects = [
    {
      id: "horizonte-prevencao",
      name: "Cuidar antes da urgência",
      stage: "Em criação",
      progress: 46,
      owner: "Renata",
      updated: "Hoje, 11:08",
      next: "Validar orientação clínica",
      decision: "Aprovar a abordagem para check-up preventivo",
      signal: "+42% nas conversas sobre prevenção",
      pieces: 7,
      versions: 14,
      outputs: ["Carrossel", "Reels", "Guia"],
      image: "/canonical/brands/horizonte/campaign.svg",
    },
    {
      id: "horizonte-checkup",
      name: "Check-up em cada fase da vida",
      stage: "Controle de qualidade",
      progress: 74,
      owner: "Caio",
      updated: "Hoje, 09:32",
      next: "Revisar linguagem médica",
      decision: "Resolver duas ressalvas do corpo clínico",
      signal: "2,6× mais compartilhamentos no guia-base",
      pieces: 10,
      versions: 21,
      outputs: ["Guia", "Feed", "Stories"],
      image: "/canonical/brands/horizonte/winner.svg",
    },
    {
      id: "horizonte-sinais",
      name: "Sinais que não devem esperar",
      stage: "Pronto para sair",
      progress: 88,
      owner: "Renata",
      updated: "Ontem, 17:10",
      next: "Confirmar agenda de publicação",
      decision: "Escolher entre estreia orgânica ou impulsionada",
      signal: "Alta de buscas locais por atendimento rápido",
      pieces: 8,
      versions: 16,
      outputs: ["Reels", "Busca", "Stories"],
      image: "/canonical/brands/horizonte/signal.svg",
    },
  ];
  const demoProjects = isHorizonte ? horizonteProjects : auroraProjects;
  const projects = demo
    ? demoProjects
    : (data.snapshot?.campaigns || []).map((c: AnyRecord, i: number) => ({
        id: c.id,
        name: c.name,
        stage: statusLabel[c.status] || c.status,
        progress: c.progress || 0,
        owner: c.ownerName || "Equipe",
        updated: c.updatedAt || "Atualizado agora",
        next: "Abrir campanha",
        decision: "Abrir próxima decisão criativa",
        signal: "Oportunidade relacionada disponível",
        pieces: c.pieceCount || 0,
        versions: c.versionCount || 0,
        outputs: c.outputs || ["Conteúdo"],
        image: demoProjects[i % 3].image,
      }));
  const [filter, setFilter] = React.useState("Todos");
  const [query, setQuery] = React.useState("");
  const filtered = projects.filter((p: AnyRecord) => {
    const matchesStage =
      filter === "Todos" ||
      (filter === "Em produção" &&
        ["Em criação", "Em estruturação"].includes(p.stage)) ||
      (filter === "Em revisão" && p.stage === "Controle de qualidade") ||
      (filter === "Agendados" && p.stage === "Pronto para sair") ||
      (filter === "Concluídos" && p.stage === "Concluído");
    return matchesStage && p.name.toLowerCase().includes(query.toLowerCase());
  });
  return (
    <section className="cx-projects-approved">
      <div className="cx-projects-title">
        <h1>Projetos</h1>
        <Button
          tone="primary"
          icon={Plus}
          actionId="PROJECTS-NEW"
          onClick={() => navigate("/campaigns/new")}
        >
          Novo projeto
        </Button>
      </div>
      <div className="cx-projects-toolbar">
        <button
          disabled
          title="O workspace já está fixado para esta visão de projetos."
        >
          {brand?.name || "Workspace"} <ChevronDown />
        </button>
        <label>
          <Search />
          <input
            data-action-id="PROJECTS-SELECT-FILTER"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Buscar projetos"
          />
        </label>
        {["Todos", "Em produção", "Em revisão", "Agendados", "Concluídos"].map(
          (x) => (
            <button
              data-action-id="PROJECTS-SELECT-FILTER"
              className={filter === x ? "is-active" : ""}
              onClick={() => setFilter(x)}
              key={x}
            >
              {x}
            </button>
          ),
        )}
      </div>
      {filtered.length ? (
        <>
          <h2>Retome o trabalho</h2>
          <div className="cx-project-resume">
            {filtered.slice(0, 3).map((p: AnyRecord) => (
              <button
                data-action-id="PROJECTS-OPEN"
                key={p.id}
                onClick={() => navigate(`/campaigns/${p.id}`)}
              >
                <img src={p.image} />
                <span />
                <div>
                  <h3>{p.name}</h3>
                  <p>{brand?.name || "Workspace"}</p>
                  <small>Produção {p.progress}%</small>
                  <i>
                    <em style={{ width: `${p.progress}%` }} />
                  </i>
                  <b>{p.stage}</b>
                  <strong>{p.next} →</strong>
                </div>
              </button>
            ))}
          </div>
          <div className="cx-project-universe-head">
            <h2>
              Universos criativos em movimento{" "}
              <small>{filtered.length} projetos</small>
            </h2>
            <div>
              <span>
                {filtered.reduce(
                  (sum: number, item: AnyRecord) => sum + item.pieces,
                  0,
                )}{" "}
                peças
              </span>
              <span>
                {filtered.reduce(
                  (sum: number, item: AnyRecord) => sum + item.versions,
                  0,
                )}{" "}
                versões
              </span>
            </div>
          </div>
          <div className="cx-project-universes">
            {filtered.map((p: AnyRecord) => (
              <button
                data-action-id="PROJECTS-OPEN"
                key={p.id}
                onClick={() => navigate(`/campaigns/${p.id}`)}
              >
                <span className="cx-project-universe-visual">
                  <img src={p.image} />
                  <i style={{ width: `${p.progress}%` }} />
                  <em>{p.progress}% criativo</em>
                </span>
                <span className="cx-project-universe-copy">
                  <small>
                    {p.stage} · {p.owner}
                  </small>
                  <b>{p.name}</b>
                  <p>{p.signal}</p>
                  <span className="cx-project-output-list">
                    {p.outputs.map((output: string) => (
                      <i key={output}>{output}</i>
                    ))}
                  </span>
                  <strong>
                    {p.pieces} peças · {p.versions} versões
                  </strong>
                  <em>PRÓXIMA DECISÃO</em>
                  <span>{p.decision}</span>
                </span>
                <ArrowRight />
              </button>
            ))}
          </div>
        </>
      ) : (
        <EmptyState
          title="Nenhum projeto nesta visão"
          detail="Ajuste os filtros ou crie uma nova campanha."
          action="Novo projeto"
          onAction={() => navigate("/campaigns/new")}
        />
      )}
    </section>
  );
}

const socialIntegrationConfigs: AnyRecord = {
  instagram: {
    mark: "◎",
    color: "#ff4169",
    name: "Instagram",
    subtitle: "Publicação, interação e aprendizado visual da marca.",
    identity: "@cafeaurora · Business",
    badge: "Conexão compartilhada pela Meta",
    tabs: ["Visão geral", "Publicação", "Interações", "Insights", "Conexão"],
    capabilities: [
      ["Feed e carrossel", "Imagens, múltiplos cards e legendas"],
      ["Reels", "Vídeo vertical com capa e áudio"],
      ["Stories", "Janela de 24 horas"],
      ["Comentários", "Triagem e resposta assistida"],
    ],
    defaults: [
      ["Formato padrão", "Carrossel 4:5"],
      ["Primeiro comentário", "Hashtags da marca"],
      ["Aprovação", "Obrigatória"],
      ["Stories", "Reutilizar vencedores"],
    ],
    flow: [
      ["Preparar", "Valida proporção, copy e identidade"],
      ["Publicar", "Cria contêiner e acompanha o envio"],
      ["Aprender", "Importa alcance, saves e retenção"],
    ],
    metrics: [
      ["Aprovação", "86%", "+11%"],
      ["Salvamentos", "1,8 mil", "+24%"],
      ["Retenção Reels", "42%", "+7%"],
    ],
    scope: "Perfil profissional",
    health: "Conexão Meta ativa e escopos válidos",
    next: "em 26 dias",
    permissions: [
      ["Publicar", "Permitido"],
      ["Ler comentários", "Permitido"],
      ["Responder menções", "Permitido"],
    ],
    memory: [
      ["Janela", "90 dias"],
      ["Conteúdos", "284"],
      ["Insight", "Rituais matinais"],
    ],
  },
  facebook: {
    mark: "f",
    color: "#2878ff",
    name: "Facebook",
    subtitle: "Gestão editorial da Página, comunidade e desempenho.",
    identity: "Café Aurora · Página",
    badge: "Conexão compartilhada pela Meta",
    tabs: ["Visão geral", "Publicação", "Comunidade", "Insights", "Conexão"],
    capabilities: [
      ["Feed e fotos", "Posts, álbuns e links"],
      ["Vídeos e Reels", "Publicação e processamento"],
      ["Comunidade", "Comentários e mensagens"],
      ["Métricas", "Alcance, cliques e respostas"],
    ],
    defaults: [
      ["Público padrão", "Público"],
      ["CTA de link", "Saiba mais"],
      ["Aprovação", "Obrigatória"],
      ["Crosspost", "Revisar antes"],
    ],
    flow: [
      ["Validar ator", "Confirma Página e função"],
      ["Publicar", "Envia mídia, copy e CTA"],
      ["Aprender", "Compara criativo, alcance e cliques"],
    ],
    metrics: [
      ["Publicados", "32", "+8"],
      ["Cliques", "4,2%", "+0,8%"],
      ["Respostas", "91%", "+6%"],
    ],
    scope: "Página gerenciada",
    health: "Função de administrador confirmada",
    next: "em 26 dias",
    permissions: [
      ["Publicar como Página", "Permitido"],
      ["Gerir comentários", "Permitido"],
      ["Ler mensagens", "Revisar"],
    ],
    memory: [
      ["Janela", "180 dias"],
      ["Posts", "412"],
      ["Padrão", "Oferta + prova"],
    ],
  },
  tiktok: {
    mark: "TK",
    color: "#f5f5f2",
    name: "TikTok",
    subtitle: "Publicação nativa, segurança comercial e sinais de retenção.",
    identity: "@cafeaurora",
    badge: "Conta Business",
    tabs: ["Visão geral", "Publicação", "Audiência", "Insights", "Conexão"],
    capabilities: [
      ["Direct Post", "Publicação automática liberada"],
      ["Rascunho", "Entrega para finalização no app"],
      ["Interações", "Comentários, dueto e stitch"],
      ["Conteúdo comercial", "Declaração obrigatória"],
    ],
    defaults: [
      ["Modo de envio", "Direct Post"],
      ["Privacidade", "Público"],
      ["Comentários", "Ativados"],
      ["Dueto e Stitch", "Sob aprovação"],
    ],
    flow: [
      ["Preparar", "Valida música, disclosure e formato"],
      ["Processar", "Acompanha upload e moderação"],
      ["Aprender", "Lê retenção, replay e compartilhamento"],
    ],
    metrics: [
      ["Retenção 3s", "78%", "+9%"],
      ["Conclusão", "31%", "+5%"],
      ["Shares", "680", "+18%"],
    ],
    scope: "Conta Business",
    health: "Direct Post liberado",
    next: "em 12 dias",
    permissions: [
      ["Publicar direto", "Permitido"],
      ["Ler vídeos", "Permitido"],
      ["Interações", "Parcial"],
    ],
    memory: [
      ["Janela", "60 dias"],
      ["Vídeos", "96"],
      ["Hook", "Ritual em 3 passos"],
    ],
  },
  youtube: {
    mark: "YT",
    color: "#ff2727",
    name: "YouTube",
    subtitle: "Vídeos, Shorts e metadados orientados por descoberta.",
    identity: "Café Aurora Oficial",
    badge: "Canal de marca",
    tabs: ["Visão geral", "Upload", "Metadados", "Analytics", "Conexão"],
    capabilities: [
      ["Vídeo", "Upload resumível e processamento"],
      ["Shorts", "Vertical com detecção automática"],
      ["Miniatura", "Arquivo customizado e teste"],
      ["Legendas", "Upload e revisão assistida"],
    ],
    defaults: [
      ["Visibilidade", "Não listado"],
      ["Categoria", "Educação"],
      ["Playlist", "Rituais Aurora"],
      ["Legendas", "PT-BR automático"],
    ],
    flow: [
      ["Enviar", "Upload retomável e checksum"],
      ["Processar", "Qualidade, direitos e miniatura"],
      ["Aprender", "Retenção, CTR e origem do tráfego"],
    ],
    metrics: [
      ["CTR miniatura", "6,8%", "+1,1%"],
      ["Retenção 30s", "64%", "+8%"],
      ["Inscritos", "12,4 mil", "+3%"],
    ],
    scope: "Canal de marca",
    health: "Quota diária saudável",
    next: "em 18 dias",
    permissions: [
      ["Enviar vídeos", "Permitido"],
      ["Gerir playlists", "Permitido"],
      ["Ler Analytics", "Permitido"],
    ],
    memory: [
      ["Janela", "365 dias"],
      ["Vídeos", "148"],
      ["Tema", "Foco sem ansiedade"],
    ],
  },
  x: {
    mark: "𝕏",
    color: "#f5f5f2",
    name: "X",
    subtitle: "Conversas em tempo real, threads e controle de limite.",
    identity: "@cafeaurora",
    badge: "Plano API monitorado",
    tabs: ["Visão geral", "Publicação", "Conversas", "Uso da API", "Conexão"],
    capabilities: [
      ["Posts e threads", "Texto, mídia e encadeamento"],
      ["Enquetes", "Opções e duração"],
      ["Respostas", "Controle de quem pode interagir"],
      ["Monitoramento", "Limites variam por plano"],
    ],
    defaults: [
      ["Resposta padrão", "Seguidores"],
      ["Mídia sensível", "Desativada"],
      ["Parceria paga", "Perguntar sempre"],
      ["Threads", "Numerar posts"],
    ],
    flow: [
      ["Compor", "Adapta hook ao contexto vivo"],
      ["Publicar", "Valida limite e disclosure"],
      ["Aprender", "Lê respostas, reposts e cliques"],
    ],
    metrics: [
      ["Engajamento", "5,4%", "+1,3%"],
      ["Reposts", "184", "+21%"],
      ["Uso do plano", "63%", "estável"],
    ],
    scope: "Conta de organização",
    health: "Rate limit dentro da faixa",
    next: "em 3 horas",
    permissions: [
      ["Publicar", "Permitido"],
      ["Ler menções", "Permitido"],
      ["Buscar tendências", "Limitado"],
    ],
    memory: [
      ["Janela", "30 dias"],
      ["Posts", "221"],
      ["Assunto", "Rotina sem ruído"],
    ],
  },
  linkedin: {
    mark: "in",
    color: "#43a6db",
    name: "LinkedIn",
    subtitle: "Autoridade, documentos e publicação institucional.",
    identity: "Café Aurora · Organização",
    badge: "Organização administrada",
    tabs: ["Visão geral", "Publicação", "Documentos", "Analytics", "Conexão"],
    capabilities: [
      ["Posts", "Texto, imagem e múltiplas imagens"],
      ["Vídeos", "Upload nativo"],
      ["Documentos", "Carrossel PDF"],
      ["Comentários", "Leitura e resposta assistida"],
    ],
    defaults: [
      ["Ator padrão", "Organização"],
      ["Audiência", "Todos"],
      ["Documento", "PDF 4:5"],
      ["Aprovação", "Head de marca"],
    ],
    flow: [
      ["Validar admin", "Confirma função e organização"],
      ["Publicar", "Envia conteúdo no ator correto"],
      ["Aprender", "Compara autoridade e conversão"],
    ],
    metrics: [
      ["Impressões", "82 mil", "+14%"],
      ["Cliques", "3,7%", "+0,6%"],
      ["Seguidores", "18,9 mil", "+2%"],
    ],
    scope: "Organização administrada",
    health: "Papel de conteúdo confirmado",
    next: "em 21 dias",
    permissions: [
      ["Publicar pela empresa", "Permitido"],
      ["Ler Analytics", "Permitido"],
      ["Responder comentários", "Permitido"],
    ],
    memory: [
      ["Janela", "180 dias"],
      ["Posts", "198"],
      ["Ângulo", "Bastidores + método"],
    ],
  },
  pinterest: {
    mark: "p",
    color: "#e71c39",
    name: "Pinterest",
    subtitle: "Descoberta visual, tráfego durável e organização por boards.",
    identity: "Café Aurora · Business",
    badge: "Conta Business",
    tabs: ["Visão geral", "Pins", "Boards", "Analytics", "Conexão"],
    capabilities: [
      ["Pin de imagem", "Título, descrição, link e alt text"],
      ["Pin de vídeo", "Formato vertical"],
      ["Boards", "Seleção e organização"],
      ["Tendências", "Sinais de busca e sazonalidade"],
    ],
    defaults: [
      ["Board padrão", "Rituais de café"],
      ["Link", "UTM automática"],
      ["Alt text", "Obrigatório"],
      ["Formato", "2:3 vertical"],
    ],
    flow: [
      ["Enriquecer", "Gera metadata e acessibilidade"],
      ["Publicar", "Seleciona board e destino"],
      ["Aprender", "Lê saves, outbound clicks e trends"],
    ],
    metrics: [
      ["Saves", "3,1 mil", "+28%"],
      ["Cliques externos", "9,6%", "+2,2%"],
      ["Vida média", "47 dias", "+6"],
    ],
    scope: "Conta Business",
    health: "Boards sincronizados",
    next: "em 14 dias",
    permissions: [
      ["Criar Pins", "Permitido"],
      ["Gerir boards", "Permitido"],
      ["Ler Analytics", "Permitido"],
    ],
    memory: [
      ["Janela", "365 dias"],
      ["Pins", "612"],
      ["Trend", "Coffee corner"],
    ],
  },
  threads: {
    mark: "@",
    color: "#f5f5f2",
    name: "Threads",
    subtitle: "Conversas rápidas, contexto cultural e formatos leves.",
    identity: "@cafeaurora",
    badge: "Via ecossistema Meta",
    tabs: ["Visão geral", "Publicação", "Conversas", "Insights", "Conexão"],
    capabilities: [
      ["Texto e links", "Posts curtos e contexto"],
      ["Imagem e vídeo", "Mídia nativa"],
      ["Carrossel", "Sequência visual"],
      ["Respostas e polls", "Controles por publicação"],
    ],
    defaults: [
      ["Quem responde", "Todos"],
      ["Topic tag", "Sugerir"],
      ["Alt text", "Obrigatório"],
      ["Ghost post", "Sob aprovação"],
    ],
    flow: [
      ["Detectar contexto", "Radar prioriza conversas aderentes"],
      ["Publicar", "Cria contêiner e acompanha status"],
      ["Aprender", "Lê replies, views e reposts"],
    ],
    metrics: [
      ["Respostas", "342", "+33%"],
      ["Reposts", "118", "+19%"],
      ["Views", "48 mil", "+12%"],
    ],
    scope: "Perfil profissional",
    health: "Contêineres processando normalmente",
    next: "em 25 dias",
    permissions: [
      ["Publicar", "Permitido"],
      ["Ler insights", "Permitido"],
      ["Moderar replies", "Limitado"],
    ],
    memory: [
      ["Janela", "21 dias"],
      ["Posts", "87"],
      ["Conversa", "Ritual matinal"],
    ],
  },
  twitch: {
    mark: "▣",
    color: "#9147ff",
    name: "Twitch",
    subtitle: "Fonte ao vivo para detectar momentos e reutilizar conteúdo.",
    identity: "cafeaurora_live",
    badge: "Canal-fonte",
    tabs: ["Visão geral", "Agenda", "Clipes", "Reutilização", "Conexão"],
    capabilities: [
      ["Agenda", "Lives e categorias"],
      ["VODs", "Importação após a transmissão"],
      ["Clipes", "Detecção de momentos"],
      ["Reutilização", "Reels, Shorts e cortes"],
    ],
    defaults: [
      ["Janela de clipe", "20–45s"],
      ["Detector", "Pico + frase-chave"],
      ["Legendas", "PT-BR dinâmico"],
      ["Destino", "Reels e Shorts"],
    ],
    flow: [
      ["Observar", "Lê chat, áudio e picos"],
      ["Recortar", "Propõe momentos com contexto"],
      ["Distribuir", "Adapta e aprende nos destinos"],
    ],
    metrics: [
      ["Clipes sugeridos", "24", "+9"],
      ["Aprovação", "79%", "+12%"],
      ["Views derivados", "91 mil", "+31%"],
    ],
    scope: "Canal parceiro",
    health: "Eventos e VODs sincronizados",
    next: "em 7 dias",
    permissions: [
      ["Ler streams", "Permitido"],
      ["Importar VOD", "Permitido"],
      ["Criar clipes", "Permitido"],
    ],
    memory: [
      ["Janela", "90 dias"],
      ["Lives", "36"],
      ["Momento", "Pergunta do chat"],
    ],
  },
  "google-business-profile": {
    mark: "G",
    color: "#55b5e8",
    name: "Google Business Profile",
    subtitle: "Presença local em Search e Maps, posts e reputação.",
    identity: "Café Aurora · Pinheiros",
    badge: "Local verificado",
    tabs: ["Visão geral", "Publicações", "Avaliações", "Métricas", "Conexão"],
    capabilities: [
      ["Atualização", "Post institucional e mídia"],
      ["Evento", "Período, detalhes e CTA"],
      ["Oferta", "Cupom, termos e validade"],
      ["Avaliações", "Triagem e resposta assistida"],
    ],
    defaults: [
      ["Local padrão", "Pinheiros"],
      ["CTA", "Saiba mais"],
      ["UTM", "Automática"],
      ["Resposta pública", "Sob aprovação"],
    ],
    flow: [
      ["Preparar", "Valida local, CTA e datas"],
      ["Publicar", "Envia para Search e Maps"],
      ["Aprender", "Lê ações, rotas e avaliações"],
    ],
    metrics: [
      ["Ações no perfil", "2,4 mil", "+17%"],
      ["Rotas", "680", "+12%"],
      ["Nota média", "4,8", "+0,1"],
    ],
    scope: "Local verificado",
    health: "Local e permissões válidos",
    next: "em 29 dias",
    permissions: [
      ["Publicar posts", "Permitido"],
      ["Ler avaliações", "Permitido"],
      ["Responder avaliações", "Permitido"],
    ],
    memory: [
      ["Janela", "180 dias"],
      ["Avaliações", "624"],
      ["Tema", "Atendimento rápido"],
    ],
  },
};

function ApprovedAppsSurface({ demo, navigate, setToast, data }: AnyRecord) {
  const [query, setQuery] = React.useState("");
  const [category, setCategory] = React.useState("Todas");
  const [connected, setConnected] = React.useState<string[]>([]);
  React.useEffect(() => {
    const persisted = (data.snapshot?.connectedAccounts || [])
      .map((item: AnyRecord) => item.payload?.name)
      .filter(Boolean);
    if (persisted.length) setConnected(persisted);
  }, [data.snapshot?.connectedAccounts]);
  const essentials = [
    [
      "Meta",
      "Instagram e Facebook",
      "Publicação",
      "Reconexão necessária",
      "meta",
      "instagram",
    ],
    [
      "Google Drive",
      "Acesse e organize arquivos",
      "Arquivos",
      "Conectado",
      "googleDrive",
      "",
    ],
    [
      "Canva",
      "Importe designs para aprovação",
      "Design",
      "Disponível",
      "canva",
      "",
    ],
    [
      "Dropbox",
      "Compartilhe arquivos da equipe",
      "Arquivos",
      "Disponível",
      "dropbox",
      "",
    ],
    [
      "Webhooks / API",
      "Automatize fluxos internos",
      "Automação",
      "Em breve",
      "webhooks",
      "",
    ],
  ];
  const discover = [
    ["Pexels / Unsplash", "Assets", "unsplash"],
    ["Slack", "Comunicação", "slack"],
    ["Google Calendar", "Produtividade", "googleCalendar"],
    ["Importação de dados", "Dados", "database"],
  ];
  const socials = Object.entries(socialIntegrationConfigs) as [
    string,
    AnyRecord,
  ][];
  const match = (values: unknown[]) =>
    values.join(" ").toLowerCase().includes(query.trim().toLowerCase());
  const filteredEssentials = essentials.filter(
    (x) => (category === "Todas" || x[2] === category) && match(x),
  );
  return (
    <section className="cx-apps-approved">
      <header>
        <div>
          <h1>Apps e integrações</h1>
          <p>Conecte as ferramentas que impulsionam sua operação criativa.</p>
        </div>
        <label>
          <Search size={15} />
          <input
            data-action-id="APPS-SEARCH"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Buscar integração"
          />
        </label>
      </header>
      <nav>
        {[
          "Todas",
          "Publicação",
          "Arquivos",
          "Design",
          "Dados",
          "Automação",
        ].map((x) => (
          <button
            data-action-id="APPS-SELECT-CATEGORY"
            key={x}
            className={category === x ? "is-active" : ""}
            onClick={() => setCategory(x)}
          >
            {x}
          </button>
        ))}
      </nav>
      <StateBanner
        tone="orange"
        title="Publicação automatizada depende da conexão e das permissões do canal."
        detail="Algumas integrações exigem reconexão periódica; no workspace demonstrativo nenhum vínculo externo é presumido."
      />
      <h2>Essenciais para sua operação</h2>
      <div className="cx-apps-essential-grid">
        {filteredEssentials.map(([name, desc, type, status, mark, slug]) => {
          const isConnected = connected.includes(name);
          const disabled = status === "Em breve" || name === "Google Drive";
          return (
            <article key={name}>
              <span>
                <BrandIcon brand={mark} label={name} />
              </span>
              <h3>{name}</h3>
              <p>{desc}</p>
              <strong
                className={status === "Reconexão necessária" ? "is-danger" : ""}
              >
                {isConnected ? "Conectado nesta sessão" : status}
              </strong>
              <Button
                actionId="APPS-CONNECT"
                disabled={disabled}
                onClick={() => {
                  if (slug) navigate(`/apps/${slug}`);
                  else {
                    setConnected((x) => [...x, name]);
                    if (!demo) {
                      void data.saveWorkspaceResource(
                        "connected_account",
                        name.toLowerCase().replace(/[^a-z0-9]+/g, "-"),
                        {
                          name,
                          provider: name,
                          status: "configured",
                          externalPublishing: false,
                          configuredAt: new Date().toISOString(),
                        },
                      );
                    }
                    setToast(
                      demo
                        ? `${name}: conexão demonstrativa preparada`
                        : `${name}: configuração persistida`,
                    );
                  }
                }}
              >
                {status === "Reconexão necessária"
                  ? "Reconectar"
                  : disabled
                    ? "Indisponível no MVP"
                    : "Conectar app"}
              </Button>
              <small>{type}</small>
            </article>
          );
        })}
      </div>
      {!filteredEssentials.length && (
        <EmptyState
          title="Nenhuma integração encontrada"
          detail="Ajuste a busca ou a categoria."
        />
      )}
      <div className="cx-apps-lower">
        <section>
          <h2>Descobrir integrações</h2>
          <div className="cx-apps-discover-grid">
            {discover.filter(match).map(([name, type, mark]) => (
              <article key={name}>
                <span>
                  <BrandIcon brand={mark} label={name} />
                </span>
                <h3>{name}</h3>
                <p>{type}</p>
                <b>
                  {name === "Importação de dados" ? "Em breve" : "Disponível"}
                </b>
                <Button
                  actionId="APPS-CONNECT"
                  disabled={name === "Importação de dados"}
                  onClick={() => setToast(`${name}: configuração preparada`)}
                >
                  Conectar
                </Button>
              </article>
            ))}
          </div>
        </section>
        <aside>
          <h2>Atividade de integrações</h2>
          <article>
            <b>
              <BrandIcon brand="googleDrive" label="Google Drive" />
            </b>
            <span>
              Google Drive<small>Sincronizado há 2 horas</small>
            </span>
            <strong>OK</strong>
          </article>
          <article>
            <b>
              <BrandIcon brand="meta" label="Meta" />
            </b>
            <span>
              Instagram e Facebook<small>Erro de conexão</small>
            </span>
            <Button
              actionId="APPS-OPEN-INTEGRATION"
              onClick={() => navigate("/apps/instagram")}
            >
              Reconectar
            </Button>
          </article>
          <StateBanner
            tone="orange"
            title="Problemas de conexão podem impedir publicações e métricas."
          />
        </aside>
      </div>
      <h2>Canais sociais aprovados</h2>
      <div className="cx-social-catalog">
        {socials
          .filter(([, config]) => match([config.name, config.subtitle]))
          .map(([slug, config]) => (
            <button
              data-action-id="APPS-OPEN-INTEGRATION"
              key={slug}
              onClick={() => navigate(`/apps/${slug}`)}
              style={{ "--social-color": config.color } as React.CSSProperties}
            >
              <span>
                <BrandIcon brand={slug} label={config.name} />
              </span>
              <div>
                <b>{config.name}</b>
                <small>{config.subtitle}</small>
              </div>
              <ArrowRight />
            </button>
          ))}
      </div>
      {demo && (
        <footer>
          Estados de conexão exibidos como referência de produto; autorizações
          externas não são executadas neste workspace demonstrativo.
        </footer>
      )}
    </section>
  );
}

function SocialIntegrationSurface({
  pathname,
  navigate,
  setToast,
  demo,
  data,
  brand,
}: AnyRecord) {
  const slug = normalize(pathname).split("/").pop() || "instagram";
  const config =
    socialIntegrationConfigs[slug] || socialIntegrationConfigs.instagram;
  const [tab, setTab] = React.useState("Visão geral");
  const [tested, setTested] = React.useState(false);
  const [managing, setManaging] = React.useState(false);
  React.useEffect(() => {
    const resource = (data.snapshot?.connectedAccounts || []).find(
      (item: AnyRecord) => item.resourceKey === slug,
    );
    setTested(resource?.payload?.status === "verified");
  }, [data.snapshot?.connectedAccounts, slug]);
  return (
    <section
      className="cx-social-detail"
      style={{ "--social-color": config.color } as React.CSSProperties}
    >
      <header>
        <button
          className="cx-social-back"
          data-action-id="SOCIAL-BACK-APPS"
          onClick={() => navigate("/apps")}
          aria-label="Voltar para Apps"
        >
          <ArrowLeft />
        </button>
        <span className="cx-social-mark">
          <BrandIcon brand={slug} label={config.name} />
        </span>
        <div>
          <h1>{config.name}</h1>
          <p>{config.subtitle}</p>
          <small>{config.identity}</small>
          {config.badge && <em>{config.badge}</em>}
        </div>
        <div className="cx-social-health">
          <i /> <b>{tested ? "Conexão verificada" : "Conectado"}</b>
          <small>
            {demo ? "Estado demonstrativo" : "Sincronização saudável"}
          </small>
        </div>
        <Button
          actionId="SOCIAL-TEST-CONNECTION"
          onClick={() => {
            setTested(true);
            if (!demo) {
              void data.saveWorkspaceResource("connected_account", slug, {
                provider: slug,
                name: config.name,
                identity: config.identity,
                status: "verified",
                health: config.health,
                permissions: config.permissions,
                externalPublishing: false,
                lastTestedAt: new Date().toISOString(),
              });
            }
            setToast(`${config.name}: conexão testada`);
          }}
        >
          Testar conexão
        </Button>
        <Button
          tone="primary"
          actionId="SOCIAL-TOGGLE-MANAGEMENT"
          onClick={() => setManaging(!managing)}
        >
          {managing ? "Concluir" : "Gerenciar"}
        </Button>
      </header>
      <nav>
        {config.tabs.map((x: string) => (
          <button
            data-action-id="SOCIAL-SELECT-TAB"
            key={x}
            className={tab === x ? "is-active" : ""}
            onClick={() => setTab(x)}
          >
            {x}
          </button>
        ))}
      </nav>
      {tab !== "Visão geral" && (
        <StateBanner
          title={`${tab} de ${config.name}`}
          detail="A configuração detalhada permanece rastreável nesta mesma conexão; a visão abaixo resume o contrato operacional aprovado."
        />
      )}
      <div className="cx-social-layout">
        <main>
          <section>
            <h2>O que a Clicko pode fazer</h2>
            <p>Recursos disponíveis para a conta conectada</p>
            <div className="cx-social-capabilities">
              {config.capabilities.map(([a, b]: string[]) => (
                <article key={a}>
                  <i />
                  <b>{a}</b>
                  <small>{b}</small>
                </article>
              ))}
            </div>
          </section>
          <section>
            <h2>Configuração editorial</h2>
            <p>Defaults usados no estúdio e calendário</p>
            <div className="cx-social-pairs">
              {config.defaults.map(([a, b]: string[]) => (
                <span key={a}>
                  <small>{a}</small>
                  <b>{b}</b>
                </span>
              ))}
            </div>
          </section>
          <section>
            <h2>Fluxo de conteúdo e aprendizado</h2>
            <p>Do conteúdo ao aprendizado do canal</p>
            <div className="cx-social-flow">
              {config.flow.map(([a, b]: string[], i: number) => (
                <article key={a} className={i === 1 ? "is-active" : ""}>
                  <b>{a}</b>
                  <small>{b}</small>
                </article>
              ))}
            </div>
            <div className="cx-social-metrics">
              {config.metrics.map(([a, b, c]: string[]) => (
                <article key={a}>
                  <small>{a}</small>
                  <strong>{b}</strong>
                  <em>{c}</em>
                </article>
              ))}
            </div>
          </section>
        </main>
        <aside>
          <section>
            <h2>Conta e identidade</h2>
            <p>{config.identity}</p>
            <span>
              <small>Ator principal</small>
              <b>{config.identity.split(" · ")[0]}</b>
            </span>
            <span>
              <small>Escopo</small>
              <b>{config.scope}</b>
            </span>
          </section>
          <section>
            <h2>Saúde da conexão</h2>
            <p>{config.health}</p>
            <span>
              <small>Última sincronização</small>
              <b>{tested ? "agora" : "há 4 min"}</b>
            </span>
            <span>
              <small>Próxima verificação</small>
              <b className="is-positive">{config.next}</b>
            </span>
          </section>
          <section>
            <h2>Permissões operacionais</h2>
            <p>Traduzidas em resultados</p>
            {config.permissions.map(([a, b]: string[]) => (
              <span key={a}>
                <small>{a}</small>
                <b className={b === "Permitido" ? "is-positive" : "is-warning"}>
                  {b}
                </b>
              </span>
            ))}
          </section>
          <section>
            <h2>Dados para a inteligência Clicko</h2>
            <p>
              Memória separada e privada de {brand?.name || "seu workspace"}
            </p>
            {config.memory.map(([a, b]: string[]) => (
              <span key={a}>
                <small>{a}</small>
                <b className="is-link">{b}</b>
              </span>
            ))}
          </section>
        </aside>
      </div>
    </section>
  );
}

function IdentityLibrarySurface({
  navigate,
  setToast,
  data,
  demo,
  params,
}: AnyRecord) {
  const workspaceId = data.activeWorkspace?.id as string | undefined;
  const [loading, setLoading] = React.useState(!demo);
  const [error, setError] = React.useState<string>();
  const [identities, setIdentities] = React.useState<AnyRecord[]>([]);
  const [versions, setVersions] = React.useState<Record<string, AnyRecord[]>>({});
  const [voices, setVoices] = React.useState<AnyRecord[]>([]);
  const [voiceVersions, setVoiceVersions] = React.useState<Record<string, AnyRecord[]>>({});
  const [consents, setConsents] = React.useState<AnyRecord[]>([]);
  const [enrolling, setEnrolling] = React.useState(params?.get("enroll") === "1");
  const [saving, setSaving] = React.useState(false);
  const [name, setName] = React.useState("");
  const [purpose, setPurpose] = React.useState("Criar amostras privadas para anúncios da marca");
  const [expiresOn, setExpiresOn] = React.useState(() => {
    const next = new Date();
    next.setDate(next.getDate() + 30);
    return next.toISOString().slice(0, 10);
  });
  const [capture, setCapture] = React.useState<File>();
  const [voiceCapture, setVoiceCapture] = React.useState<File>();
  const [declared, setDeclared] = React.useState(false);
  const presenterCapability = data.snapshot?.studioCapabilities?.presenter;

  const load = React.useCallback(async () => {
    if (demo || !workspaceId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(undefined);
    try {
      const [nextIdentities, nextConsents, nextVoices] = await Promise.all([
        productApi.studioIdentities(workspaceId),
        productApi.studioConsents(workspaceId),
        productApi.studioVoices(workspaceId),
      ]);
      const [versionEntries, voiceVersionEntries] = await Promise.all([
        Promise.all(
          nextIdentities.map(async (identity) => [
            identity.id,
            await productApi.studioIdentityVersions(identity.id),
          ] as const),
        ),
        Promise.all(
          nextVoices.map(async (voice) => [
            voice.id,
            await productApi.studioVoiceVersions(voice.id),
          ] as const),
        ),
      ]);
      setIdentities(nextIdentities);
      setVersions(Object.fromEntries(versionEntries));
      setVoices(nextVoices);
      setVoiceVersions(Object.fromEntries(voiceVersionEntries));
      setConsents(nextConsents);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Não foi possível carregar as identidades.");
    } finally {
      setLoading(false);
    }
  }, [demo, workspaceId]);

  React.useEffect(() => {
    void load();
  }, [load]);

  const submitEnrollment = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!workspaceId || !capture || !voiceCapture || !name.trim() || !purpose.trim() || !declared) return;
    setSaving(true);
    setError(undefined);
    try {
      const evidence = await productApi.uploadStudioAsset(workspaceId, capture);
      const voiceEvidence = await productApi.uploadStudioAsset(workspaceId, voiceCapture);
      const subjectKey = `person/${crypto.randomUUID()}`;
      const consent = await productApi.createStudioConsent({
        workspaceId,
        subjectKey,
        subjectDisplayName: name.trim(),
        purpose: purpose.trim(),
        scopes: ["identity.enroll", "avatar.generate", "voice.enroll", "voice.clone"],
        brandIds: data.activeWorkspace?.brandProfile?.id
          ? [data.activeWorkspace.brandProfile.id]
          : [],
        channels: ["private-preview"],
        policyVersion: "clicko.identity-consent.v1",
        evidenceAssetId: evidence.id,
        expiresAt: new Date(`${expiresOn}T23:59:59.000Z`).toISOString(),
      });
      const identity = await productApi.createStudioIdentity({
        workspaceId,
        subjectKey,
        displayName: name.trim(),
        identityType: "natural_person",
        ownerUserId: null,
      });
      await productApi.createStudioIdentityVersion(identity.id, {
        consentGrantId: consent.id,
        capabilities: ["avatar.generate"],
        sampleAssetIds: [evidence.id],
        derivedArtifacts: [],
      });
      const voice = await productApi.createStudioVoice({
        workspaceId,
        identityProfileId: identity.id,
        displayName: `${name.trim()} · PT-BR`,
        locale: "pt-BR",
        voiceType: "cloned",
      });
      await productApi.createStudioVoiceVersion(voice.id, {
        consentGrantId: consent.id,
        sampleAssetIds: [voiceEvidence.id],
        derivedArtifacts: [],
        pronunciationProfile: {},
      });
      setToast("Candidato privado criado. Ele continua bloqueado até avaliação e revisão independentes.");
      setEnrolling(false);
      setName("");
      setCapture(undefined);
      setVoiceCapture(undefined);
      setDeclared(false);
      await load();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "O cadastro foi bloqueado com segurança.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Page
      eyebrow="Biblioteca de identidades"
      title="Escolha presença sem perder o controle"
      description="Avatares stock e pessoas reais seguem direitos, versões e gates diferentes. Nenhum candidato é liberado por aparência."
      actions={
        <Button
          actionId="IDENTITY-START-ENROLLMENT"
          tone="primary"
          onClick={() => setEnrolling((current) => !current)}
        >
          Cadastrar identidade própria
        </Button>
      }
    >
      {loading && <HonestState state="loading" detail="Carregando versões e consentimentos…" />}
      {error && (
        <HonestState
          state="recoverable-error"
          detail={error}
          actionLabel="Tentar novamente"
          actionId="IDENTITY-RETRY-LOAD"
          onAction={() => void load()}
        />
      )}

      <section className="cx-identity-library" aria-label="Avatares stock pré-selecionados">
        <header>
          <div>
            <small>CATÁLOGO STOCK · 3 MULHERES + 3 HOMENS</small>
            <h2>Seis direções de presença</h2>
          </div>
          <p>
            O slot visual pode ser explorado agora. Produção só habilita quando identidade sintética,
            modelo, licença e provider estão ativos no workspace.
          </p>
        </header>
        <div className="cx-stock-avatar-grid">
          {STOCK_AVATAR_CANDIDATES.map((avatar) => {
            const profile = identities.find((item) => item.subjectKey === avatar.subjectKey);
            const activeVersion = profile
              ? versions[profile.id]?.find((version) => version.status === "active")
              : undefined;
            const usable = Boolean(
              activeVersion && profile?.status === "active" && presenterCapability?.providerReady,
            );
            return (
              <article key={avatar.id} data-avatar-status={usable ? "ready" : "candidate"}>
                <div className="cx-stock-avatar-mark" style={{ "--avatar-accent": avatar.accent } as React.CSSProperties}>
                  <span>{avatar.displayName.slice(0, 1)}</span>
                  <small>{avatar.presentation === "woman" ? "F" : "M"}</small>
                </div>
                <h3>{avatar.displayName}</h3>
                <p>{avatar.direction}</p>
                <small>{avatar.voiceLabel}</small>
                <em>{usable ? `Ativo · identidade v${activeVersion.version}` : "Candidato · ativação pendente"}</em>
                {usable ? (
                  <Button
                    actionId="IDENTITY-SELECT-STOCK"
                    onClick={() =>
                      navigate(
                        `/content/post-ritual/edit?mode=presenter&avatar=${avatar.id}&identityVersion=${activeVersion.id}`,
                      )
                    }
                  >
                    Usar no Presenter
                  </Button>
                ) : (
                  <Button
                    actionId="IDENTITY-PREVIEW-STOCK"
                    disabled={!demo}
                    title={!demo ? "Provider, modelo, licença e IdentityVersion ativa são obrigatórios" : undefined}
                    onClick={() =>
                      navigate(`/content/post-ritual/edit?mode=presenter&avatar=${avatar.id}&preview=1`)
                    }
                  >
                    {demo ? "Ver prévia local" : "Ativação pendente"}
                  </Button>
                )}
              </article>
            );
          })}
        </div>
      </section>

      {enrolling && (
        <form className="cx-identity-enrollment" onSubmit={submitEnrollment}>
          <header>
            <div><small>CAPTURE & CONSENT</small><h2>Candidato privado, nunca ativação automática</h2></div>
            <button
              type="button"
              data-action-id="IDENTITY-CLOSE-ENROLLMENT"
              onClick={() => setEnrolling(false)}
              aria-label="Fechar cadastro"
            >
              ×
            </button>
          </header>
          <p>
            Este fluxo registra escopo, expiração e evidência. A versão nasce como rascunho e exige avaliação e revisão independentes antes de qualquer amostra.
          </p>
          <div className="cx-identity-enrollment-grid">
            <label htmlFor="identity-person-name">Nome da pessoa<input data-action-id="IDENTITY-EDIT-ENROLLMENT" id="identity-person-name" required value={name} onChange={(event) => setName(event.target.value)} /></label>
            <label htmlFor="identity-consent-expiry">Válido até<input data-action-id="IDENTITY-EDIT-ENROLLMENT" id="identity-consent-expiry" required type="date" value={expiresOn} min={new Date().toISOString().slice(0, 10)} onChange={(event) => setExpiresOn(event.target.value)} /></label>
            <label className="is-wide" htmlFor="identity-purpose">Finalidade<textarea data-action-id="IDENTITY-EDIT-ENROLLMENT" id="identity-purpose" required rows={3} value={purpose} onChange={(event) => setPurpose(event.target.value)} /></label>
            <label className="is-wide" htmlFor="identity-private-capture">Vídeo privado de consentimento e captura<input data-action-id="IDENTITY-SELECT-PRIVATE-MEDIA" id="identity-private-capture" required type="file" accept="video/*" onChange={(event) => setCapture(event.target.files?.[0])} /><small>Usado como evidência e amostra privada; não é publicado.</small></label>
            <label className="is-wide" htmlFor="identity-private-voice">Áudio privado para matrícula de voz<input data-action-id="IDENTITY-SELECT-PRIVATE-MEDIA" id="identity-private-voice" required type="file" accept="audio/*" onChange={(event) => setVoiceCapture(event.target.files?.[0])} /><small>Corpus separado para avaliação de voz; nunca é usado como prova visual.</small></label>
          </div>
          <label className="cx-identity-declaration">
            <input data-action-id="IDENTITY-EDIT-ENROLLMENT" type="checkbox" checked={declared} onChange={(event) => setDeclared(event.target.checked)} />
            Confirmo que a pessoa identificada autorizou identity.enroll, avatar.generate, voice.enroll e voice.clone para a finalidade e prazo informados.
          </label>
          <Button
            actionId="IDENTITY-SUBMIT-ENROLLMENT"
            tone="primary"
            type="submit"
            disabled={saving || !declared || !capture || !voiceCapture || !name.trim() || !purpose.trim()}
          >
            {saving ? "Protegendo captura…" : "Criar candidato para revisão"}
          </Button>
        </form>
      )}

      {!demo && !loading && (
        <section className="cx-governed-identities">
          <header><small>IDENTIDADES DO WORKSPACE</small><h2>Versões e consentimentos reais</h2></header>
          {identities.length === 0 ? (
            <HonestState state="empty" detail="Nenhuma identidade foi cadastrada neste workspace." />
          ) : identities.map((identity) => {
            const currentVersions = versions[identity.id] ?? [];
            const consent = consents.find((item) => item.subjectKey === identity.subjectKey);
            const linkedVoices = voices.filter((voice) => voice.identityProfileId === identity.id);
            const activeIdentityVersion = currentVersions.find((version) => version.status === "active");
            const activeVoice = linkedVoices.find((voice) => voice.status === "active");
            const activeVoiceVersion = activeVoice
              ? voiceVersions[activeVoice.id]?.find((version) => version.status === "active")
              : undefined;
            return (
              <article key={identity.id}>
                <div><b>{identity.displayName}</b><small>{identity.identityType} · {identity.status}</small></div>
                <span>{currentVersions.length} versão(ões) · {currentVersions[0]?.status ?? "sem versão"}</span>
                <span>{linkedVoices.length} voz(es) · {activeVoiceVersion ? `voz v${activeVoiceVersion.version} ativa` : "sem voz ativa"}</span>
                <em>Consentimento: {consent?.status ?? "ausente"}{consent?.expiresAt ? ` · expira ${new Date(consent.expiresAt).toLocaleDateString("pt-BR")}` : ""}</em>
                {activeIdentityVersion && activeVoiceVersion && consent?.status === "active" && (
                  <Button
                    actionId="IDENTITY-SELECT-STOCK"
                    onClick={() =>
                      navigate(
                        `/content/post-ritual/edit?mode=presenter&identityVersion=${activeIdentityVersion.id}&voiceVersion=${activeVoiceVersion.id}&consent=${consent.id}`,
                      )
                    }
                  >
                    Usar identidade e voz no Presenter
                  </Button>
                )}
                {consent?.status === "active" && (
                  <Button
                    actionId="IDENTITY-REVOKE-CONSENT"
                    onClick={() => {
                      if (!window.confirm("Revogar este consentimento bloqueará usos futuros e versões vinculadas. Continuar?")) return;
                      void productApi.revokeStudioConsent(consent.id, "Revogado pelo responsável no Identity Library")
                        .then(() => load())
                        .then(() => setToast("Consentimento revogado; usos futuros foram bloqueados."))
                        .catch((requestError) => setError(requestError instanceof Error ? requestError.message : "Não foi possível revogar."));
                    }}
                  >
                    Revogar consentimento
                  </Button>
                )}
              </article>
            );
          })}
        </section>
      )}
    </Page>
  );
}

function safeImageLabReturn(value: string | null) {
  if (!value) return "/library/assets";
  if (value === "/library/assets") return value;
  if (/^\/content\/[^/?#]+\/edit(?:\?[^#]*)?$/.test(value)) return value;
  return "/library/assets";
}

function ImageLabSurface({ data, navigate, params, pathname, setToast }: AnyRecord) {
  const assetId = decodeURIComponent(pathname.split("/")[3] || "");
  const demoIndex = assetId.startsWith("demo-")
    ? Number(assetId.replace("demo-", "")) || 0
    : -1;
  const demoSource = demoIndex >= 0 ? phase3Arts[demoIndex % phase3Arts.length] : "";
  const asset = data.snapshot?.assets?.find((item: AnyRecord) => item.id === assetId);
  const returnTarget = safeImageLabReturn(params.get("returnTo"));
  const [sourceUrl, setSourceUrl] = React.useState(demoSource);
  const [derivedUrl, setDerivedUrl] = React.useState("");
  const [derivedAsset, setDerivedAsset] = React.useState<AnyRecord>();
  const [brightness, setBrightness] = React.useState(1);
  const [contrast, setContrast] = React.useState(1);
  const [comparison, setComparison] = React.useState(55);
  const [maskEnabled, setMaskEnabled] = React.useState(false);
  const [maskShape, setMaskShape] = React.useState<"rectangle" | "ellipse">("ellipse");
  const [protectFace, setProtectFace] = React.useState(false);
  const [protectProduct, setProtectProduct] = React.useState(true);
  const [protectLogo, setProtectLogo] = React.useState(false);
  const [status, setStatus] = React.useState<"loading" | "ready" | "saving" | "error">(
    demoSource ? "ready" : "loading",
  );
  const [error, setError] = React.useState("");

  React.useEffect(() => {
    if (demoSource) {
      setSourceUrl(demoSource);
      setStatus("ready");
      return;
    }
    if (!asset?.id) return;
    let objectUrl = "";
    let current = true;
    setStatus("loading");
    void productApi
      .studioAssetBlob(asset.id)
      .then((blob) => {
        if (!current) return;
        objectUrl = URL.createObjectURL(blob);
        setSourceUrl(objectUrl);
        setStatus("ready");
      })
      .catch((requestError) => {
        if (!current) return;
        setError(requestError instanceof Error ? requestError.message : "Não foi possível abrir a imagem privada.");
        setStatus("error");
      });
    return () => {
      current = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [asset?.id, demoSource]);
  React.useEffect(
    () => () => {
      if (derivedUrl.startsWith("blob:")) URL.revokeObjectURL(derivedUrl);
    },
    [derivedUrl],
  );

  if (!demoSource && data.status === "loading") {
    return <HonestState state="loading" title="Abrindo Image Lab…" detail="Validando o ativo privado e seu checksum." />;
  }
  if (!demoSource && !asset) {
    return (
      <HonestState
        state="empty"
        title="Imagem não encontrada"
        detail="O ativo não existe neste workspace ou você não possui acesso."
        preserved="nenhum arquivo foi alterado"
        actionLabel="Voltar à Biblioteca"
        actionId="IMAGE-RETURN"
        onAction={() => navigate("/library/assets")}
      />
    );
  }
  const protectedRegions = [
    ...(protectFace
      ? [{ kind: "face" as const, label: "Rosto", x: 0.32, y: 0.08, width: 0.36, height: 0.28 }]
      : []),
    ...(protectProduct
      ? [{ kind: "product" as const, label: "Produto central", x: 0.3, y: 0.35, width: 0.4, height: 0.42 }]
      : []),
    ...(protectLogo
      ? [{ kind: "logo" as const, label: "Assinatura", x: 0.66, y: 0.84, width: 0.26, height: 0.1 }]
      : []),
  ];
  const createDerivation = async () => {
    setError("");
    if (demoSource) {
      setDerivedUrl(demoSource);
      setDerivedAsset({ id: `demo-derived-${demoIndex}`, title: "Derivação demonstrativa" });
      setToast("Derivação demonstrativa criada apenas nesta sessão");
      return;
    }
    if (!asset?.checksumSha256 || !data.activeWorkspace?.id) {
      setError("Este ativo não possui checksum verificável e não pode ser derivado com segurança.");
      return;
    }
    setStatus("saving");
    try {
      const idempotencyKey = `image-${asset.id}-${crypto.randomUUID()}`;
      const created = await productApi.deriveStudioImage(asset.id, {
        workspaceId: data.activeWorkspace.id,
        title: `${asset.title} · derivação`,
        brightness,
        contrast,
        editMask: maskEnabled
          ? { shape: maskShape, x: 0.1, y: 0.12, width: 0.8, height: 0.72 }
          : null,
        protectedRegions,
        expectedSourceChecksumSha256: asset.checksumSha256,
        idempotencyKey,
      });
      const blob = await productApi.studioAssetBlob(created.id);
      const objectUrl = URL.createObjectURL(blob);
      setDerivedUrl((previous: string) => {
        if (previous.startsWith("blob:")) URL.revokeObjectURL(previous);
        return objectUrl;
      });
      setDerivedAsset(created);
      setComparison(50);
      setStatus("ready");
      await data.refresh();
      setToast("Derivação privada criada; o original permanece intacto");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Não foi possível criar a derivação.");
      setStatus("error");
    }
  };
  const returnWithAsset = () => {
    const destination = derivedAsset
      ? `${returnTarget}${returnTarget.includes("?") ? "&" : "?"}derivedAsset=${encodeURIComponent(derivedAsset.id)}`
      : returnTarget;
    navigate(destination);
  };
  return (
    <section className="cx-image-lab">
      <header>
        <button data-action-id="IMAGE-RETURN" onClick={() => navigate(returnTarget)}>
          ← Voltar
        </button>
        <div>
          <small>IMAGE LAB · EDIÇÃO NÃO DESTRUTIVA</small>
          <h1>{asset?.title || "Imagem demonstrativa"}</h1>
        </div>
        <Chip tone="green">ORIGINAL IMUTÁVEL</Chip>
        <Button actionId="IMAGE-RETURN" onClick={returnWithAsset}>
          {derivedAsset ? "Voltar com derivação" : "Voltar sem aplicar"}
        </Button>
        <Button
          tone="primary"
          actionId="IMAGE-CREATE-DERIVATION"
          disabled={status === "saving" || (!demoSource && !asset?.checksumSha256)}
          onClick={() => void createDerivation()}
        >
          {status === "saving" ? "Criando…" : "Criar derivação privada"}
        </Button>
      </header>
      <aside className="cx-image-controls">
        <h2>Ajustes</h2>
        <label>
          Brilho <b>{Math.round(brightness * 100)}%</b>
          <input data-action-id="IMAGE-ADJUST-PARAMETER" type="range" min="0.5" max="1.5" step="0.05" value={brightness} onChange={(event) => setBrightness(Number(event.target.value))} />
        </label>
        <label>
          Contraste <b>{Math.round(contrast * 100)}%</b>
          <input data-action-id="IMAGE-ADJUST-PARAMETER" type="range" min="0.5" max="1.5" step="0.05" value={contrast} onChange={(event) => setContrast(Number(event.target.value))} />
        </label>
        <hr />
        <h2>Máscara de edição</h2>
        <label className="cx-motion-toggle">
          <input data-action-id="IMAGE-TOGGLE-MASK" type="checkbox" checked={maskEnabled} onChange={(event) => setMaskEnabled(event.target.checked)} />
          Limitar ajuste a uma região
        </label>
        <div className="cx-image-mask-shape">
          {(["ellipse", "rectangle"] as const).map((shape) => (
            <button
              key={shape}
              data-action-id="IMAGE-SELECT-MASK-SHAPE"
              className={maskShape === shape ? "is-active" : ""}
              disabled={!maskEnabled}
              onClick={() => setMaskShape(shape)}
            >
              {shape === "ellipse" ? "Elipse" : "Retângulo"}
            </button>
          ))}
        </div>
        <hr />
        <h2>Regiões protegidas</h2>
        <p>Pixels nestas áreas são copiados do original.</p>
        {[
          ["Rosto", protectFace, setProtectFace],
          ["Produto central", protectProduct, setProtectProduct],
          ["Logo", protectLogo, setProtectLogo],
        ].map(([label, checked, setter]) => (
          <label className="cx-motion-toggle" key={String(label)}>
            <input data-action-id="IMAGE-TOGGLE-PROTECTION" type="checkbox" checked={Boolean(checked)} onChange={(event) => (setter as React.Dispatch<React.SetStateAction<boolean>>)(event.target.checked)} />
            Bloquear {String(label).toLowerCase()}
          </label>
        ))}
        <StateBanner
          tone="blue"
          title="Locks explícitos, não inferidos"
          detail="Neste corte, você define as regiões. Detecção automática só será liberada após benchmark."
        />
      </aside>
      <main className="cx-image-stage">
        {status === "loading" ? (
          <HonestState
            state="loading"
            title="Carregando mídia privada…"
            detail="O original está sendo materializado apenas para esta sessão autenticada."
          />
        ) : sourceUrl ? (
          <div className="cx-image-compare-stage">
            <img src={sourceUrl} alt="Original" />
            <div className="cx-image-after" style={{ width: `${comparison}%` }}>
              <img
                src={derivedUrl || sourceUrl}
                alt={derivedUrl ? "Derivação exata" : "Prévia local do ajuste"}
                style={derivedUrl ? undefined : { filter: `brightness(${brightness}) contrast(${contrast})` }}
              />
            </div>
            <i style={{ left: `${comparison}%` }}><span>ANTES</span><span>DEPOIS</span></i>
            {maskEnabled && <span className={`cx-image-mask is-${maskShape}`} />}
            {protectedRegions.map((region) => (
              <span
                className={`cx-image-lock is-${region.kind}`}
                key={region.kind}
                style={{ left: `${region.x * 100}%`, top: `${region.y * 100}%`, width: `${region.width * 100}%`, height: `${region.height * 100}%` }}
              >
                {region.label}
              </span>
            ))}
          </div>
        ) : null}
        <label className="cx-image-compare-control">
          Comparação
          <input
            data-testid="image-compare"
            data-action-id="IMAGE-COMPARE"
            aria-label="Comparar antes e depois"
            type="range"
            min="0"
            max="100"
            value={comparison}
            onChange={(event) => setComparison(Number(event.target.value))}
          />
        </label>
        <Button
          actionId="IMAGE-COMPARE"
          onClick={() => setComparison((value) => (value < 100 ? 100 : 0))}
        >
          {comparison < 100 ? "Ver depois completo" : "Ver original completo"}
        </Button>
      </main>
      <aside className="cx-image-lineage">
        <h2>Saída e linhagem</h2>
        <KeyValue label="Origem" value={asset?.id || `demo-${demoIndex}`} />
        <KeyValue label="Checksum" value={asset?.checksumSha256 ? `${asset.checksumSha256.slice(0, 12)}…` : "Demonstração local"} />
        <KeyValue label="Máscara" value={maskEnabled ? maskShape : "Imagem inteira"} />
        <KeyValue label="Locks" value={protectedRegions.map((item) => item.label).join(", ") || "Nenhum"} />
        {error && <StateBanner tone="orange" title="Nada foi alterado" detail={error} />}
        {derivedAsset ? (
          <StateBanner
            tone="green"
            title="Derivação pronta para revisão"
            detail={`Novo asset ${derivedAsset.id}. O original continua disponível.`}
          />
        ) : (
          <StateBanner
            tone="orange"
            title="Prévia ainda não é um arquivo"
            detail="Crie a derivação para fixar checksum, provider e regiões protegidas."
          />
        )}
      </aside>
    </section>
  );
}

function PresenterStudioSurface({
  navigate,
  setToast,
  data,
  demo,
  brand,
  params,
  pathname,
}: AnyRecord) {
  const [generated, setGenerated] = React.useState(false);
  const [captured, setCaptured] = React.useState(false);
  const [scenario, setScenario] = React.useState<"yes" | "no" | "">("");
  const [materialTab, setMaterialTab] = React.useState<
    "video" | "voice" | "brand"
  >("video");
  const [rulesOpen, setRulesOpen] = React.useState(false);
  const [avatarProvider, setAvatarProvider] = React.useState<AnyRecord>();
  const [avatarJob, setAvatarJob] = React.useState<AnyRecord>();
  const [avatarJobError, setAvatarJobError] = React.useState<string>();
  const [avatarDocument, setAvatarDocument] = React.useState<AnyRecord>();
  const workspaceId = data.activeWorkspace?.id as string | undefined;
  const contentId = pathname?.split("/")[2] as string | undefined;
  const post = data.snapshot?.posts?.find((item: AnyRecord) => item.id === contentId);
  const presenterCapability = data.snapshot?.studioCapabilities?.presenter;
  const providerReady = Boolean(presenterCapability?.providerReady);
  // Authenticated capture must go through the governed private ingest in the
  // Identity Library. Capability readiness alone must never persist a fake
  // capture boolean as evidence.
  const captureReady = demo;
  const captureCapabilityReady = Boolean(presenterCapability?.captureReady);
  const publicationReady = !demo && Boolean(presenterCapability?.publicationAllowed);
  const selectedAvatar = STOCK_AVATAR_CANDIDATES.find(
    (avatar) => avatar.id === params?.get("avatar"),
  );
  const selectedIdentityVersionId = params?.get("identityVersion") as string | null;
  const selectedVoiceVersionId = params?.get("voiceVersion") as string | null;
  const selectedConsentId = params?.get("consent") as string | null;
  // Authenticated production remains fail-closed until Presenter owns a real
  // observable avatar_video job. The guest path is explicitly local only.
  const canGenerate = demo || Boolean(
    providerReady &&
      selectedIdentityVersionId &&
      selectedVoiceVersionId &&
      selectedConsentId &&
      avatarProvider,
  );
  const productionSelectionReady = Boolean(
    !demo &&
      providerReady &&
      presenterCapability?.captureReady &&
      selectedIdentityVersionId &&
      selectedVoiceVersionId &&
      selectedConsentId,
  );
  React.useEffect(() => {
    if (demo || !workspaceId) return;
    let active = true;
    void Promise.all([
      productApi.studioProviders(workspaceId, "avatar_video"),
      productApi.studioDocuments(workspaceId, { postId: contentId }),
    ]).then(async ([providers, documents]) => {
      if (!active) return;
      const approved = providers.find((provider) => provider.status === "approved");
      const document = documents.find((candidate) => candidate.contentType === "presenter");
      setAvatarProvider(approved);
      setAvatarDocument(document);
      if (document) {
        const jobs = await productApi.studioGenerationJobs(workspaceId, {
          documentId: document.documentId,
          jobType: "avatar_video",
          limit: 1,
        });
        if (active) setAvatarJob(jobs[0]);
      }
    }).catch((requestError) => {
      if (active) setAvatarJobError(requestError instanceof Error ? requestError.message : "Falha ao carregar o Presenter.");
    });
    return () => { active = false; };
  }, [contentId, demo, workspaceId]);

  React.useEffect(() => {
    if (!avatarJob || !["queued", "running", "retrying"].includes(avatarJob.status)) return;
    const timer = window.setTimeout(() => {
      void productApi.studioGenerationJob(avatarJob.id)
        .then(setAvatarJob)
        .catch((requestError) => setAvatarJobError(requestError instanceof Error ? requestError.message : "Não foi possível atualizar o job."));
    }, 900);
    return () => window.clearTimeout(timer);
  }, [avatarJob]);

  const generatePrivateSample = async () => {
    if (!workspaceId || !selectedIdentityVersionId || !selectedVoiceVersionId || !selectedConsentId || !avatarProvider) {
      setToast("Selecione identidade, voz, consentimento e provider aprovados");
      return;
    }
    setAvatarJobError(undefined);
    try {
      let document = avatarDocument;
      if (!document) {
        document = await productApi.createStudioDocument({
          workspaceId,
          title: post?.title || "Amostra Presenter privada",
          contentType: "presenter",
          campaignId: post?.campaignId ?? null,
          postId: post?.id ?? null,
          opportunityId: null,
          brandRevision: Math.max(1, data.activeWorkspace?.brandProfile?.versions?.length || 1),
          brief: {
            schemaVersion: "studio.creative-brief.v1",
            objective: post?.objective || "Criar amostra privada para revisão humana",
            audience: data.activeWorkspace?.brandProfile?.targetAudience || "Público da marca",
            angle: "Apresentação humana, consentida e fiel à marca",
            promise: "Uma amostra privada pronta para edição e revisão",
            tone: data.activeWorkspace?.brandProfile?.tone || "Humano e preciso",
            hook: post?.copy || "Conheça a proposta.",
            cta: "Conheça a marca",
            channel: "instagram",
            format: "reel-vertical",
            restrictions: ["Não publicar sem revisão humana", "Não alterar traços da identidade"],
            hypotheses: ["Uma presença consentida aumenta confiança sem perder controle"],
            evidence: [],
          },
          composition: {
            pages: [{
              id: `presenter-${crypto.randomUUID()}`,
              role: "ugc",
              width: 1080,
              height: 1920,
              safeArea: 48,
              background: "#10181c",
              layers: [],
            }],
          },
          assets: [],
        });
        setAvatarDocument(document);
      }
      const nextJob = await productApi.enqueueStudioGenerationJob({
        workspaceId,
        documentId: document.documentId,
        consentGrantId: selectedConsentId,
        identityVersionId: selectedIdentityVersionId,
        voiceVersionId: selectedVoiceVersionId,
        jobType: "avatar_video",
        provider: avatarProvider.provider,
        request: {
          schemaVersion: "studio.avatar-video-request.v1",
          script: post?.copy || "Conheça a proposta.",
          locale: "pt-BR",
          width: 1080,
          height: 1920,
          fps: 30,
          disclosureLabel: "Conteúdo sintético",
        },
      }, `avatar-video-${crypto.randomUUID()}`);
      setAvatarJob(nextJob);
      setToast("Amostra privada enviada ao worker de visão");
    } catch (requestError) {
      setAvatarJobError(requestError instanceof Error ? requestError.message : "O job foi bloqueado com segurança.");
    }
  };
  React.useEffect(() => {
    const session = (data.snapshot?.presenterSessions || []).find(
      (item: AnyRecord) => item.resourceKey === "post-ritual",
    );
    if (!session) return;
    setGenerated(Boolean(session.payload?.generated) && demo);
    setCaptured(Boolean(session.payload?.captured) && captureReady);
    setScenario(session.payload?.scenario || "");
  }, [captureReady, data.snapshot?.presenterSessions, demo]);
  const persist = (next: AnyRecord) => {
    if (demo) return;
    void data.saveWorkspaceResource("presenter_session", "post-ritual", {
      generated,
      captured,
      scenario,
      rights: "unverified",
      externalPublishing: false,
      updatedAt: new Date().toISOString(),
      ...next,
    });
  };
  const isHorizonte = brand?.id === "horizonte";
  const materialRowsByTab = {
    video: demo
      ? [
          ["3 takes aprovados", "Expressão, pausas e planos", "✓"],
          ["4 cenários reais", "Escritório, bancada e externo", "✓"],
          ["Plano principal", "Vertical · 1080 × 1920", "✓"],
          ["Luz e continuidade", "Revisão visual demonstrativa", "✓"],
        ]
      : [
          ["Fonte humana não verificada", "Consentimento e asset privado pendentes", "—"],
          ["Cenário sem evidência", "A análise física ainda não foi executada", "—"],
          ["Plano principal", "Aguardando mídia privada", "—"],
          ["Continuidade", "Benchmark visual pendente", "—"],
        ],
    voice: demo
      ? [
          ["2 áudios limpos", "Voz natural · 4 min 18 s", "✓"],
          ["Cadência", "PT-BR · conversa segura", "✓"],
          ["Ruído de fundo", "Dentro do limite demonstrativo", "✓"],
          ["Clone de voz", "Simulação local · não publicável", "✓"],
        ]
      : [
          ["Voz não matriculada", "Nenhuma versão aprovada para este workspace", "—"],
          ["Consentimento de voz", "Grant voice.clone pendente", "—"],
          ["Qualidade acústica", "Corpus privado não avaliado", "—"],
          ["Clone de voz", "Provider ainda desativado", "—"],
        ],
    brand: demo
      ? [
          ["Brand kit aplicado", "Cores, tipografia e produto", "✓"],
          ["Produto preservado", "Forma e embalagem sem alteração", "✓"],
          ["Tom editorial", "Humano, seguro e preciso", "✓"],
          ["CTA", "Aplicado ao teste local", "✓"],
        ]
      : [
          ["Brand kit disponível", "Aplicação pode ser revisada sem publicar", "✓"],
          ["Produto", "Asset final ainda não selecionado", "—"],
          ["Tom editorial", "Aguardando revisão da marca", "—"],
          ["CTA", "Aguardando roteiro aprovado", "—"],
        ],
  };
  const materialRows = materialRowsByTab[materialTab];
  const scoreRows = [
    ["REALISMO", demo ? "94/100" : "—"],
    ["VOZ", demo ? "91/100" : "—"],
    ["MARCA", demo ? "96/100" : "—"],
    ["CENA", demo ? (captured ? "91/100" : "82/100") : "—"],
  ];
  return (
    <section className="cx-presenter-studio">
      <aside className="cx-production-rail">
        <header>
          <b>Clicko*</b>
          <span>Video Studio</span>
        </header>
        <section>
          <small>EM PRODUÇÃO · 62%</small>
          <h2>{isHorizonte ? "Cuidar antes da urgência" : "Ritual de Foco"}</h2>
          <p>
            Identidade · {isHorizonte ? "Especialista real" : "Founder-led"}
          </p>
        </section>
        <section>
          <small>FLUXO DE PRODUÇÃO</small>
          <p>
            ✓ Direção
            <br />✓ Roteiro
          </p>
          <b>● Materiais</b>
          <p>
            ○ Montagem
            <br />○ Revisão
            <br />○ Entrega
          </p>
          <em>
            PRÓXIMO GATE
            <br />
            Validar 2 fontes reais
          </em>
        </section>
        <section>
          <small>BANDEJAS DA CÉLULA</small>
          <b>
            Fontes reais <i>8</i>
          </b>
          <b>
            Cenas <i>4</i>
          </b>
          <b>
            Versões <i>3</i>
          </b>
        </section>
        <footer>
          <button
            data-action-id="CONTENT-BACK-INVENTORY"
            onClick={() => navigate("/content")}
          >
            ← Voltar ao projeto
          </button>
          <small>SALVO · HÁ 12 S</small>
          <Button
            actionId="PRESENTER-SAVE-EXIT"
            onClick={() => {
              setToast("Célula salva");
              navigate("/content");
            }}
          >
            Salvar e sair
          </Button>
        </footer>
      </aside>
      <div className="cx-presenter-main">
        <header>
          <span>
            VIDEO STUDIO　/　FACTORY CELL　/　{demo
              ? "DEMONSTRAÇÃO LOCAL"
              : providerReady
                ? "PROVIDER ATIVO"
                : "PRÉVIA SEM PROVIDER"}
          </span>
          <div>
            <h1>
               {selectedAvatar
                 ? `${selectedAvatar.displayName} × ${brand?.name || "marca"}`
                 : isHorizonte
                   ? "Dra. Renata × Clínica Horizonte"
                   : "Mariana × Café Aurora"}
            </h1>
            <small>
              Identidade de produção para{" "}
              {isHorizonte ? "Cuidar antes da urgência" : "Ritual de Foco"} —
              {demo
                ? "pronta para gerar exemplos locais, não para publicar."
                : providerReady
                  ? publicationReady
                    ? "provider atestado; consentimento de publicação verificado, revisão humana ainda obrigatória."
                    : "provider atestado; publicação exige consentimento publish.synthetic e revisão humana."
                  : "interface preparada; provider, consentimento e benchmark ainda não estão ativos."}
            </small>
            <div
              className="cx-presenter-editor-switcher"
              aria-label="Modos de edição"
            >
                <button
                  className="is-active"
                  aria-current="page"
                  disabled
                  title="Você já está na seleção de avatares."
                >
                  <Users size={15} /> Avatares
                </button>
                <button
                  data-action-id="PRESENTER-OPEN-IDENTITIES"
                  onClick={() => navigate("/library/identities")}
                >
                  <UserRoundCheck size={15} /> Identidades
                </button>
              <button
                data-action-id="PRESENTER-OPEN-VISUAL"
                onClick={() =>
                  navigate("/content/post-ritual/edit?mode=visual")
                }
              >
                <Image size={15} /> Editar foto
              </button>
              <button
                data-action-id="PRESENTER-OPEN-VIDEO"
                onClick={() =>
                  navigate("/content/post-ritual/edit?mode=video")
                }
              >
                <Play size={15} /> Editar vídeo
              </button>
            </div>
          </div>
          <nav>
            <i>CONTEXTO ✓</i>
            <i>MATERIAIS 8/10</i>
            <i>{demo ? "CALIBRANDO" : providerReady ? "PROVIDER ATIVO" : "PROVIDER PENDENTE"}</i>
            <i>TESTES {generated ? "1/3" : "0/3"}</i>
          </nav>
          {demo ? (
            <Button
              tone="primary"
              actionId="PRESENTER-PREVIEW-DEMO"
              onClick={() => {
                setGenerated(true);
                setToast("Demonstração local pronta; nenhum job ou artefato publicável foi criado.");
              }}
            >
              Gerar demonstração local
            </Button>
          ) : (
            <Button
              tone="primary"
              actionId="PRESENTER-GENERATE-SAMPLE"
              disabled={!canGenerate || ["queued", "running", "retrying"].includes(avatarJob?.status)}
              title="A geração real exige um job avatar_video observável e ligado aos direitos exatos"
              onClick={() => void generatePrivateSample()}
            >
              {["queued", "running", "retrying"].includes(avatarJob?.status)
                ? `Gerando amostra · ${avatarJob.progress ?? 0}%`
                : productionSelectionReady
                  ? "Gerar amostra privada"
                  : "Direitos ou provider pendentes"}
            </Button>
          )}
        </header>
        {avatarJobError && <HonestState compact state="recoverable-error" detail={avatarJobError} />}
        {avatarJob && !demo && (
          <div className="cx-presenter-job" role="status" aria-live="polite">
            <b>Job Presenter · {avatarJob.status}</b>
            <span>{avatarJob.progress}% · {avatarJob.provider}</span>
            {avatarJob.status === "succeeded" && avatarJob.result?.assetId && (
              <Button
                actionId="PRESENTER-OPEN-VIDEO"
                onClick={async () => {
                  await data.refresh();
                  navigate(`/content/${contentId || "post-ritual"}/edit?mode=video&sourceAsset=${avatarJob.result.assetId}`);
                }}
              >
                Abrir amostra no Video Studio
              </Button>
            )}
          </div>
        )}
        <div className="cx-presenter-focusbar">
          <article>
            <small>1 · O SISTEMA ESTÁ FAZENDO</small>
            <b>
              {!canGenerate
                  ? "Aguardando provider de voz/identidade e evidência de consentimento"
                : captured
                ? "Recalibrando a cena com a nova pausa"
                : "Calibrando rosto, voz, marca e cenário"}
            </b>
          </article>
          <article className="is-decision">
            <small>2 · SUA DECISÃO AGORA</small>
            <b>
              {scenario
                ? `Cenário ${scenario === "yes" ? "aceito" : "recusado"}`
                : "Aceitar o cenário de escritório?"}
            </b>
          </article>
          <article>
            <small>3 · RESULTADO DESTA ETAPA</small>
            <b>
              {generated
                ? "1 teste pronto para revisão humana"
                : demo
                  ? "Primeiro teste não publicável"
                  : "Nenhum teste gerado · provider pendente"}
            </b>
          </article>
        </div>
        <div className="cx-presenter-grid">
          <aside className="cx-presenter-materials">
            <small>MATÉRIA-PRIMA</small>
            <article>
              <img src="/canonical/figma/phase5/presenter-source.jpeg" />
              <b>
                  {selectedAvatar
                    ? `${selectedAvatar.displayName} · avatar stock candidato`
                    : isHorizonte
                    ? "Renata Lima · fonte real"
                    : "Mariana Costa · fonte real"}
              </b>
              <em>
                {demo
                  ? "Exemplo demonstrativo · não é consentimento real"
                  : providerReady
                    ? "Consentimento precisa ser verificado no workspace"
                    : "Consentimento não verificado · provider pendente"}
              </em>
            </article>
            <nav>
              {(["video", "voice", "brand"] as const).map((tab) => (
                <button
                  key={tab}
                  data-action-id="PRESENTER-SELECT-MATERIAL"
                  className={materialTab === tab ? "is-active" : ""}
                  aria-pressed={materialTab === tab}
                  onClick={() => setMaterialTab(tab)}
                >
                  {tab === "video"
                    ? "VÍDEO"
                    : tab === "voice"
                      ? "VOZ"
                      : "MARCA"}
                </button>
              ))}
            </nav>
            {materialRows.map(([a, b, status]) => (
              <span key={a}>
                <b>{a}</b>
                <small>{b}</small>
                <i>{status}</i>
              </span>
            ))}
            <section>
              <b>NÃO NEGOCIÁVEIS</b>
              <p>
                · Sem voz publicitária artificial
                <br />· Sem alterar traços do rosto
                <br />· Produto sempre fiel ao original
              </p>
              {rulesOpen && (
                <p className="cx-presenter-rule-detail">
                  Publicação exige consentimento separado, revisão humana e
                  aprovação do render exato. A demonstração nunca publica.
                </p>
              )}
              <button
                data-action-id="PRESENTER-TOGGLE-RULES"
                onClick={() => setRulesOpen((current) => !current)}
              >
                {rulesOpen ? "Fechar regras ↑" : "Editar regras →"}
              </button>
            </section>
            <Button
              actionId="PRESENTER-OPEN-IDENTITIES"
              onClick={() => navigate("/library/identities")}
            >
              {demo ? "Ver seis avatares e fontes" : "＋ Adicionar fonte consentida"}
            </Button>
          </aside>
          <main className="cx-presenter-bench">
            <small>BANCADA DE IDENTIDADE</small>
            <h2>Receita · Founder-led realista</h2>
            <div className="cx-presenter-composition">
              <article>
                <img src="/canonical/figma/phase5/presenter-source.jpeg" />
                <small>FONTE HUMANA · TAKE 07</small>
                <b>
                  {selectedAvatar
                    ? `${selectedAvatar.displayName} · ${selectedAvatar.direction}`
                    : demo
                    ? "Rosto, voz e cadência reais · exemplo"
                    : "Rosto, voz e cadência aguardando verificação"}
                </b>
              </article>
              <i>
                ＋<small>MARCA, ROTEIRO, CONTEXTO</small>
              </i>
              <article className="cx-generated-scene">
                <span>
                  {demo && generated ? "TESTE 01" : demo ? "TESTE 00" : "CONCEITO"} · NÃO PUBLICÁVEL
                </span>
                <img src="/canonical/figma/phase5/presenter-scene.jpeg" />
                <h3>“Clareza começa antes da primeira tarefa.”</h3>
                <small>25 S · Founder-led · Ritmo 6.5/10</small>
              </article>
            </div>
            <div className="cx-presenter-scores">
              {scoreRows.map(([a, b]) => (
                <span key={a}>
                  <small>{a}</small>
                  <b>{b}</b>
                </span>
              ))}
            </div>
            <div className="cx-presenter-next">
              <small>PRÓXIMA MELHOR AÇÃO</small>
              <b>
                {!captureReady
                  ? captureCapabilityReady
                    ? "Provider de captura disponível; registre a evidência privada no Identity Library."
                    : "Captura privada ainda não está conectada a um ingest autorizado."
                  : captured
                  ? "Pausas capturadas e cena recalibrada."
                  : "Capturar 8 s de pausa olhando para o produto."}
              </b>
              {!captureReady ? (
                <Button
                  tone="primary"
                  actionId="PRESENTER-OPEN-IDENTITIES"
                  onClick={() => navigate("/library/identities?enroll=1")}
                >
                  Abrir captura governada
                </Button>
              ) : (
                <Button
                  tone="primary"
                  actionId="PRESENTER-CAPTURE-LOCAL"
                  onClick={() => {
                    setCaptured(true);
                    persist({ captured: true });
                    setToast("Captura de pausa registrada");
                  }}
                >
                  {captured ? "Capturado" : "Abrir captura local"}
                </Button>
              )}
            </div>
          </main>
          <aside className="cx-presenter-limits">
            <small>DIREÇÃO & LIMITES</small>
            <section className="is-highlight">
              <small>PRESENÇA DESEJADA</small>
              <h3>Humana, segura e precisa.</h3>
              <p>Parece levemente curiosa — nunca uma personagem.</p>
            </section>
            <section>
              <small>DIREÇÃO CRIATIVA</small>
              {[
                ["Naturalidade", "92%"],
                ["Energia", "58%"],
                ["Premium", "72%"],
                ["UGC espontâneo", "46%"],
              ].map(([a, b]) => (
                <span key={a}>
                  <b>{a}</b>
                  <i style={{ width: b }} />
                  <em>{b}</em>
                </span>
              ))}
            </section>
            <section>
              <small>
                DIREITOS　 <em>VÁLIDOS</em>
              </small>
              <p>
                Rosto + voz <b>{demo ? "Exemplo" : "Não verificado"}</b>
                <br />
                Social + ads <b>
                  {demo
                    ? "Exemplo"
                    : publicationReady
                      ? "Consentimento OK · revisão"
                      : "Bloqueado"}
                </b>
                <br />
                Alterar traços <strong>Bloqueado</strong>
                <br />
                Política <em>{demo ? "Aprovação extra" : "Aguardando aprovação"}</em>
              </p>
            </section>
            <section>
              <small>GATES DE AUTENTICIDADE</small>
              <p>
                Rosto <b>{demo ? "Aprovado · exemplo" : "Não avaliado"}</b>
                <br />
                Voz <b>{demo ? "Aprovado · exemplo" : "Não avaliado"}</b>
                <br />
                Marca <b>{demo ? "Aprovado · exemplo" : "Disponível"}</b>
                <br />
                Cena <em>{demo ? (captured ? "Aprovado" : "Revisar luz") : "Não avaliada"}</em>
                <br />
                Publicação <b>
                  {demo
                    ? "Não publicável"
                    : publicationReady
                      ? "Consentimento OK · revisão"
                      : "Bloqueada"}
                </b>
              </p>
              <small>Nada sai desta célula sem revisão humana.</small>
            </section>
            <section className="is-decision">
              <small>1 DECISÃO SUA</small>
              <b>Aceitar o cenário de escritório?</b>
              <div>
                <button
                  data-action-id="PRESENTER-DECIDE-SCENARIO"
                  className={scenario === "no" ? "is-active" : ""}
                  onClick={() => {
                    setScenario("no");
                    persist({ scenario: "no" });
                  }}
                >
                  Não
                </button>
                <button
                  data-action-id="PRESENTER-DECIDE-SCENARIO"
                  className={scenario === "yes" ? "is-active" : ""}
                  onClick={() => {
                    setScenario("yes");
                    persist({ scenario: "yes" });
                  }}
                >
                  Sim
                </button>
              </div>
            </section>
          </aside>
          <section className="cx-presenter-tests">
            <header>
              <b>TESTES DE SAÍDA</b>
              <small>
                {demo
                  ? `Provar antes de liberar · ${generated ? "1/3" : "0/3"} aprovados`
                  : "Nenhum teste aprovado · provider pendente"}
              </small>
            </header>
            <div>
              {[
                ["FOUNDER-LED", "Autoridade íntima", "PRONTO PARA TESTE", 0],
                ["UGC NATURAL", "Descoberta e prova", "REVISAR RITMO", 0],
                ["EXPERT CUT", "Produto e clareza", "MATERIAL PENDENTE", 1],
              ].map(([a, b, c, img]) => (
                <article
                  key={String(a)}
                  className={
                    demo && generated && a === "FOUNDER-LED" ? "is-active" : ""
                  }
                >
                  <img
                    src={
                      img
                        ? "/canonical/figma/phase5/presenter-scene.jpeg"
                        : "/canonical/figma/phase5/presenter-source.jpeg"
                    }
                  />
                  <small>{a}　25 S</small>
                  <b>{b}</b>
                  <em>{demo ? c : "PROVIDER PENDENTE"}</em>
                </article>
              ))}
            </div>
            {generated && (
              <Button
                actionId="PRESENTER-OPEN-VIDEO"
                tone="primary"
                onClick={() => navigate("/content/post-ritual/edit?mode=video&source=presenter-demo")}
              >
                Abrir amostra no Video Studio
              </Button>
            )}
          </section>
        </div>
      </div>
    </section>
  );
}

function AppsSurface({ demo, navigate }: AnyRecord) {
  const apps = [
    [
      "Instagram",
      "Publicação e métricas",
      "IG",
      demo ? "Exemplo" : "Configurar",
    ],
    ["Google Drive", "Importação de assets", "GD", "Configurar"],
    ["Slack", "Avisos e aprovações", "SL", "Configurar"],
    ["Canva", "Fluxo de design", "CV", "Em breve"],
    ["Notion", "Briefings e documentos", "NT", "Em breve"],
    ["Zapier", "Automações", "ZP", "Em breve"],
  ];
  return (
    <Page
      eyebrow="Apps"
      title="Conecte seu fluxo"
      description="Integrações deixam dados e decisões circularem sem duplicar trabalho."
      actions={<Button icon={CircleHelp}>Como funciona</Button>}
    >
      <StateBanner
        title={demo ? "Workspace demonstrativo" : "Nenhuma conexão presumida"}
        detail={
          demo
            ? "Os estados abaixo são exemplos. Entre para configurar conexões reais."
            : "Uma integração só aparece conectada depois de autorização e verificação."
        }
      />
      <div className="cx-apps-feature">
        <div>
          <span>
            <Link2 />
          </span>
          <small>RECOMENDADO</small>
          <h2>Leve a campanha até a publicação</h2>
          <p>
            Conecte um canal para programar posts e trazer métricas reais de
            volta aos aprendizados.
          </p>
          <Button
            tone="primary"
            actionId="APPS-CONFIGURE-CHANNELS"
            onClick={() => navigate("/settings/channels")}
          >
            Configurar canais
          </Button>
        </div>
        <div className="cx-app-lines">
          <i />
          <i />
          <i />
          <span>IG</span>
          <span>TT</span>
          <span>YT</span>
        </div>
      </div>
      <div className="cx-app-grid">
        {apps.map(([name, desc, mark, status]) => (
          <article key={name}>
            <span>{mark}</span>
            <div>
              <h3>{name}</h3>
              <p>{desc}</p>
            </div>
            <button
              data-action-id="APPS-CONFIGURE-CHANNELS"
              disabled={status === "Em breve"}
              onClick={() => navigate("/settings/channels")}
            >
              {status}
            </button>
          </article>
        ))}
      </div>
    </Page>
  );
}

function CreateMenu({ navigate, onClose }: AnyRecord) {
  const [query, setQuery] = React.useState("");
  const intents = [
    [Radar, "Usar uma oportunidade", "Do Radar para uma campanha", "/radar"],
    [
      Target,
      "Criar a partir de uma oferta",
      "Produto, público e objetivo",
      "/campaigns/new",
    ],
    [
      WandSparkles,
      "Reutilizar um vencedor",
      "Preserve o que funcionou",
      "/content/post-ritual/remix",
    ],
    [
      FileText,
      "Começar com um briefing",
      "Transforme uma demanda em peças",
      "/content/draft/edit?mode=editorial",
    ],
  ] as const;
  const groups = [
    [
      "Produzir conteúdo",
      [
        [Image, "Post para Instagram", "/content/draft/edit?mode=visual"],
        [Layers3, "Carrossel", "/content/draft/edit?mode=carousel"],
        [Play, "Stories ou Reels", "/content/draft/edit?mode=video"],
      ],
    ],
    [
      "Planejar e organizar",
      [
        [FolderKanban, "Campanha", "/campaigns/new"],
        [CalendarDays, "Calendário editorial", "/calendar"],
        [Radar, "Explorar Radar", "/radar"],
      ],
    ],
    [
      "Adaptar e reutilizar",
      [
        [Copy, "Gerar variações", "/content/post-ritual/remix"],
        [Palette, "Explorar direção", "/campaigns/campaign-aurora/moodboard"],
        [Activity, "Continue criando", "/content"],
      ],
    ],
  ] as const;
  const matches = (value: string) =>
    value.toLowerCase().includes(query.trim().toLowerCase());
  const filteredIntents = intents.filter(
    ([, title, detail]) => !query || matches(`${title} ${detail}`),
  );
  const filteredGroups = groups
    .map(
      ([title, items]) =>
        [
          title,
          items.filter(([, label]) => !query || matches(`${title} ${label}`)),
        ] as const,
    )
    .filter(([, items]) => items.length);
  return (
    <ModalFrame onClose={onClose} label="Criar">
      <div className="cx-create-modal cx-create-modal--approved">
        <header>
          <div>
            <h2>O que você quer criar?</h2>
            <p>
              Escolha um ponto de partida. O contexto da Café Aurora será
              aplicado.
            </p>
          </div>
          <button
            data-action-id="CREATE-CLOSE"
            onClick={onClose}
            aria-label="Fechar launcher"
          >
            <X />
          </button>
        </header>
        <label className="cx-create-search">
          <Search />
          <input
            data-action-id="CREATE-SEARCH"
            data-autofocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Busque um formato, objetivo ou ação..."
          />
          <kbd>Esc</kbd>
        </label>
        {filteredIntents.length > 0 && (
          <div className="cx-intent-grid">
            {filteredIntents.map(([Icon, title, detail, path]) => (
              <button
                data-action-id="CREATE-START-ITEM"
                key={title}
                onClick={() => navigate(path)}
              >
                <span>
                  <Icon />
                </span>
                <div>
                  <b>{title}</b>
                  <small>{detail}</small>
                </div>
                <ArrowRight />
              </button>
            ))}
          </div>
        )}
        {filteredGroups.length > 0 && (
          <div className="cx-create-groups">
            {filteredGroups.map(([title, items]) => (
              <section key={title}>
                <h3>{title}</h3>
                {items.map(([Icon, label, path]) => (
                  <button
                    data-action-id="CREATE-START-ITEM"
                    key={label}
                    onClick={() => navigate(path)}
                  >
                    <Icon />
                    <span>{label}</span>
                    <ArrowRight />
                  </button>
                ))}
              </section>
            ))}
          </div>
        )}
        {!filteredIntents.length && !filteredGroups.length && (
          <EmptyState
            title="Nenhum ponto de partida encontrado"
            detail="Tente um formato, objetivo ou ação diferente."
          />
        )}
        <footer>
          <span>
            <b>Ctrl</b> + <b>C</b> para abrir de qualquer lugar
          </span>
          <span>
            <Command />K também encontra qualquer ferramenta
          </span>
        </footer>
      </div>
    </ModalFrame>
  );
}
function ActivityDrawer({ data, demo, navigate, onClose }: AnyRecord) {
  const [filter, setFilter] = React.useState("Todas");
  const [read, setRead] = React.useState<Set<string>>(() => new Set());
  const demoEvents = [
    {
      id: "a1",
      kind: "Aprovações",
      Icon: Check,
      title: "Mariana solicitou sua aprovação",
      subject: "O Brasil cabe em uma xícara · Carrossel v3",
      time: "Há 18 min",
      unread: true,
    },
    {
      id: "a2",
      kind: "Menções",
      Icon: AtSign,
      title: "João mencionou você",
      subject: "Ritual de foco · Carrossel",
      time: "Há 47 min",
      unread: true,
    },
    {
      id: "a3",
      kind: "Sistema",
      Icon: CalendarDays,
      title: "Publicação programada",
      subject: "Hoje, 18h00",
      time: "Há 1h",
    },
    {
      id: "a4",
      kind: "Sistema",
      Icon: Radar,
      title: "Oportunidade do Radar em alta",
      subject: "“Rituais de café” atingiu alta relevância",
      time: "Há 2h",
    },
    {
      id: "a5",
      kind: "Sistema",
      Icon: Activity,
      title: "Conflito de versão detectado",
      subject: "Carrossel v2 foi editado após sua revisão.",
      time: "Ontem, 16h22",
    },
    {
      id: "a6",
      kind: "Sistema",
      Icon: Link2,
      title: "Integração com Meta desconectada",
      subject: "Reconecte para continuar publicando.",
      time: "Ontem, 11h05",
      action: "Reconectar",
    },
  ];
  const backendEvents = (data.snapshot?.approvalEvents || []).map(
    (e: AnyRecord, i: number) => ({
      id: e.id || `event-${i}`,
      kind: "Aprovações",
      Icon: Check,
      title: `${e.actorName || "Equipe"} ${e.detail || e.action || "atualizou uma aprovação"}`,
      subject: e.subject || "Atividade do workspace",
      time: i ? "Há 18 min" : "Agora",
      unread: i === 0,
    }),
  );
  const events = demo ? demoEvents : backendEvents;
  const visible =
    filter === "Todas"
      ? events
      : events.filter((e: AnyRecord) => e.kind === filter);
  return (
    <>
      <button
        className="cx-drawer-scrim"
        data-action-id="ACTIVITY-CLOSE"
        onClick={onClose}
        aria-label="Fechar atividade"
      />
      <aside
        className="cx-activity"
        role="dialog"
        aria-modal="true"
        aria-label="Central de atividades"
      >
        <header>
          <div>
            <small>WORKSPACE</small>
            <h2>Central de atividades</h2>
          </div>
          <button
            data-action-id="ACTIVITY-CLOSE"
            onClick={onClose}
            aria-label="Fechar central de atividades"
          >
            <X />
          </button>
        </header>
        <div className="cx-activity-tools">
          <button
            data-action-id="ACTIVITY-MARK-READ"
            onClick={() => setRead(new Set(events.map((e: AnyRecord) => e.id)))}
          >
            Marcar como lidas
          </button>
        </div>
        <div className="cx-activity-filter">
          {["Todas", "Aprovações", "Menções", "Sistema"].map((x) => (
            <button
              data-action-id="ACTIVITY-SELECT-FILTER"
              key={x}
              className={filter === x ? "is-active" : ""}
              onClick={() => setFilter(x)}
            >
              {x}
            </button>
          ))}
        </div>
        <section>
          {visible.length ? (
            visible.map((e: AnyRecord) => (
              <article
                key={e.id}
                onClick={() => setRead((current) => new Set(current).add(e.id))}
              >
                <span>
                  <e.Icon size={16} />
                </span>
                <div>
                  <p>
                    <b>{e.title}</b>
                  </p>
                  <p>{e.subject}</p>
                  <small>{e.time}</small>
                  {e.action && (
                    <button
                      data-action-id="ACTIVITY-OPEN-ACTION"
                      onClick={(event) => {
                        event.stopPropagation();
                        onClose();
                        navigate("/apps/instagram");
                      }}
                    >
                      {e.action}
                    </button>
                  )}
                </div>
                {e.unread && !read.has(e.id) && <i />}
              </article>
            ))
          ) : (
            <EmptyState
              title="Tudo em dia"
              detail="Aprovações e mudanças importantes aparecem aqui."
            />
          )}
        </section>
      </aside>
    </>
  );
}
function WorkspaceDialog({
  data,
  demo,
  pathname,
  brand,
  navigate,
  onClose,
}: AnyRecord) {
  const demoWorkspaces = [
    {
      id: "aurora",
      name: "Café Aurora",
      avatar: "CA",
      category: "Gastronomia",
      projects: 12,
    },
    {
      id: "horizonte",
      name: "Clínica Horizonte",
      avatar: "CH",
      category: "Saúde",
      projects: 8,
    },
    {
      id: "norte",
      name: "Studio Norte",
      avatar: "SN",
      category: "Criatividade",
      projects: 6,
    },
    {
      id: "origens",
      name: "Casa Origens",
      avatar: "CO",
      category: "Casa & decoração",
      projects: 4,
    },
    {
      id: "alvorada",
      name: "Bistrô Alvorada",
      avatar: "BA",
      category: "Gastronomia",
      projects: 3,
    },
  ];
  const workspaces = demo
    ? [...demoWorkspaces].sort((a, b) =>
        a.id === brand?.id ? -1 : b.id === brand?.id ? 1 : 0,
      )
    : (data.workspaces || []).map((w: AnyRecord) => ({
        ...w,
        avatar: w.avatar?.slice?.(0, 2) || w.name.slice(0, 2),
        category: w.role || "Workspace",
        projects: w.projectCount || 0,
      }));
  return (
    <ModalFrame onClose={onClose} label="Trocar workspace">
      <div className="cx-workspace-modal cx-workspace-modal--approved">
        <header>
          <div>
            <small>WORKSPACES</small>
            <h2>Trocar workspace</h2>
          </div>
          <button
            data-action-id="WORKSPACE-CLOSE-SELECTOR"
            onClick={onClose}
            aria-label="Fechar seletor de workspace"
          >
            <X />
          </button>
        </header>
        <div>
          {workspaces.map((w: AnyRecord, i: number) => (
            <React.Fragment key={w.id}>
              {i === 0 && (
                <small className="cx-workspace-group">Workspace atual</small>
              )}
              {i === 1 && (
                <small className="cx-workspace-group">
                  Todos os workspaces
                </small>
              )}
              <button
                data-action-id="SHELL-SELECT-WORKSPACE"
                onClick={() => {
                  if (!demo) {
                    void data.selectWorkspace(w.id);
                    onClose();
                    return;
                  }
                  const selectedBrand =
                    w.id === "horizonte" ? "horizonte" : "aurora";
                  navigate(`${normalize(pathname)}?brand=${selectedBrand}`);
                }}
              >
                <span>{w.avatar}</span>
                <div>
                  <b>{w.name}</b>
                  <small>
                    {w.category} · {w.projects} projetos ativos
                  </small>
                </div>
                {brand?.id === w.id ? <Check /> : <ChevronRight />}
              </button>
            </React.Fragment>
          ))}
        </div>
        <footer>
          <button
            data-action-id="WORKSPACE-CREATE"
            onClick={() => {
              onClose();
              navigate("/settings/workspaces/new");
            }}
          >
            <Plus />
            Criar workspace
          </button>
          <button
            data-action-id="WORKSPACE-MANAGE"
            onClick={() => {
              onClose();
              navigate("/settings/workspaces");
            }}
          >
            <Settings />
            Gerenciar
          </button>
        </footer>
      </div>
    </ModalFrame>
  );
}
function Spotlight({ onClose, navigate }: AnyRecord) {
  const [query, setQuery] = React.useState("");
  const [selected, setSelected] = React.useState(0);
  const all = [
    ...navItems.map(([path, Icon, label]) => ({
      path,
      Icon,
      label,
      group: "Navegar",
      detail: "Destino global",
    })),
    {
      path: "/campaigns/new",
      Icon: FolderKanban,
      label: "Criar campanha",
      group: "Ações rápidas",
      detail: "Planeje e crie uma campanha",
    },
    {
      path: "/content/draft/edit?mode=visual",
      Icon: Image,
      label: "Criar post",
      group: "Ações rápidas",
      detail: "Novo post para redes sociais",
    },
    {
      path: "/radar",
      Icon: Radar,
      label: "Explorar Radar",
      group: "Ações rápidas",
      detail: "Oportunidades e tendências",
    },
    {
      path: "/campaigns/campaign-aurora",
      Icon: FolderKanban,
      label: "Campanha Ritual de Foco",
      group: "Recentes",
      detail: "Em criação",
    },
    {
      path: "/campaigns/institucional",
      Icon: FolderKanban,
      label: "Institucional Café Aurora",
      group: "Projetos e campanhas",
      detail: "Finalizado",
    },
    {
      path: "/content/post-ritual",
      Icon: Image,
      label: "Post: A pausa que inspira",
      group: "Recentes",
      detail: "Conteúdo",
    },
    {
      path: "/content/post-ritual/edit?mode=video",
      Icon: Play,
      label: "Reel: O ritual do foco",
      group: "Recentes",
      detail: "Sugestão para você",
    },
    {
      path: "/brand-memory",
      Icon: BookOpen,
      label: "Memória da marca",
      group: "Navegar",
      detail: "Voz, identidade e provas",
    },
    {
      path: "/factory",
      Icon: Boxes,
      label: "Fábrica de conteúdo",
      group: "Navegar",
      detail: "Ferramentas criativas",
    },
    {
      path: "/apps",
      Icon: AppWindow,
      label: "Apps e integrações",
      group: "Navegar",
      detail: "Canais e conexões",
    },
  ];
  const results = all.filter((x) =>
    `${x.label} ${x.group} ${x.detail}`
      .toLowerCase()
      .includes(query.toLowerCase()),
  );
  const ref = React.useRef<HTMLInputElement>(null);
  React.useEffect(() => {
    ref.current?.focus();
  }, []);
  React.useEffect(() => setSelected(0), [query]);
  const open = (item: AnyRecord) => {
    onClose();
    navigate(item.path);
  };
  return (
    <ModalFrame onClose={onClose} label="Busca global">
      <div
        className="cx-spotlight cx-spotlight--approved"
        onKeyDown={(e) => {
          if (e.key === "ArrowDown") {
            e.preventDefault();
            setSelected((x) => Math.min(x + 1, results.length - 1));
          }
          if (e.key === "ArrowUp") {
            e.preventDefault();
            setSelected((x) => Math.max(x - 1, 0));
          }
          if (e.key === "Enter" && results[selected]) {
            e.preventDefault();
            open(results[selected]);
          }
        }}
      >
        <label>
          <Search />
          <input
            data-action-id="SEARCH-UPDATE-QUERY"
            ref={ref}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Buscar projetos, conteúdos, oportunidades ou comandos"
          />
          <kbd>ESC</kbd>
        </label>
        <div>
          {results.length ? (
            results.map((item, i) => (
              <React.Fragment key={`${item.path}${item.label}`}>
                {(i === 0 || results[i - 1].group !== item.group) && (
                  <small className="cx-result-group">{item.group}</small>
                )}
                <button
                  data-action-id="SEARCH-OPEN-RESULT"
                  onMouseEnter={() => setSelected(i)}
                  onClick={() => open(item)}
                  className={i === selected ? "is-active" : ""}
                >
                  <span>
                    <item.Icon />
                  </span>
                  <div>
                    <b>{item.label}</b>
                    <small>{item.detail}</small>
                  </div>
                  <kbd>↵</kbd>
                </button>
              </React.Fragment>
            ))
          ) : (
            <EmptyState
              title="Nada encontrado"
              detail="Tente o nome de uma campanha, conteúdo, oportunidade ou comando."
            />
          )}
        </div>
        <footer>
          <span>
            <b>↑↓</b> Navegar
          </span>
          <span>
            <b>Enter</b> Abrir
          </span>
          <span>
            <b>Esc</b> Fechar
          </span>
        </footer>
      </div>
    </ModalFrame>
  );
}
function ModalFrame({ children, onClose, label }: AnyRecord) {
  const ref = React.useRef<HTMLDivElement>(null);
  React.useEffect(() => {
    const node = ref.current;
    if (!node) return;
    const focusables = [
      ...node.querySelectorAll<HTMLElement>(
        'button,input,textarea,[tabindex]:not([tabindex="-1"])',
      ),
    ];
    const preferred = node.querySelector<HTMLElement>("[data-autofocus]");
    window.requestAnimationFrame(() => (preferred || focusables[0])?.focus());
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Tab" || !focusables.length) return;
      const first = focusables[0],
        last = focusables[focusables.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };
    node.addEventListener("keydown", onKey);
    return () => node.removeEventListener("keydown", onKey);
  }, []);
  return (
    <div
      className="cx-modal-wrap"
      role="dialog"
      aria-modal="true"
      aria-label={label}
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div ref={ref}>{children}</div>
    </div>
  );
}
function KeyValue({ label, value }: AnyRecord) {
  return (
    <div className="cx-key-value">
      <span>{label}</span>
      <b>{value}</b>
    </div>
  );
}
