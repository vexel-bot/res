"""Render ÓRBITA, product and interface locally via Clicko's native project services."""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
KEY = "miolo-transferencia-20261113-v1"


def sha(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def ff(*args):
    return subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-y", *map(str, args)], check=True,
                          capture_output=True, timeout=120).stdout


def probe(path):
    return json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-show_format", "-show_streams",
                                               "-of", "json", str(path)], timeout=20))


def clip(src, dst, start, length, output_length, size, crop):
    w, h = size
    color = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}" if crop else f"scale={w}:{h}"
    ff("-ss", start, "-i", src, "-t", output_length, "-an",
       "-vf", f"trim=duration={length},setpts={output_length/length:.8f}*(PTS-STARTPTS),{color},fps=30,tpad=stop_duration=0.12:stop_mode=clone",
       "-threads", 2, "-c:v", "libx264", "-crf", 16, "-pix_fmt", "yuv420p", dst)


def prepared(output, source_root, case):
    materials = output / "materiais"
    materials.mkdir(exist_ok=True)
    footage = source_root / "clicko-orbita-referencia-mcp-2026-11-12" / "materiais"
    ui = source_root / "clicko-timeline-real-2026-11-10" / "timeline-clicko-ampliada.mp4"
    product = ROOT.parent / "Torta mousse oreo.mov"
    if case == "orbita":
        rows = [
            (footage / "07-travessia.mp4", "travessia", .08, 2.18, 2.2, (540, 960), True),
            (footage / "05-maquina.mp4", "detalhe", .08, 1.22, 1.4, (540, 960), False),
            (footage / "05-maquina.mp4", "encontro", 1.47, 1.49, 2.4, (540, 960), False),
        ]
    elif case == "produto":
        rows = [(product, "giro", 4.53, 2.73, 2.73, (540, 960), False),
                (product, "camadas", 9.53, 2.30, 2.30, (540, 960), False)]
    else:
        rows = [(ui, "divisao-real", .25, 4.8, 4.8, (540, 960), False)]
    from app.services.studios.craft_source_media import shot_candidates
    inventory = {}
    results = []
    for src, name, start, length, duration, size, crop in rows:
        if src not in inventory:
            seconds = float(probe(src)["format"]["duration"])
            identity = {"assetId": src.name, "checksumSha256": sha(src), "path": str(src)}
            window = {"start": 4, "duration": 8} if case == "produto" else {}
            inventory[src] = shot_candidates(identity, seconds, time.monotonic()+25, **window)
        dest = materials / (name + ".mp4")
        clip(src, dest, start, length, duration, size, crop)
        info = {"source": src.name, "sourceHash": inventory[src]["checksumSha256"], "sourceStart": start,
                "sourceEnd": round(start+length, 4), "outputSeconds": duration, "hash": sha(dest)}
        results.append((dest, info))
    return results, list(inventory.values())


def proof_script(case, seconds):
    base = """
var c=app.project.activeItem;
function tr(l,n){return l.property("ADBE Transform Group").property(n);}
function span(l,a,b){l.startTime=a;l.inPoint=a;l.outPoint=b;tr(l,"ADBE Position").setValue([270,480]);}
function title(s,y,a,b,size,color){
  var l=c.layers.addText(s),p=l.property("ADBE Text Properties").property("ADBE Text Document"),d=p.value;
  d.font="Inter-Bold";d.fontSize=size;d.justification=ParagraphJustification.CENTER_JUSTIFY;d.fillColor=color;p.setValue(d);
  span(l,a,b);tr(l,"ADBE Position").setValue([270,y]);return l;
}
function plate(name,w,h,x,y,a,b,color){
  var l=c.layers.addSolid(color,name,w,h,1,c.duration);span(l,a,b);
  tr(l,"ADBE Position").setValue([x,y]);return l;
}
"""
    if case == "produto":
        return base + f"""
c.duration={seconds};
var close=c.layer(1),giro=c.layer(2);
span(giro,0,2.73);span(close,2.73,{seconds});
plate("Área de leitura",540,132,270,66,0,{seconds},[.15,.055,.09]);
title("Torta mousse",66,0,{seconds},52,[1,.93,.88]);
title("Giro da fatia",106,.12,2.73,27,[1,.64,.71]);
title("As camadas de perto",106,2.73,{seconds},27,[1,.64,.71]);
"""
    return base + f"""
c.duration={seconds};
span(c.layer(1),0,{seconds});
"""


def main(output, case, phase):
    runtime = ROOT / ".codex-runtime/clicko-dev/studios"
    os.environ.update(ENVIRONMENT="development", DATABASE_URL="sqlite:///" + (runtime / "records.sqlite").as_posix(),
                      STORAGE_PATH=str(runtime / "uploads"))
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

    output.mkdir(parents=True, exist_ok=True)
    source_root = output.parents[1]
    prior = json.loads((source_root / "clicko-quality-cycle-2026-11-13/revisao-local/recibo-revisao.json").read_text(encoding="utf-8"))
    file = output / "edicao.json"
    key = KEY + "-" + case + ("-compact-media" if case == "orbita" else "")
    with SessionLocal() as db:
        origin = db.get(CreativeDocument, prior["documentId"])
        source = record_to_contract(origin)
        user = db.get(User, source.actor_id)
        assert source.native_editor_state.checksum_sha256 == prior["nativeSha256"]
        title = {"orbita": "ÓRBITA · miolo remontado", "produto": "Torta mousse · giro e camadas",
                 "interface": "Clicko · divisão de clipe contínua"}[case]
        if file.exists():
            edit = json.loads(file.read_text(encoding="utf-8"))
            branch = db.get(CreativeDocument, edit["documentId"])
            assert branch.revision == edit["revision"]
        else:
            materials, inventory = prepared(output, source_root, case)
            seconds = round(sum(row["outputSeconds"] for _, row in materials), 6)
            composition = source.composition.model_dump(mode="json", by_alias=True) if case == "orbita" else {
                "pages": [{"id": "main", "width": 540, "height": 960, "durationMs": round(seconds*1000), "layers": []}],
                "mediaTimeline": {"frameRate": {"numerator": 30, "denominator": 1},
                                  "durationFrames": round(seconds*30), "tracks": []},
            }
            branch = create_document(db, CreateStudioDocumentRequest.model_validate({
                "workspaceId": origin.workspace_id, "contentType": "video", "brandRevision": source.brand_memory_ref.revision,
                "title": title, "brief": {"objective": title, "audience": "Visualização em celular", "format": "video"},
                "composition": composition,
                "assets": [item.model_dump(mode="json", by_alias=True) for item in source.assets] if case == "orbita" else [],
            }), user, creation_key=key)
            if branch.revision == 1 and case == "orbita":
                native = source.native_editor_state
                with craft.workspace_files(db, origin, native) as (_, params, _):
                    craft.save_native(db, branch, user, Path(params["nativePath"]), engine="effectcraft",
                        expected_revision=1, key=key+"-clone", asset_manifest=native.asset_manifest, font_manifest=native.font_manifest)
            elif branch.revision == 1:
                craft.migrate(db, branch, CraftMigrationRequestV1(expectedRevision=1, engine="effectcraft"), user, key+"-migrate")
            commands = []
            for path, info in materials:
                metadata = ResourceMetadataV1(kind="video", description=path.stem,
                    usageEvidence={"orbita": "Tears of Steel © Blender Foundation, CC BY 3.0, excerto editado",
                        "produto": "Gravação local existente, usada para prova interna",
                        "interface": "Captura de operação real da Clicko"}[case])
                asset = editing_resources.store_resource(db, branch.workspace_id, path.name, path, metadata, user.id)
                info["assetId"] = asset.id
                commands.append({"id": "asset.import", "params": {"assetId": asset.id, "addToComp": True}})
            script = (ROOT/"benchmarks/studios/orbita/miolo-local.jsx").read_text(encoding="utf-8") if case == "orbita" else proof_script(case, seconds)
            (output/"montagem.jsx").write_text(script, encoding="utf-8")
            commands.append({"id": "script.run", "params": {"code": script}})
            answer = craft.commands(db, branch, CraftCommandRequestV1(expectedRevision=branch.revision, label=title, commands=commands),
                                    user, key+"-edit")
            db.commit()
            edit = {"documentId": branch.id, "revision": branch.revision, "receiptId": answer["receiptId"],
                    "sources": [row for _, row in materials], "scan": inventory, "apiSpendUsd": 0}
            write(file, edit)
        current = record_to_contract(branch)
        if phase == "preview":
            fps = 30
            times = [5.45,6.7,7.65,8.9,10.6,11.2] if case == "orbita" else [0.35,1.6,2.95,4.2]
            for second in times:
                (output / f"preview-{second:.2f}.png").write_bytes(craft.render_frame(db, branch, frame=round(second*fps)))
            return
        start = time.monotonic()
        job, _ = craft.create_render_job(db, branch, CraftRenderRequestV1(expectedRevision=current.revision,
            format="mp4", quality="high"), user, key+"-render")
        if job.status in {"queued", "retrying"}:
            execute_job_once(db, job)
            db.refresh(job)
        if job.status != "succeeded":
            raise RuntimeError(f"{case} render {job.status}: {job.error_code}")
        artifact = job.result_payload["artifact"]
        asset = craft.scoped_asset(db, branch.workspace_id, artifact["assetId"], artifact["checksumSha256"])
        with get_object_storage(asset.storage_backend).materialize(asset.storage_key) as media:
            shutil.copyfile(media, output / f"{case}.mp4")
        with craft.native_bundle(db, branch, current.native_editor_state) as bundle:
            shutil.copyfile(bundle, output / f"{case}-editavel.zip")
        db.refresh(origin)
        assert origin.revision == source.revision and record_to_contract(origin).native_editor_state.checksum_sha256 == prior["nativeSha256"]
        assert sha(output / f"{case}.mp4") == artifact["checksumSha256"]
        write(output/"recibo.json", {**edit, "sourcePreserved": True, "renderJobId": job.id, "artifact": artifact,
                                     "renderSeconds": round(time.monotonic()-start, 3), "editor": "Codex via Clicko EffectCraft"})
        print(case, artifact["durationMs"], artifact["checksumSha256"], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("case", choices=("orbita", "produto", "interface"))
    parser.add_argument("phase", choices=("preview", "render"))
    args = parser.parse_args()
    main(args.output.resolve()/args.case, args.case, args.phase)
