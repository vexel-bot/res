"""Read-only cold/warm validation comparison and current HTTP response parity."""
import ast
import hashlib
import json
import runpy
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/studios/research/editor-oss-20261002/plan-history-validation"


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def main():
    target = OUT / "observation.json"
    if target.exists():
        raise ValueError("preserve_existing_observation")
    helper = runpy.run_path(str(ROOT / "scripts/validation/visual-distance-study.py"))
    token, workspace_id = helper["identity"]()
    from app.database import SessionLocal
    from app.services.studios import contextual_editing as plans
    from app.services.studios import editing_plan_validation as validation

    execution = json.loads((ROOT / "output/visual-directed-native14-20261004/execution.json").read_text(encoding="utf-8"))
    original_parser = plans.parse_editing_plan
    parser_calls = []

    def counted(raw):
        parser_calls.append(raw.get("revision", 1))
        return original_parser(raw)

    # Compile only the backed-up function with isolated globals, not the full
    # service module: no code/module replacement in the running API or writes.
    tree = ast.parse((OUT / "contextual_editing.py.before").read_text(encoding="utf-8"))
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "get_plan")
    scope = {**plans.__dict__, "parse_editing_plan": counted}
    exec(compile(ast.Module(body=[function], type_ignores=[]), "backed_up_get_plan", "exec"), scope)
    legacy = scope["get_plan"]
    samples = []
    plans.parse_editing_plan = counted
    try:
        for name in ["organization-a", "comparison-a", "interface-a"]:
            study = execution["variants"][name]
            modes = []
            reference_digest = None
            validation._validated_revisions.clear()
            for mode in ["legacy", "cold", "warm"]:
                parser_calls.clear()
                with SessionLocal() as db:
                    started = time.perf_counter()
                    current = (legacy if mode == "legacy" else plans.get_plan)(db, workspace_id, study["planId"])
                    elapsed = (time.perf_counter() - started) * 1000
                    value = current.model_dump(mode="json", by_alias=True)
                    current_digest = digest(value)
                    assert value["documentId"] == study["documentId"] and value["documentRevision"] == 2
                    if reference_digest is None:
                        reference_digest = current_digest
                    assert current_digest == reference_digest
                    modes.append({"mode": mode, "getPlanMs": elapsed, "parserCalls": len(parser_calls),
                                  "canonicalPlanDigest": current_digest,
                                  "validationFactCount": len(validation._validated_revisions._entries)})
                    del current, value
                print(json.dumps({"study": name, "mode": mode, "getPlanMs": round(elapsed, 2),
                                  "parserCalls": len(parser_calls)}), flush=True)
            samples.append({"study": name, "planId": study["planId"], "documentId": study["documentId"],
                            "allModesEqual": True, "modes": modes})
    finally:
        plans.parse_editing_plan = original_parser
        validation._validated_revisions.clear()
    prior = json.loads((OUT.parent / "inspection-response/http-parity.json").read_text(encoding="utf-8"))
    document_id = execution["variants"]["interface-a"]["documentId"]
    wire = []
    for frame in [0, 244, 449]:
        path = f"/api/v1/studios/v1/documents/{document_id}/editor/inspection?frame={frame}&evaluationDetail=summary"
        started = time.perf_counter()
        with urlopen(Request("http://127.0.0.1:8000" + path, headers={"Authorization": "Bearer " + token}), timeout=60) as response:
            raw = response.read()
            status = response.status
        elapsed = (time.perf_counter() - started) * 1000
        value = json.loads(raw)
        current_digest = digest(value)
        expected = next(s for s in prior["samples"] if s["frame"] == frame)["wire"]["summary"]["canonicalJsonDigest"]
        assert status == 200 and current_digest == expected
        wire.append({"frame": frame, "status": status, "completeBodyMs": elapsed, "bytes": len(raw),
                     "canonicalJsonDigest": current_digest, "matchesPreviousSummary": True})
        print(json.dumps({"frame": frame, "httpMs": round(elapsed, 2), "matchesPreviousSummary": True}), flush=True)
    target.write_text(json.dumps({"observedAt": datetime.now(timezone.utc).isoformat(),
        "scope": "Three real plan histories, legacy/cold/warm in a separate process, three direct summary API responses",
        "samples": samples, "http": wire,
        "limits": ["One ordered legacy/cold/warm comparison per study; not randomized or p95",
                   "Cache facts are cleared per study in the separate diagnostic process, not in the API process",
                   "Timings exclude model serialization and digest; HTTP includes response transfer",
                   "No historical event mutations, renders or paid calls; no realtime claim",
                   "Cast-to-string tested on local SQLite; PostgreSQL execution not demonstrated"]}, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
