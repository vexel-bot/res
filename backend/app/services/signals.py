import hashlib
import re
import unicodedata
from collections import Counter
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import ExternalSignal
from ..schemas import SignalIn


def content_hash(source: str, url: str, title: str) -> str:
    canonical = unicodedata.normalize("NFKC", f"{source}|{url}|{title}").strip().lower()
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def cluster_key(title: str) -> str:
    words = sorted(_signal_tokens(title))
    return hashlib.sha256(" ".join(words[:12]).encode("utf-8")).hexdigest()[:24]


def _signal_tokens(value: str) -> set[str]:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    normalized = "".join(character for character in normalized if not unicodedata.combining(character))
    stopwords = {"para", "como", "uma", "com", "dos", "das", "que", "por", "sobre", "apos", "entre"}
    return {token for token in re.findall(r"[a-z0-9]{4,}", normalized) if token not in stopwords}


def infer_topics(title: str, summary: str) -> list[str]:
    normalized = unicodedata.normalize("NFKD", f"{title} {summary}".casefold())
    normalized = "".join(character for character in normalized if not unicodedata.combining(character))
    tokens = re.findall(r"[a-z0-9]{4,}", normalized)
    ignored = {"para", "como", "uma", "com", "dos", "das", "que", "por", "sobre", "apos", "entre"}
    counts = Counter(token for token in tokens if token not in ignored)
    return [token for token, _ in counts.most_common(12)]


def infer_entities(title: str, summary: str) -> list[str]:
    words = re.findall(r"\b[\w-]+\b", f"{title}. {summary}")
    entities: list[str] = []
    current: list[str] = []
    for word in words + ["."]:
        if len(word) > 2 and word[:1].isupper():
            current.append(word)
            continue
        if current:
            entity = " ".join(current[:4])
            if entity not in entities:
                entities.append(entity)
            current = []
    return entities[:20]


def find_cluster_key(db: Session, data: SignalIn, published_at: datetime) -> str:
    title_tokens = _signal_tokens(data.title)
    if not title_tokens:
        return cluster_key(data.title)
    candidates = db.scalars(
        select(ExternalSignal).where(
            ExternalSignal.workspace_id == data.workspace_id,
            ExternalSignal.published_at >= published_at - timedelta(days=3),
            ExternalSignal.published_at <= published_at + timedelta(days=3),
        )
    ).all()
    best_key = None
    best_similarity = 0.0
    for candidate in candidates:
        candidate_tokens = _signal_tokens(candidate.title)
        similarity = len(title_tokens & candidate_tokens) / max(1, len(title_tokens | candidate_tokens))
        if similarity > best_similarity:
            best_key = candidate.cluster_key
            best_similarity = similarity
    return best_key if best_key and best_similarity >= 0.45 else cluster_key(data.title)


def normalize_and_store(db: Session, data: SignalIn) -> tuple[ExternalSignal, bool]:
    digest = content_hash(data.source, data.url, data.title)
    existing = db.scalar(
        select(ExternalSignal).where(
            ExternalSignal.workspace_id == data.workspace_id,
            ExternalSignal.source == data.source,
            ExternalSignal.content_hash == digest,
        )
    )
    if existing:
        return existing, False
    published_at = data.published_at
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=UTC)
    expires_at = data.expires_at or published_at + timedelta(days=7)
    signal = ExternalSignal(
        workspace_id=data.workspace_id,
        source=data.source.strip(),
        url=data.url.strip(),
        title=data.title.strip(),
        summary=data.summary.strip()[:5000],
        raw_text=data.raw_text[:20_000],
        published_at=published_at,
        expires_at=expires_at,
        language=data.language,
        region=data.region,
        category=data.category,
        topics=(data.topics or infer_topics(data.title, data.summary))[:50],
        entities=(data.entities or infer_entities(data.title, data.summary))[:50],
        metrics=data.metrics,
        content_hash=digest,
        cluster_key=find_cluster_key(db, data, published_at),
        status="normalized",
        collected_at=datetime.now(UTC),
    )
    db.add(signal)
    db.commit()
    db.refresh(signal)
    return signal, True
