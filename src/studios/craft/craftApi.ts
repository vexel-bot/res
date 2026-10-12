import { apiFetch, authToken, APIError } from "../../api";
import type { AssetRecord, StudioDocumentRecord, StudioGenerationJobRecord } from "../../api/productApi";

export type CraftEngine = "photocraft" | "filmcraft" | "effectcraft";
export interface CraftInputSchema {
  type?: string | string[];
  title?: string;
  description?: string;
  enum?: unknown[];
  default?: unknown;
  minimum?: number;
  maximum?: number;
  minItems?: number;
  maxItems?: number;
  minLength?: number;
  maxLength?: number;
  format?: string;
  properties?: Record<string, CraftInputSchema>;
  required?: string[];
  items?: CraftInputSchema;
}
export interface CraftCapability {
  id: string;
  label: string;
  inputSchema: CraftInputSchema;
}
export interface CraftEngineDescriptor {
  engine: CraftEngine;
  available: boolean;
  buildId: string;
  upstreamRevision: string;
  formatVersion: string;
  commands: CraftCapability[];
  formats: string[];
  reason?: string;
}
export interface NativeEditorStateV1 {
  schemaVersion: "studio.native-editor-state.v1";
  engine: CraftEngine;
  formatVersion: string;
  buildId: string;
  upstreamRevision: string;
  projectAssetId: string;
  checksumSha256: string;
  sizeBytes: number;
  assetManifest: Array<{ assetId: string; path: string; checksumSha256: string; mediaType: string }>;
  fontManifest: Array<{ assetId: string; path: string; checksumSha256: string; mediaType: string }>;
  dependencies: Array<{ engine: CraftEngine; projectAssetId: string; checksumSha256: string; buildId: string }>;
  migrationWarnings: string[];
  legacyArchiveAssetId?: string;
  pageProjects?: Array<{ pageId: string; title: string; width: number; height: number; projectAssetId: string; checksumSha256: string; sizeBytes: number }>;
}
export type CraftDocument = StudioDocumentRecord & { nativeEditorState?: NativeEditorStateV1 | null };
export interface CraftLayer {
  id: string;
  name?: string;
  kind?: string;
  properties?: Record<string, unknown>;
  [key: string]: unknown;
}
export interface CraftInspection {
  schemaVersion: "studio.craft-inspection.v1";
  documentId: string;
  revision: number;
  engine: CraftEngine;
  nativeEditorState: NativeEditorStateV1;
  project: {
    width?: number;
    height?: number;
    durationMs?: number;
    fps?: number;
    layers?: CraftLayer[];
    timeline?: Array<Record<string, unknown>>;
    warnings?: string[];
    [key: string]: unknown;
  };
  capabilities: CraftEngineDescriptor | CraftCapability[];
  migrationWarnings?: string[];
  pages?: Array<{ id: string; title: string; width: number; height: number; projectAssetId: string; checksumSha256: string; sizeBytes: number }>;
  activePageId?: string;
}
export interface CraftCommand { id: string; params: Record<string, unknown> }
export interface CraftReceipt {
  document: CraftDocument;
  inspection: CraftInspection;
  receiptId: string;
  aiTrace?: Record<string, unknown>;
}

const base = "/api/v1/studios/v1";
const path = (id: string) => `${base}/documents/${encodeURIComponent(id)}`;
function json(body: unknown, key?: string): RequestInit {
  return { method: "POST", body: JSON.stringify(body), headers: key ? { "Idempotency-Key": key } : undefined };
}

/** Binary requests must not inherit the JSON content type used by apiFetch. */
async function binary(url: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers);
  const token = authToken.get();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  headers.set("X-Correlation-ID", crypto.randomUUID());
  const response = await fetch(url, { ...init, headers });
  if (!response.ok) {
    let message = `Não foi possível acessar o projeto (${response.status}).`;
    try {
      const value = await response.json();
      message = typeof value.detail === "string" ? value.detail : value.detail?.message || value.detail?.code || message;
    } catch { /* Preserve HTTP status for non-JSON failures. */ }
    if (response.status === 401) window.dispatchEvent(new Event("nexus:unauthorized"));
    throw new APIError(message, response.status);
  }
  return response;
}

export const craftApi = {
  assetDetails: (id: string, signal?: AbortSignal) => apiFetch<AssetRecord>(`/api/v1/assets/${encodeURIComponent(id)}`, { signal }),
  engines: (signal?: AbortSignal) => apiFetch<{ schemaVersion: "studio.craft-engines.v1"; engines: CraftEngineDescriptor[] }>(`${base}/craft/engines`, { signal }),
  inspection: (id: string, signal?: AbortSignal, pageId?: string) => apiFetch<CraftInspection>(`${path(id)}/craft/inspection${pageId ? `?pageId=${encodeURIComponent(pageId)}` : ""}`, { signal }),
  migrate: (id: string, engine: CraftEngine, revision: number, key: string) => apiFetch<CraftInspection>(`${path(id)}/craft/migrate`, json({ engine, expectedRevision: revision }, key)),
  commands: (id: string, revision: number, commands: CraftCommand[], key: string, label?: string, pageId?: string) => apiFetch<CraftReceipt>(`${path(id)}/craft/commands`, json({ expectedRevision: revision, commands, label, pageId }, key)),
  ai: (id: string, revision: number, instruction: string, key: string, pageId?: string) => apiFetch<CraftReceipt>(`${path(id)}/craft/ai-commands`, json({ expectedRevision: revision, instruction, pageId }, key)),
  render: (id: string, revision: number, format: string, key: string, frame = 0, pageId?: string) => apiFetch<StudioGenerationJobRecord>(`${path(id)}/craft/render-jobs`, json({ expectedRevision: revision, format, frame, pageId }, key)),
  linkComposition: (id: string, revision: number, compositionDocumentId: string, key: string) => apiFetch<CraftReceipt>(`${path(id)}/craft/link-composition`, json({ expectedRevision: revision, compositionDocumentId }, key)),
  async preview(id: string, frame: number, signal?: AbortSignal, pageId?: string) {
    const response = await binary(`${path(id)}/craft/preview`, { ...json({ frame, pageId }), headers: { "Content-Type": "application/json" }, signal });
    return response.blob();
  },
  async loadNative(id: string, signal?: AbortSignal, allPages = false, pageId?: string) {
    const query = new URLSearchParams();
    if (allPages) query.set("allPages", "true");
    if (pageId) query.set("pageId", pageId);
    const response = await binary(`${path(id)}/native-project${query.size ? `?${query}` : ""}`, { signal });
    return response.blob();
  },
  async saveNative(id: string, engine: CraftEngine, revision: number, file: Blob, key: string, pageId?: string) {
    const query = new URLSearchParams({ engine, expectedRevision: String(revision) });
    if (pageId) query.set("pageId", pageId);
    const response = await binary(`${path(id)}/native-project?${query}`, { method: "PUT", body: file, headers: { "Content-Type": "application/octet-stream", "Idempotency-Key": key } });
    return response.json() as Promise<CraftReceipt>;
  },
  async uploadAsset(workspaceId: string, file: File) {
    const query = new URLSearchParams({ workspace_id: workspaceId, title: file.name, filename: file.name, media_type: file.type || "application/octet-stream" });
    const response = await binary(`${base}/craft/assets?${query}`, { method: "POST", body: file, headers: { "Content-Type": file.type || "application/octet-stream" } });
    return response.json() as Promise<AssetRecord>;
  },
};
