"""Deterministic local calibration checks; these are not aesthetic or model grades."""
from __future__ import annotations

import hashlib
import wave
from pathlib import Path

import numpy as np
from PIL import Image

from .craft_flash import inspect_transition_flash

GEOMETRY_TOLERANCE_PX = 2
VISUAL_TOLERANCE_FRAMES = 1
AUDIO_TOLERANCE_SECONDS = .05


def color_bounds(image: Image.Image, rgb: tuple[int, int, int], tolerance=8):
    """Bounds of a known fixture marker in decoded pixels, not general object detection."""
    data = np.asarray(image.convert("RGBA")).astype(np.int16)
    match = (np.abs(data[:, :, :3] - np.array(rgb)).max(axis=2) <= tolerance) & (data[:, :, 3] > 128)
    y, x = np.nonzero(match)
    return None if not len(x) else [int(x.min()), int(y.min()), int(x.max()) + 1, int(y.max()) + 1]


def inspect_marker(image, rgb, expected_bounds, *, tolerance=GEOMETRY_TOLERANCE_PX):
    actual = color_bounds(image, rgb)
    error = None if actual is None else max(abs(a - b) for a, b in zip(actual, expected_bounds))
    return {"status": "pass" if error is not None and error <= tolerance else "defect",
            "observedBounds": actual, "expectedBounds": list(expected_bounds),
            "maximumErrorPixels": error, "tolerancePixels": tolerance,
            "interpretation": "Known marker geometry only; not movement taste or semantic recognition."}


def inspect_text_ink(image, *, margin=10):
    """A supplied text-only RGBA render can expose clipping; no OCR or reading claim."""
    alpha = image.convert("RGBA").getchannel("A")
    bounds = alpha.getbbox()
    safe = bounds is not None and min(bounds[0], bounds[1], image.width - bounds[2], image.height - bounds[3]) >= margin
    return {"status": "pass" if safe else "defect", "inkBounds": bounds,
            "previewWidth": image.width, "minimumMarginPixels": margin,
            "interpretation": "Clipping of known text-only ink, not OCR, reading comfort or hierarchy approval."}


def inspect_occlusion(image, *, front_point, front_color, transparent_point=None):
    rgba = image.convert("RGBA")
    observed = rgba.getpixel(tuple(front_point))
    front_ok = max(abs(a - b) for a, b in zip(observed[:3], front_color)) <= 2 and observed[3] == 255
    alpha = rgba.getpixel(tuple(transparent_point))[3] if transparent_point is not None else None
    return {"status": "pass" if front_ok and (alpha is None or alpha == 0) else "defect",
            "frontPixel": list(observed), "backgroundAlpha": alpha,
            "interpretation": "Known overlap and alpha sample, not automatic person segmentation or contact-shadow assessment."}


def inspect_flash(frames, fps, *, intentional=False):
    result = inspect_transition_flash(frames, fps)
    detected = bool(result["events"])
    return {**result, "signalStatus": result["status"],
            "status": "defect" if detected and not intentional else "pass" if result["status"] != "inconclusive" else "inconclusive",
            "intentional": intentional,
            "interpretation": "Intent comes from the fixture contract. Detection is not a universal prohibition on bright transitions."}


def inspect_audio(path: Path | None, *, required=True, expected_onset=None, tolerance=AUDIO_TOLERANCE_SECONDS):
    present = path is not None and path.is_file()
    first = None
    peak = 0.0
    if present:
        with wave.open(str(path), "rb") as wav:
            if wav.getsampwidth() != 2:
                raise ValueError("quality_fixture_requires_pcm16")
            samples = np.frombuffer(wav.readframes(wav.getnframes()), dtype="<i2").reshape(-1, wav.getnchannels())
            amplitude = np.max(np.abs(samples.astype(np.float64)) / 32768, axis=1)
            peak = float(amplitude.max(initial=0))
            active = np.flatnonzero(amplitude >= .05)
            first = float(active[0] / wav.getframerate()) if len(active) else None
    error = abs(first - expected_onset) if first is not None and expected_onset is not None else None
    passed = (not required or first is not None) and (expected_onset is None or error is not None and error <= tolerance)
    return {"status": "pass" if passed else "defect", "filePresent": present, "peak": peak,
            "firstOnsetSeconds": first, "expectedOnsetSeconds": expected_onset,
            "onsetErrorSeconds": error, "toleranceSeconds": tolerance,
            "interpretation": "PCM signal check; no perceptual listening, intelligibility or final-mix approval."}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def score_controls(cases):
    """Report denominator and errors for fixture classifiers, never for AI editorial skill."""
    positives = [c for c in cases if c["expectedDefect"]]
    negatives = [c for c in cases if not c["expectedDefect"]]
    detected = lambda c: c["observed"]["status"] == "defect"
    missed = [c["id"] for c in positives if not detected(c)]
    false_positives = [c["id"] for c in negatives if detected(c)]
    inconclusive = [c["id"] for c in cases if c["observed"]["status"] == "inconclusive"]
    return {"status": "pass" if not missed and not false_positives and not inconclusive else "fail",
            "positiveControls": len(positives), "negativeControls": len(negatives),
            "detectedDefects": len(positives) - len(missed), "missedDefects": missed,
            "falsePositiveCount": len(false_positives), "falsePositives": false_positives,
            "inconclusive": inconclusive,
            "interpretation": "Calibration on known local fixtures, not model evaluation or population accuracy."}
