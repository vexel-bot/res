from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from .contracts import StudioContract

SHA256_PATTERN = r"^[0-9a-fA-F]{64}$"
OPAQUE_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,159}$"

VideoFamilyV1 = Literal[
    "presenter_ugc",
    "split_screen_proof",
    "motion_visual_essay",
    "cinematic_hybrid",
]

NarrativeRoleV1 = Literal[
    "hook",
    "setup",
    "problem",
    "tension",
    "proof",
    "demo",
    "contrast",
    "transformation",
    "benefit",
    "offer",
    "payoff",
    "cta",
]

VisualFunctionV1 = Literal[
    "evidence",
    "demonstration",
    "context",
    "metaphor",
    "contrast",
    "continuity",
    "breathing_room",
    "rhythm",
    "identity",
    "call_to_action",
]

VisualModalityV1 = Literal[
    "presenter",
    "product",
    "screen_ui",
    "source_video",
    "archive",
    "typography",
    "shape",
    "data",
    "environment",
    "generated_scene",
    "avatar",
]


def _digest(contract: StudioContract) -> str:
    canonical = json.dumps(
        contract.model_dump(mode="json", by_alias=True, exclude_none=True),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


class CreativeEvidenceV1(StudioContract):
    evidence_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    kind: Literal["verified", "user_provided", "hypothesis", "creative_reference"]
    summary: str = Field(min_length=1, max_length=2000)
    source_url: str | None = Field(default=None, max_length=4000)
    allowed_claims: list[str] = Field(default_factory=list, max_length=100)
    prohibited_claims: list[str] = Field(default_factory=list, max_length=100)
    human_review_required: bool = True

    @model_validator(mode="after")
    def validate_evidence(self) -> CreativeEvidenceV1:
        if len(self.allowed_claims) != len(set(self.allowed_claims)):
            raise ValueError("Creative evidence allowed claims must be unique")
        if len(self.prohibited_claims) != len(set(self.prohibited_claims)):
            raise ValueError("Creative evidence prohibited claims must be unique")
        if self.kind in {"hypothesis", "creative_reference"} and not self.human_review_required:
            raise ValueError("Hypotheses and creative references require human review")
        if self.kind == "creative_reference" and not self.source_url:
            raise ValueError("A creative reference requires a source URL")
        return self


class MessageClaimV1(StudioContract):
    claim_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    text: str = Field(min_length=1, max_length=2000)
    evidence_ids: list[str] = Field(default_factory=list, max_length=100)
    status: Literal["verified", "human_review_required", "hypothesis"]

    @model_validator(mode="after")
    def validate_claim(self) -> MessageClaimV1:
        if len(self.evidence_ids) != len(set(self.evidence_ids)):
            raise ValueError("Message claim evidence ids must be unique")
        if self.status == "verified" and not self.evidence_ids:
            raise ValueError("A verified message claim requires evidence")
        return self


class HookHypothesisV1(StudioContract):
    hook_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    text: str = Field(min_length=1, max_length=500)
    mechanism: Literal[
        "curiosity",
        "contrarian",
        "proof",
        "demonstration",
        "question",
        "tension",
        "transformation",
    ]
    evidence_ids: list[str] = Field(default_factory=list, max_length=100)
    promise_delivered_by_beat_id: str = Field(pattern=OPAQUE_ID_PATTERN)


class MessageArchitectureV1(StudioContract):
    schema_version: Literal["studio.message-architecture.v1"] = (
        "studio.message-architecture.v1"
    )
    message_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    objective: str = Field(min_length=1, max_length=1000)
    audience: str = Field(min_length=1, max_length=2000)
    awareness_stage: Literal[
        "unaware",
        "problem_aware",
        "solution_aware",
        "product_aware",
        "most_aware",
    ]
    belief_before: str = Field(min_length=1, max_length=1000)
    belief_after: str = Field(min_length=1, max_length=1000)
    thesis: str = Field(min_length=1, max_length=2000)
    promise: str = Field(min_length=1, max_length=1000)
    mechanism: str = Field(min_length=1, max_length=2000)
    claims: list[MessageClaimV1] = Field(default_factory=list, max_length=100)
    hooks: list[HookHypothesisV1] = Field(min_length=2, max_length=5)
    selected_hook_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    cta: str = Field(min_length=1, max_length=500)
    locked_facts: list[str] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def validate_message(self) -> MessageArchitectureV1:
        claim_ids = [item.claim_id for item in self.claims]
        hook_ids = [item.hook_id for item in self.hooks]
        if len(claim_ids) != len(set(claim_ids)):
            raise ValueError("Message claim ids must be unique")
        if len(hook_ids) != len(set(hook_ids)):
            raise ValueError("Hook hypothesis ids must be unique")
        if self.selected_hook_id not in hook_ids:
            raise ValueError("Selected hook must exist in hook hypotheses")
        if len(self.locked_facts) != len(set(self.locked_facts)):
            raise ValueError("Message locked facts must be unique")
        return self


class ContentBeatV1(StudioContract):
    schema_version: Literal["studio.content-beat.v1"] = "studio.content-beat.v1"
    beat_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    order: int = Field(ge=0, le=1000)
    narrative_role: NarrativeRoleV1
    purpose: str = Field(min_length=1, max_length=1000)
    message: str = Field(min_length=1, max_length=2000)
    opens_expectation: str = Field(default="", max_length=1000)
    closes_expectation: str = Field(default="", max_length=1000)
    visual_function: VisualFunctionV1
    modalities: list[VisualModalityV1] = Field(min_length=1, max_length=6)
    relation_to_previous: Literal[
        "origin",
        "continuity",
        "contrast",
        "cause",
        "escalation",
        "return",
        "conclusion",
    ]
    start_milliseconds: int = Field(ge=0, le=300_000)
    duration_milliseconds: int = Field(gt=0, le=300_000)
    spoken_text: str = Field(default="", max_length=4000)
    on_screen_text: str = Field(default="", max_length=1000)
    sound_intent: str = Field(default="", max_length=1000)
    evidence_ids: list[str] = Field(default_factory=list, max_length=100)
    prohibited_claims: list[str] = Field(default_factory=list, max_length=100)
    reality_constraints: list[str] = Field(default_factory=list, max_length=100)
    success_criterion: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def validate_beat(self) -> ContentBeatV1:
        if len(self.modalities) != len(set(self.modalities)):
            raise ValueError("Content beat modalities must be unique")
        if len(self.evidence_ids) != len(set(self.evidence_ids)):
            raise ValueError("Content beat evidence ids must be unique")
        if self.order == 0 and self.relation_to_previous != "origin":
            raise ValueError("First content beat relation must be origin")
        if self.order > 0 and self.relation_to_previous == "origin":
            raise ValueError("Only the first content beat can have origin relation")
        return self


class CreativeScriptV1(StudioContract):
    schema_version: Literal["studio.creative-script.v1"] = "studio.creative-script.v1"
    script_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    message_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    message_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    target_duration_milliseconds: int = Field(ge=5_000, le=300_000)
    beats: list[ContentBeatV1] = Field(min_length=2, max_length=100)

    @model_validator(mode="after")
    def validate_timeline(self) -> CreativeScriptV1:
        ids = [item.beat_id for item in self.beats]
        orders = [item.order for item in self.beats]
        if len(ids) != len(set(ids)):
            raise ValueError("Creative script beat ids must be unique")
        if orders != list(range(len(self.beats))):
            raise ValueError("Creative script beat order must be contiguous")
        cursor = 0
        for beat in self.beats:
            if beat.start_milliseconds != cursor:
                raise ValueError("Creative script beats must cover a contiguous timeline")
            cursor += beat.duration_milliseconds
        if cursor != self.target_duration_milliseconds:
            raise ValueError("Creative script beats must exactly cover target duration")
        if self.beats[0].narrative_role != "hook":
            raise ValueError("Creative script must start with a hook")
        if self.beats[-1].narrative_role not in {"payoff", "cta"}:
            raise ValueError("Creative script must end with payoff or CTA")
        return self


class RecipeDesignTokensV1(StudioContract):
    background_color: str = Field(pattern=r"^#[0-9a-fA-F]{6}$")
    foreground_color: str = Field(pattern=r"^#[0-9a-fA-F]{6}$")
    accent_color: str = Field(pattern=r"^#[0-9a-fA-F]{6}$")
    muted_color: str = Field(pattern=r"^#[0-9a-fA-F]{6}$")
    display_font_family: str = Field(min_length=1, max_length=240)
    body_font_family: str = Field(min_length=1, max_length=240)
    display_font_size: int = Field(ge=24, le=240)
    caption_font_size: int = Field(ge=16, le=160)
    safe_zone_top: int = Field(ge=0, le=1000)
    safe_zone_right: int = Field(ge=0, le=1000)
    safe_zone_bottom: int = Field(ge=0, le=1000)
    safe_zone_left: int = Field(ge=0, le=1000)
    base_spacing: int = Field(ge=2, le=128)
    transition_milliseconds: int = Field(ge=0, le=5000)


class RecipeFallbackV1(StudioContract):
    fallback_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    trigger: Literal[
        "asset_unavailable",
        "provider_unavailable",
        "rights_unverified",
        "reality_risk",
        "budget_exceeded",
        "reduced_motion",
    ]
    strategy: str = Field(min_length=1, max_length=1000)
    preserves_visual_functions: list[VisualFunctionV1] = Field(min_length=1, max_length=10)

    @model_validator(mode="after")
    def validate_fallback(self) -> RecipeFallbackV1:
        if len(self.preserves_visual_functions) != len(set(self.preserves_visual_functions)):
            raise ValueError("Recipe fallback visual functions must be unique")
        return self


class FormatRecipeV1(StudioContract):
    schema_version: Literal["studio.format-recipe.v1"] = "studio.format-recipe.v1"
    recipe_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    family: VideoFamilyV1
    name: str = Field(min_length=1, max_length=240)
    canvas_width: int = Field(ge=320, le=8192)
    canvas_height: int = Field(ge=320, le=8192)
    minimum_duration_milliseconds: int = Field(ge=1_000, le=300_000)
    maximum_duration_milliseconds: int = Field(ge=1_000, le=300_000)
    required_capabilities: list[str] = Field(min_length=1, max_length=100)
    allowed_modalities: list[VisualModalityV1] = Field(min_length=1, max_length=11)
    layout_rules: list[str] = Field(min_length=1, max_length=100)
    motion_rules: list[str] = Field(min_length=1, max_length=100)
    audio_rules: list[str] = Field(min_length=1, max_length=100)
    design_tokens: RecipeDesignTokensV1
    fallbacks: list[RecipeFallbackV1] = Field(min_length=2, max_length=20)
    reduced_motion_rules: list[str] = Field(min_length=1, max_length=100)
    fallback_recipe_id: str | None = Field(default=None, pattern=OPAQUE_ID_PATTERN)
    reduced_motion_supported: Literal[True] = True
    human_review_required: Literal[True] = True

    @model_validator(mode="after")
    def validate_recipe(self) -> FormatRecipeV1:
        if self.maximum_duration_milliseconds < self.minimum_duration_milliseconds:
            raise ValueError("Format recipe maximum duration must not precede minimum")
        for values, label in (
            (self.required_capabilities, "capabilities"),
            (self.allowed_modalities, "modalities"),
            (self.layout_rules, "layout rules"),
            (self.motion_rules, "motion rules"),
            (self.audio_rules, "audio rules"),
            (self.reduced_motion_rules, "reduced motion rules"),
        ):
            if len(values) != len(set(values)):
                raise ValueError(f"Format recipe {label} must be unique")
        if self.fallback_recipe_id == self.recipe_id:
            raise ValueError("Format recipe cannot fall back to itself")
        fallback_ids = [item.fallback_id for item in self.fallbacks]
        fallback_triggers = [item.trigger for item in self.fallbacks]
        if len(fallback_ids) != len(set(fallback_ids)):
            raise ValueError("Format recipe fallback ids must be unique")
        if len(fallback_triggers) != len(set(fallback_triggers)):
            raise ValueError("Format recipe fallback triggers must be unique")
        if "reduced_motion" not in fallback_triggers:
            raise ValueError("Format recipe requires a reduced motion fallback")
        return self


class FormatRouteCandidateV1(StudioContract):
    family: VideoFamilyV1
    score: float = Field(ge=0, le=1)
    rationale: str = Field(min_length=1, max_length=1000)
    blockers: list[str] = Field(default_factory=list, max_length=100)


class FormatRouterV1(StudioContract):
    schema_version: Literal["studio.format-router.v1"] = "studio.format-router.v1"
    route_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    script_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    script_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    candidates: list[FormatRouteCandidateV1] = Field(min_length=4, max_length=4)
    selected_family: VideoFamilyV1
    selected_recipe_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    selected_recipe_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    selection_rationale: str = Field(min_length=1, max_length=2000)
    human_review_required: Literal[True] = True

    @model_validator(mode="after")
    def validate_route(self) -> FormatRouterV1:
        families = [item.family for item in self.candidates]
        if len(families) != len(set(families)) or set(families) != {
            "presenter_ugc",
            "split_screen_proof",
            "motion_visual_essay",
            "cinematic_hybrid",
        }:
            raise ValueError("Format route must score every family exactly once")
        selected = next(item for item in self.candidates if item.family == self.selected_family)
        eligible_scores = [item.score for item in self.candidates if not item.blockers]
        if selected.blockers:
            raise ValueError("Selected format route cannot contain blockers")
        if eligible_scores and selected.score < max(eligible_scores):
            raise ValueError("Selected format route must be the highest eligible score")
        return self


class VisualMetaphorV1(StudioContract):
    metaphor_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    source_concept: str = Field(min_length=1, max_length=500)
    target_concept: str = Field(min_length=1, max_length=500)
    causal_relation: str = Field(min_length=1, max_length=1000)
    interpretation_risk: str = Field(min_length=1, max_length=1000)
    literalness: Literal["literal", "balanced", "abstract"]
    fallback_description: str = Field(min_length=1, max_length=1000)


class VisualShotV1(StudioContract):
    shot_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    order: int = Field(ge=0, le=1000)
    beat_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    modality: VisualModalityV1
    composition: str = Field(min_length=1, max_length=2000)
    camera: str = Field(min_length=1, max_length=1000)
    lighting: str = Field(min_length=1, max_length=1000)
    entry_state: str = Field(min_length=1, max_length=1000)
    exit_state: str = Field(min_length=1, max_length=1000)
    transition: str = Field(min_length=1, max_length=1000)
    asset_requirements: list[str] = Field(default_factory=list, max_length=100)
    reality_constraints: list[str] = Field(default_factory=list, max_length=100)


class VisualDirectionV1(StudioContract):
    schema_version: Literal["studio.visual-direction.v1"] = "studio.visual-direction.v1"
    direction_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    script_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    script_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    family: VideoFamilyV1
    recipe_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    recipe_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    selection_rationale: str = Field(min_length=1, max_length=2000)
    design_principles: list[str] = Field(min_length=1, max_length=100)
    palette: list[str] = Field(min_length=2, max_length=20)
    typography_direction: str = Field(min_length=1, max_length=1000)
    metaphors: list[VisualMetaphorV1] = Field(default_factory=list, max_length=20)
    shots: list[VisualShotV1] = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def validate_direction(self) -> VisualDirectionV1:
        shot_ids = [item.shot_id for item in self.shots]
        orders = [item.order for item in self.shots]
        metaphor_ids = [item.metaphor_id for item in self.metaphors]
        if len(shot_ids) != len(set(shot_ids)):
            raise ValueError("Visual direction shot ids must be unique")
        if orders != list(range(len(self.shots))):
            raise ValueError("Visual direction shot order must be contiguous")
        if len(metaphor_ids) != len(set(metaphor_ids)):
            raise ValueError("Visual direction metaphor ids must be unique")
        return self


class SoundCueV1(StudioContract):
    cue_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    beat_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    role: Literal[
        "dialogue",
        "narration",
        "location_sound",
        "foley",
        "interface",
        "impact",
        "riser",
        "music",
        "silence",
    ]
    start_milliseconds: int = Field(ge=0, le=300_000)
    end_milliseconds: int = Field(gt=0, le=300_000)
    description: str = Field(min_length=1, max_length=1000)
    asset_id: str | None = Field(default=None, pattern=OPAQUE_ID_PATTERN)
    rights_status: Literal["verified", "required_before_render", "not_applicable"]
    event_binding: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def validate_cue(self) -> SoundCueV1:
        if self.end_milliseconds <= self.start_milliseconds:
            raise ValueError("Sound cue end must be after start")
        if self.asset_id and self.rights_status != "verified":
            raise ValueError("A bound sound asset must have verified rights")
        if self.role == "silence" and self.rights_status != "not_applicable":
            raise ValueError("Intentional silence has no rights requirement")
        return self


class SoundDesignPlanV1(StudioContract):
    schema_version: Literal["studio.sound-design-plan.v1"] = "studio.sound-design-plan.v1"
    sound_plan_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    script_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    script_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    mode: Literal[
        "natural_foley_only",
        "spoken_with_foley",
        "narrated_editorial",
        "cinematic_mix",
        "intentional_silence",
    ]
    voice_inference_authorized: Literal[False] = False
    music_authorized: bool = False
    target_loudness_lufs: float = Field(default=-14, ge=-30, le=-6)
    cues: list[SoundCueV1] = Field(min_length=1, max_length=500)
    mix_notes: list[str] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_sound_plan(self) -> SoundDesignPlanV1:
        cue_ids = [item.cue_id for item in self.cues]
        if len(cue_ids) != len(set(cue_ids)):
            raise ValueError("Sound cue ids must be unique")
        if not self.music_authorized and any(item.role == "music" for item in self.cues):
            raise ValueError("Music cue requires music authorization")
        if self.mode == "natural_foley_only" and any(
            item.role in {"dialogue", "narration", "music"} for item in self.cues
        ):
            raise ValueError("Natural foley only mode prohibits speech and music")
        return self


class ExecutableStoryboardShotV1(StudioContract):
    shot_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    order: int = Field(ge=0, le=1000)
    beat_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    visual_function: VisualFunctionV1
    start_milliseconds: int = Field(ge=0, le=300_000)
    duration_milliseconds: int = Field(gt=0, le=300_000)
    placeholder_kind: Literal[
        "solid_card",
        "typography_card",
        "source_thumbnail",
        "wireframe_ui",
        "shape_blocking",
        "generated_scene_blocking",
    ]
    frame_description: str = Field(min_length=1, max_length=2000)
    on_screen_text: str = Field(default="", max_length=1000)
    primary_color: str = Field(pattern=r"^#[0-9a-fA-F]{6}$")
    accent_color: str = Field(pattern=r"^#[0-9a-fA-F]{6}$")
    sound_cue_ids: list[str] = Field(min_length=1, max_length=50)
    reality_constraints: list[str] = Field(min_length=1, max_length=100)
    planned_clip_ids: list[str] = Field(default_factory=list, max_length=100)
    asset_state: Literal["placeholder", "rights_verified"] = "placeholder"
    expensive_generation_required: bool = False

    @model_validator(mode="after")
    def validate_storyboard_shot(self) -> ExecutableStoryboardShotV1:
        if len(self.sound_cue_ids) != len(set(self.sound_cue_ids)):
            raise ValueError("Storyboard shot sound cue ids must be unique")
        if len(self.reality_constraints) != len(set(self.reality_constraints)):
            raise ValueError("Storyboard shot reality constraints must be unique")
        if len(self.planned_clip_ids) != len(set(self.planned_clip_ids)):
            raise ValueError("Storyboard shot clip ids must be unique")
        return self


class ExecutableStoryboardV1(StudioContract):
    schema_version: Literal["studio.executable-storyboard.v1"] = (
        "studio.executable-storyboard.v1"
    )
    storyboard_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    script_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    script_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    direction_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    direction_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    sound_plan_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    sound_plan_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    route_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    route_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    target_duration_milliseconds: int = Field(ge=5_000, le=300_000)
    status: Literal["draft", "ready_for_review", "human_approved"] = "draft"
    shots: list[ExecutableStoryboardShotV1] = Field(min_length=2, max_length=200)
    reviewer_id: str | None = Field(default=None, pattern=OPAQUE_ID_PATTERN)
    approved_at: datetime | None = None
    human_review_required: Literal[True] = True

    @model_validator(mode="after")
    def validate_storyboard(self) -> ExecutableStoryboardV1:
        shot_ids = [item.shot_id for item in self.shots]
        orders = [item.order for item in self.shots]
        if len(shot_ids) != len(set(shot_ids)):
            raise ValueError("Executable storyboard shot ids must be unique")
        if orders != list(range(len(self.shots))):
            raise ValueError("Executable storyboard shot order must be contiguous")
        cursor = 0
        for shot in self.shots:
            if shot.start_milliseconds != cursor:
                raise ValueError("Executable storyboard must cover a contiguous timeline")
            cursor += shot.duration_milliseconds
        if cursor != self.target_duration_milliseconds:
            raise ValueError("Executable storyboard must exactly cover target duration")
        if self.status == "human_approved":
            if not self.reviewer_id or not self.approved_at:
                raise ValueError("Approved storyboard requires reviewer and timestamp")
        elif self.reviewer_id or self.approved_at:
            raise ValueError("Unapproved storyboard cannot carry approval metadata")
        return self


class AnimaticShotV1(StudioContract):
    storyboard_shot_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    start_milliseconds: int = Field(ge=0, le=300_000)
    duration_milliseconds: int = Field(gt=0, le=300_000)
    visual_placeholder: Literal[True] = True
    sound_cue_ids: list[str] = Field(min_length=1, max_length=50)
    transition_preview: str = Field(min_length=1, max_length=500)


class AnimaticPlanV1(StudioContract):
    schema_version: Literal["studio.animatic-plan.v1"] = "studio.animatic-plan.v1"
    animatic_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    storyboard_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    storyboard_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    width: int = Field(ge=320, le=4096)
    height: int = Field(ge=320, le=4096)
    frame_rate: int = Field(ge=12, le=60)
    reduced_motion: bool = False
    render_tier: Literal["placeholder_only"] = "placeholder_only"
    expensive_provider_calls_allowed: Literal[False] = False
    provisional_audio_only: Literal[True] = True
    status: Literal["planned", "rendered", "human_approved"] = "planned"
    shots: list[AnimaticShotV1] = Field(min_length=2, max_length=200)
    render_asset_path: str | None = Field(default=None, max_length=4000)
    render_digest_sha256: str | None = Field(default=None, pattern=SHA256_PATTERN)
    reviewer_id: str | None = Field(default=None, pattern=OPAQUE_ID_PATTERN)
    approved_at: datetime | None = None
    human_review_required: Literal[True] = True

    @model_validator(mode="after")
    def validate_animatic(self) -> AnimaticPlanV1:
        shot_ids = [item.storyboard_shot_id for item in self.shots]
        if len(shot_ids) != len(set(shot_ids)):
            raise ValueError("Animatic storyboard shot ids must be unique")
        cursor = 0
        for shot in self.shots:
            if shot.start_milliseconds != cursor:
                raise ValueError("Animatic must cover a contiguous timeline")
            cursor += shot.duration_milliseconds
        if self.status in {"rendered", "human_approved"} and (
            not self.render_asset_path or not self.render_digest_sha256
        ):
            raise ValueError("Rendered animatic requires artifact path and digest")
        if self.status == "planned" and (self.render_asset_path or self.render_digest_sha256):
            raise ValueError("Planned animatic cannot claim a rendered artifact")
        if self.status == "human_approved":
            if not self.reviewer_id or not self.approved_at:
                raise ValueError("Approved animatic requires reviewer and timestamp")
        elif self.reviewer_id or self.approved_at:
            raise ValueError("Unapproved animatic cannot carry approval metadata")
        return self


class BeatLearningMetricV1(StudioContract):
    beat_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    viewers_entered: int | None = Field(default=None, ge=0)
    viewers_exited: int | None = Field(default=None, ge=0)
    rewatches: int | None = Field(default=None, ge=0)
    qualitative_notes: list[str] = Field(default_factory=list, max_length=100)


class LearningRecordV1(StudioContract):
    schema_version: Literal["studio.learning-record.v1"] = "studio.learning-record.v1"
    learning_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    case_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    document_id: str | None = Field(default=None, pattern=OPAQUE_ID_PATTERN)
    document_revision: int | None = Field(default=None, ge=1)
    render_digest_sha256: str | None = Field(default=None, pattern=SHA256_PATTERN)
    status: Literal["planned", "measured", "rejected"]
    hypotheses: list[str] = Field(min_length=1, max_length=100)
    beat_metrics: list[BeatLearningMetricV1] = Field(default_factory=list, max_length=100)
    blockers: list[str] = Field(default_factory=list, max_length=100)
    human_reviewed: bool = False
    recorded_at: datetime | None = None

    @model_validator(mode="after")
    def validate_learning(self) -> LearningRecordV1:
        beat_ids = [item.beat_id for item in self.beat_metrics]
        if len(beat_ids) != len(set(beat_ids)):
            raise ValueError("Learning beat metrics must be unique")
        if self.status == "measured":
            if not self.render_digest_sha256 or not self.recorded_at or not self.human_reviewed:
                raise ValueError("Measured learning requires render, timestamp, and human review")
            if not self.beat_metrics:
                raise ValueError("Measured learning requires beat metrics")
        if self.status == "rejected" and not self.blockers:
            raise ValueError("Rejected learning record requires blockers")
        return self


class CreativeAutonomyCaseV1(StudioContract):
    schema_version: Literal["studio.creative-autonomy-case.v1"] = (
        "studio.creative-autonomy-case.v1"
    )
    case_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    title: str = Field(min_length=1, max_length=240)
    family: VideoFamilyV1
    golden: bool = False
    structural_reference_urls: list[str] = Field(default_factory=list, max_length=20)
    evidence: list[CreativeEvidenceV1] = Field(min_length=1, max_length=100)
    message: MessageArchitectureV1
    script: CreativeScriptV1
    recipe: FormatRecipeV1
    format_route: FormatRouterV1
    visual_direction: VisualDirectionV1
    sound_design: SoundDesignPlanV1
    storyboard: ExecutableStoryboardV1
    animatic: AnimaticPlanV1
    learning: LearningRecordV1
    hard_gates: list[str] = Field(min_length=1, max_length=100)
    identity_inference_authorized: Literal[False] = False
    publication_authorized: Literal[False] = False

    @model_validator(mode="after")
    def validate_bindings(self) -> CreativeAutonomyCaseV1:
        if self.recipe.family != self.family or self.visual_direction.family != self.family:
            raise ValueError("Case family must match recipe and visual direction")
        if self.script.message_id != self.message.message_id:
            raise ValueError("Creative script must bind to the case message")
        if self.script.message_digest_sha256.lower() != message_architecture_digest(self.message):
            raise ValueError("Creative script message digest does not match")
        if self.visual_direction.script_id != self.script.script_id:
            raise ValueError("Visual direction must bind to the case script")
        if self.visual_direction.script_digest_sha256.lower() != creative_script_digest(self.script):
            raise ValueError("Visual direction script digest does not match")
        if self.visual_direction.recipe_id != self.recipe.recipe_id:
            raise ValueError("Visual direction must bind to the case recipe")
        if self.visual_direction.recipe_digest_sha256.lower() != format_recipe_digest(self.recipe):
            raise ValueError("Visual direction recipe digest does not match")
        if (
            self.format_route.script_id != self.script.script_id
            or self.format_route.script_digest_sha256.lower() != creative_script_digest(self.script)
            or self.format_route.selected_family != self.family
            or self.format_route.selected_recipe_id != self.recipe.recipe_id
            or self.format_route.selected_recipe_digest_sha256.lower()
            != format_recipe_digest(self.recipe)
        ):
            raise ValueError("Format route does not bind to the selected script and recipe")
        if self.sound_design.script_id != self.script.script_id:
            raise ValueError("Sound design must bind to the case script")
        if self.sound_design.script_digest_sha256.lower() != creative_script_digest(self.script):
            raise ValueError("Sound design script digest does not match")
        if self.learning.case_id != self.case_id:
            raise ValueError("Learning record must bind to the case")
        if (
            self.storyboard.script_id != self.script.script_id
            or self.storyboard.script_digest_sha256.lower() != creative_script_digest(self.script)
            or self.storyboard.direction_id != self.visual_direction.direction_id
            or self.storyboard.direction_digest_sha256.lower()
            != visual_direction_digest(self.visual_direction)
            or self.storyboard.sound_plan_id != self.sound_design.sound_plan_id
            or self.storyboard.sound_plan_digest_sha256.lower()
            != sound_design_plan_digest(self.sound_design)
            or self.storyboard.route_id != self.format_route.route_id
            or self.storyboard.route_digest_sha256.lower() != format_router_digest(self.format_route)
            or self.storyboard.target_duration_milliseconds
            != self.script.target_duration_milliseconds
        ):
            raise ValueError("Executable storyboard bindings do not match the case")
        if (
            self.animatic.storyboard_id != self.storyboard.storyboard_id
            or self.animatic.storyboard_digest_sha256.lower()
            != executable_storyboard_digest(self.storyboard)
        ):
            raise ValueError("Animatic does not bind to the executable storyboard")

        evidence_ids = [item.evidence_id for item in self.evidence]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("Creative case evidence ids must be unique")
        known_evidence = set(evidence_ids)
        used_evidence = {
            evidence_id
            for values in (
                *(claim.evidence_ids for claim in self.message.claims),
                *(hook.evidence_ids for hook in self.message.hooks),
                *(beat.evidence_ids for beat in self.script.beats),
            )
            for evidence_id in values
        }
        missing_evidence = sorted(used_evidence - known_evidence)
        if missing_evidence:
            raise ValueError(f"Creative case references unknown evidence: {missing_evidence}")

        beat_ids = {item.beat_id for item in self.script.beats}
        if self.message.hooks[0].promise_delivered_by_beat_id not in beat_ids:
            raise ValueError("Hook payoff must bind to a script beat")
        for hook in self.message.hooks:
            if hook.promise_delivered_by_beat_id not in beat_ids:
                raise ValueError("Hook payoff must bind to a script beat")
        if {item.beat_id for item in self.visual_direction.shots} - beat_ids:
            raise ValueError("Visual shots must bind to script beats")
        if {item.beat_id for item in self.sound_design.cues} - beat_ids:
            raise ValueError("Sound cues must bind to script beats")
        storyboard_beat_ids = {item.beat_id for item in self.storyboard.shots}
        if storyboard_beat_ids != beat_ids:
            raise ValueError("Executable storyboard must cover every script beat")
        sound_cue_ids = {item.cue_id for item in self.sound_design.cues}
        if {
            cue_id for shot in self.storyboard.shots for cue_id in shot.sound_cue_ids
        } - sound_cue_ids:
            raise ValueError("Executable storyboard references unknown sound cues")
        storyboard_shots = {item.shot_id: item for item in self.storyboard.shots}
        if len(self.animatic.shots) != len(self.storyboard.shots):
            raise ValueError("Animatic must contain every storyboard shot")
        for animatic_shot in self.animatic.shots:
            storyboard_shot = storyboard_shots.get(animatic_shot.storyboard_shot_id)
            if not storyboard_shot or (
                animatic_shot.start_milliseconds != storyboard_shot.start_milliseconds
                or animatic_shot.duration_milliseconds != storyboard_shot.duration_milliseconds
                or animatic_shot.sound_cue_ids != storyboard_shot.sound_cue_ids
            ):
                raise ValueError("Animatic shot does not match storyboard timing and sound")
        if not (
            self.recipe.minimum_duration_milliseconds
            <= self.script.target_duration_milliseconds
            <= self.recipe.maximum_duration_milliseconds
        ):
            raise ValueError("Script duration is outside recipe bounds")
        used_modalities = {
            modality for beat in self.script.beats for modality in beat.modalities
        } | {shot.modality for shot in self.visual_direction.shots}
        unsupported = sorted(used_modalities - set(self.recipe.allowed_modalities))
        if unsupported:
            raise ValueError(f"Case uses modalities unsupported by recipe: {unsupported}")
        if len(self.hard_gates) != len(set(self.hard_gates)):
            raise ValueError("Creative case hard gates must be unique")
        return self


class CreativePilotCasebookV1(StudioContract):
    schema_version: Literal["studio.creative-pilot-casebook.v1"] = (
        "studio.creative-pilot-casebook.v1"
    )
    suite_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    cases: list[CreativeAutonomyCaseV1] = Field(min_length=12, max_length=12)

    @model_validator(mode="after")
    def validate_casebook(self) -> CreativePilotCasebookV1:
        case_ids = [item.case_id for item in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("Creative pilot case ids must be unique")
        family_counts = Counter(item.family for item in self.cases)
        expected = {
            "presenter_ugc": 3,
            "split_screen_proof": 3,
            "motion_visual_essay": 3,
            "cinematic_hybrid": 3,
        }
        if dict(family_counts) != expected:
            raise ValueError("Creative pilot casebook requires exactly three cases per family")
        if sum(item.golden for item in self.cases) < 4:
            raise ValueError("Creative pilot casebook requires at least four golden cases")
        return self


class CreativeCasebookAuditV1(StudioContract):
    schema_version: Literal["studio.creative-casebook-audit.v1"] = (
        "studio.creative-casebook-audit.v1"
    )
    suite_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    casebook_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    case_count: int = Field(ge=0)
    family_counts: dict[str, int]
    golden_count: int = Field(ge=0)
    eligible: bool
    blockers: list[str]
    audited_at: datetime


class CreativePreproductionGateV1(StudioContract):
    schema_version: Literal["studio.creative-preproduction-gate.v1"] = (
        "studio.creative-preproduction-gate.v1"
    )
    case_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    storyboard_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    animatic_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    placeholder_render_eligible: bool
    expensive_render_eligible: bool
    blockers: list[str]
    evaluated_at: datetime


class AnimaticRenderEvidenceV1(StudioContract):
    case_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    animatic_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    animatic_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    artifact_path: str = Field(min_length=1, max_length=4000)
    artifact_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    width: int = Field(ge=320, le=4096)
    height: int = Field(ge=320, le=4096)
    frame_rate: float = Field(ge=12, le=60)
    duration_milliseconds: int = Field(ge=5_000, le=300_000)
    expected_duration_milliseconds: int = Field(ge=5_000, le=300_000)
    placeholder_only: Literal[True] = True
    expensive_provider_calls: Literal[False] = False
    publication_authorized: Literal[False] = False
    qc_passed: bool
    qc_notes: list[str] = Field(default_factory=list, max_length=100)


class AnimaticBatchEvidenceV1(StudioContract):
    schema_version: Literal["studio.animatic-batch-evidence.v1"] = (
        "studio.animatic-batch-evidence.v1"
    )
    suite_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    casebook_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    renders: list[AnimaticRenderEvidenceV1] = Field(min_length=12, max_length=12)
    eligible: bool
    blockers: list[str]
    rendered_at: datetime

    @model_validator(mode="after")
    def validate_batch(self) -> AnimaticBatchEvidenceV1:
        case_ids = [item.case_id for item in self.renders]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("Animatic batch case ids must be unique")
        expected_eligible = all(item.qc_passed for item in self.renders) and not self.blockers
        if self.eligible != expected_eligible:
            raise ValueError("Animatic batch eligibility does not match render evidence")
        return self


def message_architecture_digest(message: MessageArchitectureV1) -> str:
    return _digest(message)


def creative_script_digest(script: CreativeScriptV1) -> str:
    return _digest(script)


def format_recipe_digest(recipe: FormatRecipeV1) -> str:
    return _digest(recipe)


def format_router_digest(route: FormatRouterV1) -> str:
    return _digest(route)


def visual_direction_digest(direction: VisualDirectionV1) -> str:
    return _digest(direction)


def sound_design_plan_digest(plan: SoundDesignPlanV1) -> str:
    return _digest(plan)


def executable_storyboard_digest(storyboard: ExecutableStoryboardV1) -> str:
    return _digest(storyboard)


def animatic_plan_digest(animatic: AnimaticPlanV1) -> str:
    return _digest(animatic)


def creative_casebook_digest(casebook: CreativePilotCasebookV1) -> str:
    return _digest(casebook)


def audit_creative_casebook(
    casebook: CreativePilotCasebookV1, *, audited_at: datetime
) -> CreativeCasebookAuditV1:
    blockers: list[str] = []
    family_counts = dict(Counter(item.family for item in casebook.cases))
    for item in casebook.cases:
        if item.identity_inference_authorized:
            blockers.append(f"identity_inference_authorized:{item.case_id}")
        if item.publication_authorized:
            blockers.append(f"publication_authorized:{item.case_id}")
        if item.sound_design.voice_inference_authorized:
            blockers.append(f"voice_inference_authorized:{item.case_id}")
        if any(evidence.kind == "hypothesis" and not evidence.human_review_required for evidence in item.evidence):
            blockers.append(f"unreviewed_hypothesis:{item.case_id}")
        if any(claim.status == "verified" and not claim.evidence_ids for claim in item.message.claims):
            blockers.append(f"unsupported_verified_claim:{item.case_id}")
    return CreativeCasebookAuditV1(
        suite_id=casebook.suite_id,
        casebook_digest_sha256=creative_casebook_digest(casebook),
        case_count=len(casebook.cases),
        family_counts=family_counts,
        golden_count=sum(item.golden for item in casebook.cases),
        eligible=not blockers,
        blockers=sorted(set(blockers)),
        audited_at=audited_at,
    )


def evaluate_preproduction_gate(
    case: CreativeAutonomyCaseV1, *, evaluated_at: datetime
) -> CreativePreproductionGateV1:
    blockers: list[str] = []
    if case.storyboard.status != "human_approved":
        blockers.append("storyboard_human_approval_required")
    if case.animatic.status != "human_approved":
        blockers.append("animatic_human_approval_required")
    if any(shot.asset_state != "rights_verified" for shot in case.storyboard.shots):
        blockers.append("storyboard_asset_rights_pending")
    if any(
        cue.rights_status == "required_before_render" for cue in case.sound_design.cues
    ):
        blockers.append("sound_rights_pending")
    placeholder_eligible = (
        case.animatic.render_tier == "placeholder_only"
        and not case.animatic.expensive_provider_calls_allowed
        and case.animatic.provisional_audio_only
    )
    return CreativePreproductionGateV1(
        case_id=case.case_id,
        storyboard_digest_sha256=executable_storyboard_digest(case.storyboard),
        animatic_digest_sha256=animatic_plan_digest(case.animatic),
        placeholder_render_eligible=placeholder_eligible,
        expensive_render_eligible=placeholder_eligible and not blockers,
        blockers=sorted(set(blockers)),
        evaluated_at=evaluated_at,
    )
