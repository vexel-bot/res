"""Typed editorial scenes. Renderer details are compiled, never supplied as code."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from .cinematic_direction import CinematicArtDirectionV1, CinematicShotIntentV1
from .contextual_editing import ContextualEditPlanV1, EditingIntentV1
from .contracts import FrameRateV1, StudioContract
from .motion import PROPERTY_UNITS, MotionGraphV1, MotionKeyframeV1, MotionProperty
from .native_scenes import NATIVE_COMPONENTS, NativeSceneComponentV1

ID = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$"
COLOR = r"^#[0-9a-fA-F]{6}$"


class EditorialAnimationV2(StudioContract):
    property: MotionProperty
    keyframes: list[MotionKeyframeV1] = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def valid_track(self):
        from .motion import MotionTrackV1

        MotionTrackV1(
            track_id="check",
            target_layer_id="check",
            property=self.property,
            unit=PROPERTY_UNITS[self.property],
            keyframes=self.keyframes,
        )
        return self


class EditorialPointV2(StudioContract):
    x: float = Field(ge=0, le=8192, allow_inf_nan=False)
    y: float = Field(ge=0, le=8192, allow_inf_nan=False)


class EditorialAlignmentV2(StudioContract):
    target_id: str = Field(pattern=ID)
    horizontal: Literal["left", "center", "right"] | None = None
    vertical: Literal["top", "middle", "bottom"] | None = None


class EditorialShadowV2(StudioContract):
    x: float = Field(default=0, ge=-100, le=100)
    y: float = Field(default=6, ge=-100, le=100)
    blur: float = Field(default=12, ge=0, le=100)
    color: str = Field(default="#000000", pattern=COLOR)
    opacity: float = Field(default=0.18, ge=0, le=1)


class EditorialEffectV2(StudioContract):
    """A deterministic, ordered effect supported by the registered runtime."""

    id: str = Field(pattern=ID)
    kind: Literal["blur", "brightness", "contrast", "saturate", "hue_rotate", "drop_shadow"]
    amount: float = Field(allow_inf_nan=False)
    x: float = Field(default=0, ge=-100, le=100, allow_inf_nan=False)
    y: float = Field(default=0, ge=-100, le=100, allow_inf_nan=False)
    color: str = Field(default="#000000", pattern=COLOR)
    opacity: float = Field(default=1, ge=0, le=1)

    @model_validator(mode="after")
    def valid_amount(self):
        low, high = {
            "blur": (0, 40),
            "brightness": (0, 4),
            "contrast": (0, 4),
            "saturate": (0, 4),
            "hue_rotate": (-360, 360),
            "drop_shadow": (0, 100),
        }[self.kind]
        if not low <= self.amount <= high:
            raise ValueError("editing_v2_effect_amount_out_of_range")
        return self


class EditorialDepthTreatmentV2(StudioContract):
    """Layer separation controls; this is not a depth-map/DoF claim."""

    opacity: float = Field(default=1, ge=0, le=1)
    blur_px: float = Field(default=0, ge=0, le=40)
    parallax: float = Field(default=0, ge=0, le=1)


class EditorialMotionCueV2(StudioContract):
    kind: Literal["entrance", "emphasis", "secondary", "exit", "deliberate_hold"]
    profile: Literal["gentle", "standard", "emphasis", "stagger", "path_flow", "deliberate_hold"]
    start_frame: int = Field(default=0, ge=0)
    duration_frames: int = Field(default=18, ge=1, le=3600)
    intensity: float = Field(default=1, ge=0.1, le=2)
    rationale: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def valid_profile(self):
        if (self.kind == "deliberate_hold") != (self.profile == "deliberate_hold"):
            raise ValueError("editing_v2_deliberate_hold_profile_required")
        return self


class EditorialCameraCueV2(StudioContract):
    mode: Literal["static", "push_in", "pull_out", "pan", "focus_transition"]
    target_id: str | None = Field(default=None, pattern=ID)
    start_frame: int = Field(default=0, ge=0)
    duration_frames: int = Field(default=60, ge=2, le=3600)
    intensity: float = Field(default=0.06, ge=0, le=0.15)
    pan_x: float = Field(default=0, ge=-2048, le=2048)
    pan_y: float = Field(default=0, ge=-2048, le=2048)
    easing_profile: Literal["gentle", "standard"] = "standard"
    rationale: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def valid_camera(self):
        if self.mode in {"push_in", "pull_out", "focus_transition"} and not self.target_id:
            raise ValueError("editing_v2_camera_target_required")
        if self.mode == "pan" and self.pan_x == self.pan_y == 0:
            raise ValueError("editing_v2_camera_pan_required")
        if self.mode == "static" and (self.pan_x or self.pan_y or self.intensity):
            self.intensity = 0
            self.pan_x = self.pan_y = 0
        return self


class EditorialKeywordCueV2(StudioContract):
    id: str = Field(pattern=ID)
    text: str = Field(min_length=1, max_length=80)
    source_excerpt: str = Field(min_length=1, max_length=500)
    purpose: str = Field(min_length=1, max_length=1000)
    start_frame: int = Field(ge=0)
    duration_frames: int = Field(ge=12, le=3600)
    position: Literal["top", "center", "bottom"] = "center"
    profile: Literal["gentle", "standard", "emphasis"] = "standard"
    highlight_color: str = Field(default="#ff4d6d", pattern=COLOR)


class EditorialTextSpanV2(StudioContract):
    """A source-bound typographic range; offsets use Python Unicode code points."""

    id: str = Field(pattern=ID)
    start: int = Field(ge=0, le=4000)
    end: int = Field(gt=0, le=4000)
    purpose: str = Field(min_length=1, max_length=1000)
    color: str | None = Field(default=None, pattern=COLOR)
    font_weight: int | None = Field(default=None, ge=100, le=900)
    scale: float = Field(default=1, ge=0.5, le=2)
    start_frame: int | None = Field(default=None, ge=0)
    duration_frames: int | None = Field(default=None, ge=1, le=3600)
    profile: Literal["gentle", "standard", "emphasis", "deliberate_hold"] = "deliberate_hold"

    @model_validator(mode="after")
    def valid_interval(self):
        if self.end <= self.start:
            raise ValueError("editing_v2_text_span_interval_invalid")
        if (self.start_frame is None) != (self.duration_frames is None):
            raise ValueError("editing_v2_text_span_timing_incomplete")
        return self


class EditorialRegionOfInterestV2(StudioContract):
    """Normalized material coordinates; independent from the destination layout."""

    x: float = Field(default=0, ge=0, le=1)
    y: float = Field(default=0, ge=0, le=1)
    width: float = Field(default=1, gt=0, le=1)
    height: float = Field(default=1, gt=0, le=1)
    purpose: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def inside_material(self):
        if self.x + self.width > 1 or self.y + self.height > 1:
            raise ValueError("editing_v2_roi_out_of_bounds")
        return self


class EditorialVisualStateV2(StudioContract):
    id: str = Field(pattern=ID)
    phase: Literal["initial", "action", "consequence", "exit"]
    frame: int = Field(ge=0, le=108000)
    purpose: str = Field(min_length=1, max_length=1000)
    essential_element_ids: list[str] = Field(default_factory=list, max_length=50)
    expected_changes: list[str] = Field(default_factory=list, max_length=50)


class EditorialObservationCueV2(StudioContract):
    id: str = Field(pattern=ID)
    start_frame: int = Field(ge=0, le=108000)
    end_frame_exclusive: int = Field(gt=0, le=108000)
    target_ids: list[str] = Field(min_length=1, max_length=50)
    question: str = Field(min_length=1, max_length=1000)
    minimum_samples_per_second: float = Field(default=8, ge=1, le=60)

    @model_validator(mode="after")
    def valid_interval(self):
        if self.end_frame_exclusive <= self.start_frame:
            raise ValueError("editing_v2_observation_interval_invalid")
        return self


class EditorialContentPartV1(StudioContract):
    """One stable, recognizable part of content that survives layout changes."""

    id: str = Field(pattern=ID)
    role: Literal["primary_media", "title", "identity", "body", "call_to_action"]
    text: str | None = Field(default=None, max_length=1000)
    asset_id: str | None = Field(default=None, max_length=120)
    checksum_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    required: bool = True

    @model_validator(mode="after")
    def has_source(self):
        if not (self.text and self.text.strip()) and not self.asset_id:
            raise ValueError("editing_v2_content_part_source_required")
        if self.checksum_sha256 and not self.asset_id:
            raise ValueError("editing_v2_content_part_checksum_requires_asset")
        return self


class EditorialContentReferenceV1(StudioContract):
    """Canonical content; derived formats reorganize its parts instead of replacing them."""

    id: str = Field(pattern=ID)
    version: int = Field(default=1, ge=1)
    purpose: str = Field(min_length=1, max_length=1000)
    parts: list[EditorialContentPartV1] = Field(min_length=2, max_length=20)

    @model_validator(mode="after")
    def unique_parts(self):
        if len({part.id for part in self.parts}) != len(self.parts):
            raise ValueError("editing_v2_content_part_ids_duplicate")
        if not any(part.role == "primary_media" for part in self.parts):
            raise ValueError("editing_v2_content_primary_media_required")
        if not any(part.role == "title" for part in self.parts):
            raise ValueError("editing_v2_content_title_required")
        return self


class EditorialSemanticAssertionV1(StudioContract):
    """A falsifiable claim about what the exported sequence must visibly or audibly show."""

    id: str = Field(pattern=ID)
    kind: Literal[
        "content_present",
        "content_continuity",
        "format_adaptation",
        "feed_insertion",
        "feed_passage",
        "visual_action",
        "audible_event",
    ]
    object_id: str = Field(pattern=ID)
    initial_state: str = Field(min_length=1, max_length=1000)
    event: str = Field(min_length=1, max_length=1000)
    final_state: str = Field(min_length=1, max_length=1000)
    start_frame: int = Field(ge=0, le=108000)
    end_frame_exclusive: int = Field(gt=0, le=108000)
    target_ids: list[str] = Field(min_length=1, max_length=20)
    required_part_ids: list[str] = Field(default_factory=list, max_length=20)
    evidence_required: Literal[
        "rendered_geometry",
        "rendered_pixels_and_geometry",
        "temporal_sequence",
        "mixed_audio",
    ]
    essential: bool = True

    @model_validator(mode="after")
    def valid_assertion(self):
        if self.end_frame_exclusive <= self.start_frame:
            raise ValueError("editing_v2_semantic_assertion_interval_invalid")
        if self.kind in {"content_continuity", "format_adaptation"} and len(self.target_ids) < 2:
            raise ValueError("editing_v2_semantic_assertion_multiple_states_required")
        if self.kind == "audible_event" and self.evidence_required != "mixed_audio":
            raise ValueError("editing_v2_audible_assertion_requires_audio_evidence")
        if self.kind != "audible_event" and self.evidence_required == "mixed_audio":
            raise ValueError("editing_v2_visual_assertion_cannot_use_audio_evidence")
        if self.kind == "visual_action" and self.required_part_ids:
            raise ValueError("editing_v2_visual_action_cannot_claim_canonical_parts")
        return self


class EditorialElementV2(StudioContract):
    id: str = Field(pattern=ID)
    kind: Literal["text", "shape", "image", "video", "group", "path", "card"]
    purpose: str = Field(min_length=1, max_length=1000)
    parent_id: str | None = Field(default=None, pattern=ID)
    alignment: EditorialAlignmentV2 | None = None
    connector_from_id: str | None = Field(default=None, pattern=ID)
    connector_to_id: str | None = Field(default=None, pattern=ID)
    fit_text: bool = False
    start_frame: int = Field(default=0, ge=0)
    duration_frames: int = Field(ge=1, le=108000)
    after_element_id: str | None = Field(default=None, pattern=ID)
    match_previous_element_id: str | None = Field(default=None, pattern=ID)
    x: float = Field(default=0, ge=-8192, le=16384, allow_inf_nan=False)
    y: float = Field(default=0, ge=-8192, le=16384, allow_inf_nan=False)
    width: float = Field(gt=0, le=8192, allow_inf_nan=False)
    height: float = Field(gt=0, le=8192, allow_inf_nan=False)
    z_index: int = Field(default=0, ge=0, le=10000)
    visual_role: Literal["background", "hero", "support", "text", "accent"] = "support"
    depth_treatment: EditorialDepthTreatmentV2 = Field(default_factory=EditorialDepthTreatmentV2)
    rotation: float = Field(default=0, ge=-360, le=360, allow_inf_nan=False)
    origin_x: float = Field(default=0.5, ge=0, le=1)
    origin_y: float = Field(default=0.5, ge=0, le=1)
    text: str = Field(default="", max_length=4000)
    concise_text: str | None = Field(default=None, max_length=4000)
    text_role: Literal["support", "fact", "caption"] = "support"
    font_asset_id: str | None = Field(default=None, max_length=120)
    font_size: float = Field(default=48, ge=8, le=320)
    font_weight: int = Field(default=700, ge=100, le=900)
    letter_spacing: float = Field(default=0, ge=-10, le=50)
    line_height: float = Field(default=1.1, ge=0.8, le=3)
    text_align: Literal["left", "center", "right"] = "left"
    text_spans: list[EditorialTextSpanV2] = Field(default_factory=list, max_length=100)
    shadow: EditorialShadowV2 | None = None
    effects: list[EditorialEffectV2] = Field(default_factory=list, max_length=8)
    blend_mode: Literal["normal", "multiply", "screen", "overlay", "darken", "lighten"] = "normal"
    border_width: float = Field(default=0, ge=0, le=80)
    border_color: str = Field(default="#ffffff", pattern=COLOR)
    path_mode: Literal["polyline", "quadratic"] = "polyline"

    color: str = Field(default="#ffffff", pattern=COLOR)
    fill: str = Field(default="#183343", pattern=COLOR)
    radius: float = Field(default=16, ge=0, le=512)
    shape: Literal["rectangle", "ellipse"] = "rectangle"
    asset_id: str | None = Field(default=None, max_length=120)
    # Stable semantic identity for content that survives a deterministic
    # representation change (for example, the same message moving from a
    # portrait viewport to a landscape viewport).  This is deliberately
    # distinct from the element id: sharing a composition label is not proof
    # that two unrelated shapes contain the same information.
    content_identity: str | None = Field(default=None, pattern=ID)
    content_reference_id: str | None = Field(default=None, pattern=ID)
    content_part_id: str | None = Field(default=None, pattern=ID)
    mask_asset_id: str | None = Field(default=None, max_length=120)
    source_start_seconds: float = Field(default=0, ge=0, le=86400, allow_inf_nan=False)
    playback_rate: float = Field(default=1, ge=0.5, le=2, allow_inf_nan=False)
    source_audio: Literal["preserve", "mute"] = "preserve"
    object_fit: Literal["contain", "cover"] = "contain"
    region_of_interest: EditorialRegionOfInterestV2 | None = None
    crop_intentional: bool = False
    reveal: Literal["none", "wipe", "words", "path"] = "none"
    reveal_frames: int = Field(default=12, ge=1, le=3600)
    points: list[EditorialPointV2] = Field(default_factory=list, max_length=256)
    stroke_width: float = Field(default=4, gt=0, le=100)
    animations: list[EditorialAnimationV2] = Field(default_factory=list, max_length=11)
    motion_cues: list[EditorialMotionCueV2] = Field(default_factory=list, max_length=8)
    repeat_count: int = Field(default=1, ge=1, le=50)
    repeat_dx: float = Field(default=0, ge=-8192, le=8192)
    repeat_dy: float = Field(default=0, ge=-8192, le=8192)
    stagger_frames: int = Field(default=0, ge=0, le=3600)

    @model_validator(mode="after")
    def content(self):
        if bool(self.connector_from_id) != bool(self.connector_to_id) or (
            self.connector_from_id and self.kind != "path"
        ):
            raise ValueError("editing_v2_connector_requires_path_and_two_targets")
        if self.kind in {"text", "card"} and not self.text.strip():
            raise ValueError("editing_v2_text_required")
        if self.text_spans and self.kind not in {"text", "card"}:
            raise ValueError("editing_v2_text_spans_require_text")
        ordered_spans = sorted(self.text_spans, key=lambda item: (item.start, item.end, item.id))
        if ordered_spans != self.text_spans:
            raise ValueError("editing_v2_text_spans_must_be_ordered")
        for index, span in enumerate(self.text_spans):
            if span.end > len(self.text):
                raise ValueError("editing_v2_text_span_out_of_range")
            if index and self.text_spans[index - 1].end > span.start:
                raise ValueError("editing_v2_text_spans_overlap")
            if span.start_frame is not None and span.start_frame + span.duration_frames > self.duration_frames:
                raise ValueError("editing_v2_text_span_timing_out_of_range")
        if self.path_mode == "quadratic" and (self.kind != "path" or len(self.points) != 3):
            raise ValueError("editing_v2_quadratic_requires_three_points")
        if self.kind == "path" and len(self.points) < 2:
            raise ValueError("editing_v2_path_points_required")
        if self.reveal == "path" and self.kind != "path":
            raise ValueError("editing_v2_path_reveal_requires_path")
        if self.reveal == "words" and self.kind not in {"text", "card"}:
            raise ValueError("editing_v2_word_reveal_requires_text")
        properties = [a.property for a in self.animations]
        if len(properties) != len(set(properties)):
            raise ValueError("editing_v2_duplicate_animation_property")
        if any(a.keyframes[-1].frame >= self.duration_frames for a in self.animations):
            raise ValueError("editing_v2_animation_out_of_range")
        if self.depth_treatment.blur_px and any(a.property == "blur_px" for a in self.animations):
            raise ValueError("editing_v2_static_and_animated_blur_conflict")
        if len({effect.id for effect in self.effects}) != len(self.effects):
            raise ValueError("editing_v2_duplicate_effect")
        if self.depth_treatment.blur_px and any(effect.kind == "blur" for effect in self.effects):
            raise ValueError("editing_v2_duplicate_static_blur")
        if self.shadow and any(effect.kind == "drop_shadow" for effect in self.effects):
            raise ValueError("editing_v2_duplicate_drop_shadow")
        if self.effects and (self.shadow or self.depth_treatment.blur_px):
            raise ValueError("editing_v2_effect_stack_conflicts_legacy_filters")
        if any(c.start_frame + c.duration_frames > self.duration_frames for c in self.motion_cues):
            raise ValueError("editing_v2_motion_cue_out_of_range")
        if self.kind == "group" and self.repeat_count != 1:
            raise ValueError("editing_v2_repeat_children_not_group")
        if self.content_part_id and not self.content_reference_id:
            raise ValueError("editing_v2_content_part_requires_reference")
        if self.content_reference_id and not self.content_part_id and self.kind != "group":
            raise ValueError("editing_v2_content_binding_requires_part_or_group")
        return self


class EditorialAudioV2(StudioContract):
    id: str = Field(pattern=ID)
    role: Literal["narration", "dialogue", "music", "ambience", "effect", "silence"]
    purpose: str = Field(min_length=1, max_length=1000)
    asset_id: str | None = Field(default=None, max_length=120)
    start_frame: int = Field(default=0, ge=0)
    duration_frames: int = Field(ge=1, le=108000)
    source_start_seconds: float = Field(default=0, ge=0, le=86400)
    sync_element_id: str | None = Field(default=None, pattern=ID)
    sync_offset_frames: int = Field(default=0, ge=-3600, le=3600)
    attack_offset_frames: int = Field(default=0, ge=0, le=3600)
    gain_db: float = Field(default=0, ge=-96, le=12)
    fade_in_frames: int = Field(default=0, ge=0, le=3600)
    fade_out_frames: int = Field(default=0, ge=0, le=3600)

    @model_validator(mode="after")
    def valid_audio(self):
        if self.fade_in_frames + self.fade_out_frames > self.duration_frames:
            raise ValueError("editing_v2_audio_fades_out_of_range")
        if self.attack_offset_frames >= self.duration_frames:
            raise ValueError("editing_v2_audio_attack_out_of_range")
        return self


class EditorialMaterialV2(StudioContract):
    id: str = Field(pattern=ID)
    target_id: str = Field(pattern=ID)
    field: Literal["asset", "mask", "font"] = "asset"
    kind: Literal["font", "logo", "image", "video", "wardrobe", "sound_effect", "music"]
    query: str = Field(min_length=1, max_length=500)
    purpose: str = Field(min_length=1, max_length=1000)
    required: bool = True
    official_required: bool = False
    source_class: Literal[
        "auto", "project", "catalog", "licensed_stock", "brand_asset", "generated_original"
    ] = "auto"
    visual_description: str = Field(default="", max_length=2000)
    entity: str = Field(default="", max_length=500)
    action: str = Field(default="", max_length=500)
    appearance: str = Field(default="", max_length=1000)
    orientation: Literal["any", "portrait", "landscape", "square"] = "any"
    duration_seconds: float | None = Field(default=None, gt=0, le=120)
    alpha_required: bool = False
    post_processing: list[Literal["remove_background", "convert_to_png", "trim", "chroma_key"]] = Field(
        default_factory=list, max_length=5
    )
    fallback_behavior: Literal["block", "generated_original"] = "block"
    acceptance_criteria: list[str] = Field(default_factory=list, max_length=30)
    blueprint_requirement_id: str | None = Field(default=None, pattern=ID)
    requirement_class: Literal["mandatory", "preferred", "composable"] = "mandatory"
    preferred_criteria: list[str] = Field(default_factory=list, max_length=30)
    component_id: str | None = Field(default=None, pattern=ID)

    @model_validator(mode="after")
    def classification_is_executable(self):
        if self.requirement_class == "composable" and not self.component_id:
            raise ValueError("editing_v2_composable_material_component_required")
        if self.requirement_class != "composable" and self.component_id:
            raise ValueError("editing_v2_component_only_for_composable_material")
        if self.requirement_class == "preferred" and self.required:
            self.required = False
        return self


class EditorialExecutionVersionsV2(StudioContract):
    """Versions whose output is part of the plan's reproducible meaning."""

    compiler: str = Field(min_length=1, max_length=100)
    components: str = Field(min_length=1, max_length=100)
    runtime: str = Field(min_length=1, max_length=100)
    visual_audit_policy: str = Field(min_length=1, max_length=100)


class EditorialCompositionV1(StudioContract):
    id: str = Field(pattern=ID)
    family: Literal[
        "evidence",
        "comparison",
        "sequence",
        "repetition",
        "focus",
        "continuity",
        "annotated_material",
        "format_transformation",
        "demonstrative_interface",
        "continuity_comparison",
    ]
    target_ids: list[str] = Field(min_length=1, max_length=8)
    purpose: str = Field(min_length=1, max_length=1000)
    expected_result: str = Field(min_length=1, max_length=1000)
    action_frames: int = Field(default=18, ge=1, le=3600)
    # Optional V2 timing. Legacy compositions continue to use action_frames.
    state_hold_frames: list[int] = Field(default_factory=list, max_length=8)
    movement_frames: int | None = Field(default=None, ge=1, le=3600)
    previous_element_id: str | None = Field(default=None, pattern=ID)
    axis: Literal["horizontal", "vertical"] = "horizontal"
    margin_ratio: float = Field(default=0.07, ge=0.02, le=0.15)
    gap_ratio: float = Field(default=0.035, ge=0.01, le=0.08)
    repeat_count: int = Field(default=3, ge=2, le=8)
    focus_scale: float = Field(default=1.08, ge=1, le=1.2)
    continuity_key: str | None = Field(default=None, pattern=ID)
    viewport_formats: list[Literal["portrait", "square", "landscape"]] = Field(
        default_factory=list, max_length=8
    )
    interface_events: list[Literal["insert", "pass", "select", "scroll", "open", "reorganize"]] = Field(
        default_factory=list, max_length=8
    )

    @model_validator(mode="after")
    def semantic_parameters(self):
        if self.state_hold_frames and (
            self.family not in {"format_transformation", "sequence"}
            or len(self.state_hold_frames) != len(self.target_ids)
            or any(value < 1 for value in self.state_hold_frames)
            or self.movement_frames is None
        ):
            raise ValueError("editing_component_state_timing_invalid")
        if self.viewport_formats and (
            self.family != "format_transformation" or len(self.viewport_formats) != len(self.target_ids)
        ):
            raise ValueError("editing_component_viewport_format_binding_invalid")
        if self.interface_events and (
            self.family != "demonstrative_interface" or len(self.interface_events) != len(self.target_ids)
        ):
            raise ValueError("editing_component_interface_event_binding_invalid")
        return self


class EditorialOperationBindingV1(StudioContract):
    """An editorial decision bound to observable elements, not executable code."""

    technique_id: Literal["action_progression", "motif_continuity", "gesture_occlusion_reveal", "moving_variant_mask"]
    version: Literal[1] = 1
    target_ids: list[str] = Field(min_length=1, max_length=12)
    anchor_id: str = Field(min_length=1, max_length=120)
    cut_motivation: str = Field(min_length=1, max_length=1000)
    new_information: str = Field(min_length=1, max_length=1000)
    evidence_type: Literal["observed", "creator_claim", "inference"] = "inference"


class EditorialSceneV2(StudioContract):
    id: str = Field(pattern=ID)
    purpose: str = Field(min_length=1, max_length=2000)
    duration_frames: int = Field(ge=2, le=108000)
    native_components: list[NativeSceneComponentV1] = Field(default_factory=list, max_length=20)
    facts: list[str] = Field(default_factory=list, max_length=100)
    narration: str = Field(default="", max_length=10000)
    background: str = Field(default="#10181c", pattern=COLOR)
    elements: list[EditorialElementV2] = Field(min_length=1, max_length=200)
    audio: list[EditorialAudioV2] = Field(default_factory=list, max_length=50)
    material_needs: list[EditorialMaterialV2] = Field(default_factory=list, max_length=100)
    verification: list[str] = Field(min_length=1, max_length=50)
    technique_ids: list[str] = Field(default_factory=list, max_length=25)
    operation_bindings: list[EditorialOperationBindingV1] = Field(default_factory=list, max_length=12)
    entrance: Literal["cut", "dissolve", "wipe"] = "cut"
    transition_frames: int = Field(default=12, ge=1, le=120)
    compositions: list[EditorialCompositionV1] = Field(default_factory=list, max_length=8)
    camera_cues: list[EditorialCameraCueV2] = Field(default_factory=list, max_length=1)
    keyword_cues: list[EditorialKeywordCueV2] = Field(default_factory=list, max_length=8)
    visual_states: list[EditorialVisualStateV2] = Field(default_factory=list, max_length=20)
    observation_cues: list[EditorialObservationCueV2] = Field(default_factory=list, max_length=20)
    content_reference_ids: list[str] = Field(default_factory=list, max_length=20)
    semantic_assertions: list[EditorialSemanticAssertionV1] = Field(default_factory=list, max_length=30)
    shot_plan: list[CinematicShotIntentV1] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def references(self):
        native_targets = set()
        native_index = {element.id: element for element in self.elements}
        for component in self.native_components:
            for target in component.target_ids:
                element = native_index.get(target)
                if target in native_targets or element is None or element.kind not in NATIVE_COMPONENTS[component.component]["kinds"]:
                    raise ValueError("editing_native_component_target_invalid")
                if component.entrance_frames > element.duration_frames:
                    raise ValueError("editing_native_component_timing_invalid")
                native_targets.add(target)
            if component.component in {"gesture_occlusion_reveal", "moving_variant_mask"}:
                if len(component.target_ids) != 1:
                    raise ValueError("editing_native_variant_target_count_invalid")
                variant = native_index[component.target_ids[0]]
                base = native_index.get(component.base_target_id)
                if not base or base.kind != variant.kind or base.asset_id == variant.asset_id:
                    raise ValueError("editing_native_variant_pair_invalid")
                if (base.x, base.y, base.width, base.height) != (variant.x, variant.y, variant.width, variant.height):
                    raise ValueError("editing_native_variant_geometry_mismatch")
                if base.visual_role != variant.visual_role or base.z_index >= variant.z_index:
                    raise ValueError("editing_native_variant_layer_order_invalid")
                if (base.start_frame, base.duration_frames) != (variant.start_frame, variant.duration_frames):
                    raise ValueError("editing_native_variant_timing_mismatch")
                if (base.object_fit, base.region_of_interest, base.crop_intentional) != (
                    variant.object_fit, variant.region_of_interest, variant.crop_intentional
                ) or (base.kind == "video" and (
                    base.source_start_seconds, base.playback_rate
                ) != (variant.source_start_seconds, variant.playback_rate)):
                    raise ValueError("editing_native_variant_registration_mismatch")
                if component.switch_frame >= variant.duration_frames:
                    raise ValueError("editing_native_variant_switch_out_of_range")
                if component.component == "gesture_occlusion_reveal":
                    occluder = native_index.get(component.occluder_target_id)
                    if (not occluder or occluder.kind not in {"image", "video"}
                            or occluder.z_index <= variant.z_index or not occluder.mask_asset_id):
                        raise ValueError("editing_native_occluder_layer_invalid")
                    if occluder.visual_role != variant.visual_role or not (
                        occluder.start_frame <= variant.start_frame + component.switch_frame
                        < occluder.start_frame + occluder.duration_frames
                    ):
                        raise ValueError("editing_native_occluder_timing_invalid")
                    if any(animation.property in {"position_x", "position_y"} for animation in occluder.animations):
                        raise ValueError("editing_native_occluder_motion_conflict")
        if len({binding.technique_id for binding in self.operation_bindings}) != len(self.operation_bindings):
            raise ValueError("editing_operation_binding_duplicate")
        for binding in self.operation_bindings:
            if binding.technique_id not in self.technique_ids or any(
                target not in native_index for target in binding.target_ids
            ):
                raise ValueError("editing_operation_binding_target_invalid")
        if any(element.playback_rate != 1 and (element.kind != "video" or element.id not in native_targets) for element in self.elements):
            raise ValueError("editing_native_speed_requires_video_component")
        if self.entrance != "cut" and self.transition_frames >= self.duration_frames:
            raise ValueError("editing_v2_transition_out_of_scene")
        indexed = {e.id: e for e in self.elements}
        claimed = []
        if len({c.id for c in self.compositions}) != len(self.compositions):
            raise ValueError("editing_v2_duplicate_composition")
        for composition in self.compositions:
            if any(target not in indexed for target in composition.target_ids):
                raise ValueError("editing_v2_composition_target_missing")
            claimed.extend(composition.target_ids)
        if len(claimed) != len(set(claimed)):
            raise ValueError("editing_v2_composition_target_conflict")
        ids = [e.id for e in self.elements] + [a.id for a in self.audio]
        if len(ids) != len(set(ids)):
            raise ValueError("editing_v2_duplicate_scene_target")
        for element in self.elements:
            if element.connector_from_id:
                anchors = [indexed.get(element.connector_from_id), indexed.get(element.connector_to_id)]
                if any(a is None or a.kind == "path" or a.repeat_count != 1 for a in anchors):
                    raise ValueError("editing_v2_connector_anchor_invalid")
            if element.alignment:
                target = indexed.get(element.alignment.target_id)
                if target is None or target.parent_id != element.parent_id:
                    raise ValueError("editing_v2_alignment_requires_sibling")
                seen, current = set(), element
                while current and current.alignment:
                    if current.id in seen:
                        raise ValueError("editing_v2_alignment_cycle")
                    seen.add(current.id)
                    current = indexed.get(current.alignment.target_id)
            if element.parent_id and (element.parent_id not in indexed or indexed[element.parent_id].kind != "group"):
                raise ValueError("editing_v2_parent_group_required")
            if element.after_element_id and element.after_element_id not in indexed:
                raise ValueError("editing_v2_unknown_temporal_reference")
            for relation in ("parent_id", "after_element_id"):
                seen, current = set(), element
                while current is not None:
                    if current.id in seen:
                        raise ValueError("editing_v2_relation_cycle")
                    seen.add(current.id)
                    current = indexed.get(getattr(current, relation))
        if any(a.sync_element_id and a.sync_element_id not in indexed for a in self.audio):
            raise ValueError("editing_v2_unknown_audio_sync")
        if any(c.start_frame + c.duration_frames > self.duration_frames for c in self.camera_cues):
            raise ValueError("editing_v2_camera_out_of_range")
        if any(c.target_id and c.target_id not in indexed for c in self.camera_cues):
            raise ValueError("editing_v2_camera_target_missing")
        if sum(element.visual_role == "hero" for element in self.elements) > 1:
            raise ValueError("editing_v2_multiple_heroes")
        if any(
            c.target_id and indexed[c.target_id].visual_role not in {"hero", "support"}
            for c in self.camera_cues
        ):
            raise ValueError("editing_v2_camera_target_role_invalid")
        if any(c.start_frame + c.duration_frames > self.duration_frames for c in self.keyword_cues):
            raise ValueError("editing_v2_keyword_out_of_range")
        if len({state.id for state in self.visual_states}) != len(self.visual_states):
            raise ValueError("editing_v2_visual_state_ids_duplicate")
        if any(state.frame >= self.duration_frames for state in self.visual_states):
            raise ValueError("editing_v2_visual_state_out_of_range")
        phase_order = {"initial": 0, "action": 1, "consequence": 2, "exit": 3}
        if self.visual_states != sorted(
            self.visual_states, key=lambda state: (state.frame, phase_order[state.phase], state.id)
        ):
            raise ValueError("editing_v2_visual_states_must_be_ordered")
        if any(
            target not in indexed
            for state in self.visual_states
            for target in state.essential_element_ids
        ):
            raise ValueError("editing_v2_visual_state_target_missing")
        if len({cue.id for cue in self.observation_cues}) != len(self.observation_cues):
            raise ValueError("editing_v2_observation_ids_duplicate")
        if any(cue.end_frame_exclusive > self.duration_frames for cue in self.observation_cues):
            raise ValueError("editing_v2_observation_out_of_range")
        if any(
            shot.end_frame_exclusive is not None and shot.end_frame_exclusive > self.duration_frames
            for shot in self.shot_plan
        ):
            raise ValueError("editing_v2_shot_out_of_range")
        if self.shot_plan:
            if any(shot.start_frame is None for shot in self.shot_plan):
                raise ValueError("editing_v2_shot_timing_required")
            ordered_shots = sorted(self.shot_plan, key=lambda shot: (shot.start_frame, shot.id))
            if ordered_shots != self.shot_plan:
                raise ValueError("editing_v2_shots_must_be_ordered")
            if ordered_shots[0].start_frame != 0 or ordered_shots[-1].end_frame_exclusive != self.duration_frames:
                raise ValueError("editing_v2_shots_must_cover_scene")
            if any(
                left.end_frame_exclusive != right.start_frame
                for left, right in zip(ordered_shots, ordered_shots[1:], strict=False)
            ):
                raise ValueError("editing_v2_shot_intervals_must_be_contiguous")
            requirement_ids = {
                need.blueprint_requirement_id or need.id for need in self.material_needs
            }
            component_ids = {
                *self.technique_ids,
                *(composition.family for composition in self.compositions),
            }
            if any(
                requirement not in requirement_ids
                for shot in self.shot_plan
                for requirement in shot.material_requirement_ids
            ):
                raise ValueError("editing_v2_shot_material_requirement_missing")
            if any(
                component not in component_ids
                for shot in self.shot_plan
                for component in shot.execution_component_ids
            ):
                raise ValueError("editing_v2_shot_component_missing")
        if any(target not in indexed for cue in self.observation_cues for target in cue.target_ids):
            raise ValueError("editing_v2_observation_target_missing")
        if len({assertion.id for assertion in self.semantic_assertions}) != len(self.semantic_assertions):
            raise ValueError("editing_v2_semantic_assertion_ids_duplicate")
        if any(assertion.end_frame_exclusive > self.duration_frames for assertion in self.semantic_assertions):
            raise ValueError("editing_v2_semantic_assertion_out_of_range")
        audio_ids = {audio.id for audio in self.audio}
        if any(
            target not in indexed and not (assertion.kind == "audible_event" and target in audio_ids)
            for assertion in self.semantic_assertions
            for target in assertion.target_ids
        ):
            raise ValueError("editing_v2_semantic_assertion_target_missing")
        source = " ".join([self.narration, *self.facts]).casefold()
        for cue in self.keyword_cues:
            if cue.source_excerpt.casefold() not in source or cue.text.casefold() not in cue.source_excerpt.casefold():
                raise ValueError("editing_v2_keyword_source_required")
        if any(n.target_id not in ids for n in self.material_needs):
            raise ValueError("editing_v2_unknown_material_target")
        return self


class ContextualPlanRequestV2(StudioContract):
    execution_scope: Literal["audiovisual", "visual_only"] = "audiovisual"
    require_material_inspection: bool = False
    semantic_verification_policy: Literal[
        "legacy_execution_v1", "canonical_demonstration_v1"
    ] = "legacy_execution_v1"
    schema_version: Literal["studio.contextual-plan-request.v2"] = "studio.contextual-plan-request.v2"
    expected_document_revision: int = Field(ge=1)
    intent: EditingIntentV1
    frame_rate: FrameRateV1 = Field(default_factory=FrameRateV1)
    execution_versions: EditorialExecutionVersionsV2 | None = None
    scenes: list[EditorialSceneV2] = Field(min_length=1, max_length=50)
    art_direction: CinematicArtDirectionV1 | None = None
    content_references: list[EditorialContentReferenceV1] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def unique_scenes(self):
        if self.execution_scope == "visual_only" and any(s.audio for s in self.scenes):
            raise ValueError("editing_v2_visual_only_audio_not_requested")
        if len({s.id for s in self.scenes}) != len(self.scenes):
            raise ValueError("editing_v2_duplicate_scene")
        if sum(e.repeat_count for s in self.scenes for e in s.elements) > 900:
            raise ValueError("editing_v2_composition_too_large")
        needs = [n.id for s in self.scenes for n in s.material_needs]
        if len(needs) != len(set(needs)):
            raise ValueError("editing_v2_duplicate_material_need")
        if self.scenes[0].entrance != "cut":
            raise ValueError("editing_v2_first_scene_requires_cut")
        if self.semantic_verification_policy == "canonical_demonstration_v1" and not any(
            scene.semantic_assertions for scene in self.scenes
        ):
            raise ValueError("editing_v2_semantic_assertions_required")
        references = {reference.id: reference for reference in self.content_references}
        if len(references) != len(self.content_references):
            raise ValueError("editing_v2_content_reference_ids_duplicate")
        for scene in self.scenes:
            if any(reference_id not in references for reference_id in scene.content_reference_ids):
                raise ValueError("editing_v2_scene_content_reference_missing")
            for element in scene.elements:
                if not element.content_reference_id:
                    continue
                reference = references.get(element.content_reference_id)
                if reference is None or element.content_reference_id not in scene.content_reference_ids:
                    raise ValueError("editing_v2_element_content_reference_missing")
                if element.content_part_id and element.content_part_id not in {part.id for part in reference.parts}:
                    raise ValueError("editing_v2_element_content_part_missing")
                if element.content_part_id:
                    part = next(part for part in reference.parts if part.id == element.content_part_id)
                    # A stable semantic id alone is not continuity.  Bind the
                    # rendered element to the source carried by the canonical
                    # part so a director cannot silently swap pixels or copy.
                    if part.asset_id and element.kind in {"image", "video"} and element.asset_id != part.asset_id:
                        raise ValueError("editing_v2_content_part_asset_binding_mismatch")
                    if part.text and element.kind in {"text", "card"} and element.text.strip() != part.text.strip():
                        raise ValueError("editing_v2_content_part_text_binding_mismatch")
            for assertion in scene.semantic_assertions:
                if (
                    self.semantic_verification_policy == "canonical_demonstration_v1"
                    and assertion.kind in {
                        "content_present", "content_continuity", "format_adaptation",
                        "feed_insertion", "feed_passage",
                    }
                    and assertion.object_id not in scene.content_reference_ids
                ):
                    raise ValueError("editing_v2_assertion_content_reference_required")
                if assertion.object_id in scene.content_reference_ids:
                    reference = references[assertion.object_id]
                    part_ids = {part.id for part in reference.parts}
                    if any(part_id not in part_ids for part_id in assertion.required_part_ids):
                        raise ValueError("editing_v2_assertion_content_part_missing")
        return self


class ContextualEditPlanV2(ContextualEditPlanV1):
    schema_version: Literal["studio.contextual-edit-plan.v2"] = "studio.contextual-edit-plan.v2"
    direction: ContextualPlanRequestV2
    motion_graph: MotionGraphV1
    render_policy: Literal["automatic_draft"] = "automatic_draft"
    manifest: dict = Field(default_factory=dict)
    evaluation: dict = Field(
        default_factory=lambda: {"technical": "pending", "audiovisual": "pending", "human": "pending"}
    )


class EditorialMaterialChoiceV2(StudioContract):
    expected_plan_revision: int = Field(ge=1)
    need_id: str = Field(pattern=ID)
    asset_id: str = Field(min_length=1, max_length=120)


class ContextualPlanRecompileRequestV1(StudioContract):
    """Create a new executable derivative without asking a director to re-plan scenes."""

    schema_version: Literal["studio.contextual-plan-recompile-request.v1"] = (
        "studio.contextual-plan-recompile-request.v1"
    )
    expected_document_revision: int = Field(ge=1)
    expected_plan_revision: int = Field(ge=1)


def parse_editing_plan(raw):
    contract = (
        ContextualEditPlanV2 if raw.get("schemaVersion") == "studio.contextual-edit-plan.v2" else ContextualEditPlanV1
    )
    return contract.model_validate(raw)
