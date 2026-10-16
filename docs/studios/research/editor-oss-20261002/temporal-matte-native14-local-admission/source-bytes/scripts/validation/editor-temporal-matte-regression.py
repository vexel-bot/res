"""Replay the exact earlier qualified test set against current runtime bytes."""
import hashlib
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / "docs/studios/research/editor-oss-20261002"
previous = ["spatial-effects-native12-render-tests.xml", "spatial-effects-native12-pure-regression-tests.xml",
            "spatial-effects-native12-native-regression-tests.xml"]
node_ids = sorted({case.attrib["classname"].replace("tests.", "tests/", 1)+".py::"+case.attrib["name"]
                   for name in previous for case in ET.parse(DIRECTORY / name).findall(".//testcase")})
assert len(node_ids) == 171
node_ids.append("tests/test_temporal_matte_oracle.py")
old_sources = json.loads((DIRECTORY / "spatial-effects-native12-sources.json").read_text(encoding="utf-8"))["sources"]
names = sorted(set(old_sources) | {"workers/remotion-benchmark/src/asset-matte.tsx",
    "backend/app/domain/studios/temporal_exposure.py", "backend/tests/temporal_matte_kernel_diagnostic.py",
    "backend/tests/test_temporal_matte_oracle.py", "scripts/validation/editor-temporal-matte-regression.py"})
sources = {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in names}
(DIRECTORY / "temporal-matte-native13-current-sources.json").write_text(json.dumps({
    "providerVersion": "4.0.527-native.13", "combinedAdmission": "pending", "sources": sources}, indent=2), encoding="utf-8")
environment = dict(os.environ)
for key, suffix in {"SPATIAL_EFFECTS_EVIDENCE_DIR": "spatial", "TEMPORAL_RIG_EVIDENCE_DIR": "rig",
                    "TEMPORAL_EXPOSURE_EVIDENCE_DIR": "exposure", "ASSET_MATTE_EVIDENCE_DIR": "matte",
                    "TYPOGRAPHY_EVIDENCE_DIR": "typography", "TEXT_LAYOUT_EVIDENCE_DIR": "layout",
                    "EDITOR_COMMAND_EVIDENCE_DIR": "command"}.items():
    environment[key] = str(DIRECTORY / ("temporal-matte-native13-regression-"+suffix))
environment.pop("TEMPORAL_MATTE_BASELINE", None)
command = [sys.executable, "-m", "pytest", *node_ids, "-q", "--tb=short",
           "--junitxml="+str(DIRECTORY / "temporal-matte-native13-regression-tests.xml")]
result = subprocess.run(command, cwd=ROOT/"backend", env=environment, check=False)
assert all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == digest for name, digest in sources.items())
(DIRECTORY / "temporal-matte-native13-regression-run.json").write_text(json.dumps({
    "selectedPriorUniqueCases": 171, "addedModule": "tests/test_temporal_matte_oracle.py",
    "exitCode": result.returncode, "sourceDrift": False}, indent=2), encoding="utf-8")
sys.exit(result.returncode)
