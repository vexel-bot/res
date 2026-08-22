from io import BytesIO

from conftest import register
from PIL import Image

from app.schemas import CreativeTextLayer
from app.services.creatives import fit_text


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


def test_creative_autosave_version_export_and_tenant_isolation(client, tmp_path, monkeypatch):
    from app.routers import creatives as creatives_router

    monkeypatch.setattr(creatives_router.settings, "storage_path", str(tmp_path))
    token, workspace = register(client, "creative@example.com", "Marca Criativa")
    other_token, _ = register(client, "other-creative@example.com", "Outra Marca")

    source = BytesIO()
    Image.new("RGB", (120, 80), "#ffcc00").save(source, format="PNG")
    uploaded = client.post(
        "/api/v1/assets/upload",
        headers=auth(token),
        data={"workspace_id": workspace, "title": "Produto", "tags": "produto,real"},
        files={"file": ("produto.png", source.getvalue(), "image/png")},
    )
    assert uploaded.status_code == 201, uploaded.text

    created = client.post(
        "/api/v1/creatives",
        headers=auth(token),
        json={"workspaceId": workspace, "title": "Peça principal", "document": canvas(uploaded.json()["id"])},
    )
    assert created.status_code == 201, created.text
    creative_id = created.json()["id"]
    assert created.json()["version"] == 1
    assert created.json()["kind"] == "document"
    assert client.get(f"/api/v1/creatives/{creative_id}", headers=auth(other_token)).status_code == 404

    changed_canvas = canvas(uploaded.json()["id"])
    changed_canvas["background"] = "#081018"
    original_updated_at = created.json()["updatedAt"]
    autosaved = client.patch(
        f"/api/v1/creatives/{creative_id}",
        headers=auth(token),
        json={"document": changed_canvas, "expectedUpdatedAt": original_updated_at},
    )
    assert autosaved.status_code == 200 and autosaved.json()["version"] == 1
    conflict = client.patch(
        f"/api/v1/creatives/{creative_id}",
        headers=auth(token),
        json={"title": "Sobrescrita obsoleta", "expectedUpdatedAt": original_updated_at},
    )
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["code"] == "creative_version_conflict"

    versioned = client.post(
        f"/api/v1/creatives/{creative_id}/versions",
        headers=auth(token),
        json={"label": "Direção aprovada"},
    )
    assert versioned.status_code == 200 and versioned.json()["version"] == 2
    assert versioned.json()["versions"][0]["document"]["background"] == "#081018"

    changed_again = canvas(uploaded.json()["id"])
    changed_again["background"] = "#ffffff"
    client.patch(f"/api/v1/creatives/{creative_id}", headers=auth(token), json={"document": changed_again})
    restored = client.post(f"/api/v1/creatives/{creative_id}/versions/2/restore", headers=auth(token))
    assert restored.status_code == 200 and restored.json()["version"] == 3
    assert restored.json()["document"]["background"] == "#081018"

    exported = client.post(
        f"/api/v1/creatives/{creative_id}/export",
        headers=auth(token),
        json={"format": "png"},
    )
    assert exported.status_code == 201, exported.text
    assert {"export", "png", f"creative:{creative_id}"}.issubset(set(exported.json()["tags"]))
    downloaded = client.get(exported.json()["url"], headers=auth(token))
    assert downloaded.status_code == 200 and downloaded.headers["content-type"] == "image/png"
    with Image.open(BytesIO(downloaded.content)) as result:
        assert result.size == (1080, 1080)

    from app.services import creatives as creatives_service

    monkeypatch.setattr(creatives_service, "MAX_SOURCE_PIXELS", 1)
    oversized = client.post(
        f"/api/v1/creatives/{creative_id}/export",
        headers=auth(token),
        json={"format": "jpeg"},
    )
    assert oversized.status_code == 422


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


def test_text_fitting_reduces_font_size_to_prevent_overflow():
    layer = CreativeTextLayer.model_validate(
        {
            "id": "fit",
            "name": "Texto longo",
            "type": "text",
            "x": 0,
            "y": 0,
            "width": 220,
            "height": 100,
            "text": "Esta chamada precisa caber sem ultrapassar a área definida",
            "fontSize": 80,
            "minFontSize": 12,
        }
    )
    font, lines, line_height = fit_text(layer)
    assert getattr(font, "size", 12) < 80
    assert line_height * len(lines) <= layer.height
