from __future__ import annotations

import gc
import json
import time
from pathlib import Path


def _tensor_stats(torch, value):
    sample = value.detach().float()
    if not bool(torch.isfinite(sample).all()):
        raise ValueError("local_diffusion_numeric_failure")
    return {
        "minimum": float(sample.min().item()),
        "maximum": float(sample.max().item()),
        "mean": float(sample.mean().item()),
        "standardDeviation": float(sample.std().item()),
        "shape": list(sample.shape),
    }


def _content_safety_scores(torch, safety_checker, clip_input):
    """Expose the legacy checker's evidence without changing its verdict."""
    import torch.nn.functional as functional

    pooled_output = safety_checker.vision_model(clip_input)[1]
    image_embeds = safety_checker.visual_projection(pooled_output)
    normalized_image = functional.normalize(image_embeds)
    special = torch.mm(
        normalized_image,
        functional.normalize(safety_checker.special_care_embeds).t(),
    )[0].cpu().float()
    concepts = torch.mm(
        normalized_image,
        functional.normalize(safety_checker.concept_embeds).t(),
    )[0].cpu().float()
    special_margins = special - safety_checker.special_care_embeds_weights.cpu().float()
    adjustment = 0.01 if bool(torch.any(torch.round(special_margins * 1000) / 1000 > 0)) else 0.0
    concept_margins = concepts - safety_checker.concept_embeds_weights.cpu().float() + adjustment
    rounded = torch.round(concept_margins * 1000) / 1000
    return {
        "maximumSpecialMargin": float(special_margins.max().item()),
        "maximumConceptMargin": float(concept_margins.max().item()),
        "flaggedConceptIds": [
            int(index) for index, value in enumerate(rounded.tolist()) if value > 0
        ],
    }


def _copy_checkpoint_entries(torch, targets, safe_open, checkpoints):
    loaded = set()
    with torch.no_grad():
        for checkpoint_path in checkpoints:
            with safe_open(str(checkpoint_path), framework="pt", device="cpu") as checkpoint:
                for key in checkpoint.keys():
                    target = targets.get(key)
                    if target is None:
                        continue
                    source = checkpoint.get_tensor(key)
                    if not bool(torch.isfinite(source).all()):
                        raise ValueError("local_diffusion_checkpoint_nonfinite:" + key)
                    if tuple(source.shape) != tuple(target.shape):
                        raise ValueError("local_diffusion_checkpoint_shape_mismatch:" + key)
                    target.copy_(source.to(device=target.device, dtype=target.dtype))
                    loaded.add(key)
                    del source
    return loaded


def _motion_unet_config(base_root: Path):
    config = json.loads((base_root / "unet" / "config.json").read_text(encoding="utf-8"))
    config["_class_name"] = "UNetMotionModel"
    config["down_block_types"] = [
        "CrossAttnDownBlockMotion" if "CrossAttn" in name else "DownBlockMotion"
        for name in config["down_block_types"]
    ]
    config["up_block_types"] = [
        "CrossAttnUpBlockMotion" if "CrossAttn" in name else "UpBlockMotion"
        for name in config["up_block_types"]
    ]
    config.update(
        {
            "layers_per_block": 2,
            "motion_num_attention_heads": 8,
            "motion_max_seq_length": 32,
            "use_motion_mid_block": True,
            "temporal_transformer_layers_per_block": 1,
            "temporal_transformer_layers_per_mid_block": 1,
        }
    )
    if not config.get("num_attention_heads"):
        config["num_attention_heads"] = config["attention_head_dim"]
    return config


def inspect_checkpoint_structure(torch, unet_class, safe_open, base_root: Path, motion_root: Path):
    previous_dtype = torch.get_default_dtype()
    try:
        torch.set_default_dtype(torch.float16)
        with torch.device("meta"):
            unet = unet_class.from_config(_motion_unet_config(base_root))
    finally:
        torch.set_default_dtype(previous_dtype)
    expected = {key: tuple(value.shape) for key, value in unet.state_dict().items()}
    found = {}
    for checkpoint_path in (
        base_root / "unet" / "diffusion_pytorch_model.fp16.safetensors",
        motion_root / "animatediff_lightning_4step_diffusers.safetensors",
    ):
        with safe_open(str(checkpoint_path), framework="pt", device="cpu") as checkpoint:
            for key in checkpoint.keys():
                if key in expected:
                    found[key] = tuple(checkpoint.get_slice(key).get_shape())
    mismatched = sorted(key for key, shape in found.items() if shape != expected[key])
    missing = sorted(set(expected) - set(found))
    return {
        "expectedStateEntries": len(expected),
        "checkpointStateEntries": len(found),
        "missingStateEntries": missing,
        "shapeMismatches": mismatched,
        "status": "passed" if not missing and not mismatched else "failed",
    }


def _stream_motion_unet(torch, unet_class, safe_open, base_root: Path, motion_root: Path):
    """Build the temporal UNet on CUDA without materializing two UNets in RAM."""
    config = _motion_unet_config(base_root)

    previous_dtype = torch.get_default_dtype()
    try:
        torch.set_default_dtype(torch.float16)
        with torch.device("meta"):
            unet = unet_class.from_config(config)
    finally:
        torch.set_default_dtype(previous_dtype)
    unet.to_empty(device="cuda")

    targets = unet.state_dict()
    checkpoints = (
        base_root / "unet" / "diffusion_pytorch_model.fp16.safetensors",
        motion_root / "animatediff_lightning_4step_diffusers.safetensors",
    )
    loaded = _copy_checkpoint_entries(torch, targets, safe_open, checkpoints)
    missing = sorted(set(targets) - loaded)
    del targets
    gc.collect()
    if missing:
        raise ValueError(f"local_diffusion_unet_weights_incomplete:{','.join(missing[:8])}")
    return unet, {
        "expectedStateEntries": len(loaded) + len(missing),
        "loadedStateEntries": len(loaded),
        "missingStateEntries": missing,
        "allCheckpointValuesFinite": True,
    }


def generate(profile: dict, repositories: dict[str, Path], prompt: str, seed: int):
    load_started = time.monotonic()
    import torch
    from diffusers import AnimateDiffPipeline, EulerDiscreteScheduler, UNetMotionModel
    from safetensors import safe_open

    motion_root = repositories["ByteDance/AnimateDiff-Lightning"]
    base_root = repositories["stable-diffusion-v1-5/stable-diffusion-v1-5"]
    dtype = torch.float16
    unet, state_validation = _stream_motion_unet(torch, UNetMotionModel, safe_open, base_root, motion_root)
    pipeline = AnimateDiffPipeline.from_pretrained(
        str(base_root),
        unet=unet,
        motion_adapter=None,
        torch_dtype=dtype,
        variant="fp16",
        local_files_only=True,
        use_safetensors=True,
        low_cpu_mem_usage=True,
        safety_checker=None,
        feature_extractor=None,
        requires_safety_checker=False,
        # Loading every component on CPU creates a transient peak larger than
        # the 8 GiB host can sustain. Balanced dispatch streams components to
        # the RTX during deserialization and keeps overflow on CPU.
        device_map="balanced",
        max_memory={0: "3000MB"},
        offload_folder=str(base_root.parent.parent / ".offload"),
    )
    pipeline.scheduler = EulerDiscreteScheduler.from_config(
        pipeline.scheduler.config, timestep_spacing="trailing", beta_schedule="linear"
    )
    pipeline.vae.enable_slicing()
    pipeline.enable_attention_slicing("max")
    if hasattr(pipeline.unet, "enable_forward_chunking"):
        pipeline.unet.enable_forward_chunking(chunk_size=1, dim=1)
    load_seconds = time.monotonic() - load_started
    inference_started = time.monotonic()
    denoising_stats = []

    def observe_step(_pipeline, step, timestep, callback_kwargs):
        stats = _tensor_stats(torch, callback_kwargs["latents"])
        stats.update({"step": int(step), "timestep": int(timestep)})
        denoising_stats.append(stats)
        return callback_kwargs

    output = pipeline(
        prompt=prompt,
        negative_prompt="text, watermark, logo, deformed, flicker, low quality",
        width=int(profile["width"]),
        height=int(profile["height"]),
        num_frames=int(profile["frames"]),
        guidance_scale=float(profile["guidanceScale"]),
        num_inference_steps=int(profile["inferenceSteps"]),
        generator=torch.Generator(device="cpu").manual_seed(seed),
        callback_on_step_end=observe_step,
        callback_on_step_end_tensor_inputs=["latents"],
    )
    denoising_and_decode_seconds = time.monotonic() - inference_started
    frames = output.frames[0]
    del output, pipeline, unet
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    # The safety checker is loaded only after diffusion has been unloaded. This
    # preserves the content check while avoiding an otherwise unnecessary peak
    # where the pipeline, checkpoint copy, CLIP processor and checker coexist.
    safety_started = time.monotonic()
    import numpy as np
    from diffusers.pipelines.stable_diffusion.safety_checker import StableDiffusionSafetyChecker
    from transformers import CLIPImageProcessorPil

    feature_extractor = CLIPImageProcessorPil.from_pretrained(
        str(base_root / "feature_extractor"), local_files_only=True
    )
    # Run the CPU classifier in FP32. Its output is still advisory because the
    # legacy SD 1.5 checker has known false positives; a positive result sends
    # the candidate to quarantine and can never grant automatic admission.
    safety_checker = StableDiffusionSafetyChecker.from_pretrained(
        str(base_root / "safety_checker"),
        torch_dtype=torch.float32,
        variant="fp16",
        local_files_only=True,
        use_safetensors=True,
        low_cpu_mem_usage=True,
    ).to("cpu")
    checked_frames = 0
    frame_stats = []
    flagged_frames = []
    for index, frame in enumerate(frames):
        clip_input = feature_extractor(images=[frame], return_tensors="pt").pixel_values.float()
        image = np.asarray(frame, dtype=np.float32)[None, ...] / 255.0
        if not np.isfinite(image).all():
            raise ValueError("local_diffusion_numeric_failure:decoded_frame")
        frame_stats.append(
            {
                "index": index,
                "minimum": float(image.min()),
                "maximum": float(image.max()),
                "mean": float(image.mean()),
                "standardDeviation": float(image.std()),
            }
        )
        score_evidence = _content_safety_scores(torch, safety_checker, clip_input)
        _, flags = safety_checker(images=image.copy(), clip_input=clip_input)
        checked_frames += 1
        frame_stats[-1]["contentSafety"] = score_evidence
        if any(bool(flag) for flag in flags):
            flagged_frames.append(index)
    del safety_checker, feature_extractor
    gc.collect()
    return (
        frames,
        torch,
        {
            "modelLoadSeconds": load_seconds,
            "denoisingAndDecodeSeconds": denoising_and_decode_seconds,
            "contentSafetySeconds": time.monotonic() - safety_started,
            "contentSafetyFramesChecked": checked_frames,
            "contentSafetyFlaggedFrames": flagged_frames,
            "contentSafetyStatus": "flagged" if flagged_frames else "passed",
            "contentSafetyDisposition": "quarantine" if flagged_frames else "eligible_for_visual_review",
            "stateValidation": state_validation,
            "denoisingStatistics": denoising_stats,
            "decodedFrameStatistics": frame_stats,
        },
    )
