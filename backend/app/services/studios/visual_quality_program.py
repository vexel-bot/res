"""Internal visual-quality projection; technical success is never visual approval."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from sqlalchemy import select

from ...models import CreativeDocument, LibraryAsset, StudioDomainEvent, StudioGenerationJob
from .gemini_editing import committed_test_amount

BASELINE_PATH = (
    Path(__file__).resolve().parents[4] / "benchmarks/studios/video/visual-quality-baseline-2026-09-30.v1.json"
)
MINIMUM_SCORE = 4


def _document_payload(record):
    return record.canonical_document or record.document or {}


def _brief_key(payload):
    brief = payload.get("brief") or {}
    meaningful = {key: brief.get(key) for key in ("objective", "angle", "promise", "cta")}
    return hashlib.sha256(json.dumps(meaningful, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def material_readiness(payload):
    assets = payload.get("assets") or []
    verified = [asset for asset in assets if asset.get("rightsStatus") == "verified" and asset.get("checksum")]
    motion_sources = {asset["checksum"] for asset in verified if str(asset.get("mediaType", "")).startswith("video/")}
    action_sources = {
        asset["checksum"]
        for asset in verified
        if str(asset.get("mediaType", "")).startswith("video/")
        and str(
            (asset.get("provenance") or {}).get("observableAction")
            or ((asset.get("provenance") or {}).get("editingResource") or {}).get("motionDescription")
            or ""
        ).strip()
    }
    brand_asset = any(
        asset.get("visualRole") in {"product", "package", "logo", "brand"}
        or (asset.get("provenance") or {}).get("assetRole") in {"product", "package", "logo", "brand"}
        or ((asset.get("provenance") or {}).get("editingResource") or {}).get("assetRole")
        in {"product", "package", "logo", "brand"}
        or ((asset.get("provenance") or {}).get("editingResource") or {}).get("kind") == "logo"
        for asset in verified
    )
    blockers = []
    if not (payload.get("brief") or {}).get("objective"):
        blockers.append("brief_missing")
    if not payload.get("brandMemoryRef"):
        blockers.append("brand_identity_missing")
    if len(motion_sources) < 2:
        blockers.append("two_distinct_action_sources_required")
    elif len(action_sources) < 2:
        blockers.append("observable_action_evidence_missing")
    if not brand_asset:
        blockers.append("authorized_product_or_brand_asset_missing")
    return {
        "status": "ready" if not blockers else "pending",
        "blockers": blockers,
        "distinctMotionSources": len(motion_sources),
        "actionSourcesWithEvidence": len(action_sources),
    }


def render_quality(state, asset, document):
    artifact = (
        (state.get("artifacts") or {}).get("video") or (state.get("artifacts") or {}).get("animatic") or {}
    ).get("artifact") or {}
    checksum = artifact.get("checksumSha256")
    asset_id = artifact.get("assetId")
    technical = state.get("technicalEvaluation")
    if not isinstance(technical, dict):
        technical = (
            (state.get("artifacts") or {}).get("video") or (state.get("artifacts") or {}).get("animatic") or {}
        ).get("qualityEvaluation") or {}
    technical_status = technical.get("status", "pending") if isinstance(technical, dict) else "pending"
    blockers = []
    visual = "not_assessed"
    scores = None
    findings = []
    review = None
    if not checksum or not asset_id or not asset or asset.lifecycle_status != "active":
        blockers.append("render_missing")
    elif asset.checksum_sha256 != checksum or asset.workspace_id != document.workspace_id:
        blockers.append("render_checksum_mismatch")
    elif state.get("documentRevision") != document.revision:
        blockers.append("document_revision_stale")
    elif (asset.object_metadata or {}).get("documentId") != document.id or (asset.object_metadata or {}).get(
        "documentRevision"
    ) != document.revision:
        blockers.append("render_document_binding_mismatch")
    else:
        metadata = asset.object_metadata or {}
        receipt = metadata.get("visualHumanReview") or {}
        if (
            receipt.get("renderChecksum") == checksum
            and receipt.get("expectedDocumentRevision") == document.revision
            and receipt.get("assetId") == asset_id
        ):
            review = receipt
            scores = {key: receipt.get(key) for key in ("clarity", "rhythm", "continuity", "finish")}
            findings = receipt.get("findings") or []
            if not receipt.get("fullVideoInspected") or not receipt.get("mobileInspected"):
                blockers.append("full_playback_and_mobile_review_required")
            elif any(not isinstance(value, int) or isinstance(value, bool) for value in scores.values()):
                blockers.append("four_human_scores_required")
            elif min(scores.values()) >= MINIMUM_SCORE and receipt.get("status") == "meets_human_criteria":
                visual = "approved"
            elif min(scores.values()) <= 2:
                visual = "rejected"
            else:
                visual = "correction_needed"
        else:
            blockers.append("current_render_human_review_missing")
    if technical_status != "passed":
        blockers.append("technical_qc_not_passed")
    authorship = (state.get("artifacts") or {}).get("directionAuthorship") or {}
    manual_interventions = len(state.get("history") or []) or int(bool(state.get("revisionRequest")))
    autonomy = (
        ("assisted" if manual_interventions else "demonstrated")
        if state.get("autonomousProductionQualified") and visual == "approved" and technical_status == "passed"
        else "partial"
        if authorship.get("kind") == "provider"
        else "not_demonstrated"
    )
    return {
        "runId": state.get("id"),
        "documentId": document.id,
        "qualityPhaseId": (state.get("request") or {}).get("qualityPhaseId"),
        "documentRevision": state.get("documentRevision"),
        "assetId": asset_id,
        "renderChecksum": checksum,
        "technicalStatus": technical_status,
        "visualStatus": visual,
        "autonomyStatus": autonomy,
        "recordedManualInterventions": manual_interventions,
        "humanScores": scores,
        "findings": findings,
        "reviewedAt": review.get("at") if review else None,
        "blockers": blockers,
    }


def project_quality_program(db, workspace_id):
    documents = db.scalars(select(CreativeDocument).where(CreativeDocument.workspace_id == workspace_id)).all()
    events = db.scalars(
        select(StudioDomainEvent).where(
            StudioDomainEvent.workspace_id == workspace_id,
            StudioDomainEvent.aggregate_type == "editorial-production",
        )
    ).all()
    latest = {}
    for event in events:
        value = event.payload or {}
        if value.get("revision", 0) > latest.get(event.aggregate_id, {}).get("revision", -1):
            latest[event.aggregate_id] = value
    comparison_events = db.scalars(
        select(StudioDomainEvent).where(
            StudioDomainEvent.workspace_id == workspace_id,
            StudioDomainEvent.aggregate_type == "visual-quality-comparison",
        )
    ).all()
    comparisons = {}
    for event in sorted(comparison_events, key=lambda item: item.created_at):
        comparisons[event.aggregate_id] = event.payload or {}
    assets = {
        asset.id: asset
        for asset in db.scalars(
            select(LibraryAsset).where(
                LibraryAsset.workspace_id == workspace_id,
            )
        ).all()
    }
    docs = {record.id: record for record in documents}
    runs = []
    for state in latest.values():
        document = docs.get(state.get("documentId"))
        if not document:
            continue
        artifact = (
            (state.get("artifacts") or {}).get("video") or (state.get("artifacts") or {}).get("animatic") or {}
        ).get("artifact") or {}
        runs.append(render_quality(state, assets.get(artifact.get("assetId")), document))
    runs.sort(key=lambda item: (item["documentId"], item["runId"] or ""))
    candidates = {}
    for record in documents:
        payload = _document_payload(record)
        key = _brief_key(payload)
        material = material_readiness(payload)
        candidate = {"documentId": record.id, "title": record.title, "briefKey": key, "materials": material}
        old = candidates.get(key)
        if old is None or (len(material["blockers"]), record.id) < (
            len(old["materials"]["blockers"]),
            old["documentId"],
        ):
            candidates[key] = candidate
    cases = sorted(candidates.values(), key=lambda item: (len(item["materials"]["blockers"]), item["documentId"]))[:3]
    for case in cases:
        matching = [
            row
            for row in runs
            if row["documentId"] == case["documentId"] and row["qualityPhaseId"] == "visual-quality-2026-10-01"
        ]
        current = [
            row
            for row in matching
            if row["renderChecksum"]
            and not any(
                blocker in row["blockers"]
                for blocker in (
                    "render_missing",
                    "render_checksum_mismatch",
                    "document_revision_stale",
                    "render_document_binding_mismatch",
                )
            )
        ]
        case["renderStatus"] = "rendered" if current else "pending"
        case["visualStatus"] = (
            "approved"
            if any(row["visualStatus"] == "approved" and row["technicalStatus"] == "passed" for row in current)
            else "pending"
        )
        receipt = comparisons.get(case["documentId"]) or {}
        selected_run = receipt.get("editARunId") if receipt.get("preferred") == "edit_a" else receipt.get("editBRunId")
        selected_checksum = (
            receipt.get("editAChecksum") if receipt.get("preferred") == "edit_a" else receipt.get("editBChecksum")
        )
        selected = next(
            (row for row in current if row["runId"] == selected_run and row["renderChecksum"] == selected_checksum),
            None,
        )
        both_edits_current = all(
            any(
                row["runId"] == receipt.get(run_key) and row["renderChecksum"] == receipt.get(checksum_key)
                and row["technicalStatus"] == "passed"
                for row in current
            )
            for run_key, checksum_key in (("editARunId", "editAChecksum"), ("editBRunId", "editBChecksum"))
        )
        control = assets.get(receipt.get("controlAssetId"))
        comparison_current = bool(
            receipt.get("expectedDocumentRevision") == docs[case["documentId"]].revision
            and selected
            and both_edits_current
            and control
            and control.lifecycle_status == "active"
            and control.checksum_sha256 == receipt.get("controlChecksum")
            and len({receipt.get("editAChecksum"), receipt.get("editBChecksum"), control.checksum_sha256}) == 3
            and latest.get(receipt.get("editARunId"), {}).get("sourceChecksums") == receipt.get("sourceChecksums")
            and latest.get(receipt.get("editBRunId"), {}).get("sourceChecksums") == receipt.get("sourceChecksums")
            and all(
                assets.get(asset_id)
                and assets[asset_id].lifecycle_status == "active"
                and assets[asset_id].checksum_sha256 == checksum
                for asset_id, checksum in (receipt.get("sourceChecksums") or {}).items()
            )
        )
        case["comparisonStatus"] = (
            "passed"
            if comparison_current
            and receipt.get("status") == "passed"
            and selected["visualStatus"] == "approved"
            and selected["technicalStatus"] == "passed"
            else "rejected"
            if comparison_current and receipt.get("status") == "rejected"
            else "pending"
        )
    phase_jobs = db.scalars(
        select(StudioGenerationJob).where(
            StudioGenerationJob.request_payload["budgetGroupId"].as_string() == "visual-quality-2026-10-01"
        )
    ).all()
    reserved = sum(
        committed_test_amount(job) for job in phase_jobs if job.request_payload.get("environment") != "production"
    )
    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    return {
        "schemaVersion": "studio.visual-quality-program.v1",
        "workspaceId": workspace_id,
        "targetBriefs": 3,
        "baseline": baseline,
        "cases": cases,
        "renders": runs,
        "budget": {
            "limitUsd": 10,
            "committedOrReservedUsd": round(reserved, 6),
            "attempts": len(phase_jobs),
            "remainingUsd": round(max(0, 10 - reserved), 6),
        },
        "progress": {
            "distinctBriefs": len(candidates),
            "materialsReady": sum(case["materials"]["status"] == "ready" for case in cases),
            "rendered": sum(case["renderStatus"] == "rendered" for case in cases),
            "visualApproved": sum(case["visualStatus"] == "approved" for case in cases),
            "comparisonPassed": sum(case["comparisonStatus"] == "passed" for case in cases),
        },
        "phaseStatus": "validated"
        if len(cases) == 3
        and all(
            case["materials"]["status"] == "ready"
            and case["visualStatus"] == "approved"
            and case["comparisonStatus"] == "passed"
            for case in cases
        )
        else "pending",
    }
