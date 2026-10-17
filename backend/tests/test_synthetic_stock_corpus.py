import sys
from pathlib import Path

from app.domain.studios.benchmarking import BenchmarkPolicyV1, benchmark_corpus_manifest_digest

SCRIPTS_ROOT = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_ROOT))

from generate_synthetic_stock_corpus import build_corpus  # noqa: E402


def test_synthetic_stock_corpus_is_deterministic_and_has_no_biometric_refs():
    policy = BenchmarkPolicyV1.model_validate_json(
        (
            Path(__file__).resolve().parents[2]
            / "benchmarks"
            / "studios"
            / "identity"
            / "voice-stock-pt-br-policy.v1.json"
        ).read_text(encoding="utf-8")
    )
    manifest, scriptbook = build_corpus(policy)
    repeat, repeat_scriptbook = build_corpus(policy)

    assert len(manifest.cases) == 64
    assert manifest == repeat
    assert scriptbook == repeat_scriptbook
    assert benchmark_corpus_manifest_digest(manifest) == scriptbook["corpusManifestDigestSha256"]
    assert {scenario for case in manifest.cases for scenario in case.scenarios} == set(
        policy.corpus.required_scenarios
    )
    assert all(case.synthetic for case in manifest.cases)
    assert all(
        case.pseudonymous_subject_id is None
        and case.reference_asset_id is None
        and case.consent_grant_id is None
        for case in manifest.cases
    )
