from conftest import register


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_brand_readiness_is_explainable_versioned_and_tenant_isolated(client):
    token, workspace = register(client, "brand-ready@example.com", "Restaurante Local")
    other_token, _ = register(client, "brand-ready-other@example.com", "Clínica")
    headers = auth(token)

    initial = client.get(f"/api/v1/workspaces/{workspace}/brand-readiness", headers=headers)
    assert initial.status_code == 200, initial.text
    assert initial.json()["status"] == "incomplete"
    assert initial.json()["percentage"] < 50
    assert any(gap["field"] == "products_and_offers" for gap in initial.json()["missingFields"])
    assert client.get(
        f"/api/v1/workspaces/{workspace}/brand-readiness",
        headers=auth(other_token),
    ).status_code == 404

    profile = client.get("/api/v1/bootstrap", headers=headers).json()["workspaces"][0]["brandProfile"]
    profile.update(
        {
            "industry": "restaurante e gastronomia local",
            "regions": ["São Paulo", "Centro"],
            "tone": "próximo, claro e confiável",
            "targetAudience": "profissionais que almoçam no centro",
            "products": [{"name": "Menu executivo", "description": "almoço rápido com reserva"}],
            "pillars": ["gastronomia", "rotina local", "qualidade"],
            "prohibitedTopics": ["promessas de tempo sem confirmação"],
            "watchlist": {
                "topics": ["gastronomia local", "eventos no centro"],
                "players": ["restaurantes da região"],
                "brainRevision": 3,
                "brain": {
                    "company": "Restaurante local no centro de São Paulo",
                    "products": "Menu executivo",
                    "services": "Reserva antecipada",
                    "visualIdentity": "paleta verde e fotografias reais dos pratos",
                    "toneOfVoice": "próximo e claro",
                    "audience": "profissionais da região",
                    "personas": "pessoas com pouco tempo de almoço",
                    "objectives": "aumentar reservas no almoço",
                    "differentiators": "cardápio e disponibilidade confirmados",
                    "competitors": "restaurantes de almoço executivo da região",
                    "objections": "receio de demora",
                    "pains": "pouco tempo para almoçar",
                    "desires": "comer bem perto do trabalho",
                    "faq": "horários, cardápio e reservas",
                    "forbiddenWords": "garantido, instantâneo",
                    "sourceFiles": [{"id": "asset-1", "type": "image", "name": "prato-real.jpg"}],
                },
            },
        }
    )
    updated = client.patch(
        f"/api/v1/workspaces/{workspace}",
        headers=headers,
        json={"brandProfile": profile},
    )
    assert updated.status_code == 200, updated.text

    ready = client.get(f"/api/v1/workspaces/{workspace}/brand-readiness", headers=headers)
    assert ready.status_code == 200, ready.text
    assert ready.json()["status"] == "ready"
    assert ready.json()["percentage"] == 100
    assert ready.json()["missingFields"] == []
    assert ready.json()["revision"] == 3
    assert ready.json()["versionCount"] == 1

    changed_profile = updated.json()["brandProfile"]
    changed_profile["tone"] = "tom alterado"
    changed = client.patch(
        f"/api/v1/workspaces/{workspace}",
        headers=headers,
        json={"brandProfile": changed_profile},
    )
    assert changed.status_code == 200, changed.text
    versions = client.get(f"/api/v1/workspaces/{workspace}/brand-versions", headers=headers)
    assert versions.status_code == 200, versions.text
    assert [version["number"] for version in versions.json()] == [2, 1]

    restored = client.post(
        f"/api/v1/workspaces/{workspace}/brand-versions/1/restore",
        headers=headers,
    )
    assert restored.status_code == 200, restored.text
    assert restored.json()["brandProfile"]["tone"] == "próximo, claro e confiável"
    assert len(restored.json()["brandProfile"]["versions"]) == 3
