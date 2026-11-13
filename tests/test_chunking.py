from rag_juridique.corpus.chunking import chunk_articles
from rag_juridique.corpus.loader import Article


def test_chunk_overlap_and_ids():
    articles = [
        Article(
            id="A1",
            num="L. 1-1",
            title="Article L. 1-1",
            text=("mot " * 300).strip(),
        )
    ]
    chunks = chunk_articles(articles, chunk_size=100, overlap=20)
    assert len(chunks) > 1
    assert chunks[0].chunk_id.startswith("A1#")
    assert all(c.article_num == "L. 1-1" for c in chunks)


def test_small_article_single_chunk():
    articles = [Article(id="A2", num="L. 2-1", title="Article L. 2-1", text="court")]
    chunks = chunk_articles(articles, chunk_size=500, overlap=50)
    assert len(chunks) == 1
