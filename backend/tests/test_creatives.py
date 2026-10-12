from conftest import register


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def canvas(image_asset_id: str | None = None) -> dict:
    layers = [
        {
            "id": "accent",
            "name": "Faixa",
            "type": "shape",
            "x": 50,
            "y": 60,
            "width": 500,
            "height": 180,
            "zIndex": 0,
            "shape": "rectangle",
            "fill": "#6366f1",
            "radius": 24,
        },
        {
            "id": "headline",
            "name": "Título",
            "type": "text",
            "x": 80,
            "y": 90,
            "width": 440,
            "height": 120,
            "zIndex": 1,
            "text": "Uma campanha editável",
            "fontSize": 72,
            "minFontSize": 18,
            "color": "#ffffff",
            "align": "center",
        },
    ]
    if image_asset_id:
        layers.insert(
            0,
            {
                "id": "product",
                "name": "Produto real",
                "type": "image",
                "x": 600,
                "y": 60,
                "width": 400,
                "height": 500,
                "zIndex": 0,
                "assetId": image_asset_id,
                "fit": "cover",
            },
        )
    return {
        "schemaVersion": "creative-v1",
        "width": 1080,
        "height": 1080,
        "safeArea": 48,
        "background": "#10181c",
        "brandTokens": {"primaryColor": "#6366f1"},
        "layers": layers,
    }


def test_legacy_canvas_is_readable_but_cannot_edit_or_restore(client):
    token, workspace = register(client, "creative-archive@example.com", "Marca Criativa")
    other_token, _ = register(client, "other-archive@example.com", "Outra Marca")
    created = client.post(
        "/api/v1/creatives", headers=auth(token),
        json={"workspaceId": workspace, "title": "Arquivo importado", "document": canvas()},
    )
    assert created.status_code == 201, created.text
    creative_id = created.json()["id"]
    base = f"/api/v1/creatives/{creative_id}"
    assert client.get(base, headers=auth(other_token)).status_code == 404
    assert client.get(base, headers=auth(token)).json()["document"] == created.json()["document"]
    changed = canvas()
    changed["background"] = "#ffffff"
    assert client.patch(base, headers=auth(token), json={"document": changed}).status_code == 410
    assert client.post(base + "/versions", headers=auth(token), json={"label": "Antigo"}).status_code == 410
    assert client.post(base + "/versions/1/restore", headers=auth(token)).status_code == 410
    assert client.post(base + "/versions", headers=auth(other_token), json={}).status_code == 404
    assert client.get(base, headers=auth(token)).json()["document"] == created.json()["document"]


def test_creative_schema_rejects_invalid_dimensions_and_colors(client):
    token, workspace = register(client, "invalid-creative@example.com")
    invalid = canvas()
    invalid["width"] = 100
    invalid["background"] = "red"
    response = client.post(
        "/api/v1/creatives",
        headers=auth(token),
        json={"workspaceId": workspace, "title": "Inválida", "document": invalid},
    )
    assert response.status_code == 422


def test_layered_template_can_be_saved_and_filtered(client):
    token, workspace = register(client, "template-creative@example.com")
    headers = auth(token)
    template = client.post(
        "/api/v1/creatives",
        headers=headers,
        json={
            "workspaceId": workspace,
            "kind": "template",
            "title": "Manifesto por camadas",
            "document": canvas(),
        },
    )
    assert template.status_code == 201, template.text
    assert template.json()["kind"] == "template"

    filtered = client.get(
        "/api/v1/creatives",
        headers=headers,
        params={"workspace_id": workspace, "kind": "template"},
    )
    assert filtered.status_code == 200
    assert [item["id"] for item in filtered.json()] == [template.json()["id"]]

    documents = client.get(
        "/api/v1/creatives",
        headers=headers,
        params={"workspace_id": workspace, "kind": "document"},
    )
    assert documents.status_code == 200 and documents.json() == []

    history = client.get(
        "/api/v1/history",
        headers=headers,
        params={"workspace_id": workspace, "query": "Manifesto", "item_type": "template"},
    )
    assert history.status_code == 200
    assert history.json()[0]["resourceId"] == template.json()["id"]
    reused = client.post(
        f"/api/v1/history/creatives/{template.json()['id']}/reuse",
        headers=headers,
        json={},
    )
    assert reused.status_code == 201, reused.text
    assert reused.json()["kind"] == "document"
    assert reused.json()["document"]["layers"] == template.json()["document"]["layers"]
