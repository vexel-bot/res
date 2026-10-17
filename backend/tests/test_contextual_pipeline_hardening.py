import json

import httpx
import pytest
from test_scene_compiler_v2 import direction, document

from app.domain.studios.material_inspection import (
    MaterialInspectionRequestV1,
    MaterialInspectionResultV1,
    inspect_verdict,
)
from app.providers.studios.gemini_editing import GeminiEditingProvider
from app.services.studios.material_ranking import rank_candidates
from app.services.studios.scene_compiler import compile_scenes


def test_gemini_native_schema_is_sent():
    schema = {"type": "object", "properties": {"answer": {"type": "string"}}, "required": ["answer"]}

    def respond(request):
        assert json.loads(request.content)["generationConfig"]["responseJsonSchema"] == schema
        return httpx.Response(200, json={"candidates": []})

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        GeminiEditingProvider("test", client).plan("pinned", {"outputSchema": schema}, [])


def test_gemini_referenced_schema_stays_in_context_for_local_validation():
    schema = {
        "$defs": {"answer": {"type": "object", "properties": {"value": {"type": "string"}}}},
        "$ref": "#/$defs/answer",
    }

    def respond(request):
        body = json.loads(request.content)
        assert "responseJsonSchema" not in body["generationConfig"]
        supplied = json.loads(body["contents"][0]["parts"][0]["text"])
        assert supplied["outputSchema"] == schema
        return httpx.Response(200, json={"candidates": []})

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        GeminiEditingProvider("test", client).plan("pinned", {"outputSchema": schema}, [])


def test_visual_only_keeps_script_without_requesting_voice():
    request = direction()
    request.scenes[0].narration = "Distribuição não garante sucesso."
    request.intent.locked_facts = [request.scenes[0].narration]
    request.execution_scope = "visual_only"
    _, _, _, manifest = compile_scenes(document(), request, "user", "plan")
    assert not manifest["missingMaterials"]
    request.execution_scope = "audiovisual"
    _, _, _, manifest = compile_scenes(document(), request, "user", "plan")
    assert manifest["missingMaterials"][0]["reason"] == "narration_audio_required"


def test_unresolved_visual_elements_become_exact_material_requests():
    from app.services.studios.contextual_editing_v2 import ensure_visual_material_needs

    request = direction()
    scene = request.scenes[0]
    media = scene.elements[0].model_copy(
        deep=True,
        update={"id": "specific-media", "kind": "image", "asset_id": None, "purpose": "Mostrar o público"},
    )
    scene.elements = [media]
    scene.material_needs = []

    ensure_visual_material_needs(request)
    ensure_visual_material_needs(request)

    assert len(scene.material_needs) == 1
    assert scene.material_needs[0].target_id == "specific-media"
    assert scene.material_needs[0].query == "Mostrar o público"


def test_evidence_without_annotation_repairs_to_auditable_focus():
    from app.domain.studios.contextual_editing_v2 import EditorialCompositionV1
    from app.services.studios.editorial_components import repair_composition_contracts

    request = direction()
    scene = request.scenes[0]
    scene.elements[0] = scene.elements[0].model_copy(update={"kind": "image", "text": ""})
    scene.elements.append(
        scene.elements[0].model_copy(update={"id": "ambient-shape", "kind": "shape", "purpose": "Fundo"})
    )
    scene.compositions = [
        EditorialCompositionV1(
            id="malformed-evidence",
            family="evidence",
            target_ids=[scene.elements[0].id, "ambient-shape"],
            purpose="Destacar a mídia",
            expected_result="Foco identificável",
        )
    ]

    repairs = repair_composition_contracts(request)

    assert repairs[0]["reason"] == "evidence_without_annotation"
    assert scene.compositions[0].family == "focus"
    assert scene.compositions[0].target_ids == [scene.elements[0].id]


def test_procedural_shape_can_be_the_subject_of_an_evidence_composition():
    from app.domain.studios.contextual_editing_v2 import EditorialCompositionV1
    from app.services.studios.editorial_components import lower_compositions

    request = direction()
    scene = request.scenes[0]
    subject = scene.elements[0].model_copy(
        update={"id": "idea-core", "kind": "shape", "text": "", "visual_role": "hero"}
    )
    annotation = scene.elements[0].model_copy(
        update={"id": "idea-copy", "kind": "text", "text": "Uma ideia", "visual_role": "text"}
    )
    scene.elements = [subject, annotation]
    scene.compositions = [
        EditorialCompositionV1(
            id="idea-evidence",
            family="evidence",
            target_ids=[subject.id, annotation.id],
            purpose="Associar símbolo e explicação",
            expected_result="Símbolo e texto relacionados",
        )
    ]

    lowered = lower_compositions(request, 1080, 1080)

    assert lowered.scenes[0].elements[0].kind == "shape"
    assert lowered.scenes[0].elements[0].width == subject.width
    assert lowered.scenes[0].elements[0].height == subject.height
    assert any(element.connector_from_id == "idea-core" for element in lowered.scenes[0].elements)


def test_comparison_preserves_media_aspect_and_uses_contain():
    from app.domain.studios.contextual_editing_v2 import EditorialCompositionV1
    from app.services.studios.editorial_components import lower_compositions

    request = direction()
    scene = request.scenes[0]
    video = scene.elements[0].model_copy(
        update={
            "id": "generated-video",
            "kind": "video",
            "text": "",
            "width": 880,
            "height": 520,
            "visual_role": "hero",
        }
    )
    person = scene.elements[0].model_copy(
        update={
            "id": "person",
            "kind": "shape",
            "text": "",
            "width": 110,
            "height": 170,
            "visual_role": "support",
        }
    )
    scene.elements = [video, person]
    scene.compositions = [
        EditorialCompositionV1(
            id="connection-comparison",
            family="comparison",
            target_ids=[video.id, person.id],
            purpose="Relacionar caminho e destino",
            expected_result="Vídeo e pessoa permanecem reconhecíveis",
        )
    ]

    lowered = lower_compositions(request, 1080, 1080)
    result_video, result_person = lowered.scenes[0].elements

    assert result_video.width / result_video.height == pytest.approx(880 / 520)
    assert result_video.object_fit == "contain"
    assert result_person.width == 110
    assert result_person.height == 170


def test_focus_animates_without_turning_a_small_primitive_into_a_full_screen_shape():
    from app.domain.studios.contextual_editing_v2 import EditorialCompositionV1
    from app.services.studios.editorial_components import lower_compositions

    request = direction()
    target = request.scenes[0].elements[0]
    target.kind = "shape"
    target.text = ""
    target.width = 160
    target.height = 160
    request.scenes[0].compositions = [
        EditorialCompositionV1(
            id="focus-target",
            family="focus",
            target_ids=[target.id],
            purpose="Dirigir atenção",
            expected_result="Alvo em evidência sem distorção",
        )
    ]

    lowered = lower_compositions(request, 1080, 1080)
    result = lowered.scenes[0].elements[0]

    assert (result.width, result.height) == (160, 160)
    assert result.x == pytest.approx(460)
    assert result.y == pytest.approx(460)


def test_repetition_distributes_small_instances_across_the_allocated_cells():
    from app.domain.studios.contextual_editing_v2 import EditorialCompositionV1
    from app.services.studios.editorial_components import lower_compositions

    request = direction()
    target = request.scenes[0].elements[0]
    target.kind = "shape"
    target.text = ""
    target.width = 80
    target.height = 80
    request.scenes[0].compositions = [
        EditorialCompositionV1(
            id="repeat-target",
            family="repetition",
            target_ids=[target.id],
            purpose="Mostrar alcance",
            expected_result="Instâncias distribuídas",
            repeat_count=3,
        )
    ]

    result = lower_compositions(request, 1080, 1080).scenes[0].elements[0]

    assert result.repeat_count == 3
    assert result.repeat_dx > result.width * 3
    assert result.x + 2 * result.repeat_dx + result.width < 1080


def test_sequence_action_is_clamped_to_scene_interval():
    from app.domain.studios.contextual_editing_v2 import EditorialCompositionV1
    from app.services.studios.editorial_components import repair_composition_contracts

    request = direction()
    scene = request.scenes[0]
    scene.duration_frames = 30
    scene.elements = [
        scene.elements[0].model_copy(update={"id": f"step-{index}", "duration_frames": 30})
        for index in range(3)
    ]
    scene.compositions = [
        EditorialCompositionV1(
            id="slow-sequence",
            family="sequence",
            target_ids=[element.id for element in scene.elements],
            purpose="Explicar etapas",
            expected_result="Etapas visíveis em ordem",
            action_frames=18,
        )
    ]

    repairs = repair_composition_contracts(request)

    assert scene.compositions[0].action_frames == 9
    assert repairs[0]["reason"] == "action_exceeds_available_interval"


def test_raw_contract_repair_removes_duplicate_owner_and_decorative_pan_target():
    from app.domain.studios.contextual_editing_v2 import ContextualPlanRequestV2
    from app.services.studios.editorial_components import repair_raw_composition_contracts

    raw = direction().model_dump(mode="json", by_alias=True)
    scene = raw["scenes"][0]
    scene["elements"][0]["visualRole"] = "accent"
    scene["cameraCues"] = [
        {
            "mode": "pan",
            "targetId": scene["elements"][0]["id"],
            "startFrame": 0,
            "durationFrames": 20,
            "intensity": 0.05,
            "panX": 20,
            "panY": 0,
            "easingProfile": "gentle",
            "rationale": "Percorrer a composição",
        }
    ]
    first = {
        "id": "first-owner",
        "family": "focus",
        "targetIds": [scene["elements"][0]["id"]],
        "purpose": "Destacar o elemento",
        "expectedResult": "Elemento em foco",
        "actionFrames": 18,
    }
    scene["compositions"] = [first]
    scene["compositions"].append(
        {
            **first,
            "id": "second-owner",
            "targetIds": [first["targetIds"][0]],
        }
    )

    repairs = repair_raw_composition_contracts(raw)
    validated = ContextualPlanRequestV2.model_validate(raw)

    assert [item["reason"] for item in repairs] == [
        "duplicate_semantic_component_target_removed",
        "empty_semantic_component_removed",
        "decorative_camera_target_removed",
    ]
    assert len(validated.scenes[0].compositions) == 1
    assert validated.scenes[0].camera_cues[0].target_id is None
    camera_repair = next(
        repair for repair in repairs if repair["reason"] == "decorative_camera_target_removed"
    )
    assert camera_repair["classification"] == "bounded_normalization"


def test_raw_contract_repair_preserves_multi_point_path_as_polyline():
    from app.domain.studios.contextual_editing_v2 import ContextualPlanRequestV2
    from app.services.studios.editorial_components import repair_raw_composition_contracts

    raw = direction().model_dump(mode="json", by_alias=True)
    path = raw["scenes"][0]["elements"][0]
    path.update(
        kind="path",
        text="",
        pathMode="quadratic",
        points=[{"x": 0, "y": 0}, {"x": 10, "y": 10}, {"x": 20, "y": 0}, {"x": 30, "y": 10}],
    )

    repairs = repair_raw_composition_contracts(raw)
    validated = ContextualPlanRequestV2.model_validate(raw)

    assert repairs[0]["reason"] == "multi_point_quadratic_normalized_to_polyline"
    assert validated.scenes[0].elements[0].path_mode == "polyline"


def test_raw_contract_repair_binds_video_need_to_executable_video_element():
    from app.domain.studios.contextual_editing_v2 import ContextualPlanRequestV2
    from app.services.studios.editorial_components import repair_raw_composition_contracts

    raw = direction().model_dump(mode="json", by_alias=True)
    scene = raw["scenes"][0]
    target = scene["elements"][0]
    target.update(
        kind="path",
        pathMode="quadratic",
        points=[{"x": 0, "y": 0}, {"x": 10, "y": 10}, {"x": 20, "y": 0}, {"x": 30, "y": 10}],
        reveal="path",
    )
    scene["materialNeeds"] = [
        {
            "id": "generated-clip",
            "targetId": target["id"],
            "field": "asset",
            "kind": "video",
            "query": "Fluxo original conectando formatos ao público",
            "purpose": "Mostrar a conexão",
            "sourceClass": "generated_original",
            "durationSeconds": 4,
            "fallbackBehavior": "block",
        }
    ]

    repairs = repair_raw_composition_contracts(raw)
    validated = ContextualPlanRequestV2.model_validate(raw)

    assert repairs[0]["reason"] == "video_material_target_normalized_to_video_element"
    assert repairs[0]["requiresAlternative"] is False
    assert validated.scenes[0].elements[0].kind == "video"
    assert validated.scenes[0].elements[0].source_audio == "mute"


def test_raw_contract_repair_normalizes_inactive_reveal_and_radius_bounds():
    from app.domain.studios.contextual_editing_v2 import ContextualPlanRequestV2
    from app.services.studios.editorial_components import repair_raw_composition_contracts

    raw = direction().model_dump(mode="json", by_alias=True)
    raw["scenes"][0]["elements"][0].update(
        reveal="none",
        revealFrames=0,
        radius=540,
        color="#ABC",
        motionCues=[
            {
                "kind": "deliberate_hold",
                "profile": "gentle",
                "durationFrames": 2,
                "rationale": "Pausa editorial",
            }
        ],
    )
    raw["scenes"][0]["cameraCues"] = [
        {
            "mode": "static",
            "durationFrames": 2,
            "easingProfile": "emphasis",
            "rationale": "Quadro estável",
        }
    ]

    repairs = repair_raw_composition_contracts(raw)
    validated = ContextualPlanRequestV2.model_validate(raw)

    assert validated.scenes[0].elements[0].reveal_frames == 1
    assert validated.scenes[0].elements[0].radius == 512
    assert validated.scenes[0].elements[0].color == "#AABBCC"
    assert validated.scenes[0].elements[0].motion_cues[0].profile == "deliberate_hold"
    assert validated.scenes[0].camera_cues[0].easing_profile == "standard"
    relevant = [
        repair
        for repair in repairs
        if repair["reason"]
        in {
            "inactive_reveal_duration_normalized",
            "radius_clamped_to_contract_limit",
            "short_hex_color_expanded",
            "camera_easing_profile_normalized",
            "deliberate_hold_profile_normalized",
        }
    ]
    assert {repair["reason"] for repair in relevant} == {
        "inactive_reveal_duration_normalized",
        "radius_clamped_to_contract_limit",
        "short_hex_color_expanded",
        "camera_easing_profile_normalized",
        "deliberate_hold_profile_normalized",
    }
    assert all(repair["classification"] == "bounded_normalization" for repair in relevant)


def test_raw_contract_repair_preserves_keyword_and_motion_intent_without_paid_replan():
    from app.domain.studios.contextual_editing_v2 import ContextualPlanRequestV2
    from app.services.studios.editorial_components import repair_raw_composition_contracts

    raw = direction().model_dump(mode="json", by_alias=True)
    scene = raw["scenes"][0]
    scene["narration"] = "Mas distribuir não garante atenção."
    scene["keywordCues"] = [
        {
            "id": "attention",
            "text": "não garante atenção",
            "sourceExcerpt": "Mas distribuir não garante atenção.",
            "purpose": "Preservar a ressalva",
            "startFrame": 1,
            "durationFrames": 12,
        }
    ]
    scene["elements"][0]["motionCues"] = [
        {
            "kind": "entrance",
            "profile": "deliberate_hold",
            "durationFrames": 12,
            "rationale": "Entrada seguida de pausa",
        }
    ]

    repairs = repair_raw_composition_contracts(raw)
    validated = ContextualPlanRequestV2.model_validate(raw)

    assert validated.scenes[0].keyword_cues[0].source_excerpt == "não garante atenção"
    assert validated.scenes[0].elements[0].motion_cues[0].profile == "standard"
    assert {repair["reason"] for repair in repairs} >= {
        "standalone_keyword_source_narrowed",
        "non_hold_profile_normalized",
    }
    assert all(repair["classification"] == "bounded_normalization" for repair in repairs)


def test_raw_contract_repair_clamps_spans_and_removes_unbound_keyword_without_replan():
    from app.domain.studios.contextual_editing_v2 import ContextualPlanRequestV2
    from app.services.studios.editorial_components import repair_raw_composition_contracts

    raw = direction(text="não chega sozinha").model_dump(mode="json", by_alias=True)
    scene = raw["scenes"][0]
    scene["narration"] = "Uma boa ideia não chega sozinha às pessoas."
    scene["elements"][0]["textSpans"] = [
        {
            "id": "negative",
            "start": 0,
            "end": 999,
            "purpose": "Destacar a negação",
        }
    ]
    scene["keywordCues"] = [
        {
            "id": "bound",
            "text": "não chega sozinha",
            "sourceExcerpt": "texto aproximado inventado",
            "purpose": "Preservar a negação",
            "startFrame": scene["durationFrames"] - 4,
            "durationFrames": 12,
        },
        {
            "id": "unbound",
            "text": "viraliza",
            "sourceExcerpt": "viraliza",
            "purpose": "Destaque sem origem",
            "startFrame": 14,
            "durationFrames": 12,
        },
    ]

    repairs = repair_raw_composition_contracts(raw)
    validated = ContextualPlanRequestV2.model_validate(raw)

    element = validated.scenes[0].elements[0]
    assert element.text_spans[0].end == len(element.text)
    assert [cue.id for cue in validated.scenes[0].keyword_cues] == ["bound"]
    assert validated.scenes[0].keyword_cues[0].source_excerpt == "não chega sozinha"
    assert validated.scenes[0].keyword_cues[0].start_frame == scene["durationFrames"] - 12
    assert validated.scenes[0].keyword_cues[0].duration_frames == 12
    assert {repair["reason"] for repair in repairs} >= {
        "text_span_clamped_to_text",
        "keyword_source_bound_to_script",
        "keyword_cue_clamped_to_scene",
        "unbound_keyword_cue_removed",
    }
    assert all(repair["classification"] == "bounded_normalization" for repair in repairs)


def test_raw_contract_repair_resolves_duplicate_blur_and_camera_identifies_primary_hero():
    from app.domain.studios.contextual_editing_v2 import ContextualPlanRequestV2
    from app.services.studios.editorial_components import repair_raw_composition_contracts

    raw = direction().model_dump(mode="json", by_alias=True)
    scene = raw["scenes"][0]
    primary = scene["elements"][0]
    primary["visualRole"] = "hero"
    primary["depthTreatment"] = {"opacity": 1, "blurPx": 8, "parallax": 0}
    primary["effects"] = [{"id": "soft-blur", "kind": "blur", "amount": 12}]
    secondary = dict(primary)
    secondary.update(
        id="connector",
        kind="path",
        purpose="Conectar o foco ao destino",
        visualRole="hero",
        pathMode="polyline",
        points=[{"x": 0, "y": 0}, {"x": 100, "y": 100}],
        effects=[],
        depthTreatment={"opacity": 1, "blurPx": 0, "parallax": 0},
    )
    secondary.pop("textSpans", None)
    scene["elements"].append(secondary)
    scene["cameraCues"] = [
        {
            "mode": "push_in",
            "targetId": primary["id"],
            "startFrame": 0,
            "durationFrames": 20,
            "intensity": 0.05,
            "rationale": "Manter o foco principal",
        }
    ]

    repairs = repair_raw_composition_contracts(raw)
    validated = ContextualPlanRequestV2.model_validate(raw)

    elements = {element.id: element for element in validated.scenes[0].elements}
    assert elements[primary["id"]].depth_treatment.blur_px == 0
    assert elements["connector"].visual_role == "accent"
    assert {repair["reason"] for repair in repairs} >= {
        "duplicate_depth_blur_removed",
        "secondary_hero_role_demoted",
    }
    assert all(repair["classification"] == "bounded_normalization" for repair in repairs)


def test_duplicate_target_stays_with_composition_that_cannot_spare_it():
    from app.domain.studios.contextual_editing_v2 import ContextualPlanRequestV2
    from app.services.studios.editorial_components import repair_raw_composition_contracts

    raw = direction().model_dump(mode="json", by_alias=True)
    scene = raw["scenes"][0]
    seed = scene["elements"][0]
    scene["elements"] = [
        {**seed, "id": "origin"},
        {**seed, "id": "format-a"},
        {**seed, "id": "format-b"},
        {**seed, "id": "format-c"},
    ]
    scene["compositions"] = [
        {
            "id": "formats",
            "family": "sequence",
            "targetIds": ["format-a", "format-b", "format-c"],
            "purpose": "Mostrar formatos",
            "expectedResult": "Três formatos aparecem",
            "actionFrames": 12,
        },
        {
            "id": "comparison",
            "family": "comparison",
            "targetIds": ["origin", "format-a"],
            "purpose": "Comparar origem e formato",
            "expectedResult": "Origem e formato permanecem relacionados",
            "actionFrames": 12,
        },
    ]

    repairs = repair_raw_composition_contracts(raw)
    validated = ContextualPlanRequestV2.model_validate(raw)

    compositions = {item.id: item for item in validated.scenes[0].compositions}
    assert compositions["formats"].target_ids == ["format-b", "format-c"]
    assert compositions["comparison"].target_ids == ["origin", "format-a"]
    repair = next(item for item in repairs if item["reason"] == "duplicate_semantic_target_reallocated")
    assert repair["classification"] == "bounded_normalization"


def test_effect_amount_is_clamped_without_replanning():
    from app.domain.studios.contextual_editing_v2 import ContextualPlanRequestV2
    from app.services.studios.editorial_components import repair_raw_composition_contracts

    raw = direction().model_dump(mode="json", by_alias=True)
    raw["scenes"][0]["elements"][0]["effects"] = [
        {"id": "glow", "kind": "blur", "amount": 42}
    ]

    repairs = repair_raw_composition_contracts(raw)
    validated = ContextualPlanRequestV2.model_validate(raw)

    assert validated.scenes[0].elements[0].effects[0].amount == 40
    repair = next(item for item in repairs if item["reason"] == "effect_amount_clamped_to_contract_limit")
    assert repair["classification"] == "bounded_normalization"


def test_evidence_can_use_a_registered_support_path_as_visual_annotation():
    from app.domain.studios.cinematic_direction import CinematicShotIntentV1
    from app.domain.studios.contextual_editing_v2 import ContextualPlanRequestV2
    from app.services.studios.editorial_components import repair_composition_contracts

    candidate = direction()
    scene = candidate.scenes[0]
    media = scene.elements[0].model_copy(
        deep=True,
        update={"id": "footage", "kind": "video", "visual_role": "hero", "text": ""},
    )
    marker = scene.elements[0].model_copy(
        deep=True,
        update={
            "id": "marker",
            "kind": "path",
            "visual_role": "support",
            "text": "",
            "path_mode": "polyline",
            "points": [{"x": 0, "y": 0}, {"x": 100, "y": 100}],
        },
    )
    scene.elements = [media, marker]
    scene.compositions = [
        {
            "id": "evidence",
            "family": "evidence",
            "targetIds": ["footage", "marker"],
            "purpose": "Marcar a evidência na imagem",
            "expectedResult": "A marca aponta o foco observado",
            "actionFrames": 12,
        }
    ]
    candidate = ContextualPlanRequestV2.model_validate(
        candidate.model_dump(mode="json", by_alias=True)
    )
    scene = candidate.scenes[0]
    scene.shot_plan = [
        CinematicShotIntentV1.model_validate(
            {
                "id": "annotation-shot",
                "function": "demonstrate",
                "subject": "Material anotado",
                "observableAction": "O caminho aponta a região observada",
                "shotScale": "graphic",
                "angle": "not_applicable",
                "regionOfInterest": "Material e caminho",
                "attentionStart": "Material",
                "attentionEnd": "Caminho",
                "lighting": {
                    "quality": "graphic",
                    "direction": "not_applicable",
                    "contrast": "medium",
                    "temperatureRelationship": "neutra",
                    "subjectSeparation": "contraste gráfico",
                    "executionMode": "deterministic_composite",
                },
                "cutMotivation": "Demonstrar a anotação",
                "executionComponentIds": ["evidence"],
                "targetElementIds": ["marker"],
                "verification": ["Caminho visível"],
                "startFrame": 0,
                "endFrameExclusive": scene.duration_frames,
            }
        )
    ]

    repairs = repair_composition_contracts(candidate)

    assert candidate.scenes[0].compositions[0].family == "annotated_material"
    assert candidate.scenes[0].shot_plan[0].execution_component_ids == ["annotated_material"]
    ContextualPlanRequestV2.model_validate(candidate.model_dump(mode="json", by_alias=True))
    assert any(
        repair["reason"] == "evidence_path_annotation_promoted_to_annotated_material"
        for repair in repairs
    )
    assert not any(item["reason"] == "evidence_without_annotation" for item in repairs)


def test_semantic_component_removes_duplicate_target_layout_controls():
    from app.domain.studios.contextual_editing_v2 import EditorialCompositionV1
    from app.services.studios.editorial_components import (
        classify_contract_repairs,
        repair_composition_contracts,
    )

    request = direction()
    scene = request.scenes[0]
    scene.elements = [
        scene.elements[0].model_copy(
            update={"id": f"format-{index}", "parent_id": "formats-group", "alignment": "center"}
        )
        for index in range(3)
    ]
    scene.compositions = [
        EditorialCompositionV1(
            id="formats-sequence",
            family="sequence",
            target_ids=[element.id for element in scene.elements],
            purpose="Mostrar adaptação em formatos",
            expected_result="Formatos entram em sequência",
            action_frames=12,
        )
    ]

    repairs = repair_composition_contracts(request)

    assert [repair["reason"] for repair in repairs] == [
        "semantic_component_owns_layout_and_base_motion",
        "semantic_component_owns_layout_and_base_motion",
        "semantic_component_owns_layout_and_base_motion",
    ]
    classified = classify_contract_repairs(repairs)
    assert all(item["classification"] == "bounded_normalization" for item in classified)
    assert all(item["requiresAlternative"] is False for item in classified)
    assert all(element.parent_id is None and element.alignment is None for element in scene.elements)


def test_semantic_component_removes_only_motion_cues_for_properties_it_owns():
    from app.domain.studios.contextual_editing_v2 import EditorialCompositionV1, EditorialMotionCueV2
    from app.services.studios.editorial_components import (
        classify_contract_repairs,
        repair_composition_contracts,
    )

    request = direction()
    scene = request.scenes[0]
    target = scene.elements[0]
    scene.elements.append(target.model_copy(update={"id": "second-target"}))
    target.motion_cues = [
        EditorialMotionCueV2(
            kind="entrance",
            profile="path_flow",
            start_frame=0,
            duration_frames=12,
            rationale="Revelar no início",
        ),
        EditorialMotionCueV2(
            kind="secondary",
            profile="standard",
            start_frame=20,
            duration_frames=12,
            rationale="Dar vida ao elemento",
        ),
    ]
    scene.compositions = [
        EditorialCompositionV1(
            id="owned-opacity",
            family="sequence",
            target_ids=[target.id, scene.elements[1].id],
            purpose="Exibir em sequência",
            expected_result="Ordem visível",
        )
    ]

    repairs = repair_composition_contracts(request)

    assert any(item["reason"] == "semantic_component_owns_motion_property" for item in repairs)
    classified = classify_contract_repairs(repairs)
    assert all(item["classification"] == "bounded_normalization" for item in classified)
    assert all(item["requiresAlternative"] is False for item in classified)
    assert [cue.kind for cue in target.motion_cues] == ["secondary"]


def test_explicit_animation_wins_over_conflicting_semantic_motion_cue():
    from app.domain.studios.contextual_editing_v2 import EditorialAnimationV2, EditorialMotionCueV2
    from app.services.studios.editorial_components import (
        classify_contract_repairs,
        repair_composition_contracts,
    )

    request = direction()
    target = request.scenes[0].elements[0]
    target.animations = [
        EditorialAnimationV2(
            property="opacity",
            keyframes=[{"frame": 0, "value": 0}, {"frame": 10, "value": 1}],
        )
    ]
    target.motion_cues = [
        EditorialMotionCueV2(
            kind="entrance",
            profile="path_flow",
            start_frame=0,
            duration_frames=12,
            rationale="Revelar o caminho",
        )
    ]

    repairs = repair_composition_contracts(request)

    assert repairs[0]["reason"] == "explicit_animation_owns_motion_property"
    classified = classify_contract_repairs(repairs)
    assert classified[0]["classification"] == "bounded_normalization"
    assert classified[0]["requiresAlternative"] is False
    assert target.motion_cues == []


def test_layout_solver_scales_small_non_text_hero_without_moving_its_center():
    from app.services.studios.editorial_components import (
        classify_contract_repairs,
        repair_hero_readability,
    )

    request = direction()
    hero = request.scenes[0].elements[0]
    hero.kind = "shape"
    hero.text = ""
    hero.visual_role = "hero"
    hero.x = 500
    hero.y = 500
    hero.width = 50
    hero.height = 50
    center = (hero.x + hero.width / 2, hero.y + hero.height / 2)

    repairs = repair_hero_readability(request, 1080, 1080)

    assert hero.width * hero.height == pytest.approx(1080 * 1080 * 0.025 * 2)
    assert (hero.x + hero.width / 2, hero.y + hero.height / 2) == pytest.approx(center)
    assert classify_contract_repairs(repairs)[0]["classification"] == "bounded_normalization"


def test_sequence_with_path_preserves_authored_spatial_network():
    from app.domain.studios.contextual_editing_v2 import EditorialCompositionV1
    from app.services.studios.editorial_components import lower_compositions

    request = direction()
    scene = request.scenes[0]
    node = scene.elements[0]
    node.kind = "shape"
    node.text = ""
    node.x, node.y, node.width, node.height = 420, 420, 240, 240
    path = node.model_copy(
        update={
            "id": "network-path",
            "kind": "path",
            "visual_role": "support",
            "x": 0,
            "y": 0,
            "width": 1080,
            "height": 1080,
            "points": [{"x": 540, "y": 540}, {"x": 900, "y": 200}],
        }
    )
    scene.elements.append(path)
    scene.compositions = [
        EditorialCompositionV1(
            id="network-sequence",
            family="sequence",
            target_ids=[node.id, path.id],
            purpose="Revelar a rede",
            expected_result="Nó e caminho preservam sua relação espacial",
            action_frames=12,
        )
    ]

    lowered = lower_compositions(request, 1080, 1080)
    lowered_node = next(element for element in lowered.scenes[0].elements if element.id == node.id)
    lowered_path = next(element for element in lowered.scenes[0].elements if element.id == path.id)
    assert (lowered_node.x, lowered_node.y, lowered_node.width, lowered_node.height) == (420, 420, 240, 240)
    assert (lowered_path.x, lowered_path.y, lowered_path.width, lowered_path.height) == (0, 0, 1080, 1080)
    assert lowered_path.start_frame == 12


def test_group_interval_expands_to_contain_staggered_children():
    from app.services.studios.editorial_components import repair_composition_contracts

    request = direction()
    scene = request.scenes[0]
    scene.duration_frames = 90
    seed = scene.elements[0]
    parent = seed.model_copy(
        update={"id": "audience", "kind": "group", "text": "", "start_frame": 0, "duration_frames": 40}
    )
    child = seed.model_copy(
        update={"id": "person", "parent_id": parent.id, "start_frame": 20, "duration_frames": 40}
    )
    scene.elements = [parent, child]
    scene.compositions = []

    repairs = repair_composition_contracts(request)

    assert repairs[0]["reason"] == "group_interval_expanded_to_contain_children"
    assert parent.duration_frames == 60


def test_portrait_sequence_uses_readable_grid():
    from app.domain.studios.contextual_editing_v2 import EditorialCompositionV1
    from app.services.studios.editorial_components import lower_compositions

    request = direction()
    scene = request.scenes[0]
    scene.duration_frames = 180
    scene.elements = [
        scene.elements[0].model_copy(update={"id": f"destination-{index}", "duration_frames": 180})
        for index in range(6)
    ]
    scene.compositions = [
        EditorialCompositionV1(
            id="destinations",
            family="sequence",
            target_ids=[element.id for element in scene.elements],
            purpose="Mostrar destinos",
            expected_result="Destinos legíveis",
            action_frames=20,
        )
    ]

    lowered = lower_compositions(request, 1080, 1920)
    targets = lowered.scenes[0].elements

    assert len({round(element.x) for element in targets}) == 2
    assert len({round(element.y) for element in targets}) == 3
    assert min(element.width for element in targets) > 400


def test_candidate_after_third_is_ranked_before_irrelevant_candidates():
    from types import SimpleNamespace

    need = SimpleNamespace(query="distribuição mensagem", purpose="Mostrar mensagem", acceptance_criteria=[])
    result = rank_candidates(
        {
            "candidates": [
                *({"id": str(i), "description": "paisagem"} for i in range(105)),
                {"id": "relevant", "description": "distribuição mensagem"},
            ]
        },
        need,
    )
    assert result[0]["catalogAssetId"] == "relevant"
    assert len(result) == 106


def test_relevant_external_candidate_precedes_irrelevant_catalog_asset():
    from types import SimpleNamespace

    need = SimpleNamespace(query="ícone de mensagem", purpose="Mostrar conversa", acceptance_criteria=[])
    requirement = {
        "candidates": [{"id": "catalog-lightbulb", "description": "lâmpada e ideia"}],
        "discovery": {
            "candidates": [
                {"id": "procedural-message", "provider": "procedural-icon", "description": "ícone de mensagem"}
            ]
        },
    }

    assert rank_candidates(requirement, need)[0]["id"] == "procedural-message"


@pytest.mark.parametrize("duration,expected", [(12, "requires_alternative"), (15, "accepted")])
def test_inspection_requires_full_selected_interval(duration, expected):
    request = MaterialInspectionRequestV1(
        asset_id="a",
        checksum="a" * 64,
        purpose="Mostrar produto",
        criteria=["Produto visível"],
        source_start_seconds=10,
        required_seconds=5,
    )
    result = MaterialInspectionResultV1(
        description="Produto",
        criteria=[{"index": 0, "result": "supported", "evidence": "Produto visível", "sampleIndices": [0]}],
        confidence=1,
        uncertainty="Intervalos entre amostras não observados",
    )
    assert inspect_verdict(result, request, [{"index": 0}], duration) == expected


@pytest.mark.parametrize("family,count", [("comparison", 2), ("sequence", 3), ("repetition", 1), ("focus", 1)])
def test_semantic_components_compile_without_changing_source(family, count):
    from app.domain.studios.contextual_editing_v2 import EditorialCompositionV1

    request = direction()
    request.scenes[0].elements = [
        request.scenes[0].elements[0].model_copy(deep=True, update={"id": f"target-{i}"}) for i in range(count)
    ]
    request.scenes[0].compositions = [
        EditorialCompositionV1(
            id="action",
            family=family,
            target_ids=[e.id for e in request.scenes[0].elements],
            purpose="Demonstrar",
            expected_result="Relação compreensível",
        )
    ]
    snapshot = request.model_dump()
    draft, graph, _, manifest = compile_scenes(document(), request, "user", "plan")
    assert request.model_dump() == snapshot
    assert manifest["compositionDecisions"][0]["family"] == family
    assert graph.tracks
    assert draft.composition.pages[0].layers


def test_evidence_component_binds_connector_to_actual_layers():
    from app.domain.studios.contextual_editing_v2 import EditorialCompositionV1

    request = direction()
    scene = request.scenes[0]
    scene.elements.insert(
        0, scene.elements[0].model_copy(deep=True, update={"id": "evidence", "kind": "image", "text": ""})
    )
    scene.compositions = [
        EditorialCompositionV1(
            id="show",
            family="evidence",
            target_ids=["evidence", "title"],
            purpose="Mostrar detalhe",
            expected_result="Anotação ligada à imagem",
        )
    ]
    draft, _, _, manifest = compile_scenes(document(), request, "user", "plan")
    connector = next(
        layer.properties["editorialConnector"]
        for layer in draft.composition.pages[0].layers
        if layer.properties.get("editorialConnector")
    )
    assert {connector["from"], connector["to"]} <= {layer.id for layer in draft.composition.pages[0].layers}
    assert manifest["missingMaterials"]


def test_export_sanitizes_credentials_without_erasing_usage():
    from app.services.studios.production_evidence import sanitize

    assert sanitize(
        {"apiKey": "private", "usage": {"total_tokens": 50}, "url": "https://example.com/a?secret=private"}
    ) == {"usage": {"total_tokens": 50}, "url": "https://example.com/a"}


def test_critique_cannot_advance_without_matching_render_evidence():
    from app.services.studios.production_audit import animatic_ready

    critique = {"coverage": "full", "findings": []}
    state = {"artifacts": {"animatic": {"artifact": {"checksumSha256": "a" * 64}}}}
    assert not animatic_ready(state, critique)
    state["visualAudit"] = {
        "renderChecksum": "a" * 64,
        "renderedEvidence": [{"frame": 0}],
        "coverage": {"complete": True, "frameSampleComplete": True},
        "actionVerification": {
            "status": "observed",
            "evidence": [{"sceneId": "scene", "frame": 0}],
        },
    }
    assert animatic_ready(state, critique)
    state["visualAudit"]["actionVerification"] = {"status": "pending", "evidence": []}
    assert not animatic_ready(state, critique)
    state["visualAudit"]["actionVerification"] = {
        "status": "observed",
        "evidence": [{"sceneId": "scene", "frame": 0}],
    }
    critique["coverage"] = "partial"
    assert not animatic_ready(state, critique)
    critique["coverage"] = "full"
    state["visualAudit"]["renderChecksum"] = "b" * 64
    assert not animatic_ready(state, critique)


def test_visual_findings_schedule_at_most_two_local_correction_rounds():
    from app.services.studios.production_audit import prepare_visual_correction

    state = {
        "revision": 1,
        "jobs": {"animatic": "job"},
        "artifacts": {"plan": {"direction": {"scenes": [{"id": "scene"}]}}},
    }
    audit = {
        "findings": [
            {
                "sceneId": "scene",
                "code": "concurrent_text_collision",
                "severity": "correction",
                "correction": "Vincule o destaque ao span existente.",
            }
        ]
    }

    assert prepare_visual_correction(state, audit)
    assert state["stage"] == "composition"
    assert state["correctionRounds"] == 1
    state["correctionRounds"] = 2
    assert prepare_visual_correction(state, audit)
    assert state["status"] == "awaiting_review"
    assert state["blockers"] == ["production_visual_correction_limit_reached"]


def test_export_checks_bytes_and_contains_no_private_storage_paths(monkeypatch, tmp_path):
    import hashlib
    import zipfile
    from contextlib import nullcontext
    from types import SimpleNamespace as NS

    from app.services.studios import production_evidence as service

    path = tmp_path / "fixture.bin"
    path.write_bytes(b"export integrity fixture")
    checksum = hashlib.sha256(path.read_bytes()).hexdigest()
    state = {"jobs": {}, "artifacts": {"video": {"artifact": {"assetId": "asset", "checksumSha256": checksum}}}}
    asset = NS(
        workspace_id="tenant",
        checksum_sha256=checksum,
        lifecycle_status="active",
        media_type="application/octet-stream",
        storage_backend="local",
        storage_key="private/path",
        title="Fixture",
        object_metadata={"storageKey": "private/path"},
    )
    monkeypatch.setattr(service, "get_run", lambda *args: state)
    monkeypatch.setattr(service, "get_object_storage", lambda *args: NS(materialize=lambda key: nullcontext(path)))
    db, record = NS(get=lambda *args: asset), NS(workspace_id="tenant")
    with service.export_package(db, record, "run") as stream, zipfile.ZipFile(stream) as archive:
        assert archive.read("materials/0000.bin") == path.read_bytes()
        assert "private/path" not in archive.read("materials.json").decode()
        assert "avaliacao.md" in archive.namelist()
    path.write_bytes(b"changed")
    with pytest.raises(ValueError, match="checksum_conflict"):
        service.export_package(db, record, "run")


def test_material_inspection_samples_selected_interval_and_scene_changes(monkeypatch, tmp_path):
    from contextlib import ExitStack, nullcontext
    from types import SimpleNamespace as NS

    from app.services.studios import material_inspection as service

    source = tmp_path / "fixture.bin"
    source.write_bytes(b"inspection fixture")
    checksum = service.sha256_file(source)
    request = MaterialInspectionRequestV1(
        asset_id="asset",
        checksum=checksum,
        purpose="Produto",
        criteria=["Visível"],
        required_seconds=5,
        source_start_seconds=10,
        max_samples=18,
    )
    asset = NS(id="asset", media_type="video/mp4", storage_backend="local", storage_key="file")
    monkeypatch.setattr(service, "bound_asset", lambda *args: asset)
    monkeypatch.setattr(service, "get_object_storage", lambda *args: NS(materialize=lambda key: nullcontext(source)))
    monkeypatch.setitem(
        service.MEDIA_PROBE_PROVIDERS,
        "builtin.ffprobe",
        NS(probe=lambda *args, **kwargs: NS(duration_microseconds=20000000)),
    )

    def run(self, args, directory, cancelled):
        if args[-1] == "-":
            (directory / "scene-changes.txt").write_text("frame:0 pts:0 pts_time:2.0\n")
        else:
            from pathlib import Path

            Path(args[-1]).write_bytes(b"sample")

    monkeypatch.setattr(service.ContextualFFmpegProvider, "_run", run)
    with ExitStack() as stack:
        _, samples, _ = service.prepare_samples(
            None, "tenant", request, stack, tmp_path, NS(ffmpeg_path="ffmpeg", ffmpeg_timeout_seconds=30), lambda: False
        )
    assert 6 < len(samples) <= 18
    assert all(10 <= s["seconds"] < 15 for s in samples)
    assert any(abs(s["seconds"] - 12.08) < 0.001 for s in samples)


def test_http_continuation_queues_once_instead_of_acquiring_on_request(monkeypatch):
    from types import SimpleNamespace as NS

    from app.services.studios import production_queue as service
    from app.tasks import advance_editorial_production

    state = {"status": "pending", "request": {"useSemanticCompositions": True}}
    monkeypatch.setattr(service, "get_run", lambda *args: state)
    monkeypatch.setattr(service, "save", lambda db, record, user, value: value)
    monkeypatch.setattr(service, "lock_editing_budget", lambda *args: None)
    calls = []
    monkeypatch.setattr(advance_editorial_production, "apply_async", lambda **kwargs: calls.append(kwargs))
    for _ in range(2):
        service.continue_from_api(None, NS(id="doc", workspace_id="tenant"), "run", NS(id="user"))
    assert len(calls) == 1
    assert state["continuationTaskId"] == calls[0]["task_id"]


def test_continuity_component_compiles_and_requires_prior_identity():
    from app.domain.studios.contextual_editing_v2 import EditorialCompositionV1

    request = direction(durationFrames=120)
    second = request.scenes[0].model_copy(deep=True, update={"id": "second", "entrance": "dissolve"})
    second.elements[0].id = "next"
    second.compositions = [
        EditorialCompositionV1(
            id="handoff",
            family="continuity",
            action_frames=12,
            target_ids=["next"],
            previous_element_id="title",
            purpose="Manter identidade",
            expected_result="Objeto persiste",
        )
    ]
    request.scenes.append(second)
    _, graph, _, manifest = compile_scenes(document(), request, "user", "plan")
    assert graph.transitions
    assert manifest["compositionDecisions"][0]["family"] == "continuity"
    second.compositions[0].previous_element_id = "absent"
    with pytest.raises(ValueError, match="match_transform_incompatible"):
        compile_scenes(document(), request, "user", "plan")


def test_external_analysis_does_not_approve_and_rejects_stale_binding(monkeypatch):
    from types import SimpleNamespace as NS

    from app.domain.studios.editorial_production import ExternalProductionReviewV1
    from app.services.studios import production_evidence as service

    state = {
        "revision": 4,
        "humanReview": "pending",
        "artifacts": {"video": {"artifact": {"checksumSha256": "a" * 64}}},
    }
    monkeypatch.setattr(service, "get_run", lambda *args: state)
    monkeypatch.setattr(service, "save", lambda db, record, user, value: value)
    request = ExternalProductionReviewV1(
        expected_run_revision=4, render_checksum="a" * 64, text="Simplificar a cena dois"
    )
    result = service.record_external_review(None, None, "run", request, NS(id="reviewer"))
    assert result["humanReview"] == "pending"
    assert result["externalReviews"][0]["status"] == "unverified"
    request.render_checksum = "b" * 64
    with pytest.raises(ValueError, match="review_conflict"):
        service.record_external_review(None, None, "run", request, NS(id="reviewer"))


def test_calm_revision_changes_executable_component_without_changing_other_scene():
    from app.domain.studios.contextual_editing_v2 import EditorialCompositionV1
    from app.services.studios.contextual_editing_v2 import revise_direction

    request = direction()
    request.scenes[0].compositions = [
        EditorialCompositionV1(
            id="focus",
            family="focus",
            target_ids=["title"],
            purpose="Focar mensagem",
            expected_result="Mensagem legível",
        )
    ]
    request.scenes.append(request.scenes[0].model_copy(deep=True, update={"id": "conclusion"}))
    revised = revise_direction(request, {"scene"}, "mais calmo")
    assert revised.scenes[0].compositions[0].action_frames > request.scenes[0].compositions[0].action_frames
    assert revised.scenes[1] == request.scenes[1]
    _, graph, _, _ = compile_scenes(document(), revised, "user", "plan")
    assert graph.tracks[0].keyframes[-1].frame == revised.scenes[0].compositions[0].action_frames


def test_raw_contract_repairs_preserve_geometry_and_fill_unambiguous_defaults():
    from app.services.studios.editorial_components import repair_raw_composition_contracts

    raw = {
        "scenes": [
            {
                "id": "scene",
                "durationFrames": 90,
                "cameraCues": [{"id": "camera", "intensity": 0.2}],
                "elements": [
                    {"id": "background", "kind": "shape"},
                    {"id": "card", "kind": "card", "textSpans": []},
                    {"id": "annotation-media", "kind": "image"},
                    {
                        "id": "annotation-text",
                        "kind": "text",
                        "text": "Ideia",
                        "alignment": {
                            "targetId": "annotation-text",
                            "horizontal": "center",
                            "vertical": "middle",
                        },
                    },
                    {
                        "id": "path",
                        "kind": "path",
                        "x": 100,
                        "y": 100,
                        "points": [{"x": 0, "y": 0}, {"x": 20, "y": -30}],
                    },
                ],
                "compositions": [
                    {
                        "id": "formats",
                        "family": "format_transformation",
                        "targetIds": ["background", "card", "path"],
                        "viewportFormats": ["portrait", "landscape"],
                    }
                ],
                "materialNeeds": [
                    {"id": "need", "blueprintRequirementId": "blueprint-need"}
                ],
                "shotPlan": [
                    {
                        "id": "shot",
                        "materialRequirementIds": ["need"],
                        "executionComponentIds": ["formats"],
                        "startFrame": 0,
                        "endFrameExclusive": 120,
                    }
                ],
            }
        ]
    }

    raw["scenes"][0]["compositions"].append(
        {
            "id": "annotation",
            "family": "annotated_material",
            "targetIds": ["annotation-media", "annotation-text"],
            "viewportFormats": ["portrait", "square"],
            "interfaceEvents": ["select", "open"],
        }
    )

    repairs = repair_raw_composition_contracts(raw)

    scene = raw["scenes"][0]
    assert scene["cameraCues"][0]["intensity"] == 0.15
    assert scene["elements"][0]["durationFrames"] == 90
    assert scene["elements"][1]["kind"] == "shape"
    path = next(element for element in scene["elements"] if element["id"] == "path")
    assert path["y"] == 70
    assert path["points"][1]["y"] == 0
    assert len(scene["compositions"][0]["viewportFormats"]) == 3
    assert scene["compositions"][1]["viewportFormats"] == []
    assert scene["compositions"][1]["interfaceEvents"] == []
    assert scene["elements"][3]["alignment"] is None
    assert scene["shotPlan"][0]["materialRequirementIds"] == ["blueprint-need"]
    assert scene["shotPlan"][0]["executionComponentIds"] == ["format_transformation"]
    assert scene["shotPlan"][0]["endFrameExclusive"] == 90
    assert {repair["reason"] for repair in repairs} >= {
        "camera_intensity_clamped_to_contract_limit",
        "empty_card_normalized_to_shape",
        "missing_element_duration_bound_to_scene",
        "negative_path_points_rebased_preserving_absolute_geometry",
        "semantic_parameter_count_bound_to_targets",
        "shot_material_bound_to_blueprint_requirement",
        "shot_component_bound_to_registered_family",
        "final_shot_bound_to_scene_duration",
        "foreign_semantic_parameters_removed",
        "self_alignment_removed",
    }


def test_camera_target_on_preserved_text_rebinds_to_single_scene_hero():
    from app.services.studios.editorial_components import repair_raw_composition_contracts

    raw = {
        "scenes": [
            {
                "id": "scene",
                "durationFrames": 60,
                "elements": [
                    {"id": "footage", "kind": "video", "visualRole": "hero"},
                    {"id": "headline", "kind": "text", "visualRole": "text", "text": "Atenção"},
                ],
                "cameraCues": [
                    {
                        "mode": "pull_out",
                        "targetId": "headline",
                        "startFrame": 10,
                        "durationFrames": 20,
                    }
                ],
            }
        ]
    }

    repairs = repair_raw_composition_contracts(raw)

    assert raw["scenes"][0]["cameraCues"][0]["targetId"] == "footage"
    assert any(
        repair["reason"] == "camera_target_rebound_to_primary_visual"
        for repair in repairs
    )


def test_raw_format_transformation_instances_one_media_asset_and_preserves_text_overlay():
    from app.services.studios.editorial_components import repair_raw_composition_contracts

    raw = {
        "scenes": [
            {
                "id": "scene",
                "durationFrames": 90,
                "elements": [
                    {"id": "footage", "kind": "video", "purpose": "Mesma mensagem"},
                    {
                        "id": "caption",
                        "kind": "text",
                        "text": "FORMATOS",
                        "purpose": "Explicar",
                        "afterElementId": "footage",
                    },
                ],
                "compositions": [
                    {
                        "id": "formats",
                        "family": "format_transformation",
                        "targetIds": ["footage", "caption"],
                        "viewportFormats": ["landscape", "portrait"],
                    }
                ],
                "materialNeeds": [
                    {
                        "id": "need",
                        "targetId": "footage",
                        "field": "asset",
                        "kind": "video",
                        "query": "devices showing one message",
                        "purpose": "Mesma mensagem",
                        "sourceClass": "licensed_stock",
                        "blueprintRequirementId": "source-message",
                        "postProcessing": ["remove_background"],
                    }
                ],
                "shotPlan": [
                    {
                        "id": "shot-1",
                        "materialRequirementIds": ["source-message"],
                        "targetElementIds": [],
                    },
                    {
                        "id": "shot-2",
                        "materialRequirementIds": ["source-message"],
                        "targetElementIds": [],
                    },
                ],
            }
        ]
    }

    repairs = repair_raw_composition_contracts(raw)

    scene = raw["scenes"][0]
    composition = scene["compositions"][0]
    assert composition["targetIds"] == ["footage", "footage-format-2"]
    assert composition["viewportFormats"] == ["landscape", "portrait"]
    assert composition["continuityKey"] == "footage"
    assert {
        element["contentIdentity"]
        for element in scene["elements"]
        if element["id"] in composition["targetIds"]
    } == {"footage"}
    caption = next(element for element in scene["elements"] if element["id"] == "caption")
    assert caption["afterElementId"] is None
    clone_need = next(need for need in scene["materialNeeds"] if need["targetId"] == "footage-format-2")
    assert clone_need["blueprintRequirementId"] == "source-message"
    assert clone_need["query"] == "devices showing one message"
    assert clone_need["postProcessing"] == []
    assert [shot["targetElementIds"] for shot in scene["shotPlan"]] == [
        ["footage"],
        ["footage-format-2"],
    ]
    assert "format_transformation_media_states_instanced" in {
        repair["reason"] for repair in repairs
    }


def test_raw_contract_repairs_rebase_scene_global_motion_cue_frames():
    from app.domain.studios.contextual_editing_v2 import ContextualPlanRequestV2
    from app.services.studios.editorial_components import repair_raw_composition_contracts

    raw = direction().model_dump(mode="json", by_alias=True)
    element = raw["scenes"][0]["elements"][0]
    element["startFrame"] = 90
    element["durationFrames"] = 90
    element["motionCues"] = [
        {
            "kind": "entrance",
            "profile": "gentle",
            "startFrame": 90,
            "durationFrames": 10,
            "intensity": 0.5,
            "rationale": "Entrada ligada ao início global do elemento.",
        }
    ]

    repairs = repair_raw_composition_contracts(raw)
    validated = ContextualPlanRequestV2.model_validate(raw)

    assert validated.scenes[0].elements[0].motion_cues[0].start_frame == 0
    assert "motion_cue_global_frame_rebased" in {repair["reason"] for repair in repairs}


def test_raw_contract_repairs_convert_absolute_position_tracks_and_normalized_paths():
    from app.domain.studios.contextual_editing_v2 import ContextualPlanRequestV2
    from app.services.studios.editorial_components import repair_raw_composition_contracts

    raw = direction().model_dump(mode="json", by_alias=True)
    element = raw["scenes"][0]["elements"][0]
    element.update(
        {
            "kind": "path",
            "text": "",
            "x": 200,
            "y": 300,
            "width": 400,
            "height": 200,
            "points": [{"x": 0.1, "y": 0.25}, {"x": 0.9, "y": 0.75}],
            "animations": [
                {
                    "property": "position_x",
                    "keyframes": [
                        {"frame": 0, "value": 200, "easing": "ease_in_out"},
                        {"frame": 20, "value": 224, "easing": "ease_in_out"},
                    ],
                }
            ],
        }
    )

    repairs = repair_raw_composition_contracts(raw)
    validated = ContextualPlanRequestV2.model_validate(raw)
    repaired = validated.scenes[0].elements[0]

    assert [key.value for key in repaired.animations[0].keyframes] == [0, 24]
    assert [(point.x, point.y) for point in repaired.points] == [(40, 50), (360, 150)]
    reasons = {repair["reason"] for repair in repairs}
    assert "absolute_position_track_rebased_to_delta" in reasons
    assert "normalized_path_points_scaled_to_element" in reasons


def test_annotated_material_keeps_multiple_overlays_bound_to_media():
    from app.domain.studios.contextual_editing_v2 import EditorialAnimationV2, EditorialCompositionV1
    from app.services.studios.editorial_components import (
        lower_compositions,
        repair_composition_contracts,
    )

    request = direction()
    scene = request.scenes[0]
    prototype = scene.elements[0]
    media = prototype.model_copy(
        update={
            "id": "footage",
            "kind": "video",
            "text": "",
            "x": 100,
            "y": 200,
            "width": 400,
            "height": 300,
            "visual_role": "hero",
        }
    )
    marker = prototype.model_copy(
        update={
            "id": "marker",
            "kind": "shape",
            "text": "",
            "x": 200,
            "y": 260,
            "width": 80,
            "height": 80,
            "visual_role": "accent",
            "animations": [
                EditorialAnimationV2.model_validate(
                    {
                        "property": "position_x",
                        "keyframes": [
                            {"frame": 0, "value": 0, "easing": "ease_in_out"},
                            {"frame": 20, "value": 12, "easing": "ease_in_out"},
                        ],
                    }
                )
            ],
        }
    )
    shade = marker.model_copy(
        update={
            "id": "shade",
            "x": 100,
            "y": 200,
            "width": 400,
            "height": 300,
            "animations": [],
        }
    )
    caption = prototype.model_copy(
        update={"id": "caption", "text": "Mensagem", "visual_role": "text"}
    )
    scene.elements = [media, marker, shade, caption]
    scene.compositions = [
        EditorialCompositionV1(
            id="annotated",
            family="annotated_material",
            target_ids=["footage", "marker", "shade", "caption"],
            purpose="Relacionar marcações ao material",
            expected_result="Marcações permanecem sobre seus alvos",
            action_frames=20,
        )
    ]

    repair_composition_contracts(request)
    lowered = lower_compositions(request, 640, 640)
    lowered_scene = lowered.scenes[0]
    indexed = {element.id: element for element in lowered_scene.elements}

    assert indexed["marker"].animations[0].property == "position_x"
    assert indexed["footage"].x <= indexed["marker"].x < indexed["footage"].x + indexed["footage"].width
    assert indexed["footage"].y <= indexed["marker"].y < indexed["footage"].y + indexed["footage"].height
    assert indexed["shade"].x == pytest.approx(indexed["footage"].x)
    assert indexed["shade"].y == pytest.approx(indexed["footage"].y)
    assert not any(element.connector_from_id for element in lowered_scene.elements)


def test_explicit_semantic_icon_is_promoted_from_primitive_to_registered_material_need():
    from app.domain.studios.contextual_editing_v2 import ContextualPlanRequestV2
    from app.services.studios.editorial_components import repair_raw_composition_contracts

    raw = direction().model_dump(mode="json", by_alias=True)
    scene = raw["scenes"][0]
    icon = scene["elements"][0]
    icon.update(
        kind="shape",
        purpose="Ícone procedural de lâmpada para representar uma ideia",
        shape="ellipse",
        assetId=None,
    )
    scene["materialNeeds"] = []

    repairs = repair_raw_composition_contracts(raw)
    validated = ContextualPlanRequestV2.model_validate(raw)
    repaired = validated.scenes[0].elements[0]
    need = validated.scenes[0].material_needs[0]

    assert repaired.kind == "image"
    assert need.target_id == repaired.id
    assert need.source_class == "catalog"
    assert need.alpha_required is True
    assert "ícone" in need.query.casefold()
    assert any(item["reason"] == "semantic_icon_shape_promoted_to_material_need" for item in repairs)


def test_provider_animation_edges_are_repaired_without_another_submission():
    from app.domain.studios.contextual_editing_v2 import ContextualPlanRequestV2
    from app.services.studios.editorial_components import repair_raw_composition_contracts

    raw = direction().model_dump(mode="json", by_alias=True)
    element = raw["scenes"][0]["elements"][0]
    element.update(
        kind="shape",
        reveal="path",
        animations=[
            {
                "property": "opacity",
                "keyframes": [
                    {
                        "frame": 0,
                        "value": 0,
                        "easing": "ease_in_out",
                        "cubicBezier": [0.42, 0, 0.58, 1],
                    },
                    {
                        "frame": element["durationFrames"],
                        "value": 1,
                        "easing": "ease_in_out",
                        "cubicBezier": [0.42, 0, 0.58, 1],
                    },
                ],
            }
        ],
    )

    repairs = repair_raw_composition_contracts(raw)
    validated = ContextualPlanRequestV2.model_validate(raw)
    repaired = validated.scenes[0].elements[0]

    assert repaired.reveal == "wipe"
    assert [item.frame for item in repaired.animations[0].keyframes] == [
        0,
        repaired.duration_frames - 1,
    ]
    assert all(item.easing == "cubic_bezier" for item in repaired.animations[0].keyframes)
    reasons = {item["reason"] for item in repairs}
    assert "path_reveal_normalized_to_element_wipe" in reasons
    assert "animation_frames_clamped_to_element_interval" in reasons
    assert "explicit_bezier_bound_to_cubic_easing" in reasons


def test_raw_contract_repairs_preserve_hold_blur_and_shot_semantics():
    from app.domain.studios.contextual_editing_v2 import ContextualPlanRequestV2
    from app.services.studios.editorial_components import repair_raw_composition_contracts

    raw = direction().model_dump(mode="json", by_alias=True)
    scene = raw["scenes"][0]
    element = scene["elements"][0]
    element["depthTreatment"]["blurPx"] = 2
    element["effects"] = [{"id": "light", "kind": "brightness", "amount": 1.1}]
    element["motionCues"] = [
        {
            "kind": "deliberate_hold",
            "profile": "deliberate_hold",
            "startFrame": 0,
            "durationFrames": 10,
            "intensity": 0,
            "rationale": "Pausa para leitura",
        }
    ]
    scene["compositions"] = [
        {
            "id": "focus",
            "family": "focus",
            "targetIds": [element["id"]],
            "purpose": "Manter o foco",
            "expectedResult": "Foco preservado",
            "actionFrames": 10,
            "repeatCount": 1,
        }
    ]
    scene["shotPlan"] = [
        {
            "id": "shot",
            "function": "demonstrate",
            "subject": "Elemento principal",
            "observableAction": "O elemento permanece visível",
            "shotScale": "medium",
            "angle": "eye_level",
            "regionOfInterest": "Centro do elemento",
            "attentionStart": "Elemento principal",
            "attentionEnd": "Elemento principal",
            "lighting": {
                "quality": "graphic",
                "direction": "not_applicable",
                "contrast": "medium",
                "temperatureRelationship": "Neutra",
                "subjectSeparation": "Contraste tonal",
                "executionMode": "deterministic_composite",
            },
            "cutMotivation": "Sustentar a explicação",
            "continuity": ["Preservar o elemento"],
            "materialRequirementIds": [],
            "executionComponentIds": ["groups"],
            "targetElementIds": [element["id"]],
            "verification": ["Elemento permanece visível"],
            "startFrame": 0,
            "endFrameExclusive": scene["durationFrames"],
        }
    ]

    repairs = repair_raw_composition_contracts(raw)
    validated = ContextualPlanRequestV2.model_validate(raw)
    repaired = validated.scenes[0]

    assert repaired.elements[0].depth_treatment.blur_px == 0
    assert {effect.kind for effect in repaired.elements[0].effects} == {"brightness", "blur"}
    assert repaired.elements[0].motion_cues[0].intensity == 0.1
    assert repaired.compositions[0].repeat_count == 3
    assert repaired.shot_plan[0].execution_component_ids == ["focus"]
    assert {item["reason"] for item in repairs} >= {
        "legacy_blur_moved_to_effect_stack",
        "deliberate_hold_intensity_normalized",
        "semantic_repeat_count_defaulted",
        "shot_component_rebound_after_composition_repair",
    }
