"""Conservative source assembly and captions using canonical transcript contracts."""

from __future__ import annotations

from fractions import Fraction

from ...domain.studios.contextual_editing import digest
from ...domain.studios.contracts import CaptionCueV1, CaptionTrackV1, MarkerTrackV1, TranscriptDocumentV1
from ...models import StudioTranscript
from .transcripts import _subtract_ranges


def bound_transcript(db, document, beat, clip):
    record = db.get(StudioTranscript, beat.transcript_id) if beat.transcript_id else None
    if not record or record.workspace_id != document.workspace_id or record.asset_id != clip.asset_id:
        raise ValueError("editing_transcript_missing")
    if record.revision != beat.transcript_revision or record.status not in {"ready", "reviewed"}:
        raise ValueError("editing_transcript_conflict")
    asset = next(a for a in document.assets if a.id == clip.asset_id)
    if record.source_checksum_sha256 and record.source_checksum_sha256 != asset.checksum:
        raise ValueError("editing_transcript_source_conflict")
    transcript = TranscriptDocumentV1.model_validate(record.transcript_document)
    if transcript.asset_id != clip.asset_id or transcript.workspace_id != document.workspace_id:
        raise ValueError("editing_transcript_source_conflict")
    return transcript.model_copy(update={"status": record.status, "revision": record.revision}), {
        "revision": record.revision,
        "digest": digest(record.transcript_document),
        "assetId": clip.asset_id,
        "status": record.status,
    }


def validate_transcript_bindings(db, document, bindings):
    for transcript_id, binding in bindings.items():
        record = db.get(StudioTranscript, transcript_id)
        if (
            not record
            or record.workspace_id != document.workspace_id
            or record.asset_id != binding["assetId"]
            or record.revision != binding["revision"]
            or record.status != binding["status"]
            or digest(record.transcript_document) != binding["digest"]
        ):
            raise ValueError("editing_transcript_conflict")


def _range(clip, beat, transcript):
    """Source decisions may shorten margins; every transcript segment stays intact."""
    source = clip.source
    if not source or clip.playback_rate != 1 or clip.effects or clip.keyframes or clip.locked:
        raise ValueError("editing_source_selection_incompatible")
    start, end = source.start_microseconds, source.start_microseconds + source.duration_microseconds
    decisions = [d for d in beat.source_decisions if d.status != "rejected" and d.operation != "marker"]
    if any(d.start_microseconds < start or d.end_microseconds > end for d in decisions):
        raise ValueError("editing_selection_out_of_bounds")
    keeps = [(d.start_microseconds, d.end_microseconds) for d in decisions if d.operation == "keep"]
    retained = _subtract_ranges(
        keeps or [(start, end)],
        [(d.start_microseconds, d.end_microseconds) for d in decisions if d.operation == "remove"],
    )
    if len(retained) != 1:
        raise ValueError("editing_contiguous_selection_required")
    left, right = retained[0]
    spoken = [s for s in transcript.segments if s.start_microseconds < end and s.end_microseconds > start]
    if not spoken or any(s.start_microseconds < left or s.end_microseconds > right for s in spoken):
        raise ValueError("editing_selection_would_change_message")
    return left, right


def assemble(document, beats, transcripts, order):
    """Return a new timeline and trace without mutating the source on failure.

    Cross-scene tracks require an explicit future reconform policy; never drop them.
    """
    timeline = document.composition.media_timeline.model_copy(deep=True)
    changes = any(any(d.status != "rejected" and d.operation != "marker" for d in b.source_decisions) for b in beats)
    if not changes and not order:
        return timeline, []
    videos = [t for t in timeline.tracks if t.kind == "video" and any(c.enabled for c in t.clips)]
    if len(videos) != 1 or videos[0].locked or any(not c.enabled for c in videos[0].clips):
        raise ValueError("editing_assembly_primary_track_required")
    primary = videos[0]
    clips = sorted(primary.clips, key=lambda c: c.timeline.start_frame)
    original_order = [c.id for c in clips]
    if order and set(order) != set(original_order):
        raise ValueError("editing_order_must_preserve_all_clips")
    cursor = 0
    for clip in clips:
        if clip.timeline.start_frame != cursor or clip.locked:
            raise ValueError("editing_assembly_contiguous_unlocked_required")
        cursor += clip.timeline.duration_frames
    if cursor != timeline.duration_frames:
        raise ValueError("editing_assembly_contiguous_unlocked_required")
    fps = Fraction(timeline.frame_rate.numerator, timeline.frame_rate.denominator)
    by_id = {c.id: c for c in clips}
    spans = {c.id: (c.timeline.start_frame, c.timeline.start_frame + c.timeline.duration_frames) for c in clips}
    for beat in beats:
        if not any(d.status != "rejected" and d.operation != "marker" for d in beat.source_decisions):
            continue
        transcript = transcripts.get(beat.clip_id)
        if transcript is None or transcript.status != "reviewed":
            raise ValueError("editing_reviewed_transcript_required_for_selection")
        clip = by_id[beat.clip_id]
        left, right = _range(clip, beat, transcript)
        # Round outwards, so frame quantisation cannot cut into a retained syllable.
        offset = (left - clip.source.start_microseconds) * fps // 1_000_000
        end = -(-(right - clip.source.start_microseconds) * fps // 1_000_000)
        if end > clip.timeline.duration_frames or offset >= end:
            raise ValueError("editing_selection_out_of_bounds")
        old = clip.timeline.start_frame
        spans[clip.id] = (old + int(offset), old + int(end))
        clip.source.start_microseconds += round(offset * 1_000_000 / fps)
        clip.source.duration_microseconds = round((end - offset) * 1_000_000 / fps)
        clip.timeline.duration_frames = int(end - offset)
    cursor, mappings, trace = 0, [], []
    for clip_id in order or original_order:
        clip = by_id[clip_id]
        left, right = spans[clip_id]
        mappings.append((left, right, cursor))
        trace.append(
            {
                "clipId": clip_id,
                "fromStartFrame": left,
                "fromEndFrame": right,
                "toStartFrame": cursor,
                "durationFrames": right - left,
            }
        )
        clip.timeline.start_frame = cursor
        cursor += right - left
    for track in timeline.tracks:
        if track.id == primary.id or track.kind == "mask":
            continue
        items = getattr(track, "clips", getattr(track, "cues", getattr(track, "markers", [])))
        for item in items:
            start = item.frame if track.kind == "marker" else item.timeline.start_frame
            end = start + 1 if track.kind == "marker" else start + item.timeline.duration_frames
            match = next(((a, c) for a, b, c in mappings if a <= start and end <= b), None)
            if match is None or track.locked or getattr(item, "locked", False):
                raise ValueError("editing_cross_scene_reconform_required")
            if track.kind == "marker":
                item.frame = match[1] + start - match[0]
            else:
                item.timeline.start_frame = match[1] + start - match[0]
    primary.clips = [by_id[i] for i in order or original_order]
    timeline.duration_frames = cursor
    return type(timeline).model_validate(timeline.model_dump(mode="json", by_alias=True)), trace


def transcript_captions(document, beat, clip, transcript):
    if clip.source is None or any(e.get("kind") == "freeze" for e in clip.effects):
        raise ValueError("editing_caption_source_incompatible")
    timeline = document.composition.media_timeline
    fps = Fraction(timeline.frame_rate.numerator, timeline.frame_rate.denominator)
    rate = Fraction(str(clip.playback_rate))
    start = clip.source.start_microseconds
    end = start + clip.source.duration_microseconds
    cues = []
    for index, segment in enumerate(transcript.segments):
        if segment.start_microseconds >= end or segment.end_microseconds <= start:
            continue
        if segment.start_microseconds < start or segment.end_microseconds > end:
            raise ValueError("editing_caption_incomplete_sentence")
        # Word timings allow segmentation without inventing or paraphrasing any text.
        groups = []
        words = segment.words
        if words and " ".join(w.text for w in words).split() == segment.text.split():
            group = []
            for word in words:
                if group and len(" ".join(w.text for w in [*group, word])) > 48:
                    groups.append(
                        (group[0].start_microseconds, group[-1].end_microseconds, " ".join(w.text for w in group))
                    )
                    group = []
                group.append(word)
            if group:
                groups.append(
                    (group[0].start_microseconds, group[-1].end_microseconds, " ".join(w.text for w in group))
                )
        else:
            groups.append((segment.start_microseconds, segment.end_microseconds, segment.text))
        for part, (left, right, text) in enumerate(groups):
            a = round((left - start) * fps / (1_000_000 * rate))
            b = round((right - start) * fps / (1_000_000 * rate))
            if b <= a or b > clip.timeline.duration_frames:
                raise ValueError("editing_caption_timing_unrepresentable")
            cues.append(
                CaptionCueV1(
                    id=f"editorial-{digest([beat.id, index, part])[:24]}",
                    timeline={"startFrame": clip.timeline.start_frame + a, "durationFrames": b - a},
                    text=text,
                    source_segment_id=segment.id,
                    speaker=segment.speaker,
                    confidence=segment.confidence,
                    style={"fontSize": max(16, round(document.composition.pages[0].width * 0.045))},
                )
            )
    if not cues:
        raise ValueError("editing_caption_transcript_empty")
    return CaptionTrackV1(id=f"editorial-track-{beat.id}", locale=transcript.locale, cues=cues)


def decision_markers(document, beats, clips):
    """Markers retain the existing source decision vocabulary and never imply acceptance."""
    timeline = document.composition.media_timeline
    fps = Fraction(timeline.frame_rate.numerator, timeline.frame_rate.denominator)
    markers = []
    for beat in beats:
        clip = clips[beat.clip_id]
        for item in beat.source_decisions:
            if item.operation != "marker" or item.status == "rejected" or not clip.source:
                continue
            frame = round(
                (item.start_microseconds - clip.source.start_microseconds)
                * fps
                / (1_000_000 * Fraction(str(clip.playback_rate)))
            )
            if not 0 <= frame < clip.timeline.duration_frames:
                raise ValueError("editing_marker_out_of_bounds")
            markers.append(
                {
                    "id": f"editorial-marker-{digest([beat.id, item.id])[:20]}",
                    "frame": clip.timeline.start_frame + frame,
                    "label": item.reason or "Revisar trecho",
                }
            )
    return MarkerTrackV1(id="editorial-markers", markers=markers) if markers else None
