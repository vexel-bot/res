import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

spec=importlib.util.spec_from_file_location('source_patches',Path(__file__).resolve().parents[2]/'scripts/craft/source_patches.py')
patches=importlib.util.module_from_spec(spec);spec.loader.exec_module(patches)


def test_overlay_restores_exact_bytes_even_after_failed_build_and_rejects_unknown_sources(tmp_path):
    source=tmp_path/'source.rs';original=b'original\r\n';source.write_bytes(original)
    manifest=tmp_path/'workers/craft/patches/effect-audio-levels.json';manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({'path':'source.rs','sourceSha256':hashlib.sha256(original).hexdigest(),
        'replacements':[{'before':'original','after':'patched'}]}))
    with pytest.raises(RuntimeError):
        with patches.patched_sources(tmp_path):
            assert source.read_bytes()==b'patched\n'
            raise RuntimeError('compiler failed')
    assert source.read_bytes()==original
    source.write_bytes(b'new user edit')
    with pytest.raises(ValueError,match='exact_upstream_hash'):
        with patches.patched_sources(tmp_path):pass
    assert source.read_bytes()==b'new user edit'
