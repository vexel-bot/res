import pytest

from app.services.studios.craft_artifact_copy import checksum, copy_verified


def test_unchanged_delivery_is_not_rewritten_while_consumers_read_it(tmp_path):
    source, target = tmp_path / "source", tmp_path / "target"
    source.write_bytes(b"native movie bytes")
    assert copy_verified(source, target)
    before = target.stat().st_mtime_ns
    with target.open("rb") as reader:
        assert copy_verified(source, target, checksum(source)) is False
        assert reader.read() == b"native movie bytes"
    assert target.stat().st_mtime_ns == before


def test_bad_copy_does_not_destroy_a_preserved_candidate(tmp_path):
    source, target = tmp_path / "source", tmp_path / "target"
    source.write_bytes(b"different")
    target.write_bytes(b"preserved")
    with pytest.raises(ValueError, match="checksum_mismatch"):
        copy_verified(source, target, "0" * 64)
    assert target.read_bytes() == b"preserved"
