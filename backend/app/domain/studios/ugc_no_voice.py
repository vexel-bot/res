from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field, model_validator

from .contracts import SHA256_PATTERN, StudioContract
from .ugc_acceptance import AVATAR_CANDIDATE_IDS, UgcAvatarCatalogSlotV1

CaptionLine = Annotated[str, Field(min_length=1, max_length=42)]


class UgcNoVoiceProfileV1(StudioContract):
    """Immutable audiovisual policy for the no-narration UGC lane."""

    schema_version: Literal["studio.ugc-no-voice-profile.v1"] = "studio.ugc-no-voice-profile.v1"
    audio_mode: Literal["natural-foley-only"] = "natural-foley-only"
    voice_policy: Literal["prohibited"] = "prohibited"
    captured_speech_policy: Literal["prohibited"] = "prohibited"
    music_policy: Literal["prohibited"] = "prohibited"
    captions: Literal["editorial-burned-in"] = "editorial-burned-in"
    sound_rights_required: Literal[True] = True
    avatar_rights_required: Literal[True] = True
    human_listening_review_required: Literal[True] = True
    publication_enabled: Literal[False] = False


class UgcNoVoiceSceneV1(StudioContract):
    setting: str = Field(min_length=1, max_length=400)
    background_direction: str = Field(min_length=1, max_length=1000)
    action_direction: str = Field(min_length=1, max_length=1000)
    continuity_constraints: list[str] = Field(min_length=2, max_length=12)


class UgcEditorialCaptionCueV1(StudioContract):
    cue_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,79}$")
    order: int = Field(ge=0, le=20)
    role: Literal["hook", "problem", "demo", "benefit", "offer", "cta"]
    start_seconds: float = Field(ge=0, le=300)
    end_seconds: float = Field(gt=0, le=300)
    lines: list[CaptionLine] = Field(min_length=1, max_length=2)
    safe_area: Literal["lower-third", "upper-third", "center"] = "lower-third"
    editorial_not_transcription: Literal[True] = True

    @model_validator(mode="after")
    def validate_timing_and_lines(self) -> UgcEditorialCaptionCueV1:
        if self.end_seconds <= self.start_seconds:
            raise ValueError("UGC caption end must be after start")
        if any(line != line.strip() for line in self.lines):
            raise ValueError("UGC caption lines must be trimmed")
        return self


class UgcNaturalSoundCueV1(StudioContract):
    cue_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,79}$")
    sound_class: Literal["room-tone", "object-foley", "movement-foley", "environment"]
    start_seconds: float = Field(ge=0, le=300)
    end_seconds: float = Field(gt=0, le=300)
    visible_action: str = Field(min_length=1, max_length=400)
    sound_direction: str = Field(min_length=1, max_length=400)
    source_license_required: Literal[True] = True
    captured_speech_allowed: Literal[False] = False
    music_allowed: Literal[False] = False

    @model_validator(mode="after")
    def validate_timing(self) -> UgcNaturalSoundCueV1:
        if self.end_seconds <= self.start_seconds:
            raise ValueError("UGC natural sound end must be after start")
        return self


class UgcNoVoiceCreativeCaseV1(StudioContract):
    schema_version: Literal["studio.ugc-no-voice-case.v1"] = "studio.ugc-no-voice-case.v1"
    case_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,79}$")
    niche: str = Field(min_length=1, max_length=160)
    concept: str = Field(min_length=1, max_length=240)
    avatar: UgcAvatarCatalogSlotV1
    scene: UgcNoVoiceSceneV1
    duration_seconds: Literal[15, 20, 30]
    width: Literal[1080] = 1080
    height: Literal[1920] = 1920
    fps: Literal[25, 30] = 30
    approved_facts: list[str] = Field(min_length=1, max_length=20)
    forbidden_claims: list[str] = Field(min_length=1, max_length=40)
    captions: list[UgcEditorialCaptionCueV1] = Field(min_length=4, max_length=8)
    natural_sounds: list[UgcNaturalSoundCueV1] = Field(min_length=2, max_length=12)

    @model_validator(mode="after")
    def validate_timeline(self) -> UgcNoVoiceCreativeCaseV1:
        caption_ids = [item.cue_id for item in self.captions]
        sound_ids = [item.cue_id for item in self.natural_sounds]
        if len(caption_ids) != len(set(caption_ids)) or len(sound_ids) != len(set(sound_ids)):
            raise ValueError("UGC no-voice cue ids must be unique within their track")
        if [item.order for item in self.captions] != list(range(len(self.captions))):
            raise ValueError("UGC no-voice caption order must be contiguous")
        if self.captions[0].role != "hook" or self.captions[-1].role != "cta":
            raise ValueError("UGC no-voice timeline must start with a hook and end with a CTA")
        if "demo" not in {item.role for item in self.captions}:
            raise ValueError("UGC no-voice timeline requires a visual demo")
        previous_end = 0.0
        for caption in self.captions:
            if caption.start_seconds < previous_end:
                raise ValueError("UGC no-voice captions cannot overlap")
            if caption.end_seconds > self.duration_seconds:
                raise ValueError("UGC no-voice caption exceeds video duration")
            previous_end = caption.end_seconds
        if any(sound.end_seconds > self.duration_seconds for sound in self.natural_sounds):
            raise ValueError("UGC natural sound exceeds video duration")
        return self


class UgcNoVoiceCasebookV1(StudioContract):
    schema_version: Literal["studio.ugc-no-voice-casebook.v1"] = "studio.ugc-no-voice-casebook.v1"
    suite_id: str = Field(min_length=1, max_length=160)
    status: Literal["frozen"] = "frozen"
    frozen_at: datetime
    supersedes_audio_profile: Literal["spoken-ugc-v1"] = "spoken-ugc-v1"
    profile: UgcNoVoiceProfileV1
    cases: list[UgcNoVoiceCreativeCaseV1] = Field(min_length=10, max_length=10)

    @model_validator(mode="after")
    def validate_matrix(self) -> UgcNoVoiceCasebookV1:
        case_ids = [case.case_id for case in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("UGC no-voice case ids must be unique")
        if len({case.niche for case in self.cases}) != 10:
            raise ValueError("UGC no-voice matrix must cover ten distinct niches")
        if {case.avatar.candidate_id for case in self.cases} != AVATAR_CANDIDATE_IDS:
            raise ValueError("UGC no-voice matrix must cover all six catalog slots")
        return self


class UgcNoVoiceSoundEvidenceV1(StudioContract):
    cue_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,79}$")
    asset_id: str = Field(min_length=1, max_length=160)
    path: str = Field(min_length=1, max_length=2000)
    checksum_sha256: str = Field(pattern=SHA256_PATTERN)
    size_bytes: int = Field(ge=1)
    duration_seconds: float = Field(gt=0, le=300)
    source_uri: str = Field(min_length=1, max_length=4000)
    license_name: str = Field(min_length=1, max_length=240)
    license_uri: str = Field(min_length=1, max_length=4000)
    rights_status: Literal["verified"] = "verified"
    speech_detector: str = Field(min_length=1, max_length=240)
    speech_report_path: str = Field(min_length=1, max_length=2000)
    speech_report_checksum_sha256: str = Field(pattern=SHA256_PATTERN)
    speech_detection_status: Literal["pass", "fail", "inconclusive"]
    music_detection_status: Literal["pass", "fail", "inconclusive"]
    human_listening_status: Literal["pending", "pass", "fail"]


class UgcNoVoiceVideoEvidenceV1(StudioContract):
    asset_id: str = Field(min_length=1, max_length=160)
    path: str = Field(min_length=1, max_length=2000)
    checksum_sha256: str = Field(pattern=SHA256_PATTERN)
    size_bytes: int = Field(ge=1)
    width: Literal[1080] = 1080
    height: Literal[1920] = 1920
    duration_seconds: float = Field(gt=0, le=300)
    fps: Literal[25, 30]
    codec: Literal["h264"] = "h264"
    captions_burned_in: Literal[True] = True
    audio_stream_present: Literal[True] = True
    avatar_rights_status: Literal["verified"] = "verified"
    avatar_rights_reference: str = Field(min_length=1, max_length=1000)
    final_mix_report_path: str = Field(min_length=1, max_length=2000)
    final_mix_report_checksum_sha256: str = Field(pattern=SHA256_PATTERN)
    speech_detection_status: Literal["pass", "fail", "inconclusive"]
    music_detection_status: Literal["pass", "fail", "inconclusive"]
    human_visual_review_status: Literal["pending", "pass", "fail"]
    human_listening_status: Literal["pending", "pass", "fail"]


class UgcNoVoiceEditorialReviewEvidenceV1(StudioContract):
    case_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,79}$")
    case_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    reviewer_id: str = Field(min_length=1, max_length=160)
    reviewed_at: datetime
    copy_status: Literal["approved", "rejected"]
    caption_status: Literal["approved", "rejected"]
    synchronization_status: Literal["approved", "rejected"]
    safety_status: Literal["approved", "rejected"]
    notes: list[str] = Field(default_factory=list, max_length=30)


class UgcNoVoiceCapabilityGateV1(StudioContract):
    capability: Literal[
        "caption_plan",
        "natural_sound_assets",
        "voice_absence",
        "music_absence",
        "avatar_video",
        "editorial_review",
        "publication",
    ]
    status: Literal["executed", "blocked"]
    reason: str = Field(min_length=1, max_length=1000)


class UgcNoVoiceCaseAssessmentV1(StudioContract):
    case_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,79}$")
    planning_checks: dict[str, Literal["pass", "fail"]]
    planning_status: Literal["pass", "fail"]
    production_status: Literal["ready", "blocked"]
    capability_gates: list[UgcNoVoiceCapabilityGateV1] = Field(min_length=7, max_length=7)
    human_review_required: Literal[True] = True


class UgcNoVoicePlanAuditV1(StudioContract):
    schema_version: Literal["studio.ugc-no-voice-plan-audit.v1"] = "studio.ugc-no-voice-plan-audit.v1"
    suite_id: str = Field(min_length=1, max_length=160)
    casebook_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    assessed_at: datetime
    assessments: list[UgcNoVoiceCaseAssessmentV1] = Field(min_length=10, max_length=10)
    production_assets_supplied: Literal[False] = False
    external_publication_executed: Literal[False] = False
