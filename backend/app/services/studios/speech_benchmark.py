from __future__ import annotations

import hashlib
import math
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from ...domain.studios.benchmarking import (
    BenchmarkCaseExecutionV1,
    BenchmarkCorpusManifestV1,
    BenchmarkEnvironmentV1,
    BenchmarkEvidenceBundleV1,
    BenchmarkMeasurementV1,
    BenchmarkMetricObservationV1,
    BenchmarkPolicyV1,
    BenchmarkRunV1,
    SpeechBenchmarkCleanupBundleV1,
    benchmark_corpus_manifest_digest,
    benchmark_evidence_bundle_digest,
    benchmark_policy_digest,
)
from ...domain.studios.contracts import SpeechSynthesisRequestV1
from ...domain.studios.providers import SpeechSynthesisProvider
from ..object_storage import sha256_file

PeakRamSampler = Callable[[], float]


class SpeechBenchmarkEvidenceSink(Protocol):
    def persist_output(self, case_id: str, source: Path, metadata: dict[str, Any]) -> str: ...

    def persist_provenance(self, case_id: str, payload: dict[str, Any]) -> str: ...

    def delete(self, asset_id: str) -> bool: ...


@dataclass(frozen=True)
class StockVoiceBenchmarkArtifacts:
    run: BenchmarkRunV1
    evidence_bundle: BenchmarkEvidenceBundleV1


def append_cleanup_evidence(
    artifacts: StockVoiceBenchmarkArtifacts,
    cleanup: SpeechBenchmarkCleanupBundleV1,
    *,
    cleanup_asset_id: str,
    evaluator: str,
    evaluator_digest_sha256: str,
) -> StockVoiceBenchmarkArtifacts:
    if cleanup.run_id != artifacts.run.run_id:
        raise ValueError("speech_benchmark_cleanup_run_mismatch")
    execution_case_ids = {case.case_id for case in artifacts.evidence_bundle.case_executions}
    cleanup_by_id = {case.case_id: case for case in cleanup.cases}
    if set(cleanup_by_id) != execution_case_ids:
        raise ValueError("speech_benchmark_cleanup_case_set_mismatch")
    if any(item.metric_id == "derived_cleanup_success_rate" for item in artifacts.run.measurements):
        raise ValueError("speech_benchmark_cleanup_already_attached")

    observations = list(artifacts.evidence_bundle.observations)
    cleanup_observations = [
        BenchmarkMetricObservationV1(
            observation_id=f"obs-derived_cleanup_success_rate-{case_id}",
            metric_id="derived_cleanup_success_rate",
            case_id=case_id,
            unit="ratio",
            value=1 if cleanup_by_id[case_id].verified_absent else 0,
            evaluator=evaluator,
            evaluator_digest_sha256=evaluator_digest_sha256,
            evidence_asset_id=cleanup_asset_id,
        )
        for case_id in sorted(execution_case_ids)
    ]
    observations.extend(cleanup_observations)
    evidence_bundle = artifacts.evidence_bundle.model_copy(
        update={"generated_at": cleanup.generated_at, "observations": observations}
    )
    cleanup_success = all(item.verified_absent for item in cleanup.cases)
    cleanup_measurement = BenchmarkMeasurementV1(
        metric_id="derived_cleanup_success_rate",
        unit="ratio",
        aggregation="rate",
        value=sum(item.value for item in cleanup_observations) / len(cleanup_observations),
        sample_count=len(cleanup_observations),
        evaluator=evaluator,
        evaluator_digest_sha256=evaluator_digest_sha256,
        case_set_digest_sha256=artifacts.run.corpus_manifest_digest_sha256,
        evidence_asset_ids=[cleanup_asset_id],
    )
    run = artifacts.run.model_copy(
        update={
            "environment": artifacts.run.environment.model_copy(
                update={"cleanup_verified": cleanup_success}
            ),
            "controls": {
                **artifacts.run.controls,
                "deletion_cleanup_verified": cleanup_success,
            },
            "evidence_refs": {
                **artifacts.run.evidence_refs,
                "cleanup_receipt": cleanup_asset_id,
            },
            "evidence_bundle_digest_sha256": benchmark_evidence_bundle_digest(evidence_bundle),
            "measurements": [*artifacts.run.measurements, cleanup_measurement],
        }
    )
    return StockVoiceBenchmarkArtifacts(run=run, evidence_bundle=evidence_bundle)


def _aggregate(values: list[float], aggregation: str) -> float:
    if aggregation in {"mean", "rate"}:
        return sum(values) / len(values)
    ordered = sorted(values)
    if aggregation == "p50":
        return ordered[math.ceil(0.50 * len(ordered)) - 1]
    if aggregation == "p95":
        return ordered[math.ceil(0.95 * len(ordered)) - 1]
    if aggregation == "maximum":
        return max(values)
    if aggregation == "minimum":
        return min(values)
    if aggregation == "count":
        return float(len(values))
    raise ValueError(f"unsupported_benchmark_aggregation:{aggregation}")


def _scriptbook_cases(
    scriptbook: dict[str, Any],
    *,
    policy: BenchmarkPolicyV1,
    corpus: BenchmarkCorpusManifestV1,
) -> dict[str, dict[str, Any]]:
    policy_digest = benchmark_policy_digest(policy)
    corpus_digest = benchmark_corpus_manifest_digest(corpus)
    if scriptbook.get("schemaVersion") != "clicko.synthetic-scriptbook.v1":
        raise ValueError("stock_scriptbook_schema_mismatch")
    if scriptbook.get("suiteId") != policy.suite_id:
        raise ValueError("stock_scriptbook_suite_mismatch")
    if str(scriptbook.get("policyDigestSha256", "")).lower() != policy_digest:
        raise ValueError("stock_scriptbook_policy_digest_mismatch")
    if str(scriptbook.get("corpusManifestDigestSha256", "")).lower() != corpus_digest:
        raise ValueError("stock_scriptbook_corpus_digest_mismatch")
    raw_cases = scriptbook.get("cases")
    if not isinstance(raw_cases, list):
        raise ValueError("stock_scriptbook_cases_missing")
    cases = {
        str(case.get("caseId")): case
        for case in raw_cases
        if isinstance(case, dict) and case.get("caseId")
    }
    if len(cases) != len(raw_cases):
        raise ValueError("stock_scriptbook_case_ids_invalid")
    corpus_by_id = {case.case_id: case for case in corpus.cases}
    if set(cases) != set(corpus_by_id):
        raise ValueError("stock_scriptbook_case_set_mismatch")
    for case_id, manifest_case in corpus_by_id.items():
        entry = cases[case_id]
        if entry.get("locale") != manifest_case.locale:
            raise ValueError(f"stock_scriptbook_locale_mismatch:{case_id}")
        if entry.get("scenarios") != manifest_case.scenarios:
            raise ValueError(f"stock_scriptbook_scenarios_mismatch:{case_id}")
        text = entry.get("text")
        if not isinstance(text, str) or not text:
            raise ValueError(f"stock_scriptbook_text_missing:{case_id}")
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if digest != manifest_case.script_digest_sha256.lower() or digest != str(
            entry.get("scriptDigestSha256", "")
        ).lower():
            raise ValueError(f"stock_scriptbook_script_digest_mismatch:{case_id}")
    return cases


def run_stock_voice_benchmark(
    *,
    policy: BenchmarkPolicyV1,
    corpus: BenchmarkCorpusManifestV1,
    scriptbook: dict[str, Any],
    candidate_id: str,
    voice_key: str,
    provider: SpeechSynthesisProvider,
    evidence_sink: SpeechBenchmarkEvidenceSink,
    environment: BenchmarkEnvironmentV1,
    component_digests_sha256: dict[str, str],
    run_id: str,
    bundle_id: str,
    bundle_asset_id: str,
    evaluator: str,
    evaluator_digest_sha256: str,
    peak_ram_sampler: PeakRamSampler,
) -> StockVoiceBenchmarkArtifacts:
    if policy.capability != "stock_voice":
        raise ValueError("stock_voice_policy_required")
    policy_digest = benchmark_policy_digest(policy)
    corpus_digest = benchmark_corpus_manifest_digest(corpus)
    if corpus.suite_id != policy.suite_id or corpus.policy_digest_sha256.lower() != policy_digest:
        raise ValueError("stock_corpus_identity_mismatch")
    if any(not item.synthetic or item.locale != policy.locale for item in corpus.cases):
        raise ValueError("stock_corpus_must_be_synthetic_and_match_locale")
    candidate = next((item for item in policy.candidates if item.candidate_id == candidate_id), None)
    if candidate is None or candidate.role != "stock_voice" or candidate.benchmark_scope != "synthetic_only":
        raise ValueError("stock_candidate_not_in_policy")
    if provider.name != candidate_id:
        raise ValueError("stock_provider_candidate_mismatch")
    required_components = {item.component_id for item in candidate.components if item.required}
    if set(component_digests_sha256) != required_components:
        raise ValueError("stock_component_digest_set_mismatch")
    cases = _scriptbook_cases(scriptbook, policy=policy, corpus=corpus)
    started_at = datetime.now(UTC)
    executions: list[BenchmarkCaseExecutionV1] = []
    observations: list[BenchmarkMetricObservationV1] = []

    def observe(case_id: str, metric_id: str, unit: str, value: float, evidence_asset_id: str) -> None:
        observations.append(
            BenchmarkMetricObservationV1(
                observation_id=f"obs-{metric_id}-{case_id}",
                metric_id=metric_id,
                case_id=case_id,
                unit=unit,
                value=value,
                evaluator=evaluator,
                evaluator_digest_sha256=evaluator_digest_sha256,
                evidence_asset_id=evidence_asset_id,
            )
        )

    for corpus_case in corpus.cases:
        case_id = corpus_case.case_id
        entry = cases[case_id]
        case_started_at = datetime.now(UTC)
        started = time.perf_counter()
        output_asset_id: str | None = None
        provenance_asset_id: str | None = None
        try:
            request = SpeechSynthesisRequestV1(
                locale=corpus_case.locale,
                text=entry["text"],
                script_digest_sha256=corpus_case.script_digest_sha256,
                voice_key=voice_key,
            )
            with tempfile.TemporaryDirectory(prefix=f"clicko-stock-{case_id}-") as temporary:
                output = Path(temporary) / "speech.wav"
                result = provider.synthesize(request, output, lambda _value: None, lambda: False)
                active_seconds = max(0.0, time.perf_counter() - started)
                if not output.is_file() or output.stat().st_size <= 0:
                    raise ValueError("stock_benchmark_output_missing")
                checksum = sha256_file(output)
                if (
                    result.provider != provider.name
                    or result.provider_version != provider.version
                    or result.audio_format != request.audio_format
                    or result.sample_rate != request.sample_rate
                    or result.artifact_checksum_sha256.lower() != checksum
                ):
                    raise ValueError("stock_benchmark_result_binding_mismatch")
                direct_cost = result.metrics.get("directCostUsd")
                if direct_cost is None or not math.isfinite(direct_cost) or direct_cost < 0:
                    raise ValueError("stock_benchmark_direct_cost_missing")
                peak_ram_gb = peak_ram_sampler()
                if not math.isfinite(peak_ram_gb) or peak_ram_gb <= 0:
                    raise ValueError("stock_benchmark_peak_ram_missing")
                duration_seconds = result.duration_ms / 1000
                output_asset_id = evidence_sink.persist_output(
                    case_id,
                    output,
                    {
                        "checksumSha256": checksum,
                        "scriptDigestSha256": request.script_digest_sha256,
                        "provider": result.provider,
                        "providerVersion": result.provider_version,
                    },
                )
                provenance_asset_id = evidence_sink.persist_provenance(
                    case_id,
                    {
                        "schemaVersion": "studio.stock-voice-case-provenance.v1",
                        "caseId": case_id,
                        "outputAssetId": output_asset_id,
                        "outputChecksumSha256": checksum,
                        "scriptDigestSha256": request.script_digest_sha256,
                        "speechProvenance": result.provenance.model_dump(by_alias=True, mode="json"),
                    },
                )
            completed_at = datetime.now(UTC)
            executions.append(
                BenchmarkCaseExecutionV1(
                    case_id=case_id,
                    status="succeeded",
                    generation_job_id=f"job-{case_id}",
                    provider=result.provider,
                    provider_version=result.provider_version,
                    started_at=case_started_at,
                    completed_at=completed_at,
                    output_asset_id=output_asset_id,
                    output_checksum_sha256=checksum,
                    provenance_asset_id=provenance_asset_id,
                    output_duration_seconds=duration_seconds,
                    active_compute_seconds=active_seconds,
                    peak_vram_gb=0,
                    direct_cost_usd=direct_cost,
                )
            )
            observe(case_id, "p95_real_time_factor", "ratio", active_seconds / duration_seconds, provenance_asset_id)
            observe(case_id, "peak_ram_gb", "gb", peak_ram_gb, provenance_asset_id)
            observe(
                case_id,
                "usd_per_output_minute",
                "usd_per_output_minute",
                direct_cost / (duration_seconds / 60),
                provenance_asset_id,
            )
            observe(case_id, "job_failure_rate", "ratio", 0, provenance_asset_id)
        except Exception as error:
            if provenance_asset_id is not None:
                evidence_sink.delete(provenance_asset_id)
            if output_asset_id is not None:
                evidence_sink.delete(output_asset_id)
            completed_at = datetime.now(UTC)
            executions.append(
                BenchmarkCaseExecutionV1(
                    case_id=case_id,
                    status="failed",
                    generation_job_id=f"job-{case_id}",
                    provider=provider.name,
                    provider_version=provider.version,
                    started_at=case_started_at,
                    completed_at=completed_at,
                    active_compute_seconds=max(0.0, time.perf_counter() - started),
                    peak_vram_gb=0,
                    direct_cost_usd=0,
                    failure_code=type(error).__name__,
                )
            )
            observe(case_id, "job_failure_rate", "ratio", 1, bundle_asset_id)

    generated_at = datetime.now(UTC)
    bundle = BenchmarkEvidenceBundleV1(
        bundle_id=bundle_id,
        run_id=run_id,
        suite_id=policy.suite_id,
        candidate_id=candidate_id,
        policy_digest_sha256=policy_digest,
        corpus_manifest_digest_sha256=corpus_digest,
        generated_at=generated_at,
        case_executions=executions,
        observations=observations,
    )
    thresholds = {item.metric_id: item for item in policy.thresholds}
    measurements: list[BenchmarkMeasurementV1] = []
    for metric_id in sorted({item.metric_id for item in observations}):
        threshold = thresholds[metric_id]
        metric_observations = [item for item in observations if item.metric_id == metric_id]
        values = [item.value for item in metric_observations]
        measurements.append(
            BenchmarkMeasurementV1(
                metric_id=metric_id,
                unit=threshold.unit,
                aggregation=threshold.aggregation,
                value=_aggregate(values, threshold.aggregation),
                sample_count=len(values),
                evaluator=evaluator,
                evaluator_digest_sha256=evaluator_digest_sha256,
                case_set_digest_sha256=corpus_digest,
                evidence_asset_ids=sorted({item.evidence_asset_id for item in metric_observations}),
            )
        )
    run = BenchmarkRunV1(
        run_id=run_id,
        suite_id=policy.suite_id,
        policy_digest_sha256=policy_digest,
        candidate_id=candidate_id,
        status="completed",
        corpus_manifest_digest_sha256=corpus_digest,
        subject_count=0,
        case_count=len(corpus.cases),
        consent_coverage=1,
        started_at=started_at,
        completed_at=generated_at,
        environment=environment,
        component_digests_sha256=component_digests_sha256,
        controls={"synthetic_provenance_emitted": True},
        evidence_refs={
            "private_corpus_manifest": corpus.corpus_id,
            "raw_metric_bundle": bundle_asset_id,
        },
        evidence_bundle_digest_sha256=benchmark_evidence_bundle_digest(bundle),
        measurements=measurements,
    )
    return StockVoiceBenchmarkArtifacts(run=run, evidence_bundle=bundle)
