"""Graph expansion and temporal as_of filtering."""

from __future__ import annotations

from datetime import date

from rag_juridique.contracts.corpus import Article, ArticleVersion, CrossRef, CrossRefKind
from rag_juridique.corpus.chunking import PerArticleChunker
from rag_juridique.retrieval.bm25 import BM25Retriever
from rag_juridique.retrieval.graph import GraphFollowingRetriever, build_adjacency


def _docs() -> list[Article]:
    return [
        Article(id="S", num="L. 1", title="Article L. 1", text="source alpha renvoi"),
        Article(id="T", num="L. 2", title="Article L. 2", text="cible beta unique"),
        Article(id="U", num="L. 3", title="Article L. 3", text="autre gamma"),
    ]


def test_build_adjacency_undirected():
    refs = [
        CrossRef(
            source_article_id="S",
            target_article_id="T",
            kind=CrossRefKind.EXPLICIT_CITATION,
        )
    ]
    adj = build_adjacency(refs)
    assert adj["S"] == ["T"]
    assert adj["T"] == ["S"]


def test_graph_expands_crossref_neighbour():
    articles = _docs()
    base = BM25Retriever(articles, chunker=PerArticleChunker())
    refs = [
        CrossRef(
            source_article_id="S",
            target_article_id="T",
            kind=CrossRefKind.RENVOI,
            target_num="L. 2",
        )
    ]
    graph = GraphFollowingRetriever(
        base, chunks=base.chunks, cross_refs=refs, max_hops=1, seed_k=1
    )
    hits = graph.retrieve("source alpha renvoi", k=5)
    ids = [h.chunk.article_id for h in hits]
    assert ids[0] == "S"
    assert "T" in ids
    hop1 = next(h for h in hits if h.chunk.article_id == "T")
    assert hop1.graph_hops == 1


def test_bm25_as_of_switches_version_text():
    articles = _docs()
    versions = [
        ArticleVersion(
            version_id="S-old",
            article_id="S",
            num="L. 1",
            text="ancienne formulation UNIQUEOLD",
            debut=date(2015, 1, 1),
            fin=date(2021, 1, 1),
        ),
        ArticleVersion(
            version_id="S-new",
            article_id="S",
            num="L. 1",
            text="nouvelle formulation UNIQUENEW",
            debut=date(2021, 1, 1),
            fin=None,
        ),
    ]
    ret = BM25Retriever(
        articles, chunker=PerArticleChunker(versions=versions), versions=versions
    )
    old_hits = ret.retrieve("UNIQUEOLD", k=3, as_of=date(2018, 5, 1))
    new_hits = ret.retrieve("UNIQUENEW", k=3, as_of=date(2022, 5, 1))
    assert old_hits and old_hits[0].chunk.article_id == "S"
    assert "UNIQUEOLD" in old_hits[0].chunk.text
    assert new_hits and new_hits[0].chunk.article_id == "S"
    assert "UNIQUENEW" in new_hits[0].chunk.text


def test_as_of_noop_when_no_versions():
    ret = BM25Retriever(_docs(), chunker=PerArticleChunker())
    a = ret.retrieve("alpha", k=2, as_of=None)
    b = ret.retrieve("alpha", k=2, as_of=date(2010, 1, 1))
    assert [h.chunk.chunk_id for h in a] == [h.chunk.chunk_id for h in b]
