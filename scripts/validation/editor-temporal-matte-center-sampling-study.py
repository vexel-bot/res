"""Research-only pixel-center texture model; production oracle is untouched.

Geometric coverage is supersampled. PNG texels are reconstructed once at each
output pixel center, so exact 1:1 translations do not gain an artificial blur.
This study does not qualify admission or reinterpret historical test receipts.
"""
import hashlib
import json
import math
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
    raster_value,
    times_for,
    worlds,
)

STUDY = ROOT / "docs/studios/research/editor-oss-20261002"
mask = original_mask()


def center_sampled_pixel(frame, scope, branch, mode, invert, x, y, grid=8):
    source_opacity = .6 + .3 * min(frame / 8, 1)
    total = 0
    sample_times = times_for(frame, scope)
    for sample in sample_times:
        target, source = worlds(frame, sample, scope, branch)
        target, source = inverse(target), inverse(source)
        for px in range(2):
            for py in range(2):
                u, v = point(source, x + px + .5, y + py + .5)
                # Texture color and viewport coverage are separate. At an
                # antialiased viewport edge, use the clamped edge texel while
                # the geometric coverage below attenuates the image.
                texture = raster_value(mask, max(1e-8, min(mask.width - 1e-8, u)),
                                       max(1e-8, min(mask.height - 1e-8, v)), mode)
                content = intersection = 0
                for dx in range(grid):
                    for dy in range(grid):
                        wx, wy = x + px + (dx + .5) / grid, y + py + (dy + .5) / grid
                        tx, ty = point(target, wx, wy)
                        if not (0 <= tx < 170 and 0 <= ty < 150):
                            continue
                        content += 1
                        su, sv = point(source, wx, wy)
                        intersection += int(0 <= su < mask.width and 0 <= sv < mask.height)
                content /= grid ** 2
                intersection /= grid ** 2
                image_alpha = intersection * texture * source_opacity
                mask_alpha = content - image_alpha if invert else image_alpha
                total += content * mask_alpha * .9 * .9 * .85 * 255
    return total / (len(sample_times) * 4)


conformance = json.loads((STUDY / "temporal-matte-texel-conformance.json").read_text(encoding="utf-8"))
for case in conformance["cases"]:
    actual = center_sampled_pixel(0, "control", "external", "alpha", case["invert"], case["x"], case["y"])
    assert math.isclose(actual, case["exactTranslatedTexelChannel"], abs_tol=1e-9)

records = []
for phase in ["filter-opacity", "balanced-composition-opacity", "factored-balanced-opacity"]:
    directory = STUDY / ("temporal-matte-native14-" + phase)
    for file in sorted(directory.glob("*/evidence.json")):
        evidence = json.loads(file.read_text(encoding="utf-8"))
        scope, branch, mode, invert = evidence["variant"].split("-")
        video = file.parent / "matte-exposure.mp4"
        checksum = hashlib.sha256(video.read_bytes()).hexdigest()
        assert checksum == evidence["renderResult"]["artifact"]["checksumSha256"]
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-f", "rawvideo",
                              "-pix_fmt", "rgb24", "pipe:1"], check=True, capture_output=True, timeout=30,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout
        assert len(raw) == 16 * 320 * 320 * 3
        checks = []
        for check in evidence["pixelChecks"]:
            frame, x, y = check["frame"], check["x"], check["y"]
            expected = center_sampled_pixel(frame, scope, branch, mode, invert == "inverted", x, y)
            observed = [sum(raw[(frame * 320 * 320 + (y + dy) * 320 + x + dx) * 3 + c]
                            for dx in range(2) for dy in range(2)) / 4 for c in range(3)]
            checks.append({"frame": frame, "x": x, "y": y, "expectedChannel": expected,
                           "previousOracleChannel": check["expectedChannel"], "observedRgb": observed,
                           "maximumChannelError": max(abs(channel - expected) for channel in observed)})
        records.append({"phase": phase, "variant": evidence["variant"], "videoSha256": checksum,
                        "maximumChannelError": max(check["maximumChannelError"] for check in checks),
                        "failedProbes": [check for check in checks if check["maximumChannelError"] >= 8],
                        "checks": checks})
report = {"scope": "research_only_corrected_texture_sampling_reassessment", "productionAdmission": "pending",
          "originalTestsChanged": False, "tolerance": 8, "texelConformanceCases": len(conformance["cases"]),
          "referenceLimitation": "Affine/mask AA still requires independent validation before adoption",
          "studyScriptSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "records": records}
(STUDY / "temporal-matte-center-sampling-study.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps([{key: value for key, value in record.items() if key != "checks"} for record in records]))
