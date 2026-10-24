from datetime import UTC, datetime, timedelta

import jwt
from fastapi.testclient import TestClient

from app.studio_app import app

KEY = "studio-bridge-test-key-with-at-least-32-characters"


def headers(workspace="ws-1", client=None, module="create-image", allowed=None, **changes):
    now = datetime.now(UTC)
    payload = {
        "iss": "clicko-governance", "aud": "clicko-studios", "type": "studio_bridge", "sub": "member-1",
        "workspaceId": workspace, "clientId": client, "module": module, "name": "Pedro", "workspaceName": "Clicko",
        "role": "Owner", "allowedModules": allowed or [module], "iat": now, "exp": now + timedelta(seconds=60),
        **changes,
    }
    return {"Authorization": "Bearer " + jwt.encode(payload, KEY, algorithm="HS256")}


def test_bridge_requires_a_signed_current_session(monkeypatch):
    monkeypatch.setenv("CLICKO_STUDIOS_BRIDGE_SECRET", KEY)
    with TestClient(app) as client:
        url = "/api/v1/studios/v1/bridge/session"
        assert client.get(url).status_code == 401
        assert client.get(url, headers=headers(aud="other")).status_code == 401
        assert client.get(url, headers=headers(exp=datetime.now(UTC) - timedelta(seconds=1))).status_code == 401
        assert client.get(url, headers={"Authorization": "Bearer browser-token"}).status_code == 401
        assert client.get(url, headers=headers()).status_code == 200


def test_workspace_client_isolation_and_idempotent_projects(monkeypatch):
    monkeypatch.setenv("CLICKO_STUDIOS_BRIDGE_SECRET", KEY)
    with TestClient(app) as client:
        auth = headers(client="brand-a")
        session = client.get("/api/v1/studios/v1/bridge/session", headers=auth).json()
        base = "/api/v1/studios/v1/projects"
        payload = {
            "workspaceId": session["workspace"]["id"], "requestKey": "bridge-project-001", "title": "Semana da marca",
            "objective": "Explicar como o produto funciona", "audience": "Clientes interessados", "format": "image",
        }
        response = client.post(base, json=payload, headers=auth)
        assert response.status_code == 201, response.text
        project = response.json()
        assert client.post(base, json=payload, headers=auth).json()["id"] == project["id"]
        assert client.get(base + "/" + project["id"], headers=headers(client="brand-b")).status_code == 404
        assert client.get(base + "/" + project["id"], headers=headers(workspace="ws-2", client="brand-a")).status_code == 404
        wrong_workspace = {**payload, "workspaceId": "ws-from-browser", "requestKey": "bridge-project-002"}
        assert client.post(base, json=wrong_workspace, headers=auth).status_code == 404
        selected = client.patch(base + "/" + project["id"], json={"expectedRevision": 1, "directionId": "guide"}, headers=auth)
        assert selected.status_code == 200
        assert selected.json()["revision"] == 2
        assert client.patch(base + "/" + project["id"], json={"expectedRevision": 1, "directionId": "guide"}, headers=auth).status_code == 409


def test_image_permission_cannot_create_a_video_project(monkeypatch):
    monkeypatch.setenv("CLICKO_STUDIOS_BRIDGE_SECRET", KEY)
    with TestClient(app) as client:
        auth = headers()
        session = client.get("/api/v1/studios/v1/bridge/session", headers=auth).json()
        payload = {
            "workspaceId": session["workspace"]["id"], "requestKey": "video-project-001", "title": "Vídeo da marca",
            "objective": "Mostrar como funciona", "audience": "Clientes", "format": "video",
        }
        assert client.post("/api/v1/studios/v1/projects", json=payload, headers=auth).status_code == 403
        allowed = headers(module="create-video", allowed=["create-video"])
        assert client.post("/api/v1/studios/v1/projects", json=payload, headers=allowed).status_code == 201
