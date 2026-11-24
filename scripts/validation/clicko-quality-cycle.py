"""Prepare one versioned Clicko project; paid direction requires --phase generate and local gate receipts."""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "benchmarks/studios/orbita/quality-cycle.v1.yaml"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    temporary.replace(path)


def sound_materials(directory):
    """Original local sketch stems, with no fixed cuts baked into the main composition."""
    rate = 24000
    rng = np.random.default_rng(13112026)
    materials = []
    for name, seconds, description in [
        ("01-campo-estelar.wav", 60, "Cama musical original: pulso harmônico lento, 60 s; pode cortar/fazer fade"),
        ("02-impacto.wav", .9, "Impacto curto original; alinhar à ação escolhida"),
        ("03-passagem.wav", .65, "Passagem de ar original; alinhar a deslocamento ou corte"),
        ("04-revelacao.wav", 1.6, "Revelação tonal original; opcional, não narração"),
    ]:
        t = np.arange(round(rate * seconds)) / rate
        if name.startswith("01"):
            chord = np.array([146.832, 116.541, 174.614, 130.813])[np.minimum((t / 8).astype(int) % 4, 3)]
            phase = np.cumsum(chord) / rate
            pulse = .65 + .35 * np.sin(2 * np.pi * .5 * t) ** 2
            signal = (.055 * np.sin(2 * np.pi * phase) + .025 * np.sin(2 * np.pi * phase * 1.5)
                      + .016 * np.sin(2 * np.pi * phase * 2)) * pulse
            signal += .024 * np.sin(2 * np.pi * phase / 2) * np.exp(-7 * np.mod(t, .5))
            signal *= np.clip(t / 1.5, 0, 1) * np.clip((seconds - t) / 2, 0, 1)
        elif name.startswith("02"):
            signal = .25 * np.sin(2 * np.pi * (90 * t - 28 * t * t)) * np.exp(-8 * t)
            signal += rng.normal(0, .035, len(t)) * np.exp(-20 * t)
        elif name.startswith("03"):
            signal = np.convolve(rng.normal(0, .12, len(t)), np.ones(9) / 9, mode="same") * np.sin(np.pi * t / seconds) ** 2
        else:
            signal = (.07 * np.sin(2 * np.pi * 293.665 * t) + .035 * np.sin(2 * np.pi * 440 * t)) * np.exp(-2.4 * t)
        signal *= np.clip(t / .008, 0, 1) * np.clip((seconds - t) / .025, 0, 1)
        pcm = np.stack([signal, signal], axis=1)
        path = directory / name
        with wave.open(str(path), "wb") as target:
            target.setparams((2, 2, rate, 0, "NONE", "not compressed"))
            target.writeframes((np.clip(pcm, -.95, .95) * 32767).astype("<i2").tobytes())
        materials.append((path, "music" if name.startswith("01") else "sound_effect", description))
    return materials


def environment():
    runtime = ROOT / ".codex-runtime/clicko-dev"
    os.environ.update(ENVIRONMENT="development", DATABASE_URL="sqlite:///" + (runtime / "studios/records.sqlite").as_posix(),
                      STORAGE_PATH=str(runtime / "studios/uploads"), PYTHONIOENCODING="utf-8")
    key = runtime / "llm-credential-key"
    if key.is_file():
        os.environ["STUDIO_LLM_CREDENTIAL_KEY"] = key.read_text().strip()
    sys.path.insert(0, str(ROOT / "backend"))


def main(output, phase, gate):
    environment()
    from app.database import SessionLocal
    from app.domain.studios.contracts import CreateStudioDocumentRequest
    from app.domain.studios.craft import CraftAICommandRequestV1, CraftMigrationRequestV1
    from app.domain.studios.editing_resources import ResourceMetadataV1
    from app.models import CreativeDocument, StudioGenerationJob, User
    from app.services.object_storage import get_object_storage
    from app.services.studios import craft, craft_agent, craft_ai, craft_drafts, craft_references, editing_resources
    from app.services.studios.compatibility import record_to_contract
    from app.services.studios.external_policy import job_scope
    from app.services.studios.kernel import create_document

    config = json.loads(CONFIG.read_text(encoding="utf-8"))  # JSON is a YAML subset.
    output.mkdir(parents=True, exist_ok=True)
    file = output / "cycle-receipt.json"
    state = json.loads(file.read_text(encoding="utf-8")) if file.exists() else {
        "schemaVersion": "clicko.quality-cycle-receipt.v1", "cycleId": config["cycleId"],
        "configSha256": digest(CONFIG), "apiSpendUsd": 0, "paidGenerations": 0,
    }
    preflight_retry = (state.get("stage") == "incomplete" and not state.get("jobId")
                       and state.get("runnerError") == "llm_server_credential_key_not_configured")
    resume = (state.get("stage") == "incomplete" and state.get("jobId")
              and state.get("error") in craft_agent.TOKEN_COUNT_TRANSIENT_ERRORS
              and state.get("uncertainUsd") == 0 and state.get("countFailureResumes", 0) < 3)
    if state["configSha256"] != digest(CONFIG):
        raise ValueError("quality_cycle_configuration_changed")
    with SessionLocal() as db:
        origin = db.get(CreativeDocument, config["sourceDocumentId"])
        source = record_to_contract(origin)
        user = db.get(User, source.actor_id)
        previous = db.get(StudioGenerationJob, config["sourceJobId"])
        assert previous.workspace_id == origin.workspace_id and previous.requested_by == user.id
        user._studio_billing_scope = job_scope(previous)
        if phase == "prepare":
            if state.get("stage") == "prepared":
                print(json.dumps({"stage": "prepared", "documentId": state["documentId"], "apiSpendUsd": 0}), flush=True)
                return
            if state.get("paidGenerations"):
                raise ValueError("quality_cycle_generation_already_exists_preserve_receipt")
            baseline = ROOT / "docs/studios/knowledge/orbita-quality-baseline.v1.json"
            record = json.loads(baseline.read_text(encoding="utf-8"))
            baseline_video = output.parent / "clicko-orbita-independente-2026-11-12" / record["artifact"]["filename"]
            assert digest(baseline_video) == record["artifact"]["sha256"]
            state["baseline"] = record
            state["source"] = {"documentId": origin.id, "revision": source.revision,
                               "sha256": source.native_editor_state.checksum_sha256}
            evidence = []
            for identifier in config["referenceIds"]:
                item = craft_references.inspect_reference(db, origin.workspace_id, user.id, identifier)
                assert any(block["type"] == "image" for block in item["blocks"])
                evidence.append(item["reference"])
            state["references"] = evidence
            db.commit()
            branch = create_document(db, CreateStudioDocumentRequest.model_validate({
                "workspaceId": origin.workspace_id, "contentType": "video", "brandRevision": source.brand_memory_ref.revision,
                "title": "ÓRBITA · ciclo de qualidade com referências visuais · 13 novembro",
                "brief": {"objective": config["copy"], "audience": "Público de cinema de ficção científica no celular", "format": "video"},
                "composition": {"pages": [{"id": "main", "width": config["width"], "height": config["height"],
                    "durationMs": config["initialDurationSeconds"] * 1000, "layers": [], "background": "#070c17"}],
                    "mediaTimeline": {"frameRate": {"numerator": config["frameRate"], "denominator": 1},
                        "durationFrames": config["initialDurationSeconds"] * config["frameRate"], "tracks": []}},
            }), user, creation_key=config["cycleId"] + "-project")
            state["documentId"] = branch.id
            write(file, state)
            if not record_to_contract(branch).native_editor_state:
                craft.migrate(db, branch, CraftMigrationRequestV1(engine="effectcraft", expectedRevision=branch.revision), user, config["cycleId"] + "-migrate")
            materials = output / "materials"
            materials.mkdir(exist_ok=True)
            prepared = sound_materials(materials)
            fonts = ROOT / "docs/studios/research/2026-11-13-motion-quality-investigation/probes/orbita-runtime-source.zip"
            import zipfile
            with zipfile.ZipFile(fonts) as archive:
                for name in archive.namelist():
                    if name.endswith(".ttf"):
                        path = materials / Path(name).name
                        path.write_bytes(archive.read(name))
                        prepared.append((path, "font", "Fonte do baseline com licença SIL OFL arquivada junto ao fonte original"))
            rows = []
            for path, kind, description in prepared:
                asset = editing_resources.store_resource(db, branch.workspace_id, path.name, path,
                    ResourceMetadataV1(kind=kind, description=description,
                                       usageEvidence="Síntese original local" if kind != "font" else "SIL Open Font License; licenças no pacote de baseline"), user.id)
                editing_resources.attach_resource(db, branch, asset.id, branch.revision)
                rows.append({"assetId": asset.id, "filename": path.name, "kind": kind, "description": description, "sha256": digest(path)})
            # Existing licensed footage is optional material; no fixed scene structure is imported.
            for item in source.assets:
                if item.media_type.startswith("video/"):
                    editing_resources.attach_resource(db, branch, item.id, branch.revision)
                    rows.append({"assetId": item.id, "kind": "video", "description": item.provenance.get("editingResource", {}).get("description"),
                                 "sha256": item.checksum, "credit": "Tears of Steel © Blender Foundation · CC BY 3.0 · excerto reenquadrado; ilustrativo, não programação confirmada"})
            db.commit()
            state.update(preparedMaterials=rows, revision=branch.revision, stage="prepared", paidGenerations=0)
            write(file, state)
            print(json.dumps({"stage": "prepared", "documentId": branch.id, "materials": len(rows), "references": len(evidence), "apiSpendUsd": 0}), flush=True)
            return

        if not gate or not gate.is_file():
            raise ValueError("quality_cycle_local_gate_required")
        checks = json.loads(gate.read_text(encoding="utf-8"))
        if (checks.get("status") != "passed" or checks.get("apiSpendUsd") != 0
                or checks.get("preparedReceiptSha256") != (state.get("preparedReceiptSha256") if preflight_retry or resume else digest(file))
                or checks.get("animaticReceiptSha256") != digest(output / "animatic.json")
                or checks.get("requiredFailures") != []):
            raise ValueError("quality_cycle_local_gate_not_passed")
        branch = db.get(CreativeDocument, state["documentId"])
        if branch.revision != state["revision"]:
            raise ValueError("quality_cycle_prepared_revision_changed")
        key = config["cycleId"] + "-single-generation"
        existing = craft_drafts.session_job(db, branch, key)
        if resume:
            if not existing or existing.id != state["jobId"] or not craft_agent.can_resume(existing):
                raise ValueError("quality_cycle_draft_not_resumable")
        elif existing is not None or (state.get("paidGenerations") and not preflight_retry):
            raise ValueError("quality_cycle_generation_already_exists_preserve_receipt")
        from app.models import StudioLLMConnection
        connection = db.get(StudioLLMConnection, config["connectionId"])
        if (not connection or connection.workspace_id != branch.workspace_id or not connection.config["enabled"]
                or config["model"] not in connection.config["models"]
                or connection.provider != "anthropic" or connection.config["billingMode"] == "local_free"
                or connection.config["baseUrl"].rstrip("/") != "https://api.anthropic.com/v1"
                or (connection.config["inputUsdPerMillion"], connection.config["outputUsdPerMillion"]) != (4, 20)):
            raise ValueError("quality_cycle_connection_or_pricing_mismatch")
        instruction = f'''Crie UM anúncio motion graphics completo de ÓRBITA, mostra fictícia de curtas de ficção científica.
Copy aprovada, preservar texto e sentido: {config['copy']}
Nenhuma data, local, ingresso ou programação específica foi fornecida. Não invente esses dados.

Você dirige duração, cenas, composições, cortes, luz, sombras, efeitos, camadas, ritmo e som. Os 30 s iniciais do projeto são ponto de partida. Mude a duração se servir à peça. Procure progressão, materialidade, variação de escala e uma consequência visual ligada à promessa. Cada trecho deve dar ao espectador algo reconhecível que se revela, transforma ou ganha significado.

Use inspect_reference para ver os exemplos reais pelos IDs {json.dumps(config['referenceIds'], ensure_ascii=False)}. São referências de funções distintas, não obrigação de combinar estilos. O baseline ÓRBITA foi o primeiro progresso reconhecido pelo proprietário; não foi aprovado como anúncio final: é silencioso e tem clarão perto de8s. Aprenda sua relação entre filme e mundos, sem repetir o clarão. Descrições não substituem ver as imagens. Som dos Reels não foi auditado.

Materiais preparados: {json.dumps(state['preparedMaterials'], ensure_ascii=False)}
Sons são esboços originais editáveis, não uma trilha já sincronizada: escolha importação, posição e ganho/fades. A peça exige desenho sonoro; narração é opcional e não há serviço pago de voz neste ciclo. Os clipes de Tears of Steel são opcionais e ilustrativos: se usados, conservar crédito discreto de Blender Foundation/CC BY3.0 e indicar edição, sem sugerir presença na programação. Fontes estão disponíveis; confira família/peso no motor antes de compor.

Registre sua direção, construa a montagem editável, reveja abertura/desenvolvimento/assinatura e as transições relevantes em tamanho de celular. review_clip mostra quadros e medidas, não escuta perceptiva. Corrija problemas essenciais e peça você mesmo finish_project para exportar o MP4. Você pode editar com script livre do EffectCraft e quantas camadas forem úteis. O runtime e os materiais já estão prontos; não reconstrua infraestrutura. O teto total de direção/revisão/correções é US$5; não é meta de consumo. Nesta sessão limitada não há delegação paga, pois a rota antiga de enxame ainda não compartilha esse teto. Preserve rascunho se faltar orçamento. Termine com uma justificativa curta em português.'''
        if resume:
            instruction = existing.request_payload["input"]["instruction"]
            state["countFailureResumes"] = state.get("countFailureResumes", 0) + 1
        (output / "briefing.txt").write_text(instruction, encoding="utf-8")
        request = CraftAICommandRequestV1(expectedRevision=branch.revision, instruction=instruction,
            connectionId=config["connectionId"], model=config["model"], directionEffort="deliberate",
            generationBudgetUsd=config["generationBudgetUsd"], executionTimeLimitSeconds=config["executionTimeLimitSeconds"], requireExport=True)
        state.pop("runnerError", None)
        state.update(stage="submitted", paidGenerations=1, sessionKey=key, localGateSha256=digest(gate),
                     preparedReceiptSha256=checks["preparedReceiptSha256"])
        write(file, state)
        start = time.monotonic()
        try:
            answer = craft_ai.ai_commands(db, branch, request, user, key)
            state["receiptId"] = answer["receiptId"]
        except Exception as error:
            db.rollback()
            state["runnerError"] = str(error).split(":", 1)[0]
        job = craft_drafts.session_job(db, branch, key)
        if job:
            result = job.result_payload or {}
            state.update(jobId=job.id, status=job.status, error=job.error_code, measuredUsd=result.get("measuredCostUsd", 0),
                uncertainUsd=round(result.get("uncertainCostUpperBoundUsd", 0) + craft_agent.pending_exposure(job), 8),
                exportRequested=result.get("exportRequested"), exportJobId=result.get("exportJobId"),
                turns=result.get("turns", []), tools=result.get("tools", []),
                savedBatches=result.get("draft", {}).get("batches", 0), rationale=result.get("aiTrace", {}).get("rationale"))
            state["apiSpendUsd"] = state["measuredUsd"]
            render = db.get(StudioGenerationJob, state["exportJobId"]) if state.get("exportJobId") else None
            if render:
                state.update(exportStatus=render.status, exportError=render.error_code)
                if render.status == "succeeded":
                    artifact = render.result_payload["artifact"]
                    asset = craft.scoped_asset(db, branch.workspace_id, artifact["assetId"], artifact["checksumSha256"])
                    with get_object_storage(asset.storage_backend).materialize(asset.storage_key) as media:
                        shutil.copyfile(media, output / "orbita-opus-quality-cycle.mp4")
                    state["artifact"] = artifact
                    with craft.native_bundle(db, branch, record_to_contract(branch).native_editor_state) as bundle:
                        shutil.copyfile(bundle, output / "orbita-opus-editavel.zip")
            if not state.get("artifact") and (result.get("draft") or {}).get("storageKey"):
                with craft_drafts.bundle(db, branch, job) as bundle:
                    shutil.copyfile(bundle, output / "orbita-opus-rascunho.zip")
            write(output / "job-evidence.json", {"request": job.request_payload, "result": result})
        db.refresh(origin)
        state.update(elapsedSeconds=round(time.monotonic() - start, 3), sourceUnchanged=origin.revision == state["source"]["revision"]
                     and record_to_contract(origin).native_editor_state.checksum_sha256 == state["source"]["sha256"],
                     stage="completed" if state.get("exportStatus") == "succeeded" else "incomplete")
        write(file, state)
        print(json.dumps({key: state.get(key) for key in ("stage", "jobId", "status", "error", "runnerError", "measuredUsd", "uncertainUsd", "exportStatus", "elapsedSeconds")}), flush=True)
        if state["stage"] != "completed":
            raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--phase", choices=["prepare", "generate"], default="prepare")
    parser.add_argument("--local-gate", type=Path)
    args = parser.parse_args()
    main(args.output.resolve(), args.phase, args.local_gate.resolve() if args.local_gate else None)
