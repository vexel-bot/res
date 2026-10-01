"""Loopback-only control API for the isolated diffusion worker."""

from __future__ import annotations

import hmac
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from uuid import UUID

from execution_store import atomic_json, file_sha256, lease_stale, process_identity, process_matches, request_digest
from model_store import quick_status as model_status
from fastapi import FastAPI, Header, HTTPException, Request, status
from preflight import _environment_status, inspect
from profile_registry import get_profile, list_profiles
from pydantic import BaseModel, Field

app = FastAPI(title="res local media generation", docs_url=None, redoc_url=None)
ROOT = Path(__file__).resolve().parent
RUNS = ROOT / ".runs"
RUNS.mkdir(exist_ok=True)
GPU_LEASE = RUNS / ".heavy-media-lease.json"


class GenerateScene(BaseModel):
    schemaVersion: str = Field(pattern=r"^studio\.scene-generation-request\.v[12]$")
    operation: str = Field(pattern=r"^text_to_video$")
    prompt: str = Field(min_length=1, max_length=4000)
    seed: int = Field(ge=0, le=2**63 - 1)
    durationSeconds: float = Field(gt=0, le=2.0)
    profileId: str = Field(pattern=r"^[a-z0-9][a-z0-9.-]{2,119}$")
    cameraIntent: dict = Field(default_factory=dict)
    executionId: str = Field(pattern=r"^[0-9a-f-]{36}$")


def _authorize(request: Request, authorization: str | None):
    host = request.client.host if request.client else ""
    if host not in {"127.0.0.1", "::1", "localhost", "testclient"}:
        raise HTTPException(status_code=403, detail="loopback_required")
    expected = os.environ.get("RES_LOCAL_DIFFUSION_TOKEN", "")
    supplied = (authorization or "").removeprefix("Bearer ")
    if len(expected) < 32 or not hmac.compare_digest(expected, supplied):
        raise HTTPException(status_code=401, detail="internal_token_required")


def _run_directory(execution_id):
    try:
        normalized = str(UUID(execution_id))
    except ValueError as error:
        raise HTTPException(status_code=404, detail="execution_not_found") from error
    if normalized != execution_id:
        raise HTTPException(status_code=404, detail="execution_not_found")
    return RUNS / normalized


def _read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _release_owned_lease(execution_id: str):
    lease = _read_json(GPU_LEASE)
    if lease and lease.get("executionId") == execution_id:
        GPU_LEASE.unlink(missing_ok=True)


def _recover_stale_lease():
    lease = _read_json(GPU_LEASE)
    if not lease:
        GPU_LEASE.unlink(missing_ok=True)
        return
    if lease.get("ownerType") != "local_diffusion":
        if process_matches(lease):
            return
        GPU_LEASE.unlink(missing_ok=True)
        return
    try:
        directory = _run_directory(lease["executionId"])
    except (KeyError, HTTPException):
        GPU_LEASE.unlink(missing_ok=True)
        return
    descriptor = _read_json(directory / "process.json")
    if lease_stale(lease, descriptor):
        GPU_LEASE.unlink(missing_ok=True)


def _known_result(directory: Path, execution_id: str):
    result = _read_json(directory / "receipt.json")
    if result is not None:
        _release_owned_lease(execution_id)
        return result
    descriptor = _read_json(directory / "process.json")
    request = _read_json(directory / "request.json") or {}
    if not descriptor and time.time() - float(request.get("createdAt", directory.stat().st_mtime)) > 30:
        _release_owned_lease(execution_id)
        failure = {"executionId": execution_id, "status": "failed", "reason": "supervisor_not_started"}
        atomic_json(directory / "receipt.json", failure)
        return failure
    if descriptor and not process_matches(descriptor):
        _release_owned_lease(execution_id)
        failure = {"executionId": execution_id, "status": "failed", "reason": "supervisor_exited_without_receipt"}
        atomic_json(directory / "receipt.json", failure)
        return failure
    return {"executionId": execution_id, "status": "running"}


@app.get("/api/v1/capabilities")
def capabilities(request: Request, authorization: str | None = Header(default=None)):
    _authorize(request, authorization)
    results = []
    environment = _environment_status()
    for profile in list_profiles():
        admission = inspect(
            profile_id=profile["profileId"],
            phase="execution",
            check_environment=True,
            environment_status=environment,
        )
        provisioned = model_status(profile["profileId"])
        adapter_supported = profile.get("adapter") == "animatediff_lightning"
        qualification = profile.get("status", "unavailable") if adapter_supported else "unavailable"
        results.append(
            {
                **admission,
                "resourceAdmission": admission["status"],
                "modelReadiness": provisioned.get("status", "unavailable"),
                "adapterSupport": "available" if adapter_supported else "unavailable",
                "qualificationState": qualification,
                "usableNow": bool(
                    admission["status"] == "admitted"
                    and provisioned.get("status") == "ready"
                    and adapter_supported
                    and qualification in {"experimental", "qualified"}
                ),
            }
        )
    return {"schemaVersion": "res.local-video-capabilities.v2", "profiles": results}


@app.post("/api/v1/generate-scene", status_code=status.HTTP_202_ACCEPTED)
def generate_scene(payload: GenerateScene, request: Request, authorization: str | None = Header(default=None)):
    _authorize(request, authorization)
    profile = get_profile(payload.profileId)
    if payload.durationSeconds > float(profile["maximumDurationSeconds"]):
        raise HTTPException(status_code=409, detail="scene_generation_duration_unavailable")
    execution_id = payload.executionId
    directory = _run_directory(execution_id)
    body = payload.model_dump()
    digest = request_digest(body)
    if directory.exists():
        stored = _read_json(directory / "request.json")
        if stored and stored.get("requestDigest") != digest:
            raise HTTPException(status_code=409, detail="execution_payload_conflict")
        return _known_result(directory, execution_id)
    admission = inspect(profile_id=profile["profileId"], phase="execution", check_environment=True)
    if admission["status"] != "admitted":
        raise HTTPException(status_code=409, detail=admission)
    _recover_stale_lease()
    try:
        descriptor = os.open(GPU_LEASE, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(descriptor, "w", encoding="utf-8") as lease:
            json.dump(
                {
                    "executionId": execution_id,
                    "createdAt": time.time(),
                    "state": "initializing",
                    "ownerType": "local_diffusion",
                    "pid": os.getpid(),
                    "identity": process_identity(os.getpid()),
                },
                lease,
            )
    except FileExistsError as error:
        raise HTTPException(status_code=409, detail="gpu_execution_in_progress") from error
    try:
        directory.mkdir()
        frozen_profile = json.loads(json.dumps(profile, sort_keys=True))
        atomic_json(
            directory / "request.json",
            {
                **body,
                "requestDigest": digest,
                "createdAt": time.time(),
                "profileSnapshot": frozen_profile,
                "profileDigestSha256": request_digest(frozen_profile),
                "runtimeDigests": {
                    "api": file_sha256(ROOT / "api.py"),
                    "supervisor": file_sha256(ROOT / "supervisor.py"),
                    "runner": file_sha256(ROOT / "runner.py"),
                    "adapter": file_sha256(ROOT / "adapters" / "animatediff_lightning.py"),
                    "lock": file_sha256(ROOT / "requirements.lock"),
                },
            },
        )
        stdout = (directory / "stdout.log").open("w", encoding="utf-8")
        stderr = (directory / "stderr.log").open("w", encoding="utf-8")
        try:
            process = subprocess.Popen(
                [
                    sys.executable,
                    str(ROOT / "supervisor.py"),
                    str(directory / "request.json"),
                    str(directory / "candidate.mp4"),
                    str(directory / "receipt.json"),
                ],
                stdout=stdout,
                stderr=stderr,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
                | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
                start_new_session=os.name != "nt",
            )
        finally:
            stdout.close()
            stderr.close()
        identity = process_identity(process.pid)
        if identity is None:
            process.kill()
            raise RuntimeError("supervisor_identity_unavailable")
        atomic_json(directory / "process.json", {"pid": process.pid, "identity": identity, "createdAt": time.time()})
        atomic_json(
            GPU_LEASE,
            {
                "executionId": execution_id,
                "createdAt": time.time(),
                "state": "running",
                "ownerType": "local_diffusion",
                "pid": process.pid,
                "identity": identity,
            },
        )
    except Exception:
        _release_owned_lease(execution_id)
        raise
    return {"executionId": execution_id, "status": "running", "preflight": admission}


@app.get("/api/v1/executions/{execution_id}")
def execution(execution_id: str, request: Request, authorization: str | None = Header(default=None)):
    _authorize(request, authorization)
    directory = _run_directory(execution_id)
    if not directory.is_dir():
        raise HTTPException(status_code=404, detail="execution_not_found")
    return _known_result(directory, execution_id)


@app.post("/api/v1/executions/{execution_id}/cancel")
def cancel_execution(execution_id: str, request: Request, authorization: str | None = Header(default=None)):
    _authorize(request, authorization)
    directory = _run_directory(execution_id)
    descriptor = _read_json(directory / "process.json")
    if not directory.is_dir() or not descriptor:
        raise HTTPException(status_code=404, detail="execution_not_found")
    if not process_matches(descriptor):
        existing = _read_json(directory / "receipt.json")
        if existing:
            return existing
        raise HTTPException(status_code=409, detail="execution_process_identity_mismatch")
    pid = int(descriptor["pid"])
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            timeout=15,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    else:
        os.killpg(pid, signal.SIGTERM)
    deadline = time.monotonic() + 10
    while process_matches(descriptor) and time.monotonic() < deadline:
        time.sleep(0.1)
    if process_matches(descriptor):
        raise HTTPException(status_code=409, detail="execution_cancel_not_confirmed")
    receipt = {"executionId": execution_id, "status": "cancelled"}
    atomic_json(directory / "receipt.json", receipt)
    _release_owned_lease(execution_id)
    return receipt
