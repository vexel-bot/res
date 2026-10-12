"""Persistence/access tests mock the engine process boundary, never claim pixel fidelity."""

import json
from pathlib import Path

import pytest
from conftest import register
from sqlalchemy import select, update

from app.config import get_settings
from app.database import SessionLocal
from app.models import CreativeDocument, LibraryAsset, User
from app.providers.studios.craft import HOST_COMMANDS, PAGE_COMMANDS
from app.services.studios import craft


def test_old_environment_cannot_reactivate_retired_renderers():
    from app.config import Settings
    from app.providers.studios.video_render import VIDEO_RENDER_PROVIDERS

    settings = Settings(
        _env_file=None,
        hyperframes_enabled=True,
        motion_canvas_enabled=True,
        remotion_enabled=True,
        remotion_native_enabled=True,
        studio_alight_motion_enabled=True,
        studio_editorial_motion_provider="remotion.contextual-v2",
    )
    assert not any(
        (
            settings.hyperframes_enabled,
            settings.motion_canvas_enabled,
            settings.remotion_enabled,
            settings.remotion_native_enabled,
            settings.studio_alight_motion_enabled,
        )
    )
    assert settings.studio_editorial_motion_provider == "craft.effectcraft"
    assert VIDEO_RENDER_PROVIDERS == {}


def headers(token, key=None):
    result = {"Authorization": "Bearer " + token}
    if key:
        result["Idempotency-Key"] = key
    return result


def test_invalid_carousel_returns_validation_error_without_creating_document(client):
    token, workspace = register(client, "invalid-craft-carousel@example.com")
    base = "/api/v1/studios/v1/documents"
    before = client.get(base, headers=headers(token), params={"workspace_id": workspace}).json()
    response = client.post(base, headers=headers(token), json={
        "workspaceId": workspace, "title": "Incomplete carousel", "contentType": "carousel",
        "brief": {"objective": "Validate page cardinality", "audience": "QA"},
        "composition": {"pages": [{
            "id": "only-page", "width": 320, "height": 320, "layers": [],
        }]},
    })
    assert response.status_code == 422, response.text
    assert "at least two pages" in response.text
    after = client.get(base, headers=headers(token), params={"workspace_id": workspace}).json()
    assert after == before


@pytest.fixture
def native_boundary(monkeypatch, tmp_path):
    settings = get_settings()
    monkeypatch.setattr(settings, "storage_path", str(tmp_path / "objects"))
    command_schema = {
        "type": "object",
        "properties": {"color": {"type": "string"}},
        "required": ["color"],
        "additionalProperties": False,
    }
    capability = {
        "engine": "photocraft",
        "available": True,
        "buildId": "test-native-process-boundary",
        "upstreamRevision": "a" * 40,
        "formatVersion": "1",
        "formats": ["png", "png_set"],
        "commands": [
            {"id": "paint.set", "label": "Color", "inputSchema": command_schema},
            {
                "id": "asset.import",
                "label": "Import",
                "inputSchema": {
                    "type": "object",
                    "properties": {"assetId": {"type": "string"}},
                    "required": ["assetId"],
                    "additionalProperties": False,
                },
            },
            *HOST_COMMANDS,
            *PAGE_COMMANDS,
        ],
    }
    monkeypatch.setattr(craft, "require_capability", lambda engine: {**capability, "engine": engine})
    monkeypatch.setattr(
        "app.providers.studios.craft.require_capability", lambda engine: {**capability, "engine": engine}
    )
    calls = []

    def engine(engine, method, params, **kwargs):
        calls.append((method, params))
        if method == "project.new":
            data = {"width": params["width"], "height": params["height"], "layers": [], "color": "original"}
            legacy = params.get("legacyDocument", {}).get("composition", {}).get("pages", [])
            if legacy:
                data["layers"] = legacy[0]["layers"]
            Path(params["outputPath"]).write_text(json.dumps(data), encoding="utf-8")
            return {"inspection": data, "warnings": []}
        data = json.loads(Path(params["nativePath"]).read_text(encoding="utf-8"))
        if method in {"render.frame", "render.export"}:
            # A known decodable fixture exercises byte/storage contracts, not engine fidelity.
            from PIL import Image

            Image.new("RGB", (2, 2), "blue").save(params["outputPath"], "PNG")
            return {"artifact": {"width": 2, "height": 2, "path": params["outputPath"]}, "warnings": []}
        if method == "engine.execute":
            for command in params["commands"]:
                if command["id"] == "paint.set":
                    if command["params"]["color"] == "fail":
                        Path(params["outputPath"]).write_text("partial", encoding="utf-8")
                        raise ValueError("native_engine_failed")
                    data["color"] = command["params"]["color"]
            Path(params["outputPath"]).write_text(json.dumps(data), encoding="utf-8")
        return {"inspection": data, "warnings": []}

    monkeypatch.setattr(craft, "call_engine", engine)
    return calls


def create(client, token, workspace, count=1):
    response = client.post(
        "/api/v1/studios/v1/documents",
        headers=headers(token),
        json={
            "workspaceId": workspace,
            "title": "Native document",
            "contentType": "carousel" if count > 1 else "visual",
            "brandRevision": 1,
            "brief": {"objective": "Native integration", "audience": "Editors"},
            "composition": {
                "pages": [
                    {"id": "page-" + str(index), "width": 640, "height": 480, "background": "#ffffff", "layers": []}
                    for index in range(count)
                ]
            },
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def migrate(client, token, document, key="migration-test-0001"):
    response = client.post(
        f"/api/v1/studios/v1/documents/{document['documentId']}/craft/migrate",
        headers=headers(token, key),
        json={"engine": "photocraft", "expectedRevision": document["revision"]},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_migration_all_pages_archive_and_project_access(client, native_boundary):
    token, workspace = register(client, "craft-pages@example.com")
    other_token, _workspace = register(client, "craft-other@example.com")
    document = create(client, token, workspace, 3)
    result = migrate(client, token, document)
    assert len(result["nativeEditorState"]["pageProjects"]) == 3
    assert [page["id"] for page in result["pages"]] == ["page-0", "page-1", "page-2"]
    assert result["nativeEditorState"]["legacyArchiveAssetId"]
    assert sum(method == "project.new" for method, _params in native_boundary) == 3
    url = f"/api/v1/studios/v1/documents/{document['documentId']}/native-project"
    assert client.get(url, headers=headers(other_token)).status_code == 404
    loaded = client.get(url + "?pageId=page-2", headers=headers(token))
    assert loaded.status_code == 200
    assert json.loads(loaded.content)["width"] == 640
    archive = client.get(url + "?allPages=true", headers=headers(token))
    assert archive.status_code == 200 and archive.content[:2] == b"PK"
    archived = client.get(
        f"/api/v1/assets/{result['nativeEditorState']['legacyArchiveAssetId']}/content", headers=headers(token)
    )
    assert len(archived.json()["canonicalDocument"]["composition"]["pages"]) == 3


def test_atomic_commands_replay_conflict_failed_engine_retains_bytes(client, native_boundary):
    token, workspace = register(client, "craft-save@example.com")
    document = create(client, token, workspace)
    state = migrate(client, token, document)
    base = f"/api/v1/studios/v1/documents/{document['documentId']}"
    payload = {"expectedRevision": state["revision"], "commands": [{"id": "paint.set", "params": {"color": "blue"}}]}
    changed = client.post(base + "/craft/commands", headers=headers(token, "save-command-0001"), json=payload)
    assert changed.status_code == 200, changed.text
    repeat = client.post(base + "/craft/commands", headers=headers(token, "save-command-0001"), json=payload)
    assert repeat.json()["receiptId"] == changed.json()["receiptId"]
    conflict = client.post(base + "/craft/commands", headers=headers(token, "save-command-0002"), json=payload)
    assert conflict.status_code == 409
    bad_replay = client.post(
        base + "/craft/commands",
        headers=headers(token, "save-command-0001"),
        json={**payload, "commands": [{"id": "paint.set", "params": {"color": "red"}}]},
    )
    assert bad_replay.status_code == 409
    before = client.get(base + "/native-project", headers=headers(token)).content
    with SessionLocal() as db:
        asset_count = len(db.scalars(select(LibraryAsset)).all())
    failed = client.post(
        base + "/craft/commands",
        headers=headers(token, "save-command-failure"),
        json={
            "expectedRevision": changed.json()["document"]["revision"],
            "commands": [{"id": "paint.set", "params": {"color": "fail"}}],
        },
    )
    assert failed.status_code == 422
    assert client.get(base + "/native-project", headers=headers(token)).content == before
    with SessionLocal() as db:
        assert len(db.scalars(select(LibraryAsset)).all()) == asset_count


def test_page_specific_edit_add_delete_order_and_undo_redo(client, native_boundary):
    token, workspace = register(client, "craft-history@example.com")
    document = create(client, token, workspace, 2)
    state = migrate(client, token, document)
    base = f"/api/v1/studios/v1/documents/{document['documentId']}"

    def execute(command, params, page_id=None):
        nonlocal state
        response = client.post(
            base + "/craft/commands",
            headers=headers(token, "history-" + str(state["revision"])),
            json={
                "expectedRevision": state["revision"],
                "commands": [{"id": command, "params": params}],
                "pageId": page_id,
            },
        )
        assert response.status_code == 200, response.text
        state = response.json()["inspection"]
        return response.json()

    execute("paint.set", {"color": "blue"}, "page-1")
    assert (
        json.loads(client.get(base + "/native-project?pageId=page-0", headers=headers(token)).content)["color"]
        == "original"
    )
    assert (
        json.loads(client.get(base + "/native-project?pageId=page-1", headers=headers(token)).content)["color"]
        == "blue"
    )
    execute("host.history.undo", {})
    assert (
        json.loads(client.get(base + "/native-project?pageId=page-1", headers=headers(token)).content)["color"]
        == "original"
    )
    execute("host.history.redo", {})
    assert (
        json.loads(client.get(base + "/native-project?pageId=page-1", headers=headers(token)).content)["color"]
        == "blue"
    )
    execute("host.pages.add", {"pageId": "added", "title": "Added", "width": 320, "height": 640})
    assert len(state["pages"]) == 3
    execute("host.pages.move", {"pageId": "added", "index": 0})
    assert state["pages"][0]["id"] == "added"
    execute("host.pages.delete", {"pageId": "added"})
    assert [page["id"] for page in state["pages"]] == ["page-0", "page-1"]


def test_schema_paths_cross_workspace_and_retention_are_enforced(client, native_boundary):
    token, workspace = register(client, "craft-security@example.com")
    document = create(client, token, workspace)
    state = migrate(client, token, document)
    base = f"/api/v1/studios/v1/documents/{document['documentId']}"
    invalid = client.post(
        base + "/craft/commands",
        headers=headers(token, "params-invalid-001"),
        json={"expectedRevision": state["revision"], "commands": [{"id": "paint.set", "params": {"color": 5}}]},
    )
    assert invalid.status_code == 422
    foreign = client.post(
        base + "/craft/commands",
        headers=headers(token, "asset-foreign-001"),
        json={
            "expectedRevision": state["revision"],
            "commands": [{"id": "asset.import", "params": {"assetId": "unknown"}}],
        },
    )
    assert foreign.status_code == 422
    asset_id = state["nativeEditorState"]["projectAssetId"]
    assert client.delete(f"/api/v1/assets/{asset_id}", headers=headers(token)).status_code == 409
    legacy_commands = client.post(base + "/editor/commands", headers=headers(token), json={})
    assert legacy_commands.status_code == 404
    canonical = client.get(base, headers=headers(token)).json()
    canonical["nativeEditorState"] = None
    rejected = client.put(
        base, headers=headers(token), json={"expectedRevision": state["revision"], "document": canonical}
    )
    assert rejected.status_code == 422


def test_compare_and_swap_preserves_concurrent_native_document(client, native_boundary, monkeypatch, tmp_path):
    token, workspace = register(client, "craft-cas@example.com")
    document = create(client, token, workspace)
    state = migrate(client, token, document)
    with SessionLocal() as db:
        record = db.get(CreativeDocument, document["documentId"])
        actor = db.get(User, record.created_by)
        capability = craft.require_capability("photocraft")
        source = tmp_path / "incoming.pcraft"
        source.write_text('{"width":640,"height":480,"layers":[]}', encoding="utf-8")
        with SessionLocal() as other:
            other.execute(
                update(CreativeDocument).where(CreativeDocument.id == record.id).values(revision=record.revision + 1)
            )
            other.commit()
        with pytest.raises(ValueError, match="studio_document_conflict"):
            craft._commit_project(
                db,
                record,
                actor,
                source,
                engine="photocraft",
                capability=capability,
                expected_revision=state["revision"],
                key="cas-conflict-save",
                digest="digest",
                project={},
            )
        db.refresh(record)
        assert record.revision == state["revision"] + 1
        assert (
            record.canonical_document["nativeEditorState"]["projectAssetId"]
            == state["nativeEditorState"]["projectAssetId"]
        )
