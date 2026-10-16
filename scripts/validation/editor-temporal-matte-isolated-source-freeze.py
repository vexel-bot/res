"""Freeze source bytes for the isolated-sample diagnostic already rendered."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / "docs/studios/research/editor-oss-20261002"
FOLDER = STUDY / "temporal-matte-isolated-samples"
paths = [
    "workers/remotion-benchmark/src/hybrid.tsx",
    "workers/remotion-benchmark/src/asset-matte.tsx",
    "workers/remotion-benchmark/src/temporal-exposure.tsx",
    "workers/remotion-benchmark/render-hybrid.mjs",
    "scripts/validation/editor-temporal-matte-isolated-samples.mjs",
    "scripts/validation/editor-temporal-matte-isolated-analysis.py",
]
sources = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in paths}
receipt = json.loads((FOLDER / "receipt.json").read_text(encoding="utf-8"))
freeze = {
    "scope": "isolated_single_sample_raster_diagnostic",
    "productionAdmission": "pending",
    "sourceManifestSha256": receipt["sourceManifestSha256"],
    "maskSha256": receipt["maskSha256"],
    "sources": sources,
    "renderRecords": receipt["records"],
    "humanReview": "pending",
}
(FOLDER / "source-freeze.json").write_text(json.dumps(freeze, indent=2), encoding="utf-8")
print(json.dumps({"sources": len(sources), "records": len(receipt["records"]), "folder": str(FOLDER)}))
