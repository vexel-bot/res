"""Exact integer-translated PNG texels under a moving, fully covering target."""
import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / "docs/studios/research/editor-oss-20261002"
OUT = STUDY / "temporal-matte-svg-subtract-frame0-controls"
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "backend/tests"))
from tests.temporal_matte_kernel_diagnostic import expected_pixel, inverse, original_mask, point, worlds  # noqa: E402

helper_path = ROOT / "scripts/validation/editor-temporal-matte-residual-analysis.py"
spec = importlib.util.spec_from_file_location("residual_geometry_reference", helper_path)
reference = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reference)
mask = original_mask()


def sha(file):
    return hashlib.sha256(file.read_bytes()).hexdigest()


def exact_channel(case, x, y):
    alpha = sum(mask.getpixel((x - 100 + dx, y - 74 + dy))[3] for dx in range(2) for dy in range(2)) / 4
    source = alpha * .6 * .9 * .9 * .85
    return 255 * .9 * .9 * .85 if case.get("unmasked") else 255 * .9 * .9 * .85 - source if case["invert"] else source


def main():
    run = json.loads((OUT / "run.json").read_text(encoding="utf-8"))
    receipt = json.loads((OUT / "receipt.json").read_text(encoding="utf-8"))
    assert run["originalBytesRestored"] and run["exitCode"] == 0 and not run["conflictingConcurrentEdits"]
    frozen = json.loads((OUT / "sources.json").read_text(encoding="utf-8"))
    for file, checksum in frozen["sources"].items():
        assert sha(OUT / "source-bytes" / file) == checksum
    cases, images = [], {}
    for case in receipt["cases"]:
        records = []
        for record in case["records"]:
            folder = OUT / case["name"]
            png, manifest = folder / (record["name"] + ".png"), folder / (record["name"] + ".json")
            assert sha(png) == record["pngSha256"] and sha(manifest) == record["manifestSha256"]
            if record["name"] != "temporal":
                reference.verify_derived_geometry(case, record, json.loads(manifest.read_text(encoding="utf-8")))
            # Check all source viewport corners against the convex target.
            # This proves full target coverage for every block tested below.
            for sample in case["sampleTimes"] + [0]:
                target, source = worlds(0, sample, "child", "external")
                assert source == (1, 0, 0, 1, 100, 74)
                for u, v in [(0, 0), (80, 0), (80, 96), (0, 96)]:
                    x, y = point(inverse(target), u + 100, v + 74)
                    assert 0 < x < 170 and 0 < y < 150
            image = Image.open(png).convert("RGB")
            images[case["name"], record["name"]] = image
            checks = []
            for u in range(0, 80, 2):
                for v in range(0, 96, 2):
                    x, y = u + 100, v + 74
                    expected = exact_channel(case, x, y)
                    rgb = reference.block(image, x, y)
                    checks.append({"x": x, "y": y, "exactTranslatedTexelChannel": expected, "observedRgb": rgb,
                                   "maximumChannelError": max(abs(channel - expected) for channel in rgb)})
            records.append({"name": record["name"], "probeCount": len(checks),
                            "maximumError": max(check["maximumChannelError"] for check in checks),
                            "rmsMaximumChannelError": math.sqrt(sum(check["maximumChannelError"] ** 2 for check in checks) / len(checks)),
                            "failedProbesAtOriginalThreshold": [check for check in checks if check["maximumChannelError"] >= 8],
                            "checks": checks})
        cases.append({"variant": case["name"], "records": records})
    paired = []
    for name in [record["name"] for record in receipt["cases"][0]["records"]]:
        errors = []
        for u in range(0, 80, 2):
            for v in range(0, 96, 2):
                x, y = u + 100, v + 74
                a = reference.block(images['child-external-alpha-normal', name], x, y)
                b = reference.block(images['child-external-alpha-inverted', name], x, y)
                c = reference.block(images['child-external-unmasked', name], x, y)
                errors.append(max(abs(av + bv - cv) for av, bv, cv in zip(a, b, c, strict=True)))
        paired.append({"sample": name, "probeCount": len(errors), "maximumComplementError": max(errors)})
    focal = []
    for case in receipt["cases"]:
        focal.append({"variant": case["name"], "frame": 0, "x": 138, "y": 82,
                      "authoredAlphaTexels": [mask.getpixel((38 + dx, 8 + dy))[3] for dx in range(2) for dy in range(2)],
                      "exactTranslatedTexelChannel": exact_channel(case, 138, 82),
                      "originalSupersampledTextureChannel": None if case.get("unmasked") else expected_pixel(mask, 0, "child", "external", "alpha", case["invert"], 138, 82),
                      "observedByCapture": {record["name"]: reference.block(images[case["name"], record["name"]], 138, 82)
                                            for record in case["records"]}})
    report = {"scope": "exact_integer_translated_texel_conformance_under_clipped_temporal_target",
              "productionAdmission": "pending", "originalOracleChanged": False,
              "sourceTranslation": [100, 74], "sourceOpacity": .6, "targetOpacity": .9 * .9 * .85,
              "geometryScope": "Entire source viewport strictly inside target at every sample; no target AA expectation needed.",
              "captureReceiptSha256": sha(OUT / "receipt.json"), "analysisScriptSha256": sha(Path(__file__)),
              "geometryHelperSha256": sha(helper_path), "cases": cases, "pairedComplementChecks": paired, "focal": focal}
    (OUT / "analysis.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"focal": focal, "maximumErrors": [{"variant": case["variant"],
            "maximumError": max(record["maximumError"] for record in case["records"]),
            "failedProbes": sum(len(record["failedProbesAtOriginalThreshold"]) for record in case["records"])} for case in cases],
            "maximumComplementError": max(check["maximumComplementError"] for check in paired)}))


if __name__ == "__main__":
    main()
