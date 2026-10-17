from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORPUS = (
    ROOT
    / "benchmarks/studios/reality/supervision-benchmark-corpus.v1.json"
)
REPORT = (
    ROOT
    / "benchmarks/studios/reality/supervision-benchmark-run-2026-08-28.v1.json"
)
VISION_MANIFEST = ROOT / "workers/vision-gpu/worker.manifest.json"


def test_supervision_benchmark_is_bound_to_frozen_synthetic_corpus() -> None:
    corpus_bytes = CORPUS.read_bytes()
    corpus = json.loads(corpus_bytes)
    report = json.loads(REPORT.read_text(encoding="utf-8"))

    assert corpus["schemaVersion"] == "clicko.supervision-benchmark-corpus.v1"
    assert corpus["syntheticOnly"] is True
    assert corpus["humanData"] is False
    assert len(corpus["cases"]) == 8
    assert report["corpus"]["digestSha256"] == hashlib.sha256(
        corpus_bytes
    ).hexdigest()
    assert report["corpus"]["caseCount"] == len(corpus["cases"])
    assert report["thresholds"] == corpus["thresholds"]


def test_supervision_sv2_passes_technical_gates_without_promotion() -> None:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    result = report["results"]

    assert report["candidate"]["version"] == "0.30.1"
    assert report["candidate"]["sourceRevision"] == (
        "5f25aa0ee6dc22891415b6e3d2e1689ce7a32952"
    )
    assert report["technicalDecision"] == "passed"
    assert report["activationDecision"] == "incomplete"
    assert report["candidate"]["advertisedByWorkerManifest"] is False
    assert all(report["checks"].values())
    assert result["adapterFidelity"] == 1.0
    assert result["determinism"] == 1.0
    assert result["zones"]["parity"] == 1.0
    assert result["overlays"]["pixelParity"] == 1.0
    assert result["metrics"]["absoluteErrorMax"] == 0.0
    assert result["invalidInputs"]["rejectionRate"] == 1.0
    assert "sbom_missing" in report["activationBlockers"]
    assert "shadow_mode_not_run" in report["activationBlockers"]


def test_benchmark_does_not_activate_runtime_or_make_physics_claims() -> None:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    manifest = json.loads(VISION_MANIFEST.read_text(encoding="utf-8"))

    assert manifest["providers"] == []
    assert report["environment"]["networkDeniedDuringRun"] is True
    assert report["corpus"]["humanData"] is False
    assert any(
        "No physical-world conclusion" in limitation
        for limitation in report["limitations"]
    )
    assert "nonComparable" in report["comparisonScope"]
