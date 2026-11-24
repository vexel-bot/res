import subprocess
import time

import pytest

from app.services.studios.craft_source_media import shot_candidates


def test_shot_scan_reports_source_time_and_keeps_continuous_window(tmp_path):
    path = tmp_path / "cuts.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i",
                    "color=black:s=160x90:r=24:d=3,drawbox=x=0:y=0:w=iw:h=ih:color=white:t=fill:enable='gte(t,1)'",
                    "-threads", "1", "-pix_fmt", "yuv420p", str(path)], check=True)
    asset = {"assetId": "fixture", "checksumSha256": "a" * 64, "path": str(path)}
    full = shot_candidates(asset, 3, time.monotonic()+20, start=.5, duration=1.5)
    assert full["checksumSha256"] == asset["checksumSha256"]
    assert full["nextStartSeconds"] == 2
    assert [item["second"] for item in full["candidates"]] == pytest.approx([1], abs=1/24)
    continuous = shot_candidates(asset, 3, time.monotonic()+20, start=1.5)
    assert continuous["candidates"] == []
    assert continuous["nextStartSeconds"] is None
    with pytest.raises(ValueError, match="craft_shot_window_invalid"):
        shot_candidates(asset, 3, time.monotonic()+20, duration=float("nan"))
