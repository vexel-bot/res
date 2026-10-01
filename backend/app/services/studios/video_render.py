from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
from collections.abc import Callable
from contextlib import ExitStack
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...domain.studios.contracts import (
    CreateGenerationJobRequest,
    CreateVideoRenderJobRequest,
    CreativeDocumentV1,
    RenderedVideoArtifactV1,
    VideoRenderRequestV1,
    VideoRenderResultV1,
    VideoTechnicalQualityPolicyV1,
)
from ...domain.studios.motion import (
    MotionGraphEvaluationV1,
    MotionGraphProjectionV1,
    MotionGraphV1,
    project_motion_graph,
)
from ...models import (
    CreativeDocument,
    LibraryAsset,
    StudioGenerationJob,
    StudioMediaIngest,
    StudioMotionGraph,
    User,
)
from ...providers.studios.video_quality import VIDEO_TECHNICAL_QUALITY_PROVIDERS
from ...providers.studios.video_render import VIDEO_RENDER_PROVIDERS
from ..object_storage import get_object_storage, object_key
from .compatibility import record_to_contract
from .editorial_review import require_editorial_render_readiness
from .jobs import create_job
from .kernel import emit_event

CONTEXTUAL_RENDERERS = {"builtin.ffmpeg-contextual-v1", "hyperframes.contextual-v2", "motion-canvas.contextual-v1", "remotion.contextual-v1", "remotion.contextual-v2"}
CONTEXTUAL_V2_RENDERERS = {"hyperframes.contextual-v2", "motion-canvas.contextual-v1", "remotion.contextual-v1", "remotion.contextual-v2"}


def create_video_render_job(
    db: Session,
    document: CreativeDocument,
    request: CreateVideoRenderJobRequest,
    idempotency_key: str,
    user: User,
) -> tuple[StudioGenerationJob, bool]:
    if request.provider in CONTEXTUAL_RENDERERS:
        from .contextual_editing import lock_editing_budget

        lock_editing_budget(db, document.workspace_id)
        from ...models import Workspace

        db.execute(select(Workspace).where(Workspace.id == document.workspace_id).with_for_update()).scalar_one()
    db.refresh(document, with_for_update=True)
    if document.workspace_id != request.workspace_id or document.id != request.document_id:
        raise ValueError("studio_render_document_mismatch")
    if document.revision != request.expected_document_revision or document.version != request.expected_document_version:
        raise ValueError("studio_document_conflict")
    snapshot = record_to_contract(document)
    if snapshot.content_type != "video" or snapshot.composition.media_timeline is None:
        raise ValueError("video_media_timeline_required")
    contextual_plan = None
    if request.provider in CONTEXTUAL_RENDERERS:
        from .contextual_editing import require_render_plan, reserve_cost

        contextual_plan = require_render_plan(db, document, snapshot, request.contextual_plan_id)
        is_v2 = contextual_plan.schema_version == "studio.contextual-edit-plan.v2"
        if is_v2 != (request.provider in CONTEXTUAL_V2_RENDERERS):
            raise ValueError("editing_render_plan_provider_mismatch")
        native_renderer = (snapshot.composition.narrative.get("editorialV2") or {}).get("renderer")
        if native_renderer and request.provider != native_renderer:
            raise ValueError("editing_native_renderer_binding_conflict")
        reserve_cost(db, document, contextual_plan, user, idempotency_key)
        editorial_plan_id = None
    else:
        editorial_plan_id = require_editorial_render_readiness(db, document)
    if request.provider not in VIDEO_RENDER_PROVIDERS:
        raise ValueError("video_render_provider_unavailable")
    if request.provider == "builtin.ffmpeg-ugc-v1":
        timeline = snapshot.composition.media_timeline
        assert timeline is not None
        source_asset_ids = {
            clip.asset_id for track in timeline.tracks if track.kind == "video" for clip in track.clips if clip.enabled
        }
        if not source_asset_ids or len(source_asset_ids) > 8:
            raise ValueError("video_render_source_asset_count_unsupported")
        for source_asset_id in source_asset_ids:
            source_asset = db.scalar(
                select(LibraryAsset).where(
                    LibraryAsset.id == source_asset_id,
                    LibraryAsset.workspace_id == document.workspace_id,
                    LibraryAsset.lifecycle_status == "active",
                )
            )
            source_ingest = db.scalar(
                select(StudioMediaIngest).where(
                    StudioMediaIngest.workspace_id == document.workspace_id,
                    StudioMediaIngest.asset_id == source_asset_id,
                    StudioMediaIngest.status == "ready",
                )
            )
            metadata = source_asset.object_metadata if source_asset else {}
            if (
                not source_asset
                or not source_ingest
                or metadata.get("derivedFromAssetId")
                or metadata.get("derivation")
            ):
                raise ValueError("video_render_original_ingest_required")
        for asset_ref in snapshot.assets:
            if asset_ref.id in source_asset_ids:
                continue
            sound = db.scalar(
                select(LibraryAsset).where(
                    LibraryAsset.id == asset_ref.id,
                    LibraryAsset.workspace_id == document.workspace_id,
                    LibraryAsset.lifecycle_status == "active",
                )
            )
            sound_ingest = db.scalar(
                select(StudioMediaIngest).where(
                    StudioMediaIngest.workspace_id == document.workspace_id,
                    StudioMediaIngest.asset_id == asset_ref.id,
                    StudioMediaIngest.status == "ready",
                )
            )
            if (
                not sound
                or not (sound.media_type or "").startswith("audio/")
                or not sound_ingest
                or not asset_ref.checksum
                or asset_ref.checksum != sound.checksum_sha256
            ):
                raise ValueError("video_render_sound_ingest_required")
    available_pages = {page.id for page in snapshot.composition.pages}
    page_ids = request.page_ids or [page.id for page in snapshot.composition.pages]
    if not page_ids or not set(page_ids) <= available_pages:
        raise ValueError("video_render_page_not_found")
    render_request = VideoRenderRequestV1(
        workspace_id=request.workspace_id,
        document_id=document.id,
        document_revision=document.revision,
        document_version=document.version,
        page_ids=page_ids,
        asset_ids=[asset.id for asset in snapshot.assets],
        output=request.output,
        correlation_id=request.correlation_id or f"video-render:{document.id}:{document.version}",
    )
    motion_projection: MotionGraphProjectionV1 | None = None
    if request.motion_graph_id:
        motion_record = db.scalar(
            select(StudioMotionGraph).where(
                StudioMotionGraph.id == request.motion_graph_id,
                StudioMotionGraph.workspace_id == request.workspace_id,
                StudioMotionGraph.document_id == document.id,
                StudioMotionGraph.status == "reviewed",
            )
        )
        if motion_record is None:
            raise ValueError("video_render_reviewed_motion_graph_required")
        if (
            motion_record.document_revision != document.revision
            or motion_record.graph_digest_sha256.lower() != (request.motion_graph_digest_sha256 or "").lower()
        ):
            raise ValueError("video_render_motion_graph_conflict")
        graph = MotionGraphV1.model_validate(motion_record.graph)
        evaluation = MotionGraphEvaluationV1.model_validate(motion_record.evaluation)
        motion_projection = project_motion_graph(
            graph,
            "hyperframes",
            evaluation,
            reduced_motion=request.reduced_motion,
        )
    job_request = CreateGenerationJobRequest(
        workspace_id=request.workspace_id,
        document_id=document.id,
        job_type="video_render",
        provider=request.provider,
        request={
            "renderRequest": render_request.model_dump(by_alias=True, mode="json"),
            "documentSnapshot": snapshot.model_dump(by_alias=True, mode="json"),
            "editorialPlanId": editorial_plan_id,
            "contextualPlanId": contextual_plan.id if contextual_plan else None,
            "contextualPlanRevision": contextual_plan.revision if contextual_plan else None,
            "motionProjection": (
                motion_projection.model_dump(by_alias=True, mode="json") if motion_projection is not None else None
            ),
        },
        correlation_id=render_request.correlation_id,
    )
    return create_job(db, job_request, idempotency_key, user)


def _existing_result(db: Session, job: StudioGenerationJob) -> dict | None:
    records = db.scalars(
        select(LibraryAsset).where(
            LibraryAsset.workspace_id == job.workspace_id,
            LibraryAsset.asset_type == "video",
            LibraryAsset.lifecycle_status == "active",
        )
    ).all()
    for asset in records:
        metadata = asset.object_metadata or {}
        if metadata.get("generationJobId") == job.id and metadata.get("derivation") == "video_render":
            result = metadata.get("videoRenderResult")
            if isinstance(result, dict):
                return VideoRenderResultV1.model_validate(result).model_dump(by_alias=True, mode="json")
    return None


def execute_video_render(
    db: Session,
    job: StudioGenerationJob,
    progress: Callable[[int], None],
    is_cancelled: Callable[[], bool],
) -> dict:
    existing = _existing_result(db, job)
    if existing:
        return existing
    render_request = VideoRenderRequestV1.model_validate(job.request_payload.get("renderRequest"))
    document = CreativeDocumentV1.model_validate(job.request_payload.get("documentSnapshot"))
    motion_projection = (
        MotionGraphProjectionV1.model_validate(job.request_payload.get("motionProjection"))
        if job.request_payload.get("motionProjection") is not None
        else None
    )
    if (
        render_request.workspace_id != job.workspace_id
        or render_request.document_id != job.document_id
        or document.workspace_id != job.workspace_id
        or document.document_id != job.document_id
        or document.revision != render_request.document_revision
        or document.version != render_request.document_version
    ):
        raise ValueError("video_render_snapshot_mismatch")
    provider = VIDEO_RENDER_PROVIDERS.get(job.provider)
    if not provider:
        raise ValueError("video_render_provider_unavailable")
    if is_cancelled():
        return {"cancelled": True}
    current_document = db.get(CreativeDocument, job.document_id, populate_existing=True)
    if current_document is None or current_document.workspace_id != job.workspace_id:
        raise ValueError("video_render_document_missing")
    if job.provider in CONTEXTUAL_RENDERERS:
        from .contextual_editing import require_render_plan

        contextual_plan = require_render_plan(
            db, current_document, document, job.request_payload.get("contextualPlanId")
        )
        if contextual_plan.revision != job.request_payload.get("contextualPlanRevision"):
            raise ValueError("editing_plan_revision_conflict")
        if job.provider in CONTEXTUAL_V2_RENDERERS:
            from .scene_compiler import executable_composition_digest

            timeline = document.composition.media_timeline
            expected_digest = (contextual_plan.manifest.get("hashes") or {}).get(
                "executableComposition"
            )
            digest_required = contextual_plan.manifest.get("compilerVersion") == "res.scene-compiler.v2.3"
            if digest_required and (not expected_digest or timeline is None):
                raise ValueError("editing_executable_composition_digest_required")
            if expected_digest and timeline is not None:
                actual_digest = executable_composition_digest(
                    document.composition.pages[0], timeline, contextual_plan.motion_graph
                )
                if actual_digest != expected_digest:
                    raise ValueError("editing_executable_composition_conflict")
    else:
        require_editorial_render_readiness(
            db,
            current_document,
            document,
            expected_plan_id=job.request_payload.get("editorialPlanId"),
        )
    suffix = ".mp4" if render_request.output.format == "mp4" else ".webm"
    media_type = "video/mp4" if suffix == ".mp4" else "video/webm"
    storage = get_object_storage()
    stored = None
    source_bindings: list[dict[str, str | None]] = []
    with ExitStack() as stack:
        materialized_assets: dict[str, Path] = {}
        for asset_ref in document.assets:
            asset = db.scalar(
                select(LibraryAsset).where(
                    LibraryAsset.id == asset_ref.id,
                    LibraryAsset.workspace_id == job.workspace_id,
                    LibraryAsset.lifecycle_status == "active",
                )
            )
            if not asset or not asset.storage_key:
                raise ValueError("video_render_asset_not_stored")
            if (
                asset_ref.checksum
                and asset.checksum_sha256
                and asset_ref.checksum.lower() != asset.checksum_sha256.lower()
            ):
                raise ValueError("video_render_asset_checksum_mismatch")
            asset_storage = get_object_storage(asset.storage_backend or "local")
            materialized_assets[asset.id] = stack.enter_context(asset_storage.materialize(asset.storage_key))
            with materialized_assets[asset.id].open("rb") as source_bytes:
                actual_checksum = hashlib.file_digest(source_bytes, "sha256").hexdigest()
            if asset.checksum_sha256 and actual_checksum != asset.checksum_sha256.lower():
                raise ValueError("video_render_asset_checksum_mismatch")
            if asset_ref.checksum and actual_checksum != asset_ref.checksum.lower():
                raise ValueError("video_render_asset_checksum_mismatch")
            source_bindings.append(
                {
                    "assetId": asset.id,
                    "checksumSha256": actual_checksum,
                    "role": "canonical-source",
                }
            )
        temporary = stack.enter_context(tempfile.TemporaryDirectory(prefix="clicko-video-render-"))
        output_path = Path(temporary) / f"render{suffix}"
        try:
            from ...providers.studios.heavy_media_lease import heavy_media_lease

            with heavy_media_lease("video_render", job.id):
                if motion_projection is None:
                    encoded = provider.render(
                        document,
                        render_request,
                        materialized_assets,
                        output_path,
                        progress,
                        is_cancelled,
                    )
                else:
                    encoded = provider.render(
                        document,
                        render_request,
                        materialized_assets,
                        output_path,
                        progress,
                        is_cancelled,
                        motion_projection=motion_projection,
                    )
        except InterruptedError:
            return {"cancelled": True}
        if is_cancelled():
            return {"cancelled": True}
        progress(84)
        timeline = document.composition.media_timeline
        assert timeline is not None
        expected_duration_ms = round(
            timeline.duration_frames * timeline.frame_rate.denominator / timeline.frame_rate.numerator * 1000
        )
        quality_evaluation = VIDEO_TECHNICAL_QUALITY_PROVIDERS["builtin.ffmpeg-qc-v1"].evaluate(
            output_path,
            expected=render_request.output,
            expected_duration_ms=expected_duration_ms,
            policy=VideoTechnicalQualityPolicyV1(),
            is_cancelled=is_cancelled,
        )
        if is_cancelled():
            return {"cancelled": True}
        progress(90)
        if job.provider in CONTEXTUAL_RENDERERS:
            from .contextual_editing import verify_render_receipt

            operation_checks = verify_render_receipt(contextual_plan, encoded)
            db.refresh(current_document)
            checked_plan = require_render_plan(db, current_document, document, contextual_plan.id)
            if checked_plan.revision != contextual_plan.revision:
                raise ValueError("editing_plan_revision_conflict")
        audiovisual_observations = None
        visual_audit = None
        if job.provider in CONTEXTUAL_V2_RENDERERS:
            from ...providers.studios.editorial_observation import observe_render

            try:
                rate = contextual_plan.direction.frame_rate
                audiovisual_observations = observe_render(
                    output_path,
                    scenes=contextual_plan.direction.scenes,
                    frame_rate=rate.numerator / rate.denominator,
                )
            except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
                audiovisual_observations = {
                    "status": "unavailable",
                    "reason": type(error).__name__,
                    "humanReview": "pending",
                }
            from ...domain.studios.contextual_editing_v2 import ContextualPlanRequestV2
            from ...providers.studios.visual_state_observation import observe_visual_states

            try:
                executable_direction = ContextualPlanRequestV2.model_validate(
                    contextual_plan.manifest.get("executableDirection")
                    or contextual_plan.direction.model_dump(mode="json", by_alias=True)
                )
                hashes = contextual_plan.manifest.get("hashes") or {}
                visual_audit = observe_visual_states(
                    output_path,
                    executable_direction,
                    contextual_plan.motion_graph,
                    renderer_checks=encoded.renderer_checks,
                    expected_direction_digest=hashes.get("executableDirection"),
                    expected_composition_digest=hashes.get("executableComposition"),
                    legacy_preparation="executableDirection" not in contextual_plan.manifest,
                )
            except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
                visual_audit = {"status": "unavailable", "reason": type(error).__name__, "human": "pending"}
        key = object_key(job.workspace_id, "exports", suffix)
        stored = storage.put_file(
            output_path,
            key=key,
            media_type=media_type,
            metadata={
                "workspace-id": job.workspace_id,
                "role": "video-render",
                "document-id": document.document_id,
                "generation-job-id": job.id,
                "provider": encoded.provider,
            },
        )
    if is_cancelled():
        storage.delete(stored.key)
        return {"cancelled": True}
    progress(92)
    try:
        asset = LibraryAsset(
            workspace_id=job.workspace_id,
            title=f"{document.title} — render v{document.version}",
            asset_type="video",
            tags=[
                "studio-render",
                f"document-version-{document.version}",
                f"technical-qc-{quality_evaluation.status}",
            ],
            campaign_id=document.campaign_ref.id if document.campaign_ref else None,
            content_id=document.post_ref.id if document.post_ref else None,
            storage_key=stored.key,
            storage_backend=stored.backend,
            media_type=stored.media_type,
            size_bytes=stored.size_bytes,
            checksum_sha256=stored.checksum_sha256,
            object_metadata={
                **stored.metadata,
                "schemaVersion": "studio.asset-lineage.v1",
                "derivation": "video_render",
                "generationJobId": job.id,
                "documentId": document.document_id,
                "documentRevision": document.revision,
                "documentVersion": document.version,
                "providerVersion": encoded.provider_version,
                "renderedFromOriginal": job.provider == "builtin.ffmpeg-ugc-v1",
                "sourceAssetBindings": source_bindings,
                "documentSnapshotSha256": hashlib.sha256(
                    json.dumps(
                        document.model_dump(by_alias=True, mode="json"),
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ).encode("utf-8")
                ).hexdigest(),
                "compositionProjection": {
                    "schemaVersion": "studio.ugc-composition-projection.v1",
                    "renderedLayerIds": encoded.rendered_layer_ids,
                    "renderedCaptionTrackIds": encoded.rendered_caption_track_ids,
                    "warnings": encoded.warnings,
                },
                "contextualEditing": (
                    {
                        "planId": contextual_plan.id,
                        "planRevision": contextual_plan.revision,
                        "operations": [o.model_dump(mode="json", by_alias=True) for o in contextual_plan.operations],
                        "verification": "encoded-and-probed",
                        "operationChecks": operation_checks,
                        "editorialReview": "pending",
                        "rendererChecks": encoded.renderer_checks,
                        "manifest": getattr(contextual_plan, "manifest", None),
                    }
                    if job.provider in CONTEXTUAL_RENDERERS
                    else None
                ),
                "qualityEvaluation": quality_evaluation.model_dump(by_alias=True, mode="json"),
                "audiovisualObservations": audiovisual_observations,
                "visualAudit": visual_audit,
                "workerExecutionContext": job.worker_execution_context,
                "renderRequest": render_request.model_dump(by_alias=True, mode="json"),
            },
        )
        db.add(asset)
        db.flush()
        result = VideoRenderResultV1(
            job_id=job.id,
            workspace_id=job.workspace_id,
            document_id=document.document_id,
            document_revision=document.revision,
            document_version=document.version,
            provider=encoded.provider,
            provider_version=encoded.provider_version,
            artifact=RenderedVideoArtifactV1(
                asset_id=asset.id,
                storage_uri=f"/api/v1/assets/{asset.id}/content",
                media_type=media_type,
                checksum_sha256=stored.checksum_sha256,
                size_bytes=stored.size_bytes,
                width=encoded.width,
                height=encoded.height,
                duration_ms=encoded.duration_ms,
                fps=encoded.fps,
                video_codec=encoded.video_codec,
                audio_codec=encoded.audio_codec,
            ),
            render_duration_ms=encoded.render_duration_ms,
            frames_rendered=encoded.frames_rendered,
            peak_rss_mb=encoded.peak_rss_mb,
            rendered_layer_ids=encoded.rendered_layer_ids,
            rendered_caption_track_ids=encoded.rendered_caption_track_ids,
            quality_evaluation=quality_evaluation,
            worker_execution_context=job.worker_execution_context,
            warnings=encoded.warnings,
            completed_at=datetime.now(UTC),
        )
        asset.object_metadata = {
            **asset.object_metadata,
            "videoRenderResult": result.model_dump(by_alias=True, mode="json"),
        }
        if job.provider in CONTEXTUAL_V2_RENDERERS:
            from . import contextual_editing as editing

            contextual_plan.evaluation = {
                "technical": {
                    "status": quality_evaluation.status,
                    "coverage": operation_checks,
                    "rendererChecks": encoded.renderer_checks,
                    "jobId": job.id,
                    "assetId": asset.id,
                    "checksum": stored.checksum_sha256,
                    "renderDurationMs": encoded.render_duration_ms,
                    "framesRendered": encoded.frames_rendered,
                },
                "audiovisual": "pending",
                "observations": audiovisual_observations,
                "visualAudit": visual_audit,
                "human": "pending",
            }
            editing._save(db, current_document, contextual_plan, None, {"evaluationJobId": job.id})
        emit_event(
            db,
            workspace_id=job.workspace_id,
            event_type="studio.video.render_ready",
            aggregate_type="creative_document",
            aggregate_id=document.document_id,
            correlation_id=job.correlation_id,
            actor_id=None,
            payload={
                "jobId": job.id,
                "documentVersion": document.version,
                "assetId": asset.id,
                "checksumSha256": stored.checksum_sha256,
                "qualityStatus": quality_evaluation.status,
                "workerManifestDigest": ((job.worker_execution_context or {}).get("manifestDigestSha256")),
            },
        )
        db.commit()
        return result.model_dump(by_alias=True, mode="json")
    except Exception:
        db.rollback()
        if stored is not None:
            storage.delete(stored.key)
        raise
