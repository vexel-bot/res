"""Controlled encoder diagnostic using checksum-bound real visual intermediates."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / "docs/studios/research/editor-oss-20261002"
FOLDER = DIRECTORY / "temporal-rig-raster/codecs"
FOLDER.mkdir(parents=True, exist_ok=True)
records = []
for variant in ["rig", "child"]:
    parent = DIRECTORY / "temporal-rig-render" / variant
    evidence = json.loads((parent / "evidence.json").read_text(encoding="utf-8"))
    source = parent / "graphics-intermediate.mp4"
    receipt = evidence["renderMetadata"]["contextualEditing"]["rendererChecks"]["graphics"]["remotionReceipt"]
    assert hashlib.sha256(source.read_bytes()).hexdigest() == receipt["videoSha256"]
    for preset in ["veryfast", "medium", "slow"]:
        output = FOLDER / f"{variant}-{preset}.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(source), "-vf", "format=yuv420p", "-an",
                        "-c:v", "libx264", "-crf", "18", "-preset", preset, "-threads", "2", str(output)],
                       capture_output=True, check=True, timeout=30,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        rgb = subprocess.run(["ffmpeg", "-v", "error", "-i", str(output), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                             capture_output=True, check=True, timeout=30,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout
        checks = []
        for probe in evidence["pixelChecks"]:
            frame, x, y = probe["frame"], probe["x"], probe["y"]
            observed = [sum(rgb[(frame * 320 * 320 + (y + dy) * 320 + x + dx) * 3 + channel]
                            for dx in range(2) for dy in range(2)) / 4 for channel in range(3)]
            error = abs(sum((a - b) * weight for a, b, weight in zip(
                observed, probe["expectedRgb"], [.2126, .7152, .0722], strict=True)))
            checks.append({"frame": frame, "x": x, "y": y, "luminanceError": error})
        records.append({"variant": variant, "preset": preset, "crf": 18,
                        "sourceSha256": receipt["videoSha256"], "videoSha256": hashlib.sha256(output.read_bytes()).hexdigest(),
                        "maximumLuminanceError": max(p["luminanceError"] for p in checks),
                        "failedProbes": [p for p in checks if p["luminanceError"] >= 8], "probes": len(checks)})
report = {"scope": "direct_encode_diagnostic_not_API_finalization_qualification", "records": records}
(FOLDER / "receipt.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(records))
