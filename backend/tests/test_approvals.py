from datetime import UTC, datetime, timedelta

from conftest import register


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def create_pending_post(client, token: str, workspace_id: str) -> dict:
    response = client.post(
        "/api/v1/posts",
        headers=auth(token),
        json={
            "workspaceId": workspace_id,
            "title": "Conteúdo para aprovação",
            "platform": "instagram",
            "format": "post",
            "copy": "Texto em revisão",
            "status": "pending_approval",
            "author": "Redação",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_approval_comments_and_transitions_are_persistent(client):
    token, workspace_id = register(client, "approval-owner@example.com")
    post = create_pending_post(client, token, workspace_id)

    comment = client.post(
        f"/api/v1/posts/{post['id']}/approval-actions",
        headers=auth(token),
        json={"action": "comment", "comment": "Ajustar a chamada antes de publicar."},
    )
    assert comment.status_code == 200, comment.text
    assert comment.json()["event"]["eventType"] == "comment"

    approved = client.post(
        f"/api/v1/posts/{post['id']}/approval-actions",
        headers=auth(token),
        json={"action": "approve", "comment": "Revisão concluída."},
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["post"]["status"] == "approved"

    events = client.get(
        f"/api/v1/posts/approval-events?workspace_id={workspace_id}",
        headers=auth(token),
    )
    assert events.status_code == 200
    assert [item["eventType"] for item in events.json()] == ["comment", "action"]
    assert events.json()[0]["detail"] == "Ajustar a chamada antes de publicar."

    governance = client.get(
        f"/api/v1/workspace-features/{workspace_id}/governance",
        headers=auth(token),
    )
    assert governance.status_code == 200
    assert len(governance.json()["approvalEvents"]) == 2


def test_approval_events_are_tenant_isolated_and_transitions_are_validated(client):
    token, workspace_id = register(client, "approval-first@example.com")
    other_token, _ = register(client, "approval-second@example.com")
    post = create_pending_post(client, token, workspace_id)

    foreign = client.get(
        f"/api/v1/posts/approval-events?workspace_id={workspace_id}",
        headers=auth(other_token),
    )
    assert foreign.status_code == 404

    invalid = client.post(
        f"/api/v1/posts/{post['id']}/approval-actions",
        headers=auth(token),
        json={"action": "publish"},
    )
    assert invalid.status_code == 409

    missing_comment = client.post(
        f"/api/v1/posts/{post['id']}/approval-actions",
        headers=auth(token),
        json={"action": "comment", "comment": "   "},
    )
    assert missing_comment.status_code == 422

    approved = client.post(
        f"/api/v1/posts/{post['id']}/approval-actions",
        headers=auth(token),
        json={"action": "approve"},
    )
    assert approved.status_code == 200

    past_schedule = client.post(
        f"/api/v1/posts/{post['id']}/approval-actions",
        headers=auth(token),
        json={"action": "schedule", "scheduledAt": (datetime.now(UTC) - timedelta(minutes=1)).isoformat()},
    )
    assert past_schedule.status_code == 422

    future_schedule = client.post(
        f"/api/v1/posts/{post['id']}/approval-actions",
        headers=auth(token),
        json={"action": "schedule", "scheduledAt": (datetime.now(UTC) + timedelta(hours=1)).isoformat()},
    )
    assert future_schedule.status_code == 200
    assert future_schedule.json()["post"]["status"] == "scheduled"
