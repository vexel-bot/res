"""Real archived-layer recovery, animated alpha and FilmCraft composition linkage.

Run against the isolated QA API after acceptance.py. No engine is mocked.
"""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
from uuid import uuid4
import requests
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / ".codex-runtime/craft"
ORIGIN = "http://127.0.0.1:8018"


def main():
    session = requests.Session()
    token = json.loads((OUTPUT / "frontend-qa-auth.json").read_text())["token"]
    session.headers["Authorization"] = "Bearer " + token

    def call(method, path, body=None, expected=200, binary=False, key=None):
        response = session.request(
            method,
            ORIGIN + path,
            json=body,
            headers={"Idempotency-Key": key or str(uuid4())},
            timeout=600,
        )
        assert response.status_code == expected, (
            path,
            response.status_code,
            response.text[:1200],
        )
        return response.content if binary else response.json()

    workspace = call("GET", "/api/v1/bootstrap")["workspaces"][0]["id"]
    document = call(
        "POST",
        "/api/v1/studios/v1/documents",
        {
            "workspaceId": workspace,
            "title": "Real migration composition recovery",
            "contentType": "video",
            "brandRevision": 1,
            "brief": {
                "objective": "Recover editable visual layers without duplicating footage",
                "audience": "QA",
            },
            "composition": {
                "pages": [
                    {
                        "id": "visual-page",
                        "width": 320,
                        "height": 320,
                        "background": "#112233",
                        "durationMs": 500,
                        "layers": [
                            {
                                "id": "overlay",
                                "kind": "shape",
                                "name": "Animated overlay",
                                "x": 0,
                                "y": 0,
                                "width": 160,
                                "height": 160,
                                "properties": {"fill": "#ff0000"},
                            }
                        ],
                    }
                ],
                "mediaTimeline": {
                    "schemaVersion": "studio.media-timeline.v1",
                    "frameRate": {"numerator": 30, "denominator": 1},
                    "durationFrames": 15,
                    "tracks": [],
                },
                "narrative": {
                    "motionGraph": {
                        "frameRate": {"numerator": 30, "denominator": 1},
                        "durationFrames": 15,
                        "tracks": [
                            {
                                "targetLayerId": "overlay",
                                "property": "opacity",
                                "keyframes": [
                                    {"frame": 0, "value": 0.0},
                                    {"frame": 10, "value": 1.0},
                                ],
                            }
                        ],
                    }
                },
            },
        },
        201,
    )
    base = "/api/v1/studios/v1/documents/" + document["documentId"]
    state = call(
        "POST",
        base + "/craft/migrate",
        {"engine": "filmcraft", "expectedRevision": document["revision"]},
    )
    receipt = call(
        "POST",
        base + "/craft/commands",
        {
            "expectedRevision": state["revision"],
            "commands": [
                {
                    "id": "file.newColorMatte",
                    "params": {"color": "#0000ff", "seconds": 0.5},
                }
            ],
        },
    )
    items = receipt["inspection"]["project"]["raw"]["project"]
    item = next(
        entry["item"]
        for entry in items["root"]["children"]
        if entry.get("item") and entry["item"] != items.get("activeSequence")
    )
    receipt = call(
        "POST",
        base + "/craft/commands",
        {
            "expectedRevision": receipt["document"]["revision"],
            "commands": [
                {
                    "id": "timeline.place",
                    "params": {
                        "item": item,
                        "seconds": 0,
                        "video": True,
                        "audio": False,
                        "insert": False,
                    },
                }
            ],
        },
    )
    before = call("GET", base + "/native-project", binary=True)
    key, revision = str(uuid4()), receipt["document"]["revision"]
    recovered = call(
        "POST", base + "/craft/recover-effects", {"expectedRevision": revision}, key=key
    )
    assert recovered["requiresCompositionReview"]
    assert call("GET", base + "/native-project", binary=True) == before
    assert (
        call(
            "POST",
            base + "/craft/recover-effects",
            {"expectedRevision": revision},
            key=key,
        )["receiptId"]
        == recovered["receiptId"]
    )
    call(
        "POST",
        base + "/craft/recover-effects",
        {"expectedRevision": revision},
        expected=409,
    )
    source = "/api/v1/studios/v1/documents/" + recovered["compositionDocumentId"]
    child = call("GET", source)
    assert child["composition"]["mediaTimeline"] is None
    assert child["composition"]["pages"][0]["background"] == "#00000000"
    frames = {}
    for frame in (0, 10):
        payload = call("POST", source + "/craft/preview", {"frame": frame}, binary=True)
        with Image.open(io.BytesIO(payload)) as png:
            image = png.convert("RGBA")
            assert image.getpixel((300, 300))[3] == 0
            if frame == 0:
                assert image.getpixel((80, 80))[3] == 0
            else:
                assert (
                    image.getpixel((80, 80))[0] > 220
                    and image.getpixel((80, 80))[3] > 220
                )
        frames[str(frame)] = hashlib.sha256(payload).hexdigest()
    linked = call(
        "POST",
        base + "/craft/link-composition",
        {
            "expectedRevision": recovered["document"]["revision"],
            "compositionDocumentId": child["documentId"],
        },
    )
    for frame in (0, 10):
        payload = call("POST", base + "/craft/preview", {"frame": frame}, binary=True)
        with Image.open(io.BytesIO(payload)) as png:
            pixel = png.convert("RGB").getpixel((80, 80))
            assert pixel[2] > 220 if frame == 0 else pixel[0] > 220, (frame, pixel)
    (OUTPUT / "recovery-acceptance-results.json").write_text(
        json.dumps(
            {
                "schemaVersion": "clicko.craft-recovery-acceptance.v1",
                "documentId": document["documentId"],
                "compositionDocumentId": child["documentId"],
                "recoveredAnimation": True,
                "transparentOverlay": True,
                "montageNativeBytesPreserved": True,
                "revisionConflict": True,
                "idempotentReplay": True,
                "linkedRevision": linked["document"]["revision"],
                "effectFrameSha256": frames,
            },
            indent=2,
        )
        + "\n"
    )
    print(
        "Passed real archived-layer recovery, animated alpha and transparent FilmCraft linkage",
        flush=True,
    )


if __name__ == "__main__":
    main()
