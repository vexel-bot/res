"""Consolidate exact-byte affine qualification, current regressions and retained API outputs."""
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


source_record = read(DIRECTORY / "temporal-rig-sources.json")
assert all(sha(ROOT / name) == digest for name, digest in source_record["sources"].items()), "Source bytes changed"
outcomes, runs = {}, []
for name in ["temporal-rig-render-tests.xml", "temporal-rig-pure-regression-tests.xml",
             "temporal-rig-native-regression-tests.xml", "temporal-rig-overflow-regression-tests.xml",
             "temporal-rig-command-audio-regression-tests.xml"]:
    path = DIRECTORY / name
    cases = ET.parse(path).findall(".//testcase")
    counts = {tag: sum(case.find(tag) is not None for case in cases) for tag in ["failure", "error", "skipped"]}
    for case in cases:
        outcomes[(case.get("classname"), case.get("name"))] = next(
            (tag for tag in counts if case.find(tag) is not None), "passed")
    runs.append({"path": path.relative_to(ROOT).as_posix(), "sha256": sha(path), "cases": len(cases), **counts})
assert all(status == "passed" for status in outcomes.values()), "Outstanding latest failure/error/skip"

folders = ["temporal-rig-render", "temporal-rig-exposure-regression", "temporal-rig-typography-regression",
           "temporal-rig-matte-regression", "temporal-rig-command-regression"]
renders, negatives = [], []
for name in folders:
    for path in sorted((DIRECTORY / name).rglob("evidence.json")):
        evidence = read(path)
        if "renderResult" not in evidence:
            assert evidence["publishedArtifact"] is False
            assert "hybrid_asset_matte_animated_png_pending" in evidence["errorMessage"]
            negatives.append({"path": path.relative_to(ROOT).as_posix(), "sha256": sha(path),
                              "diagnostic": evidence["errorMessage"], "publishedArtifact": False})
            continue
        result = evidence["renderResult"]
        assert result["providerVersion"] == "4.0.527-native.10"
        assert result["qualityEvaluation"]["status"] == "passed"
        assert result["documentRevision"] == evidence["inspection"]["document"]["revision"]
        assert evidence["humanReview"] == "pending"
        checks = evidence["renderMetadata"]["contextualEditing"]["rendererChecks"]
        receipt = checks["graphics"]["remotionReceipt"]
        quality = checks["audiovisual"]["encodeQuality"]
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
                  "quality": quality, "intermediateCrf": receipt["videoCrf"], "finalCrf": checks["audiovisual"]["videoCrf"],
                  "renderDurationMs": result["renderDurationMs"], "timingsMs": receipt["timingsMs"]}
        if name == "temporal-rig-render":
            assert evidence["measurementStatus"] == "passed" and not evidence["failures"]
            assert sha(path.parent / "graphics-intermediate.mp4") == receipt["videoSha256"]
            assert len(evidence["pixelChecks"]) == 90 and len(evidence["geometryChecks"]) == 6
            assert max(p["luminanceError"] for p in evidence["pixelChecks"]) < 8
            assert max(p["maximumErrorPx"] for p in evidence["geometryChecks"]) < .15
            record.update(variant=evidence["variant"], pixelProbes=90,
                          maximumLuminanceError=max(p["luminanceError"] for p in evidence["pixelChecks"]),
                          maximumGeometryErrorPx=max(p["maximumErrorPx"] for p in evidence["geometryChecks"]))
        renders.append(record)
assert len(renders) == 19 and len(negatives) == 1


def decoded(path):
    return subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                          capture_output=True, check=True, timeout=30,
                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout


control = decoded(DIRECTORY / "temporal-rig-exposure-regression/samples-0-shutter-180/exposure.mp4")
zero = decoded(DIRECTORY / "temporal-rig-exposure-regression/samples-8-shutter-0/exposure.mp4")
assert control == zero and len(control) == 60 * 320 * 320 * 3
overflow = read(DIRECTORY / "temporal-rig-layout-regression/negative.json")
assert not overflow["outputPublished"] and overflow["reportedFrame"] in {0, 1}
report = {"schemaVersion": "res.temporal-rig-receipt.v1", "generatedAt": datetime.now(UTC).isoformat(),
          "qualification": "fixture_specific_technical_evidence", "humanReview": "pending",
          "providerVersion": "4.0.527-native.10", "contextualFinalizerVersion": "1.4.0",
          "compilerVersion": "res.native-recipes.v4", "componentLibraryVersion": 7,
          "uniquePassedPytestCases": len(outcomes), "testRuns": runs,
          "testRunInterpretation": "Latest result per case; one nondeterministic overflow assertion was corrected and rerun.",
          "renders": renders, "negativeAPIJobs": negatives,
          "zeroShutterControlDecodedEquality": {"frames": 60, "rgbBytes": len(control), "maximumChannelDifference": 0},
          "fontOverflow": {"reportedFrame": overflow["reportedFrame"], "publishedOutput": False, "scope": "direct_renderer"},
          "sources": source_record["sources"],
          "correctedOverflowTestSha256": sha(ROOT / "backend/tests/test_typography_layout_render.py"),
          "consolidatorSha256": sha(Path(__file__)),
          "temporaryBundleCleanup": read(DIRECTORY / "temporal-rig-raster/temporary-bundle.json"),
          "limitations": ["Technical fixtures do not supply human scores or blind preference.",
                          "Parents outside the exposed subtree stay at center frame; no whole-world temporal claim.",
                          "Overlapping ancestor/child exposures with new policy are explicitly rejected.",
                          "Spatial shadow parameter mismatch predates this correction; shadow and nonzero spatial blur are unqualified.",
                          "Moving-external-ancestor matte and legacy CSS-mask combinations remain pending.",
                          "PNG raster capture is lossless; H264/444/CRF1 visual intermediate still has finite losses.",
                          "Aligned 2x2 luminance is an 8-bit SDR codec-aware oracle, not linear-light HDR.",
                          "Typography false/true cases all passed; retained variant evidence is the latter temporal case.",
                          "One legacy pixel regression overlapped the long regression; timings are observations, not p95.",
                          "Three fresh briefs/autonomy and human four-axis blind review remain pending.",
                          "Recursive cleanup of study repositories and bundles was blocked by automatic policy review."]}
(DIRECTORY / "temporal-rig-receipt.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"passedUnique": len(outcomes), "retainedAPIMP4s": len(renders), "negativeAPIJobs": len(negatives),
                  "rigResults": [r for r in renders if "variant" in r]}))
