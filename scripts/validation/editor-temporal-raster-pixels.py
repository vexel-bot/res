"""Contrast lossless browser pixels with independent exposure quadrature."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FOLDER = ROOT / "docs/studios/research/editor-oss-20261002/temporal-raster-diagnostic"
records = []
for samples, shutter in [(0, 180), (2, 180), (8, 180), (16, 180), (8, 0)]:
    for frame in [4, 34]:
        file = FOLDER / f"samples-{samples}-shutter-{shutter}-frame-{frame}.png"
        rgb = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", str(file), "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
            capture_output=True, check=True, timeout=30,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        ).stdout
        assert len(rgb) == 320 * 320 * 3
        part = int(frame >= 30)
        background, foreground = ([20, 40, 80], [220, 180, 70]) if not part else ([80, 20, 40], [40, 200, 220])
        times = ([frame] if samples == 0 or shutter == 0 else
                 [frame - shutter / 720 + (index + .5) * shutter / 360 / samples for index in range(samples)])
        probes = []
        for x in [86, 93, 96, 102, 120, 154, 159, 162, 167]:
            coverage = sum(max(0, min(x + 1, 20 + 18.75 * (time - part * 30) + 64)
                               - max(x, 20 + 18.75 * (time - part * 30))) for time in times) / len(times)
            expected = [b + .5 * coverage * (f - b) for b, f in zip(background, foreground, strict=True)]
            offset = ((52 + 60 * part) * 320 + x) * 3
            observed = list(rgb[offset:offset + 3])
            probes.append({"x": x, "expected": expected, "observed": observed,
                           "lumaError": abs(sum((a - b) * w for a, b, w in zip(
                               observed, expected, [.2126, .7152, .0722], strict=True)))})
        records.append({"samples": samples, "shutter": shutter, "frame": frame,
                        "pngSha256": hashlib.sha256(file.read_bytes()).hexdigest(), "probes": probes})
output = FOLDER / "pixels.json"
output.write_text(json.dumps({"scope": "lossless_browser_diagnostic_not_API_job", "records": records}, indent=2), encoding="utf-8")
print(json.dumps({"output": str(output), "maximumLumaError": max(p["lumaError"] for r in records for p in r["probes"])}))
