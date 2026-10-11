"""Independent edge-distance ramp versus exact area on retained uniform PNGs."""
import hashlib
import importlib.util
import json
import math
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / "docs/studios/research/editor-oss-20261002"
FOLDER = STUDY / "temporal-matte-uniform-controls"
helper_path = ROOT / "scripts/validation/editor-temporal-matte-uniform-analysis.py"
spec = importlib.util.spec_from_file_location("independent_polygon_reference", helper_path)
geometry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(geometry)


def edge_ramp(polygon, x, y):
    # Inward oriented Euclidean distance from pixel center to each straight
    # edge. This half-pixel linear ramp is not fitted to observed values.
    signed_area = sum(px * polygon[(i + 1) % len(polygon)][1] - py * polygon[(i + 1) % len(polygon)][0]
                      for i, (px, py) in enumerate(polygon))
    sign = 1 if signed_area > 0 else -1
    distances = []
    for i, (px, py) in enumerate(polygon):
        dx, dy = polygon[(i + 1) % len(polygon)][0] - px, polygon[(i + 1) % len(polygon)][1] - py
        distances.append(sign * (dx * (y - py) - dy * (x - px)) / math.hypot(dx, dy))
    return max(0, min(1, .5 + min(distances)))


def main():
    rect = [(0, 0), (10, 0), (10, 10), (0, 10)]
    assert edge_ramp(rect, 0, 5) == .5 and edge_ramp(rect, .5, .5) == 1
    assert edge_ramp(rect, -.5, 5) == 0
    # At a fractional corner, the ramp takes the minimum, whereas exact area
    # is a product. This distinguishes the two mathematically before capture.
    translated = [(.35, .65), (10.35, .65), (10.35, 10.65), (.35, 10.65)]
    assert math.isclose(edge_ramp(translated, .5, .5), .35)
    assert math.isclose(geometry.pixel_coverage(translated, 0, 0), .65 * .35)
    receipt = json.loads((FOLDER / "receipt.json").read_text(encoding="utf-8"))
    records = []
    for record in receipt["records"]:
        if record["mode"] != "unmasked":
            continue
        manifest_path, png = FOLDER / (record["name"] + ".json"), FOLDER / (record["name"] + ".png")
        assert hashlib.sha256(manifest_path.read_bytes()).hexdigest() == record["manifestSha256"]
        assert hashlib.sha256(png.read_bytes()).hexdigest() == record["pngSha256"]
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        hero = next(layer for layer in manifest["layers"] if layer["name"] == "hero")
        polygon = [geometry.transform_point(manifest, hero["id"], x, y)
                   for x, y in [(0, 0), (170, 0), (170, 150), (0, 150)]]
        image = Image.open(png).convert("RGB")
        bounds = (max(0, math.floor(min(x for x, y in polygon)) - 2), max(0, math.floor(min(y for x, y in polygon)) - 2),
                  min(320, math.ceil(max(x for x, y in polygon)) + 2), min(320, math.ceil(max(y for x, y in polygon)) + 2))
        checks = []
        for y in range(bounds[1], bounds[3]):
            for x in range(bounds[0], bounds[2]):
                ramp = edge_ramp(polygon, x + .5, y + .5)
                # Only area samples around edges; interiors are identical.
                if ramp in (0, 1) and all(edge_ramp(polygon, x + .5 + dx, y + .5 + dy) == ramp
                                         for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]):
                    continue
                area = geometry.pixel_coverage(polygon, x, y)
                observed = image.getpixel((x, y))
                checks.append({"x": x, "y": y, "rampCoverage": ramp, "areaCoverage": area, "observedRgb": observed,
                               "rampError": max(abs(channel - ramp * .9 * .9 * .85 * 255) for channel in observed),
                               "areaError": max(abs(channel - area * .9 * .9 * .85 * 255) for channel in observed)})
        records.append({"variant": record["variant"], "pixelCount": len(checks),
                        "rampMaximumError": max(check["rampError"] for check in checks),
                        "areaMaximumError": max(check["areaError"] for check in checks),
                        "rampRmsError": math.sqrt(sum(check["rampError"] ** 2 for check in checks) / len(checks)),
                        "areaRmsError": math.sqrt(sum(check["areaError"] ** 2 for check in checks) / len(checks)),
                        "worstRampPixels": sorted(checks, key=lambda check: check["rampError"], reverse=True)[:5], "checks": checks})
    report = {"scope": "research_only_unmasked_affine_quad_coverage", "productionAdmission": "pending", "originalOracleChanged": False,
              "hypothesis": "Minimum half-device-pixel Euclidean edge ramp at output pixel center.",
              "limitations": "No claim about every Chromium path, nested raster spaces, mask clipping or textures.",
              "closedFormCalibrationCases": 5, "analysisScriptSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "polygonHelperSha256": hashlib.sha256(helper_path.read_bytes()).hexdigest(), "records": records}
    (STUDY / "temporal-matte-edge-ramp-study.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps([{key: value for key, value in record.items() if key not in {"checks", "worstRampPixels"}} for record in records]))


if __name__ == "__main__":
    main()
