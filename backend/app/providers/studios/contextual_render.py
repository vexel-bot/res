"""Bounded multi-track FFmpeg compiler. Never accepts raw filter expressions.

Filter semantics: https://ffmpeg.org/ffmpeg-filters.html . All times are converted
from the canonical timeline; masks are grayscale static images in clip space.
"""

from __future__ import annotations

import copy
import math
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Literal

from PIL import Image, ImageDraw, ImageFont
from pydantic import Field, model_validator

from ...domain.studios.contextual_editing import CONTEXTUAL_PROVIDER
from ...domain.studios.contracts import (
    StudioContract,
    UgcShapeLayerPropertiesV1,
    VideoRenderEncodeResultV1,
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


def motion_expression(clip, prop: str, fps: float, default: float, *, local_time=False, variable="t") -> str:
    track = next(
        (MotionTrackV1.model_validate(k) for k in clip.keyframes if MotionTrackV1.model_validate(k).property == prop),
        None,
    )
    if not track:
        return str(default)
    keys = track.keyframes
    local = variable if local_time else f"({variable}-{clip.timeline.start_frame / fps:.9f})"
    expression = str(keys[-1].value)
    for a, b in reversed(list(zip(keys[:-1], keys[1:], strict=True))):
        progress = f"(({local}-{a.frame / fps:.9f})/{(b.frame - a.frame) / fps:.9f})"
        curve = {
            "ease_in": f"pow({progress},2)",
            "ease_out": f"(1-pow(1-{progress},2))",
            "ease_in_out": f"({progress}*{progress}*(3-2*{progress}))",
        }.get(a.easing, progress)
        value = str(a.value) if a.easing == "hold" else f"({a.value}+({b.value - a.value})*{curve})"
        expression = f"if(lt({local},{b.frame / fps:.9f}),{value},{expression})"
    return f"if(lt({local},{keys[0].frame / fps:.9f}),{keys[0].value},{expression})"


class ContextualFFmpegProvider:
    name = CONTEXTUAL_PROVIDER
    version = "1.2.0"

    def __init__(self, executable: str, timeout_seconds: int, font_path: str | None = None):
        self.executable = executable
        self.timeout_seconds = timeout_seconds
        self.font_path = font_path
        self.font_assets = {}

    def capabilities(self):
        available = bool(shutil.which(self.executable) or Path(self.executable).is_file())
        return {
            "provider": self.name,
            "version": self.version,
            "available": available,
            "capabilities": [{"id": k, "description": v, "status": "implemented"} for k, v in CAPABILITIES.items()],
            "unsupported": ADVANCED,
            "limits": {"maxDimension": 3840, "maxFps": 60, "maxClips": 100, "maxDurationSeconds": 1800},
            "externalApiCostCents": 0,
        }

    def _font(self, size, asset_id=None, text=""):
        if asset_id:
            path = self.font_assets.get(asset_id)
            if path is None:
                raise ValueError("editing_font_asset_missing")
            from fontTools.ttLib import TTFont

            with TTFont(path) as font:
                cmap = font.getBestCmap() or {}
                if any(ord(c) not in cmap for c in text if not c.isspace()):
                    raise ValueError("editing_font_glyph_missing")
            return ImageFont.truetype(str(path), size)
        candidates = [
            self.font_path,
            "C:/Windows/Fonts/arialbd.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]
        for path in candidates:
            if path and Path(path).is_file():
                return ImageFont.truetype(path, size)
        raise ValueError("editing_font_unavailable")

    def validate_text(self, document, assets=None):
        self = copy.copy(self)
        self.font_assets = assets or {}
        page = document.composition.pages[0]
        for layer in page.layers:
            if layer.visible and layer.kind == "text":
                self._layer_text(layer)
        timeline = document.composition.media_timeline
        if timeline:
            for track in timeline.tracks:
                if track.kind == "caption":
                    for cue in track.cues:
                        margin = max(16, page.safe_area)
                        self._text_image(
                            cue.text,
                            page.width - 2 * margin,
                            min(round(page.height * 0.32), page.height - 2 * margin),
                            cue.style.font_size,
                            cue.style.color,
                            outline=cue.style.outline_width,
                            outline_color=cue.style.outline_color,
                            max_lines=cue.style.max_lines,
                            font_asset_id=cue.style.font_asset_id,
                        )

    def _layer_text(self, layer):
        style = ContextualTextStyleV1.model_validate(layer.properties)
        if style.font_family != "Liberation Sans" and not style.font_asset_id:
            raise ValueError("editing_font_asset_required")
        for size in range(style.font_size, style.min_font_size - 1, -1):
            try:
                return self._text_image(
                    style.text,
                    round(layer.width),
                    round(layer.height),
                    size,
                    style.color,
                    style.align,
                    layer.opacity,
                    line_height=style.line_height,
                    font_asset_id=style.font_asset_id,
                )
            except ValueError as error:
                if str(error) not in {"editing_text_overflow", "editing_text_word_overflow"}:
                    raise
        raise ValueError("editing_text_overflow")

    def _text_image(
        self,
        text,
        width,
        height,
        size,
        color,
        align="center",
        opacity=1,
        outline=2,
        max_lines=20,
        outline_color="#000000",
        line_height=1.05,
        font_asset_id=None,
    ):
        image = Image.new("RGBA", (width, height))
        draw = ImageDraw.Draw(image)
        font = self._font(size, font_asset_id, text)
        lines = []
        for paragraph in text.splitlines() or [text]:
            line = ""
            for word in paragraph.split():
                if draw.textlength(word, font=font) > width - 2 * outline:
                    raise ValueError("editing_text_word_overflow")
                candidate = f"{line} {word}".strip()
                if draw.textlength(candidate, font=font) > width - 2 * outline and line:
                    lines.append(line)
                    line = word
                else:
                    line = candidate
            lines.append(line)
        content = "\n".join(lines)
        spacing = max(0, round(size * (line_height - 1)))
        box = draw.multiline_textbbox((0, 0), content, font=font, spacing=spacing, stroke_width=outline)
        if len(lines) > max_lines or box[3] - box[1] > height:
            raise ValueError("editing_text_overflow")
        x = (width - (box[2] - box[0])) / 2 if align == "center" else (width - box[2] if align == "right" else outline)
        draw.multiline_text(
            (x, (height - (box[3] - box[1])) / 2 - box[1]),
            content,
            font=font,
            fill=color,
            spacing=spacing,
            align=align,
            stroke_width=outline,
            stroke_fill=outline_color,
        )
        image.putalpha(image.getchannel("A").point(lambda a: round(a * opacity)))
        return image

    def _run(self, args, cwd, cancelled):
        with tempfile.TemporaryFile() as log:
            process = subprocess.Popen(
                [self.executable, *args],
                cwd=cwd,
                stdout=log,
                stderr=log,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            started = time.monotonic()
            try:
                while process.poll() is None:
                    if cancelled():
                        raise InterruptedError("editing_cancelled")
                    if time.monotonic() - started > self.timeout_seconds:
                        raise TimeoutError("editing_render_timeout")
                    time.sleep(0.1)
                if process.returncode:
                    log.seek(0)
                    raise ValueError("editing_ffmpeg_failed:" + log.read().decode(errors="replace")[-2000:])
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()

    def render(self, document, request, assets, destination, progress, is_cancelled, **kwargs):
        self = copy.copy(self)
        self.font_assets = assets
        if kwargs or inspect_document(document):
            raise ValueError("editing_preflight_required:" + str(inspect_document(document)))
        page = document.composition.pages[0]
        timeline = document.composition.media_timeline
        fps = timeline.frame_rate.numerator / timeline.frame_rate.denominator
        if (request.output.width, request.output.height) != (page.width, page.height) or abs(
            request.output.fps - fps
        ) > 1e-6:
            raise ValueError("editing_output_snapshot_mismatch")
        if (request.output.format, request.output.video_codec, request.output.audio_codec) != ("mp4", "h264", "aac"):
            raise ValueError("editing_output_codec_unsupported")
        started = time.monotonic()
        duration = timeline.duration_frames / fps
        references = {a.id: a for a in document.assets}
        from .media_probe import MEDIA_PROBE_PROVIDERS

        probe = MEDIA_PROBE_PROVIDERS["builtin.ffprobe"]
        probes = {}
        progress(10)
        with tempfile.TemporaryDirectory(prefix="clicko-contextual-") as temporary:
            directory = Path(temporary)
            inputs, graph = [], []
            input_count = 0

            def add_input(path, image=False):
                nonlocal input_count
                n = input_count
                input_count += 1
                if image:
                    inputs.extend(["-loop", "1", "-framerate", str(fps)])
                inputs.extend(["-threads", "2", "-i", str(path)])
                return n

            def media(asset_id):
                path = assets.get(asset_id)
                if not path or not path.is_file():
                    raise ValueError("editing_asset_missing")
                if asset_id not in probes and not references[asset_id].media_type.startswith("image/"):
                    probes[asset_id] = probe.probe(
                        path, asset_id=asset_id, checksum_sha256=references[asset_id].checksum
                    )
                return add_input(path, references[asset_id].media_type.startswith("image/"))

            graph.append(
                f"color=c={page.background.replace('#', '0x')}:s={page.width}x{page.height}:r={fps}:d={duration}[base0]"
            )
            visual_count = 0
            audio = {"speech": [], "music": [], "other": []}
            layers, captions, audio_clips = [], [], []

            def place(label, x, y, start, end):
                nonlocal visual_count
                graph.append(
                    f"[base{visual_count}][{label}]overlay=x='{x}':y='{y}':eof_action=pass:repeatlast=0:"
                    f"enable='gte(t,{start})*lt(t,{end})'[base{visual_count + 1}]"
                )
                visual_count += 1

            for track in timeline.tracks:
                if track.kind not in {"video", "overlay", "audio"} or (track.kind == "audio" and track.muted):
                    continue
                for clip in track.clips:
                    if not clip.enabled:
                        continue
                    n = media(clip.asset_id)
                    transform = ClipTransform.model_validate(clip.transform)
                    effects = [ClipEffect.model_validate(e) for e in clip.effects]
                    start = clip.timeline.start_frame / fps
                    length = clip.timeline.duration_frames / fps
                    source_start = (clip.source.start_microseconds if clip.source else 0) / 1e6
                    source_length = length * clip.playback_rate
                    still = references[clip.asset_id].media_type.startswith("image/")
                    freeze = any(e.kind == "freeze" for e in effects)
                    source_probe = probes.get(clip.asset_id)
                    if source_probe and source_probe.duration_microseconds / 1e6 + 1 / fps < source_start + (
                        1 / fps if freeze else source_length
                    ):
                        raise ValueError("editing_source_out_of_bounds")
                    if track.kind != "audio":
                        width = max(2, round((transform.width or page.width) * transform.scale))
                        height = max(2, round((transform.height or page.height) * transform.scale))
                        chain = (
                            f"[{n}:v]trim=start={source_start}:duration={1 / fps if freeze else source_length},"
                            f"setpts=(PTS-STARTPTS)/{clip.playback_rate},fps={fps}"
                        )
                        if freeze:
                            chain += f",tpad=stop_mode=clone:stop_duration={length}"
                        chain += f",trim=duration={length},settb=AVTB,setsar=1"
                        crop = transform.crop
                        if any([crop.top, crop.bottom, crop.left, crop.right]):
                            chain += (
                                f",crop=iw*{1 - crop.left - crop.right}:ih*{1 - crop.top - crop.bottom}:"
                                f"iw*{crop.left}:ih*{crop.top}"
                            )
                        if transform.fit == "cover":
                            chain += (
                                f",scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}"
                            )
                        else:
                            chain += (
                                f",format=rgba,scale={width}:{height}:force_original_aspect_ratio=decrease,"
                                f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black@0"
                            )
                        for effect in effects:
                            if effect.kind == "color":
                                chain += (
                                    f",exposure=exposure={effect.exposure},eq=contrast={effect.contrast}:"
                                    f"saturation={effect.saturation}"
                                )
                        chain += ",format=rgba"
                        mask = next(
                            (t for t in timeline.tracks if t.kind == "mask" and t.target_track_id == track.id), None
                        )
                        if mask:
                            m = media(mask.artifact_asset_id)
                            graph.append(chain + f",split=2[unmasked{n}][alpha-source{n}]")
                            graph.append(f"[alpha-source{n}]alphaextract,format=gray[original-alpha{n}]")
                            graph.append(
                                f"[{m}:v]scale={width}:{height},format=gray,trim=duration={length},setpts=PTS-STARTPTS[mask{n}]"
                            )
                            graph.append(f"[original-alpha{n}][mask{n}]blend=all_mode=multiply[combined-alpha{n}]")
                            chain = f"[unmasked{n}][combined-alpha{n}]alphamerge"
                        chain += f",colorchannelmixer=aa={transform.opacity}"
                        properties = {MotionTrackV1.model_validate(k).property for k in clip.keyframes}
                        if "opacity" in properties:
                            opacity = motion_expression(clip, "opacity", fps, 1, local_time=True, variable="T")
                            chain += f",geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='alpha(X,Y)*({opacity})'"
                        if properties & {"scale_x", "scale_y"}:
                            sx = motion_expression(clip, "scale_x", fps, 1, local_time=True)
                            sy = motion_expression(clip, "scale_y", fps, 1, local_time=True)
                            chain += (
                                f",scale=w='max(2,round({width}*({sx})))':h='max(2,round({height}*({sy})))':eval=frame"
                            )
                        if "rotation_degrees" in properties:
                            rotation = motion_expression(clip, "rotation_degrees", fps, 0, local_time=True)
                            bound = math.ceil(
                                math.hypot(width, height) * (4 if properties & {"scale_x", "scale_y"} else 1)
                            )
                            chain += f",rotate=angle='({rotation})*PI/180':ow={bound}:oh={bound}:c=none"
                        if transform.rotation:
                            angle = transform.rotation * math.pi / 180
                            chain += f",rotate={angle}:ow=rotw({angle}):oh=roth({angle}):c=none"
                        for effect in effects:
                            if effect.kind == "fade":
                                if effect.in_frames:
                                    chain += f",fade=t=in:st=0:d={effect.in_frames / fps}:alpha=1"
                                if effect.out_frames:
                                    chain += (
                                        f",fade=t=out:st={length - effect.out_frames / fps}:"
                                        f"d={effect.out_frames / fps}:alpha=1"
                                    )
                        graph.append(chain + f",setpts=PTS+{start}/TB[v{n}]")
                        place(
                            f"v{n}",
                            motion_expression(clip, "position_x", fps, transform.x),
                            motion_expression(clip, "position_y", fps, transform.y),
                            start,
                            start + length,
                        )
                        layers.append(clip.id)
                    include_audio = track.kind == "audio" or (
                        transform.original_audio_enabled
                        and not getattr(track, "muted", False)
                        and not still
                        and not freeze
                    )
                    if include_audio and source_probe and source_probe.audio_streams:
                        audio_clips.append(clip.id)
                        role = next(
                            (e.role for e in effects if e.kind == "audio_role"),
                            "dialogue"
                            if (track.kind == "video" or references[clip.asset_id].media_type.startswith("video/"))
                            else "effect",
                        )
                        gain = getattr(clip, "gain_db", 0)
                        chain = (
                            f"[{n}:a]atrim=start={source_start}:duration={source_length},asetpts=PTS-STARTPTS,"
                            + (
                                f"atempo={clip.playback_rate},"
                                if abs(clip.playback_rate - 1) > 1e-9
                                else ""
                            )
                            + f"aresample=48000,aformat=channel_layouts=stereo,volume={gain}dB"
                        )
                        pan = getattr(clip, "pan", 0)
                        if pan:
                            chain += f",pan=stereo|c0={1 - max(0, pan)}*c0|c1={1 + min(0, pan)}*c1"
                        for direction, frames in [
                            ("in", getattr(clip, "fade_in_frames", 0)),
                            ("out", getattr(clip, "fade_out_frames", 0)),
                        ]:
                            if frames:
                                fade_start = 0 if direction == "in" else length - frames / fps
                                chain += f",afade=t={direction}:st={fade_start}:d={frames / fps}"
                        graph.append(
                            chain
                            + f",apad,atrim=duration={length},asetpts=PTS-STARTPTS,"
                            + f"adelay={round(start * 48000)}S:all=1,"
                            + f"apad,atrim=duration={duration}[a{n}]"
                        )
                        audio[
                            "speech" if role in {"dialogue", "narration"} else "music" if role == "music" else "other"
                        ].append(f"a{n}")
                    elif track.kind == "audio":
                        raise ValueError("editing_audio_stream_missing")
            for layer in sorted(page.layers, key=lambda item: item.z_index):
                if not layer.visible:
                    continue
                width, height = round(layer.width), round(layer.height)
                if layer.kind == "text":
                    overlay = self._layer_text(layer)
                else:
                    overlay = Image.new("RGBA", (width, height))
                    ImageDraw.Draw(overlay).rounded_rectangle(
                        (0, 0, width - 1, height - 1),
                        radius=layer.properties.get("radius", 0),
                        fill=layer.properties.get("fill", "#ffffff"),
                    )
                    overlay.putalpha(overlay.getchannel("A").point(lambda a, opacity=layer.opacity: round(a * opacity)))
                path = directory / f"layer{visual_count}.png"
                overlay.save(path)
                n = add_input(path, True)
                graph.append(f"[{n}:v]trim=duration={duration},setpts=PTS-STARTPTS[p{n}]")
                place(f"p{n}", layer.x, layer.y, 0, duration)
                layers.append(layer.id)
            for track in timeline.tracks:
                if track.kind != "caption":
                    continue
                for cue in track.cues:
                    margin = max(16, page.safe_area)
                    width, height = page.width - 2 * margin, min(round(page.height * 0.32), page.height - 2 * margin)
                    overlay = self._text_image(
                        cue.text,
                        width,
                        height,
                        cue.style.font_size,
                        cue.style.color,
                        outline=cue.style.outline_width,
                        outline_color=cue.style.outline_color,
                        max_lines=cue.style.max_lines,
                        font_asset_id=cue.style.font_asset_id,
                    )
                    path = directory / f"caption{visual_count}.png"
                    overlay.save(path)
                    n = add_input(path, True)
                    start, length = cue.timeline.start_frame / fps, cue.timeline.duration_frames / fps
                    graph.append(f"[{n}:v]trim=duration={length},setpts=PTS-STARTPTS+{start}/TB[c{n}]")
                    place(f"c{n}", margin, page.height - margin - height, start, start + length)
                captions.append(track.id)
            mixes = []
            for role, labels in audio.items():
                if labels:
                    graph.append(
                        "".join(f"[{label}]" for label in labels)
                        + f"amix=inputs={len(labels)}:normalize=0:duration=longest[{role}]"
                    )
                    mixes.append(role)
            if "music" in mixes and "speech" in mixes:
                graph.append("[speech]asplit=2[voice][sidechain]")
                graph.append(
                    "[music][sidechain]sidechaincompress=threshold=0.025:ratio=8:attack=20:release=250[ducked]"
                )
                mixes = ["voice", "ducked"] + (["other"] if "other" in mixes else [])
            if mixes:
                graph.append(
                    "".join(f"[{label}]" for label in mixes)
                    + f"amix=inputs={len(mixes)}:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=11,"
                    + f"aresample=48000,apad,atrim=duration={duration}[audio]"
                )
            else:
                graph.append(f"anullsrc=r=48000:cl=stereo,atrim=duration={duration}[audio]")
            graph.append(f"[base{visual_count}]format=yuv420p[video]")
            (directory / "filters.txt").write_text(";\n".join(graph), encoding="utf-8")
            progress(25)
            self._run(
                [
                    "-hide_banner",
                    "-nostdin",
                    "-y",
                    "-filter_complex_threads",
                    "1",
                    *inputs,
                    "-filter_complex_script",
                    "filters.txt",
                    "-map",
                    "[video]",
                    "-map",
                    "[audio]",
                    "-t",
                    str(duration),
                    "-r",
                    str(fps),
                    "-c:v",
                    "libx264",
                    "-threads",
                    "2",
                    "-preset",
                    "veryfast",
                    "-crf",
                    "23",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "192k",
                    "-movflags",
                    "+faststart",
                    str(destination.resolve()),
                ],
                directory,
                is_cancelled,
            )
        progress(80)
        result = probe.probe(destination, asset_id="contextual-output", checksum_sha256=None)
        if not result.video_streams or not result.audio_streams:
            raise ValueError("editing_output_stream_missing")
        stream = result.video_streams[0]
        if (stream.width, stream.height) != (page.width, page.height) or abs(
            result.duration_microseconds / 1e6 - duration
        ) > max(0.1, 2 / fps):
            raise ValueError("editing_output_verification_failed")
        return VideoRenderEncodeResultV1(
            provider=self.name,
            provider_version=self.version,
            width=stream.width,
            height=stream.height,
            duration_ms=round(result.duration_microseconds / 1000),
            fps=fps,
            video_codec=stream.codec,
            audio_codec=result.audio_streams[0].codec,
            render_duration_ms=round((time.monotonic() - started) * 1000),
            frames_rendered=timeline.duration_frames,
            rendered_layer_ids=layers[:100],
            rendered_caption_track_ids=captions,
            rendered_audio_clip_ids=audio_clips,
            warnings=[
                "Editorial quality requires review of the rendered video.",
            ]
            + (
                [f"Raster font: {self._font(16).getname()[0]}."]
                if captions or any(layer.visible and layer.kind == "text" for layer in page.layers)
                else []
            ),
        )
