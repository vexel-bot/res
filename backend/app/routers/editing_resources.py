import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..domain.studios.editing_resources import (
    ApplyGeneratedResourceV1,
    AttachResourceV1,
    EditingAIRequestV1,
    GeminiEditingRequestV1,
    ImportResourceV1,
    RegisteredEditingSourceV1,
    ResolveResourceV1,
    ResourceMetadataV1,
    ReviewGeneratedResourceV1,
)
from ..domain.studios.editorial_production import ExternalProductionReviewV1, ProductionRequestV1, ProductionRevisionV1
from ..domain.studios.visual_audit import VisualComparisonReviewV1, VisualHumanReviewV1
from ..models import LibraryAsset, User
from ..security import get_current_user
from ..services.studios import editing_resources as resources
from .assets import assert_access, asset_out
from .studios import assert_governance_access, owned_document

router = APIRouter(prefix="/studios/v1", tags=["editing-resources"])


@router.get("/workspaces/{workspace_id}/visual-quality")
def get_visual_quality_program(
    workspace_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    if not get_settings().studio_visual_quality_indicator_enabled:
        raise HTTPException(status_code=404, detail={"code": "visual_quality_indicator_disabled"})
    assert_governance_access(db, user.id, workspace_id)
    from ..services.studios.visual_quality_program import project_quality_program

    return project_quality_program(db, workspace_id)


@router.post("/documents/{document_id}/visual-quality-comparison")
def review_visual_quality_comparison(
    document_id: str, request: VisualComparisonReviewV1,
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    if not get_settings().studio_visual_quality_indicator_enabled:
        raise HTTPException(status_code=404, detail={"code": "visual_quality_indicator_disabled"})
    document = owned_document(db, user.id, document_id)
    assert_governance_access(db, user.id, document.workspace_id)
    from ..services.studios.visual_quality_comparison import record_visual_comparison

    try:
        return record_visual_comparison(db, document, request, user)
    except ValueError as error:
        raise failure(db, error) from error


@router.get("/documents/{document_id}/production-runs/{run_id}/evidence")
def export_production_evidence(
    document_id: str, run_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    from fastapi.responses import StreamingResponse

    from ..services.studios.production_evidence import export_package

    record = owned_document(db, user.id, document_id)
    try:
        stream = export_package(db, record, run_id)
    except ValueError as error:
        raise failure(db, error) from error

    def chunks():
        try:
            while chunk := stream.read(1024 * 1024):
                yield chunk
        finally:
            stream.close()

    return StreamingResponse(
        chunks(),
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="res-evidencias.zip"', "Cache-Control": "no-store"},
    )


@router.post("/documents/{document_id}/production-runs/{run_id}/external-review")
def external_production_review(
    document_id: str,
    run_id: str,
    request: ExternalProductionReviewV1,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from ..services.studios.production_evidence import record_external_review

    record = owned_document(db, user.id, document_id)
    try:
        return record_external_review(db, record, run_id, request, user)
    except ValueError as error:
        raise failure(db, error) from error


@router.post("/documents/{document_id}/renders/{asset_id}/visual-review")
def review_render_visuals(
    document_id: str,
    asset_id: str,
    request: VisualHumanReviewV1,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from ..services.studios.visual_review import record_visual_review

    document = owned_document(db, user.id, document_id)
    asset = db.get(LibraryAsset, asset_id)
    if not asset or asset.workspace_id != document.workspace_id:
        raise HTTPException(404, "Render not found")
    try:
        receipt = record_visual_review(db, document, asset, request, user)
        db.commit()
        return receipt
    except ValueError as error:
        raise failure(db, error) from error


@router.post("/documents/{document_id}/production-runs", status_code=202)
def create_production_run(
    document_id: str,
    request: ProductionRequestV1,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=8, max_length=160),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from ..services.studios.editorial_production import create_run

    record = owned_document(db, user.id, document_id)
    if request.quality_phase_id:
        if not get_settings().studio_visual_quality_indicator_enabled:
            raise HTTPException(status_code=404, detail={"code": "visual_quality_indicator_disabled"})
        assert_governance_access(db, user.id, record.workspace_id)
    try:
        run = create_run(db, record, request, user, idempotency_key)
        from ..services.studios.production_queue import continue_from_api

        return continue_from_api(db, record, run["id"], user) if run["status"] == "pending" else run
    except ValueError as error:
        raise failure(db, error) from error


@router.get("/documents/{document_id}/production-runs/{run_id}")
def get_production_run(
    document_id: str, run_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    from ..services.studios.editorial_production import get_run

    record = owned_document(db, user.id, document_id)
    try:
        return get_run(db, record, run_id)
    except ValueError as error:
        raise failure(db, error) from error


@router.post("/documents/{document_id}/production-runs/{run_id}/resume")
def resume_production_run(
    document_id: str, run_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    from ..services.studios.production_queue import continue_from_api

    record = owned_document(db, user.id, document_id)
    try:
        return continue_from_api(db, record, run_id, user)
    except ValueError as error:
        raise failure(db, error) from error


@router.post("/documents/{document_id}/production-runs/{run_id}/cancel")
def cancel_production_run(
    document_id: str, run_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    from ..services.studios.editorial_production import advance_run

    record = owned_document(db, user.id, document_id)
    try:
        return advance_run(db, record, run_id, user, cancel=True)
    except ValueError as error:
        raise failure(db, error) from error


@router.post("/documents/{document_id}/production-runs/{run_id}/revise", status_code=202)
def revise_production_run(
    document_id: str,
    run_id: str,
    request: ProductionRevisionV1,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from ..services.studios.editorial_production import revise_run

    record = owned_document(db, user.id, document_id)
    try:
        revise_run(db, record, run_id, request, user)
        from ..services.studios.production_queue import continue_from_api

        return continue_from_api(db, record, run_id, user)
    except ValueError as error:
        raise failure(db, error) from error


@router.get("/editing/ai")
def editing_ai_status(user: User = Depends(get_current_user)):
    from dataclasses import asdict

    from ..providers.studios.contextual_render import ADVANCED, CAPABILITIES
    from ..providers.studios.editing_ai import ADAPTERS, compatible_binding, selected_adapter
    from ..providers.studios.video_render import VIDEO_RENDER_PROVIDERS
    from ..services.studios.scene_compiler import COMPONENTS

    settings = get_settings()
    providers = []
    for key, spec in ADAPTERS.items():
        reason = None
        if key == "gemini":
            configured = gemini_status(user)["configured"]
            if not configured:
                reason = "editing_gemini_not_configured"
        elif key == "runway":
            from ..providers.studios.runway_editing import runway_binding

            try:
                runway_binding(settings, "generate_video")
                configured = True
            except ValueError as error:
                configured, reason = False, str(error)
        elif key == "sora":
            from datetime import UTC, datetime

            from ..providers.studios.openai_video import SORA_API_SHUTDOWN_DATE

            configured = bool(
                datetime.now(UTC).date() < SORA_API_SHUTDOWN_DATE
                and settings.environment != "production"
                and settings.openai_outbound_enabled
                and settings.openai_video_generation_enabled
                and settings.openai_api_key
                and settings.openai_max_external_spend_usd >= 0.40
            )
            if not configured:
                reason = "sora_local_test_not_configured_or_retired"
        else:
            try:
                compatible_binding(settings)
                configured = True
            except ValueError as error:
                configured, reason = False, str(error)
        providers.append({**asdict(spec), "key": key, "configured": configured, "reason": reason})
    stages = {}
    for operation in ["plan", "generate_image", "edit_image", "generate_video", "edit_video"]:
        try:
            key, _ = selected_adapter(settings, operation)
            provider = next(p for p in providers if p["key"] == key)
            stages[operation] = {"provider": key, "configured": provider["configured"], "label": provider["label"]}
        except ValueError as error:
            stages[operation] = {"provider": None, "configured": False, "reason": str(error)}
    return {
        "configured": any(stage["configured"] for stage in stages.values()),
        "selectedProvider": settings.studio_editing_ai_provider,
        "label": stages["plan"].get("label", "Sem planejador de IA"),
        "operations": [operation for operation, stage in stages.items() if stage["configured"]],
        "stages": stages,
        "providers": providers,
        "automaticFallback": False,
        "qualityIndicatorEnabled": settings.studio_visual_quality_indicator_enabled,
        "qualification": "pending_real_media_validation",
        "generatedMaterialPolicy": "candidate-human-review-v1",
        "contextualV2": {
            "configured": "hyperframes.contextual-v2" in VIDEO_RENDER_PROVIDERS,
            "provider": "hyperframes.contextual-v2",
            "components": COMPONENTS,
            "qualification": "pending_full_audiovisual_validation",
        },
        "motionCanvas": {
            "configured": "motion-canvas.contextual-v1" in VIDEO_RENDER_PROVIDERS,
            "provider": "motion-canvas.contextual-v1",
            "qualification": "experimental_engineering_render;visual_review_pending",
        },
        "remotion": {
            "configured": "remotion.contextual-v1" in VIDEO_RENDER_PROVIDERS,
            "provider": "remotion.contextual-v1",
            "qualification": "experimental_engineering_render;license_and_visual_review_pending",
        },
        "remotionNative": {
            "configured": "remotion.contextual-v2" in VIDEO_RENDER_PROVIDERS,
            "provider": "remotion.contextual-v2",
            "experimental": True,
            "qualification": "license_and_human_visual_review_pending",
        },
        "renderer": {
            "provider": "builtin.ffmpeg-contextual-v1",
            "requiresAI": False,
            "capabilities": CAPABILITIES,
            "unsupported": ADVANCED,
        },
    }


@router.post("/documents/{document_id}/editing-ai-jobs", status_code=202)
def create_ai_job(
    document_id: str,
    request: EditingAIRequestV1,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=8, max_length=160),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from sqlalchemy import select

    from ..models import StudioGenerationJob
    from ..providers.studios.editing_ai import selected_adapter
    from ..services.studios.contextual_editing import lock_editing_budget
    from ..services.studios.jobs import job_out

    record = owned_document(db, user.id, document_id)
    # Reuse the shared transaction lock to serialize cross-adapter idempotency checks.
    lock_editing_budget(db, record.workspace_id)
    existing = db.scalar(
        select(StudioGenerationJob).where(
            StudioGenerationJob.workspace_id == record.workspace_id,
            StudioGenerationJob.job_type.in_(["editing_gemini", "editing_ai"]),
            StudioGenerationJob.idempotency_key == idempotency_key,
        )
    )
    if existing:
        previous = EditingAIRequestV1.model_validate(existing.request_payload["input"])
        if existing.document_id != document_id or previous != request:
            raise HTTPException(409, detail={"code": "idempotency_payload_conflict"})
        return job_out(existing)

    try:
        selected, _ = selected_adapter(get_settings(), request.operation)
    except ValueError as error:
        raise HTTPException(
            422,
            detail={
                "code": str(error),
                "alternatives": ["Usar material do projeto ou acervo", "Configurar um adaptador com esta capacidade"],
            },
        ) from error
    return _enqueue_editing_job(
        document_id, request, idempotency_key, db, user, compatible=selected == "compatible", adapter=selected
    )


@router.post("/documents/{document_id}/editing-resources/apply")
def apply_generated(
    document_id: str,
    request: ApplyGeneratedResourceV1,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    record = owned_document(db, user.id, document_id)
    try:
        result = resources.apply_generated_resource(db, record, request)
        db.commit()
        return result
    except ValueError as error:
        raise failure(db, error) from error


@router.post("/editing/resources/{asset_id}/review")
def review_resource(
    asset_id: str,
    request: ReviewGeneratedResourceV1,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from datetime import UTC, datetime

    asset = db.get(LibraryAsset, asset_id)
    if not asset or asset.lifecycle_status != "active":
        raise HTTPException(404, "Resource not found")
    assert_access(db, user.id, asset.workspace_id)
    if asset.checksum_sha256 != request.checksum or not (asset.object_metadata or {}).get("generationJobId"):
        raise HTTPException(409, detail={"code": "resource_review_binding_conflict"})
    asset.object_metadata = {
        **asset.object_metadata,
        "visualReview": request.result,
        "visualReviewReceipt": {
            "reviewedBy": user.id,
            "at": datetime.now(UTC).isoformat(),
            **request.model_dump(mode="json"),
        },
    }
    db.commit()
    return asset_out(asset)


def failure(db, error):
    db.rollback()
    return HTTPException(status_code=409 if "conflict" in str(error) else 422, detail={"code": str(error)})


@router.get("/editing/resources")
def catalog(
    workspace_id: str,
    query: str = "",
    kind: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    assert_access(db, user.id, workspace_id)
    return resources.catalog(db, workspace_id, query, kind)


@router.post("/editing/resources/import")
def import_url(
    request: ImportResourceV1, workspace_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    assert_access(db, user.id, workspace_id)
    try:
        asset = resources.import_resource(db, workspace_id, request, user.id)
        db.commit()
        return asset_out(asset)
    except (ValueError, OSError) as error:
        raise failure(db, error) from error


@router.post("/editing/resources/upload")
async def upload(
    workspace_id: str = Form(...),
    title: str = Form(..., max_length=240),
    metadata: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    assert_access(db, user.id, workspace_id)
    try:
        info = ResourceMetadataV1.model_validate_json(metadata)
        with tempfile.TemporaryDirectory(prefix="res-upload-") as directory:
            path = Path(directory) / "resource"
            size = 0
            with path.open("wb") as output:
                while chunk := await file.read(65536):
                    size += len(chunk)
                    if size > 100 * 1024 * 1024:
                        raise ValueError("resource_too_large")
                    output.write(chunk)
            asset = resources.store_resource(db, workspace_id, title, path, info, user.id)
            db.commit()
            return asset_out(asset)
    except (ValueError, OSError) as error:
        raise failure(db, error) from error


@router.post("/editing/resources/resolve")
def resolve(
    request: ResolveResourceV1, workspace_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    assert_access(db, user.id, workspace_id)
    try:
        return resources.resolve_resource(db, workspace_id, request)
    except ValueError as error:
        raise failure(db, error) from error


@router.get("/editing/resource-sources")
def list_resource_sources(
    workspace_id: str, query: str = "", db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    assert_access(db, user.id, workspace_id)
    return resources.registered_sources(db, workspace_id, query)


@router.post("/editing/resource-sources")
def register_resource_source(
    request: RegisteredEditingSourceV1,
    workspace_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    assert_access(db, user.id, workspace_id)
    try:
        result = resources.register_source(db, workspace_id, request, user.id)
        db.commit()
        return result
    except ValueError as error:
        raise failure(db, error) from error


@router.post("/editing/resource-sources/{source_id}/acquire")
def acquire_resource_source(
    source_id: str, workspace_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    assert_access(db, user.id, workspace_id)
    try:
        result = resources.acquire_registered_source(db, workspace_id, source_id, user.id)
        db.commit()
        return asset_out(result)
    except (ValueError, OSError) as error:
        raise failure(db, error) from error


@router.post("/documents/{document_id}/editing-resources")
def attach(
    document_id: str, request: AttachResourceV1, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    record = owned_document(db, user.id, document_id)
    try:
        contract = resources.attach_resource(db, record, request.asset_id, request.expected_document_revision)
        db.commit()
        return contract
    except ValueError as error:
        raise failure(db, error) from error


@router.get("/editing/fonts")
def fonts(family: str = Query(min_length=1, max_length=120), user: User = Depends(get_current_user)):
    from ..services.studios.editing_fonts import lookup_fonts

    try:
        return lookup_fonts(family)
    except ValueError as error:
        raise HTTPException(422, detail={"code": str(error)}) from error


@router.get("/editing/gemini")
def gemini_status(user: User = Depends(get_current_user)):
    settings = get_settings()
    key = (
        settings.studio_gemini_production_key
        if settings.environment == "production"
        else settings.studio_gemini_test_key
    )
    return {
        "configured": bool(settings.studio_gemini_enabled and key),
        "environment": settings.environment,
        "productionBudgetLimit": None,
        "qualification": "pending_real_media_validation",
        "models": {
            "plan": settings.studio_gemini_planning_model,
            "image": settings.studio_gemini_image_model,
            "video": settings.studio_gemini_video_model,
        },
    }


@router.get("/editing/usage")
def editing_usage(workspace_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    from sqlalchemy import select

    from ..models import StudioGenerationJob

    assert_access(db, user.id, workspace_id)
    jobs = db.scalars(
        select(StudioGenerationJob)
        .where(
            StudioGenerationJob.workspace_id == workspace_id,
            StudioGenerationJob.job_type.in_(["editing_gemini", "editing_ai"]),
        )
        .order_by(StudioGenerationJob.created_at.desc())
        .limit(100)
    ).all()
    return {
        "productionLimit": None,
        "jobs": [
            {
                "id": job.id,
                "provider": job.provider,
                "status": job.status,
                "environment": job.request_payload.get("environment"),
                "model": job.request_payload.get("model"),
                "priceVersion": job.request_payload.get("priceVersion"),
                "usage": (job.result_payload or {}).get("usage"),
                "verificationUsage": (job.result_payload or {}).get("verificationUsage"),
                "outputImages": (job.result_payload or {}).get("outputImages"),
                "outputVideoSeconds": (job.result_payload or {}).get("outputVideoSeconds"),
                "storageBytes": (job.result_payload or {}).get("storageBytes"),
                "processingSeconds": (job.result_payload or {}).get("processingSeconds"),
                "submissionOutcomeUnknown": bool(
                    (job.result_payload or {}).get("submissionStarted")
                    and not (job.result_payload or {}).get("responseKey")
                    and not (job.result_payload or {}).get("providerOperationId")
                ),
                "createdAt": job.created_at,
                "finishedAt": job.finished_at,
                "attempts": job.attempts,
                "testReservationUsd": (job.result_payload or {}).get("testReservationUsd"),
            }
            for job in jobs
        ],
    }


@router.post("/documents/{document_id}/editing-gemini-jobs", status_code=202)
def create_gemini_job(
    document_id: str,
    request: GeminiEditingRequestV1,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=8, max_length=160),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return _enqueue_editing_job(document_id, request, idempotency_key, db, user)


def _enqueue_editing_job(document_id, request, idempotency_key, db, user, *, compatible=False, adapter=None):
    from ..services.studios.gemini_editing import create_editing_job
    from ..services.studios.jobs import enqueue_job_task, job_out
    from ..tasks import execute_studio_generation

    record = owned_document(db, user.id, document_id)
    try:
        job, created = create_editing_job(
            db, record, request, user, idempotency_key, compatible=compatible, adapter=adapter
        )
        if created:
            try:
                enqueue_job_task(
                    execute_studio_generation,
                    job,
                    isolated_queues_enabled=get_settings().studio_isolated_queues_enabled,
                )
            except Exception as error:
                from datetime import UTC, datetime

                db.refresh(job)
                if job.status == "queued":
                    job.status = "failed"
                    job.error_code = "queue_unavailable"
                    job.error_message = type(error).__name__
                    job.finished_at = datetime.now(UTC)
                    db.commit()
        return job_out(job)
    except ValueError as error:
        raise failure(db, error) from error


@router.get("/editing/visual-audit-policy")
def visual_audit_policy(user: User = Depends(get_current_user)):
    from ..domain.studios.visual_audit import VisualAuditPolicyV2

    return VisualAuditPolicyV2().model_dump(mode="json", by_alias=True)


@router.post("/editing/font-packs/editorial-v1/import")
def import_editorial_fonts(workspace_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    from ..services.studios.editorial_font_pack import import_pack

    assert_access(db, user.id, workspace_id)
    try:
        result = import_pack(db, workspace_id, user.id)
        db.commit()
        return result
    except (ValueError, OSError) as error:
        raise failure(db, error) from error


@router.get("/editing/resources/discover/pexels")
def discover_pexels(
    workspace_id: str,
    query: str,
    kind: str = "video",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from ..providers.studios.pexels_resources import discover

    assert_access(db, user.id, workspace_id)
    if not query.strip() or len(query) > 500:
        raise HTTPException(status_code=422, detail="resource_query_invalid")
    key = get_settings().pexels_api_key
    try:
        return discover(key.get_secret_value() if key else None, query, kind)
    except ValueError as error:
        raise failure(db, error) from error
