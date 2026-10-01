from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from .benchmarking import OPAQUE_REFERENCE_PATTERN
from .contracts import StudioContract

SHA256_PATTERN = r"^[0-9a-fA-F]{64}$"


class SpeechReviewAssignmentV1(StudioContract):
    assignment_id: str = Field(pattern=OPAQUE_REFERENCE_PATTERN)
    case_id: str = Field(min_length=1, max_length=160)
    review_clip_id: str = Field(pattern=OPAQUE_REFERENCE_PATTERN)
    audio_asset_id: str = Field(pattern=OPAQUE_REFERENCE_PATTERN)
    output_checksum_sha256: str = Field(pattern=SHA256_PATTERN)
    script: str = Field(min_length=1, max_length=100000)
    script_digest_sha256: str = Field(pattern=SHA256_PATTERN)

    @model_validator(mode="after")
    def validate_script(self) -> SpeechReviewAssignmentV1:
        if hashlib.sha256(self.script.encode("utf-8")).hexdigest() != self.script_digest_sha256.lower():
            raise ValueError("Speech review script digest does not match text")
        return self


class SpeechReviewerPacketV1(StudioContract):
    schema_version: Literal["studio.speech-reviewer-packet.v1"] = (
        "studio.speech-reviewer-packet.v1"
    )
    packet_id: str = Field(pattern=OPAQUE_REFERENCE_PATTERN)
    run_id: str = Field(min_length=1, max_length=160)
    reviewer_pseudonym: str = Field(pattern=OPAQUE_REFERENCE_PATTERN)
    blinded_candidate_label: str = Field(min_length=1, max_length=160)
    assignments: list[SpeechReviewAssignmentV1] = Field(min_length=1, max_length=100000)

    @model_validator(mode="after")
    def validate_assignments(self) -> SpeechReviewerPacketV1:
        assignment_ids = [item.assignment_id for item in self.assignments]
        case_ids = [item.case_id for item in self.assignments]
        if len(assignment_ids) != len(set(assignment_ids)) or len(case_ids) != len(set(case_ids)):
            raise ValueError("Speech reviewer packet assignments and cases must be unique")
        return self


class SpeechReviewPlanV1(StudioContract):
    schema_version: Literal["studio.speech-review-plan.v1"] = "studio.speech-review-plan.v1"
    plan_id: str = Field(pattern=OPAQUE_REFERENCE_PATTERN)
    run_id: str = Field(min_length=1, max_length=160)
    suite_id: str = Field(min_length=1, max_length=160)
    candidate_id: str = Field(min_length=1, max_length=160)
    evidence_bundle_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    generated_at: datetime
    packets: list[SpeechReviewerPacketV1] = Field(min_length=3, max_length=100)

    @model_validator(mode="after")
    def validate_packets(self) -> SpeechReviewPlanV1:
        packet_ids = [item.packet_id for item in self.packets]
        reviewers = [item.reviewer_pseudonym for item in self.packets]
        if len(packet_ids) != len(set(packet_ids)) or len(reviewers) != len(set(reviewers)):
            raise ValueError("Speech review packet ids and reviewers must be unique")
        if any(item.run_id != self.run_id for item in self.packets):
            raise ValueError("Speech review packets must match plan run")
        labels = {item.blinded_candidate_label for item in self.packets}
        if len(labels) != 1:
            raise ValueError("Every speech reviewer must receive the same blinded label")
        expected_cases = {item.case_id for item in self.packets[0].assignments}
        if any({item.case_id for item in packet.assignments} != expected_cases for packet in self.packets):
            raise ValueError("Every speech reviewer must receive the same case set")
        expected_bindings = {
            item.case_id: (
                item.review_clip_id,
                item.audio_asset_id,
                item.output_checksum_sha256.lower(),
                item.script_digest_sha256.lower(),
            )
            for item in self.packets[0].assignments
        }
        for packet in self.packets[1:]:
            observed = {
                item.case_id: (
                    item.review_clip_id,
                    item.audio_asset_id,
                    item.output_checksum_sha256.lower(),
                    item.script_digest_sha256.lower(),
                )
                for item in packet.assignments
            }
            if observed != expected_bindings:
                raise ValueError("Every speech reviewer must receive identical blinded assets")
        return self


class SpeechReviewResponseV1(StudioContract):
    assignment_id: str = Field(pattern=OPAQUE_REFERENCE_PATTERN)
    script_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    output_checksum_sha256: str = Field(pattern=SHA256_PATTERN)
    naturalness_mos: int = Field(ge=1, le=5)
    intelligibility_word_accuracy: float = Field(ge=0, le=1)
    critical_term_accuracy: float = Field(ge=0, le=1)
    critical_off_script: bool
    repeat_or_truncation: bool


class SpeechReviewSubmissionV1(StudioContract):
    schema_version: Literal["studio.speech-review-submission.v1"] = (
        "studio.speech-review-submission.v1"
    )
    submission_id: str = Field(pattern=OPAQUE_REFERENCE_PATTERN)
    packet_id: str = Field(pattern=OPAQUE_REFERENCE_PATTERN)
    plan_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    reviewer_pseudonym: str = Field(pattern=OPAQUE_REFERENCE_PATTERN)
    submitted_at: datetime
    responses: list[SpeechReviewResponseV1] = Field(min_length=1, max_length=100000)

    @model_validator(mode="after")
    def validate_responses(self) -> SpeechReviewSubmissionV1:
        assignment_ids = [item.assignment_id for item in self.responses]
        if len(assignment_ids) != len(set(assignment_ids)):
            raise ValueError("Speech review response assignments must be unique")
        return self


class SpeechReviewBundleV1(StudioContract):
    schema_version: Literal["studio.speech-review-bundle.v1"] = "studio.speech-review-bundle.v1"
    bundle_id: str = Field(pattern=OPAQUE_REFERENCE_PATTERN)
    run_id: str = Field(min_length=1, max_length=160)
    plan_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    generated_at: datetime
    submissions: list[SpeechReviewSubmissionV1] = Field(min_length=3, max_length=100)

    @model_validator(mode="after")
    def validate_submissions(self) -> SpeechReviewBundleV1:
        submission_ids = [item.submission_id for item in self.submissions]
        reviewers = [item.reviewer_pseudonym for item in self.submissions]
        if len(submission_ids) != len(set(submission_ids)) or len(reviewers) != len(set(reviewers)):
            raise ValueError("Speech review submissions and reviewers must be unique")
        if any(item.plan_digest_sha256.lower() != self.plan_digest_sha256.lower() for item in self.submissions):
            raise ValueError("Speech review submissions must bind the same plan")
        return self


def speech_review_plan_digest(plan: SpeechReviewPlanV1) -> str:
    return _digest(plan)


def speech_review_bundle_digest(bundle: SpeechReviewBundleV1) -> str:
    return _digest(bundle)


def _digest(contract: StudioContract) -> str:
    canonical = json.dumps(
        contract.model_dump(mode="json", by_alias=True),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()
