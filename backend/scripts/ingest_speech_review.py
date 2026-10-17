from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
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
from app.domain.studios.speech_review import (  # noqa: E402
    SpeechReviewPlanV1,
    SpeechReviewSubmissionV1,
)
from app.services.studios.speech_benchmark import (  # noqa: E402
    StockVoiceBenchmarkArtifacts,
)
from app.services.studios.speech_benchmark_storage import (  # noqa: E402
    PrivateSpeechBenchmarkEvidenceSink,
)
from app.services.studios.speech_review import append_blinded_review_evidence  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY = ROOT / "benchmarks/studios/identity/voice-stock-pt-br-policy.v1.json"


def _require_outside_repository(path: Path) -> None:
    resolved = path.resolve()
    repository = ROOT.resolve()
    if resolved == repository or resolved.is_relative_to(repository):
        raise ValueError(f"private_speech_review_path_inside_repository:{path.name}")


def _load_json_without_asset(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload.pop("assetId", None)
    return payload


def _evaluator_digest() -> str:
    digest = hashlib.sha256()
    for source in (
        ROOT / "backend/app/domain/studios/speech_review.py",
        ROOT / "backend/app/services/studios/speech_review.py",
    ):
        digest.update(hashlib.sha256(source.read_bytes()).digest())
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest three blinded speech review submissions.")
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--private-output-root", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--submission", type=Path, action="append", required=True)
    args = parser.parse_args()

    for private_path in (args.corpus, args.private_output_root, *args.submission):
        _require_outside_repository(private_path)

    policy = BenchmarkPolicyV1.model_validate_json(args.policy.read_text(encoding="utf-8"))
    corpus = BenchmarkCorpusManifestV1.model_validate_json(args.corpus.read_text(encoding="utf-8"))
    initial = args.private_output_root / "snapshots" / "initial"
    artifacts = StockVoiceBenchmarkArtifacts(
        run=BenchmarkRunV1.model_validate_json(
            (initial / "benchmark-run.json").read_text(encoding="utf-8")
        ),
        evidence_bundle=BenchmarkEvidenceBundleV1.model_validate(
            _load_json_without_asset(initial / "evidence-bundle.json")
        ),
    )
    plan = SpeechReviewPlanV1.model_validate(
        _load_json_without_asset(
            args.private_output_root / "review" / "organizer" / "review-plan.json"
        )
    )
    submissions = [
        SpeechReviewSubmissionV1.model_validate_json(path.read_text(encoding="utf-8"))
        for path in args.submission
    ]
    sink = PrivateSpeechBenchmarkEvidenceSink.open_existing(
        args.private_output_root,
        run_id=args.run_id,
        forbidden_root=ROOT,
    )
    reviewed, review_bundle = append_blinded_review_evidence(
        artifacts,
        policy,
        plan,
        submissions,
        review_bundle_id=f"{args.run_id}-blinded-review",
        review_bundle_asset_id=sink.review_bundle_asset_id(),
        evaluator="clicko.blinded-speech-review.v1",
        evaluator_digest_sha256=_evaluator_digest(),
        generated_at=datetime.now(UTC),
    )
    stored = sink.persist_review_result(review_bundle, reviewed)
    gate = evaluate_benchmark_run(
        policy,
        reviewed.run,
        corpus_manifest=corpus,
        evidence_bundle=reviewed.evidence_bundle,
    )
    print(
        json.dumps(
            {
                "decision": gate.decision,
                "missingMetrics": gate.missing_metrics,
                "packageManifestDigestSha256": stored["packageManifestDigestSha256"],
                "ratingCount": sum(len(item.responses) for item in submissions),
                "reviewBundleAssetId": stored["reviewBundleAssetId"],
                "runId": args.run_id,
                "status": "blinded-review-ingested-retain-audio-for-cleanup-stage",
            },
            sort_keys=True,
        )
    )
    return 2 if gate.decision == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
