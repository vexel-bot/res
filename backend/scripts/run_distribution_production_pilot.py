"""Run the autonomous Distribution pilot through normal res services.

The harness supplies only a brief. It does not create scenes, select materials,
or insert media into the document. Missing provider capability must block the run
instead of degrading a mixed montage into generic procedural graphics.
"""

# Configuration must precede imports that initialize the engine/provider registry.
# ruff: noqa: E402
from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VARIANT = os.environ.get("RES_DISTRIBUTION_PILOT_VARIANT", "repertoire")
if VARIANT not in {"repertoire", "video-api", "editorial-motion"}:
    raise RuntimeError("pilot_variant_invalid")
PLANNER = os.environ.get("RES_DISTRIBUTION_PILOT_PLANNER", "compatible")
if PLANNER not in {"compatible", "gemini"}:
    raise RuntimeError("pilot_planner_invalid")
REVISION = os.environ.get("RES_DISTRIBUTION_PILOT_REVISION", "v5-demonstrable-materials")
if not REVISION.replace("-", "").replace("_", "").isalnum():
    raise RuntimeError("pilot_revision_invalid")
OUT = ROOT / "artifacts/validation/distribution-production-live" / ("director-" + VARIANT + "-" + REVISION)
OUT.mkdir(parents=True, exist_ok=True)
os.chdir(ROOT)

from app.config import get_settings

s = get_settings()
if s.environment == "production":
    raise RuntimeError("local_test_only")
s.environment = "test"
s.database_url = "sqlite:///" + (OUT / "pilot.sqlite").as_posix()
s.storage_path = str(OUT / "storage")
s.object_storage_backend = "local"
s.studio_editing_ai_planning_provider = PLANNER
s.studio_editing_ai_base_url = "https://api.openai.com/v1" if PLANNER == "compatible" else None
s.studio_editing_ai_model = "gpt-4.1-2025-04-14" if PLANNER == "compatible" else None
s.studio_editing_ai_test_key = s.openai_api_key if PLANNER == "compatible" else None
PILOT_API_LIMIT_USD = float(os.environ.get(
    "RES_DISTRIBUTION_PILOT_API_LIMIT_USD",
    "2" if VARIANT == "editorial-motion" else "1",
))
if not 0 < PILOT_API_LIMIT_USD <= 2:
    raise RuntimeError("pilot_api_limit_invalid")
s.studio_editing_ai_test_budget_usd = PILOT_API_LIMIT_USD
s.studio_gemini_enabled = PLANNER == "gemini"
s.gemini_outbound_enabled = PLANNER == "gemini"
s.studio_gemini_test_key = (s.gemini_api_key_2 or s.gemini_api_key_1) if PLANNER == "gemini" else None
s.studio_gemini_planning_model = os.environ.get("RES_DISTRIBUTION_PILOT_GEMINI_MODEL", "gemini-3.8-flash")
s.studio_gemini_test_budget_usd = PILOT_API_LIMIT_USD
s.studio_gemini_input_usd_per_million = 0.75
s.studio_gemini_output_usd_per_million = 3.75
s.studio_production_test_budget_usd = PILOT_API_LIMIT_USD
s.studio_editing_ai_price_version = "openai-gpt-4.1-standard-2026-09-08"
s.studio_editing_ai_input_usd_per_million = 2
s.studio_editing_ai_output_usd_per_million = 8
s.studio_editing_ai_max_output_tokens = 16384 if VARIANT == "editorial-motion" else 10240
s.studio_editing_ai_max_prompt_chars = 100_000
s.studio_editing_ai_video_provider = "sora" if VARIANT == "video-api" else "none"
s.openai_outbound_enabled = VARIANT == "video-api"
s.openai_video_generation_enabled = VARIANT == "video-api"
s.openai_max_external_spend_usd = 0.40 if VARIANT == "video-api" else 0
s.hyperframes_enabled = True
s.studio_isolated_queues_enabled = False
s.hyperframes_local_qualification_enabled = True
s.celery_task_always_eager = True
s.hyperframes_cli_path = str(ROOT / "node_modules/hyperframes/dist/cli.js")
s.hyperframes_timeout_seconds = 600

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.domain.studios.contracts import CreativeDocumentV1
from app.domain.studios.editorial_production import ProductionRequestV1
from app.main import app
from app.models import CreativeDocument, LibraryAsset, StudioGenerationJob, User
from app.services.object_storage import get_object_storage
from app.services.studios.compatibility import persist_contract
from app.services.studios.editorial_production import advance_run, create_run, get_run
from app.services.studios.jobs import execute_job_once, transition


def write(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def production_request(revision: int) -> ProductionRequestV1:
    editorial = VARIANT == "editorial-motion"
    visual_hint = os.environ.get("RES_DISTRIBUTION_PILOT_VISUAL_HINT", "").strip()
    if visual_hint:
        visual_hint = " Direção adicional desta rodada: " + visual_hint
    return ProductionRequestV1.model_validate(
        {
            "direction": {
                "expectedDocumentRevision": revision,
                "intent": {
                    "objective": (
                        "Criar um motion editorial vertical de 10–12 segundos sobre distribuição. "
                        "Escolha a linguagem visual, os textos e o motivo gráfico. Mostre uma ação "
                        "compreensível com começo, desenvolvimento e conclusão; preserve a ressalva."
                        + visual_hint
                    ) if editorial else (
                        "Explicar visualmente como distribuição conecta uma ideia às pessoas. "
                        "Criar uma peça original, com progressão clara, profundidade, câmera "
                        "e tipografia seletiva. O sistema deve descobrir e selecionar os materiais."
                    ),
                    "format": "educational",
                    "script": (
                        "Uma ideia nasce. Distribuição a leva por caminhos diferentes até o público. "
                        "Ela pode chegar a muitas telas, mas aparecer não garante atenção."
                    ) if editorial else (
                        "Uma boa ideia não chega sozinha às pessoas. Distribuir é adaptar a mensagem "
                        "e escolher os caminhos para encontrar o público. Um vídeo pode virar diferentes "
                        "conteúdos, conectados pela mesma ideia. Mas distribuir não garante atenção."
                    ),
                    "lockedFacts": [
                        "mas aparecer não garante atenção." if editorial
                        else "Mas distribuir não garante atenção."
                    ],
                    "pacing": "balanced",
                    "emphasis": "demonstration",
                    "preserveMessage": True,
                },
            },
            "durationSeconds": 11 if editorial else 18,
            "mode": "motion" if editorial else "mixed_montage",
            "evaluationScope": "visual_only",
            "requireVisualBlueprint": True,
            "demonstrationPolicy": "required",
            "materialSemanticsPolicy": "legacy" if editorial else "contextual_video_v1",
            "cinematicDirectionPolicy": "editorial_motion_v2" if editorial else "disabled",
            "useSemanticCompositions": True,
            "generatedVideoPolicy": "single_short_clip" if VARIANT == "video-api" else "disabled",
        }
    )


def main():
    if PLANNER == "compatible" and not s.studio_editing_ai_test_key:
        raise RuntimeError("local_planning_key_required")
    if PLANNER == "gemini" and not s.studio_gemini_test_key:
        raise RuntimeError("local_gemini_planning_key_required")
    Base.metadata.create_all(engine)
    binding = OUT / "binding.json"
    if not binding.exists():
        client = TestClient(app)
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": f"distribution-autonomous-{VARIANT}-{REVISION}@example.com",
                "name": "Res autonomous pilot",
                "password": "local-pilot-" + os.urandom(20).hex(),
                "workspaceName": f"Distribuição — piloto {VARIANT}",
            },
        )
        response.raise_for_status()
        bootstrap = client.get(
            "/api/v1/bootstrap", headers={"Authorization": "Bearer " + response.json()["accessToken"]}
        )
        bootstrap.raise_for_status()
        workspace = bootstrap.json()["workspaces"][0]["id"]
        with SessionLocal() as db:
            user = db.scalar(
                select(User).where(User.email == f"distribution-autonomous-{VARIANT}-{REVISION}@example.com")
            )
            record = CreativeDocument(
                workspace_id=workspace,
                title=f"Distribuição — teste {VARIANT}",
                document={},
                created_by=user.id,
            )
            db.add(record)
            db.flush()
            document = CreativeDocumentV1(
                document_id=record.id,
                workspace_id=workspace,
                title=record.title,
                content_type="video",
                correlation_id=f"distribution-{VARIANT}-live",
                brand_memory_ref={"id": "neutral-pilot", "revision": 1},
                brief={"objective": "Explicar distribuição", "audience": "Criadores de conteúdo"},
                assets=[],
                composition={"pages": [{"id": "canvas", "width": 720 if VARIANT == "editorial-motion" else 1080,
                                         "height": 1280 if VARIANT == "editorial-motion" else 1080,
                                         "safeArea": 72}]},
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            persist_contract(record, document)
            db.commit()
            request = production_request(record.revision)
            write("brief.json", request.model_dump(mode="json", by_alias=True))
            state = create_run(db, record, request, user, f"distribution-{VARIANT}-{REVISION}-live-v1")
            write("binding.json", {"documentId": record.id, "runId": state["id"]})

    ids = json.loads(binding.read_text(encoding="utf-8"))
    with SessionLocal() as db:
        record = db.get(CreativeDocument, ids["documentId"])
        user = db.get(User, record.created_by)
        # This harness executes jobs eagerly in its own process. A running job
        # left by a previous terminated invocation has no worker to finish it.
        # Keep its reservation and classify an uncertain submission; never
        # submit the same inspection again merely because the process restarted.
        for stale in db.scalars(
            select(StudioGenerationJob).where(
                StudioGenerationJob.document_id == record.id,
                StudioGenerationJob.status == "running",
            )
        ):
            result = stale.result_payload or {}
            if (
                stale.job_type in {"editing_ai", "editing_gemini"}
                and (stale.worker_execution_context or {}).get("mode") == "embedded"
                and result.get("responseKey")
                and not result.get("providerOperationId")
            ):
                # The local harness was interrupted after receiving and
                # persisting a paid response. Reparse that exact response on
                # restart; never submit a second provider request.
                transition(stale, "failed")
                stale.error_message = "editing_ai_local_postprocessing_interrupted"
                continue
            if (
                (stale.worker_execution_context or {}).get("mode") == "embedded"
                and result.get("submissionStarted")
                and result.get("submissionOutcome") == "pending"
                and not result.get("responseKey")
            ):
                transition(stale, "failed")
                stale.error_message = "editing_submission_outcome_unknown_manual_reconciliation_required"
                stale.result_payload = {
                    **result,
                    "submissionOutcome": "unknown_after_local_worker_interruption",
                }
        db.commit()
        for _ in range(24):
            state = advance_run(db, record, ids["runId"], user)
            write("run.json", state)
            print(
                json.dumps(
                    {"stage": state["stage"], "status": state["status"], "blockers": state["blockers"]},
                    ensure_ascii=False,
                ),
                flush=True,
            )
            if state["status"] in {"blocked", "awaiting_review", "cancelled"}:
                break
            job_id = state["jobs"].get(state["stage"])
            if not job_id:
                continue
            job = db.get(StudioGenerationJob, job_id)
            db.refresh(job)
            if job.status == "queued" and not s.celery_task_always_eager:
                status = execute_job_once(db, job)
                print(json.dumps({"job": job.id, "status": status, "error": job.error_message}), flush=True)
            write(
                f"job-{state['stage']}.json",
                {
                    "id": job.id,
                    "status": job.status,
                    "request": job.request_payload,
                    "result": job.result_payload,
                    "error": job.error_message,
                },
            )
        state = get_run(db, record, ids["runId"])
        write("run.json", state)
        write("document.json", record.document)
        plan = state.get("artifacts", {}).get("plan") or {}
        if plan:
            write("plan.json", plan)
            write("direction.json", plan.get("direction"))
            write("motion-graph.json", plan.get("motionGraph"))
            write("manifest.json", plan.get("manifest"))
        write("visual-audit.json", state.get("visualAudit"))
        write("technical-evaluation.json", state.get("technicalEvaluation"))
        write(
            "material-receipts.json",
            {
                "materialWork": state.get("materialWork", {}),
                "materialHistory": state.get("materialHistory", []),
            },
        )
        jobs = list(
            db.scalars(
                select(StudioGenerationJob)
                .where(StudioGenerationJob.workspace_id == record.workspace_id)
                .order_by(StudioGenerationJob.created_at)
            )
        )
        usage_jobs = []
        for job in jobs:
            result = job.result_payload or {}
            usage_jobs.append(
                {
                    "id": job.id,
                    "jobType": job.job_type,
                    "provider": job.provider,
                    "status": job.status,
                    "attempts": job.attempts,
                    "submissionStarted": result.get("submissionStarted", False),
                    "providerOperationId": result.get("providerOperationId"),
                    "model": result.get("model"),
                    "usage": result.get("usage"),
                    "measuredCostUsd": result.get("measuredCostUsd"),
                    "processingSeconds": result.get("processingSeconds"),
                    "renderDurationMs": result.get("renderDurationMs")
                    or (result.get("videoRenderResult") or {}).get("renderDurationMs"),
                    "errorCode": job.error_code,
                }
            )
        measured = sum(float(item["measuredCostUsd"] or 0) for item in usage_jobs)
        write(
            "usage-observed.json",
            {
                "schemaVersion": "studio.pilot-usage-observed.v1",
                "budgetEnvelope": state.get("budgetEnvelope"),
                "measuredCostUsd": round(measured, 6),
                "costCoverage": "provider calls with returned measured cost; local render has no API cost",
                "jobs": usage_jobs,
            },
        )
        video = (
            state.get("artifacts", {}).get("video", {}).get("artifact", {})
            or state.get("artifacts", {}).get("animatic", {}).get("artifact", {})
        )
        if video.get("assetId"):
            import shutil

            asset = db.get(LibraryAsset, video["assetId"])
            with get_object_storage(asset.storage_backend).materialize(asset.storage_key) as path:
                shutil.copyfile(path, OUT / "distribution.mp4")
            print("VIDEO " + str(OUT / "distribution.mp4"), flush=True)


if __name__ == "__main__":
    main()
