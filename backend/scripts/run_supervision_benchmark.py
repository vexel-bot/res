"""Execute the frozen SV-2 synthetic benchmark against independent/OpenCV checks."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import platform
import socket
import time
import tracemalloc
from contextlib import AbstractContextManager
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from types import TracebackType
from typing import Any

import numpy as np

from app.domain.studios.contracts import AssetReferenceV1, FrameRateV1
from app.domain.studios.reality import (
    RealityAnalysisRequestV1,
    RealityFrameRangeV1,
    RealityShotV1,
)
from app.providers.studios.supervision_detection import (
    SupervisionAdapterConfig,
    SupervisionClassSpec,
    SupervisionDetectionAdapter,
    SupervisionFrameInput,
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CORPUS = (
    ROOT
    / "benchmarks/studios/reality/supervision-benchmark-corpus.v1.json"
)
VISION_MANIFEST = ROOT / "workers/vision-gpu/worker.manifest.json"
OPENCV_BASELINE_REPORT = (
    ROOT
    / "benchmarks/studios/reality/opencv-baseline-run-2026-08-25.v1.json"
)
FROZEN_TIME = datetime(2026, 8, 28, 0, 0, tzinfo=UTC)


class _NetworkDenied(AbstractContextManager[None]):
    def __enter__(self) -> None:
        self._connect = socket.socket.connect
        self._connect_ex = socket.socket.connect_ex
        self._create_connection = socket.create_connection

        def denied(*_args: object, **_kwargs: object) -> None:
            raise RuntimeError("supervision_benchmark_network_denied")

        socket.socket.connect = denied  # type: ignore[method-assign]
        socket.socket.connect_ex = denied  # type: ignore[method-assign]
        socket.create_connection = denied  # type: ignore[assignment]
        return None

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        socket.socket.connect = self._connect  # type: ignore[method-assign]
        socket.socket.connect_ex = self._connect_ex  # type: ignore[method-assign]
        socket.create_connection = self._create_connection  # type: ignore[assignment]
        return None


def main() -> int:
    args = _parse_args()
    corpus = json.loads(args.corpus.read_text(encoding="utf-8"))
    _validate_corpus(corpus)
    with _NetworkDenied():
        supervision = importlib.import_module("supervision")
        cv2 = importlib.import_module("cv2")
        if str(supervision.__version__) != "0.30.1":
            raise SystemExit(f"unexpected Supervision version: {supervision.__version__}")
        if str(cv2.__version__) != "4.13.0":
            raise SystemExit(f"unexpected OpenCV version: {cv2.__version__}")
        request = _request(corpus)
        frames = _frames(corpus, supervision)
        adapter = _adapter(supervision, render_overlays=False)
        first = adapter.project(
            request,
            frames,
            lambda _value: None,
            lambda: False,
            generated_at=FROZEN_TIME,
        )
        second = adapter.project(
            request,
            frames,
            lambda _value: None,
            lambda: False,
            generated_at=FROZEN_TIME,
        )
        fidelity = _adapter_fidelity(corpus, first.contribution)
        determinism = float(
            _contract_digest(first.contribution)
            == _contract_digest(second.contribution)
        )
        zone = _zone_benchmark(corpus, supervision, cv2)
        overlay = _overlay_benchmark(corpus, supervision, cv2)
        metrics = _metric_benchmark(corpus, supervision)
        invalid = _invalid_input_benchmark(request, adapter, supervision)
        performance = _projection_performance(request, frames, adapter)

    thresholds = corpus["thresholds"]
    checks = {
        "adapter_fidelity": fidelity >= thresholds["adapterFidelity"],
        "determinism": determinism >= thresholds["determinism"],
        "zone_parity": zone["parity"] >= thresholds["zoneParity"],
        "overlay_box_pixel_parity": overlay["pixelParity"]
        >= thresholds["overlayBoxPixelParity"],
        "metrics_match_independent_reference": metrics["absoluteErrorMax"]
        <= thresholds["metricAbsoluteErrorMax"],
        "perfect_case_map50": metrics["perfectCaseMap50"]
        >= thresholds["perfectCaseMap50Min"],
        "invalid_input_rejection": invalid["rejectionRate"]
        >= thresholds["invalidInputRejection"],
        "projection_throughput": performance["detectionsPerSecond"]
        >= thresholds["projectionDetectionsPerSecondMin"],
        "projection_peak_memory": performance["pythonPeakMemoryMib"]
        <= thresholds["projectionPythonPeakMemoryMibMax"],
        "zone_latency_ratio": zone["latencyRatioP95VsOpenCv"]
        <= thresholds["zoneLatencyRatioVsOpenCvP95Max"],
        "overlay_latency_ratio": overlay["latencyRatioP95VsOpenCv"]
        <= thresholds["overlayLatencyRatioVsOpenCvP95Max"],
        "network_denied": True,
        "synthetic_only": corpus["syntheticOnly"] is True,
        "worker_provider_manifest_empty": _providers_empty(),
    }
    report = {
        "schemaVersion": "clicko.supervision-benchmark-report.v1",
        "runId": f"supervision-sv2-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}",
        "generatedAt": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "corpus": {
            "id": corpus["corpusId"],
            "digestSha256": _sha256(args.corpus.read_bytes()),
            "caseCount": len(corpus["cases"]),
            "syntheticOnly": True,
            "humanData": False,
        },
        "candidate": {
            "name": "supervision",
            "version": str(supervision.__version__),
            "sourceRevision": "5f25aa0ee6dc22891415b6e3d2e1689ce7a32952",
            "status": "evaluation",
            "advertisedByWorkerManifest": False,
        },
        "environment": {
            "python": platform.python_version(),
            "numpy": str(np.__version__),
            "opencv": str(cv2.__version__),
            "platform": platform.platform(),
            "networkDeniedDuringRun": True,
            "runtime": "local-windows-isolated-target",
        },
        "results": {
            "adapterFidelity": fidelity,
            "determinism": determinism,
            "zones": zone,
            "overlays": overlay,
            "metrics": metrics,
            "invalidInputs": invalid,
            "performance": performance,
        },
        "thresholds": thresholds,
        "checks": checks,
        "technicalDecision": "passed" if all(checks.values()) else "failed",
        "activationDecision": "incomplete",
        "activationBlockers": [
            "inventory_status:incomplete",
            "linux_lock_missing",
            "oci_digest_missing",
            "sbom_missing",
            "provenance_missing",
            "signature_missing",
            "shadow_mode_not_run",
        ],
        "comparisonScope": {
            "openCvPrimitives": (
                "Polygon-zone bottom-center anchors and box rendering are compared "
                "directly with OpenCV 4.13.0 primitives."
            ),
            "existingRealityBaseline": str(OPENCV_BASELINE_REPORT.relative_to(ROOT)),
            "nonComparable": (
                "The existing OpenCV reality provider estimates horizon, camera motion "
                "and sparse tracks; Supervision is a toolkit projection layer, so its "
                "11-case quality score is referenced but not merged into this score."
            ),
        },
        "limitations": [
            "The corpus is synthetic and validates plumbing, not detector quality.",
            "Python tracemalloc excludes native allocator/codec memory.",
            "Windows evaluation does not satisfy the required Linux OCI supply-chain gate.",
            "No physical-world conclusion or provider promotion is authorized.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, separators=(",", ":")))
    return 0 if report["technicalDecision"] == "passed" else 2


def _adapter(supervision, *, render_overlays: bool) -> SupervisionDetectionAdapter:
    return SupervisionDetectionAdapter(
        SupervisionAdapterConfig(
            source_provider="synthetic.fixture-detector",
            source_provider_version="1.0.0",
            source_code_digest_sha256="a" * 64,
            model_id="synthetic-no-weights",
            model_revision="fixture-v1",
            model_digest_sha256="b" * 64,
            class_map={
                0: SupervisionClassSpec("Person", "person"),
                1: SupervisionClassSpec("Product", "rigid_object"),
            },
            render_overlays=render_overlays,
        ),
        supervision_module=supervision,
    )


def _request(corpus: dict[str, Any]) -> RealityAnalysisRequestV1:
    total_frames = len(corpus["cases"])
    return RealityAnalysisRequestV1(
        analysis_id="supervision-sv2-synthetic",
        workspace_id="workspace-supervision-sv2",
        source_asset=AssetReferenceV1(
            id="asset-supervision-sv2",
            version=1,
            media_type="video/mp4",
            checksum="c" * 64,
            origin="synthetic-test",
            rights_status="verified",
            provenance={"synthetic": True, "humanData": False},
        ),
        source_time_map_id="time-map-supervision-sv2",
        source_time_map_digest_sha256="d" * 64,
        frame_rate=FrameRateV1(numerator=30, denominator=1),
        total_frames=total_frames,
        shots=[
            RealityShotV1(
                shot_id="shot-supervision-sv2",
                frame_range=RealityFrameRangeV1(
                    start_frame=0,
                    end_frame_exclusive=total_frames,
                ),
                transition_in="start",
                transition_out="end",
            )
        ],
        analysis_policy_digest_sha256="e" * 64,
    )


def _frames(corpus: dict[str, Any], supervision) -> list[SupervisionFrameInput]:
    width = corpus["frame"]["width"]
    height = corpus["frame"]["height"]
    frames: list[SupervisionFrameInput] = []
    for frame_index, case in enumerate(corpus["cases"]):
        predictions = case["predictions"]
        frames.append(
            SupervisionFrameInput(
                frame_index=frame_index,
                width=width,
                height=height,
                detections=_detections(supervision, predictions, prediction=True),
            )
        )
    return frames


def _detections(supervision, items: list[dict[str, Any]], *, prediction: bool):
    boxes = np.array([item["xyxy"] for item in items], dtype=float).reshape(-1, 4)
    class_ids = np.array([item["classId"] for item in items], dtype=int)
    kwargs: dict[str, Any] = {"xyxy": boxes, "class_id": class_ids}
    if prediction:
        kwargs["confidence"] = np.array(
            [item["confidence"] for item in items], dtype=float
        )
        kwargs["tracker_id"] = np.array(
            [item["trackerId"] for item in items], dtype=int
        )
    return supervision.Detections(**kwargs)


def _adapter_fidelity(corpus: dict[str, Any], contribution) -> float:
    width = corpus["frame"]["width"]
    height = corpus["frame"]["height"]
    expected: list[tuple[Any, ...]] = []
    for frame_index, case in enumerate(corpus["cases"]):
        for item in case["predictions"]:
            expected.append(
                (
                    frame_index,
                    item["classId"],
                    item["confidence"],
                    *item["xyxy"],
                )
            )
    entities = {item.entity_id: item for item in contribution.entities}
    actual: list[tuple[Any, ...]] = []
    for track in contribution.tracks:
        class_id = entities[track.entity_id].properties["source_class_id"]
        for sample in track.samples:
            box = sample.bounding_box
            if box is None:
                continue
            actual.append(
                (
                    sample.frame_index,
                    class_id,
                    sample.confidence,
                    box.x_min * width,
                    box.y_min * height,
                    box.x_max * width,
                    box.y_max * height,
                )
            )
    expected.sort()
    actual.sort()
    if len(expected) != len(actual):
        return 0.0
    matches = sum(
        row_expected[:2] == row_actual[:2]
        and np.allclose(row_expected[2:], row_actual[2:], atol=1e-9)
        for row_expected, row_actual in zip(expected, actual, strict=True)
    )
    return matches / max(len(expected), 1)


def _zone_benchmark(corpus: dict[str, Any], supervision, cv2) -> dict[str, Any]:
    polygon = np.array(corpus["polygonZone"], dtype=np.int64)
    parity_rows: list[bool] = []
    supervision_times: list[float] = []
    opencv_times: list[float] = []
    for case in corpus["cases"]:
        detections = _detections(supervision, case["predictions"], prediction=True)
        zone = supervision.PolygonZone(polygon=polygon)
        started = time.perf_counter_ns()
        observed = zone.trigger(detections).tolist()
        supervision_times.append((time.perf_counter_ns() - started) / 1_000_000)
        started = time.perf_counter_ns()
        reference = [
            _inside_polygon(cv2, polygon, item["xyxy"])
            for item in case["predictions"]
        ]
        opencv_times.append((time.perf_counter_ns() - started) / 1_000_000)
        parity_rows.append(observed == reference == case["expectedZone"])

    perf_detections = _detections(
        supervision,
        [
            {
                "xyxy": [10 + (index % 10) * 12, 10, 20 + (index % 10) * 12, 40],
                "classId": 0,
                "confidence": 0.9,
                "trackerId": index,
            }
            for index in range(100)
        ],
        prediction=True,
    )
    perf_items = [
        {"xyxy": item.tolist()}
        for item in np.asarray(perf_detections.xyxy)
    ]
    supervision_times = []
    opencv_times = []
    for _ in range(100):
        zone = supervision.PolygonZone(polygon=polygon)
        started = time.perf_counter_ns()
        zone.trigger(perf_detections)
        supervision_times.append((time.perf_counter_ns() - started) / 1_000_000)
        started = time.perf_counter_ns()
        [_inside_polygon(cv2, polygon, item["xyxy"]) for item in perf_items]
        opencv_times.append((time.perf_counter_ns() - started) / 1_000_000)
    supervision_p95 = _p95(supervision_times)
    opencv_p95 = max(_p95(opencv_times), 1e-9)
    return {
        "parity": sum(parity_rows) / len(parity_rows),
        "caseCount": len(parity_rows),
        "supervisionLatencyP95Ms": supervision_p95,
        "openCvLatencyP95Ms": opencv_p95,
        "latencyRatioP95VsOpenCv": supervision_p95 / opencv_p95,
    }


def _inside_polygon(cv2, polygon: np.ndarray, xyxy: list[float]) -> bool:
    x1, _y1, x2, y2 = xyxy
    point = (float(np.rint((x1 + x2) / 2)), float(np.rint(y2)))
    return bool(cv2.pointPolygonTest(polygon, point, False) >= 0)


def _overlay_benchmark(corpus: dict[str, Any], supervision, cv2) -> dict[str, Any]:
    width = corpus["frame"]["width"]
    height = corpus["frame"]["height"]
    parity: list[bool] = []
    detections = [
        _detections(supervision, case["predictions"], prediction=True)
        for case in corpus["cases"]
    ]
    annotator = supervision.BoxAnnotator(
        color=supervision.Color.RED,
        thickness=2,
        color_lookup=supervision.ColorLookup.INDEX,
    )
    for case_detections in detections:
        scene = np.zeros((height, width, 3), dtype=np.uint8)
        observed = annotator.annotate(
            scene=scene.copy(),
            detections=case_detections,
        )
        reference = scene.copy()
        for raw_box in case_detections.xyxy.astype(int):
            x1, y1, x2, y2 = (int(value) for value in raw_box)
            cv2.rectangle(reference, (x1, y1), (x2, y2), (0, 0, 255), 2)
        parity.append(bool(np.array_equal(observed, reference)))

    perf = _detections(
        supervision,
        [
            {
                "xyxy": [10 + (index % 10) * 12, 10, 20 + (index % 10) * 12, 40],
                "classId": 0,
                "confidence": 0.9,
                "trackerId": index,
            }
            for index in range(100)
        ],
        prediction=True,
    )
    supervision_times: list[float] = []
    opencv_times: list[float] = []
    for _ in range(100):
        scene = np.zeros((height, width, 3), dtype=np.uint8)
        started = time.perf_counter_ns()
        annotator.annotate(scene=scene, detections=perf)
        supervision_times.append((time.perf_counter_ns() - started) / 1_000_000)
        scene = np.zeros((height, width, 3), dtype=np.uint8)
        started = time.perf_counter_ns()
        for raw_box in perf.xyxy.astype(int):
            x1, y1, x2, y2 = (int(value) for value in raw_box)
            cv2.rectangle(scene, (x1, y1), (x2, y2), (0, 0, 255), 2)
        opencv_times.append((time.perf_counter_ns() - started) / 1_000_000)
    supervision_p95 = _p95(supervision_times)
    opencv_p95 = max(_p95(opencv_times), 1e-9)
    return {
        "pixelParity": sum(parity) / len(parity),
        "caseCount": len(parity),
        "supervisionLatencyP95Ms": supervision_p95,
        "openCvLatencyP95Ms": opencv_p95,
        "latencyRatioP95VsOpenCv": supervision_p95 / opencv_p95,
    }


def _metric_benchmark(corpus: dict[str, Any], supervision) -> dict[str, Any]:
    metrics_cases = [case for case in corpus["cases"] if case["includeInMetrics"]]
    predictions = [
        _detections(supervision, case["predictions"], prediction=True)
        for case in metrics_cases
    ]
    targets = [
        _detections(supervision, case["targets"], prediction=False)
        for case in metrics_cases
    ]
    metric_module = importlib.import_module("supervision.metrics")
    observed = {
        "precision": float(
            metric_module.Precision().update(predictions, targets).compute().precision_at_50
        ),
        "recall": float(
            metric_module.Recall().update(predictions, targets).compute().recall_at_50
        ),
        "f1": float(
            metric_module.F1Score().update(predictions, targets).compute().f1_50
        ),
    }
    reference = _independent_detection_metrics(metrics_cases)
    expected = corpus["expectedAggregateAtIou50"]
    if any(reference[key] != expected[key] for key in ("truePositive", "falsePositive", "falseNegative")):
        raise ValueError("independent metric counts diverge from frozen corpus")
    errors = [abs(observed[key] - reference[key]) for key in ("precision", "recall", "f1")]
    perfect_prediction = supervision.Detections(
        xyxy=np.array([[10, 10, 40, 40]], dtype=float),
        class_id=np.array([0]),
        confidence=np.array([0.99]),
    )
    perfect_target = supervision.Detections(
        xyxy=np.array([[10, 10, 40, 40]], dtype=float),
        class_id=np.array([0]),
    )
    map50 = float(
        metric_module.MeanAveragePrecision()
        .update(perfect_prediction, perfect_target)
        .compute()
        .map50
    )
    return {
        "observed": observed,
        "independentReference": reference,
        "absoluteErrorMax": max(errors),
        "perfectCaseMap50": map50,
    }


def _independent_detection_metrics(cases: list[dict[str, Any]]) -> dict[str, Any]:
    true_positive = 0
    false_positive = 0
    false_negative = 0
    for case in cases:
        targets = case["targets"]
        unmatched = set(range(len(targets)))
        for prediction in sorted(
            case["predictions"],
            key=lambda item: item["confidence"],
            reverse=True,
        ):
            candidates = [
                (index, _iou(prediction["xyxy"], target["xyxy"]))
                for index, target in enumerate(targets)
                if index in unmatched and target["classId"] == prediction["classId"]
            ]
            best = max(candidates, key=lambda item: item[1], default=None)
            if best is not None and best[1] >= 0.5:
                true_positive += 1
                unmatched.remove(best[0])
            else:
                false_positive += 1
        false_negative += len(unmatched)
    precision = true_positive / max(true_positive + false_positive, 1)
    recall = true_positive / max(true_positive + false_negative, 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-12)
    return {
        "truePositive": true_positive,
        "falsePositive": false_positive,
        "falseNegative": false_negative,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def _iou(first: list[float], second: list[float]) -> float:
    intersection_width = max(0.0, min(first[2], second[2]) - max(first[0], second[0]))
    intersection_height = max(0.0, min(first[3], second[3]) - max(first[1], second[1]))
    intersection = intersection_width * intersection_height
    first_area = (first[2] - first[0]) * (first[3] - first[1])
    second_area = (second[2] - second[0]) * (second[3] - second[1])
    return intersection / max(first_area + second_area - intersection, 1e-12)


def _invalid_input_benchmark(request, adapter, supervision) -> dict[str, Any]:
    invalid_boxes = [
        [-1, 0, 10, 10],
        [0, 0, 321, 10],
        [10, 10, 10, 20],
        [float("nan"), 0, 10, 10],
    ]
    rejected = 0
    for box in invalid_boxes:
        frame = SupervisionFrameInput(
            frame_index=0,
            width=320,
            height=180,
            detections=supervision.Detections(
                xyxy=np.array([box], dtype=float),
                class_id=np.array([0]),
                confidence=np.array([0.9]),
                tracker_id=np.array([1]),
            ),
        )
        try:
            adapter.project(request, [frame], lambda _value: None, lambda: False)
        except ValueError:
            rejected += 1
    return {
        "caseCount": len(invalid_boxes),
        "rejected": rejected,
        "rejectionRate": rejected / len(invalid_boxes),
    }


def _projection_performance(request, frames, adapter) -> dict[str, Any]:
    detection_count = sum(len(frame.detections) for frame in frames)
    latencies: list[float] = []
    for _ in range(30):
        started = time.perf_counter_ns()
        adapter.project(
            request,
            frames,
            lambda _value: None,
            lambda: False,
            generated_at=FROZEN_TIME,
        )
        latencies.append((time.perf_counter_ns() - started) / 1_000_000)
    tracemalloc.start()
    adapter.project(
        request,
        frames,
        lambda _value: None,
        lambda: False,
        generated_at=FROZEN_TIME,
    )
    _current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    average_ms = mean(latencies)
    return {
        "iterations": len(latencies),
        "detectionsPerIteration": detection_count,
        "latencyMeanMs": average_ms,
        "latencyP95Ms": _p95(latencies),
        "detectionsPerSecond": detection_count / max(average_ms / 1000, 1e-12),
        "pythonPeakMemoryMib": peak / (1024 * 1024),
    }


def _validate_corpus(corpus: dict[str, Any]) -> None:
    if corpus.get("schemaVersion") != "clicko.supervision-benchmark-corpus.v1":
        raise ValueError("unexpected benchmark corpus schema")
    if corpus.get("syntheticOnly") is not True or corpus.get("humanData") is not False:
        raise ValueError("SV-2 corpus must be synthetic and non-human")
    if not corpus.get("cases") or not corpus.get("thresholds"):
        raise ValueError("SV-2 corpus requires cases and frozen thresholds")


def _providers_empty() -> bool:
    manifest = json.loads(VISION_MANIFEST.read_text(encoding="utf-8"))
    return manifest["providers"] == []


def _contract_digest(contract) -> str:
    return _digest(
        contract.model_dump(mode="json", by_alias=True, exclude_none=True)
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


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _p95(values: list[float]) -> float:
    return float(np.percentile(np.asarray(values, dtype=float), 95))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
