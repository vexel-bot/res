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
from app.providers.studios.remotion_projection import compile_remotion_composition
from app.providers.studios.remotion_render import RemotionNativeGraphicsProvider
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


def test_native_parameters_are_persisted_and_invalidate_digest():
    direction = native_direction()
    first, projection = native_document(direction)
    assert first.composition.narrative["editorialV2"]["renderer"] == "remotion.contextual-v2"
    first_manifest = compile_remotion_composition(first, projection, {})
    direction.scenes[0].native_components[0].entrance_frames = 8
    second, second_projection = native_document(direction)
    assert digest(first.composition) != digest(second.composition)
    assert (
        first_manifest["nativeCompositionDigest"]
        != compile_remotion_composition(second, second_projection, {})["nativeCompositionDigest"]
    )


def test_unknown_component_and_unbound_speed_rejected():
    value = native_direction().model_dump(mode="json", by_alias=True)
    value["scenes"][0]["nativeComponents"][0]["component"] = "execute_javascript"
    with pytest.raises(ValidationError):
        ContextualPlanRequestV2.model_validate(value)
    value = native_direction("footage", 2).model_dump(mode="json", by_alias=True)
    value["scenes"][0]["nativeComponents"] = []
    with pytest.raises(ValidationError):
        ContextualPlanRequestV2.model_validate(value)


@pytest.mark.parametrize("source_fps", [24, 60])
def test_native_video_trim_speed_and_observed_geometry(tmp_path, source_fps):
    # A 1s red / 1s green / 1s blue source. Trim at 1s, play 2x for 0.5s: green only.
    source = tmp_path / "source.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=red:s=320x320:r={source_fps}:d=1",
            "-f",
            "lavfi",
            "-i",
            f"color=green:s=320x320:r={source_fps}:d=1",
            "-f",
            "lavfi",
            "-i",
            f"color=blue:s=320x320:r={source_fps}:d=1",
            "-filter_complex",
            "[0:v][1:v][2:v]concat=n=3:v=1:a=0[v]",
            "-map",
            "[v]",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(source),
        ],
        check=True,
    )
    checksum = hashlib.sha256(source.read_bytes()).hexdigest()
    doc, projection = native_document(
        native_direction("footage", 2),
        [{"id": "footage", "mediaType": "video/mp4", "checksum": checksum, "rightsStatus": "verified"}],
    )
    request = VideoRenderRequestV1(
        workspace_id=doc.workspace_id,
        document_id=doc.document_id,
        document_revision=doc.revision,
        document_version=doc.version,
        page_ids=["page"],
        asset_ids=["footage"],
        correlation_id="native-test",
        output={"width": 320, "height": 320, "fps": 30, "audioCodec": "none"},
    )
    output = tmp_path / "native.mp4"
    result = RemotionNativeGraphicsProvider("node", "ffmpeg", 180).render(
        doc,
        request,
        {"footage": source},
        output,
        lambda _: None,
        lambda: False,
        motion_projection=projection,
        automatic_draft=True,
    )
    assert result.frames_rendered == 15
    assert len(result.renderer_checks["geometrySamples"]) == 15
    pixels = subprocess.check_output(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(output),
            "-vf",
            "crop=2:2:160:160",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-",
        ]
    )
    for offset in range(0, len(pixels), 12):
        red, green, blue = pixels[offset : offset + 3]
        assert green > red + 50 and green > blue + 50


def test_native_missing_checksum_and_cancellation(tmp_path):
    doc, projection = native_document(
        native_direction("missing"),
        [{"id": "missing", "mediaType": "video/mp4", "checksum": "a" * 64, "rightsStatus": "verified"}],
    )
    with pytest.raises(ValueError, match="asset_missing"):
        compile_remotion_composition(doc, projection, {})
    with pytest.raises(ValueError, match="checksum_conflict"):
        compile_remotion_composition(doc, projection, {"missing": {"sha256": "b" * 64}})
