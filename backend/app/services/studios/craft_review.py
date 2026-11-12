"""Local, revision-bound temporal review with measured audio and playable excerpts."""

from __future__ import annotations

import base64
import hashlib
import json
import math
import subprocess
import sys
import time
from array import array
from fractions import Fraction
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw

from ...providers.studios.media_runtime import h264_encoder, resolve_tool
from ..object_storage import sha256_file
from . import craft_source_media

PAGE_SIZE = 12
AUDIO_RATE = 16000
AUDIO_WINDOW_SECONDS = 0.02


def _run(arguments, deadline):
    remaining = deadline - time.monotonic()
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
                   "format=duration:stream=codec_type,width,height,avg_frame_rate,r_frame_rate,duration", "-of", "json", str(path)], deadline)
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


def _audio_report(path, output, start, duration, deadline):
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


def _frames(path, directory, start, duration, fps, page, page_size, total, deadline):
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
    canvas = Image.new("RGB", (4 * 310, math.ceil(len(images) / 4) * 430), "#11141a")
    draw = ImageDraw.Draw(canvas)
    seconds = []
    for index, image_path in enumerate(images):
        second = sample_start + index / fps
        seconds.append(round(second, 6))
        x, y = index % 4 * 310, index // 4 * 430
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
    _run([*args, str(output)], deadline)
    return output


def review_draft(draft, args, *, db=None, workspace_id=None):
    """Inspect one temporal page and return a playable excerpt of the requested interval."""
    folder = Path(draft.directory) / "temporal-review"
    folder.mkdir(exist_ok=True)
    asset = None
    if args.get("assetId"):
        asset = craft_source_media.source_asset(draft.params["media"], args["assetId"])
        path = Path(asset["path"])
        source_checksum = sha256_file(path)
        if source_checksum != asset["checksumSha256"]:
            raise ValueError("craft_review_source_checksum_mismatch")
        source = {"kind": "registered_source", "assetId": asset["assetId"], "checksumSha256": source_checksum}
    else:
        if draft.engine not in {"effectcraft", "filmcraft"}:
            raise ValueError("craft_review_video_engine_required")
        native_checksum = sha256_file(Path(draft.params["nativePath"]))
        identity = hashlib.sha256(f"{draft.engine}:{draft.batches}:{native_checksum}".encode()).hexdigest()
        path = folder / f"draft-{identity}.mp4"
        if not path.is_file():
            draft.call("render.export", outputPath=str(path), format="mp4")
        if not path.is_file():
            raise ValueError("craft_review_export_missing")
        source = {"kind": "native_draft", "draftBatch": draft.batches, "nativeChecksumSha256": native_checksum,
                  "checksumSha256": sha256_file(path)}
    metadata = _metadata(path, draft.deadline)
    start = _number(args, "startSeconds", 0)
    if start >= metadata["durationSeconds"]:
        raise ValueError("craft_review_start_out_of_range")
    duration = _number(args, "durationSeconds", metadata["durationSeconds"] - start, positive=True)
    duration = min(duration, metadata["durationSeconds"] - start)
    page, page_size = args.get("page", 0), args.get("pageSize", PAGE_SIZE)
    if type(page) is not int or page < 0 or type(page_size) is not int or not 1 <= page_size <= PAGE_SIZE:
        raise ValueError("craft_review_invalid_page")
    fps = _number(args, "fps", metadata["fps"] or 1, positive=True)
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
        audio = (_audio_report(path, interval_dir, start, duration, draft.deadline) if metadata["hasAudio"]
                 else {"status": "absent", "interpretation": "No audio stream in this source."})
        audio_file.write_text(json.dumps(audio), encoding="utf-8")
    excerpt = _excerpt(path, interval_dir, start, duration, bool(metadata["video"]), metadata["hasAudio"], draft.deadline)
    images = []
    sampled = []
    if total:
        page_dir = interval_dir / f"frames-{fps:g}-{page}-{page_size}"
        page_dir.mkdir(exist_ok=True)
        sampled, image = _frames(path, page_dir, start, duration, fps, page, page_size, total, draft.deadline)
        images.append(image)
    transcript = {"status": "unavailable", "reason": "No registered source transcript was supplied for this render."}
    if asset is not None and db is not None and workspace_id is not None:
        transcript = craft_source_media.read_transcript(db, workspace_id, asset, args.get("transcriptOffset", 0), "segment")
    next_page = page + 1 if total and (page + 1) * page_size < total else None
    report = {
        "source": source, "draftBatch": draft.batches,
        "interval": {"startSeconds": start, "endSeconds": round(start + duration, 6), "durationSeconds": round(duration, 6)},
        "visual": {"status": "ordered_samples" if sampled else "absent", "sourceFps": metadata["fps"], "sampleFps": fps,
                   "sampledSeconds": sampled, "page": page, "pageSize": page_size, "nextPage": next_page,
                   "totalSamples": total, "consecutiveOnRequestedGrid": True,
                   "nativeRateRequested": bool(metadata["fps"] and abs(fps - metadata["fps"]) < 0.000001)},
        "audio": audio, "transcript": transcript,
        "artifact": {"checksumSha256": sha256_file(excerpt), "mediaType": "video/mp4" if metadata["video"] else "audio/wav"},
        "limitations": ["Visual evidence covers only the ordered frames listed on this page. Request subsequent pages or a denser grid for unresolved motion.",
                        "Audio levels, silence and onsets are measured signals. They do not establish intelligibility, sound identity, musical quality or perceptual synchronization.",
                        "Transcription, when available, describes a registered source; it is not a transcription of the edited mix."],
    }
    blocks = [{"type": "text", "text": json.dumps(report, ensure_ascii=False)}, *images]
    return {"blocks": blocks, "report": report, "path": excerpt}
