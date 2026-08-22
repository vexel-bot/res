from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


def to_camel(value: str) -> str:
    parts = value.split("_")
    return parts[0] + "".join(part.capitalize() for part in parts[1:])


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, alias_generator=to_camel, populate_by_name=True)


class UserOut(APIModel):
    id: str
    email: EmailStr
    name: str


class RegisterIn(APIModel):
    email: EmailStr
    name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=12, max_length=128)
    workspace_name: str = Field(min_length=2, max_length=120)


class LoginIn(APIModel):
    email: EmailStr
    password: str


class PasswordChangeIn(APIModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=12, max_length=128)


class ProfileUpdateIn(APIModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr


class TokenOut(APIModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class BrandProfileIn(APIModel):
    name: str = Field(min_length=1, max_length=120)
    industry: str = Field(default="", max_length=120)
    regions: list[str] = Field(default_factory=lambda: ["BR"])
    languages: list[str] = Field(default_factory=lambda: ["pt-BR"])
    tone: str = ""
    target_audience: str = ""
    keywords: list[str] = Field(default_factory=list)
    do_and_donts: str = ""
    primary_color: str = "#6366f1"
    products: list[dict[str, Any]] = Field(default_factory=list)
    pillars: list[str] = Field(default_factory=list)
    watchlist: dict[str, Any] = Field(default_factory=dict)
    prohibited_topics: list[str] = Field(default_factory=list)


class BrandProfileOut(BrandProfileIn):
    id: str
    workspace_id: str
    versions: list[dict[str, Any]] = Field(default_factory=list)


class BrandReadinessGapOut(APIModel):
    field: str
    label: str
    impact: Literal["high", "medium", "low"]
    weight: int = Field(ge=1, le=100)
    reason: str


class BrandReadinessOut(APIModel):
    workspace_id: str
    percentage: int = Field(ge=0, le=100)
    status: Literal["incomplete", "usable", "ready"]
    completed_fields: list[str]
    missing_fields: list[BrandReadinessGapOut]
    revision: int = Field(ge=1)
    version_count: int = Field(ge=0)
    updated_at: datetime


class BrandVersionOut(APIModel):
    number: int = Field(ge=1)
    label: str
    created_at: datetime
    profile: dict[str, Any]


class WorkspaceCreate(APIModel):
    name: str = Field(min_length=2, max_length=120)


class WorkspaceUpdate(APIModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    avatar: str | None = Field(default=None, max_length=500)
    brand_profile: BrandProfileIn | None = None


class WorkspaceOut(APIModel):
    id: str
    name: str
    avatar: str
    plan: str
    members_count: int
    role: str
    brand_profile: BrandProfileOut


class WorkspaceResourceIn(APIModel):
    workspace_id: str
    kind: Literal[
        "template",
        "connected_account",
        "automation",
        "video_project",
        "ai_chat",
        "presenter_session",
    ]
    resource_key: str = Field(min_length=1, max_length=120)
    payload: dict[str, Any] = Field(default_factory=dict)


class WorkspaceResourceUpdate(APIModel):
    payload: dict[str, Any]


class WorkspaceResourceOut(APIModel):
    id: str
    workspace_id: str
    kind: str
    resource_key: str
    payload: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class MemberInviteIn(APIModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    modules: list[str] = Field(default_factory=list, max_length=32)


class MemberUpdateIn(APIModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    status: Literal["active", "disabled"] | None = None
    modules: list[str] | None = Field(default=None, max_length=32)


class PlanUpdateIn(APIModel):
    plan_id: Literal["solo", "team", "business", "enterprise"]


class UserSettingsIn(APIModel):
    settings: dict[str, Any] = Field(default_factory=dict)
    auxiliary: dict[str, Any] = Field(default_factory=dict)


class SupportTicketIn(APIModel):
    subject: Literal["technical", "billing", "account", "feature"]
    title: str = Field(min_length=3, max_length=160)
    details: str = Field(min_length=10, max_length=8000)


class CompanySettingsIn(APIModel):
    legal_name: str = Field(default="", max_length=200)
    brand_name: str = Field(default="", max_length=120)
    tax_id: str = Field(default="", max_length=40)
    site: str = Field(default="", max_length=500)
    email: str = Field(default="", max_length=254)
    phone: str = Field(default="", max_length=40)
    language: str = Field(default="pt-BR", max_length=20)
    timezone: str = Field(default="America/Sao_Paulo", max_length=80)


class PostIn(APIModel):
    workspace_id: str
    title: str = Field(min_length=1, max_length=240)
    platform: str = Field(min_length=1, max_length=32)
    format: str = Field(min_length=1, max_length=32)
    copy: str = ""
    hashtags: list[str] = Field(default_factory=list)
    image_url: str | None = None
    video_url: str | None = None
    slides: list[dict[str, Any]] | None = None
    scheduled_at: datetime | None = None
    status: Literal[
        "draft", "in_review", "pending_approval", "approved", "changes_requested", "rejected", "scheduled", "published"
    ] = "draft"
    author: str = Field(default="Usuário", max_length=120)
    ai_score: float | None = Field(default=None, ge=0, le=100)
    campaign_id: str | None = None
    strategy_id: str | None = None
    brain_revision: int | None = Field(default=None, ge=1)
    objective: str | None = None
    origin: Literal["manual", "brain", "strategy", "automation", "analytics"] | None = None
    versions: list[dict[str, Any]] = Field(default_factory=list)


class PostOut(PostIn):
    id: str
    created_at: datetime
    likes: int | None = None
    comments: int | None = None
    shares: int | None = None
    reach: int | None = None
    impressions: int | None = None
    saves: int | None = None
    clicks: int | None = None
    conversions: int | None = None


class PostUpdate(APIModel):
    title: str | None = Field(default=None, min_length=1, max_length=240)
    platform: str | None = Field(default=None, min_length=1, max_length=32)
    format: str | None = Field(default=None, min_length=1, max_length=32)
    copy: str | None = None
    hashtags: list[str] | None = None
    image_url: str | None = None
    video_url: str | None = None
    slides: list[dict[str, Any]] | None = None
    scheduled_at: datetime | None = None
    status: (
        Literal[
            "draft",
            "in_review",
            "pending_approval",
            "approved",
            "changes_requested",
            "rejected",
            "scheduled",
            "published",
        ]
        | None
    ) = None
    author: str | None = Field(default=None, max_length=120)
    ai_score: float | None = Field(default=None, ge=0, le=100)
    campaign_id: str | None = None
    strategy_id: str | None = None
    brain_revision: int | None = Field(default=None, ge=1)
    objective: str | None = None
    origin: Literal["manual", "brain", "strategy", "automation", "analytics"] | None = None
    versions: list[dict[str, Any]] | None = None


class ApprovalActionIn(APIModel):
    action: Literal["approve", "request_changes", "reject", "publish", "schedule", "comment"]
    comment: str | None = Field(default=None, max_length=4000)
    scheduled_at: datetime | None = None

    @model_validator(mode="after")
    def validate_action_fields(self):
        if self.action == "comment" and not (self.comment or "").strip():
            raise ValueError("Comment action requires a message")
        if self.action == "schedule" and self.scheduled_at is None:
            raise ValueError("Schedule action requires a publication date")
        if self.action == "schedule" and self.scheduled_at is not None:
            scheduled_at = self.scheduled_at
            if scheduled_at.tzinfo is None:
                scheduled_at = scheduled_at.replace(tzinfo=UTC)
            if scheduled_at <= datetime.now(UTC):
                raise ValueError("Schedule action requires a future publication date")
        return self


class ApprovalEventOut(APIModel):
    id: str
    workspace_id: str
    post_id: str
    actor_id: str | None
    actor_name: str
    event_type: str
    action: str
    detail: str
    created_at: datetime


class ApprovalActionOut(APIModel):
    post: PostOut
    event: ApprovalEventOut


class CampaignIn(APIModel):
    workspace_id: str
    opportunity_id: str | None = None
    origin_context: dict[str, Any] = Field(default_factory=dict)
    name: str = Field(min_length=1, max_length=240)
    objective: str = ""
    start_date: str = ""
    end_date: str = ""
    budget: str = ""
    kpis: list[str] = Field(default_factory=list)
    products: str = ""
    audience: str = ""
    offer: str = ""
    promise: str = ""
    proof: str = ""
    emotion: str = ""
    constraints: str = ""
    formats: list[str] = Field(default_factory=list)
    format_suggestions: list[str] = Field(default_factory=list)
    cta: str = ""
    channels: list[str] = Field(default_factory=list)
    important_dates: str = ""
    funnel: str = ""
    ctas: list[str] = Field(default_factory=list)
    execution_plan: list[str] = Field(default_factory=list)
    big_idea: str = ""
    central_message: str = ""
    angles: list[str] = Field(default_factory=list, max_length=5)
    hooks: list[str] = Field(default_factory=list)
    narrative_sequence: list[str] = Field(default_factory=list)
    creative_matrix: list[dict[str, Any]] = Field(default_factory=list)
    status: Literal["draft", "planned", "active", "completed"] = "draft"
    brain_revision: int = Field(default=1, ge=1)


class CampaignUpdate(APIModel):
    origin_context: dict[str, Any] | None = None
    name: str | None = Field(default=None, min_length=1, max_length=240)
    objective: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    budget: str | None = None
    kpis: list[str] | None = None
    products: str | None = None
    audience: str | None = None
    offer: str | None = None
    promise: str | None = None
    proof: str | None = None
    emotion: str | None = None
    constraints: str | None = None
    formats: list[str] | None = None
    cta: str | None = None
    channels: list[str] | None = None
    important_dates: str | None = None
    funnel: str | None = None
    ctas: list[str] | None = None
    execution_plan: list[str] | None = None
    big_idea: str | None = None
    central_message: str | None = None
    angles: list[str] | None = Field(default=None, max_length=5)
    hooks: list[str] | None = None
    narrative_sequence: list[str] | None = None
    creative_matrix: list[dict[str, Any]] | None = None
    format_suggestions: list[str] | None = None
    status: Literal["draft", "planned", "active", "completed"] | None = None


class CampaignOut(CampaignIn):
    id: str
    versions: list[dict[str, Any]] = Field(default_factory=list)
    decisions: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class CampaignDecisionIn(APIModel):
    decision_type: Literal["approved", "rejected", "changed", "paused", "resumed"]
    summary: str = Field(min_length=1, max_length=500)
    rationale: str | None = Field(default=None, max_length=2000)


class CampaignVersionIn(APIModel):
    label: str = Field(default="Versão salva", min_length=1, max_length=120)


class CreativeLayerBase(APIModel):
    id: str = Field(min_length=1, max_length=80)
    name: str = Field(default="Camada", min_length=1, max_length=120)
    x: float = Field(ge=-4096, le=8192)
    y: float = Field(ge=-4096, le=8192)
    width: float = Field(gt=0, le=4096)
    height: float = Field(gt=0, le=4096)
    rotation: float = Field(default=0, ge=-360, le=360)
    opacity: float = Field(default=1, ge=0, le=1)
    visible: bool = True
    locked: bool = False
    z_index: int = Field(default=0, ge=0, le=500)


class CreativeTextLayer(CreativeLayerBase):
    type: Literal["text"]
    text: str = Field(default="Texto", max_length=2000)
    font_size: int = Field(default=64, ge=8, le=400)
    min_font_size: int = Field(default=18, ge=8, le=200)
    font_family: str = Field(default="DejaVu Sans", max_length=120)
    font_weight: Literal["normal", "bold"] = "bold"
    color: str = Field(default="#ffffff", pattern=r"^#[0-9a-fA-F]{6}$")
    align: Literal["left", "center", "right"] = "left"
    line_height: float = Field(default=1.15, ge=0.8, le=2)


class CreativeShapeLayer(CreativeLayerBase):
    type: Literal["shape"]
    shape: Literal["rectangle", "ellipse"] = "rectangle"
    fill: str = Field(default="#6366f1", pattern=r"^#[0-9a-fA-F]{6}$")
    radius: int = Field(default=0, ge=0, le=500)


class CreativeImageLayer(CreativeLayerBase):
    type: Literal["image"]
    asset_id: str
    fit: Literal["cover", "contain"] = "cover"


CreativeLayer = CreativeTextLayer | CreativeShapeLayer | CreativeImageLayer


class CreativeCanvas(APIModel):
    schema_version: Literal["creative-v1"] = "creative-v1"
    width: int = Field(ge=320, le=4096)
    height: int = Field(ge=320, le=4096)
    safe_area: int = Field(default=48, ge=0, le=400)
    background: str = Field(default="#10181c", pattern=r"^#[0-9a-fA-F]{6}$")
    brand_tokens: dict[str, Any] = Field(default_factory=dict)
    layers: list[CreativeLayer] = Field(default_factory=list, max_length=100)


class CreativeDocumentIn(APIModel):
    workspace_id: str
    campaign_id: str | None = None
    post_id: str | None = None
    kind: Literal["document", "template"] = "document"
    title: str = Field(min_length=1, max_length=240)
    document: CreativeCanvas


class CreativeDocumentUpdate(APIModel):
    expected_updated_at: datetime | None = None
    title: str | None = Field(default=None, min_length=1, max_length=240)
    campaign_id: str | None = None
    post_id: str | None = None
    kind: Literal["document", "template"] | None = None
    document: CreativeCanvas | None = None


class CreativeDocumentOut(CreativeDocumentIn):
    id: str
    version: int
    versions: list[dict[str, Any]]
    created_at: datetime
    updated_at: datetime


class CreativeVersionIn(APIModel):
    label: str = Field(default="Versão salva", min_length=1, max_length=120)


class CreativeExportIn(APIModel):
    format: Literal["png", "jpeg"] = "png"
    quality: int = Field(default=92, ge=60, le=100)


class CampaignPiecesIn(APIModel):
    formats: list[str] = Field(default_factory=list)


class AssetIn(APIModel):
    workspace_id: str
    title: str = Field(min_length=1, max_length=240)
    type: Literal["content", "upload", "campaign", "version", "prompt", "image", "video", "template", "document"]
    tags: list[str] = Field(default_factory=list)
    campaign_id: str | None = None
    content_id: str | None = None
    url: str | None = Field(default=None, max_length=4000)


class AssetOut(AssetIn):
    id: str
    created_at: datetime
    updated_at: datetime


class KnowledgeDocumentIn(APIModel):
    workspace_id: str
    title: str = Field(min_length=1, max_length=240)
    content: str = Field(min_length=1, max_length=200_000)
    source_type: Literal["manual", "upload", "url", "brain", "import"] = "manual"
    source_url: str | None = Field(default=None, max_length=4000)
    asset_id: str | None = None
    language: str = Field(default="pt-BR", min_length=2, max_length=16)
    metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeDocumentOut(APIModel):
    id: str
    workspace_id: str
    asset_id: str | None
    title: str
    source_type: str
    source_url: str | None
    language: str
    metadata: dict[str, Any]
    status: str
    embedding_status: str
    embedding_model: str | None
    chunk_count: int
    created_at: datetime
    updated_at: datetime


class KnowledgeSearchResult(APIModel):
    document_id: str
    chunk_id: str
    title: str
    content: str
    score: float
    lexical_score: float | None
    semantic_score: float | None
    citation: dict[str, Any]


class KnowledgeSearchOut(APIModel):
    query: str
    retrieval_mode: Literal["lexical", "hybrid"]
    embedding_model: str | None
    results: list[KnowledgeSearchResult]


class BootstrapOut(APIModel):
    user: UserOut
    workspaces: list[WorkspaceOut]
    posts: list[PostOut]
    suggestions: list[dict[str, Any]]


class SignalIn(APIModel):
    workspace_id: str | None = None
    source: str = Field(min_length=2, max_length=120)
    url: str = Field(min_length=8, max_length=4000)
    title: str = Field(min_length=3, max_length=500)
    summary: str = ""
    raw_text: str = ""
    published_at: datetime
    expires_at: datetime | None = None
    language: str = "pt-BR"
    region: str = "BR"
    category: str = "general"
    topics: list[str] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)

    @field_validator("raw_text")
    @classmethod
    def cap_raw_text(cls, value: str) -> str:
        return value[:20_000]


class SignalOut(SignalIn):
    id: str
    collected_at: datetime
    expires_at: datetime
    content_hash: str
    status: str
    cluster_key: str | None


class RankRequest(APIModel):
    workspace_id: str
    signal_ids: list[str] | None = None


class RadarSourceIn(APIModel):
    workspace_id: str
    name: str = Field(min_length=2, max_length=120)
    connector_type: Literal["rss"] = "rss"
    feed_url: str = Field(min_length=8, max_length=4000)
    region: str = Field(default="BR", min_length=2, max_length=32)
    language: str = Field(default="pt-BR", min_length=2, max_length=16)
    category: str = Field(default="general", min_length=2, max_length=80)
    is_active: bool = True


class RadarSourceUpdate(APIModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    feed_url: str | None = Field(default=None, min_length=8, max_length=4000)
    region: str | None = Field(default=None, min_length=2, max_length=32)
    language: str | None = Field(default=None, min_length=2, max_length=16)
    category: str | None = Field(default=None, min_length=2, max_length=80)
    is_active: bool | None = None


class RadarSourceOut(APIModel):
    id: str
    workspace_id: str
    name: str
    connector_type: str
    feed_url: str
    region: str
    language: str
    category: str
    is_active: bool
    last_synced_at: datetime | None
    last_status: str
    last_error: str | None
    last_item_count: int
    created_at: datetime
    updated_at: datetime


class OpportunityOut(APIModel):
    id: str
    workspace_id: str
    signal_id: str
    title: str
    event_summary: str
    bridge: str
    recommended_format: str
    hook: str
    objective: str
    publish_until: datetime
    score: float
    score_breakdown: dict[str, float]
    score_version: str
    risks: list[str]
    evidence: list[dict[str, Any]]
    eligible: bool
    rejection_reason: str | None
    source: dict[str, Any] = Field(default_factory=dict)
    updated_at: datetime | None = None
    why_it_fits: str = ""
    related_context: dict[str, str] = Field(default_factory=dict)
    score_label: str = ""
    risk_level: Literal["low", "medium", "high"] = "low"
    window_label: str = ""
    saved: bool = False
    rejected: bool = False
    actions: dict[str, bool] = Field(default_factory=dict)


class RadarEvergreenSuggestionOut(APIModel):
    title: str
    rationale: str
    recommended_format: str
    objective: Literal["reach", "authority", "leads", "conversion"]
    grounded_in: list[str]


class RadarStateOut(APIModel):
    workspace_id: str
    state: Literal[
        "brand_incomplete",
        "no_sources",
        "awaiting_first_collection",
        "collecting",
        "collection_error",
        "insufficient_signals",
        "ready",
    ]
    reason: str
    last_collection_at: datetime | None
    next_collection_at: datetime | None
    collection_status: str
    sources_used: list[dict[str, Any]]
    signal_count: int = Field(ge=0)
    brand_readiness: BrandReadinessOut
    evergreen_suggestions: list[RadarEvergreenSuggestionOut]
    opportunities: list[OpportunityOut]


class FeedbackIn(APIModel):
    workspace_id: str
    opportunity_id: str | None = None
    campaign_id: str | None = None
    content_id: str | None = None
    creative_document_id: str | None = None
    event_type: Literal[
        "shown",
        "opened",
        "saved",
        "chosen",
        "rejected",
        "generated",
        "edited",
        "approved",
        "discarded",
        "published",
        "rated",
        "performance_recorded",
        "reused",
    ]
    reason: str | None = Field(default=None, max_length=2000)
    payload: dict[str, Any] = Field(default_factory=dict)


class PostMetricsIn(APIModel):
    source: Literal["manual"] = "manual"
    observed_at: datetime | None = None
    impressions: int | None = Field(default=None, ge=0, le=2_000_000_000)
    reach: int | None = Field(default=None, ge=0, le=2_000_000_000)
    likes: int | None = Field(default=None, ge=0, le=2_000_000_000)
    comments: int | None = Field(default=None, ge=0, le=2_000_000_000)
    shares: int | None = Field(default=None, ge=0, le=2_000_000_000)
    saves: int | None = Field(default=None, ge=0, le=2_000_000_000)
    clicks: int | None = Field(default=None, ge=0, le=2_000_000_000)
    conversions: int | None = Field(default=None, ge=0, le=2_000_000_000)

    @model_validator(mode="after")
    def require_metric(self):
        fields = ("impressions", "reach", "likes", "comments", "shares", "saves", "clicks", "conversions")
        if all(getattr(self, field) is None for field in fields):
            raise ValueError("At least one metric is required")
        return self


class PostMetricSnapshotOut(APIModel):
    id: str
    workspace_id: str
    post_id: str
    source: str
    metrics: dict[str, int]
    observed_at: datetime
    created_at: datetime


class PostFeedbackIn(APIModel):
    rating: int = Field(ge=1, le=5)
    reason: str | None = Field(default=None, max_length=2000)


class HistoryItemOut(APIModel):
    id: str
    resource_id: str
    workspace_id: str
    item_type: Literal["post", "campaign", "creative", "template", "asset"]
    title: str
    snippet: str
    tags: list[str]
    campaign_id: str | None = None
    reusable: bool
    version_count: int = 0
    decision_count: int = 0
    created_at: datetime
    updated_at: datetime


class HistoryReuseIn(APIModel):
    title: str | None = Field(default=None, min_length=1, max_length=240)


class LearningPreferenceOut(APIModel):
    workspace_id: str
    score_version: str
    feature_bias: dict[str, float]
    explicit_events: int
    performance_samples: int
    performance_active: bool
    status: Literal["no_feedback", "explicit_feedback", "feedback_and_performance"]


class ProductMetricOut(APIModel):
    key: str
    label: str
    value: float | int | None
    unit: str
    status: Literal["available", "insufficient_data"]
    source: Literal["observed", "user_reported", "derived"]
    sample_size: int = Field(ge=0)
    definition: str


class ActionableInsightOut(APIModel):
    key: str
    title: str
    statement: str
    recommendation: str
    evidence_type: Literal["observed", "user_reported", "insufficient_data"]
    sample_size: int = Field(ge=0)


class AnalyticsSummaryOut(APIModel):
    workspace_id: str
    generated_at: datetime
    metrics: list[ProductMetricOut]
    insights: list[ActionableInsightOut]
    weekly_campaign_activity: list[dict[str, Any]]
    rejection_reasons: list[dict[str, Any]]


class JobOut(APIModel):
    id: str
    workspace_id: str | None
    job_type: str
    idempotency_key: str
    status: str
    attempts: int
    error: str | None
    started_at: datetime | None
    finished_at: datetime | None
