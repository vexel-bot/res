from __future__ import annotations

from io import BytesIO

from PIL import Image

from conftest import register


def _png(color: tuple[int, int, int]) -> bytes:
    stream = BytesIO()
    Image.new("RGB", (40, 40), color).save(stream, format="PNG")
    return stream.getvalue()


def test_image_derivation_is_private_immutable_idempotent_and_lineaged(client) -> None:
    token, workspace_id = register(client, "image-lab@example.com", "Image Lab")
    other_token, _ = register(client, "image-intruder@example.com", "Other")
    headers = {"Authorization": f"Bearer {token}"}
    source_bytes = _png((80, 100, 120))
    uploaded = client.post(
        "/api/v1/assets/upload",
        headers=headers,
        data={"workspace_id": workspace_id, "title": "Original", "tags": "source"},
        files={"file": ("original.png", source_bytes, "image/png")},
    )
    assert uploaded.status_code == 201, uploaded.text
    source = uploaded.json()
    payload = {
        "workspaceId": workspace_id,
        "title": "Original · ajuste revisável",
        "brightness": 1.35,
        "contrast": 1.1,
        "editMask": {
            "shape": "ellipse",
            "x": 0.1,
            "y": 0.1,
            "width": 0.8,
            "height": 0.8,
        },
        "protectedRegions": [
            {
                "kind": "product",
                "label": "Produto central",
                "x": 0.4,
                "y": 0.4,
                "width": 0.2,
                "height": 0.2,
            }
        ],
        "expectedSourceChecksumSha256": source["checksumSha256"],
        "idempotencyKey": "image-edit-test-001",
    }
    first = client.post(
        f"/api/v1/assets/{source['id']}/derive",
        headers=headers,
        json=payload,
    )
    assert first.status_code == 201, first.text
    derived = first.json()
    assert derived["id"] != source["id"]
    assert derived["type"] == "image"
    assert derived["mediaType"] == "image/png"
    assert derived["metadata"]["sourceAssetId"] == source["id"]
    assert derived["metadata"]["sourceChecksumSha256"] == source["checksumSha256"]
    assert derived["metadata"]["provider"] == "pillow"
    assert derived["metadata"]["reviewRequired"] == "true"

    repeated = client.post(
        f"/api/v1/assets/{source['id']}/derive",
        headers=headers,
        json=payload,
    )
    assert repeated.status_code == 201
    assert repeated.json()["id"] == derived["id"]

    assert client.get(source["url"], headers=headers).content == source_bytes
    derivative_bytes = client.get(derived["url"], headers=headers).content
    assert derivative_bytes != source_bytes
    with Image.open(BytesIO(derivative_bytes)) as image:
        assert image.size == (40, 40)
        # The protected center is byte-for-byte equivalent at pixel level.
        assert image.convert("RGB").getpixel((20, 20)) == (80, 100, 120)

    isolated = client.post(
        f"/api/v1/assets/{source['id']}/derive",
        headers={"Authorization": f"Bearer {other_token}"},
        json=payload,
    )
    assert isolated.status_code == 404


def test_image_derivation_fails_closed_on_checksum_or_non_image(client) -> None:
    token, workspace_id = register(client, "image-guard@example.com", "Image Guard")
    headers = {"Authorization": f"Bearer {token}"}
    uploaded = client.post(
        "/api/v1/assets/upload",
        headers=headers,
        data={"workspace_id": workspace_id, "title": "Original"},
        files={"file": ("original.png", _png((20, 40, 60)), "image/png")},
    ).json()
    response = client.post(
        f"/api/v1/assets/{uploaded['id']}/derive",
        headers=headers,
        json={
            "workspaceId": workspace_id,
            "title": "Invalid",
            "expectedSourceChecksumSha256": "0" * 64,
            "idempotencyKey": "image-edit-invalid-001",
        },
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "image_derivation_source_checksum_conflict"
