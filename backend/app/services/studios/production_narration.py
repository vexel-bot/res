"""Reuse admitted stock speech jobs and measure each beat before composing it."""

import hashlib
from datetime import UTC, datetime

from ...domain.studios.contracts import AssetReferenceV1, CreateGenerationJobRequest, SpeechSynthesisRequestV1
from ...domain.studios.providers import SPEECH_PROVIDERS
from ...models import LibraryAsset, StudioGenerationJob
from ...providers.studios.media_probe import MEDIA_PROBE_PROVIDERS
from ..object_storage import get_object_storage, sha256_file
from .compatibility import persist_contract, record_to_contract
from .jobs import create_job
from .review_binding import invalidate_linked_post_review


def measured_asset(db, record, asset_id, expected_checksum):
    asset = db.get(LibraryAsset, asset_id)
    if (
        not asset
        or asset.workspace_id != record.workspace_id
        or asset.lifecycle_status != "active"
        or not asset.storage_key
        or not asset.media_type.startswith("audio/")
        or asset.checksum_sha256 != expected_checksum
    ):
        raise ValueError("production_narration_asset_conflict")
    with get_object_storage(asset.storage_backend).materialize(asset.storage_key) as path:
        if sha256_file(path) != expected_checksum:
            raise ValueError("production_narration_checksum_conflict")
        probe = MEDIA_PROBE_PROVIDERS["builtin.ffprobe"].probe(
            path, asset_id=asset.id, checksum_sha256=expected_checksum
        )
    if not probe.duration_microseconds:
        raise ValueError("production_narration_duration_required")
    return asset, probe.duration_microseconds / 1e6


def prepare_narration(db, record, state, request, user):
    """Return (measurements, queued job). No fabricated human review or provider admission."""
    if request.evaluation_scope == "visual_only":
        return [], None
    beats = state["artifacts"]["direction"]["beats"]
    document = record_to_contract(record)
    if request.narration_asset_id:
        # A single recording cannot establish multiple beat boundaries without alignment.
        if len(beats) != 1:
            raise ValueError("production_supplied_narration_alignment_required")
        ref = next((a for a in document.assets if a.id == request.narration_asset_id), None)
        if not ref or ref.rights_status != "verified":
            raise ValueError("production_qualified_narration_required")
        asset, seconds = measured_asset(db, record, ref.id, ref.checksum)
        return [
            {
                "beatId": beats[0]["id"],
                "assetId": asset.id,
                "durationSeconds": seconds,
                "checksum": ref.checksum,
                "origin": "supplied",
            }
        ], None
    if request.stock_voice_provider not in SPEECH_PROVIDERS:
        raise ValueError("production_qualified_narration_required")
    measurements, assets = [], []
    for beat in beats:
        text = beat["narration"]
        if not text.strip():
            continue
        key = "voice:" + beat["id"]
        job = db.get(StudioGenerationJob, state["jobs"].get(key)) if state["jobs"].get(key) else None
        script_hash = hashlib.sha256(text.encode()).hexdigest()
        if job is None:
            speech = SpeechSynthesisRequestV1(
                text=text, script_digest_sha256=script_hash, voice_key=request.stock_voice_key, locale="pt-BR"
            )
            job, _ = create_job(
                db,
                CreateGenerationJobRequest(
                    workspace_id=record.workspace_id,
                    document_id=record.id,
                    job_type="stock_voice",
                    provider=request.stock_voice_provider,
                    request=speech.model_dump(mode="json", by_alias=True),
                ),
                f"production:{state['id']}:voice:{beat['id']}:{script_hash[:16]}",
                user,
            )
            state["jobs"] = {**state["jobs"], key: job.id}
            return None, job
        if job.workspace_id != record.workspace_id or job.document_id != record.id:
            raise ValueError("production_voice_job_conflict")
        if job.status in {"failed", "cancelled"}:
            raise ValueError("production_voice_job_failed")
        if job.status != "succeeded":
            return None, job
        result = job.result_payload or {}
        if result.get("scriptDigestSha256") != script_hash or result.get("jobType") != "stock_voice":
            raise ValueError("production_voice_script_conflict")
        asset, seconds = measured_asset(db, record, result["assetId"], result["checksumSha256"])
        if (asset.object_metadata or {}).get("generationJobId") != job.id:
            raise ValueError("production_voice_lineage_conflict")
        assets.append(asset)
        measurements.append(
            {
                "beatId": beat["id"],
                "assetId": asset.id,
                "durationSeconds": seconds,
                "checksum": asset.checksum_sha256,
                "jobId": job.id,
                "origin": "stock_synthesis",
            }
        )
    changed = False
    for asset in assets:
        if asset.id not in {a.id for a in document.assets}:
            document.assets.append(
                AssetReferenceV1(
                    id=asset.id,
                    media_type=asset.media_type,
                    checksum=asset.checksum_sha256,
                    version=asset.checksum_sha256,
                    rights_status="verified",
                    origin="generated",
                    provenance=asset.object_metadata or {},
                )
            )
            changed = True
    if changed:
        document.revision += 1
        document.updated_at = datetime.now(UTC)
        invalidate_linked_post_review(db, record)
        persist_contract(record, document)
        state["documentRevision"] = record.revision
        state["sourceChecksums"] = {a.id: a.checksum for a in document.assets}
    return measurements, None
