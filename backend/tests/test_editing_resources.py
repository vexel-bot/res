# Fixtures imported from the existing contextual integration suite are intentionally reused.
# ruff: noqa: F811
import base64
import io
import json
from pathlib import Path
from types import SimpleNamespace as NS

import httpx
import pytest
from PIL import Image
from pydantic import SecretStr
from test_contextual_editing import document, ffmpeg, request
from test_contextual_editing import media as media
from test_contextual_editing import project as project

from app.config import get_settings
from app.database import SessionLocal
from app.domain.studios.contracts import CreativeDocumentV1
from app.models import LibraryAsset, StudioGenerationJob
from app.providers.studios.contextual_render import ContextualFFmpegProvider, inspect_document
from app.providers.studios.gemini_editing import GeminiEditingProvider
from app.providers.studios.resource_download import PublicHTTPSConnection, download_resource
from app.services.studios.jobs import execute_job_once, retry_job


def png():
    output = io.BytesIO()
    Image.new("RGB", (160, 100), "orange").save(output, "PNG")
    return output.getvalue()


def headers(project):
    return {"Authorization": f"Bearer {project['token']}", "Idempotency-Key": "editing-resource-job-test"}


def upload(client, project, kind="logo", data=None):
    return client.post(
        "/api/v1/studios/v1/editing/resources/upload",
        headers=headers(project),
        data={
            "workspace_id": project["workspace"],
            "title": "Marca arbitrária",
            "metadata": json.dumps({"kind": kind, "usageEvidence": "Arquivo próprio"}),
        },
        files={"file": ("resource", data or png(), "application/octet-stream")},
    )


def enable(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "studio_gemini_enabled", True)
    monkeypatch.setattr(settings, "studio_editing_ai_planning_provider", "gemini")
    monkeypatch.setattr(settings, "studio_gemini_test_key", SecretStr("test-only"))
    monkeypatch.setattr(settings, "studio_gemini_test_budget_usd", 5)
    monkeypatch.setattr(settings, "studio_production_test_budget_usd", 5)
    monkeypatch.setattr(settings, "studio_gemini_input_usd_per_million", 1)
    monkeypatch.setattr(settings, "studio_gemini_output_usd_per_million", 4)
    from app import tasks

    monkeypatch.setattr(tasks.execute_studio_generation, "delay", lambda _: None)
    monkeypatch.setattr(GeminiEditingProvider, "validate_model", lambda _, model: {"name": f"models/{model}"})
    monkeypatch.setattr(
        GeminiEditingProvider,
        "verify",
        lambda *args: {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": json.dumps(
                                    {"passed": False, "confidence": 0.5, "issues": ["Needs visual review"]}
                                )
                            }
                        ]
                    }
                }
            ]
        },
    )


def test_only_optional_art_direction_tail_can_be_closed_locally():
    from app.services.studios.gemini_editing import recover_truncated_art_direction_tail

    truncated = (
        '{"scenes":[{"id":"scene"}],"artDirection":'
        '{"rejectedStyleMoves":["generic", "unfinished'
    )
    recovered = recover_truncated_art_direction_tail(truncated)

    assert recovered is not None
    assert json.loads(recovered)["artDirection"]["rejectedStyleMoves"][-1] == "unfinished"
    assert recover_truncated_art_direction_tail('{"scenes":[{"id":"unfinished') is None


def test_only_optional_material_uncertainty_tail_can_be_closed_locally():
    from app.services.studios.gemini_editing import recover_truncated_material_inspection_tail

    truncated = (
        '{"description":"pixels inspected","criteria":['
        '{"index":0,"result":"supported","evidence":"visible","sampleIndices":[0]},'
        '{"index":1,"result":"contradicted","evidence":"missing","sampleIndices":[1]}],'
        '"confidence":0.9,"uncertainty":"sparse sam'
    )
    recovered = recover_truncated_material_inspection_tail(truncated, 2)

    assert recovered is not None
    assert json.loads(recovered)["criteria"][1]["result"] == "contradicted"
    assert recover_truncated_material_inspection_tail(truncated, 3) is None
    assert recover_truncated_material_inspection_tail(
        '{"criteria":[{"index":0,"result":"supported","evidence":"unfinished', 1
    ) is None


def job(client, project, **extra):
    response = client.post(
        f"/api/v1/studios/v1/documents/{project['document']}/editing-gemini-jobs",
        headers=headers(project),
        json={
            "expectedDocumentRevision": 1,
            "operation": "generate_image",
            "prompt": "Uma composição de produto",
            **extra,
        },
    )
    assert response.status_code == 202, response.text
    return response.json()["id"]


def test_catalog_deduplicates_and_isolates_tenants(client, project):
    first = upload(client, project)
    assert first.status_code == 200, first.text
    assert upload(client, project).json()["id"] == first.json()["id"]
    response = client.get(
        f"/api/v1/studios/v1/editing/resources?workspace_id={project['workspace']}&query=arbitrária",
        headers=headers(project),
    )
    assert len(response.json()) == 1
    from conftest import register

    token, _ = register(client, "catalog-other@example.com")
    assert (
        client.get(
            f"/api/v1/studios/v1/editing/resources?workspace_id={project['workspace']}",
            headers={"Authorization": f"Bearer {token}"},
        ).status_code
        == 404
    )
    attached = client.post(
        f"/api/v1/studios/v1/documents/{project['document']}/editing-resources",
        headers=headers(project),
        json={"expectedDocumentRevision": 1, "assetId": first.json()["id"]},
    )
    assert attached.status_code == 200, attached.text
    assert attached.json()["revision"] == 2
    assert (
        client.post(
            f"/api/v1/studios/v1/documents/{project['document']}/editing-resources",
            headers=headers(project),
            json={"expectedDocumentRevision": 1, "assetId": first.json()["id"]},
        ).status_code
        == 409
    )


def test_download_rejects_unregistered_hosts_and_private_dns(tmp_path, monkeypatch):
    for url in ["http://fonts.gstatic.com/a", "https://localhost/a", "https://fonts.gstatic.com@127.0.0.1/a"]:
        with pytest.raises(ValueError, match="resource_host_not_registered"):
            download_resource(url, tmp_path / "file", ["fonts.gstatic.com"])
    import socket

    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs: [(2, 1, 6, "", ("127.0.0.1", 443))])
    with pytest.raises(ValueError, match="resource_private_address"):
        PublicHTTPSConnection("fonts.gstatic.com").connect()


def test_public_https_prefers_reachable_ipv4_when_ipv6_is_listed_first(monkeypatch):
    import socket

    addresses = [
        (socket.AF_INET6, socket.SOCK_STREAM, 6, "", ("2606:4700::6812:42dc", 443, 0, 0)),
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("104.18.66.220", 443)),
    ]
    attempts = []

    class FakeSocket:
        def __init__(self, family):
            self.family = family

        def settimeout(self, _timeout):
            pass

        def connect(self, address):
            attempts.append((self.family, address))

        def close(self):
            pass

    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs: addresses)
    monkeypatch.setattr(socket, "socket", lambda family, *_args: FakeSocket(family))
    connection = PublicHTTPSConnection("images.pexels.com")
    connection._context = NS(wrap_socket=lambda sock, **_kwargs: sock)

    connection.connect()

    assert attempts == [(socket.AF_INET, ("104.18.66.220", 443))]
    assert connection.sock.family == socket.AF_INET


def test_pexels_variant_fallback_keeps_same_candidate_and_registered_hosts(tmp_path, monkeypatch):
    from app.services.studios import material_acquisition

    attempts = []

    def download(url, destination, hosts):
        attempts.append((url, hosts))
        if url.endswith("small.mp4"):
            raise ValueError("resource_download_failed")
        destination.write_bytes(b"video")

    monkeypatch.setattr(material_acquisition, "download_resource", download)
    files = [
        {"link": "https://videos.pexels.com/small.mp4", "width": 1280, "height": 720},
        {"link": "https://videos.pexels.com/large.mp4", "width": 1920, "height": 1080},
    ]
    destination = tmp_path / "candidate"

    selected = material_acquisition._download_candidate_variants(
        files, destination, ["videos.pexels.com"]
    )

    assert selected is files[1]
    assert destination.read_bytes() == b"video"
    assert [item[0] for item in attempts] == [file["link"] for file in files]
    assert all(item[1] == ["videos.pexels.com"] for item in attempts)


def test_font_used_in_export_and_missing_font_never_falls_back(tmp_path, media):
    candidates = [Path("C:/Windows/Fonts/georgia.ttf"), Path("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf")]
    font = next((p for p in candidates if p.exists()), None)
    if not font:
        pytest.skip("Serif font required")
    raw = document().model_dump(mode="json", by_alias=True)
    raw["assets"].append({"id": "font", "mediaType": "font/ttf"})
    raw["composition"]["pages"][0]["layers"] = [
        {
            "id": "text",
            "kind": "text",
            "width": 300,
            "height": 100,
            "properties": {"text": "Ação e precisão", "fontSize": 32, "fontAssetId": "font"},
        }
    ]
    doc = CreativeDocumentV1.model_validate(raw)
    renderer = ContextualFFmpegProvider("ffmpeg", 60)
    with pytest.raises(ValueError, match="editing_font_asset_missing"):
        renderer.validate_text(doc)
    renderer.validate_text(doc, {"font": font})
    custom = tmp_path / "custom.mp4"
    renderer.render(doc, request(doc), {**media, "font": font}, custom, lambda _: None, lambda: False)
    raw["composition"]["pages"][0]["layers"][0]["properties"].pop("fontAssetId")
    default_doc = CreativeDocumentV1.model_validate(raw)
    default = tmp_path / "default.mp4"
    renderer.render(default_doc, request(default_doc), media, default, lambda _: None, lambda: False)
    ffmpeg("-i", custom, "-frames:v", "1", tmp_path / "custom.png")
    ffmpeg("-i", default, "-frames:v", "1", tmp_path / "default.png")
    assert (tmp_path / "custom.png").read_bytes() != (tmp_path / "default.png").read_bytes()


@pytest.mark.parametrize(
    "prop,unit,values",
    [
        ("opacity", "ratio", [0, 1]),
        ("scale_x", "ratio", [0.5, 1]),
        ("rotation_degrees", "degrees", [0, 45]),
    ],
)
def test_motion_renders_with_curves(tmp_path, media, prop, unit, values):
    doc = document()
    clip = doc.composition.media_timeline.tracks[0].clips[0]
    clip.keyframes = [
        {
            "trackId": "motion",
            "targetLayerId": clip.id,
            "property": prop,
            "unit": unit,
            "keyframes": [{"frame": 0, "value": values[0], "easing": "ease_in_out"}, {"frame": 49, "value": values[1]}],
        }
    ]
    assert not inspect_document(doc)
    result = ContextualFFmpegProvider("ffmpeg", 60).render(
        doc, request(doc), media, tmp_path / "motion.mp4", lambda _: None, lambda: False
    )
    assert result.frames_rendered == 50


def test_gemini_image_job_persists_result_and_requires_review(client, project, monkeypatch):
    enable(monkeypatch)
    calls = []

    def image(*args):
        calls.append(1)
        return {
            "candidates": [
                {
                    "content": {
                        "parts": [{"inlineData": {"mimeType": "image/png", "data": base64.b64encode(png()).decode()}}]
                    }
                }
            ],
            "usageMetadata": {"totalTokenCount": 1200},
        }

    monkeypatch.setattr(GeminiEditingProvider, "image", image)
    identifier = job(client, project)
    assert job(client, project) == identifier
    with SessionLocal() as db:
        record = db.get(StudioGenerationJob, identifier)
        execute_job_once(db, record)
        assert record.status == "succeeded", record.error_message
        result = record.result_payload
        assert result["usage"]["totalTokenCount"] == 1200
        asset = db.get(LibraryAsset, result["assetId"])
        assert asset.object_metadata["visualReview"] == "pending"
    denied = client.post(
        f"/api/v1/studios/v1/documents/{project['document']}/editing-resources",
        headers=headers(project),
        json={"expectedDocumentRevision": 1, "assetId": result["assetId"]},
    )
    assert denied.status_code == 422, denied.text
    resolve_path = f"/api/v1/studios/v1/editing/resources/resolve?workspace_id={project['workspace']}"
    unresolved = client.post(resolve_path, headers=headers(project), json={"query": "produto", "kind": "image"})
    assert unresolved.json()["status"] == "awaiting_choice"
    accepted = client.post(
        f"/api/v1/studios/v1/editing/resources/{result['assetId']}/review",
        headers=headers(project),
        json={
            "checksum": result["checksumSha256"],
            "result": "passed",
            "observation": "Rosto, mãos e conteúdo conferidos",
        },
    )
    assert accepted.status_code == 200, accepted.text
    assert (
        client.post(resolve_path, headers=headers(project), json={"query": "produto", "kind": "image"}).json()["status"]
        == "resolved"
    )
    assert len(calls) == 1


def test_model_availability_rejects_unexpected_identity():
    calls = []

    def response(request):
        calls.append(request.method)
        return httpx.Response(200, json={"name": "models/unexpected-model"})

    with httpx.Client(transport=httpx.MockTransport(response)) as client:
        with pytest.raises(ValueError, match="gemini_model_not_available"):
            GeminiEditingProvider("test-only", client).validate_model("gemini-3.8-flash")
    assert calls == ["GET"]


def test_uncertain_submission_is_not_reposted_even_on_manual_retry(client, project, monkeypatch):
    enable(monkeypatch)
    calls = []

    def timeout(*args):
        calls.append(1)
        raise ValueError("gemini_transport_outcome_unknown")

    monkeypatch.setattr(GeminiEditingProvider, "image", timeout)
    identifier = job(client, project)
    with SessionLocal() as db:
        record = db.get(StudioGenerationJob, identifier)
        for _ in range(3):
            execute_job_once(db, record)
        assert record.status == "failed"
        retry_job(db, record, record.requested_by)
        execute_job_once(db, record)
        assert "outcome_unknown" in record.error_message
    assert len(calls) == 1


def test_production_has_no_test_budget_and_never_uses_test_key(monkeypatch):
    from app.services.studios.contextual_editing import budget_remaining
    from app.services.studios.gemini_editing import provider_key

    enable(monkeypatch)
    settings = get_settings()
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "studio_editing_monthly_budget_cents", 0)
    assert budget_remaining(None, "workspace") == float("inf")
    with pytest.raises(ValueError, match="not_configured"):
        provider_key(settings)
    monkeypatch.setattr(settings, "studio_gemini_production_key", SecretStr("production-only"))
    assert provider_key(settings) == "production-only"


def test_transport_uses_google_and_does_not_retry_or_expose_keys():
    calls = []

    def respond(request):
        calls.append(request)
        assert request.url.host == "generativelanguage.googleapis.com"
        return httpx.Response(429, json={"error": "private provider body"})

    provider = GeminiEditingProvider("never-expose-this", httpx.Client(transport=httpx.MockTransport(respond)))
    with pytest.raises(ValueError, match="^gemini_http_429$"):
        provider.image("gemini-3.1-flash-image", "test", [])
    assert len(calls) == 1


def test_planner_samples_actual_media_and_resolves_catalog_support(client, project, monkeypatch):
    enable(monkeypatch)
    asset = upload(client, project).json()["id"]
    seen = []

    def planning(self, model, context, media):
        seen.append(context)
        assert media and media[0][0].is_file()
        assert context["sampling"]["samples"][0]["clipId"] == "clip"
        return {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": json.dumps(
                                    {
                                        "beats": [
                                            {
                                                "id": "scene",
                                                "clipId": "clip",
                                                "purpose": "Mostrar o detalhe",
                                                "supportAssetId": asset,
                                            }
                                        ],
                                        "rationale": "Apoio vinculado ao objetivo",
                                        "clipOrder": [],
                                        "requiredTechniques": [],
                                        "missingResources": [],
                                    }
                                )
                            }
                        ]
                    }
                }
            ]
        }

    monkeypatch.setattr(GeminiEditingProvider, "plan", planning)
    identifier = job(
        client,
        project,
        operation="plan",
        direction={"expectedDocumentRevision": 1, "intent": {"objective": "Mostrar o produto"}},
    )
    with SessionLocal() as db:
        record = db.get(StudioGenerationJob, identifier)
        execute_job_once(db, record)
        assert record.status == "succeeded", record.error_message
        plan = record.result_payload["plan"]
        assert plan["status"] == "ready", plan["blockers"]
        assert asset in {a["id"] for a in plan["draftDocument"]["assets"]}
        assert plan["humanApproved"] is False
    assert len(seen) == 1


def test_test_budget_blocks_before_external_post(client, project, monkeypatch):
    enable(monkeypatch)
    monkeypatch.setattr(get_settings(), "studio_gemini_test_budget_usd", 0)
    monkeypatch.setattr(GeminiEditingProvider, "image", lambda *args: pytest.fail("Unexpected external call"))
    identifier = job(client, project)
    with SessionLocal() as db:
        record = db.get(StudioGenerationJob, identifier)
        execute_job_once(db, record)
        assert "test_budget_exceeded" in record.error_message
        assert not (record.result_payload or {}).get("submissionStarted")


def test_one_dollar_production_envelope_is_partitioned_and_blocks_video(monkeypatch):
    from types import SimpleNamespace

    from app.services.studios.gemini_editing import reserve_test_request

    settings = get_settings()
    monkeypatch.setattr(settings, "studio_gemini_test_budget_usd", 1)
    monkeypatch.setattr(settings, "studio_production_test_budget_usd", 1)
    monkeypatch.setattr("app.services.studios.contextual_editing.lock_editing_budget", lambda *args: None)
    jobs = []

    class Results:
        def all(self):
            return jobs

    db = SimpleNamespace(scalars=lambda query: Results())

    def task(operation="plan", stage=None):
        payload = {"operation": operation}
        if stage:
            payload["productionStage"] = stage
        job = SimpleNamespace(
            workspace_id="workspace",
            correlation_id="pilot",
            provider="google.gemini-editing",
            job_type="editing_gemini",
            request_payload={
                "environment": "test",
                "input": payload,
                "maxPromptChars": 100_000,
                "maxOutputTokens": 4096,
                "budgetAllocations": {
                    "planning": 0.20,
                    "image": 0.40,
                    "critique": 0.20,
                    "video": 0.0,
                },
                "pricing": {
                    "inputUsdPerMillion": 0.75,
                    "outputUsdPerMillion": 3.75,
                    "imageReservationUsd": 0.10,
                },
            },
            result_payload={},
        )
        jobs.append(job)
        return job

    planning = task()
    reserve_test_request(db, planning, 1)
    assert planning.result_payload["budgetCategoryCapUsd"] == 0.2
    second_planning = task()
    reserve_test_request(db, second_planning, 1)
    with pytest.raises(ValueError, match="test_budget_exceeded"):
        reserve_test_request(db, task(), 1)
    image_jobs = [task("generate_image") for _ in range(4)]
    for image_job in image_jobs:
        reserve_test_request(db, image_job, 1)
    assert sum(job.result_payload.get("testReservationUsd", 0) for job in jobs) == pytest.approx(0.6)
    with pytest.raises(ValueError, match="test_budget_exceeded"):
        reserve_test_request(db, task("generate_video"), 3)


def test_zero_production_budget_cannot_fall_back_to_provider_budget(monkeypatch):
    from types import SimpleNamespace

    from app.services.studios.gemini_editing import reserve_test_request

    settings = get_settings()
    monkeypatch.setattr(settings, "studio_editing_ai_test_budget_usd", 1)
    monkeypatch.setattr(settings, "studio_production_test_budget_usd", 0)
    job = SimpleNamespace(request_payload={"budgetAllocations": {"planning": 0.2}})
    with pytest.raises(ValueError, match="production_test_budget_not_configured"):
        reserve_test_request(None, job, 1)


def test_two_dollar_policy_uses_absolute_category_caps_and_protects_critique(monkeypatch):
    from types import SimpleNamespace

    from app.services.studios.editorial_production import motion_only_allocations
    from app.services.studios.gemini_editing import reserve_test_request

    settings = get_settings()
    monkeypatch.setattr(settings, "studio_editing_ai_test_budget_usd", 2)
    monkeypatch.setattr(settings, "studio_production_test_budget_usd", 2)
    monkeypatch.setattr("app.services.studios.contextual_editing.lock_editing_budget", lambda *args: None)
    jobs = []

    class Results:
        def all(self):
            return jobs

    db = SimpleNamespace(scalars=lambda _query: Results())

    def task(stage="direction"):
        candidate = SimpleNamespace(
            workspace_id="workspace",
            correlation_id="two-dollar-pilot",
            provider="compatible.editing-planner",
            job_type="editing_ai",
            status="queued",
            request_payload={
                "environment": "test",
                "input": {"operation": "plan", "productionStage": stage},
                "maxPromptChars": 300,
                "maxOutputTokens": 256,
                "budgetAllocations": motion_only_allocations(2),
                "pricing": {
                    "inputUsdPerMillion": 2,
                    "outputUsdPerMillion": 8,
                    "minimumReservationUsd": 0.10,
                },
            },
            result_payload={},
        )
        jobs.append(candidate)
        return candidate

    planning = task()
    reserve_test_request(db, planning, 1)
    assert planning.result_payload["budgetCategoryCapUsd"] == pytest.approx(0.85)

    critique = task("critique")
    reserve_test_request(db, critique, 1)
    assert critique.result_payload["budgetCategoryCapUsd"] == pytest.approx(0.80)
    assert critique.result_payload["budgetSubcategory"] == "final_critique"
    assert critique.result_payload["budgetSubcategoryCapUsd"] == pytest.approx(0.55)

    inspection = task("composition")
    inspection.request_payload["input"]["materialInspection"] = {"assetId": "candidate"}
    reserve_test_request(db, inspection, 1)
    assert inspection.result_payload["budgetSubcategory"] == "material_inspection"
    assert inspection.result_payload["budgetSubcategoryCapUsd"] == pytest.approx(0.40)


def test_completed_planning_uses_measured_cost_while_uncertain_submission_keeps_reservation(monkeypatch):
    from types import SimpleNamespace

    from app.services.studios.gemini_editing import reserve_test_request

    settings = get_settings()
    monkeypatch.setattr(settings, "studio_editing_ai_test_budget_usd", 1)
    monkeypatch.setattr(settings, "studio_production_test_budget_usd", 1)
    monkeypatch.setattr("app.services.studios.contextual_editing.lock_editing_budget", lambda *args: None)
    jobs = []

    class Results:
        def all(self):
            return jobs

    db = SimpleNamespace(scalars=lambda query: Results())

    def task(*, status="queued", result=None):
        candidate = SimpleNamespace(
            workspace_id="workspace",
            correlation_id="pilot",
            provider="compatible.editing-planner",
            job_type="editing_ai",
            status=status,
            request_payload={
                "environment": "test",
                "input": {"operation": "plan", "productionStage": "direction"},
                "maxPromptChars": 100_000,
                "maxOutputTokens": 4096,
                "budgetAllocations": {
                    "planning": 0.40,
                    "image": 0.20,
                    "critique": 0.20,
                    "video": 0.0,
                    "reserve": 0.20,
                },
                "pricing": {
                    "inputUsdPerMillion": 2,
                    "outputUsdPerMillion": 8,
                    "imageReservationUsd": 0.10,
                },
            },
            result_payload=result or {},
        )
        jobs.append(candidate)
        return candidate

    # Three definitive responses consumed less than their conservative
    # reservations, leaving room for the separate composition call.
    for measured in (0.055688, 0.057494, 0.096554):
        task(
            status="succeeded",
            result={
                "testReservationUsd": 0.10,
                "budgetCategory": "planning",
                "submissionStarted": True,
                "submissionOutcome": "accepted",
                "measuredCostUsd": measured,
            },
        )
    composition = task()
    reserve_test_request(db, composition, 1)
    assert composition.result_payload["testReservationUsd"] == pytest.approx(0.1)

    # An uncertain provider submission keeps its full reservation and prevents
    # another call from exceeding the planning allocation.
    uncertain = task(
        status="failed",
        result={
            "testReservationUsd": 0.09,
            "budgetCategory": "planning",
            "submissionStarted": True,
            "submissionOutcome": "unknown",
        },
    )
    with pytest.raises(ValueError, match="test_budget_exceeded"):
        reserve_test_request(db, task(), 1)
    assert uncertain.result_payload["testReservationUsd"] == pytest.approx(0.09)


def test_local_prompt_preflight_rejection_releases_reservation(monkeypatch):
    from types import SimpleNamespace

    from app.services.studios.gemini_editing import reserve_test_request

    settings = get_settings()
    monkeypatch.setattr(settings, "studio_editing_ai_test_budget_usd", 0.2)
    monkeypatch.setattr(settings, "studio_production_test_budget_usd", 0.2)
    monkeypatch.setattr("app.services.studios.contextual_editing.lock_editing_budget", lambda *args: None)

    rejected = SimpleNamespace(
        workspace_id="workspace",
        correlation_id="pilot",
        status="retrying",
        request_payload={"environment": "test", "input": {"operation": "plan"}},
        result_payload={
            "testReservationUsd": 0.1,
            "budgetCategory": "planning",
            "submissionStarted": True,
            "submissionOutcome": "rejected",
            "preflightFailure": "editing_ai_prompt_too_large",
        },
    )
    current = SimpleNamespace(
        workspace_id="workspace",
        correlation_id="pilot",
        status="queued",
        provider="compatible.editing-planner",
        job_type="editing_ai",
        request_payload={
            "environment": "test",
            "input": {"operation": "plan"},
            "maxPromptChars": 1000,
            "maxOutputTokens": 256,
            "budgetAllocations": {"planning": 1, "image": 0, "critique": 0, "video": 0},
            "pricing": {"inputUsdPerMillion": 2, "outputUsdPerMillion": 8},
        },
        result_payload={},
    )

    class Results:
        @staticmethod
        def all():
            return [rejected, current]

    class DB:
        @staticmethod
        def scalars(*args, **kwargs):
            return Results()

    reserve_test_request(DB(), current, 1)
    assert current.result_payload["testReservationUsd"] == pytest.approx(0.1)


def test_retry_reuses_its_own_rejected_reservation(monkeypatch):
    from types import SimpleNamespace

    from app.services.studios.gemini_editing import reserve_test_request

    settings = get_settings()
    monkeypatch.setattr(settings, "studio_gemini_test_budget_usd", 0.15)
    monkeypatch.setattr(settings, "studio_production_test_budget_usd", 0.15)
    monkeypatch.setattr("app.services.studios.contextual_editing.lock_editing_budget", lambda *args: None)
    retrying = SimpleNamespace(
        workspace_id="workspace",
        correlation_id="pilot",
        provider="google.gemini-editing",
        job_type="editing_gemini",
        status="retrying",
        request_payload={
            "environment": "test",
            "input": {"operation": "plan", "productionStage": "direction"},
            "maxPromptChars": 1000,
            "maxOutputTokens": 256,
            "budgetAllocations": {"planning": 1, "image": 0, "critique": 0, "video": 0},
            "pricing": {"inputUsdPerMillion": 0.75, "outputUsdPerMillion": 3.75},
        },
        result_payload={
            "testReservationUsd": 0.1,
            "budgetCategory": "planning",
            "submissionStarted": True,
            "submissionOutcome": "rejected",
        },
    )

    class Results:
        @staticmethod
        def all():
            return [retrying]

    db = SimpleNamespace(scalars=lambda query: Results())
    reserve_test_request(db, retrying, 1)

    assert retrying.result_payload["testReservationUsd"] == pytest.approx(0.1)


def test_local_material_inspection_uses_bounded_reservation(monkeypatch):
    from types import SimpleNamespace

    from app.services.studios.gemini_editing import reserve_test_request

    settings = get_settings()
    monkeypatch.setattr(settings, "studio_editing_ai_test_budget_usd", 0.5)
    monkeypatch.setattr(settings, "studio_production_test_budget_usd", 0.5)
    monkeypatch.setattr("app.services.studios.contextual_editing.lock_editing_budget", lambda *args: None)

    job = SimpleNamespace(
        workspace_id="workspace",
        correlation_id="pilot",
        provider="compatible.editing-planner",
        job_type="editing_ai",
        status="queued",
        request_payload={
            "environment": "test",
            "input": {"operation": "plan", "materialInspection": {"assetId": "asset"}},
            "maxPromptChars": 24_000,
            "maxOutputTokens": 1024,
            "budgetAllocations": {
                "planning": 0.2,
                "image": 0.2,
                "critique": 0.4,
                "video": 0.0,
                "reserve": 0.2,
                "preRenderLimitUsd": 0.4,
            },
            "pricing": {
                "inputUsdPerMillion": 2,
                "outputUsdPerMillion": 8,
                "minimumReservationUsd": 0.035,
            },
        },
        result_payload={},
    )

    class Results:
        @staticmethod
        def all():
            return [job]

    db = SimpleNamespace(scalars=lambda query: Results())
    reserve_test_request(db, job, 1)
    assert job.result_payload["budgetCategory"] == "critique"
    assert job.result_payload["testReservationUsd"] == pytest.approx(0.035)


def test_truncated_local_revision_closes_only_after_executable_phases():
    from app.services.studios.gemini_editing import recover_truncated_local_revision_tail

    truncated = (
        '{"scenes":[{"id":"scene","elements":[{}],'
        '"compositions":[{}],"visualStates":[{"phase":"initial"},{"phase":"action"},'
        '{"phase":"consequence","purpose":"visible result'
    )

    recovered = recover_truncated_local_revision_tail(truncated, ["scene"])

    assert recovered is not None
    assert json.loads(recovered)["scenes"][0]["id"] == "scene"
    assert recover_truncated_local_revision_tail(truncated, ["other"]) is None


def test_truncated_local_revision_rejects_missing_consequence():
    from app.services.studios.gemini_editing import recover_truncated_local_revision_tail

    truncated = (
        '{"scenes":[{"id":"scene","elements":[{}],'
        '"compositions":[{}],"visualStates":[{"phase":"initial"},{"phase":"action"}'
    )

    assert recover_truncated_local_revision_tail(truncated, ["scene"]) is None


def test_one_dollar_envelope_requires_a_versioned_tariff(monkeypatch):
    from types import SimpleNamespace

    from app.services.studios.gemini_editing import reserve_test_request

    settings = get_settings()
    monkeypatch.setattr(settings, "studio_editing_ai_test_budget_usd", 1)
    monkeypatch.setattr(settings, "studio_production_test_budget_usd", 1)
    monkeypatch.setattr("app.services.studios.contextual_editing.lock_editing_budget", lambda *args: None)

    class Results:
        @staticmethod
        def all():
            return []

    job = SimpleNamespace(
        workspace_id="workspace",
        correlation_id="pilot",
        provider="compatible.editing-planner",
        job_type="editing_ai",
        request_payload={"environment": "test", "input": {"operation": "plan"}, "pricing": {}},
        result_payload={},
    )
    db = SimpleNamespace(scalars=lambda query: Results())
    with pytest.raises(ValueError, match="tariff_required"):
        reserve_test_request(db, job, 1)


def test_stale_document_blocks_before_external_post(client, project, monkeypatch):
    from app.models import CreativeDocument

    enable(monkeypatch)
    identifier = job(client, project)
    with SessionLocal() as db:
        document_record = db.get(CreativeDocument, project["document"])
        document_record.revision += 1
        db.commit()
        record = db.get(StudioGenerationJob, identifier)
        execute_job_once(db, record)
        assert "document_conflict" in record.error_message


def test_mask_scale_and_opacity_compose_on_late_overlay(tmp_path, media):
    raw = document().model_dump(mode="json", by_alias=True)
    picture, mask = tmp_path / "picture.png", tmp_path / "mask.png"
    Image.new("RGB", (100, 100), "red").save(picture)
    Image.new("L", (100, 100), 255).save(mask)
    raw["assets"] += [{"id": "picture", "mediaType": "image/png"}, {"id": "mask", "mediaType": "image/png"}]
    raw["composition"]["mediaTimeline"]["tracks"] += [
        {
            "id": "overlay",
            "kind": "overlay",
            "clips": [
                {
                    "id": "overlay-clip",
                    "assetId": "picture",
                    "timeline": {"startFrame": 5, "durationFrames": 40},
                    "transform": {"width": 100, "height": 100},
                    "keyframes": [
                        {
                            "trackId": prop,
                            "targetLayerId": "overlay-clip",
                            "property": prop,
                            "unit": "ratio",
                            "keyframes": [{"frame": 0, "value": 0.25, "easing": "ease_out"}, {"frame": 39, "value": 1}],
                        }
                        for prop in ["scale_x", "scale_y", "opacity"]
                    ],
                }
            ],
        },
        {"id": "mask-track", "kind": "mask", "targetTrackId": "overlay", "artifactAssetId": "mask"},
    ]
    doc = CreativeDocumentV1.model_validate(raw)
    output = tmp_path / "combined.mp4"
    ContextualFFmpegProvider("ffmpeg", 60).render(
        doc, request(doc), {**media, "picture": picture, "mask": mask}, output, lambda _: None, lambda: False
    )
    ffmpeg("-ss", "0.3", "-i", output, "-frames:v", "1", tmp_path / "early.png")
    ffmpeg("-ss", "1.6", "-i", output, "-frames:v", "1", tmp_path / "late.png")
    early = Image.open(tmp_path / "early.png").convert("RGB")
    late = Image.open(tmp_path / "late.png").convert("RGB")
    assert late.getpixel((70, 70))[0] > early.getpixel((70, 70))[0] + 100


def test_library_audio_is_planned_with_explicit_role(client, project, tmp_path):
    audio = tmp_path / "effect.wav"
    ffmpeg("-f", "lavfi", "-i", "sine=frequency=220:duration=3", audio)
    asset = upload(client, project, kind="music", data=audio.read_bytes()).json()["id"]
    response = client.post(
        f"/api/v1/studios/v1/documents/{project['document']}/editing-plans",
        headers=headers(project),
        json={
            "expectedDocumentRevision": 1,
            "intent": {"objective": "Criar atmosfera"},
            "beats": [
                {
                    "id": "scene",
                    "clipId": "clip",
                    "purpose": "Apoiar o clima da cena",
                    "audioAssetId": asset,
                    "audioRole": "music",
                }
            ],
        },
    )
    assert response.status_code == 200, response.text
    plan = response.json()
    assert plan["status"] == "ready", plan["blockers"]
    assert any(o["kind"] == "insert_audio" for o in plan["operations"])


def test_video_transformation_preserves_original_audio_and_neighboring_footage(client, project, tmp_path, monkeypatch):
    import numpy as np

    from app.models import CreativeDocument
    from app.services.object_storage import get_object_storage
    from app.services.studios.compatibility import persist_contract, record_to_contract

    enable(monkeypatch)
    original, generated = tmp_path / "long.mp4", tmp_path / "generated.mp4"
    for path, color, frequency, seconds in [(original, "blue", 440, 6), (generated, "red", 880, 3)]:
        ffmpeg(
            "-f",
            "lavfi",
            "-i",
            f"color={color}:s=320x320:r=25:d={seconds}",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency={frequency}:duration={seconds}:sample_rate=48000",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            path,
        )
    with SessionLocal() as db:
        asset = db.get(LibraryAsset, project["asset"])
        stored = get_object_storage().put_file(original, key=f"{project['workspace']}/long.mp4", media_type="video/mp4")
        asset.storage_key, asset.checksum_sha256 = stored.key, stored.checksum_sha256
        record = db.get(CreativeDocument, project["document"])
        contract = record_to_contract(record)
        contract.assets[0].checksum = stored.checksum_sha256
        timeline = contract.composition.media_timeline
        timeline.duration_frames = 150
        timeline.tracks[0].clips[0].timeline.duration_frames = 150
        timeline.tracks[0].clips[0].source.duration_microseconds = 6_000_000
        persist_contract(record, contract)
        db.commit()
    calls = []

    def generate(*args):
        calls.append(True)
        return {"id": "known-operation", "output_video": {"data": base64.b64encode(generated.read_bytes()).decode()}}

    monkeypatch.setattr(GeminiEditingProvider, "video", generate)
    identifier = job(
        client, project, operation="edit_video", sourceAssetId=project["asset"], sourceStartSeconds=1, durationSeconds=3
    )
    with SessionLocal() as db:
        task = db.get(StudioGenerationJob, identifier)
        assert execute_job_once(db, task) == "succeeded", task.error_message
        result = task.result_payload
        output_asset = db.get(LibraryAsset, result["assetId"])
        with get_object_storage().materialize(output_asset.storage_key) as output:
            ffmpeg("-i", output, "-vn", "-ac", "1", "-ar", "48000", "-f", "f32le", tmp_path / "audio.raw")
        samples = np.fromfile(tmp_path / "audio.raw", dtype=np.float32)[24000:72000]
        peak = np.fft.rfftfreq(len(samples), 1 / 48000)[np.argmax(abs(np.fft.rfft(samples)))]
        assert abs(peak - 440) < 2  # The generated 880Hz audio must never replace the source.
    base = f"/api/v1/studios/v1/documents/{project['document']}/editing-resources/apply"
    body = {"expectedDocumentRevision": 1, "assetId": result["assetId"], "targetClipId": "clip"}
    assert client.post(base, headers=headers(project), json=body).status_code == 422
    review = client.post(
        f"/api/v1/studios/v1/editing/resources/{result['assetId']}/review",
        headers=headers(project),
        json={"checksum": result["checksumSha256"], "result": "passed", "observation": "Reviewed test frames"},
    )
    assert review.status_code == 200, review.text
    applied = client.post(base, headers=headers(project), json=body)
    assert applied.status_code == 200, applied.text
    clips = applied.json()["composition"]["mediaTimeline"]["tracks"][0]["clips"]
    assert [c["assetId"] for c in clips] == [project["asset"], result["assetId"], project["asset"]]
    assert [c["timeline"] for c in clips] == [
        {"startFrame": 0, "durationFrames": 25},
        {"startFrame": 25, "durationFrames": 75},
        {"startFrame": 100, "durationFrames": 50},
    ]
    assert clips[2]["source"]["startMicroseconds"] == 4_000_000
    assert client.post(base, headers=headers(project), json=body).status_code == 409
    assert len(calls) == 1


@pytest.mark.parametrize("raises", [False, True])
def test_cancelled_submission_retains_outcome_on_retry(client, project, monkeypatch, raises):
    from app.services.studios import gemini_editing

    enable(monkeypatch)
    identifier = job(client, project)

    def cancelled(db, task, *_):
        task.status = "cancel_requested"
        task.result_payload = {"submissionStarted": True, "providerOperationId": "known-id"}
        db.commit()
        if raises:
            raise ValueError("cancelled_during_provider_operation")
        return {"submissionStarted": True, "providerOperationId": "known-id", "cancelled": True}

    monkeypatch.setattr(gemini_editing, "execute_editing_gemini", cancelled)
    with SessionLocal() as db:
        task = db.get(StudioGenerationJob, identifier)
        task.status = "cancel_requested"
        db.commit()
        # Simulate cancellation arriving during execution rather than before entry.
        task.status = "queued"
        db.commit()
        assert execute_job_once(db, task) == "cancelled"
        retry_job(db, task, task.requested_by)
        assert task.result_payload["providerOperationId"] == "known-id"
