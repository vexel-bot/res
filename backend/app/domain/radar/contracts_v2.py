from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class RadarContract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProviderTraceV2(RadarContract):
    provider: str
    provider_version: str | None = None
    model: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)


class SourceEvidenceV2(RadarContract):
    schema_version: Literal["radar.source-evidence.v2"] = "radar.source-evidence.v2"
    signal_id: str
    source: str
    url: str
    published_at: datetime
    collected_at: datetime
    expires_at: datetime
    confidence: float | None = Field(default=None, ge=0, le=1)
    knowledge_type: Literal["fact", "inference", "suggestion"] = "fact"
    provider_trace: ProviderTraceV2


class SignalClusterV2(RadarContract):
    schema_version: Literal["radar.signal-cluster.v2"] = "radar.signal-cluster.v2"
    cluster_id: str
    member_signal_ids: list[str]
    evidence: list[SourceEvidenceV2]


class DimensionScoreV2(RadarContract):
    status: Literal["observed", "derived", "unknown"]
    value: float | None = Field(default=None, ge=0, le=100)
    reason: str
    evidence_refs: list[str] = Field(default_factory=list)


class EligibilityGateV2(RadarContract):
    gate: str
    status: Literal["pass", "block", "unknown"]
    reason: str


class OpportunityCandidateV2(RadarContract):
    schema_version: Literal["radar.opportunity-candidate.v2"] = "radar.opportunity-candidate.v2"
    score_version: Literal["radar-v2.0-shadow"] = "radar-v2.0-shadow"
    workspace_id: str
    signal_id: str
    cluster_id: str
    brand_revision: int = Field(ge=1)
    title: str
    what_to_post: str
    why_it_fits: str
    recommended_format: str
    hook: str
    objective: str
    publish_until: datetime
    confidence: float = Field(ge=0, le=1)
    score: float | None = Field(default=None, ge=0, le=100)
    dimensions: dict[str, DimensionScoreV2]
    penalties: dict[str, DimensionScoreV2]
    gates: list[EligibilityGateV2]
    eligible: bool
    rejection_reason: str | None = None
    evidence: list[SourceEvidenceV2]
    effort: Literal["low", "medium", "high"] = "medium"
    lineage: dict[str, Any] = Field(default_factory=dict)
