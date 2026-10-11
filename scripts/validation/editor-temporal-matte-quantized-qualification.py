"""Seal new API evidence, independent controls and unaltered historical verdicts."""
import hashlib
import json
import statistics
import subprocess
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / "docs/studios/research/editor-oss-20261002"
API = STUDY / "temporal-matte-native14-balanced-vector-guard-svg-subtract-quantized-full"
REGRESSION = STUDY / "temporal-matte-native14-quantized-candidate-regression"
EXPOSURE = STUDY / "temporal-matte-native14-quantized-exposure-regression"
OUT = STUDY / "temporal-matte-quantized-qualification.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def tests(path):
    return [{"name": case.attrib["classname"] + "::" + case.attrib["name"],
             "status": next((tag for tag in ["failure", "error", "skipped"] if case.find(tag) is not None), "passed"),
             "message": next((case.find(tag).get("message", "") for tag in ["failure", "error", "skipped"]
                              if case.find(tag) is not None), "")}
            for case in ET.parse(path).findall(".//testcase")]


def frozen_run(folder):
    run, frozen = read(folder / "run.json"), read(folder / "sources.json")
    assert run["originalBytesRestored"] and not run["conflictingConcurrentEdits"]
    for name, checksum in frozen["sources"].items():
        assert sha(folder / "source-bytes" / name) == checksum, "Archived source drift"
    for kind in ["original-bytes", "candidate-bytes"]:
        for path in (folder / kind).rglob("*"):
            if path.is_file():
                name = path.relative_to(folder / kind).as_posix()
                expected = (baseline["sources"].get(name, sha(ROOT / name)) if kind == "original-bytes"
                            else frozen["sources"][name])
                assert sha(path) == expected
    return run, frozen


baseline = read(STUDY / "temporal-matte-native13-current-sources.json")
assert all(sha(ROOT / name) == checksum for name, checksum in baseline["sources"].items())
api_run, api_frozen = frozen_run(API)
regression_run, regression_frozen = frozen_run(REGRESSION)
exposure_run, exposure_frozen = frozen_run(EXPOSURE)
assert exposure_run["exitCode"] == 0
assert api_run["exitCode"] == 0
api_tests = tests(API / "tests.xml")
historical_tests = tests(REGRESSION / "historical-tests.xml")
proposed_tests = tests(REGRESSION / "proposed-contract-tests.xml")
exposure_tests = tests(EXPOSURE / "tests.xml")
assert len(api_tests) == 7 and all(case["status"] == "passed" for case in api_tests)
assert len(historical_tests) == 188 and len(proposed_tests) == 4
assert len(exposure_tests) == 5 and all(case["status"] == "passed" for case in exposure_tests)
expected_contract_changes = {
    "tests.test_contextual_encode_quality::test_requested_quality_controls_real_contextual_encode[draft-28]",
    "tests.test_contextual_encode_quality::test_requested_quality_controls_real_contextual_encode[standard-23]",
    "tests.test_contextual_encode_quality::test_requested_quality_controls_real_contextual_encode[high-14]",
    "tests.test_temporal_exposure::test_matte_under_moving_external_parent_requires_exposing_its_rig",
}
expected_exposure_metadata_changes = {
    "tests.test_temporal_exposure_render::test_temporal_exposure_actual_api_measurement[" + case + "]"
    for case in ["0-180", "16-180", "2-180", "8-0", "8-180"]
}
expected_contract_changes |= expected_exposure_metadata_changes
failed = {case["name"] for case in historical_tests if case["status"] == "failure"}
assert failed == expected_contract_changes, "An unplanned historical regression remains"
assert all("assert 10 == 14" in case["message"] for case in historical_tests
           if case["name"] in expected_exposure_metadata_changes)
assert not any(case["status"] in {"error", "skipped"} for case in historical_tests)
assert all(case["status"] == "passed" for case in proposed_tests)
assert regression_run["historicalExitCode"] == 1 and regression_run["proposedContractsExitCode"] == 0
exposure_test = "backend/tests/test_temporal_exposure_render.py"
assert (EXPOSURE / "original-bytes" / exposure_test).read_bytes().replace(
    b'assert checks["audiovisual"]["videoCrf"] == 14', b'assert checks["audiovisual"]["videoCrf"] == 10') == (
        EXPOSURE / "candidate-bytes" / exposure_test).read_bytes()

renders, negatives = [], []
for folder, role in [(API, "new_quantized_API_matrix"), (REGRESSION, "new_existing_capability_regression"),
                     (EXPOSURE, "new_exposure_regression_with_updated_encode_receipt")]:
    for file in sorted(folder.rglob("evidence.json")):
        evidence = read(file)
        if "renderResult" not in evidence:
            assert evidence["publishedArtifact"] is False
            assert "hybrid_asset_matte_animated_png_pending" in evidence["errorMessage"]
            negatives.append({"path": file.relative_to(STUDY).as_posix(), "sha256": sha(file),
                              "diagnostic": evidence["errorMessage"], "publishedArtifact": False})
            continue
        result = evidence["renderResult"]
        assert result["providerVersion"] == "4.0.527-native.14"
        assert result["qualityEvaluation"]["status"] == "passed" and evidence["humanReview"] == "pending"
        assert result["documentRevision"] == evidence["inspection"]["document"]["revision"]
        checks = evidence["renderMetadata"]["contextualEditing"]["rendererChecks"]
        receipt = checks["graphics"]["remotionReceipt"]
        assert receipt["graphicsBackend"] == "chromium_swangle"
        audiovisual, quality = checks["audiovisual"], checks["audiovisual"]["encodeQuality"]
        assert audiovisual["videoCrf"] == {"draft": 28, "standard": 23, "high": 10}[quality]
        videos = [path for path in file.parent.glob("*.mp4") if path.name != "graphics-intermediate.mp4"]
        assert len(videos) == 1 and sha(videos[0]) == result["artifact"]["checksumSha256"]
        if (intermediate := file.parent / "graphics-intermediate.mp4").exists():
            assert sha(intermediate) == receipt["videoSha256"]
        if "measurementStatus" in evidence:
            assert evidence["measurementStatus"] == "passed" and not evidence["failures"]
        record = {"role": role, "variant": evidence.get("variant", file.parent.name),
                  "video": videos[0].relative_to(STUDY).as_posix(), "videoSha256": sha(videos[0]),
                  "evidence": file.relative_to(STUDY).as_posix(), "evidenceSha256": sha(file),
                  "bytes": videos[0].stat().st_size, "jobId": result["jobId"], "documentId": result["documentId"],
                  "documentRevision": result["documentRevision"], "qc": "passed", "humanReview": "pending",
                  "quality": quality, "renderDurationMs": result["renderDurationMs"], "timingsMs": receipt["timingsMs"]}
        if role == "new_quantized_API_matrix":
            assert evidence["pixelReference"]["id"] == "swiftshader4_affine_png_v1"
            assert evidence["pixelReference"]["quadConformanceSha256"] == sha(STUDY / "temporal-matte-quad-raster-conformance.json")
            assert evidence["pixelReference"]["texturedConformanceSha256"] == sha(STUDY / "temporal-matte-textured-source-conformance.json")
            assert len(evidence["matrixChecks"]) == 6
            assert len(evidence["pixelChecks"]) == (162 if "-common-" in evidence["variant"] else 168)
            record.update(pixelProbes=len(evidence["pixelChecks"]), matrixChecks=6,
                          maximumPixelError=max(check["maximumChannelError"] for check in evidence["pixelChecks"]),
                          maximumMatrixError=max(check["maximumError"] for check in evidence["matrixChecks"]))
            assert record["maximumPixelError"] < 8 and record["maximumMatrixError"] < .002
        renders.append(record)
assert len(renders) == 29 and len(negatives) == 1


def decoded(file):
    return subprocess.run(["ffmpeg", "-v", "error", "-i", str(file), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                          capture_output=True, check=True, timeout=30).stdout


control = decoded(EXPOSURE / "exposure/samples-0-shutter-180/exposure.mp4")
zero = decoded(EXPOSURE / "exposure/samples-8-shutter-0/exposure.mp4")
assert control == zero and len(control) == 60 * 320 * 320 * 3
overflow = read(REGRESSION / "layout/negative.json")
assert not overflow["outputPublished"] and overflow["reportedFrame"] in {0, 1}
runtime_path = STUDY / "swiftshader-subpixel-runtime.json"
phase_path = STUDY / "temporal-matte-subpixel-phase-controls/analysis.json"
quad_path = STUDY / "temporal-matte-quad-raster-conformance.json"
textured_path = STUDY / "temporal-matte-textured-source-conformance.json"
phase, quad, textured, runtime = map(read, [phase_path, quad_path, textured_path, runtime_path])
assert runtime["values"]["subpixelBits"] == phase["subpixelBits"] == quad["subpixelBits"] == 4
assert phase["runtimeSha256"] == sha(runtime_path)
assert len(phase["records"]) == 64 and len(quad["records"]) == 28 and len(textured["records"]) == 7
assert all(not record["failedSnappedByteProbesAtOriginalThreshold"] for record in phase["records"])
assert all(not record["failedProbesAtOriginalThreshold"] for record in quad["records"] + textured["records"])
for prefix in ["temporal-matte-subpixel-phase-controls", "temporal-matte-svg-subtract-uniform-controls"]:
    capture = read(STUDY / prefix / "receipt.json")
    for record in capture["records"]:
        for extension, key in [("png", "pngSha256"), ("json", "manifestSha256")]:
            assert sha(STUDY / prefix / (record["name"] + "." + extension)) == record[key]
balanced_path = STUDY / "temporal-matte-native14-balanced-runtime.json"
balanced = read(balanced_path)
assert balanced["passed"] == 38 and balanced["sourceSha256"] == api_frozen["sources"][balanced["source"]]
assert balanced["apiSourcesSha256"] == sha(API / "sources.json")
history = STUDY / "temporal-matte-native14-balanced-vector-guard-svg-subtract-crf10-full"
history_tests = tests(history / "tests.xml")
assert len(history_tests) == 7 and sum(case["status"] == "failure" for case in history_tests) == 1
api_renders = [record for record in renders if record["role"] == "new_quantized_API_matrix"]
durations = [record["renderDurationMs"] for record in api_renders]
proofs = [runtime_path, phase_path, quad_path, textured_path, balanced_path, API / "tests.xml",
          REGRESSION / "historical-tests.xml", REGRESSION / "proposed-contract-tests.xml", history / "tests.xml"]
proofs.append(EXPOSURE / "tests.xml")
report = {"schemaVersion": "res.temporal-matte-qualification.v1", "generatedAt": datetime.now(UTC).isoformat(),
          "qualification": "fixture_specific_technical_ready_for_local_incorporation", "productionAdmission": "pending",
          "humanReview": "pending", "autonomy": "pending", "providerVersion": "4.0.527-native.14",
          "contextualFinalizerVersion": "1.4.1", "highCrf": 10, "pixelReference": "swiftshader4_affine_png_v1",
          "originalDiagnosticAndVerdictsPreserved": True, "newApiCasesPassed": 7,
          "historicalCases": historical_tests, "historicalUnchangedCasesPassed": 179,
          "intentionallyChangedHistoricalContracts": sorted(expected_contract_changes),
          "newContractCases": proposed_tests + exposure_tests,
          "pixelProbeCount": sum(record["pixelProbes"] for record in api_renders),
          "matrixCheckCount": sum(record["matrixChecks"] for record in api_renders),
          "maximumPixelError": max(record["maximumPixelError"] for record in api_renders),
          "maximumMatrixError": max(record["maximumMatrixError"] for record in api_renders),
          "newSubpixelPngControls": 64, "subpixelPixelComparisons": sum(record["allPixelProbeCount"] for record in phase["records"]),
          "retainedQuadControlsReassessed": 28, "quadPixelComparisons": sum(record["probeCount"] for record in quad["records"]),
          "retainedTexturedControlsReassessed": 7, "texturedPixelComparisons": sum(record["pixelCount"] for record in textured["records"]),
          "runtimeTreeChecks": 38, "newApiRenders": renders, "negativeApiJobs": negatives,
          "zeroShutterControlDecodedEquality": {"frames": 60, "rgbBytes": len(control), "maximumDifference": 0},
          "fontOverflow": {"reportedFrame": overflow["reportedFrame"], "outputPublished": False},
          "localFixtureRenderDurationMs": {"count": 7, "min": min(durations), "median": statistics.median(durations),
                                           "max": max(durations), "interpretation": "320x320, 16 frames, 30fps; no p95/realtime claim."},
          "proofHashes": {file.relative_to(STUDY).as_posix(): sha(file) for file in proofs},
          "candidateSources": {name: api_frozen["sources"][name] for name in baseline["sources"]},
          "historicalSupersampledReferenceVerdicts": history_tests,
          "scriptSha256": sha(Path(__file__)),
          "limitations": ["Large affine quads and PNG fixtures on pinned four-bit SwiftShader; no arbitrary path/perspective oracle claim.",
                          "Quantized coverage and premultiplied texture sampling are independently derived, not fitted to failing video probes.",
                          "Original historical oracle/thresholds/probes and negative receipts remain unchanged.",
                          "No human scores, blind preference or autonomy evidence is inferred from QC or pixel passes.",
                          "The rejected cleanup of study repositories and existing DOM/PNG bundles has not been retried."]}
assert not OUT.exists(), "Preserve sealed qualification evidence"
OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"apiCasesPassed": 7, "unchangedHistoricalCasesPassed": 179, "newContractCasesPassed": 9,
                  "newRetainedMp4s": 29, "pixelProbes": report["pixelProbeCount"], "maximumError": report["maximumPixelError"],
                  "productionAdmission": "pending"}))
