from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field, model_validator

from .contracts import CreativeDocumentV1, FrameRateV1, StudioContract
from .intelligence import IntelligenceLineageV1
from .reality import RealityModelV1, reality_model_digest

SHA256_PATTERN = r"^[0-9a-fA-F]{64}$"
OPAQUE_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,159}$"

MotionProperty = Literal[
    "position_x",
    "position_y",
    "scale_x",
    "scale_y",
    "rotation_degrees",
    "opacity",
    "blur_px",
    "font_size_px",
    "letter_spacing_px",
    "line_height_ratio",
    "font_weight",
]
MotionUnit = Literal["pixels", "ratio", "degrees", "number"]

PROPERTY_UNITS: dict[MotionProperty, MotionUnit] = {
    "position_x": "pixels",
    "position_y": "pixels",
    "scale_x": "ratio",
    "scale_y": "ratio",
    "rotation_degrees": "degrees",
    "opacity": "ratio",
    "blur_px": "pixels",
    "font_size_px": "pixels",
    "letter_spacing_px": "pixels",
    "line_height_ratio": "ratio",
    "font_weight": "number",
}

PROJECTION_PROPERTY_PATHS: dict[str, dict[MotionProperty, str]] = {
    "hyperframes": {
        "position_x": "transform.translateX",
        "position_y": "transform.translateY",
        "scale_x": "transform.scaleX",
        "scale_y": "transform.scaleY",
        "rotation_degrees": "transform.rotateDegrees",
        "opacity": "style.opacity",
        "blur_px": "style.blurPx",
        "font_size_px": "typography.fontSizePx",
        "letter_spacing_px": "typography.letterSpacingPx",
        "line_height_ratio": "typography.lineHeightRatio",
        "font_weight": "typography.fontWeight",
    },
    "motion_canvas": {
        "position_x": "position.x",
        "position_y": "position.y",
        "scale_x": "scale.x",
        "scale_y": "scale.y",
        "rotation_degrees": "rotation.degrees",
        "opacity": "opacity",
        "blur_px": "filters.blurPx",
        "font_size_px": "fontSize.px",
        "letter_spacing_px": "letterSpacing.px",
        "line_height_ratio": "lineHeight.ratio",
        "font_weight": "fontWeight",
    },
}


PROJECTION_PROPERTY_PATHS["remotion"] = dict(PROJECTION_PROPERTY_PATHS["motion_canvas"])

def _contract_digest(contract: StudioContract) -> str:
    canonical = json.dumps(
        contract.model_dump(mode="json", by_alias=True, exclude_none=True),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


class MotionFrameRangeV1(StudioContract):
    start_frame: int = Field(ge=0, le=2_073_600_000)
    end_frame_exclusive: int = Field(gt=0, le=2_073_600_000)

    @model_validator(mode="after")
    def validate_range(self) -> MotionFrameRangeV1:
        if self.end_frame_exclusive <= self.start_frame:
            raise ValueError("Motion frame range must be non-empty and half-open")
        return self


class MotionKeyframeV1(StudioContract):
    frame: int = Field(ge=0, le=2_073_600_000)
    value: float
    easing: Literal[
        "hold",
        "linear",
        "ease_in",
        "ease_out",
        "ease_in_out",
        "cubic_bezier",
    ] = "linear"
    cubic_bezier: list[float] | None = Field(default=None, min_length=4, max_length=4)

    @model_validator(mode="after")
    def validate_easing(self) -> MotionKeyframeV1:
        if self.easing == "cubic_bezier":
            if self.cubic_bezier is None:
                raise ValueError("Cubic-bezier keyframes require four control values")
            x1, y1, x2, y2 = self.cubic_bezier
            if not 0 <= x1 <= 1 or not 0 <= x2 <= 1 or not -4 <= y1 <= 4 or not -4 <= y2 <= 4:
                raise ValueError("Cubic-bezier control values are out of deterministic bounds")
        elif self.cubic_bezier is not None:
            raise ValueError("Bezier controls are only valid for cubic-bezier easing")
        return self


class MotionTrackV1(StudioContract):
    track_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    target_layer_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    property: MotionProperty
    unit: MotionUnit
    keyframes: list[MotionKeyframeV1] = Field(min_length=1, max_length=100_000)

    @model_validator(mode="after")
    def validate_track(self) -> MotionTrackV1:
        if self.unit != PROPERTY_UNITS[self.property]:
            raise ValueError("Motion property and unit do not match")
        frames = [item.frame for item in self.keyframes]
        if frames != sorted(frames) or len(frames) != len(set(frames)):
            raise ValueError("Motion keyframes must be unique and ordered by frame")
        for keyframe in self.keyframes:
            value = keyframe.value
            if self.property == "opacity" and not 0 <= value <= 1:
                raise ValueError("Motion opacity must stay between zero and one")
            if self.property in {"scale_x", "scale_y"} and not 0.001 <= value <= 100:
                raise ValueError("Motion scale is out of bounds")
            if self.property in {"position_x", "position_y"} and not -32768 <= value <= 32768:
                raise ValueError("Motion position is out of bounds")
            if self.property == "rotation_degrees" and not -36000 <= value <= 36000:
                raise ValueError("Motion rotation is out of bounds")
            if self.property == "blur_px" and not 0 <= value <= 500:
                raise ValueError("Motion blur is out of bounds")
            if self.property == "font_size_px" and not 8 <= value <= 800:
                raise ValueError("Motion font size is out of bounds")
            if self.property == "letter_spacing_px" and not -100 <= value <= 500:
                raise ValueError("Motion letter spacing is out of bounds")
            if self.property == "line_height_ratio" and not 0.5 <= value <= 4:
                raise ValueError("Motion line height is out of bounds")
            if self.property == "font_weight" and not 100 <= value <= 900:
                raise ValueError("Motion font weight is out of bounds")
        return self


class MotionNodeV1(StudioContract):
    node_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    target_layer_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    parent_node_id: str | None = Field(default=None, pattern=OPAQUE_ID_PATTERN)
    transform_origin_x: float = Field(default=0.5, ge=0, le=1)
    transform_origin_y: float = Field(default=0.5, ge=0, le=1)


class MotionTransitionV1(StudioContract):
    transition_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    kind: Literal["hard_cut", "dissolve", "wipe", "match_transform", "semantic_morph"]
    reduced_motion_kind: Literal["hard_cut", "dissolve"]
    from_layer_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    to_layer_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    start_frame: int = Field(ge=0, le=2_073_600_000)
    end_frame_exclusive: int = Field(gt=0, le=2_073_600_000)
    motivation: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def validate_transition(self) -> MotionTransitionV1:
        if self.end_frame_exclusive <= self.start_frame:
            raise ValueError("Motion transition must be non-empty and half-open")
        if self.from_layer_id == self.to_layer_id:
            raise ValueError("Motion transition layers must be distinct")
        return self


class MotionAudioEventV1(StudioContract):
    event_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    frame: int = Field(ge=0, le=2_073_600_000)
    role: Literal["foley", "interface", "impact", "riser", "dialogue", "music", "silence"]
    event_binding: str = Field(min_length=1, max_length=1000)
    audio_clip_id: str | None = Field(default=None, pattern=OPAQUE_ID_PATTERN)
    asset_id: str | None = Field(default=None, pattern=OPAQUE_ID_PATTERN)
    rights_status: Literal["verified", "required_before_render", "not_applicable"]

    @model_validator(mode="after")
    def validate_audio_event(self) -> MotionAudioEventV1:
        if self.asset_id and self.rights_status != "verified":
            raise ValueError("Bound motion audio assets require verified rights")
        if self.role == "silence" and self.rights_status != "not_applicable":
            raise ValueError("Motion silence events have no rights requirement")
        return self


class MotionDesignConstraintV1(StudioContract):
    constraint_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    kind: Literal[
        "safe_area",
        "maximum_velocity",
        "maximum_acceleration",
        "no_overshoot",
        "readability",
    ]
    target_track_ids: list[str] = Field(min_length=1, max_length=100)
    frame_range: MotionFrameRangeV1
    threshold: float | None = None
    severity: Literal["advisory", "blocking"] = "blocking"

    @model_validator(mode="after")
    def validate_threshold(self) -> MotionDesignConstraintV1:
        threshold_required = {
            "safe_area",
            "maximum_velocity",
            "maximum_acceleration",
            "readability",
        }
        if self.kind in threshold_required and (self.threshold is None or self.threshold <= 0):
            raise ValueError(f"Motion {self.kind} constraint requires a positive threshold")
        if self.kind == "no_overshoot" and self.threshold is not None:
            raise ValueError("Motion no-overshoot constraint does not accept a threshold")
        return self


class MotionPhysicalConstraintV1(StudioContract):
    constraint_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    kind: Literal[
        "support_gravity",
        "contact_lock",
        "collision_avoidance",
        "perspective_consistency",
        "occlusion_order",
    ]
    target_track_ids: list[str] = Field(min_length=1, max_length=100)
    frame_range: MotionFrameRangeV1
    evidence_ids: list[str] = Field(min_length=1, max_length=100)
    severity: Literal["advisory", "blocking"] = "advisory"

    @model_validator(mode="after")
    def validate_evidence_ids(self) -> MotionPhysicalConstraintV1:
        if len(self.evidence_ids) != len(set(self.evidence_ids)):
            raise ValueError("Motion physical constraint evidence ids must be unique")
        return self


MotionConstraintV1 = Annotated[
    MotionDesignConstraintV1 | MotionPhysicalConstraintV1,
    Field(discriminator="kind"),
]


class MotionRealityBindingV1(StudioContract):
    reality_model_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    reality_model_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    evidence_ids: list[str] = Field(min_length=1, max_length=10_000)

    @model_validator(mode="after")
    def validate_evidence_ids(self) -> MotionRealityBindingV1:
        if len(self.evidence_ids) != len(set(self.evidence_ids)):
            raise ValueError("Motion reality binding evidence ids must be unique")
        return self


class MotionGraphV1(StudioContract):
    schema_version: Literal["studio.motion-graph.v1"] = "studio.motion-graph.v1"
    graph_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    workspace_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    document_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    document_revision: int = Field(ge=1)
    frame_rate: FrameRateV1
    duration_frames: int = Field(gt=0, le=2_073_600_000)
    canvas_width: int = Field(ge=320, le=8192)
    canvas_height: int = Field(ge=320, le=8192)
    reality_mode: Literal["graphic", "stylized_physical", "realistic_overlay"] = "graphic"
    completeness: Literal["partial", "complete"] = "complete"
    status: Literal["suggested", "reviewed"] = "suggested"
    nodes: list[MotionNodeV1] = Field(default_factory=list, max_length=10_000)
    tracks: list[MotionTrackV1] = Field(min_length=1, max_length=10_000)
    transitions: list[MotionTransitionV1] = Field(default_factory=list, max_length=10_000)
    audio_events: list[MotionAudioEventV1] = Field(default_factory=list, max_length=10_000)
    reduced_motion_supported: Literal[True] = True
    constraints: list[MotionConstraintV1] = Field(default_factory=list, max_length=10_000)
    source_evidence_ids: list[str] = Field(default_factory=list, max_length=10_000)
    reality_binding: MotionRealityBindingV1 | None = None
    abstentions: list[str] = Field(default_factory=list, max_length=1000)
    created_by: str = Field(pattern=OPAQUE_ID_PATTERN)
    lineage: IntelligenceLineageV1 | None = None
    human_review_required: Literal[True] = True
    created_at: datetime

    @model_validator(mode="after")
    def validate_graph(self) -> MotionGraphV1:
        track_ids = [item.track_id for item in self.tracks]
        node_ids = [item.node_id for item in self.nodes]
        node_layer_ids = [item.target_layer_id for item in self.nodes]
        transition_ids = [item.transition_id for item in self.transitions]
        audio_event_ids = [item.event_id for item in self.audio_events]
        constraint_ids = [item.constraint_id for item in self.constraints]
        if len(track_ids) != len(set(track_ids)):
            raise ValueError("Motion track ids must be unique")
        if len(node_ids) != len(set(node_ids)) or len(node_layer_ids) != len(set(node_layer_ids)):
            raise ValueError("Motion nodes and target layers must be unique")
        if len(transition_ids) != len(set(transition_ids)):
            raise ValueError("Motion transition ids must be unique")
        if len(audio_event_ids) != len(set(audio_event_ids)):
            raise ValueError("Motion audio event ids must be unique")
        if len(constraint_ids) != len(set(constraint_ids)):
            raise ValueError("Motion constraint ids must be unique")
        if len(self.source_evidence_ids) != len(set(self.source_evidence_ids)):
            raise ValueError("Motion source evidence ids must be unique")
        if self.completeness == "complete" and self.abstentions:
            raise ValueError("Complete motion graphs cannot contain abstentions")
        known_tracks = set(track_ids)
        known_nodes = set(node_ids)
        parents = {item.node_id: item.parent_node_id for item in self.nodes}
        for node in self.nodes:
            if node.parent_node_id and node.parent_node_id not in known_nodes:
                raise ValueError("Motion node references an unknown parent")
            cursor = node.node_id
            visited: set[str] = set()
            while cursor:
                if cursor in visited:
                    raise ValueError("Motion node hierarchy must be acyclic")
                visited.add(cursor)
                cursor = parents.get(cursor) or ""
        known_evidence = set(self.source_evidence_ids)
        physical_constraints = [
            item for item in self.constraints if isinstance(item, MotionPhysicalConstraintV1)
        ]
        for track in self.tracks:
            if track.keyframes[-1].frame >= self.duration_frames:
                raise ValueError("Motion keyframe exceeds graph duration")
        for transition in self.transitions:
            if transition.end_frame_exclusive > self.duration_frames:
                raise ValueError("Motion transition exceeds graph duration")
        for event in self.audio_events:
            if event.frame >= self.duration_frames:
                raise ValueError("Motion audio event exceeds graph duration")
        for constraint in self.constraints:
            if constraint.frame_range.end_frame_exclusive > self.duration_frames:
                raise ValueError("Motion constraint exceeds graph duration")
            unknown_tracks = sorted(set(constraint.target_track_ids) - known_tracks)
            if unknown_tracks:
                raise ValueError(f"Motion constraint references unknown tracks: {unknown_tracks}")
            if len(constraint.target_track_ids) != len(set(constraint.target_track_ids)):
                raise ValueError("Motion constraint target tracks must be unique")
        if physical_constraints:
            if self.reality_mode == "graphic":
                raise ValueError("Graphic motion cannot assert physical constraints")
            if self.reality_binding is None:
                raise ValueError("Physical motion constraints require a reality binding")
            bound_evidence = set(self.reality_binding.evidence_ids)
            for constraint in physical_constraints:
                if not set(constraint.evidence_ids) <= bound_evidence:
                    raise ValueError("Physical motion constraint uses unbound reality evidence")
                if not set(constraint.evidence_ids) <= known_evidence:
                    raise ValueError("Physical motion constraint uses unknown source evidence")
        if self.reality_mode == "realistic_overlay" and self.reality_binding is None:
            raise ValueError("Realistic overlay motion requires a reality binding")
        return self


class MotionProjectionKeyframeV1(StudioContract):
    frame: int = Field(ge=0, le=2_073_600_000)
    value: float
    easing: str = Field(min_length=1, max_length=80)
    cubic_bezier: list[float] | None = Field(default=None, min_length=4, max_length=4)


class MotionProjectionTrackV1(StudioContract):
    source_track_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    target_layer_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    property_path: str = Field(min_length=1, max_length=240)
    unit: MotionUnit
    keyframes: list[MotionProjectionKeyframeV1] = Field(min_length=1, max_length=100_000)


class MotionGraphProjectionV1(StudioContract):
    schema_version: Literal["studio.motion-graph-projection.v1"] = (
        "studio.motion-graph-projection.v1"
    )
    target: Literal["hyperframes", "motion_canvas", "remotion"]
    source_graph_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    source_graph_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    frame_rate: FrameRateV1
    duration_frames: int = Field(gt=0, le=2_073_600_000)
    nodes: list[MotionNodeV1] = Field(default_factory=list, max_length=10_000)
    tracks: list[MotionProjectionTrackV1] = Field(min_length=1, max_length=10_000)
    transitions: list[MotionTransitionV1] = Field(default_factory=list, max_length=10_000)
    audio_events: list[MotionAudioEventV1] = Field(default_factory=list, max_length=10_000)
    reduced_motion: bool = False
    preview_only: bool
    warnings: list[str] = Field(default_factory=list, max_length=1000)
    human_apply_required: Literal[True] = True


class MotionConstraintObservationV1(StudioContract):
    constraint_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    status: Literal["passed", "failed", "incomplete"]
    measured_value: float | None = None
    threshold: float | None = None
    reason: str = Field(min_length=1, max_length=1000)
    evidence_ids: list[str] = Field(default_factory=list, max_length=100)


class MotionGraphEvaluationV1(StudioContract):
    schema_version: Literal["studio.motion-graph-evaluation.v1"] = (
        "studio.motion-graph-evaluation.v1"
    )
    graph_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    graph_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    eligible_for_reviewed_projection: bool
    observations: list[MotionConstraintObservationV1] = Field(max_length=10_000)
    blocking_reasons: list[str] = Field(default_factory=list, max_length=10_000)
    warnings: list[str] = Field(default_factory=list, max_length=10_000)

    @model_validator(mode="after")
    def validate_decision(self) -> MotionGraphEvaluationV1:
        if self.eligible_for_reviewed_projection == bool(self.blocking_reasons):
            raise ValueError("Motion evaluation eligibility and blocking reasons disagree")
        return self


class CreateMotionGraphRequestV1(StudioContract):
    workspace_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    graph: MotionGraphV1
    reality_model: RealityModelV1 | None = None
    idempotency_key: str = Field(pattern=OPAQUE_ID_PATTERN)

    @model_validator(mode="after")
    def validate_scope(self) -> CreateMotionGraphRequestV1:
        if self.graph.workspace_id != self.workspace_id:
            raise ValueError("Motion graph request workspace does not match graph")
        if self.graph.status != "suggested":
            raise ValueError("Motion graphs must enter storage as suggestions")
        return self


class ReplaceMotionGraphRequestV1(StudioContract):
    workspace_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    expected_revision: int = Field(ge=1)
    graph: MotionGraphV1
    reality_model: RealityModelV1 | None = None

    @model_validator(mode="after")
    def validate_scope(self) -> ReplaceMotionGraphRequestV1:
        if self.graph.workspace_id != self.workspace_id:
            raise ValueError("Motion graph replacement workspace does not match graph")
        if self.graph.status != "suggested":
            raise ValueError("Motion graph replacements must return to suggested status")
        return self


class ReviewMotionGraphRequestV1(StudioContract):
    workspace_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    expected_revision: int = Field(ge=1)
    reality_model: RealityModelV1 | None = None


class MotionGraphRecordV1(StudioContract):
    schema_version: Literal["studio.motion-graph-record.v1"] = "studio.motion-graph-record.v1"
    graph: MotionGraphV1
    graph_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    storage_revision: int = Field(ge=1)
    evaluation: MotionGraphEvaluationV1 | None = None
    created_by: str = Field(pattern=OPAQUE_ID_PATTERN)
    updated_by: str = Field(pattern=OPAQUE_ID_PATTERN)
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def validate_record(self) -> MotionGraphRecordV1:
        if self.graph_digest_sha256 != motion_graph_digest(self.graph):
            raise ValueError("Motion graph record digest does not match graph")
        if self.evaluation is not None and (
            self.evaluation.graph_id != self.graph.graph_id
            or self.evaluation.graph_digest_sha256 != self.graph_digest_sha256
        ):
            raise ValueError("Motion graph record evaluation does not match graph")
        if self.graph.status == "reviewed" and self.evaluation is None:
            raise ValueError("Reviewed motion graph records require evaluation")
        return self


def motion_graph_digest(graph: MotionGraphV1) -> str:
    return _contract_digest(graph)


def motion_projection_digest(projection: MotionGraphProjectionV1) -> str:
    return _contract_digest(projection)


def validate_motion_graph_bindings(
    document: CreativeDocumentV1,
    graph: MotionGraphV1,
    reality_model: RealityModelV1 | None = None,
) -> None:
    if graph.workspace_id != document.workspace_id:
        raise ValueError("Motion graph workspace does not match document")
    if graph.document_id != document.document_id:
        raise ValueError("Motion graph document id does not match")
    if graph.document_revision != document.revision:
        raise ValueError("Motion graph document revision does not match")
    timeline = document.composition.media_timeline
    if timeline is None:
        raise ValueError("Motion graph requires a document media timeline")
    if graph.frame_rate != timeline.frame_rate:
        raise ValueError("Motion graph frame rate does not match document")
    if graph.duration_frames != timeline.duration_frames:
        raise ValueError("Motion graph duration does not match document")
    page = document.composition.pages[0]
    if graph.canvas_width != page.width or graph.canvas_height != page.height:
        raise ValueError("Motion graph canvas does not match document")
    layer_ids = [layer.id for page in document.composition.pages for layer in page.layers]
    if len(layer_ids) != len(set(layer_ids)):
        raise ValueError("Creative document layer ids must be globally unique for motion")
    referenced_layers = {
        *(track.target_layer_id for track in graph.tracks),
        *(node.target_layer_id for node in graph.nodes),
        *(transition.from_layer_id for transition in graph.transitions),
        *(transition.to_layer_id for transition in graph.transitions),
    }
    missing_layers = sorted(referenced_layers - set(layer_ids))
    if missing_layers:
        raise ValueError(f"Motion graph references unknown document layers: {missing_layers}")
    audio_clips = {
        clip.id: clip
        for track in timeline.tracks
        if track.kind == "audio"
        for clip in track.clips
    }
    missing_audio_clips = sorted(
        {
            event.audio_clip_id
            for event in graph.audio_events
            if event.audio_clip_id is not None
        }
        - set(audio_clips)
    )
    if missing_audio_clips:
        raise ValueError(f"Motion graph references unknown audio clips: {missing_audio_clips}")
    for event in graph.audio_events:
        if event.audio_clip_id is None:
            continue
        clip = audio_clips[event.audio_clip_id]
        if event.frame != clip.timeline.start_frame:
            raise ValueError(
                "Motion audio event frame must match its bound audio clip start frame"
            )
        if event.asset_id is not None and event.asset_id != clip.asset_id:
            raise ValueError(
                "Motion audio event asset id must match its bound audio clip asset id"
            )
    if graph.reality_binding is None:
        if reality_model is not None:
            raise ValueError("Unbound reality model cannot be supplied to motion validation")
        return
    if reality_model is None:
        raise ValueError("Motion graph reality binding requires the bound reality model")
    if graph.reality_binding.reality_model_id != reality_model.reality_model_id:
        raise ValueError("Motion graph reality model id does not match")
    if graph.reality_binding.reality_model_digest_sha256 != reality_model_digest(reality_model):
        raise ValueError("Motion graph reality model digest does not match")
    known_reality_evidence = {item.evidence_id for item in reality_model.evidence}
    if not set(graph.reality_binding.evidence_ids) <= known_reality_evidence:
        raise ValueError("Motion graph binds unknown reality evidence")


def _track_velocity(track: MotionTrackV1, frames_per_second: float) -> float | None:
    if len(track.keyframes) < 2:
        return None
    return max(
        abs(right.value - left.value) * frames_per_second / (right.frame - left.frame)
        for left, right in zip(track.keyframes, track.keyframes[1:], strict=False)
    )


def _track_acceleration(track: MotionTrackV1, frames_per_second: float) -> float | None:
    if len(track.keyframes) < 3:
        return None
    segments = []
    for left, right in zip(track.keyframes, track.keyframes[1:], strict=False):
        duration_seconds = (right.frame - left.frame) / frames_per_second
        velocity = (right.value - left.value) / duration_seconds
        midpoint_seconds = (left.frame + right.frame) / (2 * frames_per_second)
        segments.append((velocity, midpoint_seconds))
    return max(
        abs(right_velocity - left_velocity) / (right_time - left_time)
        for (left_velocity, left_time), (right_velocity, right_time) in zip(
            segments,
            segments[1:],
            strict=False,
        )
    )


def _potential_overshoot(track: MotionTrackV1) -> bool:
    return any(
        keyframe.easing == "cubic_bezier"
        and keyframe.cubic_bezier is not None
        and (keyframe.cubic_bezier[1] < 0 or keyframe.cubic_bezier[3] > 1)
        for keyframe in track.keyframes
    )


def _safe_area_violation(
    track: MotionTrackV1,
    document: CreativeDocumentV1,
    margin: float,
) -> float | None:
    if track.property not in {"position_x", "position_y"}:
        return None
    layers = {
        layer.id: (layer, page)
        for page in document.composition.pages
        for layer in page.layers
    }
    layer, page = layers[track.target_layer_id]
    violations: list[float] = []
    for keyframe in track.keyframes:
        if track.property == "position_x":
            start = layer.x + keyframe.value
            end = start + layer.width
            violations.append(max(0, margin - start, end - (page.width - margin)))
        else:
            start = layer.y + keyframe.value
            end = start + layer.height
            violations.append(max(0, margin - start, end - (page.height - margin)))
    return max(violations, default=0)


def _physical_principle(kind: str) -> str:
    return {
        "support_gravity": "support_gravity",
        "contact_lock": "contact_collision",
        "collision_avoidance": "contact_collision",
        "perspective_consistency": "camera_perspective",
        "occlusion_order": "solidity",
    }[kind]


def evaluate_motion_graph(
    document: CreativeDocumentV1,
    graph: MotionGraphV1,
    reality_model: RealityModelV1 | None = None,
) -> MotionGraphEvaluationV1:
    validate_motion_graph_bindings(document, graph, reality_model)
    tracks = {item.track_id: item for item in graph.tracks}
    frames_per_second = graph.frame_rate.numerator / graph.frame_rate.denominator
    observations: list[MotionConstraintObservationV1] = []
    blocking_reasons: list[str] = []
    warnings: list[str] = []

    for constraint in graph.constraints:
        status: Literal["passed", "failed", "incomplete"]
        measured: float | None = None
        evidence_ids: list[str] = []
        if isinstance(constraint, MotionDesignConstraintV1):
            selected = [tracks[track_id] for track_id in constraint.target_track_ids]
            if constraint.kind == "maximum_velocity":
                values = [_track_velocity(track, frames_per_second) for track in selected]
                measured = max((value for value in values if value is not None), default=None)
                status = "incomplete" if measured is None else (
                    "passed" if measured <= constraint.threshold else "failed"  # type: ignore[operator]
                )
                reason = "maximum-velocity-evaluated" if measured is not None else "velocity-needs-two-keyframes"
            elif constraint.kind == "maximum_acceleration":
                values = [_track_acceleration(track, frames_per_second) for track in selected]
                measured = max((value for value in values if value is not None), default=None)
                status = "incomplete" if measured is None else (
                    "passed" if measured <= constraint.threshold else "failed"  # type: ignore[operator]
                )
                reason = (
                    "maximum-acceleration-evaluated"
                    if measured is not None
                    else "acceleration-needs-three-keyframes"
                )
            elif constraint.kind == "no_overshoot":
                measured = float(any(_potential_overshoot(track) for track in selected))
                status = "passed" if measured == 0 else "failed"
                reason = "bezier-overshoot-static-check"
            elif constraint.kind == "safe_area":
                values = [
                    _safe_area_violation(track, document, constraint.threshold or 0)
                    for track in selected
                ]
                applicable = [value for value in values if value is not None]
                measured = max(applicable, default=None)
                status = "incomplete" if measured is None else ("passed" if measured == 0 else "failed")
                reason = "safe-area-keyframe-check" if measured is not None else "safe-area-needs-position-track"
            else:
                status = "incomplete"
                reason = "readability-needs-rendered-frame-evaluator"
        else:
            evidence_ids = list(constraint.evidence_ids)
            principle = _physical_principle(constraint.kind)
            supported = [] if reality_model is None else [
                hypothesis
                for hypothesis in reality_model.hypotheses
                if hypothesis.principle == principle
                and hypothesis.status == "supported"
                and set(hypothesis.supporting_evidence_ids) & set(constraint.evidence_ids)
            ]
            status = "passed" if supported else "incomplete"
            reason = (
                "physical-constraint-supported-by-reality-hypothesis"
                if supported
                else "physical-constraint-needs-supported-reality-hypothesis"
            )

        observation = MotionConstraintObservationV1(
            constraint_id=constraint.constraint_id,
            status=status,
            measured_value=measured,
            threshold=getattr(constraint, "threshold", None),
            reason=reason,
            evidence_ids=evidence_ids,
        )
        observations.append(observation)
        if status != "passed":
            message = f"{constraint.constraint_id}:{status}:{reason}"
            if constraint.severity == "blocking":
                blocking_reasons.append(message)
            else:
                warnings.append(message)

    return MotionGraphEvaluationV1(
        graph_id=graph.graph_id,
        graph_digest_sha256=motion_graph_digest(graph),
        eligible_for_reviewed_projection=not blocking_reasons,
        observations=observations,
        blocking_reasons=blocking_reasons,
        warnings=warnings,
    )


def project_motion_graph(
    graph: MotionGraphV1,
    target: Literal["hyperframes", "motion_canvas", "remotion"],
    evaluation: MotionGraphEvaluationV1 | None = None,
    *,
    reduced_motion: bool = False,
) -> MotionGraphProjectionV1:
    paths = PROJECTION_PROPERTY_PATHS[target]
    warnings = list(graph.abstentions)
    if evaluation is not None:
        if evaluation.graph_id != graph.graph_id or evaluation.graph_digest_sha256 != motion_graph_digest(graph):
            raise ValueError("Motion evaluation does not match graph")
        warnings.extend(evaluation.warnings)
    blocking_constraints = [item for item in graph.constraints if item.severity == "blocking"]
    if graph.status == "reviewed" and blocking_constraints:
        if evaluation is None:
            raise ValueError("Reviewed motion projection requires constraint evaluation")
        if not evaluation.eligible_for_reviewed_projection:
            raise ValueError("Reviewed motion projection is blocked by constraint evaluation")
    if graph.status != "reviewed":
        warnings.append("human-review-required-before-production-render")
    if reduced_motion:
        warnings.append("reduced-motion-projection")

    def projection_keyframes(track: MotionTrackV1) -> list[MotionProjectionKeyframeV1]:
        if reduced_motion and track.property in {
            "position_x",
            "position_y",
            "scale_x",
            "scale_y",
            "rotation_degrees",
            "blur_px",
        }:
            final = track.keyframes[-1]
            return [
                MotionProjectionKeyframeV1(
                    frame=0,
                    value=final.value,
                    easing="hold",
                )
            ]
        return [
            MotionProjectionKeyframeV1(
                frame=keyframe.frame,
                value=keyframe.value,
                easing=("linear" if reduced_motion else keyframe.easing),
                cubic_bezier=None if reduced_motion else keyframe.cubic_bezier,
            )
            for keyframe in track.keyframes
        ]

    return MotionGraphProjectionV1(
        target=target,
        source_graph_id=graph.graph_id,
        source_graph_digest_sha256=motion_graph_digest(graph),
        frame_rate=graph.frame_rate,
        duration_frames=graph.duration_frames,
        nodes=graph.nodes,
        tracks=[
            MotionProjectionTrackV1(
                source_track_id=track.track_id,
                target_layer_id=track.target_layer_id,
                property_path=paths[track.property],
                unit=track.unit,
                keyframes=projection_keyframes(track),
            )
            for track in graph.tracks
        ],
        transitions=[
            transition.model_copy(
                update={"kind": transition.reduced_motion_kind}
            )
            if reduced_motion
            else transition
            for transition in graph.transitions
        ],
        audio_events=graph.audio_events,
        reduced_motion=reduced_motion,
        preview_only=graph.status != "reviewed",
        warnings=warnings,
    )
