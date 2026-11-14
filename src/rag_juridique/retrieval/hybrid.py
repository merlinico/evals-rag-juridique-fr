"""Hybrid BM25 + dense retrieval with Reciprocal Rank Fusion."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Sequence

from rag_juridique.contracts.chunking import Chunk, Chunker
from rag_juridique.contracts.corpus import Article, ArticleVersion, CrossRef
from rag_juridique.contracts.retrieval import RetrievedChunk
from rag_juridique.corpus.chunking import FixedSizeChunker, chunk_articles
from rag_juridique.retrieval.bm25 import BM25Index
from rag_juridique.retrieval.dense import MVP_DENSE_MODEL, DenseIndex

# Back-compat alias: MVP code and tests imported RetrievalResult.
RetrievalResult = RetrievedChunk


def rrf_fuse(
    bm25_hits: list[tuple[Chunk, float]],
    dense_hits: list[tuple[Chunk, float]],
    k: int = 60,
) -> list[RetrievedChunk]:
    """Reciprocal Rank Fusion of BM25 and dense hits."""
    scores: dict[str, float] = {}
    meta: dict[str, dict[str, Any]] = {}

    for rank, (chunk, _) in enumerate(bm25_hits, start=1):
        scores[chunk.chunk_id] = scores.get(chunk.chunk_id, 0.0) + 1.0 / (k + rank)
        meta.setdefault(chunk.chunk_id, {"chunk": chunk})["bm25_rank"] = rank

    for rank, (chunk, _) in enumerate(dense_hits, start=1):
        scores[chunk.chunk_id] = scores.get(chunk.chunk_id, 0.0) + 1.0 / (k + rank)
        entry = meta.setdefault(chunk.chunk_id, {"chunk": chunk})
        entry["dense_rank"] = rank
        entry["chunk"] = chunk

    ordered = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    results: list[RetrievedChunk] = []
    for chunk_id, score in ordered:
        info = meta[chunk_id]
        results.append(
            RetrievedChunk(
                chunk=info["chunk"],
                score=score,
                bm25_rank=info.get("bm25_rank"),
                dense_rank=info.get("dense_rank"),
            )
        )
    return results


class HybridRetriever:
    """Hybrid BM25 + dense retriever implementing the frozen Retriever protocol."""

    name = "hybrid_rrf"

    def __init__(
        self,
        articles: list[Article],
        chunk_size: int = 800,
        overlap: int = 100,
        embedding_model: str = MVP_DENSE_MODEL,
        rrf_k: int = 60,
        dense_model: Any | None = None,
        chunker: Chunker | None = None,
        versions: list[ArticleVersion] | None = None,
        cross_refs: Sequence[CrossRef] | None = None,
        cache_dir: Path | None = None,
        use_cache: bool = True,
    ) -> None:
        del cross_refs
        self.articles = articles
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.embedding_model = embedding_model
        self.rrf_k = rrf_k
        self.versions = versions
        self._injected_model = dense_model
        self.cache_dir = cache_dir
        self.use_cache = use_cache
        self.chunker = chunker or FixedSizeChunker(
            chunk_size=chunk_size, overlap=overlap, versions=versions
        )
        self._state_by_as_of: dict[
            date | None, tuple[list[Chunk], BM25Index, DenseIndex]
        ] = {}
        self._ensure_state(None)

    def _ensure_state(
        self, as_of: date | None
    ) -> tuple[list[Chunk], BM25Index, DenseIndex]:
        if as_of in self._state_by_as_of:
            return self._state_by_as_of[as_of]
        chunks = self.chunker.chunk(self.articles, as_of=as_of)
        bm25 = BM25Index.build(chunks)
        dense = DenseIndex.build(
            chunks,
            model_name=self.embedding_model,
            model=self._injected_model,
            cache_dir=self.cache_dir,
            use_cache=self.use_cache and self._injected_model is None,
        )
        state = (chunks, bm25, dense)
        self._state_by_as_of[as_of] = state
        return state

    @property
    def chunks(self) -> list[Chunk]:
        return self._state_by_as_of[None][0]

    @property
    def bm25(self) -> BM25Index:
        return self._state_by_as_of[None][1]

    @property
    def dense(self) -> DenseIndex:
        return self._state_by_as_of[None][2]

    def retrieve(
        self,
        query: str,
        k: int | None = None,
        as_of: date | None = None,
        *,
        top_k: int | None = None,
    ) -> list[RetrievedChunk]:
        """Retrieve top-k chunks.

        `k` is the frozen protocol parameter; `top_k` remains as MVP alias.
        `as_of` selects a temporal index when versions were provided at build.
        """
        limit = k if k is not None else (top_k if top_k is not None else 5)
        key = as_of if self.versions else None
        _chunks, bm25, dense = self._ensure_state(key)
        pool = max(limit * 4, 20)
        bm25_hits = bm25.search(query, top_k=pool)
        dense_hits = dense.search(query, top_k=pool)
        fused = rrf_fuse(bm25_hits, dense_hits, k=self.rrf_k)
        return fused[:limit]

    def retrieve_article_ids(self, query: str, top_k: int = 5) -> list[str]:
        hits = self.retrieve(query, k=top_k)
        seen: list[str] = []
        for hit in hits:
            aid = hit.chunk.article_id
            if aid not in seen:
                seen.append(aid)
        return seen


__all__ = [
    "HybridRetriever",
    "RetrievalResult",
    "RetrievedChunk",
    "chunk_articles",
    "rrf_fuse",
]
