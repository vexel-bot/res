from __future__ import annotations

from pathlib import Path

import pytest

from app.domain.studios.factory_pre_review import (
    FactoryMachinePreReviewSuiteV1,
    assert_machine_pre_review_allows_human_quality_review,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PRE_REVIEW_PATH = (
    REPOSITORY_ROOT
    / "artifacts"
    / "validation"
    / "video-creative-pilot"
    / "factory-20260901-v1"
    / "machine-pre-review.json"
)


def pre_review() -> FactoryMachinePreReviewSuiteV1:
    return FactoryMachinePreReviewSuiteV1.model_validate_json(
        PRE_REVIEW_PATH.read_text(encoding="utf-8")
    )


def test_placeholder_pilots_are_only_eligible_for_storyboard_review() -> None:
    suite = pre_review()

    assert len(suite.reviews) == 12
    assert suite.ready_for_final_human_review_count == 0
    assert suite.storyboard_review_only_count == 12
    assert suite.promotion_eligible is False
    assert all(item.verdict == "storyboard_review_only" for item in suite.reviews)
    assert all(item.final_edit_claimed is False for item in suite.reviews)
    assert all(item.human_review_replaced is False for item in suite.reviews)
    assert all(
        "final_audiovisual_quality" not in item.reviewable_dimensions
        for item in suite.reviews
    )


def test_machine_pre_review_keeps_artifact_and_source_lineage() -> None:
    suite = pre_review()

    assert all(len(item.artifact_digest_sha256) == 64 for item in suite.reviews)
    assert all(len(item.source_animatic_digest_sha256) == 64 for item in suite.reviews)
    assert len({item.job_id for item in suite.reviews}) == 12
    assert len({item.case_id for item in suite.reviews}) == 12


def test_placeholder_pre_review_blocks_final_review_import() -> None:
    with pytest.raises(ValueError, match="machine_pre_review_blocks_final_human_review"):
        assert_machine_pre_review_allows_human_quality_review(pre_review())
