import base64
import hashlib
from types import SimpleNamespace

import httpx
import pytest
from test_contextual_editing import ffmpeg
from test_scene_compiler_v2 import direction

from app.domain.studios.contextual_editing_v2 import EditorialElementV2
from app.domain.studios.visual_audit import VisualHumanReviewV1, checkpoint_frames, contrast_ratio, preflight_visual
from app.providers.studios.pexels_resources import discover
from app.providers.studios.visual_state_observation import observe_visual_states
from app.services.studios.visual_review import record_visual_review


def test_contrast_is_a_preflight_finding_not_a_render_or_human_approval():
    request = direction(color="#10181c")
    audit = preflight_visual(request)
    assert contrast_ratio("#ffffff", "#000000") == pytest.approx(21)
    assert any(finding["elementId"] == "title" for finding in audit["findings"])
    assert audit["visualEditorial"] == "requires_correction"
    assert audit["human"] == "pending"
    assert audit["renderedEvidence"] == []


def test_visual_audit_rejects_competing_elements_and_duplicate_text():
    request = direction(visualRole="hero")
    scene = request.scenes[0]
    seed = scene.elements[0]
    scene.elements.extend(
        seed.model_copy(
            update={
                "id": f"support-{index}",
                "kind": "shape",
                "text": "",
                "visual_role": "support",
                "x": index * 20,
                "y": index * 20,
                "width": 180,
                "height": 180,
            }
        )
        for index in range(5)
    )
    scene.elements.append(
        seed.model_copy(
            update={
                "id": "duplicate-title",
                "text": "DISTRIBUIÇÃO",
                "visual_role": "text",
                "x": seed.x,
                "y": seed.y,
            }
        )
    )

    audit = preflight_visual(request)
    codes = {finding["code"] for finding in audit["findings"]}

    assert "too_many_simultaneous_salient_elements" in codes
    assert "duplicate_concurrent_text" in codes
    assert audit["visualEditorial"] == "requires_correction"


def test_visual_audit_records_true_format_geometry_and_content_continuity():
    from test_demonstrable_production import composition

    from app.services.studios.editorial_components import lower_compositions

    candidate = composition(
        kinds=("image", "image", "image"),
        assets=("shared", "shared", "shared"),
        family="format_transformation",
    )
    lowered = lower_compositions(candidate, 640, 640)

    audit = preflight_visual(lowered, canvas_width=640, canvas_height=640)
    evidence = audit["states"][0]["formatTransformations"][0]

    assert [round(item["aspectRatio"], 2) for item in evidence["states"]] == [0.64, 1.0, 1.68]
    assert "format_viewport_ratio_mismatch" not in {
        finding["code"] for finding in audit["findings"]
    }
    assert "format_content_identity_lost" not in {
        finding["code"] for finding in audit["findings"]
    }

    for element in lowered.scenes[0].elements:
        if element.kind == "image":
            element.asset_id = f"different-{element.id}"
    broken = preflight_visual(lowered, canvas_width=640, canvas_height=640)
    assert "format_content_identity_lost" in {
        finding["code"] for finding in broken["findings"]
    }


def test_element_count_is_advisory_and_does_not_define_a_bad_plan_by_itself():
    from test_scene_compiler_v2 import document

    from app.services.studios.gemini_editing import validate_production_visual_preflight

    request = direction(visualRole="hero")
    seed = request.scenes[0].elements[0]
    request.scenes[0].elements.extend(
        seed.model_copy(
            update={"id": f"competing-{index}", "kind": "shape", "text": "", "visual_role": "support"}
        )
        for index in range(5)
    )

    result = validate_production_visual_preflight(request, document())
    finding = next(item for item in result["findings"] if item["code"] == "too_many_simultaneous_salient_elements")
    assert finding["severity"] == "advisory"


def test_production_preflight_still_blocks_a_structurally_missing_focus():
    from test_scene_compiler_v2 import document

    from app.services.studios.gemini_editing import validate_production_visual_preflight

    with pytest.raises(ValueError, match="production_visual_preflight_failed"):
        validate_production_visual_preflight(direction(), document())


def test_checkpoints_follow_temporal_dependency_and_repetition():
    scene = direction(durationFrames=20).scenes[0]
    scene.elements.append(
        EditorialElementV2(
            id="next",
            kind="text",
            purpose="Consequence",
            text="Conexão",
            width=200,
            height=100,
            duration_frames=20,
            start_frame=5,
            after_element_id="title",
            repeat_count=3,
            stagger_frames=10,
            reveal="words",
            reveal_frames=8,
        )
    )
    assert checkpoint_frames(scene)["consequence"] == 53


def test_real_export_checkpoints_have_checksum_and_explicit_coverage(tmp_path):
    path = tmp_path / "evidence.mp4"
    ffmpeg("-f", "lavfi", "-i", "testsrc2=s=320x320:r=25:d=4", "-c:v", "libx264", path)
    result = observe_visual_states(path, direction(reveal="words", revealFrames=30), max_frames=2)
    assert result["coverage"]["observedFrames"] == 2
    assert result["coverage"]["complete"] is False
    assert result["states"][0]["status"] == "incomplete_rendered_coverage"
    assert result["human"] == "pending"
    assert result["actionVerification"]["status"] == "pending"
    for evidence in result["renderedEvidence"]:
        assert evidence["encodedFrame"] == round(evidence["frame"] * 25 / 30)
        data = base64.b64decode(evidence["image"].split(",", 1)[1])
        assert data.startswith(b"\xff\xd8")
        assert hashlib.sha256(data).hexdigest() == evidence["checksumSha256"]


def test_renderer_geometry_detects_clipped_material_region_of_interest(tmp_path):
    path = tmp_path / "roi-evidence.mp4"
    ffmpeg("-f", "lavfi", "-i", "color=blue:s=320x320:r=30:d=4", "-c:v", "libx264", path)
    request = direction(kind="image", text="", assetId="material")
    request.scenes[0].elements[0].region_of_interest = {
        "x": 0.25,
        "y": 0.25,
        "width": 0.5,
        "height": 0.5,
        "purpose": "Preservar o objeto principal",
    }
    request = request.model_validate(request.model_dump(mode="json", by_alias=True))
    result = observe_visual_states(
        path,
        request,
        renderer_checks={
            "geometrySamples": [
                {
                    "frame": 0,
                    "elements": [
                        {
                            "semanticId": "title",
                            "present": True,
                            "visible": True,
                            "opacity": 1,
                            "bounds": {"x": 0, "y": 0, "width": 320, "height": 320},
                            "roiMeasurement": {
                                "method": "renderer_axis_aligned_object_fit",
                                "visibleRatio": 0.5,
                                "sourceWidth": 640,
                                "sourceHeight": 640,
                            },
                        }
                    ],
                }
            ]
        },
    )

    assert result["materialRegionOfInterest"][0]["status"] == "requires_review"
    assert any(
        finding["code"] == "material_region_of_interest_clipped"
        for finding in result["findings"]
    )


def test_discovery_never_claims_downloaded_or_verified_assets():
    assert discover(None, "people", "video")["status"] == "unconfigured"

    def respond(request):
        assert request.url.host == "api.pexels.com"
        return httpx.Response(200, json={"videos": [{"id": 7, "video_files": [{"link": "https://example.com/v.mp4"}]}]})

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        candidate = discover("test", "people", "video", client=client)["candidates"][0]
    assert candidate["renderReady"] is False
    assert candidate["observation"] == "not_inspected"


def test_discovery_transport_failure_is_sanitized():
    def fail(request):
        raise httpx.ConnectError("sensitive transport details", request=request)

    with httpx.Client(transport=httpx.MockTransport(fail)) as client:
        with pytest.raises(ValueError, match="^pexels_transport_unavailable$"):
            discover("test", "people", "image", client=client)


def test_image_discovery_exposes_bounded_hd_variant_before_original():
    def respond(_request):
        return httpx.Response(
            200,
            json={
                "photos": [
                    {
                        "id": 7,
                        "width": 9000,
                        "height": 7000,
                        "src": {
                            "original": "https://images.pexels.com/photos/7/original.jpeg",
                            "large2x": "https://images.pexels.com/photos/7/large2x.jpeg",
                            "large": "https://images.pexels.com/photos/7/large.jpeg",
                        },
                    }
                ]
            },
        )

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        files = discover("test", "people", "image", client=client)["candidates"][0]["files"]

    assert files[0] == {
        "link": "https://images.pexels.com/photos/7/large2x.jpeg",
        "width": 1880,
        "height": 1300,
    }
    assert files[-1]["width"] == 9000


def test_human_review_rejects_stale_export_and_records_actual_actor(monkeypatch):
    events = []
    monkeypatch.setattr("app.services.studios.visual_review.emit_event", lambda *args, **kwargs: events.append(kwargs))
    db = SimpleNamespace(flush=lambda: None)
    document = SimpleNamespace(id="doc", workspace_id="tenant", revision=2)
    asset = SimpleNamespace(
        id="export",
        workspace_id="tenant",
        lifecycle_status="active",
        checksum_sha256="a" * 64,
        object_metadata={"derivation": "video_render", "documentId": "doc", "documentRevision": 1},
    )
    request = VisualHumanReviewV1(
        expected_document_revision=2,
        render_checksum="a" * 64,
        clarity=4,
        rhythm=3,
        suitability=4,
        continuity=4,
        notes="A pausa final é longa.",
    )
    user = SimpleNamespace(id="reviewer")
    with pytest.raises(ValueError, match="visual_review_binding_conflict"):
        record_visual_review(db, document, asset, request, user)
    assert events == []
    asset.object_metadata["documentRevision"] = 2
    receipt = record_visual_review(db, document, asset, request, user)
    assert receipt["status"] == "requires_correction"
    assert events[0]["actor_id"] == "reviewer"
    assert "humanApproved" not in asset.object_metadata


def test_required_footage_cannot_silently_become_typography():
    from app.domain.studios.editorial_production import validate_blueprint_composition

    candidate = direction()
    storyboard = SimpleNamespace(
        beats=[SimpleNamespace(id="scene", visual_blueprint=SimpleNamespace(representation="footage"))]
    )
    request = SimpleNamespace(require_visual_blueprint=True)
    with pytest.raises(ValueError, match="production_blueprint_footage_missing:scene"):
        validate_blueprint_composition(candidate, storyboard, request)
    # V1/older requests are not retrospectively subjected to the opt-in blueprint contract.
    validate_blueprint_composition(candidate, storyboard, SimpleNamespace(require_visual_blueprint=False))


def test_procedural_hero_can_satisfy_a_cutout_blueprint():
    from app.domain.studios.editorial_production import validate_blueprint_composition

    candidate = direction()
    candidate.scenes[0].elements[0] = candidate.scenes[0].elements[0].model_copy(
        update={"kind": "shape", "text": "", "visual_role": "hero", "shape": "ellipse"}
    )
    storyboard = SimpleNamespace(
        beats=[
            SimpleNamespace(
                id="scene",
                visual_blueprint=SimpleNamespace(representation="cutout"),
            )
        ]
    )

    validate_blueprint_composition(
        candidate,
        storyboard,
        SimpleNamespace(require_visual_blueprint=True, mode="motion"),
    )


def test_mixed_montage_allows_a_typographic_ending_after_real_media():
    from app.domain.studios.editorial_production import validate_blueprint_composition

    candidate = direction()
    media_scene = candidate.scenes[0]
    media_scene.elements[0] = media_scene.elements[0].model_copy(
        update={"kind": "image", "text": "", "asset_id": "verified-media", "visual_role": "hero"}
    )
    ending = media_scene.model_copy(deep=True)
    ending.id = "ending"
    ending.elements = [
        ending.elements[0].model_copy(
            update={"id": "ending-copy", "kind": "text", "text": "Não garante atenção", "visual_role": "hero"}
        )
    ]
    ending.material_needs = []
    candidate.scenes = [media_scene, ending]
    storyboard = SimpleNamespace(
        beats=[
            SimpleNamespace(id=media_scene.id, visual_blueprint=SimpleNamespace(representation="mixed")),
            SimpleNamespace(
                id="ending",
                visual_blueprint=SimpleNamespace(
                    representation="mixed", primary_material_query="typography/alert-warning-pt"
                ),
            ),
        ]
    )
    request = SimpleNamespace(require_visual_blueprint=True, mode="mixed_montage")

    validate_blueprint_composition(candidate, storyboard, request)


def test_visual_only_skips_voice_without_provider_calls():
    from app.services.studios.production_narration import prepare_narration

    assert prepare_narration(None, None, {}, SimpleNamespace(evaluation_scope="visual_only"), None) == ([], None)
