"""Run the bounded 2-prompt x 3-seed local diffusion qualification matrix."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import time
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import httpx


PROMPTS = (
    (
        "single-object-motion",
        "One small blue toy car moves steadily from left to right across a plain light floor, "
        "locked camera, centered medium shot, one recognizable object, one observable action, "
        "clean background, no text, no logo, no watermark",
    ),
    (
        "destination-motion",
        "One red paper airplane glides toward one open cardboard mailbox and stops at the destination, "
        "locked camera, centered medium shot, simple neutral background, coherent temporal motion, "
        "no text, no logo, no watermark",
    ),
)
SEEDS = (20260911, 20260912, 20260913)


def run(
    base_url: str,
    token: str,
    output: Path,
    profile_id: str,
    maximum_samples: int | None = None,
) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    matrix = []
    planned_samples = min(
        len(PROMPTS) * len(SEEDS),
        maximum_samples if maximum_samples is not None else len(PROMPTS) * len(SEEDS),
    )
    headers = {"Authorization": "Bearer " + token}
    with httpx.Client(base_url=base_url.rstrip("/"), headers=headers, timeout=30) as client:
        capabilities = client.get("/api/v1/capabilities")
        capabilities.raise_for_status()
        selected = next(
            (item for item in capabilities.json()["profiles"] if item["profileId"] == profile_id),
            None,
        )
        if not selected or not selected.get("usableNow"):
            result = {
                "schemaVersion": "res.local-video-qualification-suite.v1",
                "profileId": profile_id,
                "status": "blocked_resources",
                "capability": selected,
                "matrix": [],
            }
            (output / "suite-receipt.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
            return result
        for prompt_id, prompt in PROMPTS:
            for seed in SEEDS:
                if len(matrix) >= planned_samples:
                    break
                suite_id = output.resolve().name
                execution_id = str(
                    uuid5(
                        NAMESPACE_URL,
                        f"res:local-video-qualification:{suite_id}:{profile_id}:{prompt_id}:{seed}",
                    )
                )
                payload = {
                    "schemaVersion": "studio.scene-generation-request.v2",
                    "operation": "text_to_video",
                    "prompt": prompt,
                    "seed": seed,
                    "durationSeconds": 1,
                    "profileId": profile_id,
                    "cameraIntent": {"type": "static", "control": "prompt_guidance"},
                    "executionId": execution_id,
                }
                submitted = client.post("/api/v1/generate-scene", json=payload)
                if submitted.status_code == 409:
                    receipt = submitted.json().get("detail", submitted.json())
                else:
                    submitted.raise_for_status()
                    receipt = submitted.json()
                    deadline = time.monotonic() + 1800
                    while receipt.get("status") == "running" and time.monotonic() < deadline:
                        time.sleep(5)
                        response = client.get(f"/api/v1/executions/{execution_id}")
                        response.raise_for_status()
                        receipt = response.json()
                    if receipt.get("status") == "running":
                        client.post(f"/api/v1/executions/{execution_id}/cancel")
                        receipt = {"executionId": execution_id, "status": "deadline_exceeded"}
                artifact = receipt.get("artifact") or {}
                source_path = Path(artifact.get("path", "")) if artifact.get("path") else None
                if (
                    receipt.get("status") in {"candidate_generated", "content_flagged"}
                    and source_path
                    and source_path.is_file()
                ):
                    checksum = hashlib.sha256(source_path.read_bytes()).hexdigest()
                    if checksum != artifact.get("checksumSha256"):
                        raise ValueError("qualification_artifact_checksum_mismatch")
                    preserved = output / f"{prompt_id}-{seed}.mp4"
                    shutil.copy2(source_path, preserved)
                    artifact = {
                        **artifact,
                        "preservedPath": str(preserved.resolve()),
                    }
                    receipt = {**receipt, "artifact": artifact}
                record = {"promptId": prompt_id, "prompt": prompt, "seed": seed, "receipt": receipt}
                matrix.append(record)
                (output / f"{prompt_id}-{seed}.json").write_text(
                    json.dumps(record, indent=2), encoding="utf-8"
                )
                if receipt.get("status") in {"blocked_resources", "model_unavailable"}:
                    break
            if matrix and matrix[-1]["receipt"].get("status") in {"blocked_resources", "model_unavailable"}:
                break
            if len(matrix) >= planned_samples:
                break
    result = {
        "schemaVersion": "res.local-video-qualification-suite.v1",
        "profileId": profile_id,
        "status": (
            "awaiting_visual_review"
            if len(matrix) == planned_samples
            and all(item["receipt"].get("status") == "candidate_generated" for item in matrix)
            else "awaiting_content_and_visual_review"
            if len(matrix) == planned_samples
            and all(
                item["receipt"].get("status") in {"candidate_generated", "content_flagged"}
                for item in matrix
            )
            else "partial_blocked_resources"
            if any(item["receipt"].get("status") in {"blocked_resources", "model_unavailable"} for item in matrix)
            and any(item["receipt"].get("status") == "candidate_generated" for item in matrix)
            else "blocked_resources"
            if any(item["receipt"].get("status") in {"blocked_resources", "model_unavailable"} for item in matrix)
            else "failed"
        ),
        "matrix": matrix,
        "plannedSamples": planned_samples,
        "automaticQualification": False,
    }
    (output / "suite-receipt.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8094")
    parser.add_argument("--profile-id", default="animatediff-lightning-sd15-a-v1")
    parser.add_argument("--output", required=True)
    parser.add_argument("--maximum-samples", type=int)
    args = parser.parse_args()
    secret = os.environ.get("RES_LOCAL_DIFFUSION_TOKEN", "")
    if len(secret) < 32:
        raise SystemExit("RES_LOCAL_DIFFUSION_TOKEN is required")
    print(
        json.dumps(
            run(
                args.base_url,
                secret,
                Path(args.output),
                args.profile_id,
                max(1, args.maximum_samples) if args.maximum_samples is not None else None,
            ),
            separators=(",", ":"),
        )
    )
