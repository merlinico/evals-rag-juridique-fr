"""BM25 index and Retriever protocol implementation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Sequence

from rank_bm25 import BM25Okapi

from rag_juridique.contracts.chunking import Chunk, Chunker
from rag_juridique.contracts.corpus import Article, ArticleVersion, CrossRef
from rag_juridique.contracts.retrieval import RetrievedChunk
from rag_juridique.corpus.chunking import FixedSizeChunker

_TOKEN_RE = re.compile(r"[\w\-']+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text)]


@dataclass
class BM25Index:
    chunks: list[Chunk]
    _bm25: BM25Okapi

    @classmethod
    def build(cls, chunks: list[Chunk]) -> BM25Index:
        corpus = [tokenize(c.text) for c in chunks]
        return cls(chunks=chunks, _bm25=BM25Okapi(corpus))

    def search(self, query: str, top_k: int = 10) -> list[tuple[Chunk, float]]:
        if not self.chunks:
            return []
        scores = self._bm25.get_scores(tokenize(query))
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:top_k]
        return [(self.chunks[i], float(score)) for i, score in ranked if score > 0]


class BM25Retriever:
    """Sparse BM25 retriever implementing the frozen Retriever protocol."""

    name = "bm25"

    def __init__(
        self,
        articles: list[Article],
        *,
        chunker: Chunker | None = None,
        chunk_size: int = 800,
        overlap: int = 100,
        versions: list[ArticleVersion] | None = None,
        cross_refs: Sequence[CrossRef] | None = None,
    ) -> None:
        del cross_refs  # accepted for uniform factory signatures
        self.articles = articles
        self.versions = versions
        self.chunker = chunker or FixedSizeChunker(
            chunk_size=chunk_size, overlap=overlap, versions=versions
        )
        self._index_by_as_of: dict[date | None, BM25Index] = {}
        self._chunks_by_as_of: dict[date | None, list[Chunk]] = {}
        # Eager tip index (as_of=None).
        self._ensure_index(None)

    def _ensure_index(self, as_of: date | None) -> BM25Index:
        if as_of in self._index_by_as_of:
            return self._index_by_as_of[as_of]
        chunks = self.chunker.chunk(self.articles, as_of=as_of)
        index = BM25Index.build(chunks)
        self._chunks_by_as_of[as_of] = chunks
        self._index_by_as_of[as_of] = index
        return index

    @property
    def chunks(self) -> list[Chunk]:
        return self._chunks_by_as_of[None]

    def retrieve(
        self,
        query: str,
        k: int,
        as_of: date | None = None,
    ) -> list[RetrievedChunk]:
        # Temporal index only when versions are available; else as_of is a no-op.
        key = as_of if self.versions else None
        index = self._ensure_index(key)
        hits = index.search(query, top_k=k)
        return [
            RetrievedChunk(chunk=chunk, score=score, bm25_rank=rank)
            for rank, (chunk, score) in enumerate(hits, start=1)
        ]
