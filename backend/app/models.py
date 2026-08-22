from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pgvector.sqlalchemy import VECTOR
from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
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
