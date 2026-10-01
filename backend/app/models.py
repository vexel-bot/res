from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pgvector.sqlalchemy import VECTOR
from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def new_id() -> str:
    return str(uuid4())


def utcnow() -> datetime:
    return datetime.now(UTC)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Workspace(Base, TimestampMixin):
    __tablename__ = "workspaces"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    avatar: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    plan: Mapped[str] = mapped_column(String(32), default="Growth", nullable=False)
    memberships: Mapped[list[Membership]] = relationship(back_populates="workspace", cascade="all, delete-orphan")
    brand_profile: Mapped[BrandProfile | None] = relationship(
        back_populates="workspace", cascade="all, delete-orphan", uselist=False
    )
    knowledge_documents: Mapped[list[KnowledgeDocument]] = relationship(
        back_populates="workspace", cascade="all, delete-orphan"
    )


class Membership(Base, TimestampMixin):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("user_id", "workspace_id", name="uq_membership_user_workspace"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(32), default="Owner", nullable=False)
    workspace: Mapped[Workspace] = relationship(back_populates="memberships")


class BrandProfile(Base, TimestampMixin):
    __tablename__ = "brand_profiles"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    industry: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    regions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    languages: Mapped[list[str]] = mapped_column(JSON, default=lambda: ["pt-BR"], nullable=False)
    tone: Mapped[str] = mapped_column(Text, default="", nullable=False)
    target_audience: Mapped[str] = mapped_column(Text, default="", nullable=False)
    keywords: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    do_and_donts: Mapped[str] = mapped_column(Text, default="", nullable=False)
    primary_color: Mapped[str] = mapped_column(String(16), default="#6366f1", nullable=False)
    products: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    pillars: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    watchlist: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    prohibited_topics: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    versions: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    workspace: Mapped[Workspace] = relationship(back_populates="brand_profile")


class Post(Base, TimestampMixin):
    __tablename__ = "posts"
    __table_args__ = (Index("ix_posts_workspace_created", "workspace_id", "created_at"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    format: Mapped[str] = mapped_column(String(32), nullable=False)
    copy: Mapped[str] = mapped_column(Text, default="", nullable=False)
    hashtags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    image_url: Mapped[str | None] = mapped_column(Text)
    video_url: Mapped[str | None] = mapped_column(Text)
    slides: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    author: Mapped[str] = mapped_column(String(120), nullable=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    ai_score: Mapped[float | None] = mapped_column(Float)
    campaign_id: Mapped[str | None] = mapped_column(
        ForeignKey("campaigns.id", ondelete="SET NULL", name="fk_posts_campaign_id"), index=True
    )
    strategy_id: Mapped[str | None] = mapped_column(String(36), index=True)
    brain_revision: Mapped[int | None] = mapped_column(Integer)
    objective: Mapped[str | None] = mapped_column(Text)
    origin: Mapped[str | None] = mapped_column(String(32))
    versions: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)


class ApprovalEvent(Base):
    __tablename__ = "approval_events"
    __table_args__ = (Index("ix_approval_events_workspace_post_created", "workspace_id", "post_id", "created_at"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    post_id: Mapped[str] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"), index=True)
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    actor_name: Mapped[str] = mapped_column(String(120), nullable=False)
    event_type: Mapped[str] = mapped_column(String(24), nullable=False)
    action: Mapped[str] = mapped_column(String(48), nullable=False)
    detail: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)


class ExternalSignal(Base, TimestampMixin):
    __tablename__ = "external_signals"
    __table_args__ = (
        UniqueConstraint("workspace_id", "source", "content_hash", name="uq_signal_workspace_source_hash"),
        Index("ix_signals_workspace_published", "workspace_id", "published_at"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str | None] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    source: Mapped[str] = mapped_column(String(120), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    language: Mapped[str] = mapped_column(String(16), default="pt-BR", nullable=False)
    region: Mapped[str] = mapped_column(String(32), default="BR", nullable=False)
    category: Mapped[str] = mapped_column(String(80), default="general", nullable=False)
    topics: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    entities: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="normalized", nullable=False)
    cluster_key: Mapped[str | None] = mapped_column(String(64), index=True)
    schema_version: Mapped[str] = mapped_column(String(32), default="radar.signal.v1", nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), default="external", nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float)
    knowledge_type: Mapped[str] = mapped_column(String(32), default="fact", nullable=False)
    provider_trace: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class RadarSource(Base, TimestampMixin):
    __tablename__ = "radar_sources"
    __table_args__ = (
        UniqueConstraint("workspace_id", "feed_url", name="uq_radar_source_workspace_feed"),
        Index("ix_radar_sources_workspace_active", "workspace_id", "is_active"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    connector_type: Mapped[str] = mapped_column(String(32), default="rss", nullable=False)
    feed_url: Mapped[str] = mapped_column(Text, nullable=False)
    region: Mapped[str] = mapped_column(String(32), default="BR", nullable=False)
    language: Mapped[str] = mapped_column(String(16), default="pt-BR", nullable=False)
    category: Mapped[str] = mapped_column(String(80), default="general", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_status: Mapped[str] = mapped_column(String(32), default="never", nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text)
    last_item_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class Opportunity(Base, TimestampMixin):
    __tablename__ = "opportunities"
    __table_args__ = (Index("ix_opportunities_workspace_score", "workspace_id", "score"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    signal_id: Mapped[str] = mapped_column(ForeignKey("external_signals.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    event_summary: Mapped[str] = mapped_column(Text, nullable=False)
    bridge: Mapped[str] = mapped_column(Text, nullable=False)
    recommended_format: Mapped[str] = mapped_column(String(80), nullable=False)
    hook: Mapped[str] = mapped_column(Text, nullable=False)
    objective: Mapped[str] = mapped_column(String(32), nullable=False)
    publish_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    score_breakdown: Mapped[dict[str, float]] = mapped_column(JSON, nullable=False)
    score_version: Mapped[str] = mapped_column(String(32), nullable=False)
    risks: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    evidence: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    eligible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    rejection_reason: Mapped[str | None] = mapped_column(Text)


class Campaign(Base, TimestampMixin):
    __tablename__ = "campaigns"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    opportunity_id: Mapped[str | None] = mapped_column(ForeignKey("opportunities.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    brief: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    strategy: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_trace: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    versions: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    decisions: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)


class CreativeDocument(Base, TimestampMixin):
    __tablename__ = "creative_documents"
    __table_args__ = (Index("ix_creative_documents_workspace_updated", "workspace_id", "updated_at"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    campaign_id: Mapped[str | None] = mapped_column(ForeignKey("campaigns.id", ondelete="SET NULL"), index=True)
    post_id: Mapped[str | None] = mapped_column(ForeignKey("posts.id", ondelete="SET NULL"), index=True)
    kind: Mapped[str] = mapped_column(String(16), default="document", nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    document: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    schema_version: Mapped[str] = mapped_column(String(64), default="creative-v1", nullable=False)
    canonical_document: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    correlation_id: Mapped[str | None] = mapped_column(String(128), index=True)
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    studio_creation_key: Mapped[str | None] = mapped_column(String(300), unique=True, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    versions: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)


class LibraryAsset(Base, TimestampMixin):
    __tablename__ = "library_assets"
    __table_args__ = (Index("ix_library_assets_workspace_created", "workspace_id", "created_at"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    asset_type: Mapped[str] = mapped_column("type", String(32), nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    campaign_id: Mapped[str | None] = mapped_column(ForeignKey("campaigns.id", ondelete="SET NULL"), index=True)
    content_id: Mapped[str | None] = mapped_column(ForeignKey("posts.id", ondelete="SET NULL"), index=True)
    url: Mapped[str | None] = mapped_column(Text)
    storage_key: Mapped[str | None] = mapped_column(String(120), unique=True)
    storage_backend: Mapped[str] = mapped_column(String(32), default="local", nullable=False)
    media_type: Mapped[str | None] = mapped_column(String(160))
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), index=True)
    object_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict, nullable=False)
    lifecycle_status: Mapped[str] = mapped_column(String(32), default="active", nullable=False, index=True)
    legal_hold: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    legal_hold_reason: Mapped[str | None] = mapped_column(Text)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deletion_receipt: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


EMBEDDING_DIMENSIONS = 1536


class KnowledgeDocument(Base, TimestampMixin):
    __tablename__ = "knowledge_documents"
    __table_args__ = (
        UniqueConstraint("workspace_id", "content_hash", name="uq_knowledge_document_workspace_hash"),
        Index("ix_knowledge_documents_workspace_created", "workspace_id", "created_at"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    asset_id: Mapped[str | None] = mapped_column(ForeignKey("library_assets.id", ondelete="SET NULL"), index=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(16), default="pt-BR", nullable=False)
    document_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="ready", nullable=False)
    embedding_status: Mapped[str] = mapped_column(String(32), default="unconfigured", nullable=False)
    embedding_model: Mapped[str | None] = mapped_column(String(160))
    workspace: Mapped[Workspace] = relationship(back_populates="knowledge_documents")
    chunks: Mapped[list[KnowledgeChunk]] = relationship(
        back_populates="document", cascade="all, delete-orphan", order_by="KnowledgeChunk.chunk_index"
    )


class KnowledgeChunk(Base, TimestampMixin):
    __tablename__ = "knowledge_chunks"
    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_knowledge_chunk_document_index"),
        Index("ix_knowledge_chunks_workspace_document", "workspace_id", "document_id"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    document_id: Mapped[str] = mapped_column(ForeignKey("knowledge_documents.id", ondelete="CASCADE"), index=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    char_start: Mapped[int] = mapped_column(Integer, nullable=False)
    char_end: Mapped[int] = mapped_column(Integer, nullable=False)
    citation: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(
        VECTOR(EMBEDDING_DIMENSIONS).with_variant(JSON(), "sqlite"), nullable=True
    )
    document: Mapped[KnowledgeDocument] = relationship(back_populates="chunks")


class FeedbackEvent(Base):
    __tablename__ = "feedback_events"
    __table_args__ = (Index("ix_feedback_events_workspace_type_occurred", "workspace_id", "event_type", "occurred_at"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    opportunity_id: Mapped[str | None] = mapped_column(ForeignKey("opportunities.id", ondelete="SET NULL"), index=True)
    campaign_id: Mapped[str | None] = mapped_column(ForeignKey("campaigns.id", ondelete="SET NULL"), index=True)
    content_id: Mapped[str | None] = mapped_column(ForeignKey("posts.id", ondelete="SET NULL"), index=True)
    creative_document_id: Mapped[str | None] = mapped_column(
        ForeignKey("creative_documents.id", ondelete="SET NULL"), index=True
    )
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    event_type: Mapped[str] = mapped_column(String(48), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    schema_version: Mapped[str] = mapped_column(String(32), default="feedback.v1", nullable=False)
    opportunity_score_version: Mapped[str | None] = mapped_column(String(32))
    object_version: Mapped[int | None] = mapped_column(Integer)


class PostMetricSnapshot(Base):
    __tablename__ = "post_metric_snapshots"
    __table_args__ = (Index("ix_post_metric_snapshots_workspace_observed", "workspace_id", "observed_at"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    post_id: Mapped[str] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"), index=True)
    recorded_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    source: Mapped[str] = mapped_column(String(32), default="manual", nullable=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class JobAudit(Base):
    __tablename__ = "job_audits"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str | None] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    job_type: Mapped[str] = mapped_column(String(80), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="queued", nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class StudioGenerationJob(Base, TimestampMixin):
    __tablename__ = "studio_generation_jobs"
    __table_args__ = (
        UniqueConstraint("workspace_id", "job_type", "idempotency_key", name="uq_studio_job_scope_key"),
        Index("ix_studio_jobs_workspace_status", "workspace_id", "status"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    requested_by: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    document_id: Mapped[str | None] = mapped_column(
        ForeignKey("creative_documents.id", ondelete="SET NULL"), index=True
    )
    consent_grant_id: Mapped[str | None] = mapped_column(
        ForeignKey("studio_consent_grants.id", ondelete="SET NULL"), index=True
    )
    identity_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("studio_identity_versions.id", ondelete="SET NULL"), index=True
    )
    voice_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("studio_voice_versions.id", ondelete="SET NULL"), index=True
    )
    job_type: Mapped[str] = mapped_column(String(80), nullable=False)
    provider: Mapped[str] = mapped_column(String(120), nullable=False)
    execution_capability: Mapped[str] = mapped_column(String(32), default="control", nullable=False)
    queue_name: Mapped[str] = mapped_column(String(80), default="studio.cpu", nullable=False)
    resource_class: Mapped[str] = mapped_column(String(80), default="cpu.standard", nullable=False)
    hard_time_limit_seconds: Mapped[int] = mapped_column(Integer, default=300, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(160), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="queued", nullable=False)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    request_payload: Mapped[dict[str, Any]] = mapped_column("request", JSON, default=dict, nullable=False)
    result_payload: Mapped[dict[str, Any] | None] = mapped_column("result", JSON)
    error_code: Mapped[str | None] = mapped_column(String(120))
    error_message: Mapped[str | None] = mapped_column(Text)
    cancel_reason: Mapped[str | None] = mapped_column(Text)
    worker_execution_context: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class StudioMediaIngest(Base, TimestampMixin):
    __tablename__ = "studio_media_ingests"
    __table_args__ = (
        UniqueConstraint("workspace_id", "idempotency_key", name="uq_studio_media_ingest_scope_key"),
        Index("ix_studio_media_ingests_workspace_status", "workspace_id", "status"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    asset_id: Mapped[str] = mapped_column(ForeignKey("library_assets.id", ondelete="RESTRICT"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    probe_provider: Mapped[str] = mapped_column(String(120), default="builtin.ffprobe", nullable=False)
    media_info: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    validation_errors: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    proxy_asset_id: Mapped[str | None] = mapped_column(
        ForeignKey("library_assets.id", ondelete="SET NULL"), index=True
    )
    waveform_asset_id: Mapped[str | None] = mapped_column(
        ForeignKey("library_assets.id", ondelete="SET NULL"), index=True
    )
    proxy_time_map: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    generation_job_id: Mapped[str | None] = mapped_column(
        ForeignKey("studio_generation_jobs.id", ondelete="SET NULL"), index=True
    )
    idempotency_key: Mapped[str] = mapped_column(String(160), nullable=False)
    requested_by: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)


class StudioTranscript(Base, TimestampMixin):
    __tablename__ = "studio_transcripts"
    __table_args__ = (
        UniqueConstraint("workspace_id", "idempotency_key", name="uq_studio_transcript_scope_key"),
        Index("ix_studio_transcripts_workspace_status", "workspace_id", "status"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    media_ingest_id: Mapped[str] = mapped_column(
        ForeignKey("studio_media_ingests.id", ondelete="CASCADE"), index=True
    )
    asset_id: Mapped[str] = mapped_column(ForeignKey("library_assets.id", ondelete="RESTRICT"), index=True)
    locale: Mapped[str] = mapped_column(String(32), default="pt-BR", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    provider: Mapped[str] = mapped_column(String(120), default="manual", nullable=False)
    provider_version: Mapped[str | None] = mapped_column(String(240))
    source_checksum_sha256: Mapped[str | None] = mapped_column(String(64))
    provenance: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    metrics: Mapped[dict[str, float]] = mapped_column(JSON, default=dict, nullable=False)
    transcript_document: Mapped[dict[str, Any]] = mapped_column("document", JSON, nullable=False)
    versions: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(160), nullable=False)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    updated_by: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)


class StudioEditDecisionSet(Base, TimestampMixin):
    __tablename__ = "studio_edit_decision_sets"
    __table_args__ = (
        UniqueConstraint("workspace_id", "idempotency_key", name="uq_studio_edit_decision_scope_key"),
        Index("ix_studio_edit_decisions_workspace_status", "workspace_id", "status"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    media_ingest_id: Mapped[str] = mapped_column(
        ForeignKey("studio_media_ingests.id", ondelete="CASCADE"), index=True
    )
    transcript_id: Mapped[str | None] = mapped_column(
        ForeignKey("studio_transcripts.id", ondelete="SET NULL"), index=True
    )
    document_id: Mapped[str | None] = mapped_column(
        ForeignKey("creative_documents.id", ondelete="SET NULL"), index=True
    )
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    decisions: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    versions: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(160), nullable=False)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    updated_by: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)


class StudioMotionGraph(Base, TimestampMixin):
    __tablename__ = "studio_motion_graphs"
    __table_args__ = (
        UniqueConstraint("workspace_id", "idempotency_key", name="uq_studio_motion_graph_scope_key"),
        Index("ix_studio_motion_graphs_workspace_document", "workspace_id", "document_id"),
        Index("ix_studio_motion_graphs_workspace_status", "workspace_id", "status"),
    )
    id: Mapped[str] = mapped_column(String(160), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    document_id: Mapped[str] = mapped_column(
        ForeignKey("creative_documents.id", ondelete="CASCADE"), index=True
    )
    document_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="suggested", nullable=False)
    storage_revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    graph_digest_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    graph: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    evaluation: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    idempotency_key: Mapped[str] = mapped_column(String(160), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    updated_by: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)


class StudioDomainEvent(Base):
    __tablename__ = "studio_domain_events"
    __table_args__ = (
        Index("ix_studio_events_workspace_occurred", "workspace_id", "occurred_at"),
        Index("ix_studio_events_aggregate", "aggregate_type", "aggregate_id"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    event_type: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    schema_version: Mapped[str] = mapped_column(String(64), default="studio.domain-event.v1", nullable=False)
    aggregate_type: Mapped[str] = mapped_column(String(80), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(120), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)


class StudioReviewRequest(Base):
    __tablename__ = "studio_review_requests"
    __table_args__ = (
        Index("ix_studio_reviews_workspace_status", "workspace_id", "status"),
        Index("ix_studio_reviews_document_requested", "document_id", "requested_at"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    document_id: Mapped[str] = mapped_column(
        ForeignKey("creative_documents.id", ondelete="CASCADE"), index=True
    )
    document_version: Mapped[int] = mapped_column(Integer, nullable=False)
    post_id: Mapped[str | None] = mapped_column(ForeignKey("posts.id", ondelete="SET NULL"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="requested", nullable=False)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    render_job_id: Mapped[str | None] = mapped_column(
        ForeignKey("studio_generation_jobs.id", ondelete="SET NULL"), index=True
    )
    render_asset_id: Mapped[str | None] = mapped_column(
        ForeignKey("library_assets.id", ondelete="SET NULL"), index=True
    )
    render_checksum_sha256: Mapped[str | None] = mapped_column(String(64), index=True)
    requested_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    decided_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    decision_comment: Mapped[str | None] = mapped_column(Text)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class StudioConsentGrant(Base, TimestampMixin):
    __tablename__ = "studio_consent_grants"
    __table_args__ = (
        Index("ix_studio_consents_workspace_status", "workspace_id", "status"),
        Index("ix_studio_consents_subject", "workspace_id", "subject_key"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    subject_key: Mapped[str] = mapped_column(String(160), nullable=False)
    subject_display_name: Mapped[str] = mapped_column(String(240), nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    scopes: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    brand_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    channels: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    policy_version: Mapped[str] = mapped_column(String(120), nullable=False)
    evidence_asset_id: Mapped[str | None] = mapped_column(
        ForeignKey("library_assets.id", ondelete="SET NULL"), index=True
    )
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    granted_by: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    revocation_reason: Mapped[str | None] = mapped_column(Text)


class StudioIdentityProfile(Base, TimestampMixin):
    __tablename__ = "studio_identity_profiles"
    __table_args__ = (
        UniqueConstraint("workspace_id", "subject_key", name="uq_studio_identity_subject"),
        Index("ix_studio_identity_workspace_status", "workspace_id", "status"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    subject_key: Mapped[str] = mapped_column(String(160), nullable=False)
    display_name: Mapped[str] = mapped_column(String(240), nullable=False)
    identity_type: Mapped[str] = mapped_column(String(32), default="natural_person", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    owner_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)


class StudioIdentityVersion(Base, TimestampMixin):
    __tablename__ = "studio_identity_versions"
    __table_args__ = (
        UniqueConstraint("profile_id", "version", name="uq_studio_identity_version"),
        Index("ix_studio_identity_versions_workspace_status", "workspace_id", "status"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    profile_id: Mapped[str] = mapped_column(
        ForeignKey("studio_identity_profiles.id", ondelete="CASCADE"), index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    consent_grant_id: Mapped[str | None] = mapped_column(
        ForeignKey("studio_consent_grants.id", ondelete="SET NULL"), index=True
    )
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    capabilities: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    sample_asset_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    derived_artifacts: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    reviewed_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_comment: Mapped[str | None] = mapped_column(Text)


class StudioVoiceProfile(Base, TimestampMixin):
    __tablename__ = "studio_voice_profiles"
    __table_args__ = (Index("ix_studio_voice_workspace_status", "workspace_id", "status"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    identity_profile_id: Mapped[str | None] = mapped_column(
        ForeignKey("studio_identity_profiles.id", ondelete="SET NULL"), index=True
    )
    display_name: Mapped[str] = mapped_column(String(240), nullable=False)
    locale: Mapped[str] = mapped_column(String(32), default="pt-BR", nullable=False)
    voice_type: Mapped[str] = mapped_column(String(32), default="cloned", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)


class StudioVoiceVersion(Base, TimestampMixin):
    __tablename__ = "studio_voice_versions"
    __table_args__ = (
        UniqueConstraint("profile_id", "version", name="uq_studio_voice_version"),
        Index("ix_studio_voice_versions_workspace_status", "workspace_id", "status"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    profile_id: Mapped[str] = mapped_column(ForeignKey("studio_voice_profiles.id", ondelete="CASCADE"), index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    consent_grant_id: Mapped[str | None] = mapped_column(
        ForeignKey("studio_consent_grants.id", ondelete="SET NULL"), index=True
    )
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    sample_asset_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    derived_artifacts: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    pronunciation_profile: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    reviewed_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_comment: Mapped[str | None] = mapped_column(Text)


class StudioIdentityEvaluation(Base, TimestampMixin):
    __tablename__ = "studio_identity_evaluations"
    __table_args__ = (
        CheckConstraint(
            "(identity_version_id IS NOT NULL AND voice_version_id IS NULL) OR "
            "(identity_version_id IS NULL AND voice_version_id IS NOT NULL)",
            name="ck_studio_identity_evaluation_one_target",
        ),
        Index("ix_studio_identity_evaluations_workspace_status", "workspace_id", "status"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    target_type: Mapped[str] = mapped_column(String(32), nullable=False)
    identity_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("studio_identity_versions.id", ondelete="CASCADE"), index=True
    )
    voice_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("studio_voice_versions.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    evaluator_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    quality_metrics: Mapped[dict[str, float]] = mapped_column(JSON, default=dict, nullable=False)
    checks: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    preview_asset_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    provider_registration_id: Mapped[str | None] = mapped_column(
        ForeignKey("studio_provider_registrations.id", ondelete="SET NULL"), index=True
    )
    model_registration_id: Mapped[str | None] = mapped_column(
        ForeignKey("studio_model_registrations.id", ondelete="SET NULL"), index=True
    )
    evaluated_by: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


class StudioIdentityDeletionRequest(Base, TimestampMixin):
    __tablename__ = "studio_identity_deletion_requests"
    __table_args__ = (
        CheckConstraint(
            "(identity_profile_id IS NOT NULL AND voice_profile_id IS NULL) OR "
            "(identity_profile_id IS NULL AND voice_profile_id IS NOT NULL)",
            name="ck_studio_identity_deletion_one_target",
        ),
        UniqueConstraint("workspace_id", "idempotency_key", name="uq_studio_identity_deletion_scope_key"),
        Index("ix_studio_identity_deletion_workspace_status", "workspace_id", "status"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    target_type: Mapped[str] = mapped_column(String(32), nullable=False)
    identity_profile_id: Mapped[str | None] = mapped_column(
        ForeignKey("studio_identity_profiles.id", ondelete="CASCADE"), index=True
    )
    voice_profile_id: Mapped[str | None] = mapped_column(
        ForeignKey("studio_voice_profiles.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(32), default="planned", nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    delete_source_samples: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deletion_plan: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(160), nullable=False)
    requested_by: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    queued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    execution_receipt: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)


class StudioProviderRegistration(Base, TimestampMixin):
    __tablename__ = "studio_provider_registrations"
    __table_args__ = (
        UniqueConstraint("capability", "provider", "provider_version", name="uq_studio_provider_version"),
        Index("ix_studio_provider_capability_status", "capability", "status"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    capability: Mapped[str] = mapped_column(String(120), nullable=False)
    provider: Mapped[str] = mapped_column(String(120), nullable=False)
    provider_version: Mapped[str] = mapped_column(String(120), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_revision: Mapped[str] = mapped_column(String(160), nullable=False)
    code_license: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="evaluation", nullable=False)
    risk_class: Mapped[str] = mapped_column(String(32), default="medium", nullable=False)
    manifest: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    approved_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class StudioModelRegistration(Base, TimestampMixin):
    __tablename__ = "studio_model_registrations"
    __table_args__ = (
        UniqueConstraint("provider_registration_id", "name", "version", name="uq_studio_model_version"),
        UniqueConstraint("digest_sha256", name="uq_studio_model_digest"),
        Index("ix_studio_model_status", "status"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    provider_registration_id: Mapped[str] = mapped_column(
        ForeignKey("studio_provider_registrations.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    version: Mapped[str] = mapped_column(String(120), nullable=False)
    digest_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    model_license: Mapped[str] = mapped_column(String(160), nullable=False)
    commercial_use: Mapped[str] = mapped_column(String(32), default="unknown", nullable=False)
    languages: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    capabilities: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="evaluation", nullable=False)
    manifest: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    approved_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RadarShadowEvaluation(Base):
    __tablename__ = "radar_shadow_evaluations"
    __table_args__ = (
        Index("ix_radar_shadow_workspace_created", "workspace_id", "created_at"),
        Index("ix_radar_shadow_signal_candidate", "signal_id", "candidate_version"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    signal_id: Mapped[str] = mapped_column(ForeignKey("external_signals.id", ondelete="CASCADE"), index=True)
    active_opportunity_id: Mapped[str | None] = mapped_column(
        ForeignKey("opportunities.id", ondelete="SET NULL"), index=True
    )
    baseline_version: Mapped[str] = mapped_column(String(32), nullable=False)
    baseline_score: Mapped[float] = mapped_column(Float, nullable=False)
    candidate_version: Mapped[str] = mapped_column(String(32), nullable=False)
    candidate_score: Mapped[float | None] = mapped_column(Float)
    brand_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    candidate: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    comparison: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    provider_trace: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class WorkspaceResource(Base, TimestampMixin):
    __tablename__ = "workspace_resources"
    __table_args__ = (
        UniqueConstraint("workspace_id", "kind", "resource_key", name="uq_workspace_resource_kind_key"),
        Index("ix_workspace_resources_workspace_kind", "workspace_id", "kind"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(48), nullable=False)
    resource_key: Mapped[str] = mapped_column(String(120), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (Index("ix_audit_events_workspace_created", "workspace_id", "created_at"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    actor_name: Mapped[str] = mapped_column(String(120), nullable=False)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    resource: Mapped[str] = mapped_column(String(80), nullable=False)
    detail: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
