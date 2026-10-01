from __future__ import annotations

import hashlib
from collections.abc import Callable, Iterable
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...config import get_settings
from ...models import (
    BrandProfile,
    Campaign,
    CreativeDocument,
    KnowledgeDocument,
    LibraryAsset,
    Post,
    StudioConsentGrant,
    StudioEditDecisionSet,
    StudioGenerationJob,
    StudioIdentityDeletionRequest,
    StudioIdentityEvaluation,
    StudioIdentityProfile,
    StudioIdentityVersion,
    StudioMediaIngest,
    StudioReviewRequest,
    StudioTranscript,
    StudioVoiceProfile,
    StudioVoiceVersion,
)
from ..object_storage import ObjectStorage, get_object_storage
from .kernel import emit_event

TERMINAL_JOB_STATES = {"cancelled", "succeeded", "failed"}


class IdentityDeletionDeferred(RuntimeError):
    """The deletion is safe to retry after active generation jobs stop."""


class IdentityDeletionStorageError(RuntimeError):
    """Object storage failed after preflight; per-object receipts make retry safe."""


def queue_identity_deletion(db: Session, deletion: StudioIdentityDeletionRequest) -> bool:
    if deletion.status in {"queued", "running", "completed"}:
        return False
    deletion.status = "queued"
    deletion.queued_at = datetime.now(UTC)
    deletion.error_message = None
    db.commit()
    db.refresh(deletion)
    return True


def record_identity_deletion_queue_failure(
    db: Session,
    deletion: StudioIdentityDeletionRequest,
    error: Exception,
) -> None:
    deletion.status = "failed"
    deletion.error_message = f"queue_unavailable:{type(error).__name__}"[:2000]
    db.commit()


def _values(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _values(item)
    elif isinstance(value, (list, tuple, set)):
        for item in value:
            yield from _values(item)


def _referenced_assets(value: Any, candidates: set[str]) -> set[str]:
    matches: set[str] = set()
    for text in _values(value):
        if text in candidates:
            matches.add(text)
            continue
        if len(text) > 36:
            matches.update(asset_id for asset_id in candidates if asset_id in text)
    return matches


def _add_reference(
    references: dict[str, set[str]],
    asset_ids: Iterable[str],
    reference: str,
) -> None:
    for asset_id in asset_ids:
        references.setdefault(asset_id, set()).add(reference)


def _collect_external_references(
    db: Session,
    *,
    workspace_id: str,
    candidate_ids: set[str],
    identity_version_ids: set[str],
    voice_version_ids: set[str],
) -> dict[str, set[str]]:
    references: dict[str, set[str]] = {}
    if not candidate_ids:
        return references

    identity_versions = db.scalars(
        select(StudioIdentityVersion).where(
            StudioIdentityVersion.workspace_id == workspace_id,
            StudioIdentityVersion.status != "deleted",
        )
    ).all()
    for version in identity_versions:
        if version.id in identity_version_ids:
            continue
        matched = _referenced_assets(
            [version.sample_asset_ids, version.derived_artifacts], candidate_ids
        )
        _add_reference(references, matched, f"identity_version:{version.id}")

    voice_versions = db.scalars(
        select(StudioVoiceVersion).where(
            StudioVoiceVersion.workspace_id == workspace_id,
            StudioVoiceVersion.status != "deleted",
        )
    ).all()
    for version in voice_versions:
        if version.id in voice_version_ids:
            continue
        matched = _referenced_assets(
            [version.sample_asset_ids, version.derived_artifacts], candidate_ids
        )
        _add_reference(references, matched, f"voice_version:{version.id}")

    evaluations = db.scalars(
        select(StudioIdentityEvaluation).where(StudioIdentityEvaluation.workspace_id == workspace_id)
    ).all()
    for evaluation in evaluations:
        if (
            evaluation.identity_version_id in identity_version_ids
            or evaluation.voice_version_id in voice_version_ids
        ):
            continue
        matched = _referenced_assets(evaluation.preview_asset_ids, candidate_ids)
        _add_reference(references, matched, f"identity_evaluation:{evaluation.id}")

    for grant in db.scalars(
        select(StudioConsentGrant).where(StudioConsentGrant.workspace_id == workspace_id)
    ).all():
        if grant.evidence_asset_id in candidate_ids:
            _add_reference(references, [grant.evidence_asset_id], f"consent_evidence:{grant.id}")

    for document in db.scalars(
        select(KnowledgeDocument).where(KnowledgeDocument.workspace_id == workspace_id)
    ).all():
        if document.asset_id in candidate_ids:
            _add_reference(references, [document.asset_id], f"knowledge_document:{document.id}")

    for ingest in db.scalars(
        select(StudioMediaIngest).where(StudioMediaIngest.workspace_id == workspace_id)
    ).all():
        for field_name in ("asset_id", "proxy_asset_id", "waveform_asset_id"):
            asset_id = getattr(ingest, field_name)
            if asset_id in candidate_ids:
                _add_reference(references, [asset_id], f"media_ingest:{ingest.id}:{field_name}")

    for transcript in db.scalars(
        select(StudioTranscript).where(StudioTranscript.workspace_id == workspace_id)
    ).all():
        if transcript.asset_id in candidate_ids:
            _add_reference(references, [transcript.asset_id], f"transcript:{transcript.id}")

    for document in db.scalars(
        select(CreativeDocument).where(CreativeDocument.workspace_id == workspace_id)
    ).all():
        matched = _referenced_assets(
            [document.document, document.canonical_document, document.versions], candidate_ids
        )
        _add_reference(references, matched, f"creative_document:{document.id}")

    for review in db.scalars(
        select(StudioReviewRequest).where(StudioReviewRequest.workspace_id == workspace_id)
    ).all():
        matched = _referenced_assets(review.snapshot, candidate_ids)
        _add_reference(references, matched, f"studio_review:{review.id}")

    for decision_set in db.scalars(
        select(StudioEditDecisionSet).where(StudioEditDecisionSet.workspace_id == workspace_id)
    ).all():
        matched = _referenced_assets(
            [decision_set.decisions, decision_set.versions], candidate_ids
        )
        _add_reference(references, matched, f"edit_decision_set:{decision_set.id}")

    jobs = db.scalars(
        select(StudioGenerationJob).where(StudioGenerationJob.workspace_id == workspace_id)
    ).all()
    for job in jobs:
        if job.identity_version_id in identity_version_ids or job.voice_version_id in voice_version_ids:
            continue
        matched = _referenced_assets([job.request_payload, job.result_payload], candidate_ids)
        _add_reference(references, matched, f"generation_job:{job.id}")

    for post in db.scalars(select(Post).where(Post.workspace_id == workspace_id)).all():
        matched = _referenced_assets(
            [post.image_url, post.video_url, post.slides, post.versions], candidate_ids
        )
        _add_reference(references, matched, f"post:{post.id}")

    for campaign in db.scalars(select(Campaign).where(Campaign.workspace_id == workspace_id)).all():
        matched = _referenced_assets(
            [campaign.brief, campaign.strategy, campaign.versions, campaign.decisions], candidate_ids
        )
        _add_reference(references, matched, f"campaign:{campaign.id}")

    brand = db.scalar(select(BrandProfile).where(BrandProfile.workspace_id == workspace_id))
    if brand:
        matched = _referenced_assets([brand.products, brand.watchlist, brand.versions], candidate_ids)
        _add_reference(references, matched, f"brand_profile:{brand.id}")

    other_assets = db.scalars(
        select(LibraryAsset).where(
            LibraryAsset.workspace_id == workspace_id,
            LibraryAsset.lifecycle_status == "active",
        )
    ).all()
    for asset in other_assets:
        if asset.id in candidate_ids:
            continue
        matched = _referenced_assets(asset.object_metadata, candidate_ids)
        _add_reference(references, matched, f"asset_lineage:{asset.id}")
    return references


def _resolve_targets(
    db: Session, deletion: StudioIdentityDeletionRequest
) -> tuple[
    list[StudioIdentityProfile],
    list[StudioVoiceProfile],
    list[StudioIdentityVersion],
    list[StudioVoiceVersion],
    list[StudioIdentityEvaluation],
    list[StudioGenerationJob],
]:
    identity_profiles: list[StudioIdentityProfile] = []
    voice_profiles: list[StudioVoiceProfile] = []
    if deletion.target_type == "identity_profile":
        profile = db.scalar(
            select(StudioIdentityProfile).where(
                StudioIdentityProfile.id == deletion.identity_profile_id,
                StudioIdentityProfile.workspace_id == deletion.workspace_id,
            )
        )
        if profile:
            identity_profiles = [profile]
            voice_profiles = db.scalars(
                select(StudioVoiceProfile).where(
                    StudioVoiceProfile.workspace_id == deletion.workspace_id,
                    StudioVoiceProfile.identity_profile_id == profile.id,
                    StudioVoiceProfile.status != "deleted",
                )
            ).all()
    elif deletion.target_type == "voice_profile":
        profile = db.scalar(
            select(StudioVoiceProfile).where(
                StudioVoiceProfile.id == deletion.voice_profile_id,
                StudioVoiceProfile.workspace_id == deletion.workspace_id,
            )
        )
        if profile:
            voice_profiles = [profile]
    else:
        raise ValueError("identity_deletion_target_mismatch")

    identity_profile_ids = [profile.id for profile in identity_profiles]
    voice_profile_ids = [profile.id for profile in voice_profiles]
    identity_versions = (
        db.scalars(
            select(StudioIdentityVersion).where(
                StudioIdentityVersion.workspace_id == deletion.workspace_id,
                StudioIdentityVersion.profile_id.in_(identity_profile_ids),
            )
        ).all()
        if identity_profile_ids
        else []
    )
    voice_versions = (
        db.scalars(
            select(StudioVoiceVersion).where(
                StudioVoiceVersion.workspace_id == deletion.workspace_id,
                StudioVoiceVersion.profile_id.in_(voice_profile_ids),
            )
        ).all()
        if voice_profile_ids
        else []
    )
    identity_version_ids = {version.id for version in identity_versions}
    voice_version_ids = {version.id for version in voice_versions}
    evaluations = db.scalars(
        select(StudioIdentityEvaluation).where(StudioIdentityEvaluation.workspace_id == deletion.workspace_id)
    ).all()
    evaluations = [
        evaluation
        for evaluation in evaluations
        if evaluation.identity_version_id in identity_version_ids
        or evaluation.voice_version_id in voice_version_ids
    ]
    jobs = db.scalars(
        select(StudioGenerationJob).where(StudioGenerationJob.workspace_id == deletion.workspace_id)
    ).all()
    jobs = [
        job
        for job in jobs
        if job.identity_version_id in identity_version_ids or job.voice_version_id in voice_version_ids
    ]
    return (
        identity_profiles,
        voice_profiles,
        identity_versions,
        voice_versions,
        evaluations,
        jobs,
    )


def _fail(
    db: Session,
    deletion: StudioIdentityDeletionRequest,
    *,
    code: str,
    receipt: dict[str, Any],
) -> None:
    deletion.status = "failed"
    deletion.error_message = code
    deletion.execution_receipt = receipt
    db.commit()


def _asset_receipt(
    *,
    asset: LibraryAsset,
    deletion_id: str,
    disposition: str,
    object_was_present: bool,
) -> dict[str, Any]:
    key_digest = hashlib.sha256((asset.storage_key or "").encode()).hexdigest() if asset.storage_key else None
    return {
        "schemaVersion": "studio.asset-deletion-receipt.v1",
        "assetId": asset.id,
        "deletionRequestId": deletion_id,
        "disposition": disposition,
        "objectWasPresent": object_was_present,
        "storageBackend": asset.storage_backend,
        "objectKeySha256": key_digest,
        "deletedAt": datetime.now(UTC).isoformat(),
    }


def _tombstone_asset(asset: LibraryAsset, receipt: dict[str, Any]) -> None:
    deleted_at = datetime.fromisoformat(str(receipt["deletedAt"]))
    asset.lifecycle_status = "deleted"
    asset.deleted_at = deleted_at
    asset.title = "Deleted identity asset"
    asset.tags = []
    asset.campaign_id = None
    asset.content_id = None
    asset.url = None
    asset.storage_key = None
    asset.media_type = None
    asset.size_bytes = None
    asset.checksum_sha256 = None
    asset.object_metadata = {
        "schemaVersion": "studio.asset-tombstone.v1",
        "deletionRequestId": receipt["deletionRequestId"],
    }
    asset.deletion_receipt = receipt


def execute_identity_deletion(
    db: Session,
    deletion_id: str,
    *,
    execution_enabled: bool | None = None,
    storage_factory: Callable[[str | None], ObjectStorage] = get_object_storage,
) -> dict[str, Any]:
    enabled = (
        get_settings().identity_deletion_execution_enabled
        if execution_enabled is None
        else execution_enabled
    )
    if not enabled:
        raise ValueError("identity_deletion_execution_disabled")

    deletion = db.scalar(
        select(StudioIdentityDeletionRequest)
        .where(StudioIdentityDeletionRequest.id == deletion_id)
        .with_for_update()
    )
    if not deletion:
        raise ValueError("identity_deletion_request_not_found")
    if deletion.status == "completed":
        return deletion.execution_receipt

    now = datetime.now(UTC)
    if deletion.status == "running" and deletion.started_at:
        started_at = deletion.started_at
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=UTC)
        if started_at > now - timedelta(minutes=15):
            raise IdentityDeletionDeferred("identity_deletion_already_running")
    previous_receipt = dict(deletion.execution_receipt or {})
    attempt_history = list(previous_receipt.get("attemptHistory") or [])
    if previous_receipt.get("schemaVersion") == "studio.identity-deletion-receipt.v1":
        attempt_history.append(
            {key: value for key, value in previous_receipt.items() if key != "attemptHistory"}
        )
    deletion.status = "running"
    deletion.started_at = now
    deletion.attempt_count += 1
    deletion.error_message = None
    receipt: dict[str, Any] = {
        "schemaVersion": "studio.identity-deletion-receipt.v1",
        "deletionRequestId": deletion.id,
        "workspaceId": deletion.workspace_id,
        "attempt": deletion.attempt_count,
        "startedAt": now.isoformat(),
        "deletedAssets": [],
        "alreadyDeletedAssetIds": [],
        "preservedSourceAssetIds": [],
        "blockedReferences": {},
        "legalHoldAssetIds": [],
        "attemptHistory": attempt_history[-20:],
    }
    deletion.execution_receipt = receipt
    db.commit()

    try:
        (
            identity_profiles,
            voice_profiles,
            identity_versions,
            voice_versions,
            evaluations,
            jobs,
        ) = _resolve_targets(db, deletion)
        if deletion.target_type == "identity_profile" and not identity_profiles:
            raise ValueError("identity_deletion_target_not_found")
        if deletion.target_type == "voice_profile" and not voice_profiles:
            raise ValueError("identity_deletion_target_not_found")
        active_jobs = [job for job in jobs if job.status not in TERMINAL_JOB_STATES]
        if active_jobs:
            for job in active_jobs:
                if job.status == "queued":
                    job.status = "cancelled"
                    job.finished_at = now
                elif job.status != "cancel_requested":
                    job.status = "cancel_requested"
                job.cancel_reason = "identity_deletion_requested"
            deletion.status = "queued"
            deletion.error_message = "identity_deletion_waiting_for_jobs"
            receipt["waitingForJobIds"] = sorted(job.id for job in active_jobs)
            deletion.execution_receipt = receipt
            db.commit()
            raise IdentityDeletionDeferred("identity_deletion_waiting_for_jobs")

        for target in [*identity_profiles, *voice_profiles, *identity_versions, *voice_versions]:
            if target.status != "deleted":
                target.status = "deleting"

        source_ids = {
            asset_id
            for version in [*identity_versions, *voice_versions]
            for asset_id in (version.sample_asset_ids or [])
        }
        derived_ids = {
            artifact.get("id")
            for version in [*identity_versions, *voice_versions]
            for artifact in (version.derived_artifacts or [])
            if isinstance(artifact, dict) and artifact.get("id")
        }
        preview_ids = {
            asset_id
            for evaluation in evaluations
            for asset_id in (evaluation.preview_asset_ids or [])
        }
        derived_and_preview_ids = derived_ids | preview_ids
        preserved_source_ids = source_ids if not deletion.delete_source_samples else set()
        candidate_ids = derived_and_preview_ids | (source_ids if deletion.delete_source_samples else set())
        candidate_ids -= preserved_source_ids
        receipt["preservedSourceAssetIds"] = sorted(preserved_source_ids)

        deletion.deletion_plan = {
            **(deletion.deletion_plan or {}),
            "identityProfileIds": sorted(profile.id for profile in identity_profiles),
            "identityVersionIds": sorted(version.id for version in identity_versions),
            "voiceProfileIds": sorted(profile.id for profile in voice_profiles),
            "voiceVersionIds": sorted(version.id for version in voice_versions),
            "derivedAssetIds": sorted(derived_ids),
            "previewAssetIds": sorted(preview_ids),
            "sourceSampleAssetIds": sorted(source_ids),
            "jobIds": sorted(job.id for job in jobs),
        }
        db.commit()

        assets: dict[str, LibraryAsset] = {}
        for asset_id in sorted(candidate_ids):
            asset = db.get(LibraryAsset, asset_id)
            if not asset:
                receipt["alreadyDeletedAssetIds"].append(asset_id)
                continue
            if asset.workspace_id != deletion.workspace_id:
                receipt["crossWorkspaceAssetIds"] = [asset_id]
                _fail(
                    db,
                    deletion,
                    code="identity_deletion_cross_workspace_asset",
                    receipt=receipt,
                )
                raise ValueError("identity_deletion_cross_workspace_asset")
            if asset.lifecycle_status == "deleted":
                receipt["alreadyDeletedAssetIds"].append(asset_id)
                continue
            assets[asset_id] = asset

        legal_holds = sorted(asset.id for asset in assets.values() if asset.legal_hold)
        if legal_holds:
            receipt["legalHoldAssetIds"] = legal_holds
            _fail(db, deletion, code="identity_deletion_legal_hold", receipt=receipt)
            raise ValueError("identity_deletion_legal_hold")

        references = _collect_external_references(
            db,
            workspace_id=deletion.workspace_id,
            candidate_ids=set(assets),
            identity_version_ids={version.id for version in identity_versions},
            voice_version_ids={version.id for version in voice_versions},
        )
        if references:
            receipt["blockedReferences"] = {
                asset_id: sorted(values)[:100] for asset_id, values in sorted(references.items())
            }
            _fail(db, deletion, code="identity_deletion_shared_reference", receipt=receipt)
            raise ValueError("identity_deletion_shared_reference")

        for asset in assets.values():
            asset.lifecycle_status = "deleting"
        deletion.execution_receipt = receipt
        db.commit()

        for asset_id in sorted(assets):
            asset = db.get(LibraryAsset, asset_id)
            if not asset or asset.lifecycle_status == "deleted":
                if asset_id not in receipt["alreadyDeletedAssetIds"]:
                    receipt["alreadyDeletedAssetIds"].append(asset_id)
                continue
            if asset.legal_hold:
                receipt["legalHoldAssetIds"] = sorted(
                    set(receipt["legalHoldAssetIds"]) | {asset.id}
                )
                _fail(db, deletion, code="identity_deletion_legal_hold", receipt=receipt)
                raise ValueError("identity_deletion_legal_hold")
            object_was_present = False
            if asset.storage_key:
                try:
                    storage = storage_factory(asset.storage_backend or "local")
                    object_was_present = storage.exists(asset.storage_key)
                    if object_was_present:
                        storage.delete(asset.storage_key)
                except Exception as error:
                    raise IdentityDeletionStorageError(
                        f"identity_deletion_storage_error:{type(error).__name__}"
                    ) from error
            asset_receipt = _asset_receipt(
                asset=asset,
                deletion_id=deletion.id,
                disposition="deleted" if object_was_present or asset.url else "already_absent",
                object_was_present=object_was_present,
            )
            _tombstone_asset(asset, asset_receipt)
            receipt["deletedAssets"].append(asset_receipt)
            deletion.execution_receipt = receipt
            db.commit()

        for version in [*identity_versions, *voice_versions]:
            version.status = "deleted"
            version.sample_asset_ids = []
            version.derived_artifacts = []
            version.content_hash = hashlib.sha256(f"deleted:{version.id}".encode()).hexdigest()
            version.review_comment = None
            if isinstance(version, StudioIdentityVersion):
                version.capabilities = []
            else:
                version.pronunciation_profile = {}
        for evaluation in evaluations:
            evaluation.preview_asset_ids = []
            evaluation.notes = None
        for profile in identity_profiles:
            profile.status = "deleted"
            profile.subject_key = f"deleted:{profile.id}"
            profile.display_name = "Deleted identity"
            profile.owner_user_id = None
        for profile in voice_profiles:
            profile.status = "deleted"
            profile.display_name = "Deleted voice"

        completed_at = datetime.now(UTC)
        tombstoned_asset_ids = sorted(
            asset_id
            for asset_id in candidate_ids
            if (asset := db.get(LibraryAsset, asset_id)) and asset.lifecycle_status == "deleted"
        )
        receipt["completedAt"] = completed_at.isoformat()
        receipt["deletedThisAttemptCount"] = len(receipt["deletedAssets"])
        receipt["tombstonedAssetIds"] = tombstoned_asset_ids
        receipt["deletedAssetCount"] = len(tombstoned_asset_ids)
        receipt["preservedSourceAssetCount"] = len(receipt["preservedSourceAssetIds"])
        deletion.status = "completed"
        deletion.completed_at = completed_at
        deletion.error_message = None
        deletion.execution_receipt = receipt
        emit_event(
            db,
            workspace_id=deletion.workspace_id,
            event_type="studio.identity.deletion_completed",
            aggregate_type=deletion.target_type,
            aggregate_id=deletion.identity_profile_id or deletion.voice_profile_id or deletion.id,
            correlation_id=f"identity-deletion:{deletion.id}",
            actor_id=deletion.requested_by,
            payload={
                "deletionRequestId": deletion.id,
                "deletedAssetCount": receipt["deletedAssetCount"],
                "preservedSourceAssetCount": receipt["preservedSourceAssetCount"],
            },
        )
        db.commit()
        return receipt
    except IdentityDeletionDeferred:
        raise
    except Exception as error:
        db.rollback()
        deletion = db.get(StudioIdentityDeletionRequest, deletion_id)
        if deletion and deletion.status not in {"completed", "failed"}:
            deletion.status = "failed"
            deletion.error_message = str(error)[:2000]
            deletion.execution_receipt = receipt
            db.commit()
        raise
