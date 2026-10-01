"""Human comparison receipt bound to current phase renders and source material."""

from datetime import UTC, datetime

from ...models import LibraryAsset
from .compatibility import record_to_contract
from .editorial_production import get_run
from .kernel import emit_event
from .visual_quality_program import render_quality


def _artifact(state):
    return ((state.get("artifacts") or {}).get("video") or (state.get("artifacts") or {}).get("animatic") or {}).get(
        "artifact"
    ) or {}


def record_visual_comparison(db, document, request, user):
    if request.expected_document_revision != document.revision:
        raise ValueError("visual_comparison_revision_conflict")
    states = [get_run(db, document, run_id) for run_id in (request.edit_a_run_id, request.edit_b_run_id)]
    if any(
        state.get("documentRevision") != document.revision
        or (state.get("request") or {}).get("qualityPhaseId") != "visual-quality-2026-10-01"
        for state in states
    ):
        raise ValueError("visual_comparison_phase_run_required")
    sources = [state.get("sourceChecksums") or {} for state in states]
    if not sources[0] or sources[0] != sources[1]:
        raise ValueError("visual_comparison_same_sources_required")
    if states[0].get("requestDigest") == states[1].get("requestDigest"):
        raise ValueError("visual_comparison_distinct_edit_decisions_required")
    renders = []
    for state in states:
        artifact = _artifact(state)
        asset = db.get(LibraryAsset, artifact.get("assetId"))
        if not asset or asset.lifecycle_status != "active":
            raise ValueError("visual_comparison_render_missing")
        quality = render_quality(state, asset, document)
        if any(
            blocker in quality["blockers"]
            for blocker in (
                "render_missing",
                "render_checksum_mismatch",
                "document_revision_stale",
                "render_document_binding_mismatch",
            )
        ):
            raise ValueError("visual_comparison_render_binding_conflict")
        renders.append(quality)
    if [render["renderChecksum"] for render in renders] != [request.edit_a_checksum, request.edit_b_checksum]:
        raise ValueError("visual_comparison_viewed_render_changed")
    if renders[0]["renderChecksum"] == renders[1]["renderChecksum"]:
        raise ValueError("visual_comparison_distinct_renders_required")
    control = db.get(LibraryAsset, request.control_asset_id)
    if (
        not control
        or control.workspace_id != document.workspace_id
        or control.lifecycle_status != "active"
        or control.media_type != "video/mp4"
        or control.checksum_sha256 != request.control_checksum
    ):
        raise ValueError("visual_comparison_control_binding_conflict")
    if control.checksum_sha256 in {render["renderChecksum"] for render in renders}:
        raise ValueError("visual_comparison_distinct_control_required")
    technical = ((control.object_metadata or {}).get("editingResource") or {}).get("technical") or {}
    probe = technical.get("probe") or {}
    video_streams = probe.get("videoStreams") or []
    if (
        abs(float(probe.get("durationMicroseconds") or 0) / 1_000_000 - 15) > 0.1
        or not video_streams
        or any(stream.get("width", 0) * 16 != stream.get("height", 0) * 9 for stream in video_streams)
        or not probe.get("audioStreams")
    ):
        raise ValueError("visual_comparison_control_format_required")
    references = {asset.id: asset for asset in record_to_contract(document).assets}
    edl_checksums = set()
    for clip in request.control_edl:
        source = references.get(clip.asset_id)
        if (
            not source
            or source.rights_status != "verified"
            or not source.media_type.startswith("video/")
            or sources[0].get(clip.asset_id) != source.checksum
        ):
            raise ValueError("visual_comparison_control_source_conflict")
        edl_checksums.add(source.checksum)
        source_asset = db.get(LibraryAsset, clip.asset_id)
        if (
            not source_asset
            or source_asset.workspace_id != document.workspace_id
            or source_asset.lifecycle_status != "active"
            or source_asset.checksum_sha256 != source.checksum
        ):
            raise ValueError("visual_comparison_control_source_conflict")
        source_technical = ((source_asset.object_metadata or {}).get("editingResource") or {}).get("technical") or {}
        duration_us = source_technical.get("durationMicroseconds") or (
            source_technical.get("probe") or {}
        ).get("durationMicroseconds")
        if not isinstance(duration_us, (int, float)) or duration_us <= 0:
            raise ValueError("visual_comparison_source_probe_required")
        if clip.start_seconds + clip.duration_seconds > duration_us / 1_000_000 + 0.05:
            raise ValueError("visual_comparison_control_source_interval_invalid")
    if len(edl_checksums) < 2:
        raise ValueError("visual_comparison_two_sources_required")
    all_inspected = all(
        (
            request.blind_review_completed,
            request.normal_speed_inspected,
            request.mobile_inspected,
            request.straight_concatenation_confirmed,
            request.same_materials_confirmed,
            not request.unrecorded_manual_corrections,
        )
    )
    selected = renders[0] if request.preferred == "edit_a" else renders[1] if request.preferred == "edit_b" else None
    passed = bool(
        all_inspected
        and selected
        and selected["visualStatus"] == "approved"
        and all(render["technicalStatus"] == "passed" for render in renders)
    )
    receipt = {
        **request.model_dump(mode="json", by_alias=True),
        "documentId": document.id,
        "workspaceId": document.workspace_id,
        "editAChecksum": renders[0]["renderChecksum"],
        "editBChecksum": renders[1]["renderChecksum"],
        "sourceChecksums": sources[0],
        "status": "passed"
        if passed
        else "rejected"
        if all_inspected and request.preferred == "concat_control"
        else "pending",
        "evidenceLevel": "human_attested_control_with_verified_source_ids_and_media_probe",
        "reviewedBy": user.id,
        "at": datetime.now(UTC).isoformat(),
    }
    emit_event(
        db,
        workspace_id=document.workspace_id,
        event_type="studio.visual_quality.comparison_recorded",
        aggregate_type="visual-quality-comparison",
        aggregate_id=document.id,
        correlation_id=document.id,
        actor_id=user.id,
        payload=receipt,
    )
    db.commit()
    return receipt
