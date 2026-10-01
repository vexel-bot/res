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
from app.providers.studios.contextual_render import ContextualFFmpegProvider
from app.services.object_storage import get_object_storage
from app.services.studios.compatibility import persist_contract, record_to_contract


def local_font():
    options = [Path("C:/Windows/Fonts/georgia.ttf"), Path("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf")]
    path = next((p for p in options if p.exists()), None)
    if not path:
        pytest.skip("A real TTF font is required")
    return path


@pytest.mark.parametrize("dimensions", [(320, 320), (360, 640), (640, 360)])
def test_missing_font_and_svg_material_resolve_to_real_mp4(client, project, monkeypatch, tmp_path, dimensions):
    with SessionLocal() as db:
        record = db.get(CreativeDocument, project["document"])
        document = record_to_contract(record)
        document.composition.pages[0].width, document.composition.pages[0].height = dimensions
        persist_contract(record, document)
        db.commit()
    font = local_font()
    downloads = []
    monkeypatch.setattr(
        "app.services.studios.editing_fonts.lookup_fonts",
        lambda family: [
            {
                "family": family,
                "version": "fixture-v1",
                "files": {"regular": "https://fonts.gstatic.com/fixture.ttf"},
            }
        ],
    )

    def download(url, destination, hosts):
        downloads.append(url)
        shutil.copyfile(font, destination)
        return url

    monkeypatch.setattr("app.services.studios.editing_resources.download_resource", download)
    logo = upload(
        client,
        project,
        data=(
            b'<svg xmlns="http://www.w3.org/2000/svg" width="80" height="40">'
            b'<rect x="20" width="40" height="40" fill="red"/></svg>'
        ),
    )
    assert logo.status_code == 200, logo.text
    plan = create_plan(
        client,
        project,
        beats=[{"id": "beat", "clipId": "clip", "purpose": "Identificar a marca", "onScreenText": "Ação e precisão"}],
        materialNeeds=[need(), need(id="type", kind="font", role="font", query="Fixture Serif")],
    )
    assert plan["status"] == "ready", plan["blockers"]
    assert len(downloads) == 1
    doc = CreativeDocumentV1.model_validate(plan["draftDocument"])
    output = tmp_path / "directed.mp4"
    with SessionLocal() as db, ExitStack() as stack:
        files = {}
        for ref in doc.assets:
            asset = db.get(LibraryAsset, ref.id)
            files[ref.id] = stack.enter_context(
                get_object_storage(asset.storage_backend).materialize(asset.storage_key)
            )
        receipt = ContextualFFmpegProvider("ffmpeg", 60).render(
            doc, request(doc), files, output, lambda _: None, lambda: False
        )
    assert output.stat().st_size > 1000
    assert receipt.frames_rendered == 50
    from PIL import Image

    frame = tmp_path / "preview.png"
    ffmpeg("-ss", "0.8", "-i", output, "-frames:v", "1", frame)
    image = Image.open(frame).convert("RGB")
    red_pixels = [
        (x, y)
        for y in range(image.height)
        for x in range(image.width)
        if image.getpixel((x, y))[0] > 180 and image.getpixel((x, y))[2] < 70
    ]
    assert red_pixels, "SVG shape must appear in the export"
    assert min(y for x, y in red_pixels) >= doc.composition.pages[0].safe_area - 1
    artifact_root = os.environ.get("RES_EDITING_VALIDATION_OUTPUT")
    if artifact_root:
        target = Path(artifact_root) / f"materials-{dimensions[0]}x{dimensions[1]}"
        target.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(output, target / "video.mp4")
        shutil.copyfile(frame, target / "preview.png")
        (target / "evidence.json").write_text(
            json.dumps(
                {
                    "sourceKind": "synthetic technical fixture",
                    "fontDiscovery": "stubbed official API contract",
                    "fontBytes": "real local TTF",
                    "externalGenerativeCalls": 0,
                    "humanReview": "pending",
                    "plan": plan,
                    "framesRendered": receipt.frames_rendered,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )


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
