"""Editorial decisions are provider output, never evidence of audiovisual quality."""

import re
import unicodedata
from typing import Any, Literal

from pydantic import Field, model_validator

from .cinematic_direction import CinematicArtDirectionV1, CinematicShotIntentV1
from .contextual_editing import ContextualPlanRequestV1
from .contracts import StudioContract
from .hybrid_video import HybridProductionPolicyV1


class VisualConceptV1(StudioContract):
    id: str = Field(min_length=1, max_length=120)
    premise: str = Field(min_length=1, max_length=2000)
    visual_mechanism: str = Field(min_length=1, max_length=2000)
    clarity: str = Field(min_length=1, max_length=1000)
    specificity: str = Field(min_length=1, max_length=1000)
    continuity: str = Field(min_length=1, max_length=1000)
    identity_fit: str = Field(min_length=1, max_length=1000)
    feasibility: str = Field(min_length=1, max_length=1000)


class IndispensableVisualMaterialV1(StudioContract):
    """A visual dependency whose absence changes what a beat can demonstrate."""

    id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
    kind: Literal["image", "video", "logo"]
    visual_role: Literal["hero", "support", "background"] = "hero"
    query: str = Field(min_length=1, max_length=500)
    purpose: str = Field(min_length=1, max_length=1000)
    acceptance_criteria: list[str] = Field(min_length=1, max_length=15)
    source_class: Literal[
        "auto", "project", "catalog", "licensed_stock", "brand_asset", "generated_original"
    ] = "auto"
    procedural_allowed: bool = False
    requirement_class: Literal["mandatory", "preferred", "composable"] = "mandatory"
    preferred_criteria: list[str] = Field(default_factory=list, max_length=15)
    component_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")

    @model_validator(mode="after")
    def classification_is_executable(self):
        if self.requirement_class == "composable" and not self.component_id:
            raise ValueError("production_composable_material_component_required")
        if self.requirement_class != "composable" and self.component_id:
            raise ValueError("production_component_only_for_composable_material")
        return self


class VisualDemonstrationV1(StudioContract):
    """The falsifiable visual claim made by one storyboard beat."""

    schema_version: Literal["studio.visual-demonstration.v1"] = "studio.visual-demonstration.v1"
    observable_action: str = Field(min_length=1, max_length=2000)
    intended_understanding: str = Field(min_length=1, max_length=2000)
    proof_elements: list[str] = Field(min_length=1, max_length=10)
    indispensable_materials: list[IndispensableVisualMaterialV1] = Field(default_factory=list, max_length=10)
    generic_failure_signals: list[str] = Field(min_length=1, max_length=10)
    procedural_sufficiency_reason: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def procedural_choice_is_explained(self):
        if (
            any(item.procedural_allowed for item in self.indispensable_materials)
            and not self.procedural_sufficiency_reason
        ):
            raise ValueError("production_procedural_sufficiency_reason_required")
        return self


class VisualBlueprintV1(StudioContract):
    """Editorial decisions, not evidence that a scene has been rendered."""

    schema_version: Literal["studio.visual-blueprint.v1"] = "studio.visual-blueprint.v1"
    message: str = Field(min_length=1, max_length=2000)
    evidence: str = Field(min_length=1, max_length=2000)
    representation: Literal["footage", "cutout", "comparison", "process", "typography", "mixed"]
    rejected_alternatives: list[str] = Field(min_length=1, max_length=5)
    primary_material_query: str = Field(min_length=1, max_length=500)
    supporting_material_queries: list[str] = Field(default_factory=list, max_length=10)
    region_of_interest: str = Field(min_length=1, max_length=1000)
    hierarchy: list[str] = Field(min_length=1, max_length=8)
    completion_criteria: list[str] = Field(min_length=1, max_length=10)
    visual_register: str = Field(min_length=1, max_length=100)
    demonstration: VisualDemonstrationV1 | None = None
    shot_sequence: list[CinematicShotIntentV1] = Field(default_factory=list, max_length=12)


class StoryboardBeatV1(StudioContract):
    id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
    source_excerpt: str = Field(min_length=1, max_length=4000)
    narration: str = Field(default="", max_length=4000)
    initial_state: str = Field(min_length=1, max_length=2000)
    action: str = Field(min_length=1, max_length=2000)
    consequence: str = Field(min_length=1, max_length=2000)
    focus: str = Field(min_length=1, max_length=1000)
    knowledge_gained: str = Field(min_length=1, max_length=2000)
    transition_reason: str = Field(min_length=1, max_length=1000)
    material_queries: list[str] = Field(default_factory=list, max_length=20)
    technique_ids: list[str] = Field(default_factory=list, max_length=20)
    hold_reason: str | None = Field(default=None, max_length=1000)
    visual_blueprint: VisualBlueprintV1 | None = None


class EditorialDirectionV1(StudioContract):
    schema_version: Literal["studio.editorial-direction.v1"] = "studio.editorial-direction.v1"
    concepts: list[VisualConceptV1] = Field(min_length=2, max_length=2)
    selected_concept_id: str
    selection_reason: str = Field(min_length=1, max_length=3000)
    beats: list[StoryboardBeatV1] = Field(min_length=1, max_length=50)
    art_direction: CinematicArtDirectionV1 | None = None

    @model_validator(mode="after")
    def references(self):
        ids = [c.id for c in self.concepts]
        if len(set(ids)) != 2 or self.selected_concept_id not in ids:
            raise ValueError("production_concept_selection_invalid")
        if len({b.id for b in self.beats}) != len(self.beats):
            raise ValueError("production_beat_ids_duplicate")
        if self.concepts[0].visual_mechanism.strip() == self.concepts[1].visual_mechanism.strip():
            raise ValueError("production_concepts_must_differ")
        return self


class GeneratedVideoPolicyV2(StudioContract):
    """Provider-neutral limits exposed to the director and material resolver."""

    schema_version: Literal["studio.generated-video-policy.v2"] = "studio.generated-video-policy.v2"
    mode: Literal["disabled", "local_experimental", "auto"] = "disabled"
    allowed_profile_ids: list[str] = Field(
        default_factory=lambda: ["animatediff-lightning-sd15-a-v1"],
        min_length=1,
        max_length=5,
    )
    max_candidates: int = Field(default=1, ge=1, le=6)
    allow_experimental: bool = False
    maximum_generated_seconds: float = Field(default=1, gt=0, le=4)

    @model_validator(mode="after")
    def experimental_requires_consent(self):
        if self.mode == "local_experimental" and not self.allow_experimental:
            raise ValueError("production_experimental_video_consent_required")
        return self


class ProductionRequestV1(StudioContract):
    schema_version: Literal["studio.editorial-production-request.v1"] = "studio.editorial-production-request.v1"
    direction: ContextualPlanRequestV1
    duration_seconds: int = Field(default=15, ge=5, le=120)
    mode: Literal["mixed_montage", "motion"] = "mixed_montage"
    evaluation_scope: Literal["audiovisual", "visual_only"] = "audiovisual"
    quality_phase_id: Literal["visual-quality-2026-10-01"] | None = None
    require_visual_blueprint: bool = False
    use_semantic_compositions: bool = False
    demonstration_policy: Literal["disabled", "required"] = "disabled"
    material_semantics_policy: Literal["legacy", "contextual_video_v1"] = "legacy"
    cinematic_direction_policy: Literal["disabled", "mixed_motion_v1", "editorial_motion_v2"] = "disabled"
    native_scene_editing: bool = False
    generated_video_policy: Literal["disabled", "single_short_clip"] = "disabled"
    generated_video: GeneratedVideoPolicyV2 | None = None
    hybrid_policy: HybridProductionPolicyV1 | None = None
    narration_asset_id: str | None = None
    stock_voice_provider: str = Field(default="kokoro-82m-stock", min_length=1, max_length=160)
    stock_voice_key: str = Field(default="pf_dora", min_length=1, max_length=120)

    def effective_generated_video_policy(self) -> GeneratedVideoPolicyV2:
        if self.generated_video is not None:
            return self.generated_video
        if self.generated_video_policy == "single_short_clip":
            return GeneratedVideoPolicyV2(
                mode="auto",
                allowed_profile_ids=["sora-2"],
                max_candidates=1,
                allow_experimental=False,
                maximum_generated_seconds=4,
            )
        return GeneratedVideoPolicyV2()

    def effective_hybrid_policy(self) -> HybridProductionPolicyV1:
        if self.hybrid_policy is not None:
            return self.hybrid_policy
        legacy = self.effective_generated_video_policy()
        if legacy.mode == "disabled":
            return HybridProductionPolicyV1()
        return HybridProductionPolicyV1(
            mode="auto",
            allowed_profile_ids=list(legacy.allowed_profile_ids),
            allow_experimental=legacy.allow_experimental,
            allow_conditional_commercial_use=legacy.allow_experimental,
            allow_remote_api=legacy.mode == "auto",
            max_candidates_per_need=legacy.max_candidates,
            maximum_generated_seconds_total=legacy.maximum_generated_seconds,
            budget_envelope_id="legacy-generated-video" if legacy.mode == "auto" else None,
            maximum_api_spend_usd=(
                0.40
                if legacy.mode == "auto" and "sora-2" in legacy.allowed_profile_ids
                else 0
            ),
        )

    @model_validator(mode="after")
    def one_generation_policy(self):
        if self.quality_phase_id and (
            self.duration_seconds != 15 or self.mode != "mixed_montage" or self.evaluation_scope != "audiovisual"
        ):
            raise ValueError("visual_quality_phase_requires_15s_audiovisual_montage")
        if self.native_scene_editing and self.mode != "mixed_montage":
            raise ValueError("native_scene_mixed_montage_required")
        if self.native_scene_editing:
            policy = self.effective_hybrid_policy()
            if policy.max_candidates_per_need > 2 or policy.maximum_api_spend_usd > 10:
                raise ValueError("native_pilot_budget_or_candidate_limit")
        if self.hybrid_policy is not None and (
            self.generated_video is not None or self.generated_video_policy != "disabled"
        ):
            raise ValueError("production_generation_policy_conflict")
        return self


class ProductionRevisionV1(StudioContract):
    expected_run_revision: int = Field(ge=1)
    scene_ids: list[str] = Field(min_length=1, max_length=50)
    instruction: str = Field(min_length=1, max_length=4000)


class ExternalProductionReviewV1(StudioContract):
    expected_run_revision: int = Field(ge=1)
    render_checksum: str = Field(pattern=r"^[a-f0-9]{64}$")
    provider_label: str = Field(default="Gemini", min_length=1, max_length=120)
    text: str = Field(min_length=1, max_length=40000)


class ProductionFindingV1(StudioContract):
    scene_id: str
    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(gt=0)
    severity: Literal["observation", "correction", "blocker"]
    observation: str = Field(min_length=1, max_length=2000)
    evidence: str = Field(min_length=1, max_length=2000)
    correction: str = Field(default="", max_length=2000)
    confidence: float = Field(ge=0, le=1)
    uncertainty: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def interval(self):
        if self.end_seconds <= self.start_seconds:
            raise ValueError("production_finding_interval_invalid")
        return self


class ProductionCritiqueV1(StudioContract):
    schema_version: Literal["studio.production-critique.v1"] = "studio.production-critique.v1"
    coverage: Literal["partial", "full"]
    summary: str = Field(min_length=1, max_length=4000)
    findings: list[ProductionFindingV1] = Field(default_factory=list, max_length=100)
    speech_intelligibility: Literal["clear", "impaired", "unknown"] = "unknown"
    sound_event_accuracy: Literal["aligned", "misaligned", "unknown"] = "unknown"
    human_review: Literal["pending"] = "pending"


def normalize_direction_identifiers(payload: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """Repair transport-only IDs without changing editorial text or relationships."""
    value = dict(payload)
    repairs: list[dict[str, str]] = []
    concept_mappings: dict[str, str] = {}

    art_key = "artDirection" if "artDirection" in value else "art_direction"
    art_direction = value.get(art_key)
    if isinstance(art_direction, dict) and "rejectedstylemoves" in art_direction:
        art_direction = dict(art_direction)
        art_direction["rejectedStyleMoves"] = art_direction.pop("rejectedstylemoves")
        value[art_key] = art_direction
        repairs.append(
            {
                "field": "artDirection.rejectedStyleMoves",
                "from": "rejectedstylemoves",
                "to": "rejectedStyleMoves",
            }
        )

    def normalized(identifier: object, prefix: str, used: set[str]) -> tuple[str, str]:
        original = str(identifier or "")
        ascii_value = unicodedata.normalize("NFKD", original).encode("ascii", "ignore").decode("ascii")
        candidate = re.sub(r"[^A-Za-z0-9._-]+", "-", ascii_value).strip("-._") or prefix
        candidate = candidate[:80]
        base, suffix = candidate, 2
        while candidate in used:
            tail = f"-{suffix}"
            candidate = base[: 80 - len(tail)] + tail
            suffix += 1
        used.add(candidate)
        if original != candidate:
            repairs.append({"field": "id", "from": original, "to": candidate})
        return original, candidate

    concepts = []
    concept_ids: set[str] = set()
    for item in value.get("concepts", []):
        concept = dict(item)
        original, concept["id"] = normalized(concept.get("id"), "concept", concept_ids)
        concept_mappings[original] = concept["id"]
        concepts.append(concept)
    beats = []
    beat_ids: set[str] = set()
    for item in value.get("beats", []):
        if not isinstance(item, dict):
            raise ValueError("production_direction_beat_object_required")
        beat = dict(item)
        _, beat["id"] = normalized(beat.get("id"), "beat", beat_ids)
        blueprint_key = "visualBlueprint" if "visualBlueprint" in beat else "visual_blueprint"
        blueprint = beat.get(blueprint_key)
        if isinstance(blueprint, dict):
            blueprint = dict(blueprint)
            demonstration = blueprint.get("demonstration")
            if isinstance(demonstration, dict):
                demonstration = dict(demonstration)
                reason = demonstration.get(
                    "proceduralSufficiencyReason",
                    demonstration.get("procedural_sufficiency_reason"),
                )
                materials_key = (
                    "indispensableMaterials"
                    if "indispensableMaterials" in demonstration
                    else "indispensable_materials"
                )
                materials = []
                for material in demonstration.get(materials_key, []):
                    material = dict(material)
                    requirement_key = (
                        "requirementClass"
                        if "requirementClass" in material
                        else "requirement_class"
                    )
                    component_key = "componentId" if "componentId" in material else "component_id"
                    allowed_key = (
                        "proceduralAllowed" if "proceduralAllowed" in material else "procedural_allowed"
                    )
                    if (
                        material.get(component_key)
                        and material.get(requirement_key, "mandatory") != "composable"
                    ):
                        # A component must never silently satisfy a material the
                        # director classified as mandatory or preferred. Keep the
                        # stronger acquisition requirement and remove the
                        # contradictory procedural authorization.
                        removed = material.pop(component_key)
                        material[allowed_key] = False
                        repairs.append(
                            {
                                "field": (
                                    f"beats.{beat['id']}.demonstration."
                                    f"{material.get('id', 'material')}.componentId"
                                ),
                                "from": str(removed),
                                "to": "removed_non_composable",
                            }
                        )
                    if material.get(allowed_key) is True and not str(reason or "").strip():
                        # Lack of an explanation cannot grant a procedural
                        # substitution. Conservatively require acquisition and
                        # record the transport repair instead of paying for a
                        # second creative decision.
                        material[allowed_key] = False
                        repairs.append(
                            {
                                "field": (
                                    f"beats.{beat['id']}.demonstration."
                                    f"{material.get('id', 'material')}.proceduralAllowed"
                                ),
                                "from": "true_without_reason",
                                "to": "false",
                            }
                        )
                    materials.append(material)
                demonstration[materials_key] = materials
                blueprint["demonstration"] = demonstration
            beat[blueprint_key] = blueprint
        beats.append(beat)
    value["concepts"] = concepts
    value["beats"] = beats
    selected_key = "selectedConceptId" if "selectedConceptId" in value else "selected_concept_id"
    if selected_key in value and value[selected_key] in concept_mappings:
        value[selected_key] = concept_mappings[value[selected_key]]
    return value, repairs


def automatic_corrections(critique, rounds):
    """Bounded recommendations; provider confidence never grants human approval."""
    if rounds >= 2 or critique.coverage != "full" or any(f.severity == "blocker" for f in critique.findings):
        return []
    return [
        f for f in critique.findings if f.severity == "correction" and f.confidence >= 0.85 and f.correction.strip()
    ]


def validate_direction(direction: EditorialDirectionV1, request: ProductionRequestV1):
    """Source excerpts are verbatim. Semantic faithfulness still requires review."""
    source = request.direction.intent.script
    if request.cinematic_direction_policy in {"mixed_motion_v1", "editorial_motion_v2"} and direction.art_direction is None:
        raise ValueError("production_cinematic_art_direction_required")
    if request.cinematic_direction_policy == "editorial_motion_v2" and not direction.art_direction.motion_system:
        raise ValueError("production_editorial_motion_system_required")
    for beat in direction.beats:
        if request.require_visual_blueprint and beat.visual_blueprint is None:
            raise ValueError("production_visual_blueprint_required")
        if request.demonstration_policy == "required" and (
            beat.visual_blueprint is None or beat.visual_blueprint.demonstration is None
        ):
            raise ValueError("production_visual_demonstration_required:" + beat.id)
        if beat.source_excerpt not in source:
            raise ValueError("production_source_excerpt_not_in_script")
        if beat.narration and beat.narration not in source:
            raise ValueError("production_narration_not_in_script")
        if request.cinematic_direction_policy == "mixed_motion_v1":
            if not beat.visual_blueprint or not beat.visual_blueprint.shot_sequence:
                raise ValueError("production_cinematic_shot_sequence_required:" + beat.id)
            requirement_ids = {
                material.id
                for material in beat.visual_blueprint.demonstration.indispensable_materials
            } if beat.visual_blueprint.demonstration else set()
            referenced = {
                requirement_id
                for shot in beat.visual_blueprint.shot_sequence
                for requirement_id in shot.material_requirement_ids
            }
            unknown = referenced - requirement_ids
            if unknown:
                raise ValueError("production_cinematic_shot_material_unknown:" + sorted(unknown)[0])
    narration = " ".join(b.narration for b in direction.beats)
    if " ".join(narration.split()) != " ".join(source.split()):
        raise ValueError("production_script_coverage_required")
    for fact in request.direction.intent.locked_facts:
        if fact not in narration:
            raise ValueError("production_locked_fact_missing")
    if request.material_semantics_policy == "contextual_video_v1" and not any(
        material.kind == "video"
        and material.source_class == "licensed_stock"
        and not material.procedural_allowed
        and material.requirement_class == "mandatory"
        for beat in direction.beats
        if beat.visual_blueprint and beat.visual_blueprint.demonstration
        for material in beat.visual_blueprint.demonstration.indispensable_materials
    ):
        raise ValueError("production_direction_contextual_video_missing")
    return direction


def bind_storyboard_scene_ids(candidate, storyboard):
    """Bind scene identity by ordered beat without changing scene content."""
    if len(candidate.scenes) != len(storyboard.beats):
        return []
    repairs = []
    if storyboard.art_direction is not None and candidate.art_direction != storyboard.art_direction:
        before = (
            candidate.art_direction.model_dump(mode="json", by_alias=True)
            if hasattr(candidate.art_direction, "model_dump")
            else dict(candidate.art_direction)
        ) if candidate.art_direction is not None else None
        approved = (
            storyboard.art_direction
            if isinstance(storyboard.art_direction, CinematicArtDirectionV1)
            else CinematicArtDirectionV1.model_validate(storyboard.art_direction)
        )
        candidate.art_direction = approved.model_copy(deep=True)
        repairs.append(
            {
                "reason": "compiled_art_direction_rebound_to_approved_direction",
                "before": before,
                "after": candidate.art_direction.model_dump(mode="json", by_alias=True),
                "classification": "bounded_normalization",
                "requiresAlternative": False,
            }
        )
    for scene, beat in zip(candidate.scenes, storyboard.beats, strict=True):
        if scene.id == beat.id:
            continue
        before = scene.id
        scene.id = beat.id
        repairs.append(
            {
                "sceneId": beat.id,
                "reason": "scene_id_bound_to_storyboard_beat",
                "before": before,
                "after": beat.id,
                "classification": "bounded_normalization",
                "requiresAlternative": False,
            }
        )
    return repairs


def production_gates(direction: EditorialDirectionV1, request: ProductionRequestV1, candidate=None):
    """Report planning evidence without treating declarations as rendered proof."""

    validate_direction(direction, request)
    fidelity = {
        "status": "passed",
        "evidence": [beat.source_excerpt for beat in direction.beats],
        "reason": "Script coverage and locked facts are preserved verbatim.",
        "nextAction": None,
    }
    demonstrations = [
        beat.visual_blueprint.demonstration
        for beat in direction.beats
        if beat.visual_blueprint and beat.visual_blueprint.demonstration
    ]
    if request.demonstration_policy == "disabled":
        demonstrability = {
            "status": "inconclusive",
            "evidence": [],
            "reason": "This legacy request does not require a falsifiable visual demonstration.",
            "nextAction": "replan_scene",
        }
    elif len(demonstrations) != len(direction.beats):
        demonstrability = {
            "status": "failed",
            "evidence": [],
            "reason": "At least one beat has no observable action and visual proof contract.",
            "nextAction": "replan_scene",
        }
    else:
        demonstrability = {
            "status": "passed",
            "evidence": [
                {
                    "beatId": beat.id,
                    "observableAction": beat.visual_blueprint.demonstration.observable_action,
                    "intendedUnderstanding": beat.visual_blueprint.demonstration.intended_understanding,
                    "proofElements": beat.visual_blueprint.demonstration.proof_elements,
                }
                for beat in direction.beats
            ],
            "reason": "Every beat declares an observable action, intended understanding and falsifiable proof.",
            "nextAction": None,
        }
    technique = {
        "status": "inconclusive",
        "evidence": [],
        "reason": "Technique suitability requires an executable composition and resolved material needs.",
        "nextAction": "select_route",
    }
    scene_stages = [
        {"sceneId": beat.id, "stage": "planned", "evidence": []}
        for beat in direction.beats
    ]
    if candidate is not None:
        scene_by_id = {scene.id: scene for scene in candidate.scenes}
        missing_route = []
        unresolved_materials = []
        stages = []
        for beat in direction.beats:
            scene = scene_by_id.get(beat.id)
            demo = beat.visual_blueprint.demonstration if beat.visual_blueprint else None
            if not scene or not scene.compositions:
                missing_route.append({"beatId": beat.id, "reason": "registered_composition_missing"})
                stages.append({"sceneId": beat.id, "stage": "planned", "evidence": []})
                continue
            indexed = {element.id: element for element in scene.elements}
            scene_pending = []
            if request.demonstration_policy == "required":
                for element in scene.elements:
                    normalized_purpose = unicodedata.normalize("NFKD", element.purpose).encode(
                        "ascii", "ignore"
                    ).decode().casefold()
                    asks_for_symbol = any(
                        term in normalized_purpose
                        for term in ("icon", "icone", "symbol", "simbolo", "lightbulb", "lampada")
                    )
                    if element.kind == "shape" and asks_for_symbol:
                        missing_route.append(
                            {
                                "beatId": beat.id,
                                "elementId": element.id,
                                "reason": "recognizable_symbol_represented_by_primitive_shape",
                            }
                        )
                for composition in scene.compositions:
                    targets = [indexed.get(identity) for identity in composition.target_ids]
                    targets = [item for item in targets if item is not None]
                    if composition.family == "format_transformation":
                        media = [item for item in targets if item.kind in {"image", "video"}]
                        formats = list(composition.viewport_formats)
                        asset_ids = {item.asset_id for item in media if item.asset_id}
                        procedural_identity = (
                            bool(composition.continuity_key)
                            and {item.content_identity for item in targets}
                            == {composition.continuity_key}
                            and all(item.kind in {"card", "shape", "text", "path"} for item in targets)
                        )
                        if (
                            len(set(formats)) < 2
                            or (
                                not procedural_identity
                                and (
                                    len(media) < 2
                                    or len(media) != len(targets)
                                    or (asset_ids and len(asset_ids) != 1)
                                )
                            )
                        ):
                            missing_route.append(
                                {
                                    "beatId": beat.id,
                                    "compositionId": composition.id,
                                    "reason": "format_transformation_not_visibly_continuous",
                                }
                            )
                    if composition.family == "annotated_material" and targets:
                        media = next(
                            (item for item in targets if item.kind in {"image", "video"}),
                            None,
                        )
                        semantic_annotations = []
                        for item in targets:
                            if item.kind not in {"shape", "path"}:
                                continue
                            purpose = unicodedata.normalize("NFKD", item.purpose).encode(
                                "ascii", "ignore"
                            ).decode().casefold()
                            if any(
                                term in purpose
                                for term in (
                                    "attention",
                                    "atencao",
                                    "highlight",
                                    "spotlight",
                                    "individ",
                                    "person",
                                    "people",
                                    "publico",
                                    "focus",
                                    "foco",
                                )
                            ):
                                semantic_annotations.append(item)
                        if semantic_annotations and media is not None and not (
                            media.region_of_interest
                            or all(item.region_of_interest for item in semantic_annotations)
                        ):
                            missing_route.append(
                                {
                                    "beatId": beat.id,
                                    "compositionId": composition.id,
                                    "elementIds": [item.id for item in semantic_annotations],
                                    "reason": "semantic_annotation_requires_observed_region",
                                }
                            )
            for material in demo.indispensable_materials if demo else []:
                if material.requirement_class == "preferred":
                    continue
                if material.requirement_class == "composable" or material.procedural_allowed:
                    available = {
                        *scene.technique_ids,
                        *(composition.family for composition in scene.compositions),
                    }
                    component = material.component_id
                    if component and component not in available:
                        missing_route.append(
                            {
                                "beatId": beat.id,
                                "requirementId": material.id,
                                "reason": "declared_component_missing",
                                "componentId": component,
                            }
                        )
                    continue
                needs = [
                    need
                    for need in scene.material_needs
                    if need.blueprint_requirement_id == material.id
                ]
                if not needs:
                    missing_route.append({"beatId": beat.id, "requirementId": material.id})
                    continue
                for need in needs:
                    target = indexed.get(need.target_id)
                    field = {"asset": "asset_id", "mask": "mask_asset_id", "font": "font_asset_id"}[
                        need.field
                    ]
                    if target is None or not getattr(target, field, None):
                        item = {
                            "beatId": beat.id,
                            "requirementId": material.id,
                            "needId": need.id,
                        }
                        unresolved_materials.append(item)
                        scene_pending.append(item)
            stages.append(
                {
                    "sceneId": beat.id,
                    "stage": "material_pending" if scene_pending else "executable",
                    "evidence": scene_pending or [composition.id for composition in scene.compositions],
                }
            )
        scene_stages = stages
        if missing_route:
            status, reason, action = (
                "failed",
                "The selected route cannot satisfy every mandatory material or component.",
                "select_route",
            )
            evidence = missing_route
        elif unresolved_materials:
            status, reason, action = (
                "inconclusive",
                "The route is planned, but mandatory materials are not resolved yet.",
                "resolve_material",
            )
            evidence = unresolved_materials
        else:
            status, reason, action = (
                "passed",
                "Registered compositions and mandatory materials are executable.",
                None,
            )
            evidence = [
                {"sceneId": scene.id, "compositionIds": [item.id for item in scene.compositions]}
                for scene in candidate.scenes
            ]
        technique = {
            "status": status,
            "evidence": evidence,
            "reason": reason,
            "nextAction": action,
        }
    return {
        "schemaVersion": "studio.production-gates.v1",
        "fidelity": fidelity,
        "demonstrability": demonstrability,
        "techniqueSuitability": technique,
        "sceneStages": scene_stages,
        "observedResult": {
            "status": "inconclusive",
            "evidence": [],
            "reason": "Rendered frames and temporal evidence are not available yet.",
            "nextAction": "inspect_interval",
        },
    }


def derive_blueprint_material_needs(candidate, storyboard):
    """Turn indispensable blueprint materials into stable executable requests."""

    from .contextual_editing_v2 import EditorialMaterialV2

    if len(candidate.scenes) != len(storyboard.beats):
        raise ValueError("production_storyboard_scene_binding_conflict")
    for scene, beat in zip(candidate.scenes, storyboard.beats, strict=True):
        demo = beat.visual_blueprint.demonstration if beat.visual_blueprint else None
        if demo is None:
            continue
        for requirement in demo.indispensable_materials:
            if requirement.requirement_class == "composable" or requirement.procedural_allowed:
                continue
            matches = [
                need for need in scene.material_needs if need.blueprint_requirement_id == requirement.id
            ]
            if matches:
                continue
            permitted_kinds = {"image"} if requirement.kind in {"image", "logo"} else {"video"}
            eligible_targets = [
                element for element in scene.elements if element.kind in permitted_kinds
            ]
            target = next(
                (element for element in eligible_targets if element.visual_role == requirement.visual_role),
                None,
            )
            if target is None:
                grouped_needs = [
                    need
                    for need in scene.material_needs
                    if need.target_id in {element.id for element in eligible_targets}
                    and need.kind in permitted_kinds
                    and need.blueprint_requirement_id is None
                ]
                if len(grouped_needs) > 1:
                    for need in grouped_needs:
                        need.blueprint_requirement_id = requirement.id
                        need.required = requirement.requirement_class == "mandatory"
                        need.requirement_class = requirement.requirement_class
                        need.preferred_criteria = requirement.preferred_criteria
                        if need.source_class == "auto":
                            need.source_class = requirement.source_class
                    continue
                if len(eligible_targets) == 1:
                    target = eligible_targets[0]
            if target is None:
                raise ValueError(
                    "production_indispensable_material_target_missing:"
                    + scene.id
                    + ":"
                    + requirement.id
                )
            existing = [
                need
                for need in scene.material_needs
                if need.target_id == target.id
                and need.kind in permitted_kinds
                and need.blueprint_requirement_id is None
            ]
            if len(existing) == 1:
                need = existing[0]
                need.blueprint_requirement_id = requirement.id
                need.required = requirement.requirement_class == "mandatory"
                need.requirement_class = requirement.requirement_class
                need.preferred_criteria = requirement.preferred_criteria
                if need.source_class == "auto":
                    need.source_class = requirement.source_class
                if not need.visual_description.strip():
                    need.visual_description = requirement.query
                need.acceptance_criteria = list(
                    dict.fromkeys([*need.acceptance_criteria, *requirement.acceptance_criteria])
                )[:30]
                continue
            scene.material_needs.append(
                EditorialMaterialV2(
                    id=("blueprint-" + requirement.id)[:80],
                    target_id=target.id,
                    kind=requirement.kind,
                    query=requirement.query,
                    purpose=requirement.purpose,
                    required=requirement.requirement_class == "mandatory",
                    official_required=requirement.source_class == "brand_asset",
                    source_class=requirement.source_class,
                    visual_description=requirement.query,
                    acceptance_criteria=requirement.acceptance_criteria,
                    blueprint_requirement_id=requirement.id,
                    requirement_class=requirement.requirement_class,
                    preferred_criteria=requirement.preferred_criteria,
                    component_id=requirement.component_id,
                )
            )
    return candidate


def rebind_selected_blueprint_materials(storyboard, candidate, selected_scene_ids):
    """Project an approved local route's material contract into its blueprint.

    Material rejection can legitimately change *how* one scene proves the same
    message.  The replacement scene remains authoritative only for executable
    material requirements; facts, narration, concepts and every unselected
    beat remain copied from the approved direction.
    """

    selected = set(selected_scene_ids)
    if not selected:
        return storyboard, []
    scene_by_id = {scene.id: scene for scene in candidate.scenes}
    if not selected <= scene_by_id.keys():
        raise ValueError("production_revision_scene_binding_conflict")
    revised = storyboard.model_copy(deep=True)
    repairs = []
    for beat in revised.beats:
        if beat.id not in selected or not beat.visual_blueprint:
            continue
        scene = scene_by_id[beat.id]
        target_by_id = {element.id: element for element in scene.elements}
        materials = []
        for need in scene.material_needs:
            if need.kind not in {"image", "video", "logo"}:
                continue
            # `requirementClass` carries the editorial contract. Keep the
            # legacy boolean aligned so downstream acquisition cannot skip a
            # material the selected route itself calls mandatory.
            need.required = need.requirement_class == "mandatory"
            target = target_by_id.get(need.target_id)
            role = getattr(target, "visual_role", "hero")
            if role not in {"hero", "support", "background"}:
                role = "support"
            requirement_class = need.requirement_class
            component_id = need.component_id if requirement_class == "composable" else None
            materials.append(
                IndispensableVisualMaterialV1(
                    id=need.blueprint_requirement_id or need.id,
                    kind=need.kind,
                    visual_role=role,
                    query=need.visual_description or need.query,
                    purpose=need.purpose,
                    acceptance_criteria=need.acceptance_criteria
                    or ["The requested material is visibly present and usable."],
                    source_class=need.source_class,
                    procedural_allowed=requirement_class == "composable",
                    requirement_class=requirement_class,
                    preferred_criteria=need.preferred_criteria,
                    component_id=component_id,
                )
            )
        demonstration = beat.visual_blueprint.demonstration
        if demonstration is None:
            raise ValueError("production_revision_demonstration_missing")
        before = [item.id for item in demonstration.indispensable_materials]
        demonstration.indispensable_materials = materials
        if any(item.procedural_allowed for item in materials):
            demonstration.procedural_sufficiency_reason = (
                demonstration.procedural_sufficiency_reason
                or "The registered deterministic component performs the observable action."
            )
        if materials:
            beat.visual_blueprint.primary_material_query = materials[0].query
        candidate_shots = {shot.id: shot for shot in scene.shot_plan}
        for shot in beat.visual_blueprint.shot_sequence:
            proposed = candidate_shots.get(shot.id)
            if proposed is None:
                continue
            shot.material_requirement_ids = list(proposed.material_requirement_ids)
            shot.execution_component_ids = list(proposed.execution_component_ids)
        repairs.append(
            {
                "sceneId": beat.id,
                "reason": "selected_scene_material_route_rebound",
                "beforeRequirementIds": before,
                "afterRequirementIds": [item.id for item in materials],
                "shotBindings": {
                    shot.id: {
                        "materialRequirementIds": list(shot.material_requirement_ids),
                        "executionComponentIds": list(shot.execution_component_ids),
                    }
                    for shot in beat.visual_blueprint.shot_sequence
                },
                "classification": "localized_direction_revision",
                "requiresAlternative": False,
            }
        )
    return revised, repairs


def recover_selected_scene_shot_plans(storyboard, candidate, selected_scene_ids):
    """Derive shot intervals from a recovered scene's authored visual states.

    This is intentionally narrow: it runs only for selected local revisions
    whose provider response already contains initial, action and consequence
    states but was truncated before ``shotPlan``. The derivation chooses only
    elements and component relations present in that response, then writes the
    same shot contract to the executable scene and its revised blueprint.
    """

    selected = set(selected_scene_ids)
    revised = storyboard.model_copy(deep=True)
    beats = {beat.id: beat for beat in revised.beats}
    repairs = []
    phase_function = {
        "initial": "establish",
        "action": "demonstrate",
        "consequence": "consequence",
        "exit": "consequence",
    }
    for scene in candidate.scenes:
        if scene.id not in selected or scene.shot_plan:
            continue
        beat = beats.get(scene.id)
        if not beat or not beat.visual_blueprint:
            continue
        phases = {state.phase for state in scene.visual_states}
        if not {"initial", "action", "consequence"} <= phases:
            continue
        indexed = {element.id: element for element in scene.elements}
        ordered_states = sorted(scene.visual_states, key=lambda item: item.frame)
        authored = list(beat.visual_blueprint.shot_sequence)
        recovered = []
        used_starts = set()
        for index, state in enumerate(ordered_states):
            preferred = [indexed[item] for item in state.essential_element_ids if item in indexed]
            if not preferred:
                preferred = [
                    element
                    for element in scene.elements
                    if element.start_frame <= state.frame < element.start_frame + element.duration_frames
                    and element.visual_role in {"hero", "support"}
                ]
            if not preferred:
                continue
            preferred.sort(
                key=lambda element: (
                    state.phase == "consequence" and element.kind not in {"image", "video"},
                    element.start_frame,
                    element.id,
                )
            )
            target = preferred[0]
            start = max(state.frame, target.start_frame)
            if start in used_starts or start >= scene.duration_frames:
                continue
            used_starts.add(start)
            recovered.append((state, target, start, index))
        recovered.sort(key=lambda item: item[2])
        if not recovered or recovered[0][2] != 0:
            continue
        shots = []
        for index, (state, target, start, _) in enumerate(recovered):
            end = recovered[index + 1][2] if index + 1 < len(recovered) else scene.duration_frames
            end = min(end, target.start_frame + target.duration_frames)
            if end <= start:
                continue
            composition = next(
                (item for item in scene.compositions if target.id in item.target_ids),
                None,
            )
            template = authored[-1] if state.phase in {"consequence", "exit"} else authored[0]
            material_ids = [
                need.blueprint_requirement_id or need.id
                for need in scene.material_needs
                if need.target_id == target.id
            ]
            action = state.purpose
            if state.expected_changes:
                action = "; ".join(state.expected_changes)
            shots.append(
                template.model_copy(
                    deep=True,
                    update={
                        "id": f"recovered-{state.phase}-{index + 1}",
                        "function": phase_function[state.phase],
                        "subject": target.purpose,
                        "observable_action": action,
                        "region_of_interest": target.purpose,
                        "attention_start": state.purpose,
                        "attention_end": action,
                        "material_requirement_ids": material_ids,
                        "execution_component_ids": [composition.family] if composition else [],
                        "target_element_ids": [target.id],
                        "verification": scene.verification or [state.purpose],
                        "start_frame": start,
                        "end_frame_exclusive": end,
                    },
                )
            )
        if not shots or shots[-1].end_frame_exclusive != scene.duration_frames:
            continue
        scene.shot_plan = shots
        beat.visual_blueprint.shot_sequence = [shot.model_copy(deep=True) for shot in shots]
        repairs.append(
            {
                "sceneId": scene.id,
                "reason": "truncated_local_revision_shot_plan_recovered_from_visual_states",
                "shotIds": [shot.id for shot in shots],
                "classification": "bounded_normalization",
                "requiresAlternative": False,
            }
        )
    return revised, repairs


def validate_blueprint_composition(candidate, storyboard, request):
    """Reject a structural substitution; relevance still needs observed material."""
    if not request.require_visual_blueprint:
        return
    cinematic_policy = getattr(request, "cinematic_direction_policy", "disabled")
    if [scene.id for scene in candidate.scenes] != [beat.id for beat in storyboard.beats]:
        raise ValueError("production_storyboard_scene_binding_conflict")
    if cinematic_policy in {"mixed_motion_v1", "editorial_motion_v2"}:
        if candidate.art_direction is None:
            raise ValueError("production_compiled_art_direction_missing")
        if candidate.art_direction != storyboard.art_direction:
            raise ValueError("production_compiled_art_direction_changed")
    all_media = [
        element
        for candidate_scene in candidate.scenes
        for element in candidate_scene.elements
        if element.kind in {"image", "video"}
    ]
    if getattr(request, "mode", None) == "mixed_montage" and not all_media:
        raise ValueError("production_mixed_montage_media_missing")
    if (
        getattr(request, "mode", None) == "mixed_montage"
        and getattr(request, "demonstration_policy", "disabled") == "required"
        and getattr(request, "material_semantics_policy", "legacy") == "contextual_video_v1"
        and not any(
            need.source_class == "licensed_stock"
            and need.kind == "video"
            and not need.alpha_required
            and bool(need.visual_description.strip() or need.query.strip())
            for scene in candidate.scenes
            for need in scene.material_needs
        )
    ):
        raise ValueError("production_mixed_montage_contextual_media_missing")
    for scene, beat in zip(candidate.scenes, storyboard.beats, strict=True):
        blueprint = beat.visual_blueprint
        if blueprint is None:
            raise ValueError("production_visual_blueprint_required")
        if cinematic_policy == "mixed_motion_v1":
            if not scene.shot_plan:
                raise ValueError("production_compiled_shot_plan_missing:" + scene.id)
            blueprint_shots = {shot.id: shot for shot in blueprint.shot_sequence}
            if set(blueprint_shots) != {shot.id for shot in scene.shot_plan}:
                raise ValueError("production_compiled_shot_binding_conflict:" + scene.id)
            for shot in scene.shot_plan:
                authored = blueprint_shots[shot.id]
                for field in (
                    "function",
                    "subject",
                    "observable_action",
                    "shot_scale",
                    "angle",
                    "lighting",
                    "material_requirement_ids",
                    "execution_component_ids",
                ):
                    if getattr(shot, field) != getattr(authored, field):
                        raise ValueError("production_compiled_shot_changed:" + scene.id + ":" + shot.id)
                if not shot.target_element_ids:
                    raise ValueError("production_compiled_shot_target_missing:" + scene.id + ":" + shot.id)
                indexed = {element.id: element for element in scene.elements}
                targets = [indexed.get(identity) for identity in shot.target_element_ids]
                if any(target is None for target in targets):
                    raise ValueError("production_compiled_shot_target_unknown:" + scene.id + ":" + shot.id)
                if not any(target.visual_role != "background" for target in targets):
                    raise ValueError("production_compiled_shot_interval_not_executed:" + scene.id + ":" + shot.id)
                if any(
                    target.start_frame > shot.start_frame
                    or target.start_frame + target.duration_frames < shot.end_frame_exclusive
                    for target in targets
                ):
                    raise ValueError("production_compiled_shot_target_not_visible:" + scene.id + ":" + shot.id)
                bound = {
                    need.blueprint_requirement_id
                    for need in scene.material_needs
                    if need.target_id in shot.target_element_ids
                }
                composable = {
                    item.id for item in blueprint.demonstration.indispensable_materials
                    if item.requirement_class == "composable"
                } if blueprint.demonstration else set()
                if not (set(shot.material_requirement_ids) - composable) <= bound:
                    raise ValueError("production_compiled_shot_material_unbound:" + scene.id + ":" + shot.id)
                available_components = set(scene.technique_ids) | {
                    composition.family
                    for composition in scene.compositions
                    if set(composition.target_ids) & set(shot.target_element_ids)
                }
                if not set(shot.execution_component_ids) <= available_components:
                    raise ValueError("production_compiled_shot_component_unbound:" + scene.id + ":" + shot.id)
        media = [element for element in scene.elements if element.kind in {"image", "video"}]
        if blueprint.representation == "footage" and not any(element.kind == "video" for element in media):
            raise ValueError("production_blueprint_footage_missing:" + scene.id)
        demonstration = getattr(blueprint, "demonstration", None)
        procedural_hero = any(
            element.kind in {"shape", "path"} and element.visual_role == "hero"
            for element in scene.elements
        )
        explicit_procedural = bool(
            demonstration
            and demonstration.procedural_sufficiency_reason
            and any(item.procedural_allowed for item in demonstration.indispensable_materials)
        )
        procedural_cutout = procedural_hero and (
            getattr(request, "demonstration_policy", "disabled") == "disabled"
            or explicit_procedural
        )
        if blueprint.representation == "cutout" and not media and not procedural_cutout:
            raise ValueError("production_blueprint_media_missing:" + scene.id)
        if (
            blueprint.representation == "mixed"
            and not media
            and blueprint.primary_material_query.split("/", 1)[0].casefold()
            in {"footage", "image", "video", "photo", "cutout"}
        ):
            raise ValueError("production_blueprint_media_missing:" + scene.id)
        for element in media:
            if not element.asset_id and not any(
                need.target_id == element.id and need.field == "asset"
                for need in scene.material_needs
            ):
                raise ValueError("production_blueprint_material_request_missing:" + scene.id + ":" + element.id)
