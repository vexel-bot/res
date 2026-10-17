import json
import os

import pytest

from app.providers.studios import heavy_media_lease as lease


def test_heavy_media_lease_blocks_concurrent_operation_and_releases(tmp_path, monkeypatch):
    path = tmp_path / ".heavy-media-lease.json"
    monkeypatch.setattr(lease, "lease_path", lambda: path)

    with lease.heavy_media_lease("video_render", "render-1") as receipt:
        assert receipt["operation"] == "video_render"
        assert path.is_file()
        with pytest.raises(ValueError, match="heavy_media_execution_in_progress"):
            with lease.heavy_media_lease("background_removal", "cutout-1"):
                pass

    assert not path.exists()


def test_heavy_media_lease_recovers_dead_owner(tmp_path, monkeypatch):
    path = tmp_path / ".heavy-media-lease.json"
    path.write_text(
        json.dumps({"pid": os.getpid(), "identity": "stale", "executionId": "old"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(lease, "lease_path", lambda: path)

    with lease.heavy_media_lease("video_render", "new"):
        assert json.loads(path.read_text(encoding="utf-8"))["executionId"] == "new"

    assert not path.exists()
