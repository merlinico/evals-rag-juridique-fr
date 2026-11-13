"""Contracts validate MVP data and expose frozen protocols/schemas."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from rag_juridique.contracts.chunking import Chunker
from rag_juridique.contracts.corpus import Article, ArticleVersion, CrossRef, CrossRefKind
from rag_juridique.contracts.export_schemas import (
    SCHEMA_MODELS,
    default_schemas_dir,
    export_schemas,
)
from rag_juridique.contracts.generation import GenerationRecord
from rag_juridique.contracts.gold import GoldSet, Question, QuestionType
from rag_juridique.contracts.metrics import MetricReport, MetricResult, PerConfigMetrics
from rag_juridique.corpus.chunking import FixedSizeChunker
from rag_juridique.corpus.loader import load_corpus
from rag_juridique.generation.ollama import load_generation_records
from rag_juridique.gold.loader import load_gold, load_gold_set
from rag_juridique.retrieval.hybrid import HybridRetriever

ROOT = Path(__file__).resolve().parents[1]


def test_article_and_corpus_roundtrip():
    corpus = load_corpus()
    assert len(corpus) >= 50
    art = corpus.articles[0]
    assert isinstance(art, Article)
    assert art.id.startswith("LEGIARTI")
    assert art.display_id == art.num


def test_version_and_crossref_models():
    ver = ArticleVersion(
        version_id="LEGIARTI000044142438",
        article_id="LEGIARTI000044142438",
        num="L. 111-1",
        text="…",
        debut=date(2022, 1, 1),
        fin=None,
    )
    ref = CrossRef(
        source_article_id="LEGIARTI000032227350",
        target_article_id="LEGIARTI000044142438",
        kind=CrossRefKind.EXPLICIT_CITATION,
        target_num="L. 111-1",
    )
    assert ver.fin is None
    assert ref.kind == CrossRefKind.EXPLICIT_CITATION


def test_gold_infers_type_from_legacy():
    gold = load_gold_set(ROOT / "data" / "gold" / "questions.json")
    assert isinstance(gold, GoldSet)
    questions = load_gold(ROOT / "data" / "gold" / "questions.json")
    assert len(questions) >= 35
    unans = [q for q in questions if q.unanswerable]
    assert unans
    assert all(q.type == QuestionType.UNANSWERABLE for q in unans)
    directs = [q for q in questions if not q.unanswerable]
    assert all(q.type == QuestionType.DIRECT for q in directs)


def test_question_temporal_fields():
    q = Question(
        id="t1",
        question="Quel texte s'appliquait ?",
        type=QuestionType.TEMPORAL,
        expected_article_ids=["LEGIARTI000044142438"],
        as_of=date(2020, 6, 1),
        validated=False,
    )
    assert q.as_of == date(2020, 6, 1)


def test_generation_fixture_legacy_alias():
    records = load_generation_records(
        str(ROOT / "data" / "fixtures" / "generations_chunk_500.json")
    )
    assert len(records) >= 30
    first = records[0]
    assert isinstance(first, GenerationRecord)
    assert first.question_id
    assert first.cited_ids or first.answer
    assert first.config_id.startswith("chunk_")


def test_fixed_chunker_protocol():
    chunker = FixedSizeChunker(chunk_size=200, overlap=20)
    assert isinstance(chunker, Chunker)
    corpus = load_corpus()
    chunks = chunker.chunk(corpus.articles[:3])
    assert chunks
    assert chunks[0].chunk_id


def test_hybrid_retriever_protocol_signature():
    assert "as_of" in HybridRetriever.retrieve.__code__.co_varnames
    assert "k" in HybridRetriever.retrieve.__code__.co_varnames
    assert HybridRetriever.name == "hybrid_rrf"


def test_metric_report_contract():
    per = PerConfigMetrics(
        config_id="chunk_500",
        chunk_size=500,
        recall_at_k=0.95,
        faithfulness=0.88,
        metrics=[MetricResult(name="recall_at_k", value=0.95, k=5)],
    )
    report = MetricReport(configs=[per])
    assert report.configs[0].metric_map()["recall_at_k"] == 0.95


def test_export_schemas_writes_files(tmp_path: Path):
    written = export_schemas(tmp_path)
    names = {p.stem for p in written}
    assert names == set(SCHEMA_MODELS)
    for path in written:
        assert path.stat().st_size > 50


def test_committed_schemas_match_models():
    schemas_dir = default_schemas_dir()
    assert schemas_dir.is_dir()
    for name in SCHEMA_MODELS:
        path = schemas_dir / f"{name}.json"
        assert path.is_file(), f"missing schema {path}"
