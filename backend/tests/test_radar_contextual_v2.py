from __future__ import annotations

from datetime import UTC, datetime

from conftest import register

from app.config import get_settings
from app.database import SessionLocal
from app.domain.radar.evaluation import RankingExample, evaluate_ranking
from app.models import BrandProfile, ExternalSignal, FeedbackEvent, RadarShadowEvaluation
from app.services.radar_contextual_v2 import evaluate_candidate_v2


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def configure_brand(client, token: str, workspace: str) -> None:
    profile = client.get("/api/v1/bootstrap", headers=auth(token)).json()["workspaces"][0]["brandProfile"]
    profile.update(
        {
            "industry": "cafés especiais",
            "targetAudience": "pessoas que valorizam café especial e origem brasileira",
            "keywords": ["café", "origem", "produtores"],
            "products": [{"name": "Café de origem", "description": "cafés especiais brasileiros"}],
            "pillars": ["origem brasileira", "produtores", "café especial"],
            "prohibitedTopics": ["apostas"],
            "watchlist": {"brainRevision": 2, "topics": ["café especial"]},
        }
    )
    response = client.patch(
        f"/api/v1/workspaces/{workspace}",
        headers=auth(token),
        json={"brandProfile": profile},
    )
    assert response.status_code == 200


def ingest(client, token: str, workspace: str, suffix: str, *, metrics: dict | None = None) -> dict:
    response = client.post(
        "/api/v1/radar/signals",
        headers=auth(token),
        json={
            "workspaceId": workspace,
            "source": f"Fonte independente {suffix}",
            "sourceType": "manual",
            "providerTrace": {"provider": "manual-fixture", "providerVersion": "1"},
            "url": f"https://example.com/cafe-origem-{suffix}",
            "title": f"Produtores de café especial ampliam origem brasileira {suffix}",
            "summary": "Café especial, produtores e origem brasileira ganham atenção.",
            "publishedAt": datetime.now(UTC).isoformat(),
            "topics": ["café especial", "produtores", "origem brasileira"],
            "metrics": metrics or {},
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_v2_marks_unobserved_metrics_unknown_and_gates_single_source(client):
    token, workspace = register(client, "radar-v2-unknown@example.com", "Radar V2 Unknown")
    configure_brand(client, token, workspace)
    signal_data = ingest(client, token, workspace, "única")
    with SessionLocal() as db:
        signal = db.get(ExternalSignal, signal_data["id"])
        brand = db.query(BrandProfile).filter(BrandProfile.workspace_id == workspace).one()
        candidate = evaluate_candidate_v2(db, signal, brand)
    assert candidate.dimensions["momentum"].status == "unknown"
    assert candidate.dimensions["novelty"].status == "unknown"
    assert candidate.penalties["saturation"].status == "unknown"
    evidence_gate = next(gate for gate in candidate.gates if gate.gate == "evidence_sufficiency")
    assert evidence_gate.status == "block"
    assert candidate.eligible is False
    assert "menos de duas evidências" in (candidate.rejection_reason or "")


def test_shadow_mode_preserves_v11_and_records_one_candidate_per_cluster(client, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "radar_contextual_v2_enabled", True)
    monkeypatch.setattr(settings, "radar_contextual_v2_shadow_mode", True)
    token, workspace = register(client, "radar-v2-shadow@example.com", "Radar V2 Shadow")
    other_token, _ = register(client, "radar-v2-shadow-other@example.com", "Radar V2 Other")
    configure_brand(client, token, workspace)
    first = ingest(client, token, workspace, "evento")
    second = ingest(client, token, workspace, "eventos")
    assert first["clusterKey"] == second["clusterKey"]

    ranked = client.post(
        "/api/v1/radar/rank",
        headers=auth(token),
        json={"workspaceId": workspace},
    )
    assert ranked.status_code == 200, ranked.text
    assert {item["scoreVersion"] for item in ranked.json()} == {"radar-v1.1"}
    with SessionLocal() as db:
        rows = db.query(RadarShadowEvaluation).filter(RadarShadowEvaluation.workspace_id == workspace).all()
    assert len(rows) == 1
    assert rows[0].candidate_version == "radar-v2.0-shadow"
    assert rows[0].candidate["penalties"]["saturation"]["status"] == "unknown"

    audit = client.get(
        "/api/v1/radar/shadow-evaluations",
        headers=auth(token),
        params={"workspace_id": workspace},
    )
    assert audit.status_code == 200 and len(audit.json()) == 1
    assert (
        client.get(
            "/api/v1/radar/shadow-evaluations",
            headers=auth(other_token),
            params={"workspace_id": workspace},
        ).status_code
        == 404
    )

    opportunity = ranked.json()[0]
    feedback = client.post(
        "/api/v1/radar/feedback",
        headers=auth(token),
        json={"workspaceId": workspace, "opportunityId": opportunity["id"], "eventType": "chosen"},
    )
    assert feedback.status_code == 204
    with SessionLocal() as db:
        event = db.query(FeedbackEvent).filter(FeedbackEvent.opportunity_id == opportunity["id"]).one()
    assert event.schema_version == "feedback.v2"
    assert event.opportunity_score_version == "radar-v1.1"


def test_offline_evaluation_reports_ranking_and_duplicate_metrics():
    metrics = evaluate_ranking(
        [
            RankingExample("a", "cluster-1", 90, 3, True, True),
            RankingExample("b", "cluster-1", 85, 2, True, False),
            RankingExample("c", "cluster-2", 70, 0, False, False),
        ],
        k=3,
    )
    assert metrics["evaluationVersion"] == "radar-eval-v1"
    assert metrics["precisionAtK"] == 0.6667
    assert metrics["duplicateClusterRateAtK"] == 0.3333
    assert metrics["eligibilityAgreement"] == 0.6667
