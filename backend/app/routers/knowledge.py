from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import KnowledgeChunk, KnowledgeDocument, LibraryAsset, Membership, User
from ..schemas import KnowledgeDocumentIn, KnowledgeDocumentOut, KnowledgeSearchOut
from ..security import get_current_user
from ..services.knowledge import (
    OpenAICompatibleEmbeddingProvider,
    chunk_content,
    document_hash,
    hybrid_search,
    normalize_content,
)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


def assert_access(db: Session, user_id: str, workspace_id: str) -> None:
    if not db.scalar(
        select(Membership.id).where(Membership.user_id == user_id, Membership.workspace_id == workspace_id)
    ):
        raise HTTPException(status_code=404, detail="Workspace not found")


def document_out(document: KnowledgeDocument, chunk_count: int | None = None) -> KnowledgeDocumentOut:
    return KnowledgeDocumentOut(
        id=document.id,
        workspace_id=document.workspace_id,
        asset_id=document.asset_id,
        title=document.title,
        source_type=document.source_type,
        source_url=document.source_url,
        language=document.language,
        metadata=document.document_metadata or {},
        status=document.status,
        embedding_status=document.embedding_status,
        embedding_model=document.embedding_model,
        chunk_count=len(document.chunks) if chunk_count is None else chunk_count,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


@router.get("/documents", response_model=list[KnowledgeDocumentOut])
def list_documents(
    workspace_id: str = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[KnowledgeDocumentOut]:
    assert_access(db, user.id, workspace_id)
    rows = db.execute(
        select(KnowledgeDocument, func.count(KnowledgeChunk.id))
        .outerjoin(KnowledgeChunk)
        .where(KnowledgeDocument.workspace_id == workspace_id)
        .group_by(KnowledgeDocument.id)
        .order_by(KnowledgeDocument.created_at.desc())
    ).all()
    return [document_out(document, int(count)) for document, count in rows]


@router.post("/documents", response_model=KnowledgeDocumentOut, status_code=status.HTTP_201_CREATED)
def create_document(
    data: KnowledgeDocumentIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> KnowledgeDocumentOut:
    assert_access(db, user.id, data.workspace_id)
    if data.asset_id and not db.scalar(
        select(LibraryAsset.id).where(LibraryAsset.id == data.asset_id, LibraryAsset.workspace_id == data.workspace_id)
    ):
        raise HTTPException(status_code=422, detail="Asset does not belong to workspace")
    content = normalize_content(data.content)
    if not content:
        raise HTTPException(status_code=422, detail="Document has no searchable content")
    content_hash = document_hash(content)
    if db.scalar(
        select(KnowledgeDocument.id).where(
            KnowledgeDocument.workspace_id == data.workspace_id,
            KnowledgeDocument.content_hash == content_hash,
        )
    ):
        raise HTTPException(status_code=409, detail="Document content already exists in workspace")
    chunks = chunk_content(content)
    provider = OpenAICompatibleEmbeddingProvider()
    vectors: list[list[float]] | None = None
    embedding_status = "unconfigured"
    embedding_model = None
    if provider.configured:
        try:
            vectors, trace = provider.embed([chunk.content for chunk in chunks])
            embedding_status = "ready"
            embedding_model = str(trace["model"])
        except Exception:
            embedding_status = "failed"
    document = KnowledgeDocument(
        workspace_id=data.workspace_id,
        asset_id=data.asset_id,
        title=data.title.strip(),
        source_type=data.source_type,
        source_url=data.source_url,
        language=data.language,
        document_metadata=data.metadata,
        content_hash=content_hash,
        status="ready",
        embedding_status=embedding_status,
        embedding_model=embedding_model,
    )
    db.add(document)
    try:
        db.flush()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="Document content already exists in workspace") from error
    for index, chunk in enumerate(chunks):
        db.add(
            KnowledgeChunk(
                document_id=document.id,
                workspace_id=document.workspace_id,
                chunk_index=index,
                content=chunk.content,
                char_start=chunk.char_start,
                char_end=chunk.char_end,
                citation={
                    "documentId": document.id,
                    "title": document.title,
                    "sourceType": document.source_type,
                    "sourceUrl": document.source_url,
                    "chunkIndex": index,
                    "charStart": chunk.char_start,
                    "charEnd": chunk.char_end,
                },
                embedding=vectors[index] if vectors else None,
            )
        )
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="Document content already exists in workspace") from error
    db.refresh(document)
    return document_out(document, len(chunks))


@router.get("/search", response_model=KnowledgeSearchOut)
def search_knowledge(
    workspace_id: str = Query(...),
    q: str = Query(..., min_length=2, max_length=500),
    limit: int = Query(default=8, ge=1, le=20),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> KnowledgeSearchOut:
    assert_access(db, user.id, workspace_id)
    provider = OpenAICompatibleEmbeddingProvider()
    query_embedding = None
    embedding_model = None
    if provider.configured:
        try:
            vectors, trace = provider.embed([q])
            query_embedding = vectors[0]
            embedding_model = str(trace["model"])
        except Exception:
            query_embedding = None
    results = hybrid_search(db, workspace_id, q, query_embedding, limit)
    return KnowledgeSearchOut(
        query=q,
        retrieval_mode="hybrid" if query_embedding else "lexical",
        embedding_model=embedding_model,
        results=results,
    )


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    document = db.get(KnowledgeDocument, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Knowledge document not found")
    assert_access(db, user.id, document.workspace_id)
    db.delete(document)
    db.commit()
