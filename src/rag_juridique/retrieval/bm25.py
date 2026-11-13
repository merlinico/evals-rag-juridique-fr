from __future__ import annotations

import re
from dataclasses import dataclass

from rank_bm25 import BM25Okapi

from rag_juridique.corpus.chunking import Chunk

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
        scores = self._bm25.get_scores(tokenize(query))
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:top_k]
        return [(self.chunks[i], float(score)) for i, score in ranked if score > 0]
