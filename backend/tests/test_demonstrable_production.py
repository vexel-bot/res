# ruff: noqa: F811
import pytest
from test_contextual_editing import media as media
from test_contextual_editing import project as project

from app.domain.studios.contextual_editing_v2 import (
    ContextualPlanRequestV2,
    EditorialElementV2,
    EditorialMaterialV2,
)
from app.domain.studios.editorial_production import (
    EditorialDirectionV1,
    ProductionRequestV1,
    bind_storyboard_scene_ids,
    derive_blueprint_material_needs,
    normalize_direction_identifiers,
    production_gates,
    validate_blueprint_composition,
    validate_direction,
)
from app.services.studios.editorial_components import lower_compositions, repair_composition_contracts
from app.services.studios.gemini_editing import editorial_direction_output_schema
from app.services.studios.production_audit import correction_action, observed_result_gate

SCRIPT = "Um conteúdo pode virar diferentes formatos. Mas distribuir não garante atenção."


def request(*, required=True):
    return ProductionRequestV1.model_validate(
        {
            "direction": {
                "expectedDocumentRevision": 1,
                "intent": {
                    "objective": "Explicar distribuição",
                    "script": SCRIPT,
                    "lockedFacts": ["Mas distribuir não garante atenção."],
                },
            },
            "mode": "motion",
            "requireVisualBlueprint": required,
            "demonstrationPolicy": "required" if required else "disabled",
        }
    )


def test_direction_schema_requires_policy_fields_without_breaking_persisted_v1_contract():
    production_request = request(required=True).model_copy(update={"cinematic_direction_policy": "mixed_motion_v1"})

    schema = editorial_direction_output_schema(production_request)
    beat = schema["$defs"]["StoryboardBeatV1"]
    blueprint = schema["$defs"]["VisualBlueprintV1"]

    assert beat["properties"]["visualBlueprint"] == {"$ref": "#/$defs/VisualBlueprintV1"}
    assert "visualBlueprint" in beat["required"]
    assert blueprint["properties"]["demonstration"] == {"$ref": "#/$defs/VisualDemonstrationV1"}
    assert "demonstration" in blueprint["required"]
    assert "shotSequence" in blueprint["required"]
    assert blueprint["properties"]["shotSequence"]["minItems"] == 1
    assert "artDirection" in schema["required"]
    assert schema["properties"]["artDirection"] == {"$ref": "#/$defs/CinematicArtDirectionV1"}


def test_compiler_reuses_the_approved_art_direction():
    from app.domain.studios.contextual_editing_v2 import CinematicArtDirectionV1
    from app.domain.studios.editorial_production import bind_storyboard_scene_ids

    direction = storyboard()
    direction.art_direction = {
        "visualSystem": "Sistema aprovado",
        "palette": ["#101c29", "#ffffff"],
        "typography": "Sem serifa",
        "contrastStrategy": "Alto contraste",
        "footageTreatment": "Natural",
        "graphicsRelationship": "Gráficos discretos",
        "continuityRules": ["Preservar o objeto"],
        "rejectedStyleMoves": ["Ornamento genérico"],
    }
    candidate = composition()
    candidate.art_direction = {
        "visualSystem": "Alternativa do compilador",
        "palette": ["#000000", "#ff0000"],
        "typography": "Decorativa",
        "contrastStrategy": "Baixo contraste",
        "footageTreatment": "Artificial",
        "graphicsRelationship": "Cobrir a filmagem",
        "continuityRules": ["Nenhuma"],
        "rejectedStyleMoves": ["Outra regra"],
    }

    repairs = bind_storyboard_scene_ids(candidate, direction)

    assert candidate.art_direction == CinematicArtDirectionV1.model_validate(direction.art_direction)
    assert repairs[0]["reason"] == "compiled_art_direction_rebound_to_approved_direction"
    assert repairs[0]["requiresAlternative"] is False


def test_approved_shot_expands_its_bound_target_visibility():
    from app.services.studios.editorial_components import bind_shot_semantics_to_blueprint

    direction = storyboard()
    payload = composition().model_dump(mode="json", by_alias=True)
    payload["scenes"][0]["id"] = direction.beats[0].id
    payload["scenes"][0]["elements"][0].update(startFrame=20, durationFrames=30)
    shot = {
        "id": "shot",
        "function": "demonstrate",
        "subject": "Conteúdo",
        "observableAction": "Transforma",
        "shotScale": "medium",
        "angle": "eye_level",
        "regionOfInterest": "Centro",
        "attentionStart": "Origem",
        "attentionEnd": "Formato",
        "lighting": {
            "quality": "graphic",
            "direction": "not_applicable",
            "contrast": "high",
            "temperatureRelationship": "Neutra",
            "subjectSeparation": "Alta",
            "executionMode": "deterministic_composite",
        },
        "cutMotivation": "Demonstrar",
        "continuity": [],
        "materialRequirementIds": [],
        "executionComponentIds": [],
        "targetElementIds": ["element-0"],
        "verification": ["Visível"],
        "startFrame": 0,
        "endFrameExclusive": 90,
    }
    payload["scenes"][0]["shotPlan"] = [shot]
    direction_payload = direction.model_dump(mode="json", by_alias=True)
    direction_payload["beats"][0]["visualBlueprint"]["shotSequence"] = [shot]
    direction = EditorialDirectionV1.model_validate(direction_payload)
    candidate = ContextualPlanRequestV2.model_validate(payload)

    repairs = bind_shot_semantics_to_blueprint(candidate, direction)
    target = candidate.scenes[0].elements[0]

    assert (target.start_frame, target.duration_frames) == (0, 90)
    assert any(repair["reason"] == "shot_target_interval_expanded_to_shot" for repair in repairs)


def test_evidence_with_visual_annotation_uses_the_annotation_composition():
    candidate = composition(kinds=("video", "shape"), family="evidence")
    candidate.scenes[0].elements[1].visual_role = "accent"

    repairs = repair_composition_contracts(candidate)

    assert candidate.scenes[0].compositions[0].family == "annotated_material"
    assert any(
        repair["reason"] == "evidence_path_annotation_promoted_to_annotated_material"
        and repair["requiresAlternative"] is False
        for repair in repairs
    )


def storyboard(*, demonstration=True, procedural=False):
    blueprint = {
        "message": SCRIPT,
        "evidence": "O mesmo conteúdo muda de enquadramento e preserva a identidade.",
        "representation": "process",
        "rejectedAlternatives": ["Somente três rótulos ligados por linhas"],
        "primaryMaterialQuery": "imagem de conteúdo original",
        "regionOfInterest": "conteúdo dentro dos formatos",
        "hierarchy": ["conteúdo", "formatos", "conclusão"],
        "completionCriteria": ["A origem permanece reconhecível"],
        "visualRegister": "editorial",
    }
    if demonstration:
        blueprint["demonstration"] = {
            "observableAction": "Uma imagem ocupa um Reel e depois um carrossel.",
            "intendedUnderstanding": "A distribuição adapta o mesmo conteúdo.",
            "proofElements": ["a mesma imagem nos dois suportes"],
            "indispensableMaterials": [
                {
                    "id": "source-content",
                    "kind": "image",
                    "visualRole": "hero",
                    "query": "conteúdo original sobre uma mesa",
                    "purpose": "Manter uma origem reconhecível entre formatos",
                    "acceptanceCriteria": ["a imagem aparece inteira"],
                    "proceduralAllowed": procedural,
                }
            ],
            "genericFailureSignals": ["Aparecem apenas rótulos sem transformação"],
            **(
                {"proceduralSufficiencyReason": "Os suportes registrados mostram a transformação."}
                if procedural
                else {}
            ),
        }
    concept = {
        "premise": "Transformar uma origem",
        "clarity": "A mudança é visível",
        "specificity": "Reel e carrossel",
        "continuity": "A imagem persiste",
        "identityFit": "Tokens do projeto",
        "feasibility": "Composição registrada",
    }
    return EditorialDirectionV1.model_validate(
        {
            "concepts": [
                {"id": "formats", "visualMechanism": "Transformar o mesmo material", **concept},
                {"id": "contexts", "visualMechanism": "Mostrar pessoas em contextos distintos", **concept},
            ],
            "selectedConceptId": "formats",
            "selectionReason": "Mostra adaptação diretamente",
            "beats": [
                {
                    "id": "formats",
                    "sourceExcerpt": SCRIPT,
                    "narration": SCRIPT,
                    "initialState": "Uma origem",
                    "action": "Transformar em formatos",
                    "consequence": "A origem alcança contextos diferentes",
                    "focus": "Conteúdo",
                    "knowledgeGained": "Distribuição exige adaptação",
                    "transitionReason": "Apresentar a ressalva",
                    "visualBlueprint": blueprint,
                }
            ],
        }
    )


def composition(*, kinds=("image", "card"), assets=(None, None), family="evidence"):
    elements = []
    for index, kind in enumerate(kinds):
        elements.append(
            {
                "id": f"element-{index}",
                "kind": kind,
                "purpose": "Demonstrar",
                "text": "Formato" if kind in {"text", "card"} else "",
                "assetId": assets[index],
                "visualRole": "hero" if index == 0 else "support",
                "width": 240,
                "height": 240,
                "durationFrames": 90,
            }
        )
    return ContextualPlanRequestV2.model_validate(
        {
            "expectedDocumentRevision": 1,
            "intent": {"objective": "Explicar", "script": SCRIPT},
            "scenes": [
                {
                    "id": "formats",
                    "purpose": "Demonstrar adaptação",
                    "durationFrames": 90,
                    "narration": SCRIPT,
                    "verification": ["Transformação observável"],
                    "elements": elements,
                    "compositions": [
                        {
                            "id": "demo",
                            "family": family,
                            "targetIds": [item["id"] for item in elements],
                            "purpose": "Demonstrar",
                            "expectedResult": "Mudança reconhecível",
                            "actionFrames": 15,
                        }
                    ],
                }
            ],
        }
    )


def test_required_demonstration_rejects_structural_blueprint_only():
    with pytest.raises(ValueError, match="visual_demonstration_required"):
        validate_direction(storyboard(demonstration=False), request())
    validate_direction(storyboard(demonstration=False), request(required=False))


def test_unexplained_procedural_permission_is_conservatively_removed_without_replanning():
    payload = storyboard(procedural=True).model_dump(mode="json", by_alias=True)
    demonstration = payload["beats"][0]["visualBlueprint"]["demonstration"]
    demonstration.pop("proceduralSufficiencyReason")
    normalized, repairs = normalize_direction_identifiers(payload)
    material = normalized["beats"][0]["visualBlueprint"]["demonstration"]["indispensableMaterials"][0]
    assert material["proceduralAllowed"] is False
    assert any("proceduralAllowed" in repair["field"] for repair in repairs)
    EditorialDirectionV1.model_validate(normalized)


def test_non_composable_material_cannot_keep_a_procedural_component():
    payload = storyboard(procedural=True).model_dump(mode="json", by_alias=True)
    material = payload["beats"][0]["visualBlueprint"]["demonstration"]["indispensableMaterials"][0]
    material.update(requirementClass="mandatory", componentId="groups")

    normalized, repairs = normalize_direction_identifiers(payload)
    material = normalized["beats"][0]["visualBlueprint"]["demonstration"]["indispensableMaterials"][0]

    assert material["requirementClass"] == "mandatory"
    assert material["proceduralAllowed"] is False
    assert "componentId" not in material
    assert any(repair["to"] == "removed_non_composable" for repair in repairs)
    EditorialDirectionV1.model_validate(normalized)


def test_indispensable_material_becomes_bound_need_but_gate_waits_for_file():
    direction = storyboard()
    candidate = derive_blueprint_material_needs(composition(), direction)
    need = candidate.scenes[0].material_needs[0]
    assert need.blueprint_requirement_id == "source-content"
    assert need.target_id == "element-0"
    validate_blueprint_composition(candidate, direction, request())
    gates = production_gates(direction, request(), candidate)
    assert gates["fidelity"]["status"] == "passed"
    assert gates["demonstrability"]["status"] == "passed"
    assert gates["techniqueSuitability"]["status"] == "inconclusive"
    assert gates["techniqueSuitability"]["nextAction"] == "resolve_material"
    assert gates["sceneStages"][0]["stage"] == "material_pending"
    assert gates["observedResult"]["status"] == "inconclusive"


def test_existing_need_on_indispensable_target_is_bound_instead_of_duplicated():
    direction = storyboard()
    candidate = composition()
    scene = candidate.scenes[0]
    scene.material_needs = [
        {
            "id": "director-need",
            "targetId": "element-0",
            "kind": "image",
            "query": "conteúdo original sobre uma mesa",
            "purpose": "Fornecer a evidência principal",
            "sourceClass": "licensed_stock",
            "visualDescription": "imagem real de conteúdo sobre uma mesa",
            "acceptanceCriteria": ["o conteúdo está visível"],
        }
    ]
    candidate = ContextualPlanRequestV2.model_validate(candidate.model_dump(mode="json", by_alias=True))

    derive_blueprint_material_needs(candidate, direction)

    assert len(candidate.scenes[0].material_needs) == 1
    need = candidate.scenes[0].material_needs[0]
    assert need.id == "director-need"
    assert need.blueprint_requirement_id == "source-content"
    assert need.acceptance_criteria == ["o conteúdo está visível", "a imagem aparece inteira"]


def test_composite_blueprint_requirement_binds_multiple_support_clips_as_a_group():
    direction = storyboard()
    requirement = direction.beats[0].visual_blueprint.demonstration.indispensable_materials[0]
    requirement.kind = "video"
    requirement.visual_role = "hero"
    requirement.source_class = "licensed_stock"
    candidate = composition(kinds=("video", "video"))
    scene = candidate.scenes[0]
    for element in scene.elements:
        element.visual_role = "support"
    raw = candidate.model_dump(mode="json", by_alias=True)
    raw["scenes"][0]["materialNeeds"] = [
        {
            "id": "clip-a",
            "targetId": "element-0",
            "kind": "video",
            "query": "pessoa usando smartphone",
            "purpose": "Primeiro contexto",
            "sourceClass": "licensed_stock",
            "acceptanceCriteria": ["uma pessoa usa smartphone"],
        },
        {
            "id": "clip-b",
            "targetId": "element-1",
            "kind": "video",
            "query": "pessoa usando tablet",
            "purpose": "Segundo contexto",
            "sourceClass": "licensed_stock",
            "acceptanceCriteria": ["uma pessoa usa tablet"],
        },
    ]
    candidate = ContextualPlanRequestV2.model_validate(raw)

    derive_blueprint_material_needs(candidate, direction)

    needs = candidate.scenes[0].material_needs
    assert len(needs) == 2
    assert {need.blueprint_requirement_id for need in needs} == {"source-content"}
    assert needs[0].acceptance_criteria == ["uma pessoa usa smartphone"]
    assert needs[1].acceptance_criteria == ["uma pessoa usa tablet"]


def test_required_mixed_montage_needs_contextual_stock_not_only_cutout_icons():
    mixed_request = request().model_copy(
        update={"mode": "mixed_montage", "material_semantics_policy": "contextual_video_v1"}
    )
    icon_only_direction = storyboard()
    icon_only_candidate = derive_blueprint_material_needs(composition(), icon_only_direction)
    with pytest.raises(ValueError, match="mixed_montage_contextual_media_missing"):
        validate_blueprint_composition(icon_only_candidate, icon_only_direction, mixed_request)

    contextual_direction = storyboard()
    requirement = contextual_direction.beats[0].visual_blueprint.demonstration.indispensable_materials[0]
    requirement.kind = "video"
    requirement.source_class = "licensed_stock"
    contextual_candidate = derive_blueprint_material_needs(composition(kinds=("video", "card")), contextual_direction)
    validate_blueprint_composition(contextual_candidate, contextual_direction, mixed_request)


def test_legacy_mixed_montage_plan_is_not_reinterpreted_by_new_material_policy():
    legacy_request = request().model_copy(update={"mode": "mixed_montage"})
    direction = storyboard()
    candidate = derive_blueprint_material_needs(composition(), direction)
    validate_blueprint_composition(candidate, direction, legacy_request)


def test_contextual_video_policy_starts_in_direction_and_scene_ids_bind_by_order():
    strict_request = request().model_copy(
        update={"mode": "mixed_montage", "material_semantics_policy": "contextual_video_v1"}
    )
    incomplete = storyboard()
    with pytest.raises(ValueError, match="direction_contextual_video_missing"):
        validate_direction(incomplete, strict_request)

    complete = storyboard()
    requirement = complete.beats[0].visual_blueprint.demonstration.indispensable_materials[0]
    requirement.kind = "video"
    requirement.source_class = "licensed_stock"
    requirement.procedural_allowed = False
    validate_direction(complete, strict_request)

    candidate = composition(kinds=("video", "card"))
    candidate.scenes[0].id = "provider-invented-scene-id"
    repairs = bind_storyboard_scene_ids(candidate, complete)
    assert candidate.scenes[0].id == complete.beats[0].id
    assert repairs[0]["classification"] == "bounded_normalization"


def test_shape_does_not_replace_indispensable_image_without_explicit_permission():
    with pytest.raises(ValueError, match="indispensable_material_target_missing"):
        derive_blueprint_material_needs(composition(kinds=("shape", "card")), storyboard())


def test_format_transformation_requires_same_real_material_in_each_state():
    invalid = composition(kinds=("image", "image"), assets=("one", "two"), family="format_transformation")
    with pytest.raises(ValueError, match="shared_material"):
        lower_compositions(invalid, 640, 640)
    valid = composition(kinds=("image", "image"), assets=("same", "same"), family="format_transformation")
    assert lower_compositions(valid, 640, 640).scenes[0].elements[1].start_frame == 15


def test_format_transformation_accepts_pending_states_bound_to_one_requirement():
    pending = composition(
        kinds=("video", "video"),
        assets=(None, None),
        family="format_transformation",
    )
    scene = pending.scenes[0]
    scene.compositions[0].continuity_key = scene.elements[0].id
    for index, element in enumerate(scene.elements):
        scene.material_needs.append(
            EditorialMaterialV2.model_validate(
                {
                    "id": f"need-{index}",
                    "targetId": element.id,
                    "kind": "video",
                    "query": "same message on devices",
                    "purpose": "Preserve the same source",
                    "sourceClass": "licensed_stock",
                    "blueprintRequirementId": "source-message",
                }
            )
        )

    lowered = lower_compositions(pending, 640, 640)

    states = [element for element in lowered.scenes[0].elements if element.kind == "video"]
    labels = [element for element in lowered.scenes[0].elements if element.id.startswith("format-label-")]
    assert [element.asset_id for element in states] == [None, None]
    assert states[1].start_frame == 15
    assert [element.text for element in labels] == ["VERTICAL", "QUADRADO"]
    assert all(element.text_role == "support" for element in labels)


def test_format_transformation_changes_viewport_and_retires_previous_state():
    candidate = composition(
        kinds=("image", "image", "image"),
        assets=("shared", "shared", "shared"),
        family="format_transformation",
    )
    lowered = lower_compositions(candidate, 640, 640).scenes[0]
    first, second, third = [element for element in lowered.elements if element.kind == "image"]
    labels = [element for element in lowered.elements if element.id.startswith("format-label-")]
    assert [element.asset_id for element in (first, second, third)] == ["shared"] * 3
    assert [round(element.width / element.height, 2) for element in (first, second, third)] == [0.64, 1.0, 1.68]
    assert [element.start_frame for element in (first, second, third)] == [0, 15, 30]
    assert first.duration_frames == second.duration_frames == 16
    assert first.object_fit == second.object_fit == third.object_fit == "cover"
    assert first.animations[0].keyframes[-1].value == 0
    assert {animation.property for animation in first.animations} == {
        "opacity",
        "scale_x",
        "scale_y",
    }
    assert all(
        {animation.property for animation in element.animations}
        == {"opacity", "position_x", "position_y", "scale_x", "scale_y"}
        for element in (second, third)
    )
    assert second.animations[3].keyframes[0].value == pytest.approx(first.width / second.width)
    assert third.animations[4].keyframes[0].value == pytest.approx(second.height / third.height)
    assert [element.text for element in labels] == ["VERTICAL", "QUADRADO", "HORIZONTAL"]
    assert all(element.border_width > 0 for element in (first, second, third))


def test_format_transformation_reserves_measured_title_band():
    candidate = composition(
        kinds=("card", "card", "card"),
        assets=(None, None, None),
        family="format_transformation",
    )
    scene = candidate.scenes[0]
    for element in scene.elements:
        element.content_identity = "shared-message"
    scene.compositions[0].continuity_key = "shared-message"
    scene.elements.append(
        EditorialElementV2(
            id="scene-title",
            kind="text",
            purpose="Explain the transformation",
            text="Distribuir é adaptar a mensagem a cada formato.",
            visual_role="text",
            x=55,
            y=70,
            width=610,
            height=225,
            duration_frames=90,
        )
    )

    lowered = lower_compositions(candidate, 720, 1280).scenes[0]
    states = [element for element in lowered.elements if element.id.startswith("element-")]
    labels = [element for element in lowered.elements if element.id.startswith("format-label-")]

    title_bottom = 70 + 225
    assert all(element.y >= title_bottom for element in states)
    assert all(label.y + label.height <= 1280 - 0.07 * 720 for label in labels)


def test_procedural_format_transformation_requires_explicit_shared_content_identity():
    candidate = composition(
        kinds=("card", "card"),
        family="format_transformation",
    )
    scene = candidate.scenes[0]
    scene.compositions[0].continuity_key = scene.elements[0].id

    with pytest.raises(ValueError, match="shared_material"):
        lower_compositions(candidate, 640, 640)

    for element in scene.elements:
        element.content_identity = "shared-message"
    scene.compositions[0].continuity_key = "shared-message"

    lowered = lower_compositions(candidate, 640, 640).scenes[0]
    states = [element for element in lowered.elements if element.kind == "card"]
    assert [element.content_identity for element in states] == ["shared-message"] * 2
    assert states[1].animations[3].keyframes[0].value == pytest.approx(states[0].width / states[1].width)


def test_format_transformation_compiles_viewport_morph_tracks_in_the_production_graph():
    from test_scene_compiler_v2 import document

    from app.services.studios.scene_compiler import compile_scenes

    candidate = composition(
        kinds=("card", "card", "card"),
        assets=(None, None, None),
        family="format_transformation",
    )
    scene = candidate.scenes[0]
    for element in scene.elements:
        element.content_identity = "shared-message"
    scene.compositions[0].continuity_key = "shared-message"

    _, graph, _, _ = compile_scenes(document(), candidate, "user", "format-morph-plan")

    properties = {track.property for track in graph.tracks}
    assert {"position_x", "position_y", "scale_x", "scale_y"} <= properties


def test_format_transformation_does_not_fabricate_shared_content_from_distinct_footage():
    from app.services.studios.editorial_components import repair_raw_composition_contracts

    raw = {
        "scenes": [
            {
                "id": "formats",
                "durationFrames": 72,
                "background": "#101c29",
                "elements": [
                    {"id": "phone", "kind": "video", "purpose": "Contexto mobile", "zIndex": 1},
                    {"id": "laptop", "kind": "video", "purpose": "Contexto desktop", "zIndex": 2},
                    {
                        "id": "message",
                        "kind": "text",
                        "text": "Distribuir é adaptar a mensagem a cada formato.",
                        "conciseText": "ADAPTAR A MENSAGEM",
                        "purpose": "Explicar a transformação",
                        "color": "#ffffff",
                        "textSpans": [{"color": "#60aaff"}],
                        "zIndex": 10,
                    },
                ],
                "materialNeeds": [
                    {
                        "id": "phone-stock",
                        "targetId": "phone",
                        "field": "asset",
                        "kind": "video",
                        "blueprintRequirementId": "phone-context",
                    },
                    {
                        "id": "laptop-stock",
                        "targetId": "laptop",
                        "field": "asset",
                        "kind": "video",
                        "blueprintRequirementId": "laptop-context",
                    },
                ],
                "compositions": [
                    {
                        "id": "adapt",
                        "family": "format_transformation",
                        "targetIds": ["phone", "laptop"],
                        "continuityKey": "shared-message",
                        "viewportFormats": ["portrait", "landscape"],
                        "expectedResult": "A mesma mensagem muda de formato.",
                    }
                ],
                "shotPlan": [],
            }
        ]
    }

    repairs = repair_raw_composition_contracts(raw)

    scene = raw["scenes"][0]
    composition = scene["compositions"][0]
    assert composition["targetIds"] == ["phone", "laptop"]
    assert {element["id"] for element in scene["elements"] if element["kind"] == "video"} == {
        "phone",
        "laptop",
    }
    assert not any(
        item["reason"] == "format_transformation_context_media_separated_from_shared_content" for item in repairs
    )


def test_annotated_material_accepts_registered_graphic_overlay():
    candidate = composition(
        kinds=("video", "shape"),
        assets=("footage", None),
        family="annotated_material",
    )
    lowered = lower_compositions(candidate, 640, 640)
    media, overlay = lowered.scenes[0].elements[:2]
    group = next(element for element in lowered.scenes[0].elements if element.kind == "group")
    assert media.kind == "video"
    assert overlay.kind == "shape"
    assert media.parent_id == overlay.parent_id == group.id
    assert {animation.property for animation in group.animations} == {"scale_x", "scale_y"}
    assert media.animations == []
    assert media.x - 1e-6 <= overlay.x <= media.x + media.width - overlay.width + 1e-6
    assert media.y - 1e-6 <= overlay.y <= media.y + media.height - overlay.height + 1e-6
    assert not any(element.connector_from_id for element in lowered.scenes[0].elements[2:])


def test_attention_annotation_requires_an_observed_region_before_execution():
    direction = storyboard()
    candidate = composition(
        kinds=("video", "shape"),
        assets=("inspected-footage", None),
        family="annotated_material",
    )
    scene = candidate.scenes[0]
    scene.elements[1].purpose = "Destacar a atenção de uma pessoa específica"
    direction.beats[0].visual_blueprint.demonstration.indispensable_materials = []

    blocked = production_gates(direction, request(), candidate)

    assert blocked["techniqueSuitability"]["status"] == "failed"
    assert blocked["techniqueSuitability"]["nextAction"] == "select_route"
    assert any(
        item.get("reason") == "semantic_annotation_requires_observed_region"
        for item in blocked["techniqueSuitability"]["evidence"]
    )

    scene.elements[0].region_of_interest = {
        "x": 0.25,
        "y": 0.2,
        "width": 0.35,
        "height": 0.45,
        "purpose": "Região de pessoa observada nos frames inspecionados",
    }
    accepted = production_gates(direction, request(), candidate)
    assert accepted["techniqueSuitability"]["status"] == "passed"


def test_primitive_shape_cannot_claim_to_be_a_recognizable_icon():
    direction = storyboard()
    direction.beats[0].visual_blueprint.demonstration.indispensable_materials = []
    candidate = composition(kinds=("shape",), family="focus")
    candidate.scenes[0].elements[0].purpose = "Ícone de lâmpada que representa uma ideia"

    gates = production_gates(direction, request(), candidate)

    assert gates["techniqueSuitability"]["status"] == "failed"
    assert gates["techniqueSuitability"]["evidence"][0]["reason"] == (
        "recognizable_symbol_represented_by_primitive_shape"
    )


def test_interface_uses_one_viewport_with_temporal_states_not_spatial_grid():
    candidate = composition(kinds=("card", "card", "card"), assets=(None, None, None), family="demonstrative_interface")
    first, second, third = lower_compositions(candidate, 640, 640).scenes[0].elements
    assert first.x == second.x == third.x
    assert first.y == second.y == third.y
    assert [element.start_frame for element in (first, second, third)] == [0, 15, 30]
    assert first.animations[0].keyframes[-1].value == 0
    assert third.animations[0].keyframes[-1].value == 1


def test_interface_state_change_reaches_the_executable_graph():
    from test_scene_compiler_v2 import document

    from app.services.studios.scene_compiler import compile_scenes

    candidate = composition(kinds=("card", "card"), family="demonstrative_interface")
    candidate.scenes[0].compositions[0].interface_events = ["open", "scroll"]
    draft, graph, _, manifest = compile_scenes(document(), candidate, "test", "interface-test")
    layers = [layer for layer in draft.composition.pages[0].layers if layer.name.startswith("element-")]
    assert len(layers) == 2
    assert layers[0].x == layers[1].x
    assert graph.tracks
    assert manifest["hashes"]["executableComposition"]


def test_material_suitability_is_refreshed_only_after_mandatory_asset_binding():
    direction = storyboard()
    candidate = derive_blueprint_material_needs(composition(), direction)
    assert production_gates(direction, request(), candidate)["techniqueSuitability"]["status"] == "inconclusive"
    candidate.scenes[0].elements[0].asset_id = "resolved-asset"
    gates = production_gates(direction, request(), candidate)
    assert gates["techniqueSuitability"]["status"] == "passed"
    assert gates["sceneStages"][0]["stage"] == "executable"


def test_preferred_material_does_not_become_a_mandatory_acquisition():
    direction = storyboard()
    direction.beats[0].visual_blueprint.demonstration.indispensable_materials[0].requirement_class = "preferred"
    candidate = derive_blueprint_material_needs(composition(), direction)
    assert candidate.scenes[0].material_needs[0].required is False
    assert production_gates(direction, request(), candidate)["techniqueSuitability"]["status"] == "passed"
    validate_blueprint_composition(candidate, direction, request())


def test_cinematic_shot_must_bind_its_material_and_executable_interval():
    from app.domain.studios.cinematic_direction import CinematicArtDirectionV1, CinematicShotIntentV1

    direction = storyboard()
    direction.art_direction = CinematicArtDirectionV1(
        visual_system="Material real com anotações",
        palette=["#112233"],
        typography="Legível",
        contrast_strategy="Sujeito em destaque",
        footage_treatment="Preservar o enquadramento",
        graphics_relationship="Anotar sem encobrir",
        continuity_rules=["Manter o objeto reconhecível"],
    )
    shot = CinematicShotIntentV1(
        id="shot-1",
        function="demonstrate",
        subject="Conteúdo original",
        observable_action="Mostrar o mesmo conteúdo",
        shot_scale="medium",
        angle="eye_level",
        region_of_interest="Conteúdo",
        attention_start="Objeto",
        attention_end="Anotação",
        lighting={
            "quality": "available",
            "direction": "motivated",
            "contrast": "medium",
            "temperatureRelationship": "Neutra",
            "subjectSeparation": "Fundo discreto",
            "executionMode": "select_existing_footage",
        },
        cut_motivation="Mostrar consequência",
        material_requirement_ids=["source-content"],
        execution_component_ids=["evidence"],
        verification=["Conteúdo visível"],
    )
    direction.beats[0].visual_blueprint.shot_sequence = [shot]
    candidate = derive_blueprint_material_needs(composition(assets=("accepted-asset", None)), direction)
    candidate.art_direction = direction.art_direction
    candidate.scenes[0].shot_plan = [
        shot.model_copy(update={"start_frame": 0, "end_frame_exclusive": 90, "target_element_ids": ["element-0"]})
    ]
    cinematic_request = request().model_copy(update={"cinematic_direction_policy": "mixed_motion_v1"})
    validate_blueprint_composition(candidate, direction, cinematic_request)
    candidate.scenes[0].shot_plan[0].target_element_ids = ["element-1"]
    with pytest.raises(ValueError, match="shot_material_unbound"):
        validate_blueprint_composition(candidate, direction, cinematic_request)


def test_visual_findings_choose_typed_correction_and_render_evidence_controls_gate():
    assert correction_action({"code": "material_irrelevant"}) == "resolve_material"
    assert correction_action({"code": "inspection_coverage_incomplete"}) == "inspect_interval"
    failed = observed_result_gate(
        {
            "renderChecksum": "a" * 64,
            "findings": [{"code": "material_irrelevant", "severity": "correction"}],
        },
        "a" * 64,
    )
    assert failed["status"] == "failed" and failed["nextAction"] == "resolve_material"
    passed = observed_result_gate(
        {
            "renderChecksum": "a" * 64,
            "findings": [],
            "renderedEvidence": [{"frame": 20}],
            "coverage": {"frameSampleComplete": True},
            "actionVerification": {"status": "observed", "evidence": [{"sceneId": "formats"}]},
        },
        "a" * 64,
    )
    assert passed["status"] == "passed"
    semantic_false_positive = observed_result_gate(
        {
            "renderChecksum": "a" * 64,
            "findings": [],
            "renderedEvidence": [{"frame": 20}],
            "coverage": {"frameSampleComplete": True},
            "actionVerification": {"status": "observed", "evidence": [{"pixelDifference": 0.2}]},
            "semanticVerification": {
                "required": True,
                "status": "inconclusive",
                "evidence": [],
            },
        },
        "a" * 64,
    )
    assert semantic_false_positive["status"] == "inconclusive"


def test_canonical_content_requires_real_parts_in_every_derived_format():
    payload = composition(kinds=("group", "group"), family="format_transformation").model_dump(
        mode="json", by_alias=True
    )
    payload["semanticVerificationPolicy"] = "canonical_demonstration_v1"
    payload["contentReferences"] = [
        {
            "id": "campaign-piece",
            "purpose": "Conteúdo reconhecível",
            "parts": [
                {"id": "photo", "role": "primary_media", "assetId": "asset-photo"},
                {"id": "headline", "role": "title", "text": "Uma ideia clara"},
                {"id": "brand", "role": "identity", "text": "RES CAFÉ"},
            ],
        }
    ]
    scene = payload["scenes"][0]
    scene["contentReferenceIds"] = ["campaign-piece"]
    scene["elements"][0]["contentReferenceId"] = "campaign-piece"
    scene["elements"][1]["contentReferenceId"] = "campaign-piece"
    scene["elements"].extend(
        [
            {
                "id": f"{state}-{part}",
                "kind": "image" if part == "photo" else "text",
                "purpose": "Parte canônica",
                "text": "Uma ideia clara" if part == "headline" else "RES CAFÉ" if part == "brand" else "",
                "assetId": "asset-photo" if part == "photo" else None,
                "parentId": state,
                "contentReferenceId": "campaign-piece",
                "contentPartId": part,
                "width": 180,
                "height": 120,
                "durationFrames": 90,
            }
            for state in ("element-0", "element-1")
            for part in ("photo", "headline", "brand")
        ]
    )
    scene["compositions"][0].update(continuityKey="campaign-piece", viewportFormats=["portrait", "square"])
    scene["semanticAssertions"] = [
        {
            "id": "same-piece-two-formats",
            "kind": "format_adaptation",
            "objectId": "campaign-piece",
            "initialState": "Peça vertical",
            "event": "Layout se reorganiza",
            "finalState": "Peça quadrada",
            "startFrame": 0,
            "endFrameExclusive": 90,
            "targetIds": ["element-0", "element-1"],
            "requiredPartIds": ["photo", "headline", "brand"],
            "evidenceRequired": "temporal_sequence",
        }
    ]
    candidate = ContextualPlanRequestV2.model_validate(payload)
    lowered = lower_compositions(candidate, 640, 960)
    assert {element.content_reference_id for element in lowered.scenes[0].elements[:2]} == {"campaign-piece"}
    scene = lowered.scenes[0]
    portrait, square = scene.elements[:2]
    assert portrait.width / portrait.height == pytest.approx(0.64, rel=0.01)
    assert square.width / square.height == pytest.approx(1.0, rel=0.01)
    portrait_photo = next(element for element in scene.elements if element.id == "element-0-photo")
    square_photo = next(element for element in scene.elements if element.id == "element-1-photo")
    portrait_title = next(element for element in scene.elements if element.id == "element-0-headline")
    square_title = next(element for element in scene.elements if element.id == "element-1-headline")
    assert portrait_photo.object_fit == square_photo.object_fit == "cover"
    assert not any(element.id.startswith("format-label-") for element in scene.elements)
    assert {animation.property for animation in square.animations} == {"opacity"}
    for child in (element for element in scene.elements if element.parent_id == square.id):
        child_tracks = {animation.property: animation for animation in child.animations}
        assert {"position_x", "position_y", "scale_x", "scale_y"} == set(child_tracks)
        assert child_tracks["scale_x"].keyframes[0].value == pytest.approx(
            child_tracks["scale_y"].keyframes[0].value
        )
    assert portrait_photo.start_frame == portrait.start_frame
    assert square_photo.start_frame == square.start_frame
    assert portrait_title.width != square_title.width or portrait_title.height != square_title.height
    for state in (portrait, square):
        for child in (element for element in scene.elements if element.parent_id == state.id):
            assert child.x >= 0 and child.y >= 0
            assert child.x + child.width <= state.width + 1e-6
            assert child.y + child.height <= state.height + 1e-6
    # Revalidating the lowered contract catches child/parent timing drift that
    # a static layout-only fixture would miss.
    ContextualPlanRequestV2.model_validate(lowered.model_dump(mode="json", by_alias=True))


def test_canonical_content_rejects_empty_derived_state():
    payload = composition(kinds=("group", "group"), family="format_transformation").model_dump(
        mode="json", by_alias=True
    )
    payload["semanticVerificationPolicy"] = "canonical_demonstration_v1"
    payload["contentReferences"] = [
        {
            "id": "piece",
            "purpose": "Peça",
            "parts": [
                {"id": "photo", "role": "primary_media", "assetId": "asset-photo"},
                {"id": "title", "role": "title", "text": "Título"},
            ],
        }
    ]
    scene = payload["scenes"][0]
    scene["contentReferenceIds"] = ["piece"]
    for element in scene["elements"]:
        element["contentReferenceId"] = "piece"
    scene["semanticAssertions"] = [
        {
            "id": "adapt",
            "kind": "format_adaptation",
            "objectId": "piece",
            "initialState": "vertical",
            "event": "adapta",
            "finalState": "quadrado",
            "startFrame": 0,
            "endFrameExclusive": 90,
            "targetIds": ["element-0", "element-1"],
            "requiredPartIds": ["photo", "title"],
            "evidenceRequired": "temporal_sequence",
        }
    ]
    scene["compositions"][0].update(continuityKey="piece", viewportFormats=["portrait", "square"])
    candidate = ContextualPlanRequestV2.model_validate(payload)
    with pytest.raises(ValueError, match="format_transformation_requires_shared_material"):
        lower_compositions(candidate, 640, 960)


def test_canonical_content_rejects_asset_or_text_swapped_behind_stable_ids():
    payload = composition(kinds=("group", "group"), family="format_transformation").model_dump(
        mode="json", by_alias=True
    )
    payload["semanticVerificationPolicy"] = "canonical_demonstration_v1"
    payload["contentReferences"] = [
        {
            "id": "piece",
            "purpose": "Peça",
            "parts": [
                {"id": "photo", "role": "primary_media", "assetId": "asset-original"},
                {"id": "title", "role": "title", "text": "Título original"},
            ],
        }
    ]
    scene = payload["scenes"][0]
    scene["contentReferenceIds"] = ["piece"]
    for element in scene["elements"]:
        element["contentReferenceId"] = "piece"
    scene["elements"].extend(
        [
            {
                "id": "swapped-photo",
                "kind": "image",
                "purpose": "troca indevida",
                "assetId": "asset-different",
                "parentId": "element-0",
                "contentReferenceId": "piece",
                "contentPartId": "photo",
                "width": 100,
                "height": 100,
                "durationFrames": 90,
            },
            {
                "id": "swapped-title",
                "kind": "text",
                "purpose": "troca indevida",
                "text": "Outro título",
                "parentId": "element-1",
                "contentReferenceId": "piece",
                "contentPartId": "title",
                "width": 100,
                "height": 100,
                "durationFrames": 90,
            },
        ]
    )
    scene["semanticAssertions"] = [
        {
            "id": "adapt",
            "kind": "format_adaptation",
            "objectId": "piece",
            "initialState": "vertical",
            "event": "adapta",
            "finalState": "quadrado",
            "startFrame": 0,
            "endFrameExclusive": 90,
            "targetIds": ["element-0", "element-1"],
            "requiredPartIds": ["photo", "title"],
            "evidenceRequired": "temporal_sequence",
        }
    ]

    with pytest.raises(ValueError, match="content_part_asset_binding_mismatch"):
        ContextualPlanRequestV2.model_validate(payload)


def test_human_render_examples_are_tenant_scoped_deduplicated_and_not_training(project):
    from sqlalchemy import select

    from app.database import SessionLocal
    from app.models import KnowledgeDocument
    from app.services.studios.editing_repertoire import store_render_example

    receipt = {
        "schemaVersion": "studio.visual-human-review.v1",
        "renderChecksum": "a" * 64,
        "status": "requires_correction",
        "reviewedBy": "reviewer",
    }
    state = {
        "id": "production",
        "documentId": project["document"],
        "documentRevision": 1,
        "artifacts": {
            "plan": {
                "direction": {
                    "scenes": [
                        {
                            "techniqueIds": ["annotated_material"],
                            "compositions": [{"family": "annotated_material"}],
                        }
                    ]
                }
            }
        },
    }
    with SessionLocal() as db:
        first = store_render_example(db, project["workspace"], state, receipt)
        second = store_render_example(db, project["workspace"], state, receipt)
        assert first.id == second.id
        records = db.scalars(
            select(KnowledgeDocument).where(
                KnowledgeDocument.workspace_id == project["workspace"],
                KnowledgeDocument.source_type == "editing-example",
            )
        ).all()
        assert len(records) == 1
        assert records[0].document_metadata["decision"] == "rejected"
        assert records[0].document_metadata["evaluatorType"] == "human"
        assert records[0].document_metadata["trainingApplied"] is False
def test_visual_correction_rejects_weakened_proof_and_visual_noop():
    from copy import deepcopy

    from app.services.studios.production_audit import visual_correction_effect

    original = {
        "artDirection": {"palette": ["#101820", "#ffffff"]},
        "frameRate": {"numerator": 30, "denominator": 1},
        "scenes": [{
            "id": "scene", "durationFrames": 90, "background": "#101820",
            "elements": [
                {"id": "background", "kind": "shape", "zIndex": 0, "fill": "#101820"},
                {"id": "hero", "kind": "text", "zIndex": 2, "text": "IDEIA", "color": "#ffffff"},
            ],
            "semanticAssertions": [{
                "id": "claim", "kind": "content_present", "objectId": "piece",
                "targetIds": ["hero"], "requiredPartIds": ["title"],
                "evidenceRequired": "rendered_pixels_and_geometry", "essential": True,
            }],
        }],
    }
    weakened = deepcopy(original)
    weakened["scenes"][0]["semanticAssertions"][0]["requiredPartIds"] = []
    assert visual_correction_effect(original, weakened, "recompile_composition")["reason"] == (
        "production_visual_correction_weakened_verification"
    )
    noop = deepcopy(original)
    noop["scenes"][0]["elements"][0]["zIndex"] = 1
    noop["scenes"][0]["elements"][1]["purpose"] = "Bigger emotional impact"
    assert visual_correction_effect(original, noop, "recompile_composition")["reason"] == (
        "production_visual_correction_no_render_delta"
    )
    changed = deepcopy(original)
    changed["scenes"][0]["elements"][1]["color"] = "#ffcc00"
    assert visual_correction_effect(original, changed, "recompile_composition")["status"] == "accepted"
