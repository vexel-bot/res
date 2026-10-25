"""Contract tests only: fake credentials/transports, never real Gemini inference."""

import hashlib
import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from fastapi.testclient import TestClient
from test_clicko_studio_bridge import headers
from test_local_agents import BASE, apply, create, prepare

from app.config import get_settings
from app.database import SessionLocal
from app.domain.studios.contracts import CreativeDocumentV1
from app.models import StudioGenerationJob, StudioLLMConnection
from app.providers.studios.universal_llm import UniversalLLMPlanner
from app.services.studios import local_agents
from app.services.studios import motion_gemini as service
from app.services.studios.jobs import execute_job_once
from app.studio_app import app

KEY = "AIza" + "A" * 35
MODEL = "gemini-contract-test"
BRIEF = (
    "Crie um Motion Design de 15 segundos sobre inteligência artificial nas empresas, "
    "com tipografia dinâmica, elementos tecnológicos, transições fluidas e estética premium."
)


def setup(monkeypatch, tmp_path):
    prepare(monkeypatch, tmp_path)
    settings = get_settings()
    monkeypatch.setattr(settings, "clicko_dev_mode", True)
    monkeypatch.setattr(settings, "clicko_motion_gemini_experimental", True)
    monkeypatch.setattr(
        settings,
        "studio_llm_credential_key",
        __import__("pydantic").SecretStr("test-encryption-key-not-a-real-secret-000"),
    )
    monkeypatch.setattr(settings, "clicko_motion_gemini_free_tier_evidence_file", None)
    monkeypatch.setenv("CLICKO_LOCAL_DATA_DIR", str(tmp_path))
    return headers(module="create-video", client="local-agents", motionGeminiExperimental=True)


def paths(client, auth):
    workspace = client.get(BASE + "/bridge/session", headers=auth).json()["workspace"]["id"]
    return workspace, BASE + "/agents/motion-gemini?workspace_id=" + workspace


def url(path, suffix):
    return path.replace("?", suffix + "?")


def configure(client, auth, path, monkeypatch):
    assert client.put(url(path, "/key"), headers=auth, json={"apiKey": KEY}).status_code == 200
    monkeypatch.setattr(
        UniversalLLMPlanner,
        "gemini_models",
        lambda _: [{"id": MODEL, "label": "Contract fixture", "outputTokenLimit": 8000}],
    )
    response = client.post(url(path, "/test"), headers=auth)
    assert response.status_code == 200, response.text
    assert KEY not in response.text
    response = client.put(path, headers=auth, json={"enabled": True, "model": MODEL})
    assert response.status_code == 200, response.text


def receipt(monkeypatch, tmp_path):
    with SessionLocal() as db:
        row = db.query(StudioLLMConnection).filter_by(provider=service.PROVIDER).one()
        data = {
            "credentialSha256": hashlib.sha256(KEY.encode()).hexdigest(),
            "workspaceId": row.workspace_id,
            "userId": row.created_by,
            "model": MODEL,
            "projectId": "contract-fixture-only",
            "tier": "free",
            "billingDisabled": True,
            "inferenceAuthorized": True,
            "structuredOutputVerified": True,
            "evidenceReference": "TEST FIXTURE — not a live billing verification",
            "verifiedAt": datetime.now(UTC).isoformat(),
            "expiresAt": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
            "requestsPerMinute": 1,
            "requestsPerDay": 2,
            "maxOutputTokens": 6000,
            "inputTokensPerMinute": 24000,
        }
    filename = tmp_path / "proof.json"
    filename.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(get_settings(), "clicko_motion_gemini_free_tier_evidence_file", str(filename))
    return filename


def test_dev_flag_signed_claim_and_production_isolation(monkeypatch, tmp_path):
    auth = setup(monkeypatch, tmp_path)
    with TestClient(app) as client:
        _, path = paths(client, auth)
        assert client.get(path).status_code == 401
        assert client.get(path, headers=headers(module="create-video", client="local-agents")).status_code == 404
        assert client.get(path, headers=auth).status_code == 200
        monkeypatch.setattr(get_settings(), "clicko_motion_gemini_experimental", False)
        assert client.get(path, headers=auth).status_code == 404
        monkeypatch.setattr(get_settings(), "clicko_motion_gemini_experimental", True)
        monkeypatch.setattr(get_settings(), "environment", "production")
        assert client.get(path, headers=auth).status_code == 404


def test_key_encrypted_scoped_hidden_and_removed(monkeypatch, tmp_path):
    auth = setup(monkeypatch, tmp_path)
    with TestClient(app) as client:
        workspace, path = paths(client, auth)
        invalid = client.put(url(path, "/key"), headers=auth, json={"apiKey": "bad-key"})
        assert invalid.status_code == 422 and "bad-key" not in invalid.text
        configure(client, auth, path, monkeypatch)
        with SessionLocal() as db:
            row = db.query(StudioLLMConnection).one()
            assert KEY not in row.credential_ciphertext and KEY not in json.dumps(row.config)
            identifier = row.id
        generic = client.get(BASE + "/craft/llm-connections?workspace_id=" + workspace, headers=auth)
        assert generic.json()["connections"] == []
        other = headers(module="create-video", client="local-agents", sub="other", motionGeminiExperimental=True)
        assert client.get(path, headers=other).json()["hasCredential"] is False
        assert (
            client.delete(
                BASE + f"/craft/llm-connections/{identifier}?workspace_id={workspace}&expected_revision=1", headers=auth
            ).status_code
            == 422
        )
        result = client.delete(url(path, "/key"), headers=auth).json()
        assert not result["hasCredential"] and not result["enabled"]
        with SessionLocal() as db:
            assert db.query(StudioLLMConnection).one().credential_ciphertext is None


def test_catalog_never_proves_free_and_unverified_inference_is_not_called(monkeypatch, tmp_path):
    auth = setup(monkeypatch, tmp_path)
    with TestClient(app) as client:
        _, path = paths(client, auth)
        configure(client, auth, path, monkeypatch)
        status = client.get(path, headers=auth).json()
        assert status["hasCredential"] and not status["freeTierVerified"] and not status["inferenceReady"]
        assert client.put(path, headers=auth, json={"model": "invented-model", "enabled": True}).status_code == 422
        doc, _ = create(client, auth)

        def forbidden(*args):
            pytest.fail("No inference before verified free-tier admission")

        monkeypatch.setattr(UniversalLLMPlanner, "plan", forbidden)
        response = client.post(
            BASE + f"/documents/{doc['documentId']}/agent-tasks",
            headers={**auth, "Idempotency-Key": "blocked-plan-001"},
            json={"instruction": BRIEF, "expectedRevision": doc["revision"], "planner": "gemini_experimental"},
        )
        assert response.status_code == 422 and "free_tier_unverified" in response.text
        assert client.get(BASE + f"/documents/{doc['documentId']}", headers=auth).json()["revision"] == doc["revision"]


def test_validated_mock_plan_uses_real_review_apply_edit_render_contract(monkeypatch, tmp_path):
    auth = setup(monkeypatch, tmp_path)
    with TestClient(app) as client:
        _, path = paths(client, auth)
        configure(client, auth, path, monkeypatch)
        receipt(monkeypatch, tmp_path)
        doc, _ = create(client, auth)

        def transport(self, model, context, media):
            assert model == MODEL and context["motionExperimental"] and not context["renderer"]["true3D"]
            output = local_agents.AudiovisualAgent(local_agents.ImageAgent()).plan(
                CreativeDocumentV1.model_validate(context["project"]), BRIEF
            )
            payload = output.model_dump(mode="json", by_alias=True)
            payload["direction"] = {
                "concept": "Contract fixture",
                "narrative": "Not an artistic evaluation",
                "scenes": [{"title": "Test", "durationSeconds": 15, "description": "Editable"}],
                "palette": ["#6EB8F5"],
                "typography": "system",
                "motionAndTransitions": "2D fades",
                "rhythm": "three scenes",
                "audioRecommendations": "none",
            }
            return {"text": json.dumps(payload), "usage": {"prompt_tokens": 123, "completion_tokens": 456}}

        monkeypatch.setattr(UniversalLLMPlanner, "plan", transport)
        route = BASE + f"/documents/{doc['documentId']}/agent-tasks"
        body = {
            "instruction": BRIEF,
            "expectedRevision": doc["revision"],
            "planner": "gemini_experimental",
            "durationSeconds": 15,
        }
        response = client.post(route, headers={**auth, "Idempotency-Key": "verified-plan-001"}, json=body)
        assert response.status_code == 200, response.text
        task = response.json()
        assert task["provider"] == "google.motion-gemini" and task["result"]["usage"]["completion_tokens"] == 456
        assert (
            client.post(route, headers={**auth, "Idempotency-Key": "verified-plan-001"}, json=body).json()["id"]
            == task["id"]
        )
        limited = client.post(route, headers={**auth, "Idempotency-Key": "verified-plan-002"}, json=body)
        assert limited.status_code == 422 and "quota" in limited.text
        changed = apply(client, auth, doc, task)
        assert changed["revision"] == 2 and len(changed["composition"]["pages"][0]["layers"]) > 0
        assert changed["composition"]["mediaTimeline"]["durationFrames"] == 360
        rendered = client.post(
            BASE + f"/video/documents/{changed['documentId']}/render-jobs",
            headers={**auth, "Idempotency-Key": "mock-plan-real-render"},
            json={"expectedRevision": changed["revision"]},
        )
        assert rendered.status_code == 202, rendered.text
        with SessionLocal() as db:
            job = db.get(StudioGenerationJob, rendered.json()["id"])
            assert execute_job_once(db, job) == "succeeded", job.error_message
            assert job.result_payload["downloadUrl"]
        client.put(path, headers=auth, json={"enabled": False})
        assert client.get(BASE + f"/documents/{doc['documentId']}", headers=auth).json()["revision"] == 2


@pytest.mark.parametrize("bad", ["not json", '{"commands":[{"id":"shell.execute","params":{}}],"rationale":"x"}'])
def test_bad_model_output_never_applies_or_falls_back(monkeypatch, tmp_path, bad):
    auth = setup(monkeypatch, tmp_path)
    with TestClient(app) as client:
        _, path = paths(client, auth)
        configure(client, auth, path, monkeypatch)
        receipt(monkeypatch, tmp_path)
        doc, _ = create(client, auth)
        monkeypatch.setattr(UniversalLLMPlanner, "plan", lambda *args: {"text": bad, "usage": {}})
        response = client.post(
            BASE + f"/documents/{doc['documentId']}/agent-tasks",
            headers={**auth, "Idempotency-Key": "malformed-plan-001"},
            json={"instruction": BRIEF, "expectedRevision": doc["revision"], "planner": "gemini_experimental"},
        )
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "failed" and response.json()["result"]["inference"] == "gemini_experimental"
        assert client.get(BASE + f"/documents/{doc['documentId']}", headers=auth).json()["revision"] == 1


def test_discovery_header_pagination_filter_and_no_inference():
    calls = []

    def handler(request):
        calls.append(request)
        assert request.method == "GET" and request.headers["x-goog-api-key"] == KEY and KEY not in str(request.url)
        if "pageToken" not in request.url.params:
            return httpx.Response(
                200,
                json={
                    "models": [{"name": "models/gemini-image", "supportedGenerationMethods": ["generateContent"]}],
                    "nextPageToken": "page2",
                },
            )
        return httpx.Response(
            200,
            json={
                "models": [
                    {
                        "name": "models/" + MODEL,
                        "supportedGenerationMethods": ["generateContent"],
                        "outputTokenLimit": 8000,
                    }
                ]
            },
        )

    config = {"protocol": "gemini_generate", "baseUrl": service.BASE, "models": [], "authHeader": "x-goog-api-key"}
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = UniversalLLMPlanner(config, KEY, client=client).gemini_models()
    assert result[0]["id"] == MODEL and len(calls) == 2


@pytest.mark.parametrize("code", [400, 401, 403, 404, 429, 500])
def test_provider_error_is_sanitized_and_never_retried(code):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(code, json={"error": {"message": KEY}})

    config = {
        "protocol": "gemini_generate",
        "baseUrl": service.BASE,
        "models": [MODEL],
        "authHeader": "x-goog-api-key",
        "authPrefix": "",
    }
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ValueError, match="llm_provider_http_" + str(code)) as caught:
            UniversalLLMPlanner(config, KEY, client=client).plan(
                MODEL, {"outputSchema": {}, "motionExperimental": True}, []
            )
        assert KEY not in str(caught.value) and len(calls) == 1


def test_minimal_probe_and_cancellation_use_existing_durable_job(monkeypatch, tmp_path):
    from app.services.studios.jobs import request_cancel

    auth = setup(monkeypatch, tmp_path)
    with TestClient(app) as client:
        _, path = paths(client, auth)
        configure(client, auth, path, monkeypatch)
        receipt(monkeypatch, tmp_path)
        doc, _ = create(client, auth)

        def probe(self, model, context, media):
            assert context["maxOutputTokens"] == 128 and "project" not in context
            with SessionLocal() as db:
                task = db.query(StudioGenerationJob).filter_by(provider="google.motion-gemini", status="running").one()
                request_cancel(db, task, "Contract cancellation", task.requested_by)
            return {"text": '{"commands":[],"rationale":"ok"}', "usage": {"prompt_tokens": 5, "completion_tokens": 5}}

        monkeypatch.setattr(UniversalLLMPlanner, "plan", probe)
        result = client.post(
            BASE + f"/documents/{doc['documentId']}/agent-tasks",
            headers={**auth, "Idempotency-Key": "probe-cancel-001"},
            json={"instruction": "Probe", "expectedRevision": 1, "planner": "gemini_experimental", "probe": True},
        )
        assert result.status_code == 200, result.text
        assert result.json()["status"] == "cancelled" and result.json()["result"]["commands"] == []
        assert client.get(BASE + f"/documents/{doc['documentId']}", headers=auth).json()["revision"] == 1


def test_expired_verification_cannot_enable_inference(monkeypatch, tmp_path):
    auth = setup(monkeypatch, tmp_path)
    with TestClient(app) as client:
        _, path = paths(client, auth)
        configure(client, auth, path, monkeypatch)
        filename = receipt(monkeypatch, tmp_path)
        data = json.loads(filename.read_text())
        data["expiresAt"] = (datetime.now(UTC) - timedelta(minutes=1)).isoformat()
        filename.write_text(json.dumps(data), encoding="utf-8")
        result = client.get(path, headers=auth).json()
        assert not result["inferenceReady"] and not result["freeTierVerified"]


def test_native_schema_subset_does_not_replace_server_validation():
    from app.domain.studios.motion_gemini import MotionAgentOutput
    from app.providers.studios.universal_llm import gemini_json_schema

    original = MotionAgentOutput.model_json_schema(by_alias=True)
    native = gemini_json_schema(original)
    assert "maxProperties" in json.dumps(original) and "maxProperties" not in json.dumps(native)
    assert "$defs" in native and "commands" in native["properties"]
    assert native["properties"]["direction"] == {"$ref": "#/$defs/MotionCreativeDirection"}


@pytest.mark.parametrize(
    "credential", [KEY, "AQ." + "contract-fixture_" * 20 + "=", "opaque-test-credential-" + "X" * 200]
)
def test_registration_accepts_opaque_auth_keys_without_legacy_truncation(monkeypatch, tmp_path, credential):
    auth = setup(monkeypatch, tmp_path)
    with TestClient(app) as client:
        _, path = paths(client, auth)
        result = client.put(url(path, "/key"), headers=auth, json={"apiKey": credential})
        assert result.status_code == 200, result.text
        assert result.json()["hasCredential"] and not result.json()["inferenceReady"]
        assert credential not in result.text
        with SessionLocal() as db:
            row = db.query(StudioLLMConnection).one()
            assert credential not in row.credential_ciphertext
            assert credential not in json.dumps(row.config)


@pytest.mark.parametrize("credential", ["short", "A" * 30 + "\r\ninjected", "B" * 9000, "A" * 30 + " contains space"])
def test_opaque_key_validation_still_rejects_unsafe_or_incomplete_input(monkeypatch, tmp_path, credential):
    auth = setup(monkeypatch, tmp_path)
    with TestClient(app) as client:
        _, path = paths(client, auth)
        result = client.put(url(path, "/key"), headers=auth, json={"apiKey": credential})
        assert result.status_code == 422
        assert credential not in result.text
        assert not client.get(path, headers=auth).json()["hasCredential"]
