"""Render an original diagnostic piece through the res compiler and registered providers.

This runner never promotes providers or marks audiovisual/human review as passed.
Supply separately reviewed, scene-aligned narration files to complete acceptance.
"""

import argparse
import json
import math
import random
import wave
from datetime import UTC, datetime
from pathlib import Path

from PIL import Image, ImageDraw

from app.domain.studios.contextual_editing_v2 import ContextualPlanRequestV2
from app.domain.studios.contracts import AssetReferenceV1, CreativeDocumentV1, VideoRenderRequestV1
from app.providers.studios.contextual_motion_render import ContextualMotionRenderProvider
from app.providers.studios.contextual_render import ContextualFFmpegProvider
from app.providers.studios.video_render import HyperFramesCliVideoRenderProvider
from app.services.object_storage import sha256_file
from app.services.studios.scene_compiler import compile_scenes

NARRATION = [
    "Uma ideia pode ser boa e, mesmo assim, não chegar a ninguém. Entre criar e ser "
    "encontrado, existe um caminho: a distribuição.",
    "Pense na ideia como um ponto de partida. Cada canal abre uma conexão diferente: uma "
    "conversa, um vídeo, uma comunidade.",
    "Distribuir não é copiar a mesma peça em todos os lugares. É adaptar a forma, "
    "preservando o que a mensagem quer dizer.",
    "Um vídeo pode virar um trecho curto. O trecho pode levar a uma explicação. E a "
    "explicação pode abrir uma nova conversa.",
    "Mas publicar mais não garante atenção. Observe onde as pessoas entendem, participam "
    "e encontram valor. Ajuste o percurso com essas respostas.",
    "Distribuição conecta uma ideia às pessoas. Crie com clareza, escolha os caminhos e "
    "aprenda com cada encontro. A mensagem continua. A forma se adapta.",
]


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def tone(path, seconds, role):
    rng = random.Random(24)
    rate = 24000
    data = bytearray()
    for i in range(round(seconds * rate)):
        t = i / rate
        if role == "effect":
            value = 0.2 * math.sin(2 * math.pi * (950 - t * 800) * t) * math.exp(-t * 22)
        elif role == "ambience":
            value = 0.006 * rng.uniform(-1, 1)
        else:
            value = 0.025 * sum(math.sin(2 * math.pi * f * t) for f in (220, 275, 330)) / 3
        data.extend(int(max(-1, min(1, value)) * 32767).to_bytes(2, "little", signed=True))
    with wave.open(str(path), "wb") as output:
        output.setparams((1, 2, rate, 0, "NONE", "not compressed"))
        output.writeframes(data)


def build(root, font):
    root.mkdir(parents=True, exist_ok=True)
    files = {"font": font}
    for role, duration in (("music", 60), ("ambience", 60), ("effect", 0.5)):
        files[role] = root / (role + ".wav")
        tone(files[role], duration, role)
    mask = Image.new("L", (320, 320), 0)
    ImageDraw.Draw(mask).ellipse((8, 8, 312, 312), fill=255)
    files["mask"] = root / "mask.png"
    mask.save(files["mask"])
    art = Image.new("RGB", (320, 320), "#53ddbb")
    draw = ImageDraw.Draw(art)
    for x in range(0, 320, 24):
        draw.line((x, 0, 320 - x, 320), fill="#163b4b", width=9)
    files["art"] = root / "original-network.png"
    art.save(files["art"])
    now = datetime.now(UTC)
    document = CreativeDocumentV1(
        document_id="distribution-v2",
        workspace_id="qualification-local",
        title="Distribuição: uma ideia encontra pessoas",
        content_type="video",
        correlation_id="qualification-v2",
        brand_memory_ref={"id": "neutral-fixed", "revision": 1},
        brief={"objective": "Explicar como distribuição conecta uma ideia às pessoas", "audience": "Criadores"},
        composition={"pages": [{"id": "page", "width": 960, "height": 540}]},
        created_at=now,
        updated_at=now,
    )
    for key, file in files.items():
        document.assets.append(
            AssetReferenceV1(
                id=key,
                checksum=sha256_file(file),
                rights_status="verified",
                media_type="font/ttf"
                if key == "font"
                else "audio/wav"
                if key in {"music", "ambience", "effect"}
                else "image/png",
                origin="workspace",
                provenance={
                    "qualificationOnly": True,
                    "usageEvidence": "Procedural original assets; installed font used locally",
                },
            )
        )

    titles = [
        "Uma ideia precisa encontrar pessoas.",
        "Cada canal abre uma conexão.",
        "A mensagem continua. A forma se adapta.",
        "Um conteúdo abre novos caminhos.",
        "Publicar mais não garante atenção.",
        "Distribuição conecta uma ideia às pessoas.",
    ]
    short = [
        "Uma ideia",
        "uma conexão.",
        "A mensagem continua.",
        "novos caminhos.",
        "Publicar mais não garante atenção.",
        "Distribuição conecta uma ideia às pessoas.",
    ]
    durations, scenes, cursor = [240, 270, 270, 270, 270, 300], [], 0
    for index, duration in enumerate(durations):
        if index:
            cursor -= 18

        def element(key, kind, duration=duration, **kwargs):
            return {
                "id": key,
                "kind": kind,
                "purpose": "Tornar visível a relação explicada nesta cena",
                "durationFrames": duration,
                "width": 840,
                "height": 120,
                **kwargs,
            }

        elements = [
            element(
                "title",
                "text",
                x=60,
                y=48,
                text=titles[index],
                conciseText=short[index],
                fontAssetId="font",
                fontSize=46,
                reveal="words",
                revealFrames=38,
                textRole="fact" if index in {4, 5} else "support",
            ),
            element(
                "status",
                "text",
                x=60,
                y=507,
                height=28,
                text="DIAGNÓSTICO VISUAL · NARRAÇÃO PENDENTE",
                fontAssetId="font",
                fontSize=14,
                color="#83a19f",
            ),
        ]
        if index in {0, 5}:
            elements += [
                element(
                    "idea",
                    "image",
                    x=80,
                    y=215,
                    width=230,
                    height=230,
                    assetId="art",
                    maskAssetId="mask",
                    reveal="wipe",
                    revealFrames=45,
                ),
                element(
                    "destination",
                    "card",
                    x=570,
                    y=276,
                    width=305,
                    height=90,
                    text="PESSOAS" if index == 5 else "UMA IDEIA",
                    fontAssetId="font",
                    fontSize=32,
                ),
                element(
                    "connection",
                    "path",
                    x=330,
                    y=313,
                    width=225,
                    height=14,
                    points=[{"x": 0, "y": 7}, {"x": 220, "y": 7}],
                    color="#53ddbb",
                    reveal="path",
                    revealFrames=65,
                ),
            ]
        elif index == 1:
            elements += [
                element(
                    "network",
                    "group",
                    x=90,
                    y=245,
                    width=740,
                    height=160,
                    rotation=-3,
                    animations=[
                        {
                            "property": "rotation_degrees",
                            "keyframes": [
                                {"frame": 0, "value": -3, "easing": "ease_in_out"},
                                {"frame": 90, "value": 0},
                            ],
                        }
                    ],
                ),
                element(
                    "node",
                    "shape",
                    parentId="network",
                    width=100,
                    height=100,
                    shape="ellipse",
                    fill="#53ddbb",
                    durationFrames=duration - 30,
                    repeatCount=4,
                    repeatDx=200,
                    staggerFrames=10,
                    reveal="wipe",
                    revealFrames=25,
                ),
                element(
                    "connector",
                    "path",
                    parentId="network",
                    x=95,
                    y=42,
                    width=510,
                    height=16,
                    points=[{"x": 0, "y": 8}, {"x": 505, "y": 8}],
                    color="#53ddbb",
                    reveal="path",
                    revealFrames=90,
                ),
            ]
        else:
            labels = (
                ["VÍDEO", "CONVERSA", "COMUNIDADE"]
                if index == 2
                else ["CONTEÚDO", "TRECHO", "EXPLICAÇÃO"]
                if index == 3
                else ["ENTENDER", "PARTICIPAR", "AJUSTAR"]
            )
            for n, label in enumerate(labels):
                elements.append(
                    element(
                        f"card-{n}",
                        "card",
                        x=60 + n * 292,
                        y=245 + n * 25,
                        width=264,
                        height=112,
                        text=label,
                        fontAssetId="font",
                        fontSize=28,
                        fill="#183343",
                        reveal="wipe",
                        revealFrames=35 + n * 12,
                        animations=[
                            {
                                "property": "position_y",
                                "keyframes": [
                                    {"frame": 0, "value": 35, "easing": "ease_out"},
                                    {"frame": 50 + n * 12, "value": 0},
                                ],
                            }
                        ],
                    )
                )
        audio = [
            {
                "id": role,
                "role": role,
                "purpose": "Base discreta de continuidade",
                "assetId": role,
                "durationFrames": duration,
                "sourceStartSeconds": cursor / 30,
                "gainDb": -7,
                "fadeInFrames": 18,
                "fadeOutFrames": 18,
            }
            for role in ["music", "ambience"]
        ]
        audio.append(
            {
                "id": "accent",
                "role": "effect",
                "purpose": "Pontuar a entrada do elemento principal",
                "assetId": "effect",
                "durationFrames": 15,
                "syncElementId": elements[2]["id"],
                "syncOffsetFrames": 38,
                "gainDb": -9,
            }
        )
        scenes.append(
            {
                "id": f"scene-{index + 1}",
                "purpose": NARRATION[index],
                "narration": NARRATION[index],
                "facts": [titles[index]],
                "durationFrames": duration,
                "elements": elements,
                "audio": audio,
                "entrance": "cut" if not index else "wipe" if index == 3 else "dissolve",
                "transitionFrames": 18,
                "verification": ["Texto legível", "Conexões apoiam a explicação", "Som coincide com a entrada visual"],
            }
        )
        cursor += duration
    direction = ContextualPlanRequestV2(
        expected_document_revision=1,
        intent={"objective": document.brief.objective, "script": " ".join(NARRATION), "lockedFacts": titles[-2:]},
        scenes=scenes,
    )
    return document, direction, files


def render(document, direction, files, root, name, provider):
    draft, graph, operations, manifest = compile_scenes(document, direction, "local-validation", name)
    if manifest["missingMaterials"]:
        raise ValueError("Cannot render a plan with missing materials")
    draft.composition.narrative["editorialV2"]["motionGraph"] = graph.model_dump(mode="json", by_alias=True)
    request = VideoRenderRequestV1(
        workspace_id=draft.workspace_id,
        document_id=draft.document_id,
        document_revision=draft.revision,
        document_version=draft.version,
        page_ids=["page"],
        asset_ids=list(files),
        output={"width": 960, "height": 540, "fps": 30, "quality": "draft"},
        correlation_id=name,
    )
    for suffix, value in (("document", draft), ("graph", graph), ("plan", direction)):
        write_json(root / f"{name}.{suffix}.json", value.model_dump(mode="json", by_alias=True))
    write_json(root / f"{name}.manifest.json", manifest)
    write_json(root / f"{name}.operations.json", [o.model_dump(mode="json", by_alias=True) for o in operations])
    print("render " + name, flush=True)
    result = provider.render(
        draft, request, files, root / f"{name}.mp4", lambda p: print(f"{name}: {p}%", flush=True), lambda: False
    )
    write_json(root / f"{name}.receipt.json", result.model_dump(mode="json", by_alias=True))
    return draft


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cli", required=True)
    parser.add_argument("--font", type=Path, required=True)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--reuse-only", action="store_true")
    args = parser.parse_args()
    root = args.output.resolve()
    document, requested, files = build(root / "materials", args.font.resolve())
    write_json(root / "requested-plan-with-narration.json", requested.model_dump(mode="json", by_alias=True))
    _, _, _, unavailable = compile_scenes(document, requested, "local-validation", "requested")
    write_json(root / "narration-pending.json", unavailable["missingMaterials"])
    diagnostic = requested.model_copy(deep=True)
    for scene in diagnostic.scenes:
        scene.narration = ""  # Separate visual diagnostic, never the requested narrated deliverable.
    if args.smoke:
        diagnostic.scenes = diagnostic.scenes[:1]
        diagnostic.intent.locked_facts = []
    provider = ContextualMotionRenderProvider(
        HyperFramesCliVideoRenderProvider("node", args.cli, 1200), ContextualFFmpegProvider("ffmpeg", 1200)
    )
    if args.reuse_only:
        source = root / "distribution-motion-diagnostic.mp4"
        if not source.exists():
            raise ValueError("Render the initial diagnostic before reusing footage")
        files["edited-source"] = source
        document.assets.append(
            AssetReferenceV1(
                id="edited-source",
                media_type="video/mp4",
                checksum=sha256_file(source),
                rights_status="verified",
                origin="derived",
            )
        )
        footage = ContextualPlanRequestV2(
            expected_document_revision=1,
            intent={"objective": "Reutilizar um trecho mantendo seu áudio e explicar sua função"},
            scenes=[
                {
                    "id": "reuse",
                    "purpose": "Preservar o trecho e adicionar contexto",
                    "durationFrames": 120,
                    "verification": [
                        "Origem deslocada 1,2 segundos",
                        "Áudio de origem sincronizado",
                        "Texto adicional legível",
                    ],
                    "elements": [
                        {
                            "id": "footage",
                            "kind": "video",
                            "purpose": "Reutilizar o vídeo produzido",
                            "durationFrames": 120,
                            "width": 960,
                            "height": 540,
                            "assetId": "edited-source",
                            "sourceStartSeconds": 1.2,
                        },
                        {
                            "id": "context",
                            "kind": "card",
                            "purpose": "Contextualizar a seleção",
                            "durationFrames": 120,
                            "width": 480,
                            "height": 70,
                            "x": 430,
                            "y": 430,
                            "text": "Um trecho. Um novo contexto.",
                            "fontAssetId": "font",
                            "fontSize": 26,
                        },
                    ],
                }
            ],
        )
        render(document, footage, files, root, "reused-footage-diagnostic", provider)
        return
    render(document, diagnostic, files, root, "distribution-motion-diagnostic", provider)
    if not args.smoke:
        # Exercise the same deterministic local revision transformation used by the service.
        from app.services.studios.contextual_editing_v2 import revise_direction

        revised = revise_direction(diagnostic, {s.id for s in diagnostic.scenes[:-1]}, "mais calmo")
        revised = revise_direction(revised, {s.id for s in revised.scenes[:-1]}, "menos texto")
        assert revised.scenes[-1] == diagnostic.scenes[-1]
        render(document, revised, files, root, "distribution-motion-revised-diagnostic", provider)
    write_json(
        root / "qualification.json",
        {
            "technical": "renders_created",
            "humanReview": "pending",
            "audiovisualReview": "pending",
            "narration": "unavailable",
            "llmPlanning": "not_exercised",
            "deliveryComplete": False,
            "paidCalls": 0,
            "reference": "https://www.instagram.com/mep.io_/reel/DciIBRYBHBK/",
        },
    )


if __name__ == "__main__":
    main()
