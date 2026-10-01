from __future__ import annotations

from datetime import UTC, datetime

from conftest import register


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def create_video_document(client, token: str, workspace_id: str) -> dict[str, object]:
    response = client.post(
        "/api/v1/studios/v1/documents",
        headers=auth(token),
        json={
            "workspaceId": workspace_id,
            "title": "Motion document",
            "contentType": "video",
            "brandRevision": 1,
            "brief": {
                "objective": "Animar uma peça vertical revisável",
                "audience": "Criadores de anúncios",
            },
            "composition": {
                "pages": [
                    {
                        "id": "scene-1",
                        "width": 360,
                        "height": 640,
                        "layers": [
                            {
                                "id": "headline",
                                "kind": "text",
                                "x": 24,
                                "y": 180,
                                "width": 312,
                                "height": 180,
                            }
                        ],
                    }
                ],
                "mediaTimeline": {
                    "frameRate": {"numerator": 30, "denominator": 1},
                    "durationFrames": 30,
                    "tracks": [],
                },
            },
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def motion_graph(
    document: dict[str, object],
    workspace_id: str,
    *,
    graph_id: str = "motion-api-1",
    velocity_threshold: float = 400,
) -> dict[str, object]:
    return {
        "graphId": graph_id,
        "workspaceId": workspace_id,
        "documentId": document["documentId"],
        "documentRevision": document["revision"],
        "frameRate": {"numerator": 30, "denominator": 1},
        "durationFrames": 30,
        "canvasWidth": 360,
        "canvasHeight": 640,
        "status": "suggested",
        "tracks": [
            {
                "trackId": "headline-x",
                "targetLayerId": "headline",
                "property": "position_x",
                "unit": "pixels",
                "keyframes": [
                    {"frame": 0, "value": -120, "easing": "ease_out"},
                    {"frame": 12, "value": 0, "easing": "linear"},
                ],
            }
        ],
        "constraints": [
            {
                "constraintId": "headline-velocity",
                "kind": "maximum_velocity",
                "targetTrackIds": ["headline-x"],
                "frameRange": {"startFrame": 0, "endFrameExclusive": 13},
                "threshold": velocity_threshold,
                "severity": "blocking",
            }
        ],
        "createdBy": "evaluation.qwen-motion",
        "createdAt": datetime(2026, 8, 26, 19, 30, tzinfo=UTC).isoformat(),
    }


def test_motion_graph_api_is_idempotent_versioned_reviewed_and_tenant_scoped(client) -> None:
    token, workspace = register(client, "motion-owner@example.com", "Motion Owner")
    other_token, _ = register(client, "motion-other@example.com", "Motion Other")
    document = create_video_document(client, token, workspace)
    graph = motion_graph(document, workspace)
    request = {
        "workspaceId": workspace,
        "graph": graph,
        "idempotencyKey": "motion-create-1",
    }

    created = client.post(
        "/api/v1/studios/v1/motion-graphs",
        headers=auth(token),
        json=request,
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["storageRevision"] == 1
    assert body["graph"]["status"] == "suggested"
    assert body["evaluation"] is None
    assert len(body["graphDigestSha256"]) == 64

    repeated = client.post(
        "/api/v1/studios/v1/motion-graphs",
        headers=auth(token),
        json=request,
    )
    assert repeated.status_code == 201
    assert repeated.json()["graphDigestSha256"] == body["graphDigestSha256"]

    changed_request = dict(request)
    changed_request["graph"] = motion_graph(document, workspace, velocity_threshold=450)
    conflict = client.post(
        "/api/v1/studios/v1/motion-graphs",
        headers=auth(token),
        json=changed_request,
    )
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["code"] == "motion_graph_idempotency_conflict"

    graph_id = graph["graphId"]
    assert (
        client.get(
            f"/api/v1/studios/v1/motion-graphs/{graph_id}",
            headers=auth(other_token),
        ).status_code
        == 404
    )
    assert (
        client.get(
            "/api/v1/studios/v1/motion-graphs",
            headers=auth(other_token),
            params={"workspace_id": workspace},
        ).status_code
        == 404
    )

    review = client.post(
        f"/api/v1/studios/v1/motion-graphs/{graph_id}/review",
        headers=auth(token),
        json={"workspaceId": workspace, "expectedRevision": 1},
    )
    assert review.status_code == 200, review.text
    reviewed = review.json()
    assert reviewed["storageRevision"] == 2
    assert reviewed["graph"]["status"] == "reviewed"
    assert reviewed["evaluation"]["eligibleForReviewedProjection"] is True
    assert reviewed["evaluation"]["observations"][0]["measuredValue"] == 300

    projection = client.get(
        f"/api/v1/studios/v1/motion-graphs/{graph_id}/projection/hyperframes",
        headers=auth(token),
    )
    assert projection.status_code == 200, projection.text
    assert projection.json()["previewOnly"] is False
    assert projection.json()["sourceGraphDigestSha256"] == reviewed["graphDigestSha256"]

    stale = client.put(
        f"/api/v1/studios/v1/motion-graphs/{graph_id}",
        headers=auth(token),
        json={"workspaceId": workspace, "expectedRevision": 1, "graph": graph},
    )
    assert stale.status_code == 409
    assert stale.json()["detail"]["code"] == "motion_graph_conflict"

    replacement_graph = motion_graph(document, workspace, velocity_threshold=500)
    replaced = client.put(
        f"/api/v1/studios/v1/motion-graphs/{graph_id}",
        headers=auth(token),
        json={
            "workspaceId": workspace,
            "expectedRevision": 2,
            "graph": replacement_graph,
        },
    )
    assert replaced.status_code == 200, replaced.text
    assert replaced.json()["storageRevision"] == 3
    assert replaced.json()["graph"]["status"] == "suggested"
    assert replaced.json()["evaluation"] is None


def test_motion_review_fails_closed_and_preserves_suggestion(client) -> None:
    token, workspace = register(client, "motion-gate@example.com", "Motion Gate")
    document = create_video_document(client, token, workspace)
    graph = motion_graph(
        document,
        workspace,
        graph_id="motion-api-blocked",
        velocity_threshold=100,
    )
    created = client.post(
        "/api/v1/studios/v1/motion-graphs",
        headers=auth(token),
        json={
            "workspaceId": workspace,
            "graph": graph,
            "idempotencyKey": "motion-create-blocked",
        },
    )
    assert created.status_code == 201, created.text

    blocked = client.post(
        "/api/v1/studios/v1/motion-graphs/motion-api-blocked/review",
        headers=auth(token),
        json={"workspaceId": workspace, "expectedRevision": 1},
    )
    assert blocked.status_code == 422
    assert blocked.json()["detail"]["code"] == "motion_graph_constraints_block_review"

    unchanged = client.get(
        "/api/v1/studios/v1/motion-graphs/motion-api-blocked",
        headers=auth(token),
    )
    assert unchanged.status_code == 200
    assert unchanged.json()["storageRevision"] == 1
    assert unchanged.json()["graph"]["status"] == "suggested"
    assert unchanged.json()["evaluation"] is None
