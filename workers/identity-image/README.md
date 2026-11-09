# Appearance-conditioned image worker

This candidate uses Qwen Image Edit 2511 to condition a new image on a selected
appearance and, optionally, an existing scene image. It is separate from the
PhotoCraft portrait layer and from LongCat talking-video generation.

The typed request binds the identity version/grant, reference asset/checksum,
optional scene asset/checksum, creative direction, dimensions, seed and steps.
Input 1 is the appearance; input 2 is the scene. The prompt explicitly states
those roles. This is model guidance, not proof of preserved identity or pixels.
Every result requires review and remains unqualified until measured separately.

## Frozen candidate

| Input | Revision |
| --- | --- |
| Qwen source repository | `QwenLM/Qwen-Image`, `6b5e1f5cec987d404be5ac6657db3b9aacb56a89` |
| Model | `Qwen/Qwen-Image-Edit-2511`, `6f3ccc0b56e431dc6a0c2b2039706d7d26f22cb9` |
| Diffusers | `0.42.0`, commit `95f9b8925c34469ccac829866d7ad4e3fca1bd89` |
| Torch | `2.6.0+cu124` |
| Transformers | `5.16.1` |
| Dependencies | `candidate/uv.lock`, SHA-256 `2bc620e445e02453d2464801e2243c2803f55e9350777de4af00a16587798d1d` |

The complete Qwen source checkout is retained locally at
`.candidate-build/qwen-image-source` (86 commits, 15 tracked files at this
revision, non-shallow, clean). It is excluded from build contexts and public
assets. This small source repository is not the model weights. The manifest
records all 35 upstream model files. Safetensors alone total 57,699,249,798 bytes.
No model weights were downloaded for the contract tests.

The source and model card identify Apache-2.0. Approval of the complete dependency
and deployment license chain remains separate. The CUDA lock resolution does
not prove runtime compatibility or qualify model outputs.

## Resource check and execution

With `PYTHONPATH=backend`, run:

```text
python workers/identity-image/runner.py --check --model-root /private/models/qwen-image-edit-2511
```

The check imports no Torch and performs no downloads. It checks inventory sizes
and the selected GPU's free memory; it explicitly reports that asset hashes
have not yet been verified. Multiple small GPUs are not summed. The provisional
baseline requires weight bytes plus 4 GiB on one device, and remains unqualified.
This is a conservative screening rule, not a measured peak or performance claim.
`CUDA_VISIBLE_DEVICES`, if supplied, selects the physical device queried.

The runner does not switch to CPU or quantized weights when the baseline fails.
On the inspected 4 GiB GPU this candidate cannot start. Quantized/offloaded
profiles need their own dependency, memory and visual evidence.

Asset preparation uses the frozen manifest:

```text
python backend/scripts/download_appearance_model_assets.py --manifest workers/identity-image/model-assets.v1.json --model-root /private/models/qwen-image-edit-2511
```

The default verifies existing files. Add `--download` only to explicitly fetch
missing public bytes. The downloader checks available disk space first, streams
with size/SHA-256 bounds and publishes complete files without overwriting an
existing destination. Mismatched existing files stop preparation.

Inference arguments, on a provisioned compatible host:

```text
python workers/identity-image/runner.py --model-root /private/models/qwen-image-edit-2511 --request /private/job/request.json --reference /private/job/reference.png --source /private/job/scene.png --output /private/job/output.png --result /private/job/result.json --cancel-file /private/job/cancel --progress /private/job/progress
```

Omit `--source` only when the request also omits its scene binding. The runner
verifies every model file before loading, enforces local-only safetensors and
offline Hub settings, and checks cancellation during denoising. Output is a new
PNG, with no original file replaced. The receipt binds the request, appearance,
reference, scene, manifest, dimensions and output checksum.

`QwenAppearanceProvider` owns a private temporary directory, validates receipts
before copying a result, and stops its owned process tree on timeout/cancellation.
Its child inherits only runtime/system environment, not provider credentials.
This process adapter is an internal evaluation port. Deployment must still
enforce container filesystem/network isolation and pass the registry gates;
offline Hub flags alone are not network isolation.

## Image recipe

`Dockerfile.candidate` uses the frozen lock, checks the pipeline imports and
keeps weights out of the image. The scoped `.dockerignore` excludes private data,
credentials, model caches and Craft sources. Build from the repository root:

```text
docker build -f workers/identity-image/Dockerfile.candidate -t clicko-qwen-appearance:candidate .
```

This recipe does not register a provider or approve a face. Candidate image
construction and model inference are different checks. Use a non-root,
read-only, network-disabled container with read-only model/input mounts on the
qualified host; only the private output directory should be writable.

## Verification and remaining integration

```text
python -m unittest discover -s workers/identity-image/tests -v
```

Tests use tiny generated color images, fake model objects and an explicit
subprocess fixture. They exercise ordered inputs, request/result bindings,
complete asset verification, cancellation, timeout, output preservation and
credential isolation. They are not a face-fidelity benchmark.

The project job boundary, commercial image admission and consent rechecks are
implemented with contract fixtures. Client controls and real model validation
still need to be completed. The
provider registry remains empty. Do not call this port directly from an HTTP
request or treat an unverified model image as a ready client feature.

Primary sources:

- https://github.com/QwenLM/Qwen-Image
- https://huggingface.co/Qwen/Qwen-Image-Edit-2511
- https://github.com/huggingface/diffusers/blob/v0.42.0/src/diffusers/pipelines/qwenimage/pipeline_qwenimage_edit_plus.py
