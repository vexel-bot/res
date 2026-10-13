"""Apply qualified native conversions to a local database, retaining a SQLite backup.

Explicit --apply is required. Engine transactions retain the original document
and native files; nonrepresentable treatments remain visible as review warnings.
Run with the application stopped so that the backup defines the rollout boundary.
"""

import argparse
from copy import deepcopy
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import sqlite3
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--storage", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--document-id", action="append", default=[])
    args = parser.parse_args()
    database, storage = (
        args.database.resolve(strict=True),
        args.storage.resolve(strict=True),
    )
    if not database.is_relative_to(ROOT) or not storage.is_relative_to(ROOT):
        raise ValueError("Primary database and storage must belong to this checkout")
    if not args.apply:
        print(
            "No changes made; use --apply after qualifying the private-copy rehearsal."
        )
        return
    output = ROOT / ".codex-runtime/craft" / ("primary-migration-" + uuid4().hex[:12])
    output.mkdir(parents=True)
    backup = output / "database-before-native-migration.sqlite"
    with (
        sqlite3.connect(database.as_uri() + "?mode=ro", uri=True) as source,
        sqlite3.connect(backup) as target,
    ):
        source.backup(target)
    os.environ.update(
        {
            "ENVIRONMENT": "development",
            "DATABASE_URL": "sqlite:///" + database.as_posix(),
            "STORAGE_PATH": str(storage),
            "OBJECT_STORAGE_BACKEND": "local",
            "OPENAI_OUTBOUND_ENABLED": "false",
            "STUDIO_GEMINI_ENABLED": "false",
            "STUDIO_EDITING_AI_PLANNING_PROVIDER": "none",
            "STUDIO_PRODUCTION_TEST_BUDGET_USD": "0",
            "CELERY_TASK_ALWAYS_EAGER": "true",
        }
    )
    sys.path.insert(0, str(ROOT / "backend"))
    from sqlalchemy import select

    from app.database import SessionLocal
    from app.domain.studios.craft import (
        CraftMigrationRequestV1,
        CraftRecoverEffectsRequestV1,
    )
    from app.models import CreativeDocument, LibraryAsset, Membership, User
    from app.services.object_storage import get_object_storage, sha256_file
    from app.services.studios import craft
    from app.services.studios.compatibility import record_to_contract

    with SessionLocal() as db:
        query = select(CreativeDocument.id)
        if args.document_id:
            query = query.where(CreativeDocument.id.in_(args.document_id))
        identifiers = list(db.scalars(query))
        if set(args.document_id) - set(identifiers):
            raise ValueError("migration_document_not_found")
    results = []
    evidence = {
        "schemaVersion": "clicko.craft-primary-migration.v1",
        "sourceDatabase": str(database),
        "backupDatabase": str(backup),
        "startedAt": datetime.now(UTC).isoformat(),
        "backupSha256": sha256_file(backup),
        "sourceDocuments": len(identifiers),
        "results": results,
    }
    destination = output / "results.json"
    for identifier in identifiers:
        item = {"documentId": identifier, "status": "pending"}
        try:
            with SessionLocal() as db:
                record = db.get(CreativeDocument, identifier)
                actor_id = record.created_by or db.scalar(
                    select(Membership.user_id).where(
                        Membership.workspace_id == record.workspace_id,
                        Membership.role.in_(["owner", "admin"]),
                    )
                )
                actor = db.get(User, actor_id) if actor_id else None
                if actor is None:
                    raise ValueError("migration_owner_missing")
                contract = record_to_contract(record)
                state = contract.native_editor_state
                original_canvas, original_versions = (
                    deepcopy(record.document),
                    deepcopy(record.versions or []),
                )
                chosen = (
                    state.engine
                    if state
                    else "filmcraft"
                    if contract.content_type in {"video", "presenter"}
                    else "photocraft"
                )
                if state is None:
                    craft.migrate(
                        db,
                        record,
                        CraftMigrationRequestV1(
                            engine=chosen, expected_revision=record.revision
                        ),
                        actor,
                        f"craft-primary-migration:{identifier}:{record.revision}:{chosen}",
                    )
                elif (
                    state.engine == "effectcraft"
                    and state.build_id != "clicko-effectcraft-1.0.2+67434e90"
                ):
                    from app.domain.studios.craft import CraftUpgradeRequestV1

                    craft.upgrade_build(
                        db,
                        record,
                        CraftUpgradeRequestV1(
                            expected_revision=record.revision,
                            target_build_id="clicko-effectcraft-1.0.2+67434e90",
                        ),
                        actor,
                        f"craft-primary-upgrade:{identifier}:{record.revision}",
                    )
                detail = craft.inspection(db, record)
                state = record_to_contract(record).native_editor_state
                assert state is not None
                if state.legacy_archive_asset_id:
                    archive_asset = db.get(LibraryAsset, state.legacy_archive_asset_id)
                    with get_object_storage(archive_asset.storage_backend).materialize(
                        archive_asset.storage_key
                    ) as path:
                        assert sha256_file(path) == archive_asset.checksum_sha256
                        archived = json.loads(path.read_text(encoding="utf-8"))
                    if contract.native_editor_state is None:
                        assert archived["legacyCanvas"] == original_canvas
                        assert archived["versions"] == original_versions
                item.update(
                    status="converted",
                    engine=chosen,
                    nativeBuildId=state.build_id,
                    nativeChecksumSha256=state.checksum_sha256,
                    originalArchived=bool(state.legacy_archive_asset_id),
                    nativeReopened=True,
                    warnings=detail.get("migrationWarnings", []),
                )
                if chosen == "filmcraft":
                    try:
                        recovered = craft.recover_effects(
                            db,
                            record,
                            CraftRecoverEffectsRequestV1(
                                expected_revision=record.revision
                            ),
                            actor,
                            f"craft-primary-effects:{identifier}:{record.revision}",
                        )
                        child = db.get(
                            CreativeDocument, recovered["compositionDocumentId"]
                        )
                        composition = craft.inspection(db, child)
                        item.update(
                            compositionDocumentId=child.id,
                            compositionReopened=True,
                            effectBuildId=composition["nativeEditorState"]["buildId"],
                            effectWarnings=composition.get("migrationWarnings", []),
                            requiresCompositionReview=True,
                        )
                    except ValueError as exc:
                        if str(exc) != "craft_legacy_visual_layers_missing":
                            raise
                        item["withoutVisualLayers"] = True
        except Exception as exc:
            item.update(
                status="pending",
                errorType=type(exc).__name__,
                reason=str(exc).split(":", 1)[0][:160],
            )
        results.append(item)
        destination.write_text(json.dumps(evidence, ensure_ascii=False, indent=2))
        print(
            json.dumps(
                {
                    "completed": len(results),
                    "total": len(identifiers),
                    "status": item["status"],
                    "engine": item.get("engine"),
                    "compositionReopened": item.get("compositionReopened", False),
                }
            ),
            flush=True,
        )
    evidence.update(
        completedAt=datetime.now(UTC).isoformat(),
        converted=sum(r["status"] == "converted" for r in results),
        pending=sum(r["status"] != "converted" for r in results),
    )
    destination.write_text(json.dumps(evidence, ensure_ascii=False, indent=2))
    (ROOT / ".codex-runtime/craft/primary-migration-latest.json").write_text(
        json.dumps(evidence, indent=2)
    )
    if evidence["pending"]:
        raise SystemExit(
            "Native migration retains pending documents; review the private evidence before continuing."
        )


if __name__ == "__main__":
    main()
