# Local automatic material effects

This worker prepares **moving-person mattes** with RVM MobileNetV3 ONNX and generates **background/region images** with the provisioned SD 1.5 model. It aligns the generated image to the original footage before the canonical timeline renders the editable layers.

## Installation

The tested segmentation environment uses the versions in `requirements-matting.txt`. Install those into the backend's selected Python environment, then run:

```powershell
.\.venv\Scripts\python.exe backend/scripts/provision_material_effects.py
```

Provisioning downloads the official 14,975,696-byte RVM ONNX artifact and checks its pinned SHA-256 before installation. Weights are ignored by Git. Inference never downloads weights.

Generation reuses `workers/media-generation-local/.venv` and the `animatediff-lightning-sd15-a-v1` profile's pinned **SD 1.5 base** cache. It uses `StableDiffusionImg2ImgPipeline`, not the AnimateDiff motion adapter. It checks weight hashes before loading. It requires CUDA and at least 2,800 MiB free VRAM at admission inside the isolated process. It retains the installed safety checker.

Model identities, sources and licenses are in `models.lock.json` and the existing SD profile. RVM's upstream license is GPL-3.0; the SD base profile records CreativeML-OpenRAIL-M. These internal experimental executions are not a claim of commercial/legal qualification.

## Execution and contracts

`POST /api/v1/studios/v1/materials/document/{id}/effects` accepts the bounded `EffectRequest`. Operations:

- `segment_person`: recurrent temporal matte; source, PNG cutout, clean-plate candidate, matte video, editable output and rendered MP4.
- `replace_background`: generate an image conditioned on the automatically prepared plate; reveal it behind the source person; retain the lower interaction area by default.
- `localized_edit`: generate an image and composite only its requested normalized rectangle, with feathered alpha. The source person remains above the region.

Clip duration: 2–12 seconds; output: 24 fps, at most 640 pixels per dimension. This profile is for constrained local tests. A wider platform does not automatically qualify longer/higher-resolution inference.

The job is durable, tenant scoped, idempotent and cancellable. An immutable request captures source checksum, kit version and document. A new editable document and reusable kit are committed with the resulting assets. The original document is preserved. Durable receipts prevent a completed job from generating again after acknowledgement interruption.

Inference workers receive an environment allowlist without API credentials. Hugging Face offline mode is enabled, outbound socket connection attempts are rejected, and there is no paid fallback. RVM uses CPU with two ONNX threads. Generative jobs advertise the GPU queue. Both stages use the host-wide heavy-media lease. Cancel/timeout closes the owned process tree on Windows.

## Quality limits

The RVM alpha uses sequential recurrent states. Scene-cut resets and motion-compensated alpha residuals are recorded as diagnostic evidence, not an approval score. There is no claim of perfect hair, transparent objects, multiple-person instance selection or held-product segmentation.

Background features outside the person and contact area drive a per-frame similarity transform. Forward/backward flow, spatially distributed inliers and plate coverage qualify the result. If registration fails, the job returns a copy of the original and records `camera.fallback=original_video`. The aligned plate uses transparency where the original camera reveals pixels outside the generated image.

The interaction band follows that transform and retains the observed desk or floor and its shadows. Connected motion near the contact boundary extends its protection around moving objects. The RVM foreground colors remove old background spill from translucent edges. This supports translation, roll and moderate zoom on a predominantly planar background. Strong parallax, large occlusions and lighting changes require a different approach. All outputs require review.

Primary implementation references:

- [RVM inference and recurrent-state contract](https://github.com/PeterL1n/RobustVideoMatting/blob/master/documentation/inference.md)
- [Diffusers image-to-image pipeline](https://huggingface.co/docs/diffusers/api/pipelines/stable_diffusion/img2img)
