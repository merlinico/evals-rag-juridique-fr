from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from rag_juridique.corpus.chunking import Chunk


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
        model_name: str = "intfloat/multilingual-e5-small",
        model: Any | None = None,
    ) -> DenseIndex:
        encoder = model
        if encoder is None:
            from sentence_transformers import SentenceTransformer

            encoder = SentenceTransformer(model_name)

        texts = [_passage_text(c, model_name) for c in chunks]
        emb = encoder.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return cls(
            chunks=chunks,
            embeddings=np.asarray(emb, dtype=np.float32),
            model_name=model_name,
            _model=encoder,
        )

    def search(self, query: str, top_k: int = 10) -> list[tuple[Chunk, float]]:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        q = _query_text(query, self.model_name)
        q_emb = self._model.encode([q], normalize_embeddings=True, show_progress_bar=False)
        scores = (self.embeddings @ np.asarray(q_emb, dtype=np.float32).T).ravel()
        ranked = np.argsort(-scores)[:top_k]
        return [(self.chunks[i], float(scores[i])) for i in ranked]


def _is_e5(model_name: str) -> bool:
    return "e5" in model_name.lower()


def _query_text(query: str, model_name: str) -> str:
    return f"query: {query}" if _is_e5(model_name) else query


def _passage_text(chunk: Chunk, model_name: str) -> str:
    return f"passage: {chunk.text}" if _is_e5(model_name) else chunk.text
