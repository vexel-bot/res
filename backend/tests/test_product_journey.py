from datetime import UTC, datetime
from io import BytesIO

from conftest import register
from PIL import Image


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def configure_brand(
    client,
    token: str,
    workspace: str,
    *,
    industry: str,
    product: str,
    audience: str,
    pillars: list[str],
    prohibited: list[str],
) -> None:
    headers = auth(token)
    profile = client.get("/api/v1/bootstrap", headers=headers).json()["workspaces"][0]["brandProfile"]
    profile.update(
        {
            "industry": industry,
            "regions": ["BR"],
            "tone": "claro, humano e responsável",
            "targetAudience": audience,
            "keywords": [industry, product, *pillars],
            "products": [{"name": product, "description": f"Oferta real de {product}"}],
            "pillars": pillars,
            "prohibitedTopics": prohibited,
            "watchlist": {
                "topics": pillars,
                "players": [f"referências de {industry}"],
                "brainRevision": 2,
                "brain": {
                    "company": f"Marca do segmento {industry} com atuação no Brasil",
                    "products": product,
                    "services": product,
                    "visualIdentity": "fotografias reais, logo e paleta cadastrada",
                    "toneOfVoice": "claro, humano e responsável",
                    "audience": audience,
                    "personas": audience,
                    "objectives": f"gerar demanda qualificada para {product}",
                    "differentiators": "experiência real e comunicação verificável",
                    "competitors": f"players de {industry}",
                    "objections": "dúvidas antes da decisão",
                    "pains": "falta de informação confiável",
                    "desires": "tomar uma decisão segura",
                    "faq": f"perguntas frequentes sobre {product}",
                    "forbiddenWords": "garantido, milagroso",
                    "sourceFiles": [{"id": f"asset-{workspace}", "type": "image", "name": "produto-real.jpg"}],
                },
            },
        }
    )
    updated = client.patch(
        f"/api/v1/workspaces/{workspace}", headers=headers, json={"brandProfile": profile}
    )
    assert updated.status_code == 200, updated.text
    readiness = client.get(f"/api/v1/workspaces/{workspace}/brand-readiness", headers=headers)
    assert readiness.status_code == 200 and readiness.json()["status"] == "ready"


def ingest(client, token: str, workspace: str, *, title: str, summary: str, topics: list[str], suffix: str):
    response = client.post(
        "/api/v1/radar/signals",
        headers=auth(token),
        json={
            "workspaceId": workspace,
            "source": f"Fonte pública {suffix}",
            "url": f"https://example.com/journey-{suffix}",
            "title": title,
            "summary": summary,
            "publishedAt": datetime.now(UTC).isoformat(),
            "topics": topics,
            "metrics": {"novelty_score": 70, "momentum_score": 45},
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def canvas() -> dict:
    return {
        "schemaVersion": "creative-v1",
        "width": 1080,
        "height": 1080,
        "safeArea": 48,
        "background": "#102018",
        "brandTokens": {"primaryColor": "#4f8a3f"},
        "layers": [
            {
                "id": "headline",
                "name": "Título",
                "type": "text",
                "x": 100,
                "y": 120,
                "width": 880,
                "height": 240,
                "zIndex": 1,
                "text": "Campanha conectada e editável",
                "fontSize": 72,
                "minFontSize": 18,
                "color": "#ffffff",
                "align": "center",
            }
        ],
    }


def test_three_workspace_critical_product_journey(client, tmp_path, monkeypatch):
    from app.routers import creatives as creatives_router

    monkeypatch.setattr(creatives_router.settings, "storage_path", str(tmp_path))
    restaurant_token, restaurant = register(client, "journey-restaurant@example.com", "Restaurante Local")
    clinic_token, clinic = register(client, "journey-clinic@example.com", "Clínica")
    creator_token, creator = register(client, "journey-creator@example.com", "Creator Educação")
    configure_brand(
        client,
        restaurant_token,
        restaurant,
        industry="restaurante e gastronomia local",
        product="Menu executivo",
        audience="profissionais que procuram almoço no centro",
        pillars=["almoço executivo", "gastronomia local", "reservas"],
        prohibited=["apostas"],
    )
    configure_brand(
        client,
        clinic_token,
        clinic,
        industry="clínica de saúde preventiva",
        product="Consulta preventiva",
        audience="pacientes que buscam orientação de saúde responsável",
        pillars=["prevenção", "bem-estar", "consulta"],
        prohibited=["cura garantida"],
    )
    configure_brand(
        client,
        creator_token,
        creator,
        industry="creator e educação online",
        product="Curso online",
        audience="profissionais que querem aprender uma nova habilidade",
        pillars=["aprendizado", "carreira", "aula prática"],
        prohibited=["renda garantida"],
    )

    ingest(
        client,
        restaurant_token,
        restaurant,
        title="Restaurantes ampliam reservas com menu executivo no almoço",
        summary="Profissionais no centro procuram gastronomia local, menu executivo e reserva.",
        topics=["restaurante", "almoço executivo", "menu executivo", "reservas"],
        suffix="restaurant",
    )
    ingest(
        client,
        restaurant_token,
        restaurant,
        title="Apostas esportivas crescem durante campeonato nacional",
        summary="Casas de apostas divulgam promoções para novos usuários.",
        topics=["apostas", "esportes"],
        suffix="restaurant-inappropriate",
    )
    ingest(
        client,
        clinic_token,
        clinic,
        title="Clínicas reforçam consulta preventiva e orientação de saúde",
        summary="Pacientes buscam prevenção, bem-estar e consulta responsável.",
        topics=["clínica", "prevenção", "consulta", "saúde"],
        suffix="clinic",
    )
    ingest(
        client,
        creator_token,
        creator,
        title="Profissionais procuram curso online com aula prática",
        summary="Creators de educação apresentam aprendizado aplicado à carreira.",
        topics=["creator", "curso online", "aprendizado", "carreira"],
        suffix="creator",
    )

    ranked_by_workspace = {}
    for token, workspace in (
        (restaurant_token, restaurant),
        (clinic_token, clinic),
        (creator_token, creator),
    ):
        ranked = client.post("/api/v1/radar/rank", headers=auth(token), json={"workspaceId": workspace})
        assert ranked.status_code == 200, ranked.text
        ranked_by_workspace[workspace] = ranked.json()
    inappropriate = next(item for item in ranked_by_workspace[restaurant] if "Apostas" in item["title"])
    assert inappropriate["eligible"] is False
    assert inappropriate["riskLevel"] == "high"
    assert inappropriate["rejectionReason"]

    states = {}
    for token, workspace in (
        (restaurant_token, restaurant),
        (clinic_token, clinic),
        (creator_token, creator),
    ):
        state = client.get("/api/v1/radar/state", headers=auth(token), params={"workspace_id": workspace})
        assert state.status_code == 200, state.text
        assert state.json()["state"] == "ready"
        assert state.json()["opportunities"][0]["source"]["publishedAt"]
        states[workspace] = state.json()
    recommendation_titles = {states[workspace]["opportunities"][0]["title"] for workspace in states}
    assert len(recommendation_titles) == 3

    opportunity = states[restaurant]["opportunities"][0]
    score_before_rejection = opportunity["score"]
    campaign = client.post(
        "/api/v1/campaigns",
        headers=auth(restaurant_token),
        json={
            "workspaceId": restaurant,
            "opportunityId": opportunity["id"],
            "name": "Campanha do almoço executivo",
            "status": "planned",
        },
    )
    assert campaign.status_code == 201, campaign.text
    campaign_data = campaign.json()
    assert campaign_data["originContext"]["source"]["url"] == opportunity["source"]["url"]
    pieces = client.post(
        f"/api/v1/campaigns/{campaign_data['id']}/pieces",
        headers=auth(restaurant_token),
        json={},
    )
    assert pieces.status_code == 200 and len(pieces.json()) == 8
    post = pieces.json()[0]

    creative = client.post(
        "/api/v1/creatives",
        headers=auth(restaurant_token),
        json={
            "workspaceId": restaurant,
            "campaignId": campaign_data["id"],
            "postId": post["id"],
            "title": "Peça do almoço executivo",
            "document": canvas(),
        },
    )
    assert creative.status_code == 201, creative.text
    creative_id = creative.json()["id"]
    changed = canvas()
    changed["background"] = "#1f3022"
    saved = client.patch(
        f"/api/v1/creatives/{creative_id}",
        headers=auth(restaurant_token),
        json={"document": changed},
    )
    assert saved.status_code == 200 and saved.json()["document"]["background"] == "#1f3022"
    versioned = client.post(
        f"/api/v1/creatives/{creative_id}/versions",
        headers=auth(restaurant_token),
        json={"label": "Versão aprovada"},
    )
    assert versioned.status_code == 200 and versioned.json()["version"] == 2
    reopened = client.get(f"/api/v1/creatives/{creative_id}", headers=auth(restaurant_token))
    assert reopened.status_code == 200
    assert reopened.json()["campaignId"] == campaign_data["id"]
    assert reopened.json()["postId"] == post["id"]
    assert reopened.json()["document"]["background"] == "#1f3022"
    exported = client.post(
        f"/api/v1/creatives/{creative_id}/export",
        headers=auth(restaurant_token),
        json={"format": "png"},
    )
    assert exported.status_code == 201, exported.text
    rendered = client.get(exported.json()["url"], headers=auth(restaurant_token))
    assert rendered.status_code == 200
    with Image.open(BytesIO(rendered.content)) as image:
        assert image.size == (1080, 1080)

    assert client.post(
        "/api/v1/radar/feedback",
        headers=auth(restaurant_token),
        json={
            "workspaceId": restaurant,
            "opportunityId": opportunity["id"],
            "eventType": "rejected",
            "reason": "Não combina com a agenda desta semana",
        },
    ).status_code == 204
    reranked = client.post(
        "/api/v1/radar/rank",
        headers=auth(restaurant_token),
        json={"workspaceId": restaurant},
    )
    changed_opportunity = next(item for item in reranked.json() if item["id"] == opportunity["id"])
    assert changed_opportunity["score"] < score_before_rejection
    preferences = client.get(
        "/api/v1/radar/preferences",
        headers=auth(restaurant_token),
        params={"workspace_id": restaurant},
    )
    assert preferences.status_code == 200 and preferences.json()["explicitEvents"] >= 1

    assert client.get(f"/api/v1/creatives/{creative_id}", headers=auth(clinic_token)).status_code == 404
    assert client.get(
        "/api/v1/campaigns",
        headers=auth(clinic_token),
        params={"workspace_id": restaurant},
    ).status_code == 404
    assert client.get(
        "/api/v1/radar/state",
        headers=auth(creator_token),
        params={"workspace_id": restaurant},
    ).status_code == 404
