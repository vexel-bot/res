import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from app.domain.studios.artifacts import (
    ArtifactInventoryV1,
    ProviderCandidateManifestV1,
    ProviderPromotionEvidenceV1,
    artifact_inventory_digest,
    evaluate_provider_promotion_gate,
    provider_candidate_manifest_digest,
)
from app.services.studios.worker_runtime import load_worker_manifest, manifest_digest

ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 8, 25, 23, 0, tzinfo=UTC)
SHA = "a" * 64


def load_inputs() -> tuple[ProviderCandidateManifestV1, ArtifactInventoryV1, object]:
    candidate = ProviderCandidateManifestV1.model_validate_json(
        (ROOT / "workers/vision-gpu/providers/opencv-baseline.provider.json").read_text(
            encoding="utf-8"
        )
    )
    inventory = ArtifactInventoryV1.model_validate_json(
        (ROOT / "benchmarks/studios/reality/pgv1-artifact-inventory.v1.json").read_text(
            encoding="utf-8"
        )
    )
    manifest = load_worker_manifest(ROOT / "workers/vision-gpu/worker.manifest.json")
    return candidate, inventory, manifest


def evidence_for(candidate, inventory, manifest, **updates):
    payload = {
        "candidate_id": candidate.candidate_id,
        "candidate_manifest_digest_sha256": provider_candidate_manifest_digest(candidate),
        "artifact_inventory_id": inventory.inventory_id,
        "artifact_inventory_digest_sha256": artifact_inventory_digest(inventory),
        "artifact_inventory_status": inventory.status,
        "benchmark_evidence_digest_sha256": SHA,
        "legal_approval_ref": "legal-review-pending",
        "image_digest": "sha256:" + SHA,
        "image_sbom_digest_sha256": SHA,
        "image_provenance_digest_sha256": SHA,
        "worker_manifest_digest_sha256": manifest_digest(manifest),
        "image_platform": "linux/amd64",
        "worker_manifest_advertised": False,
        "attestation_verified": False,
        "no_egress_verified": False,
        "cleanup_verified": False,
        "tenant_scoped_storage_verified": False,
        "promoted_at": NOW,
        "promoted_by": "release-gate",
    }
    payload.update(updates)
    return ProviderPromotionEvidenceV1.model_validate(payload)


def test_current_opencv_candidate_can_never_promote_from_preflight_inputs():
    candidate, inventory, manifest = load_inputs()
    evidence = evidence_for(candidate, inventory, manifest)

    result = evaluate_provider_promotion_gate(
        candidate,
        inventory,
        evidence,
        manifest,
        evaluated_at=NOW,
    )

    assert result.decision == "blocked"
    assert "worker_provider_advertisement_mismatch" in result.blocking_reasons
    assert "candidate_status:evaluation" in result.incomplete_reasons
    assert "artifact_inventory_status:review_required" in result.incomplete_reasons
    assert "preflight_runtime_not_promotable" in result.incomplete_reasons


def test_promotion_evidence_tampering_is_a_binding_failure():
    candidate, inventory, manifest = load_inputs()
    evidence = evidence_for(
        candidate,
        inventory,
        manifest,
        candidate_manifest_digest_sha256="b" * 64,
    )

    result = evaluate_provider_promotion_gate(
        candidate,
        inventory,
        evidence,
        manifest,
        evaluated_at=NOW,
    )

    assert result.decision == "blocked"
    assert "candidate_manifest_binding_mismatch" in result.blocking_reasons


def test_promotion_cli_fails_closed_without_changing_worker_manifest(tmp_path):
    candidate, inventory, manifest = load_inputs()
    evidence = evidence_for(candidate, inventory, manifest)
    evidence_path = tmp_path / "evidence.json"
    evidence_path.write_text(evidence.model_dump_json(by_alias=True), encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "backend/scripts/evaluate_provider_promotion.py"),
            "--backend",
            str(ROOT / "backend"),
            "--candidate",
            str(ROOT / "workers/vision-gpu/providers/opencv-baseline.provider.json"),
            "--inventory",
            str(ROOT / "benchmarks/studios/reality/pgv1-artifact-inventory.v1.json"),
            "--evidence",
            str(evidence_path),
            "--manifest",
            str(ROOT / "workers/vision-gpu/worker.manifest.json"),
            "--evaluated-at",
            "2026-08-25T23:00:00Z",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 2
    assert '"decision": "blocked"' in completed.stdout
    assert '"worker_provider_advertisement_mismatch"' in completed.stdout
