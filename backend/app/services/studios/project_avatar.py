"""Immutable project plans join an authorized appearance to the final selected speech."""

import hashlib
import json
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import select

from ...domain.studios.contracts import AvatarVideoJobResultV2, AvatarVideoRequestV2, CreateStudioDocumentRequest
from ...models import BrandProfile, CreativeDocument, LibraryAsset, StudioGenerationJob, StudioIdentityVersion
from ..brand import brand_readiness
from .cast_speech import selected_speech_asset
from .casting import resolve_cast
from .jobs import (
    _avatar_v2_hybrid_binding,
    require_avatar_provider_admission,
    require_avatar_v2_media_binding,
    require_avatar_video_binding,
)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def materials(db, row):
    payload = row.payload
    if payload.get("format") != "video":
        raise ValueError("avatar_video_project_required")
    if not payload.get("directionId"):
        raise ValueError("narration_direction_required")
    refs = resolve_cast(db, row.workspace_id, payload.get("identityVersionId"), payload.get("voiceVersionId"))
    if not refs.get("identity") or not refs.get("voice"):
        raise ValueError("avatar_appearance_and_voice_required")
    if payload.get("casting") != refs:
        raise ValueError("cast_version_reference_mismatch")
    identity = db.get(StudioIdentityVersion, refs["identity"]["id"])
    if "avatar.generate" not in (identity.capabilities or []):
        raise ValueError("identity_capability_missing")
    narration = payload.get("narration") or {}
    job = db.get(StudioGenerationJob, narration.get("jobId")) if narration.get("jobId") else None
    if not job or job.workspace_id != row.workspace_id or job.correlation_id != f"department-narration:{row.id}":
        raise ValueError("avatar_final_narration_required")
    if payload.get("narrationDraft") and payload["narrationDraft"] != narration.get("text"):
        raise ValueError("avatar_narration_draft_not_generated")
    audio = selected_speech_asset(db, job, refs["voice"], narration["text"])
    if not audio:
        raise ValueError("avatar_final_narration_required")
    duration = (job.result_payload.get("speech") or {}).get("durationMs")
    if not isinstance(duration, int) or isinstance(duration, bool) or duration <= 0:
        raise ValueError("avatar_driving_audio_duration_mismatch")
    image = next(
        (
            item
            for asset_id in identity.sample_asset_ids
            if (item := db.get(LibraryAsset, asset_id))
            and item.workspace_id == row.workspace_id
            and item.lifecycle_status == "active"
            and item.storage_key
            and item.checksum_sha256
            and (item.media_type or "").startswith("image/")
        ),
        None,
    )
    if not image:
        raise ValueError("identity_image_sample_required")
    return refs, job, image, audio, duration


def plan(db, row, performance_direction: str):
    from .hybrid_video import hybrid_capability_manifest

    refs, narration, image, audio, duration = materials(db, row)
    manifest = hybrid_capability_manifest()
    candidates = sorted(
        (
            p
            for p in manifest.profiles
            if p.capability == "avatar_video" and p.environment == "local" and "image_audio_to_avatar" in p.operations
        ),
        key=lambda p: (p.qualification_state != "qualified", p.profile_id),
    )
    blocker = "avatar_provider_runtime_unavailable"
    for profile in candidates:
        try:
            request = AvatarVideoRequestV2(
                expected_document_revision=1,
                scene_id="presenter",
                requirement_id="project-presenter",
                script=row.payload["narration"]["text"],
                reference_image_asset_id=image.id,
                reference_image_checksum_sha256=image.checksum_sha256,
                driving_audio_asset_id=audio.id,
                driving_audio_checksum_sha256=audio.checksum_sha256,
                driving_audio_duration_ms=duration,
                driving_audio_origin="cloned_voice_synthesis"
                if narration.job_type == "voice_clone"
                else "stock_voice_synthesis",
                performance_direction=performance_direction,
                acceptance_criteria=["Preservar a aparência autorizada", "Preservar a fala final e a voz escolhida"],
                preserve=["appearance", "selected_voice", "final_speech"],
                profile_id=profile.profile_id,
            )
            raw = request.model_dump(by_alias=True, mode="json")
            hybrid = _avatar_v2_hybrid_binding(raw, profile.provider_id)
            provider = require_avatar_provider_admission(db, provider_name=profile.provider_id, require_runtime=True)
        except ValueError as error:
            blocker = str(error)
            continue
        binding = {
            "projectId": row.id,
            "workspaceId": row.workspace_id,
            "directionId": row.payload["directionId"],
            "narrationJobId": narration.id,
            "casting": refs,
            "request": raw,
            "hybrid": hybrid,
            "provider": provider,
        }
        fingerprint = digest(binding)
        document_id = str(uuid5(NAMESPACE_URL, f"clicko-project-avatar:{row.workspace_id}:{row.id}:{fingerprint}"))
        return {
            "schemaVersion": "clicko.project-avatar-plan.v1",
            "planDigestSha256": fingerprint,
            "documentId": document_id,
            "durationSeconds": duration / 1000,
            "operation": "generate_avatar",
            "expectedRevision": row.payload["revision"],
            "binding": binding,
        }
    raise ValueError(blocker)


def context_request(db, row, avatar_plan):
    binding = avatar_plan["binding"]
    brand = db.scalar(select(BrandProfile).where(BrandProfile.workspace_id == row.workspace_id))
    if not brand:
        raise ValueError("studio_brand_revision_mismatch")
    request = binding["request"]
    return CreateStudioDocumentRequest.model_validate(
        {
            "workspaceId": row.workspace_id,
            "title": row.payload["title"],
            "contentType": "presenter",
            "brandRevision": brand_readiness(brand)["revision"],
            "identityRef": binding["casting"]["identity"],
            "voiceRef": binding["casting"]["voice"],
            "brief": {"objective": row.payload["objective"], "audience": row.payload["audience"]},
            "composition": {
                "pages": [
                    {
                        "id": "presenter",
                        "width": request["width"],
                        "height": request["height"],
                        "durationMs": request["drivingAudioDurationMs"],
                        "layers": [],
                    }
                ],
                "tracks": [],
                "narrative": {"departmentProjectId": row.id, "avatarPlanDigestSha256": avatar_plan["planDigestSha256"]},
            },
            "assets": [
                {
                    "id": asset.id,
                    "mediaType": asset.media_type,
                    "checksum": asset.checksum_sha256,
                }
                for asset in (
                    db.get(LibraryAsset, request["referenceImageAssetId"]),
                    db.get(LibraryAsset, request["drivingAudioAssetId"]),
                )
            ],
        }
    )


def current_job(db, row):
    saved = row.payload.get("avatar") or {}
    job = db.get(StudioGenerationJob, saved.get("jobId")) if saved.get("jobId") else None
    if saved.get("jobId") and (
        not job or job.workspace_id != row.workspace_id or job.correlation_id != f"department-avatar:{row.id}"
    ):
        raise ValueError("avatar_project_job_conflict")
    return job


def completed_asset(db, row):
    """A completed artifact remains reopenable offline, but never after cast/script changes."""
    refs, narration, image, audio, duration = materials(db, row)
    saved = row.payload.get("avatar") or {}
    job = current_job(db, row)
    if not job or job.status != "succeeded":
        return None
    if saved.get("narrationJobId") != narration.id or saved.get("directionId") != row.payload["directionId"]:
        raise ValueError("avatar_project_materials_changed")
    request = AvatarVideoRequestV2.model_validate(
        {k: v for k, v in job.request_payload.items() if k != "executionBinding"}
    )
    if (
        job.identity_version_id != refs["identity"]["id"]
        or job.voice_version_id != refs["voice"]["id"]
        or request.driving_audio_asset_id != audio.id
        or request.reference_image_asset_id != image.id
        or request.driving_audio_duration_ms != duration
        or request.script != row.payload["narration"]["text"]
    ):
        raise ValueError("avatar_project_materials_changed")
    require_avatar_video_binding(
        db,
        workspace_id=row.workspace_id,
        document_id=job.document_id,
        identity_version_id=job.identity_version_id,
        voice_version_id=job.voice_version_id,
        consent_grant_id=job.consent_grant_id,
        independent_cast=True,
    )
    context = db.get(CreativeDocument, job.document_id)
    if context.revision != request.expected_document_revision:
        raise ValueError("studio_document_conflict")
    require_avatar_v2_media_binding(
        db,
        workspace_id=row.workspace_id,
        document_id=job.document_id,
        identity_version_id=job.identity_version_id,
        voice_version_id=job.voice_version_id,
        payload=request.model_dump(by_alias=True, mode="json"),
    )
    result = AvatarVideoJobResultV2.model_validate(job.result_payload)
    asset = db.get(LibraryAsset, result.asset_id)
    if (
        not asset
        or asset.workspace_id != row.workspace_id
        or asset.lifecycle_status != "active"
        or not asset.storage_key
        or asset.media_type != "video/mp4"
        or asset.checksum_sha256 != result.checksum_sha256
        or result.generation_job_id != job.id
        or result.document_id != job.document_id
        or result.identity_version_id != job.identity_version_id
        or result.voice_version_id != job.voice_version_id
        or result.consent_grant_id != job.consent_grant_id
        or result.document_revision != context.revision
        or result.profile_id != request.profile_id
        or result.reference_image_asset_id != image.id
        or result.execution_binding_digest_sha256
        != job.request_payload["executionBinding"]["hybrid"]["bindingDigestSha256"]
        or abs(result.avatar.duration_ms - duration) > 150
        or result.driving_audio_asset_id != audio.id
        or result.driving_audio_checksum_sha256 != audio.checksum_sha256
        or result.reference_image_checksum_sha256 != image.checksum_sha256
        or result.script_digest_sha256 != hashlib.sha256(request.script.encode()).hexdigest()
        or (asset.object_metadata or {}).get("avatarVideoJobResult") != job.result_payload
    ):
        raise ValueError("avatar_project_result_conflict")
    return asset
