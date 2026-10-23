"""The retired Pillow editor is not a fallback for an unavailable PhotoCraft runtime."""

from io import BytesIO

from conftest import register
from PIL import Image


def test_retired_derivation_is_explicit_private_and_never_changes_the_original(client):
    token, workspace = register(client, "image-lab@example.com")
    other, _ = register(client, "image-intruder@example.com")
    auth = {"Authorization": f"Bearer {token}"}
    source = BytesIO()
    Image.new("RGB", (40, 40), (80, 100, 120)).save(source, "PNG")
    original = source.getvalue()
    uploaded = client.post(
        "/api/v1/assets/upload",
        headers=auth,
        data={"workspace_id": workspace, "title": "Original"},
        files={"file": ("original.png", original, "image/png")},
    )
    assert uploaded.status_code == 201, uploaded.text
    asset = uploaded.json()
    body = {
        "workspaceId": workspace,
        "title": "Ajuste",
        "brightness": 1.35,
        "idempotencyKey": "retired-derive-001",
        "expectedSourceChecksumSha256": asset["checksumSha256"],
    }
    path = f"/api/v1/assets/{asset['id']}/derive"
    response = client.post(path, headers=auth, json=body)
    assert response.status_code == 410
    assert response.json()["detail"]["code"] == "image_editor_replaced_by_photocraft"
    assert client.post(path, headers={"Authorization": f"Bearer {other}"}, json=body).status_code == 404
    assert client.get(asset["url"], headers=auth).content == original


def test_retired_derivation_does_not_claim_checksum_validation_or_success(client):
    token, workspace = register(client, "image-guard@example.com")
    response = client.post(
        "/api/v1/assets/missing/derive",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "workspaceId": workspace,
            "title": "Invalid",
            "idempotencyKey": "retired-missing-001",
            "expectedSourceChecksumSha256": "0" * 64,
        },
    )
    assert response.status_code == 404
