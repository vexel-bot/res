"""Backend coordination over existing document, event, connection and job stores.

This stage admits only deterministic tools or an explicitly configured local
Ollama model. The existing Gemini KLIC and paid admission policy are untouched.
"""

import math
import re
import time
from datetime import UTC, datetime
from uuid import uuid4

import httpx
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from ...domain.studios.agents import AgentOutput, LocalCommandsRequest, RoleConfiguration
from ...domain.studios.contracts import (
    AssetReferenceV1,
    CreativeCompositionV1,
    CreativeLayerV1,
    MediaTimelineV1,
    ReviewReferenceV1,
)
from ...domain.studios.local_composition import LocalLayerStyle, validate_composition
from ...models import BrandProfile, CreativeDocument, StudioDomainEvent, StudioGenerationJob
from ...providers.studios.local_composition import raster
from ...providers.studios.universal_llm import validate_endpoint
from . import local_agents, timeline_editor
from .compatibility import composition_to_canvas, record_to_contract
from .contextual_editing import lock_editing_budget
from .craft import scoped_asset
from .kernel import emit_event
from .llm_connections import access, planner
from .review_binding import invalidate_linked_post_review

CONFIG_EVENT = "studio.agents.roles"
COMMIT_EVENT = "studio.local.commands.committed"


def configuration(db, workspace_id):
    event = db.scalar(
        select(StudioDomainEvent)
        .where(StudioDomainEvent.workspace_id == workspace_id, StudioDomainEvent.event_type == CONFIG_EVENT)
        .order_by(StudioDomainEvent.occurred_at.desc(), StudioDomainEvent.id.desc())
    )
    return (
        event.payload
        if event
        else {"revision": 0, "audiovisual": {"mode": "local_tools"}, "image": {"mode": "local_tools"}}
    )


def local_planner(db, workspace_id, binding):
    row, provider, model, fingerprint = planner(db, workspace_id, binding["connectionId"], binding["model"])
    # A loopback address alone does not prove zero cost (Ollama also has cloud models).
    config = row.config
    if (
        config["billingMode"] != "local_free"
        or config["protocol"] != "ollama_chat"
        or not validate_endpoint(config)
        or row.credential_ciphertext
        or config.get("extraHeaders")
        or config.get("requestPath")
        or "cloud" in model.lower()
    ):
        raise ValueError("agent_requires_local_ollama_no_cloud_or_credential")
    return row, provider, model, fingerprint


def save_configuration(db, workspace_id, request: RoleConfiguration, user):
    access(db, user.id, workspace_id, owner=True)
    lock_editing_budget(db, workspace_id)
    current = configuration(db, workspace_id)
    if request.expected_revision != current["revision"]:
        raise ValueError("agent_role_revision_conflict")
    payload = request.model_dump(mode="json", by_alias=True, exclude={"expected_revision"})
    for binding in payload.values():
        if binding["mode"] == "local_model":
            local_planner(db, workspace_id, binding)
    payload["revision"] = current["revision"] + 1
    emit_event(
        db,
        workspace_id=workspace_id,
        event_type=CONFIG_EVENT,
        aggregate_type="agent_roles",
        aggregate_id=workspace_id,
        correlation_id=str(uuid4()),
        actor_id=user.id,
        payload=payload,
    )
    db.commit()
    return payload


def validate_document(db, contract):
    if len(contract.assets) > 1000:
        raise ValueError("agent_asset_reference_limit")
    if contract.native_editor_state:
        raise ValueError("agent_native_project_use_existing_craft_commands")
    refs = validate_composition(contract.composition, contract.content_type)
    if contract.content_type == "video":
        refs |= timeline_editor.validate(contract)
    known = {asset.id: asset for asset in contract.assets}
    for identifier in refs:
        reference = known.get(identifier)
        if not reference or not reference.checksum:
            raise ValueError("agent_asset_not_bound")
        asset = scoped_asset(db, contract.workspace_id, identifier, reference.checksum)
        if reference.rights_status == "restricted" or (asset.object_metadata or {}).get("rightsStatus") == "restricted":
            raise ValueError("agent_asset_restricted")
        if identifier in {
            layer.properties.get("assetId") or layer.properties.get("asset_id")
            for layer in contract.composition.pages[0].layers
        } and not asset.media_type.startswith("image/"):
            raise ValueError("agent_layer_requires_image")
    for layer in contract.composition.pages[0].layers:
        if not all(
            math.isfinite(value)
            for value in (layer.x, layer.y, layer.width, layer.height, layer.opacity, layer.rotation)
        ):
            raise ValueError("agent_layer_value_invalid")
        if layer.kind in {"text", "shape"}:
            raster(layer, {})  # Fit validation precedes committing an unusable editable layer.
    return refs


def exact(params, names):
    if set(params) != set(names):
        raise ValueError("agent_command_parameters_invalid")


def validate_selection_scope(operations, selected_ids):
    """A model/rule cannot turn a selected-layer edit into a project-wide edit."""
    if not selected_ids:
        return
    allowed = set(selected_ids)
    for command in operations:
        if command.id == "asset.attach":
            continue
        target = (
            command.params.get("layer", {}).get("id")
            if command.id == "layer.upsert" and isinstance(command.params.get("layer"), dict)
            else command.params.get("layerId")
            if command.id == "layer.remove"
            else None
        )
        if not isinstance(target, str) or target not in allowed:
            raise ValueError("agent_selection_scope_violation")


def proposed_document(db, contract, operations):
    if contract.native_editor_state:
        raise ValueError("agent_native_project_use_existing_craft_commands")
    proposal = contract.model_copy(deep=True)
    page = proposal.composition.pages[0]
    for command in operations:
        params = command.params
        if command.id == "composition.replace":
            exact(params, {"composition"})
            proposal.composition = CreativeCompositionV1.model_validate(params["composition"])
            page = proposal.composition.pages[0]
        elif command.id == "layer.upsert":
            exact(params, {"layer"})
            layer = CreativeLayerV1.model_validate(params["layer"])
            previous = next((item for item in page.layers if item.id == layer.id), None)
            if previous and previous.locked and layer != previous:
                raise ValueError("agent_layer_locked")
            page.layers = [layer if item.id == layer.id else item for item in page.layers]
            if not previous:
                page.layers.append(layer)
        elif command.id == "layer.remove":
            exact(params, {"layerId"})
            target = next((layer for layer in page.layers if layer.id == params["layerId"]), None)
            if not target or target.locked:
                raise ValueError("agent_layer_missing_or_locked")
            page.layers = [layer for layer in page.layers if layer.id != target.id]
        elif command.id == "project.background":
            exact(params, {"color"})
            if not isinstance(params["color"], str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", params["color"]):
                raise ValueError("agent_color_invalid")
            page.background = params["color"]
        elif command.id == "project.duration":
            exact(params, {"seconds"})
            seconds = params["seconds"]
            if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or not 1 <= seconds <= 120:
                raise ValueError("agent_duration_invalid")
            timeline = proposal.composition.media_timeline
            if not timeline or any(
                getattr(track, "clips", []) or getattr(track, "cues", []) for track in timeline.tracks
            ):
                raise ValueError("agent_media_duration_use_timeline_editor")
            length = round(seconds * timeline.frame_rate.numerator / timeline.frame_rate.denominator)
            ratio = length / timeline.duration_frames
            for layer in page.layers:
                style = LocalLayerStyle.model_validate(layer.properties)
                start = min(length - 1, round(style.start_frame * ratio))
                old_end = style.start_frame + (style.duration_frames or timeline.duration_frames)
                end = min(length, max(start + 1, round(old_end * ratio)))
                style.start_frame, style.duration_frames = start, end - start
                if style.text_reveal == "words":
                    style.word_stagger_frames = max(1, min(120, round(style.word_stagger_frames * ratio)))
                # Rounding may collide; keep the last key at the resulting frame.
                keys = {}
                for key in style.keyframes:
                    key.frame = min(end - start, round(key.frame * ratio))
                    keys[(key.property, key.frame)] = key
                style.keyframes = list(keys.values())
                layer.properties = style.model_dump(mode="json", by_alias=True)
            timeline.duration_frames, page.duration_ms = length, round(seconds * 1000)
            production = proposal.composition.narrative.get("localProduction", {})
            for scene in production.get("scenes", []):
                start = min(length - 1, round(scene["startFrame"] * ratio))
                end = min(length, max(start + 1, round((scene["startFrame"] + scene["durationFrames"]) * ratio)))
                scene.update(startFrame=start, durationFrames=end - start)
        elif command.id == "timeline.replace":
            exact(params, {"timeline"})
            if proposal.content_type != "video":
                raise ValueError("agent_video_project_required")
            proposal.composition.media_timeline = MediaTimelineV1.model_validate(params["timeline"])
            timeline = proposal.composition.media_timeline
            page.duration_ms = round(
                timeline.duration_frames * timeline.frame_rate.denominator / timeline.frame_rate.numerator * 1000
            )
        elif command.id == "asset.attach":
            exact(params, {"assetId"})
            if not isinstance(params["assetId"], str):
                raise ValueError("agent_asset_id_invalid")
            asset = scoped_asset(db, contract.workspace_id, params["assetId"])
            if not asset.media_type.startswith(("image/", "audio/", "video/")):
                raise ValueError("agent_asset_type_unsupported")
            if asset.id not in {ref.id for ref in proposal.assets}:
                proposal.assets.append(
                    AssetReferenceV1(id=asset.id, media_type=asset.media_type, checksum=asset.checksum_sha256)
                )
    old_locked = {layer.id: layer for layer in contract.composition.pages[0].layers if layer.locked}
    new_layers = {layer.id: layer for layer in page.layers}
    if any(new_layers.get(identifier) != layer for identifier, layer in old_locked.items()):
        raise ValueError("agent_layer_locked")
    old_timeline, new_timeline = contract.composition.media_timeline, proposal.composition.media_timeline
    if old_timeline:
        targets = {track.id: track for track in new_timeline.tracks} if new_timeline else {}
        for track in old_timeline.tracks:
            if track.locked and targets.get(track.id) != track:
                raise ValueError("agent_track_locked")
            target_items = {item.id: item for item in getattr(targets.get(track.id), "clips", [])}
            for item in getattr(track, "clips", []):
                if item.locked and target_items.get(item.id) != item:
                    raise ValueError("agent_clip_locked")
    validate_document(db, proposal)
    return proposal


def command_receipt(db, document, key, fingerprint):
    event = db.scalar(
        select(StudioDomainEvent).where(
            StudioDomainEvent.workspace_id == document.workspace_id,
            StudioDomainEvent.aggregate_id == document.id,
            StudioDomainEvent.event_type == COMMIT_EVENT,
            StudioDomainEvent.correlation_id == key,
        )
    )
    if event:
        if event.payload["fingerprint"] != fingerprint:
            raise ValueError("idempotency_payload_conflict")
        return event.payload["document"]


def commit_commands(db, document, request: LocalCommandsRequest, user, key, *, selected_layer_ids=()):
    if len(request.model_dump_json()) > 256000:
        raise ValueError("agent_command_size_limit")
    fingerprint = timeline_editor.digest(request.model_dump(mode="json", by_alias=True))
    lock_editing_budget(db, document.workspace_id)
    replay = command_receipt(db, document, key, fingerprint)
    if replay:
        db.rollback()
        return replay
    db.refresh(document)
    if document.revision != request.expected_revision:
        raise ValueError("studio_document_conflict")
    current = record_to_contract(document)
    # Exact committed receipts stay replayable across validation upgrades. Only
    # a new mutation must satisfy the selected-layer scope policy.
    validate_selection_scope(request.commands, selected_layer_ids)
    result = proposed_document(db, current, request.commands)
    now = datetime.now(UTC)
    result = result.model_copy(
        update={
            "revision": current.revision + 1,
            "version": current.version + 1,
            "updated_at": now,
            "actor_id": user.id,
            "status": "draft",
            "review": ReviewReferenceV1(),
        }
    )
    payload = result.model_dump(mode="json", by_alias=True)
    versions = [
        *(document.versions or []),
        {
            "number": current.version,
            "label": "Antes da edição local",
            "createdAt": now.isoformat(),
            "actorId": user.id,
            "canonicalDocument": current.model_dump(mode="json", by_alias=True),
            "document": document.document,
        },
    ][-20:]
    changed = db.execute(
        update(CreativeDocument)
        .where(CreativeDocument.id == document.id, CreativeDocument.revision == request.expected_revision)
        .values(
            canonical_document=payload,
            document=composition_to_canvas(result).model_dump(by_alias=True),
            revision=result.revision,
            version=result.version,
            versions=versions,
            updated_at=now,
        ),
        execution_options={"synchronize_session": False},
    )
    if changed.rowcount != 1:
        raise ValueError("studio_document_conflict")
    invalidate_linked_post_review(db, document)
    emit_event(
        db,
        workspace_id=document.workspace_id,
        event_type=COMMIT_EVENT,
        aggregate_type="creative_document",
        aggregate_id=document.id,
        actor_id=user.id,
        correlation_id=key,
        payload={"fingerprint": fingerprint, "document": payload},
    )
    db.commit()
    db.refresh(document)
    return payload


def task_out(job, db=None):
    result = {
        "id": job.id,
        "documentId": job.document_id,
        "workspaceId": job.workspace_id,
        "status": job.status,
        "role": job.request_payload["role"],
        "documentRevision": job.request_payload["documentRevision"],
        "provider": job.provider,
        "model": job.request_payload.get("model"),
        "externalCostUsd": 0,
        "result": job.result_payload,
        "errorCode": job.error_code,
        "requestedBy": job.requested_by,
        "instruction": job.request_payload.get("instruction"),
        "selectedLayerIds": job.request_payload.get("selectedLayerIds", []),
        "createdAt": job.created_at.isoformat() if job.created_at else None,
        "finishedAt": job.finished_at.isoformat() if job.finished_at else None,
        "limits": {"externalBudgetUsd": 0, "maxAttempts": 1, "maxCommands": 32},
    }
    if db is not None:
        events = db.scalars(
            select(StudioDomainEvent)
            .where(
                StudioDomainEvent.workspace_id == job.workspace_id,
                StudioDomainEvent.aggregate_id == job.id,
            )
            .order_by(StudioDomainEvent.occurred_at, StudioDomainEvent.id)
        ).all()
        receipt = db.scalar(
            select(StudioDomainEvent).where(
                StudioDomainEvent.workspace_id == job.workspace_id,
                StudioDomainEvent.aggregate_id == job.document_id,
                StudioDomainEvent.event_type == COMMIT_EVENT,
                StudioDomainEvent.correlation_id == "agent-apply:" + job.id,
            )
        )
        result["appliedRevision"] = receipt.payload["document"]["revision"] if receipt else None
        result["history"] = [
            {
                "type": event.event_type,
                "at": event.occurred_at.isoformat(),
                "actorId": event.actor_id,
                "detail": event.payload,
            }
            for event in events
        ]
    return result


def require_installed_model(provider, model):
    # Never pull weights or invoke an Ollama cloud proxy. Explicitly registered,
    # already-installed model metadata must describe local tensor weights.
    try:
        with httpx.Client(timeout=5, follow_redirects=False, trust_env=False) as client:
            response = client.post(provider.config["baseUrl"].rstrip("/") + "/api/show", json={"model": model})
            response.raise_for_status()
            if len(response.content) > 1_000_000:
                raise ValueError("agent_model_metadata_too_large")
            info = response.json()
    except (httpx.HTTPError, ValueError) as error:
        raise ValueError("agent_local_model_unavailable") from error
    if info.get("remote_host") or info.get("remote_model") or not info.get("model_info"):
        raise ValueError("agent_model_must_be_installed_local_weights")


def create_task(db, document, request, user, key):
    payload = request.model_dump(mode="json", by_alias=True)
    if payload.get("planner") == "current":
        payload.pop("planner")
    if payload.get("durationSeconds") is None:
        payload.pop("durationSeconds", None)
    if not payload.get("probe"):
        payload.pop("probe", None)
    if not payload.get("selectedLayerIds"):
        payload.pop("selectedLayerIds", None)  # Preserve replay hashes of pre-selection tasks.
    fingerprint = timeline_editor.digest(payload)
    existing = db.scalar(
        select(StudioGenerationJob).where(
            StudioGenerationJob.workspace_id == document.workspace_id,
            StudioGenerationJob.job_type == "agent_plan",
            StudioGenerationJob.idempotency_key == key,
        )
    )
    if existing:
        if existing.document_id != document.id or existing.payload_hash != fingerprint:
            raise ValueError("idempotency_payload_conflict")
        return task_out(existing, db)
    contract = record_to_contract(document)
    if request.expected_revision != contract.revision:
        raise ValueError("studio_document_conflict")
    validate_document(db, contract)
    if set(request.selected_layer_ids) - {layer.id for layer in contract.composition.pages[0].layers}:
        raise ValueError("agent_selected_layer_not_found")
    role = request.role if request.role != "auto" else ("audiovisual" if contract.content_type == "video" else "image")
    if (role == "image") != (contract.content_type == "visual"):
        raise ValueError("agent_role_project_mismatch")
    roles = configuration(db, contract.workspace_id)
    binding = roles[role]
    experimental = request.planner == "gemini_experimental"
    history_output = (
        None
        if experimental
        else local_agents.history_undo(contract, request.instruction, document.versions, request.selected_layer_ids)
    )
    model, provider = None, None
    experiment_row, proof = None, None
    if experimental:
        from ...domain.studios.motion_gemini import MotionAgentOutput
        from . import motion_gemini

        if role != "audiovisual":
            raise ValueError("motion_gemini_motion_only")
        experiment_row, provider, model, proof = motion_gemini.admitted_planner(db, document, user)
    elif history_output is None and binding["mode"] == "local_model" and request.planner != "deterministic":
        _connection, provider, model, _fingerprint = local_planner(db, contract.workspace_id, binding)
        require_installed_model(provider, model)
    lock_editing_budget(db, contract.workspace_id)
    # Recheck after acquiring the workspace write lock: simultaneous replays must
    # observe the admitted task rather than creating another inference attempt.
    existing = db.scalar(
        select(StudioGenerationJob).where(
            StudioGenerationJob.workspace_id == document.workspace_id,
            StudioGenerationJob.job_type == "agent_plan",
            StudioGenerationJob.idempotency_key == key,
        )
    )
    if existing:
        if existing.document_id != document.id or existing.payload_hash != fingerprint:
            raise ValueError("idempotency_payload_conflict")
        db.rollback()
        return task_out(existing, db)
    in_flight = db.scalars(
        select(StudioGenerationJob).where(
            StudioGenerationJob.workspace_id == contract.workspace_id,
            StudioGenerationJob.job_type == "agent_plan",
            StudioGenerationJob.status.in_(["running", "cancel_requested"]),
        )
    ).all()
    if in_flight:
        raise ValueError("agent_workspace_busy_or_interrupted_task")
    job = StudioGenerationJob(
        id=str(uuid4()),
        workspace_id=contract.workspace_id,
        requested_by=user.id,
        document_id=document.id,
        job_type="agent_plan",
        provider="google.motion-gemini" if experimental else "llm.ollama" if provider else "clicko.local-tools",
        execution_capability="media_cpu",
        queue_name="studio.control",
        resource_class="cpu.media",
        hard_time_limit_seconds=180,
        max_attempts=1,
        attempts=1,
        idempotency_key=key,
        payload_hash=fingerprint,
        correlation_id=key,
        status="running",
        request_payload={
            "role": role,
            "instruction": request.instruction,
            "documentRevision": contract.revision,
            "roleRevision": roles["revision"],
            "mode": "gemini_experimental"
            if experimental
            else "local_tools"
            if history_output is not None or request.planner == "deterministic"
            else binding["mode"],
            "model": model,
            "selectedLayerIds": request.selected_layer_ids,
        },
    )
    if experimental:
        motion_gemini.reserve(db, job, experiment_row, proof)
    db.add(job)
    emit_event(
        db,
        workspace_id=contract.workspace_id,
        event_type="studio.agent.started",
        aggregate_type="agent_task",
        aggregate_id=job.id,
        actor_id=user.id,
        correlation_id=key,
        payload={
            "role": role,
            "documentId": document.id,
            "documentRevision": contract.revision,
            "selectedLayerIds": request.selected_layer_ids,
            "externalBudgetUsd": 0,
        },
    )
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise ValueError("agent_task_already_admitted") from error
    started, response = time.monotonic(), None
    try:
        if provider:
            context = {
                "instruction": request.instruction,
                "agentRole": role,
                "selectedLayerIds": request.selected_layer_ids,
                "project": contract.model_dump(mode="json", by_alias=True),
                "outputSchema": (MotionAgentOutput if experimental else AgentOutput).model_json_schema(by_alias=True),
                "layerStyleSchema": LocalLayerStyle.model_json_schema(by_alias=True),
                "maxOutputTokens": proof.max_output_tokens if experimental else 3000,
                "maxPromptChars": 24000,
                "localExecution": not experimental,
                "motionExperimental": experimental,
                "structuredPlanningInstruction": "Return commands and rationale only. Use the declared local "
                "operations. No shell, URLs, scripts, remote generation, new asset IDs or execution claims.",
            }
            if experimental:
                brand = db.scalar(select(BrandProfile).where(BrandProfile.workspace_id == contract.workspace_id))
                context["brandIdentity"] = (
                    {
                        "name": brand.name,
                        "primaryColor": brand.primary_color,
                        "tone": brand.tone[:1000],
                        "guidelines": brand.do_and_donts[:1500],
                    }
                    if brand
                    else {}
                )
                context.update(
                    requestedDurationSeconds=request.duration_seconds,
                    renderer={
                        "name": "Clicko local 2D / FFmpeg",
                        "maxLayers": 24,
                        "operations": [
                            "composition.replace",
                            "layer.upsert",
                            "layer.remove",
                            "project.duration",
                            "project.background",
                            "asset.attach",
                        ],
                        "kinds": ["text", "shape", "image"],
                        "transitions": ["opacity fades via keyframes"],
                        "easing": ["linear", "ease-out", "ease-in-out"],
                        "true3D": False,
                        "fonts": ["system", "Liberation Sans"],
                        "audio": "recommendations only; do not synthesize or invent assets",
                    },
                    creativeBrief=(
                        "Plan concept, narrative, scenes/durations, text, graphic layers, palette, typography, "
                        "movement, keyframes, available transitions, rhythm and audio recommendations. "
                        "Put review notes in direction; put scene metadata in "
                        "composition.narrative.localProduction.scenes. "
                        "Use only supplied schemas and authorized project asset IDs."
                    ),
                )
            if experimental and request.probe:
                context = {
                    "instruction": "Connectivity check. Return commands:[] and rationale:ok. Do not propose edits.",
                    "outputSchema": AgentOutput.model_json_schema(by_alias=True),
                    "maxOutputTokens": 128,
                    "maxPromptChars": 24000,
                    "motionExperimental": True,
                }
            response = provider.plan(model, context, [])
            if experimental:
                from .llm_connections import decrypt

                if decrypt(experiment_row) in response["text"]:
                    raise ValueError("motion_gemini_response_credential_rejected")
            output = (MotionAgentOutput if experimental and not request.probe else AgentOutput).model_validate_json(
                response["text"]
            )
            if request.probe and output.commands:
                raise ValueError("motion_gemini_probe_must_not_edit")
            trace = {
                "inference": "gemini_experimental" if experimental else "local_model",
                "usage": response["usage"],
                "delegations": [role],
            }
        else:
            image_agent = local_agents.ImageAgent()
            agent = image_agent if role == "image" else local_agents.AudiovisualAgent(image_agent)
            output = (
                history_output
                if history_output is not None
                else agent.plan(contract, request.instruction, request.selected_layer_ids)
            )
            trace = {
                "inference": "none",
                "planning": "deterministic_rules",
                "delegations": [role] + (["image"] if role != "image" and image_agent.requests else []),
                "delegateRequests": image_agent.requests,
            }
        if len(output.model_dump_json()) > 160000:
            raise ValueError("agent_plan_too_large")
        db.refresh(job)
        if job.status in {"cancel_requested", "cancelled"}:
            job.status = "cancelled"
            job.result_payload = {
                "state": "cancelled",
                "commands": [],
                "rationale": "Planejamento cancelado; nenhuma edição aplicada.",
                **trace,
            }
            job.finished_at = datetime.now(UTC)
            db.commit()
            emit_event(
                db,
                workspace_id=contract.workspace_id,
                event_type="studio.agent.cancelled",
                aggregate_type="agent_task",
                aggregate_id=job.id,
                actor_id=user.id,
                correlation_id=key,
                payload={"role": role},
            )
            db.commit()
            return task_out(job, db)
        if job.status != "running":
            raise ValueError("agent_task_no_longer_active")
        if output.commands:
            validate_selection_scope(output.commands, request.selected_layer_ids)
            proposal = proposed_document(db, contract, output.commands)
            if experimental and request.duration_seconds:
                t = proposal.composition.media_timeline
                if (
                    abs(
                        t.duration_frames * t.frame_rate.denominator / t.frame_rate.numerator - request.duration_seconds
                    )
                    > 0.05
                ):
                    raise ValueError("motion_gemini_duration_mismatch")
        job.status, job.progress = "succeeded", 100
        job.result_payload = {
            **output.model_dump(mode="json", by_alias=True),
            **trace,
            "state": "planned" if output.commands else "unsupported",
            "planningTimeMs": round((time.monotonic() - started) * 1000),
            **({"connectionProbe": True} if request.probe else {}),
            **({"billingAdmission": "verified_free_tier", "llmReservationUsd": 0} if experimental else {}),
        }
        for delegation in trace.get("delegateRequests", []):
            emit_event(
                db,
                workspace_id=contract.workspace_id,
                event_type="studio.agent.delegated",
                aggregate_type="agent_task",
                aggregate_id=job.id,
                actor_id=user.id,
                correlation_id=job.correlation_id,
                payload={"parentRole": role, "role": "image", "stage": "planned", **delegation},
            )
    except Exception as error:
        db.rollback()
        db.refresh(job)
        code = str(error)
        cancelled = job.status in {"cancel_requested", "cancelled"}
        job.status, job.error_code = (
            "cancelled" if cancelled else "failed",
            (
                None
                if cancelled
                else code
                if isinstance(error, ValueError) and re.fullmatch(r"[a-z0-9_]{1,150}", code)
                else "agent_planning_failed"
            ),
        )
        job.error_message = "Não foi possível concluir o plano; nenhuma edição foi aplicada."
        job.result_payload = {
            "state": "cancelled" if cancelled else "failed",
            "inference": "gemini_experimental" if experimental else binding["mode"],
            "usage": response.get("usage") if response else None,
            "planningTimeMs": round((time.monotonic() - started) * 1000),
        }
    job.finished_at = datetime.now(UTC)
    emit_event(
        db,
        workspace_id=contract.workspace_id,
        event_type="studio.agent." + job.status,
        aggregate_type="agent_task",
        aggregate_id=job.id,
        actor_id=user.id,
        correlation_id=key,
        payload={
            "role": role,
            "errorCode": job.error_code,
            "commandCount": len((job.result_payload or {}).get("commands", [])),
            "externalCostUsd": 0,
        },
    )
    db.commit()
    return task_out(job, db)


def apply_task(db, document, task, request, user):
    if (
        task.document_id != document.id
        or task.workspace_id != document.workspace_id
        or task.job_type != "agent_plan"
        or task.status != "succeeded"
    ):
        raise ValueError("agent_task_not_applicable")
    if request.expected_revision != task.request_payload["documentRevision"]:
        raise ValueError("studio_document_conflict")
    output = AgentOutput.model_validate({key: task.result_payload[key] for key in ("commands", "rationale")})
    if not output.commands:
        raise ValueError("agent_operation_unsupported")
    return commit_commands(
        db,
        document,
        LocalCommandsRequest(expected_revision=request.expected_revision, commands=output.commands),
        user,
        "agent-apply:" + task.id,
        selected_layer_ids=task.request_payload.get("selectedLayerIds", []),
    )
