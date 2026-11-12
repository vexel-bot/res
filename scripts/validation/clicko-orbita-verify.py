"""Measure animation, typography and final audio on the actual Craft renders."""
import argparse
import hashlib
import json
import math
import os
import subprocess
import time
from pathlib import Path
from zipfile import ZipFile

import numpy as np


def audio(path, seconds):
    result = subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-i", str(path), "-t", str(seconds),
        "-vn", "-ac", "1", "-ar", "24000", "-f", "f32le", "pipe:1"], capture_output=True, check=True, timeout=60)
    return np.frombuffer(result.stdout, dtype="<f4").astype(np.float64)


def main(output):
    root = Path(".codex-runtime/clicko-dev").resolve()
    os.environ.update(ENVIRONMENT="development", DATABASE_URL="sqlite:///" + (root / "studios/records.sqlite").as_posix(),
                      STORAGE_PATH=str(root / "studios/uploads"))
    from app.database import SessionLocal
    from app.models import CreativeDocument
    from app.providers.studios.craft import require_capability
    from app.services.studios import craft
    from app.services.studios.compatibility import record_to_contract
    from app.services.studios.craft_agent import Draft
    from app.services.studios.craft_flash import inspect_video_flash

    receipt = json.loads((output / "exercicio-recibo.json").read_text(encoding="utf-8"))
    video = output / "orbita-recuo-corrigido.mp4"
    assert hashlib.sha256(video.read_bytes()).hexdigest() == receipt["artifact"]["checksumSha256"]
    source_video = output.parent / "clicko-orbita-aprendizado-2026-11-12/orbita-aprendizado.mp4"
    source_audio = audio(source_video, 17.75)
    repaired_audio = audio(video, 17.75)
    assert len(source_audio) == len(repaired_audio)
    fade = []
    for start, end in [(3, 6), (16, 16.3), (16.6, 16.85), (17.1, 17.25), (17.42, 17.65)]:
        sample = slice(round(start * 24000), round(end * 24000))
        reference = np.linalg.norm(source_audio[sample])
        gain = 20 * math.log10(max(1e-12, np.linalg.norm(repaired_audio[sample]) / reference))
        fade.append({"startSeconds": start, "endSeconds": end, "gainRelativeToOriginalDb": round(gain, 2)})
    assert 5.5 <= fade[0]["gainRelativeToOriginalDb"] <= 8.5, fade
    assert fade[-1]["gainRelativeToOriginalDb"] <= -25, fade
    assert np.max(np.abs(repaired_audio)) < .8

    code = '''var c=app.project.item(1); var a=[];
var screen=c.layer("TELA (rig)"), first=c.layer("O futuro"), second=c.layer("cabe num curta.");
for(var i=0;i<=104;i++){ var t=i/24; a.push({frame:i,t:t,scale:screen.transform.scale.valueAtTime(t,false)[0],
    first:first.transform.opacity.valueAtTime(t,false),second:second.transform.opacity.valueAtTime(t,false)}); } a;'''
    with SessionLocal() as db:
        evidence = {}
        for label, identifier in (("before", receipt["sourceId"]), ("after", receipt["exerciseId"])):
            record = db.get(CreativeDocument, identifier)
            state = record_to_contract(record).native_editor_state
            with craft.workspace_files(db, record, state) as (directory, params, _manifests):
                draft = Draft(state, directory, params, require_capability("effectcraft"), None, time.monotonic() + 90)
                project_path = Path(params["nativePath"])
                original_bytes = project_path.read_bytes()
                faces = draft.run("inspect_motion_fonts", {"faces": [{"font": "Inter-Bold"}, {"font": "Inter-Black"}]})
                font, fallback = [entry["resolved"] for entry in faces["faces"]]
                assert fallback == {"family": "Inter", "style": "Regular", "missing": True}, fallback
                assert draft.batches == 0 and project_path.read_bytes() == original_bytes
                result = draft.call("engine.execute", outputPath=str(directory / "proof.ecproj"),
                                    commands=[{"id": "script.run", "params": {"code": code}}])
                craft.require_command_success(result)
                samples = result["results"][0]["result"]
                peak = max(abs(a["scale"] - b["scale"]) * 24 for a, b in zip(samples[1:], samples))
                evidence[label] = {"peakScalePercentagePointsPerSecond": round(peak, 3),
                    "frame63": samples[63], "frame81": samples[81], "font": font, "fallback": fallback,
                    "samples": samples}
    assert evidence["after"]["peakScalePercentagePointsPerSecond"] < .75 * evidence["before"]["peakScalePercentagePointsPerSecond"]
    assert evidence["after"]["frame63"]["first"] == evidence["after"]["frame63"]["second"] == 0
    assert evidence["after"]["frame81"]["first"] == evidence["after"]["frame81"]["second"] == 100
    assert evidence["after"]["font"] == {"family": "Inter", "style": "Bold", "missing": False}

    with ZipFile(output / "orbita-exercicio-corrigido.zip") as archive:
        assert archive.testzip() is None
        project = json.loads(archive.read("001.ecproj"))
        raw = project["items"]["1"]["kind"]
        text_fonts = []
        for layer in raw["layers"]:
            for group in layer["props"]["children"]:
                if group.get("match") == "text":
                    text_fonts.extend(child["value"]["v"]["font"] for child in group["children"]
                                      if child.get("match") == "sourceText")
    assert text_fonts and set(text_fonts) == {"Inter-Bold"}, text_fonts
    flash = inspect_video_flash(video)
    assert flash["status"] == "pass", flash
    result = {"verified": True, "apiSpendUsd": 0, "evidence": evidence, "fade": fade, "flash": flash,
              "projectFontRequests": text_fonts, "sourceUnchanged": receipt["sourceUnchanged"],
              "limits": "Frame measurements and native property samples. Subjective listening and audience comprehension are outside this test."}
    (output / "verificacao-local.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"verified": True, "beforePeak": evidence["before"]["peakScalePercentagePointsPerSecond"],
                      "afterPeak": evidence["after"]["peakScalePercentagePointsPerSecond"], "fade": fade, "flash": flash}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    main(parser.parse_args().output.resolve())
