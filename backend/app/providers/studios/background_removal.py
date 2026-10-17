"""Isolated, fail-closed local background removal adapter."""

import hashlib
import subprocess
import sys
from pathlib import Path

from PIL import Image

from .heavy_media_lease import heavy_media_lease


def remove_background(source: Path, destination: Path, settings):
    if not settings.studio_background_removal_enabled:
        raise ValueError("background_removal_not_configured")
    model = Path(settings.studio_background_removal_model_path or "").resolve()
    checksum = settings.studio_background_removal_model_sha256
    if model.name != "u2netp.onnx" or not model.is_file() or not checksum:
        raise ValueError("background_removal_pinned_model_required")
    if hashlib.sha256(model.read_bytes()).hexdigest() != checksum:
        raise ValueError("background_removal_model_checksum_mismatch")
    python = Path(settings.studio_background_removal_python_path or sys.executable).resolve()
    if not python.is_file():
        raise ValueError("background_removal_python_unavailable")
    worker = Path(__file__).with_name("rembg_worker.py")
    try:
        execution_id = "background-removal:" + hashlib.sha256(source.read_bytes()).hexdigest()
        with heavy_media_lease("background_removal", execution_id):
            subprocess.run(
                [str(python), str(worker), str(source), str(destination), str(model), checksum],
                check=True,
                capture_output=True,
                timeout=180,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
    except (OSError, subprocess.SubprocessError) as error:
        raise ValueError("background_removal_worker_failed") from error
    try:
        with Image.open(destination) as image:
            image.verify()
        with Image.open(destination) as image:
            if image.format != "PNG" or "A" not in image.getbands():
                raise ValueError("background_removal_alpha_missing")
            alpha = image.getchannel("A")
            low, high = alpha.getextrema()
            if low == high:
                raise ValueError("background_removal_alpha_unusable")
    except OSError as error:
        raise ValueError("background_removal_output_invalid") from error
    return {
        "provider": "local.rembg-u2netp",
        "model": "u2netp",
        "modelChecksum": checksum,
        "license": {
            "code": "MIT",
            "model": "Apache-2.0",
            "modelSource": "https://github.com/xuebinqin/U-2-Net",
        },
    }
