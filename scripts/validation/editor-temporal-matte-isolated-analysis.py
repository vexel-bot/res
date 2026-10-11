"""Compare isolated canonical matte samples with the authored raster oracle."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

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
FOLDER = STUDY / "temporal-matte-isolated-samples"
mask = original_mask()


def expected_single(frame, sample, x, y, mode="alpha", invert=False, grid=8):
    target, source = worlds(frame, sample, "rig", "external")
    target, source = inverse(target), inverse(source)
    alpha = 0.9 * 0.9 * 0.85
    source_opacity = 0.6 + 0.3 * min(frame / 8, 1)
    value = 0.0
    for px in range(2):
        for py in range(2):
            content_coverage = 0
            mask_coverage = 0
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


def decode(path):
    return subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        check=True,
        capture_output=True,
        timeout=30,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    ).stdout


receipt = json.loads((FOLDER / "receipt.json").read_text(encoding="utf-8"))
records = []
for item in receipt["records"]:
    raw = decode(FOLDER / f"{item['name']}.mp4")
    assert hashlib.sha256((FOLDER / f"{item['name']}.mp4").read_bytes()).hexdigest() == item["videoSha256"]
    checks = []
    for x, y in probe_points(0, "rig", "external"):
        expected = expected_single(0, item["time"], x, y)
        observed = [
            sum(raw[((y + dy) * 320 + x + dx) * 3 + channel] for dx in range(2) for dy in range(2)) / 4
            for channel in range(3)
        ]
        checks.append({"x": x, "y": y, "expectedChannel": expected, "observedRgb": observed,
                       "maximumChannelError": max(abs(value - expected) for value in observed)})
    records.append({"sample": item["name"], "time": item["time"], "maximumChannelError": max(c["maximumChannelError"] for c in checks),
                    "failedProbes": [c for c in checks if c["maximumChannelError"] >= 8], "checks": checks})
report = {"scope": "isolated_single_sample_raster_diagnostic", "sourceReceipt": receipt, "records": records}
composite_path = STUDY / "temporal-matte-native14-filter-opacity/rig-external-alpha-normal/matte-exposure.mp4"
composite = decode(composite_path)
sample_raws = [decode(FOLDER / f"sample-{index}.mp4") for index in range(1, 9)]
comparison = []
for x, y in [(138, 134), (140, 82)]:
    actual = [
        sum(composite[((y + dy) * 320 + x + dx) * 3 + channel] for dx in range(2) for dy in range(2)) / 4
        for channel in range(3)
    ]
    isolated_average = [
        sum(
            sum(raw[((y + dy) * 320 + x + dx) * 3 + channel] for dx in range(2) for dy in range(2)) / 4
            for raw in sample_raws
        ) / len(sample_raws)
        for channel in range(3)
    ]
    expected_average = sum(expected_single(0, item["time"], x, y) for item in receipt["records"][1:]) / 8
    comparison.append({"x": x, "y": y, "actualTemporalRgb": actual, "averageIsolatedRgb": isolated_average,
                       "expectedAverageChannel": expected_average,
                       "temporalMinusIsolated": [a - b for a, b in zip(actual, isolated_average, strict=True)]})
report["compositeComparison"] = {"scope": "same_fixture_filter_weighted_accumulation_diagnostic",
                                 "compositeSha256": hashlib.sha256(composite_path.read_bytes()).hexdigest(),
                                 "probes": comparison}
(FOLDER / "pixel-analysis.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps([{key: value for key, value in record.items() if key != "checks"} for record in records]))
