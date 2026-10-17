"""Run the frozen stock pt-BR suite in a pinned, offline Linux worker.

This command intentionally retains private WAV outputs for blinded review. Cleanup
is a later evidenced stage; the command never registers or advertises the provider.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.domain.studios.artifacts import (  # noqa: E402
    ArtifactInventoryV1,
    ProviderCandidateManifestV1,
    artifact_inventory_digest,
)
from app.domain.studios.benchmarking import (  # noqa: E402
    BenchmarkCorpusManifestV1,
    BenchmarkEnvironmentV1,
    BenchmarkPolicyV1,
    benchmark_policy_digest,
    evaluate_benchmark_run,
)
from app.domain.studios.speech_assets import (  # noqa: E402
    EspeakRuntimeManifestV1,
    KokoroModelAssetManifestV1,
    verify_espeak_runtime,
    verify_kokoro_model_snapshot,
)
from app.providers.studios.kokoro_stock import (  # noqa: E402
    KokoroStockConfig,
    KokoroStockVoiceProvider,
)
from app.services.studios.speech_benchmark import run_stock_voice_benchmark  # noqa: E402
from app.services.studios.speech_benchmark_storage import (  # noqa: E402
    PrivateSpeechBenchmarkEvidenceSink,
)
from app.services.studios.worker_runtime import (  # noqa: E402
    load_worker_manifest,
    manifest_digest,
)
from scripts.verify_kokoro_candidate_lock import (  # noqa: E402
    ESPEAKNG_LOADER_BUNDLED_ESPEAK_REVISION,
    ESPEAKNG_LOADER_LINUX_AMD64_WHEEL_DIGEST,
    verify_lock,
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY = ROOT / "benchmarks/studios/identity/voice-stock-pt-br-policy.v1.json"
DEFAULT_CANDIDATE = ROOT / "workers/speech-cpu/providers/kokoro-82m-stock.provider.json"
DEFAULT_INVENTORY = ROOT / "workers/speech-cpu/providers/kokoro-82m-stock.artifacts.json"
DEFAULT_WORKER_MANIFEST = ROOT / "workers/speech-cpu/worker.manifest.json"
_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")
_IMAGE_DIGEST = re.compile(r"^sha256:[0-9a-fA-F]{64}$")


def _json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"benchmark_json_unreadable:{path.name}") from error
    if not isinstance(value, dict):
        raise ValueError(f"benchmark_json_object_required:{path.name}")
    return value


def _require_outside_repository(path: Path) -> None:
    resolved = path.resolve()
    repository = ROOT.resolve()
    if resolved == repository or resolved.is_relative_to(repository):
        raise ValueError(f"private_benchmark_path_inside_repository:{path.name}")


def _parse_component_digests(values: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for value in values:
        component_id, separator, digest = value.partition("=")
        if (
            not separator
            or not component_id
            or component_id in result
            or not _SHA256.fullmatch(digest)
        ):
            raise ValueError("component_digest_must_be_unique_id_equals_sha256")
        result[component_id] = digest.lower()
    return result


def _verify_espeak_runtime_binding(
    manifest: EspeakRuntimeManifestV1,
    *,
    manifest_digest_sha256: str,
    component_digests_sha256: dict[str, str],
    expected_source_revision: str,
) -> None:
    if manifest.source_revision != expected_source_revision:
        raise SystemExit("kokoro_benchmark_espeak_policy_revision_mismatch")
    if (
        manifest.bundled_espeak_revision
        != ESPEAKNG_LOADER_BUNDLED_ESPEAK_REVISION
        or manifest.loader_wheel_digest_sha256
        != ESPEAKNG_LOADER_LINUX_AMD64_WHEEL_DIGEST
    ):
        raise SystemExit("kokoro_benchmark_espeak_loader_binding_mismatch")
    if component_digests_sha256.get("espeak-ng-runtime") != manifest_digest_sha256:
        raise SystemExit("kokoro_benchmark_espeak_component_digest_mismatch")


def _cpu_name() -> str:
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.is_file():
        for line in cpuinfo.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.lower().startswith("model name") and ":" in line:
                return line.split(":", 1)[1].strip()[:240]
    return (platform.processor() or "unknown-linux-cpu")[:240]


def _ram_gb() -> float:
    page_size = os.sysconf("SC_PAGE_SIZE")
    pages = os.sysconf("SC_PHYS_PAGES")
    return page_size * pages / 1024**3


def _peak_ram_gb() -> float:
    import resource

    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024**2


def _evaluator_digest() -> str:
    digest = hashlib.sha256()
    for source in (
        ROOT / "backend/app/services/studios/speech_benchmark.py",
        ROOT / "backend/app/services/studios/speech_benchmark_storage.py",
    ):
        digest.update(hashlib.sha256(source.read_bytes()).digest())
    return digest.hexdigest()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--worker-manifest", type=Path, default=DEFAULT_WORKER_MANIFEST)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--scriptbook", type=Path, required=True)
    parser.add_argument("--candidate-lock", type=Path, required=True)
    parser.add_argument("--model-manifest", type=Path, required=True)
    parser.add_argument("--model-snapshot", type=Path, required=True)
    parser.add_argument("--espeak-runtime-manifest", type=Path, required=True)
    parser.add_argument("--espeak-runtime-root", type=Path, required=True)
    parser.add_argument("--private-output-root", type=Path, required=True)
    parser.add_argument("--worker-image-digest", required=True)
    parser.add_argument("--component-digest", action="append", default=[])
    parser.add_argument("--voice", choices=["pf_dora", "pm_alex", "pm_santa"], required=True)
    parser.add_argument("--cpu-hourly-cost-usd", type=float, required=True)
    parser.add_argument("--run-id")
    parser.add_argument("--attest-isolated-tenant", action="store_true", required=True)
    parser.add_argument("--attest-no-egress", action="store_true", required=True)
    parser.add_argument("--attest-ephemeral-workspace", action="store_true", required=True)
    parser.add_argument("--attest-cleanup-mechanism", action="store_true", required=True)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if platform.system() != "Linux" or platform.machine().lower() not in {"x86_64", "amd64"}:
        raise SystemExit("kokoro_benchmark_requires_linux_amd64")
    if not _IMAGE_DIGEST.fullmatch(args.worker_image_digest):
        raise SystemExit("kokoro_benchmark_worker_image_digest_invalid")
    for private_path in (
        args.corpus,
        args.scriptbook,
        args.candidate_lock,
        args.model_manifest,
        args.model_snapshot,
        args.espeak_runtime_manifest,
        args.espeak_runtime_root,
        args.private_output_root,
    ):
        _require_outside_repository(private_path)

    policy = BenchmarkPolicyV1.model_validate_json(args.policy.read_text(encoding="utf-8"))
    corpus = BenchmarkCorpusManifestV1.model_validate_json(args.corpus.read_text(encoding="utf-8"))
    scriptbook = _json(args.scriptbook)
    candidate = ProviderCandidateManifestV1.model_validate_json(
        args.candidate.read_text(encoding="utf-8")
    )
    inventory = ArtifactInventoryV1.model_validate_json(args.inventory.read_text(encoding="utf-8"))
    worker = load_worker_manifest(args.worker_manifest)
    if candidate.candidate_id != "kokoro-82m-stock" or candidate.status != "evaluation":
        raise SystemExit("kokoro_benchmark_candidate_must_remain_evaluation")
    if candidate.advertised_by_worker_manifest or worker.providers:
        raise SystemExit("kokoro_benchmark_pre_promotion_worker_must_be_unadvertised")
    if candidate.artifact_inventory_digest_sha256 != artifact_inventory_digest(inventory):
        raise SystemExit("kokoro_benchmark_inventory_binding_mismatch")
    if inventory.policy_digests_sha256 != [benchmark_policy_digest(policy)]:
        raise SystemExit("kokoro_benchmark_policy_inventory_mismatch")
    if worker.capability != "speech_cpu":
        raise SystemExit("kokoro_benchmark_worker_capability_mismatch")
    policy_candidate = next(
        (item for item in policy.candidates if item.candidate_id == candidate.candidate_id),
        None,
    )
    if policy_candidate is None:
        raise SystemExit("kokoro_benchmark_candidate_not_in_policy")

    lock_verification = verify_lock(args.candidate_lock)
    model_manifest = KokoroModelAssetManifestV1.model_validate_json(
        args.model_manifest.read_text(encoding="utf-8")
    )
    model_digest = verify_kokoro_model_snapshot(model_manifest, args.model_snapshot)
    espeak_manifest = EspeakRuntimeManifestV1.model_validate_json(
        args.espeak_runtime_manifest.read_text(encoding="utf-8")
    )
    espeak_runtime_digest = verify_espeak_runtime(
        espeak_manifest,
        args.espeak_runtime_root,
    )
    if os.getenv("HF_HUB_OFFLINE") != "1":
        raise SystemExit("kokoro_benchmark_hf_offline_required")
    if os.getenv("CLICKO_KOKORO_MODEL_REVISION") != model_manifest.source_revision:
        raise SystemExit("kokoro_benchmark_model_revision_environment_mismatch")
    if os.getenv("CLICKO_KOKORO_MODEL_DIGEST_SHA256", "").lower() != model_digest:
        raise SystemExit("kokoro_benchmark_model_digest_environment_mismatch")

    implementation_digest = hashlib.sha256(
        (ROOT / "backend/app/providers/studios/kokoro_stock.py").read_bytes()
    ).hexdigest()
    if candidate.code_digests_sha256 != {"kokoro-82m-stock": implementation_digest}:
        raise SystemExit("kokoro_benchmark_adapter_digest_mismatch")
    component_digests = _parse_component_digests(args.component_digest)
    if component_digests.get("kokoro-82m-weights") != model_digest:
        raise SystemExit("kokoro_benchmark_model_component_digest_mismatch")
    expected_espeak_revision = next(
        item.source_revision
        for item in policy_candidate.components
        if item.component_id == "espeak-ng-runtime"
    )
    _verify_espeak_runtime_binding(
        espeak_manifest,
        manifest_digest_sha256=espeak_runtime_digest,
        component_digests_sha256=component_digests,
        expected_source_revision=expected_espeak_revision,
    )

    run_id = args.run_id or f"kokoro-stock-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
    sink = PrivateSpeechBenchmarkEvidenceSink(
        args.private_output_root,
        run_id=run_id,
        forbidden_root=ROOT,
    )
    worker_manifest_digest = manifest_digest(worker)
    expected_model_revision = next(
        item.source_revision
        for item in policy_candidate.components
        if item.component_id == "kokoro-82m-weights"
    )
    if model_manifest.source_revision != expected_model_revision:
        raise SystemExit("kokoro_benchmark_model_policy_revision_mismatch")
    provider = KokoroStockVoiceProvider(
        KokoroStockConfig(
            source_revision=next(
                item.source_revision
                for item in policy_candidate.components
                if item.component_id == "kokoro-code"
            ),
            model_revision=model_manifest.source_revision,
            model_digest_sha256=model_digest,
            worker_manifest_digest_sha256=worker_manifest_digest,
            worker_image_digest=args.worker_image_digest,
            cpu_hourly_cost_usd=args.cpu_hourly_cost_usd,
        )
    )
    evaluator_digest = _evaluator_digest()
    artifacts = run_stock_voice_benchmark(
        policy=policy,
        corpus=corpus,
        scriptbook=scriptbook,
        candidate_id=candidate.candidate_id,
        voice_key=args.voice,
        provider=provider,
        evidence_sink=sink,
        environment=BenchmarkEnvironmentV1(
            worker_image_digest_sha256=args.worker_image_digest.removeprefix("sha256:"),
            dependency_lock_digest_sha256=lock_verification["lockDigestSha256"],
            operating_system=platform.platform(),
            architecture="amd64",
            cpu=_cpu_name(),
            ram_gb=_ram_gb(),
            accelerator="none",
            accelerator_memory_gb=0,
            isolated_tenant=args.attest_isolated_tenant,
            no_egress=args.attest_no_egress,
            ephemeral_workspace=args.attest_ephemeral_workspace,
            cleanup_mechanism_available=args.attest_cleanup_mechanism,
            cleanup_verified=False,
        ),
        component_digests_sha256=component_digests,
        run_id=run_id,
        bundle_id=f"{run_id}-evidence",
        bundle_asset_id=sink.evidence_bundle_asset_id("initial"),
        evaluator="clicko.stock-voice-runner.v1",
        evaluator_digest_sha256=evaluator_digest,
        peak_ram_sampler=_peak_ram_gb,
    )
    package = sink.persist_snapshot(artifacts, stage="initial")
    gate = evaluate_benchmark_run(
        policy,
        artifacts.run,
        corpus_manifest=corpus,
        evidence_bundle=artifacts.evidence_bundle,
    )
    print(
        json.dumps(
            {
                "automatedMeasurementCount": len(artifacts.run.measurements),
                "caseCount": artifacts.run.case_count,
                "decision": gate.decision,
                "evidenceBundleAssetId": package["evidenceBundleAssetId"],
                "packageManifestDigestSha256": package["packageManifestDigestSha256"],
                "providerAdvertised": False,
                "runId": run_id,
                "status": "retained-for-blinded-review",
            },
            sort_keys=True,
        )
    )
    return 2 if gate.decision == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
