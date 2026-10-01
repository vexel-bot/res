"""Atomic execution state and non-destructive process identity checks."""

from __future__ import annotations

import ctypes
import hashlib
import json
import os
import time
from pathlib import Path


def atomic_json(path: Path, value: dict) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")
    temporary.replace(path)


def request_digest(payload: dict) -> str:
    value = {key: item for key, item in payload.items() if key != "executionId"}
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def file_sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def process_identity(pid: int) -> str | None:
    if pid <= 0:
        return None
    if os.name == "nt":
        handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
        if not handle:
            return None
        try:
            creation, exit_time, kernel, user = (ctypes.c_ulonglong() for _ in range(4))
            if not ctypes.windll.kernel32.GetProcessTimes(
                handle, ctypes.byref(creation), ctypes.byref(exit_time), ctypes.byref(kernel), ctypes.byref(user)
            ):
                return None
            return f"windows-filetime:{creation.value}"
        finally:
            ctypes.windll.kernel32.CloseHandle(handle)
    stat = Path(f"/proc/{pid}/stat")
    if stat.is_file():
        fields = stat.read_text(encoding="utf-8").split()
        return f"proc-start:{fields[21]}" if len(fields) > 21 else None
    try:
        os.kill(pid, 0)
        return "posix-unknown"
    except OSError:
        return None


def process_matches(descriptor: dict) -> bool:
    current = process_identity(int(descriptor.get("pid", 0)))
    return current is not None and current == descriptor.get("identity")


def lease_stale(lease: dict, descriptor: dict | None, grace_seconds=30) -> bool:
    if descriptor and process_matches(descriptor):
        return False
    return time.time() - float(lease.get("createdAt", 0)) > grace_seconds
