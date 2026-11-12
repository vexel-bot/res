"""Rendered techniques enter workspace knowledge as auditable candidates."""
import hashlib
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from ...models import KnowledgeDocument


def _guide_scope(db, workspace_id, scope, scope_id):
    from ...models import BrandProfile, CreativeDocument, Workspace

    if scope == "workspace":
        if scope_id not in {None, workspace_id} or db.get(Workspace, workspace_id) is None:
            raise ValueError("craft_style_guide_scope_invalid")
        scope_id = workspace_id
    elif scope in {"document", "brand"}:
        model = CreativeDocument if scope == "document" else BrandProfile
        row = db.get(model, scope_id) if scope_id else None
        if row is None or row.workspace_id != workspace_id:
            raise ValueError("craft_style_guide_scope_unavailable")
    else:
        raise ValueError("craft_style_guide_scope_invalid")
    digest = hashlib.sha256(f"craft-style-guide:{scope}:{scope_id}".encode()).hexdigest()
    return scope_id, digest


def style_guide(db, workspace_id, scope="workspace", scope_id=None, version=None):
    scope_id, digest = _guide_scope(db, workspace_id, scope, scope_id)
    row = db.scalar(select(KnowledgeDocument).where(
        KnowledgeDocument.workspace_id == workspace_id, KnowledgeDocument.content_hash == digest,
        KnowledgeDocument.source_type == "craft_style_guide",
    ))
    guide = ((row.document_metadata or {}).get("styleGuide", {}) if row else {})
    current = {"scope": scope, "scopeId": scope_id, "version": 0, "lessons": [], **guide}
    if version is not None and version != current["version"]:
        old = next((item for item in guide.get("history", []) if item["version"] == version), None)
        if old is None:
            raise ValueError("craft_style_guide_version_unavailable")
        current = old
    return {key: value for key, value in current.items() if key != "history"}


def save_editorial_lesson(db, workspace_id, lesson, expected_version, scope="workspace", scope_id=None,
                         source_job_id=None, approved=False, actor_id=None):
    from ...models import StudioGenerationJob

    scope_id, digest = _guide_scope(db, workspace_id, scope, scope_id)
    if type(expected_version) is not int or expected_version < 0 or not isinstance(lesson, dict):
        raise ValueError("craft_style_guide_lesson_invalid")
    for key in ("situation", "correction"):
        if not isinstance(lesson.get(key), str) or not lesson[key].strip() or len(lesson[key]) > 4000:
            raise ValueError("craft_style_guide_lesson_invalid")
    for key in ("useWhen", "avoidWhen"):
        values = lesson.get(key, [])
        if not isinstance(values, list) or (key == "useWhen" and not values) or len(values) > 20:
            raise ValueError("craft_style_guide_lesson_invalid")
        if any(not isinstance(value, str) or not value.strip() or len(value) > 2000 for value in values):
            raise ValueError("craft_style_guide_lesson_invalid")
    if approved and actor_id is None:
        raise ValueError("craft_style_guide_approval_required")
    if source_job_id:
        job = db.get(StudioGenerationJob, source_job_id)
        if job is None or job.workspace_id != workspace_id:
            raise ValueError("craft_style_guide_scope_unavailable")
    row = db.scalar(select(KnowledgeDocument).where(
        KnowledgeDocument.workspace_id == workspace_id, KnowledgeDocument.content_hash == digest,
    ).with_for_update())
    previous = (row.document_metadata or {}).get("styleGuide", {}) if row else {}
    if previous.get("version", 0) != expected_version:
        raise ValueError("craft_style_guide_version_conflict")
    lessons = list(previous.get("lessons", []))
    lesson_id = lesson.get("id") or str(uuid4())
    old = next((item for item in lessons if item["id"] == lesson_id), None)
    if lesson.get("id") and old is None:
        raise ValueError("craft_style_guide_lesson_unavailable")
    if old and old.get("status") == "approved" and not approved:
        raise ValueError("craft_style_guide_approved_lesson_requires_user")
    item = {key: lesson[key] for key in ("situation", "correction", "useWhen", "avoidWhen", "sourceFeedback", "sourceUrl")
            if key in lesson}
    item.update(id=lesson_id, status="approved" if approved else "candidate", sourceJobId=source_job_id,
                actorId=actor_id, updatedAt=datetime.now(UTC).isoformat())
    lessons = [item if old_item["id"] == lesson_id else old_item for old_item in lessons] if old else [*lessons, item]
    history = list(previous.get("history", []))
    if previous:
        history.append({key: value for key, value in previous.items() if key != "history"})
    guide = {"scope": scope, "scopeId": scope_id, "version": expected_version + 1,
             "lessons": lessons, "updatedAt": item["updatedAt"], "history": history}
    if row:
        result = db.execute(update(KnowledgeDocument).where(
            KnowledgeDocument.id == row.id,
            KnowledgeDocument.document_metadata["styleGuide"]["version"].as_integer() == expected_version,
        ).values(document_metadata={**row.document_metadata, "styleGuide": guide}).execution_options(synchronize_session=False))
        if result.rowcount != 1:
            raise ValueError("craft_style_guide_version_conflict")
        db.expire(row)
    else:
        try:
            with db.begin_nested():
                db.add(KnowledgeDocument(workspace_id=workspace_id, title="Guia de edição", source_type="craft_style_guide",
                                         status="ready", content_hash=digest, document_metadata={"styleGuide": guide}))
                db.flush()
        except IntegrityError as error:
            raise ValueError("craft_style_guide_version_conflict") from error
    db.flush()
    return {key: value for key, value in guide.items() if key != "history"}


def record_render(db, job, evidence):
    content_hash = hashlib.sha256(("craft-learning:" + job.id).encode()).hexdigest()
    item = db.scalar(select(KnowledgeDocument).where(
        KnowledgeDocument.workspace_id == job.workspace_id, KnowledgeDocument.content_hash == content_hash,
    ))
    metadata = {"craftLearning": evidence, "documentId": job.document_id, "revision": job.request_payload["documentRevision"],
                "engineBuildId": job.request_payload["engineBuildId"]}
    if item:
        old = (item.document_metadata or {}).get("craftLearning", {})
        checksum = (evidence.get("artifact") or {}).get("checksumSha256")
        if checksum and checksum == (old.get("artifact") or {}).get("checksumSha256"):
            if item.status == "ready" or old.get("viewerFeedback"):
                return item
        item.document_metadata = metadata
        item.status = "draft"
    else:
        item = KnowledgeDocument(
            workspace_id=job.workspace_id, title="Motion · evidência do render " + job.id,
            source_type="craft_experiment", status="draft", content_hash=content_hash,
            document_metadata=metadata,
        )
        db.add(item)
    db.flush()
    return item


def record_viewer_feedback(db, job, feedback):
    item = record_render(db, job, (job.result_payload or {}).get("learningEvidence", {}))
    evidence = item.document_metadata["craftLearning"]
    evidence = {**evidence, "state": "revision requested", "viewerFeedback": {
        "source": "project owner", "comment": feedback,
    }}
    item.document_metadata = {**item.document_metadata, "documentId": job.document_id, "craftLearning": evidence}
    item.status = "draft"
    job.result_payload = {**job.result_payload, "learningEvidence": evidence, "learningKnowledgeId": item.id}
    db.flush()
    return item


def project_feedback(db, workspace_id, document_id):
    rows = db.scalars(select(KnowledgeDocument).where(
        KnowledgeDocument.workspace_id == workspace_id, KnowledgeDocument.source_type == "craft_experiment",
        KnowledgeDocument.document_metadata["documentId"].as_string() == document_id,
    ).order_by(KnowledgeDocument.updated_at.desc()).limit(5))
    return [{"sourceJobId": row.document_metadata["craftLearning"].get("sourceJobId"),
             "feedback": row.document_metadata["craftLearning"]["viewerFeedback"],
             "state": row.document_metadata["craftLearning"]["state"]}
            for row in rows if row.document_metadata.get("craftLearning", {}).get("viewerFeedback")]


def validated_lessons(db, workspace_id):
    rows = db.scalars(select(KnowledgeDocument).where(
        KnowledgeDocument.workspace_id == workspace_id, KnowledgeDocument.source_type == "craft_experiment",
        KnowledgeDocument.status == "ready",
    ).order_by(KnowledgeDocument.updated_at.desc()).limit(10))
    return [
        {"id": row.id, **row.document_metadata["craftLearning"]}
        for row in rows if row.document_metadata.get("craftLearning", {}).get("localTest", {}).get("passed")
    ]


def promote_local_test(db, knowledge_id, workspace_id, validation):
    row = db.scalar(select(KnowledgeDocument).where(
        KnowledgeDocument.id == knowledge_id, KnowledgeDocument.workspace_id == workspace_id,
        KnowledgeDocument.source_type == "craft_experiment",
    ).with_for_update())
    if row is None:
        raise ValueError("craft_learning_candidate_unavailable")
    evidence = (row.document_metadata or {}).get("craftLearning", {})
    checksum = (evidence.get("artifact") or {}).get("checksumSha256")
    if (validation.get("passed") is not True or validation.get("artifactChecksum") != checksum
            or not checksum or not validation.get("testId") or not validation.get("observedResult")):
        raise ValueError("craft_learning_local_test_required")
    has_feedback = bool(evidence.get("viewerFeedback"))
    row.document_metadata = {**row.document_metadata, "craftLearning": {
        **evidence, "state": "revision requested" if has_feedback else "reproduced locally", "localTest": validation,
    }}
    row.status = "draft" if has_feedback else "ready"
    db.flush()
    return row
