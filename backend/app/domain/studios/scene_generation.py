from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from .contracts import StudioContract
from .hybrid_video import HybridExecutionBindingV1, HybridProductionPolicyV1


class GenerativeCameraIntentV1(StudioContract):
    type: Literal["static", "push_in", "pull_out", "pan", "orbit"] = "static"
    control: Literal["prompt_guidance"] = "prompt_guidance"


class SceneGenerationRequestV1(StudioContract):
    schema_version: Literal["studio.scene-generation-request.v1"] = "studio.scene-generation-request.v1"
    expected_document_revision: int = Field(ge=1)
    scene_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,119}$")
    requirement_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,119}$")
    operation: Literal["text_to_video"] = "text_to_video"
    prompt: str = Field(min_length=8, max_length=4000)
    seed: int = Field(ge=0, le=2**63 - 1)
    duration_seconds: float = Field(gt=0, le=2.0625)
    profile_id: Literal["wan21-t2v-local-experimental-v1"] = "wan21-t2v-local-experimental-v1"
    camera_intent: GenerativeCameraIntentV1 = Field(default_factory=GenerativeCameraIntentV1)

    @model_validator(mode="after")
    def fixed_experimental_duration(self):
        if self.duration_seconds > 33 / 16:
            raise ValueError("scene_generation_duration_unavailable")
        return self


LOCAL_VIDEO_PROFILE_IDS = {
    "animatediff-lightning-sd15-a-v1",
    "animatediff-lightning-sd15-b-v1",
    "wan21-t2v-local-experimental-v1",
}


class SceneGenerationRequestV2(StudioContract):
    schema_version: Literal["studio.scene-generation-request.v2"] = "studio.scene-generation-request.v2"
    expected_document_revision: int = Field(ge=1)
    scene_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,119}$")
    requirement_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,119}$")
    operation: Literal["text_to_video"] = "text_to_video"
    prompt: str = Field(min_length=8, max_length=4000)
    seed: int = Field(ge=0, le=2**63 - 1)
    duration_seconds: float = Field(gt=0, le=2)
    profile_id: str = Field(pattern=r"^[a-z0-9][a-z0-9.-]{2,119}$")
    camera_intent: GenerativeCameraIntentV1 = Field(default_factory=GenerativeCameraIntentV1)
    execution_binding: HybridExecutionBindingV1 | None = None
    selection_policy: HybridProductionPolicyV1 | None = None

    @model_validator(mode="after")
    def binding_is_complete(self):
        if bool(self.execution_binding) != bool(self.selection_policy):
            raise ValueError("scene_generation_execution_binding_incomplete")
        if self.execution_binding and self.execution_binding.profile_id != self.profile_id:
            raise ValueError("scene_generation_execution_profile_mismatch")
        return self

    @model_validator(mode="after")
    def registered_profile(self):
        if self.profile_id not in LOCAL_VIDEO_PROFILE_IDS:
            raise ValueError("scene_generation_profile_unavailable")
        maximum = 1 if self.profile_id.endswith("-a-v1") else 2
        if self.duration_seconds > maximum:
            raise ValueError("scene_generation_duration_unavailable")
        return self


class SceneGenerationCapabilityV1(StudioContract):
    schema_version: Literal["studio.scene-generation-capability.v1"] = "studio.scene-generation-capability.v1"
    state: Literal["unavailable", "experimental", "qualified"]
    profile_id: str
    operation: Literal["text_to_video"] = "text_to_video"
    preflight: dict = Field(default_factory=dict)
    service_accessible: bool = False
    model_readiness: Literal[
        "ready", "missing", "legacy_unprovisioned", "not_installed", "blocked_resources", "unavailable", "unknown"
    ] = "unknown"
    resource_admission: Literal["admitted", "blocked_resources", "unavailable", "unknown"] = "unknown"
    adapter_support: Literal["available", "unavailable", "unknown"] = "unknown"
    qualification_state: Literal["unavailable", "experimental", "qualified"] = "unavailable"
    paid_fallback_enabled: Literal[False] = False
    profiles: list[dict] = Field(default_factory=list)


class SceneCandidateEvaluationV1(StudioContract):
    relevance: int = Field(ge=1, le=5)
    subject_identity: int = Field(ge=1, le=5)
    temporal_continuity: int = Field(ge=1, le=5)
    action_clarity: int = Field(ge=1, le=5)
    sequence_inspected: bool
    flicker_observed: bool = False
    deformation_observed: bool = False
    observation: str = Field(min_length=1, max_length=4000)


class SceneGenerationAdmissionRequestV1(StudioContract):
    schema_version: Literal["studio.scene-generation-admission-request.v1"] = (
        "studio.scene-generation-admission-request.v1"
    )
    expected_document_revision: int = Field(ge=1)
    decision: Literal["accept", "reject"]
    comment: str | None = Field(default=None, max_length=2000)
    evaluation: SceneCandidateEvaluationV1 | None = None

    @model_validator(mode="after")
    def accepted_candidate_is_evidenced(self):
        if self.decision == "accept":
            if self.evaluation is None or not self.evaluation.sequence_inspected:
                raise ValueError("scene_generation_sequence_evaluation_required")
            if min(
                self.evaluation.relevance,
                self.evaluation.subject_identity,
                self.evaluation.temporal_continuity,
                self.evaluation.action_clarity,
            ) < 4:
                raise ValueError("scene_generation_candidate_below_acceptance_threshold")
            if self.evaluation.flicker_observed or self.evaluation.deformation_observed:
                raise ValueError("scene_generation_candidate_visual_defect")
        return self
