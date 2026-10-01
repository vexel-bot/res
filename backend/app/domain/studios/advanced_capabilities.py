from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from .contracts import StudioContract

SHA256_PATTERN = r"^[0-9a-fA-F]{64}$"
OPAQUE_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,159}$"


class AdvancedCapabilityCandidateV1(StudioContract):
    candidate_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    capability: Literal["voice_clone", "avatar_video", "lip_sync", "generative_scene"]
    repository_name: str = Field(min_length=1, max_length=240)
    source_revision: str = Field(min_length=7, max_length=120)
    local_source_available: bool
    license_document_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    code_license: str = Field(min_length=1, max_length=240)
    transitive_license_status: Literal["verified", "review_required", "rejected"]
    model_asset_status: Literal["complete", "incomplete", "not_acquired"]
    pt_br_status: Literal["passed", "failed", "unmeasured"]
    hardware_status: Literal["eligible", "ineligible", "unmeasured"]
    supply_chain_status: Literal["promotable", "incomplete", "rejected"]
    provider_registry_status: Literal["not_registered", "evaluation", "approved"]
    biometric_inference_executed: Literal[False] = False
    notes: list[str] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def validate_candidate(self) -> AdvancedCapabilityCandidateV1:
        if self.provider_registry_status == "approved":
            if not (
                self.transitive_license_status == "verified"
                and self.model_asset_status == "complete"
                and self.pt_br_status == "passed"
                and self.hardware_status == "eligible"
                and self.supply_chain_status == "promotable"
            ):
                raise ValueError("Approved advanced provider lacks promotion evidence")
        return self


class AdvancedIdentitySlotV1(StudioContract):
    slot_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    authorization_status: Literal["not_acquired", "consented", "revoked"]
    identity_version_id: str | None = Field(default=None, pattern=OPAQUE_ID_PATTERN)
    voice_version_id: str | None = Field(default=None, pattern=OPAQUE_ID_PATTERN)
    consent_grant_id: str | None = Field(default=None, pattern=OPAQUE_ID_PATTERN)
    benchmark_case_ids: list[str] = Field(default_factory=list, max_length=24)
    private_artifact_count: int = Field(default=0, ge=0, le=10_000)

    @model_validator(mode="after")
    def validate_slot(self) -> AdvancedIdentitySlotV1:
        bindings = (self.identity_version_id, self.voice_version_id, self.consent_grant_id)
        if self.authorization_status == "consented" and not all(bindings):
            raise ValueError("A consented identity slot requires identity, voice and grant bindings")
        if self.authorization_status != "consented" and any(bindings):
            raise ValueError("An unauthorized identity slot cannot retain biometric bindings")
        if self.authorization_status != "consented" and self.private_artifact_count:
            raise ValueError("Unauthorized identity slots cannot contain generated artifacts")
        return self


class AdvancedCapabilityAuditV1(StudioContract):
    schema_version: Literal["studio.advanced-capability-audit.v1"] = (
        "studio.advanced-capability-audit.v1"
    )
    audit_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    candidates: list[AdvancedCapabilityCandidateV1] = Field(min_length=6, max_length=30)
    identity_slots: list[AdvancedIdentitySlotV1] = Field(min_length=6, max_length=6)
    required_authorized_identity_count: Literal[6] = 6
    authorized_identity_count: int = Field(ge=0, le=6)
    required_benchmark_case_count: Literal[24] = 24
    executed_benchmark_case_count: int = Field(ge=0, le=24)
    revocation_rail_implemented: bool
    deletion_rail_implemented: bool
    revocation_deletion_drill_passed: bool
    disclosure_required: Literal[True] = True
    provenance_required: Literal[True] = True
    publish_synthetic_grant_count: int = Field(ge=0)
    enabled_provider_ids: list[str] = Field(default_factory=list, max_length=0)
    fallback_modes: list[
        Literal["real_person", "licensed_stock", "faceless_motion"]
    ] = Field(min_length=3, max_length=3)
    activation_eligible: bool
    blockers: list[str] = Field(min_length=1, max_length=100)
    audited_at: datetime

    @model_validator(mode="after")
    def validate_audit(self) -> AdvancedCapabilityAuditV1:
        slots = [item.slot_id for item in self.identity_slots]
        if len(slots) != len(set(slots)):
            raise ValueError("Advanced identity slot ids must be unique")
        candidate_ids = [item.candidate_id for item in self.candidates]
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("Advanced candidate ids must be unique")
        authorized = sum(
            item.authorization_status == "consented" for item in self.identity_slots
        )
        cases = sum(len(item.benchmark_case_ids) for item in self.identity_slots)
        if authorized != self.authorized_identity_count:
            raise ValueError("Authorized identity count disagrees with identity slots")
        if cases != self.executed_benchmark_case_count:
            raise ValueError("Benchmark case count disagrees with identity slots")
        expected = (
            self.authorized_identity_count == self.required_authorized_identity_count
            and self.executed_benchmark_case_count == self.required_benchmark_case_count
            and self.revocation_deletion_drill_passed
            and self.publish_synthetic_grant_count >= self.required_authorized_identity_count
            and any(item.provider_registry_status == "approved" for item in self.candidates)
            and not self.blockers
        )
        if self.activation_eligible != expected:
            raise ValueError("Advanced capability activation disagrees with gate evidence")
        if self.activation_eligible != bool(self.enabled_provider_ids):
            raise ValueError("Provider enablement must match the activation gate")
        if set(self.fallback_modes) != {
            "real_person",
            "licensed_stock",
            "faceless_motion",
        }:
            raise ValueError("Advanced audit requires all non-biometric fallbacks")
        return self
