"""One host-wide lease for memory-heavy local media operations."""

from __future__ import annotations

import ctypes
import json
import os
import time
from contextlib import contextmanager
from pathlib import Path


def _identity(pid: int) -> str | None:
    if pid <= 0:
        return None
    if os.name == "nt":
        handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
        if not handle:
            return None
        try:
            creation, exit_time, kernel, user = (ctypes.c_ulonglong() for _ in range(4))
            if not ctypes.windll.kernel32.GetProcessTimes(
                handle,
                ctypes.byref(creation),
                ctypes.byref(exit_time),
                ctypes.byref(kernel),
                ctypes.byref(user),
            ):
                return None
            # Keep this byte-for-byte compatible with the local diffusion
            # worker. Both processes must be able to prove that the lease
            # owner is still the same OS process after a PID is reused.
            return f"windows-filetime:{creation.value}"
        finally:
            ctypes.windll.kernel32.CloseHandle(handle)
    try:
        stat = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8").split()
    except OSError:
        return None
    return f"proc-start:{stat[21]}" if len(stat) > 21 else None


def lease_path() -> Path:
    root = Path(__file__).resolve().parents[4]
    directory = root / "workers" / "media-generation-local" / ".runs"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / ".heavy-media-lease.json"


def _read(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _active(value: dict | None) -> bool:
    if not value:
        return False
    pid = int(value.get("pid", 0))
    return _identity(pid) == value.get("identity")


@contextmanager
def heavy_media_lease(operation: str, execution_id: str):
    path = lease_path()
    existing = _read(path)
    if existing and not _active(existing):
        path.unlink(missing_ok=True)
    descriptor = None
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        pid = os.getpid()
        payload = {
            "ownerType": "backend_media_operation",
            "operation": operation,
            "executionId": execution_id,
            "pid": pid,
            "identity": _identity(pid),
            "createdAt": time.time(),
        }
        with os.fdopen(descriptor, "w", encoding="utf-8") as target:
            descriptor = None
            json.dump(payload, target, sort_keys=True)
        yield payload
    except FileExistsError as error:
        raise ValueError("heavy_media_execution_in_progress") from error
    finally:
        if descriptor is not None:
            os.close(descriptor)
        owned = _read(path)
        if owned and owned.get("executionId") == execution_id and owned.get("identity") == _identity(os.getpid()):
            path.unlink(missing_ok=True)
