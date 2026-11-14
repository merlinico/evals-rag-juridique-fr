"""Config id registry coverage."""

from __future__ import annotations

from rag_juridique.retrieval.registry import (
    CHUNKER_KEYS,
    MVP_ALIASES,
    RETRIEVER_KEYS,
    all_config_ids,
    describe_config,
    heavy_config_ids,
    light_config_ids,
)


def test_config_id_cartesian_product():
    ids = all_config_ids(include_mvp_aliases=False)
    assert len(ids) == len(RETRIEVER_KEYS) * len(CHUNKER_KEYS)
    assert all("__" in i for i in ids)


def test_mvp_aliases_resolve():
    a = describe_config("chunk_500")
    b = describe_config("hybrid_e5__fixed_500")
    assert a.retriever_key == b.retriever_key == "hybrid_e5"
    assert a.chunker_key == b.chunker_key == "fixed_500"
    assert MVP_ALIASES["chunk_1000"] == "hybrid_e5__fixed_1000"


def test_light_vs_heavy_partition():
    light = set(light_config_ids())
    assert "chunk_500" in light and "chunk_1000" in light
    assert all(x.startswith("bm25__") or x.startswith("chunk_") for x in light)
    heavy = set(heavy_config_ids())
    assert "dense_bge_m3__fixed_500" in heavy
    assert "hybrid_bge_m3_rerank__per_article" in heavy
    assert "bm25__fixed_500" not in heavy
