from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ...domain.studios.contracts import (
    ConsentGrantV1,
    CreateConsentGrantRequest,
    CreateIdentityDeletionRequest,
    CreateIdentityEvaluationRequest,
    CreateIdentityProfileRequest,
    CreateIdentityVersionRequest,
    CreateVoiceProfileRequest,
    CreateVoiceVersionRequest,
    IdentityDeletionRequestV1,
    IdentityEvaluationV1,
    IdentityProfileV1,
    IdentityVersionV1,
    ReviewIdentityVersionRequest,
    VoiceProfileV1,
    VoiceVersionV1,
)
from ...models import (
    StudioConsentGrant,
    StudioGenerationJob,
    StudioIdentityDeletionRequest,
    StudioIdentityEvaluation,
    StudioIdentityProfile,
    StudioIdentityVersion,
    StudioModelRegistration,
    StudioProviderRegistration,
    StudioVoiceProfile,
    StudioVoiceVersion,
    User,
)
from .kernel import emit_event


def _utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def _canonical_hash(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


def consent_status(grant: StudioConsentGrant, now: datetime | None = None) -> str:
    if grant.status == "active" and _utc(grant.expires_at) <= (now or datetime.now(UTC)):
        return "expired"
    return grant.status


def consent_out(grant: StudioConsentGrant) -> ConsentGrantV1:
    return ConsentGrantV1(
        id=grant.id,
        workspace_id=grant.workspace_id,
        subject_key=grant.subject_key,
        subject_display_name=grant.subject_display_name,
        purpose=grant.purpose,
        scopes=grant.scopes,
        brand_ids=grant.brand_ids,
        channels=grant.channels,
        policy_version=grant.policy_version,
        evidence_asset_id=grant.evidence_asset_id,
        status=consent_status(grant),
        granted_by=grant.granted_by,
        granted_at=grant.granted_at,
        expires_at=grant.expires_at,
        revoked_at=grant.revoked_at,
        revoked_by=grant.revoked_by,
        revocation_reason=grant.revocation_reason,
        created_at=grant.created_at,
        updated_at=grant.updated_at,
    )


def identity_profile_out(profile: StudioIdentityProfile) -> IdentityProfileV1:
    return IdentityProfileV1.model_validate(profile)


def identity_version_out(version: StudioIdentityVersion) -> IdentityVersionV1:
    return IdentityVersionV1.model_validate(version)


def voice_profile_out(profile: StudioVoiceProfile) -> VoiceProfileV1:
    return VoiceProfileV1.model_validate(profile)


def voice_version_out(version: StudioVoiceVersion) -> VoiceVersionV1:
    return VoiceVersionV1.model_validate(version)


def identity_evaluation_out(evaluation: StudioIdentityEvaluation) -> IdentityEvaluationV1:
    return IdentityEvaluationV1.model_validate(evaluation)


def identity_deletion_out(deletion: StudioIdentityDeletionRequest) -> IdentityDeletionRequestV1:
    return IdentityDeletionRequestV1.model_validate(deletion)


def create_consent_grant(
    db: Session, request: CreateConsentGrantRequest, user: User
) -> StudioConsentGrant:
    now = datetime.now(UTC)
    if _utc(request.expires_at) <= now:
        raise ValueError("consent_expiry_must_be_future")
    grant = StudioConsentGrant(
        workspace_id=request.workspace_id,
        subject_key=request.subject_key,
        subject_display_name=request.subject_display_name,
        purpose=request.purpose,
        scopes=request.scopes,
        brand_ids=request.brand_ids,
        channels=request.channels,
        policy_version=request.policy_version,
        evidence_asset_id=request.evidence_asset_id,
        status="active",
        granted_by=user.id,
        granted_at=now,
        expires_at=request.expires_at,
    )
    db.add(grant)
    db.flush()
    emit_event(
        db,
        workspace_id=grant.workspace_id,
        event_type="studio.consent.granted",
        aggregate_type="consent_grant",
        aggregate_id=grant.id,
        correlation_id=f"consent:{grant.id}",
        actor_id=user.id,
        payload={"policyVersion": grant.policy_version, "scopes": grant.scopes},
    )
    db.commit()
    db.refresh(grant)
    return grant


def require_consent(
    db: Session,
    *,
    consent_grant_id: str | None,
    workspace_id: str,
    subject_key: str,
    scopes: set[str],
) -> StudioConsentGrant:
    if not consent_grant_id:
        raise ValueError("consent_required")
    grant = db.scalar(
        select(StudioConsentGrant).where(
            StudioConsentGrant.id == consent_grant_id,
            StudioConsentGrant.workspace_id == workspace_id,
        )
    )
    if not grant:
        raise ValueError("consent_not_found")
    if grant.subject_key != subject_key:
        raise ValueError("consent_subject_mismatch")
    if consent_status(grant) != "active":
        raise ValueError("consent_not_active")
    if not scopes.issubset(set(grant.scopes)):
        raise ValueError("consent_scope_missing")
    return grant


def revoke_consent_grant(
    db: Session, grant: StudioConsentGrant, *, reason: str, user: User
) -> StudioConsentGrant:
    if grant.status == "revoked":
        return grant
    now = datetime.now(UTC)
    grant.status = "revoked"
    grant.revoked_at = now
    grant.revoked_by = user.id
    grant.revocation_reason = reason

    identity_versions = db.scalars(
        select(StudioIdentityVersion).where(
            StudioIdentityVersion.consent_grant_id == grant.id,
            StudioIdentityVersion.status.not_in(("deleted", "deleting")),
        )
    ).all()
    voice_versions = db.scalars(
        select(StudioVoiceVersion).where(
            StudioVoiceVersion.consent_grant_id == grant.id,
            StudioVoiceVersion.status.not_in(("deleted", "deleting")),
        )
    ).all()
    for version in identity_versions:
        version.status = "revoked"
    for version in voice_versions:
        version.status = "revoked"

    identity_profile_ids = {version.profile_id for version in identity_versions}
    voice_profile_ids = {version.profile_id for version in voice_versions}
    if identity_profile_ids:
        for profile in db.scalars(
            select(StudioIdentityProfile).where(StudioIdentityProfile.id.in_(identity_profile_ids))
        ).all():
            profile.status = "revoked"
    if voice_profile_ids:
        for profile in db.scalars(
            select(StudioVoiceProfile).where(StudioVoiceProfile.id.in_(voice_profile_ids))
        ).all():
            profile.status = "revoked"

    jobs = db.scalars(
        select(StudioGenerationJob).where(
            StudioGenerationJob.consent_grant_id == grant.id,
            StudioGenerationJob.status.in_(("queued", "running", "retrying")),
        )
    ).all()
    for job in jobs:
        if job.status == "queued":
            job.status = "cancelled"
            job.finished_at = now
        else:
            job.status = "cancel_requested"
        job.cancel_reason = "consent_revoked"

    emit_event(
        db,
        workspace_id=grant.workspace_id,
        event_type="studio.consent.revoked",
        aggregate_type="consent_grant",
        aggregate_id=grant.id,
        correlation_id=f"consent:{grant.id}",
        actor_id=user.id,
        payload={
            "reason": reason,
            "identityVersionsInvalidated": len(identity_versions),
            "voiceVersionsInvalidated": len(voice_versions),
            "jobsBlocked": len(jobs),
        },
    )
    db.commit()
    db.refresh(grant)
    return grant


def create_identity_profile(
    db: Session, request: CreateIdentityProfileRequest, user: User
) -> StudioIdentityProfile:
    existing = db.scalar(
        select(StudioIdentityProfile).where(
            StudioIdentityProfile.workspace_id == request.workspace_id,
            StudioIdentityProfile.subject_key == request.subject_key,
        )
    )
    if existing:
        raise ValueError("identity_subject_already_exists")
    profile = StudioIdentityProfile(
        workspace_id=request.workspace_id,
        subject_key=request.subject_key,
        display_name=request.display_name,
        identity_type=request.identity_type,
        status="draft",
        owner_user_id=request.owner_user_id,
        created_by=user.id,
    )
    db.add(profile)
    db.flush()
    emit_event(
        db,
        workspace_id=profile.workspace_id,
        event_type="studio.identity.created",
        aggregate_type="identity_profile",
        aggregate_id=profile.id,
        correlation_id=f"identity:{profile.id}",
        actor_id=user.id,
        payload={"identityType": profile.identity_type},
    )
    db.commit()
    db.refresh(profile)
    return profile


def create_identity_version(
    db: Session, profile: StudioIdentityProfile, request: CreateIdentityVersionRequest, user: User
) -> StudioIdentityVersion:
    if profile.status in {"revoked", "deleting", "deleted"}:
        raise ValueError("identity_profile_not_usable")
    if profile.identity_type == "natural_person":
        if not request.sample_asset_ids:
            raise ValueError("identity_samples_required")
        require_consent(
            db,
            consent_grant_id=request.consent_grant_id,
            workspace_id=profile.workspace_id,
            subject_key=profile.subject_key,
            scopes={"identity.enroll"},
        )
    sample_ids = request.sample_asset_ids
    artifact_payload = [item.model_dump(by_alias=True, mode="json") for item in request.derived_artifacts]
    next_version = (db.scalar(select(func.max(StudioIdentityVersion.version)).where(
        StudioIdentityVersion.profile_id == profile.id
    )) or 0) + 1
    digest = _canonical_hash(
        {
            "profileId": profile.id,
            "version": next_version,
            "consentGrantId": request.consent_grant_id,
            "capabilities": request.capabilities,
            "sampleAssetIds": sample_ids,
            "derivedArtifacts": artifact_payload,
        }
    )
    version = StudioIdentityVersion(
        workspace_id=profile.workspace_id,
        profile_id=profile.id,
        version=next_version,
        consent_grant_id=request.consent_grant_id,
        status="draft",
        capabilities=request.capabilities,
        sample_asset_ids=sample_ids,
        derived_artifacts=artifact_payload,
        content_hash=digest,
        created_by=user.id,
    )
    db.add(version)
    db.flush()
    emit_event(
        db,
        workspace_id=version.workspace_id,
        event_type="studio.identity.version_created",
        aggregate_type="identity_profile",
        aggregate_id=profile.id,
        correlation_id=f"identity:{profile.id}",
        actor_id=user.id,
        payload={"versionId": version.id, "version": version.version},
    )
    db.commit()
    db.refresh(version)
    return version


def create_voice_profile(
    db: Session, request: CreateVoiceProfileRequest, user: User
) -> StudioVoiceProfile:
    profile = StudioVoiceProfile(
        workspace_id=request.workspace_id,
        identity_profile_id=request.identity_profile_id,
        display_name=request.display_name,
        locale=request.locale,
        voice_type=request.voice_type,
        status="draft",
        created_by=user.id,
    )
    db.add(profile)
    db.flush()
    emit_event(
        db,
        workspace_id=profile.workspace_id,
        event_type="studio.voice.created",
        aggregate_type="voice_profile",
        aggregate_id=profile.id,
        correlation_id=f"voice:{profile.id}",
        actor_id=user.id,
        payload={"voiceType": profile.voice_type, "locale": profile.locale},
    )
    db.commit()
    db.refresh(profile)
    return profile


def create_voice_version(
    db: Session, profile: StudioVoiceProfile, request: CreateVoiceVersionRequest, user: User
) -> StudioVoiceVersion:
    if profile.status in {"revoked", "deleting", "deleted"}:
        raise ValueError("voice_profile_not_usable")
    if profile.voice_type == "cloned":
        if not request.sample_asset_ids:
            raise ValueError("voice_samples_required")
        if not profile.identity_profile_id:
            raise ValueError("cloned_voice_requires_identity")
        identity = db.scalar(
            select(StudioIdentityProfile).where(
                StudioIdentityProfile.id == profile.identity_profile_id,
                StudioIdentityProfile.workspace_id == profile.workspace_id,
            )
        )
        if not identity:
            raise ValueError("identity_not_found")
        require_consent(
            db,
            consent_grant_id=request.consent_grant_id,
            workspace_id=profile.workspace_id,
            subject_key=identity.subject_key,
            scopes={"voice.enroll", "voice.clone"},
        )
    artifact_payload = [item.model_dump(by_alias=True, mode="json") for item in request.derived_artifacts]
    next_version = (db.scalar(select(func.max(StudioVoiceVersion.version)).where(
        StudioVoiceVersion.profile_id == profile.id
    )) or 0) + 1
    digest = _canonical_hash(
        {
            "profileId": profile.id,
            "version": next_version,
            "consentGrantId": request.consent_grant_id,
            "sampleAssetIds": request.sample_asset_ids,
            "derivedArtifacts": artifact_payload,
            "pronunciationProfile": request.pronunciation_profile,
        }
    )
    version = StudioVoiceVersion(
        workspace_id=profile.workspace_id,
        profile_id=profile.id,
        version=next_version,
        consent_grant_id=request.consent_grant_id,
        status="draft",
        sample_asset_ids=request.sample_asset_ids,
        derived_artifacts=artifact_payload,
        pronunciation_profile=request.pronunciation_profile,
        content_hash=digest,
        created_by=user.id,
    )
    db.add(version)
    db.flush()
    emit_event(
        db,
        workspace_id=version.workspace_id,
        event_type="studio.voice.version_created",
        aggregate_type="voice_profile",
        aggregate_id=profile.id,
        correlation_id=f"voice:{profile.id}",
        actor_id=user.id,
        payload={"versionId": version.id, "version": version.version},
    )
    db.commit()
    db.refresh(version)
    return version


def create_identity_evaluation(
    db: Session,
    version: StudioIdentityVersion | StudioVoiceVersion,
    request: CreateIdentityEvaluationRequest,
    user: User,
    *,
    target_type: str,
) -> StudioIdentityEvaluation:
    if version.status != "draft":
        raise ValueError("identity_evaluation_requires_draft")
    provider = (
        db.get(StudioProviderRegistration, request.provider_registration_id)
        if request.provider_registration_id
        else None
    )
    model = db.get(StudioModelRegistration, request.model_registration_id) if request.model_registration_id else None
    if request.evaluator_kind in {"automated", "combined"} and (not provider or not model):
        raise ValueError("automated_evaluation_requires_provider_and_model")
    if request.provider_registration_id and (not provider or provider.status != "approved"):
        raise ValueError("evaluation_provider_not_approved")
    if request.model_registration_id and (not model or model.status != "approved"):
        raise ValueError("evaluation_model_not_approved")
    if model and provider and model.provider_registration_id != provider.id:
        raise ValueError("evaluation_model_provider_mismatch")
    now = datetime.now(UTC)
    evaluation = StudioIdentityEvaluation(
        workspace_id=version.workspace_id,
        target_type=target_type,
        identity_version_id=version.id if target_type == "identity_version" else None,
        voice_version_id=version.id if target_type == "voice_version" else None,
        status=request.status,
        evaluator_kind=request.evaluator_kind,
        quality_metrics=request.quality_metrics,
        checks=[item.model_dump(by_alias=True, mode="json") for item in request.checks],
        preview_asset_ids=request.preview_asset_ids,
        provider_registration_id=request.provider_registration_id,
        model_registration_id=request.model_registration_id,
        evaluated_by=user.id,
        evaluated_at=now,
        notes=request.notes,
    )
    db.add(evaluation)
    db.flush()
    emit_event(
        db,
        workspace_id=version.workspace_id,
        event_type=f"studio.{target_type.removesuffix('_version')}.evaluated",
        aggregate_type=target_type,
        aggregate_id=version.id,
        correlation_id=f"{target_type}:{version.id}",
        actor_id=user.id,
        payload={
            "evaluationId": evaluation.id,
            "status": evaluation.status,
            "evaluatorKind": evaluation.evaluator_kind,
            "providerRegistrationId": evaluation.provider_registration_id,
            "modelRegistrationId": evaluation.model_registration_id,
        },
    )
    db.commit()
    db.refresh(evaluation)
    return evaluation


def _latest_evaluation(
    db: Session, version: StudioIdentityVersion | StudioVoiceVersion, target_type: str
) -> StudioIdentityEvaluation | None:
    target_column = (
        StudioIdentityEvaluation.identity_version_id
        if target_type == "identity_version"
        else StudioIdentityEvaluation.voice_version_id
    )
    return db.scalar(
        select(StudioIdentityEvaluation)
        .where(target_column == version.id)
        .order_by(StudioIdentityEvaluation.evaluated_at.desc(), StudioIdentityEvaluation.created_at.desc())
    )


def _activation_consent(
    db: Session,
    version: StudioIdentityVersion | StudioVoiceVersion,
    profile: StudioIdentityProfile | StudioVoiceProfile,
    target_type: str,
) -> None:
    if target_type == "identity_version":
        if not isinstance(profile, StudioIdentityProfile) or profile.identity_type != "natural_person":
            return
        scopes = {"identity.enroll"}
        scopes.update(set(version.capabilities).intersection({"avatar.generate"}))
        require_consent(
            db,
            consent_grant_id=version.consent_grant_id,
            workspace_id=profile.workspace_id,
            subject_key=profile.subject_key,
            scopes=scopes,
        )
        return
    if not isinstance(profile, StudioVoiceProfile) or profile.voice_type != "cloned":
        return
    identity = db.get(StudioIdentityProfile, profile.identity_profile_id) if profile.identity_profile_id else None
    if not identity:
        raise ValueError("identity_not_found")
    require_consent(
        db,
        consent_grant_id=version.consent_grant_id,
        workspace_id=profile.workspace_id,
        subject_key=identity.subject_key,
        scopes={"voice.enroll", "voice.clone"},
    )


def review_identity_version(
    db: Session,
    profile: StudioIdentityProfile | StudioVoiceProfile,
    version: StudioIdentityVersion | StudioVoiceVersion,
    request: ReviewIdentityVersionRequest,
    user: User,
    *,
    target_type: str,
) -> StudioIdentityVersion | StudioVoiceVersion:
    if version.status != "draft":
        raise ValueError("identity_version_already_reviewed")
    now = datetime.now(UTC)
    if request.action == "approve":
        evaluation = _latest_evaluation(db, version, target_type)
        if not evaluation or evaluation.status != "passed":
            raise ValueError("passed_identity_evaluation_required")
        _activation_consent(db, version, profile, target_type)
        version_model = StudioIdentityVersion if target_type == "identity_version" else StudioVoiceVersion
        for active in db.scalars(
            select(version_model).where(
                version_model.profile_id == profile.id,
                version_model.status == "active",
                version_model.id != version.id,
            )
        ).all():
            active.status = "superseded"
        version.status = "active"
        profile.status = "active"
    else:
        version.status = "rejected"
    version.reviewed_by = user.id
    version.reviewed_at = now
    version.review_comment = request.comment
    emit_event(
        db,
        workspace_id=version.workspace_id,
        event_type=f"studio.{target_type.removesuffix('_version')}.{version.status}",
        aggregate_type=target_type,
        aggregate_id=version.id,
        correlation_id=f"{target_type}:{version.id}",
        actor_id=user.id,
        payload={"action": request.action, "comment": request.comment},
    )
    db.commit()
    db.refresh(version)
    return version


def require_active_version_consent(
    db: Session,
    version: StudioIdentityVersion | StudioVoiceVersion,
    *,
    consent_grant_id: str | None,
) -> None:
    if version.status != "active":
        raise ValueError("identity_version_not_active")
    if not version.consent_grant_id:
        return
    if consent_grant_id != version.consent_grant_id:
        raise ValueError("identity_version_consent_mismatch")
    grant = db.get(StudioConsentGrant, version.consent_grant_id)
    if not grant or consent_status(grant) != "active":
        raise ValueError("consent_not_active")


def request_identity_deletion(
    db: Session,
    profile: StudioIdentityProfile | StudioVoiceProfile,
    request: CreateIdentityDeletionRequest,
    idempotency_key: str,
    user: User,
    *,
    target_type: str,
) -> tuple[StudioIdentityDeletionRequest, bool]:
    replay = db.scalar(
        select(StudioIdentityDeletionRequest).where(
            StudioIdentityDeletionRequest.workspace_id == profile.workspace_id,
            StudioIdentityDeletionRequest.idempotency_key == idempotency_key,
        )
    )
    if replay:
        target_matches = (
            target_type == replay.target_type
            and (replay.identity_profile_id == profile.id or replay.voice_profile_id == profile.id)
        )
        payload_matches = (
            replay.reason == request.reason
            and replay.delete_source_samples == request.delete_source_samples
        )
        if not target_matches or not payload_matches:
            raise ValueError("idempotency_payload_conflict")
        return replay, False
    if profile.status in {"deleting", "deleted"}:
        raise ValueError("identity_deletion_already_planned")

    identity_profiles: list[StudioIdentityProfile] = []
    voice_profiles: list[StudioVoiceProfile] = []
    if target_type == "identity_profile":
        if not isinstance(profile, StudioIdentityProfile):
            raise ValueError("identity_deletion_target_mismatch")
        identity_profiles = [profile]
        voice_profiles = db.scalars(
            select(StudioVoiceProfile).where(
                StudioVoiceProfile.workspace_id == profile.workspace_id,
                StudioVoiceProfile.identity_profile_id == profile.id,
                StudioVoiceProfile.status != "deleted",
            )
        ).all()
    else:
        if not isinstance(profile, StudioVoiceProfile):
            raise ValueError("identity_deletion_target_mismatch")
        voice_profiles = [profile]

    identity_profile_ids = [item.id for item in identity_profiles]
    voice_profile_ids = [item.id for item in voice_profiles]
    identity_versions = (
        db.scalars(
            select(StudioIdentityVersion).where(
                StudioIdentityVersion.profile_id.in_(identity_profile_ids),
                StudioIdentityVersion.status != "deleted",
            )
        ).all()
        if identity_profile_ids
        else []
    )
    voice_versions = (
        db.scalars(
            select(StudioVoiceVersion).where(
                StudioVoiceVersion.profile_id.in_(voice_profile_ids),
                StudioVoiceVersion.status != "deleted",
            )
        ).all()
        if voice_profile_ids
        else []
    )
    identity_version_ids = [item.id for item in identity_versions]
    voice_version_ids = [item.id for item in voice_versions]
    target_filters = []
    if identity_version_ids:
        target_filters.append(StudioIdentityEvaluation.identity_version_id.in_(identity_version_ids))
    if voice_version_ids:
        target_filters.append(StudioIdentityEvaluation.voice_version_id.in_(voice_version_ids))
    evaluations = (
        db.scalars(select(StudioIdentityEvaluation).where(or_(*target_filters))).all()
        if target_filters
        else []
    )

    source_sample_ids = {
        asset_id
        for version in [*identity_versions, *voice_versions]
        for asset_id in (version.sample_asset_ids or [])
    }
    derived_asset_ids = {
        artifact.get("id")
        for version in [*identity_versions, *voice_versions]
        for artifact in (version.derived_artifacts or [])
        if artifact.get("id")
    }
    preview_asset_ids = {
        asset_id for evaluation in evaluations for asset_id in (evaluation.preview_asset_ids or [])
    }
    job_filters = []
    if identity_version_ids:
        job_filters.append(StudioGenerationJob.identity_version_id.in_(identity_version_ids))
    if voice_version_ids:
        job_filters.append(StudioGenerationJob.voice_version_id.in_(voice_version_ids))
    jobs = (
        db.scalars(
            select(StudioGenerationJob).where(
                or_(*job_filters),
                StudioGenerationJob.status.in_(("queued", "running", "retrying", "cancel_requested")),
            )
        ).all()
        if job_filters
        else []
    )
    now = datetime.now(UTC)
    for job in jobs:
        if job.status == "queued":
            job.status = "cancelled"
            job.finished_at = now
        elif job.status != "cancel_requested":
            job.status = "cancel_requested"
        job.cancel_reason = "identity_deletion_requested"
    for item in [*identity_versions, *voice_versions, *identity_profiles, *voice_profiles]:
        item.status = "deleting"

    deletion_plan = {
        "schemaVersion": "studio.identity-deletion-plan.v1",
        "identityProfileIds": identity_profile_ids,
        "identityVersionIds": identity_version_ids,
        "voiceProfileIds": voice_profile_ids,
        "voiceVersionIds": voice_version_ids,
        "derivedAssetIds": sorted(derived_asset_ids),
        "previewAssetIds": sorted(preview_asset_ids),
        "sourceSampleAssetIds": sorted(source_sample_ids),
        "jobIds": [job.id for job in jobs],
        "steps": [
            "block_new_jobs",
            "cancel_or_discard_active_jobs",
            "verify_legal_hold_and_shared_references",
            "delete_derived_and_preview_objects",
            "delete_source_samples_if_explicit_and_unshared",
            "tombstone_versions_and_profiles",
        ],
        "executionGate": "identity_deletion_execution_enabled",
    }
    deletion = StudioIdentityDeletionRequest(
        workspace_id=profile.workspace_id,
        target_type=target_type,
        identity_profile_id=profile.id if target_type == "identity_profile" else None,
        voice_profile_id=profile.id if target_type == "voice_profile" else None,
        status="planned",
        reason=request.reason,
        delete_source_samples=request.delete_source_samples,
        deletion_plan=deletion_plan,
        idempotency_key=idempotency_key,
        requested_by=user.id,
        requested_at=now,
    )
    db.add(deletion)
    db.flush()
    emit_event(
        db,
        workspace_id=profile.workspace_id,
        event_type="studio.identity.deletion_planned",
        aggregate_type=target_type,
        aggregate_id=profile.id,
        correlation_id=f"identity-deletion:{deletion.id}",
        actor_id=user.id,
        payload={
            "deletionRequestId": deletion.id,
            "jobsBlocked": len(jobs),
            "derivedAssets": len(derived_asset_ids | preview_asset_ids),
            "sourceSamples": len(source_sample_ids),
            "deleteSourceSamples": request.delete_source_samples,
        },
    )
    db.commit()
    db.refresh(deletion)
    return deletion, True
