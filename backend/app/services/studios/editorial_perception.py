"""Bounded scene-change evidence with explicit sampling gaps; no claim of full perception."""

import re
from uuid import uuid4


def sample_offsets(runner, path, directory, start, span, cancelled, intervals=(), limit=12):
    analyzed = min(span, 120)
    name = "scene-changes-" + uuid4().hex + ".txt"
    metadata = directory / name
    runner._run(
        [
            "-y",
            "-ss",
            str(start),
            "-i",
            str(path),
            "-t",
            str(analyzed),
            "-an",
            "-vf",
            "scale=160:-2,select=gt(scene\\,0.3),metadata=print:file=" + name,
            "-threads",
            "2",
            "-f",
            "null",
            "-",
        ],
        directory,
        cancelled,
    )
    text = metadata.read_text(encoding="utf-8") if metadata.exists() else ""
    cuts = [float(t) for t in re.findall(r"pts_time:([0-9.]+)", text)]
    requested = [
        max(0, min(span - 0.04, t - start))
        for i in intervals
        for t in (i.start_seconds, (i.start_seconds + i.end_seconds) / 2, i.end_seconds)
        if start <= t < start + span
    ]
    anchors = [0, max(0, span / 2), max(0, span - 0.04)]
    around_cuts = [max(0, min(span - 0.04, t + d)) for t in cuts for d in (-0.12, 0.12)]
    ordered = list(dict.fromkeys(round(t, 4) for t in [*requested, *anchors, *around_cuts]))
    offsets = sorted(ordered[:limit])
    return offsets, {
        "method": "scene_changes_and_requested_intervals",
        "sceneChangeThreshold": 0.3,
        "analyzedIntervalSeconds": [start, start + analyzed],
        "detectedChanges": len(cuts),
        "requestedSamples": len(requested),
        "omittedSamples": max(0, len(ordered) - limit),
        "unobservedGapsSeconds": [
            [start + a, start + b] for a, b in zip(offsets, offsets[1:], strict=False) if b - a > 0.25
        ],
        "notFullVideoAnalysis": True,
        "eventClaimsRequireComplementaryInspection": True,
    }
