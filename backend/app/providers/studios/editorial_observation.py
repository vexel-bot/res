"""Measurements from encoded pixels, independent of declared layer IDs.

This is partial machine observation, not an editorial approval or listening test.
"""

import json
import subprocess

from ...services.object_storage import sha256_file


def observe_render(path, *, scenes=(), frame_rate=30, max_seconds=120):
    def run(args):
        return subprocess.run(
            args, capture_output=True, check=True, timeout=90, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
        ).stdout

    probe = json.loads(run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)]))
    duration = float(probe["format"]["duration"])
    coverage = min(duration, max_seconds)
    pixels = run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-threads",
            "1",
            "-filter_threads",
            "1",
            "-i",
            str(path),
            "-t",
            str(coverage),
            "-an",
            "-vf",
            "fps=2,scale=64:64,format=gray",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "gray",
            "-",
        ]
    )
    size = 64 * 64
    frames = [pixels[i : i + size] for i in range(0, len(pixels), size) if len(pixels[i : i + size]) == size]
    differences = [
        sum(abs(x - y) for x, y in zip(a, b, strict=True)) / (255 * size)
        for a, b in zip(frames, frames[1:], strict=False)
    ]
    # Low-resolution temporal samples cannot prove that small/fast details were absent.
    still = [difference <= 0.001 for difference in differences]
    intervals, start = [], None
    for i, value in enumerate([*still, False]):
        if value and start is None:
            start = i
        if not value and start is not None:
            if (i - start) / 2 >= 2:
                intervals.append((start / 2, i / 2))
            start = None
    scene_ranges, offset = [], 0
    for scene in scenes:
        if getattr(scene, "entrance", "cut") != "cut":
            offset -= scene.transition_frames / frame_rate
        end = offset + scene.duration_frames / frame_rate
        scene_ranges.append((scene.id, offset, end))
        offset = end
    findings = []
    for start, end in intervals:
        overlaps = [
            (scene_id, max(start, left), min(end, right))
            for scene_id, left, right in scene_ranges
            if left < end and right > start
        ]
        for scene_id, left, right in overlaps or [(None, start, end)]:
            findings.append(
                {
                    "code": "near_static_sampled_interval",
                    "sceneId": scene_id,
                    "startSeconds": left,
                    "endSeconds": right,
                    "severity": "observation",
                    "evidence": "normalized_mean_pixel_difference_at_2fps_lte_0.001",
                    "suggestedReview": "Verificar se a pausa sustenta a compreensão ou interrompe a progressão.",
                    "uncertainty": "Movimentos pequenos ou entre amostras podem não ter sido observados.",
                }
            )
    return {
        "schemaVersion": "studio.editorial-observation.v1",
        "status": "partial",
        "checksum": sha256_file(path),
        "durationSeconds": duration,
        "coverageSeconds": coverage,
        "sampleRate": 2,
        "sampleCount": len(frames),
        "nearStaticSampleRatio": sum(still) / len(still) if still else None,
        "audioStreamPresent": any(s.get("codec_type") == "audio" for s in probe["streams"]),
        "speechIntelligibility": "unknown",
        "soundEventAccuracy": "unknown",
        "editorialQuality": "unreviewed",
        "humanReview": "pending",
        "findings": findings,
    }
