from __future__ import annotations

import math
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...domain.studios.contracts import (
    TranscriptDocumentV1,
    TranscriptionJobResultV1,
    TranscriptionRequestV1,
    TranscriptionResultV1,
)
from ...domain.studios.providers import TRANSCRIPTION_PROVIDERS
from ...models import LibraryAsset, StudioGenerationJob, StudioMediaIngest, StudioTranscript, User
from ..object_storage import get_object_storage, sha256_file
from .kernel import emit_event


def _existing_result(db: Session, job: StudioGenerationJob) -> dict | None:
    record = db.scalar(
        select(StudioTranscript).where(
            StudioTranscript.workspace_id == job.workspace_id,
            StudioTranscript.idempotency_key == f"transcription-job:{job.id}",
        )
    )
    if not record:
        return None
    if not record.source_checksum_sha256 or not record.provenance:
        raise ValueError("transcription_persisted_result_incomplete")
    document = TranscriptDocumentV1.model_validate(record.transcript_document)
    source_checksum = record.source_checksum_sha256
    result = TranscriptionJobResultV1(
        generation_job_id=job.id,
        workspace_id=job.workspace_id,
        transcript_id=record.id,
        media_ingest_id=record.media_ingest_id,
        asset_id=record.asset_id,
        source_checksum_sha256=source_checksum,
        locale=document.locale,
        provider=document.provider,
        provider_version=document.provider_version or "unknown",
        transcript_revision=record.revision,
        transcript_version=record.version,
        segment_count=len(document.segments),
        transcription=TranscriptionResultV1(
            media_ingest_id=record.media_ingest_id,
            source_asset_id=record.asset_id,
            source_checksum_sha256=source_checksum,
            locale=document.locale,
            provider=document.provider,
            provider_version=document.provider_version or "unknown",
            segments=document.segments,
            provenance=record.provenance or {},
            metrics=record.metrics or {},
        ),
    )
    return result.model_dump(by_alias=True, mode="json")


def _validate_segments(result: TranscriptionResultV1, duration_microseconds: int) -> None:
    if duration_microseconds <= 0:
        raise ValueError("media_ingest_not_ready")
    for segment in result.segments:
        if segment.end_microseconds > duration_microseconds:
            raise ValueError("transcription_segment_exceeds_media_duration")


def _result_binding(
    result: TranscriptionResultV1,
    *,
    provider_name: str,
    provider_version: str,
    ingest: StudioMediaIngest,
    asset: LibraryAsset,
    checksum: str,
    locale: str,
) -> None:
    if result.provider != provider_name or result.provider_version != provider_version:
        raise ValueError("transcription_result_provider_mismatch")
    if result.media_ingest_id != ingest.id or result.source_asset_id != asset.id:
        raise ValueError("transcription_result_source_mismatch")
    if result.source_checksum_sha256.lower() != checksum.lower():
        raise ValueError("transcription_result_checksum_mismatch")
    if result.locale != locale:
        raise ValueError("transcription_result_locale_mismatch")
    if any(not math.isfinite(value) or value < 0 for value in result.metrics.values()):
        raise ValueError("transcription_metric_invalid")


def execute_transcription(
    db: Session,
    job: StudioGenerationJob,
    progress: Callable[[int], None],
    is_cancelled: Callable[[], bool],
) -> dict:
    """Run a promoted ASR adapter and persist a draft transcript atomically."""
    if job.job_type != "transcription":
        raise ValueError("transcription_job_type_required")
    existing = _existing_result(db, job)
    if existing:
        return existing
    request = TranscriptionRequestV1.model_validate(job.request_payload)
    provider = TRANSCRIPTION_PROVIDERS.get(job.provider)
    if provider is None:
        raise ValueError("transcription_provider_unavailable")
    if is_cancelled():
        return {"cancelled": True}
    ingest = db.scalar(
        select(StudioMediaIngest).where(
            StudioMediaIngest.id == request.media_ingest_id,
            StudioMediaIngest.workspace_id == job.workspace_id,
        )
    )
    if not ingest or ingest.status != "ready":
        raise ValueError("media_ingest_not_ready")
    asset = db.scalar(
        select(LibraryAsset).where(
            LibraryAsset.id == ingest.asset_id,
            LibraryAsset.workspace_id == job.workspace_id,
            LibraryAsset.lifecycle_status == "active",
        )
    )
    if not asset or not asset.storage_key:
        raise ValueError("stored_media_asset_required")
    if request.source_asset_id != asset.id:
        raise ValueError("transcription_source_asset_mismatch")
    if not asset.checksum_sha256 or request.source_checksum_sha256.lower() != asset.checksum_sha256.lower():
        raise ValueError("transcription_source_checksum_mismatch")
    actor_id = job.requested_by
    if not actor_id or db.get(User, actor_id) is None:
        raise ValueError("transcription_actor_missing")
    storage = get_object_storage(asset.storage_backend or "local")
    with storage.materialize(asset.storage_key) as source:
        checksum = sha256_file(source)
        if asset.checksum_sha256 and asset.checksum_sha256.lower() != checksum.lower():
            raise ValueError("source_asset_checksum_mismatch")
        progress(25)
        try:
            provider_result = provider.transcribe(request, source, progress, is_cancelled)
        except InterruptedError:
            return {"cancelled": True}
    if is_cancelled():
        return {"cancelled": True}
    result = TranscriptionResultV1.model_validate(provider_result)
    _result_binding(
        result,
        provider_name=provider.name,
        provider_version=provider.version,
        ingest=ingest,
        asset=asset,
        checksum=checksum,
        locale=request.locale,
    )
    _validate_segments(result, int((ingest.media_info or {}).get("durationMicroseconds") or 0))
    now = datetime.now(UTC)
    transcript_id = str(uuid4())
    document = TranscriptDocumentV1(
        id=transcript_id,
        workspace_id=job.workspace_id,
        media_ingest_id=ingest.id,
        asset_id=asset.id,
        locale=result.locale,
        status="draft",
        revision=1,
        version=1,
        provider=result.provider,
        provider_version=result.provider_version,
        segments=result.segments,
        created_by=actor_id,
        updated_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    record = StudioTranscript(
        id=transcript_id,
        workspace_id=job.workspace_id,
        media_ingest_id=ingest.id,
        asset_id=asset.id,
        locale=result.locale,
        status="draft",
        revision=1,
        version=1,
        provider=result.provider,
        provider_version=result.provider_version,
        source_checksum_sha256=checksum,
        provenance=result.provenance.model_dump(by_alias=True, mode="json"),
        metrics=result.metrics,
        transcript_document={
            **document.model_dump(by_alias=True, mode="json"),
        },
        versions=[],
        idempotency_key=f"transcription-job:{job.id}",
        created_by=actor_id,
        updated_by=actor_id,
    )
    db.add(record)
    db.flush()
    job_result = TranscriptionJobResultV1(
        generation_job_id=job.id,
        workspace_id=job.workspace_id,
        transcript_id=record.id,
        media_ingest_id=ingest.id,
        asset_id=asset.id,
        source_checksum_sha256=checksum,
        locale=result.locale,
        provider=result.provider,
        provider_version=result.provider_version,
        transcript_revision=record.revision,
        transcript_version=record.version,
        segment_count=len(result.segments),
        transcription=result,
    )
    emit_event(
        db,
        workspace_id=job.workspace_id,
        event_type="studio.transcript.generated",
        aggregate_type="transcript",
        aggregate_id=record.id,
        correlation_id=job.correlation_id,
        actor_id=actor_id,
        payload={
            "generationJobId": job.id,
            "mediaIngestId": ingest.id,
            "assetId": asset.id,
            "sourceChecksumSha256": checksum,
            "provider": result.provider,
            "providerVersion": result.provider_version,
            "segments": len(result.segments),
        },
    )
    db.commit()
    return job_result.model_dump(by_alias=True, mode="json")
