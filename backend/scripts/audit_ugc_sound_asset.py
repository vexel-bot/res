"""Create a fail-closed speech/music preflight report for one UGC sound asset.

WebRTC VAD and a pinned local YAMNet ONNX export are preflight signals, not
proof. Natural transients can resemble voice or instruments, so every positive
detection remains inconclusive and human listening stays mandatory. This
script never approves production by itself.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
import webrtcvad

SAMPLE_RATE = 16_000
FRAME_MILLISECONDS = 30
FRAME_BYTES = SAMPLE_RATE * FRAME_MILLISECONDS // 1_000 * 2
DETECTOR_ID = "webrtcvad-wheels/2.0.14:mode3:zero-frame-policy"
YAMNET_MODEL_SHA256 = "1bee379e01b759465c09a646160263fcea5ced95b779820aa832c0f72abdb165"
YAMNET_DATA_SHA256 = "aa05b5b196bdfd74fb59ae4cbba22578c5ab25b9e792e52867678844bcecc839"
YAMNET_CLASS_MAP_SHA256 = "cdf24d193e196d9e95912a2667051ae203e92a2ba09449218ccb40ef787c6df2"
YAMNET_DETECTOR_ID = (
    "anchor-flux/yamnet-onnx@d8b2365b3cdaa367185a620305bd93683d8e3840"
)
YAMNET_SCORE_THRESHOLD = 0.35

# AudioSet's CSV is flat, so these conservative families are explicit. Voice
# includes speech, singing and other human vocalisations. Music spans the Music
# parent and its instrument/genre children in the canonical YAMNet class map.
VOICE_CLASS_INDICES = frozenset(range(0, 46)) | frozenset({61, 63, 64, 65, 66, 213})
MUSIC_CLASS_INDICES = frozenset(range(132, 277))

STFT_WINDOW_SAMPLES = 400
STFT_HOP_SAMPLES = 160
FFT_LENGTH = 512
MEL_BANDS = 64
MEL_MIN_HZ = 125.0
MEL_MAX_HZ = 7_500.0
LOG_OFFSET = 0.001
PATCH_FRAMES = 96
PATCH_HOP_FRAMES = 48


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def probe_duration(path: Path, ffprobe: str) -> float:
    completed = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=codec_type:format=duration",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    payload = json.loads(completed.stdout)
    if not payload.get("streams") or payload["streams"][0].get("codec_type") != "audio":
        raise ValueError("ugc_sound_audio_stream_required")
    return float(payload["format"]["duration"])


def decode_pcm(path: Path, ffmpeg: str) -> bytes:
    completed = subprocess.run(
        [
            ffmpeg,
            "-v",
            "error",
            "-xerror",
            "-i",
            str(path),
            "-ac",
            "1",
            "-ar",
            str(SAMPLE_RATE),
            "-f",
            "s16le",
            "pipe:1",
        ],
        capture_output=True,
        check=True,
        timeout=60,
    )
    return completed.stdout


def analyze_speech(pcm: bytes) -> dict[str, int | float | str]:
    detector = webrtcvad.Vad(3)
    frames = [
        pcm[offset : offset + FRAME_BYTES]
        for offset in range(0, len(pcm) - FRAME_BYTES + 1, FRAME_BYTES)
    ]
    if not frames:
        raise ValueError("ugc_sound_too_short_for_speech_preflight")
    speech_frames = sum(detector.is_speech(frame, SAMPLE_RATE) for frame in frames)
    ratio = speech_frames / len(frames)
    return {
        "frameMilliseconds": FRAME_MILLISECONDS,
        "framesAnalyzed": len(frames),
        "speechFrames": speech_frames,
        "speechFrameRatio": round(ratio, 8),
        # Any positive detection stays inconclusive because transient foley can
        # trigger VAD. Zero detections are a preflight pass, not final approval.
        "speechDetectionStatus": "pass" if speech_frames == 0 else "inconclusive",
    }


def _frame(data: np.ndarray, window_length: int, hop_length: int) -> np.ndarray:
    if data.shape[0] < window_length:
        raise ValueError("ugc_sound_too_short_for_acoustic_preflight")
    frame_count = 1 + (data.shape[0] - window_length) // hop_length
    shape = (frame_count, window_length) + data.shape[1:]
    strides = (data.strides[0] * hop_length,) + data.strides
    return np.lib.stride_tricks.as_strided(data, shape=shape, strides=strides)


def _hertz_to_mel(frequencies_hertz: np.ndarray | float) -> np.ndarray:
    return 1_127.0 * np.log(1.0 + (np.asarray(frequencies_hertz) / 700.0))


def _mel_weight_matrix() -> np.ndarray:
    spectrogram_bins_hertz = np.linspace(0.0, SAMPLE_RATE / 2, FFT_LENGTH // 2 + 1)
    spectrogram_bins_mel = _hertz_to_mel(spectrogram_bins_hertz)
    band_edges_mel = np.linspace(
        _hertz_to_mel(MEL_MIN_HZ),
        _hertz_to_mel(MEL_MAX_HZ),
        MEL_BANDS + 2,
    )
    weights = np.empty((FFT_LENGTH // 2 + 1, MEL_BANDS), dtype=np.float32)
    for index in range(MEL_BANDS):
        lower_edge, center, upper_edge = band_edges_mel[index : index + 3]
        lower_slope = (spectrogram_bins_mel - lower_edge) / (center - lower_edge)
        upper_slope = (upper_edge - spectrogram_bins_mel) / (upper_edge - center)
        weights[:, index] = np.maximum(0.0, np.minimum(lower_slope, upper_slope))
    weights[0, :] = 0.0
    return weights


def waveform_to_yamnet_patches(pcm: bytes) -> np.ndarray:
    waveform = np.frombuffer(pcm, dtype="<i2").astype(np.float32) / 32_768.0
    minimum_samples = int((0.96 + 0.025 - 0.010) * SAMPLE_RATE)
    target_samples = max(waveform.shape[0], minimum_samples)
    after_first_patch = target_samples - minimum_samples
    patch_hop_samples = int(0.48 * SAMPLE_RATE)
    target_samples = minimum_samples + math.ceil(after_first_patch / patch_hop_samples) * patch_hop_samples
    if waveform.shape[0] < target_samples:
        waveform = np.pad(waveform, (0, target_samples - waveform.shape[0]))

    frames = _frame(waveform, STFT_WINDOW_SAMPLES, STFT_HOP_SAMPLES)
    periodic_hann = 0.5 - 0.5 * np.cos(
        2 * np.pi * np.arange(STFT_WINDOW_SAMPLES) / STFT_WINDOW_SAMPLES
    )
    magnitude = np.abs(np.fft.rfft(frames * periodic_hann, n=FFT_LENGTH)).astype(np.float32)
    log_mel = np.log(magnitude @ _mel_weight_matrix() + LOG_OFFSET).astype(np.float32)
    return np.asarray(
        _frame(log_mel, PATCH_FRAMES, PATCH_HOP_FRAMES),
        dtype=np.float32,
    )


def _load_class_names(class_map_path: Path) -> list[str]:
    with class_map_path.open("r", encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    if len(rows) != 521 or [int(row["index"]) for row in rows] != list(range(521)):
        raise ValueError("yamnet_class_map_invalid")
    return [row["display_name"] for row in rows]


def _family_summary(
    scores: np.ndarray,
    class_names: list[str],
    indices: frozenset[int],
) -> dict[str, Any]:
    family_scores = scores[:, sorted(indices)]
    patch_index, family_index = np.unravel_index(
        int(np.argmax(family_scores)),
        family_scores.shape,
    )
    class_index = sorted(indices)[family_index]
    maximum = float(family_scores[patch_index, family_index])
    return {
        "maximumScore": round(maximum, 8),
        "maximumClassIndex": class_index,
        "maximumClassName": class_names[class_index],
        "maximumPatchIndex": int(patch_index),
        "status": "pass" if maximum < YAMNET_SCORE_THRESHOLD else "inconclusive",
    }


def analyze_acoustic_events(
    pcm: bytes,
    model_path: Path,
    class_map_path: Path,
) -> dict[str, Any]:
    try:
        import onnxruntime as ort
    except ImportError as error:  # pragma: no cover - deployment guard
        raise RuntimeError("onnxruntime_required_for_acoustic_preflight") from error

    model_path = model_path.resolve(strict=True)
    data_path = model_path.with_name("model.data")
    class_map_path = class_map_path.resolve(strict=True)
    if sha256_file(model_path) != YAMNET_MODEL_SHA256:
        raise ValueError("yamnet_model_checksum_mismatch")
    if not data_path.exists() or sha256_file(data_path) != YAMNET_DATA_SHA256:
        raise ValueError("yamnet_external_data_checksum_mismatch")
    if sha256_file(class_map_path) != YAMNET_CLASS_MAP_SHA256:
        raise ValueError("yamnet_class_map_checksum_mismatch")

    class_names = _load_class_names(class_map_path)
    patches = waveform_to_yamnet_patches(pcm)
    session = ort.InferenceSession(
        str(model_path),
        providers=["CPUExecutionProvider"],
    )
    raw_scores = np.vstack([
        session.run(
            ["class_scores"],
            {"audio": patch[np.newaxis, np.newaxis, :, :]},
        )[0]
        for patch in patches
    ])
    # This third-party ONNX export exposes the pre-sigmoid logits even though
    # its output is named class_scores. Convert them to the probabilities used
    # by canonical YAMNet before applying the conservative threshold.
    scores = 1.0 / (1.0 + np.exp(-np.clip(raw_scores, -80.0, 80.0)))
    maxima = scores.max(axis=0)
    top_indices = np.argsort(maxima)[-8:][::-1]
    return {
        "detector": YAMNET_DETECTOR_ID,
        "scoreTransform": "sigmoid(raw_logits)",
        "scoreThreshold": YAMNET_SCORE_THRESHOLD,
        "patchesAnalyzed": int(scores.shape[0]),
        "voice": _family_summary(scores, class_names, VOICE_CLASS_INDICES),
        "music": _family_summary(scores, class_names, MUSIC_CLASS_INDICES),
        "topEvents": [
            {
                "classIndex": int(index),
                "className": class_names[index],
                "maximumScore": round(float(maxima[index]), 8),
            }
            for index in top_indices
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset", type=Path, required=True)
    parser.add_argument("--cue-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--yamnet-model", type=Path)
    parser.add_argument("--yamnet-class-map", type=Path)
    args = parser.parse_args()

    asset = args.asset.resolve(strict=True)
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        raise RuntimeError("ffmpeg_and_ffprobe_required")
    duration = probe_duration(asset, ffprobe)
    pcm = decode_pcm(asset, ffmpeg)
    speech = analyze_speech(pcm)
    acoustic = None
    if args.yamnet_model or args.yamnet_class_map:
        if not args.yamnet_model or not args.yamnet_class_map:
            raise ValueError("yamnet_model_and_class_map_required_together")
        acoustic = analyze_acoustic_events(pcm, args.yamnet_model, args.yamnet_class_map)

    voice_status = acoustic["voice"]["status"] if acoustic else "inconclusive"
    music_status = acoustic["music"]["status"] if acoustic else "inconclusive"
    speech_status = (
        "pass"
        if speech["speechDetectionStatus"] == "pass" and voice_status == "pass"
        else "inconclusive"
    )
    blocking_reasons = ["human_listening_review_pending"]
    if acoustic is None:
        blocking_reasons.append("dedicated_acoustic_classifier_missing")
    if speech_status != "pass":
        blocking_reasons.append("voice_activity_requires_human_review")
    if music_status != "pass":
        blocking_reasons.append("music_activity_requires_human_review")
    report = {
        "schemaVersion": "studio.ugc-sound-preflight.v1",
        "cueId": args.cue_id,
        "assetPath": args.asset.as_posix(),
        "assetChecksumSha256": sha256_file(asset),
        "assetSizeBytes": asset.stat().st_size,
        "durationSeconds": duration,
        "speechDetector": DETECTOR_ID,
        **speech,
        "acousticClassifier": acoustic,
        "speechDetectionStatus": speech_status,
        "musicDetectionStatus": music_status,
        "humanListeningStatus": "pending",
        "productionReady": False,
        "blockingReasons": blocking_reasons,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
