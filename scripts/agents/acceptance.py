"""Live QA bridge acceptance; own content only, no browser login or paid provider.

Run create, restart dev:local, then verify. It proves the real local backend,
not LLM autonomy, paid generation, commercial license or a browser session.
"""

import hashlib
import io
import json
import math
import struct
import subprocess
import sys
import time
import wave
from pathlib import Path
from uuid import uuid4

import httpx
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))
from scripts.video.stage1_acceptance import headers  # noqa: E402
from app.providers.studios.timeline_ffmpeg import probe, tool  # noqa: E402

OUTPUT = ROOT / ".codex-runtime/stage2-validation"
BASE = "/api/v1/studios/v1"


def digest(content):
    return hashlib.sha256(content).hexdigest()


def main():
    OUTPUT.mkdir(exist_ok=True)
    with httpx.Client(base_url="http://127.0.0.1:8018", timeout=180) as client:
        def request(method, path, *, visual=False, key=None, **kwargs):
            custom = kwargs.pop("headers", {})
            response = client.request(method, path, headers={**headers(
                "create-image" if visual else "create-video", "stage2-own-qa"),
                **custom, **({"Idempotency-Key": key} if key else {})}, **kwargs)
            assert response.is_success, (response.status_code, response.text[:400])
            return response

        evidence_path = OUTPUT / "evidence.json"
        if sys.argv[1:] == ["verify"]:
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            for name, item in evidence["deliveries"].items():
                content = request("GET", item["path"], visual=item.get("visual", False)).content
                assert digest(content) == item["checksumSha256"], name
            doc = request("GET", BASE+"/documents/"+evidence["documentId"]).json()
            assert doc["revision"] == evidence["revision"]
            assert len(doc["composition"]["pages"][0]["layers"]) == 9
            evidence["persistenceAfterRestart"] = True
            evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps({"persisted": True, "deliveries": len(evidence["deliveries"])}))
            return

        run = uuid4().hex[:12]
        session = request("GET", BASE+"/bridge/session").json()
        workspace = session["workspace"]["id"]

        def create(visual=False):
            return request("POST", BASE+"/agents/projects", visual=visual, key=f"stage2-create-{visual}-{run}",
                json={"workspaceId": workspace, "title": "Clicko · produção local editável",
                      "contentType": "visual" if visual else "video", "width": 640, "height": 640 if visual else 360}).json()

        def plan_apply(doc, instruction, suffix):
            path = BASE+f"/documents/{doc['documentId']}/agent-tasks"
            task = request("POST", path, key=f"stage2-plan-{suffix}-{run}",
                           json={"expectedRevision": doc["revision"], "instruction": instruction}).json()
            assert task["status"] == "succeeded", task
            assert task["result"]["inference"] == "none"
            (OUTPUT/f"plan-{suffix}.json").write_text(json.dumps(task, ensure_ascii=False, indent=2), encoding="utf-8")
            result = request("POST", path+f"/{task['id']}/apply",
                             json={"expectedRevision": doc["revision"]}).json()
            assert request("POST", path+f"/{task['id']}/apply", json={"expectedRevision": doc["revision"]}).json() == result
            return result

        def upload(content, name, media_type, visual=False):
            return request("POST", BASE+"/craft/assets", visual=visual,
                params={"workspace_id": workspace, "title": "QA · "+name, "filename": name, "media_type": media_type},
                headers={"Content-Type": media_type}, content=content).json()

        def render(doc, suffix):
            path = BASE+f"/video/documents/{doc['documentId']}/render-jobs"
            key = f"stage2-render-{suffix}-{run}"
            job = request("POST", path, key=key, json={"expectedRevision": doc["revision"]}).json()
            assert request("POST", path, key=key, json={"expectedRevision": doc["revision"]}).json()["id"] == job["id"]
            deadline = time.monotonic()+180
            while job["status"] not in {"succeeded", "failed", "cancelled"} and time.monotonic() < deadline:
                time.sleep(.5)
                job = request("GET", BASE+"/jobs/"+job["id"]).json()
            assert job["status"] == "succeeded", job
            delivery = job["result"]["downloadUrl"]
            content = request("GET", delivery).content
            output = OUTPUT/f"motion-{suffix}.mp4"
            output.write_bytes(content)
            metadata = probe(output)
            decoded = subprocess.run([tool("ffmpeg"), "-v", "error", "-i", str(output), "-f", "null", "-"],
                                     capture_output=True, timeout=90)
            assert decoded.returncode == 0, decoded.stderr[:400]
            assert abs(float(metadata["format"]["duration"])-12) < .1
            assert any(stream.get("codec_name") == "h264" and stream.get("width") == 640
                       for stream in metadata["streams"])
            (OUTPUT/f"document-{suffix}.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
            return {"path": delivery, "checksumSha256": digest(content), "bytes": len(content),
                    "jobId": job["id"], "durationSeconds": float(metadata["format"]["duration"])}

        doc = plan_apply(create(), 'Crie um motion design de 12 segundos sobre inteligência artificial, '
                         'com cartões e tipografia animada.', "v1")
        wave_bytes = io.BytesIO()
        with wave.open(wave_bytes, "wb") as audio:
            audio.setparams((1, 2, 24000, 0, "NONE", "not compressed"))
            audio.writeframes(b"".join(struct.pack("<h", round(1800*math.sin(2*math.pi*220*index/24000)))
                                       for index in range(12*24000)))
        soundtrack = upload(wave_bytes.getvalue(), "own-test-tone.wav", "audio/wav")
        timeline = doc["composition"]["mediaTimeline"]
        timeline["tracks"] = [{"id": "own-audio", "kind": "audio", "name": "Tom de teste próprio",
            "clips": [{"id": "audio-clip", "assetId": soundtrack["id"], "gainDb": -12,
                       "fadeInFrames": 12, "fadeOutFrames": 12,
                       "timeline": {"startFrame": 0, "durationFrames": 288}}]}]
        first_card = doc["composition"]["pages"][0]["layers"][0]
        first_card["properties"]["gradientEnd"] = "#242424"
        first_card["properties"]["keyframes"] += [
            {"property": "rotation", "frame": 0, "value": -1},
            {"property": "rotation", "frame": 96, "value": 1, "easing": "ease-in-out"}]
        doc = request("POST", BASE+f"/documents/{doc['documentId']}/local-commands", key="stage2-media-"+run,
                      json={"expectedRevision": doc["revision"], "commands": [
                          {"id": "asset.attach", "params": {"assetId": soundtrack["id"]}},
                          {"id": "timeline.replace", "params": {"timeline": timeline}},
                          {"id": "layer.upsert", "params": {"layer": first_card}}]}).json()
        first = render(doc, "v1")
        doc = plan_apply(doc, 'Mude o primeiro título para "Ideias que ganham movimento"', "v2")
        second = render(doc, "v2")
        assert first["checksumSha256"] != second["checksumSha256"]
        history = request("GET", BASE+f"/documents/{doc['documentId']}/versions").json()
        assert len(history) >= 3
        (OUTPUT/"versions.json").write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
        preview = request("GET", BASE+f"/documents/{doc['documentId']}/local-preview", params={"frame": 36})
        # Audio-only tracks do not alter visual composition; the exact still remains available.
        (OUTPUT/"motion-frame.png").write_bytes(preview.content)

        picture = Image.new("RGB", (480, 640), "#6EB8F5")
        ImageDraw.Draw(picture).rounded_rectangle((60, 180, 420, 460), radius=25, fill="#FF7F50")
        buffer = io.BytesIO(); picture.save(buffer, format="PNG"); original = buffer.getvalue()
        (OUTPUT/"own-source.png").write_bytes(original)
        visual = create(True)
        image = upload(original, "own-source.png", "image/png", True)
        layers = [{"id": "source", "kind": "image", "name": "Original preservado", "x": 0, "y": 0,
                   "width": 640, "height": 640, "properties": {"schemaVersion": "studio.local-layer.v1",
                       "assetId": image["id"], "brightness": .9, "contrast": 1.05,
                       "crop": {"x": .1, "y": .1, "width": .8, "height": .8}}},
                  {"id": "title", "kind": "text", "name": "Título", "x": 50, "y": 55,
                   "width": 540, "height": 200, "zIndex": 2, "properties": {
                       "schemaVersion": "studio.local-layer.v1", "text": "Produção local\nClicko Studios",
                       "fontFamily": "system", "fontSize": 42, "color": "#000000"}}]
        visual = request("POST", BASE+f"/documents/{visual['documentId']}/local-commands", visual=True,
                         key="stage2-image-"+run, json={"expectedRevision": 1, "commands": [
                            {"id": "asset.attach", "params": {"assetId": image["id"]}},
                            *[{"id": "layer.upsert", "params": {"layer": layer}} for layer in layers]]}).json()
        exported = request("POST", BASE+f"/documents/{visual['documentId']}/local-image-export", visual=True,
                           key="stage2-image-export-"+run, json={"expectedRevision": visual["revision"]}).json()
        content = request("GET", exported["downloadUrl"], visual=True).content
        assert request("GET", f"/api/v1/assets/{image['id']}/content", visual=True).content == original
        (OUTPUT/"composition.png").write_bytes(content)
        (OUTPUT/"image-document.json").write_text(json.dumps(visual, ensure_ascii=False, indent=2), encoding="utf-8")
        evidence = {"schemaVersion": "clicko.local-agents-acceptance.v1", "documentId": doc["documentId"],
                    "revision": doc["revision"], "mode": "deterministic_local_tools_not_ai_inference",
                    "paidCalls": 0, "persistenceAfterRestart": False, "versions": len(history),
                    "deliveries": {"videoV1": first, "videoV2": second, "image": {
                        "path": exported["downloadUrl"], "checksumSha256": digest(content), "visual": True}}}
        evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"realLocalMotion": True, "changedTitle": True, "originalPreserved": True, "paidCalls": 0}))


if __name__ == "__main__":
    main()
