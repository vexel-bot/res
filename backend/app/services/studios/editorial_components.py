"""Registered semantic compositions lowered into the existing scene contract."""

from copy import deepcopy

from ...domain.studios.contextual_editing import digest
from ...domain.studios.contextual_editing_v2 import (
    ContextualPlanRequestV2,
    EditorialAnimationV2,
    EditorialElementV2,
    EditorialPointV2,
)
from ...domain.studios.motion import MotionKeyframeV1

VERSION = "res.editorial-components.v2.20"
REPAIR_VERSION = "res.editorial-components.repairs.v2.72"
FAMILIES = (
    "evidence",
    "comparison",
    "sequence",
    "repetition",
    "focus",
    "continuity",
    "annotated_material",
    "format_transformation",
    "demonstrative_interface",
    "continuity_comparison",
)

FAMILY_LAYOUT = {
    "annotated_material": "evidence",
    "format_transformation": "sequence",
    "demonstrative_interface": "sequence",
    "continuity_comparison": "comparison",
}


def layout_family(family):
    return FAMILY_LAYOUT.get(family, family)
NON_SEMANTIC_REPAIRS = {
    "unsourced_unreferenced_procedural_content_binding_removed",
    "action_exceeds_available_interval",
    "group_interval_expanded_to_contain_children",
    "inactive_reveal_duration_normalized",
    "radius_clamped_to_contract_limit",
    "short_hex_color_expanded",
    "camera_easing_profile_normalized",
    "deliberate_hold_profile_normalized",
    "non_hold_profile_normalized",
    "standalone_keyword_source_narrowed",
    "keyword_source_bound_to_script",
    "keyword_cue_clamped_to_scene",
    "unbound_keyword_cue_removed",
    "text_span_clamped_to_text",
    "empty_text_span_removed",
    "text_span_expanded_to_word_boundaries",
    "overlapping_text_span_removed_after_word_binding",
    "duplicate_depth_blur_removed",
    "secondary_hero_role_demoted",
    "decorative_camera_target_removed",
    "camera_target_rebound_to_primary_visual",
    "evidence_path_annotation_promoted_to_annotated_material",
    "scene_id_bound_to_storyboard_beat",
    "duplicate_semantic_target_reallocated",
    "effect_amount_clamped_to_contract_limit",
    "semantic_component_owns_motion_property",
    "explicit_animation_owns_motion_property",
    "semantic_component_owns_layout_and_base_motion",
    "hero_scaled_to_minimum_readable_area",
    "missing_element_duration_bound_to_scene",
    "empty_annotation_card_rebound_to_text_element",
    "empty_card_normalized_to_shape",
    "negative_path_points_rebased_preserving_absolute_geometry",
    "camera_intensity_clamped_to_contract_limit",
    "semantic_parameter_count_bound_to_targets",
    "shot_material_bound_to_blueprint_requirement",
    "shot_component_bound_to_registered_family",
    "final_shot_bound_to_scene_duration",
    "shot_component_rebound_after_composition_repair",
    "shot_target_interval_bound_to_shot",
    "shot_target_interval_expanded_to_shot",
    "material_tail_hold_for_shot",
    "shot_semantics_rebound_to_storyboard",
    "format_transformation_continuity_key_bound",
    "legacy_blur_moved_to_effect_stack",
    "semantic_repeat_count_defaulted",
    "deliberate_hold_intensity_normalized",
    "visual_only_composition_bounded_to_requested_duration",
    "foreign_semantic_parameters_removed",
    "self_alignment_removed",
    "per_scene_project_duration_normalized",
    "video_material_target_normalized_to_video_element",
    "shot_target_bound_to_material_requirement",
    "shared_shot_target_interval_bound",
    "format_transformation_media_states_instanced",
    "shot_target_bound_to_material_transformation_state",
    "format_transformation_overlay_timing_detached",
    "inapplicable_background_removal_removed",
    "motion_cue_global_frame_rebased",
    "motion_cue_duration_clamped_to_element",
    "shot_target_augmented_for_material_requirement",
    "annotated_material_targets_bound",
    "annotated_material_targets_ordered",
    "absolute_position_track_rebased_to_delta",
    "normalized_path_points_scaled_to_element",
    "invalid_external_alignment_removed",
    "incomplete_connector_binding_removed",
    "shot_intervals_reconciled_to_contiguous_timeline",
    "animation_frames_clamped_to_element_interval",
    "explicit_bezier_bound_to_cubic_easing",
    "path_reveal_normalized_to_element_wipe",
    "animation_reconciled_after_interval_binding",
    "motion_cue_removed_after_interval_binding",
    "motion_cue_reconciled_after_interval_binding",
    "text_span_timing_removed_after_interval_binding",
    "text_span_timing_reconciled_after_interval_binding",
    "semantic_icon_shape_promoted_to_material_need",
    "first_scene_entrance_normalized_to_cut",
    "shot_component_rebound_after_final_composition_ownership",
    "format_transformation_context_media_separated_from_shared_content",
    "shot_component_bound_to_executable_primitive",
}

MOTION_PROFILES = {
    "gentle": {"bezier": [0.22, 1.0, 0.36, 1.0], "travel": 18.0},
    "standard": {"bezier": [0.2, 0.8, 0.2, 1.0], "travel": 28.0},
    "emphasis": {"bezier": [0.22, 1.0, 0.36, 1.0], "travel": 0.0},
    "stagger": {"bezier": [0.2, 0.8, 0.2, 1.0], "travel": 24.0},
    "path_flow": {"bezier": None, "travel": 0.0},
    "deliberate_hold": {"bezier": None, "travel": 0.0},
}


def repair_hero_readability(direction, canvas_width, canvas_height, minimum_area_ratio=0.025):
    """Let the deterministic layout solver enforce the declared hero floor.

    This preserves content, aspect ratio and center. Pixel-aware inspection still
    runs later and may reject whitespace, masks or competing layers.
    """
    repairs = []
    # Registered entrance profiles can begin below scale 1. Keep bounded
    # headroom so checkpoint sampling still observes the policy minimum.
    target_area_ratio = minimum_area_ratio * 2
    minimum_area = float(canvas_width) * float(canvas_height) * target_area_ratio
    for scene in direction.scenes:
        embedded_annotations = {
            target_id
            for composition in scene.compositions
            if composition.family == "annotated_material"
            and any(
                element.id in composition.target_ids and element.kind in {"image", "video"}
                for element in scene.elements
            )
            for target_id in composition.target_ids
        }
        for element in scene.elements:
            if element.visual_role != "hero" or element.kind in {"group", "path", "text"}:
                continue
            # A graphical annotation is sized relative to its media target by
            # the registered component.  Expanding it to the global hero floor
            # turns a small marker into a full-frame blob before that relation
            # can be lowered.
            if element.id in embedded_annotations and element.kind == "shape":
                continue
            area = element.width * element.height
            if area <= 0 or area >= minimum_area:
                continue
            scale = (minimum_area / area) ** 0.5
            center_x = element.x + element.width / 2
            center_y = element.y + element.height / 2
            width = min(float(canvas_width), element.width * scale)
            height = min(float(canvas_height), element.height * scale)
            element.width = width
            element.height = height
            element.x = min(max(0.0, center_x - width / 2), float(canvas_width) - width)
            element.y = min(max(0.0, center_y - height / 2), float(canvas_height) - height)
            repairs.append(
                {
                    "sceneId": scene.id,
                    "elementId": element.id,
                    "reason": "hero_scaled_to_minimum_readable_area",
                    "minimumAreaRatio": minimum_area_ratio,
                    "targetAreaRatio": target_area_ratio,
                }
            )
    return repairs


def repair_raw_composition_contracts(payload, *, graphic_motion=False):
    """Normalize unambiguous cross-reference conflicts before Pydantic validation.

    These repairs do not invent layout or content. A target can be owned by only
    one registered composition, so the first declaration keeps ownership and a
    later declaration loses only the duplicate target. Pan/static camera cues do
    not require a semantic target; an invalid decorative target is removed while
    preserving the explicit pan vector or hold.
    """
    repairs = []
    if graphic_motion:
        # A procedural mark/path is not a sourced canonical content part.
        # Some planners emit empty content references merely to name motifs.
        # Remove only references that have no text or file AND are not used by
        # a semantic assertion or continuity operator. Never invent a source.
        references = payload.get("contentReferences", [])
        bound = {
            assertion.get("objectId")
            for scene in payload.get("scenes", [])
            for assertion in scene.get("semanticAssertions", [])
        } | {
            composition.get("continuityKey")
            for scene in payload.get("scenes", [])
            for composition in scene.get("compositions", [])
        }
        removed_parts = {}
        removable = set()
        for reference in references:
            identity = reference.get("id")
            if not identity or identity in bound:
                continue
            unsourced = {
                part.get("id") for part in reference.get("parts", [])
                if part.get("id") and not part.get("text") and not part.get("assetId")
            }
            if not unsourced:
                continue
            reference["parts"] = [
                part for part in reference["parts"] if part.get("id") not in unsourced
            ]
            removed_parts[identity] = unsourced
            if len(reference["parts"]) < 2:
                removable.add(identity)
        if removed_parts:
            payload["contentReferences"] = [
                reference for reference in references if reference.get("id") not in removable
            ]
            for scene in payload.get("scenes", []):
                scene["contentReferenceIds"] = [
                    identity for identity in scene.get("contentReferenceIds", [])
                    if identity not in removable
                ]
                for element in scene.get("elements", []):
                    reference_id = element.get("contentReferenceId")
                    if reference_id in removable or (
                        reference_id in removed_parts
                        and element.get("contentPartId") in removed_parts[reference_id]
                    ):
                        element.pop("contentReferenceId", None)
                        element.pop("contentPartId", None)
            repairs.append({
                "reason": "unsourced_unreferenced_procedural_content_binding_removed",
                "referenceIds": sorted(removable),
                "partIds": {key: sorted(value) for key, value in removed_parts.items()},
                "classification": "bounded_normalization",
                "requiresAlternative": False,
            })
    for scene_index, scene in enumerate(payload.get("scenes", [])):
        scene_duration = scene.get("durationFrames")
        if scene_index == 0 and scene.get("entrance", "cut") != "cut":
            before = scene.get("entrance")
            scene["entrance"] = "cut"
            repairs.append(
                {
                    "sceneId": scene.get("id"),
                    "reason": "first_scene_entrance_normalized_to_cut",
                    "before": before,
                    "after": "cut",
                }
            )
        elements = {element.get("id"): element for element in scene.get("elements", [])}
        # The director may mark both the source and the transformed copy as
        # heroes. A scene has one attention anchor; keep the first declared
        # hero and demote later claims instead of rejecting an otherwise
        # executable composition.
        hero_seen = False
        for element in scene.get("elements", []):
            if element.get("visualRole") != "hero":
                continue
            if hero_seen:
                element["visualRole"] = "support"
                repairs.append(
                    {
                        "sceneId": scene.get("id"),
                        "elementId": element.get("id"),
                        "reason": "multiple_hero_roles_normalized_to_single_focus",
                        "before": "hero",
                        "after": "support",
                        "classification": "bounded_normalization",
                    }
                )
            else:
                hero_seen = True
        existing_need_targets = {
            need.get("targetId") for need in scene.get("materialNeeds", []) if need.get("targetId")
        }
        # A provider may describe a recognizable icon while emitting only a
        # primitive ellipse/rectangle.  The primitive is not evidence of the
        # requested symbol.  Promote the explicit request to the registered
        # material pipeline so Lucide (or another qualified provider) supplies
        # a real, inspectable asset.  This is a direct realization of the
        # provider's declared purpose, not an invented visual treatment.
        icon_terms = ("icon", "icone", "ícone", "symbol", "simbolo", "símbolo")
        semantic_icon_terms = (
            "idea",
            "ideia",
            "lightbulb",
            "lampada",
            "lâmpada",
            "message",
            "mensagem",
            "network",
            "rede",
            "audio",
            "áudio",
            "video",
            "vídeo",
            "publico",
            "público",
            "audiencia",
            "audiência",
        )
        for element in scene.get("elements", []):
            purpose = str(element.get("purpose") or "").casefold()
            if (
                element.get("kind") != "shape"
                or element.get("assetId")
                or element.get("id") in existing_need_targets
                or not any(term in purpose for term in icon_terms)
                or not any(term in purpose for term in semantic_icon_terms)
                or any(term in purpose for term in ("logo", "marca oficial", "official brand"))
            ):
                continue
            element["kind"] = "image"
            element["objectFit"] = "contain"
            need_id = ("semantic-icon-" + str(element.get("id") or "element"))[:80]
            scene.setdefault("materialNeeds", []).append(
                {
                    "id": need_id,
                    "targetId": element.get("id"),
                    "field": "asset",
                    "kind": "image",
                    "query": ("ícone " + str(element.get("purpose") or "")).strip()[:500],
                    "purpose": str(element.get("purpose") or "Representar o símbolo solicitado")[:1000],
                    "required": True,
                    "officialRequired": False,
                    "sourceClass": "catalog",
                    "visualDescription": str(element.get("purpose") or "")[:2000],
                    "orientation": "square",
                    "alphaRequired": True,
                    "postProcessing": ["convert_to_png"],
                    "fallbackBehavior": "block",
                    "acceptanceCriteria": [
                        "O símbolo corresponde semanticamente ao conceito solicitado",
                        "O fundo permanece transparente",
                    ],
                    "requirementClass": "mandatory",
                    "preferredCriteria": [],
                }
            )
            existing_need_targets.add(element.get("id"))
            repairs.append(
                {
                    "sceneId": scene.get("id"),
                    "elementId": element.get("id"),
                    "needId": need_id,
                    "reason": "semantic_icon_shape_promoted_to_material_need",
                    "before": "shape",
                    "after": "image",
                }
            )
        for element in scene.get("elements", []):
            alignment = element.get("alignment")
            if alignment:
                target = elements.get(alignment.get("targetId"))
                if target is None or target.get("parentId") != element.get("parentId"):
                    element["alignment"] = None
                    repairs.append(
                        {
                            "sceneId": scene.get("id"),
                            "elementId": element.get("id"),
                            "reason": "invalid_external_alignment_removed",
                            "before": alignment,
                        }
                    )
            connector_from = element.get("connectorFromId")
            connector_to = element.get("connectorToId")
            if (
                bool(connector_from) != bool(connector_to)
                or (connector_from and element.get("kind") != "path")
                or (connector_from and (connector_from not in elements or connector_to not in elements))
            ):
                element["connectorFromId"] = None
                element["connectorToId"] = None
                repairs.append(
                    {
                        "sceneId": scene.get("id"),
                        "elementId": element.get("id"),
                        "reason": "incomplete_connector_binding_removed",
                        "before": [connector_from, connector_to],
                    }
                )
        for composition in scene.get("compositions", []):
            holds = composition.get("stateHoldFrames") or []
            targets = composition.get("targetIds") or []
            if holds and (
                composition.get("family") not in {"format_transformation", "sequence"}
                or len(holds) != len(targets)
                or any(not isinstance(value, int) or value < 1 for value in holds)
                or not composition.get("movementFrames")
            ):
                before = {
                    "stateHoldFrames": holds,
                    "movementFrames": composition.get("movementFrames"),
                }
                composition["stateHoldFrames"] = []
                composition["movementFrames"] = None
                repairs.append(
                    {
                        "sceneId": scene.get("id"),
                        "compositionId": composition.get("id"),
                        "reason": "invalid_state_timing_fell_back_to_action_frames",
                        "before": before,
                        "after": {"stateHoldFrames": [], "movementFrames": None},
                        "classification": "bounded_normalization",
                    }
                )
        narration_source = " ".join(
            [str(scene.get("narration") or ""), *(str(fact) for fact in scene.get("facts", []))]
        ).casefold()
        textual_content = [
            str(element.get("text") or "").casefold()
            for element in scene.get("elements", [])
            if element.get("kind") in {"text", "card"} and not element.get("afterElementId")
        ]
        keyword_cues = []
        for cue in scene.get("keywordCues", []):
            cue_text = str(cue.get("text") or "").strip()
            source_excerpt = str(cue.get("sourceExcerpt") or "").strip()
            if cue_text and cue_text.casefold() not in narration_source:
                repairs.append(
                    {
                        "sceneId": scene.get("id"),
                        "keywordCueId": cue.get("id"),
                        "reason": "unbound_keyword_cue_removed",
                        "text": cue_text,
                    }
                )
                continue
            if cue_text and source_excerpt.casefold() != cue_text.casefold():
                cue["sourceExcerpt"] = cue_text
                repairs.append(
                    {
                        "sceneId": scene.get("id"),
                        "keywordCueId": cue.get("id"),
                        "reason": (
                            "standalone_keyword_source_narrowed"
                            if not any(cue_text.casefold() in content for content in textual_content)
                            else "keyword_source_bound_to_script"
                        ),
                        "before": source_excerpt,
                        "after": cue_text,
                    }
                )
            cue_start = cue.get("startFrame")
            cue_duration = cue.get("durationFrames")
            if (
                isinstance(scene_duration, int)
                and scene_duration > 0
                and isinstance(cue_start, int)
                and isinstance(cue_duration, int)
                and cue_start >= 0
                and cue_duration > 0
                and cue_start < scene_duration
                and cue_start + cue_duration > scene_duration
            ):
                before = {"startFrame": cue_start, "durationFrames": cue_duration}
                cue["durationFrames"] = min(cue_duration, scene_duration)
                cue["startFrame"] = scene_duration - cue["durationFrames"]
                repairs.append(
                    {
                        "sceneId": scene.get("id"),
                        "keywordCueId": cue.get("id"),
                        "reason": "keyword_cue_clamped_to_scene",
                        "before": before,
                        "after": {
                            "startFrame": cue["startFrame"],
                            "durationFrames": cue["durationFrames"],
                        },
                    }
                )
            keyword_cues.append(cue)
        scene["keywordCues"] = keyword_cues
        for need in scene.get("materialNeeds", []):
            target = elements.get(need.get("targetId"))
            post_processing = list(need.get("postProcessing", []))
            if (
                need.get("kind") != "image"
                and "remove_background" in post_processing
                and not need.get("alphaRequired", False)
            ):
                need["postProcessing"] = [
                    operation for operation in post_processing if operation != "remove_background"
                ]
                repairs.append(
                    {
                        "sceneId": scene.get("id"),
                        "needId": need.get("id"),
                        "reason": "inapplicable_background_removal_removed",
                        "kind": need.get("kind"),
                    }
                )
            if (
                target
                and need.get("field", "asset") == "asset"
                and need.get("kind") == "video"
                and target.get("kind") != "video"
            ):
                before_kind = target.get("kind")
                target.update(
                    kind="video",
                    pathMode="polyline",
                    # The V2 contract keeps a typed path field on every
                    # element. A video does not draw a path, but the field
                    # still needs valid geometry for the post-normalization
                    # model validation step.
                    points=[{"x": 0.0, "y": 0.0}, {"x": 0.0, "y": 0.0}],
                    reveal="none",
                    connectorFromId=None,
                    connectorToId=None,
                    objectFit="cover",
                    sourceAudio="mute",
                )
                repairs.append(
                    {
                        "sceneId": scene.get("id"),
                        "elementId": target.get("id"),
                        "needId": need.get("id"),
                        "reason": "video_material_target_normalized_to_video_element",
                        "before": before_kind,
                        "after": "video",
                    }
                )
        # A format transformation is a sequence of viewports containing the
        # same visual material.  Models sometimes return one media target plus
        # an explanatory text target.  Keep the text as an independent overlay
        # and instantiate the media target for every requested viewport.  The
        # cloned needs deliberately retain the exact same semantic requirement,
        # allowing the material resolver to reuse the acquired and inspected
        # asset instead of downloading or inspecting it again.
        existing_ids = set(elements)
        for composition in scene.get("compositions", []):
            if composition.get("family") != "format_transformation":
                continue
            targets = list(composition.get("targetIds", []))
            target_elements = [elements.get(target_id) for target_id in targets]
            media = [
                element
                for element in target_elements
                if element is not None and element.get("kind") in {"image", "video"}
            ]
            # Footage of several devices is useful context, but the footage
            # files are not automatically the same content identity. When the
            # provider explicitly supplied a continuity key and concise copy,
            # separate those concerns: preserve every acquired clip in the
            # scene and let deterministic cards carry one shared message
            # through the requested viewports. This implements the authored
            # transformation instead of falsely certifying unrelated media as
            # one asset or degrading the action to a sequence of fades.
            needs_by_target = {
                need.get("targetId"): need
                for need in scene.get("materialNeeds", [])
                if need.get("field", "asset") == "asset"
            }
            media_need_identities = {
                (
                    needs_by_target.get(element.get("id"), {}).get("blueprintRequirementId")
                    or needs_by_target.get(element.get("id"), {}).get("id")
                )
                for element in media
                if needs_by_target.get(element.get("id"))
            }
            if (
                len(media) > 1
                and len(media) == len(target_elements)
                and len(media_need_identities) > 1
            ):
                # Distinct footage is context, not proof that one piece of
                # content survived a format change. Older code fabricated
                # empty cards from nearby copy and exposed continuityKey as
                # visible text. Preserve the authored targets so validation
                # rejects the unsupported transformation explicitly.
                continue
            if len(media) != 1 or len(media) == len(target_elements):
                continue
            source = media[0]
            content_identity = source.get("contentIdentity") or source["id"]
            source["contentIdentity"] = content_identity
            formats = list(composition.get("viewportFormats", []))
            state_count = max(2, len(formats))
            if not formats:
                formats = ["portrait", "landscape"][:state_count]
            elif state_count > len(set(formats)):
                # A transformation must visibly change the viewport.  Repeating
                # the sole format on cloned states produces two fades of the
                # same rectangle and cannot demonstrate adaptation.
                alternatives = [item for item in ("portrait", "square", "landscape") if item not in formats]
                formats = [*formats, *alternatives]
            source_needs = [
                need
                for need in scene.get("materialNeeds", [])
                if need.get("targetId") == source.get("id")
                and need.get("field", "asset") == "asset"
            ]
            state_ids = [source["id"]]
            for index in range(1, state_count):
                base_id = f"{source['id']}-format-{index + 1}"
                clone_id = base_id[:80]
                suffix = 2
                while clone_id in existing_ids:
                    tail = f"-{suffix}"
                    clone_id = base_id[: 80 - len(tail)] + tail
                    suffix += 1
                existing_ids.add(clone_id)
                clone = deepcopy(source)
                clone["id"] = clone_id
                clone["contentIdentity"] = content_identity
                # The registered component owns state timing and geometry.
                clone["parentId"] = None
                clone["alignment"] = None
                clone["afterElementId"] = None
                clone["animations"] = []
                clone["motionCues"] = []
                scene.setdefault("elements", []).append(clone)
                elements[clone_id] = clone
                state_ids.append(clone_id)
                for source_need in source_needs:
                    need_clone = deepcopy(source_need)
                    need_base_id = f"{source_need.get('id', 'material')}-format-{index + 1}"
                    need_clone["id"] = need_base_id[:80]
                    need_clone["targetId"] = clone_id
                    scene.setdefault("materialNeeds", []).append(need_clone)
            composition["targetIds"] = state_ids
            composition["viewportFormats"] = [
                formats[index % len(formats)] for index in range(state_count)
            ]
            composition["continuityKey"] = content_identity
            preserved_overlays = [target_id for target_id in targets if target_id not in state_ids]
            for overlay_id in preserved_overlays:
                overlay = elements.get(overlay_id)
                if overlay and overlay.get("afterElementId") in state_ids:
                    before = overlay.get("afterElementId")
                    overlay["afterElementId"] = None
                    repairs.append(
                        {
                            "sceneId": scene.get("id"),
                            "compositionId": composition.get("id"),
                            "elementId": overlay_id,
                            "reason": "format_transformation_overlay_timing_detached",
                            "before": before,
                            "after": None,
                        }
                    )
            repairs.append(
                {
                    "sceneId": scene.get("id"),
                    "compositionId": composition.get("id"),
                    "reason": "format_transformation_media_states_instanced",
                    "sourceElementId": source.get("id"),
                    "stateElementIds": state_ids,
                    "preservedOverlayTargetIds": preserved_overlays,
                }
            )
        for element in scene.get("elements", []):
            alignment = element.get("alignment")
            if isinstance(alignment, dict) and alignment.get("targetId") == element.get("id"):
                element["alignment"] = None
                repairs.append(
                    {
                        "sceneId": scene.get("id"),
                        "elementId": element.get("id"),
                        "reason": "self_alignment_removed",
                    }
                )
            if isinstance(scene_duration, int) and scene_duration > 1:
                if element.get("startFrame") is None:
                    element["startFrame"] = 0
                if element.get("durationFrames") is None:
                    element["durationFrames"] = scene_duration
                    repairs.append(
                        {
                            "sceneId": scene.get("id"),
                            "elementId": element.get("id"),
                            "reason": "missing_element_duration_bound_to_scene",
                            "after": scene_duration,
                        }
                    )
            text = str(element.get("text") or "")
            repaired_spans = []
            for span in element.get("textSpans", []):
                start = span.get("start")
                end = span.get("end")
                if not isinstance(start, int) or not isinstance(end, int):
                    repaired_spans.append(span)
                    continue
                clamped_end = min(end, len(text))
                if start >= clamped_end:
                    repairs.append(
                        {
                            "sceneId": scene.get("id"),
                            "elementId": element.get("id"),
                            "textSpanId": span.get("id"),
                            "reason": "empty_text_span_removed",
                            "before": [start, end],
                        }
                    )
                    continue
                if clamped_end != end:
                    span["end"] = clamped_end
                    repairs.append(
                        {
                            "sceneId": scene.get("id"),
                            "elementId": element.get("id"),
                            "textSpanId": span.get("id"),
                            "reason": "text_span_clamped_to_text",
                            "before": [start, end],
                            "after": [start, clamped_end],
                        }
                    )
                original = [start, clamped_end]
                while start > 0 and text[start - 1].isalnum() and text[start].isalnum():
                    start -= 1
                while clamped_end < len(text) and text[clamped_end - 1].isalnum() and text[clamped_end].isalnum():
                    clamped_end += 1
                if [start, clamped_end] != original:
                    span["start"], span["end"] = start, clamped_end
                    repairs.append(
                        {
                            "sceneId": scene.get("id"),
                            "elementId": element.get("id"),
                            "textSpanId": span.get("id"),
                            "reason": "text_span_expanded_to_word_boundaries",
                            "before": original,
                            "after": [start, clamped_end],
                        }
                    )
                if repaired_spans and repaired_spans[-1].get("end", 0) > start:
                    repairs.append(
                        {
                            "sceneId": scene.get("id"),
                            "elementId": element.get("id"),
                            "textSpanId": span.get("id"),
                            "reason": "overlapping_text_span_removed_after_word_binding",
                            "before": [start, clamped_end],
                        }
                    )
                    continue
                repaired_spans.append(span)
            element["textSpans"] = repaired_spans
            depth = element.get("depthTreatment") or {}
            effects = element.get("effects") or []
            effect_ranges = {
                "blur": (0, 40),
                "brightness": (0, 4),
                "contrast": (0, 4),
                "saturate": (0, 4),
                "hue_rotate": (-360, 360),
                "drop_shadow": (0, 100),
            }
            for effect in effects:
                bounds = effect_ranges.get(effect.get("kind"))
                amount = effect.get("amount")
                if bounds and isinstance(amount, (int, float)):
                    clamped = min(max(amount, bounds[0]), bounds[1])
                    if clamped != amount:
                        effect["amount"] = clamped
                        repairs.append(
                            {
                                "sceneId": scene.get("id"),
                                "elementId": element.get("id"),
                                "effectId": effect.get("id"),
                                "reason": "effect_amount_clamped_to_contract_limit",
                                "before": amount,
                                "after": clamped,
                            }
                        )
            if depth.get("blurPx", 0) and any(effect.get("kind") == "blur" for effect in effects):
                before = depth.get("blurPx")
                depth["blurPx"] = 0
                element["depthTreatment"] = depth
                repairs.append(
                    {
                        "sceneId": scene.get("id"),
                        "elementId": element.get("id"),
                        "reason": "duplicate_depth_blur_removed",
                        "before": before,
                        "after": 0,
                    }
                )
            elif depth.get("blurPx", 0) and effects:
                before = depth.get("blurPx")
                effects.append(
                    {
                        "id": f"{element.get('id', 'element')}-legacy-blur",
                        "kind": "blur",
                        "amount": before,
                    }
                )
                depth["blurPx"] = 0
                element["depthTreatment"] = depth
                element["effects"] = effects
                repairs.append(
                    {
                        "sceneId": scene.get("id"),
                        "elementId": element.get("id"),
                        "reason": "legacy_blur_moved_to_effect_stack",
                        "before": before,
                        "after": 0,
                    }
                )
            for color_key in ("color", "fill", "borderColor"):
                color = element.get(color_key)
                if isinstance(color, str) and len(color) == 4 and color.startswith("#"):
                    expanded = "#" + "".join(channel * 2 for channel in color[1:])
                    element[color_key] = expanded
                    repairs.append(
                        {
                            "sceneId": scene.get("id"),
                            "elementId": element.get("id"),
                            "reason": "short_hex_color_expanded",
                            "field": color_key,
                            "before": color,
                            "after": expanded,
                        }
                    )
            if element.get("reveal") == "none" and element.get("revealFrames", 12) < 1:
                before = element.get("revealFrames")
                element["revealFrames"] = 1
                repairs.append(
                    {
                        "sceneId": scene.get("id"),
                        "elementId": element.get("id"),
                        "reason": "inactive_reveal_duration_normalized",
                        "before": before,
                        "after": 1,
                    }
                )
            if element.get("reveal") == "path" and element.get("kind") != "path":
                before = element.get("reveal")
                element["reveal"] = "wipe"
                repairs.append(
                    {
                        "sceneId": scene.get("id"),
                        "elementId": element.get("id"),
                        "reason": "path_reveal_normalized_to_element_wipe",
                        "before": before,
                        "after": "wipe",
                    }
                )
            radius = element.get("radius")
            if isinstance(radius, (int, float)) and radius > 512:
                element["radius"] = 512
                repairs.append(
                    {
                        "sceneId": scene.get("id"),
                        "elementId": element.get("id"),
                        "reason": "radius_clamped_to_contract_limit",
                        "before": radius,
                        "after": 512,
                    }
                )
            duration = element.get("durationFrames")
            if isinstance(duration, int) and duration > 0:
                for animation in element.get("animations", []):
                    repaired_by_frame = {}
                    original_frames = []
                    for keyframe in animation.get("keyframes", []):
                        frame = keyframe.get("frame")
                        if not isinstance(frame, int):
                            continue
                        original_frames.append(frame)
                        clamped_frame = min(max(0, frame), duration - 1)
                        keyframe["frame"] = clamped_frame
                        if keyframe.get("cubicBezier") is not None and keyframe.get("easing") != "cubic_bezier":
                            keyframe["easing"] = "cubic_bezier"
                            repairs.append(
                                {
                                    "sceneId": scene.get("id"),
                                    "elementId": element.get("id"),
                                    "reason": "explicit_bezier_bound_to_cubic_easing",
                                    "frame": clamped_frame,
                                }
                            )
                        repaired_by_frame[clamped_frame] = keyframe
                    repaired_keyframes = [repaired_by_frame[frame] for frame in sorted(repaired_by_frame)]
                    if original_frames != [item.get("frame") for item in repaired_keyframes]:
                        animation["keyframes"] = repaired_keyframes
                        repairs.append(
                            {
                                "sceneId": scene.get("id"),
                                "elementId": element.get("id"),
                                "reason": "animation_frames_clamped_to_element_interval",
                                "before": original_frames,
                                "after": [item.get("frame") for item in repaired_keyframes],
                            }
                        )
            # Position tracks are deltas in MotionGraph.  Models occasionally
            # repeat the authored x/y coordinates in those tracks, which would
            # apply the base position twice.  Rebase only when every keyframe
            # clusters around the matching base coordinate and the authored
            # motion span is small enough to be an offset animation.
            for animation in element.get("animations", []):
                prop = animation.get("property")
                if prop not in {"position_x", "position_y"}:
                    continue
                base_field = "x" if prop == "position_x" else "y"
                base = element.get(base_field)
                values = [keyframe.get("value") for keyframe in animation.get("keyframes", [])]
                if (
                    isinstance(base, (int, float))
                    and values
                    and all(isinstance(value, (int, float)) for value in values)
                    and abs(sum(values) / len(values) - base) <= max(8.0, abs(base) * 0.2)
                    and max(values) - min(values)
                    <= max(
                        96.0,
                        float(element.get("width", 0)),
                        float(element.get("height", 0)),
                    )
                ):
                    before = list(values)
                    for keyframe in animation["keyframes"]:
                        keyframe["value"] = float(keyframe["value"]) - float(base)
                    repairs.append(
                        {
                            "sceneId": scene.get("id"),
                            "elementId": element.get("id"),
                            "reason": "absolute_position_track_rebased_to_delta",
                            "property": prop,
                            "before": before,
                            "after": [item["value"] for item in animation["keyframes"]],
                        }
                    )
            for cue in element.get("motionCues", []):
                element_start = element.get("startFrame", 0)
                element_duration = element.get("durationFrames")
                cue_start = cue.get("startFrame", 0)
                cue_duration = cue.get("durationFrames", 18)
                # Motion-cue frames are local to their element. Providers can
                # return the scene-global frame for an element that starts
                # later; rebase only when subtracting the element start yields
                # an interval that fits exactly inside that element.
                if (
                    isinstance(element_start, int)
                    and element_start > 0
                    and isinstance(element_duration, int)
                    and isinstance(cue_start, int)
                    and isinstance(cue_duration, int)
                    and cue_start + cue_duration > element_duration
                    and 0 <= cue_start - element_start
                    and cue_start - element_start + cue_duration <= element_duration
                ):
                    before = cue_start
                    cue["startFrame"] = cue_start - element_start
                    cue_start = cue["startFrame"]
                    repairs.append(
                        {
                            "sceneId": scene.get("id"),
                            "elementId": element.get("id"),
                            "reason": "motion_cue_global_frame_rebased",
                            "before": before,
                            "after": cue_start,
                        }
                    )
                if (
                    isinstance(element_duration, int)
                    and isinstance(cue_start, int)
                    and isinstance(cue_duration, int)
                    and cue_start < element_duration
                    and cue_start + cue_duration > element_duration
                ):
                    before = cue_duration
                    cue["durationFrames"] = element_duration - cue_start
                    repairs.append(
                        {
                            "sceneId": scene.get("id"),
                            "elementId": element.get("id"),
                            "reason": "motion_cue_duration_clamped_to_element",
                            "before": before,
                            "after": cue["durationFrames"],
                        }
                    )
                if cue.get("kind") == "deliberate_hold" and cue.get("intensity", 1) < 0.1:
                    before = cue.get("intensity")
                    cue["intensity"] = 0.1
                    repairs.append(
                        {
                            "sceneId": scene.get("id"),
                            "elementId": element.get("id"),
                            "reason": "deliberate_hold_intensity_normalized",
                            "before": before,
                            "after": 0.1,
                        }
                    )
                if cue.get("kind") == "deliberate_hold" and cue.get("profile") != "deliberate_hold":
                    before = cue.get("profile")
                    cue["profile"] = "deliberate_hold"
                    repairs.append(
                        {
                            "sceneId": scene.get("id"),
                            "elementId": element.get("id"),
                            "reason": "deliberate_hold_profile_normalized",
                            "before": before,
                            "after": "deliberate_hold",
                        }
                    )
                elif cue.get("kind") != "deliberate_hold" and cue.get("profile") == "deliberate_hold":
                    before = cue.get("profile")
                    cue["profile"] = "standard"
                    repairs.append(
                        {
                            "sceneId": scene.get("id"),
                            "elementId": element.get("id"),
                            "reason": "non_hold_profile_normalized",
                            "before": before,
                            "after": "standard",
                        }
                    )
            points = element.get("points", [])
            if element.get("kind") == "path" and points:
                xs = [point.get("x") for point in points]
                ys = [point.get("y") for point in points]
                if all(isinstance(value, (int, float)) for value in [*xs, *ys]):
                    if (
                        max(xs) <= 1
                        and max(ys) <= 1
                        and isinstance(element.get("width"), (int, float))
                        and isinstance(element.get("height"), (int, float))
                    ):
                        before = deepcopy(points)
                        for point in points:
                            point["x"] *= float(element["width"])
                            point["y"] *= float(element["height"])
                        xs = [point.get("x") for point in points]
                        ys = [point.get("y") for point in points]
                        repairs.append(
                            {
                                "sceneId": scene.get("id"),
                                "elementId": element.get("id"),
                                "reason": "normalized_path_points_scaled_to_element",
                                "before": before,
                                "after": deepcopy(points),
                            }
                        )
                    minimum_x = min(xs)
                    minimum_y = min(ys)
                    if minimum_x < 0 or minimum_y < 0:
                        element["x"] = float(element.get("x", 0)) + minimum_x
                        element["y"] = float(element.get("y", 0)) + minimum_y
                        for point in points:
                            point["x"] -= minimum_x
                            point["y"] -= minimum_y
                        repairs.append(
                            {
                                "sceneId": scene.get("id"),
                                "elementId": element.get("id"),
                                "reason": "negative_path_points_rebased_preserving_absolute_geometry",
                                "offset": [minimum_x, minimum_y],
                            }
                        )
            if element.get("kind") == "path" and element.get("pathMode") == "quadratic" and len(points) != 3:
                element["pathMode"] = "polyline"
                repairs.append(
                    {
                        "sceneId": scene.get("id"),
                        "elementId": element.get("id"),
                        "reason": "multi_point_quadratic_normalized_to_polyline",
                        "pointCount": len(points),
                    }
                )
        raw_compositions = scene.get("compositions", [])
        nonempty_text_ids = [
            element.get("id")
            for element in scene.get("elements", [])
            if element.get("kind") == "text" and str(element.get("text") or "").strip()
        ]
        for element in scene.get("elements", []):
            if element.get("kind") != "card" or str(element.get("text") or "").strip():
                continue
            for composition in raw_compositions:
                if composition.get("family") not in {"annotated_material", "evidence"}:
                    continue
                targets = composition.get("targetIds", [])
                if element.get("id") not in targets or not nonempty_text_ids:
                    continue
                replacement = nonempty_text_ids[0]
                composition["targetIds"] = [
                    replacement if target == element.get("id") else target for target in targets
                ]
                repairs.append(
                    {
                        "sceneId": scene.get("id"),
                        "compositionId": composition.get("id"),
                        "reason": "empty_annotation_card_rebound_to_text_element",
                        "before": element.get("id"),
                        "after": replacement,
                    }
                )
            element["kind"] = "shape"
            element["textSpans"] = []
            repairs.append(
                {
                    "sceneId": scene.get("id"),
                    "elementId": element.get("id"),
                    "reason": "empty_card_normalized_to_shape",
                }
            )
        for cue in scene.get("cameraCues", []):
            intensity = cue.get("intensity")
            if isinstance(intensity, (int, float)) and intensity > 0.15:
                cue["intensity"] = 0.15
                repairs.append(
                    {
                        "sceneId": scene.get("id"),
                        "cameraCueId": cue.get("id"),
                        "reason": "camera_intensity_clamped_to_contract_limit",
                        "before": intensity,
                        "after": 0.15,
                    }
                )
        for composition in raw_compositions:
            family = composition.get("family")
            if family == "annotated_material" and len(composition.get("targetIds", [])) > 2:
                before = list(composition["targetIds"])
                media = [
                    target_id
                    for target_id in before
                    if elements.get(target_id, {}).get("kind") in {"image", "video"}
                ]
                annotations = [
                    target_id
                    for target_id in before
                    if elements.get(target_id, {}).get("kind") in {"card", "text"}
                    or elements.get(target_id, {}).get("kind") in {"shape", "path"}
                ]
                base_media = next(
                    (target_id for target_id in media if elements.get(target_id, {}).get("kind") == "video"),
                    next(
                        (
                            target_id
                            for target_id in media
                            if elements.get(target_id, {}).get("visualRole") in {"hero", "background"}
                        ),
                        media[0] if media else None,
                    ),
                )
                image_annotations = [
                    target_id
                    for target_id in media
                    if target_id != base_media
                    and elements.get(target_id, {}).get("visualRole") != "background"
                ]
                if base_media and (annotations or image_annotations):
                    composition["targetIds"] = [
                        base_media,
                        *image_annotations[:1],
                        *annotations[: 3 - len(image_annotations[:1])],
                    ]
                    repairs.append(
                        {
                            "sceneId": scene.get("id"),
                            "compositionId": composition.get("id"),
                            "reason": "annotated_material_targets_ordered",
                            "before": before,
                            "after": list(composition["targetIds"]),
                        }
                    )
            foreign_parameters = (
                ("viewportFormats", "format_transformation"),
                ("interfaceEvents", "demonstrative_interface"),
            )
            for parameter, owning_family in foreign_parameters:
                values = composition.get(parameter)
                if values and family != owning_family:
                    composition[parameter] = []
                    repairs.append(
                        {
                            "sceneId": scene.get("id"),
                            "compositionId": composition.get("id"),
                            "reason": "foreign_semantic_parameters_removed",
                            "field": parameter,
                            "family": family,
                            "before": list(values),
                            "after": [],
                        }
                    )
            if composition.get("repeatCount", 3) < 2:
                before = composition.get("repeatCount")
                composition["repeatCount"] = 3
                repairs.append(
                    {
                        "sceneId": scene.get("id"),
                        "compositionId": composition.get("id"),
                        "reason": "semantic_repeat_count_defaulted",
                        "before": before,
                        "after": 3,
                    }
                )
            targets = composition.get("targetIds", [])
            field = (
                "viewportFormats"
                if composition.get("family") == "format_transformation"
                else "interfaceEvents"
                if composition.get("family") == "demonstrative_interface"
                else None
            )
            values = composition.get(field, []) if field else []
            if field and values and len(values) != len(targets):
                before = list(values)
                composition[field] = [values[index % len(values)] for index in range(len(targets))]
                repairs.append(
                    {
                        "sceneId": scene.get("id"),
                        "compositionId": composition.get("id"),
                        "reason": "semantic_parameter_count_bound_to_targets",
                        "field": field,
                        "before": before,
                        "after": list(composition[field]),
                    }
                )
            if composition.get("family") == "format_transformation" and targets:
                target_elements = [elements.get(target_id) for target_id in targets]
                # Procedural states are accepted only when the author supplied
                # the same explicit content identity on every target.  Never
                # manufacture continuity from target ids: that certified the
                # unrelated empty rectangles used by the rejected pilot.
                content_identities = {
                    element.get("contentIdentity")
                    for element in target_elements
                    if element is not None and element.get("contentIdentity")
                }
                if (
                    not composition.get("continuityKey")
                    and len(content_identities) == 1
                    and len(target_elements) >= 2
                    and all(element is not None and element.get("contentIdentity") for element in target_elements)
                ):
                    composition["continuityKey"] = next(iter(content_identities))
                    repairs.append(
                        {
                            "sceneId": scene.get("id"),
                            "compositionId": composition.get("id"),
                            "reason": "format_transformation_explicit_content_identity_bound",
                            "continuityKey": composition["continuityKey"],
                        }
                    )
        material_bindings = {
            need.get("id"): need.get("blueprintRequirementId") or need.get("id")
            for need in scene.get("materialNeeds", [])
            if need.get("id")
        }
        material_targets = {}
        for need in scene.get("materialNeeds", []):
            target_id = need.get("targetId")
            if not target_id:
                continue
            for identity in (need.get("id"), need.get("blueprintRequirementId")):
                if identity:
                    material_targets.setdefault(identity, set()).add(target_id)
        component_bindings = {
            composition.get("id"): composition.get("family")
            for composition in raw_compositions
            if composition.get("id") and composition.get("family")
        }
        shot_plan = scene.get("shotPlan", [])
        primitive_element_kinds = {
            "typography": {"text", "card"},
            "groups": {"group"},
            "paths": {"path"},
            "depth": {"image", "video", "shape", "group"},
            "effects": {"image", "video", "shape", "text", "card", "group"},
            "panels": {"card", "image", "video"},
            "continuity": {"image", "video", "shape", "text", "card", "group"},
            "sound_events": {"audio"},
        }
        present_kinds = {element.get("kind") for element in scene.get("elements", [])}
        technique_ids = scene.setdefault("techniqueIds", [])
        for component in {
            item
            for shot in shot_plan
            for item in shot.get("executionComponentIds", [])
        }:
            supported_kinds = primitive_element_kinds.get(component)
            if (
                supported_kinds
                and present_kinds.intersection(supported_kinds)
                and component not in technique_ids
            ):
                technique_ids.append(component)
                repairs.append(
                    {
                        "sceneId": scene.get("id"),
                        "componentId": component,
                        "reason": "shot_component_bound_to_executable_primitive",
                    }
                )
        if isinstance(scene_duration, int) and shot_plan:
            expected_start = 0
            for index, shot in enumerate(shot_plan):
                before = [shot.get("startFrame"), shot.get("endFrameExclusive")]
                shot_end = shot.get("endFrameExclusive")
                if not isinstance(shot_end, int):
                    continue
                if index == len(shot_plan) - 1:
                    shot_end = scene_duration
                shot_end = min(scene_duration, max(expected_start + 1, shot_end))
                shot["startFrame"] = expected_start
                shot["endFrameExclusive"] = shot_end
                expected_start = shot_end
                after = [shot["startFrame"], shot["endFrameExclusive"]]
                if before != after:
                    repairs.append(
                        {
                            "sceneId": scene.get("id"),
                            "shotId": shot.get("id"),
                            "reason": "shot_intervals_reconciled_to_contiguous_timeline",
                            "before": before,
                            "after": after,
                        }
                    )
                    if index == len(shot_plan) - 1 and before[1] != scene_duration:
                        repairs.append(
                            {
                                "sceneId": scene.get("id"),
                                "shotId": shot.get("id"),
                                "reason": "final_shot_bound_to_scene_duration",
                                "before": before[1],
                                "after": scene_duration,
                            }
                        )
        for shot_index, shot in enumerate(shot_plan):
            material_ids = shot.get("materialRequirementIds", [])
            normalized_material_ids = [material_bindings.get(item, item) for item in material_ids]
            if material_ids != normalized_material_ids:
                shot["materialRequirementIds"] = normalized_material_ids
                repairs.append(
                    {
                        "sceneId": scene.get("id"),
                        "shotId": shot.get("id"),
                        "reason": "shot_material_bound_to_blueprint_requirement",
                        "before": material_ids,
                        "after": normalized_material_ids,
                    }
                )
            if not shot.get("targetElementIds"):
                bound_targets = {
                    target_id
                    for material_id in normalized_material_ids
                    for target_id in material_targets.get(material_id, set())
                }
                if len(bound_targets) == 1:
                    shot["targetElementIds"] = sorted(bound_targets)
                    repairs.append(
                        {
                            "sceneId": scene.get("id"),
                            "shotId": shot.get("id"),
                            "reason": "shot_target_bound_to_material_requirement",
                            "materialRequirementIds": normalized_material_ids,
                            "after": list(shot["targetElementIds"]),
                        }
                    )
                elif len(bound_targets) > 1:
                    transformations = [
                        composition
                        for composition in raw_compositions
                        if composition.get("family") == "format_transformation"
                        and bound_targets.issubset(set(composition.get("targetIds", [])))
                    ]
                    if len(transformations) == 1:
                        states = transformations[0].get("targetIds", [])
                        selected = states[min(shot_index, len(states) - 1)]
                        shot["targetElementIds"] = [selected]
                        repairs.append(
                            {
                                "sceneId": scene.get("id"),
                                "shotId": shot.get("id"),
                                "reason": "shot_target_bound_to_material_transformation_state",
                                "materialRequirementIds": normalized_material_ids,
                                "stateIndex": min(shot_index, len(states) - 1),
                                "after": [selected],
                            }
                        )
            component_ids = shot.get("executionComponentIds", [])
            normalized_component_ids = [component_bindings.get(item, item) for item in component_ids]
            available_components = {
                *scene.get("techniqueIds", []),
                *(composition.get("family") for composition in raw_compositions),
            }
            missing_components = [
                item for item in normalized_component_ids if item not in available_components
            ]
            if missing_components:
                shot_targets = set(shot.get("targetElementIds", []))
                matching_families = {
                    composition.get("family")
                    for composition in raw_compositions
                    if shot_targets.intersection(composition.get("targetIds", []))
                }
                if len(matching_families) == 1:
                    family = next(iter(matching_families))
                    normalized_component_ids = [
                        family if item in missing_components else item
                        for item in normalized_component_ids
                    ]
                    repairs.append(
                        {
                            "sceneId": scene.get("id"),
                            "shotId": shot.get("id"),
                            "reason": "shot_component_rebound_after_composition_repair",
                            "before": component_ids,
                            "after": normalized_component_ids,
                        }
                    )
            if component_ids != normalized_component_ids:
                shot["executionComponentIds"] = normalized_component_ids
                repairs.append(
                    {
                        "sceneId": scene.get("id"),
                        "shotId": shot.get("id"),
                        "reason": "shot_component_bound_to_registered_family",
                        "before": component_ids,
                        "after": normalized_component_ids,
                    }
                )
            shot_start = shot.get("startFrame")
            shot_end = shot.get("endFrameExclusive")
            if isinstance(shot_start, int) and isinstance(shot_end, int):
                for target_id in shot.get("targetElementIds", []):
                    target = elements.get(target_id)
                    if not target or target.get("visualRole") == "background":
                        continue
                    related_intervals = []
                    for related_shot in scene.get("shotPlan", []):
                        related_targets = set(related_shot.get("targetElementIds", []))
                        if not related_targets:
                            for related_material in related_shot.get("materialRequirementIds", []):
                                related_targets.update(material_targets.get(related_material, set()))
                        related_start = related_shot.get("startFrame")
                        related_end = related_shot.get("endFrameExclusive")
                        if (
                            target_id in related_targets
                            and isinstance(related_start, int)
                            and isinstance(related_end, int)
                        ):
                            related_intervals.append((related_start, related_end))
                    if len(related_intervals) > 1:
                        union_start = min(start for start, _ in related_intervals)
                        union_end = max(end for _, end in related_intervals)
                        before = [target.get("startFrame"), target.get("durationFrames")]
                        target["startFrame"] = union_start
                        target["durationFrames"] = max(1, union_end - union_start)
                        if before != [target["startFrame"], target["durationFrames"]]:
                            repairs.append(
                                {
                                    "sceneId": scene.get("id"),
                                    "elementId": target_id,
                                    "reason": "shared_shot_target_interval_bound",
                                    "before": before,
                                    "after": [target["startFrame"], target["durationFrames"]],
                                }
                            )
                        continue
                    if target.get("startFrame") is None:
                        target["startFrame"] = shot_start
                    expected_duration = max(1, shot_end - shot_start)
                    if target.get("startFrame") == shot_start and target.get("durationFrames") != expected_duration:
                        before = target.get("durationFrames")
                        target["durationFrames"] = expected_duration
                        repairs.append(
                            {
                                "sceneId": scene.get("id"),
                                "shotId": shot.get("id"),
                                "elementId": target_id,
                                "reason": "shot_target_interval_bound_to_shot",
                                "before": before,
                                "after": expected_duration,
                            }
                        )
        if (
            isinstance(scene_duration, int)
            and shot_plan
            and shot_plan[0].get("startFrame") == 0
            and all(
                left.get("endFrameExclusive") == right.get("startFrame")
                for left, right in zip(shot_plan, shot_plan[1:], strict=False)
            )
            and shot_plan[-1].get("endFrameExclusive") != scene_duration
            and int(shot_plan[-1].get("startFrame", scene_duration)) < scene_duration
        ):
            before = shot_plan[-1].get("endFrameExclusive")
            shot_plan[-1]["endFrameExclusive"] = scene_duration
            repairs.append(
                {
                    "sceneId": scene.get("id"),
                    "shotId": shot_plan[-1].get("id"),
                    "reason": "final_shot_bound_to_scene_duration",
                    "before": before,
                    "after": scene_duration,
                }
            )
        claims = {}
        minimum_targets = {
            "evidence": 2,
            "comparison": 2,
            "sequence": 2,
            "repetition": 1,
            "focus": 1,
            "continuity": 1,
            "annotated_material": 2,
            "format_transformation": 2,
            "demonstrative_interface": 2,
            "continuity_comparison": 2,
        }
        for index, composition in enumerate(raw_compositions):
            for target_id in composition.get("targetIds", []):
                claims.setdefault(target_id, []).append(index)
        for target_id, owners in claims.items():
            if len(owners) < 2:
                continue
            removable = []
            for index in owners:
                composition = raw_compositions[index]
                minimum = minimum_targets.get(composition.get("family"), 1)
                slack = len(composition.get("targetIds", [])) - minimum
                if slack > 0:
                    removable.append((slack, index))
            if not removable:
                continue
            highest = max(slack for slack, _ in removable)
            candidates = [index for slack, index in removable if slack == highest]
            if len(candidates) != 1:
                continue
            index = candidates[0]
            composition = raw_compositions[index]
            before = list(composition.get("targetIds", []))
            composition["targetIds"] = [item for item in before if item != target_id]
            repairs.append(
                {
                    "sceneId": scene.get("id"),
                    "compositionId": composition.get("id"),
                    "reason": "duplicate_semantic_target_reallocated",
                    "targetId": target_id,
                    "before": before,
                    "after": list(composition["targetIds"]),
                }
            )

        claimed = set()
        compositions = []
        for composition in raw_compositions:
            before = list(composition.get("targetIds", []))
            after = [target_id for target_id in before if target_id not in claimed]
            claimed.update(after)
            if before != after:
                repairs.append(
                    {
                        "sceneId": scene.get("id"),
                        "compositionId": composition.get("id"),
                        "reason": "duplicate_semantic_component_target_removed",
                        "before": before,
                        "after": after,
                    }
                )
            if after:
                composition["targetIds"] = after
                compositions.append(composition)
            else:
                repairs.append(
                    {
                        "sceneId": scene.get("id"),
                        "compositionId": composition.get("id"),
                        "reason": "empty_semantic_component_removed",
                    }
                )
        scene["compositions"] = compositions
        for shot in scene.get("shotPlan", []):
            available = {
                *scene.get("techniqueIds", []),
                *(composition.get("family") for composition in compositions),
            }
            component_ids = list(shot.get("executionComponentIds", []))
            missing = [item for item in component_ids if item not in available]
            if not missing:
                continue
            shot_targets = set(shot.get("targetElementIds", []))
            matching = {
                composition.get("family")
                for composition in compositions
                if shot_targets.intersection(composition.get("targetIds", []))
            }
            if len(matching) != 1:
                continue
            family = next(iter(matching))
            rebound = [family if item in missing else item for item in component_ids]
            shot["executionComponentIds"] = list(dict.fromkeys(rebound))
            repairs.append(
                {
                    "sceneId": scene.get("id"),
                    "shotId": shot.get("id"),
                    "reason": "shot_component_rebound_after_final_composition_ownership",
                    "before": component_ids,
                    "after": shot["executionComponentIds"],
                }
            )
        heroes = [element for element in scene.get("elements", []) if element.get("visualRole") == "hero"]
        if len(heroes) > 1:
            camera_targets = {
                cue.get("targetId") for cue in scene.get("cameraCues", []) if cue.get("targetId")
            }
            required_material_targets = {
                need.get("targetId")
                for need in scene.get("materialNeeds", [])
                if need.get("required", True)
            }
            preferred = [element for element in heroes if element.get("id") in camera_targets]
            if len(preferred) != 1:
                preferred = [
                    element for element in heroes if element.get("id") in required_material_targets
                ]
            if len(preferred) == 1:
                primary_id = preferred[0].get("id")
                for element in heroes:
                    if element.get("id") == primary_id:
                        continue
                    before = element.get("visualRole")
                    after = "accent" if element.get("kind") == "path" else "support"
                    element["visualRole"] = after
                    repairs.append(
                        {
                            "sceneId": scene.get("id"),
                            "elementId": element.get("id"),
                            "reason": "secondary_hero_role_demoted",
                            "primaryElementId": primary_id,
                            "before": before,
                            "after": after,
                        }
                    )
        for cue in scene.get("cameraCues", []):
            if cue.get("easingProfile") not in {None, "gentle", "standard"}:
                before = cue.get("easingProfile")
                cue["easingProfile"] = "standard"
                repairs.append(
                    {
                        "sceneId": scene.get("id"),
                        "cameraMode": cue.get("mode"),
                        "reason": "camera_easing_profile_normalized",
                        "before": before,
                        "after": "standard",
                    }
                )
            target_id = cue.get("targetId")
            role = elements.get(target_id, {}).get("visualRole")
            if (
                target_id
                and role not in {"hero", "support"}
                and cue.get("mode") in {"push_in", "pull_out", "focus_transition"}
            ):
                primary = [
                    element
                    for element in scene.get("elements", [])
                    if element.get("visualRole") == "hero"
                ]
                if len(primary) == 1:
                    cue["targetId"] = primary[0].get("id")
                    repairs.append(
                        {
                            "sceneId": scene.get("id"),
                            "cameraMode": cue.get("mode"),
                            "reason": "camera_target_rebound_to_primary_visual",
                            "before": target_id,
                            "after": cue["targetId"],
                        }
                    )
                    target_id = cue["targetId"]
                    role = "hero"
            if target_id and role not in {"hero", "support"} and cue.get("mode") in {"pan", "static"}:
                cue.pop("targetId", None)
                repairs.append(
                    {
                        "sceneId": scene.get("id"),
                        "cameraMode": cue.get("mode"),
                        "reason": "decorative_camera_target_removed",
                        "before": target_id,
                        "after": None,
                    }
                )
        # Shot binding can shorten an element after the early animation pass.
        # Reconcile the final interval once all structural repairs have run so
        # a stored provider response can be replayed without another API call.
        for element in scene.get("elements", []):
            duration = element.get("durationFrames")
            if not isinstance(duration, int) or duration <= 0:
                continue
            for animation in element.get("animations", []):
                keyframes = animation.get("keyframes", [])
                before = [item.get("frame") for item in keyframes]
                by_frame = {}
                for keyframe in keyframes:
                    frame = keyframe.get("frame")
                    if not isinstance(frame, int):
                        continue
                    keyframe["frame"] = min(max(0, frame), duration - 1)
                    by_frame[keyframe["frame"]] = keyframe
                after_items = [by_frame[frame] for frame in sorted(by_frame)]
                after = [item.get("frame") for item in after_items]
                if before != after:
                    animation["keyframes"] = after_items
                    repairs.append(
                        {
                            "sceneId": scene.get("id"),
                            "elementId": element.get("id"),
                            "reason": "animation_reconciled_after_interval_binding",
                            "before": before,
                            "after": after,
                        }
                    )
            reconciled_cues = []
            for cue in element.get("motionCues", []):
                start = max(0, int(cue.get("startFrame", 0)))
                cue_duration = max(1, int(cue.get("durationFrames", 1)))
                if start >= duration:
                    repairs.append(
                        {
                            "sceneId": scene.get("id"),
                            "elementId": element.get("id"),
                            "reason": "motion_cue_removed_after_interval_binding",
                            "before": [start, cue_duration],
                        }
                    )
                    continue
                bounded_duration = min(cue_duration, duration - start)
                if start != cue.get("startFrame", 0) or bounded_duration != cue_duration:
                    repairs.append(
                        {
                            "sceneId": scene.get("id"),
                            "elementId": element.get("id"),
                            "reason": "motion_cue_reconciled_after_interval_binding",
                            "before": [cue.get("startFrame", 0), cue_duration],
                            "after": [start, bounded_duration],
                        }
                    )
                cue["startFrame"] = start
                cue["durationFrames"] = bounded_duration
                reconciled_cues.append(cue)
            element["motionCues"] = reconciled_cues
            for span in element.get("textSpans", []):
                start = span.get("startFrame")
                span_duration = span.get("durationFrames")
                if start is None or span_duration is None:
                    continue
                if start >= duration:
                    span["startFrame"] = None
                    span["durationFrames"] = None
                    repairs.append(
                        {
                            "sceneId": scene.get("id"),
                            "elementId": element.get("id"),
                            "textSpanId": span.get("id"),
                            "reason": "text_span_timing_removed_after_interval_binding",
                        }
                    )
                    continue
                bounded_duration = min(span_duration, duration - start)
                if bounded_duration != span_duration:
                    span["durationFrames"] = bounded_duration
                    repairs.append(
                        {
                            "sceneId": scene.get("id"),
                            "elementId": element.get("id"),
                            "textSpanId": span.get("id"),
                            "reason": "text_span_timing_reconciled_after_interval_binding",
                            "before": span_duration,
                            "after": bounded_duration,
                        }
                    )
    return classify_contract_repairs(repairs)


def motion_cue_keyframes(cue):
    """Lower an editorial motion cue to local, deterministic property keyframes."""
    if cue.kind == "deliberate_hold":
        return {}
    end = cue.start_frame + cue.duration_frames - 1
    curve = MOTION_PROFILES[cue.profile]["bezier"]

    def key(frame, value, *, linear=False):
        if linear or curve is None:
            return MotionKeyframeV1(frame=frame, value=value, easing="linear")
        return MotionKeyframeV1(frame=frame, value=value, easing="cubic_bezier", cubic_bezier=curve)

    def final(frame, value):
        return MotionKeyframeV1(frame=frame, value=value)

    intensity = cue.intensity
    if cue.kind == "entrance":
        travel = MOTION_PROFILES[cue.profile]["travel"] * intensity
        return {
            "opacity": [key(cue.start_frame, 0), final(end, 1)],
            "position_y": [key(cue.start_frame, travel), final(end, 0)],
        }
    if cue.kind == "exit":
        travel = MOTION_PROFILES[cue.profile]["travel"] * intensity
        return {
            "opacity": [key(cue.start_frame, 1), final(end, 0)],
            "position_y": [key(cue.start_frame, 0), final(end, -travel)],
        }
    middle = cue.start_frame + max(1, round((cue.duration_frames - 1) * 0.58))
    if cue.kind == "emphasis":
        return {
            "scale_x": [key(cue.start_frame, 0.92), key(middle, 1.04), final(end, 1)],
            "scale_y": [key(cue.start_frame, 0.92), key(middle, 1.04), final(end, 1)],
        }
    return {
        "rotation_degrees": [
            key(cue.start_frame, -1.5 * intensity),
            key(middle, 1.5 * intensity),
            final(end, 0),
        ]
    }


def repair_composition_contracts(direction):
    """Repair only unambiguous family/target-shape mismatches.

    No prose is converted into geometry. The repair narrows a malformed
    evidence or sequence action to an existing visual target that can be
    focused, while keeping every other element available for audit.
    """
    repairs = []
    for scene in direction.scenes:
        indexed = {element.id: element for element in scene.elements}
        for element in scene.elements:
            explicit_properties = {animation.property for animation in element.animations}
            kept_cues = []
            for cue in element.motion_cues:
                generated_properties = set(motion_cue_keyframes(cue))
                if explicit_properties & generated_properties:
                    repairs.append(
                        {
                            "sceneId": scene.id,
                            "elementId": element.id,
                            "reason": "explicit_animation_owns_motion_property",
                            "motionCue": cue.model_dump(mode="json", by_alias=True),
                            "properties": sorted(explicit_properties & generated_properties),
                        }
                    )
                else:
                    kept_cues.append(cue)
            element.motion_cues = kept_cues
        for composition in scene.compositions:
            composition_family = layout_family(composition.family)
            targets = [indexed[target_id] for target_id in composition.target_ids if target_id in indexed]
            for target_index, element in enumerate(targets):
                owned_properties = {"scale_x", "scale_y"} if composition_family == "focus" else {"opacity"}
                kept_cues = []
                for cue in element.motion_cues:
                    generated_properties = set(motion_cue_keyframes(cue))
                    if owned_properties & generated_properties:
                        repairs.append(
                            {
                                "sceneId": scene.id,
                                "compositionId": composition.id,
                                "elementId": element.id,
                                "reason": "semantic_component_owns_motion_property",
                                "motionCue": cue.model_dump(mode="json", by_alias=True),
                                "properties": sorted(owned_properties & generated_properties),
                            }
                        )
                    else:
                        kept_cues.append(cue)
                element.motion_cues = kept_cues
                conflicting = {
                    "parentId": element.parent_id,
                    "alignment": element.alignment,
                    "afterElementId": element.after_element_id,
                    "animations": [item.model_dump(mode="json", by_alias=True) for item in element.animations],
                    "repeatCount": element.repeat_count,
                }
                preserve_annotation_motion = (
                    composition.family == "annotated_material"
                    and target_index > 0
                    and element.kind in {"shape", "path"}
                )
                if any(
                    (
                        element.parent_id,
                        element.alignment,
                        element.after_element_id,
                        element.animations and not preserve_annotation_motion,
                        element.repeat_count != 1,
                    )
                ):
                    # A registered semantic composition owns target layout and its
                    # base entrance. Removing duplicate manual controls is an
                    # unambiguous contract repair; content and timing remain intact.
                    element.parent_id = None
                    element.alignment = None
                    element.after_element_id = None
                    if not preserve_annotation_motion:
                        element.animations = []
                    element.repeat_count = 1
                    repairs.append(
                        {
                            "sceneId": scene.id,
                            "compositionId": composition.id,
                            "elementId": element.id,
                            "reason": "semantic_component_owns_layout_and_base_motion",
                            "before": conflicting,
                            "after": {
                                "parentId": None,
                                "alignment": None,
                                "afterElementId": None,
                                "animations": (
                                    [
                                        item.model_dump(mode="json", by_alias=True)
                                        for item in element.animations
                                    ]
                                    if preserve_annotation_motion
                                    else []
                                ),
                                "repeatCount": 1,
                            },
                        }
                    )
            media = [element for element in targets if element.kind in {"image", "video", "shape"}]
            evidence_media = [element for element in targets if element.kind in {"image", "video"}]
            annotations = [
                element
                for element in targets
                if element.kind in {"text", "card"}
                or (
                    element.kind == "shape"
                    and element.visual_role == "accent"
                )
                or (
                    element.kind == "path"
                    and element.visual_role in {"support", "accent"}
                )
            ]
            reason = None
            if (
                composition_family == "evidence"
                and evidence_media
                and any(
                    (element.kind == "shape" and element.visual_role == "accent")
                    or (
                        element.kind == "path"
                        and element.visual_role in {"support", "accent"}
                    )
                    for element in targets
                )
                and not any(element.kind in {"text", "card"} for element in targets)
            ):
                before_family = composition.family
                composition.family = "annotated_material"
                composition_family = composition.family
                repairs.append(
                    {
                        "sceneId": scene.id,
                        "compositionId": composition.id,
                        "reason": "evidence_path_annotation_promoted_to_annotated_material",
                        "before": before_family,
                        "after": composition.family,
                    }
                )
            if composition_family == "evidence" and evidence_media and not annotations:
                reason = "evidence_without_annotation"
            elif composition_family == "sequence" and len(targets) == 1:
                media = targets
                reason = "sequence_with_single_target"
            if reason and media:
                before = {"family": composition.family, "targetIds": list(composition.target_ids)}
                composition.family = "focus"
                composition.target_ids = [media[0].id]
                repairs.append(
                    {
                        "sceneId": scene.id,
                        "compositionId": composition.id,
                        "reason": reason,
                        "before": before,
                        "after": {"family": "focus", "targetIds": [media[0].id]},
                    }
                )
                targets = [media[0]]
            if composition_family != "continuity" and targets:
                max_action = min(element.duration_frames - 1 for element in targets)
                count = (
                    len(targets)
                    if composition_family == "sequence"
                    else composition.repeat_count
                    if composition_family == "repetition"
                    else 1
                )
                if composition_family in {"sequence", "repetition"}:
                    max_action = min(max_action, (scene.duration_frames - 1) // count)
                if max_action >= 1 and composition.action_frames > max_action:
                    before_frames = composition.action_frames
                    composition.action_frames = max_action
                    repairs.append(
                        {
                            "sceneId": scene.id,
                            "compositionId": composition.id,
                            "reason": "action_exceeds_available_interval",
                            "before": {"actionFrames": before_frames},
                            "after": {"actionFrames": max_action},
                        }
                    )
        indexed = {element.id: element for element in scene.elements}
        for parent in (element for element in scene.elements if element.kind == "group"):
            children = [element for element in scene.elements if element.parent_id == parent.id]
            if not children:
                continue
            required_end = max(child.start_frame + child.duration_frames for child in children)
            current_end = parent.start_frame + parent.duration_frames
            if required_end > current_end and required_end <= scene.duration_frames:
                before = parent.duration_frames
                parent.duration_frames = required_end - parent.start_frame
                repairs.append(
                    {
                        "sceneId": scene.id,
                        "elementId": parent.id,
                        "reason": "group_interval_expanded_to_contain_children",
                        "before": {"durationFrames": before},
                        "after": {"durationFrames": parent.duration_frames},
                    }
                )
        component_bindings = {composition.id: composition.family for composition in scene.compositions}
        for shot in scene.shot_plan:
            before = list(shot.execution_component_ids)
            after = [component_bindings.get(component, component) for component in before]
            available_components = {
                *scene.technique_ids,
                *(composition.family for composition in scene.compositions),
            }
            missing = {component for component in after if component not in available_components}
            if missing:
                shot_targets = set(shot.target_element_ids)
                matching_families = {
                    composition.family
                    for composition in scene.compositions
                    if shot_targets.intersection(composition.target_ids)
                }
                if len(matching_families) == 1:
                    family = next(iter(matching_families))
                    after = [family if component in missing else component for component in after]
            if before != after:
                shot.execution_component_ids = after
                repairs.append(
                    {
                        "sceneId": scene.id,
                        "shotId": shot.id,
                        "reason": "shot_component_rebound_after_composition_repair",
                        "before": before,
                        "after": after,
                    }
                )
    return classify_contract_repairs(repairs)


def classify_contract_repairs(repairs):
    """Make intent-changing normalization visible to the production gate."""
    for repair in repairs:
        semantic = repair.get("reason") not in NON_SEMANTIC_REPAIRS
        repair["classification"] = "semantic_change" if semantic else "bounded_normalization"
        repair["requiresAlternative"] = semantic
    return repairs


def semantic_contract_repairs(repairs):
    return [repair for repair in repairs if repair.get("requiresAlternative")]


def bind_shot_semantics_to_blueprint(candidate, editorial_direction):
    """Keep executable shot references aligned with the approved storyboard."""
    repairs = []
    beats = {beat.id: beat for beat in editorial_direction.beats}
    for scene in candidate.scenes:
        beat = beats.get(scene.id)
        if not beat or not beat.visual_blueprint:
            continue
        authored = {shot.id: shot for shot in beat.visual_blueprint.shot_sequence}
        indexed = {element.id: element for element in scene.elements}
        for shot in scene.shot_plan:
            source = authored.get(shot.id)
            if not source:
                continue
            before_materials = list(shot.material_requirement_ids)
            before_components = list(shot.execution_component_ids)
            before_action = shot.observable_action
            for field in (
                "function",
                "subject",
                "observable_action",
                "shot_scale",
                "angle",
                "lighting",
            ):
                setattr(shot, field, getattr(source, field))
            shot.material_requirement_ids = list(source.material_requirement_ids)
            shot.execution_component_ids = list(source.execution_component_ids)
            material_targets = {
                need.target_id
                for need in scene.material_needs
                if (need.blueprint_requirement_id or need.id) in shot.material_requirement_ids
            }
            missing_material_targets = sorted(material_targets - set(shot.target_element_ids))
            if missing_material_targets:
                shot.target_element_ids.extend(missing_material_targets)
                repairs.append(
                    {
                        "sceneId": scene.id,
                        "shotId": shot.id,
                        "reason": "shot_target_augmented_for_material_requirement",
                        "materialRequirementIds": list(shot.material_requirement_ids),
                        "addedTargetElementIds": missing_material_targets,
                    }
                )
            if shot.start_frame is not None and shot.end_frame_exclusive is not None:
                for target_id in shot.target_element_ids:
                    target = indexed.get(target_id)
                    if target is None:
                        continue
                    current_end = target.start_frame + target.duration_frames
                    if (
                        target.start_frame <= shot.start_frame
                        and current_end >= shot.end_frame_exclusive
                    ):
                        continue
                    before_interval = [target.start_frame, current_end]
                    target.start_frame = min(target.start_frame, shot.start_frame)
                    target.duration_frames = (
                        max(current_end, shot.end_frame_exclusive) - target.start_frame
                    )
                    repairs.append(
                        {
                            "sceneId": scene.id,
                            "shotId": shot.id,
                            "elementId": target_id,
                            "reason": "shot_target_interval_expanded_to_shot",
                            "before": before_interval,
                            "after": [
                                target.start_frame,
                                target.start_frame + target.duration_frames,
                            ],
                        }
                    )
            for component in source.execution_component_ids:
                if component not in scene.technique_ids:
                    scene.technique_ids.append(component)
            if (
                before_materials != shot.material_requirement_ids
                or before_components != shot.execution_component_ids
                or before_action != shot.observable_action
            ):
                repairs.append(
                    {
                        "sceneId": scene.id,
                        "shotId": shot.id,
                        "reason": "shot_semantics_rebound_to_storyboard",
                        "before": {
                            "materialRequirementIds": before_materials,
                            "executionComponentIds": before_components,
                        },
                        "after": {
                            "materialRequirementIds": list(shot.material_requirement_ids),
                            "executionComponentIds": list(shot.execution_component_ids),
                        },
                    }
                )
    return repairs


def lower_compositions(direction, width, height):
    def fit_in_box(element, left, top, box_width, box_height, *, allow_upscale=False):
        """Fit a semantic target without changing its visual proportions.

        Composition families describe relationships, not permission to stretch
        an icon, person or piece of footage to the size of its layout cell.
        Media can grow to make evidence readable; graphical primitives keep
        their authored scale unless the cell is smaller.
        """
        source_width, source_height = element.width, element.height
        scale = min(box_width / source_width, box_height / source_height)
        if not allow_upscale:
            scale = min(1.0, scale)
        element.width = source_width * scale
        element.height = source_height * scale
        element.x = left + (box_width - element.width) / 2
        element.y = top + (box_height - element.height) / 2

    result = direction.model_copy(deep=True)
    motion_system = result.art_direction.motion_system if result.art_direction else None
    for scene in result.scenes:
        if motion_system and result.art_direction.palette:
            background_color = result.art_direction.palette[0]
            if isinstance(background_color, str) and background_color.startswith("#") and len(background_color) in {4, 7}:
                scene.background = background_color
        indexed = {e.id: e for e in scene.elements}
        generated_format_labels = []
        generated_annotation_groups = []
        format_label_sources = {}
        for composition in scene.compositions:
            editorial_timing = False
            margin = min(width, height) * composition.margin_ratio
            gap = min(width, height) * composition.gap_ratio
            elements = [indexed[identity] for identity in composition.target_ids]
            target_ids = {element.id for element in elements}
            authored_geometry = {
                element.id: (element.x, element.y, element.width, element.height)
                for element in elements
            }
            if any(
                e.parent_id
                or e.alignment
                or e.after_element_id
                or (
                    e.animations
                    and not (
                        composition.family == "annotated_material"
                        and index > 0
                        and e.kind in {"shape", "path"}
                    )
                )
                or e.repeat_count != 1
                for index, e in enumerate(elements)
            ):
                raise ValueError("editing_component_conflicting_manual_geometry")
            family = layout_family(composition.family)
            editorial_sequence = bool(
                motion_system and composition.family == "sequence" and composition.state_hold_frames
            )
            if composition.family == "sequence" and composition.state_hold_frames and not editorial_sequence:
                raise ValueError("editing_component_editorial_sequence_requires_motion_system")
            if editorial_sequence and sum(composition.state_hold_frames) > scene.duration_frames:
                raise ValueError("editing_component_editorial_timing_exceeds_scene")
            sequence_preserves_spatial_layout = family == "sequence" and any(
                element.kind == "path" for element in elements
            )
            if composition.family == "demonstrative_interface":
                sequence_preserves_spatial_layout = False
            if family == "evidence" and composition.family != "annotated_material" and len(elements) != 2:
                raise ValueError("editing_component_requires_two_targets")
            if family == "comparison" and len(elements) != 2:
                raise ValueError("editing_component_requires_two_targets")
            if family in {"focus", "repetition", "continuity"} and len(elements) != 1:
                raise ValueError("editing_component_requires_single_target")
            if family == "sequence" and len(elements) < 2:
                raise ValueError("editing_component_sequence_requires_multiple_targets")
            if composition.family == "annotated_material":
                valid_annotation = (
                    2 <= len(elements) <= 4
                    and elements[0].kind in {"image", "video"}
                    and all(
                        element.kind in {"text", "card", "shape", "path", "image"}
                        for element in elements[1:]
                    )
                )
                if not valid_annotation:
                    raise ValueError("editing_component_annotated_material_requires_media_and_annotation")
            if composition.family == "format_transformation":
                if not composition.viewport_formats:
                    defaults = ("portrait", "square", "landscape")
                    composition.viewport_formats = [
                        defaults[index % len(defaults)] for index in range(len(elements))
                    ]
                media = [element for element in elements if element.kind in {"image", "video"}]
                asset_ids = {element.asset_id for element in media if element.asset_id}
                procedural_identity = (
                    bool(composition.continuity_key)
                    and {element.content_identity for element in elements}
                    == {composition.continuity_key}
                    and all(element.kind in {"card", "shape", "text", "path"} for element in elements)
                )
                canonical_reference_ids = {element.content_reference_id for element in elements}
                canonical_reference = (
                    next(iter(canonical_reference_ids))
                    if len(canonical_reference_ids) == 1 and None not in canonical_reference_ids
                    else None
                )
                reference = next(
                    (item for item in result.content_references if item.id == canonical_reference),
                    None,
                )
                required_parts = {part.id for part in reference.parts if part.required} if reference else set()
                canonical_groups = bool(reference) and all(element.kind == "group" for element in elements)
                if canonical_groups:
                    for state in elements:
                        state_parts = {
                            candidate.content_part_id
                            for candidate in scene.elements
                            if candidate.parent_id == state.id
                            and candidate.content_reference_id == reference.id
                            and candidate.content_part_id
                        }
                        if not required_parts.issubset(state_parts):
                            canonical_groups = False
                            break
                editorial_timing = bool(canonical_groups and composition.state_hold_frames)
                if composition.state_hold_frames and not canonical_groups:
                    raise ValueError("editing_component_editorial_timing_requires_canonical_parts")
                if editorial_timing:
                    required_frames = sum(composition.state_hold_frames) + (
                        len(elements) - 1
                    ) * composition.movement_frames
                    if required_frames > scene.duration_frames:
                        raise ValueError("editing_component_editorial_timing_exceeds_scene")
                needs = {
                    need.target_id: need
                    for need in scene.material_needs
                    if need.field == "asset" and need.target_id in {element.id for element in media}
                }
                pending_signatures = {
                    (
                        need.blueprint_requirement_id,
                        need.kind,
                        need.query,
                        need.purpose,
                        need.source_class,
                    )
                    for need in needs.values()
                }
                pending_shared_material = (
                    len(media) == len(elements)
                    and len(needs) == len(media)
                    and len(pending_signatures) == 1
                    and len(asset_ids) <= 1
                    and composition.continuity_key in {element.id for element in media}
                )
                if (
                    len(media) != len(elements)
                    or (len(asset_ids) != 1 and not pending_shared_material)
                ) and not procedural_identity and not canonical_groups:
                    raise ValueError("editing_component_format_transformation_requires_shared_material")
            if composition.family == "demonstrative_interface" and not all(
                element.kind in {"card", "image", "video", "text", "shape"} for element in elements
            ):
                raise ValueError("editing_component_demonstrative_interface_target_invalid")
            if composition.family == "continuity_comparison" and len(elements) != 2:
                raise ValueError("editing_component_continuity_comparison_requires_two_states")
            if composition.family == "continuity_comparison":
                shared_assets = {
                    element.asset_id for element in elements if element.asset_id
                }
                if len(shared_assets) > 1 or (not shared_assets and not composition.continuity_key):
                    raise ValueError("editing_component_continuity_comparison_common_element_required")
            for i, element in enumerate(elements):
                if composition.action_frames >= element.duration_frames:
                    raise ValueError("editing_component_action_out_of_interval")
                element.fit_text = element.kind in {"text", "card"}
                if family == "evidence":
                    if i == 0:
                        evidence_height = height * 0.62
                        fit_in_box(
                            element,
                            margin,
                            margin,
                            width - 2 * margin,
                            evidence_height,
                            allow_upscale=element.kind in {"image", "video"},
                        )
                        if element.kind in {"image", "video"}:
                            element.object_fit = "contain"
                        # An annotation that belongs to the scene, but not to
                        # the media target itself, needs its own reading band.
                        # Keeping a headline at its authored coordinate can put
                        # it over the bottom of a large evidence box and make
                        # the subject/text relationship look accidental.
                        for copy in scene.elements:
                            if (
                                copy.id not in target_ids
                                and copy.kind in {"text", "card"}
                                and copy.text
                                and copy.parent_id is None
                            ):
                                copy.x = margin
                                copy.y = height * 0.75
                                copy.width = width - 2 * margin
                                copy.height = height * 0.13
                                copy.font_size = max(copy.font_size, width * 0.07)
                                copy.text_align = motion_system.alignment if motion_system else copy.text_align
                                copy.fit_text = True
                    else:
                        if element.kind in {"text", "card"}:
                            annotation_top = height * 0.73
                            annotation_height = height * 0.20
                            element.x = margin
                            element.y = annotation_top
                            element.width = width - 2 * margin
                            element.height = annotation_height
                        else:
                            # Shapes and paths annotate the media itself. Map
                            # their authored relation into the component's
                            # resolved media box instead of moving them into a
                            # caption strip below the subject.
                            media = elements[0]
                            media_x, media_y, media_width, media_height = authored_geometry[media.id]
                            source_x, source_y, source_width, source_height = authored_geometry[element.id]
                            relative_x = (source_x - media_x) / max(media_width, 1)
                            relative_y = (source_y - media_y) / max(media_height, 1)
                            relative_width = source_width / max(media_width, 1)
                            relative_height = source_height / max(media_height, 1)
                            element.x = media.x + min(max(relative_x, 0), 1) * media.width
                            element.y = media.y + min(max(relative_y, 0), 1) * media.height
                            element.width = min(media.width, max(2.0, relative_width * media.width))
                            element.height = min(media.height, max(2.0, relative_height * media.height))
                            element.x = min(max(media.x, element.x), media.x + media.width - element.width)
                            element.y = min(max(media.y, element.y), media.y + media.height - element.height)
                elif composition.family == "format_transformation":
                    # The same source occupies successive, visibly different viewports.
                    # Bounding dimensions are registered component geometry, not LLM coordinates.
                    format_name = (
                        composition.viewport_formats[i]
                        if composition.viewport_formats
                        else ("portrait", "square", "landscape")[i % 3]
                    )
                    aspect = {"portrait": 0.64, "square": 1.0, "landscape": 1.68}[format_name]
                    # Fit the requested aspect inside the available canvas while
                    # preserving the ratio in both dimensions.  The old code
                    # capped width but retained the original height, making a
                    # labelled landscape viewport visibly portrait on 9:16.
                    # Reserve authored title/caption bands before sizing the
                    # changing viewport.  A transformation is only useful when
                    # its content remains readable beside the explanation; the
                    # previous centered 70% box could sit underneath a measured
                    # multi-line title and fail only in Chromium preflight.
                    # Generated format labels are not present yet and are
                    # accounted for separately below.
                    external_text = [
                        item
                        for item in scene.elements
                        if item.id not in target_ids
                        and item.parent_id is None
                        and item.kind in {"text", "card"}
                        and item.text
                        and not item.id.startswith("format-label-")
                    ]
                    top_edge = margin
                    bottom_edge = height - margin
                    for item in external_text:
                        midpoint = item.y + item.height / 2
                        if midpoint <= height / 2:
                            top_edge = max(top_edge, item.y + item.height + gap)
                        else:
                            bottom_edge = min(bottom_edge, item.y - gap)
                    # Canonical content must explain its adaptation through the
                    # visible content itself. Technical format labels remain a
                    # compatibility aid for older single-layer transformations,
                    # but are deliberately absent from derived canonical states.
                    label_height = 0 if canonical_groups else min(height * 0.05, 64)
                    label_gap = 0 if canonical_groups else min(height * 0.018, 18)
                    viewport_bottom = bottom_edge - label_height - label_gap
                    if viewport_bottom <= top_edge:
                        raise ValueError("editing_component_format_transformation_text_band_conflict")
                    max_width = width - 2 * margin
                    max_height = min(height * 0.70, viewport_bottom - top_edge)
                    box_width = max_width
                    box_height = box_width / aspect
                    if box_height > max_height:
                        box_height = max_height
                        box_width = box_height * aspect
                    element.width, element.height = box_width, box_height
                    if motion_system and canonical_groups:
                        element.x = (
                            margin if motion_system.alignment == "left" else width - margin - box_width
                        )
                    else:
                        element.x = (width - box_width) / 2
                    element.y = top_edge + (max_height - box_height) / 2
                    element.object_fit = "cover"
                    element.crop_intentional = True
                    if motion_system and canonical_groups:
                        element.border_width = (
                            max(1.0, min(width, height) * 0.002)
                            if motion_system.frame == "hairline" else 0
                        )
                        if result.art_direction.palette:
                            candidate_color = result.art_direction.palette[-1]
                            if isinstance(candidate_color, str) and candidate_color.startswith("#") and len(candidate_color) in {4, 7}:
                                element.border_color = candidate_color
                    else:
                        element.border_width = max(2.0, min(width, height) * 0.006)
                        element.border_color = "#ffffff"
                    if canonical_groups and reference and element.kind == "group":
                        # Resolve a real responsive layout for every derived
                        # viewport.  The director chooses semantic parts; this
                        # component owns their measurements and does not rely
                        # on invented coordinates or scale a flattened poster.
                        children = [candidate for candidate in scene.elements if candidate.parent_id == element.id]
                        parts = {part.id: part for part in reference.parts}
                        by_role = {
                            role: [
                                child
                                for child in children
                                if child.content_part_id
                                and parts[child.content_part_id].role == role
                            ]
                            for role in {part.role for part in reference.parts}
                        }
                        local_width, local_height = element.width, element.height
                        padding = max(10.0, min(local_width, local_height) * 0.06)
                        media = (by_role.get("primary_media") or [None])[0]
                        title = (by_role.get("title") or [None])[0]
                        identity = (by_role.get("identity") or [None])[0]
                        body = (by_role.get("body") or [None])[0]
                        call_to_action = (by_role.get("call_to_action") or [None])[0]
                        if format_name == "landscape":
                            copy_width = local_width * 0.38
                            if title:
                                title.x, title.y = padding, local_height * 0.20
                                title.width, title.height = copy_width - padding, local_height * 0.26
                            if body:
                                body.x, body.y = padding, local_height * 0.48
                                body.width, body.height = copy_width - padding, local_height * 0.18
                            if media:
                                media.x, media.y = local_width * 0.42, padding
                                media.width, media.height = local_width * 0.52, local_height - 2 * padding
                        else:
                            title_fraction = (
                                0.31 if motion_system and motion_system.layout == "typography_dominant"
                                else 0.18 if format_name == "portrait" else 0.20
                            )
                            media_fraction = (
                                0.37 if motion_system and motion_system.layout == "typography_dominant"
                                else 0.62 if motion_system and motion_system.layout == "graphic_motif"
                                else 0.54 if format_name == "portrait" else 0.50
                            )
                            title_height = local_height * title_fraction
                            media_top = padding + title_height
                            media_height = local_height * media_fraction
                            if title:
                                title.x, title.y = padding, padding
                                title.width, title.height = local_width - 2 * padding, title_height - padding * 0.35
                            if media:
                                media.x, media.y = padding, media_top
                                media.width, media.height = local_width - 2 * padding, media_height
                            if body:
                                body.x, body.y = padding, media_top + media_height + padding * 0.55
                                body.width, body.height = local_width - 2 * padding, local_height * 0.12
                        if identity:
                            identity_font_size = max(identity.font_size, width * 16 / 300)
                            identity_height = max(padding, identity_font_size * identity.line_height + 10)
                            identity.x = padding
                            identity.y = local_height - padding - identity_height
                            identity.width, identity.height = local_width * 0.55, identity_height
                        if call_to_action:
                            call_to_action.width, call_to_action.height = local_width * 0.38, padding * 1.25
                            call_to_action.x = local_width - padding - call_to_action.width
                            call_to_action.y = local_height - padding - call_to_action.height
                        for child in children:
                            child.visual_role = "support" if child is media else "text"
                            if child.kind in {"image", "video"}:
                                # A persistent content part must remain visually
                                # identifiable in both derived layouts. Cropping it
                                # to fill the new viewport can erase the very object
                                # whose continuity the composition promises.
                                child.object_fit = "contain" if editorial_timing else "cover"
                                child.crop_intentional = not editorial_timing
                            if child.kind in {"text", "card"}:
                                child.fit_text = True
                                if child is title:
                                    title_scale = (
                                        0.095 if motion_system and motion_system.layout == "typography_dominant"
                                        else 0.075
                                    )
                                    child.font_size = min(96, max(18, local_width * title_scale))
                                    child.font_weight = max(700, child.font_weight)
                                else:
                                    child.font_size = min(42, max(14, local_width * 0.038))
                                if motion_system:
                                    child.text_align = motion_system.alignment
                            # A derived state represents the same already-known
                            # content. Re-revealing its words makes continuity
                            # look like new copy and leaves partial phrases in
                            # the transition frames.
                            if i > 0 and child.content_part_id:
                                child.reveal = "none"
                    if not canonical_groups:
                        label_id = ("format-label-" + digest([scene.id, composition.id, element.id]))[:80]
                        if label_id in indexed or any(item.id == label_id for item in generated_format_labels):
                            raise ValueError("editing_component_generated_id_conflict")
                        label_y = element.y + element.height + label_gap
                        if label_y + label_height > bottom_edge:
                            label_y = element.y - label_height - label_gap
                        generated_format_labels.append(
                            EditorialElementV2(
                                id=label_id,
                                kind="text",
                                purpose="Identificar o estado visível da transformação de formato",
                                text={
                                    "portrait": "VERTICAL",
                                    "square": "QUADRADO",
                                    "landscape": "HORIZONTAL",
                                }[format_name],
                                text_role="support",
                                font_size=max(18, min(width, height) * 0.035),
                                font_weight=800,
                                letter_spacing=1.2,
                                text_align="center",
                                color="#ffffff",
                                x=max(margin, element.x),
                                y=label_y,
                                width=min(element.width, width - 2 * margin),
                                height=label_height,
                                z_index=max(1, element.z_index + 1),
                                visual_role="text",
                                content_identity=f"format-label.{element.id}",
                                start_frame=element.start_frame,
                                duration_frames=element.duration_frames,
                                reveal="none",
                                animations=[
                                    EditorialAnimationV2(
                                        property="opacity",
                                        keyframes=[
                                            MotionKeyframeV1(frame=0, value=0, easing="ease_out"),
                                            MotionKeyframeV1(
                                                frame=max(
                                                    1,
                                                    min(
                                                        composition.action_frames // 3,
                                                        element.duration_frames - 1,
                                                    ),
                                                ),
                                                value=1,
                                            ),
                                        ],
                                    )
                                ],
                            )
                        )
                        format_label_sources[label_id] = element.id
                elif composition.family == "demonstrative_interface":
                    # One viewport changes state at each event; it is not a grid of labels.
                    element.width = width - 2 * margin
                    element.height = height * 0.66
                    element.x = margin
                    element.y = (height - element.height) / 2
                    element.fit_text = element.kind in {"text", "card"}
                    if element.kind in {"image", "video"}:
                        element.object_fit = "contain"
                elif composition.family == "sequence" and any(item.kind == "path" for item in elements):
                    # A sequence with a connector is a relationship diagram, not a
                    # row of tiny source boxes. Resolve the readable geometry from
                    # semantic roles and derive the connector from the resulting
                    # media centers. This keeps the planner responsible for the
                    # subjects and the component responsible for layout.
                    media = [item for item in elements if item.kind in {"image", "video"}]
                    path = next((item for item in elements if item.kind == "path"), None)
                    if not media or path is None:
                        raise ValueError("editing_component_sequence_path_requires_media")
                    hero = next((item for item in media if item.visual_role == "hero"), media[0])
                    supports = [item for item in media if item.id != hero.id]
                    hero_width = width * (0.62 if len(supports) else 0.76)
                    hero_height = height * (0.30 if len(supports) else 0.42)
                    fit_in_box(
                        hero,
                        (width - hero_width) / 2,
                        height * 0.16,
                        hero_width,
                        hero_height,
                        allow_upscale=True,
                    )
                    hero.object_fit = "contain"
                    support_width = min(width * 0.24, (width - margin * 2 - gap * max(0, len(supports) - 1)) / max(1, len(supports)))
                    support_height = height * 0.16
                    support_total = len(supports) * support_width + max(0, len(supports) - 1) * gap
                    support_left = (width - support_total) / 2
                    for support_index, support in enumerate(supports):
                        fit_in_box(
                            support,
                            support_left + support_index * (support_width + gap),
                            height * 0.66,
                            support_width,
                            support_height,
                            allow_upscale=True,
                        )
                        support.object_fit = "contain"
                    path.x, path.y, path.width, path.height = 0, 0, width, height
                    path.points = [
                        EditorialPointV2(x=hero.x + hero.width / 2, y=hero.y + hero.height),
                        *[
                            EditorialPointV2(x=item.x + item.width / 2, y=item.y)
                            for item in supports
                        ],
                    ]
                    if len(path.points) < 2:
                        # A single-media sequence may still carry a path for
                        # emphasis. Keep it valid and visibly attached to the
                        # hero instead of emitting a one-point path.
                        path.points.append(
                            EditorialPointV2(
                                x=hero.x + hero.width / 2,
                                y=min(height - margin, hero.y + hero.height + height * 0.16),
                            )
                        )
                    path.stroke_width = max(path.stroke_width, min(width, height) * 0.008)
                    path.visual_role = "accent"
                elif editorial_sequence and not sequence_preserves_spatial_layout:
                    asymmetric = motion_system.layout == "editorial_asymmetric"
                    left = margin if motion_system.alignment == "left" else width - margin - width * 0.82
                    if element.kind in {"text", "card"}:
                        element.width = width * (0.48 if asymmetric else 0.82)
                        element.x = (margin if motion_system.alignment == "left" else width - margin - element.width)
                        element.y = height * (0.20 if motion_system.layout == "typography_dominant" else 0.34)
                        element.height = height * (0.31 if motion_system.layout == "typography_dominant" else 0.22)
                        element.text_align = motion_system.alignment
                        element.fit_text = True
                        element.font_size = min(120, max(element.font_size, width * 0.10))
                        if len(result.art_direction.palette) > 1:
                            candidate_color = result.art_direction.palette[1]
                            if isinstance(candidate_color, str) and candidate_color.startswith("#") and len(candidate_color) in {4, 7}:
                                element.color = candidate_color
                    elif element.kind in {"shape", "image", "video"}:
                        box_width = width * (0.78 if motion_system.layout == "graphic_motif" else 0.48)
                        box_height = height * (0.58 if motion_system.layout == "graphic_motif" else 0.36)
                        media_left = (
                            width - margin - box_width if motion_system.alignment == "left"
                            else margin
                        ) if asymmetric else left
                        fit_in_box(element, media_left, height * 0.23, box_width, box_height,
                                   allow_upscale=element.kind in {"image", "video"})
                        if element.kind == "shape" and len(result.art_direction.palette) > 2:
                            candidate_color = result.art_direction.palette[2]
                            if isinstance(candidate_color, str) and candidate_color.startswith("#") and len(candidate_color) in {4, 7}:
                                element.fill = candidate_color
                elif family in {"comparison", "sequence"} and not sequence_preserves_spatial_layout:
                    count = len(elements)
                    responsive_grid = family == "sequence" and height > width and count >= 4
                    if responsive_grid:
                        columns = 2
                        rows = (count + columns - 1) // columns
                        cell_width = (width - margin * 2 - gap * (columns - 1)) / columns
                        cell_height = (height - margin * 2 - gap * (rows - 1)) / rows
                        cell_x = margin + (i % columns) * (cell_width + gap)
                        cell_y = margin + (i // columns) * (cell_height + gap)
                    else:
                        cell_width = (width - margin * 2 - gap * (count - 1)) / count
                        cell_height = height - margin * 2
                        cell_x, cell_y = margin + i * (cell_width + gap), margin
                    if composition.axis == "vertical" and not responsive_grid:
                        cell_width = width - 2 * margin
                        cell_height = (height - 2 * margin - gap * (count - 1)) / count
                        cell_x, cell_y = margin, margin + i * (cell_height + gap)
                    fit_in_box(
                        element,
                        cell_x,
                        cell_y,
                        cell_width,
                        cell_height,
                        allow_upscale=element.kind in {"image", "video"},
                    )
                    if element.kind in {"image", "video"}:
                        element.object_fit = "contain"
                elif family in {"focus", "repetition"}:
                    if family == "focus":
                        fit_in_box(
                            element,
                            margin,
                            margin,
                            width - margin * 2,
                            height - margin * 2,
                            allow_upscale=element.kind in {"image", "video"},
                        )
                        if element.kind in {"image", "video"}:
                            element.object_fit = "contain"
                if family == "sequence":
                    if editorial_timing:
                        element.start_frame = sum(composition.state_hold_frames[:i]) + i * composition.movement_frames
                    elif editorial_sequence:
                        element.start_frame = sum(composition.state_hold_frames[:i])
                    else:
                        element.start_frame = i * composition.action_frames
                    element.duration_frames = scene.duration_frames - element.start_frame
                    if editorial_sequence:
                        element.duration_frames = (
                            composition.state_hold_frames[i] if i < len(elements) - 1
                            else scene.duration_frames - element.start_frame
                        )
                    if element.duration_frames <= (
                        composition.movement_frames if editorial_timing else composition.action_frames
                    ) and not editorial_sequence:
                        raise ValueError("editing_component_sequence_too_short")
                    if composition.family in {"format_transformation", "demonstrative_interface"}:
                        # Each state exits when the next arrives. Keeping every state
                        # visible would turn the demonstration back into a static grid.
                        next_frame = (
                            element.start_frame + composition.state_hold_frames[i] + composition.movement_frames
                            if editorial_timing and i < len(elements) - 1
                            else min(scene.duration_frames, (i + 1) * composition.action_frames)
                        )
                        if i < len(elements) - 1:
                            element.duration_frames = next_frame - element.start_frame + (
                                0 if editorial_timing else 1
                            )
                        if element.duration_frames <= (
                            composition.movement_frames if editorial_timing else composition.action_frames
                        ):
                            raise ValueError("editing_component_state_too_short")
                    if (
                        composition.family == "format_transformation"
                        and canonical_groups
                        and reference
                        and element.kind == "group"
                    ):
                        for child in scene.elements:
                            if child.parent_id == element.id:
                                child.start_frame = element.start_frame
                                child.duration_frames = element.duration_frames
                if family == "repetition":
                    count = composition.repeat_count
                    cell_width = (width - 2 * margin - (count - 1) * gap) / count
                    cell_height = height * 0.55
                    fit_in_box(element, margin, margin, cell_width, cell_height)
                    element.repeat_count, element.repeat_dx = count, cell_width + gap
                    if composition.axis == "vertical":
                        cell_width = width - 2 * margin
                        cell_height = (height - 2 * margin - (count - 1) * gap) / count
                        fit_in_box(element, margin, margin, cell_width, cell_height)
                        element.repeat_dx, element.repeat_dy = 0, cell_height + gap
                    element.stagger_frames = composition.action_frames
                    element.duration_frames = scene.duration_frames - (count - 1) * composition.action_frames
                    if element.duration_frames <= composition.action_frames:
                        raise ValueError("editing_component_repetition_too_short")
                if family == "continuity":
                    if not composition.previous_element_id or scene.entrance == "cut":
                        raise ValueError("editing_component_continuity_requires_prior_and_transition")
                    if composition.action_frames != scene.transition_frames:
                        raise ValueError("editing_component_continuity_duration_must_match_transition")
                    element.match_previous_element_id = composition.previous_element_id
                elif not result.intent.reduced_motion:
                    end = (
                        min(composition.movement_frames, element.duration_frames - 1)
                        if editorial_timing or editorial_sequence else composition.action_frames
                    )
                    middle = max(1, round(end * 0.58))

                    def track(prop, values):
                        return EditorialAnimationV2(property=prop, keyframes=values)

                    def from_to(prop, start, finish, easing="ease_out", end_frame=end):
                        return track(
                            prop,
                            [
                                {"frame": 0, "value": start, "easing": easing},
                                {"frame": end_frame, "value": finish},
                            ],
                        )

                    if composition.family == "annotated_material":
                        if i == 0:
                            element.animations = [
                                track(
                                    prop,
                                    [
                                        {
                                            "frame": 0,
                                            "value": 1,
                                            "easing": "cubic_bezier",
                                            "cubicBezier": [0.22, 1, 0.36, 1],
                                        },
                                        {"frame": end, "value": 1.035},
                                    ],
                                )
                                for prop in ("scale_x", "scale_y")
                            ]
                        elif element.kind in {"text", "card"}:
                            element.animations = [
                                from_to("opacity", 0, 1),
                                from_to("position_y", 24, 0),
                            ]
                        elif not element.animations:
                            element.animations = [from_to("opacity", 0, 1)]
                    elif composition.family == "format_transformation":
                        if editorial_timing:
                            element.animations = []
                            # Current geometry has now been resolved. Bind the
                            # preceding state to it rather than reading the next
                            # state's still-unresolved placeholder coordinates.
                            if i:
                                previous = elements[i - 1]
                                next_children = {
                                    child.content_part_id: child
                                    for child in scene.elements
                                    if child.parent_id == element.id and child.content_part_id
                                }
                                for child in (
                                    candidate for candidate in scene.elements if candidate.parent_id == previous.id
                                ):
                                    later = next_children.get(child.content_part_id)
                                    if later is None:
                                        continue
                                    if child.animations:
                                        raise ValueError("editing_component_editorial_child_animation_conflict")
                                    start_x = previous.x + child.x + child.width / 2
                                    start_y = previous.y + child.y + child.height / 2
                                    finish_x = element.x + later.x + later.width / 2
                                    finish_y = element.y + later.y + later.height / 2
                                    begin = composition.state_hold_frames[i - 1] - 1
                                    finish = min(previous.duration_frames - 1, begin + end)
                                    if finish <= begin:
                                        raise ValueError("editing_component_editorial_movement_too_short")
                                    uniform_scale = min(later.width / child.width, later.height / child.height)
                                    child.animations = [
                                        track("position_x", [
                                            {"frame": begin, "value": 0, "easing": "ease_in_out"},
                                            {"frame": finish, "value": finish_x - start_x},
                                        ]),
                                        track("position_y", [
                                            {"frame": begin, "value": 0, "easing": "ease_in_out"},
                                            {"frame": finish, "value": finish_y - start_y},
                                        ]),
                                        track("scale_x", [
                                            {"frame": begin, "value": 1, "easing": "ease_in_out"},
                                            {"frame": finish, "value": uniform_scale},
                                        ]),
                                        track("scale_y", [
                                            {"frame": begin, "value": 1, "easing": "ease_in_out"},
                                            {"frame": finish, "value": uniform_scale},
                                        ]),
                                    ]
                            continue
                        if i:
                            previous = elements[i - 1]
                            previous_center_x = previous.x + previous.width / 2
                            previous_center_y = previous.y + previous.height / 2
                            current_center_x = element.x + element.width / 2
                            current_center_y = element.y + element.height / 2
                            if canonical_groups and reference and element.kind == "group":
                                # Never morph a complete poster by applying different
                                # X/Y scales to its root: that deforms type and imagery.
                                # Each stable canonical part travels to its responsive
                                # destination with one uniform scale instead.
                                element.animations = [from_to("opacity", 0, 1)]
                                previous_children = {
                                    child.content_part_id: child
                                    for child in scene.elements
                                    if child.parent_id == previous.id and child.content_part_id
                                }
                                for child in (
                                    candidate for candidate in scene.elements if candidate.parent_id == element.id
                                ):
                                    prior_child = previous_children.get(child.content_part_id)
                                    if not prior_child:
                                        continue
                                    prior_center_x = previous.x + prior_child.x + prior_child.width / 2
                                    prior_center_y = previous.y + prior_child.y + prior_child.height / 2
                                    child_center_x = element.x + child.x + child.width / 2
                                    child_center_y = element.y + child.y + child.height / 2
                                    uniform_scale = min(
                                        prior_child.width / child.width,
                                        prior_child.height / child.height,
                                    )
                                    child.animations = [
                                        from_to("position_x", prior_center_x - child_center_x, 0),
                                        from_to("position_y", prior_center_y - child_center_y, 0),
                                        from_to("scale_x", uniform_scale, 1),
                                        from_to("scale_y", uniform_scale, 1),
                                    ]
                            else:
                                element.animations = [
                                    track("opacity", [{"frame": 0, "value": 1}]),
                                    from_to("position_x", previous_center_x - current_center_x, 0),
                                    from_to("position_y", previous_center_y - current_center_y, 0),
                                    from_to("scale_x", previous.width / element.width, 1),
                                    from_to("scale_y", previous.height / element.height, 1),
                                ]
                        else:
                            scale_values = (
                                [
                                    {
                                        "frame": 0,
                                        "value": 0.92,
                                        "easing": "cubic_bezier",
                                        "cubicBezier": [0.22, 1, 0.36, 1],
                                    },
                                    {"frame": middle, "value": 1.04, "easing": "ease_out"},
                                    {"frame": end, "value": 1},
                                ]
                                if end > 1
                                else [
                                    {"frame": 0, "value": 0.92, "easing": "ease_out"},
                                    {"frame": end, "value": 1},
                                ]
                            )
                            element.animations = [
                                from_to(
                                    "opacity",
                                    0,
                                    1,
                                    end_frame=max(1, min(end // 3, element.duration_frames - 2)),
                                ),
                                track("scale_x", scale_values),
                                track("scale_y", scale_values),
                            ]
                        if i < len(elements) - 1:
                            element.animations[0].keyframes.extend(
                                [
                                    MotionKeyframeV1(frame=element.duration_frames - 2, value=1),
                                    MotionKeyframeV1(frame=element.duration_frames - 1, value=0),
                                ]
                            )
                    elif composition.family == "demonstrative_interface":
                        event = (
                            composition.interface_events[i]
                            if composition.interface_events
                            else ("open" if i == 0 else "select")
                        )
                        if event == "pass":
                            element.animations = [
                                track(
                                    "opacity",
                                    [
                                        {"frame": 0, "value": 1, "easing": "ease_in_out"},
                                        {"frame": max(1, round(end * 0.7)), "value": 1, "easing": "ease_in_out"},
                                        {"frame": end, "value": 0},
                                    ],
                                ),
                                from_to("position_y", 0, -96, easing="ease_in_out"),
                            ]
                        else:
                            element.animations = [
                                from_to(
                                    "opacity",
                                    0,
                                    1,
                                    end_frame=max(1, min(end // 3, element.duration_frames - 2)),
                                ),
                            ]
                        if event == "insert":
                            element.animations.append(from_to("position_y", 96, 0))
                        elif event == "scroll":
                            element.animations.append(from_to("position_y", 48, -12))
                        elif event == "reorganize":
                            element.animations.append(from_to("position_x", 42, 0))
                        elif event == "select":
                            element.animations.extend(
                                [from_to("scale_x", 0.96, 1.03), from_to("scale_y", 0.96, 1.03)]
                            )
                        elif event == "open":
                            element.animations.extend(
                                [from_to("scale_x", 0.88, 1), from_to("scale_y", 0.88, 1)]
                            )
                        if i < len(elements) - 1 and event != "pass":
                            element.animations[0].keyframes.extend(
                                [
                                    MotionKeyframeV1(frame=element.duration_frames - 2, value=1),
                                    MotionKeyframeV1(frame=element.duration_frames - 1, value=0),
                                ]
                            )
                    elif composition.family == "continuity_comparison":
                        element.animations = (
                            [from_to("opacity", 1, 1)]
                            if i == 0
                            else [
                                from_to("opacity", 0, 1),
                                from_to("position_x", 28, 0),
                            ]
                        )
                    elif editorial_sequence:
                        if end < 1:
                            element.animations = []
                        else:
                            direction_sign = -1 if motion_system.alignment == "left" else 1
                            element.animations = [
                                from_to("position_x", direction_sign * min(width * 0.09, 65), 0,
                                        easing="ease_out", end_frame=end),
                            ]
                    else:
                        props = (
                            [("scale_x", 1, composition.focus_scale), ("scale_y", 1, composition.focus_scale)]
                            if family == "focus"
                            else [("opacity", 0, 1)]
                        )
                        element.animations = [
                            track(
                                prop,
                                [
                                    {"frame": 0, "value": start, "easing": "ease_out"},
                                    {"frame": end, "value": finish},
                                ],
                            )
                            for prop, start, finish in props
                        ]
            if family == "evidence":
                annotation_kinds = (
                    {"text", "card", "shape", "path"}
                    if composition.family == "annotated_material"
                    else {"text", "card"}
                )
                if (
                    elements[0].kind not in {"image", "video", "shape"}
                    or elements[1].kind not in annotation_kinds
                ):
                    raise ValueError("editing_component_evidence_requires_media_and_annotation")
                # A connector is meaningful for generic evidence callouts.
                # Annotated material can contain masks, spotlights and labels;
                # drawing an unconditional diagonal between the media and the
                # first annotation creates a visual artifact rather than proof.
                if composition.family == "annotated_material":
                    if not result.intent.reduced_motion:
                        group_id = "annotation-group-" + digest([scene.id, composition.id])[:20]
                        if group_id in indexed or any(
                            item.id == group_id for item in generated_annotation_groups
                        ):
                            raise ValueError("editing_component_generated_id_conflict")
                        # The media and its annotation must share the same
                        # transform tree.  Animating only the footage caused a
                        # marker to drift away from the target it purported to
                        # explain.  The parent owns the subtle focus move while
                        # child-specific reveals remain on the children.
                        media_focus_tracks = list(elements[0].animations)
                        elements[0].animations = []
                        for element in elements:
                            element.parent_id = group_id
                        generated_annotation_groups.append(
                            EditorialElementV2(
                                id=group_id,
                                kind="group",
                                purpose="Preservar o vínculo espacial entre o material e suas anotações",
                                x=0,
                                y=0,
                                width=width,
                                height=height,
                                duration_frames=scene.duration_frames,
                                visual_role="support",
                                animations=media_focus_tracks,
                            )
                        )
                    continue
                connector_id = "connector-" + digest([scene.id, composition.id])[:20]
                if connector_id in indexed:
                    raise ValueError("editing_component_generated_id_conflict")
                scene.elements.append(
                    EditorialElementV2(
                        id=connector_id,
                        kind="path",
                        purpose=composition.purpose,
                        width=width,
                        height=height,
                        duration_frames=scene.duration_frames,
                        connector_from_id=elements[0].id,
                        connector_to_id=elements[1].id,
                        points=[{"x": 0, "y": 0}, {"x": 1, "y": 1}],
                        color=elements[1].color,
                        reveal="none" if result.intent.reduced_motion else "path",
                        reveal_frames=composition.action_frames,
                    )
                )
        if generated_format_labels:
            ordered_labels = sorted(
                generated_format_labels,
                key=lambda label: indexed[format_label_sources[label.id]].start_frame,
            )
            for label_index, label in enumerate(ordered_labels):
                source = indexed[format_label_sources[label.id]]
                label.start_frame = source.start_frame
                source_end = source.start_frame + source.duration_frames
                if label_index + 1 < len(ordered_labels):
                    next_source = indexed[format_label_sources[ordered_labels[label_index + 1].id]]
                    source_end = min(source_end, next_source.start_frame)
                label.duration_frames = max(1, source_end - label.start_frame)
                for animation in label.animations:
                    animation.keyframes = [
                        keyframe
                        for keyframe in animation.keyframes
                        if keyframe.frame < label.duration_frames
                    ]
                    if len(animation.keyframes) == 1 and label.duration_frames > 1:
                        animation.keyframes.append(
                            MotionKeyframeV1(frame=label.duration_frames - 1, value=1)
                        )
            scene.elements.extend(generated_format_labels)
        if generated_annotation_groups:
            scene.elements.extend(generated_annotation_groups)
    if result.semantic_verification_policy == "legacy_execution_v1":
        # Historical directions were persisted with the generic path field on
        # non-path elements. Preserve their visual intent while making the
        # payload consumable by the stricter current schema. New directions
        # still fail validation at the boundary instead of being repaired.
        for legacy_scene in result.scenes:
            for legacy_element in legacy_scene.elements:
                if legacy_element.path_mode in {"polyline", "quadratic"} and not legacy_element.points:
                    legacy_element.points = [
                        EditorialPointV2(x=0.0, y=0.0),
                        EditorialPointV2(x=0.0, y=0.0),
                    ]
    return ContextualPlanRequestV2.model_validate(result.model_dump(mode="json", by_alias=True))
