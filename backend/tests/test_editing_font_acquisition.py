"""Font discovery is stubbed; acquired bytes and FFmpeg output are real local files."""

# ruff: noqa: F401, F811
import json
import os
import shutil
from contextlib import ExitStack
from pathlib import Path

import pytest
from test_contextual_editing import create_plan, ffmpeg, media, project, request
from test_editing_material_director import need
from test_editing_resources import headers, upload

from app.database import SessionLocal
from app.domain.studios.contracts import CreativeDocumentV1
from app.models import CreativeDocument, LibraryAsset
from app.services.object_storage import get_object_storage
from app.services.studios.compatibility import persist_contract, record_to_contract


def local_font():
    options = [Path("C:/Windows/Fonts/georgia.ttf"), Path("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf")]
    path = next((p for p in options if p.exists()), None)
    if not path:
        pytest.skip("A real TTF font is required")
    return path




def test_requested_font_variant_is_not_replaced(client, project, monkeypatch):
    monkeypatch.setattr(
        "app.services.studios.editing_fonts.lookup_fonts",
        lambda family: [
            {
                "family": family,
                "version": "v1",
                "files": {"regular": "https://fonts.gstatic.com/regular.ttf"},
            }
        ],
    )
    monkeypatch.setattr(
        "app.services.studios.editing_resources.download_resource",
        lambda *args: (_ for _ in ()).throw(AssertionError("A different variant cannot be downloaded")),
    )
    plan = create_plan(
        client, project, materialNeeds=[need(kind="font", role="font", query="Fixture", fontVariant="700")]
    )
    assert plan["status"] == "awaiting_choice"
    assert plan["materialRequests"][0]["fontVariant"] == "700"
