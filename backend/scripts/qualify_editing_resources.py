"""Render real footage with a downloaded font and parameterized editorial compositions.

Uses an existing local source. Never calls a paid generation API or modifies application data.
"""

import argparse
import hashlib
import html
import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import httpx
from PIL import Image, ImageDraw

from app.domain.studios.contracts import CreativeDocumentV1, VideoRenderRequestV1
from app.domain.studios.editing_resources import ResourceMetadataV1
from app.providers.studios.contextual_render import ContextualFFmpegProvider
from app.providers.studios.resource_download import download_resource
from app.services.studios.editing_resources import validate_resource


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = args.source.resolve(strict=True)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    font = output / "roboto.ttf"
    with httpx.Client(timeout=30, trust_env=False) as client:
        response = client.get("https://fonts.googleapis.com/css2?family=Roboto:wght@700")
        response.raise_for_status()
    urls = re.findall(r"url\((https://fonts\.gstatic\.com/[^)]+)\)", response.text)
    if not urls:
        raise ValueError("google_font_file_not_found")
    font_url = download_resource(urls[-1], font, ["fonts.gstatic.com"])
    validate_resource(font, ResourceMetadataV1(kind="font", usage_evidence="Technical font rendering qualification"))
    support = output / "support.png"
    image = Image.new("RGBA", (320, 200), "#125c57")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((12, 12, 308, 188), radius=20, outline="#d4f38a", width=5)
    image.save(support)
    mask = output / "mask.png"
    image = Image.new("L", (320, 200), 0)
    ImageDraw.Draw(image).rounded_rectangle((0, 0, 320, 200), radius=24, fill=255)
    image.save(mask)
    assets = {"source": source, "font": font, "support": support, "mask": mask}
    refs = [
        {
            "id": key,
            "mediaType": "video/mp4" if key == "source" else "font/ttf" if key == "font" else "image/png",
            "checksum": hashlib.sha256(path.read_bytes()).hexdigest(),
            "rightsStatus": "verified",
        }
        for key, path in assets.items()
    ]
    results = []
    for name, width, height, color, start, motion in [
        ("vertical-clarity", 360, 640, "#ffffff", 0, False),
        ("square-demonstration", 480, 480, "#d4f38a", 1, True),
        ("horizontal-atmosphere", 640, 360, "#ffdda8", 2, True),
    ]:
        clips = [
            {
                "id": "source-clip",
                "assetId": "source",
                "timeline": {"startFrame": 0, "durationFrames": 100},
                "source": {"startMicroseconds": start * 1_000_000, "durationMicroseconds": 4_000_000},
            }
        ]
        tracks = [{"id": "main", "kind": "video", "clips": clips}]
        if motion:
            support_clip = {
                "id": "support-clip",
                "assetId": "support",
                "timeline": {"startFrame": 10, "durationFrames": 80},
                "transform": {
                    "width": width // 2,
                    "height": height // 3,
                    "x": width // 4,
                    "y": height // 2,
                    "originalAudioEnabled": False,
                },
                "keyframes": [
                    {
                        "trackId": prop,
                        "targetLayerId": "support-clip",
                        "property": prop,
                        "unit": "ratio",
                        "keyframes": [
                            {"frame": 0, "value": 0.2 if prop == "opacity" else 0.75, "easing": "ease_out"},
                            {"frame": 25, "value": 1},
                        ],
                    }
                    for prop in ["scale_x", "scale_y", "opacity"]
                ],
            }
            tracks += [
                {"id": "support-track", "kind": "overlay", "clips": [support_clip]},
                {"id": "mask-track", "kind": "mask", "targetTrackId": "support-track", "artifactAssetId": "mask"},
            ]
        doc = CreativeDocumentV1(
            document_id=name,
            workspace_id="qualification",
            title=name,
            content_type="video",
            correlation_id=name,
            brand_memory_ref={"id": "brand", "revision": 1},
            assets=refs,
            brief={"objective": name, "audience": "Revisão técnica"},
            composition={
                "pages": [
                    {
                        "id": "page",
                        "width": width,
                        "height": height,
                        "safeArea": 20,
                        "layers": [
                            {
                                "id": "title",
                                "kind": "text",
                                "x": 20,
                                "y": 20,
                                "width": width - 40,
                                "height": 110,
                                "properties": {
                                    "text": "Criação com intenção",
                                    "fontAssetId": "font",
                                    "fontSize": 36,
                                    "minFontSize": 24,
                                    "color": color,
                                },
                            }
                        ],
                    }
                ],
                "mediaTimeline": {
                    "frameRate": {"numerator": 25, "denominator": 1},
                    "durationFrames": 100,
                    "tracks": tracks,
                },
            },
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        request = VideoRenderRequestV1(
            workspace_id=doc.workspace_id,
            document_id=name,
            document_revision=1,
            document_version=1,
            page_ids=["page"],
            asset_ids=list(assets),
            correlation_id=name,
            output={"width": width, "height": height, "fps": 25},
        )
        video = output / f"{name}.mp4"
        receipt = ContextualFFmpegProvider("ffmpeg", 120).render(
            doc, request, assets, video, lambda _: None, lambda: False
        )
        frame = output / f"{name}.png"
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-ss", "2", "-i", str(video), "-frames:v", "1", str(frame)],
            check=True,
            timeout=30,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        results.append(
            {
                "name": name,
                "video": video.name,
                "frame": frame.name,
                "receipt": receipt.model_dump(mode="json", by_alias=True),
            }
        )
        print(f"{name}: {receipt.render_duration_ms} ms", flush=True)
    report = {
        "source": str(source),
        "fontSource": font_url,
        "createdAt": datetime.now(UTC).isoformat(),
        "realFootage": True,
        "generatedSupport": "local test graphic",
        "externalGenerativeCalls": 0,
        "geminiQualification": "pending credentials and real API evaluation",
        "results": results,
    }
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    cards = "".join(
        f'<article><h2>{html.escape(item["name"])}</h2><video controls src="{item["video"]}"></video></article>'
        for item in results
    )
    (output / "index.html").write_text(
        '<!doctype html><meta charset="utf-8"><title>Recursos de edição</title>'
        "<style>body{background:#122124;color:white;font:16px system-ui;margin:32px}"
        "main{display:flex;gap:20px;flex-wrap:wrap}"
        "article{width:360px}video{max-width:100%;max-height:600px}</style>"
        "<h1>Acervo aplicado a vídeo real</h1><p>Fonte baixada, três proporções, máscaras e motion. "
        "Esta galeria não qualifica geração ou transformação com Gemini.</p><main>" + cards + "</main>",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
