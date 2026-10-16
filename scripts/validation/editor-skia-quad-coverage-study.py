"""Read exact installed-browser quad AA sources in memory, without cloning."""
import base64
import hashlib
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / "docs/studios/research/editor-oss-20261002"
browser = json.loads((STUDY / "spatial-effects-browser-sources.json").read_text(encoding="utf-8"))
assert hashlib.sha256(Path(browser["browserPath"]).read_bytes()).hexdigest() == browser["installedBrowserSha256"]
revision = browser["skiaRevisionFromChromiumDeps"]
targets = {
    "src/gpu/ganesh/ops/QuadPerEdgeAA.cpp": ["edgeDistances = 0.5f", "fAAHelper.inset", "fAAHelper.outset", "float coverage", "geomSubset"],
    "src/gpu/ganesh/geometry/GrQuadUtils.cpp": ["inset", "outset", "edge", "coverage"],
    "src/core/SkCanvas.cpp": ["void SkCanvas::clipPath", "rectStaysRect", "this->topDevice()->clipPath"],
    "src/gpu/ganesh/ClipStack.cpp": ["clip", "coverage", "analytic"],
}
records = []
for file, markers in targets.items():
    url = f"https://skia.googlesource.com/skia/+/{revision}/{file}"
    with urllib.request.urlopen(url + "?format=TEXT", timeout=25) as response:
        raw = base64.b64decode(response.read(), validate=True)
    lines = raw.decode("utf-8").splitlines()
    locations = {marker: [i + 1 for i, line in enumerate(lines) if marker in line] for marker in markers}
    assert all(locations.values()), (file, "upstream_marker_drift")
    records.append({"url": url, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
                    "lines": len(lines), "selectedSymbolLines": locations})
    for marker in markers[:4]:
        print(json.dumps({"file": file, "marker": marker, "firstLines": locations[marker][:8]}))
report = {"scope": "selected_primary_sources_read_in_memory_no_clone_no_implementation_copied",
          "browserVersion": browser["installedBrowserVersion"], "browserSha256": browser["installedBrowserSha256"],
          "skiaRevision": revision, "license": "Skia BSD-style; no implementation copied", "sources": records,
          "scriptSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          "finding": "Ganesh quad AA insets/outsets edges by a half device pixel and interpolates vertex coverage.",
          "inference": "For large affine convex quads, a minimum of normalized edge ramps is a research candidate, not exact area intersection.",
          "limitation": "This source path alone does not prove that every installed-browser draw uses this operation.",
          "productionAdmission": "pending"}
(STUDY / "skia-quad-coverage-study.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
