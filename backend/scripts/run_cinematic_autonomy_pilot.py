"""Run two bounded, autonomous Studio pilots against an isolated local database.

Only the editorial brief and identity are supplied here. The res plans shots,
discovers/acquires materials, compiles, renders and evaluates. No scene or asset
selection is authored by this runner.
"""

import argparse
import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "output" / "cinematic-autonomy-2026-09-16"
EVIDENCE.mkdir(parents=True, exist_ok=True)
os.environ["DATABASE_URL"] = "sqlite:///" + (EVIDENCE / "pilot.db").as_posix()
os.environ["ENVIRONMENT"] = "development"
os.environ["GEMINI_OUTBOUND_ENABLED"] = "true"
os.environ["STUDIO_GEMINI_ENABLED"] = "true"
PILOT_LIMIT_USD = float(os.environ.get("PILOT_LIMIT_USD", "2.00"))
if not 0 < PILOT_LIMIT_USD <= 2.00:
    raise SystemExit("pilot_limit_out_of_range")
PILOT_DIRECTOR = os.environ.get("PILOT_DIRECTOR", "gemini")
if PILOT_DIRECTOR not in {"gemini", "compatible"}:
    raise SystemExit("pilot_director_invalid")
os.environ["STUDIO_EDITING_AI_PROVIDER"] = PILOT_DIRECTOR
os.environ["STUDIO_EDITING_AI_PLANNING_PROVIDER"] = PILOT_DIRECTOR
os.environ["STUDIO_GEMINI_TEST_BUDGET_USD"] = str(PILOT_LIMIT_USD)
os.environ["STUDIO_PRODUCTION_TEST_BUDGET_USD"] = str(PILOT_LIMIT_USD)
os.environ["STUDIO_EDITING_AI_TEST_BUDGET_USD"] = str(PILOT_LIMIT_USD)
if PILOT_DIRECTOR == "compatible":
    if os.environ.get("PILOT_GPT_MODEL"):
        os.environ["STUDIO_EDITING_AI_MODEL"] = os.environ["PILOT_GPT_MODEL"]
    os.environ["STUDIO_EDITING_AI_INPUT_USD_PER_MILLION"] = os.environ.get(
        "PILOT_GPT_INPUT_USD_PER_MILLION", "2.00"
    )
    os.environ["STUDIO_EDITING_AI_OUTPUT_USD_PER_MILLION"] = os.environ.get(
        "PILOT_GPT_OUTPUT_USD_PER_MILLION", "8.00"
    )
    os.environ["STUDIO_EDITING_AI_MINIMUM_RESERVATION_USD"] = os.environ.get(
        "PILOT_GPT_MINIMUM_RESERVATION_USD", "0.10"
    )
if os.environ.get("PILOT_GEMINI_MODEL"):
    os.environ["STUDIO_GEMINI_PLANNING_MODEL"] = os.environ["PILOT_GEMINI_MODEL"]
os.environ["STUDIO_GEMINI_INPUT_USD_PER_MILLION"] = "0.75"
os.environ["STUDIO_GEMINI_OUTPUT_USD_PER_MILLION"] = "3.75"
os.environ["STUDIO_EDITING_AI_MAX_OUTPUT_TOKENS"] = os.environ.get(
    "PILOT_MAX_OUTPUT_TOKENS", "10000"
)
os.environ.setdefault("STUDIO_LOCAL_VLM_INSPECTION_ENABLED", "true")
os.environ.setdefault(
    "STUDIO_LOCAL_VLM_PYTHON_PATH",
    str(ROOT / "workers" / "media-generation-local" / ".venv" / "Scripts" / "python.exe"),
)

from app.config import get_settings  # noqa: E402

initial = get_settings()
if PILOT_DIRECTOR == "compatible" and not initial.studio_editing_ai_test_key:
    raise SystemExit("Compatible local test credential unavailable")
if PILOT_DIRECTOR == "gemini" and not initial.studio_gemini_test_key:
    available = initial.gemini_api_key_1 or initial.gemini_api_key_2
    if not available:
        raise SystemExit("Gemini test credential unavailable")
    os.environ["STUDIO_GEMINI_TEST_KEY"] = available.get_secret_value()
    get_settings.cache_clear()

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import CreativeDocument, StudioGenerationJob, User  # noqa: E402
from app.services.studios.editorial_production import advance_run  # noqa: E402
from app.services.studios.jobs import execute_job_once  # noqa: E402
from app.tasks import execute_studio_generation  # noqa: E402

execute_studio_generation.delay = lambda _job_id: None
Base.metadata.create_all(bind=engine)

PILOTS = [
    {
        "slug": "distribution",
        "title": "Distribuição — estudo cinematográfico",
        "objective": (
            "Explicar visualmente como distribuição conecta uma ideia às pessoas, mostrando "
            "adaptação de formato e caminho. Preservar a ressalva de que alcance não garante atenção."
        ),
        "script": (
            "Uma ideia só encontra pessoas quando circula. Distribuir é adaptar a mensagem a cada formato "
            "e colocá-la nos caminhos do público. Isso amplia o alcance, mas não garante atenção."
        ),
        "identity": "Editorial claro, contraste nítido, tipografia concisa, filmagem humana e gráficos discretos.",
        "background": "#101c29",
    },
    {
        "slug": "tasks",
        "title": "Organização de tarefas — estudo cinematográfico",
        "objective": (
            "Demonstrar como pedidos dispersos viram uma sequência de trabalho visível, "
            "sem prometer que uma ferramenta substitui decisões humanas."
        ),
        "script": (
            "Organizar tarefas transforma pedidos dispersos em uma sequência visível. Cada tarefa ganha "
            "prioridade, responsável e próximo passo. O quadro ajuda a coordenar o trabalho, mas não "
            "substitui a decisão da equipe."
        ),
        "identity": "Editorial acolhedor, cores quentes, interface legível, filmagem contextual e movimento calmo.",
        "background": "#261d19",
    },
]


def save_snapshot(slug, state, executed):
    values = {
        "recordedAt": datetime.now(UTC).isoformat(),
        "pilot": slug,
        "run": state,
        "executedJobs": executed,
        "manualSceneOrAssetSelection": False,
        "apiLimitUsd": PILOT_LIMIT_USD,
        "director": PILOT_DIRECTOR,
    }
    (EVIDENCE / f"{slug}.json").write_text(
        json.dumps(values, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def run(client, spec):
    email = f"studio-cinematic-{spec['slug']}-{uuid4().hex[:10]}@example.com"
    registered = client.post(
        "/api/v1/auth/register",
        json={
            "email": email, "name": "Studio Pilot", "password": uuid4().hex + "-Pilot",
            "workspaceName": spec["title"],
        },
    )
    if registered.status_code != 201:
        raise ValueError("pilot_registration_failed:" + registered.text[:1000])
    token = registered.json()["accessToken"]
    headers = {"Authorization": f"Bearer {token}"}
    workspace = client.get("/api/v1/bootstrap", headers=headers).json()["workspaces"][0]["id"]
    document = client.post(
        "/api/v1/studios/v1/documents",
        headers=headers,
        json={
            "workspaceId": workspace,
            "title": spec["title"],
            "contentType": "video",
            "brandRevision": 1,
            "brief": {
                "objective": spec["objective"],
                "audience": "Criadores e equipes pequenas",
                "angle": spec["identity"],
                "hook": spec["script"].split(".")[0] + ".",
                "cta": "Compreender a explicação",
            },
            "composition": {
                "pages": [{"id": "page-1", "role": "hook", "width": 720, "height": 1280,
                           "safeArea": 38, "background": spec["background"], "layers": []}],
            },
            "assets": [],
        },
    )
    document.raise_for_status()
    document_id = document.json()["documentId"]
    url = f"/api/v1/studios/v1/documents/{document_id}/production-runs"
    headers["Idempotency-Key"] = "cinematic-" + spec["slug"] + "-" + uuid4().hex
    created = client.post(
        url,
        headers=headers,
        json={
            "direction": {"expectedDocumentRevision": document.json()["revision"],
                          "intent": {"objective": spec["objective"], "script": spec["script"],
                                     "lockedFacts": [spec["script"].split(".")[-2].strip() + "."],
                                     "pacing": "balanced", "emphasis": "demonstration"}},
            "durationSeconds": 18,
            "mode": "mixed_montage",
            "evaluationScope": "visual_only",
            "requireVisualBlueprint": True,
            "useSemanticCompositions": True,
            "demonstrationPolicy": "required",
            "materialSemanticsPolicy": "contextual_video_v1",
            "cinematicDirectionPolicy": "mixed_motion_v1",
        },
    )
    created.raise_for_status()
    state = created.json()
    executed = []
    for step in range(60):
        if state["status"] in {"blocked", "awaiting_review", "cancelled"}:
            break
        with SessionLocal() as db:
            jobs = db.scalars(select(StudioGenerationJob).where(
                StudioGenerationJob.document_id == document_id,
                StudioGenerationJob.status.in_(["queued", "retrying", "running"]),
            )).all()
            actionable = [job for job in jobs if job.status == "queued" or (
                job.status == "retrying"
                and (
                    (job.result_payload or {}).get("submissionOutcome") == "rejected"
                    or (job.result_payload or {}).get("localReplayPending") is True
                )
            )]
            uncertain = [job for job in jobs if job not in actionable]
            if uncertain:
                save_snapshot(spec["slug"], state, executed)
                print(json.dumps({"pilot": spec["slug"], "submissionUncertain": [j.id for j in uncertain]}), flush=True)
                return state
            for job in actionable:
                if job.status == "retrying":
                    time.sleep(8)
                if (job.result_payload or {}).get("localReplayPending") is True:
                    job.result_payload = {**job.result_payload, "localReplayPending": False}
                    db.commit()
                outcome = execute_job_once(db, job)
                executed.append({"jobId": job.id, "kind": job.job_type, "provider": job.provider,
                                 "outcome": outcome, "error": job.error_code})
        response = client.post(url + "/" + state["id"] + "/resume", headers=headers)
        response.raise_for_status()
        state = response.json()
        print(json.dumps({"pilot": spec["slug"], "step": step, "stage": state["stage"],
                          "status": state["status"], "blockers": state.get("blockers", []),
                          "jobs": executed[-len(actionable):] if actionable else []}, ensure_ascii=False), flush=True)
        save_snapshot(spec["slug"], state, executed)
        if not actionable and state["status"] in {"running", "blocked"}:
            break
    save_snapshot(spec["slug"], state, executed)
    return state


def resume_existing(slug):
    snapshot = json.loads((EVIDENCE / f"{slug}.json").read_text(encoding="utf-8"))
    state = snapshot["run"]
    executed = snapshot["executedJobs"]
    for step in range(20):
        recoverable_review = (
            state["status"] == "awaiting_review"
            and state.get("blockers") == ["production_visual_correction_limit_reached"]
            and state.get("stage") in {"animatic", "render"}
        )
        repairable_block = (
            state["status"] == "blocked"
            and (
                state.get("blockers")
                in (
                ["production_provider_job_failed"],
                ["background_removal_image_required"],
                ["production_material_inspection_budget_exceeded"],
                ["production_material_inspection_failed"],
                ["production_material_source_or_evidence_required"],
                ["production_material_choice_required"],
                ["production_technique_suitability_failed"],
                ["production_material_inspection_call_limit_reached"],
                # A pre-fix local material-response replay attempted the
                # invalid retrying -> queued transition.  The provider response
                # is already stored and can now be replayed without network IO.
                ["invalid_job_transition:retrying:queued"],
                )
                or any(
                    "Provider does not support requested job type" in blocker
                    or "editing_v2_shot_component_missing" in blocker
                    or "editing_component_action_out_of_interval" in blocker
                    for blocker in state.get("blockers", [])
                )
            )
        )
        if (state["status"] == "awaiting_review" and not recoverable_review) or state[
            "status"
        ] == "cancelled" or (
            state["status"] == "blocked" and not repairable_block
        ):
            break
        with SessionLocal() as db:
            record = db.get(CreativeDocument, state["documentId"])
            if not record:
                raise ValueError("pilot_document_missing")
            user = db.get(User, record.created_by)
            jobs = db.scalars(select(StudioGenerationJob).where(
                StudioGenerationJob.document_id == record.id,
                StudioGenerationJob.status.in_(["queued", "retrying", "running"]),
            )).all()
            # A material repair can replace a need while leaving its unpaid,
            # queued inspection in the job ledger.  Only execute jobs that the
            # current immutable run state still references; historical jobs are
            # evidence, not work awaiting dispatch.
            active_job_ids = {
                str(job_id)
                for job_id in state.get("jobs", {}).values()
                if job_id
            }
            for material_work in state.get("materialWork", {}).values():
                active_job_ids.update(
                    str(job_id)
                    for job_id in (
                        material_work.get("jobId"),
                        material_work.get("generationJobId"),
                    )
                    if job_id
                )
            jobs = [job for job in jobs if job.id in active_job_ids]
            actionable = []
            for job in jobs:
                receipt = job.result_payload or {}
                if job.status == "queued" or (
                    job.status == "retrying" and (
                        receipt.get("submissionOutcome") == "rejected"
                        or not receipt.get("submissionStarted")
                        or receipt.get("localReplayPending") is True
                    )
                ):
                    actionable.append(job)
                elif (
                    job.status == "retrying"
                    and receipt.get("submissionOutcome") == "accepted"
                    and receipt.get("responseKey")
                ):
                    # A complete provider response is durably stored. Let the
                    # production state machine classify or correct it locally;
                    # never resubmit the same paid request.
                    continue
                elif job.status in {"retrying", "running"}:
                    state["status"] = "blocked"
                    state["blockers"] = ["pilot_submission_outcome_uncertain:" + job.id]
                    save_snapshot(slug, state, executed)
                    return state
            for job in actionable:
                if job.status == "retrying":
                    time.sleep(8)
                if (job.result_payload or {}).get("localReplayPending") is True:
                    job.result_payload = {**job.result_payload, "localReplayPending": False}
                    db.commit()
                outcome = execute_job_once(db, job)
                executed.append({"jobId": job.id, "kind": job.job_type, "provider": job.provider,
                                 "outcome": outcome, "error": job.error_code})
            state = advance_run(db, record, state["id"], user)
        save_snapshot(slug, state, executed)
        print(json.dumps({"pilot": slug, "step": step, "stage": state["stage"],
                          "status": state["status"], "blockers": state.get("blockers", []),
                          "job": executed[-1] if actionable else None}, ensure_ascii=False), flush=True)
        if not actionable and state["status"] in {"running", "blocked"}:
            break
    return state


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume", help="Existing pilot snapshot slug")
    parser.add_argument("--suffix", default="", help="Unique suffix for a new, isolated pilot")
    parser.add_argument("--pilot", choices=[pilot["slug"] for pilot in PILOTS], help="Run only one pilot")
    args = parser.parse_args()
    if args.resume:
        result = resume_existing(args.resume)
        print(json.dumps({"pilot": args.resume, "finalStatus": result["status"],
                          "video": bool(result.get("artifacts", {}).get("video"))}, ensure_ascii=False), flush=True)
    else:
        with TestClient(app) as client:
            for pilot in PILOTS:
                if args.pilot and pilot["slug"] != args.pilot:
                    continue
                spec = {**pilot, "slug": pilot["slug"] + args.suffix}
                result = run(client, spec)
                print(json.dumps({
                    "pilot": spec["slug"],
                    "finalStatus": result["status"],
                    "video": bool(result.get("artifacts", {}).get("video")),
                }, ensure_ascii=False), flush=True)
                if not result.get("artifacts", {}).get("video"):
                    break
