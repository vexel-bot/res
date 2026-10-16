"""Native runtime contracts and real frame-level trim/speed qualification."""

import hashlib
import subprocess
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.domain.studios.contextual_editing import digest
from app.domain.studios.contextual_editing_v2 import ContextualPlanRequestV2
from app.domain.studios.contracts import CreativeDocumentV1, VideoRenderRequestV1
from app.domain.studios.motion import evaluate_motion_graph, project_motion_graph
from app.services.studios.scene_compiler import compile_scenes


def native_direction(asset=None, rate=1):
    element = dict(
        id="hero",
        kind="video" if asset else "text",
        purpose="Visible action",
        width=320,
        height=320,
        durationFrames=15,
        **(
            {"assetId": asset, "sourceStartSeconds": 1, "playbackRate": rate, "sourceAudio": "mute"}
            if asset
            else {"text": "Aurora"}
        ),
    )
    return ContextualPlanRequestV2.model_validate(
        {
            "expectedDocumentRevision": 1,
            "intent": {"objective": "Demonstrate native composition"},
            "scenes": [
                {
                    "id": "action",
                    "purpose": "Demonstrate",
                    "durationFrames": 15,
                    "verification": ["Action stays visible"],
                    "elements": [element],
                    "nativeComponents": [
                        {
                            "component": "action_montage" if asset else "integrated_typography",
                            "version": 1,
                            "targetIds": ["hero"],
                            "entranceFrames": 4,
                        }
                    ],
                }
            ],
        }
    )


def native_document(direction, assets=None):
    now = datetime.now(UTC)
    doc = CreativeDocumentV1(
        document_id="native-test",
        workspace_id="workspace",
        title="Native test",
        content_type="video",
        correlation_id="test",
        brand_memory_ref={"id": "brand", "revision": 1},
        brief={"objective": "Native proof", "audience": "Reviewers"},
        assets=assets or [],
        composition={"pages": [{"id": "page", "width": 320, "height": 320, "safeArea": 0}]},
        created_at=now,
        updated_at=now,
    )
    draft, graph, _, _ = compile_scenes(doc, direction, "user", "plan")
    evaluation = evaluate_motion_graph(draft, graph)
    assert evaluation.eligible_for_reviewed_projection
    return draft, project_motion_graph(graph, "remotion", evaluation)




def test_unknown_component_and_unbound_speed_rejected():
    value = native_direction().model_dump(mode="json", by_alias=True)
    value["scenes"][0]["nativeComponents"][0]["component"] = "execute_javascript"
    with pytest.raises(ValidationError):
        ContextualPlanRequestV2.model_validate(value)
    value = native_direction("footage", 2).model_dump(mode="json", by_alias=True)
    value["scenes"][0]["nativeComponents"] = []
    with pytest.raises(ValidationError):
        ContextualPlanRequestV2.model_validate(value)
