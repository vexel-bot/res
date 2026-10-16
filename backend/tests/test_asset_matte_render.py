"""Original PNG matte through canonical API/job/MP4, with independent pixel oracle."""

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
from PIL import Image, ImageDraw
from test_asset_matte import matte_direction
from test_contextual_editing import media as media
from test_contextual_editing import project as project

from app.database import SessionLocal
from app.models import CreativeDocument, LibraryAsset, StudioGenerationJob
from app.providers.studios.heavy_media_lease import _active, _read, lease_path
from app.providers.studios.video_render import VIDEO_RENDER_PROVIDERS
from app.services.object_storage import get_object_storage
from app.services.studios.compatibility import persist_contract, record_to_contract
from app.services.studios.jobs import execute_job_once
