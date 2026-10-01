from __future__ import annotations

import json
import sys
import wave
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.domain.studios.benchmarking import (
    BenchmarkEnvironmentV1,
    BenchmarkPolicyV1,
    SpeechBenchmarkCleanupBundleV1,
    SpeechBenchmarkCleanupCaseV1,
    evaluate_benchmark_run,
)
from app.domain.studios.contracts import SpeechProvenanceV1, SpeechSynthesisResultV1
from app.domain.studios.speech_review import (
    SpeechReviewPlanV1,
    SpeechReviewResponseV1,
    SpeechReviewSubmissionV1,
    speech_review_plan_digest,
)
from app.services.object_storage import sha256_file
from app.services.studios.speech_benchmark import append_cleanup_evidence, run_stock_voice_benchmark
from app.services.studios.speech_benchmark_storage import PrivateSpeechBenchmarkEvidenceSink
from app.services.studios.speech_review import (
    append_blinded_review_evidence,
    build_blinded_review_plan,
)

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_ROOT))

import finalize_speech_benchmark_cleanup  # noqa: E402
import ingest_speech_review  # noqa: E402
import prepare_speech_review  # noqa: E402
from generate_synthetic_stock_corpus import build_corpus  # noqa: E402


class ReviewFixtureProvider:
    name = "kokoro-82m-stock"
    version = "review-fixture-1"

    def synthesize(self, request, destination, progress, is_cancelled):
        with wave.open(str(destination), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(request.sample_rate)
            output.writeframes(b"\x00\x00" * (request.sample_rate // 10))
        return SpeechSynthesisResultV1(
            provider=self.name,
            provider_version=self.version,
            audio_format="wav",
            sample_rate=request.sample_rate,
            duration_ms=100,
            artifact_checksum_sha256=sha256_file(destination),
            provenance=SpeechProvenanceV1(
                source_revision="review-fixture-revision",
                model_digest_sha256="1" * 64,
                worker_manifest_digest_sha256="2" * 64,
                worker_image_digest=f"sha256:{'3' * 64}",
                provenance_mode="fixture",
            ),
            metrics={"directCostUsd": 0.00001},
        )


class ReviewFixtureSink:
    def persist_output(self, case_id, source, metadata):
        return f"audio-{case_id}"

    def persist_provenance(self, case_id, payload):
        return f"provenance-{case_id}"

    def delete(self, asset_id):
        return True


def _inputs(*, evidence_sink=None, run_id="speech-review-run-001"):
    policy = BenchmarkPolicyV1.model_validate_json(
        (ROOT / "benchmarks/studios/identity/voice-stock-pt-br-policy.v1.json").read_text(
            encoding="utf-8"
        )
    )
    corpus, scriptbook = build_corpus(policy)
    component_digests = {
        component.component_id: f"{index:x}" * 64
        for index, component in enumerate(policy.candidates[0].components, start=6)
        if component.required
    }
    selected_sink = evidence_sink or ReviewFixtureSink()
    bundle_asset_id = (
        selected_sink.evidence_bundle_asset_id("initial")
        if isinstance(selected_sink, PrivateSpeechBenchmarkEvidenceSink)
        else "asset-speech-review-automated-001"
    )
    artifacts = run_stock_voice_benchmark(
        policy=policy,
        corpus=corpus,
        scriptbook=scriptbook,
        candidate_id="kokoro-82m-stock",
        voice_key="pf_dora",
        provider=ReviewFixtureProvider(),
        evidence_sink=selected_sink,
        environment=BenchmarkEnvironmentV1(
            worker_image_digest_sha256="4" * 64,
            dependency_lock_digest_sha256="5" * 64,
            operating_system="linux",
            architecture="amd64",
            cpu="fixture-cpu",
            ram_gb=4,
            accelerator="none",
            accelerator_memory_gb=0,
            isolated_tenant=True,
            no_egress=True,
            ephemeral_workspace=True,
            cleanup_verified=True,
        ),
        component_digests_sha256=component_digests,
        run_id=run_id,
        bundle_id="speech-review-automated-001",
        bundle_asset_id=bundle_asset_id,
        evaluator="clicko.stock-voice-runner.v1",
        evaluator_digest_sha256="a" * 64,
        peak_ram_sampler=lambda: 0.25,
    )
    return policy, corpus, scriptbook, artifacts


def _submissions(plan):
    plan_digest = speech_review_plan_digest(plan)
    submissions = []
    for packet in plan.packets:
        submissions.append(
            SpeechReviewSubmissionV1(
                submission_id=f"submission-{packet.reviewer_pseudonym}",
                packet_id=packet.packet_id,
                plan_digest_sha256=plan_digest,
                reviewer_pseudonym=packet.reviewer_pseudonym,
                submitted_at=datetime(2026, 8, 26, 12, 0, tzinfo=UTC),
                responses=[
                    SpeechReviewResponseV1(
                        assignment_id=assignment.assignment_id,
                        script_digest_sha256=assignment.script_digest_sha256,
                        output_checksum_sha256=assignment.output_checksum_sha256,
                        naturalness_mos=5,
                        intelligibility_word_accuracy=1,
                        critical_term_accuracy=1,
                        critical_off_script=False,
                        repeat_or_truncation=False,
                    )
                    for assignment in packet.assignments
                ],
            )
        )
    return submissions


def test_three_blinded_reviewers_emit_192_bound_ratings_and_recomputable_metrics(tmp_path):
    policy, corpus, scriptbook, artifacts = _inputs()
    plan = build_blinded_review_plan(
        policy=policy,
        corpus=corpus,
        artifacts=artifacts,
        scriptbook=scriptbook,
        reviewer_pseudonyms=["reviewer-01", "reviewer-02", "reviewer-03"],
        blinded_candidate_label="Voz A7",
        blinding_secret=b"a-secret-that-is-at-least-thirty-two-bytes",
        generated_at=datetime(2026, 8, 26, 11, 0, tzinfo=UTC),
    )

    assert len(plan.packets) == 3
    assert sum(len(packet.assignments) for packet in plan.packets) == 192
    reviewer_projection = json.dumps(
        [packet.model_dump(by_alias=True, mode="json") for packet in plan.packets],
        ensure_ascii=False,
    ).lower()
    assert "kokoro" not in reviewer_projection
    assert "review-fixture" not in reviewer_projection
    sink = PrivateSpeechBenchmarkEvidenceSink(
        tmp_path / "private-review",
        run_id=artifacts.run.run_id,
        forbidden_root=ROOT,
    )
    stored_plan = sink.persist_review_plan(plan)
    assert stored_plan["packetCount"] == 3
    packet_projection = " ".join(
        path.read_text(encoding="utf-8")
        for path in (sink.root / "review" / "packets").glob("*.json")
    ).lower()
    assert "kokoro" not in packet_projection
    assert "review-fixture" not in packet_projection

    reviewed, review_bundle = append_blinded_review_evidence(
        artifacts,
        policy,
        plan,
        _submissions(plan),
        review_bundle_id="speech-review-bundle-001",
        review_bundle_asset_id=sink.review_bundle_asset_id(),
        evaluator="clicko.blinded-speech-review.v1",
        evaluator_digest_sha256="b" * 64,
        generated_at=datetime(2026, 8, 26, 13, 0, tzinfo=UTC),
    )

    assert len(review_bundle.submissions) == 3
    naturalness = next(
        item for item in reviewed.run.measurements if item.metric_id == "human_naturalness_mos"
    )
    assert naturalness.value == 5
    assert naturalness.sample_count == 192
    assert reviewed.run.controls["human_review_completed"] is True
    assert reviewed.run.evidence_refs["blinded_human_review"] == sink.review_bundle_asset_id()
    assert len(reviewed.evidence_bundle.observations) == 256 + 5 * 192
    stored_review = sink.persist_review_result(review_bundle, reviewed)
    assert stored_review["reviewBundleAssetId"] == sink.review_bundle_asset_id()
    assert (sink.root / "snapshots" / "post-review" / "package-manifest.json").is_file()

    gate = evaluate_benchmark_run(
        policy,
        reviewed.run,
        corpus_manifest=corpus,
        evidence_bundle=reviewed.evidence_bundle,
    )
    assert gate.decision == "incomplete"
    assert "human_naturalness_mos" not in gate.missing_metrics
    assert "pt_br_intelligibility_word_accuracy" not in gate.missing_metrics
    assert gate.missing_metrics == ["derived_cleanup_success_rate"]
    assert gate.blocking_reasons == []

    cleanup = SpeechBenchmarkCleanupBundleV1(
        bundle_id="speech-review-cleanup-001",
        run_id=reviewed.run.run_id,
        generated_at=datetime(2026, 8, 26, 14, 0, tzinfo=UTC),
        cases=[
            SpeechBenchmarkCleanupCaseV1(
                case_id=execution.case_id,
                output_asset_id=execution.output_asset_id,
                output_checksum_sha256=execution.output_checksum_sha256,
                deletion_attempted=True,
                deleted=True,
                verified_absent=True,
            )
            for execution in reviewed.evidence_bundle.case_executions
        ],
    )
    reviewed_and_cleaned = append_cleanup_evidence(
        reviewed,
        cleanup,
        cleanup_asset_id="asset-speech-review-cleanup-001",
        evaluator="clicko.stock-cleanup.v1",
        evaluator_digest_sha256="c" * 64,
    )
    post_cleanup_gate = evaluate_benchmark_run(
        policy,
        reviewed_and_cleaned.run,
        corpus_manifest=corpus,
        evidence_bundle=reviewed_and_cleaned.evidence_bundle,
    )
    assert post_cleanup_gate.decision == "incomplete"
    assert post_cleanup_gate.missing_metrics == []
    assert post_cleanup_gate.failed_metrics == []
    assert post_cleanup_gate.blocking_reasons == []


def test_review_plan_rejects_candidate_name_in_blinded_label():
    policy, corpus, scriptbook, artifacts = _inputs()

    with pytest.raises(ValueError, match="speech_review_label_leaks_candidate"):
        build_blinded_review_plan(
            policy=policy,
            corpus=corpus,
            artifacts=artifacts,
            scriptbook=scriptbook,
            reviewer_pseudonyms=["reviewer-01", "reviewer-02", "reviewer-03"],
            blinded_candidate_label="kokoro-82m-stock",
            blinding_secret=b"a-secret-that-is-at-least-thirty-two-bytes",
        )


def test_private_review_cli_lifecycle_is_resumable_after_cleanup(
    tmp_path, monkeypatch, capsys
):
    run_id = "speech-review-cli-run-001"
    private_root = tmp_path / "private-cli-review"
    sink = PrivateSpeechBenchmarkEvidenceSink(
        private_root,
        run_id=run_id,
        forbidden_root=ROOT,
    )
    policy, corpus, scriptbook, artifacts = _inputs(
        evidence_sink=sink,
        run_id=run_id,
    )
    sink.persist_snapshot(artifacts, stage="initial")
    corpus_path = tmp_path / "stock-corpus.json"
    corpus_path.write_text(corpus.model_dump_json(by_alias=True), encoding="utf-8")
    scriptbook_path = tmp_path / "stock-scriptbook.json"
    scriptbook_path.write_text(
        json.dumps(scriptbook, ensure_ascii=False),
        encoding="utf-8",
    )
    monkeypatch.setenv(
        "CLICKO_SPEECH_REVIEW_BLINDING_SECRET_B64",
        "YS1zZWNyZXQtdGhhdC1pcy1hdC1sZWFzdC10aGlydHktdHdvLWJ5dGVz",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prepare_speech_review.py",
            "--corpus",
            str(corpus_path),
            "--scriptbook",
            str(scriptbook_path),
            "--private-output-root",
            str(private_root),
            "--run-id",
            run_id,
            "--reviewer",
            "reviewer-01",
            "--reviewer",
            "reviewer-02",
            "--reviewer",
            "reviewer-03",
            "--blinded-label",
            "Voz A7",
        ],
    )
    assert prepare_speech_review.main() == 0
    prepared_output = json.loads(capsys.readouterr().out)
    assert prepared_output["packetCount"] == 3

    plan_payload = json.loads(
        (private_root / "review" / "organizer" / "review-plan.json").read_text(
            encoding="utf-8"
        )
    )
    plan_payload.pop("assetId")
    plan = SpeechReviewPlanV1.model_validate(plan_payload)
    submission_paths = []
    for index, submission in enumerate(_submissions(plan), start=1):
        submission_path = tmp_path / f"review-submission-{index}.json"
        submission_path.write_text(
            submission.model_dump_json(by_alias=True),
            encoding="utf-8",
        )
        submission_paths.append(submission_path)

    ingest_argv = [
        "ingest_speech_review.py",
        "--corpus",
        str(corpus_path),
        "--private-output-root",
        str(private_root),
        "--run-id",
        run_id,
    ]
    for submission_path in submission_paths:
        ingest_argv.extend(["--submission", str(submission_path)])
    monkeypatch.setattr(sys, "argv", ingest_argv)
    assert ingest_speech_review.main() == 0
    ingested_output = json.loads(capsys.readouterr().out)
    assert ingested_output["ratingCount"] == 192
    assert ingested_output["decision"] == "incomplete"
    assert len(list((private_root / "audio").glob("*.wav"))) == 64

    cleanup_argv = [
        "finalize_speech_benchmark_cleanup.py",
        "--corpus",
        str(corpus_path),
        "--private-output-root",
        str(private_root),
        "--run-id",
        run_id,
    ]
    monkeypatch.setattr(sys, "argv", cleanup_argv)
    assert finalize_speech_benchmark_cleanup.main() == 0
    cleanup_output = json.loads(capsys.readouterr().out)
    assert cleanup_output["verifiedAbsentCount"] == 64
    assert cleanup_output["decision"] == "incomplete"
    assert list((private_root / "audio").glob("*.wav")) == []

    monkeypatch.setattr(sys, "argv", cleanup_argv)
    assert finalize_speech_benchmark_cleanup.main() == 0
    resumed_output = json.loads(capsys.readouterr().out)
    assert resumed_output == cleanup_output
