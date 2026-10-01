from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from .contracts import StudioContract, StudioWorkerRuntimeManifestV1

SHA256_PATTERN = r"^[0-9a-fA-F]{64}$"
OPAQUE_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,159}$"
OCI_DIGEST_PATTERN = r"^sha256:[0-9a-fA-F]{64}$"


class ArtifactIntegrityV1(StudioContract):
    method: Literal["git_commit", "sha256", "oci_digest"]
    value: str = Field(min_length=7, max_length=160)
    size_bytes: int | None = Field(default=None, gt=0, le=100 * 1024**3)

    @model_validator(mode="after")
    def validate_integrity(self) -> ArtifactIntegrityV1:
        if self.method == "git_commit":
            valid = len(self.value) == 40 and all(
                character in "0123456789abcdefABCDEF" for character in self.value
            )
        elif self.method == "sha256":
            valid = len(self.value) == 64 and all(
                character in "0123456789abcdefABCDEF" for character in self.value
            )
            if self.size_bytes is None:
                raise ValueError("SHA-256 artifacts require a byte size")
        else:
            valid = self.value.startswith("sha256:") and len(self.value) == 71 and all(
                character in "0123456789abcdefABCDEF" for character in self.value[7:]
            )
        if not valid:
            raise ValueError(f"Invalid {self.method} integrity value")
        if self.method == "git_commit" and self.size_bytes is not None:
            raise ValueError("Git commit integrity cannot claim artifact bytes")
        return self


class ArtifactLicenseDecisionV1(StudioContract):
    declared_license: str = Field(min_length=1, max_length=240)
    evidence_url: str = Field(min_length=1, max_length=4000)
    evidence_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    commercial_saas_use_allowed: bool | None = None
    decision: Literal["approved", "review_required", "rejected"]
    rationale: str = Field(min_length=1, max_length=2000)

    @model_validator(mode="after")
    def validate_legal_decision(self) -> ArtifactLicenseDecisionV1:
        if self.decision == "approved" and self.commercial_saas_use_allowed is not True:
            raise ValueError("Approved artifacts require explicit commercial SaaS permission")
        if self.decision == "rejected" and self.commercial_saas_use_allowed is True:
            raise ValueError("Rejected artifacts cannot claim approved commercial SaaS use")
        return self


class ArtifactRecordV1(StudioContract):
    artifact_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    component_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    kind: Literal["code", "model", "runtime", "container", "dataset"]
    role: str = Field(min_length=1, max_length=160)
    required: bool = True
    source_url: str = Field(min_length=1, max_length=4000)
    source_revision: str = Field(min_length=7, max_length=240)
    expected_filename: str | None = Field(default=None, max_length=240)
    resolution_status: Literal["resolved", "unresolved", "rejected"]
    integrity: ArtifactIntegrityV1 | None = None
    verification_method: Literal[
        "git_remote",
        "vendor_metadata",
        "downloaded_external",
        "registry_manifest",
        "local_oci_layout",
        "not_verified",
    ]
    external_evaluation_ref: str | None = Field(default=None, pattern=OPAQUE_ID_PATTERN)
    license: ArtifactLicenseDecisionV1
    notes: list[str] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def validate_resolution(self) -> ArtifactRecordV1:
        if self.resolution_status == "resolved":
            if self.integrity is None or self.verification_method == "not_verified":
                raise ValueError("Resolved artifacts require verified integrity")
        elif self.integrity is not None:
            raise ValueError("Unresolved/rejected artifacts cannot carry trusted integrity")
        if self.verification_method == "downloaded_external":
            if (
                not self.external_evaluation_ref
                or self.integrity is None
                or self.integrity.method != "sha256"
            ):
                raise ValueError("Externally downloaded artifacts require opaque ref and SHA-256")
        elif self.external_evaluation_ref is not None:
            raise ValueError("External evaluation refs are only valid for downloaded artifacts")
        if self.kind == "model" and self.resolution_status == "resolved":
            if self.integrity is None or self.integrity.method != "sha256":
                raise ValueError("Resolved model artifacts require SHA-256 bytes")
        if self.kind == "container" and self.resolution_status == "resolved":
            if self.integrity is None or self.integrity.method != "oci_digest":
                raise ValueError("Resolved containers require an OCI digest")
        if self.kind == "code" and self.resolution_status == "resolved":
            if self.integrity is None or self.integrity.method != "git_commit":
                raise ValueError("Resolved code artifacts require a git commit")
        return self


class ArtifactInventoryV1(StudioContract):
    schema_version: Literal["studio.artifact-inventory.v1"] = "studio.artifact-inventory.v1"
    inventory_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    capability: str = Field(min_length=1, max_length=160)
    policy_digests_sha256: list[str] = Field(min_length=1, max_length=30)
    status: Literal["incomplete", "review_required", "approved", "rejected"]
    frozen_at: datetime
    frozen_by: str = Field(pattern=OPAQUE_ID_PATTERN)
    required_artifact_ids: list[str] = Field(min_length=1, max_length=100)
    artifacts: list[ArtifactRecordV1] = Field(min_length=1, max_length=200)
    notes: list[str] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def validate_inventory(self) -> ArtifactInventoryV1:
        if len(self.policy_digests_sha256) != len(set(self.policy_digests_sha256)) or any(
            len(item) != 64 or any(character not in "0123456789abcdefABCDEF" for character in item)
            for item in self.policy_digests_sha256
        ):
            raise ValueError("Artifact inventory policy digests must be unique SHA-256 values")
        artifact_ids = [item.artifact_id for item in self.artifacts]
        component_ids = [item.component_id for item in self.artifacts]
        if len(artifact_ids) != len(set(artifact_ids)):
            raise ValueError("Artifact inventory ids must be unique")
        if len(component_ids) != len(set(component_ids)):
            raise ValueError("Artifact inventory component ids must be unique")
        if len(self.required_artifact_ids) != len(set(self.required_artifact_ids)):
            raise ValueError("Required artifact ids must be unique")
        records = {item.artifact_id: item for item in self.artifacts}
        missing = sorted(set(self.required_artifact_ids) - records.keys())
        if missing:
            raise ValueError(f"Required artifact records are missing: {missing}")
        required = [records[item] for item in self.required_artifact_ids]
        declared_required = {item.artifact_id for item in self.artifacts if item.required}
        if set(self.required_artifact_ids) != declared_required:
            raise ValueError("Required artifact ids must match records marked required")
        if any(
            item.resolution_status == "rejected" or item.license.decision == "rejected"
            for item in required
        ):
            expected = "rejected"
        elif any(item.resolution_status == "unresolved" for item in required):
            expected = "incomplete"
        elif any(item.license.decision == "review_required" for item in required):
            expected = "review_required"
        else:
            expected = "approved"
        if self.status != expected:
            raise ValueError(f"Artifact inventory status must be {expected}")
        return self


class ProviderCandidateManifestV1(StudioContract):
    schema_version: Literal["studio.provider-candidate-manifest.v1"] = (
        "studio.provider-candidate-manifest.v1"
    )
    candidate_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    provider_ids: list[str] = Field(min_length=1, max_length=20)
    provider_versions: dict[str, str] = Field(min_length=1, max_length=20)
    capabilities: list[
        Literal[
            "vision_normalization",
            "visual_geometry",
            "object_tracking",
            "physical_scene_understanding",
            "video_world_model",
            "physical_plausibility",
            "stock_voice",
            "voice_clone",
        ]
    ] = Field(min_length=1, max_length=20)
    status: Literal["disabled", "evaluation", "approved"]
    implementation_modules: list[str] = Field(min_length=1, max_length=20)
    artifact_inventory_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    artifact_inventory_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    artifact_inventory_status: Literal[
        "incomplete", "review_required", "approved", "rejected"
    ]
    required_artifact_ids: list[str] = Field(min_length=1, max_length=100)
    code_digests_sha256: dict[str, str] = Field(min_length=1, max_length=20)
    default_parameters_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    advertised_by_worker_manifest: bool = False
    benchmark_evidence_digest_sha256: str | None = Field(
        default=None,
        pattern=SHA256_PATTERN,
    )
    shadow_evidence_digest_sha256: str | None = Field(
        default=None,
        pattern=SHA256_PATTERN,
    )
    runtime_evidence_digest_sha256: str | None = Field(
        default=None,
        pattern=SHA256_PATTERN,
    )
    legal_approval_ref: str | None = Field(default=None, pattern=OPAQUE_ID_PATTERN)
    activation_gates: list[str] = Field(min_length=1, max_length=50)
    limitations: list[str] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def validate_candidate(self) -> ProviderCandidateManifestV1:
        for label, values in (
            ("provider ids", self.provider_ids),
            ("capabilities", self.capabilities),
            ("implementation modules", self.implementation_modules),
            ("required artifact ids", self.required_artifact_ids),
        ):
            if len(values) != len(set(values)):
                raise ValueError(f"Provider candidate {label} must be unique")
        if set(self.provider_versions) != set(self.provider_ids):
            raise ValueError("Provider candidate versions must cover exactly its provider ids")
        if set(self.code_digests_sha256) != set(self.provider_ids) or any(
            len(value) != 64
            or any(character not in "0123456789abcdefABCDEF" for character in value)
            for value in self.code_digests_sha256.values()
        ):
            raise ValueError("Provider candidate code digests must cover exactly its provider ids")
        if self.status != "approved" and self.advertised_by_worker_manifest:
            raise ValueError("Unapproved provider candidates cannot be advertised")
        if self.status == "approved" and (
            self.artifact_inventory_status != "approved"
            or not self.advertised_by_worker_manifest
            or not self.benchmark_evidence_digest_sha256
            or not self.shadow_evidence_digest_sha256
            or not self.legal_approval_ref
        ):
            raise ValueError(
                "Approved provider candidates require approved artifacts, benchmark, legal ref and advertisement"
            )
        return self


class ProviderPromotionEvidenceV1(StudioContract):
    """Immutable evidence bundle required before a candidate can be advertised."""

    schema_version: Literal["studio.provider-promotion-evidence.v1"] = (
        "studio.provider-promotion-evidence.v1"
    )
    candidate_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    candidate_manifest_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    artifact_inventory_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    artifact_inventory_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    artifact_inventory_status: Literal["incomplete", "review_required", "approved", "rejected"]
    benchmark_evidence_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    shadow_evidence_digest_sha256: str | None = Field(
        default=None,
        pattern=SHA256_PATTERN,
    )
    legal_approval_ref: str = Field(pattern=OPAQUE_ID_PATTERN)
    image_digest: str = Field(pattern=OCI_DIGEST_PATTERN)
    image_sbom_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    image_provenance_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    worker_manifest_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    image_platform: Literal["linux/amd64"]
    worker_manifest_advertised: bool
    attestation_verified: bool
    no_egress_verified: bool
    cleanup_verified: bool
    tenant_scoped_storage_verified: bool
    promoted_at: datetime
    promoted_by: str = Field(pattern=OPAQUE_ID_PATTERN)


class ProviderPromotionGateResultV1(StudioContract):
    """Decision record; eligible is intentionally impossible with incomplete evidence."""

    schema_version: Literal["studio.provider-promotion-gate-result.v1"] = (
        "studio.provider-promotion-gate-result.v1"
    )
    candidate_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    candidate_manifest_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    evidence_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    worker_manifest_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    decision: Literal["eligible", "blocked", "incomplete"]
    blocking_reasons: list[str] = Field(default_factory=list, max_length=100)
    incomplete_reasons: list[str] = Field(default_factory=list, max_length=100)
    evaluator_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    evaluated_at: datetime


def provider_promotion_evidence_digest(evidence: ProviderPromotionEvidenceV1) -> str:
    return _contract_digest(evidence)


def evaluate_provider_promotion_gate(
    candidate: ProviderCandidateManifestV1,
    inventory: ArtifactInventoryV1,
    evidence: ProviderPromotionEvidenceV1,
    worker_manifest: StudioWorkerRuntimeManifestV1,
    *,
    evaluated_at: datetime,
) -> ProviderPromotionGateResultV1:
    """Fail closed on bindings and keep missing external evidence explicitly incomplete."""

    candidate_digest = provider_candidate_manifest_digest(candidate)
    inventory_digest = artifact_inventory_digest(inventory)
    manifest_digest_value = _contract_digest(worker_manifest)
    blocking: list[str] = []
    incomplete: list[str] = []

    if evidence.candidate_id != candidate.candidate_id:
        blocking.append("candidate_id_mismatch")
    if evidence.candidate_manifest_digest_sha256.lower() != candidate_digest:
        blocking.append("candidate_manifest_binding_mismatch")
    if evidence.artifact_inventory_id != inventory.inventory_id:
        blocking.append("artifact_inventory_id_mismatch")
    if evidence.artifact_inventory_digest_sha256.lower() != inventory_digest:
        blocking.append("artifact_inventory_binding_mismatch")
    if candidate.artifact_inventory_id != inventory.inventory_id:
        blocking.append("candidate_inventory_id_mismatch")
    if candidate.artifact_inventory_digest_sha256.lower() != inventory_digest:
        blocking.append("candidate_inventory_binding_mismatch")
    if evidence.worker_manifest_digest_sha256.lower() != manifest_digest_value:
        blocking.append("worker_manifest_binding_mismatch")
    worker_capabilities = {
        "vision_normalization": "vision_gpu",
        "visual_geometry": "vision_gpu",
        "object_tracking": "vision_gpu",
        "physical_scene_understanding": "vision_gpu",
        "video_world_model": "vision_gpu",
        "physical_plausibility": "vision_gpu",
        "planning_copy": "llm_gpu",
        "stock_voice": "speech_cpu",
        "voice_clone": "speech_gpu",
    }
    expected_worker_capabilities = {
        worker_capabilities[capability] for capability in candidate.capabilities
    }
    if len(expected_worker_capabilities) != 1:
        blocking.append("candidate_worker_capability_ambiguous")
    elif worker_manifest.capability not in expected_worker_capabilities:
        blocking.append("worker_capability_mismatch")
    if "preflight" in worker_manifest.runtime_version.lower():
        incomplete.append("preflight_runtime_not_promotable")
    if set(worker_manifest.providers) != set(candidate.provider_ids):
        blocking.append("worker_provider_advertisement_mismatch")
    if not evidence.worker_manifest_advertised:
        incomplete.append("worker_manifest_not_advertised")

    if candidate.status != "approved":
        incomplete.append(f"candidate_status:{candidate.status}")
    if inventory.status != "approved":
        incomplete.append(f"artifact_inventory_status:{inventory.status}")
    if evidence.artifact_inventory_status != "approved":
        incomplete.append(f"evidence_inventory_status:{evidence.artifact_inventory_status}")
    if candidate.artifact_inventory_status != "approved":
        incomplete.append(f"candidate_inventory_status:{candidate.artifact_inventory_status}")
    if not candidate.benchmark_evidence_digest_sha256:
        incomplete.append("candidate_benchmark_evidence_missing")
    elif candidate.benchmark_evidence_digest_sha256.lower() != evidence.benchmark_evidence_digest_sha256.lower():
        blocking.append("benchmark_evidence_binding_mismatch")
    if not candidate.shadow_evidence_digest_sha256:
        incomplete.append("candidate_shadow_evidence_missing")
    elif not evidence.shadow_evidence_digest_sha256:
        incomplete.append("promotion_shadow_evidence_missing")
    elif (
        candidate.shadow_evidence_digest_sha256.lower()
        != evidence.shadow_evidence_digest_sha256.lower()
    ):
        blocking.append("shadow_evidence_binding_mismatch")
    if not candidate.legal_approval_ref:
        incomplete.append("candidate_legal_approval_missing")
    elif candidate.legal_approval_ref != evidence.legal_approval_ref:
        blocking.append("legal_approval_binding_mismatch")
    for field, reason in (
        ("attestation_verified", "worker_attestation_missing"),
        ("no_egress_verified", "no_egress_not_verified"),
        ("cleanup_verified", "cleanup_not_verified"),
        ("tenant_scoped_storage_verified", "tenant_scoped_storage_not_verified"),
    ):
        if not getattr(evidence, field):
            incomplete.append(reason)

    decision = "blocked" if blocking else "incomplete" if incomplete else "eligible"
    return ProviderPromotionGateResultV1(
        candidate_id=candidate.candidate_id,
        candidate_manifest_digest_sha256=candidate_digest,
        evidence_digest_sha256=provider_promotion_evidence_digest(evidence),
        worker_manifest_digest_sha256=manifest_digest_value,
        decision=decision,
        blocking_reasons=sorted(set(blocking)),
        incomplete_reasons=sorted(set(incomplete)),
        evaluator_digest_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        evaluated_at=evaluated_at,
    )


def artifact_inventory_digest(inventory: ArtifactInventoryV1) -> str:
    canonical = json.dumps(
        inventory.model_dump(mode="json", by_alias=True, exclude_none=True),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def provider_candidate_manifest_digest(manifest: ProviderCandidateManifestV1) -> str:
    canonical = json.dumps(
        manifest.model_dump(mode="json", by_alias=True, exclude_none=True),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _contract_digest(contract: StudioContract) -> str:
    canonical = json.dumps(
        contract.model_dump(mode="json", by_alias=True, exclude_none=True),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()
