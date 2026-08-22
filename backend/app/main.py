import json
import logging
import time
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import get_settings
from .database import Base, engine
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
from .services.rate_limit import RateLimitBackendError, RedisRateLimiter, policy_for_request

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
    yield


app = FastAPI(title="Nexus AI API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Correlation-ID", "Idempotency-Key"],
)


@app.middleware("http")
async def correlation_and_access_log(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid4()))[:128]
    started = time.perf_counter()
    rate_headers: dict[str, str] = {}
    try:
        policy = None
        if settings.environment == "production":
            policy = policy_for_request(
                request.method,
                request.url.path,
                default_limit=settings.rate_limit_requests,
                auth_limit=settings.rate_limit_auth_requests,
                intensive_limit=settings.rate_limit_intensive_requests,
                upload_limit=settings.rate_limit_upload_requests,
                window_seconds=settings.rate_limit_window_seconds,
            )
        if policy:
            identity = request.client.host if request.client else "unknown"
            try:
                rate = rate_limiter.consume(identity, policy)
            except RateLimitBackendError:
                logger.exception(
                    "rate_limit_backend_error correlation_id=%s path=%s policy=%s",
                    correlation_id,
                    request.url.path,
                    policy.name,
                )
                if policy.name == "auth":
                    response = JSONResponse(
                        status_code=503, content={"detail": "Authentication temporarily unavailable"}
                    )
                else:
                    response = await call_next(request)
            else:
                rate_headers = {
                    "X-RateLimit-Limit": str(rate.limit),
                    "X-RateLimit-Remaining": str(rate.remaining),
                }
                if rate.allowed:
                    response = await call_next(request)
                else:
                    rate_headers["Retry-After"] = str(rate.retry_after)
                    response = JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
        else:
            response = await call_next(request)
    except Exception:
        logger.exception("unhandled_request_error correlation_id=%s path=%s", correlation_id, request.url.path)
        response = JSONResponse(status_code=500, content={"detail": "Internal server error"})
    response.headers["X-Correlation-ID"] = correlation_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    for name, value in rate_headers.items():
        response.headers[name] = value
    logger.info(
        "request correlation_id=%s method=%s path=%s status=%s latency_ms=%s",
        correlation_id,
        request.method,
        request.url.path,
        response.status_code,
        round((time.perf_counter() - started) * 1000, 2),
    )
    return response


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
app.include_router(workspace_features.router, prefix="/api/v1")
app.include_router(ai.router, prefix="/api")
