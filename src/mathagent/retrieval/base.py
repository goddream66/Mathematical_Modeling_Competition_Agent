from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_\u4e00-\u9fff]+")


@dataclass(frozen=True)
class RetrievalChunk:
    source: str
    content: str
    title: str | None = None
    score: float | None = None
    chunk_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RetrievalResult:
    query: str = ""
    provider: str = "none"
    chunks: list[RetrievalChunk] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not self.chunks


class Retriever(ABC):
    name: str = "retriever"

    @abstractmethod
    def retrieve(
        self,
        query: str,
        *,
        problem_text: str,
        input_data: dict[str, Any] | None = None,
        top_k: int = 5,
    ) -> RetrievalResult:
        raise NotImplementedError


class NullRetriever(Retriever):
    name = "none"

    def retrieve(
        self,
        query: str,
        *,
        problem_text: str,
        input_data: dict[str, Any] | None = None,
        top_k: int = 5,
    ) -> RetrievalResult:
        return RetrievalResult(query=query, provider=self.name, chunks=[])


@dataclass(frozen=True)
class StaticRetriever(Retriever):
    chunks: list[RetrievalChunk] = field(default_factory=list)
    name: str = "static"

    def retrieve(
        self,
        query: str,
        *,
        problem_text: str,
        input_data: dict[str, Any] | None = None,
        top_k: int = 5,
    ) -> RetrievalResult:
        del problem_text, input_data
        selected = list(self.chunks[: max(top_k, 0)])
        return RetrievalResult(query=query, provider=self.name, chunks=selected)


def retrieval_result_to_payload(
    result: RetrievalResult,
    *,
    query: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    selected = select_retrieval_chunks(result, query=query or result.query, limit=limit)
    return {
        "provider": result.provider,
        "query": result.query or (query or ""),
        "chunks": [
            {
                "chunk_id": chunk.chunk_id,
                "source": chunk.source,
                "title": chunk.title,
                "score": chunk.score,
                "content": chunk.content,
                "metadata": chunk.metadata,
            }
            for chunk in selected
        ],
    }


def format_retrieval_context(
    result: RetrievalResult,
    *,
    query: str | None = None,
    limit: int = 4,
    max_chars: int = 1600,
) -> str:
    selected = select_retrieval_chunks(result, query=query or result.query, limit=limit)
    if not selected:
        return "No retrieval context available."

    lines = [
        f"Retriever: {result.provider}",
        f"Query: {result.query or (query or '')}",
        "Retrieved references:",
    ]
    remaining = max(max_chars, 0)
    for index, chunk in enumerate(selected, start=1):
        title = f" | title={chunk.title}" if chunk.title else ""
        score = f" | score={chunk.score}" if chunk.score is not None else ""
        preview = " ".join(chunk.content.split())
        if remaining:
            preview = preview[:remaining]
            remaining = max(remaining - len(preview), 0)
        lines.append(f"[{index}] source={chunk.source}{title}{score}")
        lines.append(preview)
        if remaining <= 0:
            break
    return "\n".join(lines).strip()


def select_retrieval_chunks(
    result: RetrievalResult,
    *,
    query: str | None = None,
    limit: int | None = None,
) -> list[RetrievalChunk]:
    if not result.chunks:
        return []
    if limit is not None and limit <= 0:
        return []

    target_tokens = _tokenize(query or result.query)
    scored: list[tuple[float, float, int, RetrievalChunk]] = []
    for index, chunk in enumerate(result.chunks):
        chunk_tokens = _tokenize(" ".join(part for part in [chunk.title or "", chunk.content] if part))
        overlap = len(target_tokens & chunk_tokens)
        lexical_score = overlap / max(len(target_tokens), 1) if target_tokens else 0.0
        base_score = float(chunk.score) if chunk.score is not None else 0.0
        scored.append((lexical_score, base_score, -index, chunk))

    scored.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)
    selected = [item[-1] for item in scored]
    if limit is None:
        return selected
    return selected[:limit]


def _tokenize(text: str) -> set[str]:
    return {
        token.lower()
        for token in _TOKEN_PATTERN.findall(text or "")
        if token and (len(token) > 1 or any("\u4e00" <= char <= "\u9fff" for char in token))
    }
