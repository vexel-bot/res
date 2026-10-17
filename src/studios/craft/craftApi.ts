import { apiFetch, studioRequestHeaders, APIError } from "../../api";
import type { AssetRecord, StudioDocumentRecord, StudioGenerationJobRecord } from "../../api/productApi";

export type CraftEngine = "photocraft" | "filmcraft" | "effectcraft";
export type LLMProtocol = "openai_chat" | "openai_responses" | "anthropic_messages" | "gemini_generate" | "cohere_chat" | "ollama_chat" | "custom_json";
export interface LLMConnectionInput {
  label: string; provider: string; protocol: LLMProtocol; baseUrl: string; models: string[];
  apiKey?: string; authHeader: string; authPrefix: string; extraHeaders?: Record<string, string>;
  requestPath?: string | null; requestTemplate?: Record<string, unknown> | null; responseTextPath?: string | null;
  enabled: boolean; billingMode: "metered" | "local_free"; budgetUsd: number;
  inputUsdPerMillion: number; outputUsdPerMillion: number; maxOutputTokens: number; expectedRevision?: number;
}
export interface LLMConnection {
  id: string; workspaceId: string; label: string; provider: string; revision: number; hasCredential: boolean;
  config: Omit<LLMConnectionInput, "label" | "provider" | "apiKey" | "expectedRevision">;
  qualification: string;
}
export interface LLMCatalog {
  credentialStorageReady: boolean; legacyPlanningAvailable?: boolean;
  providers: { id: string; label: string; protocol: LLMProtocol; baseUrl: string;
    models: { id: string; label: string }[]; documentationUrl: string; verifiedAt: string;
    authHeader?: string; authPrefix?: string; billingMode?: "metered" | "local_free" }[];
}
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
  compositionDocumentId?: string;
  aiTrace?: Record<string, unknown>;
}
export interface CraftAIRecovery {
  schemaVersion: "clicko.craft-ai-recovery.v1";
  userId: string; workspaceId: string; documentId: string; engine: CraftEngine;
  expectedRevision: number; instruction: string; idempotencyKey: string;
  pageId?: string; connectionId?: string; model?: string;
}

const base = "/api/v1/studios/v1";
const path = (id: string) => `${base}/documents/${encodeURIComponent(id)}`;
function json(body: unknown, key?: string): RequestInit {
  return { method: "POST", body: JSON.stringify(body), headers: key ? { "Idempotency-Key": key } : undefined };
}

/** Binary requests must not inherit the JSON content type used by apiFetch. */
async function binary(url: string, init: RequestInit = {}): Promise<Response> {
  const headers = studioRequestHeaders(new Headers(init.headers));
  headers.set("X-Correlation-ID", crypto.randomUUID());
  const response = await fetch(url, { ...init, credentials: 'same-origin', headers });
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
  llmCatalog: (signal?: AbortSignal) => apiFetch<LLMCatalog>(`${base}/craft/llm-catalog`, { signal }),
  llmConnections: (workspaceId: string, signal?: AbortSignal) => apiFetch<{ connections: LLMConnection[]; canManage: boolean }>(`${base}/craft/llm-connections?workspace_id=${encodeURIComponent(workspaceId)}`, { signal }),
  saveLLMConnection: (workspaceId: string, body: LLMConnectionInput, id?: string) => apiFetch<LLMConnection>(`${base}/craft/llm-connections${id ? `/${encodeURIComponent(id)}` : ""}?workspace_id=${encodeURIComponent(workspaceId)}`, { method: id ? "PUT" : "POST", body: JSON.stringify(body) }),
  removeLLMConnection: (workspaceId: string, connection: LLMConnection) => apiFetch<LLMConnection>(`${base}/craft/llm-connections/${encodeURIComponent(connection.id)}?workspace_id=${encodeURIComponent(workspaceId)}&expected_revision=${connection.revision}`, { method: "DELETE" }),
  assetDetails: (id: string, signal?: AbortSignal) => apiFetch<AssetRecord>(`/api/v1/assets/${encodeURIComponent(id)}`, { signal }),
  engines: (signal?: AbortSignal) => apiFetch<{ schemaVersion: "studio.craft-engines.v1"; engines: CraftEngineDescriptor[] }>(`${base}/craft/engines`, { signal }),
  inspection: (id: string, signal?: AbortSignal, pageId?: string) => apiFetch<CraftInspection>(`${path(id)}/craft/inspection${pageId ? `?pageId=${encodeURIComponent(pageId)}` : ""}`, { signal }),
  migrate: (id: string, engine: CraftEngine, revision: number, key: string) => apiFetch<CraftInspection>(`${path(id)}/craft/migrate`, json({ engine, expectedRevision: revision }, key)),
  upgradeBuild: (id: string, revision: number, targetBuildId: string, key: string) => apiFetch<CraftReceipt>(`${path(id)}/craft/upgrade-build`, json({ expectedRevision: revision, targetBuildId }, key)),
  commands: (id: string, revision: number, commands: CraftCommand[], key: string, label?: string, pageId?: string) => apiFetch<CraftReceipt>(`${path(id)}/craft/commands`, json({ expectedRevision: revision, commands, label, pageId }, key)),
  ai: (id: string, revision: number, instruction: string, key: string, pageId?: string, connectionId?: string, model?: string) => apiFetch<CraftReceipt>(`${path(id)}/craft/ai-commands`, json({ expectedRevision: revision, instruction, pageId, connectionId, model }, key)),
  aiRequest: (id: string, key: string) => apiFetch<{ status: string; receipt?: CraftReceipt; responseReady?: boolean; errorCode?: string }>(`${path(id)}/craft/ai-requests/${encodeURIComponent(key)}`),
  render: (id: string, revision: number, format: string, key: string, frame = 0, pageId?: string) => apiFetch<StudioGenerationJobRecord>(`${path(id)}/craft/render-jobs`, json({ expectedRevision: revision, format, frame, pageId }, key)),
  linkComposition: (id: string, revision: number, compositionDocumentId: string, key: string) => apiFetch<CraftReceipt>(`${path(id)}/craft/link-composition`, json({ expectedRevision: revision, compositionDocumentId }, key)),
  recoverEffects: (id: string, revision: number, key: string) => apiFetch<CraftReceipt & { compositionDocumentId: string }>(`${path(id)}/craft/recover-effects`, json({ expectedRevision: revision }, key)),
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
