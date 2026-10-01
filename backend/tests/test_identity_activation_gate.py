from datetime import UTC, datetime, timedelta

from conftest import register
from sqlalchemy import select

from app.database import SessionLocal
from app.models import (
    LibraryAsset,
    Membership,
    StudioConsentGrant,
    StudioGenerationJob,
    StudioIdentityProfile,
    StudioIdentityVersion,
    StudioVoiceProfile,
    User,
)


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_identity_and_voice_require_private_preview_human_review_and_live_consent(client, monkeypatch):
    token, workspace = register(client, "activation-owner@example.com", "Activation Studio")
    editor_token, _ = register(client, "activation-editor@example.com", "Editor Home")
    with SessionLocal() as db:
        editor = db.scalar(select(User).where(User.email == "activation-editor@example.com"))
        db.add(Membership(user_id=editor.id, workspace_id=workspace, role="Editor"))
        sample = LibraryAsset(workspace_id=workspace, title="Identity sample", asset_type="upload", tags=[])
        preview = LibraryAsset(
            workspace_id=workspace,
            title="Private preview",
            asset_type="video",
            tags=[],
            storage_key=f"{workspace}/identity/private-preview.mp4",
            media_type="video/mp4",
        )
        db.add_all([sample, preview])
        db.commit()
        db.refresh(sample)
        db.refresh(preview)
        sample_id = sample.id
        preview_id = preview.id

    consent = client.post(
        "/api/v1/studios/v1/consents",
        headers=auth(token),
        json={
            "workspaceId": workspace,
            "subjectKey": "subject-gabi-001",
            "subjectDisplayName": "Gabi",
            "purpose": "UGC autorizado com preview privado e revisão humana.",
            "scopes": ["identity.enroll", "avatar.generate", "voice.enroll", "voice.clone"],
            "policyVersion": "identity-consent.v1",
            "expiresAt": (datetime.now(UTC) + timedelta(days=30)).isoformat(),
        },
    ).json()
    identity = client.post(
        "/api/v1/studios/v1/identities",
        headers=auth(token),
        json={
            "workspaceId": workspace,
            "subjectKey": consent["subjectKey"],
            "displayName": "Gabi",
            "identityType": "natural_person",
        },
    ).json()
    version = client.post(
        f"/api/v1/studios/v1/identities/{identity['id']}/versions",
        headers=auth(token),
        json={
            "consentGrantId": consent["id"],
            "capabilities": ["avatar.generate"],
            "sampleAssetIds": [sample_id],
        },
    ).json()

    premature = client.post(
        f"/api/v1/studios/v1/identities/{identity['id']}/versions/{version['id']}/review",
        headers=auth(token),
        json={"action": "approve", "comment": "Preview revisado pela responsável."},
    )
    assert premature.status_code == 422
    assert premature.json()["detail"]["code"] == "passed_identity_evaluation_required"

    forbidden = client.post(
        f"/api/v1/studios/v1/identities/{identity['id']}/versions/{version['id']}/evaluations",
        headers=auth(editor_token),
        json={
            "status": "passed",
            "evaluatorKind": "human",
            "checks": [{"code": "identity-match", "passed": True}],
            "previewAssetIds": [preview_id],
        },
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["detail"]["code"] == "identity_governance_role_required"

    evaluation = client.post(
        f"/api/v1/studios/v1/identities/{identity['id']}/versions/{version['id']}/evaluations",
        headers=auth(token),
        json={
            "status": "passed",
            "evaluatorKind": "human",
            "qualityMetrics": {"identitySimilarity": 0.93, "temporalStability": 0.91},
            "checks": [
                {"code": "identity-match", "passed": True, "score": 0.93},
                {"code": "artifact-review", "passed": True, "score": 0.91},
            ],
            "previewAssetIds": [preview_id],
            "notes": "Preview privado aprovado para revisão final.",
        },
    )
    assert evaluation.status_code == 201, evaluation.text
    assert evaluation.json()["targetType"] == "identity_version"

    activated = client.post(
        f"/api/v1/studios/v1/identities/{identity['id']}/versions/{version['id']}/review",
        headers=auth(token),
        json={"action": "approve", "comment": "Rosto e movimento conferidos no preview privado."},
    )
    assert activated.status_code == 200, activated.text
    assert activated.json()["status"] == "active"
    assert activated.json()["reviewedBy"]

    voice = client.post(
        "/api/v1/studios/v1/voices",
        headers=auth(token),
        json={
            "workspaceId": workspace,
            "identityProfileId": identity["id"],
            "displayName": "Gabi PT-BR",
            "locale": "pt-BR",
            "voiceType": "cloned",
        },
    ).json()
    voice_version = client.post(
        f"/api/v1/studios/v1/voices/{voice['id']}/versions",
        headers=auth(token),
        json={"consentGrantId": consent["id"], "sampleAssetIds": [sample_id]},
    ).json()
    voice_evaluation = client.post(
        f"/api/v1/studios/v1/voices/{voice['id']}/versions/{voice_version['id']}/evaluations",
        headers=auth(token),
        json={
            "status": "passed",
            "evaluatorKind": "human",
            "qualityMetrics": {"naturalness": 0.9, "speakerSimilarity": 0.92},
            "checks": [{"code": "pt-br-listening-review", "passed": True, "score": 0.9}],
            "previewAssetIds": [preview_id],
        },
    )
    assert voice_evaluation.status_code == 201, voice_evaluation.text
    voice_activated = client.post(
        f"/api/v1/studios/v1/voices/{voice['id']}/versions/{voice_version['id']}/review",
        headers=auth(token),
        json={"action": "approve", "comment": "Pronúncia PT-BR e identidade vocal conferidas."},
    )
    assert voice_activated.status_code == 200, voice_activated.text
    assert voice_activated.json()["status"] == "active"

    from app import tasks

    monkeypatch.setattr(tasks.execute_studio_generation, "delay", lambda _job_id: None)
    missing_consent = client.post(
        "/api/v1/studios/v1/jobs",
        headers={**auth(token), "Idempotency-Key": "activated-identities-no-consent"},
        json={
            "workspaceId": workspace,
            "identityVersionId": version["id"],
            "voiceVersionId": voice_version["id"],
        },
    )
    assert missing_consent.status_code == 422
    assert missing_consent.json()["detail"]["code"] == "identity_version_consent_mismatch"

    bound_job = client.post(
        "/api/v1/studios/v1/jobs",
        headers={**auth(token), "Idempotency-Key": "activated-identities-live-consent"},
        json={
            "workspaceId": workspace,
            "consentGrantId": consent["id"],
            "identityVersionId": version["id"],
            "voiceVersionId": voice_version["id"],
        },
    )
    assert bound_job.status_code == 202, bound_job.text

    with SessionLocal() as db:
        assert db.get(StudioIdentityVersion, version["id"]).status == "active"
        grant = db.get(StudioConsentGrant, consent["id"])
        grant.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()

    expired = client.post(
        "/api/v1/studios/v1/jobs",
        headers={**auth(token), "Idempotency-Key": "activated-identities-expired-consent"},
        json={
            "workspaceId": workspace,
            "consentGrantId": consent["id"],
            "identityVersionId": version["id"],
            "voiceVersionId": voice_version["id"],
        },
    )
    assert expired.status_code == 422
    assert expired.json()["detail"]["code"] == "consent_not_active"

    forbidden_deletion = client.post(
        f"/api/v1/studios/v1/identities/{identity['id']}/deletion-requests",
        headers={**auth(editor_token), "Idempotency-Key": "identity-delete-editor-001"},
        json={"reason": "Editor não pode planejar exclusão."},
    )
    assert forbidden_deletion.status_code == 403

    deletion_headers = {**auth(token), "Idempotency-Key": "identity-delete-owner-001"}
    deletion_body = {
        "reason": "Titular solicitou remoção da cápsula e derivados.",
        "deleteSourceSamples": False,
    }
    deletion = client.post(
        f"/api/v1/studios/v1/identities/{identity['id']}/deletion-requests",
        headers=deletion_headers,
        json=deletion_body,
    )
    assert deletion.status_code == 202, deletion.text
    deletion_plan = deletion.json()["deletionPlan"]
    assert deletion.json()["status"] == "planned"
    assert version["id"] in deletion_plan["identityVersionIds"]
    assert voice_version["id"] in deletion_plan["voiceVersionIds"]
    assert preview_id in deletion_plan["previewAssetIds"]
    assert sample_id in deletion_plan["sourceSampleAssetIds"]
    assert bound_job.json()["id"] in deletion_plan["jobIds"]
    assert deletion_plan["executionGate"] == "identity_deletion_execution_enabled"

    replay = client.post(
        f"/api/v1/studios/v1/identities/{identity['id']}/deletion-requests",
        headers=deletion_headers,
        json=deletion_body,
    )
    assert replay.status_code == 202
    assert replay.json()["id"] == deletion.json()["id"]
    with SessionLocal() as db:
        assert db.get(StudioIdentityProfile, identity["id"]).status == "deleting"
        assert db.get(StudioVoiceProfile, voice["id"]).status == "deleting"
        assert db.get(StudioGenerationJob, bound_job.json()["id"]).status == "cancelled"
