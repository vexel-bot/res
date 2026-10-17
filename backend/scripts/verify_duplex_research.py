"""Verify frozen duplex research without downloading or activating model weights."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from app.domain.studios.artifacts import ArtifactInventoryV1


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SystemExit(f"duplex_research_json_unreadable:{path.name}") from error
    if not isinstance(value, dict):
        raise SystemExit(f"duplex_research_json_object_required:{path.name}")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(
    alternatives_path: Path,
    qwen_path: Path,
    personaplex_path: Path,
    speech_manifest_path: Path,
) -> dict[str, Any]:
    alternatives = _load(alternatives_path)
    qwen = _load(qwen_path)
    personaplex = ArtifactInventoryV1.model_validate(_load(personaplex_path))
    speech_manifest = _load(speech_manifest_path)

    if alternatives.get("schema_version") != "studio.duplex-alternatives-research.v1":
        raise SystemExit("duplex_research_schema_invalid")
    if alternatives.get("policy") != "open-source-only-strict":
        raise SystemExit("duplex_research_policy_not_strict")
    if alternatives.get("runtime_authorized") is not False:
        raise SystemExit("duplex_research_runtime_must_remain_disabled")
    if alternatives.get("weights_downloaded") is not False:
        raise SystemExit("duplex_research_weights_must_remain_absent")
    if alternatives.get("providers_enabled") != []:
        raise SystemExit("duplex_research_provider_enabled")

    candidates = alternatives.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise SystemExit("duplex_research_candidates_missing")
    candidate_ids = [item.get("id") for item in candidates if isinstance(item, dict)]
    if len(candidate_ids) != len(candidates) or len(candidate_ids) != len(
        set(candidate_ids)
    ):
        raise SystemExit("duplex_research_candidate_ids_invalid")
    qwen_candidate = next(
        (item for item in candidates if item["id"] == qwen.get("candidateId")),
        None,
    )
    if qwen_candidate is None:
        raise SystemExit("duplex_research_qwen_candidate_missing")
    if qwen_candidate.get("artifact_manifest_digest_sha256") != _sha256(qwen_path):
        raise SystemExit("duplex_research_qwen_manifest_binding_mismatch")

    if qwen.get("schemaVersion") != "studio.external-model-vendor-manifest.v1":
        raise SystemExit("duplex_research_qwen_schema_invalid")
    if qwen.get("runtimeAuthorized") is not False:
        raise SystemExit("duplex_research_qwen_runtime_authorized")
    if qwen.get("weightsDownloaded") is not False:
        raise SystemExit("duplex_research_qwen_weights_downloaded")
    if qwen.get("providersEnabled") != []:
        raise SystemExit("duplex_research_qwen_provider_enabled")
    model = qwen.get("model", {})
    if (
        model.get("declaredLicense") != "other"
        or model.get("licenseFilePresent") is not False
        or model.get("licenseDecision") != "review_required"
    ):
        raise SystemExit("duplex_research_qwen_license_gate_invalid")
    files = qwen.get("files")
    if not isinstance(files, list) or len(files) != 25:
        raise SystemExit("duplex_research_qwen_file_inventory_incomplete")
    paths = [item.get("path") for item in files if isinstance(item, dict)]
    if len(paths) != len(files) or len(paths) != len(set(paths)):
        raise SystemExit("duplex_research_qwen_file_paths_invalid")
    for item in files:
        digest = item.get("sha256")
        if (
            not isinstance(digest, str)
            or len(digest) != 64
            or any(char not in "0123456789abcdef" for char in digest)
            or item.get("downloaded") is not False
        ):
            raise SystemExit("duplex_research_qwen_file_evidence_invalid")
    weights = [item for item in files if item.get("kind") == "weight"]
    if len(weights) != 15 or sum(item["sizeBytes"] for item in weights) != qwen.get(
        "totalWeightBytes"
    ):
        raise SystemExit("duplex_research_qwen_weight_inventory_invalid")

    if personaplex.status != "rejected":
        raise SystemExit("duplex_research_personaplex_must_remain_rejected")
    personaplex_weights = next(
        item
        for item in personaplex.artifacts
        if item.artifact_id == "personaplex-7b-v1-weights"
    )
    if (
        personaplex_weights.resolution_status != "rejected"
        or personaplex_weights.integrity is not None
    ):
        raise SystemExit("duplex_research_personaplex_weights_present")
    if speech_manifest.get("providers") != []:
        raise SystemExit("duplex_research_speech_provider_enabled")

    return {
        "candidateCount": len(candidates),
        "personaplexDecision": "rejected",
        "providersEnabled": [],
        "qwenLicenseDecision": "review_required",
        "qwenWeightBytesDownloaded": 0,
        "qwenWeightFileCount": len(weights),
        "status": "duplex-research-gates-verified",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--alternatives", type=Path, required=True)
    parser.add_argument("--qwen", type=Path, required=True)
    parser.add_argument("--personaplex", type=Path, required=True)
    parser.add_argument("--speech-manifest", type=Path, required=True)
    args = parser.parse_args()
    result = verify(
        args.alternatives,
        args.qwen,
        args.personaplex,
        args.speech_manifest,
    )
    print(json.dumps(result, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
