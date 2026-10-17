"""Regression coverage for editorial constraints and transcript evidence."""
# ruff: noqa: F811

import json

from test_contextual_editing import attach_transcript, media, project  # noqa: F401
from test_editing_resources import enable, headers

from app.database import SessionLocal
from app.models import StudioGenerationJob
from app.providers.studios.gemini_editing import GeminiEditingProvider
from app.services.studios.jobs import execute_job_once


def run_plan(client, project, monkeypatch, direction, output):
    enable(monkeypatch)
    seen = []

    def planning(self, model, context, media):
        seen.append(context)
        return {"candidates": [{"content": {"parts": [{"text": json.dumps(output)}]}}]}

    monkeypatch.setattr(GeminiEditingProvider, "plan", planning)
    response = client.post(
        f"/api/v1/studios/v1/documents/{project['document']}/editing-ai-jobs",
        headers=headers(project),
        json={
            "expectedDocumentRevision": 1,
            "operation": "plan",
            "prompt": "Planejar edição preservando as instruções do usuário",
            "direction": direction,
        },
    )
    assert response.status_code == 202, response.text
    identifier = response.json()["id"]
    with SessionLocal() as db:
        record = db.get(StudioGenerationJob, identifier)
        execute_job_once(db, record)
        assert record.status == "succeeded", record.error_message
        return record.result_payload["plan"], seen[0]


def direction(**extra):
    return {"expectedDocumentRevision": 1, "intent": {"objective": "Explicar com precisão"}, **extra}


def test_required_technique_must_survive_model_omission(client, project, monkeypatch):
    plan, _ = run_plan(
        client,
        project,
        monkeypatch,
        direction(requiredTechniques=["tracking"]),
        {"beats": [], "requiredTechniques": [], "rationale": "Conservar material"},
    )
    assert plan["status"] == "awaiting_choice", {
        "observed_status": plan["status"],
        "blockers": plan["blockers"],
        "expected": "Unsupported user requirement must not disappear",
    }


def transcript_direction(project):
    transcript = attach_transcript(project)
    return direction(
        beats=[
            {
                "id": "user-beat",
                "clipId": "clip",
                "purpose": "Preservar a ressalva",
                "transcriptId": transcript.id,
                "transcriptRevision": 1,
                "captionFromTranscript": True,
            }
        ]
    )


def test_user_caption_binding_must_survive_omitted_beat(client, project, monkeypatch):
    plan, _ = run_plan(
        client, project, monkeypatch, transcript_direction(project), {"beats": [], "rationale": "Conservar material"}
    )
    cues = [
        cue
        for track in plan["draftDocument"]["composition"]["mediaTimeline"]["tracks"]
        if track["kind"] == "caption"
        for cue in track["cues"]
    ]
    assert any(cue["text"] == "Não garante resultado." for cue in cues), {
        "observed_status": plan["status"],
        "cues": cues,
        "sourceTranscripts": plan["sourceTranscripts"],
    }


def test_planner_must_receive_bound_transcript_content(client, project, monkeypatch):
    _, context = run_plan(
        client, project, monkeypatch, transcript_direction(project), {"beats": [], "rationale": "Conservar material"}
    )
    assert "Não garante resultado." in json.dumps(context, ensure_ascii=False), {
        "contextKeys": list(context),
        "sampling": context["sampling"],
        "expected": "Actual reviewed transcript must reach editorial reasoning",
    }


def test_generated_text_must_not_contradict_locked_fact(client, project, monkeypatch):
    plan, _ = run_plan(
        client,
        project,
        monkeypatch,
        direction(
            intent={
                "objective": "Explicar com precisão",
                "script": "Não garante resultado.",
                "lockedFacts": ["Não garante resultado."],
            }
        ),
        {
            "beats": [
                {
                    "id": "ai-beat",
                    "clipId": "clip",
                    "purpose": "Resumir informação",
                    "onScreenText": "Garante resultado.",
                }
            ],
            "rationale": "Resumo factual",
        },
    )
    cues = [
        cue["text"]
        for track in plan["draftDocument"]["composition"]["mediaTimeline"]["tracks"]
        if track["kind"] == "caption"
        for cue in track["cues"]
    ]
    assert plan["status"] == "awaiting_choice" or "Garante resultado." not in cues, {
        "observed_status": plan["status"],
        "lockedFacts": plan["intent"]["lockedFacts"],
        "outputText": cues,
    }
