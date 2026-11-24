"""Exercise the installed EffectCraft command and rendering paths without a paid model."""

import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
from app.providers.studios.craft import require_capability
from app.services.studios.craft_agent import Draft
from app.services.studios.craft_review import review_draft
from PIL import Image, ImageChops


def run(seed, output):
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="clicko-native-3d-") as folder:
        root = Path(folder)
        native = root / "source.ecproj"
        shutil.copyfile(seed, native)
        draft = Draft(SimpleNamespace(engine="effectcraft", migration_warnings=[]), root,
                      {"nativePath": str(native), "mediaRoot": str(root), "media": []},
                      require_capability("effectcraft"), SimpleNamespace(expected_revision=1), time.monotonic() + 360)
        script = """var c=app.project.activeItem; while(c.numLayers)c.layer(1).remove();
c.duration=2;c.frameRate=24;c.width=320;c.height=240;
var title=c.layers.addText('3D');title.name='Extrusion';title.threeDLayer=true;
var transform=title.property('ADBE Transform Group');
transform.property('ADBE Position').setValue([175,185,-30]);"""
        changes = [
            {"id": "script.run", "params": {"code": script}},
            {"id": "comp.renderer", "params": {"renderer": "advanced3d"}},
            {"id": "layer.new3dPrimitive", "params": {"kind": "cube", "width": 83, "height": 54, "depth": 42,
                "position": [145, 115, 0], "baseColor": [0.82, 0.25, 0.1], "name": "Volume"}},
            {"id": "layer.new3dPrimitive", "params": {"kind": "sphere", "radius": 25,
                "position": [173, 110, -40], "baseColor": [0.1, 0.62, 0.35], "name": "Occluder"}},
            {"id": "layer.newLight", "params": {"kind": "Point", "position": [70, 70, -200], "intensity": 175}},
            {"id": "layer.newCamera", "params": {"type": "twoNode", "position": [150, 122, -450],
                "poi": [160, 120, 0], "zoom": 460, "name": "Dolly"}},
        ]
        draft.run("edit_project", {"commands": changes})
        draft.run("run_motion_script", {"code": """var c=app.project.activeItem;
var cam=c.layer('Dolly').property('ADBE Transform Group').property('ADBE Position');
cam.setValueAtTime(0,[80,118,-455]);cam.setValueAtTime(1.8,[305,145,-405]);
var t=c.layer('Extrusion');app.project.activeItem;
var geo=t.property('ADBE Extrsn Options Group');
if(geo)geo.property('ADBE Extrsn Depth').setValue(16);"""})
        frames=[]
        for index, frame in enumerate([2, 20, 40]):
            target = output / f"native-3d-{index}.png"
            draft.call("render.frame", outputPath=str(root / target.name), frame=frame, format="png")
            shutil.copyfile(root / target.name, target)
            with Image.open(target) as picture:
                frames.append(picture.convert("RGB"))
        assert all(frame.getextrema()[0][1] - frame.getextrema()[0][0] > 18 for frame in frames)
        assert ImageChops.difference(frames[0], frames[2]).getbbox()
        review = review_draft(draft, {"startSeconds": 0, "durationSeconds": 2, "sampling": "overview", "pageSize": 4})
        shutil.copyfile(review["path"], output / "native-3d.mp4")
        (output / "inspection.json").write_text(json.dumps(draft.project, indent=2), encoding="utf8")


if __name__ == "__main__":
    run(Path(sys.argv[1]), Path(sys.argv[2]))
