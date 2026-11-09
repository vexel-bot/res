"""Customer materials, explainable recipe selection and free local composition studies."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..domain.studios.contracts import StudioContract
from ..domain.studios.timeline_editor import TimelineEditRequest
from ..models import User
from ..security import get_current_user
from ..services.studios import ad_materials as materials
from ..services.studios import ad_copy_workflow, ad_editing_recipes, timeline_editor
from ..services.studios.compatibility import record_to_contract
from .studio_copy_workflow import target
from ..domain.studios.material_effects import EffectRequest

router = APIRouter(prefix="/studios/v1/materials", tags=["ad-materials"])


class BindingRequest(StudioContract):
    expected_revision: int = Field(ge=0)
    kit_id: str = Field(min_length=1, max_length=120)
    kit_revision: int = Field(ge=1)


class RecipeRequest(StudioContract):
    recipe_id: str = Field(min_length=1, max_length=80)
    plan_digest: str | None = None
    request_key: str = Field(min_length=8, max_length=80)


Coordinate = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]


class CutoutRequest(StudioContract):
    source_asset_id: str = Field(min_length=1, max_length=120)
    points: list[tuple[Coordinate, Coordinate]] = Field(min_length=3, max_length=128)
    feather_pixels: float = Field(default=1, ge=0, le=12, allow_inf_nan=False)


class ImportRequest(StudioContract):
    expected_revision: int = Field(ge=1)
    request_key: str = Field(min_length=8, max_length=80)


def failure(error):
    return HTTPException(409 if "conflict" in str(error) or "stale" in str(error) else 422, detail={"code": str(error)})


@router.get("/{kind}/{identifier}")
def get_materials(kind: Literal["project", "document"], identifier: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    record = target(db, user, kind, identifier)
    contract = record_to_contract(record) if kind == "document" else None
    from ..providers.studios.material_effects import capability
    return {**materials.view(db, record.workspace_id, kind, identifier), "localEffects": capability(),
            "documentRevision": contract.revision if contract else None, "canonical": bool(contract and not contract.native_editor_state)}


@router.put("/{kind}/{identifier}/kits/{kit_id}")
def save_kit(kind: Literal["project", "document"], identifier: str, kit_id: str, request: materials.KitRequest,
             db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    record = target(db, user, kind, identifier)
    if len(kit_id) > 120:
        raise HTTPException(422, detail={"code": "ad_material_kit_id_invalid"})
    try:
        return materials.save_kit(db, record.workspace_id, kit_id, request, user)
    except ValueError as error:
        db.rollback()
        raise failure(error) from error


@router.put("/{kind}/{identifier}/binding")
def bind_kit(kind: Literal["project", "document"], identifier: str, request: BindingRequest,
             db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    record = target(db, user, kind, identifier)
    try:
        materials.bind(db, record.workspace_id, kind, identifier, request.kit_id, request.kit_revision, request.expected_revision, user)
        return materials.view(db, record.workspace_id, kind, identifier)
    except ValueError as error:
        db.rollback()
        raise failure(error) from error


def make_plan(db, record, kind, request):
    kit = materials.selected_kit(db, record.workspace_id, kind, record.id)
    if not kit:
        raise ValueError("ad_material_kit_required")
    copy = ad_copy_workflow.view(db, record.workspace_id, kind, record.id)
    headline = copy["data"].get("hook", "")
    if request.recipe_id == "subject_occluded_typography" and not headline.strip():
        raise ValueError("ad_recipe_saved_headline_required")
    contract = record_to_contract(record) if kind == "document" else None
    page = contract.composition.pages[0] if contract else None
    timeline = ad_editing_recipes.compose(request.recipe_id, kit, headline, width=page.width if page else 1080, height=page.height if page else 1920)
    if contract:
        candidate = contract.model_copy(update={"composition": contract.composition.model_copy(update={"media_timeline": timeline})})
        timeline_editor.validate(candidate, require_content=True)
    plan = {"recipeId": request.recipe_id, "kitId": kit["id"], "kitRevision": kit["revision"],
            "copyRevision": copy["revision"], "documentRevision": contract.revision if contract else None,
            "timeline": timeline.model_dump(mode="json", by_alias=True),
            "canApply": bool(contract and not contract.composition.pages[0].layers and
                             not any(getattr(t, "clips", []) or getattr(t, "cues", []) for t in (contract.composition.media_timeline.tracks if contract.composition.media_timeline else []))),
            "apiCalls": 0, "note": "Estudo de composição de 6 segundos. Preserva os arquivos originais; não aprova alegações, não gera voz/avatar e não substitui um anúncio completo."}
    return {**plan, "planDigest": materials.fingerprint(plan)}


@router.post("/{kind}/{identifier}/preview")
def preview(kind: Literal["project", "document"], identifier: str, request: RecipeRequest,
            db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    record = target(db, user, kind, identifier)
    try:
        return make_plan(db, record, kind, request)
    except ValueError as error:
        raise failure(error) from error


@router.post("/{kind}/{identifier}/cutout")
def cutout(kind: Literal["project", "document"], identifier: str, request: CutoutRequest,
           db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    record = target(db, user, kind, identifier)
    try:
        return materials.prepare_cutout(db, record, request.source_asset_id, request.points, request.feather_pixels, user)
    except ValueError as error:
        raise failure(error) from error


@router.post("/document/{identifier}/apply")
def apply(identifier: str, request: RecipeRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    record = target(db, user, "document", identifier)
    try:
        plan = make_plan(db, record, "document", request)
        if not request.plan_digest or request.plan_digest != plan["planDigest"]:
            raise ValueError("ad_recipe_preview_conflict")
        if not plan["canApply"]:
            raise ValueError("ad_recipe_requires_empty_canonical_timeline")
        document = timeline_editor.save(db, record, TimelineEditRequest(expectedRevision=plan["documentRevision"], timeline=plan["timeline"]), user, request.request_key)
        return {"document": document, "apiCalls": 0}
    except ValueError as error:
        db.rollback()
        raise failure(error) from error


@router.post("/document/{identifier}/import")
def import_materials(identifier: str, request: ImportRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    record = target(db, user, "document", identifier)
    try:
        kit = materials.selected_kit(db, record.workspace_id, "document", identifier)
        if not kit:
            raise ValueError("ad_material_kit_required")
        contract = record_to_contract(record)
        ids = [m["assetId"] for m in kit["materials"] if m["role"] != "identity"]
        document = timeline_editor.save(db, record, TimelineEditRequest(expectedRevision=request.expected_revision,
            timeline=contract.composition.media_timeline), user, request.request_key, extra_asset_ids=ids)
        return {"document": document, "apiCalls": 0}
    except ValueError as error:
        db.rollback()
        raise failure(error) from error


@router.post("/document/{identifier}/effects",status_code=202)
def prepare_effect(identifier: str,request: EffectRequest,db: Session=Depends(get_db),user: User=Depends(get_current_user)):
    from ..services.studios import material_effects
    from ..services.studios.jobs import job_out
    from .studio_video import dispatch
    record=target(db,user,"document",identifier)
    try:
        job,created=material_effects.create(db,record,request,user)
        if created:
            try:
                dispatch(job)
            except Exception as error:
                job.status="failed"
                job.error_code="material_effect_queue_unavailable"
                job.error_message="Não foi possível iniciar o processamento local."
                db.commit()
                raise HTTPException(503,detail={"code":"material_effect_queue_unavailable","jobId":job.id}) from error
        return job_out(job)
    except ValueError as error:
        db.rollback()
        raise failure(error) from error
