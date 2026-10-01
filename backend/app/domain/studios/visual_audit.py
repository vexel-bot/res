"""Versioned visual audit policy. Measurements never imply human approval."""

import re
from collections import Counter
from typing import Literal

from pydantic import Field, model_validator

from .composition_geometry import evaluate_scene_geometry
from .contracts import StudioContract


class VisualAuditPolicyV1(StudioContract):
    schema_version: Literal["studio.visual-audit-policy.v1"] = "studio.visual-audit-policy.v1"
    preview_width: int = 300
    text_contrast_minimum: float = 4.5
    essential_graphic_contrast_minimum: float = 3
    max_corrections_per_stage: int = 2
    minimum_human_score: int = 4
    max_simultaneous_salient_elements: int = 5
    minimum_hero_area_ratio: float = 0.025
    maximum_support_area_ratio: float = 0.55
    maximum_text_overlap_ratio: float = 0.1
    maximum_comparison_area_ratio: float = 6
    human_scale: dict[int, str] = {
        1: "incompreensível",
        2: "deficiente",
        3: "compreensível com problemas",
        4: "claro e coerente",
        5: "excelente",
    }
    limitations: list[str] = [
        "Contrast thresholds are internal readability heuristics, not a complete accessibility certification.",
        "No universal cut-count, movement ratio or maximum hold duration certifies quality.",
        "Model judgments and scene declarations do not constitute human review.",
    ]


class VisualAuditPolicyV2(VisualAuditPolicyV1):
    schema_version: Literal["studio.visual-audit-policy.v2"] = "studio.visual-audit-policy.v2"


class VisualReviewFindingV1(StudioContract):
    scene_id: str | None = Field(default=None, max_length=120)
    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(gt=0)
    cause: Literal["material", "cut", "framing", "continuity", "motion", "mask", "sound", "direction", "readability"]
    observation: str = Field(min_length=1, max_length=1000)
    correction: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def valid_interval(self):
        if self.end_seconds <= self.start_seconds:
            raise ValueError("visual_review_finding_interval_invalid")
        return self


class VisualHumanReviewV1(StudioContract):
    expected_document_revision: int = Field(ge=1)
    render_checksum: str = Field(pattern=r"^[a-f0-9]{64}$")
    clarity: int = Field(ge=1, le=5)
    rhythm: int = Field(ge=1, le=5)
    suitability: int = Field(ge=1, le=5)
    continuity: int = Field(ge=1, le=5)
    finish: int | None = Field(default=None, ge=1, le=5)
    hierarchy: int | None = Field(default=None, ge=1, le=5)
    motion_naturalness: int | None = Field(default=None, ge=1, le=5)
    material_relevance: int | None = Field(default=None, ge=1, le=5)
    notes: str = Field(min_length=1, max_length=4000)
    failure_cause: Literal["material", "cut", "framing", "motion", "mask", "sound", "direction", "none"] | None = None
    full_video_inspected: bool = False
    mobile_inspected: bool = False
    findings: list[VisualReviewFindingV1] = Field(default_factory=list, max_length=40)


class VisualControlClipV1(StudioContract):
    asset_id: str = Field(min_length=1, max_length=120)
    start_seconds: float = Field(ge=0, allow_inf_nan=False)
    duration_seconds: float = Field(gt=0, le=15, allow_inf_nan=False)


class VisualComparisonReviewV1(StudioContract):
    schema_version: Literal["studio.visual-comparison-review.v1"] = "studio.visual-comparison-review.v1"
    expected_document_revision: int = Field(ge=1)
    edit_a_run_id: str = Field(min_length=1, max_length=120)
    edit_b_run_id: str = Field(min_length=1, max_length=120)
    edit_a_checksum: str = Field(pattern=r"^[a-f0-9]{64}$")
    edit_b_checksum: str = Field(pattern=r"^[a-f0-9]{64}$")
    control_asset_id: str = Field(min_length=1, max_length=120)
    control_checksum: str = Field(pattern=r"^[a-f0-9]{64}$")
    control_edl: list[VisualControlClipV1] = Field(min_length=2, max_length=20)
    preferred: Literal["edit_a", "edit_b", "concat_control"]
    blind_review_completed: bool
    normal_speed_inspected: bool
    mobile_inspected: bool
    straight_concatenation_confirmed: bool
    same_materials_confirmed: bool
    unrecorded_manual_corrections: bool
    notes: str = Field(min_length=1, max_length=4000)

    @model_validator(mode="after")
    def valid_comparison(self):
        if self.edit_a_run_id == self.edit_b_run_id:
            raise ValueError("visual_comparison_distinct_runs_required")
        if abs(sum(clip.duration_seconds for clip in self.control_edl) - 15) > 0.05:
            raise ValueError("visual_comparison_control_duration_required")
        return self


def checkpoint_frames(scene):
    """States sample a single executable timeline, including completed reveals."""
    last = scene.duration_frames - 1
    declared = {state.phase: state.frame for state in scene.visual_states}
    if declared:
        fallback = {
            "start": 0,
            "demonstration": min(declared.get("action", 0), last),
            "consequence": min(declared.get("consequence", declared.get("action", 0)), last),
            "exit": min(declared.get("exit", last), last),
        }
        fallback["start"] = min(declared.get("initial", fallback["start"]), last)
        return fallback
    indexed = {element.id: element for element in scene.elements}
    starts = {}

    def start_of(element):
        if element.id not in starts:
            before = indexed.get(element.after_element_id)
            starts[element.id] = element.start_frame + (start_of(before) + before.duration_frames if before else 0)
        return starts[element.id]

    active = [
        min(
            last,
            start_of(e)
            + (e.repeat_count - 1) * e.stagger_frames
            + max(
                [a.keyframes[-1].frame for a in e.animations]
                + [c.start_frame + c.duration_frames - 1 for c in e.motion_cues]
                + ([e.reveal_frames] if e.reveal != "none" else [0])
            ),
        )
        for e in scene.elements
    ]
    end = max(active, default=0)
    return {"start": 0, "demonstration": end // 2, "consequence": end, "exit": last}


def contrast_ratio(a, b):
    def luminance(color):
        values = [int(color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
        linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in values]
        return sum(c * w for c, w in zip(linear, (0.2126, 0.7152, 0.0722), strict=True))

    x, y = luminance(a), luminance(b)
    return (max(x, y) + 0.05) / (min(x, y) + 0.05)


def preflight_visual(direction, graph=None, *, canvas_width=None, canvas_height=None):
    policy = VisualAuditPolicyV2()
    findings, states, cursor = [], [], 0
    peak_salient = 0
    fps = direction.frame_rate.numerator / direction.frame_rate.denominator
    for scene in direction.scenes:
        if scene.entrance != "cut":
            cursor -= scene.transition_frames
        states.append(
            {
                "sceneId": scene.id,
                "frames": {key: cursor + frame for key, frame in checkpoint_frames(scene).items()},
                "declaredStates": [state.model_dump(mode="json", by_alias=True) for state in scene.visual_states],
                "observationCues": [cue.model_dump(mode="json", by_alias=True) for cue in scene.observation_cues],
                "status": "awaiting_rendered_evidence",
            }
        )
        indexed = {element.id: element for element in scene.elements}
        starts = {}

        def start_of(element, *, starts=starts, indexed=indexed):
            if element.id not in starts:
                before = indexed.get(element.after_element_id)
                starts[element.id] = element.start_frame + (start_of(before) + before.duration_frames if before else 0)
            return starts[element.id]

        canvas_candidates = [
            element for element in scene.elements if element.visual_role == "background" and element.x == element.y == 0
        ]
        scene_canvas_width = canvas_width or max((element.width for element in canvas_candidates), default=1080)
        scene_canvas_height = canvas_height or max((element.height for element in canvas_candidates), default=1080)
        canvas_area = scene_canvas_width * scene_canvas_height
        geometry_cache = {}

        def geometry_at(
            local_frame,
            *,
            scene=scene,
            graph=graph,
            cursor=cursor,
            geometry_cache=geometry_cache,
            scene_canvas_width=scene_canvas_width,
            scene_canvas_height=scene_canvas_height,
        ):
            frame = max(0, min(scene.duration_frames - 1, local_frame))
            if frame not in geometry_cache:
                geometry_cache[frame] = evaluate_scene_geometry(
                    scene,
                    graph,
                    cursor,
                    frame,
                    scene_canvas_width,
                    scene_canvas_height,
                )
            return geometry_cache[frame]

        def bounds_of(element, local_frame=None, *, scene=scene, geometry_at=geometry_at):
            frame = checkpoint_frames(scene)["consequence"] if local_frame is None else local_frame
            items = [item for item in geometry_at(frame).get(element.id, []) if item.visible]
            if not items:
                return element.x, element.y, element.width, element.height
            left = min(item.x for item in items)
            top = min(item.y for item in items)
            right = max(item.x + item.width for item in items)
            bottom = max(item.y + item.height for item in items)
            return left, top, right - left, bottom - top

        boundaries = sorted(
            {
                frame
                for element in scene.elements
                if element.visual_role in {"hero", "support", "accent"}
                for frame in (start_of(element), start_of(element) + element.duration_frames - 1)
            }
        )
        scene_peak = 0
        for frame in boundaries:
            geometry = geometry_at(frame)
            scene_peak = max(
                scene_peak,
                sum(
                    element.visual_role in {"hero", "support", "accent"}
                    and element.kind != "group"
                    and any(item.visible and item.opacity >= 0.65 for item in geometry.get(element.id, []))
                    for element in scene.elements
                ),
            )
        peak_salient = max(peak_salient, scene_peak)
        if scene_peak > policy.max_simultaneous_salient_elements:
            findings.append(
                {
                    "sceneId": scene.id,
                    "elementId": scene.id,
                    "startSeconds": cursor / fps,
                    "endSeconds": (cursor + scene.duration_frames) / fps,
                    "code": "too_many_simultaneous_salient_elements",
                    "severity": "advisory",
                    "evidence": {
                        "peak": scene_peak,
                        "maximum": policy.max_simultaneous_salient_elements,
                    },
                    "confidence": 0.7,
                    "uncertainty": "Effective geometry and opacity; perceived dominance still requires pixel review.",
                    "correction": "Reduce, stagger or visually subordinate competing support and accent elements.",
                }
            )
        heroes = [element for element in scene.elements if element.visual_role == "hero"]
        if not heroes:
            findings.append(
                {
                    "sceneId": scene.id,
                    "elementId": scene.id,
                    "startSeconds": cursor / fps,
                    "endSeconds": (cursor + scene.duration_frames) / fps,
                    "code": "scene_has_no_primary_focus",
                    "severity": "correction",
                    "evidence": {"heroCount": 0},
                    "confidence": 1,
                    "uncertainty": (
                        "A rendered frame may create focus through contrast, "
                        "but the executable plan does not declare it."
                    ),
                    "correction": "Declare one principal element and subordinate the remaining layers.",
                }
            )
        for element in scene.elements:
            observed_bounds = [
                bounds_of(element, frame)
                for frame in set(checkpoint_frames(scene).values())
                if any(item.visible for item in geometry_at(frame).get(element.id, []))
            ]
            area_ratio = max(
                (
                    element_width * element_height / canvas_area
                    for _, _, element_width, element_height in observed_bounds
                ),
                default=element.width * element.height / canvas_area,
            )
            if element.visual_role == "hero" and area_ratio < policy.minimum_hero_area_ratio:
                findings.append(
                    {
                        "sceneId": scene.id,
                        "elementId": element.id,
                        "startSeconds": (cursor + start_of(element)) / fps,
                        "endSeconds": (cursor + start_of(element) + element.duration_frames) / fps,
                        "code": "hero_declared_too_small",
                        "severity": "correction",
                        "evidence": {"areaRatio": area_ratio, "minimum": policy.minimum_hero_area_ratio},
                        "confidence": 0.9,
                        "uncertainty": (
                            "Computed transform occupancy; media whitespace and masks still require pixel review."
                        ),
                        "correction": "Increase the hero's readable scale or target it with a verified camera move.",
                    }
                )
            if (
                element.visual_role in {"support", "accent"}
                and element.kind not in {"group", "path"}
                and area_ratio > policy.maximum_support_area_ratio
            ):
                findings.append(
                    {
                        "sceneId": scene.id,
                        "elementId": element.id,
                        "startSeconds": (cursor + start_of(element)) / fps,
                        "endSeconds": (cursor + start_of(element) + element.duration_frames) / fps,
                        "code": "support_element_competes_with_hero",
                        "severity": "advisory",
                        "evidence": {"areaRatio": area_ratio, "maximum": policy.maximum_support_area_ratio},
                        "confidence": 0.7,
                        "uncertainty": "Opacity and blur can reduce rendered dominance and require pixel review.",
                        "correction": "Reduce the support layer's occupied area or reclassify the intended focus.",
                    }
                )
        text_elements = [element for element in scene.elements if element.kind in {"text", "card"}]
        format_target_sets = [
            set(composition.target_ids)
            for composition in scene.compositions
            if composition.family == "format_transformation"
        ]

        def format_state_id(
            element,
            format_target_sets=format_target_sets,
            indexed=indexed,
        ):
            if (element.content_identity or "").startswith("format-label."):
                return element.content_identity.removeprefix("format-label.")
            current = element
            while current:
                if any(current.id in targets for targets in format_target_sets):
                    return current.id
                current = indexed.get(current.parent_id) if current.parent_id else None
            return element.id

        format_state_by_element = {element.id: format_state_id(element) for element in text_elements}
        for index, element in enumerate(text_elements):
            a_start, a_end = start_of(element), start_of(element) + element.duration_frames
            normalized = re.sub(r"[^\w]+", " ", element.text.casefold()).strip()
            for other in text_elements[index + 1 :]:
                b_start, b_end = start_of(other), start_of(other) + other.duration_frames
                if a_start >= b_end or b_start >= a_end:
                    continue
                temporal_overlap = min(a_end, b_end) - max(a_start, b_start)
                element_state = format_state_by_element[element.id]
                other_state = format_state_by_element[other.id]
                registered_handoff = (
                    temporal_overlap <= 1
                    and element_state != other_state
                    and any({element_state, other_state}.issubset(targets) for targets in format_target_sets)
                )
                registered_format_label = (
                    element.content_identity == f"format-label.{other.id}"
                    or other.content_identity == f"format-label.{element.id}"
                )
                if registered_handoff or registered_format_label:
                    continue
                overlap_frame = max(a_start, b_start) + (min(a_end, b_end) - max(a_start, b_start)) // 2
                ax, ay, aw, ah = bounds_of(element, overlap_frame)
                bx, by, bw, bh = bounds_of(other, overlap_frame)
                intersection = max(0, min(ax + aw, bx + bw) - max(ax, bx)) * max(0, min(ay + ah, by + bh) - max(ay, by))
                overlap_ratio = intersection / max(1, min(aw * ah, bw * bh))
                other_normalized = re.sub(r"[^\w]+", " ", other.text.casefold()).strip()
                code = None
                exact_duplicate = normalized == other_normalized
                contained_copy = (
                    normalized in other_normalized or other_normalized in normalized
                ) and overlap_ratio > 0.5
                if (
                    normalized
                    and other_normalized
                    and (exact_duplicate or contained_copy)
                    and not (element.text_spans or other.text_spans)
                ):
                    code = "duplicate_concurrent_text"
                elif overlap_ratio > policy.maximum_text_overlap_ratio:
                    code = "concurrent_text_collision"
                if code:
                    findings.append(
                        {
                            "sceneId": scene.id,
                            "elementId": element.id,
                            "startSeconds": (cursor + max(a_start, b_start)) / fps,
                            "endSeconds": (cursor + min(a_end, b_end)) / fps,
                            "code": code,
                            "severity": "correction",
                            "evidence": {
                                "otherElementId": other.id,
                                "overlapRatio": overlap_ratio,
                            },
                            "confidence": 0.95,
                            "uncertainty": "Declared boxes; glyph outlines and motion require rendered verification.",
                            "correction": "Keep one textual focus or separate the text layers in space or time.",
                        }
                    )
        for composition in scene.compositions:
            if composition.family == "format_transformation":
                expected_aspects = {
                    "portrait": 0.64,
                    "square": 1.0,
                    "landscape": 1.68,
                }
                transformation_evidence = []
                transformation_targets = [indexed[target_id] for target_id in composition.target_ids]
                media_targets = [target for target in transformation_targets if target.kind in {"image", "video"}]
                shared_asset = (
                    len(media_targets) == len(transformation_targets)
                    and len({target.asset_id for target in media_targets if target.asset_id}) == 1
                    and all(target.asset_id for target in media_targets)
                )
                shared_procedural_identity = bool(composition.continuity_key) and all(
                    target.content_identity == composition.continuity_key for target in transformation_targets
                )
                canonical_reference = next(
                    (
                        reference
                        for reference in direction.content_references
                        if reference.id == composition.continuity_key
                    ),
                    None,
                )
                required_parts = (
                    {part.id for part in canonical_reference.parts if part.required} if canonical_reference else set()
                )
                shared_canonical_content = bool(canonical_reference) and all(
                    target.kind == "group"
                    and target.content_reference_id == canonical_reference.id
                    and required_parts.issubset(
                        {
                            child.content_part_id
                            for child in scene.elements
                            if child.parent_id == target.id
                            and child.content_reference_id == canonical_reference.id
                            and child.content_part_id
                        }
                    )
                    for target in transformation_targets
                )
                if not (shared_asset or shared_procedural_identity or shared_canonical_content):
                    findings.append(
                        {
                            "sceneId": scene.id,
                            "elementId": composition.id,
                            "startSeconds": cursor / fps,
                            "endSeconds": (cursor + scene.duration_frames) / fps,
                            "code": "format_content_identity_lost",
                            "severity": "correction",
                            "evidence": {
                                "continuityKey": composition.continuity_key,
                                "assetIds": [target.asset_id for target in media_targets],
                                "contentIdentities": [target.content_identity for target in transformation_targets],
                            },
                            "confidence": 1,
                            "uncertainty": "Deterministic source and content-identity bindings.",
                            "correction": (
                                "Reuse one acquired source or bind every procedural state "
                                "to one explicit content identity."
                            ),
                        }
                    )
                for target_id, format_name in zip(
                    composition.target_ids,
                    composition.viewport_formats,
                    strict=True,
                ):
                    target = indexed[target_id]
                    actual_aspect = target.width / target.height
                    expected_aspect = expected_aspects[format_name]
                    transformation_evidence.append(
                        {
                            "targetId": target_id,
                            "format": format_name,
                            "aspectRatio": actual_aspect,
                            "contentIdentity": target.content_identity,
                            "contentReferenceId": target.content_reference_id,
                            "assetId": target.asset_id,
                        }
                    )
                    if abs(actual_aspect - expected_aspect) > 0.03:
                        findings.append(
                            {
                                "sceneId": scene.id,
                                "elementId": target_id,
                                "startSeconds": (cursor + start_of(target)) / fps,
                                "endSeconds": (cursor + start_of(target) + target.duration_frames) / fps,
                                "code": "format_viewport_ratio_mismatch",
                                "severity": "correction",
                                "evidence": {
                                    "format": format_name,
                                    "actualAspectRatio": actual_aspect,
                                    "expectedAspectRatio": expected_aspect,
                                },
                                "confidence": 1,
                                "uncertainty": "Deterministic viewport geometry.",
                                "correction": (
                                    "Recompute both viewport dimensions while preserving the requested aspect ratio."
                                ),
                            }
                        )
                states[-1].setdefault("formatTransformations", []).append(
                    {
                        "compositionId": composition.id,
                        "continuityKey": composition.continuity_key,
                        "states": transformation_evidence,
                    }
                )
                continue
            if composition.family != "comparison":
                continue
            comparison_frame = checkpoint_frames(scene)["consequence"]
            target_areas = [
                bounds_of(indexed[target_id], comparison_frame)[2] * bounds_of(indexed[target_id], comparison_frame)[3]
                for target_id in composition.target_ids
                if target_id in indexed
            ]
            if len(target_areas) == 2 and min(target_areas) > 0:
                area_ratio = max(target_areas) / min(target_areas)
                if area_ratio > policy.maximum_comparison_area_ratio:
                    findings.append(
                        {
                            "sceneId": scene.id,
                            "elementId": composition.id,
                            "startSeconds": cursor / fps,
                            "endSeconds": (cursor + scene.duration_frames) / fps,
                            "code": "comparison_targets_have_incompatible_visual_scale",
                            "severity": "correction",
                            "evidence": {
                                "areaRatio": area_ratio,
                                "maximum": policy.maximum_comparison_area_ratio,
                                "targetIds": composition.target_ids,
                            },
                            "confidence": 0.9,
                            "uncertainty": (
                                "Rendered content may contain internal whitespace that changes perceived scale."
                            ),
                            "correction": (
                                "Use comparable representations, or express the relationship "
                                "with evidence, paths or sequence."
                            ),
                        }
                    )
        # Only diagnose simple unobscured graphics against a known solid scene.
        # Footage, masks and overlaps require pixel/region analysis at render time.
        for element in scene.elements:
            if (
                element.parent_id
                or element.alignment
                or element.after_element_id
                or element.animations
                or element.rotation
                or element.repeat_count > 1
                or element.kind not in {"text", "path"}
            ):
                continue
            overlaps = any(
                other.id != element.id
                and other.kind != "group"
                and other.start_frame < element.start_frame + element.duration_frames
                and other.start_frame + other.duration_frames > element.start_frame
                and other.x < element.x + element.width
                and other.x + other.width > element.x
                and other.y < element.y + element.height
                and other.y + other.height > element.y
                for other in scene.elements
            )
            if overlaps:
                continue
            ratio = contrast_ratio(element.color, scene.background)
            minimum = (
                policy.text_contrast_minimum if element.kind == "text" else policy.essential_graphic_contrast_minimum
            )
            if ratio < minimum:
                findings.append(
                    {
                        "sceneId": scene.id,
                        "elementId": element.id,
                        "startSeconds": (cursor + element.start_frame) / fps,
                        "endSeconds": (cursor + element.start_frame + element.duration_frames) / fps,
                        "code": "declared_contrast_below_reference",
                        "severity": "correction",
                        "evidence": {
                            "ratio": ratio,
                            "minimum": minimum,
                            "foreground": element.color,
                            "background": scene.background,
                        },
                        "confidence": 1,
                        "uncertainty": "Declared static colors; rendered appearance still requires inspection.",
                        "correction": "Choose a readable foreground/background pair consistent with the identity.",
                    }
                )
        cursor += scene.duration_frames
    property_counts = Counter()
    easing_counts = Counter()
    camera_tracks = []
    linear_camera_tracks = []
    overshoot_tracks = []
    if graph is not None:
        for track in graph.tracks:
            property_counts[track.property] += 1
            easing_counts.update(keyframe.easing for keyframe in track.keyframes[:-1])
            if "-camera-" in track.track_id:
                camera_tracks.append(track.track_id)
                if any(keyframe.easing == "linear" for keyframe in track.keyframes[:-1]):
                    linear_camera_tracks.append(track.track_id)
            values = [keyframe.value for keyframe in track.keyframes]
            if track.property in {"scale_x", "scale_y"} and min(values) < 1 < max(values) and values[-1] == 1:
                overshoot_tracks.append(track.track_id)
        for track_id in linear_camera_tracks:
            findings.append(
                {
                    "sceneId": "motion-graph",
                    "elementId": track_id,
                    "startSeconds": 0,
                    "endSeconds": 0,
                    "code": "linear_camera_motion_requires_rationale",
                    "severity": "correction",
                    "evidence": {"trackId": track_id},
                    "confidence": 1,
                    "uncertainty": "Static graph inspection; rendered velocity still requires pixel verification.",
                    "correction": "Use a registered nonlinear camera profile or declare a deliberate linear move.",
                }
            )
    for finding in findings:
        finding.setdefault("category", "motion" if finding["sceneId"] == "motion-graph" else "visual_editorial")
        finding.setdefault("impact", "clarity_and_execution")
    return {
        "schemaVersion": "studio.visual-audit.v2",
        "policy": policy.model_dump(mode="json", by_alias=True),
        "technical": "pending",
        "visualEditorial": "requires_correction" if findings else "unreviewed",
        "human": "pending",
        "findings": findings,
        "states": states,
        "renderedEvidence": [],
        "motion": {
            "componentVersion": (
                direction.execution_versions.components if direction.execution_versions else "unversioned-legacy-plan"
            ),
            "propertyCounts": dict(property_counts),
            "easingCounts": dict(easing_counts),
            "cameraTrackIds": camera_tracks,
            "linearCameraTrackIds": linear_camera_tracks,
            "overshootTrackIds": overshoot_tracks,
            "motionCueCount": sum(len(element.motion_cues) for scene in direction.scenes for element in scene.elements),
            "deliberateHoldCount": sum(
                cue.kind == "deliberate_hold"
                for scene in direction.scenes
                for element in scene.elements
                for cue in element.motion_cues
            ),
            "keywordCueCount": sum(len(scene.keyword_cues) for scene in direction.scenes),
            "peakSimultaneousSalientElements": peak_salient,
        },
    }
