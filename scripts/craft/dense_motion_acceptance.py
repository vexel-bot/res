"""Real HTTP/native qualification above the former 10,000-key import limit."""

import hashlib
import io
import json
from pathlib import Path
from uuid import uuid4

from PIL import Image
import requests

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / ".codex-runtime/craft"


def main():
    session = requests.Session()
    session.headers["Authorization"] = "Bearer " + json.loads((OUTPUT / "frontend-qa-auth.json").read_text())["token"]

    def call(method, path, body=None, expected=200, binary=False):
        result = session.request(method, "http://127.0.0.1:8018" + path, json=body,
                                 headers={"Idempotency-Key": str(uuid4())}, timeout=600)
        assert result.status_code == expected, (result.status_code, result.text[:1000])
        return result.content if binary else result.json()

    workspace = call("GET", "/api/v1/bootstrap")["workspaces"][0]["id"]
    page = {"id": "dense", "width": 320, "height": 320, "durationMs": 1200000,
            "background": "#00000000", "layers": [{"id": "square", "kind": "shape", "x": 0, "y": 0,
                "width": 8, "height": 8, "properties": {"fill": "#ff0000"}}]}
    graph = {"schemaVersion": "studio.motion-graph.v1", "frameRate": {"numerator": 10, "denominator": 1},
             "durationFrames": 12000, "tracks": [{"targetLayerId": "square", "property": "opacity",
                 "keyframes": [{"frame": 0, "value": 0, "easing": "linear"}, {"frame": 11999, "value": 1}]}]}
    document = call("POST", "/api/v1/studios/v1/documents", {
        "workspaceId": workspace, "title": "Dense animation native qualification", "contentType": "visual",
        "brief": {"objective": "Recover every sampled opacity key", "audience": "QA"},
        "composition": {"pages": [page], "narrative": {"motionGraph": graph}},
    }, expected=201)
    base = "/api/v1/studios/v1/documents/" + document["documentId"]
    state = call("POST", base + "/craft/migrate", {"engine": "effectcraft", "expectedRevision": document["revision"]})
    assert state["nativeEditorState"]["buildId"] == "clicko-effectcraft-1.0.2+67434e90"
    assert not any("keyframe budget" in warning for warning in state.get("migrationWarnings", []))
    frames = []
    for frame, alpha in [(0, 0), (6000, 128), (11999, 255)]:
        png = call("POST", base + "/craft/preview", {"frame": frame}, binary=True)
        with Image.open(io.BytesIO(png)) as image:
            assert image.convert("RGBA").getpixel((4, 4))[3] == alpha
        (OUTPUT / f"dense-native-{frame}.png").write_bytes(png)
        frames.append({"frame": frame, "alpha": alpha, "sha256": hashlib.sha256(png).hexdigest()})
    native = call("GET", base + "/native-project", binary=True)
    (OUTPUT / "dense-native.ecproj").write_bytes(native)
    assert call("GET", base + "/craft/inspection")["nativeEditorState"]["checksumSha256"] == hashlib.sha256(native).hexdigest()
    assert call("POST", base + "/craft/preview", {"frame": 6000}, binary=True) == (OUTPUT / "dense-native-6000.png").read_bytes()
    fixture = {"width": 320, "height": 320, "fps": 10, "durationMs": 1200000,
               "legacyDocument": {"composition": {"pages": [page]}}, "legacyMotionGraph": graph}
    (OUTPUT / "dense-fixture.json").write_text(json.dumps(fixture))
    result = {"documentId": document["documentId"], "buildId": state["nativeEditorState"]["buildId"],
              "sampledFrames": 12000, "nativeReopened": True, "frames": frames,
              "nativeSha256": hashlib.sha256(native).hexdigest()}
    (OUTPUT / "dense-motion-results.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result))


if __name__ == "__main__":
    main()
