from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType

import numpy as np
import pytest

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
    SupervisionRuntimeUnavailable,
)

ROOT = Path(__file__).resolve().parents[2]
VISION_MANIFEST = ROOT / "workers/vision-gpu/worker.manifest.json"
ADAPTER_SOURCE = ROOT / "backend/app/providers/studios/supervision_detection.py"


class _FakeDetections:
    def __init__(
        self,
        *,
        xyxy: np.ndarray,
        confidence: np.ndarray | None = None,
        class_id: np.ndarray | None = None,
        tracker_id: np.ndarray | None = None,
        mask: np.ndarray | None = None,
    ) -> None:
        self.xyxy = xyxy
        self.confidence = confidence
        self.class_id = class_id
        self.tracker_id = tracker_id
        self.mask = mask


class _FakeBoxAnnotator:
    def __init__(self, *, thickness: int) -> None:
        self.thickness = thickness

    def annotate(self, *, scene: np.ndarray, detections: _FakeDetections) -> np.ndarray:
        for raw in detections.xyxy.astype(int):
            x1, y1, x2, y2 = raw
            scene[y1 : y1 + self.thickness, x1:x2] = (0, 255, 0)
            scene[y2 - self.thickness : y2, x1:x2] = (0, 255, 0)
            scene[y1:y2, x1 : x1 + self.thickness] = (0, 255, 0)
            scene[y1:y2, x2 - self.thickness : x2] = (0, 255, 0)
        return scene


class _FakeLabelAnnotator:
    def __init__(self, **_kwargs: object) -> None:
        pass

    def annotate(
        self,
        *,
        scene: np.ndarray,
        detections: _FakeDetections,
        labels: list[str],
    ) -> np.ndarray:
        assert len(labels) == len(detections.xyxy)
        if labels:
            scene[0, 0] = (len(labels), len(labels), len(labels))
        return scene


def _supervision(version: str = "0.30.1") -> ModuleType:
    module = ModuleType("supervision")
    module.__version__ = version
    module.Detections = _FakeDetections
    module.BoxAnnotator = _FakeBoxAnnotator
    module.LabelAnnotator = _FakeLabelAnnotator
    return module


def _config(*, render_overlays: bool = True) -> SupervisionAdapterConfig:
    return SupervisionAdapterConfig(
        source_provider="synthetic.detector",
        source_provider_version="1.2.3",
        source_code_digest_sha256="a" * 64,
        model_id="synthetic-detector",
        model_revision="fixture-v1",
        model_digest_sha256="b" * 64,
        class_map={
            0: SupervisionClassSpec("Person", "person"),
            1: SupervisionClassSpec("Product", "rigid_object"),
        },
        render_overlays=render_overlays,
    )


def _request() -> RealityAnalysisRequestV1:
    return RealityAnalysisRequestV1(
        analysis_id="supervision-spike-001",
        workspace_id="workspace-supervision-test",
        source_asset=AssetReferenceV1(
            id="asset-supervision-test",
            version=1,
            media_type="video/mp4",
            checksum="c" * 64,
            origin="synthetic-test",
            rights_status="verified",
            provenance={"synthetic": True},
        ),
        source_time_map_id="time-map-supervision-test",
        source_time_map_digest_sha256="d" * 64,
        frame_rate=FrameRateV1(numerator=30, denominator=1),
        total_frames=12,
        shots=[
            RealityShotV1(
                shot_id="shot-supervision-test",
                frame_range=RealityFrameRangeV1(
                    start_frame=0,
                    end_frame_exclusive=12,
                ),
                transition_in="start",
                transition_out="end",
            )
        ],
        analysis_policy_digest_sha256="e" * 64,
    )


def _frames() -> list[SupervisionFrameInput]:
    scene = np.zeros((100, 200, 3), dtype=np.uint8)
    return [
        SupervisionFrameInput(
            frame_index=2,
            width=200,
            height=100,
            scene_bgr=scene,
            detections=_FakeDetections(
                xyxy=np.array([[20, 10, 80, 70], [100, 20, 180, 90]], dtype=float),
                confidence=np.array([0.9, 0.8]),
                class_id=np.array([0, 1]),
                tracker_id=np.array([17, 24]),
            ),
        ),
        SupervisionFrameInput(
            frame_index=5,
            width=200,
            height=100,
            scene_bgr=scene,
            detections=_FakeDetections(
                xyxy=np.array([[30, 12, 90, 72]], dtype=float),
                confidence=np.array([0.85]),
                class_id=np.array([0]),
                tracker_id=np.array([17]),
            ),
        ),
    ]


def _canonical_projection(result) -> str:
    payload = result.contribution.model_dump(
        mode="json",
        by_alias=True,
        exclude_none=True,
    )
    return json.dumps(payload, separators=(",", ":"), sort_keys=True)


def test_adapter_projects_supervision_detections_into_clicko_contracts() -> None:
    progress: list[int] = []
    frozen_time = datetime(2026, 8, 27, 20, 0, tzinfo=UTC)
    adapter = SupervisionDetectionAdapter(
        _config(),
        supervision_module=_supervision(),
    )

    result = adapter.project(
        _request(),
        _frames(),
        progress.append,
        lambda: False,
        generated_at=frozen_time,
    )

    contribution = result.contribution
    assert contribution.schema_version == "studio.reality-contribution.v1"
    assert contribution.lineage.provider == "synthetic.detector"
    assert contribution.lineage.provider_version == "1.2.3+supervision.0.30.1"
    assert contribution.lineage.model_id == "synthetic-detector"
    assert contribution.lineage.code_digest_sha256 != "a" * 64
    assert len(contribution.entities) == 2
    assert len(contribution.tracks) == 2
    person_track = next(
        track
        for track in contribution.tracks
        if len(track.samples) == 2
    )
    assert [sample.frame_index for sample in person_track.samples] == [2, 5]
    assert person_track.samples[0].bounding_box is not None
    assert person_track.samples[0].bounding_box.x_min == pytest.approx(0.1)
    assert {item.kind for item in contribution.evidence} == {"frame_crop"}
    assert not contribution.relations
    assert not contribution.hypotheses
    assert any("No identity" in item for item in contribution.limitations)
    assert len(result.overlays) == 2
    assert all(item.content.startswith(b"\x89PNG") for item in result.overlays)
    assert all(
        item.checksum_sha256 == hashlib.sha256(item.content).hexdigest()
        for item in result.overlays
    )
    assert progress == [0, 35, 70, 100]


def test_projection_is_deterministic_with_frozen_time() -> None:
    adapter = SupervisionDetectionAdapter(
        _config(),
        supervision_module=_supervision(),
    )
    frozen_time = datetime(2026, 8, 27, 20, 0, tzinfo=UTC)

    first = adapter.project(
        _request(), _frames(), lambda _value: None, lambda: False, generated_at=frozen_time
    )
    second = adapter.project(
        _request(), _frames(), lambda _value: None, lambda: False, generated_at=frozen_time
    )

    assert _canonical_projection(first) == _canonical_projection(second)
    assert [item.checksum_sha256 for item in first.overlays] == [
        item.checksum_sha256 for item in second.overlays
    ]


@pytest.mark.parametrize(
    ("box", "error"),
    [
        ([-1, 10, 20, 30], "box_out_of_bounds"),
        ([10, 10, 201, 30], "box_out_of_bounds"),
        ([10, 10, 10, 30], "box_out_of_bounds"),
        ([float("nan"), 10, 20, 30], "non_finite_box"),
    ],
)
def test_invalid_boxes_fail_closed(box: list[float], error: str) -> None:
    adapter = SupervisionDetectionAdapter(
        _config(render_overlays=False),
        supervision_module=_supervision(),
    )
    frame = SupervisionFrameInput(
        frame_index=0,
        width=200,
        height=100,
        detections=_FakeDetections(xyxy=np.array([box], dtype=float)),
    )

    with pytest.raises(ValueError, match=error):
        adapter.project(_request(), [frame], lambda _value: None, lambda: False)


def test_version_mismatch_and_partial_model_lineage_fail_closed() -> None:
    with pytest.raises(SupervisionRuntimeUnavailable, match="version_mismatch"):
        SupervisionDetectionAdapter(
            _config(),
            supervision_module=_supervision("0.31.0"),
        )
    with pytest.raises(ValueError, match="model_lineage_incomplete"):
        SupervisionAdapterConfig(
            source_provider="synthetic.detector",
            source_provider_version="1",
            source_code_digest_sha256="a" * 64,
            class_map={},
            model_id="missing-fields",
        )


def test_cancellation_stops_before_projection() -> None:
    adapter = SupervisionDetectionAdapter(
        _config(),
        supervision_module=_supervision(),
    )
    with pytest.raises(InterruptedError, match="supervision_projection_cancelled"):
        adapter.project(_request(), _frames(), lambda _value: None, lambda: True)


def test_empty_detections_are_valid_and_remain_explicitly_incomplete() -> None:
    adapter = SupervisionDetectionAdapter(
        _config(render_overlays=False),
        supervision_module=_supervision(),
    )
    frame = SupervisionFrameInput(
        frame_index=0,
        width=200,
        height=100,
        detections=_FakeDetections(xyxy=np.empty((0, 4), dtype=float)),
    )

    result = adapter.project(
        _request(), [frame], lambda _value: None, lambda: False
    )

    assert not result.contribution.entities
    assert not result.contribution.evidence
    assert not result.contribution.tracks
    assert any("No detections" in item for item in result.contribution.limitations)


def test_masks_and_tracker_ids_are_strictly_validated() -> None:
    adapter = SupervisionDetectionAdapter(
        _config(render_overlays=False),
        supervision_module=_supervision(),
    )
    wrong_mask = SupervisionFrameInput(
        frame_index=0,
        width=200,
        height=100,
        detections=_FakeDetections(
            xyxy=np.array([[10, 10, 20, 20]], dtype=float),
            mask=np.zeros((1, 99, 200), dtype=bool),
        ),
    )
    duplicate_tracker = SupervisionFrameInput(
        frame_index=0,
        width=200,
        height=100,
        detections=_FakeDetections(
            xyxy=np.array([[10, 10, 20, 20], [30, 30, 40, 40]], dtype=float),
            tracker_id=np.array([7, 7]),
        ),
    )

    with pytest.raises(ValueError, match="mask_shape_mismatch"):
        adapter.project(
            _request(), [wrong_mask], lambda _value: None, lambda: False
        )
    with pytest.raises(ValueError, match="duplicate_tracker_in_frame"):
        adapter.project(
            _request(), [duplicate_tracker], lambda _value: None, lambda: False
        )


def test_adapter_cannot_activate_provider_or_leak_into_domain() -> None:
    manifest = json.loads(VISION_MANIFEST.read_text(encoding="utf-8"))
    domain_text = "\n".join(
        path.read_text(encoding="utf-8").lower()
        for path in (ROOT / "backend/app/domain/studios").glob("*.py")
    )
    source = ADAPTER_SOURCE.read_text(encoding="utf-8")

    assert manifest["providers"] == []
    assert "supervision" not in domain_text
    assert "ByteTrack" not in source
    assert "requests." not in source
    assert "urllib" not in source
    assert "http://" not in source and "https://" not in source
