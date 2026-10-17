"""Controlled engineering renders; these do not measure creative autonomy."""

import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from app.domain.studios.contracts import CreativeDocumentV1
from app.domain.studios.motion import MotionGraphProjectionV1
from app.providers.studios.motion_canvas_projection import compile_motion_canvas_composition


CAPABILITIES = (
    "accented_typography", "camera_and_groups", "cutout_and_occlusion",
    "bound_paths", "product_annotation", "element_continuity", "image_fit", "single_line_fit",
)


def _asset(path, media_type):
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "mime": media_type}


def _layer(id, kind, *, x=0, y=0, width=480, height=320, z=1, props=None):
    return {"id": id, "kind": kind, "x": x, "y": y, "width": width, "height": height,
            "zIndex": z, "properties": props or {}}


def _pixels(path, predicate):
    frame = Image.open(path).convert("RGB")
    return [(x, y) for y in range(frame.height) for x in range(frame.width)
            if predicate(*frame.getpixel((x, y)))]


@pytest.mark.parametrize("capability", CAPABILITIES)
def test_motion_canvas_controlled_case_renders_real_frames(tmp_path, capability):
    worker = Path(__file__).resolve().parents[2] / "workers" / "motion-canvas-local"
    if not (worker / "node_modules" / "@motion-canvas" / "core").exists():
        pytest.skip("isolated Motion Canvas worker not installed")
    now = datetime.now(UTC)
    assets = {}
    layers = []
    nodes = []
    tracks = []
    if capability == "accented_typography":
        font = Path("C:/Windows/Fonts/arial.ttf")
        if font.is_file():
            assets["font"] = _asset(font, "font/ttf")
        layers.append(_layer("title", "text", x=30, y=110, width=420, height=100,
                             props={"text": "Distribuição é conexão", "fontSize": 40, "fontFamily": "ResFixtureFont",
                                    "fontAssetId": "font" if "font" in assets else None,
                                    "editorialTiming": {"startFrame": 0, "durationFrames": 15, "reveal": "words", "revealFrames": 9}}))
    elif capability == "camera_and_groups":
        layers.extend([_layer("camera", "group"), _layer("hero", "shape", x=170, y=90, width=140, height=140,
                                                        props={"shape": "ellipse", "fill": "#ff8844"})])
        nodes = [{"nodeId": "camera-node", "targetLayerId": "camera"},
                 {"nodeId": "hero-node", "targetLayerId": "hero", "parentNodeId": "camera-node"}]
        tracks = [{"sourceTrackId": "push", "targetLayerId": "camera", "propertyPath": "scale.x", "unit": "ratio",
                   "keyframes": [{"frame": 0, "value": 1, "easing": "ease_in_out"}, {"frame": 14, "value": 1.2, "easing": "hold"}]},
                  {"sourceTrackId": "push-y", "targetLayerId": "camera", "propertyPath": "scale.y", "unit": "ratio",
                   "keyframes": [{"frame": 0, "value": 1, "easing": "ease_in_out"}, {"frame": 14, "value": 1.2, "easing": "hold"}]}]
    elif capability in {"cutout_and_occlusion", "product_annotation"}:
        image = Image.new("RGBA", (180, 180), (0, 0, 0, 0))
        ImageDraw.Draw(image).ellipse((15, 15, 165, 165), fill=(255, 167, 56, 255))
        path = tmp_path / "isolated-object.png"
        image.save(path)
        assets["object"] = _asset(path, "image/png")
        layers.extend([_layer("backdrop", "shape", props={"fill": "#101827"}),
                       _layer("cutout", "image", x=150, y=65, width=180, height=180, z=2,
                              props={"assetId": "object"})])
        if capability == "cutout_and_occlusion":
            layers.append(_layer("foreground", "shape", x=0, y=230, height=90, z=3, props={"fill": "#276c91"}))
        else:
            layers.extend([_layer("label", "text", x=330, y=90, width=135, height=65, z=3,
                                  props={"text": "Produto", "fontSize": 29}),
                           _layer("connector", "shape", x=250, y=90, width=80, height=50, z=2,
                                  props={"color": "#ffffff", "editorialPath": {
                                      "points": [{"x": 0, "y": 50}, {"x": 80, "y": 0}], "strokeWidth": 3}})])
    elif capability == "bound_paths":
        layers.extend([_layer("origin", "shape", x=55, y=140, width=60, height=60, props={"shape": "ellipse", "fill": "#ff8844"}),
                       _layer("destination", "shape", x=370, y=140, width=60, height=60, props={"shape": "ellipse", "fill": "#ff8844"}),
                       _layer("path", "shape", x=100, y=105, width=300, height=130,
                              props={"color": "#ffffff", "editorialTiming": {"startFrame": 0, "durationFrames": 15,
                                                                                   "reveal": "path", "revealFrames": 12},
                                     "editorialPath": {"points": [{"x": 0, "y": 65}, {"x": 150, "y": 0},
                                                                 {"x": 300, "y": 65}], "strokeWidth": 5}})])
    elif capability == "element_continuity":
        layers.append(_layer("persistent", "shape", x=30, y=110, width=100, height=100,
                             props={"fill": "#ff8844"}))
        tracks.append({"sourceTrackId": "move", "targetLayerId": "persistent", "propertyPath": "position.x", "unit": "pixels",
                       "keyframes": [{"frame": 0, "value": 0, "easing": "ease_in_out"},
                                     {"frame": 14, "value": 300, "easing": "hold"}]})
    elif capability == "image_fit":
        image = Image.new("RGB", (200, 100), "#ff0000")
        ImageDraw.Draw(image).rectangle((100, 0, 199, 99), fill="#0000ff")
        path = tmp_path / "wide-image.png"
        image.save(path)
        assets["wide"] = _asset(path, "image/png")
        layers.extend([
            _layer("contain", "image", x=40, y=110, width=100, height=100,
                   props={"assetId": "wide", "objectFit": "contain"}),
            _layer("cover", "image", x=240, y=110, width=100, height=100,
                   props={"assetId": "wide", "objectFit": "cover"}),
        ])
    elif capability == "single_line_fit":
        layers.append(_layer("title", "text", x=60, y=110, width=360, height=90,
                             props={"text": "Uma ideia nasce.", "fontSize": 48,
                                    "fontWeight": 700, "lineHeight": 1.1}))
    raw_assets = [{"id": id, "mediaType": info["mime"], "checksum": info["sha256"], "rightsStatus": "verified"}
                  for id, info in assets.items()]
    document = CreativeDocumentV1.model_validate({
        "documentId": "controlled-" + capability, "workspaceId": "test", "title": capability,
        "contentType": "video", "correlationId": "controlled", "brandMemoryRef": {"id": "brand", "revision": 1},
        "brief": {"objective": capability, "audience": "engineering"},
        "composition": {"pages": [{"id": "page", "width": 480, "height": 320, "layers": layers}],
                        "mediaTimeline": {"frameRate": {"numerator": 15, "denominator": 1},
                                          "durationFrames": 15, "tracks": []}},
        "assets": raw_assets, "createdAt": now.isoformat(), "updatedAt": now.isoformat(),
    })
    if not tracks:
        tracks = [{"sourceTrackId": "hold", "targetLayerId": layers[0]["id"], "propertyPath": "opacity", "unit": "ratio",
                   "keyframes": [{"frame": 0, "value": 1, "easing": "hold"}]}]
    projection = MotionGraphProjectionV1.model_validate({
        "target": "motion_canvas", "sourceGraphId": "controlled", "sourceGraphDigestSha256": "a" * 64,
        "frameRate": {"numerator": 15, "denominator": 1}, "durationFrames": 15,
        "nodes": nodes, "tracks": tracks, "previewOnly": True,
    })
    manifest = compile_motion_canvas_composition(document, projection, assets)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    output = tmp_path / "render"
    subprocess.run(["node", str(worker / "render.mjs"), str(manifest_path), str(output)],
                   cwd=worker, check=True, timeout=120, stdout=subprocess.DEVNULL)
    receipt = json.loads((output / "receipt.json").read_text(encoding="utf-8"))
    assert receipt["result"] == 0 and len(receipt["frames"]) == 15
    assert receipt["videoSha256"] and (output / "visual.mp4").is_file()
    if capability == "image_fit":
        frame = Image.open(output / "000008.png").convert("RGB")
        background = frame.getpixel((60, 115))
        assert background == frame.getpixel((150, 115))
        assert frame.getpixel((60, 160))[0] > 240  # contained red half
        assert frame.getpixel((120, 160))[2] > 240  # contained blue half
        assert frame.getpixel((260, 115))[0] > 240  # covered frame has no letterbox
        assert frame.getpixel((320, 115))[2] > 240
    if capability == "accented_typography":
        white = lambda r, g, b: min(r, g, b) > 220
        assert len(_pixels(output / "000014.png", white)) > 1.5 * len(_pixels(output / "000000.png", white))
    if capability == "single_line_fit":
        diagnostic = receipt["layoutDiagnostics"][0]
        assert diagnostic["oneLineBox"] is True
        assert diagnostic["effectiveFontSize"] < diagnostic["authoredFontSize"]
        white = _pixels(output / "000008.png", lambda r, g, b: min(r, g, b) > 220)
        assert max(y for _, y in white) - min(y for _, y in white) < 60
        assert max(x for x, _ in white) - min(x for x, _ in white) > 250
    if capability == "camera_and_groups":
        orange = lambda r, g, b: r > 220 and 90 < g < 180 and b < 120
        assert len(_pixels(output / "000014.png", orange)) > len(_pixels(output / "000000.png", orange)) * 1.3
    if capability == "cutout_and_occlusion":
        frame = Image.open(output / "000008.png").convert("RGB")
        assert frame.getpixel((240, 120))[0] > 220  # isolated subject
        assert frame.getpixel((240, 250))[2] > frame.getpixel((240, 250))[0]  # foreground occludes
    if capability == "bound_paths":
        white = lambda r, g, b: min(r, g, b) > 220
        assert len(_pixels(output / "000014.png", white)) > len(_pixels(output / "000003.png", white)) * 2
    if capability == "product_annotation":
        frame = Image.open(output / "000008.png").convert("RGB")
        assert min(frame.getpixel((285, 118))) > 220  # line visibly leaves the object
        assert min(frame.getpixel((320, 95))) > 220  # and approaches the label
    if capability == "element_continuity":
        orange = lambda r, g, b: r > 220 and 90 < g < 180 and b < 120
        first = _pixels(output / "000000.png", orange)
        last = _pixels(output / "000014.png", orange)
        assert first and last
        assert sum(x for x, _ in last) / len(last) - sum(x for x, _ in first) / len(first) > 250
        geometry = receipt["geometrySamples"]
        assert geometry[0]["elements"][0]["bounds"]["x"] == pytest.approx(30, abs=1)
        assert geometry[14]["elements"][0]["bounds"]["x"] == pytest.approx(330, abs=1)
    if capability != "cutout_and_occlusion":
        assert len({frame["sha256"] for frame in receipt["frames"]}) > 1 or capability in {"product_annotation", "image_fit", "single_line_fit"}
