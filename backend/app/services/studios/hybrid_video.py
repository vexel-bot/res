"""Build the observable hybrid capability registry from current runtime state."""

from __future__ import annotations

import httpx

from ...config import get_settings
from ...domain.studios.hybrid_video import (
    CapabilityReadinessV1,
    CapabilityUnitCostV1,
    HybridCapabilityManifestV1,
    HybridExecutionProfileV1,
)


def _readiness(
    configured=False,
    accessible=False,
    installed=False,
    resources=False,
    validated=False,
    *,
    uses=(),
    blockers=(),
):
    return CapabilityReadinessV1(
        service_configured=configured,
        service_accessible=accessible,
        model_installed=installed,
        resources_available=resources,
        inference_validated=validated,
        qualified_use_cases=list(uses),
        blocking_reasons=list(blockers),
    )


def hybrid_capability_manifest(settings=None) -> HybridCapabilityManifestV1:
    settings = settings or get_settings()
    local_diffusion_enabled = bool(getattr(settings, "studio_local_diffusion_enabled", False))
    gemini_video_enabled = bool(getattr(settings, "gemini_video_generation_enabled", False))
    longcat_enabled = bool(getattr(settings, "studio_longcat_avatar_enabled", False))
    longcat_worker = None
    if longcat_enabled and getattr(settings, "studio_longcat_avatar_token", None):
        try:
            response = httpx.get(
                settings.studio_longcat_avatar_url.rstrip("/") + "/api/v1/capabilities",
                headers={"Authorization": "Bearer " + settings.studio_longcat_avatar_token.get_secret_value()},
                timeout=2,
            )
            response.raise_for_status()
            longcat_worker = response.json()
        except (httpx.HTTPError, ValueError, AttributeError):
            longcat_worker = None
    profiles = [
        HybridExecutionProfileV1(
            profile_id="musetalk-1.5-evidence-v1",
            provider_id="musetalk",
            capability="lip_sync",
            operations=["dub_existing_presenter"],
            environment="local",
            qualification_state="unavailable",
            commercial_use="conditional",
            readiness=_readiness(blockers=("license_review_required", "benchmark_evidence_pending")),
            input_requirements=["authorized_presenter_video", "speech_audio", "identity_consent"],
            cost=CapabilityUnitCostV1(price_version="local-unpriced-v1"),
            evidence_refs=["benchmarks/studios/identity/avatar-pt-br-policy.v1.json"],
        ),
        HybridExecutionProfileV1(
            profile_id="latentsync-1.6-evidence-v1",
            provider_id="latentsync",
            capability="lip_sync",
            operations=["dub_existing_presenter"],
            environment="serverless",
            qualification_state="unavailable",
            commercial_use="rejected",
            readiness=_readiness(blockers=("model_license_rejected", "local_vram_insufficient")),
            input_requirements=["authorized_presenter_video", "speech_audio", "identity_consent"],
            cost=CapabilityUnitCostV1(currency="USD", unit="gpu_second", amount=None, price_version="unpriced"),
            evidence_refs=["benchmarks/studios/identity/avatar-pt-br-policy.v1.json"],
        ),
        HybridExecutionProfileV1(
            profile_id="longcat-avatar-1.5-ai2v-480p-int8-experimental-v1",
            provider_id="local.longcat-avatar-1.5",
            capability="avatar_video",
            operations=["image_audio_to_avatar"],
            environment="local",
            qualification_state=(
                "experimental" if longcat_worker and longcat_worker.get("usableNow") else "unavailable"
            ),
            commercial_use="conditional",
            readiness=_readiness(
                configured=longcat_enabled,
                accessible=longcat_worker is not None,
                installed=bool(
                    longcat_worker
                    and not any(reason == "weights_not_installed" for reason in longcat_worker.get("reasons", []))
                ),
                resources=bool(longcat_worker and longcat_worker.get("usableNow")),
                validated=False,
                blockers=tuple(longcat_worker.get("reasons", []))
                if longcat_worker
                else (
                    "longcat_avatar_disabled" if not longcat_enabled else "worker_not_accessible",
                    "compatible_multi_gpu_hardware_required",
                    "dependency_license_chain_pending",
                    "pt_br_visual_qualification_pending",
                ),
            ),
            input_requirements=[
                "authorized_reference_image",
                "final_speech_audio",
                "identity_consent",
            ],
            maximum_native_seconds=3.72,
            cost=CapabilityUnitCostV1(price_version="local-unmeasured-v1"),
            model_id="meituan-longcat/LongCat-Video-Avatar-1.5",
            model_revision="92016c71d5d318d0f5d84e4db30015a571484ab6",
            runtime_revision="6b3f4b8582a8bc3f20f795735f5383716c4ba794",
            default_parameters={
                "resolution": "832x480",
                "fps": 25,
                "inferenceSteps": 8,
                "quantization": "int8",
                "textGuidanceScale": 1.0,
                "audioGuidanceScale": 1.0,
                "segmentFrames": 93,
                "overlapFrames": 13,
                "presenters": 1,
                "framing": "medium",
            },
            evidence_refs=[
                "benchmarks/studios/identity/longcat-avatar-1.5-screening-policy.v1.json",
                "workers/longcat-avatar/model-manifest.json",
                "https://github.com/meituan-longcat/LongCat-Video",
            ],
        ),
        HybridExecutionProfileV1(
            profile_id="animatediff-lightning-sd15-a-v1",
            provider_id="local-diffusion",
            capability="generative_video",
            operations=["text_to_video"],
            environment="local",
            qualification_state="experimental" if local_diffusion_enabled else "unavailable",
            commercial_use="conditional",
            readiness=_readiness(
                local_diffusion_enabled,
                False,
                local_diffusion_enabled,
                False,
                False,
                blockers=("numerical_equivalence_pending", "visual_qualification_pending")
                if local_diffusion_enabled
                else ("local_diffusion_disabled",),
            ),
            maximum_native_seconds=1,
            cost=CapabilityUnitCostV1(price_version="local-measured-v1"),
            evidence_refs=["docs/studios/LOCAL_DIFFUSION_REVISED_PLAN_2026-09-10.md"],
        ),
        HybridExecutionProfileV1(
            profile_id="veo-3.1-lite-720p-experimental-v1",
            provider_id="google-veo",
            capability="generative_video",
            operations=["text_to_video", "image_to_video"],
            environment="remote_api",
            qualification_state="experimental" if gemini_video_enabled else "unavailable",
            commercial_use="approved",
            readiness=_readiness(
                gemini_video_enabled,
                False,
                True,
                True,
                False,
                blockers=("provider_account_validation_pending", "real_media_benchmark_pending")
                if gemini_video_enabled
                else ("gemini_video_disabled",),
            ),
            maximum_native_seconds=10,
            cost=CapabilityUnitCostV1(currency="USD", unit="second", amount=0.05, price_version="google-2026-09-14"),
            model_id=getattr(settings, "studio_gemini_video_model", "veo-3.1-lite-generate-preview"),
            model_revision="google-api-price-and-model-binding-2026-09-14",
            runtime_revision="res-gemini-editing-adapter-v1",
            evidence_refs=["https://ai.google.dev/gemini-api/docs/pricing"],
        ),
        HybridExecutionProfileV1(
            profile_id="wan2.2-ti2v-5b-serverless-experimental-v1",
            provider_id="wan2.2",
            capability="generative_video",
            operations=["text_to_video", "image_to_video"],
            environment="serverless",
            qualification_state="unavailable",
            commercial_use="conditional",
            readiness=_readiness(blockers=("serverless_gpu_not_authorized", "worker_not_deployed")),
            maximum_native_seconds=5,
            cost=CapabilityUnitCostV1(currency="USD", unit="gpu_second", amount=None, price_version="unpriced"),
            evidence_refs=["https://github.com/Wan-Video/Wan2.2"],
        ),
    ]
    from ...providers.studios.craft import engine_capability

    profiles = [profile for profile in profiles if profile.capability != "motion"]
    native = engine_capability("effectcraft")
    available = native["available"]
    profiles.append(
        HybridExecutionProfileV1(
            profile_id="effectcraft-motion-v1",
            provider_id="craft.effectcraft",
            capability="motion",
            operations=["compose_motion_graph"],
            environment="local",
            qualification_state="experimental" if available else "unavailable",
            commercial_use="approved",
            readiness=_readiness(
                configured=available,
                accessible=available,
                installed=available,
                resources=available,
                blockers=() if available else (native.get("reason", "craft_runtime_unavailable"),),
            ),
            input_requirements=["motion_graph"],
            cost=CapabilityUnitCostV1(price_version="local-unpriced-v1"),
            evidence_refs=["workers/craft/sources.lock.json"],
        )
    )
    return HybridCapabilityManifestV1(profiles=profiles)
