"""Reference evidence for the native editor, with a local REA-Video adapter."""

from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

from ...config import get_settings
from ...providers.studios.media_runtime import h264_encoder, resolve_tool
from ..object_storage import get_object_storage, sha256_file
from . import craft_references, craft_review, craft_source_media


REA_REVISION = "86486c6e104b917fb4b6a2d6501134686c05b219"
REPOSITORY = f"https://github.com/JuneYaooo/rea-video/tree/{REA_REVISION}"
MAX_REPORT_BYTES = 24 * 1024 * 1024


@contextmanager
def _source(draft, args, workspace_id, db):
    if ("referenceId" in args) == ("assetId" in args):
        raise ValueError("craft_motion_reference_select_one_source")
    if "referenceId" in args:
        item, path = craft_references.temporal_source(args["referenceId"], workspace_id)
        if path is None or item["temporal"]["mediaType"] != "video/mp4":
            raise ValueError("craft_motion_reference_video_required")
        yield path, {"referenceId": item["id"], "checksumSha256": item["temporal"]["sha256"]}
        return
    identifier = args["assetId"]
    if db is not None:
        from .craft import scoped_asset

        record = scoped_asset(db, workspace_id, identifier)
        if not (record.media_type or "").startswith("video/"):
            raise ValueError("craft_motion_reference_video_required")
        with get_object_storage(record.storage_backend).materialize(record.storage_key) as path:
            if sha256_file(path) != record.checksum_sha256:
                raise ValueError("craft_review_source_checksum_mismatch")
            yield path, {"assetId": record.id, "checksumSha256": record.checksum_sha256}
        return
    asset = craft_source_media.source_asset(draft.params["media"], identifier)
    if not asset["mediaType"].startswith("video/"):
        raise ValueError("craft_motion_reference_video_required")
    path = Path(asset["path"])
    if sha256_file(path) != asset["checksumSha256"]:
        raise ValueError("craft_review_source_checksum_mismatch")
    yield path, {"assetId": asset["assetId"], "checksumSha256": asset["checksumSha256"]}


def _analyzer():
    configured = get_settings().studio_craft_rea_video_binary
    if configured:
        return shutil.which(configured)
    root = Path(__file__).resolve().parents[4] / ".codex-runtime/rea-video/venv"
    binary = root / ("Scripts/rea-video.exe" if os.name == "nt" else "bin/rea-video")
    return str(binary) if binary.is_file() else None


def _compact(report):
    shots = report["shots"]
    if not isinstance(shots, list) or not shots:
        raise ValueError("craft_rea_video_report_invalid")
    fields = ("index", "start", "end", "start_frame", "end_frame", "transition_in", "transition", "beats")
    return [{
        **{key: shot[key] for key in fields if key in shot},
        "cameraMeasurement": (shot.get("aspects") or {}).get("camera", {}).get("measured", {}),
        "keyframes": [{k: frame[k] for k in ("t", "frame", "role") if k in frame}
                      for frame in shot.get("keyframes", [])[:8]],
    } for shot in shots[:40]], len(shots)


def analyze(draft, args, workspace_id, *, db=None):
    with _source(draft, args, workspace_id, db) as (path, source):
        return _analyze(draft, args, path, source)


def _analyze(draft, args, path, source):
    start = craft_review._number(args, "startSeconds", 0)
    duration = craft_review._number(args, "durationSeconds", 10, positive=True)
    if duration > 30:
        raise ValueError("craft_motion_reference_duration_limit")
    metadata = craft_review._metadata(path, draft.deadline)
    if not metadata["video"] or start >= metadata["durationSeconds"]:
        raise ValueError("craft_motion_reference_window_invalid")
    duration = min(duration, metadata["durationSeconds"] - start)
    binary = _analyzer()
    if not binary:
        return {**source, "status": "unavailable", "code": "craft_rea_video_not_configured",
                "next": "Use compare_motion_reference to inspect visual evidence directly."}

    folder = Path(draft.directory) / "motion-reference"
    folder.mkdir(exist_ok=True)
    cache_key = hashlib.sha256(json.dumps([source, start, duration, REA_REVISION], sort_keys=True).encode()).hexdigest()
    cached = folder / f"{cache_key}.json"
    if cached.is_file():
        return json.loads(cached.read_text(encoding="utf-8"))

    deadline = min(draft.deadline, time.monotonic() + 180)
    with tempfile.TemporaryDirectory(dir=folder) as scratch:
        work = Path(scratch)
        excerpt = work / "reference.mp4"
        ffmpeg = resolve_tool("ffmpeg")
        craft_review._run([
            ffmpeg, "-v", "error", "-nostdin", "-threads", "1", "-protocol_whitelist", "file,pipe",
            "-ss", str(start), "-i", str(path), "-t", str(duration), "-map", "0:V:0", "-map", "0:a:0?",
            "-vf", "scale=720:720:force_original_aspect_ratio=decrease:force_divisible_by=2",
            "-c:v", h264_encoder(ffmpeg), "-threads", "1", "-c:a", "aac", str(excerpt),
        ], deadline)
        report_dir = work / "analysis"
        # Carry OS executable search paths, but no provider keys or Clicko settings.
        env = {k: os.environ[k] for k in ("PATH", "Path", "SystemRoot", "WINDIR", "TEMP", "TMP", "LD_LIBRARY_PATH",
                                             "HOME", "USERPROFILE", "HOMEDRIVE", "HOMEPATH")
               if k in os.environ}
        env["PATH"] = os.pathsep.join(dict.fromkeys(
            [str(Path(ffmpeg).parent), str(Path(resolve_tool("ffprobe")).parent), os.defpath, env.get("PATH", env.get("Path", ""))]
        ))
        env.update(REA_VIDEO_HOME=str(work / "prefs"), REA_VIDEO_THREADS="2", PYTHONUTF8="1")
        try:
            completed = subprocess.run(
                [binary, "decompose", str(excerpt), "-o", str(report_dir), "--lang", "en",
                 "--no-vlm", "--no-ocr", "--no-stems", "--no-asr"],
                cwd=work, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                timeout=max(0.01, deadline - time.monotonic()),
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except subprocess.TimeoutExpired as exc:
            raise ValueError("craft_rea_video_timeout") from exc
        report_path = report_dir / "breakdown.json"
        if completed.returncode or not report_path.is_file() or report_path.stat().st_size > MAX_REPORT_BYTES:
            raise ValueError("craft_rea_video_report_unavailable")
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
            shots, count = _compact(report)
            excerpt_fps = report["source"]["fps"]
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("craft_rea_video_report_invalid") from exc

    audio = report.get("audio") or {}
    result = {**source, "status": "analyzed", "analyzer": REPOSITORY, "startSeconds": start,
              "hasAudio": bool(audio.get("has_audio")),
              "durationSeconds": duration, "shotCount": count, "shots": shots, "excerptFps": excerpt_fps,
              "interpretation": (
                  "Times and frame indices are relative to the transcoded analysis excerpt. "
                  "Add startSeconds to compare to original source time. Cuts, transitions, and beats are candidates. "
                  "Use original source pixels around important events to verify them. "
                  "No recognition of hidden layers, masks, or source edit parameters. No VLM, OCR, or stem separation."
              )}
    cached.write_text(json.dumps(result), encoding="utf-8")
    return result


def compare(draft, args, workspace_id, *, db=None):
    """Render reference and draft samples at the same relative offsets, at review size."""
    with _source(draft, args, workspace_id, db) as (path, source):
        return _compare(draft, args, path, source)


def _compare(draft, args, path, source):
    from .craft_agent import contact_sheet

    metadata = craft_review._metadata(path, draft.deadline)
    fps = draft.project.get("fps")
    length = (draft.project.get("durationMs") or 0) / 1000
    if not fps or not metadata["video"]:
        raise ValueError("craft_motion_reference_video_timebase_required")
    reference_start = craft_review._number(args, "referenceStartSeconds", 0)
    draft_start = craft_review._number(args, "draftStartSeconds", 0)
    offsets = args.get("offsets", [])
    if (not isinstance(offsets, list) or len(offsets) != 3
            or any(type(value) not in {int, float} or not math.isfinite(value) for value in offsets)
            or not 0 <= offsets[0] < offsets[1] < offsets[2] <= 30):
        raise ValueError("craft_motion_reference_three_ordered_offsets_required")
    if reference_start + offsets[-1] >= metadata["durationSeconds"] or draft_start + offsets[-1] >= length:
        raise ValueError("craft_motion_reference_window_invalid")

    reference_times = [round(reference_start + offset, 6) for offset in offsets]
    draft_frames = [math.floor((draft_start + offset) * fps + 1e-8) for offset in offsets]
    if len(set(draft_frames)) != 3:
        raise ValueError("craft_motion_reference_offsets_collide")
    samples = [(("reference", seconds), f"Reference | {seconds:.3f} s") for seconds in reference_times]
    samples += [(("draft", frame), f"Draft | {frame / fps:.3f} s") for frame in draft_frames]

    def render(sample, output):
        kind, value = sample
        if kind == "reference":
            craft_source_media.still({"path": str(path)}, value, output, draft.deadline)
        else:
            try:
                draft.call("render.frame", outputPath=str(output), frame=value, format="png", maxSide=480)
            except (ValueError, OSError) as exc:
                detail = getattr(exc, "message", str(exc)).casefold()
                if not any(token in detail for token in ("memory", "alloc", "oom")):
                    raise
                draft.call("render.frame", outputPath=str(output), frame=value, format="png", maxSide=300)

    report = {"reference": source, "referenceSeconds": reference_times, "draftFrames": draft_frames,
              "draftFps": fps, "draftBatch": draft.batches, "offsets": offsets,
              "interpretation": "Columns share event offsets. Top row is reference; bottom row is native draft. "
                                "Reference times are requested seek positions. Review motion and audio separately."}
    return [{"type": "text", "text": json.dumps(report)}, *contact_sheet(draft.directory, samples, render)]
