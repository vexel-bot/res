from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from .contracts import SHA256_PATTERN, StudioContract
from .creative_intelligence import CharacterBibleV1, RightsStatusV1


class AvatarVisualSourceV1(StudioContract):
    """One consent/right-bound base video used to drive a visual avatar."""

    schema_version: Literal["studio.avatar-visual-source.v1"] = (
        "studio.avatar-visual-source.v1"
    )
    source_kind: Literal["authorized_performer_video", "synthetic_original_video"]
    asset_id: str = Field(min_length=1, max_length=160)
    checksum_sha256: str = Field(pattern=SHA256_PATTERN)
    duration_milliseconds: int = Field(ge=8_000, le=300_000)
    width: int = Field(ge=720, le=7680)
    height: int = Field(ge=720, le=7680)
    exactly_one_person: Literal[True] = True
    face_visible_and_unobstructed: Literal[True] = True
    neutral_capture_approved: Literal[True] = True
    rights_status: RightsStatusV1
    consent_grant_id: str | None = Field(default=None, min_length=1, max_length=160)
    voice_training_allowed: Literal[False] = False

    @model_validator(mode="after")
    def validate_source_rights(self) -> AvatarVisualSourceV1:
        if self.rights_status not in {"open_license", "rights_verified"}:
            raise ValueError("Avatar visual sources require cleared rights")
        if self.source_kind == "authorized_performer_video" and not self.consent_grant_id:
            raise ValueError("Performer video requires an explicit consent grant")
        if self.source_kind == "synthetic_original_video" and self.consent_grant_id:
            raise ValueError("Synthetic original video cannot claim performer consent")
        return self


class FixedAvatarModelV1(StudioContract):
    schema_version: Literal["studio.fixed-avatar-model.v1"] = (
        "studio.fixed-avatar-model.v1"
    )
    avatar_id: str = Field(min_length=1, max_length=160)
    gender_presentation: Literal["man", "woman"]
    character: CharacterBibleV1
    system_roles: list[str] = Field(min_length=1, max_length=20)
    performance_strengths: list[str] = Field(min_length=1, max_length=20)
    prohibited_uses: list[str] = Field(min_length=1, max_length=50)
    visual_source: AvatarVisualSourceV1 | None = None
    provider_candidate: Literal["heygem-visual-only", "musetalk-v1.5-local"] = "heygem-visual-only"
    provider_status: Literal[
        "disabled", "pending_source_video", "pending_benchmark", "approved"
    ] = "disabled"
    local_voice_only: Literal[True] = True

    @model_validator(mode="after")
    def validate_provider_status(self) -> FixedAvatarModelV1:
        if self.character.identity_kind != "fictional_original":
            raise ValueError("The fixed system cast must use original fictional characters")
        if self.provider_status in {"pending_benchmark", "approved"} and not self.visual_source:
            raise ValueError("A benchmarkable avatar requires a validated base video")
        if self.provider_status == "approved":
            raise ValueError("Avatar models cannot self-approve through their specification")
        return self


class FixedAvatarCastV1(StudioContract):
    schema_version: Literal["studio.fixed-avatar-cast.v1"] = "studio.fixed-avatar-cast.v1"
    cast_id: str = Field(min_length=1, max_length=160)
    models: list[FixedAvatarModelV1] = Field(min_length=6, max_length=6)
    council_lenses: list[str] = Field(min_length=1, max_length=10)
    shared_continuity_rules: list[str] = Field(min_length=1, max_length=50)

    @model_validator(mode="after")
    def validate_cast(self) -> FixedAvatarCastV1:
        ids = [model.avatar_id for model in self.models]
        character_ids = [model.character.character_id for model in self.models]
        if len(ids) != len(set(ids)) or len(character_ids) != len(set(character_ids)):
            raise ValueError("Avatar and character ids must be unique")
        presentations = [model.gender_presentation for model in self.models]
        if presentations.count("man") != 3 or presentations.count("woman") != 3:
            raise ValueError("The fixed cast requires exactly three men and three women")
        return self


class AvatarSourceVideoSpecificationV1(StudioContract):
    duration_milliseconds: Literal[8000, 12000] = 8000
    resolution: Literal["720x1280", "768x1280", "1080x1920"] = "1080x1920"
    aspect_ratio: Literal["9:16"] = "9:16"
    shot_count: Literal[1] = 1
    camera: str = Field(min_length=1, max_length=1000)
    performance: str = Field(min_length=1, max_length=2000)
    lighting: str = Field(min_length=1, max_length=1000)
    environment: str = Field(min_length=1, max_length=1000)
    audio: str = Field(min_length=1, max_length=1000)
    positive_prompt: str = Field(min_length=1, max_length=8000)
    negative_constraints: list[str] = Field(min_length=1, max_length=50)


class AvatarPilotCouncilDecisionV1(StudioContract):
    dominant_lens: str = Field(min_length=1, max_length=200)
    supporting_lens: str = Field(min_length=1, max_length=200)
    decision: str = Field(min_length=1, max_length=2000)
    rejected: list[str] = Field(min_length=1, max_length=20)


class AvatarPilotVerificationV1(StudioContract):
    external_request_sent: bool = False
    video_generated: bool = False
    heygem_model_created: bool = False
    external_cost_incurred_usd: float = Field(default=0, ge=0)
    generation_attempt_count: int = Field(default=0, ge=0, le=100)
    provider_request_id: str | None = Field(default=None, min_length=1, max_length=200)
    failure_reason: str | None = Field(default=None, min_length=1, max_length=1000)

    @model_validator(mode="after")
    def validate_attempt_record(self) -> AvatarPilotVerificationV1:
        if self.external_request_sent != (self.generation_attempt_count > 0):
            raise ValueError("External request flag must match the recorded attempt count")
        if self.provider_request_id and not self.external_request_sent:
            raise ValueError("Provider request id requires an external request")
        if self.video_generated and self.failure_reason:
            raise ValueError("A successful video cannot retain a generation failure")
        return self


class SingleAvatarPilotV1(StudioContract):
    """Fail-closed production record for one base video and one visual avatar."""

    schema_version: Literal["studio.single-avatar-pilot.v1"] = (
        "studio.single-avatar-pilot.v1"
    )
    pilot_id: str = Field(min_length=1, max_length=160)
    avatar_id: str = Field(min_length=1, max_length=160)
    base_video_count: Literal[1] = 1
    source_video: AvatarVisualSourceV1 | None = None
    video_generation_provider: Literal[
        "gemini-omni-1.1-flash",
        "veo-3.1-lite-generate-preview",
        "ltx-video-0.9.8-zero-gpu",
        "authorized-capture",
        "openai-sora-2",
    ]
    provider_free_tier_verified: bool = False
    external_spend_limit_usd: float = Field(ge=0, le=10_000)
    production_state: Literal[
        "blocked_no_zero_cost_provider",
        "blocked_zero_gpu_generation_failed",
        "blocked_provider_quota_exhausted",
        "blocked_provider_authentication_failed",
        "awaiting_voice_casting",
        "awaiting_authorized_capture",
        "source_video_ready",
        "heygem_runtime_blocked",
        "avatar_pending_benchmark",
        "avatar_rendered_private_review",
    ]
    visual_provider: Literal["heygem-visual-only", "musetalk-v1.5-local"] = "heygem-visual-only"
    voice_route: Literal["local-only"] = "local-only"
    training_video_reuse: Literal["one-video-only"] = "one-video-only"
    blockers: list[str] = Field(default_factory=list, max_length=30)
    source_video_specification: AvatarSourceVideoSpecificationV1
    council_decision: AvatarPilotCouncilDecisionV1
    verification: AvatarPilotVerificationV1

    @model_validator(mode="after")
    def validate_single_video_gate(self) -> SingleAvatarPilotV1:
        source_required_states = {
            "source_video_ready",
            "heygem_runtime_blocked",
            "avatar_pending_benchmark",
            "avatar_rendered_private_review",
        }
        if self.production_state in source_required_states and not self.source_video:
            raise ValueError("This pilot state requires exactly one validated base video")
        if self.source_video and self.production_state in {
            "blocked_no_zero_cost_provider",
            "blocked_zero_gpu_generation_failed",
            "blocked_provider_authentication_failed",
            "awaiting_voice_casting",
            "awaiting_authorized_capture",
        }:
            raise ValueError("A blocked source stage cannot already claim a base video")
        if (
            self.video_generation_provider == "gemini-omni-1.1-flash"
            and not self.provider_free_tier_verified
            and self.external_spend_limit_usd == 0
            and self.production_state != "blocked_no_zero_cost_provider"
        ):
            raise ValueError("Paid Gemini video generation must remain blocked at zero spend")
        if self.verification.external_cost_incurred_usd > self.external_spend_limit_usd:
            raise ValueError("Recorded external cost exceeds the approved spend limit")
        if self.verification.video_generated and not self.source_video:
            raise ValueError("Generated-video verification requires an admitted source video")
        if self.verification.heygem_model_created and not self.source_video:
            raise ValueError("HeyGem verification requires an admitted source video")
        return self
