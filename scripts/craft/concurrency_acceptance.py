"""Race two real native edits in the isolated QA API; exactly one revision wins."""

from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
from pathlib import Path
from threading import Barrier
from uuid import uuid4

from PIL import Image
import requests

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / ".codex-runtime/craft"
ORIGIN = "http://127.0.0.1:8018"


def main():
    token = json.loads((OUTPUT / "frontend-qa-auth.json").read_text())["token"]
    headers = {"Authorization": "Bearer " + token}

    def call(method, path, body=None, *, key=None, expected=200, binary=False):
        response = requests.request(
            method,
            ORIGIN + path,
            json=body,
            headers={**headers, "Idempotency-Key": key or str(uuid4())},
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
            "title": "Concurrent native edit QA",
            "contentType": "visual",
            "brandRevision": 1,
            "brief": {"objective": "Reject a concurrent stale edit", "audience": "QA"},
            "composition": {
                "pages": [
                    {
                        "id": "concurrency-page",
                        "width": 320,
                        "height": 320,
                        "background": "#ffffff",
                        "durationMs": 100,
                        "layers": [],
                    }
                ]
            },
        },
        expected=201,
    )
    base = "/api/v1/studios/v1/documents/" + document["documentId"]
    initial = call(
        "POST",
        base + "/craft/migrate",
        {
            "engine": "photocraft",
            "expectedRevision": document["revision"],
        },
    )
    native_path = base + "/native-project?pageId=concurrency-page"
    original = call("GET", native_path, binary=True)
    barrier = Barrier(2)

    def edit(color):
        key = str(uuid4())
        body = {
            "expectedRevision": initial["revision"],
            "pageId": "concurrency-page",
            "commands": [
                {
                    "id": "shape.create",
                    "params": {
                        "kind": "rect",
                        "rect": [0, 0, 160, 160],
                        "fill": color,
                    },
                }
            ],
        }
        barrier.wait(timeout=30)
        response = requests.post(
            ORIGIN + base + "/craft/commands",
            json=body,
            headers={**headers, "Idempotency-Key": key},
            timeout=600,
        )
        return color, key, body, response

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(edit, ["#ff0000", "#0000ff"]))
    assert sorted(item[3].status_code for item in outcomes) == [200, 409], [
        (item[3].status_code, item[3].text[:1200]) for item in outcomes
    ]
    winner = next(item for item in outcomes if item[3].status_code == 200)
    receipt = winner[3].json()
    inspection = call("GET", base + "/craft/inspection?pageId=concurrency-page")
    assert inspection["revision"] == initial["revision"] + 1
    replay = call("POST", base + "/craft/commands", winner[2], key=winner[1])
    assert replay["receiptId"] == receipt["receiptId"]
    preview = call(
        "POST",
        base + "/craft/preview",
        {"frame": 0, "pageId": "concurrency-page"},
        binary=True,
    )
    with Image.open(io.BytesIO(preview)) as image:
        expected = (255, 0, 0, 255) if winner[0] == "#ff0000" else (0, 0, 255, 255)
        assert image.convert("RGBA").getpixel((80, 80)) == expected
    call(
        "POST",
        base + "/craft/commands",
        {
            "expectedRevision": inspection["revision"],
            "pageId": "concurrency-page",
            "commands": [{"id": "host.history.undo", "params": {}}],
        },
    )
    restored = call("GET", native_path, binary=True)
    assert restored == original, "Conflicting edit leaked into the undo snapshot"
    result = {
        "schemaVersion": "clicko.craft-concurrency-acceptance.v1",
        "documentId": document["documentId"],
        "statuses": [200, 409],
        "singleRevisionCommitted": True,
        "winnerReplayStable": True,
        "undoRestoresOriginal": True,
        "originalSha256": hashlib.sha256(original).hexdigest(),
    }
    (OUTPUT / "concurrency-acceptance-results.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print(json.dumps(result))


if __name__ == "__main__":
    main()
