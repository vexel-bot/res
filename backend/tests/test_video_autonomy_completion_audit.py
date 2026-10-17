from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.domain.studios.autonomy_completion import VideoAutonomyCompletionAuditV1

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
AUDIT_PATH = (
    REPOSITORY_ROOT
    / "artifacts"
    / "validation"
    / "video-creative-pilot"
    / "program-audit-20260901-v1"
    / "audit.json"
)


def audit() -> VideoAutonomyCompletionAuditV1:
    return VideoAutonomyCompletionAuditV1.model_validate_json(
        AUDIT_PATH.read_text(encoding="utf-8")
    )


def test_completion_audit_separates_implementation_render_and_approval() -> None:
    evidence = audit()

    assert evidence.implementation_complete is True
    assert evidence.objective_complete is False
    assert evidence.produced_private_artifact_count == 36
    assert evidence.human_approved_artifact_count == 0
    assert evidence.scale_job_count == 64
    assert evidence.dispatched_scale_job_count == 0
    assert evidence.external_publication_count == 0
    assert [item.phase for item in evidence.phases] == [f"P{index}" for index in range(8)]
    assert evidence.phases[5].operational_status == "rejected_replan_required"
    assert "pilot_machine_pre_review_not_final_edit" in evidence.phases[5].blockers
    assert evidence.phases[6].operational_status == "blocked_by_gate"
    assert evidence.phases[7].operational_status == "disabled_fail_closed"


def test_completion_cannot_be_forged_from_36_technical_renders() -> None:
    payload = audit().model_dump(mode="json", by_alias=True)
    payload["objectiveComplete"] = True

    with pytest.raises(ValidationError, match="Objective completion disagrees"):
        VideoAutonomyCompletionAuditV1.model_validate(payload)
