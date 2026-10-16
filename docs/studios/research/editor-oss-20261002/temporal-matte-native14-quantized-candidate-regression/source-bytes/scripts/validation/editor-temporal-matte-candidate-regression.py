"""Keep the exact historical regression verdicts and proposed contracts separate.

Candidate bytes come only from the completed source-frozen API experiment.
All production bytes are restored even when historical contracts fail. No
baseline receipt, historical test, or acceptance threshold is rewritten.
"""
import hashlib
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / "docs/studios/research/editor-oss-20261002"
API = STUDY / "temporal-matte-native14-balanced-vector-guard-svg-subtract-quantized-full"
OUT = STUDY / "temporal-matte-native14-quantized-candidate-regression"
assert not OUT.exists(), "Preserve previous regression evidence"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


baseline = read(STUDY / "temporal-matte-native13-current-sources.json")
assert all(sha(ROOT / name) == digest for name, digest in baseline["sources"].items())
api_sources, api_run = read(API / "sources.json"), read(API / "run.json")
assert api_run["exitCode"] == 0 and api_run["originalBytesRestored"]
assert api_sources["pixelReference"] == "swiftshader4_affine_png_v1"
api_cases = ET.parse(API / "tests.xml").findall(".//testcase")
assert len(api_cases) == 7 and all(not any(case.find(tag) is not None for tag in ["failure", "error", "skipped"])
                                for case in api_cases)
previous = ["spatial-effects-native12-render-tests.xml", "spatial-effects-native12-pure-regression-tests.xml",
            "spatial-effects-native12-native-regression-tests.xml"]
node_ids = sorted({case.attrib["classname"].replace("tests.", "tests/", 1) + ".py::" + case.attrib["name"]
                   for name in previous for case in ET.parse(STUDY / name).findall(".//testcase")})
assert len(node_ids) == 171
node_ids.append("tests/test_temporal_matte_oracle.py")
names = sorted(path.relative_to(API / "candidate-bytes").as_posix()
               for path in (API / "candidate-bytes").rglob("*") if path.is_file())
assert len(names) == 5
original = {name: (ROOT / name).read_bytes() for name in names}
candidate = {name: (API / "candidate-bytes" / name).read_bytes() for name in names}
assert all(sha(API / "candidate-bytes" / name) == api_sources["sources"][name] for name in names)
OUT.mkdir()
for kind, source in [("original-bytes", original), ("candidate-bytes", candidate)]:
    for name, raw in source.items():
        path = OUT / kind / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
run = {"historicalExitCode": None, "proposedContractsExitCode": None}
try:
    for name, raw in candidate.items():
        (ROOT / name).write_bytes(raw)
    freeze = set(baseline["sources"]) | set(api_sources["sources"]) | {
        "backend/tests/temporal_matte_candidate_contract_diagnostic.py",
        "scripts/validation/editor-temporal-matte-candidate-regression.py"}
    # Include every collected module, rather than just production code.
    freeze |= {"backend/" + node.split("::")[0] for node in node_ids}
    frozen = {name: sha(ROOT / name) for name in sorted(freeze)}
    for name in frozen:
        path = OUT / "source-bytes" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT / name).read_bytes())
    (OUT / "sources.json").write_text(json.dumps({"sources": frozen,
        "candidateApiSourcesSha256": sha(API / "sources.json"), "providerVersion": "4.0.527-native.14",
        "historicalSelectedUniqueCases": 171, "additionalHistoricalModule": "tests/test_temporal_matte_oracle.py",
        "productionAdmission": "pending"}, indent=2), encoding="utf-8")
    environment = dict(os.environ)
    for key, suffix in {"SPATIAL_EFFECTS_EVIDENCE_DIR": "spatial", "TEMPORAL_RIG_EVIDENCE_DIR": "rig",
                        "TEMPORAL_EXPOSURE_EVIDENCE_DIR": "exposure", "ASSET_MATTE_EVIDENCE_DIR": "matte",
                        "TYPOGRAPHY_EVIDENCE_DIR": "typography", "TEXT_LAYOUT_EVIDENCE_DIR": "layout",
                        "EDITOR_COMMAND_EVIDENCE_DIR": "command"}.items():
        environment[key] = str(OUT / suffix)
    environment.pop("TEMPORAL_MATTE_BASELINE", None)
    historical = subprocess.run([sys.executable, "-m", "pytest", *node_ids, "-q", "--tb=short",
        "--junitxml=" + str(OUT / "historical-tests.xml")], cwd=ROOT / "backend", env=environment, check=False)
    run["historicalExitCode"] = historical.returncode
    proposed = subprocess.run([sys.executable, "-m", "pytest", "tests/temporal_matte_candidate_contract_diagnostic.py",
        "-q", "--tb=short", "--junitxml=" + str(OUT / "proposed-contract-tests.xml")],
        cwd=ROOT / "backend", env=environment, check=False)
    run["proposedContractsExitCode"] = proposed.returncode
    assert all(sha(ROOT / name) == digest for name, digest in frozen.items()), "Source drift during regression"
finally:
    conflicts = [name for name in names if (ROOT / name).read_bytes() != candidate[name]]
    for name, raw in original.items():
        if name not in conflicts:
            (ROOT / name).write_bytes(raw)
    restored = not conflicts and all((ROOT / name).read_bytes() == raw for name, raw in original.items())
    run.update(originalBytesRestored=restored, conflictingConcurrentEdits=conflicts, productionAdmission="pending")
    (OUT / "run.json").write_text(json.dumps(run, indent=2), encoding="utf-8")
    assert restored, "Inspect concurrent edits without overwriting them"
print(json.dumps(run))
sys.exit(run["historicalExitCode"] or run["proposedContractsExitCode"])
