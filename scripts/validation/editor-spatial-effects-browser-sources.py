"""Pin selected primary browser research without cloning or retaining source trees."""
import base64
import hashlib
import json
import re
import subprocess
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / "docs/studios/research/editor-oss-20261002"
browser = ROOT / ("workers/remotion-benchmark/node_modules/.remotion/chrome-headless-shell/win64/"
                  "chrome-headless-shell-win64/chrome-headless-shell.exe")
version = subprocess.run([str(browser), "--version"], capture_output=True, text=True, check=True,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout.strip()
assert version == "Google Chrome for Testing 149.0.7790.0"


def read(url):
    return base64.b64decode(urllib.request.urlopen(url + "?format=TEXT", timeout=30).read())


deps_url = "https://chromium.googlesource.com/chromium/src/+/refs/tags/149.0.7790.0/DEPS"
deps = read(deps_url)
revision = re.search(rb"'skia_revision':\s*'([0-9a-f]+)'", deps).group(1).decode()
assert revision == "0cb35533022b3912904831c2290680bb8eea0363"
records = [{"url": deps_url, "sha256": hashlib.sha256(deps).hexdigest(), "bytes": len(deps)}]
for name in ["src/core/SkBlurEngine.cpp", "src/core/SkBlurEngine.h",
             "src/effects/imagefilters/SkBlurImageFilter.cpp", "LICENSE"]:
    url = f"https://skia.googlesource.com/skia/+/{revision}/{name}"
    content = read(url)
    records.append({"url": url, "sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content),
                    "lines": len(content.splitlines())})
digest = hashlib.sha256()
with browser.open("rb") as handle:
    for block in iter(lambda: handle.read(1024 * 1024), b""):
        digest.update(block)
report = {"scope": "selected_primary_sources_read_in_memory_no_repository_clone_no_source_code_copied",
          "installedBrowserVersion": version, "installedBrowserSha256": digest.hexdigest(),
          "browserPath": str(browser), "skiaRevisionFromChromiumDeps": revision,
          "license": "Skia BSD-style; no implementation copied", "sources": records,
          "inference": "Source has backend/build-dependent kernels; exact branch executed is not observed",
          "experiment": "Controlled actual job sigma .25/.75 had sharp edges under default GL; explicit swangle passed strong temporal fixture"}
(DIRECTORY / "spatial-effects-browser-sources.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps({"sources": len(records), "browserVersion": version, "repositoryClones": 0}))
