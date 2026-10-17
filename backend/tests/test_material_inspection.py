from types import SimpleNamespace

import pytest

from app.domain.studios.material_inspection import (
    MaterialInspectionRequestV1,
    MaterialInspectionResultV1,
    inspect_verdict,
    material_inspection_criteria,
)


def request():
    return MaterialInspectionRequestV1(
        asset_id="asset",
        checksum="a" * 64,
        purpose="Show a conversation",
        criteria=["People visibly interacting"],
        required_seconds=4,
    )


def result(**changes):
    return MaterialInspectionResultV1.model_validate(
        {
            "description": "Two people face each other",
            "confidence": 0.95,
            "uncertainty": "Sparse samples only",
            "criteria": [
                {"index": 0, "result": "supported", "evidence": "People facing each other", "sampleIndices": [0]}
            ],
            **changes,
        }
    )


def test_acceptance_needs_complete_supported_evidence_and_enough_duration():
    assert inspect_verdict(result(), request(), [{}], 5) == "accepted"
    assert inspect_verdict(result(), request(), [{}], 2) == "requires_alternative"
    assert inspect_verdict(result(confidence=0.5), request(), [{}], 5) == "requires_alternative"
    uncertain = result()
    uncertain.criteria[0].result = "unknown"
    assert inspect_verdict(uncertain, request(), [{}], 5) == "requires_alternative"


def test_invented_sample_or_omitted_criterion_fails_closed():
    with pytest.raises(ValueError, match="sample_binding"):
        inspect_verdict(result(), request(), [], 5)
    wrong = result()
    wrong.criteria[0].index = 1
    with pytest.raises(ValueError, match="criteria_coverage"):
        inspect_verdict(wrong, request(), [{}], 5)


def test_processing_requirement_is_not_treated_as_completed_processing():
    candidate = result(
        processingRequirements=["chroma_key"],
        confidenceKind="uncalibrated_rule",
        confidence=None,
    )
    eligible = request().model_copy(update={"allowed_post_processing": ["chroma_key"]})

    assert inspect_verdict(candidate, eligible, [{}], 5) == "requires_processing"


def test_inspection_cannot_be_combined_with_generation():
    from app.domain.studios.editing_resources import EditingAIRequestV1

    with pytest.raises(ValueError, match="independent_planning_job"):
        EditingAIRequestV1(
            expected_document_revision=1, operation="generate_image", prompt="test", material_inspection=request()
        )


def test_inspection_always_requires_pixel_level_semantic_identity():
    need = SimpleNamespace(
        visual_description="uma caneta-tinteiro preta isolada",
        entity="",
        query="pen",
        acceptance_criteria=["o objeto aparece centralizado"],
    )

    criteria = material_inspection_criteria(need)

    assert "uma caneta-tinteiro preta isolada" in criteria[0]
    assert "pixels themselves" in criteria[0]
    assert "future overlay" in criteria[0]
    assert criteria[1] == "o objeto aparece centralizado"


def test_decomposed_visual_identity_does_not_add_a_redundant_veto_criterion():
    need = SimpleNamespace(
        visual_description="Pessoa claramente visível. Objeto claramente visível. Braços e mãos sem obstrução",
        entity="",
        query="person holding a tablet",
        acceptance_criteria=[
            "Pessoa claramente visível",
            "Objeto claramente visível",
            "Braços e mãos sem obstrução",
        ],
    )

    assert material_inspection_criteria(need) == need.acceptance_criteria
