"""Consolidate exact source bytes, API jobs, decoded exposure and test limits."""
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


source_record = json.loads((DIRECTORY / "temporal-exposure-final-sources.json").read_text())
if any(sha(ROOT / name) != digest for name, digest in source_record["sources"].items()):
    raise SystemExit("Production source bytes changed during final qualification")
runtime = json.loads((DIRECTORY / "temporal-exposure-runtime-study.json").read_text())
if runtime["passed"] != 22 or sha(ROOT / runtime["source"]) != runtime["sourceSha256"]:
    raise SystemExit("Runtime sampler/reducer evidence conflict")
outcomes, runs = {}, []
for name in ["temporal-exposure-regression-tests.xml", "temporal-exposure-hold-contract-tests.xml",
             "temporal-exposure-final-regression-tests.xml", "temporal-exposure-final-render-tests.xml",
             "temporal-exposure-legacy-typography-tests.xml"]:
    path = DIRECTORY / name
    cases = ET.parse(path).findall(".//testcase")
    counts = {tag: sum(case.find(tag) is not None for case in cases) for tag in ["failure", "error", "skipped"]}
    for case in cases:
        outcomes[(case.get("classname"), case.get("name"))] = next(
            (tag for tag in counts if case.find(tag) is not None), "passed"
        )
    runs.append({"path": path.relative_to(ROOT).as_posix(), "sha256": sha(path), "cases": len(cases), **counts})
if any(status != "passed" for status in outcomes.values()):
    raise SystemExit("Outstanding current qualification failure/error/skip")
renders = []
for samples, shutter in [(0, 180), (2, 180), (8, 180), (16, 180), (8, 0)]:
    folder = DIRECTORY / "temporal-exposure-render" / f"samples-{samples}-shutter-{shutter}"
    evidence = json.loads((folder / "evidence.json").read_text(encoding="utf-8"))
    result = evidence["renderResult"]
    checks = evidence["renderMetadata"]["contextualEditing"]["rendererChecks"]
    receipt = checks["graphics"]["remotionReceipt"]
    if (sha(folder / "exposure.mp4") != result["artifact"]["checksumSha256"]
            or result["providerVersion"] != "4.0.527-native.9" or result["qualityEvaluation"]["status"] != "passed"
            or receipt["rasterCapture"] != "png_lossless_intermediate" or receipt["videoCrf"] != 18
            or checks["audiovisual"] != {"encodeQuality": "high", "videoCrf": 18}
            or result["documentRevision"] != evidence["inspection"]["document"]["revision"]):
        raise SystemExit("Render integrity conflict: " + str((samples, shutter)))
    probes = evidence["edgeChecks"]
    if samples and (len(probes) != 16 or any(
            abs(probe["observedLuminance"] - probe["expectedLuminance"]) >= 8
            or probe["footprint"] != "aligned_2x2_yuv420p_block" for probe in probes)):
        raise SystemExit("Independent edge pixel evidence conflict")
    renders.append({"samples": samples, "shutterDegrees": shutter, "scope": evidence["scope"],
                    "jobId": result["jobId"], "documentId": result["documentId"],
                    "documentRevision": result["documentRevision"], "providerVersion": result["providerVersion"],
                    "videoSha256": result["artifact"]["checksumSha256"], "bytes": (folder / "exposure.mp4").stat().st_size,
                    "renderDurationMs": result["renderDurationMs"], "runnerTimingsMs": receipt["timingsMs"],
                    "decodeProfile": receipt["decodeProfile"], "qc": "passed", "humanReview": "pending",
                    "width": 320, "height": 320, "fps": 30, "frames": 60, "quality": "high",
                    "edgeProbes": len(probes), "maximumLuminanceError": max(
                        (abs(p["observedLuminance"] - p["expectedLuminance"]) for p in probes), default=None),
                    "evidenceSha256": sha(folder / "evidence.json")})


def decoded(path):
    return subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                          capture_output=True, check=True, timeout=30,
                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout


control = decoded(DIRECTORY / "temporal-exposure-render/samples-0-shutter-180/exposure.mp4")
zero = decoded(DIRECTORY / "temporal-exposure-render/samples-8-shutter-0/exposure.mp4")
if len(control) != 60 * 320 * 320 * 3 or control != zero:
    raise SystemExit("Zero shutter must reproduce whole decoded sharp control exactly")
held_frame_comparisons = []
frame_bytes = 320 * 320 * 3
for samples in [2, 8, 16]:
    frames = decoded(DIRECTORY / f"temporal-exposure-render/samples-{samples}-shutter-180/exposure.mp4")
    for frame in [10, 29, 40, 59]:
        left, right = control[frame * frame_bytes:(frame + 1) * frame_bytes], frames[frame * frame_bytes:(frame + 1) * frame_bytes]
        errors = [abs(a - b) for a, b in zip(left, right, strict=True)]
        held_frame_comparisons.append({"samples": samples, "frame": frame,
                                       "wholeFrameMeanAbsoluteChannelError": sum(errors) / len(errors),
                                       "maximumChannelError": max(errors),
                                       "scope": "encoded frames comparison; codec differences remain"})
typography = []
for variant in ["unicode", "wrapped_words"]:
    folder = DIRECTORY / "temporal-typography-render" / variant
    evidence = json.loads((folder / "evidence.json").read_text(encoding="utf-8"))
    result = evidence["renderResult"]
    if (not evidence["temporalExposure"] or result["qualityEvaluation"]["status"] != "passed"
            or sha(folder / "typography.mp4") != result["artifact"]["checksumSha256"]
            or result["providerVersion"] != "4.0.527-native.9"):
        raise SystemExit("Typography exposure actual API evidence conflict")
    typography.append({"variant": variant, "jobId": result["jobId"], "documentRevision": result["documentRevision"],
                       "videoSha256": result["artifact"]["checksumSha256"], "fontSha256": evidence["font"]["sha256"],
                       "effectiveHoldStartFrame": evidence["effectiveHoldStartFrame"],
                       "decodedPixelChecks": evidence["decodedPixelChecks"], "qc": "passed", "humanReview": "pending"})
diagnostics = []
for name in ["temporal-exposure-baseline-tests.xml", "temporal-exposure-jpeg-render-tests.xml",
             "temporal-exposure-png-standard-render-tests.xml", "temporal-exposure-high-single-pixel-tests.xml"]:
    path = DIRECTORY / name
    cases = ET.parse(path).findall(".//testcase")
    diagnostics.append({"path": path.relative_to(ROOT).as_posix(), "sha256": sha(path),
                        "status": "historical_diagnostic_not_current_qualification",
                        "failures": [{"name": case.get("name"), "message": case.find("failure").get("message")}
                                     for case in cases if case.find("failure") is not None]})
report = {"schemaVersion": "res.temporal-exposure-receipt.v1", "generatedAt": datetime.now(UTC).isoformat(),
          "qualification": "implemented_with_fixture_specific_technical_evidence", "humanReview": "pending",
          "compilerVersion": "res.native-recipes.v4", "componentLibraryVersion": 7,
          "providerVersion": "4.0.527-native.9", "contextualFinalizerVersion": "1.3.0",
          "uniquePassedPytestCases": len(outcomes), "testRuns": runs, "testRunsOverlap": True,
          "runtimeSamplerReducerChecks": 22, "renders": renders, "typographyRenders": typography,
          "zeroShutterControlDecodedEquality": {"frames": 60, "rgbBytes": len(control), "maximumChannelDifference": 0},
          "heldFrameComparisons": held_frame_comparisons,
          "diagnostics": diagnostics, "sources": source_record["sources"],
          "limitations": ["Finite browser sRGB plus-lighter precision; not linear-light HDR exposure.",
                          "Local subtree exposure; external ancestors evaluated at center frame.",
                          "New exposure below affine rigs/nested exposure requires further real pixel qualification.",
                          "Legacy CSS mask assets and mattes below a moving external ancestor pending with correction.",
                          "Single-pixel encoded color is not the oracle; phase probes average aligned 2x2 yuv420p blocks.",
                          "High quality qualified here; historical standard compression failures remain documented.",
                          "Lossless reconstructed PNG diagnostics are not substituted for API MP4 evidence.",
                          "DOM sample geometry is not mask/pixel coverage or human approval.",
                          "Compile/backend finalization/CPU peak timings not isolated; no p95 or realtime claim.",
                          "Human axes/blind preference/three fresh briefs still pending.",
                          "Research clones/DOM bundle deletion previously blocked by automatic policy review."]}
report["rasterDiagnosticBundleCleanup"] = json.loads(
    (DIRECTORY / "temporal-raster-diagnostic/temporary-bundle.json").read_text(encoding="utf-8-sig")
)
output = DIRECTORY / "temporal-exposure-receipt.json"
output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"output": str(output), "passed": len(outcomes), "API_MP4s": len(renders) + len(typography)}))
