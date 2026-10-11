"""Analyze lossless Chromium PNG captures against the authored raster oracle."""
import hashlib
import json
import sys
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "backend/tests"))
from tests.temporal_matte_kernel_diagnostic import (  # noqa: E402
    inverse,
    original_mask,
    point,
    probe_points,
    raster_value,
    worlds,
)

STUDY = ROOT / "docs/studios/research/editor-oss-20261002"
fixture = sys.argv[1] if len(sys.argv) > 1 else "rig"
assert fixture in {"rig", "child-inverted"}
scope, inverted = ("rig", False) if fixture == "rig" else ("child", True)
FOLDER = STUDY / ("temporal-matte-png-capture" if fixture == "rig" else "temporal-matte-png-capture-child-inverted")
mask = original_mask()


def expected_single(frame, sample, x, y, mode="alpha", invert=None, grid=8):
    invert = inverted if invert is None else invert
    target, source = worlds(frame, sample, scope, "external")
    target, source = inverse(target), inverse(source)
    alpha = 0.9 * 0.9 * 0.85
    source_opacity = 0.6 + 0.3 * min(frame / 8, 1)
    value = 0.0
    for px in range(2):
        for py in range(2):
            content_coverage = mask_coverage = 0
            for dx in range(grid):
                for dy in range(grid):
                    wx, wy = x + px + (dx + 0.5) / grid, y + py + (dy + 0.5) / grid
                    tx, ty = point(target, wx, wy)
                    if not (0 <= tx < 170 and 0 <= ty < 150):
                        continue
                    content_coverage += 1
                    coverage = raster_value(mask, *point(source, wx, wy), mode) * source_opacity
                    mask_coverage += 1 - coverage if invert else coverage
            value += content_coverage / grid**2 * mask_coverage / grid**2 * alpha * 255
    return value / 4


def pixels(name):
    path = FOLDER / f"{name}.png"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == next(item["pngSha256"] for item in receipt["records"] if item["name"] == name)
    return Image.open(path).convert("RGB")


receipt = json.loads((FOLDER / "receipt.json").read_text(encoding="utf-8"))
records = []
sample_times = [0, *[(i + 0.5) / 8 * 0.25 for i in range(8)]]
for name, sample in zip(["center", *[f"sample-{i}" for i in range(1, 9)]], sample_times, strict=True):
    image = pixels(name)
    checks = []
    for x, y in probe_points(0, scope, "external"):
        expected = expected_single(0, sample, x, y)
        observed = [sum(image.getpixel((x + dx, y + dy))[channel] for dx in range(2) for dy in range(2)) / 4
                    for channel in range(3)]
        checks.append({"x": x, "y": y, "expectedChannel": expected, "observedRgb": observed,
                       "maximumChannelError": max(abs(value - expected) for value in observed)})
    records.append({"sample": name, "time": sample, "maximumChannelError": max(c["maximumChannelError"] for c in checks),
                    "failedProbes": [c for c in checks if c["maximumChannelError"] >= 8], "checks": checks})
temporal = pixels("temporal")
comparison = []
sample_images = [pixels(f"sample-{i}") for i in range(1, 9)]
for x, y in ([(138, 134), (140, 82)] if fixture == "rig" else [(214, 96)]):
    actual = [sum(temporal.getpixel((x + dx, y + dy))[channel] for dx in range(2) for dy in range(2)) / 4
              for channel in range(3)]
    average = [sum(sum(image.getpixel((x + dx, y + dy))[channel] for dx in range(2) for dy in range(2)) / 4
                   for image in sample_images) / 8 for channel in range(3)]
    expected = sum(expected_single(0, time, x, y) for time in sample_times[1:]) / 8
    comparison.append({"x": x, "y": y, "temporalRgb": actual, "averageIsolatedRgb": average,
                       "expectedAverageChannel": expected, "temporalMinusIsolated": [a - b for a, b in zip(actual, average, strict=True)]})
report = {"scope": "lossless_browser_png_composition_diagnostic", "fixture": fixture,
          "productionAdmission": "pending", "receipt": receipt, "isolated": records,
          "compositeComparison": comparison}
(FOLDER / "pixel-analysis.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps({"isolated": len(records), "maximumIsolatedError": max(item["maximumChannelError"] for item in records),
                  "comparison": comparison}))
