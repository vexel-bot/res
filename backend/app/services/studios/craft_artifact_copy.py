"""Idempotent, verified local delivery copies without truncating an existing artifact."""
import hashlib
from pathlib import Path
import shutil


def checksum(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def copy_verified(source, destination, expected_sha256=None):
    source, destination = Path(source), Path(destination)
    expected = expected_sha256 or checksum(source)
    if destination.is_file() and checksum(destination) == expected:
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".copying")
    shutil.copyfile(source, temporary)
    if checksum(temporary) != expected:
        temporary.unlink(missing_ok=True)
        raise ValueError("craft_delivery_copy_checksum_mismatch")
    temporary.replace(destination)
    return True
