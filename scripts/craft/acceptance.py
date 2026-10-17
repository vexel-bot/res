"""Exercise the real HTTP API and real native engines against the isolated QA database.

Start the QA API on port 8018 with CELERY_TASK_ALWAYS_EAGER=true, then run this
script. No engine, storage or renderer is mocked. Credentials stay in ignored output.
"""

from __future__ import annotations
import hashlib
import io
import json
from pathlib import Path
import time
from uuid import uuid4
import zipfile
import requests
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / ".codex-runtime/craft"
ORIGIN = "http://127.0.0.1:8018"


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    auth_file = OUTPUT / "frontend-qa-auth.json"
    if auth_file.is_file():
        token = json.loads(auth_file.read_text())["token"]
    else:
        response = session.post(
            ORIGIN + "/api/v1/auth/register",
            json={
                "email": f"craft-{uuid4()}@example.com",
                "name": "Craft QA",
                "password": str(uuid4()) + str(uuid4()),
                "workspaceName": "Craft isolated QA",
            },
            timeout=30,
        )
        assert response.status_code == 201, "QA registration failed"
        token = response.json()["accessToken"]
        auth_file.write_text(json.dumps({"token": token}), encoding="utf-8")
    session.headers["Authorization"] = "Bearer " + token

    def call(method, path, body=None, expected=200, key=None, binary=False):
        response = session.request(
            method,
            ORIGIN + path,
            json=body,
            headers={"Idempotency-Key": key or str(uuid4())},
            timeout=600,
        )
        assert response.status_code == expected, (
            f"{method} {path}: {response.status_code} {response.text[:1500]}"
        )
        return response.content if binary else response.json()

    workspace = call("GET", "/api/v1/bootstrap")["workspaces"][0]["id"]
    engines = call("GET", "/api/v1/studios/v1/craft/engines")["engines"]
    assert all(engine["available"] for engine in engines), [
        (e["engine"], e.get("reason")) for e in engines
    ]
    results = []
    for engine in ("photocraft", "filmcraft", "effectcraft"):
        print(
            f"Validating {engine}: create, migrate, edit, reopen, history, preview, export",
            flush=True,
        )
        document = call(
            "POST",
            "/api/v1/studios/v1/documents",
            {
                "workspaceId": workspace,
                "title": "Craft native acceptance " + engine,
                "contentType": "carousel" if engine == "photocraft" else "video",
                "brandRevision": 1,
                "brief": {"objective": "Real native acceptance", "audience": "QA"},
                "composition": {
                    "pages": [
                        {
                            "id": f"page-{index}",
                            "width": 320,
                            "height": 320,
                            "background": "#ffffff",
                            "durationMs": 100,
                            "layers": [],
                        }
                        for index in range(2 if engine == "photocraft" else 1)
                    ]
                },
            },
            expected=201,
        )
        base = "/api/v1/studios/v1/documents/" + document["documentId"]
        state = call(
            "POST",
            base + "/craft/migrate",
            {"engine": engine, "expectedRevision": document["revision"]},
        )
        page_id = "page-1" if engine == "photocraft" else None

        def native():
            return call(
                "GET",
                base + "/native-project" + ("?pageId=" + page_id if page_id else ""),
                binary=True,
            )

        def preview():
            payload = call(
                "POST",
                base + "/craft/preview",
                {"frame": 0, "pageId": page_id},
                binary=True,
            )
            with Image.open(io.BytesIO(payload)) as image:
                assert image.size == (320, 320)
            return payload

        before_native, before_png = native(), preview()
        original_page = (
            call("GET", base + "/native-project?pageId=page-0", binary=True)
            if engine == "photocraft"
            else None
        )
        if engine == "photocraft":
            commands = [
                {
                    "id": "shape.create",
                    "params": {
                        "kind": "rect",
                        "rect": [0, 0, 160, 160],
                        "fill": "#ff0000",
                    },
                }
            ]
        elif engine == "effectcraft":
            commands = [
                {
                    "id": "layer.newSolid",
                    "params": {"color": "#ff0000", "width": 320, "height": 320},
                }
            ]
        else:
            first = call(
                "POST",
                base + "/craft/commands",
                {
                    "expectedRevision": state["revision"],
                    "commands": [
                        {
                            "id": "file.newColorMatte",
                            "params": {"color": "#ff0000", "seconds": 0.1},
                        }
                    ],
                },
            )
            state = first["inspection"]
            items = state["project"]["raw"]["project"]
            # Query the actual inspection's media bin, not an assumed item ID.
            item = next(
                (
                    entry["item"]
                    for entry in items.get("root", {}).get("children", [])
                    if "item" in entry and entry["item"] != items.get("activeSequence")
                ),
                None,
            )
            if item is None:
                raise AssertionError(
                    "Native FilmCraft inspection did not expose the created media item"
                )
            commands = [
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
            ]
        key = str(uuid4())
        body = {
            "expectedRevision": state["revision"],
            "commands": commands,
            "pageId": page_id,
        }
        receipt = call("POST", base + "/craft/commands", body, key=key)
        assert (
            call("POST", base + "/craft/commands", body, key=key)["receiptId"]
            == receipt["receiptId"]
        )
        call("POST", base + "/craft/commands", body, expected=409)
        state = receipt["inspection"]
        edited_native, edited_png = native(), preview()
        assert edited_native != before_native and edited_png != before_png, (
            "Native edit did not change the rendered pixels"
        )
        if original_page is not None:
            assert (
                call("GET", base + "/native-project?pageId=page-0", binary=True)
                == original_page
            )
        for command in ("host.history.undo", "host.history.redo"):
            state = call(
                "POST",
                base + "/craft/commands",
                {
                    "expectedRevision": state["revision"],
                    "commands": [{"id": command, "params": {}}],
                    "pageId": page_id,
                },
            )["inspection"]
            assert preview() == (before_png if command.endswith("undo") else edited_png)
        reopened = call(
            "GET",
            base + "/craft/inspection" + ("?pageId=" + page_id if page_id else ""),
        )
        assert reopened["revision"] == state["revision"] and native() == edited_native
        extension = {
            "photocraft": "pcraft",
            "filmcraft": "fcproj",
            "effectcraft": "ecproj",
        }[engine]
        (OUTPUT / f"acceptance-{engine}.{extension}").write_bytes(edited_native)
        (OUTPUT / f"acceptance-{engine}.png").write_bytes(edited_png)
        fmt = "png_set" if engine == "photocraft" else "mp4"
        job = call(
            "POST",
            base + "/craft/render-jobs",
            {"expectedRevision": state["revision"], "format": fmt},
            expected=201,
        )
        for _ in range(120):
            job = call("GET", "/api/v1/studios/v1/jobs/" + job["id"])
            if job["status"] in ("succeeded", "failed", "cancelled"):
                break
            time.sleep(0.5)
        assert job["status"] == "succeeded", {
            k: job.get(k) for k in ("status", "errorCode", "errorMessage")
        }
        artifact = job["result"]["artifact"]
        rendered = call("GET", artifact["downloadUrl"], binary=True)
        assert hashlib.sha256(rendered).hexdigest() == artifact["checksumSha256"]
        if fmt == "png_set":
            with zipfile.ZipFile(io.BytesIO(rendered)) as archive:
                assert archive.read("002.png") == edited_png
                assert archive.read("001.png") == before_png
        else:
            assert rendered[4:8] == b"ftyp", (
                "Native encoder did not produce an MP4 container"
            )
        (
            OUTPUT / f"acceptance-{engine}.{'zip' if fmt == 'png_set' else 'mp4'}"
        ).write_bytes(rendered)
        results.append(
            {
                "engine": engine,
                "documentId": document["documentId"],
                "revision": state["revision"],
                "pageId": page_id,
                "nativeSha256": hashlib.sha256(edited_native).hexdigest(),
                "previewSha256": hashlib.sha256(edited_png).hexdigest(),
                "exportSha256": artifact["checksumSha256"],
            }
        )
        (OUTPUT / "acceptance-results.json").write_text(
            json.dumps(results, indent=2), encoding="utf-8"
        )
        print(f"Passed {engine}", flush=True)


if __name__ == "__main__":
    main()
