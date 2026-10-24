"""Explicit native acceptance: requires the built Craft runtime, no pixel mocks.

Run with PYTHONPATH=backend python -m pytest backend/tests/native_identity_acceptance.py.
The active identity fixture tests composition; it does not qualify face cloning.
"""

from datetime import UTC, datetime, timedelta
from io import BytesIO
from types import SimpleNamespace

from conftest import register
from PIL import Image
from test_studio_identity_library import activate_for_binding_test

from app.config import get_settings
from app.database import SessionLocal
from app.models import StudioGenerationJob
from app.routers import studio_department
from app.services.studios import craft


def test_reference_portrait_survives_native_composition_export_reopen_and_revocation(client, tmp_path, monkeypatch):
    monkeypatch.setattr(get_settings(), "storage_path", str(tmp_path))
    token, workspace = register(client, "native-cast@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    source = BytesIO()
    Image.new("RGB", (64, 64), (3, 171, 99)).save(source, "PNG")
    asset_ids = []
    for name, content, mime in (
        ("sample.png", source.getvalue(), "image/png"),
        ("authorization.txt", b"Consent for private test composition and review.", "text/plain"),
    ):
        upload = client.post(
            "/api/v1/assets/upload",
            headers=headers,
            data={"workspace_id": workspace, "title": name},
            files={"file": (name, content, mime)},
        )
        assert upload.status_code == 201, upload.text
        asset_ids.append(upload.json()["id"])
    response = client.post(
        "/api/v1/studios/v1/identity-library/enrollments",
        headers=headers,
        json={
            "workspaceId": workspace,
            "requestKey": "native-cast-001",
            "mode": "face",
            "displayName": "Test portrait",
            "imageAssetId": asset_ids[0],
            "evidenceAssetId": asset_ids[1],
            "purpose": "Private native composition verification",
            "declared": True,
            "expiresAt": (datetime.now(UTC) + timedelta(days=7)).isoformat(),
        },
    )
    assert response.status_code == 201, response.text
    receipt = response.json()
    activate_for_binding_test(receipt)
    base = "/api/v1/studios/v1/projects"
    response = client.post(
        base,
        headers=headers,
        json={
            "workspaceId": workspace,
            "requestKey": "native-project-001",
            "title": "Uma composição com retrato",
            "objective": "Apresentar uma referência visual na composição da marca.",
            "audience": "Equipe de verificação",
            "format": "image",
            "identityVersionId": receipt["identityVersionId"],
        },
    )
    assert response.status_code == 201, response.text
    project = response.json()
    project = client.patch(
        f"{base}/{project['id']}",
        headers=headers,
        json={"expectedRevision": project["revision"], "directionId": "guide"},
    ).json()

    def render_here(document_id, request, key, db, user):
        from app.models import CreativeDocument

        job, _ = craft.create_render_job(db, db.get(CreativeDocument, document_id), request, user, key)
        result = craft.execute_render_job(db, job, lambda _: None, lambda: False)
        job.status, job.progress, job.result_payload = "succeeded", 100, result
        db.commit()
        return SimpleNamespace(id=job.id)

    # Only the queue transport is replaced; Rust migration and PNG rendering are real.
    monkeypatch.setattr(studio_department, "render_job", render_here)
    response = client.post(
        f"{base}/{project['id']}/produce", headers=headers, json={"expectedRevision": project["revision"]}
    )
    assert response.status_code == 200, response.text
    project = response.json()
    reopened = client.get(f"/api/v1/studios/v1/documents/{project['documentId']}", headers=headers).json()
    assert reopened["identityRef"]["id"] == receipt["identityVersionId"]
    assert reopened["nativeEditorState"]["engine"] == "photocraft"
    with SessionLocal() as db:
        result = db.get(StudioGenerationJob, project["jobId"]).result_payload
    exported = client.get(f"/api/v1/assets/{result['artifact']['assetId']}/content", headers=headers)
    assert exported.status_code == 200
    with Image.open(BytesIO(exported.content)) as image:
        assert image.size == (1080, 1350)
        assert image.convert("RGB").getpixel((800, 1000)) == (3, 171, 99)
        assert image.convert("RGB").getpixel((10, 10)) != (3, 171, 99)
    revoked = client.post(
        f"/api/v1/studios/v1/consents/{receipt['consentGrantId']}/revoke",
        headers=headers,
        json={"reason": "End of native acceptance"},
    )
    assert revoked.status_code == 200
    preview = client.post(
        f"/api/v1/studios/v1/documents/{project['documentId']}/craft/preview", headers=headers, json={"frame": 0}
    )
    assert preview.status_code == 422, preview.text
