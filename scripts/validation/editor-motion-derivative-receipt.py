"""Reproduce curve probes and record final test receipts; no renderer/provider calls."""
from __future__ import annotations

import hashlib
import json
import platform
import sys
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.domain.studios.motion import MotionTrackV1  # noqa: E402
from app.domain.studios.motion_derivatives import track_derivative  # noqa: E402

directory = ROOT / "docs/studios/research/editor-oss-20261002"
receipts = []
for name in ["motion-derivative-final-tests.xml", "motion-derivative-regression-tests.xml"]:
    path = directory / name
    cases = ET.parse(path).findall(".//testcase")
    counts = {tag: sum(case.find(tag) is not None for case in cases) for tag in ["failure", "error", "skipped"]}
    if counts["failure"] or counts["error"] or counts["skipped"]:
        raise SystemExit(f"Unqualified final receipt: {name}: {counts}")
    receipts.append({"path": path.relative_to(ROOT).as_posix(), "tests": len(cases),
                     "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), **counts})

track = MotionTrackV1.model_validate({
    "trackId": "probe", "targetLayerId": "title", "property": "position_x", "unit": "pixels",
    "keyframes": [{"frame": 0, "value": 0, "easing": "cubic_bezier", "cubicBezier": [0.22, 0.75, 0.25, 1]},
                  {"frame": 30, "value": 100}],
})
begin = perf_counter()
results = [track_derivative(track, 30, order)[0] for _ in range(1000) for order in [1, 2]]
elapsed = perf_counter() - begin
sources = ["backend/app/domain/studios/motion.py", "backend/app/domain/studios/motion_derivatives.py",
           "backend/tests/test_motion_derivatives.py", "backend/tests/test_studio_motion_graph.py",
           "backend/tests/test_studio_motion_graph_api.py", "scripts/validation/editor-motion-derivative-receipt.py"]
report = {
    "schemaVersion": "res.motion-derivative-receipt.v1", "generatedAt": datetime.now(UTC).isoformat(),
    "evidenceLevel": "contract_math_and_actual_api_gates; renderer_interpolation_unchanged",
    "tests": receipts, "testCountsOverlap": True,
    "sources": [{"path": name, "sha256": hashlib.sha256((ROOT / name).read_bytes()).hexdigest()} for name in sources],
    "localTiming": {"platform": platform.platform(), "python": platform.python_version(), "segments": 1000,
                    "ordersPerSegment": 2, "elapsedSeconds": elapsed, "peakVelocity": results[0],
                    "peakAcceleration": results[1], "limitations": "Single warmed-process run, identical segment repeated; no p95, render, memory or realtime claim."},
    "method": "quadratic analytic bounds; cubic dy/dx and (y''x'-y'x'')/(x')^3; polynomial critical roots",
    "numerics": {"bisectionIterations": 60, "rootResidualRelativeTolerance": 1e-12,
                 "singularTimeDerivativeCutoff": 1e-10, "joinVelocityRelativeAndAbsoluteTolerance": 1e-9},
    "limitations": ["Singular/near-singular nonidentity Bezier curves abstain, even if a removable limit might exist.",
                    "Bounds describe intended continuous interpolation, not sub-iteration derivative of runtime's 18-step inversion.",
                    "No new MP4 or aesthetic/human qualification in this increment; earlier render receipts remain historical.",
                    "First broad run had one legacy fixture loaded before its expected peak/threshold update; preserved in motion-derivative-tests.xml."],
    "externalCodeCopied": False,
}
(directory / "motion-derivative-receipt.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"tests": receipts, "localTiming": report["localTiming"]}, ensure_ascii=False))
