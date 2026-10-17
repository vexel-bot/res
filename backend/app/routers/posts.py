from datetime import UTC, datetime
from difflib import SequenceMatcher
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ApprovalEvent, Campaign, FeedbackEvent, Membership, Post, PostMetricSnapshot, User, utcnow
from ..schemas import (
    ApprovalActionIn,
    ApprovalActionOut,
    ApprovalEventOut,
    PostFeedbackIn,
    PostIn,
    PostMetricsIn,
    PostMetricSnapshotOut,
    PostOut,
    PostUpdate,
)
from ..security import get_current_user
from ..serializers import post_out

router = APIRouter(prefix="/posts", tags=["posts"])
EDITORIAL_FIELDS = {"title", "platform", "format", "copy", "hashtags", "image_url", "video_url", "slides"}


def assert_valid_schedule(status_value: str, scheduled_at: datetime | None) -> None:
    if status_value != "scheduled":
        return
    if scheduled_at is None:
        raise HTTPException(status_code=422, detail="Scheduled content requires a publication date")
    comparable = scheduled_at if scheduled_at.tzinfo else scheduled_at.replace(tzinfo=UTC)
    if comparable <= datetime.now(UTC):
        raise HTTPException(status_code=422, detail="Scheduled content requires a future publication date")


def assert_access(db: Session, user_id: str, workspace_id: str) -> None:
    if not db.scalar(
        select(Membership.id).where(Membership.user_id == user_id, Membership.workspace_id == workspace_id)
    ):
        raise HTTPException(status_code=404, detail="Workspace not found")


def owned_post(db: Session, user_id: str, post_id: str) -> Post:
    post = db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    assert_access(db, user_id, post.workspace_id)
    return post


def assert_campaign_links(db: Session, workspace_id: str, campaign_id: str | None, strategy_id: str | None) -> None:
    for linked_id in {value for value in (campaign_id, strategy_id) if value}:
        if not db.scalar(select(Campaign.id).where(Campaign.id == linked_id, Campaign.workspace_id == workspace_id)):
            raise HTTPException(status_code=422, detail="Campaign link does not belong to workspace")


def linked_opportunity_id(db: Session, campaign_id: str | None) -> str | None:
    if not campaign_id:
        return None
    return db.scalar(select(Campaign.opportunity_id).where(Campaign.id == campaign_id))


def snapshot(post: Post, label: str, number: int | None = None) -> dict:
    versions = post.versions or []
    return {
        "id": str(uuid4()),
        "number": number or max((int(item.get("number", 0)) for item in versions), default=0) + 1,
        "label": label,
        "author": post.author,
        "createdAt": utcnow().isoformat(),
        "title": post.title,
        "platform": post.platform,
        "format": post.format,
        "copy": post.copy,
        "hashtags": post.hashtags or [],
        "imageUrl": post.image_url,
        "videoUrl": post.video_url,
        "slides": post.slides,
    }


def feedback_event(post: Post, user_id: str, event_type: str, *, reason: str | None = None, payload=None):
    return FeedbackEvent(
        workspace_id=post.workspace_id,
        opportunity_id=None,
        campaign_id=post.campaign_id,
        content_id=post.id,
        user_id=user_id,
        event_type=event_type,
        reason=reason,
        payload=payload or {},
    )


def approval_event(post: Post, user: User, event_type: str, action: str, detail: str) -> ApprovalEvent:
    return ApprovalEvent(
        workspace_id=post.workspace_id,
        post_id=post.id,
        actor_id=user.id,
        actor_name=user.name,
        event_type=event_type,
        action=action,
        detail=detail,
    )


@router.get("", response_model=list[PostOut])
def list_posts(
    workspace_id: str = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[PostOut]:
    assert_access(db, user.id, workspace_id)
    posts = db.scalars(select(Post).where(Post.workspace_id == workspace_id).order_by(Post.created_at.desc())).all()
    return [post_out(item) for item in posts]


@router.get("/approval-events", response_model=list[ApprovalEventOut])
def list_approval_events(
    workspace_id: str = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ApprovalEvent]:
    assert_access(db, user.id, workspace_id)
    return list(
        db.scalars(
            select(ApprovalEvent).where(ApprovalEvent.workspace_id == workspace_id).order_by(ApprovalEvent.created_at)
        ).all()
    )


@router.post("", response_model=PostOut, status_code=status.HTTP_201_CREATED)
def create_post(
    data: PostIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PostOut:
    assert_access(db, user.id, data.workspace_id)
    assert_campaign_links(db, data.workspace_id, data.campaign_id, data.strategy_id)
    assert_valid_schedule(data.status, data.scheduled_at)
    values = data.model_dump(exclude={"versions"})
    post = Post(**values, versions=[])
    db.add(post)
    db.flush()
    post.versions = [snapshot(post, "Versão inicial", 1)]
    event_type = "generated" if data.origin and data.origin != "manual" else "created"
    event = feedback_event(post, user.id, event_type, payload={"origin": data.origin or "manual"})
    event.opportunity_id = linked_opportunity_id(db, post.campaign_id)
    db.add(event)
    db.commit()
    db.refresh(post)
    return post_out(post)


@router.patch("/{post_id}", response_model=PostOut)
def update_post(
    post_id: str,
    data: PostUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PostOut:
    post = owned_post(db, user.id, post_id)
    requested = data.model_dump(exclude_unset=True, exclude={"versions"})
    assert_campaign_links(
        db,
        post.workspace_id,
        requested.get("campaign_id", post.campaign_id),
        requested.get("strategy_id", post.strategy_id),
    )
    changes = {field: value for field, value in requested.items() if getattr(post, field) != value}
    resulting_status = changes.get("status", post.status)
    resulting_schedule = changes.get("scheduled_at", post.scheduled_at)
    assert_valid_schedule(resulting_status, resulting_schedule)
    previous_copy = post.copy
    previous_status = post.status
    for field, value in changes.items():
        setattr(post, field, value)
    editorial_changes = sorted(EDITORIAL_FIELDS & changes.keys())
    if editorial_changes:
        versions = list(post.versions or [])
        versions.append(snapshot(post, "Edição salva"))
        post.versions = versions[-50:]
        copy_intensity = 1.0 - SequenceMatcher(None, previous_copy, post.copy).ratio() if "copy" in changes else 0.0
        field_intensity = len(editorial_changes) / len(EDITORIAL_FIELDS)
        event = feedback_event(
            post,
            user.id,
            "edited",
            payload={
                "changedFields": editorial_changes,
                "copyEditIntensity": round(copy_intensity, 4),
                "editIntensity": round(max(copy_intensity, field_intensity), 4),
            },
        )
        event.opportunity_id = linked_opportunity_id(db, post.campaign_id)
        db.add(event)
    if post.status != previous_status:
        event_type = {
            "approved": "approved",
            "rejected": "discarded",
            "published": "published",
        }.get(post.status, "status_changed")
        event = feedback_event(
            post,
            user.id,
            event_type,
            payload={
                "from": previous_status,
                "to": post.status,
                "scheduledAt": post.scheduled_at.isoformat() if post.scheduled_at else None,
            },
        )
        event.opportunity_id = linked_opportunity_id(db, post.campaign_id)
        db.add(event)
        db.add(
            approval_event(
                post,
                user,
                "action",
                "status_changed",
                f"Status alterado de {previous_status} para {post.status}",
            )
        )
    db.commit()
    db.refresh(post)
    return post_out(post)


@router.post("/{post_id}/approval-actions", response_model=ApprovalActionOut)
def apply_approval_action(
    post_id: str,
    data: ApprovalActionIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ApprovalActionOut:
    post = owned_post(db, user.id, post_id)
    if data.action == "comment":
        event = approval_event(post, user, "comment", "comment", data.comment.strip())
        db.add(event)
        db.commit()
        db.refresh(event)
        return ApprovalActionOut(post=post_out(post), event=ApprovalEventOut.model_validate(event))

    status_map = {
        "approve": "approved",
        "request_changes": "changes_requested",
        "reject": "rejected",
        "publish": "published",
        "schedule": "scheduled",
    }
    allowed_from = {
        "approve": {"draft", "in_review", "pending_approval", "changes_requested"},
        "request_changes": {"in_review", "pending_approval", "approved"},
        "reject": {"draft", "in_review", "pending_approval", "approved"},
        "publish": {"approved", "scheduled"},
        "schedule": {"approved", "scheduled"},
    }
    if post.status not in allowed_from[data.action]:
        raise HTTPException(status_code=409, detail=f"Action {data.action} is not valid from status {post.status}")
    previous_status = post.status
    post.status = status_map[data.action]
    if data.action == "schedule":
        post.scheduled_at = data.scheduled_at
    detail = (data.comment or "").strip() or f"Status alterado de {previous_status} para {post.status}"
    event = approval_event(post, user, "action", data.action, detail)
    feedback_type = {"approve": "approved", "reject": "discarded", "publish": "published"}.get(
        data.action, "status_changed"
    )
    feedback = feedback_event(
        post,
        user.id,
        feedback_type,
        reason=(data.comment or None),
        payload={
            "action": data.action,
            "from": previous_status,
            "to": post.status,
            "scheduledAt": post.scheduled_at.isoformat() if post.scheduled_at else None,
        },
    )
    feedback.opportunity_id = linked_opportunity_id(db, post.campaign_id)
    db.add_all([event, feedback])
    db.commit()
    db.refresh(post)
    db.refresh(event)
    return ApprovalActionOut(post=post_out(post), event=ApprovalEventOut.model_validate(event))


@router.post("/{post_id}/versions/{version_number}/restore", response_model=PostOut)
def restore_post_version(
    post_id: str,
    version_number: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PostOut:
    post = owned_post(db, user.id, post_id)
    version = next((item for item in post.versions or [] if int(item.get("number", 0)) == version_number), None)
    if not version:
        raise HTTPException(status_code=404, detail="Post version not found")
    mapping = {
        "title": "title",
        "platform": "platform",
        "format": "format",
        "copy": "copy",
        "hashtags": "hashtags",
        "imageUrl": "image_url",
        "videoUrl": "video_url",
        "slides": "slides",
    }
    for source, target in mapping.items():
        if source in version:
            setattr(post, target, version[source])
    versions = list(post.versions or [])
    versions.append(snapshot(post, f"Restaurada da versão {version_number}"))
    post.versions = versions[-50:]
    event = feedback_event(post, user.id, "edited", payload={"restoredVersion": version_number, "editIntensity": 1.0})
    event.opportunity_id = linked_opportunity_id(db, post.campaign_id)
    db.add(event)
    db.commit()
    db.refresh(post)
    return post_out(post)


@router.post("/{post_id}/metrics", response_model=PostMetricSnapshotOut, status_code=status.HTTP_201_CREATED)
def record_metrics(
    post_id: str,
    data: PostMetricsIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PostMetricSnapshot:
    post = owned_post(db, user.id, post_id)
    supplied = data.model_dump(exclude={"source", "observed_at"}, exclude_none=True)
    metrics = {**(post.metrics or {}), **supplied}
    metric_snapshot = PostMetricSnapshot(
        workspace_id=post.workspace_id,
        post_id=post.id,
        recorded_by=user.id,
        source=data.source,
        metrics=metrics,
        observed_at=data.observed_at or utcnow(),
    )
    post.metrics = metrics
    db.add(metric_snapshot)
    db.flush()
    event = feedback_event(
        post,
        user.id,
        "performance_recorded",
        payload={"snapshotId": metric_snapshot.id, "source": data.source, "metrics": metrics},
    )
    event.opportunity_id = linked_opportunity_id(db, post.campaign_id)
    db.add(event)
    db.commit()
    db.refresh(metric_snapshot)
    return metric_snapshot


@router.get("/{post_id}/metrics", response_model=list[PostMetricSnapshotOut])
def list_metrics(
    post_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[PostMetricSnapshot]:
    post = owned_post(db, user.id, post_id)
    return list(
        db.scalars(
            select(PostMetricSnapshot)
            .where(PostMetricSnapshot.post_id == post.id, PostMetricSnapshot.workspace_id == post.workspace_id)
            .order_by(PostMetricSnapshot.observed_at.desc())
        ).all()
    )


@router.post("/{post_id}/feedback", status_code=status.HTTP_204_NO_CONTENT)
def rate_post(
    post_id: str,
    data: PostFeedbackIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    post = owned_post(db, user.id, post_id)
    event = feedback_event(post, user.id, "rated", reason=data.reason, payload={"rating": data.rating})
    event.opportunity_id = linked_opportunity_id(db, post.campaign_id)
    db.add(event)
    db.commit()


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(
    post_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    post = owned_post(db, user.id, post_id)
    event = feedback_event(
        post,
        user.id,
        "discarded",
        reason="deleted",
        payload={"resourceId": post.id, "title": post.title},
    )
    # Preserve the learning event after deletion without relying on an insert/delete
    # ordering side effect for the content foreign key.
    event.content_id = None
    event.opportunity_id = linked_opportunity_id(db, post.campaign_id)
    db.add(event)
    db.delete(post)
    db.commit()
