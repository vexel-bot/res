from __future__ import annotations

import hashlib
import sys
import wave
from pathlib import Path

import pytest

from app.domain.studios.benchmarking import (
    BenchmarkEnvironmentV1,
    BenchmarkPolicyV1,
    evaluate_benchmark_run,
)
from app.domain.studios.contracts import SpeechProvenanceV1, SpeechSynthesisResultV1
from app.services.object_storage import sha256_file
from app.services.studios.speech_benchmark import (
    append_cleanup_evidence,
    run_stock_voice_benchmark,
)
from app.services.studios.speech_benchmark_storage import PrivateSpeechBenchmarkEvidenceSink

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_ROOT))

from generate_synthetic_stock_corpus import build_corpus  # noqa: E402


class FixtureProvider:
    name = "kokoro-82m-stock"
    version = "fixture-1"

    def synthesize(self, request, destination, progress, is_cancelled):
        frames = b"\x00\x00" * (request.sample_rate // 10)
        with wave.open(str(destination), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(request.sample_rate)
            output.writeframes(frames)
        return SpeechSynthesisResultV1(
            provider=self.name,
            provider_version=self.version,
            audio_format="wav",
            sample_rate=request.sample_rate,
            duration_ms=100,
            artifact_checksum_sha256=sha256_file(destination),
            provenance=SpeechProvenanceV1(
                source_revision="fixture-revision-1",
                model_digest_sha256="1" * 64,
                worker_manifest_digest_sha256="2" * 64,
                worker_image_digest=f"sha256:{'3' * 64}",
                provenance_mode="fixture",
            ),
            metrics={"directCostUsd": 0.00001},
        )


def _policy() -> BenchmarkPolicyV1:
    return BenchmarkPolicyV1.model_validate_json(
        (ROOT / "benchmarks/studios/identity/voice-stock-pt-br-policy.v1.json").read_text(
            encoding="utf-8"
        )
    )


def _environment() -> BenchmarkEnvironmentV1:
    return BenchmarkEnvironmentV1(
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
    )


def _component_digests(policy: BenchmarkPolicyV1) -> dict[str, str]:
    return {
        component.component_id: f"{index:x}" * 64
        for index, component in enumerate(policy.candidates[0].components, start=6)
        if component.required
    }


def test_private_sink_retains_review_audio_then_emits_cleanup_evidence(tmp_path):
    policy = _policy()
    corpus, scriptbook = build_corpus(policy)
    private_root = tmp_path / "stock-run-private"
    sink = PrivateSpeechBenchmarkEvidenceSink(
        private_root,
        run_id="stock-private-run-001",
        forbidden_root=ROOT,
    )
    artifacts = run_stock_voice_benchmark(
        policy=policy,
        corpus=corpus,
        scriptbook=scriptbook,
        candidate_id="kokoro-82m-stock",
        voice_key="pf_dora",
        provider=FixtureProvider(),
        evidence_sink=sink,
        environment=_environment(),
        component_digests_sha256=_component_digests(policy),
        run_id="stock-private-run-001",
        bundle_id="stock-private-bundle-001",
        bundle_asset_id=sink.evidence_bundle_asset_id("initial"),
        evaluator="clicko.stock-voice-runner.v1",
        evaluator_digest_sha256="a" * 64,
        peak_ram_sampler=lambda: 0.25,
    )

    assert len(list((private_root / "audio").glob("*.wav"))) == 64
    assert len(list((private_root / "metadata").glob("*.json"))) == 64
    assert len(list((private_root / "provenance").glob("*.json"))) == 64
    snapshot = sink.persist_snapshot(artifacts, stage="initial")
    assert snapshot["evidenceBundleAssetId"] == artifacts.run.evidence_refs["raw_metric_bundle"]
    assert (private_root / "snapshots" / "initial" / "package-manifest.json").is_file()
    assert sink.persist_snapshot(artifacts, stage="initial") == snapshot

    reopened = PrivateSpeechBenchmarkEvidenceSink.open_existing(
        private_root,
        run_id="stock-private-run-001",
        forbidden_root=ROOT,
    )
    cleanup_asset_id, cleanup = reopened.finalize_audio_cleanup(
        artifacts.evidence_bundle,
        cleanup_bundle_id="stock-cleanup-001",
    )
    finalized = append_cleanup_evidence(
        artifacts,
        cleanup,
        cleanup_asset_id=cleanup_asset_id,
        evaluator="clicko.stock-cleanup.v1",
        evaluator_digest_sha256="b" * 64,
    )

    assert list((private_root / "audio").glob("*.wav")) == []
    assert list((private_root / "metadata").glob("*.json")) == []
    assert len(list((private_root / "provenance").glob("*.json"))) == 64
    assert (private_root / "receipts" / "cleanup-bundle.json").is_file()
    reopened_after_cleanup = PrivateSpeechBenchmarkEvidenceSink.open_existing(
        private_root,
        run_id="stock-private-run-001",
        forbidden_root=ROOT,
    )
    loaded_cleanup_asset_id, loaded_cleanup = reopened_after_cleanup.load_cleanup_bundle()
    assert loaded_cleanup_asset_id == cleanup_asset_id
    assert loaded_cleanup == cleanup
    cleanup_measurement = next(
        item
        for item in finalized.run.measurements
        if item.metric_id == "derived_cleanup_success_rate"
    )
    assert cleanup_measurement.value == 1
    assert cleanup_measurement.sample_count == 64
    assert finalized.run.controls["deletion_cleanup_verified"] is True
    assert finalized.run.evidence_refs["cleanup_receipt"] == cleanup_asset_id

    gate = evaluate_benchmark_run(
        policy,
        finalized.run,
        corpus_manifest=corpus,
        evidence_bundle=finalized.evidence_bundle,
    )
    assert gate.decision == "incomplete"
    assert "derived_cleanup_success_rate" not in gate.missing_metrics
    assert "missing_control:deletion_cleanup_verified" not in gate.incomplete_reasons
    assert "missing_evidence:cleanup_receipt" not in gate.incomplete_reasons


def test_private_sink_refuses_repository_paths(tmp_path):
    forbidden = tmp_path / "repository"
    forbidden.mkdir()
    unsafe = forbidden / "benchmark-output"

    try:
        PrivateSpeechBenchmarkEvidenceSink(
            unsafe,
            run_id="unsafe-run",
            forbidden_root=forbidden,
        )
    except ValueError as error:
        assert str(error) == "benchmark_private_root_must_stay_outside_repository"
    else:
        raise AssertionError("repository-local private evidence root was accepted")
    assert not unsafe.exists()


def test_private_sink_refuses_tampered_audio_when_reopened(tmp_path):
    private_root = tmp_path / "private-reopen"
    sink = PrivateSpeechBenchmarkEvidenceSink(
        private_root,
        run_id="reopen-run",
        forbidden_root=ROOT,
    )
    source = tmp_path / "source.wav"
    source.write_bytes(b"fixture-wav-bytes")
    checksum = hashlib.sha256(source.read_bytes()).hexdigest()
    sink.persist_output(
        "case-001",
        source,
        {
            "checksumSha256": checksum,
            "scriptDigestSha256": "1" * 64,
            "provider": "fixture",
            "providerVersion": "1",
        },
    )
    stored = next((private_root / "audio").glob("*.wav"))
    stored.write_bytes(b"tampered")

    with pytest.raises(ValueError, match="benchmark_private_reopen_checksum_mismatch"):
        PrivateSpeechBenchmarkEvidenceSink.open_existing(
            private_root,
            run_id="reopen-run",
            forbidden_root=ROOT,
        )
