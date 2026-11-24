"""One real Claude session through Clicko. No manual scene editing or model simulation."""
import argparse
import json
import os
import shutil
import sqlite3
import sys
import time
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
KEY = "video-quality-fixes-claude-20261114-v1"
CONNECTION = "9947192f-7acf-466c-b46b-a3eab369f618"
SOURCE = "acee0fdc-007b-47be-8eae-70a5f5eb2381"


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    temporary.replace(path)


def preflight(runtime, output, *, expected_build="clicko-effectcraft-1.0.3+67434e90"):
    """Read the existing configuration; count_tokens is not a Messages submission."""
    from app.providers.studios.craft import require_capability
    from app.providers.studios.universal_llm import UniversalLLMPlanner
    from app.services.studios.llm_connections import decrypt

    checks = {"apiSpendUsd": 0, "messagesSubmitted": False, "checks": {}, "errors": []}
    with sqlite3.connect((runtime / "studios/records.sqlite").as_uri() + "?mode=ro", uri=True) as db:
        row = db.execute("SELECT id,workspace_id,config,credential_ciphertext FROM studio_llm_connections WHERE id=?",
                         (CONNECTION,)).fetchone()
    if not row:
        raise ValueError("configured_claude_connection_missing")
    connection = SimpleNamespace(id=row[0], workspace_id=row[1], config=json.loads(row[2]), credential_ciphertext=row[3])
    config = connection.config
    if not (config["enabled"] and config["protocol"] == "anthropic_messages" and config["billingMode"] == "metered"
            and config["baseUrl"].rstrip("/") == "https://api.anthropic.com/v1"
            and "claude-opus-5-5" in config["models"]
            and (config["inputUsdPerMillion"], config["outputUsdPerMillion"]) == (4, 20)):
        raise ValueError("claude_connection_or_verified_pricing_mismatch")
    try:
        planner = UniversalLLMPlanner(config, decrypt(connection))
        count = planner.count_craft_tokens("claude-opus-5-5", "Connectivity preflight",
            [{"role": "user", "content": "Check availability only."}], [], 15)
        checks["checks"]["claude"] = {"ready": True, "inputTokens": count}
    except Exception as error:
        checks["checks"]["claude"] = {"ready": False}
        checks["errors"].append(str(error).split(":", 1)[0])
    try:
        capability = require_capability("effectcraft")
        checks["checks"]["engine"] = {"ready": "mp4" in capability["formats"]
            and capability["buildId"] == expected_build, "buildId": capability["buildId"]}
        if not checks["checks"]["engine"]["ready"]:
            checks["errors"].append("qualified_video_fixes_build_or_mp4_export_unavailable")
    except Exception as error:
        checks["checks"]["engine"] = {"ready": False}
        checks["errors"].append(str(error).split(":", 1)[0])
    checks["status"] = "ready" if not checks["errors"] else "blocked"
    write(output / "preflight.json", checks)
    print(json.dumps(checks, ensure_ascii=False), flush=True)
    return checks["status"] == "ready"


def main(args):
    runtime, output = args.runtime.resolve(), args.output.resolve()
    os.environ.update(ENVIRONMENT="development", DATABASE_URL="sqlite:///" + (runtime / "studios/records.sqlite").as_posix(),
                      STORAGE_PATH=str(runtime / "studios/uploads"), PYTHONIOENCODING="utf-8")
    os.environ["STUDIO_LLM_CREDENTIAL_KEY"] = (runtime / "llm-credential-key").read_text().strip()
    if args.binary:
        os.environ["STUDIO_CRAFT_EFFECTCRAFT_BINARY"] = str(args.binary.resolve(strict=True))
    sys.path.insert(0, str(ROOT / "backend"))
    if args.phase != "collect" and not preflight(runtime, output):
        return 2
    if args.phase == "preflight":
        return 0

    from app.database import SessionLocal
    from app.domain.studios.contracts import CreateStudioDocumentRequest
    from app.domain.studios.craft import CraftAICommandRequestV1
    from app.domain.studios.editing_resources import ResourceMetadataV1
    from app.models import CreativeDocument, StudioGenerationJob, User
    from app.services.object_storage import get_object_storage
    from app.services.studios import craft, craft_ai, craft_agent, craft_drafts, editing_resources
    from app.services.studios.compatibility import record_to_contract
    from app.services.studios.craft_media_prepare import prepare_video_excerpt
    from app.services.studios.kernel import create_document

    file = output / "recibo.json"
    receipt = json.loads(file.read_text(encoding="utf-8")) if file.exists() else {}
    with SessionLocal() as db:
        origin = db.get(CreativeDocument, SOURCE)
        if origin is None:
            raise ValueError("source_project_missing")
        source = record_to_contract(origin)
        user = db.get(User, source.actor_id)
        if args.phase == "prepare":
            if receipt or not args.master:
                raise ValueError("prepared_receipt_exists_or_master_missing")
            materials = []
            for name, start, duration in (("travessia-master", 219.8, 3), ("maquina-master", 299.5, 6)):
                path = output / "materiais" / (name + ".mp4")
                preparation = prepare_video_excerpt(args.master, path, start, duration)
                metadata = ResourceMetadataV1(kind="video", description=name + "; quadro completo e cadência nativa",
                    usageEvidence="Tears of Steel © Blender Foundation, CC BY 3.0; excerto para o teste interno ÓRBITA.",
                    framing="Quadro completo do master, sem recorte nem ampliação.",
                    motionDescription="Velocidade 1; sem duplicação artificial para alongar a tomada.")
                asset = editing_resources.store_resource(db, origin.workspace_id, path.name, path, metadata, user.id,
                    provenance={"productionPreparation": preparation})
                materials.append({"assetId": asset.id, "preparation": preparation})
            branch = create_document(db, CreateStudioDocumentRequest.model_validate({
                "workspaceId": origin.workspace_id, "contentType": "video", "brandRevision": source.brand_memory_ref.revision,
                "title": "ÓRBITA · teste do sistema com Claude · correções de qualidade",
                "brief": source.brief.model_dump(mode="json", by_alias=True),
                "composition": source.composition.model_dump(mode="json", by_alias=True),
                "assets": [item.model_dump(mode="json", by_alias=True) for item in source.assets],
            }), user, creation_key=KEY)
            native = source.native_editor_state
            with craft.workspace_files(db, origin, native) as (_, params, _):
                craft.save_native(db, branch, user, Path(params["nativePath"]), engine="effectcraft", expected_revision=1,
                                  key=KEY+"-clone", asset_manifest=native.asset_manifest, font_manifest=native.font_manifest)
            for item in materials:
                editing_resources.attach_resource(db, branch, item["assetId"], branch.revision)
            db.commit()
            receipt = {"stage": "prepared", "documentId": branch.id, "revision": branch.revision,
                "sourceDocumentId": origin.id, "sourceRevision": source.revision,
                "sourceSha256": native.checksum_sha256, "materials": materials,
                "generationBudgetUsd": 5, "apiSpendUsd": 0, "editor": "Claude via Clicko; no manual scene edits"}
            write(file, receipt)
            print(json.dumps({"stage": "prepared", "apiSpendUsd": 0, "documentId": branch.id}), flush=True)
            return 0
        if not receipt:
            raise ValueError("prepare_the_system_test_first")
        branch = db.get(CreativeDocument, receipt["documentId"])
        if args.phase == "generate":
            existing = craft_drafts.session_job(db, branch, KEY)
            if existing:
                raise ValueError("existing_test_do_not_submit_a_second_generation")
            instruction = f'''Edite este anúncio de ÓRBITA no sistema. Você, Claude, escolhe e executa as edições.
Preserve 0–5 s e 11–18 s do projeto e eleve o miolo 5–11 s. Preserve a copy, identidade e atribuição CC BY 3.0 existentes.
Copy: O futuro cabe num curta. ÓRBITA, mostra de curtas de ficção científica. Confira a programação.
Não invente data, local, ingressos ou programação. A mostra é fictícia.
Foram preparados estes ativos de produção: {json.dumps(receipt['materials'], ensure_ascii=False)}.
Use os masters novos para a ação, mantendo cadência natural e informação suficiente para ver sujeito e máquina.
Os antigos derivados cortados e esticados não são as fontes de produção deste teste.
Observe o projeto, veja as fontes e as referências research.model.cinematic_motif, research.model.product_in_action,
research.model.layered_collage e orbita.quality.baseline. Escolha uma transformação editorial que o material realmente sustente.
Consulte contratos e fontes só quando necessário, aproveitando inspectionMemory. Registre uma direção curta e aplique edições.
Confirme curvas de entrada/saída e assentamento do movimento; use easing quando a intenção pedir desaceleração.
Revise a composição completa com review_clip overview. Nas janelas solicitadas, examine páginas consecutivas na taxa nativa.
Se editar depois, revise novamente a versão alterada. Confira texto em tamanho de celular, cortes e som técnico.
Não afirme escuta perceptiva nem aprovação humana. Ao concluir, peça finish_project com deliveryStatus reviewed e pendências vazias
somente se os critérios verificáveis passaram. Se faltar orçamento ou houver defeito, preserve/exporte draft e liste unresolvedIssues.
O teto total desta única tarefa é US$ 5, incluindo todas as consultas, direção, edição e revisão. Não use especialistas pagos.'''
            request = CraftAICommandRequestV1(expectedRevision=receipt["revision"], instruction=instruction,
                connectionId=CONNECTION, model="claude-opus-5-5", directionEffort="open_ended", generationBudgetUsd=5,
                requireExport=True, reviewWindows=[{"startSeconds": 5, "durationSeconds": .4},
                    {"startSeconds": 8.6, "durationSeconds": .4}, {"startSeconds": 10.7, "durationSeconds": .3}])
            write(output / "pedido.json", request.model_dump(mode="json", by_alias=True))
            started = time.monotonic()
            try:
                craft_ai.ai_commands(db, branch, request, user, KEY)
            except Exception as error:
                db.rollback()
                receipt["error"] = str(error).split(":", 1)[0]
            receipt["executionSeconds"] = round(time.monotonic()-started, 3)
        job = craft_drafts.session_job(db, branch, KEY)
        if not job:
            write(file, receipt)
            return 1
        state = job.result_payload or {}
        receipt.update(stage=job.status, jobId=job.id, apiSpendUsd=state.get("measuredCostUsd", 0),
            uncertainUsd=round(state.get("uncertainCostUpperBoundUsd", 0) + craft_agent.pending_exposure(job), 8),
            paidResponses=len(state.get("turns", [])), tools=[item["name"] for item in state.get("tools", [])],
            savedBatches=state.get("draft", {}).get("batches", 0), deliveryReview=state.get("deliveryReview"),
            exportRequested=state.get("exportRequested"), exportJobId=state.get("exportJobId"))
        write(output / "evidencia-job.json", {"request": job.request_payload, "result": state})
        if state.get("exportJobId"):
            render = db.get(StudioGenerationJob, state["exportJobId"])
            receipt["exportStatus"] = render.status
            if render.status == "succeeded":
                artifact = render.result_payload["artifact"]
                asset = craft.scoped_asset(db, branch.workspace_id, artifact["assetId"], artifact["checksumSha256"])
                with get_object_storage(asset.storage_backend).materialize(asset.storage_key) as path:
                    shutil.copyfile(path, output / "claude-via-clicko.mp4")
                native = record_to_contract(branch).native_editor_state
                with craft.native_bundle(db, branch, native) as bundle:
                    shutil.copyfile(bundle, output / "claude-via-clicko-editavel.zip")
                receipt.update(artifact=artifact, finalRevision=branch.revision)
        db.refresh(origin)
        receipt["sourcePreserved"] = (origin.revision == receipt["sourceRevision"]
            and record_to_contract(origin).native_editor_state.checksum_sha256 == receipt["sourceSha256"])
        if not receipt["sourcePreserved"]:
            raise ValueError("source_project_changed_during_test")
        write(file, receipt)
        print(json.dumps({k: receipt.get(k) for k in ("stage", "apiSpendUsd", "uncertainUsd", "paidResponses", "savedBatches", "deliveryReview", "exportStatus")}), flush=True)
        return 0 if receipt.get("exportStatus") == "succeeded" else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("preflight", "prepare", "generate", "collect"))
    parser.add_argument("--runtime", type=Path, default=ROOT/".codex-runtime/clicko-dev")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--master", type=Path)
    parser.add_argument("--binary", type=Path)
    raise SystemExit(main(parser.parse_args()))
