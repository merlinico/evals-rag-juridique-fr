"""Retriever protocol and ranked hit type."""

from __future__ import annotations

from datetime import date
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from rag_juridique.contracts.chunking import Chunk


class RetrievedChunk(BaseModel):
    """A ranked retrieval hit."""

    model_config = ConfigDict(extra="ignore")

    chunk: Chunk
    score: float
    bm25_rank: int | None = None
    dense_rank: int | None = None
    rerank_score: float | None = None
    graph_hops: int | None = Field(
        default=None,
        description="Hops followed over CrossRef edges, if graph retrieval",
    )


@runtime_checkable
class Retriever(Protocol):
    """Retrieval boundary used by eval / generation.

    Signature frozen for phase 2::

        retrieve(query, k, as_of=None) -> list[RetrievedChunk]
    """

    name: str

    def retrieve(
        self,
        query: str,
        k: int,
        as_of: date | None = None,
    ) -> list[RetrievedChunk]:
        """Return top-k ranked chunks for query (optionally as-of a date)."""
        ...
