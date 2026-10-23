"""Live loopback acceptance against the isolated dev:local Studios service.

Service-to-service bridge credentials, NOT a browser login or license bypass.
Own QA media only. Run `create`, restart dev:local, then `verify`.
"""

import hashlib
import json
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import httpx
import jwt

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / ".codex-runtime/stage1-local"
OUTPUT = ROOT / ".codex-runtime/stage1-validation"
ORIGIN = "http://127.0.0.1:8018"


def digest(value):
    return hashlib.sha256(value).hexdigest()


def headers(module="create-video", client="live-stage1"):
    now = datetime.now(UTC)
    token = jwt.encode({"iss": "clicko-governance", "aud": "clicko-studios", "type": "studio_bridge",
        "sub": "stage1-qa-only", "workspaceId": "stage1-isolated-qa", "clientId": client, "module": module,
        "name": "QA audiovisual", "workspaceName": "QA Stage 1", "allowedModules": ["create-video", "create-image"],
        "role": "Owner", "iat": now, "exp": now + timedelta(seconds=60)},
        (DATA / "bridge-key").read_text().strip(), algorithm="HS256")
    return {"Authorization": "Bearer " + token}


def main():
    with httpx.Client(base_url=ORIGIN, timeout=120) as client:
        def request(method, path, *, module="create-video", **kwargs):
            supplied = kwargs.pop("headers", {})
            response = client.request(method, path, headers={**headers(module), **supplied}, **kwargs)
            assert response.is_success, (response.status_code, response.text[:400])
            return response

        session = request("GET", "/api/v1/studios/v1/bridge/session").json()
        workspace = session["workspace"]["id"]
        evidence_path = OUTPUT / "live-evidence.json"
        if sys.argv[1:] == ["verify"]:
            evidence = json.loads(evidence_path.read_text())
            for name, path in evidence["deliveries"].items():
                actual = request("GET", path).content
                assert digest(actual) == evidence["checksums"][name]
            doc = request("GET", "/api/v1/studios/v1/documents/" + evidence["documentId"]).json()
            assert doc["revision"] == 2
            evidence["persistenceAfterRestart"] = True
            evidence_path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
            print(json.dumps({"persisted": True, "assets": len(evidence["deliveries"]), "revision": 2}))
            return

        run = uuid4().hex[:12]
        source = OUTPUT / "publicidade-local-18s.mp4"
        image = OUTPUT / "reference-4x5.png"
        assets = []
        for path, mime in ((source, "video/mp4"), (image, "image/png")):
            assets.append(request("POST", "/api/v1/studios/v1/craft/assets", params={"workspace_id": workspace,
                "title": "QA Stage1 " + path.name, "filename": path.name, "media_type": mime},
                headers={"Content-Type": mime}, content=path.read_bytes()).json())
        video, picture = assets
        document = {"workspaceId": workspace, "title": "QA Stage 1 · edição local 16s",
            "contentType": "video", "brandRevision": 1,
            "brief": {"objective": "Validar edição local", "audience": "QA", "angle": "Materiais próprios"},
            "composition": {"pages": [{"id": "page", "width": 1280, "height": 720,
                "durationMs": 16000, "layers": [], "background": "#000000"}], "tracks": [],
                "mediaTimeline": {"schemaVersion": "studio.media-timeline.v1", "frameRate": {"numerator": 30, "denominator": 1},
                    "durationFrames": 480, "tracks": []}}, "assets": [], "correlationId": "qa-stage1-" + run}
        document = request("POST", "/api/v1/studios/v1/documents", json=document).json()
        timeline = document["composition"]["mediaTimeline"]
        timeline["tracks"] = [{"id": "video", "kind": "video", "name": "Dois cortes locais", "clips": [
            {"id": "first", "assetId": video["id"], "timeline": {"startFrame": 0, "durationFrames": 240},
             "source": {"startMicroseconds": 0, "durationMicroseconds": 8_000_000}},
            {"id": "second", "assetId": video["id"], "timeline": {"startFrame": 240, "durationFrames": 240},
             "source": {"startMicroseconds": 10_000_000, "durationMicroseconds": 8_000_000},
             "transform": {"fadeInFrames": 10, "fadeOutFrames": 15}},
        ]}, {"id": "titles", "kind": "caption", "name": "Texto manual", "cues": [{"id": "qa-title",
            "text": "Validação local · nenhuma geração de IA", "timeline": {"startFrame": 0, "durationFrames": 480},
            "style": {"fontFamily": "system", "fontSize": 26},
            "motion": {"fadeInFrames": 12}, "keyframes": [{"property": "y", "frame": 0, "value": -490},
                {"property": "y", "frame": 30, "value": -500}]}]}]
        path = "/api/v1/studios/v1/video/documents/" + document["documentId"]
        request("PUT", path + "/timeline", headers={"Idempotency-Key": "stage1-save-" + run},
                json={"expectedRevision": 1, "timeline": timeline})
        key = {"Idempotency-Key": "stage1-render-" + run}
        job = request("POST", path + "/render-jobs", headers=key, json={"expectedRevision": 2}).json()
        replay = request("POST", path + "/render-jobs", headers=key, json={"expectedRevision": 2}).json()
        assert replay["id"] == job["id"]
        deadline = time.monotonic() + 120
        while job["status"] not in {"succeeded", "failed", "cancelled"} and time.monotonic() < deadline:
            time.sleep(0.5)
            job = request("GET", "/api/v1/studios/v1/jobs/" + job["id"]).json()
        assert job["status"] == "succeeded", job.get("error")
        result = job["result"]
        deliveries = {"video": "/api/v1/studios/v1/video/library/" + result["assetId"] + "/content?download=1",
                      "image": "/api/v1/assets/" + picture["id"] + "/content"}
        checksums = {}
        for name, delivery in deliveries.items():
            response = request("GET", delivery)
            checksums[name] = digest(response.content)
            (OUTPUT / ("live-export-16s.mp4" if name == "video" else "live-image-export.png")).write_bytes(response.content)
        assert checksums["image"] == digest(image.read_bytes())
        assert client.get(deliveries["video"]).status_code == 401
        other = client.get(deliveries["video"], headers=headers(client="other-qa-partition"))
        assert other.status_code in {403, 404}
        probe = request("GET", "/api/v1/studios/v1/video/assets/" + result["assetId"] + "/probe",
                        params={"workspace_id": workspace}).json()
        assert abs(probe["durationSeconds"] - 16) <= 0.1
        assert any(s.get("codec_name") == "h264" and s.get("width") == 1280 for s in probe["streams"])
        assert any(s.get("codec_name") == "aac" for s in probe["streams"])
        evidence = {"schemaVersion": "clicko.stage1-live.v1", "documentId": document["documentId"],
            "jobId": job["id"], "deliveries": deliveries, "checksums": checksums, "probe": probe,
            "duplicateRenderJobPrevented": True, "unauthenticatedAndCrossScopeDenied": True,
            "persistenceAfterRestart": False, "paidCalls": 0, "generationType": "deterministic-local-editing"}
        evidence_path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
        print(json.dumps({"render": "succeeded", "duration": 16, "assets": 2, "paidCalls": 0}))


if __name__ == "__main__":
    main()
