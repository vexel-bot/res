# ruff: noqa: E402
import atexit
import os
import shutil
import tempfile
from pathlib import Path

os.environ["ENVIRONMENT"] = "test"
_test_db_dir = Path(tempfile.mkdtemp(prefix="res-studio-tests-")).resolve()
os.environ["DATABASE_URL"] = "sqlite:///" + (_test_db_dir / "nexus-test.db").as_posix()
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production"
os.environ.pop("AI_API_KEY", None)
# Unit/integration tests must never inherit a paid local provider from .env.
os.environ["STUDIO_EDITING_AI_PLANNING_PROVIDER"] = "none"
os.environ["STUDIO_PRODUCTION_TEST_BUDGET_USD"] = "0"
os.environ["STUDIO_VISUAL_QUALITY_INDICATOR_ENABLED"] = "false"
os.environ["OPENAI_OUTBOUND_ENABLED"] = "false"
os.environ["OPENAI_VIDEO_GENERATION_ENABLED"] = "false"
os.environ["HYPERFRAMES_ENABLED"] = "false"
os.environ["MOTION_CANVAS_ENABLED"] = "false"
os.environ["STUDIO_EDITORIAL_MOTION_PROVIDER"] = "hyperframes.contextual-v2"

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app


def _cleanup_test_database():
    engine.dispose()
    shutil.rmtree(_test_db_dir, ignore_errors=True)


atexit.register(_cleanup_test_database)


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
