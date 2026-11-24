"""Local, revision-bound temporal review with measured audio and playable excerpts."""

from __future__ import annotations

import base64
import hashlib
import json
import math
import subprocess
import sys
import tempfile
import time
from array import array
from fractions import Fraction
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw

from ...config import get_settings
from ...providers.studios.media_runtime import h264_encoder, resolve_tool
from ..object_storage import sha256_file
from . import craft_source_media

PAGE_SIZE = 12
MAX_PAGE_SIZE = 48
AUDIO_RATE = 16000
AUDIO_WINDOW_SECONDS = 0.02


def _run(arguments, deadline):
    remaining = deadline - time.monotonic()
    if math.isinf(remaining):
        remaining = get_settings().studio_craft_timeout_seconds
    if remaining <= 0:
        raise ValueError("craft_agent_deadline")
    try:
        result = subprocess.run(arguments, capture_output=True, timeout=remaining,
                                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except subprocess.TimeoutExpired as exc:
        raise ValueError("craft_review_timeout") from exc
    if result.returncode:
        raise ValueError("craft_review_media_failed: " + result.stderr.decode(errors="replace")[-700:])
    return result


def _metadata(path, deadline):
    result = _run([resolve_tool("ffprobe"), "-v", "error", "-protocol_whitelist", "file,pipe", "-show_entries",
                   "format=duration:stream=codec_type,width,height,nb_frames,avg_frame_rate,r_frame_rate,duration", "-of", "json", str(path)], deadline)
    info = json.loads(result.stdout)
    streams = info.get("streams", [])
    video = next((item for item in streams if item.get("codec_type") == "video"), None)
    try:
        duration = float((video or {}).get("duration") or info.get("format", {}).get("duration")
                         or max(float(item.get("duration") or 0) for item in streams))
        fps = float(Fraction(video["avg_frame_rate"])) if video else None
    except (ValueError, KeyError, ZeroDivisionError) as exc:
        raise ValueError("craft_review_timebase_unavailable") from exc
    if not math.isfinite(duration) or duration <= 0 or (fps is not None and (not math.isfinite(fps) or fps <= 0)):
        raise ValueError("craft_review_timebase_unavailable")
    return {"durationSeconds": duration, "fps": fps, "video": video,
            "hasAudio": any(item.get("codec_type") == "audio" for item in streams)}


def _number(args, key, default, *, positive=False):
    value = args.get(key, default)
    if type(value) not in {float, int} or not math.isfinite(value) or value < 0 or (positive and value == 0):
        raise ValueError("craft_review_invalid_" + key)
    return float(value)


def _dbfs(value):
    return round(20 * math.log10(max(value, 1e-12)), 2)


def _audio_report(path, output, start, duration, deadline, *, time_origin=0):
    raw = output / "audio.f32"
    _run([resolve_tool("ffmpeg"), "-v", "error", "-nostdin", "-y", "-threads", "1", "-protocol_whitelist", "file,pipe",
          "-ss", str(start), "-i", str(path), "-t", str(duration), "-map", "0:a:0", "-vn", "-ac", "1",
          "-ar", str(AUDIO_RATE), "-c:a", "pcm_f32le", "-f", "f32le", str(raw)], deadline)
    window_samples = round(AUDIO_WINDOW_SECONDS * AUDIO_RATE)
    silent_threshold = 10 ** (-50 / 20)
    waveform_stride = max(1, math.ceil(duration / AUDIO_WINDOW_SECONDS / 128))
    waveform = []
    current_wave_peak = 0.0
    windows = 0
    sample_count = 0
    start += time_origin
    squared_sum = 0.0
    peak = 0.0
    clipped = 0
    silence = []
    silence_start = None
    onsets = []
    onset_count = 0
    previous_level = -120.0
    previous_onset = -1.0
    with raw.open("rb") as handle:
        for payload in iter(lambda: handle.read(window_samples * 4), b""):
            if time.monotonic() >= deadline:
                raise ValueError("craft_agent_deadline")
            samples = array("f")
            samples.frombytes(payload)
            if sys.byteorder != "little":
                samples.byteswap()
            if not samples:
                continue
            energy = sum(value * value for value in samples)
            local_peak = max(abs(value) for value in samples)
            rms = math.sqrt(energy / len(samples))
            elapsed = sample_count / AUDIO_RATE
            level = _dbfs(rms)
            if rms <= silent_threshold and silence_start is None:
                silence_start = elapsed
            if rms > silent_threshold and silence_start is not None:
                if elapsed - silence_start >= 0.1:
                    silence.append({"startSeconds": round(start + silence_start, 4), "endSeconds": round(start + elapsed, 4)})
                silence_start = None
            if level >= -35 and level - previous_level >= 8 and elapsed - previous_onset >= 0.08:
                onset_count += 1
                if len(onsets) < 200:
                    onsets.append({"timeSeconds": round(start + elapsed, 4), "rmsDbfs": level})
                previous_onset = elapsed
            previous_level = level
            sample_count += len(samples)
            squared_sum += energy
            peak = max(peak, local_peak)
            clipped += sum(abs(value) >= 0.999 for value in samples)
            current_wave_peak = max(current_wave_peak, local_peak)
            windows += 1
            if windows % waveform_stride == 0:
                waveform.append(round(current_wave_peak, 5))
                current_wave_peak = 0.0
    measured_duration = sample_count / AUDIO_RATE
    if silence_start is not None and measured_duration - silence_start >= 0.1:
        silence.append({"startSeconds": round(start + silence_start, 4), "endSeconds": round(start + measured_duration, 4)})
    if windows % waveform_stride:
        waveform.append(round(current_wave_peak, 5))
    raw.unlink(missing_ok=True)
    return {
        "status": "measured", "interpretation": "Signal measurements of a mono downmix; no perceptual listening or sound identification.",
        "sampleRateHz": AUDIO_RATE, "windowSeconds": AUDIO_WINDOW_SECONDS, "measuredDurationSeconds": round(measured_duration, 4),
        "rmsDbfs": _dbfs(math.sqrt(squared_sum / max(sample_count, 1))), "peakDbfs": _dbfs(peak),
        "nearClipSampleCount": clipped, "nearClipFraction": round(clipped / max(sample_count, 1), 6),
        "silenceThresholdDbfs": -50, "minimumSilenceSeconds": 0.1, "silenceIntervals": silence[:200],
        "silenceIntervalCount": len(silence), "onsetThresholdRiseDb": 8, "onsetMinimumRmsDbfs": -35,
        "onsetCount": onset_count, "onsets": onsets,
        "eventListTruncated": len(silence) > 200 or onset_count > 200,
        "waveformPeaks": waveform, "waveformBinSeconds": round(waveform_stride * AUDIO_WINDOW_SECONDS, 6),
    }


def _image_block(image):
    buffer = BytesIO()
    image.convert("RGB").save(buffer, "JPEG", quality=86)
    return {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                        "data": base64.b64encode(buffer.getvalue()).decode("ascii")}}


def _detail_frame(path, directory, second, args, deadline):
    """Single high-resolution observation; never treated as temporal coverage."""
    maximum = args.get("maximumSide", 1920)
    if type(maximum) is not int or not 400 <= maximum <= 3840:
        raise ValueError("craft_review_resolution_invalid")
    crop = args.get("crop")
    filters = []
    if crop is not None:
        if (not isinstance(crop, list) or len(crop) != 4
                or any(type(v) not in (float, int) or not math.isfinite(v) for v in crop)):
            raise ValueError("craft_review_crop_invalid")
        x, y, width, height = crop
        if not (0 <= x < 1 and 0 <= y < 1 and 0 < width <= 1 - x and 0 < height <= 1 - y):
            raise ValueError("craft_review_crop_invalid")
        filters.append(f"crop=iw*{width}:ih*{height}:iw*{x}:ih*{y}")
    filters.append(f"scale='min(iw,{maximum})':'min(ih,{maximum})':force_original_aspect_ratio=decrease")
    output = directory / (hashlib.sha256(json.dumps([second, maximum, crop]).encode()).hexdigest() + ".png")
    _run([resolve_tool("ffmpeg"), "-v", "error", "-nostdin", "-y", "-threads", "1",
          "-protocol_whitelist", "file,pipe", "-ss", str(second), "-i", str(path),
          "-map", "0:v:0", "-an", "-frames:v", "1", "-vf", ",".join(filters), str(output)], deadline)
    with Image.open(output) as image:
        return [second], _image_block(image)


def _frames(path, directory, start, duration, fps, page, page_size, total, deadline, *, time_origin=0):
    offset = page * page_size
    count = min(page_size, total - offset)
    sample_start = start + offset / fps
    pattern = directory / "frame-%02d.png"
    _run([resolve_tool("ffmpeg"), "-v", "error", "-nostdin", "-y", "-threads", "1", "-protocol_whitelist", "file,pipe",
          "-ss", str(sample_start), "-i", str(path), "-t", str(max(1 / fps, duration - offset / fps)),
          "-map", "0:v:0", "-an", "-vf", f"fps={fps:.8f},scale=300:400:force_original_aspect_ratio=decrease",
          "-frames:v", str(count), "-threads", "1", "-start_number", "0", str(pattern)], deadline)
    images = sorted(directory.glob("frame-*.png"))[:count]
    if not images:
        raise ValueError("craft_review_no_frames")
    columns = 4 if len(images) <= 12 else 6 if len(images) <= 36 else 8
    canvas = Image.new("RGB", (columns * 310, math.ceil(len(images) / columns) * 430), "#11141a")
    draw = ImageDraw.Draw(canvas)
    seconds = []
    for index, image_path in enumerate(images):
        second = time_origin + sample_start + index / fps
        seconds.append(round(second, 6))
        x, y = index % columns * 310, index // columns * 430
        with Image.open(image_path) as image:
            canvas.paste(image, (x + (310 - image.width) // 2, y + 25))
        draw.text((x + 8, y + 5), f"{offset + index} | {second:.4f} s", fill="white")
    return seconds, _image_block(canvas)


def _excerpt(path, directory, start, duration, has_video, has_audio, deadline):
    output = directory / ("excerpt.mp4" if has_video else "excerpt.wav")
    if output.is_file():
        return output
    args = [resolve_tool("ffmpeg"), "-v", "error", "-nostdin", "-y", "-threads", "1", "-protocol_whitelist", "file,pipe",
            "-ss", str(start), "-i", str(path), "-t", str(duration)]
    if has_video:
        encoder = h264_encoder(resolve_tool("ffmpeg"))
        args += ["-map", "0:v:0", "-map", "0:a:0?", "-c:v", encoder]
        args += ["-preset", "veryfast", "-crf", "20"] if encoder == "libx264" else ["-b:v", "4M"]
        args += ["-c:a", "aac", "-movflags", "+faststart"]
    else:
        args += ["-map", "0:a:0", "-vn", "-c:a", "pcm_s16le"]
    pending = output.with_suffix(".pending" + output.suffix)
    try:
        _run([*args, str(pending)], deadline)
        pending.replace(output)
    finally:
        pending.unlink(missing_ok=True)
    return output


def _overview_frames(path, directory, start, duration, source_fps, page_size, deadline, *, time_origin=0):
    count = min(page_size, max(1, math.ceil(duration * (source_fps or 1))))
    last = max(start, start + duration - 1 / (source_fps or 24))
    times = [start + (last - start) * index / max(1, count - 1) for index in range(count)]
    canvas = Image.new("RGB", (4 * 310, math.ceil(count / 4) * 430), "#11141a")
    draw = ImageDraw.Draw(canvas)
    for index, second in enumerate(times):
        frame = directory / f"overview-{index:02d}.png"
        _run([resolve_tool("ffmpeg"), "-v", "error", "-nostdin", "-y", "-threads", "1",
              "-protocol_whitelist", "file,pipe", "-ss", str(second), "-i", str(path),
              "-map", "0:v:0", "-an", "-frames:v", "1", "-vf", "scale=300:400:force_original_aspect_ratio=decrease",
              "-threads", "1", str(frame)], deadline)
        x, y = index % 4 * 310, index // 4 * 430
        with Image.open(frame) as image:
            canvas.paste(image, (x + (310 - image.width) // 2, y + 25))
        draw.text((x + 8, y + 5), f"{second + time_origin:.4f} s requested", fill="white")
    return [round(second + time_origin, 6) for second in times], _image_block(canvas)


def _draft_metadata(draft, path, *, segmented=False, **render_options):
    """Publish only a validated complete render to the revision-bound review cache."""
    if path.is_file():
        try:
            return _metadata(path, draft.deadline)
        except ValueError as error:
            if not str(error).startswith(('craft_review_media_failed:', 'craft_review_timebase_unavailable')):
                raise
            path.unlink()
    pending = path.with_suffix('.pending.mp4')
    pending.unlink(missing_ok=True)
    try:
        if segmented:
            render_frame_ranges(draft.call, pending, render_options["reviewWindow"], draft.project["fps"],
                                render_options["quality"], draft.deadline)
        else:
            draft.call('render.export', outputPath=str(pending), format='mp4', **render_options)
        if not pending.is_file():
            raise ValueError('craft_review_export_missing')
        metadata = _metadata(pending, draft.deadline)
        pending.replace(path)
        return metadata
    finally:
        pending.unlink(missing_ok=True)


def memory_failure(error):
    message = getattr(error, "message", str(error)).casefold()
    return any(term in message for term in ("memory", "oom", "alloc", "exit 137", "exited 137", "exit code 137"))


def render_frame_ranges(call, output, window, fps, quality, deadline):
    """Bound native memory and join only complete ranges, preserving the frame clock."""
    first, end = window["firstFrame"], window["endFrameExclusive"]
    stride = max(1, int(8 * fps))
    warnings = []
    with tempfile.TemporaryDirectory(dir=output.parent) as temporary:
        folder = Path(temporary)
        segments = []
        has_audio = None
        start = first
        while start < end:
            stop = min(start + stride, end)
            frames = stop - start
            part = folder / "range.mp4"
            try:
                result = call("render.export", outputPath=str(part), format="mp4", quality=quality,
                              reviewWindow={**window, "firstFrame": start, "endFrameExclusive": stop})
            except ValueError as error:
                if frames <= 1 or not memory_failure(error):
                    raise
                stride = max(1, frames // 2)
                part.unlink(missing_ok=True)
                continue
            warnings.extend((result or {}).get("warnings", []))
            info = _metadata(part, deadline)
            if (int((info["video"] or {}).get("nb_frames") or 0) != frames
                    or not math.isclose(info["fps"], fps, rel_tol=1e-6)
                    or (has_audio is not None and info["hasAudio"] != has_audio)):
                raise ValueError("craft_review_render_window_mismatch")
            has_audio = info["hasAudio"]
            name = f"part-{start}.mov"
            audio = ["-an"]
            if has_audio:
                samples = round(stop * 48000 / fps) - round(start * 48000 / fps)
                audio = ["-map", "0:a:0", "-af", f"aresample=48000,apad,atrim=end_sample={samples}",
                         "-c:a", "pcm_s24le"]
            _run([resolve_tool("ffmpeg"), "-v", "error", "-nostdin", "-y", "-i", str(part),
                  "-map", "0:v:0", "-c:v", "copy", *audio, str(folder / name)], deadline)
            segments.extend([f"file {name}", f"duration {frames / fps:.12f}"])
            start = stop
        listing = folder / "segments.txt"
        listing.write_text("\n".join(segments), encoding="ascii")
        pending = folder / "joined.mp4"
        _run([resolve_tool("ffmpeg"), "-v", "error", "-nostdin", "-y", "-f", "concat", "-safe", "1",
              "-i", str(listing), "-map", "0:v:0", "-map", "0:a:0?", "-c:v", "copy", "-c:a", "aac",
              "-b:a", "192k", "-movflags", "+faststart", str(pending)], deadline)
        info = _metadata(pending, deadline)
        if (int(info["video"]["nb_frames"]) != end - first
                or abs(info["durationSeconds"] * fps - (end - first)) > 0.51 or info["hasAudio"] != has_audio):
            raise ValueError("craft_review_render_window_mismatch")
        pending.replace(output)
    return {"warnings": warnings, "frames": end - first, "fps": fps}


def _native_window(draft, args):
    """Resolve the requested interval against the native composition clock."""
    capability = getattr(draft, "capability", {})
    if (draft.engine != "effectcraft" or not capability.get("temporalReview", {}).get("frameRange")):
        return None
    fps = draft.project.get("fps")
    duration = (draft.project.get("durationMs") or 0) / 1000
    if not fps or not duration:
        return None
    start = _number(args, "startSeconds", 0)
    if start >= duration:
        raise ValueError("craft_review_start_out_of_range")
    length = _number(args, "durationSeconds", duration - start, positive=True)
    end = min(start + length, duration)
    if not start and end >= duration and duration <= 8:
        return None
    side = max(draft.project.get("width") or 0, draft.project.get("height") or 0)
    return {
        "firstFrame": math.floor(start * fps + 1e-8),
        "endFrameExclusive": max(math.floor(start * fps + 1e-8) + 1, math.ceil(end * fps - 1e-8)),
        "resolutionDivisor": 2 if side > 1080 else 1,
    }


def _review_render(draft, folder, identity, window):
    if window is None:
        path = folder / f"draft-{identity}.mp4"
        return path, _draft_metadata(draft, path), None
    options = []
    for divisor in (window["resolutionDivisor"], 4):
        settings = {**window, "resolutionDivisor": divisor}
        key = hashlib.sha256(json.dumps(settings, sort_keys=True).encode()).hexdigest()[:16]
        options.append((folder / f"draft-{identity}-{key}.mp4", settings))
    options.sort(key=lambda option: not option[0].is_file())
    for path, settings in options:
        try:
            fps = draft.project["fps"]
            segmented = settings["endFrameExclusive"] - settings["firstFrame"] > 8 * fps
            metadata = _draft_metadata(draft, path, segmented=segmented, reviewWindow=settings, quality="draft")
        except ValueError as error:
            if settings["resolutionDivisor"] == 4 or not memory_failure(error):
                raise
            continue
        fps = draft.project["fps"]
        frame_count = settings["endFrameExclusive"] - settings["firstFrame"]
        if (not metadata["video"] or not math.isclose(metadata["fps"], fps, abs_tol=1e-5)
                or abs(metadata["durationSeconds"] * fps - frame_count) > 0.51):
            path.unlink(missing_ok=True)
            raise ValueError("craft_review_render_window_mismatch")
        return path, metadata, settings


def review_draft(draft, args, *, db=None, workspace_id=None):
    """Inspect one temporal page and return a playable excerpt of the requested interval."""
    folder = Path(draft.directory) / "temporal-review"
    folder.mkdir(exist_ok=True)
    asset = None
    time_origin = 0
    if args.get("assetId"):
        asset = craft_source_media.source_asset(draft.params["media"], args["assetId"])
        path = Path(asset["path"])
        source_checksum = sha256_file(path)
        if source_checksum != asset["checksumSha256"]:
            raise ValueError("craft_review_source_checksum_mismatch")
        source = {"kind": "registered_source", "assetId": asset["assetId"], "checksumSha256": source_checksum}
        metadata = _metadata(path, draft.deadline)
    else:
        if draft.engine not in {"effectcraft", "filmcraft"}:
            raise ValueError("craft_review_video_engine_required")
        native_checksum = sha256_file(Path(draft.params["nativePath"]))
        build = getattr(draft, "capability", {}).get("buildId", "unknown")
        identity = hashlib.sha256(f"{draft.engine}:{build}:{draft.batches}:{native_checksum}".encode()).hexdigest()
        path, metadata, window = _review_render(draft, folder, identity, _native_window(draft, args))
        source = {"kind": "native_draft", "draftBatch": draft.batches, "nativeChecksumSha256": native_checksum,
                  "checksumSha256": sha256_file(path)}
        if window:
            time_origin = window["firstFrame"] / draft.project["fps"]
            source["reviewWindow"] = window
    absolute_start = _number(args, "startSeconds", 0)
    start = max(0, absolute_start - time_origin)
    if start >= metadata["durationSeconds"]:
        raise ValueError("craft_review_start_out_of_range")
    duration = _number(args, "durationSeconds", metadata["durationSeconds"] - start, positive=True)
    duration = min(duration, metadata["durationSeconds"] - start)
    if time_origin and draft.project.get("durationMs"):
        duration = min(duration, draft.project["durationMs"] / 1000 - absolute_start)
    page, page_size = args.get("page", 0), args.get("pageSize", PAGE_SIZE)
    if type(page) is not int or page < 0 or type(page_size) is not int or not 1 <= page_size <= MAX_PAGE_SIZE:
        raise ValueError("craft_review_invalid_page")
    fps = _number(args, "fps", metadata["fps"] or 1, positive=True)
    sampling = args.get("sampling", "native")
    if sampling not in {"native", "overview", "detail"} or (sampling in {"overview", "detail"} and page):
        raise ValueError("craft_review_sampling_invalid")
    if metadata["fps"] and fps > metadata["fps"] + 0.000001:
        raise ValueError("craft_review_fps_exceeds_source")
    total = max(1, math.ceil(duration * fps - 0.000001)) if metadata["video"] else 0
    if (total and page * page_size >= total) or (not total and page):
        raise ValueError("craft_review_page_out_of_range")
    key = hashlib.sha256(json.dumps([source, start, duration], sort_keys=True).encode()).hexdigest()
    interval_dir = folder / key
    interval_dir.mkdir(exist_ok=True)
    audio_file = interval_dir / "audio-report.json"
    if audio_file.is_file():
        audio = json.loads(audio_file.read_text(encoding="utf-8"))
    else:
        audio = (_audio_report(path, interval_dir, start, duration, draft.deadline, time_origin=time_origin) if metadata["hasAudio"]
                 else {"status": "absent", "interpretation": "No audio stream in this source."})
        audio_file.write_text(json.dumps(audio), encoding="utf-8")
    excerpt = _excerpt(path, interval_dir, start, duration, bool(metadata["video"]), metadata["hasAudio"], draft.deadline)
    images = []
    sampled = []
    if total:
        page_dir = interval_dir / f"frames-{fps:g}-{page}-{page_size}"
        page_dir.mkdir(exist_ok=True)
        if sampling == "detail":
            sampled, image = _detail_frame(path, page_dir, start, args, draft.deadline)
            sampled = [round(second + time_origin, 6) for second in sampled]
        elif sampling == "overview":
            sampled, image = _overview_frames(path, page_dir, start, duration, metadata["fps"], page_size, draft.deadline, time_origin=time_origin)
        else:
            sampled, image = _frames(path, page_dir, start, duration, fps, page, page_size, total, draft.deadline, time_origin=time_origin)
        images.append(image)
    transcript = {"status": "unavailable", "reason": "No registered source transcript was supplied for this render."}
    if asset is not None and db is not None and workspace_id is not None:
        transcript = craft_source_media.read_transcript(db, workspace_id, asset, args.get("transcriptOffset", 0), "segment")
    next_page = page + 1 if sampling == "native" and total and (page + 1) * page_size < total else None
    report = {
        "source": source, "draftBatch": draft.batches,
        "interval": {"startSeconds": absolute_start, "endSeconds": round(absolute_start + duration, 6), "durationSeconds": round(duration, 6)},
        "visual": {"status": "ordered_samples" if sampled else "absent", "sourceFps": metadata["fps"],
                   "sampling": sampling, "sampleFps": fps if sampling == "native" else None,
                   "sampledSeconds": sampled, "page": page, "pageSize": page_size, "nextPage": next_page,
                   "totalSamples": total if sampling == "native" else len(sampled),
                   "crop": args.get("crop") if sampling == "detail" else None,
                   "maximumSide": args.get("maximumSide", 1920) if sampling == "detail" else 400,
                   "consecutiveOnRequestedGrid": sampling == "native",
                   "nativeRateRequested": sampling == "native" and bool(metadata["fps"] and abs(fps - metadata["fps"]) < 0.000001)},
        "audio": audio, "transcript": transcript,
        "artifact": {"checksumSha256": sha256_file(excerpt), "mediaType": "video/mp4" if metadata["video"] else "audio/wav"},
        "limitations": ["Visual evidence covers only the ordered frames listed on this page. Request subsequent pages or a denser grid for unresolved motion.",
                        "Audio levels, silence and onsets are measured signals. They do not establish intelligibility, sound identity, musical quality or perceptual synchronization.",
                        "Transcription, when available, describes a registered source; it is not a transcription of the edited mix."],
    }
    blocks = [{"type": "text", "text": json.dumps(report, ensure_ascii=False)}, *images]
    return {"blocks": blocks, "report": report, "path": excerpt}


def review_join(draft, seconds, *, overlay=False):
    project_fps = draft.project.get("fps")
    duration = (draft.project.get("durationMs") or 0) / 1000
    if (type(seconds) not in {float, int} or not math.isfinite(seconds) or not project_fps
            or not 0 < seconds < duration or type(overlay) is not bool):
        raise ValueError("craft_join_out_of_range")
    after = math.floor(seconds * project_fps + 0.5)
    if after < 1 or after / project_fps >= duration:
        raise ValueError("craft_join_needs_two_frames")
    start = max(0, (after - math.ceil(2 * project_fps)) / project_fps)
    end = min(duration, (after + math.ceil(2 * project_fps)) / project_fps)
    review = review_draft(draft, {"startSeconds": start, "durationSeconds": end - start,
                                 "sampling": "overview", "pageSize": 3})
    images = []
    for index in (after - 1, after):
        frame = draft.directory / f"join-{draft.batches}-{index}.png"
        draft.call("render.frame", outputPath=str(frame), frame=index, format="png", maxSide=960)
        with Image.open(frame) as picture:
            images.append(picture.convert("RGB"))
    width, height = images[0].size
    sheet = Image.new("RGB", (width * (3 if overlay else 2), height))
    for column, image in enumerate(images):
        sheet.paste(image, (column * width, 0))
    if overlay:
        sheet.paste(Image.blend(*images, 0.5), (width * 2, 0))
    report = review["report"]
    report["source"].update(kind="edit_join", label="Emenda com mixagem")
    report["join"] = {"requestedSeconds": seconds, "frameBefore": after - 1, "frameAfter": after,
                      "actualSeconds": after / project_fps, "overlay": overlay}
    review["blocks"] = [{"type": "text", "text": json.dumps(report, ensure_ascii=False)}, _image_block(sheet)]
    return review
