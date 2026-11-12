"""Bounded Claude refinement between local direction and the real editorial preview."""

import json
import re
import tempfile
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field

from ...domain.studios.agents import AgentOutput
from ...domain.studios.contracts import CreativeCompositionV1, CreativeLayerV1, SourceTimeRangeV1, StudioContract, TimelineFrameRangeV1
from ...domain.studios.local_composition import LocalLayerStyle
from ...domain.studios.timeline_editor import CropWindow, MotionKey, VisualMotion
from ...providers.studios import timeline_ffmpeg
from . import llm_connections, motion_editorial
from .craft import workspace_files
from .gemini_editing import measured_request_cost

MODEL = "claude-opus-5-5"
ENDPOINT = "https://api.anthropic.com/v1"
OUTPUT_TOKENS = 4096
CUT_OUTPUT_TOKENS = 6000
CUT_BUDGET_USD = 1.50
HexColor = Annotated[str, Field(pattern=r"^#[0-9a-fA-F]{6}$")]


def binding(db, workspace, connection_id):
    row, adapter, _, _ = llm_connections.planner(db, workspace, connection_id, MODEL)
    config = row.config
    if (
        row.provider != "anthropic" or config["protocol"] != "anthropic_messages"
        or config["baseUrl"] != ENDPOINT or config.get("requestPath") not in (None, "/messages")
        or config["authHeader"].lower() != "x-api-key" or config["authPrefix"]
        or config["billingMode"] != "metered"
        or not re.fullmatch(r"wrkspc_[A-Za-z0-9]{16,80}", config.get("extraHeaders", {}).get("anthropic-workspace-id", ""))
    ):
        raise ValueError("editorial_claude_connection_invalid")
    return row, adapter


class LayerEdit(StudioContract):
    id: str = Field(min_length=1, max_length=120)
    x: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    y: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    width: float | None = Field(default=None, ge=2, allow_inf_nan=False)
    height: float | None = Field(default=None, ge=2, allow_inf_nan=False)
    font_size: int | None = Field(default=None, ge=14, le=160)
    align: Literal["left", "center", "right"] | None = None
    keyframes: list[MotionKey] | None = Field(default=None, max_length=12)


class MotionRefinement(StudioContract):
    edits: list[LayerEdit] = Field(min_length=1, max_length=12)
    rationale: str = Field(min_length=1, max_length=900)


class CutLayerEdit(LayerEdit):
    start_frame: int | None = Field(default=None, ge=0, le=36000)
    duration_frames: int | None = Field(default=None, ge=1, le=36000)
    color: HexColor | None = None
    fill: HexColor | None = None
    z_index: int | None = Field(default=None, ge=0, le=100)


class CreativeLayerEdit(CutLayerEdit):
    text: str | None = Field(default=None, min_length=1, max_length=110)


class Graphic(StudioContract):
    x: float = Field(ge=0, allow_inf_nan=False)
    y: float = Field(ge=0, allow_inf_nan=False)
    width: float = Field(ge=2, allow_inf_nan=False)
    height: float = Field(ge=2, allow_inf_nan=False)
    fill: HexColor
    radius: int = Field(default=0, ge=0, le=120)
    shape: Literal["rectangle", "ellipse"] = "rectangle"
    z_index: int = Field(ge=0, le=100)
    start_frame: int = Field(ge=0)
    duration_frames: int = Field(ge=1)
    keyframes: list[MotionKey] = Field(default_factory=list, max_length=10)


class ClipSlip(StudioContract):
    track_id: str = Field(min_length=1, max_length=120)
    clip_id: str = Field(min_length=1, max_length=120)
    source_start_microseconds: int = Field(ge=0, le=86_400_000_000)


class CutRefinement(StudioContract):
    edits: list[CutLayerEdit] = Field(default_factory=list, max_length=16)
    clip_slips: list[ClipSlip] = Field(default_factory=list, max_length=8)
    background: HexColor | None = None
    rationale: str = Field(min_length=1, max_length=900)


class Recut(ClipSlip):
    start_frame: int = Field(ge=0)
    duration_frames: int = Field(ge=1)
    crop: CropWindow | None = None


class CreativeCut(CutRefinement):
    edits: list[CreativeLayerEdit] = Field(default_factory=list, max_length=16)
    graphics: list[Graphic] = Field(default_factory=list, max_length=6)
    recuts: list[Recut] = Field(default_factory=list, max_length=8)


def _editable_clips(comp, roles):
    return {(track.id, clip.id): clip for track in comp.media_timeline.tracks
            if track.kind == "video" and track.muted and not track.locked
            for clip in track.clips if clip.enabled and not clip.locked and clip.source is not None
            and roles.get(clip.asset_id) not in {"logo", "interface"}}


def apply_refinement(comp, plan, roles, source_limits=None):
    candidate = comp.model_copy(deep=True)
    page = candidate.pages[0]
    layers = {layer.id: layer for layer in page.layers if not layer.locked and layer.visible}
    seen = set()
    for edit in plan.edits:
        layer = layers.get(edit.id)
        if edit.id in seen or layer is None:
            raise ValueError("editorial_claude_layer_invalid")
        seen.add(edit.id)
        style = LocalLayerStyle.model_validate(layer.properties)
        protected = roles.get(style.asset_id) in {"logo", "interface"}
        for field in ("x", "y", "width", "height"):
            value = getattr(edit, field)
            if value is not None:
                setattr(layer, field, value)
        if layer.x + layer.width > page.width or layer.y + layer.height > page.height:
            raise ValueError("editorial_claude_layer_outside_canvas")
        if edit.font_size is not None or edit.align is not None:
            if layer.kind != "text":
                raise ValueError("editorial_claude_text_style_invalid")
            if edit.font_size is not None:
                style.font_size = edit.font_size
            if edit.align is not None:
                style.align = edit.align
        if edit.keyframes is not None:
            if any(k.property not in {"x", "y", "scale", "rotation", "opacity"} for k in edit.keyframes):
                raise ValueError("editorial_claude_keyframe_invalid")
            if protected and any(k.property != "opacity" for k in edit.keyframes):
                raise ValueError("editorial_claude_protected_asset_motion_invalid")
            style.keyframes = edit.keyframes
        if isinstance(edit, CreativeLayerEdit) and edit.text is not None:
            if layer.kind != "text" or not edit.text.strip():
                raise ValueError("editorial_claude_text_style_invalid")
            style.text = edit.text.strip()
        if isinstance(edit, CutLayerEdit):
            if edit.color is not None:
                if layer.kind != "text":
                    raise ValueError("editorial_claude_text_style_invalid")
                style.color = edit.color
            if edit.fill is not None:
                if layer.kind != "shape":
                    raise ValueError("editorial_claude_shape_style_invalid")
                style.fill = edit.fill
            for field in ("start_frame", "duration_frames"):
                if getattr(edit, field) is not None:
                    setattr(style, field, getattr(edit, field))
            if edit.z_index is not None:
                layer.z_index = edit.z_index
        layer.properties = style.model_dump(mode="json", by_alias=True, exclude_defaults=True)
        layer.properties["schemaVersion"] = style.schema_version
    if isinstance(plan, CutRefinement):
        if plan.background:
            page.background = plan.background
        clips = _editable_clips(candidate, roles)
        for slip in plan.clip_slips:
            clip = clips.pop((slip.track_id, slip.clip_id), None)
            if clip is None:
                raise ValueError("editorial_claude_clip_invalid")
            if source_limits is not None and (slip.source_start_microseconds + clip.source.duration_microseconds >
                                              source_limits.get(clip.asset_id, 0)):
                raise ValueError("editorial_claude_source_outside_media")
            clip.source = SourceTimeRangeV1(start_microseconds=slip.source_start_microseconds,
                                          duration_microseconds=clip.source.duration_microseconds)
        if isinstance(plan, CreativeCut):
            timeline = candidate.media_timeline
            for cut in plan.recuts:
                clip = clips.pop((cut.track_id, cut.clip_id), None)
                if clip is None or cut.start_frame + cut.duration_frames > timeline.duration_frames:
                    raise ValueError("editorial_claude_clip_invalid")
                rate = timeline.frame_rate
                source_duration = round(cut.duration_frames * rate.denominator / rate.numerator * clip.playback_rate * 1e6)
                if cut.source_start_microseconds + source_duration > (source_limits or {}).get(clip.asset_id, 0):
                    raise ValueError("editorial_claude_source_outside_media")
                clip.timeline = TimelineFrameRangeV1(start_frame=cut.start_frame, duration_frames=cut.duration_frames)
                clip.source = SourceTimeRangeV1(start_microseconds=cut.source_start_microseconds,
                                                duration_microseconds=source_duration)
                if cut.crop:
                    motion = VisualMotion.model_validate(clip.transform)
                    motion.crop = cut.crop
                    clip.transform = motion.model_dump(mode="json", by_alias=True, exclude_defaults=True)
            existing = {layer.id for layer in page.layers}
            for index, item in enumerate(plan.graphics):
                identifier = f"opus-graphic-{index}"
                if (identifier in existing or item.x + item.width > page.width or item.y + item.height > page.height
                        or any(k.property not in {"x", "y", "scale", "rotation", "opacity"} for k in item.keyframes)):
                    raise ValueError("editorial_claude_graphic_invalid")
                geometry = item.model_dump(include={"x", "y", "width", "height", "z_index"})
                style = item.model_dump(mode="json", by_alias=True, exclude={"x", "y", "width", "height", "z_index"})
                page.layers.append(CreativeLayerV1(id=identifier, kind="shape", name="Grafismo Opus", **geometry,
                                                  properties={"schemaVersion":"studio.local-layer.v1", **style}))
        if candidate == comp:
            raise ValueError("editorial_claude_cut_unchanged")
    return candidate


def _cut_samples(db, record, contract, evidence, directory, cancelled, *, summary=None, render_copy=None, long_edge=360):
    from PIL import Image
    from .motion_editorial_review import _raw, render_and_review

    timeline = contract.composition.media_timeline
    page = contract.composition.pages[0]
    width, height = min(long_edge, round(long_edge*page.width/page.height)), min(long_edge, round(long_edge*page.height/page.width))
    edges = sorted({LocalLayerStyle.model_validate(layer.properties).start_frame for layer in page.layers if layer.visible} |
                   {clip.timeline.start_frame for track in timeline.tracks if track.kind == "video" for clip in track.clips if clip.enabled})
    # Sample just before/after up to two cuts, plus endpoints and progression.
    total = timeline.duration_frames
    fractions = {round((total-1)*p) for p in (.04, .23, .51, .76, .94)}
    frames = sorted(fractions | {n for edge in [n for n in edges if n > 0][:2] for n in (edge-1, edge+2) if n < total})
    select = "+".join(f"eq(n,{frame})" for frame in frames)
    with render_and_review(db, record, contract, evidence, cancelled) as (review, output):
        if not output:
            raise ValueError("editorial_claude_cut_evidence_unavailable")
        if render_copy is not None:
            import shutil

            shutil.copyfile(output, render_copy)
        raw = _raw(output, ["-an", "-vf", f"select='{select}',scale={width}:{height}", "-fps_mode", "passthrough",
                            "-c:v", "rawvideo", "-threads", "1", "-pix_fmt", "rgb24", "-f", "rawvideo"])
    if summary is not None:
        summary.update(review)
    pixels = width*height*3
    if len(raw) != len(frames)*pixels:
        raise ValueError("editorial_claude_cut_samples_incomplete")
    media = []
    for first in range(0, len(frames), 3):
        group = frames[first:first+3]
        strip = Image.new("RGB", (width*len(group), height))
        for index, _ in enumerate(group):
            offset = (first+index)*pixels
            strip.paste(Image.frombytes("RGB", (width,height), raw[offset:offset+pixels]), (index*width,0))
        file = Path(directory) / f"cut-samples-{first}.jpg"
        strip.save(file, quality=88)
        media.append((file, "image/jpeg"))
    return media, frames, review["renderChecksum"]


def _layout_creative_text(candidate):
    page = candidate.pages[0]
    changed = []
    for layer in page.layers:
        if layer.kind != "text" or layer.locked or not layer.visible:
            continue
        style = LocalLayerStyle.model_validate(layer.properties)
        minimum = max(16, round(page.width * 14 / 360))
        for backing in sorted(page.layers, key=lambda item: item.z_index, reverse=True):
            if (style.align != "center" or backing.kind != "shape" or backing.locked or not backing.visible
                    or backing.z_index >= layer.z_index or backing.opacity < 1
                    or abs(backing.x + backing.width/2 - layer.x - layer.width/2) > 24
                    or abs(backing.y - layer.y) > 12 or backing.width < layer.width*.7
                    or backing.height < minimum*1.3 + 16):
                continue
            plate = LocalLayerStyle.model_validate(backing.properties)
            if (plate.shape != "rectangle" or plate.gradient_end or plate.start_frame != style.start_frame
                    or plate.duration_frames != style.duration_frames
                    or not (plate.keyframes or motion_editorial.contrast(style.color, plate.fill) < 4.5)):
                continue
            # A paired label and backing are a single reading surface. Match their
            # boxes before the general review can mistake the canvas for the surface.
            colors = (style.color, "#FFFFFF", "#080D12")
            if motion_editorial.contrast(style.color, plate.fill) < 4.5:
                style.color = max(colors, key=lambda color: motion_editorial.contrast(color, plate.fill))
            layer.x, layer.y = backing.x + 8, backing.y + 8
            layer.width, layer.height = backing.width - 16, backing.height - 16
            motion_editorial._fit_text(page, layer, style, minimum)
            layer.y = max(layer.y, backing.y + (backing.height-style.font_size*1.3)/2)
            layer.height = backing.y + backing.height - layer.y
            plate.keyframes = []
            backing.properties = plate.model_dump(by_alias=True, mode="json", exclude_defaults=True)
            backing.properties["schemaVersion"] = plate.schema_version
            changed.append(layer.id)
            break
        try:
            motion_editorial._text_boxes(page, layer, style)
        except ValueError as error:
            if str(error) != "local_text_does_not_fit":
                raise
            # Preserve the anchor and type size when a new line needs more height.
            layer.height = max(layer.height, min(page.height - layer.y - 20, style.font_size * 2.65))
            motion_editorial._fit_text(page, layer, style, minimum)
            changed.append(layer.id)
        if layer.id in changed:
            layer.properties = style.model_dump(by_alias=True, mode="json", exclude_defaults=True)
            layer.properties["schemaVersion"] = style.schema_version
    return list(dict.fromkeys(changed))


def _cut_output(candidate, proposed):
    return AgentOutput.model_validate({
        "commands": [{"id": "composition.replace", "params": {"composition": candidate.model_dump(mode="json", by_alias=True)}}],
        "rationale": proposed.rationale,
    })


def refine(db, record, job, connection, adapter, local_output, evidence, instruction, cut_source=None, effort=None,
           creative=False, replay=None):
    from PIL import Image, ImageOps

    if cut_source is None:
        if not local_output.commands or local_output.commands[0].id != "composition.replace":
            raise ValueError("editorial_claude_local_candidate_required")
        comp = CreativeCompositionV1.model_validate(local_output.commands[0].params["composition"])
    else:
        if connection.config["inputUsdPerMillion"] < 4 or connection.config["outputUsdPerMillion"] < 20:
            raise ValueError("editorial_claude_cut_pricing_invalid")
        comp = cut_source.composition
        if not comp.media_timeline:
            raise ValueError("editorial_claude_cut_timeline_required")
    page = comp.pages[0]
    roles = evidence["materialSnapshot"]["roles"]
    layers = [layer.model_dump(mode="json", by_alias=True, exclude_defaults=True) for layer in page.layers
              if layer.visible and not layer.locked]
    image_ids = list(dict.fromkeys(layer["properties"].get("assetId") for layer in layers if layer["kind"] == "image"))[:3]
    image_ids = [identifier for identifier in image_ids if identifier]
    cards = [card for card in motion_editorial.knowledge()["cards"] if card["id"] in evidence["cardIds"]]
    context = {
        "editorialMotion": True,
        "instruction": instruction,
        "canvas": {"width": page.width, "height": page.height, "background": page.background},
        "timelineFrames": comp.media_timeline.duration_frames,
        "direction": evidence["receipts"][0],
        "motionCards": cards,
        "layers": layers,
        "assetRoles": roles,
        "imageOrder": image_ids,
        "structuredPlanningInstruction": (
            "For this Clicko refinement only, return JSON {edits:[{id,x?,y?,width?,height?,fontSize?,align?,keyframes?}],rationale}. "
            "Use the supplied schema. Propose distinct motion for photo, subject and reveal. Improve visual hierarchy and framing. "
            "Respect the canvas and keep text readable at phone width. Keyframe values x/y are offsets relative to layer position "
            "and frames are relative to each existing layer. No text, source, color, timing, audio, new layer or asset changes. "
            "For logos and interface layers use opacity only. Leave room for safe margins at the maximum animated scale. "
            "Images are original stills only, not evidence of completed motion."
        ),
        "outputSchema": MotionRefinement.model_json_schema(by_alias=True),
        "maxPromptChars": 28000,
        "maxOutputTokens": min(OUTPUT_TOKENS, connection.config["maxOutputTokens"]),
    }
    clips = _editable_clips(comp, roles) if effort else {}
    source_ids = list(dict.fromkeys(clip.asset_id for clip in clips.values())) if creative else []
    source_limits = {} if creative else None
    if replay is not None:
        with workspace_files(db, record, None, extra_asset_ids=source_ids) as (_, params, _):
            for asset in params["media"]:
                info = timeline_ffmpeg.probe(asset["path"])
                source_limits[asset["assetId"]] = int(float(info["format"]["duration"]) * 1e6)
        proposed = CreativeCut.model_validate(replay.result_payload["claudeRefinement"])
        candidate = apply_refinement(comp, proposed, roles, source_limits)
        fixed = _layout_creative_text(candidate)
        motion_editorial._fit_proof_images(db, record, candidate, evidence["format"], roles)
        evidence["claude"] = {"provider":"anthropic", "model":MODEL, "cutEffort":effort,
                              "creativeCut":True, "replayedTaskId":replay.id, "measuredCostUsd":0,
                              "originalMeasuredCostUsd":replay.result_payload.get("measuredCostUsd")}
        evidence["receipts"].append({"stage":"local_layout_repair","status":"complete","layerIds":fixed})
        return _cut_output(candidate, proposed)
    with tempfile.TemporaryDirectory() as visual_directory, workspace_files(
            db, record, None, extra_asset_ids=image_ids + source_ids) as (directory, params, _):
        paths = {entry["assetId"]: entry["path"] for entry in params["media"]}
        media = []
        for index, identifier in enumerate(image_ids):
            sample = Path(directory) / f"editorial-source-{index}.jpg"
            with Image.open(paths[identifier]) as source:
                image = ImageOps.exif_transpose(source).convert("RGBA")
                image.thumbnail((448, 448))
                background = Image.new("RGBA", image.size, page.background)
                background.alpha_composite(image)
                background.convert("RGB").save(sample, quality=83)
            media.append((sample, "image/jpeg"))
        if cut_source is not None:
            def cancelled():
                db.refresh(job, attribute_names=["status"])
                return job.status != "running"

            strips, frames, checksum = _cut_samples(db, record, cut_source, evidence, visual_directory, cancelled)
            if cancelled():
                raise InterruptedError("editorial_cut_cancelled")
            media.extend(strips)
            timeline = comp.media_timeline
            context.update(
                editorialCutEffort=effort,
                maxOutputTokens=min(CUT_OUTPUT_TOKENS, connection.config["maxOutputTokens"]),
                outputSchema=CutRefinement.model_json_schema(by_alias=True),
                cutFrames=[frames[i:i+3] for i in range(0, len(frames), 3)],
                cutFrameRate=timeline.frame_rate.model_dump(by_alias=True),
                editableClips=[{"trackId": track_id, **clip.model_dump(mode="json", by_alias=True,
                                include={"id", "asset_id", "label", "timeline", "source"})}
                               for (track_id, _), clip in clips.items()],
                structuredPlanningInstruction=(
                    "Edit the supplied existing cut as a motion director. After the asset stills, the filmstrips show real "
                    "samples of the current export left to right at cutFrames. Use them to diagnose the biggest visible failure. "
                    "Make a meaningful change to staging, rhythm and the handoff between shots. Use the schema to adjust "
                    "position, sizing, text color, background, layer timing, stack order and motion. Layer times are absolute "
                    "but keyframe frames and x/y offsets are relative to their layer. When retiming, coordinate all visual "
                    "and text layers and avoid any empty frames or overlapping titles. Preserve words, assets, full duration "
                    "and all audio. Keep logos and interfaces at original aspect and use only opacity in their keyframes. "
                    "For listed muted video clips a slip changes source in-point at fixed duration. Keep range within media. "
                    "Never assume continuous playback or audible evidence. Return edits, optional background and clipSlips, "
                    "and rationale citing frames with the observed problem and the intended correction."
                ),
            )
        if creative:
            from .motion_editorial_review import _raw

            context.update(creativeCut=True, maxOutputTokens=connection.config["maxOutputTokens"],
                           outputSchema=CreativeCut.model_json_schema(by_alias=True))
            context["structuredPlanningInstruction"] = context["structuredPlanningInstruction"].replace(
                "Preserve words, assets, full duration and all audio.", "Preserve assets, full duration and all audio."
            ) + (
                " This is a creative recut. You may rewrite titles and CTA using only facts and destination authorized in the brief. "
                "You may add vector graphics with a specific role and reassemble muted editable clips using recuts, respecting source limits. "
                "A recut may move, shorten, extend or reframe a clip. Cover the visual timeline without gaps. Keep audio, approved media and total duration. "
                "Choose a different editorial structure if it serves the audience. Anchor the ad in the observed proof and do not invent features, prices or results. "
                "Use concise Portuguese copy. Recuts replaces clipSlips for modified clips. Design legible phone-sized captions over a solid backplate if needed."
            )
            for identifier in source_ids:
                meta = timeline_ffmpeg.probe(paths[identifier])
                source_limits[identifier] = int(float(meta["format"]["duration"]) * 1e6)
            context["sourceLimitsMicroseconds"] = source_limits
            if source_ids and len(media) < 6:
                identifier = source_ids[0]
                filename = Path(visual_directory) / "raw-coverage.jpg"
                duration = source_limits[identifier] / 1e6
                interval = duration / 8
                data = _raw(paths[identifier], ["-an", "-vf", f"fps=1/{interval},scale=180:-2,tile=4x2",
                                                "-frames:v", "1", "-c:v", "mjpeg", "-f", "image2pipe"])
                if data:
                    filename.write_bytes(data)
                    media.append((filename, "image/jpeg"))
                    context["rawCoverage"] = {"assetId": identifier, "durationSeconds": duration,
                                              "sampleIntervalSeconds": interval, "image": "last; scan left to right and top to bottom"}
        prompt_bytes = len(json.dumps(context, ensure_ascii=False).encode())
        if prompt_bytes > context["maxPromptChars"]:
            raise ValueError("editing_ai_prompt_too_large")
        llm_connections.reserve_request(db, job, connection, prompt_bytes + 1024 + len(media) * 6000,
                                        context["maxOutputTokens"], max_amount=CUT_BUDGET_USD if effort else None, reserve_full=creative)
        job.result_payload = {**(job.result_payload or {}), "submissionStarted": True, "submissionOutcome": "unknown"}
        db.commit()
        response = adapter.plan(MODEL, context, media)
    usage = response["usage"]
    cost = measured_request_cost(job, usage)
    job.result_payload = {**job.result_payload, "submissionOutcome": "response_received",
                          "measuredCostUsd": cost, "usage": usage}
    db.commit()  # Usage remains available if the model output or preview is rejected.
    if adapter.credential and adapter.credential in response["text"]:
        raise ValueError("editorial_claude_response_credential_rejected")
    schema = CreativeCut if creative else CutRefinement if effort else MotionRefinement
    proposed = schema.model_validate_json(response["text"])
    job.result_payload = {**job.result_payload, "claudeRefinement": proposed.model_dump(mode="json", by_alias=True)}
    db.commit()
    candidate = apply_refinement(comp, proposed, roles, source_limits)
    if creative:
        fixed = _layout_creative_text(candidate)
        if fixed:
            evidence["receipts"].append({"stage":"local_layout_repair","status":"complete","layerIds":fixed})
    motion_editorial._fit_proof_images(db, record, candidate, evidence["format"], roles)
    evidence["receipts"].append({"stage": "claude_refinement", "status": "complete", "layerIds": [e.id for e in proposed.edits]})
    evidence["claude"] = {"provider": "anthropic", "model": response.get("responseModel") or MODEL,
                          "usage": usage, "measuredCostUsd": cost, "imageEvidence": image_ids}
    if effort:
        evidence["claude"].update(cutEffort=effort, cutFrames=frames, sourceRenderChecksum=checksum,
                                  generationBudgetUsd=CUT_BUDGET_USD, creativeCut=creative)
    return _cut_output(candidate, proposed)
