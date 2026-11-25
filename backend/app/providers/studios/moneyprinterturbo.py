"""Prepare frame-accurate inputs for MoneyPrinterTurbo's assembly function."""

import os
import shutil
import subprocess
from fractions import Fraction
from pathlib import Path

from ...config import get_settings
from .media_runtime import resolve_tool
from .timeline_ffmpeg import probe

PROVIDER = "moneyprinterturbo"
FPS = 30
REVISION = "2dc10e850d78c61264a64ea180def2b7f1f334d8"
SIZES = {"9:16": (1080, 1920), "16:9": (1920, 1080), "1:1": (1080, 1080)}
# The worker lives in a separate interpreter because Clicko and upstream both
# use the top-level package name "app".
ASSEMBLE = """
import sys
sys.path.insert(0, sys.argv[1])
from app.services.video import concat_video_clips_with_ffmpeg
from pathlib import Path
if len(sys.argv) > 2:
    output = Path(sys.argv[2])
    concat_video_clips_with_ffmpeg(sys.argv[3:], str(output), 2, str(output.parent))
"""


def runtime():
    local = runtime_root()
    interpreter = local / ("venv/Scripts/python.exe" if os.name == "nt" else "venv/bin/python")
    source = Path(os.environ.get("CLICKO_MPT_SOURCE") or local / f"MoneyPrinterTurbo-{REVISION}").resolve()
    python = shutil.which(os.environ.get("CLICKO_MPT_PYTHON") or str(interpreter))
    if not python or not (source / "app" / "services" / "video.py").is_file():
        raise ValueError("moneyprinterturbo_runtime_unavailable")
    return source, python


def runtime_root():
    configured = os.environ.get("CLICKO_MPT_ROOT")
    if configured:
        return Path(configured).resolve()
    return Path(os.environ.get("LOCALAPPDATA") or Path.home() / ".local" / "share") / "Clicko-MoneyPrinterTurbo"


def require_available():
    settings = get_settings()
    if settings.studio_isolated_queues_enabled and not settings.celery_task_always_eager:
        if not settings.studio_moneyprinterturbo_worker_enabled:
            raise ValueError("moneyprinterturbo_runtime_unavailable")
    else:
        runtime()
        resolve_tool("ffmpeg")
        resolve_tool("ffprobe")


def render(plan, paths, directory, progress, cancelled):
    source, python = runtime()
    ffmpeg = resolve_tool("ffmpeg")
    directory = Path(directory).resolve()
    width, height = SIZES[plan.aspect]
    expected_frames = sum(clip.duration_frames for clip in plan.clips)
    duration = expected_frames / FPS
    audio = paths[plan.audio_asset_id] if plan.audio_asset_id else None
    if audio:
        audio_info = probe(audio)
        if not any(stream["codec_type"] == "audio" for stream in audio_info["streams"]):
            raise ValueError("moneyprinterturbo_invalid_audio")
        if abs(float(audio_info["format"]["duration"]) - duration) > 1 / FPS:
            raise ValueError("moneyprinterturbo_audio_duration_mismatch")

    def run(command, name, environment=None):
        if cancelled():
            raise InterruptedError
        with (directory / f"{name}.log").open("wb") as log:
            with subprocess.Popen(
                command, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                env=environment, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            ) as process:
                try:
                    process.wait(timeout=900)
                except subprocess.TimeoutExpired as exc:
                    process.kill()
                    raise ValueError("moneyprinterturbo_render_timeout") from exc
                if process.returncode:
                    raise ValueError(f"moneyprinterturbo_{name}_failed")
        if cancelled():
            raise InterruptedError

    scenes = []
    for index, clip in enumerate(plan.clips):
        path = paths[clip.asset_id]
        info = probe(path)
        video = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
        if not video or video["width"] * video["height"] > 3840 * 2160:
            raise ValueError("moneyprinterturbo_invalid_source_video")
        end = (clip.start_frame + clip.duration_frames) / FPS
        if end > float(video.get("duration", info["format"]["duration"])) + 0.001:
            raise ValueError("moneyprinterturbo_source_range_exceeded")
        target = directory / f"scene-{index:03}.mp4"
        fit = (
            f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}"
            if clip.fit == "cover"
            else f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"
        )
        run(
            [ffmpeg, "-nostdin", "-y", "-v", "error", "-ss", f"{clip.start_frame / FPS:.9f}",
             "-protocol_whitelist", "file,pipe", "-i", str(path), "-map", "0:v:0", "-an",
             "-vf", f"{fit},setsar=1,fps={FPS}",
             "-frames:v", str(clip.duration_frames), "-c:v", "libx264", "-threads", "2",
             "-pix_fmt", "yuv420p", str(target)],
            "prepare_clip",
        )
        verify_video(target, clip.duration_frames)
        scenes.append(str(target))
        progress(10 + (index + 1) * 55 // len(plan.clips))

    picture = directory / "picture.mp4"
    system_variables = ("PATH", "SystemRoot", "WINDIR", "TEMP", "TMP", "TMPDIR", "LANG", "LC_ALL")
    environment = {
        **{name: os.environ[name] for name in system_variables if name in os.environ},
        "MPT_HOME": str(directory / "mpt"),
        "IMAGEIO_FFMPEG_EXE": ffmpeg,
        "FFMPEG_BINARY": ffmpeg,
    }
    run([python, "-I", "-c", ASSEMBLE, str(source), str(picture), *scenes], "assemble", environment)
    verify_video(picture, expected_frames)
    progress(82)
    output = directory / "video.mp4"
    if audio:
        run([ffmpeg, "-nostdin", "-y", "-v", "error", "-i", str(picture),
             "-protocol_whitelist", "file,pipe", "-i", str(audio),
             "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac",
             "-af", "apad", "-t", f"{duration:.9f}", "-movflags", "+faststart", str(output)], "mux")
        verify_video(output, expected_frames)
    else:
        picture.replace(output)
    return output, {"durationSeconds": duration, "width": width, "height": height, "frameRate": FPS}


def verify_video(path, frames):
    info = probe(path)
    video = next(stream for stream in info["streams"] if stream["codec_type"] == "video")
    if int(video.get("nb_frames", 0)) != frames or Fraction(video["avg_frame_rate"]) != FPS:
        raise ValueError("moneyprinterturbo_render_timing_mismatch")
