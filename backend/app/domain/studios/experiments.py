from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from .contracts import StudioContract

SHA256_PATTERN = r"^[0-9a-fA-F]{64}$"
OPAQUE_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,159}$"


class AvatarCatalogRequirementV1(StudioContract):
    total_profiles: int = Field(ge=1, le=100)
    men: int = Field(ge=0, le=100)
    women: int = Field(ge=0, le=100)
    minimum_age: int = Field(ge=18, le=120)
    casting_release_required: bool = True
    consent_required: bool = True
    publication_allowed_during_benchmark: bool = False

    @model_validator(mode="after")
    def validate_catalog(self) -> AvatarCatalogRequirementV1:
        if self.men + self.women != self.total_profiles:
            raise ValueError("Catalog presentation counts must equal total profiles")
        if not self.casting_release_required or not self.consent_required:
            raise ValueError("Avatar catalogs require release and consent")
        if self.publication_allowed_during_benchmark:
            raise ValueError("Benchmark outputs must remain private")
        return self


class ExperimentRoundV1(StudioContract):
    round_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    sequence: int = Field(ge=1, le=100)
    profile_count: int = Field(ge=1, le=100)
    copy_archetypes: list[str] = Field(min_length=1, max_length=30)
    durations_seconds: list[int] = Field(min_length=1, max_length=20)
    scenarios: list[str] = Field(min_length=1, max_length=30)
    formats: list[str] = Field(min_length=1, max_length=20)
    expected_output_count: int = Field(ge=1, le=100000)
    max_experiment_spend_usd: float = Field(gt=0, le=1_000_000)
    max_gpu_hours: float = Field(gt=0, le=100_000)
    max_wall_clock_hours: float = Field(gt=0, le=100_000)
    max_regeneration_rate: float = Field(ge=0, le=1)
    prerequisite_round_ids: list[str] = Field(default_factory=list, max_length=20)
    human_review_required: bool = True
    cleanup_receipt_required: bool = True

    @model_validator(mode="after")
    def validate_round_matrix(self) -> ExperimentRoundV1:
        for label, values in (
            ("copy archetypes", self.copy_archetypes),
            ("durations", self.durations_seconds),
            ("scenarios", self.scenarios),
            ("formats", self.formats),
            ("prerequisites", self.prerequisite_round_ids),
        ):
            if len(values) != len(set(values)):
                raise ValueError(f"Experiment round {label} must be unique")
        matrix_size = (
            self.profile_count
            * len(self.copy_archetypes)
            * len(self.durations_seconds)
            * len(self.scenarios)
            * len(self.formats)
        )
        if self.expected_output_count != matrix_size:
            raise ValueError(
                f"Expected output count must equal the declared matrix size ({matrix_size})"
            )
        if not self.human_review_required or not self.cleanup_receipt_required:
            raise ValueError("Every identity experiment round requires review and cleanup evidence")
        return self


class AvatarAdExperimentProtocolV1(StudioContract):
    schema_version: Literal["studio.avatar-ad-experiment-protocol.v1"] = (
        "studio.avatar-ad-experiment-protocol.v1"
    )
    protocol_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    status: Literal["draft", "frozen", "approved", "retired"]
    benchmark_policy_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    frozen_at: datetime
    frozen_by: str = Field(pattern=OPAQUE_ID_PATTERN)
    catalog: AvatarCatalogRequirementV1
    rounds: list[ExperimentRoundV1] = Field(min_length=1, max_length=20)
    per_output_minute_cost_ceiling_usd: float = Field(gt=0, le=10_000)
    required_controls: list[str] = Field(min_length=1, max_length=100)
    notes: list[str] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def validate_protocol(self) -> AvatarAdExperimentProtocolV1:
        round_ids = [item.round_id for item in self.rounds]
        sequences = [item.sequence for item in self.rounds]
        if len(round_ids) != len(set(round_ids)):
            raise ValueError("Experiment round ids must be unique")
        if sequences != list(range(1, len(self.rounds) + 1)):
            raise ValueError("Experiment rounds must be ordered and contiguous")
        known: set[str] = set()
        previous_spend = 0.0
        previous_outputs = 0
        for item in self.rounds:
            if item.profile_count != self.catalog.total_profiles:
                raise ValueError("Every round must cover the complete catalog")
            if any(prerequisite not in known for prerequisite in item.prerequisite_round_ids):
                raise ValueError("Round prerequisites must reference earlier rounds")
            if item.expected_output_count <= previous_outputs:
                raise ValueError("Experiment output counts must increase by round")
            if item.max_experiment_spend_usd <= previous_spend:
                raise ValueError("Experiment spend caps must increase by round")
            known.add(item.round_id)
            previous_outputs = item.expected_output_count
            previous_spend = item.max_experiment_spend_usd
        if len(self.required_controls) != len(set(self.required_controls)):
            raise ValueError("Required experiment controls must be unique")
        return self


def avatar_ad_experiment_protocol_digest(protocol: AvatarAdExperimentProtocolV1) -> str:
    canonical = json.dumps(
        protocol.model_dump(mode="json", by_alias=True, exclude_none=True),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()
