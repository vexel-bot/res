"""Run paired baseline/candidate source-edge controls and restore the worker."""
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / "docs/studios/research/editor-oss-20261002"
OUT = STUDY / "temporal-matte-source-edge-controls"
CANDIDATE = STUDY / "temporal-matte-native14-balanced-padded-vector-guard-band"
baseline = json.loads((STUDY / "temporal-matte-native13-current-sources.json").read_text(encoding="utf-8"))
assert all(hashlib.sha256((ROOT / f).read_bytes()).hexdigest() == sha for f, sha in baseline["sources"].items())
assert not OUT.exists(), "Do not overwrite evidence"
names = ["workers/remotion-benchmark/src/asset-matte.tsx", "workers/remotion-benchmark/src/temporal-exposure.tsx"]
original = {f: (ROOT / f).read_bytes() for f in names}
candidate = {f: (CANDIDATE / "candidate-bytes" / f).read_bytes() for f in names}
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "backend/tests"))
from app.providers.studios.heavy_media_lease import heavy_media_lease  # noqa: E402
from tests.temporal_matte_kernel_diagnostic import original_mask  # noqa: E402

results = []
with heavy_media_lease("temporal_matte_source_edge_diagnostic", "source-edge-controls-20261003"):
    OUT.mkdir()
    shutil.copy2(STUDY / "temporal-matte-frame7-vector-guard/center.json", OUT / "base-manifest.json")
    shutil.copy2(STUDY / "temporal-matte-native14-manifest-capture-2/rig-external-alpha-normal/original-matte.png", OUT / "original.png")
    authored = original_mask()
    assert authored.tobytes() == Image.open(OUT / "original.png").convert("RGBA").tobytes()
    for alpha, name in [(128, "uniform50"), (255, "uniform255")]:
        Image.new("RGBA", (80, 96), (255, 255, 255, alpha)).save(OUT / (name + ".png"))
    whitened = Image.new("RGBA", (80, 96), (255, 255, 255, 0))
    for y in range(96):
        for x in range(80):
            whitened.putpixel((x, y), (255, 255, 255, authored.getpixel((x, y))[3]))
    whitened.save(OUT / "original-whitened.png")
    for f, raw in original.items():
        target = OUT / "original-bytes" / f
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    try:
        for phase, implementation in [("native13", original), ("vector-guard", candidate)]:
            for f, raw in implementation.items():
                (ROOT / f).write_bytes(raw)
            folder = OUT / phase
            folder.mkdir()
            frozen_files = set(baseline["sources"]) | {Path(__file__).relative_to(ROOT).as_posix(),
                "scripts/validation/editor-temporal-matte-source-edge-capture.mjs"}
            hashes = {}
            for f in sorted(frozen_files):
                raw = (ROOT / f).read_bytes()
                hashes[f] = hashlib.sha256(raw).hexdigest()
                target = folder / "source-bytes" / f
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
            (folder / "sources.json").write_text(json.dumps({"scope": "research_only_static_source_edge_controls",
                "phase": phase, "providerAndGateChanged": False, "sources": hashes}, indent=2), encoding="utf-8")
            with (folder / "capture.log").open("w", encoding="utf-8") as log:
                result = subprocess.run(["node", "scripts/validation/editor-temporal-matte-source-edge-capture.mjs", phase],
                                        cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=False)
            results.append({"phase": phase, "exitCode": result.returncode})
            assert result.returncode == 0, "Inspect diagnostic capture.log"
    finally:
        expected = candidate if any(r["phase"] == "vector-guard" for r in results) or (OUT / "vector-guard").exists() else original
        conflicts = [f for f in names if (ROOT / f).read_bytes() != expected[f]]
        for f, raw in original.items():
            if f not in conflicts:
                (ROOT / f).write_bytes(raw)
        restored = not conflicts and all((ROOT / f).read_bytes() == raw for f, raw in original.items())
        (OUT / "run.json").write_text(json.dumps({"phases": results, "originalBytesRestored": restored,
            "conflictingConcurrentEdits": conflicts, "providerAndGateChanged": False, "productionAdmission": "pending"}, indent=2), encoding="utf-8")
        assert restored, "Inspect conflicts; do not overwrite concurrent edits"
assert all(hashlib.sha256((ROOT / f).read_bytes()).hexdigest() == sha for f, sha in baseline["sources"].items())
print(json.dumps({"phases": len(results), "restored": True, "productionAdmission": "pending"}))
