from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Membership, Post, User, Workspace
from ..schemas import BootstrapOut, UserOut
from ..security import get_current_user
from ..serializers import post_out, workspace_out

router = APIRouter(tags=["bootstrap"])


@router.get("/bootstrap", response_model=BootstrapOut)
def bootstrap(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> BootstrapOut:
    workspaces = (
        db.scalars(
            select(Workspace).join(Membership).where(Membership.user_id == user.id).order_by(Workspace.created_at)
        )
        .unique()
        .all()
    )
    workspace_ids = [item.id for item in workspaces]
    posts = []
    if workspace_ids:
        posts = db.scalars(
            select(Post).where(Post.workspace_id.in_(workspace_ids)).order_by(Post.created_at.desc())
        ).all()
    suggestions = [
        {
            "id": "radar-today",
            "title": "Consultar oportunidades contextuais",
            "description": "Veja sinais atuais com conexão verificável para sua marca.",
            "type": "campaign",
            "badge": "Radar",
            "impact": "Contexto atual",
        }
    ]
    return BootstrapOut(
        user=UserOut.model_validate(user),
        workspaces=[workspace_out(db, item, user.id) for item in workspaces],
        posts=[post_out(item) for item in posts],
        suggestions=suggestions,
    )
