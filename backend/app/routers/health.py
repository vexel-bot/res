import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
def live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
def ready(db: Session = Depends(get_db)):
    settings = get_settings()
    dependencies = {}
    try:
        db.execute(text("SELECT 1"))
        dependencies["database"] = "ok"
    except Exception:
        db.rollback()
        dependencies["database"] = "unavailable"
    try:
        if settings.object_storage_backend == "local":
            root = Path(settings.storage_path).resolve()
            root.mkdir(parents=True, exist_ok=True)
            # Probe only a fresh disposable object, never client files.
            with tempfile.TemporaryFile(dir=root) as probe:
                probe.write(b"clicko-ready")
                probe.seek(0)
                if probe.read() != b"clicko-ready":
                    raise OSError("storage_probe_failed")
        else:
            from ..services.object_storage import get_object_storage

            storage = get_object_storage()
            storage.client.head_bucket(Bucket=settings.object_storage_bucket)
        dependencies["storage"] = "ok"
    except Exception:
        dependencies["storage"] = "unavailable"
    try:
        if settings.celery_task_always_eager and settings.environment != "production":
            dependencies["queue"] = "local-thread-pool"
        else:
            from redis import Redis

            from ..celery_app import celery_app

            with Redis.from_url(settings.redis_url, socket_connect_timeout=1, socket_timeout=1) as redis:
                redis.ping()
            queues = celery_app.control.inspect(timeout=1).active_queues() or {}
            names = {queue["name"] for worker in queues.values() for queue in worker}
            required = {"celery", "studio.media.cpu"} if settings.studio_isolated_queues_enabled else {"celery"}
            dependencies["queue"] = "ok" if required <= names else "worker-unavailable"
    except Exception:
        dependencies["queue"] = "unavailable"
    from ..providers.studios.timeline_ffmpeg import capability

    dependencies["ffmpeg"] = "ok" if capability()["available"] else "unavailable"
    ok = all(value in {"ok", "local-thread-pool"} for value in dependencies.values())
    return JSONResponse(
        status_code=200 if ok else 503,
        content={
            "status": "ready" if ok else "not_ready",
            "service": "clicko-studios",
            "dependencies": dependencies,
            "optionalRuntimes": {"craft": "check_authenticated_engine_capabilities"},
        },
    )
