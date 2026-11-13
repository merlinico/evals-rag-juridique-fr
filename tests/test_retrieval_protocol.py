"""Retriever protocol conformity for all phase-2 implementations."""

from __future__ import annotations

from datetime import date

from rag_juridique.contracts.corpus import Article, CrossRef, CrossRefKind
from rag_juridique.contracts.retrieval import Retriever
from rag_juridique.corpus.loader import load_corpus
from rag_juridique.retrieval.bm25 import BM25Retriever
from rag_juridique.retrieval.dense import DenseRetriever
from rag_juridique.retrieval.graph import GraphFollowingRetriever
from rag_juridique.retrieval.hybrid import HybridRetriever
from rag_juridique.retrieval.light import HashEncoder
from rag_juridique.retrieval.registry import all_config_ids, build_retriever, describe_config
from rag_juridique.retrieval.rerank import RerankingRetriever


def _tiny_articles() -> list[Article]:
    corpus = load_corpus()
    return corpus.articles[:8]


def test_bm25_retriever_protocol():
    ret = BM25Retriever(_tiny_articles(), chunk_size=400, overlap=50)
    assert isinstance(ret, Retriever)
    hits = ret.retrieve("rétractation quatorze jours", k=3, as_of=None)
    assert len(hits) <= 3
    assert all(h.chunk.chunk_id for h in hits)


def test_dense_and_hybrid_use_hash_encoder_without_heavy(monkeypatch):
    monkeypatch.delenv("RAG_HEAVY", raising=False)
    articles = _tiny_articles()
    encoder = HashEncoder(dim=64)
    dense = DenseRetriever(
        articles, chunk_size=400, overlap=50, dense_model=encoder, use_cache=False
    )
    hybrid = HybridRetriever(
        articles, chunk_size=400, overlap=50, dense_model=encoder
    )
    assert isinstance(dense, Retriever)
    assert isinstance(hybrid, Retriever)
    assert dense.retrieve("information précontractuelle", k=2)
    assert hybrid.retrieve("information précontractuelle", k=2, as_of=None)


def test_reranker_and_graph_protocol():
    articles = _tiny_articles()
    encoder = HashEncoder(dim=64)
    base = HybridRetriever(articles, chunk_size=500, overlap=50, dense_model=encoder)
    refs = [
        CrossRef(
            source_article_id=articles[0].id,
            target_article_id=articles[1].id,
            kind=CrossRefKind.RENVOI,
            target_num=articles[1].num,
        )
    ]

    class _Stub:
        def predict(self, pairs, show_progress_bar=False):
            return [float(len(p[1])) for p in pairs]

    rerank = RerankingRetriever(base, model=_Stub())
    graph = GraphFollowingRetriever(base, chunks=base.chunks, cross_refs=refs, max_hops=1)
    assert isinstance(rerank, Retriever)
    assert isinstance(graph, Retriever)
    assert rerank.retrieve("consommateur", k=3, as_of=date(2024, 1, 1))
    hits = graph.retrieve("consommateur", k=5)
    assert hits
    assert all(h.graph_hops is not None for h in hits)


def test_registry_builds_all_configs_light():
    articles = _tiny_articles()
    encoder = HashEncoder(dim=32)
    ids = all_config_ids(include_mvp_aliases=True)
    assert "chunk_500" in ids
    assert "bm25__per_article" in ids
    assert "hybrid_bge_m3_rerank__structural" in ids
    # Smoke-build a representative subset.
    for cid in (
        "bm25__fixed_500",
        "dense_bge_m3__per_article",
        "hybrid_bge_m3__structural",
        "hybrid_bge_m3_rerank__fixed_500",
        "hybrid_bge_m3_graph__fixed_500",
        "chunk_500",
    ):
        meta = describe_config(cid)
        assert meta.config_id == cid
        ret = build_retriever(
            cid,
            articles,
            dense_model=encoder,
            rerank_model=_PredictStub(),
            cross_refs=[
                CrossRef(
                    source_article_id=articles[0].id,
                    target_article_id=articles[1].id,
                    kind=CrossRefKind.EXPLICIT_CITATION,
                )
            ],
        )
        assert isinstance(ret, Retriever)
        assert ret.retrieve("prix", k=2)


class _PredictStub:
    def predict(self, pairs, show_progress_bar=False):
        return [1.0 / (i + 1) for i, _ in enumerate(pairs)]
