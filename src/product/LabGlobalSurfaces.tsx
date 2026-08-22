import React from "react";
import {
  BarChart3,
  Bell,
  BookOpen,
  Bot,
  CalendarDays,
  Check,
  ChevronDown,
  CircleUserRound,
  Command,
  FolderKanban,
  Home,
  Images,
  Plus,
  Radio,
  Search,
  Settings2,
  ShieldCheck,
  Sparkles,
  Users,
  Workflow,
  X,
} from "lucide-react";
import { useGovernance } from "../context/GovernanceContext";
import { useOperations } from "../context/OperationsContext";
import { useServerState } from "../context/ServerStateContext";

interface LabGlobalSurfacesProps {
  pathname: string;
  search: string;
  onNavigate: (path: string) => void;
  onOpenSpotlight: () => void;
}

const launchItems = [
  { label: "Inspiração e Radar", detail: "Sinais relevantes para a marca", path: "/discover", icon: Sparkles },
  { label: "Creative Lab", detail: "Ideia, referência e geração", path: "/content/dashboard", icon: Command },
  { label: "Projetos", detail: "Boards, campanhas e entregas", path: "/projects", icon: FolderKanban },
  { label: "Biblioteca", detail: "Uploads e peças do workspace", path: "/library/assets", icon: Images },
  { label: "Templates", detail: "Sistemas visuais reutilizáveis", path: "/templates", icon: BookOpen },
  { label: "Memória da marca", detail: "Oferta, público e tom de voz", path: "/brand-memory", icon: Settings2 },
  { label: "Calendário", detail: "Cadência editorial", path: "/calendar", icon: CalendarDays },
  { label: "Aprovações", detail: "Decisões e comentários", path: "/approvals/post-1", icon: ShieldCheck },
  { label: "Publicação", detail: "Fila, canais e horários", path: "/publish/active", icon: Radio },
  { label: "Desempenho", detail: "Aprendizados com evidência", path: "/analytics/learning", icon: BarChart3 },
  { label: "Copiloto", detail: "Conversar usando o contexto atual", path: "/copilot?context=campaign", icon: Bot },
  { label: "Equipe", detail: "Acessos e permissões", path: "/settings/team", icon: Users },
  { label: "Automações", detail: "Gatilhos e regras", path: "/automations/active", icon: Workflow },
] as const;

const destinations = [
  { label: "Home", path: "/dashboard", icon: Home },
  { label: "Criar", path: "/content/dashboard", icon: Sparkles },
  { label: "Projetos", path: "/projects", icon: FolderKanban },
  { label: "Biblioteca", path: "/library/assets", icon: Images },
  { label: "Publicar", path: "/calendar", icon: CalendarDays },
] as const;

function isActive(pathname: string, path: string) {
  if (path === "/dashboard") return pathname === "/dashboard" || pathname === "/";
  if (path === "/content/dashboard") return pathname.startsWith("/content");
  if (path === "/projects")
    return pathname.startsWith("/projects") || pathname.startsWith("/campaigns");
  if (path === "/library/assets") return pathname.startsWith("/library") || pathname === "/templates" || pathname === "/brand-memory";
  return pathname.startsWith("/calendar") || pathname.startsWith("/publish") || pathname.startsWith("/approvals") || pathname.startsWith("/analytics") || pathname === "/settings/channels";
}

export function LabGlobalSurfaces({
  pathname,
  search,
  onNavigate,
  onOpenSpotlight,
}: LabGlobalSurfacesProps) {
  const params = new URLSearchParams(search);
  const [createOpen, setCreateOpen] = React.useState(params.get("create") === "open");
  const [launcherOpen, setLauncherOpen] = React.useState(["open", "search", "customize"].includes(params.get("atlas") || "") || params.get("spotlight") === "open" || params.get("menu") === "open");
  const [launcherQuery, setLauncherQuery] = React.useState("");
  const [workspaceOpen, setWorkspaceOpen] = React.useState(Boolean(params.get("workspace")));
  const { currentUser, accounts, activeAccount, switchAccount } = useGovernance();
  const { activeWorkspace } = useOperations();
  const server = useServerState();
  const focusMode = pathname.startsWith("/content/") && pathname.includes("/edit");

  React.useEffect(() => {
    const close = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setLauncherOpen(true);
      }
      if (event.key === "Escape") {
        setCreateOpen(false);
        setLauncherOpen(false);
        setWorkspaceOpen(false);
      }
    };
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, []);

  React.useEffect(() => {
    const next = new URLSearchParams(search);
    const atlas = next.get("atlas");
    if (atlas) setLauncherOpen(["open", "search", "customize"].includes(atlas));
    if (next.get("spotlight") === "open" || next.get("menu") === "open") setLauncherOpen(true);
    if (next.get("menu") === "closed") setLauncherOpen(false);
    if (next.get("create") === "open") setCreateOpen(true);
    if (next.get("workspace")) setWorkspaceOpen(true);
  }, [search]);

  const filteredLaunchItems = launchItems.filter((item) => `${item.label} ${item.detail}`.toLowerCase().includes(launcherQuery.toLowerCase()));

  return (
    <>
      <aside className="clicko-lab-rail fixed inset-y-0 left-0 z-[60] flex w-[76px] flex-col border-r border-white/[0.07] bg-[#0b0b0c]/95 px-2 py-3 backdrop-blur-xl">
        <button
          type="button"
          onClick={() => onNavigate("/dashboard")}
          className="clicko-lab-mark mx-auto grid h-11 w-11 place-items-center rounded-2xl bg-white text-xl font-extrabold text-black"
          aria-label="Ir para a Home"
        >
          C
        </button>

        <nav className="mt-7 flex flex-1 flex-col gap-1" aria-label="Navegação principal">
          {destinations.map(({ label, path, icon: Icon }) => {
            const active = isActive(pathname, path);
            return (
              <button
                key={label}
                type="button"
                onClick={() => onNavigate(path)}
                title={label}
                aria-label={label}
                aria-current={active ? "page" : undefined}
                className={`clicko-lab-nav-item relative flex min-h-[52px] flex-col items-center justify-center gap-1 rounded-2xl text-[11px] font-semibold transition ${
                  active
                    ? "bg-white text-black shadow-[0_8px_28px_rgba(255,255,255,.08)]"
                    : "text-white/45 hover:bg-white/[0.055] hover:text-white"
                }`}
              >
                <Icon className="h-[18px] w-[18px]" strokeWidth={active ? 2.4 : 1.8} />
                <span>{label}</span>
              </button>
            );
          })}
        </nav>

        <div className="space-y-1 border-t border-white/[0.07] pt-3">
          <button
            type="button"
            onClick={() => onNavigate("/settings/ai-governance")}
            className="mx-auto grid h-11 w-11 place-items-center rounded-2xl text-white/45 hover:bg-white/[0.055] hover:text-white"
            aria-label="Configurações"
            title="Configurações"
          >
            <Settings2 className="h-[18px] w-[18px]" />
          </button>
          <button
            type="button"
            onClick={() =>
              server.status === "connected" ? void server.refresh() : onNavigate("/login")
            }
            className="mx-auto grid h-11 w-11 place-items-center rounded-2xl border border-white/[0.09] bg-white/[0.035] text-white/70 hover:bg-white/[0.07]"
            aria-label="Conta"
            title={currentUser?.name || "Conta"}
          >
            <CircleUserRound className="h-[19px] w-[19px]" />
          </button>
        </div>
      </aside>

      {!focusMode && (
        <header className="clicko-lab-topbar fixed left-[76px] right-0 top-0 z-50 flex h-[60px] items-center gap-3 border-b border-white/[0.07] bg-[#101011]/88 px-5 backdrop-blur-2xl">
          <button
            type="button"
            onClick={() => setWorkspaceOpen(true)}
            className="min-w-0 text-left"
          >
            <span className="block truncate text-[13px] font-bold text-white">
              {activeWorkspace?.name || "Workspace Clicko"}
            </span>
            <span className="mt-0.5 flex items-center gap-1 text-[11px] text-white/35">
              Social Media Lab <ChevronDown className="h-3 w-3" />
            </span>
          </button>

          <div className="ml-auto flex items-center gap-2">
            <button
              type="button"
              onClick={() => setLauncherOpen(true)}
              className="hidden h-9 w-48 items-center gap-2 rounded-xl border border-white/[0.08] bg-white/[0.035] px-3 text-left text-[12px] text-white/35 transition hover:border-white/[0.15] hover:text-white/65 md:flex"
            >
              <Search className="h-4 w-4" />
              Buscar no workspace
            </button>
            <button
              type="button"
              className="grid h-9 w-9 place-items-center rounded-xl text-white/45 hover:bg-white/[0.05] hover:text-white"
              aria-label="Notificações"
            >
              <Bell className="h-[18px] w-[18px]" />
            </button>
            <div className="relative">
              <button
                type="button"
                onClick={() => setCreateOpen((value) => !value)}
                className="clicko-primary-action inline-flex h-10 items-center gap-2 rounded-xl bg-[#ff6969] px-4 text-[12px] font-extrabold text-[#260707] transition hover:bg-[#ff8585]"
              >
                <Plus className="h-4 w-4" strokeWidth={2.5} />
                Criar
                <ChevronDown className="h-3.5 w-3.5" />
              </button>
              {createOpen && (
                <div className="absolute right-0 top-12 w-[320px] overflow-hidden rounded-2xl border border-white/[0.1] bg-[#19191b] p-2 shadow-2xl shadow-black/70">
                  {[
                    ["Post social", "Começar com um formato", "/content/new?type=post"],
                    ["Visual", "Compor com referências e marca", "/content/draft/edit?mode=visual"],
                    ["Vídeo", "Gerar e editar uma sequência", "/content/draft/edit?mode=video"],
                    ["Projeto", "Organizar uma campanha completa", "/campaigns/new"],
                  ].map(([label, detail, path]) => (
                    <button
                      key={label}
                      type="button"
                      onClick={() => {
                        setCreateOpen(false);
                        onNavigate(path);
                      }}
                      className="flex w-full items-center justify-between rounded-xl px-3 py-3 text-left hover:bg-white/[0.055]"
                    >
                      <span>
                        <strong className="block text-[13px] text-white">{label}</strong>
                        <small className="mt-0.5 block text-[11px] text-white/38">{detail}</small>
                      </span>
                      <Plus className="h-4 w-4 text-[#ff8d68]" />
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </header>
      )}

      {launcherOpen && (
        <div className="fixed inset-0 z-[100] flex items-start justify-center bg-black/72 px-4 pt-[9vh] backdrop-blur-md" role="dialog" aria-modal="true" aria-label="Launcher do workspace" onMouseDown={(event) => { if (event.target === event.currentTarget) setLauncherOpen(false); }}>
          <section className="w-full max-w-3xl overflow-hidden rounded-[24px] border border-white/[0.1] bg-[#18181a] shadow-2xl shadow-black/70">
            <header className="flex items-center gap-3 border-b border-white/[0.08] p-4"><Search className="h-5 w-5 text-[#ff8d68]" /><input autoFocus value={launcherQuery} onChange={(event) => setLauncherQuery(event.target.value)} placeholder="O que você quer fazer?" className="min-w-0 flex-1 bg-transparent text-[15px] text-white outline-none placeholder:text-white/25" /><span className="hidden rounded-lg border border-white/[0.08] px-2 py-1 font-mono text-[10px] text-white/28 sm:block">CTRL K</span><button type="button" onClick={() => setLauncherOpen(false)} className="grid h-8 w-8 place-items-center rounded-lg text-white/35 hover:bg-white/[0.05] hover:text-white" aria-label="Fechar"><X className="h-4 w-4" /></button></header>
            <div className="grid max-h-[66vh] overflow-y-auto p-3 sm:grid-cols-2">{filteredLaunchItems.map(({label,detail,path,icon:Icon}) => <button key={label} type="button" onClick={() => { setLauncherOpen(false); onNavigate(path); }} className="flex min-h-[76px] items-center gap-3 rounded-[16px] p-3 text-left hover:bg-white/[0.05]"><span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-white/[0.05] text-[#ff8d68]"><Icon className="h-4 w-4" /></span><span><strong className="block text-[12px] text-white/75">{label}</strong><small className="mt-1 block text-[11px] text-white/30">{detail}</small></span><ArrowRightIcon /></button>)}</div>
          </section>
        </div>
      )}

      {workspaceOpen && (
        <div className="fixed inset-0 z-[100] grid place-items-center bg-black/72 p-4 backdrop-blur-md" role="dialog" aria-modal="true" aria-label="Trocar workspace" onMouseDown={(event) => { if (event.target === event.currentTarget) setWorkspaceOpen(false); }}>
          <section className="w-full max-w-md rounded-[24px] border border-white/[0.1] bg-[#18181a] p-3 shadow-2xl"><header className="flex items-center justify-between px-2 py-2"><div><h2 className="text-[14px] font-bold text-white">Workspaces</h2><p className="mt-1 text-[11px] text-white/30">Escolha onde criar e publicar.</p></div><button type="button" onClick={() => setWorkspaceOpen(false)} className="grid h-8 w-8 place-items-center text-white/35" aria-label="Fechar"><X className="h-4 w-4" /></button></header><div className="mt-2 space-y-2">{accounts.map((account) => <button key={account.id} type="button" onClick={() => { switchAccount(account.id); setWorkspaceOpen(false); }} className={`flex w-full items-center gap-3 rounded-[16px] border p-3 text-left ${account.id === activeAccount?.id ? "border-[#ff6969]/35 bg-[#ff6969]/[0.07]" : "border-white/[0.07] hover:bg-white/[0.04]"}`}><span className="grid h-10 w-10 place-items-center rounded-xl bg-white/[0.06] text-[13px] font-bold text-white/65">{account.name.slice(0,1)}</span><span><strong className="block text-[12px] text-white/75">{account.name}</strong><small className="mt-1 block text-[10px] text-white/28">{account.type === "company" ? "Workspace de equipe" : "Conta pessoal"}</small></span>{account.id === activeAccount?.id && <Check className="ml-auto h-4 w-4 text-[#ff8d68]" />}</button>)}</div><button type="button" onClick={() => { setWorkspaceOpen(false); onNavigate("/workspaces/new"); }} className="mt-3 flex w-full items-center justify-center gap-2 rounded-[14px] border border-dashed border-white/[0.1] p-3 text-[11px] font-bold text-white/45 hover:text-white"><Plus className="h-4 w-4" /> Novo workspace</button></section>
        </div>
      )}

    </>
  );
}

function ArrowRightIcon() {
  return <span className="ml-auto text-[16px] text-white/18">→</span>;
}
