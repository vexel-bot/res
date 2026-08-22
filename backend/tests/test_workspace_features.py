from conftest import register


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_workspace_resources_are_persistent_and_audited(client):
    token, workspace_id = register(client, "features@example.com")
    created = client.post(
        "/api/v1/workspace-resources",
        headers=auth(token),
        json={
            "workspaceId": workspace_id,
            "kind": "template",
            "resourceKey": "template-1",
            "payload": {"id": "template-1", "name": "Modelo persistido"},
        },
    )
    assert created.status_code == 201, created.text
    resource_id = created.json()["id"]

    listed = client.get(
        f"/api/v1/workspace-resources?workspace_id={workspace_id}&kind=template",
        headers=auth(token),
    )
    assert listed.status_code == 200
    assert listed.json()[0]["payload"]["name"] == "Modelo persistido"

    updated = client.patch(
        f"/api/v1/workspace-resources/{resource_id}?workspace_id={workspace_id}",
        headers=auth(token),
        json={"payload": {"id": "template-1", "name": "Modelo atualizado"}},
    )
    assert updated.status_code == 200
    assert updated.json()["payload"]["name"] == "Modelo atualizado"

    governance = client.get(f"/api/v1/workspace-features/{workspace_id}/governance", headers=auth(token))
    assert governance.status_code == 200
    assert any(item["resource"] == "template" for item in governance.json()["auditLogs"])


def test_settings_team_and_subscription_flow(client):
    token, workspace_id = register(client, "owner@example.com")

    settings = client.put(
        f"/api/v1/workspace-features/{workspace_id}/settings/me",
        headers=auth(token),
        json={"settings": {"appearance": {"theme": "dark"}}, "auxiliary": {"twoFactor": True}},
    )
    assert settings.status_code == 200
    loaded = client.get(f"/api/v1/workspace-features/{workspace_id}/settings/me", headers=auth(token))
    assert loaded.json()["settings"]["appearance"]["theme"] == "dark"

    company = client.put(
        f"/api/v1/workspace-features/{workspace_id}/company",
        headers=auth(token),
        json={
            "legalName": "Empresa Teste Ltda.",
            "brandName": "Marca Teste",
            "taxId": "12.345.678/0001-90",
            "site": "https://example.com",
            "email": "contato@example.com",
            "phone": "+55 11 99999-0000",
            "language": "pt-BR",
            "timezone": "America/Sao_Paulo",
        },
    )
    assert company.status_code == 200, company.text
    company_loaded = client.get(f"/api/v1/workspace-features/{workspace_id}/company", headers=auth(token))
    assert company_loaded.status_code == 200
    assert company_loaded.json()["brandName"] == "Marca Teste"
    governance_after_company = client.get(f"/api/v1/workspace-features/{workspace_id}/governance", headers=auth(token))
    assert governance_after_company.json()["workspace"]["name"] == "Marca Teste"

    invited = client.post(
        f"/api/v1/workspace-features/{workspace_id}/members",
        headers=auth(token),
        json={"name": "Colaborador", "email": "colaborador@example.com", "modules": ["dashboard"]},
    )
    assert invited.status_code == 201, invited.text
    assert invited.json()["status"] == "invited"

    changed = client.patch(
        f"/api/v1/workspace-features/{workspace_id}/subscription",
        headers=auth(token),
        json={"planId": "business"},
    )
    assert changed.status_code == 200
    governance = client.get(f"/api/v1/workspace-features/{workspace_id}/governance", headers=auth(token)).json()
    assert governance["subscription"]["planId"] == "business"
    assert any(item["email"] == "colaborador@example.com" for item in governance["users"])


def test_workspace_features_enforce_tenant_and_private_resource_boundaries(client):
    first_token, first_workspace = register(client, "first-features@example.com")
    second_token, _ = register(client, "second-features@example.com")

    forbidden_workspace = client.get(
        f"/api/v1/workspace-resources?workspace_id={first_workspace}&kind=template",
        headers=auth(second_token),
    )
    assert forbidden_workspace.status_code == 404

    private_kind = client.get(
        f"/api/v1/workspace-resources?workspace_id={first_workspace}&kind=user_settings",
        headers=auth(first_token),
    )
    assert private_kind.status_code == 400

    solo = client.patch(
        f"/api/v1/workspace-features/{first_workspace}/subscription",
        headers=auth(first_token),
        json={"planId": "solo"},
    )
    assert solo.status_code == 200
    over_capacity = client.post(
        f"/api/v1/workspace-features/{first_workspace}/members",
        headers=auth(first_token),
        json={"name": "Sem vaga", "email": "no-seat@example.com", "modules": ["dashboard"]},
    )
    assert over_capacity.status_code == 409


def test_ai_chat_history_resource_is_persistent(client):
    token, workspace_id = register(client, "chat-history@example.com")
    created = client.post(
        "/api/v1/workspace-resources",
        headers=auth(token),
        json={
            "workspaceId": workspace_id,
            "kind": "ai_chat",
            "resourceKey": "default",
            "payload": {"messages": [{"id": "m1", "role": "user", "content": "Olá"}]},
        },
    )
    assert created.status_code == 201, created.text
    resource_id = created.json()["id"]

    updated = client.patch(
        f"/api/v1/workspace-resources/{resource_id}?workspace_id={workspace_id}",
        headers=auth(token),
        json={
            "payload": {
                "messages": [
                    {"id": "m1", "role": "user", "content": "Olá"},
                    {"id": "m2", "role": "assistant", "content": "Como posso ajudar?"},
                ]
            }
        },
    )
    assert updated.status_code == 200

    listed = client.get(
        f"/api/v1/workspace-resources?workspace_id={workspace_id}&kind=ai_chat",
        headers=auth(token),
    )
    assert listed.status_code == 200
    assert len(listed.json()[0]["payload"]["messages"]) == 2


def test_integration_and_presenter_states_are_persistent_and_tenant_isolated(client):
    token, workspace_id = register(client, "production-state@example.com")
    other_token, _ = register(client, "production-state-other@example.com")

    integration = client.post(
        "/api/v1/workspace-resources",
        headers=auth(token),
        json={
            "workspaceId": workspace_id,
            "kind": "connected_account",
            "resourceKey": "instagram",
            "payload": {
                "provider": "instagram",
                "status": "verified",
                "externalPublishing": False,
                "lastTestedAt": "2026-08-18T12:00:00Z",
            },
        },
    )
    assert integration.status_code == 201, integration.text
    assert integration.json()["payload"]["externalPublishing"] is False

    presenter = client.post(
        "/api/v1/workspace-resources",
        headers=auth(token),
        json={
            "workspaceId": workspace_id,
            "kind": "presenter_session",
            "resourceKey": "post-ritual",
            "payload": {"generated": True, "captured": False, "scenario": ""},
        },
    )
    assert presenter.status_code == 201, presenter.text
    presenter_id = presenter.json()["id"]

    updated = client.patch(
        f"/api/v1/workspace-resources/{presenter_id}?workspace_id={workspace_id}",
        headers=auth(token),
        json={"payload": {"generated": True, "captured": True, "scenario": "yes"}},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["payload"]["scenario"] == "yes"

    listed = client.get(
        f"/api/v1/workspace-resources?workspace_id={workspace_id}&kind=presenter_session",
        headers=auth(token),
    )
    assert listed.status_code == 200
    assert listed.json()[0]["payload"]["captured"] is True

    isolated = client.get(
        f"/api/v1/workspace-resources?workspace_id={workspace_id}&kind=connected_account",
        headers=auth(other_token),
    )
    assert isolated.status_code == 404


def test_support_tickets_are_persistent_validated_and_tenant_isolated(client):
    token, workspace_id = register(client, "support-owner@example.com")
    other_token, _ = register(client, "support-other@example.com")

    invalid = client.post(
        f"/api/v1/workspace-features/{workspace_id}/support-tickets",
        headers=auth(token),
        json={"subject": "technical", "title": "Oi", "details": "curto"},
    )
    assert invalid.status_code == 422

    created = client.post(
        f"/api/v1/workspace-features/{workspace_id}/support-tickets",
        headers=auth(token),
        json={
            "subject": "technical",
            "title": "Falha ao salvar uma publicação",
            "details": "A publicação retorna erro ao concluir o salvamento.",
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["status"] == "open"

    listed = client.get(
        f"/api/v1/workspace-features/{workspace_id}/support-tickets",
        headers=auth(token),
    )
    assert listed.status_code == 200
    assert listed.json()[0]["title"] == "Falha ao salvar uma publicação"

    isolated = client.get(
        f"/api/v1/workspace-features/{workspace_id}/support-tickets",
        headers=auth(other_token),
    )
    assert isolated.status_code == 404
