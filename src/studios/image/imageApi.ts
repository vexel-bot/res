import { apiFetch } from "../../api";
import type {
  AssetRecord,
  StudioGenerationJobRecord,
} from "../../api/productApi";
import type { CraftDocument } from "../craft/craftApi";

export type ImageOperation = "generate_image" | "edit_image";
export interface ImageAIStatus {
  configured: boolean;
  operations: string[];
  stages: Record<
    string,
    {
      provider?: string | null;
      configured: boolean;
      label?: string;
      reason?: string;
    }
  >;
  qualification?: string;
  automaticFallback: boolean;
}
export interface ImageJobInput {
  schemaVersion: "studio.editing-ai-request.v1";
  expectedDocumentRevision: number;
  operation: ImageOperation;
  prompt: string;
  sourceAssetId?: string;
  referenceAssetIds: string[];
  preserve: string[];
  aspectRatio?: string;
  imageSize?: "1K" | "2K" | "4K";
}
export interface ImageUsage {
  productionLimit: number | null;
  jobs: Array<{
    id: string;
    model?: string;
    status: string;
    usage?: unknown;
    outputImages?: number;
    storageBytes?: number;
    testReservationUsd?: number;
    createdAt: string;
  }>;
}
const base = "/api/v1/studios/v1";
const post = (body: unknown, key?: string): RequestInit => ({
  method: "POST",
  body: JSON.stringify(body),
  headers: key ? { "Idempotency-Key": key } : undefined,
});

/** Bindings to existing resource/jobs endpoints; no provider request runs in the browser. */
export const imageApi = {
  status: (signal?: AbortSignal) =>
    apiFetch<ImageAIStatus>(`${base}/editing/ai`, { signal }),
  models: (signal?: AbortSignal) =>
    apiFetch<{ configured: boolean; models: { image: string } }>(
      `${base}/editing/gemini`,
      { signal },
    ),
  usage: (workspaceId: string, signal?: AbortSignal) =>
    apiFetch<ImageUsage>(
      `${base}/editing/usage?workspace_id=${encodeURIComponent(workspaceId)}`,
      { signal },
    ),
  generate: (documentId: string, input: ImageJobInput, key: string) =>
    apiFetch<StudioGenerationJobRecord>(
      `${base}/documents/${encodeURIComponent(documentId)}/editing-ai-jobs`,
      post(input, key),
    ),
  attach: (documentId: string, revision: number, assetId: string) =>
    apiFetch<CraftDocument>(
      `${base}/documents/${encodeURIComponent(documentId)}/editing-resources`,
      post({ expectedDocumentRevision: revision, assetId }),
    ),
  review: (
    asset: AssetRecord,
    result: "passed" | "failed",
    observation: string,
  ) =>
    apiFetch<AssetRecord>(
      `${base}/editing/resources/${encodeURIComponent(asset.id)}/review`,
      post({ checksum: asset.checksumSha256, result, observation }),
    ),
  upload: (workspaceId: string, file: File, usageEvidence: string) => {
    const body = new FormData();
    body.set("workspace_id", workspaceId);
    body.set("title", file.name);
    body.set("metadata", JSON.stringify({ kind: "image", usageEvidence }));
    body.set("file", file);
    return apiFetch<AssetRecord>(`${base}/editing/resources/upload`, {
      method: "POST",
      body,
    });
  },
};
