"""Legacy payload validation and routing to the native Craft editing entry point."""
from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from test_local_agents import BASE, prepare
from test_motion_editorial_workflow import seed
from app.database import SessionLocal
from app.models import StudioGenerationJob
from app.services.studios import production_editing
from app.studio_app import app


def test_paid_editorial_route_directs_to_craft_before_creating_a_job(monkeypatch, tmp_path):
    auth = prepare(monkeypatch, tmp_path)
    with TestClient(app) as client:
        _, _, document, _ = seed(client, auth)
        response = client.post(
            BASE + f"/documents/{document['documentId']}/agent-tasks",
            headers={**auth, "Idempotency-Key": "legacy-editorial-native-route"},
            json={
                "expectedRevision": document["revision"],
                "instruction": "Monte o anúncio no editor nativo.",
                "planner": "editorial_experimental",
                "editorial": {
                    "variant": "orchestrated", "connectionId": "unused-provider-connection",
                    "cutEffort": "high", "openEdit": True, "purpose": "advertisement",
                    "references": [{"assetId": "unused-reference", "durationSeconds": 2}],
                },
            },
        )
        assert response.status_code == 422, response.text
        assert response.json()["detail"]["code"] == "craft_native_ai_required"
        with SessionLocal() as db:
            assert db.query(StudioGenerationJob).count() == 0


def free_cut(document):
    composition = deepcopy(document["composition"])
    page = composition["pages"][0]
    page["background"] = "#152339"  # A color outside the old three preset palettes.
    product = next(layer for layer in page["layers"] if layer["kind"] == "image")
    product["properties"].update(
        keyframes=[
            {"property": "x", "frame": 0, "value": -40},
            {"property": "x", "frame": 14, "value": 0, "easing": "ease-out"},
        ]
    )
    page["layers"] = [product]
    decisions = []
    for index, text in enumerate(("Onde ficou?", "Separe", "Encontre", "Veja o organizador")):
        identifier = f"free-title-{index}"
        page["layers"].append(
            {
                "id": identifier,
                "kind": "text",
                "x": 20,
                "y": 30,
                "width": 280,
                "height": 70,
                "zIndex": 5,
                "properties": {
                    "schemaVersion": "studio.local-layer.v1",
                    "text": text,
                    "color": "#FFFFFF",
                    "fontSize": 22,
                    "startFrame": index * 12,
                    "durationFrames": 12,
                },
            }
        )
        decisions.append(
            {
                "startFrame": index * 12,
                "endFrame": (index + 1) * 12,
                "viewerUnderstands": "O mesmo objeto fica reconhecível enquanto a intenção muda.",
                "executedIds": [identifier, product["id"]],
                "referenceObservation": "A referência mantém uma figura identificável sobre planos de cor.",
            }
        )
    return {
        "composition": composition,
        "decisions": decisions,
        "gaps": ["Sem filmagem de uso real do produto."],
        "rationale": "Quatro momentos editáveis, sem o modelo anterior de três cenas.",
    }


def test_new_flow_rejects_legacy_template_and_nonexecuted_direction(monkeypatch, tmp_path):
    from pydantic import ValidationError

    from app.domain.studios.agents import EditorialExperiment

    with pytest.raises(ValidationError):
        EditorialExperiment(
            openEdit=True,
            connectionId="connection",
            cutEffort="high",
            sceneDirection=True,
            references=[{"assetId": "ref"}],
        )
    auth = prepare(monkeypatch, tmp_path)
    with TestClient(app) as client:
        _, _, document, _ = seed(client, auth)
        cut = free_cut(document)
        cut["decisions"][0]["executedIds"] = ["imagined-effect"]
        with SessionLocal() as db, pytest.raises(ValueError, match="direction_not_executed"):
            from app.domain.studios.contracts import CreativeDocumentV1

            production_editing.validate_cut(
                db, CreativeDocumentV1.model_validate(document), production_editing.OpenCut.model_validate(cut)
            )
        for invisible, inactive in ((True, False), (False, True)):
            cut = free_cut(document)
            if invisible:
                cut["composition"]["pages"][0]["layers"][0]["visible"] = False
            if inactive:
                cut["decisions"][0]["executedIds"] = ["free-title-3"]
            with SessionLocal() as db, pytest.raises(ValueError, match="direction_not_executed"):
                production_editing.validate_cut(
                    db, CreativeDocumentV1.model_validate(document), production_editing.OpenCut.model_validate(cut)
                )


def test_caption_reading_floor_is_not_silently_ignored():
    from app.domain.studios.contracts import CreativeCompositionV1, CreativeDocumentV1
    from app.services.studios.motion_editorial_review import caption_findings

    composition = CreativeCompositionV1.model_validate(
        {
            "pages": [{"id": "main", "width": 1080, "height": 1920, "layers": []}],
            "mediaTimeline": {
                "durationFrames": 48,
                "frameRate": {"numerator": 24, "denominator": 1},
                "tracks": [
                    {
                        "id": "titles",
                        "kind": "caption",
                        "cues": [
                            {
                                "id": "tiny",
                                "text": "Texto ilegível no celular",
                                "timeline": {"startFrame": 0, "durationFrames": 48},
                                "style": {"fontSize": 16},
                            }
                        ],
                    }
                ],
            },
        }
    )
    contract = CreativeDocumentV1.model_construct(composition=composition)
    assert caption_findings(contract) == [{"code": "caption_below_phone_floor", "cueId": "tiny", "frame": 0}]
