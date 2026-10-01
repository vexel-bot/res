from __future__ import annotations

import hashlib
import json
import tempfile
from collections.abc import Callable
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...domain.studios.contracts import (
    AudioWaveformResultV1,
    AudioWaveformSpecV1,
    CreateAudioWaveformRequest,
    CreateGenerationJobRequest,
    MediaProbeResultV1,
)
from ...models import LibraryAsset, StudioGenerationJob, StudioMediaIngest, User
from ...providers.studios.media_waveform import MEDIA_WAVEFORM_PROVIDERS
from ..object_storage import get_object_storage, object_key, sha256_file
from .jobs import create_job
from .kernel import emit_event

WAVEFORM_MEDIA_TYPE = "application/vnd.clicko.audio-waveform+json"


def _spec_digest(spec: AudioWaveformSpecV1) -> str:
    raw = json.dumps(
        spec.model_dump(by_alias=True, mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def create_media_waveform_job(
    db: Session,
    ingest: StudioMediaIngest,
    request: CreateAudioWaveformRequest,
    idempotency_key: str,
    user: User,
) -> tuple[StudioGenerationJob, bool]:
    if ingest.workspace_id != request.workspace_id:
        raise ValueError("media_ingest_workspace_mismatch")
    if ingest.status != "ready" or not ingest.media_info:
        raise ValueError("media_ingest_not_ready")
    media_info = MediaProbeResultV1.model_validate(ingest.media_info)
    stream_indexes = {stream.index for stream in media_info.audio_streams}
    selected_stream = request.spec.audio_stream_index
    if selected_stream is not None and selected_stream not in stream_indexes:
        raise ValueError("media_waveform_audio_stream_not_found")
    if selected_stream is None and not stream_indexes:
        raise ValueError("media_waveform_audio_stream_required")
    job_request = CreateGenerationJobRequest(
        workspace_id=request.workspace_id,
        job_type="media_waveform",
        provider="builtin.ffmpeg-waveform",
        request={
            "mediaIngestId": ingest.id,
            "spec": request.spec.model_dump(by_alias=True, mode="json"),
        },
        correlation_id=f"media-waveform:{ingest.id}",
    )
    job, created = create_job(db, job_request, idempotency_key, user)
    if created:
        emit_event(
            db,
            workspace_id=ingest.workspace_id,
            event_type="studio.media.waveform_requested",
            aggregate_type="media_ingest",
            aggregate_id=ingest.id,
            correlation_id=job.correlation_id,
            actor_id=user.id,
            payload={"jobId": job.id, "sourceAssetId": ingest.asset_id},
        )
        db.commit()
        db.refresh(job)
    return job, created


def _existing_result(db: Session, job: StudioGenerationJob) -> dict | None:
    records = db.scalars(
        select(LibraryAsset).where(
            LibraryAsset.workspace_id == job.workspace_id,
            LibraryAsset.asset_type == "waveform",
            LibraryAsset.lifecycle_status == "active",
        )
    ).all()
    for asset in records:
        metadata = asset.object_metadata or {}
        if metadata.get("generationJobId") != job.id or metadata.get("derivation") != "audio_waveform":
            continue
        result = metadata.get("audioWaveformResult")
        if isinstance(result, dict):
            return AudioWaveformResultV1.model_validate(result).model_dump(by_alias=True, mode="json")
    return None


def execute_media_waveform(
    db: Session,
    job: StudioGenerationJob,
    progress: Callable[[int], None],
    is_cancelled: Callable[[], bool],
) -> dict:
    existing = _existing_result(db, job)
    if existing:
        return existing
    ingest_id = str(job.request_payload.get("mediaIngestId") or "")
    ingest = db.scalar(
        select(StudioMediaIngest).where(
            StudioMediaIngest.id == ingest_id,
            StudioMediaIngest.workspace_id == job.workspace_id,
        )
    )
    if not ingest or ingest.status != "ready" or not ingest.media_info:
        raise ValueError("media_ingest_not_ready")
    source_asset = db.scalar(
        select(LibraryAsset).where(
            LibraryAsset.id == ingest.asset_id,
            LibraryAsset.workspace_id == ingest.workspace_id,
            LibraryAsset.lifecycle_status == "active",
        )
    )
    if not source_asset or not source_asset.storage_key:
        raise ValueError("stored_media_asset_required")
    spec = AudioWaveformSpecV1.model_validate(job.request_payload.get("spec") or {})
    provider = MEDIA_WAVEFORM_PROVIDERS.get(job.provider)
    if not provider:
        raise ValueError("media_waveform_provider_unavailable")
    media_info = MediaProbeResultV1.model_validate(ingest.media_info)
    selected = None
    if spec.audio_stream_index is not None:
        selected = next(
            (stream for stream in media_info.audio_streams if stream.index == spec.audio_stream_index),
            None,
        )
    elif media_info.audio_streams:
        selected = media_info.audio_streams[0]
    if selected is None:
        raise ValueError("media_waveform_audio_stream_not_found")
    if is_cancelled():
        return {"cancelled": True}
    source_storage = get_object_storage(source_asset.storage_backend or "local")
    destination_storage = get_object_storage(source_asset.storage_backend or "local")
    stored = None
    checksum = source_asset.checksum_sha256
    with source_storage.materialize(source_asset.storage_key) as source_path:
        checksum = checksum or sha256_file(source_path)
        with tempfile.TemporaryDirectory(prefix="clicko-media-waveform-") as temporary:
            output_path = Path(temporary) / "waveform.json"
            try:
                manifest = provider.generate(
                    source_path,
                    output_path,
                    media_ingest_id=ingest.id,
                    source_asset_id=source_asset.id,
                    source_checksum_sha256=checksum,
                    audio_stream_index=selected.index,
                    start_microseconds=selected.start_microseconds - media_info.start_microseconds,
                    source_duration_microseconds=media_info.duration_microseconds,
                    spec=spec,
                    progress=progress,
                    is_cancelled=is_cancelled,
                )
            except InterruptedError:
                return {"cancelled": True}
            if is_cancelled():
                return {"cancelled": True}
            if (
                manifest.media_ingest_id != ingest.id
                or manifest.source_asset_id != source_asset.id
                or manifest.source_checksum_sha256.lower() != checksum.lower()
                or manifest.audio_stream_index != selected.index
                or manifest.spec != spec
                or manifest.spec_digest != _spec_digest(spec)
            ):
                raise ValueError("media_waveform_manifest_mismatch")
            if manifest.total_samples <= 0:
                raise ValueError("media_waveform_empty")
            decoded_end = manifest.start_microseconds + manifest.duration_microseconds
            sample_tolerance = max(1, (1_000_000 + spec.sample_rate - 1) // spec.sample_rate)
            if decoded_end > media_info.duration_microseconds + sample_tolerance:
                raise ValueError("media_waveform_duration_exceeds_source")
            key = object_key(ingest.workspace_id, "derived", ".json")
            stored = destination_storage.put_file(
                output_path,
                key=key,
                media_type=WAVEFORM_MEDIA_TYPE,
                metadata={
                    "workspace-id": ingest.workspace_id,
                    "role": "audio-waveform",
                    "source-asset-id": source_asset.id,
                    "media-ingest-id": ingest.id,
                    "generation-job-id": job.id,
                    "provider": manifest.provider,
                },
            )
    if is_cancelled():
        destination_storage.delete(stored.key)
        return {"cancelled": True}
    progress(90)
    try:
        waveform_asset = LibraryAsset(
            workspace_id=ingest.workspace_id,
            title=f"{source_asset.title} — waveform",
            asset_type="waveform",
            tags=[*(source_asset.tags or []), "studio-waveform"],
            campaign_id=source_asset.campaign_id,
            content_id=source_asset.content_id,
            storage_key=stored.key,
            storage_backend=stored.backend,
            media_type=stored.media_type,
            size_bytes=stored.size_bytes,
            checksum_sha256=stored.checksum_sha256,
            object_metadata={
                **stored.metadata,
                "schemaVersion": "studio.asset-lineage.v1",
                "derivedFromAssetId": source_asset.id,
                "derivation": "audio_waveform",
                "generationJobId": job.id,
                "providerVersion": manifest.provider_version,
                "waveformManifestSchema": manifest.schema_version,
                "waveformSpec": spec.model_dump(by_alias=True, mode="json"),
                "waveformSpecDigest": manifest.spec_digest,
            },
        )
        db.add(waveform_asset)
        db.flush()
        ingest.waveform_asset_id = waveform_asset.id
        source_asset.checksum_sha256 = checksum
        result = AudioWaveformResultV1(
            media_ingest_id=ingest.id,
            source_asset_id=source_asset.id,
            waveform_asset_id=waveform_asset.id,
            provider=manifest.provider,
            provider_version=manifest.provider_version,
            storage_backend=stored.backend,
            size_bytes=stored.size_bytes,
            checksum_sha256=stored.checksum_sha256,
            source_checksum_sha256=checksum,
            spec_digest=manifest.spec_digest,
            start_microseconds=manifest.start_microseconds,
            duration_microseconds=manifest.duration_microseconds,
            sample_rate=manifest.sample_rate,
            bucket_count=manifest.bucket_count,
        )
        waveform_asset.object_metadata = {
            **waveform_asset.object_metadata,
            "audioWaveformResult": result.model_dump(by_alias=True, mode="json"),
        }
        emit_event(
            db,
            workspace_id=ingest.workspace_id,
            event_type="studio.media.waveform_ready",
            aggregate_type="media_ingest",
            aggregate_id=ingest.id,
            correlation_id=job.correlation_id,
            actor_id=None,
            payload={
                "sourceAssetId": source_asset.id,
                "waveformAssetId": waveform_asset.id,
                "checksumSha256": stored.checksum_sha256,
                "bucketCount": manifest.bucket_count,
            },
        )
        db.commit()
        return result.model_dump(by_alias=True, mode="json")
    except Exception:
        db.rollback()
        if stored is not None:
            destination_storage.delete(stored.key)
        raise
