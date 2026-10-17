from datetime import UTC, datetime, timedelta

import pytest
from conftest import register
from fastapi.testclient import TestClient

from app.connectors.base import NormalizedSignal
from app.connectors.rss import plain_text, validate_public_http_url
from app.database import SessionLocal
from app.models import ExternalSignal, JobAudit, RadarSource
from app.routers import radar as radar_router
from app.tasks import sync_workspace_sources


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_rss_url_validation_blocks_private_networks(monkeypatch):
    monkeypatch.setattr(
        "app.connectors.rss.socket.getaddrinfo",
        lambda *_args, **_kwargs: [(2, 1, 6, "", ("93.184.216.34", 443))],
    )
    validate_public_http_url("https://example.com/feed.xml")
    assert plain_text("<p>Texto <strong>limpo</strong></p>") == "Texto limpo"

    monkeypatch.setattr(
        "app.connectors.rss.socket.getaddrinfo",
        lambda *_args, **_kwargs: [(2, 1, 6, "", ("127.0.0.1", 80))],
    )
    with pytest.raises(ValueError, match="public addresses"):
        validate_public_http_url("http://localhost/feed")
    with pytest.raises(ValueError, match="port 80 or 443"):
        validate_public_http_url("http://example.com:8080/feed")


def test_radar_source_crud_sync_job_and_tenant_isolation(client: TestClient, monkeypatch):
    monkeypatch.setattr("app.connectors.rss.validate_public_http_url", lambda _url: None)
    monkeypatch.setattr(radar_router.sync_workspace_sources, "delay", lambda *_args: None)
    token, workspace = register(client, "radar-source@example.com")
    other_token, _ = register(client, "radar-source-other@example.com")
    payload = {
        "workspaceId": workspace,
        "name": "Portal do setor",
        "feedUrl": "https://news.example.com/feed.xml",
        "category": "negócios",
    }
    created = client.post("/api/v1/radar/sources", headers=auth(token), json=payload)
    assert created.status_code == 201, created.text
    source_id = created.json()["id"]
    assert created.json()["lastStatus"] == "never"
    assert client.post("/api/v1/radar/sources", headers=auth(token), json=payload).status_code == 409
    assert client.get(f"/api/v1/radar/sources?workspace_id={workspace}", headers=auth(other_token)).status_code == 404

    updated = client.patch(f"/api/v1/radar/sources/{source_id}", headers=auth(token), json={"isActive": False})
    assert updated.status_code == 200 and updated.json()["isActive"] is False
    job_headers = {**auth(token), "Idempotency-Key": "radar-source-sync-test-001"}
    job = client.post("/api/v1/radar/sync/jobs", headers=job_headers, json={"workspaceId": workspace})
    duplicate_job = client.post("/api/v1/radar/sync/jobs", headers=job_headers, json={"workspaceId": workspace})
    assert job.status_code == 202 and duplicate_job.json()["id"] == job.json()["id"]
    assert client.delete(f"/api/v1/radar/sources/{source_id}", headers=auth(token)).status_code == 204


def test_signal_deduplication_is_tenant_aware_and_similar_titles_cluster(client: TestClient):
    token, workspace = register(client, "radar-cluster@example.com")
    other_token, other_workspace = register(client, "radar-cluster-other@example.com")
    now = datetime.now(UTC)

    def payload(workspace_id: str, title: str, url: str) -> dict:
        return {
            "workspaceId": workspace_id,
            "source": "Portal público",
            "url": url,
            "title": title,
            "summary": "Restaurantes observam aumento de pedidos e adoção de cardápio digital.",
            "publishedAt": now.isoformat(),
            "expiresAt": (now + timedelta(days=3)).isoformat(),
        }

    first = client.post(
        "/api/v1/radar/signals",
        headers=auth(token),
        json=payload(
            workspace,
            "Restaurantes locais ampliam pedidos delivery com cardápio digital",
            "https://example.com/noticia-1",
        ),
    )
    second = client.post(
        "/api/v1/radar/signals",
        headers=auth(token),
        json=payload(
            workspace,
            "Restaurantes locais ampliam pedidos delivery usando cardápio digital",
            "https://example.com/noticia-2",
        ),
    )
    same_other_tenant = client.post(
        "/api/v1/radar/signals",
        headers=auth(other_token),
        json=payload(
            other_workspace,
            "Restaurantes locais ampliam pedidos delivery com cardápio digital",
            "https://example.com/noticia-1",
        ),
    )
    assert first.status_code == second.status_code == same_other_tenant.status_code == 201
    assert first.json()["clusterKey"] == second.json()["clusterKey"]
    assert first.json()["topics"]
    assert first.json()["entities"]


def test_source_sync_task_is_audited_and_idempotent(client: TestClient, monkeypatch):
    _, workspace = register(client, "radar-sync-task@example.com")

    class FakeConnector:
        def __init__(self, *_args):
            pass

        def collect(self):
            now = datetime.now(UTC)
            return [
                NormalizedSignal(
                    source="Feed de teste",
                    url="https://example.com/sinal-task",
                    title="Restaurantes adotam cardápio digital para novos pedidos",
                    summary="Sinal coletado por um conector controlado no teste.",
                    raw_text="Sinal coletado por um conector controlado no teste.",
                    published_at=now,
                    expires_at=now + timedelta(days=3),
                )
            ]

    monkeypatch.setattr("app.tasks.RSSConnector", FakeConnector)
    with SessionLocal() as db:
        db.add(
            RadarSource(
                workspace_id=workspace,
                name="Feed de teste",
                feed_url="https://example.com/feed.xml",
            )
        )
        db.commit()

    key = "radar-sync-task-idempotency-001"
    first = sync_workspace_sources.apply(args=[workspace, key])
    second = sync_workspace_sources.apply(args=[workspace, key])
    assert first.successful() and first.result["created"] == 1
    assert second.successful() and second.result["status"] == "already-completed"
    with SessionLocal() as db:
        source = db.query(RadarSource).filter_by(workspace_id=workspace).one()
        audit = db.query(JobAudit).filter_by(idempotency_key=key).one()
        assert source.last_status == "ok" and source.last_item_count == 1
        assert audit.status == "completed" and audit.attempts == 1
        assert db.query(ExternalSignal).filter_by(workspace_id=workspace).count() == 1
