"""Load saved worker bytes for clipped frame-zero paired PNG controls."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / "docs/studios/research/editor-oss-20261002"
OUT = STUDY / "temporal-matte-svg-subtract-uniform-controls"
CANDIDATE = STUDY / "temporal-matte-native14-balanced-vector-guard-svg-subtract-full"
baseline = json.loads((STUDY / "temporal-matte-native13-current-sources.json").read_text(encoding="utf-8"))
assert all(hashlib.sha256((ROOT / file).read_bytes()).hexdigest() == sha for file, sha in baseline["sources"].items())
assert not OUT.exists(), "Do not overwrite evidence"
names = ["workers/remotion-benchmark/src/asset-matte.tsx", "workers/remotion-benchmark/src/temporal-exposure.tsx"]
original = {file: (ROOT / file).read_bytes() for file in names}
candidate = {file: (CANDIDATE / "candidate-bytes" / file).read_bytes() for file in names}
sys.path.insert(0, str(ROOT / "backend"))
from app.providers.studios.heavy_media_lease import heavy_media_lease  # noqa: E402

result = None
with heavy_media_lease("temporal_matte_uniform_candidate_diagnostic", "svg-subtract-uniform-20261003"):
    assert not (STUDY / "temporal-matte-svg-subtract-uniform-control-sources.json").exists()
    # Capture creates its output directory after validation.
    for file, raw in original.items():
        target = STUDY / "temporal-matte-svg-subtract-uniform-source-archive" / "original-bytes" / file
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    try:
        for file, raw in candidate.items():
            (ROOT / file).write_bytes(raw)
        frozen_files = set(baseline["sources"]) | {
            Path(__file__).relative_to(ROOT).as_posix(), "scripts/validation/editor-temporal-matte-uniform-capture.mjs"}
        hashes = {}
        for file in sorted(frozen_files):
            raw = (ROOT / file).read_bytes()
            hashes[file] = hashlib.sha256(raw).hexdigest()
            target = STUDY / "temporal-matte-svg-subtract-uniform-source-archive" / "source-bytes" / file
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        (STUDY / "temporal-matte-svg-subtract-uniform-source-archive" / "sources.json").write_text(json.dumps({"scope": "research_only_partial_worker_candidate",
            "providerAndGateChanged": False, "productionAdmission": "pending", "sources": hashes}, indent=2), encoding="utf-8")
        (STUDY / "temporal-matte-svg-subtract-uniform-control-sources.json").write_text(json.dumps({"sources": hashes}, indent=2), encoding="utf-8")
        with (STUDY / "temporal-matte-svg-subtract-uniform-source-archive" / "capture.log").open("w", encoding="utf-8") as log:
            result = subprocess.run(["node", "scripts/validation/editor-temporal-matte-uniform-capture.mjs", "svg-subtract"],
                                    cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=False)
    finally:
        conflicts = [file for file in names if (ROOT / file).read_bytes() != candidate[file]]
        for file, raw in original.items():
            if file not in conflicts:
                (ROOT / file).write_bytes(raw)
        restored = not conflicts and all((ROOT / file).read_bytes() == raw for file, raw in original.items())
        (STUDY / "temporal-matte-svg-subtract-uniform-source-archive" / "run.json").write_text(json.dumps({"exitCode": result.returncode if result else None,
            "originalBytesRestored": restored, "conflictingConcurrentEdits": conflicts,
            "providerAndGateChanged": False, "productionAdmission": "pending"}, indent=2), encoding="utf-8")
        assert restored, "Inspect conflicts; do not overwrite concurrent edits"
assert all(hashlib.sha256((ROOT / file).read_bytes()).hexdigest() == sha for file, sha in baseline["sources"].items())
sys.exit(result.returncode)
