import React from "react";
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
  Users,
  WandSparkles,
  X,
  Zap,
} from "lucide-react";
import { useProductData } from "../context/ProductDataContext";
import {
  demoCampaign,
  demoMedia,
  demoOpportunity,
  demoPosts,
  statusLabel,
} from "./demo";
import "./canonical.css";
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
  const p = normalize(pathname);
  return (
    p === "/" ||
    p === "/dashboard" ||
    p === "/today" ||
    p === "/radar" ||
    p.startsWith("/radar/opportunities/") ||
    p === "/campaigns/new" ||
    /^\/campaigns\/[^/]+$/.test(p) ||
    /^\/campaigns\/[^/]+\/(world|moodboard)$/.test(p) ||
    p === "/content" ||
    /^\/content\/[^/]+$/.test(p) ||
    /^\/content\/[^/]+\/(edit|remix)$/.test(p) ||
    /^\/approvals\/[^/]+$/.test(p) ||
    p === "/calendar" ||
    /^\/publish\/[^/]+$/.test(p) ||
    p === "/brand-memory" ||
    p === "/library/assets" ||
    p === "/analytics/learning" ||
    p === "/factory" ||
    p === "/projects" ||
    p === "/apps" ||
    /^\/apps\/[^/]+$/.test(p)
  );
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

  return (
    <div
      className={`cx-product ${focus ? "cx-focus" : ""}`}
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
      {focus && <FocusRail navigate={navigate} />}
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
        />
        <main id="cx-main" className="cx-main" tabIndex={-1}>
          {data.status === "error" && (
            <StateBanner
              tone="danger"
              title="A sincronização falhou"
              detail={data.error || "Tente novamente."}
              action="Tentar novamente"
              onAction={() => void data.refresh()}
            />
          )}
          {demo && (
            <div className="cx-demo-banner">
              <Sparkles size={14} /> Workspace demonstrativo · exemplos não são
              persistidos{" "}
              <button onClick={() => navigate("/login")}>
                Entrar para conectar dados reais
              </button>
            </div>
          )}
          <RouteSurface {...state} />
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

function FocusRail({ navigate }: { navigate: Navigate }) {
  return (
    <aside className="cx-focus-rail">
      <button
        aria-label="Voltar à campanha"
        onClick={() => navigate("/campaigns/active")}
      >
        <ArrowLeft size={20} />
      </button>
      <div className="cx-mark">c</div>
      <button aria-label="Camadas">
        <Layers3 size={19} />
      </button>
      <button aria-label="Assets">
        <Image size={19} />
      </button>
      <button aria-label="Comentários">
        <MessageSquare size={19} />
      </button>
      <span />
      <button aria-label="Ajuda">
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
  triggerRef,
}: AnyRecord) {
  return (
    <header className="cx-header">
      {!focus && (
        <button
          className="cx-mobile-menu"
          onClick={onMenu}
          aria-label="Abrir navegação"
        >
          <Menu size={20} />
        </button>
      )}
      <button
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
        onClick={onActivity}
        aria-label="Abrir atividade"
      >
        <Bell size={19} />
        <i />
      </button>
      <button className="cx-icon-button" aria-label="Abrir ajuda">
        <CircleHelp size={19} />
      </button>
      <button className="cx-avatar" aria-label="Menu do perfil">
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
  if (p === "/library/assets") return <ApprovedLibrarySurface {...props} />;
  if (p === "/analytics/learning")
    return <ApprovedAnalyticsSurface {...props} />;
  if (p === "/factory") return <ApprovedFactorySurface {...props} />;
  if (p === "/projects") return <ProjectsSurface {...props} />;
  if (p === "/apps") return <ApprovedAppsSurface {...props} />;
  if (/^\/apps\/[^/]+$/.test(p)) return <SocialIntegrationSurface {...props} />;
  return (
    <EmptyState
      title="Ainda não há nada aqui"
      detail="Volte à Home para iniciar um projeto."
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
}: AnyRecord) {
  return (
    <button
      type={type}
      className={`cx-button cx-button--${tone}`}
      onClick={onClick}
      disabled={disabled}
      aria-label={ariaLabel}
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
}: AnyRecord) {
  return (
    <div className={`cx-state-banner cx-state-banner--${tone}`} role="status">
      <div>
        <b>{title}</b>
        <span>{detail}</span>
      </div>
      {action && <Button onClick={onAction}>{action}</Button>}
    </div>
  );
}
function EmptyState({ title, detail, action, onAction }: AnyRecord) {
  return (
    <div className="cx-empty">
      <div>
        <Sparkles />
      </div>
      <h2>{title}</h2>
      <p>{detail}</p>
      {action && (
        <Button tone="primary" onClick={onAction}>
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
          <button key={String(title)} onClick={() => navigate(String(path))}>
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
          <button onClick={() => navigate("/dashboard?create=open")}>
            <Plus size={17} />
            <span>Tamanho personalizado</span>
          </button>
          <button onClick={() => navigate("/library/assets")}>
            <Upload size={17} />
            <span>Importar</span>
          </button>
        </footer>
      </div>
      <div className="cx-approved-section-head">
        <div>
          <small>PARA VOCÊ</small>
          <h2>Recomendado para sua marca hoje</h2>
        </div>
        <button onClick={() => navigate("/radar")}>
          Ver radar completo <ArrowRight size={15} />
        </button>
      </div>
      <div className="cx-recommendations">
        <button
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
        <button onClick={() => navigate("/projects")}>
          Ver projetos <ArrowRight size={15} />
        </button>
      </div>
      <div className="cx-continue-grid">
        {continues.map(([title, state, meta, path, image]) => (
          <button key={String(title)} onClick={() => navigate(String(path))}>
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
function SectionHead({ title, action, onAction }: AnyRecord) {
  return (
    <div className="cx-section-head">
      <h2>{title}</h2>
      {action && (
        <button onClick={onAction}>
          {action}
          <ArrowRight size={15} />
        </button>
      )}
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
          <button>
            Últimas 24h <ChevronDown />
          </button>
          <button>
            Brasil <ChevronDown />
          </button>
          <button>
            Todos os temas <ChevronDown />
          </button>
          <button aria-label="Alternar visualização">
            <Grid2X2 />
          </button>
          <small>↘ 12 fontes monitoradas</small>
        </div>
      </div>
      {!demo && radarState?.state !== "ready" && (
        <StateBanner
          tone="orange"
          title="Radar em preparação"
          detail={
            radarState?.reason ||
            "Conecte fontes para revelar oportunidades relevantes."
          }
          action="Configurar fontes"
          onAction={() => navigate("/settings/channels")}
        />
      )}
      <div className="cx-radar-tabs">
        <button className="is-active">Prioridades</button>
        <button>Salvos</button>
        <button>Descartados</button>
      </div>
      {opportunities.length ? (
        <div className="cx-radar-layout">
          <div className="cx-radar-queue">
            {opportunities.map((op: AnyRecord) => (
              <button
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
              onClick={() =>
                navigate(`/campaigns/new?opportunity=${selected.id}`)
              }
            >
              Transformar em campanha
            </Button>
            <Button
              icon={Sparkles}
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
        <h3>♢ Guardrails</h3>
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
          onClick={() =>
            navigate(`/campaigns/new?opportunity=${demoOpportunity.id}`)
          }
        >
          Criar campanha com esta oportunidade
        </Button>
        <Button
          icon={Sparkles}
          onClick={() => setApproach((value) => value + 1)}
        >
          {approach
            ? `Abordagem alternativa ${approach}`
            : "Explorar outra abordagem"}
        </Button>
        <Button
          icon={saved ? Check : BookOpen}
          onClick={() => setSaved(!saved)}
        >
          {saved ? "Salva para depois" : "Salvar para depois"}
        </Button>
      </aside>
    </section>
  );
}

function CampaignIntake({ data, demo, params, navigate, setToast }: AnyRecord) {
  const [name, setName] = React.useState(
    params.get("opportunity") ? "O Brasil cabe em uma xícara" : "",
  );
  const [objective, setObjective] = React.useState(
    params.get("opportunity")
      ? "Transformar o interesse por origens brasileiras em alcance qualificado e pedidos do Kit Degustação."
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
          originContext: { source: "canonical-intake" },
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
      navigate(`/campaigns/${id}`);
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
                autoFocus
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </label>
            <label>
              <span>Objetivo</span>
              <textarea
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
          <h2>♧ Oferta e público</h2>
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
          <h2>♢ Guardrails preservados</h2>
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
        <h3>♢ Kit inicial previsto</h3>
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
          disabled={busy || !name.trim()}
        >
          {busy ? "Criando…" : "Criar campanha"}
        </Button>
        <Button
          icon={Sparkles}
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
          onClick={() =>
            navigate(
              `/radar/opportunities/${params.get("opportunity") || demoOpportunity.id}`,
            )
          }
        >
          Voltar à oportunidade
        </Button>
        <small>♙ Nada será publicado automaticamente.</small>
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
            onClick={() => navigate("/content/draft/edit?mode=visual")}
          >
            Criar peça
          </Button>
          <Button
            icon={Sparkles}
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
              onClick={() =>
                navigate("/content/post-ritual/edit?mode=carousel")
              }
            >
              Retomar criação
            </Button>
          </div>
        </section>
        <section className="cx-campaign-kit">
          <h3>♢ Kit da campanha</h3>
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
                  <button onClick={() => navigate(path)}>{action}</button>
                </footer>
              </article>
            ))}
          </div>
        </section>
        <section className="cx-campaign-flow">
          <h3>♧ Fluxo da campanha</h3>
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
        <h3>♢ Guardrails</h3>
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
        <Button onClick={() => navigate(`/campaigns/${id}/world`)}>
          Abrir mundo da campanha
        </Button>
        <Button onClick={() => navigate(`/campaigns/${id}/moodboard`)}>
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

function ApprovedContentHub({ navigate }: AnyRecord) {
  const [query, setQuery] = React.useState("");
  const [tab, setTab] = React.useState("Para criar");
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
          <button className="is-active">
            <Grid2X2 />
            Board visual
          </button>
          <button>
            <LayoutGrid />
            Inventário
          </button>
        </div>
        <Button
          tone="primary"
          icon={Plus}
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
          <button key={x}>{x}⌄</button>
        ))}
        <button>
          <ListFilter />
          Filtros
        </button>
      </div>
      <div className="cx-content-hub-layout">
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
            <button>Ver todos</button>
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
            <button>Ver todos</button>
          </div>
          {winners.map(([title, metric, image]) => (
            <article key={title}>
              <img src={image} />
              <div>
                <b>{title}</b>
                <small>Campanha Ritual de Foco</small>
                <strong>{metric}</strong>
                <button onClick={() => navigate("/content/post-ritual/remix")}>
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
  return <ApprovedVisualEditor {...props} />;
}

function ApprovedEditorialDesk({ navigate, setToast }: AnyRecord) {
  const [selected, setSelected] = React.useState(0);
  const [hook, setHook] = React.useState(
    "O Brasil cabe em uma xícara — mas você sabe reconhecer a origem do que bebe?",
  );
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
          className="cx-editor-home"
          onClick={() => navigate("/dashboard")}
        >
          <strong>
            Clicko<span>*</span>
          </strong>
          <small>Home</small>
        </button>
        <button onClick={() => navigate("/campaigns/campaign-aurora")}>
          ← O Brasil cabe em uma xícara
        </button>
        <h1>Carrossel editorial</h1>
        <span>◉ Instagram · 4:5　● Salvo há poucos segundos</span>
        <div />
        <Button>Preview</Button>
        <Button onClick={() => setToast("Conteúdo salvo")}>Salvar</Button>
        <Button
          onClick={() => navigate("/content/post-ritual/edit?mode=visual")}
        >
          Abrir no Visual
        </Button>
        <Button
          tone="primary"
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
            className={i === 0 ? "is-active" : ""}
            title={String(label)}
            key={String(label)}
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
        <textarea value={hook} onChange={(e) => setHook(e.target.value)} />
        <Button icon={Sparkles}>Fortalecer hook</Button>
        <h2>Sequência do carrossel</h2>
        <div className="cx-sequence-list">
          {slides.map((slide, i) => (
            <button
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
          B　I　•　☷　↗　◇
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
          <button className="is-active">Feed</button>
          <button>Legenda</button>
          <button>Slides</button>
        </nav>
        <span>{selected + 1} / 6</span>
        <img src={selected === 5 ? phase3Arts[3] : phase3Arts[0]} />
        <div className="cx-preview-arrows">
          <button onClick={() => setSelected((selected + 5) % 6)}>‹</button>
          <button>○ Exibir área segura</button>
          <button onClick={() => setSelected((selected + 1) % 6)}>›</button>
        </div>
        <div className="cx-preview-strip">
          {slides.map((_, i) => (
            <button
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
          <button key={title}>
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

function ApprovedVisualEditor({ navigate, setToast }: AnyRecord) {
  const [layer, setLayer] = React.useState(0);
  const [zoom, setZoom] = React.useState(82);
  const [synced, setSynced] = React.useState(true);
  const [slidesOpen, setSlidesOpen] = React.useState(true);
  const layers = [
    "O Brasil cabe em uma xícara.",
    "Quatro territórios. Uma caixa.",
    "Imagem do produto",
    "Xícara de café",
    "Textura de fundo",
    "Café Aurora (assinatura)",
  ];
  return (
    <section className="cx-visual-approved">
      <header>
        <button
          className="cx-editor-home"
          onClick={() => navigate("/dashboard")}
        >
          <strong>
            Clicko<span>*</span>
          </strong>
          <small>Home</small>
        </button>
        <button
          className="cx-editor-back"
          onClick={() => navigate("/content/post-ritual/edit?mode=editorial")}
        >
          ← Carrossel editorial
        </button>
        <b>O Brasil cabe em uma xícara · Slide 1</b>
        <span>1080×1350 · Instagram 4:5</span>
        <strong>v3</strong>
        <i>● {synced ? "Sincronizado" : "Alterado"}</i>
        <div />
        <Button>Preview</Button>
        <Button
          onClick={() => {
            setSynced(true);
            setToast("Peça visual salva");
          }}
        >
          Salvar
        </Button>
        <Button>Exportar</Button>
        <Button
          tone="primary"
          onClick={() => navigate("/approvals/post-ritual?view=creative")}
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
          <button className={i === 5 ? "is-active" : ""} key={String(label)}>
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
            className={layer === i ? "is-active" : ""}
            onClick={() => setLayer(i)}
            key={x}
          >
            ◉　{i < 2 ? "T" : "▣"}
            <span>{x}</span>♙
          </button>
        ))}
        <Button icon={Plus}>Adicionar camada</Button>
      </aside>
      <main className="cx-visual-canvas">
        <div className="cx-visual-toolbar">
          <button>Bricolage Grotesque</button>
          <button>Semibold</button>
          <button>76</button>
          <button>▣</button>
          <button>☰</button>
          <button>X 90</button>
          <button>Y 120</button>
        </div>
        <div className="cx-visual-stage">
          <div>
            <img src={phase3Arts[0]} />
            <span className="cx-safe-area" />
            <span className="cx-selection">
              <strong>
                O BRASIL
                <br />
                CABE EM UMA
                <br />
                XÍCARA.
              </strong>
              <i />
              <i />
              <i />
              <i />
            </span>
          </div>
        </div>
        <div className="cx-zoom">
          <button onClick={() => setZoom(Math.max(40, zoom - 5))}>−</button>
          {zoom}%
          <button onClick={() => setZoom(Math.min(120, zoom + 5))}>+</button>
          　☝　⌗
        </div>
      </main>
      <aside className="cx-design-approved">
        <nav>
          <button className="is-active">Design</button>
          <button>Efeitos · Beta</button>
          <button>Movimento · Depois</button>
        </nav>
        <h2>Tipografia</h2>
        <input value="Bricolage Grotesque" readOnly />
        <div>
          <input value="Semibold" readOnly />
          <input value="76 px" readOnly />
        </div>
        <small>Altura da linha　 Espaçamento　 Alinhamento</small>
        <p>0,95　　　　 0%　　　　 ☰ ≡</p>
        <hr />
        <h2>Posição e tamanho</h2>
        <div className="cx-design-grid">
          {["X 90", "Y 120", "L 900", "A 540", "↻ 0°", "Opacidade 100%"].map(
            (x) => (
              <button key={x}>{x}</button>
            ),
          )}
        </div>
        <hr />
        <h2>Guardrail da marca</h2>
        <p>✓ Contraste aprovado</p>
        <p>✓ Headline dentro da área segura</p>
        <p>✓ Tom visual alinhado à Memória v4</p>
        <Button onClick={() => setToast("Composition Coach aberto")}>
          ✦ Ver Composition Coach
        </Button>
        <hr />
        <h2>Plano de fundo</h2>
        <article>
          <img src={phase3Arts[0]} />
          <span>
            Textura de fundo · Café Aurora
            <small>Asset aprovado da campanha</small>
          </span>
          <button>Substituir</button>
        </article>
        <hr />
        <h2>Recursos avançados</h2>
        {[
          "Sombras　Beta △",
          "Máscaras　Beta △",
          "Modos de mesclagem　Beta △",
        ].map((x) => (
          <button className="cx-disabled" key={x}>
            {x}
          </button>
        ))}
      </aside>
      <div
        className={`cx-slide-strip-approved ${slidesOpen ? "" : "is-collapsed"}`}
      >
        <b>Slides do carrossel</b>
        <button
          className="cx-slide-strip-toggle"
          onClick={() => setSlidesOpen(!slidesOpen)}
        >
          {slidesOpen ? "Recolher" : "Abrir slides"}
        </button>
        <div>
          {[1, 2, 3, 4, 5, 6].map((x) => (
            <button className={x === 1 ? "is-active" : ""} key={x}>
              <img src={x === 6 ? phase3Arts[3] : phase3Arts[0]} />
              <span>{x}</span>
            </button>
          ))}
          <button className="cx-add-slide">
            <Plus />
            Adicionar slide
          </button>
          <aside>
            <button>⌁ Variações</button>
            <button>▣ Referências</button>
          </aside>
        </div>
      </div>
    </section>
  );
}

function ApprovedCarouselBuilder({ setToast }: AnyRecord) {
  const initial = [
    "Ritual de foco",
    "Mais ruído, menos clareza",
    "Foco é escolha",
    "Um ritual muda o ritmo",
    "Comece pequeno",
    "Salve para amanhã",
  ];
  const [slides, setSlides] = React.useState(initial);
  const [selected, setSelected] = React.useState(0);
  const [shared, setShared] = React.useState(false);
  const [title, setTitle] = React.useState("FOCO NÃO É SILÊNCIO. É ESCOLHA.");
  return (
    <section className="cx-carousel-approved">
      <header>
        <strong>Clicko*</strong>
        <b>Carrossel — Ritual de foco</b>
        <span>Salvo agora</span>
        <div />
        <Button>↶</Button>
        <Button>Visualizar</Button>
        <Button
          icon={shared ? Check : Share2}
          onClick={() => setShared(!shared)}
        >
          {shared ? "Link copiado" : "Compartilhar"}
        </Button>
        <Button tone="primary">Exportar</Button>
      </header>
      <aside className="cx-carousel-narrative">
        <small>NARRATIVA</small>
        <p>{slides.length} slides · 48s de leitura</p>
        {slides.map((text, i) => (
          <button
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
          onClick={() => setSlides([...slides, "Novo momento"])}
        >
          Adicionar slide
        </Button>
        <footer>
          Ritmo narrativo
          <br />
          <b>PROMESSA → TENSÃO → VIRADA → PROVA → AÇÃO</b>
        </footer>
      </aside>
      <main className="cx-carousel-stage">
        <nav>
          <button className="is-active">Conteúdo</button>
          <button>Design</button>
          <button>Animação</button>
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
            onClick={() =>
              setSelected((selected - 1 + slides.length) % slides.length)
            }
          >
            ‹
          </button>
          <span>
            Transição entre slides<button>Corte limpo · 0,4s</button>
          </span>
          <button>▶</button>
          <button onClick={() => setSelected((selected + 1) % slides.length)}>
            ›
          </button>
        </div>
      </main>
      <aside className="cx-carousel-inspector">
        <nav>
          {["Conteúdo", "Design", "Marca", "Sequência"].map((x, i) => (
            <button className={i === 0 ? "is-active" : ""} key={x}>
              {x}
            </button>
          ))}
        </nav>
        <small>FUNÇÃO NARRATIVA</small>
        <button>Promessa principal</button>
        <small>TÍTULO</small>
        <textarea value={title} onChange={(e) => setTitle(e.target.value)} />
        <small>TEXTO DE APOIO</small>
        <textarea defaultValue="Um ritual simples ajuda a separar o que importa do que apenas chama." />
        <small>ASSET PRINCIPAL</small>
        <article>
          <img src="/canonical/figma/phase3/s17-visual.png" />
          <span>
            ritual_de_foco_01.jpg<small>Campanha Aurora · Licenciado</small>
          </span>
          <button>Trocar</button>
        </article>
        <small>CTA</small>
        <button>Salve para amanhã</button>
        <small>CONSISTÊNCIA DA SEQUÊNCIA</small>
        <p className="cx-sequence-check">
          ✓ Tipografia consistente
          <br />✓ Progressão narrativa clara
          <br />! Slide 04 precisa de mais contraste
        </p>
        <StateBanner
          tone="orange"
          title="✦ Sugestão Clicko Intelligence"
          detail="Encurte o título do slide 03 para preservar o ritmo da sequência."
        />
        <button
          className="cx-apply-suggestion"
          onClick={() => {
            setTitle("FOCO É ESCOLHA.");
            setToast("Sugestão aplicada");
          }}
        >
          Aplicar sugestão
        </button>
        <button>Ajustes avançados　⌄</button>
      </aside>
    </section>
  );
}

function ContentBoard({ data, demo, navigate }: AnyRecord) {
  const posts = demo ? demoPosts : data.snapshot?.posts || [];
  return (
    <Page
      eyebrow="Produção"
      title="Conteúdos"
      description="Todas as peças, do primeiro rascunho à publicação."
      actions={
        <Button
          tone="primary"
          icon={Plus}
          onClick={() => navigate("/dashboard?create=open")}
        >
          Novo conteúdo
        </Button>
      }
    >
      <div className="cx-toolbar">
        <div className="cx-view-switch">
          <button className="is-active">
            <Grid2X2 size={16} />
            Quadro
          </button>
          <button>
            <LayoutGrid size={16} />
            Lista
          </button>
        </div>
        <button>
          <ListFilter size={16} />
          Filtrar
        </button>
        <label>
          <Search size={15} />
          <input placeholder="Buscar conteúdo" />
        </label>
      </div>
      <div className="cx-board">
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
                {posts.filter((p: AnyRecord) => p.status === status).length ||
                  [3, 2, 2, 1][col]}
              </span>
              <Plus size={15} />
            </header>
            {posts
              .filter((p: AnyRecord) => p.status === status)
              .map((p: AnyRecord) => (
                <button
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
            {!posts.some((p: AnyRecord) => p.status === status) && (
              <button
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
        <button onClick={() => navigate("/campaigns/active")}>
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
            onClick={() => navigate("/approvals/post-ritual?view=creative")}
          >
            Visualizar
          </Button>
          <Button
            tone="primary"
            icon={Send}
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
          <button key={label} title={label}>
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
          <button className="is-active">Design</button>
          <button>Camadas</button>
        </div>
        <section>
          <small>TEXTO</small>
          <label>
            Conteúdo
            <textarea
              value={caption}
              onChange={(e) => setCaption(e.target.value)}
              onBlur={save}
            />
          </label>
          <div className="cx-inline-fields">
            <button>Manrope</button>
            <button>64 px</button>
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
            <button>↤</button>
            <button>↔</button>
            <button>↦</button>
          </div>
        </section>
        <section className="cx-ai-box">
          <Sparkles />
          <b>Ajustar com IA</b>
          <p>Peça contraste, uma nova hierarquia ou adapte o texto.</p>
          <Button icon={Sparkles}>Abrir co-piloto</Button>
        </section>
      </aside>
      {carousel && (
        <div className="cx-page-strip">
          {[1, 2, 3, 4, 5].map((x) => (
            <button className={x === 1 ? "is-active" : ""} key={x}>
              <span>{x}</span>
            </button>
          ))}
          <button>
            <Plus />
          </button>
        </div>
      )}
    </div>
  );
}

function ApprovedReviewSurface({ data, demo, navigate, setToast }: AnyRecord) {
  const post = demo ? demoPosts[0] : data.snapshot?.posts?.[0];
  const [version, setVersion] = React.useState("v3");
  const [comment, setComment] = React.useState("");
  const [decision, setDecision] = React.useState("Decisão");
  const decide = async (action: "approve" | "request_changes" | "reject") => {
    if (action === "request_changes" && !comment.trim()) {
      setToast("Escreva o comentário obrigatório para solicitar ajustes");
      return;
    }
    try {
      if (!demo && post && action !== "reject")
        await data.decidePost(post.id, {
          action,
          comment: comment || "Direção aprovada na revisão canônica.",
        });
      setToast(
        action === "approve"
          ? "Versão aprovada"
          : action === "reject"
            ? "Versão rejeitada"
            : "Ajustes solicitados",
      );
      if (action === "approve") navigate("/calendar");
    } catch {
      setToast("A decisão não pôde ser salva");
    }
  };
  return (
    <section className="cx-review-approved">
      <header>
        <button onClick={() => navigate("/campaigns/campaign-aurora")}>
          ← Campaign Room
        </button>
        <b>Carrossel editorial · O Brasil cabe em uma xícara</b>
        <Chip>{version}</Chip>
        <span>● Em revisão</span>
        <span>◷ Hoje, 18h</span>
        <div />
        <Button
          onClick={() => navigate("/content/post-ritual/edit?mode=visual")}
        >
          Editar
        </Button>
        <Button onClick={() => setToast("Variação criada")}>
          Criar variação
        </Button>
        <Button onClick={() => setVersion(version === "v3" ? "v2" : "v3")}>
          Comparar versões
        </Button>
      </header>
      <main>
        <section className="cx-review-preview-approved">
          <div className="cx-review-version">
            <button
              className={version === "v3" ? "is-active" : ""}
              onClick={() => setVersion("v3")}
            >
              Versão atual　 <b>v3</b>
            </button>
            <button
              className={version === "v2" ? "is-active" : ""}
              onClick={() => setVersion("v2")}
            >
              Versão anterior　 v2
            </button>
            <button>▣ Lado a lado</button>
          </div>
          <img src={phase3Arts[0]} />
          <div className="cx-review-zoom">−　82%　+　☝　⌗</div>
          <div className="cx-review-thumbs">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <button className={i === 1 ? "is-active" : ""} key={i}>
                <img src={i === 6 ? phase3Arts[3] : phase3Arts[0]} />
                <span>{i}</span>
              </button>
            ))}
            <button className="cx-add-slide">
              <Plus />
              Adicionar slide
            </button>
          </div>
          <footer>
            <p>
              Festival Brasileiro de Cafés Especiais　→　O Brasil cabe em uma
              xícara　→　Carrossel v3
            </p>
            <div>
              {[
                "Produtores creditados",
                "Sem alegação de premiação",
                "Contraste aprovado",
              ].map((x) => (
                <span key={x}>
                  ♧ {x}
                  <Check />
                </span>
              ))}
            </div>
          </footer>
        </section>
        <aside className="cx-review-decision">
          <nav>
            {["Decisão", "Comentários · 3", "Versões · 3", "Contexto"].map(
              (x) => (
                <button
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
                <KeyValue label="Revisão por" value="JO　João" />
                <KeyValue label="Autor" value="MA　Mariana" />
              </div>
              <p>Hook e composição ajustados na v3. CTA preservado.</p>
              <Button tone="primary" onClick={() => void decide("approve")}>
                Aprovar esta versão　→
              </Button>
              <Button onClick={() => void decide("request_changes")}>
                △ Solicitar ajustes　→
              </Button>
              <Button onClick={() => void decide("reject")}>
                ⊗ Rejeitar　→
              </Button>
              <label>
                Comentário da decisão
                <textarea
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  placeholder="Explique o que deve mudar ou por que está aprovado."
                />
                <small>Comentário obrigatório para solicitar ajustes.</small>
              </label>
              <div className="cx-review-comments">
                <p>
                  <b>MA　Mariana · 14:32</b>
                  <br />
                  Reduzi o texto do slide 3 e reforcei a origem.
                </p>
                <p>
                  <b>JO　João · 15:10</b>
                  <br />A composição ficou mais clara.
                </p>
              </div>
              <h3>Evidência de performance ⓘ</h3>
              <div className="cx-no-evidence">
                ⊕ Sem evidência de performance para esta decisão.
              </div>
              <h3>Contexto rápido</h3>
              {[
                ["Campanha", "O Brasil cabe em uma xícara"],
                ["Objetivo", "Autoridade + conversão"],
                ["Público", "café especial · procedência"],
                ["Brand Memory", "v4"],
              ].map(([a, b]) => (
                <KeyValue label={a} value={b} key={a} />
              ))}
            </>
          ) : (
            <div className="cx-review-tab-state">
              <h2>{decision}</h2>
              <p>
                {decision.startsWith("Comentários")
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
        <button onClick={() => navigate("/content")}>
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
            <button>−</button>
            <span>72%</span>
            <button>+</button>
            <button>Ajustar</button>
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
                <button>Responder</button>
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
            <textarea placeholder="Deixe um comentário…" />
            <footer>
              <button>
                <Link2 />
              </button>
              <Button tone="primary" icon={Send}>
                Comentar
              </Button>
            </footer>
          </label>
          <div className="cx-review-actions">
            <Button onClick={() => void decide("request_changes")}>
              Solicitar ajustes
            </Button>
            <Button
              tone="primary"
              icon={Check}
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
          onClick={() => navigate("/dashboard?create=open")}
        >
          Agendar conteúdo
        </Button>
        <Button
          icon={Sparkles}
          onClick={() => navigate("/campaigns/campaign-aurora/world")}
        >
          Explorar direção
        </Button>
      </header>
      <div className="cx-calendar-controls">
        <nav>
          {["Semana", "Mês", "Trimestre"].map((x) => (
            <button
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
                    className={selected === i ? "is-selected" : ""}
                    onClick={() => setSelected(i)}
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
                      <button onClick={() => setSelected(1)} key={x[1]}>
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
                    <Button tone="primary" onClick={() => navigate("/content")}>
                      Criar para esta lacuna
                    </Button>
                  </div>
                )}
                {i === 3 && (
                  <button
                    className="cx-add-calendar"
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
              "↔ Arraste para reagendar",
            ].map((x) => (
              <span key={x}>{x}</span>
            ))}
          </footer>
        </main>
        <aside>
          <header>
            <h2>O Brasil cabe em uma xícara</h2>
            <button>×</button>
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
            onClick={() => navigate("/publish/post-ritual")}
          >
            Abrir Publisher Control
          </Button>
          <Button onClick={() => setMoved(!moved)}>
            {moved ? "Reagendado" : "Reagendar"}
          </Button>
          <Button onClick={() => navigate("/content/post-ritual")}>
            Abrir peça ↗
          </Button>
          <StateBanner
            tone="orange"
            title="O agendamento interno não confirma publicação na rede."
          />
          <small>Campanha　›　Carrossel v3　›　Calendário</small>
        </aside>
      </div>
    </section>
  );
}

function ApprovedPublisherSurface({ navigate, setToast }: AnyRecord) {
  const [slide, setSlide] = React.useState(0);
  const [scheduled, setScheduled] = React.useState(false);
  const [copied, setCopied] = React.useState(false);
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
            <button className="is-active">Visual</button>
            <button>Legenda</button>
            <button>Metadados</button>
          </nav>
          <div className="cx-publisher-preview">
            <span>{slide + 1} / 6</span>
            <button onClick={() => setSlide((slide + 5) % 6)}>‹</button>
            <img src={slide === 5 ? phase3Arts[3] : phase3Arts[0]} />
            <button onClick={() => setSlide((slide + 1) % 6)}>›</button>
          </div>
          <div className="cx-publisher-thumbs">
            {[1, 2, 3, 4, 5, 6].map((x, i) => (
              <button
                className={slide === i ? "is-active" : ""}
                onClick={() => setSlide(i)}
                key={x}
              >
                <img src={i === 5 ? phase3Arts[3] : phase3Arts[0]} />
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
              onClick={() => {
                setCopied(true);
                setToast("Legenda copiada");
              }}
            >
              ▣ {copied ? "Legenda copiada" : "Copiar legenda"}
            </Button>
            <Button>↧ Baixar imagens</Button>
            <Button
              onClick={() => navigate("/content/post-ritual/edit?mode=visual")}
            >
              ⌁ Abrir no editor
            </Button>
          </div>
          <footer>
            ⓘ A prévia representa o formato, não o chrome exato da rede.
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
            <button className={i === 5 ? "is-warning" : ""} key={x}>
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
            onClick={() => {
              setScheduled(true);
              setToast("Agendamento interno salvo");
            }}
          >
            ▣ {scheduled ? "Agendamento salvo" : "Agendar internamente"}
          </Button>
          <Button onClick={() => setToast("Pacote exportado")}>
            ↧ Exportar pacote
          </Button>
          <Button disabled>♧ Publicar agora · conector indisponível</Button>
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
          onClick={() => navigate("/content/post-ritual/edit?mode=visual")}
        >
          Editar
        </Button>
        <Button>Comparar versões</Button>
        <Button
          tone="primary"
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
            {["Peça", "Legenda", "Versões", "Comentários"].map((x, i) => (
              <button className={i === 0 ? "is-active" : ""} key={x}>
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
                  <span>{i ? "♧" : "✦"}</span>
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

function ApprovedRemixSurface({ navigate, setToast }: AnyRecord) {
  const [hypothesis, setHypothesis] = React.useState(0);
  const [created, setCreated] = React.useState(false);
  const formats = [
    ["Instagram Post 4:5", "Pronto como rascunho", "Baixo"],
    ["Story 9:16", "Revisão manual necessária", "Médio"],
    ["Square 1:1", "Ajuste de composição", "Médio"],
    ["Smart resize automático", "Ainda não disponível", "—"],
  ];
  return (
    <section className="cx-remix-approved">
      <header>
        <div>
          <small>Conteúdos　/　Ritual de foco　/　Reuse Lab</small>
          <h1>Transforme o que funcionou em uma nova peça</h1>
          <p>Preserve a força, adapte o formato e registre a hipótese.</p>
        </div>
        <Button>Duplicar sem adaptar</Button>
        <Button onClick={() => setHypothesis((hypothesis + 1) % 2)}>
          Sugerir hipótese
        </Button>
        <Button
          tone="primary"
          onClick={() => {
            setCreated(true);
            setToast("Derivação criada");
          }}
        >
          Criar derivação
        </Button>
      </header>
      <nav>
        <button className="is-active">✦ Remix guiado</button>
        <button>♧ Variações</button>
      </nav>
      <div className="cx-remix-approved-grid">
        <aside>
          <h2>Peça de origem</h2>
          <img src="/canonical/figma/phase3/s17-visual.png" />
          <Chip tone="green">Publicado</Chip>
          {[
            ["Campanha", "Aurora Origens"],
            ["Formato", "Carrossel v2"],
            ["Publicado em", "12 mai 2026"],
          ].map(([a, b]) => (
            <KeyValue label={a} value={b} key={a} />
          ))}
          <h3>Evidência real</h3>
          <div className="cx-remix-metrics">
            <KeyValue label="Alcance" value="45,2 mil" />
            <KeyValue label="Salvamentos" value="1,2 mil" />
            <StateBanner
              tone="orange"
              title="✦ 3× mais salvamentos que a média da campanha"
            />
          </div>
          <h3>Por que reutilizar</h3>
          <p>
            ✓ Clareza do ritual
            <br />✓ Fotografia de produto
            <br />✓ Compartilhamento acima da campanha
          </p>
          <h3>Linhagem</h3>
          <p>
            Aurora Origens　›　Campanha　›　Carrossel v2　›　Ritual de foco v2
          </p>
        </aside>
        <main>
          <h2>Plano da derivação</h2>
          <small>PRESERVAR</small>
          {[
            ["Texto do ritual", "Conexão emocional e foco"],
            ["Composição central", "Foco no produto e atmosfera"],
            ["Assinatura Café Aurora", "Reconhecimento da marca"],
          ].map((x) => (
            <label key={x[0]}>
              <input type="checkbox" defaultChecked />
              {x[0]}
              <span>{x[1]}</span>
            </label>
          ))}
          <small>ADAPTAR</small>
          {[
            ["Formato", "Do carrossel para outro formato"],
            ["CTA", "Refinar chamada para conversão"],
            ["Quantidade de texto", "Menos texto para leitura rápida"],
          ].map((x) => (
            <label key={x[0]}>
              ♧ {x[0]}
              <span>{x[1]}</span>
            </label>
          ))}
          <small>TESTAR</small>
          <button className="cx-hypothesis">
            <i />
            Novo hook:{" "}
            {hypothesis
              ? "Seu foco começa no primeiro gole."
              : "Seu ritual começa antes do primeiro gole."}
            <span>Hipótese principal</span>
          </button>
          <label>
            <input type="radio" />
            Imagem de produto mais próxima　Hipótese opcional
          </label>
          <Button>Objetivo da nova versão　Conversão　⌄</Button>
          <Button>Campanha de destino　O Brasil cabe em uma xícara　⌄</Button>
          <footer>ⓘ A hipótese ficará registrada na linhagem.</footer>
        </main>
        <section>
          <header>
            <h2>Formatos derivados</h2>
            <nav>
              <button>Original</button>
              <button className="is-active">Derivação</button>
            </nav>
          </header>
          <div>
            {formats.map(([title, state, risk], i) => (
              <article className={i === 3 ? "is-disabled" : ""} key={title}>
                <h3>{title}</h3>
                <small>
                  {i === 0 ? "✓" : "△"} {state}
                </small>
                {i < 3 ? (
                  <img src="/canonical/figma/phase3/s17-visual.png" />
                ) : (
                  <div className="cx-smart-empty">▣</div>
                )}
                <p>
                  Elementos preservados
                  <br />✓ ◻ T
                </p>
                <p>
                  Risco de adaptação
                  <br />
                  <b>{risk}</b>
                </p>
                <Button
                  disabled={i === 3}
                  onClick={() =>
                    navigate("/content/post-ritual/edit?mode=visual")
                  }
                >
                  {i === 3 ? "Em breve" : "Abrir no editor →"}
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
          ["Ritual de foco v2", "Peça de origem"],
          ["Reuse event", "Remix guiado"],
          [
            created ? "Nova derivação v1 criada" : "Nova derivação v1",
            "Em rascunho",
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
        <Button tone="primary" onClick={() => setToast("Importação preparada")}>
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
            <button onClick={() => navigate("/content/post-ritual")} key={x[0]}>
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
            <button>Alcance</button>
            <button>Salvamentos</button>
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
            onClick={() => navigate("/dashboard?create=open")}
          >
            Agendar conteúdo
          </Button>
        </>
      }
      wide
    >
      <div className="cx-calendar-head">
        <button>‹</button>
        <h2>Agosto 2026</h2>
        <button>›</button>
        <div />
        <button className="is-active">Semana</button>
        <button>Mês</button>
      </div>
      <div className="cx-calendar">
        {days.map((day, i) => (
          <section key={day}>
            <header>{day}</header>
            <div className="cx-time">09:00</div>
            {(i === 1 || i === 3 || i === 5) && (
              <button
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
            <span>♡</span>
            <span>○</span>
            <span>⌁</span>
          </div>
          <p>
            <b>cafeaurora</b> O primeiro gole não acorda apenas o corpo. Ele
            abre espaço para o que importa.
          </p>
        </div>
        <aside className="cx-publish-panel">
          <section>
            <small>CANAL</small>
            <button className="cx-channel">
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
              <button className="is-active">
                <Clock3 />
                Agendar
              </button>
              <button>
                <Zap />
                Agora
              </button>
            </div>
            <input
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
            onClick={() => navigate(`/content/${post.id}/remix`)}
          >
            Reutilizar
          </Button>
          <Button
            tone="primary"
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
            <button onClick={() => navigate("/campaigns/active")}>
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
          <Button icon={Send} onClick={() => navigate(`/publish/${post.id}`)}>
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
        <Button onClick={() => navigate("/content/post-ritual")}>
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
          onClick={() => setApproved(!approved)}
        >
          {approved ? "Direção aprovada" : "Aprovar direção"}
        </Button>
        <Button
          icon={Sparkles}
          onClick={() => setAngleVersion((value) => value + 1)}
        >
          {angleVersion ? "Novo ângulo aplicado" : "Explorar outro ângulo"}
        </Button>
      </div>
      <CampaignTabs id={id} navigate={navigate} active="Direção" />
      <div className="cx-world-subtabs">
        <button className="is-active">Mundo</button>
        <button onClick={() => navigate(`/campaigns/${id}/moodboard`)}>
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
          <Button onClick={() => navigate(`/campaigns/${id}/moodboard`)}>
            Abrir Moodboard
          </Button>
          <Button
            tone="primary"
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
          onClick={() => setShared(!shared)}
        >
          {shared ? "Link copiado" : "Compartilhar"}
        </Button>
      </div>
      <div className="cx-moodboard-tabs">
        <button>Visão geral</button>
        <button className="is-active">Moodboard</button>
        <button>Narrativa</button>
        <button>Peças</button>
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
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Buscar referências"
              />
            </label>
            <Button
              tone="primary"
              icon={added ? Check : Plus}
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
          onClick={() => navigate("/settings/ai-governance")}
        >
          Histórico
        </Button>
        <Button
          tone="primary"
          icon={Sparkles}
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
            <Button onClick={() => navigate("/settings/brand-memory")}>
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
          <Button onClick={() => navigate("/settings/brand-memory/sources")}>
            Ver fontes, mudanças e responsáveis
          </Button>
        </aside>
      </div>
    </section>
  );
}

function ApprovedLibrarySurface({ navigate, setToast }: AnyRecord) {
  const assets = [
    ["Ritual de foco 01", "Post · 4 usos", phase3Arts[0]],
    ["Aurora — UGC", "UGC · 2 usos", phase3Arts[1]],
    ["Carrossel tipográfico", "Carrossel · 3 usos", phase3Arts[2]],
    ["Origem e textura", "Foto · 5 usos", phase3Arts[4]],
    ["Oferta espresso", "Produto · licenciado", phase3Arts[3]],
    ["Produto limpo", "Produto · próprio", phase3Arts[5]],
    ["Textura Cerrado", "Referência · interna", phase3Arts[4]],
    ["Fumaça e movimento", "Referência · licenciada", phase3Arts[0]],
  ];
  const [selected, setSelected] = React.useState(0);
  const [query, setQuery] = React.useState("");
  const [deleted, setDeleted] = React.useState(false);
  const visible = assets.filter((x) =>
    x[0].toLowerCase().includes(query.toLowerCase()),
  );
  const current = assets[selected] || assets[0];
  return (
    <section className="cx-library-approved">
      <header>
        <div>
          <h1>Biblioteca</h1>
          <p>Tudo o que a marca pode reutilizar, adaptar e provar.</p>
        </div>
        <Button icon={Upload} onClick={() => setToast("Upload preparado")}>
          Upload
        </Button>
        <Button tone="primary" icon={Plus}>
          Criar modelo
        </Button>
      </header>
      <nav>
        {["Arquivos", "Modelos", "Marca", "Campanhas", "Linhagem"].map(
          (x, i) => (
            <button className={i === 0 ? "is-active" : ""} key={x}>
              {x}
            </button>
          ),
        )}
      </nav>
      <div className="cx-library-toolbar">
        <label>
          <Search />
          <input
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
                <button>Ver campanha →</button>
              </div>
              <div className="cx-library-used">
                {visible.slice(0, 4).map((asset, i) => (
                  <button
                    className={selected === i ? "is-active" : ""}
                    onClick={() => setSelected(i)}
                    key={asset[0]}
                  >
                    <img src={asset[2]} />
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
                  <button onClick={() => setSelected(i + 4)} key={asset[0]}>
                    <img src={asset[2]} />
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
                <button>Abrir →</button>
              </article>
            </>
          )}
        </main>
        <aside>
          <h2>{current[0]}</h2>
          <p>Imagem selecionada</p>
          <div className="cx-library-preview">
            <img src={current[2]} />
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
            <button>Abrir →</button>
          </article>
          <KeyValue label="Origem" value="Moodboard / Ref. 04" />
          <KeyValue label="Alterações" value="Corte, contraste, texto" />
          <Button
            tone="primary"
            onClick={() => navigate("/content/post-ritual/edit?mode=visual")}
          >
            Inserir no editor
          </Button>
          <Button onClick={() => navigate("/content/post-ritual/remix")}>
            Criar variação com contexto
          </Button>
          <button className="cx-delete-asset" onClick={() => setDeleted(true)}>
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
          <button className="is-active">Todos</button>
          <button>Imagens</button>
          <button>Vídeos</button>
          <button>Logos</button>
          <button>Documentos</button>
        </div>
        <label>
          <Search />
          <input placeholder="Buscar por nome ou tag" />
        </label>
      </div>
      {assets.length ? (
        <div className="cx-assets">
          {assets.map((asset: AnyRecord, i: number) => (
            <button
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
          <Button onClick={() => navigate("/content/post-ritual/remix")}>
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
            <button>
              <ArrowRight />
            </button>
          </article>
        ))}
      </div>
    </Page>
  );
}

function ApprovedFactorySurface({ navigate, setToast, brand }: AnyRecord) {
  const [round, setRound] = React.useState(false);
  const isHorizonte = brand?.id === "horizonte";
  const factoryVisuals = isHorizonte
    ? [
        "/canonical/brands/horizonte/signal.svg",
        "/canonical/brands/horizonte/winner.svg",
        "/canonical/brands/horizonte/campaign.svg",
      ]
    : [phase3Arts[2], phase3Arts[4], phase3Arts[0]];
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
          onClick={() => navigate("/campaigns/new")}
        >
          Nova produção
        </Button>
      </header>
      <div className="cx-factory-metrics">
        {[
          ["12", "PEÇAS EM PROCESSAMENTO"],
          ["3", "PRECISAM DE VOCÊ"],
          ["5", "PRONTOS HOJE"],
          ["18", "PEÇAS NA SEMANA"],
        ].map(([v, l], i) => (
          <article className={`tone-${i}`} key={l}>
            <strong>{v}</strong>
            <span>{l}</span>
          </article>
        ))}
        <small>Capacidade saudável · 2 slots livres</small>
      </div>
      <div className="cx-factory-system">
        <section className="cx-factory-inputs">
          <header>
            <span>01</span>
            <div>
              <small>ENTRADAS VIVAS</small>
              <h2>Contexto que alimenta esta rodada</h2>
            </div>
            <Button onClick={() => navigate("/radar")}>Ver origem</Button>
          </header>
          <div>
            {[
              [
                Radar,
                "Oportunidade",
                isHorizonte ? "+42% prevenção" : "+38% ritual de foco",
              ],
              [
                Target,
                "Oferta",
                isHorizonte ? "Check-up integrado" : "Kit quatro origens",
              ],
              [FileText, "Briefing", "Promessa e guardrails validados"],
              [
                BarChart3,
                "Vencedor",
                isHorizonte ? "2,6× compartilhamentos" : "3× mais salvamentos",
              ],
            ].map(([Icon, label, value]) => (
              <article key={String(label)}>
                <Icon />
                <small>{label}</small>
                <b>{value}</b>
                <i>✓ pronto</i>
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
                {isHorizonte
                  ? "Clareza clínica sem alarmismo"
                  : "Presença antes da produtividade"}
              </h2>
            </div>
            <strong>COERÊNCIA 92%</strong>
          </header>
          <div>
            {[
              "Tensão real",
              "Prova da marca",
              "Formato certo",
              "CTA responsável",
            ].map((item, index) => (
              <React.Fragment key={item}>
                <span>
                  <b>{index + 1}</b>
                  {item}
                </span>
                {index < 3 && <ArrowRight />}
              </React.Fragment>
            ))}
          </div>
        </section>

        <section className="cx-factory-engine">
          <header>
            <span>03</span>
            <div>
              <small>MOTOR CLICKO · PROCESSANDO</small>
              <h2>Uma promessa, três células de produção</h2>
            </div>
            <em>7 variações originadas</em>
          </header>
          <div className="cx-factory-cells">
            {[
              [
                "Carrossel de autoridade",
                "6 slides · 4:5",
                "Montagem 78%",
                "REVISÃO HUMANA",
                "Instagram",
              ],
              [
                isHorizonte ? "Reel com especialista" : "Reel com Mariana",
                "25 s · 9:16",
                "Calibrando 64%",
                "CENA PENDENTE",
                "Reels + TikTok",
              ],
              [
                "Sequência de Stories",
                "5 telas · 9:16",
                "Finalização 91%",
                "PRÉ-FLIGHT",
                "Stories",
              ],
            ].map(([title, format, progress, gate, destination], index) => (
              <article key={title}>
                <img src={factoryVisuals[index]} alt="" />
                <span>{String(index + 1).padStart(2, "0")}</span>
                <small>{format}</small>
                <h3>{title}</h3>
                <div>
                  <i style={{ width: `${[78, 64, 91][index]}%` }} />
                </div>
                <p>{progress}</p>
                <b>{gate}</b>
                <footer>Destino · {destination}</footer>
              </article>
            ))}
          </div>
        </section>

        <aside className="cx-factory-decisions">
          <header>
            <span>04</span>
            <div>
              <small>GATES HUMANOS</small>
              <h2>3 decisões antes da saída</h2>
            </div>
          </header>
          {[
            [
              "Cenário do vídeo",
              "Aceitar consultório com luz natural?",
              "Alta",
            ],
            [
              "Contraste do slide 04",
              "Texto está abaixo do mínimo da marca.",
              "Média",
            ],
            [
              "Cadência de sábado",
              "Dois conteúdos disputam o mesmo horário.",
              "Média",
            ],
          ].map(([title, detail, urgency], index) => (
            <button
              key={title}
              onClick={() =>
                navigate(
                  index === 2
                    ? "/calendar"
                    : "/approvals/post-ritual?view=creative",
                )
              }
            >
              <i>{index + 1}</i>
              <span>
                <b>{title}</b>
                <small>{detail}</small>
              </span>
              <em>{urgency}</em>
              <ChevronRight />
            </button>
          ))}
        </aside>

        <section className="cx-factory-destinations">
          <small>DESTINOS DESTA RODADA</small>
          <div>
            {[
              "Instagram · 3",
              "TikTok · 1",
              "Stories · 3",
              "Biblioteca · 7",
              "Aprendizado · ligado",
            ].map((item) => (
              <span key={item}>{item}</span>
            ))}
          </div>
          <strong>5 peças prontas hoje · 2 slots de capacidade livres</strong>
        </section>
      </div>
      <footer className="cx-factory-next">
        <small>✦ PRÓXIMA MELHOR AÇÃO</small>
        <div>
          <b>
            {round
              ? "Nova rodada iniciada com contexto preservado."
              : "Transforme ‘Ritual de foco’ em 3 Reels com rosto mantendo a promessa e a direção visual."}
          </b>
          <span>Baseado no vencedor dos últimos 30 dias</span>
        </div>
        <Button
          tone="primary"
          onClick={() => {
            setRound(true);
            setToast("Nova rodada iniciada");
          }}
        >
          Iniciar nova rodada
        </Button>
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
          <button onClick={() => navigate("/campaigns/new")}>
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
          <button key={title} onClick={() => navigate(path)}>
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
        <Button onClick={() => navigate("/content/draft/edit?mode=visual")}>
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
          onClick={() => navigate("/campaigns/new")}
        >
          Novo projeto
        </Button>
      </div>
      <div className="cx-projects-toolbar">
        <button>
          {brand?.name || "Workspace"} <ChevronDown />
        </button>
        <label>
          <Search />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Buscar projetos"
          />
        </label>
        {["Todos", "Em produção", "Em revisão", "Agendados", "Concluídos"].map(
          (x) => (
            <button
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
              <button key={p.id} onClick={() => navigate(`/campaigns/${p.id}`)}>
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
              <button key={p.id} onClick={() => navigate(`/campaigns/${p.id}`)}>
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
    mark: "♪",
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
    mark: "▶",
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
            <Button onClick={() => navigate("/apps/instagram")}>
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
        <Button tone="primary" onClick={() => setManaging(!managing)}>
          {managing ? "Concluir" : "Gerenciar"}
        </Button>
      </header>
      <nav>
        {config.tabs.map((x: string) => (
          <button
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

function PresenterStudioSurface({
  navigate,
  setToast,
  data,
  demo,
  brand,
}: AnyRecord) {
  const [generated, setGenerated] = React.useState(false);
  const [captured, setCaptured] = React.useState(false);
  const [scenario, setScenario] = React.useState<"yes" | "no" | "">("");
  React.useEffect(() => {
    const session = (data.snapshot?.presenterSessions || []).find(
      (item: AnyRecord) => item.resourceKey === "post-ritual",
    );
    if (!session) return;
    setGenerated(Boolean(session.payload?.generated));
    setCaptured(Boolean(session.payload?.captured));
    setScenario(session.payload?.scenario || "");
  }, [data.snapshot?.presenterSessions]);
  const persist = (next: AnyRecord) => {
    if (demo) return;
    void data.saveWorkspaceResource("presenter_session", "post-ritual", {
      generated,
      captured,
      scenario,
      rights: "valid",
      externalPublishing: false,
      updatedAt: new Date().toISOString(),
      ...next,
    });
  };
  const isHorizonte = brand?.id === "horizonte";
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
          <button onClick={() => navigate("/content")}>
            ← Voltar ao projeto
          </button>
          <small>SALVO · HÁ 12 S</small>
          <Button
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
          <span>VIDEO STUDIO　/　FACTORY CELL　/　PRODUÇÃO APROVADA</span>
          <div>
            <h1>
              {isHorizonte
                ? "Dra. Renata × Clínica Horizonte"
                : "Mariana × Café Aurora"}
            </h1>
            <small>
              Identidade de produção para{" "}
              {isHorizonte ? "Cuidar antes da urgência" : "Ritual de Foco"} —
              pronta para gerar testes, não para publicar.
            </small>
          </div>
          <nav>
            <i>CONTEXTO ✓</i>
            <i>MATERIAIS 8/10</i>
            <i>CALIBRANDO</i>
            <i>TESTES {generated ? "1/3" : "0/3"}</i>
          </nav>
          <Button
            tone="primary"
            onClick={() => {
              setGenerated(true);
              persist({ generated: true });
              setToast("Primeiro teste gerado para revisão");
            }}
          >
            Gerar primeiro teste
          </Button>
        </header>
        <div className="cx-presenter-focusbar">
          <article>
            <small>1 · O SISTEMA ESTÁ FAZENDO</small>
            <b>
              {captured
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
                : "Primeiro teste não publicável"}
            </b>
          </article>
        </div>
        <div className="cx-presenter-grid">
          <aside className="cx-presenter-materials">
            <small>MATÉRIA-PRIMA</small>
            <article>
              <img src="/canonical/figma/phase5/presenter-source.jpeg" />
              <b>
                {isHorizonte
                  ? "Renata Lima · fonte real"
                  : "Mariana Costa · fonte real"}
              </b>
              <em>Rosto + voz · consentimento válido</em>
            </article>
            <nav>
              <button className="is-active">VÍDEO</button>
              <button>VOZ</button>
              <button>MARCA</button>
            </nav>
            {[
              ["3 takes aprovados", "Expressão, pausas e planos"],
              ["2 áudios limpos", "Voz natural · 4 min 18 s"],
              ["4 cenários reais", "Escritório, bancada e externo"],
              ["Brand kit aplicado", "Cores, tipografia e produto"],
            ].map(([a, b]) => (
              <span key={a}>
                <b>{a}</b>
                <small>{b}</small>
                <i>✓</i>
              </span>
            ))}
            <section>
              <b>NÃO NEGOCIÁVEIS</b>
              <p>
                · Sem voz publicitária artificial
                <br />· Sem alterar traços do rosto
                <br />· Produto sempre fiel ao original
              </p>
              <button>Editar regras →</button>
            </section>
            <Button>＋ Adicionar fonte real</Button>
          </aside>
          <main className="cx-presenter-bench">
            <small>BANCADA DE IDENTIDADE</small>
            <h2>Receita · Founder-led realista</h2>
            <div className="cx-presenter-composition">
              <article>
                <img src="/canonical/figma/phase5/presenter-source.jpeg" />
                <small>FONTE HUMANA · TAKE 07</small>
                <b>Rosto, voz e cadência reais</b>
              </article>
              <i>
                ＋<small>MARCA, ROTEIRO, CONTEXTO</small>
              </i>
              <article className="cx-generated-scene">
                <span>TESTE {generated ? "01" : "00"} · NÃO PUBLICÁVEL</span>
                <img src="/canonical/figma/phase5/presenter-scene.jpeg" />
                <h3>“Clareza começa antes da primeira tarefa.”</h3>
                <small>25 S · Founder-led · Ritmo 6.5/10</small>
              </article>
            </div>
            <div className="cx-presenter-scores">
              {[
                ["REALISMO", "94/100"],
                ["VOZ", "91/100"],
                ["MARCA", "96/100"],
                ["CENA", captured ? "91/100" : "82/100"],
              ].map(([a, b]) => (
                <span key={a}>
                  <small>{a}</small>
                  <b>{b}</b>
                </span>
              ))}
            </div>
            <div className="cx-presenter-next">
              <small>PRÓXIMA MELHOR AÇÃO</small>
              <b>
                {captured
                  ? "Pausas capturadas e cena recalibrada."
                  : "Capturar 8 s de pausa olhando para o produto."}
              </b>
              <Button
                tone="primary"
                onClick={() => {
                  setCaptured(true);
                  persist({ captured: true });
                  setToast("Captura de pausa registrada");
                }}
              >
                {captured ? "Capturado" : "Abrir captura"}
              </Button>
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
                Rosto + voz <b>Permitido</b>
                <br />
                Social + ads <b>Brasil · 12 meses</b>
                <br />
                Alterar traços <strong>Bloqueado</strong>
                <br />
                Política <em>Aprovação extra</em>
              </p>
            </section>
            <section>
              <small>GATES DE AUTENTICIDADE</small>
              <p>
                Rosto <b>Aprovado</b>
                <br />
                Voz <b>Aprovado</b>
                <br />
                Marca <b>Aprovado</b>
                <br />
                Cena <em>{captured ? "Aprovado" : "Revisar luz"}</em>
              </p>
              <small>Nada sai desta célula sem revisão humana.</small>
            </section>
            <section className="is-decision">
              <small>1 DECISÃO SUA</small>
              <b>Aceitar o cenário de escritório?</b>
              <div>
                <button
                  className={scenario === "no" ? "is-active" : ""}
                  onClick={() => {
                    setScenario("no");
                    persist({ scenario: "no" });
                  }}
                >
                  Não
                </button>
                <button
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
                Provar antes de liberar · {generated ? "1/3" : "0/3"} aprovados
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
                    generated && a === "FOUNDER-LED" ? "is-active" : ""
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
                  <em>{c}</em>
                </article>
              ))}
            </div>
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
          <Button tone="primary" onClick={() => navigate("/settings/channels")}>
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
          <button onClick={onClose} aria-label="Fechar launcher">
            <X />
          </button>
        </header>
        <label className="cx-create-search">
          <Search />
          <input
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
              <button key={title} onClick={() => navigate(path)}>
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
                  <button key={label} onClick={() => navigate(path)}>
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
          <button onClick={onClose} aria-label="Fechar central de atividades">
            <X />
          </button>
        </header>
        <div className="cx-activity-tools">
          <button
            onClick={() => setRead(new Set(events.map((e: AnyRecord) => e.id)))}
          >
            Marcar como lidas
          </button>
        </div>
        <div className="cx-activity-filter">
          {["Todas", "Aprovações", "Menções", "Sistema"].map((x) => (
            <button
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
          <button onClick={onClose} aria-label="Fechar seletor de workspace">
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
            onClick={() => {
              onClose();
              navigate("/settings/workspaces/new");
            }}
          >
            <Plus />
            Criar workspace
          </button>
          <button
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
