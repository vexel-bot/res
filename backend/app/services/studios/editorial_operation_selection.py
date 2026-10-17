"""Eligibility checks for the first executable research-backed editing operations."""

from ...domain.studios.contextual_editing import digest
from .editing_repertoire import RESEARCH_EXECUTABLE_IDS


def evaluate_operation_bindings(direction, document):
    """Return explicit decisions; a referenced technique alone never authorizes execution."""
    assets = {asset.id: asset for asset in document.assets}
    fps = direction.frame_rate.numerator / direction.frame_rate.denominator
    decisions = []
    for scene in direction.scenes:
        elements = {element.id: element for element in scene.elements}
        bindings = {binding.technique_id: binding for binding in scene.operation_bindings}
        components = {component.component: component for component in scene.native_components}
        for identifier in scene.technique_ids:
            if identifier not in RESEARCH_EXECUTABLE_IDS:
                continue
            binding = bindings.get(identifier)
            reasons = []
            if binding is None:
                reasons.append("Vincule a técnica a elementos, âncora, motivo do corte e informação nova.")
                targets = []
            else:
                targets = [elements[target] for target in binding.target_ids]
                missing = [
                    target.id
                    for target in targets
                    if target.kind in {"image", "video"}
                    and (
                        not target.asset_id
                        or target.asset_id not in assets
                        or assets[target.asset_id].rights_status != "verified"
                    )
                ]
                if missing:
                    reasons.append("Material ausente ou sem direitos verificados: " + ", ".join(missing))
            if identifier == "action_progression" and binding:
                if len(targets) < 2 or any(target.kind != "video" for target in targets):
                    reasons.append("Progressão exige pelo menos dois trechos de vídeo com ação observável.")
                intervals = sorted(
                    (target.start_frame, target.start_frame + target.duration_frames) for target in targets
                )
                if len(intervals) < 2 or any(
                    left[1] != right[0] for left, right in zip(intervals, intervals[1:], strict=False)
                ):
                    reasons.append("Os trechos de ação precisam formar uma montagem temporal contígua.")
                shots = [shot for shot in scene.shot_plan if set(shot.target_element_ids) & set(binding.target_ids)]
                if (
                    len(shots) < 2
                    or len({shot.observable_action for shot in shots}) < 2
                    or not all(shot.cut_motivation for shot in shots)
                ):
                    reasons.append("Descreva dois estados de ação distintos no plano de tomadas.")
            elif identifier == "motif_continuity" and binding:
                if len(targets) < 2 or any(target.content_identity != binding.anchor_id for target in targets):
                    reasons.append("O motivo deve ter a mesma identidade explícita em pelo menos dois planos.")
                if len({target.start_frame for target in targets}) < 2:
                    reasons.append("O motivo precisa atravessar momentos diferentes da sequência.")
            elif identifier in {"gesture_occlusion_reveal", "moving_variant_mask"} and binding:
                component = components.get(identifier)
                if not component or set(component.target_ids) != set(binding.target_ids):
                    reasons.append("Associe a variante ao componente Remotion registrado desta técnica.")
                else:
                    references = [component.base_target_id, *component.target_ids]
                    if component.occluder_target_id:
                        references.append(component.occluder_target_id)
                    asset_ids = [elements[target].asset_id for target in references]
                    if component.occluder_target_id:
                        asset_ids.append(elements[component.occluder_target_id].mask_asset_id)
                    if any(
                        not asset_id or asset_id not in assets or assets[asset_id].rights_status != "verified"
                        for asset_id in asset_ids
                    ):
                        reasons.append("Base, variante e oclusor precisam de materiais com direitos verificados.")
            decisions.append(
                {
                    "sceneId": scene.id,
                    "techniqueId": identifier,
                    "version": 1,
                    "status": "eligible" if not reasons else "blocked",
                    "reasons": reasons,
                    "alternative": "Use uma montagem de ação simples ou forneça os materiais e vínculos exigidos.",
                    "bindingDigest": digest(binding) if binding else None,
                    "targetIds": binding.target_ids if binding else [],
                    "anchorId": binding.anchor_id if binding else None,
                    "cutMotivation": binding.cut_motivation if binding else None,
                    "newInformation": binding.new_information if binding else None,
                    "sourceRanges": [
                        {
                            "elementId": target.id,
                            "assetId": target.asset_id,
                            "startSeconds": target.source_start_seconds,
                            "endSeconds": target.source_start_seconds
                            + target.duration_frames / fps * target.playback_rate,
                        }
                        for target in targets
                        if target.kind == "video"
                    ],
                }
            )
    return decisions
