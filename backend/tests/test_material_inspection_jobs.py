# Reuse the isolated tenant and synthetic image fixtures. No external media or model calls.
# ruff: noqa: F811
import json

from test_contextual_editing import media as media
from test_contextual_editing import project as project
from test_editing_resources import enable, headers, upload

from app.database import SessionLocal
from app.models import StudioGenerationJob
from app.providers.studios.gemini_editing import GeminiEditingProvider
from app.services.studios.jobs import execute_job_once


def test_inspection_job_reads_unattached_candidate_and_persists_evidence(client, project, monkeypatch):
    enable(monkeypatch)
    resource = upload(client, project, kind="image").json()
    seen = []

    def inspect(self, model, context, images):
        seen.append(context)
        assert len(images) == 1
        assert images[0][0].is_file()
        assert "document" not in context
        response = {
            "description": "Orange rectangle",
            "confidence": 0.95,
            "uncertainty": "Only the supplied image was examined",
            "criteria": [
                {"index": 0, "result": "supported", "evidence": "Orange fill is visible", "sampleIndices": [0]}
            ],
        }
        return {"candidates": [{"content": {"parts": [{"text": json.dumps(response)}]}}]}

    monkeypatch.setattr(GeminiEditingProvider, "plan", inspect)
    payload = {
        "expectedDocumentRevision": 1,
        "operation": "plan",
        "prompt": "Inspect material",
        "direction": {"expectedDocumentRevision": 1, "intent": {"objective": "Show orange"}},
        "materialInspection": {
            "assetId": resource["id"],
            "checksum": resource["checksumSha256"],
            "purpose": "Show orange",
            "criteria": ["Orange rectangle"],
            "requiredSeconds": 3,
        },
    }
    url = f"/api/v1/studios/v1/documents/{project['document']}/editing-gemini-jobs"
    created = client.post(url, headers=headers(project), json=payload)
    assert created.status_code == 202, created.text
    replay = client.post(url, headers=headers(project), json=payload)
    assert replay.json()["id"] == created.json()["id"]
    with SessionLocal() as db:
        job = db.get(StudioGenerationJob, created.json()["id"])
        execute_job_once(db, job)
        assert job.status == "succeeded", job.error_message
        receipt = job.result_payload["materialInspection"]
        assert receipt["status"] == "accepted"
        assert receipt["humanReview"] == "pending"
        assert receipt["checksum"] == resource["checksumSha256"]
        assert receipt["samples"][0]["checksum"] == resource["checksumSha256"]
    assert len(seen) == 1
