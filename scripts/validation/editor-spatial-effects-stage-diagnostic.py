"""Locate a retained real-job pixel deviation without substituting the final artifact."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / "docs/studios/research/editor-oss-20261002/spatial-effects-fast-stage-diagnostic/exposure"
evidence = json.loads((DIRECTORY / "evidence.json").read_text(encoding="utf-8"))
receipt = evidence["renderMetadata"]["contextualEditing"]["rendererChecks"]["graphics"]["remotionReceipt"]
records = []
for name, digest in [("graphics-intermediate.mp4", receipt["videoSha256"]),
                     ("spatial.mp4", evidence["renderResult"]["artifact"]["checksumSha256"])]:
    path = DIRECTORY / name
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
    rgb = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True, check=True, timeout=30,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout
    checks = []
    for probe in evidence["pixelChecks"]:
        frame, x, y = probe["frame"], probe["x"], probe["y"]
        observed = [sum(rgb[(frame * 320 * 320 + (y + dy) * 320 + x + dx) * 3 + channel]
                        for dx in range(2) for dy in range(2)) / 4 for channel in range(3)]
        error = abs(sum((a - b) * w for a, b, w in zip(
            observed, probe["expectedRgb"], [.2126, .7152, .0722], strict=True)))
        checks.append({"frame": frame, "x": x, "y": y, "observedRgb": observed,
                       "expectedRgb": probe["expectedRgb"], "luminanceError": error})
    records.append({"stage": name, "sha256": digest, "maximumLuminanceError": max(p["luminanceError"] for p in checks),
                    "failedProbes": [p for p in checks if p["luminanceError"] >= 8], "checks": checks})
report = {"scope": "retained_actual_job_decode_diagnostic_not_new_qualification", "records": records}
(DIRECTORY / "stages.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps([{k: v for k, v in record.items() if k != "checks"} for record in records]))
