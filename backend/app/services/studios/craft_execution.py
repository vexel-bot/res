"""Detect native no-op commands without confusing JSON formatting with edits."""
import json
import shutil


def require_storage(path):
    # Working-space reserve; independent of financial budget and creative choices.
    if shutil.disk_usage(path).free < 1024 * 1024 * 1024:
        raise ValueError("craft_runtime_storage_exhausted")


def native_equivalent(before, after):
    left, right = before.read_bytes(), after.read_bytes()
    if left == right:
        return True
    try:
        a, b = json.loads(left), json.loads(right)
        return a == b
    except (ValueError, UnicodeError):
        return False
