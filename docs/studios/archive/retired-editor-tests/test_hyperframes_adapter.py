import os
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.config import Settings
from app.domain.studios.contracts import (
    CreativeDocumentV1,
    CreativeLayerV1,
    VideoRenderRequestV1,
    VideoRenderSpecV1,
)
from app.domain.studios.motion import (
    MotionGraphV1,
    project_motion_graph,
    validate_motion_graph_bindings,
)
from app.providers.studios.hyperframes_projection import project_creative_document
from app.providers.studios.video_render import HyperFramesCliVideoRenderProvider


def render_fixture() -> tuple[CreativeDocumentV1, VideoRenderRequestV1]:
    now = datetime.now(UTC)
    document = CreativeDocumentV1.model_validate(
        {
            "documentId": "hyperframes-adapter-smoke",
            "workspaceId": "workspace-smoke",
            "title": "HyperFrames adapter",
            "contentType": "video",
            "revision": 1,
            "version": 1,
            "correlationId": "hyperframes-smoke-001",
            "brandMemoryRef": {"id": "brand-smoke", "revision": 1},
            "brief": {
                "objective": "Validar render isolado",
                "audience": "Equipe Clicko",
                "hook": "Rosto entra, anúncio sai.",
            },
            "composition": {
                "pages": [
                    {
                        "id": "scene-1",
                        "role": "hook",
                        "width": 360,
                        "height": 640,
                        "durationMs": 1000,
                        "background": "#10181c",
                        "layers": [
                            {
                                "id": "headline",
                                "kind": "text",
                                "name": "Headline",
                                "x": 24,
                                "y": 180,
                                "width": 312,
                                "height": 180,
                                "zIndex": 2,
                                "properties": {
                                    "text": "Rosto <script>alert(1)</script> anúncio",
                                    "fontSize": 38,
                                    "color": "#ffffff",
                                    "textAlign": "center",
                                },
                            }
                        ],
                    }
                ],
                "mediaTimeline": {
                    "durationFrames": 30,
                    "frameRate": {"numerator": 30, "denominator": 1},
                    "tracks": [
                        {
                            "id": "captions",
                            "kind": "caption",
                            "locale": "pt-BR",
                            "cues": [
                                {
                                    "id": "caption-1",
                                    "timeline": {"startFrame": 0, "durationFrames": 30},
                                    "text": "Olá <b>Clicko</b>",
                                    "style": {"color": "#ffffff"},
                                }
                            ],
                        }
                    ],
                },
            },
            "assets": [],
            "createdAt": now,
            "updatedAt": now,
        }
    )
    request = VideoRenderRequestV1(
        workspace_id=document.workspace_id,
        document_id=document.document_id,
        document_revision=1,
        document_version=1,
        page_ids=["scene-1"],
        output=VideoRenderSpecV1(
            format="mp4",
            width=360,
            height=640,
            fps=30,
            video_codec="h264",
            audio_codec="aac",
            quality="draft",
        ),
        correlation_id="hyperframes-smoke-001",
    )
    return document, request


def test_hyperframes_projection_is_offline_typed_and_escapes_content():
    document, request = render_fixture()
    projected, warnings = project_creative_document(document, request, {})
    assert warnings == []
    assert "connect-src 'none'" in projected
    assert 'data-fps="30"' in projected
    assert 'data-duration="1.000000000"' in projected
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in projected
    assert "Olá &lt;b&gt;Clicko&lt;/b&gt;" in projected
    assert "https://" not in projected and "http://" not in projected
    assert "overflow-wrap:normal" in projected
    assert "word-break:normal" in projected
    assert "hyphens:none" in projected
    assert "overflow-wrap:break-word" not in projected


def test_hyperframes_projection_accepts_canonical_canvas_layer_properties():
    document, request = render_fixture()
    page = document.composition.pages[0].model_copy(
        update={
            "layers": [
                CreativeLayerV1(
                    id="canonical-copy",
                    kind="text",
                    name="Canonical copy",
                    x=20,
                    y=40,
                    width=320,
                    height=120,
                    properties={
                        "text": "Distribuição",
                        "fontSize": 44,
                        "fontWeight": "bold",
                        "align": "right",
                        "color": "#ffffff",
                    },
                ),
                CreativeLayerV1(
                    id="canonical-signal",
                    kind="shape",
                    name="Canonical signal",
                    x=130,
                    y=260,
                    width=100,
                    height=100,
                    properties={"shape": "ellipse", "fill": "#6c5ce7", "radius": 50},
                ),
            ]
        }
    )
    canonical = document.model_copy(
        update={"composition": document.composition.model_copy(update={"pages": [page]})}
    )

    projected, warnings = project_creative_document(canonical, request, {})

    assert warnings == []
    assert "font-weight:700" in projected
    assert "text-align:right" in projected
    assert "border-radius:50%" in projected


def motion_graph(document: CreativeDocumentV1, *, status: str = "reviewed") -> MotionGraphV1:
    timeline = document.composition.media_timeline
    assert timeline is not None
    page = document.composition.pages[0]
    return MotionGraphV1.model_validate(
        {
            "graphId": "hyperframes-motion-1",
            "workspaceId": document.workspace_id,
            "documentId": document.document_id,
            "documentRevision": document.revision,
            "frameRate": timeline.frame_rate.model_dump(by_alias=True),
            "durationFrames": timeline.duration_frames,
            "canvasWidth": page.width,
            "canvasHeight": page.height,
            "status": status,
            "tracks": [
                {
                    "trackId": "headline-x",
                    "targetLayerId": "headline",
                    "property": "position_x",
                    "unit": "pixels",
                    "keyframes": [
                        {"frame": 0, "value": -120, "easing": "ease_out"},
                        {"frame": 12, "value": 0, "easing": "linear"},
                    ],
                },
                {
                    "trackId": "headline-opacity",
                    "targetLayerId": "headline",
                    "property": "opacity",
                    "unit": "ratio",
                    "keyframes": [
                        {"frame": 0, "value": 0, "easing": "ease_in_out"},
                        {"frame": 8, "value": 1, "easing": "hold"},
                    ],
                },
            ],
            "createdBy": "clicko.human-motion",
            "createdAt": datetime(2026, 8, 26, 19, 0, tzinfo=UTC),
        }
    )


def test_reviewed_motion_projection_is_embedded_as_seekable_offline_runtime():
    document, request = render_fixture()
    projection = project_motion_graph(motion_graph(document), "hyperframes")

    projected, warnings = project_creative_document(document, request, {}, projection)
    repeated, repeated_warnings = project_creative_document(document, request, {}, projection)

    assert projected == repeated
    assert warnings == repeated_warnings == []
    assert 'id="clicko-motion-spec"' in projected
    assert 'data-clicko-motion-layer="headline"' in projected
    assert '"propertyPath":"transform.translateX"' in projected
    assert '"propertyPath":"style.opacity"' in projected
    assert "window.__clickoMotionApply(t)" in projected
    assert "connect-src 'none'" in projected
    assert "https://" not in projected and "http://" not in projected


def test_hyperframes_rejects_unreviewed_motion_projection():
    document, request = render_fixture()
    projection = project_motion_graph(motion_graph(document, status="suggested"), "hyperframes")

    with pytest.raises(ValueError, match="requires_review"):
        project_creative_document(document, request, {}, projection)


def test_rich_motion_projects_hierarchy_typography_transition_audio_and_reduced_motion():
    document, request = render_fixture()
    page = document.composition.pages[0].model_copy(
        update={
            "layers": [
                CreativeLayerV1(
                    id="panel",
                    kind="shape",
                    name="Panel",
                    x=20,
                    y=130,
                    width=320,
                    height=300,
                    properties={"shape": "rectangle", "fill": "#4c7dff", "radius": 24},
                ),
                document.composition.pages[0].layers[0],
                CreativeLayerV1(
                    id="signal",
                    kind="shape",
                    name="Signal",
                    x=130,
                    y=470,
                    width=100,
                    height=100,
                    properties={"shape": "ellipse", "fill": "#ffffff"},
                ),
            ]
        }
    )
    rich_document = document.model_copy(
        update={"composition": document.composition.model_copy(update={"pages": [page]})}
    )
    graph = MotionGraphV1.model_validate(
        {
            "graphId": "rich-motion-golden",
            "workspaceId": document.workspace_id,
            "documentId": document.document_id,
            "documentRevision": document.revision,
            "frameRate": {"numerator": 30, "denominator": 1},
            "durationFrames": 30,
            "canvasWidth": 360,
            "canvasHeight": 640,
            "status": "reviewed",
            "nodes": [
                {"nodeId": "node-panel", "targetLayerId": "panel"},
                {
                    "nodeId": "node-headline",
                    "targetLayerId": "headline",
                    "parentNodeId": "node-panel",
                    "transformOriginX": 0,
                    "transformOriginY": 0.5,
                },
                {"nodeId": "node-signal", "targetLayerId": "signal"},
            ],
            "tracks": [
                {
                    "trackId": "panel-x",
                    "targetLayerId": "panel",
                    "property": "position_x",
                    "unit": "pixels",
                    "keyframes": [
                        {"frame": 0, "value": -80, "easing": "ease_out"},
                        {"frame": 12, "value": 0},
                    ],
                },
                {
                    "trackId": "headline-size",
                    "targetLayerId": "headline",
                    "property": "font_size_px",
                    "unit": "pixels",
                    "keyframes": [
                        {"frame": 0, "value": 24, "easing": "ease_out"},
                        {"frame": 12, "value": 38},
                    ],
                },
                {
                    "trackId": "headline-spacing",
                    "targetLayerId": "headline",
                    "property": "letter_spacing_px",
                    "unit": "pixels",
                    "keyframes": [
                        {"frame": 0, "value": 8},
                        {"frame": 12, "value": 0},
                    ],
                },
                {
                    "trackId": "signal-opacity",
                    "targetLayerId": "signal",
                    "property": "opacity",
                    "unit": "ratio",
                    "keyframes": [
                        {"frame": 0, "value": 0},
                        {"frame": 20, "value": 1},
                    ],
                },
            ],
            "transitions": [
                {
                    "transitionId": "panel-to-signal",
                    "kind": "semantic_morph",
                    "reducedMotionKind": "hard_cut",
                    "fromLayerId": "panel",
                    "toLayerId": "signal",
                    "startFrame": 15,
                    "endFrameExclusive": 24,
                    "motivation": "A explicação condensada se torna o sinal final.",
                }
            ],
            "audioEvents": [
                {
                    "eventId": "semantic-impact",
                    "frame": 15,
                    "role": "silence",
                    "eventBinding": "Silêncio intencional marca a transformação sem asset externo.",
                    "rightsStatus": "not_applicable",
                }
            ],
            "createdBy": "clicko.motion-golden",
            "createdAt": datetime(2026, 9, 1, 12, 0, tzinfo=UTC),
        }
    )
    validate_motion_graph_bindings(rich_document, graph)
    normal = project_motion_graph(graph, "hyperframes")
    reduced = project_motion_graph(graph, "hyperframes", reduced_motion=True)
    projected, warnings = project_creative_document(rich_document, request, {}, normal)

    assert warnings == []
    assert normal.reduced_motion is False and reduced.reduced_motion is True
    assert reduced.transitions[0].kind == "hard_cut"
    assert reduced.tracks[0].keyframes[0].frame == 0
    assert len(reduced.tracks[0].keyframes) == 1
    assert reduced.tracks[0].keyframes[0].value == 0
    assert len(reduced.tracks[1].keyframes) == 2
    assert '"parentNodeId":"node-panel"' in projected
    assert '"propertyPath":"typography.fontSizePx"' in projected
    assert "__clickoMotionAudioEventsAt" in projected
    assert "transitionState" in projected


def test_hyperframes_activation_requires_isolated_queue_and_cli():
    with pytest.raises(RuntimeError, match="STUDIO_ISOLATED_QUEUES_ENABLED"):
        Settings(
            hyperframes_enabled=True,
            studio_isolated_queues_enabled=False,
            hyperframes_local_qualification_enabled=False,
            hyperframes_cli_path="hyperframes.mjs",
        ).validate_for_startup()
    with pytest.raises(RuntimeError, match="HYPERFRAMES_CLI_PATH"):
        Settings(
            hyperframes_enabled=True,
            studio_isolated_queues_enabled=True,
            hyperframes_cli_path=None,
        ).validate_for_startup()


def test_hyperframes_process_is_cooperatively_cancelled(tmp_path):
    script = Path(tmp_path) / "slow-cli.mjs"
    script.write_text("setTimeout(() => process.exit(0), 10000);", encoding="utf-8")
    provider = HyperFramesCliVideoRenderProvider("node", str(script), 30)
    started = time.monotonic()
    with pytest.raises(InterruptedError, match="video_render_cancelled"):
        provider._run([], Path(tmp_path), lambda: time.monotonic() - started > 0.5, started)


@pytest.mark.skipif(
    not os.environ.get("CLICKO_HYPERFRAMES_SMOKE_CLI"),
    reason="Set CLICKO_HYPERFRAMES_SMOKE_CLI to run the pinned local adapter smoke",
)
def test_hyperframes_cli_adapter_real_smoke(tmp_path):
    document, request = render_fixture()
    provider = HyperFramesCliVideoRenderProvider(
        os.environ.get("CLICKO_HYPERFRAMES_NODE", "node"),
        os.environ["CLICKO_HYPERFRAMES_SMOKE_CLI"],
        300,
    )
    output = Path(tmp_path) / "hyperframes-adapter.mp4"
    progress: list[int] = []
    result = provider.render(document, request, {}, output, progress.append, lambda: False)
    assert provider.version == "0.8.31"
    assert output.stat().st_size > 0
    assert result.provider == "hyperframes.cli"
    assert result.width == 360 and result.height == 640
    assert result.video_codec == "h264"
    assert result.frames_rendered == 30
    assert progress == [12, 24, 84]


@pytest.mark.skipif(
    not os.environ.get("CLICKO_HYPERFRAMES_SMOKE_CLI"),
    reason="Set CLICKO_HYPERFRAMES_SMOKE_CLI to run the contextual motion smoke",
)
def test_hyperframes_contextual_motion_real_smoke(tmp_path):
    from test_scene_compiler_v2 import direction, document

    from app.domain.studios.contextual_editing_v2 import ContextualPlanRequestV2
    from app.providers.studios.visual_state_observation import observe_visual_states
    from app.services.studios.scene_compiler import compile_scenes

    raw = direction(
        visualRole="hero",
        motionCues=[
            {
                "kind": "emphasis",
                "profile": "emphasis",
                "startFrame": 0,
                "durationFrames": 18,
                "rationale": "Estabelecer o foco",
            }
        ],
    ).model_dump(mode="json", by_alias=True)
    raw["intent"]["script"] = "Distribuição conecta IDEIA e pessoas."
    raw["scenes"][0]["durationFrames"] = 60
    raw["scenes"][0]["elements"][0]["durationFrames"] = 60
    raw["scenes"][0]["narration"] = raw["intent"]["script"]
    raw["scenes"][0]["elements"].insert(
        0,
        {
            "id": "depth",
            "kind": "shape",
            "purpose": "Separar o plano de fundo",
            "durationFrames": 60,
            "width": 540,
            "height": 540,
            "x": 50,
            "y": 50,
            "shape": "ellipse",
            "fill": "#245c6f",
            "visualRole": "background",
            "depthTreatment": {"opacity": 0.55, "blurPx": 3, "parallax": 0.3},
        },
    )
    raw["scenes"][0]["elements"][1]["effects"] = [
        {"id": "contrast", "kind": "contrast", "amount": 1.1},
        {
            "id": "contact-shadow",
            "kind": "drop_shadow",
            "amount": 4,
            "x": 0,
            "y": 3,
            "color": "#000000",
            "opacity": 0.3,
        },
    ]
    raw["scenes"][0]["cameraCues"] = [
        {
            "mode": "push_in",
            "targetId": "title",
            "startFrame": 0,
            "durationFrames": 60,
            "intensity": 0.08,
            "rationale": "Aproximar o foco principal",
        }
    ]
    raw["scenes"][0]["keywordCues"] = [
        {
            "id": "idea",
            "text": "IDEIA",
            "sourceExcerpt": "IDEIA",
            "purpose": "Marcar o conceito",
            "startFrame": 20,
            "durationFrames": 30,
            "profile": "emphasis",
        }
    ]
    editorial_direction = ContextualPlanRequestV2.model_validate(raw)
    draft, graph, _, _ = compile_scenes(document(), editorial_direction, "user", "plan")
    projection = project_motion_graph(graph, "hyperframes")
    request = VideoRenderRequestV1(
        workspace_id=draft.workspace_id,
        document_id=draft.document_id,
        document_revision=draft.revision,
        document_version=draft.version,
        page_ids=[draft.composition.pages[0].id],
        output=VideoRenderSpecV1(width=640, height=640, fps=30, audio_codec="none", quality="draft"),
        correlation_id="contextual-motion-smoke",
    )
    provider = HyperFramesCliVideoRenderProvider(
        os.environ.get("CLICKO_HYPERFRAMES_NODE", "node"),
        os.environ["CLICKO_HYPERFRAMES_SMOKE_CLI"],
        300,
    )
    output = Path(tmp_path) / "contextual-motion.mp4"
    result = provider.render(
        draft,
        request,
        {},
        output,
        lambda _: None,
        lambda: False,
        motion_projection=projection,
        automatic_draft=True,
    )
    audit = observe_visual_states(output, editorial_direction, graph)

    assert result.frames_rendered == 60
    assert audit["motion"]["cameraTrackIds"]
    assert audit["motion"]["overshootTrackIds"]
    assert audit["actionVerification"]["evidence"]
def test_typed_text_spans_are_escaped_and_preserve_word_reveal():
    from app.providers.studios.hyperframes_projection import _text_content

    content = _text_content(
        "Uma <IDEIA> clara",
        [
            {
                "id": "idea",
                "start": 4,
                "end": 11,
                "color": "#ff4d6d",
                "fontWeight": 800,
            }
        ],
        True,
    )

    assert "<IDEIA>" not in content
    assert "&lt;IDEIA&gt;" in content
    assert 'data-res-text-span="idea"' in content
    assert content.count("data-res-word") == 3


def test_text_span_expands_to_complete_words_and_keeps_normal_wrap_points():
    from app.providers.studios.hyperframes_projection import _text_content

    content = _text_content(
        "A mensagem encontra pessoas",
        [{"id": "message", "start": 4, "end": 8, "color": "#ff4d6d"}],
        False,
    )

    assert ">mensagem<" in content
    assert ">mens<" not in content
    assert content.count('data-res-text-span="message"') == 1
    assert "display:inline-block" in content
