from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.domain.studios.benchmarking import (  # noqa: E402
    BenchmarkCorpusManifestV1,
    BenchmarkEvidenceBundleV1,
    BenchmarkPolicyV1,
    BenchmarkRunV1,
    evaluate_benchmark_run,
)
from app.services.studios.speech_benchmark import (  # noqa: E402
    StockVoiceBenchmarkArtifacts,
    append_cleanup_evidence,
)
from app.services.studios.speech_benchmark_storage import (  # noqa: E402
    PrivateSpeechBenchmarkEvidenceSink,
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY = ROOT / "benchmarks/studios/identity/voice-stock-pt-br-policy.v1.json"
_HUMAN_METRICS = {
    "human_naturalness_mos",
    "pt_br_intelligibility_word_accuracy",
    "critical_term_accuracy",
    "critical_off_script_rate",
    "repeat_or_truncation_rate",
}


def _require_outside_repository(path: Path) -> None:
    resolved = path.resolve()
    repository = ROOT.resolve()
    if resolved == repository or resolved.is_relative_to(repository):
        raise ValueError(f"private_speech_cleanup_path_inside_repository:{path.name}")


def _load_post_review(private_root: Path) -> StockVoiceBenchmarkArtifacts:
    snapshot = private_root / "snapshots" / "post-review"
    run = BenchmarkRunV1.model_validate_json(
        (snapshot / "benchmark-run.json").read_text(encoding="utf-8")
    )
    payload = json.loads((snapshot / "evidence-bundle.json").read_text(encoding="utf-8"))
    payload.pop("assetId", None)
    return StockVoiceBenchmarkArtifacts(
        run=run,
        evidence_bundle=BenchmarkEvidenceBundleV1.model_validate(payload),
    )


def _evaluator_digest() -> str:
    digest = hashlib.sha256()
    for source in (
        ROOT / "backend/app/domain/studios/benchmarking.py",
        ROOT / "backend/app/services/studios/speech_benchmark.py",
        ROOT / "backend/app/services/studios/speech_benchmark_storage.py",
    ):
        digest.update(hashlib.sha256(source.read_bytes()).digest())
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Delete retained review WAVs and attach per-case cleanup evidence."
    )
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--private-output-root", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    _require_outside_repository(args.corpus)
    _require_outside_repository(args.private_output_root)

    policy = BenchmarkPolicyV1.model_validate_json(args.policy.read_text(encoding="utf-8"))
    corpus = BenchmarkCorpusManifestV1.model_validate_json(args.corpus.read_text(encoding="utf-8"))
    reviewed = _load_post_review(args.private_output_root)
    measurement_ids = {item.metric_id for item in reviewed.run.measurements}
    if (
        reviewed.run.controls.get("human_review_completed") is not True
        or "blinded_human_review" not in reviewed.run.evidence_refs
        or not _HUMAN_METRICS.issubset(measurement_ids)
    ):
        raise SystemExit("speech_cleanup_requires_complete_persisted_blinded_review")

    sink = PrivateSpeechBenchmarkEvidenceSink.open_existing(
        args.private_output_root,
        run_id=args.run_id,
        forbidden_root=ROOT,
    )
    receipt_path = sink.root / "receipts" / "cleanup-bundle.json"
    if receipt_path.exists():
        cleanup_asset_id, cleanup = sink.load_cleanup_bundle()
    else:
        cleanup_asset_id, cleanup = sink.finalize_audio_cleanup(
            reviewed.evidence_bundle,
            cleanup_bundle_id=f"{args.run_id}-cleanup",
        )
    finalized = append_cleanup_evidence(
        reviewed,
        cleanup,
        cleanup_asset_id=cleanup_asset_id,
        evaluator="clicko.stock-cleanup.v1",
        evaluator_digest_sha256=_evaluator_digest(),
    )
    snapshot = sink.persist_snapshot(finalized, stage="post-cleanup")
    gate = evaluate_benchmark_run(
        policy,
        finalized.run,
        corpus_manifest=corpus,
        evidence_bundle=finalized.evidence_bundle,
    )
    verified = sum(1 for item in cleanup.cases if item.verified_absent)
    print(
        json.dumps(
            {
                "caseCount": len(cleanup.cases),
                "cleanupReceiptAssetId": cleanup_asset_id,
                "decision": gate.decision,
                "missingMetrics": gate.missing_metrics,
                "packageManifestDigestSha256": snapshot[
                    "packageManifestDigestSha256"
                ],
                "runId": args.run_id,
                "status": "cleanup-finalized",
                "verifiedAbsentCount": verified,
            },
            sort_keys=True,
        )
    )
    return 2 if gate.decision == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
