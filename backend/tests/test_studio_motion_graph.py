from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.domain.studios.contracts import CreativeDocumentV1
from app.domain.studios.motion import (
    MotionGraphV1,
    MotionTrackV1,
    evaluate_motion_graph,
    motion_graph_digest,
    project_motion_graph,
    validate_motion_graph_bindings,
)
from app.domain.studios.reality import RealityModelV1, reality_model_digest

NOW = datetime(2026, 8, 26, 18, 30, tzinfo=UTC)


def document() -> CreativeDocumentV1:
    return CreativeDocumentV1.model_validate(
        {
            "documentId": "document-motion-1",
            "workspaceId": "workspace-1",
            "title": "Motion UGC",
            "contentType": "video",
            "revision": 4,
            "version": 4,
            "correlationId": "correlation-motion-1",
            "brandMemoryRef": {"id": "brand-1", "revision": 2},
            "brief": {
                "objective": "Animar hook e CTA com movimento revisável",
                "audience": "Criadores de anúncios",
            },
            "composition": {
                "pages": [
                    {
                        "id": "scene-1",
                        "width": 1080,
                        "height": 1920,
                        "layers": [
                            {
                                "id": "hook-text",
                                "kind": "text",
                                "width": 900,
                                "height": 180,
                            },
                            {
                                "id": "cta-card",
                                "kind": "shape",
                                "width": 760,
                                "height": 220,
                            },
                        ],
                    }
                ],
                "mediaTimeline": {
                    "frameRate": {"numerator": 30, "denominator": 1},
                    "durationFrames": 60,
                    "tracks": [],
                },
            },
            "createdAt": NOW.isoformat(),
            "updatedAt": NOW.isoformat(),
        }
    )


def graph_payload() -> dict[str, object]:
    return {
        "graphId": "motion-graph-1",
        "workspaceId": "workspace-1",
        "documentId": "document-motion-1",
        "documentRevision": 4,
        "frameRate": {"numerator": 30, "denominator": 1},
        "durationFrames": 60,
        "canvasWidth": 1080,
        "canvasHeight": 1920,
        "realityMode": "graphic",
        "completeness": "complete",
        "status": "suggested",
        "tracks": [
            {
                "trackId": "track-hook-x",
                "targetLayerId": "hook-text",
                "property": "position_x",
                "unit": "pixels",
                "keyframes": [
                    {"frame": 0, "value": -120, "easing": "ease_out"},
                    {"frame": 12, "value": 0, "easing": "linear"},
                ],
            },
            {
                "trackId": "track-cta-opacity",
                "targetLayerId": "cta-card",
                "property": "opacity",
                "unit": "ratio",
                "keyframes": [
                    {"frame": 30, "value": 0, "easing": "ease_in_out"},
                    {"frame": 42, "value": 1, "easing": "hold"},
                ],
            },
        ],
        "constraints": [
            {
                "constraintId": "constraint-hook-speed",
                "kind": "maximum_velocity",
                "targetTrackIds": ["track-hook-x"],
                "frameRange": {"startFrame": 0, "endFrameExclusive": 13},
                "threshold": 400,
                "severity": "blocking",
            }
        ],
        "createdBy": "evaluation.qwen-motion",
        "createdAt": NOW.isoformat(),
    }


def graph() -> MotionGraphV1:
    return MotionGraphV1.model_validate(graph_payload())


def reality_model() -> RealityModelV1:
    return RealityModelV1.model_validate(
        {
            "realityModelId": "reality-1",
            "analysisId": "analysis-1",
            "workspaceId": "workspace-1",
            "sourceAsset": {
                "id": "source-video-1",
                "mediaType": "video/mp4",
                "checksum": "a" * 64,
                "rightsStatus": "verified",
            },
            "sourceTimeMapId": "time-map-1",
            "sourceTimeMapDigestSha256": "b" * 64,
            "analysisPolicyDigestSha256": "c" * 64,
            "frameRate": {"numerator": 30, "denominator": 1},
            "totalFrames": 60,
            "shots": [
                {
                    "shotId": "shot-1",
                    "frameRange": {"startFrame": 0, "endFrameExclusive": 60},
                    "transitionIn": "start",
                    "transitionOut": "end",
                }
            ],
            "status": "partial",
            "evidence": [
                {
                    "evidenceId": "reality-evidence-1",
                    "contributionId": "contribution-human-1",
                    "kind": "human_annotation",
                    "frameRange": {"startFrame": 0, "endFrameExclusive": 60},
                    "description": "Pessoa revisora confirmou o plano de apoio e a direção vertical.",
                    "confidence": 1,
                }
            ],
            "lineage": [
                {
                    "contributionId": "contribution-human-1",
                    "contributionKind": "human",
                    "provider": "clicko.human-review",
                    "providerVersion": "1.0.0",
                    "codeDigestSha256": "d" * 64,
                    "inputDigestSha256": "e" * 64,
                    "parametersDigestSha256": "f" * 64,
                    "generatedAt": NOW.isoformat(),
                }
            ],
            "limitations": ["Sem reconstrução métrica 3D."],
            "generatedAt": NOW.isoformat(),
        }
    )


def physical_graph(model: RealityModelV1) -> MotionGraphV1:
    payload = graph_payload()
    payload["realityMode"] = "realistic_overlay"
    payload["sourceEvidenceIds"] = ["reality-evidence-1"]
    payload["realityBinding"] = {
        "realityModelId": model.reality_model_id,
        "realityModelDigestSha256": reality_model_digest(model),
        "evidenceIds": ["reality-evidence-1"],
    }
    payload["constraints"] = [
        {
            "constraintId": "constraint-gravity-1",
            "kind": "support_gravity",
            "targetTrackIds": ["track-hook-x"],
            "frameRange": {"startFrame": 0, "endFrameExclusive": 13},
            "evidenceIds": ["reality-evidence-1"],
            "severity": "advisory",
        }
    ]
    return MotionGraphV1.model_validate(payload)


def test_motion_graph_binds_to_document_and_projects_deterministically() -> None:
    item = graph()
    validate_motion_graph_bindings(document(), item)

    hyperframes = project_motion_graph(item, "hyperframes")
    motion_canvas = project_motion_graph(item, "motion_canvas")
    repeated = project_motion_graph(item, "hyperframes")

    assert hyperframes == repeated
    assert hyperframes.source_graph_digest_sha256 == motion_graph_digest(item)
    assert hyperframes.preview_only is True
    assert hyperframes.warnings == ["human-review-required-before-production-render"]
    assert [track.property_path for track in hyperframes.tracks] == [
        "transform.translateX",
        "style.opacity",
    ]
    assert [track.property_path for track in motion_canvas.tracks] == [
        "position.x",
        "opacity",
    ]


def test_reviewed_motion_projection_is_not_preview_only() -> None:
    payload = graph_payload()
    payload["status"] = "reviewed"
    item = MotionGraphV1.model_validate(payload)
    evaluation = evaluate_motion_graph(document(), item)
    projection = project_motion_graph(item, "hyperframes", evaluation)

    assert evaluation.eligible_for_reviewed_projection is True
    assert evaluation.observations[0].measured_value == pytest.approx(300)
    assert projection.preview_only is False
    assert projection.warnings == []


def test_reviewed_projection_requires_a_matching_constraint_evaluation() -> None:
    payload = graph_payload()
    payload["status"] = "reviewed"
    item = MotionGraphV1.model_validate(payload)

    with pytest.raises(ValueError, match="requires constraint evaluation"):
        project_motion_graph(item, "hyperframes")

    evaluation = evaluate_motion_graph(document(), item)
    changed = item.model_copy(deep=True)
    changed.tracks[0].keyframes[1].value = 1
    with pytest.raises(ValueError, match="does not match graph"):
        project_motion_graph(changed, "hyperframes", evaluation)


def test_blocking_velocity_constraint_prevents_reviewed_projection() -> None:
    payload = graph_payload()
    payload["status"] = "reviewed"
    payload["constraints"][0]["threshold"] = 100  # type: ignore[index]
    item = MotionGraphV1.model_validate(payload)
    evaluation = evaluate_motion_graph(document(), item)

    assert evaluation.eligible_for_reviewed_projection is False
    assert evaluation.observations[0].status == "failed"
    assert evaluation.blocking_reasons
    with pytest.raises(ValueError, match="blocked by constraint evaluation"):
        project_motion_graph(item, "hyperframes", evaluation)


@pytest.mark.parametrize(
    ("property_name", "unit", "values", "message"),
    [
        ("opacity", "ratio", [0, 1.1], "opacity"),
        ("scale_x", "ratio", [1, 0], "scale"),
        ("position_x", "ratio", [0, 1], "property and unit"),
    ],
)
def test_motion_track_rejects_invalid_property_values(
    property_name: str,
    unit: str,
    values: list[float],
    message: str,
) -> None:
    with pytest.raises(ValidationError, match=message):
        MotionTrackV1.model_validate(
            {
                "trackId": "invalid-track",
                "targetLayerId": "hook-text",
                "property": property_name,
                "unit": unit,
                "keyframes": [
                    {"frame": index, "value": value} for index, value in enumerate(values)
                ],
            }
        )


def test_motion_graph_rejects_time_and_reference_drift() -> None:
    payload = graph_payload()
    payload["tracks"][0]["keyframes"][1]["frame"] = 60  # type: ignore[index]
    with pytest.raises(ValidationError, match="exceeds graph duration"):
        MotionGraphV1.model_validate(payload)

    item = graph()
    changed_document = document().model_dump(mode="json", by_alias=True)
    changed_document["revision"] = 5
    with pytest.raises(ValueError, match="revision does not match"):
        validate_motion_graph_bindings(CreativeDocumentV1.model_validate(changed_document), item)

    unknown_layer_payload = graph_payload()
    unknown_layer_payload["tracks"][0]["targetLayerId"] = "missing-layer"  # type: ignore[index]
    with pytest.raises(ValueError, match="unknown document layers"):
        validate_motion_graph_bindings(
            document(),
            MotionGraphV1.model_validate(unknown_layer_payload),
        )


def test_physical_motion_is_evidence_bound_to_the_reality_model() -> None:
    model = reality_model()
    item = physical_graph(model)
    validate_motion_graph_bindings(document(), item, model)
    evaluation = evaluate_motion_graph(document(), item, model)

    assert evaluation.eligible_for_reviewed_projection is True
    assert evaluation.observations[0].status == "incomplete"
    assert evaluation.warnings == [
        "constraint-gravity-1:incomplete:physical-constraint-needs-supported-reality-hypothesis"
    ]

    payload = item.model_dump(mode="json", by_alias=True)
    payload["realityBinding"]["realityModelDigestSha256"] = "0" * 64  # type: ignore[index]
    tampered = MotionGraphV1.model_validate(payload)
    with pytest.raises(ValueError, match="digest does not match"):
        validate_motion_graph_bindings(document(), tampered, model)


def test_physical_constraints_fail_closed_without_binding_or_evidence() -> None:
    model = reality_model()
    payload = physical_graph(model).model_dump(mode="json", by_alias=True)
    payload["realityBinding"] = None
    with pytest.raises(ValidationError, match="require a reality binding"):
        MotionGraphV1.model_validate(payload)

    unbound = physical_graph(model).model_dump(mode="json", by_alias=True)
    unbound["constraints"][0]["evidenceIds"] = ["unknown-evidence"]  # type: ignore[index]
    with pytest.raises(ValidationError, match="unbound reality evidence"):
        MotionGraphV1.model_validate(unbound)


def test_motion_digest_changes_when_keyframe_changes() -> None:
    original = graph()
    payload = deepcopy(graph_payload())
    payload["tracks"][0]["keyframes"][1]["value"] = 10  # type: ignore[index]
    changed = MotionGraphV1.model_validate(payload)

    assert motion_graph_digest(original) != motion_graph_digest(changed)


def test_acceleration_constraint_abstains_when_track_has_too_few_keyframes() -> None:
    payload = graph_payload()
    payload["constraints"] = [
        {
            "constraintId": "constraint-acceleration",
            "kind": "maximum_acceleration",
            "targetTrackIds": ["track-hook-x"],
            "frameRange": {"startFrame": 0, "endFrameExclusive": 13},
            "threshold": 1000,
            "severity": "blocking",
        }
    ]
    item = MotionGraphV1.model_validate(payload)
    evaluation = evaluate_motion_graph(document(), item)

    assert evaluation.eligible_for_reviewed_projection is False
    assert evaluation.observations[0].status == "incomplete"
    assert "acceleration-needs-three-keyframes" in evaluation.blocking_reasons[0]


def test_safe_area_constraint_evaluates_layer_geometry_at_keyframes() -> None:
    payload = graph_payload()
    payload["constraints"] = [
        {
            "constraintId": "constraint-safe-area",
            "kind": "safe_area",
            "targetTrackIds": ["track-hook-x"],
            "frameRange": {"startFrame": 0, "endFrameExclusive": 13},
            "threshold": 48,
            "severity": "blocking",
        }
    ]
    item = MotionGraphV1.model_validate(payload)
    evaluation = evaluate_motion_graph(document(), item)

    assert evaluation.observations[0].status == "failed"
    assert evaluation.observations[0].measured_value == pytest.approx(168)


def test_no_overshoot_constraint_detects_unbounded_bezier_controls() -> None:
    payload = graph_payload()
    payload["tracks"][0]["keyframes"][0] = {  # type: ignore[index]
        "frame": 0,
        "value": -120,
        "easing": "cubic_bezier",
        "cubicBezier": [0.2, -0.5, 0.8, 1.5],
    }
    payload["constraints"] = [
        {
            "constraintId": "constraint-overshoot",
            "kind": "no_overshoot",
            "targetTrackIds": ["track-hook-x"],
            "frameRange": {"startFrame": 0, "endFrameExclusive": 13},
            "severity": "blocking",
        }
    ]
    item = MotionGraphV1.model_validate(payload)
    evaluation = evaluate_motion_graph(document(), item)

    assert evaluation.observations[0].status == "failed"
    assert evaluation.observations[0].measured_value == 1
