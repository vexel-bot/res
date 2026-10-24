"""Canonical video editing, immutable render requests and durable delivery."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from hashlib import sha256

from sqlalchemy import select, update

from ...domain.studios.contracts import (
    AssetReferenceV1,
    CreateGenerationJobRequest,
    CreativeDocumentV1,
    ExportReferenceV1,
    ReviewReferenceV1,
)
from ...domain.studios.timeline_editor import JOB_TYPE, PROVIDER, MotionKey, VisualMotion
from ...models import CreativeDocument, LibraryAsset, StudioDomainEvent, StudioGenerationJob
from ...providers.studios import timeline_ffmpeg as renderer
from ..object_storage import get_object_storage, sha256_file
from .compatibility import composition_to_canvas, persist_contract, record_to_contract
from .craft import scoped_asset, workspace_files, write_asset
from .kernel import emit_event
from .review_binding import invalidate_linked_post_review


def editable(contract):
    if contract.content_type != "video" or contract.native_editor_state:
        raise ValueError("timeline_requires_canonical_video_project")
    if len(contract.composition.pages) != 1:
        raise ValueError("timeline_existing_composition_requires_native_editor")
    if contract.composition.pages[0].layers:
        from ...domain.studios.local_composition import validate_composition

        validate_composition(contract.composition, contract.content_type)


def validate(contract, *, require_content=False):
    editable(contract)
    page, timeline = contract.composition.pages[0], contract.composition.media_timeline
    if not timeline:
        raise ValueError("timeline_required")
    fps = timeline.frame_rate.numerator / timeline.frame_rate.denominator
    if not 1 <= fps <= 60 or timeline.duration_frames / fps > 600:
        raise ValueError("timeline_duration_or_rate_exceeds_limit")
    if not (320 <= page.width <= 1920 and 320 <= page.height <= 1920 and page.width % 2 == page.height % 2 == 0):
        raise ValueError("timeline_dimensions_unsupported")
    if len(timeline.tracks) > 16:
        raise ValueError("timeline_track_limit")
    from ...domain.studios.local_composition import validate_composition

    ids = {layer.id for layer in page.layers}
    asset_ids = validate_composition(contract.composition, contract.content_type) if page.layers else set()
    for track in timeline.tracks:
        if track.kind not in {"video", "audio", "overlay", "caption", "marker"}:
            raise ValueError("timeline_track_unsupported")
        items = track.cues if track.kind == "caption" else getattr(track, "clips", [])
        for item in items:
            if item.id in ids:
                raise ValueError("timeline_item_ids_must_be_unique")
            ids.add(item.id)
            if item.timeline.start_frame + item.timeline.duration_frames > timeline.duration_frames:
                raise ValueError("timeline_item_exceeds_duration")
            if track.kind == "caption":
                if item.style.font_asset_id or item.style.preset or item.style.emphasis_color:
                    raise ValueError("timeline_caption_style_unsupported")
                motion = VisualMotion.model_validate(item.motion)
            else:
                if item.effects:
                    raise ValueError("timeline_effect_not_supported")
                if getattr(item, "pan", 0) != 0:
                    raise ValueError("timeline_audio_pan_not_supported")
                motion = VisualMotion.model_validate(item.transform)
                if motion.background_color:
                    raise ValueError("timeline_background_requires_title")
                asset_ids.add(item.asset_id)
            keys = [MotionKey.model_validate(k) for k in item.keyframes]
            if len(keys) > 32 or len({(k.property, k.frame) for k in keys}) != len(keys):
                raise ValueError("timeline_keyframes_invalid")
            if any(k.frame > item.timeline.duration_frames for k in keys):
                raise ValueError("timeline_keyframe_exceeds_clip")
            if motion.fade_in_frames + motion.fade_out_frames > item.timeline.duration_frames:
                raise ValueError("timeline_fade_exceeds_clip")
            if track.kind == "audio" and (
                item.fade_in_frames + item.fade_out_frames > item.timeline.duration_frames or keys or item.transform
            ):
                raise ValueError("timeline_audio_parameters_unsupported")
    if len(ids) > 32:
        raise ValueError("timeline_layer_limit")
    if require_content and not ids:
        raise ValueError("timeline_empty")
    return asset_ids


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def save(db, record, request, user, key, *, operation=None):
    fingerprint = digest(request.model_dump(mode="json", by_alias=True))
    events = db.scalars(
        select(StudioDomainEvent).where(
            StudioDomainEvent.aggregate_id == record.id, StudioDomainEvent.event_type == "studio.video.timeline.saved"
        )
    ).all()
    for event in events:
        if event.payload.get("key") == key:
            if event.payload["digest"] != fingerprint:
                raise ValueError("idempotency_payload_conflict")
            # Return the exact committed revision; never claim old edits saved newer ones.
            return CreativeDocumentV1.model_validate(event.payload["document"])
    db.refresh(record)
    if record.revision != request.expected_revision:
        raise ValueError("studio_document_conflict")
    current = record_to_contract(record)
    frame_rate = request.timeline.frame_rate.numerator / request.timeline.frame_rate.denominator
    pages = [
        current.composition.pages[0].model_copy(
            update={"duration_ms": round(request.timeline.duration_frames / frame_rate * 1000)}
        ),
        *current.composition.pages[1:],
    ]
    composition = current.composition.model_copy(update={"media_timeline": request.timeline, "pages": pages})
    contract = current.model_copy(update={"composition": composition})
    references = validate(contract)
    assets = {a.id: a for a in current.assets}
    total = 0
    for identifier in references:
        asset = scoped_asset(db, record.workspace_id, identifier)
        if not (asset.media_type or "").startswith(("video/", "audio/", "image/")):
            raise ValueError("timeline_media_type_unsupported")
        if (
            (asset.object_metadata or {}).get("rightsStatus") == "restricted"
            or assets.get(identifier)
            and assets[identifier].rights_status == "restricted"
        ):
            raise ValueError("timeline_asset_restricted")
        total += asset.size_bytes or 0
        assets[identifier] = AssetReferenceV1(
            id=asset.id,
            media_type=asset.media_type,
            checksum=asset.checksum_sha256,
            origin="workspace",
            rights_status=assets[identifier].rights_status if identifier in assets else "unknown",
        )
    if total > 1024**3:
        raise ValueError("timeline_media_size_limit")
    if len(assets) > 1000:
        raise ValueError("timeline_asset_reference_limit")
    now = datetime.now(UTC)
    contract = contract.model_copy(
        update={
            "assets": list(assets.values()),
            "revision": current.revision + 1,
            "actor_id": user.id,
            "updated_at": now,
            "status": "draft",
            "review": ReviewReferenceV1(),
        }
    )
    payload = contract.model_dump(mode="json", by_alias=True)
    snapshots = [
        *(record.versions or []),
        {
            "number": record.version,
            "label": "Edição de vídeo",
            "createdAt": now.isoformat(),
            "actorId": user.id,
            "canonicalDocument": current.model_dump(mode="json", by_alias=True),
            "document": record.document,
        },
    ][-20:]
    changed = db.execute(
        update(CreativeDocument)
        .where(CreativeDocument.id == record.id, CreativeDocument.revision == request.expected_revision)
        .values(
            canonical_document=payload,
            document=composition_to_canvas(contract).model_dump(by_alias=True),
            revision=contract.revision,
            versions=snapshots,
            updated_at=now,
        ),
        execution_options={"synchronize_session": False},
    )
    if changed.rowcount != 1:
        db.rollback()
        raise ValueError("studio_document_conflict")
    invalidate_linked_post_review(db, record)
    emit_event(
        db,
        workspace_id=record.workspace_id,
        event_type="studio.video.timeline.saved",
        aggregate_type="creative_document",
        aggregate_id=record.id,
        actor_id=user.id,
        correlation_id=key,
        payload={"key": key, "digest": fingerprint, "revision": contract.revision, "document": payload},
    )
    if operation:
        from uuid import uuid4

        answer = {"document": payload, "receiptId": str(uuid4()), "aiTrace": operation.get("aiTrace", {})}
        emit_event(
            db,
            workspace_id=record.workspace_id,
            event_type="studio.craft.operation_committed",
            aggregate_type="creative_document",
            aggregate_id=record.id,
            actor_id=user.id,
            correlation_id=key,
            payload={**operation, "receipt": answer},
        )
    db.commit()
    db.refresh(record)
    return contract


def validate_admission(db, request):
    snapshot = CreativeDocumentV1.model_validate(request.request.get("documentSnapshot"))
    record = db.get(CreativeDocument, request.document_id)
    if (
        request.provider != PROVIDER
        or not record
        or request.workspace_id != record.workspace_id
        or snapshot != record_to_contract(record)
    ):
        raise ValueError("timeline_render_snapshot_conflict")
    validate(snapshot, require_content=True)
    known = {asset.id: asset.checksum for asset in snapshot.assets}
    for identifier in validate(snapshot):
        if not known.get(identifier):
            raise ValueError("timeline_snapshot_asset_checksum_required")
        scoped_asset(db, snapshot.workspace_id, identifier, known[identifier])
    if not renderer.capability()["available"]:
        raise ValueError("timeline_runtime_unavailable")


def create_render(db, record, request, user, key):
    from .jobs import create_job

    # Replaying an admitted request remains safe after the project changes.
    previous = db.scalar(
        select(StudioGenerationJob).where(
            StudioGenerationJob.workspace_id == record.workspace_id,
            StudioGenerationJob.job_type == JOB_TYPE,
            StudioGenerationJob.idempotency_key == key,
        )
    )
    if previous:
        if (
            previous.document_id != record.id
            or previous.request_payload.get("documentRevision") != request.expected_revision
        ):
            raise ValueError("idempotency_payload_conflict")
        return previous, False
    contract = record_to_contract(record)
    if contract.revision != request.expected_revision:
        raise ValueError("studio_document_conflict")
    return create_job(
        db,
        CreateGenerationJobRequest(
            workspace_id=record.workspace_id,
            document_id=record.id,
            job_type=JOB_TYPE,
            provider=PROVIDER,
            correlation_id=key,
            request={
                "documentSnapshot": contract.model_dump(by_alias=True, mode="json"),
                "documentRevision": contract.revision,
            },
        ),
        key,
        user,
    )


def execute(db, job, progress, is_cancelled):
    contract = CreativeDocumentV1.model_validate(job.request_payload["documentSnapshot"])
    if contract.workspace_id != job.workspace_id or contract.document_id != job.document_id:
        raise ValueError("timeline_job_identity_mismatch")
    references = validate(contract, require_content=True)
    record = db.get(CreativeDocument, job.document_id)
    if not record or record.workspace_id != job.workspace_id:
        raise ValueError("timeline_document_unavailable")
    # Recover delivery after a worker interruption between asset commit and job acknowledgement.
    cached = db.scalars(
        select(LibraryAsset).where(LibraryAsset.workspace_id == job.workspace_id, LibraryAsset.asset_type == "video")
    ).all()
    for asset in cached:
        if (asset.object_metadata or {}).get("timelineJobId") == job.id:
            with get_object_storage(asset.storage_backend).materialize(asset.storage_key) as path:
                if sha256_file(path) != asset.checksum_sha256:
                    raise ValueError("timeline_cached_output_checksum_mismatch")
            return asset.object_metadata["result"]
    written = None
    try:
        checksums = {a.id: a.checksum for a in contract.assets}
        total = 0
        for identifier in references:
            asset = scoped_asset(db, contract.workspace_id, identifier, checksums.get(identifier))
            total += asset.size_bytes or 0
            if total > 1024**3:
                raise ValueError("timeline_media_size_limit")
        with workspace_files(db, record, None, extra_asset_ids=references) as (directory, params, _manifest):
            paths = {entry["assetId"]: entry["path"] for entry in params["media"]}
            media_info = {}
            checksums = {a.id: a.checksum for a in contract.assets}
            total = 0
            for identifier in references:
                asset = scoped_asset(db, contract.workspace_id, identifier, checksums.get(identifier))
                total += asset.size_bytes or 0
                if total > 1024**3:
                    raise ValueError("timeline_media_size_limit")
                if not (asset.media_type or "").startswith("image/"):
                    media_info[identifier] = renderer.probe(paths[identifier])
                    if any(
                        s.get("width", 0) * s.get("height", 0) > 3840 * 2160 for s in media_info[identifier]["streams"]
                    ):
                        raise ValueError("timeline_source_resolution_limit")
            timeline = contract.composition.media_timeline
            fps = timeline.frame_rate.numerator / timeline.frame_rate.denominator
            for track in timeline.tracks:
                for clip in getattr(track, "clips", []):
                    if clip.asset_id not in media_info:
                        if track.kind == "audio":
                            raise ValueError("timeline_audio_stream_missing")
                        continue
                    info = media_info[clip.asset_id]
                    required = clip.timeline.duration_frames / fps * clip.playback_rate
                    start = clip.source.start_microseconds / 1e6 if clip.source else 0
                    if clip.source and required > clip.source.duration_microseconds / 1e6 + 1 / fps:
                        raise ValueError("timeline_source_range_exceeded")
                    if start + required > float(info["format"]["duration"]) + 1 / fps:
                        raise ValueError("timeline_source_range_exceeded")
                    if not any(
                        s["codec_type"] == ("audio" if track.kind == "audio" else "video") for s in info["streams"]
                    ):
                        raise ValueError("timeline_media_stream_missing")
            progress(10)
            output, metadata = renderer.render(contract, paths, directory, media_info, is_cancelled)
            progress(90)
            if is_cancelled():
                return {"cancelled": True}
            asset, storage, storage_key = write_asset(
                db,
                record,
                output,
                suffix=".mp4",
                media_type="video/mp4",
                asset_type="video",
                title=f"{contract.title} · revisão {contract.revision}",
                metadata={"timelineJobId": job.id, "documentRevision": contract.revision},
            )
            written = storage, storage_key
            db.flush()
            result = {
                "schemaVersion": "studio.timeline-render-result.v1",
                "assetId": asset.id,
                "jobId": job.id,
                "documentId": contract.document_id,
                "workspaceId": contract.workspace_id,
                "documentRevision": contract.revision,
                "checksumSha256": asset.checksum_sha256,
                "mediaType": "video/mp4",
                "sizeBytes": asset.size_bytes,
                "downloadUrl": f"/api/v1/assets/{asset.id}/content",
                **metadata,
            }
            asset.object_metadata = {**asset.object_metadata, "result": result, "provider": PROVIDER}
            asset.tags = [*asset.tags, "clicko-video-export"]
            if is_cancelled():
                db.rollback()
                storage.delete(storage_key)
                return {"cancelled": True}
            db.refresh(record, with_for_update=True)
            latest = record_to_contract(record)
            exports = [
                *latest.exports,
                ExportReferenceV1(
                    asset_id=asset.id,
                    document_version=contract.version,
                    target="download",
                    format="mp4",
                    created_at=datetime.now(UTC),
                ),
            ][-100:]
            persist_contract(record, latest.model_copy(update={"exports": exports}))
            db.commit()
            return result
    except InterruptedError:
        if written:
            db.rollback()
            written[0].delete(written[1])
        return {"cancelled": True}
    except Exception:
        if written:
            db.rollback()
            written[0].delete(written[1])
        raise
