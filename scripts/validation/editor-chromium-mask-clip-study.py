"""Pin the actual rectangle clip call and default in the installed Chromium."""
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
    "core/paint/svg_mask_painter.cc": ["context.Clip(masker->ResourceBoundingBox(reference_box, zoom));"],
    "platform/graphics/graphics_context.h": ["void Clip(const gfx::RectF& rect)", "void ClipRect(const SkRect&", "AntiAliasingMode = kNotAntiAliased"],
    "platform/graphics/graphics_context.cc": ["void GraphicsContext::ClipRect", "canvas_->clipRect"],
}
records = []
for file, markers in targets.items():
    url = f"https://chromium.googlesource.com/chromium/src/+/{version}/third_party/blink/renderer/{file}"
    with urllib.request.urlopen(url + "?format=TEXT", timeout=20) as response:
        raw = base64.b64decode(response.read(), validate=True)
    lines = raw.decode("utf-8").splitlines()
    locations = {marker: [i + 1 for i, line in enumerate(lines) if marker in line] for marker in markers}
    assert all(locations.values()), "upstream_marker_drift"
    records.append({"url": url, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
                    "lines": len(lines), "selectedSymbolLines": locations})
report = {"scope": "selected_primary_sources_read_in_memory_no_clone_no_implementation_copied",
          "browserVersion": browser["installedBrowserVersion"], "browserSha256": browser["installedBrowserSha256"],
          "license": "Chromium BSD-style; no implementation copied", "sources": records,
          "scriptSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          "finding": "SVG mask resource bounds call GraphicsContext::Clip(RectF), whose ClipRect default is kNotAntiAliased.",
          "limitation": "The call does not establish the device raster transform or a universal final pixel-center/coverage-squared model.",
          "productionAdmission": "pending"}
(STUDY / "chromium-mask-clip-study.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps({"browser": report["browserVersion"], "sources": len(records), "finding": report["finding"]}))
