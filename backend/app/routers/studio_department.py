"""Persistent client-facing creative department; native production stays in Craft."""

from datetime import UTC, datetime
from hashlib import sha256
from typing import Literal
from uuid import NAMESPACE_URL, uuid4, uuid5

from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..domain.studios.contracts import CreateStudioDocumentRequest, StudioContract
from ..domain.studios.craft import CraftCommandRequestV1, CraftMigrationRequestV1, CraftRenderRequestV1
from ..models import BrandProfile, LibraryAsset, Post, User, Workspace, WorkspaceResource
from ..security import get_current_user
from ..services.brand import brand_readiness
from ..services.studios import craft
from ..services.studios.compatibility import record_to_contract
from ..services.studios.kernel import create_document
from .studio_craft import render_job
from .studios import assert_access, validate_references

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


class ProjectChange(StudioContract):
    expected_revision: int = Field(ge=1)
    direction_id: Literal["guide", "demonstrate"]


class ProductionRequest(StudioContract):
    expected_revision: int = Field(ge=1)


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
    fingerprint = sha256(data.model_dump_json(exclude={"request_key"}).encode()).hexdigest()
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
        "planningBasis": "Pesquisa editorial aplicada ao pedido; esboço sem geração por LLM.",
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


def document_request(project, post_id, brand_revision, asset=None):
    direction = next(d for d in project["directions"] if d["id"] == project["directionId"])
    texts = [(direction["opening"], project["objective"])]
    if project["format"] == "carousel":
        texts += [("O contexto", project["evidence"] or project["objective"]), ("O próximo passo", direction["cta"])]
    pages = []
    for i, (title, body) in enumerate(texts):
        pages.append(
            {
                "id": f"page-{i + 1}",
                "width": 1080,
                "height": 1350,
                "background": "#e8e5dc",
                "durationMs": 5000 if project["format"] == "video" else None,
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
            page["layers"].append(
                {
                    "id": "source-material",
                    "kind": "image",
                    "width": 420,
                    "height": 360,
                    "x": 585,
                    "y": 940,
                    "zIndex": 1,
                    "properties": {"assetId": asset.id},
                }
            )
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
            "assets": [{"id": asset.id, "mediaType": asset.media_type, "checksum": asset.checksum_sha256}]
            if asset
            else [],
            "composition": {
                "pages": pages,
                "tracks": [],
                "narrative": {
                    "departmentProjectId": project["id"],
                    "front": project["front"],
                    "intent": project["intent"],
                    "direction": direction,
                },
            },
        }
    )


@router.post("/{project_id}/produce")
def produce_project(
    project_id: str, data: ProductionRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    row = owned(db, user, project_id)
    if not row.payload.get("directionId"):
        raise HTTPException(422, "Escolha uma direção editorial primeiro.")
    if row.payload.get("jobId"):
        if row.payload["revision"] != data.expected_revision:
            raise HTTPException(409, "Recarregue o projeto antes de continuar.")
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
    asset = db.get(LibraryAsset, row.payload["sourceAssetId"]) if row.payload.get("sourceAssetId") else None
    if asset and (
        not asset.storage_key
        or not (asset.media_type or "").startswith("video/" if row.payload["format"] == "video" else "image/")
    ):
        raise HTTPException(422, "Escolha um material armazenado e compatível com o formato.")
    if row.payload["format"] == "video" and not asset:
        raise HTTPException(422, "Selecione um vídeo da biblioteca para preparar a primeira montagem.")
    row = change(db, row, data.expected_revision, {"status": "producing"})
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
        request = document_request(project, post_id, brand_readiness(brand)["revision"], asset)
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
        if project["format"] == "video":
            # Import is an idempotent native operation; a retry never duplicates the clip.
            if not row.payload.get("sourceRevision"):
                row = change(db, row, row.payload["revision"], {"sourceRevision": document.revision})
            craft.commands(
                db,
                document,
                CraftCommandRequestV1(
                    expected_revision=row.payload["sourceRevision"],
                    commands=[{"id": "asset.import", "params": {"assetId": asset.id, "addToTimeline": True}}],
                    label="Primeira montagem com material da marca",
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
