"""Bounded checkpoints decoded from the final export, never from the plan alone."""

import base64
import hashlib
import io
import json
import struct
import subprocess
import tempfile
from fractions import Fraction
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

from ...domain.studios.visual_audit import preflight_visual
from ...services.object_storage import sha256_file


def observe_visual_states(
    path,
    direction,
    graph=None,
    *,
    renderer_checks=None,
    expected_direction_digest=None,
    expected_composition_digest=None,
    legacy_preparation=False,
    max_frames=32,
    max_bytes=3_000_000,
):
    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=avg_frame_rate,width,height",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        check=True,
        timeout=30,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    try:
        encoded_rate = Fraction(json.loads(probe.stdout)["streams"][0]["avg_frame_rate"])
    except (IndexError, KeyError, TypeError, ZeroDivisionError) as error:
        raise ValueError("visual_audit_frame_rate_unknown") from error
    timeline_rate = Fraction(direction.frame_rate.numerator, direction.frame_rate.denominator)
    if encoded_rate <= 0:
        raise ValueError("visual_audit_frame_rate_unknown")
    from ...domain.studios.contextual_editing import digest

    observed_direction_digest = digest(direction.model_dump(mode="json", by_alias=True))
    if legacy_preparation and any(scene.compositions or scene.keyword_cues for scene in direction.scenes):
        from ...services.studios.scene_compiler import prepare_direction

        dimensions = json.loads(probe.stdout)["streams"][0]
        direction = prepare_direction(direction, dimensions["width"], dimensions["height"])
        observed_direction_digest = digest(direction.model_dump(mode="json", by_alias=True))
    if expected_direction_digest and observed_direction_digest != expected_direction_digest:
        raise ValueError("visual_audit_executable_direction_conflict")
    audit = preflight_visual(
        direction,
        graph,
        canvas_width=json.loads(probe.stdout)["streams"][0]["width"],
        canvas_height=json.loads(probe.stdout)["streams"][0]["height"],
    )
    renderer_geometry_frames = sorted(
        {
            int(sample["frame"])
            for sample in (renderer_checks or {}).get("geometrySamples", [])
            if sample.get("frame") is not None
        }
    )

    def state_probe_frame(scene_cursor, active_start, active_end):
        midpoint = scene_cursor + active_start + round((active_end - active_start) * 0.5)
        candidates = [
            frame
            for frame in renderer_geometry_frames
            if scene_cursor + active_start <= frame <= scene_cursor + active_end
        ]
        return min(candidates, key=lambda frame: abs(frame - midpoint)) if candidates else midpoint

    action_frames = set()
    cursor = 0
    for scene in direction.scenes:
        if scene.entrance != "cut":
            cursor -= scene.transition_frames
        indexed_elements = {element.id: element for element in scene.elements}
        for element in scene.elements:
            for cue in element.motion_cues:
                start = cursor + element.start_frame + cue.start_frame
                end = start + cue.duration_frames - 1
                action_frames.update(
                    {
                        start,
                        start + round((end - start) * 0.58),
                        end,
                    }
                )
        for cue in scene.camera_cues:
            start = cursor + cue.start_frame
            end = start + cue.duration_frames - 1
            action_frames.update({start, (start + end) // 2, end})
        for cue in scene.observation_cues:
            interval = cue.end_frame_exclusive - cue.start_frame
            samples = max(2, round(interval / float(timeline_rate) * cue.minimum_samples_per_second))
            action_frames.update(
                cursor + cue.start_frame + round(index * (interval - 1) / max(1, samples - 1))
                for index in range(samples)
            )
        for assertion in scene.semantic_assertions:
            interval = assertion.end_frame_exclusive - assertion.start_frame
            sample_count = max(3, len(assertion.target_ids))
            action_frames.update(
                cursor
                + assertion.start_frame
                + round(index * (interval - 1) / max(1, sample_count - 1))
                for index in range(sample_count)
            )
            # Sample inside each target's actual active range as well. A global
            # start/middle/end triplet can miss a valid first state whose exit
            # precedes the assertion midpoint (and can sample its opacity-zero
            # entrance frame). These probes establish observed state coverage;
            # they do not, by themselves, certify the semantic action.
            for target_id in assertion.target_ids:
                target = indexed_elements.get(target_id)
                if not target:
                    continue
                active_start = max(assertion.start_frame, target.start_frame)
                active_end = min(
                    assertion.end_frame_exclusive,
                    target.start_frame + target.duration_frames,
                ) - 1
                if active_end >= active_start:
                    action_frames.add(state_probe_frame(cursor, active_start, active_end))
        cursor += scene.duration_frames
    state_frames = sorted({frame for state in audit["states"] for frame in state["frames"].values()})
    action_only_frames = [frame for frame in sorted(action_frames) if frame not in state_frames]
    requested = [*state_frames, *action_only_frames]
    evidence, consumed = {}, 0

    def evenly_bounded(frames, count):
        if count <= 0 or not frames:
            return []
        if len(frames) <= count:
            return list(frames)
        if count == 1:
            return [frames[0]]
        return list(
            dict.fromkeys(
                frames[round(index * (len(frames) - 1) / (count - 1))]
                for index in range(count)
            )
        )

    # Preserve coverage across the entire piece. Taking the first N frames hid
    # late scenes and could falsely report their actions as unobserved.
    state_budget = min(
        len(state_frames),
        max(1, round(max_frames * 0.75)) if action_only_frames else max_frames,
    )
    selected = evenly_bounded(state_frames, state_budget)
    selected.extend(
        evenly_bounded(
            [frame for frame in action_only_frames if frame not in selected],
            max_frames - len(selected),
        )
    )
    selected = sorted(set(selected))
    encoded_frames = {frame: round(frame * encoded_rate / timeline_rate) for frame in selected}
    decoded = {}
    raw_images = {}
    with tempfile.TemporaryDirectory(prefix="res-visual-states-") as temp:
        directory = Path(temp)
        unique_frames = sorted(set(encoded_frames.values()))
        expression = "+".join(f"eq(n\\,{frame})" for frame in unique_frames)
        if selected:
            subprocess.run(
                [
                    "ffmpeg",
                    "-v",
                    "error",
                    "-threads",
                    "1",
                    "-filter_threads",
                    "1",
                    "-i",
                    str(path),
                    "-an",
                    "-vf",
                    f"select={expression},scale=300:-2",
                    "-fps_mode",
                    "passthrough",
                    "-frames:v",
                    str(len(selected)),
                    "-c:v",
                    "mjpeg",
                    "-q:v",
                    "4",
                    str(directory / "frame-%04d.jpg"),
                ],
                capture_output=True,
                check=True,
                timeout=90,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        for frame, image_path in zip(unique_frames, sorted(directory.glob("frame-*.jpg")), strict=False):
            data = image_path.read_bytes()
            if consumed + len(data) > max_bytes:
                break
            consumed += len(data)
            decoded[frame] = {
                "encodedFrame": frame,
                "timestampSeconds": float(frame / encoded_rate),
                "checksumSha256": hashlib.sha256(data).hexdigest(),
                "previewWidth": 300,
                "image": "data:image/jpeg;base64," + base64.b64encode(data).decode("ascii"),
                "origin": "decoded_export_frame",
            }
            raw_images[frame] = data
    evidence = {
        frame: {"frame": frame, **decoded[encoded_frame]}
        for frame, encoded_frame in encoded_frames.items()
        if encoded_frame in decoded
    }
    region_motion = []
    roi_evidence = []
    rendered_findings = []
    action_evidence = []
    cursor = 0
    preview_width = 300
    original_width = json.loads(probe.stdout)["streams"][0]["width"]
    original_height = json.loads(probe.stdout)["streams"][0]["height"]
    preview_height = round(original_height * preview_width / original_width)
    geometry_samples = {
        int(sample["frame"]): sample.get("elements", [])
        for sample in (renderer_checks or {}).get("geometrySamples", [])
    }

    def geometry_for(element, frame):
        matches = [
            item
            for item in geometry_samples.get(frame, [])
            if item.get("semanticId") == element.id and item.get("present")
        ]
        if not matches:
            return None
        visible = [item for item in matches if item.get("visible")]
        candidates = visible or matches
        boxes = [item["bounds"] for item in candidates if item.get("bounds")]
        if not boxes:
            return None
        left = min(box["x"] for box in boxes)
        top = min(box["y"] for box in boxes)
        right = max(box["x"] + box["width"] for box in boxes)
        bottom = max(box["y"] + box["height"] for box in boxes)
        return {
            "x": left,
            "y": top,
            "width": right - left,
            "height": bottom - top,
            "visible": bool(visible),
            "opacity": max((item.get("opacity", 0) for item in candidates), default=0),
            "origin": "renderer_dom_geometry",
        }

    def crop_for(element, frame):
        encoded_frame = encoded_frames.get(frame)
        data = raw_images.get(encoded_frame)
        if not data:
            return None
        image = Image.open(io.BytesIO(data)).convert("RGB")
        geometry = geometry_for(element, frame)
        bounds = geometry or {
            "x": element.x,
            "y": element.y,
            "width": element.width,
            "height": element.height,
        }
        left = max(0, round(bounds["x"] * preview_width / original_width))
        top = max(0, round(bounds["y"] * preview_height / original_height))
        right = min(preview_width, round((bounds["x"] + bounds["width"]) * preview_width / original_width))
        bottom = min(preview_height, round((bounds["y"] + bounds["height"]) * preview_height / original_height))
        return image.crop((left, top, right, bottom)) if right > left and bottom > top else None

    def difference(first, second):
        if first is None or second is None:
            return None
        if first.size != second.size:
            first = first.resize((64, 64))
            second = second.resize((64, 64))
        return round(sum(ImageStat.Stat(ImageChops.difference(first, second)).mean) / (3 * 255), 6)

    def visual_signal(element, frame):
        """Measure whether a declared visible part has actual discriminative pixels.

        This deliberately does not try to infer meaning. It prevents geometry-only
        evidence (including a solid-colour placeholder) from being promoted to a
        semantic proof while preserving that judgment for the human/VLM gate.
        """
        crop = crop_for(element, frame)
        if crop is None or crop.width < 2 or crop.height < 2:
            return {
                "status": "inconclusive",
                "frame": frame,
                "lumaStdDev": None,
                "signature": None,
            }
        grayscale = crop.convert("L")
        deviation = float(ImageStat.Stat(grayscale).stddev[0])
        thumbnail = grayscale.resize((16, 16))
        pixels = list(thumbnail.getdata())
        mean = sum(pixels) / max(1, len(pixels))
        bits = "".join("1" if value >= mean else "0" for value in pixels)
        content_bits = None
        if element.kind in {"image", "video"} and element.object_fit == "contain":
            # A contained image may occupy different fractions of its layout
            # box in portrait and square states. The outer letterbox must not
            # be mistaken for a change of the source image. Remove only a
            # near-uniform border before comparing the rendered pixels.
            corner = crop.getpixel((0, 0))
            border_difference = ImageChops.difference(
                crop, Image.new("RGB", crop.size, corner)
            ).convert("L")
            visible_box = border_difference.point(lambda value: 255 if value > 14 else 0).getbbox()
            if visible_box:
                visible = crop.crop(visible_box)
                if visible.width * visible.height >= crop.width * crop.height * 0.1:
                    content_pixels = list(visible.convert("L").resize((16, 16)).getdata())
                    content_mean = sum(content_pixels) / len(content_pixels)
                    content_bits = "".join(
                        "1" if value >= content_mean else "0" for value in content_pixels
                    )
        return {
            "status": "observed" if deviation >= 2 else "flat_placeholder",
            "frame": frame,
            "lumaStdDev": round(deviation, 3),
            "signature": bits,
            "contentSignature": content_bits,
        }

    def signature_similarity(first, second):
        if not first or not second or len(first) != len(second):
            return None
        return round(sum(left == right for left, right in zip(first, second, strict=True)) / len(first), 6)

    def geometry_delta(first, second):
        if not first or not second:
            return None
        diagonal = max(1, (original_width**2 + original_height**2) ** 0.5)
        center_a = (first["x"] + first["width"] / 2, first["y"] + first["height"] / 2)
        center_b = (second["x"] + second["width"] / 2, second["y"] + second["height"] / 2)
        travel = ((center_b[0] - center_a[0]) ** 2 + (center_b[1] - center_a[1]) ** 2) ** 0.5 / diagonal
        area_a = max(1, first["width"] * first["height"])
        area_b = max(1, second["width"] * second["height"])
        return {"normalizedTravel": round(travel, 6), "areaRatio": round(area_b / area_a, 6)}

    for scene in direction.scenes:
        if scene.entrance != "cut":
            cursor -= scene.transition_frames
        for element in scene.elements:
            if element.region_of_interest is not None:
                samples = []
                for frame in requested:
                    if not (
                        cursor + element.start_frame
                        <= frame
                        < cursor + element.start_frame + element.duration_frames
                    ):
                        continue
                    for item in geometry_samples.get(frame, []):
                        if item.get("semanticId") != element.id or not item.get("visible"):
                            continue
                        measurement = item.get("roiMeasurement")
                        if measurement is not None:
                            samples.append({"frame": frame, **measurement})
                minimum_visible = min(
                    (sample.get("visibleRatio", 0) for sample in samples), default=None
                )
                roi_evidence.append(
                    {
                        "sceneId": scene.id,
                        "elementId": element.id,
                        "purpose": element.region_of_interest.purpose,
                        "cropIntentional": element.crop_intentional,
                        "samples": samples,
                        "minimumVisibleRatio": minimum_visible,
                        "status": "unobserved"
                        if not samples
                        else "observed"
                        if minimum_visible is not None and minimum_visible >= 0.95
                        else "requires_review",
                    }
                )
                if samples and minimum_visible is not None and minimum_visible < 0.95:
                    rendered_findings.append(
                        {
                            "sceneId": scene.id,
                            "elementId": element.id,
                            "startSeconds": samples[0]["frame"] / float(timeline_rate),
                            "endSeconds": samples[-1]["frame"] / float(timeline_rate),
                            "code": "material_region_of_interest_clipped",
                            "severity": "correction",
                            "category": "material_framing",
                            "impact": "essential_content_visibility",
                            "evidence": {
                                "minimumVisibleRatio": minimum_visible,
                                "samples": len(samples),
                                "measurement": "renderer_axis_aligned_object_fit",
                            },
                            "confidence": 0.9,
                            "uncertainty": (
                                "Axis-aligned browser measurement does not reconstruct "
                                "perspective or a rotated ancestor's source-space polygon."
                            ),
                            "correction": (
                                "Reframe the material so the declared region of interest remains visible."
                            ),
                        }
                    )
            for cue in element.motion_cues:
                start = cursor + element.start_frame + cue.start_frame
                end = start + cue.duration_frames - 1
                middle = start + round((end - start) * 0.58)
                score = difference(crop_for(element, start), crop_for(element, end))
                middle_score = difference(crop_for(element, start), crop_for(element, middle))
                start_geometry = geometry_for(element, start)
                middle_geometry = geometry_for(element, middle)
                end_geometry = geometry_for(element, end)
                geometry_change = geometry_delta(start_geometry, end_geometry)
                expected_hold = cue.kind == "deliberate_hold"
                if expected_hold:
                    verified = score is not None and score <= 0.01 and (
                        geometry_change is None
                        or (
                            geometry_change["normalizedTravel"] <= 0.005
                            and abs(geometry_change["areaRatio"] - 1) <= 0.01
                        )
                    )
                    criterion = "stable_pixels_and_geometry"
                elif cue.kind == "emphasis" and start_geometry and middle_geometry and end_geometry:
                    start_area = start_geometry["width"] * start_geometry["height"]
                    middle_area = middle_geometry["width"] * middle_geometry["height"]
                    end_area = end_geometry["width"] * end_geometry["height"]
                    verified = (
                        middle_area > max(start_area, end_area) * 1.01
                        and abs(end_area / max(1, start_area) - 1) < 0.25
                    )
                    criterion = "anticipation_peak_and_stabilization"
                else:
                    verified = score is not None and (score > 0.01 or (middle_score or 0) > 0.01)
                    criterion = "temporal_pixel_or_geometry_change"
                observed_basis = score is not None or (
                    cue.kind == "emphasis"
                    and start_geometry is not None
                    and middle_geometry is not None
                    and end_geometry is not None
                )
                action_evidence.append(
                    {
                        "sceneId": scene.id,
                        "elementId": element.id,
                        "cue": cue.kind,
                        "profile": cue.profile,
                        "startFrame": start,
                        "endFrame": end,
                        "middleFrame": middle,
                        "normalizedPixelDifference": score,
                        "middlePixelDifference": middle_score,
                        "geometryChange": geometry_change,
                        "geometryOrigin": "renderer_dom_geometry" if start_geometry else "declared_static_bounds",
                        "criterion": criterion,
                        "status": "unobserved"
                        if not observed_basis
                        else "observed"
                        if verified
                        else "requires_review",
                    }
                )
            element_frames = [
                frame
                for frame in requested
                if cursor + element.start_frame <= frame < cursor + element.start_frame + element.duration_frames
                and frame in evidence
            ]
            scores = [
                difference(crop_for(element, first), crop_for(element, second))
                for first, second in zip(element_frames, element_frames[1:], strict=False)
            ]
            scores = [score for score in scores if score is not None]
            if scores:
                region_motion.append(
                    {
                        "sceneId": scene.id,
                        "elementId": element.id,
                        "visualRole": element.visual_role,
                        "samplePairs": len(scores),
                        "meanNormalizedPixelDifference": round(sum(scores) / len(scores), 6),
                        "maximumNormalizedPixelDifference": max(scores),
                    }
                )
        cursor += scene.duration_frames
    for state in audit["states"]:
        state["observedFrames"] = {name: frame for name, frame in state["frames"].items() if frame in evidence}
        state["status"] = (
            "awaiting_visual_review"
            if len(state["observedFrames"]) == len(state["frames"])
            else "incomplete_rendered_coverage"
        )
    semantic_evidence = []

    def audible_interval(start_seconds, duration_seconds):
        completed = subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-ss",
                f"{start_seconds:.6f}",
                "-t",
                f"{duration_seconds:.6f}",
                "-i",
                str(path),
                "-vn",
                "-ac",
                "1",
                "-ar",
                "8000",
                "-f",
                "s16le",
                "pipe:1",
            ],
            capture_output=True,
            timeout=30,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if completed.returncode or len(completed.stdout) < 2:
            return {"status": "inconclusive", "sampleCount": 0, "rms": None, "peak": None}
        sample_count = len(completed.stdout) // 2
        samples = struct.unpack(f"<{sample_count}h", completed.stdout[: sample_count * 2])
        rms = (sum(sample * sample for sample in samples) / max(1, sample_count)) ** 0.5
        peak = max((abs(sample) for sample in samples), default=0)
        return {
            "status": "passed" if rms >= 20 and peak >= 100 else "failed",
            "sampleCount": sample_count,
            "rms": round(rms, 3),
            "peak": peak,
        }

    cursor = 0
    for scene in direction.scenes:
        if scene.entrance != "cut":
            cursor -= scene.transition_frames
        indexed = {element.id: element for element in scene.elements}
        content_references = {reference.id: reference for reference in direction.content_references}

        def descendants(target_id, scene=scene, indexed=indexed):
            result = []
            for candidate in scene.elements:
                parent = candidate.parent_id
                while parent:
                    if parent == target_id:
                        result.append(candidate)
                        break
                    parent = indexed.get(parent).parent_id if indexed.get(parent) else None
            return result

        for assertion in scene.semantic_assertions:
            interval = assertion.end_frame_exclusive - assertion.start_frame
            checkpoints = {
                cursor
                + assertion.start_frame
                + round(index * (interval - 1) / max(1, max(3, len(assertion.target_ids)) - 1))
                for index in range(max(3, len(assertion.target_ids)))
            }
            for target_id in assertion.target_ids:
                target = indexed.get(target_id)
                if not target:
                    continue
                active_start = max(assertion.start_frame, target.start_frame)
                active_end = min(
                    assertion.end_frame_exclusive,
                    target.start_frame + target.duration_frames,
                ) - 1
                if active_end >= active_start:
                    checkpoints.add(state_probe_frame(cursor, active_start, active_end))
            checkpoints = sorted(checkpoints)
            checkpoint_coverage = all(frame in evidence for frame in checkpoints)
            targets = [indexed[target_id] for target_id in assertion.target_ids if target_id in indexed]
            visibility = {
                target.id: [bool((geometry_for(target, frame) or {}).get("visible")) for frame in checkpoints]
                for target in targets
            }
            part_visibility = {}
            state_content_visibility = {}
            pixel_evidence = {}
            observed_state_frames = {}
            observed_viewport_aspects = {}
            primary_media_similarity = None
            sequence_ordered = None
            interface_event = None
            interface_geometry = []
            contract_ok = True
            reason = ""
            if assertion.kind in {"content_present", "content_continuity", "format_adaptation"}:
                reference_ids = {target.content_reference_id for target in targets}
                contract_ok = reference_ids == {assertion.object_id}
                if contract_ok and assertion.required_part_ids:
                    for target in targets:
                        bound_children = [
                            child
                            for child in descendants(target.id)
                            if child.content_reference_id == assertion.object_id and child.content_part_id
                        ]
                        bound_parts = {child.content_part_id for child in bound_children}
                        if not set(assertion.required_part_ids).issubset(bound_parts):
                            contract_ok = False
                            reason = "A derived state does not contain every required canonical content part."
                            break
                        for part_id in assertion.required_part_ids:
                            candidates = [child for child in bound_children if child.content_part_id == part_id]
                            part_visibility[f"{target.id}:{part_id}"] = [
                                any(bool((geometry_for(child, frame) or {}).get("visible")) for child in candidates)
                                and visibility[target.id][index]
                                for index, frame in enumerate(checkpoints)
                            ]
                if not contract_ok and not reason:
                    reason = "The rendered targets are not bound to the asserted canonical content."
            if assertion.kind == "format_adaptation" and contract_ok:
                formats = {
                    item
                    for composition in scene.compositions
                    if composition.family == "format_transformation"
                    and set(assertion.target_ids).issubset(set(composition.target_ids))
                    for item in composition.viewport_formats
                }
                if len(formats) < 2:
                    contract_ok = False
                    reason = "The same content was not projected into two distinct viewport formats."
            feed_content_ok = True
            if assertion.kind in {"feed_insertion", "feed_passage"}:
                target = targets[0]
                feed_content_ok = (
                    bool(assertion.required_part_ids)
                    and target.content_reference_id == assertion.object_id
                )
                bound_children = [
                    child
                    for child in descendants(target.id)
                    if child.content_reference_id == assertion.object_id and child.content_part_id
                ]
                bound_parts = {child.content_part_id for child in bound_children}
                feed_content_ok = feed_content_ok and set(assertion.required_part_ids).issubset(bound_parts)
                visible_indices = [index for index, visible in enumerate(visibility[target.id]) if visible]
                if feed_content_ok and visible_indices:
                    selected_index = visible_indices[len(visible_indices) // 2]
                    selected_frame = checkpoints[selected_index]
                    observed_state_frames[target.id] = selected_frame
                    for part_id in assertion.required_part_ids:
                        candidate = next(
                            (child for child in bound_children if child.content_part_id == part_id),
                            None,
                        )
                        pixel_evidence[f"{target.id}:{part_id}"] = (
                            visual_signal(candidate, selected_frame)
                            if candidate
                            else {
                                "status": "inconclusive",
                                "frame": selected_frame,
                                "lumaStdDev": None,
                                "signature": None,
                            }
                        )
                    feed_content_ok = all(
                        item["status"] == "observed" for item in pixel_evidence.values()
                    )
                else:
                    feed_content_ok = False
            if assertion.kind == "audible_event":
                asserted_audio = next(
                    (
                        audio_item
                        for audio_item in scene.audio
                        if audio_item.id in assertion.target_ids
                        and audio_item.role == "effect"
                        and audio_item.asset_id
                        and audio_item.start_frame < assertion.end_frame_exclusive
                        and audio_item.start_frame + audio_item.duration_frames > assertion.start_frame
                    ),
                    None,
                )
                audio = audible_interval(
                    (cursor + assertion.start_frame) / float(timeline_rate),
                    interval / float(timeline_rate),
                )
                status = audio["status"] if asserted_audio else "failed"
                reason = (
                    "A bound effect event and decoded mixed audio are both present in the asserted interval."
                    if status == "passed" and asserted_audio
                    else "No materialized effect event is bound to the asserted interval."
                    if not asserted_audio
                    else "The asserted interval has no measurable audible signal in the exported mix."
                    if status == "failed"
                    else "The exported audio interval could not be decoded."
                )
            elif not contract_ok:
                status = "failed"
            elif not checkpoint_coverage:
                status = "inconclusive"
                reason = "The assertion interval was not fully sampled."
            elif assertion.kind in {"content_present", "content_continuity", "format_adaptation"}:
                states_visible = all(any(visibility[target.id]) for target in targets)
                state_content_visibility = {
                    target.id: [
                        visibility[target.id][index]
                        and all(
                            part_visibility.get(f"{target.id}:{part_id}", [False] * len(checkpoints))[index]
                            for part_id in assertion.required_part_ids
                        )
                        for index in range(len(checkpoints))
                    ]
                    for target in targets
                }
                parts_visible = all(any(samples) for samples in state_content_visibility.values())
                requires_pixels = assertion.evidence_required in {
                    "rendered_pixels_and_geometry",
                    "temporal_sequence",
                }
                for target in targets:
                    complete_indices = [
                        index
                        for index, visible in enumerate(state_content_visibility[target.id])
                        if visible
                    ]
                    if not complete_indices:
                        continue
                    selected_index = complete_indices[len(complete_indices) // 2]
                    selected_frame = checkpoints[selected_index]
                    observed_state_frames[target.id] = selected_frame
                    target_geometry = geometry_for(target, selected_frame)
                    if target_geometry and target_geometry["height"] > 0:
                        observed_viewport_aspects[target.id] = round(
                            target_geometry["width"] / target_geometry["height"], 6
                        )
                    bound_children = [
                        child
                        for child in descendants(target.id)
                        if child.content_reference_id == assertion.object_id and child.content_part_id
                    ]
                    for part_id in assertion.required_part_ids:
                        candidate = next(
                            (child for child in bound_children if child.content_part_id == part_id),
                            None,
                        )
                        pixel_evidence[f"{target.id}:{part_id}"] = (
                            visual_signal(candidate, selected_frame)
                            if candidate
                            else {
                                "status": "inconclusive",
                                "frame": selected_frame,
                                "lumaStdDev": None,
                                "signature": None,
                            }
                        )
                ordered_frames = [observed_state_frames.get(target.id) for target in targets]
                sequence_ordered = (
                    all(frame is not None for frame in ordered_frames)
                    and all(left < right for left, right in zip(ordered_frames, ordered_frames[1:], strict=False))
                ) if len(targets) > 1 else bool(ordered_frames and ordered_frames[0] is not None)
                pixel_statuses = [item["status"] for item in pixel_evidence.values()]
                pixels_observed = bool(pixel_statuses) and all(status == "observed" for status in pixel_statuses)
                actual_format_change = True
                if assertion.kind == "format_adaptation":
                    aspects = list(observed_viewport_aspects.values())
                    actual_format_change = len(aspects) == len(targets) and any(
                        abs(left - right) >= 0.1
                        for left, right in zip(aspects, aspects[1:], strict=False)
                    )
                    reference = content_references.get(assertion.object_id)
                    primary_part_ids = {
                        part.id for part in reference.parts if part.role == "primary_media"
                    } if reference else set()
                    media_signatures = []
                    for target in targets:
                        for part_id in primary_part_ids:
                            observed = pixel_evidence.get(f"{target.id}:{part_id}", {})
                            signature = observed.get("contentSignature") or observed.get("signature")
                            if signature:
                                media_signatures.append(signature)
                    if len(media_signatures) >= 2:
                        similarities = [
                            signature_similarity(left, right)
                            for left, right in zip(media_signatures, media_signatures[1:], strict=False)
                        ]
                        primary_media_similarity = min(
                            (value for value in similarities if value is not None),
                            default=None,
                        )
                    if primary_part_ids and primary_media_similarity is None:
                        pixels_observed = False
                    elif primary_media_similarity is not None and primary_media_similarity < 0.52:
                        pixels_observed = False
                passed = (
                    states_visible
                    and parts_visible
                    and sequence_ordered
                    and actual_format_change
                    and (pixels_observed or not requires_pixels)
                )
                status = "passed" if passed else "failed"
                if not states_visible or not parts_visible:
                    reason = (
                        "At least one required canonical state or content part is not visible "
                        "in the exported interval."
                    )
                elif not sequence_ordered:
                    reason = "The canonical states were not observed in the asserted chronological order."
                elif not actual_format_change:
                    reason = "The exported target geometry does not demonstrate two distinct viewport formats."
                elif requires_pixels and not pixels_observed:
                    reason = (
                        "Visible geometry lacks discriminative pixel evidence for the canonical content "
                        "or its primary media changed."
                    )
                else:
                    reason = "Canonical parts have rendered pixel evidence in ordered, visibly distinct states."
            elif assertion.kind == "feed_insertion":
                target_visibility = visibility[targets[0].id]
                interface_composition = next(
                    (
                        composition
                        for composition in scene.compositions
                        if composition.family == "demonstrative_interface"
                        and targets[0].id in composition.target_ids
                    ),
                    None,
                )
                if interface_composition:
                    event_index = interface_composition.target_ids.index(targets[0].id)
                    interface_event = (
                        interface_composition.interface_events[event_index]
                        if interface_composition.interface_events
                        else ("open" if event_index == 0 else "select")
                    )
                interface_geometry = [
                    {"frame": frame, **geometry}
                    for frame in checkpoints
                    if (geometry := geometry_for(targets[0], frame)) is not None
                ]
                vertical_travel = (
                    abs(interface_geometry[-1]["y"] - interface_geometry[0]["y"]) / max(1, original_height)
                    if len(interface_geometry) >= 2
                    else 0
                )
                passed = (
                    feed_content_ok
                    and interface_event == "insert"
                    and not target_visibility[0]
                    and any(target_visibility[1:])
                    and vertical_travel >= 0.03
                )
                status = "passed" if passed else "failed"
                reason = (
                    "The bound feed item travels into the interface and becomes visible."
                    if passed
                    else "The feed item does not render the required canonical content parts."
                    if not feed_content_ok
                    else (
                        "A fade or visibility change without a bound insertion trajectory does not "
                        "prove feed insertion."
                    )
                )
            elif assertion.kind == "feed_passage":
                target_visibility = visibility[targets[0].id]
                interface_composition = next(
                    (
                        composition
                        for composition in scene.compositions
                        if composition.family == "demonstrative_interface"
                        and targets[0].id in composition.target_ids
                    ),
                    None,
                )
                if interface_composition:
                    event_index = interface_composition.target_ids.index(targets[0].id)
                    interface_event = (
                        interface_composition.interface_events[event_index]
                        if interface_composition.interface_events
                        else ("open" if event_index == 0 else "select")
                    )
                interface_geometry = [
                    {"frame": frame, **geometry}
                    for frame in checkpoints
                    if (geometry := geometry_for(targets[0], frame)) is not None
                ]
                vertical_travel = (
                    abs(interface_geometry[-1]["y"] - interface_geometry[0]["y"]) / max(1, original_height)
                    if len(interface_geometry) >= 2
                    else 0
                )
                passed = (
                    feed_content_ok
                    and
                    interface_event in {"pass", "scroll"}
                    and any(target_visibility[:-1])
                    and not target_visibility[-1]
                    and vertical_travel >= 0.03
                )
                status = "passed" if passed else "failed"
                reason = (
                    "The bound feed item follows a vertical passage and later leaves the viewport."
                    if passed
                    else "The feed item does not render the required canonical content parts."
                    if not feed_content_ok
                    else "Disappearance without a bound scrolling trajectory does not prove feed passage."
                )
            else:
                status = "inconclusive"
                reason = "No semantic verifier is registered for this assertion."
            semantic_evidence.append(
                {
                    "assertionId": assertion.id,
                    "sceneId": scene.id,
                    "kind": assertion.kind,
                    "essential": assertion.essential,
                    "status": status,
                    "checkpoints": checkpoints,
                    "visibility": visibility,
                    "partVisibility": part_visibility,
                    "completeContentVisibility": (
                        state_content_visibility
                        if assertion.kind in {"content_present", "content_continuity", "format_adaptation"}
                        else {}
                    ),
                    "pixelEvidence": pixel_evidence,
                    "observedStateFrames": observed_state_frames,
                    "observedViewportAspects": observed_viewport_aspects,
                    "sequenceOrdered": sequence_ordered,
                    "primaryMediaSimilarity": primary_media_similarity,
                    "interfaceEvent": interface_event,
                    "interfaceGeometry": interface_geometry,
                    "audioMeasurement": audio if assertion.kind == "audible_event" else None,
                    "reason": reason,
                    "evidenceRequired": assertion.evidence_required,
                    "evidenceBasis": (
                        "bound_effect_and_decoded_mix"
                        if assertion.kind == "audible_event"
                        else "rendered_pixels_geometry_and_contract"
                        if assertion.evidence_required
                        in {"rendered_pixels_and_geometry", "temporal_sequence"}
                        else "renderer_geometry_and_contract"
                    ),
                    "provesHumanComprehension": False,
                }
            )
            if assertion.essential:
                action_evidence.append(
                    {
                        "sceneId": scene.id,
                        "assertionId": assertion.id,
                        "criterion": "checksum_bound_semantic_sequence",
                        "startFrame": cursor + assertion.start_frame,
                        "endFrame": cursor + assertion.end_frame_exclusive - 1,
                        "status": "observed"
                        if status == "passed"
                        else "requires_review"
                        if status == "failed"
                        else "unobserved",
                    }
                )
        cursor += scene.duration_frames
    essential_semantics = [item for item in semantic_evidence if item["essential"]]
    semantic_required = direction.semantic_verification_policy == "canonical_demonstration_v1"
    semantic_status = (
        "not_applicable"
        if not semantic_required
        else
        "inconclusive"
        if not essential_semantics
        else "failed"
        if any(item["status"] == "failed" for item in essential_semantics)
        else "inconclusive"
        if any(item["status"] != "passed" for item in essential_semantics)
        else "passed"
    )
    execution_status = (
        "pending"
        if not action_evidence
        else "requires_review"
        if any(item["status"] != "observed" for item in action_evidence)
        else "observed"
    )
    audit.update(
        {
            "findings": [*audit.get("findings", []), *rendered_findings],
            "visualEditorial": "requires_correction"
            if any(
                item.get("severity") in {"correction", "blocker"}
                for item in [*audit.get("findings", []), *rendered_findings]
            )
            else audit.get("visualEditorial", "unreviewed"),
            "renderChecksum": sha256_file(path),
            "executableDirectionDigest": observed_direction_digest,
            "executableCompositionDigest": expected_composition_digest,
            "renderedEvidence": list(evidence.values()),
            "coverage": {
                "schemaVersion": "studio.visual-coverage.v2",
                "requestedFrames": len(requested),
                "observedFrames": len(evidence),
                "complete": len(evidence) == len(requested),
                "frameSampleComplete": len(evidence) == len(requested),
                "wholeVideoInspected": False,
                "rendererGeometryFrames": len(geometry_samples),
            },
            "executionVerification": {
                "status": execution_status,
                "evidence": action_evidence,
            },
            # Compatibility alias for stored v2 audit readers. It is execution
            # evidence only and cannot certify semantic completion.
            "actionVerification": {"status": execution_status, "evidence": action_evidence},
            "semanticVerification": {
                "policy": direction.semantic_verification_policy,
                "required": semantic_required,
                "status": semantic_status,
                "evidence": semantic_evidence,
            },
            "humanVerification": {"status": "pending", "evidence": []},
            "regionMotion": region_motion,
            "materialRegionOfInterest": roi_evidence,
            "limitations": [
                "Checkpoints do not prove continuous motion, material relevance or action completion.",
                "Declared contrast findings require review against the decoded images.",
                "Human scores are never inferred from successful decoding.",
                "Whole-video coverage is false until every required interval is inspected at its declared density.",
            ],
        }
    )
    return audit
