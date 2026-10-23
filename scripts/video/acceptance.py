"""Run the real vertical flow ONLY against the isolated local QA service.

Start the Node preview on 3018 and Studio API on 8018 with the private QA
storage described in docs/video/VIDEO_STUDIO_DELIVERY.md. No paid AI calls.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.providers.studios import timeline_ffmpeg as ff
from app.providers.studios.ffmpeg_utility import FFmpegUtility


def main():
    origin = "http://127.0.0.1:3018"
    output_dir = ROOT / ".codex-runtime" / "video-qa"
    output_dir.mkdir(parents=True, exist_ok=True)
    source = output_dir / "fixture.mp4"
    FFmpegUtility(ff.tool("ffmpeg"), 60)._run([
        "-hide_banner", "-loglevel", "error", "-nostdin", "-y", "-f", "lavfi", "-i", "testsrc2=s=640x360:r=24:d=4",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=4", "-c:v", ff.capability()["encoder"], "-b:v", "1M", "-c:a", "aac", "-shortest", str(source)
    ], output_dir, lambda: False)
    with httpx.Client(base_url=origin, timeout=90, headers={"Origin": origin, "x-workspace-id": "ws-1", "x-clicko-studio-module": "create-video", "x-clicko-client-id": "client-clicko"}) as client:
        def request(method, path, **kwargs):
            response = client.request(method, path, **kwargs)
            response.raise_for_status()
            return response
        request("POST", "/api/governance/clients/register", json={"id": "client-clicko", "name": "QA Vídeo Clicko"})
        session = request("GET", "/api/v1/studios/v1/bridge/session").json()
        workspace = session["workspace"]["id"]
        asset = request("POST", f"/api/v1/studios/v1/craft/assets?workspace_id={workspace}&title=QA%20Video&filename=fixture.mp4&media_type=video/mp4", content=source.read_bytes(), headers={"Content-Type": "video/mp4"}).json()
        project = {"workspaceId": workspace, "title": "QA · Studio de Vídeo funcional", "contentType": "video", "brandRevision": 1,
            "brief": {"objective": "Conferir edição e exportação real", "audience": "Equipe Clicko", "angle": "Teste de aceitação audiovisual", "format": "video"},
            "composition": {"pages": [{"id": "page-1", "width": 640, "height": 360, "background": "#000000", "durationMs": 3000, "layers": []}], "tracks": [],
                "narrative": {"videoStudio": {"engine": "filmcraft", "kind": "social", "locale": "pt-BR"}},
                "mediaTimeline": {"schemaVersion": "studio.media-timeline.v1", "durationFrames": 72, "frameRate": {"numerator": 24, "denominator": 1}, "tracks": []}},
            "assets": [], "correlationId": "clicko-video-real-qa-" + str(time.time_ns())}
        document = request("POST", "/api/v1/studios/v1/documents", json=project).json()
        timeline = project["composition"]["mediaTimeline"]
        timeline["tracks"] = [
            {"id": "video-main", "kind": "video", "name": "Vídeo", "clips": [{"id": "clip-main", "assetId": asset["id"], "label": "Vídeo real · corte de 3 segundos", "timeline": {"startFrame": 0, "durationFrames": 72}, "source": {"startMicroseconds": 500_000, "durationMicroseconds": 3_000_000}, "transform": {"fadeInFrames": 6, "fadeOutFrames": 6}}]},
            {"id": "title-main", "kind": "caption", "name": "Título / CTA", "cues": [{"id": "title", "text": "Crie. Edite. Clicko.", "timeline": {"startFrame": 0, "durationFrames": 72}, "style": {"fontFamily": "system", "fontSize": 34, "outlineWidth": 2}, "motion": {"fadeInFrames": 8, "fadeOutFrames": 8, "backgroundColor": "#000000"}, "keyframes": [{"property": "y", "frame": 0, "value": 36}, {"property": "y", "frame": 12, "value": 0}]}]},
        ]
        path = "/api/v1/studios/v1/video/documents/" + document["documentId"]
        saved = request("PUT", path + "/timeline", json={"expectedRevision": 1, "timeline": timeline}, headers={"Idempotency-Key": "qa-save-" + document["documentId"]}).json()
        body = {"expectedRevision": saved["revision"]}
        identity = {"Idempotency-Key": "qa-render-" + document["documentId"]}
        job = request("POST", path + "/render-jobs", json=body, headers=identity).json()
        assert request("POST", path + "/render-jobs", json=body, headers=identity).json()["id"] == job["id"]
        deadline = time.monotonic() + 120
        while job["status"] not in {"succeeded", "failed", "cancelled"} and time.monotonic() < deadline:
            time.sleep(.5)
            job = request("GET", "/api/v1/studios/v1/jobs/" + job["id"]).json()
        assert job["status"] == "succeeded", {"status": job["status"], "error": job.get("errorMessage")}
        identifier = job["result"]["assetId"]
        library = request("GET", "/api/v1/studios/v1/video/library").json()
        assert any(item["id"] == identifier for item in library)
        delivery = f"/api/v1/studios/v1/video/library/{identifier}/content?workspaceId=ws-1&clientId=client-clicko"
        result = request("GET", delivery)
        final = output_dir / "final.mp4"
        final.write_bytes(result.content)
        assert request("GET", delivery, headers={"Range": "bytes=0-99"}).status_code == 206
        measured = ff.probe(final)
        assert abs(float(measured["format"]["duration"]) - 3) < .1
        evidence = {"documentId": document["documentId"], "jobId": job["id"], "assetId": identifier, "revision": saved["revision"], "output": str(final), "renderer": ff.capability(), "metadata": job["result"]}
        (output_dir / "evidence.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"status": "passed", "documentId": document["documentId"], "jobId": job["id"], "output": str(final)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
