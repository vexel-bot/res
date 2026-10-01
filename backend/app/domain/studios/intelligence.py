from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field, model_validator

from .contracts import (
    BrandMemoryReferenceV1,
    CreateEditDecisionSetRequest,
    CreativeBriefV1,
    CreativeDocumentV1,
    EditDecisionV1,
    OpportunityEvidenceReferenceV1,
    StudioContract,
)

SHA256_PATTERN = r"^[0-9a-fA-F]{64}$"
OPAQUE_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,159}$"
MAX_MEDIA_MICROSECONDS = 86_400_000_000


class MediaIntervalV1(StudioContract):
    start_microseconds: int = Field(ge=0, le=MAX_MEDIA_MICROSECONDS)
    end_microseconds: int = Field(gt=0, le=MAX_MEDIA_MICROSECONDS)

    @model_validator(mode="after")
    def validate_interval(self) -> MediaIntervalV1:
        if self.end_microseconds <= self.start_microseconds:
            raise ValueError("Media interval end must be after start")
        return self


class IntelligenceLineageV1(StudioContract):
    provider: str = Field(min_length=1, max_length=160)
    provider_version: str = Field(min_length=1, max_length=160)
    model: str = Field(min_length=1, max_length=240)
    model_revision: str = Field(min_length=1, max_length=240)
    parameters_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    prompt_digest_sha256: str | None = Field(default=None, pattern=SHA256_PATTERN)
    worker_manifest_digest_sha256: str | None = Field(default=None, pattern=SHA256_PATTERN)
    generated_at: datetime


class PlanningCopyRevisionContextV1(StudioContract):
    schema_version: Literal["studio.planning-copy-revision-context.v1"] = (
        "studio.planning-copy-revision-context.v1"
    )
    previous_request_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    previous_script: str = Field(min_length=1, max_length=20_000)
    feedback: list[str] = Field(min_length=1, max_length=100)
    locked_fields: list[
        Literal["channel", "format", "restrictions", "evidence"]
    ] = Field(default_factory=list, max_length=4)

    @model_validator(mode="after")
    def validate_revision_context(self) -> PlanningCopyRevisionContextV1:
        if len(self.feedback) != len(set(self.feedback)):
            raise ValueError("Planning revision feedback items must be unique")
        if len(self.locked_fields) != len(set(self.locked_fields)):
            raise ValueError("Planning revision locked fields must be unique")
        return self


class PlanningCopyProductionContextV1(StudioContract):
    """Non-biometric execution direction supplied to planning, not an inference grant."""

    schema_version: Literal["studio.planning-copy-production-context.v1"] = (
        "studio.planning-copy-production-context.v1"
    )
    target_duration_seconds: int = Field(ge=5, le=300)
    avatar_catalog_slot: str = Field(pattern=OPAQUE_ID_PATTERN)
    presenter_direction: str = Field(min_length=1, max_length=500)
    scene_setting: str = Field(min_length=1, max_length=500)
    background_direction: str = Field(min_length=1, max_length=1500)
    continuity_constraints: list[str] = Field(min_length=1, max_length=20)
    avatar_inference_authorized: Literal[False] = False


class PlanningCopyRequestV1(StudioContract):
    """Provider-neutral input; tenant context remains explicit and digestible."""

    schema_version: Literal["studio.planning-copy-request.v1"] = (
        "studio.planning-copy-request.v1"
    )
    request_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    workspace_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    brand_memory_ref: BrandMemoryReferenceV1
    objective: str = Field(min_length=1, max_length=1000)
    audience: str = Field(min_length=1, max_length=2000)
    product: str = Field(min_length=1, max_length=2000)
    offer: str = Field(default="", max_length=2000)
    channel: str = Field(default="instagram", min_length=1, max_length=80)
    format: str = Field(default="short-video", min_length=1, max_length=80)
    locale: str = Field(default="pt-BR", min_length=2, max_length=32)
    tone: str = Field(default="", max_length=1000)
    restrictions: list[str] = Field(default_factory=list, max_length=100)
    evidence: list[OpportunityEvidenceReferenceV1] = Field(default_factory=list, max_length=100)
    production_context: PlanningCopyProductionContextV1 | None = None
    revision_context: PlanningCopyRevisionContextV1 | None = None

    @model_validator(mode="after")
    def validate_evidence(self) -> PlanningCopyRequestV1:
        evidence_ids = [item.id for item in self.evidence]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("Planning copy evidence ids must be unique")
        return self


class PlanningClaimV1(StudioContract):
    claim_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    text: str = Field(min_length=1, max_length=2000)
    evidence_ids: list[str] = Field(default_factory=list, max_length=100)
    requires_human_review: bool

    @model_validator(mode="after")
    def validate_unverified_claim(self) -> PlanningClaimV1:
        if len(self.evidence_ids) != len(set(self.evidence_ids)):
            raise ValueError("Planning claim evidence ids must be unique")
        if not self.evidence_ids and not self.requires_human_review:
            raise ValueError("A claim without evidence must require human review")
        return self


class PlanningStoryboardBeatV1(StudioContract):
    beat_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    order: int = Field(ge=0, le=1000)
    narrative_role: Literal["hook", "setup", "problem", "proof", "demo", "benefit", "offer", "cta"]
    duration_seconds: float = Field(gt=0, le=300)
    visual_direction: str = Field(min_length=1, max_length=2000)
    copy_text: str = Field(default="", max_length=4000)
    on_screen_text: str = Field(default="", max_length=1000)
    evidence_ids: list[str] = Field(default_factory=list, max_length=100)
    requires_human_review: bool = False

    @model_validator(mode="after")
    def validate_storyboard_beat(self) -> PlanningStoryboardBeatV1:
        if len(self.evidence_ids) != len(set(self.evidence_ids)):
            raise ValueError("Planning storyboard evidence ids must be unique")
        if not self.evidence_ids and self.narrative_role == "proof" and not self.requires_human_review:
            raise ValueError("An unsupported proof beat must require human review")
        return self


class PlanningCopyDraftV1(StudioContract):
    """Structured model output before Clicko adds trusted execution lineage."""

    schema_version: Literal["studio.planning-copy-draft.v1"] = "studio.planning-copy-draft.v1"
    brief: CreativeBriefV1
    script: str = Field(min_length=1, max_length=20_000)
    claims: list[PlanningClaimV1] = Field(default_factory=list, max_length=100)
    storyboard: list[PlanningStoryboardBeatV1] = Field(default_factory=list, max_length=100)
    alternatives: list[str] = Field(default_factory=list, max_length=20)
    abstentions: list[str] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def validate_claim_ids(self) -> PlanningCopyDraftV1:
        claim_ids = [item.claim_id for item in self.claims]
        beat_ids = [item.beat_id for item in self.storyboard]
        beat_orders = [item.order for item in self.storyboard]
        if len(claim_ids) != len(set(claim_ids)):
            raise ValueError("Planning claim ids must be unique")
        if len(beat_ids) != len(set(beat_ids)):
            raise ValueError("Planning storyboard beat ids must be unique")
        if beat_orders != list(range(len(self.storyboard))):
            raise ValueError("Planning storyboard beat order must be contiguous")
        return self


class PlanningCopyBenchmarkExpectationV1(StudioContract):
    scenario: str = Field(min_length=1, max_length=160)
    expected_result_status: Literal["complete", "partial"]
    required_abstention: bool
    preserve_channel: Literal[True] = True
    preserve_format: Literal[True] = True
    preserve_restrictions: Literal[True] = True
    preserve_evidence: Literal[True] = True
    unsupported_claims_require_human_review: Literal[True] = True
    required_evidence_ids: list[str] = Field(default_factory=list, max_length=100)
    forbidden_output_fragments: list[str] = Field(default_factory=list, max_length=100)
    minimum_storyboard_beats: int = Field(default=0, ge=0, le=100)
    revision_feedback_items: list[str] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def validate_expectation(self) -> PlanningCopyBenchmarkExpectationV1:
        for values, label in (
            (self.required_evidence_ids, "required evidence ids"),
            (self.forbidden_output_fragments, "forbidden output fragments"),
            (self.revision_feedback_items, "revision feedback items"),
        ):
            if len(values) != len(set(values)):
                raise ValueError(f"Planning benchmark {label} must be unique")
        if self.required_abstention != (self.expected_result_status == "partial"):
            raise ValueError("Planning benchmark partial status must match required abstention")
        return self


class PlanningCopySyntheticCaseV1(StudioContract):
    case_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    request: PlanningCopyRequestV1
    expectation: PlanningCopyBenchmarkExpectationV1

    @model_validator(mode="after")
    def validate_case_binding(self) -> PlanningCopySyntheticCaseV1:
        if self.request.request_id != self.case_id:
            raise ValueError("Planning benchmark request id must match case id")
        known_evidence = {item.id for item in self.request.evidence}
        missing = sorted(set(self.expectation.required_evidence_ids) - known_evidence)
        if missing:
            raise ValueError(f"Planning benchmark expects unknown evidence: {missing}")
        if self.expectation.revision_feedback_items:
            revision = self.request.revision_context
            if revision is None or revision.feedback != self.expectation.revision_feedback_items:
                raise ValueError("Planning benchmark revision feedback is not request-bound")
        return self


class PlanningCopySyntheticCasebookV1(StudioContract):
    schema_version: Literal["studio.planning-copy-synthetic-casebook.v1"] = (
        "studio.planning-copy-synthetic-casebook.v1"
    )
    suite_id: str = Field(min_length=1, max_length=160)
    policy_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    corpus_manifest_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    cases: list[PlanningCopySyntheticCaseV1] = Field(min_length=1, max_length=100_000)

    @model_validator(mode="after")
    def validate_casebook(self) -> PlanningCopySyntheticCasebookV1:
        case_ids = [item.case_id for item in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("Planning benchmark case ids must be unique")
        return self


class PlanningCopyResultV1(StudioContract):
    schema_version: Literal["studio.planning-copy-result.v1"] = "studio.planning-copy-result.v1"
    request_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    request_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    workspace_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    status: Literal["partial", "complete"]
    draft: PlanningCopyDraftV1
    lineage: IntelligenceLineageV1
    human_review_required: Literal[True] = True
    created_at: datetime

    @model_validator(mode="after")
    def validate_status(self) -> PlanningCopyResultV1:
        if self.status == "complete" and self.draft.abstentions:
            raise ValueError("A complete planning result cannot contain abstentions")
        return self


class MediaEvidenceV1(StudioContract):
    evidence_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    evidence_type: Literal[
        "frame",
        "shot",
        "transcript",
        "audio",
        "motion",
        "object",
        "reality",
        "technical_qc",
        "human_annotation",
    ]
    asset_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    asset_checksum_sha256: str = Field(pattern=SHA256_PATTERN)
    interval: MediaIntervalV1 | None = None
    source_contract_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    source_contract_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    summary: str = Field(min_length=1, max_length=2000)


class MediaIndexEntryV1(StudioContract):
    entry_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    kind: Literal[
        "scene",
        "cut",
        "speech",
        "silence",
        "person",
        "product",
        "action",
        "motion",
        "claim",
        "risk",
        "emotion",
    ]
    interval: MediaIntervalV1
    label: str = Field(min_length=1, max_length=500)
    confidence: float = Field(ge=0, le=1)
    evidence_ids: list[str] = Field(min_length=1, max_length=100)
    attributes: dict[str, str | int | float | bool] = Field(default_factory=dict, max_length=100)

    @model_validator(mode="after")
    def validate_evidence_ids(self) -> MediaIndexEntryV1:
        if len(self.evidence_ids) != len(set(self.evidence_ids)):
            raise ValueError("Media index entry evidence ids must be unique")
        return self


class MediaIndexV1(StudioContract):
    schema_version: Literal["studio.media-index.v1"] = "studio.media-index.v1"
    index_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    workspace_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    media_ingest_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    source_asset_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    source_checksum_sha256: str = Field(pattern=SHA256_PATTERN)
    duration_microseconds: int = Field(gt=0, le=MAX_MEDIA_MICROSECONDS)
    locale: str = Field(default="pt-BR", min_length=2, max_length=32)
    status: Literal["partial", "complete"]
    evidence: list[MediaEvidenceV1] = Field(min_length=1, max_length=100_000)
    entries: list[MediaIndexEntryV1] = Field(default_factory=list, max_length=100_000)
    abstentions: list[str] = Field(default_factory=list, max_length=1000)
    lineage: list[IntelligenceLineageV1] = Field(min_length=1, max_length=100)
    created_at: datetime

    @model_validator(mode="after")
    def validate_index(self) -> MediaIndexV1:
        evidence_ids = [item.evidence_id for item in self.evidence]
        entry_ids = [item.entry_id for item in self.entries]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("Media evidence ids must be unique")
        if len(entry_ids) != len(set(entry_ids)):
            raise ValueError("Media index entry ids must be unique")
        known_evidence = set(evidence_ids)
        for evidence in self.evidence:
            if evidence.asset_id != self.source_asset_id:
                raise ValueError("Media evidence asset must match the indexed source asset")
            if evidence.asset_checksum_sha256.lower() != self.source_checksum_sha256.lower():
                raise ValueError("Media evidence checksum must match the indexed source asset")
            if evidence.interval and evidence.interval.end_microseconds > self.duration_microseconds:
                raise ValueError("Media evidence interval exceeds source duration")
        for entry in self.entries:
            if entry.interval.end_microseconds > self.duration_microseconds:
                raise ValueError("Media index entry exceeds source duration")
            missing = sorted(set(entry.evidence_ids) - known_evidence)
            if missing:
                raise ValueError(f"Media index entry references unknown evidence: {missing}")
        if self.status == "complete" and self.abstentions:
            raise ValueError("A complete media index cannot contain unresolved abstentions")
        return self


class StoryboardBeatV1(StudioContract):
    beat_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    order: int = Field(ge=0, le=10_000)
    narrative_role: Literal["hook", "setup", "problem", "proof", "demo", "benefit", "offer", "cta"]
    purpose: str = Field(min_length=1, max_length=1000)
    target_interval: MediaIntervalV1
    source_evidence_ids: list[str] = Field(min_length=1, max_length=100)
    copy_text: str | None = Field(default=None, max_length=4000)
    locked: bool = False

    @model_validator(mode="after")
    def validate_sources(self) -> StoryboardBeatV1:
        if len(self.source_evidence_ids) != len(set(self.source_evidence_ids)):
            raise ValueError("Storyboard evidence ids must be unique")
        return self


class LStoryboardV1(StudioContract):
    schema_version: Literal["studio.l-storyboard.v1"] = "studio.l-storyboard.v1"
    storyboard_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    workspace_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    document_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    document_revision: int = Field(ge=1)
    media_index_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    media_index_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    target_duration_microseconds: int = Field(gt=0, le=MAX_MEDIA_MICROSECONDS)
    status: Literal["draft", "reviewed"] = "draft"
    beats: list[StoryboardBeatV1] = Field(min_length=1, max_length=1000)
    lineage: IntelligenceLineageV1
    human_review_required: Literal[True] = True
    created_at: datetime

    @model_validator(mode="after")
    def validate_beats(self) -> LStoryboardV1:
        ids = [item.beat_id for item in self.beats]
        orders = [item.order for item in self.beats]
        if len(ids) != len(set(ids)):
            raise ValueError("Storyboard beat ids must be unique")
        if orders != list(range(len(self.beats))):
            raise ValueError("Storyboard beat order must be contiguous")
        previous_end = 0
        for beat in self.beats:
            if beat.target_interval.start_microseconds < previous_end:
                raise ValueError("Storyboard target intervals cannot overlap")
            if beat.target_interval.end_microseconds > self.target_duration_microseconds:
                raise ValueError("Storyboard beat exceeds target duration")
            previous_end = beat.target_interval.end_microseconds
        return self


class EditOperationBaseV1(StudioContract):
    operation_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    evidence_ids: list[str] = Field(min_length=1, max_length=100)
    confidence: float = Field(ge=0, le=1)
    rationale: str = Field(min_length=1, max_length=2000)

    @model_validator(mode="after")
    def validate_operation_evidence(self) -> EditOperationBaseV1:
        if len(self.evidence_ids) != len(set(self.evidence_ids)):
            raise ValueError("Edit operation evidence ids must be unique")
        return self


class RemoveRangeOperationV1(EditOperationBaseV1):
    kind: Literal["remove_range"] = "remove_range"
    source_track_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    interval: MediaIntervalV1


class AddMarkerOperationV1(EditOperationBaseV1):
    kind: Literal["add_marker"] = "add_marker"
    target_track_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    interval: MediaIntervalV1
    label: str = Field(min_length=1, max_length=500)
    marker_type: str = Field(default="ai-suggestion", min_length=1, max_length=80)


class AddCaptionOperationV1(EditOperationBaseV1):
    kind: Literal["add_caption"] = "add_caption"
    target_track_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    interval: MediaIntervalV1
    text: str = Field(min_length=1, max_length=4000)
    style_preset: str = Field(default="brand-bold", pattern=OPAQUE_ID_PATTERN)


class SetAudioGainOperationV1(EditOperationBaseV1):
    kind: Literal["set_audio_gain"] = "set_audio_gain"
    target_track_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    interval: MediaIntervalV1
    gain_db: float = Field(ge=-96, le=24)


class InsertBrollOperationV1(EditOperationBaseV1):
    kind: Literal["insert_broll"] = "insert_broll"
    target_track_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    interval: MediaIntervalV1
    asset_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    rights_status: Literal["verified"] = "verified"


class ApplyMotionPresetOperationV1(EditOperationBaseV1):
    kind: Literal["apply_motion_preset"] = "apply_motion_preset"
    target_track_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    interval: MediaIntervalV1
    preset_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    intensity: Literal["subtle", "balanced", "high"] = "balanced"


EditOperationV1 = Annotated[
    RemoveRangeOperationV1
    | AddMarkerOperationV1
    | AddCaptionOperationV1
    | SetAudioGainOperationV1
    | InsertBrollOperationV1
    | ApplyMotionPresetOperationV1,
    Field(discriminator="kind"),
]


class EditProposalV1(StudioContract):
    schema_version: Literal["studio.edit-proposal.v1"] = "studio.edit-proposal.v1"
    proposal_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    workspace_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    document_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    base_document_revision: int = Field(ge=1)
    media_index_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    media_index_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    storyboard_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    storyboard_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    status: Literal["suggested", "rejected", "applied"] = "suggested"
    operations: list[EditOperationV1] = Field(min_length=1, max_length=10_000)
    affected_track_ids: list[str] = Field(min_length=1, max_length=100)
    estimated_duration_before_microseconds: int = Field(gt=0, le=MAX_MEDIA_MICROSECONDS)
    estimated_duration_after_microseconds: int = Field(gt=0, le=MAX_MEDIA_MICROSECONDS)
    abstentions: list[str] = Field(default_factory=list, max_length=1000)
    lineage: IntelligenceLineageV1
    human_apply_required: Literal[True] = True
    created_at: datetime

    @model_validator(mode="after")
    def validate_operations(self) -> EditProposalV1:
        operation_ids = [item.operation_id for item in self.operations]
        if len(operation_ids) != len(set(operation_ids)):
            raise ValueError("Edit proposal operation ids must be unique")
        if len(self.affected_track_ids) != len(set(self.affected_track_ids)):
            raise ValueError("Edit proposal affected track ids must be unique")
        referenced_tracks = {
            track_id
            for item in self.operations
            for track_id in [getattr(item, "source_track_id", None), getattr(item, "target_track_id", None)]
            if track_id
        }
        if referenced_tracks != set(self.affected_track_ids):
            raise ValueError("Affected tracks must exactly match operation targets")
        if self.status == "applied":
            raise ValueError("A generated proposal cannot declare itself applied")
        return self


class EditProposalApplicationV1(StudioContract):
    schema_version: Literal["studio.edit-proposal-application.v1"] = (
        "studio.edit-proposal-application.v1"
    )
    proposal_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    proposal_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    expected_document_revision: int = Field(ge=1)
    selected_operation_ids: list[str] = Field(min_length=1, max_length=10_000)
    decision: Literal["accept_selected"] = "accept_selected"
    human_confirmed: Literal[True] = True
    applied_by: str = Field(pattern=OPAQUE_ID_PATTERN)
    applied_at: datetime

    @model_validator(mode="after")
    def validate_selection(self) -> EditProposalApplicationV1:
        if len(self.selected_operation_ids) != len(set(self.selected_operation_ids)):
            raise ValueError("Selected edit operation ids must be unique")
        return self


class EditProposalGateResultV1(StudioContract):
    schema_version: Literal["studio.edit-proposal-gate-result.v1"] = (
        "studio.edit-proposal-gate-result.v1"
    )
    proposal_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    eligible: bool
    selected_operation_ids: list[str]
    blocking_reasons: list[str]


def _contract_digest(contract: StudioContract) -> str:
    canonical = json.dumps(
        contract.model_dump(mode="json", by_alias=True, exclude_none=True),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def media_index_digest(index: MediaIndexV1) -> str:
    return _contract_digest(index)


def planning_copy_request_digest(request: PlanningCopyRequestV1) -> str:
    return _contract_digest(request)


def validate_planning_copy_result_bindings(
    request: PlanningCopyRequestV1,
    result: PlanningCopyResultV1,
) -> None:
    if result.request_id != request.request_id:
        raise ValueError("Planning result request id does not match")
    if result.workspace_id != request.workspace_id:
        raise ValueError("Planning result workspace does not match")
    if result.request_digest_sha256.lower() != planning_copy_request_digest(request):
        raise ValueError("Planning result request digest does not match")
    known_evidence = {item.id for item in request.evidence}
    if result.draft.brief.channel != request.channel:
        raise ValueError("Planning result channel does not match request")
    if result.draft.brief.format != request.format:
        raise ValueError("Planning result format does not match request")
    missing_restrictions = sorted(
        set(request.restrictions) - set(result.draft.brief.restrictions)
    )
    if missing_restrictions:
        raise ValueError(f"Planning result dropped restrictions: {missing_restrictions}")
    request_evidence = {
        item.id: item.model_dump(mode="json", by_alias=True, exclude_none=True)
        for item in request.evidence
    }
    output_evidence_ids = {item.id for item in result.draft.brief.evidence}
    missing_evidence = sorted(set(request_evidence) - output_evidence_ids)
    if missing_evidence:
        raise ValueError(f"Planning result dropped evidence: {missing_evidence}")
    for item in result.draft.brief.evidence:
        expected = request_evidence.get(item.id)
        actual = item.model_dump(mode="json", by_alias=True, exclude_none=True)
        if expected is None or actual != expected:
            raise ValueError(f"Planning result altered or invented evidence: {item.id}")
    unknown = sorted(
        {
            evidence_id
            for evidence_ids in (
                *(claim.evidence_ids for claim in result.draft.claims),
                *(beat.evidence_ids for beat in result.draft.storyboard),
            )
            for evidence_id in evidence_ids
            if evidence_id not in known_evidence
        }
    )
    if unknown:
        raise ValueError(f"Planning result references unknown evidence: {unknown}")


def l_storyboard_digest(storyboard: LStoryboardV1) -> str:
    return _contract_digest(storyboard)


def edit_proposal_digest(proposal: EditProposalV1) -> str:
    return _contract_digest(proposal)


def validate_storyboard_bindings(index: MediaIndexV1, storyboard: LStoryboardV1) -> None:
    if storyboard.workspace_id != index.workspace_id:
        raise ValueError("Storyboard workspace does not match media index")
    if storyboard.media_index_id != index.index_id:
        raise ValueError("Storyboard media index id does not match")
    if storyboard.media_index_digest_sha256.lower() != media_index_digest(index):
        raise ValueError("Storyboard media index digest does not match")
    known_evidence = {item.evidence_id for item in index.evidence}
    missing = sorted(
        {
            evidence_id
            for beat in storyboard.beats
            for evidence_id in beat.source_evidence_ids
            if evidence_id not in known_evidence
        }
    )
    if missing:
        raise ValueError(f"Storyboard references unknown evidence: {missing}")


def evaluate_edit_proposal_application(
    document: CreativeDocumentV1,
    index: MediaIndexV1,
    storyboard: LStoryboardV1,
    proposal: EditProposalV1,
    application: EditProposalApplicationV1,
) -> EditProposalGateResultV1:
    reasons: list[str] = []
    try:
        validate_storyboard_bindings(index, storyboard)
    except ValueError as error:
        reasons.append(f"storyboard_binding:{error}")
    bindings = (
        (proposal.workspace_id, document.workspace_id, "workspace_mismatch"),
        (proposal.workspace_id, index.workspace_id, "index_workspace_mismatch"),
        (proposal.document_id, document.document_id, "document_id_mismatch"),
        (proposal.media_index_id, index.index_id, "media_index_id_mismatch"),
        (proposal.storyboard_id, storyboard.storyboard_id, "storyboard_id_mismatch"),
    )
    for actual, expected, reason in bindings:
        if actual != expected:
            reasons.append(reason)
    if proposal.base_document_revision != document.revision:
        reasons.append("stale_proposal_document_revision")
    if application.expected_document_revision != document.revision:
        reasons.append("stale_application_document_revision")
    if proposal.media_index_digest_sha256.lower() != media_index_digest(index):
        reasons.append("media_index_digest_mismatch")
    if proposal.storyboard_digest_sha256.lower() != l_storyboard_digest(storyboard):
        reasons.append("storyboard_digest_mismatch")
    if application.proposal_id != proposal.proposal_id:
        reasons.append("proposal_id_mismatch")
    if application.proposal_digest_sha256.lower() != edit_proposal_digest(proposal):
        reasons.append("proposal_digest_mismatch")
    if proposal.status != "suggested":
        reasons.append(f"proposal_status:{proposal.status}")

    operations = {item.operation_id: item for item in proposal.operations}
    missing_operations = sorted(set(application.selected_operation_ids) - operations.keys())
    if missing_operations:
        reasons.append(f"unknown_operations:{','.join(missing_operations)}")
    evidence_ids = {item.evidence_id for item in index.evidence}
    selected = [operations[item] for item in application.selected_operation_ids if item in operations]
    timeline = document.composition.media_timeline
    if document.content_type != "video" or timeline is None:
        reasons.append("video_timeline_required")
        known_tracks: dict[str, object] = {}
    else:
        known_tracks = {track.id: track for track in timeline.tracks}
    assets = {item.id: item for item in document.assets}
    for operation in selected:
        missing_evidence = sorted(set(operation.evidence_ids) - evidence_ids)
        if missing_evidence:
            reasons.append(
                f"operation_evidence_missing:{operation.operation_id}:{','.join(missing_evidence)}"
            )
        interval = operation.interval
        if interval.end_microseconds > index.duration_microseconds:
            reasons.append(f"operation_interval_exceeds_source:{operation.operation_id}")
        track_id = getattr(operation, "source_track_id", None) or getattr(
            operation, "target_track_id", None
        )
        if track_id not in known_tracks and not isinstance(operation, AddCaptionOperationV1):
            reasons.append(f"operation_track_missing:{operation.operation_id}")
        if isinstance(operation, InsertBrollOperationV1):
            asset = assets.get(operation.asset_id)
            if asset is None or asset.rights_status != "verified":
                reasons.append(f"broll_rights_not_verified:{operation.operation_id}")
        if not isinstance(operation, RemoveRangeOperationV1):
            reasons.append(f"operation_applicator_unavailable:{operation.operation_id}")

    unique_reasons = sorted(set(reasons))
    return EditProposalGateResultV1(
        proposal_id=proposal.proposal_id,
        eligible=not unique_reasons,
        selected_operation_ids=application.selected_operation_ids,
        blocking_reasons=unique_reasons,
    )


def materialize_edit_decision_set_request(
    document: CreativeDocumentV1,
    index: MediaIndexV1,
    storyboard: LStoryboardV1,
    proposal: EditProposalV1,
    application: EditProposalApplicationV1,
    *,
    media_ingest_id: str,
    transcript_id: str | None = None,
) -> CreateEditDecisionSetRequest:
    gate = evaluate_edit_proposal_application(document, index, storyboard, proposal, application)
    if not gate.eligible:
        raise ValueError(f"Edit proposal is not eligible: {gate.blocking_reasons}")
    operations = {item.operation_id: item for item in proposal.operations}
    decisions: list[EditDecisionV1] = []
    for operation_id in application.selected_operation_ids:
        operation = operations[operation_id]
        if not isinstance(operation, RemoveRangeOperationV1):
            raise ValueError(
                f"Operation {operation.kind} has no reviewed v1 applicator; document remains unchanged"
            )
        decisions.append(
            EditDecisionV1(
                id=operation.operation_id,
                operation="remove",
                start_microseconds=operation.interval.start_microseconds,
                end_microseconds=operation.interval.end_microseconds,
                status="accepted",
                reason=operation.rationale,
                confidence=operation.confidence,
                source=f"proposal:{proposal.proposal_id}",
            )
        )
    return CreateEditDecisionSetRequest(
        workspace_id=document.workspace_id,
        media_ingest_id=media_ingest_id,
        transcript_id=transcript_id,
        document_id=document.document_id,
        decisions=decisions,
    )
