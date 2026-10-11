"""Own directed studies through the real Studio API, no paid providers.

Run prepare, capture the task using capture-visual-distance.mjs, then render.
Receipts contain no tokens. Every editorial intervention is disclosed.
"""

import argparse
import hashlib
import json
import math
import os
import shutil
import struct
import subprocess
import sys
import wave
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from sqlalchemy import select  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.models import LibraryAsset, Membership, StudioGenerationJob, User, Workspace  # noqa: E402
from app.security import create_access_token  # noqa: E402

OUT = ROOT / "output/visual-distance-20261002"
STATE = OUT / "execution.json"
BASE = "http://127.0.0.1:3000/api/v1"
INTERVENTIONS = [
    "Original direction, text, choreography and timing authored by Codex for this directed phase.",
    "Real API documents, plans, jobs and registered Remotion/FFmpeg providers; no autonomous direction claimed.",
    "Original PCM accents and licensed local Manrope; no reference media or client assets.",
]


def identity():
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "motion-study-20261001@example.com"))
        workspace = db.get(Workspace, "4812f2c0-1a2a-4f6d-967d-17b370c8d849")
        if not user or not workspace or workspace.name != "Laboratório Motion 01-10":
            raise ValueError("existing_isolated_study_identity_required")
        member = db.scalar(select(Membership).where(Membership.user_id == user.id, Membership.workspace_id == workspace.id))
        if not member or member.role.lower() not in {"owner", "admin"}:
            raise ValueError("isolated_owner_required")
        return create_access_token(user.id), workspace.id


def api(path, method="GET", body=None, key=None):
    token, _ = identity()
    headers = {"Authorization": "Bearer " + token}
    if isinstance(body, tuple):
        payload, mime = body
        headers["Content-Type"] = mime
    else:
        headers["Content-Type"] = "application/json"
        payload = None if body is None else json.dumps(body, ensure_ascii=False).encode()
    if key:
        headers["Idempotency-Key"] = key
    try:
        with urlopen(Request(BASE + path, data=payload, headers=headers, method=method), timeout=120) as response:
            return json.load(response)
    except HTTPError as error:
        raise ValueError(f"{method} {path} {error.code}: {error.read().decode()}") from error


def save(state):
    OUT.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def upload(path, workspace_id, mime):
    boundary = "res-owned-study-20261002"
    chunks = []
    for key, value in {"workspace_id": workspace_id, "title": path.stem, "tags": "owned,study,visual-distance"}.items():
        chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
    chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{path.name}"\r\nContent-Type: {mime}\r\n\r\n'.encode())
    chunks += [path.read_bytes(), f"\r\n--{boundary}--\r\n".encode()]
    result = api("/assets/upload", "POST", (b"".join(chunks), f"multipart/form-data; boundary={boundary}"))
    return {"id": result["id"], "mediaType": mime, "checksum": hashlib.sha256(path.read_bytes()).hexdigest(),
            "rightsStatus": "unknown", "origin": "user-upload", "provenance": {
                "sourceDeclaration": "Own study or bundled OFL font, no client assets",
                "licenseDeclaration": "Original internal res study / Manrope SIL Open Font License",
            }}


def original_sound():
    path = OUT / "graphic-events.wav"
    with wave.open(str(path), "wb") as output:
        output.setparams((1, 2, 48000, 0, "NONE", "not compressed"))
        samples = bytearray()
        for i in range(720000):
            t = i / 48000
            value = 0
            for at, hz in [(0.2, 160), (3, 220), (8, 330), (11, 440)]:
                dt = t - at
                if 0 <= dt < .8:
                    value += .2 * math.sin(2 * math.pi * hz * dt) * math.exp(-dt * 8) * min(1, dt * 300)
            samples.extend(struct.pack("<h", round(value * 32767)))
        output.writeframes(samples)
    return path


def prepare():
    previous = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else None
    if previous and previous.get("capturePostId"):
        return previous
    _, workspace_id = identity()
    state = previous or {"schemaVersion": "res.visual-distance-execution.v1", "workspaceId": workspace_id,
             "apiSpendUsd": 0, "budgetGroupId": "visual-quality-2026-10-01", "interventions": INTERVENTIONS,
             "visualApproval": "not_assessed", "autonomy": "not_demonstrated", "variants": []}
    save(state)
    font_path = ROOT / "node_modules/@fontsource-variable/manrope/files/manrope-latin-wght-normal.woff2"
    license_path = ROOT / "node_modules/@fontsource-variable/manrope/LICENSE"
    if not license_path.exists() or "OPEN FONT LICENSE" not in license_path.read_text().upper():
        raise ValueError("font_license_evidence_required")
    shutil.copyfile(license_path, OUT / "Manrope-OFL.txt")
    if not state.get("font"):
        state["font"] = upload(font_path, workspace_id, "font/woff2")
        save(state)
    if not state.get("sound"):
        state["sound"] = upload(original_sound(), workspace_id, "audio/wav")
        save(state)
    post = api("/posts", "POST", {"workspaceId": workspace_id, "title": "Tarefa de teste — conteúdo fictício",
        "platform": "instagram", "format": "reels", "status": "draft", "origin": "manual",
        "objective": "Mostrar edição real de texto e consequência no res", "copy": "Rascunho de teste.", "author": "Laboratório res"})
    state["capturePostId"] = post["id"]
    api("/studios/v1/documents", "POST", {"workspaceId": workspace_id, "postId": post["id"],
        "title": post["title"], "contentType": "video", "brandRevision": 1,
        "brief": {"objective": post["objective"], "audience": "Equipe do res"},
        "composition": {"pages": [{"id": "capture-page", "width": 1080, "height": 1920,
            "safeArea": 90, "background": "#101416", "durationMs": 15000, "layers": []}]}})
    save(state)
    return state


def recipe(key, technique, targets, parameters, start=0, end=450):
    return {"id": key, "technique": technique, "version": 1, "targetIds": targets,
        "startFrame": start, "endFrameExclusive": end, "intent": "Transformação dirigida com leitura e consequência",
        "continuityAnchor": "Mesmo texto, identidade, cor e fonte durante a passagem", "parameters": parameters,
        "verification": ["Identidade preservada; estados inicial e final legíveis; sem salto de acomodação"]}


def track(target, prop, values):
    return {"targetId": target, "property": prop, "keyframes": [
        {"frame": frame, "value": value, "curve": [.22, .75, .25, 1]} for frame, value in values]}


def direction(state, study, variant, revision):
    font = state["font"]["id"]
    cream, green, muted = "#efece1", "#c9ed84", "#818f92"
    elements, recipes = [], []

    def el(key, kind, x, y, width, height, **extra):
        value = {"id": key, "kind": kind, "x": x, "y": y, "width": width, "height": height,
                 "startFrame": 0, "durationFrames": 450, "purpose": "Identidade e transformação " + key,
                 "visualRole": "support", "zIndex": 4, **extra}
        elements.append(value)
        return value

    def text(key, value, x, y, width=880, size=64, **extra):
        style = {"text": value, "fontAssetId": font, "fontSize": size, "fontWeight": 700,
                 "lineHeight": 1.1, "color": cream, "fitText": True, "visualRole": "text", **extra}
        return el(key, "text", x, y, width, size * (2.8 if "\n" in value else 1.5),
                  **style)

    labels = ["Ideia", "Plano", "Resultado"]
    title = "Dê direção\nàs suas ideias." if study == "organization" else "Mesmas peças.\nOutra relação."
    if study == "interface":
        title = "Uma mudança.\nUm resultado real."
    text("signature", "res / laboratório de movimento", 90, 165, size=26, color=muted)
    text("title", title, 90, 330, size=88, visualRole="text" if study == "interface" else "hero",
         contentReferenceId="study-content", contentPartId="title")
    text("ending", "Clareza é o resultado.", 90, 1530, size=45, color=green)
    text("disclosure", "ESTUDO PRÓPRIO · REVISÃO HUMANA PENDENTE", 90, 1730, size=21, color=muted)
    if study != "interface":
        for i, value in enumerate(labels):
            initial = [(90, 750), (520, 1030), (130, 1280)][i]
            el("item-" + str(i), "group", *initial, 440, 135)
            el("panel-" + str(i), "shape", 0, 0, 440, 135, parentId="item-" + str(i),
               fill="#1c282b", radius=18, visualRole="background")
            el("dot-" + str(i), "shape", 28, 55, 22, 22, parentId="item-" + str(i), fill=green,
               shape="ellipse", visualRole="accent")
            text("word-" + str(i), value, 74, 38, 340, 48, parentId="item-" + str(i),
                 contentReferenceId="study-content", contentPartId="part-" + str(i))
            dx, dy = (210 + (i * 90 if variant == "b" else 0)) - initial[0], 795 + i * 175 - initial[1]
            if variant != "control":
                begin = 80 + i * (10 if variant == "a" else 25)
                finish = 218 if variant == "a" else 238
                recipes.append(recipe("arrange-" + str(i), "motion_choreography", ["item-" + str(i)], {
                    "pivot": [0, .5], "tracks": [track("item-" + str(i), "x", [(0, 0), (begin, 0),
                        (begin + 12, -14), (finish - 14, dx + 8), (finish, dx), (449, dx)]),
                        track("item-" + str(i), "y", [(0, 0), (begin, 0), (finish - 14, dy + 6), (finish, dy), (449, dy)])]}))
                recipes.append(recipe("rig-" + str(i), "layer_rig", ["panel-" + str(i), "dot-" + str(i), "word-" + str(i)],
                                      {"parentTargetId": "item-" + str(i)}))
            else:
                # Simple states; identical source content, no directed choreography.
                elements[-4]["animations"] = [{"property": prop, "keyframes": [
                    {"frame": 0, "value": 0, "easing": "hold"}, {"frame": 225, "value": delta}, {"frame": 449, "value": delta},
                ]} for prop, delta in [("position_x", dx), ("position_y", dy)]]
        el("connector", "path", 249, 861, 200 if variant == "b" else 30, 440,
           points=[{"x": 0, "y": 0}, {"x": 90 if variant == "b" else 0, "y": 175},
                   {"x": 180 if variant == "b" else 0, "y": 350}],
           color=green, strokeWidth=4)
        if variant != "control":
            recipes.append(recipe("draw-connection", "vector_reveal", ["connector"], {
                "tracks": [track("connector", "stroke_progress", [(0, 0), (190, 0), (245, 1), (449, 1)])]}))
            recipes.append(recipe("title-arrives", "integrated_type", ["title"],
                                  {"textUnit": "word", "staggerFrames": 4, "readingHoldFrames": 120}))
            recipes.append(recipe("ending-arrives", "integrated_type", ["ending"],
                                  {"textUnit": "word", "staggerFrames": 2, "readingHoldFrames": 90}, start=330))
        if study == "comparison":
            el("reveal-group", "group", 0, 0, 1080, 1920)
            el("result", "text", 210, 1390, 710, 85, text="Conectadas, fazem sentido.", fontAssetId=font,
               fontSize=43, fontWeight=600, color=cream, visualRole="support", parentId="reveal-group")
            if variant != "control":
                el("occluder", "shape", -200, 1370, 100, 140, fill="#101416", zIndex=8, parentId="reveal-group")
                recipes.append(recipe("sweep", "motion_choreography", ["occluder"], {
                    "tracks": [track("occluder", "x", [(0, 0), (245, 0), (310, 1400), (449, 1400)])]}))
                recipes.append(recipe("revealed-result", "motivated_occlusion", ["result"],
                                      {"occluderTargetId": "occluder"}, end=450))
            else:
                elements[-1]["animations"] = [{"property": "opacity", "keyframes": [
                    {"frame": 0, "value": 0, "easing": "hold"}, {"frame": 310, "value": 1}, {"frame": 449, "value": 1}]}]
    else:
        cut = 285 if variant != "b" else 276
        asset_id = state["interfaceCrops"]["edit"]["id"]
        first = el("capture", "video", 72, 620, 936, 840, assetId=asset_id, sourceStartSeconds=0,
           playbackRate=1, sourceAudio="mute", objectFit="contain", visualRole="hero",
           contentReferenceId="study-content", contentPartId="primary")
        first["durationFrames"] = cut
        result = el("capture-result", "video", 72 if variant != "b" else 96, 620, 936 if variant != "b" else 888, 840,
           assetId=state["interfaceCrops"]["result"]["id"], sourceStartSeconds=cut/30, playbackRate=1,
           sourceAudio="mute", objectFit="contain", visualRole="hero",
           contentReferenceId="study-content", contentPartId="result-media")
        result.update({"startFrame": cut, "durationFrames": 450-cut})
        text("action-label", "Editar / aplicar / conferir", 90, 1455, size=34, color=muted)
        if variant != "control":
            recipes.append(recipe("type-task", "integrated_type", ["title"],
                                  {"textUnit": "word", "staggerFrames": 5, "readingHoldFrames": 160}))
            recipes.append(recipe("frame-task", "motion_choreography", ["capture"], {
                "tracks": [track("capture", "scale_x", [(0, 1), (90, 1), (cut-1, 1.03 if variant == "a" else .98)]),
                           track("capture", "scale_y", [(0, 1), (90, 1), (cut-1, 1.03 if variant == "a" else .98)])]}, end=cut))
            recipes.append(recipe("interface-consequence", "integrated_type", ["ending"],
                                  {"textUnit": "word", "staggerFrames": 2, "readingHoldFrames": 90}, start=330))
    primary = {"id": "primary", "role": "primary_media", "assetId": state["interfaceCrops"]["edit"]["id"],
               "checksumSha256": state["interfaceCrops"]["edit"]["checksum"]} if study == "interface" else {
                   "id": "part-0", "role": "primary_media", "text": labels[0]}
    parts = [primary, {"id": "title", "role": "title", "text": title}]
    if study == "interface":
        parts += [{"id": "result-media", "role": "body", "assetId": state["interfaceCrops"]["result"]["id"],
                   "checksumSha256": state["interfaceCrops"]["result"]["checksum"]}]
    if study != "interface":
        parts += [{"id": "part-" + str(i), "role": "body", "text": labels[i]} for i in (1, 2)]
    targets = ["capture", "capture-result"] if study == "interface" else ["item-0", "item-1", "item-2"]
    return {"expectedDocumentRevision": revision, "visualStudyLanguage": "interface_capture" if study == "interface" else "motion_graphics",
        "visualStudyVariant": variant,
        "semanticVerificationPolicy": "canonical_demonstration_v1", "executionScope": "audiovisual",
        "intent": {"objective": title.replace("\n", " "), "script": title, "pacing": "balanced", "preserveMessage": True},
        "artDirection": {"visualSystem": "Editorial original: um mundo escuro, informação clara, motivo verde persistente",
            "palette": ["#101416", cream, green], "typography": "Manrope licenciada, palavras inteiras e pausa final",
            "contrastStrategy": "Texto creme sobre fundo escuro; verde marca a consequência",
            "footageTreatment": "Captura de teste real sem inventar ações" if study == "interface" else "Não há filmagem neste estudo gráfico",
            "graphicsRelationship": "Elementos se organizam para explicar a mensagem",
            "continuityRules": ["Preservar texto e identidade", "Movimento local sob grupo explícito"],
            "rejectedStyleMoves": ["Zoom sem consequência", "Dissolve como substituto de oclusão" ]},
        "contentReferences": [{"id": "study-content", "purpose": "Conteúdo próprio reconhecível", "parts": parts}],
        "scenes": [{"id": "study", "purpose": "Estado inicial, transformação e consequência legível", "durationFrames": 450,
            "background": "#101416", "elements": elements, "motionRecipes": recipes,
            "techniqueIds": sorted({"alight." + r["technique"] for r in recipes}),
            "contentReferenceIds": ["study-content"],
            "shotPlan": [{"id": "transform", "function": "demonstrate", "subject": "Conteúdo próprio",
                "observableAction": "Aplicação real de uma edição" if study == "interface" else "Mesmo conjunto passa de dispersão a estrutura legível",
                "shotScale": "interface" if study == "interface" else "graphic", "angle": "not_applicable",
                "regionOfInterest": "Centro e consequência", "attentionStart": "Título e estado inicial", "attentionEnd": "Resultado legível",
                "lighting": {"quality": "graphic", "direction": "not_applicable", "contrast": "high",
                    "temperatureRelationship": "Paleta gráfica própria", "subjectSeparation": "Contraste e espaço",
                    "executionMode": "deterministic_composite"}, "cutMotivation": "A consequência resolve a pergunta inicial",
                "continuity": ["Mesmo objeto/texto durante ação"], "targetElementIds": targets,
                "startFrame": 0, "endFrameExclusive": 450, "verification": ["Compreender a transformação no vídeo completo"]}],
            "semanticAssertions": [{"id": "observable-change", "kind": "visual_action", "objectId": "task" if study == "interface" else "set",
                "initialState": "Antes da aplicação" if study == "interface" else "Conjunto disperso",
                "event": "Editar, aplicar e conferir" if study == "interface" else "Reorganização com identidade constante",
                "finalState": "Resultado real" if study == "interface" else "Estrutura ordenada e conectada",
                "startFrame": 0, "endFrameExclusive": 450, "targetIds": targets, "evidenceRequired": "temporal_sequence"}],
            "audio": [{"id": "original-events", "role": "effect", "purpose": "Pontuação dos estados e da leitura",
                "assetId": state["sound"]["id"], "startFrame": 0, "durationFrames": 450, "gainDb": -6, "fadeOutFrames": 15}],
            "verification": ["Texto inteiro e estado final reconhecível", "Vídeo completo em tamanho de celular",
                             "Contraprova: objetos trocados, título oculto ou movimento sem consequência"]}]}


def create_variant(state, study, variant):
    key = f"{study}-{variant}"
    existing = next((v for v in state["variants"] if v["key"] == key), None)
    if existing:
        return existing
    post = api("/posts", "POST", {"workspaceId": state["workspaceId"], "title": f"Estudo {study} · {variant.upper()} · 15 s",
        "platform": "instagram", "format": "reels", "status": "draft", "origin": "manual",
        "objective": "Qualidade dirigida — " + study, "copy": "Estudo próprio, aprovação humana pendente.", "author": "Laboratório res"})
    state["font"]["rightsStatus"] = "verified"
    state["sound"]["provenance"]["purpose"] = "natural-sound-candidate"
    assets = [state["font"], state["sound"]] + ([state["capture"], *state["interfaceCrops"].values()] if study == "interface" else [])
    document = api("/studios/v1/documents", "POST", {"workspaceId": state["workspaceId"], "postId": post["id"],
        "title": post["title"], "contentType": "video", "brandRevision": 1,
        "brief": {"objective": "Qualidade dirigida — " + study, "audience": "Equipe interna do res", "restrictions": ["Não publicar; estudo sem aprovação humana"]},
        "assets": assets, "composition": {"pages": [{"id": "page", "width": 1080, "height": 1920,
            "safeArea": 90, "background": "#101416", "durationMs": 15000, "layers": []}]}})
    for asset in assets:
        if asset["mediaType"] != "audio/wav":
            continue
        review = api(f"/studios/v1/documents/{document['documentId']}/assets/{asset['id']}/rights-reviews", "POST", {
            "expectedDocumentRevision": document["revision"], "assetChecksumSha256": asset["checksum"], "decision": "verified",
            "basis": "open-license" if asset is state["font"] else "owned", "sourceReference": "scripts/validation/visual-distance-study.py",
            "rightsReference": "Manrope SIL OFL / own original study / own test interface capture", "noExpirationConfirmed": True,
            "notes": "Authorized for internal study; no visual approval asserted"}, key + "-rights-" + asset["id"])
        document = review["document"]
    value = {"key": key, "study": study, "variant": variant, "postId": post["id"], "documentId": document["documentId"],
             "revision": document["revision"], "sourceChecksums": {a["id"]: a["checksum"] for a in assets},
             "url": "http://127.0.0.1:3000/content/" + post["id"] + "/edit?mode=video", "interventions": INTERVENTIONS}
    state["variants"].append(value)
    save(state)
    return value


def render(state, studies):
    from app.services.studios.jobs import execute_job_once
    for study in studies:
        for variant in ("a", "b", "control"):
            value = create_variant(state, study, variant)
            if value.get("status") == "succeeded":
                continue
            base = f"/studios/v1/documents/{value['documentId']}/editing-plans"
            try:
                current = api("/studios/v1/documents/" + value["documentId"])
                if study == "interface":
                    videos = [state["capture"], *state["interfaceCrops"].values()]
                    if {a["id"] for a in current["assets"] if a["mediaType"].startswith("video/")} != {a["id"] for a in videos}:
                        current["assets"] = [a for a in current["assets"] if not a["mediaType"].startswith("video/")] + videos
                        current["composition"]["pages"][0]["layers"] = []
                        current["composition"]["mediaTimeline"]["tracks"] = []
                        current["composition"]["narrative"] = {}
                        current = api("/studios/v1/documents/" + value["documentId"], "PUT", {
                            "expectedRevision": current["revision"], "document": current})
                        value.setdefault("interventions", []).append("Explicit source normalization after audited decode failure; new asset IDs/checksums.")
                value["sourceChecksums"] = {a["id"]: a["checksum"] for a in current["assets"]}
                value["revision"] = current["revision"]
                request = direction(state, study, variant, value["revision"])
                request_digest = hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()[:16]
                plan = api(base, "POST", request, value["key"] + "-plan-" + request_digest)
                (OUT / (value["key"] + "-plan.json")).write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
                if plan["status"] != "ready":
                    raise ValueError("plan_pending:" + json.dumps(plan["blockers"]))
                document = api(base + "/" + plan["id"] + "/apply", "POST", {"expectedPlanRevision": plan["revision"]})
                value["revision"] = document["revision"]
                save(state)
                job = api("/studios/v1/video-renders", "POST", {
                    "workspaceId": state["workspaceId"], "documentId": value["documentId"],
                    "expectedDocumentRevision": document["revision"], "expectedDocumentVersion": document["version"],
                    "contextualPlanId": plan["id"], "provider": "remotion.contextual-v2",
                    "output": {"width": 1080, "height": 1920, "fps": 30}}, value["key"] + "-render-" + plan["id"])
                value.update({"jobId": job["id"], "planId": plan["id"], "status": "rendering", "revision": document["revision"]})
                save(state)
                print(json.dumps({"key": value["key"], "stage": "rendering", "jobId": job["id"]}), flush=True)
                with SessionLocal() as db:
                    record = db.get(StudioGenerationJob, job["id"])
                    execute_job_once(db, record)
                    db.refresh(record)
                    value["status"] = record.status
                    if record.status != "succeeded":
                        raise ValueError("job_failed:" + str(record.error_message))
                    value["result"] = record.result_payload
                    artifact = record.result_payload["artifact"]
                    library = db.get(LibraryAsset, artifact["assetId"])
                    value["metadata"] = library.object_metadata
                    # Fetch through the authenticated API; no storage-path guess.
                    token, _ = identity()
                    with urlopen(Request(BASE + f"/assets/{library.id}/content", headers={"Authorization": "Bearer " + token}), timeout=120) as response:
                        (OUT / (value["key"] + ".mp4")).write_bytes(response.read())
                value["visualApproval"] = "not_assessed"
                if value.get("error"):
                    value.setdefault("auditedErrors", []).append(value.pop("error"))
                save(state)
                print(json.dumps({"key": value["key"], "status": value["status"], "artifact": artifact}), flush=True)
            except Exception as error:
                value["error"] = str(error)
                save(state)
                raise


def probe(state, asset, key):
    from app.services.studios.jobs import execute_job_once

    ingest = api("/studios/v1/media-ingests", "POST", {"workspaceId": state["workspaceId"], "assetId": asset["id"]},
                 "visual-distance-probe-" + key + "-" + asset["id"])
    with SessionLocal() as db:
        job = db.get(StudioGenerationJob, ingest["generationJobId"])
        execute_job_once(db, job)
        db.refresh(job)
        if job.status != "succeeded":
            raise ValueError("probe_failed:" + str(job.error_message))
    return ingest


def prepare_capture_source(state):
    if state.get("captureSourceReady"):
        return
    from PIL import Image, ImageDraw

    graphic = Image.new("RGB", (1080, 1920), "#101416")
    canvas = ImageDraw.Draw(graphic)
    for i in range(3):
        canvas.rounded_rectangle((160, 660+i*200, 920, 800+i*200), radius=24, fill="#1c282b")
        canvas.ellipse((195, 709+i*200, 235, 749+i*200), fill="#c9ed84")
    canvas.text((160, 480), "RES / TESTE DE INTERFACE", fill="#efece1", font_size=48)
    canvas.text((280, 710), "Ideia", fill="#efece1", font_size=48)
    canvas.text((280, 910), "Plano", fill="#efece1", font_size=48)
    canvas.text((280, 1110), "Resultado", fill="#efece1", font_size=48)
    image = OUT / "capture-source.png"
    graphic.save(image)
    video = OUT / "capture-source.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-i", str(image), "-t", "15",
                    "-r", "30", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(video)], check=True)
    asset = upload(video, state["workspaceId"], "video/mp4")
    asset["rightsStatus"] = "verified"
    probe(state, asset, "interface-source")
    docs = api("/studios/v1/documents?workspace_id=" + state["workspaceId"] + "&post_id=" + state["capturePostId"])
    document = docs[0]
    document["assets"] = [asset]
    document["composition"]["narrative"] = {"sourceAssetId": asset["id"]}
    document["composition"]["mediaTimeline"] = {"durationFrames": 450, "frameRate": {"numerator": 30, "denominator": 1},
        "tracks": [{"id": "test-video", "kind": "video", "name": "Take próprio de teste", "clips": [{
            "id": "test-take", "assetId": asset["id"], "timeline": {"startFrame": 0, "durationFrames": 450},
            "source": {"startMicroseconds": 0, "durationMicroseconds": 15000000}, "enabled": True,
            "label": "Conteúdo fictício próprio", "playbackRate": 1, "transform": {"fit": "contain", "anchor": "center"}}]}]}
    updated = api("/studios/v1/documents/" + document["documentId"], "PUT", {
        "expectedRevision": document["revision"], "document": document})
    state["captureSourceReady"] = True
    state["captureSource"] = asset
    state["captureSourceRevision"] = updated["revision"]
    save(state)


def compare(state, studies):
    for study in studies:
        variants = [v for v in state["variants"] if v["study"] == study and v.get("status") == "succeeded"]
        if len(variants) != 3:
            raise ValueError("three_successful_variants_required:" + study)
        existing = state.setdefault("comparisons", {}).get(study)
        if existing:
            continue
        request = {"variants": [{"documentId": v["documentId"], "documentRevision": v["revision"],
            "assetId": v["result"]["artifact"]["assetId"], "checksum": v["result"]["artifact"]["checksumSha256"]} for v in variants]}
        session = api(f"/studios/v1/workspaces/{state['workspaceId']}/visual-study-comparisons", "POST", request)
        state["comparisons"][study] = session
        save(state)
    program = api(f"/studios/v1/workspaces/{state['workspaceId']}/visual-quality")
    (OUT / "quality-program.json").write_text(json.dumps(program, ensure_ascii=False, indent=2), encoding="utf-8")


def register_capture(state, captured):
    if captured["evidence"][0]["text"] == next(e["text"] for e in captured["evidence"] if e["stage"] == "after"):
        raise ValueError("capture_different_states_required")
    state["captureEvidence"] = captured
    checksum = hashlib.sha256(Path(captured["path"]).read_bytes()).hexdigest()
    asset = state.get("capture") if (state.get("capture") or {}).get("checksum") == checksum else None
    asset = asset or upload(Path(captured["path"]), state["workspaceId"], "video/mp4")
    asset["provenance"].update({"testEnvironmentCapture": True,
        "observableAction": "Texto fictício alterado e aplicado à timeline real do res",
        "sourceIntervals": captured.get("sourceIntervals"),
        "editorialIntervention": captured.get("editorialIntervention", "Startup trim")})
    asset["rightsStatus"] = "verified"
    state["capture"] = asset
    save(state)
    probe(state, asset, "real-interface-capture-" + asset["checksum"][:12])
    # Explicit editorial crops preserve actual pixels and the source time.
    state["interfaceCrops"] = {}
    for name, crop in {"edit": "300:300:978:342", "result": "244:220:475:350"}.items():
        destination = OUT / ("interface-" + name + ".mp4")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", captured["path"], "-vf", "crop=" + crop + ",fps=30",
                        "-an", "-c:v", "libx264", "-g", "1", "-bf", "0", "-crf", "18",
                        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(destination)], check=True)
        cropped = upload(destination, state["workspaceId"], "video/mp4")
        cropped["rightsStatus"] = "verified"
        cropped["provenance"].update(asset["provenance"])
        cropped["provenance"].update({"parentAssetId": asset["id"], "parentChecksum": asset["checksum"],
                                      "cropPixels": crop, "sourceTimeUnchanged": True,
                                      "encodingProfile": "h264_cfr30_all_intra_no_b_frames",
                                      "reason": "Explicit compatibility experiment after audited OffthreadVideo decode failure"})
        state["interfaceCrops"][name] = cropped
        probe(state, cropped, "interface-crop-" + name + "-" + asset["checksum"][:12])
    save(state)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["prepare", "capture", "render", "compare", "materials"])
    parser.add_argument("--studies", nargs="+", default=["organization", "comparison", "interface"])
    args = parser.parse_args()
    state = prepare()
    if args.mode == "capture":
        prepare_capture_source(state)
        # Previous failed recordings may have saved captions. Reset only this
        # isolated task so a new recording has genuinely different states.
        docs = api("/studios/v1/documents?workspace_id=" + state["workspaceId"] + "&post_id=" + state["capturePostId"])
        document = docs[0]
        timeline = document["composition"]["mediaTimeline"]
        timeline["tracks"] = [t for t in timeline["tracks"] if t["kind"] != "caption"]
        api("/studios/v1/documents/" + document["documentId"], "PUT", {"expectedRevision": document["revision"], "document": document})
        if state.get("capture"):
            state.setdefault("supersededCaptures", []).append({"asset": state["capture"],
                "evidence": state.get("captureEvidence"),
                "reason": "Re-recording isolated task for readable action; previous capture retained, rejection details in attempt logs"})
        save(state)
        token, workspace_id = identity()
        capture = subprocess.run(["node", str(ROOT / "scripts/validation/capture-visual-distance.mjs")],
            input=json.dumps({"token": token, "workspaceId": workspace_id, "postId": state["capturePostId"], "out": str(OUT),
                              "origin": os.environ.get("VISUAL_STUDY_UI_ORIGIN", "http://127.0.0.1:3000")}),
            text=True, capture_output=True)
        if capture.returncode:
            (OUT / "capture-error.log").write_text(capture.stderr, encoding="utf-8")
            raise ValueError("capture_failed:" + capture.stderr[-3000:])
        captured = json.loads(capture.stdout.strip().splitlines()[-1])
        register_capture(state, captured)
    elif args.mode == "materials":
        captured = json.loads((OUT / "interface-capture-evidence.json").read_text(encoding="utf-8"))
        captured["path"] = captured["output"]
        register_capture(state, captured)
    elif args.mode == "render":
        render(state, args.studies)
    elif args.mode == "compare":
        compare(state, args.studies)
    print(json.dumps({"state": str(STATE), "variants": len(state["variants"]), "apiSpendUsd": 0}), flush=True)


if __name__ == "__main__":
    main()
