"""Provider-neutral qualification and routing contracts for hybrid video production."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

from pydantic import Field, model_validator

from .contracts import StudioContract

HybridCapability = Literal[
    "motion",
    "lip_sync",
    "avatar_video",
    "stock_voice",
    "voice_clone",
    "generative_video",
]
QualificationState = Literal["unavailable", "experimental", "qualified"]


class CapabilityReadinessV1(StudioContract):
    service_configured: bool = False
    service_accessible: bool = False
    model_installed: bool = False
    resources_available: bool = False
    inference_validated: bool = False
    qualified_use_cases: list[str] = Field(default_factory=list, max_length=40)
    blocking_reasons: list[str] = Field(default_factory=list, max_length=40)


class HybridUseCaseEvidenceV1(StudioContract):
    use_case: str = Field(min_length=1, max_length=160)
    accepted_candidates: int = Field(default=0, ge=0)
    total_candidates: int = Field(default=0, ge=0)
    median_seconds_to_accepted_result: float | None = Field(default=None, ge=0)
    mean_cost_per_accepted_result_usd: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def accepted_does_not_exceed_total(self):
        if self.accepted_candidates > self.total_candidates:
            raise ValueError("hybrid_use_case_acceptance_invalid")
        return self


class CapabilityUnitCostV1(StudioContract):
    currency: Literal["USD", "LOCAL"] = "LOCAL"
    unit: Literal["second", "gpu_second", "request", "local_execution"] = "local_execution"
    amount: float | None = Field(default=None, ge=0)
    price_version: str = Field(min_length=1, max_length=160)
    includes_cold_start: bool = False
    includes_storage: bool = False


class HybridExecutionProfileV1(StudioContract):
    profile_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{2,159}$")
    provider_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{2,159}$")
    capability: HybridCapability
    operations: list[str] = Field(min_length=1, max_length=20)
    environment: Literal["local", "remote_api", "serverless"]
    qualification_state: QualificationState
    commercial_use: Literal["approved", "conditional", "rejected", "unknown"]
    readiness: CapabilityReadinessV1
    input_requirements: list[str] = Field(default_factory=list, max_length=30)
    maximum_native_seconds: float | None = Field(default=None, gt=0, le=3600)
    cost: CapabilityUnitCostV1
    model_id: str | None = Field(default=None, max_length=240)
    model_revision: str | None = Field(default=None, max_length=240)
    runtime_revision: str | None = Field(default=None, max_length=240)
    default_parameters: dict[str, Any] = Field(default_factory=dict, max_length=80)
    use_case_evidence: list[HybridUseCaseEvidenceV1] = Field(default_factory=list, max_length=40)
    evidence_refs: list[str] = Field(default_factory=list, max_length=30)

    @model_validator(mode="after")
    def qualification_has_evidence(self):
        ready = self.readiness
        fully_ready = all(
            (
                ready.service_configured,
                ready.service_accessible,
                ready.model_installed,
                ready.resources_available,
                ready.inference_validated,
                bool(ready.qualified_use_cases),
                not ready.blocking_reasons,
            )
        )
        if self.qualification_state == "qualified" and not fully_ready:
            raise ValueError("hybrid_profile_qualified_without_complete_evidence")
        if self.commercial_use == "rejected" and self.qualification_state == "qualified":
            raise ValueError("hybrid_profile_commercially_rejected")
        return self


class HybridCapabilityManifestV1(StudioContract):
    schema_version: Literal["studio.hybrid-capability-manifest.v1"] = (
        "studio.hybrid-capability-manifest.v1"
    )
    profiles: list[HybridExecutionProfileV1]
    paid_fallback_enabled: Literal[False] = False
    remote_gpu_authorized: Literal[False] = False


class HybridProductionPolicyV1(StudioContract):
    schema_version: Literal["studio.hybrid-production-policy.v1"] = (
        "studio.hybrid-production-policy.v1"
    )
    mode: Literal["disabled", "auto"] = "disabled"
    allowed_profile_ids: list[str] = Field(default_factory=list, max_length=20)
    allow_experimental: bool = False
    allow_conditional_commercial_use: bool = False
    allow_remote_api: bool = False
    allow_serverless_gpu: Literal[False] = False
    paid_fallback_enabled: Literal[False] = False
    max_candidates_per_need: int = Field(default=1, ge=1, le=6)
    maximum_generated_seconds_total: float = Field(default=0, ge=0, le=600)
    budget_envelope_id: str | None = Field(default=None, max_length=160)
    maximum_api_spend_usd: float = Field(default=0, ge=0, le=100_000)

    @model_validator(mode="after")
    def enabled_policy_is_bounded(self):
        if self.mode == "auto" and not self.allowed_profile_ids:
            raise ValueError("hybrid_policy_profiles_required")
        if self.maximum_api_spend_usd and not self.budget_envelope_id:
            raise ValueError("hybrid_policy_budget_envelope_required")
        return self


class HybridSelectionRequestV1(StudioContract):
    capability: HybridCapability
    operation: str = Field(min_length=1, max_length=120)
    required_inputs: list[str] = Field(default_factory=list, max_length=30)
    duration_seconds: float | None = Field(default=None, gt=0, le=3600)
    remaining_api_budget_usd: float = Field(default=0, ge=0, le=100_000)
    use_case: str | None = Field(default=None, min_length=1, max_length=160)
    requested_parameters: dict[str, Any] = Field(default_factory=dict, max_length=80)


class HybridExecutionBindingV1(StudioContract):
    schema_version: Literal["studio.hybrid-execution-binding.v1"] = (
        "studio.hybrid-execution-binding.v1"
    )
    profile_id: str
    provider_id: str
    capability: HybridCapability
    operation: str
    environment: Literal["local", "remote_api", "serverless"]
    model_id: str | None = None
    model_revision: str | None = None
    runtime_revision: str | None = None
    effective_parameters: dict[str, Any] = Field(default_factory=dict)
    estimated_api_cost_usd: float = Field(default=0, ge=0)
    evidence_refs: list[str] = Field(default_factory=list)
    binding_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class HybridSelectionResultV1(StudioContract):
    schema_version: Literal["studio.hybrid-selection-result.v1"] = "studio.hybrid-selection-result.v1"
    selected_profile_id: str | None = None
    blockers: list[str] = Field(default_factory=list)
    eligible_profile_ids: list[str] = Field(default_factory=list)
    rejected_profiles: dict[str, list[str]] = Field(default_factory=dict)
    execution_binding: HybridExecutionBindingV1 | None = None


class HybridSelectionEnvelopeV1(StudioContract):
    policy: HybridProductionPolicyV1
    request: HybridSelectionRequestV1


def estimated_api_cost(profile: HybridExecutionProfileV1, duration_seconds: float | None) -> float:
    if profile.cost.currency != "USD":
        return 0
    if profile.cost.amount is None:
        raise ValueError("hybrid_selection_price_required")
    if profile.cost.unit in {"second", "gpu_second"}:
        if duration_seconds is None:
            raise ValueError("hybrid_selection_duration_required_for_cost")
        return profile.cost.amount * duration_seconds
    return profile.cost.amount


def select_hybrid_profile(
    manifest: HybridCapabilityManifestV1,
    policy: HybridProductionPolicyV1,
    request: HybridSelectionRequestV1,
) -> HybridSelectionResultV1:
    rejected: dict[str, list[str]] = {}
    eligible: list[tuple[HybridExecutionProfileV1, float]] = []
    allowed = set(policy.allowed_profile_ids)
    for profile in manifest.profiles:
        reasons: list[str] = []
        if policy.mode == "disabled" or profile.profile_id not in allowed:
            reasons.append("profile_not_allowed")
        if profile.capability != request.capability or request.operation not in profile.operations:
            reasons.append("operation_unsupported")
        if profile.qualification_state == "unavailable":
            reasons.append("profile_unavailable")
        elif profile.qualification_state == "experimental" and not policy.allow_experimental:
            reasons.append("experimental_not_allowed")
        if profile.commercial_use == "rejected" or (
            profile.commercial_use != "approved" and not policy.allow_conditional_commercial_use
        ):
            reasons.append("commercial_use_not_approved")
        if profile.environment == "remote_api" and not policy.allow_remote_api:
            reasons.append("remote_api_not_allowed")
        if profile.environment == "serverless":
            reasons.append("serverless_gpu_not_authorized")
        ready = profile.readiness
        operational = (
            ready.service_configured,
            ready.service_accessible,
            ready.model_installed,
            ready.resources_available,
        )
        for ok, reason in zip(
            operational,
            (
                "service_not_configured",
                "service_not_accessible",
                "model_not_installed",
                "resources_unavailable",
            ),
            strict=True,
        ):
            if not ok:
                reasons.append(reason)
        if (
            request.use_case
            and profile.qualification_state == "qualified"
            and request.use_case not in ready.qualified_use_cases
        ):
            reasons.append("use_case_not_qualified")
        if not set(profile.input_requirements) <= set(request.required_inputs):
            reasons.append("required_input_missing")
        if (
            request.duration_seconds is not None
            and profile.maximum_native_seconds is not None
            and request.duration_seconds > profile.maximum_native_seconds
        ):
            reasons.append("native_duration_exceeded")
        if profile.readiness.blocking_reasons:
            reasons.extend(profile.readiness.blocking_reasons)
        try:
            cost = estimated_api_cost(profile, request.duration_seconds)
        except ValueError as error:
            reasons.append(str(error))
            cost = 0
        budget = min(policy.maximum_api_spend_usd, request.remaining_api_budget_usd)
        if cost > budget:
            reasons.append("budget_insufficient")
        if reasons:
            rejected[profile.profile_id] = sorted(set(reasons))
        else:
            eligible.append((profile, cost))
    # Qualified beats experimental. Within a state, prefer measured acceptance,
    # then cost and provider id for deterministic routing.
    def score(item: tuple[HybridExecutionProfileV1, float]):
        profile, cost = item
        evidence = next(
            (entry for entry in profile.use_case_evidence if entry.use_case == request.use_case),
            None,
        )
        acceptance = (
            evidence.accepted_candidates / evidence.total_candidates
            if evidence and evidence.total_candidates
            else 0
        )
        observed_cost = (
            evidence.mean_cost_per_accepted_result_usd
            if evidence and evidence.mean_cost_per_accepted_result_usd is not None
            else cost
        )
        observed_time = (
            evidence.median_seconds_to_accepted_result
            if evidence and evidence.median_seconds_to_accepted_result is not None
            else float("inf")
        )
        return (
            0 if profile.qualification_state == "qualified" else 1,
            -acceptance,
            observed_cost,
            observed_time,
            profile.profile_id,
        )

    eligible.sort(key=score)
    ids = [item[0].profile_id for item in eligible]
    blockers = [] if ids else sorted({reason for reasons in rejected.values() for reason in reasons})
    binding = None
    if eligible:
        selected, selected_cost = eligible[0]
        effective_parameters = {**selected.default_parameters, **request.requested_parameters}
        binding_payload = {
            "profileId": selected.profile_id,
            "providerId": selected.provider_id,
            "capability": selected.capability,
            "operation": request.operation,
            "environment": selected.environment,
            "modelId": selected.model_id,
            "modelRevision": selected.model_revision,
            "runtimeRevision": selected.runtime_revision,
            "effectiveParameters": effective_parameters,
            "estimatedApiCostUsd": selected_cost,
            "evidenceRefs": selected.evidence_refs,
        }
        digest = hashlib.sha256(
            json.dumps(binding_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        binding = HybridExecutionBindingV1(
            **binding_payload,
            bindingDigestSha256=digest,
        )
    return HybridSelectionResultV1(
        selected_profile_id=ids[0] if ids else None,
        eligible_profile_ids=ids,
        rejected_profiles=rejected,
        blockers=blockers or (["no_matching_profile"] if not manifest.profiles else []),
        execution_binding=binding,
    )
