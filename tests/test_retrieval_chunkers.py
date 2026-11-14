"""Phase-2 chunkers: fixed-size, per-article, structural + as_of."""

from __future__ import annotations

from datetime import date

from rag_juridique.contracts.chunking import Chunker
from rag_juridique.contracts.corpus import Article, ArticleVersion
from rag_juridique.corpus.chunking import (
    FixedSizeChunker,
    PerArticleChunker,
    StructuralChunker,
    get_chunker,
    hierarchy_parent_context,
)


def _articles() -> list[Article]:
    return [
        Article(
            id="A1",
            num="L. 1-1",
            title="Article L. 1-1",
            text=("mot " * 200).strip(),
            livre="Livre Ier",
            titre="Titre Ier",
            chapitre="Chapitre Ier",
            contexte="Livre Ier > Titre Ier > Chapitre Ier",
        ),
        Article(
            id="A2",
            num="L. 2-1",
            title="Article L. 2-1",
            text="court",
            contexte="Autre contexte",
        ),
    ]


def test_chunkers_satisfy_protocol():
    for chunker in (
        FixedSizeChunker(chunk_size=100, overlap=20),
        PerArticleChunker(),
        StructuralChunker(chunk_size=100, overlap=20),
    ):
        assert isinstance(chunker, Chunker)
        chunks = chunker.chunk(_articles())
        assert chunks
        assert all(c.chunk_id for c in chunks)


def test_per_article_one_chunk_each():
    chunks = PerArticleChunker().chunk(_articles())
    assert len(chunks) == 2
    assert {c.article_id for c in chunks} == {"A1", "A2"}
    assert all(c.chunk_id.endswith("#0") for c in chunks)


def test_structural_sets_parent_context():
    chunks = StructuralChunker(chunk_size=80, overlap=10).chunk(_articles())
    a1 = [c for c in chunks if c.article_id == "A1"]
    assert a1
    assert a1[0].parent_context is not None
    assert "Livre Ier" in a1[0].parent_context
    assert a1[0].parent_context in a1[0].text


def test_hierarchy_fallback_to_contexte():
    art = Article(
        id="X",
        num="L. 9-9",
        title="Article L. 9-9",
        text="x",
        contexte="Partie > Livre > Titre",
    )
    assert hierarchy_parent_context(art) == "Partie > Livre > Titre"


def test_as_of_applies_version_text():
    versions = [
        ArticleVersion(
            version_id="A1-v1",
            article_id="A1",
            num="L. 1-1",
            text="texte historique unique XYZ",
            debut=date(2018, 1, 1),
            fin=date(2022, 1, 1),
        ),
        ArticleVersion(
            version_id="A1-v2",
            article_id="A1",
            num="L. 1-1",
            text="texte actuel ABC",
            debut=date(2022, 1, 1),
            fin=None,
        ),
    ]
    chunker = PerArticleChunker(versions=versions)
    old = chunker.chunk(_articles(), as_of=date(2020, 6, 1))
    new = chunker.chunk(_articles(), as_of=date(2023, 1, 1))
    a1_old = next(c for c in old if c.article_id == "A1")
    a1_new = next(c for c in new if c.article_id == "A1")
    assert "historique" in a1_old.text
    assert "actuel" in a1_new.text
    assert a1_old.version_id == "A1-v1"
    assert a1_new.version_id == "A1-v2"


def test_as_of_noop_without_versions():
    chunker = FixedSizeChunker(chunk_size=200, overlap=20)
    a = chunker.chunk(_articles(), as_of=None)
    b = chunker.chunk(_articles(), as_of=date(2020, 1, 1))
    assert [c.text for c in a] == [c.text for c in b]


def test_get_chunker_factory():
    assert get_chunker("fixed_size", chunk_size=500).name == "fixed_size"
    assert get_chunker("per_article").name == "per_article"
    assert get_chunker("structural").name == "structural"
