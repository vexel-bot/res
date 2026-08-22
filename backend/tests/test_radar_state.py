from datetime import UTC, datetime, timedelta

from conftest import register


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def configure_restaurant(client, token: str, workspace: str) -> None:
    headers = auth(token)
    profile = client.get("/api/v1/bootstrap", headers=headers).json()["workspaces"][0]["brandProfile"]
    profile.update(
        {
            "industry": "restaurante almoço executivo delivery",
            "regions": ["BR", "São Paulo"],
            "tone": "claro e próximo",
            "targetAudience": "profissionais que procuram almoço executivo em São Paulo",
            "keywords": ["restaurante", "almoço", "menu executivo", "São Paulo"],
            "products": [{"name": "Menu executivo", "description": "almoço com reserva no centro"}],
            "pillars": ["almoço executivo", "gastronomia local", "reservas"],
            "prohibitedTopics": ["promessa garantida"],
            "watchlist": {
                "topics": ["restaurantes", "almoço", "eventos no centro"],
                "brainRevision": 2,
                "brain": {
                    "company": "Restaurante local no centro de São Paulo",
                    "products": "Menu executivo",
                    "services": "Reservas",
                    "visualIdentity": "fotografias reais e paleta verde",
                    "toneOfVoice": "claro e próximo",
                    "audience": "profissionais que almoçam no centro",
                    "personas": "pessoas com intervalo curto",
                    "objectives": "aumentar reservas",
                    "differentiators": "cardápio informado pela equipe",
                    "competitors": "restaurantes do centro",
                    "objections": "tempo de espera",
                    "pains": "pouco tempo para almoçar",
                    "desires": "comer bem perto do trabalho",
                    "faq": "cardápio, horário e reserva",
                    "forbiddenWords": "garantido",
                    "sourceFiles": [{"id": "photo", "type": "image", "name": "prato.jpg"}],
                },
            },
        }
    )
    response = client.patch(
        f"/api/v1/workspaces/{workspace}",
        headers=headers,
        json={"brandProfile": profile},
    )
    assert response.status_code == 200, response.text


def test_radar_state_is_honest_enriched_and_persists_save_and_rejection(client):
    token, workspace = register(client, "radar-state@example.com", "Restaurante Local")
    other_token, _ = register(client, "radar-state-other@example.com", "Clínica")
    headers = auth(token)
    configure_restaurant(client, token, workspace)

    empty = client.get("/api/v1/radar/state", headers=headers, params={"workspace_id": workspace})
    assert empty.status_code == 200, empty.text
    assert empty.json()["state"] == "no_sources"
    assert empty.json()["lastCollectionAt"] is None
    assert empty.json()["nextCollectionAt"] is None
    assert len(empty.json()["evergreenSuggestions"]) == 3
    assert all(suggestion["groundedIn"] for suggestion in empty.json()["evergreenSuggestions"])
    assert client.get(
        "/api/v1/radar/state",
        headers=auth(other_token),
        params={"workspace_id": workspace},
    ).status_code == 404

    signals = [
        (
            "Restaurantes de São Paulo ampliam reservas de almoço executivo",
            "Profissionais no centro procuram menu executivo e reserva para o almoço.",
        ),
        (
            "Almoço executivo ganha espaço entre profissionais com intervalo curto",
            "Restaurantes locais apresentam cardápio e opções de reserva em São Paulo.",
        ),
        (
            "Eventos no centro aumentam procura por restaurantes no horário do almoço",
            "Público busca menu executivo perto do trabalho e informações de reserva.",
        ),
    ]
    for index, (title, summary) in enumerate(signals):
        response = client.post(
            "/api/v1/radar/signals",
            headers=headers,
            json={
                "workspaceId": workspace,
                "source": f"Fonte pública {index + 1}",
                "url": f"https://example.com/radar-state-{index + 1}",
                "title": title,
                "summary": summary,
                "publishedAt": (datetime.now(UTC) - timedelta(minutes=index * 10)).isoformat(),
                "topics": ["restaurante", "almoço executivo", "reserva", "São Paulo"],
                "metrics": {"novelty_score": 70, "momentum_score": 40},
            },
        )
        assert response.status_code == 201, response.text

    ranked = client.post("/api/v1/radar/rank", headers=headers, json={"workspaceId": workspace})
    assert ranked.status_code == 200, ranked.text
    assert len(ranked.json()) == 3
    state = client.get("/api/v1/radar/state", headers=headers, params={"workspace_id": workspace})
    assert state.status_code == 200, state.text
    assert state.json()["state"] == "ready"
    assert len(state.json()["opportunities"]) == 3
    first = state.json()["opportunities"][0]
    assert first["source"]["url"].startswith("https://example.com/")
    assert first["source"]["publishedAt"]
    assert first["whyItFits"] == first["bridge"]
    assert first["relatedContext"]["audience"]
    assert first["relatedContext"]["product"] == "Menu executivo"
    assert first["scoreLabel"]
    assert first["windowLabel"]
    assert first["actions"]["canCreateCampaign"] is True

    saved = client.post(
        "/api/v1/radar/feedback",
        headers=headers,
        json={"workspaceId": workspace, "opportunityId": first["id"], "eventType": "saved"},
    )
    assert saved.status_code == 204
    saved_state = client.get("/api/v1/radar/state", headers=headers, params={"workspace_id": workspace})
    saved_item = next(item for item in saved_state.json()["opportunities"] if item["id"] == first["id"])
    assert saved_item["saved"] is True
    assert saved_item["actions"]["canSave"] is False

    rejected = client.post(
        "/api/v1/radar/feedback",
        headers=headers,
        json={
            "workspaceId": workspace,
            "opportunityId": first["id"],
            "eventType": "rejected",
            "reason": "Não combina com a agenda editorial atual",
        },
    )
    assert rejected.status_code == 204
    after_rejection = client.get("/api/v1/radar/state", headers=headers, params={"workspace_id": workspace})
    assert all(item["id"] != first["id"] for item in after_rejection.json()["opportunities"])
