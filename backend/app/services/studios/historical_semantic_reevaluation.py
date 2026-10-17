"""Re-evaluate stored renders without rewriting their historical receipts.

This module deliberately limits itself to evidence already bound to a stored
production.  Missing assertions become inconclusive; they are never inferred
from filenames, element labels, or pixel movement.
"""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

POLICY_VERSION = "studio.semantic-reevaluation.v1"


def _sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def reevaluate_production_snapshot(snapshot: dict[str, Any], source_checksum: str) -> dict[str, Any]:
    run = snapshot.get("run") or {}
    artifacts = run.get("artifacts") or {}
    plan = artifacts.get("plan") or {}
    direction = plan.get("direction") or {}
    audit = run.get("visualAudit") or {}
    old_gate = deepcopy((run.get("productionGates") or {}).get("observedResult"))
    rendered_checksum = audit.get("renderChecksum") or (
        ((artifacts.get("animatic") or {}).get("artifact") or {}).get("checksumSha256")
    )

    findings: list[dict[str, Any]] = []
    semantic_assertions = [
        assertion
        for scene in direction.get("scenes", [])
        for assertion in scene.get("semanticAssertions", [])
    ]
    content_references = direction.get("contentReferences", [])
    if direction.get("semanticVerificationPolicy") != "canonical_demonstration_v1":
        findings.append(
            {
                "code": "historical_semantic_policy_missing",
                "status": "inconclusive",
                "reason": "The stored direction predates the canonical demonstration policy.",
            }
        )
    if not semantic_assertions:
        findings.append(
            {
                "code": "historical_semantic_assertions_missing",
                "status": "inconclusive",
                "reason": "No falsifiable action assertions are bound to the stored scenes.",
            }
        )
    for scene in direction.get("scenes", []):
        indexed = {element.get("id"): element for element in scene.get("elements", [])}
        for composition in scene.get("compositions", []):
            if composition.get("family") != "format_transformation":
                continue
            targets = [indexed.get(target_id) or {} for target_id in composition.get("targetIds", [])]
            bound = {
                target.get("contentReferenceId") for target in targets if target.get("contentReferenceId")
            }
            if len(bound) != 1 or next(iter(bound), None) not in {
                reference.get("id") for reference in content_references
            }:
                findings.append(
                    {
                        "code": "historical_format_transformation_has_no_canonical_content",
                        "status": "failed",
                        "sceneId": scene.get("id"),
                        "compositionId": composition.get("id"),
                        "reason": (
                            "The stored targets do not carry one checksum-bound image/title/identity "
                            "reference through the format change."
                        ),
                    }
                )

    quality = ((artifacts.get("animatic") or {}).get("qualityEvaluation") or {})
    metrics = quality.get("metrics") or {}
    if float(metrics.get("silenceRatio") or 0) >= 0.99:
        findings.append(
            {
                "code": "historical_mix_is_silent",
                "status": "failed",
                "reason": "The decoded mix is silent for the full artifact.",
                "evidence": {
                    "silenceRatio": metrics.get("silenceRatio"),
                    "integratedLoudnessLufs": metrics.get("integratedLoudnessLufs"),
                    "truePeakDbfs": metrics.get("truePeakDbfs"),
                },
            }
        )

    execution_evidence = (audit.get("executionVerification") or audit.get("actionVerification") or {}).get(
        "evidence", []
    )
    execution_status = "observed" if execution_evidence and all(
        item.get("status") == "observed" for item in execution_evidence
    ) else "requires_review"
    semantic_status = "failed" if any(item["status"] == "failed" for item in findings) else "inconclusive"
    return {
        "schemaVersion": POLICY_VERSION,
        "evaluatedAt": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "source": {
            "pilot": snapshot.get("pilot"),
            "productionId": run.get("id"),
            "snapshotChecksumSha256": source_checksum,
            "renderChecksumSha256": rendered_checksum,
            "historicalReceiptPreserved": True,
        },
        "status": "requires_correction",
        "execution": {"status": execution_status, "evidence": execution_evidence},
        "semantic": {"status": semantic_status, "evidence": findings},
        "human": {"status": "pending", "evidence": []},
        "historicalObservedResult": old_gate,
        "limitations": [
            "This receipt does not retrofit assertions into the historical plan.",
            "Pixel change proves execution only; absent semantic evidence remains inconclusive.",
            "The source snapshot and historical gate are not modified.",
        ],
    }


def reevaluate_file(source: Path, destination: Path) -> dict[str, Any]:
    snapshot = json.loads(source.read_text(encoding="utf-8"))
    receipt = reevaluate_production_snapshot(snapshot, _sha256(source))
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return receipt
