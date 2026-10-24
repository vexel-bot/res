import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .database import Base, engine
from .http_middleware import install_http_middleware
from .routers import (
    ai,
    analytics,
    assets,
    auth,
    bootstrap,
    campaigns,
    creatives,
    health,
    history,
    jobs,
    knowledge,
    posts,
    radar,
    workspace_features,
    workspaces,
)
from .services.rate_limit import RedisRateLimiter
from .studio_routes import include_studio_routes

settings = get_settings()
rate_limiter = RedisRateLimiter(settings.redis_url)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps(
            {
                "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%SZ"),
                "level": record.levelname.lower(),
                "logger": record.name,
                "message": record.getMessage(),
            },
            ensure_ascii=False,
        )


handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
logger = logging.getLogger("nexus.api")


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.validate_for_startup()
    if settings.environment in {"development", "test"}:
        Base.metadata.create_all(bind=engine)
    from .routers.studio_video import recover_interrupted_local_jobs

    recover_interrupted_local_jobs()
    yield


app = FastAPI(title="Nexus AI API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Correlation-ID", "Idempotency-Key"],
)


install_http_middleware(app, settings, rate_limiter, logger)


app.include_router(health.router)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(bootstrap.router, prefix="/api/v1")
app.include_router(workspaces.router, prefix="/api/v1")
app.include_router(posts.router, prefix="/api/v1")
app.include_router(campaigns.router, prefix="/api/v1")
app.include_router(creatives.router, prefix="/api/v1")
app.include_router(history.router, prefix="/api/v1")
app.include_router(assets.router, prefix="/api/v1")
app.include_router(jobs.router, prefix="/api/v1")
app.include_router(knowledge.router, prefix="/api/v1")
app.include_router(radar.router, prefix="/api/v1")
include_studio_routes(app)
app.include_router(workspace_features.router, prefix="/api/v1")
app.include_router(ai.router, prefix="/api")
