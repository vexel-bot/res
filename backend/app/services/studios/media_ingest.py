from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...domain.studios.contracts import (
    CreateGenerationJobRequest,
    CreateMediaIngestRequest,
    MediaIngestV1,
)
from ...models import LibraryAsset, StudioGenerationJob, StudioMediaIngest, User
from ...providers.studios.media_probe import MEDIA_PROBE_PROVIDERS
from ..object_storage import get_object_storage, sha256_file
from .jobs import create_job
from .kernel import emit_event


def media_ingest_out(ingest: StudioMediaIngest) -> MediaIngestV1:
    return MediaIngestV1.model_validate(ingest)


def create_media_ingest(
    db: Session,
    request: CreateMediaIngestRequest,
    idempotency_key: str,
    user: User,
) -> tuple[StudioMediaIngest, StudioGenerationJob, bool]:
    existing = db.scalar(
        select(StudioMediaIngest).where(
            StudioMediaIngest.workspace_id == request.workspace_id,
            StudioMediaIngest.idempotency_key == idempotency_key,
        )
    )
    if existing:
        if existing.asset_id != request.asset_id:
            raise ValueError("idempotency_payload_conflict")
        job = db.get(StudioGenerationJob, existing.generation_job_id) if existing.generation_job_id else None
        if not job:
            raise ValueError("media_ingest_job_missing")
        return existing, job, False
    asset = db.scalar(
        select(LibraryAsset).where(
            LibraryAsset.id == request.asset_id,
            LibraryAsset.workspace_id == request.workspace_id,
            LibraryAsset.lifecycle_status == "active",
        )
    )
    if not asset or not asset.storage_key:
        raise ValueError("stored_media_asset_required")
    if not (asset.media_type or "").startswith(("video/", "audio/")):
        raise ValueError("video_asset_required")
    ingest = StudioMediaIngest(
        workspace_id=request.workspace_id,
        asset_id=request.asset_id,
        status="pending",
        probe_provider="builtin.ffprobe",
        validation_errors=[],
        idempotency_key=idempotency_key,
        requested_by=user.id,
    )
    db.add(ingest)
    db.flush()
    emit_event(
        db,
        workspace_id=ingest.workspace_id,
        event_type="studio.media.ingest_requested",
        aggregate_type="media_ingest",
        aggregate_id=ingest.id,
        correlation_id=f"media-ingest:{ingest.id}",
        actor_id=user.id,
        payload={"assetId": ingest.asset_id, "provider": ingest.probe_provider},
    )
    db.commit()
    db.refresh(ingest)
    try:
        job_request = CreateGenerationJobRequest(
            workspace_id=request.workspace_id,
            job_type="media_probe",
            provider="builtin.ffprobe",
            request={"mediaIngestId": ingest.id, "assetId": asset.id},
            correlation_id=f"media-ingest:{ingest.id}",
        )
        job, _ = create_job(db, job_request, idempotency_key, user)
        ingest.generation_job_id = job.id
        db.commit()
        db.refresh(ingest)
        return ingest, job, True
    except Exception:
        ingest.status = "failed"
        db.commit()
        raise


def execute_media_probe(
    db: Session,
    job: StudioGenerationJob,
    progress: Callable[[int], None],
    is_cancelled: Callable[[], bool],
) -> dict:
    ingest_id = str(job.request_payload.get("mediaIngestId") or "")
    ingest = db.scalar(
        select(StudioMediaIngest).where(
            StudioMediaIngest.id == ingest_id,
            StudioMediaIngest.workspace_id == job.workspace_id,
        )
    )
    if not ingest:
        raise ValueError("media_ingest_not_found")
    if ingest.status in {"ready", "rejected"} and ingest.media_info:
        return {"mediaIngestId": ingest.id, "status": ingest.status, "mediaInfo": ingest.media_info}
    asset = db.scalar(
        select(LibraryAsset).where(
            LibraryAsset.id == ingest.asset_id,
            LibraryAsset.workspace_id == ingest.workspace_id,
            LibraryAsset.lifecycle_status == "active",
        )
    )
    if not asset or not asset.storage_key:
        raise ValueError("stored_media_asset_required")
    provider = MEDIA_PROBE_PROVIDERS.get(ingest.probe_provider)
    if not provider:
        raise ValueError("media_probe_provider_unavailable")
    ingest.status = "probing"
    ingest.validation_errors = []
    db.commit()
    progress(10)
    if is_cancelled():
        ingest.status = "pending"
        db.commit()
        return {"cancelled": True}
    storage = get_object_storage(asset.storage_backend or "local")
    with storage.materialize(asset.storage_key) as path:
        checksum = asset.checksum_sha256 or sha256_file(path)
        progress(35)
        result = provider.probe(path, asset_id=asset.id, checksum_sha256=checksum)
    if is_cancelled():
        ingest.status = "pending"
        db.commit()
        return {"cancelled": True}
    validation_errors = []
    if (asset.media_type or "").startswith("audio/"):
        if len(result.audio_streams) != 1 or result.video_streams:
            validation_errors.append("single_audio_only_stream_required")
    elif not result.video_streams:
        validation_errors.append("video_stream_required")
    if result.duration_microseconds <= 0:
        validation_errors.append("positive_duration_required")
    ingest.media_info = result.model_dump(by_alias=True, mode="json")
    ingest.validation_errors = validation_errors
    ingest.status = "rejected" if validation_errors else "ready"
    asset.checksum_sha256 = checksum
    asset.size_bytes = result.size_bytes
    asset.object_metadata = {
        **(asset.object_metadata or {}),
        "mediaProbeProvider": result.provider,
        "mediaProbeVersion": result.provider_version,
        "mediaProbeSchema": result.schema_version,
    }
    progress(90)
    emit_event(
        db,
        workspace_id=ingest.workspace_id,
        event_type=f"studio.media.ingest_{ingest.status}",
        aggregate_type="media_ingest",
        aggregate_id=ingest.id,
        correlation_id=job.correlation_id,
        actor_id=None,
        payload={
            "assetId": asset.id,
            "durationMicroseconds": result.duration_microseconds,
            "videoStreams": len(result.video_streams),
            "audioStreams": len(result.audio_streams),
            "validationErrors": validation_errors,
        },
    )
    db.commit()
    return {
        "mediaIngestId": ingest.id,
        "status": ingest.status,
        "mediaInfo": ingest.media_info,
        "validationErrors": validation_errors,
    }


def mark_media_ingest_failed(db: Session, job: StudioGenerationJob, error: Exception) -> None:
    ingest_id = str(job.request_payload.get("mediaIngestId") or "")
    ingest = db.get(StudioMediaIngest, ingest_id)
    if not ingest or ingest.workspace_id != job.workspace_id:
        return
    ingest.status = "failed"
    ingest.validation_errors = [f"{type(error).__name__}:{str(error)[:500]}"]
    db.commit()
