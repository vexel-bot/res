"""Check real EffectCraft group migration, inherited alpha and native reopening."""

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
    session.headers["Authorization"] = (
        "Bearer " + json.loads((OUTPUT / "frontend-qa-auth.json").read_text())["token"]
    )

    def call(method, path, body=None, expected=200, binary=False):
        response = session.request(
            method,
            "http://127.0.0.1:8018" + path,
            json=body,
            headers={"Idempotency-Key": str(uuid4())},
            timeout=600,
        )
        assert response.status_code == expected, (
            response.status_code,
            response.text[:1200],
        )
        return response.content if binary else response.json()

    workspace = call("GET", "/api/v1/bootstrap")["workspaces"][0]["id"]
    page = {
        "id": "group-page",
        "width": 320,
        "height": 320,
        "durationMs": 200,
        "background": "#00000000",
        "layers": [
            {
                "id": "child",
                "kind": "shape",
                "x": 4,
                "y": 0,
                "width": 4,
                "height": 4,
                "opacity": 0.5,
                "properties": {"fill": "#ff0000"},
            },
            {
                "id": "group",
                "kind": "group",
                "x": 20,
                "y": 20,
                "width": 16,
                "height": 16,
                "rotation": 90,
                "opacity": 0.5,
                "properties": {},
            },
        ],
    }
    graph = {
        "schemaVersion": "studio.motion-graph.v1",
        "frameRate": {"numerator": 10, "denominator": 1},
        "durationFrames": 2,
        "nodes": [
            {
                "nodeId": "g",
                "targetLayerId": "group",
                "transformOriginX": 0,
                "transformOriginY": 0,
            },
            {"nodeId": "c", "targetLayerId": "child", "parentNodeId": "g"},
        ],
        "tracks": [
            {
                "targetLayerId": "group",
                "property": "position_x",
                "keyframes": [{"frame": 0, "value": 0}, {"frame": 1, "value": 8}],
            },
            {
                "targetLayerId": "group",
                "property": "opacity",
                "keyframes": [{"frame": 0, "value": 0.5}, {"frame": 1, "value": 1}],
            },
        ],
    }
    document = call(
        "POST",
        "/api/v1/studios/v1/documents",
        {
            "workspaceId": workspace,
            "title": "Native group hierarchy QA",
            "contentType": "visual",
            "brandRevision": 1,
            "brief": {
                "objective": "Keep parent transforms and inherited alpha",
                "audience": "QA",
            },
            "composition": {"pages": [page], "narrative": {"motionGraph": graph}},
        },
        expected=201,
    )
    base = "/api/v1/studios/v1/documents/" + document["documentId"]
    state = call(
        "POST",
        base + "/craft/migrate",
        {"engine": "effectcraft", "expectedRevision": document["revision"]},
    )
    assert state["nativeEditorState"]["buildId"] == "clicko-effectcraft-1.0.1+67434e90"
    frames = []
    for frame, x, alpha in [(0, 17, 64), (1, 25, 128)]:
        png = call("POST", base + "/craft/preview", {"frame": frame}, binary=True)
        with Image.open(io.BytesIO(png)) as image:
            assert image.convert("RGBA").getpixel((x, 25)) == (255, 0, 0, alpha)
            assert image.convert("RGBA").getpixel((40, 40))[3] == 0
        (OUTPUT / f"hierarchy-native-{frame}.png").write_bytes(png)
        frames.append(hashlib.sha256(png).hexdigest())
    native = call("GET", base + "/native-project", binary=True)
    (OUTPUT / "hierarchy-native.ecproj").write_bytes(native)
    reopened = call("GET", base + "/craft/inspection")
    assert (
        reopened["nativeEditorState"]["checksumSha256"]
        == hashlib.sha256(native).hexdigest()
    )
    assert (
        call("POST", base + "/craft/preview", {"frame": 1}, binary=True)
        == (OUTPUT / "hierarchy-native-1.png").read_bytes()
    )
    (OUTPUT / "hierarchy-fixture.json").write_text(
        json.dumps(
            {
                "width": 320,
                "height": 320,
                "fps": 10,
                "durationMs": 200,
                "legacyDocument": {"composition": {"pages": [page]}},
                "legacyMotionGraph": graph,
            },
            indent=2,
        )
        + "\n"
    )
    result = {
        "schemaVersion": "clicko.craft-hierarchy-acceptance.v1",
        "documentId": document["documentId"],
        "nativeReopened": True,
        "groupRotationAndMovement": True,
        "inheritedAlpha": True,
        "nativeSha256": hashlib.sha256(native).hexdigest(),
        "frameSha256": frames,
    }
    (OUTPUT / "hierarchy-acceptance-results.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print(json.dumps(result))


if __name__ == "__main__":
    main()
