from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from app.domain.studios.contracts import AssetReferenceV1, FrameRateV1
from app.domain.studios.providers import PROVIDERS
from app.domain.studios.reality import (
    RealityAnalysisRequestV1,
    RealityFrameRangeV1,
    RealityShotV1,
)
from app.providers.studios.opencv_reality import (
    OpenCVGeometryProvider,
    OpenCVPointTrackingProvider,
    OpenCVRealityConfig,
)
from app.providers.studios.reality_scene import CanonicalContributionSceneProvider
from app.services.studios.reality_analysis import RealityAnalysisOrchestrator

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
VISION_MANIFEST = REPOSITORY_ROOT / "workers/vision-gpu/worker.manifest.json"


def _synthetic_pan_video(destination: Path, cv2) -> int:
    width, height, total_frames = 320, 180, 48
    canvas = np.full((height, width + total_frames + 10, 3), 238, dtype=np.uint8)
    cv2.line(canvas, (0, 90), (canvas.shape[1] - 1, 90), (10, 10, 10), 3)
    for x in range(20, canvas.shape[1] - 20, 35):
        for y in (35, 65, 120, 150):
            cv2.circle(canvas, (x, y), 5, (25, 25, 25), -1)
    cv2.rectangle(canvas, (110, 105), (190, 165), (40, 40, 40), 3)

    writer = cv2.VideoWriter(
        str(destination),
        cv2.VideoWriter_fourcc(*"mp4v"),
        30.0,
        (width, height),
    )
    if not writer.isOpened():
        pytest.skip("OpenCV test runtime cannot encode mp4v")
    for frame_index in range(total_frames):
        writer.write(canvas[:, frame_index : frame_index + width])
    writer.release()
    return total_frames


def _request(source: Path, total_frames: int) -> RealityAnalysisRequestV1:
    checksum = hashlib.sha256(source.read_bytes()).hexdigest()
    return RealityAnalysisRequestV1(
        analysis_id="opencv-synthetic-pan-001",
        workspace_id="workspace-opencv-test",
        source_asset=AssetReferenceV1(
            id="asset-opencv-test",
            version=1,
            media_type="video/mp4",
            checksum=checksum,
            origin="synthetic-test",
            rights_status="verified",
            provenance={"synthetic": True},
        ),
        source_time_map_id="time-map-opencv-test",
        source_time_map_digest_sha256="b" * 64,
        frame_rate=FrameRateV1(numerator=30, denominator=1),
        total_frames=total_frames,
        shots=[
            RealityShotV1(
                shot_id="shot-opencv-test",
                frame_range=RealityFrameRangeV1(
                    start_frame=0,
                    end_frame_exclusive=total_frames,
                ),
                transition_in="start",
                transition_out="end",
            )
        ],
        analysis_policy_digest_sha256="c" * 64,
    )


def test_opencv_baseline_is_not_registered_or_advertised() -> None:
    manifest = json.loads(VISION_MANIFEST.read_text(encoding="utf-8"))

    assert "opensource.opencv-geometry" not in PROVIDERS
    assert "opensource.opencv-point-tracking" not in PROVIDERS
    assert manifest["providers"] == []


def test_opencv_baseline_produces_bound_camera_and_motion_evidence(tmp_path: Path) -> None:
    cv2 = pytest.importorskip("cv2")
    source = tmp_path / "synthetic-pan.mp4"
    total_frames = _synthetic_pan_video(source, cv2)
    request = _request(source, total_frames)
    config = OpenCVRealityConfig(
        sample_stride_frames=2,
        max_samples_per_shot=30,
        max_features_per_shot=32,
        minimum_track_samples=4,
    )
    progress: list[int] = []
    orchestrator = RealityAnalysisOrchestrator(
        geometry=OpenCVGeometryProvider(config, cv2_module=cv2),
        tracking=OpenCVPointTrackingProvider(config, cv2_module=cv2),
        scene=CanonicalContributionSceneProvider(),
    )

    model = orchestrator.analyze(source, request, progress.append, lambda: False)

    assert model.status == "partial"
    assert model.source_asset.checksum == hashlib.sha256(source.read_bytes()).hexdigest()
    assert progress[0] == 0 and progress[-1] == 100
    assert progress == sorted(progress)
    assert len(model.camera_observations) == 1
    camera = model.camera_observations[0]
    assert camera.motion == "pan"
    assert camera.horizon_y == pytest.approx(0.5, abs=0.08)
    assert camera.gravity_direction is not None and camera.gravity_direction.y > 0.95
    assert camera.up_vector is not None and camera.up_vector.y < -0.95
    assert model.tracks
    assert any(
        abs(track.samples[-1].centroid.x - track.samples[0].centroid.x) > 0.03
        for track in model.tracks
    )
    assert {item.kind for item in model.evidence} >= {"camera_geometry", "point_track"}
    assert {item.provider for item in model.lineage} == {
        "opensource.opencv-geometry",
        "opensource.opencv-point-tracking",
        "builtin.canonical-reality-scene",
    }
    assert "camera_perspective" not in model.abstained_principles
    assert "motion" not in model.abstained_principles
    assert "support_gravity" in model.abstained_principles
    assert any("not semantic objects" in item for item in model.limitations)


def test_opencv_baseline_honors_cancellation_before_observation(tmp_path: Path) -> None:
    cv2 = pytest.importorskip("cv2")
    source = tmp_path / "synthetic-cancel.mp4"
    total_frames = _synthetic_pan_video(source, cv2)
    request = _request(source, total_frames)
    provider = OpenCVGeometryProvider(cv2_module=cv2)

    with pytest.raises(InterruptedError, match="opencv_reality_cancelled"):
        provider.observe(source, request, lambda _value: None, lambda: True)
