from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.musetalk_fixed_camera_pilot import MODEL_HASHES, SOURCE_SHA, cycle_index, validate_render_probe


def test_ping_pong_is_continuous_and_does_not_duplicate_endpoints():
    assert [cycle_index(i, 4) for i in range(12)] == [0, 1, 2, 3, 2, 1, 0, 1, 2, 3, 2, 1]
    values = [cycle_index(i, 300) for i in range(1125)]
    assert min(values) == 0
    assert max(values) == 299
    assert all(abs(a - b) == 1 for a, b in zip(values, values[1:], strict=False))


@pytest.mark.parametrize("index,count", [(-1, 3), (0, 1), (0, 0)])
def test_cycle_rejects_invalid_source(index, count):
    with pytest.raises(ValueError):
        cycle_index(index, count)


def test_render_requires_expected_streams_duration_and_frame_count():
    probe = {
        "streams": [
            {"codec_type": "video", "width": 720, "height": 1280, "avg_frame_rate": "25/1", "nb_frames": "75"},
            {"codec_type": "audio"},
        ],
        "format": {"duration": "3.0"},
    }
    validate_render_probe(probe, 75)
    with pytest.raises(ValueError, match="frame_count"):
        validate_render_probe(probe, 76)
    probe["format"]["duration"] = "4.0"
    with pytest.raises(ValueError, match="duration"):
        validate_render_probe(probe, 75)
    probe["streams"].pop()
    with pytest.raises(ValueError, match="stream_count"):
        validate_render_probe(probe, 75)


def test_private_license_scope_matches_exact_model_hashes():
    root = Path(__file__).resolve().parents[2]
    review = json.loads(
        (root / "docs/studios/knowledge/ledgers/musetalk-fixed-camera-private-model-review-2026-09-04.json")
        .read_text(encoding="utf-8")
    )
    assert review["fileHashes"] == MODEL_HASHES
    assert review["decision"] == "approved_private_evaluation"
    assert review["productionPromotion"] is False
    assert all(len(digest) == 64 for digest in MODEL_HASHES.values())
    ledger = json.loads(
        (root / "docs/studios/knowledge/ledgers/single-avatar-pilot-caio-vale-2026-09-02.json")
        .read_text(encoding="utf-8")
    )
    assert ledger["sourceVideo"]["checksumSha256"] == SOURCE_SHA
    assert ledger["verification"]["heygemModelCreated"] is False
