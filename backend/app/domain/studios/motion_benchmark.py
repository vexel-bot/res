from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from .contracts import StudioContract
from .creative_autonomy import VideoFamilyV1

SHA256_PATTERN = r"^[0-9a-fA-F]{64}$"
OPAQUE_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,159}$"


class MotionGoldenRenderV1(StudioContract):
    mode: Literal["normal", "reduced_motion"]
    projection_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    artifact_path: str = Field(min_length=1, max_length=4000)
    artifact_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    width: int = Field(ge=320, le=4096)
    height: int = Field(ge=320, le=4096)
    frame_rate: float = Field(ge=12, le=60)
    duration_milliseconds: int = Field(ge=100, le=300_000)
    checkpoint_frame_digests: dict[int, str] = Field(min_length=3, max_length=20)
    technical_qc_passed: bool

    @model_validator(mode="after")
    def validate_checkpoints(self) -> MotionGoldenRenderV1:
        if any(frame < 0 for frame in self.checkpoint_frame_digests):
            raise ValueError("Motion golden checkpoint frames must be non-negative")
        if any(
            not re.fullmatch(SHA256_PATTERN, digest)
            for digest in self.checkpoint_frame_digests.values()
        ):
            raise ValueError("Motion golden checkpoint digests must be SHA-256")
        return self


class MotionGoldenCaseEvidenceV1(StudioContract):
    case_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    family: VideoFamilyV1
    graph_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    covered_property_paths: list[str] = Field(min_length=5, max_length=100)
    parent_child_covered: bool
    typography_covered: bool
    transition_covered: bool
    audio_clock_covered: bool
    normal: MotionGoldenRenderV1
    reduced_motion: MotionGoldenRenderV1
    normal_repeat_artifact_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    normal_repeat_checkpoint_digests: dict[int, str] = Field(min_length=3, max_length=20)
    exact_artifact_repeat: bool
    exact_checkpoint_repeat: bool
    reduced_motion_static_track_count: int = Field(ge=1)
    eligible: bool
    blockers: list[str]

    @model_validator(mode="after")
    def validate_case(self) -> MotionGoldenCaseEvidenceV1:
        expected = (
            self.normal.technical_qc_passed
            and self.reduced_motion.technical_qc_passed
            and self.exact_checkpoint_repeat
            and self.parent_child_covered
            and self.typography_covered
            and self.transition_covered
            and self.audio_clock_covered
            and not self.blockers
        )
        if self.eligible != expected:
            raise ValueError("Motion golden case eligibility disagrees with evidence")
        return self


class MotionGoldenSuiteEvidenceV1(StudioContract):
    schema_version: Literal["studio.motion-golden-suite-evidence.v1"] = (
        "studio.motion-golden-suite-evidence.v1"
    )
    suite_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    provider: Literal["hyperframes.cli"] = "hyperframes.cli"
    provider_version: str = Field(min_length=1, max_length=240)
    cases: list[MotionGoldenCaseEvidenceV1] = Field(min_length=4, max_length=4)
    eligible: bool
    blockers: list[str]
    rendered_at: datetime

    @model_validator(mode="after")
    def validate_suite(self) -> MotionGoldenSuiteEvidenceV1:
        case_ids = [item.case_id for item in self.cases]
        families = [item.family for item in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("Motion golden case ids must be unique")
        if len(families) != len(set(families)) or len(families) != 4:
            raise ValueError("Motion golden suite requires one case per family")
        expected = all(item.eligible for item in self.cases) and not self.blockers
        if self.eligible != expected:
            raise ValueError("Motion golden suite eligibility disagrees with case evidence")
        return self
