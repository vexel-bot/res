"""Verify retained inverse-operator experiments without changing pixel verdicts."""
import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / "docs/studios/research/editor-oss-20261002"


def sha(file):
    return hashlib.sha256(file.read_bytes()).hexdigest()


def main():
    baseline = json.loads((STUDY / "temporal-matte-native13-current-sources.json").read_text(encoding="utf-8"))
    assert all(sha(ROOT / file) == checksum for file, checksum in baseline["sources"].items()), "production_source_drift"
    phases = []
    for name, count in [("composite-inverse", 3), ("target-inverse", 3), ("svg-subtract", 3), ("svg-subtract-full", 7)]:
        folder = STUDY / ("temporal-matte-native14-balanced-vector-guard-" + name)
        run = json.loads((folder / "run.json").read_text(encoding="utf-8"))
        assert run["originalBytesRestored"] and not run["conflictingConcurrentEdits"]
        frozen = json.loads((folder / "sources.json").read_text(encoding="utf-8"))
        for file, checksum in frozen["sources"].items():
            assert sha(folder / "source-bytes" / file) == checksum
        for file in (folder / "original-bytes").rglob("*"):
            if file.is_file():
                relative = file.relative_to(folder / "original-bytes").as_posix()
                assert sha(file) == baseline["sources"][relative]
                assert sha(folder / "candidate-bytes" / relative) == frozen["sources"][relative]
        tests = [{"name": test.attrib["name"], "failed": test.find("failure") is not None,
                  "errored": test.find("error") is not None, "skipped": test.find("skipped") is not None}
                 for test in ET.parse(folder / "tests.xml").findall(".//testcase")]
        assert len(tests) == count and not any(test["errored"] or test["skipped"] for test in tests)
        records = []
        for file in sorted(folder.glob("*/evidence.json")):
            evidence = json.loads(file.read_text(encoding="utf-8"))
            checksum = sha(file.parent / "matte-exposure.mp4")
            assert checksum == evidence["renderResult"]["artifact"]["checksumSha256"]
            assert evidence["renderResult"]["qualityEvaluation"]["status"] == "passed"
            # The frozen oracle deduplicates probe positions; common-parent
            # fixtures have 27 per frame, external fixtures have 28.
            probe_count = 162 if "-common-" in evidence["variant"] else 168
            assert len(evidence["pixelChecks"]) == probe_count and len(evidence["matrixChecks"]) == 6
            failures = [check for check in evidence["pixelChecks"] if check["maximumChannelError"] >= 8]
            records.append({"variant": evidence["variant"], "measurementStatus": evidence["measurementStatus"],
                            "qc": "passed", "maximumChannelError": max(c["maximumChannelError"] for c in evidence["pixelChecks"]),
                            "maximumMatrixError": max(c["maximumError"] for c in evidence["matrixChecks"]),
                            "failures": evidence["failures"], "failedPixelChecks": failures, "pixelProbeCount": probe_count,
                            "videoSha256": checksum, "evidenceSha256": sha(file)})
        assert len(records) == count
        assert sum(test["failed"] for test in tests) == sum(bool(record["failures"]) for record in records)
        phases.append({"name": name, "testCount": count, "run": run, "tests": tests, "records": records})
    controls_path = STUDY / "temporal-matte-source-edge-controls/analysis.json"
    controls = json.loads(controls_path.read_text(encoding="utf-8"))
    residual_path = STUDY / "temporal-matte-svg-subtract-residual-controls-v2/analysis.json"
    residual = json.loads(residual_path.read_text(encoding="utf-8"))
    encode_path = STUDY / "temporal-matte-svg-subtract-final-encode-study-v2/analysis.json"
    encode = json.loads(encode_path.read_text(encoding="utf-8"))
    assert encode["crf14ControlMatchesAllApiProbes"] and len(encode["records"]) == 21
    for record in encode["records"]:
        video = encode_path.parent / (record["variant"] + "-crf" + str(record["crf"]) + ".mp4")
        assert sha(video) == record["outputSha256"]
        source_folder = STUDY / "temporal-matte-native14-balanced-vector-guard-svg-subtract-full" / record["variant"]
        assert sha(source_folder / "graphics-intermediate.mp4") == record["sourceVideoSha256"]
        assert sha(source_folder / "matte-exposure.mp4") == record["apiVideoSha256"]
        assert sha(source_folder / "evidence.json") == record["apiEvidenceSha256"]
        if record["crf"] == 14:
            assert all(check["differenceFromApiFinal"] == 0 for check in record["checks"])
    report = {"scope": "temporary_actual_API_inverse_operator_experiments", "productionAdmission": "pending",
              "providerAfterExperiments": baseline["providerVersion"], "humanReview": "pending",
              "originalOracleChanged": False, "tolerance": 8, "phases": phases,
              "sourceEdgeControls": {"analysisSha256": sha(controls_path), "phaseCount": len(controls["phases"]),
                                     "captureCount": 8 * len(controls["phases"]), "scope": "worker_PNG_controls_not_API_videos"},
              "derivedResidualControls": {"analysisSha256": sha(residual_path), "caseCount": len(residual["comparisons"]),
                                          "validCaptureCount": 20, "scope": "derived_worker_PNG_controls_not_API_admission",
                                          "invalidEarlierControlsExcluded": residual["invalidEarlierControlsExcluded"]},
              "finalEncodeStudy": {"analysisSha256": sha(encode_path), "derivativeVideoCount": len(encode["records"]),
                                   "crf14ControlMatchesAllApiProbes": True, "scope": "retained_intermediate_reencode_not_API_admission"},
              "productionSourceHashes": baseline["sources"], "consolidatorSha256": sha(Path(__file__))}
    (STUDY / "temporal-matte-source-edge-experiments.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"phases": len(phases), "testExecutions": sum(len(p["tests"]) for p in phases),
                      "passed": sum(not t["failed"] for p in phases for t in p["tests"]),
                      "videos": sum(len(p["records"]) for p in phases),
                      "probes": sum(r["pixelProbeCount"] for p in phases for r in p["records"]),
                      "controls": report["sourceEdgeControls"], "productionAdmission": "pending"}))


if __name__ == "__main__":
    main()
