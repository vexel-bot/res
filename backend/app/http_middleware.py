"""Shared request tracing, safe errors and production rate limits for both APIs."""

import time
from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse

from .services.rate_limit import RateLimitBackendError, policy_for_request


def install_http_middleware(app, settings, rate_limiter, logger):
    @app.middleware("http")
    async def correlation_and_access_log(request: Request, call_next):
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid4()))[:128]
        started = time.perf_counter()
        headers = {}
        try:
            policy = (
                policy_for_request(
                    request.method,
                    request.url.path,
                    default_limit=settings.rate_limit_requests,
                    auth_limit=settings.rate_limit_auth_requests,
                    intensive_limit=settings.rate_limit_intensive_requests,
                    upload_limit=settings.rate_limit_upload_requests,
                    window_seconds=settings.rate_limit_window_seconds,
                )
                if settings.environment == "production"
                else None
            )
            response = None
            if policy:
                try:
                    rate = rate_limiter.consume(request.client.host if request.client else "unknown", policy)
                except RateLimitBackendError:
                    logger.error("rate_limit_backend_error correlation_id=%s policy=%s", correlation_id, policy.name)
                    # Authentication and media mutations fail closed when their safety dependency fails.
                    if policy.name == "auth" or request.method not in {"GET", "HEAD", "OPTIONS"}:
                        response = JSONResponse(
                            status_code=503, content={"detail": "Required safety service unavailable"}
                        )
                else:
                    headers = {"X-RateLimit-Limit": str(rate.limit), "X-RateLimit-Remaining": str(rate.remaining)}
                    if not rate.allowed:
                        headers["Retry-After"] = str(rate.retry_after)
                        response = JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
            if response is None:
                response = await call_next(request)
        except Exception:
            # Never log provider exceptions containing request bodies, keys or client material.
            logger.error("unhandled_request_error correlation_id=%s path=%s", correlation_id, request.url.path)
            response = JSONResponse(status_code=500, content={"detail": "Internal server error"})
        response.headers.update(
            {
                "X-Correlation-ID": correlation_id,
                "X-Content-Type-Options": "nosniff",
                "Referrer-Policy": "strict-origin-when-cross-origin",
                **headers,
            }
        )
        logger.info(
            "request correlation_id=%s method=%s path=%s status=%s latency_ms=%s",
            correlation_id,
            request.method,
            request.url.path,
            response.status_code,
            round((time.perf_counter() - started) * 1000, 2),
        )
        return response
