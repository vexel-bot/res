# Fixtures deliberately reused from the established API boundary tests.
# ruff: noqa: F811
from test_contextual_editing import media as media
from test_contextual_editing import project as project
from test_remotion_native import native_direction


def test_native_plan_apply_render_api_and_provider_binding(client, project, monkeypatch):
    from app.database import SessionLocal
    from app.models import CreativeDocument, StudioGenerationJob
    from app.providers.studios.remotion_render import (
        RemotionNativeContextualRenderProvider,
        RemotionNativeGraphicsProvider,
    )
    from app.providers.studios.video_render import VIDEO_RENDER_PROVIDERS
    from app.services.studios.compatibility import persist_contract, record_to_contract
    from app.services.studios.jobs import execute_job_once

    monkeypatch.setitem(
        VIDEO_RENDER_PROVIDERS,
        "remotion.contextual-v2",
        RemotionNativeContextualRenderProvider(
            RemotionNativeGraphicsProvider("node", "ffmpeg", 180),
            VIDEO_RENDER_PROVIDERS["builtin.ffmpeg-contextual-v1"],
        ),
    )
    monkeypatch.setattr("app.tasks.execute_studio_generation.delay", lambda *_: None)
    # This is a new B-roll composition, not a semantic edit of the fixture's interview.
    with SessionLocal() as db:
        record = db.get(CreativeDocument, project["document"])
        document = record_to_contract(record)
        document.composition.media_timeline.tracks = []
        persist_contract(record, document)
        db.commit()
    headers = {"Authorization": "Bearer " + project["token"], "Idempotency-Key": "native-api-plan"}
    base = f"/api/v1/studios/v1/documents/{project['document']}/editing-plans"
    response = client.post(
        base, headers=headers, json=native_direction(project["asset"]).model_dump(mode="json", by_alias=True)
    )
    assert response.status_code == 200, response.text
    plan = response.json()
    assert plan["status"] == "ready", plan["blockers"]
    response = client.post(
        base + "/" + plan["id"] + "/apply", headers=headers, json={"expectedPlanRevision": plan["revision"]}
    )
    assert response.status_code == 200, response.text
    body = {
        "workspaceId": project["workspace"],
        "documentId": project["document"],
        "expectedDocumentRevision": response.json()["revision"],
        "expectedDocumentVersion": 1,
        "contextualPlanId": plan["id"],
        "provider": "hyperframes.contextual-v2",
        "output": {"width": 320, "height": 320, "fps": 30},
    }
    response = client.post("/api/v1/studios/v1/video-renders", headers=headers, json=body)
    assert response.status_code in {409, 422}, response.text
    assert "native_renderer_binding_conflict" in response.text
    body["provider"] = "remotion.contextual-v2"
    headers["Idempotency-Key"] = "native-api-render"
    response = client.post("/api/v1/studios/v1/video-renders", headers=headers, json=body)
    assert response.status_code == 202, response.text
    replay = client.post("/api/v1/studios/v1/video-renders", headers=headers, json=body)
    assert replay.json()["id"] == response.json()["id"]
    with SessionLocal() as db:
        job = db.get(StudioGenerationJob, response.json()["id"])
        execute_job_once(db, job)
        assert job.status == "succeeded", job.error_message
        assert job.result_payload["artifact"]["width"] == 320
        rendered = job.result_payload["artifact"]
        revision = job.result_payload["documentRevision"]
    response = client.post(
        f"/api/v1/studios/v1/documents/{project['document']}/renders/{rendered['assetId']}/visual-review",
        headers=headers,
        json={
            "expectedDocumentRevision": revision,
            "renderChecksum": rendered["checksumSha256"],
            "clarity": 4,
            "rhythm": 4,
            "suitability": 4,
            "continuity": 4,
            "notes": "Test gate",
        },
    )
    assert response.status_code == 422
    assert "visual_review_finish_score_required" in response.text
