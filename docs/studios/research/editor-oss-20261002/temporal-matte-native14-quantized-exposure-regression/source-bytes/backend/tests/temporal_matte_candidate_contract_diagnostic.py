"""Explicit proposed native.14 contracts; historical assertions stay intact."""
# ruff: noqa: F811
import copy

import pytest
from test_asset_matte import matte_direction
from test_contextual_editing import document, request
from test_contextual_editing import media as media
from test_native_motion_recipes import recipe
from test_remotion_native import native_document
from test_temporal_exposure import POLICY

from app.domain.studios.contextual_editing_v2 import ContextualPlanRequestV2
from app.providers.studios.contextual_render import ContextualFFmpegProvider


@pytest.mark.parametrize("quality,crf", [("draft", "28"), ("standard", "23"), ("high", "10")])
def test_candidate_quality_controls_real_contextual_encode(media, tmp_path, monkeypatch, quality, crf):
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
    assert result.frames_rendered == 50 and result.provider_version == "1.4.1"
    assert result.renderer_checks == {"encodeQuality": quality, "videoCrf": int(crf)}


def test_candidate_matte_under_moving_external_parent_compiles_at_both_scopes():
    direction = matte_direction()
    blur = recipe("velocity_blur", temporalExposure=POLICY, temporalSamples=8)
    blur.update(id="matte-exposure", targetIds=["hero"])
    raw = direction.model_dump(mode="json", by_alias=True)
    raw["scenes"][0]["motionRecipes"].append(blur)
    assets = [{"id": "mask", "mediaType": "image/png", "checksum": "a" * 64, "rightsStatus": "verified"}]
    for target in ["hero", "target-rig"]:
        scoped = copy.deepcopy(raw)
        scoped["scenes"][0]["motionRecipes"][-1]["targetIds"] = [target]
        document, projection = native_document(ContextualPlanRequestV2.model_validate(scoped), assets)
        exposed = [layer for layer in document.composition.pages[0].layers
                   if layer.properties.get("recipeTemporalBlur")]
        assert len(exposed) == 1
        assert exposed[0].properties["recipeTemporalBlur"]["exposurePolicy"] == POLICY
        assert projection is not None
