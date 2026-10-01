"""Execute sampled material inspection in the isolated local VLM runtime."""

from __future__ import annotations

import json
import subprocess
import tempfile
from contextlib import ExitStack
from pathlib import Path

from ...config import get_settings
from ...domain.studios.editing_resources import EditingAIRequestV1
from ...domain.studios.material_inspection import MaterialInspectionResultV1, inspect_verdict
from .gemini_editing import validate_binding
from .material_inspection import bound_asset, prepare_samples

PROVIDER = "local.smolvlm-material-inspection"
MODEL = "HuggingFaceTB/SmolVLM-500M-Instruct"
REVISION = "a7da5b986cb59b408707209984f360a5f4ad7e47"
PRICE_VERSION = "local-no-api-spend-2026-09-20"


def binding(settings=None) -> tuple[str, str, str]:
    settings = settings or get_settings()
    if not settings.studio_local_vlm_inspection_enabled:
        raise ValueError("local_vlm_inspection_disabled")
    python = Path(str(settings.studio_local_vlm_python_path or ""))
    if not python.is_file():
        raise ValueError("local_vlm_python_unavailable")
    worker = Path(__file__).resolve().parents[4] / "workers" / "media-generation-local" / "local_material_inspector.py"
    if not worker.is_file():
        raise ValueError("local_vlm_worker_unavailable")
    return str(python.resolve()), str(worker.resolve()), f"{MODEL}@{REVISION}"


def execute_local_material_inspection(db, job, progress, is_cancelled):
    settings = get_settings()
    python, worker, model = binding(settings)
    record, _contract = validate_binding(db, job)
    request = EditingAIRequestV1.model_validate(job.request_payload["input"])
    if request.operation != "plan" or request.material_inspection is None:
        raise ValueError("local_vlm_material_inspection_only")
    with ExitStack() as stack:
        directory = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix="res-local-vlm-")))
        media, samples, duration = prepare_samples(
            db,
            job.workspace_id,
            request.material_inspection,
            stack,
            directory,
            settings,
            is_cancelled,
        )
        progress(30)
        if is_cancelled():
            raise InterruptedError("local_vlm_inspection_cancelled")
        payload = directory / "inspection.json"
        payload.write_text(
            json.dumps(
                {
                    "samplePaths": [str(path) for path, _media_type in media],
                    "criteria": request.material_inspection.criteria,
                    "evidenceKind": request.material_inspection.evidence_kind,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        completed = subprocess.run(
            [python, worker, str(payload)],
            cwd=str(Path(worker).parent),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=min(settings.ffmpeg_timeout_seconds, 900),
            check=False,
        )
        if completed.returncode != 0:
            raise ValueError("local_vlm_inspection_failed")
        try:
            raw = json.loads(completed.stdout.strip().splitlines()[-1])
            result = MaterialInspectionResultV1.model_validate(
                {
                    key: raw[key]
                    for key in (
                        "description",
                        "criteria",
                        "confidence",
                        "confidenceKind",
                        "evidenceKind",
                        "processingRequirements",
                        "uncertainty",
                    )
                }
            )
        except (IndexError, json.JSONDecodeError, ValueError) as error:
            raise ValueError("local_vlm_inspection_output_invalid") from error
        status = inspect_verdict(
            result,
            request.material_inspection,
            samples,
            duration,
        )
        bound_asset(db, job.workspace_id, request.material_inspection)
        progress(90)
        return {
            "providerSubmission": False,
            "measuredCostUsd": 0,
            "materialInspection": {
                "status": status,
                "assetId": request.material_inspection.asset_id,
                "checksum": request.material_inspection.checksum,
                "request": request.material_inspection.model_dump(mode="json", by_alias=True),
                "samplingCoverage": {
                    "sourceStartSeconds": request.material_inspection.source_start_seconds,
                    "requiredSeconds": request.material_inspection.required_seconds,
                    "sampledSeconds": [item.get("seconds") for item in samples if "seconds" in item],
                    "continuousObservation": False,
                    "evidenceKind": request.material_inspection.evidence_kind,
                },
                "result": result.model_dump(mode="json", by_alias=True),
                "samples": samples,
                "coverage": "sampled",
                "humanReview": "pending",
                "jobId": job.id,
                "model": model,
                "runtime": {
                    "provider": PROVIDER,
                    "priceVersion": PRICE_VERSION,
                    "stderrTail": completed.stderr[-1000:],
                },
            },
            "documentRevision": record.revision,
        }
