"""Local directed reference through res APIs; never fabricates human approval.

Run from repository root with PYTHONPATH=backend. The isolated database and
shared correlation retain reservations across runs. Paid jobs never auto retry.
"""

# ruff: noqa: E402
import base64
import json
import os
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output/hybrid-aurora-pilot"
OUT.mkdir(parents=True, exist_ok=True)
os.chdir(ROOT)
from app.config import get_settings

s = get_settings()
if s.environment == "production":
    raise RuntimeError("local_pilot_only")
s.environment = "test"
s.database_url = "sqlite:///" + (OUT / "pilot.sqlite").as_posix()
s.storage_path = str(OUT / "storage")
s.object_storage_backend = "local"
s.remotion_native_enabled = True
s.studio_isolated_queues_enabled = False
s.studio_production_test_budget_usd = 10
s.studio_gemini_test_budget_usd = 10
s.studio_editing_ai_test_budget_usd = 10
s.studio_gemini_enabled = True
s.gemini_outbound_enabled = True
s.gemini_video_generation_enabled = True
s.studio_gemini_test_key = s.gemini_api_key_2 or s.gemini_api_key_1
s.studio_gemini_video_model = "veo-3.1-fast-generate-preview"
s.studio_editing_ai_video_provider = "gemini"
s.studio_editing_ai_planning_provider = "compatible"
s.studio_editing_ai_test_key = s.openai_api_key
s.studio_editing_ai_input_usd_per_million = 2
s.studio_editing_ai_output_usd_per_million = 8
s.studio_editing_ai_price_version = "openai-gpt41-2026-09-30"
s.studio_editing_ai_max_output_tokens = 12000
s.celery_task_always_eager = False

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.domain.studios.contracts import CreativeDocumentV1
from app.domain.studios.editing_resources import EditingAIRequestV1
from app.main import app
from app.models import CreativeDocument, LibraryAsset, StudioGenerationJob, User
from app.providers.studios.gemini_editing import GeminiEditingProvider
from app.services.object_storage import get_object_storage
from app.services.studios.compatibility import persist_contract, record_to_contract
from app.services.studios.gemini_editing import create_editing_job
from app.services.studios.jobs import execute_job_once

CORRELATION = "hybrid-aurora-pilot-20260930"


def write(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def initialize():
    Base.metadata.create_all(engine)
    credentials = OUT / ".local-session.json"
    client = TestClient(app)
    if credentials.exists():
        binding = json.loads(credentials.read_text())
        response = client.post("/api/v1/auth/login", json={"email": binding["email"], "password": binding["password"]})
    else:
        binding = {"email": "hybrid-aurora-local@example.com", "password": "local-" + os.urandom(20).hex()}
        response = client.post(
            "/api/v1/auth/register",
            json={**binding, "name": "Aurora pilot", "workspaceName": "Aurora · edição híbrida"},
        )
    response.raise_for_status()
    client.headers["Authorization"] = "Bearer " + response.json()["accessToken"]
    workspace = client.get("/api/v1/bootstrap").json()["workspaces"][0]["id"]
    binding["workspace"] = workspace
    if "document" not in binding:
        with SessionLocal() as db:
            user = db.scalar(select(User).where(User.email == binding["email"]))
            record = CreativeDocument(
                workspace_id=workspace, title="Aurora · materiais e geração", document={}, created_by=user.id
            )
            db.add(record)
            db.flush()
            doc = base_document(record, [])
            persist_contract(record, doc)
            db.commit()
            binding["document"] = record.id
        write(".local-session.json", binding)
    return client, binding


def base_document(record, assets):
    now = datetime.now(UTC)
    return CreativeDocumentV1(
        document_id=record.id,
        workspace_id=record.workspace_id,
        title=record.title,
        content_type="video",
        correlation_id=CORRELATION,
        brand_memory_ref={"id": "aurora-reference", "revision": 1},
        brief={
            "objective": "Anúncio Café Aurora, 15 segundos, sem locução; filmagem, motion e som",
            "audience": "Pessoas que apreciam café",
        },
        assets=assets,
        composition={"pages": [{"id": "canvas", "width": 720, "height": 1280, "safeArea": 36}]},
        created_at=now,
        updated_at=now,
    )


def receipts(db):
    jobs = db.scalars(select(StudioGenerationJob).where(StudioGenerationJob.correlation_id == CORRELATION)).all()
    rows = [
        {
            "jobId": j.id,
            "provider": j.provider,
            "status": j.status,
            "model": j.request_payload.get("model"),
            "error": j.error_message,
            "reservedUsd": (j.result_payload or {}).get("testReservationUsd", 0),
            "measuredUsd": (j.result_payload or {}).get("measuredCostUsd"),
            "usage": (j.result_payload or {}).get("usage"),
            "submissionOutcome": (j.result_payload or {}).get("submissionOutcome"),
        }
        for j in jobs
    ]
    music_path = OUT / "music-reservation.json"
    external = [json.loads(music_path.read_text(encoding="utf-8"))] if music_path.exists() else []
    conservative = sum(
        float(row["measuredUsd"] if row["measuredUsd"] is not None else row["reservedUsd"]) for row in rows
    )
    conservative += sum(float(row.get("measuredUsd", row["reservedUsd"])) for row in external)
    write(
        "cost-receipts.json",
        {
            "limitUsd": 10,
            "jobs": rows,
            "externalReservations": external,
            "conservativeCommittedUsd": round(conservative, 6),
            "billingReconciliation": "Reservations are retained when provider omits measured cost.",
        },
    )


def generate(binding, label):
    prompts = {
        "beans": (
            "Single continuous macro shot, vertical 9:16, roasted coffee beans fall from upper right "
            "onto a dark walnut table and bounce, warm sunrise sidelight, premium tactile food advertising, "
            "crisp natural movement, no camera move, no text, no packaging, no logos, no dialogue, no music. "
            "Sound: sharp dry bean impacts synchronized with each visible landing, quiet room ambience."
        ),
        "pour": (
            "Single continuous vertical 9:16 close shot, dark freshly brewed coffee pours from a clear glass "
            "carafe from upper right into a plain ivory ceramic cup on a dark walnut table, warm sunrise sidelight, "
            "realistic liquid and faint steam. No text, no logos, no packaging, no dialogue, no music. "
            "Audible coffee pouring and gentle cup contact, no added dramatic effects."
        ),
    }
    if label not in prompts:
        raise ValueError("unknown_generation_need")
    with SessionLocal() as db:
        record = db.get(CreativeDocument, binding["document"])
        user = db.get(User, record.created_by)
        job, _ = create_editing_job(
            db,
            record,
            EditingAIRequestV1(
                expected_document_revision=record.revision,
                operation="generate_video",
                prompt=prompts[label],
                duration_seconds=4,
            ),
            user,
            CORRELATION + "-" + label + "-candidate1",
            adapter="gemini",
            correlation_id=CORRELATION,
            budget_allocations={"planning": 0.2, "image": 0.1, "critique": 0.1, "video": 0.5, "reserve": 0.1},
            budget_policy="res.native-hybrid-pilot.v1",
        )
        if job.status == "queued":
            execute_job_once(db, job)
        receipts(db)
        write(
            label + "-generation.json",
            {"jobId": job.id, "status": job.status, "error": job.error_message, "result": job.result_payload},
        )
        print(label, job.status, job.error_message, flush=True)
        if job.status == "succeeded":
            asset = db.get(LibraryAsset, job.result_payload["assetId"])
            target = OUT / "materials" / (label + "-generated.mp4")
            with get_object_storage().materialize(asset.storage_key) as source:
                shutil.copyfile(source, target)


def generate_music():
    """One bounded source acquisition, with a durable pre-submission reservation."""
    reservation = OUT / "music-reservation.json"
    target = OUT / "materials/aurora-music.mp3"
    if reservation.exists():
        print("music", json.loads(reservation.read_text()).get("status"), flush=True)
        return
    receipts_path = OUT / "cost-receipts.json"
    existing = json.loads(receipts_path.read_text()) if receipts_path.exists() else {"jobs": []}
    committed = sum(
        float(j.get("measuredUsd") if j.get("measuredUsd") is not None else j.get("reservedUsd", 0))
        for j in existing.get("jobs", [])
    )
    if committed + 0.04 > 10:
        raise RuntimeError("pilot_budget_exceeded")
    entry = {
        "provider": "google.gemini-editing",
        "model": "lyria-3-clip-preview",
        "priceVersion": "google-lyria-2026-09-30",
        "reservedUsd": 0.04,
        "status": "submitted_uncertain",
        "prompt": "Instrumental only: warm intimate bossa jazz for a premium Brazilian coffee ritual ad. "
        "Soft brushed drums, upright bass, mellow piano, subtle rhythmic pulse, "
        "gentle lift near the final four seconds. "
        "No voice, no lyrics, no sound effects. Seamless 30 second cue.",
    }
    write(reservation.name, entry)
    try:
        response = GeminiEditingProvider(s.studio_gemini_test_key.get_secret_value()).request(
            "POST", "/interactions", {"model": entry["model"], "input": entry["prompt"], "store": False}
        )
        blocks = [
            part
            for step in response.get("steps", [])
            if step.get("type") == "model_output"
            for part in step.get("content", [])
            if part.get("type") == "audio"
        ]
        audio = response.get("output_audio", {})
        encoded = audio.get("data") or next((part.get("data") for part in blocks if part.get("data")), None)
        if not encoded:
            raise ValueError("music_output_missing")
        target.write_bytes(base64.b64decode(encoded, validate=True))
        from app.services.object_storage import sha256_file

        entry.update(
            status="ready", checksumSha256=sha256_file(target), providerOperationId=response.get("id"), measuredUsd=0.04
        )
    except ValueError as error:
        entry.update(status="submission_uncertain", error=str(error)[:120])
    write(reservation.name, entry)
    print("music", entry["status"], flush=True)


def import_materials(db, workspace, user):
    paths = {
        "beans": OUT / "materials/beans1.mp4",
        "brew": OUT / "materials/brew1.mp4",
        "pour": OUT / "materials/pour0.mp4",
        "wide": OUT / "materials/pour1.mp4",
        "product": ROOT / "public/canonical/figma/phase2/s16-texture.png",
        "beans_alt": OUT / "materials/beans0.mp4",
        "brew_alt": OUT / "materials/brew0.mp4",
        "product_alt": ROOT / "public/canonical/figma/phase2/s16-product.png",
        "product_ritual": ROOT / "public/canonical/figma/phase2/s16-product-ritual.png",
    }
    sound_paths = {"music": "aurora-music.mp3", "pour_sfx": "water-pour.mp3", "cup_sfx": "cup-set-down.mp3"}
    paths.update(
        {label: OUT / "materials" / name for label, name in sound_paths.items() if (OUT / "materials" / name).exists()}
    )
    for label in ("beans", "pour"):
        generated = OUT / "materials" / (label + "-generated.mp4")
        if generated.exists():
            paths[label] = generated
    refs, ids = [], {}
    for label, path in paths.items():
        mime = "image/png" if path.suffix == ".png" else "audio/mpeg" if path.suffix == ".mp3" else "video/mp4"
        key = f"{workspace}/hybrid/{label}{path.suffix}"
        asset = db.scalar(
            select(LibraryAsset).where(LibraryAsset.workspace_id == workspace, LibraryAsset.storage_key == key)
        )
        if asset is None:
            stored = get_object_storage().put_file(path, key=key, media_type=mime)
            asset = LibraryAsset(
                workspace_id=workspace,
                title="Aurora · " + label,
                asset_type="image" if mime.startswith("image") else "audio" if mime.startswith("audio") else "video",
                media_type=mime,
                storage_key=stored.key,
                storage_backend=stored.backend,
                checksum_sha256=stored.checksum_sha256,
                size_bytes=stored.size_bytes,
                object_metadata={
                    "pilot": True,
                    "sourcePath": str(path),
                    "commercialReview": "pending",
                    "materialReview": "directed_reference_only",
                },
            )
            db.add(asset)
            db.flush()
        elif not get_object_storage().exists(key):
            from app.services.object_storage import sha256_file

            if sha256_file(path) != asset.checksum_sha256:
                raise RuntimeError("source_checksum_changed")
            get_object_storage().put_file(path, key=key, media_type=mime)
        ids[label] = asset.id
        if mime.startswith(("video/", "audio/")):
            from app.domain.studios.contracts import CreateMediaIngestRequest
            from app.services.studios.media_ingest import create_media_ingest

            ingest, job, _ = create_media_ingest(
                db,
                CreateMediaIngestRequest(workspace_id=workspace, asset_id=asset.id),
                "native-ingest-" + asset.id,
                user,
            )
            if job.status == "failed":
                from app.services.studios.jobs import retry_job

                retry_job(db, job, user.id)
            if job.status in {"queued", "retrying"}:
                execute_job_once(db, job)
            if job.status != "succeeded":
                raise RuntimeError("ingest: " + str(job.error_message))
        refs.append(
            {
                "id": asset.id,
                "mediaType": mime,
                "checksum": asset.checksum_sha256,
                "rightsStatus": "verified",
                "origin": "uploaded",
            }
        )
    return refs, ids


def reference_direction(ids, variant):
    # Explicit authored reference, kept separate from the planner experiment.
    # Same material set, two editorial rhythms. Values relative to 720x1280 canvas.
    w, h, fps = 720, 1280, 30

    def video_scene(identity, label, seconds, offset=0, rate=1, close=False):
        frames = round(seconds * fps)
        return {
            "id": identity,
            "purpose": "Ação observável: " + label,
            "durationFrames": frames,
            "background": "#17130e",
            "verification": ["A ação avança dentro da imagem; avaliar corte em reprodução."],
            "elements": [
                {
                    "id": "action",
                    "kind": "video",
                    "purpose": "Preparo real em movimento",
                    "assetId": ids[label],
                    "sourceStartSeconds": offset,
                    "playbackRate": rate,
                    "sourceAudio": "mute",
                    "durationFrames": frames,
                    "width": w * (1.14 if close else 1),
                    "height": h * (1.14 if close else 1),
                    "x": -w * 0.07 if close else 0,
                    "y": -h * 0.07 if close else 0,
                    "objectFit": "cover",
                    "cropIntentional": True,
                    "visualRole": "hero",
                }
            ],
            "nativeComponents": [{"component": "action_montage", "version": 1, "targetIds": ["action"]}],
        }

    if variant in {"a", "c", "e", "g"}:
        scenes = [
            video_scene("opening", "beans", 2, 0.3),
            video_scene("preparation", "brew", 1.5, 1),
            video_scene("preparation-detail", "brew", 1.5, 2.5, close=True),
            video_scene("serving", "pour", 3, 0.7),
        ]
    else:
        scenes = [
            video_scene("opening", "beans", 1.2, 0.3),
            video_scene("preparation", "brew", 1.8, 1),
            video_scene("preparation-detail", "brew", 1, 2.8, 1.2, True),
            video_scene("serving", "pour", 2, 0.7),
            video_scene("serving-detail", "pour", 2, 2.7, close=True),
        ]
    for identity, seconds, final in [("reveal", 3, False), ("closing", 4, True)]:
        frames = round(seconds * fps)
        continuous_pour = variant in {"g", "h"}
        continuation_start = 3.7 if variant == "g" else 4.7
        elements = [
            {
                "id": "atmosphere",
                "kind": "video",
                "purpose": "Continuar o ritual ao fundo",
                "assetId": ids["pour"] if continuous_pour else ids["wide"],
                "sourceStartSeconds": (continuation_start + (3 if final else 0))
                if continuous_pour
                else (6 if final else 3),
                "sourceAudio": "mute",
                "durationFrames": frames,
                "width": w,
                "height": h,
                "objectFit": "cover",
                "cropIntentional": True,
                "visualRole": "background",
            },
            {
                "id": "panel",
                "kind": "shape",
                "purpose": "Área de leitura contrastante",
                "durationFrames": frames,
                "x": w * 0.05,
                "y": h * 0.29,
                "width": w * 0.9,
                "height": h * 0.43,
                "fill": "#17130e",
                "depthTreatment": {"opacity": 0.76} if continuous_pour else {"opacity": 1},
                "radius": 0,
            },
            {
                "id": "package",
                "kind": "image",
                "purpose": "Produto do acervo, referência de baixa resolução",
                "assetId": ids["product"],
                "durationFrames": frames,
                "x": w * 0.1,
                "y": h * 0.36,
                "width": w * 0.8,
                "height": h * 0.25,
                "objectFit": "contain",
                "visualRole": "hero",
                "zIndex": 2,
            },
            {
                "id": "name",
                "kind": "text",
                "purpose": "Identificar a marca",
                "text": "CAFÉ AURORA",
                "durationFrames": frames,
                "x": w * 0.13,
                "y": h * 0.30,
                "width": w * 0.74,
                "height": h * 0.055,
                "fontSize": w * 0.046,
                "letterSpacing": 4,
                "color": "#e8c48c",
                "textAlign": "center",
                "visualRole": "text",
            },
            {
                "id": "claim",
                "kind": "text",
                "purpose": "Mensagem final",
                "text": "Seu próximo ritual." if final else "O tempo de um bom café.",
                "durationFrames": frames,
                "x": w * 0.12,
                "y": h * 0.63,
                "width": w * 0.76,
                "height": h * 0.052,
                "fontSize": w * 0.039,
                "color": "#fff3da",
                "textAlign": "center",
                "visualRole": "text",
            },
        ]
        components = [
            {"component": "action_montage", "targetIds": ["atmosphere"], "version": 1},
            {
                "component": "product_demonstration",
                "targetIds": ["package"],
                "version": 1,
                "entranceFrames": 1 if final else 20,
                "continuityKey": "aurora-package",
            },
            {
                "component": "integrated_typography",
                "targetIds": ["name", "claim"],
                "version": 1,
                "entranceFrames": 1 if final else 12,
                "staggerFrames": 0 if final else 2,
            },
        ]
        scenes.append(
            {
                "id": identity,
                "purpose": "Produto e chamada",
                "durationFrames": frames,
                "background": "#17130e",
                "elements": elements,
                "nativeComponents": components,
                "verification": ["Preservar posição da embalagem no corte; leitura confortável."],
            }
        )
    if variant in {"c", "d", "e", "f", "g", "h"}:
        if not {"music", "pour_sfx", "cup_sfx"}.issubset(ids):
            raise RuntimeError("sound_materials_missing")
        cursor = 0
        for scene in scenes:
            frames = scene["durationFrames"]
            scene["audio"] = [
                {
                    "id": "music",
                    "role": "music",
                    "purpose": "Trilha instrumental CC0",
                    "assetId": ids["music"],
                    "durationFrames": frames,
                    "sourceStartSeconds": cursor / fps,
                    "gainDb": -12,
                    "fadeInFrames": 8 if cursor == 0 else 0,
                    "fadeOutFrames": 20 if cursor + frames == 15 * fps else 0,
                }
            ]
            if scene["id"] == "opening":
                scene["audio"].append(
                    {
                        "id": "cup",
                        "role": "effect",
                        "purpose": "Xícara pousada no plano de abertura",
                        "assetId": ids["cup_sfx"],
                        "startFrame": 0,
                        "durationFrames": min(45, frames),
                        "syncElementId": "action",
                        "gainDb": -13,
                        "fadeOutFrames": 6,
                    }
                )
            elif scene["id"] in {"preparation", "preparation-detail", "serving", "serving-detail"}:
                duration = min(50, frames)
                scene["audio"].append(
                    {
                        "id": "pour",
                        "role": "effect",
                        "purpose": "Água ou café vertido em sincronia com a ação",
                        "assetId": ids["pour_sfx"],
                        "startFrame": 0,
                        "durationFrames": duration,
                        "syncElementId": "action",
                        "gainDb": 6 if variant in {"e", "f", "g", "h"} else -7,
                        "fadeOutFrames": min(8, duration // 4),
                    }
                )
            cursor += frames
    return {
        "schemaVersion": "studio.contextual-plan-request.v2",
        "expectedDocumentRevision": 1,
        "intent": {"objective": "Anúncio Café Aurora, 15 segundos, sem locução", "pacing": "balanced"},
        "scenes": scenes,
    }


def render_reference(client, binding, variant):
    from app import tasks

    tasks.execute_studio_generation.delay = lambda *_: None  # explicit local worker below
    doc_binding = OUT / ("reference-" + variant + "-binding.json")
    with SessionLocal() as db:
        if doc_binding.exists():
            saved = json.loads(doc_binding.read_text())
            record = db.get(CreativeDocument, saved["documentId"])
            ids = saved["materialIds"]
            import_materials(db, binding["workspace"], db.get(User, record.created_by))
        else:
            owner = db.get(CreativeDocument, binding["document"])
            refs, ids = import_materials(db, binding["workspace"], db.get(User, owner.created_by))
            record = CreativeDocument(
                workspace_id=binding["workspace"],
                title="Aurora · animatic " + variant.upper(),
                document={},
                created_by=owner.created_by,
            )
            db.add(record)
            db.flush()
            persist_contract(record, base_document(record, refs))
            db.commit()
            write(doc_binding.name, {"documentId": record.id, "materialIds": ids})
        doc_id = record.id
    direction = reference_direction(ids, variant)
    write(
        "reference-" + variant + "-authored.json",
        {
            "authorship": "directed_reference",
            "manualInterventions": [
                "Seleção de material, cortes, enquadramentos e textos pelo agente; "
                "não é execução autônoma do planejador."
            ],
            "direction": direction,
        },
    )
    prefix = f"/api/v1/studios/v1/documents/{doc_id}/editing-plans"
    response = client.post(
        prefix, json=direction, headers={"Idempotency-Key": "native-reference-ingested-sound-v2-" + variant}
    )
    response.raise_for_status()
    plan = response.json()
    write("reference-" + variant + "-plan.json", plan)
    if plan["status"] not in {"ready", "applied"}:
        raise RuntimeError(str(plan["blockers"]))
    if plan["status"] != "applied":
        response = client.post(prefix + "/" + plan["id"] + "/apply", json={"expectedPlanRevision": plan["revision"]})
        response.raise_for_status()
        document = response.json()
    else:
        with SessionLocal() as db:
            document = record_to_contract(db.get(CreativeDocument, doc_id)).model_dump(mode="json", by_alias=True)
    write("reference-" + variant + "-document.json", document)
    response = client.post(
        "/api/v1/studios/v1/video-renders",
        headers={"Idempotency-Key": "native-render-" + variant},
        json={
            "workspaceId": binding["workspace"],
            "documentId": doc_id,
            "expectedDocumentRevision": document["revision"],
            "expectedDocumentVersion": document["version"],
            "contextualPlanId": plan["id"],
            "provider": "remotion.contextual-v2",
            "output": {"width": 720, "height": 1280, "fps": 30, "quality": "draft"},
        },
    )
    response.raise_for_status()
    with SessionLocal() as db:
        job = db.get(StudioGenerationJob, response.json()["id"])
        if job.status in {"queued", "retrying"}:
            execute_job_once(db, job)
        write(
            "reference-" + variant + "-render.json",
            {"status": job.status, "error": job.error_message, "result": job.result_payload},
        )
        print("render", variant, job.status, job.error_message, flush=True)
        if job.status == "succeeded":
            asset = db.get(LibraryAsset, job.result_payload["artifact"]["assetId"])
            with get_object_storage().materialize(asset.storage_key) as source:
                shutil.copyfile(source, OUT / ("animatic-" + variant + ".mp4"))


def verify_component_reuse(client, binding):
    """Exercise one unchanged native component registry across three product briefs."""
    briefs = [
        (
            "kit",
            "Kit Degustação Aurora",
            "Quatro origens. Uma experiência.",
            {"beans": "beans", "brew": "brew", "pour": "pour", "wide": "wide", "product": "product"},
        ),
        (
            "ritual",
            "Ritual de Foco Aurora",
            "Concentre-se no que importa.",
            {"beans": "beans_alt", "brew": "brew_alt", "pour": "wide", "wide": "pour", "product": "product_ritual"},
        ),
        (
            "graos",
            "Café Aurora em Grãos",
            "A pausa começa no preparo.",
            {"beans": "beans", "brew": "brew_alt", "pour": "pour", "wide": "wide", "product": "product_alt"},
        ),
    ]
    results = []
    with SessionLocal() as db:
        owner = db.get(CreativeDocument, binding["document"])
        user = db.get(User, owner.created_by)
        refs, all_ids = import_materials(db, binding["workspace"], user)
        for slug, title, claim, bindings in briefs:
            record = CreativeDocument(
                workspace_id=binding["workspace"], title=title, document={}, created_by=owner.created_by
            )
            db.add(record)
            db.flush()
            document = base_document(record, refs)
            document.title = title
            document.brief.objective = f"Anúncio de {title}, 15 segundos, sem locução"
            persist_contract(record, document)
            db.commit()
            ids = {role: all_ids[label] for role, label in bindings.items()}
            direction = reference_direction(ids, "a")
            direction["intent"]["objective"] = document.brief.objective
            for scene in direction["scenes"]:
                for element in scene["elements"]:
                    if element["id"] == "name":
                        element["text"] = title.upper()
                    if element["id"] == "claim":
                        element["text"] = claim
            response = client.post(
                f"/api/v1/studios/v1/documents/{record.id}/editing-plans",
                json=direction,
                headers={"Idempotency-Key": f"native-reuse-{slug}"},
            )
            response.raise_for_status()
            plan = response.json()
            results.append(
                {
                    "brief": title,
                    "documentId": record.id,
                    "planId": plan["id"],
                    "status": plan["status"],
                    "materialIds": ids,
                    "nativeComponents": sorted(
                        {c["component"] for scene in direction["scenes"] for c in scene["nativeComponents"]}
                    ),
                    "blockers": plan["blockers"],
                }
            )
    write("component-reuse-three-briefs.json", results)
    if any(result["status"] != "ready" for result in results):
        raise RuntimeError("component_reuse_plan_not_ready")


def main():
    client, binding = initialize()
    if len(sys.argv) > 1 and sys.argv[1] == "receipts":
        with SessionLocal() as db:
            receipts(db)
    if len(sys.argv) > 1 and sys.argv[1] == "generate":
        generate(binding, sys.argv[2])
    if len(sys.argv) > 1 and sys.argv[1] == "render":
        render_reference(client, binding, sys.argv[2])
    if len(sys.argv) > 1 and sys.argv[1] == "reuse":
        verify_component_reuse(client, binding)
    if len(sys.argv) > 1 and sys.argv[1] == "plan":
        with SessionLocal() as db:
            record = db.get(CreativeDocument, binding["document"])
            user = db.get(User, record.created_by)
            refs, ids = import_materials(db, binding["workspace"], user)
            doc = record_to_contract(record)
            doc.assets = base_document(record, refs).assets
            persist_contract(record, doc)
            db.commit()
            prompt = (
                "Create a 15s vertical Café Aurora product ad without voiceover. Return nativeComponents version 1: "
                "action_montage targets video, product_demonstration targets image/video/group, "
                "integrated_typography targets text. "
                "Provide >=8s of action inside footage; no slide counters or fixed title block. Text optional. "
                "Use sourceAudio mute: current licensed footage has no sound. "
                "Declare missing sound and a high resolution "
                "real package asset as material needs; supplied product is only a low resolution reference. "
                "Use at most two candidates per need, at most two corrections and US$10 total. "
                "Do not use effects, textSpans or matchPreviousElementId. "
                "Available materials, inspected by the operator: "
                + json.dumps(
                    {
                        "beans": {
                            "id": ids["beans"],
                            "action": "hand moves black cup above scattered beans",
                            "seconds": 5.8,
                        },
                        "brew": {
                            "id": ids["brew"],
                            "action": "kettle pours water into white coffee dripper",
                            "seconds": 10,
                        },
                        "pour": {
                            "id": ids["pour"],
                            "action": "black carafe pours coffee into blue ceramic cup",
                            "seconds": 13.79,
                        },
                        "wide": {
                            "id": ids["wide"],
                            "action": "hand brings glass carafe to ivory cup",
                            "seconds": 14.72,
                        },
                        "product": {"id": ids["product"], "resolution": "474x236", "referenceOnly": True},
                    },
                    ensure_ascii=False,
                )
            )
            request = EditingAIRequestV1(
                expected_document_revision=record.revision,
                operation="plan",
                prompt=prompt,
                plan_version=2,
                direction={
                    "expectedDocumentRevision": record.revision,
                    "intent": {
                        "objective": (
                            "Criar anúncio híbrido Café Aurora, 15 segundos; ritmo, continuidade, clareza e acabamento."
                        ),
                        "script": "Do preparo à primeira xícara. Café Aurora. Seu próximo ritual.",
                        "pacing": "balanced",
                    },
                },
            )
            write("planner-brief.json", request.model_dump(mode="json", by_alias=True))
            job, _ = create_editing_job(
                db,
                record,
                request,
                user,
                CORRELATION + "-planner1",
                compatible=True,
                adapter="compatible",
                correlation_id=CORRELATION,
                budget_allocations={"planning": 0.2, "image": 0.1, "critique": 0.1, "video": 0.5, "reserve": 0.1},
                budget_policy="res.native-hybrid-pilot.v1",
            )
            if job.status == "queued":
                execute_job_once(db, job)
            receipts(db)
            write(
                "planner-result.json", {"status": job.status, "error": job.error_message, "result": job.result_payload}
            )
            print("planner", job.status, job.error_message, flush=True)
    if len(sys.argv) > 1 and sys.argv[1] == "music":
        generate_music()


if __name__ == "__main__":
    main()
