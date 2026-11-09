"""Real storage and database; provider output is a generated color fixture."""

from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image
from sqlalchemy import select
from test_studio_identity_library import PROJECTS, activate_for_binding_test, enroll, setup

from app.database import SessionLocal
from app.domain.studios.appearance_image import AppearanceImageResultV1, AppearanceModelManifestV1, canonical_digest
from app.domain.studios.contracts import CreateGenerationJobRequest
from app.domain.studios.providers import APPEARANCE_IMAGE_PROVIDERS
from app.models import (
    CreativeDocument,
    LibraryAsset,
    StudioConsentGrant,
    StudioGenerationJob,
    StudioModelRegistration,
    StudioProviderRegistration,
    User,
    WorkspaceResource,
)
from app.routers import studio_department
from app.services.object_storage import LocalObjectStorage, sha256_file
from app.services.studios import jobs as job_service
from app.services.studios import project_appearance
from app.services.studios.compatibility import record_to_contract
from app.services.studios.jobs import create_job, execute_job_once


@pytest.mark.parametrize("revoke", [False, True])
def test_private_output_requires_current_consent_and_approved_provider(client, tmp_path, monkeypatch, revoke):
    headers, enrollment = setup(client)
    receipt = enroll(client, headers, enrollment)
    activate_for_binding_test(receipt)
    storage = LocalObjectStorage(str(tmp_path / "storage"))
    monkeypatch.setattr(project_appearance, "get_object_storage", lambda *_: storage)
    image = tmp_path / "input.png"
    Image.new("RGB", (64, 64), "blue").save(image)
    key = f"{enrollment['workspaceId']}/raw/fixture.png"
    stored = storage.put_file(image, key=key, media_type="image/png")
    scene_key = f"{enrollment['workspaceId']}/raw/scene.png"
    scene_stored = storage.put_file(image, key=scene_key, media_type="image/png")
    with SessionLocal() as db:
        portrait = db.get(LibraryAsset, enrollment["imageAssetId"])
        portrait.storage_key, portrait.storage_backend = key, "local"
        portrait.checksum_sha256, portrait.size_bytes = stored.checksum_sha256, stored.size_bytes
        scene = LibraryAsset(
            workspace_id=enrollment["workspaceId"],
            title="Cena original",
            asset_type="upload",
            storage_key=scene_key,
            storage_backend="local",
            media_type="image/png",
            checksum_sha256=scene_stored.checksum_sha256,
            size_bytes=scene_stored.size_bytes,
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
            "requestKey": "appearance-execution-001",
            "title": "Teste de imagem",
            "objective": "Uma mensagem para a marca.",
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
    availability = client.get(f"{PROJECTS}/{project['id']}/appearance", headers=headers).json()["availability"]
    assert availability == {"available": False, "reason": "appearance_provider_unavailable"}
    manifest = AppearanceModelManifestV1.model_validate_json(
        (Path(__file__).resolve().parents[2] / "workers/identity-image/model-assets.v1.json").read_text(
            encoding="utf-8"
        )
    )

    class FixtureProvider:
        name = "candidate.qwen-image-edit-2511"
        version = "fixture-explicit-not-qualified"

        def __init__(self):
            self.manifest = manifest
            self.calls = 0

        def generate(self, request, reference, scene, output, progress, is_cancelled):
            self.calls += 1
            assert sha256_file(reference) == request.reference_checksum_sha256
            assert scene is not None and sha256_file(scene) == request.source_checksum_sha256
            Image.new("RGB", (request.width, request.height), "green").save(output)
            if revoke:
                with SessionLocal() as other:
                    other.get(StudioConsentGrant, receipt["consentGrantId"]).status = "revoked"
                    other.commit()
            return AppearanceImageResultV1(
                provider_version=self.version,
                request_digest_sha256=canonical_digest(request),
                model_manifest_digest_sha256=canonical_digest(manifest),
                identity_ref=request.identity_ref,
                reference_checksum_sha256=request.reference_checksum_sha256,
                source_checksum_sha256=request.source_checksum_sha256,
                artifact_checksum_sha256=sha256_file(output),
                width=request.width,
                height=request.height,
                wall_seconds=1,
            )

    provider = FixtureProvider()
    monkeypatch.setitem(APPEARANCE_IMAGE_PROVIDERS, provider.name, provider)
    monkeypatch.setattr(job_service, "enqueue_job_task", lambda *args, **kwargs: None)
    with SessionLocal() as db:
        registration = StudioProviderRegistration(
            capability="appearance_image",
            provider=provider.name,
            provider_version=provider.version,
            source_url="https://example.invalid/fixture",
            source_revision="fixture",
            code_license="MIT",
            status="approved",
            manifest={"benchmarkStatus": "passed", "workerAdvertised": True},
        )
        db.add(registration)
        db.flush()
        db.add(
            StudioModelRegistration(
                provider_registration_id=registration.id,
                name="Fixture",
                version="fixture",
                digest_sha256=canonical_digest(manifest),
                model_license="MIT",
                commercial_use="approved",
                languages=["pt-BR"],
                capabilities=["appearance_image"],
                status="approved",
                manifest={"benchmarkStatus": "passed"},
            )
        )
        db.commit()
        row = db.get(WorkspaceResource, project["id"])
        plan = project_appearance.plan_project_appearance(db, row, "A pessoa na imagem escolhida")
        user = db.scalar(select(User).where(User.email == "cast@example.com"))
        request = CreateGenerationJobRequest(
            workspace_id=enrollment["workspaceId"],
            job_type="appearance_image",
            provider=provider.name,
            identity_version_id=receipt["identityVersionId"],
            request={"plan": plan},
        )
        with pytest.raises(ValueError, match="use_project_appearance_endpoint"):
            create_job(db, request, "appearance-job-key-001", user)
        bridged = SimpleNamespace(id=user.id, password_hash="!session-bridge-only")
        with pytest.raises(ValueError, match="commercial_media_admission_required"):
            create_job(db, request, "appearance-job-key-001", bridged, trusted_appearance_envelope=True)
        admission = {"id": "c" * 64, "documentId": row.id, "key": "bridge-job-key-001", "operation": "generate_image"}
        bridge_request = request.model_copy(update={"request": {"plan": plan, "commercialAdmission": admission}})
        bridge_job, created = create_job(
            db,
            bridge_request,
            admission["key"],
            bridged,
            trusted_appearance_envelope=True,
            commercial_admission=admission,
        )
        assert created and bridge_job.request_payload["commercialAdmission"] == admission
        with pytest.raises(ValueError, match="commercial_media_admission_required"):
            create_job(
                db,
                bridge_request,
                "different-key-001",
                bridged,
                trusted_appearance_envelope=True,
                commercial_admission=admission,
            )
        endpoint = f"{PROJECTS}/{project['id']}/appearance"
        job_headers = {**headers, "Idempotency-Key": "appearance-job-key-001"}
        body = {
            "expectedRevision": project["revision"],
            "operation": "generate_image",
            "direction": "A pessoa na imagem escolhida",
            "seed": 0,
            "planDigestSha256": plan["planDigestSha256"],
        }
        submitted = client.post(endpoint, headers=job_headers, json=body)
        assert submitted.status_code == 202, submitted.text
        replay = client.post(endpoint, headers=job_headers, json=body)
        assert replay.status_code == 202 and replay.json()["id"] == submitted.json()["id"]
        job = db.get(StudioGenerationJob, submitted.json()["id"])
        assert job.queue_name == "studio.gpu.vision" and job.max_attempts == 1
        if revoke:
            assert execute_job_once(db, job) == "failed"
            assert set((storage.root / enrollment["workspaceId"]).rglob("*.png")) == {
                storage.root / key,
                storage.root / scene_key,
            }
        else:
            assert execute_job_once(db, job) == "succeeded", job.error_message
            asset = db.get(LibraryAsset, job.result_payload["assetId"])
            assert asset.object_metadata["reviewRequired"] is True
            assert asset.object_metadata["casting"]["identity"]["id"] == receipt["identityVersionId"]
            assert storage.exists(asset.storage_key)
            recovered = project_appearance.execute_project_appearance(
                db, row, plan, provider.name, lambda _: None, lambda: False, generation_job_id=job.id
            )
            assert recovered.id == asset.id and provider.calls == 1
            state = client.get(endpoint, headers=headers)
            assert state.status_code == 200 and state.json()["job"]["id"] == job.id
            assert state.json()["availability"] == {"available": True, "reason": None}
            stale = client.post(endpoint + "/select", headers=headers, json={"expectedRevision": 1, "jobId": job.id})
            assert stale.status_code == 409
            chosen = client.post(
                endpoint + "/select", headers=headers, json={"expectedRevision": project["revision"], "jobId": job.id}
            )
            assert chosen.status_code == 200, chosen.text
            assert chosen.json()["appearanceSelection"]["assetId"] == asset.id
            db.refresh(row)
            assert (
                project_appearance.selected_appearance_asset(db, row, row.payload["appearanceSelection"]).id == asset.id
            )
            assert row.payload.get("sourceAssetId") == scene_id
            row.payload = {**row.payload, "directionId": "demonstrate"}
            db.flush()
            with pytest.raises(ValueError, match="appearance_selected_result_changed"):
                project_appearance.selected_appearance_asset(db, row, row.payload["appearanceSelection"])
            db.rollback()
            monkeypatch.setattr(
                studio_department, "record_to_contract", lambda doc: SimpleNamespace(native_editor_state=True)
            )
            monkeypatch.setattr(studio_department, "render_job", lambda *args: SimpleNamespace(id="fixture-render"))
            production = client.post(
                f"{PROJECTS}/{project['id']}/produce",
                headers=headers,
                json={"expectedRevision": chosen.json()["revision"]},
            )
            assert production.status_code == 200, production.text
            with SessionLocal() as verify:
                document = record_to_contract(verify.get(CreativeDocument, production.json()["documentId"]))
                layers = document.composition.pages[0].layers
                assert (
                    next(layer for layer in layers if layer.id == "source-material").properties["assetId"] == asset.id
                )
                scene_layer = next(layer for layer in layers if layer.id == "source-material")
                body_layer = next(layer for layer in layers if layer.id.startswith("body-"))
                assert (scene_layer.width, scene_layer.height) == (600, 600)
                assert body_layer.x + body_layer.width <= scene_layer.x
                assert not any(layer.id == "cast-portrait" for layer in layers)
                assert {item.id for item in document.assets} >= {asset.id, scene_id}
