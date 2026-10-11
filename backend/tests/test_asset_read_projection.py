"""Sparse asset reads retain scope, nulls, session semantics and full evidence."""
from types import SimpleNamespace

import pytest
from sqlalchemy import event, select

from app.database import SessionLocal
from app.models import LibraryAsset, Workspace
from app.services.studios.asset_read_projection import project_asset, project_assets
from app.services.studios.editing_resources import catalog


@pytest.fixture
def db():
    with SessionLocal() as session:
        session.add(Workspace(id="workspace", name="Projection test"))
        session.commit()
        yield session


def asset(db, identifier="asset", metadata=None, **extra):
    item = LibraryAsset(id=identifier, workspace_id="workspace", title="Café com ação", asset_type="video",
                        media_type="video/mp4", tags=["ação"], storage_key=f"unit/{identifier}.mp4",
                        checksum_sha256="a" * 64, object_metadata=metadata if metadata is not None else {}, **extra)
    db.add(item)
    db.commit()
    db.expunge_all()


def test_sparse_values_preserve_presence_types_and_do_not_create_orm_identity(db):
    asset(db, metadata={"presentNull": None, "flag": False, "count": 0, "text": "á ação",
                        "nested": {"leaf": {"rights": "unknown", "items": [1, True, None]}},
                        "unconsumed": "x" * 100_000})
    paths = [("missing",), ("presentNull",), ("flag",), ("count",), ("text",), ("nested", "leaf")]
    loaded = []

    def on_load(instance, context):
        loaded.append(instance.id)

    event.listen(LibraryAsset, "load", on_load)
    try:
        view = project_asset(db, "asset", paths)
    finally:
        event.remove(LibraryAsset, "load", on_load)
    assert view.object_metadata == {"presentNull": None, "flag": False, "count": 0, "text": "á ação",
                                    "nested": {"leaf": {"rights": "unknown", "items": [1, True, None]}}}
    assert view.object_metadata["flag"] is False and type(view.object_metadata["count"]) is int
    assert loaded == []
    original = db.get(LibraryAsset, "asset")
    assert original.object_metadata["unconsumed"] == "x" * 100_000
    assert view.title == original.title and view.checksum_sha256 == original.checksum_sha256


def test_loaded_nested_mutations_use_original_orm_path(db):
    asset(db, metadata={"editingResource": {"kind": "image", "description": "old"}})
    loaded = db.get(LibraryAsset, "asset")
    loaded.object_metadata["editingResource"]["description"] = "unflushed action"
    assert loaded not in db.dirty
    assert project_assets(db, select(LibraryAsset), [("editingResource",)]) is None
    assert catalog(db, "workspace")[0]["resource"]["description"] == "unflushed action"


@pytest.mark.parametrize("metadata", [{"nested": None}, {"nested": [1]}, {"nested": "invalid"}])
def test_malformed_ancestor_containers_fall_back_without_replacing_evidence(db, metadata):
    asset(db, metadata=metadata)
    assert project_assets(db, select(LibraryAsset), [("nested", "leaf")]) is None
    assert project_asset(db, "asset", [("nested", "leaf")]).object_metadata == metadata


def test_non_sqlite_dialect_keeps_prior_reader():
    fake = SimpleNamespace(get_bind=lambda: SimpleNamespace(dialect=SimpleNamespace(name="postgresql")))
    assert project_assets(fake, select(LibraryAsset), [("field",)]) is None


@pytest.mark.parametrize("value", [2 ** 70, -0.0])
def test_scalar_precision_edges_retain_original_json_value(db, value):
    import json

    asset(db, metadata={"scalar": value})
    assert project_assets(db, select(LibraryAsset), [("scalar",)]) is None
    current = project_asset(db, "asset", [("scalar",)]).object_metadata["scalar"]
    assert json.dumps(current) == json.dumps(value)


def test_catalog_preserves_rank_filter_fields_and_null_failure(db):
    asset(db, "first", {"editingResource": {"kind": "video", "description": "Mão abre o café"},
                        "generationJobId": "job", "visualReview": "pending", "unconsumed": "x" * 100_000})
    asset(db, "second", {"editingResource": {"kind": "font", "description": "Tipografia"}})
    result = catalog(db, "workspace", "café", "video", asset_id="first")
    assert result == [{"relevanceScore": 5, "id": "first", "title": "Café com ação", "mediaType": "video/mp4",
                      "checksum": "a" * 64, "resource": {"kind": "video", "description": "Mão abre o café"},
                      "reviewStatus": "pending", "generationJobId": "job", "url": "/api/v1/assets/first/content"}]
    assert catalog(db, "outside") == []
    asset(db, "bad", {"editingResource": None})
    with pytest.raises(AttributeError):
        catalog(db, "workspace", asset_id="bad")
