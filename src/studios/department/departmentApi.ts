import { apiFetch } from "../../api";

export type StudioFormat = "image" | "carousel" | "video";
export type PresentationLayout = "sequential" | "picture_in_picture";
export interface Direction {
  id: "guide" | "demonstrate";
  title: string;
  rationale: string;
  opening: string;
  beats: string[];
  cta: string;
  basis: string;
  knowledgeRefs: string[];
}
export interface ProjectInput {
  workspaceId: string;
  requestKey: string;
  title: string;
  objective: string;
  audience: string;
  tone: string;
  evidence: string;
  front: "content" | "ads";
  intent: "education" | "authority" | "offer";
  format: StudioFormat;
  campaignId?: string;
  postId?: string;
  sourceAssetId?: string;
  identityVersionId?: string;
  voiceVersionId?: string;
}
export interface DepartmentProject extends Omit<ProjectInput, "requestKey"> {
  id: string;
  revision: number;
  brandName: string;
  directions: Direction[];
  directionId: Direction["id"] | null;
  documentId: string | null;
  jobId: string | null;
  status: "direction" | "producing" | "production_failed" | "delivery";
  planningBasis: string;
  updatedAt: string;
  appearanceSelection?: { jobId: string; assetId: string } | null;
  montagePlan?: { mode?: string } | null;
  casting?: {
    identity?: { id: string; version: number; consentGrantId: string | null };
    voice?: { id: string; version: number; consentGrantId: string | null };
  };
}
export interface NarrationState {
  project: DepartmentProject;
  text: string;
  generatedText?: string | null;
  requestKey: string | null;
  canGenerate: boolean;
  blocker: string | null;
  assetId: string | null;
  job: { id: string; status: string; progress: number; errorCode: string | null } | null;
}
export interface NarrationInput { expectedRevision: number; requestKey: string; text: string }
export interface AvatarState extends Omit<NarrationState, 'text' | 'generatedText'> { performanceDirection?: string | null }
export interface AvatarPlan {
  operation: 'generate_avatar'; expectedRevision: number; documentId: string; durationSeconds: number;
  planDigestSha256: string; performanceDirection: string;
}
export interface AppearancePlan {
  projectRevision: number;
  planDigestSha256: string;
  request: { direction: string; seed: number };
}
export interface AppearanceJob {
  id: string;
  status: string;
  progress: number;
  idempotencyKey: string;
  errorCode: string | null;
  result: { assetId?: string } | null;
}
export interface AppearanceState {
  job: AppearanceJob | null;
  selection: { jobId: string; assetId: string } | null;
  availability: { available: boolean; reason: string | null };
}
const base = "/api/v1/studios/v1/projects";
const path = (id: string) => `${base}/${encodeURIComponent(id)}`;
export const departmentApi = {
  appearance: (id: string, signal?: AbortSignal) => apiFetch<AppearanceState>(`${path(id)}/appearance`, { signal }),
  planAppearance: (id: string, expectedRevision: number, direction: string) => apiFetch<AppearancePlan>(`${path(id)}/appearance/plan`, {
    method: 'POST', body: JSON.stringify({ expectedRevision, direction, seed: 0 }),
  }),
  generateAppearance: (id: string, plan: AppearancePlan, key: string) => apiFetch<AppearanceJob>(`${path(id)}/appearance`, {
    method: 'POST', headers: { 'Idempotency-Key': key }, body: JSON.stringify({ operation: 'generate_image',
      expectedRevision: plan.projectRevision, direction: plan.request.direction, seed: plan.request.seed, planDigestSha256: plan.planDigestSha256 }),
  }),
  selectAppearance: (id: string, expectedRevision: number, jobId: string) => apiFetch<DepartmentProject>(`${path(id)}/appearance/select`, {
    method: 'POST', body: JSON.stringify({ expectedRevision, jobId }),
  }),
  avatar: (id: string, signal?: AbortSignal) => apiFetch<AvatarState>(`${path(id)}/avatar`, { signal }),
  planAvatar: (id: string, performanceDirection: string) => apiFetch<AvatarPlan>(`${path(id)}/avatar/plan`, {
    method: 'POST', body: JSON.stringify({ performanceDirection }),
  }),
  generateAvatar: (id: string, plan: AvatarPlan, key: string) => apiFetch<{ id: string }>(`${path(id)}/avatar`, {
    method: 'POST', headers: { 'Idempotency-Key': key },
    body: JSON.stringify({ operation: plan.operation, expectedRevision: plan.expectedRevision,
      documentId: plan.documentId, durationSeconds: plan.durationSeconds, planDigestSha256: plan.planDigestSha256,
      performanceDirection: plan.performanceDirection }),
  }),
  cancelAvatar: (id: string) => apiFetch<{ id: string }>(`${path(id)}/avatar/cancel`, { method: 'POST' }),
  reconcileAvatar: (jobId: string, signal?: AbortSignal) => apiFetch<{ id: string }>(`/api/v1/studios/v1/jobs/${encodeURIComponent(jobId)}`, { signal }),
  saveNarration: (id: string, input: Omit<NarrationInput, "requestKey">) => apiFetch<NarrationState>(`${path(id)}/narration`, {
    method: "PATCH", body: JSON.stringify(input),
  }),
  narration: (id: string, signal?: AbortSignal) => apiFetch<NarrationState>(`${path(id)}/narration`, { signal }),
  narrate: (id: string, input: NarrationInput) => apiFetch<NarrationState>(`${path(id)}/narration`, {
    method: "POST", body: JSON.stringify(input),
  }),
  cancelNarration: (id: string) => apiFetch<NarrationState>(`${path(id)}/narration/cancel`, { method: "POST" }),
  list: (workspace: string, signal?: AbortSignal) =>
    apiFetch<DepartmentProject[]>(
      `${base}?workspace_id=${encodeURIComponent(workspace)}`,
      { signal },
    ),
  get: (id: string) => apiFetch<DepartmentProject>(path(id)),
  create: (input: ProjectInput) =>
    apiFetch<DepartmentProject>(base, {
      method: "POST",
      body: JSON.stringify(input),
    }),
  choose: (project: DepartmentProject, directionId: Direction["id"]) =>
    apiFetch<DepartmentProject>(path(project.id), {
      method: "PATCH",
      body: JSON.stringify({ expectedRevision: project.revision, directionId }),
    }),
  produce: (project: DepartmentProject, presentationLayout: PresentationLayout = 'sequential') =>
    apiFetch<DepartmentProject>(`${path(project.id)}/produce`, {
      method: "POST",
      body: JSON.stringify({ expectedRevision: project.revision, presentationLayout }),
    }),
};
