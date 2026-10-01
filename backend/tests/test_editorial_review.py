from copy import deepcopy
from types import SimpleNamespace

import pytest
from conftest import register

from app.database import SessionLocal
from app.domain.studios.editorial_review import EDITORIAL_AXES
from app.models import CreativeDocument, LibraryAsset, Membership, StudioDomainEvent, StudioGenerationJob
from app.providers.studios.video_render import VIDEO_RENDER_PROVIDERS
from app.services.object_storage import get_object_storage
from app.services.studios.publication import _validated_binding
from app.services.studios.video_render import execute_video_render


@pytest.fixture
def editorial(client, tmp_path, monkeypatch):
    from app import tasks
    from app.routers import assets as assets_router

    monkeypatch.setattr(assets_router.settings, "storage_path", str(tmp_path))
    monkeypatch.setattr(tasks.execute_studio_generation, "delay", lambda _: None)
    monkeypatch.setitem(VIDEO_RENDER_PROVIDERS, "hyperframes.cli", object())
    token, workspace = register(client, "editorial-owner@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    upload = client.post("/api/v1/assets/upload", headers=headers,
                         data={"workspace_id": workspace, "title": "Private technical fixture"},
                         files={"file": ("source.mp4", b"\x00\x00\x00\x18ftypisom", "video/mp4")})
    assert upload.status_code == 201, upload.text
    asset = upload.json()
    response = client.post("/api/v1/studios/v1/documents", headers=headers, json={
        "workspaceId": workspace, "title": "Editorial fixture", "contentType": "video", "brandRevision": 1,
        "brief": {"objective": "Demonstrate a verified operation", "audience": "Agencies"},
        "assets": [{"id": asset["id"], "mediaType": "video/mp4", "checksum": asset["checksumSha256"]}],
        "composition": {
            "pages": [{"id": "scene-1", "width": 720, "height": 1280, "layers": []}],
            "mediaTimeline": {"durationFrames": 30, "frameRate": {"numerator": 30, "denominator": 1},
                              "tracks": [{"id": "video-1", "kind": "video", "clips": [{
                                  "id": "clip-1", "assetId": asset["id"],
                                  "timeline": {"startFrame": 0, "durationFrames": 30},
                                  "source": {"startMicroseconds": 0, "durationMicroseconds": 1_000_000},
                              }]}]},
        },
    })
    assert response.status_code == 201, response.text
    doc = response.json()
    base = f"/api/v1/studios/v1/documents/{doc['documentId']}"
    plan_body = {"expectedDocumentRevision": doc["revision"], "objective": "One verifiable operation",
                 "cta": "Request pilot access", "beats": [{"id": "proof-1", "message": "Explain the change",
                 "visualAction": "Show the original and revised item", "editReason": "Reveal the consequence",
                 "evidenceAssetIds": [asset["id"]]}]}
    render_body = {"workspaceId": workspace, "documentId": doc["documentId"],
                   "expectedDocumentRevision": doc["revision"], "expectedDocumentVersion": doc["version"],
                   "provider": "hyperframes.cli", "pageIds": ["scene-1"],
                   "output": {"format": "mp4", "width": 720, "height": 1280, "fps": 30,
                              "videoCodec": "h264", "audioCodec": "aac", "quality": "draft"}}
    return {"headers": headers, "asset": asset, "document": doc, "base": base,
            "plan_body": plan_body, "render_body": render_body, "workspace": workspace}


def post_plan(client, data, key="editorial-plan-001"):
    result = client.post(data["base"] + "/editorial-plans",
                         headers={**data["headers"], "Idempotency-Key": key}, json=data["plan_body"])
    assert result.status_code == 200, result.text
    return result.json()


def post_review(client, data, plan, axis, decision="approved", key=None):
    return client.post(data["base"] + "/editorial-reviews",
                       headers={**data["headers"], "Idempotency-Key": key or f"review-{axis}-{decision}"},
                       json={"planId": plan["id"], "axis": axis, "decision": decision,
                             "notes": "Human fixture review, not an automated quality score.",
                             "evidenceAssetIds": [data["asset"]["id"]]})


def test_enrollment_and_independent_reviews_block_full_render(client, editorial):
    data = editorial
    before = client.get(data["base"] + "/editorial-readiness", headers=data["headers"]).json()
    assert not before["managed"] and not before["fullRenderEligible"]
    plan = post_plan(client, data)
    assert post_plan(client, data)["id"] == plan["id"]
    state = client.get(data["base"] + "/editorial-readiness", headers=data["headers"]).json()
    assert len(state["blockers"]) == 7
    assert not state["publicationAuthorized"]
    response = client.post("/api/v1/studios/v1/video-renders", json=data["render_body"],
                           headers={**data["headers"], "Idempotency-Key": "blocked-render-001"})
    assert response.status_code == 422, response.text
    assert "editorial_full_render_blocked" in response.text
    for axis in EDITORIAL_AXES:
        result = post_review(client, data, plan, axis)
        assert result.status_code == 200, result.text
        assert result.json()["reviewedBy"] == plan["createdBy"]
    state = client.get(data["base"] + "/editorial-readiness", headers=data["headers"]).json()
    assert state["fullRenderEligible"] and not state["publicationAuthorized"]
    response = client.post("/api/v1/studios/v1/video-renders", json=data["render_body"],
                           headers={**data["headers"], "Idempotency-Key": "eligible-render-001"})
    assert response.status_code == 202, response.text
    assert post_review(client, data, plan, "voice", "rejected").status_code == 200
    # Replaying an older approval must not resurrect it after rejection.
    assert post_review(client, data, plan, "voice").status_code == 200
    state = client.get(data["base"] + "/editorial-readiness", headers=data["headers"]).json()
    assert "editorial_voice_rejected" in state["blockers"]
    with SessionLocal() as db:
        job = db.get(StudioGenerationJob, response.json()["id"])
        assert job.request_payload["editorialPlanId"] == plan["id"]
        with pytest.raises(ValueError, match="editorial_voice_rejected"):
            execute_video_render(db, job, lambda _: None, lambda: False)


@pytest.mark.parametrize("change,expected", [
    ("revision", "editorial_plan_stale"), ("metadata", "editorial_assets_changed"),
    ("deleted", "editorial_assets_unavailable"),
])
def test_current_document_and_server_asset_bindings(client, editorial, change, expected):
    data = editorial
    post_plan(client, data)
    with SessionLocal() as db:
        if change == "revision":
            document = db.get(CreativeDocument, data["document"]["documentId"])
            document.revision += 1
        else:
            asset = db.get(LibraryAsset, data["asset"]["id"])
            if change == "metadata":
                asset.object_metadata = {**asset.object_metadata, "source": "synthetic-original"}
            else:
                asset.lifecycle_status = "deleted"
        db.commit()
    state = client.get(data["base"] + "/editorial-readiness", headers=data["headers"]).json()
    assert expected in state["blockers"]
    assert not state["fullRenderEligible"]


def test_plan_replacement_clears_reviews_and_idempotency_conflicts(client, editorial):
    data = editorial
    plan = post_plan(client, data)
    assert post_review(client, data, plan, "voice").status_code == 200
    changed = deepcopy(data["plan_body"])
    changed["cta"] = "Different invitation"
    conflict = client.post(data["base"] + "/editorial-plans", json=changed,
                           headers={**data["headers"], "Idempotency-Key": "editorial-plan-001"})
    assert conflict.status_code == 409
    new_plan = post_plan(client, data, "editorial-plan-002")
    assert new_plan["id"] != plan["id"]
    state = client.get(data["base"] + "/editorial-readiness", headers=data["headers"]).json()
    assert state["reviews"] == []
    assert post_review(client, data, plan, "face").status_code == 409
    with SessionLocal() as db:
        events = db.query(StudioDomainEvent).filter_by(aggregate_type="editorial_document").all()
        assert len(events) == 3  # Two plans and one preserved review.


def test_tenant_and_governance_boundary(client, editorial):
    data = editorial
    token, _ = register(client, "editorial-foreign@example.com")
    headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": "foreign-plan-001"}
    assert client.get(data["base"] + "/editorial-readiness", headers=headers).status_code == 404
    assert client.post(data["base"] + "/editorial-plans", headers=headers,
                       json=data["plan_body"]).status_code == 404
    with SessionLocal() as db:
        member = db.query(Membership).filter_by(workspace_id=data["workspace"]).one()
        member.role = "viewer"
        db.commit()
    assert client.post(data["base"] + "/editorial-plans", json=data["plan_body"],
                       headers={**data["headers"], "Idempotency-Key": "viewer-plan-001"}).status_code == 403


def test_review_rejects_forged_reviewer_or_unknown_evidence(client, editorial):
    data = editorial
    plan = post_plan(client, data)
    request = {"planId": plan["id"], "axis": "face", "decision": "approved", "notes": "Reviewed",
               "evidenceAssetIds": ["foreign-asset"], "reviewedBy": "fake-human"}
    headers = {**data["headers"], "Idempotency-Key": "forged-review-001"}
    assert client.post(data["base"] + "/editorial-reviews", headers=headers, json=request).status_code == 422
    del request["reviewedBy"]
    response = client.post(data["base"] + "/editorial-reviews", headers=headers, json=request)
    assert response.status_code == 422 and "editorial_evidence_not_in_document" in response.text


def test_review_verifies_actual_bytes_before_recording_approval(client, editorial):
    data = editorial
    plan = post_plan(client, data)
    with SessionLocal() as db:
        asset = db.get(LibraryAsset, data["asset"]["id"])
        with get_object_storage(asset.storage_backend or "local").materialize(asset.storage_key) as path:
            path.write_bytes(b"tampered technical fixture")
    result = post_review(client, data, plan, "voice")
    assert result.status_code == 422 and "editorial_evidence_changed" in result.text
    state = client.get(data["base"] + "/editorial-readiness", headers=data["headers"]).json()
    assert state["reviews"] == []


def test_worker_rejects_old_or_unbound_plan_even_if_new_plan_approved(client, editorial):
    data = editorial
    plan = post_plan(client, data)
    for axis in EDITORIAL_AXES:
        assert post_review(client, data, plan, axis).status_code == 200
    response = client.post("/api/v1/studios/v1/video-renders", json=data["render_body"],
                           headers={**data["headers"], "Idempotency-Key": "old-plan-render-001"})
    assert response.status_code == 202
    new_plan = post_plan(client, data, "replacement-plan-001")
    for axis in EDITORIAL_AXES:
        assert post_review(client, data, new_plan, axis, key=f"new-plan-{axis}").status_code == 200
    with SessionLocal() as db:
        job = db.get(StudioGenerationJob, response.json()["id"])
        with pytest.raises(ValueError, match="editorial_render_snapshot_stale"):
            execute_video_render(db, job, lambda _: None, lambda: False)
        payload = dict(job.request_payload)
        payload.pop("editorialPlanId")
        job.request_payload = payload
        with pytest.raises(ValueError, match="editorial_render_snapshot_stale"):
            execute_video_render(db, job, lambda _: None, lambda: False)


def test_preproduction_approval_never_authorizes_publication(client, editorial):
    data = editorial
    plan = post_plan(client, data)
    for axis in EDITORIAL_AXES:
        assert post_review(client, data, plan, axis).status_code == 200
    with SessionLocal() as db:
        final_review = SimpleNamespace(status="approved", document_id=data["document"]["documentId"])
        with pytest.raises(ValueError, match="studio_publication_editorial_final_review_pending"):
            _validated_binding(db, final_review)
