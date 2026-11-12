"""Detect abrupt, brief, wide-area brightening in a rendered Craft transition."""

from __future__ import annotations

import json
import math
import subprocess
import tempfile
from collections import deque
from fractions import Fraction
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageChops, ImageStat

from ...providers.studios.media_runtime import resolve_tool


SAMPLE_SIDE = 144
MIN_LIFT = 35
MIN_AREA = 0.60
RISE_SECONDS = 0.18
RETURN_SECONDS = 0.50
_LIFT_MASK = [255 if value >= MIN_LIFT else 0 for value in range(256)]


def _report(sampled_frames: int, events: list[dict], contiguous: bool = True) -> dict:
    status = "flagged" if events else "pass" if contiguous and sampled_frames >= 3 else "inconclusive"
    return {"status": status, "sampledFrames": sampled_frames, "events": events}


def _flash_at_peak(before, peak, after, fps: float) -> dict | None:
    peak_index, peak_mean, peak_image = peak
    before_index, before_mean, before_image = min(before, key=lambda sample: sample[1])
    after_index, after_mean, after_image = min(after, key=lambda sample: sample[1])
    mean_lift = min(peak_mean - before_mean, peak_mean - after_mean)
    # The average can be lower than the pixel threshold when only 60% changes.
    if mean_lift < MIN_LIFT * MIN_AREA:
        return None
    rising = ImageChops.subtract(peak_image, before_image).point(_LIFT_MASK)
    falling = ImageChops.subtract(peak_image, after_image).point(_LIFT_MASK)
    common = ImageChops.darker(rising, falling)
    area = common.histogram()[255] / (peak_image.width * peak_image.height)
    if area < MIN_AREA:
        return None
    return {
        "startFrame": before_index,
        "peakFrame": peak_index,
        "endFrame": after_index,
        "timeSeconds": round(peak_index / fps, 4),
        "areaFraction": round(area, 4),
        "meanLift": round(mean_lift, 2),
    }


def inspect_transition_flash(frames: Iterable[tuple[int, Image.Image]], fps: float) -> dict:
    """Analyze consecutive frames. Frames with a gap are never compared across it."""
    if not math.isfinite(fps) or fps <= 0:
        return _report(0, [], contiguous=False)
    rise_frames = max(1, math.floor(RISE_SECONDS * fps))
    return_frames = max(1, math.floor(RETURN_SECONDS * fps))
    samples = deque()
    events: list[dict] = []
    contiguous = True
    seen = 0
    previous = None
    candidate_offset = 0

    def advance(flush=False):
        nonlocal candidate_offset
        while candidate_offset + 1 < len(samples) and (
            flush or len(samples) - candidate_offset > return_frames
        ):
            if candidate_offset:
                window = list(samples)
                event = _flash_at_peak(
                    window[:candidate_offset], window[candidate_offset], window[candidate_offset + 1:], fps,
                )
                if event:
                    if events and event["startFrame"] <= events[-1]["endFrame"]:
                        if event["meanLift"] > events[-1]["meanLift"]:
                            events[-1] = event
                    else:
                        events.append(event)
            candidate_offset += 1
            if candidate_offset > rise_frames:
                samples.popleft()
                candidate_offset -= 1

    for frame, image in frames:
        if previous is not None and frame != previous + 1:
            advance(flush=True)
            samples.clear()
            candidate_offset = 0
            contiguous = False
        luminance = image.convert("L").resize((SAMPLE_SIDE, SAMPLE_SIDE), Image.Resampling.BOX)
        samples.append((frame, ImageStat.Stat(luminance).mean[0], luminance))
        seen += 1
        previous = frame
        advance()
    advance(flush=True)
    return _report(seen, events, contiguous)


def inspect_video_flash(
    path: Path, start_seconds: float | None = None, duration_seconds: float | None = None, *, timeout: float = 90,
) -> dict:
    """Decode a local export at its nominal frame rate with bounded in-memory data."""
    for value in (start_seconds, duration_seconds):
        if value is not None and (not math.isfinite(value) or value < 0):
            raise ValueError("craft_flash_invalid_range")
    path = path.resolve(strict=True)
    probe = subprocess.run(
        [resolve_tool("ffprobe"), "-v", "error", "-protocol_whitelist", "file,pipe", "-select_streams", "v:0", "-show_entries", "stream=avg_frame_rate",
         "-of", "json", str(path)],
        capture_output=True, text=True, timeout=min(timeout, 30), check=True,
    )
    streams = json.loads(probe.stdout).get("streams", [])
    if not streams:
        return _report(0, [], contiguous=False)
    try:
        fps = float(Fraction(streams[0]["avg_frame_rate"]))
    except (KeyError, ValueError, ZeroDivisionError):
        return _report(0, [], contiguous=False)
    if not math.isfinite(fps) or fps <= 0:
        return _report(0, [], contiguous=False)
    command = [resolve_tool("ffmpeg"), "-v", "error", "-nostdin", "-threads", "1", "-protocol_whitelist", "file,pipe"]
    if start_seconds is not None:
        command += ["-ss", str(start_seconds)]
    command += ["-i", str(path), "-an", "-map", "0:v:0"]
    if duration_seconds is not None:
        command += ["-t", str(duration_seconds)]
    command += [
        "-vf", f"fps={fps},scale={SAMPLE_SIDE}:{SAMPLE_SIDE}:flags=area,format=gray",
        "-threads", "1", "-f", "rawvideo", "-",
    ]
    frame_size = SAMPLE_SIDE * SAMPLE_SIDE
    offset = round((start_seconds or 0) * fps)
    with tempfile.TemporaryFile() as decoded:
        subprocess.run(command, stdout=decoded, stderr=subprocess.PIPE, timeout=timeout, check=True)
        decoded.seek(0)

        def frames():
            for index, payload in enumerate(iter(lambda: decoded.read(frame_size), b""), start=offset):
                if len(payload) != frame_size:
                    break
                yield index, Image.frombytes("L", (SAMPLE_SIDE, SAMPLE_SIDE), payload)

        return inspect_transition_flash(frames(), fps)
