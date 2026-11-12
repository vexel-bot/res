"""Independent technical checks against a real local render of an editorial proposal."""

from array import array
from collections import Counter
from contextlib import contextmanager
import math
import subprocess

from ...domain.studios.local_composition import LocalLayerStyle
from ...providers.studios import timeline_ffmpeg as renderer
from ...providers.studios.ffmpeg_utility import FFmpegUtility
from ..object_storage import sha256_file
from . import motion_editorial, timeline_editor
from .craft import scoped_asset, workspace_files, write_asset

MAX_PREVIEW_SECONDS = 30
MAX_PREVIEW_PIXELS = 1280 * 1280
MAX_PREVIEW_BYTES = 100 * 1024**2
SAMPLE_BYTES = 96 * 54 * 3


def _samples(total, beats):
    points = {round((total-1) * fraction) for fraction in (.08, .23, .41, .59, .76, .92)}
    for beat in beats[:10]:
        points.add((beat["startFrame"] + beat["endFrame"] - 1) // 2)
    return sorted(n for n in points if 0 <= n < total)


def _raw(path, args):
    try:
        return subprocess.run(
            [renderer.tool("ffmpeg"), "-nostdin", "-v", "error", "-threads", "1", "-protocol_whitelist", "file,pipe",
             "-i", str(path), *args, "pipe:1"],
            capture_output=True, timeout=25, check=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        ).stdout
    except subprocess.SubprocessError as error:
        raise ValueError("editorial_preview_decode_failed") from error


def _visible_source(comp, frame):
    for track in comp.media_timeline.tracks:
        if track.kind not in {"video", "overlay", "caption"}:
            continue
        for item in getattr(track, "clips", None) or getattr(track, "cues", []):
            bounds = item.timeline
            if getattr(item, "enabled", True) and bounds.start_frame <= frame < bounds.start_frame+bounds.duration_frames:
                return True
    for layer in comp.pages[0].layers:
        if not layer.visible or layer.kind not in {"text", "image"}:
            continue
        style = LocalLayerStyle.model_validate(layer.properties)
        if style.start_frame <= frame < style.start_frame + (style.duration_frames or comp.media_timeline.duration_frames):
            return True
    return False


def caption_findings(contract):
    """Static title size is measurable; video contrast and timing still need playback."""
    from ...domain.studios.timeline_editor import VisualMotion

    page = contract.composition.pages[0]
    findings = []
    for track in contract.composition.media_timeline.tracks:
        if track.kind != "caption":
            continue
        for cue in track.cues:
            motion = VisualMotion.model_validate(cue.motion)
            if cue.style.font_size * motion.scale * min(1, 360/page.width) < 14:
                findings.append({"code": "caption_below_phone_floor", "cueId": cue.id,
                                 "frame": cue.timeline.start_frame})
    return findings


def analyze_preview(contract, output, receipt):
    timeline = contract.composition.media_timeline
    fps = timeline.frame_rate.numerator / timeline.frame_rate.denominator
    beats = next((item["beats"] for item in receipt["receipts"] if item["stage"] == "direction"), [])
    frames = set(_samples(timeline.duration_frames, beats))
    for track in timeline.tracks:
        if track.kind == "video":
            for clip in track.clips:
                if clip.enabled:
                    end = clip.timeline.start_frame + clip.timeline.duration_frames
                    frames.update(frame for frame in (clip.timeline.start_frame, end-1, end)
                                  if 0 <= frame < timeline.duration_frames)
    frames = sorted(frames)
    selector = "+".join(f"eq(n,{frame})" for frame in frames)
    pixels = _raw(output, ["-an", "-vf", f"select='{selector}',scale=96:54", "-fps_mode", "passthrough",
                           "-c:v", "rawvideo", "-threads", "1", "-pix_fmt", "rgb24", "-f", "rawvideo"])
    if len(pixels) != SAMPLE_BYTES * len(frames):
        raise ValueError("editorial_preview_samples_incomplete")
    findings = motion_editorial._text_legibility(contract.composition) + caption_findings(contract)
    observations = []
    for i, frame in enumerate(frames):
        rgb = pixels[i*SAMPLE_BYTES:(i+1)*SAMPLE_BYTES]
        # Bucket colors so the detector ignores codec noise in an empty card.
        color_counts = Counter((r//12, g//12, b//12) for r,g,b in zip(rgb[::3], rgb[1::3], rgb[2::3], strict=True))
        dominant = max(color_counts.values()) / (SAMPLE_BYTES//3)
        has_content = _visible_source(contract.composition, frame)
        sample = {"frame": frame, "timeMs": round(frame*1000/fps), "dominantColorFraction": round(dominant, 4),
                  "hasPlannedSource": has_content}
        observations.append(sample)
        if not has_content or dominant >= .995:
            findings.append({"code": "empty_or_near_uniform_frame", **sample})
    pcm = array("h", _raw(output, ["-vn", "-ac", "1", "-ar", "8000", "-f", "s16le"]))
    if pcm:
        peak = max(abs(value) for value in pcm) / 32768
        rms = math.sqrt(sum(value*value for value in pcm) / len(pcm)) / 32768
    else:
        peak = rms = 0
    expected_audio = any(t.kind == "audio" and not t.muted and any(c.enabled for c in t.clips) for t in timeline.tracks)
    if expected_audio and rms < .001:
        findings.append({"code": "expected_audio_missing"})
    return {"status": "blocked" if findings else "passed_technical", "sampledFrames": observations,
            "findings": findings, "audio": {"expected": expected_audio, "peak": round(peak, 4), "rms": round(rms, 5)},
            "scope": "Sampled technical evidence; continuity, intelligibility and comprehension require review."}


@contextmanager
def render_and_review(db, record, contract, receipt, cancelled):
    timeline = contract.composition.media_timeline
    page = contract.composition.pages[0]
    seconds = timeline.duration_frames * timeline.frame_rate.denominator / timeline.frame_rate.numerator
    if seconds > MAX_PREVIEW_SECONDS or page.width * page.height > MAX_PREVIEW_PIXELS:
        yield {"status": "inconclusive", "findings": [{"code": "editorial_preview_exceeds_local_budget"}]}, None
        return
    refs = timeline_editor.validate(contract, require_content=True)
    if sum(scoped_asset(db, record.workspace_id, identifier).size_bytes or 0 for identifier in refs) > MAX_PREVIEW_BYTES:
        yield {"status": "inconclusive", "findings": [{"code": "editorial_preview_source_size_limit"}]}, None
        return
    with workspace_files(db, record, None, extra_asset_ids=refs) as (directory, params, _):
        paths = {item["assetId"]: item["path"] for item in params["media"]}
        info = {item["assetId"]: renderer.probe(item["path"]) for item in params["media"]
                if not item["mediaType"].startswith("image/")}
        args, output = renderer.compile_plan(contract, paths, directory, info)
        FFmpegUtility(renderer.tool("ffmpeg"), 45)._run(args, directory, cancelled)
        check = renderer.probe(output)
        video = next((stream for stream in check["streams"] if stream["codec_type"] == "video"), None)
        if not video or video.get("width") != page.width or video.get("height") != page.height:
            raise ValueError("editorial_preview_format_mismatch")
        if abs(float(check["format"]["duration"]) - seconds) > .15:
            raise ValueError("editorial_preview_duration_mismatch")
        reviewed = analyze_preview(contract, output, receipt)
        yield {**reviewed, "renderChecksum": sha256_file(output), "durationSeconds": seconds,
               "width": page.width, "height": page.height, "renderer": "ffmpeg.timeline-v1"}, output


def persist_preview(db, record, job, evidence, output, staged):
    if output is None:
        return
    asset, storage, key = write_asset(
        db, record, output, suffix=".mp4", media_type="video/mp4", asset_type="video",
        title=f"{record.title} · prévia editorial",
        metadata={"editorialPreview": True, "editorialTaskId": job.id, "documentRevision": record.revision},
    )
    staged.append((storage, key))
    if asset.checksum_sha256 != evidence["renderChecksum"]:
        raise ValueError("editorial_preview_checksum_mismatch")
    evidence.update(assetId=asset.id, downloadUrl=f"/api/v1/assets/{asset.id}/content",
                    mediaType="video/mp4", sizeBytes=asset.size_bytes)
