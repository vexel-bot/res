from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import JobAudit, Membership, User
from ..schemas import JobOut
from ..security import get_current_user

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobOut)
def get_job(
    job_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> JobOut:
    job = db.get(JobAudit, job_id)
    if not job or not job.workspace_id:
        raise HTTPException(status_code=404, detail="Job not found")
    if not db.scalar(
        select(Membership.id).where(Membership.user_id == user.id, Membership.workspace_id == job.workspace_id)
    ):
        raise HTTPException(status_code=404, detail="Job not found")
    return JobOut.model_validate(job)
