import {
  backendClient,
  requireBackendData,
  requireBackendSuccess,
  type BackendSchema,
} from "./client";

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
export type CreativeRecord = BackendSchema<"CreativeDocumentOut">;
export type CreativeInput = BackendSchema<"CreativeDocumentIn">;
export type CreativeUpdate = BackendSchema<"CreativeDocumentUpdate">;
export type CreativeCanvas = BackendSchema<"CreativeCanvas">;
export type AssetRecord = BackendSchema<"AssetOut">;
export type AssetInput = BackendSchema<"AssetIn">;
export type AnalyticsRecord = BackendSchema<"AnalyticsSummaryOut">;
export type RadarRecord = BackendSchema<"RadarStateOut">;
export type RadarFeedbackInput = BackendSchema<"FeedbackIn">;
export type WorkspaceResourceRecord = BackendSchema<"WorkspaceResourceOut">;
export type WorkspaceResourceInput = BackendSchema<"WorkspaceResourceIn">;
export type WorkspaceResourceUpdate = BackendSchema<"WorkspaceResourceUpdate">;

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
    ]);

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

  async reusePost(postId: string, title?: string) {
    return requireBackendData(
      await backendClient.POST("/api/v1/history/posts/{post_id}/reuse", {
        params: { path: { post_id: postId } },
        body: { title },
      }),
      "Reutilização de conteúdo",
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
