"""Real canonical exposure fixtures; measured pixels are separate from human scores."""

# ruff: noqa: F811
import hashlib
import json
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


def exposure_direction(samples, shutter=180, policy=None):
    raw = native_direction().model_dump(mode="json", by_alias=True)
    scenes = []
    for index, (background, foreground, y) in enumerate(
        [
            ("#142850", "#dcb446", 40),
            ("#501428", "#28c8dc", 100),
        ]
    ):
        scene = {
            "id": "exposure-" + str(index),
            "purpose": "Original temporal exposure and cut fixture",
            "durationFrames": 30,
            "background": background,
            "entrance": "cut",
            "verification": ["Same authored motion, color and opacity in every sample variant"],
            "elements": [
                {
                    "id": "moving",
                    "kind": "shape",
                    "purpose": "Moving semi-transparent color",
                    "x": 20,
                    "y": y,
                    "width": 64,
                    "height": 64,
                    "fill": foreground,
                    "radius": 0,
                    "durationFrames": 30,
                    "depthTreatment": {"opacity": 0.5},
                    "visualRole": "hero",
                },
                {
                    "id": "still",
                    "kind": "shape",
                    "purpose": "Stationary color and alpha witness",
                    "x": 20,
                    "y": 200,
                    "width": 80,
                    "height": 40,
                    "fill": foreground,
                    "radius": 0,
                    "durationFrames": 30,
                    "depthTreatment": {"opacity": 0.5},
                    "visualRole": "support",
                },
            ],
            "motionRecipes": [
                {
                    "id": "move",
                    "version": 1,
                    "technique": "motion_choreography",
                    "targetIds": ["moving"],
                    "startFrame": 0,
                    "endFrameExclusive": 30,
                    "intent": "Move and hold the same shape",
                    "continuityAnchor": "Authored color and opacity",
                    "parameters": {
                        "tracks": [
                            {
                                "targetId": "moving",
                                "property": "x",
                                "keyframes": [
                                    {"frame": 0, "value": 0, "curve": [0, 0, 1, 1]},
                                    {"frame": 8, "value": 150},
                                    {"frame": 29, "value": 150},
                                ],
                            }
                        ]
                    },
                    "verification": ["Hold remains sharp"],
                }
            ],
        }
        if samples:
            parameters = {"temporalSamples": samples, "shutterDegrees": shutter}
            if policy:
                parameters["temporalExposure"] = policy
            scene["motionRecipes"].append(
                {
                    "id": "exposure",
                    "version": 1,
                    "technique": "velocity_blur",
                    "targetIds": ["moving", "still"],
                    "startFrame": 0,
                    "endFrameExclusive": 30,
                    "intent": "Temporal exposure with inspectable parameters",
                    "continuityAnchor": "Same graphic, no footage or synthetic replacement",
                    "parameters": parameters,
                    "verification": ["Inspect moving edges, paused color and the cut"],
                }
            )
        scenes.append(scene)
    raw["scenes"] = scenes
    return raw
