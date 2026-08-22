from datetime import UTC, datetime

from conftest import register


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_structured_campaign_planner_and_connected_pieces_are_persistent_and_idempotent(client):
    token, workspace = register(client, "planner@example.com", "Restaurante Local")
    created = client.post(
        "/api/v1/campaigns",
        headers=auth(token),
        json={
            "workspaceId": workspace,
            "name": "Menu executivo",
            "objective": "Aumentar reservas no almoço",
            "products": "Menu executivo",
            "audience": "Profissionais que trabalham na região",
            "offer": "Reserva antecipada",
            "promise": "Almoçar bem dentro do horário disponível",
            "proof": "Cardápio e tempo de preparo informados pela equipe",
            "emotion": "tranquilidade",
            "constraints": "Não prometer tempo exato sem confirmação",
            "formats": ["post", "carousel", "ad", "script", "ugc-script"],
            "cta": "Reserve sua mesa",
            "channels": ["instagram", "facebook"],
            "funnel": "consideração",
            "brainRevision": 2,
            "status": "planned",
        },
    )
    assert created.status_code == 201, created.text
    campaign = created.json()
    assert campaign["bigIdea"]
    assert campaign["versions"][0]["number"] == 1
    assert len(campaign["angles"]) in range(3, 6)
    assert len(campaign["creativeMatrix"]) == 5
    assert campaign["creativeMatrix"][0]["cta"] == "Reserve sua mesa"

    pieces = client.post(f"/api/v1/campaigns/{campaign['id']}/pieces", headers=auth(token), json={})
    assert pieces.status_code == 200, pieces.text
    assert {piece["format"] for piece in pieces.json()} == {"post", "carousel", "ad", "script"}
    assert all(piece["campaignId"] == campaign["id"] for piece in pieces.json())
    assert next(piece for piece in pieces.json() if piece["format"] == "carousel")["slides"]

    repeated = client.post(f"/api/v1/campaigns/{campaign['id']}/pieces", headers=auth(token), json={})
    assert repeated.status_code == 200 and repeated.json() == []
    listed = client.get(f"/api/v1/posts?workspace_id={workspace}", headers=auth(token))
    assert listed.status_code == 200 and len(listed.json()) == 4

    updated = client.patch(
        f"/api/v1/campaigns/{campaign['id']}",
        headers=auth(token),
        json={"centralMessage": "Mensagem revisada e rastreável"},
    )
    assert updated.status_code == 200, updated.text
    assert len(updated.json()["versions"]) == 2
    decision = client.post(
        f"/api/v1/campaigns/{campaign['id']}/decisions",
        headers=auth(token),
        json={
            "decisionType": "approved",
            "summary": "Conceito aprovado internamente",
            "rationale": "Prova disponível no briefing",
        },
    )
    assert decision.status_code == 200, decision.text
    assert decision.json()["decisions"][0]["type"] == "approved"

    restored = client.post(f"/api/v1/campaigns/{campaign['id']}/versions/1/restore", headers=auth(token))
    assert restored.status_code == 200
    assert restored.json()["centralMessage"] == campaign["centralMessage"]
    assert len(restored.json()["versions"]) == 3

    history = client.get(
        "/api/v1/history",
        headers=auth(token),
        params={"workspace_id": workspace, "item_type": "campaign"},
    )
    assert history.status_code == 200
    assert history.json()[0]["decisionCount"] == 1
    reused = client.post(f"/api/v1/history/campaigns/{campaign['id']}/reuse", headers=auth(token), json={})
    assert reused.status_code == 201
    assert reused.json()["status"] == "draft"
    assert reused.json()["versions"][0]["label"] == "Reutilizada do histórico"


def test_opportunity_prefills_campaign_context_and_creates_connected_kit(client):
    token, workspace = register(client, "opportunity-kit@example.com", "Restaurante Local")
    headers = auth(token)
    profile = client.get("/api/v1/bootstrap", headers=headers).json()["workspaces"][0]["brandProfile"]
    profile.update(
        {
            "industry": "restaurante almoço executivo",
            "targetAudience": "profissionais que almoçam no centro",
            "keywords": ["restaurante", "almoço", "menu executivo", "reserva"],
            "products": [{"name": "Menu executivo", "description": "almoço com reserva"}],
            "pillars": ["gastronomia local", "almoço executivo"],
            "watchlist": {"brainRevision": 4, "brain": {"products": "Menu executivo"}},
        }
    )
    assert client.patch(
        f"/api/v1/workspaces/{workspace}", headers=headers, json={"brandProfile": profile}
    ).status_code == 200
    signal = client.post(
        "/api/v1/radar/signals",
        headers=headers,
        json={
            "workspaceId": workspace,
            "source": "Agenda local",
            "url": "https://example.com/agenda-local-almoco",
            "title": "Evento no centro aumenta procura por almoço executivo",
            "summary": "Profissionais procuram restaurante, menu executivo e reserva perto do trabalho.",
            "publishedAt": datetime.now(UTC).isoformat(),
            "topics": ["restaurante", "almoço executivo", "reserva"],
            "metrics": {"novelty_score": 75, "momentum_score": 55},
        },
    )
    assert signal.status_code == 201, signal.text
    ranked = client.post("/api/v1/radar/rank", headers=headers, json={"workspaceId": workspace})
    assert ranked.status_code == 200, ranked.text
    opportunity = ranked.json()[0]

    created = client.post(
        "/api/v1/campaigns",
        headers=headers,
        json={
            "workspaceId": workspace,
            "opportunityId": opportunity["id"],
            "name": "Campanha do evento local",
            "status": "planned",
        },
    )
    assert created.status_code == 201, created.text
    campaign = created.json()
    assert campaign["originContext"]["opportunityId"] == opportunity["id"]
    assert campaign["originContext"]["source"]["url"] == "https://example.com/agenda-local-almoco"
    assert campaign["originContext"]["event"] == opportunity["eventSummary"]
    assert campaign["originContext"]["connection"] == opportunity["bridge"]
    assert campaign["originContext"]["product"] == "Menu executivo"
    assert campaign["originContext"]["audience"] == "profissionais que almoçam no centro"
    assert campaign["hooks"][0] == opportunity["hook"]
    assert len(campaign["angles"]) == 3
    assert len(campaign["creativeMatrix"]) == 8
    assert campaign["formatSuggestions"] == ["stories", "reels"]

    pieces = client.post(f"/api/v1/campaigns/{campaign['id']}/pieces", headers=headers, json={})
    assert pieces.status_code == 200, pieces.text
    assert len(pieces.json()) == 8
    formats = [piece["format"] for piece in pieces.json()]
    assert formats.count("post") == 3
    assert formats.count("carousel") == 1
    assert formats.count("ad") == 2
    assert formats.count("script") == 2
    assert all(piece["campaignId"] == campaign["id"] for piece in pieces.json())
    repeated = client.post(f"/api/v1/campaigns/{campaign['id']}/pieces", headers=headers, json={})
    assert repeated.status_code == 200 and repeated.json() == []
