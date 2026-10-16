"""Consolidate native.12 exact bytes, actual outputs and historical counterevidence."""
import hashlib
import json
import subprocess
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / "docs/studios/research/editor-oss-20261002"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


source_record = read(DIRECTORY / "spatial-effects-native12-sources.json")
assert all(sha(ROOT / name) == digest for name, digest in source_record["sources"].items()), "Source bytes changed"
outcomes, runs = {}, []
for name in ["spatial-effects-native12-render-tests.xml", "spatial-effects-native12-pure-regression-tests.xml",
             "spatial-effects-native12-native-regression-tests.xml"]:
    path = DIRECTORY / name
    cases = ET.parse(path).findall(".//testcase")
    counts = {tag: sum(case.find(tag) is not None for case in cases) for tag in ["failure", "error", "skipped"]}
    for case in cases:
        outcomes[(case.get("classname"), case.get("name"))] = next(
            (tag for tag in counts if case.find(tag) is not None), "passed")
    runs.append({"path": path.relative_to(ROOT).as_posix(), "sha256": sha(path), "cases": len(cases), **counts})
assert len(outcomes) == 171 and all(status == "passed" for status in outcomes.values())

folders = ["render", "rig-regression", "exposure-regression", "typography-regression",
           "matte-regression", "command-regression"]
renders, negatives = [], []
for suffix in folders:
    for path in sorted((DIRECTORY / ("spatial-effects-native12-" + suffix)).rglob("evidence.json")):
        evidence = read(path)
        if "renderResult" not in evidence:
            assert evidence["publishedArtifact"] is False
            assert "hybrid_asset_matte_animated_png_pending" in evidence["errorMessage"]
            negatives.append({"path": path.relative_to(ROOT).as_posix(), "sha256": sha(path),
                              "diagnostic": evidence["errorMessage"], "publishedArtifact": False})
            continue
        result = evidence["renderResult"]
        assert result["providerVersion"] == "4.0.527-native.12"
        assert result["qualityEvaluation"]["status"] == "passed"
        assert result["documentRevision"] == evidence["inspection"]["document"]["revision"]
        assert evidence["humanReview"] == "pending"
        checks = evidence["renderMetadata"]["contextualEditing"]["rendererChecks"]
        receipt = checks["graphics"]["remotionReceipt"]
        quality = checks["audiovisual"]["encodeQuality"]
        assert receipt["graphicsBackend"] == "chromium_swangle"
        assert checks["audiovisual"]["videoCrf"] == {"high": 14, "standard": 23, "draft": 28}[quality]
        assert receipt["videoCrf"] == {"high": 1, "standard": 23, "draft": 28}[quality]
        assert receipt["pixelFormat"] == ("yuv444p" if quality == "high" else "yuv420p")
        assert receipt["encodeRole"] == "visual_intermediate"
        video = next(p for p in path.parent.glob("*.mp4") if p.name != "graphics-intermediate.mp4")
        assert sha(video) == result["artifact"]["checksumSha256"]
        record = {"path": video.relative_to(ROOT).as_posix(), "videoSha256": sha(video), "bytes": video.stat().st_size,
                  "evidencePath": path.relative_to(ROOT).as_posix(), "evidenceSha256": sha(path),
                  "jobId": result["jobId"], "documentId": result["documentId"], "revision": result["documentRevision"],
                  "providerVersion": result["providerVersion"], "qc": "passed", "humanReview": "pending",
                  "graphicsBackend": receipt["graphicsBackend"], "quality": quality,
                  "renderDurationMs": result["renderDurationMs"], "timingsMs": receipt["timingsMs"]}
        if suffix in {"render", "rig-regression"}:
            assert evidence["measurementStatus"] == "passed" and not evidence["failures"]
            assert sha(path.parent / "graphics-intermediate.mp4") == receipt["videoSha256"]
            probes = evidence["pixelChecks"]
            assert len(probes) == (190 if suffix == "render" else 90)
            assert max(p["luminanceError"] for p in probes) < 8
            record.update(variant=evidence["variant"], pixelProbes=len(probes),
                          maximumLuminanceError=max(p["luminanceError"] for p in probes))
            if suffix == "render":
                assert max(p["maximumChannelError"] for p in probes) < 12
                if evidence["variant"] == "exposure":
                    assert evidence["discriminatingExposureProbe"]["luminanceDifferenceFromUnexposedCenter"] > 12
                    assert [p["exposure"]["actualSamples"] for p in evidence["temporalChecks"]] == [8, 8, 1, 1, 1]
                    record["discriminatingExposureProbe"] = evidence["discriminatingExposureProbe"]
            else:
                assert len(evidence["geometryChecks"]) == 6
                assert max(p["maximumErrorPx"] for p in evidence["geometryChecks"]) < .15
                record["maximumGeometryErrorPx"] = max(p["maximumErrorPx"] for p in evidence["geometryChecks"])
        renders.append(record)
assert len(renders) == 22 and len(negatives) == 1


def decoded(path):
    return subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                          capture_output=True, check=True, timeout=30,
                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout


control = decoded(DIRECTORY / "spatial-effects-native12-exposure-regression/samples-0-shutter-180/exposure.mp4")
zero = decoded(DIRECTORY / "spatial-effects-native12-exposure-regression/samples-8-shutter-0/exposure.mp4")
assert control == zero and len(control) == 60 * 320 * 320 * 3
overflow = read(DIRECTORY / "spatial-effects-native12-layout-regression/negative.json")
assert not overflow["outputPublished"] and overflow["reportedFrame"] in {0, 1}
runtime = read(DIRECTORY / "spatial-effects-runtime-study.json")
assert runtime["passed"] == 23 and runtime["sourceSha256"] == sha(ROOT / runtime["source"])
historical = []
for folder in ["spatial-effects-native10-baseline/spatial", "spatial-effects-fast-stage-diagnostic/exposure",
               "spatial-effects-small-sigma-diagnostic/spatial"]:
    path = DIRECTORY / folder / "evidence.json"
    evidence = read(path)
    assert evidence["measurementStatus"] == "failed" and evidence["failures"]
    historical.append({"path": path.relative_to(ROOT).as_posix(), "sha256": sha(path),
                       "providerVersion": evidence["renderResult"]["providerVersion"],
                       "failedProbes": len(evidence["failures"]), "qualification": "historical_failed_diagnostic"})
report = {"schemaVersion": "res.spatial-effects-receipt.v1", "generatedAt": datetime.now(UTC).isoformat(),
          "qualification": "fixture_specific_technical_evidence", "humanReview": "pending",
          "providerVersion": "4.0.527-native.12", "contextualFinalizerVersion": "1.4.0",
          "compilerVersion": "res.native-recipes.v4", "componentLibraryVersion": 7,
          "uniquePassedPytestCases": len(outcomes), "runtimeGuardChecks": 23, "testRuns": runs,
          "testRunInterpretation": "Deduplicated current cases; file named pure-regression also contains three actual renderer cases.",
          "renders": renders, "negativeAPIJobs": negatives, "historicalFailedDiagnostics": historical,
          "zeroShutterControlDecodedEquality": {"frames": 60, "rgbBytes": len(control), "maximumChannelDifference": 0},
          "fontOverflow": {"reportedFrame": overflow["reportedFrame"], "publishedOutput": False},
          "sources": source_record["sources"], "browserResearch": read(DIRECTORY / "spatial-effects-browser-sources.json"),
          "consolidatorSha256": sha(Path(__file__)),
          "limitations": ["Technical fixtures provide no human scores or blind preference.",
                          "No qualification of every blur/sigma/content/hardware; standalone subpixel blur remains a finite raster approximation.",
                          "Parents outside the exposed subtree stay at center frame; overlapping nested exposures remain explicitly rejected.",
                          "Moving-external-ancestor matte and legacy CSS-mask combinations remain pending.",
                          "PNG capture is lossless; intermediate H264/444/CRF1 and final H264/420/CRF14 still have finite losses.",
                          "Aligned 2x2 SDR luminance oracle does not qualify linear-light HDR.",
                          "Three fresh briefs/autonomy and human four-axis blind review remain pending.",
                          "Previously rejected recursive research cleanup remains pending; no bypass was attempted."]}
(DIRECTORY / "spatial-effects-receipt.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"passedUnique": len(outcomes), "runtimeGuardChecks": 23, "retainedAPIMP4s": len(renders),
                  "negativeAPIJobs": len(negatives), "spatialResults": [r for r in renders if r.get("pixelProbes") == 190]}))
