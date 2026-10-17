import importlib.util
import sys
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient


def _module():
    root = Path(__file__).resolve().parents[2] / "workers" / "media-generation-local"
    sys.path.insert(0, str(root))
    spec = importlib.util.spec_from_file_location("res_local_diffusion_api", root / "api.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _payload(execution_id):
    return {
        "schemaVersion": "studio.scene-generation-request.v2",
        "operation": "text_to_video",
        "prompt": "A controlled visual benchmark with visible subject motion",
        "seed": 42,
        "durationSeconds": 1,
        "profileId": "animatediff-lightning-sd15-a-v1",
        "cameraIntent": {"type": "static", "control": "prompt_guidance"},
        "executionId": execution_id,
    }


def _client(module, tmp_path, monkeypatch):
    token = "local-test-token-0123456789abcdef"
    monkeypatch.setenv("RES_LOCAL_DIFFUSION_TOKEN", token)
    monkeypatch.setattr(module, "RUNS", tmp_path)
    monkeypatch.setattr(module, "GPU_LEASE", tmp_path / ".gpu-lease.json")
    return TestClient(module.app), {"Authorization": f"Bearer {token}"}


def test_generate_blocks_before_creating_execution_or_model_directory(tmp_path, monkeypatch):
    module = _module()
    client, headers = _client(module, tmp_path, monkeypatch)
    monkeypatch.setattr(
        module,
        "inspect",
        lambda **_: {"status": "blocked_resources", "reasons": ["blocked_current_load"]},
    )
    execution_id = str(uuid4())

    response = client.post("/api/v1/generate-scene", headers=headers, json=_payload(execution_id))

    assert response.status_code == 409
    assert response.json()["detail"]["status"] == "blocked_resources"
    assert not (tmp_path / execution_id).exists()
    assert not module.GPU_LEASE.exists()


def test_known_execution_is_returned_before_a_new_preflight(tmp_path, monkeypatch):
    module = _module()
    client, headers = _client(module, tmp_path, monkeypatch)
    execution_id = str(uuid4())
    payload = _payload(execution_id)
    normalized = module.GenerateScene(**payload).model_dump()
    directory = tmp_path / execution_id
    directory.mkdir()
    module.atomic_json(
        directory / "request.json",
        {**normalized, "requestDigest": module.request_digest(normalized)},
    )
    module.atomic_json(directory / "receipt.json", {"executionId": execution_id, "status": "candidate_generated"})

    def unexpected_preflight(**_):
        raise AssertionError("known execution must be read before preflight")

    monkeypatch.setattr(module, "inspect", unexpected_preflight)

    response = client.post("/api/v1/generate-scene", headers=headers, json=payload)

    assert response.status_code == 202
    assert response.json()["status"] == "candidate_generated"


def test_known_execution_rejects_a_different_payload(tmp_path, monkeypatch):
    module = _module()
    client, headers = _client(module, tmp_path, monkeypatch)
    execution_id = str(uuid4())
    payload = _payload(execution_id)
    normalized = module.GenerateScene(**payload).model_dump()
    directory = tmp_path / execution_id
    directory.mkdir()
    module.atomic_json(
        directory / "request.json",
        {**normalized, "requestDigest": module.request_digest(normalized)},
    )
    changed = {**payload, "prompt": "A different request cannot reuse this execution identity"}

    response = client.post("/api/v1/generate-scene", headers=headers, json=changed)

    assert response.status_code == 409
    assert response.json()["detail"] == "execution_payload_conflict"


def test_cancel_requires_matching_identity_and_confirms_termination(tmp_path, monkeypatch):
    module = _module()
    client, headers = _client(module, tmp_path, monkeypatch)
    execution_id = str(uuid4())
    directory = tmp_path / execution_id
    directory.mkdir()
    descriptor = {"pid": 1234, "identity": "test-process-identity"}
    module.atomic_json(directory / "process.json", descriptor)
    module.atomic_json(module.GPU_LEASE, {"executionId": execution_id, "createdAt": 1})
    matches = iter((True, False, False))
    monkeypatch.setattr(module, "process_matches", lambda _: next(matches))
    terminated = []
    monkeypatch.setattr(module.os, "name", "nt")
    monkeypatch.setattr(module.subprocess, "run", lambda command, **_: terminated.append(command))

    response = client.post(f"/api/v1/executions/{execution_id}/cancel", headers=headers)

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    assert terminated == [["taskkill", "/PID", "1234", "/T", "/F"]]
    assert not module.GPU_LEASE.exists()


def test_interrupted_initialization_becomes_a_durable_failure(tmp_path, monkeypatch):
    module = _module()
    client, headers = _client(module, tmp_path, monkeypatch)
    execution_id = str(uuid4())
    directory = tmp_path / execution_id
    directory.mkdir()
    module.atomic_json(directory / "request.json", {"createdAt": 1})
    module.atomic_json(module.GPU_LEASE, {"executionId": execution_id, "createdAt": 1})

    response = client.get(f"/api/v1/executions/{execution_id}", headers=headers)

    assert response.status_code == 200
    assert response.json()["reason"] == "supervisor_not_started"
    assert (directory / "receipt.json").is_file()
    assert not module.GPU_LEASE.exists()
