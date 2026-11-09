"""Project plan tests use synthetic metadata; no image model is executed."""

from conftest import register
from test_studio_identity_library import PROJECTS, activate_for_binding_test, enroll, setup

from app.database import SessionLocal
from app.models import LibraryAsset, StudioConsentGrant


def test_plan_binds_project_materials_and_rechecks_access_and_consent(client):
    headers, enrollment = setup(client)
    receipt = enroll(client, headers, enrollment)
    activate_for_binding_test(receipt)
    with SessionLocal() as db:
        portrait = db.get(LibraryAsset, enrollment["imageAssetId"])
        portrait.storage_key = f"{enrollment['workspaceId']}/samples/portrait.png"
        portrait.storage_backend = "local"
        scene = LibraryAsset(
            workspace_id=enrollment["workspaceId"],
            title="Cena de teste",
            asset_type="image",
            media_type="image/png",
            storage_key=f"{enrollment['workspaceId']}/assets/scene.png",
            storage_backend="local",
            checksum_sha256="b" * 64,
            size_bytes=128,
        )
        db.add(scene)
        db.flush()
        scene_id = scene.id
        db.commit()
    response = client.post(
        PROJECTS,
        headers=headers,
        json={
            "workspaceId": enrollment["workspaceId"],
            "requestKey": "appearance-plan-test-001",
            "title": "Conteúdo da marca",
            "objective": "Apresentar uma orientação para a marca.",
            "audience": "Clientes da marca",
            "format": "image",
            "sourceAssetId": scene_id,
            "identityVersionId": receipt["identityVersionId"],
            "voiceVersionId": receipt["voiceVersionId"],
        },
    )
    assert response.status_code == 201, response.text
    project = response.json()
    project = client.patch(
        f"{PROJECTS}/{project['id']}",
        headers=headers,
        json={
            "expectedRevision": project["revision"],
            "directionId": "guide",
        },
    ).json()
    url = f"{PROJECTS}/{project['id']}/appearance/plan"
    body = {"expectedRevision": project["revision"], "direction": "A pessoa no cenário escolhido.", "seed": 7}
    response = client.post(url, headers=headers, json=body)
    assert response.status_code == 200, response.text
    plan = response.json()
    assert plan["request"]["referenceAssetId"] == enrollment["imageAssetId"]
    assert plan["request"]["sourceAssetId"] == scene_id
    assert plan["casting"]["identity"]["id"] == receipt["identityVersionId"]
    assert plan["casting"]["voice"]["id"] == receipt["voiceVersionId"]
    assert client.post(url, headers=headers, json=body).json()["planDigestSha256"] == plan["planDigestSha256"]
    assert client.post(url, headers=headers, json={**body, "expectedRevision": 1}).status_code == 409
    token, _ = register(client, "appearance-other@example.com")
    assert client.post(url, headers={"Authorization": f"Bearer {token}"}, json=body).status_code == 404
    with SessionLocal() as db:
        grant = db.get(StudioConsentGrant, receipt["consentGrantId"])
        grant.status = "revoked"
        db.commit()
    assert client.post(url, headers=headers, json=body).status_code == 422
