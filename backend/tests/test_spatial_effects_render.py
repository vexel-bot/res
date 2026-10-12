"""Authored spatial effects through real API/jobs and an independent Gaussian oracle."""
# ruff: noqa: F811
import hashlib
import json
import math
import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest
from test_contextual_editing import media as media
from test_contextual_editing import project as project
from test_remotion_native import native_direction

from app.database import SessionLocal
from app.domain.studios.motion_recipes import TemporalExposureV1
from app.models import CreativeDocument, LibraryAsset, StudioGenerationJob
from app.providers.studios.heavy_media_lease import _active, _read, lease_path
from app.providers.studios.video_render import VIDEO_RENDER_PROVIDERS
from app.services.object_storage import get_object_storage
from app.services.studios.compatibility import persist_contract, record_to_contract
from app.services.studios.jobs import execute_job_once

BOXES = {"sharp": (32, 32, 56, 48), "hard": (32, 112, 48, 48), "zero": (200, 112, 48, 48),
         "soft": (200, 32, 32, 48), "blur": (32, 220, 48, 48), "combo": (200, 220, 32, 48),
         "animated": (128, 112, 32, 48)}
SHADOWS = {"hard": {"x": 32, "y": 12, "blur": 0, "color": "#ff0000", "opacity": .5},
           "zero": {"x": 32, "y": 12, "blur": 0, "color": "#0000ff", "opacity": 0},
           "soft": {"x": 32, "y": 12, "blur": 4, "color": "#00ff00", "opacity": .5},
           "combo": {"x": 32, "y": 12, "blur": 4, "color": "#0000ff", "opacity": .5}}


def spatial_direction(variant):
    raw = native_direction().model_dump(mode="json", by_alias=True)
    scene = raw["scenes"][0]
    scene.update(id="spatial-effects", durationFrames=30, background="#000000", nativeComponents=[],
                 motionRecipes=[], elements=[])
    for target, (x, y, width, height) in BOXES.items():
        element = {"id": target, "kind": "shape", "purpose": "Canonical spatial effect witness", "x": x, "y": y,
                   "width": width, "height": height, "durationFrames": 30, "fill": "#ffffff", "radius": 0,
                   "visualRole": "hero" if target == "sharp" else "support"}
        if variant != "control":
            if target in SHADOWS:
                element["shadow"] = SHADOWS[target]
            if target in {"blur", "combo"}:
                element["depthTreatment"] = {"blurPx": 4}
            if target == "animated":
                element["animations"] = [{"property": "blur_px", "keyframes": [
                    {"frame": 0, "value": 0, "easing": "linear"}, {"frame": 1, "value": 16},
                    {"frame": 29, "value": 16}]}]
        scene["elements"].append(element)
    if variant == "exposure":
        scene["motionRecipes"] = [{"id": "expose-blur", "technique": "velocity_blur", "targetIds": ["animated"],
                                   "startFrame": 0, "endFrameExclusive": 30,
                                   "intent": "Expose the animated spatial blur",
                                   "continuityAnchor": "Same rectangle and authored blur track",
                                   "parameters": {"temporalSamples": 8, "shutterDegrees": 180,
                                                  "temporalExposure": TemporalExposureV1().model_dump(
                                                      mode="json", by_alias=True)},
                                   "verification": ["Spatial blur is sampled at the same canonical time"]}]
    return raw


def gaussian_pixel_axis(x, start, length, sigma):
    """Average convolution of a unit interval across [x,x+2], analytically."""
    if sigma == 0:
        return max(0, min(x + 2, start + length) - max(x, start)) / 2

    def primitive(value, edge):
        z = (value - edge) / sigma
        cdf = (1 + math.erf(z / math.sqrt(2))) / 2
        return (value - edge) * cdf + sigma * math.exp(-z * z / 2) / math.sqrt(2 * math.pi)

    return (primitive(x + 2, start) - primitive(x, start)
            - primitive(x + 2, start + length) + primitive(x, start + length)) / 2


def rectangle_alpha(target, x, y, sigma, offset=(0, 0)):
    left, top, width, height = BOXES[target]
    return gaussian_pixel_axis(x, left + offset[0], width, sigma) * gaussian_pixel_axis(
        y, top + offset[1], height, sigma)


def sample_frames(frame, variant, target):
    if variant != "exposure" or target != "animated" or frame >= 4:
        return [frame]
    low, high = max(0, frame - .25), min(30, frame + .25)
    return [low + (i + .5) * (high - low) / 8 for i in range(8)]


def sample_rgba(target, sample, x, y, variant):
    def point_alpha(sigma, offset=(0, 0)):
        left, top, width, height = BOXES[target]
        if sigma == 0:
            return float(left + offset[0] <= x < left + offset[0] + width
                         and top + offset[1] <= y < top + offset[1] + height)
        def axis(value, start, length):
            return (math.erf((value - start) / (sigma * math.sqrt(2)))
                    - math.erf((value - start - length) / (sigma * math.sqrt(2)))) / 2
        return axis(x, left + offset[0], width) * axis(y, top + offset[1], height)

    blur = 0 if variant == "control" else 4 if target in {"blur", "combo"} else (
        16 * min(max(sample, 0), 1) if target == "animated" else 0)
    alpha = point_alpha(blur)
    shadow = SHADOWS.get(target) if variant != "control" else None
    shadow_alpha, color = 0, [0, 0, 0]
    if shadow:
        shadow_alpha = shadow["opacity"] * point_alpha(math.hypot(blur, shadow["blur"]), (shadow["x"], shadow["y"]))
        color = [int(shadow["color"][i:i + 2], 16) for i in [1, 3, 5]]
    return [255 * alpha + c * shadow_alpha * (1 - alpha) for c in color], alpha + shadow_alpha * (1 - alpha)


def expected_rgb(frame, x, y, variant):
    # Original four-point Gauss-Legendre integration per axis across the 2x2 block.
    nodes = [.1388636884059474, .6600189564151437, 1.3399810435848563, 1.8611363115940526]
    weights = [.1739274225687269, .3260725774312731, .3260725774312731, .1739274225687269]
    times = sample_frames(frame, variant, "animated")
    rgb = [0., 0., 0.]
    for dx, wx in zip(nodes, weights, strict=True):
        for dy, wy in zip(nodes, weights, strict=True):
            for sample in times:
                pixel = [0., 0., 0.]
                for target in BOXES:
                    premultiplied, alpha = sample_rgba(target, sample, x + dx, y + dy, variant)
                    pixel = [a + b * (1 - alpha) for a, b in zip(premultiplied, pixel, strict=True)]
                for channel in range(3):
                    rgb[channel] += pixel[channel] * wx * wy / len(times)
    return rgb


PROBES = {"sharp": [(26, 54), (32, 54), (54, 54), (88, 54)],
          "hard": [(42, 132), (90, 148), (108, 162), (92, 172), (120, 148)],
          "zero": [(210, 132), (258, 148), (272, 162)],
          "soft": [(208, 54), (240, 68), (246, 88), (260, 68), (266, 68), (274, 68)],
          "blur": [(24, 242), (28, 242), (32, 242), (54, 242), (76, 242), (82, 242), (32, 216)],
          "combo": [(196, 242), (206, 242), (230, 246), (238, 252), (260, 252), (266, 252), (274, 252)],
          "animated": [(120, 134), (124, 134), (128, 134), (142, 134), (158, 134), (164, 134)]}
