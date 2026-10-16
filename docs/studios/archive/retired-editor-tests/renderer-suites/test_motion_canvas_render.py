"""Real local render qualification: data from the res scene compiler reaches Motion Canvas."""

from datetime import UTC, datetime
from pathlib import Path
import hashlib
import subprocess

from PIL import Image

import pytest

from app.domain.studios.contracts import CreativeDocumentV1, VideoRenderRequestV1
from app.domain.studios.motion import MotionTransitionV1, evaluate_motion_graph, project_motion_graph
from app.providers.studios.motion_canvas_projection import compile_motion_canvas_composition
from app.providers.studios.motion_canvas_render import MotionCanvasGraphicsProvider
from app.services.studios.scene_compiler import compile_scenes
from app.domain.studios.contextual_editing_v2 import ContextualPlanRequestV2
from test_editorial_motion_v2 import editorial_direction


def _compiled():
    now = datetime.now(UTC)
    document = CreativeDocumentV1(
        document_id="motion-canvas-test", workspace_id="workspace-test", title="Render proof",
        content_type="video", correlation_id="test", brand_memory_ref={"id": "brand", "revision": 1},
        brief={"objective": "Explicar distribuição", "audience": "Público"},
        composition={"pages": [{"id": "page", "width": 480, "height": 320}]},
        created_at=now, updated_at=now,
    )
    direction = ContextualPlanRequestV2(
        expected_document_revision=1, intent={"objective": "Explicar distribuição"},
        scenes=[{"id": "scene", "purpose": "Apresentar", "durationFrames": 30,
                 "verification": ["A palavra fica legível"],
                 "elements": [{"id": "title", "kind": "text", "purpose": "Nomear o tema",
                               "text": "Distribuição", "width": 300, "height": 80,
                               "durationFrames": 30, "animations": [{"property": "position_x",
                                 "keyframes": [{"frame": 0, "value": -60}, {"frame": 15, "value": 0}]}]}]}],
    )
    draft, graph, _, _ = compile_scenes(document, direction, "user", "plan")
    evaluation = evaluate_motion_graph(draft, graph)
    assert evaluation.eligible_for_reviewed_projection
    projection = project_motion_graph(graph, "motion_canvas", evaluation)
    return draft, projection


def test_motion_canvas_compiler_blocks_unimplemented_transition():
    doc, projection = _compiled()
    projection.transitions.append(MotionTransitionV1.model_validate({
        "transitionId": "wipe", "kind": "wipe", "reducedMotionKind": "hard_cut",
        "fromLayerId": "title", "toLayerId": "other", "startFrame": 0,
        "endFrameExclusive": 10, "motivation": "test",
    }))
    with pytest.raises(ValueError, match="unsupported_transition"):
        compile_motion_canvas_composition(doc, projection, {})


def test_motion_canvas_produces_real_mp4_from_compiled_document(tmp_path):
    worker = Path(__file__).resolve().parents[2] / "workers" / "motion-canvas-local"
    if not (worker / "node_modules" / "@motion-canvas" / "core").exists():
        pytest.skip("isolated Motion Canvas worker not installed")
    doc, projection = _compiled()
    page = doc.composition.pages[0]
    timeline = doc.composition.media_timeline
    request = VideoRenderRequestV1(
        workspace_id=doc.workspace_id, document_id=doc.document_id,
        document_revision=doc.revision, document_version=doc.version,
        page_ids=[page.id], asset_ids=[], correlation_id="motion-canvas-test",
        output={"width": page.width, "height": page.height,
                "fps": timeline.frame_rate.numerator / timeline.frame_rate.denominator,
                "audioCodec": "none"},
    )
    output = tmp_path / "motion.mp4"
    result = MotionCanvasGraphicsProvider("node", "ffmpeg", 120, worker).render(
        doc, request, {}, output, lambda _: None, lambda: False,
        motion_projection=projection, automatic_draft=True,
    )
    assert output.is_file() and output.stat().st_size > 1000
    assert result.frames_rendered == 30
    assert result.renderer_checks["motionCanvasReceipt"]["result"] == 0
    assert len(result.renderer_checks["motionCanvasReceipt"]["frames"]) == 30


def test_canonical_format_transformation_reaches_motion_canvas(tmp_path):
    """A real V2 composition must compile; simple shape fixtures are insufficient."""
    image_path = tmp_path / "content.png"
    Image.new("RGB", (180, 120), "#dd8844").save(image_path)
    checksum = hashlib.sha256(image_path.read_bytes()).hexdigest()
    now = datetime.now(UTC)
    document = CreativeDocumentV1(
        document_id="motion-canvas-canonical", workspace_id="workspace-test", title="Canonical proof",
        content_type="video", correlation_id="test", brand_memory_ref={"id": "brand", "revision": 1},
        brief={"objective": "Demonstrar adaptação", "audience": "Público"},
        composition={"pages": [{"id": "page", "width": 360, "height": 640}]},
        assets=[{"id": "asset-photo", "mediaType": "image/png", "checksum": checksum, "rightsStatus": "verified"}],
        created_at=now, updated_at=now,
    )
    direction = editorial_direction()
    draft, graph, _, _ = compile_scenes(document, direction, "user", "plan")
    evaluation = evaluate_motion_graph(draft, graph)
    assert evaluation.eligible_for_reviewed_projection
    projection = project_motion_graph(graph, "motion_canvas", evaluation)
    manifest = compile_motion_canvas_composition(
        draft, projection,
        {"asset-photo": {"path": str(image_path), "sha256": checksum, "mime": "image/png"}},
    )
    images = [layer for layer in manifest["layers"] if layer["kind"] == "image"]
    assert len(images) == 2
    assert all(layer["properties"]["objectFit"] == "contain" for layer in images)
    assert all(layer["properties"]["naturalWidth"] == 180 for layer in images)
    worker = Path(__file__).resolve().parents[2] / "workers" / "motion-canvas-local"
    if not (worker / "node_modules" / "@motion-canvas" / "core").exists():
        return
    page = draft.composition.pages[0]
    timeline = draft.composition.media_timeline
    request = VideoRenderRequestV1(
        workspace_id=draft.workspace_id, document_id=draft.document_id,
        document_revision=draft.revision, document_version=draft.version,
        page_ids=[page.id], asset_ids=["asset-photo"], correlation_id="canonical-proof",
        output={"width": page.width, "height": page.height,
                "fps": timeline.frame_rate.numerator / timeline.frame_rate.denominator,
                "audioCodec": "none"},
    )
    output = tmp_path / "canonical.mp4"
    result = MotionCanvasGraphicsProvider("node", "ffmpeg", 120, worker).render(
        draft, request,
        {"asset-photo": image_path},
        output, lambda _: None, lambda: False,
        motion_projection=projection, automatic_draft=True,
    )
    assert output.is_file() and result.frames_rendered == 30
    for label, timestamp in (("initial", "0.1"), ("final", "0.9")):
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-ss", timestamp, "-i", str(output),
             "-frames:v", "1", str(tmp_path / f"{label}.png")],
            check=True, timeout=30,
        )
    observations = []
    for label in ("initial", "final"):
        image = Image.open(tmp_path / f"{label}.png").convert("RGB")
        orange = [(x, y) for y in range(image.height) for x in range(image.width)
                  if (lambda rgb: rgb[0] > 175 and 95 < rgb[1] < 185 and rgb[2] < 120)(image.getpixel((x, y)))]
        white = sum(1 for rgb in image.getdata() if min(rgb) > 220)
        assert orange and white > 500  # persistent material and headline are visible in both states
        observations.append(max(x for x, _ in orange) - min(x for x, _ in orange))
    assert observations[0] - observations[1] > 30  # the viewport composition really changed
