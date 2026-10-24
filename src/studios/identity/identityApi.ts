import { apiFetch } from "../../api";
import type {
  StudioConsentRecord,
  StudioIdentityRecord,
  StudioIdentityVersionRecord,
  StudioVoiceRecord,
  StudioVoiceVersionRecord,
} from "../../api/productApi";

export interface CastCard<P, V> {
  profile: P;
  versions: V[];
  selectedVersionId: string | null;
  previewAssetId: string | null;
  unavailableReason: string | null;
}
export interface IdentityCatalog {
  workspaceId: string;
  identities: CastCard<StudioIdentityRecord, StudioIdentityVersionRecord>[];
  voices: CastCard<StudioVoiceRecord, StudioVoiceVersionRecord>[];
  consents: StudioConsentRecord[];
}
export type EnrollmentMode =
  "face" | "voice" | "face_voice" | "character" | "stock_voice";
export interface EnrollmentInput {
  workspaceId: string;
  requestKey: string;
  mode: EnrollmentMode;
  displayName: string;
  imageAssetId?: string;
  audioAssetId?: string;
  evidenceAssetId: string;
  purpose: string;
  expiresAt?: string;
  rightsReference: string;
  declared: true;
}
const base = "/api/v1/studios/v1/identity-library";
export const identityApi = {
  catalog: async (workspace: string, signal?: AbortSignal) => {
    const value = await apiFetch<IdentityCatalog>(
      `${base}?workspace_id=${encodeURIComponent(workspace)}`,
      { signal },
    );
    if (
      value.workspaceId !== workspace ||
      !Array.isArray(value.identities) ||
      !Array.isArray(value.voices) ||
      !Array.isArray(value.consents)
    )
      throw new Error(
        "Não foi possível conferir o catálogo de identidades desta marca.",
      );
    return value;
  },
  enroll: (input: EnrollmentInput) =>
    apiFetch<{
      status: "draft";
      identityProfileId: string | null;
      voiceProfileId: string | null;
    }>(`${base}/enrollments`, { method: "POST", body: JSON.stringify(input) }),
};
