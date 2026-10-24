"""CPU-only protocol shared by the HTTP boundary and isolated runner."""

from __future__ import annotations

import hashlib
import json
import math

from pydantic import BaseModel, ConfigDict, Field, model_validator

PROFILE = "longcat-avatar-1.5-ai2v-480p-int8-experimental-v1"


def request_digest(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class AvatarExecutionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    execution_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{7,159}$")
    profile_id: str
    request_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    reference_image_checksum_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    driving_audio_checksum_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    segment_count: int = Field(gt=0, le=27000)
    produced_frames: int = Field(gt=0)
    trim_tail_ms: int = Field(ge=0)
    avatar_request: dict

    @model_validator(mode="after")
    def validate_binding(self):
        payload = self.avatar_request
        if self.request_digest_sha256 != request_digest(payload):
            raise ValueError("request_digest_mismatch")
        if self.profile_id != PROFILE or payload.get("profileId") != PROFILE:
            raise ValueError("profile_not_supported")
        if payload.get("schemaVersion") != "studio.avatar-video-request.v2":
            raise ValueError("request_v2_required")
        if payload.get("operation") != "image_audio_to_avatar":
            raise ValueError("operation_not_supported")
        if (payload.get("width"), payload.get("height"), payload.get("fps")) != (
            832,
            480,
            25,
        ):
            raise ValueError("output_parameters_not_supported")
        image_checksum = payload.get("referenceImageChecksumSha256")
        audio_checksum = payload.get("drivingAudioChecksumSha256")
        if (
            not isinstance(image_checksum, str)
            or image_checksum.lower() != self.reference_image_checksum_sha256
        ):
            raise ValueError("reference_image_binding_mismatch")
        if (
            not isinstance(audio_checksum, str)
            or audio_checksum.lower() != self.driving_audio_checksum_sha256
        ):
            raise ValueError("driving_audio_binding_mismatch")
        duration = payload.get("drivingAudioDurationMs")
        seed = payload.get("seed")
        if type(duration) is not int or not 0 < duration <= 86_400_000:
            raise ValueError("duration_invalid")
        if type(seed) is not int or not 0 <= seed < 2**32:
            raise ValueError("seed_invalid")
        if (
            not isinstance(payload.get("performanceDirection"), str)
            or not 0 < len(payload["performanceDirection"]) <= 2000
        ):
            raise ValueError("performance_direction_required")
        segments = 1 + math.ceil(max(0, math.ceil(duration / 40) - 93) / 80)
        frames = 93 + (segments - 1) * 80
        if (self.segment_count, self.produced_frames, self.trim_tail_ms) != (
            segments,
            frames,
            frames * 40 - duration,
        ):
            raise ValueError("segment_timing_mismatch")
        return self
