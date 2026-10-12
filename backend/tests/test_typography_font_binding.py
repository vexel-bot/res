from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest
from test_remotion_native import native_document
from test_typography_units import typography_direction

from app.domain.studios.contracts import AssetReferenceV1, VideoRenderRequestV1
from app.providers.studios.video_render import VIDEO_RENDER_PROVIDERS
from app.services.studios.scene_compiler import compile_scenes


@pytest.fixture(autouse=True)
def clean_database():
    yield
