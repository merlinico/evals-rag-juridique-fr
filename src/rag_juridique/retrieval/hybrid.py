from __future__ import annotations

from datetime import date
from typing import Any

from rag_juridique.contracts.chunking import Chunk
from rag_juridique.contracts.corpus import Article
from rag_juridique.contracts.retrieval import RetrievedChunk
from rag_juridique.corpus.chunking import FixedSizeChunker, chunk_articles
from rag_juridique.retrieval.bm25 import BM25Index
from rag_juridique.retrieval.dense import DenseIndex

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
        embedding_model: str = "intfloat/multilingual-e5-small",
        rrf_k: int = 60,
        dense_model: Any | None = None,
        chunker: FixedSizeChunker | None = None,
    ) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.embedding_model = embedding_model
        self.rrf_k = rrf_k
        self.chunker = chunker or FixedSizeChunker(
            chunk_size=chunk_size, overlap=overlap
        )
        self.chunks = self.chunker.chunk(articles)
        self.bm25 = BM25Index.build(self.chunks)
        self.dense = DenseIndex.build(
            self.chunks, model_name=embedding_model, model=dense_model
        )

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
        `as_of` is accepted for protocol compatibility (unused until temporal corpus).
        """
        del as_of
        limit = k if k is not None else (top_k if top_k is not None else 5)
        pool = max(limit * 4, 20)
        bm25_hits = self.bm25.search(query, top_k=pool)
        dense_hits = self.dense.search(query, top_k=pool)
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


# Keep chunk_articles import path usable for tests that build indexes manually.
__all__ = [
    "HybridRetriever",
    "RetrievalResult",
    "RetrievedChunk",
    "chunk_articles",
    "rrf_fuse",
]
