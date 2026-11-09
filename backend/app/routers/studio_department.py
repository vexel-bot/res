"""Persistent client-facing creative department; native production stays in Craft."""

from datetime import UTC, datetime
from hashlib import sha256
from typing import Literal
from uuid import NAMESPACE_URL, uuid4, uuid5

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import Field
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..domain.studios.contracts import AssetReferenceV1, CreateStudioDocumentRequest, StudioContract
from ..domain.studios.craft import CraftCommandRequestV1, CraftMigrationRequestV1, CraftRenderRequestV1
from ..models import BrandProfile, LibraryAsset, Post, User, Workspace, WorkspaceResource
from ..security import get_current_user
from ..services.brand import brand_readiness
from ..services.studios import craft
from ..services.studios.casting import resolve_cast
from ..services.studios.compatibility import record_to_contract
from ..services.studios.kernel import create_document
from ..services.studios.project_montage import native_imports, plan_video_montage
from ..services.studios.project_voiceover import native_voiceover_commands, plan_voiceover
from .studio_craft import render_job
from .studios import assert_access, studio_identity_error, validate_references

router = APIRouter(prefix="/studios/v1/projects", tags=["studio-department"])
KIND = "studio_department"


class ProjectInput(StudioContract):
    workspace_id: str
    request_key: str = Field(min_length=8, max_length=80)
    title: str = Field(min_length=3, max_length=180)
    objective: str = Field(min_length=8, max_length=1000)
    audience: str = Field(min_length=3, max_length=1000)
    tone: str = Field(default="Claro e preciso", max_length=500)
    evidence: str = Field(default="", max_length=1500)
    front: Literal["content", "ads"] = "content"
    intent: Literal["education", "authority", "offer"] = "education"
    format: Literal["image", "carousel", "video"] = "carousel"
    campaign_id: str | None = None
    post_id: str | None = None
    source_asset_id: str | None = None
    identity_version_id: str | None = None
    voice_version_id: str | None = None


class ProjectChange(StudioContract):
    expected_revision: int = Field(ge=1)
    direction_id: Literal["guide", "demonstrate"]


class ProductionRequest(StudioContract):
    expected_revision: int = Field(ge=1)
    presentation_layout: Literal["sequential", "picture_in_picture"] = "sequential"


class AppearancePlanRequest(StudioContract):
    expected_revision: int = Field(ge=1)
    direction: str = Field(min_length=3, max_length=4000)
    seed: int = Field(default=0, ge=0, lt=2**32)


class AppearanceGenerationRequest(AppearancePlanRequest):
    operation: Literal["generate_image"]
    plan_digest_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class AppearanceSelection(StudioContract):
    expected_revision: int = Field(ge=1)
    job_id: str = Field(min_length=1, max_length=80)


def now():
    return datetime.now(UTC).isoformat()


def out(record):
    return {**record.payload, "id": record.id, "workspaceId": record.workspace_id}


def owned(db, user, project_id):
    row = db.get(WorkspaceResource, project_id)
    if not row or row.kind != KIND:
        raise HTTPException(404, "Projeto não encontrado")
    assert_access(db, user.id, row.workspace_id)
    return row


def change(db, row, expected, values):
    payload = {**row.payload, **values, "revision": expected + 1, "updatedAt": now()}
    result = db.execute(
        update(WorkspaceResource)
        .where(
            WorkspaceResource.id == row.id,
            WorkspaceResource.payload["revision"].as_integer() == expected,
        )
        .values(payload=payload)
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        db.rollback()
        raise HTTPException(409, "O projeto mudou em outra sessão. Recarregue antes de continuar.")
    db.commit()
    db.refresh(row)
    return row


def directions(data):
    subject = data.title.strip()
    guide = {
        "education": (
            subject,
            "Uma explicação que parte da dúvida do público e organiza o assunto.",
            "Guarde esta orientação para consultar quando precisar.",
        ),
        "authority": (
            f"Como trabalhamos: {subject}"[:200],
            "Mostra critérios e limites do trabalho, usando apenas o material informado.",
            "Conheça o processo e traga sua dúvida.",
        ),
        "offer": (
            subject,
            "Apresenta a ajuda oferecida, para quem ela serve e qual é o próximo passo.",
            "Consulte as condições e avalie se esta solução atende ao seu contexto.",
        ),
    }[data.intent]
    return [
        {
            "id": "guide",
            "title": guide[0],
            "rationale": guide[1],
            "opening": subject,
            "beats": [data.objective.strip(), data.evidence.strip() or "", guide[2]],
            "cta": guide[2],
            "format": data.format,
            "basis": "brief-derived-outline",
            "knowledgeRefs": ["F01", "F07", "F10", "F14" if data.intent == "offer" else "F15"],
        },
        {
            "id": "demonstrate",
            "title": f"Na prática: {subject}"[:200],
            "rationale": f"Desenvolve o objetivo em uma sequência comentada para {data.audience.strip()}.",
            "opening": f"Na prática: {subject}"[:200],
            "beats": [
                data.evidence.strip() or data.objective.strip(),
                data.objective.strip(),
                "Observe o processo e seus limites antes de escolher o próximo passo.",
            ],
            "cta": "Traga uma dúvida sobre o processo.",
            "format": data.format,
            "basis": "brief-derived-outline",
            "knowledgeRefs": ["F05", "F08", "F13"],
        },
    ]


@router.get("")
def list_projects(workspace_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    assert_access(db, user.id, workspace_id)
    rows = db.scalars(
        select(WorkspaceResource)
        .where(
            WorkspaceResource.workspace_id == workspace_id,
            WorkspaceResource.kind == KIND,
        )
        .order_by(WorkspaceResource.updated_at.desc())
        .limit(100)
    ).all()
    return [out(row) for row in rows]


@router.post("", status_code=201)
def create_project(data: ProjectInput, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not data.title.strip() or not data.objective.strip() or not data.audience.strip():
        raise HTTPException(422, "Informe assunto, objetivo e público.")
    assert_access(db, user.id, data.workspace_id)
    validate_references(
        db,
        data.workspace_id,
        campaign_id=data.campaign_id,
        post_id=data.post_id,
        asset_ids=[data.source_asset_id] if data.source_asset_id else [],
    )
    try:
        casting = resolve_cast(db, data.workspace_id, data.identity_version_id, data.voice_version_id)
    except ValueError as error:
        raise studio_identity_error(error) from error
    # Retain the original fingerprint for requests created before cast fields existed.
    excluded = {"request_key"} | {
        field for field in ("identity_version_id", "voice_version_id") if getattr(data, field) is None
    }
    fingerprint = sha256(data.model_dump_json(exclude=excluded).encode()).hexdigest()
    existing = db.scalar(
        select(WorkspaceResource).where(
            WorkspaceResource.workspace_id == data.workspace_id,
            WorkspaceResource.kind == KIND,
            WorkspaceResource.resource_key == data.request_key,
        )
    )
    if existing:
        if existing.payload.get("creationFingerprint") != fingerprint:
            raise HTTPException(409, "Este pedido já foi usado para outro conteúdo.")
        return out(existing)
    workspace = db.get(Workspace, data.workspace_id)
    payload = {
        **data.model_dump(by_alias=True, exclude={"request_key"}),
        "schemaVersion": "clicko.studio-project.v1",
        "revision": 1,
        "brandName": workspace.name,
        "directions": directions(data),
        "directionId": None,
        "documentId": None,
        "jobId": None,
        "status": "direction",
        "createdAt": now(),
        "updatedAt": now(),
        "creationFingerprint": fingerprint,
        "planningBasis": "Esboço de template derivado do briefing. Pesquisa do produto e copy exigem preparação e revisão.",
        "casting": casting,
    }
    row = WorkspaceResource(
        id=str(uuid4()),
        workspace_id=data.workspace_id,
        kind=KIND,
        resource_key=data.request_key,
        payload=payload,
        created_by=user.id,
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(
            select(WorkspaceResource).where(
                WorkspaceResource.workspace_id == data.workspace_id,
                WorkspaceResource.kind == KIND,
                WorkspaceResource.resource_key == data.request_key,
            )
        )
        if existing and existing.payload.get("creationFingerprint") == fingerprint:
            return out(existing)
        raise HTTPException(409, "O pedido já foi criado. Recarregue o projeto.") from None
    db.refresh(row)
    return out(row)


@router.get("/{project_id}")
def get_project(project_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return out(owned(db, user, project_id))


@router.patch("/{project_id}")
def select_direction(
    project_id: str, data: ProjectChange, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    row = owned(db, user, project_id)
    if row.payload.get("documentId") or row.payload.get("status") == "producing":
        raise HTTPException(409, "Crie outro projeto para explorar uma nova direção sem alterar a entrega existente.")
    return out(change(db, row, data.expected_revision, {"directionId": data.direction_id}))


@router.post("/{project_id}/appearance/plan")
def plan_appearance(
    project_id: str, data: AppearancePlanRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    from ..services.studios.project_appearance import plan_project_appearance

    row = owned(db, user, project_id)
    if row.payload.get("revision") != data.expected_revision:
        raise HTTPException(409, detail={"code": "studio_project_conflict"})
    if row.payload.get("status") == "producing":
        raise HTTPException(409, detail={"code": "appearance_project_producing"})
    try:
        return plan_project_appearance(db, row, data.direction, seed=data.seed)
    except ValueError as error:
        raise studio_identity_error(error) from error


@router.get("/{project_id}/appearance")
def get_appearance(project_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    from ..domain.studios.appearance_image import PROVIDER
    from ..models import StudioGenerationJob
    from ..services.studios.jobs import job_out
    from ..services.studios.project_appearance import admitted_provider

    row = owned(db, user, project_id)
    job = db.scalar(
        select(StudioGenerationJob)
        .where(
            StudioGenerationJob.workspace_id == row.workspace_id,
            StudioGenerationJob.job_type == "appearance_image",
            StudioGenerationJob.correlation_id == f"department-appearance:{row.id}",
        )
        .order_by(StudioGenerationJob.created_at.desc(), StudioGenerationJob.id.desc())
        .limit(1)
    )
    try:
        admitted_provider(db, PROVIDER)
        availability = {"available": True, "reason": None}
    except ValueError as error:
        availability = {"available": False, "reason": str(error)}
    return {
        "job": job_out(job) if job else None,
        "selection": row.payload.get("appearanceSelection"),
        "availability": availability,
    }


@router.post("/{project_id}/appearance/select")
def select_appearance(
    project_id: str, data: AppearanceSelection, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    from ..models import StudioGenerationJob
    from ..services.studios.project_appearance import plan_project_appearance, selected_appearance_asset

    row = owned(db, user, project_id)
    if (
        row.payload.get("revision") != data.expected_revision
        or row.payload.get("documentId")
        or row.payload.get("status") == "producing"
    ):
        raise HTTPException(409, detail={"code": "studio_project_conflict"})
    job = db.get(StudioGenerationJob, data.job_id)
    if (
        not job
        or job.workspace_id != row.workspace_id
        or job.job_type != "appearance_image"
        or job.correlation_id != f"department-appearance:{row.id}"
        or job.status != "succeeded"
    ):
        raise HTTPException(404, detail={"code": "appearance_result_unavailable"})
    plan = (job.request_payload or {}).get("plan") or {}
    request = plan.get("request") or {}
    try:
        if plan_project_appearance(db, row, request.get("direction"), seed=request.get("seed", 0)) != plan:
            raise ValueError("appearance_project_plan_changed")
        selection = {"jobId": job.id, "assetId": (job.result_payload or {}).get("assetId"), "plan": plan}
        selected_appearance_asset(db, row, selection)
        return out(change(db, row, data.expected_revision, {"appearanceSelection": selection}))
    except ValueError as error:
        raise studio_identity_error(error) from error


@router.post("/{project_id}/appearance", status_code=202)
def generate_appearance(
    project_id: str,
    data: AppearanceGenerationRequest,
    request: Request,
    idempotency_key: str = Header(min_length=8, max_length=160),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from ..config import get_settings
    from ..domain.studios.appearance_image import PROVIDER
    from ..domain.studios.contracts import CreateGenerationJobRequest
    from ..services.studios.jobs import create_job, enqueue_job_task, job_out
    from ..services.studios.project_appearance import plan_project_appearance
    from ..tasks import execute_studio_generation

    row = owned(db, user, project_id)
    if row.payload.get("revision") != data.expected_revision or row.payload.get("status") == "producing":
        raise HTTPException(409, detail={"code": "studio_project_conflict"})
    try:
        plan = plan_project_appearance(db, row, data.direction, seed=data.seed)
        if plan["planDigestSha256"] != data.plan_digest_sha256:
            raise HTTPException(409, detail={"code": "appearance_project_plan_changed"})
        admission = getattr(request.state, "studio_media_admission", None)
        payload = {"plan": plan, **({"commercialAdmission": admission} if admission else {})}
        job, created = create_job(
            db,
            CreateGenerationJobRequest(
                workspace_id=row.workspace_id,
                job_type="appearance_image",
                provider=PROVIDER,
                identity_version_id=plan["casting"]["identity"]["id"],
                voice_version_id=(plan["casting"].get("voice") or {}).get("id"),
                consent_grant_id=plan["casting"]["identity"].get("consentGrantId"),
                request=payload,
                correlation_id=f"department-appearance:{row.id}",
            ),
            idempotency_key,
            user,
            trusted_appearance_envelope=True,
            commercial_admission=admission,
        )
        if created:
            try:
                enqueue_job_task(
                    execute_studio_generation,
                    job,
                    isolated_queues_enabled=get_settings().studio_isolated_queues_enabled,
                )
            except Exception as error:
                db.refresh(job)
                if job.status == "queued":
                    job.status, job.error_code, job.error_message = "failed", "queue_unavailable", type(error).__name__
                    job.finished_at = datetime.now(UTC)
                    db.commit()
        return job_out(job)
    except ValueError as error:
        db.rollback()
        raise studio_identity_error(error) from error


def document_request(project, post_id, brand_revision, asset=None, portrait=None):
    direction = next(d for d in project["directions"] if d["id"] == project["directionId"])
    texts = [(direction["opening"], project["objective"])]
    if project["format"] == "carousel":
        texts += [("O contexto", project["evidence"] or project["objective"]), ("O próximo passo", direction["cta"])]
    pages = []
    duration_ms = None
    if project["format"] == "video":
        avatar_result = ((asset.object_metadata or {}).get("avatarVideoJobResult") or {}) if asset else {}
        duration_ms = (project.get("montagePlan") or {}).get("durationMs") or (avatar_result.get("avatar") or {}).get(
            "durationMs", 5000
        )
    for i, (title, body) in enumerate(texts):
        pages.append(
            {
                "id": f"page-{i + 1}",
                "width": 1080,
                "height": 1350,
                "background": "#e8e5dc",
                "durationMs": duration_ms,
                "layers": [
                    {
                        "id": f"brand-{i}",
                        "kind": "text",
                        "width": 900,
                        "height": 70,
                        "x": 75,
                        "y": 80,
                        "properties": {"text": project["brandName"], "fontSize": 30, "color": "#334031"},
                    },
                    {
                        "id": f"headline-{i}",
                        "kind": "text",
                        "width": 900,
                        "height": 400,
                        "x": 75,
                        "y": 220,
                        "properties": {"text": title, "fontSize": 64, "color": "#253224"},
                    },
                    {
                        "id": f"body-{i}",
                        "kind": "text",
                        "width": 900,
                        "height": 500,
                        "x": 75,
                        "y": 670,
                        "properties": {"text": body, "fontSize": 32, "color": "#334031"},
                    },
                ],
            }
        )
    if asset and project["format"] != "video":
        for page in pages:
            generated_scene = bool(project.get("appearanceSelection"))
            page["layers"].append(
                {
                    "id": "source-material",
                    "kind": "image",
                    "width": 600 if generated_scene else 420,
                    "height": 600 if generated_scene else 360,
                    "x": 405 if generated_scene else 585,
                    "y": 690 if generated_scene else 940,
                    "zIndex": 1,
                    "properties": {"assetId": asset.id},
                }
            )
            if generated_scene:
                next(layer for layer in page["layers"] if layer["id"].startswith("body-"))["width"] = 300
    if portrait:
        for page in pages:
            page["layers"].append(
                {
                    "id": "cast-portrait",
                    "kind": "image",
                    "width": 400,
                    "height": 500,
                    "x": 605,
                    "y": 775,
                    "zIndex": 2,
                    "properties": {"assetId": portrait.id},
                }
            )
            next(layer for layer in page["layers"] if layer["id"].startswith("body-"))["width"] = 470
    material = {item.id: item for item in (asset, portrait) if item}
    return CreateStudioDocumentRequest.model_validate(
        {
            "workspaceId": project["workspaceId"],
            "title": project["title"],
            "postId": post_id,
            "campaignId": project.get("campaignId"),
            "brandRevision": brand_revision,
            "contentType": "visual" if project["format"] == "image" else project["format"],
            "engine": "filmcraft" if project["format"] == "video" else "photocraft",
            "brief": {
                "objective": project["objective"],
                "audience": project["audience"],
                "hook": direction["opening"],
                "angle": direction["rationale"][:1000],
                "tone": project["tone"],
                "format": project["format"],
                "cta": direction["cta"],
                "restrictions": ["Não inventar resultados, depoimentos ou condições comerciais."],
            },
            "assets": [
                {"id": item.id, "mediaType": item.media_type, "checksum": item.checksum_sha256}
                for item in material.values()
            ],
            "identityRef": project.get("casting", {}).get("identity"),
            "voiceRef": project.get("casting", {}).get("voice"),
            "composition": {
                "pages": pages,
                "tracks": [],
                "mediaTimeline": (project.get("montagePlan") or {}).get("timeline"),
                "narrative": {
                    "departmentProjectId": project["id"],
                    "front": project["front"],
                    "intent": project["intent"],
                    "direction": direction,
                    **({"montage": project["montagePlan"]} if project.get("montagePlan") else {}),
                },
            },
        }
    )


@router.post("/{project_id}/produce")
def produce_project(
    project_id: str, data: ProductionRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    row = owned(db, user, project_id)
    try:
        resolve_cast(db, row.workspace_id, row.payload.get("identityVersionId"), row.payload.get("voiceVersionId"))
    except ValueError as error:
        raise studio_identity_error(error) from error
    if not row.payload.get("directionId"):
        raise HTTPException(422, "Escolha uma direção editorial primeiro.")
    if row.payload.get("jobId"):
        if row.payload["revision"] != data.expected_revision:
            raise HTTPException(409, "Recarregue o projeto antes de continuar.")
        existing_layout = (
            "picture_in_picture"
            if (row.payload.get("montagePlan") or {}).get("mode") == "picture_in_picture"
            else "sequential"
        )
        if existing_layout != data.presentation_layout:
            raise HTTPException(409, "A entrega já foi criada com outra composição.")
        return out(row)
    if row.payload.get("status") == "producing":
        started = datetime.fromisoformat(row.payload["updatedAt"])
        if (datetime.now(UTC) - started).total_seconds() < 600:
            raise HTTPException(409, "A preparação está em andamento. Recarregue para acompanhar.")
    validate_references(
        db,
        row.workspace_id,
        campaign_id=row.payload.get("campaignId"),
        post_id=row.payload.get("postId"),
        asset_ids=[row.payload["sourceAssetId"]] if row.payload.get("sourceAssetId") else [],
    )
    voiceover = (
        row.payload["format"] == "video"
        and row.payload.get("voiceVersionId")
        and not row.payload.get("identityVersionId")
    )
    narration_audio = None
    asset = db.get(LibraryAsset, row.payload["sourceAssetId"]) if row.payload.get("sourceAssetId") else None
    if asset and (
        not asset.storage_key
        or not (asset.media_type or "").startswith(
            ("video/", "image/") if voiceover else "video/" if row.payload["format"] == "video" else "image/"
        )
    ):
        raise HTTPException(422, "Escolha um material armazenado e compatível com o formato.")
    additional_video = None
    portrait = None
    original_image = None
    if row.payload.get("identityVersionId") or row.payload.get("voiceVersionId"):
        if row.payload["format"] == "video" and not voiceover:
            from ..services.studios.project_avatar import completed_asset

            try:
                avatar = completed_asset(db, row)
            except ValueError as error:
                raise studio_identity_error(error) from error
            if not avatar:
                raise HTTPException(
                    422, "Conclua e revise a apresentação com a aparência e a voz escolhidas antes da montagem."
                )
            # The presenter leads the montage; an existing brand video remains
            # a separate native clip instead of being silently discarded.
            additional_video, asset = asset, avatar
        elif row.payload.get("identityVersionId"):
            from ..models import StudioIdentityVersion

            version = db.get(StudioIdentityVersion, row.payload["identityVersionId"])
            if row.payload.get("appearanceSelection"):
                from ..services.studios.project_appearance import selected_appearance_asset

                try:
                    original_image = asset
                    asset = selected_appearance_asset(db, row, row.payload["appearanceSelection"])
                except ValueError as error:
                    raise studio_identity_error(error) from error
            else:
                portrait = next(
                    (
                        item
                        for asset_id in version.sample_asset_ids
                        if (item := db.get(LibraryAsset, asset_id))
                        and item.workspace_id == row.workspace_id
                        and item.lifecycle_status == "active"
                        and item.storage_key
                        and (item.media_type or "").startswith("image/")
                        and item.checksum_sha256
                    ),
                    None,
                )
            if not portrait and not row.payload.get("appearanceSelection"):
                raise HTTPException(422, "A versão escolhida precisa de uma imagem de referência armazenada.")
    if row.payload["format"] == "video" and not asset:
        raise HTTPException(
            422,
            "Selecione uma imagem ou um vídeo da biblioteca para narrar."
            if voiceover
            else "Selecione um vídeo da biblioteca para preparar a primeira montagem.",
        )
    preparation = {"status": "producing"}
    if data.presentation_layout == "picture_in_picture" and (
        row.payload["format"] != "video"
        or voiceover
        or not row.payload.get("identityVersionId")
        or not additional_video
    ):
        raise HTTPException(422, detail={"code": "presenter_overlay_requires_brand_video_and_avatar"})
    if row.payload["format"] == "video":
        try:
            if voiceover:
                montage, narration_audio = plan_voiceover(db, row, asset)
            elif data.presentation_layout == "picture_in_picture":
                from ..services.studios.project_presenter_overlay import plan_presenter_overlay

                montage = plan_presenter_overlay(row.workspace_id, additional_video, asset)
            else:
                montage = plan_video_montage(
                    row.workspace_id,
                    [clip for clip in (asset, additional_video) if clip],
                    avatar_asset_id=asset.id if row.payload.get("avatar") else None,
                )
        except ValueError as error:
            raise studio_identity_error(error) from error
        if row.payload.get("documentId") and row.payload.get("montagePlan") != montage:
            raise HTTPException(409, "Os materiais da montagem mudaram. Preserve a entrega anterior em outro projeto.")
        preparation["montagePlan"] = montage
    row = change(db, row, data.expected_revision, preparation)
    try:
        project = out(row)
        post_id = project.get("postId") or str(uuid5(NAMESPACE_URL, f"clicko-department:{project_id}"))
        if not db.get(Post, post_id):
            db.add(
                Post(
                    id=post_id,
                    workspace_id=row.workspace_id,
                    title=project["title"],
                    platform="instagram",
                    format="video"
                    if project["format"] == "video"
                    else "carousel"
                    if project["format"] == "carousel"
                    else "post",
                    copy=project["objective"],
                    hashtags=[],
                    status="draft",
                    author=user.name,
                    campaign_id=project.get("campaignId"),
                    objective=project["objective"],
                    origin="manual",
                )
            )
            db.flush()
        brand = db.scalar(select(BrandProfile).where(BrandProfile.workspace_id == row.workspace_id))
        if not brand:
            raise ValueError("Configure o contexto da marca antes de produzir.")
        request = document_request(project, post_id, brand_readiness(brand)["revision"], asset, portrait)
        for extra in (additional_video, narration_audio, original_image):
            if not extra:
                continue
            request.assets.append(
                AssetReferenceV1(
                    id=extra.id,
                    media_type=extra.media_type,
                    checksum=extra.checksum_sha256,
                )
            )
        document = create_document(db, request, user, creation_key=f"department:{project_id}")
        # Save the recoverable document before calling any runtime or queue.
        row = change(db, row, row.payload["revision"], {"documentId": document.id, "postId": post_id})
        contract = record_to_contract(document)
        if not contract.native_editor_state:
            craft.migrate(
                db,
                document,
                CraftMigrationRequestV1(engine=request.engine, expected_revision=document.revision),
                user,
                f"department-migrate:{project_id}",
            )
        db.refresh(document)
        if project["format"] == "video" and project["montagePlan"].get("mode") != "picture_in_picture":
            # Import is an idempotent native operation; a retry never duplicates the clip.
            if not row.payload.get("sourceRevision"):
                row = change(db, row, row.payload["revision"], {"sourceRevision": document.revision})
            craft.commands(
                db,
                document,
                CraftCommandRequestV1(
                    expected_revision=row.payload["sourceRevision"],
                    commands=native_voiceover_commands(project["montagePlan"])
                    if voiceover
                    else native_imports(project["montagePlan"]),
                    label="Montagem com a voz escolhida" if voiceover else "Primeira montagem com material da marca",
                ),
                user,
                f"department-source:{project_id}",
            )
            db.refresh(document)
        output = {"video": "mp4", "carousel": "png_set", "image": "png"}[project["format"]]
        job = render_job(
            document.id,
            CraftRenderRequestV1(expected_revision=document.revision, format=output),
            f"department-render:{project_id}:{document.revision}",
            db,
            user,
        )
        row = change(db, row, row.payload["revision"], {"jobId": job.id, "status": "delivery"})
        return out(row)
    except (ValueError, HTTPException) as error:
        db.rollback()
        db.refresh(row)
        queue_job = (
            error.detail.get("jobId") if isinstance(error, HTTPException) and isinstance(error.detail, dict) else None
        )
        change(
            db,
            row,
            row.payload["revision"],
            {"status": "production_failed", **({"jobId": queue_job} if queue_job else {})},
        )
        if isinstance(error, HTTPException):
            raise
        raise HTTPException(422, str(error)) from error
