"""Hash-checked build overlays; imported upstream sources are restored after build."""
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]


def manifest(root=ROOT):
    return json.loads((root/'workers/craft/patches/effect-audio-levels.json').read_text(encoding='utf8'))


@contextmanager
def patched_sources(root=ROOT):
    patch=manifest(root);path=(root/patch['path']).resolve()
    if not path.is_relative_to(root.resolve()):raise ValueError('patch_path_outside_repository')
    before=path.read_bytes()
    if hashlib.sha256(before).hexdigest()!=patch['sourceSha256']:
        raise ValueError('craft_source_patch_requires_exact_upstream_hash')
    text=before.decode('utf8').replace('\r\n','\n')
    for replacement in patch['replacements']:
        if text.count(replacement['before'])!=1:raise ValueError('craft_source_patch_anchor_not_unique')
        text=text.replace(replacement['before'],replacement['after'],1)
    changed=text.encode('utf8');path.write_bytes(changed)
    try:yield
    finally:
        if path.read_bytes()!=changed:raise ValueError('craft_source_changed_during_build_preserved_for_reconciliation')
        path.write_bytes(before)
