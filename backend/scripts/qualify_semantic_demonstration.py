"""Render a controlled canonical-content fixture through the production stack.

This proves engineering behavior only. It is not an autonomous creative pilot
and never records human approval.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.domain.studios.contextual_editing_v2 import ContextualPlanRequestV2  # noqa: E402
from app.domain.studios.contracts import (  # noqa: E402
    AssetReferenceV1,
    CreativeDocumentV1,
    VideoRenderRequestV1,
    VideoTechnicalQualityPolicyV1,
)
from app.providers.studios.contextual_motion_render import ContextualMotionRenderProvider  # noqa: E402
from app.providers.studios.contextual_render import ContextualFFmpegProvider  # noqa: E402
from app.providers.studios.procedural_audio import render as render_procedural_sound  # noqa: E402
from app.providers.studios.video_quality import VIDEO_TECHNICAL_QUALITY_PROVIDERS  # noqa: E402
from app.providers.studios.video_render import HyperFramesCliVideoRenderProvider  # noqa: E402
from app.providers.studios.visual_state_observation import observe_visual_states  # noqa: E402
from app.services.object_storage import sha256_file  # noqa: E402
from app.services.studios.production_audit import observed_result_gate  # noqa: E402
from app.services.studios.scene_compiler import compile_scenes, prepare_direction  # noqa: E402


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def create_image(path: Path) -> None:
    image = Image.new("RGB", (1200, 800), "#efe7d5")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((120, 160, 1080, 690), radius=70, fill="#9d552f")
    draw.ellipse((375, 150, 825, 600), fill="#f8f2e8")
    draw.ellipse((425, 205, 775, 555), fill="#31201b")
    draw.arc((745, 250, 965, 500), start=260, end=100, fill="#f8f2e8", width=55)
    draw.line((170, 650, 1030, 650), fill="#d8be91", width=12)
    image.save(path, quality=95)


def build(output: Path, font: Path):
    output.mkdir(parents=True, exist_ok=True)
    image = output / "canonical-coffee.jpg"
    sound = output / "publish-confirm.wav"
    create_image(image)
    render_procedural_sound("publish_confirm", sound)
    assets = {"coffee": image, "font": font, "publish-sfx": sound}
    now = datetime.now(UTC)
    document = CreativeDocumentV1(
        document_id="semantic-demonstration-fixture",
        workspace_id="local-engineering-validation",
        title="Canonical content adaptation fixture",
        content_type="video",
        correlation_id="semantic-demonstration-fixture-v1",
        brand_memory_ref={"id": "fixture-neutral", "revision": 1},
        brief={
            "objective": "Verify a recognizable piece survives a format adaptation",
            "audience": "Equipe de produto avaliando a continuidade visual",
        },
        composition={"pages": [{"id": "page", "width": 720, "height": 1280}]},
        created_at=now,
        updated_at=now,
    )
    for asset_id, path in assets.items():
        document.assets.append(
            AssetReferenceV1(
                id=asset_id,
                media_type="font/ttf"
                if asset_id == "font"
                else "audio/wav"
                if asset_id == "publish-sfx"
                else "image/jpeg",
                checksum=sha256_file(path),
                rights_status="verified",
                origin="workspace" if asset_id == "font" else "generated",
                provenance={
                    "qualificationOnly": True,
                    "authorship": "deterministic local engineering fixture",
                    "humanReview": "pending",
                },
            )
        )

    elements = []
    for state in ("portrait", "square"):
        elements.extend(
            [
                {
                    "id": state,
                    "kind": "group",
                    "purpose": f"Estado {state} da mesma peça",
                    "contentReferenceId": "coffee-piece",
                    "width": 560,
                    "height": 760,
                    "durationFrames": 240,
                    "visualRole": "hero" if state == "portrait" else "support",
                },
                {
                    "id": f"{state}-photo",
                    "kind": "image",
                    "purpose": "Imagem principal persistente",
                    "assetId": "coffee",
                    "parentId": state,
                    "contentReferenceId": "coffee-piece",
                    "contentPartId": "photo",
                    "width": 480,
                    "height": 420,
                    "durationFrames": 240,
                    "regionOfInterest": {
                        "x": 0.25,
                        "y": 0.10,
                        "width": 0.50,
                        "height": 0.72,
                        "purpose": "Manter a xícara reconhecível",
                    },
                },
                {
                    "id": f"{state}-title",
                    "kind": "text",
                    "purpose": "Título persistente",
                    "text": "CAFÉ QUE ENCONTRA VOCÊ",
                    "parentId": state,
                    "contentReferenceId": "coffee-piece",
                    "contentPartId": "headline",
                    "fontAssetId": "font",
                    "color": "#fff7e8",
                    "width": 480,
                    "height": 130,
                    "durationFrames": 240,
                    "reveal": "words",
                    "revealFrames": 20,
                },
                {
                    "id": f"{state}-identity",
                    "kind": "text",
                    "purpose": "Identidade persistente",
                    "text": "RES CAFÉ",
                    "parentId": state,
                    "contentReferenceId": "coffee-piece",
                    "contentPartId": "brand",
                    "fontAssetId": "font",
                    "color": "#f4c987",
                    "width": 220,
                    "height": 50,
                    "durationFrames": 240,
                },
            ]
        )
    direction = ContextualPlanRequestV2.model_validate(
        {
            "semanticVerificationPolicy": "canonical_demonstration_v1",
            "expectedDocumentRevision": 1,
            "intent": {"objective": "Mostrar a mesma peça reorganizada em dois formatos"},
            "contentReferences": [
                {
                    "id": "coffee-piece",
                    "purpose": "Peça de café reconhecível",
                    "parts": [
                        {
                            "id": "photo",
                            "role": "primary_media",
                            "assetId": "coffee",
                            "checksumSha256": sha256_file(image),
                        },
                        {"id": "headline", "role": "title", "text": "CAFÉ QUE ENCONTRA VOCÊ"},
                        {"id": "brand", "role": "identity", "text": "RES CAFÉ"},
                    ],
                }
            ],
            "scenes": [
                {
                    "id": "adaptation",
                    "purpose": "Demonstrar continuidade e adaptação",
                    "durationFrames": 240,
                    "background": "#17120f",
                    "contentReferenceIds": ["coffee-piece"],
                    "elements": elements,
                    "audio": [
                        {
                            "id": "publish-event",
                            "role": "effect",
                            "purpose": "Sinal sintético de publicação",
                            "assetId": "publish-sfx",
                            "startFrame": 100,
                            "durationFrames": 7,
                            "gainDb": -4,
                        }
                    ],
                    "verification": [
                        "Imagem, título e identidade permanecem reconhecíveis",
                        "O layout muda entre vertical e quadrado",
                        "O evento de publicação está audível",
                    ],
                    "compositions": [
                        {
                            "id": "format-change",
                            "family": "format_transformation",
                            "targetIds": ["portrait", "square"],
                            "purpose": "Reorganizar a mesma peça",
                            "expectedResult": "Peça vertical seguida da mesma peça quadrada",
                            "actionFrames": 100,
                            "continuityKey": "coffee-piece",
                            "viewportFormats": ["portrait", "square"],
                        }
                    ],
                    "semanticAssertions": [
                        {
                            "id": "same-content-two-formats",
                            "kind": "format_adaptation",
                            "objectId": "coffee-piece",
                            "initialState": "Peça vertical completa",
                            "event": "Layout se reorganiza",
                            "finalState": "Peça quadrada completa",
                            "startFrame": 0,
                            "endFrameExclusive": 240,
                            "targetIds": ["portrait", "square"],
                            "requiredPartIds": ["photo", "headline", "brand"],
                            "evidenceRequired": "temporal_sequence",
                        },
                        {
                            "id": "publish-is-audible",
                            "kind": "audible_event",
                            "objectId": "publish-event",
                            "initialState": "Antes da mudança",
                            "event": "Mudança de formato",
                            "finalState": "Confirmação audível",
                            "startFrame": 98,
                            "endFrameExclusive": 110,
                            "targetIds": ["publish-event"],
                            "evidenceRequired": "mixed_audio",
                        },
                    ],
                }
            ],
        }
    )
    return document, direction, assets


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cli", type=Path, required=True)
    parser.add_argument("--font", type=Path, required=True)
    parser.add_argument("--editorial-motion", action="store_true",
                        help="Exercise the V2 art and choreography path as an engineering fixture")
    args = parser.parse_args()
    output = args.output.resolve()
    document, direction, assets = build(output / "materials", args.font.resolve())
    if args.editorial_motion:
        from app.domain.studios.cinematic_direction import (  # noqa: E402
            CinematicArtDirectionV1,
            EditorialMotionSystemV2,
        )

        direction.art_direction = CinematicArtDirectionV1(
            visual_system="Editorial hierarchy around one persistent piece",
            palette=["#17120f", "#f4c987", "#9d552f"],
            typography="Display headline with a quieter brand signature",
            contrast_strategy="Warm light type on a dark ground",
            footage_treatment="No footage in this controlled fixture",
            graphics_relationship="Image and headline move together between formats",
            continuity_rules=["Preserve the photo, headline and brand across states"],
            motion_system=EditorialMotionSystemV2(
                layout="typography_dominant", alignment="left", frame="none"
            ),
        )
        direction.scenes[0].compositions[0].state_hold_frames = [90, 90]
        direction.scenes[0].compositions[0].movement_frames = 30
    executable = prepare_direction(direction, 720, 1280)
    draft, graph, operations, manifest = compile_scenes(document, direction, "engineering", "semantic-fixture")
    draft.composition.narrative["editorialV2"]["motionGraph"] = graph.model_dump(mode="json", by_alias=True)
    request = VideoRenderRequestV1(
        workspace_id=draft.workspace_id,
        document_id=draft.document_id,
        document_revision=draft.revision,
        document_version=draft.version,
        page_ids=["page"],
        asset_ids=list(assets),
        output={"width": 720, "height": 1280, "fps": 30, "quality": "draft"},
        correlation_id="semantic-fixture-v1",
    )
    provider = ContextualMotionRenderProvider(
        HyperFramesCliVideoRenderProvider("node", str(args.cli.resolve()), 900),
        ContextualFFmpegProvider("ffmpeg", 900),
    )
    video = output / (
        "editorial-motion-engineering-fixture.mp4" if args.editorial_motion
        else "canonical-format-engineering-fixture.mp4"
    )
    result = provider.render(
        draft, request, assets, video, lambda value: print(f"render:{value}%", flush=True), lambda: False
    )
    quality = VIDEO_TECHNICAL_QUALITY_PROVIDERS["builtin.ffmpeg-qc-v1"].evaluate(
        video,
        expected=request.output,
        expected_duration_ms=8_000,
        policy=VideoTechnicalQualityPolicyV1(),
        is_cancelled=lambda: False,
    )
    audit = observe_visual_states(
        video,
        executable,
        graph,
        renderer_checks=(result.renderer_checks or {}).get("graphics", {}),
        expected_direction_digest=manifest["hashes"]["executableDirection"],
        expected_composition_digest=manifest["hashes"]["executableComposition"],
    )
    write_json(output / "direction.json", direction.model_dump(mode="json", by_alias=True))
    write_json(output / "executable-direction.json", executable.model_dump(mode="json", by_alias=True))
    write_json(output / "manifest.json", manifest)
    write_json(output / "operations.json", [item.model_dump(mode="json", by_alias=True) for item in operations])
    write_json(output / "render-receipt.json", result.model_dump(mode="json", by_alias=True))
    write_json(output / "visual-audit.json", audit)
    render_checksum = sha256_file(video)
    observed_gate = observed_result_gate(audit, render_checksum)
    qualification_status = (
        "failed"
        if quality.status != "passed" or observed_gate["status"] == "failed"
        else "inconclusive"
        if observed_gate["status"] != "passed"
        else "awaiting_human_review"
    )
    qualification = {
        "schemaVersion": "studio.semantic-demonstration-qualification.v2",
        "classification": "controlled_engineering_fixture",
        "autonomousCreativePilot": False,
        "renderChecksumSha256": render_checksum,
        "status": qualification_status,
        "technical": quality.status,
        "execution": audit["executionVerification"]["status"],
        "semantic": audit["semanticVerification"]["status"],
        "visualEditorial": audit["visualEditorial"],
        "observedResult": observed_gate,
        "coverage": audit["coverage"],
        "humanReview": "pending",
        "commerciallyQualified": False,
        "limitations": [
            "This fixture is authored by an engineering script and does not prove autonomous creative direction.",
            *audit.get("limitations", []),
        ],
    }
    write_json(
        output / "qualification.json",
        qualification,
    )
    print(
        json.dumps(
            {
                "video": str(video),
                "status": qualification_status,
                "technical": quality.status,
                "execution": audit["executionVerification"]["status"],
                "semantic": audit["semanticVerification"]["status"],
                "observedResult": observed_gate["status"],
                "humanReview": "pending",
            }
        )
    )
    return 0 if quality.status == "passed" and observed_gate["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
