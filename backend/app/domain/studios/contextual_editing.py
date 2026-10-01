"""Provider-neutral, message-preserving contextual editing contracts.

The planner describes a draft, never a human approval or a publication grant.
Recipes are knowledge references; executable capabilities belong to renderers.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from .contracts import CreativeDocumentV1, EditDecisionV1, StudioContract
from .intelligence import EditOperationBaseV1

CONTEXTUAL_PROVIDER = "builtin.ffmpeg-contextual-v1"


def digest(value) -> str:
    if isinstance(value, StudioContract):
        value = value.model_dump(mode="json", by_alias=True)
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()


class EditingIntentV1(StudioContract):
    objective: str = Field(min_length=1, max_length=2000)
    format: str = Field(default="general", min_length=1, max_length=120)
    script: str = Field(default="", max_length=100_000)
    locked_facts: list[str] = Field(default_factory=list, max_length=100)
    pacing: Literal["calm", "balanced", "energetic"] = "balanced"
    emphasis: Literal["auto", "message", "demonstration", "atmosphere"] = "auto"
    reduced_motion: bool = False
    preserve_message: Literal[True] = True


class EditingBeatV1(StudioContract):
    composition_technique_id: str | None = Field(default=None, max_length=120)
    audio_asset_id: str | None = Field(default=None, max_length=120)
    audio_role: Literal["music", "ambience", "effect", "narration", "dialogue"] = "effect"
    support_query: str | None = Field(default=None, max_length=500)
    id: str = Field(min_length=1, max_length=120)
    clip_id: str = Field(min_length=1, max_length=120)
    purpose: str = Field(min_length=1, max_length=1000)
    transcript: str = Field(default="", max_length=20_000)
    support_asset_id: str | None = None
    mask_asset_id: str | None = None
    support_source_start_microseconds: int = Field(default=0, ge=0)
    on_screen_text: str = Field(default="", max_length=400)
    transcript_id: str | None = None
    transcript_revision: int | None = Field(default=None, ge=1)
    caption_from_transcript: bool = False
    source_decisions: list[EditDecisionV1] = Field(default_factory=list, max_length=500)

    @model_validator(mode="after")
    def transcript_binding(self):
        if bool(self.transcript_id) != (self.transcript_revision is not None):
            raise ValueError("editing_transcript_revision_required")
        if self.caption_from_transcript and self.on_screen_text:
            raise ValueError("editing_choose_caption_or_support_text")
        return self


class EditingMaterialNeedV1(StudioContract):
    font_variant: str = Field(default="regular", min_length=1, max_length=80)
    id: str = Field(min_length=1, max_length=120)
    clip_id: str = Field(min_length=1, max_length=120)
    kind: Literal["font", "logo", "image", "video", "wardrobe", "sound_effect", "music"]
    query: str = Field(min_length=1, max_length=500)
    purpose: str = Field(min_length=1, max_length=2000)
    role: Literal["support", "mask", "music", "ambience", "effect", "narration", "dialogue", "font", "reference"] = (
        "support"
    )
    official_required: bool = False
    exact: bool = False
    required: bool = True
    asset_id: str | None = None
    acceptance_criteria: list[str] = Field(default_factory=list, max_length=30)


class ContextualPlanRequestV1(StudioContract):
    material_needs: list[EditingMaterialNeedV1] = Field(default_factory=list, max_length=100)
    font_asset_id: str | None = Field(default=None, max_length=120)
    expected_document_revision: int = Field(ge=1)
    intent: EditingIntentV1
    beats: list[EditingBeatV1] = Field(default_factory=list, max_length=500)
    required_techniques: list[str] = Field(default_factory=list, max_length=100)
    clip_order: list[str] = Field(default_factory=list, max_length=500)
    reference_technique_ids: list[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def unique_beats(self):
        for values in (
            [b.id for b in self.beats],
            [b.clip_id for b in self.beats],
            self.clip_order,
            [n.id for n in self.material_needs],
        ):
            if len(values) != len(set(values)):
                raise ValueError("editing_duplicate_beat")
        return self


class ContextualOperationV1(EditOperationBaseV1):
    kind: str = Field(min_length=1, max_length=120)
    beat_id: str
    target_id: str
    expected_result: str = Field(min_length=1, max_length=2000)
    technique_ids: list[str] = Field(default_factory=list)


class EditingAlternativeV1(StudioContract):
    id: str
    label: str
    impact: str
    action: Literal["omit_optional", "keep_original", "reduce_resolution", "wait"]


class EditingBlockerV1(StudioContract):
    id: str
    code: str
    target_id: str
    message: str
    alternatives: list[EditingAlternativeV1]


class ContextualEditPlanV1(StudioContract):
    material_requests: list[dict] = Field(default_factory=list)
    schema_version: Literal["studio.contextual-edit-plan.v1"] = "studio.contextual-edit-plan.v1"
    id: str
    revision: int = Field(default=1, ge=1)
    workspace_id: str
    document_id: str
    document_revision: int
    source_digest: str
    source_assets: dict[str, str | None]
    source_transcripts: dict[str, dict] = Field(default_factory=dict)
    editorial_evidence: list[dict] = Field(default_factory=list)
    intent: EditingIntentV1
    operations: list[ContextualOperationV1]
    blockers: list[EditingBlockerV1]
    status: Literal["ready", "awaiting_choice", "applied"]
    estimated_cost_cents: int = Field(ge=0)
    cost_basis: str
    knowledge_ids: list[str] = Field(default_factory=list)
    draft_document: CreativeDocumentV1
    created_at: datetime
    human_approved: Literal[False] = False


class EditingChoiceRequestV1(StudioContract):
    expected_plan_revision: int = Field(ge=1)
    blocker_id: str
    alternative_id: str


class EditingFeedbackRequestV1(StudioContract):
    expected_plan_revision: int = Field(ge=1)
    feedback: Literal["mais calmo", "mostrar melhor o produto", "menos texto"]
    beat_ids: list[str] = Field(min_length=1, max_length=500)


class EditingApplyRequestV1(StudioContract):
    expected_plan_revision: int = Field(ge=1)


class TechniqueExampleV1(StudioContract):
    source_url: str = Field(pattern=r"^https://", max_length=4000)
    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(gt=0)
    observation: str = Field(min_length=1, max_length=4000)
    audio_verified: bool = False

    @model_validator(mode="after")
    def interval(self):
        if self.end_seconds <= self.start_seconds:
            raise ValueError("editing_example_invalid_interval")
        return self


class EditingCompositionProfileV1(StudioContract):
    support_width_ratio: float = Field(default=0.65, ge=0.25, le=1)
    support_height_ratio: float = Field(default=0.45, ge=0.15, le=0.8)
    entrance: Literal["none", "fade", "slide", "zoom"] = "none"
    entrance_seconds: float = Field(default=0.4, ge=0.08, le=1.5)


class EditingTechniqueV1(StudioContract):
    version: int = Field(default=1, ge=1)
    qualification: Literal["knowledge_only", "implemented", "render_verified"] = "knowledge_only"
    source_digest: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    components: list[str] = Field(default_factory=list, max_length=30)
    required_material_kinds: list[Literal["font", "image", "video", "audio"]] = Field(default_factory=list)
    verification: list[str] = Field(default_factory=list, max_length=30)
    research_evidence: list[str] = Field(default_factory=list, max_length=30)
    creator_claims: list[str] = Field(default_factory=list, max_length=30)
    inferences: list[str] = Field(default_factory=list, max_length=30)
    method_limitations: list[str] = Field(default_factory=list, max_length=30)
    id: str
    group: Literal["montage", "composition", "sound"]
    title: str
    purpose: str
    suitable_when: list[str]
    avoid_when: list[str]
    prerequisites: list[str]
    parameters: dict[str, str]
    required_capabilities: list[str]
    evidence_type: Literal["principle", "observation", "trend"]
    sources: list[str]
    examples: list[TechniqueExampleV1] = Field(default_factory=list)
    composition_profile: EditingCompositionProfileV1 | None = None


class EditingObservationV1(StudioContract):
    technique: EditingTechniqueV1
    source_url: str = Field(pattern=r"^https://", max_length=4000)
    observed_at: datetime
    published_at: datetime | None = None
    metrics: dict[str, int] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def dated_metrics(self):
        if self.observed_at.tzinfo is None or (self.published_at and self.published_at.tzinfo is None):
            raise ValueError("editing_observation_timezone_required")
        if self.published_at and self.published_at > self.observed_at:
            raise ValueError("editing_observation_precedes_publication")
        if any(v < 0 for v in self.metrics.values()):
            raise ValueError("editing_metrics_negative")
        return self
