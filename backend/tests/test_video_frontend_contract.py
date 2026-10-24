"""Compatibility checks for the video-only frontend; no native or paid provider is invoked."""
from copy import deepcopy
from base64 import b64decode

from fastapi.testclient import TestClient

from app.studio_app import app
from app.config import get_settings
from test_clicko_studio_bridge import KEY, headers


def draft(workspace):
    return {
        "workspaceId": workspace, "title": "Coleção em vídeo", "contentType": "video", "brandRevision": 1,
        "brief": {"objective": "Apresentar a coleção", "audience": "Clientes", "angle": "Abertura e convite", "format": "video"},
        "composition": {
            "pages": [{"id": "page-1", "width": 1080, "height": 1920, "safeArea": 48, "background": "#000000", "durationMs": 15000, "layers": []}],
            "narrative": {"videoStudio": {"engine": "filmcraft", "kind": "social", "locale": "pt-BR"}},
            "tracks": [], "mediaTimeline": {"schemaVersion": "studio.media-timeline.v1", "frameRate": {"numerator": 30, "denominator": 1}, "durationFrames": 450, "tracks": []},
        }, "assets": [], "correlationId": "video-frontend-contract",
    }


def test_video_draft_persists_and_metadata_updates_preserve_engine_owned_composition(monkeypatch):
    monkeypatch.setenv("CLICKO_STUDIOS_BRIDGE_SECRET", KEY)
    auth = headers(module="create-video", client="video-contract")
    with TestClient(app) as client:
        workspace = client.get("/api/v1/studios/v1/bridge/session", headers=auth).json()["workspace"]["id"]
        created = client.post("/api/v1/studios/v1/documents", headers=auth, json=draft(workspace))
        assert created.status_code == 201, created.text
        doc = created.json()
        assert doc["nativeEditorState"] is None
        base = "/api/v1/studios/v1/documents/" + doc["documentId"]
        reread = client.get(base, headers=auth).json()
        assert reread["composition"]["narrative"]["videoStudio"]["locale"] == "pt-BR"
        updated = deepcopy(reread)
        updated["title"] = "Novo título"
        updated["brief"]["angle"] = "Novo roteiro sem reescrever a montagem"
        result = client.put(base, headers=auth, json={"expectedRevision": 1, "document": updated})
        assert result.status_code == 200, result.text
        saved = client.get(base, headers=auth).json()
        assert saved["revision"] == 2
        assert saved["brief"]["angle"] == updated["brief"]["angle"]
        assert saved["composition"] == reread["composition"]
        assert client.put(base, headers=auth, json={"expectedRevision": 1, "document": updated}).status_code == 409
        forbidden = deepcopy(saved)
        forbidden["composition"]["pages"][0]["height"] = 1080
        assert client.put(base, headers=auth, json={"expectedRevision": 2, "document": forbidden}).status_code == 422
        assert client.get(base, headers=headers(module="create-video", client="another-client")).status_code == 404


def test_video_drafts_do_not_bypass_image_only_permissions(monkeypatch):
    monkeypatch.setenv("CLICKO_STUDIOS_BRIDGE_SECRET", KEY)
    with TestClient(app) as client:
        auth = headers(module="create-image")
        workspace = client.get("/api/v1/studios/v1/bridge/session", headers=auth).json()["workspace"]["id"]
        assert client.post("/api/v1/studios/v1/documents", headers=auth, json=draft(workspace)).status_code == 403


def test_video_material_upload_reuses_workspace_library_and_document_asset_references(monkeypatch, tmp_path):
    monkeypatch.setenv("CLICKO_STUDIOS_BRIDGE_SECRET", KEY)
    monkeypatch.setattr(get_settings(), "storage_path", str(tmp_path / "objects"))
    auth = headers(module="create-video", client="video-material-contract")
    # Real minimal PNG fixture; no native rendering, provider call or user file.
    content = b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+ip1sAAAAASUVORK5CYII=")
    with TestClient(app) as client:
        workspace = client.get("/api/v1/studios/v1/bridge/session", headers=auth).json()["workspace"]["id"]
        upload = client.post("/api/v1/studios/v1/craft/assets", params={"workspace_id": workspace, "title": "material.png", "filename": "material.png", "media_type": "image/png"}, headers={**auth, "Content-Type": "image/png"}, content=content)
        assert upload.status_code == 201, upload.text
        asset = upload.json()
        payload = draft(workspace)
        payload["assets"] = [{"id": asset["id"], "mediaType": "image/png", "checksum": asset["checksumSha256"], "origin": "workspace", "rightsStatus": "unknown", "provenance": {}}]
        payload["composition"]["mediaTimeline"]["tracks"] = [{"id": "track-1", "kind": "video", "name": "material.png", "muted": False, "locked": False, "clips": [{"id": "clip-1", "assetId": asset["id"], "timeline": {"startFrame": 0, "durationFrames": 450}, "enabled": True, "locked": False, "label": "material.png", "playbackRate": 1}]}]
        created = client.post("/api/v1/studios/v1/documents", headers=auth, json=payload)
        assert created.status_code == 201, created.text
        reread = client.get("/api/v1/studios/v1/documents/" + created.json()["documentId"], headers=auth).json()
        assert reread["assets"][0]["id"] == asset["id"]
        assert reread["composition"]["mediaTimeline"]["tracks"][0]["clips"][0]["assetId"] == asset["id"]
        library = client.get("/api/v1/studios/v1/bridge/session", headers=auth).json()["assets"]
        assert [item["id"] for item in library] == [asset["id"]]
        assert client.get("/api/v1/assets/" + asset["id"] + "/content", headers=auth).content == content
