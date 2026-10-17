from __future__ import annotations

import shutil
import sys
import wave
from pathlib import Path

import pytest

from app.domain.studios.benchmarking import (
    BenchmarkEnvironmentV1,
    BenchmarkPolicyV1,
    benchmark_evidence_bundle_digest,
    evaluate_benchmark_run,
)
from app.domain.studios.contracts import SpeechProvenanceV1, SpeechSynthesisResultV1
from app.services.object_storage import sha256_file
from app.services.studios.speech_benchmark import run_stock_voice_benchmark

SCRIPTS_ROOT = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_ROOT))

from generate_synthetic_stock_corpus import build_corpus  # noqa: E402

POLICY_PATH = (
    Path(__file__).resolve().parents[2]
    / "benchmarks"
    / "studios"
    / "identity"
    / "voice-stock-pt-br-policy.v1.json"
)


class FakeStockVoiceProvider:
    name = "kokoro-82m-stock"
    version = "test-runtime-1"

    def __init__(self) -> None:
        self.calls = 0

    def synthesize(self, request, destination: Path, progress, is_cancelled):
        self.calls += 1
        progress(50)
        assert not is_cancelled()
        frames = b"\x00\x00" * (request.sample_rate // 10)
        with wave.open(str(destination), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(request.sample_rate)
            output.writeframes(frames)
        return SpeechSynthesisResultV1(
            provider=self.name,
            provider_version=self.version,
            audio_format=request.audio_format,
            sample_rate=request.sample_rate,
            duration_ms=100,
            artifact_checksum_sha256=sha256_file(destination),
            provenance=SpeechProvenanceV1(
                source_revision="test-revision-1",
                model_digest_sha256="1" * 64,
                worker_manifest_digest_sha256="2" * 64,
                worker_image_digest=f"sha256:{'3' * 64}",
                provenance_mode="test-fixture",
            ),
            metrics={"directCostUsd": 0.00001},
        )


class LocalEvidenceSink:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.assets: dict[str, Path | dict] = {}
        self.deleted: list[str] = []

    def persist_output(self, case_id: str, source: Path, metadata: dict) -> str:
        asset_id = f"audio-{case_id}"
        destination = self.root / f"{case_id}.wav"
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        self.assets[asset_id] = destination
        return asset_id

    def persist_provenance(self, case_id: str, payload: dict) -> str:
        asset_id = f"provenance-{case_id}"
        self.assets[asset_id] = payload
        return asset_id

    def delete(self, asset_id: str) -> bool:
        stored = self.assets.pop(asset_id, None)
        if isinstance(stored, Path):
            stored.unlink(missing_ok=True)
        self.deleted.append(asset_id)
        return stored is not None


def _policy() -> BenchmarkPolicyV1:
    return BenchmarkPolicyV1.model_validate_json(POLICY_PATH.read_text(encoding="utf-8"))


def _environment() -> BenchmarkEnvironmentV1:
    return BenchmarkEnvironmentV1(
        worker_image_digest_sha256="4" * 64,
        dependency_lock_digest_sha256="5" * 64,
        operating_system="linux",
        architecture="amd64",
        cpu="test-cpu",
        ram_gb=4,
        accelerator="none",
        accelerator_memory_gb=0,
        isolated_tenant=True,
        no_egress=True,
        ephemeral_workspace=True,
        cleanup_verified=True,
    )


def _component_digests(policy: BenchmarkPolicyV1) -> dict[str, str]:
    candidate = policy.candidates[0]
    return {
        component.component_id: f"{index:x}" * 64
        for index, component in enumerate(candidate.components, start=6)
        if component.required
    }


def test_runner_emits_recomputable_automated_evidence_but_cannot_self_approve(tmp_path):
    policy = _policy()
    corpus, scriptbook = build_corpus(policy)
    provider = FakeStockVoiceProvider()
    sink = LocalEvidenceSink(tmp_path / "private-evidence")

    artifacts = run_stock_voice_benchmark(
        policy=policy,
        corpus=corpus,
        scriptbook=scriptbook,
        candidate_id="kokoro-82m-stock",
        voice_key="pt-br-stock-test",
        provider=provider,
        evidence_sink=sink,
        environment=_environment(),
        component_digests_sha256=_component_digests(policy),
        run_id="stock-run-001",
        bundle_id="stock-bundle-001",
        bundle_asset_id="asset-raw-metric-bundle-001",
        evaluator="clicko.stock-voice-runner.v1",
        evaluator_digest_sha256="a" * 64,
        peak_ram_sampler=lambda: 0.25,
    )

    assert provider.calls == 64
    assert len(artifacts.evidence_bundle.case_executions) == 64
    assert all(case.status == "succeeded" for case in artifacts.evidence_bundle.case_executions)
    assert len(artifacts.evidence_bundle.observations) == 4 * 64
    assert {item.metric_id for item in artifacts.run.measurements} == {
        "job_failure_rate",
        "p95_real_time_factor",
        "peak_ram_gb",
        "usd_per_output_minute",
    }
    assert artifacts.run.evidence_bundle_digest_sha256 == benchmark_evidence_bundle_digest(
        artifacts.evidence_bundle
    )
    assert len(sink.assets) == 2 * 64
    assert sink.deleted == []

    gate = evaluate_benchmark_run(
        policy,
        artifacts.run,
        corpus_manifest=corpus,
        evidence_bundle=artifacts.evidence_bundle,
    )
    assert gate.decision == "incomplete"
    assert "human_naturalness_mos" in gate.missing_metrics
    assert "derived_cleanup_success_rate" in gate.missing_metrics
    assert "missing_license_manifest" in gate.incomplete_reasons
    assert gate.blocking_reasons == []


def test_runner_rejects_tampered_private_scriptbook_before_provider_execution(tmp_path):
    policy = _policy()
    corpus, scriptbook = build_corpus(policy)
    scriptbook["cases"][0]["text"] = "Texto adulterado depois do congelamento."
    provider = FakeStockVoiceProvider()
    sink = LocalEvidenceSink(tmp_path / "private-evidence")

    with pytest.raises(ValueError, match="stock_scriptbook_script_digest_mismatch"):
        run_stock_voice_benchmark(
            policy=policy,
            corpus=corpus,
            scriptbook=scriptbook,
            candidate_id="kokoro-82m-stock",
            voice_key="pt-br-stock-test",
            provider=provider,
            evidence_sink=sink,
            environment=_environment(),
            component_digests_sha256=_component_digests(policy),
            run_id="stock-run-tampered",
            bundle_id="stock-bundle-tampered",
            bundle_asset_id="asset-raw-metric-bundle-tampered",
            evaluator="clicko.stock-voice-runner.v1",
            evaluator_digest_sha256="a" * 64,
            peak_ram_sampler=lambda: 0.25,
        )

    assert provider.calls == 0
    assert sink.assets == {}
