from __future__ import annotations

import hashlib
import hmac
import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse

from preflight import ROOT, evaluate, sha256_file
from protocol import AvatarExecutionRequest
from runner import atomic_json, run

TOKEN = os.getenv("LONGCAT_WORKER_TOKEN")
_lock = threading.RLock()
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="longcat")
_futures = {}


def run_root() -> Path:
    return Path(os.getenv("LONGCAT_RUN_ROOT", ROOT / ".runs")).resolve()


def run_directory(execution_id: str) -> Path:
    root = run_root()
    candidate = root / execution_id
    directory = candidate.resolve()
    if directory.parent != root or candidate.is_symlink():
        raise HTTPException(422, detail={"code": "execution_path_invalid"})
    return directory


def read_receipt(directory: Path) -> dict:
    path = directory / "receipt.json"
    if not path.is_file():
        raise HTTPException(404, detail={"code": "execution_not_found"})
    receipt = json.loads(path.read_text(encoding="utf-8"))
    progress = directory / "progress.json"
    if receipt["status"] == "running" and progress.is_file():
        receipt.update(json.loads(progress.read_text(encoding="utf-8")))
    return receipt


def finish(directory: Path, status: str, **result):
    with _lock:
        receipt = read_receipt(directory)
        if (directory / "cancel").exists():
            status, result = "cancelled", {}
        if status != "succeeded":
            (directory / "artifact.mp4").unlink(missing_ok=True)
        atomic_json(
            directory / "receipt.json",
            {
                **receipt,
                **result,
                "status": status,
                "progress": 100
                if status == "succeeded"
                else receipt.get("progress", 0),
            },
        )


def execute(directory: Path):
    with _lock:
        if (directory / "cancel").exists():
            finish(directory, "cancelled")
            return
        receipt = read_receipt(directory)
        atomic_json(
            directory / "receipt.json", {**receipt, "status": "running", "progress": 1}
        )
    try:
        model_root, source_root = (
            Path(os.environ["LONGCAT_MODEL_ROOT"]),
            Path(os.environ["LONGCAT_SOURCE_ROOT"]),
        )
        if not evaluate(model_root)["usableNow"]:
            raise ValueError("longcat_runtime_unavailable")
        finish(directory, "succeeded", **run(directory, source_root, model_root))
    except InterruptedError:
        finish(directory, "cancelled")
    except Exception as error:
        # Model stderr, prompts, paths and tokens stay out of public receipts.
        finish(directory, "failed", errorCode=type(error).__name__)


def recover_interrupted():
    if not run_root().is_dir():
        return
    for candidate in run_root().iterdir():
        if (
            candidate.is_symlink()
            or not candidate.is_dir()
            or not (candidate / "receipt.json").is_file()
        ):
            continue
        with _lock:
            receipt = read_receipt(candidate)
            if receipt["status"] in {"queued", "running", "cancel_requested"}:
                finish(candidate, "failed", errorCode="worker_restarted")


@asynccontextmanager
async def lifespan(_app):
    recover_interrupted()
    yield
    with _lock:
        for execution_id, future in _futures.items():
            if not future.done():
                (run_directory(execution_id) / "cancel").touch()
    _executor.shutdown(wait=True)


app = FastAPI(title="Clicko LongCat avatar worker", version="0.2.0", lifespan=lifespan)


def authorize(authorization: Annotated[str | None, Header()] = None):
    if not TOKEN or not hmac.compare_digest(authorization or "", f"Bearer {TOKEN}"):
        raise HTTPException(401, detail={"code": "worker_authentication_failed"})


@app.get("/api/v1/capabilities")
def capabilities(authorization: Annotated[str | None, Header()] = None) -> dict:
    authorize(authorization)
    return evaluate(
        Path(os.environ["LONGCAT_MODEL_ROOT"])
        if os.getenv("LONGCAT_MODEL_ROOT")
        else None
    )


def write_verified(
    upload: UploadFile, destination: Path, expected_sha256: str, limit: int
):
    digest, size = hashlib.sha256(), 0
    with destination.open("xb") as stream:
        while chunk := upload.file.read(1024 * 1024):
            size += len(chunk)
            if size > limit:
                raise HTTPException(413, detail={"code": "input_too_large"})
            digest.update(chunk)
            stream.write(chunk)
    if not size or digest.hexdigest() != expected_sha256:
        raise HTTPException(422, detail={"code": "input_checksum_mismatch"})


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
        raise HTTPException(422, detail={"code": "request_invalid"}) from error
    with _lock:
        directory = run_directory(request.execution_id)
        if (directory / "receipt.json").is_file():
            receipt = read_receipt(directory)
            if receipt["requestDigestSha256"] != request.request_digest_sha256:
                raise HTTPException(409, detail={"code": "execution_id_conflict"})
            return receipt
        preflight = capabilities(authorization)
        if not preflight["usableNow"]:
            raise HTTPException(
                409,
                detail={
                    "status": "blocked_resources",
                    "reasons": preflight["reasons"],
                    "executionId": request.execution_id,
                    "requestDigestSha256": request.request_digest_sha256,
                },
            )
        if not os.getenv("LONGCAT_MODEL_ROOT") or not os.getenv("LONGCAT_SOURCE_ROOT"):
            raise HTTPException(409, detail={"code": "longcat_runtime_paths_required"})
        for execution_id, future in list(_futures.items()):
            if future.done():
                del _futures[execution_id]
        if len(_futures) >= 4:
            raise HTTPException(429, detail={"code": "worker_queue_full"})
        directory.parent.mkdir(parents=True, exist_ok=True)
        try:
            directory.mkdir()
        except FileExistsError as error:
            raise HTTPException(
                409, detail={"code": "execution_initialization_incomplete"}
            ) from error
        try:
            write_verified(
                reference_image,
                directory / "reference-image",
                request.reference_image_checksum_sha256,
                20 * 1024**2,
            )
            write_verified(
                driving_audio,
                directory / "driving-audio",
                request.driving_audio_checksum_sha256,
                200 * 1024**2,
            )
            atomic_json(directory / "request.json", request.model_dump(mode="json"))
            receipt = {
                "schemaVersion": "studio.longcat-execution-receipt.v1",
                "executionId": request.execution_id,
                "profileId": request.profile_id,
                "status": "queued",
                "progress": 0,
                "requestDigestSha256": request.request_digest_sha256,
                "segmentCount": request.segment_count,
                "producedFrames": request.produced_frames,
                "trimTailMs": request.trim_tail_ms,
            }
            atomic_json(directory / "receipt.json", receipt)
            _futures[request.execution_id] = _executor.submit(execute, directory)
            return receipt
        except Exception:
            for name in (
                "reference-image",
                "driving-audio",
                "request.json",
                "receipt.json",
                "request.tmp",
                "receipt.tmp",
            ):
                (directory / name).unlink(missing_ok=True)
            directory.rmdir()
            raise


@app.get("/api/v1/executions/{execution_id}")
def get_execution(
    execution_id: str, authorization: Annotated[str | None, Header()] = None
) -> dict:
    authorize(authorization)
    with _lock:
        return read_receipt(run_directory(execution_id))


@app.post("/api/v1/executions/{execution_id}/cancel")
def cancel_execution(
    execution_id: str, authorization: Annotated[str | None, Header()] = None
) -> dict:
    authorize(authorization)
    with _lock:
        directory = run_directory(execution_id)
        receipt = read_receipt(directory)
        if receipt["status"] in {"queued", "running", "cancel_requested"}:
            (directory / "cancel").touch()
            receipt["status"] = "cancel_requested"
            atomic_json(directory / "receipt.json", receipt)
        return receipt


@app.get("/api/v1/executions/{execution_id}/artifact")
def artifact(execution_id: str, authorization: Annotated[str | None, Header()] = None):
    authorize(authorization)
    with _lock:
        directory = run_directory(execution_id)
        receipt = read_receipt(directory)
        path = directory / "artifact.mp4"
        if receipt["status"] != "succeeded" or not path.is_file() or path.is_symlink():
            raise HTTPException(409, detail={"code": "artifact_not_ready"})
        if sha256_file(path) != receipt["artifactChecksumSha256"]:
            raise HTTPException(409, detail={"code": "artifact_checksum_mismatch"})
        return FileResponse(
            path, media_type="video/mp4", headers={"Cache-Control": "private, no-store"}
        )
