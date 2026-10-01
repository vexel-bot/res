"""Execute the frozen PGV-1 synthetic corpus against the unadvertised OpenCV baseline.

The runner intentionally creates its videos in an ephemeral directory and emits a
versioned report plus a separate activation gate. It never mutates the worker
manifest or installs a provider into the production registry.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from app.domain.studios.artifacts import ProviderCandidateManifestV1
from app.domain.studios.contracts import AssetReferenceV1, FrameRateV1
from app.domain.studios.reality import (
    RealityAnalysisRequestV1,
    RealityFrameRangeV1,
    RealityModelV1,
    RealityShotV1,
)
from app.domain.studios.reality_benchmark import (
    RealityPerceptionBenchmarkReportV1,
    RealityPerceptionEnvironmentV1,
    RealityPerceptionObservationV1,
    SyntheticRealityCaseV1,
    SyntheticRealityCorpusV1,
    evaluate_reality_perception_report,
    synthetic_reality_corpus_digest,
)
from app.providers.studios.opencv_reality import (
    OpenCVGeometryProvider,
    OpenCVPointTrackingProvider,
    OpenCVRealityConfig,
)
from app.providers.studios.reality_scene import CanonicalContributionSceneProvider
from app.services.studios.reality_analysis import RealityAnalysisOrchestrator

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CORPUS = ROOT / "benchmarks" / "studios" / "reality" / "opencv-baseline-corpus.v1.json"
DEFAULT_CANDIDATE = ROOT / "workers" / "vision-gpu" / "providers" / "opencv-baseline.provider.json"
DEFAULT_LOCK = ROOT / "workers" / "vision-gpu" / "providers" / "opencv-baseline.requirements.lock"


def main() -> int:
    args = _parse_args()
    cv2 = _load_cv2()
    corpus = SyntheticRealityCorpusV1.model_validate_json(args.corpus.read_text(encoding="utf-8"))
    candidate = ProviderCandidateManifestV1.model_validate_json(
        args.candidate.read_text(encoding="utf-8")
    )
    corpus_digest = synthetic_reality_corpus_digest(corpus)
    if corpus.candidate_id != candidate.candidate_id:
        raise SystemExit("corpus candidate_id does not match candidate manifest")

    config = OpenCVRealityConfig(
        sample_stride_frames=2,
        max_samples_per_shot=90,
        max_features_per_shot=48,
        minimum_track_samples=3,
    )
    _assert_runtime_matches_lock(args.lock, cv2)
    observations: list[RealityPerceptionObservationV1] = []
    with tempfile.TemporaryDirectory(prefix="clicko-pgv1-opencv-") as temp_dir:
        temporary_root = Path(temp_dir)
        for case in corpus.cases:
            source = temporary_root / f"{case.case_id}.mp4"
            _write_case_video(cv2, case, source)
            observations.append(_run_case(cv2, config, case, source))

    report = RealityPerceptionBenchmarkReportV1(
        report_id=f"opencv-baseline-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}",
        corpus_id=corpus.corpus_id,
        corpus_digest_sha256=corpus_digest,
        candidate_id=candidate.candidate_id,
        candidate_manifest_digest_sha256=_candidate_digest(candidate),
        generated_at=datetime.now(UTC),
        environment=RealityPerceptionEnvironmentV1(
            python_version=platform.python_version(),
            opencv_version=str(cv2.__version__),
            numpy_version=str(np.__version__),
            operating_system=platform.platform(),
            architecture=platform.machine(),
            dependency_lock_digest_sha256=_sha256(args.lock.read_bytes()),
            isolated_environment=True,
            synthetic_only=True,
        ),
        observations=observations,
    )
    gate = evaluate_reality_perception_report(
        corpus,
        candidate,
        report,
        evaluated_at=datetime.now(UTC),
    )
    result = {
        "report": report.model_dump(mode="json", by_alias=True),
        "gate": gate.model_dump(mode="json", by_alias=True),
        "run_policy": {
            "synthetic_only": True,
            "isolated_environment": True,
            "candidate_status_at_run": candidate.status,
            "provider_registered": False,
            "worker_manifest_advertised": candidate.advertised_by_worker_manifest,
            "model_digest_function": "app.domain.studios.reality.reality_model_digest",
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(gate.model_dump(mode="json", by_alias=True), ensure_ascii=False, sort_keys=True))
    return 0 if gate.technical_decision == "passed" else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("benchmark-report.json"),
        help="Path for the report and gate bundle (outside the repository is recommended).",
    )
    return parser.parse_args()


def _load_cv2():
    try:
        import cv2
    except ImportError as exc:  # pragma: no cover - exercised by the worker preflight, not CI
        raise SystemExit("OpenCV is required in the isolated evaluation environment") from exc
    return cv2


def _assert_runtime_matches_lock(lock_path: Path, cv2) -> None:
    expected: dict[str, str] = {}
    for raw_line in lock_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "==" not in line:
            continue
        package, version = line.split("==", 1)
        expected[package.lower().replace("_", "-")] = version.split(" ", 1)[0]
    actual = {
        "numpy": str(np.__version__),
        "opencv-python-headless": _distribution_version(
            "opencv-python-headless", fallback=str(cv2.__version__)
        ),
    }
    mismatches = [
        f"{package}:expected={expected[package]} actual={actual[package]}"
        for package in actual
        if package not in expected or expected[package] != actual[package]
    ]
    if mismatches:
        raise SystemExit("evaluation runtime does not match provider lock: " + ",".join(mismatches))


def _distribution_version(package: str, *, fallback: str) -> str:
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return fallback


def _write_case_video(cv2, case: SyntheticRealityCaseV1, destination: Path) -> None:
    width, height = case.width, case.height
    writer = cv2.VideoWriter(
        str(destination),
        cv2.VideoWriter_fourcc(*"mp4v"),
        float(case.fps),
        (width, height),
    )
    if not writer.isOpened():
        raise RuntimeError("OpenCV evaluation runtime cannot encode mp4v")
    try:
        for frame_index in range(case.total_frames):
            writer.write(_frame_for_case(cv2, case, frame_index))
    finally:
        writer.release()


def _frame_for_case(cv2, case: SyntheticRealityCaseV1, frame_index: int) -> np.ndarray:
    parameters = case.generator_parameters
    seed = int(parameters.get("seed", 1))
    if case.generator == "low_texture":
        value = int(parameters.get("gray_level", 128))
        return np.full((case.height, case.width, 3), value, dtype=np.uint8)

    if case.generator == "two_shot_cut":
        half = case.total_frames // 2
        return _textured_frame(
            cv2,
            case.width,
            case.height,
            frame_index=0,
            horizon_y=float(parameters.get("horizon_y", 0.52)),
            seed=seed + (0 if frame_index < half else 101),
        )

    if case.generator == "foreground_motion":
        frame = _textured_frame(
            cv2,
            case.width,
            case.height,
            frame_index=0,
            horizon_y=float(parameters.get("horizon_y", 0.52)),
            seed=seed,
        )
        step = int(parameters.get("pixels_per_frame", 3))
        left = 30 + (frame_index * step) % max(1, case.width - 90)
        cv2.rectangle(frame, (left, 35), (min(case.width - 10, left + 58), 145), (35, 35, 35), -1)
        cv2.line(frame, (left + 8, 45), (min(case.width - 12, left + 50), 135), (230, 230, 230), 2)
        return frame

    has_horizon = case.generator not in {"pan_no_horizon"}
    horizon_y = float(parameters.get("horizon_y", 0.52))
    if case.generator == "horizon_distractors":
        frame = _textured_frame(
            cv2, case.width, case.height, frame_index=0, horizon_y=horizon_y, seed=seed
        )
        for y in (22, 48, 138, 162):
            cv2.line(frame, (0, y), (case.width - 1, y), (80, 80, 80), 2)
        return frame

    if case.generator in {"pan_textured", "pan_no_horizon", "blurred_pan"}:
        step = int(parameters.get("pixels_per_frame", 2))
        frame = _textured_frame(
            cv2,
            case.width,
            case.height,
            frame_index=frame_index * step,
            horizon_y=horizon_y,
            seed=seed,
            include_horizon=has_horizon,
            horizontal_world=True,
        )
        if case.generator == "blurred_pan":
            kernel = int(parameters.get("blur_kernel", 9))
            kernel = kernel if kernel % 2 else kernel + 1
            frame = cv2.GaussianBlur(frame, (kernel, kernel), 0)
        return frame

    if case.generator == "tilt_textured":
        step = int(parameters.get("pixels_per_frame", 1))
        return _textured_frame(
            cv2,
            case.width,
            case.height,
            frame_index=frame_index * step,
            horizon_y=horizon_y,
            seed=seed,
            vertical_world=True,
        )

    base = _textured_frame(
        cv2,
        case.width,
        case.height,
        frame_index=0,
        horizon_y=horizon_y,
        seed=seed,
        include_horizon=has_horizon,
    )
    if case.generator == "roll_textured":
        degrees = float(parameters.get("degrees_per_frame", 0.25)) * frame_index
        matrix = cv2.getRotationMatrix2D((case.width / 2, case.height / 2), degrees, 1.0)
        return cv2.warpAffine(base, matrix, (case.width, case.height), borderValue=(238, 238, 238))
    if case.generator == "zoom_textured":
        scale = 1.0 + float(parameters.get("scale_per_frame", 0.003)) * frame_index
        matrix = cv2.getRotationMatrix2D((case.width / 2, case.height / 2), 0, scale)
        return cv2.warpAffine(base, matrix, (case.width, case.height), borderValue=(238, 238, 238))
    return base


def _textured_frame(
    cv2,
    width: int,
    height: int,
    *,
    frame_index: int,
    horizon_y: float,
    seed: int,
    include_horizon: bool = True,
    horizontal_world: bool = False,
    vertical_world: bool = False,
) -> np.ndarray:
    world_width = width + (240 if horizontal_world else 0)
    world_height = height + (120 if vertical_world else 0)
    rng = np.random.default_rng(seed)
    canvas = np.full((world_height, world_width, 3), 238, dtype=np.uint8)
    noise = rng.integers(0, 12, size=(world_height, world_width, 1), dtype=np.uint8)
    canvas = np.clip(canvas.astype(np.int16) - noise, 0, 255).astype(np.uint8)
    horizon = round(horizon_y * height)
    if include_horizon:
        cv2.line(canvas, (0, horizon), (world_width - 1, horizon), (18, 18, 18), 3)
    for x in range(18, world_width - 12, 34):
        for y in (28, 58, 118, 150):
            cv2.circle(canvas, (x, y), 5, (25, 25, 25), -1)
    if include_horizon:
        cv2.rectangle(canvas, (110, 105), (min(world_width - 8, 190), 165), (40, 40, 40), 3)
    x_start = frame_index if horizontal_world else 0
    y_start = frame_index if vertical_world else 0
    return canvas[y_start : y_start + height, x_start : x_start + width].copy()


def _run_case(cv2, config: OpenCVRealityConfig, case: SyntheticRealityCaseV1, source: Path):
    checksum = _sha256(source.read_bytes())
    request = RealityAnalysisRequestV1(
        analysis_id=f"benchmark-{case.case_id}",
        workspace_id="workspace-pgv1-synthetic",
        source_asset=AssetReferenceV1(
            id=f"asset-{case.case_id}",
            version=1,
            media_type="video/mp4",
            checksum=checksum,
            origin="synthetic-benchmark",
            rights_status="verified",
            provenance={"synthetic": True, "corpus_case": case.case_id},
        ),
        source_time_map_id=f"time-map-{case.case_id}",
        source_time_map_digest_sha256=_sha256(f"time-map:{case.case_id}".encode()),
        frame_rate=FrameRateV1(numerator=case.fps, denominator=1),
        total_frames=case.total_frames,
        shots=[
            RealityShotV1(
                shot_id=shot.shot_id,
                frame_range=RealityFrameRangeV1(
                    start_frame=shot.frame_range.start_frame,
                    end_frame_exclusive=shot.frame_range.end_frame_exclusive,
                ),
                transition_in=shot.transition_in,
                transition_out=shot.transition_out,
            )
            for shot in case.shots
        ],
        analysis_policy_digest_sha256=_sha256(b"clicko.pgv1.synthetic-opencv-policy.v1"),
    )
    orchestrator = RealityAnalysisOrchestrator(
        geometry=OpenCVGeometryProvider(config, cv2_module=cv2),
        tracking=OpenCVPointTrackingProvider(config, cv2_module=cv2),
        scene=CanonicalContributionSceneProvider(),
    )
    model = orchestrator.analyze(source, request, lambda _progress: None, lambda: False)
    cameras = {item.shot_id: item for item in model.camera_observations}
    shot_ids = [shot.shot_id for shot in case.shots]
    track_counts = {shot_id: 0 for shot_id in shot_ids}
    for entity in model.entities:
        shot_id = entity.properties.get("shot_id")
        if isinstance(shot_id, str) and shot_id in track_counts:
            track_counts[shot_id] += 1
    return RealityPerceptionObservationV1(
        case_id=case.case_id,
        source_checksum_sha256=checksum,
        motion_by_shot={
            shot_id: cameras.get(shot_id).motion if shot_id in cameras else "unknown"
            for shot_id in shot_ids
        },
        horizon_present_by_shot={
            shot_id: bool(cameras.get(shot_id) and cameras[shot_id].horizon_y is not None)
            for shot_id in shot_ids
        },
        gravity_present_by_shot={
            shot_id: bool(cameras.get(shot_id) and cameras[shot_id].gravity_direction is not None)
            for shot_id in shot_ids
        },
        track_count_by_shot=track_counts,
        model_status=model.status,
        abstained_principles=model.abstained_principles,
        provider_versions={item.provider: item.provider_version for item in model.lineage},
        code_digests_sha256={item.provider: item.code_digest_sha256 for item in model.lineage},
        evidence_digest_sha256=_stable_model_digest(model),
    )


def _stable_model_digest(model: RealityModelV1) -> str:
    payload: Any = model.model_dump(mode="json", by_alias=True, exclude_none=True)

    def strip_timestamps(value: Any) -> Any:
        if isinstance(value, dict):
            return {
                key: strip_timestamps(item)
                for key, item in value.items()
                if key not in {"generatedAt", "generated_at"}
            }
        if isinstance(value, list):
            return [strip_timestamps(item) for item in value]
        return value

    canonical = json.dumps(strip_timestamps(payload), ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return _sha256(canonical.encode("utf-8"))


def _candidate_digest(candidate: ProviderCandidateManifestV1) -> str:
    from app.domain.studios.artifacts import provider_candidate_manifest_digest

    return provider_candidate_manifest_digest(candidate)


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
