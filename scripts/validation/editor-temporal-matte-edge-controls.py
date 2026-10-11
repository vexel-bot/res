"""Research-only paired masked/unmasked captures; no production qualification."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "backend/tests"))
from tests.temporal_matte_kernel_diagnostic import inverse, point, worlds  # noqa: E402

STUDY = ROOT / "docs/studios/research/editor-oss-20261002"
NAMES = ["center", *[f"sample-{i}" for i in range(1, 9)]]
TIMES = [0, *[(i + .5) / 8 * .25 for i in range(8)]]


def captures(fixture):
    folder = STUDY / ("temporal-matte-png-capture-" + fixture)
    receipt = json.loads((folder / "receipt.json").read_text(encoding="utf-8"))
    result = {}
    for record in receipt["records"]:
        file = folder / (record["name"] + ".png")
        assert hashlib.sha256(file.read_bytes()).hexdigest() == record["pngSha256"]
        result[record["name"]] = Image.open(file).convert("RGB")
    return result, receipt


def coverage(sample, x, y, grid=64):
    target, source = worlds(0, sample, "child", "external")
    target, source = inverse(target), inverse(source)
    value = squared = 0
    for px in range(2):
        for py in range(2):
            inside = 0
            for dx in range(grid):
                for dy in range(grid):
                    wx, wy = x + px + (dx + .5) / grid, y + py + (dy + .5) / grid
                    sx, sy = point(source, wx, wy)
                    assert not (0 <= sx < 80 and 0 <= sy < 96), "probe_intersects_bitmap"
                    tx, ty = point(target, wx, wy)
                    inside += int(0 <= tx < 170 and 0 <= ty < 150)
            c = inside / grid ** 2
            value += c
            squared += c * c
    return value / 4 * .9 * .9 * .85 * 255, squared / 4 * .9 * .9 * .85 * 255


def observed(image, x, y):
    return [sum(image.getpixel((x + dx, y + dy))[channel]
                for dx in range(2) for dy in range(2)) / 4 for channel in range(3)]


def main():
    masked, masked_receipt = captures("child-inverted")
    unmasked, unmasked_receipt = captures("child-unmasked")
    for source, checksum in masked_receipt["sourceHashes"].items():
        if source.startswith("workers/"):
            assert unmasked_receipt["sourceHashes"][source] == checksum
    # Rebuild only the removed matte property and compare the byte-exact
    # JavaScript serialization with the earlier masked manifest receipt.
    canonical = STUDY / "temporal-matte-native14-manifest-capture-2/rig-external-alpha-normal/canonical-manifest.json"
    program = """const fs=require('fs'),crypto=require('crypto');
const canonical=JSON.parse(fs.readFileSync(process.argv[1]));
const dir=process.argv[2];const receipt=JSON.parse(fs.readFileSync(dir+'/receipt.json'));
const result=receipt.records.map(r=>{const m=JSON.parse(fs.readFileSync(dir+'/'+r.name+'.json'));
const authored=r.name==='temporal'?canonical:JSON.parse(fs.readFileSync(process.argv[3]+'/'+r.name+'.json'));
const hero=m.layers.find(l=>l.name==='hero'),original=authored.layers.find(l=>l.name==='hero').properties;
const ordered={};for(const key of Object.keys(original)){
ordered[key]=key==='recipeAssetMatte'?{...original[key],invert:true}:hero.properties[key];}
for(const key of Object.keys(hero.properties))if(!(key in ordered))ordered[key]=hero.properties[key];
hero.properties=ordered;
return {name:r.name,sha256:crypto.createHash('sha256').update(JSON.stringify(m)).digest('hex')};});
process.stdout.write(JSON.stringify(result));"""
    paired = json.loads(subprocess.run(["node", "-e", program, str(canonical),
                                       str(STUDY / "temporal-matte-png-capture-child-unmasked"),
                                       str(STUDY / "temporal-matte-isolated-samples")],
                                      capture_output=True, text=True, check=True, timeout=10).stdout)
    for record in paired:
        assert record["sha256"] == next(r["manifestSha256"] for r in masked_receipt["records"]
                                        if r["name"] == record["name"]), "paired_manifest_transform_drift"
    checks = []
    for name, sample in zip(NAMES, TIMES, strict=True):
        for x, y in [(214, 96), (44, 96), (94, 46)]:
            exact, squared = coverage(sample, x, y)
            a, b = observed(masked[name], x, y), observed(unmasked[name], x, y)
            checks.append({"sample": name, "time": sample, "x": x, "y": y,
                           "maskedRgb": a, "unmaskedRgb": b,
                           "maskedMinusUnmasked": [av - bv for av, bv in zip(a, b, strict=True)],
                           "geometricCoverageChannel": exact, "squaredCoverageChannel": squared,
                           "unmaskedGeometricError": max(abs(v - exact) for v in b),
                           "maskedSquaredError": max(abs(v - squared) for v in a)})
    temporal = []
    for x, y in [(214, 96), (44, 96), (94, 46)]:
        a, b = observed(masked["temporal"], x, y), observed(unmasked["temporal"], x, y)
        temporal.append({"x": x, "y": y, "maskedRgb": a, "unmaskedRgb": b,
                         "maskedMinusUnmasked": [av - bv for av, bv in zip(a, b, strict=True)]})
    report = {"scope": "research_only_mask_edge_control", "productionAdmission": "pending",
              "grid": 64, "bitmapIntersectionAtProbes": False,
              "pairedManifestHashesMatched": len(paired),
              "scriptSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "maskedReceipt": masked_receipt, "unmaskedReceipt": unmasked_receipt,
              "maximumMaskedUnmaskedDifference": max(abs(v) for c in checks for v in c["maskedMinusUnmasked"]),
              "maximumUnmaskedGeometricError": max(c["unmaskedGeometricError"] for c in checks),
              "checks": checks, "temporalChecks": temporal}
    (STUDY / "temporal-matte-edge-controls.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ["maximumMaskedUnmaskedDifference", "maximumUnmaskedGeometricError", "temporalChecks"]}))


if __name__ == "__main__":
    main()
