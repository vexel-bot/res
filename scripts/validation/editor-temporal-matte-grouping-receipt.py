"""Consolidate source-frozen grouping candidates without qualifying production."""
import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / "docs/studios/research/editor-oss-20261002"
MODES = ["svg-arithmetic-tree", "balanced-plus-lighter", "balanced-composition-opacity",
         "factored-plus-lighter", "factored-balanced-opacity"]
baseline = json.loads((STUDY / "temporal-matte-native13-current-sources.json").read_text(encoding="utf-8"))
assert all(hashlib.sha256((ROOT / file).read_bytes()).hexdigest() == digest
           for file, digest in baseline["sources"].items()), "Production source drift"
phases = []
for mode in MODES:
    directory = STUDY / ("temporal-matte-native14-" + mode)
    run = json.loads((directory / "run.json").read_text(encoding="utf-8"))
    assert run["originalBytesRestored"] and not run["conflictingConcurrentEdits"]
    frozen = json.loads((directory / "sources.json").read_text(encoding="utf-8"))
    for file in ["workers/remotion-benchmark/src/temporal-exposure.tsx",
                 "backend/app/domain/studios/temporal_exposure.py", "backend/app/providers/studios/remotion_render.py"]:
        assert hashlib.sha256((directory / "candidate-bytes" / file).read_bytes()).hexdigest() == frozen["sources"][file]
        assert hashlib.sha256((directory / "original-bytes" / file).read_bytes()).hexdigest() == baseline["sources"][file]
    xml = ET.parse(directory / "tests.xml")
    tests = [{"name": test.attrib["name"], "failed": test.find("failure") is not None,
              "errored": test.find("error") is not None, "skipped": test.find("skipped") is not None}
             for test in xml.findall(".//testcase")]
    assert len(tests) == 3 and not any(test["skipped"] or test["errored"] for test in tests)
    records = []
    for evidence_file in sorted(directory.glob("*/evidence.json")):
        evidence = json.loads(evidence_file.read_text(encoding="utf-8"))
        video = evidence_file.parent / "matte-exposure.mp4"
        checksum = hashlib.sha256(video.read_bytes()).hexdigest()
        assert checksum == evidence["renderResult"]["artifact"]["checksumSha256"]
        assert len(evidence["pixelChecks"]) == 168 and len(evidence["matrixChecks"]) == 6
        records.append({"variant": evidence["variant"], "measurementStatus": evidence["measurementStatus"],
                        "qc": evidence["renderResult"]["qualityEvaluation"]["status"],
                        "maximumChannelError": max(check["maximumChannelError"] for check in evidence["pixelChecks"]),
                        "failures": evidence["failures"], "pixelProbeCount": len(evidence["pixelChecks"]),
                        "videoSha256": checksum, "renderDurationMs": evidence["renderResult"]["renderDurationMs"],
                        "evidenceSha256": hashlib.sha256(evidence_file.read_bytes()).hexdigest()})
    analysis_file = directory / "failed-render-analysis.json"
    phases.append({"mode": mode, "run": run, "tests": tests, "records": records,
                   "prePixelFailureAnalysis": json.loads(analysis_file.read_text()) if analysis_file.exists() else None})
receipt = {"scope": "temporary_actual_API_grouping_experiments", "providerAfterExperiments": baseline["providerVersion"],
           "productionCombinedAdmission": "pending", "humanReview": "pending", "phases": phases,
           "sourceHashes": baseline["sources"],
           "consolidatorSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
(STUDY / "temporal-matte-grouping-experiments.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
print(json.dumps({"phases": len(phases), "testExecutions": sum(len(phase["tests"]) for phase in phases),
                  "retainedMeasuredVideos": sum(len(phase["records"]) for phase in phases),
                  "productionAdmission": receipt["productionCombinedAdmission"]}))
