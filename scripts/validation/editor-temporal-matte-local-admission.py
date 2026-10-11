"""Incorporate only the sealed candidate and its nine explicit contract updates."""
import ast
import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.providers.studios.heavy_media_lease import heavy_media_lease  # noqa: E402

STUDY = ROOT / "docs/studios/research/editor-oss-20261002"
API = STUDY / "temporal-matte-native14-balanced-vector-guard-svg-subtract-quantized-full"
REGRESSION = STUDY / "temporal-matte-native14-quantized-candidate-regression"
EXPOSURE = STUDY / "temporal-matte-native14-quantized-exposure-regression"
OUT = STUDY / "temporal-matte-native14-local-admission"
assert not OUT.exists(), "Do not repeat or overwrite local admission"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


qualification_path = STUDY / "temporal-matte-quantized-qualification.json"
qualification = read(qualification_path)
assert qualification["qualification"] == "fixture_specific_technical_ready_for_local_incorporation"
assert qualification["newApiCasesPassed"] == 7 and qualification["historicalUnchangedCasesPassed"] == 179
assert len(qualification["newContractCases"]) == 9 and all(case["status"] == "passed"
                                                         for case in qualification["newContractCases"])
for name, checksum in qualification["proofHashes"].items():
    assert sha(STUDY / name) == checksum
baseline = read(STUDY / "temporal-matte-native13-current-sources.json")
assert all(sha(ROOT / name) == digest for name, digest in baseline["sources"].items())
candidate = {path.relative_to(API / "candidate-bytes").as_posix(): path.read_bytes()
             for path in (API / "candidate-bytes").rglob("*") if path.is_file()}
runtime_names = sorted(candidate)
assert len(candidate) == 5
api_sources = read(API / "sources.json")["sources"]
assert all(hashlib.sha256(raw).hexdigest() == api_sources[name] for name, raw in candidate.items())
test_quality = "backend/tests/test_contextual_encode_quality.py"
old_quality = (ROOT / test_quality).read_bytes()
assert old_quality.count(b'("high", "14")') == old_quality.count(b'"1.4.0"') == 1
candidate[test_quality] = old_quality.replace(b'("high", "14")', b'("high", "10")').replace(b'"1.4.0"', b'"1.4.1"')
test_render = "backend/tests/test_temporal_exposure_render.py"
candidate[test_render] = (EXPOSURE / "candidate-bytes" / test_render).read_bytes()
assert (ROOT / test_render).read_bytes() == (EXPOSURE / "original-bytes" / test_render).read_bytes()
test_exposure = "backend/tests/test_temporal_exposure.py"
old_exposure = (ROOT / test_exposure).read_text(encoding="utf-8")
proposed_path = ROOT / "backend/tests/temporal_matte_candidate_contract_diagnostic.py"
proposed = proposed_path.read_text(encoding="utf-8")
assert sha(proposed_path) == read(REGRESSION / "sources.json")["sources"][proposed_path.relative_to(ROOT).as_posix()]
old_tree, proposed_tree = ast.parse(old_exposure), ast.parse(proposed)
old_name = "test_matte_under_moving_external_parent_requires_exposing_its_rig"
new_name = "test_matte_under_moving_external_parent_uses_center_frame_ancestors"
old_function = next(node for node in old_tree.body if isinstance(node, ast.FunctionDef) and node.name == old_name)
proposed_function = next(node for node in proposed_tree.body if isinstance(node, ast.FunctionDef) and
                         node.name == "test_candidate_matte_under_moving_external_parent_compiles_at_both_scopes")
lines = old_exposure.splitlines(keepends=True)
replacement = "".join(proposed.splitlines(keepends=True)[proposed_function.lineno - 1:proposed_function.end_lineno])
replacement = replacement.replace(proposed_function.name, new_name, 1)
new_exposure = "".join(lines[:old_function.lineno - 1]) + replacement + "\n" + "".join(lines[old_function.end_lineno:])
# Prove that the revision changes only this contract test, not any negative,
# hold, policy, cycle, nested-exposure or legacy assertion in the module.
def other_functions(source, excluded):
    tree = ast.parse(source)
    tree.body = [node for node in tree.body if not (isinstance(node, ast.FunctionDef) and node.name == excluded)]
    return ast.dump(tree, include_attributes=False)


assert other_functions(old_exposure, old_name) == other_functions(new_exposure, new_name)
candidate[test_exposure] = new_exposure.encode("utf-8")
original = {name: (ROOT / name).read_bytes() for name in candidate}
regression_sources = read(REGRESSION / "sources.json")["sources"]
assert all(sha(ROOT / name) == regression_sources[name] for name in [test_quality, test_render, test_exposure])
OUT.mkdir()
for kind, data in [("original-bytes", original), ("admitted-bytes", candidate)]:
    for name, raw in data.items():
        file = OUT / kind / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(raw)
with heavy_media_lease("editor_source_admission", "native14-quantized-local-admission"):
    assert all((ROOT / name).read_bytes() == raw for name, raw in original.items()), "Concurrent local edit"
    for name, raw in candidate.items():
        (ROOT / name).write_bytes(raw)
    assert all((ROOT / name).read_bytes() == raw for name, raw in candidate.items())
sources = {name: sha(ROOT / name) for name in sorted(set(regression_sources) | set(candidate) | {
    "scripts/validation/editor-temporal-matte-local-admission.py",
    "scripts/validation/editor-temporal-matte-quantized-qualification.py"})}
for name in sources:
    file = OUT / "source-bytes" / name
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_bytes((ROOT / name).read_bytes())
record = {"schemaVersion": "res.temporal-matte-local-admission.v1", "admittedAt": datetime.now(UTC).isoformat(),
          "providerVersion": "4.0.527-native.14", "contextualFinalizerVersion": "1.4.1", "highCrf": 10,
          "technicalAdmission": "fixture_specific", "humanReview": "pending", "autonomy": "pending",
          "qualificationSha256": sha(qualification_path), "runtimeSourcesIdenticalToQualifiedCandidate": True,
          "runtimeSourceNames": runtime_names, "changedFiles": sorted(candidate), "sources": sources,
          "historicalDiagnosticUnchanged": sha(ROOT / "backend/tests/temporal_matte_kernel_diagnostic.py") ==
              baseline["sources"]["backend/tests/temporal_matte_kernel_diagnostic.py"],
          "historicalVerdictsPreserved": True, "schemasChanged": [], "sqlMigrationRequired": False,
          "cleanupPreviouslyRejected": True, "cleanupBypassAttempted": False, "currentContractTests": "pending"}
assert record["historicalDiagnosticUnchanged"]
(OUT / "admission.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
result = subprocess.run([sys.executable, "-m", "pytest", "tests/test_contextual_encode_quality.py",
    "tests/test_temporal_exposure.py::" + new_name, "-q", "--tb=short",
    "--junitxml=" + str(OUT / "current-contract-tests.xml")], cwd=ROOT / "backend", check=False)
assert all(sha(ROOT / name) == checksum for name, checksum in sources.items()), "Post-admission source drift"
record["currentContractTests"] = "passed" if result.returncode == 0 else "failed"
record["currentContractTestsExitCode"] = result.returncode
(OUT / "admission.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
print(json.dumps({key: record[key] for key in ["providerVersion", "contextualFinalizerVersion", "highCrf",
    "technicalAdmission", "historicalDiagnosticUnchanged", "currentContractTests"]}))
sys.exit(result.returncode)
