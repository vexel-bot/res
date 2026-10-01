from __future__ import annotations

import io
import wave
from datetime import UTC, datetime, timedelta

from conftest import register
from test_studio_kernel import auth, create_document

from app.database import SessionLocal
from app.models import LibraryAsset, Membership, User
from app.services.object_storage import get_object_storage


def wav_fixture() -> bytes:
    output = io.BytesIO()
    with wave.open(output, "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(16_000)
        target.writeframes(bytes(16_000 * 2))
    return output.getvalue()


def test_natural_sound_rights_are_server_owned_idempotent_and_tenant_scoped(client, tmp_path, monkeypatch):
    from app.routers import assets as assets_router

    monkeypatch.setattr(assets_router.settings, "storage_path", str(tmp_path))
    owner_token, workspace = register(client, "sound-rights-owner@example.com")
    editor_token, _ = register(client, "sound-rights-editor@example.com")
    foreign_token, _ = register(client, "sound-rights-foreign@example.com")
    with SessionLocal() as db:
        editor = db.query(User).filter_by(email="sound-rights-editor@example.com").one()
        db.add(Membership(user_id=editor.id, workspace_id=workspace, role="Editor"))
        db.commit()

    uploaded = client.post(
        "/api/v1/assets/upload",
        headers=auth(owner_token),
        data={"workspace_id": workspace, "title": "Ambiente próprio"},
        files={"file": ("ambiente.wav", wav_fixture(), "audio/wav")},
    )
    assert uploaded.status_code == 201, uploaded.text
    asset = uploaded.json()
    document = create_document(client, owner_token, workspace, content_type="video").json()
    document_url = f"/api/v1/studios/v1/documents/{document['documentId']}"
    document["assets"] = [{
        "id": asset["id"],
        "version": 1,
        "mediaType": "audio/wav",
        "checksum": asset["checksumSha256"],
        "rightsStatus": "verified",
        "provenance": {
            "purpose": "natural-sound-candidate",
            "sourceDeclaration": "Gravação própria no estúdio Clicko",
            "licenseDeclaration": "Direitos patrimoniais próprios",
            "rightsReviewId": "forged-client-review",
        },
    }]
    forged = client.put(
        document_url,
        headers=auth(owner_token),
        json={"expectedRevision": document["revision"], "document": document},
    )
    assert forged.status_code == 200, forged.text
    current = forged.json()
    assert current["assets"][0]["rightsStatus"] == "unknown"
    assert current["assets"][0]["provenance"]["rightsStatusReason"] == "rights_review_missing"
    assert current["assets"][0]["provenance"].get("rightsReviewId") is None

    endpoint = f"{document_url}/assets/{asset['id']}/rights-reviews"
    request_body = {
        "expectedDocumentRevision": current["revision"],
        "assetChecksumSha256": asset["checksumSha256"],
        "decision": "verified",
        "basis": "owned",
        "sourceReference": "Registro interno de captação CLICK-FOLEY-001",
        "rightsReference": "Declaração de titularidade CLICK-RIGHTS-001",
        "noExpirationConfirmed": True,
        "notes": "Revisão técnica isolada; fixture sem uso em produção.",
    }
    editor_denied = client.post(
        endpoint,
        headers={**auth(editor_token), "Idempotency-Key": "rights-editor-denied"},
        json=request_body,
    )
    assert editor_denied.status_code == 403
    assert client.post(
        endpoint,
        headers={**auth(foreign_token), "Idempotency-Key": "rights-foreign-hidden"},
        json=request_body,
    ).status_code == 404

    reviewed = client.post(
        endpoint,
        headers={**auth(owner_token), "Idempotency-Key": "rights-owned-fixture-001"},
        json=request_body,
    )
    assert reviewed.status_code == 200, reviewed.text
    response = reviewed.json()
    rights_review = response["review"]
    assert rights_review["decision"] == "verified"
    assert rights_review["assetChecksumSha256"] == asset["checksumSha256"]
    assert rights_review["publicationScope"] == "commercial-saas"
    assert rights_review["reviewerId"]
    assert response["document"]["revision"] == current["revision"] + 1
    projected = response["document"]["assets"][0]
    assert projected["rightsStatus"] == "verified"
    assert projected["provenance"]["rightsReviewId"] == rights_review["reviewId"]
    assert projected["provenance"]["rightsStatusReason"] == "rights_review_verified"

    replay = client.post(
        endpoint,
        headers={**auth(owner_token), "Idempotency-Key": "rights-owned-fixture-001"},
        json=request_body,
    )
    assert replay.status_code == 200
    assert replay.json()["review"]["reviewId"] == rights_review["reviewId"]
    assert replay.json()["document"]["revision"] == response["document"]["revision"]
    conflict_body = {**request_body, "rightsReference": "Outra referência"}
    conflict = client.post(
        endpoint,
        headers={**auth(owner_token), "Idempotency-Key": "rights-owned-fixture-001"},
        json=conflict_body,
    )
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["code"] == "studio_asset_rights_idempotency_conflict"

    changed_declaration = response["document"]
    changed_declaration["assets"][0]["rightsStatus"] = "verified"
    changed_declaration["assets"][0]["provenance"]["licenseDeclaration"] = "Outra licença não revisada"
    changed = client.put(
        document_url,
        headers=auth(owner_token),
        json={"expectedRevision": changed_declaration["revision"], "document": changed_declaration},
    )
    assert changed.status_code == 200
    assert changed.json()["assets"][0]["rightsStatus"] == "unknown"
    assert changed.json()["assets"][0]["provenance"]["rightsStatusReason"] == "rights_declarations_changed"

    restored = changed.json()
    restored["assets"][0]["provenance"]["licenseDeclaration"] = "Direitos patrimoniais próprios"
    restored_response = client.put(
        document_url,
        headers=auth(owner_token),
        json={"expectedRevision": restored["revision"], "document": restored},
    )
    assert restored_response.status_code == 200
    assert restored_response.json()["assets"][0]["rightsStatus"] == "verified"

    expired = client.post(
        endpoint,
        headers={**auth(owner_token), "Idempotency-Key": "rights-expired-fixture"},
        json={
            **request_body,
            "expectedDocumentRevision": restored_response.json()["revision"],
            "expiresAt": (datetime.now(UTC) - timedelta(days=1)).isoformat(),
            "noExpirationConfirmed": False,
        },
    )
    assert expired.status_code == 422
    assert expired.json()["detail"]["code"] == "studio_asset_rights_expiration_invalid"

    with SessionLocal() as db:
        stored = db.get(LibraryAsset, asset["id"])
        path = get_object_storage(stored.storage_backend).local_path(stored.storage_key)
        assert path is not None
        original = path.read_bytes()
        path.write_bytes(b"changed-after-upload")
    tampered = client.post(
        endpoint,
        headers={**auth(owner_token), "Idempotency-Key": "rights-tampered-fixture"},
        json={**request_body, "expectedDocumentRevision": restored_response.json()["revision"]},
    )
    assert tampered.status_code == 422
    assert tampered.json()["detail"]["code"] == "studio_asset_rights_checksum_mismatch"
    path.write_bytes(original)

    restricted = client.post(
        endpoint,
        headers={**auth(owner_token), "Idempotency-Key": "rights-restricted-fixture"},
        json={
            **request_body,
            "expectedDocumentRevision": restored_response.json()["revision"],
            "decision": "restricted",
            "noExpirationConfirmed": False,
            "notes": "Uso comercial não permitido.",
        },
    )
    assert restricted.status_code == 200, restricted.text
    assert restricted.json()["document"]["assets"][0]["rightsStatus"] == "restricted"
    after_restriction = restricted.json()["document"]
    after_restriction["assets"][0]["provenance"]["sourceDeclaration"] = "Declaração alterada"
    still_restricted = client.put(
        document_url,
        headers=auth(owner_token),
        json={"expectedRevision": after_restriction["revision"], "document": after_restriction},
    )
    assert still_restricted.status_code == 200
    assert still_restricted.json()["assets"][0]["rightsStatus"] == "restricted"
