from __future__ import annotations

from pathlib import Path

import pytest

from app.domain.studios.creative_replan import (
    REQUIRED_REPLAN_DECISIONS,
    CreativeReplanStateV1,
    assert_one_golden_can_start,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
STATE_PATH = (
    REPOSITORY_ROOT
    / "artifacts"
    / "validation"
    / "video-creative-pilot"
    / "factory-20260901-v1"
    / "creative-replan-state-20260901-v2.json"
)


def state() -> CreativeReplanStateV1:
    return CreativeReplanStateV1.model_validate_json(
        STATE_PATH.read_text(encoding="utf-8")
    )


def test_replan_requires_every_decision_and_keeps_factory_closed() -> None:
    evidence = state()

    assert tuple(item.key for item in evidence.decisions) == REQUIRED_REPLAN_DECISIONS
    assert evidence.approved_decision_count == 0
    assert evidence.golden_production_eligible is False
    assert evidence.golden_job_limit == 1
    assert evidence.batch_dispatch_authorized is False
    assert evidence.rejected_artifact_reuse_authorized is False
    assert evidence.external_publication_authorized is False
    assert len(evidence.blockers) == 9
    with pytest.raises(ValueError, match="creative_replan_decisions_incomplete"):
        assert_one_golden_can_start(evidence)


def test_replan_cannot_claim_golden_eligibility_while_decisions_are_pending() -> None:
    payload = state().model_dump(mode="json", by_alias=True)
    payload["goldenProductionEligible"] = True

    with pytest.raises(ValueError, match="Golden eligibility disagrees"):
        CreativeReplanStateV1.model_validate(payload)
