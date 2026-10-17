from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

MUSE_TALK_COMMIT = "0a89dec45a0192b824e3cf4daf96c239440c5ed8"
REQUIRED_MODEL_FILES = frozenset(
    {
        "models/musetalkV15/musetalk.json",
        "models/musetalkV15/unet.pth",
        "models/syncnet/latentsync_syncnet.pt",
        "models/dwpose/dw-ll_ucoco_384.pth",
        "models/face-parse-bisent/79999_iter.pth",
        "models/face-parse-bisent/resnet18-5c106cde.pth",
        "models/sd-vae/config.json",
        "models/sd-vae/diffusion_pytorch_model.bin",
        "models/whisper/config.json",
        "models/whisper/pytorch_model.bin",
        "models/whisper/preprocessor_config.json",
    }
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _probe(path: Path) -> dict[str, Any]:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return json.loads(result.stdout)


def _duration(payload: dict[str, Any]) -> float:
    return float(payload["format"]["duration"])


def _verify_models(repository: Path, manifest_path: Path) -> str:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    files = payload.get("files")
    if not isinstance(files, list):
        raise ValueError("musetalk_model_manifest_files_missing")
    paths = {entry.get("relativePath") for entry in files}
    if paths != REQUIRED_MODEL_FILES:
        raise ValueError("musetalk_model_manifest_scope_mismatch")
    if payload.get("allLicensesReviewed") is not True:
        raise ValueError("musetalk_model_licenses_not_approved")
    for entry in files:
        relative = entry["relativePath"]
        if entry.get("licenseDecision") != "approved":
            raise ValueError(f"musetalk_model_license_not_approved:{relative}")
        source = repository / Path(*PurePosixPath(relative).parts)
        if not source.is_file() or _sha256(source) != entry.get("checksumSha256"):
            raise ValueError(f"musetalk_model_integrity_failed:{relative}")
    return _sha256(manifest_path)


def _write_json(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fail-closed MuseTalk 1.5 Caio Vale pilot runner.")
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--source-video", type=Path, required=True)
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--model-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    repository = args.repository.resolve()
    commit = subprocess.run(
        ["git", "-C", str(repository), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    ).stdout.strip()
    if commit != MUSE_TALK_COMMIT:
        raise ValueError("musetalk_commit_mismatch")
    if subprocess.run(
        ["git", "-C", str(repository), "status", "--porcelain"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    ).stdout.strip():
        raise ValueError("musetalk_worktree_not_clean")
    model_manifest_digest = _verify_models(repository, args.model_manifest.resolve())

    source = args.source_video.resolve()
    audio = args.audio.resolve()
    if not source.is_file() or not audio.is_file():
        raise FileNotFoundError("musetalk_inputs_missing")
    source_probe = _probe(source)
    audio_probe = _probe(audio)
    source_videos = [item for item in source_probe["streams"] if item.get("codec_type") == "video"]
    source_audio = [item for item in source_probe["streams"] if item.get("codec_type") == "audio"]
    if len(source_videos) != 1 or source_audio:
        raise ValueError("musetalk_source_requires_one_video_and_zero_audio_streams")
    if (source_videos[0].get("width"), source_videos[0].get("height")) != (720, 1280):
        raise ValueError("musetalk_source_resolution_mismatch")
    audio_duration = _duration(audio_probe)
    if not 24 <= audio_duration <= 45:
        raise ValueError("musetalk_audio_duration_outside_content_fit")

    output_dir = args.output_dir.resolve()
    work_dir = output_dir / "musetalk-work-v1"
    result_dir = work_dir / "results"
    output_dir.mkdir(parents=True, exist_ok=True)
    work_dir.mkdir(parents=True, exist_ok=True)
    normalized = work_dir / "caio-base-25fps.mp4"
    config = work_dir / "inference.yaml"
    raw_result = result_dir / "v15" / "raw-ad-v1.mp4"
    canonical = output_dir / "clicko-studios-caio-vale-raw-ad-v1.mp4"
    result_manifest = output_dir / "clicko-studios-caio-vale-raw-ad-v1.result.json"
    if canonical.exists() or result_manifest.exists():
        raise FileExistsError("musetalk_pilot_output_already_exists")

    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(source),
            "-an",
            "-vf",
            "fps=25",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(normalized),
        ],
        check=True,
        timeout=900,
    )
    config.write_text(
        "task_0:\n"
        f'  video_path: "{normalized.as_posix()}"\n'
        f'  audio_path: "{audio.as_posix()}"\n'
        '  result_name: "raw-ad-v1.mp4"\n',
        encoding="utf-8",
    )
    subprocess.run(
        [
            str(args.python.resolve()),
            "-m",
            "scripts.inference",
            "--inference_config",
            str(config),
            "--result_dir",
            str(result_dir),
            "--unet_model_path",
            "models/musetalkV15/unet.pth",
            "--unet_config",
            "models/musetalkV15/musetalk.json",
            "--version",
            "v15",
            "--fps",
            "25",
            "--batch_size",
            "1",
            "--use_float16",
        ],
        cwd=repository,
        check=True,
        timeout=7200,
    )
    if not raw_result.is_file():
        raise FileNotFoundError("musetalk_did_not_create_expected_output")
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(raw_result),
            "-map",
            "0:v:0",
            "-map",
            "0:a:0",
            "-c",
            "copy",
            "-metadata",
            "comment=Synthetic presenter rendered locally with MuseTalk 1.5",
            str(canonical),
        ],
        check=True,
        timeout=600,
    )
    final_probe = _probe(canonical)
    if abs(_duration(final_probe) - audio_duration) > 0.25:
        raise ValueError("musetalk_output_duration_mismatch")
    result = {
        "schemaVersion": "studio.avatar-render-evaluation-result.v1",
        "provider": "musetalk-v1.5-local",
        "providerCommit": MUSE_TALK_COMMIT,
        "heygemModelCreated": False,
        "sourceChecksumSha256": _sha256(source),
        "audioChecksumSha256": _sha256(audio),
        "modelManifestDigestSha256": model_manifest_digest,
        "artifactChecksumSha256": _sha256(canonical),
        "fps": 25,
        "precision": "fp16",
        "batchSize": 1,
        "durationSeconds": _duration(final_probe),
        "publicationState": "private_review",
        "generatedAt": datetime.now(UTC).isoformat(),
    }
    _write_json(result_manifest, result)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
