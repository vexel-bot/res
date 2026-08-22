from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
def live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
def ready(db: Session = Depends(get_db)) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
        if get_settings().environment == "production":
            from redis import Redis

            Redis.from_url(get_settings().redis_url, socket_connect_timeout=2).ping()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="A required dependency is unavailable") from exc
    return {
        "status": "ready",
        "database": "ok",
        "redis": "ok" if get_settings().environment == "production" else "not-required",
    }
