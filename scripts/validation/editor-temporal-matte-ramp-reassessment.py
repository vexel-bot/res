"""Independent quad/clip/texel reference over retained candidate video probes."""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / "docs/studios/research/editor-oss-20261002"
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "backend/tests"))
from tests.temporal_matte_kernel_diagnostic import inverse, original_mask, point, raster_value, times_for, worlds  # noqa: E402

helper_path = ROOT / "scripts/validation/editor-temporal-matte-mixed-coverage-study.py"
spec = importlib.util.spec_from_file_location("independent_mixed_coverage", helper_path)
reference = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reference)
mask = original_mask()


def channel(frame, scope, branch, mode, invert, x, y):
    total = 0
    samples = times_for(frame, scope)
    opacity = .6 + .3 * min(frame / 8, 1)
    for sample in samples:
        target, source = worlds(frame, sample, scope, branch)
        target_poly = [point(target, u, v) for u, v in [(0, 0), (170, 0), (170, 150), (0, 150)]]
        source_poly = [point(source, u, v) for u, v in [(0, 0), (80, 0), (80, 96), (0, 96)]]
        aligned = reference.axis_aligned(target_poly)
        for dx in range(2):
            for dy in range(2):
                px, py = x + dx, y + dy
                quad = reference.reference.edge_ramp(target_poly, px + .5, py + .5)
                clip = quad if aligned else reference.reference.geometry.pixel_coverage(target_poly, px, py)
                source_coverage = reference.reference.edge_ramp(source_poly, px + .5, py + .5)
                u, v = point(inverse(source), px + .5, py + .5)
                texture = raster_value(mask, max(1e-8, min(80 - 1e-8, u)), max(1e-8, min(96 - 1e-8, v)), mode)
                matte = source_coverage * texture * opacity
                total += quad * clip * (1 - matte if invert else matte) * .9 * .9 * .85 * 255
    return total / (4 * len(samples))


def main():
    source_path = STUDY / "temporal-matte-svg-subtract-final-encode-study-v2/analysis.json"
    source = json.loads(source_path.read_text(encoding="utf-8"))
    cache, records = {}, []
    for record in source["records"]:
        scope, branch, mode, invert = record["variant"].split("-")
        checks = []
        for check in record["checks"]:
            key = (record["variant"], check["frame"], check["x"], check["y"])
            if key not in cache:
                cache[key] = channel(check["frame"], scope, branch, mode, invert == "inverted", check["x"], check["y"])
            expected = cache[key]
            checks.append({"frame": check["frame"], "x": check["x"], "y": check["y"], "rampClipResearchChannel": expected,
                           "originalOracleChannel": check["expectedChannel"], "observedRgb": check["observedRgb"],
                           "maximumChannelError": max(abs(channel - expected) for channel in check["observedRgb"])})
        records.append({"variant": record["variant"], "crf": record["crf"], "outputSha256": record["outputSha256"],
                        "maximumResearchReferenceError": max(check["maximumChannelError"] for check in checks),
                        "failedResearchProbes": [check for check in checks if check["maximumChannelError"] >= 8], "checks": checks})
    report = {"scope": "research_only_quad_clip_texture_reassessment", "productionAdmission": "pending", "originalOracleChanged": False,
              "hypothesis": "Quad/image edge ramp, axis-aligned ramp or rotated area clip, texture reconstructed at output pixel center.",
              "limitations": "Uniform-mask source-image coincident edges and clip specialization are not fully qualified; no production admission.",
              "sourceAnalysisSha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
              "analysisScriptSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "helperSha256": hashlib.sha256(helper_path.read_bytes()).hexdigest(), "records": records}
    (STUDY / "temporal-matte-ramp-reassessment.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps([{ "variant": record["variant"], "crf": record["crf"], "maximumError": record["maximumResearchReferenceError"],
                      "failedProbes": len(record["failedResearchProbes"])} for record in records]))


if __name__ == "__main__":
    main()
