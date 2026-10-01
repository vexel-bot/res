from __future__ import annotations

import tempfile
from collections.abc import Callable
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...domain.studios.contracts import (
    CreateGenerationJobRequest,
    CreateMediaProxyRequest,
    MediaProbeResultV1,
    MediaProxyResultV1,
    MediaProxySpecV1,
    MediaTimeMapSegmentV1,
    MediaTimeMapV1,
)
from ...models import LibraryAsset, StudioGenerationJob, StudioMediaIngest, User
from ...providers.studios.media_proxy import MEDIA_PROXY_PROVIDERS
from ..object_storage import get_object_storage, object_key, sha256_file
from .jobs import create_job
from .kernel import emit_event


def _ceil_frame_duration_microseconds(numerator: int, denominator: int) -> int:
    return (1_000_000 * denominator + numerator - 1) // numerator


def _existing_result(db: Session, job: StudioGenerationJob) -> dict | None:
    records = db.scalars(
        select(LibraryAsset).where(
            LibraryAsset.workspace_id == job.workspace_id,
            LibraryAsset.asset_type == "video",
            LibraryAsset.lifecycle_status == "active",
        )
    ).all()
    for asset in records:
        metadata = asset.object_metadata or {}
        if metadata.get("generationJobId") != job.id or metadata.get("derivation") != "video_proxy":
            continue
        result = metadata.get("mediaProxyResult")
        if isinstance(result, dict):
            return MediaProxyResultV1.model_validate(result).model_dump(by_alias=True, mode="json")
    return None


def _build_time_map(
    *,
    ingest: StudioMediaIngest,
    source_asset: LibraryAsset,
    proxy_asset: LibraryAsset,
    source_checksum: str,
    proxy_checksum: str,
    spec: MediaProxySpecV1,
    encoded,
) -> MediaTimeMapV1:
    if not ingest.media_info:
        raise ValueError("media_ingest_timing_missing")
    source_info = MediaProbeResultV1.model_validate(ingest.media_info)
    if not source_info.video_streams:
        raise ValueError("media_ingest_video_stream_missing")
    source_rate = source_info.video_streams[0].frame_rate
    source_video_start = source_info.video_streams[0].start_microseconds - source_info.start_microseconds
    source_audio_start = (
        source_info.audio_streams[0].start_microseconds - source_info.start_microseconds
        if source_info.audio_streams
        else None
    )
    if bool(source_info.audio_streams) != bool(encoded.audio_codec):
        raise ValueError("media_proxy_audio_stream_mismatch")
    representation_audio_start = encoded.audio_start_microseconds if encoded.audio_codec else None
    representation_rate = encoded.frame_rate
    if (
        representation_rate.numerator != spec.target_fps
        or representation_rate.denominator != 1
    ):
        raise ValueError("media_proxy_frame_rate_mismatch")
    source_duration = source_info.duration_microseconds
    representation_duration = encoded.duration_microseconds
    drift = abs(source_duration - representation_duration)
    allowed_drift = max(
        _ceil_frame_duration_microseconds(source_rate.numerator, source_rate.denominator),
        _ceil_frame_duration_microseconds(
            representation_rate.numerator,
            representation_rate.denominator,
        ),
    )
    try:
        return MediaTimeMapV1(
            source_asset_id=source_asset.id,
            representation_asset_id=proxy_asset.id,
            source_checksum_sha256=source_checksum,
            representation_checksum_sha256=proxy_checksum,
            source_frame_rate=source_rate,
            representation_frame_rate=representation_rate,
            source_video_start_microseconds=source_video_start,
            representation_video_start_microseconds=encoded.video_start_microseconds,
            source_audio_start_microseconds=source_audio_start,
            representation_audio_start_microseconds=representation_audio_start,
            source_duration_microseconds=source_duration,
            representation_duration_microseconds=representation_duration,
            max_drift_microseconds=drift,
            max_stream_offset_drift_microseconds=(
                0
                if source_audio_start is None or representation_audio_start is None
                else abs(
                    (source_audio_start - source_video_start)
                    - (representation_audio_start - encoded.video_start_microseconds)
                )
            ),
            allowed_drift_microseconds=allowed_drift,
            segments=[
                MediaTimeMapSegmentV1(
                    duration_microseconds=min(source_duration, representation_duration),
                )
            ],
        )
    except ValueError as error:
        raise ValueError("media_proxy_timing_drift") from error


def create_media_proxy_job(
    db: Session,
    ingest: StudioMediaIngest,
    request: CreateMediaProxyRequest,
    idempotency_key: str,
    user: User,
) -> tuple[StudioGenerationJob, bool]:
    if ingest.workspace_id != request.workspace_id:
        raise ValueError("media_ingest_workspace_mismatch")
    if ingest.status != "ready":
        raise ValueError("media_ingest_not_ready")
    job_request = CreateGenerationJobRequest(
        workspace_id=request.workspace_id,
        job_type="video_proxy",
        provider="builtin.ffmpeg-proxy",
        request={
            "mediaIngestId": ingest.id,
            "spec": request.spec.model_dump(by_alias=True, mode="json"),
        },
        correlation_id=f"media-proxy:{ingest.id}",
    )
    job, created = create_job(db, job_request, idempotency_key, user)
    if created:
        emit_event(
            db,
            workspace_id=ingest.workspace_id,
            event_type="studio.media.proxy_requested",
            aggregate_type="media_ingest",
            aggregate_id=ingest.id,
            correlation_id=job.correlation_id,
            actor_id=user.id,
            payload={"jobId": job.id, "sourceAssetId": ingest.asset_id},
        )
        db.commit()
        db.refresh(job)
    return job, created


def execute_media_proxy(
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
    if not ingest or ingest.status != "ready":
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
    spec = MediaProxySpecV1.model_validate(job.request_payload.get("spec") or {})
    provider = MEDIA_PROXY_PROVIDERS.get(job.provider)
    if not provider:
        raise ValueError("media_proxy_provider_unavailable")
    if is_cancelled():
        return {"cancelled": True}
    source_storage = get_object_storage(source_asset.storage_backend or "local")
    destination_storage = get_object_storage(source_asset.storage_backend or "local")
    stored = None
    source_checksum = source_asset.checksum_sha256
    with source_storage.materialize(source_asset.storage_key) as source_path:
        source_checksum = source_checksum or sha256_file(source_path)
        with tempfile.TemporaryDirectory(prefix="clicko-media-proxy-") as temporary:
            output_path = Path(temporary) / "proxy.mp4"
            try:
                encoded = provider.transcode(source_path, output_path, spec, progress, is_cancelled)
            except InterruptedError:
                return {"cancelled": True}
            if is_cancelled():
                return {"cancelled": True}
            key = object_key(ingest.workspace_id, "derived", ".mp4")
            stored = destination_storage.put_file(
                output_path,
                key=key,
                media_type="video/mp4",
                metadata={
                    "workspace-id": ingest.workspace_id,
                    "role": "editing-proxy",
                    "source-asset-id": source_asset.id,
                    "media-ingest-id": ingest.id,
                    "generation-job-id": job.id,
                    "provider": encoded.provider,
                },
            )
    if is_cancelled():
        destination_storage.delete(stored.key)
        return {"cancelled": True}
    progress(88)
    try:
        proxy_asset = LibraryAsset(
            workspace_id=ingest.workspace_id,
            title=f"{source_asset.title} — proxy",
            asset_type="video",
            tags=[*(source_asset.tags or []), "studio-proxy"],
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
                "derivation": "video_proxy",
                "generationJobId": job.id,
                "providerVersion": encoded.provider_version,
                "proxySpec": spec.model_dump(by_alias=True, mode="json"),
            },
        )
        db.add(proxy_asset)
        db.flush()
        time_map = _build_time_map(
            ingest=ingest,
            source_asset=source_asset,
            proxy_asset=proxy_asset,
            source_checksum=source_checksum,
            proxy_checksum=stored.checksum_sha256,
            spec=spec,
            encoded=encoded,
        )
        proxy_asset.object_metadata = {
            **proxy_asset.object_metadata,
            "mediaTimeMap": time_map.model_dump(by_alias=True, mode="json"),
        }
        ingest.proxy_asset_id = proxy_asset.id
        ingest.proxy_time_map = time_map.model_dump(by_alias=True, mode="json")
        source_asset.checksum_sha256 = source_checksum
        result = MediaProxyResultV1(
            media_ingest_id=ingest.id,
            source_asset_id=source_asset.id,
            proxy_asset_id=proxy_asset.id,
            provider=encoded.provider,
            provider_version=encoded.provider_version,
            storage_backend=stored.backend,
            size_bytes=stored.size_bytes,
            checksum_sha256=stored.checksum_sha256,
            width=encoded.width,
            height=encoded.height,
            frame_rate=encoded.frame_rate,
            duration_microseconds=encoded.duration_microseconds,
            video_codec=encoded.video_codec,
            audio_codec=encoded.audio_codec,
            warnings=encoded.warnings,
            time_map=time_map,
        )
        proxy_asset.object_metadata = {
            **proxy_asset.object_metadata,
            "mediaProxyResult": result.model_dump(by_alias=True, mode="json"),
        }
        emit_event(
            db,
            workspace_id=ingest.workspace_id,
            event_type="studio.media.proxy_ready",
            aggregate_type="media_ingest",
            aggregate_id=ingest.id,
            correlation_id=job.correlation_id,
            actor_id=None,
            payload={
                "sourceAssetId": source_asset.id,
                "proxyAssetId": proxy_asset.id,
                "checksumSha256": stored.checksum_sha256,
                "maxDriftMicroseconds": time_map.max_drift_microseconds,
            },
        )
        db.commit()
        return result.model_dump(by_alias=True, mode="json")
    except Exception:
        db.rollback()
        if stored is not None:
            destination_storage.delete(stored.key)
        raise
