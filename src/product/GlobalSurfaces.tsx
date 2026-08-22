import React from "react";
import {
  BarChart3,
  Bell,
  BookOpen,
  Bot,
  CalendarDays,
  ChevronDown,
  FileText,
  FolderKanban,
  Grid2X2,
  Image,
  LayoutGrid,
  Menu,
  MonitorPlay,
  PanelLeftClose,
  Pin,
  Plus,
  Radar,
  Search,
  Settings2,
  Sparkles,
  Star,
  Users,
  Video,
  Workflow,
  X,
  CircleUserRound,
} from "lucide-react";
import { useGovernance } from "../context/GovernanceContext";
import { useOperations } from "../context/OperationsContext";
import { useServerState } from "../context/ServerStateContext";

interface GlobalSurfacesProps {
  pathname: string;
  search: string;
  onNavigate: (path: string) => void;
  onOpenSpotlight: () => void;
}

type ToolItem = {
  label: string;
  description: string;
  path: string;
  icon: React.ComponentType<{ className?: string }>;
  group: string;
};

const tools: ToolItem[] = [
  {
    label: "Radar",
    description: "Priorizar sinais e oportunidades",
    path: "/radar",
    icon: Radar,
    group: "Inteligência",
  },
  {
    label: "Projetos",
    description: "Planejar narrativa e execução",
    path: "/projects",
    icon: Sparkles,
    group: "Estratégia",
  },
  {
    label: "Content Board",
    description: "Operar toda a produção",
    path: "/content",
    icon: Grid2X2,
    group: "Conteúdo",
  },
  {
    label: "Editorial Desk",
    description: "Criar texto com contexto",
    path: "/content/draft/edit?mode=editorial",
    icon: FileText,
    group: "Criação",
  },
  {
    label: "Visual Editor",
    description: "Compor por camadas",
    path: "/content/draft/edit?mode=visual",
    icon: Image,
    group: "Criação",
  },
  {
    label: "Motion Studio",
    description: "Editar vídeo e movimento",
    path: "/content/draft/edit?mode=video",
    icon: Video,
    group: "Criação",
  },
  {
    label: "Calendário",
    description: "Planejar e detectar conflitos",
    path: "/calendar",
    icon: CalendarDays,
    group: "Operação",
  },
  {
    label: "Analytics",
    description: "Aprender com evidência",
    path: "/analytics/learning",
    icon: BarChart3,
    group: "Performance",
  },
  {
    label: "Automações",
    description: "Orquestrar fluxos auditáveis",
    path: "/automations/active",
    icon: Workflow,
    group: "Operação",
  },
  {
    label: "Memória da Marca",
    description: "Gerir fontes e versões",
    path: "/brand-memory",
    icon: BookOpen,
    group: "Inteligência",
  },
  {
    label: "Copiloto",
    description: "Conversar no contexto atual",
    path: "/copilot?context=current",
    icon: Bot,
    group: "Inteligência",
  },
  {
    label: "Governança de IA",
    description: "Configurar autonomia e fontes",
    path: "/settings/ai-governance",
    icon: Settings2,
    group: "Governança",
  },
];

function queryPath(
  pathname: string,
  search: string,
  key: string,
  value?: string,
) {
  const params = new URLSearchParams(search);
  if (value) params.set(key, value);
  else params.delete(key);
  const query = params.toString();
  return `${pathname}${query ? `?${query}` : ""}`;
}

export function GlobalSurfaces({
  pathname,
  search,
  onNavigate,
  onOpenSpotlight,
}: GlobalSurfacesProps) {
  const params = new URLSearchParams(search);
  const [localAtlas, setLocalAtlas] = React.useState(false);
  const [localCreate, setLocalCreate] = React.useState(false);
  const [localMenu, setLocalMenu] = React.useState(false);
  const atlasState = params.get("atlas");
  const createOpen = params.get("create") === "open" || localCreate;
  const menuOpen = params.get("menu") === "open" || localMenu;
  const workspaceState = params.get("workspace");
  const atlasOpen =
    ["open", "search", "customize"].includes(atlasState || "") || localAtlas;
  const server = useServerState();

  React.useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (
        (event.metaKey || event.ctrlKey) &&
        event.shiftKey &&
        event.key.toLowerCase() === "k"
      ) {
        event.preventDefault();
        setLocalAtlas(true);
      }
      if (event.key === "Escape") {
        setLocalAtlas(false);
        setLocalCreate(false);
        setLocalMenu(false);
        if (
          atlasState ||
          params.get("create") ||
          params.get("menu") ||
          workspaceState
        )
          onNavigate(pathname);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [atlasState, onNavigate, params, pathname, workspaceState]);

  React.useEffect(() => {
    if (params.get("spotlight") === "open") onOpenSpotlight();
  }, [onOpenSpotlight, params]);

  const closeAtlas = () => {
    setLocalAtlas(false);
    onNavigate(queryPath(pathname, search, "atlas"));
  };
  const closeCreate = () => {
    setLocalCreate(false);
    onNavigate(queryPath(pathname, search, "create"));
  };
  const closeMenu = () => {
    setLocalMenu(false);
    onNavigate(queryPath(pathname, search, "menu"));
  };
  const lifecycle = [
    { label: "Dashboard", path: "/dashboard" },
    { label: "Descobrir", path: "/discover" },
    { label: "Planejar", path: "/projects" },
    { label: "Criar", path: "/content/dashboard" },
    { label: "Aprovar", path: "/approvals/post-1" },
    { label: "Publicar", path: "/publish/active" },
    { label: "Aprender", path: "/analytics/learning" },
  ];
  const creativeContext =
    pathname.startsWith("/content") || pathname.startsWith("/library");
  const lifecycleActive = (label: string, path: string) => {
    if (label === "Dashboard") return pathname === "/dashboard";
    if (label === "Descobrir")
      return pathname === "/discover" || pathname === "/radar";
    if (label === "Planejar")
      return (
        pathname.startsWith("/projects") || pathname.startsWith("/campaigns")
      );
    if (label === "Criar")
      return pathname.startsWith("/content") || pathname.startsWith("/library");
    return (
      pathname === path ||
      pathname.startsWith(`${path.split("/").slice(0, 2).join("/")}/`)
    );
  };

  return (
    <>
      <header className="sticky top-0 z-50 flex h-12 items-center border-b border-[#f0a0a0]/25 bg-[#111]/95 backdrop-blur-xl">
        <button
          type="button"
          onClick={() => onNavigate("/dashboard")}
          className="flex h-full shrink-0 items-center border-r border-[#f0a0a0]/20 px-4 text-[15px] font-bold tracking-[-0.045em] text-[#ffb5b5] hover:bg-[#ffb5b5]/5"
        >
          Clicko
        </button>
        <div className="flex min-w-0 flex-1 items-center overflow-x-auto">
          <button
            type="button"
            onClick={() => setLocalMenu(true)}
            className="grid h-12 w-11 shrink-0 place-items-center border-r border-[#f0a0a0]/15 text-[#c8baba] hover:bg-[#ffb5b5]/5 hover:text-[#ffb5b5]"
            aria-label="Abrir menu essencial"
          >
            <Menu className="h-3.5 w-3.5" />
          </button>
          {lifecycle.map((item) => {
            const active = lifecycleActive(item.label, item.path);
            return (
              <button
                key={item.label}
                type="button"
                onClick={() => onNavigate(item.path)}
                aria-current={active ? "page" : undefined}
                className={`relative h-12 shrink-0 px-3 text-[9px] font-semibold transition ${active ? "bg-[#ffb5b5]/[0.07] text-[#fff2f2]" : "text-[#a99c9c] hover:bg-white/[0.025] hover:text-white"}`}
              >
                {item.label}
                {active && (
                  <span className="absolute inset-x-2 bottom-0 h-px bg-[#ff9ea3]" />
                )}
              </button>
            );
          })}
        </div>
        <div className="flex h-full shrink-0 items-center border-l border-[#f0a0a0]/15">
          <button
            type="button"
            onClick={onOpenSpotlight}
            className="hidden h-7 w-36 items-center gap-2 border border-[#f0a0a0]/20 bg-[#181616] px-2 text-left text-[8px] text-[#837878] lg:flex"
          >
            <Search className="h-3 w-3" /> Buscar
          </button>
          <button
            type="button"
            onClick={() => setLocalAtlas(true)}
            className="grid h-12 w-10 place-items-center text-[#b7aaaa] hover:bg-[#ffb5b5]/5 hover:text-[#ffb5b5]"
            aria-label="Abrir Atlas"
          >
            <LayoutGrid className="h-3.5 w-3.5" />
          </button>
          <div className="relative">
            <button
              type="button"
              onClick={() => setLocalCreate((value) => !value)}
              className="mx-1 inline-flex h-7 items-center gap-2 bg-[#ffb5b5] px-3 text-[9px] font-bold text-[#241010] hover:bg-[#ffc6c6]"
            >
              <Plus className="h-3.5 w-3.5" />
              Novo
              <ChevronDown className="h-3 w-3" />
            </button>
            {createOpen && (
              <CreateDropdown onClose={closeCreate} onNavigate={onNavigate} />
            )}
          </div>
          <button
            className="grid h-12 w-9 place-items-center text-[#b7aaaa] hover:text-[#ffb5b5]"
            aria-label="Notificações"
          >
            <Bell className="h-3.5 w-3.5" />
          </button>
          <button
            type="button"
            onClick={() =>
              server.status === "connected"
                ? void server.refresh()
                : onNavigate("/login")
            }
            className="grid h-12 w-10 place-items-center border-l border-[#f0a0a0]/15 text-[#b7aaaa] hover:text-[#ffb5b5]"
            title={
              server.status === "connected"
                ? `Sincronizado como ${server.bootstrap?.user.name}`
                : "Entrar para sincronizar"
            }
          >
            <CircleUserRound className="h-4 w-4" />
          </button>
        </div>
      </header>
      {creativeContext && (
        <aside className="fixed bottom-0 left-0 top-12 z-40 flex w-[52px] flex-col items-center border-r border-[#f0a0a0]/20 bg-[#121111] py-2">
          {[
            {
              icon: LayoutGrid,
              label: "Content Command",
              path: "/content/dashboard",
            },
            {
              icon: Grid2X2,
              label: "Inventário",
              path: "/content?view=inventory",
            },
            {
              icon: FileText,
              label: "Criar post",
              path: "/content/new?type=post",
            },
            {
              icon: Image,
              label: "Visual",
              path: "/content/draft/edit?mode=visual",
            },
            {
              icon: Video,
              label: "Motion",
              path: "/content/draft/edit?mode=video",
            },
            { icon: BookOpen, label: "Assets", path: "/library/assets" },
            { icon: Workflow, label: "Lineage", path: "/library/lineage" },
          ].map(({ icon: Icon, label, path }) => (
            <button
              key={label}
              type="button"
              onClick={() => onNavigate(path)}
              aria-label={label}
              title={label}
              className={`relative grid h-10 w-10 place-items-center border border-transparent text-[#9b8f8f] hover:border-[#f0a0a0]/20 hover:text-[#ffb5b5] ${pathname === path.split("?")[0] ? "bg-[#ffb5b5]/10 text-[#ffb5b5]" : ""}`}
            >
              <Icon className="h-3.5 w-3.5" />
            </button>
          ))}
        </aside>
      )}
      {atlasOpen && (
        <ToolAtlas
          mode={atlasState || "open"}
          onClose={closeAtlas}
          onNavigate={onNavigate}
        />
      )}
      {menuOpen && (
        <EssentialMenu onClose={closeMenu} onNavigate={onNavigate} />
      )}
      {workspaceState && (
        <WorkspaceDialog
          compact={workspaceState === "menu"}
          onClose={() => onNavigate(queryPath(pathname, search, "workspace"))}
          onNavigate={onNavigate}
        />
      )}
    </>
  );
}

function CreateDropdown({
  onClose,
  onNavigate,
}: {
  onClose: () => void;
  onNavigate: (path: string) => void;
}) {
  const choices = [
    {
      label: "Post editorial",
      detail: "Texto e preview",
      path: "/content/new?type=post",
      icon: FileText,
    },
    {
      label: "Carrossel",
      detail: "Narrativa por slides",
      path: "/content/draft/edit?mode=carousel",
      icon: Grid2X2,
    },
    {
      label: "Visual",
      detail: "Composição por camadas",
      path: "/content/draft/edit?mode=visual",
      icon: Image,
    },
    {
      label: "Vídeo",
      detail: "Timeline e motion",
      path: "/content/draft/edit?mode=video",
      icon: MonitorPlay,
    },
    {
      label: "Reutilizar",
      detail: "Derivar de conteúdo",
      path: "/content",
      icon: Sparkles,
    },
    {
      label: "Campanha",
      detail: "Da oportunidade ao kit",
      path: "/campaigns/new",
      icon: Radar,
    },
  ];
  return (
    <div className="absolute right-0 top-11 z-50 w-[340px] max-w-[calc(100vw-24px)] rounded-2xl border border-white/10 bg-[var(--clicko-surface-2)] p-2 shadow-2xl shadow-black/70">
      <div className="flex items-center justify-between px-2 py-2">
        <span className="text-[9px] font-bold uppercase tracking-[0.18em] text-white/35">
          Criar ou retomar
        </span>
        <button onClick={onClose} className="text-white/35 hover:text-white">
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="grid grid-cols-2 gap-1">
        {choices.map(({ label, detail, path, icon: Icon }) => (
          <button
            key={label}
            onClick={() => {
              onClose();
              onNavigate(path);
            }}
            className="rounded-xl border border-transparent p-3 text-left hover:border-white/[0.08] hover:bg-white/[0.04]"
          >
            <Icon className="h-4 w-4 text-[var(--clicko-creative)]" />
            <div className="mt-3 text-xs font-semibold text-white">{label}</div>
            <div className="mt-1 text-[9px] text-white/35">{detail}</div>
          </button>
        ))}
      </div>
    </div>
  );
}

function ToolAtlas({
  mode,
  onClose,
  onNavigate,
}: {
  mode: string;
  onClose: () => void;
  onNavigate: (path: string) => void;
}) {
  const [query, setQuery] = React.useState(
    mode === "search" ? "criar visual" : "",
  );
  const [pinned, setPinned] = React.useState<string[]>(() => {
    try {
      return JSON.parse(
        localStorage.getItem("clicko:tool-atlas:pinned") ||
          '["Radar","Visual Editor"]',
      );
    } catch {
      return ["Radar"];
    }
  });
  const visible = tools.filter((tool) =>
    `${tool.label} ${tool.description} ${tool.group}`
      .toLowerCase()
      .includes(query.toLowerCase()),
  );
  const togglePin = (label: string) => {
    const next = pinned.includes(label)
      ? pinned.filter((item) => item !== label)
      : [...pinned, label];
    setPinned(next);
    localStorage.setItem("clicko:tool-atlas:pinned", JSON.stringify(next));
  };
  return (
    <div
      className="fixed inset-0 z-[80] grid place-items-start bg-black/75 p-3 pt-[8vh] backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-label="Atlas de ferramentas"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div className="mx-auto w-full max-w-5xl overflow-hidden rounded-3xl border border-white/10 bg-[var(--clicko-surface-1)] shadow-2xl shadow-black">
        <header className="flex items-center gap-3 border-b border-white/[0.07] p-4">
          <Search className="h-5 w-5 text-[var(--clicko-creative)]" />
          <input
            autoFocus
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="O que você quer fazer?"
            className="min-w-0 flex-1 bg-transparent text-base text-white outline-none placeholder:text-white/25"
          />
          <span className="rounded-lg border border-white/10 px-2 py-1 text-[9px] text-white/30">
            ESC
          </span>
          <button onClick={onClose} className="text-white/35 hover:text-white">
            <X className="h-5 w-5" />
          </button>
        </header>
        <div className="grid max-h-[70vh] overflow-y-auto p-4 sm:grid-cols-2 lg:grid-cols-3">
          {visible.map(({ label, description, path, icon: Icon }) => (
            <div
              key={label}
              className="group relative rounded-2xl border border-transparent p-2 hover:border-white/[0.08] hover:bg-white/[0.025]"
            >
              <button
                onClick={() => {
                  onClose();
                  onNavigate(path);
                }}
                className="w-full p-3 text-left"
              >
                <div className="flex items-start justify-between">
                  <span className="grid h-9 w-9 place-items-center rounded-xl border border-[var(--clicko-creative)]/20 bg-[var(--clicko-creative)]/10">
                    <Icon className="h-4 w-4 text-[var(--clicko-creative)]" />
                  </span>
                  {pinned.includes(label) && (
                    <Star className="h-3.5 w-3.5 fill-[var(--clicko-action)] text-[var(--clicko-action)]" />
                  )}
                </div>
                <div className="mt-5 text-sm font-semibold text-white">
                  {label}
                </div>
                <div className="mt-1 text-[10px] text-white/35">
                  {description}
                </div>
              </button>
              <button
                onClick={() => togglePin(label)}
                className="absolute bottom-3 right-3 grid h-7 w-7 place-items-center rounded-lg text-white/25 opacity-0 hover:bg-white/[0.06] hover:text-white group-hover:opacity-100"
                aria-label={`Fixar ${label}`}
              >
                <Pin className="h-3.5 w-3.5" />
              </button>
            </div>
          ))}
        </div>
        {mode === "customize" && (
          <footer className="border-t border-white/[0.07] px-5 py-3 text-[10px] text-white/35">
            {pinned.length} ferramentas fixadas · personalização salva neste
            workspace.
          </footer>
        )}
      </div>
    </div>
  );
}

function EssentialMenu({
  onClose,
  onNavigate,
}: {
  onClose: () => void;
  onNavigate: (path: string) => void;
}) {
  const items = [
    { label: "Dashboard", path: "/dashboard", icon: LayoutGrid },
    { label: "Descobrir", path: "/discover", icon: Radar },
    { label: "Projetos", path: "/projects", icon: Sparkles },
    { label: "Conteúdo", path: "/content", icon: FolderKanban },
    { label: "Equipe", path: "/settings/team", icon: Users },
    { label: "Configurações", path: "/settings/profile", icon: Settings2 },
  ];
  return (
    <div
      className="fixed inset-0 z-[75] bg-black/65 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <aside className="h-full w-[300px] max-w-[85vw] border-r border-white/10 bg-[var(--clicko-surface-1)] p-4 shadow-2xl">
        <div className="flex items-center justify-between border-b border-white/[0.07] pb-4">
          <div className="text-sm font-semibold text-white">Menu essencial</div>
          <button onClick={onClose} className="text-white/35 hover:text-white">
            <PanelLeftClose className="h-5 w-5" />
          </button>
        </div>
        <nav className="mt-4 space-y-1">
          {items.map(({ label, path, icon: Icon }) => (
            <button
              key={label}
              onClick={() => {
                onClose();
                onNavigate(path);
              }}
              className="flex w-full items-center gap-3 rounded-xl px-3 py-3 text-xs font-semibold text-white/55 hover:bg-white/[0.05] hover:text-white"
            >
              <Icon className="h-4 w-4 text-[var(--clicko-creative)]" />
              {label}
            </button>
          ))}
        </nav>
      </aside>
    </div>
  );
}

function WorkspaceDialog({
  compact,
  onClose,
  onNavigate,
}: {
  compact: boolean;
  onClose: () => void;
  onNavigate: (path: string) => void;
}) {
  const { accounts, activeAccount, switchAccount } = useGovernance();
  const { activeWorkspace } = useOperations();
  return (
    <div
      className="fixed inset-0 z-[78] grid place-items-center bg-black/70 p-4 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        className={`w-full rounded-2xl border border-white/10 bg-[var(--clicko-surface-1)] p-3 shadow-2xl ${compact ? "max-w-sm" : "max-w-lg"}`}
      >
        <div className="flex items-center justify-between px-2 py-2">
          <div>
            <div className="text-sm font-semibold text-white">
              Trocar workspace
            </div>
            <div className="mt-1 text-[10px] text-white/30">
              Atual: {activeWorkspace.name}
            </div>
          </div>
          <button onClick={onClose} className="text-white/35 hover:text-white">
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="mt-2 space-y-2">
          {accounts.map((account) => (
            <button
              key={account.id}
              onClick={() => {
                switchAccount(account.id);
                onClose();
              }}
              className={`flex w-full items-center gap-3 rounded-xl border p-3 text-left ${account.id === activeAccount?.id ? "border-[var(--clicko-action)]/40 bg-[var(--clicko-action)]/10" : "border-white/[0.07] hover:bg-white/[0.03]"}`}
            >
              <span className="grid h-9 w-9 place-items-center rounded-xl bg-white/[0.06] text-xs font-bold text-white/55">
                {account.name.slice(0, 1)}
              </span>
              <div className="flex-1">
                <div className="text-xs font-semibold text-white">
                  {account.name}
                </div>
                <div className="mt-1 text-[9px] text-white/30">
                  {account.type === "company"
                    ? "Workspace corporativo"
                    : "Workspace pessoal"}
                </div>
              </div>
              {account.id === activeAccount?.id && (
                <span className="h-2 w-2 rounded-full bg-[var(--clicko-action)]" />
              )}
            </button>
          ))}
        </div>
        {!compact && (
          <button
            onClick={() => {
              onClose();
              onNavigate("/workspaces/new");
            }}
            className="mt-3 flex w-full items-center justify-center gap-2 rounded-xl border border-dashed border-white/15 p-3 text-xs font-semibold text-white/50 hover:border-[var(--clicko-action)]/35 hover:text-white"
          >
            <Plus className="h-4 w-4" />
            Novo workspace
          </button>
        )}
      </div>
    </div>
  );
}
