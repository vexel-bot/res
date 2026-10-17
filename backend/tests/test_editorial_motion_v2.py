"""The new graphic-motion path must change executable geometry, not just prose."""

import pytest

from app.domain.studios.contextual_editing_v2 import ContextualPlanRequestV2
from app.services.studios.gemini_editing import compact_editorial_motion_schema
from app.services.studios.editorial_components import (
    classify_contract_repairs,
    lower_compositions,
    repair_raw_composition_contracts,
    semantic_contract_repairs,
)
from app.services.studios.scene_compiler import current_execution_versions
from app.domain.studios.visual_audit import preflight_visual
from test_semantic_demonstration import canonical_direction


def editorial_direction(layout="typography_dominant", alignment="left"):
    raw = canonical_direction().model_dump(mode="json", by_alias=True)
    raw["artDirection"] = {
        "visualSystem": "An editorial composition built around one persistent piece",
        "palette": ["#101820", "#f6e9cd", "#ff6b35"],
        "typography": "A clear display hierarchy",
        "contrastStrategy": "Light type on a dark ground",
        "footageTreatment": "No footage required",
        "graphicsRelationship": "The same image and headline travel together",
        "continuityRules": ["Keep the image and headline recognizable"],
        "motionSystem": {"layout": layout, "alignment": alignment, "frame": "none"},
    }
    raw["scenes"][0]["compositions"][0].update(
        stateHoldFrames=[9, 9], movementFrames=6
    )
    return ContextualPlanRequestV2.model_validate(raw)


def test_canonical_claim_requires_sourced_content_but_procedural_action_can_wait_for_review():
    raw = canonical_direction().model_dump(mode="json", by_alias=True)
    scene = raw["scenes"][0]
    assertion = scene["semanticAssertions"][0]
    scene["contentReferenceIds"] = []
    for element in scene["elements"]:
        element["contentReferenceId"] = None
        element["contentPartId"] = None
    with pytest.raises(ValueError, match="editing_v2_assertion_content_reference_required"):
        ContextualPlanRequestV2.model_validate(raw)
    assertion["kind"] = "visual_action"
    assertion["requiredPartIds"] = []
    ContextualPlanRequestV2.model_validate(raw)


def by_id(direction):
    return {element.id: element for element in direction.scenes[0].elements}


def test_editorial_direction_changes_layout_and_removes_default_frame():
    left = lower_compositions(editorial_direction(), 720, 1280)
    right = lower_compositions(editorial_direction("graphic_motif", "right"), 720, 1280)
    a, b = by_id(left), by_id(right)

    assert left.scenes[0].background == "#101820"
    assert a["portrait"].border_width == 0
    assert a["portrait"].x < b["portrait"].x
    assert a["portrait-title"].height > b["portrait-title"].height
    assert a["portrait-media"].height < b["portrait-media"].height
    assert a["portrait-title"].text_align == "left"
    assert b["portrait-title"].text_align == "right"


def test_persistent_parts_move_before_next_state_without_fading_or_letter_distortion():
    lowered = lower_compositions(editorial_direction(), 720, 1280)
    elements = by_id(lowered)

    assert elements["portrait"].start_frame == 0
    assert elements["portrait"].duration_frames == 15
    assert elements["square"].start_frame == 15
    assert elements["square"].duration_frames == 15
    assert elements["square"].animations == []
    assert elements["portrait-media"].object_fit == "contain"
    assert elements["square-media"].object_fit == "contain"
    for part in ("media", "title"):
        tracks = {track.property: track for track in elements[f"portrait-{part}"].animations}
        assert set(tracks) == {"position_x", "position_y", "scale_x", "scale_y"}
        assert tracks["scale_x"].keyframes[-1].value == pytest.approx(
            tracks["scale_y"].keyframes[-1].value
        )
        assert tracks["position_x"].keyframes[0].frame == 8
        assert tracks["position_x"].keyframes[-1].frame == 14
        assert elements[f"square-{part}"].start_frame == 15
        assert elements[f"square-{part}"].reveal == "none"


def test_editorial_timing_rejects_an_undersized_scene():
    direction = editorial_direction()
    direction.scenes[0].duration_frames = 20
    with pytest.raises(ValueError, match="editorial_timing_exceeds_scene"):
        lower_compositions(direction, 720, 1280)


def test_audit_reports_the_version_it_actually_evaluated():
    direction = editorial_direction()
    direction.execution_versions = current_execution_versions()
    audit = preflight_visual(lower_compositions(direction, 720, 1280), canvas_width=720, canvas_height=1280)
    assert audit["motion"]["componentVersion"] == direction.execution_versions.components


def test_compact_provider_schema_keeps_executable_fields_without_default_noise():
    full = ContextualPlanRequestV2.model_json_schema(by_alias=True)
    compact = compact_editorial_motion_schema(full)
    assert "artDirection" in compact["properties"]
    assert "semanticVerificationPolicy" in compact["properties"]
    assert compact["properties"]["semanticVerificationPolicy"] == {
        "type": "string", "const": "canonical_demonstration_v1"
    }
    scene = compact["$defs"]["EditorialSceneV2"]["properties"]
    element = compact["$defs"]["EditorialElementV2"]["properties"]
    composition = compact["$defs"]["EditorialCompositionV1"]["properties"]
    assert {"semanticAssertions", "compositions", "materialNeeds"} <= set(scene)
    assert {"contentIdentity", "fontSize", "parentId"} <= set(element)
    assert "contentReferenceId" not in element
    assert "contentReferences" not in compact["properties"]
    assert "effects" not in element
    assert {"stateHoldFrames", "movementFrames"} <= set(composition)
    assert len(str(compact)) < len(str(full)) * 0.8


def test_asymmetric_sequence_reserves_opposite_regions_for_copy_and_motif():
    raw = editorial_direction("editorial_asymmetric").model_dump(mode="json", by_alias=True)
    raw["semanticVerificationPolicy"] = "legacy_execution_v1"
    raw["contentReferences"] = []
    raw["scenes"][0]["contentReferenceIds"] = []
    raw["scenes"][0]["semanticAssertions"] = []
    raw["scenes"][0]["elements"] = [
        {"id": "copy", "kind": "text", "purpose": "Explain", "text": "Uma ideia",
         "width": 200, "height": 80, "durationFrames": 30},
        {"id": "motif", "kind": "shape", "purpose": "Show movement", "shape": "ellipse",
         "width": 100, "height": 100, "durationFrames": 30},
    ]
    raw["scenes"][0]["compositions"] = [{
        "id": "progress", "family": "sequence", "targetIds": ["copy", "motif"],
        "purpose": "Move focus", "expectedResult": "Idea becomes visible",
        "stateHoldFrames": [10, 10], "movementFrames": 5,
    }]
    lowered = lower_compositions(ContextualPlanRequestV2.model_validate(raw), 720, 1280)
    elements = by_id(lowered)
    assert elements["copy"].x < elements["motif"].x
    assert elements["copy"].width < 720 * 0.6
    assert elements["motif"].start_frame == 10


def test_only_unreferenced_unsourced_procedural_bindings_are_removed():
    raw = {
        "contentReferences": [
            {"id": "unsourced", "parts": [{"id": "mark", "role": "primary_media"}]},
            {"id": "claimed", "parts": [{"id": "mark", "role": "primary_media"}]},
            {"id": "partial", "parts": [
                {"id": "label", "role": "title", "text": "Uma ideia"},
                {"id": "brand", "role": "identity", "text": "RES"},
                {"id": "line", "role": "primary_media"},
            ]},
        ],
        "scenes": [{
            "id": "scene", "durationFrames": 30,
            "contentReferenceIds": ["unsourced", "claimed", "partial"],
            "elements": [
                {"id": "path", "kind": "path", "contentReferenceId": "unsourced", "contentPartId": "mark"},
                {"id": "line", "kind": "path", "contentReferenceId": "partial", "contentPartId": "line"},
            ],
            "compositions": [],
            "semanticAssertions": [{"objectId": "claimed"}],
        }],
    }
    repairs = repair_raw_composition_contracts(raw, graphic_motion=True)
    assert [item["id"] for item in raw["contentReferences"]] == ["claimed", "partial"]
    assert [item["id"] for item in raw["contentReferences"][1]["parts"]] == ["label", "brand"]
    assert raw["scenes"][0]["contentReferenceIds"] == ["claimed", "partial"]
    assert "contentReferenceId" not in raw["scenes"][0]["elements"][0]
    assert "contentReferenceId" not in raw["scenes"][0]["elements"][1]
    assert repairs[0]["reason"] == "unsourced_unreferenced_procedural_content_binding_removed"
    assert semantic_contract_repairs(classify_contract_repairs(repairs)) == []
