from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from .contracts import StudioContract
from .intelligence import (
    EditOperationV1,
    EditProposalV1,
    LStoryboardV1,
    MediaIndexV1,
    StoryboardBeatV1,
    edit_proposal_digest,
    l_storyboard_digest,
)

SHA256_PATTERN = r"^[0-9a-fA-F]{64}$"
OPAQUE_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,159}$"


def _digest(value: StudioContract) -> str:
    payload = json.dumps(
        value.model_dump(mode="json", by_alias=True, exclude_none=True),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class StoryboardBeatCritiqueV1(StudioContract):
    critique_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    beat_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    verdict: Literal["pass", "repair"]
    dimensions: dict[
        Literal["clarity", "evidence", "continuity", "rhythm", "feasibility"],
        float,
    ] = Field(min_length=5, max_length=5)
    evidence_ids: list[str] = Field(min_length=1, max_length=100)
    diagnosis: str = Field(min_length=1, max_length=2000)
    repair_instruction: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_critique(self) -> StoryboardBeatCritiqueV1:
        if any(score < 0 or score > 1 for score in self.dimensions.values()):
            raise ValueError("Storyboard critique scores must be between zero and one")
        if self.verdict == "repair" and not self.repair_instruction:
            raise ValueError("A rejected beat requires a localized repair instruction")
        if self.verdict == "pass" and self.repair_instruction:
            raise ValueError("A passing beat cannot request repair")
        if len(self.evidence_ids) != len(set(self.evidence_ids)):
            raise ValueError("Storyboard critique evidence ids must be unique")
        return self


class StoryboardOptionV1(StudioContract):
    option_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    strategy: Literal["clarity_first", "proof_first", "rhythm_first"]
    storyboard: LStoryboardV1
    storyboard_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    critiques: list[StoryboardBeatCritiqueV1] = Field(min_length=1, max_length=1000)
    score: float = Field(ge=0, le=1)
    blockers: list[str] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def validate_option(self) -> StoryboardOptionV1:
        if self.storyboard_digest_sha256.lower() != l_storyboard_digest(self.storyboard):
            raise ValueError("Storyboard option digest does not match its storyboard")
        beat_ids = {beat.beat_id for beat in self.storyboard.beats}
        critique_ids = [item.critique_id for item in self.critiques]
        if len(critique_ids) != len(set(critique_ids)):
            raise ValueError("Storyboard critique ids must be unique")
        if {item.beat_id for item in self.critiques} != beat_ids:
            raise ValueError("Storyboard option requires exactly one critique per beat")
        return self


class StoryboardRepairV1(StudioContract):
    repair_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    option_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    source_storyboard_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    repaired_beat_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    original_beat_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    repaired_beat: StoryboardBeatV1
    preserved_beat_ids: list[str] = Field(default_factory=list, max_length=1000)
    repair_evidence_ids: list[str] = Field(min_length=1, max_length=100)
    repaired_at: datetime

    @model_validator(mode="after")
    def validate_repair(self) -> StoryboardRepairV1:
        if self.repaired_beat.beat_id != self.repaired_beat_id:
            raise ValueError("Storyboard repair cannot replace a different beat")
        if self.repaired_beat_id in self.preserved_beat_ids:
            raise ValueError("Repaired beat cannot also be marked preserved")
        if not set(self.repair_evidence_ids) <= set(self.repaired_beat.source_evidence_ids):
            raise ValueError("Storyboard repair must retain the cited repair evidence")
        return self


class StoryboardOptionSetV1(StudioContract):
    schema_version: Literal["studio.storyboard-option-set.v1"] = (
        "studio.storyboard-option-set.v1"
    )
    option_set_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    workspace_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    document_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    document_revision: int = Field(ge=1)
    media_index_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    media_index_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    options: list[StoryboardOptionV1] = Field(min_length=3, max_length=3)
    selected_option_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    selection_rationale: str = Field(min_length=1, max_length=2000)
    repair: StoryboardRepairV1 | None = None
    human_review_required: Literal[True] = True
    created_at: datetime

    @model_validator(mode="after")
    def validate_options(self) -> StoryboardOptionSetV1:
        ids = [item.option_id for item in self.options]
        if len(ids) != len(set(ids)) or set(ids) != {
            f"{self.option_set_id}-clarity",
            f"{self.option_set_id}-proof",
            f"{self.option_set_id}-rhythm",
        }:
            raise ValueError("Storyboard option set requires three stable strategy ids")
        if {item.strategy for item in self.options} != {
            "clarity_first",
            "proof_first",
            "rhythm_first",
        }:
            raise ValueError("Storyboard option set requires all three strategies")
        if self.selected_option_id not in ids:
            raise ValueError("Selected storyboard option must exist")
        selected = next(item for item in self.options if item.option_id == self.selected_option_id)
        if self.repair:
            if self.repair.option_id != selected.option_id:
                raise ValueError("Repair must belong to the selected option")
            if self.repair.source_storyboard_digest_sha256 != selected.storyboard_digest_sha256:
                raise ValueError("Repair source digest must match the selected storyboard")
            original = next(
                (beat for beat in selected.storyboard.beats if beat.beat_id == self.repair.repaired_beat_id),
                None,
            )
            if original is None or beat_digest(original) != self.repair.original_beat_digest_sha256:
                raise ValueError("Repair original beat digest does not match")
            expected_preserved = {
                beat.beat_id
                for beat in selected.storyboard.beats
                if beat.beat_id != self.repair.repaired_beat_id
            }
            if set(self.repair.preserved_beat_ids) != expected_preserved:
                raise ValueError("Localized repair must preserve every other beat")
        return self


class EditOperationDecisionV1(StudioContract):
    operation_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    decision: Literal["accept", "reject", "adjust"]
    reason: str = Field(min_length=1, max_length=2000)
    adjusted_operation: EditOperationV1 | None = None

    @model_validator(mode="after")
    def validate_decision(self) -> EditOperationDecisionV1:
        if self.decision == "adjust" and self.adjusted_operation is None:
            raise ValueError("Adjusted decisions require an adjusted operation")
        if self.decision != "adjust" and self.adjusted_operation is not None:
            raise ValueError("Only adjusted decisions may carry an adjusted operation")
        if self.adjusted_operation and self.adjusted_operation.operation_id != self.operation_id:
            raise ValueError("Adjusted operation id must remain stable")
        return self


class ReviewedEditPlanV1(StudioContract):
    schema_version: Literal["studio.reviewed-edit-plan.v1"] = "studio.reviewed-edit-plan.v1"
    review_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    proposal_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    proposal_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    expected_document_revision: int = Field(ge=1)
    decisions: list[EditOperationDecisionV1] = Field(min_length=1, max_length=10_000)
    accepted_operations: list[EditOperationV1] = Field(default_factory=list, max_length=10_000)
    rejected_operation_ids: list[str] = Field(default_factory=list, max_length=10_000)
    before_snapshot_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    inverse_snapshot_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    human_confirmed: Literal[True] = True
    reviewed_by: str = Field(pattern=OPAQUE_ID_PATTERN)
    reviewed_at: datetime

    @model_validator(mode="after")
    def validate_review(self) -> ReviewedEditPlanV1:
        decision_ids = [item.operation_id for item in self.decisions]
        if len(decision_ids) != len(set(decision_ids)):
            raise ValueError("Every proposal operation must receive one decision")
        accepted_ids = {item.operation_id for item in self.accepted_operations}
        rejected_ids = set(self.rejected_operation_ids)
        if accepted_ids & rejected_ids or accepted_ids | rejected_ids != set(decision_ids):
            raise ValueError("Reviewed plan must partition all operation decisions")
        if self.before_snapshot_digest_sha256 != self.inverse_snapshot_digest_sha256:
            raise ValueError("Inverse snapshot must restore the exact pre-application snapshot")
        return self


class AssistedIntelligenceCaseEvidenceV1(StudioContract):
    case_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    media_index: MediaIndexV1
    option_set: StoryboardOptionSetV1
    proposal: EditProposalV1
    reviewed_plan: ReviewedEditPlanV1
    eligible: bool
    blockers: list[str] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def validate_case(self) -> AssistedIntelligenceCaseEvidenceV1:
        reasons: list[str] = []
        if self.option_set.media_index_id != self.media_index.index_id:
            reasons.append("option_set_media_index_id_mismatch")
        if self.proposal.media_index_id != self.media_index.index_id:
            reasons.append("proposal_media_index_id_mismatch")
        if self.proposal.storyboard_id not in {
            option.storyboard.storyboard_id for option in self.option_set.options
        }:
            reasons.append("proposal_storyboard_not_in_option_set")
        if self.reviewed_plan.proposal_id != self.proposal.proposal_id:
            reasons.append("reviewed_plan_proposal_id_mismatch")
        if self.reviewed_plan.proposal_digest_sha256 != edit_proposal_digest(self.proposal):
            reasons.append("reviewed_plan_proposal_digest_mismatch")
        if self.option_set.repair is None:
            reasons.append("localized_repair_missing")
        reasons.extend(self.blockers)
        if self.eligible != (not reasons):
            raise ValueError("Assisted intelligence case eligibility disagrees with evidence")
        return self


class AssistedIntelligenceSuiteEvidenceV1(StudioContract):
    schema_version: Literal["studio.assisted-intelligence-suite-evidence.v1"] = (
        "studio.assisted-intelligence-suite-evidence.v1"
    )
    suite_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    source_casebook_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    cases: list[AssistedIntelligenceCaseEvidenceV1] = Field(min_length=12, max_length=12)
    eligible: bool
    blockers: list[str] = Field(default_factory=list, max_length=100)
    generated_at: datetime

    @model_validator(mode="after")
    def validate_suite(self) -> AssistedIntelligenceSuiteEvidenceV1:
        ids = [item.case_id for item in self.cases]
        if len(ids) != len(set(ids)):
            raise ValueError("Assisted intelligence case ids must be unique")
        expected = all(item.eligible for item in self.cases) and not self.blockers
        if self.eligible != expected:
            raise ValueError("Assisted intelligence suite eligibility disagrees with cases")
        return self


def beat_digest(beat: StoryboardBeatV1) -> str:
    return _digest(beat)


def storyboard_option_set_digest(option_set: StoryboardOptionSetV1) -> str:
    return _digest(option_set)


def build_reviewed_edit_plan(
    *,
    review_id: str,
    proposal: EditProposalV1,
    expected_document_revision: int,
    decisions: list[EditOperationDecisionV1],
    before_snapshot_digest_sha256: str,
    reviewed_by: str,
    reviewed_at: datetime,
) -> ReviewedEditPlanV1:
    if expected_document_revision != proposal.base_document_revision:
        raise ValueError("Reviewed edit plan targets a stale document revision")
    operations = {item.operation_id: item for item in proposal.operations}
    if {item.operation_id for item in decisions} != set(operations):
        raise ValueError("Every proposal operation must receive exactly one decision")
    accepted: list[EditOperationV1] = []
    rejected: list[str] = []
    for decision in decisions:
        original = operations[decision.operation_id]
        if decision.decision == "reject":
            rejected.append(decision.operation_id)
            continue
        operation = decision.adjusted_operation or original
        if operation.kind != original.kind:
            raise ValueError("Adjusted operation kind cannot change")
        if operation.evidence_ids != original.evidence_ids:
            raise ValueError("Adjusted operation evidence cannot change")
        original_target = getattr(original, "source_track_id", None) or getattr(
            original, "target_track_id", None
        )
        adjusted_target = getattr(operation, "source_track_id", None) or getattr(
            operation, "target_track_id", None
        )
        if adjusted_target != original_target:
            raise ValueError("Adjusted operation target cannot change")
        accepted.append(operation)
    return ReviewedEditPlanV1(
        review_id=review_id,
        proposal_id=proposal.proposal_id,
        proposal_digest_sha256=edit_proposal_digest(proposal),
        expected_document_revision=expected_document_revision,
        decisions=decisions,
        accepted_operations=accepted,
        rejected_operation_ids=rejected,
        before_snapshot_digest_sha256=before_snapshot_digest_sha256,
        inverse_snapshot_digest_sha256=before_snapshot_digest_sha256,
        reviewed_by=reviewed_by,
        reviewed_at=reviewed_at,
    )
