"""Render a held-out brief and replay a valid decision from the local model in Clicko."""
import argparse
import json
import os
import re
import shutil
import subprocess
from pathlib import Path


CASE = Path(__file__).resolve().parents[2] / "benchmarks/studios/orbita"


def main(output, apply):
    runtime = Path(".codex-runtime/clicko-dev").resolve()
    os.environ.update(ENVIRONMENT="development", DATABASE_URL="sqlite:///" + (runtime / "studios/records.sqlite").as_posix(),
                      STORAGE_PATH=str(runtime / "studios/uploads"))
    from app.database import SessionLocal
    from app.domain.studios.contracts import CreateStudioDocumentRequest
    from app.domain.studios.craft import CraftCommandRequestV1, CraftMigrationRequestV1, CraftRenderRequestV1
    from app.models import CreativeDocument, User
    from app.services.object_storage import get_object_storage
    from app.services.studios import craft
    from app.services.studios.compatibility import record_to_contract
    from app.services.studios.jobs import execute_job_once
    from app.services.studios.kernel import create_document

    case = json.loads((CASE / "transferencia-casa-lume-escolhas.json").read_text(encoding="utf-8"))
    lesson = json.loads((output / "exercicio-recibo.json").read_text(encoding="utf-8"))
    selected = {}
    if apply:
        inference = json.loads((output / "ia-local-resultados.json").read_text(encoding="utf-8"))
        for arm, result in inference["transfer"].items():
            match = re.match(r"^\s*[(*]*([ABC])(?=$|[\s.:)*-])", result["answer"], re.IGNORECASE)
            selected[arm] = match.group(1).upper() if match else None
        selected["editorialControl"] = "B"

    def write_frame(video, name, second):
        subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-y", "-ss", str(second), "-i", str(video),
            "-frames:v", "1", "-vf", "scale=300:-1", "-threads", "1", str(output / name)], check=True, timeout=30)

    with SessionLocal() as db:
        context = record_to_contract(db.get(CreativeDocument, lesson["exerciseId"]))
        user = db.get(User, context.actor_id)
        request = CreateStudioDocumentRequest.model_validate({
            "workspaceId": context.workspace_id, "contentType": "video", "brandRevision": context.brand_memory_ref.revision,
            "title": "Casa Lume · teste de transferência editorial",
            "brief": {"objective": case["briefing"], "audience": "Moradores do bairro", "format": "video"},
            "composition": {"pages": [{"id": "main", "width": 540, "height": 960, "durationMs": 6000, "layers": []}],
                "mediaTimeline": {"frameRate": {"numerator": 24, "denominator": 1}, "durationFrames": 144, "tracks": []}},
        })
        seed = create_document(db, request, user, creation_key="orbita-transfer-lume-seed-20261112")
        if seed.revision == 1:
            craft.migrate(db, seed, CraftMigrationRequestV1(engine="effectcraft", expectedRevision=1), user, "lume-seed-migrate")
        if seed.revision == 2:
            craft.commands(db, seed, CraftCommandRequestV1(expectedRevision=2, label="Semente de avaliação",
                commands=[{"id": "script.run", "params": {"code": (CASE / "transferencia-casa-lume.jsx").read_text(encoding="utf-8")}}]),
                user, "lume-seed-script-v1")
        assert seed.revision == 3
        seed_state = record_to_contract(seed).native_editor_state

        def export(record, stem):
            contract = record_to_contract(record)
            job, _ = craft.create_render_job(db, record,
                CraftRenderRequestV1(expectedRevision=contract.revision, format="mp4"), user, f"export-{stem}")
            if job.status in {"queued", "retrying"}:
                execute_job_once(db, job)
                db.refresh(job)
            assert job.status == "succeeded", (job.status, job.error_code)
            artifact = job.result_payload["artifact"]
            asset = craft.scoped_asset(db, record.workspace_id, artifact["assetId"], artifact["checksumSha256"])
            path = output / f"{stem}.mp4"
            with get_object_storage(asset.storage_backend).materialize(asset.storage_key) as media:
                shutil.copyfile(media, path)
            return path, {"documentId": record.id, "revision": contract.revision, "exportJobId": job.id, "artifact": artifact}

        if not apply:
            media, proof = export(seed, "lume-semente")
            write_frame(media, "lume-seed.png", 1.25)
            print(json.dumps(proof, ensure_ascii=False), flush=True)
            return

        results = {"seedId": seed.id, "seedRevision": 3, "gabarito": "B", "apiSpendUsd": 0, "arms": {}}
        for arm, choice in selected.items():
            if choice is None:
                results["arms"][arm] = {"selected": None, "status": "invalid_model_response"}
                continue
            payload = request.model_copy(update={"title": f"Casa Lume · {arm} · escolha {choice}"})
            branch = create_document(db, payload, user, creation_key=f"orbita-transfer-lume-{arm}-{choice}")
            if branch.revision == 1:
                with craft.workspace_files(db, seed, seed_state) as (_directory, params, _manifests):
                    craft.save_native(db, branch, user, Path(params["nativePath"]), engine="effectcraft",
                                      expected_revision=1, key=f"lume-clone-{arm}-{choice}")
            if branch.revision == 2:
                craft.commands(db, branch, CraftCommandRequestV1(expectedRevision=2, label=f"Escolha local {choice}",
                    commands=[{"id": "script.run", "params": {"code": case["options"][choice]["script"]}}]),
                    user, f"lume-edit-{arm}-{choice}")
            media, proof = export(branch, f"lume-{arm}-{choice}")
            for second in [1.25, 2.75]:
                write_frame(media, f"lume-{arm}-{choice}-{second}.png", second)
            state = record_to_contract(branch).native_editor_state
            with craft.native_bundle(db, branch, state) as bundle:
                shutil.copyfile(bundle, output / f"lume-{arm}-{choice}-editavel.zip")
            results["arms"][arm] = {**proof, "selected": choice, "matchesEditorialTarget": choice == "B", "status": "rendered",
                                     "decisionSource": "editorial_control" if arm == "editorialControl" else "local_vlm"}
        db.refresh(seed)
        assert seed.revision == 3 and record_to_contract(seed).native_editor_state.checksum_sha256 == seed_state.checksum_sha256
        (output / "transferencia-recibo.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(results, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    main(args.output.resolve(), args.apply)
