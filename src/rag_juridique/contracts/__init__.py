"""Frozen inter-module data contracts for phase-2 parallel work.

Modules must speak these types across boundaries. Implementations live in
owned packages; this package is shared and must not gain feature logic.
"""

from rag_juridique.contracts.chunking import Chunk, Chunker
from rag_juridique.contracts.corpus import Article, ArticleVersion, CrossRef, CrossRefKind
from rag_juridique.contracts.generation import GenerationFixture, GenerationRecord
from rag_juridique.contracts.gold import GoldSet, Question, QuestionType
from rag_juridique.contracts.metrics import (
    MetricName,
    MetricReport,
    MetricResult,
    PerConfigMetrics,
)
from rag_juridique.contracts.retrieval import RetrievedChunk, Retriever

__all__ = [
    "Article",
    "ArticleVersion",
    "Chunk",
    "Chunker",
    "CrossRef",
    "CrossRefKind",
    "GenerationFixture",
    "GenerationRecord",
    "GoldSet",
    "MetricName",
    "MetricReport",
    "MetricResult",
    "PerConfigMetrics",
    "Question",
    "QuestionType",
    "RetrievedChunk",
    "Retriever",
]
