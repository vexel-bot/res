"""Image Studio HTTP contract: real private storage/queue lifecycle, isolated AI boundary."""
import base64
import io
import json
import jwt

from fastapi.testclient import TestClient
from PIL import Image
from pydantic import SecretStr

from app import tasks
from app.config import get_settings
from app.database import SessionLocal
from app.models import LibraryAsset, StudioGenerationJob
from app.providers.studios.gemini_editing import GeminiEditingProvider
from app.services.studios.jobs import execute_job_once
from app.studio_app import app
from test_clicko_studio_bridge import KEY, headers


def png(color):
    stream = io.BytesIO()
    Image.new("RGB", (64, 48), color).save(stream, "PNG")
    return stream.getvalue()


def admitted(auth, document_id, key, operation="generate_image"):
    claims = jwt.decode(auth["Authorization"].split(" ")[1], KEY, algorithms=["HS256"], audience="clicko-studios")
    claims["mediaAdmission"] = {"id": "a" * 64, "documentId": document_id, "key": key, "operation": operation}
    return {"Authorization": "Bearer " + jwt.encode(claims, KEY, algorithm="HS256"), "Idempotency-Key": key}


def setup(monkeypatch, tmp_path):
    monkeypatch.setenv("CLICKO_STUDIOS_BRIDGE_SECRET", KEY)
    settings = get_settings()
    monkeypatch.setattr(settings, "storage_path", str(tmp_path / "objects"))
    monkeypatch.setattr(settings, "studio_gemini_enabled", True)
    monkeypatch.setattr(settings, "gemini_outbound_enabled", True)
    monkeypatch.setattr(settings, "studio_editing_ai_image_provider", "gemini")
    monkeypatch.setattr(settings, "studio_gemini_test_key", SecretStr("test-only-no-network"))
    monkeypatch.setattr(settings, "studio_gemini_test_budget_usd", 5)
    monkeypatch.setattr(settings, "studio_production_test_budget_usd", 5)
    for key in ("studio_external_monthly_budget_usd", "studio_external_workspace_monthly_budget_usd",
                "studio_external_user_monthly_budget_usd"):
        monkeypatch.setattr(settings, key, 10)
    monkeypatch.setattr(settings, "studio_external_model_monthly_budgets", {"gemini-3.1-flash-lite-image": 10})
    monkeypatch.setattr(tasks.execute_studio_generation, "delay", lambda _: None)
    monkeypatch.setattr(GeminiEditingProvider, "validate_model", lambda _, model: {"name": "models/" + model})
    monkeypatch.setattr(GeminiEditingProvider, "verify", lambda *args: {"candidates": [{"content": {"parts": [{"text": json.dumps({"passed": True, "confidence": 0.9, "issues": []})}]}}]})


def document(client, auth):
    workspace = client.get("/api/v1/studios/v1/bridge/session", headers=auth).json()["workspace"]["id"]
    body = {"workspaceId": workspace, "title": "Imagem do produto", "contentType": "visual", "brandRevision": 1,
            "brief": {"objective": "Fotografia do produto com luz natural", "audience": "Público a definir", "angle": "Fotografia do produto com luz natural", "restrictions": ["Enquadramento solicitado: 1:1"]},
            "composition": {"pages": [{"id": "page-1", "width": 1080, "height": 1080, "layers": [], "background": "#FFFFFF"}], "tracks": [], "narrative": {"imageStudio": {"aspect": "1:1"}}}, "assets": [], "correlationId": "image-contract"}
    response = client.post("/api/v1/studios/v1/documents", headers=auth, json=body)
    assert response.status_code == 201, response.text
    return workspace, response.json()


def test_image_generation_is_persistent_private_idempotent_and_requires_human_review(monkeypatch, tmp_path):
    setup(monkeypatch, tmp_path)
    calls = []
    generated = png("coral")

    def generate(*args):
        calls.append(1)
        return {"candidates": [{"content": {"parts": [{"inlineData": {"mimeType": "image/png", "data": base64.b64encode(generated).decode()}}]}}], "usageMetadata": {"totalTokenCount": 25}}

    monkeypatch.setattr(GeminiEditingProvider, "image", generate)
    auth = headers(client="image-contract")
    with TestClient(app) as client:
        workspace, doc = document(client, auth)
        path = f"/api/v1/studios/v1/documents/{doc['documentId']}/editing-ai-jobs"
        body = {"schemaVersion": "studio.editing-ai-request.v1", "expectedDocumentRevision": 1, "operation": "generate_image", "prompt": "Fotografia do produto com luz natural", "referenceAssetIds": [], "preserve": []}
        request_auth = admitted(auth, doc["documentId"], "image-frontend-generate-001")
        created = client.post(path, headers=request_auth, json=body)
        assert created.status_code == 202, created.text
        assert created.json()["documentId"] == doc["documentId"]
        assert created.json()["idempotencyKey"] == request_auth["Idempotency-Key"]
        assert created.json()["jobType"] == "editing_gemini"
        assert created.json()["request"]["input"]["operation"] == "generate_image"
        identifier = created.json()["id"]
        assert client.post(path, headers=request_auth, json=body).json()["id"] == identifier
        with SessionLocal() as db:
            job = db.get(StudioGenerationJob, identifier)
            execute_job_once(db, job)
            assert job.status == "succeeded", job.error_message
            result = job.result_payload
            asset = db.get(LibraryAsset, result["assetId"])
            assert asset.object_metadata["visualReview"] == "pending"
        assert len(calls) == 1
        content = f"/api/v1/assets/{result['assetId']}/content"
        assert client.get(content, headers=auth).content == generated
        assert client.get(content, headers=headers(client="another-client")).status_code == 404
        attach = f"/api/v1/studios/v1/documents/{doc['documentId']}/editing-resources"
        assert client.post(attach, headers=auth, json={"expectedDocumentRevision": 1, "assetId": result["assetId"]}).status_code == 422
        reviewed = client.post(f"/api/v1/studios/v1/editing/resources/{result['assetId']}/review", headers=auth, json={"checksum": result["checksumSha256"], "result": "passed", "observation": "Produto e cores conferidos"})
        assert reviewed.status_code == 200, reviewed.text
        attached = client.post(attach, headers=auth, json={"expectedDocumentRevision": 1, "assetId": result["assetId"]})
        assert attached.status_code == 200, attached.text
        assert attached.json()["revision"] == 2
        assert client.get("/api/v1/studios/v1/jobs", params={"workspace_id": workspace}, headers=auth).status_code == 200


def test_image_edit_binds_original_and_references_without_overwriting_upload(monkeypatch, tmp_path):
    setup(monkeypatch, tmp_path)
    calls = []

    def edit(_provider, _model, _prompt, media):
        calls.append(len(media))
        return {"candidates": [{"content": {"parts": [{"inlineData": {"mimeType": "image/png", "data": base64.b64encode(png("blue")).decode()}}]}}]}

    monkeypatch.setattr(GeminiEditingProvider, "image", edit)
    auth = headers(client="image-edit-contract")
    with TestClient(app) as client:
        workspace, doc = document(client, auth)
        original = png("green")
        uploaded = client.post("/api/v1/studios/v1/editing/resources/upload", headers=auth, data={"workspace_id": workspace, "title": "Original.png", "metadata": json.dumps({"kind": "image", "usageEvidence": "Fotografia própria autorizada"})}, files={"file": ("original.png", original, "image/png")})
        assert uploaded.status_code == 200, uploaded.text
        asset = uploaded.json()
        attach = client.post(f"/api/v1/studios/v1/documents/{doc['documentId']}/editing-resources", headers=auth, json={"expectedDocumentRevision": 1, "assetId": asset["id"]})
        assert attach.status_code == 200, attach.text
        body = {"schemaVersion": "studio.editing-ai-request.v1", "expectedDocumentRevision": 2, "operation": "edit_image", "prompt": "Ajuste a iluminação, preservando o produto", "sourceAssetId": asset["id"], "referenceAssetIds": [], "preserve": ["Produto"]}
        path = f"/api/v1/studios/v1/documents/{doc['documentId']}/editing-ai-jobs"
        created = client.post(path, headers=admitted(auth, doc["documentId"], "image-frontend-edit-001", "edit_image"), json=body)
        assert created.status_code == 202, created.text
        with SessionLocal() as db:
            job = db.get(StudioGenerationJob, created.json()["id"])
            execute_job_once(db, job)
            assert job.status == "succeeded", job.error_message
            assert job.result_payload["assetId"] != asset["id"]
        assert calls == [1]
        assert client.get(asset["url"], headers=auth).content == original
        assert client.post(path, headers=admitted(auth, doc["documentId"], "image-frontend-stale-001", "edit_image"), json={**body, "expectedDocumentRevision": 1}).status_code == 409


def test_image_provider_disabled_never_returns_a_fake_image(monkeypatch, tmp_path):
    setup(monkeypatch, tmp_path)
    monkeypatch.setattr(get_settings(), "studio_editing_ai_image_provider", "none")
    monkeypatch.setattr(GeminiEditingProvider, "image", lambda *args: (_ for _ in ()).throw(AssertionError("Unexpected provider call")))
    auth = headers(client="image-disabled")
    with TestClient(app) as client:
        _, doc = document(client, auth)
        result = client.post(f"/api/v1/studios/v1/documents/{doc['documentId']}/editing-ai-jobs", headers={**auth, "Idempotency-Key": "image-frontend-disabled-001"}, json={"expectedDocumentRevision": 1, "operation": "generate_image", "prompt": "Criar fotografia do produto"})
        assert result.status_code == 422, result.text
        assert "assetId" not in result.json()


def test_image_bridge_shares_validated_resource_routes_and_rejects_cross_module_operations(monkeypatch, tmp_path):
    setup(monkeypatch, tmp_path)
    auth = headers(client="image-module", allowed=["create-image", "create-video"])
    with TestClient(app) as client:
        _, doc = document(client, auth)
        assert client.get("/api/v1/studios/v1/editing/gemini").status_code == 401
        assert client.get("/api/v1/studios/v1/editing/gemini", headers=auth).status_code == 200
        for operation in ["generate_video", "edit_video", "plan"]:
            denied = client.post(f"/api/v1/studios/v1/documents/{doc['documentId']}/editing-ai-jobs", headers={**auth, "Idempotency-Key": "image-module-guard-001"}, json={"expectedDocumentRevision": 1, "operation": operation, "prompt": "Não executar fora do módulo"})
            assert denied.status_code == 403, denied.text
        # Shared resource routes validate inputs; audiovisual production stays video-scoped.
        assert client.post("/api/v1/studios/v1/editing/resources/import", headers=auth, json={}).status_code == 422
        assert client.post(f"/api/v1/studios/v1/documents/{doc['documentId']}/production-runs", headers=auth, json={}).status_code == 403
        # The generic queue must not bypass Node's quota-gated image admission.
        for field in ["jobType", "job_type"]:
            denied = client.post("/api/v1/studios/v1/jobs", headers={**auth, "Idempotency-Key": "image-generic-bypass-001"}, json={"workspaceId": doc["workspaceId"], "documentId": doc["documentId"], field: "editing_gemini", "provider": "google.gemini-editing", "request": {"input": {"operation": "generate_image"}}})
            assert denied.status_code == 422, denied.text
            assert denied.json()["detail"]["code"] == "use_image_editing_jobs_endpoint"
        for content_type in [None, "application/problem+json", "application/JSON"]:
            transport_headers = {**auth, "Idempotency-Key": "image-transport-bypass-001"}
            if content_type:
                transport_headers["Content-Type"] = content_type
            denied = client.post("/api/v1/studios/v1/jobs", headers=transport_headers, content=json.dumps({"workspaceId": doc["workspaceId"], "documentId": doc["documentId"], "job_type": "editing_gemini", "provider": "google.gemini-editing", "request": {"input": {"operation": "generate_image"}}}))
            assert denied.status_code == 422, denied.text
            assert denied.json()["detail"]["code"] == "use_image_editing_jobs_endpoint"
            video_headers = {**headers(client="image-module", module="create-video", allowed=["create-image", "create-video"]), "Idempotency-Key": "image-video-transport-001"}
            if content_type:
                video_headers["Content-Type"] = content_type
            denied = client.post(f"/api/v1/studios/v1/documents/{doc['documentId']}/editing-ai-jobs", headers=video_headers, content=json.dumps({"expectedDocumentRevision": 1, "operation": "generate_image", "prompt": "Não contornar a cota pela aba Vídeo"}))
            assert denied.status_code == 403, denied.text


def test_image_budget_is_enforced_before_the_provider_and_without_an_output(monkeypatch, tmp_path):
    setup(monkeypatch, tmp_path)
    monkeypatch.setattr(get_settings(), "studio_gemini_test_budget_usd", 0)
    monkeypatch.setattr(get_settings(), "studio_production_test_budget_usd", 0)
    calls = []
    monkeypatch.setattr(GeminiEditingProvider, "image", lambda *args: calls.append(1))
    auth = headers(client="image-budget")
    with TestClient(app) as client:
        _, doc = document(client, auth)
        created = client.post(f"/api/v1/studios/v1/documents/{doc['documentId']}/editing-ai-jobs", headers=admitted(auth, doc["documentId"], "image-budget-guard-001"), json={"expectedDocumentRevision": 1, "operation": "generate_image", "prompt": "Fotografia de um produto"})
        assert created.status_code == 202, created.text
        with SessionLocal() as db:
            job = db.get(StudioGenerationJob, created.json()["id"])
            for _ in range(job.max_attempts):
                execute_job_once(db, job)
            assert job.status in {"failed", "retrying"}
            assert "budget" in (job.error_message or job.error_code)
            assert not (job.result_payload or {}).get("assetId")
        assert calls == []
