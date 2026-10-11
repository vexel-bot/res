"""Full-image direct/source-mask conformance at the retained affine pose."""
import hashlib
import importlib.util
import json
import math
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / "docs/studios/research/editor-oss-20261002"
FOLDER = STUDY / "temporal-matte-source-edge-controls/svg-subtract"
reference_path = ROOT / "scripts/validation/editor-temporal-matte-quantized-reference.py"
spec = importlib.util.spec_from_file_location("independent_quantized_reference", reference_path)
reference = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reference)

receipt = json.loads((FOLDER / "receipt.json").read_text(encoding="utf-8"))
selected = {"normal-original": ("original", False, False), "inverse-original": ("original", True, False),
            "normal-uniform": ("uniform50", False, False), "inverse-uniform": ("uniform50", True, False),
            "direct-original-whitened": ("original-whitened", False, True),
            "direct-uniform50": ("uniform50", False, True), "direct-uniform255": ("uniform255", False, True)}
records = []
for record in receipt["records"]:
    if record["name"] not in selected:
        continue
    image_name, inverted, direct = selected[record["name"]]
    mask_path = FOLDER.parent / (image_name + ".png")
    mask = Image.open(mask_path).convert("RGBA")
    png = FOLDER / (record["name"] + ".png")
    assert hashlib.sha256(png.read_bytes()).hexdigest() == record["pngSha256"]
    assert hashlib.sha256(mask_path.read_bytes()).hexdigest() == record["imageSha256"]
    image = Image.open(png).convert("RGB")
    checks, maxima, count, squared = [], 0, 0, 0
    # Every output pixel, including outside the source and target, is checked.
    for y in range(320):
        for x in range(320):
            expected = (reference.source_channel(mask, 7, 7, "control", "external", "alpha", x, y) if direct
                        else reference.single_channel(mask, 7, 7, "control", "external", "alpha", inverted, x, y))
            observed = image.getpixel((x, y))
            error = max(abs(channel - expected) for channel in observed)
            maxima = max(maxima, error)
            count += 1
            squared += error ** 2
            if error:
                checks.append({"x": x, "y": y, "expectedChannel": expected, "observedRgb": observed, "maximumChannelError": error})
    records.append({"name": record["name"], "pixelCount": count, "maximumError": maxima,
                    "rmsError": math.sqrt(squared / count), "worstPixels": sorted(checks, key=lambda check: check["maximumChannelError"], reverse=True)[:10],
                    "failedProbesAtOriginalThreshold": [check for check in checks if check["maximumChannelError"] >= 8]})
report = {"scope": "retained_affine_textured_source_full_pixel_conformance", "productionAdmission": "pending", "originalOracleChanged": False,
          "referenceScriptSha256": hashlib.sha256(reference_path.read_bytes()).hexdigest(),
          "rasterReferenceSha256": hashlib.sha256((ROOT / "scripts/validation/editor-temporal-matte-quad-raster-reference.py").read_bytes()).hexdigest(),
          "scriptSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "records": records}
(STUDY / "temporal-matte-textured-source-conformance.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps([{key: value for key, value in record.items() if key not in {"worstPixels", "failedProbesAtOriginalThreshold"}} for record in records]))
