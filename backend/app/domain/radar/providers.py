from __future__ import annotations

from typing import Protocol


class ResearchProvider(Protocol):
    name: str

    def research(self, query: str, *, language: str, region: str) -> list[dict]: ...


class EmbeddingProvider(Protocol):
    name: str

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class SemanticMatcher(Protocol):
    name: str

    def similarity(self, left: str, right: str) -> float: ...


class LexicalSemanticMatcher:
    """Provider-neutral deterministic baseline; it makes no semantic-model claim."""

    name = "builtin.lexical-jaccard"

    def similarity(self, left: str, right: str) -> float:
        from .scoring import _tokens

        left_tokens = _tokens(left)
        right_tokens = _tokens(right)
        return len(left_tokens & right_tokens) / max(1, len(left_tokens | right_tokens))
