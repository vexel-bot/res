"""Consolidate actual final-font layout evidence; human scoring stays pending."""
import hashlib
import json
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / "docs/studios/research/editor-oss-20261002"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


cases, tests = set(), []
for name in [
    "text-layout-regression-tests.xml", "text-layout-policy-tests.xml", "text-layout-real-tests.xml",
    "text-layout-font-parent-tests.xml", "text-layout-real-negative-regression-tests.xml",
]:
    path = DIRECTORY / name
    found = ET.parse(path).findall(".//testcase")
    if any(case.find(tag) is not None for case in found for tag in ["failure", "error", "skipped"]):
        raise SystemExit("Incomplete evidence: " + name)
    cases.update((case.get("classname"), case.get("name")) for case in found)
    tests.append({"path": path.relative_to(ROOT).as_posix(), "cases": len(found), "sha256": sha(path)})

dom_path = DIRECTORY / "text-layout-dom-study.json"
dom = json.loads(dom_path.read_text(encoding="utf-8"))
if dom["passed"] != 13 or any(case["status"] != "passed" for case in dom["cases"]):
    raise SystemExit("DOM study incomplete")
for name, checksum in dom["sourceHashes"].items():
    if sha(ROOT / name) != checksum:
        raise SystemExit("DOM evidence has stale executable source: " + name)

renders = []
for variant in ["unicode", "wrapped_words"]:
    folder = DIRECTORY / "text-layout-render" / variant
    evidence = json.loads((folder / "evidence.json").read_text(encoding="utf-8"))
    result = evidence["renderResult"]
    if sha(folder / "typography.mp4") != result["artifact"]["checksumSha256"]:
        raise SystemExit("Video checksum conflict: " + variant)
    if result["qualityEvaluation"]["status"] != "passed" or result["providerVersion"] != "4.0.527-native.7":
        raise SystemExit("Render QC/runtime conflict: " + variant)
    typography = evidence["selectedGeometry"][3]["hero"]["typography"]
    layout = typography["layout"]
    renders.append({
        "variant": variant, "scope": evidence["scope"], "jobId": result["jobId"], "documentId": result["documentId"],
        "documentRevision": result["documentRevision"], "provider": result["provider"],
        "providerVersion": result["providerVersion"], "video": (folder / "typography.mp4").relative_to(ROOT).as_posix(),
        "videoSha256": result["artifact"]["checksumSha256"], "videoBytes": result["artifact"]["sizeBytes"],
        "width": 320, "height": 320, "fps": 30, "frames": 60, "renderDurationMs": result["renderDurationMs"],
        "qcStatus": "passed", "font": evidence["font"], "completeFrame": typography["completeFrame"],
        "animatedCount": typography["animatedCount"], "requestedFontSizePx": layout["requestedFontSizePx"],
        "effectiveFontSizePx": layout["fontSizePx"], "lineCount": len(layout["lines"]),
        "contentHeightPx": layout["contentHeightPx"], "pixels": evidence["decodedPixelChecks"],
        "evidenceSha256": sha(folder / "evidence.json"),
    })

negative = json.loads((DIRECTORY / "text-layout-negative/negative.json").read_text(encoding="utf-8"))
style = json.loads((DIRECTORY / "text-layout-negative/style-parent.json").read_text(encoding="utf-8"))
if negative["outputPublished"] or "does_not_fit_at_reading_floor" not in negative["diagnostic"]:
    raise SystemExit("Negative render evidence invalid")
if sha(DIRECTORY / "text-layout-negative/style-parent.mp4") != style["videoSha256"]:
    raise SystemExit("Style/parent video checksum conflict")
sources = [
    "backend/app/domain/studios/typography.py", "backend/app/services/studios/native_motion_recipes.py",
    "backend/app/providers/studios/remotion_projection.py", "backend/app/providers/studios/remotion_render.py",
    "workers/remotion-benchmark/src/hybrid.tsx", "workers/remotion-benchmark/src/typography-layout.tsx",
    "workers/remotion-benchmark/render-hybrid.mjs", "workers/remotion-benchmark/tests/typography-layout-study.tsx",
    "backend/tests/test_typography_layout.py", "backend/tests/test_typography_layout_render.py",
    "backend/tests/test_typography_units.py", "backend/tests/test_typography_render.py",
    "scripts/validation/editor-text-layout-dom-study.mjs", "scripts/validation/editor-text-layout-receipt.py",
]
report = {
    "schemaVersion": "res.typography-layout-receipt.v1", "generatedAt": datetime.now(UTC).isoformat(),
    "qualification": "implemented_with_technical_evidence", "humanReview": "pending",
    "compilerVersion": "res.native-recipes.v3", "componentLibraryVersion": 5,
    "providerVersion": "4.0.527-native.7", "policy": "dom.units-fit.v1", "legacyVersionsReadable": [1, 2],
    "tests": tests, "uniquePytestCases": len(cases), "testReceiptsOverlap": True,
    "officialUnicode17Vectors": 766, "actualBrowserCases": 13, "actualBrowserStudySha256": sha(dom_path),
    "renders": renders, "negativeOutputPublished": False,
    "negativeScope": negative["scope"], "negativeEvidenceSha256": sha(DIRECTORY / "text-layout-negative/negative.json"),
    "animatedStyleParentScope": style["scope"], "animatedStyleParentVideoSha256": style["videoSha256"],
    "animatedStyleParentHoldPixelDifference": style["holdMeanAbsoluteChannelDifference"],
    "sources": {name: sha(ROOT / name) for name in sources},
    "cleanup": {"status": "blocked_by_policy", "clonesLogicalBytesPreviouslyMeasured": 3831737,
                "newBrowserBundlesLogicalBytes": 59308030, "bundles": [
                    "tmp/text-layout-dom-study-4f29b935-7ff5-4177-9c84-e513542a1027",
                    "tmp/text-layout-dom-study-820d0c1d-7987-4b05-9dbf-7b887596136c",
                ], "noRemovalWorkaroundAttempted": True},
    "limitations": [
        "Ink metrics do not prove decoded pixel coverage or transformed clipping; fit constrains local DOM wrapping/block height.",
        "No human readability/mobile/esthetic/commercial/autonomy qualification.",
        "Explicit font fixture covers Latin accents. Emoji/Indic shaping and kerning across unit spans remain unqualified.",
        "Legacy integrated_typography V1 and recipes compiler v1/v2 retain their historical fitting.",
        "Unbound platform fonts are identified as unfixed_platform_font.",
        "Eight positive render tests and one negative do not establish p95/realtime performance.",
        "24/60-fps trim/speed fixtures passed this regression; earlier failures remain historical evidence.",
    ],
}
path = DIRECTORY / "text-layout-receipt.json"
path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"path": str(path), "pytestCases": len(cases), "browserCases": 13, "renders": len(renders)}))
