"""Read-only local inspector profiling on the existing isolated study identity."""
import argparse
import cProfile
import hashlib
import json
import pstats
import runpy
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/studios/research/editor-oss-20261002/inspection-latency"


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--study", choices=["organization-a", "comparison-a", "interface-a"], default="interface-a")
    args = parser.parse_args()
    target = OUT / (args.study + "-profile.json")
    if target.exists():
        raise ValueError("preserve_existing_profile")
    helper = runpy.run_path(str(ROOT / "scripts/validation/visual-distance-study.py"))
    token, workspace_id = helper["identity"]()
    from sqlalchemy import event, select
    from app.database import SessionLocal, engine
    from app.models import User
    from app.routers.studios import owned_document
    from app.services.studios.editor_commands import inspect_editor

    execution = json.loads((ROOT / "output/visual-directed-native14-20261004/execution.json").read_text(encoding="utf-8"))
    study = execution["variants"][args.study]
    document_id = study["documentId"]
    rounds, sql_calls = [], []

    def before_sql(connection, cursor, statement, parameters, context, executemany):
        context._study_sql_start = time.perf_counter()

    def after_sql(connection, cursor, statement, parameters, context, executemany):
        # Record no SQL text, params, auth values, or connection strings.
        sql_calls.append({"operation": statement.lstrip().split(None, 1)[0],
                          "durationMs": (time.perf_counter() - context._study_sql_start) * 1000})

    profiler = cProfile.Profile()
    event.listen(engine, "before_cursor_execute", before_sql)
    event.listen(engine, "after_cursor_execute", after_sql)
    try:
        for frame in [0, 244, 449]:
            sql_start = len(sql_calls)
            with SessionLocal() as db:
                user = db.scalar(select(User).where(User.email == "motion-study-20261001@example.com"))
                started = time.perf_counter()
                record = owned_document(db, user.id, document_id)
                ownership_ms = (time.perf_counter() - started) * 1000
                assert record.workspace_id == workspace_id
                started = time.perf_counter()
                profiler.enable()
                try:
                    value = inspect_editor(db, record, frame)
                finally:
                    profiler.disable()
                inspect_ms = (time.perf_counter() - started) * 1000
                assert value["document"]["revision"] == study["revision"] == 2
                assert value["frame"] == frame and value["durationFrames"] == 450
                started = time.perf_counter()
                encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()
                encode_ms = (time.perf_counter() - started) * 1000
                local_digest = digest(value)
            wire = []
            for origin in ["http://127.0.0.1:8000", "http://127.0.0.1:3000"]:
                path = f"/api/v1/studios/v1/documents/{document_id}/editor/inspection?frame={frame}"
                request = Request(origin + path, headers={"Authorization": "Bearer " + token})
                started = time.perf_counter()
                with urlopen(request, timeout=60) as response:
                    headers_ms = (time.perf_counter() - started) * 1000
                    raw = response.read()
                    status = response.status
                transfer_ms = (time.perf_counter() - started) * 1000
                started = time.perf_counter()
                received = json.loads(raw)
                parse_ms = (time.perf_counter() - started) * 1000
                assert status == 200 and digest(received) == local_digest
                wire.append({"origin": origin, "status": status, "headersMs": headers_ms,
                             "completeBodyMs": transfer_ms, "jsonParseMs": parse_ms, "bytes": len(raw),
                             "canonicalJsonDigest": local_digest, "matchesLocalInspection": True})
            rounds.append({"frame": frame, "ownershipMs": ownership_ms, "inspectionMsWithCProfile": inspect_ms,
                           "jsonEncodeMs": encode_ms, "localBytes": len(encoded), "sql": sql_calls[sql_start:],
                           "nodes": len(value["nodes"]), "tracks": len(value["tracks"]), "http": wire})
            print(json.dumps({"study": args.study, "frame": frame, "inspectionMs": round(inspect_ms, 2),
                              "httpMs": [round(w["completeBodyMs"], 2) for w in wire]}), flush=True)
    finally:
        event.remove(engine, "before_cursor_execute", before_sql)
        event.remove(engine, "after_cursor_execute", after_sql)
    stats = pstats.Stats(profiler)
    functions = []
    for (filename, line, name), (primitive, calls, internal, cumulative, callers) in sorted(stats.stats.items(), key=lambda item: item[1][3], reverse=True)[:40]:
        path = Path(filename)
        try:
            label = path.resolve().relative_to(ROOT).as_posix()
        except ValueError:
            label = path.name
        functions.append({"file": label, "line": line, "function": name, "calls": calls,
                          "internalMs": internal * 1000, "cumulativeMs": cumulative * 1000})
    result = {"observedAt": datetime.now(timezone.utc).isoformat(), "scope": "Read-only isolated identity, current inspector computation and sequential HTTP requests; no production benchmark",
              "study": args.study, "documentId": document_id, "workspaceId": workspace_id,
              "rounds": rounds, "profileFunctions": functions,
              "limits": ["Separate Python process and cProfile add overhead; not CPU timing inside running API server",
                         "HTTP requests sequential direct then proxy, with fresh urllib connections; browser has other concurrency",
                         "Three samples not p95 and not a controlled before/after comparison",
                         "SQL cursor timings exclude hydration and response serialization; no document mutations"]}
    OUT.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
