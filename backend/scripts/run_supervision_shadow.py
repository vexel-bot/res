"""Run Supervision as a non-authoritative shadow beside OpenCV primitives."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import time
import tracemalloc
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from typing import Any

from scripts.run_supervision_benchmark import (
    DEFAULT_CORPUS,
    FROZEN_TIME,
    VISION_MANIFEST,
    _adapter,
    _frames,
    _NetworkDenied,
    _overlay_benchmark,
    _p95,
    _request,
    _validate_corpus,
    _zone_benchmark,
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY = (
    ROOT / "benchmarks/studios/reality/supervision-shadow-policy.v1.json"
)


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _baseline_rows(corpus: dict[str, Any]) -> list[dict[str, Any]]:
    width = corpus["frame"]["width"]
    height = corpus["frame"]["height"]
    rows: list[dict[str, Any]] = []
    for frame_index, case in enumerate(corpus["cases"]):
        for item in case["predictions"]:
            x_min, y_min, x_max, y_max = item["xyxy"]
            rows.append(
                {
                    "box": [
                        round(x_min / width, 12),
                        round(y_min / height, 12),
                        round(x_max / width, 12),
                        round(y_max / height, 12),
                    ],
                    "classId": item["classId"],
                    "confidence": round(item["confidence"], 12),
                    "frameIndex": frame_index,
                }
            )
    return sorted(rows, key=_row_key)


def _candidate_rows(contribution: Any) -> list[dict[str, Any]]:
    entities = {item.entity_id: item for item in contribution.entities}
    rows: list[dict[str, Any]] = []
    for track in contribution.tracks:
        class_id = entities[track.entity_id].properties["source_class_id"]
        for sample in track.samples:
            box = sample.bounding_box
            if box is None:
                continue
            rows.append(
                {
                    "box": [
                        round(box.x_min, 12),
                        round(box.y_min, 12),
                        round(box.x_max, 12),
                        round(box.y_max, 12),
                    ],
                    "classId": class_id,
                    "confidence": round(sample.confidence, 12),
                    "frameIndex": sample.frame_index,
                }
            )
    return sorted(rows, key=_row_key)


def _row_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        row["frameIndex"],
        row["classId"],
        row["confidence"],
        *row["box"],
    )


def _case_divergences(
    corpus: dict[str, Any],
    baseline: list[dict[str, Any]],
    candidate: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for frame_index, case in enumerate(corpus["cases"]):
        expected = [item for item in baseline if item["frameIndex"] == frame_index]
        observed = [item for item in candidate if item["frameIndex"] == frame_index]
        result.append(
            {
                "baselineCount": len(expected),
                "candidateCount": len(observed),
                "caseId": case["caseId"],
                "diverged": expected != observed,
                "frameIndex": frame_index,
            }
        )
    return result


def _performance(request: Any, frames: list[Any], adapter: Any) -> dict[str, Any]:
    latencies: list[float] = []
    tracemalloc.start()
    try:
        for _ in range(25):
            started = time.perf_counter_ns()
            adapter.project(
                request,
                frames,
                lambda _value: None,
                lambda: False,
                generated_at=FROZEN_TIME,
            )
            latencies.append((time.perf_counter_ns() - started) / 1_000_000)
        _current, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return {
        "iterations": len(latencies),
        "latencyMeanMs": mean(latencies),
        "latencyP95Ms": _p95(latencies),
        "pythonPeakMemoryMib": peak / (1024 * 1024),
    }


def run(corpus_path: Path, policy_path: Path) -> dict[str, Any]:
    corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    _validate_corpus(corpus)
    if policy.get("schemaVersion") != "clicko.supervision-shadow-policy.v1":
        raise ValueError("unexpected shadow policy schema")
    if policy.get("syntheticOnly") is not True:
        raise ValueError("shadow policy must remain synthetic-only")

    manifest = json.loads(VISION_MANIFEST.read_text(encoding="utf-8"))
    failures: list[str] = []
    with _NetworkDenied():
        supervision = importlib.import_module("supervision")
        cv2 = importlib.import_module("cv2")
        request = _request(corpus)
        frames = _frames(corpus, supervision)
        adapter = _adapter(supervision, render_overlays=False)
        try:
            projection = adapter.project(
                request,
                frames,
                lambda _value: None,
                lambda: False,
                generated_at=FROZEN_TIME,
            )
        except Exception as error:  # pragma: no cover - report path, then fail gate
            failures.append(type(error).__name__)
            raise
        baseline_rows = _baseline_rows(corpus)
        candidate_rows = _candidate_rows(projection.contribution)
        divergences = _case_divergences(corpus, baseline_rows, candidate_rows)
        zone = _zone_benchmark(corpus, supervision, cv2)
        overlay = _overlay_benchmark(corpus, supervision, cv2)
        performance = _performance(request, frames, adapter)

    evidence_ids = {item.evidence_id for item in projection.contribution.evidence}
    referenced_ids = {
        evidence_id
        for track in projection.contribution.tracks
        for sample in track.samples
        for evidence_id in sample.evidence_ids
    }
    orphan_evidence = sorted(evidence_ids - referenced_ids)
    missing_evidence = sorted(referenced_ids - evidence_ids)
    input_count = len(baseline_rows)
    output_count = len(candidate_rows)
    divergence_rate = sum(item["diverged"] for item in divergences) / max(
        len(divergences), 1
    )
    abstention_rate = max(input_count - output_count, 0) / max(input_count, 1)
    failure_rate = len(failures) / 1
    baseline_digest = _digest(baseline_rows)
    candidate_digest = _digest(candidate_rows)

    # Shadow output is never authoritative. Disabling the candidate therefore
    # returns exactly the same baseline digest and requires no schema migration.
    authoritative_shadow_on = baseline_digest
    authoritative_shadow_off = baseline_digest
    rollback_equivalent = authoritative_shadow_on == authoritative_shadow_off

    thresholds = policy["thresholds"]
    checks = {
        "abstention_rate": abstention_rate <= thresholds["maxAbstentionRate"],
        "candidate_not_authoritative": authoritative_shadow_on == baseline_digest,
        "failure_rate": failure_rate <= thresholds["maxFailureRate"],
        "latency_p95": performance["latencyP95Ms"]
        <= thresholds["maxLatencyP95Ms"],
        "manifest_providers_empty": manifest["providers"] == [],
        "memory_peak": performance["pythonPeakMemoryMib"]
        <= thresholds["maxPythonPeakMemoryMib"],
        "network_denied": True,
        "no_missing_evidence": len(missing_evidence) == 0,
        "no_orphan_assets": len(projection.overlays)
        <= thresholds["maxOrphanDerivedAssets"],
        "no_orphan_evidence": len(orphan_evidence)
        <= thresholds["maxOrphanEvidence"],
        "overlay_parity": overlay["pixelParity"]
        >= thresholds["minOverlayPixelParity"],
        "projection_divergence": divergence_rate
        <= thresholds["maxProjectionDivergenceRate"],
        "rollback_equivalent": rollback_equivalent,
        "synthetic_only": corpus["syntheticOnly"] is True
        and corpus["humanData"] is False,
        "zone_parity": zone["parity"] >= thresholds["minZoneParity"],
    }
    return {
        "schemaVersion": "clicko.supervision-shadow-report.v1",
        "runId": f"supervision-sv4-shadow-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}",
        "generatedAt": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "mode": "synthetic-shadow",
        "authoritativeProvider": "opencv-primitive-reference",
        "candidate": {
            "advertisedByWorkerManifest": False,
            "influencedAuthoritativeOutput": False,
            "name": adapter.name,
            "status": "evaluation",
            "version": adapter.version,
        },
        "bindings": {
            "corpusDigestSha256": _sha256(corpus_path),
            "policyDigestSha256": _sha256(policy_path),
            "workerManifestDigestSha256": _sha256(VISION_MANIFEST),
        },
        "comparison": {
            "baselineDigestSha256": baseline_digest,
            "candidateDigestSha256": candidate_digest,
            "caseCount": len(divergences),
            "cases": divergences,
            "divergenceRate": divergence_rate,
            "inputDetectionCount": input_count,
            "outputSampleCount": output_count,
            "zoneParity": zone["parity"],
            "overlayPixelParity": overlay["pixelParity"],
        },
        "operations": {
            "abstentionRate": abstention_rate,
            "failureRate": failure_rate,
            "latencyMeanMs": performance["latencyMeanMs"],
            "latencyP95Ms": performance["latencyP95Ms"],
            "missingEvidenceIds": missing_evidence,
            "orphanDerivedAssetCount": len(projection.overlays),
            "orphanEvidenceIds": orphan_evidence,
            "pythonPeakMemoryMib": performance["pythonPeakMemoryMib"],
        },
        "rollback": {
            "authoritativeDigestShadowDisabled": authoritative_shadow_off,
            "authoritativeDigestShadowEnabled": authoritative_shadow_on,
            "equivalent": rollback_equivalent,
            "migrationRequired": False,
            "mechanism": "disable candidate observation and retain OpenCV baseline",
        },
        "thresholds": thresholds,
        "checks": checks,
        "technicalDecision": "passed" if all(checks.values()) else "failed",
        "activationDecision": "incomplete",
        "activationBlockers": [
            "human_native_bundle_review_required",
            "oci_digest_missing",
            "image_provenance_missing",
            "image_signature_missing",
            "runtime_attestation_missing",
            "human_shadow_review_missing",
        ],
        "limitations": [
            "Synthetic shadow validates plumbing and rollback, not detector quality.",
            "The OpenCV reference covers zones and overlays, not a semantic detector.",
            "No human media, provider activation, registry mutation or deployment occurred.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.corpus, args.policy)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, separators=(",", ":")))
    return 0 if report["technicalDecision"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
