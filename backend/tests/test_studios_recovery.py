"""Structural recovery regression tests. All provider boundaries are offline doubles."""

import base64
import io
import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from pydantic import SecretStr
from test_clicko_studio_bridge import KEY, headers
from test_image_frontend_contract import admitted, document, setup
from test_video_frontend_contract import draft

from app.config import Settings, get_settings
from app.database import SessionLocal
from app.models import StudioGenerationJob, User
from app.providers.studios.gemini_editing import GeminiEditingProvider, image_config
from app.services.studios.external_policy import assert_operation, reserve_monthly
from app.services.studios.jobs import execute_job_once
from app.studio_app import app


def test_native_image_transport_and_output_token_contract():
    calls = []

    def transport(request):
        calls.append(json.loads(request.content))
        return httpx.Response(200, json={"text": "{}"})

    with httpx.Client(transport=httpx.MockTransport(transport)) as client:
        provider = GeminiEditingProvider("test-only", client)
        provider.image("gemini-3.1-flash-lite-image", "Imagem", [], aspect_ratio="4:5", image_size="1K")
        assert calls[-1]["generationConfig"]["imageConfig"] == {"aspectRatio": "4:5", "imageSize": "1K"}
        provider.plan("gemini-3.8-flash", {"maxOutputTokens": 16384}, [])
        assert calls[-1]["generationConfig"]["maxOutputTokens"] == 16384
        with pytest.raises(ValueError, match="resolution_unsupported"):
            provider.image("gemini-3.1-flash-lite-image", "Imagem", [], image_size="4K")
        assert image_config("gemini-3.1-flash-image", "16:9", "4K")["imageSize"] == "4K"


def test_current_renderers_supply_a_real_video_artifact_to_critique():
    from types import SimpleNamespace

    from app.services.studios.gemini_editing import critique_artifact

    artifact = {"assetId": "result", "checksumSha256": "a" * 64, "mediaType": "video/mp4"}
    assert (
        critique_artifact(
            SimpleNamespace(job_type="craft_render", result_payload={"artifact": {**artifact, "durationMs": 2000}})
        )["durationMs"]
        == 2000
    )
    assert (
        critique_artifact(
            SimpleNamespace(job_type="timeline_render", result_payload={**artifact, "durationSeconds": 2.5})
        )["durationMs"]
        == 2500
    )
    with pytest.raises(ValueError, match="duration_required"):
        critique_artifact(SimpleNamespace(job_type="timeline_render", result_payload=artifact))
    with pytest.raises(ValueError, match="artifact_required"):
        critique_artifact(
            SimpleNamespace(
                job_type="craft_render", result_payload={"artifact": {**artifact, "mediaType": "image/png"}}
            )
        )


def test_image_aspect_is_validated_before_delivery_without_a_hidden_paid_review(monkeypatch, tmp_path):
    setup(monkeypatch, tmp_path)
    output = io.BytesIO()
    Image.new("RGB", (320, 400), "coral").save(output, "PNG")
    payloads = []

    def request(_self, method, path, payload=None):
        assert method == "POST"
        payloads.append(payload)
        return {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "inlineData": {
                                    "mimeType": "image/png",
                                    "data": base64.b64encode(output.getvalue()).decode(),
                                }
                            }
                        ]
                    }
                }
            ]
        }

    monkeypatch.setattr(GeminiEditingProvider, "request", request)
    monkeypatch.setattr(GeminiEditingProvider, "verify", lambda *a: pytest.fail("Unreserved paid verification"))
    auth = headers(client="aspect-recovery")
    with TestClient(app) as client:
        _, doc = document(client, auth)
        path = f"/api/v1/studios/v1/documents/{doc['documentId']}/editing-ai-jobs"
        body = {
            "expectedDocumentRevision": 1,
            "operation": "generate_image",
            "prompt": "Produto em retrato",
            "aspectRatio": "4:5",
            "imageSize": "1K",
        }
        raw = client.post(path, headers=admitted(auth, doc["documentId"], "aspect-request-001"), json=body)
        assert raw.status_code == 202, raw.text
        assert raw.json()["request"]["billingScope"] == {"workspaceId": "ws-1", "userId": "member-1"}
        with SessionLocal() as db:
            job = db.get(StudioGenerationJob, raw.json()["id"])
            assert execute_job_once(db, job) == "succeeded", job.error_message
            assert job.result_payload["imageDimensions"]["width"] == 320
            assert job.result_payload["verification"]["humanApproved"] is False
            from app.services.studios.external_policy import billing_scope

            # A worker-loaded user retains the SaaS scope through the durable job audit.
            actor = db.get(User, job.requested_by)
            assert billing_scope(actor, job.workspace_id, db) == {"workspaceId": "ws-1", "userId": "member-1"}
        assert payloads[0]["generationConfig"]["imageConfig"]["aspectRatio"] == "4:5"
        # The same provider artifact cannot falsely satisfy a landscape request.
        body["aspectRatio"] = "16:9"
        raw = client.post(path, headers=admitted(auth, doc["documentId"], "aspect-request-002"), json=body)
        with SessionLocal() as db:
            job = db.get(StudioGenerationJob, raw.json()["id"])
            execute_job_once(db, job)
            assert "aspect_mismatch" in job.error_message
            assert not (job.result_payload or {}).get("assetId")
        # Accepted native pixel-grid rounding must not be mistaken for another aspect.
        output = io.BytesIO()
        Image.new("RGB", (1536, 672), "coral").save(output, "PNG")
        body["aspectRatio"] = "21:9"
        raw = client.post(path, headers=admitted(auth, doc["documentId"], "aspect-request-003"), json=body)
        with SessionLocal() as db:
            job = db.get(StudioGenerationJob, raw.json()["id"])
            assert execute_job_once(db, job) == "succeeded", job.error_message
            assert job.result_payload["imageDimensions"]["height"] == 672


def test_bridge_cannot_bypass_commercial_admission(monkeypatch, tmp_path):
    setup(monkeypatch, tmp_path)
    auth = headers(client="no-commercial-ticket")
    with TestClient(app) as client:
        _, doc = document(client, auth)
        response = client.post(
            f"/api/v1/studios/v1/documents/{doc['documentId']}/editing-ai-jobs",
            headers={**auth, "Idempotency-Key": "unmetered-image-001"},
            json={"expectedDocumentRevision": 1, "operation": "generate_image", "prompt": "Produto"},
        )
        assert response.status_code == 422
        assert response.json()["detail"]["code"] == "commercial_media_admission_required"


def test_generic_job_cannot_choose_its_own_editing_tariff_or_billing_identity():
    from types import SimpleNamespace

    from app.domain.studios.contracts import CreateGenerationJobRequest
    from app.services.studios.jobs import create_job

    request = CreateGenerationJobRequest(
        workspace_id="workspace",
        job_type="editing_gemini",
        provider="google.gemini-editing",
        correlation_id="untrusted-envelope",
        request={
            "pricing": {"imageReservationUsd": 0.000001},
            "billingScope": {"workspaceId": "someone-else", "userId": "someone-else"},
        },
    )
    with pytest.raises(ValueError, match="use_editing_jobs_endpoint"):
        create_job(None, request, "untrusted-envelope-001", SimpleNamespace(id="user", password_hash="native-user"))


def test_duplicate_worker_delivery_does_not_run_an_already_claimed_job(monkeypatch, tmp_path):
    setup(monkeypatch, tmp_path)
    from app.models import Membership

    with TestClient(app) as client:
        client.get("/api/v1/studios/v1/bridge/session", headers=headers(client="duplicate-claim"))
    with SessionLocal() as db:
        membership = db.query(Membership).first()
        job = StudioGenerationJob(
            id="already-claimed",
            workspace_id=membership.workspace_id,
            requested_by=membership.user_id,
            provider="ffmpeg.timeline-v1",
            job_type="timeline_render",
            idempotency_key="already-claimed",
            payload_hash="a" * 64,
            correlation_id="claim",
            status="running",
            attempts=1,
            request_payload={},
        )
        db.add(job)
        db.commit()
        assert execute_job_once(db, job) == "running"
        assert job.attempts == 1
        assert job.result_payload is None


def test_direct_gemini_video_respects_operator_flags_and_native_limits():
    settings = Settings(_env_file=None)
    with pytest.raises(ValueError, match="video_generation_disabled"):
        assert_operation(settings, "google.gemini-editing", "generate_video")
    settings.gemini_outbound_enabled = settings.gemini_video_generation_enabled = True
    settings.gemini_max_external_spend_usd = 1
    with pytest.raises(ValueError, match="duration_unsupported"):
        assert_operation(
            settings, "google.gemini-editing", "generate_video", model="gemini-omni-1.1-flash", seconds=3600
        )
    with pytest.raises(ValueError, match="text_to_video_duration"):
        assert_operation(
            settings,
            "google.gemini-editing",
            "edit_video",
            model="veo-3.1-lite-generate-preview",
            media=True,
            seconds=8,
        )


def test_production_financial_limits_retain_unknown_outcomes_across_correlations(monkeypatch, tmp_path):
    setup(monkeypatch, tmp_path)
    with TestClient(app) as client:
        client.get("/api/v1/studios/v1/bridge/session", headers=headers(client="budget-global"))
        alternate = client.get(
            "/api/v1/studios/v1/bridge/session", headers=headers(client="budget-other-client")
        ).json()
    with SessionLocal() as db:
        user = db.query(User).first()
        from app.models import Membership

        workspace = db.query(Membership).filter_by(user_id=user.id).first().workspace_id

        def job(identifier, correlation):
            return StudioGenerationJob(
                id=identifier,
                workspace_id=workspace,
                requested_by=user.id,
                provider="google.gemini-editing",
                job_type="editing_gemini",
                idempotency_key=identifier,
                payload_hash="a" * 64,
                correlation_id=correlation,
                status="queued",
                created_at=datetime.now(UTC),
                request_payload={
                    "model": "gemini-3.1-flash-lite-image",
                    "input": {"operation": "generate_image"},
                    "billingScope": {"workspaceId": "saas-account", "userId": "saas-member"},
                },
                result_payload={},
            )

        first = job("financial-first", "correlation-a")
        db.add(first)
        db.commit()
        settings = Settings(_env_file=None, environment="production")
        with pytest.raises(ValueError, match="monthly_budget_required"):
            reserve_monthly(db, first, 0.1, settings)
        settings.studio_external_monthly_budget_usd = 0.2
        settings.studio_external_workspace_monthly_budget_usd = 0.2
        settings.studio_external_user_monthly_budget_usd = 0.2
        settings.studio_external_model_monthly_budgets = {"gemini-3.1-flash-lite-image": 10}
        reserve_monthly(db, first, 0.15, settings)
        # A preflight-rejected old job can be retried in a new month. Its new
        # reservation must count now, regardless of the original creation date.
        first.created_at = datetime.now(UTC) - timedelta(days=62)
        first.status = "failed"
        first.result_payload = {**first.result_payload, "submissionStarted": True, "submissionOutcome": "unknown"}
        db.commit()
        second = job("financial-second", "unrelated-correlation")
        second.workspace_id = alternate["workspace"]["id"]
        second.requested_by = alternate["user"]["id"]
        db.add(second)
        db.commit()
        with pytest.raises(ValueError, match="monthly_budget_exceeded"):
            reserve_monthly(db, second, 0.1, settings)
        # Neither a new client partition nor its derived user UUID resets SaaS limits.
        settings.studio_external_monthly_budget_usd = 10
        settings.studio_external_user_monthly_budget_usd = 10
        with pytest.raises(ValueError, match="monthly_budget_exceeded"):
            reserve_monthly(db, second, 0.1, settings)
        settings.studio_external_workspace_monthly_budget_usd = 10
        settings.studio_external_user_monthly_budget_usd = 0.2
        with pytest.raises(ValueError, match="monthly_budget_exceeded"):
            reserve_monthly(db, second, 0.1, settings)
        assert first.result_payload["providerReportedCostUsd"] is None


def test_readiness_checks_dependencies_and_entrypoints_share_media_routes(monkeypatch, tmp_path):
    monkeypatch.setenv("CLICKO_STUDIOS_BRIDGE_SECRET", KEY)
    monkeypatch.setattr(get_settings(), "celery_task_always_eager", True)
    from app.main import app as primary
    from app.providers.studios import timeline_ffmpeg

    def routes(value):
        return {
            (route.path, tuple(sorted(route.methods or [])))
            for route in value.routes
            if route.path.startswith("/api/v1/studios/v1")
        }

    assert routes(primary) <= routes(app)
    with TestClient(app) as client:
        assert client.get("/health/ready").status_code == 200
        monkeypatch.setattr(timeline_ffmpeg, "capability", lambda: {"available": False})
        response = client.get("/health/ready")
        assert response.status_code == 503
        assert response.json()["dependencies"]["ffmpeg"] == "unavailable"


def test_canonical_ai_reuses_existing_planner_and_commits_a_validated_timeline_once(monkeypatch, tmp_path):
    monkeypatch.setenv("CLICKO_STUDIOS_BRIDGE_SECRET", KEY)
    monkeypatch.setattr(get_settings(), "storage_path", str(tmp_path / "objects"))
    settings = get_settings()
    monkeypatch.setattr(settings, "studio_llm_credential_key", SecretStr("test-key-" * 8))
    from app.providers.studios.universal_llm import UniversalLLMPlanner

    calls = []

    def plan(_self, model, context, media):
        calls.append(context)
        timeline = context["project"]["timeline"]
        timeline["tracks"] = [
            {
                "id": "title",
                "kind": "caption",
                "name": "Título",
                "cues": [
                    {
                        "id": "title-one",
                        "text": "Clicko",
                        "timeline": {"startFrame": 0, "durationFrames": 24},
                        "style": {"fontFamily": "system", "fontSize": 26},
                    }
                ],
            }
        ]
        return {
            "text": json.dumps(
                {
                    "commands": [{"id": "timeline.replace", "params": {"timeline": timeline}}],
                    "rationale": "Título solicitado",
                    "submissionStarted": False,
                    "providerReportedCostUsd": 999,
                }
            ),
            "usage": {},
        }

    monkeypatch.setattr(UniversalLLMPlanner, "plan", plan)
    auth = headers(module="create-video", client="canonical-ai")
    with TestClient(app) as client:
        workspace = client.get("/api/v1/studios/v1/bridge/session", headers=auth).json()["workspace"]["id"]
        value = draft(workspace)
        response = client.post("/api/v1/studios/v1/documents", headers=auth, json=value)
        doc = response.json()
        connection = client.post(
            "/api/v1/studios/v1/craft/llm-connections",
            params={"workspace_id": workspace},
            headers=auth,
            json={
                "label": "Local free planner",
                "provider": "custom",
                "protocol": "ollama_chat",
                "baseUrl": "http://127.0.0.1:11434",
                "models": ["local-planner"],
                "enabled": True,
                "billingMode": "local_free",
                "budgetUsd": 0,
                "inputUsdPerMillion": 0,
                "outputUsdPerMillion": 0,
            },
        )
        assert connection.status_code == 201, connection.text
        path = f"/api/v1/studios/v1/video/documents/{doc['documentId']}/ai-commands"
        keyed = {**auth, "Idempotency-Key": "canonical-ai-title-001"}
        body = {
            "expectedRevision": 1,
            "instruction": "Adicione o título Clicko",
            "connectionId": connection.json()["id"],
        }
        response = client.post(path, headers=keyed, json=body)
        assert response.status_code == 200, response.text
        assert response.json()["document"]["revision"] == 2
        assert response.json()["document"]["composition"]["mediaTimeline"]["tracks"][0]["cues"][0]["text"] == "Clicko"
        assert client.post(path, headers=keyed, json=body).json()["receiptId"] == response.json()["receiptId"]
        assert len(calls) == 1
        with SessionLocal() as db:
            row = db.query(StudioGenerationJob).filter_by(idempotency_key="canonical-ai-title-001").one()
            assert row.result_payload["submissionStarted"] is True
            assert row.result_payload.get("providerReportedCostUsd") is None
