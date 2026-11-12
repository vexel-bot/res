"""Record a finished external experiment, without dispatching inference or editing its origin."""
import argparse
import hashlib
import json
import math
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models import CreativeDocument, StudioGenerationJob


def main(directory, database, document_id):
    source = directory / "recibo.json"
    raw = source.read_bytes()
    receipt = json.loads(raw)
    cost = receipt["reportedCostUsd"]
    if (receipt["subtype"] != "error_max_budget_usd" or type(cost) not in {int, float}
            or not math.isfinite(cost) or cost < 0):
        raise ValueError("Expected the closed, budget-exhausted independent experiment receipt")
    digest = hashlib.sha256(raw).hexdigest()
    engine = create_engine("sqlite:///" + database.resolve().as_posix())
    key = "orbita-independent-20261112"
    with Session(engine) as db:
        origin = db.get(CreativeDocument, document_id)
        if origin is None:
            raise ValueError("Reference project not found")
        job = db.scalar(select(StudioGenerationJob).where(
            StudioGenerationJob.workspace_id == origin.workspace_id,
            StudioGenerationJob.job_type == "agent_plan", StudioGenerationJob.idempotency_key == key,
        ))
        if job:
            if job.payload_hash != digest:
                raise ValueError("External receipt conflicts with the recorded experiment")
            if not (job.result_payload or {}).get("editorial"):
                job.result_payload = {**job.result_payload, "editorial": {"format": "motion"}}
                db.commit()
        else:
            previous = db.scalar(select(StudioGenerationJob).where(
                StudioGenerationJob.workspace_id == origin.workspace_id,
                StudioGenerationJob.requested_by == origin.created_by,
            ).order_by(StudioGenerationJob.created_at.desc()))
            scope = (previous.request_payload.get("billingScope") if previous else None) or {
                "workspaceId": origin.workspace_id, "userId": origin.created_by,
            }
            job = StudioGenerationJob(
                workspace_id=origin.workspace_id, document_id=origin.id, requested_by=origin.created_by,
                job_type="agent_plan", provider="llm.anthropic", idempotency_key=key, payload_hash=digest,
                correlation_id=key, status="failed", progress=0, attempts=1, max_attempts=1,
                error_code="independent_budget_exhausted", error_message="External Claude Code session stopped before audio and export.",
                finished_at=datetime.now(UTC),
                request_payload={"model": receipt["model"], "billingScope": scope,
                                 "executionOrigin": "claude-code-independent", "externalRecordOnly": True,
                                 "requestedBudgetUsd": receipt["ceilingUsd"], "editorial": {"format": "motion"}},
                result_payload={"submissionStarted": True, "submissionOutcome": "response_received",
                                "measuredCostUsd": cost, "costSource": "claude-code-receipt-list-pricing",
                                "invoiceVerified": False, "externalReceiptSha256": digest,
                                "planningTimeMs": round(receipt["elapsedSeconds"] * 1000),
                                "modelUsage": receipt["modelUsage"], "usage": receipt["usage"],
                                "turnCount": receipt["turns"], "exportRequested": False,
                                "editorial": {"format": "motion"},
                                "manualRecovery": {"executor": "Codex", "apiSpendUsd": 0, "audio": "absent",
                                                   "source": "Unmodified Claude renderer; local frame render and FFmpeg encoding."}},
            )
            db.add(job)
            db.commit()
        result = {"jobId": job.id, "documentId": origin.id, "originRevision": origin.revision,
                  "costUsd": cost, "costSource": "claude-code-receipt-list-pricing", "invoiceVerified": False,
                  "receiptSha256": digest, "exportByOpus": False, "apiSpendDuringImportUsd": 0}
        (directory / "clicko-registro.json").write_text(json.dumps(result, indent=2), encoding="utf8")
        print(json.dumps(result))
    engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--document", required=True)
    args = parser.parse_args()
    if not args.database.is_file():
        raise ValueError("An existing Clicko development database is required")
    main(args.directory, args.database, args.document)
