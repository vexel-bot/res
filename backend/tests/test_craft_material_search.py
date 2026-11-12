import shutil
import time
import os

import httpx
import pytest
from PIL import Image

from conftest import register
from app.database import SessionLocal
from app.services.studios import craft_material_search, editing_resources


def test_public_discovery_records_provenance_and_acquires_only_registered_eligible_sources(client, monkeypatch, tmp_path):
    token, workspace = register(client, "public-material@example.com")
    actor = client.get("/api/v1/bootstrap", headers={"Authorization": "Bearer " + token}).json()["user"]["id"]
    page = {"pageid": 101, "title": "File:Orbit.png", "index": 1, "imageinfo": [{
        "mime": "image/png", "url": "https://upload.wikimedia.org/wikipedia/commons/a/ab/Orbit.png",
        "extmetadata": {"LicenseShortName": {"value": "CC0"}, "ImageDescription": {"value": "<b>Orbital image</b>"}},
    }]}
    unknown = {**page, "pageid": 102, "title": "File:Unknown.png", "imageinfo": [{**page["imageinfo"][0], "extmetadata": {}}]}
    private = {**page, "pageid": 103, "imageinfo": [{**page["imageinfo"][0], "url": "https://127.0.0.1/secret.png"}]}
    original = httpx.Client
    seen = []

    def respond(request):
        seen.append(request)
        assert request.url.host == "commons.wikimedia.org"
        assert request.url.params["gsrsearch"] == "orbital science"
        return httpx.Response(200, json={"query": {"pages": [page, unknown, private]}})

    monkeypatch.setattr(craft_material_search.httpx, "Client",
                        lambda **kwargs: original(transport=httpx.MockTransport(respond), **kwargs))
    source = tmp_path / "source.png"
    Image.new("RGB", (80, 80), "navy").save(source)

    def download(url, destination, hosts):
        assert url.startswith("https://upload.wikimedia.org/")
        shutil.copyfile(source, destination)
        return url

    monkeypatch.setattr(editing_resources, "download_resource", download)
    with SessionLocal() as db:
        hits = craft_material_search.public_images(db, workspace, actor, "orbital science", time.monotonic() + 30)
        db.commit()
        assert len(hits) == 2 and len(seen) == 1
        assert hits[0]["autoAcquire"] is True and hits[1]["autoAcquire"] is False
        assert hits[0]["description"] == "Orbital image"
        asset = editing_resources.acquire_registered_source(db, workspace, hits[0]["id"], actor, automatic=True)
        assert asset.media_type == "image/png"
        assert "CC0" in asset.object_metadata["editingResource"]["usageEvidence"]
        with pytest.raises(ValueError, match="manual_acquisition_required"):
            editing_resources.acquire_registered_source(db, workspace, hits[1]["id"], actor, automatic=True)
        with pytest.raises(ValueError, match="not_found"):
            editing_resources.acquire_registered_source(db, "another-workspace", hits[0]["id"], actor, automatic=True)


def test_nasa_fallback_is_identified_and_does_not_invent_clearance(client, monkeypatch):
    token, workspace = register(client, "nasa-material@example.com")
    actor = client.get("/api/v1/bootstrap", headers={"Authorization": "Bearer " + token}).json()["user"]["id"]
    original = httpx.Client
    seen = []

    def respond(request):
        seen.append(request.url.host)
        if request.url.host == "commons.wikimedia.org":
            return httpx.Response(403)
        assert request.url.host == "images-api.nasa.gov"
        return httpx.Response(200, json={"collection": {"items": [{
            "data": [{"nasa_id": "test-orbit", "title": "Orbital test", "center": "JSC", "description": "A satellite"}],
            "links": [{"render": "image", "href": "https://images-assets.nasa.gov/image/test-orbit/test-orbit~small.jpg"}],
        }]}})

    monkeypatch.setattr(craft_material_search.httpx, "Client",
                        lambda **kwargs: original(transport=httpx.MockTransport(respond), **kwargs))
    with SessionLocal() as db:
        hits = craft_material_search.public_images(db, workspace, actor, "orbit", time.monotonic() + 30)
        assert len(hits) == 1
        assert seen == ["commons.wikimedia.org", "images-api.nasa.gov"]
        assert hits[0]["fallbackAfter"] == "wikimedia_commons_unavailable"
        assert hits[0]["autoAcquire"] is False
        assert "metadata only" in hits[0]["coverage"]


@pytest.mark.skipif(os.environ.get("CLICKO_TEST_PUBLIC_MEDIA") != "1", reason="opt-in free public metadata probe")
def test_live_nasa_metadata_adapter(client):
    token, workspace = register(client, "live-free-material@example.com")
    actor = client.get("/api/v1/bootstrap", headers={"Authorization": "Bearer " + token}).json()["user"]["id"]
    with SessionLocal() as db:
        # Query NASA directly: do not retry the Commons robot-policy rejection in this environment.
        hits = craft_material_search._nasa_images(db, workspace, actor, "orbital satellite", time.monotonic() + 30)
        db.commit()
        assert hits and all(item["discoveryProvider"] == "nasa_images" for item in hits)
        assert all(item["autoAcquire"] is False for item in hits)
