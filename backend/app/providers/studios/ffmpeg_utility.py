"""Bounded FFmpeg utility for probing, sampling and generated-media conversion."""

import subprocess
import tempfile
import time

from .media_runtime import resolve_tool


class FFmpegUtility:
    def __init__(self, executable: str, timeout_seconds: int):
        self.executable = resolve_tool("ffmpeg", executable)
        self.timeout_seconds = timeout_seconds

    def _run(self, args, cwd, cancelled):
        with tempfile.TemporaryFile() as log:
            process = subprocess.Popen(
                [self.executable, *args],
                cwd=cwd,
                stdout=log,
                stderr=log,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            started = time.monotonic()
            try:
                while process.poll() is None:
                    if cancelled():
                        raise InterruptedError("editing_cancelled")
                    if time.monotonic() - started > self.timeout_seconds:
                        raise TimeoutError("editing_render_timeout")
                    time.sleep(0.1)
                if process.returncode:
                    log.seek(0)
                    raise ValueError("editing_ffmpeg_failed:" + log.read().decode(errors="replace")[-2000:])
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()
