"""Verify frozen edge experiments without promoting or rewriting old receipts."""
import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / "docs/studios/research/editor-oss-20261002"
MODES = ["padded-mask-viewport", "balanced-inverted-padded-rect", "balanced-mask-guard-band"]
baseline = json.loads((STUDY / "temporal-matte-native13-current-sources.json").read_text(encoding="utf-8"))
assert all(hashlib.sha256((ROOT / file).read_bytes()).hexdigest() == digest
           for file, digest in baseline["sources"].items()), "production_source_drift"
phases = []
for mode in MODES:
    directory = STUDY / ("temporal-matte-native14-" + mode)
    run = json.loads((directory / "run.json").read_text(encoding="utf-8"))
    assert run["originalBytesRestored"] and not run["conflictingConcurrentEdits"]
    frozen = json.loads((directory / "sources.json").read_text(encoding="utf-8"))
    for original in (directory / "original-bytes").rglob("*"):
        if not original.is_file():
            continue
        file = original.relative_to(directory / "original-bytes").as_posix()
        assert hashlib.sha256(original.read_bytes()).hexdigest() == baseline["sources"][file]
        assert hashlib.sha256((directory / "candidate-bytes" / file).read_bytes()).hexdigest() == frozen["sources"][file]
    tests = [{"name": t.attrib["name"], "failed": t.find("failure") is not None,
              "errored": t.find("error") is not None, "skipped": t.find("skipped") is not None}
             for t in ET.parse(directory / "tests.xml").findall(".//testcase")]
    assert len(tests) == 3 and not any(t["skipped"] or t["errored"] for t in tests)
    records = []
    for file in sorted(directory.glob("*/evidence.json")):
        evidence = json.loads(file.read_text(encoding="utf-8"))
        checksum = hashlib.sha256((file.parent / "matte-exposure.mp4").read_bytes()).hexdigest()
        assert checksum == evidence["renderResult"]["artifact"]["checksumSha256"]
        assert len(evidence["pixelChecks"]) == 168 and len(evidence["matrixChecks"]) == 6
        assert evidence["renderResult"]["qualityEvaluation"]["status"] == "passed"
        assert max(c["maximumError"] for c in evidence["matrixChecks"]) < .002
        records.append({"variant": evidence["variant"], "qc": "passed",
                        "measurementStatus": evidence["measurementStatus"],
                        "maximumChannelError": max(c["maximumChannelError"] for c in evidence["pixelChecks"]),
                        "maximumFrameZeroError": max(c["maximumChannelError"] for c in evidence["pixelChecks"] if c["frame"] == 0),
                        "maximumHoldError": max(c["maximumChannelError"] for c in evidence["pixelChecks"] if c["frame"] >= 10),
                        "pixelProbeCount": 168, "failures": evidence["failures"],
                        "videoSha256": checksum, "evidenceSha256": hashlib.sha256(file.read_bytes()).hexdigest()})
    assert len(records) == 3
    phases.append({"mode": mode, "run": run, "tests": tests, "records": records})
report = {"scope": "research_only_actual_API_mask_edge_experiments", "humanReview": "pending",
          "productionCombinedAdmission": "pending", "providerAfterExperiments": baseline["providerVersion"],
          "tolerance": 8, "originalOracleChanged": False, "productionSourceHashes": baseline["sources"],
          "consolidatorSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "phases": phases}
(STUDY / "temporal-matte-edge-experiments.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps({"testExecutions": sum(len(p["tests"]) for p in phases),
                  "passed": sum(not t["failed"] for p in phases for t in p["tests"]),
                  "retainedVideos": sum(len(p["records"]) for p in phases), "pixelProbes": 9 * 168,
                  "productionAdmission": "pending"}))
