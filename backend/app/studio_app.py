"""Studios from the upstream branch, authenticated by the current Clicko session."""

import logging
from contextlib import asynccontextmanager
from uuid import NAMESPACE_URL, uuid5

import jwt
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .config import get_settings
from .database import Base, engine, get_db
from .http_middleware import install_http_middleware
from .models import BrandProfile, CreativeDocument, LibraryAsset, Membership, User, Workspace, WorkspaceResource
from .routers import assets, health, internal_finance, studio_video
from .security import get_current_user
from .services.rate_limit import RedisRateLimiter
from .studio_bridge_key import bridge_secret
from .studio_routes import include_studio_routes


def bridge_claims(credentials: HTTPAuthorizationCredentials | None):
    if not credentials:
        raise HTTPException(401, "Sessão Clicko necessária.")
    try:
        payload = jwt.decode(
            credentials.credentials,
            bridge_secret(),
            algorithms=["HS256"],
            audience="clicko-studios",
            issuer="clicko-governance",
            options={"require": ["exp", "iat", "sub", "workspaceId", "module"]},
        )
        if payload.get("type") != "studio_bridge" or payload["module"] not in {"create-image", "create-video"}:
            raise ValueError("Invalid studio context")
        return payload
    except (jwt.InvalidTokenError, ValueError, KeyError) as exc:
        raise HTTPException(401, "Sessão Clicko inválida ou expirada.") from exc


def scoped_ids(claims):
    scope = f"clicko-studios:{claims['workspaceId']}:{claims.get('clientId') or ''}"
    return str(uuid5(NAMESPACE_URL, scope)), str(uuid5(NAMESPACE_URL, f"{scope}:user:{claims['sub']}"))


def bridge_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(HTTPBearer(auto_error=False)),
    db: Session = Depends(get_db),
):
    claims = bridge_claims(credentials)
    request.state.motion_gemini_experimental = (
        claims.get("motionGeminiExperimental") is True and claims["module"] == "create-video"
    )
    request.state.studio_media_admission = claims.get("mediaAdmission")
    workspace_id, user_id = scoped_ids(claims)
    if request.url.path.startswith("/api/v1/studios/v1/video/") and claims["module"] != "create-video":
        raise HTTPException(403, "Abra o Studio de Vídeo para esta operação.")
    # Format and engine selection cannot escalate an image-only account into Video.
    selected = getattr(request.state, "studio_body", {})
    if request.url.path.endswith("/editing-gemini-jobs"):
        raise HTTPException(410, detail={"code": "use_image_editing_jobs_endpoint"})
    if "/production-runs" in request.url.path and claims["module"] != "create-video":
        raise HTTPException(403, "Produções audiovisuais pertencem ao Studio de Vídeo.")
    generic_job_type = selected.get("jobType") or selected.get("job_type")
    if (
        request.url.path.rstrip("/") == "/api/v1/studios/v1/jobs"
        and request.method == "POST"
        and generic_job_type in {"scene_generation", "avatar_video"}
    ):
        raise HTTPException(422, detail={"code": "use_metered_media_endpoint"})
    if generic_job_type == "timeline_render" and claims["module"] != "create-video":
        raise HTTPException(403, "Esta operação pertence ao Studio de Vídeo.")
    if (
        request.url.path.rstrip("/") == "/api/v1/studios/v1/jobs"
        and request.method == "POST"
        and isinstance(generic_job_type, str)
        and generic_job_type in {"editing_gemini", "editing_ai"}
    ):
        job_request = selected.get("request")
        job_input = job_request.get("input") if isinstance(job_request, dict) else None
        operation = job_input.get("operation") if isinstance(job_input, dict) else None
        if isinstance(operation, str) and operation in {
            "generate_image",
            "edit_image",
            "generate_video",
            "edit_video",
            "plan",
        }:
            raise HTTPException(422, detail={"code": "use_image_editing_jobs_endpoint"})
    kind = selected.get("format") or selected.get("contentType") or selected.get("engine")
    parts = request.url.path.split("/")
    for segment, model in [("projects", WorkspaceResource), ("documents", CreativeDocument)]:
        if segment in parts and len(parts) > parts.index(segment) + 1:
            row = db.get(model, parts[parts.index(segment) + 1])
            if row and row.workspace_id == workspace_id:
                source = row.payload if isinstance(row, WorkspaceResource) else row.canonical_document or row.document
                kind = source.get("format") or source.get("contentType") or kind
    target = (
        "create-video"
        if kind in {"video", "presenter", "filmcraft", "effectcraft"}
        else "create-image"
        if kind in {"image", "visual", "carousel", "photocraft"}
        else None
    )
    if request.url.path.endswith("/editing-ai-jobs"):
        operation = selected.get("operation")
        if not isinstance(operation, str):
            operation = None
        operation_target = (
            "create-image"
            if operation in {"generate_image", "edit_image"}
            else "create-video"
            if operation in {"generate_video", "edit_video"}
            else None
        )
        if operation_target and operation_target != claims["module"]:
            raise HTTPException(403, "Abra a aba correspondente à operação de mídia solicitada.")
        if claims["module"] == "create-image" and operation not in {"generate_image", "edit_image"}:
            raise HTTPException(403, "Esta integração de Imagens aceita apenas criação e edição de imagens.")
        target = operation_target or target
    if target and target not in claims.get("allowedModules", [claims["module"]]):
        raise HTTPException(403, "Este formato não está liberado para este usuário.")
    # Session, capabilities and catalog load concurrently on first entry. Another
    # request may create the same deterministic identity before this one commits.
    for _attempt in range(3):
        try:
            user = db.get(User, user_id)
            if not user:
                user = User(
                    id=user_id,
                    email=f"{user_id}@studio.clicko.internal",
                    name=str(claims.get("name") or "Usuário")[:120],
                    password_hash="!session-bridge-only",
                )
                db.add(user)
            workspace = db.get(Workspace, workspace_id)
            if not workspace:
                workspace = Workspace(id=workspace_id, name=str(claims.get("workspaceName") or "Clicko")[:120])
                db.add(workspace)
                db.flush()
                db.add(BrandProfile(workspace_id=workspace_id, name=workspace.name, primary_color="#FF7F50"))
            membership = db.scalar(
                select(Membership).where(Membership.user_id == user_id, Membership.workspace_id == workspace_id)
            )
            role = claims.get("role") if claims.get("role") in {"Owner", "Admin"} else "Member"
            if not membership:
                db.add(Membership(user_id=user_id, workspace_id=workspace_id, role=role))
            else:
                membership.role = role
            db.commit()
            # Billing belongs to the SaaS account/member, not the client-specific
            # database partition derived above for document isolation.
            user._studio_billing_scope = {"workspaceId": str(claims["workspaceId"]), "userId": str(claims["sub"])}
            return user
        except IntegrityError:
            db.rollback()
    raise HTTPException(503, "Aguarde a preparação deste ambiente e tente novamente.")


@asynccontextmanager
async def lifespan(_app):
    get_settings().validate_for_startup()
    bridge_secret()
    if get_settings().environment in {"development", "test"}:
        Base.metadata.create_all(bind=engine)
    studio_video.recover_interrupted_local_jobs()
    yield


app = FastAPI(title="Clicko Studios", lifespan=lifespan)
app.dependency_overrides[get_current_user] = bridge_user
install_http_middleware(
    app, get_settings(), RedisRateLimiter(get_settings().redis_url), logging.getLogger("clicko.studios")
)


@app.middleware("http")
async def studio_body_context(request: Request, call_next):
    content_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
    # Mirror FastAPI's JSON decoding, including +json and absent Content-Type,
    # so changing transport headers cannot skip the module/quota-boundary guards.
    if (
        not content_type
        or content_type == "application/json"
        or (content_type.startswith("application/") and content_type.endswith("+json"))
    ):
        try:
            value = await request.json()
            request.state.studio_body = value if isinstance(value, dict) else {}
        except ValueError:
            request.state.studio_body = {}
    return await call_next(request)


include_studio_routes(app)
app.include_router(assets.router, prefix="/api/v1")
app.include_router(health.router)
app.include_router(internal_finance.router)


@app.get("/api/v1/studios/v1/bridge/session")
def session(user: User = Depends(bridge_user), db: Session = Depends(get_db)):
    membership = db.scalar(select(Membership).where(Membership.user_id == user.id))
    workspace = db.get(Workspace, membership.workspace_id)
    rows = db.scalars(select(LibraryAsset).where(LibraryAsset.workspace_id == workspace.id)).all()
    return {
        "user": {"id": user.id, "name": user.name},
        "workspace": {"id": workspace.id, "name": workspace.name},
        "assets": [assets.asset_out(row) for row in rows],
        "posts": [],
    }
