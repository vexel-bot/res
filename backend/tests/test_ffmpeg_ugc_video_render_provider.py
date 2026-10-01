import json
import re
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest
from PIL import Image

from app.domain.studios.contracts import (
    CreativeDocumentV1,
    VideoRenderRequestV1,
    VideoRenderSpecV1,
)
from app.providers.studios.video_render import (
    VIDEO_RENDER_PROVIDERS,
    FFmpegUgcVideoRenderProvider,
)


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


def mean_volume(path: Path) -> float:
    completed = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-nostdin",
            "-i",
            str(path),
            "-vn",
            "-af",
            "volumedetect",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    match = re.search(r"mean_volume:\s*(-?[0-9.]+) dB", completed.stderr)
    assert match, completed.stderr
    return float(match.group(1))


def counted_video_frames(path: Path) -> int:
    completed = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-count_frames",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=nb_read_frames",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return int(json.loads(completed.stdout)["streams"][0]["nb_read_frames"])


def extract_frame(path: Path, frame: int, destination: Path) -> Image.Image:
    completed = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(path),
            "-vf",
            f"select=eq(n\\,{frame})",
            "-frames:v",
            "1",
            str(destination),
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return Image.open(destination).convert("RGB")


def test_ffmpeg_ugc_provider_is_registered_as_the_bounded_builtin():
    assert isinstance(
        VIDEO_RENDER_PROVIDERS[FFmpegUgcVideoRenderProvider.name],
        FFmpegUgcVideoRenderProvider,
    )


@pytest.mark.skipif(
    not shutil.which("ffmpeg") or not shutil.which("ffprobe"),
    reason="FFmpeg binaries unavailable",
)
def test_ffmpeg_ugc_provider_renders_frame_exact_original_audio_once(tmp_path):
    source = tmp_path / "ugc-source.mp4"
    destination = tmp_path / "ugc-render.mp4"
    create_source(source)
    document, request = ugc_fixture()
    progress: list[int] = []
    provider = FFmpegUgcVideoRenderProvider("ffmpeg", 60)

    result = provider.render(
        document,
        request,
        {"asset-source": source},
        destination,
        progress.append,
        lambda: False,
    )

    assert destination.stat().st_size > 0
    assert result.provider == "builtin.ffmpeg-ugc-v1"
    assert result.provider_version.startswith("ffmpeg version")
    assert result.width == 1080 and result.height == 1920
    assert result.duration_ms == pytest.approx(1600, abs=67)
    assert result.fps == pytest.approx(30)
    assert result.video_codec == "h264" and result.audio_codec == "aac"
    assert result.frames_rendered == 48
    assert result.rendered_layer_ids == ["brand-band", "brand-cta"]
    assert result.rendered_caption_track_ids == ["captions-main"]
    assert counted_video_frames(destination) == 48
    assert progress == [8, 18, 82]
    assert "ffmpeg_ugc_shape_radius_not_rendered:brand-band" in result.warnings
    assert "ffmpeg_ugc_embedded_audio_suppressed:video-main" in result.warnings
    assert "ffmpeg_ugc_page_duration_ignored:scene-main" in result.warnings
    assert not any("page_layer_not_rendered" in warning for warning in result.warnings)
    assert not any("caption_track_not_rendered" in warning for warning in result.warnings)
    if sys.platform == "win32":
        assert "ffmpeg_ugc_font_substituted:Arial-Bold" in result.warnings
    assert abs(mean_volume(source) - mean_volume(destination)) < 2.0

    first_frame = extract_frame(destination, 10, tmp_path / "frame-10.png")
    second_frame = extract_frame(destination, 30, tmp_path / "frame-30.png")
    brand_pixels = list(first_frame.crop((80, 1645, 1000, 1785)).getdata())
    purple_pixels = sum(
        abs(red - 108) < 30 and abs(green - 92) < 30 and abs(blue - 231) < 30
        for red, green, blue in brand_pixels
    )
    assert purple_pixels > len(brand_pixels) * 0.65
    caption_crop = first_frame.crop((120, 1320, 960, 1600))
    cta_crop = first_frame.crop((120, 1660, 960, 1780))
    assert sum(min(pixel) > 205 for pixel in caption_crop.getdata()) > 300
    assert sum(min(pixel) > 205 for pixel in cta_crop.getdata()) > 300
    assert caption_crop.tobytes() != second_frame.crop((120, 1320, 960, 1600)).tobytes()


def test_ffmpeg_ugc_provider_fails_closed_before_running_binary(tmp_path):
    source = tmp_path / "not-media.bin"
    source.write_bytes(b"not media")
    destination = tmp_path / "output.mp4"
    provider = FFmpegUgcVideoRenderProvider("ffmpeg", 60)
    document, request = ugc_fixture()

    request.output.fps = 24
    with pytest.raises(ValueError, match="ffmpeg_ugc_output_fps_mismatch"):
        provider.render(
            document,
            request,
            {"asset-source": source},
            destination,
            lambda _: None,
            lambda: False,
        )
    assert not destination.exists()

    document, request = ugc_fixture()
    video_track = next(
        track for track in document.composition.media_timeline.tracks if track.kind == "video"
    )
    video_track.clips[1].timeline.start_frame = 13
    with pytest.raises(ValueError, match="ffmpeg_ugc_non_contiguous_video_timeline"):
        provider.render(
            document,
            request,
            {"asset-source": source},
            destination,
            lambda _: None,
            lambda: False,
        )

    document, request = ugc_fixture()
    video_track = next(
        track for track in document.composition.media_timeline.tracks if track.kind == "video"
    )
    video_track.clips[1].asset_id = "asset-other"
    with pytest.raises(ValueError, match="ffmpeg_ugc_source_assets_invalid"):
        provider.render(
            document,
            request,
            {"asset-source": source},
            destination,
            lambda _: None,
            lambda: False,
        )


@pytest.mark.skipif(
    not shutil.which("ffmpeg") or not shutil.which("ffprobe"),
    reason="FFmpeg binaries unavailable",
)
def test_ffmpeg_ugc_provider_renders_two_source_assets_with_per_clip_controls(tmp_path):
    first_source = tmp_path / "source-purple.mp4"
    second_source = tmp_path / "source-green.mp4"
    destination = tmp_path / "multi-source.mp4"
    create_source(first_source, color="0x201a36", frequency=440)
    create_source(second_source, color="0x167c45", frequency=660)
    document, request = ugc_fixture()
    timeline = document.composition.media_timeline
    video_track = next(track for track in timeline.tracks if track.kind == "video")
    audio_track = next(track for track in timeline.tracks if track.kind == "audio")
    video_track.clips[1].asset_id = "asset-second"
    video_track.clips[1].transform = {"fit": "contain", "anchor": "top"}
    video_track.clips[1].timeline.duration_frames = 24
    video_track.clips[1].playback_rate = 1.5
    audio_track.clips[1].asset_id = "asset-second"
    audio_track.clips[1].timeline.duration_frames = 24
    audio_track.clips[1].playback_rate = 1.5
    audio_track.clips[1].gain_db = -6
    audio_track.clips[1].pan = 0.5
    audio_track.clips[1].fade_in_frames = 3
    audio_track.clips[1].fade_out_frames = 3
    timeline.duration_frames = 36
    caption_track = next(track for track in timeline.tracks if track.kind == "caption")
    caption_track.cues[1].timeline.duration_frames = 16
    document.composition.pages[0].duration_ms = 1200
    document.composition.narrative["sourceAssetIds"] = ["asset-source", "asset-second"]
    document.assets.append(document.assets[0].model_copy(update={"id": "asset-second"}))
    request.asset_ids.append("asset-second")
    provider = FFmpegUgcVideoRenderProvider("ffmpeg", 60)

    plan = provider._plan(
        document,
        request,
        {"asset-source": first_source, "asset-second": second_source},
    )
    graph = provider._filter_graph(plan, 1080, 1920)
    assert plan.source_asset_ids == ("asset-second", "asset-source")
    assert "force_original_aspect_ratio=decrease" in graph
    assert "volume=-6.000000dB" in graph
    assert "pan=stereo" in graph
    assert "setpts=(PTS-STARTPTS)/1.50000000" in graph
    assert "atempo=1.50000000" in graph
    assert graph.count("afade=") == 2

    result = provider.render(
        document,
        request,
        {"asset-source": first_source, "asset-second": second_source},
        destination,
        lambda _: None,
        lambda: False,
    )

    assert counted_video_frames(destination) == 36
    assert result.duration_ms == pytest.approx(1200, abs=67)
    first_frame = extract_frame(destination, 5, tmp_path / "multi-first.png")
    second_frame = extract_frame(destination, 30, tmp_path / "multi-second.png")
    first_pixel = first_frame.getpixel((540, 600))
    second_pixel = second_frame.getpixel((540, 600))
    assert first_pixel[2] > first_pixel[1]
    assert second_pixel[1] > second_pixel[0] and second_pixel[1] > second_pixel[2]


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"), reason="FFmpeg unavailable")
def test_muted_original_renders_silence_without_reading_source_audio(tmp_path):
    source = tmp_path / "source-with-audio.mp4"
    destination = tmp_path / "muted-proof.mp4"
    create_source(source)
    original_bytes = source.read_bytes()
    document, request = ugc_fixture()
    audio = next(track for track in document.composition.media_timeline.tracks if track.kind == "audio")
    audio.muted = True
    provider = FFmpegUgcVideoRenderProvider("ffmpeg", 60)
    plan = provider._plan(document, request, {"asset-source": source})
    graph = provider._filter_graph(plan, 1080, 1920)
    assert "[0:a" not in graph
    assert graph.count("anullsrc=") == 2
    result = provider.render(document, request, {"asset-source": source}, destination, lambda _: None, lambda: False)
    assert "ffmpeg_ugc_original_audio_muted" in result.warnings
    assert counted_video_frames(destination) == 48
    assert result.rendered_caption_track_ids == ["captions-main"]
    decoded = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(destination), "-vn", "-f", "s16le", "pipe:1"],
        capture_output=True, check=True, timeout=30,
    ).stdout
    assert len(decoded) > 48_000
    assert not any(decoded), "Source audio must not leak into the muted proof"
    assert source.read_bytes() == original_bytes


def test_ffmpeg_ugc_provider_accepts_ripple_reorder_without_duplicating_audio(tmp_path):
    source = tmp_path / "materialized-source.mp4"
    source.write_bytes(b"materialized for structural planning")
    document, request = ugc_fixture()
    timeline = document.composition.media_timeline
    video_track = next(track for track in timeline.tracks if track.kind == "video")
    audio_track = next(track for track in timeline.tracks if track.kind == "audio")
    video_track.clips = [video_track.clips[1], video_track.clips[0]]
    audio_track.clips = [audio_track.clips[1], audio_track.clips[0]]
    video_track.clips[0].timeline.start_frame = 0
    video_track.clips[1].timeline.start_frame = 36
    audio_track.clips[0].timeline.start_frame = 0
    audio_track.clips[1].timeline.start_frame = 36

    plan = FFmpegUgcVideoRenderProvider._plan(
        document,
        request,
        {"asset-source": source},
    )
    graph = FFmpegUgcVideoRenderProvider._filter_graph(plan, 1080, 1920)

    assert [clip.source_start_frame for clip in plan.clips] == [24, 0]
    assert graph.count("[0:a:0]atrim=") == 2
    assert graph.count("[0:a:0]atrim=start=0.800000000000") == 1
    assert graph.count("[0:a:0]atrim=start=0.000000000000") == 1
    assert "[v0][a0][v1][a1]concat=n=2:v=1:a=1[vbase][aout]" in graph
    assert "drawbox=" in graph
    assert graph.count("drawtext=") == 3


def test_ffmpeg_ugc_overlay_text_never_becomes_filter_syntax(tmp_path):
    source = tmp_path / "materialized-source.mp4"
    source.write_bytes(b"materialized for structural planning")
    document, request = ugc_fixture()
    hostile = "Oferta 50%: %{eif\\:1} [vout] {\\an7} ' segura"
    caption_track = next(
        track
        for track in document.composition.media_timeline.tracks
        if track.kind == "caption"
    )
    caption_track.cues[0].text = hostile
    plan = FFmpegUgcVideoRenderProvider._plan(
        document,
        request,
        {"asset-source": source},
    )
    files = FFmpegUgcVideoRenderProvider._materialize_overlay_texts(plan, tmp_path)
    graph = FFmpegUgcVideoRenderProvider._filter_graph(plan, 1080, 1920, files)

    assert hostile not in graph
    assert "expansion=none" in graph
    materialized = (tmp_path / files[2]).read_text(encoding="utf-8")
    assert "%{eif\\:1}" in materialized
    assert "[vout]" in materialized
    assert "{\\an7}" in materialized


def test_ffmpeg_ugc_provider_cancels_before_materialization(tmp_path):
    document, request = ugc_fixture()
    destination = tmp_path / "cancelled.mp4"
    provider = FFmpegUgcVideoRenderProvider("ffmpeg", 60)
    with pytest.raises(InterruptedError, match="ffmpeg_ugc_render_cancelled"):
        provider.render(
            document,
            request,
            {"asset-source": tmp_path / "missing.mp4"},
            destination,
            lambda _: None,
            lambda: True,
        )
    assert not destination.exists()


@pytest.mark.parametrize(
    ("timeout_seconds", "cancel_after", "error_type", "message"),
    [
        (10, 0.2, InterruptedError, "ffmpeg_ugc_render_cancelled"),
        (0.2, None, TimeoutError, "ffmpeg_ugc_render_timeout"),
    ],
)
def test_ffmpeg_ugc_process_is_cancelled_or_timed_out(
    tmp_path,
    timeout_seconds,
    cancel_after,
    error_type,
    message,
):
    destination = tmp_path / "partial.mp4"
    destination.write_bytes(b"partial")
    provider = FFmpegUgcVideoRenderProvider("ffmpeg", timeout_seconds)
    started = time.monotonic()

    def is_cancelled() -> bool:
        return cancel_after is not None and time.monotonic() - started >= cancel_after

    with pytest.raises(error_type, match=message):
        provider._run(
            [sys.executable, "-c", "import time; time.sleep(10)"],
            destination,
            is_cancelled,
            started,
        )
    assert not destination.exists()
