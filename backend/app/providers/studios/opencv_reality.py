from __future__ import annotations

import hashlib
import importlib
import json
import math
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType

import numpy as np

from ...domain.studios.providers import CancellationCheck, ProgressCallback
from ...domain.studios.reality import (
    CameraObservationV1,
    NormalizedPointV1,
    NormalizedVectorV1,
    RealityAnalysisRequestV1,
    RealityContributionV1,
    RealityEntityTrackV1,
    RealityEntityV1,
    RealityEvidenceReferenceV1,
    RealityFrameRangeV1,
    RealityProviderLineageV1,
    RealityTrackSampleV1,
)


class OpenCVRuntimeUnavailable(RuntimeError):
    """Raised when the isolated vision runtime does not contain OpenCV."""


@dataclass(frozen=True, slots=True)
class OpenCVRealityConfig:
    sample_stride_frames: int = 2
    max_samples_per_shot: int = 90
    max_features_per_shot: int = 48
    feature_quality_level: float = 0.01
    feature_min_distance_pixels: int = 10
    minimum_track_samples: int = 3
    horizon_max_tilt_degrees: float = 25.0
    horizon_min_length_ratio: float = 0.18
    static_translation_ratio: float = 0.0015
    roll_threshold_degrees: float = 0.6
    zoom_threshold_ratio: float = 0.012

    def __post_init__(self) -> None:
        if self.sample_stride_frames < 1 or self.max_samples_per_shot < 2:
            raise ValueError("opencv_reality_invalid_sampling")
        if not 1 <= self.max_features_per_shot <= 500:
            raise ValueError("opencv_reality_invalid_feature_limit")
        if not 0 < self.feature_quality_level <= 1:
            raise ValueError("opencv_reality_invalid_feature_quality")
        if self.feature_min_distance_pixels < 1 or self.minimum_track_samples < 2:
            raise ValueError("opencv_reality_invalid_tracking_threshold")
        if not 0 < self.horizon_max_tilt_degrees < 45:
            raise ValueError("opencv_reality_invalid_horizon_tilt")
        if not 0 < self.horizon_min_length_ratio <= 1:
            raise ValueError("opencv_reality_invalid_horizon_length")
        if min(
            self.static_translation_ratio,
            self.roll_threshold_degrees,
            self.zoom_threshold_ratio,
        ) <= 0:
            raise ValueError("opencv_reality_invalid_motion_threshold")

    def digest(self) -> str:
        return _canonical_digest(asdict(self))


@dataclass(frozen=True, slots=True)
class _FrameSample:
    frame_index: int
    gray: np.ndarray


@dataclass(frozen=True, slots=True)
class _MotionEstimate:
    translation_x_ratio: float
    translation_y_ratio: float
    rotation_degrees: float
    scale: float
    support: int


class _OpenCVProviderBase:
    version_prefix = "1.0.0"

    def __init__(
        self,
        config: OpenCVRealityConfig | None = None,
        *,
        cv2_module: ModuleType | None = None,
    ) -> None:
        self.config = config or OpenCVRealityConfig()
        self.cv2 = cv2_module or _load_cv2()
        raw_version = str(getattr(self.cv2, "__version__", "unknown"))
        safe_version = "".join(character for character in raw_version if character.isalnum() or character in ".-")
        self.version = f"{self.version_prefix}+opencv.{safe_version or 'unknown'}"

    def _capture(self, source: Path, request: RealityAnalysisRequestV1):
        capture = self.cv2.VideoCapture(str(source))
        if not capture.isOpened():
            raise ValueError("opencv_reality_video_unreadable")
        reported_frames = int(capture.get(self.cv2.CAP_PROP_FRAME_COUNT))
        if reported_frames > 0 and reported_frames < request.total_frames:
            capture.release()
            raise ValueError("opencv_reality_video_shorter_than_request")
        return capture

    def _read_gray(self, capture, frame_index: int) -> np.ndarray:
        capture.set(self.cv2.CAP_PROP_POS_FRAMES, frame_index)
        ok, frame = capture.read()
        if not ok or frame is None:
            raise ValueError(f"opencv_reality_frame_unreadable:{frame_index}")
        return self.cv2.cvtColor(frame, self.cv2.COLOR_BGR2GRAY)

    def _sample_frames(
        self,
        capture,
        frame_range: RealityFrameRangeV1,
        is_cancelled: CancellationCheck,
    ) -> list[_FrameSample]:
        available = range(
            frame_range.start_frame,
            frame_range.end_frame_exclusive,
            self.config.sample_stride_frames,
        )
        indices = list(available)
        if len(indices) > self.config.max_samples_per_shot:
            selected = np.linspace(
                0,
                len(indices) - 1,
                self.config.max_samples_per_shot,
                dtype=int,
            )
            indices = [indices[index] for index in np.unique(selected)]
        samples: list[_FrameSample] = []
        for frame_index in indices:
            if is_cancelled():
                raise InterruptedError("opencv_reality_cancelled")
            samples.append(_FrameSample(frame_index, self._read_gray(capture, frame_index)))
        return samples

    def _lineage(
        self,
        request: RealityAnalysisRequestV1,
        *,
        contribution_id: str,
        kind: str,
    ) -> RealityProviderLineageV1:
        return RealityProviderLineageV1(
            contribution_id=contribution_id,
            contribution_kind=kind,
            provider=self.name,
            provider_version=self.version,
            code_digest_sha256=_module_digest(),
            input_digest_sha256=request.source_asset.checksum,
            parameters_digest_sha256=self.config.digest(),
            generated_at=datetime.now(UTC),
        )


class OpenCVGeometryProvider(_OpenCVProviderBase):
    """Classical, weight-free camera/horizon evidence; never judges plausibility."""

    name = "opensource.opencv-geometry"

    def observe(
        self,
        source: Path,
        request: RealityAnalysisRequestV1,
        progress: ProgressCallback,
        is_cancelled: CancellationCheck,
    ) -> RealityContributionV1:
        progress(0)
        contribution_id = _opaque_id("opencv-geometry", request.analysis_id)
        evidence: list[RealityEvidenceReferenceV1] = []
        observations: list[CameraObservationV1] = []
        limitations = [
            "Horizon and camera motion are classical 2D estimates, not metric calibration.",
            "Gravity direction is inferred only when a supported horizon is detected.",
            "Cuts, large foreground motion and low texture can invalidate affine motion estimates.",
        ]
        capture = self._capture(source, request)
        try:
            for shot_index, shot in enumerate(request.shots):
                if is_cancelled():
                    raise InterruptedError("opencv_reality_cancelled")
                samples = self._sample_frames(capture, shot.frame_range, is_cancelled)
                result = self._analyze_shot(samples)
                evidence_id = f"{contribution_id}-e{shot_index}"
                evidence.append(
                    RealityEvidenceReferenceV1(
                        evidence_id=evidence_id,
                        contribution_id=contribution_id,
                        kind="camera_geometry",
                        frame_range=shot.frame_range,
                        description=result["description"],
                        confidence=result["confidence"],
                    )
                )
                observations.append(
                    CameraObservationV1(
                        observation_id=f"{contribution_id}-o{shot_index}",
                        shot_id=shot.shot_id,
                        frame_range=shot.frame_range,
                        motion=result["motion"],
                        up_vector=result["up_vector"],
                        gravity_direction=result["gravity_direction"],
                        horizon_y=result["horizon_y"],
                        confidence=result["confidence"],
                        evidence_ids=[evidence_id],
                    )
                )
                progress(round((shot_index + 1) * 100 / len(request.shots)))
        finally:
            capture.release()
        return RealityContributionV1(
            analysis_id=request.analysis_id,
            source_asset_checksum_sha256=request.source_asset.checksum,
            lineage=self._lineage(
                request,
                contribution_id=contribution_id,
                kind="geometry",
            ),
            evidence=evidence,
            camera_observations=observations,
            limitations=limitations,
        )

    def _analyze_shot(self, samples: list[_FrameSample]) -> dict[str, object]:
        horizons = [item for sample in samples if (item := self._horizon(sample.gray)) is not None]
        motions = [
            item
            for previous, current in zip(samples, samples[1:], strict=False)
            if (item := self._motion(previous.gray, current.gray)) is not None
        ]
        horizon_y: float | None = None
        up_vector: NormalizedVectorV1 | None = None
        gravity: NormalizedVectorV1 | None = None
        horizon_confidence = 0.0
        horizon_angle = 0.0
        if horizons:
            weights = np.array([item[2] for item in horizons], dtype=np.float64)
            horizon_y = float(np.average([item[0] for item in horizons], weights=weights))
            horizon_angle = float(np.average([item[1] for item in horizons], weights=weights))
            horizon_confidence = min(1.0, len(horizons) / max(3, len(samples) * 0.6))
            radians = math.radians(horizon_angle)
            gravity = NormalizedVectorV1(x=-math.sin(radians), y=math.cos(radians))
            up_vector = NormalizedVectorV1(x=math.sin(radians), y=-math.cos(radians))

        motion = self._classify_motion(motions)
        motion_confidence = min(1.0, len(motions) / max(2, len(samples) - 1))
        confidence = round(0.55 * horizon_confidence + 0.45 * motion_confidence, 6)
        if not horizons and not motions:
            motion = "unknown"
        description = (
            f"Classical OpenCV evidence over {len(samples)} sampled frames: "
            f"horizon support {len(horizons)}/{len(samples)}, "
            f"median horizon angle {horizon_angle:.3f} degrees; "
            f"valid affine motion pairs {len(motions)}/{max(0, len(samples) - 1)}; "
            f"camera label {motion}. These are image-plane cues, not metric physics."
        )
        return {
            "confidence": confidence,
            "description": description,
            "gravity_direction": gravity,
            "horizon_y": horizon_y,
            "motion": motion,
            "up_vector": up_vector,
        }

    def _horizon(self, gray: np.ndarray) -> tuple[float, float, float] | None:
        height, width = gray.shape[:2]
        edges = self.cv2.Canny(gray, 50, 150, apertureSize=3)
        lines = self.cv2.HoughLinesP(
            edges,
            1,
            np.pi / 180,
            threshold=max(20, width // 12),
            minLineLength=max(10, round(width * self.config.horizon_min_length_ratio)),
            maxLineGap=max(4, round(width * 0.04)),
        )
        if lines is None:
            return None
        candidates: list[tuple[float, float, float]] = []
        for raw in lines:
            x1, y1, x2, y2 = (float(value) for value in raw.reshape(4))
            dx, dy = x2 - x1, y2 - y1
            length = math.hypot(dx, dy)
            if length <= 0:
                continue
            angle = math.degrees(math.atan2(dy, dx))
            if angle > 90:
                angle -= 180
            elif angle < -90:
                angle += 180
            if abs(angle) <= self.config.horizon_max_tilt_degrees:
                candidates.append((((y1 + y2) / 2) / height, angle, length))
        if not candidates:
            return None
        cluster_height = max(4.0, height * 0.05)
        cluster_scores: dict[int, float] = {}
        for y_ratio, _angle, length in candidates:
            cluster = round((y_ratio * height) / cluster_height)
            cluster_scores[cluster] = cluster_scores.get(cluster, 0.0) + length
        dominant_cluster = max(cluster_scores, key=cluster_scores.get)
        dominant = [
            item
            for item in candidates
            if round((item[0] * height) / cluster_height) == dominant_cluster
        ]
        weights = np.array([item[2] for item in dominant], dtype=np.float64)
        return (
            float(np.average([item[0] for item in dominant], weights=weights)),
            float(np.average([item[1] for item in dominant], weights=weights)),
            float(min(1.0, weights.sum() / max(width * 3, 1))),
        )

    def _motion(self, previous: np.ndarray, current: np.ndarray) -> _MotionEstimate | None:
        points = self.cv2.goodFeaturesToTrack(
            previous,
            maxCorners=self.config.max_features_per_shot,
            qualityLevel=self.config.feature_quality_level,
            minDistance=self.config.feature_min_distance_pixels,
        )
        if points is None or len(points) < 4:
            return None
        moved, status, _errors = self.cv2.calcOpticalFlowPyrLK(previous, current, points, None)
        if moved is None or status is None:
            return None
        valid = status.reshape(-1).astype(bool)
        if int(valid.sum()) < 4:
            return None
        source_points = points.reshape(-1, 2)[valid]
        target_points = moved.reshape(-1, 2)[valid]
        matrix, inliers = self.cv2.estimateAffinePartial2D(
            source_points,
            target_points,
            method=self.cv2.RANSAC,
            ransacReprojThreshold=3.0,
        )
        if matrix is None:
            return None
        height, width = previous.shape[:2]
        a, b = float(matrix[0, 0]), float(matrix[0, 1])
        support = int(inliers.sum()) if inliers is not None else int(valid.sum())
        return _MotionEstimate(
            translation_x_ratio=float(matrix[0, 2]) / width,
            translation_y_ratio=float(matrix[1, 2]) / height,
            rotation_degrees=math.degrees(math.atan2(b, a)),
            scale=math.hypot(a, b),
            support=support,
        )

    def _classify_motion(self, estimates: list[_MotionEstimate]) -> str:
        if not estimates:
            return "unknown"
        weights = np.array([max(item.support, 1) for item in estimates], dtype=np.float64)
        tx = float(np.average([item.translation_x_ratio for item in estimates], weights=weights))
        ty = float(np.average([item.translation_y_ratio for item in estimates], weights=weights))
        rotation = float(np.average([item.rotation_degrees for item in estimates], weights=weights))
        scale = float(np.average([item.scale for item in estimates], weights=weights))
        translation = math.hypot(tx, ty)
        if (
            translation < self.config.static_translation_ratio
            and abs(rotation) < self.config.roll_threshold_degrees
            and abs(scale - 1) < self.config.zoom_threshold_ratio
        ):
            return "static"
        if abs(rotation) >= self.config.roll_threshold_degrees:
            return "roll"
        if abs(scale - 1) >= self.config.zoom_threshold_ratio:
            return "zoom"
        if abs(tx) > abs(ty) * 1.5:
            return "pan"
        if abs(ty) > abs(tx) * 1.5:
            return "tilt"
        return "mixed"


class OpenCVPointTrackingProvider(_OpenCVProviderBase):
    """Sparse Lucas-Kanade tracks used as motion evidence, never semantic objects."""

    name = "opensource.opencv-point-tracking"

    def observe(
        self,
        source: Path,
        request: RealityAnalysisRequestV1,
        progress: ProgressCallback,
        is_cancelled: CancellationCheck,
    ) -> RealityContributionV1:
        progress(0)
        contribution_id = _opaque_id("opencv-tracking", request.analysis_id)
        entities: list[RealityEntityV1] = []
        tracks: list[RealityEntityTrackV1] = []
        evidence: list[RealityEvidenceReferenceV1] = []
        empty_shots: list[str] = []
        capture = self._capture(source, request)
        try:
            for shot_index, shot in enumerate(request.shots):
                samples = self._sample_frames(capture, shot.frame_range, is_cancelled)
                shot_tracks = self._track_shot(samples, is_cancelled)
                if not shot_tracks:
                    empty_shots.append(shot.shot_id)
                for feature_index, feature_samples in enumerate(shot_tracks):
                    suffix = f"s{shot_index}-f{feature_index}"
                    entity_id = f"{contribution_id}-{suffix}"
                    evidence_id = f"{contribution_id}-e-{suffix}"
                    track_id = f"{contribution_id}-t-{suffix}"
                    confidence = round(
                        sum(item[3] for item in feature_samples) / len(feature_samples),
                        6,
                    )
                    frame_range = RealityFrameRangeV1(
                        start_frame=feature_samples[0][0],
                        end_frame_exclusive=feature_samples[-1][0] + 1,
                    )
                    entities.append(
                        RealityEntityV1(
                            entity_id=entity_id,
                            display_name=f"Tracked visual point {shot_index + 1}.{feature_index + 1}",
                            entity_type="unknown",
                            semantic_tags=["classical-feature", "non-semantic"],
                            properties={
                                "semantic_object": False,
                                "shot_id": shot.shot_id,
                            },
                            confidence=confidence,
                        )
                    )
                    evidence.append(
                        RealityEvidenceReferenceV1(
                            evidence_id=evidence_id,
                            contribution_id=contribution_id,
                            kind="point_track",
                            frame_range=frame_range,
                            entity_ids=[entity_id],
                            description=(
                                "Sparse Lucas-Kanade image feature trajectory. It is motion evidence "
                                "and must not be interpreted as a recognized physical object."
                            ),
                            confidence=confidence,
                        )
                    )
                    tracks.append(
                        RealityEntityTrackV1(
                            track_id=track_id,
                            entity_id=entity_id,
                            frame_range=frame_range,
                            samples=[
                                RealityTrackSampleV1(
                                    frame_index=frame_index,
                                    centroid=NormalizedPointV1(x=x, y=y),
                                    visibility="visible",
                                    confidence=sample_confidence,
                                    evidence_ids=[evidence_id],
                                )
                                for frame_index, x, y, sample_confidence in feature_samples
                            ],
                            confidence=confidence,
                        )
                    )
                progress(round((shot_index + 1) * 100 / len(request.shots)))
        finally:
            capture.release()
        limitations = [
            "Sparse feature tracks are not semantic objects and cannot establish identity.",
            "Occlusion, cuts, blur, low texture and deformation can terminate tracks.",
            "No metric depth, contact or support relation is inferred.",
        ]
        if empty_shots:
            limitations.append(f"No durable sparse tracks in shots: {','.join(empty_shots)}")
        return RealityContributionV1(
            analysis_id=request.analysis_id,
            source_asset_checksum_sha256=request.source_asset.checksum,
            lineage=self._lineage(
                request,
                contribution_id=contribution_id,
                kind="tracking",
            ),
            evidence=evidence,
            entities=entities,
            tracks=tracks,
            limitations=limitations,
        )

    def _track_shot(
        self,
        samples: list[_FrameSample],
        is_cancelled: CancellationCheck,
    ) -> list[list[tuple[int, float, float, float]]]:
        if len(samples) < self.config.minimum_track_samples:
            return []
        height, width = samples[0].gray.shape[:2]
        points = self.cv2.goodFeaturesToTrack(
            samples[0].gray,
            maxCorners=self.config.max_features_per_shot,
            qualityLevel=self.config.feature_quality_level,
            minDistance=self.config.feature_min_distance_pixels,
        )
        if points is None:
            return []
        active: dict[int, list[tuple[int, float, float, float]]] = {}
        positions: dict[int, np.ndarray] = {}
        for index, point in enumerate(points.reshape(-1, 2)):
            x, y = float(point[0]), float(point[1])
            active[index] = [(samples[0].frame_index, x / width, y / height, 1.0)]
            positions[index] = point
        previous = samples[0].gray
        for sample in samples[1:]:
            if is_cancelled():
                raise InterruptedError("opencv_reality_cancelled")
            if not positions:
                break
            identifiers = list(positions)
            previous_points = np.array([positions[index] for index in identifiers], dtype=np.float32).reshape(-1, 1, 2)
            moved, status, errors = self.cv2.calcOpticalFlowPyrLK(
                previous,
                sample.gray,
                previous_points,
                None,
            )
            if moved is None or status is None:
                break
            next_positions: dict[int, np.ndarray] = {}
            flat_moved = moved.reshape(-1, 2)
            flat_status = status.reshape(-1)
            flat_errors = errors.reshape(-1) if errors is not None else np.zeros(len(identifiers))
            for offset, identifier in enumerate(identifiers):
                if not flat_status[offset]:
                    continue
                x, y = (float(value) for value in flat_moved[offset])
                if not (0 <= x < width and 0 <= y < height):
                    continue
                confidence = max(0.05, 1.0 - min(float(flat_errors[offset]) / 30.0, 0.95))
                active[identifier].append(
                    (sample.frame_index, x / width, y / height, round(confidence, 6))
                )
                next_positions[identifier] = flat_moved[offset]
            positions = next_positions
            previous = sample.gray
        return [
            trajectory
            for trajectory in active.values()
            if len(trajectory) >= self.config.minimum_track_samples
        ]


def _load_cv2() -> ModuleType:
    try:
        return importlib.import_module("cv2")
    except ImportError as error:
        raise OpenCVRuntimeUnavailable("opencv_reality_runtime_unavailable") from error


def _canonical_digest(value: object) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _module_digest() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def _opaque_id(prefix: str, value: str) -> str:
    return f"{prefix}-{hashlib.sha256(value.encode('utf-8')).hexdigest()[:20]}"
