"""Read the registered source media available to a native Craft draft."""

import math
import re
import subprocess
import time
from pathlib import Path

from sqlalchemy import and_, or_, select

from ...config import get_settings
from ...models import StudioMediaIngest, StudioTranscript
from ...providers.studios.media_probe import FFprobeMediaProbeProvider
from ...providers.studios.media_runtime import resolve_tool
from .transcripts import transcript_out


def source_asset(media, asset_id):
    asset = next((item for item in media if item["assetId"] == asset_id), None)
    if not asset or not asset["mediaType"].startswith(("video/", "audio/")):
        raise ValueError("craft_registered_audio_or_video_required")
    return asset


def seconds_left(deadline):
    seconds = deadline - time.monotonic()
    if seconds <= 0:
        raise ValueError("craft_agent_deadline")
    return min(seconds, 15)


def probe(asset, deadline):
    provider = FFprobeMediaProbeProvider(get_settings().ffprobe_path, seconds_left(deadline))
    try:
        return provider.probe(Path(asset["path"]), asset_id=asset["assetId"], checksum_sha256=asset["checksumSha256"])
    except subprocess.TimeoutExpired:
        raise ValueError("craft_source_probe_timeout") from None


def still(asset, second, output, deadline):
    try:
        result = subprocess.run(
            [resolve_tool("ffmpeg"), "-v", "error", "-nostdin", "-y", "-protocol_whitelist", "file,pipe",
             "-ss", f"{second:.6f}", "-i", asset["path"], "-map", "0:V:0", "-frames:v", "1",
             "-vf", "scale=512:512:force_original_aspect_ratio=decrease", str(output)],
            capture_output=True, timeout=seconds_left(deadline),
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except subprocess.TimeoutExpired:
        raise ValueError("craft_source_frame_timeout") from None
    if result.returncode or not output.is_file():
        raise ValueError(f"No video frame was decoded at source time {second:g} seconds.")


def shot_candidates(asset, media_duration, deadline, *, start=0, duration=30):
    """Find visual discontinuities in a bounded window of a verified source."""
    if (type(start) not in (int, float) or type(duration) not in (int, float)
            or not math.isfinite(start) or not math.isfinite(duration)
            or not 0 <= start < media_duration or not 0 < duration <= 30):
        raise ValueError("craft_shot_window_invalid")
    end = min(media_duration, start + duration)
    try:
        result = subprocess.run(
            [resolve_tool("ffmpeg"), "-v", "error", "-nostdin", "-threads", "1", "-filter_threads", "1",
             "-protocol_whitelist", "file,pipe", "-ss", str(start), "-t", str(end - start), "-i", asset["path"],
             "-map", "0:V:0", "-an", "-sn", "-dn", "-vf",
             "scale=192:-2,select='gt(scene,0.32)',metadata=mode=print:file=-", "-f", "null", "-"],
            capture_output=True, text=True, timeout=seconds_left(deadline),
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except subprocess.TimeoutExpired:
        raise ValueError("craft_shot_scan_timeout") from None
    if result.returncode:
        raise ValueError("craft_shot_scan_failed")
    candidates = []
    for match in re.finditer(r"pts_time:([\d.eE+-]+)\s*\n\s*lavfi\.scene_score=([\d.eE+-]+)", result.stdout):
        second, score = float(match[1]) + start, float(match[2])
        if start < second < end:
            candidates.append({"second": round(second, 6), "score": round(score, 6)})
    return {"assetId": asset["assetId"], "checksumSha256": asset["checksumSha256"],
            "startSeconds": start, "endSeconds": end, "nextStartSeconds": end if end < media_duration else None,
            "candidateCount": len(candidates), "candidates": candidates[:48], "truncated": len(candidates) > 48,
            "interpretation": "Pixel-change candidates. Confirm with source frames and timing. Flashes may register and subtle cuts may be missed. Continuous footage can still contain important actions."}


def read_transcript(db, workspace_id, asset, offset, unit):
    if type(offset) is not int or offset < 0:
        raise ValueError("craft_transcript_offset_invalid")
    if unit not in {"segment", "word"}:
        raise ValueError("craft_transcript_unit_invalid")
    row = db.scalar(select(StudioTranscript).join(StudioMediaIngest).where(
        StudioTranscript.workspace_id == workspace_id,
        StudioTranscript.asset_id == asset["assetId"],
        StudioMediaIngest.workspace_id == workspace_id,
        StudioMediaIngest.asset_id == asset["assetId"],
        or_(
            StudioTranscript.source_checksum_sha256 == asset["checksumSha256"],
            and_(
                StudioTranscript.source_checksum_sha256.is_(None),
                StudioMediaIngest.media_info["checksumSha256"].as_string() == asset["checksumSha256"],
            ),
        ),
        StudioTranscript.status.in_(["ready", "reviewed"]),
    ).order_by(StudioTranscript.updated_at.desc(), StudioTranscript.id).limit(1))
    if row is None:
        return {"status": "unavailable", "reason": "No ready transcript for this source checksum."}
    transcript = transcript_out(row)
    items = (
        [word for segment in transcript.segments for word in segment.words]
        if unit == "word" else transcript.segments
    )
    page = items[offset:offset + (60 if unit == "word" else 8)]
    return {
        "status": transcript.status, "locale": transcript.locale, "unit": unit,
        "items": [{
            "startSeconds": item.start_microseconds / 1_000_000,
            "endSeconds": item.end_microseconds / 1_000_000,
            "text": item.text,
        } for item in page],
        "nextOffset": offset + len(page) if offset + len(page) < len(items) else None,
    }
