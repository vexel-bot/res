from types import SimpleNamespace

from conftest import register
from sqlalchemy import select

from app.database import SessionLocal
from app.models import CreativeDocument, Post
from app.routers import studio_department as department

BASE = "/api/v1/studios/v1/projects"


def setup_project(client, **changes):
    token, workspace = register(client, "direction@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    body = {
        "workspaceId": workspace,
        "requestKey": "request-example-1",
        "title": "Como escolher o café",
        "objective": "Explicar como comparar a origem do café.",
        "audience": "Pessoas que preparam café em casa",
        "evidence": "Origem informada pelo produtor.",
        "format": "carousel",
        **changes,
    }
    result = client.post(BASE, headers=headers, json=body)
    assert result.status_code == 201, result.text
    return headers, body, result.json()


def choose(client, headers, project):
    result = client.patch(
        f"{BASE}/{project['id']}",
        headers=headers,
        json={"expectedRevision": project["revision"], "directionId": "guide"},
    )
    assert result.status_code == 200, result.text
    return result.json()


def test_persistent_request_is_idempotent_and_workspace_scoped(client):
    headers, body, project = setup_project(client)
    repeated = client.post(BASE, headers=headers, json=body)
    assert repeated.json()["id"] == project["id"]
    conflict = client.post(BASE, headers=headers, json={**body, "objective": "Um pedido diferente para a marca."})
    assert conflict.status_code == 409
    rows = client.get(BASE, headers=headers, params={"workspace_id": body["workspaceId"]}).json()
    assert [row["id"] for row in rows] == [project["id"]]
    other_token, other_workspace = register(client, "other@example.com")
    other = {"Authorization": f"Bearer {other_token}"}
    assert client.get(f"{BASE}/{project['id']}", headers=other).status_code == 404
    assert (
        client.patch(
            f"{BASE}/{project['id']}", headers=other, json={"expectedRevision": 1, "directionId": "guide"}
        ).status_code
        == 404
    )
    assert (
        client.post(f"{BASE}/{project['id']}/produce", headers=other, json={"expectedRevision": 1}).status_code == 404
    )
    assert client.get(BASE, headers=other, params={"workspace_id": other_workspace}).json() == []


def test_direction_revision_conflict_preserves_the_first_choice(client):
    headers, _, project = setup_project(client)
    saved = choose(client, headers, project)
    assert saved["revision"] == 2
    conflict = client.patch(
        f"{BASE}/{project['id']}", headers=headers, json={"expectedRevision": 1, "directionId": "demonstrate"}
    )
    assert conflict.status_code == 409
    assert client.get(f"{BASE}/{project['id']}", headers=headers).json()["directionId"] == "guide"
    assert all(d["basis"] == "brief-derived-outline" for d in saved["directions"])


def test_runtime_failure_preserves_recoverable_document_without_fake_output(client, monkeypatch):
    headers, _, project = setup_project(client)
    project = choose(client, headers, project)
    calls = []

    def unavailable(*args):
        calls.append(args[1].id)
        raise ValueError("craft_engine_unavailable")

    monkeypatch.setattr(department.craft, "migrate", unavailable)
    for _ in range(2):
        response = client.post(
            f"{BASE}/{project['id']}/produce", headers=headers, json={"expectedRevision": project["revision"]}
        )
        assert response.status_code == 422, response.text
        project = client.get(f"{BASE}/{project['id']}", headers=headers).json()
        assert project["status"] == "production_failed"
        assert project["documentId"]
        assert project["jobId"] is None
    assert calls[0] == calls[1]
    with SessionLocal() as db:
        assert len(db.scalars(select(CreativeDocument)).all()) == 1
        assert len(db.scalars(select(Post)).all()) == 1


def test_video_requires_real_material_and_rejects_production_before_choice(client):
    headers, _, project = setup_project(client, format="video")
    response = client.post(f"{BASE}/{project['id']}/produce", headers=headers, json={"expectedRevision": 1})
    assert response.status_code == 422
    project = choose(client, headers, project)
    response = client.post(
        f"{BASE}/{project['id']}/produce", headers=headers, json={"expectedRevision": project["revision"]}
    )
    assert response.status_code == 422
    assert "vídeo da biblioteca" in response.json()["detail"]
    with SessionLocal() as db:
        assert not db.scalars(select(CreativeDocument)).all()


def test_delivery_replay_does_not_enqueue_duplicate_production(client, monkeypatch):
    headers, _, project = setup_project(client)
    project = choose(client, headers, project)
    monkeypatch.setattr(department, "record_to_contract", lambda doc: SimpleNamespace(native_editor_state=True))
    jobs = []

    def render(*args):
        jobs.append(args)
        return SimpleNamespace(id="render-job")

    monkeypatch.setattr(department, "render_job", render)
    response = client.post(
        f"{BASE}/{project['id']}/produce", headers=headers, json={"expectedRevision": project["revision"]}
    )
    assert response.status_code == 200, response.text
    project = response.json()
    assert project["status"] == "delivery"
    assert project["jobId"] == "render-job"
    repeated = client.post(
        f"{BASE}/{project['id']}/produce", headers=headers, json={"expectedRevision": project["revision"]}
    )
    assert repeated.status_code == 200
    assert len(jobs) == 1
