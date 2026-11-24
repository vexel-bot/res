"""Pixel/signal calibration and genuine Craft/Clicko/Canvas conformance, never paid inference."""
import base64
import json
import os
import subprocess
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from app.services.studios.craft_quality_checks import (
    inspect_audio, inspect_flash, inspect_marker, inspect_occlusion, inspect_text_ink, score_controls,
)


def forbidden(*args, **kwargs):
    raise AssertionError("Paid provider must not run during local qualification")


@pytest.fixture(autouse=True)
def no_paid_provider(monkeypatch):
    from app.providers.studios.universal_llm import UniversalLLMPlanner
    monkeypatch.setattr(UniversalLLMPlanner, "craft_turn", forbidden)
    monkeypatch.setattr(UniversalLLMPlanner, "plan", forbidden)


def test_marker_uses_actual_pixels_and_tolerance():
    image = Image.new("RGBA", (100, 100))
    ImageDraw.Draw(image).rectangle((20, 30, 39, 49), fill=(255, 0, 0))
    assert inspect_marker(image, (255, 0, 0), [20, 30, 40, 50])["status"] == "pass"
    assert inspect_marker(image, (255, 0, 0), [25, 30, 45, 50])["status"] == "defect"
    assert inspect_marker(image, (0, 255, 0), [20, 30, 40, 50])["observedBounds"] is None


def test_clipping_and_occlusion_have_correct_and_defective_controls():
    image = Image.new("RGBA", (300, 100))
    draw = ImageDraw.Draw(image)
    draw.rectangle((20, 20, 99, 79), fill="white")
    assert inspect_text_ink(image)["status"] == "pass"
    draw.rectangle((0, 20, 9, 79), fill="white")
    assert inspect_text_ink(image)["status"] == "defect"
    draw.rectangle((80, 40, 110, 80), fill=(0, 255, 0, 255))
    assert inspect_occlusion(image, front_point=(90, 60), front_color=(0, 255, 0), transparent_point=(299, 99))["status"] == "pass"
    assert inspect_occlusion(image, front_point=(90, 60), front_color=(255, 0, 0))["status"] == "defect"


def test_brightness_is_reported_without_condemning_intentional_light():
    frames = [(i, Image.new("RGB", (60, 60), "white" if 5 <= i <= 6 else "#161616")) for i in range(24)]
    assert inspect_flash(frames, 30)["status"] == "defect"
    deliberate = inspect_flash(frames, 30, intentional=True)
    assert deliberate["status"] == "pass" and deliberate["events"]
    correct = inspect_flash([(i, Image.new("RGB", (60, 60), "#161616")) for i in range(24)], 30)
    assert correct["status"] == "pass" and not correct["events"]


def test_silence_and_optional_audio_do_not_create_false_claims():
    assert inspect_audio(None, required=True)["status"] == "defect"
    assert inspect_audio(None, required=False)["status"] == "pass"
    result = score_controls([
        {"id": "missing", "expectedDefect": True, "observed": inspect_audio(None)},
        {"id": "intentional", "expectedDefect": False, "observed": inspect_audio(None, required=False)},
    ])
    assert result["detectedDefects"] == 1 and result["falsePositiveCount"] == 0


@pytest.mark.skipif(os.environ.get("CLICKO_TEST_REAL_CRAFT") != "1", reason="genuine built Craft runtime")
def test_same_native_motion_through_clicko_direct_and_canvas(client, tmp_path):
    from conftest import register
    from app.database import SessionLocal
    from app.providers.studios.craft import call_engine
    from app.routers.studios import owned_document
    from app.services.studios import craft
    from app.services.studios.compatibility import record_to_contract
    from app.services.studios.craft_quality_checks import sha256

    token, workspace = register(client, "quality-conformance@example.com")
    auth = {"Authorization": "Bearer " + token}
    root = "/api/v1/studios/v1/documents"
    reply = client.post(root, headers=auth, json={
        "workspaceId": workspace, "contentType": "video", "title": "Local pixel conformance",
        "brief": {"objective": "Deterministic execution fixture", "audience": "QA"},
        "composition": {"pages": [{"id": "main", "width": 320, "height": 320, "durationMs": 2000,
                                   "background": "#00000000", "layers": []}],
                        "mediaTimeline": {"frameRate": {"numerator": 30, "denominator": 1}, "durationFrames": 60, "tracks": []}},
    })
    assert reply.status_code == 201, reply.text
    doc = reply.json()
    path = root + '/' + doc["documentId"] + '/craft'
    migrated = client.post(path + '/migrate', headers={**auth, "Idempotency-Key": "quality-migrate"},
                           json={"engine": "effectcraft", "expectedRevision": doc["revision"]})
    assert migrated.status_code == 200, migrated.text
    code = (
        'var c=app.project.activeItem;'
        'var a=c.layers.addSolid([1,0,0],"marker",32,32,1);'
        'var p=a.property("ADBE Transform Group").property("ADBE Position");'
        'p.setValueAtTime(0,[80,100,0]);p.setValueAtTime(1,[180,100,0]);'
        'var b=c.layers.addSolid([0,1,0],"foreground",20,60,1);'
        'b.property("ADBE Transform Group").property("ADBE Position").setValue([180,100,0]);'
    )
    edited = client.post(path + '/commands', headers={**auth, "Idempotency-Key": "quality-script"},
                         json={"expectedRevision": migrated.json()["revision"], "commands": [{"id": "script.run", "params": {"code": code}}]})
    assert edited.status_code == 200, edited.text
    result = {"apiSpendUsd": 0, "fixture": "linear-red-marker-green-occluder-transparent-background",
              "dimensions": [320, 320], "fps": 30, "frames": [], "sourceScript": code,
              "sourceScriptSha256": __import__('hashlib').sha256(code.encode()).hexdigest(),
              "limitations": ["Known marker conformance, not a photographic person matte or automatic segmentation", "No aesthetic, sound, human legibility or complete-ad approval"]}
    images = []
    with SessionLocal() as db:
        from app.models import User
        user = db.query(User).filter_by(email="quality-conformance@example.com").one()
        record = owned_document(db, user.id, doc["documentId"])
        state = record_to_contract(record).native_editor_state
        result.update(engine=state.engine, buildId=state.build_id, nativeSourceSha256=state.checksum_sha256,
                      documentRevision=record.revision)
        for frame in [0, 15, 30]:
            through = craft.render_frame(db, record, frame=frame)
            with craft.workspace_files(db, record, state) as (directory, params, _):
                direct_path = directory / 'direct.png'
                call_engine('effectcraft', 'render.frame', {**params, 'frame': frame, 'format': 'png', 'outputPath': str(direct_path)})
                direct = direct_path.read_bytes()
            a, b = Image.open(BytesIO(through)).convert('RGBA'), Image.open(BytesIO(direct)).convert('RGBA')
            assert a.size == b.size == (320, 320)
            assert a.tobytes() == b.tobytes(), "Clicko integration changed direct engine pixels"
            if frame < 30:
                x = 80 + frame / 30 * 100
                observed = inspect_marker(a, (255, 0, 0), [round(x-16), 84, round(x+16), 116])
                assert observed['status'] == 'pass', observed
            else:
                observed = inspect_occlusion(a, front_point=(180, 100), front_color=(0,255,0), transparent_point=(0,0))
                assert observed['status'] == 'pass', observed
            images.append(a)
            result['frames'].append({'frame': frame, 'directAndClickoPixelsEqual': True, 'observed': observed,
                                     'pngSha256': __import__('hashlib').sha256(through).hexdigest()})

    # Same visual specification in Canvas, not a claim that all engine output should be identical.
    repo = Path(__file__).resolve().parents[2]
    node = r'''const {chromium}=require('playwright');(async()=>{const b=await chromium.launch({headless:true});
    const c=await b.newContext();await c.route(/^https?:/,r=>r.abort());const p=await c.newPage();
    await p.setContent('<canvas width="320" height="320"></canvas>');let frames=[];
    for(const t of [0,.5,1]){frames.push(await p.evaluate(t=>{let c=document.querySelector('canvas'),x=c.getContext('2d');
    x.clearRect(0,0,320,320);x.fillStyle='#ff0000';x.fillRect(80+100*t-16,84,32,32);
    x.fillStyle='#00ff00';x.fillRect(170,70,20,60);return c.toDataURL().split(',')[1]},t));}
    console.log(JSON.stringify({version:b.version(),frames}));await b.close()})().catch(e=>{console.error(e.message);process.exitCode=1});'''
    run = subprocess.run(['node','-e',node],cwd=repo,capture_output=True,text=True,timeout=60)
    assert run.returncode == 0, run.stderr
    canvas = json.loads(run.stdout)
    result['canvasBrowser'] = canvas['version']
    for index, encoded in enumerate(canvas['frames']):
        image = Image.open(BytesIO(base64.b64decode(encoded))).convert('RGBA')
        if index < 2:
            x = 80 + 50 * index
            checked = inspect_marker(image,(255,0,0),[x-16,84,x+16,116])
        else:
            checked = inspect_occlusion(image,front_point=(180,100),front_color=(0,255,0),transparent_point=(0,0))
        assert checked['status'] == 'pass', checked
        assert image.tobytes() == images[index].tobytes(), "Equivalent flat fixture differs between engines"
        result['frames'][index]['canvasPixelsEqual'] = True
    result['status'] = 'pass'
    if os.environ.get('CLICKO_QUALITY_OUTPUT'):
        out = Path(os.environ['CLICKO_QUALITY_OUTPUT'])
        out.mkdir(parents=True,exist_ok=True)
        (out/'native-conformance.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')


@pytest.mark.skipif(os.environ.get("CLICKO_TEST_REAL_CRAFT") != "1", reason="genuine built Craft runtime")
def test_motion_script_can_enable_and_animate_stroke_dashes(client):
    from conftest import register

    token, workspace = register(client, "motion-dash@example.com")
    auth = {"Authorization": "Bearer " + token}
    root = "/api/v1/studios/v1/documents"
    created = client.post(root, headers=auth, json={
        "workspaceId": workspace, "contentType": "video", "title": "Dashed stroke",
        "brief": {"objective": "Inspect motion compatibility", "audience": "QA"},
        "composition": {"pages": [{"id": "main", "width": 320, "height": 320,
                                   "durationMs": 2000, "layers": []}]},
    })
    assert created.status_code == 201, created.text
    path = root + "/" + created.json()["documentId"] + "/craft"
    migrated = client.post(path + "/migrate", headers={**auth, "Idempotency-Key": "dash-migrate"},
                           json={"engine": "effectcraft", "expectedRevision": created.json()["revision"]})
    assert migrated.status_code == 200, migrated.text
    code = """
var l = app.project.activeItem.layers.addShape();
var g = l.property("ADBE Root Vectors Group").addProperty("ADBE Vector Group");
var contents = g.property("ADBE Vectors Group");
contents.addProperty("ADBE Vector Shape - Ellipse");
var s = contents.addProperty("ADBE Vector Graphic - Stroke");
if (!contents.canAddProperty("ADBE Vector Stroke Dashes")) throw Error("Unavailable");
var d = contents.addProperty("ADBE Vector Stroke Dashes");
if (d.property("Dash").value <= 0) throw Error("Invisible dash");
d.property("Dash").setValue(28);
d.property("Gap").setValue(16);
d.property("Offset").setValueAtTime(0, 0);
d.property("Offset").setValueAtTime(1, 40);
var again = s.addProperty("ADBE Vector Stroke Dashes");
if (again.property("Dash").value !== 28 || again.property("Offset").numKeys !== 2) throw Error("Reset stroke");
contents.addProperty("ADBE Vector Graphic - Stroke");
if (contents.canAddProperty("ADBE Vector Stroke Dashes")) throw Error("Ambiguous stroke selected");
"""
    edited = client.post(path + "/commands", headers={**auth, "Idempotency-Key": "dash-script"},
                         json={"expectedRevision": migrated.json()["revision"],
                               "commands": [{"id": "script.run", "params": {"code": code}}]})
    assert edited.status_code == 200, edited.text
