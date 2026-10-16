"""Compare independent uniform-alpha models and empirical paired controls."""
import hashlib
import importlib.util
import json
import math
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / "docs/studios/research/editor-oss-20261002"
FOLDER = STUDY / "temporal-matte-source-edge-controls"
helper_path = ROOT / "scripts/validation/editor-temporal-matte-uniform-analysis.py"
spec = importlib.util.spec_from_file_location("independent_polygon_reference", helper_path)
geometry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(geometry)


def block(image, x, y):
    return [sum(image.getpixel((x + dx, y + dy))[c] for dx in range(2) for dy in range(2)) / 4 for c in range(3)]


def source_polygon(manifest):
    source = next(layer for layer in manifest["layers"] if layer["name"] == "matte")
    return [geometry.transform_point(manifest, source["id"], x, y)
            for x, y in [(0, 0), (80, 0), (80, 96), (0, 96)]]


def to_source(polygon, x, y):
    ox, oy = polygon[0]
    ax, ay = (polygon[1][0] - ox) / 80, (polygon[1][1] - oy) / 80
    bx, by = (polygon[3][0] - ox) / 96, (polygon[3][1] - oy) / 96
    det = ax * by - ay * bx
    x, y = x - ox, y - oy
    return (x * by - y * bx) / det, (ax * y - ay * x) / det


def expected_models(polygon, x, y):
    integral = center_decal = 0
    for dx in range(2):
        for dy in range(2):
            coverage = geometry.pixel_coverage(polygon, x + dx, y + dy)
            integral += coverage
            u, v = to_source(polygon, x + dx + .5, y + dy + .5)
            # Half-texel kernel support with transparent values beyond the
            # authored bitmap, separate from its geometric viewport coverage.
            edge = max(0, min(1, u + .5, 80.5 - u)) * max(0, min(1, v + .5, 96.5 - v))
            center_decal += coverage * edge
    return {"areaClampedTexels": integral / 4, "areaTimesCenterDecalKernel": center_decal / 4}


def main():
    run = json.loads((FOLDER / "run.json").read_text(encoding="utf-8"))
    assert run["originalBytesRestored"] and all(p["exitCode"] == 0 for p in run["phases"])
    original = Image.open(FOLDER / "original.png").convert("RGBA")
    whitened = Image.open(FOLDER / "original-whitened.png").convert("RGBA")
    assert original.getchannel("A").tobytes() == whitened.getchannel("A").tobytes()
    assert whitened.getextrema()[:3] == ((255, 255), (255, 255), (255, 255))
    phases = []
    points = [(150, 184), (160, 170), (162, 92)]
    phase_names = ["native13", "vector-guard"]
    for additional in ["composite-inverse", "target-inverse", "svg-subtract"]:
        if (FOLDER / additional / "receipt.json").exists():
            additional_run = json.loads((FOLDER / additional / "run.json").read_text(encoding="utf-8"))
            assert additional_run["originalBytesRestored"] and additional_run["exitCode"] == 0
            phase_names.append(additional)
    for phase in phase_names:
        folder = FOLDER / phase
        receipt = json.loads((folder / "receipt.json").read_text(encoding="utf-8"))
        frozen = json.loads((folder / "sources.json").read_text(encoding="utf-8"))
        for file, checksum in frozen["sources"].items():
            assert hashlib.sha256((folder / "source-bytes" / file).read_bytes()).hexdigest() == checksum
        images, manifests = {}, {}
        for record in receipt["records"]:
            file = folder / (record["name"] + ".json")
            png = folder / (record["name"] + ".png")
            assert hashlib.sha256(file.read_bytes()).hexdigest() == record["manifestSha256"]
            assert hashlib.sha256(png.read_bytes()).hexdigest() == record["pngSha256"]
            images[record["name"]] = Image.open(png).convert("RGB")
            manifests[record["name"]] = json.loads(file.read_text(encoding="utf-8"))
        base = manifests["unmasked"]
        polygon = source_polygon(base)
        assert all(source_polygon(manifest) == polygon for manifest in manifests.values()), "source_transform_drift"
        source = next(layer for layer in base["layers"] if layer["name"] == "matte")
        source_opacity = next(t["keyframes"][0]["value"] for t in base["tracks"] if t["targetLayerId"] == source["id"] and t["propertyPath"] == "opacity")
        target_alpha = .9 * .9 * .85
        hero = next(layer for layer in base["layers"] if layer["name"] == "hero")
        target_polygon = [geometry.transform_point(base, hero["id"], x, y) for x, y in [(0, 0), (170, 0), (170, 150), (0, 150)]]
        checks = []
        for x, y in points:
            assert all(math.isclose(geometry.pixel_coverage(target_polygon, x + dx, y + dy), 1, abs_tol=1e-9)
                       for dx in range(2) for dy in range(2)), "probe_not_fully_inside_target"
            observed = {name: block(image, x, y) for name, image in images.items()}
            models = expected_models(polygon, x, y)
            expected = {name: {"directUniform50": coverage * source_opacity * 128,
                               "directUniform255": coverage * source_opacity * 255,
                               "normalUniform": coverage * source_opacity * 128 * target_alpha,
                               "inverseUniform": 255 * target_alpha - coverage * source_opacity * 128 * target_alpha}
                        for name, coverage in models.items()}
            complement = {image: [observed["normal-" + image][c] + observed["inverse-" + image][c] - observed["unmasked"][c]
                                  for c in range(3)] for image in ["original", "uniform"]}
            direct_prediction = {"uniform": [value * target_alpha for value in observed["direct-uniform50"]],
                                 "original": [value * target_alpha for value in observed["direct-original-whitened"]]}
            checks.append({"x": x, "y": y, "sourceLocalBlockCenter": to_source(polygon, x + 1, y + 1),
                           "sourceCoverageModels": models, "independentExpectedChannels": expected, "observed": observed,
                           "normalPlusInverseMinusUnmasked": complement,
                           "empiricalNormalPredictionFromDirectImage": direct_prediction,
                           "empiricalPredictionScope": "Uses captured direct-image pixels, not an independent color oracle."})
        phases.append({"phase": phase, "captureReceiptSha256": hashlib.sha256((folder / "receipt.json").read_bytes()).hexdigest(),
                       "sourceLocalOpacity": source_opacity, "targetOpacityProduct": target_alpha, "checks": checks})
    report = {"scope": "research_only_source_viewport_alpha_controls", "productionAdmission": "pending",
              "originalOracleChanged": False, "uniformAlpha": 128, "originalAlphaPreservedInWhitenedControl": True,
              "scriptSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "polygonHelperSha256": hashlib.sha256(helper_path.read_bytes()).hexdigest(), "phases": phases}
    (FOLDER / "analysis.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(phases))


if __name__ == "__main__":
    main()
