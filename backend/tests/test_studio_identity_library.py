from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from conftest import register
from sqlalchemy import select

from app.database import SessionLocal
from app.models import (
    CreativeDocument,
    LibraryAsset,
    StudioConsentGrant,
    StudioGenerationJob,
    StudioIdentityProfile,
    StudioIdentityVersion,
    StudioVoiceProfile,
    StudioVoiceVersion,
    WorkspaceResource,
)
from app.routers import studio_department, studio_identity_library
from app.services.studios import craft
from app.services.studios.casting import validate_document_cast, validate_publication_cast
from app.services.studios.compatibility import record_to_contract

BASE = "/api/v1/studios/v1/identity-library"
PROJECTS = "/api/v1/studios/v1/projects"


def setup(client):
    token, workspace = register(client, "cast@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    with SessionLocal() as db:
        assets = []
        for kind, mime in (("photo", "image/png"), ("audio", "audio/wav"), ("authorization", "text/plain")):
            asset = LibraryAsset(
                workspace_id=workspace,
                title=kind,
                asset_type="upload",
                media_type=mime,
                storage_key=f"test-{kind}",
                checksum_sha256="a" * 64,
                size_bytes=128,
            )
            db.add(asset)
            db.flush()
            assets.append(asset.id)
        db.commit()
    body = {
        "workspaceId": workspace,
        "requestKey": "enroll-cast-001",
        "mode": "face_voice",
        "displayName": "Pessoa autorizada",
        "imageAssetId": assets[0],
        "audioAssetId": assets[1],
        "evidenceAssetId": assets[2],
        "purpose": "Conteúdo privado para avaliação da marca.",
        "declared": True,
        "expiresAt": (datetime.now(UTC) + timedelta(days=30)).isoformat(),
    }
    return headers, body


def enroll(client, headers, body):
    response = client.post(f"{BASE}/enrollments", headers=headers, json=body)
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.parametrize("mode", ["face", "voice", "face_voice", "character", "stock_voice"])
def test_independent_enrollment_and_idempotent_retries(client, mode):
    headers, body = setup(client)
    body["mode"] = mode
    if mode in {"voice", "stock_voice"}:
        body.pop("imageAssetId")
    if mode in {"face", "character"}:
        body.pop("audioAssetId")
    if mode in {"character", "stock_voice"}:
        body.pop("expiresAt")
        body["rightsReference"] = "Personagem ou voz de autoria própria com comprovante anexado."
    receipt = enroll(client, headers, body)
    assert receipt["status"] == "draft"
    assert enroll(client, headers, body) == receipt
    assert (
        client.post(f"{BASE}/enrollments", headers=headers, json={**body, "displayName": "Outro nome"}).status_code
        == 409
    )
    with SessionLocal() as db:
        assert (
            len(
                db.scalars(
                    select(WorkspaceResource).where(WorkspaceResource.kind == studio_identity_library.KIND)
                ).all()
            )
            == 1
        )
        assert bool(receipt["identityVersionId"]) == (mode in {"face", "face_voice", "character"})
        assert bool(receipt["voiceVersionId"]) == (mode in {"voice", "face_voice", "stock_voice"})
        grant = db.get(StudioConsentGrant, receipt["consentGrantId"]) if receipt["consentGrantId"] else None
        if mode == "voice":
            assert set(grant.scopes) == {"voice.enroll", "voice.clone"}
            assert not db.scalars(select(StudioIdentityVersion)).all()
        if mode == "face":
            assert set(grant.scopes) == {"identity.enroll", "avatar.generate"}
            assert not db.scalars(select(StudioVoiceProfile)).all()
        if mode in {"character", "stock_voice"}:
            assert grant is None
    catalog = client.get(BASE, headers=headers, params={"workspace_id": body["workspaceId"]})
    assert catalog.status_code == 200, catalog.text
    for card in [*catalog.json()["identities"], *catalog.json()["voices"]]:
        assert card["selectedVersionId"] is None
        assert card["unavailableReason"]


def test_enrollment_rolls_back_all_records_on_partial_failure(client, monkeypatch):
    headers, body = setup(client)

    def fail(*args, **kwargs):
        raise ValueError("voice_preparation_failed")

    monkeypatch.setattr(studio_identity_library.identity, "create_voice_version", fail)
    response = client.post(f"{BASE}/enrollments", headers=headers, json=body)
    assert response.status_code == 422
    with SessionLocal() as db:
        for model in (
            StudioConsentGrant,
            StudioIdentityProfile,
            StudioIdentityVersion,
            StudioVoiceProfile,
            WorkspaceResource,
        ):
            assert not db.scalars(select(model)).all()


def test_samples_rights_expiry_and_workspace_are_enforced(client):
    headers, body = setup(client)
    assert client.get(BASE, params={"workspace_id": body["workspaceId"]}).status_code == 401
    assert (
        client.post(
            f"{BASE}/enrollments", headers=headers, json={**body, "evidenceAssetId": body["imageAssetId"]}
        ).status_code
        == 422
    )
    assert (
        client.post(
            f"{BASE}/enrollments", headers=headers, json={**body, "audioAssetId": body["imageAssetId"]}
        ).status_code
        == 422
    )
    assert (
        client.post(
            f"{BASE}/enrollments",
            headers=headers,
            json={**body, "expiresAt": (datetime.now(UTC) - timedelta(days=1)).isoformat()},
        ).status_code
        == 422
    )
    other_token, _ = register(client, "other-cast@example.com")
    other = {"Authorization": f"Bearer {other_token}"}
    assert client.get(BASE, headers=other, params={"workspace_id": body["workspaceId"]}).status_code == 404
    assert client.post(f"{BASE}/enrollments", headers=other, json=body).status_code == 404


def activate_for_binding_test(receipt):
    # Fixtures qualify reference propagation, not ML quality or approval policy.
    with SessionLocal() as db:
        for model, key in (
            (StudioIdentityProfile, "identityProfileId"),
            (StudioIdentityVersion, "identityVersionId"),
            (StudioVoiceProfile, "voiceProfileId"),
            (StudioVoiceVersion, "voiceVersionId"),
        ):
            if receipt[key]:
                db.get(model, receipt[key]).status = "active"
        db.commit()


def test_cast_references_survive_image_document_creation_and_revocation_blocks_render(client, monkeypatch):
    headers, body = setup(client)
    receipt = enroll(client, headers, body)
    project_input = {
        "workspaceId": body["workspaceId"],
        "requestKey": "cast-project-001",
        "title": "Uma presença da marca",
        "objective": "Explicar o processo com uma pessoa autorizada.",
        "audience": "Clientes da marca",
        "format": "image",
        "identityVersionId": receipt["identityVersionId"],
        "voiceVersionId": receipt["voiceVersionId"],
    }
    assert client.post(PROJECTS, headers=headers, json=project_input).status_code == 422
    activate_for_binding_test(receipt)
    project = client.post(PROJECTS, headers=headers, json=project_input).json()
    assert project["casting"]["identity"]["id"] == receipt["identityVersionId"]
    assert project["casting"]["voice"]["id"] == receipt["voiceVersionId"]
    catalog = client.get(BASE, headers=headers, params={"workspace_id": body["workspaceId"]}).json()
    assert catalog["identities"][0]["selectedVersionId"] == receipt["identityVersionId"]
    project = client.patch(
        f"{PROJECTS}/{project['id']}",
        headers=headers,
        json={"expectedRevision": project["revision"], "directionId": "guide"},
    ).json()
    monkeypatch.setattr(studio_department, "record_to_contract", lambda doc: SimpleNamespace(native_editor_state=True))
    monkeypatch.setattr(studio_department, "render_job", lambda *args: SimpleNamespace(id="fixture-render"))
    response = client.post(
        f"{PROJECTS}/{project['id']}/produce", headers=headers, json={"expectedRevision": project["revision"]}
    )
    assert response.status_code == 200, response.text
    project = response.json()
    with SessionLocal() as db:
        record = db.get(CreativeDocument, project["documentId"])
        doc = record_to_contract(record)
        assert doc.identity_ref.id == receipt["identityVersionId"]
        assert doc.voice_ref.id == receipt["voiceVersionId"]
        assert doc.composition.pages[0].layers[-1].properties["assetId"] == body["imageAssetId"]
        validate_document_cast(db, doc)
        with pytest.raises(ValueError, match="publication_scope_missing"):
            validate_publication_cast(db, doc, "instagram")
        grant = db.get(StudioConsentGrant, receipt["consentGrantId"])
        grant.scopes = [*grant.scopes, "publish.synthetic"]
        db.commit()
        with pytest.raises(ValueError, match="publication_channel_not_authorized"):
            validate_publication_cast(db, doc, "instagram")
        grant.channels = ["instagram"]
        grant.brand_ids = ["another-brand"]
        db.commit()
        with pytest.raises(ValueError, match="publication_brand_not_authorized"):
            validate_publication_cast(db, doc, "instagram")
        grant.brand_ids = [doc.brand_memory_ref.id]
        db.commit()
        validate_publication_cast(db, doc, "instagram")
    revoke = client.post(
        f"/api/v1/studios/v1/consents/{receipt['consentGrantId']}/revoke",
        headers=headers,
        json={"reason": "Encerrada a finalidade"},
    )
    assert revoke.status_code == 200
    with SessionLocal() as db:
        record = db.get(CreativeDocument, project["documentId"])
        with pytest.raises(ValueError, match="not_active"):
            craft.render_frame(db, record)
    assert (
        client.post(
            f"{PROJECTS}/{project['id']}/produce", headers=headers, json={"expectedRevision": project["revision"]}
        ).status_code
        == 422
    )
    catalog = client.get(BASE, headers=headers, params={"workspace_id": body["workspaceId"]}).json()
    assert not catalog["identities"][0]["selectedVersionId"]


def test_cross_workspace_cast_reference_cannot_be_attached_to_a_project(client):
    headers, body = setup(client)
    receipt = enroll(client, headers, body)
    activate_for_binding_test(receipt)
    token, workspace = register(client, "another-project@example.com")
    response = client.post(
        PROJECTS,
        headers={"Authorization": f"Bearer {token}"},
        json={
            "workspaceId": workspace,
            "requestKey": "cross-workspace-001",
            "title": "Outro projeto",
            "objective": "Criar conteúdo para outra marca",
            "audience": "Outro público",
            "identityVersionId": receipt["identityVersionId"],
        },
    )
    assert response.status_code == 422
    # The generic document entry point must enforce the same boundary and return
    # a client validation error, rather than an unhandled server error.
    response = client.post(
        "/api/v1/studios/v1/documents",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "workspaceId": workspace,
            "title": "Tentativa de referência externa",
            "brief": {"objective": "Verificar isolamento", "audience": "Equipe de QA"},
            "composition": {"pages": [{"id": "page", "width": 100, "height": 100, "layers": []}]},
            "identityRef": {
                "id": receipt["identityVersionId"],
                "version": 1,
                "consentGrantId": receipt["consentGrantId"],
            },
        },
    )
    assert response.status_code == 422, response.text


def test_revoking_an_independent_narrator_cancels_the_jobs_bound_to_that_voice(client):
    headers, body = setup(client)
    face = enroll(
        client, headers, {key: value for key, value in {**body, "mode": "face"}.items() if key != "audioAssetId"}
    )
    voice = enroll(
        client,
        headers,
        {
            key: value
            for key, value in {**body, "mode": "voice", "requestKey": "independent-narrator-001"}.items()
            if key != "imageAssetId"
        },
    )
    activate_for_binding_test(face)
    activate_for_binding_test(voice)
    job_ids = {}
    with SessionLocal() as db:
        for status in ("queued", "running", "succeeded"):
            job = StudioGenerationJob(
                workspace_id=body["workspaceId"],
                job_type="craft_render",
                provider="craft.photocraft",
                status=status,
                idempotency_key=f"independent-narrator-{status}",
                payload_hash="b" * 64,
                correlation_id="casting-revocation",
                identity_version_id=face["identityVersionId"],
                voice_version_id=voice["voiceVersionId"],
                consent_grant_id=face["consentGrantId"],
            )
            db.add(job)
            db.flush()
            job_ids[status] = job.id
        db.commit()
    response = client.post(
        f"/api/v1/studios/v1/consents/{voice['consentGrantId']}/revoke",
        headers=headers,
        json={"reason": "Narrator withdrew authorization"},
    )
    assert response.status_code == 200
    with SessionLocal() as db:
        assert db.get(StudioGenerationJob, job_ids["queued"]).status == "cancelled"
        assert db.get(StudioGenerationJob, job_ids["running"]).status == "cancel_requested"
        assert db.get(StudioGenerationJob, job_ids["succeeded"]).status == "succeeded"
        assert db.get(StudioConsentGrant, face["consentGrantId"]).status == "active"
