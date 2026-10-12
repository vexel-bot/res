"""Rehearse migration of existing documents in a private copy, never the source DB.

Usage: python scripts/craft/migration_acceptance.py --database /path/nexus.db
       --storage /path/uploads
Only referenced local assets are copied. Missing media/unsupported operations
are reported explicitly; original data remains untouched.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--storage", type=Path, required=True)
    parser.add_argument(
        "--recover-effects",
        action="store_true",
        help="Also recover visual layers of FilmCraft projects into editable EffectCraft overlays",
    )
    args = parser.parse_args()
    source_database = args.database.resolve(strict=True)
    source_storage = args.storage.resolve(strict=True)
    output = ROOT / ".codex-runtime/craft" / ("migration-qa-" + uuid4().hex[:12])
    output.mkdir(parents=True)
    database, storage = output / "qa.sqlite", output / "storage"
    storage.mkdir()
    with (
        sqlite3.connect(source_database.as_uri() + "?mode=ro", uri=True) as source,
        sqlite3.connect(database) as target,
    ):
        source.backup(target)
    os.environ.update(
        {
            "ENVIRONMENT": "development",
            "DATABASE_URL": "sqlite:///" + database.as_posix(),
            "STORAGE_PATH": str(storage),
            "OBJECT_STORAGE_BACKEND": "local",
            "OPENAI_OUTBOUND_ENABLED": "false",
            "STUDIO_EDITING_AI_PLANNING_PROVIDER": "none",
            "STUDIO_PRODUCTION_TEST_BUDGET_USD": "0",
            "STUDIO_CRAFT_PHOTOCRAFT_BINARY": "",
            "STUDIO_CRAFT_FILMCRAFT_BINARY": "",
            "STUDIO_CRAFT_EFFECTCRAFT_BINARY": "",
        }
    )
    sys.path.insert(0, str(ROOT / "backend"))
    from sqlalchemy import select
    from app.database import Base, SessionLocal, engine
    from app.domain.studios.craft import (
        CraftMigrationRequestV1,
        CraftRecoverEffectsRequestV1,
    )
    from app.models import CreativeDocument, LibraryAsset, Membership, User
    from app.services.object_storage import get_object_storage
    from app.services.studios import craft
    from app.services.studios.compatibility import record_to_contract

    Base.metadata.create_all(engine)
    results = []
    with SessionLocal() as db:
        identifiers = list(db.scalars(select(CreativeDocument.id)))
    for identifier in identifiers:
        result = {"documentId": identifier, "status": "pending"}
        try:
            with SessionLocal() as db:
                record = db.get(CreativeDocument, identifier)
                contract = record_to_contract(record)
                if contract.native_editor_state and not args.recover_effects:
                    result.update(
                        status="already_native",
                        engine=contract.native_editor_state.engine,
                    )
                    results.append(result)
                    continue
                original_canvas, original_versions = (
                    record.document,
                    record.versions or [],
                )
                actor_id = record.created_by or db.scalar(
                    select(Membership.user_id).where(
                        Membership.workspace_id == record.workspace_id,
                        Membership.role == "owner",
                    )
                )
                actor = db.get(User, actor_id) if actor_id else None
                if actor is None:
                    raise ValueError("migration_owner_missing")
                missing = []
                referenced = {reference.id for reference in contract.assets}
                if contract.native_editor_state:
                    native_source = contract.native_editor_state
                    referenced.update(
                        [
                            native_source.project_asset_id,
                            native_source.legacy_archive_asset_id,
                        ]
                    )
                    referenced.update(
                        item.asset_id
                        for item in [
                            *native_source.asset_manifest,
                            *native_source.font_manifest,
                        ]
                    )
                for asset_id in sorted(item for item in referenced if item):
                    asset = db.get(LibraryAsset, asset_id)
                    if asset is None or asset.storage_backend != "local":
                        missing.append(asset_id)
                        continue
                    source = (source_storage / asset.storage_key).resolve()
                    target = (storage / asset.storage_key).resolve()
                    if not source.is_relative_to(
                        source_storage
                    ) or not target.is_relative_to(storage):
                        raise ValueError("migration_asset_path_outside_storage")
                    if not source.is_file():
                        missing.append(asset_id)
                        continue
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, target)
                if missing:
                    result.update(
                        reason="original_media_unavailable", missingAssetIds=missing
                    )
                    results.append(result)
                    continue
                chosen = (
                    "filmcraft"
                    if contract.content_type in {"video", "presenter"}
                    else "photocraft"
                )
                state = (
                    craft.inspection(db, record)
                    if contract.native_editor_state
                    else craft.migrate(
                        db,
                        record,
                        CraftMigrationRequestV1(
                            engine=chosen, expected_revision=record.revision
                        ),
                        actor,
                        "migration-qa-" + uuid4().hex,
                    )
                )
                native = record_to_contract(record).native_editor_state
                archive_asset = db.get(LibraryAsset, native.legacy_archive_asset_id)
                with get_object_storage(archive_asset.storage_backend).materialize(
                    archive_asset.storage_key
                ) as path:
                    archived = json.loads(path.read_text(encoding="utf-8"))
                if not contract.native_editor_state:
                    assert archived["legacyCanvas"] == original_canvas
                    assert archived["versions"] == original_versions
                native_asset = db.get(LibraryAsset, native.project_asset_id)
                with get_object_storage(native_asset.storage_backend).materialize(
                    native_asset.storage_key
                ) as path:
                    assert (
                        hashlib.sha256(path.read_bytes()).hexdigest()
                        == native.checksum_sha256
                    )
                reopened = craft.inspection(db, record)
                assert (
                    reopened["nativeEditorState"]["checksumSha256"]
                    == native.checksum_sha256
                )
                result.update(
                    status="converted",
                    engine=chosen,
                    originalArchived=True,
                    nativeReopened=True,
                    migrationWarnings=state["migrationWarnings"],
                    pageCount=len(contract.composition.pages),
                )
                if args.recover_effects and chosen == "filmcraft":
                    if any(
                        page.get("layers")
                        for page in archived["canonicalDocument"]["composition"][
                            "pages"
                        ]
                    ):
                        recovered = craft.recover_effects(
                            db,
                            record,
                            CraftRecoverEffectsRequestV1(
                                expected_revision=record.revision
                            ),
                            actor,
                            "recovery-qa-" + uuid4().hex,
                        )
                        child = db.get(
                            CreativeDocument, recovered["compositionDocumentId"]
                        )
                        source_view = craft.inspection(db, child)
                        with get_object_storage(
                            native_asset.storage_backend
                        ).materialize(native_asset.storage_key) as path:
                            assert (
                                hashlib.sha256(path.read_bytes()).hexdigest()
                                == native.checksum_sha256
                            )
                        result.update(
                            effectCompositionReopened=True,
                            compositionDocumentId=child.id,
                            effectMigrationWarnings=source_view["migrationWarnings"],
                            requiresCompositionReview=True,
                        )
                    else:
                        result.update(
                            effectRecovery="no_visual_layers",
                            requiresCompositionReview=bool(state["migrationWarnings"]),
                        )
        except Exception as error:
            result.update(errorType=type(error).__name__, reason=str(error)[:1200])
        results.append(result)
        print(
            f"Migration rehearsal {len(results)}/{len(identifiers)}: {result['status']}",
            flush=True,
        )
    evidence = {
        "schemaVersion": "clicko.craft-migration-acceptance.v1",
        "sourceDatabaseReadOnly": True,
        "copyDatabase": str(database),
        "documentCount": len(identifiers),
        "results": results,
    }
    (output / "results.json").write_text(
        json.dumps(evidence, indent=2) + "\n", encoding="utf-8"
    )
    counts = {
        state: sum(r["status"] == state for r in results)
        for state in ("converted", "already_native", "pending")
    }
    print(json.dumps({"counts": counts, "evidence": str(output / "results.json")}))


if __name__ == "__main__":
    main()
