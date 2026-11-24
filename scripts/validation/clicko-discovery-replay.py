"""Replay recorded native discovery and verify recovery without any LLM call."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    runtime = ROOT / ".codex-runtime/clicko-dev"
    os.environ.update(ENVIRONMENT="development", DATABASE_URL="sqlite:///" + (runtime / "studios/records.sqlite").as_posix(),
                      STORAGE_PATH=str(runtime / "studios/uploads"))
    sys.path.insert(0, str(ROOT / "backend"))
    from app.database import SessionLocal
    from app.domain.studios.craft import CraftAICommandRequestV1
    from app.models import CreativeDocument
    from app.providers.studios.craft import require_capability
    from app.services.studios import craft, craft_observations as observations
    from app.services.studios.craft_agent import Draft
    from app.services.studios.craft_history import compact_messages
    from app.services.studios.compatibility import record_to_contract
    receipt = json.loads((args.output / "receipt.json").read_text(encoding="utf-8"))
    previous = json.loads((args.output / "job-evidence.json").read_text(encoding="utf-8"))["result"]
    calls = [t for t in previous["tools"] if t.get("ok") and observations.eligible(t["name"], t["input"])]
    archive, events, native_calls, recovered = {}, [], 0, 0
    with SessionLocal() as db:
        record = db.get(CreativeDocument, receipt["documentId"])
        native = record_to_contract(record).native_editor_state
        capability = require_capability("effectcraft")
        with craft.workspace_files(db, record, native) as (directory, params, _):
            draft = Draft(native, directory, params, capability,
                CraftAICommandRequestV1(expectedRevision=record.revision, instruction="Technical discovery replay"), float("inf"))
            checksum = hashlib.sha256(Path(params["nativePath"]).read_bytes()).hexdigest()
            messages = []
            for call in calls:
                name, inputs = call["name"], call["input"]
                key = observations.key(name, inputs, capability["buildId"], checksum)
                if key in archive:
                    result = observations.recall(archive, key, capability["buildId"], checksum)
                    recovered += 1
                else:
                    result = draft.run(name, inputs)
                    native_calls += 1
                    observations.remember(archive, name, inputs, result, capability["buildId"], checksum, call["toolUseId"])
                state = {"observationArchive": archive, "materialSearches": previous.get("materialSearches", []),
                         "directorContext": previous.get("directorContext")}
                # Roundtrip represents a stopped process; compact after every observation.
                state = json.loads(json.dumps(state))
                messages = compact_messages({"instruction": "Replay", "recoverableEvidenceMode": True}, {}, 0, state, messages=messages)
                assert observations.recall(state["observationArchive"], key, capability["buildId"], checksum) == result
                assert len(json.loads(messages[0]["content"][1]["text"])["nativeObservationIndex"]) == len(archive)
                assert draft.batches == 0
                assert hashlib.sha256(Path(draft.params["nativePath"]).read_bytes()).hexdigest() == checksum
                events.append({"name": name, "id": key, "resultBytes": len(json.dumps(result)),
                               "visibleResultBytes": len(json.dumps(observations.present(result))),
                               "checkpointBytes": len(json.dumps(messages)), "draftBatch": draft.batches})
    report = {"status": "passed", "llmCalls": 0, "nativeCalls": native_calls, "recoveredCalls": recovered,
              "recordedCallsReplayed": len(calls), "events": events, "buildId": capability["buildId"]}
    (args.output / "native-observations.json").write_text(json.dumps(archive), encoding="utf-8")
    (args.output / "discovery-replay.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "events"}))


if __name__ == "__main__":
    main()
