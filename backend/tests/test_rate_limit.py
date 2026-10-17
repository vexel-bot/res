from app.services.rate_limit import RateLimitPolicy, RedisRateLimiter, policy_for_request


class FakeRedis:
    def __init__(self):
        self.count = 0

    def eval(self, _script, _keys, _key, window_seconds):
        self.count += 1
        return [self.count, window_seconds]


def test_rate_limit_policies_prioritize_sensitive_routes():
    values = {
        "default_limit": 240,
        "auth_limit": 10,
        "intensive_limit": 30,
        "upload_limit": 20,
        "window_seconds": 60,
    }
    assert policy_for_request("GET", "/health/ready", **values) is None
    assert policy_for_request("POST", "/api/v1/auth/login", **values).name == "auth"
    assert policy_for_request("POST", "/api/v1/assets/upload", **values).name == "upload"
    assert policy_for_request("POST", "/api/ai/chat", **values).name == "intensive"
    assert policy_for_request("GET", "/api/v1/bootstrap", **values).name == "api"


def test_redis_rate_limiter_reports_remaining_and_retry_window():
    limiter = RedisRateLimiter("redis://unused", client=FakeRedis())
    policy = RateLimitPolicy("auth", limit=2, window_seconds=60)
    first = limiter.consume("198.51.100.10", policy)
    second = limiter.consume("198.51.100.10", policy)
    blocked = limiter.consume("198.51.100.10", policy)
    assert first.allowed and first.remaining == 1
    assert second.allowed and second.remaining == 0
    assert not blocked.allowed and blocked.retry_after == 60
