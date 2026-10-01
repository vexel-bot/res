from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...domain.studios.contracts import (
    ApplyEditDecisionSetRequest,
    ApplyTranscriptCaptionsRequest,
    CaptionCueV1,
    CaptionTrackV1,
    CreateEditDecisionSetRequest,
    CreateTranscriptRequest,
    CreativeCompositionV1,
    EditDecisionSetV1,
    MediaTimelineV1,
    ReplaceEditDecisionSetRequest,
    ReplaceStudioDocumentRequest,
    ReplaceTranscriptRequest,
    TimelineFrameRangeV1,
    TranscriptDocumentV1,
)
from ...models import (
    CreativeDocument,
    StudioEditDecisionSet,
    StudioMediaIngest,
    StudioTranscript,
    User,
)
from .compatibility import record_to_contract
from .kernel import emit_event, replace_document


def _media_duration(ingest: StudioMediaIngest) -> int:
    return int((ingest.media_info or {}).get("durationMicroseconds") or 0)


def _validate_timed_items(items: list, duration_microseconds: int, *, label: str) -> None:
    if duration_microseconds <= 0:
        raise ValueError("media_ingest_not_ready")
    for item in items:
        if item.end_microseconds > duration_microseconds:
            raise ValueError(f"{label}_exceeds_media_duration")


def transcript_out(record: StudioTranscript) -> TranscriptDocumentV1:
    return TranscriptDocumentV1.model_validate(record.transcript_document).model_copy(
        update={
            "status": record.status,
            "revision": record.revision,
            "version": record.version,
            "updated_by": record.updated_by,
            "updated_at": record.updated_at,
        }
    )


def create_transcript(
    db: Session,
    request: CreateTranscriptRequest,
    idempotency_key: str,
    user: User,
) -> tuple[StudioTranscript, bool]:
    existing = db.scalar(
        select(StudioTranscript).where(
            StudioTranscript.workspace_id == request.workspace_id,
            StudioTranscript.idempotency_key == idempotency_key,
        )
    )
    request_segments = [item.model_dump(by_alias=True, mode="json") for item in request.segments]
    if existing:
        current = transcript_out(existing)
        if (
            current.media_ingest_id != request.media_ingest_id
            or current.locale != request.locale
            or current.status != request.status
            or [item.model_dump(by_alias=True, mode="json") for item in current.segments] != request_segments
        ):
            raise ValueError("idempotency_payload_conflict")
        return existing, False
    ingest = db.scalar(
        select(StudioMediaIngest).where(
            StudioMediaIngest.id == request.media_ingest_id,
            StudioMediaIngest.workspace_id == request.workspace_id,
        )
    )
    if not ingest or ingest.status != "ready":
        raise ValueError("media_ingest_not_ready")
    _validate_timed_items(request.segments, _media_duration(ingest), label="transcript_segment")
    now = datetime.now(UTC)
    transcript_id = str(uuid4())
    document = TranscriptDocumentV1(
        id=transcript_id,
        workspace_id=request.workspace_id,
        media_ingest_id=ingest.id,
        asset_id=ingest.asset_id,
        locale=request.locale,
        status=request.status,
        provider="manual",
        segments=request.segments,
        created_by=user.id,
        updated_by=user.id,
        created_at=now,
        updated_at=now,
    )
    record = StudioTranscript(
        id=transcript_id,
        workspace_id=request.workspace_id,
        media_ingest_id=ingest.id,
        asset_id=ingest.asset_id,
        locale=request.locale,
        status=request.status,
        revision=1,
        version=1,
        provider="manual",
        transcript_document=document.model_dump(by_alias=True, mode="json"),
        versions=[],
        idempotency_key=idempotency_key,
        created_by=user.id,
        updated_by=user.id,
    )
    db.add(record)
    emit_event(
        db,
        workspace_id=record.workspace_id,
        event_type="studio.transcript.created",
        aggregate_type="transcript",
        aggregate_id=record.id,
        correlation_id=f"transcript:{record.id}",
        actor_id=user.id,
        payload={"mediaIngestId": ingest.id, "locale": request.locale, "segments": len(request.segments)},
    )
    db.commit()
    db.refresh(record)
    return record, True


def replace_transcript(
    db: Session,
    record: StudioTranscript,
    request: ReplaceTranscriptRequest,
    user: User,
) -> StudioTranscript:
    if request.expected_revision != record.revision:
        raise ValueError("studio_transcript_conflict")
    incoming = request.transcript
    if (
        incoming.id != record.id
        or incoming.workspace_id != record.workspace_id
        or incoming.media_ingest_id != record.media_ingest_id
        or incoming.asset_id != record.asset_id
        or incoming.provider != record.provider
        or incoming.provider_version != record.provider_version
    ):
        raise ValueError("studio_transcript_identity_mismatch")
    ingest = db.get(StudioMediaIngest, record.media_ingest_id)
    if not ingest:
        raise ValueError("media_ingest_not_found")
    _validate_timed_items(incoming.segments, _media_duration(ingest), label="transcript_segment")
    current = transcript_out(record)
    now = datetime.now(UTC)
    next_revision = record.revision + 1
    next_version = record.version + 1
    updated = incoming.model_copy(
        update={
            "revision": next_revision,
            "version": next_version,
            "created_by": current.created_by,
            "created_at": current.created_at,
            "updated_by": user.id,
            "updated_at": now,
        }
    )
    record.versions = [
        *(record.versions or []),
        {
            "version": current.version,
            "revision": current.revision,
            "createdAt": now.isoformat(),
            "actorId": user.id,
            "document": current.model_dump(by_alias=True, mode="json"),
        },
    ][-50:]
    record.locale = updated.locale
    record.status = updated.status
    record.revision = next_revision
    record.version = next_version
    record.transcript_document = updated.model_dump(by_alias=True, mode="json")
    record.updated_by = user.id
    emit_event(
        db,
        workspace_id=record.workspace_id,
        event_type="studio.transcript.versioned",
        aggregate_type="transcript",
        aggregate_id=record.id,
        correlation_id=f"transcript:{record.id}",
        actor_id=user.id,
        payload={"revision": next_revision, "version": next_version, "segments": len(updated.segments)},
    )
    db.commit()
    db.refresh(record)
    return record


def decision_set_out(record: StudioEditDecisionSet) -> EditDecisionSetV1:
    return EditDecisionSetV1(
        id=record.id,
        workspace_id=record.workspace_id,
        media_ingest_id=record.media_ingest_id,
        transcript_id=record.transcript_id,
        document_id=record.document_id,
        status=record.status,
        revision=record.revision,
        version=record.version,
        decisions=record.decisions,
        created_by=record.created_by,
        updated_by=record.updated_by,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def create_decision_set(
    db: Session,
    request: CreateEditDecisionSetRequest,
    idempotency_key: str,
    user: User,
) -> tuple[StudioEditDecisionSet, bool]:
    existing = db.scalar(
        select(StudioEditDecisionSet).where(
            StudioEditDecisionSet.workspace_id == request.workspace_id,
            StudioEditDecisionSet.idempotency_key == idempotency_key,
        )
    )
    decisions = [item.model_dump(by_alias=True, mode="json") for item in request.decisions]
    if existing:
        if (
            existing.media_ingest_id != request.media_ingest_id
            or existing.transcript_id != request.transcript_id
            or existing.document_id != request.document_id
            or existing.decisions != decisions
        ):
            raise ValueError("idempotency_payload_conflict")
        return existing, False
    ingest = db.scalar(
        select(StudioMediaIngest).where(
            StudioMediaIngest.id == request.media_ingest_id,
            StudioMediaIngest.workspace_id == request.workspace_id,
        )
    )
    if not ingest or ingest.status != "ready":
        raise ValueError("media_ingest_not_ready")
    _validate_timed_items(request.decisions, _media_duration(ingest), label="edit_decision")
    if request.transcript_id and not db.scalar(
        select(StudioTranscript.id).where(
            StudioTranscript.id == request.transcript_id,
            StudioTranscript.workspace_id == request.workspace_id,
            StudioTranscript.media_ingest_id == ingest.id,
        )
    ):
        raise ValueError("transcript_not_found")
    if request.document_id and not db.scalar(
        select(CreativeDocument.id).where(
            CreativeDocument.id == request.document_id,
            CreativeDocument.workspace_id == request.workspace_id,
        )
    ):
        raise ValueError("studio_document_not_found")
    record = StudioEditDecisionSet(
        workspace_id=request.workspace_id,
        media_ingest_id=ingest.id,
        transcript_id=request.transcript_id,
        document_id=request.document_id,
        status="draft",
        revision=1,
        version=1,
        decisions=decisions,
        versions=[],
        idempotency_key=idempotency_key,
        created_by=user.id,
        updated_by=user.id,
    )
    db.add(record)
    db.flush()
    emit_event(
        db,
        workspace_id=record.workspace_id,
        event_type="studio.edit_decisions.created",
        aggregate_type="edit_decision_set",
        aggregate_id=record.id,
        correlation_id=f"edit-decisions:{record.id}",
        actor_id=user.id,
        payload={"mediaIngestId": ingest.id, "decisions": len(decisions)},
    )
    db.commit()
    db.refresh(record)
    return record, True


def replace_decision_set(
    db: Session,
    record: StudioEditDecisionSet,
    request: ReplaceEditDecisionSetRequest,
    user: User,
) -> StudioEditDecisionSet:
    if request.expected_revision != record.revision:
        raise ValueError("studio_edit_decision_conflict")
    incoming = request.decision_set
    if (
        incoming.id != record.id
        or incoming.workspace_id != record.workspace_id
        or incoming.media_ingest_id != record.media_ingest_id
        or incoming.transcript_id != record.transcript_id
        or incoming.document_id != record.document_id
    ):
        raise ValueError("studio_edit_decision_identity_mismatch")
    ingest = db.get(StudioMediaIngest, record.media_ingest_id)
    if not ingest:
        raise ValueError("media_ingest_not_found")
    _validate_timed_items(incoming.decisions, _media_duration(ingest), label="edit_decision")
    current = decision_set_out(record)
    now = datetime.now(UTC)
    record.versions = [
        *(record.versions or []),
        {
            "version": current.version,
            "revision": current.revision,
            "createdAt": now.isoformat(),
            "actorId": user.id,
            "decisionSet": current.model_dump(by_alias=True, mode="json"),
        },
    ][-50:]
    record.status = incoming.status
    record.revision += 1
    record.version += 1
    record.decisions = [item.model_dump(by_alias=True, mode="json") for item in incoming.decisions]
    record.updated_by = user.id
    emit_event(
        db,
        workspace_id=record.workspace_id,
        event_type="studio.edit_decisions.versioned",
        aggregate_type="edit_decision_set",
        aggregate_id=record.id,
        correlation_id=f"edit-decisions:{record.id}",
        actor_id=user.id,
        payload={"revision": record.revision, "version": record.version, "decisions": len(record.decisions)},
    )
    db.commit()
    db.refresh(record)
    return record


def _floor_frame(microseconds: int, numerator: int, denominator: int) -> int:
    return microseconds * numerator // (1_000_000 * denominator)


def _ceil_frame(microseconds: int, numerator: int, denominator: int) -> int:
    divisor = 1_000_000 * denominator
    return (microseconds * numerator + divisor - 1) // divisor


def _frames_to_microseconds(frames: int, numerator: int, denominator: int) -> int:
    return round(frames * 1_000_000 * denominator / numerator)


def _merge_ranges(ranges: list[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[tuple[int, int]] = []
    for start, end in sorted(ranges):
        if end <= start:
            continue
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def _subtract_ranges(
    ranges: list[tuple[int, int]],
    removals: list[tuple[int, int]],
) -> list[tuple[int, int]]:
    remaining = ranges
    for remove_start, remove_end in _merge_ranges(removals):
        next_remaining: list[tuple[int, int]] = []
        for start, end in remaining:
            if remove_end <= start or remove_start >= end:
                next_remaining.append((start, end))
                continue
            if start < remove_start:
                next_remaining.append((start, min(end, remove_start)))
            if remove_end < end:
                next_remaining.append((max(start, remove_end), end))
        remaining = next_remaining
    return remaining


def _map_frame(
    frame: int,
    retained: list[tuple[int, int, int]],
) -> int | None:
    for old_start, old_end, new_start in retained:
        if old_start <= frame < old_end:
            return new_start + frame - old_start
    return None


def _remap_timed_item(
    raw: dict,
    retained: list[tuple[int, int, int]],
    *,
    numerator: int,
    denominator: int,
    id_prefix: str,
) -> list[dict]:
    timeline = raw["timeline"]
    item_start = int(timeline["startFrame"])
    item_end = item_start + int(timeline["durationFrames"])
    mapped: list[dict] = []
    for part, (old_start, old_end, new_start) in enumerate(retained, start=1):
        start = max(item_start, old_start)
        end = min(item_end, old_end)
        if end <= start:
            continue
        next_item = {**raw, "id": f"{raw['id']}:{id_prefix}:{part}"}
        next_item["timeline"] = {
            "startFrame": new_start + start - old_start,
            "durationFrames": end - start,
        }
        source = raw.get("source")
        if source:
            source_offset = _frames_to_microseconds(start - item_start, numerator, denominator)
            next_item["source"] = {
                **source,
                "startMicroseconds": int(source["startMicroseconds"]) + source_offset,
                "durationMicroseconds": _frames_to_microseconds(end - start, numerator, denominator),
            }
        if "fadeInFrames" in raw or "fadeOutFrames" in raw:
            fade_in = min(int(raw.get("fadeInFrames", 0)), end - start)
            next_item["fadeInFrames"] = fade_in
            next_item["fadeOutFrames"] = min(int(raw.get("fadeOutFrames", 0)), end - start - fade_in)
        mapped.append(next_item)
    return mapped


def apply_edit_decisions(
    db: Session,
    decision_set: StudioEditDecisionSet,
    document: CreativeDocument,
    request: ApplyEditDecisionSetRequest,
    user: User,
) -> CreativeDocument:
    if request.expected_decision_revision != decision_set.revision:
        raise ValueError("studio_edit_decision_conflict")
    if request.expected_document_revision != document.revision:
        raise ValueError("studio_document_conflict")
    if decision_set.status == "applied":
        raise ValueError("studio_edit_decision_already_applied")
    if decision_set.document_id != document.id or decision_set.workspace_id != document.workspace_id:
        raise ValueError("edit_decision_document_mismatch")
    contract = record_to_contract(document)
    timeline = contract.composition.media_timeline
    if contract.content_type != "video" or timeline is None:
        raise ValueError("video_media_timeline_required")
    if len(contract.composition.pages) != 1:
        raise ValueError("edit_decisions_single_page_required")
    source_track = next((track for track in timeline.tracks if track.id == request.source_track_id), None)
    if source_track is None or source_track.kind != "video":
        raise ValueError("edit_decision_source_video_track_not_found")
    enabled_source_clips = [clip for clip in source_track.clips if clip.enabled]
    if len(enabled_source_clips) != 1 or enabled_source_clips[0].source is None:
        raise ValueError("edit_decision_single_source_clip_required")
    ingest = db.get(StudioMediaIngest, decision_set.media_ingest_id)
    if not ingest or ingest.workspace_id != document.workspace_id or ingest.status != "ready":
        raise ValueError("media_ingest_not_ready")
    source_clip = enabled_source_clips[0]
    if source_clip.asset_id != ingest.asset_id:
        raise ValueError("edit_decision_source_asset_mismatch")

    numerator = timeline.frame_rate.numerator
    denominator = timeline.frame_rate.denominator
    source_start = _floor_frame(source_clip.source.start_microseconds, numerator, denominator)
    source_end = source_start + source_clip.timeline.duration_frames
    accepted = [
        decision
        for decision in decision_set_out(decision_set).decisions
        if decision.status == "accepted" and decision.operation in {"keep", "remove"}
    ]
    if not accepted:
        raise ValueError("accepted_edit_decision_required")
    keep_ranges = [
        (
            max(source_start, _floor_frame(item.start_microseconds, numerator, denominator)),
            min(source_end, _ceil_frame(item.end_microseconds, numerator, denominator)),
        )
        for item in accepted
        if item.operation == "keep"
    ]
    base_ranges = _merge_ranges(keep_ranges) if keep_ranges else [(source_start, source_end)]
    removal_ranges = [
        (
            max(source_start, _floor_frame(item.start_microseconds, numerator, denominator)),
            min(source_end, _ceil_frame(item.end_microseconds, numerator, denominator)),
        )
        for item in accepted
        if item.operation == "remove"
    ]
    kept_source = _subtract_ranges(base_ranges, removal_ranges)
    if not kept_source:
        raise ValueError("edit_decisions_remove_entire_timeline")

    retained: list[tuple[int, int, int]] = []
    source_clip_dict = source_clip.model_dump(by_alias=True, mode="json")
    source_clips: list[dict] = []
    output_cursor = 0
    for part, (kept_start, kept_end) in enumerate(kept_source, start=1):
        duration = kept_end - kept_start
        old_start = source_clip.timeline.start_frame + kept_start - source_start
        retained.append((old_start, old_start + duration, output_cursor))
        source_clips.append(
            {
                **source_clip_dict,
                "id": f"{source_clip.id}:select:{part}",
                "timeline": {"startFrame": output_cursor, "durationFrames": duration},
                "source": {
                    "startMicroseconds": source_clip.source.start_microseconds
                    + _frames_to_microseconds(kept_start - source_start, numerator, denominator),
                    "durationMicroseconds": _frames_to_microseconds(duration, numerator, denominator),
                },
            }
        )
        output_cursor += duration

    remapped_tracks: list[dict] = []
    for track in timeline.tracks:
        raw_track = track.model_dump(by_alias=True, mode="json")
        if track.id == request.source_track_id:
            raw_track["clips"] = source_clips
        elif track.kind in {"video", "audio", "overlay"}:
            raw_track["clips"] = [
                mapped
                for clip in raw_track.get("clips", [])
                for mapped in _remap_timed_item(
                    clip,
                    retained,
                    numerator=numerator,
                    denominator=denominator,
                    id_prefix="ripple",
                )
            ]
        elif track.kind == "caption":
            raw_track["cues"] = [
                mapped
                for cue in raw_track.get("cues", [])
                for mapped in _remap_timed_item(
                    cue,
                    retained,
                    numerator=numerator,
                    denominator=denominator,
                    id_prefix="ripple",
                )
            ]
        elif track.kind == "marker":
            markers = []
            for marker in raw_track.get("markers", []):
                frame = _map_frame(int(marker["frame"]), retained)
                if frame is not None:
                    markers.append({**marker, "frame": frame})
            raw_track["markers"] = markers
        remapped_tracks.append(raw_track)

    updated_timeline = MediaTimelineV1.model_validate(
        {
            **timeline.model_dump(by_alias=True, mode="json"),
            "durationFrames": output_cursor,
            "tracks": remapped_tracks,
        }
    )
    composition = CreativeCompositionV1.model_validate(
        {
            **contract.composition.model_dump(by_alias=True, mode="json"),
            "mediaTimeline": updated_timeline.model_dump(by_alias=True, mode="json"),
        }
    )
    updated = replace_document(
        db,
        document,
        ReplaceStudioDocumentRequest(
            expected_revision=request.expected_document_revision,
            document=contract.model_copy(update={"composition": composition}),
        ),
        user,
    )
    now = datetime.now(UTC)
    current_set = decision_set_out(decision_set)
    decision_set.versions = [
        *(decision_set.versions or []),
        {
            "version": current_set.version,
            "revision": current_set.revision,
            "createdAt": now.isoformat(),
            "actorId": user.id,
            "decisionSet": current_set.model_dump(by_alias=True, mode="json"),
        },
    ][-50:]
    decision_set.status = "applied"
    decision_set.revision += 1
    decision_set.version += 1
    decision_set.updated_by = user.id
    emit_event(
        db,
        workspace_id=document.workspace_id,
        event_type="studio.edit_decisions.applied",
        aggregate_type="creative_document",
        aggregate_id=document.id,
        correlation_id=record_to_contract(updated).correlation_id,
        actor_id=user.id,
        payload={
            "decisionSetId": decision_set.id,
            "sourceTrackId": request.source_track_id,
            "acceptedDecisions": len(accepted),
            "outputFrames": output_cursor,
        },
    )
    db.commit()
    db.refresh(updated)
    return updated


def apply_transcript_captions(
    db: Session,
    transcript: StudioTranscript,
    document: CreativeDocument,
    request: ApplyTranscriptCaptionsRequest,
    user: User,
) -> CreativeDocument:
    if transcript.workspace_id != document.workspace_id:
        raise ValueError("transcript_document_workspace_mismatch")
    contract = record_to_contract(document)
    if contract.content_type != "video" or contract.composition.media_timeline is None:
        raise ValueError("video_media_timeline_required")
    if request.expected_document_revision != document.revision:
        raise ValueError("studio_document_conflict")
    current = transcript_out(transcript)
    if transcript.asset_id not in {asset.id for asset in contract.assets}:
        raise ValueError("transcript_asset_not_in_document")
    timeline = contract.composition.media_timeline
    frame_rate = timeline.frame_rate
    cues: list[CaptionCueV1] = []
    previous_end_frame = 0
    for segment in current.segments:
        # Adjacent transcript timestamps commonly sit between frame boundaries.
        # Clamping the next start to the previous rendered end keeps a single
        # caption track deterministic instead of creating a one-frame overlap
        # through floor(start)/ceil(end) rounding.
        start_frame = max(
            previous_end_frame,
            _floor_frame(
                segment.start_microseconds,
                frame_rate.numerator,
                frame_rate.denominator,
            ),
        )
        end_frame = _ceil_frame(
            segment.end_microseconds,
            frame_rate.numerator,
            frame_rate.denominator,
        )
        if (
            start_frame >= timeline.duration_frames
            or end_frame > timeline.duration_frames
            or end_frame <= start_frame
        ):
            raise ValueError("transcript_segment_outside_timeline")
        cues.append(
            CaptionCueV1(
                id=f"caption:{segment.id}",
                timeline=TimelineFrameRangeV1(
                    start_frame=start_frame,
                    duration_frames=max(1, end_frame - start_frame),
                ),
                text=segment.text,
                speaker=segment.speaker,
                source_segment_id=segment.id,
                confidence=segment.confidence,
                style=request.style,
            )
        )
        previous_end_frame = end_frame
    caption_track = CaptionTrackV1(
        id=request.track_id,
        name=request.track_name,
        locale=current.locale,
        cues=cues,
    )
    tracks = [track for track in timeline.tracks if track.id != request.track_id]
    updated_timeline = MediaTimelineV1.model_validate(
        {
            **timeline.model_dump(by_alias=True, mode="json"),
            "tracks": [
                *[track.model_dump(by_alias=True, mode="json") for track in tracks],
                caption_track.model_dump(by_alias=True, mode="json"),
            ],
        }
    )
    composition = CreativeCompositionV1.model_validate(
        {
            **contract.composition.model_dump(by_alias=True, mode="json"),
            "mediaTimeline": updated_timeline.model_dump(by_alias=True, mode="json"),
        }
    )
    incoming = contract.model_copy(update={"composition": composition})
    updated = replace_document(
        db,
        document,
        ReplaceStudioDocumentRequest(
            expected_revision=request.expected_document_revision,
            document=incoming,
        ),
        user,
    )
    emit_event(
        db,
        workspace_id=document.workspace_id,
        event_type="studio.transcript.captions_applied",
        aggregate_type="creative_document",
        aggregate_id=document.id,
        correlation_id=record_to_contract(updated).correlation_id,
        actor_id=user.id,
        payload={"transcriptId": transcript.id, "trackId": request.track_id, "cues": len(cues)},
    )
    db.commit()
    db.refresh(updated)
    return updated
