"""Offline, single-GPU Qwen appearance runner. No weights or libraries auto-install."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import time
from importlib.metadata import version
from pathlib import Path

from app.domain.studios.appearance_image import (
    DIFFUSERS_VERSION,
    PROVIDER_VERSION,
    AppearanceImageRequestV1,
    AppearanceImageResultV1,
    AppearanceModelManifestV1,
    canonical_digest,
    file_digest,
    verify_model_assets,
)

MANIFEST_PATH = Path(__file__).with_name("model-assets.v1.json")
MAX_IMAGE_PIXELS = 32 * 1024**2


def preflight(manifest, model_root, inventory=None):
    """A conservative memory floor for the unquantized candidate, not a benchmark."""
    weight_bytes = sum(
        item.size_bytes for item in manifest.files if item.path.endswith(".safetensors")
    )
    minimum_memory = weight_bytes + 4 * 1024**3
    blockers = []
    if model_root.is_symlink() or not model_root.is_dir():
        blockers.append("appearance_weights_not_installed")
    else:
        for entry in manifest.files:
            path = model_root / entry.path
            if (
                not path.is_file()
                or path.is_symlink()
                or path.stat().st_size != entry.size_bytes
            ):
                blockers.append("appearance_weights_not_installed")
                break
    if inventory is None:
        try:
            device = os.environ.get("CUDA_VISIBLE_DEVICES", "0").split(",")[0].strip()
            if not re.fullmatch(r"[0-9]+|GPU-[a-fA-F0-9-]+", device):
                raise ValueError("appearance_visible_device_invalid")
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--id",
                    device,
                    "--query-gpu=memory.total,memory.free",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            inventory = result.stdout if result.returncode == 0 else ""
        except (OSError, ValueError, subprocess.TimeoutExpired):
            inventory = ""
    devices = []
    for line in inventory.splitlines():
        try:
            total, free = (int(value.strip()) * 1024**2 for value in line.split(","))
            if 0 <= free <= total:
                devices.append({"totalBytes": total, "freeBytes": free})
        except ValueError:
            continue
    # This candidate loads on device 0; multiple small GPUs are not summed.
    if not devices or devices[0]["freeBytes"] < minimum_memory:
        blockers.append("appearance_single_gpu_memory_insufficient")
    return {
        "schemaVersion": "clicko.appearance-worker-preflight.v1",
        "providerVersion": PROVIDER_VERSION,
        "modelManifestDigestSha256": canonical_digest(manifest),
        "weightBytes": weight_bytes,
        "provisionalMinimumDeviceBytes": minimum_memory,
        "devices": devices,
        "usableForEvaluation": not blockers,
        "blockers": blockers,
        "qualityQualified": False,
        "assetHashesVerified": False,
    }


def open_image(path, checksum):
    from PIL import Image, ImageOps

    if (
        path.is_symlink()
        or not path.is_file()
        or path.stat().st_size > 50 * 1024**2
        or file_digest(path) != checksum
    ):
        raise ValueError("appearance_input_checksum_mismatch")
    with Image.open(path) as original:
        if (
            original.width * original.height > MAX_IMAGE_PIXELS
            or getattr(original, "n_frames", 1) != 1
        ):
            raise ValueError("appearance_input_dimensions_invalid")
        return ImageOps.exif_transpose(original).convert("RGB")


def load_pipeline(model_root):
    # Set offline policy before importing the hub or neural libraries. The
    # deployment must additionally isolate network/filesystem at container level.
    for name in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE", "HF_DATASETS_OFFLINE"):
        os.environ[name] = "1"
    if version("diffusers") != DIFFUSERS_VERSION:
        raise ValueError("appearance_diffusers_version_mismatch")
    import torch
    from diffusers import QwenImageEditPlusPipeline

    if not torch.cuda.is_available():
        raise ValueError("appearance_cuda_required")
    torch.cuda.set_device(0)
    pipeline = QwenImageEditPlusPipeline.from_pretrained(
        str(model_root),
        torch_dtype=torch.bfloat16,
        local_files_only=True,
        use_safetensors=True,
        device_map="cuda",
    )
    pipeline.set_progress_bar_config(disable=True)
    return pipeline, torch


def render(
    request,
    *,
    manifest,
    model_root,
    reference_path,
    source_path,
    output_path,
    cancelled=lambda: False,
    progress=lambda _: None,
    loader=load_pipeline,
    inventory=None,
):
    if bool(source_path) != bool(request.source_asset_id):
        raise ValueError("appearance_source_binding_incomplete")
    if output_path.exists():
        raise ValueError("appearance_destination_must_be_new")
    if cancelled():
        raise InterruptedError("appearance_cancelled_before_inference")
    images = [open_image(reference_path, request.reference_checksum_sha256)]
    if source_path:
        images.append(open_image(source_path, request.source_checksum_sha256))
    readiness = preflight(manifest, model_root, inventory)
    if not readiness["usableForEvaluation"]:
        raise ValueError(readiness["blockers"][0])
    verify_model_assets(manifest, model_root, cancelled)
    progress(5)
    if cancelled():
        raise InterruptedError("appearance_cancelled_before_model_load")
    started = time.perf_counter()
    pipeline, torch = loader(model_root)
    if cancelled():
        raise InterruptedError("appearance_cancelled_after_model_load")
    instruction = "Use image 1 as the appearance reference. Preserve the subject's identity and visual characteristics. "
    if source_path:
        instruction += "Use image 2 as the scene/material to edit. "
    instruction += request.direction

    def step(_pipeline, number, _timestep, values):
        if cancelled():
            raise InterruptedError("appearance_cancelled_during_inference")
        progress(min(95, 5 + int(90 * (number + 1) / request.inference_steps)))
        return values

    with torch.inference_mode():
        output = pipeline(
            image=images,
            prompt=instruction,
            width=request.width,
            height=request.height,
            num_inference_steps=request.inference_steps,
            true_cfg_scale=4.0,
            guidance_scale=1.0,
            negative_prompt=" ",
            num_images_per_prompt=1,
            generator=torch.Generator(device="cuda:0").manual_seed(request.seed),
            callback_on_step_end=step,
            callback_on_step_end_tensor_inputs=[],
        )
    if cancelled():
        raise InterruptedError("appearance_cancelled_after_inference")
    image = output.images[0]
    if image.size != (request.width, request.height):
        raise ValueError("appearance_output_dimensions_mismatch")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    created = False
    try:
        with output_path.open("xb") as destination:
            created = True
            image.convert("RGB").save(destination, format="PNG")
        if cancelled():
            raise InterruptedError("appearance_cancelled_before_receipt")
        result = AppearanceImageResultV1(
            provider_version=PROVIDER_VERSION,
            request_digest_sha256=canonical_digest(request),
            model_manifest_digest_sha256=canonical_digest(manifest),
            identity_ref=request.identity_ref,
            reference_checksum_sha256=request.reference_checksum_sha256,
            source_checksum_sha256=request.source_checksum_sha256,
            artifact_checksum_sha256=file_digest(output_path),
            width=image.width,
            height=image.height,
            wall_seconds=max(time.perf_counter() - started, 1e-9),
        )
    except Exception:
        if created:
            output_path.unlink(missing_ok=True)
        raise
    progress(100)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-root", type=Path, required=True)
    parser.add_argument("--model-manifest", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--check", action="store_true")
    for name in (
        "request",
        "reference",
        "source",
        "output",
        "result",
        "cancel-file",
        "progress",
    ):
        parser.add_argument("--" + name, type=Path)
    args = parser.parse_args()
    manifest = AppearanceModelManifestV1.model_validate_json(
        args.model_manifest.read_text(encoding="utf-8")
    )
    if args.check:
        print(json.dumps(preflight(manifest, args.model_root)))
        return
    if not all((args.request, args.reference, args.output, args.result)):
        parser.error(
            "--request, --reference, --output and --result are required for inference"
        )
    if (
        args.request.is_symlink()
        or args.request.stat().st_size > 65536
        or args.result.exists()
    ):
        raise ValueError("appearance_execution_files_invalid")
    request = AppearanceImageRequestV1.model_validate_json(
        args.request.read_text(encoding="utf-8")
    )

    def progress(value):
        if args.progress:
            temporary = args.progress.with_suffix(".tmp")
            temporary.write_text(str(value), encoding="utf-8")
            temporary.replace(args.progress)

    result = render(
        request,
        manifest=manifest,
        model_root=args.model_root,
        reference_path=args.reference,
        source_path=args.source,
        output_path=args.output,
        cancelled=lambda: bool(args.cancel_file and args.cancel_file.exists()),
        progress=progress,
    )
    try:
        with args.result.open("x", encoding="utf-8") as receipt:
            receipt.write(result.model_dump_json(by_alias=True))
    except Exception:
        args.output.unlink(missing_ok=True)
        raise


if __name__ == "__main__":
    main()
