"""Read-only reconciliation of real Clicko jobs; no credentials or provider calls."""

import argparse
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path


def audit(database):
    db = sqlite3.connect(
        f"file:{Path(database).resolve().as_posix()}?mode=ro", uri=True
    )
    db.row_factory = sqlite3.Row
    connections = {
        r["id"]: json.loads(r["config"])
        for r in db.execute(
            "SELECT id,config FROM studio_llm_connections WHERE provider='anthropic'"
        )
    }
    rows, all_holds = [], {}
    baseline = {
        "67a02e36-f2fd-4817-997b-2fd48cdc17c6",
        "91a6f563-feb1-4fea-91c0-46a8c7710740",
        "b2d17b62-65c9-4a8d-b0f7-0b7c1b30e3bf",
        "23991a26-6d55-4595-926d-660d8140786e",
    }
    motion_documents = {
        "328b3cc3-82e0-4edf-843c-37bef49ca224",
        "b5dd171f-5360-41d1-9e8e-3faed872ba5c",
        "37415d68-14b7-4505-a80c-61684f8c663c",
    }
    for row in db.execute("SELECT * FROM studio_generation_jobs ORDER BY created_at"):
        request, result = (
            json.loads(row["request"] or "{}"),
            json.loads(row["result"] or "{}"),
        )
        submitted = bool(result.get("submissionStarted"))
        hold = max(
            float(result.get(k) or 0)
            for k in (
                "financialReservationUsd",
                "testReservationUsd",
                "llmReservationUsd",
            )
        )
        if not submitted and row["status"] in ("failed", "cancelled"):
            hold = 0
            committed = 0
        elif (
            result.get("preflightFailure")
            and result.get("submissionOutcome") == "rejected"
        ):
            committed = 0
        else:
            committed = max(
                hold,
                float(result.get("providerReportedCostUsd") or 0),
                float(
                    result.get("estimatedCostUsd", result.get("measuredCostUsd")) or 0
                ),
            )
        all_holds[request.get("model", "unknown")] = (
            all_holds.get(request.get("model", "unknown"), 0) + committed
        )
        if (
            row["provider"] != "llm.anthropic"
            and request.get("llmConnectionId") not in connections
        ):
            continue
        cost = result.get("providerReportedCostUsd")
        if cost is None:
            cost = result.get("measuredCostUsd")
        editorial = result.get("editorial", {})
        envelope = (
            "baseline"
            if row["id"] in baseline
            else "motion"
            if editorial.get("format") == "motion"
            or row["document_id"] in motion_documents
            else "editing"
        )
        rows.append(
            {
                "id": row["id"],
                "documentId": row["document_id"],
                "createdAt": row["created_at"],
                "status": row["status"],
                "state": result.get("state"),
                "model": request.get("model"),
                "submitted": submitted,
                "submissionOutcome": result.get("submissionOutcome"),
                "measuredCostUsd": cost,
                "uncertainCostUpperBoundUsd": float(result.get("uncertainCostUpperBoundUsd") or 0),
                "hasPendingTurn": bool(result.get("pendingTurnBudget")),
                "reservationUsd": hold,
                "errorCode": row["error_code"],
                "planningTimeMs": result.get("planningTimeMs"),
                "humanVerdict": editorial.get("humanVerdict"),
                "stageCount": len(result.get("directionUsage", [])) or int(submitted),
                "envelope": envelope,
                "source": "durable_generation_job",
                "appliedDoesNotMeanApproved": True,
            }
        )
    known = round(sum(float(row["measuredCostUsd"] or 0) for row in rows), 8)
    unknown = [
        r["id"]
        for r in rows
        if r["submitted"]
        and (
            r["submissionOutcome"] != "response_received"
            or r["measuredCostUsd"] is None
            or r["uncertainCostUpperBoundUsd"] > 0
            or r["hasPendingTurn"]
        )
    ]
    approved = [r for r in rows if r["humanVerdict"] == "approved"]
    judged = [
        r
        for r in rows
        if r["humanVerdict"] in ("approved", "needs_revision", "rejected")
    ]
    submitted = [r for r in rows if r["submitted"]]
    envelopes = {
        "baseline": 10,
        "editing": 70,
        "motion": 20,
        "long": 0,
        "pilot": 50,
        "reserve": 50,
    }
    report = {
        "schemaVersion": "clicko.capital-audit.v1",
        "generatedAt": datetime.now(UTC).isoformat(),
        "creditReportedByUserUsd": 200,
        "providerBalanceReconciled": False,
        "knownAnthropicCostUsd": known,
        "estimatedCreditRemainingUsd": round(200 - known, 8),
        "remainingEstimateExcludesUncertainCharges": True,
        "recordedUncertainCostUpperBoundUsd": round(sum(r["uncertainCostUpperBoundUsd"] for r in rows), 8),
        "directReservationUsd": round(sum(r["reservationUsd"] for r in rows), 8),
        "unknownSubmissionIds": unknown,
        "allProviderCommitmentsByModelUsd": all_holds,
        "planSource": "output/plano-api-claude-2026-11-07/parecer-conselho.md",
        "envelopeAttribution": "Historical classification by recorded experiment/format; not provider billing categories.",
        "envelopes": {
            key: {
                "plannedUsd": amount,
                "measuredUsd": round(
                    sum(
                        float(r["measuredCostUsd"] or 0)
                        for r in rows
                        if r["envelope"] == key
                    ),
                    8,
                ),
            }
            for key, amount in envelopes.items()
        },
        "indicators": {
            "submittedPaidJobs": len(submitted),
            "submittedPaidStages": sum(r["stageCount"] for r in submitted),
            "paidJobFailures": sum(r["status"] == "failed" for r in submitted),
            "formalApproved": len(approved),
            "formalJudged": len(judged),
            "approvalRate": len(approved) / len(judged) if judged else None,
            "costPerApprovedUsd": known / len(approved) if approved else None,
            "timeToApprovalMs": None,
            "firstVersionApprovalRate": None,
            "audienceComprehension": None,
            "pilotRepeatUse": "not_evaluated_current_focus_is_video_quality",
        },
        "jobs": rows,
    }
    db.close()
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--database", default=".codex-runtime/clicko-dev/studios/records.sqlite"
    )
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = audit(args.database)
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                k: result[k]
                for k in (
                    "knownAnthropicCostUsd",
                    "estimatedCreditRemainingUsd",
                    "indicators",
                    "unknownSubmissionIds",
                    "envelopes",
                    "allProviderCommitmentsByModelUsd",
                )
            },
            ensure_ascii=False,
        )
    )
