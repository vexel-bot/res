"""Revise an existing ÓRBITA cut in an isolated Clicko document, with local engines."""
import argparse
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "benchmarks/studios/orbita/quality-revision.jsx"
KEY = "orbita-quality-local-revision-v2-20261113"


def write(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


def star_field(path):
    width, height = 1080, 1920
    x, y = np.meshgrid(np.linspace(0, 1, width, dtype=np.float32), np.linspace(0, 1, height, dtype=np.float32))
    rng = np.random.default_rng(1611)
    horizon = .965 + .27 * (x - .5) ** 2
    glow = np.exp(-np.abs(y - horizon) * 87) * np.exp(-((x - .5) / .48) ** 2)
    sky = np.exp(-((x-.34)/.45)**2-((y-.55)/.42)**2)
    pixel = np.stack([6 + 8*sky + 70*glow, 7 + 5*sky + 23*glow, 12 + 11*sky + 10*glow], axis=-1)
    pixel[y >= horizon] *= .5
    pixel += rng.normal(0, 1, (height, width, 1))
    image = Image.fromarray(np.clip(pixel, 0, 255).astype(np.uint8))
    draw = ImageDraw.Draw(image)
    for _ in range(660):
        px, py = int(rng.integers(width)), int(rng.integers(int(height*.94)))
        level = int(rng.integers(14, 78))
        draw.point((px, py), fill=(level, level, level+8))
        if level > 72:
            draw.point((px+1, py), fill=(level//2,level//2,level//2+6))
    image.save(path)


def orbital_art(path):
    x, y = np.meshgrid(np.linspace(-1.8, 1.8, 760), np.linspace(-1.17, 1.17, 494))
    radius = np.hypot(x, y)
    sphere = radius <= .77
    z = np.sqrt(np.maximum(0, 1 - (radius / .77)**2))
    light = np.clip((-.62*x - .49*y)/.77 + z*.66, 0, 1)
    stripes = .79 + .21*np.sin(38*y + 2.6*z + .55*np.sin(9*x))
    rim = np.exp(-np.abs(radius-.77)*32) * np.clip(-x-y, 0, 1)
    rgb = np.stack([42+207*light*stripes, 19+119*light*stripes, 25+52*light*stripes], axis=-1)
    rgb[~sphere] = [255, 93, 35]
    alpha = np.where(sphere, np.clip((.775-radius)*220, 0, 1), rim*.49)
    tilt = -.25*x + y
    line = np.abs(np.hypot(x/1.6, tilt/.40)-1) < .009
    visible = line & (~sphere | (tilt > .04))
    rgb[visible] = [235, 164, 111]
    alpha[visible] = .7
    dot = np.hypot(x-1.15, y-.56) < .033
    rgb[dot], alpha[dot] = [255, 183, 96], 1
    Image.fromarray(np.clip(np.dstack([rgb, alpha*255]), 0, 255).astype(np.uint8)).save(path)


def main(previous, output, phase):
    runtime = ROOT / ".codex-runtime/clicko-dev/studios"
    os.environ.update(ENVIRONMENT="development", DATABASE_URL="sqlite:///" + (runtime / "records.sqlite").as_posix(),
                      STORAGE_PATH=str(runtime / "uploads"))
    sys.path.insert(0, str(ROOT / "backend"))
    from app.database import SessionLocal
    from app.domain.studios.contracts import CreateStudioDocumentRequest
    from app.domain.studios.craft import CraftCommandRequestV1, CraftRenderRequestV1
    from app.domain.studios.editing_resources import ResourceMetadataV1
    from app.models import CreativeDocument, User
    from app.services.object_storage import get_object_storage
    from app.services.studios import craft, editing_resources
    from app.services.studios.compatibility import record_to_contract
    from app.services.studios.jobs import execute_job_once
    from app.services.studios.kernel import create_document

    output.mkdir(parents=True, exist_ok=True)
    receipt = json.loads((previous / "cycle-receipt.json").read_text(encoding="utf-8"))
    with SessionLocal() as db:
        origin = db.get(CreativeDocument, receipt["documentId"])
        source = record_to_contract(origin)
        user = db.get(User, source.actor_id)
        if phase == "inspect":
            write(output / "source-inspection.json", craft.inspection(db, origin)["project"])
            return
        branch = create_document(db, CreateStudioDocumentRequest.model_validate({
            "workspaceId": origin.workspace_id, "contentType": "video", "brandRevision": source.brand_memory_ref.revision,
            "title": "ÓRBITA · revisão local de direção e som",
            "brief": source.brief.model_dump(mode="json", by_alias=True),
            "composition": source.composition.model_dump(mode="json", by_alias=True),
            "assets": [item.model_dump(mode="json", by_alias=True) for item in source.assets],
        }), user, creation_key=KEY)
        if branch.revision == 1:
            native = source.native_editor_state
            with craft.workspace_files(db, origin, native) as (_, params, _):
                craft.save_native(db, branch, user, Path(params["nativePath"]), engine="effectcraft",
                    expected_revision=1, key=KEY + "-clone", asset_manifest=native.asset_manifest,
                    font_manifest=native.font_manifest)
        payload = SCRIPT.read_text(encoding="utf-8")
        if phase in {"edit", "render"}:
            state = output / "edit-v2.json"
            current = json.loads(state.read_text(encoding="utf-8")) if state.exists() else {}
            asset_id = current.get("starAssetId")
            if not asset_id:
                star_field(output / "orbita-campo.png")
                art = editing_resources.store_resource(db, branch.workspace_id, "ÓRBITA · campo de estrelas original",
                    output / "orbita-campo.png", ResourceMetadataV1(kind="image", usageEvidence="Grafismo original da revisão local"), user.id)
                asset_id = art.id
                orbital_art(output / "orbita-planeta.png")
                planet = editing_resources.store_resource(db, branch.workspace_id, "ÓRBITA · planeta e órbita",
                    output / "orbita-planeta.png", ResourceMetadataV1(kind="image", usageEvidence="Grafismo original da revisão local"), user.id)
                current["planetAssetId"] = planet.id
                db.commit()
            script_hash = hashlib.sha256(payload.encode()).hexdigest()
            if current.get("scriptHash") and current["scriptHash"] != script_hash:
                raise ValueError("Revision script changed. Start a new branch from the original cut.")
            if not current.get("scriptHash"):
                write(state, {"starAssetId": asset_id, "planetAssetId": current["planetAssetId"]})
            if current.get("scriptHash") != script_hash:
                commands = []
                if not current.get("scriptHash"):
                    commands.append({"id": "asset.import", "params": {"assetId": asset_id, "addToComp": True}})
                    commands.append({"id": "asset.import", "params": {"assetId": current["planetAssetId"], "addToComp": True}})
                commands.append({"id": "script.run", "params": {"code": payload}})
                response = craft.commands(db, branch, CraftCommandRequestV1(expectedRevision=branch.revision,
                    label="Revisar a película, identidade, crédito e som", commands=commands), user,
                    KEY + "-edit-" + script_hash[:16])
                db.commit()
                write(state, {"documentId": branch.id, "revision": branch.revision, "starAssetId": asset_id,
                              "planetAssetId": current["planetAssetId"], "scriptHash": script_hash, "receiptId": response["receiptId"]})
        current = record_to_contract(branch)
        if phase == "record":
            from tempfile import TemporaryDirectory
            import time
            from types import SimpleNamespace
            from app.services.studios.craft_direction import repertoire_version
            from app.services.studios.craft_editorial import persist_review
            from app.services.studios.craft_learning import save_editorial_lesson, style_guide
            from app.services.studios.craft_review import review_draft

            evidence = json.loads((output / "recibo-revisao.json").read_text(encoding="utf-8"))
            validation = json.loads((output / "comparacao-revisao.json").read_text(encoding="utf-8"))
            transfer = json.loads((output / "transferencia-local.json").read_text(encoding="utf-8"))
            assert evidence["revision"] == current.revision
            path = output / "orbita-revisada.mp4"
            checksum = evidence["artifact"]["checksumSha256"]
            assert checksum == validation["revised"]["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
            with TemporaryDirectory(prefix="orbita-revision-review-") as directory:
                draft = SimpleNamespace(directory=Path(directory), batches=0, deadline=time.monotonic()+90,
                    params={"media": [{"assetId": evidence["artifact"]["assetId"], "path": str(path),
                                       "mediaType": "video/mp4", "checksumSha256": checksum}]})
                review = review_draft(draft, {"assetId": evidence["artifact"]["assetId"], "sampling": "overview"},
                                     db=db, workspace_id=branch.workspace_id)
                persisted = persist_review(db, branch, review, job_id=evidence["renderJobId"])
            guide = style_guide(db, branch.workspace_id, "workspace")
            feedback = "Revisão local ÓRBITA, MP4 " + checksum
            lesson = next((item for item in guide["lessons"] if item.get("sourceFeedback") == feedback), None)
            if not lesson:
                guide = save_editorial_lesson(db, branch.workspace_id, {
                    "situation": "A imagem se separa da película durante o recuo e invade a área das perfurações.",
                    "correction": "Usar os mesmos tempos, centro e escala para janela, corpo e perfurações. Conferir a folga no MP4 e preservar área independente para título, convite e crédito.",
                    "useWhen": ["Uma moldura e seu conteúdo precisam se deslocar como um objeto reconhecível."],
                    "avoidWhen": ["A moldura encobre a ação de uma demonstração ou a separação de planos é intencional."],
                    "sourceFeedback": feedback,
                }, guide["version"], source_job_id=evidence["renderJobId"], actor_id=user.id)
                lesson = guide["lessons"][-1]
            db.commit()
            write(output / "aprendizado-e-revisao.json", {"lesson": lesson, "review": persisted,
                "repertoireVersion": repertoire_version(), "guideVersion": guide["version"],
                "exportSha256": checksum, "transfer": transfer, "apiSpendUsd": 0})
            return
        if phase == "edit":
            write(output / "revised-inspection.json", craft.inspection(db, branch)["project"])
            for frame in (48, 128, 190, 234, 350, 438, 504):
                (output / f"preview-{frame}.png").write_bytes(craft.render_frame(db, branch, frame=frame))
            return
        job, _ = craft.create_render_job(db, branch, CraftRenderRequestV1(expectedRevision=current.revision,
            format="mp4", quality="high"), user, KEY + f"-render-{current.revision}")
        if job.status in {"queued", "retrying"}:
            execute_job_once(db, job)
            db.refresh(job)
        if job.status != "succeeded":
            raise RuntimeError(f"render {job.status}: {job.error_code}")
        artifact = job.result_payload["artifact"]
        asset = craft.scoped_asset(db, branch.workspace_id, artifact["assetId"], artifact["checksumSha256"])
        with get_object_storage(asset.storage_backend).materialize(asset.storage_key) as media:
            shutil.copyfile(media, output / "orbita-revisada.mp4")
        with craft.native_bundle(db, branch, current.native_editor_state) as bundle:
            shutil.copyfile(bundle, output / "orbita-revisada-editavel.zip")
        db.refresh(origin)
        assert origin.revision == source.revision
        assert record_to_contract(origin).native_editor_state.checksum_sha256 == source.native_editor_state.checksum_sha256
        write(output / "recibo-revisao.json", {"sourceDocumentId": origin.id, "sourceRevision": source.revision,
            "sourceNativeSha256": source.native_editor_state.checksum_sha256, "sourcePreserved": True,
            "documentId": branch.id, "revision": current.revision, "nativeSha256": current.native_editor_state.checksum_sha256,
            "renderJobId": job.id, "artifact": artifact, "editor": "Codex via Clicko EffectCraft local", "apiSpendUsd": 0})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("previous", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("phase", choices=["inspect", "edit", "render", "record"])
    args = parser.parse_args()
    main(args.previous.resolve(), args.output.resolve(), args.phase)
