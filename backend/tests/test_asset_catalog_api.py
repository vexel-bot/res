"""The global catalog is explicit summary; default list/detail keep full evidence."""
from datetime import UTC, datetime, timedelta

from conftest import register

from app.database import SessionLocal
from app.models import LibraryAsset


def test_catalog_and_full_detail_preserve_fields_and_scope(client):
    token, workspace = register(client, "catalog-owner@example.com")
    outsider, outside = register(client, "catalog-outsider@example.com")
    headers = {"Authorization": "Bearer " + token}
    stamp = datetime(2026, 10, 5, tzinfo=UTC)
    with SessionLocal() as db:
        for index, (identifier, metadata, scope, state) in enumerate([
            ("original", {"unconsumed": "x" * 100_000}, workspace, "active"),
            ("derivative", {"sourceAssetId": "original", "visualReview": "pending",
                            "editingResource": {"rights": "unknown"}}, workspace, "active"),
            ("null", {"sourceAssetId": None}, workspace, "active"),
            ("deleted", {"sourceAssetId": "original"}, workspace, "deleted"),
            ("foreign", {"secret": "outside tenant"}, outside, "active"),
        ]):
            db.add(LibraryAsset(id=identifier, workspace_id=scope, title="Asset " + identifier,
                asset_type="image", tags=["tag"], media_type="image/png", checksum_sha256="a" * 64,
                storage_key="unit/" + identifier + ".png", storage_backend="local", object_metadata=metadata,
                lifecycle_status=state, created_at=stamp + timedelta(seconds=index)))
        db.commit()
    legacy_response = client.get(f"/api/v1/assets?workspace_id={workspace}", headers=headers)
    catalog_response = client.get(f"/api/v1/assets/catalog?workspace_id={workspace}", headers=headers)
    assert legacy_response.status_code == catalog_response.status_code == 200
    legacy, catalog = legacy_response.json(), catalog_response.json()
    assert [a["id"] for a in legacy] == [a["id"] for a in catalog] == ["null", "derivative", "original"]
    for full, summary in zip(legacy, catalog, strict=True):
        assert {k: v for k, v in summary.items() if k not in {
            "metadata", "metadataDetail", "schemaVersion", "fullMetadataPath"}} == {
            k: v for k, v in full.items() if k != "metadata"}
        assert summary["schemaVersion"] == "studio.asset-catalog-item.v1" and summary["metadataDetail"] == "summary"
        assert summary["metadata"] == ({"sourceAssetId": full["metadata"]["sourceAssetId"]}
                                      if "sourceAssetId" in full["metadata"] else {})
        detail = client.get(summary["fullMetadataPath"], headers=headers)
        assert detail.status_code == 200 and detail.json() == full
        outsider_headers = {"Authorization": "Bearer " + outsider}
        assert client.get(summary["fullMetadataPath"], headers=outsider_headers).status_code == 404
    assert legacy[2]["metadata"]["unconsumed"] == "x" * 100_000
    assert len(legacy_response.content) - len(catalog_response.content) > 99_000
    assert client.get("/api/v1/assets/deleted", headers=headers).status_code == 404
    assert client.get("/api/v1/assets/foreign", headers=headers).status_code == 404
    assert client.get(f"/api/v1/assets/catalog?workspace_id={workspace}").status_code == 401
    assert client.get(f"/api/v1/assets/catalog?workspace_id={outside}", headers=headers).status_code == 404
