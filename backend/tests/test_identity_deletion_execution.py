from __future__ import annotations

from pathlib import Path

import pytest
from alembic.config import Config
from conftest import register
from sqlalchemy import create_engine, inspect, select

from alembic import command
from app.config import get_settings
from app.database import SessionLocal
from app.domain.studios.contracts import CreateIdentityDeletionRequest
from app.models import (
    LibraryAsset,
    StudioGenerationJob,
    StudioIdentityDeletionRequest,
    StudioIdentityEvaluation,
    StudioIdentityProfile,
    StudioIdentityVersion,
    StudioVoiceProfile,
    StudioVoiceVersion,
    User,
)
from app.services.object_storage import LocalObjectStorage, object_key
from app.services.studios.identity import request_identity_deletion
from app.services.studios.identity_deletion import (
    IdentityDeletionDeferred,
    IdentityDeletionStorageError,
    execute_identity_deletion,
)


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def add_stored_asset(
    db,
    storage: LocalObjectStorage,
    tmp_path: Path,
    *,
    workspace_id: str,
    title: str,
    legal_hold: bool = False,
) -> tuple[LibraryAsset, str]:
    source = tmp_path / f"{title.replace(' ', '-')}.bin"
    source.write_bytes(f"private:{title}".encode())
    key = object_key(workspace_id, "identity", ".bin")
    stored = storage.put_file(
        source,
        key=key,
        media_type="application/octet-stream",
        metadata={"workspace-id": workspace_id, "role": "identity-test"},
    )
    asset = LibraryAsset(
        workspace_id=workspace_id,
        title=title,
        asset_type="upload",
        tags=["identity-private"],
        storage_key=key,
        storage_backend=stored.backend,
        media_type=stored.media_type,
        size_bytes=stored.size_bytes,
        checksum_sha256=stored.checksum_sha256,
        object_metadata=stored.metadata,
        legal_hold=legal_hold,
    )
    db.add(asset)
    db.flush()
    return asset, key


def add_identity_capsule(
    db,
    *,
    workspace_id: str,
    user_id: str,
    source_asset_id: str,
    derived_asset_ids: list[str] | None = None,
    preview_asset_ids: list[str] | None = None,
) -> tuple[StudioIdentityProfile, StudioIdentityVersion]:
    profile = StudioIdentityProfile(
        workspace_id=workspace_id,
        subject_key="subject-delete-test",
        display_name="Pessoa a excluir",
        identity_type="natural_person",
        status="active",
        owner_user_id=user_id,
        created_by=user_id,
    )
    db.add(profile)
    db.flush()
    version = StudioIdentityVersion(
        workspace_id=workspace_id,
        profile_id=profile.id,
        version=1,
        status="active",
        capabilities=["avatar.generate"],
        sample_asset_ids=[source_asset_id],
        derived_artifacts=[{"id": asset_id} for asset_id in (derived_asset_ids or [])],
        content_hash="a" * 64,
        created_by=user_id,
        review_comment="Contains private review text",
    )
    db.add(version)
    db.flush()
    if preview_asset_ids:
        db.add(
            StudioIdentityEvaluation(
                workspace_id=workspace_id,
                target_type="identity_version",
                identity_version_id=version.id,
                status="passed",
                evaluator_kind="human",
                quality_metrics={"identitySimilarity": 0.9},
                checks=[{"code": "human-review", "passed": True}],
                preview_asset_ids=preview_asset_ids,
                evaluated_by=user_id,
                notes="Private preview notes",
            )
        )
    db.commit()
    return profile, version


def plan_deletion(
    db,
    *,
    profile: StudioIdentityProfile | StudioVoiceProfile,
    user: User,
    delete_source_samples: bool,
    target_type: str,
    key: str,
) -> StudioIdentityDeletionRequest:
    deletion, _ = request_identity_deletion(
        db,
        profile,
        CreateIdentityDeletionRequest(
            reason="Titular solicitou exclusão física e auditável.",
            delete_source_samples=delete_source_samples,
        ),
        key,
        user,
        target_type=target_type,
    )
    return deletion


def test_physical_deletion_tombstones_derivatives_preserves_sources_and_is_idempotent(
    client, tmp_path: Path
) -> None:
    token, workspace_id = register(client, "physical-delete@example.com", "Physical Delete")
    storage = LocalObjectStorage(str(tmp_path / "objects"))
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "physical-delete@example.com"))
        source, source_key = add_stored_asset(
            db, storage, tmp_path, workspace_id=workspace_id, title="source sample"
        )
        derived, derived_key = add_stored_asset(
            db, storage, tmp_path, workspace_id=workspace_id, title="derived capsule"
        )
        preview, preview_key = add_stored_asset(
            db, storage, tmp_path, workspace_id=workspace_id, title="private preview"
        )
        profile, version = add_identity_capsule(
            db,
            workspace_id=workspace_id,
            user_id=user.id,
            source_asset_id=source.id,
            derived_asset_ids=[derived.id],
            preview_asset_ids=[preview.id],
        )
        deletion = plan_deletion(
            db,
            profile=profile,
            user=user,
            delete_source_samples=False,
            target_type="identity_profile",
            key="physical-delete-idempotency",
        )
        deletion_id = deletion.id
        profile_id = profile.id
        version_id = version.id
        source_id = source.id
        derived_id = derived.id
        preview_id = preview.id

        with pytest.raises(ValueError, match="identity_deletion_execution_disabled"):
            execute_identity_deletion(
                db,
                deletion_id,
                execution_enabled=False,
                storage_factory=lambda _backend: storage,
            )
        assert storage.exists(source_key)
        assert storage.exists(derived_key)
        assert storage.exists(preview_key)

        receipt = execute_identity_deletion(
            db,
            deletion_id,
            execution_enabled=True,
            storage_factory=lambda _backend: storage,
        )
        replay = execute_identity_deletion(
            db,
            deletion_id,
            execution_enabled=True,
            storage_factory=lambda _backend: storage,
        )
        assert replay == receipt

        assert storage.exists(source_key)
        assert not storage.exists(derived_key)
        assert not storage.exists(preview_key)
        assert receipt["deletedAssetCount"] == 2
        assert receipt["preservedSourceAssetIds"] == [source_id]

        source_record = db.get(LibraryAsset, source_id)
        assert source_record.lifecycle_status == "active"
        for asset_id in (derived_id, preview_id):
            asset = db.get(LibraryAsset, asset_id)
            assert asset.lifecycle_status == "deleted"
            assert asset.storage_key is None
            assert asset.checksum_sha256 is None
            assert asset.url is None
            assert asset.deletion_receipt["deletionRequestId"] == deletion_id
        deleted_profile = db.get(StudioIdentityProfile, profile_id)
        deleted_version = db.get(StudioIdentityVersion, version_id)
        assert deleted_profile.status == "deleted"
        assert deleted_profile.display_name == "Deleted identity"
        assert deleted_profile.subject_key == f"deleted:{profile_id}"
        assert deleted_version.status == "deleted"
        assert deleted_version.sample_asset_ids == []
        assert deleted_version.derived_artifacts == []
        assert db.get(StudioIdentityDeletionRequest, deletion_id).status == "completed"

    assert client.get(f"/api/v1/assets/{derived_id}/content", headers=auth(token)).status_code == 404
    listed = client.get("/api/v1/assets", params={"workspace_id": workspace_id}, headers=auth(token))
    assert listed.status_code == 200
    assert derived_id not in {item["id"] for item in listed.json()}


def test_legal_hold_blocks_all_objects_before_deletion(client, tmp_path: Path) -> None:
    _, workspace_id = register(client, "legal-hold@example.com", "Legal Hold")
    storage = LocalObjectStorage(str(tmp_path / "objects"))
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "legal-hold@example.com"))
        source, _ = add_stored_asset(db, storage, tmp_path, workspace_id=workspace_id, title="hold source")
        first, first_key = add_stored_asset(
            db, storage, tmp_path, workspace_id=workspace_id, title="first derivative"
        )
        held, held_key = add_stored_asset(
            db,
            storage,
            tmp_path,
            workspace_id=workspace_id,
            title="held derivative",
            legal_hold=True,
        )
        profile, _ = add_identity_capsule(
            db,
            workspace_id=workspace_id,
            user_id=user.id,
            source_asset_id=source.id,
            derived_asset_ids=[first.id, held.id],
        )
        deletion = plan_deletion(
            db,
            profile=profile,
            user=user,
            delete_source_samples=False,
            target_type="identity_profile",
            key="legal-hold-delete",
        )

        with pytest.raises(ValueError, match="identity_deletion_legal_hold"):
            execute_identity_deletion(
                db,
                deletion.id,
                execution_enabled=True,
                storage_factory=lambda _backend: storage,
            )
        assert storage.exists(first_key)
        assert storage.exists(held_key)
        assert db.get(LibraryAsset, first.id).lifecycle_status == "active"
        blocked = db.get(StudioIdentityDeletionRequest, deletion.id)
        assert blocked.status == "failed"
        assert blocked.execution_receipt["legalHoldAssetIds"] == [held.id]


def test_explicit_source_deletion_fails_closed_when_another_profile_references_asset(
    client, tmp_path: Path
) -> None:
    _, workspace_id = register(client, "shared-source@example.com", "Shared Source")
    storage = LocalObjectStorage(str(tmp_path / "objects"))
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "shared-source@example.com"))
        shared, shared_key = add_stored_asset(
            db, storage, tmp_path, workspace_id=workspace_id, title="shared source"
        )
        target = StudioVoiceProfile(
            workspace_id=workspace_id,
            display_name="Target voice",
            locale="pt-BR",
            voice_type="cloned",
            status="active",
            created_by=user.id,
        )
        other = StudioVoiceProfile(
            workspace_id=workspace_id,
            display_name="Other voice",
            locale="pt-BR",
            voice_type="cloned",
            status="active",
            created_by=user.id,
        )
        db.add_all([target, other])
        db.flush()
        db.add_all(
            [
                StudioVoiceVersion(
                    workspace_id=workspace_id,
                    profile_id=target.id,
                    version=1,
                    status="active",
                    sample_asset_ids=[shared.id],
                    derived_artifacts=[],
                    pronunciation_profile={},
                    content_hash="b" * 64,
                    created_by=user.id,
                ),
                StudioVoiceVersion(
                    workspace_id=workspace_id,
                    profile_id=other.id,
                    version=1,
                    status="active",
                    sample_asset_ids=[shared.id],
                    derived_artifacts=[],
                    pronunciation_profile={},
                    content_hash="c" * 64,
                    created_by=user.id,
                ),
            ]
        )
        db.commit()
        deletion = plan_deletion(
            db,
            profile=target,
            user=user,
            delete_source_samples=True,
            target_type="voice_profile",
            key="shared-source-delete",
        )

        with pytest.raises(ValueError, match="identity_deletion_shared_reference"):
            execute_identity_deletion(
                db,
                deletion.id,
                execution_enabled=True,
                storage_factory=lambda _backend: storage,
            )
        assert storage.exists(shared_key)
        assert db.get(LibraryAsset, shared.id).lifecycle_status == "active"
        blocked = db.get(StudioIdentityDeletionRequest, deletion.id)
        assert blocked.status == "failed"
        refs = blocked.execution_receipt["blockedReferences"][shared.id]
        assert any(reference.startswith("voice_version:") for reference in refs)


def test_running_job_defers_then_resumes_without_deleting_early(client, tmp_path: Path) -> None:
    _, workspace_id = register(client, "delete-retry@example.com", "Delete Retry")
    storage = LocalObjectStorage(str(tmp_path / "objects"))
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "delete-retry@example.com"))
        source, _ = add_stored_asset(db, storage, tmp_path, workspace_id=workspace_id, title="retry source")
        derived, derived_key = add_stored_asset(
            db, storage, tmp_path, workspace_id=workspace_id, title="retry derivative"
        )
        profile, version = add_identity_capsule(
            db,
            workspace_id=workspace_id,
            user_id=user.id,
            source_asset_id=source.id,
            derived_asset_ids=[derived.id],
        )
        job = StudioGenerationJob(
            workspace_id=workspace_id,
            identity_version_id=version.id,
            job_type="avatar_generate",
            provider="test.provider",
            idempotency_key="running-delete-job",
            payload_hash="d" * 64,
            correlation_id="running-delete-job",
            status="running",
            request_payload={},
        )
        db.add(job)
        db.commit()
        deletion = plan_deletion(
            db,
            profile=profile,
            user=user,
            delete_source_samples=False,
            target_type="identity_profile",
            key="running-job-delete",
        )
        assert job.status == "cancel_requested"

        with pytest.raises(IdentityDeletionDeferred, match="identity_deletion_waiting_for_jobs"):
            execute_identity_deletion(
                db,
                deletion.id,
                execution_enabled=True,
                storage_factory=lambda _backend: storage,
            )
        assert storage.exists(derived_key)
        assert db.get(LibraryAsset, derived.id).lifecycle_status == "active"
        job.status = "cancelled"
        db.commit()

        receipt = execute_identity_deletion(
            db,
            deletion.id,
            execution_enabled=True,
            storage_factory=lambda _backend: storage,
        )
        assert receipt["deletedAssetCount"] == 1
        assert not storage.exists(derived_key)


def test_storage_failure_records_partial_progress_and_retry_finishes(client, tmp_path: Path) -> None:
    _, workspace_id = register(client, "delete-storage-retry@example.com", "Delete Storage Retry")
    storage = LocalObjectStorage(str(tmp_path / "objects"))
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "delete-storage-retry@example.com"))
        source, _ = add_stored_asset(db, storage, tmp_path, workspace_id=workspace_id, title="storage source")
        first, first_key = add_stored_asset(
            db, storage, tmp_path, workspace_id=workspace_id, title="storage derivative one"
        )
        second, second_key = add_stored_asset(
            db, storage, tmp_path, workspace_id=workspace_id, title="storage derivative two"
        )
        profile, _ = add_identity_capsule(
            db,
            workspace_id=workspace_id,
            user_id=user.id,
            source_asset_id=source.id,
            derived_asset_ids=[first.id, second.id],
        )
        deletion = plan_deletion(
            db,
            profile=profile,
            user=user,
            delete_source_samples=False,
            target_type="identity_profile",
            key="storage-failure-delete",
        )
        assets_by_id = {first.id: (first, first_key), second.id: (second, second_key)}
        fail_asset_id = sorted(assets_by_id)[1]
        fail_key = assets_by_id[fail_asset_id][1]

        class FailOnceStorage:
            backend = "local"

            def __init__(self) -> None:
                self.failed = False

            def exists(self, key: str) -> bool:
                return storage.exists(key)

            def delete(self, key: str) -> None:
                if key == fail_key and not self.failed:
                    self.failed = True
                    raise OSError("simulated object storage outage")
                storage.delete(key)

        flaky = FailOnceStorage()
        with pytest.raises(IdentityDeletionStorageError, match="identity_deletion_storage_error:OSError"):
            execute_identity_deletion(
                db,
                deletion.id,
                execution_enabled=True,
                storage_factory=lambda _backend: flaky,
            )

        first_processed_id = sorted(assets_by_id)[0]
        assert db.get(LibraryAsset, first_processed_id).lifecycle_status == "deleted"
        assert db.get(LibraryAsset, fail_asset_id).lifecycle_status == "deleting"
        assert db.get(StudioIdentityDeletionRequest, deletion.id).status == "failed"

        receipt = execute_identity_deletion(
            db,
            deletion.id,
            execution_enabled=True,
            storage_factory=lambda _backend: storage,
        )
        assert receipt["deletedAssetCount"] == 2
        assert receipt["deletedThisAttemptCount"] == 1
        assert receipt["attemptHistory"]
        assert first_processed_id in receipt["alreadyDeletedAssetIds"]
        assert not storage.exists(first_key)
        assert not storage.exists(second_key)
        assert db.get(StudioIdentityDeletionRequest, deletion.id).status == "completed"


def test_enabled_route_only_queues_control_task_and_does_not_execute_inline(
    client, monkeypatch, tmp_path: Path
) -> None:
    token, workspace_id = register(client, "delete-queue@example.com", "Delete Queue")
    storage = LocalObjectStorage(str(tmp_path / "objects"))
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "delete-queue@example.com"))
        source, source_key = add_stored_asset(
            db, storage, tmp_path, workspace_id=workspace_id, title="queue source"
        )
        derived, derived_key = add_stored_asset(
            db, storage, tmp_path, workspace_id=workspace_id, title="queue derivative"
        )
        profile, _ = add_identity_capsule(
            db,
            workspace_id=workspace_id,
            user_id=user.id,
            source_asset_id=source.id,
            derived_asset_ids=[derived.id],
        )
        profile_id = profile.id

    from app import tasks

    queued: list[str] = []
    settings = get_settings()
    monkeypatch.setattr(settings, "identity_deletion_execution_enabled", True)
    monkeypatch.setattr(settings, "studio_isolated_queues_enabled", False)
    monkeypatch.setattr(tasks.execute_identity_deletion_task, "delay", lambda deletion_id: queued.append(deletion_id))
    response = client.post(
        f"/api/v1/studios/v1/identities/{profile_id}/deletion-requests",
        headers={**auth(token), "Idempotency-Key": "route-queues-delete"},
        json={"reason": "Titular solicitou exclusão; execução será assíncrona."},
    )
    assert response.status_code == 202, response.text
    assert response.json()["status"] == "queued"
    assert response.json()["queuedAt"]
    assert queued == [response.json()["id"]]
    assert storage.exists(source_key)
    assert storage.exists(derived_key)


def test_identity_deletion_migration_upgrades_and_downgrades(tmp_path: Path, monkeypatch) -> None:
    database_path = (tmp_path / "identity-deletion-migration.db").resolve()
    database_url = f"sqlite:///{database_path.as_posix()}"
    monkeypatch.setattr(get_settings(), "database_url", database_url)
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    command.upgrade(config, "0019_transcript_edits")
    command.upgrade(config, "head")
    inspector = inspect(create_engine(database_url))
    asset_columns = {column["name"] for column in inspector.get_columns("library_assets")}
    deletion_columns = {
        column["name"]
        for column in inspector.get_columns("studio_identity_deletion_requests")
    }
    job_columns = {
        column["name"] for column in inspector.get_columns("studio_generation_jobs")
    }
    requested_by_foreign_keys = [
        foreign_key
        for foreign_key in inspector.get_foreign_keys("studio_generation_jobs")
        if foreign_key["constrained_columns"] == ["requested_by"]
    ]
    transcript_columns = {
        column["name"] for column in inspector.get_columns("studio_transcripts")
    }
    assert {
        "lifecycle_status",
        "legal_hold",
        "legal_hold_reason",
        "deleted_at",
        "deletion_receipt",
    } <= asset_columns
    assert {"queued_at", "started_at", "attempt_count", "execution_receipt"} <= deletion_columns
    assert "requested_by" in job_columns
    assert len(requested_by_foreign_keys) == 1
    assert requested_by_foreign_keys[0]["referred_table"] == "users"
    assert requested_by_foreign_keys[0]["referred_columns"] == ["id"]
    assert requested_by_foreign_keys[0]["options"].get("ondelete") == "SET NULL"
    assert {"source_checksum_sha256", "provenance", "metrics"} <= transcript_columns

    command.downgrade(config, "0019_transcript_edits")
    inspector = inspect(create_engine(database_url))
    asset_columns = {column["name"] for column in inspector.get_columns("library_assets")}
    deletion_columns = {
        column["name"]
        for column in inspector.get_columns("studio_identity_deletion_requests")
    }
    job_columns = {
        column["name"] for column in inspector.get_columns("studio_generation_jobs")
    }
    transcript_columns = {
        column["name"] for column in inspector.get_columns("studio_transcripts")
    }
    assert not {
        "lifecycle_status",
        "legal_hold",
        "legal_hold_reason",
        "deleted_at",
        "deletion_receipt",
    } & asset_columns
    assert not {"queued_at", "started_at", "attempt_count", "execution_receipt"} & deletion_columns
    assert "requested_by" not in job_columns
    assert not {"source_checksum_sha256", "provenance", "metrics"} & transcript_columns
