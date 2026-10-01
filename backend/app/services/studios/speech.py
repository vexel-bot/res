from __future__ import annotations

import tempfile
from collections.abc import Callable
from pathlib import Path, PurePosixPath

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...domain.studios.contracts import (
    SpeechSynthesisJobResultV1,
    SpeechSynthesisRequestV1,
    VoiceCloneReferenceV1,
)
from ...domain.studios.providers import (
    SPEECH_PROVIDERS,
    VOICE_CLONE_PROVIDERS,
    VOICE_REFERENCE_NORMALIZERS,
)
from ...models import LibraryAsset, StudioGenerationJob, StudioVoiceVersion
from ...providers.studios import voice_reference as _voice_reference  # noqa: F401
from ..object_storage import get_object_storage, object_key, sha256_file
from .jobs import require_voice_clone_binding
from .kernel import emit_event

MEDIA_TYPES = {"wav": "audio/wav", "flac": "audio/flac", "mp3": "audio/mpeg"}
VOICE_REFERENCE_NORMALIZER = "builtin.ffmpeg-voice-reference-v1"


def _existing_result(db: Session, job: StudioGenerationJob) -> dict | None:
    assets = db.scalars(
        select(LibraryAsset).where(
            LibraryAsset.workspace_id == job.workspace_id,
            LibraryAsset.asset_type == "audio",
            LibraryAsset.lifecycle_status == "active",
        )
    ).all()
    for asset in assets:
        metadata = asset.object_metadata or {}
        if metadata.get("generationJobId") != job.id or metadata.get("derivation") != "speech_synthesis":
            continue
        result = metadata.get("speechSynthesisJobResult")
        if isinstance(result, dict):
            return SpeechSynthesisJobResultV1.model_validate(result).model_dump(by_alias=True, mode="json")
    return None


def _voice_reference_asset(
    db: Session,
    job: StudioGenerationJob,
    version: StudioVoiceVersion,
) -> LibraryAsset:
    sample_ids = list(dict.fromkeys(version.sample_asset_ids or []))
    primary = (version.pronunciation_profile or {}).get("primarySampleAssetId")
    if primary is not None and (not isinstance(primary, str) or primary not in sample_ids):
        raise ValueError("voice_reference_primary_sample_invalid")
    if primary is None:
        if len(sample_ids) != 1:
            raise ValueError("voice_reference_ambiguous")
        primary = sample_ids[0]
    asset = db.scalar(
        select(LibraryAsset).where(
            LibraryAsset.id == primary,
            LibraryAsset.workspace_id == job.workspace_id,
            LibraryAsset.lifecycle_status == "active",
        )
    )
    if (
        asset is None
        or not asset.storage_key
        or not asset.checksum_sha256
        or not asset.media_type
        or not asset.media_type.startswith("audio/")
    ):
        raise ValueError("voice_reference_audio_asset_required")
    key = PurePosixPath(asset.storage_key)
    if not key.parts or key.parts[0] != job.workspace_id:
        raise ValueError("voice_reference_storage_scope_mismatch")
    return asset


def _validate_clone_result_binding(
    reference: VoiceCloneReferenceV1,
    result,
) -> None:
    provenance = result.provenance
    if (
        provenance.voice_version_id != reference.voice_version_id
        or provenance.consent_grant_id != reference.consent_grant_id
        or provenance.voice_reference_checksum_sha256 is None
        or provenance.voice_reference_checksum_sha256.lower()
        != reference.normalized_checksum_sha256.lower()
    ):
        raise ValueError("voice_clone_result_reference_mismatch")


def execute_speech_synthesis(
    db: Session,
    job: StudioGenerationJob,
    progress: Callable[[int], None],
    is_cancelled: Callable[[], bool],
) -> dict:
    if job.job_type not in {"stock_voice", "voice_clone"}:
        raise ValueError("speech_job_type_required")
    voice_version = None
    if job.job_type == "voice_clone":
        voice_version = require_voice_clone_binding(
            db,
            workspace_id=job.workspace_id,
            voice_version_id=job.voice_version_id,
            consent_grant_id=job.consent_grant_id,
        )
    existing = _existing_result(db, job)
    if existing:
        return existing
    request = SpeechSynthesisRequestV1.model_validate(job.request_payload)
    if is_cancelled():
        return {"cancelled": True}

    storage = get_object_storage()
    stored = None
    voice_reference = None
    with tempfile.TemporaryDirectory(prefix="clicko-speech-") as temporary:
        output_path = Path(temporary) / f"speech.{request.audio_format}"
        try:
            if job.job_type == "stock_voice":
                provider = SPEECH_PROVIDERS.get(job.provider)
                if provider is None:
                    raise ValueError("speech_provider_unavailable")
                result = provider.synthesize(request, output_path, progress, is_cancelled)
            else:
                if voice_version is None or job.consent_grant_id is None:
                    raise ValueError("voice_clone_binding_missing")
                if request.voice_key != voice_version.id:
                    raise ValueError("voice_clone_request_version_mismatch")
                provider = VOICE_CLONE_PROVIDERS.get(job.provider)
                if provider is None:
                    raise ValueError("voice_clone_provider_unavailable")
                normalizer = VOICE_REFERENCE_NORMALIZERS.get(VOICE_REFERENCE_NORMALIZER)
                if normalizer is None:
                    raise ValueError("voice_reference_normalizer_unavailable")
                source_asset = _voice_reference_asset(db, job, voice_version)
                source_storage = get_object_storage(source_asset.storage_backend)
                normalized_reference = Path(temporary) / "voice-reference.wav"
                with source_storage.materialize(source_asset.storage_key) as source_path:
                    if sha256_file(source_path).lower() != source_asset.checksum_sha256.lower():
                        raise ValueError("voice_reference_source_checksum_mismatch")
                    voice_reference = normalizer.normalize(
                        source_path,
                        normalized_reference,
                        voice_version_id=voice_version.id,
                        consent_grant_id=job.consent_grant_id,
                        source_asset_id=source_asset.id,
                        source_checksum_sha256=source_asset.checksum_sha256,
                        progress=progress,
                        is_cancelled=is_cancelled,
                    )
                if (
                    not normalized_reference.is_file()
                    or sha256_file(normalized_reference).lower()
                    != voice_reference.normalized_checksum_sha256.lower()
                ):
                    raise ValueError("voice_reference_normalized_checksum_mismatch")
                result = provider.clone(
                    request,
                    voice_reference,
                    normalized_reference,
                    output_path,
                    progress,
                    is_cancelled,
                )
                _validate_clone_result_binding(voice_reference, result)
        except InterruptedError:
            return {"cancelled": True}
        if is_cancelled():
            return {"cancelled": True}
        if not output_path.is_file() or output_path.stat().st_size <= 0:
            raise ValueError("speech_output_missing")
        checksum = sha256_file(output_path)
        if (
            result.provider != provider.name
            or result.provider_version != provider.version
            or result.audio_format != request.audio_format
            or result.sample_rate != request.sample_rate
            or result.artifact_checksum_sha256.lower() != checksum
        ):
            raise ValueError("speech_result_binding_mismatch")
        key = object_key(job.workspace_id, "voice", f".{request.audio_format}")
        stored = storage.put_file(
            output_path,
            key=key,
            media_type=MEDIA_TYPES[request.audio_format],
            metadata={
                "workspace-id": job.workspace_id,
                "role": "speech-synthesis",
                "generation-job-id": job.id,
                "provider": result.provider,
                "script-sha256": request.script_digest_sha256,
            },
        )
    if is_cancelled():
        storage.delete(stored.key)
        return {"cancelled": True}
    progress(90)
    try:
        asset = LibraryAsset(
            workspace_id=job.workspace_id,
            title=f"Voz gerada — {job.id[:8]}",
            asset_type="audio",
            tags=["studio-speech", job.job_type],
            storage_key=stored.key,
            storage_backend=stored.backend,
            media_type=stored.media_type,
            size_bytes=stored.size_bytes,
            checksum_sha256=stored.checksum_sha256,
            object_metadata={
                **stored.metadata,
                "schemaVersion": "studio.asset-lineage.v1",
                "derivation": "speech_synthesis",
                "generationJobId": job.id,
                "jobType": job.job_type,
                "providerVersion": result.provider_version,
                "scriptDigestSha256": request.script_digest_sha256,
                "voiceVersionId": job.voice_version_id,
                "consentGrantId": job.consent_grant_id,
                "speechProvenance": result.provenance.model_dump(by_alias=True, mode="json"),
            },
        )
        db.add(asset)
        db.flush()
        job_result = SpeechSynthesisJobResultV1(
            generation_job_id=job.id,
            job_type=job.job_type,
            asset_id=asset.id,
            storage_backend=stored.backend,
            media_type=stored.media_type,
            size_bytes=stored.size_bytes,
            checksum_sha256=stored.checksum_sha256,
            script_digest_sha256=request.script_digest_sha256,
            voice_reference=voice_reference,
            speech=result,
        )
        asset.object_metadata = {
            **asset.object_metadata,
            "speechSynthesisJobResult": job_result.model_dump(by_alias=True, mode="json"),
        }
        emit_event(
            db,
            workspace_id=job.workspace_id,
            event_type="studio.speech.ready",
            aggregate_type="generation_job",
            aggregate_id=job.id,
            correlation_id=job.correlation_id,
            actor_id=None,
            payload={
                "assetId": asset.id,
                "checksumSha256": stored.checksum_sha256,
                "provider": result.provider,
                "providerVersion": result.provider_version,
            },
        )
        db.commit()
        return job_result.model_dump(by_alias=True, mode="json")
    except Exception:
        db.rollback()
        if stored is not None:
            storage.delete(stored.key)
        raise
