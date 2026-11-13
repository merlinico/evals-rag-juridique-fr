from rag_juridique.corpus.chunking import Chunk
from rag_juridique.retrieval.hybrid import rrf_fuse


def _c(i: str) -> Chunk:
    return Chunk(
        chunk_id=i,
        article_id=i,
        article_num=i,
        title=i,
        text=i,
        start_char=0,
        end_char=1,
    )


def test_rrf_prefers_consensus():
    a, b, c = _c("a"), _c("b"), _c("c")
    bm25 = [(a, 10.0), (b, 9.0), (c, 1.0)]
    dense = [(b, 0.9), (a, 0.8), (c, 0.1)]
    fused = rrf_fuse(bm25, dense, k=60)
    assert fused[0].chunk.chunk_id in {"a", "b"}
    assert {f.chunk.chunk_id for f in fused[:2]} == {"a", "b"}
