"""Draft-first editing orchestration over the existing document/event/job stores."""

from __future__ import annotations

import math
import re
import unicodedata
from contextlib import ExitStack
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select, text

from ...config import get_settings
from ...domain.studios.contextual_editing import (
    CONTEXTUAL_PROVIDER,
    ContextualEditPlanV1,
    ContextualOperationV1,
    ContextualPlanRequestV1,
    EditingAlternativeV1,
    EditingBeatV1,
    EditingBlockerV1,
    digest,
)
from ...domain.studios.contextual_editing_v2 import ContextualEditPlanV2, parse_editing_plan
from ...domain.studios.contracts import (
    AssetReferenceV1,
    AudioClipV1,
    AudioTrackV1,
    CaptionCueV1,
    CaptionTrackV1,
    MaskTrackV1,
    MediaClipV1,
    OverlayTrackV1,
    ReviewReferenceV1,
    SourceTimeRangeV1,
)
from ...models import LibraryAsset, StudioDomainEvent, StudioGenerationJob, StudioMediaIngest, Workspace
from ...providers.studios.contextual_render import CAPABILITIES, inspect_document, used_capabilities
from ...providers.studios.media_probe import MEDIA_PROBE_PROVIDERS
from ..object_storage import get_object_storage
from .asset_rights import project_governed_audio_rights
from .compatibility import persist_contract, record_to_contract
from .contextual_assembly import (
    assemble,
    bound_transcript,
    decision_markers,
    transcript_captions,
    validate_transcript_bindings,
)
from .editing_repertoire import contextual_references, ensure_repertoire, search_repertoire
from .kernel import emit_event
from .review_binding import invalidate_linked_post_review

PLAN_EVENT = "studio.editing.plan"


def _events(db, workspace_id, event_type, aggregate_id=None):
    query = select(StudioDomainEvent).where(
        StudioDomainEvent.workspace_id == workspace_id, StudioDomainEvent.event_type == event_type
    )
    if aggregate_id:
        query = query.where(StudioDomainEvent.aggregate_id == aggregate_id)
    return list(db.scalars(query.order_by(StudioDomainEvent.occurred_at, StudioDomainEvent.id)).all())


def get_plan(db, workspace_id, plan_id):
    events = _events(db, workspace_id, PLAN_EVENT, plan_id)
    if not events:
        raise ValueError("editing_plan_not_found")
    plans = [parse_editing_plan(e.payload["plan"]) for e in events]
    return max(reversed(plans), key=lambda p: p.revision)


def latest_plan(db, document):
    events = [
        e
        for e in _events(db, document.workspace_id, PLAN_EVENT)
        if e.payload.get("plan", {}).get("documentId") == document.id
    ]
    if not events:
        return None
    # `_events` is ordered by the persisted event timestamp and id.  Using the
    # plan's client-shaped `createdAt` plus revision caused different plans
    # created in the same clock tick to tie, allowing an older sibling to be
    # returned.  The last persisted event is the actual latest projection.
    newest = events[-1]
    return parse_editing_plan(newest.payload["plan"])


def _save(db, document, plan, user, extra=None):
    emit_event(
        db,
        workspace_id=document.workspace_id,
        event_type=PLAN_EVENT,
        aggregate_type="editing_plan",
        aggregate_id=plan.id,
        correlation_id=f"editing:{plan.id}",
        actor_id=user.id if user else None,
        payload={"plan": plan.model_dump(mode="json", by_alias=True), **(extra or {})},
    )
    db.flush()


def _block(target, code, message, *, optional=False):
    alternatives = [
        EditingAlternativeV1(
            id="wait",
            label="Aguardar e ajustar os materiais",
            impact="O vídeo permanece sem renderização até resolver este impedimento.",
            action="wait",
        )
    ]
    if optional:
        alternatives.insert(
            0,
            EditingAlternativeV1(
                id="omit",
                label="Continuar sem este recurso",
                impact="A mensagem original é preservada; este complemento não será aplicado.",
                action="omit_optional",
            ),
        )
    return EditingBlockerV1(
        id=f"block-{digest([target, code])[:16]}",
        target_id=target,
        code=code,
        message=message,
        alternatives=alternatives,
    )


def _source_digest(document):
    # UI-only review state and timestamps do not change the media snapshot.
    return digest(
        {
            "documentId": document.document_id,
            "revision": document.revision,
            "version": document.version,
            "composition": document.composition.model_dump(mode="json"),
            "assets": [a.model_dump(mode="json") for a in document.assets],
            "brief": document.brief.model_dump(mode="json"),
        }
    )


def asset_blockers(db, document):
    projected = project_governed_audio_rights(db, document)
    refs = {a.id: a for a in projected.assets}
    timeline = document.composition.media_timeline
    used = (
        {
            c.asset_id
            for t in timeline.tracks
            for c in getattr(t, "clips", [])
            if c.enabled and not (t.kind == "audio" and t.muted)
        }
        if timeline
        else set()
    )
    if timeline:
        used.update(t.artifact_asset_id for t in timeline.tracks if t.kind == "mask")
        used.update(
            cue.style.font_asset_id
            for t in timeline.tracks
            if t.kind == "caption"
            for cue in t.cues
            if cue.style.font_asset_id
        )
    used.update(
        layer.properties["fontAssetId"]
        for page in document.composition.pages
        for layer in page.layers
        if layer.visible and layer.kind == "text" and layer.properties.get("fontAssetId")
    )
    used.update(
        layer.properties[field]
        for page in document.composition.pages
        for layer in page.layers
        for field in ("assetId", "maskAssetId")
        if layer.visible and layer.properties.get(field)
    )
    blockers = []
    for asset_id in sorted(used):
        ref = refs.get(asset_id)
        asset = db.scalar(
            select(LibraryAsset).where(
                LibraryAsset.id == asset_id,
                LibraryAsset.workspace_id == document.workspace_id,
                LibraryAsset.lifecycle_status == "active",
            )
        )
        if not asset or not asset.storage_key or not asset.checksum_sha256 or not ref:
            blockers.append(
                _block(asset_id, "asset_missing", "O material precisa estar disponível na biblioteca deste projeto.")
            )
            continue
        if (
            not ref.checksum
            or ref.checksum.lower() != asset.checksum_sha256.lower()
            or ref.media_type != asset.media_type
        ):
            blockers.append(
                _block(asset_id, "asset_binding_changed", "O material mudou; atualize sua referência antes de editar.")
            )
            continue
        if ref.rights_status == "restricted":
            blockers.append(_block(asset_id, "asset_rights_restricted", "Este material tem restrição de uso."))
        elif ref.provenance.get("purpose") in {"natural-sound-candidate", "licensed-music-candidate"}:
            if ref.rights_status != "verified":
                blockers.append(
                    _block(
                        asset_id, "audio_rights_required", "Confirme os direitos deste áudio na revisão de materiais."
                    )
                )
        else:
            ingest = db.scalar(
                select(StudioMediaIngest).where(
                    StudioMediaIngest.workspace_id == document.workspace_id,
                    StudioMediaIngest.asset_id == asset_id,
                    StudioMediaIngest.status == "ready",
                )
            )
            # Derivations need their established generation/consent workflow, not a forged upload claim.
            derived = (asset.object_metadata or {}).get("derivation")
            admitted = (
                generated_asset_admitted(db, asset)
                if derived
                else (
                    bool(ingest)
                    or ref.media_type.startswith(("image/", "font/"))
                    or bool((asset.object_metadata or {}).get("editingResource", {}).get("technical", {}).get("probe"))
                )
            )
            if not admitted:
                blockers.append(
                    _block(
                        asset_id,
                        "source_admission_required",
                        "O material precisa de ingestão validada; conteúdo gerado mantém seu fluxo de origem.",
                    )
                )
    return blockers


def generated_asset_admitted(db, asset, visited=None):
    """Reuse generated media without relabelling it as a user upload."""
    visited = set(visited or ())
    if asset.id in visited or len(visited) >= 20:
        return False
    visited.add(asset.id)
    metadata = asset.object_metadata or {}
    job = db.get(StudioGenerationJob, metadata.get("generationJobId")) if metadata.get("generationJobId") else None
    if not job or job.workspace_id != asset.workspace_id or job.status != "succeeded":
        return False
    result = job.result_payload or {}
    artifact = result.get("artifact") or result
    if artifact.get("assetId") != asset.id or artifact.get("checksumSha256") != asset.checksum_sha256:
        return False
    from .jobs import require_avatar_video_binding, require_voice_clone_binding

    try:
        if job.job_type == "avatar_video":
            require_avatar_video_binding(
                db,
                workspace_id=job.workspace_id,
                document_id=job.document_id,
                identity_version_id=job.identity_version_id,
                voice_version_id=job.voice_version_id,
                consent_grant_id=job.consent_grant_id,
            )
        elif job.job_type == "voice_clone":
            require_voice_clone_binding(
                db,
                workspace_id=job.workspace_id,
                voice_version_id=job.voice_version_id,
                consent_grant_id=job.consent_grant_id,
            )
        elif job.job_type == "video_render":
            bindings = metadata.get("sourceAssetBindings", [])
            if not bindings:
                return False
            for binding in bindings:
                source = db.get(LibraryAsset, binding.get("assetId"))
                if (
                    not source
                    or source.workspace_id != asset.workspace_id
                    or source.lifecycle_status != "active"
                    or source.checksum_sha256 != binding.get("checksumSha256")
                ):
                    return False
                if (source.object_metadata or {}).get("derivation") and not generated_asset_admitted(
                    db, source, visited
                ):
                    return False
            from ...domain.studios.contracts import CreativeDocumentV1

            snapshot = CreativeDocumentV1.model_validate(job.request_payload["documentSnapshot"])
            rights = project_governed_audio_rights(db, snapshot)
            if any(
                a.provenance.get("purpose") in {"natural-sound-candidate", "licensed-music-candidate"}
                and a.rights_status != "verified"
                for a in rights.assets
            ):
                return False
        elif job.job_type in {"editing_gemini", "editing_ai"}:
            if metadata.get("visualReview") != "passed":
                return False
            for source_id, checksum in metadata.get("sourceAssetBindings", {}).items():
                source = db.get(LibraryAsset, source_id)
                if (
                    not source
                    or source.workspace_id != asset.workspace_id
                    or source.checksum_sha256 != checksum
                    or source.lifecycle_status != "active"
                ):
                    return False
                if (source.object_metadata or {}).get("derivation") and not generated_asset_admitted(
                    db, source, visited
                ):
                    return False
        elif job.job_type != "stock_voice":
            return False
    except (ValueError, KeyError):
        return False
    return True


def estimate_cost(document):
    settings = get_settings()
    timeline = document.composition.media_timeline
    if not timeline:
        return 0
    seconds = timeline.duration_frames * timeline.frame_rate.denominator / timeline.frame_rate.numerator
    simultaneous_work = sum(len(getattr(t, "clips", [])) for t in timeline.tracks)
    page = document.composition.pages[0]
    complexity = max(1, simultaneous_work / 8) * max(1, page.width * page.height / (1280 * 720))
    return max(1, math.ceil(seconds / 60 * complexity * settings.studio_editing_estimated_cents_per_minute))


def reduced_resolution(document):
    draft = document.model_copy(deep=True)
    page = draft.composition.pages[0]
    factor = min(1, max(720 / max(page.width, page.height), 320 / min(page.width, page.height)))
    width, height = max(320, 2 * round(page.width * factor / 2)), max(320, 2 * round(page.height * factor / 2))
    sx, sy = width / page.width, height / page.height
    page.width, page.height = width, height
    page.safe_area = round(page.safe_area * min(sx, sy))
    for layer in page.layers:
        layer.x *= sx
        layer.y *= sy
        layer.width *= sx
        layer.height *= sy
        for key in ["fontSize", "minFontSize"]:
            if key in layer.properties:
                layer.properties[key] = max(16 if key == "fontSize" else 8, round(layer.properties[key] * min(sx, sy)))
    for track in draft.composition.media_timeline.tracks:
        for clip in getattr(track, "clips", []):
            for key, ratio in [("x", sx), ("y", sy), ("width", sx), ("height", sy)]:
                if key in clip.transform:
                    clip.transform[key] = round(clip.transform[key] * ratio)
            for motion in clip.keyframes:
                ratio = sx if motion.get("property") == "position_x" else sy
                for frame in motion.get("keyframes", []):
                    frame["value"] *= ratio
        if track.kind == "caption":
            for cue in track.cues:
                cue.style.font_size = max(16, round(cue.style.font_size * min(sx, sy)))
    return draft


def budget_remaining(db, workspace_id):
    settings = get_settings()
    if settings.environment == "production":
        return math.inf
    month = datetime.now(UTC).strftime("%Y-%m")
    # The configured R$500 envelope belongs to the deployment, not to each tenant.
    reservations = db.scalars(
        select(StudioDomainEvent).where(StudioDomainEvent.event_type == "studio.editing.cost_reserved")
    ).all()
    used = sum(e.payload["costCents"] for e in reservations if e.payload.get("month") == month)
    return max(
        0, settings.studio_editing_monthly_budget_cents - settings.studio_editing_infrastructure_reserve_cents - used
    )


def lock_editing_budget(db, workspace_id):
    if db.bind.dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(740216510)"))
    elif db.bind.dialect.name == "sqlite":
        # Acquire SQLite's write lock before reading the global reservation ledger.
        db.execute(text("UPDATE workspaces SET id = id WHERE id = :workspace_id"), {"workspace_id": workspace_id})
    else:
        raise ValueError("editing_budget_database_unsupported")


def preflight(db, document, executed_capabilities=None):
    audible_asset_ids = set()
    problems = [
        _block(
            target,
            code,
            "Esta operação ainda não pode ser executada neste material.",
            optional=target.startswith(("support-", "editorial-")),
        )
        for target, code in inspect_document(document)
    ]
    material_problems = asset_blockers(db, document)
    problems.extend(material_problems)
    if not material_problems and document.composition.media_timeline:
        timeline = document.composition.media_timeline
        fps = timeline.frame_rate.numerator / timeline.frame_rate.denominator
        refs = {a.id: a for a in document.assets}
        probes = {}
        with ExitStack() as stack:
            for track in timeline.tracks:
                for clip in getattr(track, "clips", []):
                    if not clip.enabled or (track.kind == "audio" and track.muted):
                        continue
                    if refs[clip.asset_id].media_type.startswith("image/"):
                        continue
                    if clip.asset_id not in probes:
                        asset = db.get(LibraryAsset, clip.asset_id)
                        try:
                            path = stack.enter_context(
                                get_object_storage(asset.storage_backend or "local").materialize(asset.storage_key)
                            )
                            probes[clip.asset_id] = MEDIA_PROBE_PROVIDERS["builtin.ffprobe"].probe(
                                path, asset_id=asset.id, checksum_sha256=asset.checksum_sha256
                            )
                        except (ValueError, OSError):
                            problems.append(
                                _block(clip.id, "source_probe_failed", "Não foi possível ler este material.")
                            )
                            continue
                    probe = probes[clip.asset_id]
                    if probe.audio_streams:
                        audible_asset_ids.add(clip.asset_id)
                    start = (clip.source.start_microseconds if clip.source else 0) / 1e6
                    length = (
                        1 / fps
                        if any(e.get("kind") == "freeze" for e in clip.effects)
                        else clip.timeline.duration_frames / fps * clip.playback_rate
                    )
                    if start + length > probe.duration_microseconds / 1e6 + 1 / fps:
                        problems.append(
                            _block(
                                clip.id,
                                "source_out_of_bounds",
                                "O trecho solicitado é maior que o material disponível.",
                                optional=clip.id.startswith("support-"),
                            )
                        )
                    if track.kind == "audio" and not probe.audio_streams:
                        problems.append(_block(clip.id, "audio_stream_missing", "Este material não contém áudio."))
    from ...providers.studios.video_render import VIDEO_RENDER_PROVIDERS

    renderer = VIDEO_RENDER_PROVIDERS[CONTEXTUAL_PROVIDER]
    if not renderer.capabilities()["available"]:
        problems.append(_block("renderer", "renderer_unavailable", "O renderizador local não está disponível."))
    else:
        try:
            with ExitStack() as font_stack:
                font_paths = {}
                for ref in document.assets:
                    if ref.media_type.startswith("font/"):
                        asset = db.get(LibraryAsset, ref.id)
                        if not asset or asset.workspace_id != document.workspace_id or not asset.storage_key:
                            raise ValueError("editing_font_asset_missing")
                        font_paths[ref.id] = font_stack.enter_context(
                            get_object_storage(asset.storage_backend).materialize(asset.storage_key)
                        )
                renderer.validate_text(document, font_paths)
        except ValueError as error:
            problems.append(_block("text", str(error), "O texto não cabe de forma legível; ajuste texto ou estilo."))
    cost = estimate_cost(document)
    if cost > budget_remaining(db, document.workspace_id):
        problems.append(
            _block(
                "budget",
                "budget_exceeded",
                "Esta edição ultrapassa o saldo reservado para o mês. Reduza a composição ou aguarde saldo.",
            )
        )
        smaller = reduced_resolution(document)
        if estimate_cost(smaller) < cost and estimate_cost(smaller) <= budget_remaining(db, document.workspace_id):
            page = smaller.composition.pages[0]
            problems[-1].alternatives.insert(
                0,
                EditingAlternativeV1(
                    id="reduce-resolution",
                    label=f"Gerar em {page.width} × {page.height}",
                    impact="Menor resolução; cenas, mensagem e duração preservadas.",
                    action="reduce_resolution",
                ),
            )
    if executed_capabilities is not None:
        try:
            executed_capabilities.update(used_capabilities(document, audible_asset_ids))
        except (ValueError, KeyError):
            # Invalid operations are already represented by preflight blockers.
            pass
    return problems, cost


def create_plan(db, document, request: ContextualPlanRequestV1, user, key):
    db.refresh(document, with_for_update=True)
    request_hash = digest({"documentId": document.id, "request": request.model_dump(mode="json")})
    for event in _events(db, document.workspace_id, PLAN_EVENT):
        if event.payload.get("idempotencyKey") == key:
            if event.payload.get("requestHash") != request_hash:
                raise ValueError("editing_idempotency_conflict")
            return get_plan(db, document.workspace_id, event.aggregate_id)
    if document.revision != request.expected_document_revision:
        raise ValueError("studio_document_conflict")
    source = record_to_contract(document)
    if request.intent.emphasis == "auto":
        # Conservative, inspectable editorial routing; unrecognised briefs retain their footage.
        words = unicodedata.normalize("NFKD", request.intent.objective.casefold())
        words = "".join(c for c in words if not unicodedata.combining(c))
        emphasis = "message"
        if not re.search(r"\b(nao|evitar|sem)\b", words):
            if re.search(r"\b(demonstrar|demonstracao|tutorial|mostrar|detalhe|produto)\b", words):
                emphasis = "demonstration"
            elif re.search(r"\b(ambiente|atmosfera|contemplar|paisagem)\b", words):
                emphasis = "atmosphere"
        request = request.model_copy(update={"intent": request.intent.model_copy(update={"emphasis": emphasis})})
    if source.content_type != "video" or not source.composition.media_timeline:
        raise ValueError("editing_video_timeline_required")
    # The deterministic planner never writes new dialogue or cuts inside a spoken sentence.
    # Timeline order is authoritative; every original clip remains present.
    draft = source.model_copy(deep=True)
    timeline = draft.composition.media_timeline
    # Replanning replaces only layers generated by this planner, never the customer's layers.
    # Generated IDs are retrieved from the server-owned previous plan, not guessed by prefix.
    previous_id = source.composition.narrative.get("contextualPlanId")
    if previous_id:
        previous = get_plan(db, document.workspace_id, previous_id)
        if previous.document_id != document.id:
            raise ValueError("editing_plan_document_mismatch")
        generated_ids = {
            o.target_id
            for o in previous.operations
            if o.kind in {"insert_broll", "insert_audio", "add_caption", "omit_text", "omit_optional"}
        }
        for track in timeline.tracks:
            if hasattr(track, "clips"):
                track.clips = [c for c in track.clips if c.id not in generated_ids]
            if track.kind == "caption":
                track.cues = [c for c in track.cues if c.id not in generated_ids]
        removed_track_ids = {
            t.id
            for t in timeline.tracks
            if t.kind in {"overlay", "caption", "audio"} and not getattr(t, "clips", getattr(t, "cues", []))
        }
        timeline.tracks = [
            t
            for t in timeline.tracks
            if t.id not in removed_track_ids and not (t.kind == "mask" and t.target_track_id in removed_track_ids)
        ]
    clips = {c.id: c for t in timeline.tracks if t.kind == "video" for c in t.clips if c.enabled}
    directed_clips = {b.clip_id for b in request.beats}
    beats = [
        *request.beats,
        *[
            EditingBeatV1(id=c.id, clip_id=c.id, purpose=c.label or request.intent.objective)
            for c in clips.values()
            if c.id not in directed_clips
        ],
    ]
    if any(b.clip_id not in clips for b in beats):
        raise ValueError("editing_beat_clip_not_found")
    operations, blockers = [], []
    from .material_director import resolve_material_needs

    material_requests, material_blockers = resolve_material_needs(
        db, document.workspace_id, document.id, request, beats, user.id
    )
    blockers.extend(material_blockers)
    from .editing_resources import catalog

    for beat in beats:
        if beat.support_query and not beat.support_asset_id:
            matches = [
                m
                for m in catalog(db, document.workspace_id, beat.support_query)
                if m["mediaType"].startswith(("image/", "video/"))
            ]
            if len(matches) == 1:
                beat.support_asset_id = matches[0]["id"]
            else:
                blockers.append(
                    _block(
                        beat.id,
                        "resource_choice_required" if matches else "resource_missing",
                        "Escolha o apoio visual no acervo." if matches else f"Adicionar material: {beat.support_query}",
                    )
                )
        for asset_id in [beat.support_asset_id, beat.mask_asset_id, beat.audio_asset_id, request.font_asset_id]:
            if not asset_id or any(a.id == asset_id for a in draft.assets):
                continue
            asset = db.scalar(
                select(LibraryAsset).where(
                    LibraryAsset.id == asset_id,
                    LibraryAsset.workspace_id == document.workspace_id,
                    LibraryAsset.lifecycle_status == "active",
                )
            )
            metadata = (asset.object_metadata or {}) if asset else {}
            if asset and asset.storage_key and metadata.get("editingResource", {}).get("usageEvidence"):
                draft.assets.append(
                    AssetReferenceV1(
                        id=asset.id,
                        checksum=asset.checksum_sha256,
                        version=asset.checksum_sha256,
                        media_type=asset.media_type,
                        rights_status="verified",
                        origin="generated" if metadata.get("derivation") else "workspace",
                        provenance=metadata,
                    )
                )
    source_transcripts, transcripts, assembly_trace = {}, {}, []
    for beat in beats:
        if beat.mask_asset_id and not beat.support_asset_id:
            blockers.append(
                _block(
                    beat.id,
                    "mask_support_required",
                    "A máscara precisa de um material de apoio associado à cena.",
                    optional=True,
                )
            )
        if not beat.transcript_id:
            continue
        try:
            transcript, binding = bound_transcript(db, source, beat, clips[beat.clip_id])
            transcripts[beat.clip_id] = transcript
            source_transcripts[beat.transcript_id] = binding
        except ValueError as error:
            blockers.append(
                _block(
                    beat.id, str(error), "A transcrição não corresponde à versão deste material. Atualize a referência."
                )
            )
    try:
        assembled, assembly_trace = assemble(draft, beats, transcripts, request.clip_order)
        candidate = draft.model_copy(deep=True)
        candidate.composition.media_timeline = assembled
        candidate_clips = {c.id: c for t in assembled.tracks if t.kind == "video" for c in t.clips if c.enabled}
        markers = decision_markers(candidate, beats, candidate_clips)
        if markers:
            if any(t.id == markers.id for t in assembled.tracks):
                raise ValueError("editing_marker_track_exists")
            assembled.tracks.append(markers)
        draft.composition.media_timeline = timeline = assembled
        clips = candidate_clips
    except ValueError as error:
        assembly_trace = []
        blocker = _block(
            "assembly",
            str(error),
            "Esta seleção ou ordem não pode preservar os vínculos atuais. "
            "Ajuste os trechos ou mantenha a montagem original.",
        )
        blocker.alternatives.insert(
            0,
            EditingAlternativeV1(
                id="keep-original",
                label="Manter a montagem original",
                impact="Preserva os intervalos e a ordem atuais; os demais complementos continuam no plano.",
                action="keep_original",
            ),
        )
        blockers.append(blocker)
    repertoire = ensure_repertoire(db, document.workspace_id)
    knowledge = search_repertoire(db, document.workspace_id, request.intent.objective)
    references, profiles, unavailable = contextual_references(
        db, document.workspace_id, request.intent.objective, request.reference_technique_ids, CAPABILITIES
    )
    scene_profiles = {}
    for beat in beats:
        if beat.composition_technique_id:
            evidence, matches, missing = contextual_references(
                db, document.workspace_id, beat.purpose, [beat.composition_technique_id], CAPABILITIES
            )
            references.extend({**item, "clipId": beat.clip_id} for item in evidence)
            unavailable.extend(missing)
            if matches:
                scene_profiles[beat.clip_id] = matches
                if not beat.support_asset_id:
                    blockers.append(
                        _block(
                            beat.id,
                            "reference_material_required",
                            "A técnica desta cena precisa de imagem ou vídeo de apoio.",
                            optional=True,
                        )
                    )
    for technique_id in unavailable:
        blockers.append(
            _block(
                technique_id,
                "reference_unavailable",
                "Esta referência não está disponível com as capacidades atuais.",
                optional=True,
            )
        )
    if len(profiles) > 1:
        blockers.append(
            _block(
                "references",
                "reference_profiles_conflict",
                "Escolha uma referência de composição por plano; "
                "perfis diferentes não serão combinados arbitrariamente.",
            )
        )
        profiles = []
    if profiles and not any(b.support_asset_id for b in beats):
        blockers.append(
            _block(
                "references",
                "reference_material_required",
                "A referência precisa de material de apoio associado a uma cena.",
            )
        )

    def decision(kind, beat, target, reason, expected, techniques):
        operations.append(
            ContextualOperationV1(
                operation_id=f"edit-{uuid4()}",
                kind=kind,
                beat_id=beat.id,
                target_id=target,
                evidence_ids=[f"clip:{beat.clip_id}"],
                confidence=1,
                rationale=reason,
                expected_result=expected,
                technique_ids=techniques,
            )
        )

    for beat in beats:
        clip = clips[beat.clip_id]
        if beat.audio_asset_id:
            audio_ref = next((a for a in draft.assets if a.id == beat.audio_asset_id), None)
            if not audio_ref or not audio_ref.media_type.startswith("audio/"):
                blockers.append(_block(beat.id, "audio_material_missing", "Adicione o áudio solicitado ao acervo."))
            else:
                sound = AudioClipV1(
                    id=f"sound-{beat.id}",
                    asset_id=beat.audio_asset_id,
                    timeline=clip.timeline.model_copy(deep=True),
                    source=SourceTimeRangeV1(
                        start_microseconds=0,
                        duration_microseconds=round(
                            clip.timeline.duration_frames
                            * timeline.frame_rate.denominator
                            / timeline.frame_rate.numerator
                            * 1e6
                        ),
                    ),
                    gain_db=-12 if beat.audio_role == "music" else 0,
                    fade_in_frames=min(5, clip.timeline.duration_frames // 3),
                    fade_out_frames=min(5, clip.timeline.duration_frames // 3),
                    effects=[{"kind": "audio_role", "role": beat.audio_role}],
                )
                timeline.tracks.append(AudioTrackV1(id=f"sound-track-{beat.id}", clips=[sound]))
                decision(
                    "insert_audio",
                    beat,
                    sound.id,
                    f"Usar {beat.audio_role} para {beat.purpose}.",
                    "Áudio sincronizado à cena, com entrada e saída suaves.",
                    ["speech_priority"],
                )
        decision(
            "keep",
            beat,
            clip.id,
            f"Preservar o trecho completo para {beat.purpose}.",
            "Preservar o intervalo do material; seleções de fala exigem cobertura da transcrição.",
            ["continuity"],
        )
        trace = next((t for t in assembly_trace if t["clipId"] == clip.id), None)
        if trace:
            decision(
                "assemble",
                beat,
                clip.id,
                "Aplicar a ordem e os intervalos solicitados, mantendo todas as falas transcritas.",
                f"Trecho posicionado no frame {trace['toStartFrame']}, com {trace['durationFrames']} frames.",
                ["continuity"],
            )
            operations[-1].evidence_ids.extend(
                [f"transcript:{beat.transcript_id}:{beat.transcript_revision}"] if beat.transcript_id else []
            )
        for raw in clip.effects:
            kind = raw.get("kind", "unknown")
            decision(
                kind,
                beat,
                clip.id,
                f"Manter o tratamento de {kind} já definido para esta cena.",
                "Executar os parâmetros existentes sem inserir um efeito novo.",
                [],
            )
        if clip.keyframes or clip.transform:
            decision(
                "reframe",
                beat,
                clip.id,
                "Respeitar o enquadramento e a animação definidos no material.",
                "Composição posicionada de acordo com os parâmetros da cena.",
                ["directed_motion"] if clip.keyframes else [],
            )
        if beat.support_asset_id:
            ref = next((a for a in draft.assets if a.id == beat.support_asset_id), None)
            if ref is None:
                blockers.append(
                    _block(
                        beat.id,
                        "support_missing",
                        "O apoio visual solicitado ainda não está disponível.",
                        optional=True,
                    )
                )
            else:
                span = clip.timeline.model_copy(deep=True)
                fps = timeline.frame_rate.numerator / timeline.frame_rate.denominator
                support = MediaClipV1(
                    id=f"support-{beat.id}",
                    asset_id=ref.id,
                    timeline=span,
                    source={
                        "startMicroseconds": beat.support_source_start_microseconds,
                        "durationMicroseconds": round(span.duration_frames / fps * 1e6),
                    },
                    transform={
                        "fit": "contain",
                        "width": round(draft.composition.pages[0].width * 0.55),
                        "height": round(draft.composition.pages[0].height * 0.40),
                        "x": 0,
                        "y": 0,
                        "originalAudioEnabled": False,
                    },
                    label=beat.purpose,
                )
                if request.intent.emphasis == "demonstration":
                    support.transform.update(
                        width=round(draft.composition.pages[0].width * 0.85),
                        height=round(draft.composition.pages[0].height * 0.65),
                    )
                if request.intent.pacing == "calm" and not request.intent.reduced_motion:
                    support.effects = [
                        {
                            "kind": "fade",
                            "inFrames": min(round(fps * 0.4), span.duration_frames // 3),
                            "outFrames": min(round(fps * 0.4), span.duration_frames // 3),
                        }
                    ]
                elif (
                    request.intent.pacing == "energetic"
                    and not request.intent.reduced_motion
                    and span.duration_frames > 1
                ):
                    support.keyframes = [
                        {
                            "trackId": f"attention-{beat.id}",
                            "targetLayerId": support.id,
                            "property": "position_x",
                            "unit": "pixels",
                            "keyframes": [
                                {"frame": 0, "value": -round(draft.composition.pages[0].width * 0.04)},
                                {"frame": min(round(fps * 0.4), span.duration_frames - 1), "value": 0},
                            ],
                        }
                    ]
                if request.intent.emphasis == "atmosphere":
                    support.transform.update(
                        width=draft.composition.pages[0].width,
                        height=round(draft.composition.pages[0].height * 0.45),
                        y=round(draft.composition.pages[0].height * 0.1),
                    )
                effective_profiles = scene_profiles.get(beat.clip_id, profiles)
                if effective_profiles:
                    reference_id, reference = effective_profiles[0]
                    profile = reference.composition_profile
                    support.transform.update(
                        width=round(draft.composition.pages[0].width * profile.support_width_ratio),
                        height=round(draft.composition.pages[0].height * profile.support_height_ratio),
                    )
                    support.effects, support.keyframes = [], []
                    frames = min(max(1, round(fps * profile.entrance_seconds)), span.duration_frames // 3)
                    if profile.entrance == "fade" and frames and not request.intent.reduced_motion:
                        support.effects = [{"kind": "fade", "inFrames": frames, "outFrames": frames}]
                    elif profile.entrance == "zoom" and span.duration_frames > 1 and not request.intent.reduced_motion:
                        support.keyframes = [
                            {
                                "trackId": f"reference-{axis}-{beat.id}",
                                "targetLayerId": support.id,
                                "property": f"scale_{axis}",
                                "unit": "ratio",
                                "keyframes": [
                                    {"frame": 0, "value": 0.85, "easing": "ease_out"},
                                    {"frame": max(1, frames), "value": 1},
                                ],
                            }
                            for axis in ("x", "y")
                        ]
                    elif profile.entrance == "slide" and span.duration_frames > 1 and not request.intent.reduced_motion:
                        support.keyframes = [
                            {
                                "trackId": f"reference-{beat.id}",
                                "targetLayerId": support.id,
                                "property": "position_x",
                                "unit": "pixels",
                                "keyframes": [
                                    {"frame": 0, "value": -round(draft.composition.pages[0].width * 0.04)},
                                    {"frame": max(1, frames), "value": 0},
                                ],
                            }
                        ]
                page = draft.composition.pages[0]
                # Keep generated inserts away from screen edges when the layout has room.
                for axis, extent in (("x", page.width), ("y", page.height)):
                    size = support.transform["width" if axis == "x" else "height"]
                    margin = min(page.safe_area, max(0, (extent - size) // 2))
                    if support.transform[axis] == 0:
                        support.transform[axis] = margin
                        for animation in support.keyframes:
                            if animation["property"] == f"position_{axis}":
                                for keyframe in animation["keyframes"]:
                                    keyframe["value"] += margin
                timeline.tracks.append(OverlayTrackV1(id=f"support-track-{beat.id}", clips=[support]))
                decision(
                    "insert_broll",
                    beat,
                    support.id,
                    f"Mostrar o material indicado para {beat.purpose}.",
                    "Relacionar imagem de apoio e trecho original sem substituir sua fala.",
                    ["demonstration"],
                )
                if profiles:
                    operations[-1].technique_ids.append(reference.id)
                    operations[-1].evidence_ids.append(f"knowledge:{reference_id}")
                    operations[-1].rationale += " Adaptar as proporções da referência às dimensões deste projeto."
                if beat.mask_asset_id:
                    timeline.tracks.append(
                        MaskTrackV1(
                            id=f"support-mask-{beat.id}",
                            target_track_id=f"support-track-{beat.id}",
                            artifact_asset_id=beat.mask_asset_id,
                        )
                    )
                    decision(
                        "static_mask",
                        beat,
                        support.id,
                        "Usar a máscara fornecida para separar o apoio visual em camadas.",
                        "O recorte acompanha as dimensões do apoio e preserva o vídeo original.",
                        ["depth"],
                    )
                if support.effects or support.keyframes:
                    decision(
                        "direct_attention",
                        beat,
                        support.id,
                        f"Usar entrada {'gradual' if request.intent.pacing == 'calm' else 'curta'} "
                        "para introduzir o apoio visual no ritmo solicitado.",
                        "A atenção chega ao apoio sem alterar a duração da fala.",
                        ["directed_motion"],
                    )
        if beat.caption_from_transcript:
            try:
                transcript = transcripts.get(beat.clip_id)
                if transcript is None:
                    raise ValueError("editing_caption_transcript_required")
                captions = transcript_captions(draft, beat, clip, transcript)
                timeline.tracks.append(captions)
                for cue in captions.cues:
                    decision(
                        "add_caption",
                        beat,
                        cue.id,
                        "Legendar a fala a partir da transcrição vinculada ao material.",
                        "Texto original sincronizado com cortes, ordem e velocidade do trecho.",
                        ["readable_text"],
                    )
                    operations[-1].evidence_ids.append(
                        f"transcript:{beat.transcript_id}:{beat.transcript_revision}:{cue.source_segment_id}"
                    )
            except ValueError as error:
                blockers.append(
                    _block(
                        beat.id,
                        str(error),
                        "Não foi possível gerar legendas completas e sincronizadas para esta cena.",
                        optional=True,
                    )
                )
        if beat.on_screen_text:
            cue = CaptionCueV1(
                id=f"editorial-{beat.id}",
                timeline=clip.timeline.model_copy(deep=True),
                text=beat.on_screen_text,
                style={"fontSize": max(16, round(draft.composition.pages[0].width * 0.045))},
            )
            timeline.tracks.append(CaptionTrackV1(id=f"editorial-track-{beat.id}", cues=[cue]))
            decision(
                "add_caption",
                beat,
                cue.id,
                "Reforçar o texto fornecido no intervalo da cena.",
                "Texto permanece sincronizado com o trecho correspondente.",
                ["readable_text"],
            )
    for track in timeline.tracks:
        if track.kind == "audio" and not track.muted:
            for clip in track.clips:
                if clip.enabled:
                    role = next((a.provenance.get("purpose") for a in source.assets if a.id == clip.asset_id), None)
                    if role == "licensed-music-candidate" and not any(
                        e.get("kind") == "audio_role" for e in clip.effects
                    ):
                        clip.effects.append({"kind": "audio_role", "role": "music"})
                    operations.append(
                        ContextualOperationV1(
                            operation_id=f"edit-{uuid4()}",
                            kind="audio_mix",
                            beat_id=clip.id,
                            target_id=clip.id,
                            evidence_ids=[f"asset:{clip.asset_id}"],
                            confidence=1,
                            rationale="Manter a função do áudio disponível e priorizar a compreensão da fala.",
                            expected_result="Níveis equilibrados; música reduzida durante diálogo ou narração.",
                            technique_ids=["speech_priority"],
                        )
                    )
    if request.font_asset_id:
        font_ref = next((a for a in draft.assets if a.id == request.font_asset_id), None)
        if not font_ref or not font_ref.media_type.startswith("font/"):
            raise ValueError("editing_font_asset_required")
        for page in draft.composition.pages:
            for layer in page.layers:
                if layer.visible and layer.kind == "text" and not layer.locked:
                    layer.properties = {**layer.properties, "fontAssetId": request.font_asset_id}
        for track in timeline.tracks:
            if track.kind == "caption":
                for cue in track.cues:
                    cue.style.font_asset_id = request.font_asset_id
    executed_capabilities = set()
    runtime_blockers, cost = preflight(db, draft, executed_capabilities)
    for reference_evidence in references:
        if (
            reference_evidence["selection"] == "requested"
            and not set(reference_evidence["requiredCapabilities"]) <= executed_capabilities
        ):
            blockers.append(
                _block(
                    reference_evidence["techniqueId"],
                    "reference_material_required",
                    "Esta referência precisa de materiais ou parâmetros adicionais "
                    "para ser executada nesta composição.",
                    optional=True,
                )
            )
    for technique in request.required_techniques:
        if technique not in CAPABILITIES:
            blockers.append(
                _block(
                    technique,
                    "technique_unavailable",
                    f"A técnica {technique} ainda não tem execução disponível.",
                    optional=True,
                )
            )
        elif technique not in executed_capabilities:
            blockers.append(
                _block(
                    technique,
                    "technique_requires_material",
                    f"A técnica {technique} precisa de materiais ou parâmetros de edição associados à cena.",
                    optional=True,
                )
            )
    blockers.extend(runtime_blockers)
    now = datetime.now(UTC)
    plan = ContextualEditPlanV1(
        material_requests=material_requests,
        id=str(uuid4()),
        workspace_id=document.workspace_id,
        document_id=document.id,
        document_revision=document.revision,
        source_digest=_source_digest(source),
        source_assets={a.id: a.checksum for a in source.assets},
        source_transcripts=source_transcripts,
        editorial_evidence=[
            *references,
            *([{"type": "assembly", "mapping": assembly_trace}] if assembly_trace else []),
        ],
        intent=request.intent,
        operations=operations,
        blockers=blockers,
        status="awaiting_choice" if blockers else "ready",
        estimated_cost_cents=cost,
        cost_basis=(
            "Estimativa de CPU por duração, resolução e composição. Consumo de APIs registrado separadamente nos jobs."
        ),
        knowledge_ids=list(
            dict.fromkeys(
                [r.id for r in repertoire]
                + [k["documentId"] for k in knowledge]
                + [r["documentId"] for r in references]
            )
        ),
        draft_document=draft,
        created_at=now,
    )
    _save(db, document, plan, user, {"idempotencyKey": key, "requestHash": request_hash})
    db.commit()
    return plan


def _locked_plan(db, document, plan_id, revision):
    db.refresh(document, with_for_update=True)
    plan = get_plan(db, document.workspace_id, plan_id)
    if plan.document_id != document.id:
        raise ValueError("editing_plan_not_found")
    if plan.revision != revision:
        raise ValueError("editing_plan_revision_conflict")
    if _source_digest(record_to_contract(document)) != plan.source_digest:
        raise ValueError("editing_document_conflict")
    validate_transcript_bindings(db, document, plan.source_transcripts)
    return plan


def choose(db, document, plan_id, request, user):
    plan = _locked_plan(db, document, plan_id, request.expected_plan_revision)
    if plan.status == "applied":
        raise ValueError("editing_plan_already_applied")
    blocker = next((b for b in plan.blockers if b.id == request.blocker_id), None)
    alternative = next((a for a in blocker.alternatives if a.id == request.alternative_id), None) if blocker else None
    if alternative is None:
        raise ValueError("editing_choice_invalid")
    if alternative.action == "wait":
        return plan
    if alternative.action == "reduce_resolution":
        plan.draft_document = reduced_resolution(plan.draft_document)
        plan.blockers = [b for b in plan.blockers if b.id != blocker.id]
        plan.operations.append(
            ContextualOperationV1(
                operation_id=f"edit-{uuid4()}",
                kind="output_resolution",
                beat_id="output",
                target_id=plan.draft_document.composition.pages[0].id,
                evidence_ids=[f"choice:{blocker.id}"],
                confidence=1,
                rationale="Reduzir resolução conforme escolha do cliente para caber no orçamento.",
                expected_result="Preservar conteúdo e duração com dimensões menores.",
            )
        )
    elif alternative.action == "keep_original":
        plan.blockers = [b for b in plan.blockers if b.id != blocker.id]
    elif alternative.action == "omit_optional":
        generated_ids = {o.target_id for o in plan.operations if o.kind in {"insert_broll", "add_caption"}}
        remove_ids = (
            {blocker.target_id} & generated_ids
            if blocker.code
            not in {
                "technique_unavailable",
                "technique_requires_material",
                "reference_unavailable",
                "reference_material_required",
                "support_missing",
                "mask_support_required",
            }
            else set()
        )
        for track in plan.draft_document.composition.media_timeline.tracks:
            if hasattr(track, "clips"):
                track.clips = [c for c in track.clips if c.id not in remove_ids]
            if track.kind == "caption":
                track.cues = [c for c in track.cues if c.id not in remove_ids]
        for operation in plan.operations:
            if operation.target_id in remove_ids:
                operation.kind = "omit_optional"
                operation.rationale = "Complemento removido conforme escolha explícita do cliente."
                operation.expected_result = "A mensagem original permanece intacta."
        plan.blockers = [b for b in plan.blockers if b.id != blocker.id]
    else:
        raise ValueError("editing_choice_unsupported")
    runtime, cost = preflight(db, plan.draft_document)
    existing_ids = {b.id for b in plan.blockers}
    plan.blockers.extend(b for b in runtime if b.id not in existing_ids)
    plan.estimated_cost_cents = cost
    plan.status = "awaiting_choice" if plan.blockers else "ready"
    plan.revision += 1
    _save(db, document, plan, user, {"choice": request.model_dump(mode="json", by_alias=True)})
    db.commit()
    return plan


def feedback(db, document, plan_id, request, user):
    plan = _locked_plan(db, document, plan_id, request.expected_plan_revision)
    if isinstance(plan, ContextualEditPlanV2):
        from .contextual_editing_v2 import feedback as feedback_v2

        return feedback_v2(db, document, plan, request, user)
    known = {o.beat_id for o in plan.operations}
    if not set(request.beat_ids) <= known:
        raise ValueError("editing_feedback_beat_unknown")
    target_ids = {o.target_id for o in plan.operations if o.beat_id in request.beat_ids}
    generated_ids = {o.target_id for o in plan.operations if o.kind in {"insert_broll", "add_caption"}}
    target_ids &= generated_ids
    runtime_before, _ = preflight(db, plan.draft_document)
    runtime_ids = {b.id for b in runtime_before}
    timeline = plan.draft_document.composition.media_timeline
    fps = timeline.frame_rate.numerator / timeline.frame_rate.denominator
    changed = set()
    if request.feedback == "menos texto":
        for track in timeline.tracks:
            if track.kind == "caption" and track.id.startswith("editorial-track-"):
                removed = {c.id for c in track.cues if c.id in target_ids}
                track.cues = [c for c in track.cues if c.id not in removed]
                changed.update(removed)
    else:
        for track in timeline.tracks:
            for clip in getattr(track, "clips", []):
                if clip.id not in target_ids or not clip.id.startswith("support-"):
                    continue
                if request.feedback == "mais calmo":
                    # Change only generated motion; never slow down or remove a spoken sentence.
                    clip.keyframes = []
                    clip.effects = [e for e in clip.effects if e.get("kind") != "fade"]
                    if not plan.intent.reduced_motion:
                        clip.effects.append(
                            {
                                "kind": "fade",
                                "inFrames": min(round(fps * 0.5), clip.timeline.duration_frames // 3),
                                "outFrames": min(round(fps * 0.5), clip.timeline.duration_frames // 3),
                            }
                        )
                else:
                    page = plan.draft_document.composition.pages[0]
                    clip.transform.update(width=round(page.width * 0.90), height=round(page.height * 0.70))
                changed.add(clip.id)
    if not changed:
        raise ValueError("editing_feedback_requires_matching_material")
    for operation in plan.operations:
        if operation.target_id in changed:
            operation.rationale = f"Ajuste solicitado na cena: {request.feedback}."
            operation.expected_result = (
                "Complemento textual removido; fala preservada."
                if request.feedback == "menos texto"
                else "Apoio visual ajustado; duração e mensagem originais preservadas."
            )
            if request.feedback == "menos texto":
                operation.kind = "omit_text"
    unresolved_choices = [b for b in plan.blockers if b.id not in runtime_ids]
    plan.blockers, plan.estimated_cost_cents = preflight(db, plan.draft_document)
    plan.blockers.extend(unresolved_choices)
    plan.status = "awaiting_choice" if plan.blockers else "ready"
    plan.revision += 1
    _save(db, document, plan, user, {"feedback": request.model_dump(mode="json", by_alias=True)})
    db.commit()
    return plan


def apply_plan(db, document, plan_id, request, user):
    db.refresh(document, with_for_update=True)
    current_plan = get_plan(db, document.workspace_id, plan_id)
    if (
        current_plan.document_id == document.id
        and current_plan.status == "applied"
        and request.expected_plan_revision in {current_plan.revision, current_plan.revision - 1}
        and _source_digest(record_to_contract(document)) == current_plan.source_digest
    ):
        return record_to_contract(document)
    plan = _locked_plan(db, document, plan_id, request.expected_plan_revision)
    if plan.status == "applied":
        return record_to_contract(document)
    if isinstance(plan, ContextualEditPlanV2):
        from ...domain.studios.contextual_editing_v2 import ContextualPlanRequestV2
        from ...domain.studios.visual_audit import preflight_visual
        from .contextual_editing_v2 import preflight_v2
        from .production_audit import blocking_visual_findings

        blockers, _ = preflight_v2(db, plan.draft_document)
        if plan.status != "ready" or blockers:
            raise ValueError("editing_choice_required")
        executable_direction = ContextualPlanRequestV2.model_validate(
            plan.manifest.get("executableDirection")
            or plan.direction.model_dump(mode="json", by_alias=True)
        )
        visual = preflight_visual(
            executable_direction,
            plan.motion_graph,
            canvas_width=plan.draft_document.composition.pages[0].width,
            canvas_height=plan.draft_document.composition.pages[0].height,
        )
        if blocking_visual_findings(visual):
            raise ValueError("editing_visual_preflight_required")
    else:
        blockers, _ = preflight(db, plan.draft_document)
    if plan.status != "ready" or blockers:
        raise ValueError("editing_choice_required")
    draft = plan.draft_document.model_copy(deep=True)
    draft.revision = document.revision + 1
    draft.status = "draft"
    draft.review = ReviewReferenceV1()
    draft.updated_at = datetime.now(UTC)
    draft.composition.narrative["contextualPlanId"] = plan.id
    draft.composition.narrative["editingPolicy"] = "draft-first-preserve-message"
    if isinstance(plan, ContextualEditPlanV2):
        plan.motion_graph.document_revision = draft.revision
        draft.composition.narrative["editorialV2"]["motionGraph"] = plan.motion_graph.model_dump(
            mode="json", by_alias=True
        )
    invalidate_linked_post_review(db, document)
    persist_contract(document, draft)
    plan.draft_document = draft
    plan.document_revision = draft.revision
    plan.source_digest = _source_digest(draft)
    plan.status = "applied"
    plan.revision += 1
    _save(db, document, plan, user, {"applied": True})
    db.commit()
    return record_to_contract(document)


def verify_render_receipt(plan, encoded):
    """Check compiler coverage, not semantic or perceptual correctness of the export."""
    draft = plan.draft_document
    timeline = draft.composition.media_timeline
    visuals = {c.id for t in timeline.tracks if t.kind in {"video", "overlay"} for c in t.clips if c.enabled}
    visuals.update(layer.id for layer in draft.composition.pages[0].layers if layer.visible)
    audio = {c.id for t in timeline.tracks if t.kind == "audio" and not t.muted for c in t.clips if c.enabled}
    captions = {t.id for t in timeline.tracks if t.kind == "caption" and t.cues}
    if (
        not visuals <= set(encoded.rendered_layer_ids)
        or not audio <= set(encoded.rendered_audio_clip_ids)
        or not captions <= set(encoded.rendered_caption_track_ids)
    ):
        raise ValueError("editing_render_coverage_incomplete")
    cues = {c.id for t in timeline.tracks if t.kind == "caption" for c in t.cues}
    present = visuals | audio | cues
    checks = []
    for operation in plan.operations:
        omitted = operation.kind in {"omit_optional", "omit_text"}
        output = operation.kind == "output_resolution"
        if (omitted and operation.target_id in present) or (
            not omitted and not output and operation.target_id not in present
        ):
            raise ValueError("editing_operation_coverage_incomplete")
        checks.append(
            {
                "operationId": operation.operation_id,
                "targetId": operation.target_id,
                "status": "omission-confirmed" if omitted else "compiled-and-encoded",
            }
        )
    return checks


def require_render_plan(db, document, snapshot, plan_id):
    plan = get_plan(db, document.workspace_id, plan_id)
    if plan.document_id != document.id or plan.status != "applied" or plan.blockers:
        raise ValueError("editing_applied_plan_required")
    validate_transcript_bindings(db, document, plan.source_transcripts)
    if (
        _source_digest(snapshot) != plan.source_digest
        or _source_digest(record_to_contract(document)) != plan.source_digest
    ):
        raise ValueError("editing_document_conflict")
    problems = [] if isinstance(plan, ContextualEditPlanV2) else inspect_document(snapshot)
    if problems or asset_blockers(db, snapshot):
        raise ValueError("editing_preflight_failed")
    return plan


def reserve_cost(db, document, plan, user, key):
    # Serialize workspace-wide reservations, including different documents in PostgreSQL.
    db.execute(select(Workspace).where(Workspace.id == document.workspace_id).with_for_update()).scalar_one()
    reservations = _events(db, document.workspace_id, "studio.editing.cost_reserved")
    for event in reservations:
        if event.payload.get("renderKey") == key:
            if event.payload.get("planId") != plan.id or event.payload.get("planRevision") != plan.revision:
                raise ValueError("editing_idempotency_conflict")
            return
    if plan.estimated_cost_cents > budget_remaining(db, document.workspace_id):
        raise ValueError("editing_budget_exceeded_choice_required")
    emit_event(
        db,
        workspace_id=document.workspace_id,
        event_type="studio.editing.cost_reserved",
        aggregate_type="editing_plan",
        aggregate_id=plan.id,
        correlation_id=f"editing:{plan.id}",
        actor_id=user.id,
        payload={
            "month": datetime.now(UTC).strftime("%Y-%m"),
            "costCents": plan.estimated_cost_cents,
            "renderKey": key,
            "planId": plan.id,
            "planRevision": plan.revision,
        },
    )
    db.flush()
