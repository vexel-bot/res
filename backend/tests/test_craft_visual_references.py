"""Real reference pixels are analysis evidence, not project production assets."""

import base64
import hashlib
import json
import shutil
from copy import deepcopy
from io import BytesIO

import pytest
from conftest import register
from PIL import Image
from sqlalchemy import func, select

from app.database import SessionLocal
from app.models import CreativeDocument, LibraryAsset, StudioGenerationJob, User
from app.providers.studios.universal_llm import UniversalLLMPlanner
from app.services.object_storage import get_object_storage
from app.services.studios import craft, craft_direction, craft_references, editing_resources


def identity(client, email):
    token, workspace = register(client, email)
    with SessionLocal() as db:
        user_id = db.scalar(select(User.id).where(User.email == email))
    return token, workspace, user_id


def forbidden(*args, **kwargs):
    raise AssertionError("Reference evidence must not call a paid model")


def test_reference_index_is_additive_and_preserves_legacy_evidence():
    before = deepcopy(craft_direction.repertoire())
    index = craft_references.reference_index()
    assert {row["id"] for row in index} == {
        "research.model.cinematic_motif", "research.model.product_in_action",
        "research.model.layered_collage", "orbita.quality.baseline",
    }
    assert all(row["role"] == "analysis/reference_only" for row in index)
    assert all(row["coverage"]["fullMotion"] == "not_audited" for row in index)
    originals = [row for row in index if row["id"].startswith("research.model.")]
    assert all(row["coverage"]["audio"] == "not_audited" for row in originals)
    assert before == craft_direction.repertoire()
    assert len(craft_references.evidence_version()) == 64


def test_all_reference_images_return_real_bytes_without_changing_project(client, monkeypatch):
    monkeypatch.setattr(UniversalLLMPlanner, "craft_turn", forbidden)
    token, workspace, user_id = identity(client, "reference-pixels@example.com")
    headers = {"Authorization": "Bearer " + token}
    response = client.post("/api/v1/studios/v1/documents", headers=headers, json={
        "workspaceId": workspace, "title": "Reference isolation", "contentType": "video",
        "brief": {"objective": "Read evidence without changing an edit", "audience": "QA"},
        "composition": {"pages": [{"id": "main", "width": 320, "height": 320,
                                    "durationMs": 2000, "layers": []}]},
    })
    assert response.status_code == 201, response.text
    document = response.json()
    with SessionLocal() as db:
        for row in craft_references.reference_index():
            result = craft_references.inspect_reference(db, workspace, user_id, row["id"])
            assert len(result["blocks"]) == 2
            assert result["blocks"][0]["type"] == "text"
            text = json.loads(result["blocks"][0]["text"])
            image = result["blocks"][1]
            assert image["source"]["media_type"] == "image/jpeg"
            data = base64.b64decode(image["source"]["data"], validate=True)
            assert hashlib.sha256(data).hexdigest() == text["sha256"]
            source = craft_references._evidence_file(craft_references._entry(row["id"]))
            assert data == source.read_bytes()
            with Image.open(BytesIO(data)) as actual:
                assert actual.width > 300 and actual.height > 300
                actual.verify()
            assert text["role"] == "analysis/reference_only"
            record = db.get(CreativeDocument, document["documentId"])
            asset_id = text["assetId"]
            assert editing_resources.catalog(db, workspace, asset_id=asset_id) == []
            with pytest.raises(ValueError, match="resource_analysis_only"):
                editing_resources.attach_resource(db, record, asset_id, document["revision"])
            with pytest.raises(ValueError, match="craft_analysis_asset_not_production"):
                with craft.workspace_files(db, record, None, extra_asset_ids=[asset_id]):
                    pytest.fail("Analysis evidence entered the production manifest")
            assert text["productionUse"] == "not_authorized"
            assert text["workspaceId"] == workspace
            again = craft_references.inspect_reference(db, workspace, user_id, row["id"])
            assert again["reference"]["assetId"] == text["assetId"]
            asset = db.get(LibraryAsset, text["assetId"])
            assert asset.object_metadata["rightsStatus"] == "restricted"
        assert db.scalar(select(func.count()).select_from(LibraryAsset)) == 4
        assert db.scalar(select(func.count()).select_from(StudioGenerationJob)) == 0
        db.commit()
    current = client.get("/api/v1/studios/v1/documents/" + document["documentId"], headers=headers)
    assert current.status_code == 200, current.text
    assert current.json()["revision"] == document["revision"]
    assert current.json()["assets"] == document["assets"]
    assert current.json().get("nativeEditorState") == document.get("nativeEditorState")


def test_reference_registration_is_workspace_scoped_and_requires_membership(client):
    _, first, first_user = identity(client, "reference-first@example.com")
    _, second, second_user = identity(client, "reference-second@example.com")
    ref_id = "research.model.cinematic_motif"
    with SessionLocal() as db:
        first_image = craft_references.inspect_reference(db, first, first_user, ref_id)
        with pytest.raises(ValueError, match="craft_reference_workspace_forbidden"):
            craft_references.inspect_reference(db, first, second_user, ref_id)
        second_image = craft_references.inspect_reference(db, second, second_user, ref_id)
        assert first_image["reference"]["assetId"] != second_image["reference"]["assetId"]
        assert first_image["reference"]["sha256"] == second_image["reference"]["sha256"]
        assert db.get(LibraryAsset, first_image["reference"]["assetId"]).workspace_id == first
        assert db.get(LibraryAsset, second_image["reference"]["assetId"]).workspace_id == second


def test_reference_rejects_tampered_stored_pixels(client):
    _, workspace, user_id = identity(client, "reference-tamper@example.com")
    with SessionLocal() as db:
        result = craft_references.inspect_reference(db, workspace, user_id, "research.model.cinematic_motif")
        asset = db.get(LibraryAsset, result["reference"]["assetId"])
        storage = get_object_storage(asset.storage_backend)
        path = storage.local_path(asset.storage_key)
        path.write_bytes(path.read_bytes() + b"tampered")
        with pytest.raises(ValueError, match="craft_reference_asset_checksum_mismatch"):
            craft_references.inspect_reference(db, workspace, user_id, "research.model.cinematic_motif")


def test_reference_rejects_tampered_pack_before_registering(client, monkeypatch, tmp_path):
    _, workspace, user_id = identity(client, "reference-pack-tamper@example.com")
    entry = craft_references._entry("research.model.cinematic_motif")
    target = tmp_path / entry["file"]
    shutil.copyfile(craft_references.EVIDENCE_ROOT / entry["file"], target)
    target.write_bytes(target.read_bytes() + b"tampered")
    monkeypatch.setattr(craft_references, "EVIDENCE_ROOT", tmp_path)
    with SessionLocal() as db:
        with pytest.raises(ValueError, match="craft_reference_evidence_checksum_mismatch"):
            craft_references.inspect_reference(db, workspace, user_id, entry["id"])
        assert db.scalar(select(func.count()).select_from(LibraryAsset)) == 0


@pytest.mark.parametrize("identifier", ["../../private", "/tmp/private.jpg", "file:///tmp/image.jpg", "", None])
def test_reference_tool_accepts_only_registered_identifiers(client, identifier):
    _, workspace, user_id = identity(client, "reference-identifiers@example.com")
    with SessionLocal() as db:
        with pytest.raises(ValueError, match="craft_reference_(not_found|id_invalid)"):
            craft_references.inspect_reference(db, workspace, user_id, identifier)
        assert db.scalar(select(func.count()).select_from(LibraryAsset)) == 0


def test_catalog_cannot_escape_curated_evidence_root(client, monkeypatch):
    _, workspace, user_id = identity(client, "reference-path@example.com")
    catalog = deepcopy(craft_references._catalog())
    catalog["references"][0]["file"] = "../outside.jpg"
    monkeypatch.setattr(craft_references, "_catalog", lambda: catalog)
    with SessionLocal() as db:
        with pytest.raises(ValueError, match="craft_reference_catalog_path_invalid"):
            craft_references.inspect_reference(db, workspace, user_id, catalog["references"][0]["id"])


def test_baseline_preserves_feedback_and_delivery_limitations(client):
    _, workspace, user_id = identity(client, "reference-baseline@example.com")
    with SessionLocal() as db:
        result = craft_references.inspect_reference(db, workspace, user_id, "orbita.quality.baseline")
        ref = result["reference"]
        assert ref["coverage"]["audio"] == "absent"
        assert ref["state"] == "positive_progress_needs_revision"
        assert not ref["baseline"]["ownerFeedback"]["finalAdvertisementApproved"]
        assert not ref["baseline"]["ownerFeedback"]["audienceStudy"]
        assert "recovery" in ref["baseline"]["exportOrigin"]
        assert ref["baseline"]["videoSha256"] == "040484f64c32e9d7d47aff43b5d1fe69626382dfc598ae0b217296ec7f490391"
