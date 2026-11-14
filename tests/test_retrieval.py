from rag_juridique.corpus.chunking import chunk_articles
from rag_juridique.corpus.loader import load_corpus
from rag_juridique.retrieval.bm25 import BM25Index


def test_bm25_finds_retractation_article():
    corpus = load_corpus()
    chunks = chunk_articles(corpus.articles, chunk_size=800, overlap=100)
    index = BM25Index.build(chunks)
    hits = index.search(
        "délai de quatorze jours pour exercer le droit de rétractation",
        top_k=5,
    )
    assert hits
    nums = {h[0].article_num for h in hits}
    assert "L. 221-18" in nums


def test_corpus_has_expected_size():
    corpus = load_corpus()
    assert len(corpus) >= 50
    # Phase-2 multi-code snapshot (legacy MVP ids were cdc-v0.1-…)
    assert "2025-07-13" in corpus.snapshot_id
