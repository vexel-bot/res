from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from .contracts import StudioContract

OPAQUE_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,159}$"
SHA256_PATTERN = r"^[0-9a-fA-F]{64}$"

ClaimKindV1 = Literal["observation", "documented_statement", "inference"]
RightsStatusV1 = Literal[
    "public_metadata",
    "authorized_access",
    "open_license",
    "rights_verified",
    "review_required",
    "prohibited",
]
SceneRouteV1 = Literal["real_context", "fictional_original", "hybrid_extension"]
ProductionStateV1 = Literal[
    "brief",
    "research_approved",
    "script_approved",
    "storyboard_approved",
    "assets_approved",
    "rough_cut",
    "craft_review",
    "final_qc",
    "publishable",
]

PRODUCTION_STATES: tuple[ProductionStateV1, ...] = (
    "brief",
    "research_approved",
    "script_approved",
    "storyboard_approved",
    "assets_approved",
    "rough_cut",
    "craft_review",
    "final_qc",
    "publishable",
)


class KnowledgeEvidenceV1(StudioContract):
    evidence_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    source_url: str = Field(min_length=1, max_length=4000)
    source_title: str = Field(min_length=1, max_length=1000)
    accessed_at: datetime
    locator: str | None = Field(default=None, max_length=1000)
    checksum_sha256: str | None = Field(default=None, pattern=SHA256_PATTERN)
    rights_status: RightsStatusV1
    notes: str = Field(default="", max_length=2000)


class KnowledgeClaimV1(StudioContract):
    schema_version: Literal["studio.knowledge-claim.v1"] = "studio.knowledge-claim.v1"
    claim_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    statement: str = Field(min_length=1, max_length=4000)
    kind: ClaimKindV1
    evidence: list[KnowledgeEvidenceV1] = Field(default_factory=list, max_length=100)
    confidence: float = Field(ge=0, le=1)
    inference_basis: str | None = Field(default=None, max_length=4000)
    limitations: list[str] = Field(default_factory=list, max_length=100)
    human_reviewed: bool = False

    @model_validator(mode="after")
    def validate_claim(self) -> KnowledgeClaimV1:
        evidence_ids = [item.evidence_id for item in self.evidence]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("Knowledge evidence ids must be unique")
        if self.kind != "inference" and not self.evidence:
            raise ValueError("Observed and documented claims require evidence")
        if self.kind == "inference" and not self.inference_basis:
            raise ValueError("An inference requires an explicit inference basis")
        if any(item.rights_status == "prohibited" for item in self.evidence):
            raise ValueError("Prohibited evidence cannot support a knowledge claim")
        return self


class CreativeCouncilRecommendationV1(StudioContract):
    lens: Literal[
        "content_strategy",
        "advertising_copy",
        "narrative_writing",
        "character_performance",
        "direction",
        "world_production_design",
        "cinematography",
        "editing",
        "motion_cgi_vfx",
        "sound_music_voice",
        "research_provenance",
        "adversarial_critique",
    ]
    recommendation: str = Field(min_length=1, max_length=4000)
    rationale: str = Field(min_length=1, max_length=4000)
    claim_ids: list[str] = Field(default_factory=list, max_length=100)
    confidence: float = Field(ge=0, le=1)
    dissent: str | None = Field(default=None, max_length=2000)


class CreativeCouncilDecisionV1(StudioContract):
    schema_version: Literal["studio.creative-council-decision.v1"] = "studio.creative-council-decision.v1"
    decision_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    subject_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    recommendations: list[CreativeCouncilRecommendationV1] = Field(min_length=2, max_length=20)
    divergences: list[str] = Field(default_factory=list, max_length=100)
    decision: str = Field(min_length=1, max_length=4000)
    justification: str = Field(min_length=1, max_length=4000)
    decided_by: str = Field(min_length=1, max_length=500)
    human_approved: bool = False
    decided_at: datetime

    @model_validator(mode="after")
    def validate_council(self) -> CreativeCouncilDecisionV1:
        lenses = [item.lens for item in self.recommendations]
        if len(lenses) != len(set(lenses)):
            raise ValueError("Creative council lenses must be unique")
        return self


class CopyBriefV1(StudioContract):
    schema_version: Literal["studio.copy-brief.v1"] = "studio.copy-brief.v1"
    copy_brief_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    audience: str = Field(min_length=1, max_length=2000)
    awareness_stage: Literal["unaware", "problem_aware", "solution_aware", "product_aware", "most_aware"]
    promise: str = Field(min_length=1, max_length=1000)
    mechanism: str = Field(min_length=1, max_length=2000)
    objection: str = Field(min_length=1, max_length=2000)
    proof: list[str] = Field(min_length=1, max_length=100)
    call_to_action: str = Field(min_length=1, max_length=500)
    constraints: list[str] = Field(default_factory=list, max_length=100)
    claim_ids: list[str] = Field(default_factory=list, max_length=100)


class CharacterBibleV1(StudioContract):
    schema_version: Literal["studio.character-bible.v1"] = "studio.character-bible.v1"
    character_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    name: str = Field(min_length=1, max_length=500)
    identity_kind: Literal["fictional_original", "authorized_real_person", "nonhuman"]
    appearance: str = Field(min_length=1, max_length=4000)
    personality: str = Field(min_length=1, max_length=4000)
    objective: str = Field(min_length=1, max_length=2000)
    behavior: str = Field(min_length=1, max_length=4000)
    voice: str = Field(min_length=1, max_length=2000)
    wardrobe: str = Field(min_length=1, max_length=2000)
    continuity_rules: list[str] = Field(min_length=1, max_length=100)
    consent_grant_id: str | None = Field(default=None, pattern=OPAQUE_ID_PATTERN)

    @model_validator(mode="after")
    def validate_identity(self) -> CharacterBibleV1:
        if self.identity_kind == "authorized_real_person" and not self.consent_grant_id:
            raise ValueError("A real-person character requires an explicit consent grant")
        if self.identity_kind != "authorized_real_person" and self.consent_grant_id:
            raise ValueError("Consent grants may only bind authorized real-person characters")
        return self


class WorldBibleV1(StudioContract):
    schema_version: Literal["studio.world-bible.v1"] = "studio.world-bible.v1"
    world_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    space: str = Field(min_length=1, max_length=4000)
    period: str = Field(min_length=1, max_length=1000)
    rules: list[str] = Field(min_length=1, max_length=200)
    materials: list[str] = Field(min_length=1, max_length=100)
    climate: str = Field(min_length=1, max_length=1000)
    physics: list[str] = Field(min_length=1, max_length=100)
    visual_language: str = Field(min_length=1, max_length=4000)
    prohibited_imitation_targets: list[str] = Field(default_factory=list, max_length=100)


class PerformancePlanV1(StudioContract):
    schema_version: Literal["studio.performance-plan.v1"] = "studio.performance-plan.v1"
    performance_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    character_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    intention: str = Field(min_length=1, max_length=2000)
    emotion_progression: list[str] = Field(min_length=1, max_length=100)
    pace: str = Field(min_length=1, max_length=1000)
    pauses: list[str] = Field(default_factory=list, max_length=100)
    gestures: list[str] = Field(default_factory=list, max_length=100)
    gaze: str = Field(min_length=1, max_length=1000)
    vocal_direction: str = Field(min_length=1, max_length=2000)


class SceneBlueprintV1(StudioContract):
    schema_version: Literal["studio.scene-blueprint.v1"] = "studio.scene-blueprint.v1"
    scene_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    route: SceneRouteV1
    world_bible_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    purpose: str = Field(min_length=1, max_length=2000)
    camera_reconstruction: str = Field(min_length=1, max_length=2000)
    depth_and_geometry: str = Field(min_length=1, max_length=2000)
    lighting: str = Field(min_length=1, max_length=2000)
    permitted_regions: list[str] = Field(default_factory=list, max_length=100)
    protected_regions: list[str] = Field(default_factory=list, max_length=100)
    environment_authorization_id: str | None = Field(default=None, pattern=OPAQUE_ID_PATTERN)
    continuity_checks: list[str] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_scene_route(self) -> SceneBlueprintV1:
        if self.route in {"real_context", "hybrid_extension"}:
            if not self.environment_authorization_id:
                raise ValueError("Real and hybrid scenes require environment authorization")
            if not self.protected_regions:
                raise ValueError("Real and hybrid scenes require protected regions")
        if self.route == "fictional_original" and self.environment_authorization_id:
            raise ValueError("An original fictional scene cannot claim real-environment authorization")
        return self


class VisionRegionV1(StudioContract):
    region_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    kind: Literal["box", "mask", "track", "depth", "ocr", "speech"]
    label: str = Field(min_length=1, max_length=500)
    start_microseconds: int = Field(ge=0)
    end_microseconds: int = Field(gt=0)
    confidence: float = Field(ge=0, le=1)
    coordinates_normalized: list[float] = Field(default_factory=list, max_length=8)
    artifact_ref: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def validate_region(self) -> VisionRegionV1:
        if self.end_microseconds <= self.start_microseconds:
            raise ValueError("Vision region end must be after start")
        if self.coordinates_normalized and any(
            coordinate < 0 or coordinate > 1 for coordinate in self.coordinates_normalized
        ):
            raise ValueError("Vision coordinates must be normalized")
        return self


class VisionObservationV1(StudioContract):
    schema_version: Literal["studio.vision-observation.v1"] = "studio.vision-observation.v1"
    observation_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    source_asset_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    source_checksum_sha256: str = Field(pattern=SHA256_PATTERN)
    regions: list[VisionRegionV1] = Field(default_factory=list, max_length=10000)
    objective_findings: list[str] = Field(default_factory=list, max_length=1000)
    semantic_inferences: list[str] = Field(default_factory=list, max_length=1000)
    abstentions: list[str] = Field(default_factory=list, max_length=1000)
    provider_lineage: list[str] = Field(min_length=1, max_length=100)
    observed_at: datetime


class GenerativeShotSpecV1(StudioContract):
    schema_version: Literal["studio.generative-shot-spec.v1"] = "studio.generative-shot-spec.v1"
    shot_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    scene_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    beat_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    composition: str = Field(min_length=1, max_length=2000)
    camera: str = Field(min_length=1, max_length=2000)
    lens: str = Field(min_length=1, max_length=1000)
    movement: str = Field(min_length=1, max_length=1000)
    duration_milliseconds: int = Field(ge=100, le=300_000)
    action: str = Field(min_length=1, max_length=2000)
    continuity_in: list[str] = Field(default_factory=list, max_length=100)
    continuity_out: list[str] = Field(default_factory=list, max_length=100)
    negative_constraints: list[str] = Field(min_length=1, max_length=100)
    purpose: str = Field(min_length=1, max_length=2000)


class AssetRequirementV1(StudioContract):
    resource_query: str | None = Field(default=None, max_length=500)
    resolution_status: Literal["available", "missing", "candidate", "verified"] = "available"
    asset_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    kind: Literal["video", "image", "audio", "voice", "music", "font", "model", "scene", "other"]
    purpose: str = Field(min_length=1, max_length=2000)
    origin: str = Field(min_length=1, max_length=4000)
    rights_status: RightsStatusV1
    estimated_cost_minor: int = Field(ge=0)
    dependencies: list[str] = Field(default_factory=list, max_length=100)


class AssetPlanV1(StudioContract):
    schema_version: Literal["studio.asset-plan.v1"] = "studio.asset-plan.v1"
    plan_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    assets: list[AssetRequirementV1] = Field(min_length=1, max_length=1000)
    human_approved: bool = False

    @model_validator(mode="after")
    def validate_assets(self) -> AssetPlanV1:
        ids = [item.asset_id for item in self.assets]
        if len(ids) != len(set(ids)):
            raise ValueError("Asset ids must be unique")
        if self.human_approved and any(
            item.rights_status not in {"open_license", "rights_verified"} for item in self.assets
        ):
            raise ValueError("An approved asset plan requires cleared rights for every asset")
        return self


class RepositoryCapabilityV1(StudioContract):
    schema_version: Literal["studio.repository-capability.v1"] = "studio.repository-capability.v1"
    repository_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    origin_url: str = Field(min_length=1, max_length=4000)
    commit_sha: str = Field(pattern=r"^[0-9a-fA-F]{7,64}$")
    license_spdx: str = Field(min_length=1, max_length=200)
    purpose: str = Field(min_length=1, max_length=2000)
    inputs: list[str] = Field(default_factory=list, max_length=100)
    outputs: list[str] = Field(default_factory=list, max_length=100)
    dependencies: list[str] = Field(default_factory=list, max_length=500)
    hardware: str = Field(min_length=1, max_length=2000)
    pt_br_support: Literal["native", "partial", "unknown", "none"]
    quality_notes: str = Field(min_length=1, max_length=4000)
    deterministic: Literal["yes", "partial", "no", "unknown"]
    observable: Literal["yes", "partial", "no", "unknown"]
    risks: list[str] = Field(default_factory=list, max_length=200)
    integration: str = Field(min_length=1, max_length=4000)
    decision: Literal["adopt", "adapt", "reference-only", "reject"]
    benchmark: str = Field(min_length=1, max_length=4000)
    reviewed_at: datetime


class ProductionStateEventV1(StudioContract):
    state: ProductionStateV1
    entered_at: datetime
    artifact_refs: list[str] = Field(default_factory=list, max_length=100)
    approval_id: str | None = Field(default=None, pattern=OPAQUE_ID_PATTERN)
    rejection_reason: str | None = Field(default=None, max_length=2000)


class ProductionRunV1(StudioContract):
    schema_version: Literal["studio.production-run.v1"] = "studio.production-run.v1"
    run_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    current_state: ProductionStateV1
    history: list[ProductionStateEventV1] = Field(min_length=1, max_length=1000)
    artifact_versions: dict[str, str] = Field(default_factory=dict)
    estimated_cost_minor: int = Field(ge=0)
    actual_cost_minor: int = Field(ge=0)
    lineage_ids: list[str] = Field(default_factory=list, max_length=1000)

    @model_validator(mode="after")
    def validate_history(self) -> ProductionRunV1:
        if self.history[-1].state != self.current_state:
            raise ValueError("Current production state must match the last history event")
        indices = [PRODUCTION_STATES.index(item.state) for item in self.history]
        for previous, current in zip(indices, indices[1:], strict=False):
            if current > previous + 1:
                raise ValueError("Production states cannot skip mandatory gates")
        for event in self.history:
            if (
                event.state
                in {
                    "research_approved",
                    "script_approved",
                    "storyboard_approved",
                    "assets_approved",
                    "craft_review",
                    "final_qc",
                    "publishable",
                }
                and not event.approval_id
            ):
                raise ValueError(f"Production state {event.state} requires an approval id")
        return self


class R1AnalysisReviewV1(StudioContract):
    unit_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    analysis_path: str = Field(min_length=1, max_length=4000)
    shots_path: str = Field(min_length=1, max_length=4000)
    temporal_map_complete: bool
    provenance_complete: bool
    human_reviewed: bool = False


class CreativeResearchGateV1(StudioContract):
    schema_version: Literal["studio.creative-research-gate.v1"] = "studio.creative-research-gate.v1"
    pilot_id: str = Field(pattern=OPAQUE_ID_PATTERN)
    analyses: list[R1AnalysisReviewV1] = Field(min_length=12, max_length=12)
    taxonomy_report_path: str = Field(min_length=1, max_length=4000)
    taxonomy_human_approved: bool = False
    corpus_expansion_eligible: bool
    expensive_generation_eligible: Literal[False] = False
    blockers: list[str]
    evaluated_at: datetime

    @model_validator(mode="after")
    def validate_gate(self) -> CreativeResearchGateV1:
        ids = [item.unit_id for item in self.analyses]
        if len(ids) != len(set(ids)):
            raise ValueError("R1 analysis ids must be unique")
        expected = (
            all(
                item.temporal_map_complete and item.provenance_complete and item.human_reviewed
                for item in self.analyses
            )
            and self.taxonomy_human_approved
            and not self.blockers
        )
        if self.corpus_expansion_eligible != expected:
            raise ValueError("R1 corpus eligibility does not match review evidence")
        return self


def evaluate_creative_research_gate(
    *,
    pilot_id: str,
    analyses: list[R1AnalysisReviewV1],
    taxonomy_report_path: str,
    taxonomy_human_approved: bool,
    evaluated_at: datetime,
) -> CreativeResearchGateV1:
    blockers: list[str] = []
    if len(analyses) != 12:
        blockers.append("r1_requires_exactly_12_analyses")
    for item in analyses:
        if not item.temporal_map_complete:
            blockers.append(f"temporal_map_incomplete:{item.unit_id}")
        if not item.provenance_complete:
            blockers.append(f"provenance_incomplete:{item.unit_id}")
        if not item.human_reviewed:
            blockers.append(f"human_review_required:{item.unit_id}")
    if not taxonomy_human_approved:
        blockers.append("taxonomy_human_approval_required")
    eligible = len(analyses) == 12 and not blockers
    return CreativeResearchGateV1(
        pilot_id=pilot_id,
        analyses=analyses,
        taxonomy_report_path=taxonomy_report_path,
        taxonomy_human_approved=taxonomy_human_approved,
        corpus_expansion_eligible=eligible,
        expensive_generation_eligible=False,
        blockers=sorted(set(blockers)),
        evaluated_at=evaluated_at,
    )
