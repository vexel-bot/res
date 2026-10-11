import type { StudioDocumentRecord, StudioVideoRenderCreate } from "../api/productApi";

const contextualProviders = [
  "builtin.ffmpeg-contextual-v1", "hyperframes.contextual-v2", "motion-canvas.contextual-v1",
  "remotion.contextual-v1", "remotion.contextual-v2", "alight-motion.contextual-v1",
] as const;

// The generated client still describes the older UGC-only provider union.
// These fields mirror CreateVideoRenderJobRequest in the current backend.
export type VideoStudioRenderRequest = Omit<StudioVideoRenderCreate, "provider"> & {
  provider: StudioVideoRenderCreate["provider"] | typeof contextualProviders[number];
  contextualPlanId?: string;
};

// The persisted plan selects the renderer; the output tab must not switch engines.
export function videoRenderRequest(document: StudioDocumentRecord, planId?: string): VideoStudioRenderRequest {
  const narrative = document.composition.narrative;
  const boundPlan = narrative?.contextualPlanId;
  if (planId !== undefined && planId !== boundPlan) {
    throw new Error("O plano de render não corresponde ao documento atual.");
  }
  const editorial = narrative?.editorialV2 as { renderer?: unknown } | undefined;
  if (editorial && (typeof boundPlan !== "string" || !boundPlan)) {
    throw new Error("A composição precisa de um plano associado antes do render.");
  }
  if (boundPlan !== undefined && (typeof boundPlan !== "string" || !boundPlan)) {
    throw new Error("O plano associado à composição é inválido.");
  }
  const page = document.composition.pages[0];
  if (!page) throw new Error("O documento precisa de uma página antes do render.");
  const contextual = typeof boundPlan === "string";
  const renderer = editorial?.renderer ?? (editorial ? "hyperframes.contextual-v2" : "builtin.ffmpeg-contextual-v1");
  if (contextual && !contextualProviders.some(provider => provider === renderer)) {
    throw new Error("O motor associado à composição não é suportado. Revise o plano.");
  }
  const rate = document.composition.mediaTimeline?.frameRate ?? { numerator: 30, denominator: 1 };
  return {
    workspaceId: document.workspaceId,
    documentId: document.documentId,
    expectedDocumentRevision: document.revision,
    expectedDocumentVersion: document.version,
    pageIds: contextual ? [page.id] : document.composition.pages.map(item => item.id),
    provider: contextual ? renderer as typeof contextualProviders[number] : "builtin.ffmpeg-ugc-v1",
    ...(contextual ? { contextualPlanId: boundPlan } : {}),
    output: {
      schemaVersion: "studio.video-render-spec.v1", format: "mp4",
      width: contextual ? page.width : 1080, height: contextual ? page.height : 1920,
      fps: rate.numerator / rate.denominator,
      videoCodec: "h264", audioCodec: "aac", quality: contextual ? "high" : "draft",
    },
    reducedMotion: false,
  };
}
