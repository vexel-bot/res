from __future__ import annotations

import io
import json
import zipfile
from datetime import UTC, datetime, timedelta

import pytest
from conftest import register
from test_ffmpeg_ugc_video_render_provider import ugc_fixture
from test_studio_kernel import auth, create_document

from app.database import SessionLocal
from app.models import Post, StudioDomainEvent
from app.services.studios.publication import _require_audio_admission


@pytest.mark.parametrize("policy", [
    {"naturalSoundPolicy": "required-before-approval"},
    {"voicePolicy": "prohibited"},
    {"audioMode": "natural-foley-only"},
])
def test_no_voice_delivery_cannot_be_admitted_by_editable_approval_flags(policy):
    document, _ = ugc_fixture()
    document.composition.narrative.update(policy)
    document.composition.narrative.update({"naturalSoundApproved": True, "humanListeningStatus": "pass"})
    with pytest.raises(ValueError, match="studio_publication_natural_sound_evidence_pending"):
        _require_audio_admission(document)


def test_audio_admission_does_not_change_legacy_or_visual_documents():
    document, _ = ugc_fixture()
    _require_audio_admission(document)
    document.content_type = "visual"
    document.composition.narrative["naturalSoundPolicy"] = "required-before-approval"
    _require_audio_admission(document)


def create_linked_review(client, token: str, workspace: str):
    post_response = client.post(
        "/api/v1/posts",
        headers=auth(token),
        json={
            "workspaceId": workspace,
            "title": "UGC sem narração",
            "platform": "Instagram",
            "format": "carousel",
            "copy": "Texto aprovado para a publicação.",
            "hashtags": ["#UGC", "#Clicko"],
            "status": "draft",
            "author": "Operador",
        },
    )
    assert post_response.status_code == 201, post_response.text
    post = post_response.json()
    document_response = create_document(client, token, workspace, content_type="carousel", post_id=post["id"])
    assert document_response.status_code == 201, document_response.text
    document = document_response.json()
    document_url = f"/api/v1/studios/v1/documents/{document['documentId']}"
    review_response = client.post(f"{document_url}/reviews", headers=auth(token), json={})
    assert review_response.status_code == 201, review_response.text
    review = review_response.json()
    approval = client.post(
        f"/api/v1/studios/v1/reviews/{review['id']}/decisions",
        headers=auth(token),
        json={"action": "approve", "comment": "Arte e legenda conferidas."},
    )
    assert approval.status_code == 200, approval.text
    return post, document, approval.json()


def test_preflight_package_and_internal_schedule_are_bound_to_approved_review(client):
    token, workspace = register(client, "publication-preflight@example.com")
    other_token, _ = register(client, "publication-preflight-other@example.com")
    post, document, review = create_linked_review(client, token, workspace)
    base = f"/api/v1/studios/v1/reviews/{review['id']}"

    preflight = client.get(f"{base}/publication-preflight", headers=auth(token))
    assert preflight.status_code == 200, preflight.text
    payload = preflight.json()
    assert payload["postId"] == post["id"]
    assert payload["documentId"] == document["documentId"]
    assert payload["documentVersion"] == review["documentVersion"]
    assert payload["caption"] == "Texto aprovado para a publicação."
    assert payload["hashtags"] == ["#UGC", "#Clicko"]
    assert payload["pageIds"] == ["page-1", "page-2"]
    assert payload["status"] == "ready"
    assert {check["key"] for check in payload["checks"]} == {
        "approval",
        "version",
        "media",
        "rights",
        "schedule",
        "channel",
    }
    assert client.get(f"{base}/publication-preflight").status_code in {401, 403}
    assert client.get(f"{base}/publication-preflight", headers=auth(other_token)).status_code == 404

    package = client.get(f"{base}/publication-package", headers=auth(token))
    assert package.status_code == 200, package.text
    assert package.headers["content-type"] == "application/zip"
    assert package.headers["cache-control"] == "private, no-store"
    with zipfile.ZipFile(io.BytesIO(package.content)) as archive:
        assert set(archive.namelist()) == {"slide-01.png", "slide-02.png", "legenda.txt", "manifesto.json"}
        assert archive.read("slide-01.png").startswith(b"\x89PNG")
        assert archive.read("legenda.txt").decode() == "Texto aprovado para a publicação.\n\n#UGC #Clicko"
        manifest = json.loads(archive.read("manifesto.json"))
        assert manifest["reviewId"] == review["id"]
        assert manifest["externalPublicationConfirmed"] is False
    assert client.get(f"{base}/publication-package", headers=auth(other_token)).status_code == 404

    scheduled_at = datetime.now(UTC) + timedelta(days=2)
    scheduled = client.post(
        f"{base}/internal-schedule",
        headers=auth(token),
        json={"scheduledAt": scheduled_at.isoformat()},
    )
    assert scheduled.status_code == 200, scheduled.text
    receipt = scheduled.json()
    assert receipt["reviewId"] == review["id"]
    assert receipt["externalPublicationConfirmed"] is False
    repeated = client.post(
        f"{base}/internal-schedule",
        headers=auth(token),
        json={"scheduledAt": scheduled_at.isoformat()},
    )
    assert repeated.status_code == 200
    assert repeated.json()["receiptId"] == receipt["receiptId"]
    assert client.get(f"{base}/publication-preflight", headers=auth(token)).json()["status"] == "scheduled"
    with SessionLocal() as db:
        stored = db.get(Post, post["id"])
        assert stored.status == "scheduled"
        assert stored.scheduled_at is not None
        events = (
            db.query(StudioDomainEvent)
            .filter_by(aggregate_id=review["id"], event_type="studio.publication.scheduled_internal")
            .all()
        )
        assert len(events) == 1
        assert events[0].payload["externalPublicationConfirmed"] is False


def test_copy_change_and_stale_document_fail_closed_after_approval(client):
    token, workspace = register(client, "publication-stale@example.com")
    post, document, review = create_linked_review(client, token, workspace)
    base = f"/api/v1/studios/v1/reviews/{review['id']}"
    future = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    assert (
        client.post(f"{base}/internal-schedule", headers=auth(token), json={"scheduledAt": future}).status_code == 200
    )

    edited_post = client.patch(
        f"/api/v1/posts/{post['id']}",
        headers=auth(token),
        json={"copy": "Copy trocada depois da aprovação."},
    )
    assert edited_post.status_code == 200
    for suffix, method in (("publication-preflight", "get"), ("publication-package", "get")):
        response = getattr(client, method)(f"{base}/{suffix}", headers=auth(token))
        assert response.status_code == 409
        assert response.json()["detail"]["code"] == "studio_publication_copy_changed"
    reschedule = client.post(f"{base}/internal-schedule", headers=auth(token), json={"scheduledAt": future})
    assert reschedule.status_code == 409
    assert reschedule.json()["detail"]["code"] == "studio_publication_copy_changed"

    assert (
        client.patch(
            f"/api/v1/posts/{post['id']}", headers=auth(token), json={"copy": "Texto aprovado para a publicação."}
        ).status_code
        == 200
    )
    document_url = f"/api/v1/studios/v1/documents/{document['documentId']}"
    current = client.get(document_url, headers=auth(token)).json()
    current["brief"]["hook"] = "Direção ainda não revisada"
    changed = client.put(
        document_url,
        headers=auth(token),
        json={"expectedRevision": current["revision"], "document": current},
    )
    assert changed.status_code == 200
    assert changed.json()["status"] == "draft"
    with SessionLocal() as db:
        stored = db.get(Post, post["id"])
        assert stored.status == "draft"
        assert stored.scheduled_at is None
    stale = client.get(f"{base}/publication-preflight", headers=auth(token))
    assert stale.status_code == 409
    assert stale.json()["detail"]["code"] == "studio_publication_snapshot_stale"


def test_internal_schedule_rejects_past_time(client):
    token, workspace = register(client, "publication-past@example.com")
    _, _, review = create_linked_review(client, token, workspace)
    response = client.post(
        f"/api/v1/studios/v1/reviews/{review['id']}/internal-schedule",
        headers=auth(token),
        json={"scheduledAt": (datetime.now(UTC) - timedelta(minutes=1)).isoformat()},
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "studio_publication_schedule_must_be_future"
