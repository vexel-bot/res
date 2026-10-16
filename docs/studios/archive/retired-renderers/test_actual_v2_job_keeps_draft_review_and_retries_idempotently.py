def test_actual_v2_job_keeps_draft_review_and_retries_idempotently(client, project, monkeypatch):
    import os

    import pytest

    from app import tasks
    from app.database import SessionLocal
    from app.models import LibraryAsset, StudioGenerationJob
    from app.providers.studios.contextual_motion_render import ContextualMotionRenderProvider
    from app.providers.studios.contextual_render import ContextualFFmpegProvider
    from app.providers.studios.video_render import VIDEO_RENDER_PROVIDERS, HyperFramesCliVideoRenderProvider
    from app.services.studios.jobs import execute_job_once

    cli = os.getenv("RES_HYPERFRAMES_CLI")
    if not cli:
        pytest.skip("Explicit pinned HyperFrames runtime required for actual rendering")
    monkeypatch.setitem(
        VIDEO_RENDER_PROVIDERS,
        "hyperframes.contextual-v2",
        ContextualMotionRenderProvider(
            HyperFramesCliVideoRenderProvider("node", cli, 180), ContextualFFmpegProvider("ffmpeg", 180)
        ),
    )
    monkeypatch.setattr(tasks.execute_studio_generation, "delay", lambda _: None)
    status = client.get("/api/v1/studios/v1/editing/ai", headers=headers(project))
    assert status.status_code == 200, status.text
    assert status.json()["contextualV2"]["configured"] is True
    from app.domain.studios.contextual_editing_v2 import EditorialElementV2

    candidate = direction(
        width=280,
        font_size=20,
        text="Distribuição",
        reveal="words",
        reveal_frames=25,
        font_weight=500,
        letter_spacing=1,
        shadow={"blur": 3},
        border_width=2,
    )
    candidate.scenes[0].elements.append(
        EditorialElementV2(
            id="connector",
            kind="path",
            purpose="Conectar as etapas",
            duration_frames=120,
            x=20,
            y=160,
            width=260,
            height=100,
            path_mode="quadratic",
            reveal="path",
            reveal_frames=30,
            points=[{"x": 0, "y": 80}, {"x": 130, "y": 0}, {"x": 260, "y": 80}],
        )
    )
    plan = create(client, project, candidate)
    url = f"/api/v1/studios/v1/documents/{project['document']}/editing-plans/{plan['id']}"
    response = client.post(url + "/apply", headers=headers(project), json={"expectedPlanRevision": 1})
    assert response.status_code == 200, response.text
    request = {
        "workspaceId": project["workspace"],
        "documentId": project["document"],
        "expectedDocumentRevision": 2,
        "expectedDocumentVersion": 1,
        "contextualPlanId": plan["id"],
        "provider": "hyperframes.contextual-v2",
        "output": {"width": 320, "height": 320, "fps": 30},
    }
    first = client.post(
        "/api/v1/studios/v1/video-renders", headers=headers(project, "v2-render-worker-test"), json=request
    )
    assert first.status_code == 202, first.text
    replay = client.post(
        "/api/v1/studios/v1/video-renders", headers=headers(project, "v2-render-worker-test"), json=request
    )
    assert replay.json()["id"] == first.json()["id"]
    with SessionLocal() as db:
        job = db.get(StudioGenerationJob, first.json()["id"])
        execute_job_once(db, job)
        assert job.status == "succeeded", job.error_message
        asset = db.get(LibraryAsset, job.result_payload["artifact"]["assetId"])
        assert asset.object_metadata["contextualEditing"]["editorialReview"] == "pending"
        observations = asset.object_metadata["audiovisualObservations"]
        assert observations["status"] == "partial"
        assert observations["checksum"] == asset.checksum_sha256
        assert observations["sampleCount"] > 0
        assert observations["speechIntelligibility"] == "unknown"
        audit = asset.object_metadata["visualAudit"]
        assert audit["renderChecksum"] == asset.checksum_sha256
        assert audit["coverage"]["complete"] is True
        assert audit["human"] == "pending"
        assert audit["renderedEvidence"]
        assert asset.object_metadata["contextualEditing"]["rendererChecks"]["graphics"]["ready"] is True
