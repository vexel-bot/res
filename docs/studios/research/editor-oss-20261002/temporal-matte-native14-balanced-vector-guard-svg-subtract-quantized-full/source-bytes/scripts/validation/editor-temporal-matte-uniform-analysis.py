"""Independent polygon/pixel intersections for uniform-mask research controls.

No production oracle, thresholds, fixtures or admission conditions are changed.
Both C and C² are compared; browser pixels never define expected coverage.
"""
import hashlib
import json
import math
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
FOLDER = ROOT / "docs/studios/research/editor-oss-20261002/temporal-matte-uniform-controls"


def transform_point(manifest, layer_id, x, y):
    layers = {layer["id"]: layer for layer in manifest["layers"]}
    nodes = {node["targetLayerId"]: node for node in manifest["nodes"]}
    node_ids = {node["nodeId"]: node for node in manifest["nodes"]}
    visited = set()
    while layer_id is not None:
        assert layer_id not in visited, "parent_cycle"
        visited.add(layer_id)
        layer, node = layers[layer_id], nodes[layer_id]
        values = {}
        for track in manifest["tracks"]:
            if track["targetLayerId"] == layer_id:
                assert len(track["keyframes"]) == 1 and track["keyframes"][0]["frame"] == 0
                values[track["propertyPath"]] = track["keyframes"][0]["value"]
        px, py = node["transformOriginX"] * layer["width"], node["transformOriginY"] * layer["height"]
        angle = math.radians(values.get("rotation.degrees", layer["rotation"]))
        sx, sy = values.get("scale.x", 1), values.get("scale.y", 1)
        rx, ry = (x - px) * sx, (y - py) * sy
        x, y = (layer["x"] + values.get("position.x", 0) + px + math.cos(angle) * rx - math.sin(angle) * ry,
                layer["y"] + values.get("position.y", 0) + py + math.sin(angle) * rx + math.cos(angle) * ry)
        parent = node_ids.get(node.get("parentNodeId"))
        layer_id = parent["targetLayerId"] if parent else None
        if layer_id is not None:
            border = layers[layer_id]["properties"].get("editorialBorder", {}).get("width", 0)
            x, y = x + border, y + border
    return x, y


def polygon_area(polygon):
    if len(polygon) < 3:
        return 0.0
    # Translate to the first vertex before the shoelace sum to reduce
    # cancellation for tiny slivers at large composition coordinates.
    ox, oy = polygon[0]
    points = [(x - ox, y - oy) for x, y in polygon]
    return abs(sum(x * points[(i + 1) % len(points)][1] - y * points[(i + 1) % len(points)][0]
                   for i, (x, y) in enumerate(points))) / 2


def clip(polygon, axis, boundary, above):
    if not polygon:
        return []
    result = []
    previous = polygon[-1]
    was_inside = previous[axis] >= boundary if above else previous[axis] <= boundary
    for current in polygon:
        inside = current[axis] >= boundary if above else current[axis] <= boundary
        if inside != was_inside:
            fraction = (boundary - previous[axis]) / (current[axis] - previous[axis])
            result.append(tuple(previous[a] + fraction * (current[a] - previous[a]) for a in range(2)))
        if inside:
            result.append(current)
        previous, was_inside = current, inside
    return result


def pixel_coverage(polygon, x, y):
    result = polygon
    for axis, boundary, above in [(0, x, True), (0, x + 1, False), (1, y, True), (1, y + 1, False)]:
        result = clip(result, axis, boundary, above)
    return max(0, min(1, polygon_area(result)))


def inside_polygon(polygon, x, y):
    crosses = [(polygon[(i + 1) % len(polygon)][0] - px) * (y - py)
               - (polygon[(i + 1) % len(polygon)][1] - py) * (x - px)
               for i, (px, py) in enumerate(polygon)]
    return all(c >= -1e-10 for c in crosses) or all(c <= 1e-10 for c in crosses)


def main():
    # Closed-form fixtures independent of browser captures calibrate the
    # intersection calculation, including a diagonal half pixel.
    assert math.isclose(pixel_coverage([(.35, .65), (1.35, .65), (1.35, 1.65), (.35, 1.65)], 0, 0), .65 * .35)
    assert math.isclose(pixel_coverage([(0, 0), (1, 0), (0, 1)], 0, 0), .5)
    assert pixel_coverage([(0, 0), (1, 0), (1, 1), (0, 1)], 0, 0) == 1
    assert pixel_coverage([(0, 0), (1, 0), (1, 1), (0, 1)], 1, 0) == 0
    receipt = json.loads((FOLDER / "receipt.json").read_text(encoding="utf-8"))
    for file, checksum in receipt["sourceHashes"].items():
        assert hashlib.sha256((FOLDER / "source-bytes" / file).read_bytes()).hexdigest() == checksum
    for name, alpha in [("white", 255), ("empty", 0)]:
        image = Image.open(FOLDER / (name + ".png")).convert("RGBA")
        assert image.size == (170, 150)
        assert image.getextrema() == ((255, 255), (255, 255), (255, 255), (alpha, alpha))
    records, references, captured = [], {}, {}
    for record in receipt["records"]:
        name, variant, mode = record["name"], record["variant"], record["mode"]
        file = FOLDER / (name + ".json")
        assert hashlib.sha256(file.read_bytes()).hexdigest() == record["manifestSha256"]
        manifest = json.loads(file.read_text(encoding="utf-8"))
        assert not any(layer["properties"].get("recipeTemporalBlur") for layer in manifest["layers"])
        hero = next(layer for layer in manifest["layers"] if layer["name"] == "hero")
        polygon = [transform_point(manifest, hero["id"], x, y)
                   for x, y in [(0, 0), (hero["width"], 0), (hero["width"], hero["height"]), (0, hero["height"])]]
        geometry = {key: hero[key] for key in ["x", "y", "width", "height", "rotation", "opacity"]}
        geometry["polygon"] = polygon
        geometry["tracks"] = [t for t in manifest["tracks"] if t["targetLayerId"] == hero["id"]]
        if variant in references:
            assert references[variant]["geometry"] == geometry, "paired_target_transform_drift"
        else:
            coverage = {}
            for y in range(max(0, math.floor(min(p[1] for p in polygon)) - 1), min(320, math.ceil(max(p[1] for p in polygon)) + 1)):
                for x in range(max(0, math.floor(min(p[0] for p in polygon)) - 1), min(320, math.ceil(max(p[0] for p in polygon)) + 1)):
                    coverage[x, y] = pixel_coverage(polygon, x, y)
            references[variant] = {"geometry": geometry, "coverage": coverage}
        png = FOLDER / (name + ".png")
        assert hashlib.sha256(png.read_bytes()).hexdigest() == record["pngSha256"]
        pixels = Image.open(png).convert("RGB")
        captured[name] = pixels
        alpha = .9 * .9 * .85 * 255
        reference = references[variant]["coverage"]
        negative = mode.endswith("negative")
        metrics = {}
        for power in [1, 2]:
            maximum = 0
            worst = []
            square_error = absolute_error = boundary_count = 0
            outside_max = 0
            for y in range(320):
                for x in range(320):
                    c = reference.get((x, y), 0)
                    expected = 0 if negative else c ** power * alpha
                    observed = pixels.getpixel((x, y))
                    error = max(abs(channel - expected) for channel in observed)
                    if error > maximum:
                        maximum = error
                        worst = [{"x": x, "y": y, "coverage": c, "expectedChannel": expected,
                                  "observedRgb": observed, "maximumChannelError": error}]
                    if 1e-8 < c < 1 - 1e-8:
                        square_error += error ** 2
                        absolute_error += error
                        boundary_count += 1
                    if c == 0:
                        outside_max = max(outside_max, max(observed))
            metrics[f"C{power}"] = {"maximumPerPixelChannelError": maximum, "worstPixel": worst,
                                     "boundaryPixelCount": boundary_count,
                                     "boundaryMeanAbsoluteError": absolute_error / boundary_count if boundary_count else None,
                                     "boundaryRootMeanSquareError": math.sqrt(square_error / boundary_count) if boundary_count else None,
                                     "maximumOutsideGeometryChannel": outside_max}
        source = next(layer for layer in manifest["layers"] if layer["name"] == "matte")
        target_origin, tx, ty = [transform_point(manifest, hero["id"], x, y) for x, y in [(0, 0), (1, 0), (0, 1)]]
        source_origin = transform_point(manifest, source["id"], 0, 0)
        expected_source_origin = (target_origin[0] - (tx[0] - target_origin[0]) * hero["width"] - (ty[0] - target_origin[0]) * hero["height"],
                                  target_origin[1] - (tx[1] - target_origin[1]) * hero["width"] - (ty[1] - target_origin[1]) * hero["height"])
        cover = mode in {"normal-white-cover", "inverse-white-negative"}
        assert all(math.isclose(a, b, abs_tol=1e-9) for a, b in zip(source_origin, expected_source_origin if cover else target_origin, strict=True))
        comparisons = None
        if mode != "unmasked":
            control = captured[variant + "--unmasked"]
            maximum_difference = center_clip_error = 0
            center_clip_changed_pixels = 0
            for y in range(320):
                for x in range(320):
                    maximum_difference = max(maximum_difference, *(abs(a - b) for a, b in zip(pixels.getpixel((x, y)), control.getpixel((x, y)), strict=True)))
                    # Empirical paired prediction only: use captured unmasked
                    # color, then a mathematical pixel-center inclusion test.
                    # This is not an independent expected-color oracle.
                    expected = control.getpixel((x, y)) if inside_polygon(polygon, x + .5, y + .5) else (0, 0, 0)
                    error = max(abs(a - b) for a, b in zip(pixels.getpixel((x, y)), expected, strict=True))
                    center_clip_error = max(center_clip_error, error)
                    center_clip_changed_pixels += int(error != 0)
            comparisons = {"maximumPerPixelDifferenceFromUnmasked": maximum_difference,
                           "empiricalPixelCenterClipPredictionMaximumError": center_clip_error,
                           "empiricalPixelCenterClipPredictionUnequalPixels": center_clip_changed_pixels,
                           "predictionScope": "Captured unmasked pixels plus independent center inclusion; not admission or an independent color reference."}
        records.append({**record, "negativeControl": negative, "geometry": geometry,
                        "referenceMetrics": metrics, "comparison": comparisons})
        if negative:
            assert metrics["C1"]["maximumPerPixelChannelError"] == 0, "negative_control_not_black"
    uniform_pairs = []
    for variant in receipt["variants"]:
        name = variant["name"]
        white = captured[name + "--normal-white-cover"]
        empty = captured[name + "--inverse-empty"]
        assert white.tobytes() == empty.tobytes(), "equivalent_uniform_masks_differ"
        uniform_pairs.append({"variant": name, "allRgbPixelsEqual": True})
    report = {"scope": "research_only_uniform_mask_exact_polygon_analysis", "productionAdmission": "pending",
              "humanReview": "pending", "originalOracleChanged": False,
              "reference": "Exact convex polygon intersection with output pixel; C and C² retained separately.",
              "closedFormCalibrationCases": 4,
              "uniformEquivalentPairs": uniform_pairs,
              "scriptSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "captureReceiptSha256": hashlib.sha256((FOLDER / "receipt.json").read_bytes()).hexdigest(), "records": records}
    (FOLDER / "analysis.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps([{"name": r["name"], "C1Max": r["referenceMetrics"]["C1"]["maximumPerPixelChannelError"],
                       "C2Max": r["referenceMetrics"]["C2"]["maximumPerPixelChannelError"],
                       "C1BoundaryMAE": r["referenceMetrics"]["C1"]["boundaryMeanAbsoluteError"],
                       "C2BoundaryMAE": r["referenceMetrics"]["C2"]["boundaryMeanAbsoluteError"]} for r in records]))


if __name__ == "__main__":
    main()
