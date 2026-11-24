"""Unpaid controlled movement render and forensic audit of the existing ÓRBITA media."""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
OUTPUTS = Path("C:/Users/edugu/OneDrive/Documentos/res/output")
KEY = "effectcraft-movement-diagnosis-20261113-v2"
CODE = '''var c=app.project.activeItem;
function marker(name,color,y){
 var l=c.layers.addSolid(color,name,28,28,1,2);
 var p=l.property("ADBE Transform Group").property("ADBE Position");
 p.setValueAtTime(0,[50,y]);p.setValueAtTime(1.5,[430,y]);return p;
}
var straight=marker("Linear",[1,0,0],90);
var eased=marker("Easing",[0,1,0],210);
eased.setInterpolationTypeAtKey(1,KeyframeInterpolationType.BEZIER,KeyframeInterpolationType.BEZIER);
eased.setInterpolationTypeAtKey(2,KeyframeInterpolationType.BEZIER,KeyframeInterpolationType.BEZIER);
eased.setTemporalEaseAtKey(1,[new KeyframeEase(0,33.333333)],[new KeyframeEase(0,33.333333)]);
eased.setTemporalEaseAtKey(2,[new KeyframeEase(0,33.333333)],[new KeyframeEase(0,33.333333)]);
function label(text,y){var l=c.layers.addText(text);var d=l.property("ADBE Text Properties").property("ADBE Text Document");
var v=d.value;v.fontSize=21;v.fillColor=[1,1,1];d.setValue(v);
l.property("ADBE Transform Group").property("ADBE Position").setValue([150,y]);}
label("Linear",40);label("Com easing",160);
"Controlled movement";'''


def run(*args):
    return subprocess.check_output(list(map(str, args)), timeout=120)


def decode(path):
    return np.frombuffer(run("ffmpeg", "-v", "error", "-threads", "1", "-i", path, "-an", "-threads", "1",
        "-pix_fmt", "rgb24", "-f", "rawvideo", "-"), dtype=np.uint8).reshape(-1, 320, 480, 3)


def evidence(output):
    direct, integrated = decode(output / "direto.mp4"), decode(output / "clicko.mp4")
    assert direct.shape == integrated.shape == (60, 320, 480, 3)
    observations = []
    positions = {"linear": [], "eased": []}
    for i, frame in enumerate(integrated):
        red = (frame[:, :, 0] > 180) & (frame[:, :, 1] < 70) & (frame[:, :, 2] < 70)
        green = (frame[:, :, 1] > 180) & (frame[:, :, 0] < 70) & (frame[:, :, 2] < 70)
        centers = [float(np.where(mask)[1].mean()) + .5 for mask in (red, green)]
        u = min(1, max(0, i / 30 / 1.5))
        expected = [50 + 380*u, 50 + 380*(3*u*u - 2*u*u*u)]
        observations.append({"frame": i, "centers": centers, "expected": expected})
        for name, center in zip(positions, centers):
            positions[name].append(center)
    error = max(abs(a-b) for row in observations for a, b in zip(row["centers"], row["expected"]))
    sheet = Image.new("RGB", (480*3, 344*2), "#11151d")
    draw = ImageDraw.Draw(sheet)
    for k, frame in enumerate((8, 15, 23, 37, 45, 52)):
        x, y = k % 3 * 480, k // 3 * 344
        sheet.paste(Image.fromarray(integrated[frame]), (x, y+24))
        draw.text((x+6, y+5), f"{frame/30:.3f} s", fill="white")
    sheet.save(output / "comparacao-easing.jpg", quality=93)
    return {"decodedFrames": 60, "directAndClickoPixelsEqual": bool(np.array_equal(direct, integrated)),
            "maximumPositionErrorPixels": error, "tolerancePixels": 2, "positions": observations,
            "geometryPassed": error <= 2, "apiSpendUsd": 0}


def media_audit():
    directory = OUTPUTS / "clicko-miolo-transferencia-2026-11-13/orbita/materiais"
    sources = OUTPUTS / "clicko-orbita-referencia-mcp-2026-11-12/materiais"
    rows = (("travessia", "07-travessia.mp4", .08, 2.18, 2.2),
            ("detalhe", "05-maquina.mp4", .08, 1.22, 1.4),
            ("encontro", "05-maquina.mp4", 1.47, 1.49, 2.4))
    results = []
    for name, source, start, length, duration in rows:
        probe = json.loads(run("ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", directory / (name + ".mp4")))
        # Reproduce the exact frame duplication before the intermediate H.264 encoding.
        picture = "scale=540:960:force_original_aspect_ratio=increase,crop=540:960" if name == "travessia" else "scale=540:960"
        hashes = run("ffmpeg", "-v", "error", "-ss", start, "-i", sources / source, "-t", duration, "-an",
            "-vf", f"trim=duration={length},setpts={duration/length:.8f}*(PTS-STARTPTS),{picture},fps=30,tpad=stop_duration=0.12:stop_mode=clone",
            "-threads", 1, "-f", "framemd5", "-").decode()
        frames = [line.split(",")[-1].strip() for line in hashes.splitlines() if line and not line.startswith("#")]
        duplicate = sum(a == b for a, b in zip(frames, frames[1:]))
        video = next(s for s in probe["streams"] if s["codec_type"] == "video")
        results.append({"name": name, "source": source, "sourceSeconds": length, "outputSeconds": duration,
            "dimensions": [video["width"], video["height"]], "sourceFps": 24,
            "nominalOutputFps": 30, "decodedPreEncodeFrames": len(frames), "uniquePreEncodeFrames": len(set(frames)),
            "consecutiveDuplicatedFrames": duplicate, "repeatedFrameFraction": duplicate/max(1,len(frames)-1),
            "theoreticalActionFramesPerSecond": 24*length/duration})
    return results


def main(output):
    runtime = ROOT / ".codex-runtime/clicko-dev/studios"
    os.environ.update(ENVIRONMENT="development", DATABASE_URL="sqlite:///" + (runtime / "records.sqlite").as_posix(),
                      STORAGE_PATH=str(runtime / "uploads"))
    sys.path.insert(0, str(ROOT / "backend"))
    from app.database import SessionLocal
    from app.domain.studios.contracts import CreateStudioDocumentRequest
    from app.domain.studios.craft import CraftCommandRequestV1, CraftMigrationRequestV1, CraftRenderRequestV1
    from app.models import CreativeDocument, User
    from app.providers.studios.craft import call_engine
    from app.services.object_storage import get_object_storage
    from app.services.studios import craft
    from app.services.studios.compatibility import record_to_contract
    from app.services.studios.jobs import execute_job_once
    from app.services.studios.kernel import create_document
    output.mkdir(parents=True, exist_ok=True)
    with SessionLocal() as db:
        origin = db.get(CreativeDocument, "b6970aab-20ba-48aa-9c21-1b0fc2607a09")
        user = db.get(User, record_to_contract(origin).actor_id)
        doc = create_document(db, CreateStudioDocumentRequest.model_validate({
            "workspaceId": origin.workspace_id, "title": "Diagnóstico local · curva de movimento",
            "contentType": "video", "brief": {"objective": "Comprovar curva de animação", "audience": "Teste interno"},
            "composition": {"pages": [{"id": "main", "width": 480, "height": 320, "durationMs": 2000, "layers": [], "background": "#10141c"}],
                            "mediaTimeline": {"frameRate": {"numerator": 30, "denominator": 1}, "durationFrames": 60, "tracks": []}},
        }), user, creation_key=KEY)
        if doc.revision == 1:
            craft.migrate(db, doc, CraftMigrationRequestV1(engine="effectcraft", expectedRevision=1), user, KEY+"-migrate")
        if doc.revision == 2:
            craft.commands(db, doc, CraftCommandRequestV1(expectedRevision=2, commands=[{"id": "script.run", "params": {"code": CODE}}]), user, KEY+"-edit")
        state = record_to_contract(doc).native_editor_state
        started = time.monotonic()
        with craft.workspace_files(db, doc, state) as (_, params, _):
            path = Path(params["nativePath"]).parent / "direct.mp4"
            call_engine("effectcraft", "render.export", {**params, "outputPath": str(path), "format": "mp4", "quality": "high"})
            shutil.copyfile(path, output / "direto.mp4")
        direct_seconds = time.monotonic() - started
        job, _ = craft.create_render_job(db, doc, CraftRenderRequestV1(expectedRevision=doc.revision, format="mp4", quality="high"), user, KEY+"-render")
        if job.status in {"queued", "retrying"}:
            execute_job_once(db, job)
            db.refresh(job)
        assert job.status == "succeeded", job.error_message
        artifact = job.result_payload["artifact"]
        asset = craft.scoped_asset(db, doc.workspace_id, artifact["assetId"], artifact["checksumSha256"])
        with get_object_storage(asset.storage_backend).materialize(asset.storage_key) as path:
            shutil.copyfile(path, output / "clicko.mp4")
        with craft.native_bundle(db, doc, state) as bundle:
            shutil.copyfile(bundle, output / "controle-editavel.zip")
        receipt = {"documentId": doc.id, "revision": doc.revision, "buildId": state.build_id,
                   "nativeSha256": state.checksum_sha256, "directRenderSeconds": direct_seconds,
                   "renderJobId": job.id, "apiSpendUsd": 0, "conformance": evidence(output), "sourceMedia": media_audit()}
        (output / "script.jsx").write_text(CODE, encoding="utf-8")
        (output / "diagnostico.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
        print(json.dumps({"conformance": {k:v for k,v in receipt["conformance"].items() if k!="positions"}, "sourceMedia": receipt["sourceMedia"]}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    main(parser.parse_args().output.resolve())
