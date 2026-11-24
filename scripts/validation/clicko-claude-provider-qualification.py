"""Qualify the session-bound Claude visual adapter without editing a project."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--connection", required=True)
    parser.add_argument("--video", type=Path, required=True)
    args = parser.parse_args()
    runtime = args.runtime.resolve()
    os.environ["DATABASE_URL"] = "sqlite:///" + (runtime / "studios/records.sqlite").as_posix()
    os.environ["STUDIO_LLM_CREDENTIAL_KEY"] = (runtime / "llm-credential-key").read_text().strip()
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
    from PIL import Image
    from app.database import SessionLocal
    from app.models import StudioLLMConnection
    from app.providers.studios.universal_llm import UniversalLLMPlanner
    from app.services.studios import craft_claude_review as reviewer
    from app.services.studios.llm_connections import decrypt

    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise ValueError("Qualification already submitted. Inspect its receipt before starting a new attempt.")
    proof = {"adapterVersion": reviewer.VERSION, "model": reviewer.MODEL,
             "connectionId": args.connection, "qualificationPassed": False, "status": "preparing"}
    def save():
        output.write_text(json.dumps(proof, ensure_ascii=False, indent=2), encoding="utf-8")

    with SessionLocal() as db:
        connection = db.get(StudioLLMConnection, args.connection)
        if not connection or not reviewer.valid_connection(connection, connection):
            raise ValueError("claude_connection_unavailable")
        provider = UniversalLLMPlanner(connection.config, decrypt(connection))
        proof["connectionRevision"] = connection.revision
        media = {}
        for label, color in (("A", (208, 32, 208)), ("B", (32, 208, 208))):
            image = Image.new("RGB", (640, 480), color)
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG")
            media[label] = {"frames": [buffer.getvalue()], "timestamps": [0],
                            "sampling": {"kind": "single_control_frame"},
                            "interval": {"startSeconds": 0, "durationSeconds": 1}}
        proof.update(status="control_submitted")
        save()
        result = reviewer.observe(provider, media, [
            {"sceneId": "control", "acceptance": ["The field is magenta. Report visible contradictions."]}], [])
        proof["control"] = result
        save()
        if result["status"] != "succeeded":
            return 2
        observations = {label: " ".join(f["observation"].lower() for f in assessment["findings"])
                        for label, assessment in result["assessments"].items()}
        if not (any(word in observations["A"] for word in ("magenta", "roxo", "purple", "rosa"))
                and any(word in observations["B"] for word in ("ciano", "cyan", "turquesa", "teal"))):
            proof["status"] = "control_failed"
            save()
            return 2
        # Actual historical footage, entirely read-only.
        path = args.video.resolve()
        source_sha = hashlib.file_digest(path.open("rb"), "sha256").hexdigest()
        window = {"startSeconds": 0, "durationSeconds": 4}
        actual = reviewer.frames(path, window, window, {"fps": 2, "maximumSide": 1280})
        proof.update(status="existing_video_submitted", sourceSha256=source_sha)
        save()
        result = reviewer.observe(provider, {"A": actual}, [], [])
        proof["existingVideo"] = {**result, "timestamps": actual["timestamps"], "sampling": actual["sampling"],
                                 "frameChecksums": [hashlib.sha256(frame).hexdigest() for frame in actual["frames"]]}
        proof["sourcePreserved"] = hashlib.file_digest(path.open("rb"), "sha256").hexdigest() == source_sha
        proof.update(status=result["status"], qualificationPassed=result["status"] == "succeeded",
                     providerRequestId=result.get("providerRequestId"))
        save()
    print(json.dumps({"status": proof["status"], "qualificationPassed": proof["qualificationPassed"],
                      "sourcePreserved": proof["sourcePreserved"]}))
    return 0 if proof["qualificationPassed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
