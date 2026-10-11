"""Consolidate combined vector/guard candidates, preserving original verdicts."""
import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / "docs/studios/research/editor-oss-20261002"
baseline = json.loads((STUDY / "temporal-matte-native13-current-sources.json").read_text(encoding="utf-8"))
assert all(hashlib.sha256((ROOT / file).read_bytes()).hexdigest() == checksum
           for file, checksum in baseline["sources"].items()), "production_source_drift"
phases = []
for name, count in [("balanced-padded-vector-guard-band", 3),
                    ("factored-balanced-padded-vector-guard-band", 3),
                    ("balanced-padded-vector-guard-band-padded-filter", 3),
                    ("balanced-padded-vector-guard-band-padded-filter-full", 7)]:
    folder = STUDY / ("temporal-matte-native14-" + name)
    if not folder.exists() and count == 7:
        continue
    run = json.loads((folder / "run.json").read_text(encoding="utf-8"))
    assert run["originalBytesRestored"] and not run["conflictingConcurrentEdits"]
    frozen = json.loads((folder / "sources.json").read_text(encoding="utf-8"))
    for file in (folder / "original-bytes").rglob("*"):
        if file.is_file():
            relative = file.relative_to(folder / "original-bytes").as_posix()
            assert hashlib.sha256(file.read_bytes()).hexdigest() == baseline["sources"][relative]
            assert hashlib.sha256((folder / "candidate-bytes" / relative).read_bytes()).hexdigest() == frozen["sources"][relative]
    tests = [{"name": t.attrib["name"], "failed": t.find("failure") is not None,
              "errored": t.find("error") is not None, "skipped": t.find("skipped") is not None}
             for t in ET.parse(folder / "tests.xml").findall(".//testcase")]
    assert len(tests) == count and not any(t["errored"] or t["skipped"] for t in tests)
    records = []
    for file in sorted(folder.glob("*/evidence.json")):
        evidence = json.loads(file.read_text(encoding="utf-8"))
        video = file.parent / "matte-exposure.mp4"
        checksum = hashlib.sha256(video.read_bytes()).hexdigest()
        assert checksum == evidence["renderResult"]["artifact"]["checksumSha256"]
        assert evidence["renderResult"]["qualityEvaluation"]["status"] == "passed"
        assert len(evidence["pixelChecks"]) == 168 and len(evidence["matrixChecks"]) == 6
        records.append({"variant": evidence["variant"], "measurementStatus": evidence["measurementStatus"],
                        "qc": "passed", "maximumChannelError": max(c["maximumChannelError"] for c in evidence["pixelChecks"]),
                        "maximumMatrixError": max(c["maximumError"] for c in evidence["matrixChecks"]),
                        "failures": evidence["failures"], "pixelProbeCount": 168,
                        "videoSha256": checksum, "evidenceSha256": hashlib.sha256(file.read_bytes()).hexdigest()})
    assert len(records) == count
    phases.append({"name": name, "testCount": count, "run": run, "tests": tests, "records": records})
first = STUDY / "temporal-matte-native14-balanced-padded-vector-guard-band"
second = STUDY / "temporal-matte-native14-balanced-padded-vector-guard-band-padded-filter"
matte_path = "workers/remotion-benchmark/src/asset-matte.tsx"
temporal_path = "workers/remotion-benchmark/src/temporal-exposure.tsx"
before = (first / "candidate-bytes" / matte_path).read_bytes()
after = (second / "candidate-bytes" / matte_path).read_bytes()
assert before.replace(b'<filter id={filter} x="0%" y="0%" width="100%" height="100%"',
                      b'<filter id={filter} x="-50%" y="-50%" width="200%" height="200%"') == after
assert (first / "candidate-bytes" / temporal_path).read_bytes() == (second / "candidate-bytes" / temporal_path).read_bytes()
filter_checks = []
for variant in [r["variant"] for r in phases[0]["records"]]:
    a = json.loads((first / variant / "evidence.json").read_text(encoding="utf-8"))
    b = json.loads((second / variant / "evidence.json").read_text(encoding="utf-8"))
    assert [(c["frame"], c["x"], c["y"]) for c in a["pixelChecks"]] == [(c["frame"], c["x"], c["y"]) for c in b["pixelChecks"]]
    difference = max(abs(av - bv) for c, d in zip(a["pixelChecks"], b["pixelChecks"], strict=True)
                     for av, bv in zip(c["observedRgb"], d["observedRgb"], strict=True))
    filter_checks.append({"variant": variant, "maximumObservedProbeDifference": difference, "probeCount": 168})
report = {"scope": "temporary_actual_API_vector_guard_combination_experiments", "productionAdmission": "pending",
          "providerAfterExperiments": baseline["providerVersion"], "humanReview": "pending",
          "originalOracleChanged": False, "tolerance": 8, "phases": phases,
          "controlledFilterRegionComparison": {"onlyRendererDifferenceVerifiedByBytes": True, "checks": filter_checks},
          "productionSourceHashes": baseline["sources"],
          "consolidatorSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
(STUDY / "temporal-matte-vector-guard-experiments.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps({"phases": len(phases), "testExecutions": sum(len(p["tests"]) for p in phases),
                  "passed": sum(not t["failed"] for p in phases for t in p["tests"]),
                  "videos": sum(len(p["records"]) for p in phases),
                  "probes": sum(r["pixelProbeCount"] for p in phases for r in p["records"]), "productionAdmission": "pending"}))
