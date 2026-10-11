"""Verify conformance and actual CRF10 API evidence, preserving all verdicts."""
import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / "docs/studios/research/editor-oss-20261002"
API = STUDY / "temporal-matte-native14-balanced-vector-guard-svg-subtract-crf10-full"


def sha(file):
    return hashlib.sha256(file.read_bytes()).hexdigest()


def read(file):
    return json.loads(file.read_text(encoding="utf-8"))


def main():
    baseline = read(STUDY / "temporal-matte-native13-current-sources.json")
    assert all(sha(ROOT / file) == checksum for file, checksum in baseline["sources"].items()), "production_source_drift"
    run, frozen = read(API / "run.json"), read(API / "sources.json")
    assert run["originalBytesRestored"] and not run["conflictingConcurrentEdits"]
    assert frozen["temporaryFinalCrf"] == 10
    for file, checksum in frozen["sources"].items():
        assert sha(API / "source-bytes" / file) == checksum
    for file in (API / "original-bytes").rglob("*"):
        if file.is_file():
            relative = file.relative_to(API / "original-bytes").as_posix()
            assert sha(file) == baseline["sources"][relative]
            assert sha(API / "candidate-bytes" / relative) == frozen["sources"][relative]
    renderer_files = ["workers/remotion-benchmark/src/temporal-exposure.tsx", "workers/remotion-benchmark/src/asset-matte.tsx"]
    previous = STUDY / "temporal-matte-native14-balanced-vector-guard-svg-subtract-full"
    assert all((API / "candidate-bytes" / file).read_bytes() == (previous / "candidate-bytes" / file).read_bytes()
               for file in renderer_files), "encode_experiment_changed_renderer"
    encoder_path = "backend/app/providers/studios/contextual_render.py"
    encode_original = (API / "original-bytes" / encoder_path).read_bytes()
    encode_candidate = (API / "candidate-bytes" / encoder_path).read_bytes()
    assert encode_original.replace(b'version = "1.4.0"', b'version = "1.4.1"').replace(
        b'"high": "14"', b'"high": "10"').replace(b'"high": 14}', b'"high": 10}') == encode_candidate
    tests = [{"name": test.attrib["name"], "failed": test.find("failure") is not None,
              "errored": test.find("error") is not None, "skipped": test.find("skipped") is not None}
             for test in ET.parse(API / "tests.xml").findall(".//testcase")]
    assert len(tests) == 7 and not any(test["errored"] or test["skipped"] for test in tests)
    research_paths = {"centerTexture": STUDY / "temporal-matte-qualified-texel-reassessment.json",
                      "quadClipTexture": STUDY / "temporal-matte-ramp-reassessment.json"}
    research = {key: {record["variant"]: record for record in read(path)["records"] if record["crf"] == 10}
                for key, path in research_paths.items()}
    derivative = {record["variant"]: record for record in read(STUDY / "temporal-matte-svg-subtract-final-encode-study-v2/analysis.json")["records"]
                  if record["crf"] == 10}
    records = []
    for file in sorted(API.glob("*/evidence.json")):
        evidence = read(file)
        variant = evidence["variant"]
        video = file.parent / "matte-exposure.mp4"
        assert sha(video) == evidence["renderResult"]["artifact"]["checksumSha256"]
        assert evidence["renderResult"]["qualityEvaluation"]["status"] == "passed"
        assert evidence["renderMetadata"]["contextualEditing"]["rendererChecks"]["audiovisual"] == {"encodeQuality": "high", "videoCrf": 10}
        probe_count = 162 if "-common-" in variant else 168
        assert len(evidence["pixelChecks"]) == probe_count and len(evidence["matrixChecks"]) == 6
        old_checks = derivative[variant]["checks"]
        assert [(check["frame"], check["x"], check["y"]) for check in evidence["pixelChecks"]] == [
            (check["frame"], check["x"], check["y"]) for check in old_checks]
        assert all(check["observedRgb"] == old["observedRgb"] for check, old in zip(evidence["pixelChecks"], old_checks, strict=True)), "actual_API_pixels_differ_from_derivative"
        measurements = {}
        for key, variants in research.items():
            measurements[key] = {"maximumChannelError": variants[variant]["maximumResearchReferenceError"],
                                 "failedProbes": variants[variant].get("failedResearchReferenceProbes", variants[variant].get("failedResearchProbes")),
                                 "scope": "Independent research reference; not a revised admission test."}
        records.append({"variant": variant, "videoSha256": sha(video), "evidenceSha256": sha(file), "qc": "passed",
                        "probeCount": probe_count, "matrixCheckCount": 6, "originalReferenceStatus": evidence["measurementStatus"],
                        "originalReferenceMaximumError": max(check["maximumChannelError"] for check in evidence["pixelChecks"]),
                        "originalReferenceFailures": evidence["failures"], "researchReferences": measurements,
                        "actualApiMatchesDerivativeProbePixels": True})
    assert len(records) == 7
    assert sum(test["failed"] for test in tests) == sum(record["originalReferenceStatus"] == "failed" for record in records)
    frame0_path = STUDY / "temporal-matte-svg-subtract-frame0-controls/analysis.json"
    frame0 = read(frame0_path)
    frame0_receipt = read(frame0_path.parent / "receipt.json")
    for case in frame0_receipt["cases"]:
        for record in case["records"]:
            for extension, key in [("png", "pngSha256"), ("json", "manifestSha256")]:
                assert sha(frame0_path.parent / case["name"] / (record["name"] + "." + extension)) == record[key]
    assert all(not record["failedProbesAtOriginalThreshold"] for case in frame0["cases"] for record in case["records"])
    related = [frame0_path, *research_paths.values(), STUDY / "temporal-matte-edge-ramp-study.json",
               STUDY / "temporal-matte-mixed-coverage-study.json", STUDY / "skia-quad-coverage-study.json",
               STUDY / "temporal-matte-svg-subtract-uniform-controls/analysis.json"]
    report = {"scope": "actual_API_CRf10_and_independent_texel_coverage_evidence", "productionAdmission": "pending", "humanReview": "pending",
              "originalOracleChanged": False, "tolerance": 8, "productionProvider": baseline["providerVersion"],
              "productionFinalizer": "1.4.0", "temporaryFinalizer": "1.4.1", "temporaryHighCrf": 10,
              "controlledEncoderOnlyDifferenceVerified": True, "tests": tests, "records": records,
              "validNewPngControls": 60, "exactTexelBlockComparisons": sum(record["probeCount"] for case in frame0["cases"] for record in case["records"]),
              "relatedEvidenceHashes": {path.relative_to(STUDY).as_posix(): sha(path) for path in related},
              "productionSourceHashes": baseline["sources"], "scriptSha256": sha(Path(__file__))}
    (STUDY / "temporal-matte-texel-coverage-receipt.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"actualApiVideos": len(records), "originalTestsPassed": sum(not test["failed"] for test in tests),
                      "originalTestsFailed": sum(test["failed"] for test in tests), "pixelProbes": sum(record["probeCount"] for record in records),
                      "researchReferencesBelowThreshold": {key: sum(not record["researchReferences"][key]["failedProbes"] for record in records) for key in research},
                      "productionAdmission": "pending"}))


if __name__ == "__main__":
    main()
