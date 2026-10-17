from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import BrandProfile, Membership, Post, Workspace
from .schemas import BrandProfileOut, PostOut, WorkspaceOut


def brand_out(brand: BrandProfile) -> BrandProfileOut:
    return BrandProfileOut.model_validate(brand)


def workspace_out(db: Session, workspace: Workspace, user_id: str) -> WorkspaceOut:
    brand = workspace.brand_profile
    if not brand:
        raise RuntimeError(f"Workspace {workspace.id} has no brand profile")
    count = db.scalar(select(func.count(Membership.id)).where(Membership.workspace_id == workspace.id)) or 0
    role = db.scalar(
        select(Membership.role).where(Membership.workspace_id == workspace.id, Membership.user_id == user_id)
    )
    if not role:
        raise RuntimeError(f"User {user_id} has no membership in workspace {workspace.id}")
    return WorkspaceOut(
        id=workspace.id,
        name=workspace.name,
        avatar=workspace.avatar,
        plan=workspace.plan,
        members_count=count,
        role=role,
        brand_profile=brand_out(brand),
    )


def post_out(post: Post) -> PostOut:
    metrics = post.metrics or {}
    return PostOut(
        id=post.id,
        workspace_id=post.workspace_id,
        title=post.title,
        platform=post.platform,
        format=post.format,
        copy=post.copy,
        hashtags=post.hashtags or [],
        image_url=post.image_url,
        video_url=post.video_url,
        slides=post.slides,
        scheduled_at=post.scheduled_at,
        status=post.status,
        author=post.author,
        ai_score=post.ai_score,
        created_at=post.created_at,
        likes=metrics.get("likes"),
        comments=metrics.get("comments"),
        shares=metrics.get("shares"),
        reach=metrics.get("reach"),
        impressions=metrics.get("impressions"),
        saves=metrics.get("saves"),
        clicks=metrics.get("clicks"),
        conversions=metrics.get("conversions"),
        campaign_id=post.campaign_id,
        strategy_id=post.strategy_id,
        brain_revision=post.brain_revision,
        objective=post.objective,
        origin=post.origin,
        versions=post.versions or [],
    )
