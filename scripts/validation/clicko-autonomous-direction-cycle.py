"""Run the approved diagnostic/experiment/production cycle through Clicko's native Claude session."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import subprocess
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
CONNECTION = "9947192f-7acf-466c-b46b-a3eab369f618"


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["prepare", "run", "resume", "collect", "recover-export"])
    parser.add_argument("--runtime", type=Path, default=ROOT / ".codex-runtime/clicko-dev")
    parser.add_argument("--history", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.runtime = args.runtime.resolve()
    args.output = args.output.resolve()
    os.environ.update(DATABASE_URL="sqlite:///" + (args.runtime / "studios/records.sqlite").as_posix(),
                      STORAGE_PATH=str(args.runtime / "studios/uploads"))
    os.environ["STUDIO_LLM_CREDENTIAL_KEY"] = (args.runtime / "llm-credential-key").read_text().strip()
    sys.path.insert(0, str(ROOT / "backend"))
    spec = importlib.util.spec_from_file_location("native_cycle_runner", ROOT / "scripts/validation/clicko-autonomous-cinematic-review.py")
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    receipt_path = args.output / "receipt.json"
    if args.phase == "prepare":
        if receipt_path.exists():
            raise ValueError("cycle_already_prepared")
        from app.database import SessionLocal
        from app.domain.studios.contracts import NativeMediaReferenceV1
        from app.models import CreativeDocument, StudioGenerationJob, User, StudioLLMConnection
        from app.services.studios import craft, craft_project_context as project
        from app.services.studios.compatibility import record_to_contract
        paths = [args.history / "receipt.json", *(args.history / name / "receipt.json"
                 for name in ("segunda-passagem", "terceira-passagem", "quarta-passagem"))]
        history = []
        with SessionLocal() as db:
            for path in paths:
                receipt = json.loads(path.read_text(encoding="utf-8"))
                job = db.get(StudioGenerationJob, receipt["jobId"])
                record = db.get(CreativeDocument, receipt["documentId"])
                render = db.get(StudioGenerationJob, receipt.get("exportJobId"))
                artifact = receipt.get("artifact") or ((render.result_payload or {}).get("artifact")
                                                      if render and render.status == "succeeded" else None)
                if not artifact:
                    history.append({"receipt": receipt, "path": str(path), "workspaceId": record.workspace_id,
                                    "unavailable": "No successful verified historical export"})
                    continue
                receipt["artifact"] = artifact
                asset = craft.scoped_asset(db, record.workspace_id, artifact["assetId"], artifact["checksumSha256"])
                local = path.parent / "orbita-claude-autonomo.mp4"
                if not local.exists() or hashlib.file_digest(local.open("rb"), "sha256").hexdigest() != asset.checksum_sha256:
                    raise ValueError("historical_export_checksum_conflict")
                if job.document_id != record.id or job.request_payload.get("model") != "claude-opus-5-5":
                    raise ValueError("historical_job_binding_conflict")
                history.append({"receipt": receipt, "path": str(path), "workspaceId": record.workspace_id,
                                "nativeChecksum": record_to_contract(record).native_editor_state.checksum_sha256})
            if len({entry["workspaceId"] for entry in history}) != 1:
                raise ValueError("historical_workspace_conflict")
            connection = db.get(StudioLLMConnection, CONNECTION)
            if connection.workspace_id != history[0]["workspaceId"] or not connection.config.get("enabled"):
                raise ValueError("cycle_connection_unavailable")
        # Receipt source is explicit; selection is a starting editable document, not a quality verdict.
        source = history[-1]["receipt"]["documentId"]
        options = SimpleNamespace(runtime=args.runtime, output=args.output, phase="prepare",
            task_key="orbita-direction-v2-cycle-20261115", source_document=source, direction_contract="v2")
        if runner.main(options):
            return 2
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        with SessionLocal() as db:
            branch = db.get(CreativeDocument, receipt["documentId"])
            user = db.get(User, branch.created_by)
            native = record_to_contract(branch).native_editor_state
            manifests = list(native.asset_manifest)
            neutral = sorted([entry for entry in history if not entry.get("unavailable")], key=lambda entry: hashlib.sha256(
                (receipt["taskKey"] + entry["receipt"]["artifact"]["checksumSha256"]).encode()).hexdigest())
            candidates, processes = [], []
            for index, entry in enumerate(neutral):
                label = chr(ord("A") + index)
                historical = entry["receipt"]
                artifact = historical["artifact"]
                asset = craft.scoped_asset(db, branch.workspace_id, artifact["assetId"], artifact["checksumSha256"])
                from app.services.object_storage import get_object_storage
                with get_object_storage(asset.storage_backend).materialize(asset.storage_key) as path:
                    alias, _, _ = craft.write_asset(db, branch, path, suffix=".mp4", media_type="video/mp4",
                        asset_type="video", title="Candidato histórico " + label,
                        metadata={"cycleHistorical": {"label": label, "sourceAssetId": asset.id,
                                  "sourceDocumentId": historical["documentId"], "sourceJobId": historical["jobId"]}})
                db.flush()
                manifests.append(NativeMediaReferenceV1(assetId=alias.id, path=f"assets/{alias.id}.mp4",
                    checksumSha256=alias.checksum_sha256, mediaType="video/mp4"))
                candidates.append({"label": label, "assetId": alias.id, "checksumSha256": alias.checksum_sha256,
                                   "durationSeconds": artifact["durationMs"] / 1000})
                evidence_path = Path(entry["path"]).parent / "job-evidence.json"
                raw = json.loads(evidence_path.read_text(encoding="utf-8"))["result"]
                processes.append({"label": label, "sourceDocumentId": historical["documentId"],
                    "sourceJobId": historical["jobId"], "recordedCostUsd": historical["apiSpendUsd"],
                    "referencesInspected": raw.get("referenceInspections", []),
                    "deliveryReview": historical.get("deliveryReview"),
                    "toolOutcomes": [{"name": tool.get("name"), "ok": tool.get("ok"), "error": tool.get("error")}
                                     for tool in raw.get("tools", raw.get("toolsUsed", []))]})
            processes.extend({"sourceDocumentId": entry["receipt"]["documentId"],
                              "sourceJobId": entry["receipt"]["jobId"], "unavailable": entry["unavailable"]}
                             for entry in history if entry.get("unavailable"))
            with craft.workspace_files(db, branch, native) as (_, params, _):
                craft.save_native(db, branch, user, Path(params["nativePath"]), engine="effectcraft",
                    expected_revision=branch.revision, key=receipt["taskKey"] + "-history",
                    asset_manifest=manifests, font_manifest=native.font_manifest)
            _, state = project.state(db, branch)
            state["cycle"] = {"documentId": branch.id, "stage": "diagnosis", "events": [],
                "historicalCandidates": candidates, "processHistory": processes,
                "userFeedback": "Ambas as versões citadas estão longe da meta; a mais recente foi percebida como regressão. "
                                "O par exato não está comprovado. Compare as quatro versões e registre essa incerteza.",
                "historicalLimitations": ["One of four recorded executions has no verified completed export. "
                                          "Its process log is available after visual diagnosis."],
                "delivery": "Complete draft video, editable project, comparison and unresolved issues."}
            project.save(db, branch, state, state["version"])
            db.commit()
            receipt["revision"] = branch.revision
            write(receipt_path, receipt)
        write(args.output / "history-bindings.json", history)
        briefing = """Desenvolva um novo candidato completo de ÓRBITA buscando as qualidades observáveis das referências que você escolher.
Você tem autonomia total sobre conceito, materiais, fotografia, cenas, efeitos, montagem, som e duração.
As versões anteriores estão abaixo da meta e podem ser reconstruídas. Elogio relativo não significa aprovação.
Use inspect_direction para encontrar os candidatos históricos disponíveis com rótulos neutros. Existem quatro passagens registradas, uma delas sem exportação concluída verificável. Examine a sequência inteira dos vídeos disponíveis em visão geral e aprofunde os acontecimentos, abertura, transições e desfecho. Escolha amostragem e resolução. Compare resultados visuais antes de consultar processo, custo e justificativas anteriores.
Registre diagnóstico com record_cycle_progress(stage=diagnosis, summary, toolUseIds). Depois inspect_cycle_history permite investigar causas técnicas e custos. Registre defeitos persistentes e hipóteses testáveis.
Escolha referências externas pertinentes no catálogo e consulte-as. Onde só existirem pranchas, movimento e som permanecem desconhecidos.
Registre a direção estruturada v2, teste a maior incerteza da proposta com as ferramentas nativas, observe seu resultado e registre record_cycle_progress(stage=experiment). Escolha livremente duração e estratégia. Falhas podem exigir reformulação.
Desenvolva a peça inteira e registre a fase production. Preserve candidatos com save_direction_candidate, faça observações visuais pelo avaliador claude.opus55.visual quando útil e compare com as versões históricas e critérios das referências. Registre comparação, ganhos, perdas e incertezas com record_cycle_progress(stage=comparison).
A entrada de áudio não está disponível no Claude. Você pode compor e ajustar som com ferramentas nativas e medidas técnicas, registrando a falta de escuta.
Não há teto total de custo, prazo total ou número máximo de tentativas. Se estagnar, diagnostique conceito, materiais, execução ou avaliação e escolha nova estratégia.
Entregue um vídeo completo por finish_project com deliveryStatus=draft e unresolvedIssues contendo as pendências reais. O rascunho permite apresentar o candidato completo com a escuta pendente. Registre delivered e conclua quando o candidato escolhido estiver pronto para apresentação.
A direção e a montagem são suas. Objetivo e público continuam os do projeto ÓRBITA. Leia os contratos das ferramentas antes de usá-las."""
        (args.output / "briefing.txt").write_text(briefing, encoding="utf-8")
        return 0
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    phase = "generate" if args.phase == "run" else args.phase
    result = runner.main(SimpleNamespace(runtime=args.runtime, output=args.output, phase=phase,
        task_key=receipt["taskKey"], source_document=receipt["sourceDocumentId"], direction_contract="v2"))
    from app.database import SessionLocal
    from app.models import CreativeDocument, StudioGenerationJob
    from app.services.studios import craft_project_context as project
    with SessionLocal() as db:
        branch = db.get(CreativeDocument, receipt["documentId"])
        _, state = project.state(db, branch)
        write(args.output / "director-state.json", state)
        job = db.get(StudioGenerationJob, json.loads(receipt_path.read_text(encoding="utf-8")).get("jobId"))
        if job:
            write(args.output / "consumption.json", {
                "directorRecordedUsd": job.result_payload.get("measuredCostUsd"),
                "evaluations": job.result_payload.get("directorOperations"),
                "turns": len(job.result_payload.get("turns", [])),
                "uncertainCostUpperBoundUsd": job.result_payload.get("uncertainCostUpperBoundUsd"),
            })
    if result == 0:
        observation_file = args.output / "final-observations.json"
        observations = json.loads(observation_file.read_text(encoding="utf-8")) if observation_file.exists() else []
        if not observations or any(item["operation"]["status"] != "succeeded" for item in observations):
            completed = subprocess.run([sys.executable, str(ROOT / "scripts/validation/clicko-cycle-final-observation.py"),
                                        "--runtime", str(args.runtime), "--output", str(args.output)],
                                       check=False, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            return completed.returncode
    return result


if __name__ == "__main__":
    raise SystemExit(main())
