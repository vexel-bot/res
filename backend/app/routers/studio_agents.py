"""Authenticated local agents and editable composition commands."""

import tempfile
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..domain.studios.agents import (
    AgentTaskRequest,
    ApplyAgentTaskRequest,
    LocalCommandsRequest,
    LocalProjectRequest,
    RoleConfiguration,
)
from ..domain.studios.contracts import CreateStudioDocumentRequest, ExportReferenceV1
from ..models import BrandProfile, CreativeDocument, StudioDomainEvent, StudioGenerationJob, User
from ..providers.studios.local_composition import render_page
from ..security import get_current_user
from ..services.studios import agent_orchestrator as agents
from ..services.studios.compatibility import persist_contract, record_to_contract
from ..services.studios.contextual_editing import lock_editing_budget
from ..services.studios.craft import workspace_files, write_asset
from .studios import assert_access, owned_document

router = APIRouter(prefix="/studios/v1", tags=["studio-agents"])


@router.post("/agents/projects", status_code=201)
def create_project(
    request: LocalProjectRequest,
    key: str = Header(alias="Idempotency-Key", min_length=8, max_length=128),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from ..services.brand import brand_readiness
    from ..services.studios.kernel import create_document
    from ..services.studios.timeline_editor import digest

    assert_access(db, user.id, request.workspace_id)
    fingerprint = "agent-create:" + digest(request.model_dump(mode="json"))
    creation_key = f"agent:{request.workspace_id}:{key}"
    previous = db.scalar(select(CreativeDocument).where(CreativeDocument.studio_creation_key == creation_key))
    if previous:
        if previous.correlation_id != fingerprint:
            raise HTTPException(409, detail={"code": "idempotency_payload_conflict"})
        return record_to_contract(previous)
    brand = db.scalar(select(BrandProfile).where(BrandProfile.workspace_id == request.workspace_id))
    composition = {
        "pages": [
            {"id": "page-1", "width": request.width, "height": request.height, "background": "#000000", "layers": []}
        ],
        "narrative": {"localProduction": {"kind": "motion" if request.content_type == "video" else "image"}},
    }
    if request.content_type == "video":
        composition["pages"][0]["durationMs"] = 12000
        composition["mediaTimeline"] = {
            "durationFrames": 288,
            "frameRate": {"numerator": 24, "denominator": 1},
            "tracks": [],
        }
    try:
        payload = CreateStudioDocumentRequest(
            workspace_id=request.workspace_id,
            title=request.title,
            content_type=request.content_type,
            brand_revision=brand_readiness(brand)["revision"],
            brief={"objective": request.title, "audience": "Público definido pelo usuário"},
            composition=composition,
            correlation_id=fingerprint,
        )
        from ..domain.studios.local_composition import validate_composition

        validate_composition(payload.composition, payload.content_type)
        record = create_document(db, payload, user, creation_key=creation_key)
        if record.correlation_id != fingerprint:
            raise HTTPException(409, detail={"code": "idempotency_payload_conflict"})
        return record_to_contract(record)
    except ValueError as error:
        raise failure(db, error) from error


def failure(db, error):
    db.rollback()
    code = str(error)
    if not code.replace("_", "").isalnum() or len(code) > 150:
        code = "agent_contract_rejected"
    return HTTPException(
        409 if "conflict" in code or "busy" in code else 503 if "unavailable" in code else 422, detail={"code": code}
    )


@router.get("/agents/roles")
def roles(workspace_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    assert_access(db, user.id, workspace_id)
    return {
        **agents.configuration(db, workspace_id),
        "klic": {"mode": "existing_gemini", "configurationManagedBy": "klic", "freeTierVerified": False},
        "externalBudgetUsd": 0,
    }


@router.put("/agents/roles")
def configure_roles(
    workspace_id: str, request: RoleConfiguration, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    try:
        return agents.save_configuration(db, workspace_id, request, user)
    except ValueError as error:
        raise failure(db, error) from error


@router.post("/documents/{document_id}/agent-tasks")
def plan(
    document_id: str,
    request: AgentTaskRequest,
    http_request: Request,
    key: str = Header(alias="Idempotency-Key", min_length=8, max_length=128),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        if request.planner == "gemini_experimental":
            from ..services.studios.motion_gemini import require_dev

            require_dev(http_request)
        return agents.create_task(db, owned_document(db, user.id, document_id), request, user, key)
    except ValueError as error:
        raise failure(db, error) from error


@router.get("/documents/{document_id}/agent-tasks")
def tasks(document_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    document = owned_document(db, user.id, document_id)
    rows = db.scalars(
        select(StudioGenerationJob)
        .where(
            StudioGenerationJob.workspace_id == document.workspace_id,
            StudioGenerationJob.document_id == document.id,
            StudioGenerationJob.job_type == "agent_plan",
        )
        .order_by(StudioGenerationJob.created_at.desc())
        .limit(30)
    ).all()
    return [agents.task_out(row, db) for row in rows]


@router.get("/documents/{document_id}/agent-tasks/{task_id}")
def task_detail(document_id: str, task_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    document = owned_document(db, user.id, document_id)
    task = db.get(StudioGenerationJob, task_id)
    if (
        not task
        or task.workspace_id != document.workspace_id
        or task.document_id != document.id
        or task.job_type != "agent_plan"
    ):
        raise HTTPException(404, "Tarefa não encontrada.")
    return agents.task_out(task, db)


@router.post("/documents/{document_id}/agent-tasks/{task_id}/apply")
def apply(
    document_id: str,
    task_id: str,
    request: ApplyAgentTaskRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    document = owned_document(db, user.id, document_id)
    task = db.get(StudioGenerationJob, task_id)
    if not task or task.workspace_id != document.workspace_id or task.document_id != document.id:
        raise HTTPException(404, "Tarefa não encontrada.")
    try:
        return agents.apply_task(db, document, task, request, user)
    except ValueError as error:
        raise failure(db, error) from error


@router.post("/documents/{document_id}/local-commands")
def commands(
    document_id: str,
    request: LocalCommandsRequest,
    key: str = Header(alias="Idempotency-Key", min_length=8, max_length=128),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        return agents.commit_commands(db, owned_document(db, user.id, document_id), request, user, key)
    except ValueError as error:
        raise failure(db, error) from error


@router.get("/documents/{document_id}/local-preview")
def preview(document_id: str, frame: int = 0, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    import io

    record = owned_document(db, user.id, document_id)
    contract = record_to_contract(record)
    try:
        refs = agents.validate_document(db, contract)
        timeline = contract.composition.media_timeline
        if timeline and any(
            (getattr(track, "clips", []) or getattr(track, "cues", []))
            for track in timeline.tracks
            if track.kind != "audio"
        ):
            raise ValueError("agent_media_preview_requires_canonical_render")
        duration = timeline.duration_frames if timeline else 1
        if not 0 <= frame < duration:
            raise ValueError("agent_preview_frame_out_of_range")
        with workspace_files(db, record, None, extra_asset_ids=refs) as (_directory, params, _manifest):
            paths = {entry["assetId"]: entry["path"] for entry in params["media"]}
            image = render_page(contract.composition.pages[0], paths, frame, duration)
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
        return Response(buffer.getvalue(), media_type="image/png", headers={"Cache-Control": "private, no-store"})
    except (ValueError, OSError) as error:
        raise failure(db, error) from error


@router.post("/documents/{document_id}/local-image-export")
def export_image(
    document_id: str,
    request: ApplyAgentTaskRequest,
    key: str = Header(alias="Idempotency-Key", min_length=8, max_length=128),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    record = owned_document(db, user.id, document_id)
    written = None
    try:
        lock_editing_budget(db, record.workspace_id)
        event = db.scalar(
            select(StudioDomainEvent).where(
                StudioDomainEvent.workspace_id == record.workspace_id,
                StudioDomainEvent.aggregate_id == record.id,
                StudioDomainEvent.event_type == "studio.local.image.exported",
                StudioDomainEvent.correlation_id == key,
            )
        )
        if event:
            if event.payload["revision"] != request.expected_revision:
                raise ValueError("idempotency_payload_conflict")
            return event.payload
        db.refresh(record)
        contract = record_to_contract(record)
        if contract.content_type != "visual":
            raise ValueError("agent_image_project_required")
        if contract.revision != request.expected_revision:
            raise ValueError("studio_document_conflict")
        refs = agents.validate_document(db, contract)
        with workspace_files(db, record, None, extra_asset_ids=refs) as (_dir, params, _manifest):
            paths = {entry["assetId"]: entry["path"] for entry in params["media"]}
            with tempfile.TemporaryDirectory(prefix="clicko-local-image-") as directory:
                output = Path(directory) / "composition.png"
                render_page(contract.composition.pages[0], paths).save(output)
                asset, storage, storage_key = write_asset(
                    db,
                    record,
                    output,
                    suffix=".png",
                    media_type="image/png",
                    asset_type="image",
                    title=f"{contract.title} · revisão {contract.revision}",
                    metadata={"provider": "clicko.pillow-local-v1", "documentRevision": contract.revision},
                )
                written = storage, storage_key
        db.flush()
        result = {
            "id": str(uuid4()),
            "assetId": asset.id,
            "revision": contract.revision,
            "checksumSha256": asset.checksum_sha256,
            "downloadUrl": f"/api/v1/assets/{asset.id}/content",
            "externalCostUsd": 0,
            "mediaType": "image/png",
        }
        contract.exports = [
            *contract.exports,
            ExportReferenceV1(
                asset_id=asset.id,
                document_version=contract.version,
                target="download",
                format="png",
                created_at=datetime.now(UTC),
            ),
        ][-100:]
        persist_contract(record, contract)
        from ..services.studios.kernel import emit_event

        emit_event(
            db,
            workspace_id=record.workspace_id,
            event_type="studio.local.image.exported",
            aggregate_type="creative_document",
            aggregate_id=record.id,
            correlation_id=key,
            actor_id=user.id,
            payload=result,
        )
        db.commit()
        return result
    except (ValueError, OSError) as error:
        db.rollback()
        if written:
            written[0].delete(written[1])
        raise failure(db, error) from error
    except Exception:
        db.rollback()
        if written:
            written[0].delete(written[1])
        raise
