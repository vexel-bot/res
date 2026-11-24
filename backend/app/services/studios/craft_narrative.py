"""Optional narrative and sound tools for the Claude-driven EffectCraft session."""

import hashlib
import json
import re
import unicodedata
from typing import Literal

from pydantic import Field, model_validator
from sqlalchemy import select

from ...domain.studios.contracts import StudioContract
from ...models import LibraryAsset, StudioVoiceProfile, StudioVoiceVersion
from . import craft_direction, craft_references
from .cast_speech import create_selected_speech_job, selected_speech, selected_speech_asset
from .motion_brief import first_view_direction
from .casting import resolve_cast
from .production_narration import measured_asset

SOL_ID = "workspace.sol-altkid"


def enabled(profile, engine, instruction, brief_format=""):
    if engine != "effectcraft" or profile == "general":
        return False
    if profile == "narrative_motion":
        return True
    text = unicodedata.normalize("NFKD", (instruction + " " + brief_format).casefold()).encode("ascii", "ignore").decode()
    motion = re.search(r"\b(motion|mograph|animacao|animad[oa])\b", text)
    story = re.search(r"\b(narrativ\w*|story\w*|sol|historia|roteiro|gancho|virada|anuncio|filme|tese|explicativ\w*|startup\w*)\b", text)
    return bool(motion and story)


def context(workspace_id):
    sol = next((item for item in craft_references.reference_index(workspace_id) if item["id"] == SOL_ID), None)
    cards = [card["id"] for card in craft_direction.reference_index() if card["id"].startswith("story.")]
    return {
        "primaryReference": sol or {"id": SOL_ID, "temporalAvailable": False},
        "storyRepertoireIds": cards,
        "firstViewDirection": first_view_direction(),
        "optionalMethods": [
            "Compare two opening hypotheses that leave the viewer with different questions. Decide what a visible action or sound lets them infer before you explain it.",
            "Try a rough native cut before polish if timing or order is uncertain. A hold, a cut or a missing answer can shift the reading as much as an effect.",
            "On the same native base try a different reveal time, a visual bridge with one persistent object, or a mix without the bed. Compare the evidence and apply whichever edit serves your intent.",
            "Direct voice and sound by short takes. Move words, music and effects independently and review the mix or isolate layers. Audio metrics are not listening.",
            "These are optional editorial tools. You own the story, structure, effects, sound, evaluation and final edit.",
        ],
    }


class Opening(StudioContract):
    premise: str = Field(min_length=1, max_length=600)
    viewer_question: str = Field(min_length=1, max_length=600)


class Beat(StudioContract):
    at_seconds: float = Field(ge=0, allow_inf_nan=False)
    initial_state: str = Field(min_length=1, max_length=600)
    event: str = Field(min_length=1, max_length=600)
    inference: str = Field(min_length=1, max_length=600)


class FirstViewReview(StudioContract):
    subject_in_plain_words: str = Field(min_length=1, max_length=600)
    evidence_on_screen: str = Field(min_length=1, max_length=600)
    evidence_readable_at: float = Field(ge=0, allow_inf_nan=False)
    comparison_ends_at: float = Field(ge=0, allow_inf_nan=False)
    likely_misreading: str = Field(min_length=1, max_length=600)
    editorial_decision: str = Field(min_length=1, max_length=600)
    source: Literal["editorial_review", "first_time_viewer"]

    @model_validator(mode="after")
    def validate_interval(self):
        if self.comparison_ends_at < self.evidence_readable_at:
            raise ValueError("Comparison ends before its evidence is readable")
        return self


class StoryEdit(StudioContract):
    openings: list[Opening] = Field(min_length=2, max_length=2)
    selected_opening: Literal[1, 2]
    choice: str = Field(min_length=1, max_length=1000)
    beats: list[Beat] = Field(min_length=1, max_length=16)
    payoff: str = Field(min_length=1, max_length=1000)
    first_view_review: FirstViewReview | None = None


def record_story(db, job, args):
    plan = StoryEdit.model_validate(args)
    history = (job.result_payload or {}).get("storyEdits", [])
    item = plan.model_dump(mode="json", by_alias=True, exclude_none=True)
    if history and history[-1]["plan"] == item:
        return history[-1]
    note = {"version": (history[-1]["version"] + 1 if history else 1), "plan": item}
    job.result_payload = {**(job.result_payload or {}), "storyEdits": [*history[-19:], note]}
    db.commit()
    return note


def audio_isolation_script(layer_ids):
    if (not isinstance(layer_ids, list) or not 1 <= len(layer_ids) <= 32
            or any(type(layer) is not int or not 0 < layer <= 2**53 - 1 for layer in layer_ids)
            or len(set(layer_ids)) != len(layer_ids)):
        raise ValueError("craft_audio_layer_ids_invalid")
    return (
        "var c=app.project.activeItem, keep=" + json.dumps(layer_ids) + ", found=0;"
        "for(var i=1;i<=c.numLayers;i++){var l=c.layer(i);var chosen=keep.indexOf(l.id)>=0;"
        "if(chosen&&l.hasAudio&&l.audioEnabled)found++;else if(l.audioEnabled)l.audioEnabled=false;}"
        "if(found!==keep.length)throw new Error('Requested IDs must be enabled audio layers in this composition');"
    )


def audio_source(asset, workspace_id):
    if (not asset or asset.workspace_id != workspace_id or asset.lifecycle_status != "active"
            or asset.media_type not in {"audio/wav", "audio/mpeg", "audio/flac"}
            or not asset.storage_key or not asset.checksum_sha256):
        return False
    metadata = asset.object_metadata or {}
    resource = metadata.get("editingResource") or {}
    return metadata.get("rightsStatus") != "restricted" and (
        metadata.get("rightsStatus") == "verified" or bool(resource.get("usageEvidence"))
    )


def sound_assets(db, workspace_id, query):
    terms = query.casefold().split()
    rows = db.scalars(select(LibraryAsset).where(
        LibraryAsset.workspace_id == workspace_id, LibraryAsset.lifecycle_status == "active",
        LibraryAsset.asset_type == "audio",
    ).order_by(LibraryAsset.created_at.desc()))
    results = []
    for asset in rows:
        resource = (asset.object_metadata or {}).get("editingResource") or {}
        text = " ".join([asset.title, *(asset.tags or []), resource.get("description", "") or ""]).casefold()
        if audio_source(asset, workspace_id) and all(term in text for term in terms):
            results.append({"assetId": asset.id, "title": asset.title, "mediaType": asset.media_type,
                            "kind": resource.get("kind"), "sourceUrl": resource.get("sourceUrl")})
            if len(results) == 16:
                break
    return results


def stage_sound(db, record, job, draft, manifests, asset_id):
    asset = db.get(LibraryAsset, asset_id)
    if not audio_source(asset, record.workspace_id):
        raise ValueError("craft_workspace_audio_unavailable")
    _, seconds = measured_asset(db, record, asset.id, asset.checksum_sha256)
    return craft_direction.stage_material(db, job, draft, manifests, asset, "workspace-audio:" + asset.id, {
        "assetId": asset.id, "title": asset.title, "mediaType": asset.media_type,
        "durationSeconds": seconds, "provenance": (asset.object_metadata or {}).get("editingResource", {}),
    })


def voices(db, workspace_id, voice_ref):
    if voice_ref:
        try:
            voice = selected_speech(db, workspace_id, voice_ref)
        except ValueError:
            return []
        if voice.locale.casefold() in {"pt", "pt-br"}:
            return [{"id": voice.voice_version_id, "locale": voice.locale, "source": "document_voice"}]
        return []
    rows = db.execute(select(StudioVoiceVersion, StudioVoiceProfile).join(
        StudioVoiceProfile, StudioVoiceVersion.profile_id == StudioVoiceProfile.id,
    ).where(
        StudioVoiceVersion.workspace_id == workspace_id, StudioVoiceProfile.workspace_id == workspace_id,
        StudioVoiceProfile.status == "active", StudioVoiceProfile.voice_type == "stock",
        StudioVoiceProfile.locale.in_(["pt-BR", "pt-br", "pt"]),
    ).order_by(StudioVoiceProfile.display_name, StudioVoiceVersion.version.desc()))
    results = []
    profiles = set()
    for version, profile in rows:
        if profile.id in profiles:
            continue
        try:
            ref = resolve_cast(db, workspace_id, None, version.id)["voice"]
            selected_speech(db, workspace_id, ref)
        except ValueError:
            continue
        profiles.add(profile.id)
        results.append({"id": version.id, "name": profile.display_name, "locale": profile.locale, "source": "stock"})
        if len(results) == 20:
            break
    return results


def voice_take(db, record, job, user, draft, manifests, voice_ref, args):
    from .jobs import execute_job_once

    voice_id = args["voiceId"]
    text = args["text"].strip()
    if not 1 <= len(text) <= 600:
        raise ValueError("craft_voice_take_text_invalid")
    if voice_id not in {item["id"] for item in voices(db, record.workspace_id, voice_ref)}:
        return {"status": "unavailable", "reason": "No eligible local Portuguese voice for this selection.",
                "alternatives": ["find_material_sources", "Edit with text or sound without narration."]}
    ref = resolve_cast(db, record.workspace_id, None, voice_id)["voice"]
    selection = selected_speech(db, record.workspace_id, ref)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    key = f"craft-take:{job.id}:{voice_id}:{digest}"
    speech_job, _ = create_selected_speech_job(
        db, selection, text, user, workspace_id=record.workspace_id, document_id=record.id,
        key=key, correlation_id=job.id,
    )
    status = execute_job_once(db, speech_job)
    if status != "succeeded":
        return {"status": status, "speechJobId": speech_job.id, "reason": speech_job.error_code}
    asset = selected_speech_asset(db, speech_job, ref, text)
    _, seconds = measured_asset(db, record, asset.id, asset.checksum_sha256)
    return craft_direction.stage_material(db, job, draft, manifests, asset, key, {
        "status": "ready", "assetId": asset.id, "title": asset.title, "mediaType": asset.media_type,
        "durationSeconds": seconds, "speechJobId": speech_job.id, "providerChargeUsd": 0,
    })
