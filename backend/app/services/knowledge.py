from __future__ import annotations

import hashlib
import math
import re
import time
from dataclasses import dataclass
from typing import Any

import httpx
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import EMBEDDING_DIMENSIONS, KnowledgeChunk, KnowledgeDocument

MAX_DOCUMENT_CHARS = 200_000
CHUNK_CHARS = 1_200
CHUNK_OVERLAP_CHARS = 160
RRF_K = 60


class EmbeddingUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class ChunkText:
    content: str
    char_start: int
    char_end: int


class OpenAICompatibleEmbeddingProvider:
    def __init__(self) -> None:
        settings = get_settings()
        self.base_url = (settings.ai_base_url or "").rstrip("/")
        self.api_key = settings.ai_api_key
        self.model = settings.ai_embedding_model

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.api_key and self.model)

    def embed(self, texts: list[str]) -> tuple[list[list[float]], dict[str, Any]]:
        if not self.configured:
            raise EmbeddingUnavailable("No embedding provider is configured")
        started = time.perf_counter()
        with httpx.Client(timeout=60) as client:
            response = client.post(
                f"{self.base_url}/embeddings",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": self.model, "input": texts, "dimensions": EMBEDDING_DIMENSIONS},
            )
            response.raise_for_status()
            payload = response.json()
        ordered = sorted(payload.get("data", []), key=lambda item: item.get("index", 0))
        vectors = [item.get("embedding", []) for item in ordered]
        if len(vectors) != len(texts) or any(len(vector) != EMBEDDING_DIMENSIONS for vector in vectors):
            raise EmbeddingUnavailable(f"Embedding provider must return {EMBEDDING_DIMENSIONS} dimensions")
        return vectors, {
            "provider": "openai-compatible",
            "model": self.model,
            "latencyMs": round((time.perf_counter() - started) * 1000),
            "usage": payload.get("usage", {}),
        }


def normalize_content(content: str) -> str:
    normalized = content.replace("\x00", " ").replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def document_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def chunk_content(content: str) -> list[ChunkText]:
    if not content:
        return []
    chunks: list[ChunkText] = []
    start = 0
    while start < len(content):
        hard_end = min(len(content), start + CHUNK_CHARS)
        end = hard_end
        if hard_end < len(content):
            candidates = [content.rfind("\n\n", start, hard_end), content.rfind(". ", start, hard_end)]
            boundary = max(candidates)
            if boundary >= start + CHUNK_CHARS // 2:
                end = boundary + (2 if content[boundary : boundary + 2] in {"\n\n", ". "} else 0)
        chunk = content[start:end].strip()
        if chunk:
            actual_start = content.find(chunk, start, end)
            chunks.append(ChunkText(chunk, actual_start, actual_start + len(chunk)))
        if end >= len(content):
            break
        next_start = max(start + 1, end - CHUNK_OVERLAP_CHARS)
        whitespace = content.find(" ", next_start, min(len(content), next_start + 80))
        start = whitespace + 1 if whitespace >= 0 else next_start
    return chunks


def _tokens(value: str) -> set[str]:
    return {token for token in re.findall(r"\w+", value.casefold()) if len(token) > 1}


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if not left_norm or not right_norm:
        return 0.0
    return numerator / (left_norm * right_norm)


def _lexical_candidates(db: Session, workspace_id: str, query: str, limit: int) -> list[tuple[str, float]]:
    if db.bind and db.bind.dialect.name == "postgresql":
        rows = db.execute(
            text(
                """
                WITH query AS (SELECT websearch_to_tsquery('simple', :query) AS value)
                SELECT chunk.id, ts_rank_cd(chunk.search_vector, query.value, 32) AS score
                FROM knowledge_chunks AS chunk, query
                WHERE chunk.workspace_id = :workspace_id
                  AND chunk.search_vector @@ query.value
                ORDER BY score DESC, chunk.id
                LIMIT :limit
                """
            ),
            {"query": query, "workspace_id": workspace_id, "limit": limit},
        ).all()
        return [(row.id, float(row.score or 0)) for row in rows]
    query_tokens = _tokens(query)
    chunks = db.scalars(select(KnowledgeChunk).where(KnowledgeChunk.workspace_id == workspace_id)).all()
    scored = []
    for chunk in chunks:
        content_tokens = _tokens(chunk.content)
        score = len(query_tokens & content_tokens) / max(1, len(query_tokens))
        if score:
            scored.append((chunk.id, score))
    return sorted(scored, key=lambda item: (-item[1], item[0]))[:limit]


def _vector_candidates(
    db: Session, workspace_id: str, query_embedding: list[float], limit: int
) -> list[tuple[str, float]]:
    if db.bind and db.bind.dialect.name == "postgresql":
        distance = KnowledgeChunk.embedding.cosine_distance(query_embedding)
        rows = db.execute(
            select(KnowledgeChunk.id, distance.label("distance"))
            .where(KnowledgeChunk.workspace_id == workspace_id, KnowledgeChunk.embedding.is_not(None))
            .order_by(distance, KnowledgeChunk.id)
            .limit(limit)
        ).all()
        return [(row.id, max(0.0, 1.0 - float(row.distance))) for row in rows]
    chunks = db.scalars(
        select(KnowledgeChunk).where(KnowledgeChunk.workspace_id == workspace_id, KnowledgeChunk.embedding.is_not(None))
    ).all()
    scored = [(chunk.id, _cosine_similarity(chunk.embedding or [], query_embedding)) for chunk in chunks]
    return sorted(scored, key=lambda item: (-item[1], item[0]))[:limit]


def hybrid_search(
    db: Session,
    workspace_id: str,
    query: str,
    query_embedding: list[float] | None,
    limit: int,
) -> list[dict[str, Any]]:
    candidate_limit = max(limit * 4, 20)
    lexical = _lexical_candidates(db, workspace_id, query, candidate_limit)
    semantic = _vector_candidates(db, workspace_id, query_embedding, candidate_limit) if query_embedding else []
    lexical_scores = dict(lexical)
    semantic_scores = dict(semantic)
    fused: dict[str, float] = {}
    for rank, (chunk_id, _) in enumerate(lexical, start=1):
        fused[chunk_id] = fused.get(chunk_id, 0) + 1 / (RRF_K + rank)
    for rank, (chunk_id, _) in enumerate(semantic, start=1):
        fused[chunk_id] = fused.get(chunk_id, 0) + 1 / (RRF_K + rank)
    ordered_ids = sorted(fused, key=lambda chunk_id: (-fused[chunk_id], chunk_id))[:limit]
    if not ordered_ids:
        return []
    chunks = db.scalars(select(KnowledgeChunk).where(KnowledgeChunk.id.in_(ordered_ids))).all()
    chunk_map = {chunk.id: chunk for chunk in chunks}
    documents = db.scalars(
        select(KnowledgeDocument).where(KnowledgeDocument.id.in_({chunk.document_id for chunk in chunks}))
    ).all()
    document_map = {document.id: document for document in documents}
    results = []
    for chunk_id in ordered_ids:
        chunk = chunk_map[chunk_id]
        document = document_map[chunk.document_id]
        results.append(
            {
                "documentId": document.id,
                "chunkId": chunk.id,
                "title": document.title,
                "content": chunk.content,
                "score": fused[chunk.id],
                "lexicalScore": lexical_scores.get(chunk.id),
                "semanticScore": semantic_scores.get(chunk.id),
                "citation": chunk.citation,
            }
        )
    return results
