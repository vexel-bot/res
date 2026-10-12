"""Read-only validators for archived canonical timelines before Craft migration.

No image generation, timeline execution or media rendering lives in this module.
"""

from __future__ import annotations

import math
from typing import Literal

from pydantic import Field, model_validator

from ...domain.studios.contracts import (
    StudioContract,
    UgcShapeLayerPropertiesV1,
)
from ...domain.studios.editing_resources import ContextualTextStyleV1
from ...domain.studios.motion import MotionTrackV1

CAPABILITIES = {
    "cut": "Cortes e reorganização pela timeline",
    "multitrack": "Vídeo, fotografias e apoio visual em camadas",
    "reframe": "Enquadramento cover/contain e posição",
    "text": "Texto e legendas sincronizadas",
    "static_mask": "Máscara estática em escala de cinza",
    "keyframes": "Posição, escala, rotação e opacidade com curvas de movimento",
    "transition": "Entrada/saída por opacidade; dissolve entre clips sobrepostos",
    "freeze": "Congelar o frame no início do intervalo de origem",
    "speed": "Velocidade constante entre 0,5x e 2x",
    "color": "Exposição, contraste e saturação",
    "audio_mix": "Fala, ambiente, efeitos e música; ganho, pan e fades",
    "ducking": "Compressão da música orientada pela fala",
    "normalize": "Normalização para -16 LUFS e teto de -1,5 dBTP",
}
ADVANCED = ["tracking", "rotoscoping", "temporal_mask", "speed_ramp", "stabilization", "3d"]


class ClipCrop(StudioContract):
    top: float = Field(default=0, ge=0, lt=1)
    bottom: float = Field(default=0, ge=0, lt=1)
    left: float = Field(default=0, ge=0, lt=1)
    right: float = Field(default=0, ge=0, lt=1)

    @model_validator(mode="after")
    def valid_area(self):
        if self.top + self.bottom >= 1 or self.left + self.right >= 1:
            raise ValueError("editing_crop_empty")
        return self


class ClipTransform(StudioContract):
    fit: Literal["cover", "contain"] = "cover"
    anchor: Literal["center"] = "center"
    x: float = Field(default=0, ge=-8192, le=8192)
    y: float = Field(default=0, ge=-8192, le=8192)
    width: int | None = Field(default=None, ge=2, le=3840)
    height: int | None = Field(default=None, ge=2, le=3840)
    opacity: float = Field(default=1, ge=0, le=1)
    original_audio_enabled: bool = True
    scale: float = Field(default=1, ge=0.05, le=4)
    rotation: float = Field(default=0, ge=-360, le=360)
    crop: ClipCrop = Field(default_factory=ClipCrop)


class ClipEffect(StudioContract):
    kind: Literal["freeze", "color", "fade", "audio_role"]
    exposure: float = Field(default=0, ge=-2, le=2)
    contrast: float = Field(default=1, ge=0.25, le=3)
    saturation: float = Field(default=1, ge=0, le=3)
    in_frames: int = Field(default=0, ge=0)
    out_frames: int = Field(default=0, ge=0)
    role: Literal["dialogue", "narration", "ambience", "effect", "music"] = "dialogue"


def inspect_document(document) -> list[tuple[str, str]]:
    """Return target/code pairs before any render or cost reservation."""
    problems = []
    try:
        type(document).model_validate(document.model_dump(mode="json", by_alias=True))
    except ValueError:
        problems.append(("timeline", "document_contract_invalid"))
    timeline = document.composition.media_timeline
    if timeline is None:
        return [("timeline", "timeline_required")]
    if len(document.composition.pages) != 1 or document.composition.tracks:
        problems.append(("pages", "single_canvas_required"))
    page = document.composition.pages[0]
    fps = timeline.frame_rate.numerator / timeline.frame_rate.denominator
    if max(page.width, page.height) > 3840 or page.width % 2 or page.height % 2 or fps > 60:
        problems.append(("output", "output_profile_unsupported"))
    if timeline.duration_frames / fps > 1800:
        problems.append(("timeline", "duration_exceeds_qualified_30_minutes"))
    refs = {a.id: a for a in document.assets}
    seen = set()
    active_count = 0
    all_cues = []
    for track in timeline.tracks:
        if track.kind == "mask":
            target = next((t for t in timeline.tracks if t.id == track.target_track_id), None)
            if not target or target.kind not in {"video", "overlay"}:
                problems.append((track.id, "mask_target_unsupported"))
            ref = refs.get(track.artifact_asset_id)
            if not ref or not ref.media_type.startswith("image/"):
                problems.append((track.id, "static_image_mask_required"))
            if sum(t.kind == "mask" and t.target_track_id == track.target_track_id for t in timeline.tracks) > 1:
                problems.append((track.id, "multiple_masks_per_track_unsupported"))
        for clip in getattr(track, "clips", []):
            if clip.id in seen:
                problems.append((clip.id, "duplicate_clip_id"))
            seen.add(clip.id)
            if not clip.enabled or (track.kind == "audio" and track.muted):
                continue
            active_count += 1
            ref = refs.get(clip.asset_id)
            if not ref:
                problems.append((clip.id, "asset_missing"))
                continue
            if track.kind == "audio" and not ref.media_type.startswith(("audio/", "video/")):
                problems.append((clip.id, "audio_asset_required"))
            if track.kind in {"video", "overlay"} and not ref.media_type.startswith(("image/", "video/")):
                problems.append((clip.id, "visual_asset_required"))
            try:
                transform = ClipTransform.model_validate(clip.transform)
                if (
                    max(
                        (transform.width or page.width) * transform.scale,
                        (transform.height or page.height) * transform.scale,
                    )
                    > 3840
                ):
                    raise ValueError("scaled clip exceeds composition limit")
                effects = [ClipEffect.model_validate(e) for e in clip.effects]
                if len({e.kind for e in effects}) != len(effects):
                    raise ValueError("duplicate effects")
                if track.kind == "audio" and (
                    clip.transform or clip.keyframes or any(e.kind != "audio_role" for e in effects)
                ):
                    raise ValueError("unsupported audio operation")
                for effect in effects:
                    if effect.in_frames + effect.out_frames > clip.timeline.duration_frames:
                        raise ValueError("fade exceeds clip")
                    allowed = (
                        {"kind", "in_frames", "out_frames"}
                        if effect.kind == "fade"
                        else (
                            {"kind", "exposure", "contrast", "saturation"}
                            if effect.kind == "color"
                            else {"kind", "role"}
                            if effect.kind == "audio_role"
                            else {"kind"}
                        )
                    )
                    if effect.model_fields_set - allowed:
                        raise ValueError("inapplicable effect parameter")
                properties = set()
                for raw in clip.keyframes:
                    motion = MotionTrackV1.model_validate(raw)
                    if motion.target_layer_id != clip.id or motion.property not in {
                        "position_x",
                        "position_y",
                        "scale_x",
                        "scale_y",
                        "rotation_degrees",
                        "opacity",
                    }:
                        raise ValueError("unsupported motion property")
                    if motion.property in properties:
                        raise ValueError("duplicate motion property")
                    properties.add(motion.property)
                    if any(
                        k.easing == "cubic_bezier"
                        or not math.isfinite(k.value)
                        or k.frame >= clip.timeline.duration_frames
                        for k in motion.keyframes
                    ):
                        raise ValueError("unsupported motion interval or easing")
                    if len(motion.keyframes) > 64:
                        raise ValueError("motion keyframe limit")
                    if motion.property in {"scale_x", "scale_y"} and any(k.value > 4 for k in motion.keyframes):
                        raise ValueError("motion scale limit")
                if any(not math.isfinite(x) for x in [transform.x, transform.y, transform.opacity, clip.playback_rate]):
                    raise ValueError("non-finite parameter")
                if track.kind == "audio" and clip.fade_in_frames + clip.fade_out_frames > clip.timeline.duration_frames:
                    raise ValueError("audio fade exceeds clip")
                freeze = any(e.kind == "freeze" for e in effects)
                if not ref.media_type.startswith("image/") and not freeze:
                    if (
                        not clip.source
                        or clip.source.duration_microseconds / 1e6 + 1 / fps
                        < clip.timeline.duration_frames / fps * clip.playback_rate
                    ):
                        raise ValueError("source interval too short")
            except ValueError:
                problems.append((clip.id, "clip_operation_unsupported"))
        if track.kind == "caption":
            previous_end = 0
            for cue in sorted(track.cues, key=lambda c: c.timeline.start_frame):
                all_cues.append(cue)
                if (
                    cue.timeline.start_frame < previous_end
                    or cue.timeline.start_frame + cue.timeline.duration_frames > timeline.duration_frames
                ):
                    problems.append((cue.id, "caption_overlap_or_out_of_bounds"))
                if cue.style.emphasis_color:
                    problems.append((cue.id, "word_emphasis_unsupported"))
                previous_end = cue.timeline.start_frame + cue.timeline.duration_frames
    previous_cue = None
    for cue in sorted(all_cues, key=lambda c: c.timeline.start_frame):
        if (
            previous_cue
            and cue.timeline.start_frame < previous_cue.timeline.start_frame + previous_cue.timeline.duration_frames
        ):
            problems.append((cue.id, "caption_tracks_overlap"))
        if (
            previous_cue is None
            or cue.timeline.start_frame + cue.timeline.duration_frames
            > previous_cue.timeline.start_frame + previous_cue.timeline.duration_frames
        ):
            previous_cue = cue
    if active_count + sum(layer.visible for layer in page.layers) > 100 or len(all_cues) > 500:
        problems.append(("timeline", "active_clip_limit_100"))
    for layer in page.layers:
        if not layer.visible:
            continue
        allowed = (
            {
                "text",
                "fontSize",
                "color",
                "align",
                "fontWeight",
                "fontFamily",
                "fontAssetId",
                "type",
                "schemaVersion",
                "lineHeight",
                "minFontSize",
            }
            if layer.kind == "text"
            else {"fill", "radius", "shape", "type", "schemaVersion"}
        )
        if layer.kind not in {"text", "shape"} or layer.rotation or set(layer.properties) - allowed:
            problems.append((layer.id, "page_layer_unsupported"))
        if layer.kind == "shape" and layer.properties.get("shape", "rectangle") != "rectangle":
            problems.append((layer.id, "shape_unsupported"))
        try:
            if layer.kind == "shape":
                UgcShapeLayerPropertiesV1.model_validate(layer.properties)
            elif layer.kind == "text":
                ContextualTextStyleV1.model_validate(layer.properties)
        except ValueError:
            problems.append((layer.id, "layer_properties_invalid"))
    return list(dict.fromkeys(problems))


def used_capabilities(document, audible_asset_ids=frozenset()):
    capabilities = {"cut"}
    timeline = document.composition.media_timeline
    if not timeline:
        return capabilities
    visual_clips = [c for t in timeline.tracks if t.kind in {"video", "overlay"} for c in t.clips if c.enabled]
    if len(visual_clips) > 1:
        capabilities.add("multitrack")
    if any(t.kind == "mask" for t in timeline.tracks):
        capabilities.add("static_mask")
    if any(t.kind == "caption" and t.cues for t in timeline.tracks) or any(
        layer.visible and layer.kind == "text" for layer in document.composition.pages[0].layers
    ):
        capabilities.add("text")
    audio_roles = set()
    references = {a.id: a for a in document.assets}
    for track in timeline.tracks:
        for clip in getattr(track, "clips", []):
            if not clip.enabled or (track.kind == "audio" and track.muted):
                continue
            transform = ClipTransform.model_validate(clip.transform)
            has_audio = clip.asset_id in audible_asset_ids and (
                track.kind == "audio"
                or (
                    transform.original_audio_enabled
                    and not getattr(track, "muted", False)
                    and not any(e.get("kind") == "freeze" for e in clip.effects)
                )
            )
            if has_audio:
                capabilities.update({"audio_mix", "normalize"})
                role = next(
                    (e.get("role", "dialogue") for e in clip.effects if e.get("kind") == "audio_role"),
                    "dialogue"
                    if track.kind == "video" or references[clip.asset_id].media_type.startswith("video/")
                    else "effect",
                )
                audio_roles.add(role)
            if clip.transform:
                capabilities.add("reframe")
            if clip.keyframes:
                capabilities.add("keyframes")
            if clip.playback_rate != 1:
                capabilities.add("speed")
            for effect in clip.effects:
                if effect.get("kind") == "audio_role":
                    continue
                capabilities.add(
                    {"fade": "transition", "audio_role": "audio_mix"}.get(effect.get("kind"), effect.get("kind"))
                )
    if "music" in audio_roles and audio_roles & {"dialogue", "narration"}:
        capabilities.add("ducking")
    return capabilities
