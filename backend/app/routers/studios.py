from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import FileResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..domain.studios.advanced_capabilities import AdvancedCapabilityAuditV1
from ..domain.studios.assisted_intelligence import AssistedIntelligenceSuiteEvidenceV1
from ..domain.studios.autonomy_completion import VideoAutonomyCompletionAuditV1
from ..domain.studios.contextual_editing import (
    ContextualEditPlanV1,
    ContextualPlanRequestV1,
    EditingApplyRequestV1,
    EditingChoiceRequestV1,
    EditingFeedbackRequestV1,
    EditingObservationV1,
)
from ..domain.studios.contextual_editing_v2 import (
    ContextualEditPlanV2,
    ContextualPlanRecompileRequestV1,
    ContextualPlanRequestV2,
    EditorialMaterialChoiceV2,
)
from ..domain.studios.contracts import (
    ApplyEditDecisionSetRequest,
    ApplyTranscriptCaptionsRequest,
    CancelGenerationJobRequest,
    ConsentGrantV1,
    CreateAudioWaveformRequest,
    CreateConsentGrantRequest,
    CreateEditDecisionSetRequest,
    CreateGenerationJobRequest,
    CreateIdentityDeletionRequest,
    CreateIdentityEvaluationRequest,
    CreateIdentityProfileRequest,
    CreateIdentityVersionRequest,
    CreateMediaIngestRequest,
    CreateMediaProxyRequest,
    CreateModelRegistrationRequest,
    CreateProviderRegistrationRequest,
    CreateStudioDocumentRequest,
    CreateStudioReviewRequest,
    CreateTranscriptRequest,
    CreateVideoRenderJobRequest,
    CreateVoiceProfileRequest,
    CreateVoiceVersionRequest,
    CreativeDocumentV1,
    EditDecisionSetV1,
    GenerationJobV1,
    IdentityDeletionRequestV1,
    IdentityEvaluationV1,
    IdentityProfileV1,
    IdentityVersionV1,
    MediaIngestV1,
    ModelRegistrationV1,
    ProviderRegistrationV1,
    ReplaceEditDecisionSetRequest,
    ReplaceStudioDocumentRequest,
    ReplaceTranscriptRequest,
    RestoreStudioDocumentVersionRequest,
    ReviewIdentityVersionRequest,
    RevokeConsentGrantRequest,
    StudioAcousticAnalysisCapabilityV1,
    StudioAssetRightsReviewRequestV1,
    StudioAssetRightsReviewResponseV1,
    StudioCapabilitiesV1,
    StudioDocumentVersionV1,
    StudioExportRequest,
    StudioInternalScheduleReceiptV1,
    StudioInternalScheduleRequest,
    StudioPublicationPreflightV1,
    StudioReviewDecisionRequest,
    StudioReviewRequestV1,
    TranscriptDocumentV1,
    VoiceProfileV1,
    VoiceVersionV1,
)
from ..domain.studios.creative_autonomy import (
    CreativePilotCasebookV1,
    evaluate_preproduction_gate,
)
from ..domain.studios.creative_replan import CreativeReplanStateV1
from ..domain.studios.hybrid_video import (
    HybridCapabilityManifestV1,
    HybridSelectionEnvelopeV1,
    HybridSelectionResultV1,
    select_hybrid_profile,
)
from ..domain.studios.editorial_review import (
    EditorialPlanRequestV1,
    EditorialPlanV1,
    EditorialReadinessV1,
    EditorialReviewRequestV1,
    EditorialReviewV1,
)
from ..domain.studios.motion import (
    CreateMotionGraphRequestV1,
    MotionGraphProjectionV1,
    MotionGraphRecordV1,
    ReplaceMotionGraphRequestV1,
    ReviewMotionGraphRequestV1,
    project_motion_graph,
)
from ..domain.studios.scene_generation import (
    SceneGenerationAdmissionRequestV1,
    SceneGenerationCapabilityV1,
    SceneGenerationRequestV1,
    SceneGenerationRequestV2,
)
from ..domain.studios.video_factory import VideoFactoryProgramEvidenceV1
from ..models import (
    BrandProfile,
    Campaign,
    CreativeDocument,
    LibraryAsset,
    Membership,
    Opportunity,
    Post,
    StudioConsentGrant,
    StudioEditDecisionSet,
    StudioGenerationJob,
    StudioIdentityDeletionRequest,
    StudioIdentityEvaluation,
    StudioIdentityProfile,
    StudioIdentityVersion,
    StudioMediaIngest,
    StudioModelRegistration,
    StudioMotionGraph,
    StudioProviderRegistration,
    StudioReviewRequest,
    StudioTranscript,
    StudioVoiceProfile,
    StudioVoiceVersion,
    User,
    Workspace,
)
from ..schemas import AssetOut, CreativeVersionIn
from ..security import get_current_user
from ..services.brand import brand_readiness
from ..services.studios import contextual_editing as contextual_edits
from ..services.studios import contextual_editing_v2, editing_repertoire
from ..services.studios.acoustic_analysis import (
    acoustic_analysis_capability,
    create_acoustic_analysis_job,
)
from ..services.studios.asset_rights import review_natural_sound_rights
from ..services.studios.compatibility import record_to_contract
from ..services.studios.editorial_review import (
    editorial_readiness,
    register_editorial_plan,
    submit_editorial_review,
)
from ..services.studios.exports import export_document
from ..services.studios.identity import (
    consent_out,
    consent_status,
    create_consent_grant,
    create_identity_evaluation,
    create_identity_profile,
    create_identity_version,
    create_voice_profile,
    create_voice_version,
    identity_deletion_out,
    identity_evaluation_out,
    identity_profile_out,
    identity_version_out,
    request_identity_deletion,
    require_active_version_consent,
    review_identity_version,
    revoke_consent_grant,
    voice_profile_out,
    voice_version_out,
)
from ..services.studios.identity_deletion import (
    queue_identity_deletion,
    record_identity_deletion_queue_failure,
)
from ..services.studios.jobs import create_job, enqueue_job_task, job_out, request_cancel, retry_job
from ..services.studios.kernel import (
    create_document,
    emit_event,
    replace_document,
    restore_document_version,
    save_version,
    version_history,
)
from ..services.studios.media_ingest import create_media_ingest, media_ingest_out
from ..services.studios.media_proxy import create_media_proxy_job
from ..services.studios.media_waveform import create_media_waveform_job
from ..services.studios.motion_graphs import (
    create_motion_graph,
    list_motion_graphs,
    motion_graph_out,
    replace_motion_graph,
    review_motion_graph,
)
from ..services.studios.publication import publication_package, publication_preflight, schedule_publication
from ..services.studios.readiness import studio_capabilities
from ..services.studios.registry import (
    approve_model,
    approve_provider,
    model_registration_out,
    provider_registration_out,
    register_model,
    register_provider,
)
from ..services.studios.review_preview import render_review_page
from ..services.studios.reviews import decide_review, request_review, review_out
from ..services.studios.scene_generation import (
    create_scene_generation_job,
    review_scene_candidate,
    scene_generation_capability,
)
from ..services.studios.transcripts import (
    apply_edit_decisions,
    apply_transcript_captions,
    create_decision_set,
    create_transcript,
    decision_set_out,
    replace_decision_set,
    replace_transcript,
    transcript_out,
)
from ..services.studios.video_render import create_video_render_job
from .assets import asset_out

router = APIRouter(prefix="/studios/v1", tags=["studios-v1"])

_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
_CREATIVE_CASEBOOK_PATH = (
    _REPOSITORY_ROOT / "benchmarks" / "studios" / "creative" / "video-creative-pilot-casebook.v1.json"
)
_ASSISTED_INTELLIGENCE_PATH = (
    _REPOSITORY_ROOT
    / "artifacts"
    / "validation"
    / "video-creative-pilot"
    / "assisted-intelligence-20260901-v1"
    / "manifest.json"
)
_VIDEO_FACTORY_PROGRAM_PATH = (
    _REPOSITORY_ROOT
    / "artifacts"
    / "validation"
    / "video-creative-pilot"
    / "factory-20260901-v1"
    / "current-program-manifest.json"
)
_ADVANCED_CAPABILITY_AUDIT_PATH = (
    _REPOSITORY_ROOT
    / "artifacts"
    / "validation"
    / "video-creative-pilot"
    / "advanced-capabilities-20260901-v1"
    / "audit.json"
)
_VIDEO_AUTONOMY_AUDIT_PATH = (
    _REPOSITORY_ROOT / "artifacts" / "validation" / "video-creative-pilot" / "program-audit-20260901-v1" / "audit.json"
)
_CREATIVE_REPLAN_STATE_PATH = (
    _REPOSITORY_ROOT
    / "artifacts"
    / "validation"
    / "video-creative-pilot"
    / "factory-20260901-v1"
    / "creative-replan-state-20260901-v2.json"
)


def creative_casebook() -> CreativePilotCasebookV1:
    try:
        return CreativePilotCasebookV1.model_validate_json(_CREATIVE_CASEBOOK_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise HTTPException(
            status_code=503,
            detail={"code": "creative_casebook_unavailable"},
        ) from error


def assisted_intelligence_suite() -> AssistedIntelligenceSuiteEvidenceV1:
    try:
        return AssistedIntelligenceSuiteEvidenceV1.model_validate_json(
            _ASSISTED_INTELLIGENCE_PATH.read_text(encoding="utf-8")
        )
    except (OSError, ValueError) as error:
        raise HTTPException(
            status_code=503,
            detail={"code": "assisted_intelligence_suite_unavailable"},
        ) from error


def video_factory_program() -> VideoFactoryProgramEvidenceV1:
    try:
        return VideoFactoryProgramEvidenceV1.model_validate_json(
            _VIDEO_FACTORY_PROGRAM_PATH.read_text(encoding="utf-8")
        )
    except (OSError, ValueError) as error:
        raise HTTPException(
            status_code=503,
            detail={"code": "video_factory_program_unavailable"},
        ) from error


def advanced_capability_audit() -> AdvancedCapabilityAuditV1:
    try:
        return AdvancedCapabilityAuditV1.model_validate_json(
            _ADVANCED_CAPABILITY_AUDIT_PATH.read_text(encoding="utf-8")
        )
    except (OSError, ValueError) as error:
        raise HTTPException(
            status_code=503,
            detail={"code": "advanced_capability_audit_unavailable"},
        ) from error


def video_autonomy_audit() -> VideoAutonomyCompletionAuditV1:
    try:
        return VideoAutonomyCompletionAuditV1.model_validate_json(
            _VIDEO_AUTONOMY_AUDIT_PATH.read_text(encoding="utf-8")
        )
    except (OSError, ValueError) as error:
        raise HTTPException(
            status_code=503,
            detail={"code": "video_autonomy_audit_unavailable"},
        ) from error


def creative_replan_state() -> CreativeReplanStateV1:
    try:
        return CreativeReplanStateV1.model_validate_json(_CREATIVE_REPLAN_STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise HTTPException(
            status_code=503,
            detail={"code": "creative_replan_state_unavailable"},
        ) from error


@router.get("/creative/casebook", response_model=CreativePilotCasebookV1)
def get_creative_casebook(
    _user: User = Depends(get_current_user),
) -> CreativePilotCasebookV1:
    """Expose the governed, read-only preproduction corpus to Studio surfaces."""

    return creative_casebook()


@router.get(
    "/creative/assisted-intelligence",
    response_model=AssistedIntelligenceSuiteEvidenceV1,
)
def get_assisted_intelligence_suite(
    _user: User = Depends(get_current_user),
) -> AssistedIntelligenceSuiteEvidenceV1:
    """Expose localized suggestions and their reversible human decisions."""

    return assisted_intelligence_suite()


@router.get(
    "/creative/factory-program",
    response_model=VideoFactoryProgramEvidenceV1,
)
def get_video_factory_program(
    _user: User = Depends(get_current_user),
) -> VideoFactoryProgramEvidenceV1:
    """Expose private production receipts without implying human approval."""

    return video_factory_program()


@router.get(
    "/creative/replan-state",
    response_model=CreativeReplanStateV1,
)
def get_creative_replan_state(
    _user: User = Depends(get_current_user),
) -> CreativeReplanStateV1:
    """Expose the fail-closed golden-first restart gate."""

    return creative_replan_state()


@router.get(
    "/creative/advanced-capabilities",
    response_model=AdvancedCapabilityAuditV1,
)
def get_advanced_capability_audit(
    _user: User = Depends(get_current_user),
) -> AdvancedCapabilityAuditV1:
    """Expose why voice/avatar providers remain disabled."""

    return advanced_capability_audit()


@router.get(
    "/creative/autonomy-audit",
    response_model=VideoAutonomyCompletionAuditV1,
)
def get_video_autonomy_audit(
    _user: User = Depends(get_current_user),
) -> VideoAutonomyCompletionAuditV1:
    """Expose implementation versus operational completion without conflation."""

    return video_autonomy_audit()


@router.get("/creative/cases/{case_id}/animatic", response_class=FileResponse)
def get_creative_case_animatic(
    case_id: str,
    _user: User = Depends(get_current_user),
) -> FileResponse:
    case = next((item for item in creative_casebook().cases if item.case_id == case_id), None)
    if not case or case.animatic.status not in {"rendered", "human_approved"}:
        raise HTTPException(status_code=404, detail={"code": "animatic_not_found"})
    assert case.animatic.render_asset_path and case.animatic.render_digest_sha256
    path = (_REPOSITORY_ROOT / case.animatic.render_asset_path).resolve()
    if not path.is_relative_to(_REPOSITORY_ROOT) or not path.is_file():
        raise HTTPException(status_code=404, detail={"code": "animatic_not_found"})
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != case.animatic.render_digest_sha256.lower():
        raise HTTPException(status_code=409, detail={"code": "animatic_digest_mismatch"})
    return FileResponse(
        path,
        media_type="video/mp4",
        filename=f"{case.case_id}-animatic.mp4",
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
            "X-Clicko-Placeholder": "true",
            "X-Clicko-Publication-Authorized": "false",
        },
    )


def assert_access(db: Session, user_id: str, workspace_id: str) -> None:
    if not db.scalar(
        select(Membership.id).where(Membership.user_id == user_id, Membership.workspace_id == workspace_id)
    ):
        raise HTTPException(status_code=404, detail="Workspace not found")


def assert_governance_access(db: Session, user_id: str, workspace_id: str) -> None:
    membership = db.scalar(
        select(Membership).where(Membership.user_id == user_id, Membership.workspace_id == workspace_id)
    )
    if not membership:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if membership.role.lower() not in {"owner", "admin"}:
        raise HTTPException(status_code=403, detail={"code": "identity_governance_role_required"})


@router.get("/capabilities", response_model=StudioCapabilitiesV1)
def get_studio_capabilities(
    workspace_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StudioCapabilitiesV1:
    """Return the explainable, read-only activation projection for one workspace."""

    assert_access(db, user.id, workspace_id)
    return studio_capabilities(db, workspace_id)


@router.get("/providers", response_model=list[ProviderRegistrationV1])
def list_studio_providers(
    workspace_id: str,
    capability: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ProviderRegistrationV1]:
    assert_access(db, user.id, workspace_id)
    query = select(StudioProviderRegistration)
    if capability:
        query = query.where(StudioProviderRegistration.capability == capability)
    records = db.scalars(query.order_by(StudioProviderRegistration.created_at.desc())).all()
    return [provider_registration_out(item) for item in records]


@router.post("/providers", response_model=ProviderRegistrationV1, status_code=status.HTTP_201_CREATED)
def create_studio_provider(
    request: CreateProviderRegistrationRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ProviderRegistrationV1:
    assert_governance_access(db, user.id, request.workspace_id)
    registration = register_provider(
        db,
        capability=request.capability,
        provider=request.provider,
        provider_version=request.provider_version,
        source_url=request.source_url,
        source_revision=request.source_revision,
        code_license=request.code_license,
        risk_class=request.risk_class,
        manifest=request.manifest,
    )
    emit_event(
        db,
        workspace_id=request.workspace_id,
        event_type="studio.provider.registered",
        aggregate_type="provider_registration",
        aggregate_id=registration.id,
        correlation_id=f"provider:{registration.id}",
        actor_id=user.id,
        payload={"capability": registration.capability, "status": registration.status},
    )
    db.commit()
    return provider_registration_out(registration)


@router.post("/providers/{provider_id}/approve", response_model=ProviderRegistrationV1)
def approve_studio_provider(
    provider_id: str,
    workspace_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ProviderRegistrationV1:
    assert_governance_access(db, user.id, workspace_id)
    registration = db.get(StudioProviderRegistration, provider_id)
    if not registration:
        raise HTTPException(status_code=404, detail="Provider registration not found")
    try:
        approved = approve_provider(db, registration, user=user)
        emit_event(
            db,
            workspace_id=workspace_id,
            event_type="studio.provider.approved",
            aggregate_type="provider_registration",
            aggregate_id=approved.id,
            correlation_id=f"provider:{approved.id}",
            actor_id=user.id,
            payload={"provider": approved.provider, "providerVersion": approved.provider_version},
        )
        db.commit()
        return provider_registration_out(approved)
    except ValueError as error:
        raise HTTPException(status_code=422, detail={"code": str(error)}) from error


@router.get("/models", response_model=list[ModelRegistrationV1])
def list_studio_models(
    workspace_id: str,
    provider_registration_id: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ModelRegistrationV1]:
    assert_access(db, user.id, workspace_id)
    query = select(StudioModelRegistration)
    if provider_registration_id:
        query = query.where(StudioModelRegistration.provider_registration_id == provider_registration_id)
    records = db.scalars(query.order_by(StudioModelRegistration.created_at.desc())).all()
    return [model_registration_out(item) for item in records]


@router.post("/models", response_model=ModelRegistrationV1, status_code=status.HTTP_201_CREATED)
def create_studio_model(
    request: CreateModelRegistrationRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ModelRegistrationV1:
    assert_governance_access(db, user.id, request.workspace_id)
    provider = db.get(StudioProviderRegistration, request.provider_registration_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider registration not found")
    registration = register_model(
        db,
        provider_registration=provider,
        name=request.name,
        version=request.version,
        digest_sha256=request.digest_sha256,
        model_license=request.model_license,
        commercial_use=request.commercial_use,
        languages=request.languages,
        capabilities=request.capabilities,
        manifest=request.manifest,
    )
    emit_event(
        db,
        workspace_id=request.workspace_id,
        event_type="studio.model.registered",
        aggregate_type="model_registration",
        aggregate_id=registration.id,
        correlation_id=f"model:{registration.id}",
        actor_id=user.id,
        payload={"providerRegistrationId": registration.provider_registration_id, "status": registration.status},
    )
    db.commit()
    return model_registration_out(registration)


@router.post("/models/{model_id}/approve", response_model=ModelRegistrationV1)
def approve_studio_model(
    model_id: str,
    workspace_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ModelRegistrationV1:
    assert_governance_access(db, user.id, workspace_id)
    registration = db.get(StudioModelRegistration, model_id)
    if not registration:
        raise HTTPException(status_code=404, detail="Model registration not found")
    try:
        approved = approve_model(db, registration, user=user)
        emit_event(
            db,
            workspace_id=workspace_id,
            event_type="studio.model.approved",
            aggregate_type="model_registration",
            aggregate_id=approved.id,
            correlation_id=f"model:{approved.id}",
            actor_id=user.id,
            payload={"name": approved.name, "version": approved.version},
        )
        db.commit()
        return model_registration_out(approved)
    except ValueError as error:
        raise HTTPException(status_code=422, detail={"code": str(error)}) from error


def validate_references(
    db: Session,
    workspace_id: str,
    *,
    campaign_id: str | None = None,
    post_id: str | None = None,
    opportunity_id: str | None = None,
    asset_ids: list[str] | None = None,
) -> None:
    checks = (
        (Campaign, campaign_id, "Campaign"),
        (Post, post_id, "Post"),
        (Opportunity, opportunity_id, "Opportunity"),
    )
    for model, identifier, label in checks:
        linked = identifier and db.scalar(
            select(model.id).where(model.id == identifier, model.workspace_id == workspace_id)
        )
        if identifier and not linked:
            raise HTTPException(status_code=422, detail=f"{label} does not belong to workspace")
    if asset_ids:
        count = len(
            db.scalars(
                select(LibraryAsset.id).where(
                    LibraryAsset.id.in_(set(asset_ids)),
                    LibraryAsset.workspace_id == workspace_id,
                    LibraryAsset.lifecycle_status == "active",
                )
            ).all()
        )
        if count != len(set(asset_ids)):
            raise HTTPException(status_code=422, detail="Asset does not belong to workspace")
    if not db.scalar(select(BrandProfile.id).where(BrandProfile.workspace_id == workspace_id)):
        raise HTTPException(status_code=422, detail="Brand memory is required")


def validate_private_preview_assets(db: Session, workspace_id: str, asset_ids: list[str]) -> None:
    if not asset_ids:
        return
    stored_ids = set(
        db.scalars(
            select(LibraryAsset.id).where(
                LibraryAsset.id.in_(set(asset_ids)),
                LibraryAsset.workspace_id == workspace_id,
                LibraryAsset.lifecycle_status == "active",
                LibraryAsset.storage_key.is_not(None),
            )
        ).all()
    )
    if stored_ids != set(asset_ids):
        raise HTTPException(status_code=422, detail={"code": "private_preview_asset_required"})


def owned_document(db: Session, user_id: str, document_id: str) -> CreativeDocument:
    record = db.get(CreativeDocument, document_id)
    if not record:
        raise HTTPException(status_code=404, detail="Studio document not found")
    assert_access(db, user_id, record.workspace_id)
    return record


def owned_job(db: Session, user_id: str, job_id: str) -> StudioGenerationJob:
    job = db.get(StudioGenerationJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Studio job not found")
    assert_access(db, user_id, job.workspace_id)
    return job


def owned_media_ingest(db: Session, user_id: str, ingest_id: str) -> StudioMediaIngest:
    ingest = db.get(StudioMediaIngest, ingest_id)
    if not ingest:
        raise HTTPException(status_code=404, detail="Media ingest not found")
    assert_access(db, user_id, ingest.workspace_id)
    return ingest


def owned_transcript(db: Session, user_id: str, transcript_id: str) -> StudioTranscript:
    transcript = db.get(StudioTranscript, transcript_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")
    assert_access(db, user_id, transcript.workspace_id)
    return transcript


def owned_decision_set(db: Session, user_id: str, decision_set_id: str) -> StudioEditDecisionSet:
    decision_set = db.get(StudioEditDecisionSet, decision_set_id)
    if not decision_set:
        raise HTTPException(status_code=404, detail="Edit decision set not found")
    assert_access(db, user_id, decision_set.workspace_id)
    return decision_set


def owned_motion_graph(db: Session, user_id: str, graph_id: str) -> StudioMotionGraph:
    graph = db.get(StudioMotionGraph, graph_id)
    if not graph:
        raise HTTPException(status_code=404, detail="Motion graph not found")
    assert_access(db, user_id, graph.workspace_id)
    return graph


def owned_consent(db: Session, user_id: str, consent_id: str) -> StudioConsentGrant:
    grant = db.get(StudioConsentGrant, consent_id)
    if not grant:
        raise HTTPException(status_code=404, detail="Consent grant not found")
    assert_access(db, user_id, grant.workspace_id)
    return grant


def owned_identity(db: Session, user_id: str, profile_id: str) -> StudioIdentityProfile:
    profile = db.get(StudioIdentityProfile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Identity profile not found")
    assert_access(db, user_id, profile.workspace_id)
    return profile


def owned_voice(db: Session, user_id: str, profile_id: str) -> StudioVoiceProfile:
    profile = db.get(StudioVoiceProfile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Voice profile not found")
    assert_access(db, user_id, profile.workspace_id)
    return profile


def owned_identity_version(db: Session, profile: StudioIdentityProfile, version_id: str) -> StudioIdentityVersion:
    version = db.scalar(
        select(StudioIdentityVersion).where(
            StudioIdentityVersion.id == version_id,
            StudioIdentityVersion.profile_id == profile.id,
            StudioIdentityVersion.workspace_id == profile.workspace_id,
        )
    )
    if not version:
        raise HTTPException(status_code=404, detail="Identity version not found")
    return version


def owned_voice_version(db: Session, profile: StudioVoiceProfile, version_id: str) -> StudioVoiceVersion:
    version = db.scalar(
        select(StudioVoiceVersion).where(
            StudioVoiceVersion.id == version_id,
            StudioVoiceVersion.profile_id == profile.id,
            StudioVoiceVersion.workspace_id == profile.workspace_id,
        )
    )
    if not version:
        raise HTTPException(status_code=404, detail="Voice version not found")
    return version


def studio_identity_error(error: ValueError) -> HTTPException:
    code = str(error)
    conflict_codes = {
        "identity_subject_already_exists",
        "idempotency_payload_conflict",
        "studio_document_conflict",
        "studio_edit_decision_conflict",
        "studio_transcript_conflict",
        "studio_review_render_conflict",
        "motion_graph_conflict",
        "motion_graph_idempotency_conflict",
        "motion_graph_identity_conflict",
    }
    return HTTPException(status_code=409 if code in conflict_codes else 422, detail={"code": code})


def maybe_enqueue_identity_deletion(db: Session, deletion: StudioIdentityDeletionRequest) -> None:
    settings = get_settings()
    if not settings.identity_deletion_execution_enabled:
        return
    if not queue_identity_deletion(db, deletion):
        return
    from ..tasks import execute_identity_deletion_task

    try:
        if settings.studio_isolated_queues_enabled:
            execute_identity_deletion_task.apply_async(args=[deletion.id], queue="studio.control")
        else:
            execute_identity_deletion_task.delay(deletion.id)
    except Exception as error:
        record_identity_deletion_queue_failure(db, deletion, error)


@router.post("/documents", response_model=CreativeDocumentV1, status_code=status.HTTP_201_CREATED)
def create_studio_document(
    request: CreateStudioDocumentRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CreativeDocumentV1:
    assert_access(db, user.id, request.workspace_id)
    validate_references(
        db,
        request.workspace_id,
        campaign_id=request.campaign_id,
        post_id=request.post_id,
        opportunity_id=request.opportunity_id,
        asset_ids=[asset.id for asset in request.assets],
    )
    try:
        return record_to_contract(create_document(db, request, user))
    except ValueError as error:
        if str(error) == "studio_brand_revision_mismatch":
            brand = db.scalar(select(BrandProfile).where(BrandProfile.workspace_id == request.workspace_id))
            revision = brand_readiness(brand)["revision"] if brand else None
            raise HTTPException(
                status_code=409,
                detail={"code": str(error), "currentBrandRevision": revision},
            ) from error
        raise


@router.get("/documents", response_model=list[CreativeDocumentV1])
def list_studio_documents(
    workspace_id: str,
    post_id: str | None = None,
    campaign_id: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[CreativeDocumentV1]:
    assert_access(db, user.id, workspace_id)
    query = select(CreativeDocument).where(CreativeDocument.workspace_id == workspace_id)
    if post_id is not None:
        query = query.where(CreativeDocument.post_id == post_id)
    if campaign_id is not None:
        query = query.where(CreativeDocument.campaign_id == campaign_id)
    records = db.scalars(query.order_by(CreativeDocument.updated_at.desc())).all()
    return [record_to_contract(record) for record in records]


@router.get("/documents/{document_id}", response_model=CreativeDocumentV1)
def get_studio_document(
    document_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> CreativeDocumentV1:
    return record_to_contract(owned_document(db, user.id, document_id))


@router.put("/documents/{document_id}", response_model=CreativeDocumentV1)
def replace_studio_document(
    document_id: str,
    request: ReplaceStudioDocumentRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CreativeDocumentV1:
    record = owned_document(db, user.id, document_id)
    incoming = request.document
    validate_references(
        db,
        record.workspace_id,
        campaign_id=incoming.campaign_ref.id if incoming.campaign_ref else None,
        post_id=incoming.post_ref.id if incoming.post_ref else None,
        opportunity_id=incoming.opportunity_ref.id if incoming.opportunity_ref else None,
        asset_ids=[asset.id for asset in incoming.assets],
    )
    try:
        return record_to_contract(replace_document(db, record, request, user))
    except ValueError as error:
        code = str(error)
        if code == "studio_document_conflict":
            raise HTTPException(status_code=409, detail={"code": code, "currentRevision": record.revision}) from error
        raise HTTPException(status_code=422, detail={"code": code}) from error


@router.post(
    "/documents/{document_id}/assets/{asset_id}/rights-reviews",
    response_model=StudioAssetRightsReviewResponseV1,
)
def review_studio_asset_rights(
    document_id: str,
    asset_id: str,
    request: StudioAssetRightsReviewRequestV1,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=8, max_length=160),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StudioAssetRightsReviewResponseV1:
    document = owned_document(db, user.id, document_id)
    assert_governance_access(db, user.id, document.workspace_id)
    try:
        review, updated = review_natural_sound_rights(
            db,
            document,
            asset_id,
            request,
            user,
            idempotency_key=idempotency_key,
        )
        return StudioAssetRightsReviewResponseV1(review=review, document=record_to_contract(updated))
    except ValueError as error:
        code = str(error)
        conflict = code in {
            "studio_asset_rights_document_conflict",
            "studio_asset_rights_idempotency_conflict",
        }
        raise HTTPException(status_code=409 if conflict else 422, detail={"code": code}) from error


@router.post("/documents/{document_id}/versions", response_model=CreativeDocumentV1)
def version_studio_document(
    document_id: str,
    request: CreativeVersionIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CreativeDocumentV1:
    return record_to_contract(save_version(db, owned_document(db, user.id, document_id), request.label, user))


@router.get("/documents/{document_id}/versions", response_model=list[StudioDocumentVersionV1])
def list_studio_document_versions(
    document_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[StudioDocumentVersionV1]:
    return version_history(owned_document(db, user.id, document_id))


@router.post("/documents/{document_id}/versions/{version_number}/restore", response_model=CreativeDocumentV1)
def restore_studio_document_version(
    document_id: str,
    version_number: int,
    request: RestoreStudioDocumentVersionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CreativeDocumentV1:
    record = owned_document(db, user.id, document_id)
    try:
        return record_to_contract(restore_document_version(db, record, version_number, request, user))
    except ValueError as error:
        code = str(error)
        if code == "studio_document_conflict":
            raise HTTPException(
                status_code=409,
                detail={"code": code, "currentRevision": record.revision},
            ) from error
        if code == "studio_document_version_not_found":
            raise HTTPException(status_code=404, detail={"code": code}) from error
        raise HTTPException(status_code=422, detail={"code": code}) from error


@router.post(
    "/motion-graphs",
    response_model=MotionGraphRecordV1,
    status_code=status.HTTP_201_CREATED,
)
def create_studio_motion_graph(
    request: CreateMotionGraphRequestV1,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MotionGraphRecordV1:
    assert_access(db, user.id, request.workspace_id)
    try:
        return motion_graph_out(create_motion_graph(db, request, user))
    except ValueError as error:
        raise studio_identity_error(error) from error


@router.get("/motion-graphs", response_model=list[MotionGraphRecordV1])
def list_studio_motion_graphs(
    workspace_id: str,
    document_id: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[MotionGraphRecordV1]:
    assert_access(db, user.id, workspace_id)
    return [
        motion_graph_out(item)
        for item in list_motion_graphs(
            db,
            workspace_id=workspace_id,
            document_id=document_id,
        )
    ]


@router.get("/motion-graphs/{graph_id}", response_model=MotionGraphRecordV1)
def get_studio_motion_graph(
    graph_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MotionGraphRecordV1:
    return motion_graph_out(owned_motion_graph(db, user.id, graph_id))


@router.put("/motion-graphs/{graph_id}", response_model=MotionGraphRecordV1)
def replace_studio_motion_graph(
    graph_id: str,
    request: ReplaceMotionGraphRequestV1,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MotionGraphRecordV1:
    record = owned_motion_graph(db, user.id, graph_id)
    try:
        return motion_graph_out(replace_motion_graph(db, record, request, user))
    except ValueError as error:
        raise studio_identity_error(error) from error


@router.post("/motion-graphs/{graph_id}/review", response_model=MotionGraphRecordV1)
def review_studio_motion_graph(
    graph_id: str,
    request: ReviewMotionGraphRequestV1,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MotionGraphRecordV1:
    record = owned_motion_graph(db, user.id, graph_id)
    try:
        return motion_graph_out(review_motion_graph(db, record, request, user))
    except ValueError as error:
        raise studio_identity_error(error) from error


@router.get(
    "/motion-graphs/{graph_id}/projection/{target}",
    response_model=MotionGraphProjectionV1,
)
def get_studio_motion_graph_projection(
    graph_id: str,
    target: Literal["hyperframes", "motion_canvas"],
    reduced_motion: bool = Query(default=False),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MotionGraphProjectionV1:
    item = motion_graph_out(owned_motion_graph(db, user.id, graph_id))
    try:
        return project_motion_graph(
            item.graph,
            target,
            item.evaluation,
            reduced_motion=reduced_motion,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail={"code": str(error)}) from error


@router.post(
    "/documents/{document_id}/reviews",
    response_model=StudioReviewRequestV1,
    status_code=status.HTTP_201_CREATED,
)
def request_studio_review(
    document_id: str,
    request: CreateStudioReviewRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StudioReviewRequestV1:
    try:
        review = request_review(
            db,
            owned_document(db, user.id, document_id),
            user,
            comment=request.comment,
            render_job_id=request.render_job_id,
        )
        return review_out(db, review)
    except ValueError as error:
        raise studio_identity_error(error) from error


@router.get("/reviews/latest", response_model=StudioReviewRequestV1)
def latest_studio_review(
    workspace_id: str,
    document_id: str | None = None,
    post_id: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StudioReviewRequestV1:
    assert_access(db, user.id, workspace_id)
    if not document_id and not post_id:
        raise HTTPException(status_code=422, detail="documentId or postId is required")
    query = select(StudioReviewRequest).where(StudioReviewRequest.workspace_id == workspace_id)
    if document_id:
        query = query.where(StudioReviewRequest.document_id == document_id)
    if post_id:
        query = query.where(StudioReviewRequest.post_id == post_id)
    review = db.scalars(query.order_by(StudioReviewRequest.requested_at.desc()).limit(1)).first()
    if not review:
        raise HTTPException(status_code=404, detail="Studio review not found")
    return review_out(db, review)


@router.get("/reviews/{review_id}/pages/{page_id}/preview", response_model=None)
def preview_studio_review_page(
    review_id: str,
    page_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    review = db.get(StudioReviewRequest, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Studio review not found")
    assert_access(db, user.id, review.workspace_id)
    try:
        payload = render_review_page(db, review, page_id)
    except ValueError as error:
        code = str(error)
        raise HTTPException(
            status_code=404 if code == "studio_review_page_not_found" else 422, detail={"code": code}
        ) from error
    except OSError as error:
        raise HTTPException(status_code=422, detail={"code": "studio_review_source_unavailable"}) from error
    return Response(
        payload,
        media_type="image/png",
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.post("/reviews/{review_id}/decisions", response_model=StudioReviewRequestV1)
def decide_studio_review(
    review_id: str,
    request: StudioReviewDecisionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StudioReviewRequestV1:
    review = db.get(StudioReviewRequest, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Studio review not found")
    assert_access(db, user.id, review.workspace_id)
    try:
        return review_out(
            db,
            decide_review(
                db,
                review,
                user,
                action=request.action,
                comment=request.comment,
                listening_review=request.listening_review,
            ),
        )
    except ValueError as error:
        raise HTTPException(status_code=409, detail={"code": str(error)}) from error


def owned_review(db: Session, user_id: str, review_id: str) -> StudioReviewRequest:
    review = db.get(StudioReviewRequest, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Studio review not found")
    assert_access(db, user_id, review.workspace_id)
    return review


@router.get(
    "/reviews/{review_id}/acoustic-analysis-capability",
    response_model=StudioAcousticAnalysisCapabilityV1,
)
def get_acoustic_analysis_capability(
    review_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StudioAcousticAnalysisCapabilityV1:
    owned_review(db, user.id, review_id)
    return acoustic_analysis_capability(db)


@router.post(
    "/reviews/{review_id}/acoustic-analyses",
    response_model=GenerationJobV1,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_review_acoustic_analysis(
    review_id: str,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=160),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> GenerationJobV1:
    review = owned_review(db, user.id, review_id)
    try:
        job, created = create_acoustic_analysis_job(
            db,
            review,
            user,
            idempotency_key=idempotency_key,
        )
    except ValueError as error:
        raise HTTPException(status_code=409, detail={"code": str(error)}) from error
    if created:
        from ..tasks import execute_studio_generation

        try:
            enqueue_job_task(
                execute_studio_generation,
                job,
                isolated_queues_enabled=get_settings().studio_isolated_queues_enabled,
            )
        except Exception as error:
            db.refresh(job)
            if job.status == "queued":
                job.status = "failed"
                job.error_code = "queue_unavailable"
                job.error_message = type(error).__name__
                job.finished_at = datetime.now(UTC)
                db.commit()
                db.refresh(job)
    return job_out(job)


@router.get("/reviews/{review_id}/publication-preflight", response_model=StudioPublicationPreflightV1)
def get_publication_preflight(
    review_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StudioPublicationPreflightV1:
    try:
        return publication_preflight(db, owned_review(db, user.id, review_id))
    except (OSError, ValueError) as error:
        code = str(error) if isinstance(error, ValueError) else "studio_publication_source_unavailable"
        raise HTTPException(status_code=409, detail={"code": code}) from error


@router.post(
    "/reviews/{review_id}/internal-schedule",
    response_model=StudioInternalScheduleReceiptV1,
)
def create_internal_publication_schedule(
    review_id: str,
    request: StudioInternalScheduleRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StudioInternalScheduleReceiptV1:
    try:
        return schedule_publication(db, owned_review(db, user.id, review_id), user, request.scheduled_at)
    except ValueError as error:
        raise HTTPException(status_code=409, detail={"code": str(error)}) from error


@router.get("/reviews/{review_id}/publication-package", response_model=None)
def download_publication_package(
    review_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    try:
        payload, filename = publication_package(db, owned_review(db, user.id, review_id))
    except (OSError, ValueError) as error:
        code = str(error) if isinstance(error, ValueError) else "studio_publication_source_unavailable"
        raise HTTPException(status_code=409, detail={"code": code}) from error
    return Response(
        payload,
        media_type="application/zip",
        headers={
            "Cache-Control": "private, no-store",
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.post(
    "/documents/{document_id}/exports",
    response_model=AssetOut,
    status_code=status.HTTP_201_CREATED,
)
def export_studio_document(
    document_id: str,
    request: StudioExportRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AssetOut:
    record = owned_document(db, user.id, document_id)
    try:
        return asset_out(export_document(db, record, user, export_format=request.format))
    except ValueError as error:
        raise HTTPException(status_code=422, detail={"code": str(error)}) from error
    except (OSError, KeyError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/consents", response_model=ConsentGrantV1, status_code=status.HTTP_201_CREATED)
def create_studio_consent(
    request: CreateConsentGrantRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ConsentGrantV1:
    assert_access(db, user.id, request.workspace_id)
    if request.evidence_asset_id:
        validate_references(db, request.workspace_id, asset_ids=[request.evidence_asset_id])
    try:
        return consent_out(create_consent_grant(db, request, user))
    except ValueError as error:
        raise studio_identity_error(error) from error


@router.get("/consents", response_model=list[ConsentGrantV1])
def list_studio_consents(
    workspace_id: str,
    subject_key: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ConsentGrantV1]:
    assert_access(db, user.id, workspace_id)
    query = select(StudioConsentGrant).where(StudioConsentGrant.workspace_id == workspace_id)
    if subject_key:
        query = query.where(StudioConsentGrant.subject_key == subject_key)
    return [consent_out(item) for item in db.scalars(query.order_by(StudioConsentGrant.created_at.desc())).all()]


@router.post("/consents/{consent_id}/revoke", response_model=ConsentGrantV1)
def revoke_studio_consent(
    consent_id: str,
    request: RevokeConsentGrantRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ConsentGrantV1:
    grant = owned_consent(db, user.id, consent_id)
    return consent_out(revoke_consent_grant(db, grant, reason=request.reason, user=user))


@router.post("/identities", response_model=IdentityProfileV1, status_code=status.HTTP_201_CREATED)
def create_studio_identity(
    request: CreateIdentityProfileRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> IdentityProfileV1:
    assert_access(db, user.id, request.workspace_id)
    if request.owner_user_id and not db.scalar(
        select(Membership.id).where(
            Membership.user_id == request.owner_user_id,
            Membership.workspace_id == request.workspace_id,
        )
    ):
        raise HTTPException(status_code=422, detail={"code": "identity_owner_not_in_workspace"})
    try:
        return identity_profile_out(create_identity_profile(db, request, user))
    except ValueError as error:
        raise studio_identity_error(error) from error


@router.get("/identities", response_model=list[IdentityProfileV1])
def list_studio_identities(
    workspace_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[IdentityProfileV1]:
    assert_access(db, user.id, workspace_id)
    records = db.scalars(
        select(StudioIdentityProfile)
        .where(StudioIdentityProfile.workspace_id == workspace_id)
        .order_by(StudioIdentityProfile.updated_at.desc())
    ).all()
    return [identity_profile_out(item) for item in records]


@router.post(
    "/identities/{profile_id}/versions",
    response_model=IdentityVersionV1,
    status_code=status.HTTP_201_CREATED,
)
def create_studio_identity_version(
    profile_id: str,
    request: CreateIdentityVersionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> IdentityVersionV1:
    profile = owned_identity(db, user.id, profile_id)
    asset_ids = request.sample_asset_ids + [item.id for item in request.derived_artifacts]
    if asset_ids:
        validate_references(db, profile.workspace_id, asset_ids=asset_ids)
    try:
        return identity_version_out(create_identity_version(db, profile, request, user))
    except ValueError as error:
        raise studio_identity_error(error) from error


@router.get("/identities/{profile_id}/versions", response_model=list[IdentityVersionV1])
def list_studio_identity_versions(
    profile_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[IdentityVersionV1]:
    profile = owned_identity(db, user.id, profile_id)
    versions = db.scalars(
        select(StudioIdentityVersion)
        .where(
            StudioIdentityVersion.profile_id == profile.id,
            StudioIdentityVersion.workspace_id == profile.workspace_id,
        )
        .order_by(StudioIdentityVersion.version.desc())
    ).all()
    return [identity_version_out(item) for item in versions]


@router.post(
    "/identities/{profile_id}/deletion-requests",
    response_model=IdentityDeletionRequestV1,
    status_code=status.HTTP_202_ACCEPTED,
)
def plan_studio_identity_deletion(
    profile_id: str,
    request: CreateIdentityDeletionRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=160),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> IdentityDeletionRequestV1:
    profile = owned_identity(db, user.id, profile_id)
    assert_governance_access(db, user.id, profile.workspace_id)
    try:
        deletion, _ = request_identity_deletion(
            db,
            profile,
            request,
            idempotency_key,
            user,
            target_type="identity_profile",
        )
        maybe_enqueue_identity_deletion(db, deletion)
        return identity_deletion_out(deletion)
    except ValueError as error:
        raise studio_identity_error(error) from error


@router.post(
    "/identities/{profile_id}/versions/{version_id}/evaluations",
    response_model=IdentityEvaluationV1,
    status_code=status.HTTP_201_CREATED,
)
def evaluate_studio_identity_version(
    profile_id: str,
    version_id: str,
    request: CreateIdentityEvaluationRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> IdentityEvaluationV1:
    profile = owned_identity(db, user.id, profile_id)
    assert_governance_access(db, user.id, profile.workspace_id)
    version = owned_identity_version(db, profile, version_id)
    if request.preview_asset_ids:
        validate_references(db, profile.workspace_id, asset_ids=request.preview_asset_ids)
        validate_private_preview_assets(db, profile.workspace_id, request.preview_asset_ids)
    try:
        return identity_evaluation_out(
            create_identity_evaluation(db, version, request, user, target_type="identity_version")
        )
    except ValueError as error:
        raise studio_identity_error(error) from error


@router.get(
    "/identities/{profile_id}/versions/{version_id}/evaluations",
    response_model=list[IdentityEvaluationV1],
)
def list_studio_identity_evaluations(
    profile_id: str,
    version_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[IdentityEvaluationV1]:
    profile = owned_identity(db, user.id, profile_id)
    version = owned_identity_version(db, profile, version_id)
    records = db.scalars(
        select(StudioIdentityEvaluation)
        .where(StudioIdentityEvaluation.identity_version_id == version.id)
        .order_by(StudioIdentityEvaluation.evaluated_at.desc())
    ).all()
    return [identity_evaluation_out(item) for item in records]


@router.post(
    "/identities/{profile_id}/versions/{version_id}/review",
    response_model=IdentityVersionV1,
)
def review_studio_identity_version(
    profile_id: str,
    version_id: str,
    request: ReviewIdentityVersionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> IdentityVersionV1:
    profile = owned_identity(db, user.id, profile_id)
    assert_governance_access(db, user.id, profile.workspace_id)
    version = owned_identity_version(db, profile, version_id)
    try:
        reviewed = review_identity_version(
            db,
            profile,
            version,
            request,
            user,
            target_type="identity_version",
        )
        return identity_version_out(reviewed)
    except ValueError as error:
        raise studio_identity_error(error) from error


@router.post("/voices", response_model=VoiceProfileV1, status_code=status.HTTP_201_CREATED)
def create_studio_voice(
    request: CreateVoiceProfileRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> VoiceProfileV1:
    assert_access(db, user.id, request.workspace_id)
    if request.identity_profile_id:
        identity = owned_identity(db, user.id, request.identity_profile_id)
        if identity.workspace_id != request.workspace_id:
            raise HTTPException(status_code=422, detail={"code": "identity_not_in_workspace"})
    try:
        return voice_profile_out(create_voice_profile(db, request, user))
    except ValueError as error:
        raise studio_identity_error(error) from error


@router.get("/voices", response_model=list[VoiceProfileV1])
def list_studio_voices(
    workspace_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[VoiceProfileV1]:
    assert_access(db, user.id, workspace_id)
    records = db.scalars(
        select(StudioVoiceProfile)
        .where(StudioVoiceProfile.workspace_id == workspace_id)
        .order_by(StudioVoiceProfile.updated_at.desc())
    ).all()
    return [voice_profile_out(item) for item in records]


@router.post(
    "/voices/{profile_id}/versions",
    response_model=VoiceVersionV1,
    status_code=status.HTTP_201_CREATED,
)
def create_studio_voice_version(
    profile_id: str,
    request: CreateVoiceVersionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> VoiceVersionV1:
    profile = owned_voice(db, user.id, profile_id)
    asset_ids = request.sample_asset_ids + [item.id for item in request.derived_artifacts]
    if asset_ids:
        validate_references(db, profile.workspace_id, asset_ids=asset_ids)
    try:
        return voice_version_out(create_voice_version(db, profile, request, user))
    except ValueError as error:
        raise studio_identity_error(error) from error


@router.get("/voices/{profile_id}/versions", response_model=list[VoiceVersionV1])
def list_studio_voice_versions(
    profile_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[VoiceVersionV1]:
    profile = owned_voice(db, user.id, profile_id)
    versions = db.scalars(
        select(StudioVoiceVersion)
        .where(
            StudioVoiceVersion.profile_id == profile.id,
            StudioVoiceVersion.workspace_id == profile.workspace_id,
        )
        .order_by(StudioVoiceVersion.version.desc())
    ).all()
    return [voice_version_out(item) for item in versions]


@router.post(
    "/voices/{profile_id}/deletion-requests",
    response_model=IdentityDeletionRequestV1,
    status_code=status.HTTP_202_ACCEPTED,
)
def plan_studio_voice_deletion(
    profile_id: str,
    request: CreateIdentityDeletionRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=160),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> IdentityDeletionRequestV1:
    profile = owned_voice(db, user.id, profile_id)
    assert_governance_access(db, user.id, profile.workspace_id)
    try:
        deletion, _ = request_identity_deletion(
            db,
            profile,
            request,
            idempotency_key,
            user,
            target_type="voice_profile",
        )
        maybe_enqueue_identity_deletion(db, deletion)
        return identity_deletion_out(deletion)
    except ValueError as error:
        raise studio_identity_error(error) from error


@router.get("/identity-deletion-requests", response_model=list[IdentityDeletionRequestV1])
def list_studio_identity_deletions(
    workspace_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[IdentityDeletionRequestV1]:
    assert_access(db, user.id, workspace_id)
    records = db.scalars(
        select(StudioIdentityDeletionRequest)
        .where(StudioIdentityDeletionRequest.workspace_id == workspace_id)
        .order_by(StudioIdentityDeletionRequest.requested_at.desc())
    ).all()
    return [identity_deletion_out(item) for item in records]


@router.post(
    "/voices/{profile_id}/versions/{version_id}/evaluations",
    response_model=IdentityEvaluationV1,
    status_code=status.HTTP_201_CREATED,
)
def evaluate_studio_voice_version(
    profile_id: str,
    version_id: str,
    request: CreateIdentityEvaluationRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> IdentityEvaluationV1:
    profile = owned_voice(db, user.id, profile_id)
    assert_governance_access(db, user.id, profile.workspace_id)
    version = owned_voice_version(db, profile, version_id)
    if request.preview_asset_ids:
        validate_references(db, profile.workspace_id, asset_ids=request.preview_asset_ids)
        validate_private_preview_assets(db, profile.workspace_id, request.preview_asset_ids)
    try:
        return identity_evaluation_out(
            create_identity_evaluation(db, version, request, user, target_type="voice_version")
        )
    except ValueError as error:
        raise studio_identity_error(error) from error


@router.get(
    "/voices/{profile_id}/versions/{version_id}/evaluations",
    response_model=list[IdentityEvaluationV1],
)
def list_studio_voice_evaluations(
    profile_id: str,
    version_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[IdentityEvaluationV1]:
    profile = owned_voice(db, user.id, profile_id)
    version = owned_voice_version(db, profile, version_id)
    records = db.scalars(
        select(StudioIdentityEvaluation)
        .where(StudioIdentityEvaluation.voice_version_id == version.id)
        .order_by(StudioIdentityEvaluation.evaluated_at.desc())
    ).all()
    return [identity_evaluation_out(item) for item in records]


@router.post(
    "/voices/{profile_id}/versions/{version_id}/review",
    response_model=VoiceVersionV1,
)
def review_studio_voice_version(
    profile_id: str,
    version_id: str,
    request: ReviewIdentityVersionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> VoiceVersionV1:
    profile = owned_voice(db, user.id, profile_id)
    assert_governance_access(db, user.id, profile.workspace_id)
    version = owned_voice_version(db, profile, version_id)
    try:
        reviewed = review_identity_version(
            db,
            profile,
            version,
            request,
            user,
            target_type="voice_version",
        )
        return voice_version_out(reviewed)
    except ValueError as error:
        raise studio_identity_error(error) from error


@router.post("/media-ingests", response_model=MediaIngestV1, status_code=status.HTTP_202_ACCEPTED)
def enqueue_media_ingest(
    request: CreateMediaIngestRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=160),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MediaIngestV1:
    assert_access(db, user.id, request.workspace_id)
    try:
        ingest, job, created = create_media_ingest(db, request, idempotency_key, user)
    except ValueError as error:
        raise studio_identity_error(error) from error
    if created:
        from ..tasks import execute_studio_generation

        try:
            enqueue_job_task(
                execute_studio_generation,
                job,
                isolated_queues_enabled=get_settings().studio_isolated_queues_enabled,
            )
        except Exception as error:
            job.status = "failed"
            job.error_code = "queue_unavailable"
            job.error_message = type(error).__name__
            job.finished_at = datetime.now(UTC)
            ingest.status = "failed"
            ingest.validation_errors = ["queue_unavailable"]
            db.commit()
            db.refresh(ingest)
    return media_ingest_out(ingest)


@router.get("/media-ingests", response_model=list[MediaIngestV1])
def list_media_ingests(
    workspace_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[MediaIngestV1]:
    assert_access(db, user.id, workspace_id)
    records = db.scalars(
        select(StudioMediaIngest)
        .where(StudioMediaIngest.workspace_id == workspace_id)
        .order_by(StudioMediaIngest.created_at.desc())
    ).all()
    return [media_ingest_out(item) for item in records]


@router.get("/media-ingests/{ingest_id}", response_model=MediaIngestV1)
def get_media_ingest(
    ingest_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MediaIngestV1:
    return media_ingest_out(owned_media_ingest(db, user.id, ingest_id))


@router.post(
    "/media-ingests/{ingest_id}/proxy",
    response_model=GenerationJobV1,
    status_code=status.HTTP_202_ACCEPTED,
)
def enqueue_media_proxy(
    ingest_id: str,
    request: CreateMediaProxyRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=160),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> GenerationJobV1:
    ingest = owned_media_ingest(db, user.id, ingest_id)
    assert_access(db, user.id, request.workspace_id)
    try:
        job, created = create_media_proxy_job(db, ingest, request, idempotency_key, user)
    except ValueError as error:
        raise studio_identity_error(error) from error
    if created:
        from ..tasks import execute_studio_generation

        try:
            enqueue_job_task(
                execute_studio_generation,
                job,
                isolated_queues_enabled=get_settings().studio_isolated_queues_enabled,
            )
        except Exception as error:
            db.refresh(job)
            # In eager test execution Celery propagates Retry after the task
            # has already recorded its real provider error. Only a job that
            # never left `queued` represents an actual delivery failure.
            if job.status == "queued":
                job.status = "failed"
                job.error_code = "queue_unavailable"
                job.error_message = type(error).__name__
                job.finished_at = datetime.now(UTC)
                db.commit()
                db.refresh(job)
    return job_out(job)


@router.post(
    "/media-ingests/{ingest_id}/waveform",
    response_model=GenerationJobV1,
    status_code=status.HTTP_202_ACCEPTED,
)
def enqueue_media_waveform(
    ingest_id: str,
    request: CreateAudioWaveformRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=160),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> GenerationJobV1:
    ingest = owned_media_ingest(db, user.id, ingest_id)
    assert_access(db, user.id, request.workspace_id)
    try:
        job, created = create_media_waveform_job(db, ingest, request, idempotency_key, user)
    except ValueError as error:
        raise studio_identity_error(error) from error
    if created:
        from ..tasks import execute_studio_generation

        try:
            enqueue_job_task(
                execute_studio_generation,
                job,
                isolated_queues_enabled=get_settings().studio_isolated_queues_enabled,
            )
        except Exception as error:
            job.status = "failed"
            job.error_code = "queue_unavailable"
            job.error_message = type(error).__name__
            job.finished_at = datetime.now(UTC)
            db.commit()
            db.refresh(job)
    return job_out(job)


@router.post("/transcripts", response_model=TranscriptDocumentV1, status_code=status.HTTP_201_CREATED)
def create_studio_transcript(
    request: CreateTranscriptRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=160),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TranscriptDocumentV1:
    assert_access(db, user.id, request.workspace_id)
    try:
        transcript, _ = create_transcript(db, request, idempotency_key, user)
        return transcript_out(transcript)
    except ValueError as error:
        raise studio_identity_error(error) from error


@router.get("/transcripts", response_model=list[TranscriptDocumentV1])
def list_studio_transcripts(
    workspace_id: str,
    media_ingest_id: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[TranscriptDocumentV1]:
    assert_access(db, user.id, workspace_id)
    query = select(StudioTranscript).where(StudioTranscript.workspace_id == workspace_id)
    if media_ingest_id:
        query = query.where(StudioTranscript.media_ingest_id == media_ingest_id)
    records = db.scalars(query.order_by(StudioTranscript.updated_at.desc())).all()
    return [transcript_out(item) for item in records]


@router.get("/transcripts/{transcript_id}", response_model=TranscriptDocumentV1)
def get_studio_transcript(
    transcript_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TranscriptDocumentV1:
    return transcript_out(owned_transcript(db, user.id, transcript_id))


@router.put("/transcripts/{transcript_id}", response_model=TranscriptDocumentV1)
def replace_studio_transcript(
    transcript_id: str,
    request: ReplaceTranscriptRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TranscriptDocumentV1:
    transcript = owned_transcript(db, user.id, transcript_id)
    try:
        return transcript_out(replace_transcript(db, transcript, request, user))
    except ValueError as error:
        raise studio_identity_error(error) from error


@router.post("/transcripts/{transcript_id}/apply-captions", response_model=CreativeDocumentV1)
def apply_studio_transcript_captions(
    transcript_id: str,
    request: ApplyTranscriptCaptionsRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CreativeDocumentV1:
    transcript = owned_transcript(db, user.id, transcript_id)
    document = owned_document(db, user.id, request.document_id)
    try:
        return record_to_contract(apply_transcript_captions(db, transcript, document, request, user))
    except ValueError as error:
        raise studio_identity_error(error) from error


@router.post("/edit-decision-sets", response_model=EditDecisionSetV1, status_code=status.HTTP_201_CREATED)
def create_studio_edit_decision_set(
    request: CreateEditDecisionSetRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=160),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> EditDecisionSetV1:
    assert_access(db, user.id, request.workspace_id)
    try:
        decision_set, _ = create_decision_set(db, request, idempotency_key, user)
        return decision_set_out(decision_set)
    except ValueError as error:
        raise studio_identity_error(error) from error


@router.get("/edit-decision-sets", response_model=list[EditDecisionSetV1])
def list_studio_edit_decision_sets(
    workspace_id: str,
    media_ingest_id: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[EditDecisionSetV1]:
    assert_access(db, user.id, workspace_id)
    query = select(StudioEditDecisionSet).where(StudioEditDecisionSet.workspace_id == workspace_id)
    if media_ingest_id:
        query = query.where(StudioEditDecisionSet.media_ingest_id == media_ingest_id)
    records = db.scalars(query.order_by(StudioEditDecisionSet.updated_at.desc())).all()
    return [decision_set_out(item) for item in records]


@router.get("/edit-decision-sets/{decision_set_id}", response_model=EditDecisionSetV1)
def get_studio_edit_decision_set(
    decision_set_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> EditDecisionSetV1:
    return decision_set_out(owned_decision_set(db, user.id, decision_set_id))


@router.put("/edit-decision-sets/{decision_set_id}", response_model=EditDecisionSetV1)
def replace_studio_edit_decision_set(
    decision_set_id: str,
    request: ReplaceEditDecisionSetRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> EditDecisionSetV1:
    decision_set = owned_decision_set(db, user.id, decision_set_id)
    try:
        return decision_set_out(replace_decision_set(db, decision_set, request, user))
    except ValueError as error:
        raise studio_identity_error(error) from error


@router.post("/edit-decision-sets/{decision_set_id}/apply", response_model=CreativeDocumentV1)
def apply_studio_edit_decision_set(
    decision_set_id: str,
    request: ApplyEditDecisionSetRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CreativeDocumentV1:
    decision_set = owned_decision_set(db, user.id, decision_set_id)
    document = owned_document(db, user.id, request.document_id)
    try:
        return record_to_contract(apply_edit_decisions(db, decision_set, document, request, user))
    except ValueError as error:
        raise studio_identity_error(error) from error


@router.get("/documents/{document_id}/editorial-readiness", response_model=EditorialReadinessV1)
def get_editorial_readiness(
    document_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> EditorialReadinessV1:
    return editorial_readiness(db, owned_document(db, user.id, document_id))


@router.post("/documents/{document_id}/editorial-plans", response_model=EditorialPlanV1)
def create_editorial_plan(
    document_id: str,
    request: EditorialPlanRequestV1,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=8, max_length=160),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> EditorialPlanV1:
    document = owned_document(db, user.id, document_id)
    assert_governance_access(db, user.id, document.workspace_id)
    try:
        return register_editorial_plan(db, document, request, user, idempotency_key)
    except ValueError as error:
        code = str(error)
        raise HTTPException(status_code=409 if "conflict" in code else 422, detail={"code": code}) from error


@router.post("/documents/{document_id}/editorial-reviews", response_model=EditorialReviewV1)
def create_editorial_review(
    document_id: str,
    request: EditorialReviewRequestV1,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=8, max_length=160),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> EditorialReviewV1:
    document = owned_document(db, user.id, document_id)
    assert_governance_access(db, user.id, document.workspace_id)
    try:
        return submit_editorial_review(db, document, request, user, idempotency_key)
    except ValueError as error:
        code = str(error)
        raise HTTPException(
            status_code=409 if "conflict" in code or "stale" in code else 422,
            detail={"code": code},
        ) from error


@router.get("/editing/capabilities")
def editing_capabilities(user: User = Depends(get_current_user)):
    from ..providers.studios.video_render import VIDEO_RENDER_PROVIDERS

    return VIDEO_RENDER_PROVIDERS["builtin.ffmpeg-contextual-v1"].capabilities()


@router.get("/editing/hybrid-capabilities", response_model=HybridCapabilityManifestV1)
def hybrid_editing_capabilities(user: User = Depends(get_current_user)) -> HybridCapabilityManifestV1:
    """Return observable readiness; configured never means qualified."""
    from ..services.studios.hybrid_video import hybrid_capability_manifest

    return hybrid_capability_manifest()


@router.post("/editing/hybrid-selection", response_model=HybridSelectionResultV1)
def select_hybrid_editing_profile(
    request: HybridSelectionEnvelopeV1,
    user: User = Depends(get_current_user),
) -> HybridSelectionResultV1:
    from ..services.studios.hybrid_video import hybrid_capability_manifest

    envelope = HybridSelectionEnvelopeV1.model_validate(request)
    return select_hybrid_profile(hybrid_capability_manifest(), envelope.policy, envelope.request)


@router.get("/editing/repertoire")
def get_editing_repertoire(
    workspace_id: str, query: str = "", db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    assert_access(db, user.id, workspace_id)
    return {
        "techniques": [
            t.model_dump(mode="json", by_alias=True) for t in editing_repertoire.available_repertoire(db, workspace_id)
        ],
        "matches": editing_repertoire.search_repertoire(db, workspace_id, query) if query else [],
        "collectionMode": "manual",
        "officialConnectorActive": False,
    }


@router.post("/editing/observations")
def ingest_editing_observation(
    workspace_id: str,
    request: EditingObservationV1,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    assert_access(db, user.id, workspace_id)
    assert_governance_access(db, user.id, workspace_id)
    try:
        # Serialize deduplication against the same workspace's planner seeds.
        db.execute(select(Workspace).where(Workspace.id == workspace_id).with_for_update()).scalar_one()
        return editing_repertoire.ingest_observation(db, workspace_id, request)
    except ValueError as error:
        db.rollback()
        raise HTTPException(status_code=422, detail={"code": str(error)}) from error


def _editing_error(db, error):
    db.rollback()
    code = str(error)
    return HTTPException(
        status_code=409 if "conflict" in code or "choice_required" in code else 422, detail={"code": code}
    )


@router.get(
    "/documents/{document_id}/editing-plans/latest", response_model=ContextualEditPlanV2 | ContextualEditPlanV1 | None
)
def latest_editing_plan(document_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return contextual_edits.latest_plan(db, owned_document(db, user.id, document_id))


@router.post("/documents/{document_id}/editing-plans", response_model=ContextualEditPlanV2 | ContextualEditPlanV1)
def create_editing_plan(
    document_id: str,
    request: ContextualPlanRequestV2 | ContextualPlanRequestV1,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=8, max_length=160),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    document = owned_document(db, user.id, document_id)
    try:
        db.execute(select(Workspace).where(Workspace.id == document.workspace_id).with_for_update()).scalar_one()
        return (
            contextual_editing_v2 if isinstance(request, ContextualPlanRequestV2) else contextual_edits
        ).create_plan(db, document, request, user, idempotency_key)
    except ValueError as error:
        raise _editing_error(db, error) from error


@router.post(
    "/documents/{document_id}/editing-plans/{plan_id}/choices",
    response_model=ContextualEditPlanV2 | ContextualEditPlanV1,
)
def choose_editing_alternative(
    document_id: str,
    plan_id: str,
    request: EditingChoiceRequestV1,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    document = owned_document(db, user.id, document_id)
    try:
        return contextual_edits.choose(db, document, plan_id, request, user)
    except ValueError as error:
        raise _editing_error(db, error) from error


@router.post(
    "/documents/{document_id}/editing-plans/{plan_id}/feedback",
    response_model=ContextualEditPlanV2 | ContextualEditPlanV1,
)
def revise_editing_plan(
    document_id: str,
    plan_id: str,
    request: EditingFeedbackRequestV1,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    document = owned_document(db, user.id, document_id)
    try:
        return contextual_edits.feedback(db, document, plan_id, request, user)
    except ValueError as error:
        raise _editing_error(db, error) from error


@router.post(
    "/documents/{document_id}/editing-plans/{plan_id}/recompile",
    response_model=ContextualEditPlanV2,
)
def recompile_contextual_editing_plan(
    document_id: str,
    plan_id: str,
    request: ContextualPlanRecompileRequestV1,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=8, max_length=160),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    document = owned_document(db, user.id, document_id)
    try:
        db.execute(select(Workspace).where(Workspace.id == document.workspace_id).with_for_update()).scalar_one()
        return contextual_editing_v2.recompile_plan(db, document, plan_id, request, user, idempotency_key)
    except ValueError as error:
        raise _editing_error(db, error) from error


@router.post("/documents/{document_id}/editing-plans/{plan_id}/materials", response_model=ContextualEditPlanV2)
def select_editorial_material(
    document_id: str,
    plan_id: str,
    request: EditorialMaterialChoiceV2,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=8, max_length=160),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    document = owned_document(db, user.id, document_id)
    try:
        db.execute(select(Workspace).where(Workspace.id == document.workspace_id).with_for_update()).scalar_one()
        return contextual_editing_v2.select_material(db, document, plan_id, request, user, idempotency_key)
    except ValueError as error:
        raise _editing_error(db, error) from error


@router.post("/documents/{document_id}/editing-plans/{plan_id}/apply", response_model=CreativeDocumentV1)
def apply_contextual_editing(
    document_id: str,
    plan_id: str,
    request: EditingApplyRequestV1,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    document = owned_document(db, user.id, document_id)
    try:
        return contextual_edits.apply_plan(db, document, plan_id, request, user)
    except ValueError as error:
        raise _editing_error(db, error) from error


@router.get("/scene-generation-capability", response_model=SceneGenerationCapabilityV1)
def get_scene_generation_capability(user: User = Depends(get_current_user)):
    return scene_generation_capability()


@router.post(
    "/documents/{document_id}/scene-generation-jobs",
    response_model=GenerationJobV1,
    status_code=status.HTTP_202_ACCEPTED,
)
def enqueue_scene_generation(
    document_id: str,
    request: SceneGenerationRequestV1 | SceneGenerationRequestV2,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=160),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    document = owned_document(db, user.id, document_id)
    try:
        job, created = create_scene_generation_job(db, document, request, user, idempotency_key)
        if created:
            from ..tasks import execute_studio_generation

            try:
                enqueue_job_task(
                    execute_studio_generation,
                    job,
                    isolated_queues_enabled=get_settings().studio_isolated_queues_enabled,
                )
            except Exception:
                db.refresh(job)
                if job.status == "queued":
                    job.status = "failed"
                    job.error_code = "queue_unavailable"
                    job.error_message = "Scene generation queue is unavailable"
                    db.commit()
                    db.refresh(job)
        return job_out(job)
    except ValueError as error:
        raise _editing_error(db, error) from error


@router.post("/scene-generation-jobs/{job_id}/admission", response_model=GenerationJobV1)
def admit_scene_generation_candidate(
    job_id: str,
    request: SceneGenerationAdmissionRequestV1,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    job = owned_job(db, user.id, job_id)
    try:
        return job_out(review_scene_candidate(db, job, request, user))
    except ValueError as error:
        raise _editing_error(db, error) from error


@router.get("/scene-generation-jobs/{job_id}/candidate")
def stream_scene_generation_candidate(
    job_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from fastapi.responses import StreamingResponse

    from ..services.object_storage import get_object_storage

    job = owned_job(db, user.id, job_id)
    if job.job_type != "scene_generation":
        raise HTTPException(404, "Scene candidate not found")
    candidate = (job.result_payload or {}).get("candidate")
    if not candidate or (job.result_payload or {}).get("admission") == "rejected":
        raise HTTPException(404, "Scene candidate not found")

    def chunks():
        storage = get_object_storage(candidate.get("storageBackend") or "local")
        with storage.materialize(candidate["storageKey"]) as path:
            with path.open("rb") as source:
                while chunk := source.read(1024 * 1024):
                    yield chunk

    return StreamingResponse(
        chunks(),
        media_type=candidate.get("mediaType", "video/mp4"),
        headers={"Cache-Control": "private, no-store"},
    )


@router.post("/video-renders", response_model=GenerationJobV1, status_code=status.HTTP_202_ACCEPTED)
def enqueue_video_render(
    request: CreateVideoRenderJobRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=160),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> GenerationJobV1:
    assert_access(db, user.id, request.workspace_id)
    document = owned_document(db, user.id, request.document_id)
    try:
        job, created = create_video_render_job(db, document, request, idempotency_key, user)
    except ValueError as error:
        raise studio_identity_error(error) from error
    if created:
        from ..tasks import execute_studio_generation

        try:
            enqueue_job_task(
                execute_studio_generation,
                job,
                isolated_queues_enabled=get_settings().studio_isolated_queues_enabled,
            )
        except Exception as error:
            db.refresh(job)
            # Eager execution can propagate Celery Retry after the job already
            # persisted its provider failure. Do not replace that diagnosis
            # with a false queue-delivery error.
            if job.status == "queued":
                job.status = "failed"
                job.error_code = "queue_unavailable"
                job.error_message = type(error).__name__
                job.finished_at = datetime.now(UTC)
                db.commit()
                db.refresh(job)
    return job_out(job)


@router.post("/jobs", response_model=GenerationJobV1, status_code=status.HTTP_202_ACCEPTED)
def enqueue_studio_job(
    request: CreateGenerationJobRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=160),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> GenerationJobV1:
    assert_access(db, user.id, request.workspace_id)
    record: CreativeDocument | None = None
    if request.job_type in {"media_probe", "video_proxy", "media_waveform", "video_render"}:
        endpoint = {
            "media_probe": "use_media_ingest_endpoint",
            "video_proxy": "use_media_proxy_endpoint",
            "media_waveform": "use_media_waveform_endpoint",
            "video_render": "use_video_render_endpoint",
        }[request.job_type]
        raise HTTPException(status_code=422, detail={"code": endpoint})
    if request.job_type == "voice_clone":
        if not request.voice_version_id:
            raise HTTPException(status_code=422, detail={"code": "voice_version_required"})
        if not request.consent_grant_id:
            raise HTTPException(status_code=422, detail={"code": "consent_required"})
    if request.job_type == "avatar_video":
        for identifier, code in (
            (request.document_id, "document_required"),
            (request.identity_version_id, "identity_version_required"),
            (request.voice_version_id, "voice_version_required"),
            (request.consent_grant_id, "consent_required"),
        ):
            if not identifier:
                raise HTTPException(status_code=422, detail={"code": code})
    if request.document_id:
        record = owned_document(db, user.id, request.document_id)
        if record.workspace_id != request.workspace_id:
            raise HTTPException(status_code=422, detail="Document does not belong to workspace")
    if request.job_type == "avatar_video" and record:
        document = record_to_contract(record)
        case_id = (document.composition.narrative or {}).get("creativeCaseId")
        if case_id:
            creative_case = next(
                (item for item in creative_casebook().cases if item.case_id == case_id),
                None,
            )
            if not creative_case:
                raise HTTPException(
                    status_code=409,
                    detail={"code": "creative_case_binding_invalid"},
                )
            preproduction = evaluate_preproduction_gate(
                creative_case,
                evaluated_at=datetime.now(UTC),
            )
            if not preproduction.expensive_render_eligible:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "creative_preproduction_approval_required",
                        "blockers": preproduction.blockers,
                    },
                )
    if request.consent_grant_id:
        grant = owned_consent(db, user.id, request.consent_grant_id)
        if grant.workspace_id != request.workspace_id or consent_status(grant) != "active":
            raise HTTPException(status_code=422, detail={"code": "consent_not_active"})
    resolved_versions: dict[str, StudioIdentityVersion | StudioVoiceVersion] = {}
    for model, identifier, label in (
        (StudioIdentityVersion, request.identity_version_id, "identity_version"),
        (StudioVoiceVersion, request.voice_version_id, "voice_version"),
    ):
        if not identifier:
            continue
        version = db.scalar(select(model).where(model.id == identifier, model.workspace_id == request.workspace_id))
        if not version:
            raise HTTPException(status_code=422, detail={"code": f"{label}_not_active"})
        try:
            require_active_version_consent(
                db,
                version,
                consent_grant_id=request.consent_grant_id,
            )
        except ValueError as error:
            raise studio_identity_error(error) from error
        resolved_versions[label] = version
    identity_version = resolved_versions.get("identity_version")
    voice_version = resolved_versions.get("voice_version")
    if request.job_type == "voice_clone" and voice_version:
        voice_profile = db.get(StudioVoiceProfile, voice_version.profile_id)
        if not voice_profile or voice_profile.voice_type != "cloned":
            raise HTTPException(status_code=422, detail={"code": "voice_clone_profile_required"})
        if not voice_version.consent_grant_id:
            raise HTTPException(status_code=422, detail={"code": "voice_clone_consent_required"})
    if identity_version and voice_version:
        voice_profile = db.get(StudioVoiceProfile, voice_version.profile_id)
        if not voice_profile or voice_profile.identity_profile_id != identity_version.profile_id:
            raise HTTPException(status_code=422, detail={"code": "voice_identity_version_mismatch"})
    try:
        job, created = create_job(db, request, idempotency_key, user)
    except ValueError as error:
        code = str(error)
        validation_codes = {
            "voice_version_required",
            "consent_required",
            "voice_version_not_active",
            "voice_clone_profile_required",
            "voice_clone_identity_required",
            "voice_clone_consent_required",
            "consent_not_active",
            "consent_subject_mismatch",
            "consent_scope_missing",
            "document_required",
            "document_not_found",
            "identity_version_required",
            "identity_version_not_active",
            "identity_capability_missing",
            "voice_identity_version_mismatch",
        }
        raise HTTPException(
            status_code=422 if code in validation_codes else 409,
            detail={"code": code},
        ) from error
    if created:
        from ..tasks import execute_studio_generation

        try:
            enqueue_job_task(
                execute_studio_generation,
                job,
                isolated_queues_enabled=get_settings().studio_isolated_queues_enabled,
            )
        except Exception as error:
            job.status = "failed"
            job.error_code = "queue_unavailable"
            job.error_message = type(error).__name__
            job.finished_at = datetime.now(UTC)
            db.commit()
            db.refresh(job)
    return job_out(job)


@router.get("/jobs", response_model=list[GenerationJobV1])
def list_studio_jobs(
    workspace_id: str,
    document_id: str | None = None,
    job_type: str | None = None,
    limit: int = 20,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[GenerationJobV1]:
    """Return the newest observable jobs for an owned workspace.

    This read model lets Studio surfaces recover an in-flight or completed
    operation after a reload without persisting provider details in the
    CreativeDocument.
    """
    assert_access(db, user.id, workspace_id)
    query = select(StudioGenerationJob).where(StudioGenerationJob.workspace_id == workspace_id)
    if document_id:
        document = owned_document(db, user.id, document_id)
        if document.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Document not found")
        query = query.where(StudioGenerationJob.document_id == document_id)
    if job_type:
        query = query.where(StudioGenerationJob.job_type == job_type)
    safe_limit = max(1, min(limit, 100))
    records = db.scalars(query.order_by(StudioGenerationJob.created_at.desc()).limit(safe_limit)).all()
    return [job_out(record) for record in records]


@router.get("/jobs/{job_id}", response_model=GenerationJobV1)
def get_studio_job(
    job_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> GenerationJobV1:
    return job_out(owned_job(db, user.id, job_id))


@router.post("/jobs/{job_id}/cancel", response_model=GenerationJobV1)
def cancel_studio_job(
    job_id: str,
    request: CancelGenerationJobRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> GenerationJobV1:
    try:
        return job_out(request_cancel(db, owned_job(db, user.id, job_id), request.reason, user.id))
    except ValueError as error:
        raise HTTPException(status_code=409, detail={"code": str(error)}) from error


@router.post("/jobs/{job_id}/retry", response_model=GenerationJobV1, status_code=status.HTTP_202_ACCEPTED)
def retry_studio_job(
    job_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> GenerationJobV1:
    job = owned_job(db, user.id, job_id)
    try:
        retry_job(db, job, user.id)
    except ValueError as error:
        raise HTTPException(status_code=409, detail={"code": str(error)}) from error
    from ..tasks import execute_studio_generation

    try:
        enqueue_job_task(
            execute_studio_generation,
            job,
            isolated_queues_enabled=get_settings().studio_isolated_queues_enabled,
        )
    except Exception as error:
        job.status = "failed"
        job.error_code = "queue_unavailable"
        job.error_message = type(error).__name__
        job.finished_at = datetime.now(UTC)
        db.commit()
        db.refresh(job)
    return job_out(job)
