"""Compare retained real-job intermediates and outputs with independent raster probes."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / "docs/studios/research/editor-oss-20261002"
raster = json.loads((DIRECTORY / "temporal-rig-raster/pixels-no-filter.json").read_text(encoding="utf-8"))
records = []
for variant in ["control", "rig", "child", "disjoint"]:
    folder = DIRECTORY / "temporal-rig-render" / variant
    evidence = json.loads((folder / "evidence.json").read_text(encoding="utf-8"))
    receipt = evidence["renderMetadata"]["contextualEditing"]["rendererChecks"]["graphics"]["remotionReceipt"]
    intermediates = {}
    for name in ["graphics-intermediate.mp4", "rig.mp4"]:
        source = folder / name
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        expected = receipt["videoSha256"] if name == "graphics-intermediate.mp4" else evidence["renderResult"]["artifact"]["checksumSha256"]
        assert digest == expected
        intermediates[name] = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", str(source), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
            capture_output=True, check=True, timeout=30,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout
    for probe in evidence["pixelChecks"]:
        frame, x, y = probe["frame"], probe["x"], probe["y"]
        observed = {}
        for name, rgb in intermediates.items():
            observed[name] = [sum(rgb[(frame * 320 * 320 + (y + dy) * 320 + x + dx) * 3 + channel]
                                  for dx in range(2) for dy in range(2)) / 4 for channel in range(3)]
        png = next((p for capture in raster if capture["name"] == variant and capture["frame"] == frame
                    for p in capture["checks"] if p["x"] == x and p["y"] == y), None)
        if png:
            observed["PNG"] = png["PNG"]
        errors = {name: abs(sum((a - b) * weight for a, b, weight in zip(
            value, probe["expectedRgb"], [.2126, .7152, .0722], strict=True))) for name, value in observed.items()}
        records.append({"variant": variant, "frame": frame, "x": x, "y": y,
                        "expectedRgb": probe["expectedRgb"], "observed": observed, "errors": errors})
report = {"scope": "stage_diagnostic_not_new_API_qualification", "records": records}
(DIRECTORY / "temporal-rig-raster/latest-stage-pixels.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
for variant in ["control", "rig", "child", "disjoint"]:
    checks = [p for p in records if p["variant"] == variant]
    print(json.dumps({"variant": variant, "maximumErrors": {
        name: max(p["errors"].get(name, 0) for p in checks) for name in ["PNG", "graphics-intermediate.mp4", "rig.mp4"]},
        "failures": [p for p in checks if p["errors"]["rig.mp4"] >= 8]}))
