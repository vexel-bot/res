import hashlib
from pathlib import Path

import pytest

from app.config import Settings
from app.services.object_storage import LocalObjectStorage, normalize_key, object_key


def test_local_object_storage_is_tenant_scoped_hashed_and_materialized(tmp_path: Path) -> None:
    source = tmp_path / "source.bin"
    source.write_bytes(b"clicko-object-storage")
    root = tmp_path / "objects"
    storage = LocalObjectStorage(str(root))
    key = object_key("workspace-123", "raw", ".bin")

    stored = storage.put_file(
        source,
        key=key,
        media_type="application/octet-stream",
        metadata={"workspace-id": "workspace-123"},
    )

    assert key.startswith("workspace-123/raw/")
    assert stored.backend == "local"
    assert stored.size_bytes == len(b"clicko-object-storage")
    assert stored.checksum_sha256 == hashlib.sha256(b"clicko-object-storage").hexdigest()
    with storage.materialize(key) as materialized:
        assert materialized.read_bytes() == b"clicko-object-storage"

    storage.delete(key)
    assert not storage.exists(key)
    assert list(root.iterdir()) == []


@pytest.mark.parametrize("key", ["../secret", "/absolute", "workspace\\escape", "workspace/../escape"])
def test_object_storage_rejects_unsafe_keys(key: str) -> None:
    with pytest.raises(ValueError, match="invalid_object_storage_key"):
        normalize_key(key)


def test_duplicate_put_preserves_existing_object(tmp_path):
    storage = LocalObjectStorage(str(tmp_path / "objects"))
    original = tmp_path / "original.bin"
    original.write_bytes(b"original")
    replacement = tmp_path / "replacement.bin"
    replacement.write_bytes(b"replacement")
    storage.put_file(original, key="workspace/raw/object.bin", media_type="application/octet-stream")
    with pytest.raises(FileExistsError):
        storage.put_file(replacement, key="workspace/raw/object.bin", media_type="application/octet-stream")
    with storage.materialize("workspace/raw/object.bin") as stored:
        assert stored.read_bytes() == b"original"


def test_object_storage_configuration_requires_complete_credentials() -> None:
    with pytest.raises(RuntimeError, match="OBJECT_STORAGE_BUCKET"):
        Settings(object_storage_backend="s3").validate_for_startup()
    with pytest.raises(RuntimeError, match="configured together"):
        Settings(object_storage_access_key="access-only").validate_for_startup()
