from datetime import UTC, datetime, timedelta

from conftest import register
from sqlalchemy import delete, select

from app.database import SessionLocal
from app.models import BrandProfile, JobAudit
from app.routers import assets as assets_router
from app.routers import radar as radar_router
from app.tasks import rank_workspace as rank_workspace_task


def test_authenticated_user_can_change_password(client):
    token, _ = register(client, "password-change@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    wrong = client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"currentPassword": "senha-incorreta", "newPassword": "nova-senha-segura-456"},
    )
    assert wrong.status_code == 400

    changed = client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"currentPassword": "senha-segura-123", "newPassword": "nova-senha-segura-456"},
    )
    assert changed.status_code == 204

    old_login = client.post(
        "/api/v1/auth/login",
        json={"email": "password-change@example.com", "password": "senha-segura-123"},
    )
    assert old_login.status_code == 401
    new_login = client.post(
        "/api/v1/auth/login",
        json={"email": "password-change@example.com", "password": "nova-senha-segura-456"},
    )
    assert new_login.status_code == 200


def test_authenticated_user_can_update_profile(client):
    token, _ = register(client, "profile-update@example.com")
    register(client, "profile-existing@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    updated = client.patch(
        "/api/v1/auth/me",
        headers=headers,
        json={"name": "Perfil Atualizado", "email": "profile-new@example.com"},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["name"] == "Perfil Atualizado"
    assert updated.json()["email"] == "profile-new@example.com"

    duplicate = client.patch(
        "/api/v1/auth/me",
        headers=headers,
        json={"name": "Perfil Atualizado", "email": "profile-existing@example.com"},
    )
    assert duplicate.status_code == 409

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "profile-new@example.com", "password": "senha-segura-123"},
    )
    assert login.status_code == 200


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_registration_login_and_workspace_isolation(client):
    first_token, first_workspace = register(client, "primeiro@example.com", "Primeira Marca")
    second_token, _ = register(client, "segundo@example.com", "Segunda Marca")
    created = client.post(
        "/api/v1/posts",
        headers=auth(first_token),
        json={
            "workspaceId": first_workspace,
            "title": "Post persistido",
            "platform": "instagram",
            "format": "post",
            "copy": "Conteúdo real",
            "status": "draft",
            "author": "Usuário Teste",
        },
    )
    assert created.status_code == 201, created.text
    own = client.get(f"/api/v1/posts?workspace_id={first_workspace}", headers=auth(first_token))
    assert own.status_code == 200 and own.json()[0]["title"] == "Post persistido"
    isolated = client.get(f"/api/v1/posts?workspace_id={first_workspace}", headers=auth(second_token))
    assert isolated.status_code == 404
    login = client.post("/api/v1/auth/login", json={"email": "primeiro@example.com", "password": "senha-segura-123"})
    assert login.status_code == 200 and login.json()["accessToken"]

    past_schedule = client.post(
        "/api/v1/posts",
        headers=auth(first_token),
        json={
            "workspaceId": first_workspace,
            "title": "Agendamento inválido",
            "platform": "instagram",
            "format": "post",
            "status": "scheduled",
            "scheduledAt": (datetime.now(UTC) - timedelta(minutes=5)).isoformat(),
        },
    )
    assert past_schedule.status_code == 422


def test_signal_deduplication_ranking_and_evidence(client):
    token, workspace = register(client, "radar@example.com", "Food Tech")
    update = client.patch(
        f"/api/v1/workspaces/{workspace}",
        headers=auth(token),
        json={
            "brandProfile": {
                "name": "Food Tech",
                "industry": "tecnologia para restaurantes",
                "regions": ["BR"],
                "languages": ["pt-BR"],
                "tone": "Direto",
                "targetAudience": "donos de restaurantes que querem mais pedidos por delivery",
                "keywords": ["restaurantes", "delivery", "cardápio digital"],
                "doAndDonts": "",
                "primaryColor": "#6366f1",
                "products": [{"name": "Cardápio digital", "description": "mais pedidos por delivery"}],
                "pillars": ["gestão de restaurantes", "vendas por delivery"],
                "watchlist": {"nicho": ["restaurantes", "delivery"]},
                "prohibitedTopics": [],
            }
        },
    )
    assert update.status_code == 200, update.text
    signal = {
        "workspaceId": workspace,
        "source": "Portal Restaurante",
        "url": "https://example.com/noticia-delivery",
        "title": "Restaurantes locais ampliam pedidos por delivery",
        "summary": "Cardápio digital ajuda donos de restaurantes a vender mais por delivery.",
        "publishedAt": (datetime.now(UTC) - timedelta(hours=1)).isoformat(),
        "topics": ["restaurantes", "delivery", "cardápio digital"],
        "metrics": {"momentum_score": 65, "novelty_score": 70},
    }
    first = client.post("/api/v1/radar/signals", headers=auth(token), json=signal)
    assert first.status_code == 201, first.text
    duplicate = client.post("/api/v1/radar/signals", headers=auth(token), json=signal)
    assert duplicate.status_code == 409
    ranked = client.post("/api/v1/radar/rank", headers=auth(token), json={"workspaceId": workspace})
    assert ranked.status_code == 200, ranked.text
    result = ranked.json()[0]
    assert result["scoreVersion"] == "radar-v1.1"
    assert result["evidence"][0]["url"] == signal["url"]
    assert result["eligible"] is True
    top = client.get(f"/api/v1/radar/opportunities?workspace_id={workspace}", headers=auth(token))
    assert top.status_code == 200 and len(top.json()) == 1


def test_health_and_unconfigured_ai_are_honest(client):
    token, _ = register(client, "health@example.com")
    assert client.get("/health/live").json() == {"status": "ok"}
    assert client.get("/health/ready").status_code == 200
    ai = client.post("/api/ai/chat", headers=auth(token), json={"message": "oi"})
    assert ai.status_code == 503


def test_campaign_asset_and_post_updates_are_persistent_and_isolated(client):
    token, workspace = register(client, "operations@example.com", "Marca Operacional")
    other_token, other_workspace = register(client, "intruso@example.com", "Outra Marca")

    campaign = client.post(
        "/api/v1/campaigns",
        headers=auth(token),
        json={
            "workspaceId": workspace,
            "name": "Campanha persistida",
            "objective": "Gerar demanda qualificada",
            "channels": ["linkedin"],
            "executionPlan": ["Publicar manifesto"],
            "status": "planned",
            "brainRevision": 2,
        },
    )
    assert campaign.status_code == 201, campaign.text
    campaign_id = campaign.json()["id"]
    listed = client.get(f"/api/v1/campaigns?workspace_id={workspace}", headers=auth(token))
    assert listed.status_code == 200 and listed.json()[0]["id"] == campaign_id
    assert client.get(f"/api/v1/campaigns?workspace_id={workspace}", headers=auth(other_token)).status_code == 404

    asset = client.post(
        "/api/v1/assets",
        headers=auth(token),
        json={"workspaceId": workspace, "title": "Guia da marca", "type": "document", "tags": ["brain"]},
    )
    assert asset.status_code == 201, asset.text
    assets = client.get(f"/api/v1/assets?workspace_id={workspace}", headers=auth(token))
    assert assets.status_code == 200 and assets.json()[0]["title"] == "Guia da marca"

    post = client.post(
        "/api/v1/posts",
        headers=auth(token),
        json={
            "workspaceId": workspace,
            "title": "Conteúdo em revisão",
            "platform": "linkedin",
            "format": "post",
            "status": "draft",
            "author": "Operações",
            "campaignId": campaign_id,
            "strategyId": campaign_id,
            "brainRevision": 2,
            "origin": "strategy",
        },
    )
    assert post.status_code == 201, post.text
    assert post.json()["campaignId"] == campaign_id and post.json()["brainRevision"] == 2
    post_id = post.json()["id"]
    updated = client.patch(f"/api/v1/posts/{post_id}", headers=auth(token), json={"status": "pending_approval"})
    assert updated.status_code == 200 and updated.json()["status"] == "pending_approval"
    assert (
        client.patch(f"/api/v1/posts/{post_id}", headers=auth(other_token), json={"status": "published"}).status_code
        == 404
    )
    foreign_link = client.post(
        "/api/v1/posts",
        headers=auth(other_token),
        json={
            "workspaceId": other_workspace,
            "title": "Ligação inválida",
            "platform": "linkedin",
            "format": "post",
            "author": "Intruso",
            "campaignId": campaign_id,
        },
    )
    assert foreign_link.status_code == 422

    bootstrap = client.get("/api/v1/bootstrap", headers=auth(token)).json()
    assert bootstrap["workspaces"][0]["role"] == "Owner"
    assert bootstrap["posts"][0]["origin"] == "strategy"


def test_private_upload_enforces_access_type_and_size(client, tmp_path, monkeypatch):
    monkeypatch.setattr(assets_router.settings, "storage_path", str(tmp_path))
    token, workspace = register(client, "upload@example.com", "Marca com Arquivos")
    other_token, _ = register(client, "upload-other@example.com", "Marca Isolada")

    uploaded = client.post(
        "/api/v1/assets/upload",
        headers=auth(token),
        data={"workspace_id": workspace, "title": "Guia privado", "tags": "brain,manual"},
        files={"file": ("guia.txt", b"conteudo privado", "text/plain")},
    )
    assert uploaded.status_code == 201, uploaded.text
    asset_id = uploaded.json()["id"]
    content = client.get(f"/api/v1/assets/{asset_id}/content", headers=auth(token))
    assert content.status_code == 200 and content.content == b"conteudo privado"
    assert client.get(f"/api/v1/assets/{asset_id}/content", headers=auth(other_token)).status_code == 404

    unsupported = client.post(
        "/api/v1/assets/upload",
        headers=auth(token),
        data={"workspace_id": workspace, "title": "Executável"},
        files={"file": ("payload.exe", b"MZ", "application/octet-stream")},
    )
    assert unsupported.status_code == 415

    spoofed = client.post(
        "/api/v1/assets/upload",
        headers=auth(token),
        data={"workspace_id": workspace, "title": "Imagem falsa"},
        files={"file": ("falsa.png", b"not-a-png", "image/png")},
    )
    assert spoofed.status_code == 422

    video_bytes = b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isomiso2"
    video = client.post(
        "/api/v1/assets/upload",
        headers=auth(token),
        data={"workspace_id": workspace, "title": "Vídeo real"},
        files={"file": ("video.mp4", video_bytes, "video/mp4")},
    )
    assert video.status_code == 201, video.text
    video_id = video.json()["id"]
    assert client.get(f"/api/v1/assets/{video_id}/content", headers=auth(token)).content == video_bytes

    monkeypatch.setattr(assets_router, "MAX_UPLOAD_BYTES", 4)
    oversized = client.post(
        "/api/v1/assets/upload",
        headers=auth(token),
        data={"workspace_id": workspace, "title": "Grande demais"},
        files={"file": ("grande.txt", b"cinco", "text/plain")},
    )
    assert oversized.status_code == 413
    assert client.delete(f"/api/v1/assets/{asset_id}", headers=auth(token)).status_code == 204
    assert client.delete(f"/api/v1/assets/{video_id}", headers=auth(token)).status_code == 204
    assert list(tmp_path.iterdir()) == []


def test_async_job_api_and_task_idempotency(client, monkeypatch):
    token, workspace = register(client, "jobs@example.com", "Marca com Jobs")
    other_token, _ = register(client, "jobs-other@example.com", "Outra Marca")
    queued = []
    monkeypatch.setattr(radar_router.rank_workspace, "delay", lambda *args: queued.append(args))

    response = client.post(
        "/api/v1/radar/rank/jobs",
        headers={**auth(token), "Idempotency-Key": "rank-jobs-example-001"},
        json={"workspaceId": workspace},
    )
    assert response.status_code == 202, response.text
    job_id = response.json()["id"]
    assert response.json()["status"] == "queued"
    assert queued == [(workspace, "rank-jobs-example-001")]

    duplicate = client.post(
        "/api/v1/radar/rank/jobs",
        headers={**auth(token), "Idempotency-Key": "rank-jobs-example-001"},
        json={"workspaceId": workspace},
    )
    assert duplicate.status_code == 202 and len(queued) == 1
    assert client.get(f"/api/v1/jobs/{job_id}", headers=auth(other_token)).status_code == 404

    first = rank_workspace_task.apply(args=[workspace, "rank-jobs-example-001"])
    assert first.successful() and first.get()["created"] == 0
    second = rank_workspace_task.apply(args=[workspace, "rank-jobs-example-001"])
    assert second.successful() and second.get() == {"status": "already-completed"}
    completed = client.get(f"/api/v1/jobs/{job_id}", headers=auth(token))
    assert completed.status_code == 200 and completed.json()["status"] == "completed"


def test_non_retryable_task_failure_is_audited(client):
    _, workspace = register(client, "jobs-failure@example.com", "Marca Incompleta")
    with SessionLocal() as db:
        db.execute(delete(BrandProfile).where(BrandProfile.workspace_id == workspace))
        db.commit()
    result = rank_workspace_task.apply(args=[workspace, "rank-jobs-failure-001"])
    assert result.failed()
    with SessionLocal() as db:
        audit = db.scalar(select(JobAudit).where(JobAudit.idempotency_key == "rank-jobs-failure-001"))
        assert audit and audit.status == "failed" and audit.finished_at is not None
        assert audit.error.startswith("ValueError: Brand profile not found")
