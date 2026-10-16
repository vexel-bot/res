"""Consolidate canonical mattes, real decoded pixels and explicit test limits."""
import hashlib
import json
import math
import struct
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / "docs/studios/research/editor-oss-20261002"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


outcomes, runs = {}, []
for name in [
    "asset-matte-regression-tests.xml", "asset-matte-editorial-regression-tests.xml",
    "asset-matte-font-license-tests.xml", "asset-matte-contract-tests.xml", "asset-matte-real-tests.xml",
    "asset-matte-legacy-pixel-tests.xml", "asset-matte-final-runner-tests.xml",
    "asset-matte-aspect-tests.xml",
    "asset-matte-cover-tests.xml",
    "asset-matte-complete-render-tests.xml", "asset-matte-animated-negative-tests.xml",
]:
    path = DIRECTORY / name
    cases = ET.parse(path).findall(".//testcase")
    counts = {tag: sum(case.find(tag) is not None for case in cases) for tag in ["failure", "error", "skipped"]}
    for case in cases:
        status = next((tag for tag in counts if case.find(tag) is not None), "passed")
        outcomes[(case.get("classname"), case.get("name"))] = {
            "status": status, "run": name,
            "reason": case.find(status).get("message") if status != "passed" else None,
        }
    runs.append({"path": path.relative_to(ROOT).as_posix(), "cases": len(cases), **counts, "sha256": sha(path)})
failed = [key for key, value in outcomes.items() if value["status"] in {"failure", "error"}]
skipped = [{"case": key, **value} for key, value in outcomes.items() if value["status"] == "skipped"]
if failed or any("Explicit pinned HyperFrames runtime" not in item["reason"] for item in skipped):
    raise SystemExit("Outstanding non-qualified failures/skips: " + str(failed or skipped))
png = json.loads((DIRECTORY / "asset-matte-png-study.json").read_text(encoding="utf-8"))
if png["passed"] != 17 or sha(ROOT / png["source"]) != png["sourceSha256"]:
    raise SystemExit("PNG header evidence conflict")

renders = []
for variant in [
    "alpha-normal", "alpha-inverted", "luminance-normal", "luminance-inverted", "alpha-wide-contain", "alpha-wide-cover",
]:
    folder = DIRECTORY / "asset-matte-render" / variant
    evidence = json.loads((folder / "evidence.json").read_text(encoding="utf-8"))
    result = evidence["renderResult"]
    if (sha(folder / "matte.mp4") != result["artifact"]["checksumSha256"]
            or result["providerVersion"] != "4.0.527-native.8" or result["qualityEvaluation"]["status"] != "passed"
            or sha(folder / "original-matte.png") != evidence["maskAssetSha256"]):
        raise SystemExit("Render evidence integrity conflict: " + variant)
    probes = evidence["pixelChecks"]
    bitmap_size = list(struct.unpack(">II", (folder / "original-matte.png").read_bytes()[16:24]))
    if evidence.get("sourceBitmapSize", bitmap_size) != bitmap_size:
        raise SystemExit("Bitmap dimension evidence conflict: " + variant)
    if len(probes) != 35 or any(abs(channel - probe["expectedChannel"]) >= 12 for probe in probes
                              for channel in probe["observedRgb"]):
        raise SystemExit("Pixel coverage conflict: " + variant)
    fit = "cover" if variant.endswith("-cover") else "contain"
    if variant.startswith("alpha-wide-"):
        expected_box = 102 if fit == "cover" else 0
        if (evidence["sourceBitmapSize"] != [256, 128] or evidence["sourceObjectFit"] != fit
                or any(abs(channel - expected_box) >= 12 for channel in evidence["aspectProbeRgb"])):
            raise SystemExit("Aspect/crop evidence conflict: " + variant)
    geometry = evidence["renderMetadata"]["contextualEditing"]["rendererChecks"]["geometrySamples"]
    for frame in [2, 4, 7, 12]:
        hero = next(item for item in geometry[frame]["elements"] if item["semanticId"] == "hero")
        p = min(frame / 7, 1)
        source_angle, target_angle = math.radians(90 * p), math.radians(-5 * p)
        scale, delta = 1 + .2 * p, source_angle - target_angle
        tx = 20 + 4 * (math.cos(target_angle) - math.sin(target_angle))
        ty = 20 + 10 * p + 4 * (math.sin(target_angle) + math.cos(target_angle))
        dx = 80 + 80 * p + 10 * scale * math.cos(source_angle) - tx
        dy = 80 + 10 * scale * math.sin(source_angle) - ty
        expected = [scale * math.cos(delta), scale * math.sin(delta), -scale * math.sin(delta), scale * math.cos(delta),
                    dx * math.cos(target_angle) + dy * math.sin(target_angle),
                    -dx * math.sin(target_angle) + dy * math.cos(target_angle)]
        actual = hero["assetMatte"]["sourceToTargetMatrix"]
        if any(abs(a - b) > .002 for a, b in zip(actual, expected, strict=True)):
            raise SystemExit("Independent matrix conflict: " + variant)
    renders.append({
        "variant": variant, "scope": evidence["scope"], "jobId": result["jobId"], "documentId": result["documentId"],
        "documentRevision": result["documentRevision"], "providerVersion": result["providerVersion"],
        "videoSha256": result["artifact"]["checksumSha256"], "videoBytes": result["artifact"]["sizeBytes"],
        "renderDurationMs": result["renderDurationMs"], "qc": "passed", "frames": 15, "fps": 30,
        "width": 320, "height": 320, "maskAssetSha256": evidence["maskAssetSha256"], "pixelProbes": len(probes),
        "maximumObservedPixelChannelError": max(abs(channel - probe["expectedChannel"]) for probe in probes
                                                for channel in probe["observedRgb"]),
        "evidenceSha256": sha(folder / "evidence.json"),
        "sourceBitmapSize": bitmap_size, "sourceObjectFit": fit,
        "aspectProbeRgb": evidence.get("aspectProbeRgb"),
        "decodeProfile": evidence["renderMetadata"]["contextualEditing"]["rendererChecks"]["graphics"]["remotionReceipt"]["decodeProfile"],
    })

font_report = json.loads((DIRECTORY / "font-license-integrity.json").read_text(encoding="utf-8"))
if any(record["afterSha256"] != record["expectedSha256"] for record in font_report["licenses"]):
    raise SystemExit("Font license bytes remain stale")
negative_folder = DIRECTORY / "asset-matte-render/animated-negative"
negative = json.loads((negative_folder / "evidence.json").read_text(encoding="utf-8"))
if (negative["publishedArtifact"] or "hybrid_asset_matte_animated_png_pending" not in negative["errorMessage"]
        or sha(negative_folder / "original-animated-matte.png") != negative["sourceSha256"]):
    raise SystemExit("Animated PNG negative evidence conflict")
sources = [
    "backend/app/domain/studios/asset_matte.py", "backend/app/domain/studios/motion_recipes.py",
    "backend/app/domain/studios/contextual_editing_v2.py", "backend/app/services/studios/native_motion_recipes.py",
    "backend/app/providers/studios/remotion_projection.py", "backend/app/providers/studios/remotion_render.py",
    "backend/app/services/studios/contextual_editing_v2.py", "workers/remotion-benchmark/src/hybrid.tsx",
    "workers/remotion-benchmark/src/asset-matte.tsx", "workers/remotion-benchmark/src/asset-matte-png.mjs",
    "workers/remotion-benchmark/render-hybrid.mjs", "backend/tests/test_asset_matte.py",
    "backend/tests/test_asset_matte_render.py", ".gitattributes", "scripts/validation/editor-font-license-integrity.py",
    "scripts/validation/editor-asset-matte-png-study.mjs", "scripts/validation/editor-asset-matte-receipt.py",
]
report = {
    "schemaVersion": "res.asset-matte-receipt.v1", "generatedAt": datetime.now(UTC).isoformat(),
    "qualification": "implemented_with_technical_evidence", "humanReview": "pending",
    "compilerVersion": "res.native-recipes.v4", "componentLibraryVersion": 6, "providerVersion": "4.0.527-native.8",
    "legacyVersionsReadable": [1, 2, 3], "uniquePassedPytestCases": sum(v["status"] == "passed" for v in outcomes.values()),
    "uniqueSkippedPytestCases": len(skipped), "skips": skipped, "testRuns": runs,
    "testRunsOverlap": True, "initialFontLicenseFailureCorrectedByLaterRun": True,
    "pngHeaderChecks": 17, "renders": renders, "fontLicenseIntegrity": font_report,
    "animatedPngNegative": negative,
    "sources": {name: sha(ROOT / name) for name in sources}, "cleanup": "previous_research_and_DOM_bundles_blocked_by_policy",
    "limitations": [
        "PNG field geometry is arbitrary; this is not animated mask footage, roto, tracking or path morph.",
        "One matte per target; no source-matte/filter/clip chain or transition over source lineage.",
        "Explicit source_layer_only opacity; parent source opacity is not a mask input.",
        "DOM observations are not coverage proof; decoded probes qualify only these fixtures.",
        "Human visual/mobile/commercial/autonomy review remains pending; no human scores filled.",
        "Observed 320x320 half-second renders do not establish p95 or realtime 1080p.",
        "Separate legacy HyperFrames actual-render test skipped because its explicitly pinned runtime is unavailable.",
    ],
}
output = DIRECTORY / "asset-matte-receipt.json"
output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"output": str(output), "passed": report["uniquePassedPytestCases"], "skipped": len(skipped), "renders": len(renders)}))
