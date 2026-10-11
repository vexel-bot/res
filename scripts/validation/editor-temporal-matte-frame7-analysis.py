"""Locate the remaining frame-7 residual without changing its original oracle."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / "docs/studios/research/editor-oss-20261002"
OUT = STUDY / "temporal-matte-frame7-vector-guard"
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "backend/tests"))
from tests.temporal_matte_kernel_diagnostic import inverse, original_mask, point, raster_value, worlds  # noqa: E402

mask = original_mask()


def single_expected(sample, x, y):
    target, source = worlds(7, sample, "child", "external")
    target, source = inverse(target), inverse(source)
    value = 0
    for px in range(2):
        for py in range(2):
            content = matte = 0
            for dx in range(8):
                for dy in range(8):
                    wx, wy = x + px + (dx + .5) / 8, y + py + (dy + .5) / 8
                    tx, ty = point(target, wx, wy)
                    if not (0 <= tx < 170 and 0 <= ty < 150):
                        continue
                    content += 1
                    matte += 1 - raster_value(mask, *point(source, wx, wy), "alpha") * (.6 + .3 * 7 / 8)
            value += content / 64 * matte / 64 * .9 * .9 * .85 * 255
    return value / 4


def observed(image, x, y):
    return [sum(image.getpixel((x + dx, y + dy))[c] for dx in range(2) for dy in range(2)) / 4 for c in range(3)]


def main():
    receipt = json.loads((OUT / "receipt.json").read_text(encoding="utf-8"))
    run = json.loads((OUT / "run.json").read_text(encoding="utf-8"))
    assert run["originalBytesRestored"] and run["exitCode"] == 0
    frozen = json.loads((OUT / "sources.json").read_text(encoding="utf-8"))
    for file, checksum in frozen["sources"].items():
        assert hashlib.sha256((OUT / "candidate-source-bytes" / file).read_bytes()).hexdigest() == checksum
    images = {}
    for record in receipt["records"]:
        png = OUT / (record["name"] + ".png")
        manifest = OUT / (record["name"] + ".json")
        assert hashlib.sha256(png.read_bytes()).hexdigest() == record["pngSha256"]
        assert hashlib.sha256(manifest.read_bytes()).hexdigest() == record["manifestSha256"]
        images[record["name"]] = Image.open(png).convert("RGB")
    folder = STUDY / "temporal-matte-native14-balanced-padded-vector-guard-band/child-external-alpha-inverted"
    evidence = json.loads((folder / "evidence.json").read_text(encoding="utf-8"))
    video = folder / "matte-exposure.mp4"
    assert hashlib.sha256(video.read_bytes()).hexdigest() == evidence["renderResult"]["artifact"]["checksumSha256"]
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-vf", "select=eq(n\\,7)",
                          "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"],
                         check=True, capture_output=True, timeout=30).stdout
    assert len(raw) == 320 * 320 * 3
    comparisons = []
    for x, y in [(150, 184), (180, 204), (162, 92)]:
        isolated = []
        for record in receipt["records"]:
            if record["name"] == "temporal":
                continue
            rgb = observed(images[record["name"]], x, y)
            expected = single_expected(record["sampleTime"], x, y)
            target, source = worlds(7, record["sampleTime"], "child", "external")
            isolated.append({"name": record["name"], "time": record["sampleTime"], "expectedChannel": expected,
                             "observedRgb": rgb, "maximumChannelError": max(abs(c - expected) for c in rgb),
                             "targetLocalPixelCenter": point(inverse(target), x + 1, y + 1),
                             "sourceLocalPixelCenter": point(inverse(source), x + 1, y + 1)})
        samples = [r for r in isolated if r["name"] != "center"]
        average = [sum(r["observedRgb"][c] for r in samples) / 8 for c in range(3)]
        temporal = observed(images["temporal"], x, y)
        expected = sum(r["expectedChannel"] for r in samples) / 8
        mp4 = [sum(raw[((y + dy) * 320 + x + dx) * 3 + c] for dx in range(2) for dy in range(2)) / 4 for c in range(3)]
        comparisons.append({"x": x, "y": y, "expectedChannel": expected, "temporalPngRgb": temporal,
                            "averageIsolatedRgb": average, "retainedApiMp4Rgb": mp4,
                            "temporalMinusIsolated": [a - b for a, b in zip(temporal, average, strict=True)],
                            "isolated": isolated})
    report = {"scope": "research_only_frame7_residual_lossless_diagnostic", "productionAdmission": "pending",
              "originalOracleChanged": False, "scriptSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "captureReceiptSha256": hashlib.sha256((OUT / "receipt.json").read_bytes()).hexdigest(), "comparisons": comparisons}
    (OUT / "analysis.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps([{k: v for k, v in item.items() if k != "isolated"} for item in comparisons]))


if __name__ == "__main__":
    main()
