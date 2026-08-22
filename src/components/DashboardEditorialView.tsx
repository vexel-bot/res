import React from "react";
import {
  ArrowRight,
  BarChart3,
  Bot,
  CalendarDays,
  ChartNoAxesCombined,
  CheckCircle2,
  ChevronDown,
  Clock3,
  FileText,
  Instagram,
  Lightbulb,
  LoaderCircle,
  Megaphone,
  Plus,
  RefreshCcw,
  Send,
  Sparkles,
} from "lucide-react";
import type {
  AIActionSuggestion,
  NavigationTab,
  Post,
  Workspace,
} from "../types";
import { useOperations } from "../context/OperationsContext";
import { useGovernance } from "../context/GovernanceContext";
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

export const DashboardView: React.FC<DashboardViewProps> = ({
  activeWorkspace,
  onNavigate,
  onOpenCampaignWizard,
  onNewPost,
}) => {
  const operations = useOperations();
  const productData = useProductData();
  const posts =
    productData.status === "ready" && productData.snapshot
      ? (productData.snapshot.posts as unknown as Post[])
      : operations.posts;
  const { environmentMode, currentUser } = useGovernance();
  const { sendMessage, loading: aiLoading } = useAIChat();
  const [command, setCommand] = React.useState("");
  const [activeFlowStep, setActiveFlowStep] = React.useState("Ideias");
  const isPersonal = environmentMode === "personal";
  const accountTypeLabel = isPersonal ? "Conta pessoal" : "Workspace";
  const published = posts.filter((post) => post.status === "published").length;
  const scheduled = posts.filter((post) => post.status === "scheduled").length;
  const pending = posts.filter(
    (post) => post.status === "pending_approval" || post.status === "in_review",
  ).length;
  const dataSource =
    productData.status === "ready"
      ? "Backend conectado"
      : "Dados locais de demonstração";
  const observedMetrics =
    productData.snapshot?.analytics.metrics.filter(
      (metric) => metric.status === "available",
    ) || [];
  const approvalPosts = posts.filter((post) =>
    ["in_review", "pending_approval", "changes_requested"].includes(
      post.status,
    ),
  );
  const today = React.useMemo(() => {
    const value = new Date();
    value.setHours(0, 0, 0, 0);
    return value;
  }, []);
  const weekDays = React.useMemo(
    () =>
      Array.from({ length: 7 }, (_, index) => {
        const date = new Date(today);
        date.setDate(today.getDate() + index);
        return {
          date,
          day: new Intl.DateTimeFormat("pt-BR", { weekday: "short" })
            .format(date)
            .replace(".", "")
            .toUpperCase(),
          label: new Intl.DateTimeFormat("pt-BR", {
            day: "2-digit",
            month: "short",
          })
            .format(date)
            .replace(".", "")
            .toUpperCase(),
        };
      }),
    [today],
  );
  const agendaPosts = posts.flatMap((post) => {
    if (!post.scheduledAt) return [];
    const date = new Date(post.scheduledAt);
    const day = Math.floor((date.getTime() - today.getTime()) / 86400000) + 1;
    if (day < 1 || day > 7) return [];
    const hour = date.getHours();
    return [{ post, day, row: hour < 11 ? 1 : hour < 15 ? 2 : 3 }];
  });
  const operationalFlow = [
    ["Ideias", posts.filter((post) => post.status === "draft").length],
    [
      "Produção",
      posts.filter((post) => post.status === "changes_requested").length,
    ],
    ["Revisão", posts.filter((post) => post.status === "in_review").length],
    [
      "Aprovação",
      posts.filter((post) => post.status === "pending_approval").length,
    ],
    [
      "Agendado",
      posts.filter(
        (post) => post.status === "approved" || post.status === "scheduled",
      ).length,
    ],
  ] as const;
  const metrics = isPersonal
    ? [
        ["Conteúdos", String(posts.length), "+24%", FileText],
        ["Publicados", String(published), "concluídos", CheckCircle2],
        ["Agendados", String(scheduled), "na agenda", CalendarDays],
        [
          "Métricas reais",
          String(observedMetrics.length),
          observedMetrics.length ? "conectadas" : "não conectadas",
          ChartNoAxesCombined,
        ],
      ]
    : [
        ["Conteúdos", String(posts.length), "no fluxo", FileText],
        ["Agendados", String(scheduled), "na agenda", CalendarDays],
        [
          "Em aprovação",
          String(pending),
          pending === 1 ? "1 pendência" : `${pending} pendências`,
          Clock3,
        ],
        [
          "Métricas reais",
          String(observedMetrics.length),
          observedMetrics.length ? "conectadas" : "não conectadas",
          ChartNoAxesCombined,
        ],
      ];

  const nextMovement =
    !isPersonal && pending > 0
      ? {
          title:
            pending === 1
              ? "Uma aprovação precisa da sua decisão."
              : `${pending} aprovações precisam da sua decisão.`,
          description:
            "A fila já está organizada para você revisar o contexto e liberar o próximo passo.",
          cta: "Revisar aprovações",
          action: () => onNavigate("approvals"),
          urgent: true,
        }
      : scheduled > 0
        ? {
            title:
              scheduled === 1
                ? "Uma publicação está pronta na agenda."
                : `${scheduled} publicações estão prontas na agenda.`,
            description:
              "Revise a cadência e os horários antes da próxima janela de publicação.",
            cta: "Abrir agenda",
            action: () => onNavigate("calendar"),
            urgent: false,
          }
        : {
            title: "Sua operação está livre para o próximo conteúdo.",
            description:
              "Comece por uma instrução para a IA ou abra o Studio com o contexto atual.",
            cta: "Criar conteúdo",
            action: onNewPost,
            urgent: false,
          };

  const quickActions = [
    {
      label: "Criar conteúdo",
      description: "Abrir o Studio",
      icon: Plus,
      action: onNewPost,
    },
    {
      label: "Abrir projetos",
      description: "Campanhas e Creative Lab",
      icon: Megaphone,
      action: () => onNavigate("strategy"),
    },
    {
      label: "Gerar ideias",
      description: "Usar contexto da IA",
      icon: Lightbulb,
      action: onOpenCampaignWizard,
    },
    {
      label: "Repurpose",
      description: "Reaproveitar material",
      icon: RefreshCcw,
      action: () => onNavigate("library"),
    },
  ];

  const submitCommand = (event: React.FormEvent) => {
    event.preventDefault();
    const cleanCommand = command.trim();
    if (!cleanCommand || aiLoading) return;
    void sendMessage(cleanCommand, "dashboard");
    setCommand("");
    onOpenCampaignWizard();
  };

  return (
    <div className="clicko-dashboard-editorial min-h-screen px-7 pb-10 pt-7 2xl:px-10 2xl:pt-9">
      <header className="clicko-dashboard-hero flex flex-col gap-4 border-b border-white/[0.07] pb-5 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-[18px] font-semibold tracking-[-0.035em] text-white">
            Dashboard operacional
          </h1>
          <p className="mt-1 text-[9px] text-[#a49797]">
            {new Intl.DateTimeFormat("pt-BR", {
              weekday: "long",
              day: "2-digit",
              month: "long",
            }).format(new Date())}{" "}
            · {activeWorkspace?.name || "Workspace ativo"}
          </p>
        </div>
        <div className="clicko-account-identity flex flex-wrap items-center gap-3 text-[8px] font-medium uppercase tracking-[0.14em] text-[#8d8181]">
          <span className="flex items-center gap-2 text-[#ffb5b5]">
            <span className="h-1.5 w-1.5 rounded-full bg-[#ffb5b5]" />
            {accountTypeLabel}
          </span>
          <span>{currentUser?.name || "Operação local"}</span>
          <span>{dataSource}</span>
        </div>
      </header>

      <section
        className="clicko-dashboard-command"
        aria-labelledby="dashboard-command-title"
      >
        <div className="clicko-command-heading">
          <span className="clicko-home-overline text-[9px] font-medium uppercase tracking-[0.2em] text-[#ff5c5c]">
            Comando operacional
          </span>
          <h2
            id="dashboard-command-title"
            className="clicko-home-section-title mt-1.5 text-[20px] font-medium text-white"
          >
            O que vamos fazer hoje?
          </h2>
        </div>
        <form onSubmit={submitCommand} className="clicko-ai-command-field">
          <span className="clicko-ai-command-icon" aria-hidden="true">
            <Bot className="h-4 w-4" />
          </span>
          <label htmlFor="dashboard-ai-command" className="sr-only">
            Instrução para a inteligência do Clicko
          </label>
          <input
            id="dashboard-ai-command"
            value={command}
            onChange={(event) => setCommand(event.target.value)}
            placeholder="Descreva um objetivo, conteúdo ou campanha…"
            autoComplete="off"
          />
          <button
            type="submit"
            disabled={!command.trim() || aiLoading}
            aria-label="Enviar instrução para a IA"
          >
            {aiLoading ? (
              <LoaderCircle className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </button>
        </form>
        <div className="clicko-quick-actions" aria-label="Ações rápidas">
          {quickActions.map(({ label, description, icon: Icon, action }) => (
            <button
              key={label}
              type="button"
              onClick={action}
              className="clicko-quick-action clicko-interactive-surface"
            >
              <span className="clicko-quick-action-icon">
                <Icon className="h-3.5 w-3.5" />
              </span>
              <span>
                <strong>{label}</strong>
                <small>{description}</small>
              </span>
              <ArrowRight className="ml-auto h-3 w-3" />
            </button>
          ))}
        </div>
      </section>

      <section className="clicko-dashboard-metrics grid border-b border-white/[0.07] sm:grid-cols-2 xl:grid-cols-4">
        {metrics.map(([label, value, detail, Icon], index) => {
          const MetricIcon = Icon as React.ComponentType<{
            className?: string;
          }>;
          return (
            <article
              key={String(label)}
              className={`clicko-metric-cell relative py-7 sm:px-6 ${index === 0 ? "sm:pl-0" : ""} ${index > 0 ? "sm:border-l sm:border-white/[0.06]" : ""}`}
            >
              <div className="clicko-metric-label flex items-center gap-2 text-[10px] font-medium uppercase tracking-[0.13em] text-[#6e7980]">
                <MetricIcon className="h-3.5 w-3.5" />
                {String(label)}
              </div>
              <div className="mt-3 flex items-end justify-between gap-4">
                <strong className="text-[clamp(28px,3vw,42px)] font-medium leading-none tracking-[-0.04em] text-white">
                  {String(value)}
                </strong>
                <span className="clicko-metric-detail pb-1 text-[10px] font-semibold text-[#ff5c5c]">
                  {String(detail)}
                </span>
              </div>
            </article>
          );
        })}
      </section>

      <div className="clicko-dashboard-body grid gap-0 xl:grid-cols-[minmax(0,1fr)_320px] 2xl:grid-cols-[minmax(0,1fr)_350px]">
        <section className="clicko-dashboard-calendar min-w-0 py-8 xl:pr-8">
          <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
            <div>
              <span className="clicko-home-overline text-[9px] font-medium uppercase tracking-[0.2em] text-[#ff5c5c]">
                Agenda editorial
              </span>
              <h2 className="clicko-home-section-title mt-1.5 text-[20px] font-medium text-white">
                Próximas publicações
              </h2>
            </div>
            <div className="flex items-center gap-2">
              <button className="clicko-home-action-text h-8 rounded-md border border-white/[0.07] px-3 text-[10px] text-[#8a959b]">
                Semana <ChevronDown className="ml-2 inline h-3 w-3" />
              </button>
              <button
                type="button"
                onClick={onNewPost}
                className="clicko-home-action-text h-8 rounded-md border border-white/[0.07] px-3 text-[10px] text-white hover:bg-white/[0.04]"
              >
                <Plus className="mr-1.5 inline h-3 w-3 text-[#ff5c5c]" />
                Adicionar
              </button>
            </div>
          </div>

          <div className="custom-scrollbar overflow-x-auto">
            <div className="min-w-[760px]">
              <div className="grid grid-cols-[42px_repeat(7,minmax(0,1fr))] border-y border-white/[0.06]">
                <div />
                {weekDays.map(({ day, label }, index) => (
                  <div
                    key={label}
                    className={`clicko-timeline-day py-3 text-center ${index === 0 ? "clicko-timeline-day-current bg-[#ff5c5c]/[0.06]" : ""}`}
                  >
                    <span
                      className={`clicko-calendar-day-label block text-[10px] font-semibold ${index === 0 ? "text-[#ff5c5c]" : "text-[#a7b0b5]"}`}
                    >
                      {day}
                    </span>
                    <span className="clicko-calendar-date mt-0.5 block text-[9px] text-[#59656c]">
                      {label}
                    </span>
                  </div>
                ))}
              </div>
              <div className="relative grid grid-cols-[42px_repeat(7,minmax(0,1fr))] grid-rows-3">
                {[8, 12, 16].map((time, row) => (
                  <div
                    key={time}
                    style={{ gridColumn: 1, gridRow: row + 1 }}
                    className="clicko-calendar-time border-b border-white/[0.045] pr-2 pt-3 text-right text-[8px] text-[#4f5b62]"
                  >
                    {String(time).padStart(2, "0")}:00
                  </div>
                ))}
                {Array.from({ length: 21 }).map((_, index) => (
                  <div
                    key={index}
                    style={{
                      gridColumn: (index % 7) + 2,
                      gridRow: Math.floor(index / 7) + 1,
                    }}
                    className={`h-[82px] border-b border-l border-white/[0.045] ${index % 7 === 3 ? "bg-[#ff5c5c]/[0.018]" : ""}`}
                  />
                ))}
                {agendaPosts.map(({ post, day, row }) => (
                  <button
                    key={post.id}
                    type="button"
                    onClick={() => onNavigate("calendar")}
                    style={{ gridColumn: day + 1, gridRow: row }}
                    className="clicko-interactive-surface group z-10 mx-1 my-2 flex min-w-0 items-center gap-2 rounded-md border border-white/[0.07] bg-[#11161a] px-2 py-1.5 text-left hover:border-[#ff5c5c]/35 hover:bg-[#151c20]"
                  >
                    <span className="grid h-8 w-8 shrink-0 place-items-center rounded bg-[var(--clicko-creative)]/10 text-[var(--clicko-creative)]">
                      <FileText className="h-3.5 w-3.5" />
                    </span>
                    <span className="min-w-0 flex-1">
                      <strong className="clicko-schedule-title block truncate text-[9px] font-medium text-white">
                        {post.title}
                      </strong>
                      <span className="clicko-schedule-subtitle block truncate text-[8px] text-[#68747b]">
                        {post.format} · {post.status}
                      </span>
                    </span>
                    <Instagram className="h-3 w-3 shrink-0 text-[#a66b85]" />
                  </button>
                ))}
                {agendaPosts.length === 0 && (
                  <div
                    style={{ gridColumn: "2 / span 7", gridRow: "2" }}
                    className="z-10 mx-4 my-3 grid place-items-center rounded-lg border border-dashed border-white/[0.08] bg-black/20 px-4 text-center text-[10px] text-white/35"
                  >
                    Nenhuma publicação programada nos próximos 7 dias. A agenda
                    não será preenchida com dados fictícios.
                  </div>
                )}
              </div>
            </div>
          </div>
        </section>

        <aside className="clicko-dashboard-side border-t border-white/[0.07] py-8 xl:border-l xl:border-t-0 xl:pl-8">
          <section>
            <div className="flex items-center justify-between">
              <div>
                <span className="clicko-home-overline text-[9px] uppercase tracking-[0.18em] text-[#69757c]">
                  Agora
                </span>
                <h2 className="clicko-home-side-title mt-1 text-[15px] font-medium text-white">
                  {isPersonal ? "Operação pessoal" : "Fila de aprovação"}
                </h2>
              </div>
              {!isPersonal && (
                <button
                  type="button"
                  onClick={() => onNavigate("approvals")}
                  className="clicko-home-action-text text-[9px] font-medium text-[#ff5c5c]"
                >
                  Ver tudo
                </button>
              )}
            </div>
            <div className="mt-5 divide-y divide-white/[0.055]">
              {approvalPosts.slice(0, isPersonal ? 2 : 3).map((post) => (
                <button
                  key={post.id}
                  type="button"
                  onClick={() =>
                    onNavigate(isPersonal ? "calendar" : "approvals")
                  }
                  className="clicko-interactive-surface group flex w-full items-center gap-3 rounded-md border border-transparent px-2 py-3 text-left"
                >
                  <span className="grid h-9 w-9 shrink-0 place-items-center rounded-md border border-white/[0.07] bg-white/[0.03] text-[var(--clicko-creative)]">
                    <FileText className="h-4 w-4" />
                  </span>
                  <span className="min-w-0 flex-1">
                    <strong className="clicko-side-item-title block truncate text-[10px] font-medium text-[#d6dcdf]">
                      {post.title}
                    </strong>
                    <span className="clicko-side-item-meta mt-0.5 block truncate text-[8px] text-[#5f6b72]">
                      {post.author} · {post.status}
                    </span>
                  </span>
                  <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
                </button>
              ))}
              {approvalPosts.length === 0 && (
                <div className="rounded-lg border border-dashed border-white/[0.07] px-3 py-5 text-center text-[10px] text-white/35">
                  Nenhum conteúdo aguarda decisão.
                </div>
              )}
            </div>
          </section>

          <section className="mt-8 border-t border-white/[0.07] pt-7">
            <div className="flex items-center justify-between">
              <div>
                <span className="clicko-home-overline text-[9px] uppercase tracking-[0.18em] text-[#69757c]">
                  Últimos 7 dias
                </span>
                <h2 className="clicko-home-side-title mt-1 text-[15px] font-medium text-white">
                  Desempenho
                </h2>
              </div>
              <button
                type="button"
                onClick={() => onNavigate("analytics")}
                className="grid h-8 w-8 place-items-center rounded-full border border-white/[0.07] text-[#ff5c5c]"
              >
                <ArrowRight className="h-3.5 w-3.5" />
              </button>
            </div>
            <div className="mt-5 space-y-3.5">
              {observedMetrics.slice(0, 3).map((metric) => (
                <div
                  key={metric.key}
                  className="clicko-analytics-row grid grid-cols-[1fr_auto] items-center gap-3 text-[10px]"
                >
                  <span className="text-[#69757c]">{metric.label}</span>
                  <strong className="font-medium text-white">
                    {metric.value ?? "—"}
                    {metric.unit}
                  </strong>
                </div>
              ))}
            </div>
            {observedMetrics.length === 0 && (
              <div className="mt-5 rounded-lg border border-dashed border-white/[0.07] px-3 py-5 text-center text-[10px] leading-5 text-white/35">
                Métricas ainda não sincronizadas. O dashboard não inventa
                alcance, impressões ou cliques.
              </div>
            )}
          </section>
        </aside>
      </div>

      <section
        className={`clicko-dashboard-insight clicko-next-movement grid border-y border-white/[0.07] lg:grid-cols-[1.2fr_1fr] ${nextMovement.urgent ? "is-urgent" : ""}`}
      >
        <div className="py-7 lg:pr-8">
          <div className="clicko-home-overline flex items-center gap-2 text-[9px] font-medium uppercase tracking-[0.18em] text-[#ff5c5c]">
            <Sparkles className="h-3.5 w-3.5" />
            Próximo movimento
          </div>
          <p className="clicko-next-movement-copy mt-3 max-w-2xl text-[15px] leading-6 text-[#bbc3c7]">
            <strong className="font-medium text-white">
              {nextMovement.title}
            </strong>{" "}
            {nextMovement.description}
          </p>
          <button
            type="button"
            onClick={nextMovement.action}
            className="clicko-home-action-text mt-4 text-[10px] font-semibold text-[#ff5c5c]"
          >
            {nextMovement.cta} <ArrowRight className="ml-1.5 inline h-3 w-3" />
          </button>
        </div>
        <div className="border-t border-white/[0.07] py-7 lg:border-l lg:border-t-0 lg:pl-8">
          <div className="clicko-home-overline flex items-center gap-2 text-[9px] font-medium uppercase tracking-[0.18em] text-[#69757c]">
            <BarChart3 className="h-3.5 w-3.5" />
            Ritmo da operação
          </div>
          <div className="mt-4 grid grid-cols-3 gap-5">
            <div>
              <strong className="clicko-live-value block text-[20px] font-medium text-white">
                {published}
              </strong>
              <span className="clicko-rhythm-label text-[8px] text-[#647078]">
                publicados
              </span>
            </div>
            <div>
              <strong className="clicko-live-value block text-[20px] font-medium text-white">
                {scheduled}
              </strong>
              <span className="clicko-rhythm-label text-[8px] text-[#647078]">
                agendados
              </span>
            </div>
            <div>
              <strong className="clicko-live-value block text-[20px] font-medium text-white">
                {pending}
              </strong>
              <span className="clicko-rhythm-label text-[8px] text-[#647078]">
                em decisão
              </span>
            </div>
          </div>
        </div>
      </section>

      <section className="clicko-dashboard-flow py-8">
        <div className="mb-5 flex items-center justify-between gap-4">
          <div>
            <span className="clicko-home-overline text-[9px] uppercase tracking-[0.18em] text-[#69757c]">
              Fluxo operacional
            </span>
            <h2 className="clicko-home-side-title mt-1 text-[15px] font-medium text-white">
              Da ideia ao agendamento
            </h2>
          </div>
          <span className="clicko-flow-summary text-right text-[9px] text-[#59656c]">
            {posts.length} conteúdos no sistema
          </span>
        </div>
        <div className="clicko-operational-flow custom-scrollbar flex overflow-x-auto border-y border-white/[0.055]">
          {operationalFlow.map(([step, count], index) => (
            <button
              key={step}
              type="button"
              aria-pressed={activeFlowStep === step}
              onClick={() => setActiveFlowStep(step)}
              className="clicko-flow-step clicko-interactive-surface group flex min-w-[170px] flex-1 items-center gap-3 border border-transparent border-r-white/[0.055] px-4 py-4 text-left last:border-r-transparent hover:bg-white/[0.02]"
            >
              <span className="clicko-flow-index text-[9px] text-[#4f5b62]">
                0{index + 1}
              </span>
              <span className="min-w-0">
                <strong className="clicko-flow-title block text-[10px] font-medium text-[#929ca1] group-hover:text-white">
                  {step}
                </strong>
                <small className="clicko-flow-meta mt-0.5 block text-[8px] text-[#59656c]">
                  {count} {count === 1 ? "conteúdo" : "conteúdos"}
                </small>
              </span>
              {index < operationalFlow.length - 1 && (
                <ArrowRight className="ml-auto h-3 w-3 text-[#3f494f]" />
              )}
            </button>
          ))}
        </div>
      </section>
    </div>
  );
};
