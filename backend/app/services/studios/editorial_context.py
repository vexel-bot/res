"""Editorial evidence and authoritative merging, independent of the LLM vendor."""

import re
import unicodedata

from .contextual_assembly import bound_transcript, validate_transcript_bindings


def transcript_context(db, document, direction):
    timeline = document.composition.media_timeline
    clips = {
        c.id: c for t in (timeline.tracks if timeline else []) if t.kind == "video" for c in t.clips if c.enabled
    }
    bindings, evidence = {}, []
    for beat in direction.beats:
        if not beat.transcript_id:
            continue
        if beat.clip_id not in clips:
            raise ValueError("editing_beat_clip_not_found")
        transcript, binding = bound_transcript(db, document, beat, clips[beat.clip_id])
        bindings[transcript.id] = binding
        evidence.append(
            {
                "clipId": beat.clip_id,
                "binding": binding,
                "transcript": transcript.model_dump(mode="json", by_alias=True),
            }
        )
    return bindings, evidence


def validate_planning_sources(db, document, payload):
    validate_transcript_bindings(db, document, payload.get("sourceTranscripts", {}))


def normalized_text(value):
    return " ".join(unicodedata.normalize("NFC", value).casefold().split()).strip()


def approved_text_units(direction, evidence):
    # Whole sentences/segments only: a substring could drop a negation or a condition.
    units = [direction.intent.script, *direction.intent.locked_facts]
    units.extend(re.split(r"(?<=[.!?])\s+|\n+", direction.intent.script))
    units.extend(b.on_screen_text for b in direction.beats)
    for item in evidence:
        units.extend(s["text"] for s in item["transcript"]["segments"])
    return {normalized_text(text) for text in units if text.strip()}


def merge_direction(original, generated, evidence):
    """Keep user bindings; model-authored factual text requires literal evidence.

    Returned issues are actionable blockers; rejected text never reaches the draft.
    This is a conservative admission policy, not a semantic truth detector.
    """
    candidate = original.model_copy(deep=True)
    supplied = {beat.clip_id: beat for beat in original.beats}
    accepted, issues = {}, []
    known_text = approved_text_units(original, evidence)
    for beat in generated.beats:
        if beat.clip_id in accepted:
            raise ValueError("editing_duplicate_beat")
        updated = beat.model_copy(deep=True)
        old = supplied.get(beat.clip_id)
        if old:
            # Explicit materials and copy remain fixed; optional AI choices can fill absent fields.
            updated.id = old.id
            updated.purpose = old.purpose
            for field in ("transcript_id", "transcript_revision", "caption_from_transcript", "source_decisions"):
                setattr(updated, field, getattr(old, field))
            for field in (
                "support_asset_id",
                "mask_asset_id",
                "audio_asset_id",
                "support_query",
                "on_screen_text",
                "composition_technique_id",
            ):
                if getattr(old, field):
                    setattr(updated, field, getattr(old, field))
            if old.audio_asset_id:
                updated.audio_role = old.audio_role
            if old.support_asset_id:
                updated.support_source_start_microseconds = old.support_source_start_microseconds
        if updated.caption_from_transcript:
            updated.on_screen_text = ""
        elif updated.on_screen_text and normalized_text(updated.on_screen_text) not in known_text:
            issues.append(
                {
                    "code": "editing_text_evidence_required",
                    "clipId": updated.clip_id,
                    "proposedText": updated.on_screen_text,
                    "message": "O texto proposto precisa de uma fonte ou revisão para preservar os fatos.",
                }
            )
            updated.on_screen_text = ""
        accepted[updated.clip_id] = updated
    candidate.beats = [accepted.pop(b.clip_id, b.model_copy(deep=True)) for b in original.beats]
    candidate.beats.extend(accepted.values())
    candidate.required_techniques = list(dict.fromkeys([*original.required_techniques, *generated.required_techniques]))
    candidate.reference_technique_ids = list(
        dict.fromkeys([*original.reference_technique_ids, *generated.reference_technique_ids])
    )
    candidate.clip_order = original.clip_order or generated.clip_order
    existing_needs = {n.id for n in original.material_needs}
    candidate.material_needs = [
        *original.material_needs,
        *(n for n in generated.material_needs if n.id not in existing_needs),
    ]
    # Reordering can change causality despite retaining every sentence. Keep the source pending review.
    if not original.clip_order and generated.clip_order:
        candidate.clip_order = []
        issues.append(
            {
                "code": "editing_order_review_required",
                "clipId": "timeline",
                "proposedOrder": generated.clip_order,
                "message": "A nova ordem precisa ser revisada para preservar a relação entre as cenas.",
            }
        )
    return type(candidate).model_validate(candidate.model_dump()), issues
