"""Comparable retrieval config ids and factories.

Config id scheme
----------------
``{retriever}__{chunker}`` where:

Retrievers
  - ``bm25``
  - ``dense_bge_m3``
  - ``hybrid_bge_m3``
  - ``hybrid_bge_m3_rerank``
  - ``hybrid_bge_m3_graph``
  - ``hybrid_e5`` (MVP baseline encoder)

Chunkers
  - ``fixed_500`` / ``fixed_1000``
  - ``per_article``
  - ``structural`` (fixed windows @ 800 with parent context)

MVP aliases kept for CI baselines: ``chunk_500`` → ``hybrid_e5__fixed_500``,
``chunk_1000`` → ``hybrid_e5__fixed_1000``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from rag_juridique.contracts.chunking import Chunker
from rag_juridique.contracts.corpus import Article, ArticleVersion, CrossRef
from rag_juridique.contracts.retrieval import Retriever
from rag_juridique.corpus.chunking import (
    FixedSizeChunker,
    PerArticleChunker,
    StructuralChunker,
)
from rag_juridique.retrieval.bm25 import BM25Retriever
from rag_juridique.retrieval.dense import DEFAULT_DENSE_MODEL, MVP_DENSE_MODEL, DenseRetriever
from rag_juridique.retrieval.graph import GraphFollowingRetriever
from rag_juridique.retrieval.hybrid import HybridRetriever
from rag_juridique.retrieval.rerank import DEFAULT_RERANKER_MODEL, RerankingRetriever

# --- chunker keys -----------------------------------------------------------

CHUNKER_FIXED_500 = "fixed_500"
CHUNKER_FIXED_1000 = "fixed_1000"
CHUNKER_PER_ARTICLE = "per_article"
CHUNKER_STRUCTURAL = "structural"

CHUNKER_KEYS: tuple[str, ...] = (
    CHUNKER_FIXED_500,
    CHUNKER_FIXED_1000,
    CHUNKER_PER_ARTICLE,
    CHUNKER_STRUCTURAL,
)

# --- retriever keys ---------------------------------------------------------

RET_BM25 = "bm25"
RET_DENSE = "dense_bge_m3"
RET_HYBRID_BGE = "hybrid_bge_m3"
RET_HYBRID_RERANK = "hybrid_bge_m3_rerank"
RET_HYBRID_GRAPH = "hybrid_bge_m3_graph"
RET_HYBRID_E5 = "hybrid_e5"

RETRIEVER_KEYS: tuple[str, ...] = (
    RET_BM25,
    RET_DENSE,
    RET_HYBRID_BGE,
    RET_HYBRID_RERANK,
    RET_HYBRID_GRAPH,
    RET_HYBRID_E5,
)

MVP_ALIASES: dict[str, str] = {
    "chunk_500": f"{RET_HYBRID_E5}__{CHUNKER_FIXED_500}",
    "chunk_1000": f"{RET_HYBRID_E5}__{CHUNKER_FIXED_1000}",
}


@dataclass(frozen=True)
class RetrievalConfig:
    """Resolved retrieval configuration."""

    config_id: str
    retriever_key: str
    chunker_key: str
    chunk_size: int | None
    embedding_model: str | None
    reranker_model: str | None
    uses_graph: bool
    uses_rerank: bool
    heavy: bool


def _parse_config_id(config_id: str) -> tuple[str, str]:
    resolved = MVP_ALIASES.get(config_id, config_id)
    if "__" not in resolved:
        raise ValueError(
            f"Invalid config_id {config_id!r}; expected "
            f"'{{retriever}}__{{chunker}}' or MVP alias chunk_500/chunk_1000"
        )
    retriever_key, chunker_key = resolved.split("__", 1)
    if retriever_key not in RETRIEVER_KEYS:
        raise ValueError(f"Unknown retriever key in config_id: {retriever_key!r}")
    if chunker_key not in CHUNKER_KEYS:
        raise ValueError(f"Unknown chunker key in config_id: {chunker_key!r}")
    return retriever_key, chunker_key


def all_config_ids(*, include_mvp_aliases: bool = True) -> list[str]:
    """Return every comparable config id (retriever × chunker)."""
    ids = [f"{r}__{c}" for r in RETRIEVER_KEYS for c in CHUNKER_KEYS]
    if include_mvp_aliases:
        ids = list(MVP_ALIASES.keys()) + ids
    return ids


def describe_config(config_id: str) -> RetrievalConfig:
    retriever_key, chunker_key = _parse_config_id(config_id)
    chunk_size = {
        CHUNKER_FIXED_500: 500,
        CHUNKER_FIXED_1000: 1000,
        CHUNKER_PER_ARTICLE: None,
        CHUNKER_STRUCTURAL: 800,
    }[chunker_key]
    embedding_model: str | None
    if retriever_key == RET_BM25:
        embedding_model = None
    elif retriever_key == RET_HYBRID_E5:
        embedding_model = MVP_DENSE_MODEL
    else:
        embedding_model = DEFAULT_DENSE_MODEL
    uses_rerank = retriever_key == RET_HYBRID_RERANK
    uses_graph = retriever_key == RET_HYBRID_GRAPH
    heavy = retriever_key not in {RET_BM25, RET_HYBRID_E5} or uses_rerank
    # hybrid_e5 is "medium": CI injects the model; not gated on RAG_HEAVY.
    if retriever_key == RET_HYBRID_E5:
        heavy = False
    return RetrievalConfig(
        config_id=config_id,
        retriever_key=retriever_key,
        chunker_key=chunker_key,
        chunk_size=chunk_size,
        embedding_model=embedding_model,
        reranker_model=DEFAULT_RERANKER_MODEL if uses_rerank else None,
        uses_graph=uses_graph,
        uses_rerank=uses_rerank,
        heavy=heavy,
    )


def build_chunker(
    chunker_key: str,
    *,
    overlap: int = 100,
    versions: list[ArticleVersion] | None = None,
) -> Chunker:
    if chunker_key == CHUNKER_FIXED_500:
        return FixedSizeChunker(chunk_size=500, overlap=overlap, versions=versions)
    if chunker_key == CHUNKER_FIXED_1000:
        return FixedSizeChunker(chunk_size=1000, overlap=overlap, versions=versions)
    if chunker_key == CHUNKER_PER_ARTICLE:
        return PerArticleChunker(versions=versions)
    if chunker_key == CHUNKER_STRUCTURAL:
        return StructuralChunker(chunk_size=800, overlap=overlap, versions=versions)
    raise ValueError(f"Unknown chunker_key: {chunker_key!r}")


def build_retriever(
    config_id: str,
    articles: list[Article],
    *,
    versions: list[ArticleVersion] | None = None,
    cross_refs: Sequence[CrossRef] | None = None,
    overlap: int = 100,
    rrf_k: int = 60,
    dense_model: Any | None = None,
    rerank_model: Any | None = None,
    cache_dir: Path | None = None,
) -> Retriever:
    """Instantiate a Retriever for ``config_id``."""
    meta = describe_config(config_id)
    chunker = build_chunker(meta.chunker_key, overlap=overlap, versions=versions)
    refs = list(cross_refs or [])

    if meta.retriever_key == RET_BM25:
        return BM25Retriever(
            articles, chunker=chunker, versions=versions, cross_refs=refs
        )

    if meta.retriever_key == RET_DENSE:
        return DenseRetriever(
            articles,
            chunker=chunker,
            embedding_model=DEFAULT_DENSE_MODEL,
            dense_model=dense_model,
            versions=versions,
            cross_refs=refs,
            cache_dir=cache_dir,
        )

    if meta.retriever_key in {RET_HYBRID_BGE, RET_HYBRID_E5, RET_HYBRID_RERANK, RET_HYBRID_GRAPH}:
        emb = (
            MVP_DENSE_MODEL
            if meta.retriever_key == RET_HYBRID_E5
            else DEFAULT_DENSE_MODEL
        )
        base = HybridRetriever(
            articles,
            chunker=chunker,
            embedding_model=emb,
            rrf_k=rrf_k,
            dense_model=dense_model,
            versions=versions,
            cross_refs=refs,
            cache_dir=cache_dir,
        )
        # Preserve MVP name for hybrid_e5 so baselines stay recognizable.
        if meta.retriever_key == RET_HYBRID_E5:
            base.name = "hybrid_rrf"
        elif meta.retriever_key == RET_HYBRID_BGE:
            base.name = "hybrid_bge_m3"

        if meta.retriever_key == RET_HYBRID_RERANK:
            return RerankingRetriever(
                base,
                model_name=DEFAULT_RERANKER_MODEL,
                model=rerank_model,
                name="hybrid_bge_m3_rerank",
            )
        if meta.retriever_key == RET_HYBRID_GRAPH:
            return GraphFollowingRetriever(
                base,
                chunks=base.chunks,
                cross_refs=refs,
                max_hops=1,
                name="hybrid_bge_m3_graph",
            )
        return base

    raise ValueError(f"Unhandled retriever_key: {meta.retriever_key!r}")


def light_config_ids() -> list[str]:
    """Configs safe for default CI (BM25 + MVP hybrid aliases)."""
    return [
        "chunk_500",
        "chunk_1000",
        *[f"{RET_BM25}__{c}" for c in CHUNKER_KEYS],
    ]


def heavy_config_ids() -> list[str]:
    """Configs that need RAG_HEAVY or an injected encoder for real metrics."""
    return [cid for cid in all_config_ids(include_mvp_aliases=False) if describe_config(cid).heavy]
