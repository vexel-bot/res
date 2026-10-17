from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from .contracts import StudioContract

OPAQUE_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,159}$"

CreativeReplanDecisionKeyV1 = Literal[
    "business_objective",
    "audience_and_offer",
    "channel_and_duration",
    "golden_format_family",
    "presenter_policy",
    "media_sources_and_rights",
    "voice_policy",
    "reference_matrix",
    "quality_rubric_and_owner",
]

REQUIRED_REPLAN_DECISIONS: tuple[CreativeReplanDecisionKeyV1, ...] = (
    "business_objective",
    "audience_and_offer",
    "channel_and_duration",
    "golden_format_family",
    "presenter_policy",
    "media_sources_and_rights",
    "voice_policy",
    "reference_matrix",
    "quality_rubric_and_owner",
)


class CreativeReplanDecisionV1(StudioContract):
    key: CreativeReplanDecisionKeyV1
    prompt: str = Field(min_length=1, max_length=1000)
    status: Literal["pending", "approved", "rejected"] = "pending"
    selection: str | None = Field(default=None, max_length=4000)
    reviewed_by: str | None = Field(default=None, pattern=OPAQUE_ID_PATTERN)
    reviewed_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def validate_decision(self) -> CreativeReplanDecisionV1:
        bindings = (self.selection, self.reviewed_by, self.reviewed_at)
        if self.status == "pending" and any(bindings):
            raise ValueError("Pending replan decisions cannot carry approval data")
        if self.status == "approved" and not all(bindings):
            raise ValueError("Approved replan decisions require selection and reviewer")
        if self.status == "rejected" and not self.notes:
            raise ValueError("Rejected replan decisions require notes")
        return self


class CreativeReplanStateV1(StudioContract):
    schema_version: Literal["studio.creative-replan-state.v1"] = (
        "studio.creative-replan-state.v1"
    )
    replan_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    previous_program_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    previous_rejection_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    status: Literal["awaiting_decisions", "ready_for_one_golden"]
    decisions: list[CreativeReplanDecisionV1] = Field(min_length=9, max_length=9)
    approved_decision_count: int = Field(ge=0, le=9)
    golden_job_limit: Literal[1] = 1
    golden_production_eligible: bool
    batch_dispatch_authorized: Literal[False] = False
    rejected_artifact_reuse_authorized: Literal[False] = False
    external_publication_authorized: Literal[False] = False
    blockers: list[str] = Field(max_length=100)
    evaluated_at: datetime

    @model_validator(mode="after")
    def validate_state(self) -> CreativeReplanStateV1:
        keys = tuple(item.key for item in self.decisions)
        if keys != REQUIRED_REPLAN_DECISIONS:
            raise ValueError("Replan state requires every decision in canonical order")
        approved = sum(item.status == "approved" for item in self.decisions)
        if self.approved_decision_count != approved:
            raise ValueError("Replan approved count disagrees with decisions")
        expected_eligible = approved == len(self.decisions) and not self.blockers
        if self.golden_production_eligible != expected_eligible:
            raise ValueError("Golden eligibility disagrees with replan evidence")
        expected_status = (
            "ready_for_one_golden" if expected_eligible else "awaiting_decisions"
        )
        if self.status != expected_status:
            raise ValueError("Replan status disagrees with golden eligibility")
        return self


def assert_one_golden_can_start(state: CreativeReplanStateV1) -> None:
    if not state.golden_production_eligible:
        raise ValueError("creative_replan_decisions_incomplete")
    if state.golden_job_limit != 1 or state.batch_dispatch_authorized:
        raise ValueError("golden_first_invariant_broken")
