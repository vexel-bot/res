"""Pin installed Chromium's SwiftShader precision sources without a clone."""
import base64
import hashlib
import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / "docs/studios/research/editor-oss-20261002"
browser = json.loads((STUDY / "spatial-effects-browser-sources.json").read_text(encoding="utf-8"))
assert hashlib.sha256(Path(browser["browserPath"]).read_bytes()).hexdigest() == browser["installedBrowserSha256"]
records = []


def read(url, markers):
    with urllib.request.urlopen(url + "?format=TEXT", timeout=25) as response:
        raw = base64.b64decode(response.read(), validate=True)
    lines = raw.decode("utf-8").splitlines()
    locations = {marker: [i + 1 for i, line in enumerate(lines) if marker in line] for marker in markers}
    assert all(locations.values()), (url, "source_marker_drift")
    records.append({"url": url, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
                    "lines": len(lines), "selectedSymbolLines": locations})
    return raw.decode("utf-8")


deps = read("https://chromium.googlesource.com/chromium/src/+/149.0.7790.0/DEPS", ["'swiftshader_revision'"])
revision = re.search(r"'swiftshader_revision': '([0-9a-f]{40})'", deps).group(1)
assert revision == "89556131bf9d48af3c5c9fbb9a3322e706da89a3"
root = "https://swiftshader.googlesource.com/SwiftShader/+/" + revision + "/"
for file, markers in {
    "src/Device/BUILD.gn": ["SWIFTSHADER_LEGACY_PRECISION=true"],
    "src/Pipeline/BUILD.gn": ["SWIFTSHADER_LEGACY_PRECISION=true"],
    "src/Vulkan/BUILD.gn": ["SWIFTSHADER_LEGACY_PRECISION=true"],
    "src/Vulkan/VkConfig.hpp": ["SUBPIXEL_PRECISION_BITS = SWIFTSHADER_LEGACY_PRECISION ? 4 : 8"],
    "src/Pipeline/SetupRoutine.cpp": ["vk::SUBPIXEL_PRECISION_BITS", "vk::SUBPIXEL_PRECISION_FACTOR"],
    "src/Pipeline/VertexRoutine.cpp": ["RoundIntClamped", "X0xF", "WxF"],
    "src/Device/Renderer.cpp": ["SUBPIXEL_PRECISION_FACTOR", "X0xF", "WxF"],
    "src/Vulkan/VkPhysicalDevice.cpp": ["subPixelPrecisionBits"],
}.items():
    read(root + file, markers)
report = {"scope": "selected_primary_sources_read_in_memory_no_clone_no_implementation_copied",
          "browserVersion": browser["installedBrowserVersion"], "browserSha256": browser["installedBrowserSha256"],
          "swiftshaderRevision": revision, "gnBuildSubpixelBits": 4, "gnBuildSubpixelGrid": "1/16 pixel",
          "license": "SwiftShader Apache-2.0; no implementation copied", "sources": records,
          "scriptSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          "limitation": "Source GN defaults require confirmation of installed runtime and paint path; this is not a fitted pixel oracle.",
          "productionAdmission": "pending"}
(STUDY / "swiftshader-subpixel-study.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps({"revision": revision, "sources": len(records), "gnSubpixelBits": 4}))
