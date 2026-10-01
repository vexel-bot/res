from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Literal

from pydantic import Field, model_validator

from .contracts import AssetReferenceV1, FrameRateV1, StudioContract

SHA256_PATTERN = r"^[0-9a-fA-F]{64}$"
OPAQUE_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,159}$"

RealityMode = Literal["realistic", "stylized_physical", "surreal"]
RealityPrinciple = Literal[
    "permanence",
    "immutability",
    "continuity",
    "solidity",
    "support_gravity",
    "contact_collision",
    "motion",
    "approximate_conservation",
    "material_behavior",
    "causality",
    "biomechanics",
    "camera_perspective",
    "light_shadow_reflection",
    "event_sound",
    "editorial_continuity",
]
RealityTechnique = Literal[
    "none",
    "cut",
    "jump_cut",
    "match_cut",
    "slow_motion",
    "speed_ramp",
    "reverse",
    "timelapse",
    "stop_motion",
    "freeze_frame",
    "vfx",
]


def _contract_digest(contract: StudioContract) -> str:
    canonical = json.dumps(
        contract.model_dump(mode="json", by_alias=True, exclude_none=True),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


class RealityFrameRangeV1(StudioContract):
    start_frame: int = Field(ge=0)
    end_frame_exclusive: int = Field(gt=0)

    @model_validator(mode="after")
    def end_follows_start(self) -> RealityFrameRangeV1:
        if self.end_frame_exclusive <= self.start_frame:
            raise ValueError("Reality frame range must be non-empty and half-open")
        return self


class NormalizedPointV1(StudioContract):
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)


class NormalizedVectorV1(StudioContract):
    x: float = Field(ge=-1, le=1)
    y: float = Field(ge=-1, le=1)

    @model_validator(mode="after")
    def reject_zero_vector(self) -> NormalizedVectorV1:
        if abs(self.x) + abs(self.y) < 1e-9:
            raise ValueError("Reality direction vectors cannot be zero")
        return self


class NormalizedBoxV1(StudioContract):
    x_min: float = Field(ge=0, le=1)
    y_min: float = Field(ge=0, le=1)
    x_max: float = Field(ge=0, le=1)
    y_max: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def validate_bounds(self) -> NormalizedBoxV1:
        if self.x_max <= self.x_min or self.y_max <= self.y_min:
            raise ValueError("Normalized boxes must have positive area")
        return self


class RealityShotV1(StudioContract):
    shot_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    frame_range: RealityFrameRangeV1
    transition_in: Literal["start", "cut", "dissolve", "wipe", "generated"] = "cut"
    transition_out: Literal["end", "cut", "dissolve", "wipe", "generated"] = "cut"


class RealityEvidenceReferenceV1(StudioContract):
    evidence_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    contribution_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    kind: Literal[
        "frame_crop",
        "mask",
        "point_track",
        "flow",
        "depth",
        "camera_geometry",
        "latent_prediction",
        "rule_trace",
        "human_annotation",
    ]
    frame_range: RealityFrameRangeV1
    entity_ids: list[str] = Field(default_factory=list, max_length=50)
    asset_id: str | None = Field(default=None, pattern=OPAQUE_ID_PATTERN)
    description: str = Field(min_length=1, max_length=1000)
    confidence: float = Field(ge=0, le=1)


class RealityProviderLineageV1(StudioContract):
    contribution_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    contribution_kind: Literal[
        "geometry", "tracking", "segmentation", "scene", "world_model", "rules", "semantic", "human"
    ]
    provider: str = Field(min_length=1, max_length=160)
    provider_version: str = Field(min_length=1, max_length=240)
    code_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    input_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    parameters_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    model_id: str | None = Field(default=None, max_length=240)
    model_revision: str | None = Field(default=None, max_length=240)
    model_digest_sha256: str | None = Field(default=None, pattern=SHA256_PATTERN)
    generated_at: datetime

    @model_validator(mode="after")
    def model_lineage_is_atomic(self) -> RealityProviderLineageV1:
        model_fields = (self.model_id, self.model_revision, self.model_digest_sha256)
        if any(model_fields) and not all(model_fields):
            raise ValueError("Reality model lineage requires id, revision and digest together")
        return self


class CameraObservationV1(StudioContract):
    observation_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    shot_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    frame_range: RealityFrameRangeV1
    motion: Literal[
        "static", "pan", "tilt", "roll", "dolly", "truck", "pedestal", "zoom", "handheld", "mixed", "unknown"
    ]
    up_vector: NormalizedVectorV1 | None = None
    gravity_direction: NormalizedVectorV1 | None = None
    horizon_y: float | None = Field(default=None, ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    evidence_ids: list[str] = Field(min_length=1, max_length=50)


class RealityEntityV1(StudioContract):
    entity_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    display_name: str = Field(min_length=1, max_length=240)
    entity_type: Literal[
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
    semantic_tags: list[str] = Field(default_factory=list, max_length=50)
    properties: dict[str, str | float | bool] = Field(default_factory=dict, max_length=50)
    confidence: float = Field(ge=0, le=1)


class RealityTrackSampleV1(StudioContract):
    frame_index: int = Field(ge=0)
    centroid: NormalizedPointV1
    bounding_box: NormalizedBoxV1 | None = None
    normalized_depth: float | None = Field(default=None, ge=0, le=1)
    visibility: Literal["visible", "partially_occluded", "fully_occluded", "out_of_frame", "unknown"]
    confidence: float = Field(ge=0, le=1)
    evidence_ids: list[str] = Field(default_factory=list, max_length=50)


class RealityEntityTrackV1(StudioContract):
    track_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    entity_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    frame_range: RealityFrameRangeV1
    samples: list[RealityTrackSampleV1] = Field(min_length=1, max_length=100000)
    confidence: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def samples_are_ordered_and_bound(self) -> RealityEntityTrackV1:
        frames = [sample.frame_index for sample in self.samples]
        if frames != sorted(frames) or len(frames) != len(set(frames)):
            raise ValueError("Reality track samples must be unique and ordered by frame")
        if any(
            frame < self.frame_range.start_frame or frame >= self.frame_range.end_frame_exclusive
            for frame in frames
        ):
            raise ValueError("Reality track samples must stay inside their track range")
        return self


class RealityRelationV1(StudioContract):
    relation_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    relation_type: Literal[
        "supports", "contacts", "contains", "attached_to", "occludes", "in_front_of", "behind", "inside", "near"
    ]
    source_entity_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    target_entity_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    frame_range: RealityFrameRangeV1
    state: Literal["present", "absent", "uncertain"]
    confidence: float = Field(ge=0, le=1)
    evidence_ids: list[str] = Field(min_length=1, max_length=50)

    @model_validator(mode="after")
    def reject_self_relation(self) -> RealityRelationV1:
        if self.source_entity_id == self.target_entity_id:
            raise ValueError("Reality relations require two distinct entities")
        return self


class RealityEventV1(StudioContract):
    event_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    event_type: Literal[
        "appears",
        "disappears",
        "starts_motion",
        "stops_motion",
        "contact",
        "separation",
        "collision",
        "support_change",
        "deformation",
        "state_change",
        "sound",
        "cut",
        "unknown",
    ]
    frame_range: RealityFrameRangeV1
    entity_ids: list[str] = Field(min_length=1, max_length=50)
    cause_event_ids: list[str] = Field(default_factory=list, max_length=50)
    description: str = Field(min_length=1, max_length=1000)
    confidence: float = Field(ge=0, le=1)
    evidence_ids: list[str] = Field(min_length=1, max_length=50)


class RealityHypothesisV1(StudioContract):
    hypothesis_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    principle: RealityPrinciple
    frame_range: RealityFrameRangeV1
    entity_ids: list[str] = Field(min_length=1, max_length=50)
    claim: str = Field(min_length=1, max_length=2000)
    expected_observation: str = Field(min_length=1, max_length=2000)
    observed_evidence: str = Field(min_length=1, max_length=2000)
    status: Literal["supported", "contradicted", "uncertain"]
    confidence: float = Field(ge=0, le=1)
    supporting_evidence_ids: list[str] = Field(default_factory=list, max_length=100)
    contradicting_evidence_ids: list[str] = Field(default_factory=list, max_length=100)


class RealityAnalysisRequestV1(StudioContract):
    schema_version: Literal["studio.reality-analysis-request.v1"] = "studio.reality-analysis-request.v1"
    analysis_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    workspace_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    source_asset: AssetReferenceV1
    source_time_map_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    source_time_map_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    frame_rate: FrameRateV1
    total_frames: int = Field(gt=0, le=100_000_000)
    shots: list[RealityShotV1] = Field(min_length=1, max_length=10000)
    analysis_policy_digest_sha256: str = Field(pattern=SHA256_PATTERN)

    @model_validator(mode="after")
    def validate_source_and_shots(self) -> RealityAnalysisRequestV1:
        if not self.source_asset.checksum or not _is_sha256(self.source_asset.checksum):
            raise ValueError("Reality analysis requires a source asset SHA-256")
        _validate_shots(self.shots, self.total_frames)
        return self


class RealityContributionV1(StudioContract):
    schema_version: Literal["studio.reality-contribution.v1"] = "studio.reality-contribution.v1"
    analysis_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    source_asset_checksum_sha256: str = Field(pattern=SHA256_PATTERN)
    lineage: RealityProviderLineageV1
    evidence: list[RealityEvidenceReferenceV1] = Field(default_factory=list, max_length=100000)
    camera_observations: list[CameraObservationV1] = Field(default_factory=list, max_length=10000)
    entities: list[RealityEntityV1] = Field(default_factory=list, max_length=10000)
    tracks: list[RealityEntityTrackV1] = Field(default_factory=list, max_length=10000)
    relations: list[RealityRelationV1] = Field(default_factory=list, max_length=100000)
    events: list[RealityEventV1] = Field(default_factory=list, max_length=100000)
    hypotheses: list[RealityHypothesisV1] = Field(default_factory=list, max_length=100000)
    limitations: list[str] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def validate_contribution_graph(self) -> RealityContributionV1:
        entity_ids = _unique_ids(
            "Reality contribution entity", [entity.entity_id for entity in self.entities]
        )
        evidence_ids = _unique_ids(
            "Reality contribution evidence", [item.evidence_id for item in self.evidence]
        )
        event_ids = _unique_ids(
            "Reality contribution event", [item.event_id for item in self.events]
        )
        _unique_ids("Reality contribution track", [item.track_id for item in self.tracks])
        _unique_ids("Reality contribution relation", [item.relation_id for item in self.relations])
        _unique_ids(
            "Reality contribution hypothesis", [item.hypothesis_id for item in self.hypotheses]
        )
        if any(item.contribution_id != self.lineage.contribution_id for item in self.evidence):
            raise ValueError("Reality contribution evidence must bind to its own lineage")
        for observation in self.camera_observations:
            _require_known("camera evidence", observation.evidence_ids, evidence_ids)
        for track in self.tracks:
            _require_known("track entity", [track.entity_id], entity_ids)
            for sample in track.samples:
                _require_known("track evidence", sample.evidence_ids, evidence_ids)
        for relation in self.relations:
            _require_known(
                "relation entity", [relation.source_entity_id, relation.target_entity_id], entity_ids
            )
            _require_known("relation evidence", relation.evidence_ids, evidence_ids)
        for event in self.events:
            _require_known("event entity", event.entity_ids, entity_ids)
            _require_known("event cause", event.cause_event_ids, event_ids)
            _require_known("event evidence", event.evidence_ids, evidence_ids)
        for hypothesis in self.hypotheses:
            _require_known("hypothesis entity", hypothesis.entity_ids, entity_ids)
            _require_known(
                "hypothesis evidence",
                hypothesis.supporting_evidence_ids + hypothesis.contradicting_evidence_ids,
                evidence_ids,
            )
        return self


class RealityModelV1(StudioContract):
    schema_version: Literal["studio.reality-model.v1"] = "studio.reality-model.v1"
    reality_model_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    analysis_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    workspace_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    source_asset: AssetReferenceV1
    source_time_map_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    source_time_map_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    analysis_policy_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    frame_rate: FrameRateV1
    total_frames: int = Field(gt=0, le=100_000_000)
    shots: list[RealityShotV1] = Field(min_length=1, max_length=10000)
    status: Literal["complete", "partial", "incomplete"]
    camera_observations: list[CameraObservationV1] = Field(default_factory=list, max_length=10000)
    entities: list[RealityEntityV1] = Field(default_factory=list, max_length=10000)
    tracks: list[RealityEntityTrackV1] = Field(default_factory=list, max_length=10000)
    relations: list[RealityRelationV1] = Field(default_factory=list, max_length=100000)
    events: list[RealityEventV1] = Field(default_factory=list, max_length=100000)
    hypotheses: list[RealityHypothesisV1] = Field(default_factory=list, max_length=100000)
    evidence: list[RealityEvidenceReferenceV1] = Field(default_factory=list, max_length=100000)
    lineage: list[RealityProviderLineageV1] = Field(min_length=1, max_length=100)
    abstained_principles: list[RealityPrinciple] = Field(default_factory=list, max_length=30)
    limitations: list[str] = Field(default_factory=list, max_length=100)
    generated_at: datetime

    @model_validator(mode="after")
    def validate_graph(self) -> RealityModelV1:
        if not self.source_asset.checksum or not _is_sha256(self.source_asset.checksum):
            raise ValueError("RealityModelV1 requires a source asset SHA-256")
        _validate_shots(self.shots, self.total_frames)
        shot_ids = {shot.shot_id for shot in self.shots}
        entity_ids = _unique_ids("Reality entity", [entity.entity_id for entity in self.entities])
        evidence_ids = _unique_ids("Reality evidence", [item.evidence_id for item in self.evidence])
        contribution_ids = _unique_ids(
            "Reality lineage contribution", [item.contribution_id for item in self.lineage]
        )
        _unique_ids("Reality track", [track.track_id for track in self.tracks])
        _unique_ids("Reality relation", [item.relation_id for item in self.relations])
        event_ids = _unique_ids("Reality event", [item.event_id for item in self.events])
        _unique_ids("Reality hypothesis", [item.hypothesis_id for item in self.hypotheses])
        if len(self.abstained_principles) != len(set(self.abstained_principles)):
            raise ValueError("Abstained reality principles must be unique")
        for evidence in self.evidence:
            if evidence.contribution_id not in contribution_ids:
                raise ValueError("Reality evidence references unknown lineage contribution")
            _validate_range(evidence.frame_range, self.total_frames, "evidence")
            _require_known("evidence entity", evidence.entity_ids, entity_ids)
        for observation in self.camera_observations:
            if observation.shot_id not in shot_ids:
                raise ValueError("Camera observation references unknown shot")
            _validate_range(observation.frame_range, self.total_frames, "camera observation")
            _require_known("camera evidence", observation.evidence_ids, evidence_ids)
        for track in self.tracks:
            if track.entity_id not in entity_ids:
                raise ValueError("Reality track references unknown entity")
            _validate_range(track.frame_range, self.total_frames, "track")
            for sample in track.samples:
                _require_known("track evidence", sample.evidence_ids, evidence_ids)
        for relation in self.relations:
            _require_known(
                "relation entity", [relation.source_entity_id, relation.target_entity_id], entity_ids
            )
            _require_known("relation evidence", relation.evidence_ids, evidence_ids)
            _validate_range(relation.frame_range, self.total_frames, "relation")
        for event in self.events:
            _require_known("event entity", event.entity_ids, entity_ids)
            _require_known("event cause", event.cause_event_ids, event_ids)
            _require_known("event evidence", event.evidence_ids, evidence_ids)
            if event.event_id in event.cause_event_ids:
                raise ValueError("Reality events cannot cause themselves")
            _validate_range(event.frame_range, self.total_frames, "event")
        for hypothesis in self.hypotheses:
            _require_known("hypothesis entity", hypothesis.entity_ids, entity_ids)
            _require_known(
                "hypothesis evidence",
                hypothesis.supporting_evidence_ids + hypothesis.contradicting_evidence_ids,
                evidence_ids,
            )
            _validate_range(hypothesis.frame_range, self.total_frames, "hypothesis")
        if self.status == "complete" and (not self.camera_observations or not self.evidence):
            raise ValueError("Complete reality models require camera observations and evidence")
        if self.status == "incomplete" and not self.limitations:
            raise ValueError("Incomplete reality models must explain their limitations")
        return self


class RealityLaneMarkerV1(StudioContract):
    """A review-only marker projected from evidence; never a physical fact."""

    marker_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    frame: int = Field(ge=0, le=2_073_600_000)
    label: str = Field(min_length=1, max_length=500)
    marker_type: Literal["camera_motion", "horizon", "gravity_cue", "track", "abstention"]
    shot_id: str | None = Field(default=None, pattern=OPAQUE_ID_PATTERN)
    confidence: float = Field(ge=0, le=1)
    provider: str = Field(min_length=1, max_length=160)
    evidence_ids: list[str] = Field(default_factory=list, max_length=50)
    correction_status: Literal["provider", "human_corrected"] = "provider"


class RealityLaneOverlayV1(StudioContract):
    """Editable overlay geometry for the Clicko timeline/Reality Lane projection."""

    overlay_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    kind: Literal["horizon", "gravity_direction", "track"]
    frame_range: RealityFrameRangeV1
    geometry: dict[str, Any] = Field(min_length=1, max_length=20)
    confidence: float = Field(ge=0, le=1)
    provider: str = Field(min_length=1, max_length=160)
    evidence_ids: list[str] = Field(default_factory=list, max_length=50)
    editable: Literal[True] = True


class RealityLaneProjectionV1(StudioContract):
    """Provider-neutral projection consumed by editor UX, not a second document store."""

    schema_version: Literal["studio.reality-lane-projection.v1"] = (
        "studio.reality-lane-projection.v1"
    )
    reality_model_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    reality_model_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    analysis_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    source_asset_id: str = Field(min_length=1, max_length=120)
    frame_rate: FrameRateV1
    total_frames: int = Field(gt=0, le=100_000_000)
    markers: list[RealityLaneMarkerV1] = Field(default_factory=list, max_length=100_000)
    overlays: list[RealityLaneOverlayV1] = Field(default_factory=list, max_length=100_000)
    abstained_principles: list[RealityPrinciple] = Field(default_factory=list, max_length=30)
    provider_neutral: Literal[True] = True
    human_correction_required: Literal[True] = True

    @model_validator(mode="after")
    def validate_projection(self) -> RealityLaneProjectionV1:
        marker_ids = [marker.marker_id for marker in self.markers]
        overlay_ids = [overlay.overlay_id for overlay in self.overlays]
        if len(marker_ids) != len(set(marker_ids)):
            raise ValueError("Reality Lane marker ids must be unique")
        if len(overlay_ids) != len(set(overlay_ids)):
            raise ValueError("Reality Lane overlay ids must be unique")
        for overlay in self.overlays:
            if overlay.frame_range.end_frame_exclusive > self.total_frames:
                raise ValueError("Reality Lane overlay exceeds source duration")
        return self


def project_reality_lane(model: RealityModelV1) -> RealityLaneProjectionV1:
    """Project immutable model evidence to editable markers/overlays for review UX."""

    evidence_by_id = {item.evidence_id: item for item in model.evidence}
    lineage_by_id = {item.contribution_id: item for item in model.lineage}
    markers: list[RealityLaneMarkerV1] = []
    overlays: list[RealityLaneOverlayV1] = []
    for camera in sorted(model.camera_observations, key=lambda item: (item.frame_range.start_frame, item.shot_id)):
        provider, _ = _lane_lineage(camera.evidence_ids, evidence_by_id, lineage_by_id)
        markers.append(
            RealityLaneMarkerV1(
                marker_id=f"lane-camera-{camera.observation_id}",
                frame=camera.frame_range.start_frame,
                label=f"Camera cue: {camera.motion} (image-plane evidence)",
                marker_type="camera_motion",
                shot_id=camera.shot_id,
                confidence=camera.confidence,
                provider=provider,
                evidence_ids=camera.evidence_ids,
            )
        )
        if camera.horizon_y is not None:
            markers.append(
                RealityLaneMarkerV1(
                    marker_id=f"lane-horizon-{camera.observation_id}",
                    frame=camera.frame_range.start_frame,
                    label="Horizon cue (editable)",
                    marker_type="horizon",
                    shot_id=camera.shot_id,
                    confidence=camera.confidence,
                    provider=provider,
                    evidence_ids=camera.evidence_ids,
                )
            )
            overlays.append(
                RealityLaneOverlayV1(
                    overlay_id=f"lane-overlay-horizon-{camera.observation_id}",
                    kind="horizon",
                    frame_range=camera.frame_range,
                    geometry={"start": {"x": 0.0, "y": camera.horizon_y}, "end": {"x": 1.0, "y": camera.horizon_y}},
                    confidence=camera.confidence,
                    provider=provider,
                    evidence_ids=camera.evidence_ids,
                )
            )
        if camera.gravity_direction is not None:
            markers.append(
                RealityLaneMarkerV1(
                    marker_id=f"lane-gravity-{camera.observation_id}",
                    frame=camera.frame_range.start_frame,
                    label="Up-direction cue (not proof of gravity/support)",
                    marker_type="gravity_cue",
                    shot_id=camera.shot_id,
                    confidence=camera.confidence,
                    provider=provider,
                    evidence_ids=camera.evidence_ids,
                )
            )
            overlays.append(
                RealityLaneOverlayV1(
                    overlay_id=f"lane-overlay-gravity-{camera.observation_id}",
                    kind="gravity_direction",
                    frame_range=camera.frame_range,
                    geometry={
                        "origin": {"x": 0.5, "y": 0.5},
                        "direction": {
                            "x": camera.gravity_direction.x,
                            "y": camera.gravity_direction.y,
                        },
                    },
                    confidence=camera.confidence,
                    provider=provider,
                    evidence_ids=camera.evidence_ids,
                )
            )
    for track in sorted(model.tracks, key=lambda item: (item.frame_range.start_frame, item.track_id)):
        evidence_ids = [evidence_id for sample in track.samples for evidence_id in sample.evidence_ids]
        provider, _ = _lane_lineage(evidence_ids, evidence_by_id, lineage_by_id)
        first, last = track.samples[0], track.samples[-1]
        markers.append(
            RealityLaneMarkerV1(
                marker_id=f"lane-track-{track.track_id}",
                frame=track.frame_range.start_frame,
                label="Sparse track evidence (not a semantic object)",
                marker_type="track",
                confidence=track.confidence,
                provider=provider,
                evidence_ids=sorted(set(evidence_ids)),
            )
        )
        overlays.append(
            RealityLaneOverlayV1(
                overlay_id=f"lane-overlay-track-{track.track_id}",
                kind="track",
                frame_range=track.frame_range,
                geometry={
                    "start": {"x": first.centroid.x, "y": first.centroid.y},
                    "end": {"x": last.centroid.x, "y": last.centroid.y},
                    "semantic": False,
                },
                confidence=track.confidence,
                provider=provider,
                evidence_ids=sorted(set(evidence_ids)),
            )
        )
    if model.abstained_principles:
        markers.append(
            RealityLaneMarkerV1(
                marker_id=f"lane-abstentions-{model.reality_model_id}",
                frame=0,
                label="Abstentions: " + ", ".join(model.abstained_principles),
                marker_type="abstention",
                confidence=1.0,
                provider="builtin.reality-abstention-policy",
            )
        )
    return RealityLaneProjectionV1(
        reality_model_id=model.reality_model_id,
        reality_model_digest_sha256=reality_model_digest(model),
        analysis_id=model.analysis_id,
        source_asset_id=model.source_asset.id,
        frame_rate=model.frame_rate,
        total_frames=model.total_frames,
        markers=markers,
        overlays=overlays,
        abstained_principles=model.abstained_principles,
    )


def _lane_lineage(
    evidence_ids: list[str],
    evidence_by_id: dict[str, RealityEvidenceReferenceV1],
    lineage_by_id: dict[str, RealityProviderLineageV1],
) -> tuple[str, str]:
    for evidence_id in evidence_ids:
        evidence = evidence_by_id.get(evidence_id)
        if evidence and evidence.contribution_id in lineage_by_id:
            lineage = lineage_by_id[evidence.contribution_id]
            return lineage.provider, lineage.contribution_id
    return "reality-model", "unknown"


class RealityContinuityConstraintV1(StudioContract):
    constraint_type: Literal[
        "entity_persistence", "screen_side", "eyeline", "prop_ownership", "handedness", "wardrobe", "scene_state"
    ]
    entity_ids: list[str] = Field(default_factory=list, max_length=50)
    expected_state: str = Field(min_length=1, max_length=1000)


class ShotRealityConstraintV1(StudioContract):
    schema_version: Literal["studio.shot-reality-constraint.v1"] = (
        "studio.shot-reality-constraint.v1"
    )
    constraint_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    document_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    document_revision: int = Field(ge=1)
    shot_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    frame_range: RealityFrameRangeV1
    reality_mode: RealityMode
    required_entity_ids: list[str] = Field(default_factory=list, max_length=100)
    preconditions: list[str] = Field(default_factory=list, max_length=100)
    intended_action: str = Field(min_length=1, max_length=2000)
    intended_outcome: str = Field(min_length=1, max_length=2000)
    continuity: list[RealityContinuityConstraintV1] = Field(default_factory=list, max_length=100)
    declared_techniques: list[RealityTechnique] = Field(min_length=1, max_length=20)
    enforced_principles: list[RealityPrinciple] = Field(default_factory=list, max_length=30)
    approval_status: Literal["draft", "approved", "retired"]
    authored_by: str = Field(pattern=OPAQUE_ID_PATTERN)
    authored_at: datetime

    @model_validator(mode="after")
    def validate_creative_intent(self) -> ShotRealityConstraintV1:
        for label, values in (
            ("required entities", self.required_entity_ids),
            ("declared techniques", self.declared_techniques),
            ("enforced principles", self.enforced_principles),
        ):
            if len(values) != len(set(values)):
                raise ValueError(f"Shot reality {label} must be unique")
        if "none" in self.declared_techniques and len(self.declared_techniques) != 1:
            raise ValueError("Reality technique 'none' cannot be combined with another technique")
        if self.reality_mode == "surreal" and self.approval_status == "approved" and not self.enforced_principles:
            raise ValueError("Approved surreal shots must declare which reality principles still apply")
        continuity_entities = [
            entity_id for constraint in self.continuity for entity_id in constraint.entity_ids
        ]
        _require_known("continuity entity", continuity_entities, set(self.required_entity_ids))
        return self


class ShotRealityConstraintSetV1(StudioContract):
    schema_version: Literal["studio.shot-reality-constraint-set.v1"] = (
        "studio.shot-reality-constraint-set.v1"
    )
    constraint_set_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    document_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    document_revision: int = Field(ge=1)
    constraints: list[ShotRealityConstraintV1] = Field(min_length=1, max_length=10000)
    created_at: datetime

    @model_validator(mode="after")
    def constraints_bind_to_snapshot(self) -> ShotRealityConstraintSetV1:
        _unique_ids("Shot reality constraint", [item.constraint_id for item in self.constraints])
        _unique_ids("Shot reality shot", [item.shot_id for item in self.constraints])
        if any(
            item.document_id != self.document_id or item.document_revision != self.document_revision
            for item in self.constraints
        ):
            raise ValueError("Every shot constraint must bind to the same document snapshot")
        return self


class PhysicalPlausibilityPolicyV1(StudioContract):
    schema_version: Literal["studio.physical-plausibility-policy.v1"] = (
        "studio.physical-plausibility-policy.v1"
    )
    policy_id: Literal["clicko.physical-qc.advisory.v1"] = "clicko.physical-qc.advisory.v1"
    policy_version: str = Field(min_length=1, max_length=80)
    status: Literal["draft", "frozen", "approved", "retired"]
    frozen_at: datetime
    frozen_by: str = Field(pattern=OPAQUE_ID_PATTERN)
    operating_mode: Literal["advisory"] = "advisory"
    evaluated_principles: list[RealityPrinciple] = Field(min_length=1, max_length=30)
    abstain_below_confidence: float = Field(ge=0, le=1)
    issue_min_confidence: float = Field(ge=0, le=1)
    critical_min_confidence: float = Field(ge=0, le=1)
    minimum_independent_signal_groups: int = Field(ge=1, le=10)
    benchmark_min_paired_accuracy: float = Field(ge=0, le=1)
    benchmark_min_critical_recall: float = Field(ge=0, le=1)
    benchmark_min_issue_precision: float = Field(ge=0, le=1)
    benchmark_min_temporal_iou: float = Field(ge=0, le=1)
    benchmark_max_expected_calibration_error: float = Field(ge=0, le=1)
    benchmark_max_real_ugc_false_block_rate: float = Field(ge=0, le=1)
    auto_correct: Literal[False] = False
    auto_publish: Literal[False] = False
    human_review_required: Literal[True] = True

    @model_validator(mode="after")
    def validate_policy(self) -> PhysicalPlausibilityPolicyV1:
        if len(self.evaluated_principles) != len(set(self.evaluated_principles)):
            raise ValueError("Physical QC principles must be unique")
        if not (
            self.abstain_below_confidence
            <= self.issue_min_confidence
            <= self.critical_min_confidence
        ):
            raise ValueError("Physical QC confidence thresholds must be monotonic")
        return self


class PhysicalPlausibilityCheckV1(StudioContract):
    check_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    principle: RealityPrinciple
    shot_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    frame_range: RealityFrameRangeV1
    entity_ids: list[str] = Field(default_factory=list, max_length=50)
    status: Literal["passed", "issue", "uncertain", "not_applicable"]
    severity: Literal["info", "warning", "critical"]
    confidence: float = Field(ge=0, le=1)
    expected_observation: str = Field(min_length=1, max_length=2000)
    observed_evidence: str = Field(min_length=1, max_length=2000)
    evidence_ids: list[str] = Field(default_factory=list, max_length=100)
    independent_signal_groups: list[
        Literal["geometry", "tracking", "segmentation", "world_model", "rules", "semantic", "human"]
    ] = Field(default_factory=list, max_length=10)
    uncertainty: str = Field(min_length=1, max_length=2000)
    suggestion: str | None = Field(default=None, max_length=2000)
    declared_technique: RealityTechnique | None = None
    human_decision: Literal[
        "not_required", "pending", "confirmed", "dismissed", "intentional", "needs_evidence"
    ]

    @model_validator(mode="after")
    def validate_check_semantics(self) -> PhysicalPlausibilityCheckV1:
        if len(self.entity_ids) != len(set(self.entity_ids)):
            raise ValueError("Physical QC entity ids must be unique")
        if len(self.evidence_ids) != len(set(self.evidence_ids)):
            raise ValueError("Physical QC evidence ids must be unique")
        if len(self.independent_signal_groups) != len(set(self.independent_signal_groups)):
            raise ValueError("Physical QC signal groups must be unique")
        if self.status in {"passed", "not_applicable"} and self.human_decision != "not_required":
            raise ValueError("Passed/not-applicable checks must mark human review as not required")
        if self.status in {"issue", "uncertain"} and self.human_decision == "not_required":
            raise ValueError("Issue/uncertain checks require a human decision state")
        if self.status == "issue" and not self.suggestion:
            raise ValueError("Physical QC issues require an editable suggestion")
        if self.status != "issue" and self.severity == "critical":
            raise ValueError("Only a physical QC issue can be critical")
        return self


class PhysicalPlausibilityRequestV1(StudioContract):
    schema_version: Literal["studio.physical-plausibility-request.v1"] = (
        "studio.physical-plausibility-request.v1"
    )
    evaluation_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    workspace_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    document_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    document_revision: int = Field(ge=1)
    document_snapshot_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    render_job_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    rendered_asset_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    rendered_asset_checksum_sha256: str = Field(pattern=SHA256_PATTERN)
    reality_model_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    reality_model_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    constraint_set_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    constraint_set_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    policy_digest_sha256: str = Field(pattern=SHA256_PATTERN)


class PhysicalPlausibilityEvaluationV1(StudioContract):
    schema_version: Literal["studio.physical-plausibility-evaluation.v1"] = (
        "studio.physical-plausibility-evaluation.v1"
    )
    evaluation_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    workspace_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    document_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    document_revision: int = Field(ge=1)
    document_snapshot_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    render_job_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    rendered_asset_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    rendered_asset_checksum_sha256: str = Field(pattern=SHA256_PATTERN)
    reality_model_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    reality_model_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    constraint_set_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    constraint_set_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    policy: PhysicalPlausibilityPolicyV1
    policy_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    evaluator_lineage: list[RealityProviderLineageV1] = Field(min_length=1, max_length=100)
    status: Literal["advisory_clear", "advisory_issues", "advisory_uncertain", "incomplete"]
    checks: list[PhysicalPlausibilityCheckV1] = Field(default_factory=list, max_length=100000)
    failure_code: str | None = Field(default=None, max_length=240)
    evaluated_at: datetime

    @model_validator(mode="after")
    def validate_evaluation(self) -> PhysicalPlausibilityEvaluationV1:
        if self.policy_digest_sha256.lower() != physical_plausibility_policy_digest(self.policy):
            raise ValueError("Physical QC policy digest does not match the embedded policy")
        if self.status != "incomplete" and self.policy.status not in {"frozen", "approved"}:
            raise ValueError("Completed Physical QC evaluations require a frozen or approved policy")
        _unique_ids("Physical QC check", [check.check_id for check in self.checks])
        _unique_ids(
            "Physical QC evaluator contribution",
            [item.contribution_id for item in self.evaluator_lineage],
        )
        if self.status == "incomplete":
            if not self.failure_code:
                raise ValueError("Incomplete Physical QC evaluations require a failure code")
            return self
        if self.failure_code:
            raise ValueError("Completed Physical QC evaluations cannot carry a failure code")
        if not self.checks:
            raise ValueError("Completed Physical QC evaluations require checks")
        if any(check.principle not in self.policy.evaluated_principles for check in self.checks):
            raise ValueError("Physical QC check uses a principle outside the policy")
        issue_checks = [check for check in self.checks if check.status == "issue"]
        uncertain_checks = [check for check in self.checks if check.status == "uncertain"]
        expected_status = (
            "advisory_issues"
            if issue_checks
            else "advisory_uncertain"
            if uncertain_checks
            else "advisory_clear"
        )
        if self.status != expected_status:
            raise ValueError("Physical QC evaluation status must match its checks")
        for check in issue_checks:
            if check.confidence < self.policy.issue_min_confidence:
                raise ValueError("Low-confidence physical observations must abstain, not become issues")
            if len(check.independent_signal_groups) < self.policy.minimum_independent_signal_groups:
                raise ValueError("Physical QC issues require independent signal groups")
            if check.severity == "critical" and check.confidence < self.policy.critical_min_confidence:
                raise ValueError("Critical physical issues require critical confidence")
        for check in uncertain_checks:
            if check.confidence >= self.policy.issue_min_confidence and len(
                check.independent_signal_groups
            ) >= self.policy.minimum_independent_signal_groups:
                raise ValueError("Well-supported physical observations cannot be hidden as uncertain")
        return self


def reality_model_digest(model: RealityModelV1) -> str:
    return _contract_digest(model)


def shot_reality_constraint_set_digest(constraints: ShotRealityConstraintSetV1) -> str:
    return _contract_digest(constraints)


def physical_plausibility_policy_digest(policy: PhysicalPlausibilityPolicyV1) -> str:
    return _contract_digest(policy)


def physical_plausibility_evaluation_digest(evaluation: PhysicalPlausibilityEvaluationV1) -> str:
    return _contract_digest(evaluation)


def validate_reality_model_bindings(
    model: RealityModelV1, request: RealityAnalysisRequestV1
) -> RealityModelV1:
    bindings = (
        (model.analysis_id, request.analysis_id, "analysis id"),
        (model.workspace_id, request.workspace_id, "workspace id"),
        (model.source_asset.id, request.source_asset.id, "source asset id"),
        (model.source_asset.checksum, request.source_asset.checksum, "source asset checksum"),
        (model.source_time_map_id, request.source_time_map_id, "source time-map id"),
        (
            model.source_time_map_digest_sha256.lower(),
            request.source_time_map_digest_sha256.lower(),
            "source time-map digest",
        ),
        (
            model.analysis_policy_digest_sha256.lower(),
            request.analysis_policy_digest_sha256.lower(),
            "analysis policy digest",
        ),
        (model.frame_rate, request.frame_rate, "frame rate"),
        (model.total_frames, request.total_frames, "total frames"),
        (model.shots, request.shots, "shot map"),
    )
    for actual, expected, label in bindings:
        if actual != expected:
            raise ValueError(f"Reality model {label} does not match the analysis request")
    return model


def validate_physical_evaluation_bindings(
    evaluation: PhysicalPlausibilityEvaluationV1,
    model: RealityModelV1,
    constraints: ShotRealityConstraintSetV1,
) -> PhysicalPlausibilityEvaluationV1:
    bindings = (
        (evaluation.workspace_id, model.workspace_id, "workspace"),
        (evaluation.reality_model_id, model.reality_model_id, "reality model id"),
        (evaluation.reality_model_digest_sha256.lower(), reality_model_digest(model), "reality model digest"),
        (evaluation.document_id, constraints.document_id, "document id"),
        (evaluation.document_revision, constraints.document_revision, "document revision"),
        (evaluation.constraint_set_id, constraints.constraint_set_id, "constraint set id"),
        (
            evaluation.constraint_set_digest_sha256.lower(),
            shot_reality_constraint_set_digest(constraints),
            "constraint set digest",
        ),
    )
    for actual, expected, label in bindings:
        if actual != expected:
            raise ValueError(f"Physical QC {label} binding mismatch")
    shot_constraints = {item.shot_id: item for item in constraints.constraints}
    model_shots = {item.shot_id: item for item in model.shots}
    entity_ids = {item.entity_id for item in model.entities}
    evidence_ids = {item.evidence_id for item in model.evidence}
    for constraint in constraints.constraints:
        model_shot = model_shots.get(constraint.shot_id)
        if not model_shot:
            raise ValueError("Physical QC constraint references an unknown Reality Model shot")
        _require_known("Physical QC constraint entity", constraint.required_entity_ids, entity_ids)
        if (
            constraint.frame_range.start_frame < model_shot.frame_range.start_frame
            or constraint.frame_range.end_frame_exclusive > model_shot.frame_range.end_frame_exclusive
        ):
            raise ValueError("Physical QC constraint extends beyond the Reality Model shot")
    for check in evaluation.checks:
        constraint = shot_constraints.get(check.shot_id)
        if not constraint:
            raise ValueError("Physical QC check references an unconstrained shot")
        _require_known("Physical QC check entity", check.entity_ids, entity_ids)
        _require_known("Physical QC check evidence", check.evidence_ids, evidence_ids)
        if (
            check.frame_range.start_frame < constraint.frame_range.start_frame
            or check.frame_range.end_frame_exclusive > constraint.frame_range.end_frame_exclusive
        ):
            raise ValueError("Physical QC check extends beyond its shot constraint")
    return evaluation


def validate_physical_request_bindings(
    request: PhysicalPlausibilityRequestV1,
    model: RealityModelV1,
    constraints: ShotRealityConstraintSetV1,
    policy: PhysicalPlausibilityPolicyV1,
) -> PhysicalPlausibilityRequestV1:
    bindings = (
        (request.workspace_id, model.workspace_id, "workspace"),
        (request.reality_model_id, model.reality_model_id, "reality model id"),
        (request.reality_model_digest_sha256.lower(), reality_model_digest(model), "reality model digest"),
        (request.document_id, constraints.document_id, "document id"),
        (request.document_revision, constraints.document_revision, "document revision"),
        (request.constraint_set_id, constraints.constraint_set_id, "constraint set id"),
        (
            request.constraint_set_digest_sha256.lower(),
            shot_reality_constraint_set_digest(constraints),
            "constraint set digest",
        ),
        (request.policy_digest_sha256.lower(), physical_plausibility_policy_digest(policy), "policy digest"),
    )
    for actual, expected, label in bindings:
        if actual != expected:
            raise ValueError(f"Physical QC request {label} binding mismatch")
    return request


def validate_physical_evaluation_request(
    evaluation: PhysicalPlausibilityEvaluationV1,
    request: PhysicalPlausibilityRequestV1,
) -> PhysicalPlausibilityEvaluationV1:
    fields = (
        "evaluation_id",
        "workspace_id",
        "document_id",
        "document_revision",
        "document_snapshot_digest_sha256",
        "render_job_id",
        "rendered_asset_id",
        "rendered_asset_checksum_sha256",
        "reality_model_id",
        "reality_model_digest_sha256",
        "constraint_set_id",
        "constraint_set_digest_sha256",
        "policy_digest_sha256",
    )
    for field in fields:
        actual = getattr(evaluation, field)
        expected = getattr(request, field)
        if isinstance(actual, str) and field.endswith("digest_sha256"):
            actual, expected = actual.lower(), expected.lower()
        if actual != expected:
            raise ValueError(f"Physical QC evaluation {field} does not match its request")
    return evaluation


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdefABCDEF" for character in value)


def _unique_ids(label: str, values: list[str]) -> set[str]:
    if len(values) != len(set(values)):
        raise ValueError(f"{label} ids must be unique")
    return set(values)


def _require_known(label: str, values: list[str], known: set[str]) -> None:
    unknown = sorted(set(values) - known)
    if unknown:
        raise ValueError(f"{label} references unknown ids: {unknown}")


def _validate_range(frame_range: RealityFrameRangeV1, total_frames: int, label: str) -> None:
    if frame_range.end_frame_exclusive > total_frames:
        raise ValueError(f"Reality {label} extends beyond the source")


def _validate_shots(shots: list[RealityShotV1], total_frames: int) -> None:
    _unique_ids("Reality shot", [shot.shot_id for shot in shots])
    ordered = sorted(shots, key=lambda shot: shot.frame_range.start_frame)
    for index, shot in enumerate(ordered):
        _validate_range(shot.frame_range, total_frames, "shot")
        if index and ordered[index - 1].frame_range.end_frame_exclusive > shot.frame_range.start_frame:
            raise ValueError("Reality shots cannot overlap")
