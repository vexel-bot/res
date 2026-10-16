"""Legacy document and media fixtures; no retired renderer is imported."""
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from app.domain.studios.contracts import CreativeDocumentV1, VideoRenderRequestV1, VideoRenderSpecV1

def ugc_fixture() -> tuple[CreativeDocumentV1, VideoRenderRequestV1]:
    now = datetime.now(UTC)
    document = CreativeDocumentV1.model_validate(
        {
            "documentId": "ffmpeg-ugc-smoke",
            "workspaceId": "workspace-ugc",
            "title": "UGC frame exact",
            "contentType": "video",
            "revision": 4,
            "version": 2,
            "correlationId": "ffmpeg-ugc-smoke-001",
            "brandMemoryRef": {"id": "brand-ugc", "revision": 3},
            "brief": {
                "objective": "Validar o renderer UGC local",
                "audience": "Equipe Clicko",
                "hook": "Take real, corte real.",
            },
            "composition": {
                "pages": [
                    {
                        "id": "scene-main",
                        "role": "ugc-main",
                        "width": 1080,
                        "height": 1920,
                        "durationMs": 2000,
                        "background": "#090b0d",
                        "layers": [
                            {
                                "id": "brand-band",
                                "kind": "shape",
                                "name": "Faixa da marca",
                                "x": 72,
                                "y": 1640,
                                "width": 936,
                                "height": 150,
                                "zIndex": 10,
                                "properties": {"fill": "#6c5ce7", "radius": 32},
                            },
                            {
                                "id": "brand-cta",
                                "kind": "text",
                                "name": "CTA da marca",
                                "x": 120,
                                "y": 1674,
                                "width": 840,
                                "height": 86,
                                "zIndex": 11,
                                "properties": {
                                    "text": "Conheça a marca",
                                    "fontSize": 48,
                                    "color": "#ffffff",
                                },
                            },
                        ],
                    }
                ],
                "narrative": {
                    "mode": "ugc-assisted",
                    "sourceAssetId": "asset-source",
                    "originalPreserved": True,
                },
                "mediaTimeline": {
                    "durationFrames": 48,
                    "frameRate": {"numerator": 30, "denominator": 1},
                    "tracks": [
                        {
                            "id": "video-main",
                            "kind": "video",
                            "name": "Vídeo principal",
                            "muted": False,
                            "clips": [
                                {
                                    "id": "source-select-1",
                                    "assetId": "asset-source",
                                    "timeline": {"startFrame": 0, "durationFrames": 12},
                                    "source": {
                                        "startMicroseconds": 0,
                                        "durationMicroseconds": 400000,
                                    },
                                    "transform": {"fit": "cover", "anchor": "center"},
                                },
                                {
                                    "id": "source-select-2",
                                    "assetId": "asset-source",
                                    "timeline": {"startFrame": 12, "durationFrames": 36},
                                    "source": {
                                        "startMicroseconds": 800000,
                                        "durationMicroseconds": 1200000,
                                    },
                                    "transform": {"fit": "cover", "anchor": "center"},
                                },
                            ],
                        },
                        {
                            "id": "audio-main",
                            "kind": "audio",
                            "name": "Áudio original",
                            "clips": [
                                {
                                    "id": "audio-select-1",
                                    "assetId": "asset-source",
                                    "timeline": {"startFrame": 0, "durationFrames": 12},
                                    "source": {
                                        "startMicroseconds": 0,
                                        "durationMicroseconds": 400000,
                                    },
                                },
                                {
                                    "id": "audio-select-2",
                                    "assetId": "asset-source",
                                    "timeline": {"startFrame": 12, "durationFrames": 36},
                                    "source": {
                                        "startMicroseconds": 800000,
                                        "durationMicroseconds": 1200000,
                                    },
                                },
                            ],
                        },
                        {
                            "id": "captions-main",
                            "kind": "caption",
                            "name": "Legendas PT-BR",
                            "locale": "pt-BR",
                            "cues": [
                                {
                                    "id": "caption-1",
                                    "timeline": {"startFrame": 0, "durationFrames": 20},
                                    "text": "Primeiro trecho",
                                },
                                {
                                    "id": "caption-2",
                                    "timeline": {"startFrame": 20, "durationFrames": 28},
                                    "text": "Segundo trecho",
                                },
                            ],
                        },
                    ],
                },
            },
            "assets": [
                {
                    "id": "asset-source",
                    "mediaType": "video/mp4",
                    "rightsStatus": "verified",
                    "provenance": {"source": "user-upload"},
                }
            ],
            "createdAt": now,
            "updatedAt": now,
        }
    )
    request = VideoRenderRequestV1(
        workspace_id=document.workspace_id,
        document_id=document.document_id,
        document_revision=document.revision,
        document_version=document.version,
        page_ids=["scene-main"],
        asset_ids=["asset-source"],
        output=VideoRenderSpecV1(
            format="mp4",
            width=1080,
            height=1920,
            fps=30,
            video_codec="h264",
            audio_codec="aac",
            quality="draft",
        ),
        correlation_id="ffmpeg-ugc-smoke-001",
    )
    return document, request


def create_source(
    path: Path,
    *,
    color: str = "0x201a36",
    frequency: int = 440,
) -> None:
    completed = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c={color}:size=360x640:rate=30:duration=2",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency={frequency}:sample_rate=48000:duration=2",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            str(path),
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
