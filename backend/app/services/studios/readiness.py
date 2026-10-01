from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...domain.studios.contracts import (
    StudioCapabilitiesV1,
    StudioCapabilityName,
    StudioCapabilityReadinessV1,
)
from ...models import (
    StudioConsentGrant,
    StudioIdentityVersion,
    StudioModelRegistration,
    StudioProviderRegistration,
    StudioVoiceVersion,
)
from .identity import consent_status

_CAPABILITIES: tuple[StudioCapabilityName, ...] = (
    "presenter",
    "avatar",
    "voice_clone",
    "stock_voice",
    "transcription",
)

_ALIASES: dict[StudioCapabilityName, tuple[str, ...]] = {
    "presenter": ("presenter", "presenter.generate", "avatar.generate", "avatar_video"),
    "avatar": ("avatar", "avatar.generate", "identity.enroll"),
    "voice_clone": ("voice_clone", "voice.clone", "voice.enroll"),
    "stock_voice": ("stock_voice", "stock.voice", "speech_cpu"),
    "transcription": ("transcription", "speech_to_text", "asr"),
}


def _normalized(value: str) -> str:
    return (
        value.strip()
        .lower()
        .replace("-", "")
        .replace("_", "")
        .replace(".", "")
    )


def _matches(value: str, aliases: tuple[str, ...]) -> bool:
    normalized = _normalized(value)
    return any(_normalized(alias) in normalized or normalized in _normalized(alias) for alias in aliases)


def _approved_model(model: StudioModelRegistration, approved_provider_ids: set[str], aliases: tuple[str, ...]) -> bool:
    return (
        model.status == "approved"
        and model.provider_registration_id in approved_provider_ids
        and any(_matches(capability, aliases) for capability in (model.capabilities or []))
    )


def _benchmark_ready(
    providers: list[StudioProviderRegistration], models: list[StudioModelRegistration]
) -> bool:
    """Require explicit benchmark evidence; registry approval alone is insufficient."""

    return any(
        provider.manifest.get("benchmarkStatus") == "passed"
        and provider.manifest.get("workerAdvertised") is True
        and any(
            model.provider_registration_id == provider.id
            and model.manifest.get("benchmarkStatus") == "passed"
            for model in models
        )
        for provider in providers
    )


def _consent_ready(
    capability: StudioCapabilityName,
    identity_versions: list[StudioIdentityVersion],
    voice_versions: list[StudioVoiceVersion],
    grants: list[StudioConsentGrant],
) -> bool:
    if capability in {"stock_voice", "transcription"}:
        return True
    active_grants = {
        grant.id: grant
        for grant in grants
        if consent_status(grant) == "active"
    }
    identity_ok = any(
        version.consent_grant_id in active_grants
        and (
            capability != "avatar"
            or "avatar.generate" in (active_grants[version.consent_grant_id].scopes or [])
        )
        for version in identity_versions
    )
    voice_ok = any(
        version.consent_grant_id in active_grants
        and "voice.clone" in (active_grants[version.consent_grant_id].scopes or [])
        for version in voice_versions
    )
    if capability == "avatar":
        return identity_ok
    if capability == "voice_clone":
        return voice_ok
    return identity_ok and voice_ok


def _publication_consent_ready(
    capability: StudioCapabilityName,
    grants: list[StudioConsentGrant],
) -> bool:
    """Publication is a separate legal gate from generating a private preview."""
    if capability in {"stock_voice", "transcription"}:
        return True
    return any(
        consent_status(grant) == "active" and "publish.synthetic" in (grant.scopes or [])
        for grant in grants
    )


def _readiness(
    db: Session,
    workspace_id: str,
    capability: StudioCapabilityName,
    *,
    evaluated_at: datetime,
) -> StudioCapabilityReadinessV1:
    aliases = _ALIASES[capability]
    all_providers = db.scalars(select(StudioProviderRegistration)).all()
    candidate_providers = [item for item in all_providers if _matches(item.capability, aliases)]
    approved_providers = [item for item in candidate_providers if item.status == "approved"]
    approved_provider_ids = {item.id for item in approved_providers}
    all_models = db.scalars(select(StudioModelRegistration)).all()
    candidate_models = [
        item
        for item in all_models
        if any(_matches(value, aliases) for value in (item.capabilities or []))
        or item.provider_registration_id in {provider.id for provider in candidate_providers}
    ]
    approved_models = [item for item in candidate_models if _approved_model(item, approved_provider_ids, aliases)]

    identity_versions = db.scalars(
        select(StudioIdentityVersion).where(
            StudioIdentityVersion.workspace_id == workspace_id,
            StudioIdentityVersion.status == "active",
        )
    ).all()
    voice_versions = db.scalars(
        select(StudioVoiceVersion).where(
            StudioVoiceVersion.workspace_id == workspace_id,
            StudioVoiceVersion.status == "active",
        )
    ).all()
    grants = db.scalars(
        select(StudioConsentGrant).where(StudioConsentGrant.workspace_id == workspace_id)
    ).all()
    active_grants = [grant for grant in grants if consent_status(grant) == "active"]

    benchmark_ready = _benchmark_ready(approved_providers, approved_models)
    runtime_ready = any(
        provider.manifest.get("workerAdvertised") is True for provider in approved_providers
    )
    license_ready = bool(approved_providers and approved_models)
    consent_ready = _consent_ready(capability, identity_versions, voice_versions, grants)
    publication_consent_ready = _publication_consent_ready(capability, grants)
    reasons: list[str] = []
    if not candidate_providers:
        reasons.append("provider_registry_empty")
    elif not approved_providers:
        reasons.append("provider_not_approved")
    if not candidate_models:
        reasons.append("model_registry_empty")
    elif not approved_models:
        reasons.append("model_not_approved")
    if approved_providers and not runtime_ready:
        reasons.append("worker_runtime_not_advertised")
    if not benchmark_ready:
        reasons.append("benchmark_evidence_pending")
    if capability in {"presenter", "avatar"} and not identity_versions:
        reasons.append("identity_version_not_active")
    if capability in {"presenter", "voice_clone"} and not voice_versions:
        reasons.append("voice_version_not_active")
    if not consent_ready:
        reasons.append("consent_not_verified")
    if not publication_consent_ready:
        reasons.append("publication_consent_not_verified")

    if not candidate_providers or not candidate_models:
        status = "unavailable"
    elif not approved_providers or not approved_models or not consent_ready:
        status = "blocked"
    elif not benchmark_ready:
        status = "review"
    else:
        status = "ready"
    end_to_end_ready = status == "ready"
    return StudioCapabilityReadinessV1(
        workspace_id=workspace_id,
        capability=capability,
        status=status,
        provider_ready=end_to_end_ready,
        capture_ready=end_to_end_ready and capability == "presenter",
        provider_candidates=len(candidate_providers),
        approved_providers=len(approved_providers),
        model_candidates=len(candidate_models),
        approved_models=len(approved_models),
        active_identity_versions=len(identity_versions),
        active_voice_versions=len(voice_versions),
        active_consent_grants=len(active_grants),
        benchmark_ready=benchmark_ready,
        license_ready=license_ready,
        consent_ready=consent_ready,
        publication_allowed=end_to_end_ready and publication_consent_ready,
        reasons=reasons,
        evaluated_at=evaluated_at,
    )


def studio_capabilities(db: Session, workspace_id: str) -> StudioCapabilitiesV1:
    evaluated_at = datetime.now(UTC)
    return StudioCapabilitiesV1(
        workspace_id=workspace_id,
        capabilities=[
            _readiness(db, workspace_id, capability, evaluated_at=evaluated_at)
            for capability in _CAPABILITIES
        ],
        evaluated_at=evaluated_at,
    )
