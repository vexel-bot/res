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
