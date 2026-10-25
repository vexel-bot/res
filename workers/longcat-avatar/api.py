from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import shutil
import stat
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from preflight import ROOT, evaluate, sha256_file
from protocol import AvatarExecutionRequest
from runner import atomic_json, run

TOKEN = os.getenv("LONGCAT_WORKER_TOKEN")
_lock = threading.RLock()
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="longcat")
_futures = {}
TERMINAL = {"succeeded", "failed", "cancelled"}


def retention_seconds(name: str, default: int, maximum: int) -> int:
    value = int(os.getenv(name, default))
    if not 1 <= value <= maximum:
        raise ValueError("longcat_retention_invalid")
    return value


def retention_policy():
    return {
        "artifactTtlSeconds": retention_seconds(
            "LONGCAT_ARTIFACT_TTL_SECONDS", 3600, 86400
        ),
        "executionTtlSeconds": retention_seconds(
            "LONGCAT_EXECUTION_TTL_SECONDS", 10800, 86400
        ),
        "tombstoneTtlSeconds": retention_seconds(
            "LONGCAT_TOMBSTONE_TTL_SECONDS", 86400, 604800
        ),
        "sweepIntervalSeconds": retention_seconds(
            "LONGCAT_SWEEP_INTERVAL_SECONDS", 60, 60
        ),
    }


def run_root() -> Path:
    return Path(os.getenv("LONGCAT_RUN_ROOT", ROOT / ".runs")).resolve()


def run_directory(execution_id: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{7,159}", execution_id):
        raise HTTPException(422, detail={"code": "execution_path_invalid"})
    root = run_root()
    candidate = root / execution_id
    directory = candidate.resolve()
    if directory.parent != root or candidate.is_symlink():
        raise HTTPException(422, detail={"code": "execution_path_invalid"})
    return directory


def read_receipt(directory: Path) -> dict:
    path = directory / "receipt.json"
    if not path.is_file() or path.is_symlink():
        raise HTTPException(404, detail={"code": "execution_not_found"})
    receipt = json.loads(path.read_text(encoding="utf-8"))
    progress = directory / "progress.json"
    if (
        receipt["status"] == "running"
        and progress.is_file()
        and not progress.is_symlink()
    ):
        receipt.update(json.loads(progress.read_text(encoding="utf-8")))
    return receipt


def cleanup_files(directory: Path, *, keep_artifact: bool):
    # Validate every absolute target before recursive removal. Never follow a
    # symlink or Windows reparse point into model/source directories or another job.
    if run_directory(directory.name) != directory.resolve():
        raise ValueError("execution_path_invalid")
    for entry in directory.iterdir():
        if entry.name in {"receipt.json", ".initializing"} or (
            keep_artifact and entry.name == "artifact.mp4"
        ):
            continue
        info = entry.lstat()
        reparse = bool(
            getattr(info, "st_file_attributes", 0)
            & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        )
        if entry.is_symlink() or reparse:
            if stat.S_ISDIR(info.st_mode) and not entry.is_symlink():
                entry.rmdir()  # Remove the junction, never its target.
            else:
                entry.unlink()
        elif entry.resolve().parent != directory.resolve():
            raise ValueError("execution_path_invalid")
        elif entry.is_dir():
            shutil.rmtree(entry)
        else:
            entry.unlink()
    (directory / ".initializing").unlink(missing_ok=True)


def purge(directory: Path, receipt: dict, reason: str = "requested") -> dict:
    pending = {**receipt, "status": "deletion_requested", "deletionRequested": True}
    atomic_json(directory / "receipt.json", pending)
    try:
        cleanup_files(directory, keep_artifact=False)
    except OSError:
        # A locked artifact is retried by the sweeper; it must not remain served.
        return pending
    tombstone = {
        key: receipt[key]
        for key in ("schemaVersion", "executionId", "profileId", "requestDigestSha256")
        if key in receipt
    }
    tombstone.update(status="deleted", deletedAtUnix=time.time(), deletionReason=reason)
    atomic_json(directory / "receipt.json", tombstone)
    return tombstone


def sweep_retention():
    policy = retention_policy()
    if not run_root().is_dir():
        return
    now = time.time()
    artifact_ttl, execution_ttl, tombstone_ttl = (
        policy[key]
        for key in ("artifactTtlSeconds", "executionTtlSeconds", "tombstoneTtlSeconds")
    )
    for candidate in run_root().iterdir():
        if candidate.is_symlink() or not candidate.is_dir():
            continue
        try:
            with _lock:
                directory = run_directory(candidate.name)
                if not (directory / "receipt.json").is_file():
                    if (directory / ".initializing").is_file():
                        future = _futures.get(candidate.name)
                        if not future or future.done():
                            cleanup_files(directory, keep_artifact=False)
                            directory.rmdir()
                        else:
                            (directory / "cancel").touch()
                    continue
                sweep_directory(
                    directory, now, artifact_ttl, execution_ttl, tombstone_ttl
                )
        except (OSError, ValueError, KeyError, HTTPException):
            continue


def sweep_directory(
    directory: Path,
    now: float,
    artifact_ttl: int,
    execution_ttl: int,
    tombstone_ttl: int,
):
    try:
        receipt = read_receipt(directory)
        status = receipt["status"]
    except (ValueError, KeyError):
        future = _futures.get(directory.name)
        if future and not future.done():
            (directory / "delete_requested").touch()
            (directory / "cancel").touch()
            return
        purge(directory, {"executionId": directory.name}, "receipt_invalid")
        return
    age = now - receipt.get(
        "finishedAtUnix",
        receipt.get("createdAtUnix", (directory / "receipt.json").stat().st_mtime),
    )
    if status == "deleted":
        if now - receipt["deletedAtUnix"] >= tombstone_ttl:
            cleanup_files(directory, keep_artifact=False)
            (directory / "receipt.json").unlink()
            directory.rmdir()
    elif status == "deletion_requested":
        purge(directory, receipt)
    elif status in TERMINAL:
        if receipt.get("deletionRequested") or age >= artifact_ttl:
            purge(
                directory,
                receipt,
                "requested" if receipt.get("deletionRequested") else "expired",
            )
        else:
            cleanup_files(directory, keep_artifact=status == "succeeded")
    else:
        future = _futures.get(directory.name)
        if not future or future.done():
            purge(directory, receipt, "execution_missing")
        elif age >= execution_ttl:
            (directory / "delete_requested").touch()
            (directory / "cancel").touch()
            atomic_json(
                directory / "receipt.json",
                {**receipt, "status": "cancel_requested", "deletionRequested": True},
            )


def finish(directory: Path, status: str, **result):
    with _lock:
        receipt = read_receipt(directory)
        if (directory / "cancel").exists():
            status, result = "cancelled", {}
        receipt = {
            **receipt,
            **result,
            "status": status,
            "progress": 100 if status == "succeeded" else receipt.get("progress", 0),
            "finishedAtUnix": time.time(),
        }
        if (
            receipt.get("deletionRequested")
            or (directory / "delete_requested").exists()
        ):
            return purge(directory, receipt)
        atomic_json(directory / "receipt.json", receipt)
        try:
            cleanup_files(directory, keep_artifact=status == "succeeded")
        except OSError:
            pass  # Retention sweeper retries locked files.


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
            try:
                directory = run_directory(candidate.name)
                receipt = read_receipt(directory)
            except (ValueError, KeyError):
                purge(candidate, {"executionId": candidate.name}, "receipt_invalid")
                continue
            except HTTPException:
                continue
            if receipt["status"] in {"queued", "running", "cancel_requested"}:
                finish(directory, "failed", errorCode="worker_restarted")


@asynccontextmanager
async def lifespan(_app):
    recover_interrupted()
    sweep_retention()
    stop = threading.Event()
    interval = retention_seconds("LONGCAT_SWEEP_INTERVAL_SECONDS", 60, 60)

    def sweep():
        while not stop.wait(interval):
            try:
                sweep_retention()
            except (OSError, ValueError, HTTPException):
                continue  # A bad job must not disable cleanup for the next pass.

    janitor = threading.Thread(target=sweep, name="longcat-retention", daemon=True)
    janitor.start()
    try:
        yield
    finally:
        stop.set()
        janitor.join(timeout=2)
        with _lock:
            for execution_id, future in _futures.items():
                if not future.done():
                    (run_directory(execution_id) / "cancel").touch()
        _executor.shutdown(wait=True)
        sweep_retention()


app = FastAPI(title="Clicko LongCat avatar worker", version="0.3.0", lifespan=lifespan)


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


@app.get("/api/v1/lifecycle")
def lifecycle(authorization: Annotated[str | None, Header()] = None):
    authorize(authorization)
    return {
        "schemaVersion": "studio.longcat-lifecycle.v1",
        "workerApiVersion": "0.3.0",
        "authenticatedDeletion": True,
        "removeInputsAfterExecution": True,
        "retention": retention_policy(),
    }


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
            if receipt.get("requestDigestSha256") != request.request_digest_sha256:
                raise HTTPException(409, detail={"code": "execution_id_conflict"})
            if receipt["status"] in {"deleted", "deletion_requested"}:
                raise HTTPException(410, detail={"code": "execution_deleted"})
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
            (directory / ".initializing").touch()
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
                "createdAtUnix": time.time(),
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
                ".initializing",
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
        if receipt["status"] == "succeeded" and time.time() - receipt.get(
            "finishedAtUnix", (directory / "receipt.json").stat().st_mtime
        ) >= retention_seconds("LONGCAT_ARTIFACT_TTL_SECONDS", 3600, 86400):
            purge(directory, receipt, "expired")
            raise HTTPException(410, detail={"code": "artifact_expired"})
        path = directory / "artifact.mp4"
        if receipt["status"] != "succeeded" or not path.is_file() or path.is_symlink():
            raise HTTPException(409, detail={"code": "artifact_not_ready"})
        if sha256_file(path) != receipt["artifactChecksumSha256"]:
            raise HTTPException(409, detail={"code": "artifact_checksum_mismatch"})
        return FileResponse(
            path, media_type="video/mp4", headers={"Cache-Control": "private, no-store"}
        )


@app.delete("/api/v1/executions/{execution_id}")
def delete_execution(
    execution_id: str, authorization: Annotated[str | None, Header()] = None
):
    authorize(authorization)
    with _lock:
        directory = run_directory(execution_id)
        receipt = read_receipt(directory)
        if receipt["status"] == "deleted":
            return receipt
        if receipt["status"] not in TERMINAL | {"deletion_requested"}:
            (directory / "delete_requested").touch()
            (directory / "cancel").touch()
            receipt.update(status="cancel_requested", deletionRequested=True)
            atomic_json(directory / "receipt.json", receipt)
            future = _futures.get(execution_id)
            if not future or future.done() or future.cancel():
                return purge(directory, receipt)
            return JSONResponse(receipt, status_code=202)
        result = purge(directory, receipt)
        return JSONResponse(
            result, status_code=200 if result["status"] == "deleted" else 202
        )
