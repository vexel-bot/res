"""Clean final-audio runner for the pinned LongCat Avatar 1.5 checkout.

This entry point performs real upstream inference on a separately provisioned
Linux/CUDA host. CPU tests exercise media handling and process control only.
No model download, provider promotion or output-quality qualification occurs.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import signal
import subprocess
import sys
import time
from fractions import Fraction
from pathlib import Path

from clean_audio import SOURCE_REVISION, patched_demo
from preflight import sha256_file
from protocol import AvatarExecutionRequest


def atomic_json(path: Path, payload: dict):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    os.replace(temporary, path)


def run_process(
    command: list[str],
    *,
    root: Path,
    env: dict | None = None,
    cwd: Path | None = None,
    timeout: float = 7200,
):
    """One job owns one process group; cancel/timeout also stop torch ranks."""
    if (root / "cancel").exists():
        raise InterruptedError("cancelled")
    with (root / "runner.log").open("ab") as log:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=os.name != "nt",
        )
        start = time.monotonic()
        try:
            while process.poll() is None:
                if (root / "cancel").exists():
                    raise InterruptedError("cancelled")
                if time.monotonic() - start > timeout:
                    raise TimeoutError("longcat_process_timeout")
                time.sleep(0.1)
            if process.returncode:
                raise ValueError("longcat_process_failed")
        finally:
            if process.poll() is None:
                if os.name == "nt":
                    process.kill()
                else:
                    os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    if os.name != "nt":
                        os.killpg(process.pid, signal.SIGKILL)
                    else:
                        process.kill()
                    process.wait(timeout=5)


def probe(path: Path, ffprobe: str) -> dict:
    result = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return json.loads(result.stdout)


def prepare_media(
    root: Path, request: AvatarExecutionRequest, ffmpeg: str, ffprobe: str
):
    for name, checksum in (
        ("reference-image", request.reference_image_checksum_sha256),
        ("driving-audio", request.driving_audio_checksum_sha256),
    ):
        path = root / name
        if not path.is_file() or path.is_symlink() or sha256_file(path) != checksum:
            raise ValueError("longcat_input_checksum_mismatch")
    original = probe(root / "driving-audio", ffprobe)
    if len([s for s in original["streams"] if s["codec_type"] == "audio"]) != 1:
        raise ValueError("longcat_single_audio_stream_required")
    duration_ms = request.avatar_request["drivingAudioDurationMs"]
    if abs(float(original["format"]["duration"]) * 1000 - duration_ms) > 80:
        raise ValueError("longcat_input_duration_mismatch")
    run_process(
        [
            ffmpeg,
            "-v",
            "error",
            "-nostdin",
            "-y",
            "-i",
            str(root / "driving-audio"),
            "-map",
            "0:a:0",
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            str(root / "clean-speech.wav"),
        ],
        root=root,
        timeout=120,
    )
    # The experimental profile is fixed landscape. Letterboxing preserves the
    # whole portrait instead of allowing an implicit crop or output-size change.
    run_process(
        [
            ffmpeg,
            "-v",
            "error",
            "-nostdin",
            "-y",
            "-i",
            str(root / "reference-image"),
            "-vf",
            "scale=832:480:force_original_aspect_ratio=decrease,pad=832:480:(ow-iw)/2:(oh-ih)/2,setsar=1",
            "-frames:v",
            "1",
            str(root / "reference.png"),
        ],
        root=root,
        timeout=120,
    )


def finalize(
    root: Path, request: AvatarExecutionRequest, ffmpeg: str, ffprobe: str
) -> dict:
    name = (
        "ai2v_demo_1.mp4"
        if request.segment_count == 1
        else f"video_continue_{request.segment_count}.mp4"
    )
    generated = root / "generated" / name
    if not generated.is_file() or generated.is_symlink():
        raise ValueError("longcat_generated_video_missing")
    output = root / "artifact.mp4"
    duration = request.avatar_request["drivingAudioDurationMs"] / 1000
    try:
        run_process(
            [
                ffmpeg,
                "-v",
                "error",
                "-nostdin",
                "-y",
                "-i",
                str(generated),
                "-i",
                str(root / "driving-audio"),
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-t",
                f"{duration:.3f}",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-r",
                "25",
                "-c:a",
                "aac",
                "-movflags",
                "+faststart",
                str(output),
            ],
            root=root,
            timeout=300,
        )
        media = probe(output, ffprobe)
        videos = [s for s in media["streams"] if s["codec_type"] == "video"]
        audios = [s for s in media["streams"] if s["codec_type"] == "audio"]
        if len(videos) != 1 or len(audios) != 1:
            raise ValueError("longcat_output_streams_invalid")
        video = videos[0]
        if (video["width"], video["height"], Fraction(video["avg_frame_rate"])) != (
            832,
            480,
            25,
        ):
            raise ValueError("longcat_output_parameters_mismatch")
        for stream in [video, audios[0]]:
            if abs(float(stream["duration"]) - duration) > 0.08:
                raise ValueError("longcat_output_duration_mismatch")
        return {
            "artifactChecksumSha256": sha256_file(output),
            "durationMs": round(duration * 1000),
            "segments": request.segment_count,
            "width": 832,
            "height": 480,
            "fps": 25,
        }
    except Exception:
        output.unlink(missing_ok=True)
        raise


def infer(
    root: Path, request: AvatarExecutionRequest, source_root: Path, model_root: Path
):
    if platform.system() != "Linux":
        raise ValueError("longcat_linux_cuda_required")
    revision = subprocess.run(
        ["git", "-C", str(source_root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    ).stdout.strip()
    dirty = subprocess.run(
        [
            "git",
            "-C",
            str(source_root),
            "status",
            "--porcelain",
            "--untracked-files=no",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    ).stdout.strip()
    if revision != SOURCE_REVISION or dirty:
        raise ValueError("longcat_source_checkout_mismatch")
    entry = root / "clean_audio_demo.py"
    entry.write_text(
        patched_demo(
            (source_root / "run_demo_avatar_single_audio_to_video.py").read_bytes()
        ),
        encoding="utf-8",
    )
    atomic_json(
        root / "input.json",
        {
            "prompt": request.avatar_request["performanceDirection"],
            "seed": request.avatar_request["seed"],
            "cond_image": str(root / "reference.png"),
            "cond_audio": {"person1": str(root / "clean-speech.wav")},
        },
    )
    generated = root / "generated"
    generated.mkdir(exist_ok=True)
    env = {
        **os.environ,
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "HF_HUB_DISABLE_TELEMETRY": "1",
        "PYTHONPATH": str(source_root),
    }
    run_process(
        [
            sys.executable,
            "-m",
            "torch.distributed.run",
            "--standalone",
            "--nnodes=1",
            "--nproc_per_node=2",
            str(entry),
            "--input_json",
            str(root / "input.json"),
            "--output_dir",
            str(generated),
            "--checkpoint_dir",
            str(model_root / "LongCat-Video-Avatar-1.5"),
            "--context_parallel_size",
            "2",
            "--model_type",
            "avatar-v1.5",
            "--stage_1",
            "ai2v",
            "--resolution",
            "480p",
            "--num_segments",
            str(request.segment_count),
            "--use_distill",
            "--use_int8",
        ],
        root=root,
        env=env,
        cwd=source_root,
    )


def run(root: Path, source_root: Path, model_root: Path, *, inference=infer):
    root = root.resolve()
    request = AvatarExecutionRequest.model_validate_json(
        (root / "request.json").read_text(encoding="utf-8")
    )
    ffmpeg, ffprobe = (
        os.getenv("FFMPEG_BINARY", "ffmpeg"),
        os.getenv("FFPROBE_BINARY", "ffprobe"),
    )
    atomic_json(root / "progress.json", {"stage": "preparing", "progress": 5})
    prepare_media(root, request, ffmpeg, ffprobe)
    atomic_json(root / "progress.json", {"stage": "inference", "progress": 15})
    inference(root, request, source_root.resolve(), model_root.resolve())
    if (root / "cancel").exists():
        raise InterruptedError("cancelled")
    atomic_json(root / "progress.json", {"stage": "encoding", "progress": 90})
    return finalize(root, request, ffmpeg, ffprobe)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--execution-dir", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--model-root", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.execution_dir, args.source_root, args.model_root)
    atomic_json(args.execution_dir / "result.json", result)
