from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.domain.studios.artifacts import (
    ArtifactInventoryV1,
    ProviderCandidateManifestV1,
    artifact_inventory_digest,
    provider_candidate_manifest_digest,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
INVENTORY_PATH = (
    REPOSITORY_ROOT
    / "benchmarks"
    / "studios"
    / "reality"
    / "pgv1-artifact-inventory.v1.json"
)
FROZEN_DIGEST = "d1935d35ed3af59d792a5b0c9607d477ea661a862170f4e8574c7a94015dea0c"
CANDIDATE_PATH = (
    REPOSITORY_ROOT
    / "workers"
    / "vision-gpu"
    / "providers"
    / "opencv-baseline.provider.json"
)
CANDIDATE_DIGEST = "4be8fc9c8f66d56279543324c1c5bb74a0a42e62ba33b7ed21b96bd5a0417fcd"


def _payload() -> dict[str, object]:
    return json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))


def _artifact(payload: dict[str, object], artifact_id: str) -> dict[str, object]:
    artifacts = payload["artifacts"]
    assert isinstance(artifacts, list)
    return next(item for item in artifacts if item["artifact_id"] == artifact_id)


def test_pgv1_inventory_is_frozen_and_fail_closed() -> None:
    inventory = ArtifactInventoryV1.model_validate(_payload())

    assert inventory.status == "review_required"
    assert artifact_inventory_digest(inventory) == FROZEN_DIGEST
    assert {
        item.artifact_id
        for item in inventory.artifacts
        if item.license.decision == "review_required"
    } == {
        "numpy-linux-wheel",
        "opencv-python-headless-linux-wheel",
        "pytorch-cuda-runtime",
        "raft-things-checkpoint",
    }


def test_unresolved_required_artifact_makes_inventory_incomplete() -> None:
    payload = _payload()
    runtime = _artifact(payload, "pytorch-cuda-runtime")
    runtime["resolution_status"] = "unresolved"
    runtime["integrity"] = None
    runtime["verification_method"] = "not_verified"
    payload["status"] = "incomplete"

    assert ArtifactInventoryV1.model_validate(payload).status == "incomplete"


def test_inventory_cannot_claim_approval_while_legal_review_is_open() -> None:
    payload = _payload()
    payload["status"] = "approved"

    with pytest.raises(ValidationError, match="status must be review_required"):
        ArtifactInventoryV1.model_validate(payload)


def test_legal_approval_requires_explicit_commercial_saas_permission() -> None:
    payload = _payload()
    checkpoint = _artifact(payload, "raft-things-checkpoint")
    license_decision = checkpoint["license"]
    assert isinstance(license_decision, dict)
    license_decision["decision"] = "approved"

    with pytest.raises(ValidationError, match="explicit commercial SaaS permission"):
        ArtifactInventoryV1.model_validate(payload)


def test_model_bytes_cannot_be_replaced_by_a_git_revision() -> None:
    payload = _payload()
    checkpoint = _artifact(payload, "depth-anything-v2-small-checkpoint")
    checkpoint["integrity"] = {
        "method": "git_commit",
        "value": "03876f8651c73a60fe4c2c48294e09fcb6838fcf",
    }

    with pytest.raises(ValidationError, match="model artifacts require SHA-256"):
        ArtifactInventoryV1.model_validate(payload)


@pytest.mark.parametrize(
    "external_ref",
    [
        "C:/Users/example/model.pth",
        "https://example.test/model.pth",
        "../model.pth",
    ],
)
def test_external_evaluation_ref_cannot_disclose_a_path_or_url(external_ref: str) -> None:
    payload = _payload()
    _artifact(payload, "tapir-checkpoint-panning")["external_evaluation_ref"] = external_ref

    with pytest.raises(ValidationError):
        ArtifactInventoryV1.model_validate(payload)


def test_required_flags_and_required_ids_cannot_diverge() -> None:
    payload = _payload()
    _artifact(payload, "opencv-code")["required"] = False

    with pytest.raises(ValidationError, match="must match records marked required"):
        ArtifactInventoryV1.model_validate(payload)


def test_tampering_changes_the_canonical_inventory_digest() -> None:
    original = ArtifactInventoryV1.model_validate(_payload())
    payload = deepcopy(_payload())
    _artifact(payload, "opencv-code")["notes"] = ["tampered"]
    tampered = ArtifactInventoryV1.model_validate(payload)

    assert artifact_inventory_digest(tampered) != artifact_inventory_digest(original)


def test_opencv_candidate_is_frozen_but_not_activatable() -> None:
    inventory = ArtifactInventoryV1.model_validate(_payload())
    candidate = ProviderCandidateManifestV1.model_validate_json(
        CANDIDATE_PATH.read_text(encoding="utf-8")
    )
    records = {item.artifact_id for item in inventory.artifacts}

    assert provider_candidate_manifest_digest(candidate) == CANDIDATE_DIGEST
    assert candidate.status == "evaluation"
    assert candidate.advertised_by_worker_manifest is False
    assert candidate.artifact_inventory_id == inventory.inventory_id
    assert candidate.artifact_inventory_digest_sha256 == artifact_inventory_digest(inventory)
    assert set(candidate.required_artifact_ids) <= records

    provider_module = REPOSITORY_ROOT / "backend/app/providers/studios/opencv_reality.py"
    scene_module = REPOSITORY_ROOT / "backend/app/providers/studios/reality_scene.py"
    assert candidate.code_digests_sha256 == {
        "opensource.opencv-geometry": hashlib.sha256(provider_module.read_bytes()).hexdigest(),
        "opensource.opencv-point-tracking": hashlib.sha256(provider_module.read_bytes()).hexdigest(),
        "builtin.canonical-reality-scene": hashlib.sha256(scene_module.read_bytes()).hexdigest(),
    }


def test_opencv_candidate_cannot_self_promote_without_all_gates() -> None:
    payload = json.loads(CANDIDATE_PATH.read_text(encoding="utf-8"))
    payload["status"] = "approved"
    payload["advertised_by_worker_manifest"] = True

    with pytest.raises(ValidationError, match="approved artifacts, benchmark, legal ref"):
        ProviderCandidateManifestV1.model_validate(payload)


def test_evaluation_candidate_cannot_be_advertised() -> None:
    payload = json.loads(CANDIDATE_PATH.read_text(encoding="utf-8"))
    payload["advertised_by_worker_manifest"] = True

    with pytest.raises(ValidationError, match="cannot be advertised"):
        ProviderCandidateManifestV1.model_validate(payload)


def test_opencv_evaluation_lock_is_frozen() -> None:
    lock = REPOSITORY_ROOT / "workers/vision-gpu/providers/opencv-baseline.requirements.lock"

    assert hashlib.sha256(lock.read_bytes()).hexdigest() == (
        "ff9128c901530e0285efe0e258f6bef7314a72782d7650e25a315b41e7011e76"
    )
