"""Read-only latest-plan comparison against persisted-event order in the owned lab."""
import hashlib
import json
import runpy
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/studios/research/editor-oss-20261002/inspection-latency"


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def main():
    target = OUT / "latest-plan-observation.json"
    if target.exists():
        raise ValueError("preserve_existing_observation")
    helper = runpy.run_path(str(ROOT / "scripts/validation/visual-distance-study.py"))
    token, workspace_id = helper["identity"]()
    from sqlalchemy import event, func, select
    from app.database import SessionLocal
    from app.models import CreativeDocument, StudioDomainEvent as E
    from app.domain.studios.contextual_editing_v2 import parse_editing_plan
    from app.services.studios.contextual_editing import PLAN_EVENT, latest_plan

    execution = json.loads((ROOT / "output/visual-directed-native14-20261004/execution.json").read_text(encoding="utf-8"))
    # Small scalar projection, including all workspace events. No historical JSON
    # hydration, and reference selection is performed in Python as before.
    with SessionLocal() as db:
        rows = db.execute(select(E.id, E.occurred_at, E.payload["plan"]["documentId"].as_string(),
                                 func.length(E.payload)).where(E.workspace_id == workspace_id,
                                 E.event_type == PLAN_EVENT).order_by(E.occurred_at, E.id)).all()
    before = [(r[0], r[1].isoformat(), r[2], r[3]) for r in rows]
    samples = []
    for name in ["organization-a", "comparison-a", "interface-a"]:
        study = execution["variants"][name]
        candidates = [r for r in rows if r[2] == study["documentId"]]
        assert candidates
        selected_id = candidates[-1][0]
        with SessionLocal() as db:
            raw = db.scalar(select(E.payload).where(E.id == selected_id))
            reference = parse_editing_plan(raw["plan"]).model_dump(mode="json", by_alias=True)
            reference_digest = digest(reference)
            del raw, reference
        loaded = []

        def on_load(instance, context):
            loaded.append(instance.id)

        event.listen(E, "load", on_load)
        try:
            with SessionLocal() as db:
                record = db.get(CreativeDocument, study["documentId"])
                assert record.workspace_id == workspace_id and record.revision == study["revision"] == 2
                started = time.perf_counter()
                current = latest_plan(db, record)
                compute_ms = (time.perf_counter() - started) * 1000
                current_digest = digest(current.model_dump(mode="json", by_alias=True))
                assert current_digest == reference_digest
                assert loaded == [selected_id]
                plan_id, revision = current.id, current.revision
                del current
        finally:
            event.remove(E, "load", on_load)
        request = Request("http://127.0.0.1:8000/api/v1/studios/v1/documents/" + study["documentId"] + "/editing-plans/latest",
                          headers={"Authorization": "Bearer " + token})
        started = time.perf_counter()
        with urlopen(request, timeout=60) as response:
            raw_response = response.read()
            status = response.status
        http_ms = (time.perf_counter() - started) * 1000
        value = json.loads(raw_response)
        assert status == 200 and digest(value) == reference_digest
        samples.append({"study": name, "documentId": study["documentId"], "selectedEventId": selected_id,
                        "planId": plan_id, "planRevision": revision, "hydratedEventIds": loaded,
                        "matchesPersistedOrderReference": True, "canonicalPlanDigest": current_digest,
                        "computeMs": compute_ms, "httpMs": http_ms, "httpStatus": status,
                        "responseBytes": len(raw_response), "selectedPayloadCharacters": candidates[-1][3]})
        del value, raw_response
        print(json.dumps({"study": name, "computeMs": round(compute_ms, 2), "httpMs": round(http_ms, 2)}), flush=True)
    with SessionLocal() as db:
        rows_after = db.execute(select(E.id, E.occurred_at, E.payload["plan"]["documentId"].as_string(),
                                      func.length(E.payload)).where(E.workspace_id == workspace_id,
                                      E.event_type == PLAN_EVENT).order_by(E.occurred_at, E.id)).all()
    after = [(r[0], r[1].isoformat(), r[2], r[3]) for r in rows_after]
    assert before == after
    target.write_text(json.dumps({"observedAt": datetime.now(timezone.utc).isoformat(),
        "scope": "Read-only three real latest-plan projections and direct API responses; no generation",
        "workspacePlanEvents": len(rows), "workspacePayloadCharacters": sum(r[3] for r in rows),
        "eventMetadataDigestBefore": digest(before), "eventMetadataDigestAfter": digest(after),
        "eventMetadataUnchanged": True, "samples": samples,
        "limits": ["No old full-workspace timing: memory cost avoided, no before/after speedup claimed",
                   "Reference streams SQL scalar document IDs, then validates only the selected full event",
                   "One sample per study, not p95 or browser concurrency benchmark",
                   "get_plan and full inspector response are unchanged; inspector latency not resolved"]},
        ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
