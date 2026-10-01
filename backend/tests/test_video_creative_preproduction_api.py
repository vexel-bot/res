from __future__ import annotations

from conftest import register


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_casebook_and_animatic_are_private_governed_read_models(client) -> None:
    assert client.get("/api/v1/studios/v1/creative/casebook").status_code == 401
    token, _workspace = register(client, "creative-casebook@example.com")

    response = client.get(
        "/api/v1/studios/v1/creative/casebook",
        headers=auth(token),
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert len(payload["cases"]) == 12
    assert all(item["publicationAuthorized"] is False for item in payload["cases"])
    selected = payload["cases"][0]
    assert selected["storyboard"]["status"] == "ready_for_review"
    assert selected["animatic"]["status"] == "rendered"

    animatic = client.get(
        f"/api/v1/studios/v1/creative/cases/{selected['caseId']}/animatic",
        headers=auth(token),
    )
    assert animatic.status_code == 200, animatic.text
    assert animatic.headers["content-type"].startswith("video/mp4")
    assert animatic.headers["x-clicko-placeholder"] == "true"
    assert animatic.headers["x-clicko-publication-authorized"] == "false"
    assert len(animatic.content) > 10_000


def test_unknown_animatic_is_not_disclosed(client) -> None:
    token, _workspace = register(client, "creative-casebook-missing@example.com")
    response = client.get(
        "/api/v1/studios/v1/creative/cases/not-a-case/animatic",
        headers=auth(token),
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "animatic_not_found"


def test_assisted_intelligence_is_private_and_exposes_three_reversible_choices(client) -> None:
    path = "/api/v1/studios/v1/creative/assisted-intelligence"
    assert client.get(path).status_code == 401
    token, _workspace = register(client, "creative-assistance@example.com")

    response = client.get(path, headers=auth(token))

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["eligible"] is True
    assert len(payload["cases"]) == 12
    for item in payload["cases"]:
        assert len(item["optionSet"]["options"]) == 3
        assert item["optionSet"]["repair"]
        assert {decision["decision"] for decision in item["reviewedPlan"]["decisions"]} == {
            "accept",
            "reject",
            "adjust",
        }
        assert item["reviewedPlan"]["beforeSnapshotDigestSha256"] == (
            item["reviewedPlan"]["inverseSnapshotDigestSha256"]
        )


def test_factory_program_is_private_and_does_not_forge_human_approval(client) -> None:
    path = "/api/v1/studios/v1/creative/factory-program"
    assert client.get(path).status_code == 401
    token, _workspace = register(client, "creative-factory@example.com")

    response = client.get(path, headers=auth(token))

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["producedArtifactCount"] == 36
    assert payload["humanApprovedCount"] == 0
    assert payload["externalPublicationCount"] == 0
    assert payload["completed"] is False
    assert len(payload["pilot"]["jobs"]) == 12
    assert len(payload["calibration"]["jobs"]) == 24
    assert len(payload["scale"]["jobs"]) == 64
    assert all(job["humanReviewStatus"] == "rejected" for job in payload["pilot"]["jobs"])
    assert all(
        job["humanReviewStatus"] == "rejected"
        for job in payload["calibration"]["jobs"]
    )
    assert "creative_replan_required" in payload["blockers"]
    assert all(job["status"] == "blocked_by_gate" for job in payload["scale"]["jobs"])


def test_replan_state_is_private_and_allows_only_one_golden_after_decisions(client) -> None:
    path = "/api/v1/studios/v1/creative/replan-state"
    assert client.get(path).status_code == 401
    token, _workspace = register(client, "creative-replan@example.com")

    response = client.get(path, headers=auth(token))

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["approvedDecisionCount"] == 0
    assert payload["goldenProductionEligible"] is False
    assert payload["goldenJobLimit"] == 1
    assert payload["batchDispatchAuthorized"] is False
    assert payload["rejectedArtifactReuseAuthorized"] is False
    assert payload["externalPublicationAuthorized"] is False


def test_advanced_capability_audit_is_private_and_keeps_registry_empty(client) -> None:
    path = "/api/v1/studios/v1/creative/advanced-capabilities"
    assert client.get(path).status_code == 401
    token, _workspace = register(client, "creative-advanced-audit@example.com")

    response = client.get(path, headers=auth(token))

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["activationEligible"] is False
    assert payload["authorizedIdentityCount"] == 0
    assert payload["executedBenchmarkCaseCount"] == 0
    assert payload["enabledProviderIds"] == []
    assert all(item["biometricInferenceExecuted"] is False for item in payload["candidates"])


def test_autonomy_audit_is_private_and_separates_implementation_from_completion(client) -> None:
    path = "/api/v1/studios/v1/creative/autonomy-audit"
    assert client.get(path).status_code == 401
    token, _workspace = register(client, "creative-program-audit@example.com")

    response = client.get(path, headers=auth(token))

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["implementationComplete"] is True
    assert payload["objectiveComplete"] is False
    assert payload["producedPrivateArtifactCount"] == 36
    assert payload["humanApprovedArtifactCount"] == 0
    assert payload["dispatchedScaleJobCount"] == 0
    assert payload["phases"][5]["operationalStatus"] == "rejected_replan_required"


def test_expensive_avatar_job_is_blocked_by_unapproved_bound_animatic(client) -> None:
    token, workspace = register(client, "creative-expensive-gate@example.com")
    casebook = client.get(
        "/api/v1/studios/v1/creative/casebook",
        headers=auth(token),
    ).json()
    creative_case = casebook["cases"][0]
    document = client.post(
        "/api/v1/studios/v1/documents",
        headers=auth(token),
        json={
            "workspaceId": workspace,
            "title": "Documento com pré-produção",
            "contentType": "video",
            "brandRevision": 1,
            "brief": {"objective": "Validar gate", "audience": "Equipe"},
            "composition": {
                "pages": [{"id": "scene-1", "width": 1080, "height": 1920, "layers": []}],
                "narrative": {
                    "creativeCaseId": creative_case["caseId"],
                    "storyboardId": creative_case["storyboard"]["storyboardId"],
                    "animaticId": creative_case["animatic"]["animaticId"],
                    "expensiveRenderEligible": False,
                },
                "mediaTimeline": {
                    "frameRate": {"numerator": 30, "denominator": 1},
                    "durationFrames": 30,
                    "tracks": [],
                },
            },
        },
    )
    assert document.status_code == 201, document.text

    response = client.post(
        "/api/v1/studios/v1/jobs",
        headers={**auth(token), "Idempotency-Key": "creative-expensive-gate-001"},
        json={
            "workspaceId": workspace,
            "documentId": document.json()["documentId"],
            "jobType": "avatar_video",
            "provider": "unapproved.avatar",
            "identityVersionId": "identity-version-pending",
            "voiceVersionId": "voice-version-pending",
            "consentGrantId": "consent-pending",
        },
    )
    assert response.status_code == 409, response.text
    detail = response.json()["detail"]
    assert detail["code"] == "creative_preproduction_approval_required"
    assert "animatic_human_approval_required" in detail["blockers"]
    assert "storyboard_asset_rights_pending" in detail["blockers"]
