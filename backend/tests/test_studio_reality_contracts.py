import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.domain.studios.benchmarking import BenchmarkPolicyV1, benchmark_policy_digest
from app.domain.studios.execution import execution_profile
from app.domain.studios.reality import (
    PhysicalPlausibilityEvaluationV1,
    PhysicalPlausibilityPolicyV1,
    RealityAnalysisRequestV1,
    RealityModelV1,
    ShotRealityConstraintSetV1,
    physical_plausibility_evaluation_digest,
    physical_plausibility_policy_digest,
    reality_model_digest,
    shot_reality_constraint_set_digest,
    validate_physical_evaluation_bindings,
    validate_reality_model_bindings,
)

ROOT = Path(__file__).resolve().parents[2]
REALITY_DIR = ROOT / "benchmarks" / "studios" / "reality"
FIXTURE_DIR = REALITY_DIR / "fixtures"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_reality_model() -> RealityModelV1:
    return RealityModelV1.model_validate_json(
        (FIXTURE_DIR / "reality-model-supported-cup.v1.json").read_text(encoding="utf-8")
    )


def load_constraints() -> ShotRealityConstraintSetV1:
    return ShotRealityConstraintSetV1.model_validate_json(
        (FIXTURE_DIR / "shot-reality-constraints-supported-cup.v1.json").read_text(
            encoding="utf-8"
        )
    )


def load_policy() -> PhysicalPlausibilityPolicyV1:
    return PhysicalPlausibilityPolicyV1.model_validate_json(
        (REALITY_DIR / "physical-plausibility-policy.v1.json").read_text(encoding="utf-8")
    )


def test_pgv0_fixtures_are_versioned_and_digest_bound():
    model = load_reality_model()
    constraints = load_constraints()
    policy = load_policy()
    clear = PhysicalPlausibilityEvaluationV1.model_validate_json(
        (FIXTURE_DIR / "physical-evaluation-clear.v1.json").read_text(encoding="utf-8")
    )
    abstained = PhysicalPlausibilityEvaluationV1.model_validate_json(
        (FIXTURE_DIR / "physical-evaluation-abstained.v1.json").read_text(encoding="utf-8")
    )

    assert reality_model_digest(model) == "8a1753a13a43bd121ca2e97216068953165d40e8c8e69f4df092c586fc80efba"
    assert (
        shot_reality_constraint_set_digest(constraints)
        == "f0f4f3e083a36e33a75abd799a4bdec53bdebdc793ef585244450ca72b8cbec1"
    )
    assert (
        physical_plausibility_policy_digest(policy)
        == "8f4ff3bb19caf1c50dd6a6cd627ad6cd8b58f20bd6340f2efdd9abf01712aad0"
    )
    assert clear.reality_model_digest_sha256 == reality_model_digest(model)
    assert clear.constraint_set_digest_sha256 == shot_reality_constraint_set_digest(constraints)
    assert clear.policy_digest_sha256 == physical_plausibility_policy_digest(policy)
    assert clear.status == "advisory_clear"
    assert abstained.status == "advisory_uncertain"
    assert physical_plausibility_evaluation_digest(clear) != physical_plausibility_evaluation_digest(
        abstained
    )


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda payload: payload["relations"][0].update({"targetEntityId": "missing-object"}),
            "relation entity references unknown ids",
        ),
        (
            lambda payload: payload["tracks"][1]["samples"].append(
                {
                    "frameIndex": 90,
                    "centroid": {"x": 0.5, "y": 0.5},
                    "visibility": "visible",
                    "confidence": 0.9,
                    "evidenceIds": [],
                }
            ),
            "Reality track samples must stay inside their track range",
        ),
        (
            lambda payload: payload["evidence"][0].update(
                {"contributionId": "unknown-contribution"}
            ),
            "Reality evidence references unknown lineage contribution",
        ),
    ],
)
def test_reality_model_rejects_broken_graph_references(mutation, message):
    payload = load_json(FIXTURE_DIR / "reality-model-supported-cup.v1.json")
    mutation(payload)

    with pytest.raises(ValidationError, match=message):
        RealityModelV1.model_validate(payload)


def test_reality_analysis_requires_checksum_timebase_and_non_overlapping_shots():
    model = load_reality_model()
    payload = {
        "analysisId": model.analysis_id,
        "workspaceId": model.workspace_id,
        "sourceAsset": model.source_asset.model_dump(mode="json", by_alias=True),
        "sourceTimeMapId": model.source_time_map_id,
        "sourceTimeMapDigestSha256": model.source_time_map_digest_sha256,
        "frameRate": model.frame_rate.model_dump(mode="json", by_alias=True),
        "totalFrames": 90,
        "shots": [
            {
                "shotId": "shot-a",
                "frameRange": {"startFrame": 0, "endFrameExclusive": 60},
                "transitionIn": "start",
            },
            {
                "shotId": "shot-b",
                "frameRange": {"startFrame": 59, "endFrameExclusive": 90},
                "transitionOut": "end",
            },
        ],
        "analysisPolicyDigestSha256": "9" * 64,
    }

    with pytest.raises(ValidationError, match="Reality shots cannot overlap"):
        RealityAnalysisRequestV1.model_validate(payload)

    payload["shots"][1]["frameRange"]["startFrame"] = 60
    payload["sourceAsset"]["checksum"] = None
    with pytest.raises(ValidationError, match="source asset SHA-256"):
        RealityAnalysisRequestV1.model_validate(payload)


def test_reality_model_and_physical_qc_bind_to_exact_inputs():
    model = load_reality_model()
    constraints = load_constraints()
    request = RealityAnalysisRequestV1(
        analysis_id=model.analysis_id,
        workspace_id=model.workspace_id,
        source_asset=model.source_asset,
        source_time_map_id=model.source_time_map_id,
        source_time_map_digest_sha256=model.source_time_map_digest_sha256,
        frame_rate=model.frame_rate,
        total_frames=model.total_frames,
        shots=model.shots,
        analysis_policy_digest_sha256=model.analysis_policy_digest_sha256,
    )
    evaluation = PhysicalPlausibilityEvaluationV1.model_validate_json(
        (FIXTURE_DIR / "physical-evaluation-clear.v1.json").read_text(encoding="utf-8")
    )

    assert validate_reality_model_bindings(model, request) is model
    assert validate_physical_evaluation_bindings(evaluation, model, constraints) is evaluation

    bad_request = request.model_copy(update={"source_time_map_digest_sha256": "0" * 64})
    with pytest.raises(ValueError, match="source time-map digest"):
        validate_reality_model_bindings(model, bad_request)

    bad_evaluation = evaluation.model_copy(update={"reality_model_digest_sha256": "0" * 64})
    with pytest.raises(ValueError, match="reality model digest binding mismatch"):
        validate_physical_evaluation_bindings(bad_evaluation, model, constraints)

    payload = load_json(FIXTURE_DIR / "physical-evaluation-clear.v1.json")
    payload["checks"][0]["evidenceIds"] = ["unknown-evidence"]
    unknown_evidence = PhysicalPlausibilityEvaluationV1.model_validate(payload)
    with pytest.raises(ValueError, match="check evidence references unknown ids"):
        validate_physical_evaluation_bindings(unknown_evidence, model, constraints)

def test_shot_constraints_make_creative_exceptions_explicit():
    payload = load_json(FIXTURE_DIR / "shot-reality-constraints-supported-cup.v1.json")
    payload["constraints"][0]["declaredTechniques"] = ["none", "slow_motion"]
    with pytest.raises(ValidationError, match="cannot be combined"):
        ShotRealityConstraintSetV1.model_validate(payload)

    payload = load_json(FIXTURE_DIR / "shot-reality-constraints-supported-cup.v1.json")
    payload["constraints"][0].update(
        {"realityMode": "surreal", "enforcedPrinciples": [], "declaredTechniques": ["vfx"]}
    )
    with pytest.raises(ValidationError, match="surreal shots must declare"):
        ShotRealityConstraintSetV1.model_validate(payload)


def test_physical_qc_fails_closed_on_policy_or_status_tampering():
    payload = load_json(FIXTURE_DIR / "physical-evaluation-clear.v1.json")
    payload["policyDigestSha256"] = "0" * 64
    with pytest.raises(ValidationError, match="policy digest does not match"):
        PhysicalPlausibilityEvaluationV1.model_validate(payload)

    payload = load_json(FIXTURE_DIR / "physical-evaluation-clear.v1.json")
    payload["status"] = "advisory_issues"
    with pytest.raises(ValidationError, match="status must match"):
        PhysicalPlausibilityEvaluationV1.model_validate(payload)


def test_low_confidence_or_single_signal_cannot_be_promoted_to_issue():
    payload = load_json(FIXTURE_DIR / "physical-evaluation-clear.v1.json")
    check = payload["checks"][0]
    check.update(
        {
            "status": "issue",
            "severity": "warning",
            "confidence": 0.55,
            "suggestion": "Revisar manualmente.",
            "humanDecision": "pending",
        }
    )
    payload["status"] = "advisory_issues"
    with pytest.raises(ValidationError, match="must abstain"):
        PhysicalPlausibilityEvaluationV1.model_validate(payload)

    check["confidence"] = 0.85
    check["independentSignalGroups"] = ["tracking"]
    with pytest.raises(ValidationError, match="independent signal groups"):
        PhysicalPlausibilityEvaluationV1.model_validate(payload)


def test_pgv0_benchmark_policies_are_frozen_but_not_license_approved():
    expected = {
        "physical-violation-detection-policy.v1.json": (
            "clicko.physical-violation-detection.v1",
            "909f3b556f3928cb099760a0e088eaacb8603194a325ea58cda37613c08190b0",
        ),
        "reality-product-ugc-policy.v1.json": (
            "clicko.reality-product-ugc.v1",
            "753eabd940ca10e9d74edab2c52ffdf805f293cb114105fe29ffec533123b4f6",
        ),
        "reality-understanding-policy.v1.json": (
            "clicko.reality-understanding.v1",
            "16ae8a5985c19ba5a620bb6097baccdc0bb7329ead0cc9bcaec7b0b21a927301",
        ),
    }
    for filename, (suite_id, digest) in expected.items():
        policy = BenchmarkPolicyV1.model_validate_json(
            (REALITY_DIR / filename).read_text(encoding="utf-8")
        )
        assert policy.suite_id == suite_id
        assert policy.status == "frozen"
        assert benchmark_policy_digest(policy) == digest
        assert all(candidate.license_gate == "review_required" for candidate in policy.candidates)
        assert "no_automatic_correction" in policy.required_controls
        assert all(threshold.rationale for threshold in policy.thresholds)


def test_unresolved_model_artifact_cannot_be_promoted_by_flipping_license_gate():
    payload = load_json(REALITY_DIR / "reality-understanding-policy.v1.json")
    payload["candidates"][0]["licenseGate"] = "approved"
    with pytest.raises(ValidationError, match="resolved commercial components"):
        BenchmarkPolicyV1.model_validate(payload)


def test_reality_jobs_are_reserved_for_external_vision_workers():
    for job_type in ("reality_analysis", "video_physical_qc"):
        profile = execution_profile(job_type)
        assert profile.capability == "vision_gpu"
        assert profile.queue == "studio.gpu.vision"
        assert profile.resource_class == "gpu.vision"
