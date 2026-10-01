from datetime import UTC, datetime, timedelta

from conftest import register
from sqlalchemy import select

from app.database import SessionLocal
from app.models import Membership, StudioConsentGrant, StudioDomainEvent, StudioProviderRegistration, User
from app.services.studios.identity import consent_status
from app.services.studios.readiness import _publication_consent_ready
from app.services.studios.registry import register_model, register_provider


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _grant(*scopes: str, status: str = "active", expires_at: datetime | None = None) -> StudioConsentGrant:
    return StudioConsentGrant(
        id="grant-readiness",
        workspace_id="workspace-readiness",
        subject_key="subject-readiness",
        subject_display_name="Readiness Subject",
        purpose="Readiness unit test",
        scopes=list(scopes),
        brand_ids=[],
        channels=[],
        policy_version="identity-consent.v1",
        status=status,
        granted_by="user-readiness",
        expires_at=expires_at or (datetime.now(UTC) + timedelta(days=1)),
    )


def test_publication_consent_is_separate_from_private_generation_consent() -> None:
    generation_only = _grant("voice.clone")
    assert consent_status(generation_only) == "active"
    assert _publication_consent_ready("voice_clone", [generation_only]) is False
    assert _publication_consent_ready("voice_clone", [_grant("voice.clone", "publish.synthetic")]) is True
    assert _publication_consent_ready("stock_voice", []) is True
    assert _publication_consent_ready("transcription", []) is True
    assert _publication_consent_ready(
        "presenter", [_grant("publish.synthetic", expires_at=datetime.now(UTC) - timedelta(seconds=1))]
    ) is False


def test_capability_projection_is_explicit_read_only_and_tenant_isolated(client):
    token, workspace = register(client, "capability-owner@example.com", "Capability Studio")
    other_token, other_workspace = register(client, "capability-other@example.com", "Other Capability Studio")

    response = client.get(
        "/api/v1/studios/v1/capabilities",
        headers=auth(token),
        params={"workspace_id": workspace},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["schemaVersion"] == "studio.capabilities.v1"
    assert body["workspaceId"] == workspace
    assert {item["capability"] for item in body["capabilities"]} == {
        "presenter",
        "avatar",
        "voice_clone",
        "stock_voice",
        "transcription",
    }
    presenter = next(item for item in body["capabilities"] if item["capability"] == "presenter")
    assert presenter["status"] == "unavailable"
    assert presenter["providerReady"] is False
    assert presenter["captureReady"] is False
    assert "provider_registry_empty" in presenter["reasons"]
    assert "benchmark_evidence_pending" in presenter["reasons"]
    transcription = next(item for item in body["capabilities"] if item["capability"] == "transcription")
    assert transcription["status"] == "unavailable"
    assert transcription["providerReady"] is False
    assert transcription["captureReady"] is False
    assert transcription["consentReady"] is True
    assert transcription["publicationAllowed"] is False

    cross_tenant = client.get(
        "/api/v1/studios/v1/capabilities",
        headers=auth(other_token),
        params={"workspace_id": workspace},
    )
    assert cross_tenant.status_code == 404

    # The projection may observe the global registry, but never mutates it or
    # leaks workspace data from the other tenant.
    with SessionLocal() as db:
        provider = register_provider(
            db,
            capability="PresenterProvider",
            provider="evaluation.presenter",
            provider_version="v1",
            source_url="https://example.invalid/presenter",
            source_revision="a" * 40,
            code_license="MIT",
            risk_class="biometric",
        )
        register_model(
            db,
            provider_registration=provider,
            name="Presenter evaluation model",
            version="v1",
            digest_sha256="c" * 64,
            model_license="MIT",
            commercial_use="unknown",
            languages=["pt-BR"],
            capabilities=["presenter"],
        )

    candidate = client.get(
        "/api/v1/studios/v1/capabilities",
        headers=auth(token),
        params={"workspace_id": workspace},
    )
    assert candidate.status_code == 200
    candidate_presenter = next(
        item for item in candidate.json()["capabilities"] if item["capability"] == "presenter"
    )
    assert candidate_presenter["status"] == "blocked"
    assert candidate_presenter["providerCandidates"] == 1
    assert candidate_presenter["modelCandidates"] == 1
    assert candidate_presenter["approvedProviders"] == 0
    assert candidate_presenter["approvedModels"] == 0

    other = client.get(
        "/api/v1/studios/v1/capabilities",
        headers=auth(other_token),
        params={"workspace_id": other_workspace},
    )
    assert other.status_code == 200
    assert other.json()["workspaceId"] == other_workspace


def test_registry_api_requires_governance_and_keeps_approval_evidence_gated(client):
    owner_token, workspace = register(client, "registry-api-owner@example.com", "Registry API Studio")
    editor_token, _ = register(client, "registry-api-editor@example.com", "Editor Home")
    with SessionLocal() as db:
        editor = db.scalar(select(User).where(User.email == "registry-api-editor@example.com"))
        db.add(Membership(user_id=editor.id, workspace_id=workspace, role="Editor"))
        db.commit()

    provider_request = {
        "workspaceId": workspace,
        "capability": "PresenterProvider",
        "provider": "evaluation.presenter",
        "providerVersion": "v2",
        "sourceUrl": "https://example.invalid/presenter",
        "sourceRevision": "b" * 40,
        "codeLicense": "MIT",
        "riskClass": "biometric",
        "manifest": {},
    }
    forbidden = client.post(
        "/api/v1/studios/v1/providers",
        headers=auth(editor_token),
        json=provider_request,
    )
    assert forbidden.status_code == 403

    created = client.post(
        "/api/v1/studios/v1/providers",
        headers=auth(owner_token),
        json=provider_request,
    )
    assert created.status_code == 201, created.text
    provider = created.json()
    assert provider["status"] == "evaluation"

    incomplete = client.post(
        f"/api/v1/studios/v1/providers/{provider['id']}/approve",
        headers=auth(owner_token),
        params={"workspace_id": workspace},
    )
    assert incomplete.status_code == 422
    assert incomplete.json()["detail"]["code"] == "provider_manifest_incomplete"

    approved_provider = client.post(
        "/api/v1/studios/v1/providers",
        headers=auth(owner_token),
        json={
            **provider_request,
            "providerVersion": "v3",
            "manifest": {
                "sbom": "sha256:provider-sbom",
                "licenseEvidence": "official-license-review",
                "exitStrategy": "provider-neutral-voice-version",
                "benchmarkStatus": "pending",
            },
        },
    )
    assert approved_provider.status_code == 201
    provider_v3 = approved_provider.json()
    approval = client.post(
        f"/api/v1/studios/v1/providers/{provider_v3['id']}/approve",
        headers=auth(owner_token),
        params={"workspace_id": workspace},
    )
    assert approval.status_code == 200, approval.text
    assert approval.json()["status"] == "approved"

    model = client.post(
        "/api/v1/studios/v1/models",
        headers=auth(owner_token),
        json={
            "workspaceId": workspace,
            "providerRegistrationId": provider_v3["id"],
            "name": "Presenter evaluation model",
            "version": "v1",
            "digestSha256": "d" * 64,
            "modelLicense": "MIT",
            "commercialUse": "approved",
            "languages": ["pt-BR"],
            "capabilities": ["presenter"],
            "manifest": {
                "weightsSource": "official-model-card",
                "licenseEvidence": "official-model-card",
                "datasetDisclosure": "upstream-aggregate-disclosure",
                "deletionPolicy": "ephemeral-worker-copy",
                "benchmarkStatus": "pending",
            },
        },
    )
    assert model.status_code == 201, model.text
    approved_model = client.post(
        f"/api/v1/studios/v1/models/{model.json()['id']}/approve",
        headers=auth(owner_token),
        params={"workspace_id": workspace},
    )
    assert approved_model.status_code == 200, approved_model.text
    assert approved_model.json()["status"] == "approved"

    listed = client.get(
        "/api/v1/studios/v1/providers",
        headers=auth(owner_token),
        params={"workspace_id": workspace, "capability": "PresenterProvider"},
    )
    assert listed.status_code == 200
    assert {item["providerVersion"] for item in listed.json()} == {"v2", "v3"}

    # Registry approval is not worker advertisement: benchmarkStatus remains
    # pending and the readiness projection must keep the capability in review.
    readiness = client.get(
        "/api/v1/studios/v1/capabilities",
        headers=auth(owner_token),
        params={"workspace_id": workspace},
    ).json()
    presenter = next(item for item in readiness["capabilities"] if item["capability"] == "presenter")
    assert presenter["status"] == "blocked"
    assert presenter["providerReady"] is False
    assert presenter["benchmarkReady"] is False
    with SessionLocal() as db:
        event_types = {
            event.event_type
            for event in db.query(StudioDomainEvent)
            .filter(StudioDomainEvent.workspace_id == workspace)
            .all()
        }
    assert {
        "studio.provider.registered",
        "studio.provider.approved",
        "studio.model.registered",
        "studio.model.approved",
    }.issubset(event_types)


def test_stock_voice_readiness_requires_worker_advertisement_and_matching_benchmark_pair(client):
    token, workspace = register(client, "stock-readiness@example.com", "Stock Readiness")
    with SessionLocal() as db:
        provider = register_provider(
            db,
            capability="stock_voice",
            provider="fake.stock.voice",
            provider_version="v1",
            source_url="https://example.invalid/stock-voice",
            source_revision="a" * 40,
            code_license="MIT",
            risk_class="low",
            manifest={"benchmarkStatus": "passed", "workerAdvertised": False},
        )
        provider.status = "approved"
        model = register_model(
            db,
            provider_registration=provider,
            name="Fake stock voice",
            version="v1",
            digest_sha256="e" * 64,
            model_license="MIT",
            commercial_use="approved",
            languages=["pt-BR"],
            capabilities=["stock_voice"],
            manifest={"benchmarkStatus": "passed"},
        )
        model.status = "approved"
        db.commit()

    blocked = client.get(
        "/api/v1/studios/v1/capabilities",
        headers=auth(token),
        params={"workspace_id": workspace},
    )
    assert blocked.status_code == 200
    stock = next(item for item in blocked.json()["capabilities"] if item["capability"] == "stock_voice")
    assert stock["status"] == "review"
    assert stock["providerReady"] is False
    assert stock["benchmarkReady"] is False
    assert "worker_runtime_not_advertised" in stock["reasons"]

    with SessionLocal() as db:
        provider = db.scalar(
            select(StudioProviderRegistration).where(StudioProviderRegistration.provider == "fake.stock.voice")
        )
        provider.manifest = {**provider.manifest, "workerAdvertised": True}
        db.commit()

    ready = client.get(
        "/api/v1/studios/v1/capabilities",
        headers=auth(token),
        params={"workspace_id": workspace},
    )
    stock = next(item for item in ready.json()["capabilities"] if item["capability"] == "stock_voice")
    assert stock["status"] == "ready"
    assert stock["providerReady"] is True
    assert stock["benchmarkReady"] is True
