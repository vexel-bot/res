"""Requested quality reaches the actual final FFmpeg command and receipt."""
# ruff: noqa: F811
import pytest
from test_contextual_editing import document, request
from test_contextual_editing import media as media

from app.providers.studios.contextual_render import ContextualFFmpegProvider


@pytest.mark.parametrize("quality,crf", [("draft", "28"), ("standard", "23"), ("high", "14")])
def test_requested_quality_controls_real_contextual_encode(media, tmp_path, monkeypatch, quality, crf):
    provider = ContextualFFmpegProvider("ffmpeg", 60)
    original = provider._run
    commands = []

    def observed_run(args, cwd, cancelled):
        commands.append(args)
        return original(args, cwd, cancelled)

    monkeypatch.setattr(provider, "_run", observed_run)
    doc = document()
    spec = request(doc)
    spec.output.quality = quality
    output = tmp_path / "quality.mp4"
    result = provider.render(doc, spec, media, output, lambda _: None, lambda: False)
    assert len(commands) == 1 and commands[0][commands[0].index("-crf") + 1] == crf
    assert output.stat().st_size > 1000 and result.video_codec == "h264" and result.audio_codec == "aac"
    assert result.frames_rendered == 50 and result.provider_version == "1.4.0"
    assert result.renderer_checks == {"encodeQuality": quality, "videoCrf": int(crf)}
