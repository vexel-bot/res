from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = BACKEND_ROOT.parent.resolve()
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.domain.studios.benchmarking import (  # noqa: E402
    BenchmarkCorpusManifestV1,
    BenchmarkPolicyV1,
    evaluate_voice_clone_corpus_admission,
)


def _require_outside_repository(path: Path, label: str) -> Path:
    resolved = path.resolve()
    if resolved == REPOSITORY_ROOT or resolved.is_relative_to(REPOSITORY_ROOT):
        raise ValueError(f"{label}_must_stay_outside_repository")
    return resolved


def validate_private_corpus(
    policy_path: Path,
    manifest_path: Path,
    report_path: Path,
) -> dict:
    private_manifest = _require_outside_repository(manifest_path, "private_manifest")
    private_report = _require_outside_repository(report_path, "private_report")
    policy = BenchmarkPolicyV1.model_validate_json(policy_path.read_text(encoding="utf-8"))
    manifest = BenchmarkCorpusManifestV1.model_validate_json(
        private_manifest.read_text(encoding="utf-8")
    )
    admission = evaluate_voice_clone_corpus_admission(policy, manifest)
    payload = admission.model_dump(mode="json", by_alias=True, exclude_none=True)
    private_report.parent.mkdir(parents=True, exist_ok=True)
    private_report.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate the consent-bound PT-BR voice-clone corpus and emit only a "
            "non-identifying admission report. The manifest and report must stay outside Git."
        )
    )
    parser.add_argument("policy", type=Path)
    parser.add_argument("private_manifest", type=Path)
    parser.add_argument("--report", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = validate_private_corpus(args.policy, args.private_manifest, args.report)
    except (OSError, ValueError) as exc:
        print(json.dumps({"decision": "rejected", "error": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(report, sort_keys=True))
    return 0 if report["decision"] == "ready" else 2


if __name__ == "__main__":
    raise SystemExit(main())
