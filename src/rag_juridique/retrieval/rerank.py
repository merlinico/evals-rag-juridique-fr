"""Cross-encoder reranker wrapping any Retriever (default: BAAI/bge-reranker-v2-m3)."""

from __future__ import annotations

from datetime import date
from typing import Any, Protocol

from rag_juridique.contracts.retrieval import RetrievedChunk
from rag_juridique.retrieval.light import HashEncoder, is_heavy_enabled

DEFAULT_RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"


class _BaseRetriever(Protocol):
    name: str

    def retrieve(
        self, query: str, k: int, as_of: date | None = None
    ) -> list[RetrievedChunk]: ...


class _HashCrossEncoder:
    """CPU-light stand-in: score = cosine of hash embeddings of (query, passage)."""

    def __init__(self, model_name: str = "hash-reranker") -> None:
        self.model_name = model_name
        self._encoder = HashEncoder(dim=256, model_name=model_name)

    def predict(self, pairs: list[list[str]], show_progress_bar: bool = False) -> list[float]:
        del show_progress_bar
        scores: list[float] = []
        for query, passage in pairs:
            q = self._encoder.encode([query], normalize_embeddings=True)[0]
            p = self._encoder.encode([passage], normalize_embeddings=True)[0]
            scores.append(float(q @ p))
        return scores


def _resolve_cross_encoder(model_name: str, model: Any | None = None) -> Any:
    if model is not None:
        return model
    if not is_heavy_enabled():
        return _HashCrossEncoder(model_name=f"hash:{model_name}")
    from sentence_transformers import CrossEncoder

    return CrossEncoder(model_name)


class RerankingRetriever:
    """Retrieve a candidate pool then rerank with a multilingual cross-encoder."""

    name = "hybrid_rerank"

    def __init__(
        self,
        base: _BaseRetriever,
        *,
        model_name: str = DEFAULT_RERANKER_MODEL,
        model: Any | None = None,
        candidate_multiplier: int = 4,
        min_candidates: int = 20,
        name: str | None = None,
    ) -> None:
        self.base = base
        self.model_name = model_name
        self.candidate_multiplier = candidate_multiplier
        self.min_candidates = min_candidates
        self._model = _resolve_cross_encoder(model_name, model)
        if name:
            self.name = name
        elif getattr(base, "name", None):
            self.name = f"{base.name}_rerank"

    def retrieve(
        self,
        query: str,
        k: int,
        as_of: date | None = None,
    ) -> list[RetrievedChunk]:
        pool = max(k * self.candidate_multiplier, self.min_candidates)
        candidates = self.base.retrieve(query, k=pool, as_of=as_of)
        if not candidates:
            return []
        pairs = [[query, hit.chunk.text] for hit in candidates]
        raw_scores = self._model.predict(pairs, show_progress_bar=False)
        scored: list[RetrievedChunk] = []
        for hit, rerank_score in zip(candidates, raw_scores, strict=True):
            scored.append(
                hit.model_copy(
                    update={
                        "score": float(rerank_score),
                        "rerank_score": float(rerank_score),
                    }
                )
            )
        scored.sort(key=lambda h: h.score, reverse=True)
        return scored[:k]
