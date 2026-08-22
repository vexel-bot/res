from dataclasses import dataclass
from hashlib import sha256

from redis import Redis
from redis.exceptions import RedisError


@dataclass(frozen=True)
class RateLimitPolicy:
    name: str
    limit: int
    window_seconds: int


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    limit: int
    remaining: int
    retry_after: int


class RateLimitBackendError(RuntimeError):
    pass


def policy_for_request(
    method: str,
    path: str,
    *,
    default_limit: int,
    auth_limit: int,
    intensive_limit: int,
    upload_limit: int,
    window_seconds: int,
) -> RateLimitPolicy | None:
    if not path.startswith("/api/"):
        return None
    normalized_method = method.upper()
    if normalized_method == "POST" and path in {"/api/v1/auth/login", "/api/v1/auth/register"}:
        return RateLimitPolicy("auth", auth_limit, window_seconds)
    if normalized_method == "POST" and path == "/api/v1/assets/upload":
        return RateLimitPolicy("upload", upload_limit, window_seconds)
    if normalized_method == "POST" and (
        path.startswith("/api/ai/") or (path.startswith("/api/v1/creatives/") and path.endswith("/export"))
    ):
        return RateLimitPolicy("intensive", intensive_limit, window_seconds)
    return RateLimitPolicy("api", default_limit, window_seconds)


class RedisRateLimiter:
    _SCRIPT = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then
  redis.call('EXPIRE', KEYS[1], ARGV[1])
end
local ttl = redis.call('TTL', KEYS[1])
if ttl < 0 then
  redis.call('EXPIRE', KEYS[1], ARGV[1])
  ttl = tonumber(ARGV[1])
end
return {current, ttl}
"""

    def __init__(self, redis_url: str, client: Redis | None = None):
        self.client = client or Redis.from_url(
            redis_url,
            decode_responses=False,
            socket_connect_timeout=0.5,
            socket_timeout=0.5,
        )

    def consume(self, identity: str, policy: RateLimitPolicy) -> RateLimitResult:
        digest = sha256(identity.encode("utf-8", errors="replace")).hexdigest()[:24]
        key = f"nexus:rate:{policy.name}:{digest}"
        try:
            current, ttl = self.client.eval(self._SCRIPT, 1, key, policy.window_seconds)
        except RedisError as error:
            raise RateLimitBackendError("Rate limit storage unavailable") from error
        count = int(current)
        retry_after = max(1, int(ttl))
        return RateLimitResult(
            allowed=count <= policy.limit,
            limit=policy.limit,
            remaining=max(0, policy.limit - count),
            retry_after=retry_after,
        )
