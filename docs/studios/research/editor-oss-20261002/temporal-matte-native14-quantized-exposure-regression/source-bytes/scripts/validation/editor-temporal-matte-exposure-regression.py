"""Replay exposure pixels with the declared new encode receipt, preserving history.

Only the historical test's metadata expectation changes from CRF14 to CRF10.
Every authored fixture, pixel/phase assertion, tolerance and probe stays exact.
Six original files are archived and restored; no test failure is suppressed.
"""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / "docs/studios/research/editor-oss-20261002"
API = STUDY / "temporal-matte-native14-balanced-vector-guard-svg-subtract-quantized-full"
PREVIOUS = STUDY / "temporal-matte-native14-quantized-candidate-regression"
OUT = STUDY / "temporal-matte-native14-quantized-exposure-regression"
assert not OUT.exists()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


baseline = read(STUDY / "temporal-matte-native13-current-sources.json")
assert all(sha(ROOT / name) == digest for name, digest in baseline["sources"].items())
assert read(PREVIOUS / "run.json")["originalBytesRestored"]
api_sources = read(API / "sources.json")["sources"]
candidate = {path.relative_to(API / "candidate-bytes").as_posix(): path.read_bytes()
             for path in (API / "candidate-bytes").rglob("*") if path.is_file()}
assert len(candidate) == 5 and all(hashlib.sha256(raw).hexdigest() == api_sources[name]
                                 for name, raw in candidate.items())
test_name = "backend/tests/test_temporal_exposure_render.py"
test_original = (ROOT / test_name).read_bytes()
assert sha(ROOT / test_name) == read(PREVIOUS / "sources.json")["sources"][test_name]
before, after = b'assert checks["audiovisual"]["videoCrf"] == 14', b'assert checks["audiovisual"]["videoCrf"] == 10'
assert test_original.count(before) == 1
candidate[test_name] = test_original.replace(before, after)
original = {name: (ROOT / name).read_bytes() for name in candidate}
OUT.mkdir()
for kind, data in [("original-bytes", original), ("candidate-bytes", candidate)]:
    for name, raw in data.items():
        path = OUT / kind / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
result = None
try:
    for name, raw in candidate.items():
        (ROOT / name).write_bytes(raw)
    names = set(read(PREVIOUS / "sources.json")["sources"]) | {
        "scripts/validation/editor-temporal-matte-exposure-regression.py"}
    frozen = {name: sha(ROOT / name) for name in sorted(names)}
    for name in frozen:
        path = OUT / "source-bytes" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT / name).read_bytes())
    (OUT / "sources.json").write_text(json.dumps({"sources": frozen, "providerVersion": "4.0.527-native.14",
        "testExpectationChange": "Only audiovisual receipt videoCrf:14 to videoCrf:10",
        "authoredInputsProbesAndToleranceChanged": False, "productionAdmission": "pending"}, indent=2), encoding="utf-8")
    environment = dict(os.environ, TEMPORAL_EXPOSURE_EVIDENCE_DIR=str(OUT / "exposure"), TEMPORAL_EXPOSURE_POLICY="centered")
    result = subprocess.run([sys.executable, "-m", "pytest",
        "tests/test_temporal_exposure_render.py::test_temporal_exposure_actual_api_measurement", "-q", "--tb=short",
        "--junitxml=" + str(OUT / "tests.xml")], cwd=ROOT / "backend", env=environment, check=False)
    assert all(sha(ROOT / name) == digest for name, digest in frozen.items()), "Source drift during exposure regression"
finally:
    conflicts = [name for name in candidate if (ROOT / name).read_bytes() != candidate[name]]
    for name, raw in original.items():
        if name not in conflicts:
            (ROOT / name).write_bytes(raw)
    restored = not conflicts and all((ROOT / name).read_bytes() == raw for name, raw in original.items())
    (OUT / "run.json").write_text(json.dumps({"exitCode": result.returncode if result else None,
        "originalBytesRestored": restored, "conflictingConcurrentEdits": conflicts, "productionAdmission": "pending"},
        indent=2), encoding="utf-8")
    assert restored, "Inspect concurrent edits without overwriting them"
sys.exit(result.returncode)
