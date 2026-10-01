"""Qualified speech/music absence analysis for one review-pinned render.

The research YAMNet/VAD script is intentionally not registered here. Only a
provider/model pair promoted in the control plane can create production-grade
evidence, and even that evidence cannot admit publication without rights and
human listening bound to the same review snapshot and render bytes.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...config import get_settings
from ...domain.studios.acoustic_qualification import (
    AcousticPromotionReceiptV1,
    contract_digest,
    verify_acoustic_promotion_receipt,
)
from ...domain.studios.contracts import (
    CreateGenerationJobRequest,
    StudioAcousticAnalysisCapabilityV1,
    StudioAcousticAnalysisJobRequestV1,
    StudioAcousticAnalysisRecordV1,
    StudioAcousticDetectorResultV1,
    StudioAssetRightsReviewRecordV1,
    StudioListeningReviewRecordV1,
    StudioNaturalSoundAdmissionRecordV1,
)
from ...domain.studios.providers import ACOUSTIC_ANALYSIS_PROVIDERS
from ...models import (
    StudioDomainEvent,
    StudioGenerationJob,
    StudioModelRegistration,
    StudioProviderRegistration,
    StudioReviewRequest,
    User,
)
from .jobs import create_job
from .kernel import emit_event
from .review_binding import requires_natural_sound_review
from .review_media import verified_review_video_path

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def snapshot_checksum(review: StudioReviewRequest) -> str:
    canonical = json.dumps(review.snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _event_record(db: Session, review: StudioReviewRequest, event_type: str, contract_type):
    events = db.scalars(
        select(StudioDomainEvent)
        .where(
            StudioDomainEvent.workspace_id == review.workspace_id,
            StudioDomainEvent.aggregate_type == "studio_review",
            StudioDomainEvent.aggregate_id == review.id,
            StudioDomainEvent.event_type == event_type,
        )
        .order_by(StudioDomainEvent.occurred_at.desc(), StudioDomainEvent.id.desc())
    ).all()
    for event in events:
        try:
            return contract_type.model_validate(event.payload)
        except ValueError:
            continue
    return None


def acoustic_analysis_out(
    db: Session,
    review: StudioReviewRequest,
) -> StudioAcousticAnalysisRecordV1 | None:
    return _event_record(db, review, "studio.review.acoustic_analyzed", StudioAcousticAnalysisRecordV1)


def natural_sound_admission_out(
    db: Session,
    review: StudioReviewRequest,
) -> StudioNaturalSoundAdmissionRecordV1 | None:
    return _event_record(
        db,
        review,
        "studio.review.natural_sound_admitted",
        StudioNaturalSoundAdmissionRecordV1,
    )


def _listening_out(db: Session, review: StudioReviewRequest) -> StudioListeningReviewRecordV1 | None:
    return _event_record(db, review, "studio.review.listening_recorded", StudioListeningReviewRecordV1)


def _qualified_detector(db: Session):
    settings = get_settings()
    promotion_secret = settings.studio_acoustic_promotion_hmac_secret
    promotion_key_id = settings.studio_acoustic_promotion_key_id
    registrations = db.scalars(
        select(StudioProviderRegistration)
        .where(
            StudioProviderRegistration.capability == "acoustic_analysis",
            StudioProviderRegistration.status == "approved",
        )
        .order_by(StudioProviderRegistration.provider.asc(), StudioProviderRegistration.provider_version.asc())
    ).all()
    if not registrations:
        return None, None, None, "acoustic_detector_not_approved"
    if not promotion_secret or not promotion_key_id:
        return None, None, None, "acoustic_promotion_verifier_unconfigured"
    pending_reason = "acoustic_detector_not_qualified"
    for registration in registrations:
        manifest = registration.manifest or {}
        try:
            receipt = AcousticPromotionReceiptV1.model_validate(manifest.get("acousticPromotionReceipt"))
        except ValueError:
            pending_reason = "acoustic_detector_benchmark_pending"
            continue
        if receipt.signer_key_id != promotion_key_id or not verify_acoustic_promotion_receipt(
            receipt, secret=promotion_secret
        ):
            pending_reason = "acoustic_detector_promotion_receipt_invalid"
            continue
        assessment = receipt.assessment
        benchmark_digest = contract_digest(receipt)
        if assessment.provider != registration.provider or assessment.provider_version != registration.provider_version:
            pending_reason = "acoustic_detector_promotion_binding_invalid"
            continue
        model = db.scalar(
            select(StudioModelRegistration)
            .where(
                StudioModelRegistration.provider_registration_id == registration.id,
                StudioModelRegistration.status == "approved",
            )
            .order_by(StudioModelRegistration.name.asc(), StudioModelRegistration.version.asc())
        )
        if (
            model is None
            or model.commercial_use != "approved"
            or "acoustic_analysis" not in (model.capabilities or [])
            or not SHA256_RE.fullmatch((model.digest_sha256 or "").lower())
        ):
            pending_reason = "acoustic_model_not_approved"
            continue
        if (
            assessment.model_name != model.name
            or assessment.model_version != model.version
            or assessment.model_digest_sha256.lower() != model.digest_sha256.lower()
            or str((model.manifest or {}).get("acousticPromotionReceiptDigestSha256") or "").lower() != benchmark_digest
        ):
            pending_reason = "acoustic_model_promotion_binding_invalid"
            continue
        provider = ACOUSTIC_ANALYSIS_PROVIDERS.get(registration.provider)
        if provider is None or provider.version != registration.provider_version:
            pending_reason = "acoustic_detector_runtime_unavailable"
            continue
        return registration, model, provider, None
    return None, None, None, pending_reason


def acoustic_analysis_capability(db: Session) -> StudioAcousticAnalysisCapabilityV1:
    registration, model, _provider, reason = _qualified_detector(db)
    if registration is None or model is None:
        detail = {
            "acoustic_detector_not_approved": "Nenhum detector de fala e música foi aprovado.",
            "acoustic_promotion_verifier_unconfigured": "O verificador de promoção acústica não foi configurado.",
            "acoustic_detector_benchmark_pending": "O detector ainda não passou pelo benchmark representativo.",
            "acoustic_detector_promotion_receipt_invalid": "O recibo assinado de promoção acústica é inválido.",
            "acoustic_detector_promotion_binding_invalid": "O recibo acústico não corresponde ao provider aprovado.",
            "acoustic_model_not_approved": "O modelo ou sua licença comercial ainda não foram aprovados.",
            "acoustic_model_promotion_binding_invalid": "O recibo acústico não corresponde ao modelo aprovado.",
            "acoustic_detector_runtime_unavailable": "O runtime aprovado não está disponível neste ambiente.",
            "acoustic_detector_not_qualified": "A qualificação acústica ainda está incompleta.",
        }.get(reason or "", "A análise acústica está indisponível.")
        return StudioAcousticAnalysisCapabilityV1(
            status="unavailable",
            reason_code=reason or "acoustic_detector_not_qualified",
            detail=detail,
        )
    return StudioAcousticAnalysisCapabilityV1(
        status="ready",
        reason_code="acoustic_detector_ready",
        detail="Detector qualificado disponível para o MP4 fixado.",
        provider=registration.provider,
        provider_version=registration.provider_version,
        model_name=model.name,
        model_version=model.version,
    )


def create_acoustic_analysis_job(
    db: Session,
    review: StudioReviewRequest,
    user: User,
    *,
    idempotency_key: str,
) -> tuple[StudioGenerationJob, bool]:
    snapshot = review.snapshot
    from ...domain.studios.contracts import CreativeDocumentV1

    if not requires_natural_sound_review(CreativeDocumentV1.model_validate(snapshot)):
        raise ValueError("studio_acoustic_analysis_not_applicable")
    if review.status not in {"requested", "approved"}:
        raise ValueError("studio_acoustic_analysis_review_not_active")
    if not review.render_asset_id or not review.render_checksum_sha256:
        raise ValueError("studio_acoustic_analysis_render_required")
    registration, model, _provider, reason = _qualified_detector(db)
    if registration is None or model is None:
        raise ValueError(reason or "acoustic_detector_not_qualified")
    benchmark_digest = contract_digest(
        AcousticPromotionReceiptV1.model_validate((registration.manifest or {})["acousticPromotionReceipt"])
    )
    request = StudioAcousticAnalysisJobRequestV1(
        review_id=review.id,
        document_id=review.document_id,
        document_version=review.document_version,
        snapshot_checksum_sha256=snapshot_checksum(review),
        render_asset_id=review.render_asset_id,
        render_checksum_sha256=review.render_checksum_sha256.lower(),
    )
    return create_job(
        db,
        CreateGenerationJobRequest(
            workspace_id=review.workspace_id,
            document_id=review.document_id,
            job_type="acoustic_analysis",
            provider=registration.provider,
            request={
                "analysisRequest": request.model_dump(by_alias=True, mode="json"),
                "providerRegistrationId": registration.id,
                "modelRegistrationId": model.id,
                "modelDigestSha256": model.digest_sha256.lower(),
                "benchmarkDigestSha256": benchmark_digest,
            },
            correlation_id=f"acoustic-analysis:{review.id}",
        ),
        idempotency_key,
        user,
    )


def _analysis_status(result: StudioAcousticDetectorResultV1) -> str:
    statuses = {check.status for check in result.checks}
    if "fail" in statuses:
        return "fail"
    if "inconclusive" in statuses:
        return "inconclusive"
    return "pass"


def execute_acoustic_analysis(db: Session, job: StudioGenerationJob, progress, is_cancelled) -> dict:
    if job.job_type != "acoustic_analysis":
        raise ValueError("acoustic_analysis_job_type_required")
    existing = next(
        (
            event
            for event in db.scalars(
                select(StudioDomainEvent).where(
                    StudioDomainEvent.event_type == "studio.review.acoustic_analyzed",
                    StudioDomainEvent.aggregate_type == "studio_review",
                    StudioDomainEvent.aggregate_id == job.request_payload.get("analysisRequest", {}).get("reviewId"),
                    StudioDomainEvent.workspace_id == job.workspace_id,
                )
            ).all()
            if (event.payload or {}).get("jobId") == job.id
        ),
        None,
    )
    if existing:
        return StudioAcousticAnalysisRecordV1.model_validate(existing.payload).model_dump(
            by_alias=True,
            mode="json",
        )
    request = StudioAcousticAnalysisJobRequestV1.model_validate(job.request_payload.get("analysisRequest"))
    review = db.scalar(
        select(StudioReviewRequest).where(
            StudioReviewRequest.id == request.review_id,
            StudioReviewRequest.workspace_id == job.workspace_id,
        )
    )
    if review is None:
        raise ValueError("studio_acoustic_analysis_review_missing")
    if (
        review.document_id != request.document_id
        or review.document_version != request.document_version
        or snapshot_checksum(review) != request.snapshot_checksum_sha256.lower()
        or review.render_asset_id != request.render_asset_id
        or (review.render_checksum_sha256 or "").lower() != request.render_checksum_sha256.lower()
    ):
        raise ValueError("studio_acoustic_analysis_binding_mismatch")
    registration, model, provider, reason = _qualified_detector(db)
    if registration is None or model is None or provider is None:
        raise ValueError(reason or "acoustic_detector_not_qualified")
    if (
        registration.id != job.request_payload.get("providerRegistrationId")
        or model.id != job.request_payload.get("modelRegistrationId")
        or model.digest_sha256.lower() != str(job.request_payload.get("modelDigestSha256") or "").lower()
        or contract_digest(
            AcousticPromotionReceiptV1.model_validate((registration.manifest or {}).get("acousticPromotionReceipt"))
        )
        != str(job.request_payload.get("benchmarkDigestSha256") or "").lower()
        or provider.name != job.provider
    ):
        raise ValueError("studio_acoustic_analysis_promotion_changed")
    if is_cancelled():
        return {"cancelled": True}
    progress(10)
    with verified_review_video_path(db, review) as (path, _extension):
        result = provider.analyze(path, request, progress, is_cancelled)
    if is_cancelled():
        return {"cancelled": True}
    if (
        result.provider != provider.name
        or result.provider_version != provider.version
        or result.source_checksum_sha256.lower() != request.render_checksum_sha256.lower()
    ):
        raise ValueError("studio_acoustic_analysis_result_binding_mismatch")
    analyzed_at = datetime.now(UTC)
    event = emit_event(
        db,
        workspace_id=review.workspace_id,
        event_type="studio.review.acoustic_analyzed",
        aggregate_type="studio_review",
        aggregate_id=review.id,
        correlation_id=job.correlation_id,
        actor_id=None,
        payload={},
    )
    db.flush()
    record = StudioAcousticAnalysisRecordV1(
        analysis_id=event.id,
        job_id=job.id,
        review_id=review.id,
        workspace_id=review.workspace_id,
        document_id=review.document_id,
        document_version=review.document_version,
        snapshot_checksum_sha256=request.snapshot_checksum_sha256,
        render_asset_id=request.render_asset_id,
        render_checksum_sha256=request.render_checksum_sha256,
        provider_registration_id=registration.id,
        model_registration_id=model.id,
        model_digest_sha256=model.digest_sha256.lower(),
        benchmark_digest_sha256=contract_digest(
            AcousticPromotionReceiptV1.model_validate((registration.manifest or {})["acousticPromotionReceipt"])
        ),
        result=result,
        status=_analysis_status(result),
        analyzed_at=analyzed_at,
    )
    event.payload = record.model_dump(by_alias=True, mode="json")
    db.flush()
    try_admit_natural_sound_review(db, review)
    progress(99)
    return record.model_dump(by_alias=True, mode="json")


def try_admit_natural_sound_review(
    db: Session,
    review: StudioReviewRequest,
) -> StudioNaturalSoundAdmissionRecordV1 | None:
    existing = natural_sound_admission_out(db, review)
    if existing is not None:
        return existing
    if review.status != "approved" or not review.render_asset_id or not review.render_checksum_sha256:
        return None
    listening = _listening_out(db, review)
    analysis = acoustic_analysis_out(db, review)
    if (
        listening is None
        or listening.result != "pass"
        or analysis is None
        or analysis.status != "pass"
        or not analysis.production_qualified
        or listening.submission.render_asset_id != review.render_asset_id
        or listening.submission.render_checksum_sha256.lower() != review.render_checksum_sha256.lower()
        or analysis.render_asset_id != review.render_asset_id
        or analysis.render_checksum_sha256.lower() != review.render_checksum_sha256.lower()
        or listening.snapshot_checksum_sha256 != snapshot_checksum(review)
        or analysis.snapshot_checksum_sha256 != snapshot_checksum(review)
    ):
        return None
    rights_review_ids: list[str] = []
    now = datetime.now(UTC)
    for reference in review.snapshot.get("assets", []):
        provenance = reference.get("provenance") or {}
        if provenance.get("purpose") != "natural-sound-candidate":
            continue
        review_id = provenance.get("rightsReviewId")
        if reference.get("rightsStatus") != "verified" or not isinstance(review_id, str) or not review_id:
            return None
        rights_event = db.scalar(
            select(StudioDomainEvent).where(
                StudioDomainEvent.id == review_id,
                StudioDomainEvent.workspace_id == review.workspace_id,
                StudioDomainEvent.event_type == "studio.asset.rights_reviewed",
                StudioDomainEvent.aggregate_type == "studio_asset",
                StudioDomainEvent.aggregate_id == reference.get("id"),
            )
        )
        try:
            rights = StudioAssetRightsReviewRecordV1.model_validate(
                (rights_event.payload or {}).get("record") if rights_event else None,
            )
        except ValueError:
            return None
        if (
            rights.decision != "verified"
            or rights.asset_checksum_sha256.lower() != str(reference.get("checksum") or "").lower()
            or rights.source_declaration != str(provenance.get("sourceDeclaration") or "")
            or rights.license_declaration != str(provenance.get("licenseDeclaration") or "")
            or (rights.expires_at is not None and rights.expires_at <= now)
        ):
            return None
        rights_review_ids.append(review_id)
    if not rights_review_ids:
        return None
    with verified_review_video_path(db, review):
        pass
    event = emit_event(
        db,
        workspace_id=review.workspace_id,
        event_type="studio.review.natural_sound_admitted",
        aggregate_type="studio_review",
        aggregate_id=review.id,
        correlation_id=f"natural-sound-admission:{review.id}",
        actor_id=None,
        payload={},
    )
    db.flush()
    record = StudioNaturalSoundAdmissionRecordV1(
        admission_id=event.id,
        review_id=review.id,
        document_id=review.document_id,
        document_version=review.document_version,
        snapshot_checksum_sha256=snapshot_checksum(review),
        render_asset_id=review.render_asset_id,
        render_checksum_sha256=review.render_checksum_sha256.lower(),
        acoustic_analysis_id=analysis.analysis_id,
        listening_assessment_id=listening.assessment_id,
        rights_review_ids=sorted(set(rights_review_ids)),
        admitted_at=datetime.now(UTC),
    )
    event.payload = record.model_dump(by_alias=True, mode="json")
    db.flush()
    return record


def require_current_natural_sound_admission(
    db: Session,
    review: StudioReviewRequest,
) -> StudioNaturalSoundAdmissionRecordV1:
    """Revalidate revocable evidence without rerunning the detector."""
    admission = natural_sound_admission_out(db, review)
    analysis = acoustic_analysis_out(db, review)
    listening = _listening_out(db, review)
    expected_snapshot = snapshot_checksum(review)
    if (
        admission is None
        or analysis is None
        or listening is None
        or admission.review_id != review.id
        or admission.document_id != review.document_id
        or admission.document_version != review.document_version
        or admission.snapshot_checksum_sha256 != expected_snapshot
        or admission.render_asset_id != review.render_asset_id
        or admission.render_checksum_sha256.lower() != (review.render_checksum_sha256 or "").lower()
        or admission.acoustic_analysis_id != analysis.analysis_id
        or admission.listening_assessment_id != listening.assessment_id
        or analysis.status != "pass"
        or listening.result != "pass"
    ):
        raise ValueError("studio_publication_natural_sound_evidence_pending")
    registration = db.get(StudioProviderRegistration, analysis.provider_registration_id)
    model = db.get(StudioModelRegistration, analysis.model_registration_id)
    qualified_registration, qualified_model, _provider, _reason = _qualified_detector(db)
    if (
        registration is None
        or registration.status != "approved"
        or model is None
        or model.status != "approved"
        or model.commercial_use != "approved"
        or model.digest_sha256.lower() != analysis.model_digest_sha256
        or "acoustic_analysis" not in (model.capabilities or [])
        or qualified_registration is None
        or qualified_model is None
        or qualified_registration.id != registration.id
        or qualified_model.id != model.id
        or contract_digest(
            AcousticPromotionReceiptV1.model_validate((registration.manifest or {}).get("acousticPromotionReceipt"))
        )
        != analysis.benchmark_digest_sha256
    ):
        raise ValueError("studio_publication_acoustic_promotion_revoked")
    current_rights: list[str] = []
    now = datetime.now(UTC)
    for reference in review.snapshot.get("assets", []):
        provenance = reference.get("provenance") or {}
        if provenance.get("purpose") != "natural-sound-candidate":
            continue
        rights_id = provenance.get("rightsReviewId")
        rights_event = db.scalar(
            select(StudioDomainEvent).where(
                StudioDomainEvent.id == rights_id,
                StudioDomainEvent.workspace_id == review.workspace_id,
                StudioDomainEvent.event_type == "studio.asset.rights_reviewed",
                StudioDomainEvent.aggregate_type == "studio_asset",
                StudioDomainEvent.aggregate_id == reference.get("id"),
            )
        )
        try:
            rights = StudioAssetRightsReviewRecordV1.model_validate(
                (rights_event.payload or {}).get("record") if rights_event else None,
            )
        except ValueError as error:
            raise ValueError("studio_publication_natural_sound_rights_changed") from error
        if (
            rights.decision != "verified"
            or rights.asset_checksum_sha256.lower() != str(reference.get("checksum") or "").lower()
            or rights.source_declaration != str(provenance.get("sourceDeclaration") or "")
            or rights.license_declaration != str(provenance.get("licenseDeclaration") or "")
            or (rights.expires_at is not None and rights.expires_at <= now)
        ):
            raise ValueError("studio_publication_natural_sound_rights_changed")
        current_rights.append(rights.review_id)
    if sorted(set(current_rights)) != sorted(admission.rights_review_ids):
        raise ValueError("studio_publication_natural_sound_rights_changed")
    return admission
