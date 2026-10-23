"""Shared FFmpeg/ffprobe discovery. Explicit configuration never falls back silently."""

import os
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path

from ...config import get_settings

ROOT = Path(__file__).resolve().parents[4]


def resolve_tool(name, configured=None):
    configured = configured or getattr(get_settings(), name + "_path")
    found = shutil.which(configured)
    if found:
        return found
    if configured != name:
        raise ValueError("timeline_" + name + "_unavailable")
    candidates = sorted(
        (ROOT / ".codex-runtime" / "ffmpeg").glob("*/bin/" + name + (".exe" if os.name == "nt" else ""))
    )
    if candidates:
        return str(candidates[-1])
    raise ValueError("timeline_" + name + "_unavailable")


@lru_cache(maxsize=8)
def h264_encoder(executable):
    result = subprocess.run(
        [executable, "-hide_banner", "-encoders"],
        capture_output=True,
        text=True,
        timeout=15,
        check=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    names = {parts[1] for line in result.stdout.splitlines() if len(parts := line.split()) >= 2}
    for name in ("libopenh264", "libx264"):
        if name in names:
            return name
    raise ValueError("media_h264_encoder_unavailable")
