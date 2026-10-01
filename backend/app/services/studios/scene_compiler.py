"""Compile editorial decisions into the existing document, timeline and motion graph."""

from __future__ import annotations

import math
from datetime import UTC, datetime

from ...domain.studios.contextual_editing import ContextualOperationV1, digest
from ...domain.studios.contextual_editing_v2 import (
    ContextualPlanRequestV2,
    EditorialElementV2,
    EditorialMotionCueV2,
    EditorialTextSpanV2,
)
from ...domain.studios.contracts import (
    AudioClipV1,
    AudioTrackV1,
    CreativeLayerV1,
    MediaTimelineV1,
)
from ...domain.studios.motion import (
    PROPERTY_UNITS,
    MotionAudioEventV1,
    MotionGraphV1,
    MotionNodeV1,
    MotionTrackV1,
    MotionTransitionV1,
)

COMPONENTS = {
    "typography": {"renderer": "hyperframes", "operations": ["text", "word_reveal", "kinetic_keyword"]},
    "groups": {"renderer": "hyperframes", "operations": ["group", "repeat", "stagger"]},
    "paths": {"renderer": "hyperframes", "operations": ["polyline", "path_reveal"]},
    "depth": {"renderer": "hyperframes", "operations": ["mask", "occlusion", "wipe", "layer_blur", "parallax"]},
    "effects": {
        "renderer": "hyperframes",
        "operations": ["ordered_filter_stack", "blend_mode"],
    },
    "panels": {"renderer": "hyperframes", "operations": ["card", "image", "video"]},
    "semantic_compositions": {
        "renderer": "hyperframes",
        "operations": [
            "annotated_material",
            "format_transformation",
            "demonstrative_interface",
            "continuity_comparison",
        ],
    },
    "continuity": {
        "renderer": "hyperframes",
        "operations": [
            "cut",
            "dissolve",
            "wipe",
            "match_transform",
            "opacity",
            "transform",
            "camera",
            "overshoot",
        ],
    },
    "sound_events": {"renderer": "ffmpeg", "operations": ["mix", "fade", "ducking", "silence"]},
}
COMPILER_VERSION = "res.scene-compiler.v2.15"
COMPONENTS_VERSION = "res.editorial-components.v2.20"
RUNTIME_VERSION = "res.editorial-runtime.v2.5"
VISUAL_AUDIT_POLICY_VERSION = "studio.visual-audit-policy.v4"


def current_execution_versions():
    from ...domain.studios.contextual_editing_v2 import EditorialExecutionVersionsV2

    return EditorialExecutionVersionsV2(
        compiler=COMPILER_VERSION,
        components=COMPONENTS_VERSION,
        runtime=RUNTIME_VERSION,
        visual_audit_policy=VISUAL_AUDIT_POLICY_VERSION,
    )


def pin_current_execution_versions(direction):
    """Pin new provider output to server-owned executable versions."""
    current = current_execution_versions()
    if direction.execution_versions == current:
        return []
    before = (
        direction.execution_versions.model_dump(mode="json", by_alias=True)
        if direction.execution_versions
        else None
    )
    direction.execution_versions = current
    return [
        {
            "reason": "execution_versions_pinned_by_server",
            "before": before,
            "after": current.model_dump(mode="json", by_alias=True),
            "classification": "bounded_normalization",
            "requiresAlternative": False,
        }
    ]


def require_supported_execution_versions(direction):
    versions = direction.execution_versions
    if versions is None:  # Plans persisted before execution pinning remain readable.
        return
    supported = {
        (
            "res.scene-compiler.v2.14",
            "res.editorial-components.v2.20",
            "res.editorial-runtime.v2.5",
            "studio.visual-audit-policy.v4",
        ),
        (
            "res.scene-compiler.v2.12",
            "res.editorial-components.v2.18",
            "res.editorial-runtime.v2.5",
            "studio.visual-audit-policy.v4",
        ),
        (
            "res.scene-compiler.v2.11",
            "res.editorial-components.v2.16",
            "res.editorial-runtime.v2.5",
            "studio.visual-audit-policy.v3",
        ),
        (
            "res.scene-compiler.v2.11",
            "res.editorial-components.v2.17",
            "res.editorial-runtime.v2.5",
            "studio.visual-audit-policy.v3",
        ),
        (
            "res.scene-compiler.v2.10",
            "res.editorial-components.v2.15",
            "res.editorial-runtime.v2.4",
            "studio.visual-audit-policy.v2",
        ),
        (
            "res.scene-compiler.v2.6",
            "res.editorial-components.v2.6",
            "res.editorial-runtime.v2.3",
            "studio.visual-audit-policy.v2",
        ),
        (
            "res.scene-compiler.v2.5",
            "res.editorial-components.v2.5",
            "res.editorial-runtime.v2.3",
            "studio.visual-audit-policy.v2",
        ),
        (
            COMPILER_VERSION,
            COMPONENTS_VERSION,
            RUNTIME_VERSION,
            VISUAL_AUDIT_POLICY_VERSION,
        ),
        (
            "res.scene-compiler.v2.5",
            "res.editorial-components.v2.4",
            "res.editorial-runtime.v2.3",
            "studio.visual-audit-policy.v2",
        ),
        (
            "res.scene-compiler.v2.4",
            "res.editorial-components.v2.4",
            "res.editorial-runtime.v2.3",
            "studio.visual-audit-policy.v2",
        ),
        (
            "res.scene-compiler.v2.3",
            "res.editorial-components.v2.3",
            "res.editorial-runtime.v2.3",
            "studio.visual-audit-policy.v2",
        ),
        (
            "res.scene-compiler.v2.2",
            "res.editorial-components.v2.2",
            "res.editorial-runtime.v2.2",
            "studio.visual-audit-policy.v2",
        ),
    }
    selected = (
        versions.compiler,
        versions.components,
        versions.runtime,
        versions.visual_audit_policy,
    )
    if selected not in supported:
        raise ValueError(
            "editing_v2_execution_version_unavailable:"
            + versions.model_dump_json(by_alias=True)
        )


def _materialize_keyword_cues(direction, width, height):
    result = direction.model_copy(deep=True)
    for scene in result.scenes:
        known = {element.id for element in scene.elements}
        for cue in scene.keyword_cues:
            candidates = []
            textual_matches = []
            for element in scene.elements:
                if element.kind not in {"text", "card"} or element.after_element_id:
                    continue
                start = element.text.casefold().find(cue.text.casefold())
                if start < 0:
                    continue
                textual_matches.append(element.id)
                if element.text.casefold().find(cue.text.casefold(), start + 1) >= 0:
                    continue
                end = start + len(cue.text)
                overlapping = [span for span in element.text_spans if span.start < end and start < span.end]
                if overlapping:
                    # An explicit source-bound span is more specific than a
                    # scene-level keyword cue. Keeping it avoids rendering a
                    # duplicate phrase or two animations on the same glyphs.
                    candidates.append((element, start, end, None, None, True))
                    continue
                element_end = element.start_frame + element.duration_frames
                duration = min(cue.duration_frames, element.duration_frames)
                cue_start = min(max(cue.start_frame, element.start_frame), element_end - duration)
                candidates.append((element, start, end, cue_start, duration, False))
            if len(candidates) == 1:
                element, start, end, cue_start, cue_duration, covered = candidates[0]
                if covered:
                    continue
                element.text_spans.append(
                    EditorialTextSpanV2(
                        id="keyword-" + cue.id,
                        start=start,
                        end=end,
                        purpose=cue.purpose,
                        color=cue.highlight_color,
                        font_weight=min(900, element.font_weight + 100),
                        scale=1.06 if cue.profile == "emphasis" else 1,
                        start_frame=cue_start - element.start_frame,
                        duration_frames=cue_duration,
                        profile=cue.profile,
                    )
                )
                element.text_spans.sort(key=lambda item: (item.start, item.end, item.id))
                continue
            if textual_matches:
                raise ValueError(
                    "editing_v2_keyword_source_binding_ambiguous"
                    if len(textual_matches) > 1
                    else "editing_v2_keyword_source_binding_invalid"
                )
            if cue.source_excerpt.strip().casefold() != cue.text.strip().casefold():
                raise ValueError("editing_v2_keyword_source_binding_required")
            element_id = "keyword-" + cue.id
            if element_id in known:
                raise ValueError("editing_v2_keyword_generated_id_conflict")
            y = {"top": height * 0.12, "center": height * 0.44, "bottom": height * 0.74}[cue.position]
            scene.elements.append(
                EditorialElementV2(
                    id=element_id,
                    kind="text",
                    purpose=cue.purpose,
                    visual_role="text",
                    start_frame=cue.start_frame,
                    duration_frames=cue.duration_frames,
                    x=width * 0.08,
                    y=y,
                    width=width * 0.84,
                    height=min(240, height * 0.16),
                    z_index=9000,
                    text=cue.text,
                    concise_text=cue.text,
                    text_role="support",
                    fit_text=True,
                    font_size=min(112, width * 0.1),
                    text_align="center",
                    reveal="words",
                    reveal_frames=min(12, cue.duration_frames - 1),
                    motion_cues=[
                        EditorialMotionCueV2(
                            kind="emphasis" if cue.profile == "emphasis" else "entrance",
                            profile=cue.profile,
                            start_frame=0,
                            duration_frames=min(18, cue.duration_frames),
                            rationale=cue.purpose,
                        )
                    ],
                )
            )
            known.add(element_id)
    return ContextualPlanRequestV2.model_validate(result.model_dump(mode="json", by_alias=True))


def _place_generated_keyword_layers(direction, width, height):
    """Place derived keyword cards in the least occupied safe vertical band."""

    result = direction.model_copy(deep=True)

    def active_together(left, right):
        return not (
            left.start_frame + left.duration_frames <= right.start_frame
            or right.start_frame + right.duration_frames <= left.start_frame
        )

    def overlap_ratio(left, right, candidate_y):
        intersection_x = max(
            0,
            min(left.x + left.width, right.x + right.width) - max(left.x, right.x),
        )
        intersection_y = max(
            0,
            min(candidate_y + left.height, right.y + right.height) - max(candidate_y, right.y),
        )
        return (intersection_x * intersection_y) / max(
            1, min(left.width * left.height, right.width * right.height)
        )

    bands = (height * 0.08, height * 0.42, height * 0.78)
    for scene in result.scenes:
        text = [element for element in scene.elements if element.kind in {"text", "card"}]
        for element in [item for item in text if item.id.startswith("keyword-")]:
            peers = [
                other
                for other in text
                if other.id != element.id and active_together(element, other)
            ]
            if not peers:
                continue
            candidates = [min(max(0.0, y), max(0.0, height - element.height)) for y in bands]
            element.y = min(
                (
                    max((overlap_ratio(element, peer, y) for peer in peers), default=0),
                    y,
                )
                for y in candidates
            )[1]
    return ContextualPlanRequestV2.model_validate(result.model_dump(mode="json", by_alias=True))


def _estimated_text_width(text, font_size):
    return sum(
        font_size
        * (
            0.30
            if character.isspace()
            else 0.30
            if character in ".,;:!|iIl'"
            else 0.72
            if character.isupper() or character in "mwMW@"
            else 0.55
        )
        for character in text
    )


def _wrapped_line_count(text, width, font_size):
    lines = 0
    for paragraph in text.splitlines() or [""]:
        lines += 1
        occupied = 0.0
        for word in paragraph.split():
            word_width = _estimated_text_width(word, font_size)
            gap = font_size * 0.30 if occupied else 0
            if occupied and occupied + gap + word_width > width:
                lines += 1
                occupied = word_width
            else:
                occupied += gap + word_width
    return max(1, lines)


def _normalize_text_layout(direction, width, height):
    """Make model-authored text boxes measurable without clipping content."""
    result = direction.model_copy(deep=True)
    for scene in result.scenes:
        indexed = {element.id: element for element in scene.elements}
        for element in scene.elements:
            if element.kind not in {"text", "card"} or not element.text:
                continue
            element.fit_text = True
            parent = indexed.get(element.parent_id) if element.parent_id else None
            container_width = parent.width if parent else width
            container_height = parent.height if parent else height
            margin = min(container_width, container_height) * (0.04 if parent else 0.07)
            available_width = max(1, container_width - 2 * margin)
            available_height = max(1, container_height - 2 * margin)
            minimum_font_size = width * 16 / 300
            # HyperFrames enforces this same minimum after fonts load. Measure
            # at that effective size here so recompilation cannot reproduce an
            # overflow that only appears in the browser runtime.
            font_size = max(element.font_size, minimum_font_size)
            padding = 32 if element.kind == "card" else 0
            longest_word = max(element.text.split(), key=len, default="")
            minimum_width = _estimated_text_width(longest_word, font_size) + padding
            while minimum_width > available_width and font_size > minimum_font_size:
                font_size = max(minimum_font_size, font_size - 1)
                minimum_width = _estimated_text_width(longest_word, font_size) + padding
            if minimum_width > element.width:
                center_x = element.x + element.width / 2
                element.width = min(available_width, minimum_width)
                element.x = min(
                    max(margin, center_x - element.width / 2),
                    container_width - margin - element.width,
                )
            while True:
                content_width = max(1, element.width - padding)
                lines = _wrapped_line_count(element.text, content_width, font_size)
                required = math.ceil(lines * font_size * element.line_height + 10 + padding)
                if required <= available_height or font_size <= minimum_font_size:
                    break
                font_size = max(minimum_font_size, font_size - 1)
            element.font_size = font_size
            element.height = min(available_height, max(element.height, required))
            element.x = min(max(margin, element.x), container_width - margin - element.width)
            element.y = min(
                max(margin, element.y),
                container_height - margin - element.height,
            )
    return ContextualPlanRequestV2.model_validate(result.model_dump(mode="json", by_alias=True))


def _infer_unambiguous_focus(direction):
    """Keep older single-element V2 scenes usable without guessing among peers."""
    result = direction.model_copy(deep=True)
    for scene in result.scenes:
        if any(element.visual_role == "hero" for element in scene.elements):
            continue
        candidates = [
            element
            for element in scene.elements
            if element.visual_role not in {"background", "accent"}
            and element.kind not in {"path"}
        ]
        if len(candidates) == 1:
            candidates[0].visual_role = "hero"
    return ContextualPlanRequestV2.model_validate(result.model_dump(mode="json", by_alias=True))


def prepare_direction(direction, width, height):
    from .editorial_components import lower_compositions

    lowered = lower_compositions(_materialize_keyword_cues(direction, width, height), width, height)
    return _normalize_text_layout(_place_generated_keyword_layers(lowered, width, height), width, height)


def target_id(scene, element, instance=0):
    return "ed2-" + digest([scene, element, instance])[:24]


def executable_composition_digest(page, timeline, graph):
    return digest(
        {
            "page": page.model_dump(mode="json", by_alias=True),
            "timeline": timeline.model_dump(mode="json", by_alias=True),
            "motion": {
                "nodes": [item.model_dump(mode="json", by_alias=True) for item in graph.nodes],
                "tracks": [item.model_dump(mode="json", by_alias=True) for item in graph.tracks],
                "transitions": [item.model_dump(mode="json", by_alias=True) for item in graph.transitions],
                "audioEvents": [item.model_dump(mode="json", by_alias=True) for item in graph.audio_events],
            },
        }
    )


def compile_scenes(document, direction: ContextualPlanRequestV2, user_id, plan_id):
    require_supported_execution_versions(direction)
    if document.revision != direction.expected_document_revision:
        raise ValueError("editing_document_conflict")
    from .editorial_components import VERSION, motion_cue_keyframes

    composition_decisions = [
        {"sceneId": s.id, **c.model_dump(mode="json", by_alias=True)} for s in direction.scenes for c in s.compositions
    ]
    canvas = document.composition.pages[0]
    source_direction = direction
    direction = _infer_unambiguous_focus(prepare_direction(direction, canvas.width, canvas.height))
    draft = document.model_copy(deep=True)
    draft.content_references = [
        reference.model_dump(mode="json", by_alias=True) for reference in direction.content_references
    ]
    page = draft.composition.pages[0].model_copy(deep=True)
    page.layers = []
    preserved = " ".join(" ".join([s.narration, *[e.text for e in s.elements]]) for s in direction.scenes)
    if any(" ".join(f.split()) not in " ".join(preserved.split()) for f in direction.intent.locked_facts):
        raise ValueError("editing_v2_locked_fact_missing")
    total = sum(s.duration_frames - (s.transition_frames if s.entrance != "cut" else 0) for s in direction.scenes)
    fps = direction.frame_rate.numerator / direction.frame_rate.denominator
    page.duration_ms = round(total / fps * 1000)
    timeline = MediaTimelineV1(frame_rate=direction.frame_rate, duration_frames=total)
    assets = {a.id: a for a in document.assets}
    tracks, nodes, events, operations, missing, manifest = [], [], [], [], [], []
    scene_manifest = []
    silence_regions = []
    cursor = 0
    transitions, previous_root, previous_duration, previous_elements, previous_layer_ids = [], None, 0, {}, {}

    def operation(scene, element, layer_id, kind, start, duration, reason):
        operations.append(
            ContextualOperationV1(
                operation_id="op-" + digest([scene.id, element, layer_id, kind])[:24],
                kind=kind,
                beat_id=scene.id,
                target_id=layer_id,
                rationale=reason,
                expected_result="; ".join(scene.verification)[:2000],
                technique_ids=scene.technique_ids,
                evidence_ids=["scene:" + scene.id],
                confidence=1,
            )
        )
        manifest.append(
            {
                "sceneId": scene.id,
                "elementId": element,
                "targetId": layer_id,
                "startFrame": start,
                "durationFrames": duration,
                "kind": kind,
                "rationale": reason,
            }
        )

    def require(asset_id, scene, element, role, media_prefix=None):
        asset = assets.get(asset_id)
        if asset is None or asset.rights_status != "verified" or not asset.checksum:
            missing.append(
                {
                    "sceneId": scene.id,
                    "elementId": element,
                    "role": role,
                    "assetId": asset_id,
                    "reason": "verified_material_required",
                }
            )
            return False
        if media_prefix and not asset.media_type.startswith(media_prefix):
            raise ValueError("editing_v2_material_type_mismatch")
        return True

    for scene in direction.scenes:
        root_id = target_id(scene.id, "scene-root")
        role_group_ids = {
            "background": target_id(scene.id, "background-group"),
            "content": target_id(scene.id, "content-group"),
            "text": target_id(scene.id, "text-group"),
        }
        if scene.entrance != "cut":
            if scene.transition_frames >= previous_duration:
                raise ValueError("editing_v2_transition_out_of_previous_scene")
            cursor -= scene.transition_frames
            transitions.append(
                MotionTransitionV1(
                    transition_id="transition-" + root_id,
                    kind="dissolve" if direction.intent.reduced_motion else scene.entrance,
                    reduced_motion_kind="dissolve",
                    from_layer_id=previous_root,
                    to_layer_id=root_id,
                    start_frame=cursor,
                    end_frame_exclusive=cursor + scene.transition_frames,
                    motivation=scene.purpose,
                )
            )
        scene_manifest.append(
            {
                "sceneId": scene.id,
                "startFrame": cursor,
                "durationFrames": scene.duration_frames,
                "purpose": scene.purpose,
                "verification": scene.verification,
                "sceneDigest": digest(scene),
                "visualStates": [
                    {**state.model_dump(mode="json", by_alias=True), "absoluteFrame": cursor + state.frame}
                    for state in scene.visual_states
                ],
                "observationCues": [
                    {
                        **cue.model_dump(mode="json", by_alias=True),
                        "absoluteStartFrame": cursor + cue.start_frame,
                        "absoluteEndFrameExclusive": cursor + cue.end_frame_exclusive,
                    }
                    for cue in scene.observation_cues
                ],
                "semanticAssertions": [
                    {
                        **assertion.model_dump(mode="json", by_alias=True),
                        "absoluteStartFrame": cursor + assertion.start_frame,
                        "absoluteEndFrameExclusive": cursor + assertion.end_frame_exclusive,
                    }
                    for assertion in scene.semantic_assertions
                ],
                "shotPlan": [
                    {
                        **shot.model_dump(mode="json", by_alias=True),
                        **(
                            {
                                "absoluteStartFrame": cursor + shot.start_frame,
                                "absoluteEndFrameExclusive": cursor + shot.end_frame_exclusive,
                            }
                            if shot.start_frame is not None
                            else {}
                        ),
                    }
                    for shot in scene.shot_plan
                ],
            }
        )
        page.layers.append(
            CreativeLayerV1(
                id=root_id,
                kind="group",
                width=page.width,
                height=page.height,
                z_index=len(transitions) + len(manifest) + 1,
                properties={
                    "editorialTiming": {
                        "startFrame": cursor,
                        "durationFrames": scene.duration_frames,
                        "fps": fps,
                        "reveal": "none",
                    },
                    "editorialAuditFrames": [
                        cursor + state.frame for state in scene.visual_states
                    ]
                    + [
                        cursor + frame
                        for cue in scene.observation_cues
                        for frame in (cue.start_frame, cue.end_frame_exclusive - 1)
                    ]
                    + [
                        cursor
                        + assertion.start_frame
                        + round(
                            index
                            * (assertion.end_frame_exclusive - assertion.start_frame - 1)
                            / max(1, max(3, len(assertion.target_ids)) - 1)
                        )
                        for assertion in scene.semantic_assertions
                        for index in range(max(3, len(assertion.target_ids)))
                    ],
                },
            )
        )
        root_node = MotionNodeV1(node_id="node-" + root_id, target_layer_id=root_id)
        nodes.append(root_node)
        role_nodes = {}
        for role, group_id in role_group_ids.items():
            page.layers.append(
                CreativeLayerV1(
                    id=group_id,
                    kind="group",
                    width=page.width,
                    height=page.height,
                    z_index={"background": 0, "content": 1, "text": 2}[role],
                    properties={
                        "editorialRole": role,
                        "editorialTiming": {
                            "startFrame": cursor,
                            "durationFrames": scene.duration_frames,
                            "fps": fps,
                            "reveal": "none",
                        },
                    },
                )
            )
            role_nodes[role] = MotionNodeV1(
                node_id="node-" + group_id,
                target_layer_id=group_id,
                parent_node_id="node-" + root_id,
            )
            nodes.append(role_nodes[role])
        if (
            direction.execution_scope != "visual_only"
            and scene.narration
            and not any(a.role == "narration" and a.asset_id for a in scene.audio)
        ):
            missing.append(
                {
                    "sceneId": scene.id,
                    "elementId": scene.id,
                    "role": "narration",
                    "assetId": None,
                    "reason": "narration_audio_required",
                }
            )
        indexed = {e.id: e for e in scene.elements}
        current_layer_ids = {}
        matched_prior_ids = set()
        starts = {}
        positions = {}

        def position_of(element, positions=positions, indexed=indexed):
            if element.id not in positions:
                x, y = element.x, element.y
                if element.alignment:
                    reference = indexed[element.alignment.target_id]
                    rx, ry = position_of(reference)
                    if element.alignment.horizontal:
                        ratio = {"left": 0, "center": 0.5, "right": 1}[element.alignment.horizontal]
                        x = rx + (reference.width - element.width) * ratio + element.x
                    if element.alignment.vertical:
                        ratio = {"top": 0, "middle": 0.5, "bottom": 1}[element.alignment.vertical]
                        y = ry + (reference.height - element.height) * ratio + element.y
                positions[element.id] = x, y
            return positions[element.id]

        def start_of(element, starts=starts, indexed=indexed):
            if element.id not in starts:
                before = indexed.get(element.after_element_id)
                starts[element.id] = element.start_frame + (start_of(before) + before.duration_frames if before else 0)
            return starts[element.id]

        # One page and explicit frame gates make scene boundaries independent of wall time.
        page.layers.append(
            CreativeLayerV1(
                id=target_id(scene.id, "background"),
                kind="shape",
                width=page.width,
                height=page.height,
                z_index=0,
                properties={
                    "fill": scene.background,
                    "editorialTiming": {
                        "startFrame": cursor,
                        "durationFrames": scene.duration_frames,
                        "fps": fps,
                        "reveal": "none",
                    },
                },
            )
        )
        nodes.append(
            MotionNodeV1(
                node_id="node-" + target_id(scene.id, "background"),
                target_layer_id=target_id(scene.id, "background"),
                parent_node_id="node-" + role_group_ids["background"],
            )
        )
        for element in scene.elements:
            start = start_of(element)
            if element.parent_id:
                parent = indexed[element.parent_id]
                if (
                    start < start_of(parent)
                    or start + element.duration_frames > start_of(parent) + parent.duration_frames
                ):
                    raise ValueError("editing_v2_child_out_of_parent_interval")
            if (
                start + element.duration_frames + (element.repeat_count - 1) * element.stagger_frames
                > scene.duration_frames
            ):
                raise ValueError("editing_v2_element_out_of_scene")
            if element.kind in {"image", "video"}:
                require(element.asset_id, scene, element.id, "asset", element.kind + "/")
            if element.mask_asset_id:
                require(element.mask_asset_id, scene, element.id, "mask", "image/")
            if element.font_asset_id:
                require(element.font_asset_id, scene, element.id, "font", "font/")
            if element.text_role in {"fact", "caption"} and element.text not in (
                direction.intent.script + " " + scene.narration + " " + " ".join(scene.facts)
            ):
                raise ValueError("editing_v2_text_source_required")
            for instance in range(element.repeat_count):
                x, y = position_of(element)
                layer_id = target_id(scene.id, element.id, instance)
                if instance == 0:
                    current_layer_ids[element.id] = layer_id
                local_start = start + instance * element.stagger_frames
                absolute_start = cursor + local_start
                props = {
                    "editorialSceneId": scene.id,
                    **({"nativeComponent": component.model_dump(mode="json", by_alias=True)}
                       if (component := next(
                           (c for c in scene.native_components if element.id in c.target_ids), None
                       )) else {}),
                    "editorialOperationIds": [
                        binding.technique_id for binding in scene.operation_bindings if element.id in binding.target_ids
                    ],
                    "editorialTiming": {
                        "startFrame": absolute_start,
                        "durationFrames": element.duration_frames,
                        "fps": fps,
                        "reveal": "none" if direction.intent.reduced_motion else element.reveal,
                        "revealFrames": element.reveal_frames,
                    },
                    "fill": element.fill,
                    "color": element.color,
                    "text": element.text,
                    "fontSize": element.font_size,
                    "editorialTextFit": element.fit_text,
                    "editorialConnector": {
                        "from": target_id(scene.id, element.connector_from_id),
                        "to": target_id(scene.id, element.connector_to_id),
                    }
                    if element.connector_from_id
                    else None,
                    "fontWeight": element.font_weight,
                    "letterSpacing": element.letter_spacing,
                    "lineHeight": element.line_height,
                    "textAlign": element.text_align,
                    "editorialTextSpans": [
                        span.model_dump(mode="json", by_alias=True) for span in element.text_spans
                    ],
                    "editorialShadow": element.shadow.model_dump() if element.shadow else None,
                    "editorialEffects": [
                        effect.model_dump(mode="json", by_alias=True) for effect in element.effects
                    ],
                    "editorialBlendMode": element.blend_mode,
                    "editorialBorder": {"width": element.border_width, "color": element.border_color},
                    "fontAssetId": element.font_asset_id,
                    "borderRadius": element.radius,
                    "shape": element.shape,
                    "assetId": element.asset_id,
                    "editorialContentIdentity": element.content_identity,
                    "editorialContentReferenceId": element.content_reference_id,
                    "editorialContentPartId": element.content_part_id,
                    "maskAssetId": element.mask_asset_id,
                    "objectFit": element.object_fit,
                    "editorialRegionOfInterest": (
                        element.region_of_interest.model_dump(mode="json", by_alias=True)
                        if element.region_of_interest
                        else None
                    ),
                    "editorialCropIntentional": element.crop_intentional,
                    "sourceStartSeconds": element.source_start_seconds,
                    "playbackRate": element.playback_rate,
                    "editorialVisualRole": element.visual_role,
                    "editorialDepth": element.depth_treatment.model_dump(mode="json", by_alias=True),
                }
                if element.kind == "path":
                    props["editorialPath"] = {
                        "points": [p.model_dump() for p in element.points],
                        "strokeWidth": element.stroke_width,
                        "mode": element.path_mode,
                    }
                if element.kind == "card":
                    props["editorialCard"] = True
                layer = CreativeLayerV1(
                    id=layer_id,
                    kind="shape" if element.kind == "path" else "text" if element.kind == "card" else element.kind,
                    name=element.id,
                    x=x + instance * element.repeat_dx,
                    y=y + instance * element.repeat_dy,
                    width=element.width,
                    height=element.height,
                    rotation=element.rotation,
                    opacity=element.depth_treatment.opacity,
                    z_index=min(10000, 1 + element.z_index),
                    properties=props,
                )
                page.layers.append(layer)
                nodes.append(
                    MotionNodeV1(
                        node_id="node-" + layer_id,
                        target_layer_id=layer_id,
                        parent_node_id="node-"
                        + (
                            target_id(scene.id, element.parent_id)
                            if element.parent_id
                            else role_group_ids[
                                "background"
                                if element.visual_role == "background"
                                else "text"
                                if element.visual_role == "text" or element.kind == "text"
                                else "content"
                            ]
                        ),
                        transform_origin_x=element.origin_x,
                        transform_origin_y=element.origin_y,
                    )
                )
                animations = element.animations if not direction.intent.reduced_motion else []
                if element.match_previous_element_id:
                    prior = previous_elements.get(element.match_previous_element_id)
                    if (
                        not prior
                        or scene.entrance == "cut"
                        or element.parent_id
                        or prior.parent_id
                        or element.alignment
                        or prior.alignment
                        or element.repeat_count != 1
                        or prior.repeat_count != 1
                        or prior.animations
                        or animations
                        or element.kind not in {"text", "card", "image", "shape"}
                        or prior.kind != element.kind
                        or (prior.origin_x, prior.origin_y, element.origin_x, element.origin_y) != (0.5, 0.5, 0.5, 0.5)
                        or (
                            (prior.rotation or element.rotation)
                            and abs(prior.width / element.width - prior.height / element.height) > 1e-6
                        )
                        or prior.after_element_id
                        or prior.start_frame > previous_duration - scene.transition_frames
                        or prior.start_frame + prior.duration_frames <= previous_duration - scene.transition_frames
                        or element.duration_frames <= scene.transition_frames
                        or element.match_previous_element_id in matched_prior_ids
                        or element.start_frame != 0
                        or element.after_element_id
                    ):
                        raise ValueError("editing_v2_match_transform_incompatible")
                    matched_prior_ids.add(element.match_previous_element_id)
                    if not direction.intent.reduced_motion:
                        from ...domain.studios.contextual_editing_v2 import EditorialAnimationV2

                        # Transfer this visual identity to a temporary overlay during
                        # the scene blend. Otherwise the outgoing copy remains visible
                        # while the incoming copy moves through a different position.
                        prior_layer_id = previous_layer_ids.get(prior.id)
                        if not prior_layer_id:
                            raise ValueError("editing_v2_match_transform_incompatible")
                        layer.properties["editorialMatch"] = {
                            "previousLayerId": prior_layer_id,
                            "parentLayerId": root_id,
                            "startFrame": cursor,
                            "endFrameExclusive": cursor + scene.transition_frames,
                        }
                        end = min(scene.transition_frames, element.duration_frames - 1)
                        values = {
                            "position_x": (
                                prior.x + prior.width * prior.origin_x - element.x - element.width * element.origin_x,
                                0,
                            ),
                            "position_y": (
                                prior.y + prior.height * prior.origin_y - element.y - element.height * element.origin_y,
                                0,
                            ),
                            "scale_x": (prior.width / element.width, 1),
                            "scale_y": (prior.height / element.height, 1),
                            "rotation_degrees": (prior.rotation, element.rotation),
                        }
                        animations = [
                            EditorialAnimationV2(
                                property=prop,
                                keyframes=[
                                    {"frame": 0, "value": first, "easing": "ease_in_out"},
                                    {"frame": end, "value": last},
                                ],
                            )
                            for prop, (first, last) in values.items()
                        ]
                explicit_properties = {animation.property for animation in animations}
                cue_tracks = {}
                if not direction.intent.reduced_motion:
                    for cue in element.motion_cues:
                        generated = motion_cue_keyframes(cue)
                        overlap = explicit_properties & set(generated)
                        if overlap:
                            raise ValueError("editing_v2_motion_cue_property_conflict")
                        for prop, keyframes in generated.items():
                            frames = cue_tracks.setdefault(prop, [])
                            known_frames = {keyframe.frame for keyframe in frames}
                            if known_frames & {keyframe.frame for keyframe in keyframes}:
                                raise ValueError("editing_v2_motion_cue_frame_conflict")
                            frames.extend(keyframes)
                for prop, keyframes in cue_tracks.items():
                    tracks.append(
                        MotionTrackV1(
                            track_id=layer_id + "-cue-" + prop,
                            target_layer_id=layer_id,
                            property=prop,
                            unit=PROPERTY_UNITS[prop],
                            keyframes=[
                                keyframe.model_copy(update={"frame": keyframe.frame + absolute_start})
                                for keyframe in sorted(keyframes, key=lambda item: item.frame)
                            ],
                        )
                    )
                for animation in animations:
                    tracks.append(
                        MotionTrackV1(
                            track_id=layer_id + "-" + animation.property,
                            target_layer_id=layer_id,
                            property=animation.property,
                            unit=PROPERTY_UNITS[animation.property],
                            keyframes=[
                                k.model_copy(update={"frame": k.frame + absolute_start}) for k in animation.keyframes
                            ],
                        )
                    )
                if not animations and not cue_tracks:
                    tracks.append(
                        MotionTrackV1(
                            track_id=layer_id + "-static",
                            target_layer_id=layer_id,
                            property="opacity",
                            unit="ratio",
                            # Keep the declared depth opacity in the executable graph.
                            # A constant 1 here used to erase visual subordination at render time.
                            keyframes=[
                                {
                                    "frame": absolute_start,
                                    "value": element.depth_treatment.opacity,
                                }
                            ],
                        )
                    )
                operation(
                    scene,
                    element.id,
                    layer_id,
                    "compose_" + element.kind,
                    absolute_start,
                    element.duration_frames,
                    element.purpose,
                )
                manifest[-1]["source"] = (
                    {
                        "assetId": element.asset_id,
                        "checksum": assets[element.asset_id].checksum if element.asset_id in assets else None,
                        "startSeconds": element.source_start_seconds,
                        "durationSeconds": element.duration_frames / fps * element.playback_rate,
                    }
                    if element.kind == "video"
                    else None
                )
                if (
                    direction.execution_scope != "visual_only"
                    and element.kind == "video"
                    and element.asset_id in assets
                    and element.source_audio == "preserve"
                ):
                    audio_id = layer_id + "-source-audio"
                    timeline.tracks.append(
                        AudioTrackV1(
                            id="track-" + audio_id,
                            name="dialogue",
                            clips=[
                                AudioClipV1(
                                    id=audio_id,
                                    asset_id=element.asset_id,
                                    label="dialogue",
                                    playback_rate=element.playback_rate,
                                    timeline={"startFrame": absolute_start, "durationFrames": element.duration_frames},
                                    source={
                                        "startMicroseconds": round(element.source_start_seconds * 1e6),
                                        "durationMicroseconds": round(element.duration_frames / fps * element.playback_rate * 1e6),
                                    },
                                )
                            ],
                        )
                    )
                    operation(
                        scene,
                        element.id,
                        audio_id,
                        "audio_mix",
                        absolute_start,
                        element.duration_frames,
                        "Preservar o áudio sincronizado do material de origem.",
                    )

        if scene.camera_cues and not direction.intent.reduced_motion:
            cue = scene.camera_cues[0]
            camera_start = cursor + cue.start_frame
            camera_end = camera_start + cue.duration_frames - 1
            target = indexed.get(cue.target_id) if cue.target_id else None
            if target:
                target_x, target_y = position_of(target)
                origin_x = min(1, max(0, (target_x + target.width * target.origin_x) / page.width))
                origin_y = min(1, max(0, (target_y + target.height * target.origin_y) / page.height))
                role_nodes["content"].transform_origin_x = origin_x
                role_nodes["content"].transform_origin_y = origin_y
                role_nodes["background"].transform_origin_x = origin_x
                role_nodes["background"].transform_origin_y = origin_y
            curve = [0.22, 1.0, 0.36, 1.0] if cue.easing_profile == "gentle" else [0.2, 0.8, 0.2, 1.0]

            def camera_track(
                group,
                prop,
                first,
                last,
                *,
                group_ids=role_group_ids,
                start_frame=camera_start,
                end_frame=camera_end,
                easing_curve=curve,
            ):
                if first == last:
                    return
                tracks.append(
                    MotionTrackV1(
                        track_id=group_ids[group] + "-camera-" + prop,
                        target_layer_id=group_ids[group],
                        property=prop,
                        unit=PROPERTY_UNITS[prop],
                        keyframes=[
                            {
                                "frame": start_frame,
                                "value": first,
                                "easing": "cubic_bezier",
                                "cubicBezier": easing_curve,
                            },
                            {"frame": end_frame, "value": last},
                        ],
                    )
                )

            background_parallax = max(
                (element.depth_treatment.parallax for element in scene.elements if element.visual_role == "background"),
                default=0,
            )
            if cue.mode in {"push_in", "focus_transition"}:
                for prop in ("scale_x", "scale_y"):
                    camera_track("content", prop, 1, 1 + cue.intensity)
                    camera_track("background", prop, 1, 1 + cue.intensity * background_parallax)
            elif cue.mode == "pull_out":
                for prop in ("scale_x", "scale_y"):
                    camera_track("content", prop, 1 + cue.intensity, 1)
                    camera_track("background", prop, 1 + cue.intensity * background_parallax, 1)
            if cue.mode in {"pan", "focus_transition"}:
                pan_x, pan_y = cue.pan_x, cue.pan_y
                if cue.mode == "focus_transition" and target:
                    target_x, target_y = position_of(target)
                    pan_x = (page.width / 2 - target_x - target.width * target.origin_x) * cue.intensity
                    pan_y = (page.height / 2 - target_y - target.height * target.origin_y) * cue.intensity
                camera_track("content", "position_x", 0, pan_x)
                camera_track("content", "position_y", 0, pan_y)
                camera_track("background", "position_x", 0, pan_x * background_parallax)
                camera_track("background", "position_y", 0, pan_y * background_parallax)
            operation(
                scene,
                "camera",
                role_group_ids["content"],
                "camera_" + cue.mode,
                camera_start,
                cue.duration_frames,
                cue.rationale,
            )

        def audio_start(audio, indexed=indexed, start_of=start_of):
            local_start = audio.start_frame
            if audio.sync_element_id:
                local_start += (
                    start_of(indexed[audio.sync_element_id]) + audio.sync_offset_frames - audio.attack_offset_frames
                )
            return local_start

        for audio in scene.audio:
            local_start = audio_start(audio)
            if local_start < 0 or local_start + audio.duration_frames > scene.duration_frames:
                raise ValueError("editing_v2_audio_out_of_scene")
            audio_id = target_id(scene.id, audio.id)
            if audio.role == "silence":
                silence_regions.append((cursor + local_start, cursor + local_start + audio.duration_frames))
                # Silence is absence, not a mute operation over other events.
                if any(
                    other.role != "silence"
                    and audio_start(other) < local_start + audio.duration_frames
                    and audio_start(other) + other.duration_frames > local_start
                    for other in scene.audio
                ):
                    raise ValueError("editing_v2_silence_overlaps_audio")
                if any(
                    c.timeline.start_frame < cursor + local_start + audio.duration_frames
                    and c.timeline.start_frame + c.timeline.duration_frames > cursor + local_start
                    for t in timeline.tracks
                    if t.kind == "audio" and not t.muted
                    for c in t.clips
                    if c.enabled
                ):
                    raise ValueError("editing_v2_silence_overlaps_audio")
            else:
                if not require(audio.asset_id, scene, audio.id, "audio", "audio/"):
                    continue
                clip = AudioClipV1(
                    id=audio_id,
                    asset_id=audio.asset_id,
                    timeline={"startFrame": cursor + local_start, "durationFrames": audio.duration_frames},
                    source={
                        "startMicroseconds": round(audio.source_start_seconds * 1e6),
                        "durationMicroseconds": round(audio.duration_frames / fps * 1e6),
                    },
                    label=audio.role,
                    gain_db=audio.gain_db,
                    fade_in_frames=audio.fade_in_frames,
                    fade_out_frames=audio.fade_out_frames,
                )
                timeline.tracks.append(AudioTrackV1(id="track-" + audio_id, name=audio.role, clips=[clip]))
                operation(
                    scene, audio.id, audio_id, "audio_mix", cursor + local_start, audio.duration_frames, audio.purpose
                )
            events.append(
                MotionAudioEventV1(
                    event_id="event-" + audio_id,
                    frame=cursor + local_start + audio.attack_offset_frames,
                    role={"narration": "dialogue", "ambience": "foley", "effect": "impact"}.get(audio.role, audio.role),
                    event_binding=audio.purpose,
                    audio_clip_id=audio_id if audio.role != "silence" else None,
                    asset_id=audio.asset_id if audio.role != "silence" else None,
                    rights_status="verified" if audio.role != "silence" else "not_applicable",
                )
            )
        cursor += scene.duration_frames
        previous_root, previous_duration = root_id, scene.duration_frames
        previous_elements = indexed
        previous_layer_ids = current_layer_ids
    if any(
        c.timeline.start_frame < right and c.timeline.start_frame + c.timeline.duration_frames > left
        for left, right in silence_regions
        for t in timeline.tracks
        if t.kind == "audio" and not t.muted
        for c in t.clips
        if c.enabled
    ):
        raise ValueError("editing_v2_silence_overlaps_audio")
    graph = MotionGraphV1(
        graph_id="motion-" + digest(plan_id)[:24],
        workspace_id=draft.workspace_id,
        document_id=draft.document_id,
        document_revision=draft.revision,
        frame_rate=direction.frame_rate,
        duration_frames=total,
        canvas_width=page.width,
        canvas_height=page.height,
        nodes=nodes,
        tracks=tracks,
        transitions=transitions,
        audio_events=events,
        created_by=user_id,
        created_at=datetime.now(UTC),
    )
    draft.composition.pages = [page]
    draft.composition.media_timeline = timeline
    draft.composition.narrative["editorialV2"] = {"planId": plan_id, "renderPolicy": "automatic_draft"}
    draft.composition.narrative["editorialV2"]["operationBindings"] = [
        {"sceneId": scene.id, **binding.model_dump(mode="json", by_alias=True)}
        for scene in direction.scenes for binding in scene.operation_bindings
    ]
    if any(scene.native_components for scene in direction.scenes):
        draft.composition.narrative["editorialV2"]["renderer"] = "remotion.contextual-v2"
        draft.composition.narrative["editorialV2"]["nativeComponentVersion"] = 1
    executable_direction = direction.model_dump(mode="json", by_alias=True)
    return (
        draft,
        graph,
        operations,
        {
            "schemaVersion": "studio.editorial-manifest.v2",
            "componentVersion": VERSION,
            "compilerVersion": COMPILER_VERSION,
            "componentLibraryVersion": COMPONENTS_VERSION,
            "runtimeVersion": RUNTIME_VERSION,
            "visualAuditPolicyVersion": VISUAL_AUDIT_POLICY_VERSION,
            "compositionDecisions": composition_decisions,
            "fps": fps,
            "durationFrames": total,
            "scenes": scene_manifest,
            "artDirection": (
                direction.art_direction.model_dump(mode="json", by_alias=True)
                if direction.art_direction
                else None
            ),
            "elements": manifest,
            "missingMaterials": missing,
            "sourceAssets": {a.id: a.checksum for a in document.assets},
            "executableDirection": executable_direction,
            "hashes": {
                "sourceDirection": digest(source_direction),
                "executableDirection": digest(executable_direction),
                "sourceDocument": digest(document),
                "executableComposition": executable_composition_digest(page, timeline, graph),
                "assets": digest({a.id: a.checksum for a in document.assets}),
                "fonts": digest(
                    {
                        a.id: a.checksum
                        for a in document.assets
                        if a.media_type.startswith("font/")
                        or a.media_type in {"application/font-sfnt", "application/vnd.ms-opentype"}
                    }
                ),
            },
            "humanReview": "pending",
        },
    )
