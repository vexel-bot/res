"""Separate solid quad coverage and SVG clip coverage, without pixel fitting."""
import hashlib
import importlib.util
import json
import math
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / "docs/studios/research/editor-oss-20261002"
FOLDER = STUDY / "temporal-matte-svg-subtract-uniform-controls"
helper_path = ROOT / "scripts/validation/editor-temporal-matte-edge-ramp-study.py"
spec = importlib.util.spec_from_file_location("independent_edge_ramp", helper_path)
reference = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reference)


def axis_aligned(polygon):
    return all(abs(polygon[(i + 1) % 4][0] - x) < 1e-8 or abs(polygon[(i + 1) % 4][1] - y) < 1e-8
               for i, (x, y) in enumerate(polygon))


def main():
    receipt = json.loads((FOLDER / "receipt.json").read_text(encoding="utf-8"))
    records = []
    for record in receipt["records"]:
        if record["mode"] not in {"unmasked", "normal-white-cover", "inverse-empty"}:
            continue
        manifest_path, png = FOLDER / (record["name"] + ".json"), FOLDER / (record["name"] + ".png")
        assert hashlib.sha256(manifest_path.read_bytes()).hexdigest() == record["manifestSha256"]
        assert hashlib.sha256(png.read_bytes()).hexdigest() == record["pngSha256"]
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        hero = next(layer for layer in manifest["layers"] if layer["name"] == "hero")
        polygon = [reference.geometry.transform_point(manifest, hero["id"], x, y) for x, y in [(0, 0), (170, 0), (170, 150), (0, 150)]]
        aligned = axis_aligned(polygon)
        image = Image.open(png).convert("RGB")
        bounds = (max(0, math.floor(min(x for x, y in polygon)) - 2), max(0, math.floor(min(y for x, y in polygon)) - 2),
                  min(320, math.ceil(max(x for x, y in polygon)) + 2), min(320, math.ceil(max(y for x, y in polygon)) + 2))
        checks = []
        for y in range(bounds[1], bounds[3]):
            for x in range(bounds[0], bounds[2]):
                quad = reference.edge_ramp(polygon, x + .5, y + .5)
                if quad in (0, 1) and all(reference.edge_ramp(polygon, x + .5 + dx, y + .5 + dy) == quad
                                          for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]):
                    continue
                clip = quad if aligned else reference.geometry.pixel_coverage(polygon, x, y)
                expected = quad * (1 if record["mode"] == "unmasked" else clip) * .9 * .9 * .85 * 255
                rgb = image.getpixel((x, y))
                checks.append({"x": x, "y": y, "quadCoverage": quad, "clipCoverage": clip, "expectedChannel": expected,
                               "observedRgb": rgb, "maximumChannelError": max(abs(channel - expected) for channel in rgb)})
        records.append({"name": record["name"], "axisAligned": aligned, "probeCount": len(checks),
                        "maximumError": max(check["maximumChannelError"] for check in checks),
                        "rmsError": math.sqrt(sum(check["maximumChannelError"] ** 2 for check in checks) / len(checks)),
                        "worstPixels": sorted(checks, key=lambda check: check["maximumChannelError"], reverse=True)[:5], "checks": checks})
    report = {"scope": "research_only_separate_quad_and_clip_coverage", "productionAdmission": "pending", "originalOracleChanged": False,
              "hypothesis": "Solid quad minimum distance ramp; axis-aligned clip ramp, rotated clip exact area. No fitted constants.",
              "limitations": "Mask raster-space selection and source-image edge coverage are not yet proven; this is not a production oracle.",
              "analysisScriptSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "edgeRampHelperSha256": hashlib.sha256(helper_path.read_bytes()).hexdigest(), "records": records}
    (STUDY / "temporal-matte-mixed-coverage-study.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps([{key: value for key, value in record.items() if key not in {"checks", "worstPixels"}} for record in records]))


if __name__ == "__main__":
    main()
