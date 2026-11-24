"""Validate existing clone receipts; write lineage only with explicit --apply.

Uses the configured database. No model calls, render or edits to compositions.
All receipts must validate before any new relation is committed.
"""
import argparse
import json
import sys
from pathlib import Path


def link_receipts(db, receipts, apply=False):
    from app.models import CreativeDocument
    from app.services.studios.compatibility import record_to_contract
    from app.services.studios.craft_project_context import lineage, register_branch, state

    checks = []
    for receipt in receipts:
        child = db.get(CreativeDocument, receipt["documentId"])
        parent = db.get(CreativeDocument, receipt["sourceDocumentId"])
        if not child or not parent or child.workspace_id != parent.workspace_id:
            raise ValueError("craft_lineage_workspace_conflict")
        source = record_to_contract(parent)
        if (parent.revision != receipt["sourceRevision"] or not source.native_editor_state
                or source.native_editor_state.checksum_sha256 != receipt["sourceSha256"]
                or receipt.get("sourcePreserved") is not True):
            raise ValueError("craft_lineage_receipt_source_not_verified")
        relation = lineage(db, child)
        if relation["sourceDocumentId"]:
            if relation["sourceDocumentId"] != parent.id or relation["sourceRevision"] != parent.revision:
                raise ValueError("craft_lineage_existing_relation_conflict")
            checks.append((child, parent, "already_linked"))
        else:
            if state(db, child)[1]["version"]:
                raise ValueError("craft_lineage_existing_director_state_requires_reconciliation")
            checks.append((child, parent, "verified"))
    if apply:
        # Parent links before descendants, including arbitrarily ordered receipts.
        pending = [entry for entry in checks if entry[2] == "verified"]
        while pending:
            child_ids = {child.id for child, _, _ in pending}
            ready = [entry for entry in pending if entry[1].id not in child_ids]
            if not ready:
                raise ValueError("craft_lineage_receipt_cycle")
            for child, parent, _ in ready:
                register_branch(db, child, parent.id, parent.revision, "Verified existing clone receipt")
                pending.remove((child, parent, "verified"))
        db.commit()
    return [{"documentId": child.id, "sourceDocumentId": parent.id, "status": status,
             "applied": apply} for child, parent, status in checks]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipts", nargs="+", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
    from app.database import SessionLocal
    with SessionLocal() as db:
        try:
            result = link_receipts(db, [json.loads(p.read_text(encoding="utf-8-sig")) for p in args.receipts], args.apply)
        except Exception:
            db.rollback()
            raise
    print(json.dumps(result, indent=2))
