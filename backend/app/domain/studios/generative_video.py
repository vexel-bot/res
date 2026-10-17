from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from .contracts import SHA256_PATTERN, StudioContract


class ContentFitDurationPolicyV1(StudioContract):
    """The spoken WAV determines duration; prose is never cut or time-stretched."""

    schema_version: Literal["studio.content-fit-duration-policy.v1"] = (
        "studio.content-fit-duration-policy.v1"
    )
    mode: Literal["content_fit"] = "content_fit"
    minimum_seconds: Literal[24] = 24
    maximum_seconds: Literal[45] = 45
    measured_wav_seconds: float | None = Field(default=None, ge=0, le=300)
    cut_sentences_allowed: Literal[False] = False
    artificial_speed_change_allowed: Literal[False] = False

    @model_validator(mode="after")
    def validate_measured_duration(self) -> ContentFitDurationPolicyV1:
        if self.measured_wav_seconds is not None and not (
            self.minimum_seconds <= self.measured_wav_seconds <= self.maximum_seconds
        ):
            raise ValueError("Measured WAV must fit the approved 24-45 second interval")
        return self


class GenerativeVideoRequestV1(StudioContract):
    schema_version: Literal["studio.generative-video-request.v1"] = (
        "studio.generative-video-request.v1"
    )
    request_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,159}$")
    model: Literal["sora-2"] = "sora-2"
    prompt: str = Field(min_length=1, max_length=8000)
    duration_seconds: Literal[4, 8, 12] = 12
    resolution: Literal["720x1280", "1280x720"] = "720x1280"
    output_count: Literal[1] = 1
    identity_kind: Literal["fictional_original"] = "fictional_original"
    human_image_reference_supplied: Literal[False] = False
    canonical_audio_policy: Literal["remove_all_audio"] = "remove_all_audio"
    maximum_cost_usd: float = Field(gt=0, le=1.50)

    @property
    def estimated_cost_usd(self) -> float:
        return round(self.duration_seconds * 0.10, 2)

    @model_validator(mode="after")
    def validate_spend(self) -> GenerativeVideoRequestV1:
        if self.maximum_cost_usd < self.estimated_cost_usd:
            raise ValueError("Approved spend is below the deterministic Sora estimate")
        return self


class GenerativeVideoOperationV1(StudioContract):
    schema_version: Literal["studio.generative-video-operation.v1"] = (
        "studio.generative-video-operation.v1"
    )
    request_id: str
    provider: Literal["openai.sora-2"] = "openai.sora-2"
    provider_operation_id: str
    status: Literal["queued", "in_progress", "completed", "failed", "cancelled"]
    post_count: Literal[1] = 1
    estimated_cost_usd: float = Field(ge=0, le=1.50)
    created_at: datetime
    last_observed_at: datetime
    failure_code: str | None = Field(default=None, max_length=160)


class GenerativeVideoDownloadV1(StudioContract):
    schema_version: Literal["studio.generative-video-download.v1"] = (
        "studio.generative-video-download.v1"
    )
    provider_operation_id: str
    artifact_checksum_sha256: str = Field(pattern=SHA256_PATTERN)
    byte_count: int = Field(gt=0)


class GenerativeVideoResultV1(StudioContract):
    schema_version: Literal["studio.generative-video-result.v1"] = (
        "studio.generative-video-result.v1"
    )
    request_id: str
    provider: Literal["openai.sora-2"] = "openai.sora-2"
    model: Literal["sora-2"] = "sora-2"
    provider_operation_id: str
    prompt_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    artifact_checksum_sha256: str = Field(pattern=SHA256_PATTERN)
    duration_seconds: Literal[4, 8, 12] = 12
    width: Literal[720, 1280] = 720
    height: Literal[720, 1280] = 1280
    output_count: Literal[1] = 1
    post_count: Literal[1] = 1
    estimated_cost_usd: float = Field(ge=0, le=1.50)
    canonical_audio_removed: Literal[True] = True
    rights_status: Literal["rights_verified"] = "rights_verified"
    synthetic_media: Literal[True] = True
    completed_at: datetime
