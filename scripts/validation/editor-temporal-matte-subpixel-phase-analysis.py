"""Source/runtime-derived subpixel and byte-alpha conformance on new phases."""
import hashlib
import importlib.util
import json
import math
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / "docs/studios/research/editor-oss-20261002"
FOLDER = STUDY / "temporal-matte-subpixel-phase-controls"
ARCHIVE = STUDY / "temporal-matte-subpixel-phase-source-archive"
helper_path = ROOT / "scripts/validation/editor-temporal-matte-uniform-analysis.py"
spec = importlib.util.spec_from_file_location("independent_polygon_reference", helper_path)
geometry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(geometry)


def sha(file):
    return hashlib.sha256(file.read_bytes()).hexdigest()


def byte(value):
    return max(0, min(255, math.floor(value + .5)))


def quad_coverage(bounds, x, y):
    left, top, right, bottom = bounds
    return max(0, min(1, x + 1 - left, y + 1 - top, right - x, bottom - y))


def serial_byte_channel(quad, clip=None):
    result = byte(quad * byte(.85 * 255))
    if clip is not None:
        result = byte(result * byte(clip * 255) / 255)
    for opacity in [.9, .9]:
        result = byte(result * byte(opacity * 255) / 255)
    return result


def main():
    receipt = json.loads((FOLDER / "receipt.json").read_text(encoding="utf-8"))
    run = json.loads((ARCHIVE / "run.json").read_text(encoding="utf-8"))
    frozen = json.loads((ARCHIVE / "sources.json").read_text(encoding="utf-8"))
    runtime_path, source_path = STUDY / "swiftshader-subpixel-runtime.json", STUDY / "swiftshader-subpixel-study.json"
    runtime, source = json.loads(runtime_path.read_text()), json.loads(source_path.read_text())
    assert runtime["values"]["subpixelBits"] == source["gnBuildSubpixelBits"] == 4
    assert run["originalBytesRestored"] and run["exitCode"] == 0 and not run["conflictingConcurrentEdits"]
    for file, checksum in frozen["sources"].items():
        assert sha(ARCHIVE / "source-bytes" / file) == checksum
    for file, checksum in receipt["sourceHashes"].items():
        assert sha(FOLDER / "source-bytes" / file) == checksum
    assert byte(.85 * 255) == 217 and byte(.9 * 255) == 230
    assert serial_byte_channel(1) == 177
    assert serial_byte_channel(.625) == 111 and serial_byte_channel(.625, .625) == 69
    assert serial_byte_channel(.875) == 154 and serial_byte_channel(.875, .875) == 135
    records = []
    for record in receipt["records"]:
        manifest_path, png = FOLDER / (record["name"] + ".json"), FOLDER / (record["name"] + ".png")
        assert sha(manifest_path) == record["manifestSha256"] and sha(png) == record["pngSha256"]
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        hero = next(layer for layer in manifest["layers"] if layer["name"] == "hero")
        assert hero["opacity"] == .85
        for name in ["outer", "rig"]:
            assert next(layer for layer in manifest["layers"] if layer["name"] == name)["opacity"] == .9
        polygon = [geometry.transform_point(manifest, hero["id"], x, y) for x, y in [(0, 0), (170, 0), (170, 150), (0, 150)]]
        assert all(abs(polygon[(i + 1) % 4][0] - x) < 1e-8 or abs(polygon[(i + 1) % 4][1] - y) < 1e-8
                   for i, (x, y) in enumerate(polygon))
        continuous = (min(x for x, y in polygon), min(y for x, y in polygon), max(x for x, y in polygon), max(y for x, y in polygon))
        # VertexRoutine rounds projected fixed-point coordinates. This grid
        # comes from the exact source/build and live GL capability, not a fit.
        snapped = tuple(round(value * 16) / 16 for value in continuous)
        bounds = (max(0, math.floor(continuous[0]) - 2), max(0, math.floor(continuous[1]) - 2),
                  min(320, math.ceil(continuous[2]) + 2), min(320, math.ceil(continuous[3]) + 2))
        image = Image.open(png).convert("RGB")
        masked = record["mode"] == "normal-white-cover"
        checks, maxima, count, squared = [], {"continuousFloat": 0, "snappedFloat": 0, "snappedByte": 0}, 0, 0
        for y in range(bounds[1], bounds[3]):
            for x in range(bounds[0], bounds[2]):
                q, qs = quad_coverage(continuous, x, y), quad_coverage(snapped, x, y)
                expected = {"continuousFloat": q ** (2 if masked else 1) * .9 * .9 * .85 * 255,
                            "snappedFloat": qs ** (2 if masked else 1) * .9 * .9 * .85 * 255,
                            "snappedByte": serial_byte_channel(qs, qs if masked else None)}
                observed = image.getpixel((x, y))
                errors = {key: max(abs(channel - value) for channel in observed) for key, value in expected.items()}
                for key, error in errors.items():
                    maxima[key] = max(maxima[key], error)
                count += 1
                squared += errors["snappedByte"] ** 2
                if 0 < q < 1 or 0 < qs < 1 or errors["snappedByte"] > 0:
                    checks.append({"x": x, "y": y, "continuousCoverage": q, "snappedCoverage": qs,
                                   "expected": expected, "observedRgb": observed, "errors": errors})
        records.append({"name": record["name"], "variant": record["variant"], "mode": record["mode"],
                        "continuousBounds": continuous, "snappedBounds": snapped, "allPixelProbeCount": count,
                        "maximumErrors": maxima, "snappedByteRmsError": math.sqrt(squared / count),
                        "worstPixels": sorted(checks, key=lambda check: check["errors"]["snappedByte"], reverse=True)[:5],
                        "failedSnappedByteProbesAtOriginalThreshold": [check for check in checks if check["errors"]["snappedByte"] >= 8],
                        "edgeChecks": checks})
    report = {"scope": "new_axis_aligned_subpixel_phase_conformance", "productionAdmission": "pending", "originalOracleChanged": False,
              "subpixelBits": 4, "opacityQuantization": "Round authored alpha to 8-bit; geometry, mask, rig, outer each multiply/round separately.",
              "modelOrigin": "Pinned GN build, live GL SUBPIXEL_BITS and fixed-point vertex projection; no fitted parameters.",
              "limitations": "Does not model rotated triangle vertex interpolation, non-rectangular clips or source-image resampling.",
              "runtimeSha256": sha(runtime_path), "sourceStudySha256": sha(source_path),
              "captureReceiptSha256": sha(FOLDER / "receipt.json"), "analysisScriptSha256": sha(Path(__file__)), "records": records}
    (FOLDER / "analysis.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"captures": len(records), "allPixelComparisons": sum(record["allPixelProbeCount"] for record in records),
                      "maximumErrors": {key: max(record["maximumErrors"][key] for record in records) for key in maxima},
                      "failedSnappedByteProbes": sum(len(record["failedSnappedByteProbesAtOriginalThreshold"]) for record in records)}))


if __name__ == "__main__":
    main()
