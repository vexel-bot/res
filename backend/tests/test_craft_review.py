import base64
import shutil
import subprocess
import time
from io import BytesIO
from types import SimpleNamespace

import pytest
from PIL import Image, ImageStat

from app.services.object_storage import sha256_file
from app.services.studios.craft_review import review_draft


@pytest.fixture
def source(tmp_path):
    path = tmp_path / "temporal-fixture.mp4"
    subprocess.run([
        "ffmpeg", "-v", "error", "-nostdin", "-y", "-f", "lavfi", "-i",
        "color=black:s=96x96:r=12:d=1,drawbox=x=0:y=0:w=iw:h=ih:color=white:t=fill:enable='between(t,0.249,0.32)'",
        "-f", "lavfi", "-i", "aevalsrc='if(between(t,0.25,0.5),0.5*sin(2*PI*440*t),0)':s=16000:d=1",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(path),
    ], capture_output=True, check=True)
    return path


def test_review_observes_consecutive_frames_and_measures_sound(source, tmp_path):
    draft = SimpleNamespace(directory=tmp_path, batches=0, deadline=time.monotonic() + 90,
                            params={"media": [{"assetId": "source", "path": str(source), "mediaType": "video/mp4",
                                               "checksumSha256": sha256_file(source)}]})
    result = review_draft(draft, {"assetId": "source", "durationSeconds": 1})
    report = result["report"]
    assert report["visual"]["nativeRateRequested"]
    assert report["visual"]["sampledSeconds"][3] == 0.25
    assert len(report["visual"]["sampledSeconds"]) == 12
    assert report["visual"]["nextPage"] is None
    assert report["audio"]["status"] == "measured"
    assert any(abs(event["timeSeconds"] - 0.25) < 0.05 for event in report["audio"]["onsets"])
    assert report["audio"]["silenceIntervals"][0]["startSeconds"] == 0
    assert report["transcript"]["status"] == "unavailable"
    assert "no perceptual listening" in report["audio"]["interpretation"]
    image = Image.open(BytesIO(base64.b64decode(result["blocks"][1]["source"]["data"])))
    assert ImageStat.Stat(image.crop((3 * 310 + 10, 50, 4 * 310 - 10, 200))).mean[0] > 200
    assert ImageStat.Stat(image.crop((10, 50, 300, 200))).mean[0] < 25
    assert result["path"].is_file()


def test_overview_covers_the_last_frame_without_claiming_native_rate_observation(source, tmp_path):
    draft = SimpleNamespace(directory=tmp_path, batches=0, deadline=time.monotonic() + 90,
                            params={"media": [{"assetId": "source", "path": str(source), "mediaType": "video/mp4",
                                               "checksumSha256": sha256_file(source)}]})
    result = review_draft(draft, {"assetId": "source", "durationSeconds": 1, "sampling": "overview", "pageSize": 4})
    visual = result["report"]["visual"]
    assert visual["sampledSeconds"][0] == 0
    assert visual["sampledSeconds"][-1] > .9
    assert visual["totalSamples"] == 4 and visual["nextPage"] is None
    assert not visual["nativeRateRequested"] and not visual["consecutiveOnRequestedGrid"]


def test_draft_review_caches_render_and_invalidates_after_edit(source, tmp_path):
    native = tmp_path / "draft.ecproj"
    native.write_text("revision 1")
    calls = []

    def render(method, **args):
        calls.append(method)
        shutil.copyfile(source, args["outputPath"])
        return {}

    draft = SimpleNamespace(engine="effectcraft", directory=tmp_path, batches=1, deadline=time.monotonic() + 90,
                            params={"nativePath": str(native)}, call=render)
    first = review_draft(draft, {"pageSize": 6})
    second = review_draft(draft, {"pageSize": 6, "page": 1})
    assert calls == ["render.export"]
    assert first["report"]["visual"]["nextPage"] == 1
    assert second["report"]["visual"]["sampledSeconds"][0] == 0.5
    assert first["path"] == second["path"]
    native.write_text("revision 2")
    draft.batches = 2
    changed = review_draft(draft, {})
    assert calls == ["render.export", "render.export"]
    assert changed["report"]["source"]["nativeChecksumSha256"] != first["report"]["source"]["nativeChecksumSha256"]


def test_focused_native_review_rebases_samples_and_sound_to_composition(source, tmp_path):
    native = tmp_path / "draft.ecproj"
    native.write_text("revision 1")
    calls = []

    def render(method, **args):
        assert method == "render.export"
        calls.append(args["reviewWindow"])
        if args["reviewWindow"]["resolutionDivisor"] == 2:
            raise ValueError("out of memory")
        shutil.copyfile(source, args["outputPath"])

    draft = SimpleNamespace(engine="effectcraft", directory=tmp_path, batches=1, deadline=time.monotonic() + 90,
                            capability={"temporalReview": {"frameRange": True}}, call=render,
                            project={"fps": 12, "width": 1080, "height": 1920, "durationMs": 10000},
                            params={"nativePath": str(native)})
    result = review_draft(draft, {"startSeconds": 3, "durationSeconds": 1})
    report = result["report"]
    assert calls == [{"firstFrame": 36, "endFrameExclusive": 48, "resolutionDivisor": divisor}
                     for divisor in (2, 4)]
    assert report["source"]["reviewWindow"]["resolutionDivisor"] == 4
    assert report["interval"] == {"startSeconds": 3, "endSeconds": 4, "durationSeconds": 1}
    assert report["visual"]["sampledSeconds"][3] == 3.25
    assert any(abs(event["timeSeconds"] - 3.25) < .05 for event in report["audio"]["onsets"])

def test_segmented_export_retries_only_failed_ranges(source, tmp_path):
    from app.services.studios.craft_review import _metadata, render_frame_ranges
    from app.providers.studios.craft import CraftRuntimeError

    ranges = []

    def render(_method, **args):
        window = args["reviewWindow"]
        start, stop = window["firstFrame"], window["endFrameExclusive"]
        ranges.append((start, stop))
        if stop - start > 12:
            raise CraftRuntimeError("craft_runtime_failed", "Adapter exited 137")
        shutil.copyfile(source, args["outputPath"])

    output = tmp_path / "recovered.mp4"
    deadline = time.monotonic() + 90
    render_frame_ranges(render, output, {"firstFrame": 0, "endFrameExclusive": 24, "resolutionDivisor": 1},
                        12, "high", deadline)
    info = _metadata(output, deadline)
    assert ranges == [(0, 24), (0, 12), (12, 24)]
    assert info["hasAudio"] and int(info["video"]["nb_frames"]) == 24
    assert info["durationSeconds"] == pytest.approx(2)
