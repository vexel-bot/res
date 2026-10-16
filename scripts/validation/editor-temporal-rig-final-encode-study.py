"""Original controlled study separating 4:2:0 conversion and final compression."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / "docs/studios/research/editor-oss-20261002"
FOLDER = DIRECTORY / "temporal-rig-raster/final-encode-study"
FOLDER.mkdir(parents=True, exist_ok=True)
records = []
for variant in ["control", "rig", "child", "disjoint"]:
    parent = DIRECTORY / "temporal-rig-render" / variant
    evidence = json.loads((parent / "evidence.json").read_text(encoding="utf-8"))
    source = parent / "graphics-intermediate.mp4"
    receipt = evidence["renderMetadata"]["contextualEditing"]["rendererChecks"]["graphics"]["remotionReceipt"]
    assert hashlib.sha256(source.read_bytes()).hexdigest() == receipt["videoSha256"]
    configurations = [("ffv1", None, None), ("libx264", 18, "medium"),
                      ("libx264", 16, "veryfast"), ("libx264", 14, "veryfast"),
                      ("libx264", 12, "veryfast")]
    for codec, crf, preset in configurations:
        output = FOLDER / f"{variant}-{codec}-{crf}-{preset}.mkv"
        command = ["ffmpeg", "-v", "error", "-y", "-i", str(source), "-vf", "format=yuv420p", "-an", "-c:v", codec]
        if crf is not None:
            command += ["-crf", str(crf), "-preset", preset]
        command += ["-threads", "2", str(output)]
        subprocess.run(command, capture_output=True, check=True, timeout=30,
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
        record = {"variant": variant, "codec": codec, "preset": preset, "crf": crf,
                  "sourceSha256": receipt["videoSha256"], "videoSha256": hashlib.sha256(output.read_bytes()).hexdigest(),
                  "fileBytes": output.stat().st_size,
                  "maximumLuminanceError": max(p["luminanceError"] for p in checks),
                  "failedProbes": [p for p in checks if p["luminanceError"] >= 8], "probes": len(checks)}
        records.append(record)
        print(json.dumps(record), flush=True)
report = {"scope": "direct_encode_diagnostic_not_API_finalization_qualification", "records": records}
(FOLDER / "receipt.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
