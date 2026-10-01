from __future__ import annotations

import argparse
import base64
import json
import os
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
)
from app.domain.studios.speech_review import speech_review_plan_digest  # noqa: E402
from app.services.studios.speech_benchmark import (  # noqa: E402
    StockVoiceBenchmarkArtifacts,
)
from app.services.studios.speech_benchmark_storage import (  # noqa: E402
    PrivateSpeechBenchmarkEvidenceSink,
)
from app.services.studios.speech_review import build_blinded_review_plan  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY = ROOT / "benchmarks/studios/identity/voice-stock-pt-br-policy.v1.json"


def _require_outside_repository(path: Path) -> None:
    resolved = path.resolve()
    repository = ROOT.resolve()
    if resolved == repository or resolved.is_relative_to(repository):
        raise ValueError(f"private_speech_review_path_inside_repository:{path.name}")


def _load_initial_artifacts(private_root: Path) -> StockVoiceBenchmarkArtifacts:
    snapshot = private_root / "snapshots" / "initial"
    run = BenchmarkRunV1.model_validate_json(
        (snapshot / "benchmark-run.json").read_text(encoding="utf-8")
    )
    evidence_payload = json.loads((snapshot / "evidence-bundle.json").read_text(encoding="utf-8"))
    evidence_payload.pop("assetId", None)
    evidence = BenchmarkEvidenceBundleV1.model_validate(evidence_payload)
    return StockVoiceBenchmarkArtifacts(run=run, evidence_bundle=evidence)


def _blinding_secret() -> bytes:
    encoded = os.getenv("CLICKO_SPEECH_REVIEW_BLINDING_SECRET_B64", "")
    try:
        secret = base64.b64decode(encoded, validate=True)
    except ValueError as error:
        raise ValueError("speech_review_blinding_secret_base64_invalid") from error
    if len(secret) < 32:
        raise ValueError("speech_review_blinding_secret_too_short")
    return secret


def main() -> int:
    parser = argparse.ArgumentParser(description="Create three private blinded speech review packets.")
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--scriptbook", type=Path, required=True)
    parser.add_argument("--private-output-root", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--reviewer", action="append", required=True)
    parser.add_argument("--blinded-label", required=True)
    args = parser.parse_args()

    for private_path in (args.corpus, args.scriptbook, args.private_output_root):
        _require_outside_repository(private_path)

    policy = BenchmarkPolicyV1.model_validate_json(args.policy.read_text(encoding="utf-8"))
    corpus = BenchmarkCorpusManifestV1.model_validate_json(args.corpus.read_text(encoding="utf-8"))
    scriptbook = json.loads(args.scriptbook.read_text(encoding="utf-8"))
    artifacts = _load_initial_artifacts(args.private_output_root)
    sink = PrivateSpeechBenchmarkEvidenceSink.open_existing(
        args.private_output_root,
        run_id=args.run_id,
        forbidden_root=ROOT,
    )
    plan = build_blinded_review_plan(
        policy=policy,
        corpus=corpus,
        artifacts=artifacts,
        scriptbook=scriptbook,
        reviewer_pseudonyms=args.reviewer,
        blinded_candidate_label=args.blinded_label,
        blinding_secret=_blinding_secret(),
        generated_at=datetime.now(UTC),
    )
    stored = sink.persist_review_plan(plan)
    print(
        json.dumps(
            {
                "packetCount": stored["packetCount"],
                "packetIndexDigestSha256": stored["packetIndexDigestSha256"],
                "planAssetId": stored["planAssetId"],
                "planDigestSha256": speech_review_plan_digest(plan),
                "runId": plan.run_id,
                "status": "blinded-review-packets-ready",
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
