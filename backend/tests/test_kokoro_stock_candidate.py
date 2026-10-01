from __future__ import annotations

import hashlib
import json
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
from app.domain.studios.benchmarking import BenchmarkPolicyV1, benchmark_policy_digest
from app.services.studios.worker_runtime import load_worker_manifest, manifest_digest

ROOT = Path(__file__).resolve().parents[2]
PROVIDER_ROOT = ROOT / "workers" / "speech-cpu" / "providers"
NOW = datetime(2026, 8, 25, 23, 45, tzinfo=UTC)


def _load_inputs():
    inventory = ArtifactInventoryV1.model_validate_json(
        (PROVIDER_ROOT / "kokoro-82m-stock.artifacts.json").read_text(encoding="utf-8")
    )
    candidate = ProviderCandidateManifestV1.model_validate_json(
        (PROVIDER_ROOT / "kokoro-82m-stock.provider.json").read_text(encoding="utf-8")
    )
    policy = BenchmarkPolicyV1.model_validate_json(
        (ROOT / "benchmarks/studios/identity/voice-stock-pt-br-policy.v1.json").read_text(
            encoding="utf-8"
        )
    )
    worker = load_worker_manifest(ROOT / "workers/speech-cpu/worker.manifest.json")
    return inventory, candidate, policy, worker


def test_kokoro_candidate_is_bound_but_stays_unadvertised_and_incomplete():
    inventory, candidate, policy, worker = _load_inputs()
    policy_candidate = next(item for item in policy.candidates if item.candidate_id == candidate.candidate_id)
    records = {item.artifact_id: item for item in inventory.artifacts}

    assert inventory.policy_digests_sha256 == [benchmark_policy_digest(policy)]
    assert candidate.artifact_inventory_digest_sha256 == artifact_inventory_digest(inventory)
    assert candidate.required_artifact_ids == inventory.required_artifact_ids
    assert candidate.status == "evaluation"
    assert inventory.status == "incomplete"
    assert candidate.advertised_by_worker_manifest is False
    assert worker.providers == []
    assert candidate.benchmark_evidence_digest_sha256 is None
    assert candidate.legal_approval_ref is None
    assert {item.component_id: item.source_revision for item in policy_candidate.components} == {
        component_id: records[component_id].source_revision
        for component_id in (
            "kokoro-code",
            "kokoro-82m-weights",
            "misaki-g2p",
            "espeak-ng-runtime",
        )
    }
    assert {
        item.artifact_id for item in inventory.artifacts if item.resolution_status == "unresolved"
    } == {"kokoro-82m-weights", "speech-cpu-candidate-container"}

    implementation = ROOT / "backend/app/providers/studios/kokoro_stock.py"
    assert candidate.code_digests_sha256["kokoro-82m-stock"] == hashlib.sha256(
        implementation.read_bytes()
    ).hexdigest()
    defaults = {
        "allowedVoices": ["pf_dora", "pm_alex", "pm_santa"],
        "languageCode": "p",
        "locale": "pt-BR",
        "maxChunkCharacters": 320,
        "sampleRate": 24_000,
    }
    canonical = json.dumps(defaults, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    assert candidate.default_parameters_digest_sha256 == hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()


def test_speech_candidate_cannot_promote_through_provider_empty_preflight():
    inventory, candidate, _policy, worker = _load_inputs()
    evidence = ProviderPromotionEvidenceV1(
        candidate_id=candidate.candidate_id,
        candidate_manifest_digest_sha256=provider_candidate_manifest_digest(candidate),
        artifact_inventory_id=inventory.inventory_id,
        artifact_inventory_digest_sha256=artifact_inventory_digest(inventory),
        artifact_inventory_status=inventory.status,
        benchmark_evidence_digest_sha256="a" * 64,
        legal_approval_ref="legal-review-pending",
        image_digest=f"sha256:{'b' * 64}",
        image_sbom_digest_sha256="c" * 64,
        image_provenance_digest_sha256="d" * 64,
        worker_manifest_digest_sha256=manifest_digest(worker),
        image_platform="linux/amd64",
        worker_manifest_advertised=False,
        attestation_verified=False,
        no_egress_verified=False,
        cleanup_verified=False,
        tenant_scoped_storage_verified=False,
        promoted_at=NOW,
        promoted_by="release-gate",
    )

    gate = evaluate_provider_promotion_gate(
        candidate,
        inventory,
        evidence,
        worker,
        evaluated_at=NOW,
    )

    assert gate.decision == "blocked"
    assert "worker_provider_advertisement_mismatch" in gate.blocking_reasons
    assert "worker_capability_mismatch" not in gate.blocking_reasons
    assert "candidate_status:evaluation" in gate.incomplete_reasons
    assert "artifact_inventory_status:incomplete" in gate.incomplete_reasons
