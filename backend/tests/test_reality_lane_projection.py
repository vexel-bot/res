from datetime import UTC, datetime

from app.domain.studios.contracts import AssetReferenceV1, FrameRateV1
from app.domain.studios.reality import (
    CameraObservationV1,
    NormalizedVectorV1,
    RealityEvidenceReferenceV1,
    RealityFrameRangeV1,
    RealityLaneProjectionV1,
    RealityModelV1,
    RealityProviderLineageV1,
    RealityShotV1,
    project_reality_lane,
    reality_model_digest,
)

NOW = datetime(2026, 8, 26, 0, 0, tzinfo=UTC)
SHA = "a" * 64


def model_with_camera() -> RealityModelV1:
    shot_range = RealityFrameRangeV1(start_frame=0, end_frame_exclusive=48)
    shot = RealityShotV1(
        shot_id="shot-1",
        frame_range=shot_range,
        transition_in="start",
        transition_out="end",
    )
    evidence = RealityEvidenceReferenceV1(
        evidence_id="evidence-camera",
        contribution_id="contribution-geometry",
        kind="camera_geometry",
        frame_range=shot_range,
        description="Synthetic camera evidence",
        confidence=0.9,
    )
    lineage = RealityProviderLineageV1(
        contribution_id="contribution-geometry",
        contribution_kind="geometry",
        provider="opensource.opencv-geometry",
        provider_version="1.0.0+opencv.4.13.0",
        code_digest_sha256=SHA,
        input_digest_sha256=SHA,
        parameters_digest_sha256=SHA,
        generated_at=NOW,
    )
    asset = AssetReferenceV1(
        id="asset-video-1",
        version=1,
        media_type="video/mp4",
        checksum=SHA,
        origin="synthetic-test",
        rights_status="verified",
    )
    return RealityModelV1(
        reality_model_id="reality-model-1",
        analysis_id="analysis-1",
        workspace_id="workspace-1",
        source_asset=asset,
        source_time_map_id="time-map-1",
        source_time_map_digest_sha256=SHA,
        analysis_policy_digest_sha256=SHA,
        frame_rate=FrameRateV1(numerator=30, denominator=1),
        total_frames=48,
        shots=[shot],
        status="partial",
        camera_observations=[
            CameraObservationV1(
                observation_id="camera-1",
                shot_id="shot-1",
                frame_range=shot_range,
                motion="pan",
                up_vector=NormalizedVectorV1(x=0, y=-1),
                gravity_direction=NormalizedVectorV1(x=0, y=1),
                horizon_y=0.5,
                confidence=0.9,
                evidence_ids=[evidence.evidence_id],
            )
        ],
        evidence=[evidence],
        lineage=[lineage],
        abstained_principles=["support_gravity", "contact_collision"],
        limitations=["Image-plane cues only"],
        generated_at=NOW,
    )


def test_reality_lane_projection_is_editable_and_binds_exact_model_digest():
    model = model_with_camera()
    projection = project_reality_lane(model)

    assert isinstance(projection, RealityLaneProjectionV1)
    assert projection.provider_neutral is True
    assert projection.human_correction_required is True
    assert projection.reality_model_digest_sha256 == reality_model_digest(model)
    assert {marker.marker_type for marker in projection.markers} >= {
        "camera_motion",
        "horizon",
        "gravity_cue",
        "abstention",
    }
    assert {overlay.kind for overlay in projection.overlays} == {"horizon", "gravity_direction"}
    assert all(overlay.editable for overlay in projection.overlays)
    assert any("not proof of gravity" in marker.label for marker in projection.markers)


def test_reality_lane_round_trips_without_provider_specific_document_format():
    projection = project_reality_lane(model_with_camera())
    round_trip = RealityLaneProjectionV1.model_validate_json(projection.model_dump_json(by_alias=True))

    assert round_trip == projection
    assert all("opencv" not in marker.label.lower() for marker in round_trip.markers)
