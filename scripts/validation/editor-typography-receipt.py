"""Consolidate canonical typography proof without calling paid providers."""

from __future__ import annotations

import hashlib
import json
import sys
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.domain.studios.typography import SEGMENTATION_POLICY, SEGMENTER_VERSION  # noqa: E402

directory = ROOT / "docs/studios/research/editor-oss-20261002"
unique_cases = set()
tests = []
for name in [
    "typography-contract-tests.xml",
    "typography-regression-tests.xml",
    "typography-real-regression-tests.xml",
    "typography-native-pixel-regression-tests.xml",
]:
    path = directory / name
    cases = ET.parse(path).findall(".//testcase")
    counts = {
        tag: sum(case.find(tag) is not None for case in cases)
        for tag in ["failure", "error", "skipped"]
    }
    if any(counts.values()):
        raise SystemExit(f"Incomplete final evidence: {name}: {counts}")
    unique_cases.update((case.get("classname"), case.get("name")) for case in cases)
    tests.append(
        {
            "path": path.relative_to(ROOT).as_posix(),
            "tests": len(cases),
            **counts,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    )
evidence = json.loads(
    (directory / "typography-render/evidence.json").read_text(encoding="utf-8")
)
runtime = json.loads(
    (directory / "typography-runtime-study.json").read_text(encoding="utf-8")
)
video = directory / "typography-render/typography.mp4"
checksum = hashlib.sha256(video.read_bytes()).hexdigest()
if (
    checksum != evidence["renderResult"]["artifact"]["checksumSha256"]
    or not runtime["passed"]
):
    raise SystemExit("Typography evidence checksum/runtime conflict")
sources = [
    "backend/app/domain/studios/typography.py",
    "backend/app/services/studios/native_motion_recipes.py",
    "backend/app/providers/studios/remotion_projection.py",
    "backend/app/providers/studios/remotion_render.py",
    "backend/app/services/studios/contextual_editing_v2.py",
    "backend/requirements.txt",
    "workers/remotion-benchmark/src/hybrid.tsx",
    "workers/remotion-benchmark/render-hybrid.mjs",
    "backend/tests/test_typography_units.py",
    "backend/tests/test_typography_font_binding.py",
    "backend/tests/test_typography_render.py",
    "scripts/validation/editor-typography-vectors.py",
    "scripts/validation/editor-typography-runtime-study.mjs",
    "scripts/validation/editor-typography-receipt.py",
]
data = ROOT / "backend/tests/fixtures/unicode17/GraphemeBreakTest.txt"
official_vectors = sum(
    bool(line.split("#", 1)[0].strip())
    for line in data.read_text(encoding="utf-8").splitlines()
)
if official_vectors != 766:
    raise SystemExit("Official vector set changed")
result = evidence["renderResult"]
report = {
    "schemaVersion": "res.typography-receipt.v1",
    "generatedAt": datetime.now(UTC).isoformat(),
    "policy": SEGMENTATION_POLICY,
    "dependency": {
        "name": "regex",
        "version": SEGMENTER_VERSION,
        "licenseExpression": "Apache-2.0 AND CNRI-Python",
        "source": "https://pypi.org/project/regex/2026.1.15/",
    },
    "tests": tests,
    "uniqueTestCases": len(unique_cases),
    "receiptsOverlap": True,
    "officialVectors": {
        "count": official_vectors,
        "sha256": hashlib.sha256(data.read_bytes()).hexdigest(),
        "path": data.relative_to(ROOT).as_posix(),
        "source": "https://www.unicode.org/Public/17.0.0/ucd/auxiliary/GraphemeBreakTest.txt",
        "license": "Unicode License V3",
        "licensePath": "backend/tests/fixtures/unicode17/LICENSE.txt",
    },
    "runtimeStudy": {
        "cases": len(runtime["checks"]),
        "negativeCases": len(runtime["negativeChecks"]),
        "sha256": hashlib.sha256(
            (directory / "typography-runtime-study.json").read_bytes()
        ).hexdigest(),
    },
    "render": {
        "path": video.relative_to(ROOT).as_posix(),
        "sha256": checksum,
        "bytes": video.stat().st_size,
        "width": 320,
        "height": 320,
        "fps": 30,
        "frames": result["framesRendered"],
        "durationSeconds": 2,
        "providerVersion": result["providerVersion"],
        "font": evidence["font"],
        "pixels": evidence["decodedPixelChecks"],
        "technicalQC": evidence["renderMetadata"]["qualityEvaluation"]["status"],
        "humanReview": "pending",
        "sound": "FFmpeg silent AAC; no speech/music sync qualification",
    },
    "sources": [
        {"path": path, "sha256": hashlib.sha256((ROOT / path).read_bytes()).hexdigest()}
        for path in sources
    ],
    "limitations": [
        "Native integrated_typography V1 and historical v1 recipe snapshots retain legacy segmentation.",
        "DOM span bounds are layout/transform diagnostics, not measured ink/pixel coverage or reading quality.",
        "Real font proof covers decomposed Latin accents, not every emoji, Indic shaping or line-wrap extreme.",
        "A font binary is not retained; reproduce with the same licensed local font checksum or qualify another font separately.",
        "No 15s/1080p performance, p95, commercial approval, blind preference or autonomous brief qualification.",
    ],
    "editorSourceCodeCopied": False,
    "officialTestDataRetained": True,
}
(directory / "typography-receipt.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(
    json.dumps(
        {
            "uniqueTestCases": len(unique_cases),
            "officialVectors": official_vectors,
            "render": report["render"],
        },
        ensure_ascii=True,
    )
)
