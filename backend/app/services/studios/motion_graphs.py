from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ...domain.studios.motion import (
    CreateMotionGraphRequestV1,
    MotionGraphEvaluationV1,
    MotionGraphRecordV1,
    MotionGraphV1,
    ReplaceMotionGraphRequestV1,
    ReviewMotionGraphRequestV1,
    evaluate_motion_graph,
    motion_graph_digest,
    validate_motion_graph_bindings,
)
from ...models import CreativeDocument, StudioMotionGraph, User
from .compatibility import record_to_contract
from .kernel import emit_event


def motion_graph_out(record: StudioMotionGraph) -> MotionGraphRecordV1:
    graph = MotionGraphV1.model_validate(record.graph)
    evaluation = (
        MotionGraphEvaluationV1.model_validate(record.evaluation)
        if record.evaluation is not None
        else None
    )
    return MotionGraphRecordV1(
        graph=graph,
        graph_digest_sha256=record.graph_digest_sha256,
        storage_revision=record.storage_revision,
        evaluation=evaluation,
        created_by=record.created_by,
        updated_by=record.updated_by,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def get_motion_graph(
    db: Session,
    *,
    workspace_id: str,
    graph_id: str,
) -> StudioMotionGraph | None:
    return db.scalar(
        select(StudioMotionGraph).where(
            StudioMotionGraph.id == graph_id,
            StudioMotionGraph.workspace_id == workspace_id,
        )
    )


def list_motion_graphs(
    db: Session,
    *,
    workspace_id: str,
    document_id: str | None = None,
) -> list[StudioMotionGraph]:
    query = select(StudioMotionGraph).where(StudioMotionGraph.workspace_id == workspace_id)
    if document_id is not None:
        query = query.where(StudioMotionGraph.document_id == document_id)
    return list(db.scalars(query.order_by(StudioMotionGraph.updated_at.desc())).all())


def _document_contract(
    db: Session,
    *,
    workspace_id: str,
    document_id: str,
):
    record = db.scalar(
        select(CreativeDocument).where(
            CreativeDocument.id == document_id,
            CreativeDocument.workspace_id == workspace_id,
        )
    )
    if record is None:
        raise ValueError("motion_graph_document_not_found")
    return record_to_contract(record)


def create_motion_graph(
    db: Session,
    request: CreateMotionGraphRequestV1,
    user: User,
) -> StudioMotionGraph:
    document = _document_contract(
        db,
        workspace_id=request.workspace_id,
        document_id=request.graph.document_id,
    )
    validate_motion_graph_bindings(document, request.graph, request.reality_model)
    payload_hash = motion_graph_digest(request.graph)
    existing = db.scalar(
        select(StudioMotionGraph).where(
            StudioMotionGraph.workspace_id == request.workspace_id,
            StudioMotionGraph.idempotency_key == request.idempotency_key,
        )
    )
    if existing is not None:
        if existing.payload_hash != payload_hash:
            raise ValueError("motion_graph_idempotency_conflict")
        return existing
    record = StudioMotionGraph(
        id=request.graph.graph_id,
        workspace_id=request.workspace_id,
        document_id=request.graph.document_id,
        document_revision=request.graph.document_revision,
        status=request.graph.status,
        storage_revision=1,
        graph_digest_sha256=payload_hash,
        graph=request.graph.model_dump(mode="json", by_alias=True, exclude_none=True),
        evaluation=None,
        idempotency_key=request.idempotency_key,
        payload_hash=payload_hash,
        created_by=user.id,
        updated_by=user.id,
    )
    db.add(record)
    emit_event(
        db,
        workspace_id=request.workspace_id,
        event_type="studio.motion-graph.created",
        aggregate_type="motion_graph",
        aggregate_id=record.id,
        correlation_id=document.correlation_id,
        actor_id=user.id,
        payload={"documentId": document.document_id, "documentRevision": document.revision},
    )
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        repeated = db.scalar(
            select(StudioMotionGraph).where(
                StudioMotionGraph.workspace_id == request.workspace_id,
                StudioMotionGraph.idempotency_key == request.idempotency_key,
            )
        )
        if repeated is not None and repeated.payload_hash == payload_hash:
            return repeated
        raise ValueError("motion_graph_identity_conflict") from error
    db.refresh(record)
    return record


def replace_motion_graph(
    db: Session,
    record: StudioMotionGraph,
    request: ReplaceMotionGraphRequestV1,
    user: User,
) -> StudioMotionGraph:
    if record.workspace_id != request.workspace_id:
        raise ValueError("motion_graph_workspace_mismatch")
    if record.storage_revision != request.expected_revision:
        raise ValueError("motion_graph_conflict")
    if request.graph.graph_id != record.id or request.graph.document_id != record.document_id:
        raise ValueError("motion_graph_identity_mismatch")
    document = _document_contract(
        db,
        workspace_id=request.workspace_id,
        document_id=record.document_id,
    )
    validate_motion_graph_bindings(document, request.graph, request.reality_model)
    digest = motion_graph_digest(request.graph)
    record.document_revision = request.graph.document_revision
    record.status = "suggested"
    record.storage_revision += 1
    record.graph_digest_sha256 = digest
    record.graph = request.graph.model_dump(mode="json", by_alias=True, exclude_none=True)
    record.evaluation = None
    record.payload_hash = digest
    record.updated_by = user.id
    emit_event(
        db,
        workspace_id=record.workspace_id,
        event_type="studio.motion-graph.updated",
        aggregate_type="motion_graph",
        aggregate_id=record.id,
        correlation_id=document.correlation_id,
        actor_id=user.id,
        payload={"storageRevision": record.storage_revision},
    )
    db.commit()
    db.refresh(record)
    return record


def review_motion_graph(
    db: Session,
    record: StudioMotionGraph,
    request: ReviewMotionGraphRequestV1,
    user: User,
) -> StudioMotionGraph:
    if record.workspace_id != request.workspace_id:
        raise ValueError("motion_graph_workspace_mismatch")
    if record.storage_revision != request.expected_revision:
        raise ValueError("motion_graph_conflict")
    graph = MotionGraphV1.model_validate(record.graph)
    document = _document_contract(
        db,
        workspace_id=request.workspace_id,
        document_id=record.document_id,
    )
    reviewed = graph.model_copy(update={"status": "reviewed"})
    evaluation = evaluate_motion_graph(document, reviewed, request.reality_model)
    if not evaluation.eligible_for_reviewed_projection:
        raise ValueError("motion_graph_constraints_block_review")
    digest = motion_graph_digest(reviewed)
    record.status = "reviewed"
    record.storage_revision += 1
    record.graph_digest_sha256 = digest
    record.graph = reviewed.model_dump(mode="json", by_alias=True, exclude_none=True)
    record.evaluation = evaluation.model_dump(mode="json", by_alias=True, exclude_none=True)
    record.payload_hash = digest
    record.updated_by = user.id
    emit_event(
        db,
        workspace_id=record.workspace_id,
        event_type="studio.motion-graph.reviewed",
        aggregate_type="motion_graph",
        aggregate_id=record.id,
        correlation_id=document.correlation_id,
        actor_id=user.id,
        payload={
            "storageRevision": record.storage_revision,
            "evaluationDigest": evaluation.graph_digest_sha256,
        },
    )
    db.commit()
    db.refresh(record)
    return record
