"""Compare independent Opus classifications and run one autonomous EffectCraft edit."""
import argparse
import base64
import hashlib
import json
import os
import re
import shutil
import time
import wave
from datetime import UTC, datetime
from pathlib import Path

import numpy as np


MODEL = "claude-opus-5-5"
KEY = "casa-lume-opus-transfer-20261112"
CASE = Path(__file__).resolve().parents[2] / "benchmarks/studios/orbita"
QUESTION = ("Look at the top of the video. Does a straight bright horizontal edge actually cross "
            "the letters of the white top headline, touching the letters rather than sitting below them? "
            "Answer YES, NO, or UNSURE. Judge only the image.")
FRAMES = [
    ("repaired-title", "NO"), ("original-collision", "YES"),
    ("repaired-same-time", "NO"), ("original-clean", "NO"),
]


def write_json(path, value):
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    for attempt in range(8):
        try:
            temp.replace(path)
            return
        except PermissionError:
            if attempt == 7:
                raise
            time.sleep(.25 * (attempt + 1))


def verdict(answer):
    match = re.match(r"^[\s*]*(YES|NO|UNSURE)\b", answer, re.IGNORECASE)
    return match.group(1).upper() if match else None


def measure_detection(provider, evidence, output):
    path = output / "detecao-opus.json"
    result = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"model": MODEL, "frames": {}}
    for name, expected in FRAMES:
        if name in result["frames"]:
            entry = result["frames"][name]
            if entry["status"] == "complete":
                label = verdict(entry["answer"])
                entry.update(verdict=label, correct=label == expected, falsePositive=label == "YES" and expected == "NO")
            continue
        data = (evidence / f"{name}.png").read_bytes()
        image = {"type": "image", "source": {"type": "base64", "media_type": "image/png",
                                            "data": base64.b64encode(data).decode("ascii")}}
        entry = {"sha256": hashlib.sha256(data).hexdigest(), "expected": expected, "status": "submitted"}
        result["frames"][name] = entry
        write_json(path, result)
        start = time.monotonic()
        try:
            turn = provider.craft_turn(MODEL, "You inspect one still frame for video editing.",
                [{"role": "user", "content": [image, {"type": "text", "text": QUESTION}]}], [], 192, 120, effort="low")
        except ValueError as error:
            entry.update(status="error", error=str(error), seconds=round(time.monotonic() - start, 3))
            write_json(path, result)
            raise
        answer = " ".join(block["text"] for block in turn["content"] if block["type"] == "text")
        label = verdict(answer)
        usage = turn["usage"]
        cost = (usage.get("input_tokens", 0) * 4 + usage.get("output_tokens", 0) * 20
                + usage.get("cache_creation_input_tokens", 0) * 5 + usage.get("cache_read_input_tokens", 0) * .2) / 1_000_000
        entry.update(status="complete", answer=answer, verdict=label, correct=label == expected,
                     falsePositive=label == "YES" and expected == "NO", usage=usage, costUsd=round(cost, 8),
                     providerRequestId=turn.get("request_id"), seconds=round(time.monotonic() - start, 3))
        write_json(path, result)
        print(json.dumps({"frame": name, "answer": answer, "expected": expected, "costUsd": cost}), flush=True)
    entries = list(result["frames"].values())
    result.update(correct=sum(x.get("correct", False) for x in entries),
                  falsePositives=sum(x.get("falsePositive", False) for x in entries),
                  completed=sum(x.get("status") == "complete" for x in entries),
                  measuredUsd=round(sum(x.get("costUsd", 0) for x in entries), 8))
    write_json(path, result)


def sound_assets(output):
    rate = 24000
    rng = np.random.default_rng(19)
    t = np.arange(int(rate * 1.65)) / rate
    noise = rng.normal(size=len(t))
    soft = np.convolve(noise, np.hanning(49) / 24, mode="same")
    wood = (soft * .12 + np.sin(2 * np.pi * (72 * t - 8 * t * t)) * .07) * np.sin(np.pi * t / 1.65) ** 2
    t = np.arange(int(rate * .9)) / rate
    chime = (np.sin(2 * np.pi * 523.25 * t) + .45 * np.sin(2 * np.pi * 784 * t)) * .12
    chime *= np.exp(-6 * t) * (1 - np.exp(-150 * t)) * np.clip((.9 - t) / .1, 0, 1)
    for filename, label, signal in [
        ("foley-portas.wav", "Madeira · deslizamento suave (1,65 s)", wood),
        ("acento-luz.wav", "Acento harmônico · revelação (0,9 s)", chime),
    ]:
        file = output / filename
        with wave.open(str(file), "wb") as handle:
            handle.setparams((1, 2, rate, 0, "NONE", "not compressed"))
            handle.writeframes((signal * 32767).astype("<i2").tobytes())
        yield file, label


def main(evidence, output, phase):
    runtime = Path(".codex-runtime/clicko-dev").resolve()
    os.environ.update(ENVIRONMENT="development", DATABASE_URL="sqlite:///" + (runtime / "studios/records.sqlite").as_posix(),
                      STORAGE_PATH=str(runtime / "studios/uploads"),
                      STUDIO_LLM_CREDENTIAL_KEY=(runtime / "llm-credential-key").read_text().strip())
    from sqlalchemy import select

    from app.config import get_settings
    from app.database import SessionLocal
    from app.domain.studios.contracts import CreateStudioDocumentRequest
    from app.domain.studios.craft import CraftAICommandRequestV1
    from app.domain.studios.editing_resources import ResourceMetadataV1
    from app.domain.studios.llm import LLMConnectionRequest
    from app.models import CreativeDocument, StudioGenerationJob, StudioLLMConnection, User
    from app.services.object_storage import get_object_storage
    from app.services.studios import craft, craft_agent, craft_ai, craft_drafts, editing_resources, llm_connections
    from app.services.studios.compatibility import record_to_contract
    from app.services.studios.external_policy import committed, job_scope
    from app.services.studios.kernel import create_document

    output.mkdir(parents=True, exist_ok=True)
    transfer = json.loads((evidence / "transferencia-recibo.json").read_text(encoding="utf-8"))
    case = json.loads((CASE / "transferencia-casa-lume-escolhas.json").read_text(encoding="utf-8"))
    with SessionLocal() as db:
        seed = db.get(CreativeDocument, transfer["seedId"])
        source = record_to_contract(seed)
        previous = db.get(StudioGenerationJob, "ade2bdf3-c30e-4b6a-90b4-4c99850ddc4c")
        user = db.get(User, source.actor_id)
        assert previous.workspace_id == seed.workspace_id and previous.requested_by == user.id
        user._studio_billing_scope = job_scope(previous)
        connection, provider, model, _ = llm_connections.planner(
            db, seed.workspace_id, "9947192f-7acf-466c-b46b-a3eab369f618", MODEL)
        assert connection.provider == "anthropic" and connection.config["baseUrl"].rstrip("/") == "https://api.anthropic.com/v1"
        if phase in ("all", "detect"):
            measure_detection(provider, evidence, output)
        if phase == "detect":
            return

        file = output / "recibo-edicao.json"
        log = json.loads(file.read_text(encoding="utf-8")) if file.exists() else {}
        payload = CreateStudioDocumentRequest.model_validate({
            "workspaceId": source.workspace_id, "contentType": "video", "brandRevision": source.brand_memory_ref.revision,
            "title": "Casa Lume · edição autônoma Opus 5.5",
            "brief": source.brief.model_dump(mode="json", by_alias=True),
            "composition": source.composition.model_dump(mode="json", by_alias=True),
        })
        branch = create_document(db, payload, user, creation_key=KEY)
        if branch.revision == 1:
            with craft.workspace_files(db, seed, source.native_editor_state) as (_directory, params, _manifests):
                craft.save_native(db, branch, user, Path(params["nativePath"]), engine="effectcraft",
                                  expected_revision=1, key=KEY + "-clone")
            assert record_to_contract(branch).native_editor_state.checksum_sha256 == source.native_editor_state.checksum_sha256
        run_key = KEY
        preflight = craft_drafts.session_job(db, branch, KEY)
        if (preflight and preflight.error_code == "external_monthly_budget_exceeded"
                and not (preflight.result_payload or {}).get("submissionStarted")):
            log["rejectedPreflightId"] = preflight.id
            run_key += "-reserved"
        existing = craft_drafts.session_job(db, branch, run_key)
        prior_cost = 0.0
        if existing and existing.error_code == "llm_generation_budget_exceeded":
            state = existing.result_payload or {}
            if (state.get("submissionOutcome") == "response_received" and not state.get("draft")
                    and not state.get("uncertainCostUpperBoundUsd") and not craft_agent.pending_exposure(existing)):
                prior_cost = state["measuredCostUsd"]
                log["countingRetry"] = {"jobId": existing.id, "measuredUsd": prior_cost, "turns": state["turns"]}
                run_key += "-counted"
                existing = craft_drafts.session_job(db, branch, run_key)
        budget = round(1.50 - prior_cost, 8)
        if existing is None and "sounds" not in log:
            sounds = []
            for path, title in sound_assets(output):
                asset = editing_resources.store_resource(db, branch.workspace_id, title, path,
                    ResourceMetadataV1(kind="sound_effect", usageEvidence="Síntese local original para o ensaio Casa Lume."), user.id)
                editing_resources.attach_resource(db, branch, asset.id, branch.revision)
                sounds.append({"title": title, "assetId": asset.id})
            db.commit()
            log["sounds"] = sounds
            write_json(file, log)

        edit_connection = db.get(StudioLLMConnection, log.get("connectionId")) if log.get("connectionId") else None
        if edit_connection is None:
            config = {**connection.config, "budgetUsd": 1.50, "maxOutputTokens": 12000,
                      "inputUsdPerMillion": 4, "outputUsdPerMillion": 20, "models": [MODEL],
                      "label": "Opus 5.5 · Casa Lume transferência", "provider": "anthropic",
                      "apiKey": llm_connections.decrypt(connection)}
            entry = llm_connections.save(db, branch.workspace_id, LLMConnectionRequest.model_validate(config), user)
            edit_connection = db.get(StudioLLMConnection, entry["id"])
            log["connectionId"] = edit_connection.id

        instruction = f"""{case['briefing']}

Edite o projeto nativo existente e exporte pelo EffectCraft. Consulte orbita-reveal-protect-title no repertório. Aplique o princípio ao novo briefing com sua própria direção e seus próprios comandos. Examine o material e os momentos de movimento e de repouso.

O anúncio é motion graphics para celular. Faça os seis segundos terem progressão perceptível de enquadramento, ação, luz e som. Escolha os cortes, composições, sombra, iluminação, tipografia, ritmo e camadas. A ação deve continuar inteligível e a assinatura precisa de tempo de leitura. Existem dois sons locais originais opcionais, disponíveis para importar e posicionar: {json.dumps(log['sounds'], ensure_ascii=False)}. Você decide se e onde usá-los. Preserve nome, duração, convite e a ação lateral do briefing. Você opera a timeline e a revisão sozinho. Quando estiver pronto, use finish_project para solicitar a exportação do MP4."""
        (output / "briefing.txt").write_text(instruction, encoding="utf-8")
        if run_key != KEY and existing is None:
            settings = get_settings()
            month = datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            rows = [row for row in db.scalars(select(StudioGenerationJob))
                    if row.created_at.replace(tzinfo=UTC) >= month
                    or (row.result_payload or {}).get("financialPeriod") == month.strftime("%Y-%m")
                    or (row.result_payload or {}).get("submissionOutcome") in {"pending", "unknown"}
                    or (row.result_payload or {}).get("submissionStarted")]
            scope = user._studio_billing_scope
            for field, jobs in (
                ("studio_external_monthly_budget_usd", rows),
                ("studio_external_workspace_monthly_budget_usd", [row for row in rows if job_scope(row)["workspaceId"] == scope["workspaceId"]]),
                ("studio_external_user_monthly_budget_usd", [row for row in rows if job_scope(row) == scope]),
            ):
                setattr(settings, field, max(getattr(settings, field), round(sum(committed(row) for row in jobs) + budget, 8)))
            model_ceiling = round(sum(committed(row) for row in rows if row.request_payload.get("model") == MODEL) + budget, 8)
            settings.studio_external_model_monthly_budgets = {
                **settings.studio_external_model_monthly_budgets,
                MODEL: max(settings.studio_external_model_monthly_budgets.get(MODEL, 0), model_ceiling),
            }
            log["reservationScope"] = "This runner only. Existing commitments retained plus the unspent editing budget."

        expected = existing.request_payload["documentRevision"] if existing else branch.revision
        request = CraftAICommandRequestV1(expectedRevision=expected, instruction=instruction,
            connectionId=edit_connection.id, model=model, directionEffort="deliberate")
        log.update(documentId=branch.id, seedId=seed.id, seedRevision=source.revision,
                   sessionKey=run_key, model=MODEL, editCeilingUsd=1.50, attemptCeilingUsd=budget)
        write_json(file, log)
        print(json.dumps({"editDocument": branch.id, "revision": expected, "ceilingUsd": budget}), flush=True)
        start = time.monotonic()
        try:
            if existing and not ((existing.result_payload or {}).get("receiptId") or craft_agent.can_resume(existing)):
                raise ValueError("existing_attempt_not_resumable")
            answer = craft_ai.ai_commands(db, branch, request, user, run_key, native_budget=budget)
            log.update(editReceiptId=answer["receiptId"], revision=answer["document"]["revision"])
            log.pop("runnerError", None)
        except Exception as error:
            db.rollback()
            log["runnerError"] = str(error).split(":", 1)[0]
        job = craft_drafts.session_job(db, branch, run_key)
        if job:
            state = job.result_payload or {}
            log.update(jobId=job.id, status=job.status, error=job.error_code,
                       measuredUsd=state.get("measuredCostUsd", 0), turns=state.get("turns", []),
                       combinedEditUsd=round(prior_cost + state.get("measuredCostUsd", 0), 8),
                       lastCountedInputTokens=state.get("lastCountedInputTokens"),
                       tools=state.get("tools", []), rationale=state.get("aiTrace", {}).get("rationale"),
                       savedBatches=state.get("draft", {}).get("batches", 0),
                       uncertainUsd=round(state.get("uncertainCostUpperBoundUsd", 0) + craft_agent.pending_exposure(job), 8),
                       exportRequested=state.get("exportRequested"), exportJobId=state.get("exportJobId"))
            render = db.get(StudioGenerationJob, log["exportJobId"]) if log["exportJobId"] else None
            if render:
                log.update(exportStatus=render.status, exportError=render.error_code)
                if render.status == "succeeded":
                    artifact = render.result_payload["artifact"]
                    asset = craft.scoped_asset(db, branch.workspace_id, artifact["assetId"], artifact["checksumSha256"])
                    with get_object_storage(asset.storage_backend).materialize(asset.storage_key) as media:
                        shutil.copyfile(media, output / "casa-lume-opus.mp4")
                    with craft.native_bundle(db, branch, record_to_contract(branch).native_editor_state) as bundle:
                        shutil.copyfile(bundle, output / "casa-lume-opus-editavel.zip")
                    log["artifact"] = artifact
        db.refresh(seed)
        log["sourceUnchanged"] = seed.revision == source.revision and (
            record_to_contract(seed).native_editor_state.checksum_sha256 == source.native_editor_state.checksum_sha256)
        log["elapsedSeconds"] = round(time.monotonic() - start, 3)
        write_json(file, log)
        print(json.dumps({key: log.get(key) for key in ("status", "error", "runnerError", "measuredUsd",
                         "uncertainUsd", "savedBatches", "exportStatus", "elapsedSeconds")}), flush=True)
        if log.get("exportStatus") != "succeeded":
            raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--phase", choices=["detect", "edit", "all"], default="all")
    args = parser.parse_args()
    main(args.evidence.resolve(), args.output.resolve(), args.phase)
