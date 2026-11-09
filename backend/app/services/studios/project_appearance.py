"""Bind a project, its selected appearance and optional scene to an image request."""

import tempfile
from contextlib import ExitStack
from pathlib import Path, PurePosixPath
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import select

from ...domain.studios.appearance_image import AppearanceImageRequestV1, canonical_digest
from ...domain.studios.providers import APPEARANCE_IMAGE_PROVIDERS
from ...models import (
    LibraryAsset,
    StudioGenerationJob,
    StudioIdentityVersion,
    StudioModelRegistration,
    StudioProviderRegistration,
)
from ..object_storage import get_object_storage, object_key, sha256_file
from .casting import resolve_cast


def _image_asset(db, workspace_id, asset_id):
    asset = db.get(LibraryAsset, asset_id, populate_existing=True)
    if (
        not asset
        or asset.workspace_id != workspace_id
        or asset.lifecycle_status != "active"
        or not asset.storage_key
        or not asset.storage_backend
        or not asset.checksum_sha256
        or not (asset.media_type or "").startswith("image/")
    ):
        raise ValueError("appearance_image_asset_unavailable")
    key = PurePosixPath(asset.storage_key)
    if not key.parts or key.parts[0] != workspace_id or ".." in key.parts:
        raise ValueError("appearance_image_storage_scope_mismatch")
    return asset


def selected_appearance_asset(db, row, selection):
    """Verify a reviewed result remains bound to the current cast and source."""
    job = db.get(StudioGenerationJob, selection.get("jobId"), populate_existing=True)
    plan = selection.get("plan") or {}
    request = plan.get("request") or {}
    asset = _image_asset(db, row.workspace_id, selection.get("assetId"))
    metadata = asset.object_metadata or {}
    refs = resolve_cast(db, row.workspace_id, row.payload.get("identityVersionId"), row.payload.get("voiceVersionId"))
    if (
        not job
        or job.workspace_id != row.workspace_id
        or job.job_type != "appearance_image"
        or job.status != "succeeded"
        or job.correlation_id != f"department-appearance:{row.id}"
        or (job.request_payload or {}).get("plan") != plan
        or (job.result_payload or {}).get("assetId") != asset.id
        or plan.get("projectId") != row.id
        or plan.get("directionId") != row.payload.get("directionId")
        or plan.get("casting") != refs
        or row.payload.get("casting") != refs
        or request.get("sourceAssetId") != row.payload.get("sourceAssetId")
        or metadata.get("generationJobId") != job.id
        or metadata.get("planDigestSha256") != plan.get("planDigestSha256")
        or metadata.get("projectId") != row.id
        or metadata.get("casting") != refs
        or (metadata.get("appearanceResult") or {}).get("artifactChecksumSha256") != asset.checksum_sha256
    ):
        raise ValueError("appearance_selected_result_changed")
    reference = _image_asset(db, row.workspace_id, request.get("referenceAssetId"))
    if reference.checksum_sha256 != request.get("referenceChecksumSha256"):
        raise ValueError("appearance_material_checksum_mismatch")
    if request.get("sourceAssetId"):
        source = _image_asset(db, row.workspace_id, request["sourceAssetId"])
        if source.checksum_sha256 != request.get("sourceChecksumSha256"):
            raise ValueError("appearance_material_checksum_mismatch")
    return asset


def plan_project_appearance(db, row, direction, *, seed=0):
    """Create an immutable plan; never approve a provider or start inference."""
    payload = row.payload
    if payload.get("format") not in {"image", "carousel"}:
        raise ValueError("appearance_image_project_required")
    if not payload.get("directionId"):
        raise ValueError("appearance_direction_required")
    refs = resolve_cast(db, row.workspace_id, payload.get("identityVersionId"), payload.get("voiceVersionId"))
    identity_ref = refs.get("identity")
    if not identity_ref:
        raise ValueError("appearance_identity_required")
    if payload.get("casting") != refs:
        raise ValueError("cast_version_reference_mismatch")
    identity = db.get(StudioIdentityVersion, identity_ref["id"], populate_existing=True)
    if not identity or "avatar.generate" not in (identity.capabilities or []):
        raise ValueError("identity_capability_missing")
    reference = None
    for asset_id in identity.sample_asset_ids or []:
        try:
            reference = _image_asset(db, row.workspace_id, asset_id)
            break
        except ValueError:
            continue
    if not reference:
        raise ValueError("identity_image_sample_required")
    scene = _image_asset(db, row.workspace_id, payload["sourceAssetId"]) if payload.get("sourceAssetId") else None
    request = AppearanceImageRequestV1(
        identity_ref=identity_ref,
        reference_asset_id=reference.id,
        reference_checksum_sha256=reference.checksum_sha256.lower(),
        source_asset_id=scene.id if scene else None,
        source_checksum_sha256=scene.checksum_sha256.lower() if scene else None,
        direction=direction,
        seed=seed,
    )
    binding = {
        "schemaVersion": "clicko.project-appearance-plan.v1",
        "projectId": row.id,
        "workspaceId": row.workspace_id,
        "projectRevision": payload["revision"],
        "directionId": payload["directionId"],
        "casting": refs,
        "request": request.model_dump(by_alias=True, mode="json"),
    }
    # The digest covers the selected voice as well as the appearance, so a
    # concurrent cast change cannot silently attach a stale result to a project.
    import hashlib
    import json

    binding["planDigestSha256"] = hashlib.sha256(
        json.dumps(binding, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()
    binding["requestDigestSha256"] = canonical_digest(request)
    return binding


def admitted_provider(db, name):
    """An installed candidate is not authority to generate client media."""
    provider = APPEARANCE_IMAGE_PROVIDERS.get(name)
    if not provider:
        raise ValueError("appearance_provider_unavailable")
    registration = db.scalar(
        select(StudioProviderRegistration)
        .where(
            StudioProviderRegistration.provider == name,
            StudioProviderRegistration.provider_version == provider.version,
            StudioProviderRegistration.capability == "appearance_image",
            StudioProviderRegistration.status == "approved",
        )
        .execution_options(populate_existing=True)
    )
    if (
        not registration
        or (registration.manifest or {}).get("benchmarkStatus") != "passed"
        or (registration.manifest or {}).get("workerAdvertised") is not True
    ):
        raise ValueError("appearance_provider_not_approved")
    model = db.scalar(
        select(StudioModelRegistration)
        .where(
            StudioModelRegistration.provider_registration_id == registration.id,
            StudioModelRegistration.status == "approved",
            StudioModelRegistration.digest_sha256 == canonical_digest(provider.manifest),
        )
        .execution_options(populate_existing=True)
    )
    if (
        not model
        or model.commercial_use != "approved"
        or "appearance_image" not in (model.capabilities or [])
        or (model.manifest or {}).get("benchmarkStatus") != "passed"
    ):
        raise ValueError("appearance_model_not_approved")
    return provider


def execute_project_appearance(db, row, plan, provider_name, progress, is_cancelled, *, generation_job_id=None):
    """Produce a private review asset; the caller must provide job admission."""
    provider = admitted_provider(db, provider_name)
    request = AppearanceImageRequestV1.model_validate(plan["request"])
    db.refresh(row)
    if plan_project_appearance(db, row, request.direction, seed=request.seed) != plan:
        raise ValueError("appearance_project_plan_changed")
    if is_cancelled():
        raise InterruptedError("appearance_cancelled_before_inference")
    asset_id = (
        str(uuid5(NAMESPACE_URL, f"clicko:appearance:{row.workspace_id}:{generation_job_id}"))
        if generation_job_id
        else None
    )
    existing = db.get(LibraryAsset, asset_id, populate_existing=True) if asset_id else None
    if existing:
        metadata = existing.object_metadata or {}
        previous = metadata.get("appearanceResult") or {}
        if (
            existing.workspace_id != row.workspace_id
            or existing.lifecycle_status != "active"
            or not existing.storage_key
            or metadata.get("generationJobId") != generation_job_id
            or metadata.get("planDigestSha256") != plan["planDigestSha256"]
            or previous.get("provider") != provider.name
            or previous.get("providerVersion") != provider.version
            or previous.get("modelManifestDigestSha256") != canonical_digest(provider.manifest)
            or previous.get("requestDigestSha256") != canonical_digest(request)
            or previous.get("artifactChecksumSha256") != existing.checksum_sha256
            or not existing.checksum_sha256
        ):
            raise ValueError("appearance_existing_result_conflict")
        with get_object_storage(existing.storage_backend).materialize(existing.storage_key) as path:
            if sha256_file(path) != existing.checksum_sha256:
                raise ValueError("appearance_existing_result_conflict")
        return existing
    reference = _image_asset(db, row.workspace_id, request.reference_asset_id)
    scene = _image_asset(db, row.workspace_id, request.source_asset_id) if request.source_asset_id else None
    storage, stored = get_object_storage(), None
    try:
        with ExitStack() as stack:
            reference_path = stack.enter_context(
                get_object_storage(reference.storage_backend).materialize(reference.storage_key)
            )
            scene_path = (
                stack.enter_context(get_object_storage(scene.storage_backend).materialize(scene.storage_key))
                if scene
                else None
            )
            if sha256_file(reference_path) != request.reference_checksum_sha256 or (
                scene_path and sha256_file(scene_path) != request.source_checksum_sha256
            ):
                raise ValueError("appearance_material_checksum_mismatch")
            output = (
                Path(stack.enter_context(tempfile.TemporaryDirectory(prefix="clicko-appearance-result-")))
                / "output.png"
            )
            result = provider.generate(request, reference_path, scene_path, output, progress, is_cancelled)
            if (
                result.provider != provider.name
                or result.provider_version != provider.version
                or result.request_digest_sha256 != canonical_digest(request)
                or result.model_manifest_digest_sha256 != canonical_digest(provider.manifest)
                or result.identity_ref != request.identity_ref
                or result.reference_checksum_sha256 != request.reference_checksum_sha256
                or result.source_checksum_sha256 != request.source_checksum_sha256
                or not output.is_file()
                or output.is_symlink()
                or result.artifact_checksum_sha256 != sha256_file(output)
                or result.review_required is not True
                or result.synthetic_content_disclosed is not True
            ):
                raise ValueError("appearance_result_binding_mismatch")
            if is_cancelled():
                raise InterruptedError("appearance_cancelled_before_persistence")
            from PIL import Image

            with Image.open(output) as image:
                if image.format != "PNG" or image.size != (request.width, request.height):
                    raise ValueError("appearance_result_image_invalid")
                image.verify()
            stored = storage.put_file(
                output,
                key=object_key(row.workspace_id, "derived", ".png"),
                media_type="image/png",
                metadata={"role": "private-appearance-review"},
            )
            if stored.checksum_sha256 != result.artifact_checksum_sha256:
                raise ValueError("appearance_stored_checksum_mismatch")
        db.refresh(row)
        if is_cancelled():
            raise InterruptedError("appearance_cancelled_before_persistence")
        if plan_project_appearance(db, row, request.direction, seed=request.seed) != plan:
            raise ValueError("appearance_project_plan_changed")
        if admitted_provider(db, provider_name) is not provider:
            raise ValueError("appearance_provider_changed")
        asset = LibraryAsset(
            **({"id": asset_id} if asset_id else {}),
            workspace_id=row.workspace_id,
            title=f"{row.payload['title']} — imagem para revisão",
            asset_type="image",
            tags=["studio-appearance", "private-review", "synthetic-content"],
            storage_key=stored.key,
            storage_backend=stored.backend,
            media_type=stored.media_type,
            size_bytes=stored.size_bytes,
            checksum_sha256=stored.checksum_sha256,
            object_metadata={
                **stored.metadata,
                "schemaVersion": "studio.asset-lineage.v1",
                "derivation": "appearance_image",
                "projectId": row.id,
                "generationJobId": generation_job_id,
                "planDigestSha256": plan["planDigestSha256"],
                "casting": plan["casting"],
                "referenceAssetId": reference.id,
                "sourceAssetId": scene.id if scene else None,
                "appearanceResult": result.model_dump(by_alias=True, mode="json"),
                "syntheticContentDisclosed": True,
                "reviewRequired": True,
            },
        )
        db.add(asset)
        db.flush()
        db.commit()
        return asset
    except Exception:
        db.rollback()
        if stored:
            storage.delete(stored.key)
        raise
