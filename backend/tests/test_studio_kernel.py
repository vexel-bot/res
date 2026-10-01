from __future__ import annotations

import json
import zipfile
from datetime import UTC, datetime

import pytest
from conftest import register
from pydantic import ValidationError

from app.config import get_settings
from app.database import SessionLocal
from app.domain.studios.contracts import (
    CreativeDocumentV1,
    VideoRenderRequestV1,
    VideoRenderResultV1,
)
from app.domain.studios.providers import PROVIDERS
from app.models import LibraryAsset, Post, StudioDomainEvent, StudioGenerationJob
from app.services.studios.jobs import execute_job_once


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def brief() -> dict:
    return {
        "schemaVersion": "studio.creative-brief.v1",
        "objective": "Transformar contexto em uma peça verificável",
        "audience": "Gestores de social media",
        "angle": "Contexto antes de prompt",
        "hook": "Uma peça começa antes do canvas",
        "cta": "Revisar direção",
    }


def page(page_id: str = "page-1", role: str = "hook") -> dict:
    return {
        "id": page_id,
        "role": role,
        "width": 1080,
        "height": 1350,
        "safeArea": 48,
        "background": "#10181c",
        "layers": [],
    }


def test_video_render_contract_round_trip_is_provider_neutral():
    request_payload = {
        "workspaceId": "workspace-video",
        "documentId": "document-video",
        "documentRevision": 3,
        "documentVersion": 2,
        "pageIds": ["scene-1", "scene-2"],
        "assetIds": ["asset-video", "asset-audio"],
        "output": {
            "width": 1080,
            "height": 1920,
            "fps": 30,
            "format": "mp4",
            "videoCodec": "h264",
            "audioCodec": "aac",
            "quality": "standard",
        },
        "correlationId": "video-render-contract-001",
    }
    request = VideoRenderRequestV1.model_validate(request_payload)
    encoded_request = request.model_dump(by_alias=True, mode="json")
    assert VideoRenderRequestV1.model_validate(encoded_request) == request
    assert "hyperframes" not in json.dumps(encoded_request).lower()
    assert "ffmpeg" not in json.dumps(encoded_request).lower()

    result = VideoRenderResultV1.model_validate(
        {
            "jobId": "job-video-001",
            "workspaceId": request.workspace_id,
            "documentId": request.document_id,
            "documentRevision": request.document_revision,
            "documentVersion": request.document_version,
            "provider": "adapter-under-test",
            "providerVersion": "0.1.0",
            "artifact": {
                "assetId": "asset-rendered-video",
                "storageUri": "object://workspace-video/jobs/job-video-001/output.mp4",
                "mediaType": "video/mp4",
                "checksumSha256": "a" * 64,
                "sizeBytes": 843713,
                "width": 1080,
                "height": 1920,
                "durationMs": 2000,
                "fps": 30,
                "videoCodec": "h264",
                "audioCodec": "aac",
            },
            "renderDurationMs": 14500,
            "framesRendered": 60,
            "peakRssMb": 2048,
            "warnings": [],
            "completedAt": datetime.now(UTC).isoformat(),
        }
    )
    encoded_result = result.model_dump(by_alias=True, mode="json")
    assert VideoRenderResultV1.model_validate(encoded_result) == result
    assert result.artifact.checksum_sha256 == "a" * 64

    with pytest.raises(ValidationError, match="pageIds must be unique"):
        VideoRenderRequestV1.model_validate({**request_payload, "pageIds": ["scene-1", "scene-1"]})


def create_document(client, token: str, workspace: str, *, content_type: str = "visual", post_id: str | None = None):
    pages = [page()]
    if content_type == "carousel":
        pages.append(page("page-2", "payoff"))
    return client.post(
        "/api/v1/studios/v1/documents",
        headers=auth(token),
        json={
            "workspaceId": workspace,
            "title": "Documento canônico",
            "contentType": content_type,
            "postId": post_id,
            "brandRevision": 1,
            "brief": brief(),
            "composition": {"pages": pages, "narrative": {"arc": ["hook", "payoff"]}},
        },
    )


def test_studio_document_contract_versioning_conflict_and_tenant_isolation(client):
    token, workspace = register(client, "studio-kernel@example.com", "Studio Kernel")
    other_token, _ = register(client, "studio-kernel-other@example.com", "Outro Studio")

    created = create_document(client, token, workspace, content_type="carousel")
    assert created.status_code == 201, created.text
    document = created.json()
    assert document["schemaVersion"] == "studio.creative-document.v1"
    assert document["brief"]["schemaVersion"] == "studio.creative-brief.v1"
    assert document["brandMemoryRef"]["id"]
    assert document["brandMemoryRef"]["revision"] == 1
    assert len(document["composition"]["pages"]) == 2
    document_id = document["documentId"]

    listed = client.get(
        "/api/v1/studios/v1/documents",
        headers=auth(token),
        params={"workspace_id": workspace},
    )
    assert listed.status_code == 200
    assert [item["documentId"] for item in listed.json()] == [document_id]
    assert (
        client.get(
            "/api/v1/studios/v1/documents",
            headers=auth(other_token),
            params={"workspace_id": workspace},
        ).status_code
        == 404
    )

    assert client.get(f"/api/v1/studios/v1/documents/{document_id}", headers=auth(other_token)).status_code == 404

    document["title"] = "Documento revisado"
    replaced = client.put(
        f"/api/v1/studios/v1/documents/{document_id}",
        headers=auth(token),
        json={"expectedRevision": 1, "document": document},
    )
    assert replaced.status_code == 200, replaced.text
    assert replaced.json()["revision"] == 2
    assert replaced.json()["title"] == "Documento revisado"

    conflict = client.put(
        f"/api/v1/studios/v1/documents/{document_id}",
        headers=auth(token),
        json={"expectedRevision": 1, "document": document},
    )
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["code"] == "studio_document_conflict"

    versioned = client.post(
        f"/api/v1/studios/v1/documents/{document_id}/versions",
        headers=auth(token),
        json={"label": "Direção aprovada"},
    )
    assert versioned.status_code == 200
    assert versioned.json()["version"] == 2

    with SessionLocal() as db:
        events = db.query(StudioDomainEvent).filter(StudioDomainEvent.workspace_id == workspace).all()
    assert [event.event_type for event in events] == [
        "studio.document.created",
        "studio.document.updated",
        "studio.document.versioned",
    ]


def test_studio_version_history_compare_restore_and_tenant_isolation(client):
    token, workspace = register(client, "studio-history@example.com", "Studio History")
    other_token, _ = register(client, "studio-history-other@example.com", "Other History")
    document = create_document(client, token, workspace).json()
    document_id = document["documentId"]

    document["title"] = "Direção A"
    saved_a = client.put(
        f"/api/v1/studios/v1/documents/{document_id}",
        headers=auth(token),
        json={"expectedRevision": document["revision"], "document": document},
    ).json()
    version_a = client.post(
        f"/api/v1/studios/v1/documents/{document_id}/versions",
        headers=auth(token),
        json={"label": "Direção A aprovada"},
    ).json()
    assert version_a["version"] == 2

    version_a["title"] = "Direção B"
    saved_b = client.put(
        f"/api/v1/studios/v1/documents/{document_id}",
        headers=auth(token),
        json={"expectedRevision": version_a["revision"], "document": version_a},
    ).json()
    assert saved_b["revision"] > saved_a["revision"]
    version_b = client.post(
        f"/api/v1/studios/v1/documents/{document_id}/versions",
        headers=auth(token),
        json={"label": "Direção B aprovada"},
    ).json()

    history = client.get(
        f"/api/v1/studios/v1/documents/{document_id}/versions",
        headers=auth(token),
    )
    assert history.status_code == 200
    assert [item["number"] for item in history.json()] == [3, 2]
    assert history.json()[0]["snapshot"]["title"] == "Direção B"
    assert history.json()[1]["snapshot"]["title"] == "Direção A"
    assert (
        client.get(
            f"/api/v1/studios/v1/documents/{document_id}/versions",
            headers=auth(other_token),
        ).status_code
        == 404
    )

    stale = client.post(
        f"/api/v1/studios/v1/documents/{document_id}/versions/2/restore",
        headers=auth(token),
        json={"expectedRevision": 1},
    )
    assert stale.status_code == 409

    restored = client.post(
        f"/api/v1/studios/v1/documents/{document_id}/versions/2/restore",
        headers=auth(token),
        json={"expectedRevision": version_b["revision"], "label": "Retorno à direção A"},
    )
    assert restored.status_code == 200, restored.text
    assert restored.json()["title"] == "Direção A"
    assert restored.json()["version"] == 5
    assert restored.json()["revision"] == version_b["revision"] + 1

    restored_history = client.get(
        f"/api/v1/studios/v1/documents/{document_id}/versions",
        headers=auth(token),
    ).json()
    assert [item["number"] for item in restored_history[:4]] == [5, 4, 3, 2]
    assert restored_history[0]["label"] == "Retorno à direção A"
    assert restored_history[1]["label"] == "Backup antes de restaurar v2"
    assert restored_history[1]["snapshot"]["title"] == "Direção B"
    with SessionLocal() as db:
        events = db.query(StudioDomainEvent).filter(StudioDomainEvent.workspace_id == workspace).all()
    assert events[-1].event_type == "studio.document.restored"
    assert events[-1].payload["sourceVersion"] == 2


def test_review_pins_immutable_document_version_and_updates_linked_post(client):
    token, workspace = register(client, "studio-review@example.com", "Studio Review")
    post_response = client.post(
        "/api/v1/posts",
        headers=auth(token),
        json={
            "workspaceId": workspace,
            "title": "Post revisável",
            "platform": "Instagram",
            "format": "post",
            "copy": "Direção inicial",
            "status": "draft",
            "author": "Studio Review",
        },
    )
    assert post_response.status_code == 201
    post_id = post_response.json()["id"]
    document = create_document(client, token, workspace, post_id=post_id).json()

    requested = client.post(
        f"/api/v1/studios/v1/documents/{document['documentId']}/reviews",
        headers=auth(token),
        json={"comment": "Revisar esta direção"},
    )
    assert requested.status_code == 201, requested.text
    review = requested.json()
    assert review["documentVersion"] == 1
    assert review["snapshot"]["title"] == "Documento canônico"

    latest_document = client.get(f"/api/v1/studios/v1/documents/{document['documentId']}", headers=auth(token)).json()
    latest_document["title"] = "Documento alterado depois do pedido"
    replaced = client.put(
        f"/api/v1/studios/v1/documents/{document['documentId']}",
        headers=auth(token),
        json={"expectedRevision": latest_document["revision"], "document": latest_document},
    )
    assert replaced.status_code == 200

    pinned = client.get(
        "/api/v1/studios/v1/reviews/latest",
        headers=auth(token),
        params={"workspace_id": workspace, "post_id": post_id},
    )
    assert pinned.status_code == 200
    assert pinned.json()["snapshot"]["title"] == "Documento canônico"

    decided = client.post(
        f"/api/v1/studios/v1/reviews/{review['id']}/decisions",
        headers=auth(token),
        json={"action": "approve", "comment": "Snapshot correto"},
    )
    assert decided.status_code == 409, decided.text
    assert decided.json()["detail"]["code"] == "studio_review_snapshot_stale"
    with SessionLocal() as db:
        assert db.get(Post, post_id).status == "draft"
    fresh = client.post(
        f"/api/v1/studios/v1/documents/{document['documentId']}/reviews",
        headers=auth(token),
        json={},
    ).json()
    assert fresh["id"] != review["id"]
    assert fresh["snapshot"]["title"] == "Documento alterado depois do pedido"
    decided = client.post(
        f"/api/v1/studios/v1/reviews/{fresh['id']}/decisions",
        headers=auth(token),
        json={"action": "approve", "comment": "Nova direção revisada"},
    )
    assert decided.status_code == 200, decided.text
    assert decided.json()["status"] == "approved"
    with SessionLocal() as db:
        assert db.get(Post, post_id).status == "approved"


def test_carousel_export_creates_ordered_png_zip(client, tmp_path, monkeypatch):
    monkeypatch.setattr(get_settings(), "storage_path", str(tmp_path))
    token, workspace = register(client, "studio-export@example.com", "Studio Export")
    document = create_document(client, token, workspace, content_type="carousel").json()
    response = client.post(
        f"/api/v1/studios/v1/documents/{document['documentId']}/exports",
        headers=auth(token),
        json={"format": "png_set"},
    )
    assert response.status_code == 201, response.text
    assert response.json()["type"] == "archive"
    with SessionLocal() as db:
        asset = db.get(LibraryAsset, response.json()["id"])
        archive_path = tmp_path / asset.storage_key
    with zipfile.ZipFile(archive_path) as archive:
        assert archive.namelist() == ["manifest.json", "01.png", "02.png"]
        manifest = json.loads(archive.read("manifest.json"))
    assert manifest["orderedPages"] == ["page-1", "page-2"]


def test_studio_replace_is_allowed_by_cors(client):
    response = client.options(
        "/api/v1/studios/v1/documents/document-id",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "PUT",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    assert response.status_code == 200
    assert "PUT" in response.headers["access-control-allow-methods"]


def test_studio_document_creation_is_idempotent_for_post_and_content_type(client):
    token, workspace = register(client, "studio-idempotent@example.com", "Studio Idempotent")
    post = client.post(
        "/api/v1/posts",
        headers=auth(token),
        json={
            "workspaceId": workspace,
            "title": "Post único",
            "platform": "Instagram",
            "format": "post",
            "status": "draft",
            "author": "Studio",
        },
    ).json()
    first = create_document(client, token, workspace, post_id=post["id"])
    second = create_document(client, token, workspace, post_id=post["id"])
    assert first.status_code == 201 and second.status_code == 201
    assert first.json()["documentId"] == second.json()["documentId"]
    listed = client.get(
        "/api/v1/studios/v1/documents",
        headers=auth(token),
        params={"workspace_id": workspace, "post_id": post["id"]},
    )
    assert len(listed.json()) == 1


def test_studio_document_rejects_cross_workspace_references(client):
    token, workspace = register(client, "studio-assets@example.com", "Studio Assets")
    other_token, other_workspace = register(client, "studio-assets-other@example.com", "Other Assets")
    asset = client.post(
        "/api/v1/assets",
        headers=auth(other_token),
        json={"workspaceId": other_workspace, "title": "Privado", "type": "image", "tags": []},
    )
    assert asset.status_code == 201
    response = client.post(
        "/api/v1/studios/v1/documents",
        headers=auth(token),
        json={
            "workspaceId": workspace,
            "title": "Inválido",
            "brief": brief(),
            "composition": {"pages": [page()]},
            "assets": [{"id": asset.json()["id"], "rightsStatus": "unknown"}],
        },
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "Asset does not belong to workspace"


def test_generation_job_idempotency_cancel_progress_execution_and_provider_swap(client, monkeypatch):
    token, workspace = register(client, "studio-jobs@example.com", "Studio Jobs")
    other_token, _ = register(client, "studio-jobs-other@example.com", "Other Jobs")
    document = create_document(client, token, workspace).json()
    queued_ids = []

    from app import tasks

    monkeypatch.setattr(tasks.execute_studio_generation, "delay", lambda job_id: queued_ids.append(job_id))
    payload = {
        "workspaceId": workspace,
        "documentId": document["documentId"],
        "jobType": "document_snapshot",
        "provider": "builtin.snapshot",
        "request": {"purpose": "contract-test"},
    }
    headers = {**auth(token), "Idempotency-Key": "studio-snapshot-001"}
    created = client.post("/api/v1/studios/v1/jobs", headers=headers, json=payload)
    assert created.status_code == 202, created.text
    job = created.json()
    assert job["status"] == "queued" and job["progress"] == 0
    assert queued_ids == [job["id"]]

    duplicate = client.post("/api/v1/studios/v1/jobs", headers=headers, json=payload)
    assert duplicate.status_code == 202 and duplicate.json()["id"] == job["id"]
    assert queued_ids == [job["id"]]
    changed = {**payload, "request": {"purpose": "different"}}
    conflict = client.post("/api/v1/studios/v1/jobs", headers=headers, json=changed)
    assert conflict.status_code == 409
    assert client.get(f"/api/v1/studios/v1/jobs/{job['id']}", headers=auth(other_token)).status_code == 404

    with SessionLocal() as db:
        record = db.get(StudioGenerationJob, job["id"])
        assert execute_job_once(db, record) == "succeeded"
        db.refresh(record)
        assert record.progress == 100
        assert record.result_payload["pageCount"] == 1

    completed = client.get(f"/api/v1/studios/v1/jobs/{job['id']}", headers=auth(token))
    assert completed.json()["status"] == "succeeded"

    from app.tasks import execute_studio_generation

    assert execute_studio_generation.run("missing-studio-job") == {"status": "not-found"}
    task_headers = {**auth(token), "Idempotency-Key": "studio-snapshot-task-001"}
    task_job = client.post("/api/v1/studios/v1/jobs", headers=task_headers, json=payload).json()
    assert execute_studio_generation.run(task_job["id"]) == {
        "status": "succeeded",
        "jobId": task_job["id"],
    }

    second_headers = {**auth(token), "Idempotency-Key": "studio-snapshot-002"}
    second = client.post("/api/v1/studios/v1/jobs", headers=second_headers, json=payload).json()
    cancelled = client.post(
        f"/api/v1/studios/v1/jobs/{second['id']}/cancel",
        headers=auth(token),
        json={"reason": "Usuário mudou a direção"},
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"

    class AlternateProvider:
        name = "builtin.snapshot"

        def execute(self, document: CreativeDocumentV1, request, progress, is_cancelled):
            progress(55)
            return {"adapter": "alternate", "documentId": document.document_id}

    monkeypatch.setitem(PROVIDERS, "builtin.snapshot", AlternateProvider())
    third_headers = {**auth(token), "Idempotency-Key": "studio-snapshot-003"}
    third = client.post("/api/v1/studios/v1/jobs", headers=third_headers, json=payload).json()
    with SessionLocal() as db:
        record = db.get(StudioGenerationJob, third["id"])
        assert execute_job_once(db, record) == "succeeded"
        assert record.result_payload["adapter"] == "alternate"
