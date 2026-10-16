"""Separate isolated paint, accumulation and encode at existing failed probes."""
import hashlib
import importlib.util
import json
import math
import subprocess
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / "docs/studios/research/editor-oss-20261002"
OUT = STUDY / "temporal-matte-svg-subtract-residual-controls-v2"
API = STUDY / "temporal-matte-native14-balanced-vector-guard-svg-subtract-full"
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "backend/tests"))
from tests.temporal_matte_kernel_diagnostic import inverse, original_mask, point, raster_value, worlds  # noqa: E402

helper_path = ROOT / "scripts/validation/editor-temporal-matte-uniform-analysis.py"
spec = importlib.util.spec_from_file_location("independent_polygon_reference", helper_path)
geometry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(geometry)
mask = original_mask()


def sha(file):
    return hashlib.sha256(file.read_bytes()).hexdigest()


def block(image, x, y):
    return [sum(image.getpixel((x + dx, y + dy))[c] for dx in range(2) for dy in range(2)) / 4 for c in range(3)]


def single_expected(case, sample, x, y, center_texture=False):
    target, source = worlds(case["frame"], sample, case["scope"], case["branch"])
    target, source = inverse(target), inverse(source)
    source_opacity = .6 + .3 * min(case["frame"] / 8, 1)
    value = 0
    for px in range(2):
        for py in range(2):
            content = coverage = 0
            if center_texture:
                u, v = point(source, x + px + .5, y + py + .5)
                texture = raster_value(mask, max(1e-8, min(80 - 1e-8, u)),
                                       max(1e-8, min(96 - 1e-8, v)), case["mode"])
            for dx in range(8):
                for dy in range(8):
                    wx, wy = x + px + (dx + .5) / 8, y + py + (dy + .5) / 8
                    tx, ty = point(target, wx, wy)
                    if not (0 <= tx < 170 and 0 <= ty < 150):
                        continue
                    content += 1
                    u, v = point(source, wx, wy)
                    source_alpha = (texture * int(0 <= u < 80 and 0 <= v < 96) if center_texture
                                    else raster_value(mask, u, v, case["mode"])) * source_opacity
                    coverage += 1 - source_alpha if case["invert"] else source_alpha
            value += content / 64 * coverage / 64 * .9 * .9 * .85 * 255
    return value / 4


def verify_derived_geometry(case, record, manifest):
    by_name = {layer["name"]: layer for layer in manifest["layers"]}
    expected_target, expected_source = worlds(case["frame"], record["sampleTime"], case["scope"], case["branch"])
    maximum = 0
    for name, expected in [("hero", expected_target), ("matte", expected_source)]:
        for x, y in [(0, 0), (80, 0), (0, 96)]:
            observed = geometry.transform_point(manifest, by_name[name]["id"], x, y)
            reference = point(expected, x, y)
            maximum = max(maximum, *(abs(a - b) for a, b in zip(observed, reference, strict=True)))
    assert maximum < .002, (case["name"], record["name"], maximum)
    return maximum


def main():
    run = json.loads((OUT / "run.json").read_text(encoding="utf-8"))
    receipt = json.loads((OUT / "receipt.json").read_text(encoding="utf-8"))
    assert run["originalBytesRestored"] and run["exitCode"] == 0 and not run["conflictingConcurrentEdits"]
    frozen = json.loads((OUT / "sources.json").read_text(encoding="utf-8"))
    for file, checksum in frozen["sources"].items():
        assert sha(OUT / "candidate-source-bytes" / file) == checksum
    comparisons = []
    for case in receipt["cases"]:
        folder = OUT / case["name"]
        evidence_path = API / case["name"] / "evidence.json"
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        video = evidence_path.parent / "matte-exposure.mp4"
        assert sha(video) == evidence["renderResult"]["artifact"]["checksumSha256"]
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"],
                             check=True, capture_output=True, timeout=30).stdout
        assert len(raw) == 16 * 320 * 320 * 3
        images, matrix_checks = {}, []
        for record in case["records"]:
            png, manifest_path = folder / (record["name"] + ".png"), folder / (record["name"] + ".json")
            assert sha(png) == record["pngSha256"] and sha(manifest_path) == record["manifestSha256"]
            images[record["name"]] = Image.open(png).convert("RGB")
            if record["name"] != "temporal":
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                matrix_checks.append({"sample": record["name"], "maximumWorldPointError": verify_derived_geometry(case, record, manifest)})
        probes = sorted([check for check in evidence["pixelChecks"] if check["frame"] == case["frame"]],
                        key=lambda check: check["maximumChannelError"], reverse=True)[:3]
        checks = []
        for probe in probes:
            x, y = probe["x"], probe["y"]
            samples = []
            for record in case["records"]:
                if not record["name"].startswith("sample-"):
                    continue
                observed = block(images[record["name"]], x, y)
                expected = single_expected(case, record["sampleTime"], x, y)
                samples.append({"sample": record["name"], "time": record["sampleTime"], "observedRgb": observed,
                                "originalOracleChannel": expected,
                                "centerTextureResearchChannel": single_expected(case, record["sampleTime"], x, y, True),
                                "maximumOriginalError": max(abs(channel - expected) for channel in observed)})
            expected = sum(sample["originalOracleChannel"] for sample in samples) / 8
            assert math.isclose(expected, probe["expectedChannel"], abs_tol=1e-9)
            average = [sum(sample["observedRgb"][c] for sample in samples) / 8 for c in range(3)]
            temporal = block(images["temporal"], x, y)
            mp4 = [sum(raw[(case["frame"] * 320 * 320 + (y + dy) * 320 + x + dx) * 3 + c]
                       for dx in range(2) for dy in range(2)) / 4 for c in range(3)]
            assert mp4 == probe["observedRgb"]
            checks.append({"x": x, "y": y, "originalOracleChannel": expected, "originalApiFailed": probe["maximumChannelError"] >= 8,
                           "centerTextureResearchChannel": sum(sample["centerTextureResearchChannel"] for sample in samples) / 8,
                           "centerPngRgb": block(images["center"], x, y), "temporalPngRgb": temporal,
                           "averageIsolatedRgb": average, "apiMp4Rgb": mp4,
                           "temporalMinusIsolated": [a - b for a, b in zip(temporal, average, strict=True)],
                           "apiMp4MinusTemporalPng": [a - b for a, b in zip(mp4, temporal, strict=True)], "samples": samples})
        comparisons.append({"variant": case["name"], "frame": case["frame"], "apiEvidenceSha256": sha(evidence_path),
                            "derivedGeometryChecks": matrix_checks, "checks": checks})
    report = {"scope": "research_only_derived_residual_lossless_analysis", "productionAdmission": "pending",
              "originalOracleChanged": False, "centerTextureReferenceScope": "Research only; affine AA is not independently qualified.",
              "invalidEarlierControlsExcluded": "temporal-matte-svg-subtract-residual-controls/classification.json",
              "analysisScriptSha256": sha(Path(__file__)), "polygonHelperSha256": sha(helper_path),
              "captureReceiptSha256": sha(OUT / "receipt.json"), "comparisons": comparisons}
    (OUT / "analysis.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps([{ "variant": item["variant"], "frame": item["frame"],
                      "checks": [{key: value for key, value in check.items() if key != "samples"} for check in item["checks"]]}
                     for item in comparisons]))


if __name__ == "__main__":
    main()
