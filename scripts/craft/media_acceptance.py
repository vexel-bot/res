"""Real audio mixing, transparent composition linking and native bundle acceptance.

Run after acceptance.py against the isolated QA API. Uses FFmpeg only to inspect
the Craft exports; all authoring, compositing and encoding use the Rust engines.
"""

from __future__ import annotations

import hashlib
import io
import json
import math
from pathlib import Path
import struct
import subprocess
import time
from uuid import uuid4
import wave
import zipfile

from PIL import Image
import requests

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / ".codex-runtime/craft"
ORIGIN = "http://127.0.0.1:8018"


def main():
    session = requests.Session()
    session.headers["Authorization"] = (
        "Bearer " + json.loads((OUTPUT / "frontend-qa-auth.json").read_text())["token"]
    )

    def call(method, path, body=None, expected=200, binary=False):
        response = session.request(
            method,
            ORIGIN + path,
            json=body,
            headers={"Idempotency-Key": str(uuid4())},
            timeout=600,
        )
        assert response.status_code == expected, (
            f"{path}: {response.status_code} {response.text[:1600]}"
        )
        return response.content if binary else response.json()

    workspace = call("GET", "/api/v1/bootstrap")["workspaces"][0]["id"]

    def create(engine):
        document = call(
            "POST",
            "/api/v1/studios/v1/documents",
            {
                "workspaceId": workspace,
                "title": "Craft audio and composition QA " + engine,
                "contentType": "video",
                "brandRevision": 1,
                "brief": {"objective": "Real media integration", "audience": "QA"},
                "composition": {
                    "pages": [
                        {
                            "id": "page-0",
                            "width": 320,
                            "height": 320,
                            "background": "#ffffff",
                            "durationMs": 500,
                            "layers": [],
                        }
                    ]
                },
            },
            expected=201,
        )
        base = "/api/v1/studios/v1/documents/" + document["documentId"]
        state = call(
            "POST",
            base + "/craft/migrate",
            {"engine": engine, "expectedRevision": document["revision"]},
        )
        return base, state

    def commands(base, state, operations):
        return call(
            "POST",
            base + "/craft/commands",
            {
                "expectedRevision": state["revision"],
                "commands": operations,
            },
        )["inspection"]

    def preview(base):
        return Image.open(
            io.BytesIO(call("POST", base + "/craft/preview", {"frame": 0}, binary=True))
        ).convert("RGBA")

    def export(base, state, fmt, name):
        job = call(
            "POST",
            base + "/craft/render-jobs",
            {
                "expectedRevision": state["revision"],
                "format": fmt,
            },
            expected=201,
        )
        for _ in range(120):
            job = call("GET", "/api/v1/studios/v1/jobs/" + job["id"])
            if job["status"] in ("succeeded", "failed", "cancelled"):
                break
            time.sleep(0.5)
        assert job["status"] == "succeeded", {
            k: job.get(k) for k in ("status", "errorCode", "errorMessage")
        }
        artifact = job["result"]["artifact"]
        payload = call("GET", artifact["downloadUrl"], binary=True)
        assert hashlib.sha256(payload).hexdigest() == artifact["checksumSha256"]
        path = OUTPUT / name
        path.write_bytes(payload)
        return path

    film, film_state = create("filmcraft")
    film_state = commands(
        film,
        film_state,
        [
            {
                "id": "file.newColorMatte",
                "params": {
                    "color": "#0000ff",
                    "seconds": 0.5,
                },
            }
        ],
    )
    raw = film_state["project"]["raw"]["project"]
    item = next(
        entry["item"]
        for entry in raw["root"]["children"]
        if entry.get("item") != raw["activeSequence"]
    )
    film_state = commands(
        film,
        film_state,
        [
            {
                "id": "timeline.place",
                "params": {
                    "item": item,
                    "seconds": 0,
                    "video": True,
                    "audio": False,
                    "insert": False,
                },
            }
        ],
    )

    # Stream a deterministic tone through the actual authenticated media endpoint.
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as audio:
        audio.setparams((1, 2, 48000, 0, "NONE", "not compressed"))
        audio.writeframes(
            b"".join(
                struct.pack(
                    "<h", round(12000 * math.sin(2 * math.pi * 440 * i / 48000))
                )
                for i in range(24000)
            )
        )
    response = session.post(
        ORIGIN + "/api/v1/studios/v1/craft/assets",
        params={
            "workspace_id": workspace,
            "title": "Deterministic 440Hz tone",
            "filename": "tone.wav",
            "media_type": "audio/wav",
        },
        data=buffer.getvalue(),
        timeout=60,
    )
    assert response.status_code == 201, response.text[:1000]
    audio_id = response.json()["id"]
    film_state = commands(
        film,
        film_state,
        [
            {
                "id": "asset.import",
                "params": {
                    "assetId": audio_id,
                    "addToTimeline": True,
                    "seconds": 0,
                },
            }
        ],
    )
    path = export(film, film_state, "mp4", "acceptance-audio.mp4")
    probe = json.loads(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_streams",
                "-of",
                "json",
                str(path),
            ]
        )
    )
    assert any(stream["codec_type"] == "audio" for stream in probe["streams"]), (
        "Craft export lost the audio stream"
    )
    pcm = subprocess.check_output(
        ["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:a:0", "-f", "s16le", "-"]
    )
    assert max(abs(value[0]) for value in struct.iter_unpack("<h", pcm)) > 1000, (
        "Exported audio was silent"
    )
    print("Passed native audio import, mix and MP4 encoding", flush=True)

    effect, effect_state = create("effectcraft")
    effect_state = commands(
        effect,
        effect_state,
        [
            {
                "id": "edit.clear",
                "params": {
                    "layers": [
                        int(layer["id"]) for layer in effect_state["project"]["layers"]
                    ],
                },
            },
            {
                "id": "layer.newSolid",
                "params": {"color": "#ff0000", "width": 100, "height": 100},
            },
        ],
    )
    image = preview(effect)
    assert image.getpixel((0, 0))[3] == 0 and image.getpixel((160, 160)) == (
        255,
        0,
        0,
        255,
    ), "Effect preview lost alpha"
    linked = call(
        "POST",
        film + "/craft/link-composition",
        {
            "expectedRevision": film_state["revision"],
            "compositionDocumentId": effect.rsplit("/", 1)[1],
        },
    )
    film_state = linked["inspection"]
    image = preview(film)
    assert image.getpixel((0, 0))[:3] == (0, 0, 255), (
        "Linked composition flattened the background"
    )
    assert image.getpixel((160, 160))[0] > 240, (
        "FilmCraft did not place the EffectCraft composition above the base"
    )
    print("Passed transparent EffectCraft to FilmCraft link", flush=True)

    # Refresh must relink the same native media without losing the timeline or audio.
    solid = next(
        layer for layer in effect_state["project"]["layers"] if layer["name"] != "Fundo"
    )
    effect_state = commands(
        effect,
        effect_state,
        [
            {
                "id": "prop.set",
                "params": {
                    "layer": int(solid["id"]),
                    "path": "transform/opacity",
                    "value": 50,
                },
            }
        ],
    )
    film_state = call("GET", film + "/craft/inspection")
    pixel = preview(film).getpixel((160, 160))
    assert pixel[0] > 80 and pixel[2] > 80, (
        f"Composition refresh did not preserve transparency: {pixel}"
    )
    path = export(film, film_state, "mp4", "acceptance-linked-audio.mp4")
    pcm = subprocess.check_output(
        ["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:a:0", "-f", "s16le", "-"]
    )
    assert max(abs(value[0]) for value in struct.iter_unpack("<h", pcm)) > 1000, (
        "Relinking lost audio"
    )

    payload = call("GET", film + "/native-project?allPages=true", binary=True)
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        assert any(name.endswith(".ecproj") for name in archive.namelist()), (
            "Bundle lost linked editable composition"
        )
        assert any(name.endswith(".wav") for name in archive.namelist()), (
            "Bundle lost original audio"
        )
    result = {
        "audio": True,
        "alpha": True,
        "linkedRefresh": True,
        "bundle": True,
        "filmDocumentId": film.rsplit("/", 1)[1],
        "effectDocumentId": effect.rsplit("/", 1)[1],
    }
    (OUTPUT / "media-acceptance-results.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    print(
        "Passed linked refresh, audio preservation and complete native bundle",
        flush=True,
    )


if __name__ == "__main__":
    main()
