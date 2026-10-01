"""One-shot offline local generation runner."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from execution_store import atomic_json
from model_store import repository_directory, status
from preflight import inspect
from profile_registry import get_profile


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _camera_prompt(camera: dict) -> str:
    return {
        "static": "locked-off camera",
        "push_in": "gentle camera push in",
        "pull_out": "gentle camera pull out",
        "pan": "slow controlled camera pan",
        "orbit": "subtle camera orbit",
    }.get(camera.get("type", "static"), "locked-off camera")


def _export_frames(frames, output: Path, fps: int) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise ValueError("local_diffusion_ffmpeg_unavailable")
    with tempfile.TemporaryDirectory(prefix="res-local-video-") as temporary:
        frame_directory = Path(temporary)
        for index, frame in enumerate(frames):
            frame.save(frame_directory / f"frame-{index:06d}.png", format="PNG")
        command = [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-framerate",
            str(fps),
            "-i",
            str(frame_directory / "frame-%06d.png"),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(output),
        ]
        completed = subprocess.run(command, capture_output=True, text=True, timeout=120)
        if completed.returncode != 0 or not output.is_file():
            raise ValueError("local_diffusion_video_export_failed")


def run(request_path, output_path):
    request = json.loads(Path(request_path).read_text(encoding="utf-8"))
    profile = request.get("profileSnapshot") or get_profile(request.get("profileId"))
    if profile.get("profileId") != request.get("profileId"):
        raise ValueError("local_diffusion_profile_snapshot_conflict")
    if request.get("operation") != profile["operation"]:
        raise ValueError("local_diffusion_operation_unavailable")
    if float(request["durationSeconds"]) > float(profile["maximumDurationSeconds"]):
        raise ValueError("local_diffusion_duration_unavailable")
    # The authenticated API already performs the CUDA/package qualification.
    # Repeating the Torch smoke test here briefly doubles the runtime footprint
    # on low-memory hosts before inference has even started.
    admission = inspect(profile_id=profile["profileId"], phase="execution", check_environment=False)
    if admission["status"] != "admitted":
        return {"status": "blocked_resources", "preflight": admission}
    provisioned = status(profile["profileId"])
    if provisioned["status"] != "ready":
        return {"status": "model_unavailable", "modelStatus": provisioned}
    repositories = {
        item["id"]: repository_directory(profile["profileId"], item["id"]) for item in profile["repositories"]
    }
    prompt = f"{request['prompt'].strip()}, {_camera_prompt(request.get('cameraIntent', {}))}"
    started = time.monotonic()
    if profile["adapter"] == "animatediff_lightning":
        from adapters.animatediff_lightning import generate
    else:
        raise ValueError("local_diffusion_adapter_unavailable")
    frames, torch, timings = generate(profile, repositories, prompt, int(request["seed"]))
    output = Path(output_path).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    export_started = time.monotonic()
    _export_frames(frames, output, fps=int(profile["fps"]))
    timings["videoExportSeconds"] = time.monotonic() - export_started
    profile_digest = hashlib.sha256(
        json.dumps(profile, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    if request.get("profileDigestSha256") and request["profileDigestSha256"] != profile_digest:
        raise ValueError("local_diffusion_profile_snapshot_digest_mismatch")
    dependency_versions = {}
    for package in ("diffusers", "transformers", "accelerate", "safetensors"):
        try:
            dependency_versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            dependency_versions[package] = None
    content_flagged = timings.get("contentSafetyStatus") == "flagged"
    return {
        "schemaVersion": "studio.scene-generation-receipt.v2",
        "executionId": request.get("executionId"),
        "status": "content_flagged" if content_flagged else "candidate_generated",
        "artifact": {"path": str(output), "checksumSha256": _sha256(output)},
        "profileId": profile["profileId"],
        "adapter": profile["adapter"],
        "profileDigestSha256": profile_digest,
        "requestDigestSha256": request.get("requestDigest"),
        "runtimeDigests": request.get("runtimeDigests", {}),
        "modelRepositories": [
            {
                "id": repository["id"],
                "revision": repository["revision"],
                "pinnedArtifacts": repository.get("artifacts", []),
            }
            for repository in profile["repositories"]
        ],
        "runtime": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "cuda": torch.version.cuda,
            "device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
            "dependencies": dependency_versions,
        },
        "seed": request["seed"],
        "effectiveParameters": {
            key: profile[key]
            for key in ("width", "height", "frames", "fps", "inferenceSteps", "guidanceScale", "scheduler")
        },
        "durationRequestedSeconds": request["durationSeconds"],
        "durationProducedSeconds": profile["frames"] / profile["fps"],
        "elapsedSeconds": time.monotonic() - started,
        "stageTimings": timings,
        "peakCudaMemoryBytes": torch.cuda.max_memory_allocated() if torch.cuda.is_available() else 0,
        "cameraControl": "prompt_guidance",
        "negativePromptApplied": float(profile["guidanceScale"]) > 1,
        "contentSafety": {
            "status": timings.get("contentSafetyStatus", "unknown"),
            "disposition": timings.get("contentSafetyDisposition", "quarantine"),
            "framesChecked": timings.get("contentSafetyFramesChecked", 0),
            "flaggedFrames": timings.get("contentSafetyFlaggedFrames", []),
        },
        "acceptance": "quarantined_content_signal" if content_flagged else "pending_visual_review",
    }


if __name__ == "__main__":
    request = {}
    try:
        request = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
        result = run(sys.argv[1], sys.argv[2])
    except Exception as error:
        import traceback

        traceback.print_exc(file=sys.stderr)
        Path(sys.argv[3]).with_name("runner-error.log").write_text(
            traceback.format_exc(), encoding="utf-8"
        )
        detail = str(error)
        public_detail = detail if detail.startswith("local_diffusion_") else "local_inference_failed"
        result = {
            "schemaVersion": "studio.scene-generation-receipt.v2",
            "executionId": request.get("executionId"),
            "profileId": request.get("profileId"),
            "profileDigestSha256": request.get("profileDigestSha256"),
            "requestDigestSha256": request.get("requestDigest"),
            "runtimeDigests": request.get("runtimeDigests", {}),
            "status": "failed",
            "stage": "inference",
            "errorCode": type(error).__name__,
            "errorMessage": public_detail,
        }
    atomic_json(Path(sys.argv[3]), result)
