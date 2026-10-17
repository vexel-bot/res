"""Local, rights-owned engineering animatics for three independent product briefs.

Run from backend: python -m scripts.render_editorial_operations_animatics
The drawings are diagnostic fixtures, not proposed commercial footage.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from PIL import Image, ImageDraw

from app.domain.studios.contextual_editing_v2 import ContextualPlanRequestV2
from app.domain.studios.contracts import AssetReferenceV1, CreativeDocumentV1, VideoRenderRequestV1
from app.domain.studios.motion import evaluate_motion_graph, project_motion_graph
from app.providers.studios.remotion_render import RemotionNativeGraphicsProvider
from app.services.studios.editorial_operation_selection import evaluate_operation_bindings
from app.services.studios.scene_compiler import compile_scenes

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "output" / "editorial-operations-20260930"
FPS = 30
SIZE = 320
BRIEFS = {
    "bebida": {"label": "Bebida fria", "copy": "Abra. Sirva. Sinta.", "dark": "#172c3a", "accent": "#fbbf66"},
    "mochila": {"label": "Mochila urbana", "copy": "Tudo no lugar.", "dark": "#25302b", "accent": "#b5da9a"},
    "tarefas": {
        "label": "Aplicativo de tarefas",
        "copy": "Conclua com clareza.",
        "dark": "#25253d",
        "accent": "#b7adff",
    },
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def product(draw: ImageDraw.ImageDraw, kind: str, phase: int, progress: float, accent: str):
    if kind == "bebida":
        draw.rounded_rectangle((99, 96, 192, 240), radius=18, fill=accent, outline="#ffffff", width=3)
        draw.ellipse((118, 88, 173, 104), fill="#dfe7e9", outline="#ffffff", width=2)
        draw.rounded_rectangle((116, 150, 176, 177), radius=8, fill="#172c3a")
        if phase == 0:
            draw.line((146, 89, 146 + 28 * progress, 89 - 20 * progress), fill="#ffffff", width=6)
            for i in range(3):
                x = 110 + i * 45
                y = 76 - (progress * (18 + i * 8))
                draw.ellipse((x, y, x + 5, y + 5), fill="#ffffff")
        else:
            draw.polygon([(203, 160), (248, 168), (239, 242), (209, 242)], outline="#ffffff")
            draw.rectangle((212, 240 - 65 * progress, 239, 240), fill=accent)
            draw.line((185, 110, 223, 210 - 20 * progress), fill="#fff3d8", width=5)
    elif kind == "mochila":
        draw.rounded_rectangle((88, 112, 228, 253), radius=28, fill=accent, outline="#ffffff", width=4)
        draw.arc((117, 77, 201, 143), 180, 360, fill="#ffffff", width=6)
        draw.rounded_rectangle((112, 182, 204, 237), radius=12, outline="#25302b", width=4)
        if phase == 0:
            draw.line((112, 136, 112 + 103 * progress, 136), fill="#25302b", width=8)
            draw.ellipse((108 + 103 * progress, 130, 122 + 103 * progress, 144), fill="#ffffff")
        else:
            y = 55 + 85 * progress
            draw.rounded_rectangle((136, y, 184, y + 69), radius=8, fill="#f9e0b8", outline="#ffffff", width=2)
            draw.line((160, 139, 160, 238), fill="#25302b", width=3)
    else:
        draw.rounded_rectangle((70, 45, 249, 270), radius=19, fill="#f3f0ff", outline="#ffffff", width=5)
        draw.rounded_rectangle((88, 70, 229, 105), radius=7, fill=accent)
        for row in range(3):
            y = 135 + row * 42
            draw.rectangle((94, y, 114, y + 20), outline="#6555a6", width=3)
            draw.line((131, y + 10, 214, y + 10), fill="#a6a0bc", width=5)
        if phase == 0:
            x = 120 - 20 * progress
            y = 152 - 8 * progress
            draw.polygon([(x, y), (x + 16, y + 7), (x + 5, y + 12)], fill="#24233b")
        else:
            row = min(2, int(progress * 3))
            for index in range(row + 1):
                y = 135 + index * 42
                draw.line((96, y + 10, 102, y + 16, 113, y + 2), fill="#6555a6", width=4)


def make_frame(kind: str, spec: dict, phase: int, progress: float) -> Image.Image:
    image = Image.new("RGB", (SIZE, SIZE), spec["dark"])
    draw = ImageDraw.Draw(image)
    draw.ellipse((30, 42, 294, 306), outline="#ffffff", width=2)
    product(draw, kind, phase, progress, spec["accent"])
    return image


def create_media(kind: str, spec: dict, folder: Path) -> dict[str, Path]:
    folder.mkdir(parents=True, exist_ok=True)
    files = {}
    for phase in (0, 1):
        path = folder / f"action-{phase}.mp4"
        process = subprocess.Popen(
            [
                "ffmpeg",
                "-v",
                "error",
                "-y",
                "-f",
                "rawvideo",
                "-pix_fmt",
                "rgb24",
                "-s",
                "320x320",
                "-r",
                str(FPS),
                "-i",
                "-",
                "-an",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                str(path),
            ],
            stdin=subprocess.PIPE,
        )
        assert process.stdin
        for frame in range(60):
            process.stdin.write(make_frame(kind, spec, phase, frame / 59).tobytes())
        process.stdin.close()
        if process.wait() != 0:
            raise RuntimeError("fixture_video_generation_failed")
        files[f"action{phase}"] = path
    for state, phase, progress in (("base", 0, 0), ("variant", 1, 1)):
        path = folder / f"{state}.png"
        make_frame(kind, spec, phase, progress).save(path)
        files[state] = path
    return files


def create_concatenation_baseline(files: dict[str, Path], destination: Path) -> None:
    """Use the same four sources without an editorial operation for a blind comparison."""
    filters = ";".join(
        f"[{index}:v]trim=duration=1,setpts=PTS-STARTPTS,fps={FPS}[v{index}]"
        for index in range(4)
    ) + ";[v0][v1][v2][v3]concat=n=4:v=1:a=0[v]"
    subprocess.run(
        [
            "ffmpeg", "-v", "error", "-y",
            "-i", str(files["action0"]), "-i", str(files["action1"]),
            "-loop", "1", "-t", "1", "-i", str(files["base"]),
            "-loop", "1", "-t", "1", "-i", str(files["variant"]),
            "-filter_complex", filters, "-map", "[v]", "-an", "-c:v", "libx264",
            "-pix_fmt", "yuv420p", str(destination),
        ],
        check=True,
    )


def shot(identifier: str, index: int, end: int, action: str) -> dict:
    return {
        "id": "shot-" + identifier,
        "function": "demonstrate" if index == 0 else "consequence",
        "subject": identifier,
        "observableAction": action,
        "shotScale": "close",
        "angle": "eye_level",
        "regionOfInterest": "Product and changing area",
        "attentionStart": "Product",
        "attentionEnd": "Action result",
        "lighting": {
            "quality": "graphic",
            "direction": "not_applicable",
            "contrast": "medium",
            "temperatureRelationship": "Consistent",
            "subjectSeparation": "Tonal contrast",
            "executionMode": "deterministic_composite",
        },
        "cutMotivation": "The product action continues",
        "targetElementIds": [identifier],
        "executionComponentIds": ["action_progression"],
        "verification": ["Internal action visible"],
        "startFrame": 0 if index == 0 else end,
        "endFrameExclusive": end if index == 0 else 60,
    }


def make_direction(spec: dict, cut: int, reveal: int) -> ContextualPlanRequestV2:
    return ContextualPlanRequestV2.model_validate(
        {
            "executionScope": "visual_only",
            "expectedDocumentRevision": 1,
            "intent": {"objective": spec["label"], "script": spec["copy"]},
            "scenes": [
                {
                    "id": "action",
                    "purpose": "Show action and visible consequence",
                    "durationFrames": 60,
                    "verification": ["Product action changes visibly"],
                    "techniqueIds": ["action_progression"],
                    "operationBindings": [
                        {
                            "techniqueId": "action_progression",
                            "targetIds": ["action0", "action1"],
                            "anchorId": "product",
                            "cutMotivation": "Continue product gesture across the cut",
                            "newInformation": "The operation finishes on the product",
                        }
                    ],
                    "elements": [
                        {
                            "id": "action0",
                            "kind": "video",
                            "purpose": "First product action",
                            "assetId": "action0",
                            "width": SIZE,
                            "height": SIZE,
                            "durationFrames": cut,
                            "sourceAudio": "mute",
                            "objectFit": "cover",
                        },
                        {
                            "id": "action1",
                            "kind": "video",
                            "purpose": "Action consequence",
                            "assetId": "action1",
                            "width": SIZE,
                            "height": SIZE,
                            "startFrame": cut,
                            "durationFrames": 60 - cut,
                            "sourceAudio": "mute",
                            "objectFit": "cover",
                        },
                    ],
                    "nativeComponents": [
                        {"component": "action_montage", "targetIds": ["action0", "action1"], "entranceFrames": 4}
                    ],
                    "shotPlan": [
                        shot("action0", 0, cut, "The product begins changing"),
                        shot("action1", 1, cut, "The action produces a consequence"),
                    ],
                },
                {
                    "id": "reveal",
                    "purpose": "Inspect the resulting state",
                    "durationFrames": 60,
                    "verification": ["Changed state appears only inside moving window"],
                    "techniqueIds": ["moving_variant_mask"],
                    "operationBindings": [
                        {
                            "techniqueId": "moving_variant_mask",
                            "targetIds": ["variant"],
                            "anchorId": "product",
                            "cutMotivation": "Inspect the state revealed by the action",
                            "newInformation": spec["copy"],
                        }
                    ],
                    "elements": [
                        {
                            "id": "base",
                            "kind": "image",
                            "purpose": "Original product state",
                            "assetId": "base",
                            "width": SIZE,
                            "height": SIZE,
                            "durationFrames": 60,
                            "zIndex": 1,
                        },
                        {
                            "id": "variant",
                            "kind": "image",
                            "purpose": "Changed product state",
                            "assetId": "variant",
                            "width": SIZE,
                            "height": SIZE,
                            "durationFrames": 60,
                            "zIndex": 2,
                        },
                        {
                            "id": "footer",
                            "kind": "shape",
                            "purpose": "Readable copy zone",
                            "x": 0,
                            "y": 270,
                            "width": SIZE,
                            "height": 50,
                            "startFrame": 14,
                            "durationFrames": 46,
                            "fill": spec["dark"],
                            "zIndex": 3,
                            "visualRole": "text",
                        },
                        {
                            "id": "copy",
                            "kind": "text",
                            "purpose": "Brief-specific close",
                            "text": spec["copy"],
                            "x": 20,
                            "y": 281,
                            "width": 280,
                            "height": 28,
                            "startFrame": 14,
                            "durationFrames": 46,
                            "fontSize": 18,
                            "textAlign": "center",
                            "zIndex": 4,
                            "visualRole": "text",
                        },
                    ],
                    "nativeComponents": [
                        {
                            "component": "moving_variant_mask",
                            "targetIds": ["variant"],
                            "baseTargetId": "base",
                            "entranceFrames": reveal,
                            "switchFrame": 0,
                            "maskStartX": 0.18,
                            "maskEndX": 0.82,
                            "maskRadius": 0.34,
                        },
                        {"component": "integrated_typography", "targetIds": ["copy"], "entranceFrames": 10},
                    ],
                },
            ],
        }
    )


def run() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    provider = RemotionNativeGraphicsProvider("node", "ffmpeg", 240)
    receipts = []
    baselines = []
    for kind, spec in BRIEFS.items():
        folder = OUTPUT / kind
        files = create_media(kind, spec, folder / "materials")
        baseline = folder / "concat-baseline.mp4"
        create_concatenation_baseline(files, baseline)
        baselines.append({"brief": kind, "video": str(baseline), "videoSha256": sha(baseline),
                          "apiCostUsd": 0, "humanComparison": "pending"})
        now = datetime.now(UTC)
        source = CreativeDocumentV1(
            document_id="fixture-" + kind,
            workspace_id="local-fixture",
            title=spec["label"],
            content_type="video",
            correlation_id="editorial-operations-fixture",
            brand_memory_ref={"id": "fixture", "revision": 1},
            brief={"objective": spec["label"], "audience": "Engineering review"},
            assets=[
                AssetReferenceV1.model_validate(
                    {
                        "id": name,
                        "mediaType": "video/mp4" if path.suffix == ".mp4" else "image/png",
                        "checksum": sha(path),
                        "rightsStatus": "verified",
                        "origin": "locally_generated_fixture",
                    }
                )
                for name, path in files.items()
            ],
            composition={"pages": [{"id": "page", "width": SIZE, "height": SIZE, "safeArea": 0}]},
            created_at=now,
            updated_at=now,
        )
        for rhythm, cut, reveal in (("A", 36, 42), ("B", 22, 16)):
            direction = make_direction(spec, cut, reveal)
            decisions = evaluate_operation_bindings(direction, source)
            if any(item["status"] != "eligible" for item in decisions):
                raise ValueError("fixture_operation_ineligible:" + json.dumps(decisions))
            draft, graph, _, manifest = compile_scenes(source, direction, "fixture", kind + rhythm)
            projection = project_motion_graph(graph, "remotion", evaluate_motion_graph(draft, graph))
            request = VideoRenderRequestV1(
                workspace_id=draft.workspace_id,
                document_id=draft.document_id,
                document_revision=draft.revision,
                document_version=draft.version,
                page_ids=["page"],
                asset_ids=list(files),
                correlation_id="fixture-" + kind + rhythm,
                output={"width": SIZE, "height": SIZE, "fps": FPS, "audioCodec": "none"},
            )
            video = folder / f"animatic-{rhythm}.mp4"
            rendered = provider.render(
                draft,
                request,
                files,
                video,
                lambda _: None,
                lambda: False,
                motion_projection=projection,
                automatic_draft=True,
            )
            plan = folder / f"plan-{rhythm}.json"
            plan.write_text(
                json.dumps(
                    {
                        "direction": direction.model_dump(mode="json", by_alias=True),
                        "manifest": manifest,
                        "operationDecisions": decisions,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            receipts.append(
                {
                    "brief": kind,
                    "rhythm": rhythm,
                    "video": str(video),
                    "videoSha256": sha(video),
                    "plan": str(plan),
                    "provider": rendered.provider,
                    "nativeCompositionDigest": rendered.renderer_checks["nativeCompositionDigest"],
                    "observedFrames": len(rendered.renderer_checks["geometrySamples"]),
                    "apiCostUsd": 0,
                    "technicalRender": "passed",
                    "humanVisualReview": "pending",
                    "soundReview": "not_applicable_silent_fixture",
                }
            )
            print(f"{kind} {rhythm}: {video}", flush=True)
    (OUTPUT / "receipts.json").write_text(json.dumps(receipts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUTPUT / "baseline-receipts.json").write_text(
        json.dumps(baselines, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (OUTPUT / "evaluation.json").write_text(
        json.dumps(
            {
                "schemaVersion": "studio.editorial-operations-evaluation.v1",
                "briefs": sorted(BRIEFS),
                "animatics": len(receipts),
            "concatenationBaselines": len(baselines),
                "technicalFunctioning": "passed_for_local_synthetic_fixtures",
            "visualQuality": "pending_human_review_with_real_materials",
            "blindComparison": "pending",
                "audioQuality": "not_evaluated_silent_fixtures",
                "autonomy": "partial_fixture_assets_and_plans_authored_by_test_script",
                "apiCostUsd": 0,
                "promotionToRenderVerified": False,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    run()
