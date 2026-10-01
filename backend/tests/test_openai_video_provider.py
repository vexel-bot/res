from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from app.config import Settings
from app.domain.studios.generative_video import (
    ContentFitDurationPolicyV1,
    GenerativeVideoRequestV1,
)
from app.providers.studios.openai_video import (
    OpenAISoraVideoProvider,
    OpenAIVideoProviderError,
)


def request_contract() -> GenerativeVideoRequestV1:
    return GenerativeVideoRequestV1(
        request_id="caio-vale-base-v1",
        prompt="An original fictional Brazilian male presenter in a neutral studio.",
        maximum_cost_usd=1.5,
    )


def settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "OPENAI_API_KEY": "test-secret",
        "openai_outbound_enabled": True,
        "openai_video_generation_enabled": True,
        "openai_max_external_spend_usd": 1.5,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def provider(handler: httpx.MockTransport) -> OpenAISoraVideoProvider:
    client = httpx.Client(base_url="https://api.openai.com/v1", transport=handler)
    return OpenAISoraVideoProvider(
        settings(),
        client=client,
        now=lambda: datetime(2026, 9, 4, tzinfo=UTC),
        sleep=lambda _: None,
        poll_interval_seconds=0,
        poll_timeout_seconds=10,
    )


def test_contract_cost_and_content_fit_duration() -> None:
    request = request_contract()
    assert request.estimated_cost_usd == 1.2
    assert ContentFitDurationPolicyV1(measured_wav_seconds=31.4).mode == "content_fit"
    with pytest.raises(ValueError, match="24-45"):
        ContentFitDurationPolicyV1(measured_wav_seconds=46)


def test_flags_or_insufficient_cap_block_before_transport() -> None:
    called = False

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(200, json={})

    transport = httpx.MockTransport(handler)
    client = httpx.Client(base_url="https://api.openai.com/v1", transport=transport)
    disabled = OpenAISoraVideoProvider(
        Settings(_env_file=None, OPENAI_API_KEY="secret"),
        client=client,
        now=lambda: datetime(2026, 9, 4, tzinfo=UTC),
    )
    with pytest.raises(OpenAIVideoProviderError, match="openai_outbound_disabled"):
        disabled.preflight(request_contract())
    assert called is False

    capped = OpenAISoraVideoProvider(
        settings(openai_max_external_spend_usd=1.19),
        client=client,
        now=lambda: datetime(2026, 9, 4, tzinfo=UTC),
    )
    with pytest.raises(OpenAIVideoProviderError, match="openai_spend_cap_insufficient"):
        capped.start(request_contract())
    assert called is False


def test_preflight_start_poll_and_download_use_one_post(tmp_path: Path) -> None:
    calls: Counter[str] = Counter()
    states = iter(["in_progress", "completed"])

    def handler(request: httpx.Request) -> httpx.Response:
        key = f"{request.method} {request.url.path}"
        calls[key] += 1
        if key == "GET /v1/models/sora-2":
            return httpx.Response(200, json={"id": "sora-2"})
        if key == "POST /v1/videos":
            assert request.headers["idempotency-key"] == "caio-vale-base-v1"
            return httpx.Response(200, json={"id": "video_123", "status": "queued"})
        if key == "GET /v1/videos/video_123":
            return httpx.Response(200, json={"id": "video_123", "status": next(states)})
        if key == "GET /v1/videos/video_123/content":
            return httpx.Response(200, content=b"synthetic-mp4")
        raise AssertionError(key)

    adapter = provider(httpx.MockTransport(handler))
    request = request_contract()
    adapter.preflight(request)
    operation = adapter.start(request)
    operation = adapter.wait(operation, is_cancelled=lambda: False)
    destination = tmp_path / "raw.mp4"
    result = adapter.download(request, operation, destination)

    assert operation.status == "completed"
    assert result.byte_count == len(b"synthetic-mp4")
    assert destination.read_bytes() == b"synthetic-mp4"
    assert calls["POST /v1/videos"] == 1


@pytest.mark.parametrize(
    ("status_code", "expected"),
    [(401, "provider_authentication_failed"), (429, "provider_rate_limited")],
)
def test_start_sanitizes_auth_and_rate_limit(status_code: int, expected: str) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json={"error": {"message": "test-secret"}})

    with pytest.raises(OpenAIVideoProviderError, match=expected) as raised:
        provider(httpx.MockTransport(handler)).start(request_contract())
    assert "test-secret" not in repr(raised.value)


def test_failed_job_is_not_reposted() -> None:
    calls: Counter[str] = Counter()

    def handler(request: httpx.Request) -> httpx.Response:
        calls[request.method] += 1
        if request.method == "POST":
            return httpx.Response(200, json={"id": "video_failed", "status": "queued"})
        return httpx.Response(200, json={"id": "video_failed", "status": "failed"})

    adapter = provider(httpx.MockTransport(handler))
    operation = adapter.wait(adapter.start(request_contract()), is_cancelled=lambda: False)
    assert operation.status == "failed"
    assert operation.failure_code == "provider_job_failed"
    assert calls["POST"] == 1


def test_local_cancellation_does_not_send_unsupported_delete() -> None:
    calls: Counter[str] = Counter()

    def handler(request: httpx.Request) -> httpx.Response:
        calls[request.method] += 1
        if request.method == "POST":
            return httpx.Response(200, json={"id": "video_live", "status": "queued"})
        raise AssertionError("Cancellation must not call a remote delete endpoint")

    adapter = provider(httpx.MockTransport(handler))
    operation = adapter.wait(adapter.start(request_contract()), is_cancelled=lambda: True)
    assert operation.status == "cancelled"
    assert operation.failure_code == "local_polling_cancelled_provider_job_may_continue"
    assert calls == Counter({"POST": 1})


def test_transport_timeout_is_sanitized() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("test-secret")

    with pytest.raises(OpenAIVideoProviderError, match="provider_timeout") as raised:
        provider(httpx.MockTransport(handler)).preflight(request_contract())
    assert "test-secret" not in repr(raised.value)


def test_retirement_gate_is_closed_without_transport() -> None:
    adapter = OpenAISoraVideoProvider(
        settings(),
        client=httpx.Client(transport=httpx.MockTransport(lambda _: pytest.fail("network called"))),
        now=lambda: datetime(2026, 9, 24, tzinfo=UTC),
    )
    with pytest.raises(OpenAIVideoProviderError, match="sora_api_retired"):
        adapter.start(request_contract())
