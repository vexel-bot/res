import subprocess

import pytest
from PIL import Image, ImageDraw

from app.domain.studios.contextual_editing_v2 import ContextualPlanRequestV2
from app.providers.studios.visual_state_observation import observe_visual_states


def direction_with_audio_assertion():
    return ContextualPlanRequestV2.model_validate(
        {
            "semanticVerificationPolicy": "canonical_demonstration_v1",
            "expectedDocumentRevision": 1,
            "intent": {"objective": "Demonstrar publicação", "script": "A peça entra no feed."},
            "scenes": [
                {
                    "id": "publish",
                    "purpose": "Publicar",
                    "durationFrames": 30,
                    "elements": [
                        {
                            "id": "panel",
                            "kind": "shape",
                            "purpose": "Painel",
                            "width": 120,
                            "height": 120,
                            "durationFrames": 30,
                            "visualRole": "hero",
                        }
                    ],
                    "audio": [
                        {
                            "id": "publish-sfx",
                            "role": "effect",
                            "purpose": "Confirmar publicação",
                            "assetId": "published-effect",
                            "durationFrames": 30,
                        }
                    ],
                    "verification": ["O efeito está audível"],
                    "semanticAssertions": [
                        {
                            "id": "publish-audio",
                            "kind": "audible_event",
                            "objectId": "publish-sfx",
                            "initialState": "Silêncio anterior",
                            "event": "Publicação",
                            "finalState": "Confirmação audível",
                            "startFrame": 0,
                            "endFrameExclusive": 30,
                            "targetIds": ["publish-sfx"],
                            "evidenceRequired": "mixed_audio",
                        }
                    ],
                }
            ],
        }
    )


@pytest.mark.parametrize("audible", [False, True])
def test_audible_assertion_uses_exported_samples_not_stream_presence(tmp_path, audible):
    output = tmp_path / ("audible.mp4" if audible else "silent.mp4")
    audio = "sine=frequency=660:sample_rate=48000:duration=1" if audible else "anullsrc=r=48000:cl=mono:d=1"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=#101820:s=320x480:r=30:d=1",
            "-f",
            "lavfi",
            "-i",
            audio,
            "-shortest",
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            str(output),
        ],
        check=True,
        timeout=30,
    )

    audit = observe_visual_states(output, direction_with_audio_assertion())
    evidence = audit["semanticVerification"]["evidence"][0]

    assert evidence["status"] == ("passed" if audible else "failed")
    assert evidence["audioMeasurement"]["sampleCount"] > 0
    assert audit["semanticVerification"]["status"] == ("passed" if audible else "failed")


def canonical_direction():
    elements = []
    for state in ("portrait", "square"):
        elements.extend(
            [
                {
                    "id": state,
                    "kind": "group",
                    "purpose": f"Estado {state}",
                    "contentReferenceId": "piece",
                    "width": 240,
                    "height": 300,
                    "durationFrames": 30,
                },
                {
                    "id": f"{state}-media",
                    "kind": "image",
                    "purpose": "Imagem persistente",
                    "assetId": "asset-photo",
                    "parentId": state,
                    "contentReferenceId": "piece",
                    "contentPartId": "photo",
                    "width": 180,
                    "height": 180,
                    "durationFrames": 30,
                },
                {
                    "id": f"{state}-title",
                    "kind": "text",
                    "purpose": "Título persistente",
                    "text": "Uma ideia clara",
                    "parentId": state,
                    "contentReferenceId": "piece",
                    "contentPartId": "headline",
                    "width": 180,
                    "height": 60,
                    "durationFrames": 30,
                },
            ]
        )
    return ContextualPlanRequestV2.model_validate(
        {
            "semanticVerificationPolicy": "canonical_demonstration_v1",
            "expectedDocumentRevision": 1,
            "intent": {"objective": "Demonstrar adaptação"},
            "contentReferences": [
                {
                    "id": "piece",
                    "purpose": "Peça canônica",
                    "parts": [
                        {"id": "photo", "role": "primary_media", "assetId": "asset-photo"},
                        {"id": "headline", "role": "title", "text": "Uma ideia clara"},
                    ],
                }
            ],
            "scenes": [
                {
                    "id": "adapt",
                    "purpose": "Adaptar",
                    "durationFrames": 30,
                    "contentReferenceIds": ["piece"],
                    "elements": elements,
                    "verification": ["Mesma peça visível nos dois formatos"],
                    "compositions": [
                        {
                            "id": "formats",
                            "family": "format_transformation",
                            "targetIds": ["portrait", "square"],
                            "purpose": "Adaptar",
                            "expectedResult": "Dois formatos",
                            "actionFrames": 10,
                            "continuityKey": "piece",
                            "viewportFormats": ["portrait", "square"],
                        }
                    ],
                    "semanticAssertions": [
                        {
                            "id": "same-piece",
                            "kind": "format_adaptation",
                            "objectId": "piece",
                            "initialState": "vertical",
                            "event": "reorganiza",
                            "finalState": "quadrado",
                            "startFrame": 0,
                            "endFrameExclusive": 30,
                            "targetIds": ["portrait", "square"],
                            "requiredPartIds": ["photo", "headline"],
                            "evidenceRequired": "temporal_sequence",
                        }
                    ],
                }
            ],
        }
    )


@pytest.mark.parametrize("hide_title", [False, True])
def test_geometry_only_canonical_claim_does_not_pass_pixel_semantics(tmp_path, hide_title):
    output = tmp_path / "visual.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=#101820:s=320x480:r=30:d=1",
            "-c:v",
            "libx264",
            str(output),
        ],
        check=True,
        timeout=30,
    )
    elements = []
    for semantic_id in ("portrait", "portrait-media", "portrait-title", "square", "square-media", "square-title"):
        elements.append(
            {
                "semanticId": semantic_id,
                "present": True,
                "visible": not (hide_title and semantic_id == "square-title"),
                "opacity": 1,
                "bounds": {"x": 10, "y": 10, "width": 100, "height": 100},
            }
        )
    checks = {"geometrySamples": [{"frame": frame, "elements": elements} for frame in (0, 14, 29)]}

    audit = observe_visual_states(output, canonical_direction(), renderer_checks=checks)
    evidence = audit["semanticVerification"]["evidence"][0]

    assert evidence["status"] == "failed"
    assert audit["semanticVerification"]["status"] == "failed"
    assert evidence["completeContentVisibility"]["square"] == ([True] * 3 if not hide_title else [False] * 3)
    if not hide_title:
        assert {item["status"] for item in evidence["pixelEvidence"].values()} == {"flat_placeholder"}


def test_staggered_canonical_states_are_sampled_inside_their_active_ranges(tmp_path):
    output = tmp_path / "visual.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=#101820:s=320x480:r=30:d=8",
            "-c:v",
            "libx264",
            str(output),
        ],
        check=True,
        timeout=30,
    )
    raw = canonical_direction().model_dump(mode="json", by_alias=True)
    scene = raw["scenes"][0]
    scene["durationFrames"] = 240
    assertion = scene["semanticAssertions"][0]
    assertion["endFrameExclusive"] = 240
    assertion["evidenceRequired"] = "rendered_geometry"
    for element in scene["elements"]:
        if element["id"].startswith("portrait"):
            element["startFrame"] = 0
            element["durationFrames"] = 101
        else:
            element["startFrame"] = 100
            element["durationFrames"] = 140
    direction = ContextualPlanRequestV2.model_validate(raw)
    semantic_ids = (
        "portrait",
        "portrait-media",
        "portrait-title",
        "square",
        "square-media",
        "square-title",
    )
    samples = []
    for frame in (0, 50, 120, 170, 239):
        elements = []
        for semantic_id in semantic_ids:
            portrait = semantic_id.startswith("portrait")
            visible = (portrait and 0 < frame < 101) or (not portrait and 100 <= frame < 240)
            elements.append(
                {
                    "semanticId": semantic_id,
                    "present": True,
                    "visible": visible,
                    "opacity": 1 if visible else 0,
                    "bounds": {
                        "x": 10,
                        "y": 10,
                        "width": 64 if semantic_id.startswith("portrait") and semantic_id == "portrait" else 100,
                        "height": 100,
                    },
                }
            )
        samples.append({"frame": frame, "elements": elements})

    audit = observe_visual_states(output, direction, renderer_checks={"geometrySamples": samples})
    evidence = audit["semanticVerification"]["evidence"][0]

    assert 50 in evidence["checkpoints"]
    assert 170 in evidence["checkpoints"]
    assert evidence["status"] == "passed"


def test_exported_pixels_and_order_prove_canonical_format_adaptation(tmp_path):
    portrait = Image.new("RGB", (320, 480), "#101820")
    portrait_draw = ImageDraw.Draw(portrait)
    portrait_draw.rounded_rectangle((40, 40, 168, 240), radius=8, fill="#f3ead7")
    portrait_draw.rectangle((54, 98, 154, 198), fill="#9d552f")
    portrait_draw.ellipse((79, 112, 129, 170), fill="#2a1712")
    portrait_draw.rectangle((54, 57, 154, 86), fill="#ffffff")
    portrait_draw.text((59, 66), "IDEIA", fill="#151515")
    square = Image.new("RGB", (320, 480), "#101820")
    square_draw = ImageDraw.Draw(square)
    square_draw.rounded_rectangle((60, 100, 260, 300), radius=8, fill="#f3ead7")
    square_draw.rectangle((80, 164, 240, 264), fill="#9d552f")
    square_draw.ellipse((135, 178, 185, 236), fill="#2a1712")
    square_draw.rectangle((80, 121, 240, 150), fill="#ffffff")
    square_draw.text((86, 130), "IDEIA", fill="#151515")
    portrait_path, square_path = tmp_path / "portrait.png", tmp_path / "square.png"
    portrait.save(portrait_path)
    square.save(square_path)
    output = tmp_path / "adaptation.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-loop",
            "1",
            "-t",
            "4",
            "-i",
            str(portrait_path),
            "-loop",
            "1",
            "-t",
            "4",
            "-i",
            str(square_path),
            "-filter_complex",
            "[0:v][1:v]concat=n=2:v=1:a=0,fps=30",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(output),
        ],
        check=True,
        timeout=30,
    )
    raw = canonical_direction().model_dump(mode="json", by_alias=True)
    scene = raw["scenes"][0]
    scene["durationFrames"] = 240
    scene["semanticAssertions"][0]["endFrameExclusive"] = 240
    for element in scene["elements"]:
        is_portrait = element["id"].startswith("portrait")
        element["startFrame"] = 0 if is_portrait else 120
        element["durationFrames"] = 120
    direction = ContextualPlanRequestV2.model_validate(raw)

    def geometry(semantic_id, visible):
        portrait_state = semantic_id.startswith("portrait")
        if semantic_id in {"portrait", "square"}:
            bounds = (
                {"x": 40, "y": 40, "width": 128, "height": 200}
                if portrait_state
                else {"x": 60, "y": 100, "width": 200, "height": 200}
            )
        elif semantic_id.endswith("media"):
            bounds = (
                {"x": 54, "y": 98, "width": 100, "height": 100}
                if portrait_state
                else {"x": 80, "y": 164, "width": 160, "height": 100}
            )
        else:
            bounds = (
                {"x": 54, "y": 57, "width": 100, "height": 29}
                if portrait_state
                else {"x": 80, "y": 121, "width": 160, "height": 29}
            )
        return {
            "semanticId": semantic_id,
            "present": True,
            "visible": visible,
            "opacity": 1 if visible else 0,
            "bounds": bounds,
        }

    semantic_ids = (
        "portrait",
        "portrait-media",
        "portrait-title",
        "square",
        "square-media",
        "square-title",
    )
    samples = []
    for frame in (0, 50, 119, 120, 170, 239):
        samples.append(
            {
                "frame": frame,
                "elements": [
                    geometry(
                        semantic_id,
                        (semantic_id.startswith("portrait") and frame < 120)
                        or (semantic_id.startswith("square") and frame >= 120),
                    )
                    for semantic_id in semantic_ids
                ],
            }
        )

    audit = observe_visual_states(output, direction, renderer_checks={"geometrySamples": samples})
    evidence = audit["semanticVerification"]["evidence"][0]

    assert evidence["status"] == "passed", (
        evidence["reason"],
        evidence["pixelEvidence"],
        evidence["primaryMediaSimilarity"],
        evidence["observedStateFrames"],
    )
    assert evidence["sequenceOrdered"] is True
    assert evidence["observedViewportAspects"] == {"portrait": 0.64, "square": 1.0}
    assert all(item["status"] == "observed" for item in evidence["pixelEvidence"].values())
    assert evidence["primaryMediaSimilarity"] >= 0.52


@pytest.mark.parametrize("interface_event,expected", [("open", "failed"), ("insert", "passed")])
def test_feed_insertion_requires_canonical_pixels_and_vertical_trajectory(
    tmp_path, interface_event, expected
):
    frame = Image.new("RGB", (320, 480), "#101820")
    draw = ImageDraw.Draw(frame)
    draw.rounded_rectangle((50, 140, 270, 340), radius=8, fill="#f3ead7")
    draw.rectangle((70, 205, 250, 315), fill="#9d552f")
    draw.ellipse((135, 220, 185, 280), fill="#2a1712")
    draw.rectangle((70, 160, 250, 193), fill="#ffffff")
    draw.text((78, 170), "IDEIA", fill="#151515")
    source = tmp_path / "feed.png"
    output = tmp_path / f"feed-{interface_event}.mp4"
    frame.save(source)
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-loop",
            "1",
            "-t",
            "1",
            "-i",
            str(source),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(output),
        ],
        check=True,
        timeout=30,
    )
    direction = ContextualPlanRequestV2.model_validate(
        {
            "semanticVerificationPolicy": "canonical_demonstration_v1",
            "expectedDocumentRevision": 1,
            "intent": {"objective": "Mostrar a peça entrando no feed"},
            "contentReferences": [
                {
                    "id": "piece",
                    "purpose": "Peça reconhecível",
                    "parts": [
                        {"id": "photo", "role": "primary_media", "assetId": "photo"},
                        {"id": "headline", "role": "title", "text": "IDEIA"},
                    ],
                }
            ],
            "scenes": [
                {
                    "id": "feed",
                    "purpose": "Inserir no feed",
                    "durationFrames": 30,
                    "verification": ["A peça entra por movimento vertical e permanece reconhecível"],
                    "contentReferenceIds": ["piece"],
                    "elements": [
                        {
                            "id": "feed-item",
                            "kind": "group",
                            "purpose": "Publicação",
                            "contentReferenceId": "piece",
                            "width": 220,
                            "height": 200,
                            "durationFrames": 30,
                        },
                        {
                            "id": "feed-photo",
                            "kind": "image",
                            "purpose": "Imagem",
                            "assetId": "photo",
                            "parentId": "feed-item",
                            "contentReferenceId": "piece",
                            "contentPartId": "photo",
                            "width": 180,
                            "height": 110,
                            "durationFrames": 30,
                        },
                        {
                            "id": "feed-headline",
                            "kind": "text",
                            "purpose": "Título",
                            "text": "IDEIA",
                            "parentId": "feed-item",
                            "contentReferenceId": "piece",
                            "contentPartId": "headline",
                            "width": 180,
                            "height": 33,
                            "durationFrames": 30,
                        },
                    ],
                    "compositions": [
                        {
                            "id": "feed-interface",
                            "family": "demonstrative_interface",
                            "targetIds": ["feed-item"],
                            "purpose": "Inserir a publicação",
                            "expectedResult": "A publicação entra no feed",
                            "actionFrames": 20,
                            "interfaceEvents": [interface_event],
                        }
                    ],
                    "semanticAssertions": [
                        {
                            "id": "piece-enters-feed",
                            "kind": "feed_insertion",
                            "objectId": "piece",
                            "initialState": "Fora do feed",
                            "event": "Entra verticalmente",
                            "finalState": "Visível no feed",
                            "startFrame": 0,
                            "endFrameExclusive": 30,
                            "targetIds": ["feed-item"],
                            "requiredPartIds": ["photo", "headline"],
                            "evidenceRequired": "temporal_sequence",
                        }
                    ],
                }
            ],
        }
    )
    samples = []
    for sample_frame, visible, y in ((0, False, 236), (14, True, 170), (29, True, 140)):
        samples.append(
            {
                "frame": sample_frame,
                "elements": [
                    {
                        "semanticId": "feed-item",
                        "present": True,
                        "visible": visible,
                        "opacity": 1 if visible else 0,
                        "bounds": {"x": 50, "y": y, "width": 220, "height": 200},
                    },
                    {
                        "semanticId": "feed-photo",
                        "present": True,
                        "visible": visible,
                        "opacity": 1 if visible else 0,
                        "bounds": {"x": 70, "y": 205, "width": 180, "height": 110},
                    },
                    {
                        "semanticId": "feed-headline",
                        "present": True,
                        "visible": visible,
                        "opacity": 1 if visible else 0,
                        "bounds": {"x": 70, "y": 160, "width": 180, "height": 33},
                    },
                ],
            }
        )
    if interface_event == "open":
        for sample in samples:
            sample["elements"][0]["bounds"]["y"] = 140

    audit = observe_visual_states(output, direction, renderer_checks={"geometrySamples": samples})
    evidence = audit["semanticVerification"]["evidence"][0]

    assert evidence["status"] == expected
    assert evidence["interfaceEvent"] == interface_event
    assert all(item["status"] == "observed" for item in evidence["pixelEvidence"].values())
