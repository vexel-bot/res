"""Render a reproducible technical gallery, without APIs or customer media.

Run with PYTHONPATH=backend. Synthetic images/tones validate composition only;
they do not qualify human speech, avatar quality or editorial performance.
"""

from __future__ import annotations

import argparse
import html
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from PIL import Image, ImageDraw

from app.domain.studios.contracts import CreativeDocumentV1, VideoRenderRequestV1
from app.providers.studios.contextual_render import ContextualFFmpegProvider
from app.services.studios.contextual_editing import estimate_cost


def command(*args):
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-threads",
            "2",
            "-filter_threads",
            "1",
            *map(str, args),
        ],
        check=True,
        capture_output=True,
        timeout=90,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def fixtures(directory):
    command(
        "-f",
        "lavfi",
        "-i",
        "testsrc2=size=320x320:rate=25:duration=4",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=440:duration=4:sample_rate=48000",
        "-c:v",
        "libx264",
        "-threads",
        "2",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        directory / "source.mp4",
    )
    command("-f", "lavfi", "-i", "sine=frequency=880:duration=4:sample_rate=48000", directory / "music.wav")
    for name, background, foreground in [("product", "#164b61", "#ffd38c"), ("screen", "#122938", "#55d7ba")]:
        canvas = Image.new("RGB", (320, 320), background)
        draw = ImageDraw.Draw(canvas)
        if name == "product":
            draw.rounded_rectangle((80, 45, 240, 275), radius=30, fill=foreground)
            draw.ellipse((110, 110, 210, 210), fill=background)
        else:
            for i in range(5):
                draw.rectangle((25, 30 + 50 * i, 70 + i * 40, 60 + 50 * i), fill=foreground)
        canvas.save(directory / f"{name}.png")
    mask = Image.new("L", (320, 320), 0)
    ImageDraw.Draw(mask).ellipse((10, 10, 310, 310), fill=255)
    mask.save(directory / "mask.png")
    return {
        name: directory / file
        for name, file in {
            "source": "source.mp4",
            "music": "music.wav",
            "product": "product.png",
            "screen": "screen.png",
            "mask": "mask.png",
        }.items()
    }


def clip(name, asset="source", start=0, frames=75, source_start=0, **kwargs):
    return {
        "id": name,
        "assetId": asset,
        "timeline": {"startFrame": start, "durationFrames": frames},
        "source": {"startMicroseconds": source_start, "durationMicroseconds": frames * 40_000},
        **kwargs,
    }


def scenario(name, width, height, assets):
    frames = 75
    tracks = [{"id": "main", "kind": "video", "clips": [clip("main-clip")]}]
    if name == "tutorial-tela":
        tracks[0]["clips"][0]["assetId"] = "screen"
    if name == "entrevista":
        tracks[0]["clips"][0]["transform"] = {"width": width // 2, "height": height, "x": 0}
        tracks.append(
            {
                "id": "second",
                "kind": "overlay",
                "clips": [
                    clip(
                        "second-clip",
                        source_start=500_000,
                        transform={
                            "width": width // 2,
                            "height": height,
                            "x": width // 2,
                            "originalAudioEnabled": False,
                        },
                    )
                ],
            }
        )
    if name in {"apresentacao", "demonstracao", "tutorial-tela"}:
        support = clip(
            "support",
            "product",
            frames=75,
            transform={"width": round(width * 0.6), "height": round(height * 0.4), "x": 15, "y": 25, "fit": "contain"},
            effects=[{"kind": "fade", "inFrames": 10, "outFrames": 10}],
        )
        if name == "tutorial-tela":
            support["keyframes"] = [
                {
                    "trackId": "focus",
                    "targetLayerId": "support",
                    "property": "position_x",
                    "unit": "pixels",
                    "keyframes": [{"frame": 0, "value": 0}, {"frame": 50, "value": width * 0.3}],
                }
            ]
        tracks.append({"id": "support-track", "kind": "overlay", "clips": [support]})
        if name == "demonstracao":
            tracks.append({"id": "mask", "kind": "mask", "targetTrackId": "support-track", "artifactAssetId": "mask"})
    if name == "narrativa-arquivo":
        tracks[0]["clips"] = [
            clip("later-first", frames=25, source_start=2_000_000),
            clip("earlier-second", start=25, frames=50),
        ]
    if name == "fotografias":
        frames = 100
        tracks[0]["clips"] = [clip("photo-one", "product", frames=50), clip("photo-two", "screen", start=50, frames=50)]
        tracks[0]["clips"][1]["effects"] = [{"kind": "fade", "inFrames": 10}]
    if name == "sem-fala":
        frames = 50
        tracks[0].update(
            muted=True,
            clips=[
                clip(
                    "fast",
                    frames=50,
                    playbackRate=2,
                    effects=[{"kind": "color", "exposure": 0.2, "contrast": 1.1, "saturation": 0.7}],
                )
            ],
        )
        tracks[0]["clips"][0]["source"]["durationMicroseconds"] = 4_000_000
    else:
        tracks.append(
            {
                "id": "music",
                "kind": "audio",
                "clips": [
                    clip(
                        "music-clip",
                        "music",
                        frames=frames,
                        gainDb=-15,
                        fadeInFrames=10,
                        fadeOutFrames=10,
                        effects=[{"kind": "audio_role", "role": "music"}],
                    )
                ],
            }
        )
        tracks.append(
            {
                "id": "captions",
                "kind": "caption",
                "cues": [
                    {
                        "id": "caption",
                        "text": "Exemplo técnico.\nNão é prova comercial.",
                        "timeline": {"startFrame": 10, "durationFrames": frames - 15},
                        "style": {"fontSize": 18, "outlineWidth": 1},
                    }
                ],
            }
        )
    now = datetime.now(UTC)
    return CreativeDocumentV1(
        document_id=name,
        workspace_id="qualification",
        title=name,
        content_type="video",
        correlation_id=f"qualification:{name}",
        brand_memory_ref={"id": "synthetic-brand", "revision": 1},
        brief={"objective": f"Verificar composição para {name}", "audience": "Equipe de revisão"},
        assets=[
            {"id": i, "mediaType": "video/mp4" if i == "source" else "audio/wav" if i == "music" else "image/png"}
            for i in assets
        ],
        composition={
            "pages": [{"id": "page", "width": width, "height": height, "safeArea": 16}],
            "narrative": {"syntheticTechnicalFixture": True},
            "mediaTimeline": {
                "frameRate": {"numerator": 25, "denominator": 1},
                "durationFrames": frames,
                "tracks": tracks,
            },
        },
        created_at=now,
        updated_at=now,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    options = parser.parse_args()
    output = options.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    # A new directory prevents accidentally replacing an existing qualification artifact.
    if any(output.iterdir()):
        raise SystemExit("Output directory must be empty")
    assets = fixtures(output)
    provider = ContextualFFmpegProvider("ffmpeg", 120)
    results = []
    for name, width, height in [
        ("apresentacao", 320, 568),
        ("tutorial-tela", 568, 320),
        ("entrevista", 568, 320),
        ("demonstracao", 320, 568),
        ("narrativa-arquivo", 568, 320),
        ("fotografias", 320, 320),
        ("sem-fala", 320, 568),
    ]:
        document = scenario(name, width, height, assets)
        request = VideoRenderRequestV1(
            workspace_id="qualification",
            document_id=name,
            document_revision=1,
            document_version=1,
            page_ids=["page"],
            asset_ids=list(assets),
            output={"width": width, "height": height, "fps": 25},
            correlation_id=f"qualification:{name}",
        )
        result = provider.render(document, request, assets, output / f"{name}.mp4", lambda _: None, lambda: False)
        (output / f"{name}.json").write_text(document.model_dump_json(by_alias=True, indent=2), encoding="utf-8")
        results.append(
            {
                "scenario": name,
                "file": f"{name}.mp4",
                "technicalStatus": "encoded-and-probed",
                "estimatedCostCents": estimate_cost(document),
                "bytes": (output / f"{name}.mp4").stat().st_size,
                "receipt": result.model_dump(mode="json", by_alias=True),
            }
        )
        print(f"{name}: {result.render_duration_ms} ms", flush=True)
    report = {
        "createdAt": datetime.now(UTC).isoformat(),
        "syntheticMedia": True,
        "humanEditorialReview": "pending",
        "externalApiCostCents": 0,
        "results": results,
    }
    (output / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    cards = "".join(
        f'<article><h2>{html.escape(r["scenario"])}</h2><video controls preload="metadata" src="{r["file"]}"></video>'
        f"<p>{r['receipt']['renderDurationMs']} ms · {r['bytes']} bytes</p></article>"
        for r in results
    )
    (output / "index.html").write_text(
        '<!doctype html><html lang="pt-BR"><meta charset="utf-8"><title>Qualificação da edição</title>'
        "<style>body{font:16px system-ui;background:#101c26;color:#eef6ff;margin:32px}"
        "main{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:24px}"
        "video{width:100%;max-height:480px}article{padding:20px;background:#1b2d3b;border-radius:12px}</style>"
        "<h1>Edição contextual — galeria técnica</h1><p>Sete composições com imagens sintéticas e tons de teste. "
        "Revisão editorial humana pendente; estes arquivos não medem qualidade de fala ou desempenho comercial.</p>"
        f"<main>{cards}</main></html>",
        encoding="utf-8",
    )
    print(output / "index.html")


if __name__ == "__main__":
    main()
