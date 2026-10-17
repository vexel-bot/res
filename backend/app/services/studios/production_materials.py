"""Resume acquisition and inspection through existing production state and jobs."""

import math
import re

from ...config import get_settings
from ...domain.studios.contextual_editing import digest
from ...domain.studios.contextual_editing_v2 import (
    EditorialAlignmentV2,
    EditorialAnimationV2,
    EditorialElementV2,
    EditorialMaterialChoiceV2,
    EditorialMaterialV2,
)
from ...domain.studios.editing_resources import EditingAIRequestV1
from ...domain.studios.editorial_production import ProductionRequestV1
from ...domain.studios.hybrid_video import (
    HybridProductionPolicyV1,
    HybridSelectionRequestV1,
    select_hybrid_profile,
)
from ...domain.studios.material_inspection import (
    MaterialInspectionRequestV1,
    material_inspection_criteria,
)
from ...domain.studios.motion import MotionKeyframeV1
from ...domain.studios.scene_generation import SceneGenerationRequestV2
from ...models import LibraryAsset, StudioGenerationJob
from ...providers.studios.editing_ai import selected_adapter
from .contextual_editing_v2 import select_material
from .gemini_editing import create_editing_job
from .material_acquisition import acquire_candidate
from .scene_generation import create_scene_generation_job

MATERIAL_RESOLUTION_VERSION = "res.material-resolution.v2.22"
MAX_INSPECTED_CANDIDATES_PER_NEED = 3
MAX_PAID_INSPECTIONS_PER_PLAN = 7
RECOVERABLE_CANDIDATE_ERRORS = {
    "resource_image_unsupported",
    "resource_too_large",
    "resource_empty",
    "background_removal_alpha_unusable",
    "background_removal_output_invalid",
    "procedural_semantic_mismatch",
}

GRAPHIC_TERMS = ("icon", "icone", "ícone", "logo", "symbol", "simbolo", "símbolo")
MOTION_TERMS = (
    "movement",
    "motion",
    "moving",
    "circular",
    "movimento",
    "movendo",
    "circular",
)
FORMAT_TRANSFORMATION_TERMS = (
    "adapt",
    "mensagem",
    "message",
    "format",
    "sequencia",
    "sequência",
    "continuous",
    "continua",
    "contínua",
)

AESTHETIC_ONLY_TERMS = (
    "expressão neutra",
    "expressao neutra",
    "sem distrações",
    "sem distracoes",
    "iluminação uniforme",
    "iluminacao uniforme",
    "luz natural",
    "cores semelhantes",
    "cores não saturadas",
    "cores nao saturadas",
    "gestos naturais",
    "movimento suave",
    "fundo suave",
    "fundo claro",
    "fundo uniforme",
    "ambiente real claramente visível",
    "ambiente real claramente visivel",
    "parcela central do quadro",
    "central do quadro",
)


def _contains_any(value, terms):
    normalized = str(value or "").casefold()
    return any(term in normalized for term in terms)


def _blueprint_material_query(state, scene_id, need_id):
    direction = state.get("artifacts", {}).get("direction", {})
    beat = next((item for item in direction.get("beats", []) if item.get("id") == scene_id), None)
    if not beat:
        return None
    materials = (
        beat.get("visualBlueprint", {})
        .get("demonstration", {})
        .get("indispensableMaterials", [])
    )
    item = next((value for value in materials if value.get("id") == need_id), None)
    return str((item or {}).get("query") or "").strip() or None


def _reclassify_aesthetic_acceptance_criteria(plan, requirement, need, state):
    """Keep representation facts mandatory and move art preferences out of the gate."""

    if need.requirement_class != "mandatory" or not need.acceptance_criteria:
        return None
    retained: list[str] = []
    preferred = list(need.preferred_criteria)
    changed = False
    for criterion in need.acceptance_criteria:
        normalized = criterion.casefold()
        replacement = None
        if "pessoa e express" in normalized and "neutra" in normalized:
            replacement = "Pessoa claramente visível"
        elif "ambiente real" in normalized and "neutro" in normalized:
            replacement = "Ambiente real claramente visível"
        elif "ambiente cotidiano" in normalized and _contains_any(
            normalized, ("sem distrações", "sem distracoes")
        ):
            replacement = "Ambiente cotidiano claramente visível"
        elif "ambiente natural" in normalized and "ilumina" in normalized:
            replacement = "Ambiente real claramente visível"
        elif _contains_any(normalized, AESTHETIC_ONLY_TERMS):
            preferred.append(criterion)
            changed = True
            continue
        if replacement:
            retained.append(replacement)
            preferred.append(criterion)
            changed = True
        else:
            retained.append(criterion)
    retained = list(dict.fromkeys(retained))
    preferred = list(dict.fromkeys(preferred))
    concise_visual = ". ".join(retained)
    original_query = _blueprint_material_query(
        state, requirement["sceneId"], need.id
    )
    visual_has_aesthetic = _contains_any(
        need.visual_description, AESTHETIC_ONLY_TERMS
    )
    if not retained or (
        not changed
        and not visual_has_aesthetic
        and (not original_query or need.query == original_query)
    ):
        return None
    revised = plan.direction.model_copy(deep=True)
    scene = next(item for item in revised.scenes if item.id == requirement["sceneId"])
    revised_need = next(item for item in scene.material_needs if item.id == need.id)
    revised_need.acceptance_criteria = retained
    revised_need.preferred_criteria = preferred
    revised_need.visual_description = concise_visual[:2000]
    revised_need.query = (original_query or need.query)[:500]
    revised_need.appearance = ""
    return revised, {
        "status": "material_requirement_reclassified",
        "sceneId": scene.id,
        "needId": revised_need.id,
        "reason": "aesthetic_preferences_removed_from_mandatory_pixel_gate",
        "mandatoryCriteria": retained,
        "preferredCriteria": preferred,
        "providerSubmission": False,
    }


def _decompose_unobservable_attention_state(plan, requirement, need):
    """Move an internal attention claim from stock pixels to deterministic proof.

    Stock footage can establish a real recipient and device, but it is a poor
    source for proving an internal state such as attention or indifference. If
    the scene already owns an interrupted path and an explicit textual
    qualification, those executable elements carry the causal statement while
    footage supplies only the observable human context.
    """

    if need.kind != "video" or need.source_class != "licensed_stock":
        return None
    if str(need.action).startswith(
        "Pessoa usa o dispositivo; nenhuma reação interna específica é inferida."
    ):
        return None
    description = " ".join(
        [
            need.purpose,
            need.visual_description,
            need.action,
            *need.acceptance_criteria,
        ]
    )
    attention_terms = (
        "attention",
        "atencao",
        "atenção",
        "distract",
        "distra",
        "indifference",
        "indiferen",
        "desinter",
        "ignore",
        "ignora",
    )
    if not _contains_any(description, attention_terms):
        return None
    source_scene = next((item for item in plan.direction.scenes if item.id == requirement["sceneId"]), None)
    if source_scene is None:
        return None
    has_path = any(element.kind == "path" for element in source_scene.elements)
    has_qualification = any(
        element.kind == "text"
        and _contains_any(
            " ".join((element.text, element.concise_text or "", element.purpose)),
            ("nao garante", "não garante", "attention", "atencao", "atenção"),
        )
        for element in source_scene.elements
    )
    if not has_qualification:
        return None

    direction = plan.direction.model_copy(deep=True)
    scene = next(item for item in direction.scenes if item.id == source_scene.id)
    revised_need = next(item for item in scene.material_needs if item.id == need.id)
    target = next(item for item in scene.elements if item.id == revised_need.target_id)
    path_id = next(
        (element.id for element in scene.elements if element.kind == "path"),
        None,
    )
    if path_id is None:
        path_id = f"{target.id}-delivery-path"
        scene.elements.append(
            EditorialElementV2(
                id=path_id,
                kind="path",
                purpose=(
                    "Mostrar o caminho de entrega interrompido antes de qualquer "
                    "confirmação de interação"
                ),
                start_frame=0,
                duration_frames=scene.duration_frames,
                x=max(0, target.x + target.width * 0.55),
                y=max(0, target.y + target.height * 0.45),
                width=max(120, min(420, target.width * 0.35)),
                height=max(60, min(180, target.height * 0.2)),
                z_index=target.z_index + 1,
                visual_role="accent",
                points=[{"x": 0, "y": 0}, {"x": 0.62, "y": 0}, {"x": 0.78, "y": 0.5}],
                color="#60aaff",
                reveal="path",
                reveal_frames=min(30, max(8, scene.duration_frames // 3)),
            )
        )
    if "paths" not in scene.technique_ids:
        scene.technique_ids.append("paths")
    verified_seconds = min(float(revised_need.duration_seconds or 3.0), 3.0)
    fps = direction.frame_rate.numerator / direction.frame_rate.denominator
    target.duration_frames = min(target.duration_frames, max(1, math.floor(verified_seconds * fps)))
    target.purpose = "Contextualizar uma pessoa real usando um dispositivo digital"
    revised_need.query = (
        "Pessoa em ambiente real usando smartphone, tablet ou notebook; "
        "pessoa, dispositivo e tela claramente visíveis."
    )
    revised_need.purpose = (
        "Estabelecer o contexto humano e o dispositivo; o caminho interrompido e a tipografia "
        "demonstram separadamente que alcance não garante atenção."
    )
    revised_need.visual_description = (
        "Pessoa reconhecível em ambiente real usando um dispositivo digital, com a tela visível."
    )
    revised_need.action = "Pessoa usa o dispositivo; nenhuma reação interna específica é inferida."
    revised_need.duration_seconds = verified_seconds
    revised_need.acceptance_criteria = [
        "Pessoa reconhecível em ambiente real",
        "Dispositivo digital claro em quadro",
        "Tela do dispositivo visível",
        "Gesto natural de uso do dispositivo",
    ]
    revised_need.preferred_criteria = ["Enquadramento limpo e movimento suave"]

    for composition in scene.compositions:
        if revised_need.target_id not in composition.target_ids:
            continue
        if path_id not in composition.target_ids:
            composition.target_ids.append(path_id)
        composition_elements = [
            element for element in scene.elements if element.id in composition.target_ids
        ]
        if composition_elements:
            composition.action_frames = min(
                composition.action_frames,
                max(1, min(element.duration_frames for element in composition_elements) - 1),
            )
        composition.purpose = (
            "Combinar contexto humano observável com o caminho interrompido, sem atribuir "
            "um estado mental à pessoa filmada."
        )
        composition.expected_result = (
            "A pessoa e o dispositivo estabelecem o destinatário; a interrupção do caminho e "
            "a ressalva textual comunicam que entrega não equivale a atenção."
        )
    for visual_state in scene.visual_states:
        if revised_need.target_id in visual_state.essential_element_ids:
            if path_id not in visual_state.essential_element_ids:
                visual_state.essential_element_ids.append(path_id)
            visual_state.purpose = (
                "Contexto humano visível enquanto o caminho gráfico para antes de confirmar interação"
            )
            visual_state.expected_changes = [
                "Pessoa e dispositivo permanecem identificáveis",
                "Caminho interrompido permanece visualmente separado da pessoa",
            ]
    for shot in scene.shot_plan:
        if revised_need.target_id not in shot.target_element_ids:
            continue
        if path_id not in shot.target_element_ids:
            shot.target_element_ids.append(path_id)
        if "paths" not in shot.execution_component_ids:
            shot.execution_component_ids.append("paths")
        shot.subject = "Pessoa usando um dispositivo digital"
        shot.observable_action = (
            "A pessoa usa o dispositivo enquanto o caminho gráfico interrompe seu traçado; "
            "a composição não infere atenção ou indiferença pela expressão."
        )
        shot.attention_end = "Interrupção do caminho e ressalva tipográfica"
        shot.verification = [
            "Pessoa, dispositivo e tela estão visíveis",
            "Caminho gráfico interrompido está visível",
            "A ressalva textual preserva a negação",
        ]
    return direction, {
        "status": "material_requirement_decomposed",
        "sceneId": scene.id,
        "needId": revised_need.id,
        "targetId": revised_need.target_id,
        "reason": "internal_attention_state_assigned_to_deterministic_path_and_text",
        "footageResponsibility": "observable_person_device_and_screen_only",
        "createdPathElementId": None if has_path else path_id,
        "providerSubmission": False,
    }


def _graphic_overlay_animations(duration_frames):
    """A small deterministic orbit and settled emphasis for a composited symbol."""
    last = max(1, int(duration_frames) - 1)
    quarters = sorted({0, max(1, last // 4), max(1, last // 2), max(1, (3 * last) // 4), last})
    x_values = [0.0, 16.0, 0.0, -16.0, 0.0]
    y_values = [-12.0, 0.0, 12.0, 0.0, -12.0]

    def orbit(prop, values):
        return EditorialAnimationV2(
            property=prop,
            keyframes=[
                MotionKeyframeV1(frame=frame, value=values[index], easing="ease_in_out")
                for index, frame in enumerate(quarters)
            ],
        )

    settle = min(last, 14)
    peak = min(settle - 1, 8) if settle > 1 else 0
    scale_frames = sorted({0, peak, settle})
    scale_by_frame = {0: 0.92, peak: 1.04, settle: 1.0}
    return [
        orbit("position_x", x_values),
        orbit("position_y", y_values),
        EditorialAnimationV2(
            property="scale_x",
            keyframes=[
                MotionKeyframeV1(frame=frame, value=scale_by_frame[frame], easing="ease_out")
                for frame in scale_frames
            ],
        ),
        EditorialAnimationV2(
            property="scale_y",
            keyframes=[
                MotionKeyframeV1(frame=frame, value=scale_by_frame[frame], easing="ease_out")
                for frame in scale_frames
            ],
        ),
    ]


def _retained_footage_criteria(need):
    """Keep only facts that must be visible in the acquired footage.

    Exact graphics and their motion are owned by the deterministic overlay after
    decomposition, so they must not continue to reject otherwise valid footage.
    """
    return [
        criterion
        for criterion in need.acceptance_criteria
        if not _contains_any(criterion, (*GRAPHIC_TERMS, *MOTION_TERMS))
    ]


def _inspection_support_is_admissible(result, minimum=0.9):
    """Accept calibrated confidence or the bounded all-supported local rule, never a fake probability."""
    if result.get("confidenceKind") == "uncalibrated_rule" and result.get("confidence") is None:
        criteria = result.get("criteria", [])
        return bool(criteria) and all(item.get("result") == "supported" for item in criteria)
    confidence = result.get("confidence")
    return (
        result.get("confidenceKind", "model_reported") in {"calibrated", "model_reported"}
        and isinstance(confidence, (int, float))
        and confidence >= minimum
    )


def _duration_only_rejection(receipt, need, asset):
    if receipt.get("status") != "requires_alternative" or need.kind != "video" or not need.duration_seconds:
        return False
    result = receipt.get("result", {})
    criteria = result.get("criteria", [])
    duration_us = (
        (asset.object_metadata or {})
        .get("editingResource", {})
        .get("technical", {})
        .get("durationMicroseconds", 0)
    )
    return (
        _inspection_support_is_admissible(result, 0.9)
        and criteria
        and all(item.get("result") == "supported" for item in criteria)
        and duration_us / 1_000_000 >= need.duration_seconds
        and receipt.get("request", {}).get("requiredSeconds", 0) > need.duration_seconds
    )


def _technical_duration_reconciliation(receipt, need, asset):
    """Resolve only duration findings with ffprobe evidence, never semantics."""
    if receipt.get("status") != "requires_alternative" or need.kind != "video":
        return False
    request = receipt.get("request", {})
    result = receipt.get("result", {})
    criteria = request.get("criteria", [])
    findings = result.get("criteria", [])
    if (
        not _inspection_support_is_admissible(result, 0.85)
        or len(findings) != len(criteria)
        or not any(item.get("result") == "supported" for item in findings)
    ):
        return False
    duration_terms = ("duration", "duração", "duracao", "tempo suficiente", "length")
    unresolved = []
    for item in findings:
        if item.get("result") == "supported":
            continue
        index = item.get("index")
        if not isinstance(index, int) or not 0 <= index < len(criteria):
            return False
        unresolved.append(criteria[index])
    if not unresolved or any(not _contains_any(criterion, duration_terms) for criterion in unresolved):
        return False
    duration_us = (
        (asset.object_metadata or {})
        .get("editingResource", {})
        .get("technical", {})
        .get("durationMicroseconds", 0)
    )
    required_seconds = float(request.get("requiredSeconds", 0))
    return duration_us / 1_000_000 >= required_seconds


def _decompose_rejected_stock_graphic(plan, requirement, need, state, work):
    """Split a composite stock request into footage plus a registered overlay.

    Stock providers rarely contain an exact icon, logo or message already
    embedded in the requested real-world action. After three pixel-inspected
    rejections, preserve the real action as footage and move the exact graphic
    into a separately acquired transparent element. Both needs remain bound to
    the original blueprint requirement, so this is a composition repair rather
    than a relaxation of what the final scene must show.
    """
    if (
        need.kind != "video"
        or need.source_class != "licensed_stock"
        or int(work.get("searchRevision", 0)) < 1
    ):
        return None
    rejected = [
        receipt
        for receipt in state.get("materialHistory", [])
        if receipt.get("needId") == need.id and receipt.get("status") == "requires_alternative"
    ]
    if len(rejected) < MAX_INSPECTED_CANDIDATES_PER_NEED:
        return None
    query = str(need.query or "")
    normalized = query.casefold()
    matched = next((term for term in GRAPHIC_TERMS if term in normalized), None)
    if not matched:
        return None
    scene = next((item for item in plan.direction.scenes if item.id == requirement["sceneId"]), None)
    if scene is None or any(element.id == f"{need.target_id}-graphic-overlay" for element in scene.elements):
        return None
    target = next((element for element in scene.elements if element.id == need.target_id), None)
    if target is None:
        return None

    graphic_pattern = r"(?:idea|message|brand|lightbulb|network)?\s*(?:icon|icone|ícone|logo|symbol|simbolo|símbolo)"
    graphic_match = re.search(graphic_pattern, query, flags=re.IGNORECASE)
    graphic_query = graphic_match.group(0).strip() if graphic_match else matched
    base_query = re.split(
        r"\b(?:with|showing|displaying|containing)\b",
        query.split(",", 1)[0],
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0].strip(" ,.;")
    retained_criteria = _retained_footage_criteria(need)
    if not base_query or not retained_criteria:
        return None

    revised = plan.direction.model_copy(deep=True)
    revised_scene = next(item for item in revised.scenes if item.id == scene.id)
    revised_need = next(item for item in revised_scene.material_needs if item.id == need.id)
    revised_need.query = base_query[:500]
    # The accepted criterion becomes the exact pixel-level subject.  Broader
    # art direction is fulfilled by the overlay and final composition.
    revised_need.visual_description = retained_criteria[0][:2000]
    revised_need.entity = base_query[:500]
    revised_need.action = ""
    revised_need.appearance = ""
    revised_need.acceptance_criteria = retained_criteria[:30]
    revised_need.post_processing = [
        operation for operation in revised_need.post_processing if operation != "remove_background"
    ]

    overlay_id = f"{need.target_id}-graphic-overlay"[:80]
    overlay_size = max(96.0, min(float(target.width), float(target.height)) * 0.24)
    revised_scene.elements.append(
        EditorialElementV2(
            id=overlay_id,
            kind="image",
            purpose="Representar com precisão o elemento gráfico separado da filmagem",
            visual_role="accent",
            alignment=EditorialAlignmentV2(
                target_id=target.id,
                horizontal="center",
                vertical="middle",
            ),
            x=0,
            y=0,
            width=overlay_size,
            height=overlay_size,
            start_frame=target.start_frame,
            duration_frames=target.duration_frames,
            object_fit="contain",
            animations=_graphic_overlay_animations(target.duration_frames),
        )
    )
    revised_scene.material_needs.append(
        EditorialMaterialV2(
            id=f"{need.id}-graphic-overlay"[:80],
            target_id=overlay_id,
            kind="image",
            query=graphic_query[:500],
            purpose="Fornecer o elemento gráfico exato que o stock não continha",
            required=True,
            source_class="catalog",
            visual_description=graphic_query,
            alpha_required=True,
            fallback_behavior="block",
            acceptance_criteria=[f"O componente representa {graphic_query}"],
            blueprint_requirement_id=need.blueprint_requirement_id,
            requirement_class=need.requirement_class,
        )
    )
    return revised, {
        "sceneId": scene.id,
        "needId": need.id,
        "reason": "composite_stock_requirement_decomposed",
        "footageQuery": base_query,
        "graphicQuery": graphic_query,
        "overlayElementId": overlay_id,
        "providerSubmission": False,
    }


def _harden_existing_stock_graphic_decomposition(plan, requirement, need):
    """Migrate a v2.5 decomposition to executable footage + graphic motion."""
    if need.kind != "video" or need.source_class != "licensed_stock":
        return None
    scene = next((item for item in plan.direction.scenes if item.id == requirement["sceneId"]), None)
    if scene is None:
        return None
    overlay_id = f"{need.target_id}-graphic-overlay"[:80]
    overlay = next((element for element in scene.elements if element.id == overlay_id), None)
    overlay_need = next(
        (item for item in scene.material_needs if item.target_id == overlay_id),
        None,
    )
    target = next((element for element in scene.elements if element.id == need.target_id), None)
    if overlay is None or overlay_need is None or target is None:
        return None
    retained = _retained_footage_criteria(need)
    if not retained:
        return None
    expected_alignment = EditorialAlignmentV2(
        target_id=target.id,
        horizontal="center",
        vertical="middle",
    )
    needs_repair = (
        retained != need.acceptance_criteria
        or need.visual_description != retained[0]
        or bool(need.action or need.appearance)
        or overlay.alignment != expected_alignment
        or not overlay.animations
    )
    if not needs_repair:
        return None

    revised = plan.direction.model_copy(deep=True)
    revised_scene = next(item for item in revised.scenes if item.id == scene.id)
    revised_need = next(item for item in revised_scene.material_needs if item.id == need.id)
    revised_target = next(item for item in revised_scene.elements if item.id == need.target_id)
    revised_overlay = next(item for item in revised_scene.elements if item.id == overlay_id)
    base_query = re.sub(
        r"\b(?:slow|smooth|suave|lento|fluido|fluid)?\s*(?:circular\s+)?(?:movement|motion|movimento)\b",
        "",
        str(need.query or ""),
        flags=re.IGNORECASE,
    )
    base_query = re.sub(r"\s+", " ", base_query).strip(" ,.;")
    revised_need.query = (base_query or retained[0])[:500]
    revised_need.visual_description = retained[0][:2000]
    revised_need.entity = revised_need.query
    revised_need.action = ""
    revised_need.appearance = ""
    revised_need.acceptance_criteria = retained[:30]
    revised_need.post_processing = [
        operation for operation in revised_need.post_processing if operation != "remove_background"
    ]
    revised_overlay.alignment = EditorialAlignmentV2(
        target_id=revised_target.id,
        horizontal="center",
        vertical="middle",
    )
    revised_overlay.x = 0
    revised_overlay.y = 0
    revised_overlay.animations = _graphic_overlay_animations(revised_target.duration_frames)
    return revised, {
        "sceneId": scene.id,
        "needId": need.id,
        "reason": "decomposed_overlay_execution_hardened",
        "footageCriteria": retained,
        "overlayElementId": overlay_id,
        "providerSubmission": False,
    }


def _harden_composed_stock_requirement(plan, requirement, need):
    """Keep stock criteria intrinsic when motion/graphics already exist in-scene."""
    if need.kind != "video" or need.source_class != "licensed_stock":
        return None
    retained = _retained_footage_criteria(need)
    if not retained or retained == need.acceptance_criteria:
        return None
    scene = next((item for item in plan.direction.scenes if item.id == requirement["sceneId"]), None)
    if scene is None:
        return None
    composed_overlay = any(
        element.id != need.target_id
        and element.kind in {"shape", "path", "text", "card"}
        and (element.animations or element.motion_cues)
        for element in scene.elements
    )
    if not composed_overlay:
        return None
    revised = plan.direction.model_copy(deep=True)
    revised_scene = next(item for item in revised.scenes if item.id == scene.id)
    revised_need = next(item for item in revised_scene.material_needs if item.id == need.id)
    base_query = str(need.query or "")
    base_query = re.sub(
        r"\b(?:slow|smooth|suave|lento|fluido|fluid)?\s*(?:circular\s+)?(?:movement|motion|movimento)\b",
        "",
        base_query,
        flags=re.IGNORECASE,
    )
    base_query = re.sub(
        r"\b(?:circular\s+)?(?:slow|smooth|suave|lento|fluido|fluid)\b",
        "",
        base_query,
        flags=re.IGNORECASE,
    )
    base_query = re.sub(r"\s+", " ", base_query).strip(" ,.;")
    revised_need.query = (base_query or retained[0])[:500]
    revised_need.visual_description = retained[0][:2000]
    revised_need.entity = revised_need.query
    revised_need.action = ""
    revised_need.appearance = ""
    revised_need.acceptance_criteria = retained[:30]
    revised_need.post_processing = [
        operation for operation in revised_need.post_processing if operation != "remove_background"
    ]
    return revised, {
        "sceneId": scene.id,
        "needId": need.id,
        "reason": "composed_stock_requirement_hardened",
        "footageQuery": revised_need.query,
        "footageCriteria": retained,
        "providerSubmission": False,
    }


def _harden_format_transformation_footage(plan, requirement, need):
    """Keep stock responsible for context while the component performs transformation."""
    if need.kind != "video" or need.source_class != "licensed_stock":
        return None
    scene = next((item for item in plan.direction.scenes if item.id == requirement["sceneId"]), None)
    if scene is None:
        return None
    composition = next(
        (
            item
            for item in scene.compositions
            if item.family == "format_transformation" and need.target_id in item.target_ids
        ),
        None,
    )
    if composition is None:
        return None
    retained = [
        criterion
        for criterion in need.acceptance_criteria
        if not _contains_any(criterion, (*FORMAT_TRANSFORMATION_TERMS, *MOTION_TERMS))
    ]
    if not retained:
        return None
    needs_repair = (
        retained != need.acceptance_criteria
        or need.visual_description != retained[0]
        or bool(need.action or need.appearance)
    )
    if not needs_repair:
        return None
    revised = plan.direction.model_copy(deep=True)
    revised_scene = next(item for item in revised.scenes if item.id == scene.id)
    for revised_need in revised_scene.material_needs:
        if (
            revised_need.blueprint_requirement_id == need.blueprint_requirement_id
            and revised_need.target_id in composition.target_ids
        ):
            revised_need.query = "people using digital devices"[:500]
            revised_need.visual_description = retained[0][:2000]
            revised_need.entity = "digital devices"
            revised_need.action = ""
            revised_need.appearance = ""
            revised_need.acceptance_criteria = retained[:30]
    return revised, {
        "sceneId": scene.id,
        "needId": need.id,
        "reason": "format_transformation_execution_decomposed",
        "footageCriteria": retained,
        "componentId": composition.id,
        "componentOwns": ["message_adaptation", "viewport_change", "continuous_transition"],
        "providerSubmission": False,
    }


def _project_decomposed_visual_evidence(db, workspace_id, state, plan, scene, need):
    """Reuse checksum-bound pixel evidence after an explicit decomposition.

    The projection is deliberately narrow: every remaining footage criterion
    must already have a supported finding in the old inspection, the old
    inspection must cover the requested interval, and its confidence must meet
    the normal acceptance threshold.  Removed icon/motion criteria are not
    promoted; they are implemented and audited in the overlay composition.
    """
    if not any(
        item.get("needId") == need.id
        and item.get("reason") in {
            "composite_stock_requirement_decomposed",
            "decomposed_overlay_execution_hardened",
            "composed_stock_requirement_hardened",
        }
        for item in state.get("materialHistory", [])
    ):
        return None
    if not need.acceptance_criteria or need.visual_description != need.acceptance_criteria[0]:
        return None
    target = next((element for element in scene.elements if element.id == need.target_id), None)
    if target is None:
        return None
    required_seconds = (
        target.duration_frames
        * plan.direction.frame_rate.denominator
        / plan.direction.frame_rate.numerator
    )
    if need.duration_seconds is not None:
        required_seconds = min(required_seconds, need.duration_seconds)

    for previous in reversed(state.get("materialHistory", [])):
        if previous.get("needId") != need.id or previous.get("status") != "requires_alternative":
            continue
        result = previous.get("result", {})
        request = previous.get("request", {})
        if (
            not _inspection_support_is_admissible(result, 0.9)
            or float(request.get("requiredSeconds", 0)) < required_seconds
            or float(request.get("sourceStartSeconds", 0)) != float(target.source_start_seconds)
        ):
            continue
        old_criteria = request.get("criteria", [])
        findings = {
            str(old_criteria[item.get("index")]).strip().casefold(): item
            for item in result.get("criteria", [])
            if isinstance(item.get("index"), int) and 0 <= item["index"] < len(old_criteria)
        }
        matched = []
        for criterion in need.acceptance_criteria:
            finding = findings.get(criterion.strip().casefold())
            if not finding or finding.get("result") != "supported":
                matched = []
                break
            matched.append(finding)
        if not matched:
            continue
        asset = db.get(LibraryAsset, previous.get("assetId"))
        if (
            not asset
            or asset.workspace_id != workspace_id
            or asset.lifecycle_status != "active"
            or asset.checksum_sha256 != previous.get("checksum")
        ):
            continue
        projected_criteria = material_inspection_criteria(need)
        evidence = matched[0]
        projected_findings = [
            {
                "index": index,
                "result": "supported",
                "evidence": (
                    "Projected from the prior checksum-bound pixel inspection after the "
                    f"graphic requirement was decomposed: {evidence.get('evidence', '')}"
                )[:1000],
                "sampleIndices": evidence.get("sampleIndices", [0]),
            }
            for index, _criterion in enumerate(projected_criteria)
        ]
        receipt = {
            "status": "accepted",
            "assetId": asset.id,
            "checksum": asset.checksum_sha256,
            "needId": need.id,
            "sceneId": scene.id,
            "blueprintRequirementId": need.blueprint_requirement_id,
            "request": {
                "assetId": asset.id,
                "checksum": asset.checksum_sha256,
                "purpose": need.purpose,
                "criteria": projected_criteria,
                "requiredSeconds": required_seconds,
                "sourceStartSeconds": target.source_start_seconds,
                "maxSamples": max(6, min(18, len(previous.get("samples", [])) or 6)),
            },
            "samplingCoverage": previous.get("samplingCoverage", {}),
            "samples": previous.get("samples", []),
            "coverage": previous.get("coverage", "sampled"),
            "result": {
                "description": "Existing pixel evidence projected onto the decomposed footage-only need.",
                "criteria": projected_findings,
                "confidence": result.get("confidence"),
                "uncertainty": (
                    "This receipt validates only the retained footage subject. "
                    "Graphic identity and motion remain separate render-time checks."
                ),
            },
            "humanReview": "pending",
            "projection": {
                "version": "res.material-evidence-projection.v1",
                "sourceJobId": previous.get("jobId"),
                "sourceChecksum": previous.get("checksum"),
                "reason": "requirement_decomposed_without_new_pixel_claims",
                "providerSubmission": False,
            },
        }
        return asset, receipt
    return None


def _project_equivalent_visual_evidence(db, workspace_id, state, plan, scene, need):
    """Reuse an accepted inspection for an exactly equivalent material need."""
    target = next((element for element in scene.elements if element.id == need.target_id), None)
    if target is None:
        return None
    criteria = material_inspection_criteria(need)
    required_seconds = (
        target.duration_frames
        * plan.direction.frame_rate.denominator
        / plan.direction.frame_rate.numerator
    )
    if need.kind == "video" and need.duration_seconds is not None:
        required_seconds = min(required_seconds, need.duration_seconds)
    for previous in reversed(state.get("materialHistory", [])):
        request = previous.get("request", {})
        if (
            previous.get("status") != "accepted"
            or previous.get("needId") == need.id
            or previous.get("blueprintRequirementId") != need.blueprint_requirement_id
            or request.get("purpose") != need.purpose
            or request.get("criteria") != criteria
            or float(request.get("requiredSeconds", 0)) < required_seconds
            or float(request.get("sourceStartSeconds", 0)) != float(target.source_start_seconds)
        ):
            continue
        asset = db.get(LibraryAsset, previous.get("assetId"))
        if (
            not asset
            or asset.workspace_id != workspace_id
            or asset.lifecycle_status != "active"
            or asset.checksum_sha256 != previous.get("checksum")
        ):
            continue
        receipt = {
            **previous,
            "needId": need.id,
            "sceneId": scene.id,
            "request": {
                **request,
                "requiredSeconds": required_seconds,
                "sourceStartSeconds": target.source_start_seconds,
            },
            "projection": {
                "version": "res.material-equivalent-evidence.v1",
                "sourceNeedId": previous.get("needId"),
                "sourceChecksum": previous.get("checksum"),
                "reason": "same_blueprint_purpose_criteria_and_source_interval",
                "providerSubmission": False,
            },
        }
        return asset, receipt
    return None


def _project_checksum_bound_supported_facets(db, workspace_id, state, plan, scene, need):
    """Deprecated unsafe projection kept as a compatibility symbol.

    A checksum proves file identity, not semantic entailment.  Reusing broad
    lexical facets allowed observations such as "person using a phone" to
    certify a different claim such as "person ignoring the content".  Exact
    criteria, source interval and blueprint bindings are handled by
    ``_project_equivalent_visual_evidence``; every other requirement must be
    inspected again.
    """

    return None


def _reconcile_historical_duration_evidence(db, workspace_id, state, need):
    for previous in reversed(state.get("materialHistory", [])):
        if previous.get("needId") != need.id or previous.get("status") != "requires_alternative":
            continue
        asset = db.get(LibraryAsset, previous.get("assetId"))
        if (
            not asset
            or asset.workspace_id != workspace_id
            or asset.lifecycle_status != "active"
            or asset.checksum_sha256 != previous.get("checksum")
            or not _technical_duration_reconciliation(previous, need, asset)
        ):
            continue
        receipt = {
            **previous,
            "status": "accepted",
            "reconciliation": {
                "version": "res.material-duration-evidence.v1",
                "reason": "semantic_pixels_supported_duration_verified_by_ffprobe",
                "technicalDurationMicroseconds": (
                    (asset.object_metadata or {})
                    .get("editingResource", {})
                    .get("technical", {})
                    .get("durationMicroseconds", 0)
                ),
                "providerSubmission": False,
            },
        }
        return asset, receipt
    return None


def _reuse_historical_accepted_evidence(db, workspace_id, state, plan, scene, need):
    """Rebind a previously accepted need after another need reused its asset."""
    target = next((element for element in scene.elements if element.id == need.target_id), None)
    if target is None:
        return None
    criteria = material_inspection_criteria(need)
    required_seconds = (
        target.duration_frames
        * plan.direction.frame_rate.denominator
        / plan.direction.frame_rate.numerator
    )
    if need.kind == "video" and need.duration_seconds is not None:
        required_seconds = min(required_seconds, need.duration_seconds)
    for previous in reversed(state.get("materialHistory", [])):
        request = previous.get("request", {})
        if (
            previous.get("status") != "accepted"
            or (
                previous.get("needId") is not None
                and previous.get("needId") != need.id
            )
            or request.get("purpose") != need.purpose
            or request.get("criteria") != criteria
            or float(request.get("requiredSeconds", 0)) < required_seconds
            or float(request.get("sourceStartSeconds", 0)) != float(target.source_start_seconds)
        ):
            continue
        asset = db.get(LibraryAsset, previous.get("assetId"))
        if (
            not asset
            or asset.workspace_id != workspace_id
            or asset.lifecycle_status != "active"
            or asset.checksum_sha256 != previous.get("checksum")
        ):
            continue
        return asset, {
            **previous,
            "projection": {
                "version": "res.material-accepted-evidence-rebind.v1",
                "sourceChecksum": previous.get("checksum"),
                "reason": "same_need_contract_rebound_after_shared_asset_metadata_changed",
                "providerSubmission": False,
            },
        }
    return None


def _material_acquisition_with_receipt(asset, receipt):
    """Persist need-scoped evidence without erasing another need's receipt."""
    metadata = asset.object_metadata or {}
    acquisition = metadata.get("materialAcquisition", {})
    receipts = list(acquisition.get("inspectionReceipts") or [])
    legacy = acquisition.get("inspectionReceipt")
    if legacy:
        receipts.append(legacy)
    identity = (
        receipt.get("checksum"),
        receipt.get("request", {}).get("purpose"),
        tuple(receipt.get("request", {}).get("criteria") or []),
        receipt.get("request", {}).get("sourceStartSeconds", 0),
        receipt.get("request", {}).get("requiredSeconds", 0),
    )
    deduplicated = []
    for item in [*receipts, receipt]:
        item_identity = (
            item.get("checksum"),
            item.get("request", {}).get("purpose"),
            tuple(item.get("request", {}).get("criteria") or []),
            item.get("request", {}).get("sourceStartSeconds", 0),
            item.get("request", {}).get("requiredSeconds", 0),
        )
        if item_identity == identity:
            deduplicated = [
                existing
                for existing in deduplicated
                if (
                    existing.get("checksum"),
                    existing.get("request", {}).get("purpose"),
                    tuple(existing.get("request", {}).get("criteria") or []),
                    existing.get("request", {}).get("sourceStartSeconds", 0),
                    existing.get("request", {}).get("requiredSeconds", 0),
                )
                != identity
            ]
        deduplicated.append(item)
    return {
        **metadata,
        "visualReview": "passed",
        "materialAcquisition": {
            **acquisition,
            "status": "inspected",
            "inspectionReceipt": receipt,
            "inspectionReceipts": deduplicated,
            "humanReview": "pending",
        },
    }


def _replan_after_material_rejections(state, plan, requirement, need, work):
    """Ask the director for a different *scene*, preserving the rest of the plan.

    Repeatedly inspecting weak search matches spends budget without adding evidence.
    A scene revision is bounded by the production correction budget and remains
    subject to the same material checks as the original plan.
    """
    if int(state.get("correctionRounds", 0)) >= 2 or int(work.get("attempt", 0)) < MAX_INSPECTED_CANDIDATES_PER_NEED:
        return False
    rejected = [
        receipt for receipt in state.get("materialHistory", [])
        if (
            receipt.get("needId") == need.id
            or (
                not receipt.get("needId")
                and receipt.get("request", {}).get("purpose") == need.purpose
            )
        )
        and receipt.get("status") == "requires_alternative"
    ]
    if len(rejected) < MAX_INSPECTED_CANDIDATES_PER_NEED:
        return False
    reasons = []
    for receipt in rejected[-MAX_INSPECTED_CANDIDATES_PER_NEED:]:
        for item in receipt.get("result", {}).get("criteria", []):
            if item.get("result") != "supported":
                reasons.append(str(item.get("evidence") or item.get("reason") or "visual evidence absent")[:300])
    instruction = (
        "Replan this scene because autonomous stock acquisition could not verify "
        "the mandatory material. Keep the script, facts, negations, duration, and "
        "other scenes unchanged. Choose a demonstrable visual route whose required "
        "materials are realistically obtainable, or an executable procedural "
        "demonstration when it genuinely explains the message. Do not merely "
        "weaken inspection criteria or silently replace required footage with icons. "
        f"Failed requirement: {need.visual_description or need.query}. "
        f"Observed rejections: {'; '.join(dict.fromkeys(reasons))[:900]}."
    )
    state["history"] = [
        *state.get("history", []),
        {
            "jobs": state.get("jobs", {}),
            "artifacts": state.get("artifacts", {}),
            "revision": state.get("revision"),
            "materialFailure": {
                "sceneId": requirement["sceneId"],
                "needId": need.id,
                "inspectedCandidates": int(work.get("attempt", 0)),
                "reason": "material_semantics_unverified",
            },
        },
    ]
    state["revisionRequest"] = {
        "original": plan.direction.model_dump(mode="json", by_alias=True),
        "sceneIds": [requirement["sceneId"]],
        "instruction": instruction,
    }
    state["jobs"] = {
        key: value for key, value in state.get("jobs", {}).items()
        if key not in {"composition", "animatic", "render", "critique"}
    }
    state.update(
        stage="composition", status="pending", blockers=[],
        correctionRounds=int(state.get("correctionRounds", 0)) + 1,
    )
    return True


def _retry_material_discovery(state, requirement, need, work, token):
    """Run one bounded, local search reformulation before replanning a scene.

    Candidate rejection is an acquisition finding, not evidence that the scene
    concept itself is wrong.  Keep the acceptance criteria unchanged and use a
    shorter entity/action query so verbose art direction does not dominate a
    stock provider's search.  Previously inspected provider items are excluded.
    """
    if int(work.get("searchRevision", 0)) >= 1 or int(state.get("correctionRounds", 0)) >= 2:
        return False
    concise_parts = [
        str(getattr(need, field, "") or "").strip()
        for field in ("entity", "action")
    ]
    concise_query = ". ".join(dict.fromkeys(part for part in concise_parts if part))
    if not concise_query or concise_query.strip().casefold() == str(need.query).strip().casefold():
        return False

    from .material_discovery import discover_for_need
    from .material_ranking import rank_candidates

    revised_need = need.model_copy(
        update={
            "query": concise_query,
            "visual_description": concise_query,
            "appearance": "",
        }
    )
    discovery = discover_for_need(revised_need, cache={})
    ranked = rank_candidates(
        {**requirement, "discovery": discovery}, revised_need, {}
    )
    already_seen = {
        (candidate.get("provider"), candidate.get("providerId"))
        for candidate in work.get("candidates", [])[: int(work.get("attempt", 0))]
    }
    candidates = [
        candidate
        for candidate in ranked
        if (candidate.get("provider"), candidate.get("providerId")) not in already_seen
        and candidate.get("provider") not in {"gemini-image", "gemini-video", "sora-video", "local-diffusion"}
    ]
    if not candidates:
        return False

    revised_work = {
        **work,
        "candidates": candidates,
        "discovery": discovery,
        "attempt": 0,
        "searchRevision": int(work.get("searchRevision", 0)) + 1,
        "reformulatedQuery": concise_query,
    }
    revised_work.pop("jobId", None)
    revised_work.pop("assetId", None)
    revised_work.pop("receipt", None)
    revised_work.pop("budgetRetryCount", None)
    state["materialWork"] = {**state.get("materialWork", {}), token: revised_work}
    state["materialSearchCorrections"] = [
        *state.get("materialSearchCorrections", []),
        {
            "sceneId": requirement["sceneId"],
            "needId": need.id,
            "fromQuery": need.query,
            "toQuery": concise_query,
            "excludedCandidates": len(already_seen),
            "providerSubmission": False,
        },
    ]
    state.update(
        status="pending",
        blockers=[],
        correctionRounds=int(state.get("correctionRounds", 0)) + 1,
    )
    return True


def _inspection_job_state(job):
    if job.status not in {"failed", "cancelled"}:
        return "running", "production_material_inspection_pending"
    if getattr(job, "error_message", None) in {
        "editing_gemini_test_budget_exceeded",
        "production_pre_render_budget_exceeded",
    }:
        return "blocked", "production_material_inspection_budget_exceeded"
    return "blocked", "production_material_inspection_failed"


def advance_materials(db, record, state, plan, user):
    from .editorial_production import dispatch, save

    pending = [r for r in plan.material_requests if r["status"] != "resolved" and r["required"]]
    if not pending:
        return None
    requirement = pending[0]
    pair = next(
        (
            (scene, need)
            for scene in plan.direction.scenes
            for need in scene.material_needs
            if scene.id == requirement["sceneId"] and need.id == requirement["id"]
        ),
        None,
    )
    if not pair:
        raise ValueError("production_material_need_conflict")
    scene, need = pair
    token = digest(
        {
            "production": state["id"],
            "documentRevision": state.get("documentRevision", record.revision),
            "scene": scene.id,
            "need": need.model_dump(mode="json"),
        }
    )
    work = dict(state.get("materialWork", {}).get(token, {}))
    attention_decomposition = _decompose_unobservable_attention_state(
        plan, requirement, need
    )
    if attention_decomposition:
        from .contextual_editing_v2 import create_plan

        revised_direction, receipt = attention_decomposition
        revised_direction.expected_document_revision = record.revision
        revised_plan = create_plan(
            db,
            record,
            revised_direction,
            user,
            f"auto-attention-decomposition-{MATERIAL_RESOLUTION_VERSION}-{plan.id}-{need.id}",
        )
        state["artifacts"] = {
            **state["artifacts"],
            "plan": revised_plan.model_dump(mode="json", by_alias=True),
        }
        state["materialWork"] = {}
        state["materialHistory"] = [*state.get("materialHistory", []), receipt]
        state.update(status="pending", blockers=[])
        return save(db, record, user, state)
    classification = _reclassify_aesthetic_acceptance_criteria(
        plan, requirement, need, state
    )
    if classification:
        from .contextual_editing_v2 import create_plan

        revised_direction, receipt = classification
        revised_direction.expected_document_revision = record.revision
        revised_plan = create_plan(
            db,
            record,
            revised_direction,
            user,
            f"auto-material-classification-{MATERIAL_RESOLUTION_VERSION}-{plan.id}-{need.id}",
        )
        state["artifacts"] = {
            **state["artifacts"],
            "plan": revised_plan.model_dump(mode="json", by_alias=True),
        }
        state["materialWork"] = {}
        state["materialHistory"] = [*state.get("materialHistory", []), receipt]
        state.update(status="pending", blockers=[])
        return save(db, record, user, state)
    format_hardening = _harden_format_transformation_footage(plan, requirement, need)
    if format_hardening:
        from .contextual_editing_v2 import create_plan

        revised_direction, receipt = format_hardening
        revised_direction.expected_document_revision = record.revision
        revised_plan = create_plan(
            db,
            record,
            revised_direction,
            user,
            f"auto-format-material-hardening-{MATERIAL_RESOLUTION_VERSION}-{plan.id}-{need.id}",
        )
        state["artifacts"] = {
            **state["artifacts"],
            "plan": revised_plan.model_dump(mode="json", by_alias=True),
        }
        state["materialWork"] = {}
        state["materialHistory"] = [*state.get("materialHistory", []), receipt]
        state.update(status="pending", blockers=[])
        return save(db, record, user, state)
    hardening = _harden_existing_stock_graphic_decomposition(plan, requirement, need)
    if not hardening:
        hardening = _harden_composed_stock_requirement(plan, requirement, need)
    if hardening:
        from .contextual_editing_v2 import create_plan

        revised_direction, receipt = hardening
        revised_direction.expected_document_revision = record.revision
        revised_plan = create_plan(
            db,
            record,
            revised_direction,
            user,
            f"auto-material-hardening-{MATERIAL_RESOLUTION_VERSION}-{plan.id}-{need.id}",
        )
        state["artifacts"] = {
            **state["artifacts"],
            "plan": revised_plan.model_dump(mode="json", by_alias=True),
        }
        state["materialWork"] = {}
        state["materialHistory"] = [*state.get("materialHistory", []), receipt]
        state.update(status="pending", blockers=[])
        return save(db, record, user, state)
    decomposition = _decompose_rejected_stock_graphic(plan, requirement, need, state, work)
    if decomposition:
        from .contextual_editing_v2 import create_plan

        revised_direction, receipt = decomposition
        revised_direction.expected_document_revision = record.revision
        revised_plan = create_plan(
            db,
            record,
            revised_direction,
            user,
            f"auto-material-decomposition-{MATERIAL_RESOLUTION_VERSION}-{plan.id}-{need.id}",
        )
        state["artifacts"] = {
            **state["artifacts"],
            "plan": revised_plan.model_dump(mode="json", by_alias=True),
        }
        state["materialWork"] = {}
        state["materialHistory"] = [*state.get("materialHistory", []), receipt]
        state.update(status="pending", blockers=[])
        return save(db, record, user, state)
    projected = _reuse_historical_accepted_evidence(
        db, record.workspace_id, state, plan, scene, need
    ) or _project_decomposed_visual_evidence(
        db, record.workspace_id, state, plan, scene, need
    ) or _project_equivalent_visual_evidence(
        db, record.workspace_id, state, plan, scene, need
    ) or _reconcile_historical_duration_evidence(
        db, record.workspace_id, state, need
    )
    if projected:
        asset, receipt = projected
        asset.object_metadata = _material_acquisition_with_receipt(asset, receipt)
        observed_seconds = float(receipt.get("request", {}).get("requiredSeconds", 0))
        declared_seconds = float(need.duration_seconds or 0)
        if need.kind == "video" and 0 < observed_seconds < declared_seconds:
            # Reuse only the interval that was actually observed. The rest of
            # the scene remains available to procedural layers, so no unseen
            # footage is silently certified by a prior inspection.
            from .contextual_editing_v2 import create_plan

            revised_direction = plan.direction.model_copy(deep=True)
            revised_scene = next(item for item in revised_direction.scenes if item.id == scene.id)
            revised_need = next(item for item in revised_scene.material_needs if item.id == need.id)
            revised_target = next(item for item in revised_scene.elements if item.id == need.target_id)
            setattr(
                revised_target,
                {"asset": "asset_id", "font": "font_asset_id", "mask": "mask_asset_id"}[need.field],
                asset.id,
            )
            fps = revised_direction.frame_rate.numerator / revised_direction.frame_rate.denominator
            revised_target.duration_frames = min(
                revised_target.duration_frames,
                max(1, math.floor(observed_seconds * fps)),
            )
            revised_need.duration_seconds = observed_seconds
            revised_direction.expected_document_revision = record.revision
            revised = create_plan(
                db,
                record,
                revised_direction,
                user,
                (
                    f"auto-material-observed-interval-{MATERIAL_RESOLUTION_VERSION}-"
                    f"{asset.id}-{need.id}-{observed_seconds:.6f}"
                ),
            )
            receipt = {
                **receipt,
                "intervalBinding": {
                    "version": "res.material-observed-interval.v1",
                    "observedSeconds": observed_seconds,
                    "previousDeclaredSeconds": declared_seconds,
                    "providerSubmission": False,
                },
            }
            asset.object_metadata = _material_acquisition_with_receipt(asset, receipt)
        else:
            revised = select_material(
                db,
                record,
                plan.id,
                EditorialMaterialChoiceV2(
                    expected_plan_revision=plan.revision,
                    need_id=need.id,
                    asset_id=asset.id,
                ),
                user,
                f"auto-material-evidence-projection-{MATERIAL_RESOLUTION_VERSION}-{asset.id}-{need.id}",
            )
        state["artifacts"] = {
            **state["artifacts"],
            "plan": revised.model_dump(mode="json", by_alias=True),
        }
        state["materialHistory"] = [*state.get("materialHistory", []), receipt]
        state["materialWork"] = {}
        state.update(status="pending", blockers=[])
        return save(db, record, user, state)
    from .material_ranking import rank_candidates

    candidates = work.get("candidates")
    discovery = work.get("discovery") or {}
    provider_became_available = bool(
        not candidates
        and discovery.get("status") == "unconfigured"
        and get_settings().pexels_api_key
        and any(
            receipt.get("provider") == "pexels" and not receipt.get("configured")
            for receipt in discovery.get("providerReceipts", [])
        )
    )
    resolution_stale = work.get("resolutionVersion") != MATERIAL_RESOLUTION_VERSION
    if candidates is None or resolution_stale or provider_became_available:
        if resolution_stale:
            # An unpaid inspection created for an older material contract is no
            # longer authoritative and must never be dispatched by the pilot.
            work.pop("jobId", None)
            work.pop("assetId", None)
            work.pop("receipt", None)
            work.pop("budgetRetryCount", None)
        from .material_discovery import discover_for_need

        discovery = discover_for_need(need, cache={})
        candidates = rank_candidates(
            {**requirement, "discovery": discovery}, need, getattr(plan, "source_assets", {})
        )
        hybrid_policy = (
            ProductionRequestV1.model_validate(state["request"]).effective_hybrid_policy()
            if state.get("request")
            else HybridProductionPolicyV1()
        )
        from .hybrid_video import hybrid_capability_manifest

        manifest = hybrid_capability_manifest()
        generated_seen = 0
        filtered_candidates = []
        candidate_rejections = []
        for candidate in candidates:
            provider = candidate.get("provider")
            if provider not in {"local-diffusion", "sora-video", "gemini-video"}:
                filtered_candidates.append(candidate)
                continue
            profile_id = candidate.get("profileId") or candidate.get("providerId")
            candidate_policy = hybrid_policy.model_copy(
                update={"allowed_profile_ids": [profile_id] if profile_id else []}
            )
            duration = float(candidate.get("durationSeconds") or need.duration_seconds or 1)
            selection = select_hybrid_profile(
                manifest,
                candidate_policy,
                HybridSelectionRequestV1(
                    capability="generative_video",
                    operation="text_to_video",
                    duration_seconds=duration,
                    remaining_api_budget_usd=hybrid_policy.maximum_api_spend_usd,
                    use_case=getattr(need, "source_class", None) or need.purpose,
                ),
            )
            if selection.execution_binding and generated_seen < hybrid_policy.max_candidates_per_need:
                filtered_candidates.append(
                    {
                        **candidate,
                        "profileId": selection.selected_profile_id,
                        "executionBinding": selection.execution_binding.model_dump(
                            by_alias=True, mode="json"
                        ),
                        "selectionPolicy": candidate_policy.model_dump(by_alias=True, mode="json"),
                    }
                )
                generated_seen += 1
            else:
                candidate_rejections.append(
                    {"profileId": profile_id, "reasons": selection.blockers}
                )
        candidates = filtered_candidates
        work["candidates"] = candidates
        work["discovery"] = discovery
        work["resolutionVersion"] = MATERIAL_RESOLUTION_VERSION
        work["candidateRejections"] = candidate_rejections
        work["attempt"] = 0
    attempt = work.get("attempt", 0)
    if attempt >= min(len(candidates), MAX_INSPECTED_CANDIDATES_PER_NEED):
        previous_receipt = next(
            (
                receipt
                for receipt in reversed(state.get("materialHistory", []))
                if receipt.get("request", {}).get("purpose") == need.purpose
            ),
            None,
        )
        prior_asset = db.get(LibraryAsset, previous_receipt.get("assetId")) if previous_receipt else None
        if prior_asset and _duration_only_rejection(previous_receipt, need, prior_asset):
            receipt = {
                **previous_receipt,
                "status": "accepted",
                "reconciliation": {
                    "version": "res.material-duration-binding.v1",
                    "reason": "inspection_target_exceeded_declared_source_duration",
                    "declaredSeconds": need.duration_seconds,
                    "providerSubmission": False,
                },
            }
            prior_asset.object_metadata = _material_acquisition_with_receipt(
                prior_asset, receipt
            )
            revised = select_material(
                db,
                record,
                plan.id,
                EditorialMaterialChoiceV2(
                    expected_plan_revision=plan.revision,
                    need_id=need.id,
                    asset_id=prior_asset.id,
                ),
                user,
                f"auto-material-duration-binding-{MATERIAL_RESOLUTION_VERSION}-{prior_asset.id}-{need.id}",
            )
            state["artifacts"] = {**state["artifacts"], "plan": revised.model_dump(mode="json", by_alias=True)}
            state["materialHistory"] = [*state.get("materialHistory", []), receipt]
            state["materialWork"] = {
                **state.get("materialWork", {}),
                token: {**work, "assetId": prior_asset.id, "receipt": receipt},
            }
            state.update(status="pending", blockers=[])
            return save(db, record, user, state)
    if work.get("generationJobId"):
        generation = db.get(StudioGenerationJob, work["generationJobId"])
        if not generation or generation.document_id != record.id or generation.workspace_id != record.workspace_id:
            raise ValueError("production_material_generation_job_conflict")
        if generation.status == "queued" and generation.id not in state.get("dispatchedJobs", []):
            return dispatch(db, record, user, state, generation)
        if generation.status != "succeeded":
            result_status = (generation.result_payload or {}).get("status")
            state.update(
                status="blocked" if generation.status in {"failed", "cancelled"} else "running",
                blockers=[
                    "production_material_generation_" + (result_status or "pending")
                    if generation.status in {"failed", "cancelled"}
                    else "production_material_generation_pending"
                ],
            )
            return save(db, record, user, state)
        result = generation.result_payload or {}
        if generation.job_type == "scene_generation":
            admission = result.get("admission")
            if admission == "pending_visual_review":
                state.update(
                    status="blocked",
                    blockers=["production_local_generation_review_required:" + generation.id],
                )
                return save(db, record, user, state)
            if admission == "rejected":
                attempt += 1
                work = {"attempt": attempt, "candidates": candidates, "resolutionVersion": MATERIAL_RESOLUTION_VERSION}
                state["materialWork"] = {**state.get("materialWork", {}), token: work}
                state["materialHistory"] = [
                    *state.get("materialHistory", []),
                    {"provider": generation.provider, "jobId": generation.id, "status": "rejected"},
                ]
                state.update(status="pending", blockers=[])
                return save(db, record, user, state)
            if admission != "accepted" or not result.get("assetId"):
                raise ValueError("production_local_generation_admission_conflict")
        asset = db.get(LibraryAsset, result.get("assetId"))
        result_checksum = result.get("checksumSha256") or (result.get("candidate") or {}).get("checksumSha256")
        if (
            not asset
            or asset.workspace_id != record.workspace_id
            or asset.lifecycle_status != "active"
            or asset.checksum_sha256 != result_checksum
            or record.revision
            != generation.request_payload.get(
                "documentRevision", generation.request_payload.get("sourceDocumentRevision")
            )
        ):
            raise ValueError("production_material_generation_result_conflict")
        work["generatedAssetId"] = asset.id
        work["generationReceipt"] = {
            "provider": generation.provider,
            "jobId": generation.id,
            "assetId": asset.id,
            "checksum": asset.checksum_sha256,
            "official": False,
            "classification": "generated_original",
            "usage": result.get("usage", {}),
            "reservationUsd": result.get("testReservationUsd", 0),
        }
        work.pop("generationJobId", None)
    if work.get("jobId"):
        job = db.get(StudioGenerationJob, work["jobId"])
        if not job or job.document_id != record.id or job.workspace_id != record.workspace_id:
            raise ValueError("production_material_job_conflict")
        if job.status == "queued" and job.id not in state.get("dispatchedJobs", []):
            return dispatch(db, record, user, state, job)
        if job.status != "succeeded":
            # A bounded inspection can finish every required verdict and be
            # truncated only in its final optional uncertainty note.  Replay
            # that immutable response once through the stricter local parser;
            # no provider request or new reservation is made.
            payload = getattr(job, "result_payload", None) or {}
            replay_key = (
                f"{payload.get('responseKey')}:material-inspection-tail-v1"
                if payload.get("responseKey")
                else None
            )
            if (
                job.status in {"failed", "retrying"}
                and getattr(job, "error_message", None) == "editing_ai_incomplete_response"
                and replay_key
                and not payload.get("providerOperationId")
                and replay_key not in state.get("materialInspectionResponseReplays", [])
            ):
                from .jobs import retry_job

                payload = {**payload, "localReplayPending": True}
                job.result_payload = payload
                db.commit()
                if job.status == "failed":
                    retry_job(db, job, user.id)
                else:
                    # A retrying job is already eligible for the worker's
                    # existing retry path; forcing retrying -> queued is not a
                    # valid state transition.
                    db.refresh(job)
                state["materialInspectionResponseReplays"] = [
                    *state.get("materialInspectionResponseReplays", []),
                    replay_key,
                ]
                state["materialHistory"] = [
                    *state.get("materialHistory", []),
                    {
                        "status": "local_response_replay",
                        "jobId": job.id,
                        "responseKey": payload["responseKey"],
                        "providerSubmission": False,
                    },
                ]
                state.update(status="pending", blockers=[])
                state = save(db, record, user, state)
                return dispatch(db, record, user, state, job)
            # A reservation failure happens before provider submission. It is
            # therefore safe to recreate the inspection job after a policy
            # migration (for example, reserve spillover) without duplicating
            # a provider call. Bound the recovery to one retry per candidate.
            if (
                job.status == "failed"
                and getattr(job, "error_message", None)
                in {
                    "editing_gemini_test_budget_exceeded",
                    "production_pre_render_budget_exceeded",
                }
                and not (job.result_payload or {}).get("submissionStarted")
                and int(work.get("budgetRetryCount", 0)) < 2
            ):
                work = {
                    **work,
                    "budgetRetryCount": int(work.get("budgetRetryCount", 0)) + 1,
                }
                work.pop("jobId", None)
                state["materialWork"] = {**state.get("materialWork", {}), token: work}
                state.update(status="pending", blockers=[])
                return save(db, record, user, state)
            if (
                job.status == "failed"
                    and getattr(job, "error_message", None)
                    == "editing_submission_outcome_unknown_manual_reconciliation_required"
            ):
                candidate = candidates[attempt] if attempt < len(candidates) else {}
                inconclusive = {
                    "status": "inconclusive",
                    "reason": "inspection_submission_outcome_unknown",
                    "jobId": job.id,
                    "assetId": work.get("assetId"),
                    "provider": candidate.get("provider"),
                    "providerId": candidate.get("providerId"),
                    "reservationUsd": (job.result_payload or {}).get("testReservationUsd", 0),
                    "resubmitted": False,
                }
                work = {
                    "attempt": attempt + 1,
                    "candidates": candidates,
                    "resolutionVersion": MATERIAL_RESOLUTION_VERSION,
                    "candidateRejections": [
                        *work.get("candidateRejections", []),
                        inconclusive,
                    ],
                }
                state["materialWork"] = {**state.get("materialWork", {}), token: work}
                state["materialHistory"] = [*state.get("materialHistory", []), inconclusive]
                state.update(status="pending", blockers=[])
                return save(db, record, user, state)
            status, blocker = _inspection_job_state(job)
            state.update(status=status, blockers=[blocker])
            return save(db, record, user, state)
        receipt = {
            **job.result_payload["materialInspection"],
            "needId": need.id,
            "sceneId": scene.id,
            "blueprintRequirementId": need.blueprint_requirement_id,
        }
        asset = db.get(LibraryAsset, receipt["assetId"])
        if (
            not asset
            or asset.workspace_id != record.workspace_id
            or asset.id != work["assetId"]
            or asset.checksum_sha256 != receipt["checksum"]
            or record.revision != job.request_payload["documentRevision"]
        ):
            raise ValueError("production_material_result_conflict")
        if _technical_duration_reconciliation(receipt, need, asset):
            receipt = {
                **receipt,
                "status": "accepted",
                "reconciliation": {
                    "version": "res.material-duration-evidence.v1",
                    "reason": "semantic_pixels_supported_duration_verified_by_ffprobe",
                    "technicalDurationMicroseconds": (
                        (asset.object_metadata or {})
                        .get("editingResource", {})
                        .get("technical", {})
                        .get("durationMicroseconds", 0)
                    ),
                    "providerSubmission": False,
                },
            }
        work["receipt"] = receipt
        if receipt["status"] == "accepted":
            asset.object_metadata = _material_acquisition_with_receipt(asset, receipt)
            revised = select_material(
                db,
                record,
                plan.id,
                EditorialMaterialChoiceV2(
                    expected_plan_revision=plan.revision,
                    need_id=need.id,
                    asset_id=asset.id,
                ),
                user,
                f"auto-material-{MATERIAL_RESOLUTION_VERSION}-{job.id}",
            )
            state["artifacts"] = {**state["artifacts"], "plan": revised.model_dump(mode="json", by_alias=True)}
            state["materialHistory"] = [*state.get("materialHistory", []), receipt]
            state.update(status="pending", blockers=[])
            return save(db, record, user, state)
        state["materialHistory"] = [*state.get("materialHistory", []), receipt]
        attempt += 1
        work = {
            **work,
            "attempt": attempt,
            "candidates": candidates,
            "resolutionVersion": MATERIAL_RESOLUTION_VERSION,
        }
        work.pop("jobId", None)
        work.pop("assetId", None)
        work.pop("receipt", None)
    if attempt >= min(len(candidates), MAX_INSPECTED_CANDIDATES_PER_NEED):
        if _retry_material_discovery(state, requirement, need, work, token):
            return save(db, record, user, state)
        if _replan_after_material_rejections(state, plan, requirement, need, work):
            state["materialWork"] = {**state.get("materialWork", {}), token: work}
            return save(db, record, user, state)
        state["materialWork"] = {**state.get("materialWork", {}), token: work}
        state.update(status="blocked", blockers=["production_material_source_or_evidence_required"])
        return save(db, record, user, state)
    try:
        candidate = candidates[attempt]
        if candidate.get("catalogAssetId"):
            asset = db.get(LibraryAsset, candidate["catalogAssetId"])
            if not asset or asset.workspace_id != record.workspace_id or asset.lifecycle_status != "active":
                raise ValueError("production_material_asset_conflict")
        elif candidate.get("provider") in {"gemini-image", "gemini-video", "sora-video", "local-diffusion"}:
            if need.official_required or need.source_class == "brand_asset":
                raise ValueError("generated_material_cannot_replace_official_asset")
            if not work.get("generatedAssetId"):
                if candidate.get("provider") == "local-diffusion":
                    duration = min(
                        float(candidate.get("durationSeconds") or 1),
                        float(need.duration_seconds or 1),
                        1.0,
                    )
                    local_job, created = create_scene_generation_job(
                        db,
                        record,
                        SceneGenerationRequestV2(
                            expected_document_revision=record.revision,
                            scene_id=scene.id,
                            requirement_id=need.id,
                            prompt=(
                                f"{need.visual_description or need.query}. "
                                f"Subject: {need.entity or 'editorial subject'}. "
                                f"Observable action: {need.action or need.purpose}. "
                                f"Appearance and framing: {need.appearance or need.orientation}. "
                                "One clear action, coherent temporal motion, no text, no logo, no watermark."
                            ),
                            seed=int(token[:15], 16),
                            duration_seconds=duration,
                            profile_id=candidate["profileId"],
                            execution_binding=candidate.get("executionBinding"),
                            selection_policy=candidate.get("selectionPolicy"),
                        ),
                        user,
                        f"production:{state['id']}:local-material:{token[:16]}:{attempt}",
                    )
                    work.update(generationJobId=local_job.id, candidate=candidate)
                    state["materialWork"] = {**state.get("materialWork", {}), token: work}
                    state = save(db, record, user, state)
                    if local_job.status == "queued" and (
                        created or local_job.id not in state.get("dispatchedJobs", [])
                    ):
                        return dispatch(db, record, user, state, local_job)
                    return state
                video_candidate = candidate.get("provider") in {"sora-video", "gemini-video"}
                operation = "generate_video" if video_candidate else "generate_image"
                adapter, _ = selected_adapter(get_settings(), operation)
                generation_request = EditingAIRequestV1(
                    operation=operation,
                    expected_document_revision=record.revision,
                    duration_seconds=float(candidate.get("durationSeconds") or 4) if video_candidate else 1,
                    prompt=(
                        "Create one original silent editorial video clip. "
                        if video_candidate
                        else "Create an original editorial image. "
                    )
                    + (
                        "Do not reproduce a protected logo, film frame, "
                        "sports broadcast, or recognizable fictional character. "
                        f"Visual requirement: {need.visual_description or need.query}. "
                        f"Editorial purpose: {need.purpose}. Orientation: {need.orientation}. "
                        "No text unless the requirement explicitly asks for it."
                    ),
                    preserve=need.acceptance_criteria,
                )
                generation, _ = create_editing_job(
                    db,
                    record,
                    generation_request,
                    user,
                    f"material-generation-{MATERIAL_RESOLUTION_VERSION}-{token}-{attempt}",
                    compatible=False,
                    adapter=adapter,
                    correlation_id=state.get("id"),
                    budget_group_id=(state.get("request") or {}).get("qualityPhaseId"),
                    budget_allocations=state.get("budgetEnvelope", {}).get("allocations"),
                    budget_policy=state.get("budgetEnvelope", {}).get("policy"),
                    execution_binding=candidate.get("executionBinding"),
                    selection_policy=candidate.get("selectionPolicy"),
                )
                work.update(generationJobId=generation.id, candidate=candidate)
                state["materialWork"] = {**state.get("materialWork", {}), token: work}
                state = save(db, record, user, state)
                return dispatch(db, record, user, state, generation)
            asset = db.get(LibraryAsset, work["generatedAssetId"])
            if not asset or asset.workspace_id != record.workspace_id or asset.lifecycle_status != "active":
                raise ValueError("production_material_generated_asset_conflict")
        else:
            if candidate.get("provider") == "procedural-icon":
                from ...providers.studios.procedural_resources import discover as discover_procedural

                permitted = discover_procedural(need.query, "", need.kind).get("candidates", [])
                if not any(
                    item.get("providerId") == candidate.get("providerId") for item in permitted
                ):
                    raise ValueError("procedural_semantic_mismatch")
            acquisition_candidate = (
                {**candidate, "color": next(e.color for e in scene.elements if e.id == need.target_id)}
                if candidate.get("provider") == "procedural-icon"
                else candidate
            )
            asset = acquire_candidate(db, record.workspace_id, acquisition_candidate, need, user.id)
        if candidate.get("provider") == "procedural-sound":
            from ...providers.studios.procedural_audio import discover as discover_procedural_sound

            permitted = discover_procedural_sound(need.query, need.purpose, need.kind).get("candidates", [])
            if not any(item.get("providerId") == candidate.get("providerId") for item in permitted):
                raise ValueError("procedural_semantic_mismatch")
            audio = next(item for item in scene.audio if item.id == need.target_id)
            receipt = {
                "status": "accepted",
                "assetId": asset.id,
                "checksum": asset.checksum_sha256,
                "needId": need.id,
                "sceneId": scene.id,
                "targetId": need.target_id,
                "provider": "procedural-sound",
                "component": candidate.get("providerId"),
                "verification": "registered-component-and-decoded-audio-probe",
                "semanticEvidence": candidate.get("description", ""),
                "humanReview": "pending",
                "request": {
                    "assetId": asset.id,
                    "checksum": asset.checksum_sha256,
                    "purpose": need.purpose,
                    "requiredSeconds": audio.duration_frames
                    * plan.direction.frame_rate.denominator
                    / plan.direction.frame_rate.numerator,
                },
            }
            asset.object_metadata = _material_acquisition_with_receipt(asset, receipt)
            revised = select_material(
                db,
                record,
                plan.id,
                EditorialMaterialChoiceV2(
                    expected_plan_revision=plan.revision,
                    need_id=need.id,
                    asset_id=asset.id,
                ),
                user,
                f"auto-procedural-sound-{MATERIAL_RESOLUTION_VERSION}-{asset.id}-{need.id}",
            )
            state["artifacts"] = {**state["artifacts"], "plan": revised.model_dump(mode="json", by_alias=True)}
            state["materialHistory"] = [*state.get("materialHistory", []), receipt]
            state["materialWork"] = {
                **state.get("materialWork", {}),
                token: {**work, "assetId": asset.id, "receipt": receipt},
            }
            state.update(status="pending", blockers=[])
            return save(db, record, user, state)
        if candidate.get("provider") == "procedural-icon":
            target = next(e for e in scene.elements if e.id == need.target_id)
            required_seconds = (
                target.duration_frames * plan.direction.frame_rate.denominator / plan.direction.frame_rate.numerator
            )
            receipt = {
                "status": "accepted",
                "assetId": asset.id,
                "checksum": asset.checksum_sha256,
                "needId": need.id,
                "sceneId": scene.id,
                "targetId": need.target_id,
                "provider": "procedural-icon",
                "component": candidate.get("providerId"),
                "verification": "registered-component-and-svg-raster-validation",
                "semanticEvidence": candidate.get("description", ""),
                "humanReview": "pending",
                "request": {
                    "assetId": asset.id,
                    "checksum": asset.checksum_sha256,
                    "purpose": need.purpose,
                    "criteria": material_inspection_criteria(need),
                    "requiredSeconds": required_seconds,
                    "sourceStartSeconds": target.source_start_seconds,
                    "maxSamples": 1,
                },
            }
            asset.object_metadata = _material_acquisition_with_receipt(asset, receipt)
            revised = select_material(
                db,
                record,
                plan.id,
                EditorialMaterialChoiceV2(
                    expected_plan_revision=plan.revision,
                    need_id=need.id,
                    asset_id=asset.id,
                ),
                user,
                f"auto-procedural-material-{MATERIAL_RESOLUTION_VERSION}-{asset.id}-{need.id}",
            )
            state["artifacts"] = {**state["artifacts"], "plan": revised.model_dump(mode="json", by_alias=True)}
            state["materialHistory"] = [*state.get("materialHistory", []), receipt]
            state["materialWork"] = {
                **state.get("materialWork", {}),
                token: {**work, "assetId": asset.id, "receipt": receipt},
            }
            state.update(status="pending", blockers=[])
            return save(db, record, user, state)
        target = next(e for e in scene.elements if e.id == need.target_id)
        seconds = target.duration_frames * plan.direction.frame_rate.denominator / plan.direction.frame_rate.numerator
        if need.kind == "video" and need.duration_seconds is not None:
            seconds = min(seconds, need.duration_seconds)
        request = EditingAIRequestV1(
            operation="plan",
            expected_document_revision=record.revision,
            direction={"expectedDocumentRevision": record.revision, "intent": plan.direction.intent},
            prompt="Inspect this downloaded candidate against the editorial need using actual pixels.",
            material_inspection=MaterialInspectionRequestV1(
                asset_id=asset.id,
                checksum=asset.checksum_sha256,
                purpose=need.purpose,
                criteria=material_inspection_criteria(need),
                required_seconds=seconds,
                source_start_seconds=target.source_start_seconds,
                max_samples=18,
                evidence_kind=(
                    "temporal_sequence"
                    if need.kind == "video" and bool(need.action.strip())
                    else "static_frames"
                ),
                allowed_post_processing=need.post_processing,
            ),
        )
        inspection_job_ids = list(dict.fromkeys(state.get("materialInspectionJobIds", [])))
        inspection_scope = state.get("materialInspectionScope", {})
        if inspection_scope.get("planId") != plan.id:
            inspection_scope = {"planId": plan.id, "jobIds": []}
        scoped_inspection_job_ids = list(dict.fromkeys(inspection_scope.get("jobIds", [])))
        paid_inspection_job_ids = []
        for inspection_job_id in scoped_inspection_job_ids:
            previous_inspection = db.get(StudioGenerationJob, inspection_job_id)
            previous_result = (previous_inspection.result_payload or {}) if previous_inspection else {}
            if previous_result.get("submissionStarted") or previous_result.get("measuredCostUsd") is not None:
                paid_inspection_job_ids.append(inspection_job_id)
        if len(paid_inspection_job_ids) >= MAX_PAID_INSPECTIONS_PER_PLAN:
            state.update(
                status="blocked",
                blockers=["production_material_inspection_call_limit_reached"],
            )
            return save(db, record, user, state)
        settings = get_settings()
        adapter = (
            "local_vlm"
            if settings.studio_local_vlm_inspection_enabled
            else selected_adapter(settings, "plan")[0]
        )
        job, _ = create_editing_job(
            db,
            record,
            request,
            user,
            (
                f"material-{MATERIAL_RESOLUTION_VERSION}-{token}-{attempt}"
                + (
                    f"-search-{int(work.get('searchRevision', 0))}"
                    if int(work.get("searchRevision", 0))
                    else ""
                )
                + (
                    f"-budget-retry-{int(work.get('budgetRetryCount', 0))}"
                    if int(work.get("budgetRetryCount", 0))
                    else ""
                )
            ),
            compatible=adapter == "compatible",
            adapter=adapter,
            correlation_id=state.get("id"),
            budget_group_id=(state.get("request") or {}).get("qualityPhaseId"),
            budget_allocations=state.get("budgetEnvelope", {}).get("allocations"),
            budget_policy=state.get("budgetEnvelope", {}).get("policy"),
        )
        if job.id not in inspection_job_ids:
            state["materialInspectionJobIds"] = [*inspection_job_ids, job.id]
        if job.id not in scoped_inspection_job_ids:
            scoped_inspection_job_ids.append(job.id)
        state["materialInspectionScope"] = {
            "planId": plan.id,
            "jobIds": scoped_inspection_job_ids,
        }
        work.update(jobId=job.id, assetId=asset.id)
        state["materialWork"] = {**state.get("materialWork", {}), token: work}
        state = save(db, record, user, state)
        return dispatch(db, record, user, state, job)
    except ValueError as error:
        reason = str(error)
        if reason in RECOVERABLE_CANDIDATE_ERRORS and attempt < len(candidates):
            work["attempt"] = attempt + 1
            work["candidateRejections"] = [
                *work.get("candidateRejections", []),
                {
                    "provider": candidate.get("provider"),
                    "providerId": candidate.get("providerId"),
                    "reason": reason,
                    "stage": "acquisition_or_processing",
                },
            ]
            state["materialWork"] = {**state.get("materialWork", {}), token: work}
            state.update(status="pending", blockers=[])
            return save(db, record, user, state)
        state["materialWork"] = {**state.get("materialWork", {}), token: work}
        state.update(status="blocked", blockers=[reason])
        return save(db, record, user, state)
