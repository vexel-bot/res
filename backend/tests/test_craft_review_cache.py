"""Interrupted native renders must never poison subsequent temporal reviews."""
from pathlib import Path
from types import SimpleNamespace
import shutil
import subprocess

import pytest

from app.services.studios.craft_review import _draft_metadata


@pytest.fixture(autouse=True)
def clean_database():
    yield


def test_interrupted_render_removes_partial_file_without_publishing_cache(tmp_path):
    output = tmp_path/'draft.mp4'
    def interrupted(_method, **params):
        Path(params['outputPath']).write_bytes(b'partial mp4')
        raise ValueError('Adapter exited 137')
    with pytest.raises(ValueError, match='Adapter exited 137'):
        _draft_metadata(SimpleNamespace(deadline=float('inf'), call=interrupted), output)
    assert not output.exists()
    assert not list(tmp_path.glob('*.pending.mp4'))


@pytest.mark.skipif(not shutil.which('ffmpeg'), reason='local media qualification requires FFmpeg')
def test_corrupt_cached_render_is_replaced_once_and_valid_cache_is_reused(tmp_path):
    output = tmp_path/'draft.mp4'
    output.write_bytes(b'partial old cache')
    exports = []
    def export(_method, **params):
        exports.append(params['outputPath'])
        subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=red:s=16x16:r=30:d=0.1',
                        '-threads','1','-c:v','libx264',params['outputPath']], check=True, timeout=30)
    draft = SimpleNamespace(deadline=float('inf'), call=export)
    first = _draft_metadata(draft, output)
    second = _draft_metadata(draft, output)
    assert len(exports) == 1 and first == second
    assert first['video']['width'] == 16 and first['durationSeconds'] > 0
    assert output.exists() and not list(tmp_path.glob('*.pending.mp4'))
