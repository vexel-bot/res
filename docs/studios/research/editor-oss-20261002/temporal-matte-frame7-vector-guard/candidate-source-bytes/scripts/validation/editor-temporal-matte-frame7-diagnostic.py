"""Temporarily load saved worker candidates for an isolated PNG diagnostic."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / "docs/studios/research/editor-oss-20261002"
OUT = STUDY / "temporal-matte-frame7-vector-guard"
CANDIDATE = STUDY / "temporal-matte-native14-balanced-padded-vector-guard-band"
baseline = json.loads((STUDY / "temporal-matte-native13-current-sources.json").read_text(encoding="utf-8"))
assert all(hashlib.sha256((ROOT / f).read_bytes()).hexdigest() == sha for f, sha in baseline["sources"].items())
assert not OUT.exists(), "Do not overwrite evidence"
names = ["workers/remotion-benchmark/src/asset-matte.tsx", "workers/remotion-benchmark/src/temporal-exposure.tsx"]
original = {f: (ROOT / f).read_bytes() for f in names}
candidate = {f: (CANDIDATE / "candidate-bytes" / f).read_bytes() for f in names}
sys.path.insert(0, str(ROOT / "backend"))
from app.providers.studios.heavy_media_lease import heavy_media_lease  # noqa: E402

result = None
with heavy_media_lease("temporal_matte_frame7_diagnostic", "frame7-vector-guard-20261003"):
    OUT.mkdir()
    for f, raw in original.items():
        target = OUT / "original-bytes" / f
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    try:
        for f, raw in candidate.items():
            (ROOT / f).write_bytes(raw)
        frozen_files = set(baseline["sources"]) | {
            Path(__file__).relative_to(ROOT).as_posix(), "scripts/validation/editor-temporal-matte-frame7-capture.mjs"}
        hashes = {}
        for f in sorted(frozen_files):
            raw = (ROOT / f).read_bytes()
            hashes[f] = hashlib.sha256(raw).hexdigest()
            target = OUT / "candidate-source-bytes" / f
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        (OUT / "sources.json").write_text(json.dumps({"scope": "research_only_partial_worker_candidate",
            "providerAndGateChanged": False, "productionAdmission": "pending", "sources": hashes}, indent=2), encoding="utf-8")
        with (OUT / "capture.log").open("w", encoding="utf-8") as log:
            result = subprocess.run(["node", "scripts/validation/editor-temporal-matte-frame7-capture.mjs"],
                                    cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=False)
    finally:
        conflicts = [f for f in names if (ROOT / f).read_bytes() != candidate[f]]
        for f, raw in original.items():
            if f not in conflicts:
                (ROOT / f).write_bytes(raw)
        restored = not conflicts and all((ROOT / f).read_bytes() == raw for f, raw in original.items())
        (OUT / "run.json").write_text(json.dumps({"exitCode": result.returncode if result else None,
            "originalBytesRestored": restored, "conflictingConcurrentEdits": conflicts,
            "providerAndGateChanged": False, "productionAdmission": "pending"}, indent=2), encoding="utf-8")
        assert restored, "Inspect conflicts; do not overwrite concurrent edits"
assert all(hashlib.sha256((ROOT / f).read_bytes()).hexdigest() == sha for f, sha in baseline["sources"].items())
sys.exit(result.returncode)
