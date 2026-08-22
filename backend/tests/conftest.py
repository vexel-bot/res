import os

os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = "sqlite:///./nexus-test.db"
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production"
os.environ.pop("AI_API_KEY", None)

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def register(client: TestClient, email: str, workspace: str = "Marca Teste") -> tuple[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "name": "Usuário Teste", "password": "senha-segura-123", "workspaceName": workspace},
    )
    assert response.status_code == 201, response.text
    token = response.json()["accessToken"]
    bootstrap = client.get("/api/v1/bootstrap", headers={"Authorization": f"Bearer {token}"})
    assert bootstrap.status_code == 200
    return token, bootstrap.json()["workspaces"][0]["id"]
