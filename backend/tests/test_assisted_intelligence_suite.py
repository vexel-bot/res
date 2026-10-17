from __future__ import annotations

from pathlib import Path

from app.domain.studios.assisted_intelligence import AssistedIntelligenceSuiteEvidenceV1
from app.domain.studios.creative_autonomy import (
    CreativePilotCasebookV1,
    creative_casebook_digest,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CASEBOOK_PATH = (
    REPOSITORY_ROOT
    / "benchmarks"
    / "studios"
    / "creative"
    / "video-creative-pilot-casebook.v1.json"
)
MANIFEST_PATH = (
    REPOSITORY_ROOT
    / "artifacts"
    / "validation"
    / "video-creative-pilot"
    / "assisted-intelligence-20260901-v1"
    / "manifest.json"
)


def test_assisted_intelligence_suite_has_options_repairs_and_reversible_decisions() -> None:
    casebook = CreativePilotCasebookV1.model_validate_json(
        CASEBOOK_PATH.read_text(encoding="utf-8")
    )
    suite = AssistedIntelligenceSuiteEvidenceV1.model_validate_json(
        MANIFEST_PATH.read_text(encoding="utf-8")
    )

    assert suite.eligible is True
    assert suite.source_casebook_digest_sha256 == creative_casebook_digest(casebook)
    assert len(suite.cases) == 12
    for item in suite.cases:
        assert len(item.option_set.options) == 3
        assert item.option_set.repair is not None
        assert len(item.reviewed_plan.decisions) == len(item.proposal.operations) == 3
        assert {decision.decision for decision in item.reviewed_plan.decisions} == {
            "accept",
            "reject",
            "adjust",
        }
        assert item.reviewed_plan.before_snapshot_digest_sha256 == (
            item.reviewed_plan.inverse_snapshot_digest_sha256
        )
        proposal_evidence = {
            operation.operation_id: operation.evidence_ids
            for operation in item.proposal.operations
        }
        for operation in item.reviewed_plan.accepted_operations:
            assert operation.evidence_ids == proposal_evidence[operation.operation_id]
