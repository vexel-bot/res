"""Create and render the ÓRBITA exercise in the local Clicko workspace."""
import argparse
import json
import os
import shutil
from pathlib import Path


SOURCE_ID = "1b295922-5884-411b-a54f-eebf1da83593"
CASE = Path(__file__).resolve().parents[2] / "benchmarks/studios/orbita"


def main(output):
    runtime = Path(".codex-runtime/clicko-dev").resolve()
    os.environ.update(ENVIRONMENT="development", DATABASE_URL="sqlite:///" + (runtime / "studios/records.sqlite").as_posix(),
                      STORAGE_PATH=str(runtime / "studios/uploads"))
    from app.database import SessionLocal
    from app.domain.studios.contracts import CreateStudioDocumentRequest
    from app.domain.studios.craft import CraftCommandRequestV1, CraftMigrationRequestV1, CraftRenderRequestV1
    from app.models import CreativeDocument, User
    from app.routers.studios import owned_document
    from app.services.object_storage import get_object_storage
    from app.services.studios import craft
    from app.services.studios.compatibility import record_to_contract
    from app.services.studios.jobs import execute_job_once
    from app.services.studios.kernel import create_document

    output.mkdir(parents=True, exist_ok=True)
    with SessionLocal() as db:
        source = db.get(CreativeDocument, SOURCE_ID)
        original = record_to_contract(source)
        user = db.get(User, original.actor_id)
        source = owned_document(db, user.id, SOURCE_ID)
        native = original.native_editor_state
        request = CreateStudioDocumentRequest.model_validate({
            "workspaceId": original.workspace_id, "contentType": "video", "brandRevision": original.brand_memory_ref.revision,
            "title": "ÓRBITA · exercício de movimento, texto e áudio",
            "brief": original.brief.model_dump(mode="json", by_alias=True),
            "composition": {"pages": [{"id": "main", "width": 540, "height": 960, "durationMs": 19500, "layers": []}]},
            "assets": [asset.model_dump(mode="json", by_alias=True) for asset in original.assets],
        })
        exercise = create_document(db, request, user, creation_key="orbita-recuo-exercise-20261112")
        if exercise.revision == 1:
            craft.migrate(db, exercise, CraftMigrationRequestV1(engine="effectcraft", expectedRevision=1), user,
                          "orbita-exercise-native-seed")
        if exercise.revision == 2:
            with craft.workspace_files(db, source, native) as (_directory, params, _manifests):
                craft.save_native(db, exercise, user, Path(params["nativePath"]), engine="effectcraft", expected_revision=2,
                                  key="orbita-exercise-import-original", asset_manifest=native.asset_manifest,
                                  font_manifest=native.font_manifest)
        if exercise.revision == 3:
            before = record_to_contract(exercise).native_editor_state
            with craft.native_bundle(db, exercise, before) as bundle:
                shutil.copyfile(bundle, output / "orbita-exercicio-antes.zip")
            code = (CASE / "recuo-reparo.jsx").read_text(encoding="utf-8")
            reply = craft.commands(db, exercise, CraftCommandRequestV1(expectedRevision=3,
                label="Demonstração · recuo, hierarquia tipográfica e fade",
                commands=[{"id": "script.run", "params": {"code": code}}]), user, "orbita-exercise-repair-v1")
            (output / "comandos-executados.json").write_text(json.dumps(reply, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        contract = record_to_contract(exercise)
        assert contract.revision == 4, contract.revision
        job, _ = craft.create_render_job(db, exercise,
            CraftRenderRequestV1(expectedRevision=contract.revision, format="mp4", quality="high"), user, "orbita-exercise-export-v1")
        print(json.dumps({"documentId": exercise.id, "revision": contract.revision, "exportJobId": job.id}), flush=True)
        if job.status in {"queued", "retrying"}:
            execute_job_once(db, job)
            db.refresh(job)
        assert job.status == "succeeded", (job.status, job.error_code)
        artifact = job.result_payload["artifact"]
        asset = craft.scoped_asset(db, exercise.workspace_id, artifact["assetId"], artifact["checksumSha256"])
        with get_object_storage(asset.storage_backend).materialize(asset.storage_key) as path:
            shutil.copyfile(path, output / "orbita-recuo-corrigido.mp4")
        with craft.native_bundle(db, exercise, contract.native_editor_state) as bundle:
            shutil.copyfile(bundle, output / "orbita-exercicio-corrigido.zip")
        db.refresh(source)
        current = record_to_contract(source)
        assert current.revision == original.revision and current.native_editor_state.checksum_sha256 == native.checksum_sha256
        receipt = {"sourceId": source.id, "sourceRevision": original.revision, "sourceChecksum": native.checksum_sha256,
                   "sourceUnchanged": True, "exerciseId": exercise.id, "revision": contract.revision,
                   "exportJobId": job.id, "artifact": artifact, "apiSpendUsd": 0}
        (output / "exercicio-recibo.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(receipt, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    main(parser.parse_args().output.resolve())
