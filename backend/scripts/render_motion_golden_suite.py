from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from app.domain.studios.contracts import (
    CreativeDocumentV1,
    VideoRenderRequestV1,
    VideoRenderSpecV1,
)
from app.domain.studios.creative_autonomy import VideoFamilyV1
from app.domain.studios.motion import (
    MotionGraphProjectionV1,
    MotionGraphV1,
    motion_graph_digest,
    motion_projection_digest,
    project_motion_graph,
    validate_motion_graph_bindings,
)
from app.domain.studios.motion_benchmark import (
    MotionGoldenCaseEvidenceV1,
    MotionGoldenRenderV1,
    MotionGoldenSuiteEvidenceV1,
)
from app.providers.studios.video_render import HyperFramesCliVideoRenderProvider

FAMILIES: list[tuple[VideoFamilyV1, str, str, str]] = [
    ("presenter_ugc", "F1 · Ritmo do gesto", "#6C5CE7", "dissolve"),
    ("split_screen_proof", "F2 · Prova em foco", "#00A8FF", "wipe"),
    ("motion_visual_essay", "F3 · Ideia em movimento", "#4C7DFF", "semantic_morph"),
    ("cinematic_hybrid", "F4 · Estado e transformação", "#FF7A45", "match_transform"),
]
CHECKPOINTS = [0, 8, 16, 29]
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def sha256_file(path: Path) -> str:
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def build_case(
    family: VideoFamilyV1,
    title: str,
    accent: str,
    transition_kind: str,
) -> tuple[CreativeDocumentV1, VideoRenderRequestV1, MotionGraphV1]:
    now = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)
    case_id = f"motion-golden-{family.replace('_', '-')}"
    document = CreativeDocumentV1.model_validate(
        {
            "documentId": case_id,
            "workspaceId": "motion-golden-workspace",
            "title": title,
            "contentType": "video",
            "revision": 1,
            "version": 1,
            "correlationId": case_id,
            "brandMemoryRef": {"id": "motion-golden-brand", "revision": 1},
            "brief": {
                "objective": "Validar motion determinístico, tipografia e hierarquia.",
                "audience": "Equipe Clicko",
                "hook": title,
            },
            "composition": {
                "pages": [
                    {
                        "id": "scene-main",
                        "role": "motion-golden",
                        "width": 360,
                        "height": 640,
                        "durationMs": 1000,
                        "background": "#0B0D10",
                        "layers": [
                            {
                                "id": "panel",
                                "kind": "shape",
                                "name": "Painel pai",
                                "x": 24,
                                "y": 140,
                                "width": 312,
                                "height": 260,
                                "zIndex": 1,
                                "properties": {
                                    "shape": "rectangle",
                                    "fill": accent,
                                    "radius": 28,
                                },
                            },
                            {
                                "id": "headline",
                                "kind": "text",
                                "name": "Headline filha",
                                "x": 48,
                                "y": 186,
                                "width": 264,
                                "height": 170,
                                "zIndex": 2,
                                "properties": {
                                    "text": title,
                                    "fontSize": 34,
                                    "fontWeight": 700,
                                    "lineHeight": 1.05,
                                    "color": "#FFFFFF",
                                    "align": "center",
                                },
                            },
                            {
                                "id": "signal",
                                "kind": "shape",
                                "name": "Sinal de payoff",
                                "x": 130,
                                "y": 474,
                                "width": 100,
                                "height": 100,
                                "zIndex": 3,
                                "properties": {
                                    "shape": "ellipse",
                                    "fill": "#FFFFFF",
                                },
                            },
                        ],
                    }
                ],
                "narrative": {
                    "mode": "motion-golden",
                    "family": family,
                    "publicationAuthorized": False,
                },
                "mediaTimeline": {
                    "durationFrames": 30,
                    "frameRate": {"numerator": 30, "denominator": 1},
                    "tracks": [],
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
        document_revision=document.revision,
        document_version=document.version,
        page_ids=["scene-main"],
        asset_ids=[],
        output=VideoRenderSpecV1(
            format="mp4",
            width=360,
            height=640,
            fps=30,
            video_codec="h264",
            audio_codec="aac",
            quality="draft",
        ),
        correlation_id=case_id,
    )
    graph = MotionGraphV1.model_validate(
        {
            "graphId": f"graph-{case_id}",
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
                        {"frame": 0, "value": -96, "easing": "ease_out"},
                        {"frame": 12, "value": 0},
                    ],
                },
                {
                    "trackId": "panel-scale",
                    "targetLayerId": "panel",
                    "property": "scale_x",
                    "unit": "ratio",
                    "keyframes": [
                        {"frame": 0, "value": 0.86, "easing": "ease_out"},
                        {"frame": 12, "value": 1},
                    ],
                },
                {
                    "trackId": "headline-size",
                    "targetLayerId": "headline",
                    "property": "font_size_px",
                    "unit": "pixels",
                    "keyframes": [
                        {"frame": 0, "value": 24, "easing": "ease_out"},
                        {"frame": 12, "value": 34},
                    ],
                },
                {
                    "trackId": "headline-spacing",
                    "targetLayerId": "headline",
                    "property": "letter_spacing_px",
                    "unit": "pixels",
                    "keyframes": [
                        {"frame": 0, "value": 9, "easing": "ease_out"},
                        {"frame": 12, "value": 0},
                    ],
                },
                {
                    "trackId": "headline-leading",
                    "targetLayerId": "headline",
                    "property": "line_height_ratio",
                    "unit": "ratio",
                    "keyframes": [
                        {"frame": 0, "value": 1.25},
                        {"frame": 12, "value": 1.05},
                    ],
                },
                {
                    "trackId": "headline-weight",
                    "targetLayerId": "headline",
                    "property": "font_weight",
                    "unit": "number",
                    "keyframes": [
                        {"frame": 0, "value": 400},
                        {"frame": 12, "value": 700},
                    ],
                },
                {
                    "trackId": "signal-opacity",
                    "targetLayerId": "signal",
                    "property": "opacity",
                    "unit": "ratio",
                    "keyframes": [
                        {"frame": 0, "value": 0},
                        {"frame": 24, "value": 1},
                    ],
                },
                {
                    "trackId": "signal-rotation",
                    "targetLayerId": "signal",
                    "property": "rotation_degrees",
                    "unit": "degrees",
                    "keyframes": [
                        {"frame": 0, "value": -90, "easing": "ease_in_out"},
                        {"frame": 24, "value": 0},
                    ],
                },
            ],
            "transitions": [
                {
                    "transitionId": "panel-to-signal",
                    "kind": transition_kind,
                    "reducedMotionKind": "hard_cut",
                    "fromLayerId": "panel",
                    "toLayerId": "signal",
                    "startFrame": 16,
                    "endFrameExclusive": 25,
                    "motivation": "A tese se condensa no sinal de payoff.",
                }
            ],
            "audioEvents": [
                {
                    "eventId": "payoff-silence",
                    "frame": 16,
                    "role": "silence",
                    "eventBinding": "Silêncio intencional no início da transição.",
                    "rightsStatus": "not_applicable",
                }
            ],
            "createdBy": "clicko.motion-golden",
            "createdAt": now,
        }
    )
    validate_motion_graph_bindings(document, graph)
    return document, request, graph


def extract_checkpoints(video: Path, directory: Path) -> dict[int, str]:
    result: dict[int, str] = {}
    directory.mkdir(parents=True, exist_ok=True)
    for frame in CHECKPOINTS:
        destination = directory / f"frame-{frame:03d}.png"
        completed = subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(video),
                "-vf",
                f"select=eq(n\\,{frame})",
                "-frames:v",
                "1",
                str(destination),
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(f"motion_checkpoint_failed:{frame}:{completed.stderr[-1000:]}")
        result[frame] = sha256_file(destination)
    return result


def render_variant(
    provider: HyperFramesCliVideoRenderProvider,
    document: CreativeDocumentV1,
    request: VideoRenderRequestV1,
    projection: MotionGraphProjectionV1,
    destination: Path,
) -> tuple[MotionGoldenRenderV1, object]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    result = provider.render(
        document,
        request,
        {},
        destination,
        lambda _value: None,
        lambda: False,
        motion_projection=projection,
    )
    checkpoints = extract_checkpoints(destination, destination.parent / f"{destination.stem}-frames")
    render = MotionGoldenRenderV1(
        mode="reduced_motion" if projection.reduced_motion else "normal",
        projection_digest_sha256=motion_projection_digest(projection),
        artifact_path=destination.as_posix(),
        artifact_digest_sha256=sha256_file(destination),
        width=result.width,
        height=result.height,
        frame_rate=result.fps,
        duration_milliseconds=result.duration_ms,
        checkpoint_frame_digests=checkpoints,
        technical_qc_passed=(
            result.width == request.output.width
            and result.height == request.output.height
            and abs(result.fps - request.output.fps) < 0.001
            and abs(result.duration_ms - 1000) <= 67
            and result.frames_rendered == 30
        ),
    )
    return render, result


def main() -> int:
    parser = argparse.ArgumentParser(description="Render the four-family Clicko motion golden suite.")
    parser.add_argument(
        "--cli",
        type=Path,
        default=Path(
            "C:/Users/edugu/Downloads/clicko-oss-evaluation/"
            "hyperframes/packages/cli/bin/hyperframes.mjs"
        ),
    )
    parser.add_argument("--node", default="node")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/validation/video-creative-pilot/motion-goldens-20260901-v1"),
    )
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()
    if not args.cli.is_file():
        raise SystemExit("hyperframes_cli_required")
    output_dir = args.output_dir.resolve()
    provider = HyperFramesCliVideoRenderProvider(args.node, str(args.cli.resolve()), 300)
    cases: list[MotionGoldenCaseEvidenceV1] = []
    suite_blockers: list[str] = []
    for family, title, accent, transition_kind in FAMILIES:
        document, request, graph = build_case(family, title, accent, transition_kind)
        normal_projection = project_motion_graph(graph, "hyperframes")
        reduced_projection = project_motion_graph(graph, "hyperframes", reduced_motion=True)
        case_dir = output_dir / family
        normal, _ = render_variant(
            provider,
            document,
            request,
            normal_projection,
            case_dir / "normal.mp4",
        )
        reduced, _ = render_variant(
            provider,
            document,
            request,
            reduced_projection,
            case_dir / "reduced-motion.mp4",
        )
        with tempfile.TemporaryDirectory(prefix=f"clicko-motion-repeat-{family}-") as temporary:
            repeat_path = Path(temporary) / "normal-repeat.mp4"
            repeated, _ = render_variant(
                provider,
                document,
                request,
                normal_projection,
                repeat_path,
            )
        blockers: list[str] = []
        if not normal.technical_qc_passed:
            blockers.append("normal_technical_qc_failed")
        if not reduced.technical_qc_passed:
            blockers.append("reduced_motion_technical_qc_failed")
        exact_artifact = normal.artifact_digest_sha256 == repeated.artifact_digest_sha256
        exact_checkpoints = normal.checkpoint_frame_digests == repeated.checkpoint_frame_digests
        if not exact_checkpoints:
            blockers.append("normal_checkpoint_repeat_mismatch")
        static_count = sum(
            len(track.keyframes) == 1
            for track in reduced_projection.tracks
            if track.property_path.startswith("transform.") or track.property_path == "style.blurPx"
        )
        covered_paths = sorted({track.property_path for track in normal_projection.tracks})
        case = MotionGoldenCaseEvidenceV1(
            case_id=document.document_id,
            family=family,
            graph_digest_sha256=motion_graph_digest(graph),
            covered_property_paths=covered_paths,
            parent_child_covered=any(node.parent_node_id for node in graph.nodes),
            typography_covered=any(path.startswith("typography.") for path in covered_paths),
            transition_covered=bool(graph.transitions),
            audio_clock_covered=bool(graph.audio_events),
            normal=normal.model_copy(
                update={
                    "artifact_path": Path(normal.artifact_path)
                    .relative_to(REPOSITORY_ROOT)
                    .as_posix()
                }
            ),
            reduced_motion=reduced.model_copy(
                update={
                    "artifact_path": Path(reduced.artifact_path)
                    .relative_to(REPOSITORY_ROOT)
                    .as_posix()
                }
            ),
            normal_repeat_artifact_digest_sha256=repeated.artifact_digest_sha256,
            normal_repeat_checkpoint_digests=repeated.checkpoint_frame_digests,
            exact_artifact_repeat=exact_artifact,
            exact_checkpoint_repeat=exact_checkpoints,
            reduced_motion_static_track_count=static_count,
            eligible=not blockers,
            blockers=blockers,
        )
        cases.append(case)
        suite_blockers.extend(f"{family}:{blocker}" for blocker in blockers)
        print(json.dumps({"family": family, "eligible": case.eligible, "blockers": blockers}))

    manifest = MotionGoldenSuiteEvidenceV1(
        suite_id="clicko.motion-four-family-goldens.v1",
        provider_version=provider.version,
        cases=cases,
        eligible=not suite_blockers,
        blockers=suite_blockers,
        rendered_at=datetime.now(UTC),
    )
    manifest_path = args.manifest or output_dir / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest.model_dump(mode="json", by_alias=True), ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "manifest": str(manifest_path),
                "eligible": manifest.eligible,
                "blockers": manifest.blockers,
            },
            ensure_ascii=False,
        )
    )
    return 0 if manifest.eligible else 1


if __name__ == "__main__":
    raise SystemExit(main())
