"""Native direction hands only registered, authorized media to EffectCraft."""
import shutil
from types import SimpleNamespace

import pytest
from conftest import register
from PIL import Image
from sqlalchemy import select

from app.config import get_settings
from app.database import SessionLocal
from app.domain.studios.editing_resources import RegisteredEditingSourceV1
from app.models import Membership
from app.services.studios import craft_direction, editing_resources


def test_director_inventory_keeps_editorial_metadata_and_uses_checksum_bound_ingest(client):
    from app.models import LibraryAsset, StudioMediaIngest
    from app.services.studios.craft_agent import registered_assets

    _, workspace = register(client, "inventory@example.com")
    _, foreign = register(client, "inventory-foreign@example.com")
    with SessionLocal() as db:
        actor = db.scalar(select(Membership.user_id).where(Membership.workspace_id == workspace))
        resource = LibraryAsset(workspace_id=workspace, title="Portal abre", asset_type="video",
                                checksum_sha256="a" * 64, object_metadata={"editingResource": {
                                    "description": "A porta revela o espaço", "editorialFunction": "reveal",
                                    "technical": {"durationMicroseconds": 3_000_000, "probe": {
                                        "videoStreams": [{"width": 540, "height": 960}], "audioStreams": []}}}})
        upload = LibraryAsset(workspace_id=workspace, title="Filmagem", asset_type="video", checksum_sha256="b" * 64)
        other = LibraryAsset(workspace_id=foreign, title="Private", asset_type="video", checksum_sha256="c" * 64)
        db.add_all([resource, upload, other])
        db.flush()
        db.add(StudioMediaIngest(workspace_id=workspace, asset_id=upload.id, status="ready", requested_by=actor, idempotency_key="current",
                                media_info={"checksumSha256": "b" * 64, "durationMicroseconds": 4_000_000,
                                            "videoStreams": [{"width": 1920, "height": 1080}], "audioStreams": [{}]}))
        db.add(StudioMediaIngest(workspace_id=workspace, asset_id=upload.id, status="ready", requested_by=actor, idempotency_key="stale",
                                media_info={"checksumSha256": "d" * 64, "durationMicroseconds": 9_000_000}))
        db.flush()
        manifests = [SimpleNamespace(asset_id=asset.id, media_type="video/mp4") for asset in [resource, upload, other]]
        known, ingested, inaccessible = registered_assets(db, workspace, manifests)
        assert known["description"] == "A porta revela o espaço" and known["durationSeconds"] == 3
        assert known["width"] == 540 and known["hasAudio"] is False
        assert ingested["durationSeconds"] == 4 and ingested["width"] == 1920 and ingested["hasAudio"]
        assert inaccessible["title"] is None and "checksumSha256" not in inaccessible


def test_source_acquisition_stages_working_copy_with_provenance(client, tmp_path, monkeypatch):
    _token, workspace = register(client, "craft-direction-material@example.com")
    _other_token, other_workspace = register(client, "craft-direction-other@example.com")
    monkeypatch.setattr(get_settings(), "storage_path", str(tmp_path / "storage"))
    image_file = tmp_path / "source.jpg"
    Image.new("RGB", (1800, 1000), "#33475b").save(image_file)
    calls = []

    def download(url, destination, _hosts):
        calls.append(url)
        shutil.copyfile(image_file, destination)
        return url

    monkeypatch.setattr(editing_resources, "download_resource", download)
    with SessionLocal() as db:
        user_id = db.scalar(select(Membership.user_id).where(Membership.workspace_id == workspace))
        def register_image(space, name, enabled):
            return editing_resources.register_source(db, space, RegisteredEditingSourceV1(
                title=name, kind="image", url=f"https://assets.example.org/{name}.jpg",
                source_url="https://assets.example.org/credits", usage_evidence="Workspace test authorization",
                auto_acquire=enabled,
            ), user_id)
        approved = register_image(workspace, "approved", True)
        manual = register_image(workspace, "manual", False)
        foreign = register_image(other_workspace, "foreign", True)
        db.commit()
        job = SimpleNamespace(workspace_id=workspace, request_payload={"assetIds": []}, result_payload={})
        draft = SimpleNamespace(directory=tmp_path / "draft", params={"media": []})
        actor = SimpleNamespace(id=user_id)
        manifests = []
        for source, error in ((manual, "resource_source_manual_acquisition_required"), (foreign, "resource_source_not_found")):
            with pytest.raises(ValueError, match=error):
                craft_direction.acquire_material(db, job, actor, draft, manifests, source["id"], 1280)
        assert calls == []
        assert {c["id"] for c in craft_direction.source_candidates(db, workspace, "")} == {approved["id"], manual["id"]}
        added = craft_direction.acquire_material(db, job, actor, draft, manifests, approved["id"], 1280)
        assert added["originalAssetId"] != added["assetId"]
        assert added["provenance"]["sourceUrl"] == "https://assets.example.org/credits"
        assert added["provenance"]["technical"]["width"] == 1280
        assert [m.asset_id for m in manifests] == craft_direction.media_ids(job) == [added["assetId"]]
        assert craft_direction.acquire_material(db, job, actor, draft, manifests, approved["id"], 1280) == added
        assert len(calls) == 1 and len(draft.params["media"]) == 1
