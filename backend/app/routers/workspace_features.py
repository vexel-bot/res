from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import require_workspace_access
from ..models import ApprovalEvent, AuditEvent, Membership, User, Workspace, WorkspaceResource
from ..schemas import (
    CompanySettingsIn,
    MemberInviteIn,
    MemberUpdateIn,
    PlanUpdateIn,
    SupportTicketIn,
    UserSettingsIn,
    WorkspaceResourceIn,
    WorkspaceResourceOut,
    WorkspaceResourceUpdate,
)
from ..security import get_current_user

router = APIRouter(tags=["workspace-features"])

MODULES = [
    "dashboard",
    "radar",
    "create-image",
    "create-video",
    "create-copy",
    "ai-chat",
    "templates",
    "connected-accounts",
    "workspace",
    "brain",
    "strategy",
    "studio",
    "library",
    "calendar",
    "automations",
    "analytics",
]
PLANS = [
    {
        "id": "solo",
        "name": "Solo",
        "maxUsers": 1,
        "monthlyPrice": None,
        "description": "Para uma operação individual.",
        "features": ["1 usuário", "Calendário e estúdio", "Uso de IA configurável"],
    },
    {
        "id": "team",
        "name": "Team",
        "maxUsers": 5,
        "monthlyPrice": None,
        "description": "Para equipes pequenas com aprovação.",
        "features": ["Até 5 usuários", "Aprovações e permissões", "Uso de IA configurável"],
    },
    {
        "id": "business",
        "name": "Business",
        "maxUsers": 15,
        "monthlyPrice": None,
        "description": "Para operações de conteúdo em escala.",
        "features": ["Até 15 usuários", "Automações", "Uso de IA configurável"],
    },
    {
        "id": "enterprise",
        "name": "Enterprise",
        "maxUsers": None,
        "monthlyPrice": None,
        "description": "Capacidade e governança personalizadas.",
        "features": ["Usuários personalizados", "Auditoria completa", "Suporte prioritário"],
    },
]
PLAN_BY_DB = {"Solo Creator": "solo", "Solo": "solo", "Growth": "team", "Pro": "business", "Enterprise": "enterprise"}
DB_BY_PLAN = {"solo": "Solo Creator", "team": "Growth", "business": "Pro", "enterprise": "Enterprise"}
PUBLIC_RESOURCE_KINDS = {
    "template",
    "connected_account",
    "automation",
    "video_project",
    "ai_chat",
    "presenter_session",
}


def now() -> datetime:
    return datetime.now(UTC)


def require_admin(membership: Membership) -> None:
    if membership.role not in {"Owner", "Admin"}:
        raise HTTPException(status_code=403, detail="Insufficient workspace role")


def audit(db: Session, workspace_id: str, user: User, action: str, resource: str, detail: str) -> None:
    db.add(
        AuditEvent(
            workspace_id=workspace_id,
            actor_id=user.id,
            actor_name=user.name,
            action=action,
            resource=resource,
            detail=detail,
        )
    )


def resource_for(db: Session, resource_id: str, workspace_id: str) -> WorkspaceResource:
    item = db.scalar(
        select(WorkspaceResource).where(
            WorkspaceResource.id == resource_id, WorkspaceResource.workspace_id == workspace_id
        )
    )
    if not item:
        raise HTTPException(status_code=404, detail="Resource not found")
    return item


def public_resource_for(db: Session, resource_id: str, workspace_id: str) -> WorkspaceResource:
    item = resource_for(db, resource_id, workspace_id)
    if item.kind not in PUBLIC_RESOURCE_KINDS:
        raise HTTPException(status_code=404, detail="Resource not found")
    return item


@router.get("/workspace-resources", response_model=list[WorkspaceResourceOut])
def list_resources(
    workspace_id: str = Query(),
    kind: str = Query(),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[WorkspaceResource]:
    require_workspace_access(workspace_id, db, user)
    if kind not in PUBLIC_RESOURCE_KINDS:
        raise HTTPException(status_code=400, detail="Unsupported resource kind")
    return list(
        db.scalars(
            select(WorkspaceResource)
            .where(WorkspaceResource.workspace_id == workspace_id, WorkspaceResource.kind == kind)
            .order_by(WorkspaceResource.updated_at.desc())
        ).all()
    )


@router.post("/workspace-resources", response_model=WorkspaceResourceOut, status_code=status.HTTP_201_CREATED)
def create_resource(
    data: WorkspaceResourceIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> WorkspaceResource:
    membership = require_workspace_access(data.workspace_id, db, user)
    if data.kind == "connected_account":
        require_admin(membership)
    existing = db.scalar(
        select(WorkspaceResource).where(
            WorkspaceResource.workspace_id == data.workspace_id,
            WorkspaceResource.kind == data.kind,
            WorkspaceResource.resource_key == data.resource_key,
        )
    )
    if existing:
        return existing
    item = WorkspaceResource(
        workspace_id=data.workspace_id,
        kind=data.kind,
        resource_key=data.resource_key,
        payload=data.payload,
        created_by=user.id,
    )
    db.add(item)
    audit(
        db,
        data.workspace_id,
        user,
        "created",
        data.kind,
        str(data.payload.get("name") or data.payload.get("title") or data.resource_key),
    )
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        existing = db.scalar(
            select(WorkspaceResource).where(
                WorkspaceResource.workspace_id == data.workspace_id,
                WorkspaceResource.kind == data.kind,
                WorkspaceResource.resource_key == data.resource_key,
            )
        )
        if existing:
            return existing
        raise HTTPException(status_code=409, detail="Resource key already exists") from error
    db.refresh(item)
    return item


@router.patch("/workspace-resources/{resource_id}", response_model=WorkspaceResourceOut)
def update_resource(
    resource_id: str,
    workspace_id: str,
    data: WorkspaceResourceUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WorkspaceResource:
    membership = require_workspace_access(workspace_id, db, user)
    item = public_resource_for(db, resource_id, workspace_id)
    if item.kind == "connected_account":
        require_admin(membership)
    item.payload = data.payload
    audit(
        db,
        workspace_id,
        user,
        "updated",
        item.kind,
        str(data.payload.get("name") or data.payload.get("title") or item.resource_key),
    )
    db.commit()
    db.refresh(item)
    return item


@router.delete("/workspace-resources/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resource(
    resource_id: str, workspace_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> None:
    membership = require_workspace_access(workspace_id, db, user)
    item = public_resource_for(db, resource_id, workspace_id)
    if item.kind == "connected_account":
        require_admin(membership)
    audit(
        db,
        workspace_id,
        user,
        "deleted",
        item.kind,
        str(item.payload.get("name") or item.payload.get("title") or item.resource_key),
    )
    db.delete(item)
    db.commit()


@router.get("/workspace-features/{workspace_id}/settings/me")
def get_settings(workspace_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    require_workspace_access(workspace_id, db, user)
    item = db.scalar(
        select(WorkspaceResource).where(
            WorkspaceResource.workspace_id == workspace_id,
            WorkspaceResource.kind == "user_settings",
            WorkspaceResource.resource_key == user.id,
        )
    )
    return item.payload if item else {"settings": {}, "auxiliary": {}}


@router.put("/workspace-features/{workspace_id}/settings/me")
def save_settings(
    workspace_id: str, data: UserSettingsIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> dict:
    require_workspace_access(workspace_id, db, user)
    item = db.scalar(
        select(WorkspaceResource).where(
            WorkspaceResource.workspace_id == workspace_id,
            WorkspaceResource.kind == "user_settings",
            WorkspaceResource.resource_key == user.id,
        )
    )
    payload = data.model_dump()
    if item:
        item.payload = payload
    else:
        db.add(
            WorkspaceResource(
                workspace_id=workspace_id,
                kind="user_settings",
                resource_key=user.id,
                payload=payload,
                created_by=user.id,
            )
        )
    audit(db, workspace_id, user, "updated", "settings", "Preferências pessoais atualizadas")
    db.commit()
    return payload


@router.get("/workspace-features/{workspace_id}/company")
def get_company_settings(
    workspace_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    require_workspace_access(workspace_id, db, user)
    workspace = db.get(Workspace, workspace_id)
    item = db.scalar(
        select(WorkspaceResource).where(
            WorkspaceResource.workspace_id == workspace_id,
            WorkspaceResource.kind == "workspace_company",
            WorkspaceResource.resource_key == "default",
        )
    )
    if item:
        return item.payload
    return CompanySettingsIn(brand_name=workspace.name).model_dump(by_alias=True)


@router.put("/workspace-features/{workspace_id}/company")
def save_company_settings(
    workspace_id: str,
    data: CompanySettingsIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    membership = require_workspace_access(workspace_id, db, user)
    require_admin(membership)
    payload = data.model_dump(by_alias=True)
    workspace = db.get(Workspace, workspace_id)
    if data.brand_name.strip():
        workspace.name = data.brand_name.strip()
        if workspace.brand_profile:
            workspace.brand_profile.name = data.brand_name.strip()
    item = db.scalar(
        select(WorkspaceResource).where(
            WorkspaceResource.workspace_id == workspace_id,
            WorkspaceResource.kind == "workspace_company",
            WorkspaceResource.resource_key == "default",
        )
    )
    if item:
        item.payload = payload
    else:
        db.add(
            WorkspaceResource(
                workspace_id=workspace_id,
                kind="workspace_company",
                resource_key="default",
                payload=payload,
                created_by=user.id,
            )
        )
    audit(db, workspace_id, user, "updated", "workspace_company", payload["brandName"] or "Empresa")
    db.commit()
    return payload


@router.get("/workspace-features/{workspace_id}/support-tickets")
def list_support_tickets(
    workspace_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[dict]:
    membership = require_workspace_access(workspace_id, db, user)
    query = select(WorkspaceResource).where(
        WorkspaceResource.workspace_id == workspace_id,
        WorkspaceResource.kind == "support_ticket",
    )
    if membership.role not in {"Owner", "Admin"}:
        query = query.where(WorkspaceResource.created_by == user.id)
    items = db.scalars(query.order_by(WorkspaceResource.created_at.desc())).all()
    return [{"id": item.id, **item.payload} for item in items]


@router.post("/workspace-features/{workspace_id}/support-tickets", status_code=status.HTTP_201_CREATED)
def create_support_ticket(
    workspace_id: str,
    data: SupportTicketIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    require_workspace_access(workspace_id, db, user)
    created_at = now()
    payload = {
        "subject": data.subject,
        "title": data.title.strip(),
        "details": data.details.strip(),
        "status": "open",
        "requestedBy": user.name,
        "requestedByEmail": user.email,
        "createdAt": created_at.isoformat(),
    }
    item = WorkspaceResource(
        workspace_id=workspace_id,
        kind="support_ticket",
        resource_key=f"ticket-{uuid4()}",
        payload=payload,
        created_by=user.id,
    )
    db.add(item)
    audit(db, workspace_id, user, "created", "support_ticket", payload["title"])
    db.commit()
    db.refresh(item)
    return {"id": item.id, **payload}


@router.get("/workspace-features/{workspace_id}/governance")
def governance(workspace_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    membership = require_workspace_access(workspace_id, db, user)
    require_admin(membership)
    workspace = db.get(Workspace, workspace_id)
    memberships = db.execute(
        select(Membership, User)
        .join(User, User.id == Membership.user_id)
        .where(Membership.workspace_id == workspace_id)
    ).all()
    members = [
        {
            "id": member_user.id,
            "workspaceId": workspace_id,
            "name": member_user.name,
            "email": member_user.email,
            "avatar": "",
            "role": "master" if member.role in {"Owner", "Admin"} else "collaborator",
            "status": "active" if member_user.is_active else "disabled",
            "modules": MODULES if member.role in {"Owner", "Admin"} else MODULES,
            "lastAccess": member.updated_at.isoformat(),
            "createdAt": member.created_at.isoformat(),
        }
        for member, member_user in memberships
    ]
    invites = list(
        db.scalars(
            select(WorkspaceResource).where(
                WorkspaceResource.workspace_id == workspace_id, WorkspaceResource.kind == "team_member"
            )
        ).all()
    )
    members.extend({"id": item.id, "workspaceId": workspace_id, **item.payload} for item in invites)
    plan_id = PLAN_BY_DB.get(workspace.plan, "team")
    plan = next(item for item in PLANS if item["id"] == plan_id)
    audit_events = list(
        db.scalars(
            select(AuditEvent)
            .where(AuditEvent.workspace_id == workspace_id)
            .order_by(AuditEvent.created_at.desc())
            .limit(250)
        ).all()
    )
    approval_events = list(
        db.scalars(
            select(ApprovalEvent).where(ApprovalEvent.workspace_id == workspace_id).order_by(ApprovalEvent.created_at)
        ).all()
    )
    return {
        "users": members,
        "plans": PLANS,
        "subscription": {
            "id": workspace.id,
            "workspaceId": workspace.id,
            "planId": plan_id,
            "status": "active",
            "startedAt": workspace.created_at.isoformat(),
            "renewsAt": "",
            "billingEmail": user.email,
            "paymentMethod": "Cobrança não configurada",
        },
        "workspace": {
            "id": workspace.id,
            "name": workspace.name,
            "logo": workspace.avatar,
            "planId": plan_id,
            "maxUsers": plan["maxUsers"],
            "activeUsers": len([item for item in members if item["status"] != "disabled"]),
            "subscriptionDate": workspace.created_at.isoformat(),
            "subscriptionStatus": "active",
            "settings": {"inviteExpiryDays": 7, "requireApproval": True, "timezone": "America/Sao_Paulo"},
        },
        "auditLogs": [
            {
                "id": item.id,
                "workspaceId": item.workspace_id,
                "actorId": item.actor_id or "system",
                "actorName": item.actor_name,
                "action": item.action,
                "resource": item.resource,
                "detail": item.detail,
                "createdAt": item.created_at.isoformat(),
            }
            for item in audit_events
        ],
        "approvalEvents": [
            {
                "id": item.id,
                "workspaceId": item.workspace_id,
                "postId": item.post_id,
                "actorId": item.actor_id or "system",
                "actorName": item.actor_name,
                "eventType": item.event_type,
                "action": item.action,
                "detail": item.detail,
                "createdAt": item.created_at.isoformat(),
            }
            for item in approval_events
        ],
    }


@router.post("/workspace-features/{workspace_id}/members", status_code=status.HTTP_201_CREATED)
def invite_member(
    workspace_id: str, data: MemberInviteIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> dict:
    membership = require_workspace_access(workspace_id, db, user)
    require_admin(membership)
    existing = db.scalar(
        select(WorkspaceResource).where(
            WorkspaceResource.workspace_id == workspace_id,
            WorkspaceResource.kind == "team_member",
            WorkspaceResource.resource_key == str(data.email).lower(),
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="Este e-mail já possui um convite pendente")
    workspace = db.get(Workspace, workspace_id)
    plan_id = PLAN_BY_DB.get(workspace.plan, "team")
    max_users = next(item["maxUsers"] for item in PLANS if item["id"] == plan_id)
    active_memberships = len(
        db.execute(
            select(Membership, User)
            .join(User, User.id == Membership.user_id)
            .where(Membership.workspace_id == workspace_id, User.is_active.is_(True))
        ).all()
    )
    pending_members = list(
        db.scalars(
            select(WorkspaceResource).where(
                WorkspaceResource.workspace_id == workspace_id, WorkspaceResource.kind == "team_member"
            )
        ).all()
    )
    occupied_seats = active_memberships + len(
        [item for item in pending_members if item.payload.get("status") != "disabled"]
    )
    if max_users is not None and occupied_seats >= max_users:
        raise HTTPException(status_code=409, detail="Limite de assentos do plano atingido")
    created = now()
    payload = {
        "name": data.name.strip(),
        "email": str(data.email).lower(),
        "avatar": "",
        "role": "collaborator",
        "status": "invited",
        "modules": data.modules,
        "lastAccess": "",
        "createdAt": created.isoformat(),
        "invitedAt": created.isoformat(),
        "inviteExpiresAt": (created + timedelta(days=7)).isoformat(),
    }
    item = WorkspaceResource(
        workspace_id=workspace_id,
        kind="team_member",
        resource_key=payload["email"],
        payload=payload,
        created_by=user.id,
    )
    db.add(item)
    audit(db, workspace_id, user, "invited", "team_member", payload["email"])
    db.commit()
    db.refresh(item)
    return {"id": item.id, "workspaceId": workspace_id, **payload}


@router.patch("/workspace-features/{workspace_id}/members/{member_id}")
def update_member(
    workspace_id: str,
    member_id: str,
    data: MemberUpdateIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    membership = require_workspace_access(workspace_id, db, user)
    require_admin(membership)
    item = resource_for(db, member_id, workspace_id)
    if item.kind != "team_member":
        raise HTTPException(status_code=400, detail="Only invited collaborators can be edited here")
    payload = dict(item.payload)
    payload.update(data.model_dump(exclude_none=True))
    item.payload = payload
    audit(db, workspace_id, user, "updated", "team_member", payload["email"])
    db.commit()
    return {"id": item.id, "workspaceId": workspace_id, **payload}


@router.post("/workspace-features/{workspace_id}/members/{member_id}/resend")
def resend_invite(
    workspace_id: str, member_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> dict:
    membership = require_workspace_access(workspace_id, db, user)
    require_admin(membership)
    item = resource_for(db, member_id, workspace_id)
    if item.kind != "team_member":
        raise HTTPException(status_code=400, detail="Only invited collaborators can be managed here")
    payload = dict(item.payload)
    sent = now()
    payload.update(
        {"status": "invited", "invitedAt": sent.isoformat(), "inviteExpiresAt": (sent + timedelta(days=7)).isoformat()}
    )
    item.payload = payload
    audit(db, workspace_id, user, "resent", "team_member", payload["email"])
    db.commit()
    return {"id": item.id, "workspaceId": workspace_id, **payload}


@router.delete("/workspace-features/{workspace_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_member(
    workspace_id: str, member_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> None:
    membership = require_workspace_access(workspace_id, db, user)
    require_admin(membership)
    item = resource_for(db, member_id, workspace_id)
    if item.kind != "team_member":
        raise HTTPException(status_code=400, detail="Only invited collaborators can be managed here")
    audit(db, workspace_id, user, "deleted", "team_member", str(item.payload.get("email", member_id)))
    db.delete(item)
    db.commit()


@router.patch("/workspace-features/{workspace_id}/subscription")
def change_plan(
    workspace_id: str, data: PlanUpdateIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> dict:
    membership = require_workspace_access(workspace_id, db, user)
    require_admin(membership)
    workspace = db.get(Workspace, workspace_id)
    workspace.plan = DB_BY_PLAN[data.plan_id]
    audit(db, workspace_id, user, "changed", "subscription", f"Plano alterado para {data.plan_id}")
    db.commit()
    return {"planId": data.plan_id}
