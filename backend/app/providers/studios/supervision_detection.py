from __future__ import annotations

import hashlib
import importlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from types import ModuleType
from typing import Literal

import numpy as np
from PIL import Image

from ...domain.studios.providers import CancellationCheck, ProgressCallback
from ...domain.studios.reality import (
    NormalizedBoxV1,
    NormalizedPointV1,
    RealityAnalysisRequestV1,
    RealityContributionV1,
    RealityEntityTrackV1,
    RealityEntityV1,
    RealityEvidenceReferenceV1,
    RealityFrameRangeV1,
    RealityProviderLineageV1,
    RealityTrackSampleV1,
)

SUPPORTED_SUPERVISION_VERSION = "0.30.1"

EntityType = Literal[
    "person",
    "animal",
    "rigid_object",
    "deformable_object",
    "liquid",
    "gas",
    "surface",
    "environment",
    "light_shadow",
    "unknown",
]


class SupervisionRuntimeUnavailable(RuntimeError):
    """The optional, isolated Supervision runtime is absent or incompatible."""


@dataclass(frozen=True, slots=True)
class SupervisionClassSpec:
    display_name: str
    entity_type: EntityType = "unknown"

    def __post_init__(self) -> None:
        if not self.display_name.strip() or len(self.display_name) > 240:
            raise ValueError("supervision_adapter_invalid_class_name")


@dataclass(frozen=True, slots=True)
class SupervisionAdapterConfig:
    source_provider: str
    source_provider_version: str
    source_code_digest_sha256: str
    class_map: Mapping[int, SupervisionClassSpec]
    model_id: str | None = None
    model_revision: str | None = None
    model_digest_sha256: str | None = None
    render_overlays: bool = True
    overlay_thickness: int = 2

    def __post_init__(self) -> None:
        if not self.source_provider.strip() or not self.source_provider_version.strip():
            raise ValueError("supervision_adapter_source_provider_required")
        _require_sha256(self.source_code_digest_sha256, "source_code_digest")
        model_fields = (self.model_id, self.model_revision, self.model_digest_sha256)
        if any(model_fields) and not all(model_fields):
            raise ValueError("supervision_adapter_model_lineage_incomplete")
        if self.model_digest_sha256 is not None:
            _require_sha256(self.model_digest_sha256, "model_digest")
        if not 1 <= self.overlay_thickness <= 20:
            raise ValueError("supervision_adapter_invalid_overlay_thickness")
        if any(class_id < 0 for class_id in self.class_map):
            raise ValueError("supervision_adapter_negative_class_id")

    def digest(self, supervision_version: str) -> str:
        payload = {
            **asdict(self),
            "class_map": {
                str(class_id): asdict(spec)
                for class_id, spec in sorted(self.class_map.items())
            },
            "supervision_version": supervision_version,
        }
        return _canonical_digest(payload)


@dataclass(frozen=True, slots=True)
class SupervisionFrameInput:
    frame_index: int
    width: int
    height: int
    detections: object
    scene_bgr: np.ndarray | None = None

    def __post_init__(self) -> None:
        if self.frame_index < 0 or self.width < 1 or self.height < 1:
            raise ValueError("supervision_adapter_invalid_frame")


@dataclass(frozen=True, slots=True)
class SupervisionOverlayArtifact:
    frame_index: int
    evidence_ids: tuple[str, ...]
    media_type: Literal["image/png"]
    content: bytes
    checksum_sha256: str


@dataclass(frozen=True, slots=True)
class SupervisionProjectionResult:
    contribution: RealityContributionV1
    overlays: tuple[SupervisionOverlayArtifact, ...]


@dataclass(frozen=True, slots=True)
class _DetectionRecord:
    frame_index: int
    detection_index: int
    class_id: int | None
    confidence: float
    tracker_id: int | None
    box: NormalizedBoxV1
    has_mask: bool
    evidence_id: str
    entity_key: str


class SupervisionDetectionAdapter:
    """Projects ephemeral ``sv.Detections`` into canonical Clicko evidence.

    The adapter deliberately does not run or download a detector. A separately
    approved model must supply the detections and its complete lineage.
    """

    name = "toolkit.supervision-detection-projection"

    def __init__(
        self,
        config: SupervisionAdapterConfig,
        *,
        supervision_module: ModuleType | None = None,
    ) -> None:
        self.config = config
        self.supervision = supervision_module or _load_supervision()
        self.supervision_version = str(
            getattr(self.supervision, "__version__", "unknown")
        )
        if self.supervision_version != SUPPORTED_SUPERVISION_VERSION:
            raise SupervisionRuntimeUnavailable(
                "supervision_adapter_version_mismatch:"
                f"{self.supervision_version}!={SUPPORTED_SUPERVISION_VERSION}"
            )
        if not hasattr(self.supervision, "Detections"):
            raise SupervisionRuntimeUnavailable(
                "supervision_adapter_detections_type_missing"
            )
        self.version = f"1.0.0+supervision.{self.supervision_version}"

    def project(
        self,
        request: RealityAnalysisRequestV1,
        frames: Sequence[SupervisionFrameInput],
        progress: ProgressCallback,
        is_cancelled: CancellationCheck,
        *,
        generated_at: datetime | None = None,
    ) -> SupervisionProjectionResult:
        progress(0)
        if is_cancelled():
            raise InterruptedError("supervision_projection_cancelled")
        ordered_frames = self._validate_frames(request, frames)
        contribution_id = _opaque_id(
            "supervision-projection",
            f"{request.analysis_id}:{self.config.source_provider}",
        )
        records: list[_DetectionRecord] = []
        overlays: list[SupervisionOverlayArtifact] = []
        total = max(len(ordered_frames), 1)
        for offset, frame in enumerate(ordered_frames):
            if is_cancelled():
                raise InterruptedError("supervision_projection_cancelled")
            frame_records = self._frame_records(contribution_id, frame)
            records.extend(frame_records)
            if self.config.render_overlays and frame.scene_bgr is not None:
                overlays.append(self._render_overlay(frame, frame_records))
            progress(round((offset + 1) * 70 / total))

        contribution = self._contribution(
            request,
            contribution_id,
            records,
            generated_at=generated_at or datetime.now(UTC),
        )
        if is_cancelled():
            raise InterruptedError("supervision_projection_cancelled")
        progress(100)
        return SupervisionProjectionResult(
            contribution=contribution,
            overlays=tuple(overlays),
        )

    def _validate_frames(
        self,
        request: RealityAnalysisRequestV1,
        frames: Sequence[SupervisionFrameInput],
    ) -> list[SupervisionFrameInput]:
        ordered = sorted(frames, key=lambda item: item.frame_index)
        indices = [item.frame_index for item in ordered]
        if len(indices) != len(set(indices)):
            raise ValueError("supervision_adapter_duplicate_frame")
        if any(index >= request.total_frames for index in indices):
            raise ValueError("supervision_adapter_frame_out_of_request")
        detections_type = self.supervision.Detections
        for frame in ordered:
            if not isinstance(frame.detections, detections_type):
                raise TypeError("supervision_adapter_requires_detections")
            if frame.scene_bgr is not None:
                scene = np.asarray(frame.scene_bgr)
                if scene.dtype != np.uint8 or scene.shape != (
                    frame.height,
                    frame.width,
                    3,
                ):
                    raise ValueError("supervision_adapter_invalid_scene")
        return ordered

    def _frame_records(
        self,
        contribution_id: str,
        frame: SupervisionFrameInput,
    ) -> list[_DetectionRecord]:
        detections = frame.detections
        boxes = np.asarray(detections.xyxy, dtype=np.float64)
        if boxes.ndim != 2 or boxes.shape[1:] != (4,):
            raise ValueError("supervision_adapter_invalid_xyxy_shape")
        count = len(boxes)
        confidences = _optional_vector(detections.confidence, count, "confidence")
        class_ids = _optional_vector(detections.class_id, count, "class_id")
        tracker_ids = _optional_vector(detections.tracker_id, count, "tracker_id")
        masks = detections.mask
        if masks is not None:
            if not isinstance(masks, np.ndarray):
                raise ValueError("supervision_adapter_compact_mask_unsupported")
            if masks.dtype != np.bool_ or masks.shape != (
                count,
                frame.height,
                frame.width,
            ):
                raise ValueError("supervision_adapter_mask_shape_mismatch")

        records: list[_DetectionRecord] = []
        frame_tracker_ids: set[int] = set()
        for index, raw_box in enumerate(boxes):
            if not np.isfinite(raw_box).all():
                raise ValueError("supervision_adapter_non_finite_box")
            x_min, y_min, x_max, y_max = (float(value) for value in raw_box)
            if (
                x_min < 0
                or y_min < 0
                or x_max > frame.width
                or y_max > frame.height
                or x_max <= x_min
                or y_max <= y_min
            ):
                raise ValueError("supervision_adapter_box_out_of_bounds")
            confidence = (
                float(confidences[index]) if confidences is not None else 1.0
            )
            if not np.isfinite(confidence) or not 0 <= confidence <= 1:
                raise ValueError("supervision_adapter_invalid_confidence")
            class_id = _optional_integer(class_ids, index, "class_id")
            tracker_id = _optional_integer(tracker_ids, index, "tracker_id")
            if tracker_id is not None:
                if tracker_id in frame_tracker_ids:
                    raise ValueError("supervision_adapter_duplicate_tracker_in_frame")
                frame_tracker_ids.add(tracker_id)
            entity_seed = (
                f"tracker:{tracker_id}"
                if tracker_id is not None
                else f"frame:{frame.frame_index}:detection:{index}"
            )
            entity_key = _opaque_id("entity", entity_seed)
            evidence_id = _opaque_id(
                "evidence",
                f"{contribution_id}:{frame.frame_index}:{index}",
            )
            records.append(
                _DetectionRecord(
                    frame_index=frame.frame_index,
                    detection_index=index,
                    class_id=class_id,
                    confidence=confidence,
                    tracker_id=tracker_id,
                    box=NormalizedBoxV1(
                        x_min=x_min / frame.width,
                        y_min=y_min / frame.height,
                        x_max=x_max / frame.width,
                        y_max=y_max / frame.height,
                    ),
                    has_mask=masks is not None,
                    evidence_id=evidence_id,
                    entity_key=entity_key,
                )
            )
        return records

    def _render_overlay(
        self,
        frame: SupervisionFrameInput,
        records: Sequence[_DetectionRecord],
    ) -> SupervisionOverlayArtifact:
        scene = np.asarray(frame.scene_bgr).copy()
        detections = frame.detections
        labels = [
            f"{record.evidence_id} {self._class_spec(record.class_id).display_name} "
            f"{record.confidence:.3f}"
            for record in records
        ]
        box_annotator = self.supervision.BoxAnnotator(
            thickness=self.config.overlay_thickness
        )
        label_annotator = self.supervision.LabelAnnotator(
            text_scale=0.4,
            text_padding=4,
        )
        annotated = box_annotator.annotate(scene=scene, detections=detections)
        annotated = label_annotator.annotate(
            scene=annotated,
            detections=detections,
            labels=labels,
        )
        output = BytesIO()
        Image.fromarray(np.asarray(annotated)[:, :, ::-1], mode="RGB").save(
            output,
            format="PNG",
            optimize=False,
            compress_level=9,
        )
        content = output.getvalue()
        return SupervisionOverlayArtifact(
            frame_index=frame.frame_index,
            evidence_ids=tuple(record.evidence_id for record in records),
            media_type="image/png",
            content=content,
            checksum_sha256=hashlib.sha256(content).hexdigest(),
        )

    def _contribution(
        self,
        request: RealityAnalysisRequestV1,
        contribution_id: str,
        records: Sequence[_DetectionRecord],
        *,
        generated_at: datetime,
    ) -> RealityContributionV1:
        grouped: dict[str, list[_DetectionRecord]] = {}
        for record in records:
            grouped.setdefault(record.entity_key, []).append(record)

        entities: list[RealityEntityV1] = []
        tracks: list[RealityEntityTrackV1] = []
        for entity_key, entity_records in sorted(grouped.items()):
            ordered = sorted(entity_records, key=lambda item: item.frame_index)
            class_ids = {item.class_id for item in ordered}
            class_id = ordered[0].class_id if len(class_ids) == 1 else None
            spec = self._class_spec(class_id)
            confidence = round(
                sum(item.confidence for item in ordered) / len(ordered),
                6,
            )
            entities.append(
                RealityEntityV1(
                    entity_id=entity_key,
                    display_name=spec.display_name,
                    entity_type=spec.entity_type,
                    semantic_tags=[
                        "supervision-projection",
                        "external-tracker-id" if ordered[0].tracker_id is not None else "single-frame",
                    ],
                    properties={
                        "source_provider": self.config.source_provider,
                        "source_class_id": class_id if class_id is not None else -1,
                        "semantic_object": True,
                    },
                    confidence=confidence,
                )
            )
            tracks.append(
                RealityEntityTrackV1(
                    track_id=_opaque_id("track", entity_key),
                    entity_id=entity_key,
                    frame_range=RealityFrameRangeV1(
                        start_frame=ordered[0].frame_index,
                        end_frame_exclusive=ordered[-1].frame_index + 1,
                    ),
                    samples=[
                        RealityTrackSampleV1(
                            frame_index=item.frame_index,
                            centroid=NormalizedPointV1(
                                x=(item.box.x_min + item.box.x_max) / 2,
                                y=(item.box.y_min + item.box.y_max) / 2,
                            ),
                            bounding_box=item.box,
                            visibility="visible",
                            confidence=item.confidence,
                            evidence_ids=[item.evidence_id],
                        )
                        for item in ordered
                    ],
                    confidence=confidence,
                )
            )

        evidence = [
            RealityEvidenceReferenceV1(
                evidence_id=record.evidence_id,
                contribution_id=contribution_id,
                kind="mask" if record.has_mask else "frame_crop",
                frame_range=RealityFrameRangeV1(
                    start_frame=record.frame_index,
                    end_frame_exclusive=record.frame_index + 1,
                ),
                entity_ids=[record.entity_key],
                description=(
                    "Detector output normalized through Supervision Detections. "
                    "The toolkit does not establish identity, physics or causal relations."
                ),
                confidence=record.confidence,
            )
            for record in records
        ]
        model_fields = (
            {
                "model_id": self.config.model_id,
                "model_revision": self.config.model_revision,
                "model_digest_sha256": self.config.model_digest_sha256,
            }
            if self.config.model_id is not None
            else {}
        )
        limitations = [
            "Supervision is an ephemeral normalization toolkit, not a detector or world model.",
            "Tracking identifiers originate from a separately approved external tracker.",
            "No identity, depth, gravity, contact, causality or physical plausibility is inferred.",
        ]
        if not records:
            limitations.append("No detections were supplied for the selected frames.")
        return RealityContributionV1(
            analysis_id=request.analysis_id,
            source_asset_checksum_sha256=request.source_asset.checksum,
            lineage=RealityProviderLineageV1(
                contribution_id=contribution_id,
                contribution_kind="semantic",
                provider=self.config.source_provider,
                provider_version=(
                    f"{self.config.source_provider_version}"
                    f"+supervision.{self.supervision_version}"
                ),
                code_digest_sha256=_canonical_digest(
                    {
                        "adapter": adapter_code_digest(),
                        "source_provider_code": self.config.source_code_digest_sha256,
                    }
                ),
                input_digest_sha256=request.source_asset.checksum,
                parameters_digest_sha256=self.config.digest(
                    self.supervision_version
                ),
                generated_at=generated_at,
                **model_fields,
            ),
            evidence=evidence,
            entities=entities,
            tracks=tracks,
            limitations=limitations,
        )

    def _class_spec(self, class_id: int | None) -> SupervisionClassSpec:
        if class_id is None:
            return SupervisionClassSpec("Unknown detection")
        return self.config.class_map.get(
            class_id,
            SupervisionClassSpec(f"Class {class_id}"),
        )


def _load_supervision() -> ModuleType:
    try:
        return importlib.import_module("supervision")
    except (ImportError, OSError) as error:
        raise SupervisionRuntimeUnavailable(
            "supervision_adapter_runtime_unavailable"
        ) from error


def _optional_vector(
    value: object | None,
    expected_length: int,
    field: str,
) -> np.ndarray | None:
    if value is None:
        return None
    array = np.asarray(value)
    if array.ndim != 1 or len(array) != expected_length:
        raise ValueError(f"supervision_adapter_{field}_length_mismatch")
    return array


def _optional_integer(
    values: np.ndarray | None,
    index: int,
    field: str,
) -> int | None:
    if values is None:
        return None
    raw = values[index]
    value = float(raw)
    if not np.isfinite(value) or not value.is_integer() or value < 0:
        raise ValueError(f"supervision_adapter_invalid_{field}")
    return int(value)


def _require_sha256(value: str, field: str) -> None:
    if len(value) != 64 or any(character not in "0123456789abcdefABCDEF" for character in value):
        raise ValueError(f"supervision_adapter_invalid_{field}")


def _canonical_digest(value: object) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _opaque_id(prefix: str, value: str) -> str:
    return f"{prefix}-{hashlib.sha256(value.encode('utf-8')).hexdigest()[:20]}"


def adapter_code_digest() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
