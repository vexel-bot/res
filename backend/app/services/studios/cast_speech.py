"""Bind narration to the exact selected library voice, never a default timbre."""

import hashlib
from dataclasses import dataclass

from sqlalchemy import select

from ...domain.studios.contracts import CreateGenerationJobRequest, SpeechSynthesisRequestV1, VoiceVersionReferenceV1
from ...models import LibraryAsset, StudioProviderRegistration, StudioVoiceProfile, StudioVoiceVersion
from .casting import resolve_cast
from .jobs import (
    create_job,
    require_stock_voice_binding,
    require_voice_clone_binding,
)
from .speech_runtime import resolve_speech_provider


@dataclass(frozen=True)
class SelectedSpeech:
    voice_version_id: str
    consent_grant_id: str | None
    job_type: str
    provider: str
    voice_key: str
    locale: str

    def request(self, text: str):
        return SpeechSynthesisRequestV1(
            text=text,
            script_digest_sha256=hashlib.sha256(text.encode()).hexdigest(),
            voice_key=self.voice_key,
            locale=self.locale,
        )


def selected_speech(db, workspace_id: str, reference: VoiceVersionReferenceV1 | dict) -> SelectedSpeech:
    ref = VoiceVersionReferenceV1.model_validate(reference)
    resolved = resolve_cast(db, workspace_id, None, ref.id)["voice"]
    if str(ref.version) != str(resolved["version"]) or ref.consent_grant_id != resolved["consentGrantId"]:
        raise ValueError("cast_version_reference_mismatch")
    version = db.get(StudioVoiceVersion, ref.id)
    profile = db.get(StudioVoiceProfile, version.profile_id)
    binding = (version.pronunciation_profile or {}).get("synthesisBinding") or {}
    if not isinstance(binding, dict):
        raise ValueError("stock_voice_synthesis_binding_mismatch")
    cloned = profile.voice_type == "cloned"
    kind = "voice_clone" if cloned else "stock_voice"
    preferred = binding.get("provider")
    if preferred is not None and (not isinstance(preferred, str) or not preferred.strip()):
        raise ValueError("selected_voice_runtime_unavailable")
    if not cloned and (not preferred or not binding.get("voiceKey")):
        raise ValueError("stock_voice_synthesis_binding_mismatch")
    providers = (
        [preferred]
        if preferred
        else list(
            db.scalars(
                select(StudioProviderRegistration.provider)
                .where(
                    StudioProviderRegistration.capability == kind,
                    StudioProviderRegistration.status == "approved",
                )
                .order_by(StudioProviderRegistration.provider)
            )
        )
    )
    for provider in providers:
        try:
            adapter = resolve_speech_provider(db, job_type=kind, provider_name=provider)
        except ValueError:
            if preferred:
                raise
            continue
        # Automatic production cannot select a paid remote adapter or another timbre.
        if not adapter or getattr(adapter, "execution_environment", None) != "local":
            continue
        return SelectedSpeech(
            ref.id, ref.consent_grant_id, kind, provider, ref.id if cloned else binding["voiceKey"], profile.locale
        )
    raise ValueError("selected_voice_runtime_unavailable")


def create_selected_speech_job(
    db,
    selection: SelectedSpeech,
    text: str,
    user,
    *,
    workspace_id: str,
    document_id: str | None,
    key: str,
    correlation_id: str,
    commit=True,
):
    return create_job(
        db,
        CreateGenerationJobRequest(
            workspace_id=workspace_id,
            document_id=document_id,
            consent_grant_id=selection.consent_grant_id,
            voice_version_id=selection.voice_version_id,
            job_type=selection.job_type,
            provider=selection.provider,
            request=selection.request(text).model_dump(by_alias=True, mode="json"),
            correlation_id=correlation_id,
        ),
        key,
        user,
        commit=commit,
    )


def selected_speech_asset(db, job, reference, text: str):
    """Recheck a saved result against its voice, exact script and asset lineage."""
    ref = VoiceVersionReferenceV1.model_validate(reference)
    resolved = resolve_cast(db, job.workspace_id, None, ref.id)["voice"]
    if str(ref.version) != str(resolved["version"]) or ref.consent_grant_id != resolved["consentGrantId"]:
        raise ValueError("cast_version_reference_mismatch")
    expected_hash = hashlib.sha256(text.encode()).hexdigest()
    if job.voice_version_id != ref.id or job.consent_grant_id != ref.consent_grant_id:
        raise ValueError("production_voice_selection_conflict")
    request = SpeechSynthesisRequestV1.model_validate(job.request_payload)
    if request.script_digest_sha256 != expected_hash or request.text != text:
        raise ValueError("production_voice_script_conflict")
    profile = db.get(StudioVoiceProfile, db.get(StudioVoiceVersion, ref.id).profile_id)
    if profile.voice_type == "cloned":
        if job.job_type != "voice_clone" or request.voice_key != ref.id:
            raise ValueError("production_voice_selection_conflict")
        require_voice_clone_binding(
            db, workspace_id=job.workspace_id, voice_version_id=ref.id, consent_grant_id=ref.consent_grant_id
        )
    else:
        if job.job_type != "stock_voice":
            raise ValueError("production_voice_selection_conflict")
        require_stock_voice_binding(
            db,
            workspace_id=job.workspace_id,
            voice_version_id=ref.id,
            provider=job.provider,
            payload=job.request_payload,
        )
    if job.status != "succeeded":
        return None
    result = job.result_payload or {}
    asset = db.get(LibraryAsset, result.get("assetId")) if result.get("assetId") else None
    if (
        not asset
        or asset.workspace_id != job.workspace_id
        or asset.lifecycle_status != "active"
        or not asset.storage_key
    ):
        raise ValueError("production_narration_asset_conflict")
    metadata = asset.object_metadata or {}
    if (
        result.get("scriptDigestSha256") != expected_hash
        or result.get("jobType") != job.job_type
        or asset.checksum_sha256 != result.get("checksumSha256")
        or not (asset.media_type or "").startswith("audio/")
        or metadata.get("generationJobId") != job.id
        or metadata.get("voiceVersionId") != ref.id
        or metadata.get("scriptDigestSha256") != expected_hash
        or metadata.get("consentGrantId") != ref.consent_grant_id
    ):
        raise ValueError("production_voice_lineage_conflict")
    return asset
