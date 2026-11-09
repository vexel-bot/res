"""No paid calls: discovery pricing and durable submission contracts."""

from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient
from test_video_timeline_real import create, setup

from app.config import get_settings
from app.providers.studios.openrouter_media import OpenRouterMediaProvider
from app.routers.studio_openrouter_media import MediaRequest
from app.services.studios import openrouter_media as media
from app.studio_app import app

MODEL = {
    "id": "google/veo-3.1-fast",
    "supported_durations": [4, 6, 8],
    "supported_resolutions": ["720p"],
    "supported_aspect_ratios": ["16:9"],
    "pricing_skus": {"duration_seconds_without_audio_720p": "0.08"},
}


def request(**changes):
    return {
        "connectionId": "configured",
        "kind": "video",
        "model": MODEL["id"],
        "prompt": "A clear scene",
        "durationSeconds": 6,
        "productionId": "test-production",
        "maxCostUsd": 0.9,
        **changes,
    }


def test_discovered_prices_fail_closed():
    assert media.estimate(MediaRequest.model_validate(request()), MODEL) == 0.48
    with pytest.raises(ValueError, match="pricing_unsupported"):
        media.estimate(MediaRequest.model_validate(request()), {**MODEL, "pricing_skus": {"video_tokens": "0.1"}})
    with pytest.raises(ValueError, match="duration_unsupported"):
        media.estimate(MediaRequest.model_validate(request(durationSeconds=5)), MODEL)


def test_transport_never_retries_unknown_submission():
    seen = []

    def handler(req):
        seen.append(str(req.url))
        raise httpx.ReadTimeout("lost acknowledgement")

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        adapter = OpenRouterMediaProvider("secret", client)
        with pytest.raises(ValueError, match="outcome_unknown"):
            adapter.request("POST", "/videos", {"model": "selected"})
    assert seen == ["https://openrouter.ai/api/v1/videos"]
    with pytest.raises(ValueError, match="invalid_job_id"):
        adapter.job_path("../another-origin")


def test_submit_replay_production_budget(monkeypatch, tmp_path):
    auth = setup(monkeypatch, tmp_path)
    posts = []

    class Adapter:
        def models(self):
            return [MODEL], []

        def balance(self):
            return 3.37

        def request(self, method, path, body=None):
            posts.append(body)
            return {"id": "provider-job-123", "status": "pending"}

        job_path = staticmethod(OpenRouterMediaProvider.job_path)

    monkeypatch.setattr(media, "provider", lambda *args: (SimpleNamespace(id="configured"), Adapter()))
    for setting in [
        "studio_external_monthly_budget_usd",
        "studio_external_workspace_monthly_budget_usd",
        "studio_external_user_monthly_budget_usd",
    ]:
        monkeypatch.setattr(get_settings(), setting, 5)
    monkeypatch.setattr(get_settings(), "studio_external_model_monthly_budgets", {MODEL["id"]: 5})
    with TestClient(app) as client:
        _, doc = create(client, auth)
        path = f"/api/v1/studios/v1/video/documents/{doc['documentId']}/openrouter-media"
        first = client.post(path, headers={**auth, "Idempotency-Key": "submission-001"}, json=request())
        assert first.status_code == 202, first.text
        replay = client.post(path, headers={**auth, "Idempotency-Key": "submission-001"}, json=request())
        assert replay.json()["id"] == first.json()["id"]
        assert len(posts) == 1
        conflict = client.post(
            path, headers={**auth, "Idempotency-Key": "submission-001"}, json=request(prompt="changed")
        )
        assert conflict.status_code == 409
        exhausted = client.post(path, headers={**auth, "Idempotency-Key": "submission-002"}, json=request())
        assert exhausted.status_code == 409, exhausted.text
        assert exhausted.json()["detail"]["code"] == "openrouter_media_production_budget_exceeded"
        raised = client.post(path, headers={**auth, "Idempotency-Key": "submission-003"}, json=request(maxCostUsd=5))
        assert raised.status_code == 409
        assert len(posts) == 1


def test_unknown_submission_is_not_repeated_on_retry(monkeypatch, tmp_path):
    auth = setup(monkeypatch, tmp_path)
    calls = []

    class Adapter:
        def models(self):
            return [MODEL], []

        def balance(self):
            return 3.37

        def request(self, *args):
            calls.append(args)
            raise ValueError("openrouter_media_transport_outcome_unknown")

    monkeypatch.setattr(media, "provider", lambda *args: (SimpleNamespace(id="configured"), Adapter()))
    for setting in [
        "studio_external_monthly_budget_usd",
        "studio_external_workspace_monthly_budget_usd",
        "studio_external_user_monthly_budget_usd",
    ]:
        monkeypatch.setattr(get_settings(), setting, 5)
    monkeypatch.setattr(get_settings(), "studio_external_model_monthly_budgets", {MODEL["id"]: 5})
    with TestClient(app) as client:
        _, doc = create(client, auth)
        path = f"/api/v1/studios/v1/video/documents/{doc['documentId']}/openrouter-media"
        first = client.post(path, headers={**auth, "Idempotency-Key": "unknown-submit-001"}, json=request())
        assert first.status_code == 422
        detail = first.json()["detail"]
        assert detail["requiresReconciliation"] and not detail["canDiscardPending"] and detail["jobId"]
        replay = client.post(path, headers={**auth, "Idempotency-Key": "unknown-submit-001"}, json=request())
        assert replay.json()["requiresReconciliation"]
        assert replay.json()["id"] == detail["jobId"]
        assert len(calls) == 1


def test_speech_is_imported_once_and_attached_to_document(monkeypatch, tmp_path):
    from app.providers.studios import timeline_ffmpeg

    auth = setup(monkeypatch, tmp_path)
    speech_model = {
        "id": "microsoft/mai-voice-2.1-flash",
        "supported_voices": ["pt-BR-Luana"],
        "pricing": {"prompt": "0.000015"},
    }
    calls = []

    class Adapter:
        def models(self):
            return [], [speech_model]

        def balance(self):
            return 3.37

        def request(self, *args, **kwargs):
            calls.append(args)
            return b"mock-audio-boundary", "generation-speech-123"

    monkeypatch.setattr(media, "provider", lambda *args: (SimpleNamespace(id="configured"), Adapter()))
    monkeypatch.setattr(
        timeline_ffmpeg, "probe", lambda path: {"streams": [{"codec_type": "audio"}], "format": {"duration": "4.2"}}
    )
    for setting in [
        "studio_external_monthly_budget_usd",
        "studio_external_workspace_monthly_budget_usd",
        "studio_external_user_monthly_budget_usd",
    ]:
        monkeypatch.setattr(get_settings(), setting, 5)
    monkeypatch.setattr(get_settings(), "studio_external_model_monthly_budgets", {speech_model["id"]: 5})
    with TestClient(app) as client:
        _, doc = create(client, auth)
        path = f"/api/v1/studios/v1/video/documents/{doc['documentId']}/openrouter-media"
        body = request(kind="speech", model=speech_model["id"], text="Uma ideia ganha vida.", voice="pt-BR-Luana")
        first = client.post(path, headers={**auth, "Idempotency-Key": "speech-submit-001"}, json=body)
        assert first.status_code == 202, first.text
        result = first.json()
        assert result["status"] == "succeeded" and result["assetId"]
        replay = client.post(path, headers={**auth, "Idempotency-Key": "speech-submit-001"}, json=body)
        assert replay.json()["assetId"] == result["assetId"] and len(calls) == 1
        updated = client.get(f"/api/v1/studios/v1/documents/{doc['documentId']}", headers=auth).json()
        assert updated["revision"] == doc["revision"] + 1
        assert any(a["id"] == result["assetId"] for a in updated["assets"])
