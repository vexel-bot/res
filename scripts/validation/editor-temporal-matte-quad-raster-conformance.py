"""Test projected triangle coverage on retained independent uniform fixtures."""
import hashlib
import importlib.util
import json
import math
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / "docs/studios/research/editor-oss-20261002"
FOLDER = STUDY / "temporal-matte-svg-subtract-uniform-controls"


def module(name, file):
    spec = importlib.util.spec_from_file_location(name, file)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


raster_path = ROOT / "scripts/validation/editor-temporal-matte-quad-raster-reference.py"
raster = module("independent_quad_raster", raster_path)
geometry_path = ROOT / "scripts/validation/editor-temporal-matte-uniform-analysis.py"
geometry = module("independent_polygon_geometry", geometry_path)


def main():
    rect = [(0, 0), (10, 0), (10, 10), (0, 10)]
    triangles = raster.quad_triangles(rect)
    assert raster.coverage(triangles, 5, 5) == 1
    assert raster.coverage(triangles, 0, 5) == .5
    assert raster.coverage(triangles, -.5, 5) == 0
    assert raster.coverage(triangles, 0, 0) == .5
    assert raster.serial_channel(1) == 177
    assert raster.serial_channel(.625, .625) == 69
    receipt = json.loads((FOLDER / "receipt.json").read_text(encoding="utf-8"))
    records = []
    for record in receipt["records"]:
        if record["mode"] in {"normal-empty-negative", "inverse-white-negative"}:
            continue
        manifest_path, png = FOLDER / (record["name"] + ".json"), FOLDER / (record["name"] + ".png")
        assert hashlib.sha256(manifest_path.read_bytes()).hexdigest() == record["manifestSha256"]
        assert hashlib.sha256(png.read_bytes()).hexdigest() == record["pngSha256"]
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        hero = next(layer for layer in manifest["layers"] if layer["name"] == "hero")
        polygon = [geometry.transform_point(manifest, hero["id"], x, y) for x, y in [(0, 0), (170, 0), (170, 150), (0, 150)]]
        aligned = all(abs(polygon[(i + 1) % 4][0] - x) < 1e-8 or abs(polygon[(i + 1) % 4][1] - y) < 1e-8
                      for i, (x, y) in enumerate(polygon))
        triangles = raster.quad_triangles(polygon)
        image = Image.open(png).convert("RGB")
        bounds = (max(0, math.floor(min(x for x, y in polygon)) - 2), max(0, math.floor(min(y for x, y in polygon)) - 2),
                  min(320, math.ceil(max(x for x, y in polygon)) + 2), min(320, math.ceil(max(y for x, y in polygon)) + 2))
        checks = []
        for y in range(bounds[1], bounds[3]):
            for x in range(bounds[0], bounds[2]):
                quad = raster.coverage(triangles, x + .5, y + .5)
                if quad in (0, 1) and all(raster.coverage(triangles, x + .5 + dx, y + .5 + dy) == quad
                                         for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]):
                    continue
                clip = quad if aligned else geometry.pixel_coverage(polygon, x, y)
                # Coincident image and rect clip merge in the aligned case;
                # the rotated image contributes another interpolated edge.
                image_coverage = quad if not aligned and record["mode"] == "normal-white-local" else None
                expected = raster.serial_channel(quad, None if record["mode"] == "unmasked" else clip, image_coverage)
                observed = image.getpixel((x, y))
                checks.append({"x": x, "y": y, "quadCoverage": quad, "clipCoverage": clip,
                               "imageCoverage": image_coverage, "expectedChannel": expected, "observedRgb": observed,
                               "maximumChannelError": max(abs(channel - expected) for channel in observed)})
        records.append({"name": record["name"], "axisAligned": aligned, "probeCount": len(checks),
                        "maximumError": max(check["maximumChannelError"] for check in checks),
                        "rmsError": math.sqrt(sum(check["maximumChannelError"] ** 2 for check in checks) / len(checks)),
                        "failedProbesAtOriginalThreshold": [check for check in checks if check["maximumChannelError"] >= 8],
                        "worstPixels": sorted(checks, key=lambda check: check["maximumChannelError"], reverse=True)[:5], "checks": checks})
    report = {"scope": "research_only_projected_quad_and_clip_conformance", "productionAdmission": "pending", "originalOracleChanged": False,
              "subpixelBits": 4, "calibrationCases": 6,
              "hypothesis": "Half-pixel annulus, four-bit projected vertices, barycentric coverage, separate clip/image factors, serial byte alpha.",
              "limitations": "Large affine quads only; no perspective/degenerate meshes or arbitrary path oracle claim.",
              "referenceScriptSha256": hashlib.sha256(raster_path.read_bytes()).hexdigest(),
              "geometryScriptSha256": hashlib.sha256(geometry_path.read_bytes()).hexdigest(),
              "analysisScriptSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "records": records}
    (STUDY / "temporal-matte-quad-raster-conformance.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps([{key: value for key, value in record.items() if key not in {"checks", "worstPixels", "failedProbesAtOriginalThreshold"}}
                     for record in records]))


if __name__ == "__main__":
    main()
