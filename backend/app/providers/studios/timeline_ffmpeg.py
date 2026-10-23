"""Clicko-authored compiler for canonical media timelines; no shell/user filters.

Preview and final output use this exact compiler. FFmpeg is an external process,
not copied source or a silent replacement for a native Craft project.
"""

from __future__ import annotations

import json
import math
import subprocess
from fractions import Fraction
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace

from PIL import Image, ImageDraw, ImageFont

from ...config import get_settings
from ...domain.studios.timeline_editor import MotionKey, VisualMotion
from .ffmpeg_utility import FFmpegUtility
from .media_runtime import resolve_tool

ROOT = Path(__file__).resolve().parents[4]
FILTERS = {
    "overlay",
    "scale",
    "pad",
    "trim",
    "atrim",
    "setpts",
    "asetpts",
    "amix",
    "fade",
    "afade",
    "volume",
    "atempo",
    "adelay",
    "geq",
    "rotate",
    "color",
    "format",
    "anullsrc",
    "alimiter",
    "aresample",
    "setsar",
    "fps",
    "colorchannelmixer",
}


def tool(name):
    return resolve_tool(name)


def inspect_tool(executable, *args):
    return subprocess.run(
        [executable, "-hide_banner", *args],
        capture_output=True,
        text=True,
        timeout=15,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        check=True,
    ).stdout


@lru_cache(maxsize=8)
def _capability(ffmpeg, ffprobe):
    version = inspect_tool(ffmpeg, "-version")
    encoders = inspect_tool(ffmpeg, "-encoders")
    filters = inspect_tool(ffmpeg, "-filters")
    help_text = inspect_tool(ffmpeg, "-h", "full")
    missing = sorted(name for name in FILTERS if not any(line.split()[1:2] == [name] for line in filters.splitlines()))
    encoder = next((name for name in ["libopenh264", "libx264"] if name in encoders), None)
    if not encoder or " aac " not in encoders or missing:
        raise ValueError("timeline_codec_or_filter_unavailable")
    probe_version = inspect_tool(ffprobe, "-version").splitlines()[0]
    return {
        "available": True,
        "provider": "ffmpeg.timeline-v1",
        "version": version.splitlines()[0],
        "probeVersion": probe_version,
        "encoder": encoder,
        "gplEnabled": "--enable-gpl" in version,
        "license": "GPL"
        if "--enable-gpl" in version
        else "LGPL-3.0-or-later"
        if "--enable-version3" in version
        else "LGPL-2.1-or-later",
        "filters": sorted(FILTERS),
        "maxDurationSeconds": 600,
        "maxLayers": 32,
        "maxDimension": 1920,
        "maxFrameRate": 60,
        "filterScriptOption": "-filter_complex_script" if "-filter_complex_script" in help_text else "-/filter_complex",
    }


def capability():
    try:
        return _capability(tool("ffmpeg"), tool("ffprobe"))
    except (ValueError, OSError, subprocess.SubprocessError):
        return {"available": False, "provider": "ffmpeg.timeline-v1", "reason": "timeline_runtime_unavailable"}


def probe(path):
    result = subprocess.run(
        [
            tool("ffprobe"),
            "-v",
            "error",
            "-protocol_whitelist",
            "file,pipe",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        timeout=30,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if result.returncode or len(result.stdout) > 1024 * 1024:
        raise ValueError("timeline_media_probe_failed")
    value = json.loads(result.stdout)
    duration = float(value.get("format", {}).get("duration", 0))
    if not math.isfinite(duration) or duration <= 0 or duration > 86400:
        raise ValueError("timeline_media_duration_invalid")
    if value["format"].get("format_name") not in {
        "mov,mp4,m4a,3gp,3g2,mj2",
        "matroska,webm",
        "wav",
        "mp3",
        "ogg",
        "flac",
        "aac",
    }:
        raise ValueError("timeline_media_container_unsupported")
    return value


def num(value):
    return format(float(value), ".8f").rstrip("0").rstrip(".") or "0"


def curve(keys, property, default, fps, clock="t"):
    points = sorted((key.frame / fps, key.value, key.easing) for key in keys if key.property == property)
    if not points:
        return num(default)
    expression = num(points[-1][1])
    for (a, av, _), (b, bv, easing) in reversed(list(zip(points, points[1:], strict=False))):
        progress = f"(({clock}-{num(a)})/{num(b - a)})"
        if easing == "ease-in-out":
            progress = f"({progress}*{progress}*(3-2*{progress}))"
        elif easing == "ease-out":
            progress = f"(1-pow(1-{progress},3))"
        segment = f"{num(av)}+({num(bv - av)})*{progress}"
        expression = f"if(lt({clock},{num(b)}),{segment},{expression})"
    return f"if(lt({clock},{num(points[0][0])}),{num(points[0][1])},{expression})"


def title_png(cue, width, height, destination):
    # User text is rasterized, never interpolated into a filter/shell expression.
    font_paths = (
        [Path("C:/Windows/Fonts/segoeuib.ttf"), Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")]
        if cue.style.font_family == "system"
        else [
            Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"),
            Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
        ]
    )
    font_path = next((p for p in font_paths if p.is_file()), None)
    if font_path is None:
        raise ValueError("timeline_title_font_unavailable")
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(str(font_path), cue.style.font_size)
    words = cue.text.split()
    lines, line = [], ""
    for word in words:
        candidate = (line + " " + word).strip()
        if draw.textbbox((0, 0), candidate, font=font)[2] > width * 0.86:
            if not line:
                raise ValueError("timeline_title_does_not_fit")
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    if (
        not lines
        or len(lines) > cue.style.max_lines
        or any(draw.textbbox((0, 0), text, font=font)[2] > width * 0.86 for text in lines)
    ):
        raise ValueError("timeline_title_does_not_fit")
    step = cue.style.font_size * 1.3
    y = height * 0.8 - len(lines) * step / 2
    motion = VisualMotion.model_validate(cue.motion)
    if motion.background_color:
        from PIL import ImageColor

        text_width = max(draw.textbbox((0, 0), text, font=font)[2] for text in lines)
        draw.rounded_rectangle(
            (
                max(0, (width - text_width) / 2 - 12),
                max(0, y - 8),
                min(width, (width + text_width) / 2 + 12),
                min(height, y + len(lines) * step + 8),
            ),
            radius=8,
            fill=(*ImageColor.getrgb(motion.background_color), 210),
        )
    for text in lines:
        draw.text(
            (width / 2, y),
            text,
            font=font,
            anchor="mt",
            fill=cue.style.color,
            stroke_width=cue.style.outline_width,
            stroke_fill=cue.style.outline_color,
        )
        y += step
    image.save(destination)


def compile_plan(contract, paths, directory, media_info):
    timeline = contract.composition.media_timeline
    fps = timeline.frame_rate.numerator / timeline.frame_rate.denominator
    rate_value = f"{timeline.frame_rate.numerator}/{timeline.frame_rate.denominator}"
    duration = timeline.duration_frames / fps
    page = contract.composition.pages[0]
    width, height = page.width, page.height
    args = ["-hide_banner", "-loglevel", "error", "-nostdin", "-y", "-filter_complex_threads", "1"]
    filters = [
        f"color=c=0x{page.background[1:]}:s={width}x{height}:r={rate_value}:d={num(duration)},format=rgba[base]",
        f"anullsrc=r=48000:cl=stereo,atrim=duration={num(duration)}[silence]",
    ]
    current, audio, count = "base", ["silence"], 0

    def input_file(path, image=False, source_start=0, source_duration=None):
        nonlocal count
        index = count
        count += 1
        args.extend(["-protocol_whitelist", "file,pipe"])
        if not image:
            args.extend(["-ss", num(source_start)])
            if source_duration:
                args.extend(["-t", num(source_duration)])
        if image:
            args.extend(["-loop", "1", "-framerate", num(fps)])
        args.extend(["-threads", "1", "-i", str(path)])
        return index

    def audio_clip(index, clip, track, index_name, motion):
        if getattr(track, "muted", False):
            return
        start, length = clip.timeline.start_frame / fps, clip.timeline.duration_frames / fps
        source_start = 0  # Each materialized input is already accurately seeked.
        rate = clip.playback_rate
        gain = getattr(clip, "gain_db", motion.gain_db)
        fade_in = getattr(clip, "fade_in_frames", motion.fade_in_frames) / fps
        fade_out = getattr(clip, "fade_out_frames", motion.fade_out_frames) / fps
        chain = (
            f"[{index}:a]atrim=start={num(source_start)}:duration={num(length * rate)},"
            f"asetpts=PTS-STARTPTS,atempo={num(rate)},aresample=48000,volume={num(gain)}dB"
        )
        if fade_in:
            chain += f",afade=t=in:d={num(fade_in)}"
        if fade_out:
            chain += f",afade=t=out:st={num(max(0, length - fade_out))}:d={num(fade_out)}"
        chain += f",adelay={round(start * 48000)}S:all=1[{index_name}]"
        filters.append(chain)
        audio.append(index_name)

    from ...domain.studios.local_composition import LocalLayerStyle
    from .local_composition import raster, text_layout

    # Canonical editable layers join the same compiler, after the media tracks.
    # They remain text/shapes/assets in the saved project, never flattened MP4s.
    local_items = []
    for layer in sorted(page.layers, key=lambda layer: layer.z_index):
        if not layer.visible:
            continue
        style = LocalLayerStyle.model_validate(layer.properties)
        path = directory / f"layer-{len(local_items)}.png"
        raster(layer, paths).save(path)
        local_items.append(SimpleNamespace(
            enabled=True, local_layer=layer, path=path,
            source=None, playback_rate=1, keyframes=[key.model_dump() for key in style.keyframes],
            timeline=SimpleNamespace(start_frame=style.start_frame,
                                     duration_frames=style.duration_frames or timeline.duration_frames),
            transform={"x": layer.x + layer.width / 2 - width / 2,
                       "y": layer.y + layer.height / 2 - height / 2,
                       "rotation": layer.rotation, "opacity": layer.opacity},
        ))
    tracks = [*timeline.tracks, SimpleNamespace(kind="local", clips=local_items)]
    for track in tracks:
        if track.kind == "marker":
            continue
        items = track.cues if track.kind == "caption" else track.clips
        for item in items:
            if not getattr(item, "enabled", True):
                continue
            is_title = track.kind == "caption"
            is_local = track.kind == "local"
            motion = VisualMotion.model_validate(item.motion if is_title else item.transform)
            keys = [MotionKey.model_validate(key) for key in item.keyframes]
            start, length = item.timeline.start_frame / fps, item.timeline.duration_frames / fps
            if is_local:
                path, image = item.path, True
            elif is_title:
                path = directory / f"title-{count}.png"
                title_png(item, width, height, path)
                image = True
            else:
                path = paths[item.asset_id]
                image = item.asset_id not in media_info
            source_start = 0 if is_title or not item.source else item.source.start_microseconds / 1e6
            rate = 1 if is_title else item.playback_rate
            index = input_file(path, image, source_start, length * rate)
            if track.kind == "audio":
                audio_clip(index, item, track, f"a{index}", motion)
                continue
            if (
                not is_title and not is_local
                and not image
                and motion.original_audio_enabled
                and any(s["codec_type"] == "audio" for s in media_info[item.asset_id]["streams"])
            ):
                audio_clip(index, item, track, f"a{index}", motion)
            source_start = 0
            fit = (
                f"scale={max(2, round(item.local_layer.width))}:{max(2, round(item.local_layer.height))},"
                if is_local else
                f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black@0,"
            )
            chain = (
                f"[{index}:v]trim=start={num(source_start)}:duration={num(length * rate)},"
                f"setpts=(PTS-STARTPTS)/{num(rate)},fps={rate_value},"
                f"{fit}setsar=1,format=rgba"
            )
            if is_local:
                style = LocalLayerStyle.model_validate(item.local_layer.properties)
                if style.text_reveal == "words":
                    # Mask in source coordinates before scale/rotation. Each word keeps
                    # its full-layout position; saved text remains a single editable layer.
                    _face, runs = text_layout(item.local_layer, style)
                    regions = [
                        f"gte(T,{num(i * style.word_stagger_frames / fps)})*"
                        f"between(X,{num(max(0, x - 1))},{num(x + w + 1)})*"
                        f"between(Y,{num(y)},{num(y + style.font_size * 1.3)})"
                        for i, (_word, x, y, w) in enumerate(runs)
                    ]
                    mask = "min(1," + "+".join(regions) + ")"
                    chain += f",geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='alpha(X,Y)*({mask})'"
            scale = curve(keys, "scale", motion.scale, fps)
            chain += f",scale=w='max(2,trunc(iw*({scale})/2)*2)':h='max(2,trunc(ih*({scale})/2)*2)':eval=frame"
            if any(key.property == "rotation" for key in keys):
                angle = curve(keys, "rotation", motion.rotation, fps)
                chain += f",rotate='({angle})*PI/180':c=none:ow=hypot(iw\,ih):oh=hypot(iw\,ih)"
            elif motion.rotation:
                angle = num(motion.rotation * math.pi / 180)
                chain += f",rotate={angle}:c=none:ow=rotw({angle}):oh=roth({angle})"
            alpha = curve(keys, "opacity", motion.opacity, fps, "T")
            if keys and any(k.property == "opacity" for k in keys):
                chain += f",geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='alpha(X,Y)*({alpha})'"
            elif motion.opacity != 1:
                chain += f",colorchannelmixer=aa={num(motion.opacity)}"
            if motion.fade_in_frames:
                chain += f",fade=t=in:d={num(motion.fade_in_frames / fps)}:alpha=1"
            if motion.fade_out_frames:
                chain += (
                    f",fade=t=out:st={num(max(0, length - motion.fade_out_frames / fps))}:"
                    f"d={num(motion.fade_out_frames / fps)}:alpha=1"
                )
            filters.append(chain + f",setpts=PTS+{num(start)}/TB[v{index}]")
            x = curve(keys, "x", 0 if is_local else motion.x, fps, f"(t-{num(start)})")
            y = curve(keys, "y", 0 if is_local else motion.y, fps, f"(t-{num(start)})")
            if is_local:
                x, y = f"{num(motion.x)}+({x})", f"{num(motion.y)}+({y})"
            filters.append(
                f"[{current}][v{index}]overlay=x='(W-w)/2+({x})':y='(H-h)/2+({y})':"
                f"enable='gte(t,{num(start)})*lt(t,{num(start + length)})':"
                f"eof_action=pass:repeatlast=0[out{index}]"
            )
            current = f"out{index}"
    filters.append(f"[{current}]format=yuv420p[video]")
    filters.append(
        "".join(f"[{label}]" for label in audio)
        + f"amix=inputs={len(audio)}:duration=longest:normalize=0,alimiter=limit=0.95,"
        f"atrim=duration={num(duration)}[audio]"
    )
    script = directory / "timeline.filter"
    script.write_text(";\n".join(filters), encoding="utf-8")
    encoder = capability()["encoder"]
    output = directory / "output.mp4"
    args.extend(
        [
            capability()["filterScriptOption"],
            str(script),
            "-map",
            "[video]",
            "-map",
            "[audio]",
            "-t",
            num(duration),
            "-r",
            rate_value,
            "-c:v",
            encoder,
            "-b:v",
            "6M",
            "-pix_fmt",
            "yuv420p",
            "-threads",
            "2",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            "-map_metadata",
            "-1",
            str(output),
        ]
    )
    return args, output


def render(contract, paths, directory, media_info, cancelled):
    if not capability()["available"]:
        raise ValueError("timeline_runtime_unavailable")
    args, output = compile_plan(contract, paths, directory, media_info)
    FFmpegUtility(tool("ffmpeg"), get_settings().ffmpeg_timeout_seconds)._run(args, directory, cancelled)
    result = probe(output)
    video = next((s for s in result["streams"] if s["codec_type"] == "video"), None)
    audio = next((s for s in result["streams"] if s["codec_type"] == "audio"), None)
    page = contract.composition.pages[0]
    timeline = contract.composition.media_timeline
    fps = timeline.frame_rate.numerator / timeline.frame_rate.denominator
    if (
        not video
        or video["codec_name"] != "h264"
        or video["width"] != page.width
        or video["height"] != page.height
        or abs(float(Fraction(video.get("avg_frame_rate", "0/1"))) - fps) > 1e-6
        or not audio
        or audio["codec_name"] != "aac"
        or abs(float(result["format"]["duration"]) - timeline.duration_frames / fps) > max(0.1, 2 / fps)
    ):
        raise ValueError("timeline_output_validation_failed")
    if cancelled():
        raise InterruptedError("timeline_cancelled")
    return output, {
        "durationSeconds": float(result["format"]["duration"]),
        "width": page.width,
        "height": page.height,
        "videoCodec": video["codec_name"],
        "audioCodec": audio["codec_name"],
        "frameRate": fps,
    }
