"""An impossible canonical word fails the actual renderer without an output."""

import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

import pytest
from test_remotion_native import native_document
from test_typography_units import typography_direction

from app.domain.studios.contextual_editing_v2 import ContextualPlanRequestV2
from app.domain.studios.contracts import AssetReferenceV1, VideoRenderRequestV1
from app.domain.studios.motion import PROPERTY_UNITS, MotionTrackV1, evaluate_motion_graph, project_motion_graph
from app.providers.studios.heavy_media_lease import _active, _read, lease_path
from app.services.studios.scene_compiler import compile_scenes


@pytest.fixture(autouse=True)
def clean_database():
    yield
