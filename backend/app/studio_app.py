"""Studios from the upstream branch, authenticated by the current Clicko session."""

import os
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import jwt
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .config import get_settings
from .models import BrandProfile, LibraryAsset, Membership, User, Workspace, WorkspaceResource, CreativeDocument
from .routers import assets, studio_craft, studio_department, studios
from .security import get_current_user


def bridge_secret():
    stored = get_settings().clicko_studios_bridge_secret
    configured = os.environ.get("CLICKO_STUDIOS_BRIDGE_SECRET") or (stored.get_secret_value() if stored else None)
    if configured:
        if len(configured) < 32:
            raise RuntimeError("STUDIOS_BRIDGE_KEY_INVALID")
        return configured
    filename = Path(__file__).resolve().parents[2] / ".clicko-data/studios/bridge-key"
    filename.parent.mkdir(parents=True, exist_ok=True)
    try:
        with filename.open("x", encoding="utf-8") as destination:
            destination.write(secrets.token_hex(48))
    except FileExistsError:
        pass
    value = filename.read_text(encoding="utf-8").strip()
    if len(value) < 32:
        raise RuntimeError("STUDIOS_BRIDGE_KEY_INVALID")
    return value


def bridge_claims(credentials: HTTPAuthorizationCredentials | None):
    if not credentials:
        raise HTTPException(401, "Sessão Clicko necessária.")
    try:
        payload = jwt.decode(
            credentials.credentials, bridge_secret(), algorithms=["HS256"],
            audience="clicko-studios", issuer="clicko-governance",
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
    workspace_id, user_id = scoped_ids(claims)
    # Format and engine selection cannot escalate an image-only account into Video.
    selected = getattr(request.state, "studio_body", {})
    kind = selected.get("format") or selected.get("contentType") or selected.get("engine")
    parts = request.url.path.split("/")
    for segment, model in [("projects", WorkspaceResource), ("documents", CreativeDocument)]:
        if segment in parts and len(parts) > parts.index(segment) + 1:
            row = db.get(model, parts[parts.index(segment) + 1])
            if row and row.workspace_id == workspace_id:
                source = row.payload if isinstance(row, WorkspaceResource) else row.canonical_document or row.document
                kind = source.get("format") or source.get("contentType") or kind
    target = "create-video" if kind in {"video", "presenter", "filmcraft", "effectcraft"} else "create-image" if kind in {"image", "carousel", "photocraft"} else None
    if target and target not in claims.get("allowedModules", [claims["module"]]):
        raise HTTPException(403, "Este formato não está liberado para este usuário.")
    user = db.get(User, user_id)
    if not user:
        user = User(id=user_id, email=f"{user_id}@studio.clicko.internal", name=str(claims.get("name") or "Usuário")[:120], password_hash="!session-bridge-only")
        db.add(user)
    workspace = db.get(Workspace, workspace_id)
    if not workspace:
        workspace = Workspace(id=workspace_id, name=str(claims.get("workspaceName") or "Clicko")[:120])
        db.add(workspace)
        db.flush()
        db.add(BrandProfile(workspace_id=workspace_id, name=workspace.name, primary_color="#FF7F50"))
    membership = db.scalar(select(Membership).where(Membership.user_id == user_id, Membership.workspace_id == workspace_id))
    role = claims.get("role") if claims.get("role") in {"Owner", "Admin"} else "Member"
    if not membership:
        db.add(Membership(user_id=user_id, workspace_id=workspace_id, role=role))
    else:
        membership.role = role
    db.commit()
    return user


@asynccontextmanager
async def lifespan(_app):
    bridge_secret()
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Clicko Studios", lifespan=lifespan)
app.dependency_overrides[get_current_user] = bridge_user


@app.middleware("http")
async def studio_body_context(request: Request, call_next):
    if request.headers.get("content-type", "").split(";")[0] == "application/json":
        try:
            value = await request.json()
            request.state.studio_body = value if isinstance(value, dict) else {}
        except ValueError:
            request.state.studio_body = {}
    return await call_next(request)

app.include_router(studios.router, prefix="/api/v1")
app.include_router(studio_craft.router, prefix="/api/v1")
app.include_router(studio_department.router, prefix="/api/v1")
app.include_router(assets.router, prefix="/api/v1")


@app.get("/health/ready")
def ready():
    return {"status": "ready", "service": "clicko-studios"}


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
