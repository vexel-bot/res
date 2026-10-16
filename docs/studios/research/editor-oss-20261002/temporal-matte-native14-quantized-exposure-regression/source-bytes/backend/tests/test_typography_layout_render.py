"""An impossible canonical word fails the actual renderer without an output."""

import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

import pytest
from test_remotion_native import native_document
from test_typography_units import typography_direction

from app.domain.studios.contextual_editing_v2 import ContextualPlanRequestV2
from app.domain.studios.contracts import AssetReferenceV1, VideoRenderRequestV1
from app.domain.studios.motion import PROPERTY_UNITS, MotionTrackV1, evaluate_motion_graph, project_motion_graph
from app.providers.studios.heavy_media_lease import _active, _read, lease_path
from app.providers.studios.remotion_render import RemotionNativeGraphicsProvider
from app.services.studios.scene_compiler import compile_scenes


@pytest.fixture(autouse=True)
def clean_database():
    yield


def test_real_final_font_overflow_publishes_no_mp4(tmp_path):
    font = Path(os.environ.get("TYPOGRAPHY_TEST_FONT", "C:/Windows/Fonts/arial.ttf"))
    if not font.is_file():
        pytest.skip("An explicitly installed local font is required")
    doc, projection = native_document(typography_direction("W" * 100, "word", duration=30, stagger=0, hold=20))
    hero = next(layer for layer in doc.composition.pages[0].layers if layer.name == "hero")
    hero.properties["fontAssetId"] = "final-font"
    doc.assets.append(
        AssetReferenceV1(
            id="final-font",
            media_type="font/ttf",
            checksum=hashlib.sha256(font.read_bytes()).hexdigest(),
        )
    )
    request = VideoRenderRequestV1(
        workspace_id=doc.workspace_id,
        document_id=doc.document_id,
        document_revision=doc.revision,
        document_version=doc.version,
        page_ids=[doc.composition.pages[0].id],
        asset_ids=["final-font"],
        correlation_id="final-font-overflow",
        output={"width": 320, "height": 320, "fps": 30, "audioCodec": "none"},
    )
    wait_until = time.monotonic() + 120
    while _active(_read(lease_path())):
        if time.monotonic() >= wait_until:
            pytest.skip("Another live local operation occupies heavy-media capacity")
        time.sleep(1)
    output = tmp_path / "must-not-publish.mp4"
    with pytest.raises(ValueError, match="does_not_fit_at_reading_floor") as caught:
        RemotionNativeGraphicsProvider("node", "ffmpeg", 180).render(
            doc,
            request,
            {"final-font": font},
            output,
            lambda _: None,
            lambda: False,
            motion_projection=projection,
            automatic_draft=True,
        )
    assert not output.exists()
    assert "target=" + hero.id in str(caught.value)
    reported_frame = re.search(r":frame=(\d+)\b", str(caught.value))
    # Two browser tabs start frames 0 and 1 concurrently; either can fail first.
    assert reported_frame and int(reported_frame[1]) in {0, 1}
    if directory := os.environ.get("TEXT_LAYOUT_EVIDENCE_DIR"):
        target = Path(directory)
        target.mkdir(parents=True, exist_ok=True)
        (target / "negative.json").write_text(
            json.dumps(
                {
                    "scope": "actual_canonical_projection_font_Remotion_failure_before_output",
                    "notApiJobProof": True,
                    "outputPublished": False,
                    "humanReview": "pending",
                    "document": doc.model_dump(mode="json", by_alias=True),
                    "request": request.model_dump(mode="json", by_alias=True),
                    "diagnostic": str(caught.value),
                    "reportedFrame": int(reported_frame[1]),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )


def test_real_animated_font_style_and_transformed_parent_share_canonical_frames(tmp_path):
    font = Path(os.environ.get("TYPOGRAPHY_TEST_FONT", "C:/Windows/Fonts/arial.ttf"))
    if not font.is_file():
        pytest.skip("An explicitly installed local font is required")
    raw = typography_direction("palavra inteira", "word", duration=30, stagger=0, hold=20).model_dump(
        mode="json",
        by_alias=True,
    )
    scene = raw["scenes"][0]
    scene["elements"][0].update(parentId="rig", x=10, y=20, width=200, height=140, lineHeight=1.2)
    scene["elements"].append(
        {
            "id": "rig",
            "kind": "group",
            "purpose": "Transform measured text once",
            "x": 40,
            "y": 30,
            "width": 240,
            "height": 240,
            "durationFrames": 30,
            "visualRole": "support",
            "originX": 0,
            "originY": 0,
        }
    )
    direction = ContextualPlanRequestV2.model_validate(raw)
    doc, _ = native_document(direction)
    doc, graph, _, _ = compile_scenes(doc, direction, "user", "style-parent-test")
    hero = next(layer for layer in doc.composition.pages[0].layers if layer.name == "hero")
    rig = next(layer for layer in doc.composition.pages[0].layers if layer.name == "rig")
    for target, prop, first, last in [
        (hero, "font_size_px", 42, 32),
        (hero, "font_weight", 400, 700),
        (hero, "letter_spacing_px", 0, 2),
        (hero, "line_height_ratio", 1.2, 1.4),
        (rig, "rotation_degrees", 0, 15),
        (rig, "scale_x", 1, 1.2),
        (rig, "scale_y", 1, 1.2),
    ]:
        graph.tracks.append(
            MotionTrackV1(
                track_id="style-" + prop,
                target_layer_id=target.id,
                property=prop,
                unit=PROPERTY_UNITS[prop],
                keyframes=[
                    {"frame": 0, "value": first, "easing": "hold"},
                    {"frame": 14, "value": last},
                    {"frame": 29, "value": last},
                ],
            )
        )
    # Revalidate canonical graph, evaluate and project using the actual pipeline.
    graph = type(graph).model_validate(graph.model_dump(mode="json", by_alias=True))
    hero.properties["fontAssetId"] = "final-font"
    doc.assets.append(
        AssetReferenceV1(
            id="final-font",
            media_type="font/ttf",
            checksum=hashlib.sha256(font.read_bytes()).hexdigest(),
        )
    )
    evaluation = evaluate_motion_graph(doc, graph)
    assert evaluation.eligible_for_reviewed_projection
    projection = project_motion_graph(graph, "remotion", evaluation)
    doc.composition.narrative["editorialV2"]["motionGraph"] = graph.model_dump(mode="json", by_alias=True)
    request = VideoRenderRequestV1(
        workspace_id=doc.workspace_id,
        document_id=doc.document_id,
        document_revision=doc.revision,
        document_version=doc.version,
        page_ids=[doc.composition.pages[0].id],
        asset_ids=["final-font"],
        correlation_id="animated-style-parent",
        output={"width": 320, "height": 320, "fps": 30, "audioCodec": "none"},
    )
    output = tmp_path / "style-parent.mp4"
    result = RemotionNativeGraphicsProvider("node", "ffmpeg", 180).render(
        doc,
        request,
        {"final-font": font},
        output,
        lambda _: None,
        lambda: False,
        motion_projection=projection,
        automatic_draft=True,
    )
    samples = result.renderer_checks["geometrySamples"]

    def observed(frame):
        return next(item for item in samples[frame]["elements"] if item["layerId"] == hero.id)

    before, after, settled = observed(13), observed(14), observed(29)
    for observed_frame, size, weight, spacing in [(before, 42, "400", 0), (after, 32, "700", 2)]:
        layout = observed_frame["typography"]["layout"]
        assert layout["requestedFontSizePx"] == size and layout["fontWeight"] == weight
        assert layout["letterSpacingPx"] == spacing and layout["fits"]
        assert layout["minimumFontSizePx"] <= layout["fontSizePx"] <= size
        assert [unit["text"] for unit in layout["units"]] == ["palavra", "inteira"]
    assert after["typography"]["layout"] == settled["typography"]["layout"]
    assert before["bounds"] != after["bounds"] and after["bounds"] == settled["bounds"]
    # With a 15-degree rotated 1.2 scale, AABB width = 1.2*(w*cos + h*sin).
    import math

    expected_width = 1.2 * (hero.width * math.cos(math.radians(15)) + hero.height * math.sin(math.radians(15)))
    assert after["bounds"]["width"] == pytest.approx(expected_width, abs=0.05)
    pixels = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(output), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        capture_output=True,
        check=True,
        timeout=30,
    ).stdout
    size = 320 * 320 * 3
    assert len(pixels) == size * 30
    difference = (
        sum(abs(a - b) for a, b in zip(pixels[14 * size : 15 * size], pixels[29 * size : 30 * size], strict=True))
        / size
    )
    assert difference < 1.5
    if directory := os.environ.get("TEXT_LAYOUT_EVIDENCE_DIR"):
        target = Path(directory)
        target.mkdir(parents=True, exist_ok=True)
        shutil.copy2(output, target / "style-parent.mp4")
        (target / "style-parent.json").write_text(
            json.dumps(
                {
                    "scope": "actual_canonical_graph_final_font_Remotion_frames",
                    "notApiJobProof": True,
                    "humanReview": "pending",
                    "document": doc.model_dump(mode="json", by_alias=True),
                    "projection": projection.model_dump(mode="json", by_alias=True),
                    "result": result.model_dump(mode="json", by_alias=True),
                    "videoSha256": hashlib.sha256(output.read_bytes()).hexdigest(),
                    "selectedGeometry": [before, after, settled],
                    "expectedParentTransformedWidth": expected_width,
                    "holdMeanAbsoluteChannelDifference": difference,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
