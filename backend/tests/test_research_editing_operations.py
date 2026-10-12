"""Research cards remain evidence; executable techniques require a bound recipe."""

import hashlib
import subprocess
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.domain.studios.contextual_editing import digest
from app.domain.studios.contextual_editing_v2 import ContextualPlanRequestV2
from app.domain.studios.contracts import AssetReferenceV1, CreativeDocumentV1, VideoRenderRequestV1
from app.services.studios.editing_repertoire import RESEARCH_EXECUTABLE_IDS, research_operation_cards
from app.services.studios.editorial_operation_selection import evaluate_operation_bindings
from app.services.studios.scene_compiler import compile_scenes


def variant_direction(component="moving_variant_mask"):
    return ContextualPlanRequestV2.model_validate(
        {
            "expectedDocumentRevision": 1,
            "intent": {"objective": "Reveal a change in a product"},
            "scenes": [
                {
                    "id": "reveal",
                    "purpose": "Compare variants",
                    "durationFrames": 15,
                    "verification": ["The changed region is visible"],
                    "techniqueIds": [component],
                    "operationBindings": [
                        {
                            "techniqueId": component,
                            "targetIds": ["variant"],
                            "anchorId": "product",
                            "cutMotivation": "A gesture crosses the product",
                            "newInformation": "The changed state becomes visible",
                        }
                    ],
                    "elements": [
                        {
                            "id": "base",
                            "kind": "image",
                            "purpose": "Original state",
                            "assetId": "red",
                            "width": 320,
                            "height": 320,
                            "durationFrames": 15,
                            "zIndex": 1,
                        },
                        {
                            "id": "variant",
                            "kind": "image",
                            "purpose": "Changed state",
                            "assetId": "blue",
                            "width": 320,
                            "height": 320,
                            "durationFrames": 15,
                            "zIndex": 2,
                        },
                        *(
                            [
                                {
                                    "id": "gesture",
                                    "kind": "image",
                                    "purpose": "Real covering gesture",
                                    "assetId": "hand",
                                    "maskAssetId": "mask",
                                    "width": 320,
                                    "height": 320,
                                    "durationFrames": 15,
                                    "zIndex": 3,
                                }
                            ]
                            if component == "gesture_occlusion_reveal"
                            else []
                        ),
                    ],
                    "nativeComponents": [
                        {
                            "component": component,
                            "targetIds": ["variant"],
                            "baseTargetId": "base",
                            "switchFrame": 2,
                            "entranceFrames": 8,
                            "maskStartX": 0 if component == "gesture_occlusion_reveal" else 0.25,
                            "maskEndX": 1 if component == "gesture_occlusion_reveal" else 0.75,
                            "maskRadius": 0.16,
                            **({"occluderTargetId": "gesture"} if component == "gesture_occlusion_reveal" else {}),
                        }
                    ],
                }
            ],
        }
    )


def document(assets):
    now = datetime.now(UTC)
    return CreativeDocumentV1(
        document_id="research-test",
        workspace_id="workspace",
        title="Reusable technique",
        content_type="video",
        correlation_id="test",
        brand_memory_ref={"id": "brand", "revision": 1},
        brief={"objective": "Show the changed state", "audience": "Customer"},
        assets=[
            {"id": item, "mediaType": "image/png", "checksum": item[0] * 64, "rightsStatus": "verified"}
            for item in assets
        ],
        composition={"pages": [{"id": "page", "width": 320, "height": 320, "safeArea": 0}]},
        created_at=now,
        updated_at=now,
    )


def test_research_cards_separate_executable_and_knowledge_only():
    cards = research_operation_cards()
    assert len(cards) == 12
    assert {card.id for card in cards if card.qualification == "implemented"} == RESEARCH_EXECUTABLE_IDS
    assert all(card.source_digest and card.sources and card.method_limitations for card in cards)
    assert all(card.qualification != "render_verified" for card in cards)
    assert all(not card.creator_claims for card in cards)


@pytest.mark.parametrize(
    "component,assets",
    [
        ("moving_variant_mask", ("red", "blue")),
        ("gesture_occlusion_reveal", ("red", "blue", "hand", "mask")),
    ],
)
def test_registered_reveals_bind_real_layers_and_change_composition_hash(component, assets):
    direction = variant_direction(component)
    source = document(assets)
    decisions = evaluate_operation_bindings(direction, source)
    assert decisions[0]["status"] == "eligible", decisions
    first, _, _, manifest = compile_scenes(source, direction, "user", "plan")
    assert first.composition.narrative["editorialV2"]["operationBindings"][0]["techniqueId"] == component
    assert first.composition.narrative["editorialV2"]["renderer"] == "remotion.contextual-v2"
    if component == "gesture_occlusion_reveal":
        direction.scenes[0].native_components[0].entrance_frames = 9
    else:
        direction.scenes[0].native_components[0].mask_end_x = 0.62
    second, _, _, modified = compile_scenes(source, direction, "user", "plan")
    assert digest(first.composition) != digest(second.composition)
    assert manifest["hashes"]["executableComposition"] != modified["hashes"]["executableComposition"]


def test_variant_missing_rights_or_geometry_is_rejected():
    direction = variant_direction()
    source = document(("red",))
    assert evaluate_operation_bindings(direction, source)[0]["status"] == "blocked"
    raw = direction.model_dump(mode="json", by_alias=True)
    raw["scenes"][0]["elements"][1]["x"] = 10
    with pytest.raises(ValidationError, match="editing_native_variant_geometry_mismatch"):
        ContextualPlanRequestV2.model_validate(raw)


def test_unbound_research_operation_has_a_material_blocker():
    direction = variant_direction()
    direction.scenes[0].operation_bindings = []
    decision = evaluate_operation_bindings(direction, document(("red", "blue")))[0]
    assert decision["status"] == "blocked"
    assert decision["alternative"]


def test_action_progression_requires_distinct_timed_shots():
    lighting = {
        "quality": "available",
        "direction": "side",
        "contrast": "medium",
        "temperatureRelationship": "Consistent",
        "subjectSeparation": "Visible",
        "executionMode": "select_existing_footage",
    }
    shots = []
    for index, (element, action) in enumerate((("prepare", "Opens the can"), ("result", "Pours the drink"))):
        shots.append(
            {
                "id": f"shot-{index}",
                "function": "demonstrate" if index == 0 else "consequence",
                "subject": "Canned drink",
                "observableAction": action,
                "shotScale": "close",
                "angle": "eye_level",
                "regionOfInterest": "Hands and can",
                "attentionStart": "Can",
                "attentionEnd": "Drink",
                "lighting": lighting,
                "cutMotivation": "Continue the gesture",
                "targetElementIds": [element],
                "executionComponentIds": ["action_progression"],
                "verification": ["Action visible"],
                "startFrame": index * 15,
                "endFrameExclusive": (index + 1) * 15,
            }
        )
    direction = ContextualPlanRequestV2.model_validate(
        {
            "expectedDocumentRevision": 1,
            "intent": {"objective": "Show drink preparation"},
            "scenes": [
                {
                    "id": "action",
                    "purpose": "Show preparation and consequence",
                    "durationFrames": 30,
                    "verification": ["Visible pour"],
                    "techniqueIds": ["action_progression"],
                    "operationBindings": [
                        {
                            "techniqueId": "action_progression",
                            "targetIds": ["prepare", "result"],
                            "anchorId": "can",
                            "cutMotivation": "The pouring motion continues",
                            "newInformation": "The drink reaches the glass",
                        }
                    ],
                    "elements": [
                        {
                            "id": item,
                            "kind": "video",
                            "purpose": action,
                            "assetId": item,
                            "width": 320,
                            "height": 320,
                            "startFrame": index * 15,
                            "durationFrames": 15,
                            "sourceAudio": "mute",
                        }
                        for index, (item, action) in enumerate((("prepare", "Opens can"), ("result", "Pours drink")))
                    ],
                    "nativeComponents": [
                        {"component": "action_montage", "targetIds": ["prepare", "result"], "entranceFrames": 4}
                    ],
                    "shotPlan": shots,
                }
            ],
        }
    )
    source = document(())
    source.assets = [
        AssetReferenceV1.model_validate(
            {"id": item, "mediaType": "video/mp4", "checksum": "a" * 64, "rightsStatus": "verified"}
        )
        for item in ("prepare", "result")
    ]
    assert evaluate_operation_bindings(direction, source)[0]["status"] == "eligible"
    direction.scenes[0].elements[1].start_frame = 10
    assert evaluate_operation_bindings(direction, source)[0]["status"] == "blocked"


def test_motif_requires_same_identifiable_anchor_across_shots():
    direction = variant_direction()
    scene = direction.scenes[0]
    scene.native_components = []
    scene.technique_ids = ["motif_continuity"]
    scene.operation_bindings = [
        scene.operation_bindings[0].model_copy(
            update={"technique_id": "motif_continuity", "target_ids": ["base", "variant"], "anchor_id": "product"}
        )
    ]
    scene.elements[0].content_identity = "product"
    scene.elements[1].content_identity = "product"
    scene.elements[0].duration_frames = 7
    scene.elements[1].start_frame = 7
    scene.elements[1].duration_frames = 8
    assert evaluate_operation_bindings(direction, document(("red", "blue")))[0]["status"] == "eligible"
    scene.elements[1].content_identity = "unrelated"
    assert evaluate_operation_bindings(direction, document(("red", "blue")))[0]["status"] == "blocked"


@pytest.mark.parametrize(
    "brief,base,variant",
    [
        ("cold drink", "drink_base", "drink_variant"),
        ("urban backpack", "pack_base", "pack_variant"),
        ("task app", "task_base", "task_variant"),
    ],
)
def test_same_component_supports_distinct_briefs_and_two_rhythms(brief, base, variant):
    direction = variant_direction()
    direction.intent.objective = brief
    direction.scenes[0].purpose = "Reveal change in " + brief
    direction.scenes[0].elements[0].asset_id = base
    direction.scenes[0].elements[1].asset_id = variant
    direction.scenes[0].operation_bindings[0].anchor_id = brief.replace(" ", "-")
    source = document((base, variant))
    compositions = []
    for entrance in (4, 10):
        direction.scenes[0].native_components[0].entrance_frames = entrance
        assert evaluate_operation_bindings(direction, source)[0]["status"] == "eligible"
        draft, _, _, _ = compile_scenes(source, direction, "user", "plan")
        compositions.append(digest(draft.composition))
    assert compositions[0] != compositions[1]
