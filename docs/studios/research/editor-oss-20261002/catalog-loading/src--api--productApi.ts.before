import {
  backendClient,
  requireBackendData,
  requireBackendSuccess,
  type BackendSchema,
} from "./client";
import { apiFetch, apiFetchBlob } from "../api";

export type WorkspaceRecord = BackendSchema<"WorkspaceOut">;
export type WorkspaceInput = BackendSchema<"WorkspaceCreate">;
export type BootstrapRecord = BackendSchema<"BootstrapOut">;
export type CampaignRecord = BackendSchema<"CampaignOut">;
export type CampaignInput = BackendSchema<"CampaignIn">;
export type CampaignUpdate = BackendSchema<"CampaignUpdate">;
export type CampaignPiecesInput = BackendSchema<"CampaignPiecesIn">;
export type CampaignDecisionInput = BackendSchema<"CampaignDecisionIn">;
export type PostRecord = BackendSchema<"PostOut">;
export type PostInput = BackendSchema<"PostIn">;
export type PostUpdate = BackendSchema<"PostUpdate">;
export type ApprovalEventRecord = BackendSchema<"ApprovalEventOut">;
export type ApprovalActionInput = BackendSchema<"ApprovalActionIn">;
export type PostMetricsInput = BackendSchema<"PostMetricsIn">;
export type PostFeedbackInput = BackendSchema<"PostFeedbackIn">;
export interface HistoryReuseInput {
  title?: string;
  format?: string;
  platform?: string;
  objective?: string;
  derivationKey?: string;
  hypothesis?: string;
  preserve?: string[];
  adapt?: string[];
}
export type CreativeRecord = BackendSchema<"CreativeDocumentOut">;
export type CreativeInput = BackendSchema<"CreativeDocumentIn">;
export type CreativeUpdate = BackendSchema<"CreativeDocumentUpdate">;
export type CreativeCanvas = BackendSchema<"CreativeCanvas">;
export type StudioDocumentRecord = BackendSchema<"CreativeDocumentV1-Output">;
export type StudioDocumentInput = BackendSchema<"CreativeDocumentV1-Input">;
export type StudioDocumentCreate = BackendSchema<"CreateStudioDocumentRequest">;
export type StudioDocumentVersionRecord = BackendSchema<"StudioDocumentVersionV1">;
export type StudioReviewRecord = BackendSchema<"StudioReviewRequestV1">;
export type EditorialReadiness = BackendSchema<"EditorialReadinessV1">;
export type EditorialPlanInput = BackendSchema<"EditorialPlanRequestV1">;
export type EditorialReviewInput = BackendSchema<"EditorialReviewRequestV1">;
export type StudioListeningReviewSubmission = BackendSchema<"StudioListeningReviewSubmissionV1">;
export type StudioAcousticAnalysisCapability = BackendSchema<"StudioAcousticAnalysisCapabilityV1">;
export type StudioAssetRightsReviewInput = BackendSchema<"StudioAssetRightsReviewRequestV1">;
export type StudioAssetRightsReviewResponse = BackendSchema<"StudioAssetRightsReviewResponseV1">;
export interface StudioPublicationPreflightRecord {
  schemaVersion: "studio.publication-preflight.v1";
  reviewId: string;
  documentId: string;
  documentVersion: number;
  postId: string;
  title: string;
  platform: string;
  format: string;
  caption: string;
  hashtags: string[];
  contentType: "visual" | "carousel" | "video" | "presenter";
  pageIds: string[];
  status: "ready" | "scheduled";
  scheduledAt?: string | null;
  checks: Array<{
    key: string;
    label: string;
    status: "passed" | "warning" | "failed";
    detail: string;
  }>;
}
export interface StudioInternalScheduleReceiptRecord {
  schemaVersion: "studio.internal-schedule-receipt.v1";
  receiptId: string;
  reviewId: string;
  documentId: string;
  documentVersion: number;
  postId: string;
  scheduledAt: string;
  externalPublicationConfirmed: false;
}
export type StudioMediaIngestRecord = BackendSchema<"MediaIngestV1">;
export type StudioMediaIngestCreate = BackendSchema<"CreateMediaIngestRequest">;
export type StudioTranscriptRecord = BackendSchema<"TranscriptDocumentV1-Output">;
export type StudioTranscriptCreate = BackendSchema<"CreateTranscriptRequest">;
export type StudioEditDecisionRecord = BackendSchema<"EditDecisionSetV1">;
export type StudioEditDecisionCreate = BackendSchema<"CreateEditDecisionSetRequest">;
export type StudioVideoRenderCreate = BackendSchema<"CreateVideoRenderJobRequest">;
export type StudioGenerationJobRecord = BackendSchema<"GenerationJobV1">;
export type StudioGenerationJobCreate = BackendSchema<"CreateGenerationJobRequest">;
export type StudioConsentRecord = BackendSchema<"ConsentGrantV1">;
export type StudioConsentCreate = BackendSchema<"CreateConsentGrantRequest">;
export type StudioIdentityRecord = BackendSchema<"IdentityProfileV1">;
export type StudioIdentityCreate = BackendSchema<"CreateIdentityProfileRequest">;
export type StudioIdentityVersionRecord = BackendSchema<"IdentityVersionV1">;
export type StudioIdentityVersionCreate = BackendSchema<"CreateIdentityVersionRequest">;
export type StudioVoiceRecord = BackendSchema<"VoiceProfileV1">;
export type StudioVoiceCreate = BackendSchema<"CreateVoiceProfileRequest">;
export type StudioVoiceVersionRecord = BackendSchema<"VoiceVersionV1">;
export type StudioVoiceVersionCreate = BackendSchema<"CreateVoiceVersionRequest">;
export type StudioMotionGraphRecord = BackendSchema<"MotionGraphRecordV1">;
export type StudioMotionGraphCreate = BackendSchema<"CreateMotionGraphRequestV1">;
export type StudioMotionGraphReview = BackendSchema<"ReviewMotionGraphRequestV1">;
export type StudioCreativeCasebookRecord = BackendSchema<"CreativePilotCasebookV1">;
export type StudioAssistedIntelligenceSuiteRecord = BackendSchema<"AssistedIntelligenceSuiteEvidenceV1">;
export type StudioVideoFactoryProgramRecord = BackendSchema<"VideoFactoryProgramEvidenceV1">;
export type StudioCreativeReplanStateRecord = BackendSchema<"CreativeReplanStateV1">;
export type StudioAdvancedCapabilityAuditRecord = BackendSchema<"AdvancedCapabilityAuditV1">;
export type StudioVideoAutonomyAuditRecord = BackendSchema<"VideoAutonomyCompletionAuditV1">;
export type StudioImageDerivationCreate = BackendSchema<"ImageDerivationRequestV1">;
export type AssetRecord = BackendSchema<"AssetOut">;
export type AssetInput = BackendSchema<"AssetIn">;
export type AnalyticsRecord = BackendSchema<"AnalyticsSummaryOut">;
export type RadarRecord = BackendSchema<"RadarStateOut">;
export type RadarFeedbackInput = BackendSchema<"FeedbackIn">;
export type WorkspaceResourceRecord = BackendSchema<"WorkspaceResourceOut">;
export type WorkspaceResourceInput = BackendSchema<"WorkspaceResourceIn">;
export type WorkspaceResourceUpdate = BackendSchema<"WorkspaceResourceUpdate">;

export type StudioCapabilityName =
  | "presenter"
  | "avatar"
  | "voice_clone"
  | "stock_voice"
  | "transcription";

export interface StudioCapabilityReadiness {
  schemaVersion: "studio.capability-readiness.v1";
  workspaceId: string;
  capability: StudioCapabilityName;
  status: "unavailable" | "blocked" | "review" | "ready";
  providerReady: boolean;
  captureReady: boolean;
  providerCandidates: number;
  approvedProviders: number;
  modelCandidates: number;
  approvedModels: number;
  activeIdentityVersions: number;
  activeVoiceVersions: number;
  activeConsentGrants: number;
  benchmarkReady: boolean;
  licenseReady: boolean;
  consentReady: boolean;
  publicationAllowed: boolean;
  reasons: string[];
  evaluatedAt: string;
}

export interface StudioCapabilitiesRecord {
  schemaVersion: "studio.capabilities.v1";
  workspaceId: string;
  capabilities: StudioCapabilityReadiness[];
  evaluatedAt: string;
}

export interface StudioProviderRecord {
  schemaVersion: "studio.provider-registration.v1";
  id: string;
  capability: string;
  provider: string;
  providerVersion: string;
  sourceUrl: string;
  sourceRevision: string;
  codeLicense: string;
  status: "evaluation" | "approved" | "disabled" | "rejected";
  riskClass: "low" | "medium" | "high" | "biometric";
  manifest: Record<string, unknown>;
  approvedBy?: string | null;
  approvedAt?: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface StudioModelRecord {
  schemaVersion: "studio.model-registration.v1";
  id: string;
  providerRegistrationId: string;
  name: string;
  version: string;
  digestSha256: string;
  modelLicense: string;
  commercialUse: "approved" | "restricted" | "unknown";
  languages: string[];
  capabilities: string[];
  status: "evaluation" | "approved" | "disabled" | "rejected";
  manifest: Record<string, unknown>;
  approvedBy?: string | null;
  approvedAt?: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface StudioProviderInput {
  workspaceId: string;
  capability: string;
  provider: string;
  providerVersion: string;
  sourceUrl: string;
  sourceRevision: string;
  codeLicense: string;
  riskClass: StudioProviderRecord["riskClass"];
  manifest?: Record<string, unknown>;
}

export interface StudioModelInput {
  workspaceId: string;
  providerRegistrationId: string;
  name: string;
  version: string;
  digestSha256: string;
  modelLicense: string;
  commercialUse?: StudioModelRecord["commercialUse"];
  languages?: string[];
  capabilities?: string[];
  manifest?: Record<string, unknown>;
}

export interface ProductSnapshot {
  workspaceId: string;
  campaigns: CampaignRecord[];
  posts: PostRecord[];
  creatives: CreativeRecord[];
  assets: AssetRecord[];
  approvalEvents: ApprovalEventRecord[];
  analytics: AnalyticsRecord;
  radar: RadarRecord;
  connectedAccounts: WorkspaceResourceRecord[];
  presenterSessions: WorkspaceResourceRecord[];
  factoryRounds: WorkspaceResourceRecord[];
  studioCapabilities: Partial<Record<StudioCapabilityName, StudioCapabilityReadiness>>;
  loadedAt: string;
}

export const productApi = {
  async bootstrap() {
    return requireBackendData(
      await backendClient.GET("/api/v1/bootstrap"),
      "Carregamento inicial do workspace",
    );
  },

  async workspaces() {
    return requireBackendData(
      await backendClient.GET("/api/v1/workspaces"),
      "Lista de workspaces",
    );
  },

  async createWorkspace(input: WorkspaceInput) {
    return requireBackendData(
      await backendClient.POST("/api/v1/workspaces", { body: input }),
      "Criação de workspace",
    );
  },

  async studioCapabilities(workspaceId: string) {
    return apiFetch<StudioCapabilitiesRecord>(
      `/api/v1/studios/v1/capabilities?workspace_id=${encodeURIComponent(workspaceId)}`,
    );
  },

  async studioConsents(workspaceId: string, subjectKey?: string) {
    return requireBackendData(
      await backendClient.GET("/api/v1/studios/v1/consents", {
        params: { query: { workspace_id: workspaceId, subject_key: subjectKey } },
      }),
      "Consentimentos do Studio",
    );
  },

  async createStudioConsent(input: StudioConsentCreate) {
    return requireBackendData(
      await backendClient.POST("/api/v1/studios/v1/consents", { body: input }),
      "Criação do consentimento do Studio",
    );
  },

  async revokeStudioConsent(consentId: string, reason: string) {
    return requireBackendData(
      await backendClient.POST("/api/v1/studios/v1/consents/{consent_id}/revoke", {
        params: { path: { consent_id: consentId } },
        body: { reason },
      }),
      "Revogação do consentimento do Studio",
    );
  },

  async studioIdentities(workspaceId: string) {
    return requireBackendData(
      await backendClient.GET("/api/v1/studios/v1/identities", {
        params: { query: { workspace_id: workspaceId } },
      }),
      "Identidades do Studio",
    );
  },

  async createStudioIdentity(input: StudioIdentityCreate) {
    return requireBackendData(
      await backendClient.POST("/api/v1/studios/v1/identities", { body: input }),
      "Criação da identidade do Studio",
    );
  },

  async studioIdentityVersions(profileId: string) {
    return requireBackendData(
      await backendClient.GET("/api/v1/studios/v1/identities/{profile_id}/versions", {
        params: { path: { profile_id: profileId } },
      }),
      "Versões da identidade do Studio",
    );
  },

  async createStudioIdentityVersion(
    profileId: string,
    input: StudioIdentityVersionCreate,
  ) {
    return requireBackendData(
      await backendClient.POST("/api/v1/studios/v1/identities/{profile_id}/versions", {
        params: { path: { profile_id: profileId } },
        body: input,
      }),
      "Criação da versão da identidade do Studio",
    );
  },

  async studioVoices(workspaceId: string) {
    return requireBackendData(
      await backendClient.GET("/api/v1/studios/v1/voices", {
        params: { query: { workspace_id: workspaceId } },
      }),
      "Vozes do Studio",
    );
  },

  async createStudioVoice(input: StudioVoiceCreate) {
    return requireBackendData(
      await backendClient.POST("/api/v1/studios/v1/voices", { body: input }),
      "Criação da voz do Studio",
    );
  },

  async studioVoiceVersions(profileId: string) {
    return requireBackendData(
      await backendClient.GET("/api/v1/studios/v1/voices/{profile_id}/versions", {
        params: { path: { profile_id: profileId } },
      }),
      "Versões de voz do Studio",
    );
  },

  async createStudioVoiceVersion(
    profileId: string,
    input: StudioVoiceVersionCreate,
  ) {
    return requireBackendData(
      await backendClient.POST("/api/v1/studios/v1/voices/{profile_id}/versions", {
        params: { path: { profile_id: profileId } },
        body: input,
      }),
      "Criação da versão de voz do Studio",
    );
  },

  async studioProviders(workspaceId: string, capability?: string) {
    const query = new URLSearchParams({ workspace_id: workspaceId });
    if (capability) query.set("capability", capability);
    return apiFetch<StudioProviderRecord[]>(
      `/api/v1/studios/v1/providers?${query.toString()}`,
    );
  },

  async studioMotionGraphs(workspaceId: string, documentId?: string) {
    return requireBackendData(
      await backendClient.GET("/api/v1/studios/v1/motion-graphs", {
        params: { query: { workspace_id: workspaceId, document_id: documentId } },
      }),
      "Grafos de movimento do Studio",
    );
  },

  async createStudioMotionGraph(input: StudioMotionGraphCreate) {
    return requireBackendData(
      await backendClient.POST("/api/v1/studios/v1/motion-graphs", { body: input }),
      "Criação do movimento do Studio",
    );
  },

  async reviewStudioMotionGraph(graphId: string, input: StudioMotionGraphReview) {
    return requireBackendData(
      await backendClient.POST("/api/v1/studios/v1/motion-graphs/{graph_id}/review", {
        params: { path: { graph_id: graphId } },
        body: input,
      }),
      "Aplicação revisada do movimento",
    );
  },

  async studioMotionProjection(
    graphId: string,
    target: "hyperframes" | "motion_canvas",
    reducedMotion = false,
  ) {
    return requireBackendData(
      await backendClient.GET("/api/v1/studios/v1/motion-graphs/{graph_id}/projection/{target}", {
        params: {
          path: { graph_id: graphId, target },
          query: { reduced_motion: reducedMotion },
        },
      }),
      "Projeção provider-neutral do movimento",
    );
  },

  async createStudioProvider(input: StudioProviderInput) {
    return apiFetch<StudioProviderRecord>("/api/v1/studios/v1/providers", {
      method: "POST",
      body: JSON.stringify(input),
    });
  },

  async approveStudioProvider(providerId: string, workspaceId: string) {
    return apiFetch<StudioProviderRecord>(
      `/api/v1/studios/v1/providers/${encodeURIComponent(providerId)}/approve?workspace_id=${encodeURIComponent(workspaceId)}`,
      { method: "POST" },
    );
  },

  async studioModels(workspaceId: string, providerRegistrationId?: string) {
    const query = new URLSearchParams({ workspace_id: workspaceId });
    if (providerRegistrationId)
      query.set("provider_registration_id", providerRegistrationId);
    return apiFetch<StudioModelRecord[]>(
      `/api/v1/studios/v1/models?${query.toString()}`,
    );
  },

  async createStudioModel(input: StudioModelInput) {
    return apiFetch<StudioModelRecord>("/api/v1/studios/v1/models", {
      method: "POST",
      body: JSON.stringify(input),
    });
  },

  async approveStudioModel(modelId: string, workspaceId: string) {
    return apiFetch<StudioModelRecord>(
      `/api/v1/studios/v1/models/${encodeURIComponent(modelId)}/approve?workspace_id=${encodeURIComponent(workspaceId)}`,
      { method: "POST" },
    );
  },

  async snapshot(workspaceId: string): Promise<ProductSnapshot> {
    const params = { query: { workspace_id: workspaceId } } as const;
    const [
      campaigns,
      posts,
      creatives,
      assets,
      approvalEvents,
      analytics,
      radar,
      connectedAccounts,
      presenterSessions,
      factoryRounds,
      studioCapabilitiesResponse,
    ] = await Promise.all([
      backendClient.GET("/api/v1/campaigns", { params }),
      backendClient.GET("/api/v1/posts", { params }),
      backendClient.GET("/api/v1/creatives", { params }),
      backendClient.GET("/api/v1/assets", { params }),
      backendClient.GET("/api/v1/posts/approval-events", { params }),
      backendClient.GET("/api/v1/analytics/summary", { params }),
      backendClient.GET("/api/v1/radar/state", { params }),
      backendClient.GET("/api/v1/workspace-resources", {
        params: {
          query: { workspace_id: workspaceId, kind: "connected_account" },
        },
      }),
      backendClient.GET("/api/v1/workspace-resources", {
        params: {
          query: { workspace_id: workspaceId, kind: "presenter_session" },
        },
      }),
      backendClient.GET("/api/v1/workspace-resources", {
        params: {
          query: { workspace_id: workspaceId, kind: "factory_round" },
        },
      }),
      productApi.studioCapabilities(workspaceId),
    ]);

    const studioCapabilities = Object.fromEntries(
      studioCapabilitiesResponse.capabilities.map((item) => [item.capability, item]),
    ) as Partial<Record<StudioCapabilityName, StudioCapabilityReadiness>>;

    return {
      workspaceId,
      campaigns: requireBackendData(campaigns, "Campanhas"),
      posts: requireBackendData(posts, "Conteúdos"),
      creatives: requireBackendData(creatives, "Documentos criativos"),
      assets: requireBackendData(assets, "Assets"),
      approvalEvents: requireBackendData(
        approvalEvents,
        "Eventos de aprovação",
      ),
      analytics: requireBackendData(analytics, "Analytics"),
      radar: requireBackendData(radar, "Radar"),
      connectedAccounts: requireBackendData(
        connectedAccounts,
        "Contas conectadas",
      ),
      presenterSessions: requireBackendData(
        presenterSessions,
        "Sessões do Presenter",
      ),
      factoryRounds: requireBackendData(factoryRounds, "Rodadas da Fábrica"),
      studioCapabilities,
      loadedAt: new Date().toISOString(),
    };
  },

  async createWorkspaceResource(input: WorkspaceResourceInput) {
    return requireBackendData(
      await backendClient.POST("/api/v1/workspace-resources", { body: input }),
      "Criação de estado do workspace",
    );
  },

  async updateWorkspaceResource(
    resourceId: string,
    workspaceId: string,
    input: WorkspaceResourceUpdate,
  ) {
    return requireBackendData(
      await backendClient.PATCH("/api/v1/workspace-resources/{resource_id}", {
        params: {
          path: { resource_id: resourceId },
          query: { workspace_id: workspaceId },
        },
        body: input,
      }),
      "Atualização de estado do workspace",
    );
  },

  async createCampaign(input: CampaignInput) {
    return requireBackendData(
      await backendClient.POST("/api/v1/campaigns", { body: input }),
      "Criação de campanha",
    );
  },

  async updateCampaign(campaignId: string, input: CampaignUpdate) {
    return requireBackendData(
      await backendClient.PATCH("/api/v1/campaigns/{campaign_id}", {
        params: { path: { campaign_id: campaignId } },
        body: input,
      }),
      "Atualização de campanha",
    );
  },

  async createCampaignPieces(campaignId: string, input: CampaignPiecesInput) {
    return requireBackendData(
      await backendClient.POST("/api/v1/campaigns/{campaign_id}/pieces", {
        params: { path: { campaign_id: campaignId } },
        body: input,
      }),
      "Geração do kit da campanha",
    );
  },

  async decideCampaign(campaignId: string, input: CampaignDecisionInput) {
    return requireBackendData(
      await backendClient.POST("/api/v1/campaigns/{campaign_id}/decisions", {
        params: { path: { campaign_id: campaignId } },
        body: input,
      }),
      "Decisão da campanha",
    );
  },

  async saveCampaignVersion(campaignId: string, label = "Versão manual") {
    return requireBackendData(
      await backendClient.POST("/api/v1/campaigns/{campaign_id}/versions", {
        params: { path: { campaign_id: campaignId } },
        body: { label },
      }),
      "Versionamento da campanha",
    );
  },

  async restoreCampaignVersion(campaignId: string, versionNumber: number) {
    return requireBackendData(
      await backendClient.POST(
        "/api/v1/campaigns/{campaign_id}/versions/{version_number}/restore",
        {
          params: {
            path: { campaign_id: campaignId, version_number: versionNumber },
          },
        },
      ),
      "Restauração da campanha",
    );
  },

  async createPost(input: PostInput) {
    return requireBackendData(
      await backendClient.POST("/api/v1/posts", { body: input }),
      "Criação de conteúdo",
    );
  },

  async updatePost(postId: string, input: PostUpdate) {
    return requireBackendData(
      await backendClient.PATCH("/api/v1/posts/{post_id}", {
        params: { path: { post_id: postId } },
        body: input,
      }),
      "Atualização de conteúdo",
    );
  },

  async approvalAction(postId: string, input: ApprovalActionInput) {
    return requireBackendData(
      await backendClient.POST("/api/v1/posts/{post_id}/approval-actions", {
        params: { path: { post_id: postId } },
        body: input,
      }),
      "Decisão de aprovação",
    );
  },

  async recordPostMetrics(postId: string, input: PostMetricsInput) {
    return requireBackendData(
      await backendClient.POST("/api/v1/posts/{post_id}/metrics", {
        params: { path: { post_id: postId } },
        body: input,
      }),
      "Registro de métricas",
    );
  },

  async postMetrics(postId: string) {
    return requireBackendData(
      await backendClient.GET("/api/v1/posts/{post_id}/metrics", {
        params: { path: { post_id: postId } },
      }),
      "Histórico de métricas",
    );
  },

  async recordPostFeedback(postId: string, input: PostFeedbackInput) {
    const result = await backendClient.POST(
      "/api/v1/posts/{post_id}/feedback",
      {
        params: { path: { post_id: postId } },
        body: input,
      },
    );
    requireBackendSuccess(result, "Feedback do conteúdo");
  },

  async restorePostVersion(postId: string, versionNumber: number) {
    return requireBackendData(
      await backendClient.POST(
        "/api/v1/posts/{post_id}/versions/{version_number}/restore",
        {
          params: { path: { post_id: postId, version_number: versionNumber } },
        },
      ),
      "Restauração do conteúdo",
    );
  },

  async createCreative(input: CreativeInput) {
    return requireBackendData(
      await backendClient.POST("/api/v1/creatives", { body: input }),
      "Criação de documento criativo",
    );
  },

  async getCreative(documentId: string) {
    return requireBackendData(
      await backendClient.GET("/api/v1/creatives/{document_id}", {
        params: { path: { document_id: documentId } },
      }),
      "Documento criativo",
    );
  },

  async updateCreative(documentId: string, input: CreativeUpdate) {
    return requireBackendData(
      await backendClient.PATCH("/api/v1/creatives/{document_id}", {
        params: { path: { document_id: documentId } },
        body: input,
      }),
      "Autosave do documento criativo",
    );
  },

  async createCreativeVersion(documentId: string, label?: string) {
    return requireBackendData(
      await backendClient.POST("/api/v1/creatives/{document_id}/versions", {
        params: { path: { document_id: documentId } },
        body: { label: label ?? "Versão manual" },
      }),
      "Versionamento criativo",
    );
  },

  async restoreCreativeVersion(documentId: string, versionNumber: number) {
    return requireBackendData(
      await backendClient.POST(
        "/api/v1/creatives/{document_id}/versions/{version_number}/restore",
        {
          params: {
            path: { document_id: documentId, version_number: versionNumber },
          },
        },
      ),
      "Restauração do documento criativo",
    );
  },

  async studioDocuments(
    workspaceId: string,
    options: { postId?: string; campaignId?: string } = {},
  ) {
    return requireBackendData(
      await backendClient.GET("/api/v1/studios/v1/documents", {
        params: {
          query: {
            workspace_id: workspaceId,
            post_id: options.postId,
            campaign_id: options.campaignId,
          },
        },
      }),
      "Documentos do Studio",
    );
  },

  async studioCreativeCasebook() {
    return requireBackendData(
      await backendClient.GET("/api/v1/studios/v1/creative/casebook"),
      "Casebook criativo de vídeo",
    );
  },

  async studioAssistedIntelligence() {
    return requireBackendData(
      await backendClient.GET("/api/v1/studios/v1/creative/assisted-intelligence"),
      "Inteligência editorial assistida",
    );
  },

  async studioVideoFactoryProgram() {
    return requireBackendData(
      await backendClient.GET("/api/v1/studios/v1/creative/factory-program"),
      "Programa privado da fábrica de vídeo",
    );
  },

  async studioCreativeReplanState() {
    return requireBackendData(
      await backendClient.GET("/api/v1/studios/v1/creative/replan-state"),
      "Estado do replanejamento criativo",
    );
  },

  async studioAdvancedCapabilityAudit() {
    return requireBackendData(
      await backendClient.GET("/api/v1/studios/v1/creative/advanced-capabilities"),
      "Auditoria de voz e avatar",
    );
  },

  async studioVideoAutonomyAudit() {
    return requireBackendData(
      await backendClient.GET("/api/v1/studios/v1/creative/autonomy-audit"),
      "Auditoria de conclusão da autonomia de vídeo",
    );
  },

  async studioCreativeAnimatic(caseId: string, signal?: AbortSignal) {
    return apiFetchBlob(
      `/api/v1/studios/v1/creative/cases/${encodeURIComponent(caseId)}/animatic`,
      signal,
    );
  },

  async studioDocument(documentId: string) {
    return requireBackendData(
      await backendClient.GET("/api/v1/studios/v1/documents/{document_id}", {
        params: { path: { document_id: documentId } },
      }),
      "Documento do Studio",
    );
  },

  async editorialReadiness(documentId: string, signal?: AbortSignal) {
    return requireBackendData(await backendClient.GET(
      "/api/v1/studios/v1/documents/{document_id}/editorial-readiness",
      { params: { path: { document_id: documentId } }, signal },
    ), "Prontidão editorial");
  },

  async registerEditorialPlan(documentId: string, body: EditorialPlanInput, key: string) {
    return requireBackendData(await backendClient.POST(
      "/api/v1/studios/v1/documents/{document_id}/editorial-plans",
      { params: { path: { document_id: documentId }, header: { "Idempotency-Key": key } }, body },
    ), "Plano editorial");
  },

  async reviewEditorialAxis(documentId: string, body: EditorialReviewInput, key: string) {
    return requireBackendData(await backendClient.POST(
      "/api/v1/studios/v1/documents/{document_id}/editorial-reviews",
      { params: { path: { document_id: documentId }, header: { "Idempotency-Key": key } }, body },
    ), "Revisão editorial");
  },

  async createStudioDocument(input: StudioDocumentCreate) {
    return requireBackendData(
      await backendClient.POST("/api/v1/studios/v1/documents", {
        body: input,
      }),
      "Criação do documento do Studio",
    );
  },

  async replaceStudioDocument(
    documentId: string,
    expectedRevision: number,
    document: StudioDocumentInput,
  ) {
    return requireBackendData(
      await backendClient.PUT("/api/v1/studios/v1/documents/{document_id}", {
        params: { path: { document_id: documentId } },
        body: { expectedRevision, document },
      }),
      "Gravação do documento do Studio",
    );
  },

  async reviewNaturalSoundRights(
    documentId: string,
    assetId: string,
    input: StudioAssetRightsReviewInput,
    idempotencyKey: string,
  ) {
    return requireBackendData(
      await backendClient.POST(
        "/api/v1/studios/v1/documents/{document_id}/assets/{asset_id}/rights-reviews",
        {
          params: {
            path: { document_id: documentId, asset_id: assetId },
            header: { "Idempotency-Key": idempotencyKey },
          },
          body: input,
        },
      ),
      "Revisão de direitos do som natural",
    );
  },

  async createStudioVersion(documentId: string, label = "Versão manual") {
    return requireBackendData(
      await backendClient.POST(
        "/api/v1/studios/v1/documents/{document_id}/versions",
        {
          params: { path: { document_id: documentId } },
          body: { label },
        },
      ),
      "Versionamento do documento do Studio",
    );
  },

  async studioDocumentVersions(documentId: string) {
    return requireBackendData(
      await backendClient.GET(
        "/api/v1/studios/v1/documents/{document_id}/versions",
        { params: { path: { document_id: documentId } } },
      ),
      "Histórico do documento do Studio",
    );
  },

  async restoreStudioDocumentVersion(
    documentId: string,
    versionNumber: number,
    expectedRevision: number,
    label?: string,
  ) {
    return requireBackendData(
      await backendClient.POST(
        "/api/v1/studios/v1/documents/{document_id}/versions/{version_number}/restore",
        {
          params: {
            path: { document_id: documentId, version_number: versionNumber },
          },
          body: { expectedRevision, label: label ?? null },
        },
      ),
      "Restauração da versão do Studio",
    );
  },

  async requestStudioReview(
    documentId: string,
    comment?: string,
    renderJobId?: string,
  ) {
    return requireBackendData(
      await backendClient.POST(
        "/api/v1/studios/v1/documents/{document_id}/reviews",
        {
          params: { path: { document_id: documentId } },
          body: { comment: comment ?? null, renderJobId: renderJobId ?? null },
        },
      ),
      "Solicitação de revisão do Studio",
    );
  },

  async latestStudioReview(
    workspaceId: string,
    options: { documentId?: string; postId?: string },
  ) {
    return requireBackendData(
      await backendClient.GET("/api/v1/studios/v1/reviews/latest", {
        params: {
          query: {
            workspace_id: workspaceId,
            document_id: options.documentId,
            post_id: options.postId,
          },
        },
      }),
      "Revisão fixada do Studio",
    );
  },

  async decideStudioReview(
    reviewId: string,
    action: "approve" | "request_changes" | "reject",
    comment?: string,
    listeningReview?: StudioListeningReviewSubmission,
  ) {
    return requireBackendData(
      await backendClient.POST(
        "/api/v1/studios/v1/reviews/{review_id}/decisions",
        {
          params: { path: { review_id: reviewId } },
          body: { action, comment: comment ?? null, listeningReview: listeningReview ?? null },
        },
      ),
      "Decisão da revisão do Studio",
    );
  },

  async studioAcousticAnalysisCapability(reviewId: string) {
    return requireBackendData(
      await backendClient.GET(
        "/api/v1/studios/v1/reviews/{review_id}/acoustic-analysis-capability",
        { params: { path: { review_id: reviewId } } },
      ),
      "Disponibilidade da análise acústica",
    );
  },

  async enqueueStudioAcousticAnalysis(reviewId: string, idempotencyKey: string) {
    return requireBackendData(
      await backendClient.POST(
        "/api/v1/studios/v1/reviews/{review_id}/acoustic-analyses",
        {
          params: {
            path: { review_id: reviewId },
            header: { "Idempotency-Key": idempotencyKey },
          },
        },
      ),
      "Análise de fala e música do MP4",
    );
  },

  async studioReviewPageBlob(reviewId: string, pageId: string) {
    return apiFetchBlob(`/api/v1/studios/v1/reviews/${encodeURIComponent(reviewId)}/pages/${encodeURIComponent(pageId)}/preview`);
  },

  async studioPublicationPreflight(reviewId: string) {
    return apiFetch<StudioPublicationPreflightRecord>(
      `/api/v1/studios/v1/reviews/${encodeURIComponent(reviewId)}/publication-preflight`,
    );
  },

  async scheduleStudioPublication(reviewId: string, scheduledAt: string) {
    return apiFetch<StudioInternalScheduleReceiptRecord>(
      `/api/v1/studios/v1/reviews/${encodeURIComponent(reviewId)}/internal-schedule`,
      { method: "POST", body: JSON.stringify({ scheduledAt }) },
    );
  },

  async studioPublicationPackageBlob(reviewId: string) {
    return apiFetchBlob(
      `/api/v1/studios/v1/reviews/${encodeURIComponent(reviewId)}/publication-package`,
    );
  },

  async exportStudioDocument(documentId: string, format: "png" | "png_set") {
    return requireBackendData(
      await backendClient.POST(
        "/api/v1/studios/v1/documents/{document_id}/exports",
        {
          params: { path: { document_id: documentId } },
          body: { format },
        },
      ),
      "Exportação do Studio",
    );
  },

  async studioMediaIngests(workspaceId: string) {
    return requireBackendData(
      await backendClient.GET("/api/v1/studios/v1/media-ingests", {
        params: { query: { workspace_id: workspaceId } },
      }),
      "Mídias do Studio",
    );
  },

  async studioMediaIngest(ingestId: string) {
    return requireBackendData(
      await backendClient.GET("/api/v1/studios/v1/media-ingests/{ingest_id}", {
        params: { path: { ingest_id: ingestId } },
      }),
      "Mídia ingerida do Studio",
    );
  },

  async uploadStudioAsset(workspaceId: string, file: File, title = file.name) {
    const body = new FormData();
    body.set("workspace_id", workspaceId);
    body.set("title", title);
    body.set("tags", "studio,ugc,source");
    body.set("file", file);
    return apiFetch<AssetRecord>("/api/v1/assets/upload", { method: "POST", body });
  },

  async studioAssetBlob(assetId: string, signal?: AbortSignal) {
    return apiFetchBlob(`/api/v1/assets/${assetId}/content`, signal);
  },

  async studioAssetJson<T>(assetId: string): Promise<T> {
    const blob = await this.studioAssetBlob(assetId);
    return JSON.parse(await blob.text()) as T;
  },

  async deriveStudioImage(assetId: string, input: StudioImageDerivationCreate) {
    return requireBackendData(
      await backendClient.POST("/api/v1/assets/{asset_id}/derive", {
        params: { path: { asset_id: assetId } },
        body: input,
      }),
      "Derivação não destrutiva da imagem",
    );
  },

  async enqueueStudioMediaIngest(
    input: StudioMediaIngestCreate,
    idempotencyKey: string,
  ) {
    return requireBackendData(
      await backendClient.POST("/api/v1/studios/v1/media-ingests", {
        params: { header: { "Idempotency-Key": idempotencyKey } },
        body: input,
      }),
      "Ingestão de mídia do Studio",
    );
  },

  async enqueueStudioMediaProxy(
    ingestId: string,
    input: BackendSchema<"CreateMediaProxyRequest">,
    idempotencyKey: string,
  ) {
    return requireBackendData(
      await backendClient.POST(
        "/api/v1/studios/v1/media-ingests/{ingest_id}/proxy",
        {
          params: {
            path: { ingest_id: ingestId },
            header: { "Idempotency-Key": idempotencyKey },
          },
          body: input,
        },
      ),
      "Proxy editável do Studio",
    );
  },

  async enqueueStudioMediaWaveform(
    ingestId: string,
    input: BackendSchema<"CreateAudioWaveformRequest">,
    idempotencyKey: string,
  ) {
    return requireBackendData(
      await backendClient.POST(
        "/api/v1/studios/v1/media-ingests/{ingest_id}/waveform",
        {
          params: {
            path: { ingest_id: ingestId },
            header: { "Idempotency-Key": idempotencyKey },
          },
          body: input,
        },
      ),
      "Waveform editável do Studio",
    );
  },

  async studioTranscripts(workspaceId: string, mediaIngestId?: string) {
    return requireBackendData(
      await backendClient.GET("/api/v1/studios/v1/transcripts", {
        params: {
          query: {
            workspace_id: workspaceId,
            media_ingest_id: mediaIngestId,
          },
        },
      }),
      "Transcrições do Studio",
    );
  },

  async createStudioTranscript(
    input: StudioTranscriptCreate,
    idempotencyKey: string,
  ) {
    return requireBackendData(
      await backendClient.POST("/api/v1/studios/v1/transcripts", {
        params: { header: { "Idempotency-Key": idempotencyKey } },
        body: input,
      }),
      "Criação da transcrição do Studio",
    );
  },

  async applyStudioTranscriptCaptions(
    transcriptId: string,
    input: BackendSchema<"ApplyTranscriptCaptionsRequest">,
  ) {
    return requireBackendData(
      await backendClient.POST(
        "/api/v1/studios/v1/transcripts/{transcript_id}/apply-captions",
        {
          params: { path: { transcript_id: transcriptId } },
          body: input,
        },
      ),
      "Aplicação das legendas do Studio",
    );
  },

  async studioEditDecisionSets(workspaceId: string, mediaIngestId?: string) {
    return requireBackendData(
      await backendClient.GET("/api/v1/studios/v1/edit-decision-sets", {
        params: {
          query: {
            workspace_id: workspaceId,
            media_ingest_id: mediaIngestId,
          },
        },
      }),
      "Decisões de edição do Studio",
    );
  },

  async createStudioEditDecisionSet(
    input: StudioEditDecisionCreate,
    idempotencyKey: string,
  ) {
    return requireBackendData(
      await backendClient.POST("/api/v1/studios/v1/edit-decision-sets", {
        params: { header: { "Idempotency-Key": idempotencyKey } },
        body: input,
      }),
      "Criação das decisões de edição",
    );
  },

  async replaceStudioEditDecisionSet(
    decisionSetId: string,
    expectedRevision: number,
    decisionSet: StudioEditDecisionRecord,
  ) {
    return requireBackendData(
      await backendClient.PUT(
        "/api/v1/studios/v1/edit-decision-sets/{decision_set_id}",
        {
          params: { path: { decision_set_id: decisionSetId } },
          body: { expectedRevision, decisionSet },
        },
      ),
      "Atualização das decisões de edição",
    );
  },

  async applyStudioEditDecisionSet(
    decisionSetId: string,
    input: BackendSchema<"ApplyEditDecisionSetRequest">,
  ) {
    return requireBackendData(
      await backendClient.POST(
        "/api/v1/studios/v1/edit-decision-sets/{decision_set_id}/apply",
        {
          params: { path: { decision_set_id: decisionSetId } },
          body: input,
        },
      ),
      "Aplicação dos cortes do Studio",
    );
  },

  async enqueueStudioVideoRender(
    input: StudioVideoRenderCreate,
    idempotencyKey: string,
  ) {
    return requireBackendData(
      await backendClient.POST("/api/v1/studios/v1/video-renders", {
        params: { header: { "Idempotency-Key": idempotencyKey } },
        body: input,
      }),
      "Renderização de vídeo do Studio",
    );
  },

  async studioGenerationJob(jobId: string) {
    return requireBackendData(
      await backendClient.GET("/api/v1/studios/v1/jobs/{job_id}", {
        params: { path: { job_id: jobId } },
      }),
      "Job de geração do Studio",
    );
  },

  async studioGenerationJobs(
    workspaceId: string,
    filters: { documentId?: string; jobType?: string; limit?: number } = {},
  ) {
    return requireBackendData(
      await backendClient.GET("/api/v1/studios/v1/jobs", {
        params: {
          query: {
            workspace_id: workspaceId,
            document_id: filters.documentId,
            job_type: filters.jobType,
            limit: filters.limit ?? 20,
          },
        },
      }),
      "Jobs observáveis do Studio",
    );
  },

  async enqueueStudioGenerationJob(
    input: StudioGenerationJobCreate,
    idempotencyKey: string,
  ) {
    return requireBackendData(
      await backendClient.POST("/api/v1/studios/v1/jobs", {
        params: { header: { "Idempotency-Key": idempotencyKey } },
        body: input,
      }),
      "Criação do job do Studio",
    );
  },

  async cancelStudioGenerationJob(jobId: string, reason = "Cancelado pelo usuário") {
    return requireBackendData(
      await backendClient.POST("/api/v1/studios/v1/jobs/{job_id}/cancel", {
        params: { path: { job_id: jobId } },
        body: { reason },
      }),
      "Cancelamento do job do Studio",
    );
  },

  async retryStudioGenerationJob(jobId: string) {
    return requireBackendData(
      await backendClient.POST("/api/v1/studios/v1/jobs/{job_id}/retry", {
        params: { path: { job_id: jobId } },
      }),
      "Nova tentativa do job do Studio",
    );
  },

  async exportCreative(
    documentId: string,
    format: "png" | "jpeg",
    quality = 92,
  ) {
    return requireBackendData(
      await backendClient.POST("/api/v1/creatives/{document_id}/export", {
        params: { path: { document_id: documentId } },
        body: { format, quality },
      }),
      "Exportação criativa",
    );
  },

  async createAsset(input: AssetInput) {
    return requireBackendData(
      await backendClient.POST("/api/v1/assets", { body: input }),
      "Criação de asset",
    );
  },

  async reusePost(postId: string, input: HistoryReuseInput = {}) {
    return apiFetch<PostRecord>(
      `/api/v1/history/posts/${encodeURIComponent(postId)}/reuse`,
      { method: "POST", body: JSON.stringify(input) },
    );
  },

  async reuseCampaign(campaignId: string, title?: string) {
    return requireBackendData(
      await backendClient.POST(
        "/api/v1/history/campaigns/{campaign_id}/reuse",
        {
          params: { path: { campaign_id: campaignId } },
          body: { title },
        },
      ),
      "Reutilização de campanha",
    );
  },

  async reuseCreative(creativeId: string, title?: string) {
    return requireBackendData(
      await backendClient.POST(
        "/api/v1/history/creatives/{creative_id}/reuse",
        {
          params: { path: { creative_id: creativeId } },
          body: { title },
        },
      ),
      "Reutilização criativa",
    );
  },

  async recordRadarFeedback(input: RadarFeedbackInput) {
    const result = await backendClient.POST("/api/v1/radar/feedback", {
      body: input,
    });
    requireBackendSuccess(result, "Feedback do Radar");
  },

  async removePost(postId: string) {
    const result = await backendClient.DELETE("/api/v1/posts/{post_id}", {
      params: { path: { post_id: postId } },
    });
    requireBackendSuccess(result, "Exclusão de conteúdo");
  },

  async removeCreative(documentId: string) {
    const result = await backendClient.DELETE(
      "/api/v1/creatives/{document_id}",
      {
        params: { path: { document_id: documentId } },
      },
    );
    requireBackendSuccess(result, "Exclusão do documento criativo");
  },

  async removeAsset(assetId: string) {
    const result = await backendClient.DELETE("/api/v1/assets/{asset_id}", {
      params: { path: { asset_id: assetId } },
    });
    requireBackendSuccess(result, "Exclusão do asset");
  },
};
