"""Private, fixed-camera MuseTalk benchmark; not a general avatar provider.

Uses the separately pinned MIT MuseTalk modules, without editing that checkout.
Static ROI replaces DWPose/S3FD for the admitted, locked-camera fictional source.
Models are staged sequentially to fit the RTX 2050; no cloud generation or upload.
"""

from __future__ import annotations

import argparse
import gc
import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path

from scripts.run_musetalk_avatar_pilot import MUSE_TALK_COMMIT, _probe, _sha256, _write_json

SOURCE_SHA = "e777ee42a96a44c4f1e56b8ff8273e9f1a12d2d2127a6fe11fa0675234921912"
ROI = (100, 174, 565, 650)
MODEL_HASHES = {
    "musetalkV15/musetalk.json": "5b6923aee04d71692e0e9846c471e0a4ea07a4f686d39545e472bd4ba17e1b47",
    "musetalkV15/unet.pth": "7ebf6c98c181e20838e4c0054e96e944ac60d5d692cc01db42839fe11b787007",
    "sd-vae/config.json": "92d3dfb746fca211a2c9e019e285f8597412211728dce3c5bcf4eda0f2d62e7e",
    "sd-vae/diffusion_pytorch_model.bin": "1b4889b6b1d4ce7ae320a02dedaeff1780ad77d415ea0d744b476155c6377ddc",
    "whisper/config.json": "ffdccec4f3211f4c63310f2b7098f309fe70f3952cedc5e4d11e43f5b2379b98",
    "whisper/preprocessor_config.json": "9b5cd03a36fbb8a627c64d98a5b5b126ead95a77720723944487311f0110b666",
    "whisper/pytorch_model.bin": "9607f98a2b22d9e229ae43c52ecea79dcede9e0c5cfae67e8da6eda86d8aac1d",
    "face-parse-bisent/79999_iter.pth": "468e13ca13a9b43cc0881a9f99083a430e9c0a38abd935431d1c28ee94b26567",
    "face-parse-bisent/resnet18-5c106cde.pth": "5c106cde386e87d4033832f2996f5493238eda96ccf559d1d62760c4de0613f8",
}


def cycle_index(index: int, count: int) -> int:
    if count < 2 or index < 0:
        raise ValueError("invalid_cycle_input")
    phase = index % (2 * count - 2)
    return phase if phase < count else 2 * count - 2 - phase


def validate_render_probe(probe: dict, frame_count: int) -> None:
    videos = [stream for stream in probe["streams"] if stream["codec_type"] == "video"]
    audios = [stream for stream in probe["streams"] if stream["codec_type"] == "audio"]
    if len(videos) != 1 or len(audios) != 1:
        raise ValueError("render_stream_count_failed")
    video = videos[0]
    if (video["width"], video["height"], video["avg_frame_rate"]) != (720, 1280, "25/1"):
        raise ValueError("render_format_failed")
    if int(video["nb_frames"]) != frame_count:
        raise ValueError("render_frame_count_failed")
    if abs(float(probe["format"]["duration"]) - frame_count / 25) > 0.08:
        raise ValueError("render_duration_failed")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True, type=Path)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--audio", required=True, type=Path)
    parser.add_argument("--voice-manifest", required=True, type=Path)
    parser.add_argument("--license-review", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--proof-seconds", type=int, choices=[3, 6])
    args = parser.parse_args()
    if os.environ.get("HF_HUB_OFFLINE") != "1":
        raise ValueError("offline_execution_required")
    repo = args.repository.resolve()
    source, audio, output = args.source.resolve(), args.audio.resolve(), args.output.resolve()
    if output.exists():
        raise FileExistsError("output_already_exists")
    commit = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    if commit != MUSE_TALK_COMMIT:
        raise ValueError("source_commit_mismatch")
    if subprocess.check_output(["git", "-C", str(repo), "status", "--porcelain"], text=True).strip():
        raise ValueError("source_checkout_dirty")
    review = json.loads(args.license_review.read_text(encoding="utf-8"))
    if review.get("decision") != "approved_private_evaluation" or set(review["fileHashes"]) != set(MODEL_HASHES):
        raise ValueError("license_review_scope_missing")
    for relative, digest in MODEL_HASHES.items():
        if review["fileHashes"][relative] != digest or _sha256(repo / "models" / relative) != digest:
            raise ValueError(f"model_integrity_failed:{relative}")
    if _sha256(source) != SOURCE_SHA:
        raise ValueError("only_admitted_static_source_allowed")
    voice = json.loads(args.voice_manifest.read_text(encoding="utf-8"))
    if not voice.get("contentFitPassed") or not voice.get("consentGrantId"):
        raise ValueError("voice_gate_failed")
    if _sha256(audio) != voice["artifactChecksumSha256"]:
        raise ValueError("voice_integrity_failed")
    duration = float(_probe(audio)["format"]["duration"])
    if not 24 <= duration <= 45:
        raise ValueError("voice_duration_failed")
    output.parent.mkdir(parents=True, exist_ok=True)
    work = output.parent / "fixed-camera-cache-v1"
    work.mkdir(exist_ok=True)
    normalized = work / "base-25fps.mp4"
    if not normalized.exists():
        subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-i",
                str(source),
                "-an",
                "-vf",
                "fps=25",
                "-c:v",
                "libx264",
                "-crf",
                "16",
                str(normalized),
            ],
            check=True,
        )
    sys.path.insert(0, str(repo))
    os.chdir(repo)
    import cv2
    import numpy as np
    import torch
    from diffusers import AutoencoderKL, UNet2DConditionModel
    from musetalk.models.unet import PositionalEncoding
    from musetalk.utils.audio_processor import AudioProcessor
    from musetalk.utils.blending import get_image_blending, get_image_prepare_material
    from musetalk.utils.face_parsing import FaceParsing
    from musetalk.utils.face_parsing.model import BiSeNet
    from musetalk.utils.face_parsing.resnet import Resnet18

    class CompleteCheckpointFaceParsing(FaceParsing):
        def model_init(self):
            # The full BiSeNet checkpoint includes its ResNet backbone. Avoid
            # executing the obsolete legacy-tar ImageNet checkpoint altogether.
            initialize = Resnet18.init_weight
            Resnet18.init_weight = lambda *_args, **_kwargs: None
            try:
                net = BiSeNet(str(repo / "models/face-parse-bisent/resnet18-5c106cde.pth"))
            finally:
                Resnet18.init_weight = initialize
            net.load_state_dict(
                torch.load(repo / "models/face-parse-bisent/79999_iter.pth", weights_only=True, map_location="cpu"),
                strict=True,
            )
            return net.cuda().eval()
    from transformers import WhisperModel

    torch.set_num_threads(4)
    torch.manual_seed(240904)
    torch.cuda.reset_peak_memory_stats()
    started = time.perf_counter()
    nframes = math.floor(min(duration, args.proof_seconds or duration) * 25)
    cache_features = work / (voice["artifactChecksumSha256"] + ".features.pt")
    if cache_features.exists():
        features = torch.load(cache_features, map_location="cpu", weights_only=True)
    else:
        print("stage: audio_features", flush=True)
        whisper = (
            WhisperModel.from_pretrained(str(repo / "models/whisper"), torch_dtype=torch.float16, local_files_only=True)
            .cuda()
            .eval()
        )
        processor = AudioProcessor(str(repo / "models/whisper"))
        mel, length = processor.get_audio_feature(str(audio), weight_dtype=torch.float16)
        with torch.inference_mode():
            features = processor.get_whisper_chunk(mel, "cuda", torch.float16, whisper, length).cpu()
        torch.save(features, cache_features)
        del whisper, processor, mel
        gc.collect()
        torch.cuda.empty_cache()

    cap = cv2.VideoCapture(str(normalized))
    count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cache_latents, cache_masks = work / "latents.pt", work / "masks.npz"
    if not cache_latents.exists() or not cache_masks.exists():
        print("stage: prepare_single_visual_source", flush=True)
        vae = (
            AutoencoderKL.from_pretrained(str(repo / "models/sd-vae"), torch_dtype=torch.float16, local_files_only=True)
            .cuda()
            .eval()
        )
        fp = CompleteCheckpointFaceParsing()
        latents, masks, crop_boxes = [], [], []
        x1, y1, x2, y2 = ROI
        with torch.inference_mode():
            for index in range(count):
                ok, frame = cap.read()
                if not ok:
                    raise RuntimeError("source_decode_failed")
                crop = cv2.resize(frame[y1:y2, x1:x2], (256, 256), interpolation=cv2.INTER_LANCZOS4)
                image = torch.from_numpy(crop[:, :, ::-1].copy()).permute(2, 0, 1).unsqueeze(0).cuda().half() / 255
                masked = image.clone()
                masked[:, :, 128:] = 0
                scale = vae.config.scaling_factor
                pair = [vae.encode(item * 2 - 1).latent_dist.sample() * scale for item in (masked, image)]
                latents.append(torch.cat(pair, dim=1).cpu())
                mask, box = get_image_prepare_material(frame, ROI, fp=fp, mode="jaw")
                masks.append(mask)
                crop_boxes.append(box)
                if index % 25 == 0:
                    print(f"prepare: {index}/{count}", flush=True)
        torch.save(torch.cat(latents), cache_latents)
        np.savez_compressed(cache_masks, masks=np.stack(masks), boxes=np.array(crop_boxes))
        del fp, vae, latents, masks, image, masked, pair
        gc.collect()
        torch.cuda.empty_cache()
    latents = torch.load(cache_latents, map_location="cpu", weights_only=True)
    material = np.load(cache_masks, allow_pickle=False)
    masks, boxes = material["masks"], material["boxes"]
    print("stage: load_unet_fp16_streaming", flush=True)
    config = json.loads((repo / "models/musetalkV15/musetalk.json").read_text())
    original_dtype = torch.get_default_dtype()
    torch.set_default_dtype(torch.float16)
    try:
        with torch.device("cuda"):
            unet = UNet2DConditionModel(**config).eval()
    finally:
        torch.set_default_dtype(original_dtype)
    weights = torch.load(repo / "models/musetalkV15/unet.pth", mmap=True, weights_only=True, map_location="cpu")
    unet.load_state_dict(weights)
    del weights
    gc.collect()
    vae = (
        AutoencoderKL.from_pretrained(str(repo / "models/sd-vae"), torch_dtype=torch.float16, local_files_only=True)
        .cuda()
        .eval()
    )
    pe = PositionalEncoding().half().cuda()
    temporary = output.with_suffix(".silent.mp4")
    encoder = subprocess.Popen(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "bgr24",
            "-s",
            "720x1280",
            "-r",
            "25",
            "-i",
            "-",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            str(temporary),
        ],
        stdin=subprocess.PIPE,
    )
    x1, y1, x2, y2 = ROI
    try:
        with torch.inference_mode():
            for index in range(nframes):
                src = cycle_index(index, count)
                cap.set(cv2.CAP_PROP_POS_FRAMES, src)
                ok, frame = cap.read()
                if not ok:
                    raise RuntimeError("source_decode_failed")
                pred = unet(
                    latents[src : src + 1].cuda(),
                    torch.tensor([0], device="cuda"),
                    encoder_hidden_states=pe(features[index : index + 1].cuda()),
                ).sample
                face = (vae.decode(pred / vae.config.scaling_factor).sample / 2 + 0.5).clamp(0, 1)
                if not torch.isfinite(face).all():
                    raise RuntimeError("nonfinite_render")
                face = (face[0].permute(1, 2, 0).float().cpu().numpy() * 255).round().astype(np.uint8)[:, :, ::-1]
                face = cv2.resize(face, (x2 - x1, y2 - y1))
                blended = get_image_blending(frame, face, ROI, masks[src], boxes[src].tolist())
                encoder.stdin.write(np.ascontiguousarray(blended).tobytes())
                if index % 25 == 0:
                    print(f"render: {index}/{nframes}", flush=True)
    finally:
        cap.release()
        encoder.stdin.close()
        if encoder.wait(timeout=120):
            raise RuntimeError("encoder_failed")
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(temporary),
            "-i",
            str(audio),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-t",
            str(nframes / 25),
            "-metadata",
            "comment=Synthetic fictional presenter; authorized locally cloned voice; MuseTalk 1.5 private evaluation",
            "-movflags",
            "+faststart",
            str(output),
        ],
        check=True,
    )
    validate_render_probe(_probe(output), nframes)
    result = {
        "provider": "musetalk-v1.5-local",
        "adapter": "fixed-camera-roi-v1",
        "heygemModelCreated": False,
        "sourceVideoCount": 1,
        "sourceChecksumSha256": SOURCE_SHA,
        "audioChecksumSha256": voice["artifactChecksumSha256"],
        "modelHashes": MODEL_HASHES,
        "licenseReviewSha256": _sha256(args.license_review.resolve()),
        "sourceCommit": commit,
        "roi": list(ROI),
        "loop": "ping_pong_without_duplicate_endpoints",
        "dwposeUsed": False,
        "syncnetScored": False,
        "legacyResnetCheckpointLoaded": False,
        "sourcePreparationReused": True,
        "fps": 25,
        "frameCount": nframes,
        "durationSeconds": nframes / 25,
        "proofOnly": bool(args.proof_seconds),
        "publicationState": "private_review",
        "humanApproved": False,
        "checksumSha256": _sha256(output),
        "elapsedSeconds": round(time.perf_counter() - started, 2),
        "gpuPeakAllocatedBytes": torch.cuda.max_memory_allocated(),
    }
    _write_json(output.with_suffix(".result.json"), result)
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
