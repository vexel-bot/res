"""Pin selected upstream mask paths, retaining metadata rather than a clone."""
import base64
import hashlib
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / "docs/studios/research/editor-oss-20261002"
browser = json.loads((STUDY / "spatial-effects-browser-sources.json").read_text(encoding="utf-8"))
assert hashlib.sha256(Path(browser["browserPath"]).read_bytes()).hexdigest() == browser["installedBrowserSha256"]
version = browser["installedBrowserVersion"].rsplit(" ", 1)[1]
assert version == "149.0.7790.0"
targets = {
    "css_mask_painter.cc": ["CSSMaskPainter::MaskBoundingBox", "EFillBox::kNoClip", "PhysicalBorderBoxRect"],
    "svg_mask_painter.cc": ["SVGMaskPainter::PaintSVGMaskLayer", "context.Clip(masker->ResourceBoundingBox",
                             "SVGMaskPainter::ResourceBoundsForSVGChild"],
    "paint_layer.cc": ["PhysicalRect PaintLayer::LocalBoundingBox()", "VisualOverflowRect()",
                       "PhysicalRect PaintLayer::LocalBoundingBoxIncludingSelfPaintingDescendants()"],
}
records = []
for name, markers in targets.items():
    url = f"https://chromium.googlesource.com/chromium/src/+/{version}/third_party/blink/renderer/core/paint/{name}"
    with urllib.request.urlopen(url + "?format=TEXT", timeout=20) as response:
        raw = base64.b64decode(response.read(), validate=True)
    lines = raw.decode("utf-8").splitlines()
    references = {marker: [index + 1 for index, line in enumerate(lines) if marker in line] for marker in markers}
    assert all(references.values()), "upstream_markers_changed"
    records.append({"url": url, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
                    "lines": len(lines), "selectedSymbolLines": references})
report = {
    "scope": "selected_primary_sources_read_in_memory_no_clone_no_source_code_copied",
    "installedBrowserVersion": browser["installedBrowserVersion"],
    "installedBrowserSha256": browser["installedBrowserSha256"],
    "license": "Chromium BSD-style; no implementation copied",
    "scriptSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "sources": records,
    "findings": [
        "CSSMaskPainter bounds ordinary boxes by the border box unless LayersClipMax is no-clip.",
        "The no-clip path uses local visual overflow including self-painting descendants.",
        "SVGMaskPainter also clips the mask paint record by its SVG resource bounds.",
    ],
    "inference": "Two separate bounds can affect coverage; changing SVG mask attributes alone does not remove the HTML box bound.",
    "limitation": "Source inspection does not establish which raster stage causes each observed pixel or prescribe a unique AA oracle.",
    "productionAdmission": "pending",
}
(STUDY / "chromium-mask-bounds-study.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps({"browser": report["installedBrowserVersion"], "sources": len(records),
                  "sourceBytesReadInMemory": sum(record["bytes"] for record in records)}))
