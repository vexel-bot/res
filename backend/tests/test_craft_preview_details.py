"""Detail observations keep their selected pixels and do not mutate the draft."""
import base64
from io import BytesIO
import json
from pathlib import Path

from PIL import Image
import pytest

from app.services.studios.craft_agent import Draft


@pytest.fixture(autouse=True)
def clean_database():
    yield


def fake_draft(tmp_path):
    draft = Draft.__new__(Draft)
    draft.directory = tmp_path
    draft.project = {"fps": 30, "durationMs": 1000}
    draft.engine = "effectcraft"
    draft.batches = 7
    calls = []

    def render(method, **args):
        calls.append((method, args))
        side = args["maxSide"]
        im = Image.new("RGB", (side // 2, side), "red")
        im.paste("blue", (im.width // 2, 0, im.width, im.height))
        im.save(Path(args["outputPath"]))

    draft.call = render
    return draft, calls


def test_native_detail_retains_requested_pixels_and_reports_observed_crop(tmp_path):
    draft, calls = fake_draft(tmp_path)
    blocks = draft.run("preview_frame", {"frame": 15, "maximumSide": 1920, "crop": [.5, 0, .5, 1]})
    submitted = Image.open(BytesIO(base64.b64decode(blocks[0]["source"]["data"])))
    assert submitted.size == (480, 1920)
    assert submitted.getpixel((100, 100))[2] > 240
    metadata = json.loads(blocks[1]["text"])
    assert metadata["renderedDimensions"] == [960, 1920]
    assert metadata["submittedDimensions"] == [480, 1920]
    assert "outside the crop" in metadata["coverage"]
    assert metadata["frame"] == 15 and metadata["draftBatch"] == 7
    assert calls[0][1]["maxSide"] == 1920 and draft.batches == 7


def test_legacy_preview_keeps_default_size_and_result_shape(tmp_path):
    draft, calls = fake_draft(tmp_path)
    blocks = draft.run("preview_frame", {"frame": 0})
    assert len(blocks) == 1
    assert Image.open(BytesIO(base64.b64decode(blocks[0]["source"]["data"]))).size == (512, 1024)
    assert calls[0][1]["maxSide"] == 1024 and draft.batches == 7


def test_observed_dimensions_describe_submitted_pixels_when_engine_ignores_size(tmp_path):
    draft, _ = fake_draft(tmp_path)
    draft.call = lambda method, **args: Image.new("RGB", (1080, 1920)).save(args["outputPath"])
    blocks = draft.run("preview_frame", {"frame": 1, "maximumSide": 512})
    submitted = Image.open(BytesIO(base64.b64decode(blocks[0]["source"]["data"])))
    metadata = json.loads(blocks[1]["text"])
    assert metadata["renderedDimensions"] == [1080, 1920]
    assert metadata["submittedDimensions"] == list(submitted.size) == [288, 512]


@pytest.mark.parametrize("args", [
    {"frame": -1}, {"frame": 30}, {"frame": True}, {"frame": 0, "maximumSide": 2049},
    {"frame": 0, "maximumSide": True}, {"frame": 0, "maxSide": 1920},
    {"frame": 0, "crop": [0, 0, 2, 1]}, {"frame": 0, "crop": [0, 0, 0, 1]},
    {"frame": 0, "crop": [0, 0, float("nan"), 1]}, {"frame": 0, "crop": [.8, 0, .4, 1]},
])
def test_invalid_observation_is_rejected_before_rendering(tmp_path, args):
    draft, calls = fake_draft(tmp_path)
    with pytest.raises(ValueError, match="craft_preview_frame_"):
        draft.run("preview_frame", args)
    assert not calls and draft.batches == 7
