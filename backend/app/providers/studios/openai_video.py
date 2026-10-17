from __future__ import annotations

import hashlib
import time
from collections.abc import Callable
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import httpx

from app.config import Settings
from app.domain.studios.generative_video import (
    GenerativeVideoDownloadV1,
    GenerativeVideoOperationV1,
    GenerativeVideoRequestV1,
)
from app.domain.studios.providers import CancellationCheck

SORA_API_SHUTDOWN_DATE = date(2026, 9, 24)


class OpenAIVideoProviderError(RuntimeError):
    """Sanitized adapter failure that never carries response bodies or credentials."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class OpenAISoraVideoProvider:
    name = "openai.sora-2"
    version = "2026-09-04"

    def __init__(
        self,
        settings: Settings,
        *,
        client: httpx.Client | None = None,
        now: Callable[[], datetime] | None = None,
        sleep: Callable[[float], None] = time.sleep,
        poll_interval_seconds: float = 10,
        poll_timeout_seconds: float = 1800,
    ) -> None:
        self._settings = settings
        self._now = now or (lambda: datetime.now(UTC))
        self._sleep = sleep
        self._poll_interval_seconds = poll_interval_seconds
        self._poll_timeout_seconds = poll_timeout_seconds
        secret = settings.openai_api_key
        self._api_key = secret.get_secret_value() if secret else ""
        self._client = client or httpx.Client(
            base_url="https://api.openai.com/v1",
            timeout=httpx.Timeout(15, read=120),
            headers={"Authorization": f"Bearer {self._api_key}"},
            trust_env=False,
        )

    def close(self) -> None:
        self._client.close()

    def _gate(self, request: GenerativeVideoRequestV1) -> None:
        if self._now().date() >= SORA_API_SHUTDOWN_DATE:
            raise OpenAIVideoProviderError("sora_api_retired")
        if not self._settings.openai_outbound_enabled:
            raise OpenAIVideoProviderError("openai_outbound_disabled")
        if not self._settings.openai_video_generation_enabled:
            raise OpenAIVideoProviderError("openai_video_generation_disabled")
        if not self._api_key:
            raise OpenAIVideoProviderError("openai_api_key_missing")
        if self._settings.openai_max_external_spend_usd < request.estimated_cost_usd:
            raise OpenAIVideoProviderError("openai_spend_cap_insufficient")
        if request.maximum_cost_usd < request.estimated_cost_usd:
            raise OpenAIVideoProviderError("request_spend_cap_insufficient")

    @staticmethod
    def _request(client_call: Callable[[], httpx.Response], failure_code: str) -> httpx.Response:
        try:
            response = client_call()
        except httpx.TimeoutException as exc:
            raise OpenAIVideoProviderError("provider_timeout") from exc
        except httpx.HTTPError as exc:
            raise OpenAIVideoProviderError("provider_transport_error") from exc
        if response.status_code == 401:
            raise OpenAIVideoProviderError("provider_authentication_failed")
        if response.status_code == 429:
            raise OpenAIVideoProviderError("provider_rate_limited")
        if response.status_code >= 400:
            raise OpenAIVideoProviderError(failure_code)
        return response

    @staticmethod
    def _json(response: httpx.Response) -> dict[str, Any]:
        try:
            value = response.json()
        except ValueError as exc:
            raise OpenAIVideoProviderError("provider_invalid_json") from exc
        if not isinstance(value, dict):
            raise OpenAIVideoProviderError("provider_invalid_json")
        return value

    def preflight(self, request: GenerativeVideoRequestV1) -> None:
        self._gate(request)
        self._request(lambda: self._client.get(f"/models/{request.model}"), "model_not_visible")

    def start(self, request: GenerativeVideoRequestV1) -> GenerativeVideoOperationV1:
        self._gate(request)
        response = self._request(
            lambda: self._client.post(
                "/videos",
                json={
                    "model": request.model,
                    "prompt": request.prompt,
                    "seconds": str(request.duration_seconds),
                    "size": request.resolution,
                },
                headers={"Idempotency-Key": request.request_id},
            ),
            "provider_start_failed",
        )
        payload = self._json(response)
        operation_id = payload.get("id")
        status = payload.get("status", "queued")
        if not isinstance(operation_id, str) or not operation_id:
            raise OpenAIVideoProviderError("provider_operation_id_missing")
        if status not in {"queued", "in_progress", "completed", "failed"}:
            raise OpenAIVideoProviderError("provider_unknown_status")
        observed = self._now()
        return GenerativeVideoOperationV1(
            request_id=request.request_id,
            provider_operation_id=operation_id,
            status=status,
            estimated_cost_usd=request.estimated_cost_usd,
            created_at=observed,
            last_observed_at=observed,
            failure_code="provider_job_failed" if status == "failed" else None,
        )

    def cancel(self, operation: GenerativeVideoOperationV1) -> GenerativeVideoOperationV1:
        if operation.status in {"completed", "failed", "cancelled"}:
            return operation
        return operation.model_copy(
            update={
                "status": "cancelled",
                "last_observed_at": self._now(),
                "failure_code": "local_polling_cancelled_provider_job_may_continue",
            }
        )

    def wait(
        self,
        operation: GenerativeVideoOperationV1,
        *,
        is_cancelled: CancellationCheck,
    ) -> GenerativeVideoOperationV1:
        deadline = time.monotonic() + self._poll_timeout_seconds
        current = operation
        while current.status in {"queued", "in_progress"}:
            if is_cancelled():
                return self.cancel(current)
            if time.monotonic() >= deadline:
                raise OpenAIVideoProviderError("provider_poll_timeout")
            operation_id = current.provider_operation_id
            response = self._request(
                lambda operation_id=operation_id: self._client.get(f"/videos/{operation_id}"),
                "provider_poll_failed",
            )
            payload = self._json(response)
            status = payload.get("status")
            if status not in {"queued", "in_progress", "completed", "failed"}:
                raise OpenAIVideoProviderError("provider_unknown_status")
            current = current.model_copy(
                update={
                    "status": status,
                    "last_observed_at": self._now(),
                    "failure_code": "provider_job_failed" if status == "failed" else None,
                }
            )
            if current.status in {"queued", "in_progress"}:
                self._sleep(self._poll_interval_seconds)
        return current

    def download(
        self,
        request: GenerativeVideoRequestV1,
        operation: GenerativeVideoOperationV1,
        destination: Path,
    ) -> GenerativeVideoDownloadV1:
        self._gate(request)
        if operation.request_id != request.request_id:
            raise OpenAIVideoProviderError("operation_request_mismatch")
        if operation.status != "completed":
            raise OpenAIVideoProviderError("operation_not_completed")
        if destination.exists():
            raise OpenAIVideoProviderError("destination_already_exists")
        response = self._request(
            lambda: self._client.get(f"/videos/{operation.provider_operation_id}/content"),
            "provider_download_failed",
        )
        content = response.content
        if not content:
            raise OpenAIVideoProviderError("provider_empty_download")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        return GenerativeVideoDownloadV1(
            provider_operation_id=operation.provider_operation_id,
            artifact_checksum_sha256=hashlib.sha256(content).hexdigest(),
            byte_count=len(content),
        )
