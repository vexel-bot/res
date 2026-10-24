export const EXPERIENCE_EVENT_NAME = "clicko:experience";

export interface ExperienceTelemetryDetail {
  event: string;
  kind: "view" | "action";
  route: string;
  screenId?: string;
  actionId?: string;
  occurredAt: string;
}

/** Provider-neutral boundary consumed by analytics adapters outside the CX contracts. */
export function emitExperienceTelemetry(
  detail: Omit<ExperienceTelemetryDetail, "occurredAt">,
) {
  if (typeof window === "undefined") return;
  window.dispatchEvent(
    new CustomEvent<ExperienceTelemetryDetail>(EXPERIENCE_EVENT_NAME, {
      detail: { ...detail, occurredAt: new Date().toISOString() },
    }),
  );
}
