"""Compile measured, per-beat narration without guessing word boundaries."""

import math

from .contextual_editing_v2 import EditorialAudioV2


def bind_narration(candidate, measurements):
    fps = candidate.frame_rate.numerator / candidate.frame_rate.denominator
    for scene in candidate.scenes:
        measurement = measurements.get(scene.id)
        if not measurement and scene.narration.strip():
            raise ValueError("production_scene_narration_required")
        if not measurement:
            continue
        frames = math.ceil(measurement["durationSeconds"] * fps)
        if scene.duration_frames < frames:
            raise ValueError("production_scene_shorter_than_narration")
        # Synthesized beat recordings start at zero; no inferred intra-sentence edit.
        scene.audio = [a for a in scene.audio if a.role != "narration"]
        scene.audio.append(
            EditorialAudioV2(
                id="production-narration",
                role="narration",
                purpose="Preservar a fala integral desta cena",
                asset_id=measurement["assetId"],
                duration_frames=frames,
            )
        )
    return type(candidate).model_validate(candidate.model_dump())


def normalize_visual_duration(candidate, target_seconds):
    """Normalize the timeline while preserving relative timing relationships.

    Short plans are expanded. A visual-only plan may also be contracted by at
    most 15 percent to honor the explicit requested duration. Plans with audio
    or larger overruns still require a new editorial decision because shrinking
    could remove comprehension or speech time.
    """
    fps = candidate.frame_rate.numerator / candidate.frame_rate.denominator
    current_frames = sum(
        scene.duration_frames - (scene.transition_frames if scene.entrance != "cut" else 0)
        for scene in candidate.scenes
    )
    target_frames = round(target_seconds * fps)
    if current_frames == target_frames:
        return candidate, []
    factor = target_frames / current_frames
    contracting = current_frames > target_frames
    repeated_project_duration = (
        len(candidate.scenes) > 1
        and all(scene.entrance == "cut" for scene in candidate.scenes)
        and all(scene.duration_frames == target_frames for scene in candidate.scenes)
        and current_frames == target_frames * len(candidate.scenes)
    )
    if contracting and (
        (factor < 0.85 and not repeated_project_duration)
        or candidate.execution_scope != "visual_only"
        or any(scene.audio for scene in candidate.scenes)
    ):
        raise ValueError("production_composition_duration_exceeds_target")
    result = candidate.model_copy(deep=True)

    def scaled(value, *, minimum=0, maximum=108000):
        return min(maximum, max(minimum, round(value * factor)))

    for scene in result.scenes:
        scene.duration_frames = scaled(scene.duration_frames, minimum=2)
        scene.transition_frames = scaled(scene.transition_frames, minimum=1, maximum=120)
        for shot in scene.shot_plan:
            if shot.start_frame is not None:
                shot.start_frame = scaled(shot.start_frame)
            if shot.end_frame_exclusive is not None:
                shot.end_frame_exclusive = scaled(shot.end_frame_exclusive)
        for element in scene.elements:
            element.start_frame = scaled(element.start_frame)
            element.duration_frames = scaled(element.duration_frames, minimum=1)
            element.reveal_frames = min(
                element.duration_frames, scaled(element.reveal_frames, minimum=1)
            )
            element.stagger_frames = scaled(element.stagger_frames)
            for animation in element.animations:
                for keyframe in animation.keyframes:
                    keyframe.frame = min(
                        element.duration_frames - 1,
                        scaled(keyframe.frame),
                    )
            for span in element.text_spans:
                start_frame = (
                    span.get("startFrame") if isinstance(span, dict) else span.start_frame
                )
                if start_frame is None:
                    continue
                revised_start = min(
                    element.duration_frames - 1,
                    scaled(start_frame),
                )
                duration_frames = (
                    span.get("durationFrames") if isinstance(span, dict) else span.duration_frames
                )
                revised_duration = min(
                    element.duration_frames - revised_start,
                    scaled(duration_frames, minimum=1, maximum=3600),
                )
                if isinstance(span, dict):
                    span["startFrame"] = revised_start
                    span["durationFrames"] = revised_duration
                else:
                    span.start_frame = revised_start
                    span.duration_frames = revised_duration
            for cue in element.motion_cues:
                cue.start_frame = scaled(cue.start_frame)
                cue.duration_frames = scaled(cue.duration_frames, minimum=1, maximum=3600)
        for audio in scene.audio:
            audio.start_frame = scaled(audio.start_frame)
            audio.duration_frames = scaled(audio.duration_frames, minimum=1)
            audio.sync_offset_frames = round(audio.sync_offset_frames * factor)
            audio.attack_offset_frames = min(
                audio.duration_frames - 1,
                scaled(audio.attack_offset_frames),
            )
            audio.fade_in_frames = min(audio.duration_frames, scaled(audio.fade_in_frames))
            audio.fade_out_frames = min(
                audio.duration_frames - audio.fade_in_frames,
                scaled(audio.fade_out_frames),
            )
        for composition in scene.compositions:
            composition.action_frames = scaled(composition.action_frames, minimum=1, maximum=3600)
            count = (
                len(composition.target_ids)
                if composition.family == "sequence"
                else composition.repeat_count
                if composition.family == "repetition"
                else 1
            )
            if composition.family in {"sequence", "repetition"}:
                composition.action_frames = min(
                    composition.action_frames,
                    max(1, (scene.duration_frames - 1) // count),
                )
        for cue in scene.camera_cues:
            cue.start_frame = scaled(cue.start_frame)
            cue.duration_frames = scaled(cue.duration_frames, minimum=2, maximum=3600)
        for cue in scene.keyword_cues:
            cue.start_frame = scaled(cue.start_frame)
            cue.duration_frames = scaled(cue.duration_frames, minimum=12, maximum=3600)
        for state in scene.visual_states:
            state.frame = min(scene.duration_frames - 1, scaled(state.frame))
        for cue in scene.observation_cues:
            cue.start_frame = min(scene.duration_frames - 1, scaled(cue.start_frame))
            cue.end_frame_exclusive = min(
                scene.duration_frames,
                max(cue.start_frame + 1, scaled(cue.end_frame_exclusive, minimum=1)),
            )
        indexed_elements = {element.id: element for element in scene.elements}
        for shot in scene.shot_plan:
            if shot.start_frame is None or shot.end_frame_exclusive is None:
                continue
            expected = max(1, shot.end_frame_exclusive - shot.start_frame)
            for target_id in shot.target_element_ids:
                target = indexed_elements.get(target_id)
                if target and target.start_frame == shot.start_frame:
                    target.duration_frames = expected

    actual_frames = sum(
        scene.duration_frames - (scene.transition_frames if scene.entrance != "cut" else 0)
        for scene in result.scenes
    )
    delta = target_frames - actual_frames
    last_scene = result.scenes[-1]
    last_scene.duration_frames += delta
    if last_scene.shot_plan:
        last_scene.shot_plan[-1].end_frame_exclusive = last_scene.duration_frames
        indexed_last = {element.id: element for element in last_scene.elements}
        final_shot = last_scene.shot_plan[-1]
        if final_shot.start_frame is not None:
            for target_id in final_shot.target_element_ids:
                target = indexed_last.get(target_id)
                if target and target.start_frame == final_shot.start_frame:
                    target.duration_frames = max(
                        1, final_shot.end_frame_exclusive - final_shot.start_frame
                    )
    indexed = {element.id: element for element in last_scene.elements}
    starts = {}

    def absolute_start(element):
        if element.id not in starts:
            prior = indexed.get(element.after_element_id)
            starts[element.id] = element.start_frame + (
                absolute_start(prior) + prior.duration_frames if prior else 0
            )
        return starts[element.id]

    for element in last_scene.elements:
        available = (
            last_scene.duration_frames
            - absolute_start(element)
            - (element.repeat_count - 1) * element.stagger_frames
        )
        element.duration_frames = min(element.duration_frames, available)
        element.reveal_frames = min(element.reveal_frames, element.duration_frames)
        for animation in element.animations:
            for keyframe in animation.keyframes:
                keyframe.frame = min(keyframe.frame, element.duration_frames - 1)
        for span in element.text_spans:
            start_frame = span.get("startFrame") if isinstance(span, dict) else span.start_frame
            if start_frame is None:
                continue
            revised_start = min(start_frame, element.duration_frames - 1)
            duration_frames = (
                span.get("durationFrames") if isinstance(span, dict) else span.duration_frames
            )
            revised_duration = min(
                duration_frames,
                element.duration_frames - revised_start,
            )
            if isinstance(span, dict):
                span["startFrame"] = revised_start
                span["durationFrames"] = revised_duration
            else:
                span.start_frame = revised_start
                span.duration_frames = revised_duration
        for cue in element.motion_cues:
            cue.duration_frames = min(
                cue.duration_frames,
                element.duration_frames - cue.start_frame,
            )
    for cue in last_scene.camera_cues:
        cue.duration_frames = min(cue.duration_frames, last_scene.duration_frames - cue.start_frame)
    for cue in last_scene.keyword_cues:
        cue.duration_frames = min(cue.duration_frames, last_scene.duration_frames - cue.start_frame)
    for state in last_scene.visual_states:
        state.frame = min(state.frame, last_scene.duration_frames - 1)
    for cue in last_scene.observation_cues:
        cue.start_frame = min(cue.start_frame, last_scene.duration_frames - 1)
        cue.end_frame_exclusive = min(
            last_scene.duration_frames,
            max(cue.start_frame + 1, cue.end_frame_exclusive),
        )
    normalized = type(candidate).model_validate(result.model_dump())
    return normalized, [
        {
            "reason": (
                "per_scene_project_duration_normalized"
                if repeated_project_duration
                else "visual_only_composition_bounded_to_requested_duration"
                if contracting
                else "composition_shorter_than_requested_duration"
            ),
            "beforeFrames": current_frames,
            "afterFrames": target_frames,
            "factor": factor,
        }
    ]


def bind_declared_material_durations(candidate):
    """Keep finite source clips at the duration explicitly requested for them."""
    fps = candidate.frame_rate.numerator / candidate.frame_rate.denominator
    repairs = []
    for scene in candidate.scenes:
        indexed = {element.id: element for element in scene.elements}
        shot_targets = {
            target_id
            for shot in scene.shot_plan
            for target_id in shot.target_element_ids
        }
        for need in scene.material_needs:
            if need.field != "asset" or need.kind != "video" or need.duration_seconds is None:
                continue
            target = indexed.get(need.target_id)
            if target is None or target.kind != "video":
                continue
            desired = min(round(need.duration_seconds * fps), scene.duration_frames - target.start_frame)
            if desired < 1 or target.duration_frames == desired:
                continue
            if target.id in shot_targets and desired < target.duration_frames:
                repairs.append(
                    {
                        "sceneId": scene.id,
                        "elementId": target.id,
                        "reason": "material_tail_hold_for_shot",
                        "sourceDurationFrames": desired,
                        "timelineDurationFrames": target.duration_frames,
                    }
                )
                continue
            before = target.duration_frames
            target.duration_frames = desired
            target.reveal_frames = min(target.reveal_frames, desired)
            for animation in target.animations:
                for keyframe in animation.keyframes:
                    keyframe.frame = min(keyframe.frame, desired - 1)
            target.motion_cues = [
                cue for cue in target.motion_cues if cue.start_frame + cue.duration_frames <= desired
            ]
            repairs.append(
                {
                    "sceneId": scene.id,
                    "elementId": target.id,
                    "needId": need.id,
                    "reason": "video_element_bound_to_declared_source_duration",
                    "before": {"durationFrames": before},
                    "after": {"durationFrames": desired},
                }
            )
    return candidate, repairs


def preserve_unselected_scenes(original, candidate, selected):
    """Project a model's localized proposal onto the unchanged source scenes."""
    if [s.id for s in candidate.scenes] != [s.id for s in original.scenes]:
        raise ValueError("production_revision_scene_binding_conflict")
    if not set(selected) <= {s.id for s in original.scenes}:
        raise ValueError("production_revision_scene_binding_conflict")
    selected_ids = set(selected)
    for index, source in enumerate(original.scenes):
        if source.id not in selected_ids:
            candidate.scenes[index] = source.model_copy(deep=True)
    return candidate


def merge_partial_local_revision(original, candidate, selected):
    """Expand a selected-scene response into the immutable original plan.

    A localized director request may return only the requested scenes.  Accept
    that compact contract when it names every selected scene exactly once, and
    preserve all plan-level fields plus every unselected scene from the bound
    original.  Any other scene set remains a binding conflict.
    """

    original_ids = [scene.id for scene in original.scenes]
    candidate_ids = [scene.id for scene in candidate.scenes]
    selected_ids = list(dict.fromkeys(selected))
    if not selected_ids or not set(selected_ids) <= set(original_ids):
        raise ValueError("production_revision_scene_binding_conflict")
    if candidate_ids == original_ids:
        return candidate, []
    if (
        len(candidate_ids) != len(selected_ids)
        or len(set(candidate_ids)) != len(candidate_ids)
        or set(candidate_ids) != set(selected_ids)
    ):
        raise ValueError("production_revision_scene_binding_conflict")
    proposals = {scene.id: scene for scene in candidate.scenes}
    merged = original.model_copy(deep=True)
    merged.scenes = [
        proposals[scene.id].model_copy(deep=True)
        if scene.id in proposals
        else scene.model_copy(deep=True)
        for scene in original.scenes
    ]
    return merged, [
        {
            "reason": "partial_local_revision_merged_with_bound_plan",
            "selectedSceneIds": selected_ids,
            "preservedSceneIds": [scene_id for scene_id in original_ids if scene_id not in proposals],
            "classification": "bounded_normalization",
            "requiresAlternative": False,
        }
    ]


def validate_local_revision(original, candidate, selected):
    if (
        candidate.frame_rate != original.frame_rate
        or candidate.execution_scope != original.execution_scope
        or [s.id for s in candidate.scenes] != [s.id for s in original.scenes]
        or not set(selected) <= {s.id for s in original.scenes}
    ):
        raise ValueError("production_revision_scene_binding_conflict")
    for before, after in zip(original.scenes, candidate.scenes, strict=True):
        if before.id not in selected and before != after:
            raise ValueError("production_revision_changed_unselected_scene")
        if before.facts != after.facts or before.narration != after.narration:
            raise ValueError("production_revision_changed_preserved_information")
        # Length changes shift downstream events. Until explicit dependency remapping
        # is available, calmness must be achieved within the selected scene interval.
        if (before.duration_frames, before.entrance, before.transition_frames) != (
            after.duration_frames,
            after.entrance,
            after.transition_frames,
        ):
            raise ValueError("production_revision_temporal_dependency_required")
    return candidate
