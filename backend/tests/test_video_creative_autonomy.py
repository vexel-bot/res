from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.domain.studios.creative_autonomy import (
    AnimaticPlanV1,
    CreativeAutonomyCaseV1,
    CreativePilotCasebookV1,
    CreativeScriptV1,
    ExecutableStoryboardV1,
    FormatRouterV1,
    LearningRecordV1,
    SoundDesignPlanV1,
    VisualDirectionV1,
    animatic_plan_digest,
    audit_creative_casebook,
    creative_casebook_digest,
    creative_script_digest,
    evaluate_preproduction_gate,
    executable_storyboard_digest,
    format_router_digest,
    sound_design_plan_digest,
    visual_direction_digest,
)

CASEBOOK_PATH = (
    Path(__file__).resolve().parents[2]
    / "benchmarks"
    / "studios"
    / "creative"
    / "video-creative-pilot-casebook.v1.json"
)
EXPECTED_DIGEST = "0c0f33b331eb8e389a7a0b1f8d60cb746569ee9568e3f6e0d38001caeb5638b5"


def casebook() -> CreativePilotCasebookV1:
    return CreativePilotCasebookV1.model_validate_json(CASEBOOK_PATH.read_text(encoding="utf-8"))


def test_fixed_casebook_has_three_cases_per_family_and_four_goldens() -> None:
    corpus = casebook()

    assert len(corpus.cases) == 12
    assert sum(item.golden for item in corpus.cases) == 4
    assert {family: sum(item.family == family for item in corpus.cases) for family in {
        "presenter_ugc",
        "split_screen_proof",
        "motion_visual_essay",
        "cinematic_hybrid",
    }} == {
        "presenter_ugc": 3,
        "split_screen_proof": 3,
        "motion_visual_essay": 3,
        "cinematic_hybrid": 3,
    }
    assert creative_casebook_digest(corpus) == EXPECTED_DIGEST


def test_saved_reels_are_structural_references_only() -> None:
    corpus = casebook()
    referenced = {
        item.case_id: item.structural_reference_urls for item in corpus.cases if item.structural_reference_urls
    }

    assert referenced == {
        "pilot-f2-depth-layer-explainer": [
            "https://www.instagram.com/reel/DcuHK9ChRrP/"
        ],
        "pilot-f3-distribution-network": [
            "https://www.instagram.com/reel/DciIBRYBHBK/"
        ],
    }
    for item in corpus.cases:
        for evidence in item.evidence:
            if evidence.kind == "creative_reference":
                assert "Copiar identidade" in evidence.prohibited_claims[0]


def test_casebook_audit_is_eligible_without_authorizing_execution() -> None:
    corpus = casebook()
    audit = audit_creative_casebook(corpus, audited_at=datetime(2026, 9, 1, tzinfo=UTC))

    assert audit.eligible is True
    assert audit.blockers == []
    assert all(item.identity_inference_authorized is False for item in corpus.cases)
    assert all(item.publication_authorized is False for item in corpus.cases)
    assert all(item.sound_design.voice_inference_authorized is False for item in corpus.cases)


def test_script_rejects_gap_or_overlap_between_beats() -> None:
    payload = casebook().cases[0].script.model_dump(mode="json", by_alias=True)
    payload["beats"][1]["startMilliseconds"] += 1

    with pytest.raises(ValidationError, match="contiguous timeline"):
        CreativeScriptV1.model_validate(payload)


def test_case_rejects_tampered_message_binding() -> None:
    payload = casebook().cases[0].model_dump(mode="json", by_alias=True)
    payload["script"]["messageDigestSha256"] = "f" * 64

    with pytest.raises(ValidationError, match="message digest"):
        CreativeAutonomyCaseV1.model_validate(payload)


def test_case_rejects_modality_not_supported_by_recipe() -> None:
    payload = casebook().cases[0].model_dump(mode="json", by_alias=True)
    payload["script"]["beats"][0]["modalities"] = ["avatar"]
    changed_script = CreativeScriptV1.model_validate(payload["script"])
    changed_digest = creative_script_digest(changed_script)
    payload["visualDirection"]["scriptDigestSha256"] = changed_digest
    payload["soundDesign"]["scriptDigestSha256"] = changed_digest
    payload["formatRoute"]["scriptDigestSha256"] = changed_digest
    direction = VisualDirectionV1.model_validate(payload["visualDirection"])
    sound = SoundDesignPlanV1.model_validate(payload["soundDesign"])
    route = FormatRouterV1.model_validate(payload["formatRoute"])
    payload["storyboard"]["scriptDigestSha256"] = changed_digest
    payload["storyboard"]["directionDigestSha256"] = visual_direction_digest(direction)
    payload["storyboard"]["soundPlanDigestSha256"] = sound_design_plan_digest(sound)
    payload["storyboard"]["routeDigestSha256"] = format_router_digest(route)
    storyboard = ExecutableStoryboardV1.model_validate(payload["storyboard"])
    payload["animatic"]["storyboardDigestSha256"] = executable_storyboard_digest(storyboard)

    with pytest.raises(ValidationError, match="unsupported by recipe"):
        CreativeAutonomyCaseV1.model_validate(payload)


def test_every_case_has_executable_preproduction_but_expensive_render_is_closed() -> None:
    corpus = casebook()
    evaluated_at = datetime(2026, 9, 1, tzinfo=UTC)

    for item in corpus.cases:
        assert item.storyboard.status == "ready_for_review"
        assert item.animatic.status == "rendered"
        assert item.animatic.render_asset_path
        assert item.animatic.render_digest_sha256
        assert len(item.storyboard.shots) == len(item.script.beats)
        assert item.recipe.reduced_motion_supported is True
        assert any(fallback.trigger == "reduced_motion" for fallback in item.recipe.fallbacks)
        gate = evaluate_preproduction_gate(item, evaluated_at=evaluated_at)
        assert gate.placeholder_render_eligible is True
        assert gate.expensive_render_eligible is False
        assert "animatic_human_approval_required" in gate.blockers
        assert "storyboard_asset_rights_pending" in gate.blockers


def test_animatic_digest_changes_when_timing_is_tampered() -> None:
    item = casebook().cases[0]
    payload = item.animatic.model_dump(mode="json", by_alias=True)
    original_digest = animatic_plan_digest(item.animatic)
    payload["shots"][0]["durationMilliseconds"] -= 1
    payload["shots"][1]["startMilliseconds"] -= 1
    payload["shots"][1]["durationMilliseconds"] += 1
    changed = AnimaticPlanV1.model_validate(payload)

    assert animatic_plan_digest(changed) != original_digest


def test_natural_foley_mode_rejects_speech_or_music() -> None:
    payload = deepcopy(casebook().cases[0].sound_design.model_dump(mode="json", by_alias=True))
    payload["cues"][0]["role"] = "narration"

    with pytest.raises(ValidationError, match="prohibits speech and music"):
        SoundDesignPlanV1.model_validate(payload)


def test_bound_sound_asset_requires_verified_rights() -> None:
    payload = deepcopy(casebook().cases[0].sound_design.model_dump(mode="json", by_alias=True))
    payload["cues"][0]["assetId"] = "sound-1"

    with pytest.raises(ValidationError, match="verified rights"):
        SoundDesignPlanV1.model_validate(payload)


def test_measured_learning_requires_render_metrics_and_human_review() -> None:
    payload = casebook().cases[0].learning.model_dump(mode="json", by_alias=True)
    payload["status"] = "measured"

    with pytest.raises(ValidationError, match="render, timestamp, and human review"):
        LearningRecordV1.model_validate(payload)


def test_casebook_rejects_family_imbalance() -> None:
    payload = casebook().model_dump(mode="json", by_alias=True)
    payload["cases"][0] = deepcopy(payload["cases"][3])
    payload["cases"][0]["caseId"] = "replacement-case"
    payload["cases"][0]["learning"]["caseId"] = "replacement-case"

    with pytest.raises(ValidationError, match="three cases per family"):
        CreativePilotCasebookV1.model_validate(payload)
