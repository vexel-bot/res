from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...config import get_settings
from ...domain.studios.acoustic_qualification import (
    AcousticPromotionReceiptV1,
    acoustic_registration_promotion_digest,
)
from ...domain.studios.contracts import (
    AvatarVideoRequestV1,
    AvatarVideoRequestV2,
    CreateGenerationJobRequest,
    GenerationJobV1,
    TranscriptionRequestV1,
)
from ...domain.studios.execution import execution_profile
from ...domain.studios.hybrid_video import (
    HybridProductionPolicyV1,
    HybridSelectionRequestV1,
    select_hybrid_profile,
)
from ...domain.studios.providers import (
    ACOUSTIC_ANALYSIS_PROVIDERS,
    AVATAR_VIDEO_PROVIDERS,
    PROVIDERS,
)
from ...models import (
    CreativeDocument,
    LibraryAsset,
    StudioConsentGrant,
    StudioGenerationJob,
    StudioIdentityProfile,
    StudioIdentityVersion,
    StudioMediaIngest,
    StudioModelRegistration,
    StudioProviderRegistration,
    StudioVoiceProfile,
    StudioVoiceVersion,
    User,
)
from .compatibility import record_to_contract
from .identity import consent_status, require_active_version_consent
from .kernel import emit_event
from .worker_runtime import worker_execution_context

TERMINAL_STATES = {"cancelled", "succeeded", "failed"}
ALLOWED_TRANSITIONS = {
    "queued": {"running", "cancelled"},
    "running": {"retrying", "cancel_requested", "succeeded", "failed"},
    "retrying": {"running", "cancel_requested", "failed"},
    "cancel_requested": {"cancelled"},
    "cancelled": {"queued"},
    "failed": {"queued"},
    "succeeded": set(),
}


def payload_hash(request: CreateGenerationJobRequest) -> str:
    raw = json.dumps(request.model_dump(by_alias=True, mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def require_speech_provider_admission(
    db: Session,
    *,
    job_type: str,
    provider_name: str,
) -> None:
    if job_type not in {"stock_voice", "voice_clone"}:
        return
    registration = db.scalar(
        select(StudioProviderRegistration).where(
            StudioProviderRegistration.provider == provider_name,
            StudioProviderRegistration.capability == job_type,
            StudioProviderRegistration.status == "approved",
        )
    )
    if registration is None:
        raise ValueError("speech_provider_not_approved")
    manifest = registration.manifest or {}
    if manifest.get("benchmarkStatus") != "passed":
        raise ValueError("speech_provider_benchmark_pending")
    if manifest.get("workerAdvertised") is not True:
        raise ValueError("speech_provider_not_advertised")
    model = db.scalar(
        select(StudioModelRegistration).where(
            StudioModelRegistration.provider_registration_id == registration.id,
            StudioModelRegistration.status == "approved",
        )
    )
    if (
        model is None
        or model.commercial_use != "approved"
        or job_type not in (model.capabilities or [])
        or (model.manifest or {}).get("benchmarkStatus") != "passed"
    ):
        raise ValueError("speech_model_not_approved")


def require_transcription_provider_admission(
    db: Session,
    *,
    provider_name: str,
) -> None:
    """Require an explicitly benchmarked, advertised ASR registration."""
    registration = db.scalar(
        select(StudioProviderRegistration).where(
            StudioProviderRegistration.provider == provider_name,
            StudioProviderRegistration.capability == "transcription",
            StudioProviderRegistration.status == "approved",
        )
    )
    if registration is None:
        raise ValueError("transcription_provider_not_approved")
    manifest = registration.manifest or {}
    if manifest.get("benchmarkStatus") != "passed":
        raise ValueError("transcription_provider_benchmark_pending")
    if manifest.get("workerAdvertised") is not True:
        raise ValueError("transcription_provider_not_advertised")
    model = db.scalar(
        select(StudioModelRegistration).where(
            StudioModelRegistration.provider_registration_id == registration.id,
            StudioModelRegistration.status == "approved",
        )
    )
    if (
        model is None
        or model.commercial_use != "approved"
        or "transcription" not in (model.capabilities or [])
        or (model.manifest or {}).get("benchmarkStatus") != "passed"
    ):
        raise ValueError("transcription_model_not_approved")


def require_acoustic_provider_admission(
    db: Session,
    *,
    provider_name: str,
) -> None:
    """Keep generic job callers behind the same promoted detector boundary."""
    registration = db.scalar(
        select(StudioProviderRegistration).where(
            StudioProviderRegistration.provider == provider_name,
            StudioProviderRegistration.capability == "acoustic_analysis",
            StudioProviderRegistration.status == "approved",
        )
    )
    if registration is None:
        raise ValueError("acoustic_detector_not_approved")
    model = db.scalar(
        select(StudioModelRegistration).where(
            StudioModelRegistration.provider_registration_id == registration.id,
            StudioModelRegistration.status == "approved",
        )
    )
    if model is None or model.commercial_use != "approved" or "acoustic_analysis" not in (model.capabilities or []):
        raise ValueError("acoustic_model_not_approved")
    settings = get_settings()
    if not settings.studio_acoustic_promotion_hmac_secret or not settings.studio_acoustic_promotion_key_id:
        raise ValueError("acoustic_promotion_verifier_unconfigured")
    try:
        receipt = AcousticPromotionReceiptV1.model_validate(
            (registration.manifest or {}).get("acousticPromotionReceipt")
        )
    except ValueError as error:
        raise ValueError("acoustic_detector_benchmark_pending") from error
    acoustic_registration_promotion_digest(
        receipt,
        secret=settings.studio_acoustic_promotion_hmac_secret,
        signer_key_id=settings.studio_acoustic_promotion_key_id,
        provider=registration.provider,
        provider_version=registration.provider_version,
        model_name=model.name,
        model_version=model.version,
        model_digest_sha256=model.digest_sha256,
        model_receipt_digest_sha256=str((model.manifest or {}).get("acousticPromotionReceiptDigestSha256") or ""),
    )
    provider = ACOUSTIC_ANALYSIS_PROVIDERS.get(provider_name)
    if provider is None or provider.version != registration.provider_version:
        raise ValueError("acoustic_detector_runtime_unavailable")


def require_avatar_provider_admission(
    db: Session,
    *,
    provider_name: str,
    require_runtime: bool = False,
) -> dict:
    """Admit only an explicitly benchmarked avatar worker and model pair.

    Provider readiness shown by the UI is informative. This server-side gate is
    authoritative and is deliberately separate from the generic provider map.
    """
    registration = db.scalar(
        select(StudioProviderRegistration).where(
            StudioProviderRegistration.provider == provider_name,
            StudioProviderRegistration.capability == "avatar_video",
            StudioProviderRegistration.status == "approved",
        )
    )
    if registration is None:
        raise ValueError("avatar_provider_not_approved")
    manifest = registration.manifest or {}
    if manifest.get("benchmarkStatus") != "passed":
        raise ValueError("avatar_provider_benchmark_pending")
    if manifest.get("workerAdvertised") is not True:
        raise ValueError("avatar_provider_not_advertised")
    model = db.scalar(
        select(StudioModelRegistration).where(
            StudioModelRegistration.provider_registration_id == registration.id,
            StudioModelRegistration.status == "approved",
        )
    )
    if (
        model is None
        or model.commercial_use != "approved"
        or "avatar_video" not in (model.capabilities or [])
        or (model.manifest or {}).get("benchmarkStatus") != "passed"
    ):
        raise ValueError("avatar_model_not_approved")
    provider = AVATAR_VIDEO_PROVIDERS.get(provider_name)
    if provider is None and provider_name == "local.longcat-avatar-1.5":
        from ...providers.studios.longcat_avatar import configured_longcat_avatar_provider

        provider = configured_longcat_avatar_provider()
        if provider is not None:
            AVATAR_VIDEO_PROVIDERS[provider.name] = provider
    if require_runtime and (provider is None or provider.version != registration.provider_version):
        raise ValueError("avatar_provider_runtime_unavailable")
    binding = {
        "schemaVersion": "studio.avatar-provider-binding.v1",
        "provider": registration.provider,
        "providerVersion": registration.provider_version,
        "sourceRevision": registration.source_revision,
        "modelName": model.name,
        "modelVersion": model.version,
        "modelDigestSha256": model.digest_sha256,
        "runtimeName": provider.name if provider else None,
        "runtimeVersion": provider.version if provider else None,
    }
    binding["bindingDigestSha256"] = hashlib.sha256(
        json.dumps(binding, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return binding


def _avatar_v2_hybrid_binding(payload: dict, provider_name: str) -> dict:
    """Resolve one immutable profile using the common hybrid selector."""
    from .hybrid_video import hybrid_capability_manifest

    request = AvatarVideoRequestV2.model_validate(payload)
    manifest = hybrid_capability_manifest()
    selection = select_hybrid_profile(
        manifest,
        HybridProductionPolicyV1(
            mode="auto",
            allowed_profile_ids=[request.profile_id],
            allow_experimental=True,
            allow_conditional_commercial_use=True,
        ),
        HybridSelectionRequestV1(
            capability="avatar_video",
            operation=request.operation,
            required_inputs=[
                "authorized_reference_image",
                "final_speech_audio",
                "identity_consent",
            ],
            duration_seconds=request.driving_audio_duration_ms / 1000,
            use_case="single_presenter_pt_br",
            requested_parameters=request.effective_parameters,
        ),
    )
    if not selection.execution_binding:
        reason = selection.blockers[0] if selection.blockers else "no_matching_profile"
        raise ValueError(f"avatar_profile_unavailable:{reason}")
    binding = selection.execution_binding.model_dump(by_alias=True, mode="json")
    if binding["providerId"] != provider_name:
        raise ValueError("avatar_provider_profile_mismatch")
    return binding


def require_avatar_video_binding(
    db: Session,
    *,
    workspace_id: str,
    document_id: str | None,
    identity_version_id: str | None,
    voice_version_id: str | None,
    consent_grant_id: str | None,
) -> None:
    """Bind one presenter job to content, active versions and live rights.

    This repeats the HTTP validation for direct task/CLI callers. No provider
    can turn a draft or revoked biometric capsule into a queued job.
    """
    if not document_id:
        raise ValueError("document_required")
    document = db.scalar(
        select(CreativeDocument).where(
            CreativeDocument.id == document_id,
            CreativeDocument.workspace_id == workspace_id,
        )
    )
    if document is None:
        raise ValueError("document_not_found")
    if not identity_version_id:
        raise ValueError("identity_version_required")
    if not voice_version_id:
        raise ValueError("voice_version_required")
    if not consent_grant_id:
        raise ValueError("consent_required")

    identity_version = db.scalar(
        select(StudioIdentityVersion).where(
            StudioIdentityVersion.id == identity_version_id,
            StudioIdentityVersion.workspace_id == workspace_id,
        )
    )
    voice_version = db.scalar(
        select(StudioVoiceVersion).where(
            StudioVoiceVersion.id == voice_version_id,
            StudioVoiceVersion.workspace_id == workspace_id,
        )
    )
    if identity_version is None:
        raise ValueError("identity_version_not_active")
    if voice_version is None:
        raise ValueError("voice_version_not_active")
    require_active_version_consent(db, identity_version, consent_grant_id=consent_grant_id)
    require_active_version_consent(db, voice_version, consent_grant_id=consent_grant_id)
    if "avatar.generate" not in set(identity_version.capabilities or []):
        raise ValueError("identity_capability_missing")

    identity = db.get(StudioIdentityProfile, identity_version.profile_id)
    voice = db.get(StudioVoiceProfile, voice_version.profile_id)
    if not identity or identity.workspace_id != workspace_id:
        raise ValueError("identity_version_not_active")
    if not voice or voice.workspace_id != workspace_id:
        raise ValueError("voice_version_not_active")
    if voice.identity_profile_id != identity.id:
        raise ValueError("voice_identity_version_mismatch")

    grant = db.get(StudioConsentGrant, consent_grant_id)
    if not grant or grant.workspace_id != workspace_id or consent_status(grant) != "active":
        raise ValueError("consent_not_active")
    if grant.subject_key != identity.subject_key:
        raise ValueError("consent_subject_mismatch")
    scopes = set(grant.scopes or [])
    if "avatar.generate" not in scopes:
        raise ValueError("consent_scope_missing")
    if voice.voice_type == "cloned" and "voice.clone" not in scopes:
        raise ValueError("consent_scope_missing")


def require_avatar_v2_media_binding(
    db: Session,
    *,
    workspace_id: str,
    document_id: str,
    identity_version_id: str,
    voice_version_id: str,
    payload: dict,
) -> AvatarVideoRequestV2:
    request = AvatarVideoRequestV2.model_validate(payload)
    document = db.scalar(
        select(CreativeDocument).where(
            CreativeDocument.id == document_id,
            CreativeDocument.workspace_id == workspace_id,
        )
    )
    if not document or document.revision != request.expected_document_revision:
        raise ValueError("studio_document_conflict")
    identity_version = db.get(StudioIdentityVersion, identity_version_id)
    voice_version = db.get(StudioVoiceVersion, voice_version_id)
    if not identity_version or not voice_version:
        raise ValueError("avatar_video_binding_missing")
    if request.reference_image_asset_id not in set(identity_version.sample_asset_ids or []):
        raise ValueError("avatar_reference_image_not_authorized")
    if request.driving_audio_asset_id in set(voice_version.sample_asset_ids or []):
        raise ValueError("voice_sample_cannot_be_driving_audio")
    assets = db.scalars(
        select(LibraryAsset).where(
            LibraryAsset.workspace_id == workspace_id,
            LibraryAsset.id.in_(
                [request.reference_image_asset_id, request.driving_audio_asset_id]
            ),
            LibraryAsset.lifecycle_status == "active",
        )
    ).all()
    by_id = {asset.id: asset for asset in assets}
    image = by_id.get(request.reference_image_asset_id)
    audio = by_id.get(request.driving_audio_asset_id)
    if not image or not audio:
        raise ValueError("avatar_input_asset_not_found")
    if not image.media_type or not image.media_type.startswith("image/"):
        raise ValueError("avatar_reference_image_media_invalid")
    if not audio.media_type or not audio.media_type.startswith("audio/"):
        raise ValueError("avatar_driving_audio_media_invalid")
    if (
        not image.storage_key
        or not audio.storage_key
        or not image.checksum_sha256
        or not audio.checksum_sha256
    ):
        raise ValueError("avatar_input_asset_not_stored")
    if image.checksum_sha256.lower() != request.reference_image_checksum_sha256.lower():
        raise ValueError("avatar_reference_image_checksum_mismatch")
    if audio.checksum_sha256.lower() != request.driving_audio_checksum_sha256.lower():
        raise ValueError("avatar_driving_audio_checksum_mismatch")
    speech_result = (audio.object_metadata or {}).get("speechSynthesisJobResult")
    if request.driving_audio_origin in {
        "stock_voice_synthesis",
        "cloned_voice_synthesis",
    }:
        if not isinstance(speech_result, dict):
            raise ValueError("avatar_driving_audio_provenance_missing")
        expected_job_type = (
            "voice_clone"
            if request.driving_audio_origin == "cloned_voice_synthesis"
            else "stock_voice"
        )
        if speech_result.get("jobType") != expected_job_type:
            raise ValueError("avatar_driving_audio_origin_mismatch")
        if speech_result.get("scriptDigestSha256") != hashlib.sha256(
            request.script.encode()
        ).hexdigest():
            raise ValueError("avatar_driving_audio_script_mismatch")
        produced_duration = (speech_result.get("speech") or {}).get("durationMs")
        if produced_duration != request.driving_audio_duration_ms:
            raise ValueError("avatar_driving_audio_duration_mismatch")
        if (
            expected_job_type == "voice_clone"
            and (audio.object_metadata or {}).get("voiceVersionId") != voice_version_id
        ):
            raise ValueError("avatar_driving_audio_voice_mismatch")
    elif isinstance(speech_result, dict):
        raise ValueError("avatar_driving_audio_origin_mismatch")
    for asset in (image, audio):
        key = asset.storage_key.split("/", 1)
        if not key or key[0] != workspace_id:
            raise ValueError("avatar_input_storage_scope_mismatch")
    return request


def require_transcription_input_binding(
    db: Session,
    *,
    workspace_id: str,
    payload: dict,
) -> None:
    """Bind an ASR request to one ready ingest and its immutable source digest."""
    request = TranscriptionRequestV1.model_validate(payload)
    ingest = db.scalar(
        select(StudioMediaIngest).where(
            StudioMediaIngest.id == request.media_ingest_id,
            StudioMediaIngest.workspace_id == workspace_id,
        )
    )
    if not ingest or ingest.status != "ready":
        raise ValueError("media_ingest_not_ready")
    if ingest.asset_id != request.source_asset_id:
        raise ValueError("transcription_source_asset_mismatch")
    asset = db.scalar(
        select(LibraryAsset).where(
            LibraryAsset.id == request.source_asset_id,
            LibraryAsset.workspace_id == workspace_id,
            LibraryAsset.lifecycle_status == "active",
        )
    )
    if not asset or not asset.storage_key or not asset.checksum_sha256:
        raise ValueError("stored_media_asset_required")
    if asset.checksum_sha256.lower() != request.source_checksum_sha256.lower():
        raise ValueError("transcription_source_checksum_mismatch")


def require_voice_clone_binding(
    db: Session,
    *,
    workspace_id: str,
    voice_version_id: str | None,
    consent_grant_id: str | None,
) -> StudioVoiceVersion:
    """Keep cloned-voice jobs identity-bound even when created off the HTTP router.

    The API performs the same checks to return precise HTTP errors. This second
    boundary protects direct task/CLI callers and jobs created by older code.
    """
    if not voice_version_id:
        raise ValueError("voice_version_required")
    if not consent_grant_id:
        raise ValueError("consent_required")
    version = db.scalar(
        select(StudioVoiceVersion).where(
            StudioVoiceVersion.id == voice_version_id,
            StudioVoiceVersion.workspace_id == workspace_id,
        )
    )
    if not version:
        raise ValueError("voice_version_not_active")
    profile = db.get(StudioVoiceProfile, version.profile_id)
    if not profile or profile.workspace_id != workspace_id or profile.voice_type != "cloned":
        raise ValueError("voice_clone_profile_required")
    if not profile.identity_profile_id:
        raise ValueError("voice_clone_identity_required")
    identity = db.get(StudioIdentityProfile, profile.identity_profile_id)
    if not identity or identity.workspace_id != workspace_id:
        raise ValueError("voice_clone_identity_required")
    if not version.consent_grant_id:
        raise ValueError("voice_clone_consent_required")
    require_active_version_consent(db, version, consent_grant_id=consent_grant_id)
    grant = db.get(StudioConsentGrant, consent_grant_id)
    if not grant or grant.workspace_id != workspace_id or consent_status(grant) != "active":
        raise ValueError("consent_not_active")
    if grant.subject_key != identity.subject_key:
        raise ValueError("consent_subject_mismatch")
    if "voice.clone" not in set(grant.scopes):
        raise ValueError("consent_scope_missing")
    return version


def transition(job: StudioGenerationJob, target: str) -> None:
    if target not in ALLOWED_TRANSITIONS.get(job.status, set()):
        raise ValueError(f"invalid_job_transition:{job.status}:{target}")
    job.status = target
    if target == "running" and not job.started_at:
        job.started_at = datetime.now(UTC)
    if target in TERMINAL_STATES:
        job.finished_at = datetime.now(UTC)
        if target == "succeeded":
            job.progress = 100


def job_out(job: StudioGenerationJob) -> GenerationJobV1:
    return GenerationJobV1(
        id=job.id,
        workspace_id=job.workspace_id,
        requested_by=job.requested_by,
        document_id=job.document_id,
        consent_grant_id=job.consent_grant_id,
        identity_version_id=job.identity_version_id,
        voice_version_id=job.voice_version_id,
        job_type=job.job_type,
        provider=job.provider,
        execution_capability=job.execution_capability,
        queue_name=job.queue_name,
        resource_class=job.resource_class,
        hard_time_limit_seconds=job.hard_time_limit_seconds,
        idempotency_key=job.idempotency_key,
        payload_hash=job.payload_hash,
        correlation_id=job.correlation_id,
        status=job.status,
        progress=job.progress,
        attempts=job.attempts,
        max_attempts=job.max_attempts,
        request=job.request_payload,
        result=job.result_payload,
        error_code=job.error_code,
        error_message=job.error_message,
        cancel_reason=job.cancel_reason,
        worker_execution_context=job.worker_execution_context,
        created_at=job.created_at,
        updated_at=job.updated_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
    )


def create_job(
    db: Session, request: CreateGenerationJobRequest, idempotency_key: str, user: User
) -> tuple[StudioGenerationJob, bool]:
    digest = payload_hash(request)
    existing = db.scalar(
        select(StudioGenerationJob).where(
            StudioGenerationJob.workspace_id == request.workspace_id,
            StudioGenerationJob.job_type == request.job_type,
            StudioGenerationJob.idempotency_key == idempotency_key,
        )
    )
    if existing:
        if existing.payload_hash != digest:
            raise ValueError("idempotency_payload_conflict")
        return existing, False
    if request.job_type == "editing_gemini":
        from ...domain.studios.editing_resources import GeminiEditingRequestV1
        from .gemini_editing import provider_key

        settings = get_settings()
        provider_key(settings)
        parsed = GeminiEditingRequestV1.model_validate(request.request.get("input", {}))
        record = db.get(CreativeDocument, request.document_id)
        if (
            not record
            or record.workspace_id != request.workspace_id
            or record.revision != parsed.expected_document_revision
        ):
            raise ValueError("studio_document_conflict")
        expected_model = (
            settings.studio_gemini_planning_model
            if parsed.operation == "plan"
            else (
                settings.studio_gemini_video_model
                if "video" in parsed.operation
                else settings.studio_gemini_image_model
            )
        )
        if request.request.get("model") != expected_model or request.request.get("environment") != settings.environment:
            raise ValueError("editing_gemini_model_environment_mismatch")
    if request.job_type == "editing_ai":
        from ...domain.studios.editing_resources import EditingAIRequestV1
        from ...providers.studios.editing_ai import compatible_binding

        settings = get_settings()
        parsed = EditingAIRequestV1.model_validate(request.request.get("input", {}))
        if request.provider == "local.smolvlm-material-inspection":
            from .local_material_inspection import binding

            _python, _worker, model = binding(settings)
            fingerprint = "loopback-isolated-process"
            if parsed.operation != "plan" or parsed.material_inspection is None:
                raise ValueError("local_vlm_material_inspection_only")
        elif request.provider == "openai.sora-2":
            settings = get_settings()
            model, fingerprint = "sora-2", None
            if parsed.operation != "generate_video" or parsed.duration_seconds != 4:
                raise ValueError("sora_request_limits_exceeded")
            if request.request.get("outputRatio") not in {"1280x720", "720x1280"}:
                raise ValueError("sora_output_ratio_unsupported")
            if not settings.openai_outbound_enabled or not settings.openai_video_generation_enabled:
                raise ValueError("openai_video_generation_disabled")
            if not settings.openai_api_key:
                raise ValueError("openai_api_key_missing")
        elif request.provider == "runway.editing-video":
            from ...providers.studios.runway_editing import runway_binding

            model, _ = runway_binding(settings, parsed.operation)
            fingerprint = None
            if not 2 <= parsed.duration_seconds <= 10:
                raise ValueError("runway_request_limits_exceeded")
            if request.request.get("outputRatio") not in {"1280:720", "720:1280"}:
                raise ValueError("runway_output_ratio_unsupported")
        else:
            _, model, _, fingerprint = compatible_binding(settings)
            if parsed.operation != "plan":
                raise ValueError("editing_ai_operation_unsupported")
        record = db.get(CreativeDocument, request.document_id)
        if (
            not record
            or record.workspace_id != request.workspace_id
            or record.revision != parsed.expected_document_revision
        ):
            raise ValueError("studio_document_conflict")
        if (
            request.request.get("model") != model
            or (request.provider != "openai.sora-2" and request.request.get("endpointFingerprint") != fingerprint)
            or request.request.get("environment") != settings.environment
        ):
            raise ValueError("editing_ai_provider_binding_conflict")
    if request.job_type == "voice_clone":
        require_voice_clone_binding(
            db,
            workspace_id=request.workspace_id,
            voice_version_id=request.voice_version_id,
            consent_grant_id=request.consent_grant_id,
        )
    if request.job_type == "avatar_video":
        require_avatar_video_binding(
            db,
            workspace_id=request.workspace_id,
            document_id=request.document_id,
            identity_version_id=request.identity_version_id,
            voice_version_id=request.voice_version_id,
            consent_grant_id=request.consent_grant_id,
        )
        schema_version = request.request.get("schemaVersion") or request.request.get("schema_version")
        if schema_version == "studio.avatar-video-request.v2":
            require_avatar_v2_media_binding(
                db,
                workspace_id=request.workspace_id,
                document_id=str(request.document_id),
                identity_version_id=str(request.identity_version_id),
                voice_version_id=str(request.voice_version_id),
                payload=request.request,
            )
            hybrid_binding = _avatar_v2_hybrid_binding(request.request, request.provider)
            provider_binding = require_avatar_provider_admission(
                db, provider_name=request.provider, require_runtime=True
            )
            request.request = {
                **request.request,
                "executionBinding": {
                    "schemaVersion": "studio.avatar-execution-binding.v1",
                    "hybrid": hybrid_binding,
                    "provider": provider_binding,
                },
            }
        else:
            AvatarVideoRequestV1.model_validate(request.request)
            require_avatar_provider_admission(db, provider_name=request.provider)
    if request.job_type == "transcription":
        require_transcription_provider_admission(db, provider_name=request.provider)
        require_transcription_input_binding(
            db,
            workspace_id=request.workspace_id,
            payload=request.request,
        )
    if request.job_type == "acoustic_analysis":
        require_acoustic_provider_admission(db, provider_name=request.provider)
    require_speech_provider_admission(
        db,
        job_type=request.job_type,
        provider_name=request.provider,
    )
    profile = execution_profile(request.job_type)
    job = StudioGenerationJob(
        workspace_id=request.workspace_id,
        requested_by=user.id,
        document_id=request.document_id,
        consent_grant_id=request.consent_grant_id,
        identity_version_id=request.identity_version_id,
        voice_version_id=request.voice_version_id,
        job_type=request.job_type,
        provider=request.provider,
        execution_capability=profile.capability,
        queue_name=profile.queue,
        resource_class=profile.resource_class,
        hard_time_limit_seconds=profile.hard_time_limit_seconds,
        idempotency_key=idempotency_key,
        payload_hash=digest,
        correlation_id=request.correlation_id or idempotency_key,
        status="queued",
        request_payload=request.request,
    )
    db.add(job)
    db.flush()
    emit_event(
        db,
        workspace_id=job.workspace_id,
        event_type="studio.job.queued",
        aggregate_type="generation_job",
        aggregate_id=job.id,
        correlation_id=job.correlation_id,
        actor_id=user.id,
        payload={
            "jobType": job.job_type,
            "provider": job.provider,
            "executionCapability": job.execution_capability,
            "queue": job.queue_name,
            "resourceClass": job.resource_class,
        },
    )
    db.commit()
    db.refresh(job)
    return job, True


def enqueue_job_task(task, job: StudioGenerationJob, *, isolated_queues_enabled: bool) -> None:
    if not isolated_queues_enabled:
        task.delay(job.id)
        return
    task.apply_async(
        args=[job.id],
        task_id=job.id,
        queue=job.queue_name,
        soft_time_limit=max(60, job.hard_time_limit_seconds - 60),
        time_limit=job.hard_time_limit_seconds,
        headers={
            "workspace_id": job.workspace_id,
            "correlation_id": job.correlation_id,
            "execution_capability": job.execution_capability,
            "queue_name": job.queue_name,
        },
    )


def request_cancel(db: Session, job: StudioGenerationJob, reason: str, actor_id: str) -> StudioGenerationJob:
    if job.status == "queued":
        transition(job, "cancelled")
    elif job.status in {"running", "retrying"}:
        transition(job, "cancel_requested")
    elif job.status not in TERMINAL_STATES:
        raise ValueError("job_cannot_be_cancelled")
    job.cancel_reason = reason
    emit_event(
        db,
        workspace_id=job.workspace_id,
        event_type="studio.job.cancelled" if job.status == "cancelled" else "studio.job.cancel_requested",
        aggregate_type="generation_job",
        aggregate_id=job.id,
        correlation_id=job.correlation_id,
        actor_id=actor_id,
        payload={"reason": reason},
    )
    db.commit()
    db.refresh(job)
    return job


def retry_job(db: Session, job: StudioGenerationJob, actor_id: str) -> StudioGenerationJob:
    transition(job, "queued")
    job.progress = 0
    if job.job_type not in {"editing_gemini", "editing_ai"}:
        job.result_payload = None
    job.error_code = None
    job.error_message = None
    job.worker_execution_context = None
    job.cancel_reason = None
    job.started_at = None
    job.finished_at = None
    emit_event(
        db,
        workspace_id=job.workspace_id,
        event_type="studio.job.queued",
        aggregate_type="generation_job",
        aggregate_id=job.id,
        correlation_id=job.correlation_id,
        actor_id=actor_id,
        payload={"retry": True},
    )
    db.commit()
    db.refresh(job)
    return job


def execute_job_once(db: Session, job: StudioGenerationJob) -> str:
    if job.status in TERMINAL_STATES:
        return job.status
    if job.status == "cancel_requested":
        transition(job, "cancelled")
        db.commit()
        return job.status
    transition(job, "running")
    job.attempts += 1
    job.error_code = None
    job.error_message = None
    db.commit()
    provider = None
    document = None
    speech_job = job.job_type in {"stock_voice", "voice_clone"}
    transcription_job = job.job_type == "transcription"
    acoustic_job = job.job_type == "acoustic_analysis"
    if (
        not speech_job
        and not transcription_job
        and not acoustic_job
        and job.job_type
        not in {
            "editing_gemini",
            "editing_ai",
            "media_probe",
            "video_proxy",
            "media_waveform",
            "video_render",
            "avatar_video",
            "scene_generation",
        }
    ):
        provider = PROVIDERS.get(job.provider)
        if not provider:
            transition(job, "failed")
            job.error_code = "provider_unavailable"
            job.error_message = f"Provider {job.provider} is not registered"
            db.commit()
            return job.status
        record = db.get(CreativeDocument, job.document_id) if job.document_id else None
        document = record_to_contract(record) if record else None

    def progress(value: int) -> None:
        db.refresh(job)
        if job.status == "cancel_requested":
            return
        job.progress = max(job.progress, min(99, value))
        db.commit()

    def is_cancelled() -> bool:
        db.refresh(job)
        return job.status == "cancel_requested"

    try:
        job.worker_execution_context = worker_execution_context(
            job_type=job.job_type,
            capability=job.execution_capability,
            queue_name=job.queue_name,
        ).model_dump(by_alias=True, mode="json")
        db.commit()
        if job.provider == "local.smolvlm-material-inspection":
            from .local_material_inspection import execute_local_material_inspection

            result = execute_local_material_inspection(db, job, progress, is_cancelled)
        elif job.provider == "openai.sora-2":
            from .sora_editing import execute_sora_editing

            result = execute_sora_editing(db, job, progress, is_cancelled)
        elif job.job_type in {"editing_gemini", "editing_ai"}:
            from .gemini_editing import execute_editing_gemini

            result = execute_editing_gemini(db, job, progress, is_cancelled)
        elif job.job_type == "media_probe":
            from .media_ingest import execute_media_probe

            result = execute_media_probe(db, job, progress, is_cancelled)
        elif job.job_type == "video_proxy":
            from .media_proxy import execute_media_proxy

            result = execute_media_proxy(db, job, progress, is_cancelled)
        elif job.job_type == "media_waveform":
            from .media_waveform import execute_media_waveform

            result = execute_media_waveform(db, job, progress, is_cancelled)
        elif job.job_type == "video_render":
            from .video_render import execute_video_render

            result = execute_video_render(db, job, progress, is_cancelled)
        elif job.job_type == "avatar_video":
            from .avatar_video import execute_avatar_video

            result = execute_avatar_video(db, job, progress, is_cancelled)
        elif job.job_type == "scene_generation":
            from .scene_generation import execute_scene_generation

            result = execute_scene_generation(db, job, progress, is_cancelled)
        elif speech_job:
            from .speech import execute_speech_synthesis

            result = execute_speech_synthesis(db, job, progress, is_cancelled)
        elif transcription_job:
            from .transcription import execute_transcription

            result = execute_transcription(db, job, progress, is_cancelled)
        elif acoustic_job:
            from .acoustic_analysis import execute_acoustic_analysis

            result = execute_acoustic_analysis(db, job, progress, is_cancelled)
        else:
            if provider is None:
                raise ValueError("provider_unavailable")
            result = provider.execute(document, job.request_payload, progress, is_cancelled)
        db.refresh(job)
        if job.status == "cancel_requested" or result.get("cancelled"):
            transition(job, "cancelled")
            job.result_payload = (
                result if job.job_type in {"editing_gemini", "editing_ai", "scene_generation"} else None
            )
        elif job.job_type == "scene_generation" and result.get("status") != "candidate_generated":
            outcome = str(result.get("status") or "failed")
            retryable = outcome in {"submission_unknown", "timeout"}
            target = "retrying" if retryable and job.attempts < job.max_attempts else "failed"
            transition(job, target)
            job.result_payload = result
            job.error_code = "scene_generation_" + outcome
            job.error_message = str(
                result.get("reason")
                or result.get("errorMessage")
                or outcome
            )[:2000]
        else:
            transition(job, "succeeded")
            job.result_payload = result
        emit_event(
            db,
            workspace_id=job.workspace_id,
            event_type=f"studio.job.{job.status}",
            aggregate_type="generation_job",
            aggregate_id=job.id,
            correlation_id=job.correlation_id,
            actor_id=None,
            payload={"progress": job.progress},
        )
        db.commit()
        return job.status
    except Exception as error:
        db.refresh(job)
        job.error_code = type(error).__name__
        job.error_message = str(error)[:2000]
        provider_error_kind = str(
            (job.result_payload or {}).get("providerErrorKind") or ""
        ).lower()
        provider_quota_terminal = provider_error_kind in {
            "insufficient_quota",
            "credit_balance_exhausted",
            "billing_hard_limit_reached",
            "billing_not_active",
        }
        editing_terminal = (
            job.job_type in {"editing_gemini", "editing_ai"}
            and isinstance(error, ValueError)
            and (
                provider_quota_terminal
                or
                isinstance(error, ValidationError)
                or any(
                    marker in str(error)
                    for marker in ("conflict", "mismatch", "outcome_unknown", "unsupported", "required", "invalid")
                )
            )
        )
        transition(
            job,
            "cancelled"
            if job.status == "cancel_requested"
            else ("retrying" if job.attempts < job.max_attempts and not editing_terminal else "failed"),
        )
        db.commit()
        if job.status == "failed" and job.job_type == "media_probe":
            from .media_ingest import mark_media_ingest_failed

            mark_media_ingest_failed(db, job, error)
        return job.status
