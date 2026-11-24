"""Workspace-scoped lineage and revisioned director state, using the existing knowledge store.

No heuristic migration: only an explicit source document/revision creates ancestry.
All writes participate in the caller's transaction and use compare-and-swap.
"""
import copy
import hashlib
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from ...models import CreativeDocument, KnowledgeDocument


def _hash(kind, identifier):
    return hashlib.sha256(f"{kind}:{identifier}".encode()).hexdigest()


def _row(db, workspace_id, kind, identifier):
    return db.scalar(select(KnowledgeDocument).where(
        KnowledgeDocument.workspace_id == workspace_id, KnowledgeDocument.source_type == kind,
        KnowledgeDocument.content_hash == _hash(kind, identifier),
    ))


def lineage(db, record):
    row = _row(db, record.workspace_id, "craft_lineage", record.id)
    return copy.deepcopy(row.document_metadata) if row else {
        "schemaVersion": "craft.context.v2", "familyId": record.id, "documentId": record.id,
        "ancestors": [], "sourceDocumentId": None, "sourceRevision": None,
    }


def register_branch(db, record, source_id, source_revision, reason):
    source = db.scalar(select(CreativeDocument).where(
        CreativeDocument.id == source_id, CreativeDocument.workspace_id == record.workspace_id,
    ).with_for_update())
    if source is None or source.id == record.id or source.revision != source_revision or not reason.strip():
        raise ValueError("craft_lineage_source_conflict")
    parent = lineage(db, source)
    if record.id in parent["ancestors"]:
        raise ValueError("craft_lineage_cycle")
    if _row(db, record.workspace_id, "craft_lineage", record.id):
        raise ValueError("craft_lineage_already_bound")
    value = {"schemaVersion": "craft.context.v2", "familyId": parent["familyId"], "documentId": record.id,
             "sourceDocumentId": source.id, "sourceRevision": source_revision, "reason": reason,
             "ancestors": [*parent["ancestors"], source.id], "createdAt": datetime.now(UTC).isoformat()}
    db.add(KnowledgeDocument(workspace_id=record.workspace_id, title="Director project lineage",
                            source_type="craft_lineage", content_hash=_hash("craft_lineage", record.id),
                            status="ready", document_metadata=value))
    db.flush()
    return value


def state(db, record):
    family = lineage(db, record)["familyId"]
    row = _row(db, record.workspace_id, "craft_direction_v2", family)
    value = copy.deepcopy(row.document_metadata) if row else {
        "schemaVersion": "craft.context.v2", "familyId": family, "version": 0,
        "plans": [], "issues": [], "evidence": [], "candidates": [], "comparisons": [],
        "preferredCandidateId": None, "approvedCandidateId": None, "humanApproval": "not_recorded", "operations": [],
    }
    return row, value


def save(db, record, value, expected_version):
    row, current = state(db, record)
    if type(expected_version) is not int or current["version"] != expected_version:
        raise ValueError("craft_direction_version_conflict")
    value = copy.deepcopy(value)
    previous_cycle, next_cycle = current.get("cycle"), value.get("cycle")
    if (previous_cycle and next_cycle and previous_cycle.get("documentId")
            and previous_cycle.get("documentId") != next_cycle.get("documentId")):
        value["cycleArchive"] = [*copy.deepcopy(current.get("cycleArchive", [])), copy.deepcopy(previous_cycle)]
    value.update(version=expected_version + 1, updatedAt=datetime.now(UTC).isoformat())
    if row:
        result = db.execute(update(KnowledgeDocument).where(
            KnowledgeDocument.id == row.id,
            KnowledgeDocument.document_metadata["version"].as_integer() == expected_version,
        ).values(document_metadata=value).execution_options(synchronize_session=False))
        if result.rowcount != 1:
            raise ValueError("craft_direction_version_conflict")
        db.expire(row)
    else:
        try:
            with db.begin_nested():
                db.add(KnowledgeDocument(workspace_id=record.workspace_id, title="Autonomous director state",
                                        source_type="craft_direction_v2", status="draft",
                                        content_hash=_hash("craft_direction_v2", current["familyId"]), document_metadata=value))
                db.flush()
        except IntegrityError as exc:
            raise ValueError("craft_direction_version_conflict") from exc
    db.flush()
    return value


def document_cycle(value, document_id):
    cycle = value.get("cycle", {})
    if not cycle.get("documentId") or cycle["documentId"] == document_id:
        return cycle
    return next((c for c in reversed(value.get("cycleArchive", [])) if c.get("documentId") == document_id), {})


def context(db, record, instruction):
    from .craft_learning import project_feedback, style_guide
    from .craft_director_contracts import compact_cycle

    relation = lineage(db, record)
    documents = [*relation["ancestors"], record.id]
    guides = [style_guide(db, record.workspace_id)]
    guides.extend(style_guide(db, record.workspace_id, "document", identifier) for identifier in documents)
    preferences, hypotheses, observations = [], [], []
    for guide in guides:
        for lesson in guide.get("lessons", []):
            item = {**lesson, "scope": guide["scope"], "scopeId": guide["scopeId"]}
            (preferences if lesson.get("status") == "approved" else hypotheses).append(item)
    for identifier in documents:
        observations.extend({**item, "documentId": identifier} for item in project_feedback(db, record.workspace_id, identifier))
    _, current = state(db, record)
    plans = [plan for plan in current["plans"] if plan["documentId"] in documents]
    latest = plans[-1] if plans else None
    compact_plan = ({"id": latest["id"], "version": latest["version"], "summary": latest["plan"]["summary"],
                     "chosenDirection": latest["plan"]["chosenDirection"], "alternatives": latest["plan"]["alternatives"],
                     "rejectionReasons": latest["plan"]["rejectionReasons"], "uncertainties": latest["plan"]["uncertainties"]}
                    if latest else None)
    return {"schemaVersion": "craft.context.v2", "lineage": relation,
            "currentUserRequirements": instruction, "approvedPreferences": preferences,
            "versionObservations": observations, "hypotheses": hypotheses,
            "version": current["version"], "latestPlan": compact_plan,
            "evidenceIndex": [{"id": e["id"], "binding": e["binding"], "planId": e.get("planId"),
                "interval": e["assessment"]["interval"], "modality": e["assessment"]["modality"],
                "statuses": sorted({f["status"] for f in e["assessment"]["findings"]})} for e in current["evidence"]],
            "operationIndex": [{k: o.get(k) for k in ("id", "operationKey", "kind", "status", "costUsd")}
                               for o in current["operations"]],
            "autonomousCycle": (compact_cycle(document_cycle(current, record.id))
                if document_cycle(current, record.id).get("compactEvidence") else
                {k: v for k, v in document_cycle(current, record.id).items() if k != "processHistory"}),
            "issues": [{**{k: i[k] for k in ("id", "description", "status", "binding", "interval", "scope") if k in i},
                        "applicability": "current_document" if i.get("scope") == "family"
                            or i.get("binding", {}).get("documentId", record.id) == record.id else "historical_source"}
                       for i in current["issues"]], "preferredCandidateId": current["preferredCandidateId"],
            "revisionHypotheses": [{"id": o["id"], "hypothesis": o["hypothesis"]} for o in current["operations"]
                                   if o.get("kind") == "revision_hypothesis"],
            "humanApproval": current["humanApproval"],
            "approvedCandidateId": current.get("approvedCandidateId"),
            "draftCandidateId": current.get("draftCandidateId"),
            "precedence": "Current user requirements supersede conflicting historical scope. Approved preferences are scoped. "
                          "Praise and relative improvement are observations, never blanket approval or preservation locks. "
                          "Choose references, scenes, tools and reconstruction freely. Unobserved quality stays inconclusive."}


def human_approval(db, record, user, request):
    if record.revision != request.expected_revision:
        raise ValueError("craft_candidate_revision_conflict")
    _, current = state(db, record)
    candidate = next((c for c in current["candidates"] if c["id"] == request.candidate_id), None)
    if not candidate:
        raise ValueError("craft_candidate_missing")
    approval = {"candidateId": candidate["id"], "binding": candidate["binding"], "decision": request.decision,
                "comment": request.comment, "actorId": user.id, "createdAt": datetime.now(UTC).isoformat()}
    current.setdefault("humanApprovalHistory", []).append(approval)
    current["humanApproval"] = approval
    if request.decision == "approved":
        current["approvedCandidateId"] = candidate["id"]
    elif current.get("approvedCandidateId") == candidate["id"]:
        current["approvedCandidateId"] = None
    saved = save(db, record, current, request.expected_version)
    db.commit()
    return {"version": saved["version"], "humanApproval": approval, "approvedCandidateId": saved.get("approvedCandidateId")}
