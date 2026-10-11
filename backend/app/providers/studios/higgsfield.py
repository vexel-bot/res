"""Explicit Higgsfield transport; unregistered and submission-disabled by default.

Internal transport types only. The caller must persist intent/reservation before
submission, reconcile unknown outcomes and admit artifacts through Studio assets.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Literal
from urllib.parse import urlsplit
from uuid import UUID

import httpx
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

BASE = "https://api.higgsfield.ai"
TTV = "kling-video/v3.0/std/text-to-video"
I2V = "kling-video/v3.0/std/image-to-video"
IMAGE = "ideogram/v4.0"
State = Literal["queued", "in_progress", "completed", "failed", "nsfw", "canceled"]
STATES = {"queued", "in_progress", "completed", "failed", "nsfw", "canceled"}


def _https_url(value: str) -> str:
    parsed = urlsplit(value)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
            or parsed.fragment or any(ord(c) <= 32 for c in value)):
        raise ValueError("higgsfield_https_url_required")
    return value


class _KlingBaseInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, hide_input_in_errors=True)
    prompt: str = Field(min_length=1, max_length=8000)
    duration: int = Field(default=5, ge=3, le=15)
    sound: Literal["on", "off"] = "on"
    cfg_scale: float = Field(default=0.5, ge=0, le=1, allow_inf_nan=False)
    multi_shots: Literal[False] = False


class _KlingInput(_KlingBaseInput):
    aspect_ratio: Literal["16:9", "9:16", "1:1"] = "16:9"


class _KlingImageInput(_KlingBaseInput):
    # Output ratio follows the supplied image; this endpoint has no ratio field.
    image_url: str
    last_image_url: str | None = None
    _validate_urls = field_validator("image_url", "last_image_url")(
        lambda v: _https_url(v) if v is not None else v
    )


class _IdeogramInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, hide_input_in_errors=True)
    prompt: str = Field(min_length=2, max_length=2048)
    aspect_ratio: Literal["1:1", "1:2", "2:1", "2:3", "3:2", "4:5", "5:4", "9:16", "16:9",
                          "5:8", "8:5", "3:4", "4:3", "9:22", "22:9", "9:23", "23:9",
                          "3:8", "8:3", "5:12", "12:5", "1:3", "3:1"] = "1:1"
    image_url: str | None = None
    image_weight: int | None = Field(default=None, ge=1, le=100)
    rendering_speed: Literal["TURBO", "DEFAULT", "QUALITY"] = "DEFAULT"
    _validate_url = field_validator("image_url")(lambda v: _https_url(v) if v is not None else v)


INPUTS = {TTV: _KlingInput, I2V: _KlingImageInput, IMAGE: _IdeogramInput}


def _canonical(value) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


class PreparedGeneration(BaseModel):
    """Persistable immutable intent; never a document or an approval receipt."""
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)
    model: Literal["kling-video/v3.0/std/text-to-video", "kling-video/v3.0/std/image-to-video", "ideogram/v4.0"]
    payload_json: str = Field(repr=False, max_length=65536)
    idempotency_key: str = Field(repr=False, min_length=1, max_length=255)

    @field_validator("idempotency_key")
    @classmethod
    def visible_ascii_key(cls, value):
        if not re.fullmatch(r"[!-~]{1,255}", value):
            raise ValueError("higgsfield_idempotency_key_invalid")
        return value

    @model_validator(mode="after")
    def valid_payload(self):
        try:
            body = json.loads(self.payload_json)
            INPUTS[self.model].model_validate(body)
            if _canonical(body) != self.payload_json:
                raise ValueError("noncanonical")
        except (ValueError, TypeError):
            raise ValueError("higgsfield_payload_invalid") from None
        return self

    @classmethod
    def prepare(cls, model: str, parameters: dict, idempotency_key: str):
        if model not in INPUTS:
            raise ValueError("higgsfield_model_unsupported")
        # Validate without inserting defaults: omitted vs explicit fields matter
        # to the provider's idempotency binding.
        try:
            INPUTS[model].model_validate(parameters)
            return cls(model=model, payload_json=_canonical(parameters), idempotency_key=idempotency_key)
        except (ValueError, TypeError):
            raise HiggsfieldError("higgsfield_intent_invalid") from None

    @property
    def digest_sha256(self):
        return hashlib.sha256(_canonical({"model": self.model, "body": self.payload_json,
                                         "key": self.idempotency_key}).encode()).hexdigest()


@dataclass(frozen=True)
class GenerationQuote:
    intent_sha256: str
    usd: Decimal
    credits: Decimal
    observed_monotonic: float
    credential_binding: str


@dataclass(frozen=True)
class GenerationReceipt:
    request_id: str
    status: State
    output_kind: Literal["image", "video"]
    status_url: str = field(repr=False)
    cancel_url: str | None = field(default=None, repr=False)
    candidate_urls: tuple[str, ...] = field(default=(), repr=False)

    @property
    def terminal(self):
        return self.status in {"completed", "failed", "nsfw", "canceled"}


class HiggsfieldError(ValueError):
    def __init__(self, code: str, *, outcome_unknown=False):
        super().__init__(code)
        self.outcome_unknown = outcome_unknown


def _amount(value) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise HiggsfieldError("higgsfield_amount_invalid")
    try:
        amount = Decimal(str(value))
    except InvalidOperation:
        raise HiggsfieldError("higgsfield_amount_invalid") from None
    if not amount.is_finite() or amount < 0:
        raise HiggsfieldError("higgsfield_amount_invalid")
    return amount


def _control_url(value, request_id, action):
    # Keep the server-provided URL, but never forward authentication elsewhere.
    try:
        if not isinstance(request_id, str) or str(UUID(request_id)) != request_id:
            raise ValueError("invalid")
    except ValueError:
        raise HiggsfieldError("higgsfield_request_id_invalid") from None
    if not isinstance(value, str) or value != f"{BASE}/requests/{request_id}/{action}":
        raise HiggsfieldError("higgsfield_control_url_invalid")
    return value


class HiggsfieldProvider:
    name = "higgsfield.media"
    version = "1.0.0-experimental"

    def __init__(self, key_id: str, key_secret: str, *, client=None, submission_enabled=False):
        for part in (key_id, key_secret):
            if not isinstance(part, str) or not re.fullmatch(r"[!-9;-~]+", part):
                raise HiggsfieldError("higgsfield_credentials_invalid")
        self._authorization = f"Key {key_id}:{key_secret}"
        self._credential_binding = hashlib.sha256(self._authorization.encode()).hexdigest()
        self._client = client
        self._submission_enabled = submission_enabled is True

    def _request(self, method, url, *, body=None, key=None, submission=False, empty_ok=False):
        headers = {"Authorization": self._authorization}
        if body is not None:
            headers["Content-Type"] = "application/json"
        if key is not None:
            headers["Idempotency-Key"] = key

        def call(client):
            try:
                response = client.request(method, url, content=body.encode() if body is not None else None,
                                          headers=headers, follow_redirects=False)
            except httpx.HTTPError:
                raise HiggsfieldError("higgsfield_transport_outcome_unknown",
                                      outcome_unknown=submission) from None
            if response.status_code < 200 or response.status_code >= 300:
                unknown = submission and (response.status_code >= 500 or response.status_code == 408
                                          or 300 <= response.status_code < 400)
                raise HiggsfieldError(f"higgsfield_http_{response.status_code}", outcome_unknown=unknown)
            if empty_ok and response.status_code == 202 and not response.content:
                return None
            if empty_ok:
                raise HiggsfieldError("higgsfield_cancel_response_invalid")
            try:
                value = response.json(parse_float=Decimal)
                if not isinstance(value, dict):
                    raise ValueError("object_required")
                return value
            except ValueError:
                raise HiggsfieldError("higgsfield_response_invalid", outcome_unknown=submission) from None

        if self._client is not None:
            return call(self._client)
        with httpx.Client(timeout=60, trust_env=False, follow_redirects=False) as client:
            return call(client)

    def estimate(self, intent: PreparedGeneration) -> GenerationQuote:
        value = self._request("POST", f"{BASE}/estimate/{intent.model}", body=intent.payload_json)
        return GenerationQuote(intent.digest_sha256, _amount(value.get("usd")),
                               _amount(value.get("credits")), time.monotonic(), self._credential_binding)

    def submit(self, intent: PreparedGeneration, quote: GenerationQuote, *, maximum_cost_usd) -> GenerationReceipt:
        if not self._submission_enabled:
            raise HiggsfieldError("higgsfield_submission_disabled")
        if quote.intent_sha256 != intent.digest_sha256:
            raise HiggsfieldError("higgsfield_quote_binding_conflict")
        if quote.credential_binding != self._credential_binding:
            raise HiggsfieldError("higgsfield_quote_credentials_changed")
        age = time.monotonic() - quote.observed_monotonic
        if not 0 <= age <= 300:
            raise HiggsfieldError("higgsfield_quote_expired")
        if _amount(quote.usd) > _amount(maximum_cost_usd):
            raise HiggsfieldError("higgsfield_budget_exceeded")
        value = self._request("POST", f"{BASE}/{intent.model}", body=intent.payload_json,
                              key=intent.idempotency_key, submission=True)
        try:
            return self._receipt(value, output_kind="image" if intent.model == IMAGE else "video")
        except (HiggsfieldError, ValueError, TypeError):
            # A successful HTTP response with an unusable receipt may still have
            # accepted a billable generation. Do not release/resubmit as new.
            raise HiggsfieldError("higgsfield_submission_receipt_unknown", outcome_unknown=True) from None

    @staticmethod
    def _receipt(value, previous: GenerationReceipt | None = None, *, output_kind=None):
        request_id = value.get("request_id")
        if not isinstance(request_id, str) or str(UUID(request_id)) != request_id:
            raise HiggsfieldError("higgsfield_request_id_invalid")
        if previous and request_id != previous.request_id:
            raise HiggsfieldError("higgsfield_request_binding_conflict")
        status = value.get("status")
        if not isinstance(status, str) or status not in STATES:
            raise HiggsfieldError("higgsfield_status_invalid")
        status_url = _control_url(value.get("status_url", previous.status_url if previous else None),
                                  request_id, "status")
        cancel_url = value.get("cancel_url", previous.cancel_url if previous else None)
        if cancel_url is not None:
            cancel_url = _control_url(cancel_url, request_id, "cancel")
        urls = []
        kind = previous.output_kind if previous else output_kind
        if kind not in {"image", "video"}:
            raise HiggsfieldError("higgsfield_output_kind_invalid")
        if status == "completed":
            media = value.get("images") if kind == "image" else ([value["video"]] if value.get("video") else [])
            if not isinstance(media, list) or not media:
                raise HiggsfieldError("higgsfield_completed_output_missing")
            for item in media:
                if not isinstance(item, dict) or not isinstance(item.get("url"), str):
                    raise HiggsfieldError("higgsfield_output_invalid")
                urls.append(_https_url(item["url"]))
        return GenerationReceipt(request_id, status, kind, status_url, cancel_url, tuple(urls))

    def retrieve(self, receipt: GenerationReceipt) -> GenerationReceipt:
        url = _control_url(receipt.status_url, receipt.request_id, "status")
        value = self._request("GET", url)
        return self._receipt(value, receipt)

    def cancel_queued(self, receipt: GenerationReceipt) -> bool:
        """True means cancellation accepted, not confirmed canceled/refunded."""
        if receipt.status != "queued" or receipt.cancel_url is None:
            return False
        url = _control_url(receipt.cancel_url, receipt.request_id, "cancel")
        try:
            self._request("POST", url, empty_ok=True)
        except HiggsfieldError as error:
            if str(error) == "higgsfield_http_400":
                return False  # The job may have started since the last poll.
            raise
        return True
