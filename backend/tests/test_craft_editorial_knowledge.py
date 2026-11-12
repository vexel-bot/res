from sqlalchemy import select
import pytest

from conftest import register
from app.database import SessionLocal
from app.models import KnowledgeDocument
from app.services.studios import craft_direction, craft_learning, editing_repertoire


def document(client, token, workspace, title="Projeto editorial"):
    response = client.post("/api/v1/studios/v1/documents", headers={"Authorization": "Bearer " + token}, json={
        "workspaceId": workspace, "title": title, "contentType": "video", "brandRevision": 1,
        "brief": {"objective": "Teste do guia editorial", "audience": "QA"},
        "composition": {"pages": [{"id": "main", "width": 320, "height": 320, "durationMs": 2000, "layers": []}]},
    })
    assert response.status_code == 201, response.text
    return response.json()


def test_all_editorial_libraries_are_searchable_and_keep_their_evidence(client):
    token, workspace = register(client, "editorial-repertoire@example.com")
    _, foreign = register(client, "editorial-foreign@example.com")
    cards = craft_direction.repertoire()
    assert {"show-action", "protect-interface", "readable-type", "honest-audio", "cutout-depth"} <= {
        card["id"] for card in craft_direction.reference_index()
    }
    assert len([card for card in cards.values() if card.get("kind") == "editing_language"]) == 15
    assert len([card for card in cards if card.startswith("research.")]) == 37
    target = cards["research.target.orbita.reference_triad"]
    assert target["scope"]["universalDefault"] is False
    assert target["primaryReference"]["creator"] == "@paulo.ia"
    assert "Muted playback; no auditory assessment" in target["sourceEvidence"]["limits"]
    legacy = next(card for card in cards.values() if "operations" in card)
    assert craft_direction.references([legacy["id"]])[legacy["id"]]["operations"] == legacy["operations"]
    assert legacy["operationBinding"]["requiresNativeAdaptation"]
    lesson = craft_direction.references(["orbita-reveal-protect-title"])["orbita-reveal-protect-title"]
    assert lesson["state"] == "reproduced locally"
    assert "abertura lateral" in lesson["demonstration"]["transferContraindication"]
    with SessionLocal() as db:
        targets = craft_direction.search_repertoire(db, workspace, "ÓRBITA meta referência cinematográfica", limit=6)
        assert target["id"] in {card["id"] for card in targets["matches"]}
        exercise = craft_direction.search_repertoire(db, workspace, "ÓRBITA recuo moldura colisão", limit=3)
        assert "orbita-reveal-protect-title" in {card["id"] for card in exercise["matches"]}
        technique = editing_repertoire.seed_techniques()[0].model_dump(mode="json", by_alias=True)
        technique.update(id="tenant-zebrafoco", purpose="zebrafoco universo exclusivo")
        db.add(KnowledgeDocument(workspace_id=foreign, title="Foreign lesson", source_type="editing-technique",
                                 content_hash="a" * 64, status="ready", document_metadata={"technique": technique}))
        db.commit()
        assert not any("zebrafoco" in str(card) for card in craft_direction.search_repertoire(db, workspace, "zebrafoco")["matches"])
        assert any("zebrafoco" in str(card) for card in craft_direction.search_repertoire(db, foreign, "zebrafoco")["matches"])


def test_guide_versioning_transfers_approved_preferences_and_rejects_stale_writes(client):
    token, workspace = register(client, "editorial-guide@example.com")
    first = document(client, token, workspace)
    second = document(client, token, workspace, "Próximo projeto")
    headers = {"Authorization": "Bearer " + token}
    base = "/api/v1/studios/v1/documents/"
    lesson = {"situation": "A oferta fica sem contexto", "correction": "Situar o evento durante o desenvolvimento",
              "useWhen": ["Anúncio de evento"], "avoidWhen": ["Suspense deliberado solicitado pelo cliente"]}
    body = {"expectedRevision": first["revision"], "expectedVersion": 0, "scope": "workspace", "lesson": lesson}
    saved = client.post(base + first["documentId"] + "/craft/editorial-guide", headers=headers, json=body)
    assert saved.status_code == 200, saved.text
    assert saved.json()["lessons"][0]["status"] == "approved"
    stale = client.post(base + first["documentId"] + "/craft/editorial-guide", headers=headers, json=body)
    assert stale.status_code == 409
    following = client.get(base + second["documentId"] + "/craft/editorial-guide", headers=headers)
    assert following.status_code == 200, following.text
    shared = next(guide for guide in following.json()["guides"] if guide["scope"] == "workspace")
    assert shared["version"] == 1 and shared["lessons"][0]["correction"] == lesson["correction"]
    foreign_token, foreign = register(client, "editorial-guide-foreign@example.com")
    unauthorized = client.get(base + first["documentId"] + "/craft/editorial-guide",
                              headers={"Authorization": "Bearer " + foreign_token})
    assert unauthorized.status_code in {403, 404}
    with SessionLocal() as db:
        assert craft_learning.style_guide(db, foreign)["lessons"] == []
        candidate = craft_learning.save_editorial_lesson(db, workspace, lesson, 0, "document", first["documentId"])
        db.commit()
        assert candidate["lessons"][0]["status"] == "candidate"
        actor = client.get("/api/v1/bootstrap", headers=headers).json()["user"]["id"]
        approved = craft_learning.save_editorial_lesson(
            db, workspace, candidate["lessons"][0], 1, "document", first["documentId"], approved=True, actor_id=actor,
        )
        db.commit()
        assert approved["version"] == 2 and approved["lessons"][0]["status"] == "approved"
        with pytest.raises(ValueError, match="approved_lesson_requires_user"):
            craft_learning.save_editorial_lesson(db, workspace, approved["lessons"][0], 2, "document", first["documentId"])
        previous = craft_learning.style_guide(db, workspace, "document", first["documentId"], version=1)
        assert previous["lessons"][0]["status"] == "candidate"
        context = craft_direction.editorial_context(db, workspace, second["documentId"], "evento")
        assert any(guide["scope"] == "workspace" and guide["version"] == 1 for guide in context["styleGuides"])
        long_context = craft_direction.editorial_context(db, workspace, second["documentId"], "evento e montagem " * 300)
        assert long_context["retrievalQueryCoverage"]["searchedCharacters"] == 2000
        assert long_context["retrievalQueryCoverage"]["sourceCharacters"] > 2000
        assert db.scalar(select(KnowledgeDocument).where(KnowledgeDocument.workspace_id == workspace))


def test_review_artifact_keeps_distinct_evidence_pages_for_the_same_video(client, tmp_path):
    from app.models import CreativeDocument
    from app.services.studios.craft_editorial import persist_review
    token, workspace = register(client, "review-evidence@example.com")
    item = document(client, token, workspace)
    path = tmp_path / "metadata-fixture.mp4"
    path.write_bytes(b"fixture-for-storage-identity-test")
    with SessionLocal() as db:
        record = db.get(CreativeDocument, item["documentId"])
        first_report = {"artifact": {"mediaType": "video/mp4"}, "visual": {"page": 0}}
        first = persist_review(db, record, {"path": path, "report": first_report}, job_id="job", draft_batch=2)
        db.commit()
        second = persist_review(db, record, {"path": path, "report": {**first_report, "visual": {"page": 1}}}, job_id="job", draft_batch=2)
        db.commit()
        assert first["assetId"] != second["assetId"]
        replay = persist_review(db, record, {"path": path, "report": first_report}, job_id="job", draft_batch=2)
        assert replay["assetId"] == first["assetId"]
