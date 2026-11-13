"""Graph-following retrieval: expand top hits along CrossRef edges."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Protocol, Sequence

from rag_juridique.contracts.chunking import Chunk
from rag_juridique.contracts.corpus import CrossRef
from rag_juridique.contracts.retrieval import RetrievedChunk


class _BaseRetriever(Protocol):
    name: str

    def retrieve(
        self, query: str, k: int, as_of: date | None = None
    ) -> list[RetrievedChunk]: ...


def build_adjacency(
    cross_refs: Sequence[CrossRef],
) -> dict[str, list[str]]:
    """Undirected adjacency for following citations / renvois either way."""
    adj: dict[str, list[str]] = defaultdict(list)
    for ref in cross_refs:
        src, tgt = ref.source_article_id, ref.target_article_id
        if tgt not in adj[src]:
            adj[src].append(tgt)
        if src not in adj[tgt]:
            adj[tgt].append(src)
    return dict(adj)


class GraphFollowingRetriever:
    """Expand seed hits by walking CrossRef edges, then fill remaining slots.

    Seed retrieval comes from ``base``. Neighbour article chunks (hop 1, then
    optionally hop 2) are appended with decaying scores and ``graph_hops`` set.
    When ``cross_refs`` is empty, behaviour equals the base retriever
    (``graph_hops=None``).
    """

    name = "hybrid_graph"

    def __init__(
        self,
        base: _BaseRetriever,
        *,
        chunks: list[Chunk] | None = None,
        cross_refs: Sequence[CrossRef] | None = None,
        max_hops: int = 1,
        seed_k: int | None = None,
        name: str | None = None,
    ) -> None:
        self.base = base
        self.cross_refs = list(cross_refs or [])
        self.max_hops = max(0, max_hops)
        self.seed_k = seed_k
        self._adjacency = build_adjacency(self.cross_refs)
        self._chunks_by_article = _index_chunks_by_article(
            chunks if chunks is not None else _chunks_from_base(base)
        )
        if name:
            self.name = name
        elif getattr(base, "name", None):
            self.name = f"{base.name}_graph"

    def retrieve(
        self,
        query: str,
        k: int,
        as_of: date | None = None,
    ) -> list[RetrievedChunk]:
        seed_n = self.seed_k or max(k, 5)
        seeds = self.base.retrieve(query, k=seed_n, as_of=as_of)
        if not self._adjacency or self.max_hops == 0:
            return [
                hit.model_copy(update={"graph_hops": hit.graph_hops})
                for hit in seeds[:k]
            ]

        ordered: list[RetrievedChunk] = []
        seen_chunks: set[str] = set()
        seen_articles: set[str] = set()

        for hit in seeds:
            if hit.chunk.chunk_id in seen_chunks:
                continue
            seen_chunks.add(hit.chunk.chunk_id)
            seen_articles.add(hit.chunk.article_id)
            ordered.append(
                hit.model_copy(
                    update={"graph_hops": 0 if hit.graph_hops is None else hit.graph_hops}
                )
            )

        frontier = {h.chunk.article_id for h in ordered}
        for hop in range(1, self.max_hops + 1):
            nxt: set[str] = set()
            for article_id in frontier:
                for neighbour in self._adjacency.get(article_id, []):
                    if neighbour in seen_articles:
                        continue
                    nxt.add(neighbour)
                    for chunk in self._chunks_by_article.get(neighbour, []):
                        if chunk.chunk_id in seen_chunks:
                            continue
                        # Prefer chunks valid at as_of when version metadata exists.
                        if as_of is not None and chunk.as_of is not None and chunk.as_of != as_of:
                            continue
                        seen_chunks.add(chunk.chunk_id)
                        seen_articles.add(neighbour)
                        seed_score = ordered[0].score if ordered else 0.0
                        ordered.append(
                            RetrievedChunk(
                                chunk=chunk,
                                score=float(seed_score) / (hop + 1),
                                graph_hops=hop,
                            )
                        )
                        if len(ordered) >= k:
                            return ordered[:k]
            frontier = nxt
            if not frontier:
                break

        return ordered[:k]


def _index_chunks_by_article(chunks: list[Chunk]) -> dict[str, list[Chunk]]:
    out: dict[str, list[Chunk]] = defaultdict(list)
    for chunk in chunks:
        out[chunk.article_id].append(chunk)
    return dict(out)


def _chunks_from_base(base: object) -> list[Chunk]:
    chunks = getattr(base, "chunks", None)
    if chunks is not None:
        return list(chunks)
    return []
