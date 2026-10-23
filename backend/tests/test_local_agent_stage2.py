"""Stage 2 contracts and actual media execution; no LLM inference is claimed."""

import io
from copy import deepcopy

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from test_clicko_studio_bridge import headers
from test_local_agents import BASE, apply, create, plan, prepare

from app.database import SessionLocal
from app.models import StudioGenerationJob
from app.providers.studios import timeline_ffmpeg as ff
from app.services.studios.jobs import execute_job_once
from app.studio_app import app


def selected_plan(client, auth, doc, instruction, ids, key):
    response = client.post(
        BASE + f"/documents/{doc['documentId']}/agent-tasks",
        headers={**auth, "Idempotency-Key": key},
        json={"expectedRevision": doc["revision"], "instruction": instruction, "selectedLayerIds": ids},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_scope_ambiguity_real_delegation_history_and_replay(monkeypatch, tmp_path):
    auth = prepare(monkeypatch, tmp_path)
    with TestClient(app) as client:
        doc, _ = create(client, auth)
        task = plan(
            client,
            auth,
            doc,
            "Crie um motion design de 15 segundos sobre tecnologia e inovação, "
            "com três cenas, textos animados, cartões gráficos e transições suaves.",
        )
        assert task["result"]["inference"] == "none"
        assert task["result"]["delegations"] == ["audiovisual", "image"]
        assert task["requestedBy"] and task["history"][0]["type"] == "studio.agent.started"
        assert len([event for event in task["history"] if event["type"] == "studio.agent.delegated"]) == 6
        doc = apply(client, auth, doc, task)
        detail_path = BASE + f"/documents/{doc['documentId']}/agent-tasks/{task['id']}"
        detail = client.get(detail_path, headers=auth).json()
        assert detail["appliedRevision"] == 2
        assert detail["limits"]["externalBudgetUsd"] == 0
        assert client.get(detail_path, headers=headers(module="create-video", client="foreign")).status_code == 404
        assert client.get(detail_path).status_code == 401
        ambiguous = plan(client, auth, doc, "Troque a fonte do título", "ambiguous-title-font")
        assert not ambiguous["result"]["commands"]
        before = deepcopy(doc)
        selected = selected_plan(
            client, auth, doc, "Troque a fonte para regular do sistema", ["scene-2-title"], "selected-font-stage2"
        )
        doc = apply(client, auth, doc, selected)
        for old, new in zip(
            before["composition"]["pages"][0]["layers"], doc["composition"]["pages"][0]["layers"], strict=True
        ):
            if old["id"] == "scene-2-title":
                assert new["properties"]["fontWeight"] == 400
            else:
                assert old == new
        same = selected_plan(
            client, auth, before, "Troque a fonte para regular do sistema", ["scene-2-title"], "selected-font-stage2"
        )
        assert same["id"] == selected["id"]
        invalid = client.post(
            BASE + f"/documents/{doc['documentId']}/agent-tasks",
            headers={**auth, "Idempotency-Key": "invalid-selected-id"},
            json={
                "expectedRevision": doc["revision"],
                "instruction": "Adicione sombra",
                "selectedLayerIds": ["not-this-project"],
            },
        )
        assert invalid.status_code == 422


def test_scene_targeted_dynamic_transition_colors_and_duration_metadata(monkeypatch, tmp_path):
    auth = prepare(monkeypatch, tmp_path)
    with TestClient(app) as client:
        doc, _ = create(client, auth)
        doc = apply(client, auth, doc, plan(client, auth, doc, "Crie um motion de 15 segundos"))
        before = deepcopy(doc["composition"]["pages"][0]["layers"])
        for instruction, key in [
            ("Deixe a primeira cena mais dinâmica", "scene-dynamic-001"),
            ("Adicione uma transição suave na primeira cena", "scene-transition-001"),
            ("Mude a cor dos cartões para coral", "color-cards-coral-001"),
        ]:
            task = plan(client, auth, doc, instruction, key)
            assert task["result"]["commands"], task
            doc = apply(client, auth, doc, task)
        for layer in doc["composition"]["pages"][0]["layers"]:
            if layer["id"].startswith("scene-1-"):
                assert any(key["property"] == "scale" for key in layer["properties"]["keyframes"])
            elif layer["id"].endswith("title") or layer["id"].endswith("accent"):
                assert layer == next(row for row in before if row["id"] == layer["id"])
            if layer["id"].endswith("card"):
                assert layer["properties"]["fill"] == "#FF7F50"
        doc = apply(client, auth, doc, plan(client, auth, doc, "Mude a duração para 20 segundos", "retime-stage2"))
        scenes = doc["composition"]["narrative"]["localProduction"]["scenes"]
        assert scenes[-1]["startFrame"] + scenes[-1]["durationFrames"] == 480


@pytest.mark.skipif(not ff.capability()["available"], reason="Requires actual local FFmpeg")
def test_word_reveal_still_and_real_mp4_two_versions(monkeypatch, tmp_path):
    auth = prepare(monkeypatch, tmp_path)
    with TestClient(app) as client:
        doc, _ = create(client, auth)
        doc = apply(client, auth, doc, plan(client, auth, doc, "Crie um motion de 3 segundos"))
        task = selected_plan(
            client, auth, doc, "Faça o texto aparecer palavra por palavra", ["scene-1-title"], "word-reveal-plan-001"
        )
        assert task["status"] == "succeeded", task
        doc = apply(client, auth, doc, task)
        assert len(doc["composition"]["pages"][0]["layers"]) == 9

        def render(current, key):
            response = client.post(
                BASE + f"/video/documents/{current['documentId']}/render-jobs",
                headers={**auth, "Idempotency-Key": key},
                json={"expectedRevision": current["revision"]},
            )
            assert response.status_code == 202, response.text
            with SessionLocal() as db:
                job = db.get(StudioGenerationJob, response.json()["id"])
                assert execute_job_once(db, job) == "succeeded", job.error_message
                path = job.result_payload["downloadUrl"]
            content = client.get(path, headers=auth).content
            target = tmp_path / (key + ".mp4")
            target.write_bytes(content)
            assert float(ff.probe(target)["format"]["duration"]) == pytest.approx(3, abs=0.1)
            return content, path

        first, path = render(doc, "word-render-first")
        doc = apply(
            client,
            auth,
            doc,
            selected_plan(client, auth, doc, "Mude a cor do título para coral", ["scene-1-title"], "word-color-plan"),
        )
        second, _ = render(doc, "word-render-second")
        assert first != second
        assert client.get(path, headers=auth).content == first
        png = client.get(BASE + f"/documents/{doc['documentId']}/local-preview", headers=auth, params={"frame": 18})
        assert Image.open(io.BytesIO(png.content)).size == (320, 320)


def test_word_reveal_mask_grows_without_reflow():
    from app.domain.studios.contracts import CreativeLayerV1
    from app.providers.studios.local_composition import raster

    layer = CreativeLayerV1(
        id="title",
        kind="text",
        width=300,
        height=140,
        properties={
            "schemaVersion": "studio.local-layer.v1",
            "text": "Tecnologia e inovação",
            "fontSize": 26,
            "textReveal": "words",
            "wordStaggerFrames": 6,
        },
    )
    first, full = raster(layer, {}, 0), raster(layer, {}, 18)
    a, b = first.getchannel("A"), full.getchannel("A")
    assert sum(a.getdata()) < sum(b.getdata())
    assert all(x <= y for x, y in zip(a.getdata(), b.getdata(), strict=True))


def test_word_layout_uses_shared_baseline_for_short_words():
    from app.domain.studios.contracts import CreativeLayerV1
    from app.domain.studios.local_composition import LocalLayerStyle
    from app.providers.studios.local_composition import raster, text_layout

    layer = CreativeLayerV1(
        id="baseline",
        kind="text",
        width=300,
        height=140,
        properties={"schemaVersion": "studio.local-layer.v1", "text": "Ag e", "fontSize": 42},
    )
    style = LocalLayerStyle.model_validate(layer.properties)
    _face, runs = text_layout(layer, style)
    bitmap = raster(layer, {}).getchannel("A")
    first = bitmap.crop((0, 0, round(runs[0][1] + runs[0][3]), 140)).getbbox()
    second = bitmap.crop((round(runs[1][1]), 0, 300, 140)).getbbox()
    assert second[1] > first[1]  # Lowercase e must not float at the capital's ink top.


def test_shared_image_export_can_be_attached_to_motion_without_changing_original(monkeypatch, tmp_path):
    auth = prepare(monkeypatch, tmp_path, visual=True)
    video_auth = headers(module="create-video", client="local-agents")
    with TestClient(app) as client:
        image, body = create(client, auth, visual=True)
        image = apply(client, auth, image, plan(client, auth, image, 'Crie um cartão com título "Clicko"'))
        exported = client.post(
            BASE + f"/documents/{image['documentId']}/local-image-export",
            headers={**auth, "Idempotency-Key": "shared-png-export"},
            json={"expectedRevision": image["revision"]},
        ).json()
        original = client.get(exported["downloadUrl"], headers=auth).content
        motion, _ = create(client, video_auth, key="shared-motion-create")
        response = client.post(
            BASE + f"/documents/{motion['documentId']}/local-commands",
            headers={**video_auth, "Idempotency-Key": "shared-asset-attach"},
            json={
                "expectedRevision": 1,
                "commands": [
                    {"id": "asset.attach", "params": {"assetId": exported["assetId"]}},
                    {
                        "id": "layer.upsert",
                        "params": {
                            "layer": {
                                "id": "shared-graphic",
                                "name": "Composição do Image Studio",
                                "kind": "image",
                                "width": 320,
                                "height": 320,
                                "properties": {
                                    "schemaVersion": "studio.local-layer.v1",
                                    "assetId": exported["assetId"],
                                },
                            }
                        },
                    },
                ],
            },
        )
        assert response.status_code == 200, response.text
        assert client.get(exported["downloadUrl"], headers=video_auth).content == original
        assert response.json()["assets"][0]["checksum"]
