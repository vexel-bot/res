from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.domain.studios.creative_intelligence import (
    AssetPlanV1,
    CharacterBibleV1,
    KnowledgeClaimV1,
    ProductionRunV1,
    R1AnalysisReviewV1,
    SceneBlueprintV1,
    evaluate_creative_research_gate,
)

NOW = datetime(2026, 9, 1, 20, 0, tzinfo=UTC)


def test_inference_is_explicit_and_prohibited_evidence_fails_closed() -> None:
    with pytest.raises(ValidationError, match="inference basis"):
        KnowledgeClaimV1.model_validate(
            {
                "claimId": "claim-1",
                "statement": "The cut intends to create anxiety.",
                "kind": "inference",
                "confidence": 0.62,
            }
        )

    with pytest.raises(ValidationError, match="Prohibited evidence"):
        KnowledgeClaimV1.model_validate(
            {
                "claimId": "claim-2",
                "statement": "A documented production fact.",
                "kind": "documented_statement",
                "confidence": 0.9,
                "evidence": [
                    {
                        "evidenceId": "evidence-1",
                        "sourceUrl": "https://example.invalid/source",
                        "sourceTitle": "Unavailable source",
                        "accessedAt": NOW.isoformat(),
                        "rightsStatus": "prohibited",
                    }
                ],
            }
        )


def test_real_person_and_real_scene_require_authorization() -> None:
    character = {
        "characterId": "character-1",
        "name": "Presenter",
        "identityKind": "authorized_real_person",
        "appearance": "Documented authorized appearance.",
        "personality": "Direct and calm.",
        "objective": "Explain the evidence.",
        "behavior": "Addresses camera and demonstrates the mechanism.",
        "voice": "Natural PT-BR voice.",
        "wardrobe": "Continuity-locked neutral wardrobe.",
        "continuityRules": ["wardrobe must not change inside the scene"],
    }
    with pytest.raises(ValidationError, match="consent grant"):
        CharacterBibleV1.model_validate(character)

    scene = {
        "sceneId": "scene-1",
        "route": "hybrid_extension",
        "worldBibleId": "world-1",
        "purpose": "Extend an authorized room.",
        "cameraReconstruction": "Calibrated camera and lens.",
        "depthAndGeometry": "Measured planes and occlusion boundaries.",
        "lighting": "Match key direction and color temperature.",
        "protectedRegions": ["presenter face"],
        "continuityChecks": ["parallax", "occlusion", "shadow direction"],
    }
    with pytest.raises(ValidationError, match="environment authorization"):
        SceneBlueprintV1.model_validate(scene)


def test_approved_asset_plan_requires_cleared_rights() -> None:
    with pytest.raises(ValidationError, match="cleared rights"):
        AssetPlanV1.model_validate(
            {
                "planId": "asset-plan-1",
                "humanApproved": True,
                "assets": [
                    {
                        "assetId": "asset-1",
                        "kind": "video",
                        "purpose": "Proof insert",
                        "origin": "Temporary research reference",
                        "rightsStatus": "review_required",
                        "estimatedCostMinor": 0,
                    }
                ],
            }
        )


def test_production_history_cannot_skip_gates_or_self_approve() -> None:
    with pytest.raises(ValidationError, match="cannot skip"):
        ProductionRunV1.model_validate(
            {
                "runId": "run-1",
                "currentState": "storyboard_approved",
                "history": [
                    {"state": "brief", "enteredAt": NOW.isoformat()},
                    {
                        "state": "storyboard_approved",
                        "enteredAt": NOW.isoformat(),
                        "approvalId": "approval-1",
                    },
                ],
                "estimatedCostMinor": 0,
                "actualCostMinor": 0,
            }
        )

    with pytest.raises(ValidationError, match="requires an approval id"):
        ProductionRunV1.model_validate(
            {
                "runId": "run-2",
                "currentState": "research_approved",
                "history": [
                    {"state": "brief", "enteredAt": NOW.isoformat()},
                    {"state": "research_approved", "enteredAt": NOW.isoformat()},
                ],
                "estimatedCostMinor": 0,
                "actualCostMinor": 0,
            }
        )


def test_r1_gate_stays_closed_until_all_human_reviews_and_taxonomy_approval() -> None:
    analyses = [
        R1AnalysisReviewV1(
            unit_id=f"unit-{index}",
            analysis_path=f"corpus/unit-{index}/analysis.md",
            shots_path=f"corpus/unit-{index}/shots.json",
            temporal_map_complete=True,
            provenance_complete=True,
            human_reviewed=False,
        )
        for index in range(12)
    ]
    gate = evaluate_creative_research_gate(
        pilot_id="r1-2026-09-01",
        analyses=analyses,
        taxonomy_report_path="taxonomy-correction-r1.md",
        taxonomy_human_approved=False,
        evaluated_at=NOW,
    )

    assert gate.corpus_expansion_eligible is False
    assert gate.expensive_generation_eligible is False
    assert "taxonomy_human_approval_required" in gate.blockers
    assert len([item for item in gate.blockers if item.startswith("human_review_required")]) == 12


def test_r1_approval_opens_corpus_only_not_generation() -> None:
    analyses = [
        R1AnalysisReviewV1(
            unit_id=f"unit-{index}",
            analysis_path=f"corpus/unit-{index}/analysis.md",
            shots_path=f"corpus/unit-{index}/shots.json",
            temporal_map_complete=True,
            provenance_complete=True,
            human_reviewed=True,
        )
        for index in range(12)
    ]
    gate = evaluate_creative_research_gate(
        pilot_id="r1-2026-09-01",
        analyses=analyses,
        taxonomy_report_path="taxonomy-correction-r1.md",
        taxonomy_human_approved=True,
        evaluated_at=NOW,
    )

    assert gate.corpus_expansion_eligible is True
    assert gate.expensive_generation_eligible is False
    assert gate.blockers == []
