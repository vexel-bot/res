from datetime import UTC, datetime, timedelta

from conftest import register


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_analytics_summary_uses_only_observed_or_user_reported_evidence(client):
    token, workspace = register(client, "analytics-summary@example.com", "Restaurante Local")
    other_token, _ = register(client, "analytics-summary-other@example.com", "Clínica")
    headers = auth(token)

    initial = client.get("/api/v1/analytics/summary", headers=headers, params={"workspace_id": workspace})
    assert initial.status_code == 200, initial.text
    assert initial.json()["insights"][0]["evidenceType"] == "insufficient_data"
    assert client.get(
        "/api/v1/analytics/summary",
        headers=auth(other_token),
        params={"workspace_id": workspace},
    ).status_code == 404

    profile = client.get("/api/v1/bootstrap", headers=headers).json()["workspaces"][0]["brandProfile"]
    profile.update(
        {
            "industry": "restaurante almoço executivo",
            "regions": ["BR", "São Paulo"],
            "tone": "claro",
            "targetAudience": "profissionais que almoçam no centro",
            "keywords": ["restaurante", "almoço", "menu executivo"],
            "products": [{"name": "Menu executivo", "description": "almoço com reserva"}],
            "pillars": ["almoço executivo", "gastronomia local"],
            "prohibitedTopics": ["promessa garantida"],
            "watchlist": {
                "topics": ["restaurantes", "eventos locais"],
                "brain": {
                    "company": "Restaurante no centro",
                    "products": "Menu executivo",
                    "services": "Reserva",
                    "visualIdentity": "fotos reais e paleta verde",
                    "toneOfVoice": "claro",
                    "audience": "profissionais do centro",
                    "personas": "pessoas com intervalo curto",
                    "objectives": "reservas",
                    "differentiators": "cardápio informado",
                    "competitors": "restaurantes locais",
                    "objections": "demora",
                    "pains": "pouco tempo",
                    "desires": "almoçar bem",
                    "faq": "horário e reserva",
                    "forbiddenWords": "garantido",
                    "sourceFiles": [{"id": "photo", "type": "image"}],
                },
            },
        }
    )
    updated = client.patch(
        f"/api/v1/workspaces/{workspace}", headers=headers, json={"brandProfile": profile}
    )
    assert updated.status_code == 200, updated.text

    opportunity_ids = []
    for index in range(2):
        signal = client.post(
            "/api/v1/radar/signals",
            headers=headers,
            json={
                "workspaceId": workspace,
                "source": f"Fonte {index}",
                "url": f"https://example.com/analytics-{index}",
                "title": f"Restaurante e menu executivo atraem profissionais no almoço {index}",
                "summary": "Reserva e almoço executivo para profissionais no centro.",
                "publishedAt": (datetime.now(UTC) - timedelta(minutes=index)).isoformat(),
                "topics": ["restaurante", "almoço executivo", "reserva"],
            },
        )
        assert signal.status_code == 201, signal.text
    ranked = client.post("/api/v1/radar/rank", headers=headers, json={"workspaceId": workspace})
    assert ranked.status_code == 200, ranked.text
    opportunity_ids = [item["id"] for item in ranked.json()]
    for opportunity_id in opportunity_ids:
        assert client.post(
            "/api/v1/radar/feedback",
            headers=headers,
            json={"workspaceId": workspace, "opportunityId": opportunity_id, "eventType": "shown"},
        ).status_code == 204

    campaign = client.post(
        "/api/v1/campaigns",
        headers=headers,
        json={
            "workspaceId": workspace,
            "opportunityId": opportunity_ids[0],
            "name": "Campanha conectada",
            "status": "planned",
        },
    )
    assert campaign.status_code == 201, campaign.text
    pieces = client.post(f"/api/v1/campaigns/{campaign.json()['id']}/pieces", headers=headers, json={})
    assert pieces.status_code == 200 and len(pieces.json()) == 8
    post = pieces.json()[0]
    assert client.patch(
        f"/api/v1/posts/{post['id']}", headers=headers, json={"copy": f"{post['copy']}\nEdição real"}
    ).status_code == 200
    assert client.post(
        f"/api/v1/posts/{post['id']}/metrics",
        headers=headers,
        json={"reach": 100, "likes": 10, "comments": 3, "shares": 2, "saves": 5},
    ).status_code == 201
    assert client.post(
        "/api/v1/radar/feedback",
        headers=headers,
        json={
            "workspaceId": workspace,
            "opportunityId": opportunity_ids[1],
            "eventType": "rejected",
            "reason": "Tema fora da agenda editorial",
        },
    ).status_code == 204
    assert client.post(
        f"/api/v1/history/campaigns/{campaign.json()['id']}/reuse",
        headers=headers,
        json={},
    ).status_code == 201

    summary = client.get("/api/v1/analytics/summary", headers=headers, params={"workspace_id": workspace})
    assert summary.status_code == 200, summary.text
    data = summary.json()
    metrics = {item["key"]: item for item in data["metrics"]}
    assert metrics["time_to_complete_brand"]["status"] == "available"
    assert metrics["opportunity_selection_rate"]["value"] == 50.0
    assert metrics["opportunity_to_campaign_rate"]["value"] == 50.0
    assert metrics["opportunities_rejected"]["value"] == 1
    assert metrics["campaigns_reused"]["value"] == 1
    assert metrics["useful_opportunity_campaigns_per_week"]["value"] > 0
    assert data["rejectionReasons"] == [{"reason": "Tema fora da agenda editorial", "count": 1}]
    assert {insight["evidenceType"] for insight in data["insights"]} <= {"observed", "user_reported"}
    assert any(insight["key"] == "best_measured_format" for insight in data["insights"])
