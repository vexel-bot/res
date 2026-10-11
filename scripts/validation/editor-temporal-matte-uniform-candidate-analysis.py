"""Keep all coverage hypotheses on paired candidate mask controls."""
import hashlib
import importlib.util
import json
import math
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / "docs/studios/research/editor-oss-20261002"
FOLDER = STUDY / "temporal-matte-svg-subtract-uniform-controls"
ARCHIVE = STUDY / "temporal-matte-svg-subtract-uniform-source-archive"
helper_path = ROOT / "scripts/validation/editor-temporal-matte-edge-ramp-study.py"
spec = importlib.util.spec_from_file_location("independent_edge_ramp", helper_path)
reference = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reference)


def sha(file):
    return hashlib.sha256(file.read_bytes()).hexdigest()


def main():
    receipt = json.loads((FOLDER / "receipt.json").read_text(encoding="utf-8"))
    run = json.loads((ARCHIVE / "run.json").read_text(encoding="utf-8"))
    frozen = json.loads((ARCHIVE / "sources.json").read_text(encoding="utf-8"))
    assert run["originalBytesRestored"] and run["exitCode"] == 0 and not run["conflictingConcurrentEdits"]
    for file, checksum in frozen["sources"].items():
        assert sha(ARCHIVE / "source-bytes" / file) == checksum
    for file, checksum in receipt["sourceHashes"].items():
        assert sha(FOLDER / "source-bytes" / file) == checksum
    records, images = [], {}
    for record in receipt["records"]:
        manifest_path, png = FOLDER / (record["name"] + ".json"), FOLDER / (record["name"] + ".png")
        assert sha(manifest_path) == record["manifestSha256"] and sha(png) == record["pngSha256"]
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        hero = next(layer for layer in manifest["layers"] if layer["name"] == "hero")
        polygon = [reference.geometry.transform_point(manifest, hero["id"], x, y) for x, y in [(0, 0), (170, 0), (170, 150), (0, 150)]]
        image = Image.open(png).convert("RGB")
        images[record["name"]] = image
        negative = record["mode"] in {"normal-empty-negative", "inverse-white-negative"}
        if negative:
            assert image.getextrema() == ((0, 0), (0, 0), (0, 0))
        bounds = (max(0, math.floor(min(x for x, y in polygon)) - 2), max(0, math.floor(min(y for x, y in polygon)) - 2),
                  min(320, math.ceil(max(x for x, y in polygon)) + 2), min(320, math.ceil(max(y for x, y in polygon)) + 2))
        hypotheses = {}
        for model in ["area", "ramp"]:
            for power in [1, 2, 3]:
                checks = []
                for y in range(bounds[1], bounds[3]):
                    for x in range(bounds[0], bounds[2]):
                        coverage = (reference.edge_ramp(polygon, x + .5, y + .5) if model == "ramp"
                                    else reference.geometry.pixel_coverage(polygon, x, y))
                        if coverage == 1 and all(reference.edge_ramp(polygon, x + .5 + dx, y + .5 + dy) == 1
                                                  for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]):
                            continue
                        expected = 0 if negative else coverage ** power * .9 * .9 * .85 * 255
                        rgb = image.getpixel((x, y))
                        checks.append({"x": x, "y": y, "coverage": coverage, "expectedChannel": expected, "observedRgb": rgb,
                                       "maximumChannelError": max(abs(channel - expected) for channel in rgb)})
                hypotheses[model + str(power)] = {"probeCount": len(checks),
                    "maximumError": max(check["maximumChannelError"] for check in checks),
                    "rmsError": math.sqrt(sum(check["maximumChannelError"] ** 2 for check in checks) / len(checks)),
                    "worstPixels": sorted(checks, key=lambda check: check["maximumChannelError"], reverse=True)[:3]}
        records.append({"name": record["name"], "mode": record["mode"], "variant": record["variant"],
                        "negative": negative, "hypotheses": hypotheses})
    pairs = []
    for variant in receipt["variants"]:
        name = variant["name"]
        white = images[name + "--normal-white-cover"]
        inverse = images[name + "--inverse-empty"]
        assert white.tobytes() == inverse.tobytes()
        pairs.append({"variant": name, "whiteCoverAndInverseEmptyAllRgbEqual": True})
    report = {"scope": "research_only_candidate_uniform_mask_coverage", "productionAdmission": "pending", "originalOracleChanged": False,
              "hypotheses": "Exact area or minimum edge ramp, one/two/three separate coverage factors; all retained without fitted parameters.",
              "negativeControlsBlack": True, "equivalentPairs": pairs,
              "limitations": "Does not yet establish the mask raster transform or eliminate corner clip discrepancies.",
              "analysisScriptSha256": sha(Path(__file__)), "edgeRampHelperSha256": sha(helper_path),
              "captureReceiptSha256": sha(FOLDER / "receipt.json"), "records": records}
    (FOLDER / "analysis.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps([{ "name": record["name"], "area2": record["hypotheses"]["area2"]["maximumError"],
                      "ramp1": record["hypotheses"]["ramp1"]["maximumError"],
                      "ramp2": record["hypotheses"]["ramp2"]["maximumError"],
                      "ramp3": record["hypotheses"]["ramp3"]["maximumError"]} for record in records]))


if __name__ == "__main__":
    main()
