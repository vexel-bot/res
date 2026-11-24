"""Reference-derived direction is exercised separately from production media."""

import base64
from io import BytesIO
import json
import time
from types import SimpleNamespace

import pytest
from PIL import Image

from app.services.studios import craft_direction, craft_motion_reference as motion, editing_repertoire


def test_openmotion_recipes_expose_sources_and_native_review_steps(monkeypatch):
    recipes = {key: card for key, card in craft_direction.repertoire().items() if key.startswith("openmotion-")}
    assert len(recipes) == 3
    for card in recipes.values():
        assert card["operationBinding"]["requiresCapabilityCheck"]
        assert card["operationRecipe"] and card["test"]
        assert card["upstream"]["revision"] in card["sources"][0]
        assert "pending transfer validation" in card["state"]

    monkeypatch.setattr(editing_repertoire, "search_repertoire", lambda *_: [])
    monkeypatch.setattr(editing_repertoire, "available_repertoire", lambda *_: [])
    result = craft_direction.search_repertoire(None, "workspace", "ring mask reveal", limit=3)
    assert result["matches"][0]["id"] == "openmotion-ring-mask-reveal"


def test_compare_uses_shared_offsets_and_retries_same_native_frame(tmp_path, monkeypatch):
    source = tmp_path / "reference.mp4"
    source.write_bytes(b"fixture")
    asset = {"assetId": "source", "path": str(source), "mediaType": "video/mp4",
             "checksumSha256": motion.sha256_file(source)}
    calls = []

    def render(method, **args):
        assert method == "render.frame"
        calls.append((args["frame"], args["maxSide"]))
        if calls[-1] == (30, 480):
            raise ValueError("out of memory")
        Image.new("RGB", (320, 360), "#ff0000").save(args["outputPath"])

    def source_still(asset, second, output, deadline):
        assert asset["path"] == str(source)
        calls.append(second)
        Image.new("RGB", (320, 360), "#0000ff").save(output)

    monkeypatch.setattr(motion.craft_review, "_metadata", lambda *args: {"durationSeconds": 4, "video": True})
    monkeypatch.setattr(motion.craft_source_media, "still", source_still)
    draft = SimpleNamespace(directory=tmp_path, params={"media": [asset]},
                            project={"fps": 30, "durationMs": 4000}, call=render,
                            batches=2, deadline=time.monotonic() + 30)
    args = {"assetId": "source", "referenceStartSeconds": 0.5, "draftStartSeconds": 1,
            "offsets": [0, 0.5, 1]}
    text, image = motion.compare(draft, args, None)
    report = json.loads(text["text"])
    assert report["draftBatch"] == 2
    assert report["referenceSeconds"] == [.5, 1, 1.5]
    assert report["draftFrames"] == [30, 45, 60]
    assert calls == [.5, 1, 1.5, (30, 480), (30, 300), (45, 480), (60, 480)]
    with Image.open(BytesIO(base64.b64decode(image["source"]["data"]))) as sheet:
        assert sheet.getpixel((160, 150))[2] > 240
        assert sheet.getpixel((160, 600))[0] > 240
    with pytest.raises(ValueError, match="offsets_collide"):
        motion.compare(draft, {**args, "offsets": [0, .001, 1]}, None)
