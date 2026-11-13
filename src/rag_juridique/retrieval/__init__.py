"""Retrieval package — BM25, dense bge-m3, hybrid, rerank, graph."""

from rag_juridique.contracts.retrieval import RetrievedChunk, Retriever
from rag_juridique.retrieval.bm25 import BM25Index, BM25Retriever
from rag_juridique.retrieval.dense import DEFAULT_DENSE_MODEL, DenseIndex, DenseRetriever
from rag_juridique.retrieval.graph import GraphFollowingRetriever
from rag_juridique.retrieval.hybrid import HybridRetriever, RetrievalResult, rrf_fuse
from rag_juridique.retrieval.registry import (
    all_config_ids,
    build_retriever,
    describe_config,
    light_config_ids,
)
from rag_juridique.retrieval.rerank import DEFAULT_RERANKER_MODEL, RerankingRetriever

__all__ = [
    "BM25Index",
    "BM25Retriever",
    "DEFAULT_DENSE_MODEL",
    "DEFAULT_RERANKER_MODEL",
    "DenseIndex",
    "DenseRetriever",
    "GraphFollowingRetriever",
    "HybridRetriever",
    "RetrievalResult",
    "RetrievedChunk",
    "Retriever",
    "RerankingRetriever",
    "all_config_ids",
    "build_retriever",
    "describe_config",
    "light_config_ids",
    "rrf_fuse",
]
