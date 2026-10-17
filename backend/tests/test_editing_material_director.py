# Fixtures use the existing studio integration boundary.
# ruff: noqa: F401, F811
from conftest import register
from test_contextual_editing import create_plan, media, project
from test_editing_resources import headers, png, upload


def need(**updates):
    return {
        "id": "brand",
        "clipId": "clip",
        "kind": "logo",
        "query": "Marca arbitrária",
        "purpose": "Identificar a origem visual sem inventar uma marca",
        **updates,
    }


def test_general_material_request_resolves_catalog_and_compiles(client, project):
    asset = upload(client, project).json()["id"]
    plan = create_plan(client, project, materialNeeds=[need()])
    assert plan["status"] == "ready", plan["blockers"]
    assert plan["materialRequests"][0]["resolvedAssetId"] == asset
    assert any(o["kind"] == "insert_broll" for o in plan["operations"])


def test_missing_material_has_scene_purpose_and_blocks(client, project):
    plan = create_plan(client, project, materialNeeds=[need(query="Cena de jogo ao entardecer", kind="video")])
    assert plan["status"] == "awaiting_choice"
    assert plan["materialRequests"][0]["clipId"] == "clip"
    assert plan["materialRequests"][0]["generationAllowed"]
    assert all(
        a["action"] == "wait"
        for b in plan["blockers"]
        if b["code"] == "editing_material_required"
        for a in b["alternatives"]
    )


def test_approximate_logo_does_not_satisfy_official_requirement(client, project):
    upload(client, project)
    plan = create_plan(client, project, materialNeeds=[need(officialRequired=True)])
    assert plan["status"] == "awaiting_choice"
    assert not plan["materialRequests"][0]["generationAllowed"]


def register_source(client, project, **updates):
    response = client.post(
        f"/api/v1/studios/v1/editing/resource-sources?workspace_id={project['workspace']}",
        headers=headers(project),
        json={
            "kind": "logo",
            "title": "Marca arbitrária",
            "url": "https://brand.example/logo.png",
            "official": True,
            "usageEvidence": "Arquivo fornecido pelo cliente",
            "autoAcquire": True,
            **updates,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_registered_source_downloads_only_when_authorized_and_is_tenant_scoped(client, project, monkeypatch):
    # Identical bytes from an unverified upload cannot mask an official source.
    upload(client, project)
    source = register_source(client, project)
    seen = []

    def download(url, destination, hosts):
        seen.append(url)
        assert "brand.example" in hosts
        destination.write_bytes(png())
        return url

    monkeypatch.setattr("app.services.studios.editing_resources.download_resource", download)
    plan = create_plan(client, project, materialNeeds=[need(officialRequired=True)])
    assert plan["status"] == "ready", plan["blockers"]
    assert plan["materialRequests"][0]["resolvedAssetId"]
    assert len(seen) == 1
    token, workspace = register(client, "other-director@example.com")
    denied = client.post(
        f"/api/v1/studios/v1/editing/resource-sources/{source['id']}/acquire?workspace_id={workspace}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert denied.status_code == 422
    assert len(seen) == 1


def test_registered_source_does_not_download_without_auto_acquire(client, project, monkeypatch):
    register_source(client, project, autoAcquire=False)
    monkeypatch.setattr(
        "app.services.studios.editing_resources.download_resource",
        lambda *args: (_ for _ in ()).throw(AssertionError("unexpected download")),
    )
    plan = create_plan(client, project, materialNeeds=[need()])
    assert plan["status"] == "awaiting_choice"
    assert plan["materialRequests"][0]["sources"]


def test_transcript_revision_change_rejected_before_model(client, project, monkeypatch):
    from test_contextual_editing import attach_transcript
    from test_editing_resources import enable, job

    from app.database import SessionLocal
    from app.models import StudioGenerationJob, StudioTranscript
    from app.providers.studios.gemini_editing import GeminiEditingProvider
    from app.services.studios.jobs import execute_job_once

    transcript = attach_transcript(project)
    enable(monkeypatch)
    identifier = job(
        client,
        project,
        operation="plan",
        direction={
            "expectedDocumentRevision": 1,
            "intent": {"objective": "Explicar"},
            "beats": [
                {
                    "id": "b",
                    "clipId": "clip",
                    "purpose": "Explicar",
                    "transcriptId": transcript.id,
                    "transcriptRevision": 1,
                    "captionFromTranscript": True,
                }
            ],
        },
    )
    monkeypatch.setattr(
        GeminiEditingProvider, "plan", lambda *args: (_ for _ in ()).throw(AssertionError("unexpected call"))
    )
    with SessionLocal() as db:
        db.get(StudioTranscript, transcript.id).revision = 2
        db.commit()
        record = db.get(StudioGenerationJob, identifier)
        assert execute_job_once(db, record) == "failed"
        assert "transcript_conflict" in record.error_message


def test_static_svg_logo_is_converted_to_png_with_provenance(client, project):
    svg = (
        b'<svg xmlns="http://www.w3.org/2000/svg" width="80" height="40">'
        b'<rect x="20" width="40" height="40" fill="red"/></svg>'
    )
    response = upload(client, project, data=svg)
    assert response.status_code == 200, response.text
    from PIL import Image

    from app.database import SessionLocal
    from app.models import LibraryAsset
    from app.services.object_storage import get_object_storage

    with SessionLocal() as db:
        asset = db.get(LibraryAsset, response.json()["id"])
        assert asset.media_type == "image/png"
        assert asset.object_metadata["editingResource"]["technical"]["vectorSource"]["sourceChecksum"]
        with get_object_storage(asset.storage_backend).materialize(asset.storage_key) as path:
            image = Image.open(path).convert("RGBA")
            assert image.size == (80, 40)
            assert image.getpixel((0, 20))[3] == 0
            assert image.getpixel((40, 20)) == (255, 0, 0, 255)


def test_svg_scripts_and_external_references_are_rejected(client, project):
    for content in [
        b"<script>alert(1)</script>",
        b'<image href="http://127.0.0.1/private"/>',
        b'<rect width="30" height="30" style="fill:url(https://internal/x)"/>',
    ]:
        response = upload(
            client,
            project,
            data=b'<svg xmlns="http://www.w3.org/2000/svg" width="80" height="40">' + content + b"</svg>",
        )
        assert response.status_code == 422, response.text
