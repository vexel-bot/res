"""V2 orchestration uses the existing immutable plan events and material store."""

from datetime import UTC, datetime
from uuid import uuid4

from ...domain.studios.contextual_editing import digest
from ...domain.studios.contextual_editing_v2 import ContextualEditPlanV2
from ...domain.studios.contracts import AssetReferenceV1
from ...domain.studios.material_inspection import material_inspection_criteria
from .editorial_components import FAMILIES as COMPOSITION_FAMILIES
from .scene_compiler import COMPONENTS, compile_scenes

PROVIDER = "hyperframes.contextual-v2"


def omit_unresolved_optional_materials(direction, material_requests):
    """Build an executable direction without pretending optional media exists.

    The authored direction remains intact on the plan.  When a preferred asset
    was not acquired, this projection can bind its semantic shot/state to an
    already registered deterministic composition target (notably a viewport in
    ``format_transformation``).  If no such target exists, the optional shot is
    removed and the remaining shot intervals are closed.  Every omission is
    returned as evidence for the manifest.
    """

    executable = direction.model_copy(deep=True)
    requests = {
        (item.get("sceneId"), item.get("id")): item
        for item in material_requests
    }
    receipts = []
    for scene in executable.scenes:
        ordered_needs = list(scene.material_needs)
        removals = []
        for need_index, need in enumerate(ordered_needs):
            request = requests.get((scene.id, need.id))
            if not request or request.get("required") or request.get("status") == "resolved":
                continue
            target = next((item for item in scene.elements if item.id == need.target_id), None)
            if target is None:
                continue
            replacement = None
            owner = None
            for composition in scene.compositions:
                if composition.family != "format_transformation":
                    continue
                if need_index < len(composition.target_ids):
                    replacement = composition.target_ids[need_index]
                    owner = composition
                    break
            removals.append((need, target, replacement, owner))

        removed_ids = {target.id for _need, target, _replacement, _owner in removals}
        if not removed_ids:
            continue
        scene.material_needs = [need for need in scene.material_needs if need.target_id not in removed_ids]
        scene.elements = [element for element in scene.elements if element.id not in removed_ids]
        replacement_by_target = {
            target.id: replacement
            for _need, target, replacement, _owner in removals
            if replacement
        }
        for composition in scene.compositions:
            composition.target_ids = [
                replacement_by_target.get(target_id, target_id)
                for target_id in composition.target_ids
                if target_id not in removed_ids or target_id in replacement_by_target
            ]
            composition.target_ids = list(dict.fromkeys(composition.target_ids))
        for visual_state in scene.visual_states:
            visual_state.essential_element_ids = list(
                dict.fromkeys(
                    replacement_by_target.get(target_id, target_id)
                    for target_id in visual_state.essential_element_ids
                    if target_id not in removed_ids or target_id in replacement_by_target
                )
            )
            if any(target_id in removed_ids for target_id in visual_state.essential_element_ids):
                visual_state.expected_changes = ["A demonstração determinística executa a mudança de formato."]
        scene.visual_states = [state for state in scene.visual_states if state.essential_element_ids]
        for cue in scene.observation_cues:
            cue.target_ids = list(
                dict.fromkeys(
                    replacement_by_target.get(target_id, target_id)
                    for target_id in cue.target_ids
                    if target_id not in removed_ids or target_id in replacement_by_target
                )
            )
        scene.observation_cues = [cue for cue in scene.observation_cues if cue.target_ids]
        kept_shots = []
        for shot in scene.shot_plan:
            affected = any(target_id in removed_ids for target_id in shot.target_element_ids)
            shot.target_element_ids = list(
                dict.fromkeys(
                    replacement_by_target.get(target_id, target_id)
                    for target_id in shot.target_element_ids
                    if target_id not in removed_ids or target_id in replacement_by_target
                )
            )
            shot.material_requirement_ids = [
                requirement_id
                for requirement_id in shot.material_requirement_ids
                if requirement_id not in {need.id for need, *_rest in removals}
            ]
            if affected and shot.target_element_ids:
                shot.verification = [
                    "A mesma identidade de conteúdo permanece visível durante a mudança de viewport."
                ]
                shot.lighting = shot.lighting.model_copy(
                    update={"execution_mode": "deterministic_composite"}
                )
            if shot.target_element_ids:
                kept_shots.append(shot)
        if kept_shots:
            kept_shots[0].start_frame = 0
            for left, right in zip(kept_shots, kept_shots[1:], strict=False):
                left.end_frame_exclusive = right.start_frame
            kept_shots[-1].end_frame_exclusive = scene.duration_frames
        scene.shot_plan = kept_shots
        for need, target, replacement, owner in removals:
            receipts.append(
                {
                    "sceneId": scene.id,
                    "needId": need.id,
                    "targetId": target.id,
                    "replacementTargetId": replacement,
                    "componentId": owner.id if owner else None,
                    "reason": "unresolved_preferred_material_omitted_from_executable_direction",
                    "providerSubmission": False,
                }
            )
    return executable, receipts


def admit_source_timeline(db, source, manifest):
    """Keep existing speech and temporal dependencies intact, or expose a blocker."""
    from sqlalchemy import select

    from ...domain.studios.contracts import TranscriptDocumentV1
    from ...models import StudioTranscript
    from .contextual_editing import _block

    timeline = source.composition.media_timeline
    if timeline is None:
        return [], {}
    clips = [c for t in timeline.tracks if t.kind == "video" for c in t.clips if c.enabled]
    selections = [e for e in manifest["elements"] if e.get("source")]
    used = {e["source"]["assetId"] for e in selections}
    original = [c for c in clips if c.asset_id in used]
    blockers, bindings = [], {}
    if original and any(t.kind in {"caption", "mask", "marker"} for t in timeline.tracks):
        blockers.append(
            _block(
                "timeline",
                "editing_v2_temporal_dependencies_require_mapping",
                "As legendas, máscaras ou marcações existentes precisam de um mapeamento temporal antes da remontagem.",
            )
        )
    for clip in original:
        if sum(c.asset_id == clip.asset_id for c in clips) != 1 or not clip.source:
            blockers.append(
                _block(
                    clip.id, "editing_v2_source_mapping_ambiguous", "Identifique o intervalo de origem de cada cena."
                )
            )
            continue
        ranges = [
            (
                round(e["source"]["startSeconds"] * 1e6),
                round((e["source"]["startSeconds"] + e["source"]["durationSeconds"]) * 1e6),
            )
            for e in selections
            if e["source"]["assetId"] == clip.asset_id
        ]
        left = clip.source.start_microseconds
        right = left + clip.source.duration_microseconds
        if any(a <= left and b >= right for a, b in ranges):
            continue
        ref = next(a for a in source.assets if a.id == clip.asset_id)
        transcript = db.scalar(
            select(StudioTranscript)
            .where(
                StudioTranscript.workspace_id == source.workspace_id,
                StudioTranscript.asset_id == clip.asset_id,
                StudioTranscript.status == "reviewed",
                StudioTranscript.source_checksum_sha256 == ref.checksum,
            )
            .order_by(StudioTranscript.updated_at.desc())
        )
        if not transcript:
            blockers.append(
                _block(
                    clip.id,
                    "editing_v2_reviewed_transcript_required",
                    "A seleção altera um trecho existente. "
                    "Vincule uma transcrição revisada ou mantenha o trecho completo.",
                )
            )
            continue
        parsed = TranscriptDocumentV1.model_validate(transcript.transcript_document)
        spoken = [s for s in parsed.segments if s.start_microseconds < right and s.end_microseconds > left]
        if not spoken or any(
            not any(a <= s.start_microseconds and b >= s.end_microseconds for a, b in ranges) for s in spoken
        ):
            blockers.append(
                _block(
                    clip.id,
                    "editing_v2_selection_would_change_message",
                    "A seleção removeria ou cortaria uma fala. Preserve os segmentos completos, incluindo ressalvas.",
                )
            )
        bindings[transcript.id] = {
            "assetId": clip.asset_id,
            "revision": transcript.revision,
            "status": transcript.status,
            "digest": digest(transcript.transcript_document),
        }
    old_order = list(dict.fromkeys(c.asset_id for c in original))
    new_order = list(
        dict.fromkeys(
            e["source"]["assetId"]
            for e in sorted(selections, key=lambda e: e["startFrame"])
            if e["source"]["assetId"] in old_order
        )
    )
    if old_order != new_order:
        blockers.append(
            _block(
                "timeline",
                "editing_v2_order_requires_editorial_evidence",
                "A mudança de ordem precisa preservar as relações da fala. "
                "Mantenha a ordem de origem ou revise a proposta.",
            )
        )
    return blockers, bindings


def resolve_materials(db, document, direction):
    from ...models import LibraryAsset
    from .editing_resources import catalog, registered_sources
    from .material_discovery import discover_for_need

    def incorporate(asset_id):
        existing = next((a for a in document.assets if a.id == asset_id), None)
        if existing:
            return existing.rights_status == "verified" and bool(existing.checksum)
        asset = db.get(LibraryAsset, asset_id)
        if not asset or asset.workspace_id != document.workspace_id or asset.lifecycle_status != "active":
            return False
        meta = asset.object_metadata or {}
        if meta.get("materialAcquisition", {}).get("status") == "awaiting_inspection":
            return False
        if (
            not asset.storage_key
            or not asset.checksum_sha256
            or not meta.get("editingResource", {}).get("usageEvidence")
        ):
            return False
        if meta.get("derivation") and meta.get("visualReview") != "passed":
            return False
        document.assets.append(
            AssetReferenceV1(
                id=asset.id,
                media_type=asset.media_type,
                checksum=asset.checksum_sha256,
                version=asset.checksum_sha256,
                rights_status="verified",
                origin="generated" if meta.get("derivation") else "workspace",
                provenance=meta,
            )
        )
        return True

    requests = []
    discovery_cache = {}
    for scene in direction.scenes:
        targets = {e.id: e for e in [*scene.elements, *scene.audio]}
        for need in scene.material_needs:
            target = targets[need.target_id]
            field = {"asset": "asset_id", "mask": "mask_asset_id", "font": "font_asset_id"}[need.field]
            if not hasattr(target, field):
                raise ValueError("editing_v2_material_role_mismatch")
            selected = getattr(target, field)
            if selected and need.source_class == "generated_original":
                selected_asset = db.get(LibraryAsset, selected)
                procedural = (
                    (selected_asset.object_metadata or {}).get("proceduralComponent")
                    if selected_asset
                    else None
                )
                if procedural and procedural.get("kind") == "registered-procedural-icon":
                    # A deterministic registered component is a catalog resource,
                    # even when it satisfied a director's request to create an
                    # original-looking symbol. Persist the actual provenance.
                    need.source_class = "catalog"
            semantic_query = " ".join(
                part for part in (need.query, need.entity, need.action, need.appearance) if part
            )
            candidates = catalog(
                db,
                document.workspace_id,
                "" if selected else semantic_query,
                need.kind,
                asset_id=selected,
            )
            candidates = [c for c in candidates if not c.get("generationJobId") or c.get("reviewStatus") == "passed"]
            if need.official_required:
                candidates = [c for c in candidates if c.get("resource", {}).get("official") is True]
            project_asset_ids = {a.id for a in document.assets}
            if need.source_class == "project":
                candidates = [c for c in candidates if c["id"] in project_asset_ids]
            elif need.source_class == "brand_asset":
                candidates = [c for c in candidates if c.get("resource", {}).get("official") is True]
            elif need.source_class == "generated_original":
                candidates = [
                    c
                    for c in candidates
                    if c.get("resource", {}).get("official") is False and c.get("generationJobId")
                ]
            project_candidates = [c for c in candidates if c["id"] in project_asset_ids]
            preferred = project_candidates or candidates
            # Automated inspection is specific to a need; never reuse it as a global endorsement.
            admitted = []
            for candidate in preferred:
                asset = db.get(LibraryAsset, candidate["id"])
                acquisition = (asset.object_metadata or {}).get("materialAcquisition", {}) if asset else {}
                if acquisition or (direction.require_material_inspection and need.kind in {"image", "video"}):
                    required_seconds = (
                        target.duration_frames * direction.frame_rate.denominator / direction.frame_rate.numerator
                    )
                    if need.kind == "video" and need.duration_seconds is not None:
                        # A shot may deliberately hold the final source frame to
                        # cover a longer editorial interval.  Inspection only
                        # needs to cover the declared moving-source duration;
                        # the deterministic compositor owns the tail hold.
                        required_seconds = min(required_seconds, need.duration_seconds)
                    receipts = list(acquisition.get("inspectionReceipts") or [])
                    legacy_receipt = acquisition.get("inspectionReceipt")
                    if legacy_receipt:
                        receipts.append(legacy_receipt)
                    accepted_receipt = next(
                        (
                            receipt
                            for receipt in reversed(receipts)
                            if receipt.get("status") == "accepted"
                            and receipt.get("checksum") == asset.checksum_sha256
                            and receipt.get("request", {}).get("purpose") == need.purpose
                            and receipt.get("request", {}).get("criteria")
                            == material_inspection_criteria(need)
                            and (
                                need.kind != "video"
                                or receipt.get("request", {}).get("requiredSeconds", 0)
                                >= required_seconds
                            )
                            and receipt.get("request", {}).get("sourceStartSeconds", 0)
                            == getattr(target, "source_start_seconds", 0)
                        ),
                        None,
                    )
                    if accepted_receipt is None:
                        continue
                admitted.append(candidate)
            preferred = admitted
            chosen = preferred[0] if len(preferred) == 1 else None
            resolved = bool(chosen and incorporate(chosen["id"]))
            requests.append(
                {
                    "id": need.id,
                    "sceneId": scene.id,
                    "targetId": need.target_id,
                    "clipId": scene.id,
                    "kind": need.kind,
                    "required": need.required,
                    "requirementClass": need.requirement_class,
                    "preferredCriteria": need.preferred_criteria,
                    "componentId": need.component_id,
                    "exact": bool(selected),
                    "officialRequired": need.official_required,
                    "role": need.field if need.field != "asset" else "support",
                    "query": need.query,
                    "purpose": need.purpose,
                    "sourceClass": need.source_class,
                    "visualDescription": need.visual_description,
                    "entity": need.entity,
                    "action": need.action,
                    "appearance": need.appearance,
                    "orientation": need.orientation,
                    "durationSeconds": need.duration_seconds,
                    "alphaRequired": need.alpha_required,
                    "postProcessing": need.post_processing,
                    "fallbackBehavior": need.fallback_behavior,
                    "candidates": candidates,
                    "status": "resolved" if resolved else "awaiting_choice",
                    "assetId": chosen["id"] if resolved else None,
                    "sources": registered_sources(db, document.workspace_id, need.query, need.kind),
                    "acceptanceCriteria": need.acceptance_criteria,
                    "generationAllowed": not need.official_required and need.kind in {"image", "wardrobe"},
                    "discovery": discover_for_need(need, cache=discovery_cache) if not preferred else None,
                }
            )
            if resolved:
                setattr(target, field, chosen["id"])
        # Explicit IDs outside a requirement still pass tenant, provenance and file checks.
        for target in targets.values():
            for field in ("asset_id", "font_asset_id", "mask_asset_id"):
                if getattr(target, field, None):
                    incorporate(getattr(target, field))
    return requests


def preflight_v2(db, document):
    from .contextual_editing import asset_blockers

    problems = asset_blockers(db, document)
    # Unlike V1, V2 graphical layers are validated by their typed source scene and HyperFrames.
    return problems, 0


def ensure_visual_material_needs(direction):
    """Make unresolved visual media explicit before blueprint validation.

    This is a deterministic contract repair: it never chooses or fabricates a
    resource. It only turns an image/video element without an asset into a
    material request bound to that exact element, using the element's declared
    editorial purpose as the query and acceptance criterion.
    """
    from ...domain.studios.contextual_editing_v2 import EditorialMaterialV2

    repairs = promote_synthesized_composable_icons(direction)
    for scene in direction.scenes:
        indexed = {element.id: element for element in scene.elements}
        retained = []
        for need in scene.material_needs:
            if (
                need.kind == "image"
                and need.requirement_class == "composable"
                and need.component_id == "procedural-icon"
                and not need.alpha_required
            ):
                need.alpha_required = True
                repairs.append({
                    "sceneId": scene.id,
                    "needId": need.id,
                    "reason": "registered_icon_requires_transparent_surface",
                })
            target = indexed.get(need.target_id)
            if need.field == "asset" and target is not None and target.kind not in {"image", "video"}:
                repairs.append(
                    {
                        "sceneId": scene.id,
                        "needId": need.id,
                        "reason": "asset_need_targets_non_media_element",
                        "targetId": need.target_id,
                    }
                )
                continue
            retained.append(need)
        scene.material_needs = retained
        for element in scene.elements:
            if element.kind not in {"image", "video"} or element.asset_id:
                continue
            if any(n.target_id == element.id and n.field == "asset" for n in scene.material_needs):
                continue
            scene.material_needs.append(
                EditorialMaterialV2(
                    id="inspect-" + digest({"scene": scene.id, "element": element.id})[:24],
                    target_id=element.id,
                    kind=element.kind,
                    query=element.purpose[:500],
                    purpose=element.purpose,
                    acceptance_criteria=[element.purpose],
                )
            )
            repairs.append(
                {
                    "sceneId": scene.id,
                    "needId": scene.material_needs[-1].id,
                    "reason": "unresolved_media_requires_exact_material_request",
                    "targetId": element.id,
                }
            )
    return repairs


def promote_synthesized_composable_icons(direction):
    """Keep missing icon siblings on the scene's declared procedural route.

    A generated ``inspect-`` need has no editorial source choice of its own.
    This promotion is limited to scenes whose sole image component is the
    registered icon library and to subjects that library recognizes exactly.
    Anything else remains an ordinary unresolved material request.
    """
    from ...providers.studios.procedural_resources import discover as discover_procedural

    repairs = []
    for scene in direction.scenes:
        icon_needs = [
            need for need in scene.material_needs
            if need.kind == "image"
            and need.requirement_class == "composable"
            and need.component_id == "procedural-icon"
        ]
        if not icon_needs or any(
            need.kind == "image" and need.component_id not in {None, "procedural-icon"}
            for need in scene.material_needs
        ):
            continue
        requirement_ids = {need.blueprint_requirement_id for need in icon_needs}
        blueprint_requirement_id = next(iter(requirement_ids)) if len(requirement_ids) == 1 else None
        for need in scene.material_needs:
            if not need.id.startswith("inspect-") or need.kind != "image" or need.component_id:
                continue
            query = "ícone " + need.query
            match = discover_procedural(query, need.purpose, "image")
            if not match.get("candidates"):
                continue
            need.query = query
            need.source_class = "auto"
            need.requirement_class = "composable"
            need.component_id = "procedural-icon"
            need.blueprint_requirement_id = blueprint_requirement_id
            need.alpha_required = True
            repairs.append({
                "sceneId": scene.id,
                "needId": need.id,
                "reason": "synthesized_icon_need_bound_to_declared_component",
                "component": match["candidates"][0]["providerId"],
            })
    return repairs


def create_plan(db, record, direction, user, key):
    from . import contextual_editing as v1
    from .compatibility import record_to_contract
    from .editing_repertoire import (
        RESEARCH_EXECUTABLE_IDS,
        available_repertoire,
        planning_repertoire,
        research_operation_cards,
        store_technique,
    )
    from .editorial_operation_selection import evaluate_operation_bindings
    from .scene_compiler import current_execution_versions

    source = record_to_contract(record)
    direction = direction.model_copy(deep=True)
    input_request_digest = digest(direction)
    versions_were_explicit = direction.execution_versions is not None
    if direction.execution_versions is None:
        direction.execution_versions = current_execution_versions()
    request_digest = digest(direction)
    for event in v1._events(db, record.workspace_id, v1.PLAN_EVENT):
        if event.payload.get("idempotencyKey") == key:
            matches_request = event.payload.get("requestDigest") == request_digest or (
                not versions_were_explicit
                and event.payload.get("inputRequestDigest") == input_request_digest
            )
            if not matches_request or event.payload["plan"]["documentId"] != record.id:
                raise ValueError("editing_idempotency_conflict")
            return v1.get_plan(db, record.workspace_id, event.aggregate_id)
    for research_card in research_operation_cards():
        store_technique(db, record.workspace_id, research_card)
    if direction.require_material_inspection:
        ensure_visual_material_needs(direction)
    material_source = source.model_copy(deep=True)
    material_requests = resolve_materials(db, material_source, direction)
    executable_direction, optional_omissions = omit_unresolved_optional_materials(
        direction, material_requests
    )
    plan_id = str(uuid4())
    draft, graph, operations, manifest = compile_scenes(
        material_source, executable_direction, user.id, plan_id
    )
    manifest["omittedOptionalMaterials"] = optional_omissions
    from ...domain.studios.visual_audit import preflight_visual
    from .scene_compiler import prepare_direction

    page = material_source.composition.pages[0]
    manifest["visualAudit"] = preflight_visual(
        prepare_direction(executable_direction, page.width, page.height),
        graph,
        canvas_width=page.width,
        canvas_height=page.height,
    )
    source_blockers, source_transcripts = admit_source_timeline(db, source, manifest)
    blockers = [
        v1._block(m["elementId"], m["reason"], "Adicione o material verificado para esta cena.")
        for m in manifest["missingMaterials"]
    ]
    blockers.extend(
        v1._block(r["targetId"], "editing_material_required", r["purpose"])
        for r in material_requests
        if r["status"] == "awaiting_choice" and r["required"]
    )
    runtime, estimate = preflight_v2(db, draft)
    blockers.extend([*runtime, *source_blockers])
    operation_decisions = evaluate_operation_bindings(executable_direction, draft)
    manifest["operationDecisions"] = operation_decisions
    blockers.extend(
        v1._block(
            decision["sceneId"] + ":" + decision["techniqueId"],
            "editing_operation_prerequisite_missing",
            " ".join([*decision["reasons"], decision["alternative"]]),
        )
        for decision in operation_decisions if decision["status"] == "blocked"
    )
    researched_ids = {technique.id for technique in research_operation_cards()}
    non_executable = researched_ids - RESEARCH_EXECUTABLE_IDS
    blockers.extend(
        v1._block(
            identifier,
            "editing_operation_knowledge_only",
            "Esta técnica está catalogada, mas ainda não possui executor qualificado.",
        )
        for identifier in {t for s in direction.scenes for t in s.technique_ids} & non_executable
    )
    techniques = planning_repertoire(
        db,
        record.workspace_id,
        direction.intent.objective + " " + direction.intent.script,
        [*COMPONENTS, *(op for spec in COMPONENTS.values() for op in spec["operations"])],
        [t for s in direction.scenes for t in s.technique_ids],
        material_kinds={a.media_type.split("/")[0] for a in draft.assets},
    )
    requested_ids = {t for s in direction.scenes for t in s.technique_ids}
    capabilities = {
        *COMPONENTS,
        *COMPOSITION_FAMILIES,
        *(op for spec in COMPONENTS.values() for op in spec["operations"]),
    }
    requested_references = [
        t
        for t in available_repertoire(db, record.workspace_id)
        if t.id in requested_ids and set(t.required_capabilities) <= capabilities
    ]
    techniques = list({t.id: t for t in [*techniques, *requested_references]}.values())
    known = {t.id for t in techniques} | capabilities
    blockers.extend(
        v1._block(t, "editing_reference_unavailable", "A referência não está disponível para este plano.")
        for t in {t for s in direction.scenes for t in s.technique_ids} - known
    )
    draft.composition.narrative["editorialV2"]["motionGraph"] = graph.model_dump(mode="json", by_alias=True)
    plan = ContextualEditPlanV2(
        id=plan_id,
        workspace_id=record.workspace_id,
        document_id=record.id,
        document_revision=record.revision,
        source_digest=v1._source_digest(source),
        source_assets={a.id: a.checksum for a in source.assets},
        source_transcripts=source_transcripts,
        intent=direction.intent,
        direction=direction,
        motion_graph=graph,
        operations=operations,
        blockers=blockers,
        status="awaiting_choice" if blockers else "ready",
        estimated_cost_cents=estimate,
        cost_basis="processing-measured-after-render;generation-tracked-separately",
        draft_document=draft,
        manifest=manifest,
        material_requests=material_requests,
        editorial_evidence=[
            {
                "type": "reference",
                "techniqueId": t.id,
                "techniqueDigest": digest(t),
                "sources": t.sources,
                "evidenceType": t.evidence_type,
                "causalPerformanceClaim": False,
            }
            for t in techniques
        ] + [{"type": "operation_decision", **decision} for decision in operation_decisions],
        created_at=datetime.now(UTC),
    )
    v1._save(
        db,
        record,
        plan,
        user,
        {
            "idempotencyKey": key,
            "inputRequestDigest": input_request_digest,
            "requestDigest": request_digest,
        },
    )
    db.commit()
    return plan


def recompile_plan(db, record, plan_id, request, user, key):
    """Compile a plan again with current pinned components, without new editorial authorship."""
    from . import contextual_editing as v1

    replay_key = "recompile:" + key
    for event in reversed(v1._events(db, record.workspace_id, v1.PLAN_EVENT)):
        if event.payload.get("idempotencyKey") != replay_key:
            continue
        saved = event.payload.get("plan", {})
        provenance = saved.get("manifest", {}).get("recompilation") or {}
        if provenance:
            if (saved.get("documentId") != record.id or provenance.get("sourcePlanId") != plan_id
                    or event.payload.get("recompileRequestDigest") != digest(request)):
                raise ValueError("editing_idempotency_conflict")
            return v1.get_plan(db, record.workspace_id, saved["id"])

    db.refresh(record, with_for_update=True)
    source_plan = v1.get_plan(db, record.workspace_id, plan_id)
    if not isinstance(source_plan, ContextualEditPlanV2) or source_plan.document_id != record.id:
        raise ValueError("editing_v2_plan_required")
    if record.revision != request.expected_document_revision:
        raise ValueError("editing_document_conflict")
    if source_plan.revision != request.expected_plan_revision:
        raise ValueError("editing_plan_revision_conflict")
    direction = source_plan.direction.model_copy(deep=True)
    direction.expected_document_revision = record.revision
    # Recompilation deliberately selects the current executable versions. The
    # previous version remains immutable in the source plan's manifest.
    direction.execution_versions = None
    derivative = create_plan(db, record, direction, user, replay_key)
    if not derivative.manifest.get("recompilation"):
        derivative.manifest["recompilation"] = {
            "kind": "compiler_only",
            "sourcePlanId": source_plan.id,
            "sourcePlanRevision": source_plan.revision,
            "sourceCompilerVersion": source_plan.manifest.get("compilerVersion"),
            "editorialDirectionChanged": False,
        }
        derivative.revision += 1
        v1._save(
            db,
            record,
            derivative,
            user,
            {"recompiledFromPlanId": source_plan.id, "idempotencyKey": replay_key,
             "recompileRequestDigest": digest(request)},
        )
        db.commit()
    return derivative


def reconcile_registered_component_blockers(db, document, plan, user):
    """Remove blockers made obsolete by current executable and admission checks."""
    from ...models import LibraryAsset
    from . import contextual_editing as v1
    from .contextual_editing import generated_asset_admitted
    from .scene_compiler import COMPONENTS

    removable = set()
    reasons = set()
    for blocker in plan.blockers:
        if blocker.code == "editing_reference_unavailable" and blocker.target_id in COMPONENTS:
            removable.add(blocker.id)
            reasons.add("renderer_component_is_executable")
        elif blocker.code == "source_admission_required":
            asset = db.get(LibraryAsset, blocker.target_id)
            if asset and asset.workspace_id == document.workspace_id and generated_asset_admitted(db, asset):
                removable.add(blocker.id)
                reasons.add("generated_asset_passed_current_admission")
    if not removable:
        return plan
    plan.blockers = [blocker for blocker in plan.blockers if blocker.id not in removable]
    if not plan.blockers and all(request["status"] == "resolved" for request in plan.material_requests):
        plan.status = "ready"
    plan.revision += 1
    plan.editorial_evidence.append(
        {
            "type": "contract_repair",
            "version": "res.current-capability-blockers.v2",
            "removedBlockerIds": sorted(removable),
            "reasons": sorted(reasons),
        }
    )
    v1._save(db, document, plan, user, {"repairVersion": "res.current-capability-blockers.v2"})
    db.commit()
    return plan


def revise_direction(source, selected, feedback):
    if not selected or not selected <= {s.id for s in source.scenes}:
        raise ValueError("editing_feedback_beat_unknown")
    direction = source.model_copy(deep=True)
    changed = False
    for scene in direction.scenes:
        if scene.id not in selected:
            continue
        composed_targets = {target for component in scene.compositions for target in component.target_ids}
        if feedback == "mais calmo":
            for component in scene.compositions:
                if component.family == "continuity":
                    continue
                count = (
                    len(component.target_ids)
                    if component.family == "sequence"
                    else component.repeat_count
                    if component.family == "repetition"
                    else 1
                )
                limit = min(
                    (scene.duration_frames - 1) // count,
                    *(e.duration_frames - 1 for e in scene.elements if e.id in component.target_ids),
                )
                revised = min(limit, round(component.action_frames * 1.5))
                changed = changed or revised != component.action_frames
                component.action_frames = revised
        for element in scene.elements:
            if feedback == "menos texto" and element.text_role == "support" and element.concise_text:
                if element.concise_text not in element.text:
                    raise ValueError("editing_v2_concise_text_requires_source_excerpt")
                element.text = element.concise_text
                changed = True
            elif feedback == "mais calmo":
                if element.id in composed_targets:
                    continue
                for animation in element.animations:
                    last = animation.keyframes[-1].frame
                    factor = min(1.5, (element.duration_frames - 1) / max(last, 1))
                    animation.keyframes = [
                        k.model_copy(update={"frame": round(k.frame * factor)}) for k in animation.keyframes
                    ]
                element.reveal_frames = min(element.duration_frames, max(round(element.reveal_frames * 1.5), 24))
                changed = True
            elif feedback == "mostrar melhor o produto" and element.kind in {"image", "video"}:
                element.object_fit = "contain"
                changed = True
    if not changed:
        raise ValueError("editing_feedback_requires_matching_material")
    return direction


def feedback(db, document, plan, request, user):
    from . import contextual_editing as v1
    from .compatibility import record_to_contract

    direction = revise_direction(plan.direction, set(request.beat_ids), request.feedback)
    previous_blockers = list(plan.blockers)
    direction.expected_document_revision = document.revision
    draft, graph, operations, manifest = compile_scenes(record_to_contract(document), direction, user.id, plan.id)
    draft.composition.narrative["editorialV2"]["motionGraph"] = graph.model_dump(mode="json", by_alias=True)
    plan.direction, plan.motion_graph, plan.operations, plan.manifest = direction, graph, operations, manifest
    plan.draft_document = draft
    plan.blockers, plan.estimated_cost_cents = preflight_v2(db, draft)
    plan.blockers.extend(
        v1._block(m["elementId"], m["reason"], "Material verificado necessário.") for m in manifest["missingMaterials"]
    )
    plan.blockers = list({b.id: b for b in [*previous_blockers, *plan.blockers]}.values())
    plan.blockers.extend(
        v1._block(r["targetId"], "editing_material_required", r["purpose"])
        for r in plan.material_requests
        if r["status"] == "awaiting_choice" and r.get("required", True)
    )
    plan.status = "awaiting_choice" if plan.blockers else "ready"
    plan.revision += 1
    plan.evaluation = {"technical": "pending", "audiovisual": "pending", "human": "pending"}
    v1._save(db, document, plan, user, {"feedback": request.model_dump(mode="json", by_alias=True)})
    db.commit()
    return plan


def select_material(db, document, plan_id, request, user, key):
    from . import contextual_editing as v1

    plan = v1._locked_plan(db, document, plan_id, request.expected_plan_revision)
    if not isinstance(plan, ContextualEditPlanV2) or plan.status == "applied":
        raise ValueError("editing_v2_material_choice_requires_unapplied_plan")
    direction = plan.direction.model_copy(deep=True)
    direction.expected_document_revision = document.revision
    from ...domain.studios.production_timing import bind_declared_material_durations

    direction, _ = bind_declared_material_durations(direction)
    matches = [(s, n) for s in direction.scenes for n in s.material_needs if n.id == request.need_id]
    if len(matches) != 1:
        raise ValueError("editing_v2_material_need_unknown")
    scene, need = matches[0]
    target = next(e for e in [*scene.elements, *scene.audio] if e.id == need.target_id)
    setattr(
        target, {"asset": "asset_id", "font": "font_asset_id", "mask": "mask_asset_id"}[need.field], request.asset_id
    )
    return create_plan(db, document, direction, user, key)
