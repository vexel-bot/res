"""Prepare rights-attributed sources and render an editable local EffectCraft reference."""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import wave
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
CASE = ROOT / "benchmarks/studios/orbita"
SHOTS = [
    ("01-cidade", 73.9, None, "Plano geral frio, torre e cidade em contraluz"),
    ("02-rosto", 319.55, 670, "Close de uma personagem, luz natural verde"),
    ("03-laboratorio", 399.65, 665, "Close com reflexos magenta, reação a uma interface"),
    ("04-hologramas", 45.5, None, "Contraste laranja e azul, mudança de escala"),
    ("05-maquina", 299.5, 672, "Detalhe de máquina sobre fundo exterior"),
    ("06-torre", 439.5, None, "Torre dourada contra o céu"),
    ("07-travessia", 219.8, None, "Figura cruza um espaço iluminado"),
]
BRIEF = """Crie e exporte um teaser publicitário vertical de 18 segundos para ÓRBITA, mostra fictícia de curtas de ficção científica. Público de cinema independente no celular. Copy aprovada: “O futuro cabe num curta.” / “ÓRBITA, mostra de curtas de ficção científica.” / “Confira a programação.” Nenhuma data, local, programação confirmada ou parceria foi fornecida. As imagens são excertos ilustrativos do curta Tears of Steel e exigem crédito discreto de Blender Foundation e indicação de edição do material.

Parta dos planos e sons preparados que estão no projeto, sem agregar fontes externas. Use-os para criar um anúncio, com mudança de escala, continuidade de atenção, cortes e luz orientados pela ação, e som em camadas acompanhando a montagem. Decida cenas, timing, hierarquia, efeitos e mix. Evite inferir que o filme já integra a programação. Monte em camadas editáveis, confira a leitura em celular e reveja o efeito de pelo menos uma passagem no render. Termine solicitando você mesmo a exportação MP4."""


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sound(output):
    rate = 24000
    t = np.arange(rate * 18) / rate
    fade = np.clip(t / .25, 0, 1) * np.clip((18 - t) / .8, 0, 1)
    stereo = []
    rng = np.random.default_rng(417)
    for phase in (0, .38):
        pulse = np.exp(-9 * np.mod(t + phase / 9, .5))
        bed = .073 * np.sin(2 * np.pi * 55 * t + phase) * (.52 + .48 * pulse)
        for f, gain in ((110, .025), (164.81, .017), (220, .009), (329.63, .005)):
            bed += np.sin(2 * np.pi * f * t + phase) * gain * (.55 + .45 * np.sin(2 * np.pi * .19 * t + phase))
        stereo.append(bed * fade)
    cuts = np.zeros_like(t)
    for index, at in enumerate((.125, 2.25, 4.50, 6.25, 8.0, 9.5, 11, 13.5, 14.5)):
        size = round(rate * (.62 if at == 13.5 else .28))
        x = np.arange(size) / rate
        env = np.exp(-x * (10 if at == 13.5 else 18)) * (1 - np.exp(-x * 260)) * np.clip((len(x) - np.arange(len(x))) / 180, 0, 1)
        texture = np.convolve(rng.normal(size=len(x)), np.hanning(19) / 9, mode="same")
        note = (91, 71, 82, 65)[index % 4]
        hit = (.19 * np.sin(2 * np.pi * (note * x - 12 * x * x)) + .12 * texture) * env
        if at in {13.5, 14.5}:
            hit += .058 * (np.sin(2 * np.pi * 440 * x) + .5 * np.sin(2 * np.pi * 659 * x)) * env
        start = round(at * rate)
        cuts[start:start + size] += hit
    for name, channels in (("08-pulso", stereo), ("09-acentos", [cuts, cuts])):
        with wave.open(str(output / (name + ".wav")), "wb") as file:
            file.setparams((2, 2, rate, 0, "NONE", "not compressed"))
            file.writeframes((np.stack(channels, axis=1) * 32767).astype("<i2").tobytes())


def prepare(source, output):
    sources = output / "materiais"
    sources.mkdir(parents=True, exist_ok=True)
    for index, (name, time, center, _note) in enumerate(SHOTS):
        picture = f"crop=300:534:{center - 150}:0,scale=540:960" if center is not None else "scale=540:-2"
        # Reframe and grade each shot independently. The edit, text and sound stay in EffectCraft.
        lift = (-.025, -.012, -.026, -.012, -.035, -.015, -.024)[index]
        video = sources / (name + ".mp4")
        if not video.is_file():
            subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-y", "-ss", str(time), "-i", str(source),
                "-t", "3.00", "-an", "-vf", f"{picture},eq=brightness={lift}:contrast=1.08:saturation=.92",
                "-r", "24", "-threads", "2", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
                "-movflags", "+faststart", str(video)], check=True, timeout=60)
    sound(sources)
    files = [sources / (row[0] + ".mp4") for row in SHOTS] + [sources / "08-pulso.wav", sources / "09-acentos.wav"]
    manifest = [{"file": p.name, "sha256": sha(p), "sourceSeconds": SHOTS[i][1] if i < len(SHOTS) else None,
                 "notes": SHOTS[i][3] if i < len(SHOTS) else "Pista estéreo original sintetizada localmente"}
                for i,p in enumerate(files)]
    (output / "materiais.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return files


def main(source, output):
    runtime = ROOT / ".codex-runtime/clicko-dev"
    os.environ.update(ENVIRONMENT="development", DATABASE_URL="sqlite:///" + (runtime / "studios/records.sqlite").as_posix(),
                      STORAGE_PATH=str(runtime / "studios/uploads"))
    from app.database import SessionLocal
    from app.domain.studios.contracts import CreateStudioDocumentRequest
    from app.domain.studios.craft import CraftCommandRequestV1, CraftMigrationRequestV1, CraftRenderRequestV1
    from app.domain.studios.editing_resources import ResourceMetadataV1
    from app.models import CreativeDocument, User
    from app.services.object_storage import get_object_storage
    from app.services.studios import craft, editing_resources
    from app.services.studios.compatibility import record_to_contract
    from app.services.studios.jobs import execute_job_once
    from app.services.studios.kernel import create_document

    files = prepare(source, output)
    key = "orbita-reference-mcp-20261112"
    with SessionLocal() as db:
        prior = record_to_contract(db.get(CreativeDocument, "1b295922-5884-411b-a54f-eebf1da83593"))
        user = db.get(User, prior.actor_id)
        request = CreateStudioDocumentRequest.model_validate({
            "workspaceId": prior.workspace_id, "contentType": "video", "brandRevision": prior.brand_memory_ref.revision,
            "title": "ÓRBITA · semente comum com sete planos e duas pistas",
            "brief": {"objective": BRIEF.split("\n\n", 1)[0], "audience": "Público de cinema independente no celular", "format": "video"},
            "composition": {"pages": [{"id": "main", "width": 540, "height": 960, "durationMs": 18000, "layers": []}],
                            "mediaTimeline": {"frameRate": {"numerator": 24, "denominator": 1}, "durationFrames": 432, "tracks": []}},
        })
        seed = create_document(db, request, user, creation_key=key + "-seed")
        if seed.revision == 1:
            craft.migrate(db, seed, CraftMigrationRequestV1(engine="effectcraft", expectedRevision=1), user, key + "-seed-migrate")
        seed_info = record_to_contract(seed)
        if not seed_info.assets:
            for i, file in enumerate(files):
                footage = i < len(SHOTS)
                metadata = ResourceMetadataV1(kind="video" if footage else "sound_effect",
                    description=SHOTS[i][3] if footage else "Pista estéreo editável original",
                    sourceUrl="https://studio.blender.org/projects/tears-of-steel/?asset=42" if footage else None,
                    usageEvidence=("Tears of Steel © Blender Foundation · CC BY 3.0 · excerto sem áudio e reenquadrado"
                                   if footage else "Síntese original local para este estudo"))
                asset = editing_resources.store_resource(db, seed.workspace_id, file.name, file, metadata, user.id)
                editing_resources.attach_resource(db, seed, asset.id, seed.revision)
            db.commit()
        contract = record_to_contract(seed)
        if contract.revision == 11:
            craft.commands(db, seed, CraftCommandRequestV1(expectedRevision=11, label="Preparar nove fontes editáveis",
                commands=[{"id": "asset.import", "params": {"assetId": asset.id, "addToComp": True}}
                          for asset in contract.assets]), user, key + "-seed-media")
        contract = record_to_contract(seed)
        assert contract.revision == 12 and len(contract.assets) == len(files), contract.revision
        assets = [a.model_dump(mode="json", by_alias=True) for a in contract.assets]
        with craft.native_bundle(db, seed, contract.native_editor_state) as bundle:
            shutil.copyfile(bundle, output / "orbita-semente-comum.zip")

        def clone(title, suffix):
            branch = create_document(db, CreateStudioDocumentRequest.model_validate({
                **request.model_dump(mode="json", by_alias=True), "title": title, "assets": assets,
            }), user, creation_key=key + suffix)
            if branch.revision == 1:
                with craft.workspace_files(db, seed, contract.native_editor_state) as (_dir, params, _manifests):
                    craft.save_native(db, branch, user, Path(params["nativePath"]), engine="effectcraft",
                        expected_revision=1, key=key + suffix + "-clone",
                        asset_manifest=contract.native_editor_state.asset_manifest, font_manifest=contract.native_editor_state.font_manifest)
                assert record_to_contract(branch).native_editor_state.checksum_sha256 == contract.native_editor_state.checksum_sha256
            return branch

        clicko = clone("ÓRBITA · braço Opus pela Clicko", "-clicko")
        ref = clone("ÓRBITA · anúncio de referência local", "-reference")
        if ref.revision == 2:
            craft.commands(db, ref, CraftCommandRequestV1(expectedRevision=2, label="Montagem de referência, luz, copy e som",
                commands=[{"id": "script.run", "params": {"code": (CASE / "referencia.jsx").read_text(encoding="utf-8")}}]),
                user, key + "-editorial")
        cut = record_to_contract(ref)
        job, _ = craft.create_render_job(db, ref, CraftRenderRequestV1(expectedRevision=cut.revision, format="mp4", quality="high"),
                                         user, key + "-render")
        print(json.dumps({"reference": ref.id, "seed": seed.id, "clicko": clicko.id, "job": job.id}), flush=True)
        if job.status in {"queued", "retrying"}:
            execute_job_once(db, job)
            db.refresh(job)
        assert job.status == "succeeded", (job.status, job.error_code)
        artifact = job.result_payload["artifact"]
        asset = craft.scoped_asset(db, ref.workspace_id, artifact["assetId"], artifact["checksumSha256"])
        with get_object_storage(asset.storage_backend).materialize(asset.storage_key) as material:
            shutil.copyfile(material, output / "orbita-referencia.mp4")
        with craft.native_bundle(db, ref, cut.native_editor_state) as bundle:
            shutil.copyfile(bundle, output / "orbita-referencia-editavel.zip")
        inventory = json.loads((output / "materiais.json").read_text(encoding="utf-8"))
        for row, registered in zip(inventory, contract.assets, strict=True):
            assert row["sha256"] == registered.checksum
            row["assetId"] = registered.id
        (output / "materiais.json").write_text(json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8")
        (output / "briefing.txt").write_text(BRIEF, encoding="utf-8")
        receipt = {"referenceId": ref.id, "referenceRevision": cut.revision, "seedId": seed.id,
                   "seedSha256": contract.native_editor_state.checksum_sha256, "clickoId": clicko.id,
                   "effectCraftBuild": cut.native_editor_state.build_id, "referenceJobId": job.id,
                   "artifact": artifact, "apiSpendUsd": 0}
        (output / "referencia-recibo.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(receipt, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    main(args.source.resolve(), args.output.resolve())
