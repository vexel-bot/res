from __future__ import annotations

from uuid import NAMESPACE_URL, uuid5

from ...domain.studios.contextual_editing_v2 import ContextualEditPlanV2
from ...domain.studios.contracts import CreateGenerationJobRequest
from ...domain.studios.hybrid_video import HybridSelectionRequestV1, select_hybrid_profile
from ...domain.studios.scene_generation import (
    SceneGenerationAdmissionRequestV1,
    SceneGenerationRequestV1,
    SceneGenerationRequestV2,
)
from ...models import CreativeDocument, LibraryAsset, StudioGenerationJob
from ...providers.studios.local_diffusion import capability, preflight, submit_or_resume, verify_artifact
from ..object_storage import get_object_storage, object_key
from .contextual_editing import latest_plan
from .jobs import create_job


def _validate_hybrid_execution_binding(request: SceneGenerationRequestV2) -> None:
    if not request.execution_binding or not request.selection_policy:
        return
    from .hybrid_video import hybrid_capability_manifest

    selection = select_hybrid_profile(
        hybrid_capability_manifest(),
        request.selection_policy,
        HybridSelectionRequestV1(
            capability="generative_video",
            operation=request.operation,
            duration_seconds=request.duration_seconds,
            remaining_api_budget_usd=request.selection_policy.maximum_api_spend_usd,
            requested_parameters=request.execution_binding.effective_parameters,
        ),
    )
    if (
        not selection.execution_binding
        or selection.execution_binding.binding_digest_sha256
        != request.execution_binding.binding_digest_sha256
    ):
        raise ValueError("scene_generation_execution_binding_changed")


def scene_generation_capability():
    return capability()


def create_scene_generation_job(db, record, request: SceneGenerationRequestV1 | SceneGenerationRequestV2, user, key):
    if record.revision != request.expected_document_revision:
        raise ValueError("studio_document_conflict")
    plan = latest_plan(db, record)
    if not isinstance(plan, ContextualEditPlanV2):
        raise ValueError("scene_generation_contextual_plan_required")
    scene = next((item for item in plan.direction.scenes if item.id == request.scene_id), None)
    if not scene:
        raise ValueError("scene_generation_scene_binding_conflict")
    requirement = next((item for item in scene.material_needs if item.id == request.requirement_id), None)
    if not requirement:
        raise ValueError("scene_generation_requirement_binding_conflict")
    if requirement.kind != "video":
        raise ValueError("scene_generation_requirement_type_mismatch")
    if isinstance(request, SceneGenerationRequestV2):
        _validate_hybrid_execution_binding(request)
    payload = request.model_dump(mode="json", by_alias=True)
    payload.update(
        {
            "contextualPlanId": plan.id,
            "contextualPlanRevision": plan.revision,
            "sourceDocumentRevision": record.revision,
            "sourceAssets": {asset.id: asset.checksum for asset in plan.draft_document.assets},
            "executionId": str(uuid5(NAMESPACE_URL, f"res:{record.workspace_id}:{record.id}:{key}")),
        }
    )
    provider_name = (
        "local.wan21-diffusers"
        if request.profile_id == "wan21-t2v-local-experimental-v1"
        else "local." + request.profile_id
    )
    return create_job(
        db,
        CreateGenerationJobRequest(
            workspace_id=record.workspace_id,
            document_id=record.id,
            job_type="scene_generation",
            provider=provider_name,
            request=payload,
            correlation_id="scene-generation:" + plan.id,
        ),
        key,
        user,
    )


def execute_scene_generation(db, job, progress, is_cancelled):
    record = db.get(CreativeDocument, job.document_id)
    payload = job.request_payload
    if not record or record.workspace_id != job.workspace_id:
        raise ValueError("scene_generation_document_missing")
    if record.revision != payload["sourceDocumentRevision"]:
        raise ValueError("scene_generation_document_revision_conflict")
    profile_id = payload["profileId"]
    if payload.get("schemaVersion") == "studio.scene-generation-request.v2" and payload.get(
        "executionBinding"
    ):
        request_fields = {
            key: value
            for key, value in payload.items()
            if key
            not in {
                "contextualPlanId",
                "contextualPlanRevision",
                "sourceDocumentRevision",
                "sourceAssets",
                "executionId",
            }
        }
        _validate_hybrid_execution_binding(SceneGenerationRequestV2.model_validate(request_fields))
    admission = preflight() if profile_id == "wan21-t2v-local-experimental-v1" else preflight(profile_id=profile_id)
    progress(10)
    if admission.get("status") != "admitted":
        return {
            "schemaVersion": "studio.scene-generation-receipt.v1",
            "status": "blocked_resources",
            "executionId": payload["executionId"],
            "preflight": admission,
            "modelDownloadStarted": False,
            "incorporated": False,
        }
    job.result_payload = {
        "status": "submitting",
        "executionId": payload["executionId"],
        "submissionStarted": True,
    }
    db.commit()
    worker_payload = {
        key: value
        for key, value in payload.items()
        if key
        in {
            "schemaVersion",
            "operation",
            "prompt",
            "seed",
            "durationSeconds",
            "profileId",
            "cameraIntent",
        }
    }
    receipt = submit_or_resume(payload["executionId"], worker_payload, is_cancelled)
    if receipt.get("cancelled"):
        return receipt
    if receipt.get("status") != "candidate_generated":
        return {
            "schemaVersion": "studio.scene-generation-receipt.v1",
            **receipt,
            "executionId": payload["executionId"],
            "incorporated": False,
        }
    db.refresh(record)
    if record.revision != payload["sourceDocumentRevision"]:
        raise ValueError("scene_generation_document_revision_conflict")
    artifact = receipt["artifact"]
    path = verify_artifact(payload["executionId"], artifact["path"], artifact["checksumSha256"])
    storage = get_object_storage()
    stored = storage.put_file(
        path,
        key=object_key(job.workspace_id, "temporary", ".mp4"),
        media_type="video/mp4",
        metadata={"generation-job-id": job.id, "provider": job.provider},
    )
    progress(95)
    return {
        "schemaVersion": "studio.scene-generation-receipt.v1",
        **receipt,
        "candidate": {
            "storageKey": stored.key,
            "storageBackend": stored.backend,
            "mediaType": stored.media_type,
            "sizeBytes": stored.size_bytes,
            "checksumSha256": stored.checksum_sha256,
            "officialBrandAsset": False,
        },
        "artifact": None,
        "incorporated": False,
        "admission": "pending_visual_review",
    }


def review_scene_candidate(db, job: StudioGenerationJob, request: SceneGenerationAdmissionRequestV1, user):
    if job.job_type != "scene_generation":
        raise ValueError("scene_generation_job_missing")
    record = db.get(CreativeDocument, job.document_id)
    if (
        not record
        or record.revision != request.expected_document_revision
        or record.revision != job.request_payload.get("sourceDocumentRevision")
    ):
        raise ValueError("scene_generation_document_revision_conflict")
    plan = latest_plan(db, record)
    if (
        not isinstance(plan, ContextualEditPlanV2)
        or plan.id != job.request_payload.get("contextualPlanId")
        or plan.revision != job.request_payload.get("contextualPlanRevision")
        or {asset.id: asset.checksum for asset in plan.draft_document.assets}
        != job.request_payload.get("sourceAssets", {})
    ):
        raise ValueError("scene_generation_plan_binding_conflict")
    scene = next(
        (item for item in plan.direction.scenes if item.id == job.request_payload.get("sceneId")),
        None,
    )
    requirement = next(
        (
            item
            for item in (scene.material_needs if scene else [])
            if item.id == job.request_payload.get("requirementId")
        ),
        None,
    )
    if requirement is None or requirement.kind != "video":
        raise ValueError("scene_generation_requirement_binding_conflict")
    result = dict(job.result_payload or {})
    if job.status != "succeeded" or not result.get("candidate"):
        raise ValueError("scene_generation_candidate_unavailable")
    current = result.get("admission")
    desired = "accepted" if request.decision == "accept" else "rejected"
    if current in {"accepted", "rejected"}:
        if current != desired:
            raise ValueError("scene_generation_admission_conflict")
        return job
    candidate = result["candidate"]
    storage = get_object_storage()
    if not storage.exists(candidate["storageKey"]):
        raise ValueError("scene_generation_candidate_storage_missing")
    if request.decision == "accept":
        asset = db.query(LibraryAsset).filter(LibraryAsset.storage_key == candidate["storageKey"]).one_or_none()
        if asset is None:
            asset = LibraryAsset(
                workspace_id=job.workspace_id,
                title=f"Cena gerada — {job.request_payload['sceneId']}",
                asset_type="video",
                tags=["studio-generated-scene", "synthetic-media", job.request_payload["profileId"]],
                storage_key=candidate["storageKey"],
                storage_backend=candidate["storageBackend"],
                media_type=candidate["mediaType"],
                size_bytes=candidate["sizeBytes"],
                checksum_sha256=candidate["checksumSha256"],
                object_metadata={
                    "schemaVersion": "studio.generated-scene-lineage.v1",
                    "derivation": "local_diffusion",
                    "visualReview": "passed",
                    "generationJobId": job.id,
                    "documentId": job.document_id,
                    "documentRevision": request.expected_document_revision,
                    "sceneId": job.request_payload["sceneId"],
                    "requirementId": job.request_payload["requirementId"],
                    "profileId": job.request_payload["profileId"],
                    "syntheticContent": True,
                    "officialBrandAsset": False,
                    "editingResource": {
                        "kind": "video",
                        "description": job.request_payload["prompt"],
                        "tags": ["generated-original", "local-diffusion", "inspection-pending"],
                        "sourceUrl": None,
                        "usageEvidence": (
                            "Original synthetic media generated locally for this editorial requirement; "
                            "not an official brand asset."
                        ),
                        "version": result.get("profileDigestSha256", "1"),
                        "official": False,
                        "framing": (job.request_payload.get("cameraIntent") or {}).get("type", "static"),
                        "motionDescription": job.request_payload["prompt"],
                        "editorialFunction": "Generated for requirement " + job.request_payload["requirementId"],
                        "technical": {
                            "durationMicroseconds": round(
                                float(result.get("durationProducedSeconds") or 0) * 1_000_000
                            ),
                            "generationReceipt": {
                                "executionId": result.get("executionId"),
                                "profileId": job.request_payload["profileId"],
                                "profileDigestSha256": result.get("profileDigestSha256"),
                                "artifactChecksumSha256": candidate["checksumSha256"],
                            },
                        },
                    },
                    "materialAcquisition": {
                        "provider": job.provider,
                        "providerId": job.request_payload["profileId"],
                        "checksum": candidate["checksumSha256"],
                        "status": "awaiting_contextual_inspection",
                        "humanReview": "passed",
                        "acceptanceCriteria": requirement.acceptance_criteria,
                    },
                    "reviewedBy": user.id,
                    "reviewComment": request.comment,
                },
            )
            db.add(asset)
            db.flush()
        result["assetId"] = asset.id
        result["incorporated"] = True
    else:
        result["incorporated"] = False
    result["admission"] = desired
    result["humanReview"] = {
        "reviewedBy": user.id,
        "decision": request.decision,
        "comment": request.comment,
        "evaluation": request.evaluation.model_dump(mode="json", by_alias=True)
        if request.evaluation
        else None,
    }
    job.result_payload = result
    db.commit()
    db.refresh(job)
    return job
