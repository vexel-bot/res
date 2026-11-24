"""Codex operates Clicko's real native command/render services; no external movie assembly."""
import argparse
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
SOURCE = "2699ab93-556a-4c59-940e-92452dc20382"


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["prepare", "capabilities", "script", "commands", "inspect", "render", "collect", "probe"])
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--runtime", type=Path, default=ROOT / ".codex-runtime/clicko-dev")
    parser.add_argument("--brief", type=Path)
    parser.add_argument("--source", default=SOURCE)
    parser.add_argument("--task-key", default="codex-motion-45s-20261116")
    parser.add_argument("--title", default="Clicko · 45 s · direção e edição Codex")
    parser.add_argument("--expected-build", default="clicko-effectcraft-1.0.5+67434e90")
    parser.add_argument("--objective", default="Produzir um motion sensorial e cinematográfico completo de 45 segundos da Clicko, conforme briefing.")
    parser.add_argument("--branch-reason", default="User requested Codex first, then Claude, both editing separate complete 45-second motions")
    parser.add_argument("--script", type=Path)
    parser.add_argument("--commands", type=Path)
    parser.add_argument("--label", default="inspection")
    parser.add_argument("--query", default="")
    parser.add_argument("--format", choices=["png", "mp4"], default="png")
    parser.add_argument("--frame", type=int, default=0)
    args = parser.parse_args()
    out, runtime = args.output.resolve(), args.runtime.resolve()
    out.mkdir(parents=True, exist_ok=True)
    os.environ.update(ENVIRONMENT="development", DATABASE_URL="sqlite:///" + (runtime / "studios/records.sqlite").as_posix(),
                      STORAGE_PATH=str(runtime / "studios/uploads"))
    os.environ["STUDIO_CRAFT_TIMEOUT_SECONDS"] = "3600"
    sys.path.insert(0, str(ROOT / "backend"))
    from app.database import SessionLocal
    from app.models import CreativeDocument, User, StudioGenerationJob
    from app.domain.studios.contracts import CreateStudioDocumentRequest
    from app.domain.studios.craft import CraftCommandRequestV1, CraftRenderRequestV1
    from app.providers.studios.craft import require_capability, call_engine
    from app.services.object_storage import get_object_storage
    from app.services.studios import craft
    from app.services.studios.craft_artifact_copy import copy_verified
    from app.services.studios.compatibility import record_to_contract
    from app.services.studios.kernel import create_document
    from app.services.studios.jobs import execute_job_once
    file = out / "session.json"
    session = json.loads(file.read_text(encoding="utf-8")) if file.exists() else {}
    capability = require_capability("effectcraft")
    if capability["buildId"] != args.expected_build or session.get("buildId", args.expected_build) != args.expected_build:
        raise ValueError("qualified_build_changed")
    write(out / "engine-capabilities.json", capability)
    if args.phase == "capabilities":
        from app.services.studios.craft_compatibility import scripting_reference
        print(json.dumps(scripting_reference("effectcraft", capability, args.query), ensure_ascii=False))
        return
    with SessionLocal() as db:
        origin = db.get(CreativeDocument, session.get("sourceDocumentId", args.source))
        source = record_to_contract(origin)
        user = db.get(User, source.actor_id)
        if args.phase == "prepare":
            if session:
                print(json.dumps({"status": "already_prepared", "documentId": session["documentId"]}))
                return
            if not args.brief:
                raise ValueError("brief_required")
            brief = args.brief.read_text(encoding="utf-8-sig")
            from app.services.studios import craft_project_context
            from app.domain.studios.craft_direction_v2 import HumanApproval
            _, source_state = craft_project_context.state(db, origin)
            approved = "b92b0982-3a5b-4500-88e0-dd1292ac0ceb"
            if origin.id == SOURCE and source_state.get("approvedCandidateId") != approved:
                craft_project_context.human_approval(db, origin, user, HumanApproval(
                    expectedRevision=origin.revision, expectedVersion=source_state["version"],
                    candidateId=approved, decision="approved",
                    comment="Usuário: 'Ótimo esse vídeo ficou bom, vamos avançar e fazer mais uma vez.' Aprovação desta peça de 15 s; não aprova a identidade como marca oficial nem resolve as pendências técnicas."))
                db.commit()
            branch = create_document(db, CreateStudioDocumentRequest.model_validate({
                "workspaceId": origin.workspace_id, "brandRevision": source.brand_memory_ref.revision,
                "title": args.title, "contentType": "video",
                "sourceDocumentId": origin.id, "sourceRevision": origin.revision,
                "branchReason": args.branch_reason,
                "brief": {"objective": args.objective,
                          "audience": "Criadores, profissionais de marketing e pequenas marcas no celular"},
                "composition": source.composition.model_dump(mode="json", by_alias=True),
                "assets": [a.model_dump(mode="json", by_alias=True) for a in source.assets]}),
                user, creation_key=args.task_key)
            native = source.native_editor_state
            with craft.workspace_files(db, origin, native) as (_, params, _):
                craft.save_native(db, branch, user, Path(params["nativePath"]), engine="effectcraft", expected_revision=1,
                    key=args.task_key+"-clone", asset_manifest=native.asset_manifest, font_manifest=native.font_manifest)
            db.commit()
            session = {"taskKey": args.task_key, "documentId": branch.id, "sourceDocumentId": origin.id,
                "buildId": capability["buildId"],
                "sourceRevision": source.revision, "sourceSha256": native.checksum_sha256,
                "briefSha256": hashlib.sha256(brief.encode()).hexdigest(), "director": "Codex",
                "editingRoute": "Clicko native craft.commands and craft.create_render_job",
                "modelBilling": "Codex account; no per-response USD measurement available here",
                "providerApiSpendUsd": 0, "startedAt": datetime.now(UTC).isoformat(), "edits": [], "renders": []}
            write(out / "briefing.txt", {"text": brief})
        record = db.get(CreativeDocument, session["documentId"])
        if args.phase in {"script", "commands"}:
            if args.phase == "script" and not args.script or args.phase == "commands" and not args.commands:
                raise ValueError("native_input_required")
            code = (args.script if args.phase == "script" else args.commands).read_text(encoding="utf-8-sig")
            sha = hashlib.sha256(code.encode()).hexdigest()
            step = out / "operations" / (args.label + ".json")
            previous = json.loads(step.read_text(encoding="utf-8")) if step.exists() else None
            if previous and previous["scriptSha256"] != sha:
                raise ValueError("operation_label_already_used_for_different_code")
            request = CraftCommandRequestV1.model_validate(previous["request"] if previous else {
                "expectedRevision": record.revision, "label": "Codex: " + args.label,
                "commands": ([{"id": "script.run", "params": {"code": code}}]
                             if args.phase == "script" else json.loads(code))})
            write(step, {"scriptSha256": sha, "request": request.model_dump(mode="json", by_alias=True), "status": "submitted"})
            reply = craft.commands(db, record, request, user, session["taskKey"] + "-" + args.label,
                metadata={"director": "codex", "scriptSha256": sha, "briefSha256": session["briefSha256"]})
            db.commit()
            write(step, {"scriptSha256": sha, "request": request.model_dump(mode="json", by_alias=True),
                         "status": "succeeded", "receipt": reply})
            if not any(s["label"] == args.label for s in session["edits"]):
                session["edits"].append({"label": args.label, "scriptSha256": sha, "revision": record.revision})
        if args.phase in {"inspect", "probe"}:
            state = record_to_contract(record).native_editor_state
            with craft.workspace_files(db, record, state) as (directory, params, _):
                if args.phase == "probe":
                    from app.services.studios.craft_agent import Draft
                    from types import SimpleNamespace
                    draft = Draft(state, directory, params, capability,
                                  SimpleNamespace(expected_revision=record.revision), float("inf"))
                    if args.script:
                        reply = draft.run("run_motion_script", {"code": args.script.read_text(encoding="utf-8-sig")})
                    elif args.query:
                        reply = draft.run("edit_project", {"commands": [{"id": "effect.list", "params": {"filter": args.query}}]})
                    else:
                        reply = draft.run("inspect_motion_fonts", {"faces": [
                            {"font": "Inter-Bold", "style": "Bold"}, {"font": "Inter", "style": "Bold"},
                            {"font": "Inter", "style": "SemiBold"}]})
                    write(out / (args.label + ".json"), reply)
                    print(json.dumps(reply, ensure_ascii=False)[:18000])
                    return
                else:
                    reply = call_engine("effectcraft", "project.open", params)
                    write(out / "native-inspection.json", reply)
                    shutil.copyfile(params["nativePath"], out / "native-current.ecproj")
                    print(json.dumps({"revision": record.revision, "inspectionFile": str(out / "native-inspection.json")}))
        if args.phase == "render":
            render, _ = craft.create_render_job(db, record, CraftRenderRequestV1(
                expectedRevision=record.revision, format=args.format, frame=args.frame, quality="high"),
                user, f"{session['taskKey']}-{args.format}-{record.revision}-{args.frame}")
            if render.status in {"queued", "retrying"}:
                execute_job_once(db, render)
                db.refresh(render)
            if not any(r["jobId"] == render.id for r in session["renders"]):
                session["renders"].append({"jobId": render.id, "revision": record.revision, "format": args.format,
                    "frame": args.frame, "status": render.status})
            if render.status != "succeeded":
                write(file, session)
                raise ValueError("native_render_failed: " + str(render.error_code))
        for rendering in session.get("renders", []):
            render = db.get(StudioGenerationJob, rendering["jobId"])
            if render.status != "succeeded":
                continue
            artifact = render.result_payload["artifact"]
            asset = craft.scoped_asset(db, record.workspace_id, artifact["assetId"], artifact["checksumSha256"])
            name = f"revision-{rendering['revision']}-frame-{rendering['frame']}.{rendering['format']}"
            with get_object_storage(asset.storage_backend).materialize(asset.storage_key) as path:
                copy_verified(path, out / name, artifact["checksumSha256"])
            rendering.update(artifact=artifact, file=str(out / name))
        state = record_to_contract(record).native_editor_state
        session.update(revision=record.revision, nativeSha256=state.checksum_sha256)
        if args.phase == "collect":
            with craft.native_bundle(db, record, state) as bundle:
                copy_verified(bundle, out / "clicko-codex-45s-editavel.zip")
        db.refresh(origin)
        session["sourcePreserved"] = origin.revision == session["sourceRevision"] and (
            record_to_contract(origin).native_editor_state.checksum_sha256 == session["sourceSha256"])
        assert session["sourcePreserved"]
        write(file, session)
        print(json.dumps({k: session[k] for k in ["documentId", "revision", "nativeSha256", "sourcePreserved"]}))


if __name__ == "__main__":
    main()
