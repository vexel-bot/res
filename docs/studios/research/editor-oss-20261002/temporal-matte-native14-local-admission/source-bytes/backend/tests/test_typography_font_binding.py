from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest
from test_remotion_native import native_document
from test_typography_units import typography_direction

from app.domain.studios.contracts import AssetReferenceV1, VideoRenderRequestV1
from app.providers.studios.remotion_render import RemotionNativeContextualRenderProvider, RemotionNativeGraphicsProvider
from app.providers.studios.video_render import VIDEO_RENDER_PROVIDERS
from app.services.studios.scene_compiler import compile_scenes


@pytest.fixture(autouse=True)
def clean_database():
    yield


@pytest.mark.parametrize("failure", ["missing", "checksum", "glyph"])
def test_final_font_failure_stops_before_render_and_publishes_nothing(tmp_path, failure):
    font = Path(os.environ.get("TYPOGRAPHY_TEST_FONT", "C:/Windows/Fonts/arial.ttf"))
    if not font.is_file():
        pytest.skip("Explicit local test font is required")
    text = "A\u0378" if failure == "glyph" else "AÇÃO"
    document, _ = native_document(typography_direction(text))
    document, graph, _, _ = compile_scenes(document, typography_direction(text), "user", "font-negative")
    document.composition.narrative["editorialV2"]["motionGraph"] = graph.model_dump(mode="json", by_alias=True)
    hero = next(layer for layer in document.composition.pages[0].layers if layer.name == "hero")
    hero.properties["fontAssetId"] = "final-font"
    checksum = hashlib.sha256(font.read_bytes()).hexdigest()
    document.assets.append(
        AssetReferenceV1(
            id="final-font", media_type="font/ttf", checksum="0" * 64 if failure == "checksum" else checksum
        )
    )
    request = VideoRenderRequestV1(
        workspace_id=document.workspace_id,
        document_id=document.document_id,
        document_revision=document.revision,
        document_version=document.version,
        page_ids=[document.composition.pages[0].id],
        asset_ids=["final-font"],
        correlation_id="font-negative",
        output={"width": 320, "height": 320, "fps": 30, "audioCodec": "none"},
    )
    provider = RemotionNativeContextualRenderProvider(
        RemotionNativeGraphicsProvider("node", "ffmpeg", 180),
        VIDEO_RENDER_PROVIDERS["builtin.ffmpeg-contextual-v1"],
    )
    output = tmp_path / "must-not-exist.mp4"
    expected = "font_glyph_missing" if failure == "glyph" else "font_binding_conflict"
    with pytest.raises(ValueError, match=expected):
        provider.render(
            document,
            request,
            {} if failure == "missing" else {"final-font": font},
            output,
            lambda _: None,
            lambda: False,
        )
    assert not output.exists()
