from __future__ import annotations

# Imported pytest fixtures intentionally share their parameter names.
# ruff: noqa: F401, F811
import subprocess
from datetime import UTC, datetime

from pydantic import SecretStr
from test_contextual_editing import media, project
from test_editing_resources import headers

from app.config import get_settings
from app.database import SessionLocal
from app.domain.studios.generative_video import GenerativeVideoOperationV1
from app.models import LibraryAsset, StudioGenerationJob
from app.providers.studios.openai_video import OpenAISoraVideoProvider
from app.services.studios.jobs import execute_job_once


def test_sora_job_creates_one_inspection_pending_four_second_asset(client, project, tmp_path, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "studio_editing_ai_video_provider", "sora")
    monkeypatch.setattr(settings, "openai_outbound_enabled", True)
    monkeypatch.setattr(settings, "openai_video_generation_enabled", True)
    monkeypatch.setattr(settings, "openai_api_key", SecretStr("test-only"))
    monkeypatch.setattr(settings, "openai_max_external_spend_usd", 0.40)
    monkeypatch.setattr(settings, "studio_editing_ai_test_budget_usd", 1)
    monkeypatch.setattr(settings, "studio_production_test_budget_usd", 0)
    from app import tasks

    monkeypatch.setattr(tasks.execute_studio_generation, "delay", lambda _: None)
    calls = {"start": 0}
    operation = GenerativeVideoOperationV1(
        requestId="placeholder",
        providerOperationId="video-test",
        status="completed",
        estimatedCostUsd=0.40,
        createdAt=datetime(2026, 9, 8, tzinfo=UTC),
        lastObservedAt=datetime(2026, 9, 8, tzinfo=UTC),
    )

    monkeypatch.setattr(OpenAISoraVideoProvider, "preflight", lambda *args: None)

    def start(self, request):
        calls["start"] += 1
        return operation.model_copy(update={"request_id": request.request_id})

    monkeypatch.setattr(OpenAISoraVideoProvider, "start", start)
    monkeypatch.setattr(OpenAISoraVideoProvider, "wait", lambda self, value, **kwargs: value)

    def download(self, request, value, destination):
        subprocess.run(
            [
                settings.ffmpeg_path,
                "-y",
                "-f",
                "lavfi",
                "-i",
                "color=#2457ff:s=320x180:r=25:d=4",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-threads",
                "2",
                str(destination),
            ],
            check=True,
            capture_output=True,
            timeout=30,
        )

    monkeypatch.setattr(OpenAISoraVideoProvider, "download", download)
    response = client.post(
        f"/api/v1/studios/v1/documents/{project['document']}/editing-ai-jobs",
        headers=headers(project),
        json={
            "expectedDocumentRevision": 1,
            "operation": "generate_video",
            "prompt": "Fluxo original abstrato de uma ideia chegando a pessoas, sem marcas e sem texto",
            "durationSeconds": 4,
        },
    )
    assert response.status_code == 202, response.text
    with SessionLocal() as db:
        job = db.get(StudioGenerationJob, response.json()["id"])
        assert job.provider == "openai.sora-2"
        assert execute_job_once(db, job) == "succeeded", job.error_message
        result = job.result_payload
        assert result["testReservationUsd"] == 0.40
        assert result["measuredCostUsd"] == 0.40
        assert result["outputVideoSeconds"] == 4
        asset = db.get(LibraryAsset, result["assetId"])
        assert asset.object_metadata["visualReview"] == "pending"
        assert asset.object_metadata["syntheticMedia"] is True
        assert asset.object_metadata["canonicalAudioRemoved"] is True
    assert calls == {"start": 1}
