from datetime import UTC, datetime, timedelta

from conftest import register


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_content_versions_calendar_metrics_feedback_history_and_reuse(client):
    token, workspace = register(client, "history@example.com", "Marca Histórica")
    other_token, _ = register(client, "other-history@example.com", "Outra Marca")
    headers = auth(token)
    created = client.post(
        "/api/v1/posts",
        headers=headers,
        json={
            "workspaceId": workspace,
            "title": "Guia pesquisável",
            "platform": "instagram",
            "format": "post",
            "copy": "Texto editorial original",
            "author": "Editor",
            "origin": "manual",
        },
    )
    assert created.status_code == 201, created.text
    post_id = created.json()["id"]
    assert created.json()["versions"][0]["number"] == 1

    edited = client.patch(
        f"/api/v1/posts/{post_id}",
        headers=headers,
        json={"copy": "Texto editorial revisado"},
    )
    assert edited.status_code == 200
    assert len(edited.json()["versions"]) == 2
    assert edited.json()["versions"][-1]["copy"] == "Texto editorial revisado"

    invalid_schedule = client.patch(f"/api/v1/posts/{post_id}", headers=headers, json={"status": "scheduled"})
    assert invalid_schedule.status_code == 422
    publication_date = (datetime.now(UTC) + timedelta(days=2)).isoformat()
    scheduled = client.patch(
        f"/api/v1/posts/{post_id}",
        headers=headers,
        json={"status": "scheduled", "scheduledAt": publication_date},
    )
    assert scheduled.status_code == 200 and scheduled.json()["status"] == "scheduled"

    metrics = client.post(
        f"/api/v1/posts/{post_id}/metrics",
        headers=headers,
        json={"reach": 1200, "likes": 80, "comments": 9, "shares": 6, "saves": 14},
    )
    assert metrics.status_code == 201, metrics.text
    assert metrics.json()["source"] == "manual"
    assert metrics.json()["metrics"]["reach"] == 1200
    metric_history = client.get(f"/api/v1/posts/{post_id}/metrics", headers=headers)
    assert metric_history.status_code == 200 and len(metric_history.json()) == 1
    listed = client.get("/api/v1/posts", headers=headers, params={"workspace_id": workspace})
    assert listed.json()[0]["saves"] == 14

    rated = client.post(
        f"/api/v1/posts/{post_id}/feedback",
        headers=headers,
        json={"rating": 4, "reason": "Mensagem clara"},
    )
    assert rated.status_code == 204

    history = client.get(
        "/api/v1/history",
        headers=headers,
        params={"workspace_id": workspace, "query": "pesquisável", "item_type": "post"},
    )
    assert history.status_code == 200, history.text
    assert history.json()[0]["resourceId"] == post_id
    assert history.json()[0]["versionCount"] == 2

    reused = client.post(f"/api/v1/history/posts/{post_id}/reuse", headers=headers, json={})
    assert reused.status_code == 201, reused.text
    reused_id = reused.json()["id"]
    assert reused.json()["status"] == "draft" and reused.json()["scheduledAt"] is None
    assert reused.json()["copy"] == "Texto editorial revisado"
    assert "cópia" in reused.json()["title"]
    assert client.post(f"/api/v1/history/posts/{post_id}/reuse", headers=auth(other_token), json={}).status_code == 404

    restored = client.post(f"/api/v1/posts/{post_id}/versions/1/restore", headers=headers)
    assert restored.status_code == 200
    assert restored.json()["copy"] == "Texto editorial original"
    assert len(restored.json()["versions"]) == 3

    deleted = client.delete(f"/api/v1/posts/{reused_id}", headers=headers)
    assert deleted.status_code == 204
    remaining = client.get("/api/v1/history", headers=headers, params={"workspace_id": workspace, "item_type": "post"})
    assert remaining.status_code == 200
    assert all(item["resourceId"] != reused_id for item in remaining.json())


def test_explicit_opportunity_feedback_changes_workspace_preference_and_next_score(client):
    token, workspace = register(client, "preference@example.com", "Restaurante Preferência")
    headers = auth(token)
    profile = client.get("/api/v1/bootstrap", headers=headers).json()["workspaces"][0]["brandProfile"]
    profile.update(
        {
            "industry": "restaurante delivery",
            "targetAudience": "donos de restaurantes com delivery",
            "keywords": ["restaurante", "delivery", "pedidos"],
            "products": [{"name": "Cardápio delivery", "description": "pedidos digitais"}],
            "pillars": ["delivery", "gestão de restaurante"],
            "watchlist": {"topics": ["restaurante", "delivery"]},
        }
    )
    update = client.patch(f"/api/v1/workspaces/{workspace}", headers=headers, json={"brandProfile": profile})
    assert update.status_code == 200, update.text
    signal = client.post(
        "/api/v1/radar/signals",
        headers=headers,
        json={
            "workspaceId": workspace,
            "source": "Fonte controlada",
            "url": "https://example.com/preference-signal",
            "title": "Restaurante amplia pedidos por delivery",
            "summary": "Gestão de cardápio e pedidos digitais para delivery",
            "publishedAt": datetime.now(UTC).isoformat(),
            "topics": ["restaurante", "delivery", "pedidos"],
            "metrics": {"novelty_score": 70},
        },
    )
    assert signal.status_code == 201, signal.text
    ranked = client.post("/api/v1/radar/rank", headers=headers, json={"workspaceId": workspace})
    assert ranked.status_code == 200 and ranked.json()
    opportunity = ranked.json()[0]
    initial_score = opportunity["score"]

    feedback = client.post(
        "/api/v1/radar/feedback",
        headers=headers,
        json={
            "workspaceId": workspace,
            "opportunityId": opportunity["id"],
            "eventType": "rejected",
            "reason": "Não corresponde à preferência editorial atual",
        },
    )
    assert feedback.status_code == 204
    reranked = client.post("/api/v1/radar/rank", headers=headers, json={"workspaceId": workspace})
    assert reranked.status_code == 200
    assert reranked.json()[0]["score"] < initial_score
    assert reranked.json()[0]["scoreBreakdown"]["preference_events"] == 1

    preferences = client.get("/api/v1/radar/preferences", headers=headers, params={"workspace_id": workspace})
    assert preferences.status_code == 200, preferences.text
    assert preferences.json()["status"] == "explicit_feedback"
    assert preferences.json()["explicitEvents"] == 1
    assert any(value < 0 for value in preferences.json()["featureBias"].values())

    campaign = client.post(
        "/api/v1/campaigns",
        headers=headers,
        json={
            "workspaceId": workspace,
            "opportunityId": opportunity["id"],
            "name": "Campanha mensurável",
            "objective": "Comparar performance interna",
            "products": "Cardápio delivery",
            "audience": "Donos de restaurantes",
            "formats": ["post"],
            "status": "planned",
        },
    )
    assert campaign.status_code == 201, campaign.text
    for index, likes in enumerate((2, 8, 18)):
        post = client.post(
            "/api/v1/posts",
            headers=headers,
            json={
                "workspaceId": workspace,
                "title": f"Post medido {index}",
                "platform": "instagram",
                "format": "post",
                "copy": "Conteúdo medido",
                "author": "Editor",
                "campaignId": campaign.json()["id"],
                "strategyId": campaign.json()["id"],
                "origin": "strategy",
            },
        )
        assert post.status_code == 201, post.text
        metric = client.post(
            f"/api/v1/posts/{post.json()['id']}/metrics",
            headers=headers,
            json={"reach": 100, "likes": likes},
        )
        assert metric.status_code == 201, metric.text

    performance_profile = client.get("/api/v1/radar/preferences", headers=headers, params={"workspace_id": workspace})
    assert performance_profile.status_code == 200
    assert performance_profile.json()["performanceSamples"] == 3
    assert performance_profile.json()["performanceActive"] is True
    assert performance_profile.json()["status"] == "feedback_and_performance"
