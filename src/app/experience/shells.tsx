import React from "react";

import type { ScreenState } from "./contracts";
import type { RouteShell } from "../router/routeRegistry";

export const PRODUCTION_STEPS = [
  "Direção",
  "Roteiro",
  "Materiais",
  "Montagem",
  "Revisão",
  "Entrega",
] as const;

export type ProductionStep = (typeof PRODUCTION_STEPS)[number];

const SHELL_LABELS: Record<RouteShell, string> = {
  global: "Navegação global",
  project: "Contexto do projeto",
  studio: "Área de produção",
  decision: "Área de decisão",
  operation: "Área operacional",
};

const STATE_LABELS: Record<ScreenState, string> = {
  loading: "Carregando",
  empty: "Nada encontrado",
  ready: "Pronto",
  dirty: "Alterações locais",
  saving: "Salvando",
  saved: "Sincronizado",
  "recoverable-error": "Não foi possível concluir",
  "terminal-error": "A operação foi interrompida",
  conflict: "Conflito de edição",
  readonly: "Somente leitura",
  forbidden: "Acesso indisponível",
  offline: "Você está offline",
  stale: "Os dados podem estar desatualizados",
  "job-queued": "Operação na fila",
  "job-running": "Operação em andamento",
  "job-cancelling": "Cancelamento solicitado",
  "job-cancelled": "Operação cancelada",
};

export interface ExperienceShellProps {
  shell: RouteShell;
  routeId: string;
  screenId?: string;
  state?: ScreenState;
  children: React.ReactNode;
}

/**
 * Strangler boundary for canonical route families. It does not replace the
 * approved visual shell; it gives every route one typed shell/state owner and
 * a stable hook for responsive migration, telemetry and rollback.
 */
export function ExperienceShell({
  shell,
  routeId,
  screenId,
  state = "ready",
  children,
}: ExperienceShellProps) {
  return (
    <section
      className={`cx-experience-shell cx-experience-shell--${shell}`}
      aria-label={SHELL_LABELS[shell]}
      data-route-id={routeId}
      data-screen-id={screenId}
      data-shell={shell}
      data-screen-state={state}
      data-scroll-owner="cx-main"
    >
      {children}
    </section>
  );
}

export interface HonestStateProps {
  state: Exclude<ScreenState, "ready">;
  title?: string;
  detail: string;
  preserved?: string;
  impact?: string;
  actionLabel?: string;
  actionId?: string;
  onAction?: () => void;
  disabledReason?: string;
  compact?: boolean;
}

export function HonestState({
  state,
  title = STATE_LABELS[state],
  detail,
  preserved,
  impact,
  actionLabel,
  actionId,
  onAction,
  disabledReason,
  compact = false,
}: HonestStateProps) {
  const urgent = [
    "recoverable-error",
    "terminal-error",
    "conflict",
    "forbidden",
  ].includes(state);
  const progressing = [
    "loading",
    "saving",
    "job-queued",
    "job-running",
    "job-cancelling",
  ].includes(state);

  return (
    <section
      className={`cx-honest-state cx-honest-state--${state} ${compact ? "is-compact" : ""}`}
      role={urgent ? "alert" : "status"}
      aria-live={urgent ? "assertive" : "polite"}
      aria-busy={progressing || undefined}
      data-state={state}
    >
      <span className="cx-honest-state__signal" aria-hidden="true" />
      <div className="cx-honest-state__copy">
        <strong>{title}</strong>
        <p>{detail}</p>
        {preserved && <small>Preservado: {preserved}</small>}
        {impact && <small>Impacto: {impact}</small>}
      </div>
      {actionLabel && onAction && (
        <button type="button" data-action-id={actionId} onClick={onAction}>
          {actionLabel}
        </button>
      )}
      {actionLabel && !onAction && disabledReason && (
        <button type="button" disabled aria-describedby={`${state}-reason`}>
          {actionLabel}
        </button>
      )}
      {actionLabel && !onAction && disabledReason && (
        <small id={`${state}-reason`} className="cx-honest-state__reason">
          {disabledReason}
        </small>
      )}
    </section>
  );
}

export interface ProductionRailProps {
  currentStep: ProductionStep;
  documentLabel: string;
  contextLabel: string;
  onBack: () => void;
  backActionId: string;
  onSaveAndExit?: () => void;
  saveAndExitActionId?: string;
  saveState?: Extract<ScreenState, "dirty" | "saving" | "saved" | "recoverable-error" | "conflict" | "offline">;
}

export function ProductionRail({
  currentStep,
  documentLabel,
  contextLabel,
  onBack,
  backActionId,
  onSaveAndExit,
  saveAndExitActionId,
  saveState = "saved",
}: ProductionRailProps) {
  return (
    <aside className="cx-shared-production-rail" aria-label="Etapas de produção">
      <button
        type="button"
        className="cx-shared-production-rail__back"
        data-action-id={backActionId}
        onClick={onBack}
      >
        Voltar ao projeto
      </button>
      <div>
        <strong>{documentLabel}</strong>
        <small>{contextLabel}</small>
      </div>
      <ol>
        {PRODUCTION_STEPS.map((step, index) => {
          const activeIndex = PRODUCTION_STEPS.indexOf(currentStep);
          const status = index < activeIndex ? "complete" : index === activeIndex ? "current" : "pending";
          return (
            <li key={step} data-step-state={status} aria-current={status === "current" ? "step" : undefined}>
              <span>{index + 1}</span>
              {step}
            </li>
          );
        })}
      </ol>
      <footer>
        <small data-save-state={saveState}>{STATE_LABELS[saveState]}</small>
        {onSaveAndExit && (
          <button
            type="button"
            data-action-id={saveAndExitActionId}
            onClick={onSaveAndExit}
          >
            Salvar e sair
          </button>
        )}
      </footer>
    </aside>
  );
}
