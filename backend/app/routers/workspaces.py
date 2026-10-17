from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import BrandProfile, Membership, User, Workspace
from ..schemas import BrandReadinessOut, BrandVersionOut, WorkspaceCreate, WorkspaceOut, WorkspaceUpdate
from ..security import get_current_user
from ..serializers import workspace_out
from ..services.brand import brand_profile_snapshot, brand_readiness

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


def membership_for(db: Session, user_id: str, workspace_id: str) -> Membership:
    membership = db.scalar(
        select(Membership).where(Membership.user_id == user_id, Membership.workspace_id == workspace_id)
    )
    if not membership:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return membership


@router.get("", response_model=list[WorkspaceOut])
def list_workspaces(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[WorkspaceOut]:
    workspaces = (
        db.scalars(
            select(Workspace).join(Membership).where(Membership.user_id == user.id).order_by(Workspace.created_at)
        )
        .unique()
        .all()
    )
    return [workspace_out(db, item, user.id) for item in workspaces]


@router.post("", response_model=WorkspaceOut, status_code=status.HTTP_201_CREATED)
def create_workspace(
    data: WorkspaceCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WorkspaceOut:
    workspace = Workspace(name=data.name.strip(), avatar="", plan="Growth")
    db.add(workspace)
    db.flush()
    db.add(Membership(user_id=user.id, workspace_id=workspace.id, role="Owner"))
    db.add(BrandProfile(workspace_id=workspace.id, name=workspace.name))
    db.commit()
    db.refresh(workspace)
    return workspace_out(db, workspace, user.id)


@router.patch("/{workspace_id}", response_model=WorkspaceOut)
def update_workspace(
    workspace_id: str,
    data: WorkspaceUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WorkspaceOut:
    membership = membership_for(db, user.id, workspace_id)
    if membership.role not in {"Owner", "Admin"}:
        raise HTTPException(status_code=403, detail="Insufficient workspace role")
    workspace = db.get(Workspace, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if data.name is not None:
        workspace.name = data.name.strip()
    if data.avatar is not None:
        workspace.avatar = data.avatar
    if data.brand_profile is not None:
        brand = workspace.brand_profile
        if not brand:
            brand = BrandProfile(workspace_id=workspace.id, name=workspace.name)
            db.add(brand)
        for field, value in data.brand_profile.model_dump().items():
            setattr(brand, field, value)
        versions = list(brand.versions or [])
        next_version = max((int(entry.get("number", 0)) for entry in versions), default=0) + 1
        versions.append(
            brand_profile_snapshot(
                brand,
                label=f"Revisão {next_version}",
                number=next_version,
            )
        )
        brand.versions = versions[-50:]
    db.commit()
    db.refresh(workspace)
    return workspace_out(db, workspace, user.id)


@router.get("/{workspace_id}/brand-readiness", response_model=BrandReadinessOut)
def get_brand_readiness(
    workspace_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    membership_for(db, user.id, workspace_id)
    brand = db.scalar(select(BrandProfile).where(BrandProfile.workspace_id == workspace_id))
    if not brand:
        raise HTTPException(status_code=404, detail="Brand profile not found")
    return brand_readiness(brand)


@router.get("/{workspace_id}/brand-versions", response_model=list[BrandVersionOut])
def list_brand_versions(
    workspace_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[dict]:
    membership_for(db, user.id, workspace_id)
    brand = db.scalar(select(BrandProfile).where(BrandProfile.workspace_id == workspace_id))
    if not brand:
        raise HTTPException(status_code=404, detail="Brand profile not found")
    return list(reversed(brand.versions or []))


@router.post("/{workspace_id}/brand-versions/{version_number}/restore", response_model=WorkspaceOut)
def restore_brand_version(
    workspace_id: str,
    version_number: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WorkspaceOut:
    membership = membership_for(db, user.id, workspace_id)
    if membership.role not in {"Owner", "Admin"}:
        raise HTTPException(status_code=403, detail="Insufficient workspace role")
    workspace = db.get(Workspace, workspace_id)
    if not workspace or not workspace.brand_profile:
        raise HTTPException(status_code=404, detail="Brand profile not found")
    brand = workspace.brand_profile
    version = next(
        (entry for entry in brand.versions or [] if int(entry.get("number", 0)) == version_number),
        None,
    )
    if not version:
        raise HTTPException(status_code=404, detail="Brand version not found")
    profile = version.get("profile") or {}
    restorable = {
        "name",
        "industry",
        "regions",
        "languages",
        "tone",
        "target_audience",
        "keywords",
        "do_and_donts",
        "primary_color",
        "products",
        "pillars",
        "watchlist",
        "prohibited_topics",
    }
    for field in restorable:
        if field in profile:
            setattr(brand, field, profile[field])
    versions = list(brand.versions or [])
    next_version = max((int(entry.get("number", 0)) for entry in versions), default=0) + 1
    versions.append(
        brand_profile_snapshot(
            brand,
            label=f"Restaurada da revisão {version_number}",
            number=next_version,
        )
    )
    brand.versions = versions[-50:]
    db.commit()
    db.refresh(workspace)
    return workspace_out(db, workspace, user.id)
