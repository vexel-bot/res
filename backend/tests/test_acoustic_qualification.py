from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.config import Settings
from app.domain.studios.acoustic_qualification import (
    AcousticAggregateMetricsV1,
    AcousticCasePredictionV1,
    AcousticCorpusCaseV1,
    AcousticCorpusManifestV1,
    AcousticMetricLimitsV1,
    AcousticQualificationPolicyV1,
    AcousticQualificationRunV1,
    contract_digest,
    evaluate_acoustic_qualification,
    recompute_metrics,
    sign_acoustic_promotion_receipt,
    verify_acoustic_promotion_receipt,
)

NOW = datetime(2026, 8, 31, 18, 0, tzinfo=UTC)
SECRET = "qualification-test-secret-with-more-than-32-characters"
ENVIRONMENTS = ("natural_only", "speech", "music", "speech_music", "silence")
ROOT = Path(__file__).resolve().parents[2]


def qualification_fixture(tmp_path):
    policy = AcousticQualificationPolicyV1(
        suite_id="acoustic-presence-ptbr-v1",
        policy_version="1.0.0",
        status="approved",
        approved_at=NOW,
        approved_by="quality-owner",
        minimum_case_count=20,
        minimum_cases_per_environment=4,
        minimum_positive_cases_per_target=8,
        minimum_negative_cases_per_target=8,
        required_environments=list(ENVIRONMENTS),
        required_locales=["pt-BR"],
        limits=AcousticMetricLimitsV1(
            speech_false_negative_rate_max=0.05,
            speech_false_positive_rate_max=0.05,
            music_false_negative_rate_max=0.05,
            music_false_positive_rate_max=0.05,
            inconclusive_rate_max=0.02,
        ),
        rationale=["Product risk policy fixture; not a real detector qualification."],
    )
    cases = []
    for environment in ENVIRONMENTS:
        for index in range(4):
            case_id = f"{environment}-{index}"
            payload = f"authorized-fixture:{case_id}".encode()
            relative_path = f"{environment}/{index}.wav"
            target = tmp_path / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
            rights_payload = f"rights:{case_id}".encode()
            rights_relative_path = f"rights/{environment}-{index}.json"
            rights_target = tmp_path / rights_relative_path
            rights_target.parent.mkdir(parents=True, exist_ok=True)
            rights_target.write_bytes(rights_payload)
            cases.append(
                AcousticCorpusCaseV1(
                    case_id=case_id,
                    relative_asset_path=relative_path,
                    asset_id=f"asset-{case_id}",
                    asset_checksum_sha256=hashlib.sha256(payload).hexdigest(),
                    rights_evidence_relative_path=rights_relative_path,
                    rights_evidence_digest_sha256=hashlib.sha256(rights_payload).hexdigest(),
                    rights_status="verified",
                    environment=environment,
                    speech_present=environment in {"speech", "speech_music"},
                    music_present=environment in {"music", "speech_music"},
                    duration_seconds=1,
                    locale="pt-BR",
                )
            )
    corpus = AcousticCorpusManifestV1(
        corpus_id="authorized-acoustic-fixture-v1",
        suite_id=policy.suite_id,
        policy_digest_sha256=contract_digest(policy),
        created_at=NOW,
        cases=cases,
    )
    predictions = [
        AcousticCasePredictionV1(
            case_id=case.case_id,
            input_checksum_sha256=case.asset_checksum_sha256,
            speech_present=case.speech_present,
            music_present=case.music_present,
            status="succeeded",
            evidence_digest_sha256=hashlib.sha256(f"evidence:{case.case_id}".encode()).hexdigest(),
            runtime_milliseconds=10,
        )
        for case in cases
    ]
    placeholder = AcousticAggregateMetricsV1(
        case_count=20,
        succeeded_count=20,
        inconclusive_count=0,
        failed_count=0,
        speech={"truePositive": 8, "trueNegative": 12, "falsePositive": 0, "falseNegative": 0},
        music={"truePositive": 8, "trueNegative": 12, "falsePositive": 0, "falseNegative": 0},
        speech_false_negative_rate=0,
        speech_false_positive_rate=0,
        music_false_negative_rate=0,
        music_false_positive_rate=0,
        inconclusive_rate=0,
    )
    run = AcousticQualificationRunV1(
        run_id="acoustic-fixture-run",
        suite_id=policy.suite_id,
        provider="fixture.acoustic",
        provider_version="1.0.0",
        model_name="fixture-model",
        model_version="1.0.0",
        model_digest_sha256="a" * 64,
        policy_digest_sha256=contract_digest(policy),
        corpus_manifest_digest_sha256=contract_digest(corpus),
        worker_manifest_digest_sha256="b" * 64,
        license_review_digest_sha256="c" * 64,
        conversion_provenance_digest_sha256="d" * 64,
        evaluator_digest_sha256="e" * 64,
        worker_advertised=True,
        no_egress=True,
        isolated_tenant=True,
        ephemeral_workspace=True,
        started_at=NOW,
        completed_at=NOW,
        predictions=predictions,
        reported_metrics=placeholder,
    )
    return policy, corpus, run.model_copy(update={"reported_metrics": recompute_metrics(corpus, run)})


def test_qualification_recomputes_metrics_and_signs_only_passed_evidence(tmp_path):
    policy, corpus, run = qualification_fixture(tmp_path)

    assessment = evaluate_acoustic_qualification(policy, corpus, run, asset_root=tmp_path, evaluated_at=NOW)
    assert assessment.decision == "passed"
    assert assessment.recomputed_metrics.speech.false_negative == 0
    receipt = sign_acoustic_promotion_receipt(assessment, secret=SECRET, signer_key_id="acoustic-key-2026-08")
    assert verify_acoustic_promotion_receipt(receipt, secret=SECRET)
    tampered = receipt.model_copy(
        update={"assessment": receipt.assessment.model_copy(update={"model_version": "tampered"})}
    )
    assert not verify_acoustic_promotion_receipt(tampered, secret=SECRET)


def test_qualification_blocks_metric_and_asset_tampering(tmp_path):
    policy, corpus, run = qualification_fixture(tmp_path)
    tampered_metrics = run.reported_metrics.model_copy(update={"speech_false_negative_rate": 0.01})
    metric_result = evaluate_acoustic_qualification(
        policy,
        corpus,
        run.model_copy(update={"reported_metrics": tampered_metrics}),
        asset_root=tmp_path,
        evaluated_at=NOW,
    )
    assert metric_result.decision == "failed"
    assert "reported_metrics_mismatch" in metric_result.blocking_reasons

    (tmp_path / corpus.cases[0].relative_asset_path).write_bytes(b"changed")
    asset_result = evaluate_acoustic_qualification(policy, corpus, run, asset_root=tmp_path, evaluated_at=NOW)
    assert asset_result.decision == "failed"
    assert f"asset_checksum_mismatch:{corpus.cases[0].case_id}" in asset_result.blocking_reasons


def test_qualification_is_incomplete_without_policy_coverage_and_rights(tmp_path):
    policy, corpus, run = qualification_fixture(tmp_path)
    draft_policy = policy.model_copy(update={"status": "draft"})
    reduced = corpus.model_copy(
        update={
            "policy_digest_sha256": contract_digest(draft_policy),
            "cases": [
                case.model_copy(update={"rights_status": "unknown"})
                for case in corpus.cases
                if case.environment != "silence"
            ],
        }
    )
    reduced_run = run.model_copy(
        update={
            "policy_digest_sha256": contract_digest(draft_policy),
            "corpus_manifest_digest_sha256": contract_digest(reduced),
            "predictions": [
                prediction
                for prediction in run.predictions
                if prediction.case_id in {case.case_id for case in reduced.cases}
            ],
        }
    )
    reduced_run = reduced_run.model_copy(update={"reported_metrics": recompute_metrics(reduced, reduced_run)})
    result = evaluate_acoustic_qualification(draft_policy, reduced, reduced_run, asset_root=tmp_path, evaluated_at=NOW)
    assert result.decision == "incomplete"
    assert "policy_status:draft" in result.incomplete_reasons
    assert "environment_coverage_below_minimum:silence" in result.incomplete_reasons
    assert any(reason.startswith("rights_not_verified:") for reason in result.incomplete_reasons)


def test_corpus_rejects_parent_directory_paths():
    with pytest.raises(ValueError, match="relative_asset_path"):
        AcousticCorpusCaseV1(
            case_id="escape",
            relative_asset_path="../secret.wav",
            asset_id="asset-escape",
            asset_checksum_sha256="a" * 64,
            rights_evidence_relative_path="rights/escape.json",
            rights_evidence_digest_sha256="b" * 64,
            rights_status="verified",
            environment="silence",
            speech_present=False,
            music_present=False,
            duration_seconds=1,
            locale="pt-BR",
        )


def test_promotion_configuration_requires_secret_and_key_id_together():
    with pytest.raises(RuntimeError, match="must be configured together"):
        Settings(studio_acoustic_promotion_hmac_secret=SECRET).validate_for_startup()
    Settings(
        studio_acoustic_promotion_hmac_secret=SECRET,
        studio_acoustic_promotion_key_id="acoustic-key-2026-08",
    ).validate_for_startup()


def test_qualification_cli_issues_receipt_without_mutating_registry(tmp_path):
    policy, corpus, run = qualification_fixture(tmp_path)
    policy_path = tmp_path / "policy.json"
    corpus_path = tmp_path / "corpus.json"
    run_path = tmp_path / "run.json"
    receipt_path = tmp_path / "receipt.json"
    policy_path.write_text(policy.model_dump_json(by_alias=True), encoding="utf-8")
    corpus_path.write_text(corpus.model_dump_json(by_alias=True), encoding="utf-8")
    run_path.write_text(run.model_dump_json(by_alias=True), encoding="utf-8")
    environment = os.environ.copy()
    environment["STUDIO_ACOUSTIC_PROMOTION_HMAC_SECRET"] = SECRET
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "backend/scripts/evaluate_acoustic_qualification.py"),
            "--backend",
            str(ROOT / "backend"),
            "--policy",
            str(policy_path),
            "--corpus",
            str(corpus_path),
            "--run",
            str(run_path),
            "--asset-root",
            str(tmp_path),
            "--evaluated-at",
            "2026-08-31T18:00:00Z",
            "--signer-key-id",
            "acoustic-key-2026-08",
            "--receipt-output",
            str(receipt_path),
        ],
        capture_output=True,
        text=True,
        check=False,
        env=environment,
    )
    assert completed.returncode == 0, completed.stderr
    assert '"decision": "passed"' in completed.stdout
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["signerKeyId"] == "acoustic-key-2026-08"
    assert SECRET not in receipt_path.read_text(encoding="utf-8")


def test_repository_policy_is_valid_and_deliberately_not_approved():
    policy = AcousticQualificationPolicyV1.model_validate_json(
        (ROOT / "benchmarks/studios/acoustic/acoustic-presence-ptbr-policy.v1.json").read_text(encoding="utf-8")
    )
    assert policy.status == "draft"
    assert policy.required_locales == ["pt-BR"]
    assert policy.minimum_case_count == 200
