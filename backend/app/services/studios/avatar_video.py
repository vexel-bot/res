from __future__ import annotations

import hashlib
import tempfile
from collections.abc import Callable
from contextlib import ExitStack
from pathlib import Path, PurePosixPath

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...domain.studios.contracts import (
    AvatarVideoJobResultV1,
    AvatarVideoJobResultV2,
    AvatarVideoRequestV1,
    AvatarVideoRequestV2,
)
from ...domain.studios.providers import AVATAR_VIDEO_PROVIDERS
from ...models import (
    CreativeDocument,
    LibraryAsset,
    StudioGenerationJob,
    StudioIdentityVersion,
    StudioVoiceVersion,
)
from ..object_storage import get_object_storage, object_key, sha256_file
from .compatibility import record_to_contract
from .jobs import (
    _avatar_v2_hybrid_binding,
    require_avatar_provider_admission,
    require_avatar_v2_media_binding,
    require_avatar_video_binding,
)
from .kernel import emit_event


def _existing_result(db: Session, job: StudioGenerationJob) -> dict | None:
    assets = db.scalars(
        select(LibraryAsset).where(
            LibraryAsset.workspace_id == job.workspace_id,
            LibraryAsset.asset_type == "video",
            LibraryAsset.lifecycle_status == "active",
        )
    ).all()
    for asset in assets:
        metadata = asset.object_metadata or {}
        if metadata.get("generationJobId") != job.id or metadata.get("derivation") != "avatar_video":
            continue
        result = metadata.get("avatarVideoJobResult")
        if isinstance(result, dict):
            result_type = (
                AvatarVideoJobResultV2
                if result.get("schemaVersion") == "studio.avatar-video-job-result.v2"
                else AvatarVideoJobResultV1
            )
            return result_type.model_validate(result).model_dump(
                by_alias=True, mode="json"
            )
    return None


def _version_assets(
    db: Session,
    *,
    workspace_id: str,
    asset_ids: list[str],
    expected_prefix: str,
) -> list[LibraryAsset]:
    unique_ids = list(dict.fromkeys(asset_ids))
    if not unique_ids:
        raise ValueError(f"{expected_prefix}_sample_required")
    records = db.scalars(
        select(LibraryAsset).where(
            LibraryAsset.id.in_(unique_ids),
            LibraryAsset.workspace_id == workspace_id,
            LibraryAsset.lifecycle_status == "active",
        )
    ).all()
    by_id = {asset.id: asset for asset in records}
    if len(by_id) != len(unique_ids):
        raise ValueError(f"{expected_prefix}_sample_not_found")
    ordered = [by_id[asset_id] for asset_id in unique_ids]
    for asset in ordered:
        if not asset.storage_key or not asset.checksum_sha256 or not asset.media_type:
            raise ValueError(f"{expected_prefix}_sample_not_stored")
        if expected_prefix == "identity" and not (
            asset.media_type.startswith("video/") or asset.media_type.startswith("image/")
        ):
            raise ValueError("identity_sample_media_invalid")
        if expected_prefix == "voice" and not asset.media_type.startswith("audio/"):
            raise ValueError("voice_sample_media_invalid")
        key = PurePosixPath(asset.storage_key)
        if not key.parts or key.parts[0] != workspace_id:
            raise ValueError(f"{expected_prefix}_sample_storage_scope_mismatch")
    return ordered


def _bound_asset(
    db: Session,
    *,
    workspace_id: str,
    asset_id: str,
    checksum_sha256: str,
    media_prefix: str,
) -> LibraryAsset:
    asset = db.scalar(
        select(LibraryAsset).where(
            LibraryAsset.id == asset_id,
            LibraryAsset.workspace_id == workspace_id,
            LibraryAsset.lifecycle_status == "active",
        )
    )
    if (
        not asset
        or not asset.storage_key
        or not asset.storage_backend
        or not asset.checksum_sha256
        or not asset.media_type
    ):
        raise ValueError("avatar_input_asset_not_stored")
    if not asset.media_type.startswith(media_prefix):
        raise ValueError("avatar_input_asset_media_invalid")
    if asset.checksum_sha256.lower() != checksum_sha256.lower():
        raise ValueError("avatar_input_asset_checksum_mismatch")
    key = PurePosixPath(asset.storage_key)
    if not key.parts or key.parts[0] != workspace_id:
        raise ValueError("avatar_input_storage_scope_mismatch")
    return asset


def execute_avatar_video(
    db: Session,
    job: StudioGenerationJob,
    progress: Callable[[int], None],
    is_cancelled: Callable[[], bool],
) -> dict:
    if job.job_type != "avatar_video":
        raise ValueError("avatar_video_job_type_required")
    require_avatar_video_binding(
        db,
        workspace_id=job.workspace_id,
        document_id=job.document_id,
        identity_version_id=job.identity_version_id,
        voice_version_id=job.voice_version_id,
        consent_grant_id=job.consent_grant_id,
    )
    existing = _existing_result(db, job)
    if existing:
        return existing
    provider = AVATAR_VIDEO_PROVIDERS.get(job.provider)
    if provider is None:
        raise ValueError("avatar_video_provider_unavailable")
    if not all(
        [job.document_id, job.identity_version_id, job.voice_version_id, job.consent_grant_id]
    ):
        raise ValueError("avatar_video_binding_missing")
    document_record = db.get(CreativeDocument, job.document_id)
    identity_version = db.get(StudioIdentityVersion, job.identity_version_id)
    voice_version = db.get(StudioVoiceVersion, job.voice_version_id)
    if not document_record or not identity_version or not voice_version:
        raise ValueError("avatar_video_binding_missing")
    document = record_to_contract(document_record)
    schema_version = job.request_payload.get("schemaVersion") or job.request_payload.get("schema_version")
    is_v2 = schema_version == "studio.avatar-video-request.v2"
    if is_v2:
        request = AvatarVideoRequestV2.model_validate(
            {key: value for key, value in job.request_payload.items() if key != "executionBinding"}
        )
        require_avatar_v2_media_binding(
            db,
            workspace_id=job.workspace_id,
            document_id=str(job.document_id),
            identity_version_id=str(job.identity_version_id),
            voice_version_id=str(job.voice_version_id),
            payload=request.model_dump(by_alias=True, mode="json"),
        )
        expected_hybrid = _avatar_v2_hybrid_binding(
            request.model_dump(by_alias=True, mode="json"), job.provider
        )
        stored_execution = job.request_payload.get("executionBinding") or {}
        stored_hybrid = stored_execution.get("hybrid") or {}
        if stored_hybrid.get("bindingDigestSha256") != expected_hybrid.get("bindingDigestSha256"):
            raise ValueError("avatar_execution_profile_changed")
        provider_binding = require_avatar_provider_admission(
            db, provider_name=job.provider, require_runtime=True
        )
        stored_provider = stored_execution.get("provider") or {}
        if stored_provider.get("bindingDigestSha256") != provider_binding.get("bindingDigestSha256"):
            raise ValueError("avatar_provider_binding_changed")
        identity_assets = [
            _bound_asset(
                db,
                workspace_id=job.workspace_id,
                asset_id=request.reference_image_asset_id,
                checksum_sha256=request.reference_image_checksum_sha256,
                media_prefix="image/",
            )
        ]
        driving_audio_asset = _bound_asset(
            db,
            workspace_id=job.workspace_id,
            asset_id=request.driving_audio_asset_id,
            checksum_sha256=request.driving_audio_checksum_sha256,
            media_prefix="audio/",
        )
    else:
        request = AvatarVideoRequestV1.model_validate(job.request_payload)
        require_avatar_provider_admission(db, provider_name=job.provider, require_runtime=True)
        identity_assets = _version_assets(
            db,
            workspace_id=job.workspace_id,
            asset_ids=identity_version.sample_asset_ids or [],
            expected_prefix="identity",
        )
        voice_assets = _version_assets(
            db,
            workspace_id=job.workspace_id,
            asset_ids=voice_version.sample_asset_ids or [],
            expected_prefix="voice",
        )
        if len(voice_assets) != 1:
            raise ValueError("voice_sample_ambiguous")
        driving_audio_asset = voice_assets[0]
    if is_cancelled():
        return {"cancelled": True}

    storage = get_object_storage()
    stored = None
    with ExitStack() as stack:
        identity_paths: list[Path] = []
        for asset in identity_assets:
            materialized = stack.enter_context(
                get_object_storage(asset.storage_backend or "local").materialize(asset.storage_key)
            )
            if sha256_file(materialized).lower() != asset.checksum_sha256.lower():
                raise ValueError("identity_sample_checksum_mismatch")
            identity_paths.append(materialized)
        driving_audio_path = stack.enter_context(
            get_object_storage(driving_audio_asset.storage_backend or "local").materialize(
                driving_audio_asset.storage_key
            )
        )
        if sha256_file(driving_audio_path).lower() != driving_audio_asset.checksum_sha256.lower():
            raise ValueError("avatar_driving_audio_checksum_mismatch" if is_v2 else "voice_sample_checksum_mismatch")
        temporary = stack.enter_context(tempfile.TemporaryDirectory(prefix="clicko-avatar-video-"))
        output_path = Path(temporary) / "presenter.mp4"
        try:
            encoded = provider.render(
                document,
                request,
                identity_paths,
                driving_audio_path,
                output_path,
                progress,
                is_cancelled,
            )
        except InterruptedError:
            return {"cancelled": True}
        if is_cancelled():
            return {"cancelled": True}
        if not output_path.is_file() or output_path.stat().st_size <= 0:
            raise ValueError("avatar_video_output_missing")
        checksum = sha256_file(output_path)
        if (
            encoded.provider != provider.name
            or encoded.provider_version != provider.version
            or encoded.width != request.width
            or encoded.height != request.height
            or encoded.fps != request.fps
            or encoded.artifact_checksum_sha256.lower() != checksum
            or encoded.synthetic_content_disclosed is not True
        ):
            raise ValueError("avatar_video_result_binding_mismatch")
        key = object_key(job.workspace_id, "exports", ".mp4")
        stored = storage.put_file(
            output_path,
            key=key,
            media_type="video/mp4",
            metadata={
                "workspace-id": job.workspace_id,
                "role": "private-avatar-video",
                "generation-job-id": job.id,
                "provider": provider.name,
            },
        )
    if is_cancelled():
        storage.delete(stored.key)
        return {"cancelled": True}

    script_digest = hashlib.sha256(request.script.encode("utf-8")).hexdigest()
    progress(92)
    try:
        asset = LibraryAsset(
            workspace_id=job.workspace_id,
            title=f"{document.title} — amostra Presenter privada",
            asset_type="video",
            tags=["studio-presenter", "private-review", "synthetic-content"],
            campaign_id=document.campaign_ref.id if document.campaign_ref else None,
            content_id=document.post_ref.id if document.post_ref else None,
            storage_key=stored.key,
            storage_backend=stored.backend,
            media_type=stored.media_type,
            size_bytes=stored.size_bytes,
            checksum_sha256=stored.checksum_sha256,
            object_metadata={
                **stored.metadata,
                "schemaVersion": "studio.asset-lineage.v1",
                "derivation": "avatar_video",
                "generationJobId": job.id,
                "documentId": job.document_id,
                "identityVersionId": job.identity_version_id,
                "voiceVersionId": job.voice_version_id,
                "consentGrantId": job.consent_grant_id,
                "scriptDigestSha256": script_digest,
                **(
                    {
                        "avatarRequestSchemaVersion": request.schema_version,
                        "documentRevision": request.expected_document_revision,
                        "sceneId": request.scene_id,
                        "requirementId": request.requirement_id,
                        "referenceImageAssetId": request.reference_image_asset_id,
                        "referenceImageChecksumSha256": request.reference_image_checksum_sha256,
                        "drivingAudioAssetId": request.driving_audio_asset_id,
                        "drivingAudioChecksumSha256": request.driving_audio_checksum_sha256,
                        "drivingAudioOrigin": request.driving_audio_origin,
                        "profileId": request.profile_id,
                        "executionBinding": job.request_payload.get("executionBinding"),
                    }
                    if is_v2
                    else {}
                ),
                "syntheticContentDisclosed": True,
                "reviewRequired": True,
            },
        )
        db.add(asset)
        db.flush()
        if is_v2:
            execution_binding = job.request_payload["executionBinding"]["hybrid"]
            result = AvatarVideoJobResultV2(
                generation_job_id=job.id,
                asset_id=asset.id,
                storage_backend=stored.backend,
                size_bytes=stored.size_bytes,
                checksum_sha256=stored.checksum_sha256,
                document_id=job.document_id,
                document_revision=request.expected_document_revision,
                scene_id=request.scene_id,
                requirement_id=request.requirement_id,
                identity_version_id=job.identity_version_id,
                voice_version_id=job.voice_version_id,
                consent_grant_id=job.consent_grant_id,
                reference_image_asset_id=request.reference_image_asset_id,
                reference_image_checksum_sha256=request.reference_image_checksum_sha256,
                driving_audio_asset_id=request.driving_audio_asset_id,
                driving_audio_checksum_sha256=request.driving_audio_checksum_sha256,
                driving_audio_origin=request.driving_audio_origin,
                profile_id=request.profile_id,
                execution_binding_digest_sha256=execution_binding["bindingDigestSha256"],
                script_digest_sha256=script_digest,
                avatar=encoded,
            )
        else:
            result = AvatarVideoJobResultV1(
                generation_job_id=job.id,
                asset_id=asset.id,
                storage_backend=stored.backend,
                size_bytes=stored.size_bytes,
                checksum_sha256=stored.checksum_sha256,
                document_id=job.document_id,
                identity_version_id=job.identity_version_id,
                voice_version_id=job.voice_version_id,
                consent_grant_id=job.consent_grant_id,
                script_digest_sha256=script_digest,
                avatar=encoded,
            )
        payload = result.model_dump(by_alias=True, mode="json")
        asset.object_metadata = {**asset.object_metadata, "avatarVideoJobResult": payload}
        emit_event(
            db,
            workspace_id=job.workspace_id,
            event_type="studio.avatar-video.artifact-created",
            aggregate_type="library_asset",
            aggregate_id=asset.id,
            correlation_id=job.correlation_id,
            actor_id=job.requested_by,
            payload={
                "generationJobId": job.id,
                "identityVersionId": job.identity_version_id,
                "voiceVersionId": job.voice_version_id,
                "consentGrantId": job.consent_grant_id,
                "reviewRequired": True,
            },
        )
        db.commit()
        progress(99)
        return payload
    except Exception:
        db.rollback()
        storage.delete(stored.key)
        raise
