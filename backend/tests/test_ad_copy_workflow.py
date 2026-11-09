"""Product/copy preparation is versioned, scoped and free of provider calls."""

from fastapi.testclient import TestClient
from sqlalchemy import select
from test_clicko_studio_bridge import headers
from test_video_timeline_real import create, setup

from app.database import SessionLocal
from app.models import CreativeDocument, StudioDomainEvent
from app.providers.studios.universal_llm import UniversalLLMPlanner
from app.services.studios import ad_copy_workflow as flow
from app.studio_app import app


def body(revision=0, status="draft", **changes):
    return {
        "expectedRevision": revision,
        "requestKey": "copy-request-" + str(revision),
        "status": status,
        "data": {},
        "checks": {},
        **changes,
    }


def no_provider(*args, **kwargs):
    raise AssertionError("A copy preparation route must never call a model")


def test_partial_save_replay_and_scope_without_model(monkeypatch, tmp_path):
    auth = setup(monkeypatch, tmp_path)
    monkeypatch.setattr(UniversalLLMPlanner, "plan", no_provider)
    with TestClient(app) as client:
        _, doc = create(client, auth)
        url = "/api/v1/studios/v1/copy/document/" + doc["documentId"]
        assert client.get(url, headers=auth).json()["revision"] == 0
        data = body(data={"product": "Descrição declarada pelo cliente"})
        saved = client.put(url, headers=auth, json=data)
        assert saved.status_code == 200, saved.text
        assert saved.json()["revision"] == 1
        assert saved.json()["automation"]["apiCalls"] == 0
        assert saved.json()["stages"][0]["missing"]
        assert client.put(url, headers=auth, json=data).json()["revision"] == 1
        assert client.put(url, headers=auth, json=body(requestKey="other-key-001")).status_code == 409
        foreign = headers(module="create-video", client="foreign")
        assert client.get(url, headers=foreign).status_code == 404
        assert client.put(url, headers=foreign, json=body()).status_code == 404


def test_approval_requires_saved_text_complete_fields_and_review(monkeypatch, tmp_path):
    auth = setup(monkeypatch, tmp_path)
    monkeypatch.setattr(UniversalLLMPlanner, "plan", no_provider)
    with TestClient(app) as client:
        _, doc = create(client, auth)
        url = "/api/v1/studios/v1/copy/document/" + doc["documentId"]
        data = {key: "Conteúdo manual com fonte e limites explícitos" for key in flow.FIELDS}
        checks = {key: True for key in flow.CHECKS}
        direct = client.put(url, headers=auth, json=body(status="approved", data=data, checks=checks))
        assert direct.status_code == 422
        draft = client.put(url, headers=auth, json=body(data=data, checks=checks)).json()
        assert draft["checks"] == {}  # A new text version has not been reviewed.
        no_review = client.put(url, headers=auth, json=body(1, "approved", data=data))
        assert no_review.status_code == 422
        approved = client.put(url, headers=auth, json=body(1, "approved", data=data, checks=checks))
        assert approved.status_code == 200, approved.text
        assert approved.json()["status"] == "approved"
        assert approved.json()["handoff"]["status"] == "ready"
        with SessionLocal() as db:
            context = flow.planning_context(db, db.get(CreativeDocument, doc["documentId"]))
            assert context["status"] == "approved"
            assert context["data"]["product"] == data["product"]
        data = {**data, "offer": "Oferta mudou"}
        edit = client.put(url, headers=auth, json=body(2, data=data, checks=checks))
        assert edit.status_code == 200, edit.text
        assert edit.json()["status"] == "draft"
        assert not edit.json()["checks"]
        with SessionLocal() as db:
            events = db.scalars(
                select(StudioDomainEvent).where(StudioDomainEvent.event_type == "studio.copy.workflow.saved")
            ).all()
            assert [e.payload["revision"] for e in events] == [1, 2, 3]
            assert events[1].payload["data"]["offer"] != "Oferta mudou"


def test_invalid_fields_cannot_be_persisted(monkeypatch, tmp_path):
    auth = setup(monkeypatch, tmp_path)
    with TestClient(app) as client:
        _, doc = create(client, auth)
        url = "/api/v1/studios/v1/copy/document/" + doc["documentId"]
        assert client.put(url, headers=auth, json=body(data={"execute": "untrusted"})).status_code == 422
        assert client.put(url, headers=auth, json=body(data={"product": "x" * 6001})).status_code == 422
        assert client.put(url, headers=auth, json=body(checks={"invented": True})).status_code == 422


def test_project_preparation_is_available_before_render(monkeypatch, tmp_path):
    auth = setup(monkeypatch, tmp_path)
    monkeypatch.setattr(UniversalLLMPlanner, "plan", no_provider)
    with TestClient(app) as client:
        ws = client.get("/api/v1/studios/v1/bridge/session", headers=auth).json()["workspace"]["id"]
        project = client.post(
            "/api/v1/studios/v1/projects",
            headers=auth,
            json={
                "workspaceId": ws,
                "requestKey": "copy-project-001",
                "title": "Anúncio de teste",
                "objective": "Explicar o produto de forma clara",
                "audience": "Público informado pelo cliente",
                "front": "ads",
                "format": "video",
            },
        )
        assert project.status_code == 201, project.text
        url = "/api/v1/studios/v1/copy/project/" + project.json()["id"]
        saved = client.put(url, headers=auth, json=body(data={"product": "Produto descrito"}))
        assert saved.status_code == 200, saved.text
        assert saved.json()["targetKind"] == "project"
        assert saved.json()["revision"] == 1


def test_shared_document_requires_explicit_copy_context(monkeypatch, tmp_path):
    from uuid import uuid4

    from app.models import WorkspaceResource

    auth = setup(monkeypatch, tmp_path)
    with TestClient(app) as client:
        ws, doc = create(client, auth)
        with SessionLocal() as db:
            for key in ("one", "two"):
                db.add(
                    WorkspaceResource(
                        id=str(uuid4()),
                        workspace_id=ws,
                        kind="studio_department",
                        resource_key=key,
                        payload={"documentId": doc["documentId"]},
                    )
                )
            db.commit()
            record = db.get(CreativeDocument, doc["documentId"])
            assert flow.planning_context(db, record)["status"] == "ambiguous"
            db.add(
                WorkspaceResource(
                    id=str(uuid4()),
                    workspace_id=ws,
                    kind=flow.KIND,
                    resource_key="document:" + doc["documentId"],
                    payload={"revision": 1, "status": "draft", "data": {"product": "Explicit document context"}},
                )
            )
            db.commit()
            assert flow.planning_context(db, record)["data"]["product"] == "Explicit document context"
