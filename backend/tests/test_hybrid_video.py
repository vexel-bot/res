from types import SimpleNamespace

import pytest

from app.domain.studios.hybrid_video import (
    CapabilityReadinessV1,
    CapabilityUnitCostV1,
    HybridCapabilityManifestV1,
    HybridExecutionProfileV1,
    HybridProductionPolicyV1,
    HybridSelectionRequestV1,
    select_hybrid_profile,
)
from app.services.studios.hybrid_video import hybrid_capability_manifest


def profile(profile_id, *, state="qualified", environment="local", amount=None, uses=("product_motion",)):
    return HybridExecutionProfileV1(
        profileId=profile_id,
        providerId=profile_id,
        capability="motion" if "motion" in profile_id else "generative_video",
        operations=["compose_motion_graph"] if "motion" in profile_id else ["text_to_video"],
        environment=environment,
        qualificationState=state,
        commercialUse="approved",
        readiness=CapabilityReadinessV1(
            serviceConfigured=True,
            serviceAccessible=True,
            modelInstalled=True,
            resourcesAvailable=True,
            inferenceValidated=True,
            qualifiedUseCases=list(uses),
        ),
        maximumNativeSeconds=10,
        cost=CapabilityUnitCostV1(
            currency="USD" if amount is not None else "LOCAL",
            unit="second" if amount is not None else "local_execution",
            amount=amount,
            priceVersion="test-v1",
        ),
    )


def test_selector_prefers_qualified_then_measured_use_case_and_cost():
    manifest = HybridCapabilityManifestV1(
        profiles=[
            profile("video-exp", state="experimental", amount=0.01),
            profile("video-costly", amount=0.10, uses=("product", "broll")),
            profile("video-cheap", amount=0.05, uses=("product", "broll")),
        ]
    )
    policy = HybridProductionPolicyV1(
        mode="auto",
        allowedProfileIds=["video-exp", "video-costly", "video-cheap"],
        allowExperimental=True,
        allowRemoteApi=True,
        maximumGeneratedSecondsTotal=10,
        maximumApiSpendUsd=1,
        budgetEnvelopeId="pilot",
    )
    result = select_hybrid_profile(
        manifest,
        policy,
        HybridSelectionRequestV1(
            capability="generative_video",
            operation="text_to_video",
            durationSeconds=4,
            remainingApiBudgetUsd=1,
        ),
    )
    assert result.selected_profile_id == "video-cheap"


def test_selector_fails_closed_for_budget_remote_and_serverless():
    manifest = HybridCapabilityManifestV1(
        profiles=[
            profile("video-api", environment="remote_api", amount=0.5),
            profile("video-gpu", environment="serverless", amount=0),
        ]
    )
    policy = HybridProductionPolicyV1(mode="auto", allowedProfileIds=["video-api", "video-gpu"])
    result = select_hybrid_profile(
        manifest,
        policy,
        HybridSelectionRequestV1(
            capability="generative_video",
            operation="text_to_video",
            durationSeconds=4,
        ),
    )
    assert result.selected_profile_id is None
    assert "remote_api_not_allowed" in result.rejected_profiles["video-api"]
    assert "serverless_gpu_not_authorized" in result.rejected_profiles["video-gpu"]


def test_paid_profile_requires_duration_without_throwing():
    manifest = HybridCapabilityManifestV1(profiles=[profile("video-api", environment="remote_api", amount=0.05)])
    policy = HybridProductionPolicyV1(
        mode="auto",
        allowedProfileIds=["video-api"],
        allowRemoteApi=True,
        maximumApiSpendUsd=1,
        budgetEnvelopeId="pilot",
    )
    result = select_hybrid_profile(
        manifest,
        policy,
        HybridSelectionRequestV1(capability="generative_video", operation="text_to_video"),
    )
    assert result.selected_profile_id is None
    assert "hybrid_selection_duration_required_for_cost" in result.rejected_profiles["video-api"]


def test_manifest_does_not_equate_configuration_with_qualification():
    settings = SimpleNamespace(
        studio_local_diffusion_enabled=True,
        gemini_video_generation_enabled=True,
    )
    manifest = hybrid_capability_manifest(settings)
    by_id = {item.profile_id: item for item in manifest.profiles}
    local = by_id["animatediff-lightning-sd15-a-v1"]
    assert local.readiness.service_configured is True
    assert local.qualification_state == "experimental"
    assert local.readiness.inference_validated is False
    assert manifest.paid_fallback_enabled is False
    assert manifest.remote_gpu_authorized is False
    longcat = by_id["longcat-avatar-1.5-ai2v-480p-int8-experimental-v1"]
    assert longcat.capability == "avatar_video"
    assert longcat.operations == ["image_audio_to_avatar"]
    assert longcat.qualification_state == "unavailable"
    assert longcat.readiness.model_installed is False
    assert longcat.default_parameters["segmentFrames"] == 93
    assert longcat.default_parameters["overlapFrames"] == 13


def test_qualified_profile_requires_complete_evidence():
    with pytest.raises(ValueError, match="complete_evidence"):
        HybridExecutionProfileV1(
            profileId="bad-profile",
            providerId="bad-provider",
            capability="motion",
            operations=["compose_motion_graph"],
            environment="local",
            qualificationState="qualified",
            commercialUse="approved",
            readiness={},
            cost={"priceVersion": "test"},
        )


def test_selector_requires_operational_readiness_even_for_experiments():
    candidate = profile("video-exp", state="experimental")
    candidate.readiness.service_accessible = False
    manifest = HybridCapabilityManifestV1(profiles=[candidate])
    result = select_hybrid_profile(
        manifest,
        HybridProductionPolicyV1(
            mode="auto", allowedProfileIds=[candidate.profile_id], allowExperimental=True
        ),
        HybridSelectionRequestV1(
            capability="generative_video",
            operation="text_to_video",
            durationSeconds=1,
        ),
    )
    assert result.selected_profile_id is None
    assert "service_not_accessible" in result.rejected_profiles[candidate.profile_id]


def test_selector_blocks_remote_profile_with_unknown_price():
    candidate = profile("video-api", state="experimental", environment="remote_api")
    candidate.cost = CapabilityUnitCostV1(
        currency="USD", unit="second", amount=None, priceVersion="unknown"
    )
    result = select_hybrid_profile(
        HybridCapabilityManifestV1(profiles=[candidate]),
        HybridProductionPolicyV1(
            mode="auto",
            allowedProfileIds=[candidate.profile_id],
            allowExperimental=True,
            allowRemoteApi=True,
            maximumApiSpendUsd=1,
            budgetEnvelopeId="pilot",
        ),
        HybridSelectionRequestV1(
            capability="generative_video",
            operation="text_to_video",
            durationSeconds=1,
            remainingApiBudgetUsd=1,
        ),
    )
    assert result.selected_profile_id is None
    assert "hybrid_selection_price_required" in result.rejected_profiles[candidate.profile_id]


def test_selector_returns_immutable_execution_binding():
    candidate = profile("video-local", state="experimental")
    candidate.model_id = "model-a"
    candidate.model_revision = "revision-a"
    candidate.runtime_revision = "runtime-a"
    candidate.default_parameters = {"fps": 25, "steps": 8}
    result = select_hybrid_profile(
        HybridCapabilityManifestV1(profiles=[candidate]),
        HybridProductionPolicyV1(
            mode="auto", allowedProfileIds=[candidate.profile_id], allowExperimental=True
        ),
        HybridSelectionRequestV1(
            capability="generative_video",
            operation="text_to_video",
            durationSeconds=1,
            requestedParameters={"seed": 42},
        ),
    )
    assert result.execution_binding is not None
    assert result.execution_binding.model_revision == "revision-a"
    assert result.execution_binding.effective_parameters == {"fps": 25, "steps": 8, "seed": 42}
    assert len(result.execution_binding.binding_digest_sha256) == 64
