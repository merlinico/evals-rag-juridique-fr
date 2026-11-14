"""Dense embedding index and Retriever (default model: BAAI/bge-m3)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from rag_juridique.contracts.chunking import Chunk, Chunker
from rag_juridique.contracts.corpus import Article, ArticleVersion, CrossRef
from rag_juridique.contracts.retrieval import RetrievedChunk
from rag_juridique.corpus.chunking import FixedSizeChunker
from rag_juridique.retrieval.cache import load_cached_embeddings, save_cached_embeddings
from rag_juridique.retrieval.light import HashEncoder, is_heavy_enabled

DEFAULT_DENSE_MODEL = "BAAI/bge-m3"
MVP_DENSE_MODEL = "intfloat/multilingual-e5-small"


@dataclass
class DenseIndex:
    chunks: list[Chunk]
    embeddings: np.ndarray
    model_name: str
    _model: Any | None = None

    @classmethod
    def build(
        cls,
        chunks: list[Chunk],
        model_name: str = DEFAULT_DENSE_MODEL,
        model: Any | None = None,
        *,
        cache_dir: Path | None = None,
        use_cache: bool = True,
    ) -> DenseIndex:
        encoder = model
        embeddings: np.ndarray | None = None

        # Cache is only meaningful on the heavy path (query encoder must match).
        if use_cache and encoder is None and is_heavy_enabled():
            embeddings = load_cached_embeddings(model_name, chunks, cache_dir)

        if embeddings is None:
            if encoder is None:
                encoder = _resolve_encoder(model_name)
            texts = [_passage_text(c, model_name) for c in chunks]
            emb = encoder.encode(
                texts, normalize_embeddings=True, show_progress_bar=False
            )
            embeddings = np.asarray(emb, dtype=np.float32)
            if (
                use_cache
                and is_heavy_enabled()
                and not isinstance(encoder, HashEncoder)
            ):
                save_cached_embeddings(model_name, chunks, embeddings, cache_dir)

        return cls(
            chunks=chunks,
            embeddings=embeddings,
            model_name=model_name,
            _model=encoder,
        )

    def search(self, query: str, top_k: int = 10) -> list[tuple[Chunk, float]]:
        if not self.chunks:
            return []
        if self._model is None:
            self._model = _resolve_encoder(self.model_name)
        q = _query_text(query, self.model_name)
        q_emb = self._model.encode(
            [q], normalize_embeddings=True, show_progress_bar=False
        )
        scores = (self.embeddings @ np.asarray(q_emb, dtype=np.float32).T).ravel()
        ranked = np.argsort(-scores)[:top_k]
        return [(self.chunks[i], float(scores[i])) for i in ranked]


def _resolve_encoder(model_name: str) -> Any:
    """Load a real SentenceTransformer only on the heavy path; else HashEncoder.

    The MVP CI path injects a live ``SentenceTransformer`` into HybridRetriever /
    DenseIndex so baseline recall stays meaningful without ``RAG_HEAVY``.
    """
    if model_name.startswith("hash") or not is_heavy_enabled():
        return HashEncoder(model_name=f"hash:{model_name}")
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name)


def _is_e5(model_name: str) -> bool:
    return "e5" in model_name.lower()


def _query_text(query: str, model_name: str) -> str:
    return f"query: {query}" if _is_e5(model_name) else query


def _passage_text(chunk: Chunk, model_name: str) -> str:
    return f"passage: {chunk.text}" if _is_e5(model_name) else chunk.text


class DenseRetriever:
    """Dense retriever (BAAI/bge-m3 by default) implementing Retriever."""

    name = "dense_bge_m3"

    def __init__(
        self,
        articles: list[Article],
        *,
        chunker: Chunker | None = None,
        chunk_size: int = 800,
        overlap: int = 100,
        embedding_model: str = DEFAULT_DENSE_MODEL,
        dense_model: Any | None = None,
        versions: list[ArticleVersion] | None = None,
        cross_refs: Sequence[CrossRef] | None = None,
        cache_dir: Path | None = None,
        use_cache: bool = True,
    ) -> None:
        del cross_refs
        self.articles = articles
        self.versions = versions
        self.embedding_model = embedding_model
        self._injected_model = dense_model
        self.cache_dir = cache_dir
        self.use_cache = use_cache
        self.chunker = chunker or FixedSizeChunker(
            chunk_size=chunk_size, overlap=overlap, versions=versions
        )
        self._index_by_as_of: dict[date | None, DenseIndex] = {}
        self._chunks_by_as_of: dict[date | None, list[Chunk]] = {}
        self._ensure_index(None)

    def _ensure_index(self, as_of: date | None) -> DenseIndex:
        if as_of in self._index_by_as_of:
            return self._index_by_as_of[as_of]
        chunks = self.chunker.chunk(self.articles, as_of=as_of)
        index = DenseIndex.build(
            chunks,
            model_name=self.embedding_model,
            model=self._injected_model,
            cache_dir=self.cache_dir,
            use_cache=self.use_cache and self._injected_model is None,
        )
        self._chunks_by_as_of[as_of] = chunks
        self._index_by_as_of[as_of] = index
        return index

    @property
    def chunks(self) -> list[Chunk]:
        return self._chunks_by_as_of[None]

    @property
    def dense(self) -> DenseIndex:
        return self._index_by_as_of[None]

    def retrieve(
        self,
        query: str,
        k: int,
        as_of: date | None = None,
    ) -> list[RetrievedChunk]:
        key = as_of if self.versions else None
        index = self._ensure_index(key)
        hits = index.search(query, top_k=k)
        return [
            RetrievedChunk(chunk=chunk, score=score, dense_rank=rank)
            for rank, (chunk, score) in enumerate(hits, start=1)
        ]
