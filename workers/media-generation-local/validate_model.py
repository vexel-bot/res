"""Read-only structural qualification for a provisioned local video model."""

from __future__ import annotations

import argparse
import json

from model_store import repository_directory, status
from profile_registry import get_profile


def validate(profile_id: str) -> dict:
    profile = get_profile(profile_id)
    provisioned = status(profile_id)
    if provisioned["status"] != "ready":
        return {
            "schemaVersion": "res.local-video-model-validation.v1",
            "profileId": profile_id,
            "status": "model_unavailable",
            "modelReadiness": provisioned,
        }
    if profile.get("adapter") != "animatediff_lightning":
        return {
            "schemaVersion": "res.local-video-model-validation.v1",
            "profileId": profile_id,
            "status": "adapter_unavailable",
        }
    import torch
    from diffusers import UNetMotionModel
    from safetensors import safe_open

    from adapters.animatediff_lightning import inspect_checkpoint_structure

    repositories = {
        item["id"]: repository_directory(profile_id, item["id"])
        for item in profile["repositories"]
    }
    result = inspect_checkpoint_structure(
        torch,
        UNetMotionModel,
        safe_open,
        repositories["stable-diffusion-v1-5/stable-diffusion-v1-5"],
        repositories["ByteDance/AnimateDiff-Lightning"],
    )
    return {
        "schemaVersion": "res.local-video-model-validation.v1",
        "profileId": profile_id,
        **result,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile-id", required=True)
    args = parser.parse_args()
    print(json.dumps(validate(args.profile_id), separators=(",", ":")))
