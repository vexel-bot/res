"""Explicit EffectCraft build upgrade, with real prior-runtime pixel reference and native undo."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from uuid import uuid4

import requests

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / ".codex-runtime/craft"


def main():
    session = requests.Session()
    session.headers["Authorization"] = "Bearer " + json.loads((OUTPUT / "frontend-qa-auth.json").read_text())["token"]

    def call(method, path, body=None, key=None, binary=False, expected=200):
        response = session.request(method, "http://127.0.0.1:8018" + path, json=body,
                                   headers={"Idempotency-Key": key or str(uuid4())}, timeout=600)
        assert response.status_code == expected, (response.status_code, response.text[:1000])
        return response.content if binary else response.json()

    workspace = call("GET", "/api/v1/bootstrap")["workspaces"][0]["id"]
    documents = call("GET", "/api/v1/studios/v1/documents?workspace_id=" + workspace)
    candidates = [item for item in documents if (state := item.get("nativeEditorState"))
                  and state["engine"] == "effectcraft" and state["buildId"] == "clicko-effectcraft-1.0.1+67434e90"
                  and not state["assetManifest"] and not state["fontManifest"] and not state["dependencies"]]
    assert candidates, "Requires a preserved, self-contained QA EffectCraft 1.0.1 project"
    document = candidates[0]
    state = document["nativeEditorState"]
    base = "/api/v1/studios/v1/documents/" + document["documentId"]
    original = call("GET", base + "/native-project", binary=True)
    assert hashlib.sha256(original).hexdigest() == state["checksumSha256"]
    call("GET", base + "/craft/inspection", expected=422)
    with tempfile.TemporaryDirectory(prefix="craft-upgrade-qualification-") as temporary:
        directory = Path(temporary)
        (directory / "source.ecproj").write_bytes(original)
        payload = {"protocolVersion": 1, "requestId": str(uuid4()), "engine": "effectcraft", "method": "render.frame",
                   "params": {"mediaRoot": str(directory), "nativePath": str(directory / "source.ecproj"),
                              "outputPath": str(directory / "previous.png"), "frame": 0}}
        prior = subprocess.run([sys.executable, str(ROOT / "workers/craft/run_adapter.py"), "effectcraft"],
                               input=json.dumps(payload) + "\n", text=True, capture_output=True, timeout=180,
                               env={**os.environ, "CLICKO_CRAFT_RUNTIME_IMAGE": "clicko-craft-runtime:pre-bulk-motion-1.0.1"})
        assert prior.returncode == 0 and not json.loads(prior.stdout).get("error"), prior.stderr[-1000:]
        previous_png = (directory / "previous.png").read_bytes()
    key = str(uuid4())
    request = {"expectedRevision": document["revision"], "targetBuildId": "clicko-effectcraft-1.0.2+67434e90"}
    upgraded = call("POST", base + "/craft/upgrade-build", request, key=key)
    replay = call("POST", base + "/craft/upgrade-build", request, key=key)
    assert replay["receiptId"] == upgraded["receiptId"]
    assert call("POST", base + "/craft/preview", {"frame": 0}, binary=True) == previous_png
    undo = call("POST", base + "/craft/commands", {"expectedRevision": upgraded["document"]["revision"],
                "commands": [{"id": "host.history.undo", "params": {}}]})
    assert call("POST", base + "/craft/preview", {"frame": 0}, binary=True) == previous_png
    assert undo["document"]["nativeEditorState"]["buildId"] == request["targetBuildId"]
    result = {"documentId": document["documentId"], "previousBuildId": state["buildId"],
              "targetBuildId": request["targetBuildId"], "pixelParity": True, "undo": True, "receiptReplay": True,
              "previousNativeSha256": hashlib.sha256(original).hexdigest(), "frameSha256": hashlib.sha256(previous_png).hexdigest()}
    (OUTPUT / "upgrade-build-results.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result))


if __name__ == "__main__":
    main()
