# ruff: noqa: F401, F811
import json
import shutil

import httpx
import pytest
from pydantic import SecretStr
from test_contextual_editing import media, project
from test_editing_resources import headers

from app.config import get_settings
from app.database import SessionLocal
from app.models import StudioGenerationJob
from app.providers.studios.runway_editing import RunwayEditingProvider
from app.services.studios.jobs import execute_job_once


def test_runway_native_transport_and_resume(media):
    calls = []

    def respond(request):
        calls.append(request)
        assert request.headers["X-Runway-Version"] == "2024-11-06"
        if request.method == "POST":
            assert request.url.path == "/v1/video_to_video"
            body = json.loads(request.content)
            assert body["model"] == "aleph2"
            assert body["videoUri"].startswith("data:video/mp4;base64,")
            return httpx.Response(200, json={"id": "task-1"})
        return httpx.Response(
            200, json={"id": "task-1", "status": "SUCCEEDED", "output": ["https://cdn.example/out.mp4"]}
        )

    provider = RunwayEditingProvider("test", client=httpx.Client(transport=httpx.MockTransport(respond)))
    result = provider.video("aleph2", "Change the background color", [(media["source"], "video/mp4")], 2)
    assert result["status"] == "pending"
    assert provider.retrieve(result["id"])["output_video"]["uri"]
    assert len(calls) == 2


def test_runway_timeout_does_not_repost():
    calls = []

    def respond(request):
        calls.append(request)
        raise httpx.ReadTimeout("unknown")

    provider = RunwayEditingProvider("test", client=httpx.Client(transport=httpx.MockTransport(respond)))
    with pytest.raises(ValueError, match="outcome_unknown"):
        provider.video("gen4.5", "Landscape", [], 4)
    assert len(calls) == 1


def test_runway_does_not_ignore_extra_references(media):
    provider = RunwayEditingProvider("test")
    with pytest.raises(ValueError, match="reference_layout_required"):
        provider.video("gen4.5", "Scene", [(media["source"], "image/png")] * 2, 4)


def test_invalid_input_does_not_reserve_or_claim_a_paid_submission(client, project, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "studio_runway_enabled", True)
    monkeypatch.setattr(settings, "studio_runway_test_key", SecretStr("test-only"))
    monkeypatch.setattr(settings, "studio_runway_test_budget_usd", 10)
    monkeypatch.setattr(settings, "studio_editing_ai_video_provider", "runway")
    from app import tasks

    monkeypatch.setattr(tasks.execute_studio_generation, "delay", lambda _: None)
    monkeypatch.setattr(
        RunwayEditingProvider,
        "request",
        lambda *args: (_ for _ in ()).throw(AssertionError("Input errors must not reach the API")),
    )
    response = client.post(
        f"/api/v1/studios/v1/documents/{project['document']}/editing-ai-jobs",
        headers=headers(project),
        json={"expectedDocumentRevision": 1, "operation": "generate_video", "prompt": "x" * 1001, "durationSeconds": 2},
    )
    assert response.status_code == 202, response.text
    with SessionLocal() as db:
        task = db.get(StudioGenerationJob, response.json()["id"])
        assert execute_job_once(db, task) == "failed", task.error_message
        assert not (task.result_payload or {}).get("submissionStarted")
        assert not (task.result_payload or {}).get("testReservationUsd")


def test_runway_edit_applies_after_review_without_gemini(client, project, media, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "studio_gemini_enabled", False)
    monkeypatch.setattr(settings, "studio_runway_enabled", True)
    monkeypatch.setattr(settings, "studio_runway_test_key", SecretStr("test-only"))
    monkeypatch.setattr(settings, "studio_runway_test_budget_usd", 10)
    monkeypatch.setattr(settings, "studio_editing_ai_video_provider", "runway")
    from app import tasks

    monkeypatch.setattr(tasks.execute_studio_generation, "delay", lambda _: None)
    monkeypatch.setattr(
        RunwayEditingProvider,
        "submit_video",
        lambda *args: {"id": "task-1", "status": "completed", "output_video": {"uri": "https://cdn.example/out.mp4"}},
    )
    monkeypatch.setattr(
        RunwayEditingProvider, "download", lambda self, uri, destination: shutil.copyfile(media["source"], destination)
    )
    response = client.post(
        f"/api/v1/studios/v1/documents/{project['document']}/editing-ai-jobs",
        headers=headers(project),
        json={
            "expectedDocumentRevision": 1,
            "operation": "edit_video",
            "prompt": "Alterar somente o fundo",
            "sourceAssetId": project["asset"],
            "durationSeconds": 2,
            "preserve": ["áudio", "pessoa"],
        },
    )
    assert response.status_code == 202, response.text
    with SessionLocal() as db:
        task = db.get(StudioGenerationJob, response.json()["id"])
        assert task.provider == "runway.editing-video"
        assert execute_job_once(db, task) == "succeeded", task.error_message
        result = task.result_payload
        assert result["status"] == "candidate_pending_review"
        assert result["originalAudioPreserved"]
    path = f"/api/v1/studios/v1/documents/{project['document']}/editing-resources/apply"
    body = {"expectedDocumentRevision": 1, "assetId": result["assetId"], "targetClipId": "clip"}
    assert client.post(path, headers=headers(project), json=body).status_code == 422
    reviewed = client.post(
        f"/api/v1/studios/v1/editing/resources/{result['assetId']}/review",
        headers=headers(project),
        json={"checksum": result["checksumSha256"], "result": "passed", "observation": "Local fixture checked"},
    )
    assert reviewed.status_code == 200, reviewed.text
    applied = client.post(path, headers=headers(project), json=body)
    assert applied.status_code == 200, applied.text
    assert applied.json()["composition"]["mediaTimeline"]["tracks"][0]["clips"][0]["assetId"] == result["assetId"]
