"""Observe the exported cycle candidate using sampling chosen by the session's Claude."""
import argparse
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--runtime", type=Path, default=ROOT / ".codex-runtime/clicko-dev")
    args = parser.parse_args()
    runtime, output = args.runtime.resolve(), args.output.resolve()
    os.environ.update(DATABASE_URL="sqlite:///" + (runtime / "studios/records.sqlite").as_posix(),
                      STORAGE_PATH=str(runtime / "studios/uploads"),
                      STUDIO_LLM_CREDENTIAL_KEY=(runtime / "llm-credential-key").read_text().strip())
    sys.path.insert(0, str(ROOT / "backend"))
    from app.database import SessionLocal
    from app.models import CreativeDocument, StudioGenerationJob, StudioLLMConnection
    from app.providers.studios.universal_llm import UniversalLLMPlanner
    from app.services.studios import craft, craft_director as director, craft_project_context as project
    from app.services.studios import craft_claude_review as reviewer
    from app.services.studios.compatibility import record_to_contract
    from app.services.studios.llm_connections import decrypt
    receipt = json.loads((output / "receipt.json").read_text(encoding="utf-8"))
    plan_path = output / "final-observation-plan.json"
    with SessionLocal() as db:
        record = db.get(CreativeDocument, receipt["documentId"])
        job = db.get(StudioGenerationJob, receipt["jobId"])
        _, state = project.state(db, record)
        candidate = max(state["candidates"], key=lambda item: item["binding"]["draftBatch"])
        scenes = director.latest_plan(state, record)["plan"]["scenes"]
        connection = db.get(StudioLLMConnection, job.request_payload["llmConnectionId"])
        if not plan_path.exists():
            plan_path.write_text(json.dumps({"status": "submitted"}), encoding="utf-8")
            provider = UniversalLLMPlanner(connection.config, decrypt(connection))
            reply = provider.craft_turn(reviewer.MODEL,
                'Choose visual review sampling. Return only JSON {"observations":[{"interval":{"startSeconds":0,'
                '"durationSeconds":1},"parameters":{"fps":2,"maximumSide":1280}}]}. Cover all essential scene intervals. '
                'Each observation must have at most 48 frames, fps >0 and <=60, maximumSide 256..2048. '
                'Choose enough density for the events and finishing. No sound input is available.',
                [{"role": "user", "content": json.dumps({"scenes": scenes})}], [], 2048, 180, effort="high")
            text = "".join(part["text"] for part in reply["content"] if part["type"] == "text").strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0]
            proposal = json.loads(text)
            if reply.get("stop_reason") != "end_turn":
                raise ValueError("observation_planning_incomplete")
            proposal.update(status="planned", providerRequestId=reply.get("request_id"), usage=reply["usage"])
            proposal["costEstimateUsd"] = (reply["usage"]["input_tokens"] * 4 + reply["usage"]["output_tokens"] * 20) / 1e6
            plan_path.write_text(json.dumps(proposal, indent=2, ensure_ascii=False), encoding="utf-8")
        proposal = json.loads(plan_path.read_text(encoding="utf-8"))
        if proposal.get("status") != "planned":
            raise ValueError("observation_plan_requires_reconciliation")
        for scene in scenes:
            if scene["essential"] and not any(director.contains(item["interval"], scene["interval"])
                                               for item in proposal["observations"]):
                raise ValueError("observation_plan_missing_essential_scene")
        with craft.workspace_files(db, record, record_to_contract(record).native_editor_state) as (_, params, _):
            draft = SimpleNamespace(params=params, batches=candidate["binding"]["draftBatch"])
            observations = []
            for index, item in enumerate(proposal["observations"]):
                _, state = project.state(db, record)
                existing = next((operation for operation in state["operations"]
                                 if operation.get("operationKey") == f"final-observation-v2-{candidate['id']}-{index}"), None)
                payload = {"operationId": existing["id"]} if existing else {
                    "providerId": reviewer.PROVIDER_ID, "reviewAssetId": candidate["reviewAssetId"],
                    "operationKey": f"final-observation-v2-{candidate['id']}-{index}",
                    "modality": "visual", **item,
                }
                result = director.dispatch(db, record, job, draft, "request_direction_evaluation",
                    {"expectedVersion": state["version"], "payload": payload}, "", [], [])
                observations.append(result)
                (output / "final-observations.json").write_text(
                    json.dumps(observations, indent=2, ensure_ascii=False), encoding="utf-8")
                if result["operation"]["status"] != "succeeded":
                    raise ValueError("final_observation_requires_reconciliation")
        _, state = project.state(db, record)
        (output / "director-state.json").write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Final visual observations completed.")


if __name__ == "__main__":
    main()
