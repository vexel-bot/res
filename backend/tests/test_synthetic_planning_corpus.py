from __future__ import annotations

import sys
from collections import Counter
from copy import deepcopy
from pathlib import Path

import pytest

from app.domain.studios.benchmarking import (
    BenchmarkCorpusManifestV1,
    BenchmarkPolicyV1,
    benchmark_corpus_manifest_digest,
    benchmark_policy_digest,
)
from app.domain.studios.intelligence import PlanningCopySyntheticCasebookV1

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = ROOT / "backend" / "scripts"
sys.path.insert(0, str(SCRIPTS_ROOT))

from generate_synthetic_planning_corpus import (  # noqa: E402
    ABSTENTION_SCENARIOS,
    STORYBOARD_MINIMUMS,
    build_corpus,
    main,
    validate_corpus_bindings,
)

POLICY_PATH = (
    ROOT
    / "benchmarks"
    / "studios"
    / "intelligence"
    / "planning-copy-pt-br-policy.v1.json"
)


def _policy() -> BenchmarkPolicyV1:
    return BenchmarkPolicyV1.model_validate_json(POLICY_PATH.read_text(encoding="utf-8"))


def test_synthetic_planning_corpus_is_deterministic_balanced_and_policy_bound() -> None:
    policy = _policy()
    manifest, casebook = build_corpus(policy)
    repeated_manifest, repeated_casebook = build_corpus(policy)

    assert policy.corpus.manifest_schema == manifest.schema_version
    assert benchmark_policy_digest(policy) == (
        "88a37ca064d36a8b0f3c58fe4751f0a721b008359a80fe62212c452b4b17bc54"
    )
    assert manifest == repeated_manifest
    assert casebook == repeated_casebook
    assert len(manifest.cases) == len(casebook.cases) == 60
    assert Counter(case.scenarios[0] for case in manifest.cases) == {
        scenario: 6 for scenario in policy.corpus.required_scenarios
    }
    assert manifest.policy_digest_sha256 == benchmark_policy_digest(policy)
    assert casebook.policy_digest_sha256 == manifest.policy_digest_sha256
    assert casebook.corpus_manifest_digest_sha256 == benchmark_corpus_manifest_digest(manifest)
    validate_corpus_bindings(manifest, casebook)


def test_synthetic_planning_cases_are_non_biometric_injection_aware_and_fail_closed() -> None:
    manifest, casebook = build_corpus(_policy())
    fixture_by_id = {item.case_id: item for item in casebook.cases}

    assert all(item.synthetic for item in manifest.cases)
    assert all(
        item.pseudonymous_subject_id is None
        and item.reference_asset_id is None
        and item.reference_checksum_sha256 is None
        and item.consent_grant_id is None
        and item.consent_evidence_digest_sha256 is None
        for item in manifest.cases
    )
    forbidden_markers: set[str] = set()
    for item in casebook.cases:
        request = item.request
        expected = item.expectation
        forbidden_markers.update(expected.forbidden_output_fragments)
        assert request.workspace_id == "synthetic-planning-benchmark"
        assert request.locale == "pt-BR"
        assert "não confiável" in request.product
        assert all(marker in request.product for marker in expected.forbidden_output_fragments)
        assert expected.preserve_channel is True
        assert expected.preserve_format is True
        assert expected.preserve_restrictions is True
        assert expected.preserve_evidence is True
        assert expected.unsupported_claims_require_human_review is True
        assert expected.required_evidence_ids == [evidence.id for evidence in request.evidence]
        assert all(
            evidence.source_url is not None
            and evidence.source_url.startswith("https://example.invalid/")
            for evidence in request.evidence
        )
        assert expected.required_abstention == (expected.scenario in ABSTENTION_SCENARIOS)
        assert expected.expected_result_status == (
            "partial" if expected.required_abstention else "complete"
        )
        assert expected.minimum_storyboard_beats == STORYBOARD_MINIMUMS.get(
            expected.scenario,
            0,
        )
    assert len(forbidden_markers) == 60
    assert set(fixture_by_id) == {item.case_id for item in manifest.cases}


def test_revision_cases_bind_feedback_and_locked_fields() -> None:
    _, casebook = build_corpus(_policy())
    revisions = [
        item
        for item in casebook.cases
        if item.expectation.scenario == "revision-from-human-feedback"
    ]

    assert len(revisions) == 6
    for item in revisions:
        revision = item.request.revision_context
        assert revision is not None
        assert revision.feedback == item.expectation.revision_feedback_items
        assert revision.locked_fields == ["channel", "format", "restrictions", "evidence"]


def test_corpus_binding_rejects_tampered_casebook() -> None:
    manifest, casebook = build_corpus(_policy())
    tampered = deepcopy(casebook)
    tampered.cases[0].request.objective = "Objetivo adulterado depois do congelamento"

    with pytest.raises(ValueError, match="fixture digest mismatch"):
        validate_corpus_bindings(manifest, tampered)


def test_planning_corpus_cli_writes_typed_artifacts(tmp_path: Path, monkeypatch) -> None:
    manifest_path = tmp_path / "planning-manifest.json"
    casebook_path = tmp_path / "planning-casebook.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "generate_synthetic_planning_corpus.py",
            str(POLICY_PATH),
            "--manifest",
            str(manifest_path),
            "--casebook",
            str(casebook_path),
        ],
    )

    assert main() == 0
    manifest = BenchmarkCorpusManifestV1.model_validate_json(
        manifest_path.read_text(encoding="utf-8")
    )
    casebook = PlanningCopySyntheticCasebookV1.model_validate_json(
        casebook_path.read_text(encoding="utf-8")
    )
    assert len(manifest.cases) == 60
    validate_corpus_bindings(manifest, casebook)
