"""Real ledger transactions and HTTP auth; never contacts a paid provider."""

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import SessionLocal
from app.models import StudioGenerationJob
from app.services.studios.external_policy import committed, reserve_monthly
from app.services.studios.jobs import execute_job_once, retry_job
from app.studio_app import app

KEY = "stage1-finance-test-key-only-" * 3


def auth(workspace="company", user="member", audience="clicko-finance", kind="external_finance"):
    now = datetime.now(UTC)
    return {"Authorization": "Bearer " + jwt.encode({
        "iss": "clicko-governance", "aud": audience, "type": kind, "sub": user, "workspaceId": workspace,
        "iat": now, "exp": now + timedelta(seconds=60),
    }, KEY, algorithm="HS256")}


def body(key="request-001", **extra):
    return {"provider": "google.klic", "model": "qa-model", "operation": "generate", "key": key,
            "fingerprint": "a" * 64, **extra}


@pytest.fixture
def gateway(monkeypatch):
    monkeypatch.setenv("CLICKO_STUDIOS_BRIDGE_SECRET", KEY)
    settings = get_settings()
    monkeypatch.setattr(settings, "studio_node_outbound_enabled", True)
    for name in ("studio_external_monthly_budget_usd", "studio_external_workspace_monthly_budget_usd",
                 "studio_external_user_monthly_budget_usd"):
        monkeypatch.setattr(settings, name, 1)
    monkeypatch.setattr(settings, "studio_external_model_monthly_budgets", {"qa-model": 1, "qa-voice": 1})
    monkeypatch.setattr(settings, "studio_node_tariffs", {
        "google.klic:qa-model": {"revision": "offline-test-not-a-commercial-price", "validUntil": "2099-01-01",
            "unit": "tokens", "inputUsdPerMillion": 1, "outputUsdPerMillion": 2,
            "maxInput": 100_000, "maxOutput": 10_000},
        "google.cloud-tts:qa-voice": {"revision": "offline-test", "validUntil": "2099-01-01",
            "unit": "characters", "inputUsdPerMillion": 10, "outputUsdPerMillion": 0,
            "maxInput": 10_000, "maxOutput": 1},
    })
    with TestClient(app) as client:
        yield client


def reserve(client, value=None, headers=None):
    result = client.post("/internal/finance/reserve", headers=headers or auth(), json=value or body())
    assert result.status_code == 200, result.text
    return result.json()


def test_bridge_and_browser_cannot_issue_financial_admissions(gateway):
    for headers in ({}, auth(audience="clicko-studios", kind="studio_bridge"), auth(kind="studio_bridge")):
        assert gateway.post("/internal/finance/reserve", headers=headers, json=body()).status_code == 401
    assert gateway.post("/internal/finance/reserve", headers=auth(), json=body(costUsd=0)).status_code == 422


def test_disabled_unpriced_zero_budget_and_expired_tariff_fail_closed(gateway, monkeypatch):
    settings = get_settings()
    for name, value in (("studio_node_outbound_enabled", False), ("studio_external_monthly_budget_usd", 0),
                        ("studio_external_model_monthly_budgets", {}), ("studio_node_tariffs", {})):
        with monkeypatch.context() as patch:
            patch.setattr(settings, name, value)
            assert gateway.post("/internal/finance/reserve", headers=auth(), json=body()).status_code == 403
    settings.studio_node_tariffs["google.klic:qa-model"]["validUntil"] = "2020-01-01"
    assert gateway.post("/internal/finance/reserve", headers=auth(), json=body()).status_code == 403


def test_replay_fingerprint_and_irreversible_submission_claim(gateway):
    first = reserve(gateway)
    assert first["reservedUsd"] == pytest.approx(0.12)
    assert reserve(gateway)["id"] == first["id"]
    conflict = gateway.post("/internal/finance/reserve", headers=auth(), json=body(fingerprint="b" * 64))
    assert conflict.status_code == 403
    route = "/internal/finance/" + first["id"]
    assert gateway.post(route + "/start", headers=auth(workspace="other")).status_code == 404
    assert gateway.post(route + "/start", headers=auth()).status_code == 200
    assert gateway.post(route + "/start", headers=auth()).status_code == 409
    assert gateway.post(route + "/settle", headers=auth(), json={
        "outcome": "completed", "input_tokens": 100, "output_tokens": 120,
    }).status_code == 200
    with SessionLocal() as db:
        job = db.get(StudioGenerationJob, first["id"])
        assert job.result_payload["estimatedCostUsd"] == pytest.approx(0.00034)
        assert job.result_payload["providerReportedCostUsd"] is None
        assert committed(job) == pytest.approx(0.12)
        assert job.attempts == 1
        for callback in (lambda: execute_job_once(db, job), lambda: retry_job(db, job, "actor")):
            with pytest.raises(ValueError, match="not_executable"):
                callback()


@pytest.mark.parametrize("limit", ["studio_external_monthly_budget_usd",
    "studio_external_workspace_monthly_budget_usd", "studio_external_user_monthly_budget_usd"])
def test_node_and_python_share_monthly_envelopes(gateway, monkeypatch, limit):
    first = reserve(gateway)
    monkeypatch.setattr(get_settings(), limit, 0.2)
    with SessionLocal() as db:
        original = db.get(StudioGenerationJob, first["id"])
        job = StudioGenerationJob(workspace_id=original.workspace_id, requested_by=original.requested_by,
            job_type="editing_ai", provider="google.gemini-editing", idempotency_key="python-request",
            payload_hash="a" * 64, correlation_id="python-request", request_payload=original.request_payload.copy())
        db.add(job)
        db.flush()
        with pytest.raises(ValueError, match="monthly_budget_exceeded"):
            reserve_monthly(db, job, 0.1, get_settings())
        db.rollback()


def test_per_model_limit_and_tts_character_reservation(gateway, monkeypatch):
    reserve(gateway)
    monkeypatch.setattr(get_settings(), "studio_external_model_monthly_budgets", {"qa-model": 0.2, "qa-voice": 1})
    assert gateway.post("/internal/finance/reserve", headers=auth(), json=body("request-002")).status_code == 403
    voice = reserve(gateway, body("voice-request", provider="google.cloud-tts", model="qa-voice",
                                operation="synthesize", units=500))
    assert voice["reservedUsd"] == pytest.approx(0.005)


def test_unknown_outcome_keeps_hold_and_service_restart_does_not_resubmit(gateway):
    first = reserve(gateway)
    route = "/internal/finance/" + first["id"]
    gateway.post(route + "/start", headers=auth())
    gateway.post(route + "/settle", headers=auth(), json={"outcome": "unknown"})
    from app.routers.studio_video import recover_interrupted_local_jobs

    recover_interrupted_local_jobs()
    assert reserve(gateway)["status"] == "failed"
    assert gateway.post(route + "/start", headers=auth()).status_code == 409
    with SessionLocal() as db:
        row = db.get(StudioGenerationJob, first["id"])
        assert committed(row) == pytest.approx(0.12)
        # A crash between marking a POST pending and receiving its ACK must not
        # reset the hold at the next monthly boundary, including historical rows.
        row.created_at = datetime.now(UTC) - timedelta(days=62)
        row.result_payload = {**row.result_payload, "financialPeriod": "2000-01", "submissionOutcome": "pending"}
        db.commit()
    get_settings().studio_external_user_monthly_budget_usd = 0.2
    assert gateway.post("/internal/finance/reserve", headers=auth(), json=body("after-month-boundary")).status_code == 403


def test_stale_or_repriced_reservation_cannot_start(gateway):
    first = reserve(gateway)
    get_settings().studio_node_tariffs["google.klic:qa-model"]["revision"] = "new-revision"
    assert gateway.post("/internal/finance/" + first["id"] + "/start", headers=auth()).status_code == 409
    second = reserve(gateway, body("request-after-reprice"))
    with SessionLocal() as db:
        row = db.get(StudioGenerationJob, second["id"])
        row.created_at = datetime.now(UTC) - timedelta(minutes=2)
        db.commit()
    assert gateway.post("/internal/finance/" + second["id"] + "/start", headers=auth()).status_code == 409


def test_only_one_concurrent_start_is_admitted(gateway):
    from concurrent.futures import ThreadPoolExecutor

    first = reserve(gateway)
    with ThreadPoolExecutor(max_workers=4) as pool:
        statuses = list(pool.map(lambda _: gateway.post(
            "/internal/finance/" + first["id"] + "/start", headers=auth()).status_code, range(4)))
    assert statuses.count(200) == 1
    assert statuses.count(409) == 3


def test_retirement_notice_is_explicit_and_never_auto_substitutes():
    from datetime import date

    from app.services.studios.model_lifecycle import lifecycle

    assert lifecycle("veo-3.1-fast-generate-preview", date(2026, 10, 21))["status"] == "retiring"
    assert lifecycle("veo-3.1-fast-generate-preview", date(2026, 10, 22))["status"] == "retired"
    assert lifecycle("sora-2-2025-12-08", date(2026, 10, 21))["status"] == "retired"
