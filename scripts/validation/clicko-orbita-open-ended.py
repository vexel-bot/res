"""Run one capped real Opus edit from the locally verified ÓRBITA revision."""
import argparse
import hashlib
import json
import os
import shutil
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / ".codex-runtime/clicko-dev"
KEY = "orbita-open-ended-real-20261113-v1"
CONNECTION = "9947192f-7acf-466c-b46b-a3eab369f618"
SOURCE = "b6970aab-20ba-48aa-9c21-1b0fc2607a09"
SOURCE_HASH = "e243f2aa209ab89fc498277a361664cfac65248dc8978c0393d9c53ad623ddc5"


def write(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    temporary.replace(path)


def main(output, phase):
    os.environ.update(ENVIRONMENT="development", DATABASE_URL="sqlite:///" + (RUNTIME / "studios/records.sqlite").as_posix(),
                      STORAGE_PATH=str(RUNTIME / "studios/uploads"), PYTHONIOENCODING="utf-8")
    os.environ["STUDIO_LLM_CREDENTIAL_KEY"] = (RUNTIME / "llm-credential-key").read_text().strip()
    sys.path.insert(0, str(ROOT / "backend"))
    from app.database import SessionLocal
    from app.domain.studios.contracts import CreateStudioDocumentRequest
    from app.domain.studios.craft import CraftAICommandRequestV1
    from app.models import CreativeDocument, StudioLLMConnection, StudioGenerationJob, User
    from app.services.object_storage import get_object_storage
    from app.services.studios import craft, craft_agent, craft_ai, craft_drafts, craft_references
    from app.services.studios.compatibility import record_to_contract
    from app.services.studios.kernel import create_document

    output.mkdir(parents=True, exist_ok=True)
    file = output / "recibo.json"
    receipt = json.loads(file.read_text(encoding="utf-8")) if file.exists() else {}
    with SessionLocal() as db:
        origin = db.get(CreativeDocument, SOURCE)
        source = record_to_contract(origin)
        assert origin.revision == 3 and source.native_editor_state.checksum_sha256 == SOURCE_HASH
        user = db.get(User, source.actor_id)
        connection = db.get(StudioLLMConnection, CONNECTION)
        assert connection.workspace_id == origin.workspace_id and connection.config["enabled"]
        assert connection.config["baseUrl"] == "https://api.anthropic.com/v1"
        assert (connection.config["inputUsdPerMillion"], connection.config["outputUsdPerMillion"]) == (4, 20)
        if phase == "prepare":
            if receipt:
                raise ValueError("already_prepared_use_existing_receipt")
            references = []
            for ref in craft_references.reference_index():
                evidence = craft_references.inspect_reference(db, origin.workspace_id, user.id, ref["id"])
                references.append(evidence["reference"])
            branch = create_document(db, CreateStudioDocumentRequest.model_validate({
                "workspaceId": origin.workspace_id, "contentType": "video", "brandRevision": source.brand_memory_ref.revision,
                "title": "ÓRBITA · Opus · edição real sem prazo total",
                "brief": source.brief.model_dump(mode="json", by_alias=True),
                "composition": source.composition.model_dump(mode="json", by_alias=True),
                "assets": [item.model_dump(mode="json", by_alias=True) for item in source.assets],
            }), user, creation_key=KEY)
            native = source.native_editor_state
            with craft.workspace_files(db, origin, native) as (_, params, _):
                craft.save_native(db, branch, user, Path(params["nativePath"]), engine="effectcraft",
                    expected_revision=1, key=KEY + "-clone", asset_manifest=native.asset_manifest, font_manifest=native.font_manifest)
            db.commit()
            receipt = {"documentId": branch.id, "revision": branch.revision, "sourceDocumentId": SOURCE,
                       "sourceRevision": 3, "sourceHash": SOURCE_HASH, "apiSpendUsd": 0,
                       "generationBudgetUsd": 5, "model": "claude-opus-5-5", "directionEffort": "open_ended",
                       "references": references, "stage": "prepared"}
            write(file, receipt)
            print(json.dumps({"stage": "prepared", "documentId": branch.id, "references": len(references), "apiSpendUsd": 0}), flush=True)
            return
        branch = db.get(CreativeDocument, receipt["documentId"])
        existing = craft_drafts.session_job(db, branch, KEY)
        if phase in {"generate", "resume"}:
            if phase == "generate" and existing:
                raise ValueError("existing_session_use_collect_or_resume")
            if phase == "resume" and (not existing or not craft_agent.can_resume(existing)):
                raise ValueError("session_not_resumable")
            instruction = '''Edite de verdade este anúncio da ÓRBITA com acabamento de motion publicitário.
Copy aprovada: “O futuro cabe num curta. ÓRBITA, mostra de curtas de ficção científica. Confira a programação.”
A mostra é fictícia. Não há datas, local ou programação confirmados. Os excertos de Tears of Steel são ilustração de ficção científica. Preserve o crédito existente e a licença CC BY 3.0.

Este é o corte local mais recente, 18 segundos, com abertura de 0 a 5 s e assinatura de 11 a 18 s aprovadas apenas para preservação. A tarefa é elevar o miolo, de 5 a 11 s. Preserve duração, imagem, texto, movimentos e áudio fora desse intervalo. Você escolhe a montagem, as relações entre cenas, luz, contraste, efeitos, camadas, movimentos, transições, tipografia e desenho sonoro dentro dele. Existe uma travessia, um detalhe de máquina e sua escala em relação a uma pessoa. Você pode reordenar e transformar a composição se a leitura melhorar. Uma ação pode ficar contínua quando a continuidade a explicar melhor.

Antes de editar, veja a versão atual em preview_sequence, as fontes relevantes com inspect_source_media e os exemplos visuais usando inspect_reference. IDs: research.model.cinematic_motif, research.model.product_in_action, research.model.layered_collage, orbita.quality.baseline. Estude o mecanismo que torna cada exemplo eficaz. Os exemplos são evidências de análise. Sua trilha não foi auditada. Preserve a identidade ÓRBITA em laranja, marfim e céu escuro, com película, órbita e planeta. Julgue continuidade de atenção, hierarquia e uma transformação que revele algo. A copy deve permanecer legível na tela de consumo e a categoria deve ser compreensível no miolo. Um movimento deve orientar o olhar ou revelar uma relação visível.

Os ativos travessia, detalhe e encontro de 540×960 foram preparados para este miolo e já estão em uso, ampliados em 200% numa composição 1080×1920. As tentativas com clipes de 1080×1920 esgotaram a memória local. Há material de áudio e fontes registrados. Consulte contratos e a fonte resolvida quando precisar. O resultado terá imagem e som e será feito no EffectCraft pela Clicko.

Registre sua direção em termos do que o espectador percebe, monte uma primeira alternativa editável e reveja o miolo completo, os vizinhos das passagens e o quadro de leitura no celular. Se a alternativa tiver um trecho fraco, revise-o e compare o antes/depois. Use review_clip para janelas temporais pertinentes e inspect_transition se precisar conferir o pico luminoso. Só quadros parados não comprovam movimento ou escuta. Relate as limitações observadas.

A sessão de edição não tem prazo total. O orçamento total desta única tarefa é US$5, incluindo planejamento, consultas, edição e revisão. Use-o para melhorar o vídeo. Quando a peça estiver pronta, peça você mesmo finish_project para exportar. Preserve o rascunho se o orçamento impedir uma conclusão. Termine com uma justificativa curta em português, citando as decisões e o que você verificou.'''
            if existing:
                instruction = existing.request_payload["input"]["instruction"]
            request = CraftAICommandRequestV1(expectedRevision=receipt["revision"], instruction=instruction,
                connectionId=CONNECTION, model="claude-opus-5-5", directionEffort="open_ended",
                generationBudgetUsd=5, requireExport=True)
            write(output / "pedido.json", request.model_dump(mode="json", by_alias=True))
            started = time.monotonic()
            receipt.pop("runnerError", None)
            try:
                craft_ai.ai_commands(db, branch, request, user, KEY)
            except Exception as error:
                db.rollback()
                receipt["runnerError"] = str(error).split(":", 1)[0]
            receipt["executionSeconds"] = round(receipt.get("executionSeconds", 0) + time.monotonic() - started, 3)
        job = craft_drafts.session_job(db, branch, KEY)
        if not job:
            write(file, receipt)
            print(json.dumps(receipt), flush=True)
            return
        state = job.result_payload or {}
        uncertain = round(state.get("uncertainCostUpperBoundUsd", 0) + craft_agent.pending_exposure(job), 8)
        receipt.update(jobId=job.id, stage=job.status, error=job.error_code,
                       apiSpendUsd=state.get("measuredCostUsd", 0), uncertainUsd=uncertain,
                       turns=len(state.get("turns", [])), savedBatches=state.get("draft", {}).get("batches", 0),
                       exportRequested=state.get("exportRequested"), exportJobId=state.get("exportJobId"),
                       canResume=craft_agent.can_resume(job))
        end = job.finished_at.replace(tzinfo=UTC) if job.finished_at else datetime.now(UTC)
        receipt["elapsedWindowSeconds"] = round((end - job.created_at.replace(tzinfo=UTC)).total_seconds(), 3)
        write(output / "evidencia-job.json", {"request": job.request_payload, "result": state})
        if receipt.get("exportJobId"):
            render = db.get(StudioGenerationJob, receipt["exportJobId"])
            receipt["exportStatus"] = render.status
            if render.finished_at:
                receipt["elapsedWindowSeconds"] = round((render.finished_at.replace(tzinfo=UTC)
                    - job.created_at.replace(tzinfo=UTC)).total_seconds(), 3)
            if render.status == "succeeded":
                artifact = render.result_payload["artifact"]
                asset = craft.scoped_asset(db, branch.workspace_id, artifact["assetId"], artifact["checksumSha256"])
                with get_object_storage(asset.storage_backend).materialize(asset.storage_key) as path:
                    shutil.copyfile(path, output / "orbita-opus-real.mp4")
                native = record_to_contract(branch).native_editor_state
                with craft.native_bundle(db, branch, native) as bundle:
                    shutil.copyfile(bundle, output / "orbita-opus-editavel.zip")
                receipt.update(artifact=artifact, finalRevision=branch.revision, nativeSha256=native.checksum_sha256)
        if not receipt.get("artifact") and state.get("draft"):
            with craft_drafts.bundle(db, branch, job) as bundle:
                shutil.copyfile(bundle, output / "orbita-rascunho.zip")
        db.refresh(origin)
        assert origin.revision == 3 and record_to_contract(origin).native_editor_state.checksum_sha256 == SOURCE_HASH
        receipt["sourcePreserved"] = True
        write(file, receipt)
        print(json.dumps({key: receipt.get(key) for key in ("stage", "jobId", "error", "apiSpendUsd", "uncertainUsd", "turns", "savedBatches", "exportStatus", "canResume")}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("phase", choices=("prepare", "generate", "resume", "collect"))
    args = parser.parse_args()
    main(args.output.resolve(), args.phase)
