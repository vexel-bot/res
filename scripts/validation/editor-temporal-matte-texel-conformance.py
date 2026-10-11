"""Check the raster oracle against exact translated PNG texels at scale 1:1.

Uses interior pixels with no geometric edge, scaling, rotation, or temporal
accumulation. Expectations come directly from the authored PNG bytes.
"""
import hashlib
import json
import math
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "backend/tests"))
from tests.temporal_matte_kernel_diagnostic import (  # noqa: E402
    expected_pixel,
    inverse,
    original_mask,
    point,
    worlds,
)

STUDY = ROOT / "docs/studios/research/editor-oss-20261002"
mask_file = STUDY / "temporal-matte-native14-manifest-capture-2/rig-external-alpha-normal/original-matte.png"
mask = Image.open(mask_file).convert("RGBA")
assert mask.tobytes() == original_mask().tobytes()
target, source = worlds(0, 0, "control", "external")
assert target == (1, 0, 0, 1, 45, 46)
assert source == (1, 0, 0, 1, 100, 74)
target_inverse, source_inverse = inverse(target), inverse(source)
cases = []
for inverted, folder in [(False, "temporal-matte-png-capture"), (True, "temporal-matte-png-capture-child-inverted")]:
    capture = STUDY / folder
    receipt = json.loads((capture / "receipt.json").read_text(encoding="utf-8"))
    png = capture / "center.png"
    center = next(record for record in receipt["records"] if record["name"] == "center")
    assert hashlib.sha256(png.read_bytes()).hexdigest() == center["pngSha256"]
    image = Image.open(png).convert("RGB")
    for x, y in [(138, 82), (140, 82), (138, 134), (108, 134), (142, 82)]:
        values = []
        texels = []
        for dx in range(2):
            for dy in range(2):
                world = (x + dx + .5, y + dy + .5)
                tx, ty = point(target_inverse, *world)
                assert 1 < tx < 169 and 1 < ty < 149, "No target-edge AA is involved"
                u, v = point(source_inverse, *world)
                assert 0 <= u < mask.width and 0 <= v < mask.height
                ix, iy = math.floor(u), math.floor(v)
                alpha = mask.getpixel((ix, iy))[3]
                texels.append({"x": ix, "y": iy, "alphaByte": alpha})
                coverage = .6 * alpha / 255
                values.append((1 - coverage if inverted else coverage) * .9 * .9 * .85 * 255)
        exact = sum(values) / 4
        observed = [sum(image.getpixel((x + dx, y + dy))[channel] for dx in range(2) for dy in range(2)) / 4
                    for channel in range(3)]
        old = expected_pixel(mask, 0, "control", "external", "alpha", inverted, x, y)
        cases.append({"invert": inverted, "x": x, "y": y, "texels": texels,
                      "exactTranslatedTexelChannel": exact, "existingOracleChannel": old,
                      "oracleMinusExactTexels": old - exact, "observedRgb": observed,
                      "observedMinusExactTexels": [channel - exact for channel in observed],
                      "capturePngSha256": center["pngSha256"]})
report = {"scope": "exact_1_to_1_translated_texel_conformance", "productionAdmission": "pending",
          "finding": "existing_oracle_integrates_texture_inside_pixels_and_broadens_identity_texel_boundaries",
          "geometricEdgePresent": False, "temporalAccumulationPresent": False,
          "maskSha256": hashlib.sha256(mask_file.read_bytes()).hexdigest(),
          "oracleSha256": hashlib.sha256((ROOT / "backend/tests/temporal_matte_kernel_diagnostic.py").read_bytes()).hexdigest(),
          "conformanceScriptSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "cases": cases}
assert max(abs(error) for case in cases for error in case["observedMinusExactTexels"]) < 2
assert max(abs(case["oracleMinusExactTexels"]) for case in cases) > 6
(STUDY / "temporal-matte-texel-conformance.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps({"cases": len(cases), "maximumObservedErrorAgainstExactTexels":
                  max(abs(error) for case in cases for error in case["observedMinusExactTexels"]),
                  "maximumOracleErrorAgainstExactTexels": max(abs(case["oracleMinusExactTexels"]) for case in cases)}))
