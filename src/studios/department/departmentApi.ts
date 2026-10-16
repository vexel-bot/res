import { apiFetch } from "../../api";

export type StudioFormat = "image" | "carousel" | "video";
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
}
const base = "/api/v1/studios/v1/projects";
const path = (id: string) => `${base}/${encodeURIComponent(id)}`;
export const departmentApi = {
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
  produce: (project: DepartmentProject) =>
    apiFetch<DepartmentProject>(`${path(project.id)}/produce`, {
      method: "POST",
      body: JSON.stringify({ expectedRevision: project.revision }),
    }),
};
