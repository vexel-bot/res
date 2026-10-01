from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.domain.studios.advanced_capabilities import AdvancedCapabilityAuditV1

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
AUDIT_PATH = (
    REPOSITORY_ROOT
    / "artifacts"
    / "validation"
    / "video-creative-pilot"
    / "advanced-capabilities-20260901-v1"
    / "audit.json"
)


def audit() -> AdvancedCapabilityAuditV1:
    return AdvancedCapabilityAuditV1.model_validate_json(
        AUDIT_PATH.read_text(encoding="utf-8")
    )


def test_advanced_capabilities_fail_closed_without_biometric_execution() -> None:
    evidence = audit()

    assert len(evidence.candidates) == 9
    assert len(evidence.identity_slots) == 6
    assert evidence.authorized_identity_count == 0
    assert evidence.executed_benchmark_case_count == 0
    assert evidence.enabled_provider_ids == []
    assert evidence.activation_eligible is False
    assert evidence.publish_synthetic_grant_count == 0
    assert all(item.biometric_inference_executed is False for item in evidence.candidates)
    assert all(item.authorization_status == "not_acquired" for item in evidence.identity_slots)
    assert all(item.private_artifact_count == 0 for item in evidence.identity_slots)
    assert set(evidence.fallback_modes) == {
        "real_person",
        "licensed_stock",
        "faceless_motion",
    }
    assert "six_authorized_identities_required" in evidence.blockers
    assert "provider_registry_intentionally_empty" in evidence.blockers


def test_advanced_capability_cannot_be_forged_ready() -> None:
    payload = audit().model_dump(mode="json", by_alias=True)
    payload["activationEligible"] = True

    with pytest.raises(ValidationError, match="activation disagrees"):
        AdvancedCapabilityAuditV1.model_validate(payload)
