from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from pydantic import BaseModel, ConfigDict, Field

from preflight import MANIFEST_PATH, ROOT, evaluate

app = FastAPI(title="res LongCat avatar worker", version="0.1.0")
TOKEN = os.getenv("LONGCAT_WORKER_TOKEN")


class AvatarExecutionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    execution_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{7,159}$")
    profile_id: str
    request_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    reference_image_checksum_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    driving_audio_checksum_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    segment_count: int = Field(gt=0, le=10_000)
    produced_frames: int = Field(gt=0)
    trim_tail_ms: int = Field(ge=0)


def authorize(authorization: Annotated[str | None, Header()] = None) -> None:
    if not TOKEN or authorization != f"Bearer {TOKEN}":
        raise HTTPException(status_code=401, detail={"code": "worker_authentication_failed"})


@app.get("/api/v1/capabilities")
def capabilities(authorization: Annotated[str | None, Header()] = None) -> dict:
    authorize(authorization)
    return evaluate(Path(os.environ["LONGCAT_MODEL_ROOT"]) if os.getenv("LONGCAT_MODEL_ROOT") else None)


def _write_verified(upload: UploadFile, destination: Path, expected_sha256: str) -> None:
    digest = hashlib.sha256()
    with destination.open("wb") as stream:
        while chunk := upload.file.read(1024 * 1024):
            digest.update(chunk)
            stream.write(chunk)
    if digest.hexdigest() != expected_sha256:
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail={"code": "input_checksum_mismatch"})


def _run_directory(execution_id: str) -> Path:
    allowed_root = Path(os.getenv("LONGCAT_RUN_ROOT", ROOT / ".runs")).resolve()
    run_root = (allowed_root / execution_id).resolve()
    if run_root.parent != allowed_root:
        raise HTTPException(status_code=422, detail={"code": "execution_path_invalid"})
    return run_root


@app.post("/api/v1/executions", status_code=202)
def create_execution(
    metadata: Annotated[str, Form()],
    reference_image: Annotated[UploadFile, File()],
    driving_audio: Annotated[UploadFile, File()],
    authorization: Annotated[str | None, Header()] = None,
) -> dict:
    authorize(authorization)
    try:
        request = AvatarExecutionRequest.model_validate_json(metadata)
    except ValueError as error:
        raise HTTPException(status_code=422, detail={"code": "request_invalid"}) from error
    preflight = evaluate(Path(os.environ["LONGCAT_MODEL_ROOT"]) if os.getenv("LONGCAT_MODEL_ROOT") else None)
    if not preflight["usableNow"]:
        raise HTTPException(
            status_code=409,
            detail={
                "schemaVersion": "studio.longcat-execution-receipt.v1",
                "executionId": request.execution_id,
                "profileId": request.profile_id,
                "status": "blocked_resources",
                "reasons": preflight["reasons"],
                "requestDigestSha256": request.request_digest_sha256,
                "manifestRevision": json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))["source"]["revision"],
            },
        )
    run_root = _run_directory(request.execution_id)
    receipt_path = run_root / "receipt.json"
    if receipt_path.is_file():
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if receipt.get("requestDigestSha256") != request.request_digest_sha256:
            raise HTTPException(status_code=409, detail={"code": "execution_id_conflict"})
        return receipt
    run_root.parent.mkdir(parents=True, exist_ok=True)
    run_root.mkdir(parents=False, exist_ok=False)
    _write_verified(reference_image, run_root / "reference-image", request.reference_image_checksum_sha256)
    _write_verified(driving_audio, run_root / "driving-audio", request.driving_audio_checksum_sha256)
    receipt = {
        "schemaVersion": "studio.longcat-execution-receipt.v1",
        "executionId": request.execution_id,
        "profileId": request.profile_id,
        "status": "blocked_runtime",
        "requestDigestSha256": request.request_digest_sha256,
        "segmentCount": request.segment_count,
        "producedFrames": request.produced_frames,
        "trimTailMs": request.trim_tail_ms,
        "modelDownloadStarted": False,
        "inferenceStarted": False,
    }
    receipt_path.write_text(json.dumps(receipt, sort_keys=True), encoding="utf-8")
    raise HTTPException(
        status_code=409,
        detail={**receipt, "code": "longcat_runtime_not_qualified"},
    )


@app.get("/api/v1/executions/{execution_id}")
def get_execution(
    execution_id: str,
    authorization: Annotated[str | None, Header()] = None,
) -> dict:
    authorize(authorization)
    receipt_path = _run_directory(execution_id) / "receipt.json"
    if not receipt_path.is_file():
        raise HTTPException(status_code=404, detail={"code": "execution_not_found"})
    return json.loads(receipt_path.read_text(encoding="utf-8"))


@app.post("/api/v1/executions/{execution_id}/cancel")
def cancel_execution(
    execution_id: str,
    authorization: Annotated[str | None, Header()] = None,
) -> dict:
    authorize(authorization)
    receipt_path = _run_directory(execution_id) / "receipt.json"
    if not receipt_path.is_file():
        raise HTTPException(status_code=404, detail={"code": "execution_not_found"})
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("status") in {"queued", "running"}:
        receipt["status"] = "cancel_requested"
        receipt_path.write_text(json.dumps(receipt, sort_keys=True), encoding="utf-8")
    return receipt
