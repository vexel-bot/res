from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from app.domain.studios.artifacts import (
    ArtifactInventoryV1,
    ProviderCandidateManifestV1,
    artifact_inventory_digest,
)

ROOT = Path(__file__).resolve().parents[2]
INVENTORY = ROOT / "workers/vision-gpu/providers/supervision-toolkit.artifacts.json"
CANDIDATE = ROOT / "workers/vision-gpu/providers/supervision-toolkit.provider.json"
CORPUS = ROOT / "benchmarks/studios/reality/supervision-benchmark-corpus.v1.json"
POLICY = ROOT / "benchmarks/studios/reality/supervision-shadow-policy.v1.json"
MANIFEST = ROOT / "workers/vision-gpu/worker.manifest.json"
ADAPTER = ROOT / "backend/app/providers/studios/supervision_detection.py"
ISOLATED_RUNTIME = ROOT / ".candidate-build/supervision-runtime"


def test_supervision_candidate_is_bound_and_not_advertised() -> None:
    inventory = ArtifactInventoryV1.model_validate_json(
        INVENTORY.read_text(encoding="utf-8")
    )
    candidate = ProviderCandidateManifestV1.model_validate_json(
        CANDIDATE.read_text(encoding="utf-8")
    )
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert candidate.capabilities == ["vision_normalization"]
    assert candidate.artifact_inventory_digest_sha256 == artifact_inventory_digest(
        inventory
    )
    assert candidate.code_digests_sha256[candidate.provider_ids[0]] == hashlib.sha256(
        ADAPTER.read_bytes()
    ).hexdigest()
    assert candidate.shadow_evidence_digest_sha256 == hashlib.sha256(
        (
            ROOT
            / "benchmarks/studios/reality/supervision-shadow-run-2026-08-28.v1.json"
        ).read_bytes()
    ).hexdigest()
    assert candidate.status == "evaluation"
    assert candidate.advertised_by_worker_manifest is False
    assert candidate.provider_ids[0] not in manifest["providers"]
    assert manifest["providers"] == []


def test_supervision_synthetic_shadow_is_non_authoritative_and_reversible(
    tmp_path: Path,
) -> None:
    output = tmp_path / "shadow-report.json"
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        [str(ISOLATED_RUNTIME), str(ROOT / "backend")]
    )
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.run_supervision_shadow",
            "--corpus",
            str(CORPUS),
            "--policy",
            str(POLICY),
            "--output",
            str(output),
        ],
        cwd=ROOT / "backend",
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert completed.returncode == 0, completed.stderr
    report = json.loads(output.read_text(encoding="utf-8"))

    assert report["technicalDecision"] == "passed"
    assert report["activationDecision"] == "incomplete"
    assert report["mode"] == "synthetic-shadow"
    assert report["candidate"]["advertisedByWorkerManifest"] is False
    assert report["candidate"]["influencedAuthoritativeOutput"] is False
    assert report["comparison"]["divergenceRate"] == 0
    assert report["operations"]["failureRate"] == 0
    assert report["operations"]["abstentionRate"] == 0
    assert report["operations"]["orphanEvidenceIds"] == []
    assert report["operations"]["orphanDerivedAssetCount"] == 0
    assert report["rollback"]["equivalent"] is True
    assert report["rollback"]["migrationRequired"] is False
    assert all(report["checks"].values())
    assert "oci_digest_missing" in report["activationBlockers"]
