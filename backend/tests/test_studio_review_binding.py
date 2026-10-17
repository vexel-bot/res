from __future__ import annotations

import io

import pytest
from conftest import register
from PIL import Image
from test_studio_kernel import auth, create_document

from app.config import get_settings
from app.database import SessionLocal
from app.models import LibraryAsset
from app.services.object_storage import get_object_storage


def test_changed_draft_cannot_be_approved_through_an_old_snapshot(client):
    token, workspace = register(client, "review-binding@example.com")
    document = create_document(client, token, workspace).json()
    url = f"/api/v1/studios/v1/documents/{document['documentId']}"
    review = client.post(f"{url}/reviews", headers=auth(token), json={}).json()
    current = client.get(url, headers=auth(token)).json()
    current["title"] = "Nova copy ainda não revisada"
    saved = client.put(url, headers=auth(token), json={"expectedRevision": current["revision"], "document": current})
    assert saved.status_code == 200
    decision = client.post(
        f"/api/v1/studios/v1/reviews/{review['id']}/decisions",
        headers=auth(token),
        json={"action": "approve"},
    )
    assert decision.status_code == 409, decision.text
    assert decision.json()["detail"]["code"] == "studio_review_snapshot_stale"
    assert client.get(url, headers=auth(token)).json()["status"] == "draft"
    latest = client.get(
        "/api/v1/studios/v1/reviews/latest",
        headers=auth(token),
        params={"workspace_id": workspace, "document_id": document["documentId"]},
    ).json()
    assert latest["status"] == "requested"
    assert latest["snapshot"]["title"] == "Documento canônico"


def test_review_preview_is_private_pinned_and_page_accurate(client):
    token, workspace = register(client, "review-preview@example.com")
    other, _ = register(client, "review-preview-other@example.com")
    document = create_document(client, token, workspace, content_type="carousel").json()
    url = f"/api/v1/studios/v1/documents/{document['documentId']}"
    document["composition"]["pages"][0]["background"] = "#112233"
    document["composition"]["pages"][1]["background"] = "#334455"
    client.put(url, headers=auth(token), json={"expectedRevision": document["revision"], "document": document})
    review = client.post(f"{url}/reviews", headers=auth(token), json={}).json()
    preview = f"/api/v1/studios/v1/reviews/{review['id']}/pages"
    before = client.get(f"{preview}/page-1/preview", headers=auth(token))
    assert before.status_code == 200, before.text
    assert before.headers["cache-control"] == "private, no-store"
    with Image.open(io.BytesIO(before.content)) as image:
        assert image.size == (1080, 1350)
        assert image.getpixel((10, 10))[:3] == (17, 34, 51)
    second = client.get(f"{preview}/page-2/preview", headers=auth(token))
    with Image.open(io.BytesIO(second.content)) as image:
        assert image.getpixel((10, 10))[:3] == (51, 68, 85)
    assert client.get(f"{preview}/page-1/preview").status_code in {401, 403}
    assert client.get(f"{preview}/page-1/preview", headers=auth(other)).status_code == 404
    assert client.get(f"{preview}/absent/preview", headers=auth(token)).status_code == 404
    current = client.get(url, headers=auth(token)).json()
    current["composition"]["pages"][0]["background"] = "#ff0000"
    client.put(url, headers=auth(token), json={"expectedRevision": current["revision"], "document": current})
    assert client.get(f"{preview}/page-1/preview", headers=auth(token)).content == before.content


@pytest.mark.parametrize("mutation", ["edit", "version", "restore"])
def test_approval_cannot_survive_new_content_version_or_restore(client, mutation):
    token, workspace = register(client, f"approval-invalidation-{mutation}@example.com")
    document = create_document(client, token, workspace).json()
    url = f"/api/v1/studios/v1/documents/{document['documentId']}"
    client.post(f"{url}/versions", headers=auth(token), json={"label": "Antes da revisão"})
    review = client.post(f"{url}/reviews", headers=auth(token), json={}).json()
    assert (
        client.post(
            f"/api/v1/studios/v1/reviews/{review['id']}/decisions", headers=auth(token), json={"action": "approve"}
        ).status_code
        == 200
    )
    current = client.get(url, headers=auth(token)).json()
    assert current["status"] == "approved"
    if mutation == "edit":
        current["brief"]["hook"] = "Outra promessa não revisada"
        changed = client.put(
            url, headers=auth(token), json={"expectedRevision": current["revision"], "document": current}
        )
    elif mutation == "version":
        changed = client.post(f"{url}/versions", headers=auth(token), json={"label": "Nova versão"})
    else:
        changed = client.post(
            f"{url}/versions/2/restore", headers=auth(token), json={"expectedRevision": current["revision"]}
        )
    assert changed.status_code == 200, changed.text
    assert changed.json()["status"] == "draft"
    assert changed.json()["review"]["approvalId"] is None


def test_client_cannot_forge_approval_and_request_is_idempotent_only_for_same_content(client):
    token, workspace = register(client, "review-forgery@example.com")
    document = create_document(client, token, workspace).json()
    url = f"/api/v1/studios/v1/documents/{document['documentId']}"
    document["status"] = "approved"
    document["review"] = {"status": "approved", "requestedVersion": 1, "approvalId": "invented"}
    saved = client.put(
        url, headers=auth(token), json={"expectedRevision": document["revision"], "document": document}
    ).json()
    assert saved["status"] == "draft"
    assert saved["review"]["approvalId"] is None
    review = client.post(f"{url}/reviews", headers=auth(token), json={}).json()
    assert client.post(f"{url}/reviews", headers=auth(token), json={}).json()["id"] == review["id"]
    no_comment = client.post(
        f"/api/v1/studios/v1/reviews/{review['id']}/decisions", headers=auth(token), json={"action": "request_changes"}
    )
    assert no_comment.status_code == 422
    assert "Requesting changes requires a comment" in no_comment.text
    changed = client.post(
        f"/api/v1/studios/v1/reviews/{review['id']}/decisions",
        headers=auth(token),
        json={"action": "request_changes", "comment": "Rever o CTA"},
    )
    assert changed.status_code == 200
    assert changed.json()["status"] == "changes_requested"


def test_preview_refuses_changed_source_bytes_and_does_not_use_placeholder(client, tmp_path, monkeypatch):
    monkeypatch.setattr(get_settings(), "storage_path", str(tmp_path))
    token, workspace = register(client, "review-source@example.com")
    payload = io.BytesIO()
    Image.new("RGB", (200, 200), "red").save(payload, format="PNG")
    uploaded = client.post(
        "/api/v1/assets/upload",
        headers=auth(token),
        data={"workspace_id": workspace, "title": "Fonte fixada"},
        files={"file": ("source.png", payload.getvalue(), "image/png")},
    )
    assert uploaded.status_code == 201, uploaded.text
    asset = uploaded.json()
    document = create_document(client, token, workspace).json()
    url = f"/api/v1/studios/v1/documents/{document['documentId']}"
    document["assets"] = [{"id": asset["id"], "checksum": asset["checksumSha256"], "mediaType": "image/png"}]
    document["composition"]["pages"][0]["layers"] = [
        {
            "id": "source",
            "kind": "image",
            "name": "Fonte",
            "width": 200,
            "height": 200,
            "properties": {"assetId": asset["id"]},
        }
    ]
    saved = client.put(url, headers=auth(token), json={"expectedRevision": document["revision"], "document": document})
    assert saved.status_code == 200, saved.text
    review = client.post(f"{url}/reviews", headers=auth(token), json={}).json()
    preview_url = f"/api/v1/studios/v1/reviews/{review['id']}/pages/page-1/preview"
    valid = client.get(preview_url, headers=auth(token))
    assert valid.status_code == 200, valid.text
    with SessionLocal() as db:
        stored = db.get(LibraryAsset, asset["id"])
        path = get_object_storage(stored.storage_backend).local_path(stored.storage_key)
        assert path is not None
        path.write_bytes(b"tampered fixture")
    invalid = client.get(preview_url, headers=auth(token))
    assert invalid.status_code == 422
    assert invalid.json()["detail"]["code"] == "studio_review_source_changed"


def test_export_bookkeeping_does_not_invalidate_same_creative_review(client, tmp_path, monkeypatch):
    monkeypatch.setattr(get_settings(), "storage_path", str(tmp_path))
    token, workspace = register(client, "review-export@example.com")
    document = create_document(client, token, workspace).json()
    url = f"/api/v1/studios/v1/documents/{document['documentId']}"
    review = client.post(f"{url}/reviews", headers=auth(token), json={}).json()
    assert client.post(f"{url}/exports", headers=auth(token), json={"format": "png"}).status_code == 201
    approved = client.post(
        f"/api/v1/studios/v1/reviews/{review['id']}/decisions", headers=auth(token), json={"action": "approve"}
    )
    assert approved.status_code == 200, approved.text
