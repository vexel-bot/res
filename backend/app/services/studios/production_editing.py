"""Reference-driven editing through Clicko's canonical composition, without a scene template.

Only registered local media and validated editor operations can execute. Model review
is evidence for a person, never an audience test or an automatic creative approval.
"""

import io
import json
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from PIL import Image, ImageOps
from pydantic import Field, ValidationError

from ...domain.studios.agents import AgentOutput
from ...domain.studios.contracts import CreativeCompositionV1, StudioContract
from ...domain.studios.local_composition import LocalLayerStyle
from ...domain.studios.timeline_editor import VisualMotion
from ...providers.studios import timeline_ffmpeg
from . import ad_copy_workflow, llm_connections, motion_claude, motion_editorial, timeline_editor
from .craft import scoped_asset, workspace_files
from .motion_editorial_review import _raw
from .scene_direction import _request

VERSION = "clicko.open-edit.v1"


def bounded_tokens(context, media_count, config, ceiling, requested):
    """Use the same conservative input bound as the transport before allocating output."""
    from .scene_direction import _wire_schema

    context = {**context, "wireSchema": _wire_schema(context["outputSchema"]), "maxOutputTokens": requested}
    size = (
        len(json.dumps(context, ensure_ascii=False).encode())
        + len(json.dumps(context["wireSchema"]).encode())
        + 2048
        + media_count * 6000
    )
    remaining = ceiling - size * config["inputUsdPerMillion"] / 1e6 - 0.002
    tokens = min(requested, config["maxOutputTokens"], int(remaining * 1e6 / config["outputUsdPerMillion"]))
    if tokens < 1024:
        raise ValueError("scene_direction_stage_budget_exceeded")
    return tokens


class EditorialDecision(StudioContract):
    start_frame: int = Field(ge=0)
    end_frame: int = Field(gt=0)
    viewer_understands: str = Field(min_length=5, max_length=300)
    executed_ids: list[str] = Field(min_length=1, max_length=24)
    reference_observation: str = Field(min_length=5, max_length=500)


class OpenCut(StudioContract):
    composition: CreativeCompositionV1
    decisions: list[EditorialDecision] = Field(min_length=1, max_length=24)
    gaps: list[str] = Field(default_factory=list, max_length=16)
    rationale: str = Field(min_length=5, max_length=2000)


class Finding(StudioContract):
    time_ms: int = Field(ge=0)
    dimension: Literal["hook", "product", "continuity", "legibility", "reference", "cta"]
    severity: Literal["minor", "major"]
    evidence: str = Field(min_length=10, max_length=600)


class CutReview(StudioContract):
    findings: list[Finding] = Field(default_factory=list, max_length=16)
    limitations: str = Field(min_length=10, max_length=1000)
    revision: OpenCut | None = None


def prepare(db, record, contract, experiment):
    """Preflight before reserving money: product/copy, scoped references and duration."""
    copy = ad_copy_workflow.planning_context(db, record)
    purpose = experiment.purpose or "advertisement"
    if purpose == "advertisement" and copy["status"] != "approved":
        raise ValueError("open_edit_approved_product_and_copy_required")
    timeline = contract.composition.media_timeline
    page = contract.composition.pages[0]
    if page.width * page.height > 1280 * 1280:
        raise ValueError("open_edit_preview_dimensions_exceed_local_budget")
    if not timeline or timeline.duration_frames * timeline.frame_rate.denominator / timeline.frame_rate.numerator > 30:
        raise ValueError("open_edit_preview_duration_exceeds_30_seconds")
    if (
        sum(
            scoped_asset(db, record.workspace_id, asset.id, asset.checksum).size_bytes or 0 for asset in contract.assets
        )
        > 100 * 1024**2
    ):
        raise ValueError("open_edit_project_media_exceeds_local_budget")
    references = []
    for reference in experiment.references or []:
        asset = scoped_asset(db, record.workspace_id, reference.asset_id)
        if (asset.object_metadata or {}).get("rightsStatus") == "restricted":
            raise ValueError("open_edit_reference_restricted")
        if not (asset.media_type or "").startswith(("image/", "video/")):
            raise ValueError("open_edit_reference_requires_image_or_video")
        if (asset.size_bytes or 0) > 100 * 1024**2:
            raise ValueError("open_edit_reference_too_large")
        entry = {
            **reference.model_dump(mode="json", by_alias=True),
            "checksum": asset.checksum_sha256,
            "mediaType": asset.media_type,
        }
        if asset.media_type.startswith("video/"):
            with workspace_files(db, record, None, extra_asset_ids=[asset.id]) as (_, params, _):
                probe = timeline_ffmpeg.probe(params["media"][0]["path"])
                duration = float(probe["format"]["duration"])
                if reference.start_seconds + reference.duration_seconds > duration + 0.01:
                    raise ValueError("open_edit_reference_range_exceeds_source")
        references.append(entry)
    if not references:
        raise ValueError("open_edit_visual_reference_required")
    return {"version": VERSION, "purpose": purpose, "copy": copy, "references": references}


def verify_bound_context(db, record, contract, snapshot):
    if timeline_editor.digest(ad_copy_workflow.planning_context(db, record)) != timeline_editor.digest(
        snapshot["copy"]
    ):
        raise ValueError("open_edit_copy_revision_conflict")
    for reference in snapshot["references"]:
        scoped_asset(db, record.workspace_id, reference["assetId"], reference["checksum"])


def sample_assets(db, record, entries, directory, prefix):
    """One labelled contact sheet per asset. References are never copied into the ad."""
    media, coverage = [], []
    with workspace_files(db, record, None, extra_asset_ids=[e["assetId"] for e in entries]) as (_, params, _):
        paths = {entry["assetId"]: entry["path"] for entry in params["media"]}
        for entry in entries:
            path = paths[entry["assetId"]]
            if entry["mediaType"].startswith("video/"):
                duration = float(timeline_ffmpeg.probe(path)["format"]["duration"])
                start = entry.get("startSeconds", 0)
                length = min(entry.get("durationSeconds", duration), duration - start)
                times = [round(start + max(0, length - 0.05) * i / 5, 4) for i in range(6)]
                images = [
                    Image.open(
                        io.BytesIO(
                            _raw(
                                path,
                                [
                                    "-ss",
                                    str(second),
                                    "-an",
                                    "-frames:v",
                                    "1",
                                    "-vf",
                                    "scale=360:640:force_original_aspect_ratio=decrease",
                                    "-c:v",
                                    "mjpeg",
                                    "-f",
                                    "image2pipe",
                                ],
                            )
                        )
                    ).convert("RGB")
                    for second in times
                ]
            else:
                times = []
                with Image.open(path) as source:
                    images = [ImageOps.exif_transpose(source).convert("RGB")]
            if len(images) == 1:
                strip = ImageOps.contain(images[0], (1080, 1280))
            else:
                strip = Image.new("RGB", (360 * min(3, len(images)), 640 * ((len(images) + 2) // 3)), "#151515")
                for index, image in enumerate(images):
                    thumb = ImageOps.contain(image, (360, 640))
                    strip.paste(thumb, ((index % 3) * 360, (index // 3) * 640))
            output = Path(directory) / f"{prefix}-{len(media)}.jpg"
            for quality in (85, 70, 55, 40):
                strip.save(output, quality=quality)
                if output.stat().st_size <= 512000:
                    break
            media.append((output, "image/jpeg"))
            coverage.append(
                {
                    "imageIndex": len(media) - 1,
                    "assetId": entry["assetId"],
                    "checksum": entry["checksum"],
                    "sampleSecondsApproximate": times,
                    "audioObserved": False,
                    "order": "left_to_right_then_next_row",
                    "imageSize": list(strip.size),
                }
            )
    return media, coverage


def validate_cut(db, contract, cut, snapshot=None):
    from .agent_orchestrator import proposed_document

    output = AgentOutput.model_validate(
        {
            "commands": [
                {
                    "id": "composition.replace",
                    "params": {"composition": cut.composition.model_dump(mode="json", by_alias=True)},
                }
            ],
            "rationale": cut.rationale,
        }
    )
    candidate = proposed_document(db, contract, output.commands)
    old, new = contract.composition, candidate.composition
    if (old.pages[0].width, old.pages[0].height) != (new.pages[0].width, new.pages[0].height):
        raise ValueError("open_edit_keep_project_dimensions")
    timeline = new.media_timeline
    if not timeline or timeline.duration_frames * timeline.frame_rate.denominator / timeline.frame_rate.numerator > 30:
        raise ValueError("open_edit_preview_duration_exceeds_30_seconds")
    if snapshot and snapshot["purpose"] == "advertisement":
        cta = snapshot["copy"].get("data", {}).get("cta", "").strip()
        texts = [
            str(layer.properties.get("text", ""))
            for layer in new.pages[0].layers
            if layer.kind == "text" and layer.visible
        ]
        texts += [cue.text for track in timeline.tracks if track.kind == "caption" for cue in track.cues]

        def normalized(value):
            return " ".join(value.casefold().split())

        if not cta or not any(normalized(cta) in normalized(text) for text in texts):
            raise ValueError("open_edit_approved_cta_missing")
    ranges = {}
    for layer in new.pages[0].layers:
        if layer.visible and layer.opacity > 0:
            style = LocalLayerStyle.model_validate(layer.properties)
            ranges[layer.id] = [
                (style.start_frame, style.start_frame + (style.duration_frames or timeline.duration_frames))
            ]
    for track in timeline.tracks:
        intervals = []
        for item in getattr(track, "clips", []) or getattr(track, "cues", []):
            if getattr(item, "enabled", True):
                interval = (item.timeline.start_frame, item.timeline.start_frame + item.timeline.duration_frames)
                ranges[item.id] = [interval]
                intervals.append(interval)
        ranges[track.id] = intervals
    for track in timeline.tracks:
        if track.kind == "mask":
            ranges[track.id] = ranges.get(track.target_track_id, [])
    previous_end = 0
    for decision in cut.decisions:
        if not previous_end <= decision.start_frame < decision.end_frame <= timeline.duration_frames:
            raise ValueError("open_edit_decision_range_invalid")
        active = {
            identifier
            for identifier, spans in ranges.items()
            if any(start < decision.end_frame and end > decision.start_frame for start, end in spans)
        }
        if not set(decision.executed_ids) <= active:
            raise ValueError("open_edit_direction_not_executed")
        previous_end = decision.end_frame
    return output, candidate


def direct(
    db,
    record,
    job,
    connection,
    adapter,
    contract,
    snapshot,
    materials,
    instruction,
    effort,
    format_hint,
    staged_previews=None,
):
    """One budgeted planning + rendered review cycle; no fixed palette, layout or scene count."""
    kb = motion_editorial.knowledge()
    roles = materials["roles"]
    flags = motion_editorial._flags(contract.composition, roles, {a.id: a.media_type for a in contract.assets})
    cards = [
        c
        for c in kb["cards"]
        if (format_hint == "auto" or format_hint in c["formats"]) and motion_editorial._support(c, flags)
    ][:8]
    evidence = {
        "variant": "orchestrated",
        "format": format_hint,
        "knowledgeVersion": kb["version"],
        "knowledgeDigest": timeline_editor.digest(kb),
        "cardIds": [c["id"] for c in cards],
        "materialSnapshot": materials,
        "materialDigest": motion_editorial.fingerprint(materials),
        "gaps": [],
        "receipts": [],
        "humanVerdict": "inconclusive",
        "repairCount": 0,
        "preview": {"status": "not_requested"},
        "openEditing": {
            "version": VERSION,
            "purpose": snapshot["purpose"],
            "copyRevision": snapshot["copy"].get("revision"),
            "creativeStatus": "awaiting_human_review",
            "audienceValidation": "not_performed",
        },
    }
    cfg = connection.config
    if cfg["inputUsdPerMillion"] < 4 or cfg["outputUsdPerMillion"] < 20:
        raise ValueError("editorial_claude_cut_pricing_invalid")
    tokens = min(32000 if effort == "xhigh" else 16000, cfg["maxOutputTokens"])
    times = {}

    def cancelled():
        db.refresh(job, attribute_names=["status"])
        return job.status != "running"

    with tempfile.TemporaryDirectory() as directory:
        started = time.monotonic()
        references, coverage = sample_assets(db, record, snapshot["references"], directory, "reference")
        sources = []
        for asset in contract.assets:
            if len(sources) == 2:
                break
            if asset.media_type.startswith(("image/", "video/")):
                sources.append({"assetId": asset.id, "mediaType": asset.media_type, "checksum": asset.checksum})
        source_media, source_coverage = sample_assets(db, record, sources, directory, "source")
        for item in source_coverage:
            item["imageIndex"] += len(references)
        evidence["openEditing"].update(referenceCoverage=coverage, materialCoverage=source_coverage)
        times["prepareMediaMs"] = round((time.monotonic() - started) * 1000)
        common = {
            "editorialMotion": True,
            "openEditing": True,
            "editorialCutEffort": effort,
            "maxOutputTokens": tokens,
            "maxPromptChars": 240000,
            "instruction": instruction,
            "productAndCopy": snapshot["copy"],
            "purpose": snapshot["purpose"],
            "knowledgeCards": cards,
            "project": contract.model_dump(mode="json", by_alias=True),
            "layerStyleSchema": LocalLayerStyle.model_json_schema(by_alias=True),
            "visualMotionSchema": VisualMotion.model_json_schema(by_alias=True),
            "capabilities": {
                "canvasLayers": 24,
                "timelineTracks": 16,
                "keyframesPerItem": 32,
                "maxSeconds": 30,
                "localLayerKinds": ["text", "shape", "image"],
                "shapeKinds": ["rectangle", "ellipse"],
                "canvasAboveAllTimelineTracks": True,
                "depthType": (
                    "Order background video, caption track, then aligned masked foreground video. "
                    "Canvas text is always above timeline."
                ),
                "missingOperations": (
                    "No arbitrary code, bezier paths, new media generation, narration synthesis "
                    "or implicit person segmentation. Report missing assets/operations."
                ),
            },
        }
        context = {
            **common,
            "outputSchema": OpenCut.model_json_schema(by_alias=True),
            "referenceCoverage": coverage,
            "materialCoverage": source_coverage,
            "materialRoles": roles,
            "structuredPlanningInstruction": (
                "Create an executable edit: complete canonical composition, decisions, gaps and rationale. "
                "Choose scene count, typography, colors, layers, track order, sources, timing and keyframes. "
                "There is no three-scene template. Choose a visual action that proves the approved benefit. "
                "Study the actual reference sheets. Connect an observation to each executed decision, "
                "and adapt the technique to this product. Preserve approved claims, offer conditions and CTA. "
                "A feature tour does not replace a commercial concept. Use only project asset IDs. "
                "Reference sheets are study material, never automatically authorized ad footage. "
                "Keep locked items and canvas dimensions. Describe missing proof or media rather than inventing it. "
                "Use valid local-layer properties, captions, masks, crop and motion schema; no executable code. "
                "Every decision must name IDs that actually execute it. Use increasing nonoverlapping scene ranges. "
                "Still samples cannot demonstrate sound, exact synchronization or spectator comprehension."
            ),
        }
        # Reserve from the real request size, including duplicated portable schema and image allowance.
        from .scene_direction import _wire_schema

        size = len(
            json.dumps({**context, "wireSchema": _wire_schema(context["outputSchema"])}, ensure_ascii=False).encode()
        )
        size += (
            len(json.dumps(_wire_schema(context["outputSchema"])).encode())
            + 2048
            + 6000 * (len(references) + len(source_media))
        )
        context["maxOutputTokens"] = bounded_tokens(context, len(references) + len(source_media), cfg, 1.0, tokens)
        llm_connections.reserve_request(
            db,
            job,
            connection,
            size,
            context["maxOutputTokens"],
            max_amount=motion_claude.CUT_BUDGET_USD,
            reserve_full=True,
        )
        db.commit()
        started = time.monotonic()
        raw, total = _request(db, job, adapter, context, references + source_media, "open_direction", cfg, 1.0)
        try:
            cut = OpenCut.model_validate_json(raw)
            output, candidate = validate_cut(db, contract, cut, snapshot)
        except ValueError as error:
            issues = (
                [{"field": list(item["loc"]), "type": item["type"]} for item in error.errors(include_input=False)]
                if isinstance(error, ValidationError)
                else [{"code": str(error)[:150]}]
            )
            repair_context = {
                **context,
                "editorialCutEffort": "high",
                "invalidProposal": raw,
                "validationIssues": issues,
                "structuredPlanningInstruction": (
                    "Repair this invalid canonical proposal once. Return the full OpenCut JSON. "
                    "Preserve the approved meaning and visual intention. Fix the stated schema/geometry errors, "
                    "use only supported local operations and project assets. Do not emit Markdown or executable code."
                ),
            }
            repair_context["maxOutputTokens"] = bounded_tokens(
                repair_context,
                len(references) + len(source_media),
                cfg,
                motion_claude.CUT_BUDGET_USD - total,
                min(tokens, 16000),
            )
            raw, total = _request(
                db,
                job,
                adapter,
                repair_context,
                references + source_media,
                "open_contract_repair",
                cfg,
                motion_claude.CUT_BUDGET_USD - total,
            )
            cut = OpenCut.model_validate_json(raw)
            output, candidate = validate_cut(db, contract, cut, snapshot)
            evidence["openEditing"]["contractRepairIssues"] = issues
        times["directionMs"] = round((time.monotonic() - started) * 1000)
        evidence["receipts"].append(
            {
                "stage": "direction",
                "status": "executed_proposal",
                "beats": [{"startFrame": d.start_frame, "endFrame": d.end_frame} for d in cut.decisions],
            }
        )
        summary = {}
        draft_path = Path(directory) / "first-cut.mp4"
        started = time.monotonic()
        strips, frames, checksum = motion_claude._cut_samples(
            db,
            record,
            candidate,
            evidence,
            directory,
            cancelled,
            summary=summary,
            render_copy=draft_path,
            long_edge=640,
        )
        times["draftRenderMs"] = round((time.monotonic() - started) * 1000)
        # Four ordered strips at most: two reference sheets + two actual render sheets.
        review_context = {
            **common,
            "maxOutputTokens": tokens if effort == "xhigh" else min(tokens, 12000),
            "outputSchema": CutReview.model_json_schema(by_alias=True),
            "project": candidate.model_dump(mode="json", by_alias=True),
            "referenceCoverage": coverage,
            "renderFrames": frames[:6],
            "technicalFindings": summary.get("findings", []),
            "structuredPlanningInstruction": (
                "Review the actual rendered proposal against the reference sheets and approved product/copy. "
                "Images: references first, then chronological render strips (three frames each). "
                "Use timestamped findings with observable evidence for hook, product proof, continuity, mobile text, "
                "reference technique and CTA. Report major issues honestly; a technical pass is not creative approval. "
                "Optionally return one complete localized revision with executable IDs. No audience scores. "
                "State limits: still frames do not prove audio sync, continuous motion, or comprehension. "
                "A revision will be rendered again and requires human review."
            ),
        }
        started = time.monotonic()
        try:
            review_context["maxOutputTokens"] = bounded_tokens(
                review_context,
                len(references) + len(strips[:2]),
                cfg,
                motion_claude.CUT_BUDGET_USD - total,
                review_context["maxOutputTokens"],
            )
            raw, total = _request(
                db,
                job,
                adapter,
                review_context,
                references + strips[:2],
                "open_render_review",
                cfg,
                motion_claude.CUT_BUDGET_USD - total,
            )
            review = CutReview.model_validate_json(raw)
            review_receipt = review.model_dump(mode="json", by_alias=True, exclude={"revision"})
            if review.revision:
                try:
                    revised_output, revised_candidate = validate_cut(db, contract, review.revision, snapshot)
                except ValueError:
                    review_receipt["revisionApplied"] = False
                    review_receipt["revisionRejected"] = (
                        "Revision failed canonical validation; first valid proposal preserved."
                    )
                else:
                    output, candidate, cut = revised_output, revised_candidate, review.revision
                    review_receipt["revisionApplied"] = True
                    review_receipt["scope"] = "First render reviewed; revised render awaits human review."
        except ValueError as error:
            if not (
                isinstance(error, ValidationError)
                or str(error).startswith("llm_provider_")
                or str(error) == "scene_direction_stage_budget_exceeded"
            ):
                raise
            # The paid response is already metered. Retain the valid first edit without fabricating approval.
            review_receipt = {
                "status": "inconclusive",
                "limitations": "A revisão não concluiu em formato válido; primeira proposta preservada.",
            }
        times["modelReviewMs"] = round((time.monotonic() - started) * 1000)
        evidence["receipts"][0]["beats"] = [
            {"startFrame": d.start_frame, "endFrame": d.end_frame} for d in cut.decisions
        ]
        evidence["receipts"].extend(
            [
                {
                    "stage": "design_and_edit",
                    "status": "canonical_proposal_validated",
                    "layerCount": len(candidate.composition.pages[0].layers),
                    "trackCount": len(candidate.composition.media_timeline.tracks),
                },
                {"stage": "model_editorial_review", "status": "evidence_only", "renderChecksum": checksum},
            ]
        )
        evidence["gaps"] = [{"code": "editorial_gap", "detail": gap} for gap in cut.gaps]
        evidence["openEditing"].update(
            decisions=[d.model_dump(mode="json", by_alias=True) for d in cut.decisions],
            modelReview={**review_receipt, "renderChecksum": checksum, "sampledFrames": frames[:6]},
            stageTimesMs=times,
            contextDigest=timeline_editor.digest(snapshot),
        )
        evidence["claude"] = {
            "provider": "anthropic",
            "model": motion_claude.MODEL,
            "cutEffort": effort,
            "generationBudgetUsd": motion_claude.CUT_BUDGET_USD,
            "measuredCostUsd": total,
        }
        if staged_previews is not None and draft_path.is_file():
            from .motion_editorial_review import persist_preview

            draft_receipt = dict(summary)
            persist_preview(db, record, job, draft_receipt, draft_path, staged_previews)
            evidence["openEditing"]["draftPreview"] = draft_receipt
    return output, evidence


def record_verdict(db, document, task, request, user):
    from .agent_orchestrator import task_out
    from .compatibility import record_to_contract
    from .contextual_editing import lock_editing_budget
    from .kernel import emit_event

    lock_editing_budget(db, document.workspace_id)
    db.refresh(document)
    db.refresh(task)
    if (
        task.document_id != document.id
        or task.workspace_id != document.workspace_id
        or task.job_type != "agent_plan"
        or task.status != "succeeded"
    ):
        raise ValueError("agent_task_not_applicable")
    if (
        document.revision != request.expected_revision
        or request.expected_revision != task.request_payload["documentRevision"]
    ):
        raise ValueError("studio_document_conflict")
    snapshot = task.request_payload.get("openEditSnapshot")
    if not snapshot:
        raise ValueError("open_edit_task_required")
    criteria = {"hook", "continuity", "legibility", "reference"}
    if snapshot["purpose"] == "advertisement":
        criteria |= {"product", "cta"}
    if request.verdict == "approved" and any(request.criteria.get(key) != "passed" for key in criteria):
        raise ValueError("open_edit_approval_requires_all_editorial_criteria")
    contract = record_to_contract(document)
    verify_bound_context(db, document, contract, snapshot)
    motion_editorial.verify_bound_materials(db, document, contract, task.request_payload["materialDigest"])
    editorial = (task.result_payload or {}).get("editorial", {})
    preview = editorial.get("preview", {})
    if preview.get("renderChecksum") != request.render_checksum or (
        request.verdict == "approved" and preview.get("status") != "passed_technical"
    ):
        raise ValueError("open_edit_preview_conflict")
    decision = {
        "verdict": request.verdict,
        "notes": request.notes,
        "criteria": request.criteria,
        "renderChecksum": request.render_checksum,
        "proposalDigest": timeline_editor.digest(task.result_payload["commands"]),
        "actorId": user.id,
        "at": datetime.now(UTC).isoformat(),
    }
    task.result_payload = {
        **task.result_payload,
        "editorial": {
            **editorial,
            "humanVerdict": request.verdict,
            "openEditing": {**editorial["openEditing"], "creativeStatus": request.verdict, "humanReview": decision},
        },
    }
    emit_event(
        db,
        workspace_id=document.workspace_id,
        event_type="studio.agent.editorial_reviewed",
        aggregate_type="agent_task",
        aggregate_id=task.id,
        actor_id=user.id,
        correlation_id=task.id,
        payload=decision,
    )
    db.commit()
    return task_out(task, db)
