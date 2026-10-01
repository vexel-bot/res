from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from .contracts import StudioContract


class AutonomyPhaseStatusV1(StudioContract):
    phase: Literal["P0", "P1", "P2", "P3", "P4", "P5", "P6", "P7"]
    implementation_status: Literal["complete", "gated"]
    operational_status: Literal[
        "complete",
        "pending_human_review",
        "rejected_replan_required",
        "blocked_by_gate",
        "disabled_fail_closed",
    ]
    evidence_paths: list[str] = Field(min_length=1, max_length=30)
    blockers: list[str] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def validate_phase(self) -> AutonomyPhaseStatusV1:
        if self.operational_status == "complete" and self.blockers:
            raise ValueError("Completed autonomy phase cannot retain blockers")
        if self.operational_status != "complete" and not self.blockers:
            raise ValueError("Non-complete autonomy phase requires blockers")
        return self


class VideoAutonomyCompletionAuditV1(StudioContract):
    schema_version: Literal["studio.video-autonomy-completion-audit.v1"] = (
        "studio.video-autonomy-completion-audit.v1"
    )
    audit_id: str
    phases: list[AutonomyPhaseStatusV1] = Field(min_length=8, max_length=8)
    casebook_case_count: Literal[12] = 12
    animatic_count: Literal[12] = 12
    motion_golden_count: Literal[4] = 4
    assisted_storyboard_option_count: Literal[36] = 36
    produced_private_artifact_count: int = Field(ge=0, le=100)
    human_approved_artifact_count: int = Field(ge=0, le=100)
    scale_job_count: Literal[64] = 64
    dispatched_scale_job_count: int = Field(ge=0, le=64)
    advanced_candidate_count: int = Field(ge=0, le=100)
    authorized_identity_count: int = Field(ge=0, le=6)
    advanced_benchmark_case_count: int = Field(ge=0, le=24)
    enabled_advanced_provider_count: int = Field(ge=0)
    external_publication_count: Literal[0] = 0
    implementation_complete: bool
    objective_complete: bool
    blockers: list[str] = Field(default_factory=list, max_length=100)
    audited_at: datetime

    @model_validator(mode="after")
    def validate_audit(self) -> VideoAutonomyCompletionAuditV1:
        phase_names = [item.phase for item in self.phases]
        if phase_names != [f"P{index}" for index in range(8)]:
            raise ValueError("Autonomy completion audit requires ordered P0 through P7")
        expected_implementation = all(
            item.implementation_status == "complete" for item in self.phases
        )
        expected_objective = (
            expected_implementation
            and self.produced_private_artifact_count == 100
            and self.human_approved_artifact_count == 100
            and self.dispatched_scale_job_count == 64
            and not self.blockers
        )
        if self.implementation_complete != expected_implementation:
            raise ValueError("Implementation completion disagrees with phase evidence")
        if self.objective_complete != expected_objective:
            raise ValueError("Objective completion disagrees with artifact and review evidence")
        if self.objective_complete and any(
            item.operational_status != "complete" for item in self.phases
        ):
            raise ValueError("Objective cannot complete with an operationally gated phase")
        return self
