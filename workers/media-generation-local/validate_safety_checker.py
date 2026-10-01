"""Validate the pinned content checker against deterministic benign fixtures."""

from __future__ import annotations

import argparse
import gc
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from execution_store import atomic_json, file_sha256
from model_store import repository_directory


def validate(profile_id: str) -> dict:
    import torch
    from diffusers.pipelines.stable_diffusion.safety_checker import StableDiffusionSafetyChecker
    from transformers import CLIPImageProcessorPil

    base = repository_directory(profile_id, "stable-diffusion-v1-5/stable-diffusion-v1-5")
    fixtures = [
        ("solid-white", Image.new("RGB", (256, 256), (255, 255, 255))),
        ("solid-blue", Image.new("RGB", (256, 256), (40, 90, 220))),
        ("solid-gray", Image.new("RGB", (256, 256), (128, 128, 128))),
    ]
    shapes = Image.new("RGB", (256, 256), "white")
    drawing = ImageDraw.Draw(shapes)
    drawing.rectangle((40, 100, 100, 150), fill="blue")
    drawing.ellipse((155, 100, 210, 155), fill="red")
    fixtures.append(("benign-shapes", shapes))

    processor = CLIPImageProcessorPil.from_pretrained(
        str(base / "feature_extractor"), local_files_only=True
    )
    variants = []
    for label, dtype in (("fp16", torch.float16), ("fp32", torch.float32)):
        checker = StableDiffusionSafetyChecker.from_pretrained(
            str(base / "safety_checker"),
            local_files_only=True,
            use_safetensors=True,
            low_cpu_mem_usage=True,
            torch_dtype=dtype,
            variant="fp16",
        ).to("cpu")
        results = []
        for fixture_id, image in fixtures:
            clip_input = processor(images=[image], return_tensors="pt").pixel_values.to(dtype)
            pixels = np.asarray(image, dtype=np.float32)[None, ...] / 255.0
            _, flags = checker(images=pixels.copy(), clip_input=clip_input)
            results.append({"fixtureId": fixture_id, "flagged": bool(flags[0])})
        variants.append({"precision": label, "results": results})
        del checker
        gc.collect()

    false_positives = [
        {"precision": variant["precision"], **result}
        for variant in variants
        for result in variant["results"]
        if result["flagged"]
    ]
    return {
        "schemaVersion": "res.local-video-content-safety-validation.v1",
        "profileId": profile_id,
        "checkerChecksumSha256": file_sha256(base / "safety_checker" / "model.fp16.safetensors"),
        "fixtures": [fixture_id for fixture_id, _ in fixtures],
        "variants": variants,
        "status": "false_positive_observed" if false_positives else "passed_benign_fixtures",
        "falsePositives": false_positives,
        "policy": "flagged generated frames remain quarantined; the checker is not bypassed",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile-id", default="animatediff-lightning-sd15-a-v1")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    receipt = validate(args.profile_id)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    atomic_json(output, receipt)
    print(json.dumps(receipt, separators=(",", ":")))
