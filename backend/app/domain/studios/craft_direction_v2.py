"""Versioned director contracts. Creative choices belong to the director."""
from typing import Literal

from pydantic import Field, model_validator

from .contracts import StudioContract


class Interval(StudioContract):
    start_seconds: float = Field(ge=0, allow_inf_nan=False)
    duration_seconds: float = Field(gt=0, allow_inf_nan=False)


class Scene(StudioContract):
    id: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    initial_state: str = Field(min_length=1)
    event: str = Field(min_length=1)
    final_state: str = Field(min_length=1)
    framing: str = Field(min_length=1)
    lighting: str = Field(min_length=1)
    movement: str = Field(min_length=1)
    continuity: str = Field(min_length=1)
    sound: str = Field(min_length=1)
    interval: Interval
    essential: bool = True
    materials: list[str] = Field(default_factory=list)
    capability_ids: list[str] = Field(default_factory=list)
    unmet_needs: list[str] = Field(default_factory=list)
    acceptance: list[str] = Field(min_length=1)
    production_checks: list[str] = Field(default_factory=list)
    aesthetic_criteria: list[str] = Field(default_factory=list)


class ReferenceObservation(StudioContract):
    reference_id: str = Field(min_length=1)
    observed: str = Field(min_length=1)
    limits: str = Field(min_length=1)


class DirectionPlan(StudioContract):
    schema_version: Literal["craft.direction.v2"] = "craft.direction.v2"
    summary: str = Field(min_length=1)
    audience_promise: str = Field(min_length=1)
    desired_experience: str = Field(min_length=1)
    reference_ids: list[str] = Field(min_length=1)
    reference_interpretation: str = Field(min_length=1)
    chosen_direction: str = Field(min_length=1)
    alternatives: list[str] = Field(default_factory=list)
    rejection_reasons: list[str] = Field(default_factory=list)
    progression: str = Field(min_length=1)
    payoff: str = Field(min_length=1)
    visual_language: str = Field(min_length=1)
    sound_language: str = Field(min_length=1)
    uncertainties: list[str] = Field(default_factory=list)
    experiment: str = Field(min_length=1)
    scenes: list[Scene] = Field(min_length=1)
    reference_observations: list[ReferenceObservation] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_scenes(self):
        if len({scene.id for scene in self.scenes}) != len(self.scenes):
            raise ValueError("craft_direction_duplicate_scene")
        return self


class Finding(StudioContract):
    dimension: Literal["technical", "intent", "craft", "audiovisual"]
    status: Literal["pass", "fail", "inconclusive"]
    observation: str = Field(min_length=1)
    scene_ids: list[str] = Field(default_factory=list)
    issue_ids: list[str] = Field(default_factory=list)


class Evaluation(StudioContract):
    schema_version: Literal["craft.evidence.v2"] = "craft.evidence.v2"
    modality: Literal["audio", "audiovisual", "visual"]
    interval: Interval
    findings: list[Finding] = Field(min_length=1)
    limitations: list[str] = Field(default_factory=list)


class Comparison(StudioContract):
    schema_version: Literal["craft.comparison.v2"] = "craft.comparison.v2"
    candidate_id: str
    baseline_id: str | None = None
    gains: list[str] = Field(default_factory=list)
    losses: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(min_length=1)
    rationale: str = Field(min_length=1)
    decision: Literal["preserve", "select_draft", "promote", "rebuild", "combine"]
    sound_comparison: Literal["original_and_matched", "original_only", "not_assessed"] = "not_assessed"


class HumanApproval(StudioContract):
    expected_revision: int = Field(ge=1)
    expected_version: int = Field(ge=0)
    candidate_id: str = Field(min_length=1)
    decision: Literal["approved", "rejected"]
    comment: str = Field(min_length=1)
